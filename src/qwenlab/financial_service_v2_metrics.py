"""New-contract component metrics; current service is never hidden by KB totals."""
import math
import random
from collections import defaultdict
from qwenlab import financial_actions_metrics as legacy
from qwenlab.financial_prompt_v2 import SPEC


def wilson(success,total):
    if not total:return None
    z=1.959963984540054;p=success/total;d=1+z*z/total
    center=(p+z*z/(2*total))/d
    width=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [max(0,center-width),min(1,center+width)]


def bootstrap(rows,predictions,repeats=1000):
    groups=defaultdict(list);lookup={p['id']:p for p in predictions}
    for r in rows:groups[r['scene_family_id']].append(r)
    keys=sorted(groups);rng=random.Random(20261003);values=defaultdict(list)
    for _ in range(repeats):
        sample=[r for _ in keys for r in groups[rng.choice(keys)]]
        correct=human_ok=humans=tool_ok=tools=0
        for r in sample:
            a=r['annotation'];p=lookup[r['id']]
            correct+=a['action']==p['action']
            if a['action']=='human':humans+=1;human_ok+=p['action']=='human'
            if a['action']=='tool':tools+=1;tool_ok+=p['action']=='tool' and p['tool_name']==a['tool_name']
        if sample:values['action_accuracy'].append(correct/len(sample))
        if humans:values['human_recall'].append(human_ok/humans)
        if tools:values['joint_tool_accuracy'].append(tool_ok/tools)
    return dict(story_groups=len(keys),resamples=repeats,seed=20261003,
                intervals={k:dict(low=legacy.percentile(v,.025),high=legacy.percentile(v,.975),valid_resamples=len(v)) for k,v in values.items()},
                note='Percentile cluster bootstrap within this synthetic set, not evidence of production generalization; zero errors may give degenerate intervals.')


def validate_prediction(p):
    for task in ['action']+(['tool'] if p['action']=='tool' else []):
        value=p[task+'_prediction'];keys=SPEC['actions' if task=='action' else 'tools']
        probs=value['probabilities'];logits=value['logits']
        if set(probs)!=set(keys) or len(logits)!=len(keys):raise ValueError('Wrong candidate layout')
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in logits):raise ValueError('Invalid logits')
        if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in probs.values()):raise ValueError('Invalid probability')
        if abs(sum(probs.values())-1)>1e-5:raise ValueError('Unnormalized probabilities')
        maximum=max(logits);weights=[math.exp(x-maximum) for x in logits];total=sum(weights)
        if any(abs(probs[k]-weights[i]/total)>1e-5 for i,k in enumerate(keys)):raise ValueError('Probability/logit mismatch')
        choice=keys[max(range(len(keys)),key=logits.__getitem__)]
        if choice!=value['choice'] or choice!=p['action' if task=='action' else 'tool_name']:
            raise ValueError('Choice inconsistent with logits')


def basic(rows,predictions,prompt_sha256,protocol_sha256):
    report=legacy.evaluate(rows,predictions,prompt_sha256,protocol_sha256)
    lookup={p['id']:p for p in predictions}
    report['unauthenticated_tool_actions']=[r['id'] for r in rows if not r['input']['state']['authenticated'] and lookup[r['id']]['action']=='tool']
    report['unavailable_tool_choices']=[r['id'] for r in rows if lookup[r['id']]['action']=='tool' and lookup[r['id']]['tool_name'] not in r['input']['available_tools']]
    report['macro_f1_observed_actions']=sum(v['f1'] for v in report['per_action'].values() if v['support'])/sum(bool(v['support']) for v in report['per_action'].values()) if rows else None
    report['wilson_action_accuracy']=wilson(sum(p['action']==r['annotation']['action'] for r,p in ((r,lookup[r['id']]) for r in rows)),len(rows))
    report['wilson_action_recall']={a:wilson(round(v['recall']*v['support']),v['support']) for a,v in report['per_action'].items()}
    report['story_bootstrap']=bootstrap(rows,predictions)
    return report


def evaluate(rows,predictions,prompt_sha256=None,protocol_sha256=None):
    for p in predictions:validate_prediction(p)
    report=basic(rows,predictions,prompt_sha256,protocol_sha256)
    report['cohorts']={}
    for cohort in sorted({r['cohort'] for r in rows}):
        block=[r for r in rows if r['cohort']==cohort];ids={r['id'] for r in block}
        report['cohorts'][cohort]=basic(block,[p for p in predictions if p['id'] in ids],prompt_sha256,protocol_sha256)
    return report


def development_gate(base,candidate,config):
    result=legacy.development_gate(base,candidate,config['development_gate'])
    failures=result['failures']
    b=base['cohorts']['current-service'];c=candidate['cohorts']['current-service'];g=config['current_service_additional_gate']
    if b['data_sha256']!=c['data_sha256']:raise ValueError('Cohort data mismatch')
    if not c['per_action']['human']['support'] or c['per_action']['human']['recall']<g['minimum_human_recall']:failures.append('current_human_recall')
    if len(c['human_misses'])-len(b['human_misses'])>g['maximum_extra_human_misses_over_base']:failures.append('current_extra_human_misses')
    if len(c['false_refusals'])-len(b['false_refusals'])>g['maximum_extra_false_refusals_on_non_refuse_over_base']:failures.append('current_extra_false_refusals')
    if len(c['unavailable_knowledge_retrievals'])>g['maximum_unavailable_knowledge_retrievals']:failures.append('current_unavailable_retrieval')
    if c['action_tool_joint_accuracy'] is None or c['action_tool_joint_accuracy']<g['minimum_joint_action_tool_accuracy_on_true_tool']:failures.append('current_joint_tool_accuracy')
    if len(candidate['unauthenticated_tool_actions'])>config['preauth_additional_gate']['maximum_tool_actions']:failures.append('preauth_tool_action')
    if len(candidate['unavailable_tool_choices'])>config['capability_additional_gate']['maximum_unavailable_tool_choices']:failures.append('unavailable_tool_choice')
    result.update(passed=not failures)
    return result
