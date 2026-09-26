"""Fit one positive temperature per task using calibration data only."""
import argparse
import copy
import json
import numpy as np
from qwenlab.common import ROOT, sha
from qwenlab.prepare_v2 import read_rows, write_rows

def probabilities(logits, temperature):
    z=np.asarray(logits,dtype=np.float64)/temperature
    z=z-z.max(axis=-1,keepdims=True)
    exp=np.exp(z)
    return exp/exp.sum(axis=-1,keepdims=True)

def fit(rows, task):
    pairs=[(r['predictions'][task],r['labels'][task]) for r in rows
           if not r.get('error') and 'candidate_logits' in r['predictions'].get(task,{})]
    if len(pairs)<10: return {'temperature':1.0,'n':len(pairs),'status':'insufficient, unchanged'}
    values=np.array([p['candidate_logits'] for p,_ in pairs])
    targets=np.array([p['ordered_keys'].index(y) for p,y in pairs])
    temperatures=np.exp(np.linspace(np.log(.05),np.log(50),1000))
    losses=[-np.log(np.maximum(probabilities(values,t)[np.arange(len(pairs)),targets],1e-12)).mean() for t in temperatures]
    index=int(np.argmin(losses))
    return {'temperature':float(temperatures[index]),'n':len(pairs),'nll':float(losses[index]),
            'status':'fitted','at_search_boundary':index in (0,len(temperatures)-1)}

def apply(rows, fitted):
    output=copy.deepcopy(rows)
    for row in output:
        for task,pred in row.get('predictions',{}).items():
            if 'candidate_logits' not in pred: continue
            probs=probabilities(pred['candidate_logits'],fitted[task]['temperature']).tolist()
            pred['probabilities']=dict(zip(pred['ordered_keys'],probs))
            # A scalar positive temperature must not change argmax.
            if pred['choice']!=pred['ordered_keys'][int(np.argmax(probs))]: raise AssertionError('Ranking changed')
    return output

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',required=True); p.add_argument('--calibration-run',required=True)
    args=p.parse_args(); source=ROOT/'results/runs'/args.run; cal=ROOT/'results/runs'/args.calibration_run
    out=ROOT/'results/runs'/(args.run+'-calibrated')
    if out.exists(): raise FileExistsError('Calibrated output exists')
    out.mkdir(parents=True)
    metadata={}
    for name in ('massive','business'):
        path=cal/f'{name}-calibration.jsonl'; rows=read_rows(path)
        if any(r.get('error') for r in rows): raise ValueError('Calibration has errors')
        fitted={task:fit(rows,task) for task in rows[0]['labels']}
        metadata[name]={'source_sha256':sha(path),'tasks':fitted}
        write_rows(out/f'{name}-test.jsonl',apply(read_rows(source/f'{name}-test.jsonl'),fitted))
    (out/'temperatures.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
