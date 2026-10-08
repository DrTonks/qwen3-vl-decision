"""CPU-only replacement of preauth positions; no training or evaluation examples."""
import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import random

from qwenlab.common import ROOT, sha
from qwenlab import financial_sampling_freeze as parent
from qwenlab import financial_sampling_data as pool
from qwenlab import financial_sampling_plan as old_plan
from qwenlab.financial_coverage_audit import segment, slots

CONFIG = ROOT / 'configs/financial-preauth-schedule-v1.json'
OUT = ROOT / 'data/financial-preauth-study-v1/schedule-v1'
FILES = {'plan.json', 'exposure-ledger.json', 'replacement-ledger.json', 'summary.json'}
read, raw = parent.read, parent.json_bytes


def allocate(sizes, total):
    """One per nonempty cell, then integer Hamilton allocation of residuals."""
    sizes = {k:v for k,v in sizes.items() if v}
    if not sizes or any(type(n) is not int or n<1 for n in sizes.values()) or not len(sizes)<=total<=sum(sizes.values()):
        raise ValueError('Insufficient unique bucket capacity')
    out = {k:1 for k in sorted(sizes)}
    remaining = total-len(sizes)
    capacity = sum(sizes.values())-len(sizes)
    if not remaining: return out
    residue = {}
    for k,n in sizes.items():
        quotient, rest = divmod(remaining*(n-1),capacity)
        out[k] += quotient; residue[k]=rest
    left = total-sum(out.values())
    for k in sorted(sizes,key=lambda k:(-residue[k],k))[:left]: out[k]+=1
    if sum(out.values())!=total or any(out[k]>sizes[k] for k in sizes): raise ValueError('Allocation invariant failed')
    return out


def bucket(row):
    return row['annotation']['action'] + '|' + slots(row)


def choose(rows, total, used_groups, seed, max_group=16):
    """Select once per row; never skip an entire bucket or silently relax caps."""
    buckets = defaultdict(list)
    for row in sorted(rows,key=lambda r:r['id']): buckets[bucket(row)].append(row)
    sizes={}
    for key,items in buckets.items():
        capacities=Counter(r['scene_family_id'] for r in items)
        sizes[key]=sum(min(n,max(0,max_group-used_groups[g])) for g,n in capacities.items())
        if not sizes[key]:raise ValueError(f'No remaining group capacity in nonempty bucket: {key}')
    quotas = allocate(sizes,total)
    rng = random.Random(seed); result=[]
    for key in sorted(buckets):
        groups = defaultdict(list)
        for row in buckets[key]: groups[row['scene_family_id']].append(row)
        names = sorted(groups); rng.shuffle(names)
        queues = {}
        for name in names:
            rng.shuffle(groups[name]); queues[name]=deque(groups[name])
        circle = deque(names); picked=0
        while circle and picked<quotas[key]:
            name=circle.popleft(); q=queues[name]
            if not q or used_groups[name]>=max_group: continue
            row=q.popleft(); result.append(row['id']);used_groups[name]+=1;picked+=1
            if q and used_groups[name]<max_group: circle.append(name)
        if picked!=quotas[key]: raise ValueError(f'Group cap prevents bucket quota: {key}')
    rng.shuffle(result)
    return result,quotas


def check_config(cfg):
    expected = dict(version='financial-preauth-schedule-v1',status='cpu_candidate_schedule_only',
        training_enabled=False,training_eligible=False,deployment_enabled=False,model_api_requests=0,
        seed=20261004,steps=400,batch=8,micro_batch=2,max_input_tokens=2048,
        preserve_authenticated_row_ids_and_positions=True,preauth_counts={'no_kb':320,'kb':160},
        per_original_twenty_positions={'no_kb':2,'kb':1},max_row_exposure=4,max_group_exposure=16,repeat_preauth_rows=False)
    for k,v in expected.items():
        if type(cfg.get(k)) is not type(v) or cfg[k]!=v: raise ValueError(f'Unsupported design: {k}')
    if cfg['base_schedule'] != 'data/financial-sampling-study-v1/schedule-v1/stratified-plan.json' or cfg['inherited_training_design']!='configs/financial-sampling-study-v1.json':
        raise ValueError('Wrong frozen parent')
    return cfg


def make_plan(rows, old_steps, cfg):
    check_config(cfg)
    indexed=parent.validate_rows(rows)
    for row in rows: segment(row)  # Explicit booleans; never infer auth from text.
    if len(old_steps)!=400 or any(len(s)!=8 for s in old_steps): raise ValueError('Expected400x8 base schedule')
    flat=[rid for step in old_steps for rid in step]
    if any(rid not in indexed for rid in flat): raise ValueError('Unknown old row')
    positions=[i for i,rid in enumerate(flat) if indexed[rid]['input']['state']['authenticated'] is False]
    if len(positions)!=480: raise ValueError('Expected exactly480 preauth positions')
    position_set=set(positions)
    fixed=[rid for i,rid in enumerate(flat) if i not in position_set]
    groups=Counter(indexed[rid]['scene_family_id'] for rid in fixed)
    if max(groups.values())>16 or max(Counter(fixed).values())>4: raise ValueError('Frozen prefix exceeds caps')
    no_kb=[r for r in rows if segment(r)=='preauth-no-kb']
    excluded={r['scene_family_id'] for r in no_kb}
    kb=[r for r in rows if segment(r)=='preauth-kb' and r['scene_family_id'] not in excluded]
    selected, quotas={},{}
    for j,(name,candidates) in enumerate((('no_kb',no_kb),('kb',kb))):
        selected[name],quotas[name]=choose(candidates,cfg['preauth_counts'][name],groups,cfg['seed']+j)
    queues={k:deque(v) for k,v in selected.items()}
    rng=random.Random(cfg['seed']+2);new=list(flat)
    for start in range(0,len(flat),20):
        loc=[i for i in positions if start<=i<start+20]
        if len(loc)!=3: raise ValueError('Parent must have exactly3 preauth positions per20')
        pattern=['no_kb','no_kb','kb'];rng.shuffle(pattern)
        for i,name in zip(loc,pattern):new[i]=queues[name].popleft()
    if any(queues.values()): raise ValueError('Unconsumed selected rows')
    plan=dict(version='financial-preauth-plan-v1',training_enabled=False,training_eligible=False,
        steps=400,batch=8,seed=cfg['seed'],step_rows=[new[i:i+8] for i in range(0,3200,8)],
        prefix_200_steps=[new[i:i+8] for i in range(0,1600,8)],bucket_quotas=quotas)
    validate_plan(rows,old_steps,plan,cfg)
    return plan


def validate_plan(rows,old_steps,plan,cfg):
    indexed=parent.validate_rows(rows)
    if len(plan['step_rows'])!=400 or any(len(x)!=8 for x in plan['step_rows']): raise ValueError('Bad new shape')
    old=[x for s in old_steps for x in s];new=[x for s in plan['step_rows'] for x in s]
    if len(old)!=3200 or any(rid not in indexed for rid in new): raise ValueError('Invalid plan ids')
    preauth=[]
    for oldid,newid in zip(old,new):
        if indexed[oldid]['input']['state']['authenticated']:
            if oldid!=newid: raise ValueError('Authenticated ID or position changed')
        else:
            if indexed[newid]['input']['state']['authenticated']: raise ValueError('Unauthenticated slot replaced by authenticated row')
            preauth.append(newid)
    if len(preauth)!=480 or len(set(preauth))!=480: raise ValueError('Preauth repeats or count changed')
    if max(Counter(new).values())>4 or max(Counter(indexed[x]['scene_family_id'] for x in new).values())>16:
        raise ValueError('Global row/group cap exceeded')
    if plan['prefix_200_steps']!=plan['step_rows'][:200]: raise ValueError('200 prefix differs')
    excluded={r['scene_family_id'] for r in rows if segment(r)=='preauth-no-kb'}
    for rid in preauth:
        if segment(indexed[rid])=='preauth-kb' and indexed[rid]['scene_family_id'] in excluded:
            raise ValueError('KB story group exclusion violated')
    for start in range(0,3200,20):
        counts=Counter(segment(indexed[x]) for x in new[start:start+20] if not indexed[x]['input']['state']['authenticated'])
        if counts!=Counter({'preauth-no-kb':2,'preauth-kb':1}): raise ValueError('Block capability ratio differs')
    for name,label in [('no_kb','preauth-no-kb'),('kb','preauth-kb')]:
        actual=Counter(bucket(indexed[x]) for x in preauth if segment(indexed[x])==label)
        if dict(actual)!=plan['bucket_quotas'][name]: raise ValueError('Bucket coverage differs')


def source_bindings():
    paths=[CONFIG, Path(__file__),ROOT/'tests/test_financial_preauth_schedule.py',
        ROOT/'src/qwenlab/financial_coverage_audit.py',pool.OUT/'manifest.json',pool.OUT/'train.json',parent.OUT/'manifest.json']
    paths += [parent.OUT/n for n in parent.FILES]
    paths += [ROOT/'src/qwenlab'/n for n in ('financial_sampling_freeze.py','financial_sampling_plan.py','financial_sampling_data.py','financial_prompt_v2.py','common.py')]
    paths += [ROOT/'configs/financial-sampling-study-v1.json']
    # Expand the actual parent dependency closure, not only its manifest claim.
    # This also detects transitive code/tokenizer drift after parent.verify.
    bindings=parent.source_bindings()
    bindings.update({parent.relative(p):sha(p) for p in sorted(paths,key=str)})
    return dict(sorted(bindings.items()))


def compute(tokenize):
    parent.verify(tokenize=tokenize)
    cfg=check_config(read(CONFIG));rows=pool.verify();indexed=parent.validate_rows(rows)
    old_steps=read(parent.OUT/'stratified-plan.json')['step_rows']
    plan=make_plan(rows,old_steps,cfg)
    new=[x for step in plan['step_rows'] for x in step];old=[x for step in old_steps for x in step]
    counts=Counter();ledger=[];changes=[]
    for i,rid in enumerate(new):
        row=indexed[rid];counts[rid]+=1
        ledger.append(dict(exposure_index=i+1,step=i//8+1,microbatch=(i%8)//2+1,position=i%2+1,
            row_id=rid,row_sha256=parent.row_sha(row),group=row['scene_family_id'],layer=old_plan.layer_of(row),occurrence=counts[rid]))
        if indexed[old[i]]['input']['state']['authenticated'] is False:
            changes.append(dict(exposure_index=i+1,step=i//8+1,old_row_id=old[i],new_row_id=rid,
                changed=old[i]!=rid,segment=segment(row),bucket=bucket(row),group=row['scene_family_id']))
    lengths=parent.validate_lengths(rows,read(parent.OUT/'token-lengths.json'),2048)
    old_summary=read(parent.OUT/'summary.json')['arms']['stratified']
    old_records=read(parent.OUT/'exposure-ledger.json')['arms']['stratified']
    preserved=sum(ledger[i]['row_id']==old_records[i]['row_id'] and ledger[i]['row_sha256']==old_records[i]['row_sha256']
                  for i,rid in enumerate(old) if indexed[rid]['input']['state']['authenticated'])
    if preserved!=2720:raise ValueError('Fixed row bytes or positions changed')
    summary=dict(version='financial-preauth-summary-v1',training_enabled=False,model_weights_loaded=False,
        model_api_requests=0,evaluation_examples_read=False,authenticated_positions_preserved=2720,
        preauth_positions=480,actually_changed_positions=sum(c['changed'] for c in changes),
        full_400=parent.arm_summary(ledger,indexed,lengths,2),
        prefix_200=parent.arm_summary(ledger[:1600],indexed,lengths,2),base_full_400=old_summary['full_400'],
        preauth_segments=dict(Counter(c['segment'] for c in changes)),
        preauth_prefix_200=dict(Counter(c['segment'] for c in changes if c['step']<=200)),
        bucket_quotas=plan['bucket_quotas'],
        limitations=['Changes capability allocation, bucket coverage and source-group selection together.',
            'Fixed authenticated row IDs/positions do not imply identical gradients, padding, optimizer state or dropout RNG.',
            'CPU schedule readiness is not training execution approval, model improvement or production readiness.'])
    for horizon in ('full_400','prefix_200'):
        new_stats,old_stats=summary[horizon],old_summary[horizon]
        for key in ('true_tool_exposures','supervised_tasks','supervised_weight','nonempty_tool_microbatches','tool_counts'):
            if new_stats[key]!=old_stats[key]:raise ValueError(f'Tool supervision changed: {horizon}/{key}')
        for key in ('raw_input_tokens','padded_input_tokens'):
            if new_stats[key]['tool']!=old_stats[key]['tool']:raise ValueError('Tool token budget changed')
    if [(r['step'],r['microbatch'],r['position'],r['row_id']) for r in ledger if indexed[r['row_id']]['annotation']['action']=='tool'] != [
        (r['step'],r['microbatch'],r['position'],r['row_id']) for r in old_records if indexed[r['row_id']]['annotation']['action']=='tool']:
        raise ValueError('Tool microbatch positions changed')
    no_groups={r['scene_family_id'] for r in rows if segment(r)=='preauth-no-kb'}
    excluded=[r for r in rows if segment(r)=='preauth-kb' and r['scene_family_id'] in no_groups]
    pairs=defaultdict(list)
    for row in rows:
        key=(row['scene_family_id'],json.dumps([row['input']['message'],row['input']['history']],ensure_ascii=False,sort_keys=True))
        pairs[key].append(row)
    pairs=[v for v in pairs.values() if len({r['input']['state']['authenticated'] for r in v})==2
           and {'tool','clarify'} <= {r['annotation']['action'] for r in v}]
    def retained(ids):
        ids=set(ids)
        return sum(len({r['input']['state']['authenticated'] for r in v if r['id'] in ids})==2 for v in pairs)
    summary['kb_group_exclusion']=dict(rows=len(excluded),groups=len({r['scene_family_id'] for r in excluded}))
    summary['exact_surface_auth_pairs']=dict(pool_buckets=len(pairs),base_retained=retained(old),candidate_retained=retained(new))
    return {'plan.json':plan,'exposure-ledger.json':ledger,'replacement-ledger.json':changes,'summary.json':summary}


def prepare():
    if OUT.exists():raise FileExistsError('Preserve any prior candidate; no overwrite')
    before=source_bindings();values=compute(tokenize=True)
    if before!=source_bindings():raise ValueError('Sources changed during preparation')
    payload={n:raw(values[n]) for n in sorted(FILES)}
    import hashlib
    manifest=dict(version='financial-preauth-freeze-v1',training_enabled=False,training_eligible=False,
        model_weights_loaded=False,model_api_requests=0,sources=before,
        files={n:hashlib.sha256(v).hexdigest() for n,v in payload.items()},
        tokenizer=read(parent.OUT/'manifest.json')['tokenizer'])
    OUT.mkdir(parents=True,exist_ok=False)
    for name,data in payload.items():
        with (OUT/name).open('xb') as f:f.write(data)
    if before!=source_bindings():raise ValueError('Sources changed; manifest withheld')
    with (OUT/'manifest.json').open('xb') as f:f.write(raw(manifest))
    return values['summary.json']


def verify(tokenize=False):
    manifest=read(OUT/'manifest.json')
    if (set(manifest)!={'version','training_enabled','training_eligible','model_weights_loaded','model_api_requests','sources','files','tokenizer'}
        or manifest['version']!='financial-preauth-freeze-v1' or manifest['training_enabled'] is not False
        or manifest['training_eligible'] is not False or manifest['model_weights_loaded'] is not False or manifest['model_api_requests']!=0):
        raise ValueError('Invalid CPU-only manifest')
    if set(manifest['files'])!=FILES or {p.name for p in OUT.iterdir()}!=FILES|{'manifest.json'}:raise ValueError('Manifest inventory changed')
    before=source_bindings()
    if manifest['sources']!=before or any(sha(OUT/n)!=h for n,h in manifest['files'].items()):raise ValueError('Frozen sources/output changed')
    if manifest['tokenizer']!=read(parent.OUT/'manifest.json')['tokenizer']:raise ValueError('Tokenizer binding changed')
    values=compute(tokenize)
    if any(read(OUT/n)!=values[n] for n in FILES) or source_bindings()!=before:raise ValueError('Replay differs')
    return dict(status='verified',tokenizer_replayed=bool(tokenize),authenticated_positions_preserved=2720,
        preauth_counts={'no_kb':320,'kb':160},training_enabled=False,model_weights_loaded=False,model_api_requests=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','verify']);parser.add_argument('--tokenize',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare' and args.tokenize:parser.error('prepare always tokenizes')
    print(json.dumps(prepare() if args.command=='prepare' else verify(args.tokenize),ensure_ascii=False,indent=2))
