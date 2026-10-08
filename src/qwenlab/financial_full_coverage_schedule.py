"""Two deterministic complete passes; frozen old pool and additions unchanged."""
from collections import Counter
import random
from qwenlab import financial_state_pair_cycle as old
from qwenlab import financial_state_pair_schedule as parent
from qwenlab.common import ROOT, sha

OUT = ROOT / 'data/financial-full-coverage-study-v1/schedule-v1'
CONFIG = ROOT / 'configs/financial-full-coverage-execution-v1.json'
CANDIDATES = parent.CANDIDATES
read = old.read


def source_bindings():
    parent.verify()
    values = parent.source_bindings()
    for name in ('src/qwenlab/financial_full_coverage_schedule.py',
                 'configs/financial-full-coverage-execution-v1.json'):
        values[name] = sha(ROOT / name)
    for path in (parent.OUT / 'manifest.json', parent.OUT / 'additions.json'):
        values[old.relative(path)] = sha(path)
    return values


def make_plan(ids, cfg):
    if len(ids) != cfg['rows'] or len(set(ids)) != len(ids):
        raise ValueError('Unique complete pool required')
    result, epochs = [], []
    for epoch in range(cfg['epochs']):
        rows = sorted(ids)
        random.Random(cfg['sampling_seed'] + epoch).shuffle(rows)
        batches = [rows[p:p+cfg['batch']] for p in range(0, len(rows), cfg['batch'])]
        if len(batches) != cfg['steps_per_epoch']:
            raise ValueError('Epoch step count differs')
        result.extend(batches)
        epochs.append(dict(epoch=epoch+1, first_step=epoch*len(batches)+1,
                           last_step=(epoch+1)*len(batches), rows=len(rows),
                           last_batch_size=len(batches[-1])))
    if len(result) != cfg['steps_per_arm']:
        raise ValueError('Total step count differs')
    return dict(version='financial-full-coverage-plan-v1', step_rows=result, epochs=epochs)


def validate_plan(plan, rows, cfg):
    if plan != make_plan([r['id'] for r in rows], cfg):
        raise ValueError('Frozen complete row-ID schedule changed')
    for epoch in plan['epochs']:
        counts = Counter(x for b in plan['step_rows'][epoch['first_step']-1:epoch['last_step']] for x in b)
        if counts != Counter({r['id']:1 for r in rows}):
            raise ValueError('Each original row must appear exactly once per epoch')
    return plan['step_rows']


def build():
    parent.verify()
    rows = old.execution_rows()
    cfg = read(CONFIG)
    plan = make_plan([r['id'] for r in rows], cfg)
    validate_plan(plan, rows, cfg)
    old.immutable_json(OUT / 'plan.json', plan)
    counts = Counter(r['annotation']['action'] for r in rows)
    old.immutable_json(OUT / 'summary.json', dict(rows=len(rows), epochs=cfg['epochs'],
        sample_positions=len(rows)*cfg['epochs'], optimizer_steps=len(plan['step_rows']),
        actions_per_epoch=dict(counts), training_enabled=False,
        note='Design bytes only; user execution permission recorded separately.'))
    old.immutable_json(OUT / 'manifest.json', dict(sources=source_bindings(),
        files={n:sha(OUT/n) for n in ('plan.json','summary.json')}))
    return verify()


def verify():
    manifest = read(OUT / 'manifest.json')
    if manifest['sources'] != source_bindings():
        raise ValueError('Complete coverage source closure changed')
    if any(sha(OUT/n) != h for n,h in manifest['files'].items()):
        raise ValueError('Complete coverage artifact changed')
    rows = old.execution_rows()
    validate_plan(read(OUT / 'plan.json'), rows, read(CONFIG))
    return manifest


if __name__ == '__main__':
    import json
    build()
    print(json.dumps(read(OUT / 'summary.json'), ensure_ascii=False, indent=2))
