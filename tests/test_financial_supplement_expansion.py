from copy import deepcopy
import unittest
from pathlib import Path
from unittest.mock import patch

from qwenlab import financial_supplement_expansion as e


def authored():
    return dict(id='SEA-G001-1',source_group='SEA-G001',cohort='current-service',input_layer='node-projection',
        context=dict(message='请实际查本人申请清单',authenticated=True,history=[],state={}),expected_action='tool',
        expected_tool='queryMyApplications',tool_arguments={},missing_slots=[],retrieval_collection=None,
        label_reason='明确查询本人最近申请，已有只读工具可用。')


class ExpansionTests(unittest.TestCase):
    def test_source_bounds_and_identity(self):
        a=authored();e.validate_authored([a])
        for mutation in [dict(id='DEV-001'),dict(source_group='wrong'),dict(input_layer='planned-capability-component'),
                         dict(label_reason='短'),dict(cohort='unknown'),dict(context={'authenticated':False})]:
            bad=deepcopy(a);bad.update(mutation)
            with self.assertRaises(ValueError):e.validate_authored([bad])
        with self.assertRaises(ValueError):e.validate_authored([a,a])
        oversized=[dict(a,id=f'SEA-G001-{n}') for n in range(1,6)]
        with self.assertRaises(ValueError):e.validate_authored(oversized)

    def test_file_set_cannot_skip_candidate_verification(self):
        with patch.object(e.pilot,'read',return_value={'files':{}}):
            with self.assertRaisesRegex(ValueError,'manifest'):e.verify('unused','unused')

    def test_whole_visible_input_controls_label_conflicts(self):
        value=dict(id='a',input={'message':'查记录','state':{'authenticated':True}},
            annotation=dict(action='tool',tool_name='queryMyApplications',tool_arguments={},retrieval_collection=None))
        other=deepcopy(value);other['id']='b';other['annotation']['action']='clarify';other['annotation']['tool_name']=None
        self.assertEqual(e.input_conflicts([value,other]),[['a','b']])
        other['input']['state']['authenticated']=False
        self.assertEqual(e.input_conflicts([value,other]),[])

    def test_build_does_not_overwrite(self):
        with self.assertRaises(FileExistsError):e.build([],'unused',e.ROOT)

    def test_authoring_paths_stay_in_new_dataset(self):
        with self.assertRaises(ValueError):e.source_rows([e.ROOT/'data/financial-service-v2/final.json'])


if __name__=='__main__':unittest.main()
