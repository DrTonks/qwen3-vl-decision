"""Offline development diagnostics after the fixed pilot; no model/API calls."""
import argparse
from collections import Counter,defaultdict
import json
import random

from qwenlab.common import ROOT,sha
from qwenlab import financial_train as ft


def cluster_interval(rows, reference, candidate, seed=20261001, repeats=2000):
    """Paired action-accuracy delta, conservative groups include whole macro stories."""
    groups = defaultdict(list)
    for row in rows:
        groups[row['curation']['partition_group']].append(row['id'])
    keys = sorted(groups)
    truth = {r['id']:r['annotation']['action'] for r in rows}
    effects = {key:(sum((candidate[i]['action']==truth[i])-(reference[i]['action']==truth[i])
        for i in ids),len(ids)) for key,ids in groups.items()}
    rng = random.Random(seed)
    draws = []
    for _ in range(repeats):
        sampled = [effects[rng.choice(keys)] for _ in keys]
        draws.append(sum(x[0] for x in sampled)/sum(x[1] for x in sampled))
    return dict(cluster_count=len(keys),resamples=repeats,
        interval95=[ft.metrics.percentile(draws,.025),ft.metrics.percentile(draws,.975)],
        cluster_key='effective partition_group, including macro-scene unions',
        limitation='Only eight authored macro stories in development; synthetic cluster CI is not real-user generalization.')


def stratify(rows, predictions):
    result = {}
    for profile in sorted({r['input']['capability_profile'] for r in rows}):
        subset = [r for r in rows if r['input']['capability_profile']==profile]
        result[profile] = dict(rows=len(subset),
            action_accuracy=sum(predictions[r['id']]['action']==r['annotation']['action'] for r in subset)/len(subset),
            human_misses=sum(r['annotation']['action']=='human' and predictions[r['id']]['action']!='human' for r in subset),
            unavailable_retrievals=sum(not r['input']['capabilities']['knowledge_collections'] and predictions[r['id']]['action']=='retrieve' for r in subset))
    return result


def tool_results(rows, predictions):
    result = {}
    for tool in ft.prompts.TOOLS:
        subset = [r for r in rows if r['annotation']['tool_name']==tool]
        routed = [r for r in subset if predictions[r['id']]['action']=='tool']
        joint = sum(predictions[r['id']]['action']=='tool' and predictions[r['id']]['tool_name']==tool for r in subset)
        result[tool] = dict(support=len(subset),routed_tool=len(routed),joint_correct=joint,
            joint_accuracy=joint/len(subset) if subset else None,
            selected_correct_given_routed=joint/len(routed) if routed else None,
            wrong_action_counts=dict(Counter(predictions[r['id']]['action'] for r in subset if predictions[r['id']]['action']!='tool')))
    return result


def changes(rows, reference, candidate):
    improved,regressed=[],[]
    for row in rows:
        identifier,truth = row['id'],row['annotation']['action']
        before,after = reference[identifier]['action'],candidate[identifier]['action']
        item=dict(id=identifier,gold=truth,before=before,after=after)
        if before!=truth and after==truth: improved.append(item)
        if before==truth and after!=truth: regressed.append(item)
    return dict(improved=len(improved),regressed=len(regressed),net=len(improved)-len(regressed),
        improved_ids=improved,regressed_ids=regressed,
        usage='development diagnosis only; do not append these errors to frozen training data')


def validate_selection(completion, selected, reports, protocol, protocol_hash):
    """Recompute the entire fixed selection, without rewriting execution evidence."""
    variants = ['step-'+str(n) for n in protocol['config']['pilot']['checkpoint_steps']]
    gates = {v:ft.metrics.development_gate(reports['base'],reports[v],
        protocol['config']['development_gate']) for v in variants}
    passing = [v for v in variants if gates[v]['passed']]
    winner = max(passing,key=lambda v:(reports[v]['macro_f1'],
        reports[v]['action_tool_joint_accuracy'],-int(v.split('-')[1]))) if passing else None
    expected = dict(selected=winner,gates=gates,passed=bool(passing),
        usage='development_candidate_only',default_provider_changed=False,
        calibration_evaluated=False,final_evaluated=False,protocol_sha256=protocol_hash)
    if selected!=expected:
        raise ValueError('Recorded selection differs from independently recomputed selection')
    if (completion.get('status')!='pilot_complete' or
            completion.get('protocol_sha256')!=protocol_hash or
            completion.get('selection')!=expected or
            completion.get('model_api_requests')!=0 or completion.get('deployed') is not False):
        raise ValueError('Completion is not bound to this protocol and selection')
    return expected


def analyze(name=None):
    run = ft.Run(ft.active_name(name))
    completion = ft.read(run.out/'completion.json')
    if completion.get('status')!='pilot_complete':
        raise ValueError('Wait for the complete fixed pilot, not an intermediate checkpoint')
    protocol = ft.read(run.out/'protocol.json')
    for path,digest in protocol['source_sha256'].items():
        if sha(ROOT/path)!=digest: raise ValueError('Execution source changed: '+path)
    if sha(ft.data.OUT/'manifest.json')!=protocol['dataset_manifest_sha256']:
        raise ValueError('Dataset changed')
    rows = ft.data.evaluation_rows('development')
    variants = ['base','step-100','step-200']
    reports,predictions={},{}
    for variant in variants:
        raw=ft.rows_file(run.out/variant/'predictions.jsonl')
        reports[variant]=ft.finalize_evaluation(run,variant,protocol,rows,raw)
        predictions[variant]={r['id']:r for r in raw}
    summary = ft.read(run.out/'training-summary.json')
    logs = ft.rows_file(run.out/'train.jsonl')
    if [x['step'] for x in logs]!=list(range(1,201)) or summary['optimizer_steps']!=200:
        raise ValueError('Incomplete or repeated training steps')
    if sum(summary['sampled_by_id'].values())!=1600 or summary['sample_positions']!=1600:
        raise ValueError('Coverage mismatch')
    if (len(summary['sampled_by_id'])!=summary['unique_rows'] or
            summary['repeated_positions']!=1600-summary['unique_rows'] or
            sum(summary['sampled_by_stratum'].values())!=1600):
        raise ValueError('Unique/repeated/stratum coverage mismatch')
    selected=ft.read(run.out/'selection.json')
    validate_selection(completion,selected,reports,protocol,run.protocol_hash())
    evidence = [run.out/p for p in ['protocol.json','completion.json','selection.json',
        'training-summary.json','train.jsonl']]
    evidence += [run.out/v/p for v in variants for p in
        ['predictions.jsonl','metrics.json','timing.json','binding.json']]
    result=dict(protocol_sha256=run.protocol_hash(),analysis_source_sha256=sha(ROOT/'src/qwenlab/financial_pilot_analysis.py'),
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in evidence},
        partition='development',rows=len(rows),profiles={v:stratify(rows,p) for v,p in predictions.items()},
        tools={v:tool_results(rows,p) for v,p in predictions.items()},
        pairs={v:changes(rows,predictions['base'],predictions[v]) for v in variants[1:]},
        paired_accuracy_intervals={v:cluster_interval(rows,predictions['base'],predictions[v]) for v in variants[1:]},
        train_coverage={k:summary[k] for k in ['sample_positions','unique_rows','repeated_positions','sampled_by_stratum','sampled_tools','training_elapsed_s','peak_allocated_gib']},
        training_loss=dict(first20_mean=sum(r['weighted_loss'] for r in logs[:20])/20,
            last20_mean=sum(r['weighted_loss'] for r in logs[-20:])/20,
            note='Stochastic train batches differ; not a fixed-set train accuracy or a measured generalization gap.'),
        selection=selected,calibration_evaluated=False,final_evaluated=False,jev_evaluated=False)
    ft.durable_json(run.out/'diagnostics.json',result)
    lines=['# 金融八动作试训分层诊断','',
        '只分析固定200步预算的开发集，不执行模型推理、不调用Jev，不读取校准/最终作为错题来源。','',
        '|动作|基础召回|100步召回|200步召回|基础F1|100步F1|200步F1|','|---|---:|---:|---:|---:|---:|---:|']
    for action in ft.prompts.ACTIONS:
        values=[reports[v]['per_action'][action] for v in variants]
        lines.append('|'+action+'|'+'|'.join(f'{m[metric]:.2%}' for metric in ['recall','f1'] for m in values)+'|')
    lines+=['','|工具|支持数|基础联合正确|100步联合正确|200步联合正确|','|---|---:|---:|---:|---:|']
    for tool in ft.prompts.TOOLS:
        values=[result['tools'][v][tool] for v in variants]
        lines.append('|'+tool+'|'+str(values[0]['support'])+'|'+'|'.join(f"{m['joint_correct']}/{m['support']}" for m in values)+'|')
    lines+=['','工具联合失败拆解（动作选错，或已选tool但工具名选错）：']
    for variant in variants:
        values=result['tools'][variant]
        wrong_action=sum(m['support']-m['routed_tool'] for m in values.values())
        wrong_tool=sum(m['routed_tool']-m['joint_correct'] for m in values.values())
        lines.append(f'- {variant}：动作未选tool {wrong_action} 条，已选tool但工具名错 {wrong_tool} 条。')
    lines+=['','|条件|版本|条数|动作准确率|人工漏判|不可用检索|','|---|---|---:|---:|---:|---:|']
    for variant in variants:
        for profile,m in result['profiles'][variant].items():
            lines.append(f"|{profile}|{variant}|{m['rows']}|{m['action_accuracy']:.2%}|{m['human_misses']}|{m['unavailable_retrievals']}|")
    lines+=['','同题改对/改错与动作准确率差的保守分组区间：']
    for variant in variants[1:]:
        pair=result['pairs'][variant];ci=result['paired_accuracy_intervals'][variant]
        lines.append(f"- {variant}：改对{pair['improved']}、改错{pair['regressed']}、净多对{pair['net']}；"
            f"{ci['cluster_count']}组bootstrap差值95%区间[{ci['interval95'][0]:.2%}, {ci['interval95'][1]:.2%}]。")
    lines+=['','仅8个宏故事，生成风格相关且开发已经用于选型，以上区间不能推断真实客户准确率。','',
        f"抽样1600位置中不同训练行{summary['unique_rows']}，重复位置{summary['repeated_positions']}。",
        f"训练加权损失前20步均值{result['training_loss']['first20_mean']:.4f}，后20步{result['training_loss']['last20_mean']:.4f}；抽样组成变化，不等于固定训练集准确率。",'',
        '过拟合判断：本轮尚未对固定候选做独立最终检验，因此不能排除过拟合；训练损失下降和开发提升只提供有限证据。',
        '如果动作提高而工具联合下降，应先看是路由拒绝查询还是具体工具选择错误，不能将两者混称工具模型失败。',
        '门槛失败时结束本预算并保留现有默认provider；不部署失败候选，不放宽门槛，不自动追加训练。通过时只获得开发候选资格，后续仍需冻结校准和最终对照。',
        '本集未评Jev、未做参数/后端保护/端到端比较，旧V5不是同一八动作契约，不直接作数值排名。']
    (run.out/'diagnostics.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=run.out.relative_to(ROOT).as_posix(),selected=selected['selected'],
        unique_train_rows=summary['unique_rows'],diagnostics='complete_development_only'),ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name')
    args=parser.parse_args();analyze(args.run_name)


if __name__=='__main__':main()
