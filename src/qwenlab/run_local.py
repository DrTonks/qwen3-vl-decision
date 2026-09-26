"""One fixed checkpoint: candidate first-token scoring and greedy short-label generation."""
import argparse
import json
import string
import time
import random
from datetime import datetime,timezone
from qwenlab.common import ROOT,load_rows,specification,input_state,append_json

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',choices=['business','massive'],required=True)
    p.add_argument('--split',default='test'); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--run',default='baseline-v1'); p.add_argument('--permutation',type=int,default=0)
    p.add_argument('--score-only',action='store_true'); args=p.parse_args()
    import torch,transformers
    from transformers import AutoTokenizer,Qwen3VLForConditionalGeneration
    torch.manual_seed(20260926); torch.set_num_threads(6)
    rows,data_hash=load_rows(args.dataset,args.split)
    if args.limit: rows=rows[:args.limit]
    if any(r.get('images') for r in rows):
        raise NotImplementedError('Text-only experiment: add a processor/image pipeline before testing images')
    spec=specification(args.dataset)
    folder=ROOT/'results'/args.run; folder.mkdir(parents=True,exist_ok=True)
    suffix=f'-perm{args.permutation}' if args.permutation else ''
    outputs={mode:folder/f'qwen-{mode}-{args.dataset}-{args.split}{suffix}.jsonl' for mode in (['first'] if args.score_only else ['first','generate'])}
    if any(x.exists() for x in outputs.values()): raise FileExistsError('Use new --run; do not overwrite results')
    checkpoint=ROOT/'models/Qwen3-VL-2B-Instruct'
    tokenizer=AutoTokenizer.from_pretrained(checkpoint,local_files_only=True)
    alphabet=string.ascii_uppercase+string.ascii_lowercase+string.digits
    label_tokens=[]
    for ch in alphabet:
        ids=tokenizer.encode(ch,add_special_tokens=False)
        if len(ids)==1: label_tokens.append((ch,ids[0]))
    if len(label_tokens)<max(len(q['criteria']) for q in spec['questions'].values()): raise ValueError('Insufficient single-token labels')
    t=time.perf_counter()
    model=Qwen3VLForConditionalGeneration.from_pretrained(checkpoint,torch_dtype=torch.bfloat16,
        device_map={'':'cuda:0'},attn_implementation='sdpa',local_files_only=True).eval()
    load_s=time.perf_counter()-t
    def prompt(row,name):
        q=spec['questions'][name]; keys=list(q['criteria'])
        if args.permutation: random.Random(args.permutation).shuffle(keys)
        labels=label_tokens[:len(keys)]
        options='\n'.join(f'{ch}: {q["criteria"][k]} ({k})' for (ch,_),k in zip(labels,keys))
        messages=[{'role':'system','content':spec['policy']+'\n你正在执行候选分类。只输出一个候选符号，不要解释，不要输出JSON。'},
            {'role':'user','content':json.dumps(input_state(row),ensure_ascii=False)+'\n问题：'+q['instructions']+'\n候选：\n'+options+'\n只输出候选符号：'}]
        return tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True),keys,labels
    # Warmup excluded from reported latency.
    warm=tokenizer('你好',return_tensors='pt').to('cuda')
    with torch.inference_mode(): model(**warm,logits_to_keep=1,use_cache=False)
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    meta={'started_utc':datetime.now(timezone.utc).isoformat(),'model':'Qwen/Qwen3-VL-2B-Instruct','dtype':'bfloat16','attention':'sdpa',
        'torch':torch.__version__,'transformers':transformers.__version__,'gpu':torch.cuda.get_device_name(),
        'load_s':load_s,'dataset_sha256':data_hash,'spec':spec,'permutation':args.permutation,'label_tokens':label_tokens,
        'max_new_tokens':8,'max_input_tokens':4096,'generation':'greedy; no logits mask','batch_size':1,
        'checkpoint_manifest':json.loads((checkpoint/'download_manifest.json').read_text(encoding='utf-8'))}
    for i,row in enumerate(rows):
        results={mode:{'id':row['id'],'group':row['group'],'source':row['source'],'labels':row['labels'],'predictions':{},'elapsed_s':0} for mode in outputs}
        for name in spec['questions']:
            text,keys,labels=prompt(row,name)
            for mode in outputs:
                torch.cuda.synchronize(); t=time.perf_counter()
                inputs=tokenizer(text,return_tensors='pt').to('cuda')
                if inputs.input_ids.shape[1]>4096: raise ValueError('Input exceeds declared budget; no silent truncation')
                with torch.inference_mode():
                    if mode=='first':
                        raw=model(**inputs,logits_to_keep=1,use_cache=False).logits[0,-1].float()
                        logits=raw[[idx for _,idx in labels]]
                        probs=logits.softmax(-1).cpu().tolist()
                        mass=raw.softmax(-1)[[idx for _,idx in labels]].sum().item()
                        pred={'choice':keys[max(range(len(probs)),key=probs.__getitem__)],'probabilities':dict(zip(keys,probs)),
                            'candidate_mass':mass,'candidate_logits':logits.cpu().tolist(),'ordered_keys':keys}
                    else:
                        ids=model.generate(**inputs,max_new_tokens=8,do_sample=False)
                        answer=tokenizer.decode(ids[0,inputs.input_ids.shape[1]:],skip_special_tokens=True).strip()
                        mapping={ch:k for (ch,_),k in zip(labels,keys)}
                        pred={'choice':mapping.get(answer,'__invalid__'),'raw_answer':answer}
                torch.cuda.synchronize(); elapsed=time.perf_counter()-t
                pred['elapsed_s']=elapsed; pred['input_tokens']=inputs.input_ids.shape[1]
                results[mode]['predictions'][name]=pred; results[mode]['elapsed_s']+=elapsed
        for mode,path in outputs.items(): append_json(path,results[mode])
        print(f'{i+1}/{len(rows)} {row["id"]} '+str({m:round(r['elapsed_s'],2) for m,r in results.items()}),flush=True)
    meta['peak_allocated_gib']=torch.cuda.max_memory_allocated()/2**30
    meta['peak_reserved_gib']=torch.cuda.max_memory_reserved()/2**30
    (folder/f'qwen-{args.dataset}-{args.split}{suffix}-meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('peak allocated GiB',meta['peak_allocated_gib'],flush=True)
if __name__=='__main__': main()
