"""Synthetic release integrity checks; no dataset or heldout corpus is read."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import uuid


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/finalize-financial-expansion.py'
SPEC = importlib.util.spec_from_file_location('synthetic_expansion_release', SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)

CANDIDATE = 'synthetic-candidate-digest'
POLICY = 'synthetic-policy-digest'


def row(group='SEA-G001', variant=1, action='answer', visible=None):
    return {
        'id': f'{group}-{variant}',
        'scene_family_id': group,
        'input': deepcopy(visible) if visible is not None else {
            'message': f'合成情境 {group} 的第 {variant} 个请求',
            'history': [],
            'state': {'authenticated': True},
            'capabilities': {'available_tools': []},
        },
        'annotation': {'action': action},
        'provenance': {'source_row_sha256': f'synthetic-{group}-{variant}'},
    }


def decision(source, disposition='accept'):
    return {
        'id': source['id'],
        'source_row_sha256': source['provenance']['source_row_sha256'],
        'reviewed_action': source['annotation']['action'],
        'decision': disposition,
        'reason': 'Synthetic independent review of the full visible context.',
    }


def review(rows):
    return {
        'candidate_sha256': CANDIDATE,
        'policy_sha256': POLICY,
        'independent': True,
        'human_reviewed': False,
        'evaluation_data_read': False,
        'rows': [decision(r) for r in rows if not r['id'].startswith('FSP1-')],
    }


def screen(rows, heldout=(), training=()):
    blocked = set(heldout) | set(training)
    return {
        'quarantine_groups_by_reason': {
            'heldout': list(heldout), 'training_pool': list(training),
        },
        'quarantine_groups': sorted(blocked),
        'quarantine_candidate_ids': [
            r['id'] for r in rows if r['scene_family_id'] in blocked
        ],
    }


class IndependentReviewIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.protocol = patch.object(release.e.pilot, 'protocol', return_value=({}, POLICY))
        self.protocol.start()
        self.addCleanup(self.protocol.stop)
        # This inherited-looking row is synthetic too; it is never loaded from disk.
        self.rows = [row('FSP1-SYNTHETIC'), row(), row('SEA-G002', action='clarify')]
        self.valid = review(self.rows)

    def evaluate(self, reports):
        return release.reviewed_rows(self.rows, reports, CANDIDATE)

    def test_every_new_row_has_exactly_one_review_across_files(self):
        first, second = deepcopy(self.valid), deepcopy(self.valid)
        first['rows'] = first['rows'][:1]
        second['rows'] = second['rows'][1:]
        result = self.evaluate([first, second])
        self.assertEqual(set(result), {'SEA-G001-1', 'SEA-G002-1'})
        self.assertNotIn('FSP1-SYNTHETIC-1', result)

    def test_missing_review_cannot_release_an_unchecked_row(self):
        for records in ([], self.valid['rows'][:1]):
            with self.subTest(records=len(records)):
                bad = deepcopy(self.valid)
                bad['rows'] = records
                with self.assertRaises(ValueError):
                    self.evaluate([bad])

    def test_repeated_review_is_rejected_within_or_across_files(self):
        repeated = deepcopy(self.valid)
        repeated['rows'].append(deepcopy(repeated['rows'][0]))
        for reports in ([repeated], [self.valid, self.valid]):
            with self.subTest(files=len(reports)):
                with self.assertRaises(ValueError):
                    self.evaluate(reports)

    def test_review_cannot_substitute_an_unknown_or_inherited_row(self):
        for replacement in (row('SEA-G999'), self.rows[0]):
            with self.subTest(id=replacement['id']):
                bad = deepcopy(self.valid)
                bad['rows'][0] = decision(replacement)
                with self.assertRaises(ValueError):
                    self.evaluate([bad])

    def test_old_candidate_or_policy_binding_is_rejected(self):
        for field in ('candidate_sha256', 'policy_sha256'):
            with self.subTest(field=field):
                bad = deepcopy(self.valid)
                bad[field] = 'old-synthetic-digest'
                with self.assertRaises(ValueError):
                    self.evaluate([bad])

    def test_old_source_hash_or_old_reviewed_action_is_rejected(self):
        for field, value in (
            ('source_row_sha256', 'old-source-digest'), ('reviewed_action', 'human'),
        ):
            with self.subTest(field=field):
                bad = deepcopy(self.valid)
                bad['rows'][0][field] = value
                with self.assertRaises(ValueError):
                    self.evaluate([bad])

    def test_independence_claims_must_be_explicit_boolean_values(self):
        cases = {
            'independent': [False, None, 'true', 1],
            'human_reviewed': [True, None, 'false', 0],
            'evaluation_data_read': [True, None, 'false', 0],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    bad = deepcopy(self.valid)
                    bad[field] = value
                    with self.assertRaises(ValueError):
                        self.evaluate([bad])
            with self.subTest(field=field, missing=True):
                bad = deepcopy(self.valid)
                del bad[field]
                with self.assertRaises(ValueError):
                    self.evaluate([bad])

    def test_decisions_require_a_valid_disposition_and_nonempty_reason(self):
        for field, value in (
            ('decision', 'approve-without-review'), ('reason', ''),
            ('reason', ' \n '), ('reason', None), ('reason', 1),
        ):
            with self.subTest(field=field, value=value):
                bad = deepcopy(self.valid)
                bad['rows'][0][field] = value
                with self.assertRaises(ValueError):
                    self.evaluate([bad])


class WholeGroupReleaseTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row('SEA-G001', 1), row('SEA-G001', 2),
                     row('SEA-G002', 1), row('SEA-G002', 2), row('SEA-G003')]
        self.decisions = {r['id']: decision(r) for r in self.rows}

    def test_one_semantic_failure_quarantines_its_entire_source_group(self):
        for disposition in ('quarantine', 'revise'):
            with self.subTest(disposition=disposition):
                decisions = deepcopy(self.decisions)
                decisions['SEA-G001-2']['decision'] = disposition
                accepted, quarantined = release.split_groups(
                    self.rows, decisions, screen(self.rows))
                self.assertEqual({r['id'] for r in quarantined},
                                 {'SEA-G001-1', 'SEA-G001-2'})
                self.assertEqual({r['id'] for r in accepted},
                                 {'SEA-G002-1', 'SEA-G002-2', 'SEA-G003-1'})
                self.assertTrue(all('independent_label_review' in r['quarantine_reasons']
                                    for r in quarantined))

    def test_each_blind_screen_role_quarantines_the_whole_group(self):
        for role, tag in (('heldout', 'heldout_lexical_match'),
                          ('training', 'training_pool_duplicate')):
            with self.subTest(role=role):
                report = screen(self.rows, **{role: ['SEA-G002']})
                accepted, quarantined = release.split_groups(self.rows, self.decisions, report)
                self.assertEqual({r['id'] for r in quarantined},
                                 {'SEA-G002-1', 'SEA-G002-2'})
                self.assertTrue(all(tag in r['quarantine_reasons'] for r in quarantined))
                self.assertEqual(len(accepted), 3)

    def test_semantic_and_both_blind_reasons_are_preserved_together(self):
        self.decisions['SEA-G001-1']['decision'] = 'revise'
        report = screen(self.rows, heldout=['SEA-G001'], training=['SEA-G001'])
        _, quarantined = release.split_groups(self.rows, self.decisions, report)
        self.assertEqual(len(quarantined), 2)
        for r in quarantined:
            self.assertEqual(set(r['quarantine_reasons']),
                             {'heldout_lexical_match', 'training_pool_duplicate',
                              'independent_label_review'})

    def test_screen_cannot_drop_a_role_or_invent_an_unrecognized_role(self):
        for role, replace in (('heldout', False), ('training_pool', False), ('extra', True)):
            with self.subTest(role=role):
                report = screen(self.rows)
                if replace:
                    report['quarantine_groups_by_reason'][role] = []
                else:
                    del report['quarantine_groups_by_reason'][role]
                with self.assertRaises(ValueError):
                    release.split_groups(self.rows, self.decisions, report)

    def test_screen_union_must_exactly_identify_existing_groups(self):
        variants = []
        omitted = screen(self.rows, heldout=['SEA-G001'])
        omitted['quarantine_groups'] = []
        variants.append(omitted)
        invented = screen(self.rows)
        invented['quarantine_groups'] = ['SEA-G002']
        variants.append(invented)
        variants.append(screen(self.rows, heldout=['SEA-G999']))
        for report in variants:
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    release.split_groups(self.rows, self.decisions, report)

    def test_screen_ids_cannot_omit_a_sibling_or_add_an_unblocked_row(self):
        for replacement in (['SEA-G001-1'],
                            ['SEA-G001-1', 'SEA-G001-2', 'SEA-G002-1'],
                            ['SEA-G001-1', 'SEA-G001-2', 'SEA-G999-1']):
            with self.subTest(ids=replacement):
                report = screen(self.rows, heldout=['SEA-G001'])
                report['quarantine_candidate_ids'] = replacement
                with self.assertRaises(ValueError):
                    release.split_groups(self.rows, self.decisions, report)

    def test_cross_group_duplicate_keeps_earliest_group_and_blocks_later_siblings(self):
        first = row('FSP1-SYNTHETIC')
        duplicate = row('SEA-G002', visible=first['input'])
        # Dictionary serialization order is not a visible difference.
        duplicate['input'] = dict(reversed(list(duplicate['input'].items())))
        sibling = row('SEA-G002', 2)
        rows = [first, duplicate, sibling, row('SEA-G003')]
        original = deepcopy(rows)
        accepted, quarantined = release.split_groups(rows, {}, screen(rows))
        self.assertEqual([r['id'] for r in accepted], ['FSP1-SYNTHETIC-1', 'SEA-G003-1'])
        self.assertEqual([r['id'] for r in quarantined], ['SEA-G002-1', 'SEA-G002-2'])
        self.assertTrue(all(r['quarantine_reasons'] == ['internal_exact_input_duplicate']
                            for r in quarantined))
        self.assertEqual(rows, original)

    def test_same_message_with_different_visible_context_is_not_a_duplicate(self):
        first = row()
        modifications = [
            ('state', {'authenticated': False}),
            ('state', {'authenticated': True, 'application_id': 123}),
            ('history', [{'role': 'user', 'content': '合成的前一轮问题'}]),
            ('capabilities', {'available_tools': ['queryMyApplications']}),
        ]
        for field, value in modifications:
            with self.subTest(field=field, value=value):
                other = row('SEA-G002', visible=first['input'])
                other['input'][field] = value
                rows = [first, other]
                accepted, quarantined = release.split_groups(rows, {}, screen(rows))
                self.assertEqual(len(accepted), 2)
                self.assertEqual(quarantined, [])

    def test_repeated_input_within_one_source_group_is_not_cross_group_evidence(self):
        first = row()
        second = row(variant=2, visible=first['input'])
        accepted, quarantined = release.split_groups([first, second], {}, screen([]))
        self.assertEqual(len(accepted), 2)
        self.assertEqual(quarantined, [])

    def test_no_release_result_can_claim_training_or_human_approval(self):
        self.rows[0].update(training_eligible=True, human_reviewed=True)
        accepted, quarantined = release.split_groups(
            self.rows, self.decisions, screen(self.rows, heldout=['SEA-G002']))
        self.assertTrue(accepted and quarantined)
        for r in accepted + quarantined:
            self.assertIs(r['training_eligible'], False)
            self.assertIs(r['human_reviewed'], False)


class TokenReplayIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row()]
        self.measured = {
            'action': {'count': 1, 'max': 87, 'over_limit': 0},
            'tool': {'count': 1, 'max': 42, 'over_limit': 0},
        }
        self.audit = {
            'candidate_sha256': CANDIDATE,
            'status': 'structural_and_token_pass',
            'no_truncation': True,
            'tokens': deepcopy(self.measured),
        }

    def test_tokens_are_measured_again_instead_of_trusting_pass_metadata(self):
        with patch.object(release.e, 'token_stats', return_value=deepcopy(self.measured)) as measured:
            release.verify_tokens(self.rows, self.audit, CANDIDATE)
            measured.assert_called_once_with(self.rows)

    def test_stale_or_nonpassing_audit_is_rejected(self):
        for field, value in (('candidate_sha256', 'old-digest'), ('status', 'unchecked'),
                             ('no_truncation', False), ('no_truncation', 1)):
            with self.subTest(field=field, value=value):
                audit = deepcopy(self.audit)
                audit[field] = value
                with patch.object(release.e, 'token_stats', return_value=self.measured):
                    with self.assertRaises(ValueError):
                        release.verify_tokens(self.rows, audit, CANDIDATE)

    def test_action_and_tool_measurements_must_both_match_the_full_replay(self):
        variants = []
        for section in ('action', 'tool'):
            altered = deepcopy(self.audit)
            altered['tokens'][section]['max'] -= 1
            variants.append(altered)
            incomplete = deepcopy(self.audit)
            del incomplete['tokens'][section]
            variants.append(incomplete)
        extra = deepcopy(self.audit)
        extra['tokens']['unmeasured_claim'] = 'pass'
        variants.append(extra)
        for audit in variants:
            with self.subTest(tokens=audit['tokens']):
                with patch.object(release.e, 'token_stats', return_value=self.measured) as measured:
                    with self.assertRaises(ValueError):
                        release.verify_tokens(self.rows, audit, CANDIDATE)
                    measured.assert_called_once_with(self.rows)


class BlindReportReplayIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.root = (Path(__file__).resolve().parents[1] / '.local'
                     / f'synthetic-release-test-{uuid.uuid4().hex}')
        self.root.mkdir(parents=True)
        self.addCleanup(self.cleanup_synthetic_directories)
        self.build = self.root / 'synthetic-build'
        self.build.mkdir()
        self.fresh = {
            'candidate_sha256': CANDIDATE,
            'index_sha256': 'synthetic-index-digest',
            'script_sha256': 'synthetic-script-digest',
            'corpora': [{'path': 'synthetic/never-read.json', 'sha256': 'synthetic-corpus'}],
            'quarantine_groups_by_reason': {'heldout': ['SEA-G002'], 'training_pool': []},
            'quarantine_groups': ['SEA-G002'],
            'quarantine_candidate_ids': ['SEA-G002-1', 'SEA-G002-2'],
            'counts': {'checked': 4, 'quarantined': 2},
        }

    def cleanup_synthetic_directories(self):
        # Remove only this fixture's known empty directories; never recurse into
        # dataset files or unrelated .local work produced by another test.
        for relative in ('synthetic-build', '.local/expansion-screen-replay', '.local', '.'):
            directory = self.root / relative
            if directory.exists():
                directory.rmdir()

    def replay(self, saved, returncode=0):
        # No process runs and no corpus or real report is opened. Only the scratch
        # directory lifecycle is real, underneath this test's temporary root.
        with patch.object(release, 'ROOT', self.root), \
             patch.object(release, 'SCREENER', self.root / 'synthetic-screen.py'), \
             patch.object(release.subprocess, 'run', return_value=subprocess.CompletedProcess([], returncode)) as run, \
             patch.object(release.e.pilot, 'read', return_value=deepcopy(self.fresh)) as read:
            try:
                release.verify_screen(self.build, saved)
            finally:
                self.assertEqual(list((self.root / '.local/expansion-screen-replay').iterdir()), [])
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertIn(str((self.build / 'candidates.json').resolve()), command)
            if returncode == 0:
                read.assert_called_once()
                self.assertTrue(read.call_args.args[0].is_relative_to(self.root))

    def test_complete_replay_matches_regardless_of_dictionary_key_order(self):
        saved = dict(reversed(list(deepcopy(self.fresh).items())))
        self.replay(saved)

    def test_any_report_tampering_or_omission_is_rejected(self):
        variants = []
        for field in self.fresh:
            missing = deepcopy(self.fresh)
            del missing[field]
            variants.append((f'missing:{field}', missing))
        for field, value in (
            ('candidate_sha256', 'old-candidate'),
            ('quarantine_groups', []),
            ('quarantine_candidate_ids', ['SEA-G002-1']),
            ('counts', {'checked': 4, 'quarantined': 0}),
            ('corpora', [{'path': 'synthetic/never-read.json', 'sha256': 'changed'}]),
            ('quarantine_groups_by_reason', {'heldout': [], 'training_pool': ['SEA-G002']}),
        ):
            changed = deepcopy(self.fresh)
            changed[field] = value
            variants.append((f'changed:{field}', changed))
        extra = deepcopy(self.fresh)
        extra['unsupported_claim'] = 'everything-is-safe'
        variants.append(('extra', extra))
        for label, saved in variants:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.replay(saved)

    def test_failed_screen_process_never_approves_a_saved_report(self):
        with self.assertRaises(ValueError):
            self.replay(deepcopy(self.fresh), returncode=1)


if __name__ == '__main__':
    unittest.main()
