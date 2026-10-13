"""Training-only inventory. Lexical flags select review candidates, not labels."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/evidence/financial-training-boundary-audit-v1'
INPUTS = ['data/financial-sampling-study-v1/pool-v1/train.json',
          'data/financial-state-pair-study-v1/schedule-v1/additions.json',
          'data/financial-full-coverage-study-v1/schedule-v1/plan.json',
          'configs/support-financial-v2.json']
PATTERNS = {
    'cancellation_words': r'取消|撤销|撤回|注销',
    'conversation_end_words': r'结束|关闭|再见|不聊|不用聊|问完|没有.*问题',
    'prohibited_topic_words': r'造假|伪造|假流水|骗|盗|冒充|越权|他人|别人',
    'quotation_or_negation_words': r'[“”「」]|引用|他说|她说|中介说|拒绝了|举报|投诉|不要|不是|并非',
    'capability_question_words': r'能否|能不能|可以.*吗|支持.*吗|有没有.*功能|有没有.*工具',
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def visible(row):
    value = deepcopy(row['input'])
    value['available_tools'] = sorted(value['available_tools'])
    value['capabilities']['knowledge_collections'] = sorted(value['capabilities']['knowledge_collections'])
    return value


def invariant_flags(row):
    v, a = row['input'], row['annotation']
    flags = []
    if a['action'] == 'tool':
        if v['state']['authenticated'] is not True: flags.append('tool_without_authentication')
        if a['tool_name'] not in v['available_tools']: flags.append('tool_not_available')
    if a['action'] == 'retrieve' and a['retrieval_collection'] not in v['capabilities']['knowledge_collections']:
        flags.append('retrieval_not_available')
    if a['action'] != 'tool' and a['tool_name'] is not None: flags.append('non_tool_has_tool_target')
    return flags


def needs_text_review(candidate):
    flags, action = set(candidate['flags']), candidate['action']
    return (('cancellation_words' in flags and action == 'close')
            or {'quotation_or_negation_words','prohibited_topic_words'} <= flags
            or ('capability_question_words' in flags and action in ('human','tool')))


def analyze(rows, steps):
    from qwenlab.financial_sampling_plan import layer_of
    from qwenlab.financial_state_pair_audit import audit as pair_audit
    from qwenlab.financial_serve_v2 import validate_input
    spec = read(ROOT / INPUTS[-1])
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)) or any(r.get('split') != 'train' for r in rows):
        raise ValueError('Unique training rows required')
    exposure = Counter(i for step in steps for i in step)
    if set(exposure) != set(ids): raise ValueError('Schedule and input rows differ')
    if any(type(r['input']['state']['authenticated']) is not bool for r in rows):
        raise ValueError('Authentication must be boolean')
    actions = Counter(); layers = defaultdict(Counter); tool_cells = Counter()
    invariants, lexical = [], []
    by_input, by_surface = defaultdict(list), defaultdict(list)
    for r in rows:
        validate_input(r['input'], spec)
        if r['annotation']['action'] not in spec['actions']: raise ValueError('Invalid action')
        a, v = r['annotation'], visible(r)
        actions[a['action']] += 1; layers[layer_of(r)][a['action']] += 1
        by_input[canonical(v)].append(r)
        by_surface[canonical([v['message'], v['history']])].append(r)
        flags = invariant_flags(r)
        if flags: invariants.append(dict(id=r['id'], flags=flags))
        matches = [name for name, pattern in PATTERNS.items() if re.search(pattern, v['message'])]
        if matches:
            lexical.append(dict(id=r['id'], story=r['scene_family_id'], layer=layer_of(r),
                                action=a['action'], flags=matches, input=v, annotation=a))
        if a['action'] == 'tool': tool_cells[canonical([layer_of(r), a['tool_name']])] += 1
    duplicates, conflicts = [], []
    for members in by_input.values():
        if len(members) < 2: continue
        targets = {canonical([r['annotation']['action'], r['annotation']['tool_name']]) for r in members}
        item = dict(ids=[r['id'] for r in members], targets=sorted(targets))
        (conflicts if len(targets) > 1 else duplicates).append(item)
    # Original stricter pair checker compares full annotations, not only trained targets.
    try:
        pairs, coupled, pair_summary = pair_audit(rows, {'full_two_epochs': steps})
        pair_error = None
    except ValueError as exc:
        pairs, coupled, pair_summary, pair_error = [], [], {}, str(exc)
    pair_cells = Counter()
    for p in pairs:
        if not p['matches_expected_boundary']: continue
        t = next(t['tool_name'] for t in p['targets'] if t['action'] == 'tool')
        pair_cells[canonical([p['dimension'], '/'.join(p['knowledge_profiles']), t])] += 1
    signals = {}
    for flag in PATTERNS:
        hits = [r for r in lexical if flag in r['flags']]
        signals[flag] = dict(rows=len(hits), actions=dict(Counter(r['action'] for r in hits)),
                             stories=len({r['story'] for r in hits}))
    joint = [r for r in lexical if {'prohibited_topic_words','quotation_or_negation_words'} <= set(r['flags'])]
    summary = dict(rows=len(rows), stories=len({r['scene_family_id'] for r in rows}),
        actions=dict(actions), layers={k:dict(v) for k,v in layers.items()},
        tool_cells=dict(tool_cells), unique_visible_inputs=len(by_input), unique_message_history=len(by_surface),
        duplicate_groups=len(duplicates), duplicate_extra_rows=sum(len(d['ids'])-1 for d in duplicates),
        conflicting_trained_target_groups=len(conflicts), invariant_violations=len(invariants),
        exposure_histogram=dict(Counter(exposure.values())), lexical_signals=signals,
        quoted_or_negated_topic_candidates=dict(rows=len(joint), actions=dict(Counter(r['action'] for r in joint))),
        strict_pair_summary=pair_summary, strict_pair_check_error=pair_error, strict_pair_tool_cells=dict(pair_cells),
        limitations=['Lexical hits are retrieval hints, not exhaustive semantic annotation or proof of an error.',
                     'Single-field pairs are structural evidence, not independent human-reviewed examples.',
                     'This audit cannot establish a causal explanation for model errors.'])
    return dict(summary=summary, invariants=invariants, duplicates=duplicates, conflicts=conflicts,
                lexical_candidates=lexical, text_review_ids=[r['id'] for r in lexical if needs_text_review(r)],
                pairs=pairs)


def build():
    before = {n:sha(ROOT/n) for n in INPUTS}
    # Check training-file bytes against the already completed experiment, without opening evaluation data.
    protocol = read(ROOT/'results/financial-2b-full-coverage-v1/protocol.json')
    bindings = protocol['common_binding']['source_sha256']
    for name in INPUTS[:2]:
        if bindings.get(name) != before[name]: raise ValueError('Frozen training input changed: '+name)
    rows = read(ROOT/INPUTS[0]) + read(ROOT/INPUTS[1])
    steps = read(ROOT/INPUTS[2])['step_rows']
    result = analyze(rows, steps)
    if len(rows) != 13378 or Counter(i for step in steps for i in step) != Counter({r['id']:2 for r in rows}):
        raise ValueError('Expected two complete passes of frozen 13378 rows')
    if before != {n:sha(ROOT/n) for n in INPUTS}: raise ValueError('Training source mutated during audit')
    result.update(training_eligible=False, evaluation_examples_read=False, inference_requests=0, model_api_requests=0,
                  sources=before, audit_script_sha256=sha(Path(__file__)))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in [('audit.json',result), ('summary.json',result['summary'])]:
        (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1: raise SystemExit('No custom data paths accepted; training-only fixed inputs.')
    build()
