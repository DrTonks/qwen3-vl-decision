import json
import math
from collections import Counter
from qwenlab.common import ROOT,load_rows

def main():
    folder=ROOT/'results/baseline-v1'
    def read(name):return {r['id']:r for x in (folder/(name+'.jsonl')).read_text(encoding='utf-8').splitlines() if not (r:=json.loads(x)).get('error')}
    raw=read('qwen-first-business-test'); perm=read('qwen-first-business-test-perm17')
    out={'order_sensitivity':{},'generation_agreement':{},'tool_required':{},'human_errors':{},'cost':{}}
    for task in raw[next(iter(raw))]['predictions']:
        tv=[]; changed=[]
        for id,r in raw.items():
            a=r['predictions'][task]; b=perm[id]['predictions'][task]
            tv.append(sum(abs(v-b['probabilities'][k]) for k,v in a['probabilities'].items())/2)
            if a['choice']!=b['choice']:changed.append(id)
        out['order_sensitivity'][task]={'n':len(raw),'changed':len(changed),'mean_total_variation':sum(tv)/len(tv),'changed_ids':changed}
    for dataset in ('business','massive'):
        first=read(f'qwen-first-{dataset}-test'); gen=read(f'qwen-generate-{dataset}-test')
        out['generation_agreement'][dataset]={task:{'n':len(first),'same':sum(r['predictions'][task]['choice']==gen[id]['predictions'][task]['choice'] for id,r in first.items())} for task in next(iter(first.values()))['predictions']}
    business={r['id']:r for split in ('test','dev','calibration') for r in load_rows('business',split)[0]}
    for method in ('jev','qwen-first'):
        rows=read(method+'-business-test'); required=[r for r in rows.values() if r['labels']['route']=='tool']
        out['tool_required'][method]={'n':len(required),'correct_tool':sum(r['predictions']['tool']['choice']==r['labels']['tool'] for r in required),
            'correct_route_and_tool':sum(r['predictions']['tool']['choice']==r['labels']['tool'] and r['predictions']['route']['choice']=='tool' for r in required)}
        out['human_errors'][method]=[{'id':r['id'],'message':business[r['id']]['message'],'route':r['predictions']['route']['choice'],'flag':r['predictions']['needs_human']['choice']}
            for r in rows.values() if r['labels']['route']=='human' and r['predictions']['route']['choice']!='human']
    usage=Counter(); models=Counter(); calls=0
    for path in (ROOT/'results').glob('*/jev-*.jsonl'):
        if 'gated' in path.name: continue
        for line in path.read_text(encoding='utf-8').splitlines():
            r=json.loads(line)
            if r.get('error'):continue
            calls+=1;usage.update(r.get('usage',{}));models[r.get('model','unknown')]+=1
    out['cost']={'successful_calls':calls,'usage':dict(usage),'actual_response_models':dict(models),
        'estimate_usd_at_0_042_per_million_input':usage['input_tokens']*.042/1e6,
        'note':'Estimate using published list price; actual charge subject to provider console, not balance confirmation.'}
    (folder/'diagnostics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
