import copy
import unittest
from qwenlab import financial_contract_audit as audit


class ContractAuditTests(unittest.TestCase):
    def row(self):
        return dict(id='train-only',split='train',input=dict(message='查我的申请',history=[],state={'authenticated':True},
            service_scope='loan_platform',capability_profile='current-no-kb-v1',capabilities={'knowledge_collections':[]},
            available_tools=['queryMyApplications'],images=[]),annotation=dict(action='tool',tool_name='queryMyApplications',tool_arguments={}))

    def test_heldout_row_is_rejected(self):
        row=self.row();row['split']='development'
        with self.assertRaises(ValueError):audit.assert_training(row)

    def test_state_contrast_not_mislabeled_as_exact_conflict(self):
        a=self.row();b=copy.deepcopy(a);b['id']='b';b['input']['state']['authenticated']=False
        b['annotation']={'action':'clarify','tool_name':None,'tool_arguments':{}}
        report=audit.summarize([{'row':a},{'row':b}])
        self.assertEqual(report['same_input_target_conflicts'],[])
        b['input']=copy.deepcopy(a['input'])
        report=audit.summarize([{'row':a},{'row':b}])
        self.assertEqual(len(report['same_input_target_conflicts']),1)

    def test_review_lead_never_changes_the_label(self):
        row=self.row();row['input']['message']='怎么联系人工客服？';row['annotation']['action']='answer';row['annotation']['tool_name']=None
        before=copy.deepcopy(row)
        self.assertIn('handoff_intent_vs_channel_information_review_only',audit.review_flags(row))
        self.assertEqual(row,before)


if __name__=='__main__':unittest.main()
