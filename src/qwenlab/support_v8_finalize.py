"""Finish V8 once: failed-gate report or frozen held-out comparison. Never train."""
import gc
import json
import math
import os
import time
import urllib.request
from datetime import datetime, timezone

from qwenlab.common import ROOT, append_json, input_state, load_json, sha
from qwenlab.joint_v4 import metrics
from qwenlab.joint_v5 import atomic_json, exclusive_lock, predict_one, read_resumable_rows
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.calibrate_v2 import fit, apply
from qwenlab.summarize import percentile

OUT = ROOT/'results/support-v8'
FINAL = OUT/'final'


def state(stage, **kwargs):
    atomic_json(OUT/'cycle-status.json', {'stage':stage, 'updated_at':datetime.now(timezone.utc).isoformat(), **kwargs})


def evaluate_rows(tok, model, rows, path, label):
    import torch
    done = read_resumable_rows(path)
    if [(r['id'],r['labels']) for r in done] != [(r['id'],r['labels']) for r in rows[:len(done)]]:
        raise ValueError('Final evaluation prefix mismatch')
    for row in rows[len(done):]:
        torch.cuda.synchronize(); start=time.perf_counter()
        result=predict_one(tok,model,row)
        torch.cuda.synchronize()
        result['elapsed_s']=time.perf_counter()-start
        append_json(path,result); done.append(result)
        if len(done)%10==0: state('final_local_evaluation',dataset=label,done=len(done),total=len(rows))
    return done


def latency(rows):
    good=[r['elapsed_s'] for r in rows if not r.get('error')]
    return {'requests':len(rows),'errors':len(rows)-len(good),
            'p50_s':percentile(good,.5) if good else None,
            'p95_s':percentile(good,.95) if good else None}


def record_attempt(path, record):
    # Persist the attempt before sending; a crash can require manual inspection,
    # but must not silently repeat a potentially charged request.
    with path.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(record,ensure_ascii=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def verify_candidate(selected, cfg):
    from qwenlab.support_train_v8 import latest_checkpoint, gate
    latest_checkpoint()  # Check the saved protocol/file hashes, not present-day hashes alone.
    checkpoint=ROOT/'.local/checkpoints/support-v8'/selected
    metadata=load_json(checkpoint/'checkpoint.json')
    if selected!=f'step-{metadata["step"]}' or metadata['protocol_sha256']!=sha(OUT/'protocol.json'):
        raise ValueError('Selected checkpoint identity mismatch')
    for name,digest in metadata['files'].items():
        if sha(checkpoint/name)!=digest: raise ValueError('Selected checkpoint is corrupt')
    reference={n:load_json(OUT/'v5-reference'/f'{n}-dev-metrics.json') for n in ('business','legacy','massive','crosswoz')}
    current={n:load_json(OUT/selected/f'{n}-dev-metrics.json') for n in reference}
    if not gate(reference,current,cfg)['continue_training']:
        raise ValueError('Selected candidate does not pass the frozen gate')


def failed_report(selection):
    reference={name:load_json(OUT/'v5-reference'/f'{name}-dev-metrics.json') for name in ('business','legacy','massive','crosswoz')}
    steps=sorted(OUT.glob('gate-*.json'),key=lambda p:int(p.stem.split('-')[1]))
    values={'v5-reference':reference}
    for p in steps:
        values[p.stem.replace('gate','step')]={n:load_json(OUT/p.stem.replace('gate','step')/f'{n}-dev-metrics.json') for n in reference}
    atomic_json(FINAL/'development-comparison.json',values)
    last=steps[-1] if steps else None
    reasons=load_json(last)['reasons'] if last else ['no qualified checkpoint']
    lines=['# V8周期结果：未通过开发验收','',
           '本轮没有合格的新候选。建议项目继续以Jev为默认决策方案，V5保留为本地对照；未运行新的独立挑战、校准或Jev付费对照。',
           '','停止原因：'+ '；'.join(reasons),'',
           '|版本|新业务路由|旧业务路由|旧业务人工漏判|MASSIVE意图|CrossWOZ意图|','|---|---:|---:|---:|---:|---:|']
    for v,m in values.items():
        a=lambda n,t:m[n]['tasks'][t]['accuracy']
        lines.append(f'|{v}|{a("business","route"):.2%}|{a("legacy","route"):.2%}|{m["legacy"]["human_missed"]}|{a("massive","intent"):.2%}|{a("crosswoz","intent"):.2%}|')
    lines+=['','这些是开发集结果，不能当作独立上线准确率；短程失败不证明延长训练必然无效。没有自动启动V9或修改部署。']
    (FINAL/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    state('complete_no_candidate',selected=selection['selected'],recommendation='keep_jev_default',deployment_changed=False)


def vendor(rows, speed_rows, cfg):
    """Bounded API calls with an append-before-send journal; never retry uncertain calls."""
    folder=FINAL/'jev'; folder.mkdir(exist_ok=True)
    spec=load_json(ROOT/'configs/decision-v5.json')
    evaluation=[('challenge',r) for r in rows]+[('speed',r) for r in speed_rows]
    journal=folder/'attempts.jsonl'; result_file=folder/'responses.jsonl'
    attempts=read_resumable_rows(journal); done=read_resumable_rows(result_file)
    if len(attempts)!=len(done):
        raise ValueError('Uncertain vendor request requires inspection; no automatic paid retry')
    if len(evaluation)>cfg['final_evaluation']['jev_max_requests']:
        raise ValueError('Vendor request budget exceeded')
    for i,r in enumerate(done):
        if r['sequence']!=i or (r['kind'],r['id'])!=(evaluation[i][0],evaluation[i][1]['id']):
            raise ValueError('Vendor result schedule changed')
    if any(r.get('error') for r in done):
        raise ValueError('Previous vendor error needs inspection; no retries')
    key=(ROOT/'.local/secrets/jev-api-key.txt').read_text(encoding='utf-8-sig').strip()
    if not key or any(c.isspace() for c in key): raise ValueError('Invalid API credential format')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args): return None
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    resolved=next((r['model'] for r in done if r.get('model')),None)
    for i,(kind,row) in enumerate(evaluation[len(done):],start=len(done)):
        payload={'model':'jev-latest','state':{'policy':spec['policy'],'input':input_state(row)},
                 'questions':{t:{'type':'choice',**spec['questions'][t]} for t in ('intent','route','tool')}}
        record_attempt(journal,{'sequence':i,'kind':kind,'id':row['id'],'attempted_at':datetime.now(timezone.utc).isoformat()})
        result={'sequence':i,'kind':kind,'id':row['id'],'group':row['group'],'labels':row['labels'],'predictions':{}}
        start=time.perf_counter()
        try:
            request=urllib.request.Request('https://api.typesafe.ai/v1/systemone',
                data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            with op.open(request,timeout=30) as response: body=json.load(response)
            if not body.get('model'): raise ValueError('Missing resolved vendor version')
            if resolved and resolved!=body['model']: raise ValueError('Vendor model changed during evaluation')
            resolved=body['model']
            for task,q in payload['questions'].items():
                a=body['answers'][task]; probs=a['probabilities']
                if set(probs)!=set(q['criteria']) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in probs.values()) or abs(sum(probs.values())-1)>.03:
                    raise ValueError('Invalid vendor probability schema')
                if a['choice'] not in probs: raise ValueError('Invalid vendor choice')
                result['predictions'][task]={'choice':a['choice'],'probabilities':probs}
            result['raw_tool']=result['predictions']['tool'].copy()
            if result['predictions']['route']['choice']!='tool': result['predictions']['tool']={'choice':'none','derived':True}
            result.update(model=resolved,usage=body.get('usage'))
        except Exception as exc:
            result.update(error=type(exc).__name__,status=getattr(exc,'code',None))
        result['elapsed_s']=time.perf_counter()-start
        append_json(result_file,result); done.append(result)
        state('final_vendor_evaluation',done=len(done),total=len(evaluation))
        if result.get('error'): raise RuntimeError('Vendor stopped; inspect sanitized result error type/status')
    return {kind:[r for r in done if r['kind']==kind] for kind in ('challenge','speed')}


def run():
    from qwenlab.support_train_v8 import prepare
    cfg=prepare()
    selection=load_json(OUT/'selection.json')
    FINAL.mkdir(exist_ok=True)
    selected=selection['selected']
    if selected=='v5-reference':
        failed_report(selection)
        return
    if not selection['choices'][selected]['eligible']:
        raise ValueError('Cannot finalize an ineligible candidate')
    verify_candidate(selected,cfg)
    files=cfg['final_evaluation']['datasets']
    datasets={name:read_rows(ROOT/path) for name,path in files.items()}
    calibration=datasets['calibration']
    # Fixed evenly spaced calibration inputs, never selected from challenge errors.
    count=min(cfg['final_evaluation']['speed_case_count'],len(calibration))
    chosen=[calibration[i*len(calibration)//count] for i in range(count)]
    speed=[r for _ in range(cfg['final_evaluation']['speed_repeats']) for r in chosen]
    adapters={'base':None,'v5-reference':cfg['initial_adapter'],selected:f'.local/checkpoints/support-v8/{selected}'}
    protocol={'training_protocol_sha256':sha(OUT/'protocol.json'),'selection_sha256':sha(OUT/'selection.json'),
              'datasets':{k:sha(ROOT/v) for k,v in files.items()},'variants':adapters,
              'adapter_hashes':{v:sha(ROOT/a/'adapter_model.safetensors') for v,a in adapters.items() if a},
              'speed_ids':[r['id'] for r in speed],'warmup':3,'precision':'nf4','batch':1,
              'timing':'warm resident model; serial three-task decision including encode; GPU synchronize; Jev includes network',
              'no_test_selection':True,'no_automatic_deployment':True}
    path=FINAL/'protocol.json'
    if path.exists() and load_json(path)!=protocol: raise ValueError('Frozen final protocol changed')
    atomic_json(path,protocol)
    all_metrics={}; timings={}; calibrated={}
    import torch
    with exclusive_lock('joint-v5-gpu.lock'):
        for variant,adapter in adapters.items():
            folder=FINAL/variant; folder.mkdir(exist_ok=True)
            tok,model=load_model('nf4',adapter); tok.padding_side='left'; model.eval()
            for row in chosen[:3]: predict_one(tok,model,row)
            # Speed is measured before accuracy evaluation for every variant.
            speed_results=evaluate_rows(tok,model,speed,folder/'speed.jsonl',variant+'/speed')
            timings[variant]=latency(speed_results)
            predictions={}
            for name,rows in datasets.items():
                predictions[name]=evaluate_rows(tok,model,rows,folder/f'{name}.jsonl',variant+'/'+name)
            all_metrics[variant]={name:metrics(rows) for name,rows in predictions.items()}
            fits={task:fit(predictions['calibration'],task) for task in ('intent','route','tool')}
            out=apply(predictions['challenge'],fits)
            write_rows(folder/'challenge-calibrated.jsonl',out)
            calibrated[variant]={'temperatures':fits,'metrics':metrics(out)}
            atomic_json(folder/'metrics.json',all_metrics[variant])
            del model,tok; gc.collect(); torch.cuda.empty_cache()
    atomic_json(FINAL/'local-metrics.json',all_metrics)
    atomic_json(FINAL/'calibration.json',calibrated)
    atomic_json(FINAL/'local-speed.json',timings)
    jev=vendor(datasets['challenge'],speed,cfg)
    all_metrics['jev']={'challenge':metrics(jev['challenge'])}
    timings['jev']=latency(jev['speed'])
    candidate=all_metrics[selected]; baseline=all_metrics['v5-reference']
    checks={
        'challenge_route_not_below_v5':candidate['challenge']['tasks']['route']['accuracy']>=baseline['challenge']['tasks']['route']['accuracy'],
        'challenge_route_within_3pp_jev':candidate['challenge']['tasks']['route']['accuracy']>=all_metrics['jev']['challenge']['tasks']['route']['accuracy']-.03,
        'challenge_human_misses_not_increased':candidate['challenge']['human_missed']<=baseline['challenge']['human_missed'],
        'p50_faster_than_jev':timings[selected]['p50_s']<timings['jev']['p50_s'],
        'p95_within_20percent_jev':timings[selected]['p95_s']<=1.2*timings['jev']['p95_s']}
    for name in ('legacy','massive','crosswoz'):
        for task,metric in baseline[name]['tasks'].items():
            for measure in ('accuracy','macro_f1_gold_supported_classes'):
                checks[f'{name}.{task}.{measure}.preserved']=candidate[name]['tasks'][task][measure]>=metric[measure]-.03
    checks['legacy_human_misses_not_increased']=candidate['legacy']['human_missed']<=baseline['legacy']['human_missed']
    recommendation='qwen_candidate_pending_integration' if all(checks.values()) else 'keep_jev_default'
    atomic_json(FINAL/'comparison.json',{'metrics':all_metrics,'latency':timings,'checks':checks,'recommendation':recommendation})
    lines=['# V8独立对照结果','',f'选择：{selected}；结论：{recommendation}。没有自动部署。','',
           '|模型|业务挑战路由|人工漏判|同输入P50秒|P95秒|','|---|---:|---:|---:|---:|']
    for variant,m in all_metrics.items():
        lines.append(f'|{variant}|{m["challenge"]["tasks"]["route"]["accuracy"]:.2%}|{m["challenge"]["human_missed"]}|{timings[variant]["p50_s"]:.3f}|{timings[variant]["p95_s"]:.3f}|')
    lines+=['','失败项：'+str([k for k,v in checks.items() if not v]),'',
            '挑战与校准标签为未新增人审的合成留出；旧测试和公共测试过去已观察，不是全新盲测。校准只拟合正温度，不改变argmax，不依据测试改阈值。',
            'Jev延迟含网络，本地模型为常驻GPU；输入/政策/三任务相同，未计后端真实工具执行或回答生成。API原始usage见jev/responses.jsonl，不按未知费率推算账单。',
            '本结果是决策组件验证；后端权限、八动作映射与服务切换需要单独集成验收。']
    (FINAL/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    state('evaluation_complete',selected=selected,recommendation=recommendation,integration_review_pending=True)


def main():
    with exclusive_lock('support-v8-final.lock'):
        try: run()
        except BaseException as exc:
            state('finalization_failed',error=type(exc).__name__)
            raise


if __name__=='__main__': main()
