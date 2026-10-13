"""Recompute V5 current-development results, without model loading or API calls."""
import json
from qwenlab import financial_v5_current_eval as e


def main():
    c=e.c;rows=c.read(e.DATA);protocol=c.read(e.OUT/'protocol.json')
    completion=c.read(e.OUT/'completion.json')
    assert protocol['sources']==e.source_bindings()
    assert completion['protocol_sha256']==e.sha(e.OUT/'protocol.json')
    for name,digest in completion['artifacts'].items():assert e.sha(e.OUT/name)==digest
    preds=c.ft.rows_file(e.OUT/'transfer-predictions.jsonl');c.ft.evaluation_prefix(rows,preds)
    report=c.metrics.evaluate(rows,preds,c.prompt.POLICY_HASH,e.sha(e.OUT/'protocol.json'))
    assert report==c.read(e.OUT/'transfer-metrics.json')
    native=c.ft.rows_file(e.OUT/'native-predictions.jsonl');ns=e.native_summary(rows,native)
    assert ns==c.read(e.OUT/'native-summary.json')
    refs={
        'V5-new-prompt':preds,
        '2B-base':c.ft.rows_file(c.ROOT/'results/financial-2b-full-coverage-v1/development/base/predictions.jsonl'),
        '2B-epoch1':c.ft.rows_file(c.ROOT/'results/financial-2b-full-coverage-v1/development/full2b-step-1673/predictions.jsonl'),
        '2B-epoch2':c.ft.rows_file(c.ROOT/'results/financial-2b-full-coverage-v1/development/full2b-step-3346/predictions.jsonl'),
        '08B-epoch1':c.ft.rows_file(c.ROOT/'results/financial-full-coverage-v1/development/fullcover-step-1673/predictions.jsonl'),
        '08B-epoch2':c.ft.rows_file(c.ROOT/'results/financial-full-coverage-v1/development/fullcover-step-3346/predictions.jsonl')}
    summary={}
    common=set(ns['common_ids']);lookup={r['id']:r for r in rows}
    for name,values in refs.items():
        assert len(values)==128 and {p['id'] for p in values}==set(lookup)
        m=c.metrics.evaluate(rows,values)
        summary[name]=dict(correct=round(m['action_accuracy']*128),accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],
            tool_correct=round(m['action_tool_joint_accuracy']*m['tool_support']),tool_support=m['tool_support'],
            human_misses=len(m['human_misses']),false_refusals=len(m['false_refusals']),
            current_service_correct=round(m['cohorts']['current-service']['action_accuracy']*64),
            common_66_correct=sum(p['action']==lookup[p['id']]['annotation']['action'] for p in values if p['id'] in common),
            request_p50_s=c.ft.metrics.percentile([p['elapsed_s'] for p in values],.5))
    result=dict(status='verified',eight_action_comparison=summary,native=ns,
        model_api_requests=0,training_steps=0,final_or_calibration_read=False,
        warning='Shared development only. Current prompt transfer is not original V5 service performance; native lacks four actions and capability fields. Historical timing not controlled interleaved benchmark.')
    c.durable_json(e.OUT/'comparison-audit.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
