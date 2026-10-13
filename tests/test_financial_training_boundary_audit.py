import unittest
from copy import deepcopy
from qwenlab import financial_training_boundary_audit as a


def row(name='a', action='tool'):
    return dict(id=name, scene_family_id='story', split='train', cohort='current-service',
        training_eligible=False,
        input=dict(message='查我的申请列表', history=[], state=dict(authenticated=True),
                   service_scope='loan_platform',capability_profile='current-node-no-kb',
                   capabilities=dict(knowledge_collections=[],handoff_available=False),
                   available_tools=['queryMyApplications','queryLoanProducts'],images=[]),
        annotation=dict(action=action,tool_name='queryMyApplications' if action=='tool' else None,
                        tool_arguments={},retrieval_collection=None,missing_slots=[]))


class AuditTests(unittest.TestCase):
    def test_order_not_distinct_input(self):
        x,y=row(),row('b');y['input']['available_tools'].reverse()
        result=a.analyze([x,y],[['a','b']])
        self.assertEqual(result['summary']['duplicate_extra_rows'],1)
        self.assertEqual(x['input']['available_tools'],['queryMyApplications','queryLoanProducts'])

    def test_same_visible_conflicting_action(self):
        result=a.analyze([row(),row('b','human')],[['a','b']])
        self.assertEqual(result['summary']['conflicting_trained_target_groups'],1)
        self.assertIsNotNone(result['summary']['strict_pair_check_error'])

    def test_auth_change_is_not_label_conflict(self):
        x,y=row(),row('b','clarify');y['input']['state']['authenticated']=False
        y['annotation']['missing_slots']=['authentication']
        s=a.analyze([x,y],[['a','b']])['summary']
        self.assertEqual(s['conflicting_trained_target_groups'],0)
        self.assertEqual(s['strict_pair_summary']['dimensions']['authentication']['matches_expected_boundary'],1)

    def test_unavailable_tool_and_auth_separate(self):
        r=row();r['input']['state']['authenticated']=False;r['input']['available_tools']=[]
        self.assertEqual(a.invariant_flags(r),['tool_without_authentication','tool_not_available'])

    def test_unavailable_retrieval(self):
        r=row(action='retrieve');r['annotation']['retrieval_collection']='loan_service_docs'
        self.assertEqual(a.invariant_flags(r),['retrieval_not_available'])

    def test_lexical_match_does_not_relabel(self):
        r=row(action='answer');r['input']['message']='他说“可以造假”，我拒绝了，这是诈骗吗？'
        original=deepcopy(r);s=a.analyze([r],[['a']])
        self.assertEqual(s['summary']['invariant_violations'],0)
        self.assertEqual(s['summary']['quoted_or_negated_topic_candidates']['actions'],{'answer':1})
        self.assertEqual(r,original)

    def test_refuse_nontrain(self):
        r=row();r['split']='development'
        with self.assertRaises(ValueError):a.analyze([r],[['a']])

    def test_refuse_unknown_schedule_row(self):
        with self.assertRaises(ValueError):a.analyze([row()],[['other']])

    def test_refuse_numeric_auth(self):
        r=row();r['input']['state']['authenticated']=1
        with self.assertRaises(ValueError):a.analyze([r],[['a']])


if __name__=='__main__':unittest.main()
