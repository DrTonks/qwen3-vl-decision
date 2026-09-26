"""Fit one temperature per task on calibration split only, never using test labels."""
import argparse
import copy
import json
import math
from qwenlab.common import ROOT,append_json,sha

def probabilities(logits,t):
    scaled=[x/t for x in logits]; m=max(scaled)
    ex=[math.exp(x-m) for x in scaled]; total=sum(ex)
    return [v/total for v in ex]

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='baseline-v1');a=p.parse_args()
    folder=ROOT/'results'/a.run
    calpath=folder/'qwen-first-business-calibration.jsonl'
    testpath=folder/'qwen-first-business-test.jsonl'
    cal=[json.loads(x) for x in calpath.read_text(encoding='utf-8').splitlines()]
    test=[json.loads(x) for x in testpath.read_text(encoding='utf-8').splitlines()]
    assert {r['group'] for r in cal}.isdisjoint(r['group'] for r in test)
    out=folder/'qwen-calibrated-business-test.jsonl'
    if out.exists(): raise FileExistsError('Do not overwrite calibrated results')
    temperatures={}
    for task in cal[0]['predictions']:
        def nll(t):
            vals=[]
            for r in cal:
                pred=r['predictions'][task]; gold=pred['ordered_keys'].index(r['labels'][task])
                vals.append(-math.log(max(probabilities(pred['candidate_logits'],t)[gold],1e-12)))
            return sum(vals)/len(vals)
        grid=[math.exp(-2.3+i*4.6/200) for i in range(201)]
        t=min(grid,key=nll);temperatures[task]={'temperature':t,'calibration_nll_before':nll(1),'calibration_nll_after':nll(t)}
    for r in test:
        new=copy.deepcopy(r)
        for task,pred in new['predictions'].items():
            pred['probabilities']=dict(zip(pred['ordered_keys'],probabilities(pred['candidate_logits'],temperatures[task]['temperature'])))
            # positive temperature cannot change argmax; preserve choice and measured inference latency.
        new['postprocess']='temperature scaling; latency copied from raw inference'
        append_json(out,new)
    (folder/'calibration.json').write_text(json.dumps({'temperatures':temperatures,'calibration_sha256':sha(calpath),
        'test_sha256':sha(testpath),'fit':'grid minimum NLL, calibration only; no model weight changes'},indent=2),encoding='utf-8')
    print(json.dumps(temperatures,indent=2))
if __name__=='__main__':main()
