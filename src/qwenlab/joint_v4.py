"""Full-pass mixed training, batched candidate scoring and frozen evaluation."""
import argparse
import json
import math
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from qwenlab.common import ROOT, input_state, load_json, sha, append_json
from qwenlab.modeling import load_model, specification
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.summarize import metric, paired_ci, percentile

OUT=ROOT/'results/joint-v4'
DATA=ROOT/'data/processed/v4'
CKPT=ROOT/'.local/checkpoints/joint-v4'


def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def encode(tokenizer,row,task,seed=None):
    if row.get('images'): raise NotImplementedError('Text only')
    spec=specification(row['dataset']); q=spec['questions'][task]; keys=list(q['criteria'])
    if seed is not None: random.Random(seed).shuffle(keys)
    symbols='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    ids=[tokenizer.encode(s,add_special_tokens=False) for s in symbols[:len(keys)]]
    if any(len(i)!=1 for i in ids): raise ValueError('Symbols must be single tokens')
    options='\n'.join(f'{s}: {q["criteria"][k]} ({k})' for s,k in zip(symbols,keys))
    messages=[{'role':'system','content':spec['policy']+'\n你正在执行候选分类。只输出一个候选符号，不要解释，不要输出JSON。'},
        {'role':'user','content':json.dumps(input_state(row),ensure_ascii=False)+'\n问题：'+q['instructions']+'\n候选：\n'+options+'\n只输出候选符号：'}]
    text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    tokens=tokenizer(text,add_special_tokens=False)
    if len(tokens['input_ids'])>2048: raise ValueError('No silent truncation')
    return {'tokens':tokens,'keys':keys,'ids':[i[0] for i in ids],'target':keys.index(row['labels'][task]),
        'id':row['id'],'task':task,'dataset':row['dataset']}


def batch_logits(tokenizer,model,examples):
    inputs=tokenizer.pad([x['tokens'] for x in examples],padding=True,return_tensors='pt').to('cuda')
    logits=model(**inputs,logits_to_keep=1,use_cache=False).logits[:,-1].float()
    return [logits[i,x['ids']] for i,x in enumerate(examples)]


def metrics(rows):
    result={'n':len(rows),'tasks':{task:metric(rows,task) for task in ('intent','route','tool') if task in rows[0]['labels']}}
    if 'route' in result['tasks']:
        humans=[r for r in rows if r['labels']['route']=='human']; needed=[r for r in rows if r['labels']['route']=='tool']
        result.update(human_required=len(humans),human_missed=sum(r['predictions']['route']['choice']!='human' for r in humans),
            human_false_positive=sum(r['labels']['route']!='human' and r['predictions']['route']['choice']=='human' for r in rows),
            tool_required=len(needed),joint_tool_correct=sum(r['predictions']['route']['choice']=='tool' and r['predictions']['tool']['choice']==r['labels']['tool'] for r in needed),
            all_fields_correct=sum(all(r['labels'][k]==r['predictions'][k]['choice'] for k in ('intent','route','tool')) for r in rows))
    return result


def predict_rows(tokenizer,model,rows,batch_size=1):
    import torch
    output=[{k:r[k] for k in ('id','group','labels')}|{'predictions':{}} for r in rows]
    items=[(i,encode(tokenizer,r,t)) for i,r in enumerate(rows) for t in (['intent','route','tool'] if r['dataset']=='business' else ['intent'])]
    with torch.inference_mode():
        for start in range(0,len(items),batch_size):
            block=items[start:start+batch_size]; logits=batch_logits(tokenizer,model,[x for _,x in block])
            for (i,x),scores in zip(block,logits):
                probs=scores.softmax(-1).cpu().tolist()
                output[i]['predictions'][x['task']]={'choice':x['keys'][max(range(len(probs)),key=probs.__getitem__)],
                    'probabilities':dict(zip(x['keys'],probs)),'candidate_logits':scores.cpu().tolist(),'ordered_keys':x['keys']}
    for r in output:
        if 'route' in r['predictions']:
            r['raw_tool']=r['predictions']['tool'].copy()
            route=r['predictions']['route']['choice']
            if route!='tool': r['predictions']['tool']={'choice':'none','derived':True}
            r['predictions']['needs_human']={'choice':'yes' if route=='human' else 'no','derived':True}
    return output


def add_adapter(base,cfg):
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    base=prepare_model_for_kbit_training(base,use_gradient_checkpointing=True,gradient_checkpointing_kwargs={'use_reentrant':False})
    targets=[n for n,_ in base.named_modules() if '.language_model.' in n and n.endswith(('.q_proj','.v_proj'))]
    model=get_peft_model(base,LoraConfig(r=cfg['lora_r'],lora_alpha=cfg['lora_alpha'],lora_dropout=cfg['lora_dropout'],target_modules=targets,bias='none',task_type='CAUSAL_LM'))
    if any(p.requires_grad and ('lora_' not in n or 'visual' in n) for n,p in model.named_parameters()): raise ValueError('Unexpected trainable weight')
    return model


def preflight():
    import torch
    cfg=load_json(ROOT/'configs/joint-v4.json'); tok,base=load_model('nf4'); tok.padding_side='left'; base.eval()
    business=read_rows(DATA/'business-dev.jsonl'); public=read_rows(DATA/'massive-dev.jsonl')
    rows=business[::max(1,len(business)//8)][:8]+public[::max(1,len(public)//8)][:8]
    xs=[encode(tok,r,'intent') for r in rows]
    with torch.inference_mode():
        single=[batch_logits(tok,base,[x])[0].cpu() for x in xs]
        batched=[v.cpu() for v in batch_logits(tok,base,xs)]
    differences=[float((a-b).abs().max()) for a,b in zip(single,batched)]
    agreement=sum(a.argmax()==b.argmax() for a,b in zip(single,batched))
    print(json.dumps({'batch_deltas':differences,'choice_agreement':int(agreement),
        'single_choices':[int(x.argmax()) for x in single],'batch_choices':[int(x.argmax()) for x in batched],
        'probability_deltas':[float((a.softmax(-1)-b.softmax(-1)).abs().max()) for a,b in zip(single,batched)]}),flush=True)
    if not all(torch.isfinite(x).all() for x in single+batched): raise AssertionError('Nonfinite inference')
    # NF4/BF16 kernels are batch-shape-sensitive. Record the discrepancy rather
    # than claiming bitwise equivalence. All scored evaluations use batch 1.
    model=add_adapter(base,cfg); model.train(); torch.cuda.reset_peak_memory_stats(); start=time.perf_counter()
    params=[p for p in model.parameters() if p.requires_grad]
    for _ in range(3):
        longest=sorted(xs,key=lambda x:len(x['tokens']['input_ids']),reverse=True)[:cfg['micro_batch']]
        logits=batch_logits(tok,model,longest)
        loss=sum(torch.nn.functional.cross_entropy(v[None,:],torch.tensor([x['target']],device='cuda')) for x,v in zip(longest,logits))/len(logits)
        loss.backward()
        if not all(torch.isfinite(p.grad).all() for p in params if p.grad is not None): raise FloatingPointError('Gradient not finite')
        model.zero_grad(set_to_none=True)
    result={'batch_single_max_logit_delta':max(differences),'candidate_choice_agreement':int(agreement),'n':len(xs),
        'backward_micro_batch':cfg['micro_batch'],'evaluation_batch_size':1,'elapsed_s':time.perf_counter()-start,
        'probability_max_delta':max(float((a.softmax(-1)-b.softmax(-1)).abs().max()) for a,b in zip(single,batched)),
        'peak_allocated_gib':torch.cuda.max_memory_allocated()/2**30,'status':'passed'}
    dump(OUT/'preflight.json',result); print(json.dumps(result),flush=True)


def train():
    import torch
    cfg=load_json(ROOT/'configs/joint-v4.json')
    if CKPT.exists(): raise FileExistsError('Checkpoints already exist')
    CKPT.mkdir(parents=True); rng=random.Random(cfg['seed']); torch.manual_seed(cfg['seed'])
    tok,base=load_model('nf4'); tok.padding_side='left'; model=add_adapter(base,cfg)
    # Every source row is consumed: public intent once; each business row once
    # for each of intent/route/tool. No replacement sampling hides coverage.
    pools={}
    for name in ('massive','business'):
        rows=read_rows(DATA/f'{name}-train.jsonl')
        for task in (['intent','route','tool'] if name=='business' else ['intent']):
            pools[name+'.'+task]=[encode(tok,r,task,rng.randrange(2**31)) for r in rows]
    blocks=[]
    for name,xs in pools.items():
        rng.shuffle(xs)
        blocks.extend((name,xs[i:i+cfg['micro_batch']]) for i in range(0,len(xs),cfg['micro_batch']))
    rng.shuffle(blocks)
    steps=math.ceil(len(blocks)/cfg['gradient_accumulation']); warm=max(1,int(steps*cfg['warmup_fraction']))
    checkpoints={math.ceil(steps*f) for f in cfg['checkpoints']}
    params=[p for p in model.parameters() if p.requires_grad]
    optim=torch.optim.AdamW(params,lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    summary={'config':cfg,'total_steps':steps,'optimizer_steps':0,'examples':{k:len(v) for k,v in pools.items()},
        'trainable_parameters':sum(p.numel() for p in params),'status':'running','uses_jev_outputs':False,'sampled':{},
        'vision':'frozen; no images','base_model':'Qwen/Qwen3-VL-2B-Instruct'}
    dump(OUT/'training-summary.json',summary)
    model.train(); optim.zero_grad(set_to_none=True); sampled=Counter(); start=time.perf_counter(); torch.cuda.reset_peak_memory_stats()
    try:
        for step in range(1,steps+1):
            chunk=blocks[(step-1)*cfg['gradient_accumulation']:step*cfg['gradient_accumulation']]
            scale=min(step/warm,max((steps-step+1)/max(steps-warm,1),0))
            for g in optim.param_groups: g['lr']=cfg['learning_rate']*scale
            losses=[]
            for name,xs in chunk:
                logits=batch_logits(tok,model,xs)
                loss=sum(torch.nn.functional.cross_entropy(v[None,:],torch.tensor([x['target']],device='cuda')) for x,v in zip(xs,logits))/len(xs)
                if not torch.isfinite(loss): raise FloatingPointError('Nonfinite loss')
                (loss*cfg['weights'][name]/len(chunk)).backward(); losses.append(float(loss.detach())); sampled[name]+=len(xs)
            norm=torch.nn.utils.clip_grad_norm_(params,1.)
            if not torch.isfinite(norm): raise FloatingPointError('Nonfinite gradient')
            optim.step(); optim.zero_grad(set_to_none=True)
            log={'step':step,'unweighted_loss':sum(losses)/len(losses),'lr':optim.param_groups[0]['lr'],
                'gradient_norm':norm.item(),'elapsed_s':time.perf_counter()-start}
            append_json(OUT/'train.jsonl',log); summary['optimizer_steps']=step
            if step%25==0: print(json.dumps(log),flush=True)
            if step in checkpoints:
                path=CKPT/f'step-{step}'; model.save_pretrained(path,safe_serialization=True)
                ac=load_json(path/'adapter_config.json'); ac['base_model_name_or_path']='Qwen/Qwen3-VL-2B-Instruct'; dump(path/'adapter_config.json',ac)
                dump(OUT/f'adapter-step-{step}.json',{'config':ac,'weights_sha256':sha(path/'adapter_model.safetensors')})
                summary['sampled']=dict(sampled); dump(OUT/'training-summary.json',summary)
        summary.update(status='complete',sampled=dict(sampled),elapsed_s=time.perf_counter()-start,
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30)
        assert summary['sampled']==summary['examples']
    except Exception as e:
        summary.update(status='failed',error=type(e).__name__); raise
    finally: dump(OUT/'training-summary.json',summary)


def evaluate(variant,splits):
    import torch
    tok,model=load_model('nf4',None if variant=='base' else (CKPT/variant).relative_to(ROOT).as_posix())
    tok.padding_side='left'; model.eval()
    folder=OUT/variant; folder.mkdir(exist_ok=True)
    for split in splits:
        for name in ('business','massive'):
            path=folder/f'{name}-{split}.jsonl'
            if path.exists(): raise FileExistsError(path.name)
            rows=read_rows(DATA/f'{name}-{split}.jsonl'); start=time.perf_counter()
            result=predict_rows(tok,model,rows); elapsed=time.perf_counter()-start
            write_rows(path,result); m=metrics(result); m['batch_eval_wall_s']=elapsed
            dump(folder/f'{name}-{split}-metrics.json',m)
            print(variant,name,split,json.dumps(m),flush=True)
        if split=='test':
            # True request latency: one customer at a time, three serial tasks.
            rows=read_rows(DATA/'business-test.jsonl')[:32]; predict_rows(tok,model,rows[:1])
            latencies=[]
            for row in rows:
                torch.cuda.synchronize(); start=time.perf_counter(); predict_rows(tok,model,[row]); torch.cuda.synchronize()
                latencies.append(time.perf_counter()-start)
            dump(folder/'latency.json',{'scope':'sequential customer requests, three serial intent/route/tool forwards; no model loading',
                'n':len(rows),'p50_s':percentile(latencies,.5),'p95_s':percentile(latencies,.95),'values_s':latencies})


def components(biz,pub):
    return [pub['tasks']['intent']['accuracy'],biz['tasks']['intent']['accuracy'],
        biz['tasks']['route']['macro_f1_gold_supported_classes'],biz['joint_tool_correct']/max(1,biz['tool_required'])]


def select(variants):
    values={v:{n:load_json(OUT/v/f'{n}-dev-metrics.json') for n in ('business','massive')} for v in variants}
    reference=components(values['base']['business'],values['base']['massive']); eligible={}
    for variant,result in values.items():
        score=components(result['business'],result['massive'])
        passes=all(x>=b-.03 for x,b in zip(score,reference)) and result['business']['human_missed']<=values['base']['business']['human_missed']
        eligible[variant]={'components':score,'guardrails_pass':passes,'objective':math.prod(score)**.25}
    winner=max([v for v in variants if eligible[v]['guardrails_pass']],key=lambda v:eligible[v]['objective'])
    dump(OUT/'selection.json',{'selected':winner,'development':values,'selection':eligible}); return winner


def run():
    if OUT.exists(): raise FileExistsError('Experiment already exists')
    OUT.mkdir(parents=True)
    dump(OUT/'protocol.json',{'config':load_json(ROOT/'configs/joint-v4.json'),'data':load_json(DATA/'manifest.json'),
        'source_sha256':{p:sha(ROOT/p) for p in ['src/qwenlab/joint_v4.py','src/qwenlab/joint_data.py','configs/joint-v4.json','configs/decision_spec.json']},
        'test_role':'authored wording-family holdout, shared policy generator, unreviewed; not real-world acceptance',
        'latency':'three serial task prompts per customer; needs_human derived and non-tool route forces tool none'})
    def child(*args): subprocess.run([sys.executable,'-m','qwenlab.joint_v4',*args],cwd=ROOT,check=True)
    child('preflight'); child('evaluate','--variant','base','--splits','dev'); child('train')
    variants=['base']+[p.name for p in sorted(CKPT.glob('step-*'),key=lambda p:int(p.name.split('-')[1]))]
    for v in variants[1:]: child('evaluate','--variant',v,'--splits','dev')
    winner=select(variants)
    for v in dict.fromkeys(['base',winner]): child('evaluate','--variant',v,'--splits','calibration','test')
    print('Completed local joint experiment',winner,flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['run','preflight','train','evaluate']); p.add_argument('--variant',default='base'); p.add_argument('--splits',nargs='+',default=['dev']); a=p.parse_args()
    if a.action=='run': run()
    elif a.action=='preflight': preflight()
    elif a.action=='train': train()
    else: evaluate(a.variant,a.splits)


if __name__=='__main__': main()
