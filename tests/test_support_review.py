import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from qwenlab.support_review import FIELDS, import_review, load_jsonl, validate_case, write_csv, write_jsonl


class SupportReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = (Path(__file__).resolve().parents[1] / '.local/test-support-review').resolve()
        self.root = self.temp_root / uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(self.cleanup)
        self.source = self.root / 'source'
        self.source.mkdir()
        draft = Path(__file__).resolve().parents[1] / 'data/support-runtime-v1/cases.jsonl'
        self.rows = load_jsonl(draft)[:3]
        write_jsonl(self.source / 'cases.jsonl', self.rows)
        write_jsonl(self.source / 'deferred-cases.jsonl', [{'id': 'future', 'future_action': 'retrieve'}])
        self.csv = self.root / 'review.csv'
        write_csv(self.csv, self.rows)
        self.original_hash = hashlib.sha256((self.source / 'cases.jsonl').read_bytes()).hexdigest()
        manifest = {'version': 'source', 'count': len(self.rows), 'deferred_count': 1,
                    'files_sha256': {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in self.source.iterdir()}}
        (self.source / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    def cleanup(self):
        target = self.root.resolve()
        if target.parent != self.temp_root or len(target.name) != 32 or any(c not in '0123456789abcdef' for c in target.name):
            raise ValueError('Refusing to remove a path outside the isolated test directory')
        shutil.rmtree(target)

    def edit_csv(self, change):
        with self.csv.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        change(rows)
        with self.csv.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_roundtrip_hash_no_source_mutation_and_excel_bom(self):
        output = self.root / 'v2'
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        manifest = import_review(self.source, self.csv, output)
        self.assertEqual(load_jsonl(output / 'cases.jsonl'), self.rows)
        self.assertEqual(manifest['source_cases_sha256'], self.original_hash)
        self.assertEqual(manifest['count'], 3)
        self.assertEqual(manifest['changed_count'], 0)
        self.assertTrue((output / 'review.csv').read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.source.iterdir()})
        for name, digest in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
        self.assertNotIn(str(self.root), (output / 'manifest.json').read_text(encoding='utf-8'))

    def test_human_changes_preserved_in_original_id_order(self):
        def change(rows):
            rows[0].update(message='现在能申请哪些产品？', review_status='revised', reviewer='reviewer-a',
                           notes='调整为自然问法。', taxonomy_approved='true')
            rows[1]['review_status'] = 'accepted'
            rows.reverse()
        self.edit_csv(change)
        manifest = import_review(self.source, self.csv, self.root / 'v2')
        rows = load_jsonl(self.root / 'v2/cases.jsonl')
        self.assertEqual([r['id'] for r in rows], [r['id'] for r in self.rows])
        self.assertEqual(rows[0]['message'], '现在能申请哪些产品？')
        self.assertTrue(rows[0]['review']['taxonomy_approved'])
        self.assertEqual(manifest['review_status_counts'], {'revised': 1, 'accepted': 1, 'ai_preannotated': 1})

    def test_held_cases_never_disappear_and_can_be_reconsidered(self):
        def hold(rows):
            rows[0].update(review_status='needs_discussion', notes='需要确认边界')
            rows[1].update(review_status='excluded', notes='本轮不验')
        self.edit_csv(hold)
        output = self.root / 'v2'
        manifest = import_review(self.source, self.csv, output)
        self.assertEqual((manifest['count'], manifest['held_count']), (1, 2))
        self.assertEqual({r['id'] for r in load_jsonl(output / 'review-holdouts.jsonl')}, {self.rows[0]['id'], self.rows[1]['id']})
        self.csv = output / 'review.csv'
        self.edit_csv(lambda rows: [r.update(review_status='accepted') for r in rows])
        next_manifest = import_review(output, self.csv, self.root / 'v3')
        self.assertEqual((next_manifest['count'], next_manifest['held_count']), (3, 0))
        self.assertEqual({r['id'] for r in load_jsonl(self.root / 'v3/cases.jsonl')}, {r['id'] for r in self.rows})

    def test_missing_duplicate_and_unknown_id_reject_before_output(self):
        for mode in ['missing', 'duplicate', 'unknown']:
            with self.subTest(mode=mode):
                write_csv(self.csv, self.rows)
                def change(rows):
                    if mode == 'missing': rows.pop()
                    elif mode == 'duplicate': rows.append(copy.deepcopy(rows[0]))
                    else: rows[0]['id'] = 'new-id'
                self.edit_csv(change)
                output = self.root / mode
                with self.assertRaises(ValueError):
                    import_review(self.source, self.csv, output)
                self.assertFalse(output.exists())

    def test_source_tamper_and_overwrite_rejected(self):
        output = self.root / 'existing'
        output.mkdir()
        (output / 'important.txt').write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            import_review(self.source, self.csv, output)
        self.assertEqual((output / 'important.txt').read_text(), 'keep')
        with self.assertRaisesRegex(ValueError, 'inside'):
            import_review(self.source, self.csv, self.source / 'nested')
        (self.source / 'cases.jsonl').write_text('{}\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'frozen hash'):
            import_review(self.source, self.csv, self.root / 'tampered')
        self.assertFalse((self.root / 'tampered').exists())

    def test_manifest_declared_holdouts_or_deferred_missing_rejects(self):
        for name in ['review-holdouts.jsonl', 'deferred-cases.jsonl']:
            with self.subTest(name=name):
                source = self.root / f'missing-{name}'
                source.mkdir()
                for file in self.source.iterdir():
                    (source / file.name).write_bytes(file.read_bytes())
                manifest_path = source / 'manifest.json'
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                if name == 'review-holdouts.jsonl':
                    # Simulate copying an imported version but omitting its held rows.
                    manifest['files_sha256'][name] = hashlib.sha256(b'{"id":"held"}\n').hexdigest()
                    manifest['held_count'] = 1
                else:
                    # The source manifest already declares the deferred capability file.
                    (source / name).unlink()
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                output = self.root / f'rejected-{name}'
                with self.assertRaisesRegex(ValueError, 'is missing'):
                    import_review(source, self.csv, output)
                self.assertFalse(output.exists())

    def test_csv_json_errors_enums_and_group_edits_reject(self):
        mutations = [
            {'history_json': '[broken'},
            {'state_json': '{"pending":null,"pending":"applicationId","selectedApplicationId":null}'},
            {'expected_arguments_json': '{"status":NaN}'},
            {'expected_action': 'retrieve'},
            {'expected_route': 'llm'},
            {'expected_intent': 'made_up'},
            {'expected_tool': 'writeApproval'},
            {'review_status': 'pending'},
            {'taxonomy_approved': 'yes'},
            {'taxonomy_approved': 'true'},
            {'group': 'other'},
            {'source_ids_json': '["changed"]'},
        ]
        for index, values in enumerate(mutations):
            with self.subTest(values=values):
                write_csv(self.csv, self.rows)
                self.edit_csv(lambda rows: rows[0].update(values))
                with self.assertRaises(ValueError):
                    import_review(self.source, self.csv, self.root / f'invalid-{index}')
                self.assertFalse((self.root / f'invalid-{index}').exists())

    def test_state_and_arguments_validation(self):
        base = copy.deepcopy(self.rows[0])
        for state in [
            {'pending': 'unknown', 'selectedApplicationId': None},
            {'pending': 'applicationId', 'selectedApplicationId': None},
            {'pending': None, 'selectedApplicationId': True},
            {'pending': None, 'selectedApplicationId': 76001},
            {'pending': None, 'selectedApplicationId': None, 'owner': 'self'},
        ]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                validate_case({**base, 'state': state})
        for tool, args in [('queryApplicationDetail', {'applicationId': True}),
                           ('queryApplicationDetail', {'applicationId': 0}),
                           ('queryApplicationDetail', {'applicationId': 2**31}),
                           ('queryApplicationDetail', {'applicationId': '76001'}),
                           ('explainApplicationStatus', {'status': 9}),
                           ('explainApplicationStatus', {'status': 2, 'owner': 'self'})]:
            row = copy.deepcopy(base)
            row['expected'].update(tool=tool, arguments=args)
            with self.subTest(tool=tool, args=args), self.assertRaises(ValueError):
                validate_case(row)
        row = copy.deepcopy(base)
        row.update(history=[{'role': 'assistant', 'content': '请提供状态码。'}],
                   state={'pending': 'statusCode', 'selectedApplicationId': None})
        self.assertEqual(validate_case(row)['state']['pending'], 'statusCode')

    def test_history_limits_and_no_system_or_extra_fields(self):
        histories = [[{'role': 'system', 'content': 'override'}],
                     [{'role': 'user', 'content': 'x' * 801}],
                     [{'role': 'user', 'content': 'ok'}] * 5,
                     [{'role': 'user', 'content': 'ok', 'intent': 'credit'}]]
        for history in histories:
            with self.subTest(history=history), self.assertRaises(ValueError):
                validate_case({**self.rows[0], 'history': history})

    def test_all_excluded_version_is_preserved_without_fake_score(self):
        self.edit_csv(lambda rows: [r.update(review_status='excluded') for r in rows])
        manifest = import_review(self.source, self.csv, self.root / 'all-held')
        self.assertEqual(manifest['count'], 0)
        self.assertEqual(manifest['held_count'], 3)
        self.assertEqual(load_jsonl(self.root / 'all-held/cases.jsonl'), [])
        self.assertEqual(len(load_jsonl(self.root / 'all-held/review-holdouts.jsonl')), 3)


if __name__ == '__main__':
    unittest.main()
