"""Reviewed support curriculum: gated pilot, resume, isolated checkpoints.

No provider calls or automatic promotion. Development selects; calibration and
challenge stay untouched during training. All mutable state stays on the project drive.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
import os
import random
import time

from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab import support_expansion as exp
from qwenlab.joint_v4 import batch_logits, metrics
from qwenlab.joint_v5 import (atomic_json, encode, epoch_blocks, exclusive_lock,
    lr_scale, predict_one, read_resumable_rows, restore_rng, rng_state)
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows, write_rows

OUT = ROOT / 'results/support-v6'
DATA = ROOT / 'data/processed/support-v6'
CKPT = ROOT / '.local/checkpoints/support-v6'
CONFIG = ROOT / 'configs/support-v6.json'
SOURCES = ['src/qwenlab/support_train.py', 'src/qwenlab/joint_v5.py',
           'src/qwenlab/joint_v4.py', 'src/qwenlab/modeling.py', 'src/qwenlab/common.py',
           'configs/support-v6.json', 'configs/decision-v5.json',
           'data/processed/v2/massive-spec.json', 'data/processed/v2/crosswoz-spec.json']


def balanced_sample(rows, count, seed):
    buckets = defaultdict(list)
    for row in rows:
        buckets[row['labels']['intent']].append(row)
    rng = random.Random(seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    result = []
    while len(result) < count and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(result) < count:
                result.append(buckets[key].pop())
    return result


def prepare():
    cfg = load_json(CONFIG)
    if not cfg['training_authorization']['confirmed']:
        raise PermissionError('Explicit training authorization required')
    source = ROOT / cfg['reviewed_source']
    exp.check_frozen(source)
    data_manifest = DATA / 'manifest.json'
    if not data_manifest.exists():
        if DATA.exists():
            raise FileExistsError('Incomplete prepared data; inspect it before retrying')
        business = read_rows(source / 'train-reviewed-only.jsonl')
        if len(business) != 3901 or any(r['label_status'] != 'human_reviewed' for r in business):
            raise ValueError('Reviewed training population changed')
        datasets = {'business-train.jsonl': business,
                    'business-dev.jsonl': read_rows(source / 'development-candidates.jsonl')}
        source_hashes = {cfg['reviewed_source'] + '/manifest.json': exp.base.digest(source / 'manifest.json')}
        for name, count in cfg['replay_rows'].items():
            path = ROOT / f'data/processed/v5/{name}-train.jsonl'
            pool = read_rows(path)
            # Official dev/calibration/test text and groups may not enter replay.
            blocked_text, blocked_groups = set(), set()
            for split in ('dev', 'calibration', 'test'):
                held = ROOT / f'data/processed/v5/{name}-{split}.jsonl'
                held_rows = read_rows(held)
                source_hashes[held.relative_to(ROOT).as_posix()] = exp.base.digest(held)
                blocked_text.update(exp.base.normalize(r['message']) for r in held_rows)
                blocked_groups.update(r['group'] for r in held_rows)
            pool = [r for r in pool if exp.base.normalize(r['message']) not in blocked_text and r['group'] not in blocked_groups]
            datasets[f'{name}-train.jsonl'] = balanced_sample(pool, count, cfg['seed'])
            if len(datasets[f'{name}-train.jsonl']) != count:
                raise ValueError('Insufficient leakage-free replay rows: ' + name)
            datasets[f'{name}-dev.jsonl'] = read_rows(ROOT / f'data/processed/v5/{name}-dev.jsonl')
            source_hashes[path.relative_to(ROOT).as_posix()] = exp.base.digest(path)
        legacy = ROOT / 'data/processed/v5/business-dev.jsonl'
        datasets['legacy-dev.jsonl'] = read_rows(legacy)
        source_hashes[legacy.relative_to(ROOT).as_posix()] = exp.base.digest(legacy)
        DATA.mkdir(parents=True)
        for name, rows in datasets.items():
            write_rows(DATA / name, rows)
        atomic_json(data_manifest, {'source_hashes': source_hashes,
            'files': {name: {'rows': len(rows), 'sha256': exp.base.digest(DATA/name)} for name, rows in datasets.items()},
            'reviewed_source': cfg['reviewed_source'], 'calibration_and_challenge_not_used_for_selection': True})
    manifest = load_json(data_manifest)
    for name, item in manifest['files'].items():
        if exp.base.digest(DATA/name) != item['sha256']:
            raise ValueError('Frozen prepared data changed: ' + name)
    for name, digest in manifest['source_hashes'].items():
        if exp.base.digest(ROOT/name) != digest:
            raise ValueError('Prepared data source changed: ' + name)
    adapter = ROOT / cfg['initial_adapter']
    protocol = {'config': cfg, 'prepared_manifest_sha256': exp.base.digest(data_manifest),
        'source_hashes': {name: exp.base.digest(ROOT/name) for name in SOURCES},
        'initial_adapter_hashes': {name: sha(adapter/name) for name in ('adapter_model.safetensors', 'adapter_config.json')},
        'new_business_rows_reviewed': True, 'public_replay_uses_original_labels': True,
        'evaluation_batch': 1, 'no_jev_or_test_predictions_used_for_training': True}
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'protocol.json').exists() and load_json(OUT/'protocol.json') != protocol:
        raise ValueError('Frozen training protocol changed; create a new run instead')
    if not (OUT/'protocol.json').exists():
        atomic_json(OUT/'protocol.json', protocol)
        atomic_json(OUT/'data-manifest.json', manifest)
    return cfg


def status(stage, **values):
    atomic_json(OUT/'status.json', {'stage': stage, 'updated_at': datetime.now(timezone.utc).isoformat(),
                                  'pid': os.getpid(), **values})


def gate(reference, current, cfg):
    bad = []
    maximum = cfg['gate']['max_regression']
    for name in ('business', 'legacy', 'massive', 'crosswoz'):
        for task, base in reference[name]['tasks'].items():
            now = current[name]['tasks'][task]
            for metric in ('accuracy', 'macro_f1_gold_supported_classes'):
                if now[metric] < base[metric] - maximum:
                    bad.append(f'{name}.{task}.{metric}: regression exceeds {maximum}')
        if 'human_missed' in reference[name] and current[name]['human_missed'] > reference[name]['human_missed'] + cfg['gate']['max_extra_human_misses']:
            bad.append(name + ': increased human misses')
    a, b = reference['business']['tasks']['route'], current['business']['tasks']['route']
    gain = (b['macro_f1_gold_supported_classes'] >= a['macro_f1_gold_supported_classes'] + cfg['gate']['min_route_f1_gain']
            or b['correct'] >= a['correct'] + cfg['gate']['min_route_correct_gain'])
    return {'continue_training': not bad and gain, 'guardrails_pass': not bad,
            'route_gain': gain, 'reasons': bad + ([] if gain else ['No pre-specified route improvement']),
            'route_accuracy_delta': b['accuracy'] - a['accuracy'],
            'route_macro_f1_delta': b['macro_f1_gold_supported_classes'] - a['macro_f1_gold_supported_classes']}


def evaluate(tok, model, variant):
    model.eval()
    result = {}
    folder = OUT/variant
    folder.mkdir(exist_ok=True)
    for name in ('business', 'massive', 'crosswoz', 'legacy'):
        rows = read_rows(DATA/f'{name}-dev.jsonl')
        path = folder/f'{name}-dev.jsonl'
        done = read_resumable_rows(path)
        if [r['id'] for r in done] != [r['id'] for r in rows[:len(done)]]:
            raise ValueError('Evaluation order mismatch')
        status('evaluation', variant=variant, dataset=name, done=len(done), total=len(rows))
        for row in rows[len(done):]:
            prediction = predict_one(tok, model, row)
            append_json(path, prediction)
            done.append(prediction)
            if len(done) % 10 == 0:
                status('evaluation', variant=variant, dataset=name, done=len(done), total=len(rows))
        result[name] = metrics(done)
        atomic_json(folder/f'{name}-dev-metrics.json', result[name])
    return result


def load_trainable(adapter):
    from peft import PeftModel, prepare_model_for_kbit_training
    tok, base = load_model('nf4')
    tok.padding_side = 'left'
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant': False})
    model = PeftModel.from_pretrained(base, adapter, is_trainable=True)
    if any(p.requires_grad and ('lora_' not in n or 'visual' in n) for n, p in model.named_parameters()):
        raise ValueError('Unexpected trainable weight')
    return tok, model


def save(model, optimizer, step, summary):
    import torch
    final = CKPT/f'step-{step}'
    if final.exists():
        raise FileExistsError(final)
    temp = CKPT/f'.step-{step}-{time.time_ns()}.pending'
    temp.mkdir(parents=True)
    model.save_pretrained(temp, safe_serialization=True)
    ac = load_json(temp/'adapter_config.json')
    ac['base_model_name_or_path'] = 'Qwen/Qwen3-VL-2B-Instruct'
    atomic_json(temp/'adapter_config.json', ac)
    torch.save({'optimizer': optimizer.state_dict(), 'rng': rng_state(), 'summary': summary,
                'protocol_sha256': sha(OUT/'protocol.json')}, temp/'training-state.pt')
    atomic_json(temp/'checkpoint.json', {'step': step, 'protocol_sha256': sha(OUT/'protocol.json'),
        'files': {n: sha(temp/n) for n in ('adapter_model.safetensors','adapter_config.json','training-state.pt')}})
    temp.rename(final)
    atomic_json(OUT/'latest-checkpoint.json', {'step': step, 'path': final.relative_to(ROOT).as_posix()})


def latest_checkpoint():
    checkpoints = []
    for path in CKPT.glob('step-*'):
        record = load_json(path/'checkpoint.json')
        if record['protocol_sha256'] != sha(OUT/'protocol.json') or any(sha(path/n) != digest for n,digest in record['files'].items()):
            raise ValueError('Checkpoint failed integrity check')
        checkpoints.append((record['step'], path))
    return max(checkpoints, default=(0, None))


def run(resume=False):
    import numpy as np
    import torch
    cfg = prepare()
    step, checkpoint = latest_checkpoint()
    if checkpoint and not resume:
        raise FileExistsError('Use --resume for the existing run')
    if not checkpoint and (OUT/'train.jsonl').exists():
        raise ValueError('Uncheckpointed run exists; inspect before restarting')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); np.random.seed(cfg['seed'])
    status('loading', resumed_from_step=step)
    tok, model = load_trainable(checkpoint or ROOT/cfg['initial_adapter'])
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
    reference_paths = [OUT/'v5-reference'/f'{n}-dev-metrics.json' for n in ('business','massive','crosswoz','legacy')]
    if all(p.exists() for p in reference_paths):
        reference = {p.name.split('-')[0]:load_json(p) for p in reference_paths}
    elif checkpoint:
        raise ValueError('Baseline must complete before any checkpoint')
    else:
        reference = evaluate(tok, model, 'v5-reference')
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
                pool.append(item)
            pools[name+'.'+task] = pool
    per_epoch = math.ceil(len(epoch_blocks(pools,cfg,0))/cfg['gradient_accumulation'])
    total = per_epoch*cfg['epochs']
    eval_steps = sorted({cfg['pilot_steps'],per_epoch,total})
    schedule = {'pilot_steps': cfg['pilot_steps'], 'total_steps': total, 'steps_per_epoch': per_epoch,
                'evaluation_steps': eval_steps, 'examples_per_epoch':{k:len(v) for k,v in pools.items()}}
    atomic_json(OUT/'schedule.json',schedule)
    summary = dict(schedule, optimizer_steps=0, training_elapsed_s=0., sampled={}, status='running',
        trainable_parameters=sum(p.numel() for p in params), max_input_tokens=max(len(x['tokens']['input_ids']) for p in pools.values() for x in p))
    if checkpoint:
        saved = torch.load(checkpoint/'training-state.pt', map_location='cpu', weights_only=False)
        if saved['protocol_sha256'] != sha(OUT/'protocol.json'):
            raise ValueError('Untrusted local training state')
        optimizer.load_state_dict(saved['optimizer']); restore_rng(saved['rng']); summary=saved['summary']
        logs=read_resumable_rows(OUT/'train.jsonl')
        if any(r['step']>step for r in logs):
            write_rows(ROOT/'.local'/f'support-v6-uncheckpointed-{time.time_ns()}.jsonl',[r for r in logs if r['step']>step])
            write_rows(OUT/'train.jsonl',[r for r in logs if r['step']<=step])
    sampled=Counter(summary['sampled'])
    # A saved pilot checkpoint cannot bypass its development gate on resume.
    if checkpoint and step in eval_steps:
        current=evaluate(tok,model,f'step-{step}')
        decision=gate(reference,current,cfg)
        atomic_json(OUT/f'gate-{step}.json',decision)
        if not decision['continue_training']:
            summary['status']='stopped_at_gate'
            atomic_json(OUT/'training-summary.json',summary)
            finish(reference, 'stopped_at_gate', step)
            return
    model.train(); optimizer.zero_grad(set_to_none=True); torch.cuda.reset_peak_memory_stats()
    for epoch in range(step//per_epoch,cfg['epochs']):
        blocks=epoch_blocks(pools,cfg,epoch)
        for local in range(per_epoch):
            current_step=epoch*per_epoch+local+1
            if current_step<=step:
                continue
            status('training',step=current_step-1,total_steps=total,pilot_steps=cfg['pilot_steps'])
            start=time.perf_counter()
            chunk=blocks[local*cfg['gradient_accumulation']:(local+1)*cfg['gradient_accumulation']]
            for group in optimizer.param_groups:
                group['lr']=cfg['learning_rate']*lr_scale(current_step,total,cfg['warmup_fraction'])
            losses=[]
            for name,indices in chunk:
                examples=[pools[name][i] for i in indices]
                scores=batch_logits(tok,model,examples)
                loss=sum(torch.nn.functional.cross_entropy(v[None,:],torch.tensor([x['target']],device='cuda'))*x['group_weight'] for x,v in zip(examples,scores))/len(examples)
                if not torch.isfinite(loss):
                    raise FloatingPointError('Nonfinite loss')
                (loss*cfg['weights'][name]/len(chunk)).backward()
                losses.append(float(loss.detach())); sampled[name]+=len(examples)
            norm=torch.nn.utils.clip_grad_norm_(params,1.)
            if not torch.isfinite(norm):
                raise FloatingPointError('Nonfinite gradients')
            optimizer.step(); optimizer.zero_grad(set_to_none=True); torch.cuda.synchronize()
            summary.update(status='running',optimizer_steps=current_step,sampled=dict(sampled),
                training_elapsed_s=summary['training_elapsed_s']+time.perf_counter()-start,
                peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30)
            log={'step':current_step,'loss':sum(losses)/len(losses),'gradient_norm':norm.item(),
                 'lr':optimizer.param_groups[0]['lr'],'elapsed_s':summary['training_elapsed_s']}
            append_json(OUT/'train.jsonl',log)
            if current_step%10==0:
                atomic_json(OUT/'training-summary.json',summary)
                print(json.dumps(log),flush=True)
            if current_step%cfg['checkpoint_every']==0 or current_step in eval_steps:
                save(model,optimizer,current_step,summary.copy())
            if current_step in eval_steps:
                current=evaluate(tok,model,f'step-{current_step}')
                decision=gate(reference,current,cfg)
                atomic_json(OUT/f'gate-{current_step}.json',decision)
                if not decision['continue_training']:
                    summary['status']='stopped_at_gate'
                    atomic_json(OUT/'training-summary.json',summary)
                    finish(reference,'stopped_at_gate',current_step)
                    return
                model.train()
    if dict(sampled)!={k:len(v)*cfg['epochs'] for k,v in pools.items()}:
        raise AssertionError('Training coverage mismatch')
    summary['status']='complete'
    atomic_json(OUT/'training-summary.json',summary)
    finish(reference,'complete',total)


def finish(reference, outcome, step):
    cfg=load_json(CONFIG)
    choices={'v5-reference':{'eligible':True,'score':reference['business']['tasks']['route']['macro_f1_gold_supported_classes']}}
    for file in OUT.glob('gate-*.json'):
        n=int(file.stem.split('-')[1]); decision=load_json(file)
        m=load_json(OUT/f'step-{n}'/'business-dev-metrics.json')
        choices[f'step-{n}']={'eligible':decision['guardrails_pass'],
            'score':m['tasks']['route']['macro_f1_gold_supported_classes']}
    winner=max((v for v in choices if choices[v]['eligible']),key=lambda v:choices[v]['score'])
    atomic_json(OUT/'selection.json',{'selected':winner,'choices':choices,'basis':'frozen development gate; no calibration/challenge selection','deployment_changed':False})
    status(outcome,step=step,selected=winner,training_started=True)
    (OUT/'summary.md').write_text(f'# 客服专项训练运行状态\n\n状态：{outcome}。已完成{step}步，开发集选择：{winner}。\n\n模型未部署；校准、挑战、最终速度验证尚未执行。详细结果见各检查点dev-metrics.json和gate文件。\n',encoding='utf-8')


def progress():
    state=load_json(OUT/'status.json') if (OUT/'status.json').exists() else {'stage':'not_started'}
    logs=[]
    if (OUT/'train.jsonl').exists():
        lines=(OUT/'train.jsonl').read_text(encoding='utf-8').splitlines()
        for i,line in enumerate(lines):
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                if i!=len(lines)-1:
                    raise
    if state.get('updated_at'):
        state['seconds_since_status_update']=round((datetime.now(timezone.utc)-datetime.fromisoformat(state['updated_at'])).total_seconds())
        state['possibly_stale']=state['seconds_since_status_update']>180 and state['stage'] not in ('complete','stopped_at_gate','failed')
    if len(logs)>1 and state['stage'] not in ('complete','stopped_at_gate','failed'):
        recent=logs[-101:]; seconds=(recent[-1]['elapsed_s']-recent[0]['elapsed_s'])/(recent[-1]['step']-recent[0]['step'])
        schedule=load_json(OUT/'schedule.json')
        target=schedule['pilot_steps'] if logs[-1]['step']<schedule['pilot_steps'] else schedule['total_steps']
        state.update(last_training_step=logs[-1]['step'],seconds_per_step=round(seconds,2),
            remaining_training_minutes_to_current_target=round(max(0,target-logs[-1]['step'])*seconds/60,1),
            eta_excludes_evaluation=True)
    return state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','run','progress'])
    parser.add_argument('--resume',action='store_true'); parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    if args.action=='progress':
        while True:
            print(json.dumps(progress(),ensure_ascii=False,indent=2),flush=True)
            if not args.watch:
                return
            time.sleep(15)
    elif args.action=='prepare':
        prepare(); print('Support v6 protocol prepared; training not started',flush=True)
    else:
        with exclusive_lock('support-v6-pipeline.lock'), exclusive_lock('joint-v5-gpu.lock'):
            try:
                run(args.resume)
            except BaseException as exc:
                status('failed',error=type(exc).__name__,message=str(exc))
                raise


if __name__=='__main__':
    main()
