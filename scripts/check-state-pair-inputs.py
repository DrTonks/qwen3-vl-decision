"""CPU-only tokenizer accounting and reconstruction of old training contrasts."""
from collections import Counter
import json
from pathlib import Path
import subprocess

from qwenlab.common import ROOT, sha
from qwenlab import financial_prompt_v2 as prompt
from qwenlab.financial_sampling_freeze import local_tokenizer, tokenizer_files
from qwenlab.financial_state_pair_candidates import DATA, DEFAULT_BACKEND, read, encoded, differences, verify


def main():
    verify(DATA/'build', DEFAULT_BACKEND)
    output=DATA/'checks'; output.mkdir(exist_ok=True)
    target=output/'input-accounting.json'
    if target.exists(): raise FileExistsError('No evidence overwrite')
    rows=read(DATA/'build/candidates.json'); tokenizer=local_tokenizer()
    lengths=[]
    for row in rows:
        record={'id':row['id']}
        for task in ('action','tool'):
            if task=='tool' and row['annotation']['action']!='tool':continue
            record[task]=len(prompt.encode(tokenizer,row,task=task,max_tokens=2048)['tokens']['input_ids'])
        lengths.append(record)
    audit_path=ROOT/'docs/evidence/financial-state-pair-audit-v1/audit.json'
    audit=read(audit_path)
    pairs=[p for p in audit['pairs'] if p['knowledge_profiles']==['no-kb','no-kb']]
    if len(pairs)!=10:raise ValueError('Expected ten old no-KB pairs')
    ids={rid for p in pairs for rid in p['row_ids']}
    pool_path=ROOT/'data/financial-sampling-study-v1/pool-v1/train.json'
    old={r['id']:r for r in read(pool_path) if r['id'] in ids}
    if len(old)!=17:raise ValueError('Expected seventeen training rows')
    contexts=[]
    for rid,row in sorted(old.items()):
        value=row['input']; state={}
        if value['state'].get('pending'):state['pending']=value['state']['pending']
        if value['state'].get('application_id'):state['selectedApplicationId']=value['state']['application_id']
        contexts.append(dict(id=rid,context=dict(message=value['message'],history=value['history'],state=state,
                             authenticated=value['state']['authenticated'],availableTools=value['available_tools'])))
    fixtures=output/'old-training-contexts.jsonl'; projections=output/'old-training-projections.jsonl'
    with fixtures.open('x',encoding='utf-8') as f:
        f.write(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in contexts))
    subprocess.run(['node',str(DEFAULT_BACKEND/'scripts/export-financial-input.cjs'),str(fixtures),str(projections)],
                   capture_output=True,check=True,timeout=60)
    replay=[json.loads(s) for s in projections.read_text(encoding='utf-8').splitlines()]
    projection_report=[]
    for projected in replay:
        before=old[projected['id']]['input']; after=projected['input']
        # Model prompt sorts these lists; normalize order for equivalence only.
        before=json.loads(json.dumps(before)); after=json.loads(json.dumps(after))
        for val in [before,after]:val['available_tools']=sorted(val['available_tools'])
        projection_report.append(dict(id=projected['id'],changed_fields=differences(before,after)))
    report=dict(version='state-pair-input-accounting-v1',candidate_sha256=sha(DATA/'build/candidates.json'),
                script_sha256=sha(Path(__file__)),prompt_sha256=sha(ROOT/'src/qwenlab/financial_prompt_v2.py'),
                tokenizer_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in tokenizer_files()},
                rows=lengths,length_summary={task:dict(count=sum(task in r for r in lengths),
                    minimum=min(r[task] for r in lengths if task in r),maximum=max(r[task] for r in lengths if task in r)) for task in ('action','tool')},
                max_input_tokens=2048,truncated=False,model_weights_loaded=False,model_api_requests=0,
                old_training=dict(audit_sha256=sha(audit_path),pool_sha256=sha(pool_path),pairs=len(pairs),rows=len(old),
                    reconstructed_contexts_sha256=sha(fixtures),node_projections_sha256=sha(projections),
                    note='Reconstructed from train-only inputs; not captured real sessions, not new semantic approval.',
                    projection_matches=sum(not r['changed_fields'] for r in projection_report),details=projection_report),
                training_eligible=False,human_reviewed=False)
    with target.open('xb') as f:f.write(encoded(report))
    print(json.dumps(dict(token_lengths=report['length_summary'],old_training_rows=len(old),
                         projection_matches=report['old_training']['projection_matches']),ensure_ascii=False))


if __name__=='__main__':main()
