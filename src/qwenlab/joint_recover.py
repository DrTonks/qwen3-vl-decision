"""Resume missing v4 evaluation artifacts after an externally interrupted process.

Frozen training/scoring/selection files remain unchanged. Completed predictions
are retained; incomplete dataset inference is rerun with identical batch=1 code.
"""
import gc
import time
import torch
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.joint_v4 import OUT, DATA, CKPT, dump, metrics, predict_rows
from qwenlab.modeling import load_model
from qwenlab.summarize import percentile


def main():
    protocol = load_json(OUT / 'protocol.json')
    if not all(sha(ROOT / k) == v for k, v in protocol['source_sha256'].items()):
        raise AssertionError('Frozen source changed')
    selected = load_json(OUT / 'selection.json')['selected']
    path = OUT / 'recovery.json'
    if path.exists():
        raise FileExistsError('Recovery already recorded; inspect before retrying')
    record = {'reason': 'Original GPU evaluator and completion worker absent; no traceback recorded. Underlying cause unconfirmed.',
              'training_restarted': False, 'selection_changed': False, 'frozen_source_integrity': True,
              'selected': selected, 'status': 'running', 'new_artifacts': [],
              'source_sha256': sha(ROOT / 'src/qwenlab/joint_recover.py')}
    dump(path, record)
    try:
        for variant in dict.fromkeys(['base', selected]):
            folder = OUT / variant
            missing = [(name, split) for split in ('calibration', 'test') for name in ('business', 'massive')
                       if not (folder / f'{name}-{split}.jsonl').exists()]
            need_latency = not (folder / 'latency.json').exists()
            if not missing and not need_latency:
                continue
            tok, model = load_model('nf4', None if variant == 'base' else (CKPT / variant).relative_to(ROOT).as_posix())
            tok.padding_side = 'left'; model.eval()
            for name, split in missing:
                rows = read_rows(DATA / f'{name}-{split}.jsonl'); start = time.perf_counter()
                result = predict_rows(tok, model, rows); elapsed = time.perf_counter() - start
                output = folder / f'{name}-{split}.jsonl'; write_rows(output, result)
                value = metrics(result); value['batch_eval_wall_s'] = elapsed
                dump(folder / f'{name}-{split}-metrics.json', value)
                record['new_artifacts'].append(output.relative_to(OUT).as_posix()); dump(path, record)
                print('Recovered', variant, name, split, len(rows), flush=True)
            if need_latency:
                rows = read_rows(DATA / 'business-test.jsonl')[:32]; predict_rows(tok, model, rows[:1])
                latencies = []
                for row in rows:
                    torch.cuda.synchronize(); start = time.perf_counter()
                    predict_rows(tok, model, [row]); torch.cuda.synchronize()
                    latencies.append(time.perf_counter() - start)
                dump(folder / 'latency.json', {'scope': 'sequential customer requests, three serial intent/route/tool forwards; no model loading',
                     'n': len(rows), 'p50_s': percentile(latencies, .5), 'p95_s': percentile(latencies, .95), 'values_s': latencies})
                record['new_artifacts'].append(f'{variant}/latency.json'); dump(path, record)
            del tok, model
            gc.collect(); torch.cuda.empty_cache()
        record['status'] = 'complete'; dump(path, record)
        print('Completed local joint experiment', selected, flush=True)
    except Exception as exc:
        record.update(status='failed', error=type(exc).__name__); dump(path, record)
        raise


if __name__ == '__main__':
    main()
