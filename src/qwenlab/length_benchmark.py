"""Frozen paired input-length experiment; evaluation only, bounded API calls."""
import argparse
import copy
from datetime import datetime, timezone
import json
import math
import random
import time
import urllib.request

from qwenlab.common import ROOT, append_json, input_state, load_json, sha
from qwenlab.joint_v5 import DATA, OUT, encode, adapter_for, atomic_json, exclusive_lock
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.summarize import percentile

TARGET = OUT / 'length-benchmark'
LEVELS = [0, 256, 640, 1024]
TASKS = ['intent', 'route', 'tool']


def add_background(row, paragraphs):
    result = copy.deepcopy(row)
    if paragraphs:
        history = {'role': 'assistant', 'content': '以下是此前已经结束的阅读记录。' + ''.join(paragraphs)}
        result['history'] = [history] + result.get('history', [])
    return result


def prepare():
    from transformers import AutoTokenizer
    if TARGET.exists():
        raise FileExistsError('Preserve frozen experiment')
    tok = AutoTokenizer.from_pretrained(ROOT / 'models/Qwen3-VL-2B-Instruct', local_files_only=True)
    rows = read_rows(DATA / 'business-test.jsonl')
    rng = random.Random(20260928)
    rng.shuffle(rows)
    chosen = []
    used_groups = set()
    for route in ('tool', 'clarify', 'llm', 'human'):
        count = 0
        for row in rows:
            if row['labels']['route'] == route and row['group'] not in used_groups:
                chosen.append(row); used_groups.add(row['group']); count += 1
                if count == 3: break
        if count != 3: raise ValueError('Insufficient distinct groups')
    sentences = ['阅读记录第{n}段介绍纸张与装订：书页排列整齐，封面采用浅色，章节标题置于页首。',
                 '阅读记录第{n}段介绍植物观察：叶片形状各有不同，图册按季节编排，并附有简短说明。',
                 '阅读记录第{n}段介绍展览布置：展品按主题排列，说明牌采用统一字号，过道保持宽敞。']
    cases = []
    for index, row in enumerate(chosen):
        base_length = len(encode(tok, row, 'intent')['tokens']['input_ids'])
        paragraphs = []
        for level in LEVELS:
            candidate = add_background(row, paragraphs)
            while len(encode(tok, candidate, 'intent')['tokens']['input_ids']) - base_length < level:
                paragraphs.append(sentences[(index + len(paragraphs)) % len(sentences)].format(n=len(paragraphs) + 1))
                candidate = add_background(row, paragraphs)
            lengths = {t: len(encode(tok, candidate, t)['tokens']['input_ids']) for t in TASKS}
            if max(lengths.values()) > 2048: raise ValueError('Input too long; never truncate')
            cases.append({'case_id': f'{row["id"]}/plus-{level}', 'base_id': row['id'], 'level': level,
                          'lengths': lengths, 'added_tokens_per_forward': lengths['intent'] - base_length, 'row': candidate})
    schedule = []
    for repeat in range(3):
        order = list(range(len(cases))); rng.shuffle(order)
        for j, i in enumerate(order):
            schedule.append({'case_id': cases[i]['case_id'], 'repeat': repeat,
                             'providers': ['qwen', 'jev'] if (repeat + j) % 2 == 0 else ['jev', 'qwen']})
    TARGET.mkdir()
    write_rows(TARGET / 'cases.jsonl', cases)
    atomic_json(TARGET / 'protocol.json', {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'selected': load_json(OUT / 'selection.json')['selected'],
        'levels_requested_added_tokens': LEVELS, 'base_questions': 12, 'repeats': 3, 'api_max_requests': 144,
        'api_retries': 0, 'api_expected_model': 'jev-1.13.0', 'schedule': schedule,
        'source_sha256': sha(ROOT / 'src/qwenlab/length_benchmark.py'), 'cases_sha256': sha(TARGET / 'cases.jsonl'),
        'spec_sha256': sha(ROOT / 'configs/decision-v5.json'), 'data_sha256': sha(DATA / 'business-test.jsonl'),
        'method': 'same question/state/policy/choices; prepend completed neutral reading history; randomized length order; counterbalanced provider order; batch1; Qwen three serial candidate forwards, Jev one HTTP request',
        'limits': ['12 synthetic unreviewed base questions; not a representative accuracy benchmark',
                   'added history is controlled distractor content, not mathematically pure length',
                   'local input token count and provider usage are different tokenizers/serializations',
                   'remote cache/load/hardware unknown; exact repeated payloads may be cached',
                   'Qwen load/warmup excluded; Jev network included; no throughput measurement'],
        'no_training_use': True})
    atomic_json(TARGET / 'status.json', {'status': 'prepared', 'completed': 0, 'total': 288})
    print('Prepared 48 cases, 144 requests per provider', flush=True)


def validate_answer(body, spec):
    if body.get('model') != 'jev-1.13.0': raise ValueError('Vendor version changed')
    predictions = {}
    for task in TASKS:
        value = body['answers'][task]
        probs = value['probabilities']
        if set(probs) != set(spec['questions'][task]['criteria']) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()) or abs(sum(probs.values()) - 1) > .03:
            raise ValueError('Invalid probabilities')
        if value['choice'] not in probs: raise ValueError('Invalid candidate')
        predictions[task] = value['choice']
    if predictions['route'] != 'tool': predictions['tool'] = 'none'
    return predictions


def run():
    import torch
    from qwenlab.modeling import load_model
    from qwenlab.candidate_inference import CandidateScorer
    cfg = load_json(TARGET / 'protocol.json')
    for path, key in [(ROOT / 'src/qwenlab/length_benchmark.py', 'source_sha256'), (TARGET / 'cases.jsonl', 'cases_sha256'), (ROOT / 'configs/decision-v5.json', 'spec_sha256')]:
        if sha(path) != cfg[key]: raise ValueError('Frozen experiment changed')
    output = TARGET / 'requests.jsonl'
    if output.exists(): raise FileExistsError('No automatic resume or repeated API calls')
    cases = {r['case_id']: r for r in read_rows(TARGET / 'cases.jsonl')}
    spec = load_json(ROOT / 'configs/decision-v5.json')
    state = {'status': 'loading', 'completed': 0, 'total': 288, 'api_requests': 0, 'api_errors': 0,
             'started_utc': datetime.now(timezone.utc).isoformat()}
    atomic_json(TARGET / 'status.json', state)
    try:
        key = (ROOT / '.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
        if not key or any(c.isspace() for c in key): raise ValueError('Invalid credential')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *unused): return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        def api(endpoint, payload=None):
            req = urllib.request.Request('https://api.typesafe.ai' + endpoint,
                data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
                headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            with opener.open(req, timeout=30) as response: return json.load(response)
        names = [x['name'] for x in api('/v1/models')['models']]
        model_name = 'jev-1.13.0' if 'jev-1.13.0' in names else 'jev-latest'
        if model_name not in names: raise ValueError('Expected model unavailable')
        tok, model = load_model('nf4', adapter_for(cfg['selected']))
        tok.padding_side = 'left'; model.eval(); scorer = CandidateScorer(model)
        def local(row):
            pred = {}
            for task in TASKS:
                x = encode(tok, row, task)
                inputs = tok.pad([x['tokens']], padding=True, return_tensors='pt').to('cuda')
                scores = scorer.scores(inputs, x['ids'])[0]
                values = scores.softmax(-1).cpu().tolist()
                pred[task] = x['keys'][max(range(len(values)), key=values.__getitem__)]
            if pred['route'] != 'tool': pred['tool'] = 'none'
            return pred
        consecutive_errors = 0
        with torch.inference_mode():
            # Warm each length/layout outside the timer, including candidate/full validation.
            for level in LEVELS:
                local(next(c['row'] for c in cases.values() if c['level'] == level))
            if scorer.projection != 'candidate': raise RuntimeError('Candidate verification failed')
            state['status'] = 'running'
            for item in cfg['schedule']:
                case = cases[item['case_id']]
                for provider in item['providers']:
                    record = {k: case[k] for k in ('case_id', 'base_id', 'level', 'lengths', 'added_tokens_per_forward')}
                    record.update(provider=provider, repeat=item['repeat'], labels=case['row']['labels'])
                    torch.cuda.synchronize()
                    started = time.perf_counter()
                    if provider == 'qwen':
                        record['predictions'] = local(case['row'])
                        torch.cuda.synchronize()
                        record['elapsed_s'] = time.perf_counter() - started
                    else:
                        if state['api_requests'] >= cfg['api_max_requests']: raise RuntimeError('API limit')
                        state['api_requests'] += 1
                        try:
                            body = api('/v1/systemone', {'model': model_name, 'state': {'policy': spec['policy'], 'input': input_state(case['row'])},
                                       'questions': {t: {'type': 'choice', **spec['questions'][t]} for t in TASKS}})
                            record['elapsed_s'] = time.perf_counter() - started
                            record.update(predictions=validate_answer(body, spec), usage=body.get('usage'), model=body.get('model'))
                            consecutive_errors = 0
                        except Exception as exc:
                            record.update(elapsed_s=time.perf_counter() - started, error=type(exc).__name__, http_status=getattr(exc, 'code', None), predictions={})
                            state['api_errors'] += 1; consecutive_errors += 1
                    append_json(output, record)
                    state['completed'] += 1
                    state['elapsed_s'] = time.time() - datetime.fromisoformat(state['started_utc']).timestamp()
                    state['last'] = {'provider': provider, 'level': case['level'], 'repeat': item['repeat']}
                    atomic_json(TARGET / 'status.json', state)
                    if record.get('http_status') in (401, 402, 403, 429) or record.get('error') == 'ValueError' or consecutive_errors >= 3 or state['api_errors'] >= 6:
                        raise RuntimeError('API stop condition; no retries')
                if state['completed'] % 24 == 0: print('Completed', state['completed'], '/ 288', flush=True)
        state.update(status='complete', projection=scorer.projection, fallback=scorer.fallback_reason)
        atomic_json(TARGET / 'status.json', state)
    except Exception as exc:
        state.update(status='failed', error=type(exc).__name__, http_status=getattr(exc, 'code', None))
        atomic_json(TARGET / 'status.json', state)
        print('Stopped:', type(exc).__name__, getattr(exc, 'code', None), flush=True)
        raise SystemExit(1)


def stats(rows):
    good = [r for r in rows if not r.get('error')]
    return {'n': len(rows), 'successful': len(good), 'errors': len(rows) - len(good),
            'p50_s': percentile([r['elapsed_s'] for r in good], .5) if good else None,
            'p95_s': percentile([r['elapsed_s'] for r in good], .95) if good else None,
            'accuracy_all_requests': {t: sum(not r.get('error') and r['predictions'].get(t) == r['labels'][t] for r in rows) / len(rows) for t in TASKS},
            'human_missed_or_failed': sum(r['labels']['route'] == 'human' and r['predictions'].get('route') != 'human' for r in rows)}


def report():
    if load_json(TARGET / 'status.json')['status'] != 'complete': raise RuntimeError('Experiment incomplete')
    rows = read_rows(TARGET / 'requests.jsonl')
    if len(rows) != 288 or len({(r['case_id'], r['repeat'], r['provider']) for r in rows}) != 288: raise ValueError('Coverage mismatch')
    tables = {p: {str(level): stats([r for r in rows if r['provider'] == p and r['level'] == level]) for level in LEVELS} for p in ('qwen', 'jev')}
    ids = sorted({r['base_id'] for r in rows})
    changes = {}
    for provider in ('qwen', 'jev'):
        changes[provider] = {}
        for bid in ids:
            subset = [r for r in rows if r['provider'] == provider and r['base_id'] == bid and not r.get('error')]
            lo = [r['elapsed_s'] for r in subset if r['level'] == 0]
            hi = [r['elapsed_s'] for r in subset if r['level'] == 1024]
            if lo and hi: changes[provider][bid] = percentile(hi, .5) - percentile(lo, .5)
    common = sorted(set(changes['qwen']) & set(changes['jev']))
    deltas = [changes['qwen'][i] - changes['jev'][i] for i in common]
    rng = random.Random(20260928)
    boot = [sum(rng.choices(deltas, k=len(deltas))) / len(deltas) for _ in range(4000)] if deltas else []
    ci = {'groups': len(common), 'definition': 'per base question median(long)-median(short), then Qwen growth minus Jev growth; successful requests only',
          'mean_growth_s': {p: sum(changes[p][i] for i in common) / len(common) for p in changes},
          'mean_difference_s': sum(deltas) / len(deltas), 'bootstrap_95_s': [percentile(boot, .025), percentile(boot, .975)]}
    usage = {}
    for level in LEVELS:
        subset = [r for r in rows if r['level'] == level]
        q = [r for r in subset if r['provider'] == 'qwen']
        j = [r['usage']['input_tokens'] for r in subset if r['provider'] == 'jev' and r.get('usage', {}).get('input_tokens') is not None]
        usage[str(level)] = {'qwen_mean_tokens_per_forward': sum(sum(r['lengths'].values()) / 3 for r in q) / len(q),
                             'jev_mean_usage_input_tokens': sum(j) / len(j) if j else None}
    metrics = {'tables': tables, 'token_usage': usage, 'paired_growth': ci, 'requests_sha256': sha(TARGET / 'requests.jsonl')}
    atomic_json(TARGET / 'metrics.json', metrics)
    lines = ['# 输入长度对照实测', '', '12个固定业务问题，每档重复3次。准确率分母36是重复请求，只有12个独立问题。', '',
             '|新增上下文档位（Qwen token约数）|Qwen P50/P95 ms|Jev P50/P95 ms|Qwen 路由|Jev 路由|Jev 失败|', '|---|---:|---:|---:|---:|---:|']
    for level in LEVELS:
        q, j = tables['qwen'][str(level)], tables['jev'][str(level)]
        lines.append(f'|+{level}|{q["p50_s"]*1000:.1f}/{q["p95_s"]*1000:.1f}|{j["p50_s"]*1000:.1f}/{j["p95_s"]*1000:.1f}|{q["accuracy_all_requests"]["route"]:.2%}|{j["accuracy_all_requests"]["route"]:.2%}|{j["errors"]}|')
    lines += ['', '配对增长（最长−最短，先取每题重复中位数再平均）：', json.dumps(ci, ensure_ascii=False, indent=2), '',
              '本地三次串行前向，Jev一次HTTP联合返回；API含网络，加载/预热不计时。长度顺序随机、两方案顺序交替，无自动重试。成功请求用于延迟，失败计入准确率错误。',
              '增长差区间按12个问题重采样，不能覆盖远端负载/缓存等系统误差。填充历史只是单类干扰文本，不代表所有长对话。Jev实际输入token用量另存JSON，不等同Qwen tokenizer长度。',
              '本实验只评估，不训练、不重新选择模型，不足以验收真实客服或新八类动作。']
    (TARGET / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'run', 'report'])
    action = parser.parse_args().action
    if action == 'prepare': prepare()
    elif action == 'report': report()
    else:
        with exclusive_lock('joint-v5-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'), exclusive_lock('compare-v5-api.lock'):
            run()


if __name__ == '__main__': main()
