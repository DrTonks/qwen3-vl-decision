"""Offline audit of the current Jev benchmark, including all proxy phases. No API calls."""
from collections import Counter
from qwenlab import financial_jev_reference as io
from qwenlab import financial_jev_current_session_v2 as current
from qwenlab.financial_actions_metrics import percentile


def run():
    rows, protocol = current.freeze()
    metrics, completion = current.evaluate_offline(rows, protocol)
    predictions = io.read(current.PUBLIC / 'predictions.json')
    gold = {r['id']: r['annotation'] for r in rows}
    correct = sum(p['action'] == gold[p['id']]['action'] for p in predictions)
    joint = sum(p['action'] == 'tool' and gold[p['id']]['action'] == 'tool'
                and p['tool_name'] == gold[p['id']]['tool_name'] for p in predictions)
    assert correct / 128 == metrics['action_accuracy']
    assert joint / 18 == metrics['action_tool_joint_accuracy']
    anomalies = []
    strict_correct = 0
    strict_joint = 0
    for p in predictions:
        all_valid = True
        for task in ('action', 'tool'):
            answer = p.get(task + '_prediction')
            if answer is None:
                continue
            valid = answer['probabilities'][answer['choice']] >= max(answer['probabilities'].values()) - 1e-6
            assert valid == answer['choice_probability_consistent']
            if not valid:
                all_valid = False
                anomalies.append(dict(id=p['id'], task=task, choice=answer['choice'],
                    probabilities=answer['probabilities']))
        if all_valid:
            strict_correct += p['action'] == gold[p['id']]['action']
            strict_joint += (p['action'] == 'tool' and gold[p['id']]['action'] == 'tool'
                             and p['tool_name'] == gold[p['id']]['tool_name'])

    phases = ['financial-jev-current-proxy-v1', 'financial-jev-current-session-v1',
              'financial-jev-current-session-v2']
    elapsed = Counter()
    failed = []
    phase_counts = {}
    bindings = {}
    for phase in phases:
        folder = io.ROOT / 'results' / phase
        failures = list((folder / 'authorized-retries').glob('attempt-*/failed.json'))
        failures += [p for p in (folder / 'requests').glob('*.json')
                     if io.read(p)['state'] != 'returned']
        phase_counts[phase] = len(failures)
        for path in failures:
            record = io.read(path)
            assert record['state'] in ('pending', 'failed_or_uncertain')
            assert record['request_sha256'] == protocol['requests'][record['id']][record['task']]
            note_path = path.parent / 'authorization.json'
            backoff = io.read(note_path)['backoff_s'] if note_path.exists() else 0
            elapsed[record['id']] += record.get('elapsed_s', 0) + backoff
            relative = path.relative_to(io.ROOT).as_posix()
            bindings[relative] = io.file_sha(path)
            failed.append(dict(path=relative, id=record['id'], task=record['task'],
                error=record.get('error'), elapsed_s=record.get('elapsed_s', 0), backoff_s=backoff))
    successful = []
    for path in sorted((current.OUT / 'requests').glob('*.json')):
        record = io.read(path)
        assert record['state'] == 'returned'
        elapsed[record['id']] += record['elapsed_s']
        successful.append(record)
        bindings[path.relative_to(io.ROOT).as_posix()] = io.file_sha(path)
    assert len(successful) == completion['requests']
    assert len(elapsed) == 128
    comparison = []
    sources = [
        ('Jev API (jev-1.13.0)', current.PUBLIC / 'metrics.json'),
        ('Original Qwen3-VL-2B', io.ROOT / 'results/financial-2b-full-coverage-v1/development/base/metrics.json'),
        ('Original Qwen3.5-0.8B', io.ROOT / 'results/financial-full-coverage-v1/development/base/metrics.json'),
        ('Trained Qwen3-VL-2B step 1673', io.ROOT / 'results/financial-2b-full-coverage-v1/development/full2b-step-1673/metrics.json'),
        ('Trained Qwen3.5-0.8B step 1673', io.ROOT / 'results/financial-full-coverage-v1/development/fullcover-step-1673/metrics.json')]
    for name, path in sources:
        m = io.read(path)
        assert (m['rows'], m['data_sha256']) == (128, metrics['data_sha256'])
        if name.startswith('Jev'):
            bound_policy = protocol['policy_sha256']
        else:
            model_protocol = io.read(path.parents[2] / 'protocol.json')
            assert model_protocol['prompt_sha256'] == m['prompt_sha256']
            assert io.file_sha(path.parents[2] / 'protocol.json') == m['protocol_sha256']
            bound_policy = model_protocol['policy_sha256']
        assert bound_policy == protocol['policy_sha256']
        comparison.append(dict(model=name, correct=round(m['action_accuracy'] * 128),
            action_accuracy=m['action_accuracy'], joint_tool_correct=round(m['action_tool_joint_accuracy'] * 18),
            human_misses=len(m['human_misses']), false_refusals=len(m['false_refusals']),
            latency=m['latency'], macro_f1=m['macro_f1'], source=path.relative_to(io.ROOT).as_posix(),
            source_sha256=io.file_sha(path), policy_sha256=bound_policy,
            prompt_sha256=m['prompt_sha256']))
    result = dict(status='verified', scope='128 synthetic development samples only; not final test or deployment approval',
        data_sha256=metrics['data_sha256'], policy_sha256=metrics['prompt_sha256'],
        comparison=comparison, response_anomalies=anomalies,
        strict_response_metrics=dict(policy='A sample fails if ANY returned task choice is not a probability maximum; no answer replacement or retry',
            action_correct=strict_correct, action_accuracy=strict_correct / 128,
            joint_tool_correct=strict_joint, joint_tool_accuracy=strict_joint / 18),
        all_proxy_phases=dict(successful_requests=len(successful), failed_or_uncertain_attempts=len(failed),
            total_attempts=len(successful) + len(failed), failures_per_phase=phase_counts,
            input_tokens_success=sum(r['body']['usage']['input_tokens'] for r in successful),
            output_tokens_success=sum(r['body']['usage'].get('output_tokens', 0) for r in successful),
            failed_usage_and_cost='unknown', failures=failed,
            retry_inclusive_latency=dict(p50_s=percentile(list(elapsed.values()), .5),
                p95_s=percentile(list(elapsed.values()), .95), per_sample_s=dict(elapsed),
                scope='All proxy successful/failed HTTP durations and recorded backoffs; excludes manual downtime, unauthenticated probes and process startup')),
        raw_ledger_sha256=bindings, audit_source_sha256=io.file_sha(__file__))
    io.write(current.PUBLIC / 'comparison-audit.json', result)
    print(__import__('json').dumps({k: result[k] for k in ('comparison', 'response_anomalies', 'strict_response_metrics')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
