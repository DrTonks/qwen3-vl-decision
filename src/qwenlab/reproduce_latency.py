"""Replay the v4 382 ms protocol without overwriting historical evidence."""
import gc
import subprocess
import time
from datetime import datetime, timezone

from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab.joint_v4 import DATA, OUT, CKPT, encode, predict_rows
from qwenlab.joint_v5 import atomic_json, exclusive_lock
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows
from qwenlab.summarize import percentile

TARGET = ROOT / 'results/joint-v5/latency-reproduction'


def gpu_snapshot():
    result = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,temperature.gpu,power.draw',
                             '--format=csv'], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else 'unavailable'


def main():
    import torch
    with exclusive_lock('joint-v5-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'):
        if TARGET.exists():
            raise FileExistsError('Preserve the prior reproduction; use a new protocol for another run')
        TARGET.mkdir()
        rows = read_rows(DATA / 'business-test.jsonl')[:32]
        old_selection = load_json(OUT / 'selection.json')['selected']
        new_selection = load_json(ROOT / 'results/joint-v5/selection.json')['selected']
        adapters = {'v4': CKPT / old_selection,
                    'v5_old_prompt': ROOT / '.local/checkpoints/joint-v5' / new_selection}
        protocol = {'started_utc': datetime.now(timezone.utc).isoformat(),
            'sample_ids': [r['id'] for r in rows], 'repetitions': 3,
            'selections': {'v4': old_selection, 'v5_old_prompt': new_selection},
            'original_latency': load_json(OUT / old_selection / 'latency.json'),
            'method': 'Original v4 predict_rows, same first32 test rows in original order; one warmup request; three serial forwards; NF4; complete vocabulary output; three repeats',
            'includes': 'encoding, tokenization, padding, forward, softmax and CPU result processing',
            'excludes': 'loading, warmup, file writes and GPU telemetry',
            'limits': 'same software request path; historical thermal/power/load state cannot be reproduced; v5 with v4 prompt is timing only, not a v5 business accuracy evaluation',
            'source_hashes': {name: sha(ROOT / name) for name in ['src/qwenlab/reproduce_latency.py', 'src/qwenlab/joint_v4.py', 'src/qwenlab/modeling.py', 'configs/decision_spec.json']},
            'data_sha256': sha(DATA / 'business-test.jsonl'),
            'adapter_sha256': {key: sha(path / 'adapter_model.safetensors') for key, path in adapters.items()},
            'gpu_before': gpu_snapshot()}
        atomic_json(TARGET / 'protocol.json', protocol)
        state = {'status': 'loading', 'completed': 0, 'total': 192}
        atomic_json(TARGET / 'status.json', state)
        timings = []
        try:
            references = {r['id']: r for r in read_rows(OUT / old_selection / 'business-test.jsonl')}
            differences = 0
            for variant, adapter in adapters.items():
                tok, model = load_model('nf4', adapter.relative_to(ROOT).as_posix())
                tok.padding_side = 'left'
                model.eval()
                lengths = {r['id']: {task: len(encode(tok, r, task)['tokens']['input_ids'])
                                    for task in ('intent', 'route', 'tool')} for r in rows}
                atomic_json(TARGET / f'{variant}-input-lengths.json', lengths)
                predict_rows(tok, model, rows[:1])
                state.update(status='running', variant=variant)
                for repeat in range(3):
                    for row in rows:
                        torch.cuda.synchronize()
                        start = time.perf_counter()
                        pred = predict_rows(tok, model, [row])[0]
                        torch.cuda.synchronize()
                        elapsed = time.perf_counter() - start
                        if variant == 'v4':
                            differences += sum(pred['predictions'][t]['choice'] != references[row['id']]['predictions'][t]['choice']
                                               for t in ('intent', 'route', 'tool'))
                        record = {'variant': variant, 'repeat': repeat, 'id': row['id'], 'elapsed_s': elapsed}
                        timings.append(record)
                        append_json(TARGET / 'timings.jsonl', record)
                        state['completed'] += 1
                    atomic_json(TARGET / 'status.json', state)
                    print(variant, 'repeat', repeat + 1, 'complete', flush=True)
                del model, tok
                gc.collect()
                torch.cuda.empty_cache()
            metrics = {'v4_choice_differences': differences, 'gpu_after': gpu_snapshot(), 'variants': {}}
            for variant in adapters:
                by_repeat = [[x['elapsed_s'] for x in timings if x['variant'] == variant and x['repeat'] == rep] for rep in range(3)]
                pooled = sum(by_repeat, [])
                metrics['variants'][variant] = {'n': len(pooled), 'p50_s': percentile(pooled, .5), 'p95_s': percentile(pooled, .95),
                    'repeats': [{'p50_s': percentile(xs, .5), 'p95_s': percentile(xs, .95)} for xs in by_repeat]}
            atomic_json(TARGET / 'metrics.json', metrics)
            state.update(status='complete')
            atomic_json(TARGET / 'status.json', state)
            print(metrics, flush=True)
        except Exception as exc:
            state.update(status='failed', error=type(exc).__name__)
            atomic_json(TARGET / 'status.json', state)
            raise


if __name__ == '__main__':
    main()
