"""Traceable first rewrite batch and complete raw-train work ledger.

Never turns a many-thousand-row pending queue into template-generated gold.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
import re

from qwenlab.common import ROOT, sha
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.joint_v5 import atomic_json
from qwenlab.financial_public_inventory import inventory, summary, INTEGRATED
from qwenlab.financial_pilot import base_input, label, make, protected_pool, normalize, serialize_input, review_markdown
from qwenlab.financial_expansion import check, PUBLIC_TOPICS, PUBLIC_EXCLUSIONS

OUT=ROOT/'data/financial-public-rewrite-v1'
LOCAL=ROOT/'.local/financial-public-rewrite-v1'


def retain_domain_examples(source_rows,used,blocked,existing):
    selected=[]; topics=Counter(); counts=Counter(); dialogs=set()
    seen={normalize(r['input']['message']) for r in existing}
    for s in source_rows:
        if s['already_integrated'] or s['source_id'] in used:continue
        if s['source_id'] in PUBLIC_EXCLUSIONS:continue
        msg=s['source_message'];norm=normalize(msg)
        if re.search('贷款|借款|银行|还款|客服|扣款|信用|身份证|验证码|投诉|自杀|杀人|色情',msg):continue
        if norm in blocked or norm in seen or len(norm)<8:continue
        if s['disposition_suggestion']!='out_of_scope_rewrite_pool':continue
        dataset=s['dataset']
        if dataset=='massive':
            intent=s['source_labels']['intent']
            if intent not in PUBLIC_TOPICS or topics[intent]>=2 or counts[dataset]>=36:continue
            topic,pattern=PUBLIC_TOPICS[intent]
            if intent=='iot_coffee':topic='咖啡饮品或相关设备服务'
            if intent=='play_podcasts':topic='播客播放或播放历史服务'
            if not re.search(pattern,msg):continue
            if re.search('活动',msg) and not re.search('展会|演出|音乐会',msg):continue
        else:
            if counts[dataset]>=24 or s['source_dialog_id'] in dialogs:continue
            if not re.search('酒店|景点|餐馆|餐厅|地铁|出租车',msg):continue
            topic='旅游出行服务';intent='crosswoz-tourism'
        value=base_input(msg,history=s['source_history'])
        target=label('redirect',f'明确要求{topic}，贷款客服不提供此类服务；合法域外请求只引导，不判违规。')
        if value['history']:target['evidence_paths'].append('input.history')
        r=make(s['source_id'],s['source_group'],value,target,{
            'kind':'public_retained_scope_example','source':s['source_path'],
            'parent_id':s['source_id'],'source_group':s['source_group'],'parent_message':msg,
            'parent_history':s['source_history'],'source_split':'train','source_original_labels':s['source_labels'],
            'origin':'public_original_assistant_annotation','license':'CC-BY-4.0' if dataset=='massive' else 'Apache-2.0',
            'modification':'Original past context and message retained; relabelled for loan-only service scope'})
        r['id']='FIN-R3-K-'+s['source_id'];selected.append(r)
        topics[intent]+=1;counts[dataset]+=1;seen.add(norm)
        if dataset=='crosswoz':dialogs.add(s['source_dialog_id'])
    return selected


def attach_source(row,source):
    """Verify author provenance before adding canonical links; never repair silently."""
    p=row['provenance']
    if p.get('source')!=source['source_path'] or p.get('source_split')!='train':raise ValueError('Wrong source partition/path: '+row['id'])
    if p.get('parent_message')!=source['source_message']:raise ValueError('Original message mismatch: '+row['id'])
    if p.get('parent_history',[])!=source['source_history']:raise ValueError('Original history mismatch: '+row['id'])
    expected_license='CC-BY-4.0' if source['dataset']=='massive' else 'Apache-2.0'
    if p.get('license')!=expected_license:raise ValueError('Missing/incorrect source license: '+row['id'])
    p['source_original_labels']=source['source_labels']
    p['source_group']=source['source_group']
    p['source_dialog_id']=source['source_dialog_id'];p['source_turn_index']=source['source_turn_index']
    p['original_already_processed']=source['already_processed']
    row['scene_family_id']='public-source:'+hashlib.sha256(source['source_group'].encode('utf-8')).hexdigest()[:20]
    p['grouping_note']='Original dialogue/source family; financial semantic themes may need further cross-family merging before any split.'


def stage(source_rows,candidates,old,blocked):
    source_map={s['source_id']:s for s in source_rows}
    accepted=[]; quarantined=[]; seen={serialize_input(r) for r in old}; parents=set()
    for candidate in candidates:
        row=deepcopy(candidate)
        parent=row['provenance']['parent_id']
        if parent not in source_map:raise ValueError('Unknown TRAIN parent')
        source=source_map[parent];attach_source(row,source)
        if source['already_integrated']:raise ValueError('Already integrated parent selected: '+parent)
        if parent in parents:raise ValueError('Repeated selected parent: '+parent)
        parents.add(parent)
        reason=None
        if normalize(source['source_message']) in blocked:reason='original_source_exact_protected_message'
        elif normalize(row['input']['message']) in blocked:reason='rewrite_exact_protected_message'
        elif serialize_input(row) in seen:reason='duplicate_visible_input'
        check([row],set())
        if reason:
            quarantined.append({'id':row['id'],'parent_id':parent,'reason':reason,'case':row});continue
        seen.add(serialize_input(row));accepted.append(row)
    check(old+accepted,blocked)
    return accepted,quarantined


def render(rows):
    (OUT/'review.md').write_text(review_markdown(rows),encoding='utf-8')
    sections=['# 原句与金融客服改写对照','', '当前均为助手候选；先核对迁移依据和新合成状态，再看标签。','']
    for r in rows:
        p=r['provenance']
        sections += [f"## {r['id']}",'',f"- 来源：{p['parent_id']}",
            '- 原话：'+p['parent_message'],
            '- 原历史：'+json.dumps(p.get('parent_history',[]),ensure_ascii=False),
            '- 新话语：'+r['input']['message'],
            '- 新历史：'+json.dumps(r['input']['history'],ensure_ascii=False),
            '- 动作：'+r['annotation']['action'],
            '- 改写依据：'+p.get('rewrite_rationale',p.get('modification','')),
            '- 标注依据：'+r['annotation']['reason'],'']
    (OUT/'before-after.md').write_text('\n'.join(sections),encoding='utf-8')


def build(expected_previous=None):
    previous=None
    if OUT.exists():
        if expected_previous is None or sha(OUT/'cases.jsonl')!=expected_previous:
            raise FileExistsError('Existing batch: validate instead of overwriting')
        previous=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
        if previous['cases_sha256']!=expected_previous:raise ValueError('Unreviewed edits cannot be overwritten')
    from qwenlab.financial_rewrite_massive import rows as massive_rows
    from qwenlab.financial_rewrite_crosswoz import rows as cross_rows
    src=inventory();info=summary(src);old=read_rows(ROOT/INTEGRATED)
    blocked,_,protected=protected_pool()
    rewrites=massive_rows()+cross_rows()
    used={r['provenance']['parent_id'] for r in rewrites}
    kept=retain_domain_examples(src,used,blocked,old+rewrites)
    accepted,quarantined=stage(src,rewrites+kept,old,blocked)
    byparent={r['provenance']['parent_id']:r for r in accepted}
    qmap={r['parent_id']:r for r in quarantined}
    ledger=[];status=Counter()
    for s in src:
        sid=s['source_id']; row=dict(s)
        if s['already_integrated']:state='already_integrated_v2'
        elif sid in byparent:
            state='retained_scope_candidate' if byparent[sid]['provenance']['kind']=='public_retained_scope_example' else 'financial_rewrite_candidate'
            row['output_id']=byparent[sid]['id']
        elif sid in qmap:state='quarantined';row['quarantine_reason']=qmap[sid]['reason']
        elif normalize(s['source_message']) in blocked:state='protected_source_do_not_rewrite'
        else:state='pending_financial_adaptation_review'
        row['processing_status']=state;ledger.append(row);status[state]+=1
    LOCAL.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=previous is not None)
    write_rows(LOCAL/'inventory.jsonl',ledger)
    for triage in sorted({r['disposition_suggestion'] for r in ledger}):
        write_rows(LOCAL/(triage+'.jsonl'),[r for r in ledger if not r['already_integrated'] and r['disposition_suggestion']==triage])
    write_rows(LOCAL/'pending.jsonl',[r for r in ledger if r['processing_status']=='pending_financial_adaptation_review'])
    write_rows(LOCAL/'quarantine.jsonl',quarantined)
    write_rows(OUT/'cases.jsonl',accepted)
    atomic_json(OUT/'inventory-summary.json',info)
    result={'version':'financial-public-rewrite-v1',**check(accepted,blocked),
        'selected_rewrites':len(rewrites),'accepted_rewrites':sum(r['provenance']['kind']!='public_retained_scope_example' for r in accepted),
        'accepted_retained':sum(r['provenance']['kind']=='public_retained_scope_example' for r in accepted),
        'quarantined':len(quarantined),'full_inventory_status':dict(status),
        'whole_rewrite_goal_complete':False,'training_release':False,
        'cases_sha256':sha(OUT/'cases.jsonl'),'ledger_sha256':sha(LOCAL/'inventory.jsonl')}
    atomic_json(OUT/'manifest.json',result)
    if previous:
        atomic_json(OUT/'review-revision.json',{'previous_cases_sha256':expected_previous,
            'current_cases_sha256':result['cases_sha256'],
            'review_type':'independent_agent_review_not_human',
            'changes':['CrossWOZ 454-2 and 2720-2 missing application_id',
                       'CrossWOZ 10274-2 missing error_context',
                       'CrossWOZ 391-2 retrieve to clarify: product objects not specified',
                       'Retained coffee/podcast rationale broadened to match observed requests'],
            'training_started':False})
    atomic_json(OUT/'source-code.json',{p:sha(ROOT/p) for p in [
        'src/qwenlab/financial_public_inventory.py','src/qwenlab/financial_public_rewrite.py',
        'src/qwenlab/financial_rewrite_massive.py','src/qwenlab/financial_rewrite_crosswoz.py']})
    atomic_json(OUT/'isolation-audit.json',{'protected_file_hashes':protected,'source_hashes':info['source_sha256'],
        'original_and_rewrite_exact_message_checks':True,'semantic_independence_proven':False,
        'quarantined':[{'id':r['id'],'parent_id':r['parent_id'],'reason':r['reason']} for r in quarantined]})
    render(accepted)
    print(json.dumps(result,ensure_ascii=False,indent=2))


def validate():
    src=inventory(); info=summary(src);blocked,_,protected=protected_pool()
    audit=json.loads((OUT/'isolation-audit.json').read_text(encoding='utf-8'))
    if audit['protected_file_hashes']!=protected or audit['source_hashes']!=info['source_sha256']:raise ValueError('Protected/source files changed')
    rows=read_rows(OUT/'cases.jsonl'); old=read_rows(ROOT/INTEGRATED)
    check(old+rows,blocked)
    # Compare without changing the saved candidate file.
    accepted,q=stage(src,rows,old,blocked)
    if q or accepted!=rows:raise ValueError('Saved candidate is no longer eligible')
    result=check(rows,blocked)
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    result['cases_match_manifest']=sha(OUT/'cases.jsonl')==manifest['cases_sha256']
    result['ledger_match_manifest']=sha(LOCAL/'inventory.jsonl')==manifest['ledger_sha256']
    if not result['cases_match_manifest'] or not result['ledger_match_manifest']:raise ValueError('Manifest digest mismatch; changed data requires explicit version review')
    ledger=read_rows(LOCAL/'inventory.jsonl');source_map={s['source_id']:s for s in src}
    if len(ledger)!=len(src) or {s['source_id'] for s in ledger}!=set(source_map):raise ValueError('Ledger coverage mismatch')
    outputs={r['provenance']['parent_id']:r for r in rows}
    quarantine={r['parent_id']:r for r in audit['quarantined']}
    for item in ledger:
        s=source_map[item['source_id']]; sid=s['source_id']
        if any(item.get(k)!=v for k,v in s.items()):raise ValueError('Ledger source changed: '+sid)
        if s['already_integrated']:expected='already_integrated_v2'
        elif sid in outputs:
            expected='retained_scope_candidate' if outputs[sid]['provenance']['kind']=='public_retained_scope_example' else 'financial_rewrite_candidate'
            if item.get('output_id')!=outputs[sid]['id']:raise ValueError('Ledger output mismatch')
        elif sid in quarantine:expected='quarantined'
        elif normalize(s['source_message']) in blocked:expected='protected_source_do_not_rewrite'
        else:expected='pending_financial_adaptation_review'
        if item['processing_status']!=expected:raise ValueError('Ledger state mismatch')
    if dict(Counter(r['processing_status'] for r in ledger))!=manifest['full_inventory_status']:raise ValueError('Ledger counts mismatch')
    print(json.dumps(result,ensure_ascii=False,indent=2))


def progress():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    print(json.dumps({k:manifest[k] for k in ['whole_rewrite_goal_complete','rows','accepted_rewrites','accepted_retained','quarantined','full_inventory_status']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','validate','progress']);a=p.parse_args()
    {'build':build,'validate':validate,'progress':progress}[a.action]()
