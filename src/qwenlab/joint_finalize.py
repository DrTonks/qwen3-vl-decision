"""Finish frozen v4 after GPU training, without new model selection on test."""
import argparse
import json
import shutil
import time
from qwenlab.common import ROOT, load_json, sha
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.joint_v4 import OUT, DATA, CKPT, dump, metrics, predict_rows
from qwenlab.modeling import load_model
from qwenlab.summarize import paired_ci, percentile, metric
from qwenlab.calibrate_v2 import fit, apply


def transfer():
    selected=load_json(OUT/'selection.json')['selected']
    for variant in dict.fromkeys(['base',selected]):
        tok,model=load_model('nf4',None if variant=='base' else (CKPT/variant).relative_to(ROOT).as_posix())
        tok.padding_side='left'; model.eval()
        for name,file in [('legacy-business','business-test.jsonl'),('crosswoz','crosswoz-test.jsonl')]:
            path=OUT/variant/f'{name}-test.jsonl'
            if path.exists(): continue
            rows=read_rows(ROOT/'data/processed/v2'/file)
            result=predict_rows(tok,model,rows)
            write_rows(path,result); dump(OUT/variant/f'{name}-test-metrics.json',metrics(result))
        del model,tok
        import gc,torch
        gc.collect(); torch.cuda.empty_cache()


def vendor_copy():
    target=OUT/'jev'; target.mkdir(exist_ok=True)
    sources={}
    for name,file in [('massive','massive-test.jsonl'),('legacy-business','business-test.jsonl'),('crosswoz','crosswoz-test.jsonl')]:
        source=ROOT/'results/runs/jev-v2'/file
        rows=read_rows(source)
        if any(r.get('model')!='jev-1.13.0' for r in rows if not r.get('error')):
            raise ValueError('Cached vendor version differs')
        shutil.copy2(source,target/f'{name}-test.jsonl')
        sources[name]={'source':source.relative_to(ROOT).as_posix(),'sha256':sha(source),'model':'jev-1.13.0',
            'reused':True,'note':'same original input, policy, questions, candidates; no extra API call'}
    dump(target/'reused-references.json',sources)


def summarize():
    selected=load_json(OUT/'selection.json')['selected']; summary={'selected':selected,'runs':{},'comparisons':{}}
    sets={}
    for variant in dict.fromkeys(['base',selected,'jev']):
        folder=OUT/variant
        for name in ('business','massive','legacy-business','crosswoz'):
            path=folder/f'{name}-test.jsonl'
            if not path.exists(): continue
            rows=read_rows(path); good=[r for r in rows if not r.get('error')]
            if not good: continue
            value=metrics(good); value.update(requests=len(rows),errors=len(rows)-len(good),source_sha256=sha(path))
            for task,v in value['tasks'].items(): v['accuracy_all_requests']=v['correct']/len(rows)
            if variant=='jev':
                value.update(latency_p50_s=percentile([r['elapsed_s'] for r in good],.5),latency_p95_s=percentile([r['elapsed_s'] for r in good],.95))
            key=variant+'/'+name; summary['runs'][key]=value; sets[key]=rows
    for name in ('business','massive','legacy-business','crosswoz'):
        left=selected+'/'+name; base='base/'+name; reference='jev/'+name
        if left not in sets: continue
        tasks=('intent','route') if 'business' in name else ('intent',)
        summary['comparisons'][name]={t:{'trained_minus_base':paired_ci(sets[left],sets[base],t),
            'trained_minus_jev':paired_ci(sets[left],sets[reference],t) if reference in sets else None} for t in tasks}
    calibration={}
    for variant in dict.fromkeys(['base',selected]):
        for name,tasks in [('massive',['intent']),('business',['intent','route'])]:
            cal=read_rows(OUT/variant/f'{name}-calibration.jsonl'); test=sets[variant+'/'+name]
            # Select only scored tasks; tool/human derivation must not be
            # mistaken for independently calibrated probabilities.
            cal=[{**r,'predictions':{t:r['predictions'][t] for t in tasks}} for r in cal]
            test=[{**r,'predictions':{t:r['predictions'][t] for t in tasks}} for r in test]
            fitted={t:fit(cal,t) for t in tasks}; calibrated=apply(test,fitted)
            write_rows(OUT/variant/f'{name}-test-calibrated.jsonl',calibrated)
            calibration[variant+'/'+name]={'temperatures':fitted,'metrics':{t:metric(calibrated,t) for t in tasks}}
    summary['calibration']=calibration
    summary['limitations']=['synthetic business labels not human-reviewed','only wording families held out; policy and author shared',
        'legacy and public benchmarks previously observed','one full pass, one seed; no causal data-size curve',
        'parameters, actual tool execution and screenshots not tested','positive temperature does not alter choices']
    dump(OUT/'metrics.json',summary)
    mistakes=[]
    raw={r['id']:r for r in read_rows(DATA/'business-test.jsonl')}
    for r in sets[selected+'/business']:
        wrong={k:{'gold':r['labels'][k],'predicted':r['predictions'][k]['choice']} for k in ('intent','route','tool') if r['labels'][k]!=r['predictions'][k]['choice']}
        if wrong: mistakes.append({'id':r['id'],'group':r['group'],'message':raw[r['id']]['message'],'state':raw[r['id']]['state'],'errors':wrong})
    dump(OUT/'business-mistakes.json',mistakes)
    lines=['# 第四轮机器汇总','','业务挑战为未人工复核的合成状态对照，不能当作产品准确率。','',
        '|模型 / 数据|意图准确率|路由准确率|工具准确率（含 none）|工具必要时联合正确|人工漏转|',
        '|---|---:|---:|---:|---:|---:|']
    for key,value in summary['runs'].items():
        def accuracy(t): return f"{value['tasks'][t]['accuracy_all_requests']:.2%}" if t in value['tasks'] else '—'
        joint=f"{value['joint_tool_correct']}/{value['tool_required']}" if 'tool_required' in value else '—'
        human=f"{value['human_missed']}/{value['human_required']}" if 'human_required' in value else '—'
        lines.append(f'|{key}|{accuracy("intent")}|{accuracy("route")}|{accuracy("tool")}|{joint}|{human}|')
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['transfer','references','report','all']); a=p.parse_args()
    if a.action in ('transfer','all'): transfer()
    if a.action in ('references','all'): vendor_copy()
    if a.action in ('report','all'): summarize()


if __name__=='__main__': main()
