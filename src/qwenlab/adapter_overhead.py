"""Same-process paired timing to isolate enabled LoRA inference overhead."""
from collections import defaultdict
from contextlib import nullcontext
import random
import time
import torch
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.joint_v4 import OUT, DATA, CKPT, dump, predict_rows
from qwenlab.modeling import load_model
from qwenlab.summarize import percentile


def main():
    if load_json(OUT / 'candidate-benchmark/status.json')['status'] != 'complete':
        raise RuntimeError('Previous GPU benchmark must finish first')
    folder = OUT / 'adapter-overhead'
    if folder.exists():
        raise FileExistsError('Keep the prior measurement')
    folder.mkdir()
    selected = load_json(OUT / 'selection.json')['selected']
    rows = read_rows(DATA / 'business-test.jsonl')[:32]
    dump(folder / 'protocol.json', {
        'selected': selected, 'sample_ids': [r['id'] for r in rows], 'repetitions': 3,
        'method': 'same loaded NF4+PEFT model; disable_adapter vs enabled; alternating per request; switching outside timer; 3 serial task forwards',
        'includes': 'tokenization, padding, model forward, probability processing and CPU output',
        'excludes': 'loading, warmup, adapter switching',
        'source_sha256': sha(ROOT / 'src/qwenlab/adapter_overhead.py'),
        'input_sha256': sha(DATA / 'business-test.jsonl'),
        'limits': 'not a standalone base vs merged model comparison; no merge, no retraining'})
    tok, model = load_model('nf4', (CKPT / selected).relative_to(ROOT).as_posix())
    tok.padding_side = 'left'; model.eval()
    references = {mode: {r['id']: r for r in read_rows(OUT / variant / 'business-test.jsonl')}
                  for mode, variant in [('disabled', 'base'), ('enabled', selected)]}
    timings = []; differences = defaultdict(int)
    with torch.inference_mode():
        for mode in ('disabled', 'enabled'):
            with model.disable_adapter() if mode == 'disabled' else nullcontext():
                for row in rows[:2]:
                    predict_rows(tok, model, [row])
        for repeat in range(3):
            for i, row in enumerate(rows):
                for mode in (('disabled', 'enabled') if (i + repeat) % 2 == 0 else ('enabled', 'disabled')):
                    with model.disable_adapter() if mode == 'disabled' else nullcontext():
                        torch.cuda.synchronize(); start = time.perf_counter()
                        pred = predict_rows(tok, model, [row])[0]
                        torch.cuda.synchronize(); elapsed = time.perf_counter() - start
                    timings.append({'id': row['id'], 'repeat': repeat, 'mode': mode, 'elapsed_s': elapsed})
                    for task in ('intent', 'route', 'tool'):
                        differences[mode] += pred['predictions'][task]['choice'] != references[mode][row['id']]['predictions'][task]['choice']
            print('Completed paired repeat', repeat + 1, flush=True)
    write_rows(folder / 'timings.jsonl', timings)
    latency = {mode: {f'p{int(q*100)}_s': percentile([r['elapsed_s'] for r in timings if r['mode'] == mode], q)
                      for q in (.5, .95)} for mode in ('disabled', 'enabled')}
    pairs = defaultdict(dict)
    for r in timings:
        pairs[r['id'], r['repeat']][r['mode']] = r['elapsed_s']
    grouped = defaultdict(list)
    for (row_id, repeat), values in pairs.items():
        grouped[row_id].append(values['enabled'] - values['disabled'])
    values = [sum(xs)/len(xs) for xs in grouped.values()]
    rng = random.Random(20260926)
    boot = [sum(rng.choices(values, k=len(values)))/len(values) for _ in range(2000)]
    result = {'latency': latency, 'relative_overhead': {k: latency['enabled'][k]/latency['disabled'][k]-1 for k in ('p50_s', 'p95_s')},
              'request_groups': len(rows), 'repetitions': 3, 'requests_per_mode': len(rows)*3,
              'paired_mean_overhead_s': sum(values)/len(values),
              'paired_group_bootstrap_95_s': [percentile(boot,.025), percentile(boot,.975)],
              'choice_differences_vs_frozen_reference': dict(differences),
              'compared_task_predictions_per_mode': len(rows)*3*3,
              'adapter_parameter_dtypes': sorted({str(p.dtype) for n,p in model.named_parameters() if 'lora_' in n}),
              'gpu': torch.cuda.get_device_name(), 'status': 'complete',
              'limits': ['one device session, 32 ordered business inputs', 'disabled LoRA wrapper is not a separately loaded base model',
                         'does not isolate every kernel or prove zero hardware effects', 'not an adapter merge experiment']}
    dump(folder / 'metrics.json', result)
    lines = ['# LoRA 推理开销的同进程对照', '',
             '同一个已加载模型、相同输入、相同 GPU，逐请求交替禁用/启用适配器；切换开关不计时。32 条请求，每种模式各重复三次。', '',
             '|模式|P50（ms）|P95（ms）|', '|---|---:|---:|']
    for mode, v in latency.items():
        lines.append(f'|{mode}|{v["p50_s"]*1000:.2f}|{v["p95_s"]*1000:.2f}|')
    lo, hi = result['paired_group_bootstrap_95_s']
    lines += ['', f'启用后的相对开销：P50 {result["relative_overhead"]["p50_s"]:+.2%}，P95 {result["relative_overhead"]["p95_s"]:+.2%}。',
              f'按请求分组的平均额外耗时 {result["paired_mean_overhead_s"]*1000:.2f} ms，探索性 95% 区间 [{lo*1000:.2f}, {hi*1000:.2f}] ms。',
              f'与原冻结记录比较的类别不一致次数：{dict(differences)}（每种模式 288 个任务预测）。',
              '该实验隔离启用适配器分支的开销，但不等同于加载基础模型或合并权重后的部署。硬件波动不能完全消除。',
              '没有合并 NF4 权重、修改原始测试成绩或开启新训练。']
    (folder / 'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(result, flush=True)


if __name__ == '__main__':
    main()
