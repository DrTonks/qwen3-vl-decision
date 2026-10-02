import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qwenlab import support_v8_observe as obs
from qwenlab.common import load_json, sha
from qwenlab.joint_v5 import atomic_json, lr_scale


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_json(obs.ROOT/'configs/support-v8.json')
        self.policy=load_json(obs.POLICY)
        self.ref={n:load_json(obs.PARENT/'v5-reference'/f'{n}-dev-metrics.json')
                  for n in ('business','legacy','massive','crosswoz')}
        self.now={n:load_json(obs.PARENT/'step-2401'/f'{n}-dev-metrics.json')
                  for n in self.ref}

    def test_one_miss_can_continue_but_cannot_be_selected(self):
        d=obs.observation_decision(self.ref,self.now,self.cfg,self.policy,2801)
        self.assertFalse(d['candidate_eligible'])
        self.assertTrue(d['continue_observation'])

    def test_two_misses_or_other_regression_stops(self):
        now=copy.deepcopy(self.now); now['legacy']['human_missed']=2
        self.assertFalse(obs.observation_decision(self.ref,now,self.cfg,self.policy,2801)['continue_observation'])
        now=copy.deepcopy(self.now); now['legacy']['tasks']['route']['accuracy']=.94
        self.assertFalse(obs.observation_decision(self.ref,now,self.cfg,self.policy,2801)['continue_observation'])
        now=copy.deepcopy(self.now); now['business']['human_missed']=1
        self.assertFalse(obs.observation_decision(self.ref,now,self.cfg,self.policy,2801)['continue_observation'])

    def test_progress_does_not_truncate_inflight_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            atomic_json(out/'status.json',{'stage':'training'})
            data='{"step":2402,"elapsed_s":1}\n{"step":2403'
            (out/'train.jsonl').write_text(data,encoding='utf-8')
            with patch.object(obs,'OUT',out): obs.progress()
            self.assertEqual((out/'train.jsonl').read_text(encoding='utf-8'),data)

    def test_recovered_candidate_eligible_but_budget_never_extends(self):
        now=copy.deepcopy(self.now); now['legacy']['human_missed']=0
        d=obs.observation_decision(self.ref,now,self.cfg,self.policy,3201)
        self.assertTrue(d['candidate_eligible'])
        self.assertFalse(d['continue_observation'])
        self.assertTrue(d['budget_exhausted'])

    def test_checkpoint_tamper_and_parent_protocol_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'step-2401'; p.mkdir()
            files=['adapter_model.safetensors','adapter_config.json','training-state.pt']
            for name in files: (p/name).write_text('x')
            atomic_json(p/'checkpoint.json',{'step':2401,'protocol_sha256':'parent',
                        'files':{name:sha(p/name) for name in files}})
            self.assertEqual(obs.verify_checkpoint(p,'parent'),2401)
            with self.assertRaises(ValueError): obs.verify_checkpoint(p,'other')
            (p/files[0]).write_text('changed')
            with self.assertRaises(ValueError): obs.verify_checkpoint(p,'parent')

    def test_optimizer_loss_schedule_and_rng_match_frozen_run(self):
        # Compare critical executable statements structurally, not comments or text labels.
        old=ast.parse(Path(obs.original.__file__).read_text(encoding='utf-8'))
        new=ast.parse(Path(obs.__file__).read_text(encoding='utf-8'))
        def statements(tree):
            run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
            return {ast.dump(n,include_attributes=False) for n in ast.walk(run)
                    if isinstance(n,(ast.Assign,ast.AugAssign,ast.Expr))}
        wanted=['optimizer.load_state_dict', "restore_rng(saved['rng'])",'group[\'lr\']',
                'loss = sum','kd = sum','total_loss =','optimizer.step()',
                'blocks = epoch_blocks','chunk = blocks','scores = batch_logits']
        new_statements=statements(new)
        for text in wanted:
            run=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='run')
            critical=[n for n in ast.walk(run) if isinstance(n,(ast.Assign,ast.Expr)) and text in ast.unparse(n)]
            self.assertTrue(critical,text)
            for n in critical:
                self.assertIn(ast.dump(n,include_attributes=False),new_statements,text)
        self.assertEqual(self.policy['lr_schedule_total_steps'],4802)
        self.assertNotEqual(lr_scale(2402,4802,.02),lr_scale(1,800,.02))

    def test_finish_never_promotes_failed_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            import shutil
            for name in ['v5-reference','step-200','step-2401']:
                shutil.copytree(obs.PARENT/name,out/name)
            with patch.object(obs,'OUT',out),patch.object(obs,'status'):
                obs.finish(self.ref,self.cfg,'observation_stopped',2401)
            s=load_json(out/'selection.json')
            self.assertEqual(s['selected'],'step-200')
            self.assertFalse(s['choices']['step-2401']['eligible'])


if __name__=='__main__': unittest.main()
