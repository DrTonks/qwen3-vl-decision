"""Versioned expansion packaging; original pilot and experiments stay immutable."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import uuid

from qwenlab import financial_supplement_pilot as pilot

ROOT=pilot.ROOT
DATA=ROOT/'data/financial-supplement-expansion-v1'
INHERITED=ROOT/'data/financial-supplement-pilot-v1/reviewed-v1'
FILES=['authoring-new.json','node-contexts.jsonl','node-projections.jsonl','candidates.json','summary.json','REVIEW-new.md']
CODE=['src/qwenlab/financial_supplement_expansion.py','src/qwenlab/financial_supplement_pilot.py',
      'src/qwenlab/financial_service_v2_data.py','src/qwenlab/financial_serve_v2.py','src/qwenlab/financial_prompt_v2.py',
      'configs/support-financial-v2.json']


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def inherited():
    manifest=pilot.read(INHERITED/'manifest.json')
    if manifest['training_eligible'] is not False or manifest['human_reviewed'] is not False:
        raise ValueError('Unexpected inherited eligibility')
    for file,digest in manifest['sources'].items():
        if pilot.sha(ROOT/file)!=digest: raise ValueError('Inherited review dependency changed: '+file)
    for file,digest in manifest['files'].items():
        if pilot.sha(INHERITED/file)!=digest: raise ValueError('Inherited package changed')
    rows=pilot.read(INHERITED/'accepted.json')
    if len(rows)!=158 or any(r['review_status']!='independent_ai_review_accepted' or r['training_eligible'] is not False for r in rows):
        raise ValueError('Expected 158 independently reviewed pilot candidates')
    if any(r['scene_family_id']=='FSP1-G-C08' for r in rows): raise ValueError('Quarantined pilot group cannot return')
    return rows


def validate_authored(rows):
    if not rows or len(rows)>2400 or len({r['id'] for r in rows})!=len(rows): raise ValueError('Invalid new candidate count/identity')
    groups=Counter(r['source_group'] for r in rows)
    if max(groups.values())>4: raise ValueError('Maximum four variants per authored group')
    for r in rows:
        if set(r)!=pilot.FIELDS or not re.fullmatch(r'SE[A-Z]-G\d{3}-[1-4]',r['id']): raise ValueError('Invalid authored schema or ID')
        if r['source_group']!=r['id'].rsplit('-',1)[0]: raise ValueError('Invalid group identity')
        if r['cohort'] not in pilot.COHORTS: raise ValueError('Unknown cohort')
        if r['context'].get('authenticated') is not (r['cohort']!='preauth-robustness'): raise ValueError('Authentication cohort mismatch')
        layers={'current-service':['node-projection','component-message-only'],
                'planned-retrieval':['planned-capability-component'],'preauth-robustness':['preauth-component']}
        if r['input_layer'] not in layers[r['cohort']]: raise ValueError('Wrong input layer')
        if not isinstance(r['label_reason'],str) or len(r['label_reason'].strip())<10: raise ValueError('Missing semantic rationale')


def source_rows(paths):
    rows=[]; owners={}
    for path in paths:
        path=Path(path).resolve()
        if path.parent!=DATA or not re.fullmatch(r'batch-[a-z]+\.authoring\.json',path.name): raise ValueError('Use versioned authoring batch files')
        batch=pilot.read(path)
        for row in batch:
            if row['id'] in owners: raise ValueError('Duplicate source ID')
            owners[row['id']]=relative(path)
        rows.extend(batch)
    validate_authored(rows)
    return rows,owners


def input_conflicts(rows):
    seen={};conflicts=[]
    for row in rows:
        key=json.dumps(row['input'],ensure_ascii=False,sort_keys=True)
        a=row['annotation'];label=(a['action'],a['tool_name'],json.dumps(a['tool_arguments'],sort_keys=True),a['retrieval_collection'])
        if key in seen and seen[key][1]!=label:conflicts.append([seen[key][0],row['id']])
        else:seen[key]=(row['id'],label)
    return conflicts


def compute(paths,backend):
    backend=Path(backend).resolve();spec,policy_hash=pilot.protocol()
    if pilot.sha(backend/'services/customerSupport/policies/support-financial-v2.json')!=policy_hash: raise ValueError('Node policy mismatch')
    authored,owners=source_rows(paths)
    contexts=[dict(id=r['id'],context=r['context']) for r in authored]
    scratch=ROOT/'.local/expansion-replay'/uuid.uuid4().hex;scratch.mkdir(parents=True)
    source=scratch/'context.jsonl';output=scratch/'projected.jsonl'
    try:
        source.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in contexts),encoding='utf-8')
        run=subprocess.run(['node',str(backend/'scripts/export-financial-input.cjs'),str(source),str(output)],cwd=backend,
                           capture_output=True,text=True,encoding='utf-8',timeout=90)
        if run.returncode: raise ValueError('Actual Node export failed: '+run.stderr[:600])
        projected=[json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    finally:
        for p in [source,output]:
            if p.exists():p.unlink()
        scratch.rmdir()
    if len(projected)!=len(authored):raise ValueError('Incomplete projection')
    new=[];errors=[]
    for a,p in zip(authored,projected):
        try:
            row=pilot.materialize(a,p,spec)
            row['provenance']['source_document']=owners[a['id']]
            new.append(row)
        except (ValueError,KeyError,TypeError) as exc:errors.append(dict(id=a['id'],error=str(exc)))
    if errors:raise ValueError('Authoring/Node mismatch; no build published: '+json.dumps(errors,ensure_ascii=False))
    base=inherited();all_rows=base+new
    if len({r['id'] for r in all_rows})!=len(all_rows):raise ValueError('Inherited/new ID collision')
    conflicts=input_conflicts(all_rows)
    if conflicts:raise ValueError('Identical visible input has conflicting targets: '+json.dumps(conflicts))
    summary=pilot.summary(all_rows)
    summary.update(inherited_rows=len(base),new_rows=len(new),new_groups=len({r['scene_family_id'] for r in new}))
    groups=defaultdict(list)
    for row in new:groups[row['scene_family_id']].append(row)
    summary['multi_action_new_groups']=sum(len({r['annotation']['action'] for r in g})>1 for g in groups.values())
    review=pilot.render_review(new,authored).replace('# 首批160条金融客服候选复查','# 金融客服扩充候选复查',1)
    review=review.replace('修改上一级 `authoring.json`','修改来源批次 `batch-*.authoring.json`')
    return {'authoring-new.json':authored,'node-contexts.jsonl':contexts,'node-projections.jsonl':projected,
            'candidates.json':all_rows,'summary.json':summary,'REVIEW-new.md':review}


def write_outputs(out,values):
    for name,value in values.items():
        if name.endswith('.jsonl'): (out/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in value),encoding='utf-8')
        elif name.endswith('.md'): (out/name).write_text(value,encoding='utf-8')
        else:pilot.write(out/name,value)


def build(paths,backend,out):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('New build directory required')
    if out.parent!=DATA:raise ValueError('Build must stay in expansion dataset directory')
    values=compute(paths,backend)
    out.mkdir();write_outputs(out,values)
    sources=[*map(Path,paths),INHERITED/'manifest.json',INHERITED/'accepted.json',*[ROOT/f for f in CODE]]
    pilot.write(out/'manifest.json',dict(version='financial-supplement-expansion-v1',training_eligible=False,human_reviewed=False,
                status='pending_independent_review',policy_sha256=pilot.protocol()[1],authoring_files=[relative(p) for p in paths],
                source_sha256={relative(p):pilot.sha(p) for p in sources},files={f:pilot.sha(out/f) for f in FILES}))
    print(json.dumps(values['summary.json'],ensure_ascii=False))


def verify(out,backend):
    out=Path(out);m=pilot.read(out/'manifest.json')
    if set(m)!={'version','training_eligible','human_reviewed','status','policy_sha256','authoring_files','source_sha256','files'} or set(m['files'])!=set(FILES):
        raise ValueError('Incomplete/unknown build manifest')
    if m['version']!='financial-supplement-expansion-v1' or m['status']!='pending_independent_review' or m['training_eligible'] is not False or m['human_reviewed'] is not False:
        raise ValueError('Invalid draft flags')
    paths=[ROOT/p for p in m['authoring_files']]
    # Validate the authoring allowlist before opening manifest-provided paths.
    source_rows(paths)
    expected={*[relative(p) for p in paths],relative(INHERITED/'manifest.json'),relative(INHERITED/'accepted.json'),*CODE}
    if set(m['source_sha256'])!=expected or m['policy_sha256']!=pilot.protocol()[1]:raise ValueError('Incomplete source/policy binding')
    for file,digest in m['source_sha256'].items():
        if pilot.sha(ROOT/file)!=digest:raise ValueError('Source changed: '+file)
    for file,digest in m['files'].items():
        if pilot.sha(out/file)!=digest:raise ValueError('Build edited: '+file)
    replay=compute(paths,backend)
    for file,expected_value in replay.items():
        actual=((out/file).read_text(encoding='utf-8') if file.endswith('.md') else
                [json.loads(line) for line in (out/file).read_text(encoding='utf-8').splitlines()] if file.endswith('.jsonl') else pilot.read(out/file))
        if actual!=expected_value:raise ValueError('Actual replay differs: '+file)
    return replay['candidates.json']


def token_stats(rows):
    from transformers import AutoTokenizer
    from qwenlab.financial_prompt_v2 import encode
    tokenizer=AutoTokenizer.from_pretrained(ROOT/'models/Qwen3.5-0.8B',local_files_only=True)
    lengths={'action':[],'tool':[]}
    for r in rows:
        for task in ['action']+(['tool'] if r['annotation']['action']=='tool' else []):
            lengths[task].append(len(encode(tokenizer,r,task,max_tokens=2048)['tokens']['input_ids']))
    return {k:dict(count=len(v),minimum=min(v) if v else 0,maximum=max(v) if v else 0,mean=round(sum(v)/len(v),2) if v else 0) for k,v in lengths.items()}


def audit(out,backend):
    out=Path(out)
    if (out/'audit.json').exists():raise FileExistsError('Preserve existing audit')
    rows=verify(out,backend);seen={};duplicates=[]
    for r in rows:
        key=re.sub(r'[^\w\u4e00-\u9fff]','',re.sub(r'\d+','NUM',r['input']['message']))
        # Context differences are meaningful; report message-only duplicates for review, not label equality.
        if key in seen:duplicates.append([seen[key],r['id']])
        seen[key]=r['id']
    report=dict(version='financial-expansion-audit-v1',candidate_sha256=pilot.sha(out/'candidates.json'),
                status='structural_and_token_pass',training_eligible=False,no_truncation=True,model_weights_loaded=False,model_api_requests=0,
                tokens=token_stats(rows),
                message_only_numeric_duplicates=duplicates,independent_semantic_review=False)
    pilot.write(out/'audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='message_only_numeric_duplicates'},ensure_ascii=False))


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['build','verify','audit']);p.add_argument('--backend',required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--sources',type=Path,nargs='+')
    args=p.parse_args()
    if args.command=='build':
        if not args.sources:p.error('--sources required')
        build(args.sources,args.backend,args.out)
    elif args.command=='verify':print(json.dumps(pilot.summary(verify(args.out,args.backend)),ensure_ascii=False))
    else:audit(args.out,args.backend)


if __name__=='__main__':main()
