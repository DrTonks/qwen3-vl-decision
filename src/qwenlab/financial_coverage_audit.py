"""Training-only coverage inventory and real Node parameter replay; never trains."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess

from qwenlab.common import ROOT, sha
from qwenlab import financial_sampling_data as pool

OUT = ROOT / 'docs/evidence/financial-coverage-audit-v1'
SCHEDULE = ROOT / 'data/financial-sampling-study-v1/schedule-v1'
ALIASES = {'applicationId': 'application_id', 'statusCode': 'status_code'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def segment(row):
    auth = row['input']['state']['authenticated']
    if type(auth) is not bool:
        raise ValueError('Authentication must be an explicit trusted boolean')
    return ('authenticated' if auth else 'preauth') + ('-kb' if row['input']['capabilities']['knowledge_collections'] else '-no-kb')


def slots(row):
    # Audit grouping only; original annotations remain byte-identical.
    return '+'.join(sorted({ALIASES.get(s, s) for s in row['annotation']['missing_slots']})) or 'none_declared'


def parameter_form(row, replay):
    a, state = row['annotation'], row['input']['state']
    if a['action'] != 'tool':
        return 'non_tool:' + slots(row)
    field = {'queryApplicationDetail': 'application_id', 'explainApplicationStatus': 'status_code'}.get(a['tool_name'])
    if field is None:
        return 'tool:no_extra_parameter'
    value = state.get(field)
    valid = type(value) is int and (0 <= value <= 2 if field == 'status_code' else 0 < value <= 2147483647)
    if valid:
        return 'tool:structured_' + field
    if field in replay['parsed_state']:
        return 'tool:node_parsed_' + field
    return 'tool:unresolved_by_node_' + field


def inventory(rows, exposures):
    ids = {r['id'] for r in rows}
    unique = {json.dumps(r['input'], sort_keys=True, ensure_ascii=False) for r in rows}
    group_sizes = Counter(r['scene_family_id'] for r in rows)
    return dict(rows=len(rows), story_groups=len({r['scene_family_id'] for r in rows}),
        unique_visible_inputs=len(unique), action_counts=dict(Counter(r['annotation']['action'] for r in rows)),
        isolated_cell_capacity_row4_group16=sum(min(n*4,16) for n in group_sizes.values()),
        action_story_groups={a:len({r['scene_family_id'] for r in rows if r['annotation']['action']==a})
                             for a in sorted({r['annotation']['action'] for r in rows})},
        exposures={arm:sum(count for rid,count in counts.items() if rid in ids) for arm,counts in exposures.items()},
        unique_exposed={arm:sum(rid in counts for rid in ids) for arm,counts in exposures.items()})


def audit(backend):
    rows = pool.verify()
    if any(r['split'] != 'train' or r['training_eligible'] is not False for r in rows):
        raise ValueError('Only the frozen training candidate pool may be inventoried')
    manifest = read(SCHEDULE / 'manifest.json')
    for name, digest in manifest['files'].items():
        if sha(SCHEDULE / name) != digest:
            raise ValueError('Old schedule bytes changed')
    dependencies = [Path(__file__), ROOT/'scripts/inspect-financial-training-inputs.cjs',
        ROOT/'configs/support-financial-v2.json', pool.OUT/'manifest.json', pool.OUT/'train.json',
        SCHEDULE/'manifest.json', SCHEDULE/'uniform-plan.json', SCHEDULE/'stratified-plan.json']
    backend_rel = ['services/customerSupport/financialContract.js', 'services/customerSupport/parameters.js',
                   'services/customerSupport/contract.js', 'services/customerSupport/policies/support-financial-v2.json']
    bindings = {p.relative_to(ROOT).as_posix():sha(p) for p in dependencies}
    backend_hashes = {p:sha(backend/p) for p in backend_rel}
    if backend_hashes[backend_rel[-1]] != sha(ROOT/'configs/support-financial-v2.json'):
        raise ValueError('Actual backend and dataset action policies differ')
    result = subprocess.run(['node', str(ROOT/'scripts/inspect-financial-training-inputs.cjs'), str(backend)],
                            check=True, capture_output=True, encoding='utf-8')
    replay = json.loads(result.stdout)
    projected = {r['id']:r for r in replay['rows']}
    if len(projected) != len(rows) or set(projected) != {r['id'] for r in rows}:
        raise ValueError('Incomplete or duplicate training-only Node replay')
    exposures = {a:Counter(rid for batch in read(SCHEDULE/f'{a}-plan.json')['step_rows'] for rid in batch)
                 for a in ('uniform','stratified')}
    if any(sum(v.values()) != 3200 for v in exposures.values()):
        raise ValueError('Unexpected previous exposure budget')
    segments, cross, tool_forms, missing = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    hard_violations, grounding_changes, param_mismatches = [], [], []
    full_tools = set(read(ROOT/'configs/support-financial-v2.json')['tools'])
    for row in rows:
        inp, ann, rid = row['input'], row['annotation'], row['id']
        seg = segment(row)
        tool_mode = 'all' if set(inp['available_tools']) == full_tools else ('none' if not inp['available_tools'] else 'partial')
        form = parameter_form(row, projected[rid])
        segments[seg].append(row)
        cross[(seg, tool_mode, ann['action'], form)].append(row)
        if ann['action'] == 'tool': tool_forms[(seg, ann['tool_name'], form)].append(row)
        if ann['missing_slots']: missing[(seg, slots(row))].append(row)
        if ann['action']=='tool' and (inp['state']['authenticated'] is not True or ann['tool_name'] not in inp['available_tools']):
            hard_violations.append(dict(id=rid, reason='tool_auth_or_availability'))
        if ann['action']=='retrieve' and ann['retrieval_collection'] not in inp['capabilities']['knowledge_collections']:
            hard_violations.append(dict(id=rid, reason='retrieval_collection_unavailable'))
        grounded = projected[rid]['grounded_gold']
        if ann['action']=='tool' and grounded['action']!='tool':
            grounding_changes.append(dict(id=rid, group=row['scene_family_id'], layer=row['input_layer'],
                segment=seg, target_tool=ann['tool_name'], form=form, reason=grounded['reasonCode']))
        if ann['action']=='tool' and grounded['action']=='tool' and grounded.get('arguments',{}) != ann['tool_arguments']:
            param_mismatches.append(dict(id=rid, layer=row['input_layer'], target_tool=ann['tool_name'],
                labelled_arguments=ann['tool_arguments'], parsed_arguments=grounded['arguments']))
    exact_pairs = defaultdict(list)
    for row in rows:
        # Same surface text/history, within original story. Do not infer semantic pairs from keywords.
        key = (row['scene_family_id'], json.dumps([row['input']['message'],row['input']['history']],ensure_ascii=False,sort_keys=True))
        exact_pairs[key].append(row)
    auth_pairs = [v for v in exact_pairs.values() if len({r['input']['state']['authenticated'] for r in v})>1]
    tool_auth_pairs = [v for v in auth_pairs if {'tool','clarify'} <= {r['annotation']['action'] for r in v}]
    by_id = {r['id']:r for r in rows}
    fixed_groups = Counter()
    for rid, count in exposures['stratified'].items():
        if by_id[rid]['input']['state']['authenticated']:
            fixed_groups[by_id[rid]['scene_family_id']] += count
    no_kb_groups = Counter(r['scene_family_id'] for r in segments['preauth-no-kb'])
    kb_disjoint = Counter(r['scene_family_id'] for r in segments['preauth-kb'] if r['scene_family_id'] not in no_kb_groups)
    no_kb_capacity = sum(min(n,max(0,16-fixed_groups[g])) for g,n in no_kb_groups.items())
    kb_capacity = sum(min(n,max(0,16-fixed_groups[g])) for g,n in kb_disjoint.items())
    summary = dict(version='financial-coverage-audit-v1', training_enabled=False, model_weights_loaded=False,
        evaluation_examples_read=False, model_api_requests=0, original_labels_changed=False,
        pool=inventory(rows,exposures), segments={k:inventory(v,exposures) for k,v in sorted(segments.items())},
        source_sha256=bindings, backend_source_sha256=backend_hashes, node_adapter_version=replay['adapter_version'],
        node_replay_scope=replay['scope'], hard_violations=hard_violations,
        grounded_gold_action_changes=grounding_changes, grounded_gold_parameter_mismatches=param_mismatches,
        exact_surface_auth_pairs=dict(buckets=len(auth_pairs),story_groups=len({v[0]['scene_family_id'] for v in auth_pairs}),
            tool_clarify_buckets=len(tool_auth_pairs),tool_clarify_story_groups=len({v[0]['scene_family_id'] for v in tool_auth_pairs})),
        proposed_preauth_split_capacity=dict(status='capacity_check_only_not_a_frozen_schedule',
            fixed_authenticated_exposures=sum(fixed_groups.values()), proposed_no_kb=320, proposed_kb=160,
            unique_no_kb_capacity_after_fixed=no_kb_capacity, unique_disjoint_kb_capacity_after_fixed=kb_capacity,
            feasible_for_these_constraints=no_kb_capacity>=320 and kb_capacity>=160,
            repeated_preauth_rows_required=False, group_cap=16,
            caveat='Capacity proof uses disjoint story groups for the two preauth pools; no actual ordering, action floors, token budget or training permission produced.'),
        slot_spellings=dict(Counter(s for r in rows for s in r['annotation']['missing_slots'])),
        limitations=['Training metadata and labels are audited, not independently re-labelled.',
            'Node parameters are replayed from reconstructed context, not actual sessions; unresolved is not automatically a wrong label.',
            'Story groups can cross cells; summing cell group counts overstates independent groups.',
            'Cell capacity under row4/group16 is an isolated upper bound, not joint schedule feasibility.',
            'No development/calibration/final examples, predictions, or errors used to construct coverage cells.'])
    cells = [dict(segment=k[0], available_tools=k[1], action=k[2], parameters=k[3], **inventory(v,exposures)) for k,v in sorted(cross.items())]
    forms = [dict(segment=k[0],tool=k[1],parameters=k[2],**inventory(v,exposures)) for k,v in sorted(tool_forms.items())]
    missing_cells = [dict(segment=k[0],missing_slots=k[1],**inventory(v,exposures)) for k,v in sorted(missing.items())]
    if any(sha(ROOT/p)!=h for p,h in bindings.items()) or any(sha(backend/p)!=h for p,h in backend_hashes.items()):
        raise ValueError('Dependencies changed during audit')
    write(OUT/'summary.json',summary)
    write(OUT/'coverage-cells.json',dict(training_eligible=False,cells=cells,tool_parameters=forms,missing_slot_cells=missing_cells))
    write(OUT/'manifest.json',dict(source_sha256=bindings,backend_source_sha256=backend_hashes,
        files={n:sha(OUT/n) for n in ('summary.json','coverage-cells.json')}))
    print(json.dumps(dict(segments=summary['segments'], hard_violations=len(hard_violations),
        grounded_action_changes=len(grounding_changes),parameter_mismatches=len(param_mismatches),
        exact_surface_auth_pairs=summary['exact_surface_auth_pairs']),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',type=Path,default=ROOT.parent/'uestc_Integrated_Design'/'后端')
    audit(parser.parse_args().backend.resolve())
