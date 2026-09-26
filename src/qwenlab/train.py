"""Small supervised QLoRA pilot. Human/source labels only; never vendor answers."""
import argparse
import json
import random
import time
from collections import defaultdict
from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab.modeling import dataset, prompt, score, load_model

def business_split():
    rows=dataset('business','dev'); groups=defaultdict(list)
    for row in rows: groups[row['labels']['route']].append(row['group'])
    validation=set()
    for route, values in sorted(groups.items()):
        unique=sorted(set(values)); random.Random('20260926'+route).shuffle(unique)
        validation.add(unique[0])
    return [r for r in rows if r['group'] not in validation], [r for r in rows if r['group'] in validation]

def examples(rows):
    return [(r,task) for r in rows for task in (['intent','route','tool'] if r['dataset']=='business' else ['intent'])]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',required=True); p.add_argument('--steps',type=int)
    args=p.parse_args()
    cfg=load_json(ROOT/'configs/train-v2.json')
    if args.steps is not None: cfg['steps']=args.steps
    out=ROOT/'.local/checkpoints'/args.run
    if out.exists(): raise FileExistsError('Training run exists; use a new name')
    out.mkdir(parents=True)
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); rng=random.Random(cfg['seed'])
    tokenizer,base=load_model('nf4')
    base=prepare_model_for_kbit_training(base,use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant':False})
    # Explicit language path prevents accidentally adapting the visual encoder.
    targets=[name for name,module in base.named_modules() if '.language_model.' in name and name.endswith(('.q_proj','.v_proj'))]
    if not targets: raise ValueError('No language attention targets found')
    model=get_peft_model(base,LoraConfig(r=cfg['lora_r'],lora_alpha=cfg['lora_alpha'],
        lora_dropout=cfg['lora_dropout'],target_modules=targets,bias='none',task_type='CAUSAL_LM'))
    trainable=[(name,param) for name,param in model.named_parameters() if param.requires_grad]
    if any('visual' in name or 'merger' in name or 'lora_' not in name for name,_ in trainable):
        raise ValueError('Only language LoRA parameters may train')
    train_biz,dev_biz=business_split()
    public=examples(dataset('massive','train')); business=examples(train_biz)
    dev={'massive':examples(dataset('massive','dev')), 'business':examples(dev_biz)}
    provenance={'config':cfg,'training_rows':{'massive':len(public),'business':len(train_biz)},
        'business_train_ids':[r['id'] for r in train_biz],'business_validation_ids':[r['id'] for r in dev_biz],
        'trainable_parameters':sum(p.numel() for _,p in trainable),'trainable_names':[n for n,_ in trainable],
        'data_manifest_sha256':sha(ROOT/'data/processed/v2/manifest.json'),
        'base_model':'Qwen/Qwen3-VL-2B-Instruct','vision':'frozen, no image training or evaluation',
        'optimizer_steps':0,'status':'running','uses_jev_outputs':False}
    def save_state():
        (out/'training-state.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    save_state()
    optim=torch.optim.AdamW([p for _,p in trainable],lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    best=float('inf'); start=time.perf_counter(); torch.cuda.reset_peak_memory_stats()
    def validate(step):
        nonlocal best
        model.eval(); result={'step':step,'validation':{}}
        with torch.no_grad():
            for name,values in dev.items():
                losses=[]; correct=0
                for row,task in values:
                    inputs,keys,ids=prompt(tokenizer,row,task)
                    logits=score(model,inputs.to('cuda'),ids)
                    y=torch.tensor([keys.index(row['labels'][task])],device='cuda')
                    losses.append(torch.nn.functional.cross_entropy(logits[None,:],y).item())
                    correct+=keys[logits.argmax().item()]==row['labels'][task]
                result['validation'][name]={'n':len(values),'nll':sum(losses)/len(losses),'accuracy':correct/len(values)}
        objective=sum(v['nll'] for v in result['validation'].values())/len(dev)
        result['objective']=objective
        if step>0 and objective<best:
            best=objective; model.save_pretrained(out/'best',safe_serialization=True)
            # PEFT writes the local base path by default. Persist its public ID instead.
            adapter=out/'best/adapter_config.json'; ac=load_json(adapter)
            ac['base_model_name_or_path']='Qwen/Qwen3-VL-2B-Instruct'
            adapter.write_text(json.dumps(ac,ensure_ascii=False,indent=2),encoding='utf-8')
            provenance['best_step']=step; provenance['best_development_nll']=best
        append_json(out/'validation.jsonl',result); print(json.dumps(result),flush=True)
        model.train()
    try:
        validate(0); model.train(); optim.zero_grad(set_to_none=True)
        sampled=defaultdict(int)
        for step in range(1,cfg['steps']+1):
            # Linear warmup and decay, expressed explicitly for auditability.
            scale=min(step/max(cfg['warmup_steps'],1),max((cfg['steps']-step+1)/max(cfg['steps']-cfg['warmup_steps'],1),0))
            for group in optim.param_groups: group['lr']=cfg['learning_rate']*scale
            losses=[]
            for micro in range(cfg['gradient_accumulation']):
                pool=business if rng.random()<cfg['business_sampling_probability'] else public
                row,task=rng.choice(pool); sampled[row['dataset']]+=1
                inputs,keys,ids=prompt(tokenizer,row,task,shuffle_seed=rng.randrange(2**31))
                logits=score(model,inputs.to('cuda'),ids)
                target=torch.tensor([keys.index(row['labels'][task])],device='cuda')
                loss=torch.nn.functional.cross_entropy(logits[None,:],target)
                if not torch.isfinite(loss): raise FloatingPointError('Non-finite loss')
                (loss/cfg['gradient_accumulation']).backward(); losses.append(loss.item())
            grad_norm=torch.nn.utils.clip_grad_norm_([p for _,p in trainable],1.0)
            if not torch.isfinite(grad_norm): raise FloatingPointError('Non-finite gradient')
            optim.step(); optim.zero_grad(set_to_none=True)
            log={'step':step,'loss':sum(losses)/len(losses),'lr':optim.param_groups[0]['lr'],
                'gradient_norm':grad_norm.item(),'elapsed_s':time.perf_counter()-start}
            append_json(out/'train.jsonl',log)
            provenance['optimizer_steps']=step
            if step%5==0: print(json.dumps(log),flush=True)
            if step%cfg['validation_interval']==0 or step==cfg['steps']: validate(step); save_state()
        provenance.update(status='complete',sampled_examples=dict(sampled),elapsed_s=time.perf_counter()-start,
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30)
    except Exception as e:
        provenance.update(status='failed',error=type(e).__name__,elapsed_s=time.perf_counter()-start)
        raise
    finally: save_state()
    print('Training complete',json.dumps({k:v for k,v in provenance.items() if k in ('best_step','peak_allocated_gib','elapsed_s')}),flush=True)

if __name__=='__main__': main()
