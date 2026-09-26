"""Bounded route-only pilot. Frozen v2 modules remain untouched.

Run `python -m qwenlab.route_v3 run` once in a prepared project.
Each GPU stage runs in a fresh process; selection reads development data only.
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from collections import Counter
from qwenlab.common import ROOT, append_json, input_state, load_json, sha
from qwenlab.modeling import dataset, load_model, score, specification
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.train import business_split
from qwenlab.summarize import metric, paired_ci, percentile

OUT = ROOT / 'results/route-v3'
CHECKPOINTS = ROOT / '.local/checkpoints/route-v3'


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def prompt(tokenizer, row, shuffle_seed=None):
    """Restore the exact original route prompt, without exposing gold labels."""
    if row.get('images'):
        raise NotImplementedError('Text-only route experiment')
    spec = specification('business'); q = spec['questions']['route']
    keys = list(q['criteria'])
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(keys)
    symbols = 'ABCD'
    ids = [tokenizer.encode(c, add_special_tokens=False) for c in symbols]
    if len(keys) != 4 or any(len(t) != 1 for t in ids):
        raise ValueError('Expected four single-token route symbols')
    options = '\n'.join(f'{c}: {q["criteria"][k]} ({k})' for c, k in zip(symbols, keys))
    messages = [
        {'role': 'system', 'content': spec['policy'] + '\n你正在执行候选分类。只输出一个候选符号，不要解释，不要输出JSON。'},
        {'role': 'user', 'content': json.dumps(input_state(row), ensure_ascii=False)
         + '\n问题：' + q['instructions'] + '\n候选：\n' + options + '\n只输出候选符号：'}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors='pt')
    if inputs.input_ids.shape[1] > 2048:
        raise ValueError('Input exceeds 2048; no silent truncation')
    return inputs, keys, [t[0] for t in ids]


def route_metrics(rows):
    result = metric(rows, 'route')
    human = [r for r in rows if r['labels']['route'] == 'human']
    tools = [r for r in rows if r['labels']['route'] == 'tool']
    result.update(
        human_required=len(human),
        human_missed=sum(r['predictions']['route']['choice'] != 'human' for r in human),
        human_false_positive=sum(r['labels']['route'] != 'human' and r['predictions']['route']['choice'] == 'human' for r in rows),
        tool_required=len(tools),
        tool_route_correct=sum(r['predictions']['route']['choice'] == 'tool' for r in tools),
        latency_p50_s=percentile([r.get('elapsed_s', 0) for r in rows], .5),
        latency_p95_s=percentile([r.get('elapsed_s', 0) for r in rows], .95))
    return result


def selection_key(result):
    return (result['macro_f1_gold_supported_classes'], -result['human_missed'], -result['nll'])


def train():
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    if CHECKPOINTS.exists():
        raise FileExistsError('Route training already exists; preserve the evidence')
    CHECKPOINTS.mkdir(parents=True)
    cfg = load_json(ROOT / 'configs/route-v3.json')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); rng = random.Random(cfg['seed'])
    tokenizer, base = load_model('nf4')
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant': False})
    targets = [n for n, _ in base.named_modules() if '.language_model.' in n and n.endswith(('.q_proj', '.v_proj'))]
    if not targets:
        raise ValueError('No language attention targets')
    model = get_peft_model(base, LoraConfig(r=cfg['lora_r'], lora_alpha=cfg['lora_alpha'],
        lora_dropout=cfg['lora_dropout'], target_modules=targets, bias='none', task_type='CAUSAL_LM'))
    named = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    if any('visual' in n or 'merger' in n or 'lora_' not in n for n, _ in named):
        raise ValueError('Unexpected trainable parameters')
    params = [p for _, p in named]
    train_rows, dev_rows = business_split()
    summary = {'config': cfg, 'status': 'running', 'base_model': 'Qwen/Qwen3-VL-2B-Instruct',
        'training_ids': [r['id'] for r in train_rows], 'development_ids': [r['id'] for r in dev_rows],
        'training_groups': sorted({r['group'] for r in train_rows}),
        'trainable_parameters': sum(p.numel() for p in params),
        'trainable_names': [n for n, _ in named], 'uses_jev_outputs': False,
        'vision': 'frozen; text only', 'optimizer_steps': 0}
    optim = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
    sampled = Counter(); model.train(); optim.zero_grad(set_to_none=True)
    start = time.perf_counter(); torch.cuda.reset_peak_memory_stats()
    try:
        for step in range(1, cfg['steps'] + 1):
            scale = min(step / max(cfg['warmup_steps'], 1), max((cfg['steps'] - step + 1) / max(cfg['steps'] - cfg['warmup_steps'], 1), 0))
            for group in optim.param_groups:
                group['lr'] = cfg['learning_rate'] * scale
            losses = []
            for _ in range(cfg['gradient_accumulation']):
                row = rng.choice(train_rows); sampled[row['id']] += 1
                inputs, keys, ids = prompt(tokenizer, row, rng.randrange(2**31))
                logits = score(model, inputs.to('cuda'), ids)
                target = torch.tensor([keys.index(row['labels']['route'])], device='cuda')
                loss = torch.nn.functional.cross_entropy(logits[None, :], target)
                if not torch.isfinite(loss):
                    raise FloatingPointError('Non-finite route loss')
                (loss / cfg['gradient_accumulation']).backward(); losses.append(loss.item())
            grad = torch.nn.utils.clip_grad_norm_(params, 1.)
            if not torch.isfinite(grad):
                raise FloatingPointError('Non-finite gradient')
            optim.step(); optim.zero_grad(set_to_none=True)
            summary['optimizer_steps'] = step
            log = {'step': step, 'route_loss': sum(losses) / len(losses),
                'lr': optim.param_groups[0]['lr'], 'gradient_norm': grad.item(), 'elapsed_s': time.perf_counter() - start}
            append_json(OUT / 'train.jsonl', log)
            if step % 10 == 0:
                print(json.dumps(log), flush=True)
            if step % cfg['validation_interval'] == 0 or step == cfg['steps']:
                path = CHECKPOINTS / f'step-{step}'
                model.save_pretrained(path, safe_serialization=True)
                ac = load_json(path / 'adapter_config.json')
                ac['base_model_name_or_path'] = 'Qwen/Qwen3-VL-2B-Instruct'
                dump(path / 'adapter_config.json', ac)
                dump(OUT / f'adapter-step-{step}.json', {'config': ac,
                    'weights_sha256': sha(path / 'adapter_model.safetensors')})
        summary.update(status='complete', sampled_ids=dict(sampled), elapsed_s=time.perf_counter() - start,
            peak_allocated_gib=torch.cuda.max_memory_allocated() / 2**30,
            peak_reserved_gib=torch.cuda.max_memory_reserved() / 2**30)
    finally:
        dump(OUT / 'training-summary.json', summary)


def evaluate(variant, splits):
    import torch
    adapter = None if variant == 'base' else (CHECKPOINTS / variant).relative_to(ROOT).as_posix()
    tokenizer, model = load_model('nf4', adapter=adapter); model.eval()
    # Warm up the actual route input; loading and warmup are outside latency.
    warm, _, ids = prompt(tokenizer, business_split()[1][0])
    with torch.inference_mode():
        score(model, warm.to('cuda'), ids)
    for split in splits:
        destination = OUT / f'{variant}-{split}.jsonl'
        if destination.exists():
            raise FileExistsError(destination.name)
        rows = business_split()[1] if split == 'dev' else dataset('business', split)
        for row in rows:
            torch.cuda.synchronize(); start = time.perf_counter()
            inputs, keys, ids = prompt(tokenizer, row)
            with torch.inference_mode():
                logits = score(model, inputs.to('cuda'), ids)
                probabilities = logits.softmax(-1).cpu().tolist()
            torch.cuda.synchronize(); elapsed = time.perf_counter() - start
            prediction = {'choice': keys[max(range(4), key=probabilities.__getitem__)],
                'probabilities': dict(zip(keys, probabilities)), 'candidate_logits': logits.cpu().tolist(),
                'ordered_keys': keys, 'input_tokens': inputs.input_ids.shape[1]}
            append_json(destination, {'id': row['id'], 'group': row['group'],
                'labels': {'route': row['labels']['route']}, 'predictions': {'route': prediction}, 'elapsed_s': elapsed})
        print(variant, split, json.dumps(route_metrics(read_rows(destination))), flush=True)


def report(selected):
    from qwenlab.calibrate_v2 import apply, fit
    results = {}; sets = {}
    for variant in dict.fromkeys(['base', selected]):
        rows = read_rows(OUT / f'{variant}-test.jsonl'); sets[variant] = rows
        fitted = fit(read_rows(OUT / f'{variant}-calibration.jsonl'), 'route')
        calibrated = apply(rows, {'route': fitted})
        write_rows(OUT / f'{variant}-test-calibrated.jsonl', calibrated)
        results[variant] = {'raw': route_metrics(rows), 'temperature': fitted, 'calibrated': route_metrics(calibrated)}
    comparison = paired_ci(sets[selected], sets['base'], 'route')
    dump(OUT / 'metrics.json', {'selected': selected, 'runs': results, 'selected_minus_base': comparison,
        'latency_scope': 'one route forward only; not whole customer service workflow',
        'test_role': 'seen 72-item, 18-group synthetic regression; not fresh acceptance'})
    mistakes = [{'id': r['id'], 'expected': r['labels']['route'], 'predicted': r['predictions']['route']['choice']}
        for r in sets[selected] if r['labels']['route'] != r['predictions']['route']['choice']]
    dump(OUT / 'mistakes.json', mistakes)


def run():
    if OUT.exists():
        raise FileExistsError('Route experiment exists; do not overwrite')
    OUT.mkdir(parents=True)
    train_rows, dev_rows = business_split()
    all_sets = [train_rows, dev_rows, dataset('business', 'calibration'), dataset('business', 'test')]
    groups = [{r['group'] for r in rows} for rows in all_sets]
    if any(a & b for i, a in enumerate(groups) for b in groups[i + 1:]):
        raise AssertionError('Group leakage')
    dump(OUT / 'protocol.json', {'config': load_json(ROOT / 'configs/route-v3.json'),
        'sizes': dict(zip(['train', 'dev', 'calibration', 'test'], map(len, all_sets))),
        'source_sha256': {p: sha(ROOT / p) for p in ['src/qwenlab/route_v3.py', 'src/qwenlab/modeling.py',
            'src/qwenlab/train.py', 'src/qwenlab/calibrate_v2.py', 'configs/decision_spec.json',
            'configs/route-v3.json', 'data/business_zh.jsonl', 'data/processed/v2/manifest.json']},
        'baseline': 'same original prompt and NF4 inference; no adapter',
        'selection': 'dev only; macro F1, fewer human misses, lower NLL; base eligible'})
    def child(*args):
        subprocess.run([sys.executable, '-m', 'qwenlab.route_v3', *args], cwd=ROOT, check=True)
    child('train')
    cfg = load_json(ROOT / 'configs/route-v3.json')
    steps = sorted(set(range(cfg['validation_interval'], cfg['steps'] + 1, cfg['validation_interval'])) | {cfg['steps']})
    variants = ['base'] + [f'step-{s}' for s in steps]
    for variant in variants:
        child('evaluate', '--variant', variant, '--splits', 'dev')
    development = {v: route_metrics(read_rows(OUT / f'{v}-dev.jsonl')) for v in variants}
    selected = max(variants, key=lambda v: selection_key(development[v]))
    dump(OUT / 'selection.json', {'selected': selected, 'development': development})
    for variant in dict.fromkeys(['base', selected]):
        child('evaluate', '--variant', variant, '--splits', 'calibration', 'test')
    report(selected)
    print('Completed route experiment:', selected, flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['run', 'train', 'evaluate'])
    parser.add_argument('--variant', default='base'); parser.add_argument('--splits', nargs='+', default=['dev'], choices=['dev', 'calibration', 'test'])
    args = parser.parse_args()
    if args.action == 'run': run()
    elif args.action == 'train': train()
    else: evaluate(args.variant, args.splits)


if __name__ == '__main__':
    main()
