import copy
import unittest
from collections import Counter
from qwenlab.financial_coverage_audit import inventory, parameter_form, segment, slots


def row(auth=False, kb=(), action='clarify', tool=None, missing=()):
    return dict(id='training-fixture',scene_family_id='story-fixture',
        input=dict(state=dict(authenticated=auth),capabilities=dict(knowledge_collections=list(kb))),
        annotation=dict(action=action,tool_name=tool,missing_slots=list(missing)))


class CoverageTests(unittest.TestCase):
    def test_authentication_is_not_inferred_from_truthy_text(self):
        with self.assertRaises(ValueError): segment(row(auth='false'))
        self.assertEqual(segment(row()),'preauth-no-kb')
        self.assertEqual(segment(row(kb=['docs'])),'preauth-kb')

    def test_aliases_are_audit_only_and_deduplicated(self):
        r=row(missing=['applicationId','application_id','authentication'])
        before=copy.deepcopy(r)
        self.assertEqual(slots(r),'application_id+authentication')
        self.assertEqual(r,before)

    def test_status_zero_is_valid_but_boolean_is_not_a_code(self):
        r=row(True,action='tool',tool='explainApplicationStatus')
        r['input']['state']['status_code']=0
        self.assertEqual(parameter_form(r,dict(parsed_state={})), 'tool:structured_status_code')
        r['input']['state']['status_code']=False
        self.assertEqual(parameter_form(r,dict(parsed_state={})), 'tool:unresolved_by_node_status_code')

    def test_missing_structured_id_does_not_mean_missing_from_message(self):
        r=row(True,action='tool',tool='queryApplicationDetail')
        self.assertEqual(parameter_form(r,dict(parsed_state={'application_id':81})), 'tool:node_parsed_application_id')
        self.assertEqual(parameter_form(r,dict(parsed_state={})), 'tool:unresolved_by_node_application_id')

    def test_nonparametric_tools_do_not_require_id(self):
        self.assertEqual(parameter_form(row(True,action='tool',tool='queryMyApplications'),dict(parsed_state={})),
                         'tool:no_extra_parameter')

    def test_declared_missing_is_not_hidden_semantic_label_inference(self):
        r=row(action='answer')
        self.assertEqual(parameter_form(r,dict(parsed_state={})), 'non_tool:none_declared')

    def test_repeated_exposure_does_not_create_rows_or_groups(self):
        a=row(); b=copy.deepcopy(a);b['id']='training-fixture-2'
        v=inventory([a,b],{'arm':Counter({a['id']:4,b['id']:2,'outside':7})})
        self.assertEqual((v['rows'],v['story_groups'],v['unique_visible_inputs']),(2,1,1))
        self.assertEqual(v['exposures'],{'arm':6})
        self.assertEqual(v['unique_exposed'],{'arm':2})


if __name__=='__main__': unittest.main()
