"""Bounded evaluation-only API reference for the frozen v4 challenge.

No training module imports this module or reads its outputs.
"""
import json
import time
import urllib.request
from qwenlab.common import ROOT, input_state, load_json, append_json, sha
from qwenlab.prepare_v2 import read_rows


def main():
    cfg=load_json(ROOT/'configs/joint-v4.json'); out=ROOT/'results/joint-v4/jev'
    out.mkdir(exist_ok=True); path=out/'business-test.jsonl'; source=ROOT/'data/processed/v4/business-test.jsonl'
    rows=read_rows(source)
    if len(rows)>cfg['jev_max_requests']: raise ValueError('API request cap exceeded')
    if path.exists(): raise FileExistsError('Vendor predictions already exist; no hidden retries')
    key=(ROOT/'.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
    if not key or any(c.isspace() for c in key): raise ValueError('Invalid credential format')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*unused): return None
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def call(endpoint,payload=None):
        req=urllib.request.Request('https://api.typesafe.ai'+endpoint,
            data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with op.open(req,timeout=30) as response: return json.load(response)
    # Pin the same vendor version as v2, rather than silently comparing an
    # updated latest API with cached public benchmark predictions.
    available=call('/v1/models'); model=cfg['jev_model']
    available_names=[r['name'] for r in available['models']]
    requested_model=model
    if model not in available_names:
        (out/'model-availability.json').write_text(json.dumps({'requested':model,'available':available},ensure_ascii=False,indent=2),encoding='utf-8')
        if 'jev-latest' not in available_names: raise ValueError('No compatible vendor alias')
        # The service exposes aliases only. Verify the resolved version on
        # every response before allowing any historical reference reuse.
        requested_model='jev-latest'
    spec=load_json(ROOT/'configs/decision_spec.json')
    metadata={'model':model,'requested_model':requested_model,'source_sha256':sha(source),'purpose':'vendor evaluation only, not training',
        'max_requests':cfg['jev_max_requests'],'retries':0,'completed_requests':0,'errors':0,'status':'running'}
    def save(): (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    for i,row in enumerate(rows):
        start=time.perf_counter(); result={k:row[k] for k in ('id','group','labels')}; result['predictions']={}
        try:
            payload={'model':requested_model,'state':{'policy':spec['policy'],'input':input_state(row)},
                'questions':{k:{'type':'choice',**v} for k,v in spec['questions'].items() if k!='needs_human'}}
            body=call('/v1/systemone',payload)
            if body.get('model')!=model: raise ValueError('Vendor model version changed')
            for name,q in payload['questions'].items():
                answer=body['answers'][name]; probs=answer['probabilities']
                if set(probs)!=set(q['criteria']) or any(not 0<=v<=1 for v in probs.values()) or abs(sum(probs.values())-1)>.03: raise ValueError('Invalid probabilities')
                if answer['choice'] not in probs: raise ValueError('Invalid choice')
                result['predictions'][name]={'choice':answer['choice'],'probabilities':probs}
            result['raw_tool']=result['predictions']['tool'].copy(); route=result['predictions']['route']['choice']
            if route!='tool': result['predictions']['tool']={'choice':'none','derived':True}
            result['predictions']['needs_human']={'choice':'yes' if route=='human' else 'no','derived':True}
            result.update(model=body.get('model'),usage=body.get('usage'))
        except Exception as exc:
            result.update(error=type(exc).__name__,status=getattr(exc,'code',None)); metadata['errors']+=1
        result['elapsed_s']=time.perf_counter()-start; append_json(path,result)
        metadata['completed_requests']=i+1
        if (i+1)%20==0: save(); print('Evaluated',i+1,'/',len(rows),'errors',metadata['errors'],flush=True)
        if result.get('status') in (401,402,403,429) or metadata['errors']>=3:
            metadata['status']='stopped_on_error'; save(); raise RuntimeError('Vendor run stopped; see error type/status only')
    metadata['status']='complete'; save(); print('Vendor challenge complete',len(rows),flush=True)


if __name__=='__main__': main()
