"""Bounded vendor-selection evaluation; API outputs must not be used for training."""
import argparse
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime,timezone
from qwenlab.common import ROOT,load_rows,specification,input_state,append_json,sha

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',choices=['business','massive'],required=True)
    p.add_argument('--split',default='test'); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--max-requests',type=int,default=130); p.add_argument('--model',default='jev-latest')
    p.add_argument('--run',default='baseline-v1'); args=p.parse_args()
    rows,data_hash=load_rows(args.dataset,args.split)
    if args.limit: rows=rows[:args.limit]
    if any(r.get('images') for r in rows):
        raise NotImplementedError('This adapter supports text-only vendor evaluation')
    if len(rows)>args.max_requests: raise ValueError('Request cap exceeded before reading key')
    folder=ROOT/'results'/args.run; folder.mkdir(parents=True,exist_ok=True)
    out=folder/f'jev-{args.dataset}-{args.split}.jsonl'
    if out.exists(): raise FileExistsError('Use another --run; existing results are immutable')
    key_path=ROOT/'.local/secrets/jev-api-key.txt'
    key=key_path.read_text(encoding='utf-8-sig').strip()
    if not key or any(c.isspace() for c in key): raise ValueError('Key file must contain one token only')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    spec=specification(args.dataset)
    def call(path,payload=None):
        req=urllib.request.Request('https://api.typesafe.ai'+path,
            data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST' if payload is not None else 'GET')
        # Never follow a redirect with a credential-bearing request.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*unused): return None
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with op.open(req,timeout=60) as response: return json.load(response)
    models=call('/v1/models')
    available=[m['name'] for m in models['models']]
    pinned=[n for n in available if n.startswith('jev-') and n not in ('jev-latest','jev-preview')]
    model=sorted(pinned)[-1] if args.model=='jev-latest' and pinned else args.model
    if model not in available: raise ValueError('Requested model unavailable')
    metadata={'started_utc':datetime.now(timezone.utc).isoformat(),'model_requested':model,'models':models,
        'dataset_sha256':data_hash,'spec':spec,'purpose':'vendor selection only; not training',
        'max_requests':args.max_requests,'retries':0,'endpoint':'https://api.typesafe.ai/v1/systemone'}
    (folder/f'jev-{args.dataset}-{args.split}-meta.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    for i,row in enumerate(rows):
        payload={'model':model,'state':{'policy':spec['policy'],'input':input_state(row)},'questions':{name:{'type':'choice',**q} for name,q in spec['questions'].items()}}
        t=time.perf_counter()
        try:
            body=call('/v1/systemone',payload); elapsed=time.perf_counter()-t
            predictions={}
            for name,q in spec['questions'].items():
                answer=body['answers'][name]; probs=answer['probabilities']
                if set(probs)!=set(q['criteria']) or any(not 0<=v<=1 for v in probs.values()) or abs(sum(probs.values())-1)>.03: raise ValueError('Invalid probability schema')
                if answer['choice'] not in probs: raise ValueError('Invalid choice')
                predictions[name]={'choice':answer['choice'],'probabilities':probs,'provider_confidence':answer.get('confidence')}
            append_json(out,{'id':row['id'],'group':row['group'],'labels':row['labels'],'source':row['source'],'predictions':predictions,
                'elapsed_s':elapsed,'usage':body.get('usage'),'model':body.get('model')})
            print(f"{i+1}/{len(rows)} {row['id']} {elapsed:.2f}s",flush=True)
        except Exception as e:
            # Do not serialize exception text, headers or request objects.
            append_json(out,{'id':row['id'],'labels':row['labels'],'error':type(e).__name__,'status':getattr(e,'code',None),'elapsed_s':time.perf_counter()-t})
            print('request failed',type(e).__name__,getattr(e,'code',None),flush=True)
            if getattr(e,'code',None) in (401,403,402,429): break
    print('saved',out.name,flush=True)
if __name__=='__main__': main()
