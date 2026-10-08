"""Offline audit of finished arms; preserve the failed frozen selector verbatim.

The original selector mixed study and arm protocol hashes. Re-evaluate the
validated raw predictions under each arm's evaluation context, without changing
predictions, stored metrics, thresholds, training, or held-out data.
"""
import argparse
from collections import Counter
from pathlib import Path

from qwenlab import qwen35_boundary_study as s, financial_jev_cache as cache
from qwenlab.common import ROOT, sha

ft = s.ft
OUT = ROOT / 'results/financial-qwen35-boundary-v1/recovery'


def validate_arm_protocol(study_protocol, arm_protocol, label, study_hash):
    if label not in s.ARMS or arm_protocol != dict(study_protocol, arm=label, study_protocol_sha256=study_hash):
        raise ValueError('Arm differs from the exact frozen study plus declared arm identity')


def compare_in_arm_context(protocol, arm_protocol, label, study_hash, arm_hash, rows, raw, predicted):
    validate_arm_protocol(protocol, arm_protocol, label, study_hash)
    base = ft.metrics.evaluate(rows, raw, protocol['prompt_sha256'], arm_hash)
    candidate = ft.metrics.evaluate(rows, predicted, protocol['prompt_sha256'], arm_hash)
    return ft.metrics.development_gate(base, candidate, protocol['config']['development_gate'])


def require_no_passing(gates):
    if any(g['passed'] for g in gates.values()):
        raise RuntimeError('Passing candidate requires separately reviewed holdout recovery; no holdout was read')


def paired_changes(rows, before, after):
    truth = {r['id']: r['annotation']['action'] for r in rows}
    a = {r['id']: r['action'] for r in before}
    b = {r['id']: r['action'] for r in after}
    if set(a) != set(truth) or set(b) != set(truth):
        raise ValueError('Different populations')
    return dict(fixed=[i for i in truth if a[i] != truth[i] and b[i] == truth[i]],
                regressed=[i for i in truth if a[i] == truth[i] and b[i] != truth[i]])


def compact(name, report, historical=False):
    return dict(variant=name, accuracy=report['action_accuracy'], macro_f1=report['macro_f1'],
        joint=report['action_tool_joint_accuracy'], human_misses=len(report['human_misses']),
        false_refusals=len(report['false_refusals']),
        p50_ms=report['latency']['p50_s']*1000, p95_ms=report['latency']['p95_s']*1000,
        historical_timing=historical)


def audit():
    study = s.Study()
    # No GPU loading or training: validates immutable dependencies and existing protocols.
    protocol = s.freeze(study, True)
    cfg = protocol['config']
    rows = ft.data.evaluation_rows('development')
    parent = s.cycle.Run(cfg['initial_run'])
    raw = ft.rows_file(parent.out/'development/base/predictions.jsonl')
    initial = ft.rows_file(parent.out/'development/step-2976/predictions.jsonl')
    raw_m = ft.metrics.evaluate(rows, raw, protocol['prompt_sha256'], study.protocol_hash())
    initial_m = ft.metrics.evaluate(rows, initial, protocol['prompt_sha256'], study.protocol_hash())
    table = [compact('raw_base', raw_m, True), compact('initial_step2976', initial_m, True)]
    gates, changes, coverage, bindings = {}, {}, {}, {}
    predicted = {}
    for label in s.ARMS:
        arm = s.Arm(study, label)
        validate_arm_protocol(protocol, ft.read(arm.out/'protocol.json'), label, study.protocol_hash())
        complete = ft.read(arm.out/'arm-completion.json')
        if complete['protocol_sha256'] != arm.protocol_hash() or complete['steps'] != cfg['max_steps']:
            raise ValueError('Both arms must have completed before offline selection')
        records = s.records(label)
        schedule = s.schedule(len(records), cfg['train_rows'], cfg['seed'])
        expected = Counter(records[i]['id'] for i in schedule)
        summary = ft.read(arm.out/'training-summary.json')
        logs = ft.rows_file(arm.out/'train.jsonl')
        if (Counter(summary['sampled_by_id']) != expected or summary['sample_positions'] != cfg['train_rows']
                or [r['step'] for r in logs] != list(range(1, cfg['max_steps']+1))):
            raise ValueError('Coverage or committed training steps differ from budget')
        coverage[label] = dict(steps=len(logs), positions=sum(expected.values()), unique_rows=len(expected),
                              training_minutes=summary['training_elapsed_s']/60)
        # The raw baseline is evaluated within this verified arm context, not
        # falsely compared against a different protocol hash or altered in place.
        for step in cfg['checkpoint_steps']:
            variant = f'step-{step}'
            folder = arm.out/'development'/variant
            if ft.read(folder/'binding.json') != s.cycle.eval_binding(arm, variant, 'development'):
                raise ValueError('Checkpoint or evaluation binding differs')
            pred = ft.rows_file(folder/'predictions.jsonl')
            metrics = ft.metrics.evaluate(rows, pred, protocol['prompt_sha256'], arm.protocol_hash())
            if metrics != ft.read(folder/'metrics.json'):
                raise ValueError('Stored metrics differ from actual predictions')
            key = f'{label}/{variant}'
            gates[key] = compare_in_arm_context(protocol, ft.read(arm.out/'protocol.json'), label,
                study.protocol_hash(), arm.protocol_hash(), rows, raw, pred)
            changes[key] = paired_changes(rows, initial, pred)
            predicted[key] = pred
            table.append(compact(key, metrics))
            for name in ['binding.json', 'predictions.jsonl', 'metrics.json', 'timing.json']:
                bindings[(folder/name).relative_to(ROOT).as_posix()] = sha(folder/name)
    # Do not let this recovery tool silently authorize unreviewed GPU/holdout work.
    require_no_passing(gates)
    jr, jp, _ = cache.load_cached('development')
    if jr != rows:
        raise ValueError('Cached Jev population differs')
    table.append(compact('Jev-1.13.0-cached', ft.metrics.evaluate(jr, jp), True))
    between = {str(step): paired_changes(rows, predicted[f'replay/step-{step}'], predicted[f'overlay/step-{step}'])
               for step in cfg['checkpoint_steps']}
    return dict(study_protocol_sha256=study.protocol_hash(), recovery_source_sha256=sha(Path(__file__)),
        original_status=ft.read(study.out/'status.json'), original_status_sha256=sha(study.out/'status.json'),
        repair='Verify exact arm/study contracts, then re-evaluate raw baseline under each arm hash before unchanged gate',
        development=table, gates=gates, coverage=coverage, changes_from_initial=changes,
        overlay_vs_replay_changes=between, result_bindings=bindings,
        selected=None, passed=False, training_complete=True, final_evaluated=False, calibration_evaluated=False,
        model_api_requests=0, new_training_steps=0, deployed=False,
        limitations=['Repeatedly observed synthetic development with only eight macro stories',
                    'Historical and staged timings are not a controlled speed comparison',
                    'AI-reviewed synthetic boundary additions; no human review or multimodal training',
                    'Jev zero-shot project policy vs supervised Qwen; not a universal ability ranking'])


def finish():
    result = audit()
    OUT.mkdir(parents=True, exist_ok=True)
    s.immutable_json(OUT/'audit.json', result)
    s.immutable_json(OUT/'selection.json', dict(passed=False, selected=None, gates=result['gates'],
        study_protocol_sha256=result['study_protocol_sha256'], recovery_source_sha256=result['recovery_source_sha256']))
    lines = ['# 0.8B边界对照续训结果', '',
        '两个训练分支均完成。原收尾程序因总协议/分支协议编号混用而失败；本报告为保留原始记录后的离线核验。', '',
        '|版本|开发动作准确率|宏F1|动作+工具联合|人工漏判/64|误拒绝|P50/P95毫秒|',
        '|---|---:|---:|---:|---:|---:|---:|']
    for t in result['development']:
        lines.append(f"|{t['variant']}|{t['accuracy']:.2%}|{t['macro_f1']:.4f}|{t['joint']:.2%}|{t['human_misses']}|{t['false_refusals']}|{t['p50_ms']:.1f}/{t['p95_ms']:.1f}|")
    lines += ['', '**六个候选均未通过原开发门槛。未进入校准或最终测试，不部署，不继续追加训练。**', '',
        '原数据回放384步消除了误拒绝，但人工漏判4/64，人工召回93.75%，低于95%门槛；其他五个候选仍有误拒绝。',
        '加入336条边界对照没有在本轮固定预算下取得全面改进。新增分支从384到1530步动作正确数下降，且误拒绝增加；继续加步数未显示收益。',
        '不能据此证明全部真实业务过拟合，但应将其视为开发集回退信号。开发集被反复观察且只有8个合成宏故事，不能把高分等同泛化能力。',
        '两个分支相同步数的差异仅几题，单次种子与模板数据不足以断言新增数据必然无效或有害。',
        '保持既有默认provider，不自动切换本轮候选。先独立核对任务契约、模板偏差和训练目标，再设计新的预先固定实验；不要继续围绕开发错题追加样本。',
        '所有表格是同384条开发集的组件指标。Jev使用已缓存预测，零新增API；其零样本策略与Qwen已训练策略不同。速度受阶段、硬件负载和网络影响，不宣称本轮获得因果加速。', '',
        '## 固定门槛结果', '']
    for key, gate in result['gates'].items():
        lines.append(f"- {key}: {', '.join(gate['failures'])}")
    lines += ['', '## 对照与完整性', '']
    for label, cov in result['coverage'].items():
        lines.append(f"- {label}: {cov['steps']}步、{cov['positions']}个样本位置、{cov['unique_rows']}个唯一记录ID，纯训练{cov['training_minutes']:.1f}分钟。")
    for step, change in result['overlay_vs_replay_changes'].items():
        lines.append(f"- 同第{step}步，overlay相对replay动作改对{len(change['fixed'])}条、改错{len(change['regressed'])}条。")
    (OUT/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    s.immutable_json(OUT/'completion.json', dict(status='offline_recovery_complete_no_candidate',
        audit_sha256=sha(OUT/'audit.json'), report_sha256=sha(OUT/'report.md'),
        original_frozen_execution_modified=False, trained_again=False, model_api_requests=0,
        calibration_evaluated=False, final_evaluated=False, selected=None))
    print(__import__('json').dumps(dict(output=OUT.relative_to(ROOT).as_posix(), passed=False, selected=None), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['finish'])
    parser.parse_args()
    finish()
