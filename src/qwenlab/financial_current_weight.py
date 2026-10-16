"""Prepare the 0.8B layer-weight experiment; no training launcher or API calls.

Weights belong to original business rows, not action classes or microbatches.
The frozen baseline remains untouched. GPU execution is a separate next step.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from qwenlab.financial_sampling_plan import layer_of

ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'configs/financial-08b-current-weight-v1.json'
OUT = 'docs/evidence/financial-08b-current-weight-v1/preparation.json'
TRAIN = ('data/financial-sampling-study-v1/pool-v1/train.json',
         'data/financial-state-pair-study-v1/schedule-v1/additions.json')
PLAN = 'data/financial-full-coverage-study-v1/schedule-v1/plan.json'
RAW_WEIGHTS = {'current-node': 3, 'current-component': 3, 'planned': 1, 'preauth': 1}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def weight_plan(rows, steps, raw_weights):
    if raw_weights != RAW_WEIGHTS:
        raise ValueError('This experiment fixes layer weights at 3:3:1:1')
    ids = [r['id'] for r in rows]
    if not rows or len(set(ids)) != len(ids) or any(r.get('split') != 'train' for r in rows):
        raise ValueError('Unique training-only rows required')
    if any(not isinstance(i, str) or not i for i in ids):
        raise ValueError('Nonempty string row IDs required')
    epoch_steps = (len(rows) + 7) // 8
    if len(steps) != epoch_steps * 2:
        raise ValueError('Exactly two complete epochs required')
    expected = Counter(ids)
    for epoch in range(2):
        section = steps[epoch * epoch_steps:(epoch + 1) * epoch_steps]
        if Counter(i for batch in section for i in batch) != expected:
            raise ValueError('Each row must occur once in each epoch')
        for index, batch in enumerate(section):
            size = min(8, len(rows) - index * 8)
            if len(batch) != size:
                raise ValueError('Actual batch size / final partial batch differs')
    layers = {r['id']: layer_of(r) for r in rows}
    counts = Counter(layers.values())
    mean = sum(raw_weights[layer] for layer in layers.values()) / len(rows)
    weights = {i: raw_weights[layer] / mean for i, layer in layers.items()}
    mass = {k: counts[k] * raw_weights[k] for k in raw_weights}
    summary = dict(rows=len(rows), steps=len(steps), layer_counts=dict(counts),
                   raw_weights=raw_weights, pool_mean_raw_weight=mean,
                   normalized_layer_weights={k: v / mean for k, v in raw_weights.items()},
                   objective_mass_share={k: v / sum(mass.values()) for k, v in mass.items()},
                   weighted_rows_sha256=digest(weights), step_rows_sha256=digest(steps),
                   row_layers_sha256=digest(layers), epochs=2)
    return weights, summary


def weighted_micro_backward(tokenizer, model, block, weights, actual_batch_size, *, scorer=None):
    """Backward one microbatch; return its contribution to the full batch loss.

    Sum contributions across microbatches without further averaging. The tool
    objective uses the same original-row denominator, including non-tool rows.
    """
    import torch
    if type(actual_batch_size) is not int or not 0 < len(block) <= actual_batch_size <= 8:
        raise ValueError('Invalid actual effective batch size')
    if len(block) != len(weights) or any(
            isinstance(w, bool) or not isinstance(w, (int, float))
            or not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError('Positive finite weight required for every original row')
    if scorer is None:
        from qwenlab.financial_train import batch_scores
        scorer = batch_scores

    def backward(items, item_weights, multiplier):
        if not items:
            return 0.0
        scores = scorer(tokenizer, model, items)
        if len(scores) != len(items):
            raise ValueError('Incomplete candidate scores')
        terms = [torch.nn.functional.cross_entropy(
            score[None, :], torch.tensor([item['target']], device=score.device)) * weight
            for score, item, weight in zip(scores, items, item_weights)]
        contribution = sum(terms) * multiplier / actual_batch_size
        if not bool(torch.isfinite(contribution).item()):
            raise FloatingPointError('Nonfinite weighted loss')
        contribution.backward()
        return float(contribution.detach())

    action = backward([r['action'] for r in block], weights, 1.0)
    tool_pairs = [(r['tool'], w) for r, w in zip(block, weights) if r['tool'] is not None]
    tool = backward([p[0] for p in tool_pairs], [p[1] for p in tool_pairs], .75)
    return dict(loss=action + tool, action_contribution=action,
                tool_contribution=tool, true_tools=len(tool_pairs))


def checkpoint_binding(preparation, completed_step):
    """Additional binding required alongside adapter/optimizer/RNG checkpoints."""
    if type(completed_step) is not int or not 0 <= completed_step <= preparation['weighting']['steps']:
        raise ValueError('Invalid checkpoint cursor')
    return dict(preparation_sha256=digest(preparation), completed_step=completed_step,
                next_step=completed_step + 1,
                weighted_rows_sha256=preparation['weighting']['weighted_rows_sha256'],
                step_rows_sha256=preparation['weighting']['step_rows_sha256'])


def validate_resume(saved, preparation, completed_step):
    if saved != checkpoint_binding(preparation, completed_step):
        raise ValueError('Checkpoint weights, schedule, preparation or cursor changed')


def build_preparation(root=ROOT):
    root = Path(root)
    cfg = read(root / CONFIG)
    if (cfg['model'] != 'Qwen/Qwen3.5-0.8B' or cfg['training_enabled'] is not False
            or cfg['status'] != 'preparation_only' or cfg['raw_weights'] != RAW_WEIGHTS):
        raise ValueError('Not the fixed 0.8B preparation configuration')
    for name, expected in cfg['sources'].items():
        if not (root / name).resolve().is_relative_to(root.resolve()):
            raise ValueError('Source outside repository')
        if sha(root / name) != expected:
            raise ValueError('Frozen baseline source changed: ' + name)
    rows = read(root / TRAIN[0]) + read(root / TRAIN[1])
    steps = read(root / PLAN)['step_rows']
    weights, summary = weight_plan(rows, steps, cfg['raw_weights'])
    if len(weights) != 13378 or len(steps) != 3346:
        raise ValueError('Unexpected complete-coverage dataset')
    recipe = cfg['baseline_recipe']
    if (recipe['model'] != cfg['model'] or recipe['effective_batch'] != 8
            or recipe['micro_batch'] != 2 or recipe['learning_rate'] != 5e-5
            or recipe['steps_per_arm'] != 3346 or recipe['initial_adapter'] is not None):
        raise ValueError('Baseline recipe differs')
    return dict(version=cfg['version'], status='prepared_not_training_ready',
                config_sha256=sha(root / CONFIG), baseline_protocol_sha256=cfg['baseline_protocol_sha256'],
                recipe_sha256=digest(recipe), source_sha256=cfg['sources'], weighting=summary,
                implementation_sha256=sha(root / 'src/qwenlab/financial_current_weight.py'),
                tests_sha256=sha(root / 'tests/test_financial_current_weight.py'),
                loss='sum_i(w_i * (CE_action_i + 0.75 * I_tool_i * CE_tool_i)) / actual_batch_rows',
                weight_normalization='fixed pool mean; never normalize by a microbatch or tool count',
                pending_before_main=cfg['pending_before_main'],
                evaluation_examples_read=False, model_api_requests=0, model_training_steps=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    args = parser.parse_args()
    value = build_preparation()
    path = ROOT / OUT
    if path.exists():
        if read(path) != value:
            raise ValueError('Preparation differs; preserve old version and create a new one')
    elif args.command == 'verify':
        raise FileNotFoundError('Run prepare first')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    print(json.dumps(dict(status=value['status'], weighting=value['weighting'],
                         model_training_steps=0, model_api_requests=0), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
