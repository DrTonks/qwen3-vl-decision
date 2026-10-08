"""Read-only model/data audit, development predictions only; never trains."""
from collections import Counter,defaultdict
from datetime import datetime
import json,math,random,subprocess
from qwenlab.common import ROOT,sha
from qwenlab import financial_service_v2_cycle as c

OUT=ROOT/'docs/evidence/financial-service-v2-diagnosis-v1'
VARIANTS=['base','step-200','step-1470','step-2940']


def confidence(rows,predictions):
    by_id={r['id']:r for r in rows}; nll=brier=0.;bins=defaultdict(list);incorrect=[]
    for p in predictions:
        target=c.prompt.SPEC['actions'].index(by_id[p['id']]['annotation']['action'])
        logits=p['action_prediction']['logits'];mx=max(logits)
        nll+=mx+math.log(sum(math.exp(v-mx) for v in logits))-logits[target]
        probs=[p['action_prediction']['probabilities'][k] for k in c.prompt.SPEC['actions']]
        brier+=sum((v-int(i==target))**2 for i,v in enumerate(probs))
        conf=max(probs);correct=p['action']==by_id[p['id']]['annotation']['action']
        bins[min(9,int(conf*10))].append((conf,correct))
        if not correct:incorrect.append(conf)
    ece=sum(abs(sum(x for x,y in values)-sum(y for x,y in values))/len(rows) for values in bins.values())
    return dict(action_nll=nll/len(rows),multiclass_brier=brier/len(rows),ece_10_bins=ece,
                wrong_action_count=len(incorrect),wrong_confidence_mean=sum(incorrect)/len(incorrect) if incorrect else None,
                wrong_confidence_at_least_95=sum(x>=.95 for x in incorrect),
                usage='raw development diagnostic, not calibration or threshold selection; ECE unstable on small samples')


def paired(rows,first,second):
    lookup=[{p['id']:p for p in pred} for pred in [first,second]]
    changes=Counter();groups=defaultdict(list)
    for r in rows:
        a,b=[v[r['id']]['action']==r['annotation']['action'] for v in lookup]
        changes['both_correct' if a and b else 'regressed' if a else 'improved' if b else 'both_wrong']+=1
        groups[r['scene_family_id']].append(int(b)-int(a))
    rng=random.Random(20261003);keys=sorted(groups);deltas=[]
    for _ in range(10000):
        values=[v for _ in keys for v in groups[rng.choice(keys)]]
        deltas.append(sum(values)/len(values))
    discordant=changes['regressed']+changes['improved'];tail=min(changes['regressed'],changes['improved'])
    probability=min(1.,2*sum(math.comb(discordant,i) for i in range(tail+1))/2**discordant) if discordant else 1.
    return dict(counts=dict(changes),delta_accuracy=sum(sum(v) for v in groups.values())/len(rows),
                story_bootstrap_95=[c.ft.metrics.percentile(deltas,.025),c.ft.metrics.percentile(deltas,.975)],
                row_mcnemar_exact_two_sided_p=probability,
                limitation='McNemar treats rows as independent; story correlation and synthetic author bias remain; 3 regressions alone cannot prove overfitting')


def main():
    if OUT.exists():raise FileExistsError('Keep completed diagnostic evidence; use a new version')
    run=c.Run();c.verify_review();protocol=c.read(run.out/'protocol.json')
    for name,digest in protocol['source_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Execution source changed: '+name)
    train=c.data.validate_train()
    # Deliberately never call the evaluation loader for calibration/final.
    manifest=c.read(c.data.OUT/'evaluation-manifest.json')
    if sha(c.data.OUT/'development.json')!=manifest['files']['development.json']:raise ValueError('Development changed')
    rows=c.evaluation_rows('development');reports={};predictions={};bindings={}
    for variant in VARIANTS:
        folder=run.out/'development'/variant
        if c.read(folder/'binding.json')!=c.eval_binding(run,variant,'development'):raise ValueError('Prediction binding changed')
        pred=c.ft.rows_file(folder/'predictions.jsonl');report=c.metrics.evaluate(rows,pred,protocol['prompt_sha256'],run.protocol_hash())
        if report!=c.read(folder/'metrics.json'):raise ValueError('Metrics recomputation differs')
        predictions[variant]=pred;reports[variant]=report
        bindings[variant]={p.name:sha(p) for p in [folder/'predictions.jsonl',folder/'metrics.json',folder/'binding.json',folder/'timing.json']}
    selection,recomputed=c.select(run,protocol)
    if selection['passed']:raise ValueError('This diagnostic is scoped to the completed failed cycle')
    for name in ['calibration','final']:
        if (run.out/name).exists():raise ValueError('Unexpected holdout evaluation directory')
    logs=c.ft.rows_file(run.out/'train.jsonl');summary=c.read(run.out/'training-summary.json')
    if [r['step'] for r in logs]!=list(range(1,2941)):raise ValueError('Missing or duplicated update')
    if set(summary['sampled_by_id'])!={r['id'] for r in train} or set(summary['sampled_by_id'].values())!={2}:raise ValueError('Coverage mismatch')
    expected_tools=Counter(r['annotation']['tool_name'] for r in train if r['annotation']['action']=='tool')
    if summary['sampled_tools']!={k:2*v for k,v in expected_tools.items()}:raise ValueError('Tool task coverage mismatch')
    table=[]
    for variant in VARIANTS:
        m=reports[variant];pred=predictions[variant]
        table.append(dict(variant=variant,selection_candidate=variant in ['step-1470','step-2940'],
            accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],human_misses=len(m['human_misses']),false_refusals=len(m['false_refusals']),
            joint_tool_accuracy=m['action_tool_joint_accuracy'],preauth_tool_actions=len(m['unauthenticated_tool_actions']),
            cohorts={k:dict(rows=v['rows'],accuracy=v['action_accuracy'],human_misses=len(v['human_misses']),false_refusals=len(v['false_refusals']),joint_tool_accuracy=v['action_tool_joint_accuracy']) for k,v in m['cohorts'].items()},
            confidence=confidence(rows,pred),
            speed=dict(action_p50_ms=1000*c.ft.metrics.percentile([p['action_elapsed_s'] for p in pred],.5),
                       request_p50_ms=1000*m['latency']['p50_s'],request_p95_ms=1000*m['latency']['p95_s'],
                       predicted_tool_requests=sum(p['action']=='tool' for p in pred),
                       note='Serial staged timings; changed tool-call frequency affects request latency; no controlled repeated hardware comparison')))
    lookup={v:{p['id']:p for p in predictions[v]} for v in VARIANTS};cases=[]
    for row in rows:
        a=row['annotation'];p=lookup['step-1470'][row['id']];q=lookup['step-2940'][row['id']]
        ok=lambda x:x['action']==a['action'] and (a['action']!='tool' or x['tool_name']==a['tool_name'])
        if ok(p) and ok(q):continue
        cases.append(dict(id=row['id'],cohort=row['cohort'],scene_family_id=row['scene_family_id'],input=row['input'],annotation=a,
            first=dict(action=p['action'],tool=p['tool_name'],confidence=max(p['action_prediction']['probabilities'].values())),
            second=dict(action=q['action'],tool=q['tool_name'],confidence=max(q['action_prediction']['probabilities'].values())),
            transition='regressed' if ok(p) else 'improved' if ok(q) else 'both_wrong',
            split='development',training_eligible=False,usage='diagnostic_only_never_use_as_training_or_synthetic_training_templates'))
    epochs=[]
    for epoch in [1,2]:
        block=[r for r in logs if r['epoch']==epoch]
        weighted=lambda items:sum(r['loss']*(4 if r['step']%1470==0 else 8) for r in items)/sum(4 if r['step']%1470==0 else 8 for r in items)
        epochs.append(dict(epoch=epoch,training_minutes=sum(r['elapsed_s'] for r in block)/60,
            step_median_s=c.ft.metrics.percentile([r['elapsed_s'] for r in block],.5),step_p95_s=c.ft.metrics.percentile([r['elapsed_s'] for r in block],.95),
            slow_steps_over_10s=sum(r['elapsed_s']>10 for r in block),maximum_step_s=max(r['elapsed_s'] for r in block),
            mean_online_loss=weighted(block),first100_online_loss=weighted(block[:100]),last100_online_loss=weighted(block[-100:])))
    coverage={}
    for split,rs in [('train',train),('development',rows)]:
        coverage[split]=dict(cohorts=dict(Counter(r['cohort'] for r in rs)),tool_context={})
        for tool,key in [('queryApplicationDetail','application_id'),('explainApplicationStatus','status_code')]:
            block=[r for r in rs if r['annotation']['tool_name']==tool]
            coverage[split]['tool_context'][tool]=dict(rows=len(block),explicit_state=sum(key in r['input']['state'] for r in block))
    ground_script=ROOT/'scripts/inspect-financial-service-v2-grounding.cjs'
    grounding=json.loads(subprocess.check_output(['node',str(ground_script)],cwd=ROOT,encoding='utf-8'))
    backend_files=['financialContract.js','parameters.js','financialOrchestrator.js']
    backend_bindings={'../uestc_Integrated_Design/后端/services/customerSupport/'+n:sha(ROOT/'../uestc_Integrated_Design/后端/services/customerSupport'/n) for n in backend_files}
    status=c.read(run.out/'status.json')
    wall=(datetime.fromisoformat(status['updated_at']).timestamp()-status['process_created'])/60
    result=dict(status='verified_completed_failed_gate',protocol_sha256=run.protocol_hash(),prediction_bindings=bindings,
        source_files={str(p.relative_to(ROOT).as_posix()):sha(p) for p in [ROOT/'src/qwenlab/financial_service_v2_diagnosis.py',ground_script,c.data.OUT/'train.json',c.data.OUT/'development.json']},
        backend_source_files=backend_bindings,selection=selection,table=table,paired_first_second=paired(rows,predictions['step-1470'],predictions['step-2940']),
        training=dict(rows=11756,steps=2940,epochs=epochs,total_training_minutes=summary['training_elapsed_s']/60,wall_minutes=wall,each_row_exposures=2),
        data_coverage=coverage,development_error_union=len(cases),model_calls=0,api_calls=0,calibration_read=False,final_read=False,
        note='Offline diagnosis only. No gates/labels/data/checkpoints changed. Development cases may not be used for training.')
    OUT.mkdir(parents=True)
    for name,value in [('summary.json',result),('development-cases.json',cases),('node-grounding.json',grounding)]:c.durable_json(OUT/name,value)
    c.durable_json(OUT/'manifest.json',dict(files={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
    print(json.dumps(dict(paired=result['paired_first_second'],training=result['training'],table=table,coverage=coverage),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
