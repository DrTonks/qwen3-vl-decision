"""Isolated output-head optimization experiment; does not change frozen v4 scoring."""
import argparse
from contextlib import contextmanager
import time
import torch
from torch import nn
from qwenlab.common import ROOT, load_json, sha
from qwenlab.joint_v4 import OUT, DATA, CKPT, encode, dump
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.summarize import percentile


class CandidateHead(nn.Module):
    """Inference-only copy of selected vocabulary projection rows."""
    def __init__(self, head, ids):
        super().__init__()
        if not isinstance(head, nn.Linear):
            raise TypeError('Requires an unquantized Linear lm_head')
        if not ids or len(set(ids)) != len(ids) or min(ids) < 0 or max(ids) >= head.out_features:
            raise ValueError('Candidate token IDs must be unique and in vocabulary')
        indices = torch.tensor(ids, device=head.weight.device)
        self.register_buffer('weight', head.weight.detach().index_select(0, indices).clone())
        self.register_buffer('bias', None if head.bias is None else head.bias.detach().index_select(0, indices).clone())

    def forward(self, hidden):
        return nn.functional.linear(hidden, self.weight, self.bias)


@contextmanager
def temporary_head(base, head):
    original = base.lm_head
    base.lm_head = head
    try:
        yield
    finally:
        base.lm_head = original


def ready():
    path = OUT / 'completion.json'
    status = load_json(path)['status'] if path.exists() else 'missing'
    if status == 'failed':
        raise RuntimeError('Frozen evaluation failed; inspect it before benchmarking')
    # completion.json precedes export by a few seconds: require the final marker too.
    log = ROOT / '.local/joint-v4-completion-console.txt'
    finished = log.exists() and 'Completed reports and publication audit/export' in log.read_text(encoding='utf-8-sig', errors='replace')
    return status == 'complete' and finished


def run():
    if not ready():
        raise RuntimeError('Wait for the frozen GPU evaluation and report worker to finish')
    target = OUT / 'candidate-benchmark'
    if (target / 'metrics.json').exists():
        raise FileExistsError('Preserve the completed benchmark')
    target.mkdir(exist_ok=True)
    selected = load_json(OUT / 'selection.json')['selected']
    protocol = {'variant': selected, 'precision': 'nf4 backbone, original lm_head dtype preserved',
                'batch_size': 1, 'data': 'complete business and MASSIVE development sets only',
                'latency': '12 seeded business dev requests, three serial task forwards, 3 repetitions, alternating order; tokenization and CPU result transfer included; model/head loading and warmup excluded',
                'acceptance': 'all candidate argmax equal, max probability difference <= 0.01; P50 and P95 each improve >= 5% to recommend further validation',
                'default_implementation_changed': False,
                'source_sha256': sha(ROOT / 'src/qwenlab/candidate_benchmark.py'),
                'selection_sha256': sha(OUT / 'selection.json')}
    dump(target / 'protocol.json', protocol)
    tok, model = load_model('nf4', None if selected == 'base' else (CKPT / selected).relative_to(ROOT).as_posix())
    tok.padding_side = 'left'; model.eval()
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    original = base.lm_head
    heads = {}

    def scores(x, mode):
        inputs = tok.pad([x['tokens']], padding=True, return_tensors='pt').to('cuda')
        key = tuple(x['ids'])
        if key not in heads:
            heads[key] = CandidateHead(original, x['ids']).eval()
        if mode == 'full':
            logits = model(**inputs, logits_to_keep=1, use_cache=False).logits[0, -1, x['ids']].float()
        else:
            with temporary_head(base, heads[key]):
                logits = model(**inputs, logits_to_keep=1, use_cache=False).logits[0, -1].float()
        return logits

    comparisons = []
    business = read_rows(DATA / 'business-dev.jsonl')
    public = read_rows(DATA / 'massive-dev.jsonl')
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        for row in business + public:
            for task in (['intent', 'route', 'tool'] if row['dataset'] == 'business' else ['intent']):
                x = encode(tok, row, task)
                a, b = scores(x, 'full'), scores(x, 'candidate')
                if not (torch.isfinite(a).all() and torch.isfinite(b).all()):
                    raise FloatingPointError('Nonfinite logits')
                comparisons.append({'id': row['id'], 'task': task, 'input_tokens': len(x['tokens']['input_ids']),
                                    'candidate_count': len(x['ids']), 'full_choice': x['keys'][a.argmax().item()],
                                    'candidate_choice': x['keys'][b.argmax().item()],
                                    'max_logit_delta': (a - b).abs().max().item(),
                                    'max_probability_delta': (a.softmax(-1) - b.softmax(-1)).abs().max().item()})
        import random
        rows = random.Random(20260926).sample(business, 12)

        def request(row, mode):
            # Identical three task forwards. Do not hide tokenization or CPU transfers.
            return [scores(encode(tok, row, t), mode).softmax(-1).cpu().tolist() for t in ('intent', 'route', 'tool')]

        for mode in ('full', 'candidate'):
            for row in rows[:2]:
                request(row, mode)
        timings = []
        for repeat in range(3):
            for i, row in enumerate(rows):
                for mode in (('full', 'candidate') if (repeat + i) % 2 == 0 else ('candidate', 'full')):
                    torch.cuda.synchronize(); start = time.perf_counter()
                    request(row, mode); torch.cuda.synchronize()
                    timings.append({'id': row['id'], 'repeat': repeat, 'mode': mode, 'elapsed_s': time.perf_counter() - start})
    write_rows(target / 'agreement.jsonl', comparisons)
    write_rows(target / 'latency.jsonl', timings)
    latency = {mode: {f'p{int(q*100)}_s': percentile([r['elapsed_s'] for r in timings if r['mode'] == mode], q)
                      for q in (.5, .95)} for mode in ('full', 'candidate')}
    mismatches = sum(r['full_choice'] != r['candidate_choice'] for r in comparisons)
    max_delta = max(r['max_probability_delta'] for r in comparisons)
    gains = {k: 1 - latency['candidate'][k] / latency['full'][k] for k in ('p50_s', 'p95_s')}
    result = {'n_task_predictions': len(comparisons), 'choice_mismatches': mismatches,
              'max_probability_delta': max_delta, 'max_logit_delta': max(r['max_logit_delta'] for r in comparisons),
              'latency': latency, 'relative_latency_reduction': gains,
              'agreement_gate_pass': mismatches == 0 and max_delta <= .01,
              'speed_gate_pass': all(v >= .05 for v in gains.values()),
              'peak_allocated_gib': torch.cuda.max_memory_allocated() / 2**30,
              'gpu': torch.cuda.get_device_name(), 'torch': torch.__version__,
              'default_implementation_changed': False,
              'limits': ['one device session, text dev data only', 'timing samples correlated; exploratory',
                         'original full lm_head retained in memory; no deployment memory saving measured',
                         'finite-precision kernels may differ despite algebraic equivalence',
                         'not a Mugi benchmark, no backbone compute removed']}
    dump(target / 'metrics.json', result)
    lines = ['# 候选输出层加速实验', '', '原训练/评测实现保持不变；这是独立开发集实验。', '',
             f'候选预测比较 {len(comparisons)} 次，类别不一致 {mismatches} 次，最大概率差 {max_delta:.6f}。', '',
             '|实现|请求 P50|请求 P95|', '|---|---:|---:|']
    for mode, values in latency.items():
        lines.append(f'|{mode}|{values["p50_s"]*1000:.1f} ms|{values["p95_s"]*1000:.1f} ms|')
    lines += ['', f'一致性门槛通过：{result["agreement_gate_pass"]}；速度门槛通过：{result["speed_gate_pass"]}。',
              '每个请求仍执行意图、路由、工具三个完整前向；包含分词和结果回传，不包含加载与预热。',
              '仅裁剪输出词表投影，不改变首 token 方法，不减少输入理解计算。',
              '即使通过也需要冻结后的独立回归与校准检查，再考虑替换默认实现；本实验不自动替换。']
    (target / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Candidate benchmark complete', result, flush=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--wait', action='store_true'); args = p.parse_args()
    import subprocess
    import sys
    target = OUT / 'candidate-benchmark'; target.mkdir(exist_ok=True)
    if (target / 'metrics.json').exists():
        raise FileExistsError('Preserve the completed benchmark')
    status = target / 'status.json'
    dump(status, {'status': 'waiting', 'scope': 'one-shot local follow-up, no new API requests'})
    try:
        if args.wait:
            start = time.monotonic()
            while not ready():
                if time.monotonic() - start > 4 * 3600:
                    raise TimeoutError('Prior pipeline did not complete; no GPU work started')
                time.sleep(30)
        dump(status, {'status': 'running'})
        run()
        subprocess.run([sys.executable, '-m', 'qwenlab.post_training', '--include-test'], cwd=ROOT, check=True)
        dump(status, {'status': 'complete', 'default_implementation_changed': False})
        subprocess.run([sys.executable, '-m', 'qwenlab.publish', '--export'], cwd=ROOT, check=True)
    except Exception as exc:
        dump(status, {'status': 'failed', 'error': type(exc).__name__})
        raise


if __name__ == '__main__':
    main()
