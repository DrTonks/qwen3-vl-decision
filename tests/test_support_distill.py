import copy
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from qwenlab.support_distill import (attach_teacher, cache_identity, distillation_loss, encoded_hash,
                                    training_coverage, validate_record)
from qwenlab.support_train_v8 import gate
from qwenlab.common import load_json


def example(i=0):
    return {'id':str(i),'task':'route','dataset':'business','tokens':{'input_ids':[10,i,20]},
            'keys':['human','tool'],'ids':[65,66],'target':0,'teacher_eligible':True}


class DistillTests(unittest.TestCase):
    def test_kl_zero_when_equal_and_gradient_towards_teacher(self):
        teacher=torch.tensor([2.,-1.],requires_grad=True)
        same=teacher.detach().clone().requires_grad_()
        self.assertAlmostEqual(distillation_loss(same,teacher,2.).item(),0.,places=6)
        student=torch.tensor([-1.,2.],requires_grad=True)
        loss=distillation_loss(student,teacher,2.)
        loss.backward()
        self.assertGreater(loss.item(),0.)
        self.assertLess(student.grad[0].item(),0.)
        self.assertGreater(student.grad[1].item(),0.)
        self.assertIsNone(teacher.grad)
        with self.assertRaises(ValueError): distillation_loss(student,[math.nan,1.],2.)
        with self.assertRaises(ValueError): distillation_loss(student,[1.,2.],0.)

    def test_teacher_binding_rejects_shuffled_candidates_and_changed_input(self):
        x=example(); r={'id':x['id'],'task':x['task'],'encoded_sha256':encoded_hash(x),'logits':[2.,1.]}
        validate_record(r,x)
        for key,value in [('keys',['tool','human']),('tokens',{'input_ids':[11,0,20]})]:
            changed=copy.deepcopy(x); changed[key]=value
            with self.assertRaisesRegex(ValueError,'changed'): validate_record(r,changed)

    def test_real_tokenizer_batchencoding_has_same_hash_as_plain_mapping(self):
        from transformers.tokenization_utils_base import BatchEncoding
        x=example(); expected=encoded_hash(x)
        x['tokens']=BatchEncoding(x['tokens'])
        self.assertEqual(encoded_hash(x),expected)

    def test_cache_reuse_integrity_and_student_cannot_generate_teacher(self):
        cfg={'distillation':{'cache_expected_items':1,'batch_size':2,'tasks':['route']}}
        class Model:
            def eval(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); pools={'business.route':[example()]}
            with patch('qwenlab.support_distill.batch_logits',return_value=[torch.tensor([2.,1.])]) as scorer:
                attach_teacher(None,Model(),pools,cfg,folder,'protocol',lambda *a,**k:None)
                self.assertEqual(scorer.call_count,1)
                attach_teacher(None,Model(),pools,cfg,folder,'protocol',lambda *a,**k:None,True)
                self.assertEqual(scorer.call_count,1)
            self.assertEqual(pools['business.route'][0]['teacher_logits'],[2.,1.])
            (folder/'logits.jsonl').write_text('{}\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'integrity'):
                attach_teacher(None,Model(),pools,cfg,folder,'protocol',lambda *a,**k:None,True)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'intact V5'):
                attach_teacher(None,Model(),pools,cfg,Path(tmp),'protocol',lambda *a,**k:None,True)

    def test_partial_cache_resumes_only_remaining_items(self):
        from qwenlab.common import append_json
        from qwenlab.joint_v5 import atomic_json
        cfg={'distillation':{'cache_expected_items':2,'batch_size':2,'tasks':['route']}}
        class Model:
            def eval(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); x=example(0); y=example(1)
            atomic_json(folder/'identity.json',cache_identity([x,y],'p'))
            append_json(folder/'logits.jsonl',{'id':'0','task':'route','encoded_sha256':encoded_hash(x),'logits':[2.,1.]})
            with patch('qwenlab.support_distill.batch_logits',return_value=[torch.tensor([3.,1.])]) as scorer:
                attach_teacher(None,Model(),{'business.route':[x,y]},cfg,folder,'p',lambda *a,**k:None)
                self.assertEqual([r['id'] for r in scorer.call_args.args[2]],['1'])
            self.assertEqual(load_json(folder/'manifest.json')['items'],2)
            with self.assertRaisesRegex(ValueError,'protocol changed'):
                attach_teacher(None,Model(),{'business.route':[x,y]},cfg,folder,'changed',lambda *a,**k:None)

    def test_training_coverage_rejects_heldout(self):
        r={'split':'dev','training_origin':'legacy_state_replay','labels':{'route':'human'}}
        with self.assertRaisesRegex(ValueError,'training rows'): training_coverage([r])

    def test_floors_and_human_misses_prevent_continuation(self):
        from test_support_train import SupportTrainingTests
        ref,cfg=SupportTrainingTests().reference()
        cfg['gate'].update(min_business_route_accuracy=.95,min_legacy_route_accuracy=.96)
        now=copy.deepcopy(ref)
        for name in ('business','legacy'):
            now[name]['tasks']['route'].update(accuracy=.97,correct=97,macro_f1_gold_supported_classes=.97)
        self.assertTrue(gate(ref,now,cfg)['continue_training'])
        now['business']['tasks']['route']['accuracy']=.94
        self.assertFalse(gate(ref,now,cfg)['continue_training'])
        now['business']['tasks']['route']['accuracy']=.97
        now['legacy']['human_missed']=1
        self.assertFalse(gate(ref,now,cfg)['continue_training'])


if __name__=='__main__': unittest.main()
