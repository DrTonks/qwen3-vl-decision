"""Validate the new inference wrapper after v5 releases the GPU, without retraining."""
import argparse
import json
import random
import time
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows, write_rows

TARGET = ROOT / 'results/joint-v5/projection-inference'


def run():
    import torch
    from qwenlab.candidate_inference import CandidateScorer
    from qwenlab.joint_v5 import DATA, OUT, adapter_for, atomic_json, encode
    from qwenlab.modeling import load_model
    from qwenlab.summarize import percentile
    selected = load_json(OUT / 'selection.json')['selected']
    tok, model = load_model('nf4', adapter_for(selected)); tok.padding_side = 'left'; model.eval()
    scorer = CandidateScorer(model)
    atomic_json(TARGET / 'protocol.json', {'variant': selected, 'source_sha256': {
        p: sha(ROOT / p) for p in ['src/qwenlab/candidate_inference.py', 'src/qwenlab/projection_validate.py']},
        'scope': 'All v5 business/MASSIVE/CrossWOZ dev tasks; same model, alternating 12 business requests x3 latency',
        'gate': 'No argmax differences, max probability difference <= 1e-4; no minimum speed gain required',
        'startup_verification': 'Excluded from timing; included in correctness checks', 'training_changed': False})
    rows = read_rows(DATA / 'business-dev.jsonl') + read_rows(DATA / 'massive-dev.jsonl') + read_rows(DATA / 'crosswoz-dev.jsonl')
    comparisons = []
    def score(row, task, mode):
        example = encode(tok, row, task)
        inputs = tok.pad([example['tokens']], padding=True, return_tensors='pt').to('cuda')
        if mode == 'full': return model(**inputs, logits_to_keep=1, use_cache=False).logits[0, -1, example['ids']].float()
        return scorer.scores(inputs, example['ids'])[0]
    with torch.inference_mode():
        for row in rows:
            for task in (('intent', 'route', 'tool') if row['dataset'] == 'business' else ('intent',)):
                full = score(row, task, 'full'); candidate = score(row, task, 'candidate')
                comparisons.append({'id': row['id'], 'task': task, 'same_choice': bool(full.argmax() == candidate.argmax()),
                    'max_logit_delta': (full - candidate).abs().max().item(),
                    'max_probability_delta': (full.softmax(-1) - candidate.softmax(-1)).abs().max().item()})
        write_rows(TARGET / 'agreement.jsonl', comparisons)
        sample = random.Random(20260927).sample(read_rows(DATA / 'business-dev.jsonl'), 12)
        def request(row, mode): return [score(row, task, mode).softmax(-1).cpu().tolist() for task in ('intent', 'route', 'tool')]
        for mode in ('full', 'candidate'): request(sample[0], mode)
        times = []
        for repeat in range(3):
            for i, row in enumerate(sample):
                for mode in (('full', 'candidate') if (repeat + i) % 2 == 0 else ('candidate', 'full')):
                    torch.cuda.synchronize(); start = time.perf_counter(); request(row, mode); torch.cuda.synchronize()
                    times.append({'id': row['id'], 'repeat': repeat, 'mode': mode, 'elapsed_s': time.perf_counter() - start})
        write_rows(TARGET / 'latency.jsonl', times)
    passed = scorer.projection == 'candidate' and all(r['same_choice'] and r['max_probability_delta'] <= 1e-4 for r in comparisons)
    atomic_json(TARGET / 'metrics.json', {'passed': passed, 'n': len(comparisons), 'fallback_reason': scorer.fallback_reason,
        'choice_mismatches': sum(not r['same_choice'] for r in comparisons),
        'max_probability_delta': max(r['max_probability_delta'] for r in comparisons),
        'latency': {m: {f'p{int(q*100)}_s': percentile([x['elapsed_s'] for x in times if x['mode'] == m], q) for q in (.5, .95)} for m in ('full', 'candidate')},
        'scope': 'One loaded selected model; text only; warmup/load excluded; tokenizer and result CPU transfer included'})
    if not passed: raise AssertionError('New candidate wrapper failed validation; use --projection full')


def main():
    from qwenlab.joint_v5 import OUT, atomic_json, exclusive_lock
    p = argparse.ArgumentParser(); p.add_argument('--after-v5', action='store_true'); args = p.parse_args()
    TARGET.mkdir(parents=True, exist_ok=True)
    with exclusive_lock('projection-validation.lock'):
        if (TARGET / 'metrics.json').exists(): raise FileExistsError('Preserve completed validation')
        atomic_json(TARGET / 'status.json', {'status': 'waiting', 'dependency': 'v5 pipeline completion; no GPU contention'})
        try:
            start = time.monotonic()
            while True:
                state = load_json(OUT / 'status.json')
                if state['status'] == 'failed': raise RuntimeError('v5 failed; validation not started')
                if state['status'] == 'complete': break
                if not args.after_v5: raise RuntimeError('v5 still running; use --after-v5')
                if time.monotonic() - start > 48 * 3600: raise TimeoutError('v5 not completed within 48h')
                time.sleep(30)
            # status=complete is written just before v5 publication finishes.
            # Wait until that process actually releases its pipeline lock.
            while True:
                try:
                    with exclusive_lock('joint-v5-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'):
                        atomic_json(TARGET / 'status.json', {'status': 'running'})
                        run()
                    break
                except RuntimeError as exc:
                    if not str(exc).startswith('Another worker holds'): raise
                    if time.monotonic() - start > 48 * 3600: raise TimeoutError('Pipeline lock remained busy')
                    time.sleep(30)
            atomic_json(TARGET / 'status.json', {'status': 'complete'})
        except BaseException as exc:
            atomic_json(TARGET / 'status.json', {'status': 'failed', 'error': type(exc).__name__}); raise


if __name__ == '__main__': main()
