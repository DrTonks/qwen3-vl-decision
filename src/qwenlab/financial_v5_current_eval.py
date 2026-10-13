"""Frozen V5 checkpoint on current development only. No training/vendor calls."""
from collections import Counter
from copy import deepcopy
import gc
import json
from pathlib import Path
import time

from qwenlab.common import ROOT, sha
from qwenlab import financial_2b_full_coverage_cycle as c

OUT = ROOT/'docs/evidence/financial-v5-current-development-v1'
DATA = ROOT/'data/financial-service-v2/development.json'
ADAPTER = ROOT/'.local/checkpoints/joint-v5/step-7110'
MAPPING = {'llm':'answer','tool':'tool','clarify':'clarify','human':'human'}


def project_native(row):
    """Preserve only fields accepted by the original authenticated-only service."""
    from qwenlab.serve import validate_input
    v = deepcopy(row['input'])
    if v['state']['authenticated'] is not True:
        return None
    value = {k:v[k] for k in ('message','history','state','available_tools')}
    value['state'] = {k:x for k,x in v['state'].items() if k in ('authenticated','application_id','status_code','pending')}
    return validate_input(value)


def native_summary(rows, predictions):
    by_id = {r['id']:r for r in rows}
    if len(predictions) != len({p['id'] for p in predictions}): raise ValueError('Duplicate native predictions')
    allowed = {r['id'] for r in rows if project_native(r) is not None}
    if set(p['id'] for p in predictions) != allowed: raise ValueError('Native input coverage mismatch')
    def block(ps):
        tools = [p for p in ps if by_id[p['id']]['annotation']['action']=='tool']
        humans = [p for p in ps if by_id[p['id']]['annotation']['action']=='human']
        return dict(rows=len(ps), action_correct=sum(p['action']==by_id[p['id']]['annotation']['action'] for p in ps),
                    tool_support=len(tools),tool_joint_correct=sum(p['action']=='tool' and p['tool_name']==by_id[p['id']]['annotation']['tool_name'] for p in tools),
                    human_support=len(humans),human_misses=sum(p['action']!='human' for p in humans))
    common = [p for p in predictions if by_id[p['id']]['annotation']['action'] in MAPPING.values()]
    unsupported = Counter(by_id[p['id']]['annotation']['action'] for p in predictions if by_id[p['id']]['annotation']['action'] not in MAPPING.values())
    return dict(all_accepted=block(predictions),common_four_actions=block(common),unexpressible_labels=dict(unsupported),
                rejected_input_rows=len(rows)-len(predictions),
                common_ids=[p['id'] for p in common],
                latency_scope='Original three-task service, external timer includes encoding and transfers; excludes loading/warmup/HTTP/backend.',
                request_p50_s=c.ft.metrics.percentile([p['elapsed_s'] for p in predictions],.5),
                request_p95_s=c.ft.metrics.percentile([p['elapsed_s'] for p in predictions],.95))


def source_bindings():
    files=[DATA,ADAPTER/'adapter_model.safetensors',ADAPTER/'adapter_config.json',
           ROOT/'results/joint-v5/selection.json',ROOT/'configs/support-financial-v2.json',
           ROOT/'configs/decision-v5.json',Path(__file__),ROOT/'tests/test_financial_v5_current_eval.py']
    files += [ROOT/'src/qwenlab'/n for n in ['financial_2b_model.py','financial_2b_prompt.py','financial_prompt_v2.py',
              'financial_2b_full_coverage_cycle.py','financial_train.py','financial_service_v2_metrics.py',
              'serve.py','joint_v5.py','modeling.py','candidate_inference.py']]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files}


def main():
    import torch
    from qwenlab.joint_v5 import exclusive_lock
    from qwenlab import financial_2b_model as qm
    from qwenlab.serve import QwenEngine
    with exclusive_lock('financial-eight-actions-gpu.lock'):
        rows=c.read(DATA)
        assert len(rows)==128 and all(r['split']=='development' for r in rows)
        assert c.read(ROOT/'results/joint-v5/selection.json')['selected']=='step-7110'
        old=c.read(ROOT/'results/financial-2b-full-coverage-v1/protocol.json')
        assert old['evaluation']['files']['development.json']==sha(DATA)
        protocol=dict(version='financial-v5-current-development-v1',sources=source_bindings(),
            checkpoint='joint-v5/step-7110',checkpoint_selected_by='historical V5 development, not this set',
            evaluation_scope='development only; 128 synthetic rows; no calibration/final inputs',
            modes=['current eight-action prompt transfer, no retraining','original V5 service, authenticated inputs only'],
            native_mapping=MAPPING,omitted_native_fields=['state.handoff_status','capabilities','capability_profile','service_scope','images(empty)'],
            native_rule='No capability or authentication invented; rejected preauth cases reported, not inferred.',
            current_loader='same NF4 prepared-base loader as new 2B; native uses original serve.QwenEngine',
            training_enabled=False,model_api_requests=0,deployable=False)
        c.immutable_json(OUT/'protocol.json',protocol)
        ph=sha(OUT/'protocol.json')
        if (OUT/'completion.json').exists():
            print('Completed: inspect existing result; no repeated inference.');return
        c.durable_json(OUT/'status.json',dict(stage='loading_current_prompt',updated_at=c.ft.now()))
        path=OUT/'transfer-predictions.jsonl';done=c.ft.rows_file(path) if path.exists() else []
        c.ft.evaluation_prefix(rows,done)
        if len(done)<len(rows):
            tok,model=qm.load(checkpoint=ADAPTER)
            try:
                with c.ft.inference_scorer(model) as scorer:
                    for task in ('action','tool'):c.task_prediction(tok,scorer,rows[0],task)
                    for row in rows[:10]:c.ft.predict_request(tok,scorer,row,c.task_prediction)
                    for row in rows[len(done):]:
                        p=c.ft.predict_request(tok,scorer,row,c.task_prediction)
                        p.update(projection=scorer.projection,projection_fallback=scorer.fallback_reason)
                        c.ft.append(path,p);done.append(p)
                        if len(done)%16==0:
                            print('current prompt',len(done),'/128',flush=True)
                            c.durable_json(OUT/'status.json',dict(stage='current_prompt',done=len(done),updated_at=c.ft.now()))
            finally:del model;gc.collect();torch.cuda.empty_cache()
        report=c.metrics.evaluate(rows,done,c.prompt.POLICY_HASH,ph)
        c.immutable_json(OUT/'transfer-metrics.json',report)
        c.immutable_json(OUT/'transfer-timing.json',dict(request_p50_s=c.ft.metrics.percentile([p['elapsed_s'] for p in done],.5),
            request_p95_s=c.ft.metrics.percentile([p['elapsed_s'] for p in done],.95),
            scope='action plus conditional tool; same current 2B loader and prompt, different measurement day from historical models'))
        path=OUT/'native-predictions.jsonl';native=c.ft.rows_file(path) if path.exists() else []
        eligible=[r for r in rows if project_native(r) is not None];c.ft.evaluation_prefix(eligible,native)
        if len(native)<len(eligible):
            c.durable_json(OUT/'status.json',dict(stage='loading_native',updated_at=c.ft.now()))
            engine=QwenEngine(ADAPTER,'candidate')
            try:
                for row in eligible[:10]:engine.predict(project_native(row))
                for row in eligible[len(native):]:
                    torch.cuda.synchronize();t=time.perf_counter();raw=engine.predict(project_native(row));torch.cuda.synchronize()
                    route=raw['predictions']['route']['choice']
                    p=dict(id=row['id'],action=MAPPING[route],tool_name=raw['predictions']['tool']['choice'] if route=='tool' else None,
                           raw=raw,elapsed_s=time.perf_counter()-t)
                    c.ft.append(path,p);native.append(p)
                    if len(native)%16==0:print('native',len(native),'/',len(eligible),flush=True)
            finally:del engine;gc.collect();torch.cuda.empty_cache()
        c.immutable_json(OUT/'native-summary.json',native_summary(rows,native))
        if source_bindings()!=protocol['sources']:raise ValueError('Bound inputs changed')
        c.immutable_json(OUT/'completion.json',dict(status='complete',protocol_sha256=ph,
            artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['status.json','completion.json']},
            completed_at=c.ft.now(),training_steps=0,model_api_requests=0))
        c.durable_json(OUT/'status.json',dict(stage='complete',updated_at=c.ft.now()))
        print('Complete',flush=True)


if __name__=='__main__':main()
