"""Bounded, separately recorded V8 continuation; original run stays read-only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
import random
import shutil
import time

from qwenlab import support_train_v8 as original
from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab.support_curriculum import digest
from qwenlab.support_distill import attach_teacher, distillation_loss
from qwenlab.joint_v4 import batch_logits
from qwenlab.joint_v5 import (atomic_json, encode, epoch_blocks, exclusive_lock,
                             lr_scale, read_resumable_rows, restore_rng, rng_state)
from qwenlab.prepare_v2 import read_rows, write_rows

PARENT = ROOT/'results/support-v8'
OUT = ROOT/'results/support-v8-observe'
DATA = ROOT/'data/processed/support-v8'
CKPT = ROOT/'.local/checkpoints/support-v8-observe'
SOURCE = ROOT/'.local/checkpoints/support-v8/step-2401'
POLICY = ROOT/'configs/support-v8-observe.json'
PAUSE = ROOT/'.local/support-v8-observe-pause.json'
TEACHER = ROOT/'.local/cache/support-v8-teacher'


def configure_io():
    # Only process-local output paths are redirected; frozen source files are untouched.
    original.OUT, original.CKPT = OUT, CKPT


def verify_checkpoint(path, protocol_hash):
    record = load_json(path/'checkpoint.json')
    expected = {'adapter_model.safetensors', 'adapter_config.json', 'training-state.pt'}
    if set(record['files']) != expected or path.name != f'step-{record["step"]}':
        raise ValueError('Invalid checkpoint manifest')
    if record['protocol_sha256'] != protocol_hash:
        raise ValueError('Checkpoint protocol changed')
    if any(sha(path/name) != h for name,h in record['files'].items()):
        raise ValueError('Checkpoint file changed')
    return record['step']


def prepare():
    parent = load_json(PARENT/'protocol.json')
    cfg = load_json(ROOT/'configs/support-v8.json')
    policy = load_json(POLICY)
    if cfg != parent['config']:
        raise ValueError('Original training config changed')
    for name,h in parent['source_hashes'].items():
        if digest(ROOT/name) != h:
            raise ValueError('Frozen source changed: '+name)
    manifest = load_json(DATA/'manifest.json')
    if digest(DATA/'manifest.json') != parent['prepared_manifest_sha256']:
        raise ValueError('Prepared manifest changed')
    for name,item in manifest['files'].items():
        if digest(DATA/name) != item['sha256']:
            raise ValueError('Frozen prepared data changed: '+name)
    for name,h in parent['initial_adapter_hashes'].items():
        if sha(ROOT/cfg['initial_adapter']/name) != h:
            raise ValueError('Original V5 anchor changed')
    if verify_checkpoint(SOURCE, sha(PARENT/'protocol.json')) != policy['start_step']:
        raise ValueError('Wrong continuation checkpoint')
    teacher = load_json(TEACHER/'manifest.json')
    if teacher['protocol_sha256'] != sha(PARENT/'protocol.json') or sha(TEACHER/'logits.jsonl') != teacher['logits_sha256']:
        raise ValueError('Original teacher cache changed')
    protocol = {
        'parent_protocol_sha256': sha(PARENT/'protocol.json'),
        'parent_checkpoint_sha256': sha(SOURCE/'checkpoint.json'),
        'teacher_manifest_sha256': sha(TEACHER/'manifest.json'),
        'policy': policy, 'training_config': cfg,
        'source_hashes': {name:digest(ROOT/name) for name in
                          ['src/qwenlab/support_v8_observe.py', 'configs/support-v8-observe.json']},
        'inherited_development_hashes': {p.relative_to(PARENT).as_posix():sha(p)
            for variant in ['v5-reference','step-200','step-2401']
            for p in (PARENT/variant).glob('*-dev*')},
        'post_hoc_extension': True, 'heldout_scores_previously_observed': True,
        'selection_uses_development_only': True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'protocol.json').exists():
        if load_json(OUT/'protocol.json') != protocol:
            raise ValueError('Observation protocol changed')
    else:
        atomic_json(OUT/'protocol.json', protocol)
    for rel,h in protocol['inherited_development_hashes'].items():
        target = OUT/rel
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if sha(target) != h:
                raise ValueError('Inherited development results changed')
        else:
            shutil.copyfile(PARENT/rel, target)
    return cfg, policy


def observation_decision(reference, current, cfg, policy, step):
    strict = original.gate(reference, current, cfg)
    extra = {n:current[n].get('human_missed',0)-reference[n].get('human_missed',0)
             for n in ('business','legacy')}
    other_failures = [r for r in strict['reasons'] if not r.endswith(': increased human misses')]
    severe = bool(other_failures) or sum(max(0,n) for n in extra.values()) > policy['max_extra_misses_while_observing']
    return {'candidate_eligible': strict['continue_training'], 'strict_gate': strict,
            'extra_human_misses': extra, 'severe_regression': severe,
            'continue_observation': step < policy['end_step'] and not severe,
            'budget_exhausted': step >= policy['end_step']}


def latest_checkpoint():
    candidates = []
    for p in CKPT.glob('step-*'):
        candidates.append((verify_checkpoint(p,sha(OUT/'protocol.json')),p))
    return max(candidates, default=(2401,SOURCE))


def status(stage, **values):
    original.status(stage, **values)


def pause_after_checkpoint(step):
    if not PAUSE.exists() or load_json(PAUSE).get('state') != 'requested':
        return False
    path = CKPT/f'step-{step}'
    if not path.exists():
        return False
    verify_checkpoint(path,sha(OUT/'protocol.json'))
    for p in [*path.iterdir(), OUT/'protocol.json']:
        with p.open('r+b') as f:
            f.flush(); os.fsync(f.fileno())
    status('paused',step=step,checkpoint=path.relative_to(ROOT).as_posix())
    atomic_json(PAUSE, {'state':'paused','step':step,'pid':os.getpid(),
                       'updated_at':datetime.now(timezone.utc).isoformat()})
    return True


def finish(reference, cfg, outcome, step):
    choices = {}
    trend = []
    for variant in ['v5-reference','step-200','step-2401','step-2801','step-3201']:
        folder=OUT/variant
        if not all((folder/f'{n}-dev-metrics.json').exists() for n in ('business','legacy','massive','crosswoz')):
            continue
        current={n:load_json(folder/f'{n}-dev-metrics.json') for n in ('business','legacy','massive','crosswoz')}
        decision=original.gate(reference,current,cfg)
        choices[variant]={'eligible': variant=='v5-reference' or decision['continue_training'],
                          'score':current['business']['tasks']['route']['macro_f1_gold_supported_classes'],
                          'reasons':decision['reasons']}
        trend.append({'variant':variant, 'business_accuracy':current['business']['tasks']['route']['accuracy'],
                      'legacy_accuracy':current['legacy']['tasks']['route']['accuracy'],
                      'business_human_missed':current['business']['human_missed'],
                      'legacy_human_missed':current['legacy']['human_missed']})
    winner=max((v for v in choices if choices[v]['eligible']),key=lambda v:choices[v]['score'])
    atomic_json(OUT/'selection.json',{'selected':winner,'choices':choices,'development_only':True,
        'deployment_changed':False,'independent_validation_pending':True})
    atomic_json(OUT/'development-trend.json',trend)
    lines=['# V8延续观察结果','',f'状态：{outcome}；结束步数：{step}；开发集选择：{winner}。',
           '','|检查点|新业务路由|旧业务路由|新业务人工漏判|旧业务人工漏判|',
           '|---|---:|---:|---:|---:|']
    for r in trend:
        lines.append(f"|{r['variant']}|{r['business_accuracy']:.2%}|{r['legacy_accuracy']:.2%}|{r['business_human_missed']}|{r['legacy_human_missed']}|")
    lines += ['', '本实验在观察过原V8结果后追加，只验证开发集训练轨迹。未新增Jev请求、校准或最终挑战评估；不能称为独立盲测或已可部署。',
              '原候选验收门槛未放宽。后续需要独立留出验证；默认仍保留Jev。']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    status(outcome,step=step,selected=winner,report='results/support-v8-observe/report.md')


def progress():
    state=load_json(OUT/'status.json') if (OUT/'status.json').exists() else {'stage':'not_started'}
    logs=[]
    if (OUT/'train.jsonl').exists():
        lines=(OUT/'train.jsonl').read_text(encoding='utf-8').splitlines()
        for i,line in enumerate(lines):
            try: logs.append(json.loads(line))
            except json.JSONDecodeError:
                if i != len(lines)-1: raise
    if logs and state['stage'] in ('training','encoding_training','loading','evaluation'):
        recent=logs[-101:]
        if len(recent)>1:
            seconds=(recent[-1]['elapsed_s']-recent[0]['elapsed_s'])/(recent[-1]['step']-recent[0]['step'])
            state.update(last_training_step=logs[-1]['step'],seconds_per_step=round(seconds,2),
                         remaining_training_minutes=round(max(0,3201-logs[-1]['step'])*seconds/60,1),
                         eta_excludes_evaluation=True)
    return state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','run','progress','pause'])
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    configure_io()
    if args.action=='progress':
        while True:
            print(json.dumps(progress(),ensure_ascii=False,indent=2),flush=True)
            if not args.watch: return
            time.sleep(15)
    elif args.action=='prepare':
        prepare(); print('Observation protocol verified; no training started.')
    elif args.action=='pause':
        import psutil
        state=progress()
        if state['stage'] not in ('training','evaluation','loading','encoding_training','paused'):
            raise RuntimeError('No active observation training to pause')
        if state['stage']!='paused':
            if not psutil.pid_exists(state['pid']): raise RuntimeError('Worker is not alive')
            atomic_json(PAUSE,{'state':'requested','pid':state['pid']})
        print('等待完整检查点和训练进程退出；请勿提前关机。',flush=True)
        while psutil.pid_exists(state['pid']): time.sleep(2)
        done=progress()
        if done['stage'] not in ('paused','observation_complete','observation_stopped'):
            raise RuntimeError('Worker exited unexpectedly; inspect status before shutdown')
        print('检查点已保存，训练进程已退出，可以正常关机。',flush=True)
    else:
        # Reuse original pipeline and GPU locks to exclude simultaneous original jobs.
        with exclusive_lock('support-v8-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'):
            if (OUT/'status.json').exists() and load_json(OUT/'status.json')['stage'] in ('observation_complete','observation_stopped'):
                raise RuntimeError('Bounded experiment already finished; do not restart')
            if PAUSE.exists() and load_json(PAUSE).get('state') in ('requested','paused'):
                if not args.resume: raise RuntimeError('Explicit --resume is required after pause')
                atomic_json(PAUSE,{'state':'resuming','user_command':True})
            try:
                run(args.resume)
            except BaseException as exc:
                status('failed',error=type(exc).__name__,message=str(exc))
                raise


# Training loop below follows the frozen V8 optimizer/encoding/loss code.

def run(resume=False):
    import numpy as np
    import torch
    cfg, policy = prepare()
    step, checkpoint = latest_checkpoint()
    if checkpoint != SOURCE and not resume:
        raise FileExistsError('Use --resume for the existing run')
    if not checkpoint and (OUT/'train.jsonl').exists():
        raise ValueError('Uncheckpointed run exists; inspect before restarting')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); np.random.seed(cfg['seed'])
    status('loading', resumed_from_step=step)
    tok, model = original.load_trainable(checkpoint or ROOT/cfg['initial_adapter'])
    params = [p for p in model.parameters() if p.requires_grad]
    # Anchor to the original V5 adapter even when resuming a V8 checkpoint.
    from safetensors.torch import load_file
    initial = load_file(str(ROOT/cfg['initial_adapter']/'adapter_model.safetensors'))
    anchors = []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            key = name.replace('.default.', '.')
            if key not in initial or initial[key].shape != parameter.shape:
                raise ValueError('Initial adapter anchor mismatch: ' + name)
            anchors.append(initial[key].to(device=parameter.device,dtype=parameter.dtype))
    optimizer = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
    reference_paths = [OUT/'v5-reference'/f'{n}-dev-metrics.json' for n in ('business','massive','crosswoz','legacy')]
    if all(p.exists() for p in reference_paths):
        reference = {p.name.split('-')[0]:load_json(p) for p in reference_paths}
    elif checkpoint:
        raise ValueError('Baseline must complete before any checkpoint')
    else:
        reference = original.evaluate(tok, model, 'v5-reference')
    status('encoding_training', resumed_from_step=step)
    pools = {}
    permutation = random.Random(cfg['seed'])
    for name in ('business', 'massive', 'crosswoz'):
        rows = read_rows(DATA/f'{name}-train.jsonl')
        groups = Counter(r['group'] for r in rows)
        for task in (cfg['business_tasks'] if name == 'business' else ['intent']):
            pool = []
            for row in rows:
                item = encode(tok, row, task, permutation.randrange(2**31))
                item['group_weight'] = len(rows)/(len(groups)*groups[row['group']]) if name == 'business' else 1.
                item['teacher_eligible'] = (name == 'business' and row.get('training_origin') == cfg['distillation']['origin'])
                if item['teacher_eligible'] and row['split'] != 'train':
                    raise ValueError('Teacher may only score training rows')
                pool.append(item)
            pools[name+'.'+task] = pool
    # Preserve dropout RNG regardless of whether a teacher cache was already built.
    before_teacher = rng_state()
    teacher = attach_teacher(tok, model, pools, cfg, ROOT/'.local/cache/support-v8-teacher',
                             sha(PARENT/'protocol.json'), status, checkpoint_exists=True)
    restore_rng(before_teacher)
    atomic_json(OUT/'teacher-summary.json', teacher)
    per_epoch = math.ceil(len(epoch_blocks(pools,cfg,0))/cfg['gradient_accumulation'])
    total = per_epoch*cfg['epochs']
    eval_steps = policy['evaluation_steps']
    if total != policy['lr_schedule_total_steps']:
        raise ValueError('Learning-rate horizon changed')
    schedule = {'pilot_steps': cfg['pilot_steps'], 'total_steps': total, 'observation_end_step': policy['end_step'], 'steps_per_epoch': per_epoch,
                'evaluation_steps': eval_steps, 'examples_per_epoch':{k:len(v) for k,v in pools.items()}}
    atomic_json(OUT/'schedule.json',schedule)
    summary = dict(schedule, optimizer_steps=0, training_elapsed_s=0., sampled={}, status='running',
        trainable_parameters=sum(p.numel() for p in params), max_input_tokens=max(len(x['tokens']['input_ids']) for p in pools.values() for x in p))
    if checkpoint:
        saved = torch.load(checkpoint/'training-state.pt', map_location='cpu', weights_only=False)
        expected_protocol = PARENT/'protocol.json' if checkpoint == SOURCE else OUT/'protocol.json'
        if saved['protocol_sha256'] != sha(expected_protocol):
            raise ValueError('Untrusted local training state')
        if saved['teacher_manifest_sha256'] != sha(ROOT/'.local/cache/support-v8-teacher/manifest.json'):
            raise ValueError('Checkpoint teacher cache changed')
        optimizer.load_state_dict(saved['optimizer']); restore_rng(saved['rng']); summary=saved['summary']
        if summary['optimizer_steps'] != step:
            raise ValueError('Optimizer step disagrees with checkpoint manifest')
        summary.update(schedule)
        logs=read_resumable_rows(OUT/'train.jsonl')
        if any(r['step']>step for r in logs):
            write_rows(ROOT/'.local'/f'support-v8-uncheckpointed-{time.time_ns()}.jsonl',[r for r in logs if r['step']>step])
            write_rows(OUT/'train.jsonl',[r for r in logs if r['step']<=step])
    sampled=Counter(summary['sampled'])
    if checkpoint and step in eval_steps:
        current=original.evaluate(tok,model,f'step-{step}')
        decision=observation_decision(reference,current,cfg,policy,step)
        atomic_json(OUT/f'observation-{step}.json',decision)
        if not decision['continue_observation']:
            outcome='observation_complete' if decision['budget_exhausted'] else 'observation_stopped'
            summary['status']=outcome
            atomic_json(OUT/'training-summary.json',summary)
            finish(reference,cfg,outcome,step)
            return
    model.train(); optimizer.zero_grad(set_to_none=True); torch.cuda.reset_peak_memory_stats()
    for epoch in range(step//per_epoch,cfg['epochs']):
        blocks=epoch_blocks(pools,cfg,epoch)
        for local in range(per_epoch):
            current_step=epoch*per_epoch+local+1
            if current_step>policy['end_step']:
                return
            if current_step<=step:
                continue
            status('training',step=current_step-1,total_steps=policy['end_step'],lr_schedule_total_steps=total)
            start=time.perf_counter()
            chunk=blocks[local*cfg['gradient_accumulation']:(local+1)*cfg['gradient_accumulation']]
            for group in optimizer.param_groups:
                group['lr']=cfg['learning_rate']*lr_scale(current_step,total,cfg['warmup_fraction'])
            losses=[]; distill_losses=[]
            for name,indices in chunk:
                examples=[pools[name][i] for i in indices]
                scores=batch_logits(tok,model,examples)
                loss=sum(torch.nn.functional.cross_entropy(v[None,:],torch.tensor([x['target']],device='cuda'))*x['group_weight'] for x,v in zip(examples,scores))/len(examples)
                kd=sum((distillation_loss(v,x['teacher_logits'],cfg['distillation']['temperature'])*x['group_weight']
                        for x,v in zip(examples,scores) if x.get('teacher_eligible')), scores[0].new_zeros(()))/len(examples)
                total_loss=loss+cfg['distillation']['strength']*kd
                if not torch.isfinite(total_loss):
                    raise FloatingPointError('Nonfinite loss')
                (total_loss*cfg['weights'][name]/len(chunk)).backward()
                distill_losses.append(float(kd.detach()))
                losses.append(float(loss.detach())); sampled[name]+=len(examples)
            anchor_loss = original.anchor_penalty(params, anchors, cfg['anchor_strength'])
            if not torch.isfinite(anchor_loss):
                raise FloatingPointError('Nonfinite anchor penalty')
            anchor_loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(params,1.)
            if not torch.isfinite(norm):
                raise FloatingPointError('Nonfinite gradients')
            optimizer.step(); optimizer.zero_grad(set_to_none=True); torch.cuda.synchronize()
            summary.update(status='running',optimizer_steps=current_step,sampled=dict(sampled),
                training_elapsed_s=summary['training_elapsed_s']+time.perf_counter()-start,
                peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30)
            log={'step':current_step,'loss':sum(losses)/len(losses),'distillation_loss':sum(distill_losses)/len(distill_losses),'gradient_norm':norm.item(),
                 'lr':optimizer.param_groups[0]['lr'],'elapsed_s':summary['training_elapsed_s'],'anchor_penalty':float(anchor_loss.detach())}
            append_json(OUT/'train.jsonl',log)
            if current_step%10==0:
                atomic_json(OUT/'training-summary.json',summary)
                print(json.dumps(log),flush=True)
            if current_step%cfg['checkpoint_every']==0 or current_step in eval_steps:
                original.save(model,optimizer,current_step,summary.copy())
                if pause_after_checkpoint(current_step): return
            if current_step in eval_steps:
                current=original.evaluate(tok,model,f'step-{current_step}')
                decision=observation_decision(reference,current,cfg,policy,current_step)
                atomic_json(OUT/f'observation-{current_step}.json',decision)
                if not decision['continue_observation']:
                    outcome='observation_complete' if decision['budget_exhausted'] else 'observation_stopped'
                    summary['status']=outcome
                    atomic_json(OUT/'training-summary.json',summary)
                    finish(reference,cfg,outcome,current_step)
                    return
                model.train()


if __name__=='__main__':
    main()
