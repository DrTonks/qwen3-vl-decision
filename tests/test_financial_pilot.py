"""CPU-only contract tests: leakage, grounding, isolation and review boundaries."""
from copy import deepcopy
import unittest
from qwenlab.financial_pilot import (
    base_input, label, make, serialize_input, validate_row, validate_rows,
)
from qwenlab.support_curriculum import normalize


def sample():
    return make('unit','family-1',base_input('查询本账户的申请清单'),
                label('tool','查询可信账户记录',tool='queryMyApplications'),
                {'kind':'unit','source':'unit','parent_id':'p1','source_split':'train'})


class FinancialPilotTests(unittest.TestCase):
    def test_label_and_metadata_not_encoded_and_tool_order_stable(self):
        a=sample(); b=deepcopy(a)
        b['annotation']['reason']='SECRET_ANNOTATION'
        b['provenance']['source']='SECRET_SOURCE'
        b['input']['available_tools'].reverse()
        b['input']['capabilities']['knowledge_collections'].reverse()
        self.assertEqual(serialize_input(a),serialize_input(b))
        self.assertNotIn('SECRET',serialize_input(b))

    def test_unauthenticated_tool_rejected(self):
        r=sample();r['input']['state']['authenticated']=False
        with self.assertRaisesRegex(ValueError,'unauthenticated'):validate_row(r)

    def test_application_argument_must_match_visible_state(self):
        r=sample();r['input']['message']='查看申请73168'
        r['input']['state']['application_id']=73168
        r['annotation']=label('tool','读取指定申请',tool='queryApplicationDetail',arguments={'applicationId':73169})
        with self.assertRaisesRegex(ValueError,'grounded'):validate_row(r)
        r['annotation']['tool_arguments']={'applicationId':73168}
        validate_row(r)

    def test_retrieval_requires_collection(self):
        r=sample();r['annotation']=label('retrieve','查阅平台文档',collection='loan_service_docs')
        r['input']['capabilities']['knowledge_collections']=[]
        with self.assertRaisesRegex(ValueError,'Retrieval not available'):validate_row(r)

    def test_protected_message_is_rejected(self):
        r=sample()
        with self.assertRaisesRegex(ValueError,'Protected'):validate_rows([r],{normalize(r['input']['message'])})

    def test_duplicate_input_even_with_reordered_tools_is_rejected(self):
        a=sample();b=deepcopy(a);b['id']='another'
        b['input']['available_tools'].reverse()
        with self.assertRaisesRegex(ValueError,'canonical input'):validate_rows([a,b],set())

    def test_related_source_stays_in_same_family(self):
        a=sample();b=deepcopy(a);b['id']='another';b['scene_family_id']='wrong'
        b['input']['message']='查看我的借款申请列表'
        with self.assertRaisesRegex(ValueError,'different families'):validate_rows([a,b],set())

    def test_no_inherited_human_review(self):
        r=sample();r['review']['human_reviewed_current_version']=True
        with self.assertRaisesRegex(ValueError,'human review'):validate_row(r)

    def test_evidence_path_must_exist(self):
        r=sample();r['annotation']['evidence_paths']=['input.unseen_fact']
        with self.assertRaisesRegex(ValueError,'does not exist'):validate_row(r)

    def test_discussion_excluded_from_eligible_counts(self):
        r=sample();r['review']['status']='needs_discussion'
        result=validate_rows([r],set())
        self.assertEqual(result['eligible_draft_candidates'],0)
        self.assertEqual(result['pending_discussion'],1)
        self.assertFalse(result['training_release'])


if __name__=='__main__':unittest.main()
