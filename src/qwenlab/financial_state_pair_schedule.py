"""CPU-only, exact-cell replacement schedule; frozen predecessors are read-only."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import random

from qwenlab.common import ROOT, sha
from qwenlab import financial_preauth_schedule as parent
from qwenlab import financial_sampling_freeze as accounting
from qwenlab.financial_sampling_plan import layer_of
from qwenlab.financial_coverage_audit import slots
from qwenlab.financial_state_pair_candidates import DATA as CANDIDATES, read, encoded, pair_report

CONFIG=ROOT/'configs/financial-state-pair-schedule-v1.json'
OUT=ROOT/'data/financial-state-pair-study-v1/schedule-v1'
AUDIT=ROOT/'docs/evidence/financial-state-pair-audit-v1/audit.json'
FILES={'additions.json','plan.json','exposure-ledger.json','replacement-ledger.json','pair-exposure.json','summary.json'}


def cell(row):
    v=row['input'];a=row['annotation']
    if type(v['state']['authenticated']) is not bool:raise ValueError('Explicit authentication boolean required')
    return (layer_of(row),v['state']['authenticated'],bool(v['capabilities']['knowledge_collections']),a['action'],a['tool_name'])


def check_config(cfg):
    expected=dict(version='financial-state-pair-schedule-v1',status='cpu_schedule_design_only',
                  training_enabled=False,training_eligible=False,deployment_enabled=False,model_api_requests=0,
                  seed=20261005,steps=400,batch=8,micro_batch=2,max_input_tokens=2048,
                  max_row_exposure=4,max_group_exposure=16,candidate_exposure_per_half=1,
                  base_schedule='data/financial-preauth-study-v1/schedule-v1/plan.json',
                  inherited_training_design='configs/financial-sampling-study-v1.json',
                  candidate_package='data/financial-state-pair-candidates-v1',
                  preserve_per_position=['layer','authenticated','has_knowledge','action','tool'],
                  protect_old_current_no_kb_pair_ids=True,old_anchor_deadline_step=200)
    for k,v in expected.items():
        if type(cfg.get(k)) is not type(v) or cfg[k]!=v:raise ValueError('Unsupported schedule design: '+k)
    return cfg


def additions(candidates):
    if len(candidates)!=136 or len({r['scene_family_id'] for r in candidates})!=40:raise ValueError('Expected136/40 reviewed candidates')
    out=[]
    for source in candidates:
        if (source.get('split')!='candidate' or source.get('training_eligible') is not False or source.get('human_reviewed') is not False
            or source.get('review_status')!='independent_ai_reviewed_candidate'):
            raise ValueError('Unreviewed or promoted candidate')
        row=deepcopy(source);row['split']='train'
        # Metadata migration only: model input and labels stay byte-equivalent.
        if source['cohort']=='preauth':
            row['cohort']='preauth-robustness';row['input_layer']='preauth-component'
        row['sampling_origin']=dict(candidate_row_sha256=accounting.row_sha(source),
            package='data/financial-state-pair-candidates-v1',purpose='sampling_design_only')
        if row['input']!=source['input'] or row['annotation']!=source['annotation']:raise ValueError('Candidate content changed')
        cell(row);out.append(row)
    accounting.validate_rows(out)
    return out


def fine_bucket(row):
    return (*cell(row),slots(row))


def make_plan(old_rows,new_rows,old_steps,old_pairs,cfg):
    check_config(cfg)
    indexed=accounting.validate_rows(old_rows+new_rows)
    old=[rid for step in old_steps for rid in step]
    if len(old_steps)!=400 or any(len(step)!=8 for step in old_steps) or any(i not in indexed for i in old):
        raise ValueError('Expected valid400x8 parent schedule')
    old_ids={r['id'] for r in old_rows};new_ids={r['id'] for r in new_rows}
    if not set(old)<=old_ids:raise ValueError('Parent schedule contains new/unknown rows')
    anchors={rid for pair in old_pairs for rid in pair['row_ids']}
    if len(old_pairs)!=10 or len(anchors)!=17 or not anchors<=old_ids:raise ValueError('Expected ten frozen pairs / seventeen anchors')
    result=old[:];counts=Counter(result);groups=Counter(indexed[i]['scene_family_id'] for i in result)
    changed=set();changes=[]
    for half in range(2):
        start,end=half*1600,(half+1)*1600
        missing=sorted(anchors-set(old[:1600])) if half==0 else []
        requests=[('old_anchor',i) for i in missing]+[('new_candidate',i) for i in sorted(new_ids)]
        rng=random.Random(cfg['seed']+half)
        shuffled=list(range(start,end));rng.shuffle(shuffled);rank={p:j for j,p in enumerate(shuffled)}
        # Anchor insertions first; shuffled candidate ID order is reproducible.
        candidate_requests=requests[len(missing):];rng.shuffle(candidate_requests)
        requests=requests[:len(missing)]+candidate_requests
        fine=Counter(fine_bucket(indexed[i]) for i in result[start:end])
        original_fine=set(fine)
        for kind,rid in requests:
            target=indexed[rid];target_cell=cell(target);tg=target['scene_family_id'];target_bucket=fine_bucket(target)
            eligible=[]
            for p in range(start,end):
                prior=result[p];donor=indexed[prior];dg=donor['scene_family_id'];db=fine_bucket(donor)
                if p in changed or prior in anchors or cell(donor)!=target_cell:continue
                if counts[rid]+1>cfg['max_row_exposure']:continue
                if groups[tg]+1-(dg==tg)>cfg['max_group_exposure']:continue
                if db!=target_bucket and db in original_fine and fine[db]<=1:continue
                eligible.append(p)
            if not eligible:raise ValueError('No same-cell donor within frozen caps for '+rid)
            p=min(eligible,key=lambda x:(slots(indexed[result[x]])!=slots(target),counts[result[x]]<=1,rank[x]))
            prior=result[p];donor=indexed[prior]
            counts[prior]-=1;counts[rid]+=1;groups[donor['scene_family_id']]-=1;groups[tg]+=1
            fine[fine_bucket(donor)]-=1;fine[target_bucket]+=1
            result[p]=rid;changed.add(p)
            changes.append(dict(exposure_index=p+1,step=p//8+1,half=half+1,kind=kind,
                                old_row_id=prior,new_row_id=rid,cell=list(target_cell),
                                old_missing_slots=slots(donor),new_missing_slots=slots(target)))
    plan=dict(version='financial-state-pair-plan-v1',training_enabled=False,training_eligible=False,
              steps=400,batch=8,step_rows=[result[i:i+8] for i in range(0,3200,8)],
              prefix_200_steps=[result[i:i+8] for i in range(0,1600,8)])
    validate_plan(old_rows,new_rows,old_steps,old_pairs,plan,cfg)
    return plan,sorted(changes,key=lambda r:r['exposure_index'])


def validate_plan(old_rows,new_rows,old_steps,old_pairs,plan,cfg):
    check_config(cfg);indexed=accounting.validate_rows(old_rows+new_rows)
    if plan.get('training_enabled') is not False or plan.get('training_eligible') is not False:raise ValueError('CPU schedule cannot enable training')
    if len(plan['step_rows'])!=400 or any(len(s)!=8 for s in plan['step_rows']):raise ValueError('Invalid plan shape')
    old=[i for s in old_steps for i in s];new=[i for s in plan['step_rows'] for i in s]
    if len(old)!=3200 or any(i not in indexed for i in new):raise ValueError('Invalid schedule row IDs')
    if plan['prefix_200_steps']!=plan['step_rows'][:200]:raise ValueError('Prefix mismatch')
    anchors={rid for p in old_pairs for rid in p['row_ids']};new_ids={r['id'] for r in new_rows}
    if not anchors<=set(new[:1600]):raise ValueError('Old pair not complete by200')
    for before,after in zip(old,new):
        if cell(indexed[before])!=cell(indexed[after]):raise ValueError('Position cell changed')
        if before in anchors and before!=after:raise ValueError('Protected anchor position changed')
    for start in (0,1600):
        counts=Counter(new[start:start+1600])
        if any(counts[rid]!=1 for rid in new_ids):raise ValueError('Candidate must appear once in each half')
        old_buckets={fine_bucket(indexed[i]) for i in old[start:start+1600]}
        new_buckets={fine_bucket(indexed[i]) for i in new[start:start+1600]}
        if not old_buckets<=new_buckets:raise ValueError('Original fine bucket lost')
    if max(Counter(new).values())>cfg['max_row_exposure']:raise ValueError('Row cap exceeded')
    if max(Counter(indexed[i]['scene_family_id'] for i in new).values())>cfg['max_group_exposure']:raise ValueError('Group cap exceeded')


def candidate_verifier():
    spec=importlib.util.spec_from_file_location('state_pair_readiness_verifier',ROOT/'scripts/finalize-state-pair-candidates.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def load_sources():
    parent.verify();old_rows=parent.pool.verify()
    manifest=read(CANDIDATES/'readiness-manifest.json')
    if manifest['status']!='ready_for_sampling_design_only' or manifest['training_eligible'] is not False:raise ValueError('Candidate status changed')
    for name,digest in manifest['files'].items():
        if sha(CANDIDATES/name)!=digest:raise ValueError('Candidate evidence changed')
    for name,digest in manifest['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Candidate source changed')
    checker=candidate_verifier();review,screen,_,_=checker.check_evidence()
    accepted,quarantine=checker.review_rows(read(CANDIDATES/'build/candidates.json'),review,screen)
    if accepted!=read(CANDIDATES/'reviewed-candidates.json') or quarantine!=read(CANDIDATES/'quarantine.json'):raise ValueError('Candidate review replay differs')
    new_rows=additions(accepted)
    old_pairs=[p for p in read(AUDIT)['pairs'] if p['knowledge_profiles']==['no-kb','no-kb']]
    return old_rows,new_rows,read(parent.OUT/'plan.json')['step_rows'],old_pairs


def source_bindings():
    bindings=dict(parent.source_bindings())
    for base,manifest_name in [(parent.OUT,'manifest.json'),(CANDIDATES,'readiness-manifest.json')]:
        manifest=read(base/manifest_name)
        bindings[(base/manifest_name).relative_to(ROOT).as_posix()]=sha(base/manifest_name)
        for name in manifest['files']:
            path=base/name;bindings[path.relative_to(ROOT).as_posix()]=sha(path)
        for name in manifest['sources']:bindings[name]=sha(ROOT/name)
    paths=[CONFIG,Path(__file__),ROOT/'tests/test_financial_state_pair_schedule.py',AUDIT,
           CANDIDATES/'build/manifest.json',ROOT/'src/qwenlab/financial_state_pair_candidates.py',
           ROOT/'scripts/replay-state-pair-decisions.cjs',ROOT/'scripts/screen-financial-expansion-overlap.py',
           ROOT/'src/qwenlab/financial_coverage_audit.py',parent.CONFIG,ROOT/'src/qwenlab/financial_preauth_schedule.py']
    bindings.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    return dict(sorted(bindings.items()))


def compute():
    old_rows,new_rows,old_steps,old_pairs=load_sources();cfg=check_config(read(CONFIG))
    rows=old_rows+new_rows;indexed=accounting.validate_rows(rows)
    plan,changes=make_plan(old_rows,new_rows,old_steps,old_pairs,cfg)
    old=[i for s in old_steps for i in s];new=[i for s in plan['step_rows'] for i in s]
    lengths=accounting.validate_lengths(old_rows,read(accounting.OUT/'token-lengths.json'),2048)
    for rec in read(CANDIDATES/'checks/input-accounting.json')['rows']:
        lengths[rec['id']]={'action_input_tokens':rec['action'],'tool_input_tokens':rec.get('tool')}
    counters=Counter();ledger=[]
    for p,rid in enumerate(new):
        row=indexed[rid];counters[rid]+=1
        ledger.append(dict(exposure_index=p+1,step=p//8+1,microbatch=(p%8)//2+1,position=p%2+1,
                           row_id=rid,row_sha256=accounting.row_sha(row),group=row['scene_family_id'],
                           layer=layer_of(row),occurrence=counters[rid]))
    new_pairs=pair_report(new_rows);pair_ledger=[]
    for kind,pairs in [('new',new_pairs),('old',old_pairs)]:
        for pair in pairs:
            ids=pair['ids'] if kind=='new' else pair['row_ids']
            positions={i:[p//8+1 for p,r in enumerate(new) if r==i] for i in ids}
            pair_ledger.append(dict(origin=kind,ids=ids,strict=pair['strict_single_field'] if kind=='new' else True,
                steps=positions,complete_by_200=all(any(s<=200 for s in pos) for pos in positions.values()),
                complete_in_second_half=all(any(s>200 for s in pos) for pos in positions.values()),
                complete_by_400=all(positions.values()),
                baseline_complete_by_200=all(rid in old[:1600] for rid in ids),
                baseline_complete_by_400=all(rid in old for rid in ids)))
    def distribution(seq):
        return dict(actions=dict(sorted(Counter(indexed[i]['annotation']['action'] for i in seq).items())),
            tools=dict(sorted(Counter(indexed[i]['annotation']['tool_name'] for i in seq if indexed[i]['annotation']['action']=='tool').items())),
            layers=dict(sorted(Counter(layer_of(indexed[i]) for i in seq).items())),
            unique_rows=len(set(seq)),unique_groups=len({indexed[i]['scene_family_id'] for i in seq}),
            max_row_exposure=max(Counter(seq).values()),max_group_exposure=max(Counter(indexed[i]['scene_family_id'] for i in seq).values()),
            preauth_positions=sum(not indexed[i]['input']['state']['authenticated'] for i in seq),
            preauth_unique_rows=len({i for i in seq if not indexed[i]['input']['state']['authenticated']}))
    def tokens(seq):
        action=sum(lengths[i]['action_input_tokens'] for i in seq)
        tool=sum(lengths[i]['tool_input_tokens'] or 0 for i in seq)
        padded_action=padded_tool=0
        for start in range(0,len(seq),2):
            block=seq[start:start+2]
            padded_action+=max(lengths[i]['action_input_tokens'] for i in block)*len(block)
            tool_lengths=[lengths[i]['tool_input_tokens'] for i in block if lengths[i]['tool_input_tokens'] is not None]
            if tool_lengths:padded_tool+=max(tool_lengths)*len(tool_lengths)
        return dict(unpadded_action=action,unpadded_tool=tool,total=action+tool,
                    padded_action=padded_action,padded_tool=padded_tool,padded_total=padded_action+padded_tool)
    new_ids={r['id'] for r in new_rows}
    summary=dict(version='financial-state-pair-schedule-summary-v1',training_enabled=False,training_eligible=False,
        model_weights_loaded=False,model_api_requests=0,evaluation_examples_read=False,
        base_pool_rows=len(old_rows),candidate_rows=len(new_rows),combined_design_rows=len(rows),
        total_positions=len(new),changed_positions=len(changes),unchanged_positions=len(new)-len(changes),
        new_candidate_exposures=sum(i in new_ids for i in new),old_anchor_insertions=sum(c['kind']=='old_anchor' for c in changes),
        old_unique_rows_completely_displaced=len(set(old)-set(new)),
        base=distribution(old),candidate=distribution(new),base_prefix_200=distribution(old[:1600]),candidate_prefix_200=distribution(new[:1600]),
        all_position_cells_preserved=True,all_original_fine_buckets_preserved=True,
        missing_slot_replacements=dict(sorted(Counter(c['old_missing_slots']+' -> '+c['new_missing_slots'] for c in changes).items())),
        tokens=dict(base=tokens(old),candidate=tokens(new),equal_flops_claim=False),
        pair_coverage={origin:dict(pairs=sum(p['origin']==origin for p in pair_ledger),
            strict=sum(p['origin']==origin and p['strict'] for p in pair_ledger),
            complete_by_200=sum(p['origin']==origin and p['complete_by_200'] for p in pair_ledger),
            complete_by_400=sum(p['origin']==origin and p['complete_by_400'] for p in pair_ledger),
            baseline_complete_by_200=sum(p['origin']==origin and p['baseline_complete_by_200'] for p in pair_ledger),
            baseline_complete_by_400=sum(p['origin']==origin and p['baseline_complete_by_400'] for p in pair_ledger)) for origin in ('new','old')},
        interpretation=cfg['interpretation'],historical_result_reused=False)
    return {'additions.json':new_rows,'plan.json':plan,'exposure-ledger.json':ledger,'replacement-ledger.json':changes,
            'pair-exposure.json':pair_ledger,'summary.json':summary}


def prepare():
    if OUT.exists():raise FileExistsError('Never overwrite a frozen schedule')
    before=source_bindings();values=compute()
    if before!=source_bindings():raise ValueError('Sources changed during generation')
    payload={name:encoded(values[name]) for name in sorted(FILES)}
    manifest=dict(version='financial-state-pair-schedule-freeze-v1',training_enabled=False,training_eligible=False,
                  model_weights_loaded=False,model_api_requests=0,sources=before,
                  files={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()})
    OUT.mkdir(parents=True,exist_ok=False)
    for name,data in payload.items():(OUT/name).write_bytes(data)
    if before!=source_bindings():raise ValueError('Sources changed; manifest withheld')
    (OUT/'manifest.json').write_bytes(encoded(manifest))
    return values['summary.json']


def verify():
    manifest=read(OUT/'manifest.json')
    if (manifest.get('version')!='financial-state-pair-schedule-freeze-v1' or manifest.get('training_enabled') is not False
        or manifest.get('training_eligible') is not False or manifest.get('model_api_requests')!=0 or manifest.get('model_weights_loaded') is not False):
        raise ValueError('Invalid CPU schedule manifest')
    if set(manifest['files'])!=FILES or {p.name for p in OUT.iterdir()}!=FILES|{'manifest.json'}:raise ValueError('Unexpected file set')
    if manifest['sources']!=source_bindings():raise ValueError('Source closure changed')
    for name,digest in manifest['files'].items():
        if sha(OUT/name)!=digest:raise ValueError('Frozen output changed')
    values=compute()
    if any((OUT/name).read_bytes()!=encoded(values[name]) for name in FILES):raise ValueError('Byte replay differs')
    if manifest['sources']!=source_bindings():raise ValueError('Sources changed during replay')
    return dict(status='verified',training_enabled=False,changed_positions=values['summary.json']['changed_positions'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','verify']);args=parser.parse_args()
    print(json.dumps(prepare() if args.command=='prepare' else verify(),ensure_ascii=False,indent=2))
