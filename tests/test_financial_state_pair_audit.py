from copy import deepcopy
import unittest
from qwenlab.financial_state_pair_audit import audit,capacity,differences


def row(rid,auth=True,action='tool'):
    return dict(id=rid,scene_family_id='g1',split='train',training_eligible=False,
        cohort='current-service' if auth else 'preauth-robustness',
        input=dict(message='查看本人的申请列表',history=[],state=dict(authenticated=auth),
            capabilities=dict(knowledge_collections=[]),available_tools=['queryMyApplications','queryLoanProducts']),
        annotation=dict(action=action,tool_name='queryMyApplications' if action=='tool' else None,
            tool_arguments={},retrieval_collection=None,missing_slots=['authentication'] if action=='clarify' else []))


class StatePairAuditTests(unittest.TestCase):
    def test_auth_pair_and_exposure_are_actual_both_sides(self):
        rows=[row('a'),row('b',False,'clarify')];old=deepcopy(rows)
        pairs,_,summary=audit(rows,{'one':[['a','a']],'both':[['a','b']]})
        self.assertEqual(summary['strict_single_field_pairs'],1)
        self.assertTrue(pairs[0]['matches_expected_boundary'])
        self.assertFalse(pairs[0]['exposure']['one']['both'])
        self.assertTrue(pairs[0]['exposure']['both']['both'])
        self.assertEqual(rows,old)

    def test_same_message_different_history_is_not_controlled_pair(self):
        a,b=row('a'),row('b',False,'clarify');b['input']['history']=[{'role':'user','content':'different'}]
        self.assertEqual(audit([a,b],{})[0],[])

    def test_same_surface_different_story_does_not_merge(self):
        a,b=row('a'),row('b',False,'clarify');b['scene_family_id']='g2'
        self.assertEqual(audit([a,b],{})[0],[])

    def test_two_fields_are_confounded_not_auth_only(self):
        a,b=row('a'),row('b',False,'clarify');b['input']['available_tools']=[]
        pairs,coupled,_=audit([a,b],{})
        self.assertFalse(pairs);self.assertEqual(len(coupled[0]['changed_fields']),2)

    def test_unordered_tool_list_is_normalized_without_changing_input(self):
        a,b=row('a'),row('b',False,'clarify');b['input']['available_tools'].reverse()
        pairs,_,_=audit([a,b],{})
        self.assertEqual(pairs[0]['changed_fields'],['state.authenticated'])

    def test_auth_direction_is_not_inferred_from_action_set_alone(self):
        pairs,_,_=audit([row('a',True,'clarify'),row('b',False,'tool')],{})
        self.assertFalse(pairs[0]['matches_expected_boundary'])

    def test_missing_requested_tool_required_for_availability_boundary(self):
        a,b=row('a'),row('b',True,'human');b['input']['available_tools']=['queryMyApplications']
        self.assertFalse(audit([a,b],{})[0][0]['matches_expected_boundary'])
        b['input']['available_tools']=['queryLoanProducts']
        self.assertTrue(audit([a,b],{})[0][0]['matches_expected_boundary'])

    def test_training_split_id_auth_and_schedule_boundaries(self):
        for field,value in [('split','development'),('training_eligible',True)]:
            a=row('a');a[field]=value
            with self.assertRaises(ValueError):audit([a],{})
        for auth in ('false',0,1):
            a=row('a');a['input']['state']['authenticated']=auth
            with self.assertRaises(ValueError):audit([a],{})
        with self.assertRaises(ValueError):audit([row('a'),row('a')],{})
        with self.assertRaises(ValueError):audit([row('a')],{'bad':[['unknown']]})

    def test_identical_input_conflicting_target_fails(self):
        with self.assertRaises(ValueError):audit([row('a'),row('b',True,'human')],{})

    def test_stable_ids_and_pair_order(self):
        rows=[row('z'),row('a',False,'clarify')]
        self.assertEqual(audit(rows,{}),audit(list(reversed(rows)),{}))

    def test_bool_integer_and_missing_none_are_not_same_input(self):
        self.assertEqual(differences({'x':False},{'x':0}),['x'])
        self.assertEqual(differences({}, {'x':None}),['x'])

    def test_parameter_slot_alias_is_only_normalized_for_audit(self):
        a,b=row('a'),row('b',True,'clarify')
        a['input']['state']['application_id']=23
        a['annotation'].update(tool_name='queryApplicationDetail',tool_arguments={'applicationId':23})
        b['annotation']['missing_slots']=['applicationId']
        pair=audit([a,b],{})[0][0]
        self.assertTrue(pair['matches_expected_boundary'])
        self.assertEqual(b['annotation']['missing_slots'],['applicationId'])

    def test_capacity_keeps_one_anchor_and_reports_cell_deficit(self):
        a,b=row('a'),row('b',False,'clarify')
        pairs,_,_=audit([a,b],{})
        value=capacity([a,b],pairs,[['a','a']])
        self.assertEqual(value['missing_rows'],1);self.assertFalse(value['necessary_cell_capacity_passed'])
        self.assertEqual(value['fixed_authenticated_auth_pair_ceiling'],1)
        c=row('c',False,'clarify');c['input']['message']='other';c['scene_family_id']='g2'
        value=capacity([a,b,c],pairs,[['a','c']])
        self.assertTrue(value['necessary_cell_capacity_passed'])
        self.assertEqual(value['missing_rows'],1)

    def test_capacity_output_stable_across_process_hash_seeds(self):
        import os,subprocess,sys,json
        rows=[row('a'),row('b',False,'clarify'),row('c',True,'human')]
        pairs=[{'row_ids':['a','b'],'dimension':'authentication','matches_expected_boundary':True},
               {'row_ids':['a','c'],'dimension':'tool_availability','matches_expected_boundary':True}]
        script=('import json;from qwenlab.financial_state_pair_audit import capacity;'
                f'print(json.dumps(capacity({rows!r},{pairs!r},[]),ensure_ascii=True))')
        outputs=[subprocess.check_output([sys.executable,'-c',script],env=dict(os.environ,PYTHONHASHSEED=str(seed))) for seed in (1,2,3)]
        self.assertEqual(len(set(outputs)),1)


if __name__=='__main__':unittest.main()
