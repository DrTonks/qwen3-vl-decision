"""Recompute completed sampling-study development results, without inference/API.

Run from the repository root with .venv-qwen35/Scripts/python.exe.
Only saved development predictions and training/checkpoint metadata are read.
"""
from collections import Counter
from datetime import datetime
import json
import math
import statistics

from qwenlab import financial_sampling_cycle as c


def probability_diagnostics(rows, predictions):
    lookup = {r['id']: r for r in rows}
    nll = brier = 0.
    confident_errors = 0
    for pred in predictions:
        gold = lookup[pred['id']]['annotation']['action']
        probs = pred['action_prediction']['probabilities']
        nll -= math.log(max(probs[gold], 1e-12))
        brier += sum((probs[a] - int(a == gold)) ** 2 for a in c.prompt.SPEC['actions'])
        confident_errors += pred['action'] != gold and max(probs.values()) >= .95
    return dict(action_nll=nll / len(rows), brier=brier / len(rows),
                wrong_with_confidence_at_least_95=confident_errors)


def transitions(rows, left, right):
    a, b = ({p['id']: p for p in items} for items in (left, right))
    counts = Counter()
    changes = []
    for row in rows:
        rid, gold = row['id'], row['annotation']['action']
        old, new = a[rid]['action'] == gold, b[rid]['action'] == gold
        kind = ('both_correct' if old else 'fixed') if new else ('regressed' if old else 'both_wrong')
        counts[kind] += 1
        if old != new:
            changes.append(dict(id=rid, cohort=row['cohort'], expected=gold,
                                before=a[rid]['action'], after=b[rid]['action'], change=kind))
    return dict(counts=dict(counts), changes=changes,
                paired_group_bootstrap=c.paired_bootstrap(rows, left, right, 20261004, repeats=10000))


def main():
    run = c.Run(c.DEFAULT)
    protocol = c.read(run.out / 'protocol.json')
    completion = c.read(run.out / 'completion.json')
    status = c.progress(run)
    assert status['stage'] == 'complete' and not status['worker_alive'] and status['safe_to_shutdown']
    assert completion['protocol_sha256'] == run.protocol_hash()
    assert protocol['common_binding']['source_sha256'] == c.source_bindings()
    assert protocol['common_binding']['review_sha256'] == c.sha(c.REVIEW)
    c.verify_review()
    rows = c.evaluation_rows(run, protocol, 'development', 'base')
    variants = ['base', 'uniform-step-200', 'uniform-step-400', 'stratified-step-200', 'stratified-step-400']
    reports, predictions, table = {}, {}, {}
    for variant in variants:
        folder = run.out / 'development' / variant
        assert c.read(folder / 'binding.json') == c.eval_binding(run, protocol, variant, 'development')
        preds = c.ft.rows_file(folder / 'predictions.jsonl')
        c.ft.evaluation_prefix(rows, preds)
        assert len(preds) == len(rows) == 128
        m = c.metrics.evaluate(rows, preds, protocol['prompt_sha256'], run.protocol_hash())
        assert m == c.read(folder / 'metrics.json')
        reports[variant], predictions[variant] = m, preds
        timing = c.read(folder / 'timing.json')
        for field, expected in {
            'action_p50_s': c.ft.metrics.percentile([p['action_elapsed_s'] for p in preds], .5),
            'request_p50_s': c.ft.metrics.percentile([p['elapsed_s'] for p in preds], .5),
            'request_p95_s': c.ft.metrics.percentile([p['elapsed_s'] for p in preds], .95),
            'total_measured_s': sum(p['elapsed_s'] for p in preds),
        }.items():
            assert math.isclose(timing[field], expected, abs_tol=1e-12)
        table[variant] = dict(
            rows=len(rows), correct=round(m['action_accuracy'] * len(rows)),
            action_accuracy=m['action_accuracy'], macro_f1=m['macro_f1'],
            joint_correct=round(m['action_tool_joint_accuracy'] * m['tool_support']),
            tool_support=m['tool_support'], per_action=m['per_action'],
            failures={k: len(m[k]) for k in ['human_misses', 'false_refusals',
                'unavailable_knowledge_retrievals', 'unauthenticated_tool_actions', 'unavailable_tool_choices']},
            cohorts={k: dict(rows=v['rows'], correct=round(v['action_accuracy'] * v['rows']),
                human_misses=len(v['human_misses']), false_refusals=len(v['false_refusals']),
                joint_accuracy=v['action_tool_joint_accuracy'], tool_support=v['tool_support'])
                for k, v in m['cohorts'].items()},
            probability=probability_diagnostics(rows, preds), timing=timing)
    selected_reports = dict(base=reports['base'], uniform=reports['uniform-step-400'],
                            stratified=reports['stratified-step-400'])
    decision = c.choose_candidate(selected_reports, protocol['config'], run.protocol_hash())
    assert decision == c.read(run.out / 'selection.json') == completion['selection']
    # This completed experiment failed selection. Never open calibration/final rows.
    assert not decision['passed'] and not completion['calibration_evaluated'] and not completion['final_evaluated']
    assert not (run.out / 'calibration').exists() and not (run.out / 'final').exists()
    training, initial = {}, []
    pool_rows = {r['id']: r for r in c.pool.verify()}
    ledger = c.read(c.schedule.OUT / 'exposure-ledger.json')['arms']
    for arm in c.ARMS:
        context = c.ArmRun(run, arm)
        logs = c.ft.rows_file(context.out / 'train.jsonl')
        plan = c.read(c.schedule.OUT / f'{arm}-plan.json')
        assert [r['step'] for r in logs] == list(range(1, 401))
        assert [r['row_ids'] for r in logs] == plan['step_rows']
        assert all(math.isfinite(r['loss']) and math.isfinite(r['gradient_norm']) for r in logs)
        assert all(math.isclose(r['lr'], c.learning_rate(r['step'], protocol['config'])) for r in logs)
        summary = c.read(context.out / 'training-summary.json')
        assert summary['sampled_by_id'] == dict(Counter(rid for r in logs for rid in r['row_ids']))
        assert summary['sample_positions'] == 3200
        assert math.isclose(summary['training_elapsed_s'], sum(r['elapsed_s'] for r in logs))
        for checkpoint in context.checkpoints.glob('step-*'):
            c.ft.validate_checkpoint(context, checkpoint)
        initial.append(c.read(context.out / 'initialization.json')['initial_parameter_sha256'])
        training[arm] = dict(steps=len(logs), pure_train_minutes=summary['training_elapsed_s'] / 60,
            unique_rows=summary['unique_rows'], peak_allocated_gib=summary['peak_allocated_gib'],
            first200_mean_loss=statistics.mean(r['loss'] for r in logs[:200]),
            last200_mean_loss=statistics.mean(r['loss'] for r in logs[200:]),
            first50_mean_loss=statistics.mean(r['loss'] for r in logs[:50]),
            last50_mean_loss=statistics.mean(r['loss'] for r in logs[-50:]))
        training[arm]['action_exposures'] = dict(Counter(pool_rows[e['row_id']]['annotation']['action'] for e in ledger[arm]))
        training[arm]['action_exposures_by_layer'] = {
            layer: dict(Counter(pool_rows[e['row_id']]['annotation']['action']
                               for e in ledger[arm] if e['layer'] == layer))
            for layer in sorted({e['layer'] for e in ledger[arm]})}
    assert len(set(initial)) == 1
    probe = c.read(c.ROOT / 'results' / c.PROBE / 'probe-summary.json')
    assert initial[0] == probe['initial_parameter_sha256']
    assert protocol['common_binding_sha256'] == probe['common_binding_sha256']
    comparisons = {'stratified_vs_uniform_400': transitions(rows, predictions['uniform-step-400'], predictions['stratified-step-400'])}
    for arm in c.ARMS:
        comparisons[f'{arm}_200_to_400'] = transitions(rows, predictions[f'{arm}-step-200'], predictions[f'{arm}-step-400'])
    for cohort in sorted({r['cohort'] for r in rows}):
        cohort_rows = [r for r in rows if r['cohort'] == cohort]
        ids = {r['id'] for r in cohort_rows}
        comparisons[f'stratified_vs_uniform_400_{cohort}'] = transitions(cohort_rows,
            [p for p in predictions['uniform-step-400'] if p['id'] in ids],
            [p for p in predictions['stratified-step-400'] if p['id'] in ids])
    # Launch metadata stays local; export only timezone-aware timestamps and duration.
    launch = json.loads((c.ROOT / '.local/financial-sampling-main-launch.json').read_text(encoding='utf-8-sig'))
    start, end = datetime.fromisoformat(launch['started_at']), datetime.fromisoformat(status['updated_at'])
    result = dict(version='financial-sampling-audit-v1', status='verified', training_eligible=False,
        inference_requests=0, model_api_requests=0, calibration_or_final_rows_read=False,
        protocol_sha256=run.protocol_hash(), audit_script_sha256=c.sha(c.ROOT / 'scripts/audit-financial-sampling.py'),
        artifact_sha256={c.relative(f): c.sha(f) for f in sorted(run.out.rglob('*.json*'))},
        started_at=start.isoformat(), completed_at=end.isoformat(), wall_minutes=(end-start).total_seconds()/60,
        development=table, training=training, comparisons=comparisons, selection=decision,
        limitations=['128 synthetic development rows in32 story groups, previously inspected',
                     'One training seed, no new blind test, no backend end-to-end execution',
                     'Changing sampling changes cohort/group/repetition/tool exposure jointly',
                     'Sequential timings not interleaved; desktop load may differ'])
    out = c.ROOT / 'docs/evidence/financial-sampling-audit-v1'
    c.durable_json(out / 'summary.json', result)
    lookup = {v: {p['id']: p for p in predictions[v]} for v in variants}
    cases = []
    for row in rows:
        if any(lookup[v][row['id']]['action'] != row['annotation']['action']
               or (row['annotation']['action'] == 'tool' and lookup[v][row['id']]['tool_name'] != row['annotation']['tool_name'])
               for v in ('uniform-step-400', 'stratified-step-400')):
            cases.append(dict(row=row, predictions={v:{k:lookup[v][row['id']][k] for k in ('action','tool_name')} for v in variants}))
    c.durable_json(out / 'development-cases.json', dict(training_eligible=False,
        usage='Development diagnosis only; do not train on these cases or use them as synthetic templates.', cases=cases))
    print(json.dumps(dict(status=result['status'], wall_minutes=result['wall_minutes'],
        training=training, comparisons={k:{field:v[field] for field in ('counts','paired_group_bootstrap')}
                                       for k,v in comparisons.items()}), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
