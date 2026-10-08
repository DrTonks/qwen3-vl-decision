"""Training-only single-field contrasts and exposure audit; never relabel/train."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path

from qwenlab.common import ROOT, sha
from qwenlab import financial_preauth_schedule as frozen
from qwenlab.financial_sampling_plan import layer_of
from qwenlab.financial_coverage_audit import ALIASES

OUT = ROOT / 'docs/evidence/financial-state-pair-audit-v1'
DIMENSIONS = {'state.authenticated':'authentication', 'available_tools':'tool_availability',
              'state.application_id':'application_id', 'state.status_code':'status_code',
              'capabilities.knowledge_collections':'knowledge_availability'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def visible(row):
    value = deepcopy(row['input'])
    value['available_tools'] = sorted(value['available_tools'])
    value['capabilities']['knowledge_collections'] = sorted(value['capabilities']['knowledge_collections'])
    return value


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            child = path + '.' + key if path else key
            result.extend([child] if key not in a or key not in b else differences(a[key], b[key], child))
        return result
    # JSON types matter: False and 0 must not silently compare equal.
    return [] if canonical(a) == canonical(b) else [path]


def target(row):
    a = row['annotation']
    return {k:a[k] for k in ('action','tool_name','tool_arguments','retrieval_collection','missing_slots')}


def expected_boundary(left, right, dimension):
    rows = [left,right]
    tool = next((r for r in rows if r['annotation']['action']=='tool'), None)
    if tool is None: return False
    other = right if tool is left else left
    a, b = tool['annotation'], other['annotation']
    if dimension=='authentication':
        return (tool['input']['state']['authenticated'] is True and other['input']['state']['authenticated'] is False
                and b['action']=='clarify' and 'authentication' in b['missing_slots'])
    if dimension=='tool_availability':
        return (a['tool_name'] in tool['input']['available_tools'] and a['tool_name'] not in other['input']['available_tools']
                and b['action']=='human')
    if dimension in ('application_id','status_code'):
        slot = 'application_id' if dimension=='application_id' else 'status_code'
        slots={ALIASES.get(s,s) for s in b['missing_slots']}
        return b['action']=='clarify' and slot in slots
    return False


def audit(rows, plans):
    indexed = {}
    groups = defaultdict(list)
    input_targets = {}
    for row in rows:
        if (row['id'] in indexed or row.get('split')!='train' or row.get('training_eligible') is not False
                or type(row['input']['state']['authenticated']) is not bool):
            raise ValueError('Unique train-only rows and explicit trusted authentication required')
        indexed[row['id']] = row
        value = visible(row)
        key = canonical(value)
        if key in input_targets and input_targets[key] != canonical(target(row)):
            raise ValueError('Conflicting targets for identical visible input')
        input_targets[key] = canonical(target(row))
        groups[(row['scene_family_id'],canonical([value['message'],value['history']]))].append(row)
    counts = {}
    for name, steps in plans.items():
        if any(rid not in indexed for step in steps for rid in step): raise ValueError('Unknown schedule row')
        counts[name] = Counter(rid for step in steps for rid in step)
    pairs, coupled = [], []
    for key, members in sorted(groups.items()):
        for a,b in itertools.combinations(sorted(members,key=lambda r:r['id']),2):
            changed = differences(visible(a),visible(b))
            if len(changed)!=1 or changed[0] not in DIMENSIONS:
                if changed: coupled.append(dict(row_ids=[a['id'],b['id']],story_group=key[0],changed_fields=changed))
                continue
            dim = DIMENSIONS[changed[0]]
            rid = hashlib.sha256(canonical([dim,a['id'],b['id']]).encode()).hexdigest()[:16]
            pairs.append(dict(pair_id='PAIR-'+rid,dimension=dim,story_group=key[0],changed_fields=changed,
                knowledge_profiles=['kb' if r['input']['capabilities']['knowledge_collections'] else 'no-kb' for r in (a,b)],
                row_ids=[a['id'],b['id']],source_row_sha256={r['id']:hashlib.sha256(canonical(r).encode()).hexdigest() for r in (a,b)},
                targets=[target(a),target(b)],action_changes=a['annotation']['action']!=b['annotation']['action'],
                matches_expected_boundary=expected_boundary(a,b,dim),review_status='structural_candidate_not_new_semantic_approval',
                exposure={name:dict(counts=[v[a['id']],v[b['id']]],both=v[a['id']]>0 and v[b['id']]>0,
                                   neither=v[a['id']]==v[b['id']]==0) for name,v in counts.items()}))
    summary = dict(pool_rows=len(rows),same_surface_story_groups=sum(len(v)>1 for v in groups.values()),
        strict_single_field_pairs=len(pairs),strict_story_groups=len({p['story_group'] for p in pairs}),
        non_single_target_pairs=len(coupled),coupled_field_counts=dict(Counter('+'.join(x['changed_fields']) for x in coupled)),dimensions={})
    for dim in sorted({p['dimension'] for p in pairs}):
        subset = [p for p in pairs if p['dimension']==dim]
        summary['dimensions'][dim] = dict(pairs=len(subset),story_groups=len({p['story_group'] for p in subset}),
            knowledge_profile_counts=dict(Counter('/'.join(p['knowledge_profiles']) for p in subset)),
            matches_expected_boundary=sum(p['matches_expected_boundary'] for p in subset),
            action_transitions=dict(Counter(' / '.join(sorted(t['action'] for t in p['targets'])) for p in subset)),
            coverage={name:dict(both=sum(p['exposure'][name]['both'] for p in subset),
                               neither=sum(p['exposure'][name]['neither'] for p in subset),
                               one_side=sum(not p['exposure'][name]['both'] and not p['exposure'][name]['neither'] for p in subset)) for name in counts})
    return pairs,coupled,summary


def signature(row):
    a = row['annotation']; value=row['input']
    return canonical([layer_of(row), value['state']['authenticated'],
        bool(value['capabilities']['knowledge_collections']),a['action'],a['tool_name']])


def capacity(rows, pairs, steps):
    """Necessary per-cell exchange capacity, not a validated new training schedule."""
    lookup={r['id']:r for r in rows};counts=Counter(rid for step in steps for rid in step)
    anchors={rid for p in pairs if p['matches_expected_boundary'] for rid in p['row_ids']}
    missing=anchors-counts.keys()
    # Keep at least one occurrence of every already selected anchor.
    spare=Counter()
    for rid,n in counts.items(): spare[signature(lookup[rid])] += n-int(rid in anchors)
    required=Counter(signature(lookup[rid]) for rid in sorted(missing))
    deficits={k:n-spare[k] for k,n in required.items() if n>spare[k]}
    fixed_auth_ceiling=sum(all(counts[rid]>0 for rid in p['row_ids'] if lookup[rid]['input']['state']['authenticated'])
        for p in pairs if p['dimension']=='authentication' and p['matches_expected_boundary'])
    groups=Counter(lookup[rid]['scene_family_id'] for rid in anchors)
    return dict(unique_anchor_rows=len(anchors),already_selected=len(anchors)-len(missing),
        missing_rows=len(missing),missing_authenticated=sum(lookup[rid]['input']['state']['authenticated'] for rid in missing),
        fixed_authenticated_auth_pair_ceiling=fixed_auth_ceiling,
        max_minimum_anchor_rows_per_group=max(groups.values(),default=0),per_cell_required=dict(required),
        per_cell_spare={k:spare[k] for k in required},per_cell_deficits=deficits,
        necessary_cell_capacity_passed=not deficits,training_enabled=False,
        scope='Lower bound on replacement positions. Preserves layer/auth/KB/action/tool marginal counts if constructed. '
              'Does not prove global group-cap feasibility, prefix200 balance, token budget, or semantic sufficiency.')


def bindings():
    values=frozen.source_bindings()
    for path in (Path(__file__),ROOT/'tests/test_financial_state_pair_audit.py',frozen.OUT/'manifest.json',frozen.OUT/'plan.json'):
        values[path.relative_to(ROOT).as_posix()]=sha(path)
    return values


def build():
    before=bindings();frozen.verify()
    rows=frozen.pool.verify()
    plans={name:frozen.read(frozen.parent.OUT/(name+'-plan.json'))['step_rows'] for name in ('uniform','stratified')}
    plans['preauth400']=frozen.read(frozen.OUT/'plan.json')['step_rows']
    pairs,coupled,summary=audit(rows,plans)
    summary['candidate_exchange_capacity']=capacity(rows,pairs,plans['preauth400'])
    current_pairs=[p for p in pairs if p['knowledge_profiles']==['no-kb','no-kb']]
    summary['current_no_kb_exchange_capacity']=capacity(rows,current_pairs,plans['preauth400'])
    summary['current_no_kb_pair_ids']=[p['pair_id'] for p in current_pairs]
    summary['current_no_kb_coverage']={name:dict(pairs=len(current_pairs),both=sum(p['exposure'][name]['both'] for p in current_pairs)) for name in plans}
    payload=dict(version='financial-state-pair-audit-v1',training_enabled=False,training_eligible=False,
        evaluation_examples_read=False,model_api_requests=0,summary=summary,pairs=pairs,non_single_target_pairs=coupled)
    lookup={r['id']:r for r in rows}
    lines=['# 可信状态成对覆盖：训练来源阅读版','','仅为结构审计；不改标签、不产生训练发布。完整输入/原标签见JSON。','']
    for p in pairs:
        lines += ['## '+p['pair_id']+' / '+p['dimension'],'',
            '变动字段：'+', '.join(p['changed_fields']),
            '两侧均入选：'+', '.join(k+'='+str(v['both']) for k,v in p['exposure'].items()),'']
        for rid in p['row_ids']:
            lines += ['```json',json.dumps(dict(id=rid,input=lookup[rid]['input'],annotation=lookup[rid]['annotation']),ensure_ascii=False,indent=2),'```','']
    if before!=bindings(): raise ValueError('Source changed during audit')
    files={'audit.json':json.dumps(payload,ensure_ascii=False,indent=2)+'\n','review.md':'\n'.join(lines)+'\n'}
    manifest=dict(version='financial-state-pair-audit-v1',source_sha256=before,
        files={k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()},training_enabled=False,model_api_requests=0)
    files['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    if OUT.exists():
        if {p.name for p in OUT.iterdir()}!=set(files):raise ValueError('Audit inventory changed')
        if any((OUT/n).read_bytes()!=s.encode() for n,s in files.items()):raise ValueError('Existing audit differs; preserve it')
    else:
        OUT.mkdir(parents=True)
        for n,s in files.items():
            with (OUT/n).open('xb') as stream:stream.write(s.encode())
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','verify'])
    parser.parse_args();build()
