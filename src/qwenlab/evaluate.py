"""Bounded, resumable evaluations. Responses are evaluation artifacts only."""
import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from qwenlab.common import ROOT, append_json, input_state, sha
from qwenlab.modeling import dataset, specification, load_model, predict
from qwenlab.prepare_v2 import read_rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--provider',choices=['qwen','jev'],default='qwen')
    p.add_argument('--precision',choices=['bf16','nf4'],default='bf16')
    p.add_argument('--adapter'); p.add_argument('--run',required=True)
    p.add_argument('--datasets',nargs='+',default=['massive','business','crosswoz'])
    p.add_argument('--split',default='test'); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--workers',type=int,default=3); p.add_argument('--max-requests',type=int,default=3300)
    args=p.parse_args()
    folder=ROOT/'results/runs'/args.run; folder.mkdir(parents=True,exist_ok=True)
    tasks=[(name,dataset(name,args.split)[:args.limit or None]) for name in args.datasets]
    if args.provider=='jev' and sum(len(rows) for _,rows in tasks)>args.max_requests: raise ValueError('Request cap exceeded')
    metadata=vars(args).copy(); metadata['protocol']='compact-v2; route first; tool conditional; human derived'
    metadata['data_manifest_sha256']=sha(ROOT/'data/processed/v2/manifest.json')
    mpath=folder/'metadata.json'
    if mpath.exists() and json.loads(mpath.read_text(encoding='utf-8'))!=metadata: raise ValueError('Run configuration changed')
    mpath.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.provider=='qwen':
        import torch
        tokenizer,model=load_model(args.precision,args.adapter); model.eval()
        predict(tokenizer,model,tasks[0][1][0],'intent') # Warmup is excluded.
        torch.cuda.reset_peak_memory_stats()
    else:
        key=(ROOT/'.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
        if not key or any(c.isspace() for c in key): raise ValueError('Invalid credential format')
    def process(row):
        start=time.perf_counter()
        result={k:row[k] for k in ('id','group','source','labels')}; result['predictions']={}
        spec=specification(row['dataset'])
        try:
            if args.provider=='jev':
                # One request for all questions; same policy/candidates, different API architecture.
                payload={'model':'jev-latest','state':{'policy':spec['policy'],'input':input_state(row)},
                    'questions':{k:{'type':'choice',**v} for k,v in spec['questions'].items() if k!='needs_human'}}
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self,*unused): return None
                op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
                req=urllib.request.Request('https://api.typesafe.ai/v1/systemone',data=json.dumps(payload,ensure_ascii=False).encode(),
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                with op.open(req,timeout=60) as response: body=json.load(response)
                for name,q in payload['questions'].items():
                    answer=body['answers'][name]; probs=answer['probabilities']
                    if set(probs)!=set(q['criteria']) or abs(sum(probs.values())-1)>.03 or any(not 0<=v<=1 for v in probs.values()): raise ValueError('Probability schema invalid')
                    if answer['choice'] not in probs: raise ValueError('Choice schema invalid')
                    result['predictions'][name]={'choice':answer['choice'],'probabilities':probs}
                result.update(usage=body.get('usage'),model=body.get('model'))
            else:
                for name in (['route','intent'] if row['dataset']=='business' else ['intent']):
                    result['predictions'][name]=predict(tokenizer,model,row,name)
                if row['dataset']=='business' and result['predictions']['route']['choice']=='tool':
                    result['predictions']['tool']=predict(tokenizer,model,row,'tool')
            if row['dataset']=='business':
                route=result['predictions']['route']['choice']
                if route!='tool': result['predictions']['tool']={'choice':'none','derived':True}
                result['predictions']['needs_human']={'choice':'yes' if route=='human' else 'no','derived':True}
            result['elapsed_s']=time.perf_counter()-start
        except Exception as e:
            result.update(error=type(e).__name__,status=getattr(e,'code',None),elapsed_s=time.perf_counter()-start)
        return result
    for name,rows in tasks:
        out=folder/f'{name}-{args.split}.jsonl'
        done={r['id'] for r in read_rows(out)} if out.exists() else set()
        todo=[r for r in rows if r['id'] not in done]
        executor=ThreadPoolExecutor(max_workers=args.workers) if args.provider=='jev' else None
        try:
            values=executor.map(process,todo) if executor else map(process,todo)
            for i,result in enumerate(values):
                append_json(out,result)
                if i%25==0 or i==len(todo)-1: print(name,len(done)+i+1,'/',len(rows),'error',result.get('error'),flush=True)
                if result.get('status') in (401,402,403,429): raise RuntimeError('Provider rejected request; stop this run')
                if args.provider=='qwen' and result.get('error'): raise RuntimeError('Local evaluation failed; see structured row')
        finally:
            if executor: executor.shutdown(cancel_futures=True)
    if args.provider=='qwen':
        (folder/'memory.json').write_text(json.dumps({'allocated_gib':torch.cuda.max_memory_allocated()/2**30,
            'reserved_gib':torch.cuda.max_memory_reserved()/2**30},indent=2),encoding='utf-8')

if __name__=='__main__': main()
