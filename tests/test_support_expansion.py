import copy
import csv
import json
import unittest
from xml.sax.saxutils import escape
import zipfile

from qwenlab.common import ROOT
from qwenlab import support_expansion as exp
from test_support_curriculum import isolated_root


class SupportExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = isolated_root()
        cls.root = cls.scope.__enter__()
        cls.project = ROOT.parent / 'uestc_Integrated_Design'
        cls.source = cls.root / 'source'
        cls.manifest = exp.build(cls.project, cls.source)
        cls.rows = exp.base.read_rows(cls.source / 'cases.jsonl')
        cls.review = json.loads((cls.source / 'review.json').read_text(encoding='utf-8'))['rows']
        cls.ids = {r['样本ID'] for r in cls.review}

    @classmethod
    def tearDownClass(cls):
        cls.scope.__exit__(None, None, None)

    def save_review(self, rows, name='review.csv'):
        path = self.root / name
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=exp.HEADERS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_expansion_exceeds_target_without_claiming_independent_users(self):
        self.assertGreaterEqual(self.manifest['eligible_train_count'], 3000)
        self.assertLess(self.manifest['unique_messages'], self.manifest['eligible_train_count'])
        self.assertGreaterEqual(self.manifest['scenario_groups'], 150)
        self.assertEqual(self.manifest['reviewed_eligible_count'], 0)
        self.assertFalse(self.manifest['training_started'])
        self.assertTrue(all(r['split'] == 'train' for r in self.rows))
        exp.check_frozen(self.source)

    def test_holdouts_are_byte_identical(self):
        for name in exp.EVAL_FILES:
            self.assertEqual((self.source / name).read_bytes(), (ROOT / 'data/support-curriculum-v1' / name).read_bytes())

    def test_sorted_review_preserves_ids_and_missing_rows_are_rejected(self):
        rows, _ = exp.apply_edits(self.rows, list(reversed(self.review)), self.ids, '')
        self.assertEqual([r['id'] for r in rows], [r['id'] for r in self.rows])
        with self.assertRaisesRegex(ValueError, 'ID set'):
            exp.apply_edits(self.rows, self.review[:-1], self.ids, '')
        duplicated = self.review[:-1] + [self.review[0]]
        with self.assertRaisesRegex(ValueError, 'ID set'):
            exp.apply_edits(self.rows, duplicated, self.ids, '')

    def test_edits_require_explicit_status_and_reviewer(self):
        values = copy.deepcopy(self.review)
        values[0]['当前问题'] += ' 麻烦了。'
        with self.assertRaisesRegex(ValueError, 'Edited rows'):
            exp.apply_edits(self.rows, values, self.ids, 'reviewer')
        values[0]['复核状态'] = '已修改'
        with self.assertRaisesRegex(ValueError, 'reviewer'):
            exp.apply_edits(self.rows, values, self.ids, '')
        rows, changes = exp.apply_edits(self.rows, values, self.ids, 'reviewer')
        self.assertEqual(len(changes), 1)
        revised = next(r for r in rows if r['id'] == values[0]['样本ID'])
        self.assertEqual(revised['review']['status'], 'revised')
        self.assertFalse(revised['review']['taxonomy_approved'])

    def test_partial_review_can_resume_held_rows_in_next_version(self):
        values = copy.deepcopy(self.review)
        values[0]['复核状态'] = '通过'
        values[1]['复核状态'] = '待定'
        values[2]['复核状态'] = '排除'
        out = self.root / 'reviewed-01'
        result = exp.import_review(self.project, self.source, self.save_review(values), out, 'reviewer')
        self.assertEqual(result['reviewed_eligible_count'], 1)
        self.assertFalse(result['provenance']['human_review_completed'])
        self.assertEqual(result['eligible_train_count'], self.manifest['eligible_train_count'] - 2)
        resumed = json.loads((out / 'review.json').read_text(encoding='utf-8'))['rows']
        self.assertEqual({r['样本ID'] for r in resumed}, self.ids)
        for row in resumed:
            if row['复核状态'] in ('待定', '排除'):
                row['复核状态'] = '通过'
        result2 = exp.import_review(self.project, out, self.save_review(resumed, 'resume.csv'), self.root / 'reviewed-02', 'reviewer')
        self.assertEqual(result2['reviewed_eligible_count'], 3)
        self.assertEqual(result2['eligible_train_count'], self.manifest['eligible_train_count'])
        self.assertEqual(len(exp.base.read_rows(out / 'train-reviewed-only.jsonl')), 1)

    def test_changed_tool_arguments_must_ground_to_actual_input(self):
        values = copy.deepcopy(self.review)
        row = next(r for r in values if r['工具'] == 'queryApplicationDetail')
        row['参数JSON'] = '{"applicationId":123456}'
        row['复核状态'] = '已修改'
        out = self.root / 'bad-args'
        with self.assertRaisesRegex(ValueError, 'fail validation'):
            exp.import_review(self.project, self.source, self.save_review(values), out, 'reviewer')
        self.assertFalse(out.exists())

    def test_completed_candidate_review_never_implies_training_authorization(self):
        values = copy.deepcopy(self.review)
        for row in values:
            row['复核状态'] = '通过'
        out = self.root / 'all-reviewed'
        result = exp.import_review(self.project, self.source, self.save_review(values), out, 'reviewer')
        self.assertEqual(result['status'], 'reviewed_candidates_awaiting_training_authorization')
        self.assertTrue(result['provenance']['human_review_completed'])
        self.assertEqual(result['reviewed_eligible_count'], self.manifest['eligible_train_count'])
        self.assertFalse(result['training_started'])
        self.assertFalse(result['training_authorized'])

    def test_unchanged_review_keeps_original_reviewer(self):
        values = copy.deepcopy(self.review)
        values[0]['复核状态'] = '通过'
        first, _ = exp.apply_edits(self.rows, values, self.ids, 'reviewer-a')
        next_values = [exp.review_row(r) for r in first if r['id'] in self.ids]
        second, changes = exp.apply_edits(first, next_values, self.ids, 'reviewer-b')
        self.assertEqual(changes, [])
        kept = next(r for r in second if r['id'] == values[0]['样本ID'])
        self.assertEqual(kept['review']['reviewer'], 'reviewer-a')

    def test_edited_question_cannot_enter_heldout_split(self):
        values = copy.deepcopy(self.review)
        values[0]['当前问题'] = exp.heldout_rows(self.source)[0]['message']
        values[0]['复核状态'] = '已修改'
        with self.assertRaisesRegex(ValueError, 'crosses split'):
            exp.import_review(self.project, self.source, self.save_review(values), self.root / 'bad-leak', 'reviewer')

    def test_exclusion_removes_conflict_but_retains_audit(self):
        values = copy.deepcopy(self.review)
        values[0]['当前问题'] = exp.heldout_rows(self.source)[0]['message']
        values[0]['复核状态'] = '排除'
        out = self.root / 'excluded-leak'
        exp.import_review(self.project, self.source, self.save_review(values), out, 'reviewer')
        self.assertNotIn(values[0]['样本ID'], {r['id'] for r in exp.base.read_rows(out / 'train-candidates.jsonl')})
        held = next(r for r in exp.base.read_rows(out / 'eligibility.jsonl') if r['id'] == values[0]['样本ID'])
        self.assertIn('review:excluded', held['held_reasons'])

    def test_empty_intent_cannot_be_approved_for_training(self):
        values = copy.deepcopy(self.review)
        values[0]['意图'] = ''
        values[0]['复核状态'] = '已修改'
        with self.assertRaisesRegex(ValueError, 'missing_intent_label'):
            exp.import_review(self.project, self.source, self.save_review(values), self.root / 'bad-intent', 'reviewer')

    def test_frozen_manifest_and_no_overwrite(self):
        missing = self.root / 'missing'
        missing.mkdir()
        (missing / 'manifest.json').write_text(json.dumps({'files_sha256': {}}))
        with self.assertRaisesRegex(ValueError, 'Incomplete manifest'):
            exp.check_frozen(missing)
        with self.assertRaises(FileExistsError):
            exp.import_review(self.project, self.source, self.save_review(self.review), self.source, '')
        exp.check_frozen(self.source)

    def test_xlsx_values_and_formula_rejection(self):
        main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        rels = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        path = self.root / 'minimal.xlsx'
        data = [exp.HEADERS, [str(self.review[0][h]) for h in exp.HEADERS]]
        def create(formula=False):
            body = ''.join('<row>' + ''.join(
                f'<c r="{chr(65+i)}{n}" t="inlineStr"><is><t>{escape(v)}</t></is>'
                + ('<f>1+1</f>' if formula and i == 0 and n == 2 else '') + '</c>'
                for i, v in enumerate(row)) + '</row>' for n, row in enumerate(data, 1))
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('xl/workbook.xml', f'<workbook xmlns="{main}" xmlns:r="{rels}"><sheets><sheet name="训练复核" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{main}"><sheetData>{body}</sheetData></worksheet>')
        create()
        self.assertEqual(exp.read_xlsx(path)[0]['样本ID'], self.review[0]['样本ID'])
        create(True)
        with self.assertRaisesRegex(ValueError, 'not formulas'):
            exp.read_xlsx(path)


if __name__ == '__main__':
    unittest.main()
