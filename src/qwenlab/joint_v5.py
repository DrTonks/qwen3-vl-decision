"""Resumable v5 experiment. Never imports vendor outputs or modifies v4 files."""
import argparse
from collections import Counter
from contextlib import contextmanager
import json
import math
import os
import random
import subprocess
import sys
import time

from qwenlab.common import ROOT, append_json, input_state, load_json, sha
from qwenlab.curriculum_v5 import DATA, action_label
from qwenlab.joint_v4 import add_adapter, batch_logits, components, metrics
from qwenlab.modeling import load_model, specification
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.summarize import percentile

OUT = ROOT / 'results/joint-v5'
CKPT = ROOT / '.local/checkpoints/joint-v5'
SOURCES = ['src/qwenlab/joint_v5.py', 'src/qwenlab/curriculum_v5.py',
           'src/qwenlab/joint_v4.py', 'src/qwenlab/modeling.py',
           'configs/joint-v5.json', 'configs/decision-v5.json']


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def exclusive_lock(name):
    """OS-owned lock is released after crashes; the file itself may remain."""
    import msvcrt
    path = ROOT / '.local' / name; path.parent.mkdir(exist_ok=True)
    with path.open('a+b') as handle:
        if path.stat().st_size == 0: handle.write(b'0'); handle.flush()
        handle.seek(0)
        try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc: raise RuntimeError(f'Another worker holds {name}') from exc
        try: yield
        finally:
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def encode(tokenizer, row, task, seed=None, *, spec=None):
    if row.get('images'): raise NotImplementedError('v5 is text only')
    # Long-running inference supplies the same snapshot used for its policy hash.
    # Existing experiment callers retain their original file-based specification.
    if spec is None:
        spec = load_json(ROOT / 'configs/decision-v5.json') if row['dataset'] == 'business' else specification(row['dataset'])
    question = spec['questions'][task]; keys = list(question['criteria'])
    if seed is not None: random.Random(seed).shuffle(keys)
    symbols = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    ids = [tokenizer.encode(s, add_special_tokens=False) for s in symbols[:len(keys)]]
    if len(keys) > len(symbols) or any(len(x) != 1 for x in ids): raise ValueError('Invalid candidate symbols')
    options = '\n'.join(f'{symbol}: {question["criteria"][key]} ({key})' for symbol, key in zip(symbols, keys))
    messages = [{'role': 'system', 'content': spec['policy'] + '\n你正在执行候选分类。只输出一个候选符号，不要解释，不要输出JSON。'},
                {'role': 'user', 'content': json.dumps(input_state(row), ensure_ascii=False) + '\n问题：' + question['instructions'] + '\n候选：\n' + options + '\n只输出候选符号：'}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    tokens = tokenizer(text, add_special_tokens=False)
    if len(tokens['input_ids']) > 2048: raise ValueError(f'No silent truncation: {row["id"]}')
    return {'tokens': tokens, 'keys': keys, 'ids': [x[0] for x in ids],
            'target': keys.index(row['labels'][task]), 'id': row['id'], 'task': task, 'dataset': row['dataset']}


def prediction(scores, example):
    probs = scores.softmax(-1).cpu().tolist()
    return {'choice': example['keys'][max(range(len(probs)), key=probs.__getitem__)],
            'probabilities': dict(zip(example['keys'], probs)),
            'candidate_logits': scores.cpu().tolist(), 'ordered_keys': example['keys']}


def predict_one(tok, model, row, mode='three'):
    import torch
    tasks = ['intent'] if row['dataset'] != 'business' else (['intent', 'action'] if mode == 'action' else ['intent', 'route', 'tool'])
    result = {k: row[k] for k in ('id', 'group', 'labels')}; result['predictions'] = {}
    with torch.inference_mode():
        for task in tasks:
            example = encode(tok, row, task)
            result['predictions'][task] = prediction(batch_logits(tok, model, [example])[0], example)
    p = result['predictions']
    if 'action' in p:
        choice = p['action']['choice']; route = choice if choice in ('clarify', 'llm', 'human') else 'tool'
        p['route'] = {'choice': route, 'derived': True}
        p['tool'] = {'choice': choice if route == 'tool' else 'none', 'derived': True}
    if 'route' in p:
        result['raw_tool'] = p['tool'].copy()
        if p['route']['choice'] != 'tool': p['tool'] = {'choice': 'none', 'derived': True}
        p['needs_human'] = {'choice': 'yes' if p['route']['choice'] == 'human' else 'no', 'derived': True}
    return result


def frozen_protocol():
    manifest = load_json(DATA / 'manifest.json')
    for name, record in manifest['files'].items():
        if sha(DATA / name) != record['sha256']: raise ValueError('Data changed: ' + name)
    for name, digest in manifest['source_hashes'].items():
        if sha(ROOT / name) != digest: raise ValueError('Data generator/spec changed: ' + name)
    return {'config': load_json(ROOT / 'configs/joint-v5.json'), 'manifest_sha256': sha(DATA / 'manifest.json'),
            'source_sha256': {p: sha(ROOT / p) for p in SOURCES},
            'reference_adapter': '.local/checkpoints/joint-v4/step-1582',
            'reference_adapter_sha256': sha(ROOT / '.local/checkpoints/joint-v4/step-1582/adapter_model.safetensors'),
            'label_status': 'synthetic_unreviewed; independent human acceptance pending',
            'evaluation_batch': 1, 'training_reads_jev': False}


def verify_protocol():
    current = frozen_protocol(); path = OUT / 'protocol.json'
    if path.exists() and load_json(path) != current:
        raise ValueError('Frozen v5 protocol changed; use a new experiment version')
    if not path.exists(): atomic_json(path, current)
    return current


def rng_state():
    import numpy as np
    import torch
    return {'python': random.getstate(), 'numpy': np.random.get_state(), 'torch': torch.get_rng_state(),
            'cuda': torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def restore_rng(state):
    import numpy as np
    import torch
    random.setstate(state['python']); np.random.set_state(state['numpy']); torch.set_rng_state(state['torch'].cpu())
    if state['cuda']: torch.cuda.set_rng_state_all([x.cpu() for x in state['cuda']])


def save_checkpoint(model, optim, step, summary, protocol_hash):
    import torch
    final = CKPT / f'step-{step}'
    if final.exists(): raise FileExistsError(final.name)
    # A failed staging directory is ignored; a fresh name needs no deletion.
    staging = CKPT / f'.step-{step}-{time.time_ns()}.pending'; staging.mkdir(parents=True)
    model.save_pretrained(staging, safe_serialization=True)
    ac = load_json(staging / 'adapter_config.json'); ac['base_model_name_or_path'] = 'Qwen/Qwen3-VL-2B-Instruct'
    atomic_json(staging / 'adapter_config.json', ac)
    # Scheduler is closed-form in global step, config and total_steps. Those
    # values are all frozen; no opaque scheduler state is omitted.
    torch.save({'optimizer': optim.state_dict(), 'rng': rng_state(), 'step': step,
                'summary': summary, 'protocol_sha256': protocol_hash}, staging / 'training-state.pt')
    atomic_json(staging / 'checkpoint.json', {'step': step, 'protocol_sha256': protocol_hash,
        'files': {name: sha(staging / name) for name in ('adapter_config.json', 'adapter_model.safetensors', 'training-state.pt')}})
    staging.rename(final)
    atomic_json(OUT / 'latest-checkpoint.json', {'step': step, 'path': final.relative_to(ROOT).as_posix(), 'protocol_sha256': protocol_hash})


def valid_checkpoints(protocol_hash):
    valid = []
    for path in CKPT.glob('step-*'):
        meta = load_json(path / 'checkpoint.json')
        if meta['protocol_sha256'] != protocol_hash: raise ValueError('Checkpoint protocol mismatch')
        if any(sha(path / name) != digest for name, digest in meta['files'].items()): raise ValueError('Corrupt checkpoint: ' + path.name)
        valid.append((meta['step'], path))
    return sorted(valid)


def epoch_blocks(pools, cfg, epoch):
    rng = random.Random(cfg['seed'] + epoch * 100003)
    blocks = []
    for name, xs in sorted(pools.items()):
        order = list(range(len(xs))); rng.shuffle(order)
        blocks.extend((name, order[i:i + cfg['micro_batch']]) for i in range(0, len(order), cfg['micro_batch']))
    rng.shuffle(blocks)
    return blocks


def lr_scale(step, total, warm_fraction):
    warm = max(1, int(total * warm_fraction))
    return min(step / warm, max((total - step + 1) / max(total - warm, 1), 0))


def train(resume=False):
    import numpy as np
    import torch
    cfg = verify_protocol()['config']; digest = sha(OUT / 'protocol.json')
    checkpoints = valid_checkpoints(digest)
    if checkpoints and not resume: raise FileExistsError('Use --resume to continue the same frozen experiment')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); np.random.seed(cfg['seed'])
    tok, base = load_model('nf4'); tok.padding_side = 'left'; model = add_adapter(base, cfg)
    params = [p for p in model.parameters() if p.requires_grad]
    optim = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
    pools = {}; permutation = random.Random(cfg['seed'])
    for name in ('massive', 'crosswoz', 'business'):
        rows = read_rows(DATA / f'{name}-train.jsonl')
        for task in (cfg['business_tasks'] if name == 'business' else ['intent']):
            pools[name + '.' + task] = [encode(tok, r, task, permutation.randrange(2**31)) for r in rows]
    blocks_per_epoch = len(epoch_blocks(pools, cfg, 0)); steps_per_epoch = math.ceil(blocks_per_epoch / cfg['gradient_accumulation'])
    total = steps_per_epoch * cfg['epochs']; evaluation_steps = sorted({math.ceil(total * f) for f in cfg['eval_fractions']})
    atomic_json(OUT / 'schedule.json', {'total_steps': total, 'steps_per_epoch': steps_per_epoch, 'evaluation_steps': evaluation_steps,
                                      'examples_per_epoch': {k: len(v) for k, v in pools.items()}})
    summary = {'status': 'running', 'config': cfg, 'optimizer_steps': 0, 'total_steps': total,
               'steps_per_epoch': steps_per_epoch, 'examples_per_epoch': {k: len(v) for k, v in pools.items()},
               'trainable_parameters': sum(p.numel() for p in params), 'sampled': {}, 'elapsed_s': 0,
               'max_input_tokens': max(len(x['tokens']['input_ids']) for xs in pools.values() for x in xs),
               'independent_human_acceptance': 'pending', 'uses_jev_outputs': False}
    if checkpoints:
        from peft.utils.save_and_load import load_peft_weights, set_peft_model_state_dict
        step, path = checkpoints[-1]
        set_peft_model_state_dict(model, load_peft_weights(str(path), device='cpu'))
        # Trust only locally generated, hash-verified training state. Never use
        # weights_only=False for an arbitrary downloaded checkpoint.
        saved = torch.load(path / 'training-state.pt', map_location='cpu', weights_only=False)
        if saved['protocol_sha256'] != digest or saved['step'] != step: raise ValueError('Training state mismatch')
        optim.load_state_dict(saved['optimizer']); summary = saved['summary']; restore_rng(saved['rng'])
        summary['status'] = 'running'; summary['resumed_from_step'] = step
        if (OUT / 'train.jsonl').exists():
            logs = read_resumable_rows(OUT / 'train.jsonl')
            discarded = [r for r in logs if r['step'] > step]
            if discarded: write_rows(ROOT / '.local' / f'v5-uncommitted-steps-{time.time_ns()}.jsonl', discarded)
            write_rows(OUT / 'train.jsonl', [r for r in logs if r['step'] <= step])
    start_step = summary['optimizer_steps']; sampled = Counter(summary['sampled']); elapsed_before = summary['elapsed_s']
    start = time.perf_counter(); model.train(); optim.zero_grad(set_to_none=True); torch.cuda.reset_peak_memory_stats()
    atomic_json(OUT / 'training-summary.json', summary)
    try:
        for epoch in range(start_step // steps_per_epoch, cfg['epochs']):
            blocks = epoch_blocks(pools, cfg, epoch)
            for local in range(steps_per_epoch):
                step = epoch * steps_per_epoch + local + 1
                if step <= start_step: continue
                chunk = blocks[local * cfg['gradient_accumulation']:(local + 1) * cfg['gradient_accumulation']]
                for group in optim.param_groups: group['lr'] = cfg['learning_rate'] * lr_scale(step, total, cfg['warmup_fraction'])
                losses = []
                for name, indices in chunk:
                    xs = [pools[name][i] for i in indices]; values = batch_logits(tok, model, xs)
                    loss = sum(torch.nn.functional.cross_entropy(v[None, :], torch.tensor([x['target']], device='cuda')) for x, v in zip(xs, values)) / len(xs)
                    if not torch.isfinite(loss): raise FloatingPointError('Nonfinite loss')
                    (loss * cfg['weights'][name] / len(chunk)).backward()
                    losses.append(float(loss.detach())); sampled[name] += len(xs)
                norm = torch.nn.utils.clip_grad_norm_(params, 1.)
                if not torch.isfinite(norm): raise FloatingPointError('Nonfinite gradients')
                optim.step(); optim.zero_grad(set_to_none=True)
                elapsed = elapsed_before + time.perf_counter() - start
                log = {'step': step, 'epoch_fraction': step / steps_per_epoch, 'unweighted_loss': sum(losses) / len(losses),
                       'lr': optim.param_groups[0]['lr'], 'gradient_norm': norm.item(), 'elapsed_s': elapsed}
                append_json(OUT / 'train.jsonl', log)
                summary.update(optimizer_steps=step, sampled=dict(sampled), elapsed_s=elapsed,
                    peak_allocated_gib=torch.cuda.max_memory_allocated() / 2**30, peak_reserved_gib=torch.cuda.max_memory_reserved() / 2**30)
                if step % 10 == 0:
                    atomic_json(OUT / 'training-summary.json', summary); print(json.dumps(log), flush=True)
                if step % cfg['checkpoint_every'] == 0 or step in evaluation_steps:
                    save_checkpoint(model, optim, step, summary.copy(), digest)
        expected = {k: len(v) * cfg['epochs'] for k, v in pools.items()}
        if dict(sampled) != expected: raise AssertionError('Training coverage mismatch')
        summary['status'] = 'complete'
    except BaseException as exc:
        summary.update(status='failed', error=type(exc).__name__); raise
    finally: atomic_json(OUT / 'training-summary.json', summary)


def read_resumable_rows(path):
    if not path.exists(): return []
    raw = path.read_text(encoding='utf-8'); lines = raw.splitlines(); rows = []
    for i, line in enumerate(lines):
        try: rows.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1: raise
            write_rows(path, rows)  # Only a truncated final append can be recovered.
    if raw and not raw.endswith('\n'): write_rows(path, rows)
    return rows


def adapter_for(variant):
    if variant == 'base': return None
    if variant == 'v4-reference': return '.local/checkpoints/joint-v4/step-1582'
    return (CKPT / variant).relative_to(ROOT).as_posix()


def evaluate(variant, splits):
    verify_protocol()
    tok, model = load_model('nf4', adapter_for(variant)); tok.padding_side = 'left'; model.eval()
    folder = OUT / variant; folder.mkdir(exist_ok=True)
    for split in splits:
        for name in ('business', 'massive', 'crosswoz'):
            rows = read_rows(DATA / f'{name}-{split}.jsonl'); path = folder / f'{name}-{split}.jsonl'
            done = read_resumable_rows(path)
            if [r['id'] for r in done] != [r['id'] for r in rows[:len(done)]]: raise ValueError('Evaluation order mismatch')
            for i, row in enumerate(rows[len(done):], len(done)):
                result = predict_one(tok, model, row); append_json(path, result); done.append(result)
                if (i + 1) % 100 == 0: print(variant, name, split, i + 1, '/', len(rows), flush=True)
            m = metrics(done); atomic_json(folder / f'{name}-{split}-metrics.json', m)
            print(variant, name, split, json.dumps(m, ensure_ascii=False), flush=True)


def select(variants):
    values = {v: {n: load_json(OUT / v / f'{n}-dev-metrics.json') for n in ('business', 'massive', 'crosswoz')} for v in variants}
    ref = values['v4-reference']; reference = components(ref['business'], ref['massive']); choices = {}
    for variant, result in values.items():
        score = components(result['business'], result['massive'])
        passes = (all(x >= b - .03 for x, b in zip(score, reference))
                  and result['business']['human_missed'] <= ref['business']['human_missed']
                  and result['crosswoz']['tasks']['intent']['accuracy'] >= ref['crosswoz']['tasks']['intent']['accuracy'] - .03)
        choices[variant] = {'components': score, 'guardrails_pass': passes, 'objective': math.prod(score)**.25}
    winner = max([v for v in variants if choices[v]['guardrails_pass']], key=lambda v: choices[v]['objective'])
    atomic_json(OUT / 'selection.json', {'selected': winner, 'reference': 'v4-reference', 'selection': choices, 'development': values})
    return winner


def preflight():
    """Real worst-length backward pass and optimizer step, on train only."""
    import torch
    cfg = verify_protocol()['config']; tok, base = load_model('nf4'); tok.padding_side = 'left'
    xs = []
    for name in ('business', 'massive', 'crosswoz'):
        rows = read_rows(DATA / f'{name}-train.jsonl')
        for row in rows: xs.append(encode(tok, row, 'intent'))
    longest = sorted(xs, key=lambda x: len(x['tokens']['input_ids']), reverse=True)[:cfg['micro_batch']]
    model = add_adapter(base, cfg); model.train(); params = [p for p in model.parameters() if p.requires_grad]
    optim = torch.optim.AdamW(params, lr=cfg['learning_rate']); torch.cuda.reset_peak_memory_stats(); start = time.perf_counter()
    for _ in range(2):
        values = batch_logits(tok, model, longest)
        loss = sum(torch.nn.functional.cross_entropy(v[None, :], torch.tensor([x['target']], device='cuda')) for x, v in zip(longest, values)) / len(longest)
        if not torch.isfinite(loss): raise FloatingPointError('Preflight loss')
        loss.backward(); norm = torch.nn.utils.clip_grad_norm_(params, 1.)
        if not torch.isfinite(norm): raise FloatingPointError('Preflight gradient')
        optim.step(); optim.zero_grad(set_to_none=True)
    atomic_json(OUT / 'preflight.json', {'status': 'passed', 'train_rows_tokenized': len(xs),
        'longest_input_tokens': len(longest[0]['tokens']['input_ids']), 'micro_batch': cfg['micro_batch'],
        'optimizer_steps': 2, 'elapsed_s': time.perf_counter() - start,
        'peak_allocated_gib': torch.cuda.max_memory_allocated() / 2**30,
        'peak_reserved_gib': torch.cuda.max_memory_reserved() / 2**30,
        'note': 'Disposable adapter; no held-out labels or weights used in preflight'} )
    print('GPU preflight passed', flush=True)


def action_probe(variant):
    """Exploratory action-prompt ablation, no action training or auto-promotion."""
    import torch
    tok, model = load_model('nf4', adapter_for(variant)); tok.padding_side = 'left'; model.eval()
    rows = read_rows(DATA / 'business-dev.jsonl')
    target = OUT / 'action-probe'; target.mkdir(exist_ok=True)
    path = target / 'predictions.jsonl'; done = read_resumable_rows(path)
    if [r['id'] for r in done] != [r['id'] for r in rows[:len(done)]]: raise ValueError('Probe order mismatch')
    for row in rows[len(done):]:
        result = predict_one(tok, model, row, 'action'); append_json(path, result); done.append(result)
    sample = random.Random(20260927).sample(rows, 32)
    for mode in ('three', 'action'):
        for row in sample[:2]: predict_one(tok, model, row, mode)
    timings = []
    for repeat in range(3):
        for i, row in enumerate(sample):
            for mode in (('three', 'action') if (repeat + i) % 2 == 0 else ('action', 'three')):
                torch.cuda.synchronize(); start = time.perf_counter(); predict_one(tok, model, row, mode); torch.cuda.synchronize()
                timings.append({'id': row['id'], 'repeat': repeat, 'mode': mode, 'elapsed_s': time.perf_counter() - start})
    write_rows(target / 'latency.jsonl', timings)
    atomic_json(target / 'metrics.json', {'variant': variant, 'action': metrics(done),
        'three': load_json(OUT / variant / 'business-dev-metrics.json'),
        'latency': {m: {f'p{int(q*100)}_s': percentile([t['elapsed_s'] for t in timings if t['mode'] == m], q) for q in (.5, .95)} for m in ('three', 'action')},
        'scope': '32 dev requests x3, alternating, batch1, tokenization+CPU transfer, excludes load/warmup',
        'limits': 'Untrained action prompt, not an action-finetuning result; three-task model unchanged; no automatic deployment'})


def report():
    selected = load_json(OUT / 'selection.json')['selected']
    lines = ['# 第五轮自动结果', '', f'开发集选择：`{selected}`。合成数据未人工复核，不能代替独立验收。', '',
             '|模型|业务意图|业务路由|工具必要子集联合正确|人工漏转|MASSIVE 意图|CrossWOZ 领域|', '|---|---:|---:|---:|---:|---:|---:|']
    for v in dict.fromkeys(['base', 'v4-reference', selected]):
        b = load_json(OUT / v / 'business-test-metrics.json')
        p = load_json(OUT / v / 'massive-test-metrics.json'); c = load_json(OUT / v / 'crosswoz-test-metrics.json')
        lines.append(f'|{v}|{b["tasks"]["intent"]["accuracy"]:.2%}|{b["tasks"]["route"]["accuracy"]:.2%}|{b["joint_tool_correct"]}/{b["tool_required"]}|{b["human_missed"]}/{b["human_required"]}|{p["tasks"]["intent"]["accuracy"]:.2%}|{c["tasks"]["intent"]["accuracy"]:.2%}|')
    lines += ['', '三者都使用第五轮政策提示；第四轮原始结果保存在原报告，不与本表偷换口径。',
              '没有新增 Jev 调用；这轮同时改变数据、补充政策、训练时长和学习率，不能将差异单独归因于某一项。',
              '动作合并探索的逐条结果与速度见 action-probe。该动作问题尚未专项训练，不能称为最终两次决策模型。']
    (OUT / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run(resume=False):
    verify_protocol()
    def child(*args):
        subprocess.run([sys.executable, '-m', 'qwenlab.joint_v5', *args], cwd=ROOT, check=True)
    try:
        atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'preflight'})
        if not (OUT / 'preflight.json').exists(): child('preflight')
        for variant in ('base', 'v4-reference'):
            atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'reference-dev', 'variant': variant})
            child('evaluate', '--variant', variant, '--splits', 'dev')
        atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'training'})
        child('train', *(['--resume'] if resume else []))
        steps = load_json(OUT / 'schedule.json')['evaluation_steps']
        variants = ['base', 'v4-reference'] + [f'step-{step}' for step in steps]
        for variant in variants[2:]:
            atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'checkpoint-dev', 'variant': variant})
            child('evaluate', '--variant', variant, '--splits', 'dev')
        winner = select(variants)
        for variant in dict.fromkeys(['base', 'v4-reference', winner]):
            atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'frozen-evaluation', 'variant': variant})
            child('evaluate', '--variant', variant, '--splits', 'calibration', 'test')
        atomic_json(OUT / 'status.json', {'status': 'running', 'stage': 'action-probe', 'variant': winner})
        child('action-probe', '--variant', winner)
        report(); atomic_json(OUT / 'status.json', {'status': 'complete', 'selected': winner, 'human_acceptance': 'pending'})
        subprocess.run([sys.executable, '-m', 'qwenlab.publish', '--export'], cwd=ROOT, check=True)
    except BaseException as exc:
        atomic_json(OUT / 'status.json', {'status': 'failed', 'error': type(exc).__name__, 'resume': 'python -m qwenlab.joint_v5 run --resume'})
        raise


def main():
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['run', 'preflight', 'train', 'evaluate', 'action-probe'])
    p.add_argument('--resume', action='store_true'); p.add_argument('--variant', default='base'); p.add_argument('--splits', nargs='+', default=['dev']); args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with exclusive_lock('joint-v5-pipeline.lock' if args.action == 'run' else 'joint-v5-gpu.lock'):
        if args.action == 'run': run(args.resume)
        elif args.action == 'train': train(args.resume)
        elif args.action == 'preflight': preflight()
        elif args.action == 'action-probe': action_probe(args.variant)
        else: evaluate(args.variant, args.splits)


if __name__ == '__main__': main()
