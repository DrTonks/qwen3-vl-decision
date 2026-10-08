"""CPU tests: synthetic inputs; no model or holdout examples."""
import ast
from collections import Counter
from copy import deepcopy
import inspect
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from qwenlab import financial_full_coverage_cycle as c
from qwenlab import financial_full_coverage_schedule as s
from qwenlab import financial_state_pair_cycle as old


class FullCoverageTests(unittest.TestCase):
    def cfg(self):
        return dict(rows=22,epochs=2,batch=8,steps_per_epoch=3,steps_per_arm=6,sampling_seed=7)

    def test_all_rows_once_per_epoch_including_partial_batch(self):
        rows=[{'id':str(i)} for i in range(22)]
        plan=s.make_plan([r['id'] for r in rows],self.cfg())
        self.assertEqual([len(b) for b in plan['step_rows']],[8,8,6]*2)
        s.validate_plan(plan,rows,self.cfg())
        for batches in (plan['step_rows'][:3],plan['step_rows'][3:]):
            self.assertEqual(Counter(x for b in batches for x in b),Counter({r['id']:1 for r in rows}))

    def test_schedule_deterministic_and_global_rng_unchanged(self):
        import random
        state=random.getstate()
        a=s.make_plan([str(i) for i in range(22)],self.cfg())
        b=s.make_plan(list(reversed([str(i) for i in range(22)])),self.cfg())
        self.assertEqual(a,b);self.assertEqual(state,random.getstate())
        self.assertNotEqual(a['step_rows'][:3],a['step_rows'][3:])

    def test_duplicates_or_omissions_rejected(self):
        with self.assertRaises(ValueError):s.make_plan(['x']*22,self.cfg())
        rows=[{'id':str(i)} for i in range(22)]
        plan=s.make_plan([r['id'] for r in rows],self.cfg())
        plan['step_rows'][0][0]=plan['step_rows'][0][1]
        with self.assertRaises(ValueError):s.validate_plan(plan,rows,self.cfg())

    def test_partial_batch_gradient_equals_global_mean(self):
        import torch
        for count in (6,8):
            x=torch.tensor(2.,requires_grad=True)
            values=torch.arange(1,count+1,dtype=torch.float32)
            for p in range(0,count,2):
                block=values[p:p+2]
                loss=(x*block).mean()*c.micro_weight(len(block),count)
                loss.backward()
            self.assertAlmostEqual(float(x.grad),float(values.mean()))
            self.assertAlmostEqual(sum(c.micro_weight(2,count) for _ in range(0,count,2)),1)
        for args in ((0,6),(2,0),(2,9),(True,6)):
            with self.assertRaises(ValueError):c.micro_weight(*args)

    def test_frozen_lr_long_budget_including_probe(self):
        cfg={'steps_per_arm':3346,'learning_rate':5e-5,'warmup_steps':100}
        self.assertAlmostEqual(c.learning_rate(12,cfg),6e-6)
        self.assertAlmostEqual(c.learning_rate(100,cfg),5e-5)
        self.assertGreater(c.learning_rate(400,cfg),old.learning_rate(400,cfg))
        self.assertAlmostEqual(c.learning_rate(3346,cfg),5e-5/3246)
        for n in (0,3347,True,1.5):
            with self.assertRaises(ValueError):c.learning_rate(n,cfg)

    def test_original_gates_unchanged(self):
        cfg=c.check_design(c.read(c.CONFIG))
        original=c.read(c.REFERENCE/'protocol.json')['config']
        for k in ('development_gate','current_service_additional_gate','preauth_additional_gate','capability_additional_gate','calibration','optimizer','lora','loss'):
            self.assertEqual(cfg[k],original[k])

    def test_selection_only_passing_declared_candidate_and_earlier_tie(self):
        reports={'base':{},'fullcover-step-500':{'macro_f1':.9,'action_tool_joint_accuracy':.95},
                 'fullcover-step-1000':{'macro_f1':.9,'action_tool_joint_accuracy':.95},
                 'fullcover-step-1500':{'macro_f1':1.,'action_tool_joint_accuracy':1.}}
        with patch.object(c.metrics,'development_gate',side_effect=[{'passed':True},{'passed':True},{'passed':False}]):
            decision=c.choose_candidate(reports,{},'hash')
        self.assertEqual(decision['selected'],'fullcover-step-500')
        with patch.object(c.metrics,'development_gate',return_value={'passed':False}):
            self.assertIsNone(c.choose_candidate(reports,{},'hash')['selected'])

    def test_pause_and_checkpoint_helpers_identical_to_old(self):
        names=['save_checkpoint','record_restoration','pause_check','pause','recover_logs','validate_probe_evidence','verify_probe','optimizer_for','encoded_training','ensure_finite_training']
        for name in names:
            def tree(module):
                code=inspect.getsource(getattr(module,name)).replace('financial-full-coverage','financial-state-pair').replace('fullcover','statepair')
                return ast.dump(ast.parse(code),include_attributes=False)
            self.assertEqual(tree(c),tree(old),name)

    def test_namespaces_do_not_overlap(self):
        for attr in ('out','control','checkpoints','cache'):
            self.assertNotEqual(getattr(c.Run(),attr),getattr(old.Run(),attr))
            self.assertNotEqual(getattr(c.Run(),attr),getattr(c.Run(c.PROBE),attr))

    def test_nll_uses_gold_target_probability_not_argmax(self):
        rows=[{'id':'a','annotation':{'action':'clarify'}}]
        pred=[{'id':'a','action_prediction':{'probabilities':{'clarify':.25,'tool':.75}}}]
        with patch.object(c.ft,'evaluation_prefix'):
            self.assertAlmostEqual(c.development_nll(rows,pred),-math.log(.25))
            with self.assertRaises(ValueError):c.development_nll(rows,[])

    def test_single_wave_or_first_epoch_does_not_stop(self):
        policy=c.read(c.CONFIG)['early_stop']
        def row(step,f1,nll,miss=1,tool=1):
            return dict(step=step,macro_f1=f1,nll=nll,human_misses=miss,preauth_tool_actions=tool)
        h=[row(500,.9,.3),row(1000,.85,.4),row(1500,.85,.4)]
        self.assertFalse(c.deterioration_history(h,policy))
        h += [row(1673,.85,.4),row(2000,.85,.4)]
        self.assertFalse(c.deterioration_history(h,policy))
        h += [row(2500,.85,.4)]
        self.assertTrue(c.deterioration_history(h,policy))
        h[-1]=row(2500,.92,.2)
        self.assertFalse(c.deterioration_history(h,policy))
        h[-1]=row(2500,.85,.4,tool=0)
        self.assertFalse(c.deterioration_history(h,policy))

    def test_resume_cursor_counts_actual_last_batch(self):
        plan={'step_rows':[['x']*8,['y']*6]}
        protocol={'common_binding':{'schedule_manifest_sha256':'m'}}
        summary=dict(step=2,arm='fullcover',schedule_manifest_sha256='m',cursor=dict(arm='fullcover',completed_steps=2,next_step=3),initial_parameter_sha256='a'*64,sample_positions=14)
        with patch.object(c,'read',return_value=plan):
            self.assertTrue(c.checkpoint_summary_binding(summary,protocol,'fullcover',2))
            summary['sample_positions']=16
            with self.assertRaises(ValueError):c.checkpoint_summary_binding(summary,protocol,'fullcover',2)

    def test_failed_selection_blocks_holdout_before_reading_rows(self):
        run=SimpleNamespace(probe=False,out=Path('synthetic'),protocol_hash=lambda:'h')
        with patch.object(c,'read',return_value={'passed':False,'protocol_sha256':'h'}):
            with self.assertRaises(ValueError):c.evaluation_rows(run,{},'final','fullcover-step-500')


if __name__=='__main__': unittest.main()
