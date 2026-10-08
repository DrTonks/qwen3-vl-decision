"""Release safety tests with retained, small, ignored workspace fixtures."""
from copy import deepcopy
import json
import unittest
import uuid
from unittest.mock import patch

from qwenlab.common import ROOT, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows
import qwenlab.financial_release as release
from qwenlab.financial_release_core import rows as core_rows
from qwenlab.financial_pilot import visible_input


def candidate(index=0):
    row = deepcopy(core_rows()[index])
    row['curation'] = dict(origin='new_authored_boundary', original_id=row['id'],
                           independently_read=True, human_review=False)
    return row


def fixture(row=None):
    folder = ROOT / '.local/test-financial-release' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    source = row or candidate()
    release.attach_groups([source])
    exported = deepcopy(source)
    exported.update(split='train', usage='training_release_agent_reviewed')
    exported['review'].update(status='independent_agent_review_pass',
                              semantic_review='individually_read')
    release.write_lf(folder/'parts/part-0001.jsonl', [exported])
    release.write_lf(folder/'selection-ledger.jsonl', [])
    atomic_json(folder/'groups.json', {source['id']: dict(source_family=source['scene_family_id'],
        partition_group=source['curation']['partition_group'], selected=True)})
    review_path = folder/'reviews/core-review.json'
    atomic_json(review_path, dict(decision='pass', human_review=False, unresolved_findings=[], reviewer='independent',
                                  reviewed_ids=[source['id']]))
    evidence = dict(id=source['id'], source_id=source['id'], review_kind='addition',
        reviewer='independent', review_file='reviews/core-review.json',
        source_review_path=review_path.relative_to(ROOT).as_posix(), human_review=False,
        content_sha256=release.digest({k: source[k] for k in release.CONTENT_FIELDS}))
    release.write_lf(folder/'review-evidence.jsonl', [evidence])
    manifest = dict(purpose='training_only', human_review=False, independent_evaluation_ready=False,
                    action_tokens=release.LETTERS, stats=release.summarize([exported]),
                    source_bindings={review_path.relative_to(ROOT).as_posix(): sha(review_path)}, files={})
    for name in ['parts/part-0001.jsonl', 'selection-ledger.jsonl', 'groups.json',
                 'review-evidence.jsonl', 'reviews/core-review.json']:
        manifest['files'][name] = dict(sha256=sha(folder/name))
        if name.endswith('.jsonl'):
            manifest['files'][name]['rows'] = len(read_rows(folder/name))
    atomic_json(folder/'manifest.json', manifest)
    return folder, source, exported, manifest


class ReleaseTests(unittest.TestCase):
    def test_same_input_different_executable_targets_is_rejected(self):
        a, b = candidate(111), candidate(111)
        b['id'] += '-other'
        b['annotation']['tool_name'] = 'queryMyApplications'
        b['annotation']['tool_arguments'] = {}
        with self.assertRaisesRegex(ValueError, 'Conflicting identical input'):
            release.curate([a, b], [])

    def test_group_connection_survives_duplicate_from_other_family(self):
        a, duplicate, sibling = candidate(), candidate(), candidate(2)
        duplicate['id'] += '-duplicate'
        duplicate['scene_family_id'] = sibling['scene_family_id']
        release.attach_groups([a, duplicate, sibling])
        chosen, _ = release.curate([a, duplicate, sibling], [])
        self.assertEqual(len(chosen), 2)
        self.assertEqual(a['curation']['partition_group'], sibling['curation']['partition_group'])

    def test_authentication_and_tool_availability_contrasts_are_kept(self):
        auth = [candidate(110), candidate(111)]
        capability = [candidate(180), candidate(181)]
        selected, _ = release.curate(auth + capability, [])
        self.assertEqual(len(selected), 4)
        self.assertEqual({r['annotation']['action'] for r in selected}, {'clarify', 'tool', 'human'})

    def test_numeric_pattern_dedup_has_retained_id(self):
        a, b = candidate(71), candidate(71)
        b['id'] += '-amount'
        number = b['input']['state']['application_id']
        b['input']['state']['application_id'] += 100
        b['input']['history'][0]['content'] = b['input']['history'][0]['content'].replace(str(number), str(number+100))
        b['annotation']['tool_arguments']['applicationId'] += 100
        ledger = []
        selected, _ = release.curate([a, b], ledger)
        self.assertEqual(len(selected), 1)
        self.assertEqual(ledger[0]['reason'], 'lexical_variable_pattern')
        self.assertEqual(ledger[0]['retained_id'], a['id'])

    def test_independent_review_requires_all_ids_bound_to_current_hash(self):
        folder = ROOT / '.local/test-financial-release' / uuid.uuid4().hex
        path = folder/'additions/core.jsonl'
        release.write_lf(path, [candidate()])
        report = dict(decision='pass', unresolved_findings=[], human_review=False,
                      reviewer='independent', reviewed_ids=[], data_sha256=sha(path))
        atomic_json(folder/'review/core-review.json', report)
        with patch.object(release, 'LOCAL', folder):
            with self.assertRaisesRegex(ValueError, 'full independent ID coverage'):
                release.addition_review(path)
            report['reviewed_ids'] = [candidate()['id']]
            report['reviewer'] = 'root'
            atomic_json(folder/'review/core-review.json', report)
            with self.assertRaisesRegex(ValueError, 'own addition'):
                release.addition_review(path)
            report['reviewer'] = 'independent'
            atomic_json(folder/'review/core-review.json', report)
            self.assertEqual(len(release.addition_review(path)[0]), 1)
            path.write_text(path.read_text(encoding='utf-8')+'\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                release.addition_review(path)

    def test_portable_integrity_rejects_changed_or_extra_file(self):
        folder, _, _, _ = fixture()
        self.assertEqual(release.validate(folder)['rows'], 1)
        (folder/'untracked.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unexpected or missing'):
            release.validate(folder)
        second, _, _, _ = fixture()
        p = second/'parts/part-0001.jsonl'
        p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(ValueError, 'Artifact changed'):
            release.validate(second)

    def test_resigned_manifest_cannot_hide_changed_original_from_local_validation(self):
        folder, source, exported, manifest = fixture()
        # Portable hashes are self-consistency, not a signature of authenticity.
        exported['input']['message'] += ' 请不要猜测。'
        release.write_lf(folder/'parts/part-0001.jsonl', [exported])
        manifest['files']['parts/part-0001.jsonl']['sha256'] = sha(folder/'parts/part-0001.jsonl')
        evidence = read_rows(folder/'review-evidence.jsonl')
        evidence[0]['content_sha256'] = release.digest({k: exported[k] for k in release.CONTENT_FIELDS})
        release.write_lf(folder/'review-evidence.jsonl', evidence)
        manifest['files']['review-evidence.jsonl']['sha256'] = sha(folder/'review-evidence.jsonl')
        atomic_json(folder/'manifest.json', manifest)
        self.assertEqual(release.validate(folder)['rows'], 1)
        with patch.object(release, 'load_baseline', return_value=([source], [], {}, set(), 1)), \
             patch.object(release, 'load_additions', return_value=([], {})):
            with self.assertRaisesRegex(ValueError, 'differs from reviewed original'):
                release.validate(folder, verify_local=True)

    def test_adapter_does_not_encode_labels_provenance_or_reasons(self):
        folder, _, exported, _ = fixture()
        encoded = next(release.training_rows(folder))
        self.assertEqual(json.loads(encoded['input']), visible_input(exported))
        self.assertNotIn('annotation', json.loads(encoded['input']))
        self.assertNotIn(exported['annotation']['reason'], encoded['input'])
        self.assertNotIn('producer', encoded['input'])
        self.assertEqual(encoded['action_token'], 'A')

    def test_review_evidence_cannot_claim_unread_id(self):
        folder, source, _, manifest = fixture()
        path = folder/'reviews/core-review.json'
        report = json.loads(path.read_text(encoding='utf-8'))
        report['reviewed_ids'] = ['a-different-case']
        atomic_json(path, report)
        manifest['files']['reviews/core-review.json']['sha256'] = sha(path)
        manifest['source_bindings'][path.relative_to(ROOT).as_posix()] = sha(path)
        atomic_json(folder/'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'Invalid independent review evidence'):
            release.validate(folder)

    def test_review_evidence_rejects_unknown_kind_and_unresolved_report(self):
        folder, _, _, manifest = fixture()
        evidence = read_rows(folder/'review-evidence.jsonl')
        evidence[0]['review_kind'] = 'unknown'
        release.write_lf(folder/'review-evidence.jsonl', evidence)
        manifest['files']['review-evidence.jsonl']['sha256'] = sha(folder/'review-evidence.jsonl')
        atomic_json(folder/'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'Unknown review evidence kind'):
            release.validate(folder)
        other, _, _, meta = fixture()
        p = other/'reviews/core-review.json'
        report = json.loads(p.read_text(encoding='utf-8'))
        report['unresolved_findings'] = ['unfixed ambiguity']
        atomic_json(p, report)
        meta['files']['reviews/core-review.json']['sha256'] = sha(p)
        meta['source_bindings'][p.relative_to(ROOT).as_posix()] = sha(p)
        atomic_json(other/'manifest.json', meta)
        with self.assertRaisesRegex(ValueError, 'Invalid independent review evidence'):
            release.validate(other)

    def test_review_copy_refuses_overwrite_and_keeps_edits_candidate_only(self):
        folder, _, _, _ = fixture()
        local = folder.parent/(folder.name+'-local')
        with patch.object(release, 'OUT', folder), patch.object(release, 'LOCAL', local), \
             patch.object(release, 'completion_protection', return_value=set()):
            release.review_copy()
            with self.assertRaisesRegex(FileExistsError, 'keep existing edits'):
                release.review_copy()
            path = local/'human-review/cases.jsonl'
            editable = read_rows(path)
            self.assertEqual(editable[0]['split'], 'train_candidate')
            self.assertIs(editable[0]['curation']['independently_read'], False)
            editable[0]['annotation']['reason'] += ' 经复核，确实缺少原文。'
            release.write_lf(path, editable)
            self.assertEqual(release.check_review_copy()['changed'], 1)
            editable[0]['provenance']['origin'] = 'human'
            release.write_lf(path, editable)
            with self.assertRaisesRegex(ValueError, 'Edit only input and annotation'):
                release.check_review_copy()

    def test_current_version_human_review_cannot_be_asserted(self):
        folder, _, exported, manifest = fixture()
        exported['review']['human_reviewed_current_version'] = True
        release.write_lf(folder/'parts/part-0001.jsonl', [exported])
        manifest['files']['parts/part-0001.jsonl']['sha256'] = sha(folder/'parts/part-0001.jsonl')
        atomic_json(folder/'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'False human-review'):
            release.validate(folder)


if __name__ == '__main__':
    unittest.main()
