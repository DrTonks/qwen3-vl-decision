"""Synthetic fixtures only: this suite never opens historical datasets."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('expansion_overlap', ROOT / 'scripts/screen-financial-expansion-overlap.py')
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)
READER = {'message_path': ['message'], 'history_path': ['history'], 'missing_history': 'empty',
          'split_field': 'split', 'include_splits': ['final']}


class ExpansionOverlapTests(unittest.TestCase):
    def setUp(self):
        self.parent = ROOT / '.local/tests-expansion-overlap'
        self.root = self.parent / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def tearDown(self):
        resolved = self.root.resolve()
        if not resolved.is_relative_to(self.parent.resolve()) or resolved == self.parent.resolve():
            raise AssertionError('Unsafe test cleanup path')
        shutil.rmtree(resolved)

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return path

    def fixture(self):
        evidence = self.write('metadata.json', {'rows': 2})
        entries = []
        for role, split, message in [('heldout', 'final', '请查看申请94751的金额和期数'),
                                     ('training_pool', 'train', '我需要客服帮忙说明银行卡更换流程')]:
            path = self.write(role + '.json', [{'id': 'SECRET-OLD-ID', 'split': split, 'message': message,
                                               'labels': {'action': 'SECRET-OLD-LABEL'}, 'history': []}])
            reader = deepcopy(READER); reader['include_splits'] = [split]
            entries.append({'path': path.name, 'format': 'json_array', 'role': role, 'reader': reader,
                            'sha256': screen.digest(path.read_bytes()), 'file_rows': 1, 'selected_rows': 1,
                            'evidence': {'path': evidence.name, 'sha256': screen.digest(evidence.read_bytes())}})
        index = {'version': 'financial-supplement-heldout-index-v1', 'corpora': entries, 'evidence': [],
                 'counts': {role: {'entries': 1, 'selected_rows_with_snapshot_repetition': 1,
                                    'unique_file_sha256': 1} for role in screen.ROLES}}
        return self.write('index.json', index), index

    def candidate(self, id='NEW-1', group='NEW-G-1', message='请查看申请123的金额和期数', history=None):
        return {'id': id, 'scene_family_id': group, 'input': {'message': message, 'history': history or []}}

    def test_numeric_nfkc_normalization_and_short_exact(self):
        self.assertEqual(screen.normalized('Ａ１２３！'), screen.normalized('a98'))
        index = screen.LexicalIndex()
        index.add(screen.input_keys({'message': '7'}, READER))
        kinds = index.match(screen.input_keys({'message': '1'}, READER))
        self.assertIn('numeric_normalized_message_exact', kinds)

    def test_history_exact_preserves_role_order_and_turn_boundaries(self):
        row = {'message': '查这笔', 'history': [{'role': 'assistant', 'content': '申请321'}]}
        index = screen.LexicalIndex(); index.add(screen.input_keys(row, READER))
        query = deepcopy(row); query['history'][0]['content'] = '申请654'
        self.assertIn('numeric_normalized_message_history_exact', index.match(screen.input_keys(query, READER)))
        query['history'][0]['role'] = 'user'
        self.assertNotIn('numeric_normalized_message_history_exact', index.match(screen.input_keys(query, READER)))

    def test_near_jaccard_threshold_is_inclusive_and_no_shortcut_misses(self):
        index = screen.LexicalIndex()
        index.add(screen.input_keys({'message': 'abcdefghijklmnopqr'}, READER))
        self.assertTrue(index.near('abcdefghijklmnopqrstu', 0))  # 17 / 20 == .85
        self.assertFalse(index.near('abcdefghijklmnopqrstuv', 0))  # 17 / 21 < .85
        self.assertFalse(index.near('完全不同的汉字内容', 0))

    def test_end_to_end_only_new_ids_and_whole_group_quarantine(self):
        index_path, _ = self.fixture()
        candidates = [self.candidate(), self.candidate('NEW-2', 'NEW-G-1', '无人匹配的额外问题'),
                      self.candidate('NEW-3', 'NEW-G-2', '我需要客服帮忙说明银行卡更换流程')]
        path = self.write('candidates.json', candidates)
        result = screen.run_screen(path, self.root / 'report.json', index_path, self.root)
        self.assertEqual(result['hit_candidate_counts'], {'heldout': 1, 'training_pool': 1})
        self.assertEqual(result['quarantine_candidate_ids'], ['NEW-1', 'NEW-2', 'NEW-3'])
        self.assertEqual(result['quarantine_groups_by_reason'], {'heldout': ['NEW-G-1'], 'training_pool': ['NEW-G-2']})
        text = json.dumps(result, ensure_ascii=False)
        for secret in ['SECRET-OLD-ID', 'SECRET-OLD-LABEL', '94751', '请查看', '更换流程']:
            self.assertNotIn(secret, text)
        self.assertFalse(result['training_eligible']); self.assertFalse(result['semantic_overlap_guarantee'])
        with self.assertRaises(screen.ScreeningError):
            screen.run_screen(path, self.root / 'report.json', index_path, self.root)

    def test_changed_corpus_or_metadata_hash_fails_closed(self):
        _, index = self.fixture()
        self.write('heldout.json', [])
        with self.assertRaisesRegex(screen.ScreeningError, 'corpus hash changed'):
            screen.load_corpora(self.root, index)
        _, index = self.fixture()
        self.write('metadata.json', {'changed': True})
        with self.assertRaisesRegex(screen.ScreeningError, 'evidence hash changed'):
            screen.load_corpora(self.root, index)

    def test_split_rule_reads_only_selected_partition(self):
        _, index = self.fixture()
        rows = [{'split': 'final', 'message': '保护的咨询'}, {'split': 'train', 'message': '不属此分区的内容'}]
        path = self.write('heldout.json', rows)
        index['corpora'][0].update(sha256=screen.digest(path.read_bytes()), file_rows=2)
        indexes, _, _ = screen.load_corpora(self.root, index)
        self.assertIn(screen.normalized('保护的咨询'), indexes['heldout'].messages)
        self.assertNotIn(screen.normalized('不属此分区的内容'), indexes['heldout'].messages)

    def test_wrong_count_role_or_missing_coverage_is_rejected(self):
        _, index = self.fixture()
        changed = deepcopy(index); changed['corpora'][0]['selected_rows'] = 2
        with self.assertRaises(screen.ScreeningError): screen.load_corpora(self.root, changed)
        changed = deepcopy(index); changed['corpora'][0]['reader']['include_splits'] = ['train']
        with self.assertRaises(screen.ScreeningError): screen.load_corpora(self.root, changed)
        changed = deepcopy(index); changed['corpora'].pop()
        with self.assertRaises(screen.ScreeningError): screen.load_corpora(self.root, changed)

    def test_path_escape_and_unstructured_payload_are_rejected_without_echo(self):
        for path in ['../outside.json', 'C:/private.json', '/outside.json', 'folder\\file.json']:
            with self.assertRaises(screen.ScreeningError): screen.safe_path(self.root, path)
        with self.assertRaisesRegex(screen.ScreeningError, 'payload suppressed'):
            screen.json_data(b'{SECRET-CONTENT')
        with self.assertRaises(screen.ScreeningError): screen.load_rows(b'{}', 'json_array')

    def test_bad_candidate_identifiers_and_duplicates_rejected(self):
        indexes = {role: screen.LexicalIndex() for role in screen.ROLES}
        for rows in [[], [self.candidate(), self.candidate()], [self.candidate(id='unsafe ID')]]:
            with self.assertRaises(screen.ScreeningError): screen.screen_candidates(rows, indexes)


if __name__ == '__main__':
    unittest.main()
