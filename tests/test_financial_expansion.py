from copy import deepcopy
import unittest
from qwenlab.financial_pilot import base_input, label, make
from qwenlab.financial_expansion import check, public_rows, PUBLIC_TOPICS


def example():
    r=make('unit','unit-family',base_input('请查询申请62417的明细',{'authenticated':True,'application_id':62417}),
        label('tool','已确认当前查询对象',tool='queryApplicationDetail',arguments={'applicationId':62417}),
        {'kind':'unit','source':'unit','parent_id':None,'source_split':None})
    r['id']='FIN-T2-unit'
    return r


class ExpansionTests(unittest.TestCase):
    def test_whole_id_not_substring(self):
        r=example();r['input']['message']='请查询申请624179的明细'
        with self.assertRaisesRegex(ValueError,'Whole application ID'):check([r],set())

    def test_current_explicit_id_overrides_old_context(self):
        r=example();r['input']['message']='请查询申请99999的明细'
        r['input']['history']=[{'role':'user','content':'此前查过62417'}]
        r['annotation']['evidence_paths'].append('input.history')
        with self.assertRaisesRegex(ValueError,'conflicts'):check([r],set())

    def test_number_without_application_prefix_overrides_history(self):
        r=example();r['input']['message']='这次改查编号624179的详情'
        r['input']['history']=[{'role':'user','content':'之前是申请62417'}]
        r['annotation']['evidence_paths'].append('input.history')
        with self.assertRaisesRegex(ValueError,'conflicts'):check([r],set())

    def test_boolean_is_not_integer_argument(self):
        r=example();r['input']=base_input('状态码0是什么意思',{'authenticated':True,'status_code':0})
        r['annotation']=label('tool','解释状态',tool='explainApplicationStatus',arguments={'status':False})
        with self.assertRaisesRegex(ValueError,'not bool'):check([r],set())

    def test_schema_types_rejected(self):
        mutations=[('missing_slots','application_id'),('reason',['reason']),('tool_arguments',[]),('evidence_paths','input.message')]
        for field,value in mutations:
            with self.subTest(field=field):
                r=example();r['annotation'][field]=value
                with self.assertRaises(ValueError):check([r],set())

    def test_unknown_slot_rejected(self):
        r=example();r['annotation']=label('clarify','需要补充',slots=['made_up_slot'])
        with self.assertRaisesRegex(ValueError,'missing slots'):check([r],set())

    def test_extra_annotation_field_rejected(self):
        r=example();r['annotation']['secret_label']='leak'
        with self.assertRaisesRegex(ValueError,'annotation fields'):check([r],set())

    def test_empty_family_rejected(self):
        r=example();r['scene_family_id']=' '
        with self.assertRaisesRegex(ValueError,'ID/family'):check([r],set())

    def test_valid_grounded_case(self):
        self.assertEqual(check([example()],set())['eligible_draft_candidates'],1)


if __name__=='__main__':unittest.main()
