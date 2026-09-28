import copy
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
from uuid import uuid4
import unittest
from unittest.mock import patch

from qwenlab.common import ROOT
from qwenlab.support_challenge_catalog import cards as challenge_cards
from qwenlab.support_curriculum import (
    audit_candidates, build, build_rows, check, normalize_with_backend,
    coverage, same_decision, validate_structure, write_rows,
)


@contextmanager
def isolated_root():
    parent = (ROOT / '.local/test-support-curriculum').resolve()
    root = parent / uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        if root.resolve().parent != parent or not root.name.isalnum() or len(root.name) != 32:
            raise ValueError('Refusing cleanup outside isolated test root')
        shutil.rmtree(root)


class SupportCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_rows()
        cls.project = ROOT.parent / 'uestc_Integrated_Design'

    def test_context_pairs_remain_together_without_answer_metadata(self):
        grouped = {}
        for row in self.rows:
            grouped.setdefault(row['authored_utterance_id'], []).append(row)
            self.assertFalse(row['review']['taxonomy_approved'])
            self.assertEqual(set(row['state']), {'pending', 'selectedApplicationId'})
        for pair in grouped.values():
            self.assertEqual(len(pair), 2)
            self.assertEqual(pair[0]['split'], pair[1]['split'])
            self.assertEqual(pair[0]['expected'], pair[1]['expected'])
            self.assertEqual(len(pair[1]['history']), len(pair[0]['history']) + 2)

    def test_group_or_normalized_wording_cannot_cross_splits(self):
        changed = copy.deepcopy(self.rows)
        changed[0]['split'] = 'train'
        with self.assertRaisesRegex(ValueError, 'split'):
            validate_structure(changed)
        changed = copy.deepcopy(self.rows)
        other_split = next(r for r in changed if r['split'] != changed[0]['split'])
        other_split['message'] = changed[0]['message'] + '！！！'
        with self.assertRaisesRegex(ValueError, 'crosses split'):
            validate_structure(changed)

    def test_same_observable_input_cannot_have_conflicting_labels(self):
        rows = copy.deepcopy(self.rows[:1])
        other = copy.deepcopy(rows[0])
        other['id'] += '-conflict'
        other['expected'] = {'action': 'answer', 'route': 'llm', 'intent': 'general', 'tool': None, 'arguments': {}}
        rows.append(other)
        with self.assertRaisesRegex(ValueError, 'conflicting labels'):
            validate_structure(rows)

    def test_unavailable_state_cannot_be_smuggled_into_runtime_inputs(self):
        changed = copy.deepcopy(self.rows[:1])
        changed[0]['state']['ui_disabled_reason'] = '未实名认证'
        with self.assertRaises(ValueError):
            validate_structure(changed)

    def test_production_bridge_grounds_parameters_and_keeps_guard_attribution(self):
        if not self.project.is_dir():
            self.skipTest('Sibling application repository required for production bridge')
        rows = [next(r for r in self.rows if r['card_id'] == c and r['augmentation'] == 'base')
                for c in ['F05-A', 'F05-B', 'F06-A', 'F08-A', 'F12-A', 'F14-B', 'F20-A', 'F03-B']]
        observations = normalize_with_backend(self.project, rows)
        by_card = {r['card_id']: o for r, o in zip(rows, observations)}
        self.assertEqual(by_card['F05-A']['input']['state']['application_id'], 85011)
        self.assertNotIn('application_id', by_card['F05-B']['input']['state'])
        self.assertEqual(by_card['F06-A']['mapped']['arguments'], {'applicationId': 85013})
        self.assertEqual(by_card['F12-A']['mapped']['arguments'], {'status': 2})
        self.assertIsNone(by_card['F20-A']['guard'])
        self.assertEqual(by_card['F14-B']['guard']['action'], 'human')
        self.assertEqual(by_card['F03-B']['guard']['action'], 'refuse')
        for o in observations:
            self.assertEqual(set(o['input']), {'message', 'history', 'state', 'available_tools'})

    def test_holdouts_are_filtered_but_human_supervision_not_erased(self):
        wanted = ['F01-A', 'F11-B', 'F14-B', 'F03-B']
        rows = [next(r for r in self.rows if r['card_id'] == c) for c in wanted]
        observations = [{'id': r['id'], 'input': {'message': r['message']},
                         'mapped': r['expected'], 'guard': r['expected'] if r['expected']['action'] in {'human', 'refuse'} else None}
                        for r in rows]
        audit, candidates = audit_candidates(rows, observations, {'old-test': [{'message': rows[0]['message'] + '！'}]})
        self.assertEqual([r['id'] for r in candidates], [rows[2]['id']])
        self.assertEqual(candidates[0]['labels']['route'], 'human')
        self.assertEqual(candidates[0]['runtime_path'], 'guard')
        self.assertEqual(candidates[0]['usage'], 'offline_experiment_only')
        self.assertIn('seen_regression_utterance', audit[0]['held_reasons'])
        self.assertIn('outside_current_four_routes', audit[3]['held_reasons'])
        observations[2]['guard'] = {'action': 'refuse'}
        self.assertIn('guard_conflicts_with_proposed_action', audit_candidates(rows, observations, {})[0][2]['held_reasons'])

    def test_masked_input_collisions_and_cross_split_duplicates_fail_closed(self):
        rows = [copy.deepcopy(self.rows[0]), copy.deepcopy(self.rows[2])]
        rows[0]['message'], rows[1]['message'] = '查13800000001的数据', '查13900000002的数据'
        rows[1]['expected'] = {'action': 'tool', 'route': 'tool', 'intent': 'applications',
                               'tool': 'queryMyApplications', 'arguments': {}}
        observations = [{'id': r['id'], 'input': {'message': '查[手机号]的数据'}, 'mapped': r['expected'], 'guard': None}
                        for r in rows]
        with self.assertRaisesRegex(ValueError, 'conflicting labels'):
            audit_candidates(rows, observations, {})
        rows[1]['expected'] = copy.deepcopy(rows[0]['expected'])
        rows[1]['split'] = 'calibration'
        with self.assertRaisesRegex(ValueError, 'crosses splits'):
            audit_candidates(rows, observations, {})

    def test_absent_clarification_class_cannot_pass_readiness_check(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            coverage([{'split': 'train', 'labels': {'route': 'tool', 'tool': 'queryLoanProducts'}}])

    def test_generated_draft_refuses_overwrite_and_detects_tampering(self):
        if not self.project.is_dir():
            self.skipTest('Sibling application repository required for source snapshot')
        with isolated_root() as root:
            old = root / 'old.jsonl'
            write_rows(old, [{'message': 'unrelated regression wording'}])
            fake = [{'id': r['id'], 'input': {k: r[k] for k in ('message', 'history', 'state')},
                     'guard': None, 'mapped': r['expected']} for r in self.rows + build_rows(challenge_cards(), augment=False)]
            output = root / 'draft'
            with patch('qwenlab.support_curriculum.normalize_with_backend', return_value=fake):
                build(self.project, output, [old])
                self.assertEqual(check(output, self.project)['status'], 'passed')
                with self.assertRaises(FileExistsError):
                    build(self.project, output, [old])
            cases = output / 'cases.jsonl'
            cases.write_bytes(cases.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            self.assertEqual(check(output)['status'], 'passed')
            cases.write_text(cases.read_text(encoding='utf-8') + '\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'changed'):
                check(output)

    def test_missing_regression_source_fails_before_output_creation(self):
        if not self.project.is_dir():
            self.skipTest('Sibling application repository required for source snapshot')
        with isolated_root() as root:
            output = root / 'draft'
            with self.assertRaises(FileNotFoundError):
                build(self.project, output, [root / 'missing.jsonl'])
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
