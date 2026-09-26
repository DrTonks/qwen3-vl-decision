"""Offline deterministic consistency gate, no access to labels in decision function."""
import argparse
import copy
import json
from qwenlab.common import ROOT,append_json

def gate(predictions):
    result=copy.deepcopy(predictions)
    if result['route']['choice']!='tool':
        result['tool']={'choice':'none','source':'deterministic_route_gate'}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='baseline-v1');a=p.parse_args()
    folder=ROOT/'results'/a.run
    for provider,source in [('qwen','qwen-first'),('jev','jev')]:
        target=folder/f'{provider}-gated-business-test.jsonl'
        if target.exists():raise FileExistsError('Do not overwrite gate results')
        for line in (folder/f'{source}-business-test.jsonl').read_text(encoding='utf-8').splitlines():
            r=json.loads(line)
            if not r.get('error'):r['predictions']=gate(r['predictions'])
            r['postprocess']='route != tool -> tool=none; latency copied from original inference; tool probability metrics omitted'
            append_json(target,r)
if __name__=='__main__':main()
