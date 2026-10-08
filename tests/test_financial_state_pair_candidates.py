import copy
import unittest

from qwenlab import financial_state_pair_candidates as c
from qwenlab.financial_serve_v2 import protocol


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.stories = c.read(c.STORIES)
        self.authored = c.author(self.stories)
        # These tests use saved actual-Node fixtures; CLI verify independently
        # replays the live adapter and detects stale fixture/source bytes.
        self.projected = [__import__('json').loads(line) for line in (c.DATA/'build/node-projections.jsonl').read_text(encoding='utf-8').splitlines()]
        self.spec = protocol()[0]

    def rows(self):
        return c.materialize(self.authored, self.projected, self.spec)

    def test_candidate_distribution_and_provenance(self):
        rows = self.rows()
        self.assertEqual(len(rows), 136)
        self.assertEqual(c.Counter(r['annotation']['action'] for r in rows), {'tool':40,'clarify':56,'human':24,'answer':16})
        self.assertTrue(all(r['split']=='candidate' and r['training_eligible'] is False and r['human_reviewed'] is False for r in rows))

    def test_strict_and_text_pairs_distinguished(self):
        pairs = c.pair_report(self.rows())
        self.assertEqual(sum(p['strict_single_field'] for p in pairs),88)
        self.assertEqual(sum(not p['strict_single_field'] for p in pairs),8)
        self.assertTrue(all(p['changed_fields']==['message','state.status_code'] for p in pairs if not p['strict_single_field']))

    def test_all_tools_authentication_required(self):
        rows = [r for r in self.rows() if r['variant']=='unauthenticated']
        self.assertEqual(len(rows),40)
        self.assertTrue(all(r['annotation']['action']=='clarify' and r['annotation']['tool_name'] is None for r in rows))

    def test_missing_projection_argument_fails(self):
        projected = copy.deepcopy(self.projected)
        next(r for r in projected if r['id']=='FIN-SP1-D01-ready')['input']['state'].pop('application_id')
        with self.assertRaisesRegex(ValueError,'Ungrounded'): c.materialize(self.authored,projected,self.spec)

    def test_changed_context_not_a_single_field_pair(self):
        rows = self.rows()
        next(r for r in rows if r['id']=='FIN-SP1-A01-unauthenticated')['input']['history'] = [{'role':'user','content':'额外的消息'}]
        with self.assertRaisesRegex(ValueError,'contrast'): c.pair_report(rows)

    def test_missing_auth_not_tool_gold(self):
        authored = copy.deepcopy(self.authored)
        row = next(r for r in authored if r['id']=='FIN-SP1-C01-unauthenticated')
        row.update(expected_action='tool',expected_tool='queryMyCreditScore')
        with self.assertRaisesRegex(ValueError,'Impossible tool'): c.materialize(authored,self.projected,self.spec)

    def test_tool_unavailable_does_not_always_mean_human(self):
        rows=self.rows()
        for row in rows:
            if row['variant']=='unavailable':
                expected='answer' if row['target_tool'] in ('queryLoanProducts','explainApplicationStatus') else 'human'
                self.assertEqual(row['annotation']['action'],expected)
        row=next(r for r in rows if r['id']=='FIN-SP1-P01-unavailable')
        row['annotation']['action']='human'
        with self.assertRaisesRegex(ValueError,'direction'): c.pair_report(rows)

    def test_identity_count_and_argument_types(self):
        with self.assertRaises(ValueError): c.author(self.stories[:-1])
        stories=copy.deepcopy(self.stories);stories[1]['id']=stories[0]['id']
        with self.assertRaises(ValueError): c.author(stories)
        stories=copy.deepcopy(self.stories);next(s for s in stories if s['id']=='D01')['application_id']=True
        with self.assertRaises(ValueError): c.author(stories)

    def test_projection_order_and_size_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'count'): c.materialize(self.authored,self.projected[:-1],self.spec)
        projected=self.projected[:]; projected[0],projected[1]=projected[1],projected[0]
        with self.assertRaisesRegex(ValueError,'identity'): c.materialize(self.authored,projected,self.spec)

    def test_json_types_are_distinct(self):
        self.assertEqual(c.differences({'a':False},{'a':0}),['a'])


if __name__=='__main__': unittest.main()
