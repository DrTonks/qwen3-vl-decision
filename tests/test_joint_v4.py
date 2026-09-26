import json
import unittest
from pathlib import Path
from unittest.mock import patch
from qwenlab.common import input_state
from qwenlab.joint_data import business_rows


class JointDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows=business_rows()

    def test_family_and_inputs_do_not_cross_splits(self):
        groups={}; inputs={}
        for r in self.rows:
            self.assertEqual(groups.setdefault(r['group'],r['split']),r['split'])
            state=json.dumps(input_state(r),ensure_ascii=False,sort_keys=True)
            self.assertEqual(inputs.setdefault(state,r['split']),r['split'])
        self.assertGreaterEqual(sum(r['split']=='train' for r in self.rows),2000)
        self.assertGreaterEqual(len({r['group'] for r in self.rows if r['split']=='test'}),50)

    def test_tool_and_human_contract(self):
        for r in self.rows:
            y=r['labels']
            self.assertEqual(y['needs_human']=='yes',y['route']=='human')
            self.assertEqual(y['route']=='tool',y['tool']!='none')
            if y['route']=='tool':
                self.assertIn(y['tool'],r['available_tools'])
                if y['tool']=='queryApplicationDetail': self.assertIsNotNone(r['state'].get('application_id'))

    def test_counterfactual_and_no_gold_in_input(self):
        r=next(r for r in self.rows if r['semantic_family']=='credit' and r['condition']=='live')
        peers=[x for x in self.rows if x['group']==r['group']]
        self.assertEqual({x['labels']['route'] for x in peers},{'tool','human','clarify','llm'})
        self.assertNotIn('condition',input_state(r))
        self.assertNotIn('labels',input_state(r))
        self.assertTrue(all(x['label_status']=='synthetic_unreviewed' for x in self.rows))


class JointSelectionTests(unittest.TestCase):
    def test_guardrails_reject_single_task_and_human_regression(self):
        from qwenlab.joint_v4 import select
        root=Path('virtual-test-results')
        fixtures={}
        candidates={'base':(.6,.6,.6,6,2),'better':(.7,.7,.7,7,2),
            'public_regression':(.5,.99,.99,10,0),'human_regression':(.9,.9,.9,9,3)}
        for name,(public,intent,route,tool,missed) in candidates.items():
            path=root/name
            business={'tasks':{'intent':{'accuracy':intent},'route':{'macro_f1_gold_supported_classes':route}},
                'joint_tool_correct':tool,'tool_required':10,'human_missed':missed}
            fixtures[path/'business-dev-metrics.json']=business
            fixtures[path/'massive-dev-metrics.json']={'tasks':{'intent':{'accuracy':public}}}
        with patch('qwenlab.joint_v4.OUT',root), patch('qwenlab.joint_v4.load_json',side_effect=fixtures.__getitem__), patch('qwenlab.joint_v4.dump') as saved_json:
            self.assertEqual(select(list(candidates)),'better')
        saved=saved_json.call_args.args[1]
        self.assertFalse(saved['selection']['public_regression']['guardrails_pass'])
        self.assertFalse(saved['selection']['human_regression']['guardrails_pass'])


if __name__=='__main__': unittest.main()
