"""Offline evaluation of the frozen step-2801 candidate; no training or API calls."""
import argparse
from datetime import datetime, timezone
import gc
import json
import os
import time

from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab.support_curriculum import digest
from qwenlab import support_v8_observe as observation
from qwenlab import support_train_v8 as training
from qwenlab.joint_v4 import metrics
from qwenlab.joint_v5 import atomic_json, exclusive_lock, predict_one, read_resumable_rows
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows, write_rows
from qwenlab.calibrate_v2 import fit, apply
from qwenlab.summarize import percentile

OUT=ROOT/'results/support-v8-observe/final'
CACHE=ROOT/'results/support-v8/final'
SELECTED='step-2801'
VARIANTS={'base':None,'v5-reference':'.local/checkpoints/joint-v5/step-7110',
          'step-200':'.local/checkpoints/support-v8/step-200',
          SELECTED:'.local/checkpoints/support-v8-observe/step-2801'}


def state(stage, **values):
    atomic_json(OUT/'status.json',{'stage':stage,'updated_at':datetime.now(timezone.utc).isoformat(),
                                 'pid':os.getpid(),**values})


def validate_rows(done, source, complete=False):
    if complete and len(done)!=len(source): raise ValueError('Incomplete cached evaluation')
    if [(r['id'],r['labels']) for r in done]!=[(r['id'],r['labels']) for r in source[:len(done)]]:
        raise ValueError('Prediction population or labels changed')
    if any(r.get('error') for r in done): raise ValueError('Cached evaluation contains errors')


def latency(rows):
    seconds=[r['elapsed_s'] for r in rows]
    return {'requests':len(rows),'p50_s':percentile(seconds,.5),'p95_s':percentile(seconds,.95),
            'mean_s':sum(seconds)/len(seconds),'min_s':min(seconds),'max_s':max(seconds)}


def verify_cached_file(path, snapshot):
    # Snapshot was captured before the continuation started, not when reusing caches.
    name=str(path.relative_to(ROOT))
    if snapshot.get(name)!=sha(path):
        raise ValueError('Original cached file changed: '+name)


def prepare():
    cfg, _=observation.prepare()
    selection=load_json(observation.OUT/'selection.json')
    if selection['selected']!=SELECTED or not selection['choices'][SELECTED]['eligible']:
        raise ValueError('Frozen selected candidate changed')
    observation.verify_checkpoint(ROOT/VARIANTS[SELECTED],sha(observation.OUT/'protocol.json'))
    observation.verify_checkpoint(ROOT/VARIANTS['step-200'],sha(observation.PARENT/'protocol.json'))
    reference={n:load_json(observation.OUT/'v5-reference'/f'{n}-dev-metrics.json') for n in ('business','legacy','massive','crosswoz')}
    candidate={n:load_json(observation.OUT/SELECTED/f'{n}-dev-metrics.json') for n in reference}
    if not training.gate(reference,candidate,cfg)['continue_training']:
        raise ValueError('Candidate no longer passes original development gate')
    files=cfg['final_evaluation']['datasets']
    parent=load_json(CACHE/'protocol.json')
    if parent['training_protocol_sha256']!=sha(observation.PARENT/'protocol.json') or parent['selection_sha256']!=sha(observation.PARENT/'selection.json'):
        raise ValueError('Original final protocol chain changed')
    if load_json(observation.PARENT/'cycle-status.json')['stage']!='evaluation_complete':
        raise ValueError('Original final evaluation is incomplete')
    snapshot_path=ROOT/'.local/support-v8-observe-parent-snapshot.json'
    snapshot=load_json(snapshot_path)
    for path in [CACHE/'protocol.json',CACHE/'comparison.json']:
        verify_cached_file(path,snapshot)
    previous=load_json(CACHE/'comparison.json')
    if {n:sha(ROOT/p) for n,p in files.items()}!=parent['datasets']:
        raise ValueError('Comparison input datasets changed')
    for v,h in parent['adapter_hashes'].items():
        if sha(ROOT/VARIANTS[v]/'adapter_model.safetensors')!=h:
            raise ValueError('Cached baseline weights changed')
    datasets={n:read_rows(ROOT/p) for n,p in files.items()}
    cal=datasets['calibration']; count=min(32,len(cal))
    chosen=[cal[i*len(cal)//count] for i in range(count)]
    speed=chosen*3
    if [r['id'] for r in speed]!=parent['speed_ids']:
        raise ValueError('Speed input schedule changed')
    cached={}
    cached_files=[]
    for v in ['base','v5-reference','step-200']:
        cached[v]={}
        for name,source in datasets.items():
            path=CACHE/v/f'{name}.jsonl'
            verify_cached_file(path,snapshot)
            cached[v][name]=read_rows(path)
            validate_rows(cached[v][name],source,complete=True)
            if metrics(cached[v][name])!=previous['metrics'][v][name]:
                raise ValueError('Cached metrics disagree with original final comparison')
            cached_files.append(path)
    verify_cached_file(CACHE/'jev/responses.jsonl',snapshot)
    vendor=read_rows(CACHE/'jev/responses.jsonl')
    if any(r.get('error') for r in vendor): raise ValueError('Existing Jev responses contain errors')
    jev={k:[r for r in vendor if r['kind']==k] for k in ('challenge','speed')}
    validate_rows(jev['challenge'],datasets['challenge'],complete=True)
    validate_rows(jev['speed'],speed,complete=True)
    if metrics(jev['challenge'])!=previous['metrics']['jev']['challenge']:
        raise ValueError('Jev cached metrics changed')
    cached_files.append(CACHE/'jev/responses.jsonl')
    protocol={'candidate':SELECTED,'selection_sha256':sha(observation.OUT/'selection.json'),
        'observation_protocol_sha256':sha(observation.OUT/'protocol.json'),
        'datasets':parent['datasets'],'variants':VARIANTS,
        'adapter_hashes':{v:sha(ROOT/a/'adapter_model.safetensors') for v,a in VARIANTS.items() if a},
        'source_hashes':{name:digest(ROOT/name) for name in
            ['src/qwenlab/support_v8_observe_eval.py','src/qwenlab/calibrate_v2.py',
             'src/qwenlab/summarize.py','src/qwenlab/prepare_v2.py']},
        'pre_continuation_cache_snapshot_sha256':sha(snapshot_path),
        'cached_files':{p.relative_to(ROOT).as_posix():sha(p) for p in cached_files},
        'speed_ids':[r['id'] for r in speed],'speed_order':list(VARIANTS),'warmup':3,'batch':1,'precision':'nf4',
        'purpose':'post-selection existing-test regression; not new blind evaluation',
        'calibration':'fit positive temperatures on calibration only; never select thresholds from test',
        'jev_new_requests':0,'no_training':True,'no_test_selection':True,'no_deployment':True,
        'jev_versions':sorted({r['model'] for r in vendor}),
        'baseline_accuracy':'recomputed from hash-bound original V8 predictions',
        'local_speed':'remeasured all four variants in this run; serial order, three tasks, synchronized GPU, encode included',
        'jev_speed':'historical API duration including network; not concurrent with local measurement'}
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocol.json').exists() and load_json(OUT/'protocol.json')!=protocol:
        raise ValueError('Frozen evaluation protocol changed')
    if not (OUT/'protocol.json').exists(): atomic_json(OUT/'protocol.json',protocol)
    return datasets,speed,cached,jev


def evaluate(tok,model,rows,path,label):
    import torch
    done=read_resumable_rows(path)
    validate_rows(done,rows)
    start_run=time.perf_counter(); initial=len(done)
    for row in rows[len(done):]:
        torch.cuda.synchronize(); start=time.perf_counter()
        result=predict_one(tok,model,row)
        torch.cuda.synchronize(); result['elapsed_s']=time.perf_counter()-start
        append_json(path,result); done.append(result)
        if len(done)%10==0 or len(done)==len(rows):
            per=(time.perf_counter()-start_run)/(len(done)-initial)
            state('evaluating',dataset=label,done=len(done),total=len(rows),
                  remaining_dataset_minutes=round(per*(len(rows)-len(done))/60,1))
    return done


def run():
    datasets,speed,cached,jev=prepare()
    if (OUT/'status.json').exists() and load_json(OUT/'status.json')['stage']=='complete':
        print('Evaluation already complete; stored results preserved.'); return
    state('loading',candidate=SELECTED)
    timings={}; all_metrics={v:{n:metrics(rows) for n,rows in parts.items()} for v,parts in cached.items()}
    import torch
    append_json(OUT/'hardware-history.jsonl',{'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,
        'cuda':torch.version.cuda,'started_at':datetime.now(timezone.utc).isoformat()})
    for variant,adapter in VARIANTS.items():
        folder=OUT/variant; folder.mkdir(exist_ok=True)
        state('loading',variant=variant)
        tok,model=load_model('nf4',adapter); tok.padding_side='left'; model.eval()
        for row in speed[:3]: predict_one(tok,model,row)
        timed=evaluate(tok,model,speed,folder/'speed.jsonl',variant+'/speed')
        timings[variant]=latency(timed)
        if variant==SELECTED:
            predictions={name:evaluate(tok,model,rows,folder/f'{name}.jsonl',variant+'/'+name)
                         for name,rows in datasets.items()}
            all_metrics[variant]={name:metrics(rows) for name,rows in predictions.items()}
            temperatures={t:fit(predictions['calibration'],t) for t in ('intent','route','tool')}
            calibrated=apply(predictions['challenge'],temperatures)
            write_rows(folder/'challenge-calibrated.jsonl',calibrated)
            atomic_json(OUT/'calibration.json',{'temperatures':temperatures,'raw':all_metrics[variant]['challenge'],
                                               'calibrated':metrics(calibrated)})
        atomic_json(folder/'metrics.json',all_metrics[variant])
        del model,tok; gc.collect(); torch.cuda.empty_cache()
    all_metrics['jev']={'challenge':metrics(jev['challenge'])}
    timings['jev-historical']=latency(jev['speed'])
    atomic_json(OUT/'metrics.json',all_metrics)
    atomic_json(OUT/'speed.json',timings)
    current=all_metrics[SELECTED]; baseline=all_metrics['v5-reference']
    checks={
        'challenge_route_not_below_v5':current['challenge']['tasks']['route']['accuracy']>=baseline['challenge']['tasks']['route']['accuracy'],
        'challenge_route_within_3pp_jev':current['challenge']['tasks']['route']['accuracy']>=all_metrics['jev']['challenge']['tasks']['route']['accuracy']-.03,
        'challenge_human_misses_not_increased':current['challenge']['human_missed']<=baseline['challenge']['human_missed'],
        'legacy_human_misses_not_increased':current['legacy']['human_missed']<=baseline['legacy']['human_missed'],
        'p50_faster_than_historical_jev':timings[SELECTED]['p50_s']<timings['jev-historical']['p50_s'],
        'p95_within_20percent_historical_jev':timings[SELECTED]['p95_s']<=1.2*timings['jev-historical']['p95_s']}
    for name in ('legacy','massive','crosswoz'):
        for task,m in baseline[name]['tasks'].items():
            for metric in ('accuracy','macro_f1_gold_supported_classes'):
                checks[f'{name}.{task}.{metric}.preserved']=current[name]['tasks'][task][metric]>=m[metric]-.03
    atomic_json(OUT/'checks.json',checks)
    state('complete',candidate=SELECTED,failed_checks=[k for k,v in checks.items() if not v],
          report_pending=True,new_jev_requests=0,deployment_changed=False)


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['prepare','run','progress'])
    a=p.parse_args()
    if a.action=='progress':
        print(json.dumps(load_json(OUT/'status.json') if (OUT/'status.json').exists() else {'stage':'not_started'},ensure_ascii=False,indent=2))
    elif a.action=='prepare':
        prepare(); print('Candidate and existing caches verified; no GPU or API used.')
    else:
        with exclusive_lock('support-v8-observe-eval.lock'),exclusive_lock('joint-v5-gpu.lock'):
            try: run()
            except BaseException as exc:
                state('failed',error=type(exc).__name__,message=str(exc)); raise


if __name__=='__main__': main()
