"""CPU-only provenance/isolation tests using synthetic examples, no test corpus."""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from qwenlab.financial_pilot import base_input, label, make, normalize
from qwenlab.financial_public_rewrite import stage, retain_domain_examples
from qwenlab import financial_public_rewrite as pipeline


def source(key='massive-train-unit', message='请帮我播放完整的一首爵士音乐', integrated=False):
    return {
        'dataset': 'massive', 'source_path': 'data/raw/massive-1.1-zh-CN.jsonl',
        'source_id': key, 'source_group': 'massive-' + message,
        'source_message': message, 'source_history': [],
        'source_labels': {'intent': 'play_music'}, 'source_dialog_id': None,
        'source_turn_index': None, 'already_processed': False,
        'already_integrated': integrated, 'disposition_suggestion': 'out_of_scope_rewrite_pool',
    }


def candidate(src=None, message='请说明页面中“每月一期”这几个字的含义'):
    src = src or source()
    row = make('rewrite-unit', 'authored-family', base_input(message),
        label('answer', '只解释输入中已有文本，不提供未知条款'),
        {'kind': 'synthetic-unit', 'source': src['source_path'],
         'parent_id': src['source_id'], 'parent_message': src['source_message'],
         'parent_history': src['source_history'], 'source_split': 'train',
         'license': 'CC-BY-4.0' if src['dataset']=='massive' else 'Apache-2.0'})
    row['id'] = 'FIN-R3-UNIT'
    return row


class PublicRewriteTests(unittest.TestCase):
    def test_unknown_parent_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown TRAIN parent'):
            stage([], [candidate()], [], set())

    def test_integrated_parent_rejected(self):
        src = source(integrated=True)
        with self.assertRaisesRegex(ValueError, 'Already integrated'):
            stage([src], [candidate(src)], [], set())

    def test_parent_original_text_and_history_must_match(self):
        for field, value in [('parent_message', '假来源文本'), ('parent_history', [{'role': 'user', 'content': '不存在的过去'}])]:
            with self.subTest(field=field):
                row = candidate(); row['provenance'][field] = value
                with self.assertRaisesRegex(ValueError, 'Original .* mismatch'):
                    stage([source()], [row], [], set())

    def test_source_partition_and_path_must_match(self):
        for field, value in [('source_split', 'test'), ('source', 'data/raw/other.jsonl')]:
            with self.subTest(field=field):
                row = candidate(); row['provenance'][field] = value
                with self.assertRaisesRegex(ValueError, 'Wrong source partition/path'):
                    stage([source()], [row], [], set())

    def test_original_protected_message_quarantined(self):
        src = source()
        accepted, rejected = stage([src], [candidate(src)], [], {normalize(src['source_message'])})
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]['reason'], 'original_source_exact_protected_message')

    def test_rewrite_protected_message_quarantined(self):
        row = candidate()
        accepted, rejected = stage([source()], [row], [], {normalize(row['input']['message'])})
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]['reason'], 'rewrite_exact_protected_message')

    def test_same_visible_input_as_old_quarantined(self):
        old = candidate(); old['id'] = 'FIN-R3-OLD'
        accepted, rejected = stage([source()], [candidate()], [old], set())
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]['reason'], 'duplicate_visible_input')

    def test_repeat_parent_rejected_even_for_distinct_new_text(self):
        second = candidate(message='请解释输入里“申请中”的字面含义')
        second['id'] = 'FIN-R3-SECOND'
        with self.assertRaisesRegex(ValueError, 'Repeated selected parent'):
            stage([source()], [candidate(), second], [], set())

    def test_stage_does_not_mutate_authored_candidate(self):
        row = candidate(); before = deepcopy(row)
        accepted, rejected = stage([source()], [row], [], set())
        self.assertEqual(row, before)
        self.assertFalse(rejected)
        self.assertTrue(accepted[0]['scene_family_id'].startswith('public-source:'))

    def test_retained_used_integrated_and_blocked_excluded(self):
        a = source('a'); b = source('b', '请给我放点非常舒缓的音乐', True)
        c = source('c', '我现在想听一段爵士音乐')
        self.assertEqual(retain_domain_examples([a,b,c], {'a'}, {normalize(c['source_message'])}, []), [])

    def test_retained_ambiguous_activity_excluded(self):
        src = source(message='现在还有什么优惠活动可以参加吗')
        src['source_labels']['intent'] = 'recommendation_events'
        self.assertEqual(retain_domain_examples([src], set(), set(), []), [])

    def test_retained_mixed_financial_complaint_excluded(self):
        src = source(message='先别播放音乐了我想投诉刚才的重复扣款')
        self.assertEqual(retain_domain_examples([src], set(), set(), []), [])

    def test_crosswoz_retained_limit_one_per_dialog(self):
        a = source('cross-a', '请帮我看看那家酒店有没有早餐服务')
        a.update(dataset='crosswoz', source_dialog_id='unit-dialog', source_path='data/raw/crosswoz-train.json.zip')
        b = deepcopy(a); b['source_id'] = 'cross-b'; b['source_message'] = '这家酒店附近有没有免费的停车场呢'
        selected = retain_domain_examples([a,b], set(), set(), [])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['annotation']['action'], 'redirect')


class SavedLedgerTests(unittest.TestCase):
    def fixture(self, mutate=None, refresh_hash=True):
        """Tiny synthetic train inventory to exercise saved-ledger verification."""
        with ExitStack() as stack:
            root = Path('/synthetic-only'); out = root / 'out'; local = root / 'local'
            src = [source(), source('massive-train-other', '请把客厅正在放的音乐停下来')]
            rows, _ = stage(src, [candidate()], [], set())
            ledger = [dict(src[0], processing_status='financial_rewrite_candidate', output_id=rows[0]['id']),
                      dict(src[1], processing_status='pending_financial_adaptation_review')]
            audit = {'protected_file_hashes': {}, 'source_hashes': {}, 'quarantined': []}
            def digest(value):
                return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            manifest = {'cases_sha256': digest(rows),
                        'ledger_sha256': digest(ledger),
                        'full_inventory_status': {'financial_rewrite_candidate': 1, 'pending_financial_adaptation_review': 1}}
            if mutate:
                mutate(rows, ledger)
                if refresh_hash:
                    manifest.update(cases_sha256=digest(rows), ledger_sha256=digest(ledger))
            saved_rows = {out/'cases.jsonl': rows, local/'inventory.jsonl': ledger, root/pipeline.INTEGRATED: []}
            saved_json = {out/'isolation-audit.json': audit, out/'manifest.json': manifest}
            stack.enter_context(patch.object(Path, 'read_text', autospec=True,
                side_effect=lambda path, **kwargs: json.dumps(saved_json[path])))
            stack.enter_context(patch.object(pipeline, 'read_rows', side_effect=lambda path: deepcopy(saved_rows[path])))
            stack.enter_context(patch.object(pipeline, 'sha', side_effect=lambda path: digest(saved_rows[path])))
            for name, value in [('ROOT', root), ('OUT', out), ('LOCAL', local)]:
                stack.enter_context(patch.object(pipeline, name, value))
            stack.enter_context(patch.object(pipeline, 'inventory', return_value=src))
            stack.enter_context(patch.object(pipeline, 'summary', return_value={'source_sha256': {}}))
            stack.enter_context(patch.object(pipeline, 'protected_pool', return_value=(set(), set(), {})))
            stack.enter_context(patch('sys.stdout', new_callable=io.StringIO))
            pipeline.validate()

    def test_valid_ledger_passes(self):
        self.fixture()

    def test_forged_source_group_not_silently_repaired(self):
        with self.assertRaisesRegex(ValueError, 'no longer eligible'):
            self.fixture(lambda rows, ledger: rows[0]['provenance'].update(source_group='forged-group'))

    def test_ledger_status_recomputed_even_when_digest_refreshed(self):
        with self.assertRaisesRegex(ValueError, 'Ledger state mismatch'):
            self.fixture(lambda rows, ledger: ledger[1].update(processing_status='financial_rewrite_candidate'))

    def test_ledger_source_text_recomputed_even_when_digest_refreshed(self):
        with self.assertRaisesRegex(ValueError, 'Ledger source changed'):
            self.fixture(lambda rows, ledger: ledger[1].update(source_message='伪造的原始文本'))

    def test_ledger_missing_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Ledger coverage mismatch'):
            self.fixture(lambda rows, ledger: ledger.pop())

    def test_ledger_digest_mismatch_fails_instead_of_printing_false(self):
        with self.assertRaisesRegex(ValueError, 'Manifest digest mismatch'):
            self.fixture(lambda rows, ledger: ledger[1].update(extra='edited'), refresh_hash=False)


if __name__ == '__main__':
    unittest.main()
