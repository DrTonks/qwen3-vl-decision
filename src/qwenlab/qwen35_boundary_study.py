"""Fixed-budget replay/overlay study; one global selection, no vendor requests.

The older Qwen3.5 protocol is imported, never patched. Every arm starts from
the same adapter with a fresh optimizer; a resume restores that arm's optimizer.
"""
import argparse
from collections import Counter
import gc
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import time

from qwenlab.common import ROOT, sha
from qwenlab import financial_train as ft, qwen35_cycle as cycle, qwen35_model as qm

DEFAULT = 'financial-qwen35-boundary-v1'
CONFIG = ROOT/'configs/financial-qwen35-boundary-v1.json'
ARMS = ('replay', 'overlay')
CODE_REVIEW = ROOT/'docs/evidence/qwen35-boundary-code-review.json'
REVIEW_FILES = [
    'src/qwenlab/qwen35_boundary_study.py', 'src/qwenlab/financial_boundary_release.py',
    'scripts/start-qwen35-boundary.ps1', 'scripts/pause-qwen35-boundary.ps1',
    'scripts/resume-qwen35-boundary.ps1', 'tests/test_qwen35_boundary_study.py',
    'tests/test_financial_boundary_release.py', 'configs/financial-qwen35-boundary-v1.json']
SOURCES = list(dict.fromkeys(cycle.SOURCES + [
    'src/qwenlab/qwen35_boundary_study.py', 'src/qwenlab/financial_boundary_release.py',
    'scripts/start-qwen35-boundary.ps1', 'scripts/pause-qwen35-boundary.ps1',
    'scripts/resume-qwen35-boundary.ps1']))


class Study(cycle.Run):
    def __init__(self):
        super().__init__(DEFAULT)


class Arm(cycle.Run):
    def __init__(self, study, label):
        if label not in ARMS:
            raise ValueError('Unknown study arm')
        super().__init__(study.name+'-'+label)
        self.study, self.label, self.control = study, label, study.control

    def status(self, stage, **values):
        super().status(stage, **values)
        self.study.status(stage, arm=self.label, **values)


def immutable_json(path, value):
    if path.exists() and ft.read(path) != json.loads(json.dumps(value)):
        raise ValueError('Frozen artifact differs: '+str(path))
    if not path.exists():
        ft.durable_json(path, value)


def schedule(count, total, seed):
    """Deterministic full shuffled passes plus a shuffled tail, never lost rows."""
    if count <= 0 or total < count:
        raise ValueError('Budget must cover every input row')
    order = []
    epoch = 0
    while len(order) < total:
        order.extend(cycle.epoch_order(count, seed, epoch))
        epoch += 1
    return order[:total]


def validate_config(cfg, accepted, original):
    total = original+accepted
    if (cfg['original_rows'], cfg['added_rows'], cfg['train_rows']) != (original, accepted, total):
        raise ValueError('Release and declared row budget differ')
    if accepted <= 0 or cfg['effective_batch'] != 8 or cfg['micro_batch'] != 2:
        raise ValueError('Expected reviewed nonempty overlay and fixed batches')
    steps = math.ceil(total/8)
    if cfg['max_steps'] != steps or cfg['checkpoint_steps'] != [384, 768, steps] or steps <= 768:
        raise ValueError('Fixed development/checkpoint budget differs')
    if cfg['learning_rate'] != 1e-5 or cfg['warmup_steps'] != 50 or cfg['save_every_steps'] != 100:
        raise ValueError('Fixed optimizer budget differs')
    old = ft.read(cycle.CONFIG)
    if cfg['development_gate'] != old['development_gate'] or cfg['calibration'] != old['calibration']:
        raise ValueError('Original gate and calibration must remain unchanged')
    if cfg['model_api_requests'] != 0 or cfg['initial_run'] != cycle.DEFAULT or cfg['initial_step'] != 2976:
        raise ValueError('Unexpected initialization or API budget')


def validate_code_review():
    review = ft.read(CODE_REVIEW)
    if review.get('status') != 'pass' or not set(REVIEW_FILES).issubset(review.get('files',{})):
        raise ValueError('Independent executor review has not passed')
    for name, digest in review['files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Reviewed executor file changed: '+name)
    return review


def freeze(study, resume):
    from qwenlab import financial_boundary_release as release
    validate_code_review()
    manifest = release.validate()
    if manifest.get('training_eligible') is not True:
        raise ValueError('Independent reviewed release required')
    ft.data.validate()
    original = ft.training_records()
    cfg = ft.read(CONFIG)
    validate_config(cfg, manifest['accepted_rows'], len(original))
    parent = cycle.Run(cfg['initial_run'])
    parent_protocol = ft.read(parent.out/'protocol.json')
    for name, digest in parent_protocol['source_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Frozen parent source changed: '+name)
    if parent_protocol['config'] != ft.read(cycle.CONFIG):
        raise ValueError('Frozen parent configuration changed')
    initial = parent.checkpoints/f"step-{cfg['initial_step']}"
    ft.validate_checkpoint(parent, initial)
    source = ft.read(ROOT/'configs/qwen35-model-source.json')
    for f in source['files']:
        if sha(qm.MODEL/f['Path']) != f['Sha256']:
            raise ValueError('Model checksum mismatch')
    baseline = parent.out/'development/base'
    if ft.read(baseline/'binding.json') != cycle.eval_binding(parent, 'base', 'development'):
        raise ValueError('Parent RAW base binding differs')
    m = ft.metrics.evaluate(ft.data.evaluation_rows('development'), ft.rows_file(baseline/'predictions.jsonl'),
                            parent_protocol['prompt_sha256'], parent.protocol_hash())
    if m != ft.read(baseline/'metrics.json'):
        raise ValueError('Parent RAW baseline metrics differ')
    initial_folder=parent.out/'development'/initial.name
    if ft.read(initial_folder/'binding.json') != cycle.eval_binding(parent,initial.name,'development'):
        raise ValueError('Initial adapter development binding differs')
    initial_metrics=ft.metrics.evaluate(ft.data.evaluation_rows('development'),ft.rows_file(initial_folder/'predictions.jsonl'),
                                      parent_protocol['prompt_sha256'],parent.protocol_hash())
    if initial_metrics != ft.read(initial_folder/'metrics.json'):
        raise ValueError('Initial adapter metrics differ')
    protocol = dict(config=cfg, run_name=study.name, model_api_requests=0,
        code_review_sha256=sha(CODE_REVIEW),
        release_manifest_sha256=sha(release.OUT/'manifest.json'),
        release_training_sha256=sha(release.OUT/'training.json'),
        dataset_manifest_sha256=sha(ft.data.OUT/'manifest.json'),
        parent_dataset_manifest_sha256=sha(ft.data.BASE/'manifest.json'),
        initial_protocol_sha256=parent.protocol_hash(), initial_checkpoint_sha256=sha(initial/'checkpoint.json'),
        source_sha256={name:sha(ROOT/name) for name in SOURCES},
        model_source_sha256=sha(ROOT/'configs/qwen35-model-source.json'),
        packages={name:importlib.metadata.version(name) for name in ft.PACKAGES+['tokenizers','huggingface-hub','safetensors']},
        prompt_sha256=sha(ROOT/'src/qwenlab/qwen35_model.py'),
        raw_baseline_files={name:sha(baseline/name) for name in ['binding.json','predictions.jsonl','metrics.json','timing.json']},
        initial_development_files={name:sha(initial_folder/name) for name in ['binding.json','predictions.jsonl','metrics.json','timing.json']},
        order=list(ARMS), selection='after BOTH arms: passing macroF1, joint tool, lower step, replay tie; one holdout winner',
        optimizer='fresh AdamW per arm; same seed, LR and exact sample positions; no initial optimizer transfer')
    path = study.out/'protocol.json'
    if path.exists() and not resume:
        raise FileExistsError('Explicit resume required')
    if not path.exists() and resume:
        raise FileNotFoundError('No study to resume')
    immutable_json(path, protocol)
    for label in ARMS:
        arm = Arm(study, label)
        immutable_json(arm.out/'protocol.json', dict(protocol, arm=label, study_protocol_sha256=study.protocol_hash()))
    return protocol


def records(label):
    from qwenlab import financial_boundary_release as release
    rows = ft.training_records()
    if label == 'overlay':
        for r in ft.read(release.OUT/'training.json'):
            if r['split'] != 'train':
                raise ValueError('Nontraining release row')
            rows.append(dict(id=r['id'], group=r.get('scene_family_id',r.get('group')), input=r['input'],
                             action=r['annotation']['action'], tool_name=r['annotation']['tool_name']))
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate training IDs')
    return rows


def seed_all(seed):
    import torch
    import numpy as np
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    random.seed(seed); np.random.seed(seed)


def train(arm, protocol):
    import torch
    from qwenlab.joint_v5 import rng_state, restore_rng
    cfg = protocol['config']
    rows = records(arm.label)
    order = schedule(len(rows), cfg['train_rows'], cfg['seed'])
    seed_all(cfg['seed'])
    saved = ft.latest_checkpoint(arm)
    initial = cycle.Run(cfg['initial_run']).checkpoints/f"step-{cfg['initial_step']}"
    tok, model = qm.load(training=True, checkpoint=saved or initial)
    immutable_json(arm.out/'candidate-parameter-dtypes.json', ft.dtype_summary(model))
    encoded = cycle.encode_training(arm, tok, rows)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=.01)
    summary = dict(step=0, sampled_by_id={}, sampled_tools={}, training_elapsed_s=0., sample_positions=0,
                   trainable_parameters=sum(p.numel() for p in params), dataset_rows=len(rows))
    if saved:
        state = torch.load(saved/'training-state.pt',map_location='cpu',weights_only=False)
        if state['protocol_sha256'] != arm.protocol_hash():
            raise ValueError('Training state binding differs')
        summary = state['summary']; optimizer.load_state_dict(state['optimizer']); restore_rng(state['rng'])
        logs = ft.rows_file(arm.out/'train.jsonl')
        if any(r['step']>summary['step'] for r in logs):
            ft.durable_json(arm.out/f'uncheckpointed-{time.time_ns()}.json',logs)
            (arm.out/'train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in logs if r['step']<=summary['step']),encoding='utf-8')
    elif (arm.out/'train.jsonl').exists():
        raise ValueError('Uncheckpointed log; refuse silent reset')
    else:
        ft.preflight(arm,tok,model,encoded,dict(pilot=dict(micro_batch=cfg['micro_batch'],
            gradient_accumulation=cfg['effective_batch']/cfg['micro_batch'],action_loss_weight=1.,tool_loss_weight=.75)))
    logs = ft.rows_file(arm.out/'train.jsonl')
    if [r['step'] for r in logs] != list(range(1,summary['step']+1)):
        raise ValueError('Missing or duplicated committed steps')
    if summary['step'] in cfg['checkpoint_steps']:
        state=rng_state(); cycle.evaluate(arm,tok,model,f"step-{summary['step']}",protocol); restore_rng(state)
    counts, tools = Counter(summary['sampled_by_id']), Counter(summary['sampled_tools'])
    torch.cuda.reset_peak_memory_stats()
    b=cfg['effective_batch']
    for step in range(summary['step']+1,cfg['max_steps']+1):
        cycle.pause_check(arm,'training',model,optimizer,step-1,summary)
        indices=order[(step-1)*b:step*b]
        arm.status('training',step=step-1,total_steps=cfg['max_steps'])
        model.train(); optimizer.zero_grad(set_to_none=True)
        rate=cfg['learning_rate']*min(step/cfg['warmup_steps'],(cfg['max_steps']-step+1)/(cfg['max_steps']-cfg['warmup_steps']))
        for group in optimizer.param_groups: group['lr']=rate
        torch.cuda.synchronize(); start=time.perf_counter(); loss=0.; tool_count=0
        for pos in range(0,len(indices),cfg['micro_batch']):
            chosen=indices[pos:pos+cfg['micro_batch']]
            micro=dict(pilot=dict(action_loss_weight=1.,tool_loss_weight=.75,gradient_accumulation=len(indices)/len(chosen)))
            a,t,c=ft.micro_backward(tok,model,[encoded[i] for i in chosen],micro)
            loss+=(a+.75*t)*len(chosen)/len(indices); tool_count+=c
        norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm): raise FloatingPointError('Nonfinite gradient')
        optimizer.step(); optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize(); elapsed=time.perf_counter()-start
        for i in indices:
            counts[rows[i]['id']]+=1
            if rows[i]['action']=='tool': tools[rows[i]['tool_name']]+=1
        summary.update(step=step,sampled_by_id=dict(counts),sampled_tools=dict(tools),sample_positions=sum(counts.values()),
            unique_rows=len(counts),training_elapsed_s=summary['training_elapsed_s']+elapsed,
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30)
        ft.append(arm.out/'train.jsonl',dict(step=step,loss=loss,lr=rate,true_tools=tool_count,elapsed_s=elapsed,
                  gradient_norm=float(norm),sample_positions=summary['sample_positions'],unique_rows=len(counts)))
        ft.durable_json(arm.out/'training-summary.json',summary)
        if step%25==0: print(json.dumps(dict(arm=arm.label,step=step,total=cfg['max_steps'],loss=loss)),flush=True)
        if step in cfg['checkpoint_steps'] or step%cfg['save_every_steps']==0 or ft.pause_requested(arm):
            arm.status('saving',step=step); cycle.checkpoint(arm,model,optimizer,step,summary)
        cycle.pause_check(arm,'training',model,optimizer,step,summary)
        if step in cfg['checkpoint_steps']:
            state=rng_state(); cycle.evaluate(arm,tok,model,f'step-{step}',protocol); restore_rng(state)
    expected=Counter(rows[i]['id'] for i in order)
    if counts != expected or sum(counts.values()) != cfg['train_rows']:
        raise ValueError('Exact budget/full coverage failed')
    immutable_json(arm.out/'arm-completion.json',dict(protocol_sha256=arm.protocol_hash(),steps=cfg['max_steps'],
        sample_positions=sum(counts.values()),unique_rows=len(counts),status='training_and_development_complete'))
    del model,optimizer; gc.collect(); torch.cuda.empty_cache()


def select(study, protocol):
    cfg=protocol['config']; parent=cycle.Run(cfg['initial_run'])
    for label in ARMS:
        arm=Arm(study,label)
        complete=ft.read(arm.out/'arm-completion.json')
        if complete['protocol_sha256']!=arm.protocol_hash() or complete['steps']!=cfg['max_steps']:
            raise ValueError('BOTH complete arms required before selection')
    rows=ft.data.evaluation_rows('development')
    base=ft.metrics.evaluate(rows,ft.rows_file(parent.out/'development/base/predictions.jsonl'),
                             protocol['prompt_sha256'],study.protocol_hash())
    initial=ft.metrics.evaluate(rows,ft.rows_file(parent.out/f"development/step-{cfg['initial_step']}/predictions.jsonl"),
                               protocol['prompt_sha256'],study.protocol_hash())
    reports={'raw_base':base,'initial_step2976':initial}; gates={}; passing=[]
    for label in ARMS:
        arm=Arm(study,label)
        for step in cfg['checkpoint_steps']:
            variant=f'step-{step}'; folder=arm.out/'development'/variant
            if ft.read(folder/'binding.json')!=cycle.eval_binding(arm,variant,'development'):
                raise ValueError('Development/checkpoint binding mismatch')
            m=ft.metrics.evaluate(rows,ft.rows_file(folder/'predictions.jsonl'),protocol['prompt_sha256'],arm.protocol_hash())
            if m != ft.read(folder/'metrics.json'): raise ValueError('Development metrics mismatch')
            key=f'{label}/{variant}'; reports[key]=m
            gates[key]=ft.metrics.development_gate(base,m,cfg['development_gate'])
            if gates[key]['passed']: passing.append((label,step,key))
    winner=max(passing,key=lambda x:(reports[x[2]]['macro_f1'],reports[x[2]]['action_tool_joint_accuracy'],-x[1],-ARMS.index(x[0]))) if passing else None
    decision=dict(passed=winner is not None,selected=winner[2] if winner else None,
        arm=winner[0] if winner else None,variant=f'step-{winner[1]}' if winner else None,
        protocol_sha256=study.protocol_hash(),gates=gates,usage='global_fixed_development_selection')
    immutable_json(study.out/'selection.json',decision)
    return decision,reports


def run_holdout(study, decision):
    # Global selection is already durable. Only this arm gets permission to read holdout.
    if not decision['passed'] or ft.read(study.out/'selection.json')!=decision:
        raise ValueError('No immutable global winner')
    arm=Arm(study,decision['arm'])
    selected=dict(passed=True,selected=decision['variant'],protocol_sha256=arm.protocol_hash(),
                  global_selection_sha256=sha(study.out/'selection.json'))
    immutable_json(arm.out/'selection.json',selected)
    cycle.pause_check(study,'before_holdout')
    cycle.holdout(arm,ft.read(arm.out/'protocol.json'),selected)


def report(study, decision, reports):
    cfg=ft.read(study.out/'protocol.json')['config']
    parent=cycle.Run(cfg['initial_run'])
    table=[]
    for variant,m in reports.items():
        if variant=='raw_base': timing=ft.read(parent.out/'development/base/timing.json')
        elif variant=='initial_step2976': timing=ft.read(parent.out/'development/step-2976/timing.json')
        else:
            label,checkpoint=variant.split('/')
            timing=ft.read(Arm(study,label).out/'development'/checkpoint/'timing.json')
        table.append(dict(variant=variant,accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],
            joint=m['action_tool_joint_accuracy'],human_misses=len(m['human_misses']),false_refusals=len(m['false_refusals']),
            request_p50_ms=timing['request_p50_s']*1000,request_p95_ms=timing['request_p95_s']*1000,
            historical_timing=variant in {'raw_base','initial_step2976'}))
    immutable_json(study.out/'comparison.json',dict(development=table,selection=decision))
    lines=['# 0.8B 金融边界双分支对照','', '|分支/检查点|开发准确率|宏F1|工具联合|人工漏判|误拒绝|请求P50毫秒|请求P95毫秒|',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t in table: lines.append(f"|{t['variant']}|{t['accuracy']:.2%}|{t['macro_f1']:.4f}|{t['joint']:.2%}|{t['human_misses']}|{t['false_refusals']}|{t['request_p50_ms']:.1f}|{t['request_p95_ms']:.1f}|")
    lines+=['',f"全局门槛通过：{decision['passed']}；选中：{decision['selected']}。",
        '两臂同初始化、同优化器预算和样本位置数；只用开发集一次全局选型。边界类别依据此前开发诊断设计，不能排除开发集适应。',
        'raw_base 和 initial_step2976 速度来自原实验历史测量，其余来自本实验分阶段测量；硬件负载和热状态可能不同，不能解释为架构或参数的因果测速。',
        '未调用 Jev、未切换部署。工具参数、后端保护和端到端效果不在本组件实验结论内。',
        '只有全局固定胜者允许校准和最终评估；无合格候选时不访问留出数据，也不延长预算。']
    (study.out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    immutable_json(study.out/'completion.json',dict(status='complete',selection=decision,
        protocol_sha256=study.protocol_hash(),calibration_evaluated=decision['passed'],final_evaluated=decision['passed'],
        model_api_requests=0,deployed=False))


def worker(study,resume):
    from qwenlab.joint_v5 import exclusive_lock
    with exclusive_lock('financial-eight-actions-gpu.lock'):
        if (study.out/'completion.json').exists(): raise FileExistsError('Completed study is immutable')
        control=ft.read(study.control) if study.control.exists() else {}
        if control.get('state')=='pause_requested': raise RuntimeError('Pause still pending')
        if control.get('state')=='paused' and not resume: raise RuntimeError('Explicit resume required')
        protocol=freeze(study,resume)
        if resume: ft.durable_json(study.control,dict(state='resuming',at=ft.now()))
        study.status('checking_protocol'); cycle.pause_check(study,'checking_protocol')
        import torch
        immutable_json(study.out/'hardware.json',dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__,cuda=torch.version.cuda))
        for label in ARMS:
            cycle.pause_check(study,'before_arm')
            arm=Arm(study,label)
            if not (arm.out/'arm-completion.json').exists():
                train(arm,ft.read(arm.out/'protocol.json'))
            cycle.pause_check(study,'after_arm')
        decision,reports=select(study,protocol)
        cycle.pause_check(study,'after_selection')
        if decision['passed']: run_holdout(study,decision)
        cycle.pause_check(study,'before_completion')
        report(study,decision,reports); study.status('complete',selected=decision['selected'],passed=decision['passed'])


def alive(status):
    import psutil
    try:
        p=psutil.Process(status['pid']); args=p.cmdline()
        return (abs(p.create_time()-status['process_created'])<.001 and
            'qwenlab.qwen35_boundary_study' in args and 'run' in args and Path(p.cwd()).resolve()==ROOT.resolve())
    except (KeyError,psutil.NoSuchProcess,psutil.AccessDenied): return False


def progress(study):
    status=ft.read(study.out/'status.json') if (study.out/'status.json').exists() else dict(stage='not_started',run_name=study.name)
    status['worker_alive']=alive(status)
    if not (study.out/'protocol.json').exists(): return status
    cfg=ft.read(study.out/'protocol.json')['config']; arms={}; recent=[]
    for label in ARMS:
        arm=Arm(study,label); logs=ft.rows_file(arm.out/'train.jsonl')
        step=logs[-1]['step'] if logs else 0
        arms[label]=dict(step=step,total_steps=cfg['max_steps'],percent=round(step/cfg['max_steps']*100,2),
            finished=(arm.out/'arm-completion.json').exists())
        recent.extend(r['elapsed_s'] for r in logs[-30:])
    status['arms']=arms
    status['total_percent']=round(sum(a['step'] for a in arms.values())/(2*cfg['max_steps'])*100,2)
    if recent:
        seconds=ft.metrics.percentile(recent,.5)
        status['remaining_train_minutes_estimate']=round(sum(cfg['max_steps']-a['step'] for a in arms.values())*seconds/60,1)
    status['estimate_scope']='pure training only; excludes evaluation, saving, model loading and future hardware changes'
    return status


def pause(study):
    status=ft.read(study.out/'status.json')
    if alive(status):
        ft.durable_json(study.control,dict(state='pause_requested',at=ft.now(),safe_to_shutdown=False))
        print('等待当前操作保存并退出；确认后再关机。',flush=True)
        while alive(status): time.sleep(2)
    status=ft.read(study.out/'status.json')
    if status.get('stage') not in ['paused','complete']:
        raise RuntimeError('No safe pause or completion confirmation')
    saved={}
    for label in ARMS:
        ckpt=ft.latest_checkpoint(Arm(study,label))
        if ckpt: saved[label]=ckpt.relative_to(ROOT).as_posix()
    ft.durable_json(study.control,dict(state=status['stage'],safe_to_shutdown=True,checkpoints=saved,at=ft.now()))
    print('两分支工作进程已退出，检查点完整，可以正常关机。',flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['run','progress','pause'])
    parser.add_argument('--resume',action='store_true'); parser.add_argument('--watch',action='store_true')
    args=parser.parse_args(); study=Study()
    if args.command=='progress':
        while True:
            value=progress(study); print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)
            if not args.watch or value.get('stage') in {'complete','failed','paused','not_started'} or not value['worker_alive']: break
            time.sleep(20)
    elif args.command=='pause': pause(study)
    else:
        try: worker(study,args.resume)
        except ft.Paused: print('已安全保存，退出整个双分支工作进程。',flush=True)
        except Exception as exc:
            status=ft.read(study.out/'status.json') if (study.out/'status.json').exists() else {}
            if status.get('pid')==os.getpid(): study.status('failed',error_type=type(exc).__name__,error=str(exc))
            raise


if __name__=='__main__': main()
