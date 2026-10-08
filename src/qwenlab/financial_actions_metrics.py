"""Measure model decisions separately from backend argument grounding."""
from collections import Counter
import math
import hashlib
import json
from qwenlab.financial_pilot import ACTIONS, serialize_input


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    place = (len(values)-1)*q
    lo, hi = math.floor(place), math.ceil(place)
    return values[lo]+(values[hi]-values[lo])*(place-lo)


def evaluate(rows, predictions, prompt_sha256=None, protocol_sha256=None):
    truth = {r['id']:r for r in rows}
    predicted = {p['id']:p for p in predictions}
    if (len(truth)!=len(rows) or len(predicted)!=len(predictions) or set(truth)!=set(predicted)):
        raise ValueError('Predictions must cover the exact split IDs once')
    partitions = {r.get('split') for r in rows}
    if len(partitions)>1:
        raise ValueError('Do not aggregate different evaluation partitions for selection')
    partition = next(iter(partitions), None)
    confusion, per_action = Counter(), {}
    human_misses, false_refusals, unavailable_retrieval = [], [], []
    tool_rows, joint_tool, status_rows, status_correct = 0, 0, 0, 0
    parameters = {s:dict(rows=0, correct=0) for s in ['model','trusted_state_parser']}
    elapsed, tokens = [], []
    for row in rows:
        pred, a = predicted[row['id']], row['annotation']
        actual = pred.get('action')
        confusion[a['action'], actual if actual in ACTIONS else 'invalid'] += 1
        if actual!='tool' and pred.get('tool_name') is not None:
            raise ValueError('End-to-end record cannot contain a gold/oracle tool after a non-tool prediction')
        if a['action']=='human' and actual!='human':
            human_misses.append(row['id'])
        if a['action']!='refuse' and actual=='refuse':
            false_refusals.append(row['id'])
        if not row['input']['capabilities']['knowledge_collections'] and actual=='retrieve':
            unavailable_retrieval.append(row['id'])
        if a['action']=='tool':
            tool_rows += 1
            joint = actual=='tool' and pred.get('tool_name')==a['tool_name']
            joint_tool += joint
            if a['tool_name']=='explainApplicationStatus':
                status_rows += 1
                status_correct += joint
            source = pred.get('argument_source')
            if source in parameters:
                parameters[source]['rows'] += 1
                parameters[source]['correct'] += joint and pred.get('tool_arguments')==a['tool_arguments']
        if 'elapsed_s' in pred:
            value = pred['elapsed_s']
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError('Invalid measured elapsed time')
            elapsed.append(value)
        if 'input_tokens' in pred:
            if type(pred['input_tokens']) is not int or pred['input_tokens']<=0:
                raise ValueError('Invalid observed input token count')
            tokens.append(pred['input_tokens'])
    for action in ACTIONS:
        tp = confusion[action,action]
        support = sum(n for (gold,_),n in confusion.items() if gold==action)
        count = sum(n for (_,guess),n in confusion.items() if guess==action)
        precision = tp/count if count else 0
        recall = tp/support if support else 0
        per_action[action] = dict(support=support, precision=precision, recall=recall,
            f1=2*precision*recall/(precision+recall) if precision+recall else 0)
    fingerprint = hashlib.sha256(json.dumps(sorted((r['id'],serialize_input(r),r['annotation']) for r in rows),
        sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return dict(rows=len(rows), data_sha256=fingerprint, partition=partition,
        prompt_sha256=prompt_sha256, protocol_sha256=protocol_sha256,
        action_accuracy=sum(confusion[a,a] for a in ACTIONS)/len(rows) if rows else None,
        macro_f1=sum(v['f1'] for v in per_action.values())/len(ACTIONS), per_action=per_action,
        confusion={a:{p:confusion[a,p] for p in ACTIONS+['invalid']} for a in ACTIONS},
        human_misses=human_misses, false_refusals=false_refusals,
        unavailable_knowledge_retrievals=unavailable_retrieval,
        tool_support=tool_rows, action_tool_joint_accuracy=joint_tool/tool_rows if tool_rows else None,
        status_tool_support=status_rows, status_tool_accuracy=status_correct/status_rows if status_rows else None,
        parameter_results={s:dict(**v, accuracy=v['correct']/v['rows'] if v['rows'] else None)
                           for s,v in parameters.items()},
        latency=dict(measured_rows=len(elapsed), p50_s=percentile(elapsed,.5), p95_s=percentile(elapsed,.95)),
        input_tokens=dict(measured_rows=len(tokens),p50=percentile(tokens,.5),p95=percentile(tokens,.95)),
        note='Trusted-state parameter results are backend grounding, not learned argument generation. '
             'Correlated macro stories require cluster-aware uncertainty; sample counts are not independent user counts.')


def development_gate(base, candidate, policy):
    for report in [base,candidate]:
        if report.get('partition')!='development':
            raise ValueError('Only development results may select a candidate')
        if type(report.get('rows')) is not int or report['rows']<=0:
            raise ValueError('A nonempty development split is required')
        for name in ['data_sha256','prompt_sha256','protocol_sha256']:
            value = report.get(name)
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Missing frozen evaluation binding: '+name)
        if set(report['per_action'])!=set(ACTIONS) or sum(v['support'] for v in report['per_action'].values())!=report['rows']:
            raise ValueError('Development requires all eight action supports')
        values = [report['macro_f1'],report['action_tool_joint_accuracy'],report['status_tool_accuracy']]
        for v in report['per_action'].values():
            if type(v['support']) is not int or v['support']<=0:
                raise ValueError('Development action support cannot be empty')
            values.extend([v['precision'],v['recall'],v['f1']])
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in values):
            raise ValueError('Development metrics must be finite probabilities')
    if base['prompt_sha256']!=candidate['prompt_sha256'] or base['protocol_sha256']!=candidate['protocol_sha256']:
        raise ValueError('Compare the same frozen prompt and protocol')
    if base['data_sha256']!=candidate['data_sha256'] or base['rows']!=candidate['rows']:
        raise ValueError('Compare the same frozen evaluation inputs and targets')
    failures = []
    if candidate['macro_f1']-base['macro_f1'] < policy['minimum_macro_f1_gain_over_same_prompt_base']:
        failures.append('insufficient_action_macro_f1_gain')
    if any(v['recall']<policy['minimum_per_action_recall'] for v in candidate['per_action'].values()):
        failures.append('per_action_recall')
    if candidate['per_action']['human']['recall']<policy['minimum_human_recall']:
        failures.append('human_recall')
    if len(candidate['human_misses'])-len(base['human_misses'])>policy['maximum_extra_human_misses_over_base']:
        failures.append('extra_human_misses')
    if len(candidate['false_refusals'])-len(base['false_refusals'])>policy['maximum_extra_false_refusals_on_non_refuse_over_base']:
        failures.append('extra_false_refusals')
    if len(candidate['unavailable_knowledge_retrievals'])>policy['maximum_unavailable_knowledge_retrievals']:
        failures.append('unavailable_knowledge_retrieval')
    for field, floor in [('action_tool_joint_accuracy','minimum_joint_action_tool_accuracy_on_true_tool'),
                         ('status_tool_accuracy','minimum_status_tool_accuracy')]:
        if candidate[field] is None or candidate[field]<policy[floor]:
            failures.append(field)
    return dict(passed=not failures, failures=failures, usage='development_only_not_final_selection')
