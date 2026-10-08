import copy
import unittest
from qwenlab.financial_boundary_release import select_reviewed


class BoundaryReleaseTests(unittest.TestCase):
    def examples(self):
        rows = [dict(id=str(i), scene_family_id=str(i // 3), split='train_candidate',
                     input={'message': str(i)}, annotation={'action': 'human'}) for i in range(6)]
        review = dict(candidate_sha256='bound', reviewer='separate-agent', reviewer_type='independent_ai_agent',
                      human_reviewed=False, records=[dict(id=str(i), verdict='accept', reason='read') for i in range(6)])
        return rows, review

    def test_one_disputed_row_excludes_whole_source_group(self):
        rows, review = self.examples()
        review['records'][1]['verdict'] = 'needs_discussion'
        before = copy.deepcopy(rows)
        selected, excluded = select_reviewed(rows, review, 'bound')
        self.assertEqual([r['id'] for r in selected], ['3', '4', '5'])
        self.assertEqual(excluded, {'0': ['1']})
        self.assertEqual(rows, before)
        self.assertTrue(all(r['split'] == 'train' and not r['review']['human_reviewed_current_version'] for r in selected))

    def test_rejects_wrong_hash_missing_or_duplicate_review_and_human_claim(self):
        for change in ['hash', 'missing', 'duplicate', 'human', 'identity']:
            rows, review = self.examples()
            if change == 'hash': review['candidate_sha256'] = 'other'
            if change == 'missing': review['records'].pop()
            if change == 'duplicate': review['records'].append(review['records'][0])
            if change == 'human': review['human_reviewed'] = True
            if change == 'identity': review['reviewer_type'] = 'author'
            with self.assertRaises(ValueError): select_reviewed(rows, review, 'bound')


if __name__ == '__main__':
    unittest.main()
