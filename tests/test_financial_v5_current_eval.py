import unittest
from copy import deepcopy
from qwenlab.financial_v5_current_eval import project_native, native_summary


def row(name='a',action='tool',auth=True):
    return dict(id=name,input=dict(message='查询我的申请',history=[],
        state=dict(authenticated=auth,handoff_status='none'),available_tools=['queryMyApplications'],
        capabilities=dict(knowledge_collections=[],handoff_available=False),
        service_scope='loan_platform',capability_profile='current-node-no-kb',images=[]),
        annotation=dict(action=action,tool_name='queryMyApplications' if action=='tool' else None))


class EvalTests(unittest.TestCase):
    def test_projection_preserves_query(self):
        r=row();original=deepcopy(r);v=project_native(r)
        self.assertEqual(v['message'],r['input']['message'])
        self.assertEqual(v['available_tools'],r['input']['available_tools'])
        self.assertNotIn('handoff_status',v['state']);self.assertEqual(r,original)

    def test_no_fabricated_login(self):
        self.assertIsNone(project_native(row(auth=False)))

    def test_unsupported_actions_separate(self):
        rows=[row(),row('b','refuse'),row('c','clarify',False)]
        preds=[dict(id='a',action='tool',tool_name='queryMyApplications',elapsed_s=.1),
               dict(id='b',action='human',tool_name=None,elapsed_s=.2)]
        s=native_summary(rows,preds)
        self.assertEqual(s['all_accepted']['action_correct'],1)
        self.assertEqual(s['all_accepted']['rows'],2)
        self.assertEqual(s['common_four_actions']['rows'],1)
        self.assertEqual(s['unexpressible_labels'],{'refuse':1})
        self.assertEqual(s['rejected_input_rows'],1)

    def test_missing_prediction_rejected(self):
        with self.assertRaises(ValueError):native_summary([row()],[])

    def test_duplicate_prediction_rejected(self):
        p=dict(id='a',action='tool',tool_name='queryMyApplications',elapsed_s=.1)
        with self.assertRaises(ValueError):native_summary([row()],[p,p])


if __name__=='__main__':unittest.main()
