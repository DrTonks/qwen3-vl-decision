"""Pilot leakage, sampling, freeze, checkpoint and manual-control regressions."""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
from contextlib import nullcontext
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from qwenlab.common import ROOT,sha
from qwenlab import financial_train as ft
from qwenlab import financial_actions_metrics as metrics
from qwenlab.financial_pilot import ACTIONS


def workspace():
    path = ROOT/'.local/test-financial-train'/uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def record(n, action='answer', profile='current-no-kb-v1', group='one'):
    return dict(id=str(n),group=group,action=action,tool_name=None,
        input=dict(message='测试',history=[],images=[],available_tools=[],capability_profile=profile,
            state=dict(authenticated=True),capabilities=dict(knowledge_collections=[],available_tools=[])))


class PilotTests(unittest.TestCase):
    def test_group_and_stratum_not_weighted_by_number_of_paraphrases(self):
        rows = [record(n,group='large') for n in range(1000)]
        rows += [record(1001,group='small'),record(1002,action='human',group='single')]
        sampler = ft.GroupSampler(rows,20261001)
        selected = [rows[i] for i in sampler.draw(6000)]
        humans = sum(r['action']=='human' for r in selected)
        small = sum(r['group']=='small' for r in selected)
        large = sum(r['group']=='large' for r in selected)
        self.assertTrue(2800<humans<3200)
        self.assertTrue(abs(small-large)<200)

    def test_sampler_resume_replays_exact_next_draws(self):
        rows = [record(n,group=str(n%3)) for n in range(20)]
        first = ft.GroupSampler(rows,1)
        first.draw(123)
        state = first.rng.getstate()
        expected = first.draw(80)
        resumed = ft.GroupSampler(rows,1)
        resumed.rng.setstate(state)
        self.assertEqual(resumed.draw(80),expected)

    def test_tool_is_conditioned_on_prediction_not_gold(self):
        r = record(0,'tool');r['annotation']={'action':'tool','tool_name':'queryMyCreditScore'}
        calls = []
        def predict(tok,scorer,row,task):
            calls.append(task)
            return dict(choice='clarify',input_tokens=12,elapsed_s=.1)
        result = ft.predict_request(None,None,r,predict)
        self.assertEqual(calls,['action'])
        self.assertIsNone(result['tool_name'])
        self.assertNotIn('tool_prediction',result)

    def test_false_tool_prediction_also_runs_model_tool_task(self):
        r = record(0,'answer');calls=[]
        def predict(tok,scorer,row,task):
            calls.append(task)
            return dict(choice='tool' if task=='action' else 'queryMyApplications',input_tokens=10,elapsed_s=.1)
        result = ft.predict_request(None,None,r,predict)
        self.assertEqual(calls,['action','tool'])
        self.assertEqual(result['tool_name'],'queryMyApplications')
        self.assertEqual(result['processed_input_tokens'],20)
        self.assertNotIn('tool_arguments',result)

    def test_duplicate_or_wrong_evaluation_resume_prefix_rejected(self):
        rows = [dict(id=str(n)) for n in range(3)]
        for wrong in [[dict(id='1')],[dict(id='0'),dict(id='0')],rows+[dict(id='3')]]:
            with self.assertRaises(ValueError): ft.evaluation_prefix(rows,wrong)
        ft.evaluation_prefix(rows,rows[:2])

    def test_safe_run_names_only(self):
        for name in ['../outside','C:\\outside','UPPER','a/b','a'*65]:
            with self.assertRaises(ValueError): ft.Run(name)

    def test_frozen_resume_rejects_changed_policy_and_preserves_protocol(self):
        root = workspace()
        source = root/'data/new';parent = root/'data/base'
        ft.durable_json(source/'manifest.json',dict(source_bindings={}))
        ft.durable_json(parent/'manifest.json',{})
        config = dict(base_checkpoint='models/tiny',pilot=dict(max_steps=200),initial_adapter=None,jev_requests=0)
        ft.durable_json(source/'protocol.json',config)
        (root/'models/tiny').mkdir(parents=True)
        prompt = root/'src/qwenlab/financial_actions_prompt.py';prompt.parent.mkdir(parents=True);prompt.write_text('prompt')
        with patch.object(ft,'ROOT',root),patch.object(ft,'ACTIVE',root/'.local/active.json'),patch.object(ft,'SOURCES',[]),patch.object(ft,'PACKAGES',[]),patch.object(ft.data,'OUT',source),patch.object(ft.data,'BASE',parent),patch.object(ft.data,'validate'):
            run = ft.Run('test')
            original = ft.freeze(run,False)
            digest = sha(run.out/'protocol.json')
            self.assertEqual(ft.freeze(run,True),original)
            config['pilot']['max_steps'] = 199
            ft.durable_json(source/'protocol.json',config)
            with self.assertRaises(ValueError): ft.freeze(run,True)
            self.assertEqual(sha(run.out/'protocol.json'),digest)
            with self.assertRaises(FileExistsError):
                config['pilot']['max_steps']=200;ft.durable_json(source/'protocol.json',config);ft.freeze(run,False)

    def test_checkpoint_inventory_hash_and_path_are_checked(self):
        root = workspace()
        with patch.object(ft,'ROOT',root):
            run = ft.Run('test');ft.durable_json(run.out/'protocol.json',{})
            checkpoint = run.checkpoints/'step-20';checkpoint.mkdir(parents=True)
            files = ['adapter_model.safetensors','adapter_config.json','training-state.pt']
            for name in files: (checkpoint/name).write_bytes(b'fake')
            ft.durable_json(checkpoint/'checkpoint.json',dict(step=20,protocol_sha256=run.protocol_hash(),files={n:sha(checkpoint/n) for n in files}))
            self.assertEqual(ft.latest_checkpoint(run),checkpoint)
            (checkpoint/'training-state.pt').write_bytes(b'tampered')
            with self.assertRaises(ValueError): ft.validate_checkpoint(run,checkpoint)
            with self.assertRaises(ValueError): ft.validate_checkpoint(run,root/'outside')

    def test_pause_does_not_claim_safe_shutdown_when_worker_failed(self):
        root=workspace()
        with patch.object(ft,'ROOT',root):
            run=ft.Run('test');ft.durable_json(run.out/'status.json',dict(stage='training',pid=123,process_created=1))
            with patch.object(ft,'is_worker_alive',side_effect=[True,False]):
                with self.assertRaisesRegex(RuntimeError,'without successful pause'): ft.pause(run,True)
            self.assertFalse(ft.read(run.control)['safe_to_shutdown'])

    def test_not_started_progress_without_model_or_gpu(self):
        root=workspace()
        with patch.object(ft,'ROOT',root): self.assertEqual(ft.progress(ft.Run('test'))['stage'],'not_started')

    def test_training_adapter_target_is_separate_from_input(self):
        source = dict(id='train',group='g',input=json.dumps(record(0)['input']),action='human',tool_name=None,
            tool_arguments={},retrieval_collection=None,missing_slots=[])
        with patch.object(ft.data,'training_rows',return_value=iter([source])):
            value=ft.training_records()[0]
        self.assertEqual(value['action'],'human')
        self.assertNotIn('action',value['input'])
        self.assertNotIn('annotation',value['input'])

    def test_selection_recomputes_raw_metrics_and_chooses_only_passing_candidate(self):
        root=workspace();rows=[]
        for n,action in enumerate(ACTIONS):
            r=record(n,action)
            r['split']='development'
            r['annotation']=dict(action=action,tool_name='explainApplicationStatus' if action=='tool' else None,
                tool_arguments={'status':2} if action=='tool' else {},reason='test')
            if action=='retrieve':r['input']['capabilities']['knowledge_collections']=['loan_service_docs']
            rows.append(r)
        with patch.object(ft,'ROOT',root),patch.object(ft.data,'OUT',root/'data'),patch.object(ft.data,'evaluation_rows',return_value=rows),patch.object(ft,'validate_checkpoint'):
            run=ft.Run('test')
            ft.durable_json(run.out/'protocol.json',{})
            ft.durable_json(ft.data.OUT/'evaluation/development.json',rows)
            policy=ft.read(ROOT/'configs/financial-eight-actions-pilot-v2.json')['development_gate']
            protocol=dict(prompt_sha256='0'*64,config=dict(pilot=dict(checkpoint_steps=[100,200]),development_gate=policy))
            for variant in ['base','step-100','step-200']:
                folder=run.out/variant;folder.mkdir(parents=True)
                predictions=[]
                for r in rows:
                    action=r['action']
                    if variant=='base' and action=='answer':action='clarify'
                    if variant=='step-200' and action=='human':action='answer'
                    predictions.append(dict(id=r['id'],action=action,tool_name='explainApplicationStatus' if action=='tool' else None,
                        action_elapsed_s=.02,elapsed_s=.03,input_tokens=12,projection='candidate'))
                for p in predictions:ft.append(folder/'predictions.jsonl',p)
                ft.durable_json(folder/'metrics.json',metrics.evaluate(rows,predictions,protocol['prompt_sha256'],run.protocol_hash()))
                ckhash=None
                if variant!='base':
                    ft.durable_json(run.checkpoints/variant/'checkpoint.json',{});ckhash=sha(run.checkpoints/variant/'checkpoint.json')
                ft.durable_json(folder/'binding.json',dict(protocol_sha256=run.protocol_hash(),variant=variant,checkpoint_sha256=ckhash,split_sha256=sha(ft.data.OUT/'evaluation/development.json')))
            _,_,selection=ft.select(run,protocol)
            self.assertEqual(selection['selected'],'step-100')
            self.assertIn('extra_human_misses',selection['gates']['step-200']['failures'])
            bad=ft.read(run.out/'step-100/metrics.json');bad['macro_f1']=.5;ft.durable_json(run.out/'step-100/metrics.json',bad)
            with self.assertRaisesRegex(ValueError,'differs from raw predictions'):ft.select(run,protocol)

    def test_completed_metrics_missing_timing_recovers_without_loading_a_model(self):
        root=workspace();r=record(0)
        r['split']='development';r['annotation']=dict(action='answer',tool_name=None,tool_arguments={})
        prediction=dict(id='0',action='answer',tool_name=None,elapsed_s=.3,action_elapsed_s=.3,
            input_tokens=12,projection='candidate')
        with patch.object(ft,'ROOT',root),patch.object(ft.data,'OUT',root/'data'),patch.object(ft.data,'evaluation_rows',return_value=[r]):
            run=ft.Run('test');ft.durable_json(run.out/'protocol.json',{})
            ft.durable_json(ft.data.OUT/'evaluation/development.json',[r])
            folder=run.out/'base';folder.mkdir()
            ft.durable_json(folder/'binding.json',ft.evaluation_binding(run,'base'))
            ft.append(folder/'predictions.jsonl',prediction)
            protocol=dict(prompt_sha256='0'*64)
            expected=metrics.evaluate([r],[prediction],protocol['prompt_sha256'],run.protocol_hash())
            ft.durable_json(folder/'metrics.json',expected)
            with patch.object(ft,'inference_scorer',side_effect=AssertionError('must not load/score')):
                result=ft.evaluate_development(run,None,None,'base',protocol)
            self.assertEqual(result,expected)
            self.assertEqual(ft.read(folder/'timing.json')['request_p50_s'],.3)
            broken=ft.read(folder/'timing.json');broken['request_p50_s']=.00001
            ft.durable_json(folder/'timing.json',broken)
            with self.assertRaises(ValueError):ft.finalize_evaluation(run,'base',protocol,[r],[prediction])

    def test_baseline_and_candidate_use_same_nonquantized_preparation(self):
        calls=[];tok=SimpleNamespace(padding_side='right');base=SimpleNamespace()
        def prepare(model,**kwargs):
            calls.append(kwargs);self.assertIs(model,base);return model
        fake=SimpleNamespace(prepare_model_for_kbit_training=prepare)
        with patch.dict(sys.modules,{'peft':fake}),patch('qwenlab.modeling.load_model',return_value=(tok,base)):
            self.assertIs(ft.prepared_base(dict(precision='nf4'),False)[1],base)
            self.assertIs(ft.prepared_base(dict(precision='nf4'),True)[1],base)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0]['gradient_checkpointing_kwargs'],calls[1]['gradient_checkpointing_kwargs'])
        self.assertFalse(calls[0]['use_gradient_checkpointing'])
        self.assertTrue(calls[1]['use_gradient_checkpointing'])

    def test_resume_does_not_overwrite_pause_requested_during_protocol_hashing(self):
        root=workspace()
        with patch.object(ft,'ROOT',root):
            run=ft.Run('test');ft.durable_json(run.out/'protocol.json',{})
            ft.durable_json(run.control,dict(state='paused'))
            def freeze(r,resume):
                ft.durable_json(r.control,dict(state='pause_requested'))
                return {}
            with patch('qwenlab.joint_v5.exclusive_lock',return_value=nullcontext()),patch.object(run,'status'),patch.object(ft,'freeze',side_effect=freeze):
                with self.assertRaises(ft.Paused):ft.worker(run,True)
            self.assertEqual(ft.read(run.control)['state'],'paused')


if __name__=='__main__':
    unittest.main()
