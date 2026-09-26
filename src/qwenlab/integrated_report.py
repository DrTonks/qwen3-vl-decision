"""Recompute audit tables from completed frozen predictions, without GPU/API work."""
from collections import Counter, defaultdict
import random
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows
from qwenlab.joint_v4 import OUT, DATA, dump
from qwenlab.summarize import percentile


def accuracy_all(rows, task):
    if not rows:
        raise ValueError('Empty evaluation')
    return sum(not r.get('error') and r.get('predictions', {}).get(task, {}).get('choice') == r['labels'][task]
               for r in rows) / len(rows)


def business_counts(rows):
    """Failures are misses in the relevant gold subpopulation, never omitted."""
    humans = [r for r in rows if r['labels']['route'] == 'human']
    tools = [r for r in rows if r['labels']['route'] == 'tool']
    def choice(r, task):
        return None if r.get('error') else r.get('predictions', {}).get(task, {}).get('choice')
    return {'n': len(rows), 'human_required': len(humans),
            'human_missed': sum(choice(r, 'route') != 'human' for r in humans),
            'human_false_positive': sum(r['labels']['route'] != 'human' and choice(r, 'route') == 'human' for r in rows),
            'tool_required': len(tools),
            'joint_tool_correct': sum(choice(r, 'route') == 'tool' and choice(r, 'tool') == r['labels']['tool'] for r in tools),
            'all_fields_correct': sum(not r.get('error') and all(choice(r, t) == r['labels'][t] for t in ('intent', 'route', 'tool')) for r in rows),
            'tool_route_without_tool': sum(choice(r, 'route') == 'tool' and choice(r, 'tool') == 'none' for r in rows),
            'errors': sum(bool(r.get('error')) for r in rows)}


def aligned_latency(rows, ids):
    index = {r['id']: r for r in rows}
    if len(index) != len(rows) or len(set(ids)) != len(ids) or not set(ids) <= set(index):
        raise ValueError('Invalid latency alignment')
    values = [index[i]['elapsed_s'] for i in ids if not index[i].get('error')]
    return {'requested': len(ids), 'successful': len(values), 'errors': len(ids) - len(values),
            'p50_s': percentile(values, .5), 'p95_s': percentile(values, .95)}


def table(headers, rows):
    return ['|' + '|'.join(headers) + '|', '|' + '|'.join(['---'] * len(headers)) + '|'] + [
        '|' + '|'.join(map(str, row)) + '|' for row in rows]


def paired_speed(timings):
    pairs = defaultdict(dict)
    for r in timings:
        key = (r['id'], r['repeat'])
        if r['mode'] in pairs[key]:
            raise ValueError('Duplicate timing')
        pairs[key][r['mode']] = r['elapsed_s']
    groups = defaultdict(list)
    for (row_id, _), values in pairs.items():
        if set(values) != {'full', 'candidate'}:
            raise ValueError('Unpaired timings')
        groups[row_id].append(values['full'] - values['candidate'])
    # Repeated timings for the same request are not independent observations.
    values = [sum(xs) / len(xs) for xs in groups.values()]
    if not values:
        raise ValueError('No paired timings')
    rng = random.Random(20260926)
    boot = [sum(rng.choices(values, k=len(values))) / len(values) for _ in range(2000)]
    return {'request_groups': len(groups), 'mean_saved_s': sum(values) / len(values),
            'group_bootstrap_95_s': [percentile(boot, .025), percentile(boot, .975)],
            'scope': 'one device session; exploratory paired timing, not production latency guarantee'}


def main():
    for path in (OUT / 'completion.json', OUT / 'candidate-benchmark/status.json'):
        if load_json(path)['status'] != 'complete':
            raise RuntimeError('Evaluation and speed experiment must both finish first')
    m = load_json(OUT / 'metrics.json'); selected = m['selected']
    train = load_json(OUT / 'training-summary.json'); speed = load_json(OUT / 'candidate-benchmark/metrics.json')
    agreement_path = OUT / 'candidate-benchmark/agreement.jsonl'
    agreement = read_rows(agreement_path)
    if len(agreement) != speed['n_task_predictions'] or sum(r['full_choice'] != r['candidate_choice'] for r in agreement) != speed['choice_mismatches']:
        raise AssertionError('Speed agreement aggregate mismatch')
    if abs(max(r['max_probability_delta'] for r in agreement) - speed['max_probability_delta']) > 1e-12:
        raise AssertionError('Probability delta aggregate mismatch')
    variants = list(dict.fromkeys(['base', selected, 'jev']))
    labels = {'base': 'Qwen NF4 基础模型', selected: f'Qwen QLoRA（{selected}）', 'jev': 'Jev 1.13.0'}
    source_paths = [OUT / 'metrics.json', OUT / 'selection.json', OUT / 'training-summary.json',
                    OUT / 'candidate-benchmark/metrics.json', OUT / 'candidate-benchmark/protocol.json', agreement_path,
                    ROOT / 'src/qwenlab/integrated_report.py']
    datasets = ('business', 'massive', 'legacy-business', 'crosswoz')
    predictions = {}
    for variant in variants:
        for name in datasets:
            path = OUT / variant / f'{name}-test.jsonl'; rows = read_rows(path)
            if len({r['id'] for r in rows}) != len(rows):
                raise ValueError('Duplicate prediction IDs')
            predictions[variant, name] = rows; source_paths.append(path)
            for task, saved in m['runs'][f'{variant}/{name}']['tasks'].items():
                if abs(accuracy_all(rows, task) - saved['accuracy_all_requests']) > 1e-12:
                    raise AssertionError('Published metric does not match original predictions')
    for name in datasets:
        reference = {r['id']: r['labels'] for r in predictions['base', name]}
        if any({r['id']: r['labels'] for r in predictions[v, name]} != reference for v in variants):
            raise ValueError('Models evaluated different inputs/labels')
    summary = {'selected': selected, 'source_sha256': {}, 'effects': [], 'business': {}, 'latency': {},
               'speed_experiment': speed, 'calibration': [], 'comparisons_common_success_only': m['comparisons']}
    lines = ['# 效果与速度验证总表', '',
             '本报告在第四轮完整评测和独立加速实验均完成后，从逐条预测重新计算准确率，并核对既有指标。没有重新训练、修改标签或按测试成绩重选检查点。', '',
             '**业务挑战为未人工复核的合成数据；公开与旧业务测试为回归，不能等同真实客服上线效果。**', '',
             '**结论：本轮训练有明显成效，但尚未达到“各项能力仅略弱于 Jev”。**', '',
             f'- MASSIVE 中文意图从 {accuracy_all(predictions["base", "massive"], "intent"):.2%} 提升到 {accuracy_all(predictions[selected, "massive"], "intent"):.2%}，说明扩大训练后的公共意图区分有收益。',
             f'- 新业务意图为 {accuracy_all(predictions[selected, "business"], "intent"):.2%}，Jev 为 {accuracy_all(predictions["jev", "business"], "intent"):.2%}；业务路由虽改善，仍有意图边界与标签质量问题。',
             f'- CrossWOZ 迁移从 {accuracy_all(predictions["base", "crosswoz"], "intent"):.2%} 降到 {accuracy_all(predictions[selected, "crosswoz"], "intent"):.2%}，Jev 为 {accuracy_all(predictions["jev", "crosswoz"], "intent"):.2%}。这是明确的迁移短板，不能被业务高分掩盖。',
             '- 保留本轮适配器作为后续研究候选；不据本轮结果直接替换真实客服决策。速度收益与输出层优化是否可采用分别见第 4、5 节。', '',
             '## 1. 同一协议下的准确率', '',
             '表中 API 失败计为错误；单位为百分比。不同数据集不混算总分。']
    effect_rows = []
    for name, title, tasks in [('business', '新业务挑战（180）', ['intent', 'route', 'tool']),
                               ('massive', 'MASSIVE 中文（2,974）', ['intent']),
                               ('legacy-business', '旧业务回归（72）', ['intent', 'route', 'tool']),
                               ('crosswoz', 'CrossWOZ 迁移（200）', ['intent'])]:
        for task in tasks:
            values = {v: accuracy_all(predictions[v, name], task) for v in variants}
            item = {'dataset': name, 'task': task, 'accuracy_all_requests': values,
                    'gain_vs_base_pp': 100 * (values[selected] - values['base']),
                    'gap_vs_jev_pp': 100 * (values[selected] - values['jev'])}
            summary['effects'].append(item)
            task_name = {'intent': '意图', 'route': '路由', 'tool': '工具（含 none）'}[task]
            effect_rows.append([title, task_name] + [f'{values[v]:.2%}' for v in variants] +
                               [f'{item["gain_vs_base_pp"]:+.2f}', f'{item["gap_vs_jev_pp"]:+.2f}'])
    lines += [''] + table(['数据', '任务', '基础模型', '微调模型', 'Jev', '微调−基础（百分点）', '微调−Jev（百分点）'], effect_rows)
    api_errors = {name: m['runs'][f'jev/{name}']['errors'] for name in datasets}
    lines += ['', 'Jev 请求失败数：' + '，'.join(f'{k}={v}' for k, v in api_errors.items()) + '。',
              'MASSIVE 的 Jev 成功请求准确率与全部请求准确率不同，不能把两个分母混用。工具准确率包含无需工具时的 none，请结合下一表。', '',
              '## 2. 新业务挑战的完整决策链路', '']
    for v in variants:
        summary['business'][v] = business_counts(predictions[v, 'business'])
    biz_rows = []
    for title, field, denom in [('路由与工具同时正确（需要工具）', 'joint_tool_correct', 'tool_required'),
                                ('必须人工但漏转（越少越好）', 'human_missed', 'human_required'),
                                ('意图、路由、工具全部正确', 'all_fields_correct', 'n')]:
        biz_rows.append([title] + [f'{summary["business"][v][field]}/{summary["business"][v][denom]}' for v in variants])
    for title, field in [('误转人工条数', 'human_false_positive'), ('路由为 tool 却给 none 条数', 'tool_route_without_tool')]:
        biz_rows.append([title] + [summary['business'][v][field] for v in variants])
    biz_rows.append(['路由宏 F1'] + [f'{m["runs"][v+"/business"]["tasks"]["route"]["macro_f1_gold_supported_classes"]:.4f}' for v in variants])
    lines += table(['指标', '基础模型', '微调模型', 'Jev'], biz_rows)
    lines += ['', '联合工具正确同时要求 route=tool 且工具名正确；本实验没有执行真实工具或验证参数。人工标记由路由推导，不是额外独立能力。', '',
              '## 3. 差距有多确定', '',
              '下面采用场景/对话组配对 bootstrap 的 95% 区间，差值为微调−Jev。API 失败只在本表的共同成功配对子集中排除，与第一表的全部请求口径区别标明。', '']
    ci_rows = []
    for name, tasks in m['comparisons'].items():
        for task, values in tasks.items():
            ci = values.get('trained_minus_jev')
            if ci:
                ci_rows.append([name, task, ci['n'], ci['groups'], f'{ci["accuracy_difference"]*100:+.2f}',
                                f'[{ci["group_bootstrap_95"][0]*100:+.2f}, {ci["group_bootstrap_95"][1]*100:+.2f}]'])
    lines += table(['集合', '任务', '配对条数', '组数', '差值（百分点）', '95% 区间（百分点）'], ci_rows)
    lines += ['', '区间跨零不等于两个模型等效；小样本、共享模板和标签歧义仍限制推断。看到的近似成绩不自动满足“各项能力仅略弱于 Jev”。', '',
              '### 为什么 Jev 在新业务集与旧回归的分数不同', '',
              '新集增加同一问句下的已有记录、缺失登录状态、不可用工具和前后端状态冲突；分布与旧 72 条不同。不能用分数差推断 Jev 本身退步。']
    raw_business = {r['id']: r for r in read_rows(DATA / 'business-test.jsonl')}
    intent_error_groups = Counter(r['group'] for r in predictions[selected, 'business']
                                  if r['labels']['intent'] != r['predictions']['intent']['choice'])
    summary['selected_intent_error_groups'] = dict(intent_error_groups)
    if intent_error_groups:
        group, count = intent_error_groups.most_common(1)[0]
        example = next(r for r in raw_business.values() if r['group'] == group)
        lines += ['', f'微调模型的 {sum(intent_error_groups.values())} 条新业务意图错误集中于 {len(intent_error_groups)} 个表达组；其中 {count} 条来自“{example["message"]}”这一表达的状态变体。不能把这些变体当成同等数量的独立语义失败；需要检查界面问题与申请详情等相邻意图的边界。']
    jev_route_errors = [r for r in predictions['jev', 'business'] if not r.get('error') and r['labels']['route'] != r['predictions']['route']['choice']]
    error_conditions = Counter(raw_business[r['id']]['condition'] for r in jev_route_errors)
    summary['jev_route_error_conditions'] = dict(error_conditions)
    lines += ['', 'Jev 路由错例按原标签对应的状态分布：' + '，'.join(f'{k} {v} 条' for k,v in error_conditions.most_common()) + '。',
              '已有记录是否足以回答必须结合用户原话判断，不能只因 record 字段存在就自动认定 llm。当前生成器把同一业务家族的多种问法套用同一简略记录，存在标签歧义：例如“比较这里几款贷款的条件”，只提供一款示例产品及额度/期数，并不充分支持比较。此时继续查询可能合理。',
              '这些问题作为标签待复核记录，未根据任何模型的预测修改本轮标签或重算一个更好看的分数。本实验只对 Qwen 做了相同生成课程的领域训练，未对 Jev 做同等适配；合成集胜出可能包含对生成规则的适应，必须由独立真实样本确认。', '',
              '## 4. 单客户请求速度', '',
              '本地：固定新业务测试前 32 条，每条串行执行意图、路由、工具三个前向，含分词和结果回传，排除加载与预热。Jev：取同一批 ID 的已记录请求，包含网络和服务端处理，一次联合返回字段。', '']
    raw = read_rows(DATA / 'business-test.jsonl'); ids = [r['id'] for r in raw[:32]]
    latency_rows = []
    for v in variants:
        if v == 'jev':
            value = aligned_latency(predictions[v, 'business'], ids)
        else:
            path = OUT / v / 'latency.json'; value = load_json(path); source_paths.append(path)
            if value['n'] != len(ids) or len(value['values_s']) != len(ids):
                raise ValueError('Latency sample count changed')
        summary['latency'][v] = value
        latency_rows.append([labels[v], len(ids), f'{value["p50_s"]*1000:.1f}', f'{value["p95_s"]*1000:.1f}'])
    lines += table(['实现', '请求数', 'P50（ms）', 'P95（ms）'], latency_rows)
    a, b = summary['latency'][selected], summary['latency']['jev']
    ratios = {k: b[k] / a[k] for k in ('p50_s', 'p95_s')}; summary['jev_to_local_latency_ratio'] = ratios
    lines += ['', f'在这些已记录请求上，Jev 延迟/本地微调模型延迟为 P50 {ratios["p50_s"]:.2f} 倍、P95 {ratios["p95_s"]:.2f} 倍。',
              '这是实际调用方案的观测对照，不是相同硬件的模型算力对照；两边不是同一时刻压测。前 32 条按数据顺序选取，覆盖有限；不能推算全业务吞吐或生产 SLA。', '',
              '## 5. 候选输出层加速是否成立', '',
              f'独立开发集对比 {speed["n_task_predictions"]} 个任务，类别不一致 **{speed["choice_mismatches"]}** 次；最大概率差 **{speed["max_probability_delta"]:.6f}**，最大原始分数差 {speed["max_logit_delta"]:.6f}。', '']
    lines += table(['输出层', 'P50（ms）', 'P95（ms）'], [[mode, f'{v["p50_s"]*1000:.1f}', f'{v["p95_s"]*1000:.1f}'] for mode, v in speed['latency'].items()])
    lines += ['', '正数表示缩短延迟：' + '，'.join(f'{k}={v:+.2%}' for k, v in speed['relative_latency_reduction'].items()) + '。',
              f'预设一致性门槛：{"通过" if speed["agreement_gate_pass"] else "未通过"}；速度门槛：{"通过" if speed["speed_gate_pass"] else "未通过"}。',
              '**当前默认推理实现没有替换。** ' + ('两项通过，可进入独立回归与校准复核。' if speed['agreement_gate_pass'] and speed['speed_gate_pass'] else '至少一项未通过，当前不建议采用该优化。'),
              '此表使用开发集固定 12 条请求各重复 3 次，交替测试顺序，不能与上一表的测试前 32 条混为同一组。重复测量相关，5% 是探索门槛。仍执行三个完整前向，未改变首 token 分类方法，也未测 Mugi。', '',
              '## 6. 校准是否改善置信度', '',
              '温度在独立校准集拟合，下面是固定温度应用到 test 的结果；NLL、Brier、ECE 越低越好。准确率不变。', '']
    timing_path = OUT / 'candidate-benchmark/latency.jsonl'
    timings = read_rows(timing_path)
    for mode in ('full', 'candidate'):
        for q in (.5, .95):
            actual = percentile([r['elapsed_s'] for r in timings if r['mode'] == mode], q)
            if abs(actual - speed['latency'][mode][f'p{int(q*100)}_s']) > 1e-12:
                raise AssertionError('Speed latency aggregate mismatch')
    timing_ci = paired_speed(timings); source_paths.append(timing_path)
    summary['paired_speed'] = timing_ci
    ci = timing_ci['group_bootstrap_95_s']
    insert_at = lines.index('## 6. 校准是否改善置信度')
    lines[insert_at:insert_at] = [f'将三次重复先按请求平均，再按 {timing_ci["request_groups"]} 个请求组重采样：平均节省 {timing_ci["mean_saved_s"]*1000:.2f} ms，探索性 95% 区间 [{ci[0]*1000:.2f}, {ci[1]*1000:.2f}] ms。负数表示变慢；只反映本次设备会话的波动。', '']
    cal_rows = []
    for dataset, tasks in [('business', ('intent', 'route')), ('massive', ('intent',))]:
        cal = m['calibration'][f'{selected}/{dataset}']
        for task in tasks:
            before = m['runs'][f'{selected}/{dataset}']['tasks'][task]; after = cal['metrics'][task]
            if before['correct'] != after['correct']:
                raise AssertionError('Calibration changed choices')
            item = {'dataset': dataset, 'task': task, 'temperature': cal['temperatures'][task]['temperature'],
                    'before': {k: before[k] for k in ('nll', 'brier_multiclass_sum', 'ece_10_equal_width')},
                    'after': {k: after[k] for k in ('nll', 'brier_multiclass_sum', 'ece_10_equal_width')},
                    'selective_0.9': after['selective']['0.9']}
            summary['calibration'].append(item)
            cal_rows.append([dataset, task, f'{item["temperature"]:.3f}'] + [f'{before[k]:.4f} → {after[k]:.4f}' for k in item['before']])
    lines += table(['集合', '任务', '温度 T', 'NLL', 'Brier', 'ECE'], cal_rows)
    lines += ['', '固定 0.9 阈值仅作描述，未用测试集搜索最佳阈值：', '']
    lines += table(['集合/任务', '接受数量', '覆盖率', '接受样本中的错误'], [
        [r['dataset']+'/'+r['task'], r['selective_0.9']['accepted'], f'{r["selective_0.9"]["coverage"]:.2%}', r['selective_0.9']['errors']] for r in summary['calibration']])
    lines += ['', '即使路由高置信度，工具仍可能选错；上述门槛不是完整工具执行链的安全保证，也未上线自动兜底。', '',
              '## 7. 训练资源、复现与结论边界', '',
              f'训练 {train["optimizer_steps"]} 步，{train["elapsed_s"]/3600:.2f} 小时，峰值 allocated {train["peak_allocated_gib"]:.3f} GiB、reserved {train["peak_reserved_gib"]:.3f} GiB；单种子、单轮遍历，基础视觉模块冻结但未验证图像性能。',
              '本轮与基础模型差异包含扩大数据和任务权重共同作用；四个检查点不能证明数据规模的独立因果效果。',
              '新业务错例和状态切片见 [诊断报告](../results/joint-v4/diagnostics/analysis.md)。',
              '阅读顺序见 [完整导航](00-阅读导航.md)，训练细节见 [第四轮方案](06-扩大数据与联合训练.md)，后续安排见 [下一步](08-训练后的验证与下一步.md)。', '',
              '本报告命令：`python -m qwenlab.integrated_report`。它只读完成后的结果，重算准确率和链路计数，不调用 API、不使用 GPU。',
              '机器可读表及源文件 SHA256 保存为 `results/joint-v4/verification-tables.json`；逐条预测和速度记录保留，可核查分母与计时。']
    recovery_path = OUT / 'recovery.json'
    if recovery_path.exists():
        recovery = load_json(recovery_path)
        if recovery['status'] != 'complete':
            raise RuntimeError('Recovery has not completed')
        summary['recovery'] = recovery; source_paths.append(recovery_path)
        lines += ['', '### 运行中断与恢复', '',
                  '原评测进程及完成器在微调模型公共测试写出前退出，日志没有异常栈，底层原因未确认。训练已完成，权重和已有结果保留。',
                  '恢复脚本校验冻结源码哈希，调用原单样本评分函数，仅补缺失的集合预测与计时，随后完成迁移/校准/报告。没有重训、更换检查点或改标签。详见 `results/joint-v4/recovery.json`。']
    overhead_path = OUT / 'adapter-overhead/metrics.json'
    if overhead_path.exists():
        overhead = load_json(overhead_path)
        if overhead['status'] != 'complete':
            raise RuntimeError('Adapter timing control incomplete')
        summary['adapter_overhead'] = overhead
        source_paths += [overhead_path, OUT / 'adapter-overhead/timings.jsonl', OUT / 'adapter-overhead/protocol.json']
        lo, hi = overhead['paired_group_bootstrap_95_s']
        lines += ['', '## 8. 为什么微调后略慢：同进程控制实验', '',
                  '原独立加载记录中，微调后 P50 从 367.0ms 到 382.0ms。为进一步区分适配器开销和硬件波动，补做同一模型进程内交替启用/禁用 LoRA 的实验；32 条相同输入，每种模式重复三次，切换开关不计时。', '']
        lines += table(['LoRA 分支', 'P50（ms）', 'P95（ms）'], [
            [mode, f'{v["p50_s"]*1000:.2f}', f'{v["p95_s"]*1000:.2f}'] for mode,v in overhead['latency'].items()])
        lines += ['', f'启用后的开销：P50 {overhead["relative_overhead"]["p50_s"]:+.2%}，P95 {overhead["relative_overhead"]["p95_s"]:+.2%}；平均每请求多 {overhead["paired_mean_overhead_s"]*1000:.2f}ms，按请求组 bootstrap 的探索性 95% 区间 [{lo*1000:.2f}, {hi*1000:.2f}]ms。',
                  f'与原冻结预测不一致次数：{overhead["choice_differences_vs_frozen_reference"]}，每种模式比较 288 个任务预测。',
                  '本地 PEFT 的 NF4 LoRA 实现在基础线性层之外执行 A/B 两个投影、缩放与加法，包含输入/输出类型转换；本次加载的适配器参数为 float32。更多小算子有额外开销，参数少不等于推理免费。',
                  '同进程交替对照支持“启用适配器带来额外耗时”，不是模型学会后思考更久。所有请求仍执行相同的三个分类前向；硬件温度、调度等波动不能完全排除。',
                  '没有测合并后的权重。NF4 下合并涉及量化误差与实现差异，不能直接承诺合并后完全同分；若另测合并/重量化，应重新做一致性、准确率、校准和延迟验证。',
                  '该附加实验不覆盖第 4 节的原始记录；完整记录见 [适配器开销](../results/joint-v4/adapter-overhead/summary.md)。']
    summary['source_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths}
    dump(OUT / 'verification-tables.json', summary)
    (ROOT / 'docs/09-效果与速度验证.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Verified prediction tables and wrote docs/09-效果与速度验证.md')


if __name__ == '__main__':
    main()
