"""Offline audit of the completed full-coverage experiment; no inference or training."""
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import runpy
import statistics

from qwenlab import financial_full_coverage_cycle as c

helpers = runpy.run_path(str(Path(__file__).with_name('audit-financial-sampling.py')))


def main():
    run = c.Run()
    protocol = c.read(run.out / 'protocol.json')
    completion = c.read(run.out / 'completion.json')
    status = c.progress(run)
    assert status['stage'] == 'complete' and status['safe_to_shutdown'] and not status['worker_alive']
    assert completion['protocol_sha256'] == run.protocol_hash()
    assert protocol['common_binding']['source_sha256'] == c.source_bindings()
    assert protocol['common_binding']['review_sha256'] == c.sha(c.REVIEW)
    c.verify_review()
    c.schedule.verify()
    old_protocol = c.check_reference(protocol['common_binding'], protocol['evaluation'], protocol['config'])
    rows = c.evaluation_rows(run, protocol, 'development', 'base')
    reports, predictions, table, artifacts = {}, {}, {}, {}
    from qwenlab import financial_state_pair_cycle as statecycle
    variants = [('base', run, protocol,c)] + [(f'fullcover-step-{step}',run,protocol,c) for step in c.EVALUATION_STEPS]
    variants += [('preauth-step-400',c.parent_cycle.Run(),old_protocol,c.parent_cycle),
                 ('statepair-step-400',statecycle.Run(),c.read(statecycle.Run().out/'protocol.json'),statecycle)]
    for variant, owner, frozen, module in variants:
        folder = owner.out / 'development' / variant
        binding_fn = module.eval_binding
        assert c.read(folder / 'binding.json') == binding_fn(owner, frozen, variant, 'development')
        preds = c.ft.rows_file(folder / 'predictions.jsonl')
        c.ft.evaluation_prefix(rows, preds)
        assert len(preds) == len(rows) == 128
        report = c.metrics.evaluate(rows, preds, frozen['prompt_sha256'], owner.protocol_hash())
        assert report == c.read(folder / 'metrics.json')
        reports[variant], predictions[variant] = report, preds
        timing = c.read(folder / 'timing.json')
        for key, value in {
            'action_p50_s': c.ft.metrics.percentile([p['action_elapsed_s'] for p in preds], .5),
            'request_p50_s': c.ft.metrics.percentile([p['elapsed_s'] for p in preds], .5),
            'request_p95_s': c.ft.metrics.percentile([p['elapsed_s'] for p in preds], .95),
            'total_measured_s': sum(p['elapsed_s'] for p in preds),
        }.items(): assert math.isclose(timing[key], value, abs_tol=1e-12)
        table[variant] = dict(correct=round(report['action_accuracy']*len(rows)), rows=len(rows),
            action_accuracy=report['action_accuracy'], macro_f1=report['macro_f1'], per_action=report['per_action'],
            tool_correct=round(report['action_tool_joint_accuracy']*report['tool_support']), tool_support=report['tool_support'],
            failures={k:len(report[k]) for k in ('human_misses','false_refusals','unauthenticated_tool_actions',
                                               'unavailable_knowledge_retrievals','unavailable_tool_choices')},
            cohorts={k:dict(correct=round(v['action_accuracy']*v['rows']), rows=v['rows'],
                human_misses=len(v['human_misses']), false_refusals=len(v['false_refusals'])) for k,v in report['cohorts'].items()},
            probability=helpers['probability_diagnostics'](rows,preds), timing=timing)
        artifacts.update({c.relative(p):c.sha(p) for p in folder.iterdir() if p.is_file()})
    decision = c.choose_candidate({k:v for k,v in reports.items() if k=='base' or k.startswith('fullcover-step-')},protocol['config'],run.protocol_hash())
    assert decision == c.read(run.out/'selection.json') == completion['selection']
    assert decision['passed'] is False and completion['calibration_evaluated'] is False and completion['final_evaluated'] is False
    assert not (run.out/'calibration').exists() and not (run.out/'final').exists()
    context = c.ArmRun(run,'fullcover')
    logs = c.ft.rows_file(context.out/'train.jsonl')
    plan = c.read(c.schedule.OUT/'plan.json')
    assert [r['step'] for r in logs] == list(range(1,3347))
    assert [r['row_ids'] for r in logs] == plan['step_rows']
    assert all(math.isfinite(r['loss']) and math.isfinite(r['gradient_norm']) for r in logs)
    assert all(math.isclose(r['lr'],c.learning_rate(r['step'],protocol['config'])) for r in logs)
    summary = c.read(context.out/'training-summary.json')
    assert summary['sampled_by_id'] == dict(Counter(rid for r in logs for rid in r['row_ids']))
    assert summary['sample_positions'] == 26756
    assert math.isclose(summary['training_elapsed_s'],sum(r['elapsed_s'] for r in logs))
    for checkpoint in context.checkpoints.glob('step-*'): c.ft.validate_checkpoint(context,checkpoint)
    initial = c.read(context.out/'initialization.json')['initial_parameter_sha256']
    assert initial == c.read(c.REFERENCE/'arms/preauth/initialization.json')['initial_parameter_sha256']
    probe = c.read(c.Run(c.PROBE).out/'probe-summary.json')
    assert initial == probe['initial_parameter_sha256']
    assert protocol['common_binding_sha256'] == probe['common_binding_sha256']
    assert all(n == 2 for n in summary['sampled_by_id'].values()) and len(summary['sampled_by_id']) == 13378
    assert Counter(x for r in logs[:1673] for x in r['row_ids']) == Counter({k:1 for k in summary['sampled_by_id']})
    assert not (context.out/'early-stop.json').exists() and not c.persistent_deterioration(run,protocol)
    training = dict(steps=len(logs), pure_train_minutes=summary['training_elapsed_s']/60,
        peak_allocated_gib=summary['peak_allocated_gib'], unique_rows=summary['unique_rows'],
        first200_mean_loss=statistics.mean(r['loss'] for r in logs[:200]),
        last200_mean_loss=statistics.mean(r['loss'] for r in logs[-200:]),
        first50_mean_loss=statistics.mean(r['loss'] for r in logs[:50]),last50_mean_loss=statistics.mean(r['loss'] for r in logs[-50:]))
    training.update(epoch1_mean_loss=statistics.mean(r['loss'] for r in logs[:1673]),epoch2_mean_loss=statistics.mean(r['loss'] for r in logs[1673:]),sample_positions=26756,every_row_exposure=2)
    comparisons = {name:helpers['transitions'](rows,predictions[left],predictions[right]) for name,left,right in
        [('preauth400_to_epoch1','preauth-step-400','fullcover-step-1673'),('state400_to_epoch1','statepair-step-400','fullcover-step-1673'),('epoch1_to_epoch2','fullcover-step-1673','fullcover-step-3346'),('step3000_to_epoch2','fullcover-step-3000','fullcover-step-3346')]}
    launch = json.loads((c.ROOT/'.local/financial-full-coverage-main-launch.json').read_text(encoding='utf-8-sig'))
    start,end = datetime.fromisoformat(launch['started_at']),datetime.fromisoformat(status['updated_at'])
    artifacts.update({c.relative(p):c.sha(p) for p in run.out.rglob('*.json*')})
    result = dict(version='financial-full-coverage-results-audit-v1',status='verified',training_eligible=False,
        protocol_sha256=run.protocol_hash(),audit_script_sha256=c.sha(Path(__file__)),
        audit_helper_sha256=c.sha(Path(__file__).with_name('audit-financial-sampling.py')),
        artifact_sha256=artifacts,started_at=start.isoformat(),completed_at=end.isoformat(),wall_minutes=(end-start).total_seconds()/60,
        training=training,development=table,comparisons=comparisons,selection=decision,
        inference_requests=0,model_api_requests=0,calibration_or_final_rows_read=False,
        limitations=['Repeatedly inspected synthetic development128/32 story groups; not blind.',
                     'One seed, historical sequential timing, no backend execution or generalization proof.'])
    out = c.ROOT/'docs/evidence/financial-full-coverage-results-audit-v1'
    c.durable_json(out/'summary.json',result)
    lookup = {k:{p['id']:p for p in v} for k,v in predictions.items()}
    cases = []
    for row in rows:
        r = lookup['fullcover-step-3346'][row['id']]
        if r['action']!=row['annotation']['action'] or (row['annotation']['action']=='tool' and r['tool_name']!=row['annotation']['tool_name']):
            cases.append(dict(row=row,predictions={k:{f:v[row['id']][f] for f in ('action','tool_name')} for k,v in lookup.items()}))
    c.durable_json(out/'development-cases.json',dict(training_eligible=False,
        usage='Development diagnosis only; do not train on these examples or use them as synthetic generation templates.',cases=cases))
    print(json.dumps({k:result[k] for k in ('status','wall_minutes','training','comparisons')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
