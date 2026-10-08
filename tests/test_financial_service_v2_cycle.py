"""Synthetic CPU checks: actual loss, persistence, role isolation and gates."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from collections import Counter
from unittest.mock import patch
from qwenlab import financial_service_v2_cycle as c
from qwenlab import financial_service_v2_metrics as m


def prediction(row,action=None,tool=None):
    action=action or row['annotation']['action']
    def choice(keys,value):
        logits=[5. if k==value else 0. for k in keys];weights=[math.exp(x) for x in logits]
        return dict(choice=value,logits=logits,probabilities=dict(zip(keys,[x/sum(weights) for x in weights])))
    value=dict(id=row['id'],action=action,tool_name=None,action_prediction=choice(c.prompt.SPEC['actions'],action))
    if action=='tool':
        value.update(tool_name=tool or row['annotation']['tool_name'] or 'queryMyCreditScore')
        value['tool_prediction']=choice(c.prompt.SPEC['tools'],value['tool_name'])
    return value


def rows():
    result=[]
    for cohort in ['current-service','planned-retrieval','preauth-robustness']:
        for a in c.prompt.SPEC['actions']:
            if a=='retrieve' and cohort!='planned-retrieval' or a=='tool' and cohort=='preauth-robustness':continue
            result.append(dict(id=f'{cohort}-{a}',split='development',cohort=cohort,scene_family_id=f'{cohort}-{a}',
                input=dict(message=a,history=[],state=dict(authenticated=cohort!='preauth-robustness'),available_tools=c.prompt.SPEC['tools'],
                           capabilities=dict(knowledge_collections=['loan_service_docs'] if cohort=='planned-retrieval' else [])),
                annotation=dict(action=a,tool_name='explainApplicationStatus' if a=='tool' else None,tool_arguments={})))
    return result


class ExecutionTests(unittest.TestCase):
    def test_coverage_tail_resume_and_diagnostic_excluded(self):
        cfg=c.ft.read(c.CONFIG);n=cfg['train_rows'];b=cfg['effective_batch']
        batches=[order[i:i+b] for e in range(2) for order in [c.epoch_order(n,cfg['seed'],e)] for i in range(0,n,b)]
        self.assertEqual(len(batches),2940);self.assertEqual(len(batches[1469]),4)
        self.assertEqual(set(Counter(i for block in batches for i in block).values()),{2})
        orders=[c.epoch_order(n,cfg['seed'],e) for e in range(2)]
        for step in [1,50,1470,1471,2939]:
            resumed=[]
            for s in range(step+1,2941):
                e=(s-1)//1470;off=((s-1)%1470)*8
                resumed.append(orders[e][off:off+8])
            self.assertEqual(resumed,batches[step:])
        self.assertEqual(cfg['selection_steps'],[1470,2940]);self.assertNotIn(200,cfg['selection_steps'])

    def test_positive_probe_lr_same_as_main(self):
        cfg=c.ft.read(c.CONFIG);probe=dict(cfg,max_steps=50)
        for s in range(1,51):self.assertGreater(c.learning_rate(s,probe),0);self.assertEqual(c.learning_rate(s,cfg),c.learning_rate(s,probe))

    def test_real_micro_backward_original_row_normalization(self):
        import torch
        orig_tensor=torch.tensor
        def cpu_tensor(*args,**kw):kw.pop('device',None);return orig_tensor(*args,**kw)
        for n in [1,3,4,8]:
            p=orig_tensor(.3,dtype=torch.float64,requires_grad=True)
            block=[dict(action=dict(target=i%2,x=i+1),tool=dict(target=1,x=i+2) if i%2 else None) for i in range(n)]
            def scores(tok,model,items):return [torch.stack([p*x['x'],-p*x['x']]) for x in items]
            expected=sum(torch.nn.functional.cross_entropy(scores(None,None,[r['action']])[0][None,:],orig_tensor([r['action']['target']]))+
                         (.75*torch.nn.functional.cross_entropy(scores(None,None,[r['tool']])[0][None,:],orig_tensor([1])) if r['tool'] else 0) for r in block)/n
            expected.backward();full=p.grad.clone();p.grad=None
            with patch.object(c.ft,'batch_scores',scores),patch.object(torch,'tensor',cpu_tensor):
                for pos in range(0,n,2):
                    small=block[pos:pos+2]
                    c.ft.micro_backward(None,None,small,dict(pilot=dict(action_loss_weight=1.,tool_loss_weight=.75,gradient_accumulation=n/len(small))))
            self.assertTrue(torch.allclose(p.grad,full,atol=1e-12))

    def test_tool_called_only_after_predicted_action(self):
        calls=[]
        def fake(tok,scorer,row,task):
            calls.append(task);return dict(choice='answer',input_tokens=10,elapsed_s=.1)
        r=c.ft.predict_request(None,None,{'id':'x','annotation':{'action':'tool'}},fake)
        self.assertEqual(calls,['action']);self.assertIsNone(r['tool_name'])

    def test_holdout_gates_precede_data_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=c.Run();run.out=Path(tmp)
            c.ft.durable_json(run.out/'protocol.json',{})
            c.ft.durable_json(run.out/'selection.json',dict(passed=False))
            with patch.object(c,'evaluation_rows') as reader:
                with self.assertRaises(ValueError):c.evaluate(run,None,None,'step-1470',{},'calibration')
                reader.assert_not_called()
            c.ft.durable_json(run.out/'selection.json',dict(passed=True,selected='step-1470',protocol_sha256=run.protocol_hash()))
            with patch.object(c,'evaluation_rows') as reader:
                with self.assertRaises(ValueError):c.evaluate(run,None,None,'step-1470',{},'final')
                with self.assertRaises(ValueError):c.evaluate(run,None,None,'step-200',{},'calibration')
                reader.assert_not_called()

    def test_namespace_does_not_accept_old_or_unbounded_experiments(self):
        for name in ['../x','financial-qwen35-v1','financial-service-v2-other']:
            with self.assertRaises(ValueError):c.Run(name)

    def test_atomic_checkpoint_restores_optimizer_rng_and_detects_corruption(self):
        import torch
        from safetensors.torch import save_file,load_file
        from qwenlab.joint_v5 import restore_rng
        class Toy(torch.nn.Linear):
            def save_pretrained(self,path,safe_serialization=True):
                save_file(self.state_dict(),str(path/'adapter_model.safetensors'))
                c.ft.durable_json(path/'adapter_config.json',dict(base_model_name_or_path='placeholder'))
        def update(model,opt):
            opt.zero_grad();x=torch.nn.functional.dropout(torch.ones(4,2),p=.2,training=True)
            loss=model(x).square().mean();loss.backward();opt.step()
        with tempfile.TemporaryDirectory(dir=c.ROOT/'.local') as tmp:
            run=c.Run();run.out=Path(tmp)/'out';run.checkpoints=Path(tmp)/'checkpoints'
            c.ft.durable_json(run.out/'protocol.json',{})
            torch.manual_seed(42);model=Toy(2,1);opt=torch.optim.AdamW(model.parameters(),lr=.01)
            update(model,opt);saved=c.checkpoint(run,model,opt,1,dict(step=1))
            update(model,opt);expected=copy.deepcopy(model.state_dict())
            state=torch.load(saved/'training-state.pt',weights_only=False)
            model2=Toy(2,1);model2.load_state_dict(load_file(str(saved/'adapter_model.safetensors')))
            opt2=torch.optim.AdamW(model2.parameters(),lr=.01);opt2.load_state_dict(state['optimizer']);restore_rng(state['rng']);update(model2,opt2)
            for k,v in model2.state_dict().items():self.assertTrue(torch.equal(v,expected[k]))
            (saved/'adapter_model.safetensors').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):c.ft.validate_checkpoint(run,saved)

    def test_current_and_preauth_gates_cannot_be_hidden_in_totals(self):
        rr=rows();perfect=[prediction(r) for r in rr];wrong=[prediction(r,'answer') for r in rr]
        with patch.object(m,'bootstrap',return_value={}):
            base=m.evaluate(rr,wrong,'a'*64,'b'*64);good=m.evaluate(rr,perfect,'a'*64,'b'*64)
            self.assertTrue(m.development_gate(base,good,c.ft.read(c.CONFIG))['passed'])
            altered=copy.deepcopy(perfect);idx=next(i for i,r in enumerate(rr) if r['cohort']=='preauth-robustness' and r['annotation']['action']=='answer')
            altered[idx]=prediction(rr[idx],'tool','queryMyCreditScore')
            result=m.development_gate(base,m.evaluate(rr,altered,'a'*64,'b'*64),c.ft.read(c.CONFIG))
            self.assertIn('preauth_tool_action',result['failures'])

    def test_cluster_uncertainty_and_probabilities(self):
        rr=rows();pred=[prediction(r) for r in rr]
        self.assertEqual(m.bootstrap(rr,pred,20)['intervals']['action_accuracy']['low'],1)
        self.assertLess(m.wilson(14,14)[0],.95)
        p=copy.deepcopy(pred[0]);p['action_prediction']['logits'][0]=float('nan')
        with self.assertRaises(ValueError):m.validate_prediction(p)
        p=copy.deepcopy(pred[0]);p['action_prediction']['probabilities']={k:1/8 for k in c.prompt.SPEC['actions']}
        with self.assertRaises(ValueError):m.validate_prediction(p)

    def test_cache_rejects_wrong_labels_and_tool_supervision(self):
        keys=c.prompt.SPEC['actions'];r=dict(id='r1',action='answer',tool_name=None)
        ex=dict(action=dict(id='r1',task='action',keys=keys,target=keys.index('answer'),tokens={'input_ids':[42]}),tool=None)
        c.check_encoded([ex],[r]);ex['action']['target']=0
        with self.assertRaises(ValueError):c.check_encoded([ex],[r])

    def test_empty_calibration_acceptance_stops_final_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=c.Run();run.out=Path(tmp);selected=dict(selected='step-1470',passed=True)
            rr=[r for r in rows() if r['annotation']['action']=='human'];pred=[prediction(r,'answer') for r in rr]
            c.durable_json(run.out/'protocol.json',{})
            folder=run.out/'calibration/step-1470';folder.mkdir(parents=True)
            for p in pred:c.ft.append(folder/'predictions.jsonl',p)
            protocol={'config':c.ft.read(c.CONFIG),'prompt_sha256':'a'*64}
            with patch.object(c,'evaluation_rows',return_value=rr):
                result=c.calibrate(run,protocol,'step-1470')
                self.assertFalse(result['passed']);self.assertEqual(result['accepted'],0)
            with patch.object(c.qm,'load',return_value=(None,object())),patch.object(c,'evaluate') as evaluate,patch.object(c,'calibrate',return_value=result):
                self.assertFalse(c.holdout(run,protocol,selected))
                self.assertEqual(evaluate.call_count,1)
                self.assertEqual(evaluate.call_args.args[-1],'calibration')


if __name__=='__main__':unittest.main()
