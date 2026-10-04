"""Resumable finite queue for the remaining finance rewrite project.

Jobs store canonical sources once. Draft production and independent semantic
review are separate stages. This module never runs a model or pays an API.
"""
import argparse
from collections import Counter
import json
import re
import random
import uuid
from datetime import datetime,timezone
from qwenlab.common import ROOT,sha
from qwenlab.prepare_v2 import read_rows,write_rows
from qwenlab.joint_v5 import atomic_json
from qwenlab.financial_pilot import base_input,label,protected_pool,normalize,serialize_input
from qwenlab.financial_expansion import check
from qwenlab.financial_public_rewrite import attach_source

BASE=ROOT/'.local/financial-rewrite-completion'
SOURCE=ROOT/'.local/financial-public-rewrite-v1/pending.jsonl'
PROPOSAL_FIELDS={'source_id','message','history','state','action','tool_name','tool_arguments','retrieval_collection','missing_slots','reason','rewrite_rationale'}


def identity(name):
    if not isinstance(name,str) or not name.strip():raise ValueError('Missing author/reviewer identity')
    value=name.removeprefix('/root/')
    if name=='/root':value='root'
    if not re.fullmatch(r'[a-z0-9_]+',value):raise ValueError('Unknown identity spelling')
    return value


def verify_job_sources(job):
    index=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
    if sha(SOURCE)!=index['pending_sha256']:raise ValueError('Pending source changed')
    entry=next(e for e in index['jobs'] if e['job']==job)
    folder=BASE/'jobs'/job
    if sha(folder/'source.jsonl')!=entry['source_sha256']:raise ValueError('Frozen job source changed')
    rows=read_rows(folder/'source.jsonl')
    if len(rows)!=entry['source_count'] or len({r['source_id'] for r in rows})!=len(rows):raise ValueError('Job source count/IDs invalid')
    return rows


def verify_pending_coverage(inventory,pending,expected_count):
    authoritative=[r for r in inventory if r['processing_status']=='pending_financial_adaptation_review']
    by_id={r['source_id']:r for r in authoritative}; derived={r['source_id']:r for r in pending}
    if len(by_id)!=len(authoritative) or len(derived)!=len(pending) or len(by_id)!=expected_count or by_id!=derived:
        raise ValueError('Pending queue does not equal authoritative inventory subset')
    return dict(Counter(r['processing_status'] for r in inventory))


def completion_protection():
    """Expand the old reader without changing any frozen experimental code."""
    blocked,_,hashes=protected_pool()
    original_audit=json.loads((ROOT/'data/financial-public-rewrite-v1/isolation-audit.json').read_text(encoding='utf-8'))
    for name,digest in original_audit['source_hashes'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Original source changed: '+name)
    for name in hashes:
        if name.endswith('.jsonl'):
            for row in read_rows(ROOT/name):
                message=row.get('input',{}).get('message')
                if message:blocked.add(normalize(message))
    protected=BASE/'protection.json'
    snapshot={'file_hashes':hashes,'unique_message_count':len(blocked),
              'old_candidate_hashes':{name:sha(ROOT/name) for name in [
                  'data/financial-actions-text-v2/cases.jsonl',
                  'data/financial-public-rewrite-v1/cases.jsonl']}}
    if protected.exists():
        if json.loads(protected.read_text(encoding='utf-8'))!=snapshot:
            raise ValueError('Protected files/index or frozen candidates changed')
    else:atomic_json(protected,snapshot)
    return blocked


def review_selection(rows):
    """Reproducible random sample plus action/context/risk coverage."""
    ordered=sorted(rows,key=lambda r:r['id']); rng=random.Random(20260930)
    random_ids={r['provenance']['parent_id'] for r in rng.sample(ordered,min(10,len(ordered)))}
    directed={}; strata={}
    for r in ordered:
        sid=r['provenance']['parent_id'];v=r['input'];a=r['annotation'];history=v['history']
        labels=r['provenance'].get('source_original_labels',{})
        source_function=labels.get('intent') or repr(sorted({tuple(act[:2]) for act in labels.get('dialog_acts',[]) if isinstance(act,list)}))
        key=(r['provenance'].get('source'),source_function,a['action'],len(history),v['state']['authenticated'],a['tool_name'])
        strata.setdefault(key,sid)
        risks=[]
        if a['action'] in {'refuse','human','close'}:risks.append('safety_or_close_boundary')
        if a['tool_arguments']:risks.append('grounded_parameter')
        if re.search(r'退款|扣款|撤销|注销|转账|修改|删除|利率|手续费|隐私|不是|不要|改为|上一个|这笔|那笔|提交时间|提交日期|还款日|到账|何时|几点|哪天|什么时候',v['message']):risks.append('scope_or_reference')
        if risks:directed[sid]=risks
    for sid in strata.values():directed.setdefault(sid,[]).append('stratum_coverage')
    return {'seed':20260930,'random_source_ids':sorted(random_ids),
            'directed_source_ids':directed,'required_source_ids':sorted(random_ids|set(directed))}


def proposal_to_row(proposal,source,producer):
    if set(proposal)!=PROPOSAL_FIELDS:raise ValueError('Proposal fields mismatch')
    if proposal['source_id']!=source['source_id']:raise ValueError('Wrong source ID')
    if not isinstance(proposal['rewrite_rationale'],str) or not proposal['rewrite_rationale'].strip():raise ValueError('Missing source transfer rationale')
    value=base_input(proposal['message'],proposal['state'],proposal['history'])
    # base_input defaults must not silently erase invalid empty/truthy values.
    value['state']=proposal['state'];value['history']=proposal['history']
    target=label(proposal['action'],proposal['reason'])
    for key in ['tool_name','tool_arguments','retrieval_collection','missing_slots']:target[key]=proposal[key]
    target['evidence_paths']=['input.message','input.history','input.state','input.capabilities','input.available_tools']
    r={'id':'FIN-R4-'+source['source_id'],'scene_family_id':'pending_canonical_source_group',
       'split':'train_candidate','input':value,'annotation':target,
       'provenance':{'kind':'public_financial_rewrite_completion','source':source['source_path'],
         'parent_id':source['source_id'],'source_split':'train',
         'parent_message':source['source_message'],'parent_history':source['source_history'],
         'license':'CC-BY-4.0' if source['dataset']=='massive' else 'Apache-2.0',
         'origin':'public_structure_model_synthetic_rewrite','producer':producer,
         'rewrite_rationale':proposal['rewrite_rationale'],
         'modification':'Source communication pattern adapted; financial events, context and state are new synthetic assumptions.'},
       'review':{'status':'assistant_draft','human_reviewed_current_version':False,
                 'semantic_review':'not_yet_independently_reviewed'},
       'usage':'candidate_only_not_training_release'}
    attach_source(r,source)
    check([r],set())
    # Natural ellipsis such as “还款。” is useful clarification data; length
    # alone cannot establish whether the financial context is adequate.
    return r


def audit_job(job,filename='drafts.jsonl',producer='assistant_agent'):
    if not re.fullmatch(r'\d{4}',job) or filename not in {'drafts.jsonl','local-drafts.jsonl'}:raise ValueError('Invalid job/file selector')
    folder=BASE/'jobs'/job
    manifest=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
    entry=next(x for x in manifest['jobs'] if x['job']==job)
    if sha(folder/'source.jsonl')!=entry['source_sha256']:raise ValueError('Frozen job source changed')
    source={x['source_id']:x for x in verify_job_sources(job)}
    state=json.loads((folder/'status.json').read_text(encoding='utf-8'))
    author_id=identity(state.get('worker'))
    proposals=read_rows(folder/filename)
    ids=[p.get('source_id') for p in proposals]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate proposal source IDs')
    if set(ids)-set(source):raise ValueError('Proposal not from assigned job')
    blocked=completion_protection()
    old=read_rows(ROOT/'data/financial-actions-text-v2/cases.jsonl')+read_rows(ROOT/'data/financial-public-rewrite-v1/cases.jsonl')
    seen={serialize_input(r):r['id'] for r in old}
    for path in sorted((BASE/'jobs').glob('*/validated.jsonl')):
        if path.parent==folder:continue
        for r in read_rows(path):seen[serialize_input(r)]=r['id']
    valid=[];errors=[]
    for p in proposals:
        sid=p['source_id']
        try:
            r=proposal_to_row(p,source[sid],producer)
            if normalize(source[sid]['source_message']) in blocked:raise ValueError('Protected original message')
            if normalize(r['input']['message']) in blocked:raise ValueError('Protected rewrite message')
            key=serialize_input(r)
            if key in seen:raise ValueError('Duplicate canonical input of '+seen[key])
            seen[key]=r['id'];valid.append(r)
        except (ValueError,TypeError,KeyError) as exc:errors.append({'source_id':sid,'error':str(exc)})
    missing=sorted(set(source)-set(ids))
    if (folder/'validated.jsonl').exists():
        previous=sha(folder/'validated.jsonl')
        revision=folder/'revisions'/previous;revision.mkdir(parents=True,exist_ok=True)
        for name in ['validated.jsonl','structural-audit.json','review.json','review-findings.json']:
            path=folder/name
            if path.exists() and not (revision/name).exists():(revision/name).write_bytes(path.read_bytes())
    write_rows(folder/'validated.jsonl',valid)
    atomic_json(folder/'review-selection.json',review_selection(valid))
    atomic_json(folder/'structural-audit.json',{'draft_file':filename,'draft_sha256':sha(folder/filename),
        'source_count':len(source),'valid':len(valid),'errors':errors,'missing':missing,
        'validated_sha256':sha(folder/'validated.jsonl'),'semantic_review_complete':False,
        'audited_at':datetime.now(timezone.utc).isoformat(),'author_id':author_id,
        'source_sha256':sha(folder/'source.jsonl')})
    state=json.loads((folder/'status.json').read_text(encoding='utf-8'))
    state.update(status='needs_repair' if errors or missing else 'structure_checked',
                 valid_count=len(valid),error_count=len(errors),missing_count=len(missing))
    atomic_json(folder/'status.json',state)
    print(json.dumps({'job':job,'valid':len(valid),'errors':errors,'missing_count':len(missing)},ensure_ascii=False,indent=2))
    return valid,errors


def verify_review(folder,state):
    """Review claims are valid only for the exact structurally checked artifact."""
    audit=json.loads((folder/'structural-audit.json').read_text(encoding='utf-8'))
    review=json.loads((folder/'review.json').read_text(encoding='utf-8'))
    if audit['errors'] or audit['missing']:raise ValueError('Job still requires repair')
    if sha(folder/'validated.jsonl')!=audit['validated_sha256'] or review.get('validated_sha256')!=audit['validated_sha256']:raise ValueError('Review artifact changed')
    if sha(folder/audit['draft_file'])!=audit['draft_sha256']:raise ValueError('Draft changed since audit')
    if review.get('decision')!='pass' or not review.get('reviewer') or review.get('human_review') is not False:raise ValueError('Invalid independent review')
    author=identity(state.get('worker'))
    if author!=audit.get('author_id'):raise ValueError('Audit author identity mismatch')
    if author==identity(review['reviewer']):raise ValueError('Author cannot independently review own draft')
    if audit.get('source_sha256')!=sha(folder/'source.jsonl') or review.get('source_sha256')!=audit['source_sha256']:raise ValueError('Reviewed source changed')
    if review.get('audit_sha256')!=sha(folder/'structural-audit.json'):raise ValueError('Review audit binding changed')
    findings=json.loads((folder/'review-findings.json').read_text(encoding='utf-8'))
    if review.get('findings_sha256')!=sha(folder/'review-findings.json'):raise ValueError('Review findings changed')
    if findings.get('decision')!='pass' or findings.get('validated_sha256')!=audit['validated_sha256']:raise ValueError('Findings do not pass current artifact')
    if findings.get('unresolved_findings')!=[] or review.get('unresolved_findings')!=[]:raise ValueError('Unresolved findings or missing explicit closure')
    if identity(findings.get('reviewer'))!=identity(review['reviewer']):raise ValueError('Reviewers disagree')
    rows=read_rows(folder/'validated.jsonl'); source=read_rows(folder/'source.jsonl')
    ids={r['provenance']['parent_id'] for r in rows}
    if len(rows)!=len(source) or ids!={s['source_id'] for s in source}:raise ValueError('Review not full source coverage')
    reviewed=set(review.get('reviewed_source_ids',[]))
    if set(findings.get('reviewed_source_ids',[]))!=reviewed:raise ValueError('Review source evidence differs')
    if not reviewed<=ids or len(reviewed)<min(10,len(rows)):raise ValueError('Insufficient or wrong review evidence')
    if review.get('mode')=='full_independent_agent_review' and reviewed!=ids:raise ValueError('Full review must cover every source')
    if review.get('mode') not in {'full_independent_agent_review','stratified_independent_agent_review'}:raise ValueError('Unknown review mode')
    if not set(review_selection(rows)['required_source_ids'])<=reviewed:raise ValueError('Required risk/stratum review missing')
    if review.get('unresolved_findings'):raise ValueError('Unresolved review findings')
    return len(rows),len(reviewed)


def accept_job(job):
    if not re.fullmatch(r'\d{4}',job):raise ValueError('Invalid job selector')
    folder=BASE/'jobs'/job
    state=json.loads((folder/'status.json').read_text(encoding='utf-8'))
    if state.get('status') not in {'structure_checked','reviewed'}:raise ValueError('Job is not structurally ready')
    verify_job_sources(job);completion_protection()
    count,sampled=verify_review(folder,state)
    state.update(status='reviewed',review_status='independent_agent_review_pass',
                 accepted_rows=count,individually_reviewed_rows=sampled)
    atomic_json(folder/'status.json',state)
    return state


def source_ledger(rows):
    """Count retained source wording separately from rewritten user messages.

    This comparison makes no claim that the entire input or annotation is
    original: histories, states and labels can still be newly synthesized.
    """
    return [{'source_id':r['provenance']['parent_id'],'candidate_id':r['id'],
             'scene_family_id':r['scene_family_id'],
             'status':('source_message_retained' if normalize(r['input']['message'])==
                       normalize(r['provenance']['parent_message']) else 'rewritten')}
            for r in rows]


def write_export_rows(path,rows):
    """Write hashed export JSONL with the same LF bytes on every OS."""
    with path.open('w',encoding='utf-8',newline='\n') as output:
        for row in rows:
            output.write(json.dumps(row,ensure_ascii=False)+'\n')


def write_parts(folder,rows,part_size=2000):
    """Portable JSONL shards; the local combined file remains audit canonical."""
    if part_size<1:raise ValueError('Invalid part size')
    parts=folder/'parts';parts.mkdir()
    manifest=[]
    for start in range(0,len(rows),part_size):
        name=f'parts/part-{len(manifest)+1:04d}.jsonl'
        batch=rows[start:start+part_size];write_export_rows(folder/name,batch)
        manifest.append({'path':name,'rows':len(batch),'sha256':sha(folder/name)})
    return manifest


def verify_parts(folder,manifest):
    """Validate portable bytes without claiming a new semantic review."""
    import hashlib
    digest=hashlib.sha256();count=0;expected=[]
    parts=manifest.get('parts')
    if not isinstance(parts,list) or not parts:raise ValueError('Missing export parts')
    for i,part in enumerate(parts,1):
        name=f'parts/part-{i:04d}.jsonl'
        if part.get('path')!=name:raise ValueError('Export part order/path invalid')
        path=folder/name;expected.append(path.name)
        if sha(path)!=part['sha256']:raise ValueError('Export part changed')
        data=path.read_bytes();rows=read_rows(path)
        if b'\r' in data or not data.endswith(b'\n') or len(rows)!=part['rows'] or not rows:
            raise ValueError('Export part count or LF newline invalid')
        count+=len(rows);digest.update(data)
    if sorted(p.name for p in (folder/'parts').glob('*.jsonl'))!=expected:raise ValueError('Unexpected export part files')
    if count!=manifest['candidate_rows'] or digest.hexdigest()!=manifest['cases_sha256']:
        raise ValueError('Export parts do not match combined candidates')
    return count


def verify_export(out):
    completion_protection()
    index=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
    if sha(SOURCE)!=index['pending_sha256']:raise ValueError('Frozen export source queue changed')
    original=json.loads((ROOT/'data/financial-public-rewrite-v1/manifest.json').read_text(encoding='utf-8'))
    inventory_path=BASE.parent/'financial-public-rewrite-v1/inventory.jsonl'
    if sha(inventory_path)!=original['ledger_sha256']:raise ValueError('Authoritative inventory changed')
    pending=read_rows(SOURCE)
    counts=verify_pending_coverage(read_rows(inventory_path),pending,index['source_count'])
    if counts!=original['full_inventory_status']:raise ValueError('Original inventory counts changed')
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    for name,key in [('cases.jsonl','cases_sha256'),('source-ledger.jsonl','source_ledger_sha256')]:
        if sha(out/name)!=manifest[key]:raise ValueError('Export artifact changed: '+name)
    if manifest['pending_source_sha256']!=sha(SOURCE):raise ValueError('Export source changed')
    rows=read_rows(out/'cases.jsonl');ledger=read_rows(out/'source-ledger.jsonl')
    if manifest.get('whole_goal_complete') is not True or manifest.get('training_release') is not False or manifest.get('human_reviewed_current_version') is not False:
        raise ValueError('Export completion/release claims invalid')
    if not (len(rows)==len(ledger)==len(pending)==manifest.get('source_rows')==manifest.get('candidate_rows')):
        raise ValueError('Export coverage/counts invalid')
    verify_parts(out,manifest)
    if len({r['id'] for r in rows})!=len(rows) or {r['provenance']['parent_id'] for r in rows}!={r['source_id'] for r in pending}:
        raise ValueError('Export candidate/source IDs invalid')
    expected_ledger=source_ledger(rows)
    if ledger!=expected_ledger:raise ValueError('Export ledger does not match candidates')
    if manifest.get('source_message_status')!=dict(Counter(r['status'] for r in ledger)):
        raise ValueError('Export source message counts mismatch')
    if manifest.get('actions')!=dict(Counter(r['annotation']['action'] for r in rows)) or manifest.get('original_inventory_status')!=counts:
        raise ValueError('Export distribution mismatch')
    review_ids=[item['job'] for item in manifest['reviews']]
    if len(review_ids)!=len(set(review_ids)) or set(review_ids)!={e['job'] for e in index['jobs']}:
        raise ValueError('Export review job coverage incomplete')
    combined=[];entries={e['job']:e for e in index['jobs']}
    for item in manifest['reviews']:
        folder=BASE/'jobs'/item['job']
        if sha(folder/'review.json')!=item['review_sha256'] or sha(folder/'validated.jsonl')!=item['validated_sha256']:raise ValueError('Export review evidence changed')
        if sha(folder/'source.jsonl')!=entries[item['job']]['source_sha256']:raise ValueError('Export job source changed')
        state=json.loads((folder/'status.json').read_text(encoding='utf-8'))
        if state.get('status')!='reviewed':raise ValueError('Export contains unaccepted job')
        verify_review(folder,state);combined.extend(read_rows(folder/'validated.jsonl'))
    if rows!=combined:raise ValueError('Export rows differ from reviewed job contents')
    return manifest


def finalize():
    """Fail closed: only complete, reviewed source coverage may be exported."""
    from copy import deepcopy
    from qwenlab.financial_public_rewrite import validate as validate_previous
    validate_previous()
    index=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
    if sha(SOURCE)!=index['pending_sha256']:raise ValueError('Pending source artifact changed')
    expected=read_rows(SOURCE); source_by_id={r['source_id']:r for r in expected}
    if len(source_by_id)!=len(expected) or len(expected)!=index['source_count']:raise ValueError('Duplicate/count mismatch in pending source')
    previous=json.loads((ROOT/'data/financial-public-rewrite-v1/manifest.json').read_text(encoding='utf-8'))
    inventory_status=verify_pending_coverage(read_rows(BASE.parent/'financial-public-rewrite-v1/inventory.jsonl'),expected,
            previous['full_inventory_status']['pending_financial_adaptation_review'])
    if inventory_status!=previous['full_inventory_status']:raise ValueError('Original inventory status partition differs')
    blocked=completion_protection(); actual_sources={}; rows=[]; reviews=[]
    old=read_rows(ROOT/'data/financial-actions-text-v2/cases.jsonl')+read_rows(ROOT/'data/financial-public-rewrite-v1/cases.jsonl')
    seen={serialize_input(r):r['id'] for r in old}
    for entry in index['jobs']:
        folder=BASE/'jobs'/entry['job'];state=json.loads((folder/'status.json').read_text(encoding='utf-8'))
        if state['status']!='reviewed':raise ValueError('Incomplete job '+entry['job'])
        if sha(folder/'source.jsonl')!=entry['source_sha256']:raise ValueError('Frozen job source changed')
        sources=read_rows(folder/'source.jsonl')
        if len(sources)!=entry['source_count']:raise ValueError('Wrong job source count')
        for s in sources:
            sid=s['source_id']
            if sid in actual_sources or source_by_id.get(sid)!=s:raise ValueError('Repeated/changed/unknown source')
            actual_sources[sid]=s
        verify_review(folder,state)
        review=json.loads((folder/'review.json').read_text(encoding='utf-8'))
        for r in read_rows(folder/'validated.jsonl'):
            s=actual_sources[r['provenance']['parent_id']]
            if normalize(s['source_message']) in blocked or normalize(r['input']['message']) in blocked:raise ValueError('Protected source/target')
            copy=deepcopy(r);attach_source(copy,s)
            if copy!=r:raise ValueError('Source provenance no longer canonical')
            if 'input.history' not in r['annotation']['evidence_paths']:raise ValueError('History evidence missing')
            key=serialize_input(r)
            if key in seen:raise ValueError('Canonical input duplicated with '+seen[key])
            seen[key]=r['id'];rows.append(r)
        reviews.append({'job':entry['job'],'review_sha256':sha(folder/'review.json'),
            'validated_sha256':sha(folder/'validated.jsonl'),'reviewer':review['reviewer'],
            'mode':review['mode'],'reviewed_count':len(review['reviewed_source_ids'])})
    if set(actual_sources)!=set(source_by_id) or len(rows)!=len(expected):raise ValueError('Source coverage not complete')
    check(rows,blocked)
    out=ROOT/'data/financial-public-rewrite-completion-v1'
    if out.exists():
        manifest=verify_export(out)
        if read_rows(out/'cases.jsonl')!=rows:raise ValueError('Existing export differs from validated rows')
        atomic_json(BASE/'completion.json',manifest)
        return manifest
    staging=out.with_name(out.name+'.staging-'+uuid.uuid4().hex)
    staging.mkdir(parents=True)
    write_export_rows(staging/'cases.jsonl',rows)
    parts=write_parts(staging,rows)
    ledger=source_ledger(rows)
    write_export_rows(staging/'source-ledger.jsonl',ledger)
    manifest={'version':'financial-public-rewrite-completion-v1','whole_goal_complete':True,
        'source_rows':len(expected),'candidate_rows':len(rows),'source_groups':len({r['scene_family_id'] for r in rows}),
        'unique_normalized_messages':len({normalize(r['input']['message']) for r in rows}),
        'source_message_status':dict(Counter(r['status'] for r in ledger)),
        'actions':dict(Counter(r['annotation']['action'] for r in rows)),
        'with_history':sum(bool(r['input']['history']) for r in rows),
        'human_reviewed_current_version':False,'training_release':False,
        'jsonl_newline':'LF',
        'semantic_review_note':'Agent review, not human review; provenance groups are not independent real-world scenarios.',
        'cases_sha256':sha(staging/'cases.jsonl'),'source_ledger_sha256':sha(staging/'source-ledger.jsonl'),
        'parts':parts,
        'pending_source_sha256':sha(SOURCE),'reviews':reviews,'original_inventory_status':inventory_status}
    atomic_json(staging/'manifest.json',manifest)
    verify_export(staging)
    staging.rename(out)
    atomic_json(BASE/'completion.json',manifest)
    return manifest


def prepare(target_size=200):
    if BASE.exists():
        saved=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
        if saved['pending_sha256']!=sha(SOURCE):raise ValueError('Source queue changed')
        return progress()
    records=read_rows(SOURCE)
    groups={}
    for r in records:groups.setdefault((r['dataset'],r['source_group']),[]).append(r)
    batches=[];current=[]
    for group in groups.values():
        if current and len(current)+len(group)>target_size:
            batches.append(current);current=[]
        current.extend(group)
    if current:batches.append(current)
    BASE.mkdir(parents=True)
    index=[]
    for i,batch in enumerate(batches,1):
        name=f'{i:04d}';folder=BASE/'jobs'/name;folder.mkdir(parents=True)
        write_rows(folder/'source.jsonl',batch)
        record={'job':name,'source_count':len(batch),'source_sha256':sha(folder/'source.jsonl'),
                'datasets':dict(Counter(r['dataset'] for r in batch)),
                'status':'pending_draft','review_status':'not_reviewed'}
        atomic_json(folder/'status.json',record);index.append(record)
    atomic_json(BASE/'queue.json',{'version':'financial-rewrite-completion-1',
        'pending_sha256':sha(SOURCE),'source_count':len(records),'jobs':index,
        'protected_sources_excluded':True,'whole_goal_complete':False})
    return progress()


def progress():
    index=json.loads((BASE/'queue.json').read_text(encoding='utf-8'))
    jobs=[];reviewed=0;sampled=0
    for entry in index['jobs']:
        path=BASE/'jobs'/entry['job']
        if sha(path/'source.jsonl')!=entry['source_sha256']:raise ValueError('Job source changed')
        state=json.loads((path/'status.json').read_text(encoding='utf-8'))
        if state.get('source_count')!=entry['source_count']:raise ValueError('Job metadata mismatch')
        if state['status']=='reviewed':
            count,checked=verify_review(path,state);reviewed+=count;sampled+=checked
        jobs.append(state)
    report={'source_count':index['source_count'],'jobs':len(jobs),
            'job_status':dict(Counter(r['status'] for r in jobs)),
            'source_status':dict(Counter({s:sum(r['source_count'] for r in jobs if r['status']==s) for s in {r['status'] for r in jobs}})),
            'whole_goal_complete':False,
            'review_passed_sources':reviewed,'individually_agent_reviewed_sources':sampled,
            'next_jobs':[r['job'] for r in jobs if r['status']=='pending_draft'][:8]}
    if (BASE/'completion.json').exists():
        completed=verify_export(ROOT/'data/financial-public-rewrite-completion-v1')
        if completed!=json.loads((BASE/'completion.json').read_text(encoding='utf-8')):raise ValueError('Completion evidence mismatch')
        if reviewed!=index['source_count']:raise ValueError('Completion evidence with incomplete reviews')
        report['whole_goal_complete']=True
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','progress','audit','accept','finalize','verify-parts'])
    p.add_argument('--job');p.add_argument('--draft-file',default='drafts.jsonl');p.add_argument('--producer',default='assistant_agent');a=p.parse_args()
    if a.action=='audit':
        if not a.job:p.error('--job required')
        audit_job(a.job,a.draft_file,a.producer)
    elif a.action=='accept':
        if not a.job:p.error('--job required')
        print(json.dumps(accept_job(a.job),ensure_ascii=False,indent=2))
    elif a.action=='verify-parts':
        out=ROOT/'data/financial-public-rewrite-completion-v1'
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        print(json.dumps({'verified_rows':verify_parts(out,manifest),
            'scope':'portable artifact integrity only, not independent source or semantic review'}))
    else:{'prepare':prepare,'progress':progress,'finalize':finalize}[a.action]()
