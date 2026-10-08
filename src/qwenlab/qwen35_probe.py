"""Bounded compatibility and speed probe, training-only inputs, no evaluation or API."""
import argparse,json,random,time
from qwenlab.common import ROOT,sha
from qwenlab import financial_train as ft,qwen35_model as qm


def main():
    p=argparse.ArgumentParser();p.add_argument('--steps',type=int,default=50);p.add_argument('--tag',default='probe-50')
    args=p.parse_args()
    if not 1<=args.steps<=50 or not args.tag.replace('-','').isalnum():raise ValueError('Bounded probe only')
    folder=ROOT/'results/financial-qwen35-probe'/args.tag
    if (folder/'summary.json').exists():raise FileExistsError('Keep prior probe results')
    folder.mkdir(parents=True,exist_ok=True)
    import torch
    random.seed(20261002);torch.manual_seed(20261002);torch.cuda.manual_seed_all(20261002)
    cfg=dict(pilot=dict(micro_batch=2,gradient_accumulation=4,action_loss_weight=1.,tool_loss_weight=.75))
    records=ft.training_records()
    sampler=random.Random(20261002)
    indices=list(range(len(records)));sampler.shuffle(indices)
    selected=[records[i] for i in indices[:args.steps*8]]
    tok,model=qm.load(training=True)
    encoded=[dict(action=qm.encode(tok,r,'action',r['action']),
        tool=qm.encode(tok,r,'tool',r['tool_name']) if r['action']=='tool' else None) for r in selected]
    with ft.inference_scorer(model) as scorer:
        for task in ['action','tool']:
            example=qm.encode(tok,selected[0],task)
            inputs={k:torch.tensor([v],device='cuda') for k,v in example['tokens'].items()}
            scorer.scores(inputs,example['ids'])
        projection=dict(projection=scorer.projection,fallback=scorer.fallback_reason)
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=5e-5,weight_decay=.01)
    torch.cuda.reset_peak_memory_stats()
    for step in range(1,args.steps+1):
        model.train();optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize();start=time.perf_counter()
        loss=0.;true_tools=0
        for offset in range(0,8,2):
            block=encoded[(step-1)*8+offset:(step-1)*8+offset+2]
            a,t,n=ft.micro_backward(tok,model,block,cfg);loss+=(a+.75*t)/4;true_tools+=n
        norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite probe gradient')
        optimizer.step();torch.cuda.synchronize()
        value=dict(step=step,loss=loss,gradient_norm=float(norm),true_tool_rows=true_tools,
            elapsed_s=time.perf_counter()-start,peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30)
        ft.append(folder/'steps.jsonl',value);ft.durable_json(folder/'status.json',value)
        print(json.dumps(value),flush=True)
    logs=ft.rows_file(folder/'steps.jsonl')
    result=dict(status='complete',steps=args.steps,sample_positions=len(selected),unique_rows=len({r['id'] for r in selected}),
        trainable_parameters=sum(p.numel() for p in params),projection=projection,
        warm_excluded_steps=min(5,args.steps-1),median_step_s=ft.metrics.percentile([x['elapsed_s'] for x in logs[min(5,args.steps-1):]],.5),
        total_training_s=sum(x['elapsed_s'] for x in logs),peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
        model_source_sha256=sha(ROOT/'configs/qwen35-model-source.json'),
        source_sha256={name:sha(ROOT/name) for name in ['src/qwenlab/qwen35_model.py','src/qwenlab/qwen35_probe.py','src/qwenlab/financial_train.py']},
        evaluation_rows_used=0,model_api_requests=0,adapter_discarded=True)
    ft.durable_json(folder/'summary.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    from qwenlab.joint_v5 import exclusive_lock
    with exclusive_lock('financial-eight-actions-gpu.lock'):main()
