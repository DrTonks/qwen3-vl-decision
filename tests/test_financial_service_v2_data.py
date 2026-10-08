from copy import deepcopy
import unittest
from unittest.mock import patch

from qwenlab.financial_service_v2_data import groups, migrate_input, check_row, overlap_audit
from qwenlab import financial_service_v2_data as data
from qwenlab.financial_prompt_v2 import messages, encode, SPEC


def row(rid='a'):
    return dict(id=rid, scene_family_id='family-' + rid, split='train',
        input=dict(message='查询本人的信用评分', history=[], state={'authenticated': True}, service_scope='loan_platform',
                   capability_profile='current-node-no-kb', capabilities={'knowledge_collections': [], 'handoff_available': False},
                   available_tools=list(SPEC['tools']), images=[]),
        annotation=dict(action='tool', tool_name='queryMyCreditScore', tool_arguments={}, retrieval_collection=None,
                        missing_slots=[], reason='已有评分查询', evidence_paths=['input.message'], policy_version=SPEC['version']))


class MigrationTests(unittest.TestCase):
    def test_connected_true_not_inferred_as_available(self):
        value = row()['input']; value['capability_profile'] = 'current-no-kb-v1'
        value['capabilities'] = dict(knowledge_collections=[], handoff_connected=True)
        with self.assertRaises(ValueError): migrate_input(value)
        value['capabilities']['handoff_connected'] = False
        before = deepcopy(value); new = migrate_input(value)
        self.assertEqual(value, before)
        self.assertEqual(new['state']['handoff_status'], 'none')
        self.assertIs(new['capabilities']['handoff_available'], False)

    def test_source_and_partition_links_quarantine_as_one_group(self):
        a,b,c,d = [row(x) for x in 'abcd']
        a['curation'] = {'partition_group': 'FT-G-shared'}
        b['curation'] = {'partition_group': 'FT-G-shared'}
        c['provenance'] = {'source_id': b['id']}
        mapping = groups([a,b,c,d])
        self.assertEqual(mapping['a'], mapping['c'])
        self.assertNotEqual(mapping['a'], mapping['d'])

    def test_auth_capability_arguments_are_not_just_labels(self):
        a = row(); check_row(a,SPEC)
        a['input']['state']['authenticated'] = False
        with self.assertRaises(ValueError): check_row(a,SPEC)

    def test_target_must_match_trusted_state(self):
        a=row();a['input']['state']['application_id']=100
        a['annotation'].update(tool_name='queryApplicationDetail',tool_arguments={'applicationId':101})
        with self.assertRaisesRegex(ValueError,'trusted state'):check_row(a,SPEC)

    def test_freeze_rechecks_shape_instead_of_trusting_prepare(self):
        with patch.object(data.Path,'exists',return_value=False), patch.object(data,'validate_train',return_value=[]), \
             patch.object(data,'read',return_value=[]), patch.object(data,'write',side_effect=AssertionError('must not write')):
            with self.assertRaisesRegex(ValueError,'384'):data.freeze_evaluation()

    def test_evaluation_manifest_must_bind_actual_train(self):
        m=dict(code_sha256='current',policy_sha256='policy',training_eligible=False,files={},train_sha256='stale')
        with patch.object(data,'validate_train',return_value=[]),patch.object(data,'protocol',return_value=(SPEC,'policy')), \
             patch.object(data,'read',return_value=m),patch.object(data,'sha',return_value='current'):
            with self.assertRaisesRegex(ValueError,'bound to training'):data.validate()
        a = row(); a['annotation']['action']='retrieve';a['annotation']['tool_name']=None
        a['annotation']['retrieval_collection']='loan_service_docs'
        with self.assertRaises(ValueError): check_row(a,SPEC)

    def test_cross_split_context_and_numeric_paraphrase_detected(self):
        a,b,c = [row(x) for x in 'abc']
        a['input']['message']='查申请123的状态';b['input']['message']='查申请456的状态'
        b['split']='development';c['split']='final';c['input']['message']=b['input']['message']
        result=overlap_audit([a],[b,c])
        self.assertEqual(len(result['exact_context']),2)
        self.assertEqual(len(result['cross_split']),1)

    def test_prompt_never_contains_annotations_and_order_is_canonical(self):
        a = row(); b=deepcopy(a)
        b['annotation']['reason']='PRIVATE_LABEL_DO_NOT_LEAK'
        b['input']['available_tools'].reverse()
        self.assertEqual(messages(a),messages(b))
        self.assertNotIn('PRIVATE_LABEL_DO_NOT_LEAK',str(messages(b)))
        self.assertEqual(messages(a)[1],SPEC['actions'])

    def test_encoder_refuses_silent_truncation_and_wrong_template(self):
        class Tokenizer:
            def encode(self,text,**kwargs):return [ord(text)]
            def apply_chat_template(self,*args,**kwargs):return 'prefix<think>\n\n</think>\n\n'
            def __call__(self,*args,**kwargs):return {'input_ids':[1]*20,'attention_mask':[1]*20}
        result=encode(Tokenizer(),row(),target='tool')
        self.assertEqual(result['target'],SPEC['actions'].index('tool'))
        with self.assertRaises(ValueError):encode(Tokenizer(),row(),max_tokens=10)
        tok=Tokenizer();tok.apply_chat_template=lambda *a,**k:'thinking'
        with self.assertRaises(ValueError):encode(tok,row())


if __name__=='__main__':unittest.main()
