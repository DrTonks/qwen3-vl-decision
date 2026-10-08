"""CPU-only, capped exposure plans over an explicitly supplied training pool.

Uniform shuffles all rows. Stratified changes both layer allocation and source
group weighting; comparisons therefore identify the combined sampling strategy.
No model, tokenizer, evaluation dataset, or training runtime is imported.
"""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
LAYERS = ('current-node', 'current-component', 'planned', 'preauth')
QUOTAS = dict(zip(LAYERS, (9, 3, 5, 3)))
COHORTS = ('current-service', 'planned-retrieval', 'preauth-robustness')
ACTIONS = ('clarify', 'tool', 'answer', 'human', 'retrieve', 'redirect', 'refuse', 'close')
TOOLS = ('queryLoanProducts', 'queryMyApplications', 'queryApplicationDetail',
         'queryMyCreditScore', 'explainApplicationStatus')


class CapacityError(ValueError):
    """A hard exposure bound prevents completion; no partial plan is released."""

    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__(json.dumps(diagnostic, ensure_ascii=False, sort_keys=True))


def layer_of(row):
    cohort = row.get('cohort')
    layer = row.get('input_layer')
    if cohort == 'current-service':
        if layer == 'node-projection':
            return 'current-node'
        if layer is None or layer == 'component-message-only':
            return 'current-component'
    elif cohort == 'planned-retrieval' and layer in (None, 'planned-capability-component'):
        return 'planned'
    elif cohort == 'preauth-robustness' and layer in (None, 'preauth-component'):
        return 'preauth'
    raise ValueError(f'Invalid cohort/input_layer for {row.get("id")!r}')


def _positive_integer(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f'{name} must be a positive integer')


def _digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def plan(rows, mode, seed, steps=400, batch=8, *, max_row_exposure=4, max_group_exposure=16):
    """Return immutable-by-convention step IDs and exhaustive exposure accounting.

    The input is normalized by ID, so harmless source-list reordering cannot
    change the plan. All source-group IDs share one counter across layers.
    Capacity exhaustion fails, including exhaustion caused by earlier choices;
    quotas and caps are never relaxed to finish a plan.
    """
    if mode not in ('uniform', 'stratified'):
        raise ValueError('mode must be uniform or stratified')
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    for key, value in (('steps', steps), ('batch', batch),
                       ('max_row_exposure', max_row_exposure),
                       ('max_group_exposure', max_group_exposure)):
        _positive_integer(value, key)
    total = steps * batch
    if total % 20:
        raise ValueError('steps * batch must be divisible by 20; incomplete quota blocks are forbidden')
    if not isinstance(rows, list) or not rows:
        raise ValueError('rows must be a nonempty training-row list')
    indexed = {}
    layers = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each training row must be an object')
        rid, group = row.get('id'), row.get('scene_family_id')
        if not isinstance(rid, str) or not rid or rid in indexed:
            raise ValueError('Every training row requires a unique nonempty id')
        if not isinstance(group, str) or not group:
            raise ValueError(f'Missing scene_family_id: {rid}')
        if row.get('split') != 'train':
            raise ValueError(f'Only explicit training rows may be planned: {rid}')
        annotation = row.get('annotation', {})
        action, tool = annotation.get('action'), annotation.get('tool_name')
        if action not in ACTIONS or (action == 'tool' and tool not in TOOLS):
            raise ValueError(f'Invalid action/tool annotation: {rid}')
        if action != 'tool' and tool is not None:
            raise ValueError(f'Non-tool action carries a tool: {rid}')
        indexed[rid] = row
        layers[rid] = layer_of(row)
    ids = sorted(indexed)
    groups = defaultdict(list)
    strata = {layer: defaultdict(list) for layer in LAYERS}
    for rid in ids:
        group = indexed[rid]['scene_family_id']
        groups[group].append(rid)
        strata[layers[rid]][group].append(rid)
    global_capacity = sum(min(len(members) * max_row_exposure, max_group_exposure)
                          for members in groups.values())
    if global_capacity < total:
        raise CapacityError({'reason': 'insufficient_total_capacity', 'required': total,
                             'available': global_capacity})
    if mode == 'stratified':
        for layer, quota in QUOTAS.items():
            capacity = sum(min(len(members) * max_row_exposure, max_group_exposure)
                           for members in strata[layer].values())
            required = total // 20 * quota
            if capacity < required:
                raise CapacityError({'reason': 'insufficient_layer_capacity', 'layer': layer,
                                     'required': required, 'available': capacity})
    rng = random.Random(seed)
    row_counts = Counter({rid: 0 for rid in ids})
    group_counts = Counter({group: 0 for group in sorted(groups)})
    cohort_counts = Counter({cohort: 0 for cohort in COHORTS})
    layer_counts = Counter({layer: 0 for layer in LAYERS})
    action_counts = Counter({action: 0 for action in ACTIONS})
    tool_counts = Counter({tool: 0 for tool in TOOLS})

    def eligible(rid):
        return (row_counts[rid] < max_row_exposure
                and group_counts[indexed[rid]['scene_family_id']] < max_group_exposure)

    row_queues = {}
    group_queues = {layer: deque() for layer in LAYERS}

    def within_group(layer, group):
        key = (layer, group)
        queue = row_queues.setdefault(key, deque())
        while queue:
            rid = queue.popleft()
            if eligible(rid):
                return rid
        members = [rid for rid in strata[layer][group] if eligible(rid)]
        rng.shuffle(members)
        queue.extend(members)
        return queue.popleft() if queue else None

    def stratified_pick(layer):
        queue = group_queues[layer]
        while queue:
            found = within_group(layer, queue.popleft())
            if found is not None:
                return found
        candidates = [group for group, members in strata[layer].items()
                      if any(eligible(rid) for rid in members)]
        rng.shuffle(candidates)
        queue.extend(candidates)
        if queue:
            return within_group(layer, queue.popleft())
        return None

    uniform_queue = deque()

    def uniform_pick():
        if not uniform_queue:
            candidates = ids.copy()
            rng.shuffle(candidates)
            uniform_queue.extend(candidates)
        rid = uniform_queue.popleft()
        if not eligible(rid):
            raise CapacityError({
                'reason': 'uniform_draw_exceeds_hard_cap', 'row_id': rid,
                'group_id': indexed[rid]['scene_family_id'],
                'completed_exposures': len(sequence), 'required_exposures': total,
                'row_exposure_before_draw': row_counts[rid],
                'group_exposure_before_draw': group_counts[indexed[rid]['scene_family_id']],
                'row_cap': max_row_exposure, 'group_cap': max_group_exposure,
            })
        return rid

    sequence = []
    for block in range(total // 20):
        slots = [layer for layer, quota in QUOTAS.items() for _ in range(quota)]
        if mode == 'stratified':
            rng.shuffle(slots)
        for layer in slots:
            rid = stratified_pick(layer) if mode == 'stratified' else uniform_pick()
            if rid is None:
                raise CapacityError({
                    'reason': 'hard_cap_exhausted_during_rotation', 'mode': mode,
                    'layer': layer if mode == 'stratified' else 'all',
                    'completed_exposures': len(sequence), 'required_exposures': total,
                    'row_cap': max_row_exposure, 'group_cap': max_group_exposure,
                    'exhausted_groups': sorted(g for g in groups
                                               if group_counts[g] == max_group_exposure),
                })
            source = indexed[rid]
            sequence.append(rid)
            row_counts[rid] += 1
            group_counts[source['scene_family_id']] += 1
            cohort_counts[source['cohort']] += 1
            layer_counts[layers[rid]] += 1
            action_counts[source['annotation']['action']] += 1
            if source['annotation']['action'] == 'tool':
                tool_counts[source['annotation']['tool_name']] += 1

    def coverage(counts):
        unseen = sorted(key for key, value in counts.items() if not value)
        return dict(total=len(counts), seen=len(counts) - len(unseen), unseen=unseen,
                    max_exposure=max(counts.values(), default=0))

    def count_prefix(prefix):
        counts = {
            'row': Counter({rid: 0 for rid in ids}),
            'group': Counter({group: 0 for group in sorted(groups)}),
            'cohort': Counter({cohort: 0 for cohort in COHORTS}),
            'layer': Counter({layer: 0 for layer in LAYERS}),
            'action': Counter({action: 0 for action in ACTIONS}),
            'tool': Counter({tool: 0 for tool in TOOLS}),
        }
        for rid in prefix:
            source = indexed[rid]
            for kind, key in (('row', rid), ('group', source['scene_family_id']),
                              ('cohort', source['cohort']), ('layer', layers[rid]),
                              ('action', source['annotation']['action'])):
                counts[kind][key] += 1
            if source['annotation']['action'] == 'tool':
                counts['tool'][source['annotation']['tool_name']] += 1
        return {key: dict(value) for key, value in counts.items()}

    return {
        'version': 'financial-sampling-plan-v1', 'mode': mode, 'seed': seed,
        'steps': steps, 'batch': batch, 'total_exposures': total,
        'max_row_exposure': max_row_exposure, 'max_group_exposure': max_group_exposure,
        'pool_sha256': _digest([indexed[rid] for rid in ids]),
        'quota_block_size': 20 if mode == 'stratified' else None,
        'layer_quotas_per_block': QUOTAS.copy() if mode == 'stratified' else None,
        'group_cap_scope': 'global_across_all_layers',
        'interpretation': 'combined_layer_allocation_and_group_weighting_strategy',
        'training_started': False, 'model_weights_loaded': False, 'model_api_requests': 0,
        'step_rows': [sequence[i:i + batch] for i in range(0, total, batch)],
        'counts': dict(row=dict(row_counts), group=dict(group_counts),
                       cohort=dict(cohort_counts), layer=dict(layer_counts),
                       action=dict(action_counts), tool=dict(tool_counts)),
        'coverage': {'row': coverage(row_counts), 'group': coverage(group_counts)},
        'prefix_200_steps': (dict(steps=200, exposures=200 * batch,
                                  counts=count_prefix(sequence[:200 * batch]))
                             if steps >= 200 else None),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True,
                        help='Explicit JSON list of training rows; no other datasets are read')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('uniform', 'stratified'), required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--steps', type=int, default=400)
    parser.add_argument('--batch', type=int, default=8)
    parser.add_argument('--max-row-exposure', type=int, default=4)
    parser.add_argument('--max-group-exposure', type=int, default=16)
    args = parser.parse_args(argv)
    root = ROOT.resolve()
    input_path, output_path = args.input.resolve(), args.output.resolve()
    if not input_path.is_relative_to(root) or not output_path.is_relative_to(root):
        raise ValueError('Input and output must remain inside the repository root')
    if output_path.exists():
        raise FileExistsError('Sampling plans are immutable; choose a new output path')
    raw = input_path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    rows = json.loads(raw.decode('utf-8-sig'))
    result = plan(rows, args.mode, args.seed, args.steps, args.batch,
                  max_row_exposure=args.max_row_exposure,
                  max_group_exposure=args.max_group_exposure)
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != source_hash:
        raise ValueError('Training snapshot changed during planning; no output was published')
    result['source'] = {'path': input_path.relative_to(root).as_posix(), 'sha256': source_hash}
    # Exclusive creation also protects against a concurrent writer after preflight.
    with output_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'mode': args.mode, 'exposures': result['total_exposures'],
                      'output': output_path.relative_to(root).as_posix()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
