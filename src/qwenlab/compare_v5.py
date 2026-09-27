"""Bounded vendor evaluation and matched-input local latency, never training."""
import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import math
import random
import time
import urllib.request
from qwenlab.common import ROOT, input_state, load_json, append_json, sha
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.joint_v5 import DATA, OUT, atomic_json, encode, exclusive_lock, adapter_for
from qwenlab.summarize import percentile, paired_ci

TARGET = OUT / 'comparison'


def protocol():
    selected = load_json(OUT / 'selection.json')['selected']
    rows = read_rows(DATA / 'business-test.jsonl')
    expected = {'selected': selected, 'api_max_requests': 402, 'api_retries': 0,
        'api_expected_model': 'jev-1.13.0', 'started_scope': 'same v5 business policy, input and 3 questions',
        'data_sha256': sha(DATA / 'business-test.jsonl'), 'spec_sha256': sha(ROOT / 'configs/decision-v5.json'),
        'source_sha256': sha(ROOT / 'src/qwenlab/compare_v5.py'),
        'latency_ids': [r['id'] for r in random.Random(20260927).sample(rows, 32)], 'local_repetitions': 3,
        'local_scope': 'one NF4 model; LoRA disabled=base; enabled=selected; same inputs/order rotated across 3 modes; batch1 three serial forwards; tokenizer+CPU transfer; load/warmup excluded',
        'vendor_scope': 'one HTTP call returns 3 questions; latency includes network; selected matching IDs once, not repeated or same hardware',
        'no_training_use': True}
    TARGET.mkdir(exist_ok=True); path = TARGET / 'protocol.json'
    if path.exists() and load_json(path) != expected: raise ValueError('Comparison protocol changed')
    if not path.exists(): atomic_json(path, expected)
    return expected, rows


def vendor():
    cfg, rows = protocol(); path = TARGET / 'jev-business-test.jsonl'
    if len(rows) > cfg['api_max_requests']: raise ValueError('Request cap exceeded')
    if path.exists(): raise FileExistsError('No automatic API retries or overwriting')
    state = {'status': 'starting', 'total': len(rows), 'completed': 0, 'errors': 0,
             'started_utc': datetime.now(timezone.utc).isoformat(), 'retries': 0}
    atomic_json(TARGET / 'jev-status.json', state)
    try:
        key = (ROOT / '.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
        if not key or any(c.isspace() for c in key): raise ValueError('Invalid credential format')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *unused): return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        def call(endpoint, payload=None):
            req = urllib.request.Request('https://api.typesafe.ai' + endpoint,
                data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
                headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            with opener.open(req, timeout=30) as response: return json.load(response)
        available = call('/v1/models'); names = [x['name'] for x in available['models']]
        requested = cfg['api_expected_model'] if cfg['api_expected_model'] in names else 'jev-latest'
        if requested not in names: raise ValueError('Pinned vendor version/alias unavailable')
        state.update(status='running', requested_model=requested, expected_model=cfg['api_expected_model'])
        atomic_json(TARGET / 'jev-status.json', state)
        spec = load_json(ROOT / 'configs/decision-v5.json')
        questions = {k: {'type': 'choice', **spec['questions'][k]} for k in ('intent', 'route', 'tool')}
        for i, row in enumerate(rows):
            result = {k: row[k] for k in ('id', 'group', 'labels')}; result['predictions'] = {}
            started = time.perf_counter()
            try:
                body = call('/v1/systemone', {'model': requested, 'state': {'policy': spec['policy'], 'input': input_state(row)}, 'questions': questions})
                if body.get('model') != cfg['api_expected_model']: raise ValueError('Resolved vendor model differs')
                for name, question in questions.items():
                    answer = body['answers'][name]; probs = answer['probabilities']
                    if set(probs) != set(question['criteria']) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()) or abs(sum(probs.values()) - 1) > .03:
                        raise ValueError('Invalid probability schema')
                    if answer['choice'] not in probs: raise ValueError('Invalid choice')
                    result['predictions'][name] = {'choice': answer['choice'], 'probabilities': probs}
                result['raw_tool'] = result['predictions']['tool'].copy()
                if result['predictions']['route']['choice'] != 'tool': result['predictions']['tool'] = {'choice': 'none', 'derived': True}
                result.update(model=body['model'], usage=body.get('usage'))
            except Exception as exc:
                result.update(error=type(exc).__name__, status=getattr(exc, 'code', None)); state['errors'] += 1
                result['predictions'] = {}  # Partial multi-question answers are a failed request.
            result['elapsed_s'] = time.perf_counter() - started
            append_json(path, result); state['completed'] = i + 1
            state['elapsed_s'] = time.time() - datetime.fromisoformat(state['started_utc']).timestamp()
            atomic_json(TARGET / 'jev-status.json', state)
            if (i + 1) % 25 == 0: print('Jev', i + 1, '/', len(rows), 'errors', state['errors'], flush=True)
            if result.get('status') in (401, 402, 403, 429) or state['errors'] >= 3 or (result.get('error') == 'ValueError'):
                raise RuntimeError('Stopped on API/schema/version error; no hidden retries')
        state['status'] = 'complete'; atomic_json(TARGET / 'jev-status.json', state)
    except Exception as exc:
        state.update(status='failed', error=type(exc).__name__, http_status=getattr(exc, 'code', None))
        atomic_json(TARGET / 'jev-status.json', state)
        print('Vendor comparison failed:', type(exc).__name__, getattr(exc, 'code', None), flush=True)
        raise SystemExit(1)  # Never print credential-bearing request objects.


def local():
    cfg, all_rows = protocol()
    if (TARGET / 'local-latency.jsonl').exists(): raise FileExistsError('Preserve measured timing')
    state = {'status': 'loading', 'completed': 0, 'total': 32 * 3 * 3}
    atomic_json(TARGET / 'local-status.json', state)
    try:
        import torch
        from qwenlab.modeling import load_model
        from qwenlab.candidate_inference import CandidateScorer
        tok, model = load_model('nf4', adapter_for(cfg['selected'])); tok.padding_side = 'left'; model.eval()
        scorer = CandidateScorer(model)
        source = {r['id']: r for r in all_rows}; rows = [source[i] for i in cfg['latency_ids']]
        refs = {v: {r['id']: r for r in read_rows(OUT / v / 'business-test.jsonl')} for v in ('base', cfg['selected'])}
        modes = ['base-full', 'trained-full', 'trained-candidate']
        def request(row, mode):
            predictions = {}
            with model.disable_adapter() if mode == 'base-full' else nullcontext():
                for task in ('intent', 'route', 'tool'):
                    x = encode(tok, row, task); inputs = tok.pad([x['tokens']], padding=True, return_tensors='pt').to('cuda')
                    scores = scorer.scores(inputs, x['ids'])[0] if mode == 'trained-candidate' else model(**inputs, logits_to_keep=1, use_cache=False).logits[0, -1, x['ids']].float()
                    probs = scores.softmax(-1).cpu().tolist()
                    predictions[task] = x['keys'][max(range(len(probs)), key=probs.__getitem__)]
            if predictions['route'] != 'tool': predictions['tool'] = 'none'
            return predictions
        differences = {m: 0 for m in modes}
        with torch.inference_mode():
            for mode in modes:
                for row in rows[:2]: request(row, mode)
            state['status'] = 'running'; atomic_json(TARGET / 'local-status.json', state)
            times = []
            for repeat in range(3):
                for i, row in enumerate(rows):
                    offset = (repeat + i) % len(modes); order = modes[offset:] + modes[:offset]
                    for mode in order:
                        torch.cuda.synchronize(); start = time.perf_counter(); pred = request(row, mode); torch.cuda.synchronize()
                        elapsed = time.perf_counter() - start
                        reference = refs['base' if mode == 'base-full' else cfg['selected']][row['id']]['predictions']
                        differences[mode] += sum(pred[t] != reference[t]['choice'] for t in ('intent', 'route', 'tool'))
                        item = {'id': row['id'], 'repeat': repeat, 'mode': mode, 'elapsed_s': elapsed, 'predictions': pred}
                        append_json(TARGET / 'local-latency.jsonl', item); times.append(item)
                        state['completed'] += 1
                    atomic_json(TARGET / 'local-status.json', state)
        atomic_json(TARGET / 'local-metrics.json', {'choice_differences_vs_frozen': differences,
            'projection': scorer.projection, 'fallback': scorer.fallback_reason,
            'latency': {m: {f'p{int(q*100)}_s': percentile([r['elapsed_s'] for r in times if r['mode'] == m], q) for q in (.5, .95)} for m in modes}})
        state['status'] = 'complete'; atomic_json(TARGET / 'local-status.json', state)
    except Exception as exc:
        state.update(status='failed', error=type(exc).__name__); atomic_json(TARGET / 'local-status.json', state); raise


def accuracy(rows, task):
    return sum(not r.get('error') and r['predictions'].get(task, {}).get('choice') == r['labels'][task] for r in rows) / len(rows)


def report():
    cfg, rows = protocol()
    if any(load_json(TARGET / f'{k}-status.json')['status'] != 'complete' for k in ('jev', 'local')): raise RuntimeError('Comparison not finished')
    jev = read_rows(TARGET / 'jev-business-test.jsonl')
    if [r['id'] for r in jev] != [r['id'] for r in rows]: raise ValueError('Vendor coverage mismatch')
    predictions = {v: read_rows(OUT / v / 'business-test.jsonl') for v in ('base', 'v4-reference', cfg['selected'])}
    predictions['jev'] = jev
    results = {}; lines = ['# 第五轮：原始Qwen、微调Qwen与Jev对照', '',
        '新增402次Jev评估，无自动重试；输入、业务政策与三项问题相同。基础模型为NF4原始Qwen3-VL-2B；不是BF16或生成式基线。', '',
        '|同一402条业务测试|意图准确率|路由准确率|工具必要联合正确|人工漏转|请求失败|', '|---|---:|---:|---:|---:|---:|']
    for variant, rs in predictions.items():
        result = {'n': len(rs), 'accuracy_all_requests': {t: accuracy(rs, t) for t in ('intent', 'route', 'tool')},
            'errors': sum(bool(r.get('error')) for r in rs),
            'joint_tool_correct': sum(not r.get('error') and r['labels']['route'] == 'tool' and r['predictions']['route']['choice'] == 'tool' and r['predictions']['tool']['choice'] == r['labels']['tool'] for r in rs),
            'tool_required': sum(r['labels']['route'] == 'tool' for r in rs),
            'human_missed_or_failed': sum(r['labels']['route'] == 'human' and (bool(r.get('error')) or r['predictions']['route']['choice'] != 'human') for r in rs),
            'human_required': sum(r['labels']['route'] == 'human' for r in rs)}
        results[variant] = result
        lines.append(f'|{variant}|{result["accuracy_all_requests"]["intent"]:.2%}|{result["accuracy_all_requests"]["route"]:.2%}|{result["joint_tool_correct"]}/{result["tool_required"]}|{result["human_missed_or_failed"]}/{result["human_required"]}|{result["errors"]}|')
    ci = {t: paired_ci(predictions[cfg['selected']], jev, t) for t in ('intent', 'route')}
    local_stats = load_json(TARGET / 'local-metrics.json')
    if any(local_stats['choice_differences_vs_frozen'].values()): raise ValueError('Local timing decisions differ from frozen reference')
    jev_by_id = {r['id']: r for r in jev}; matched = [jev_by_id[i] for i in cfg['latency_ids']]
    latency = dict(local_stats['latency'])
    latency['jev'] = {f'p{int(q*100)}_s': percentile([r['elapsed_s'] for r in matched if not r.get('error')], q) for q in (.5, .95)}
    lines += ['', '|同32条业务输入|P50 ms|P95 ms|', '|---|---:|---:|']
    for mode, values in latency.items(): lines.append(f'|{mode}|{values["p50_s"]*1000:.2f}|{values["p95_s"]*1000:.2f}|')
    lines += ['', '本地每条输入三次串行前向，三轮交替重复；Jev一次HTTP请求联合返回三项问题，每个ID一次，含网络。本地含分词与结果回传、不含加载/预热。这是调用方案对照，非相同硬件或相同架构的比较。',
        'base-full是在同一加载模型中禁用LoRA，逐条决策已与独立基础模型冻结预测核对。不能把不同输入的第四轮367ms或本轮此前其他样本计时混入本表。', '',
        '## 公共测试的历史Jev参考', '', '|任务|NF4基础|第五轮|Jev 1.13.0历史|', '|---|---:|---:|---:|']
    public = {}
    for name in ('massive', 'crosswoz'):
        source = ROOT / f'results/joint-v4/jev/{name}-test.jsonl'; old = read_rows(source)
        base = read_rows(OUT / 'base' / f'{name}-test.jsonl'); selected = read_rows(OUT / cfg['selected'] / f'{name}-test.jsonl')
        if {r['id']: r['labels'] for r in old} != {r['id']: r['labels'] for r in selected}: raise ValueError('Historical public IDs/labels differ')
        public[name] = {'base': accuracy(base, 'intent'), 'selected': accuracy(selected, 'intent'), 'jev': accuracy(old, 'intent'),
                        'n': len(old), 'jev_errors': sum(bool(r.get('error')) for r in old), 'jev_source_sha256': sha(source)}
        v = public[name]; lines.append(f'|{name} ({v["n"]})|{v["base"]:.2%}|{v["selected"]:.2%}|{v["jev"]:.2%}|')
    lines += ['', '公共Jev是相同固定测试问题上的历史结果，MASSIVE的2次API错误计为错误；未重新调用全部公共集。CrossWOZ本轮加入官方train，只是五领域分类，不代表零样本迁移。',
        '业务为共享生成器的21表达组、未人工复核；只对Qwen做业务课程适配。不能据合成高分宣称真实客服全面超越Jev。分组配对区间见JSON，API错误在配对区间中排除、在主表中计错。',
        '模型输出概率不等于可核验原因；比较没有执行真实工具，也没有验证截图提出的新八类业务动作。']
    (TARGET / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    atomic_json(TARGET / 'metrics.json', {'business': results, 'latency': latency, 'public': public,
        'paired_group_ci_selected_minus_jev': ci, 'matched_jev_latency_successful': sum(not r.get('error') for r in matched),
        'source_hashes': {str(p.relative_to(ROOT).as_posix()): sha(p) for p in [TARGET/'protocol.json',TARGET/'jev-business-test.jsonl',TARGET/'local-latency.jsonl',TARGET/'local-metrics.json']}})
    print('\n'.join(lines[:20]), flush=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['vendor', 'local', 'report']); args = p.parse_args()
    if args.action == 'vendor':
        with exclusive_lock('compare-v5-api.lock'): vendor()
    elif args.action == 'local':
        with exclusive_lock('joint-v5-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'): local()
    else: report()


if __name__ == '__main__': main()
