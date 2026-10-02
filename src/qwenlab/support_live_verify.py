"""Explicit loopback HTTP replay of frozen cases, no retries or model selection."""
import argparse
from datetime import datetime, timezone
import time
from urllib.parse import urlparse
import requests
from qwenlab.common import input_state, load_json, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows
from qwenlab.joint_v4 import metrics
from qwenlab.serve import POLICY_HASH, PROTOCOL
from qwenlab.summarize import percentile
from qwenlab.support_fresh_eval import DATA, OUT


def run(url, tool_order="frozen"):
    backend_order=["queryLoanProducts","queryMyApplications","queryApplicationDetail","queryMyCreditScore","explainApplicationStatus"]
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path != '/decide' or parsed.username or parsed.password:
        raise ValueError('Only explicit loopback /decide is supported')
    if load_json(OUT/'status.json')['stage'] != 'complete':
        raise ValueError('Finish offline evaluation first')
    for name, expected in load_json(DATA/'freeze.json')['files'].items():
        if sha(DATA/name) != expected: raise ValueError('Frozen data changed')
    session = requests.Session(); session.trust_env = False
    health = session.get(f'{parsed.scheme}://{parsed.netloc}/ready', timeout=10, allow_redirects=False)
    assert health.status_code == 200, 'Unexpected health status or redirect'
    health.raise_for_status(); metadata = health.json()
    if metadata['adapter'] != 'step-2801' or metadata['policyHash'] != POLICY_HASH:
        raise ValueError('Unexpected live adapter/policy')
    assert metadata['protocolVersion'] == PROTOCOL
    assert metadata['projection'] == 'candidate' and not metadata.get('projectionFallback'), 'Candidate projection not active'
    rows = read_rows(DATA/'cases.jsonl')
    offline = read_rows(OUT/'step-2801/predictions.jsonl')
    assert [r['id'] for r in rows] == [r['id'] for r in offline]
    predictions=[]; measurements=[]; differences=[]
    for row, reference in zip(rows, offline):
        start = time.perf_counter()
        value=input_state(row)
        if tool_order=='backend': value['available_tools']=sorted(value['available_tools'],key=backend_order.index)
        response=session.post(url,json={'protocolVersion':PROTOCOL,'policyHash':POLICY_HASH,'input':value},timeout=20, allow_redirects=False)
        elapsed = (time.perf_counter()-start)*1000
        assert response.status_code == 200, 'Unexpected inference status or redirect'
        response.raise_for_status(); result=response.json()
        assert result['protocolVersion'] == PROTOCOL
        assert result['projection'] == 'candidate' and not result.get('projectionFallback'), 'Candidate projection fell back'
        assert result['policyHash'] == POLICY_HASH and result['adapter'] == 'step-2801'
        p=result['predictions']; effective=dict(p)
        if p['route']['choice'] != 'tool': effective['tool']={'choice':'none','derived':True}
        effective['needs_human']={'choice':'yes' if p['route']['choice']=='human' else 'no','derived':True}
        predictions.append({k:row[k] for k in ['id','group','labels']} | {'predictions':effective,'raw_tool':p['tool']})
        for task in ['intent','route','tool']:
            old=reference['raw_tool'] if task=='tool' else reference['predictions'][task]
            if old['choice']!=p[task]['choice']:
                differences.append({'id':row['id'],'task':task,'offline':old['choice'],'live':p[task]['choice']})
        measurements.append({'id':row['id'],'clientHttpMs':elapsed,'inferenceMs':result['inferenceMs'],
            'inputTokens':result['inputTokens'],'projection':result['projection'],'projectionFallback':result.get('projectionFallback')})
    values=[m['clientHttpMs'] for m in measurements]
    report={'tool_order':tool_order,'backend_order':backend_order if tool_order=='backend' else None,'purpose':'post-result single-variable tool-order sensitivity diagnostic' if tool_order=='backend' else 'frozen-input HTTP equivalence', 'created_at':datetime.now(timezone.utc).isoformat(),'metadata':metadata,'n':len(rows),
        'metrics':metrics(predictions),'raw_choice_differences_vs_offline':differences,
        'http_ms':{'p50':percentile(values,.5),'p95':percentile(values,.95)},
        'timing_limitation':'128 mixed scenario lengths, single pass, loopback HTTP; not the historical 32x3 speed population. inferenceMs excludes encoding.',
        'predictions':predictions,'measurements':measurements,'new_jev_calls':0}
    atomic_json(OUT/('live-classifier.json' if tool_order=='frozen' else 'live-tool-order.json'),report)
    print({'n':len(rows),'raw_choice_differences':len(differences),'http_ms':report['http_ms']})


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--tool-order',choices=['frozen','backend'],default='frozen');args=p.parse_args();run(args.url,args.tool_order)
