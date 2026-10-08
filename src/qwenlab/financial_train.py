"""Local, resumable 200-step eight-action pilot. Development only, no vendor API.

Immutable data/prompt/policy from financial-eight-actions-v2 are consumed as-is.
Fresh language-only QLoRA; inference selects a tool only after predicted tool.
No calibration/final selection, automatic longer training, deployment or Git.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import re
import time

from qwenlab.common import ROOT, sha
from qwenlab import financial_ready as data
from qwenlab import financial_actions_prompt as prompts
from qwenlab import financial_actions_metrics as metrics

DEFAULT = 'financial-eight-actions-pilot-v2'
ACTIVE = ROOT/'.local/financial-eight-actions-v2/active-run.json'
SOURCES = ['src/qwenlab/financial_train.py', 'src/qwenlab/financial_actions_prompt.py',
    'src/qwenlab/financial_actions_metrics.py', 'src/qwenlab/financial_ready.py',
    'src/qwenlab/financial_pilot.py', 'src/qwenlab/financial_release.py',
    'src/qwenlab/financial_release_core.py', 'src/qwenlab/financial_completion.py',
    'src/qwenlab/financial_expansion.py', 'src/qwenlab/prepare_v2.py',
    'src/qwenlab/modeling.py', 'src/qwenlab/joint_v4.py', 'src/qwenlab/joint_v5.py',
    'src/qwenlab/candidate_inference.py', 'src/qwenlab/common.py',
    'scripts/start-financial-pilot.ps1', 'scripts/pause-financial-pilot.ps1',
    'scripts/resume-financial-pilot.ps1', 'scripts/use-env.ps1']
PACKAGES = ['torch', 'transformers', 'peft', 'bitsandbytes', 'accelerate', 'numpy', 'psutil']
TERMINAL = {'pilot_complete', 'failed', 'paused'}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def durable_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.part')
    with tmp.open('wb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
        stream.flush(); os.fsync(stream.fileno())
    tmp.replace(path)


def append(path, value):
    with Path(path).open('ab') as stream:
        stream.write((json.dumps(value, ensure_ascii=False)+'\n').encode('utf-8'))
        stream.flush(); os.fsync(stream.fileno())


def rows_file(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line] if path.exists() else []


class Run:
    def __init__(self, name):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name):
            raise ValueError('Run name must be a short lowercase identifier, never a path')
        self.name = name
        self.out = ROOT/'results'/name
        self.checkpoints = ROOT/'.local/checkpoints'/name
        self.control = ROOT/'.local/financial-eight-actions-v2'/(name+'-control.json')
        self.cache = ROOT/'.local/cache'/name

    def status(self, stage, **values):
        import psutil
        value = dict(stage=stage, updated_at=now(), pid=os.getpid(),
            process_created=psutil.Process().create_time(), run_name=self.name, **values)
        durable_json(self.out/'status.json', value)

    def protocol_hash(self):
        return sha(self.out/'protocol.json')


def active_name(explicit=None):
    return explicit or (read(ACTIVE)['run_name'] if ACTIVE.exists() else DEFAULT)


def freeze(run, resume):
    data.validate()
    manifest = read(data.OUT/'manifest.json')
    for name, digest in manifest['source_bindings'].items():
        if name.startswith(('src/', 'configs/')) and sha(ROOT/name)!=digest:
            raise ValueError('Frozen V2 source/config changed: '+name)
    config = read(data.OUT/'protocol.json')
    if config['pilot']['max_steps']!=200 or config['initial_adapter'] is not None or config['jev_requests']!=0:
        raise ValueError('Expected the frozen fresh-adapter 200-step local pilot')
    existing = run.out/'protocol.json'
    if existing.exists() and not resume:
        raise FileExistsError('Existing experiment; inspect progress and use --resume only for a paused/interrupted run')
    if resume and not existing.exists():
        raise FileNotFoundError('No prior experiment to resume')
    checkpoint = ROOT/config['base_checkpoint']
    protocol = dict(version='financial-eight-actions-pilot-execution-v1', run_name=run.name,
        config=config, dataset_manifest_sha256=sha(data.OUT/'manifest.json'),
        parent_manifest_sha256=sha(data.BASE/'manifest.json'),
        prompt_sha256=sha(ROOT/'src/qwenlab/financial_actions_prompt.py'),
        source_sha256={name:sha(ROOT/name) for name in SOURCES},
        model_files={p.relative_to(checkpoint).as_posix():sha(p) for p in sorted(checkpoint.iterdir()) if p.is_file()},
        packages={name:importlib.metadata.version(name) for name in PACKAGES},
        evaluation='development only; calibration and final never evaluated here',
        baseline_preparation='same NF4 and k-bit nonquantized FP32 preparation as candidate, without any adapter',
        inference='candidate projection with startup full-head verification, batch one; report any fallback',
        parameters='no argument parser or backend requests in this component experiment',
        training_loss='mean action CE + .75 times tool CE per true-tool row, divided by all sampled rows',
        selection='after both fixed checkpoints, passing highest macro-F1; ties joint tool then lower step',
        manual_pause='extra durable checkpoints allowed for interruption only, never selection',
        budget='200 optimizer updates; no automatic extension or vendor requests')
    if existing.exists():
        if read(existing)!=protocol:
            raise ValueError('Frozen execution/data/model/environment changed; preserve this run and use a new run-name')
    else:
        run.out.mkdir(parents=True, exist_ok=True)
        durable_json(existing, protocol)
    durable_json(ACTIVE, dict(run_name=run.name, output=run.out.relative_to(ROOT).as_posix()))
    return protocol


class GroupSampler:
    """Uniform nonempty action/profile stratum -> group -> row, with replacement."""
    def __init__(self, rows, seed):
        self.rng = random.Random(seed)
        self.pool = defaultdict(lambda:defaultdict(list))
        for index, row in enumerate(rows):
            self.pool[(row['action'], row['input']['capability_profile'])][row['group']].append(index)
        self.strata = sorted(self.pool)
        self.groups = {key:sorted(self.pool[key]) for key in self.strata}
        if not self.strata:
            raise ValueError('No training strata')

    def draw(self, n):
        result = []
        for _ in range(n):
            key = self.rng.choice(self.strata)
            group = self.rng.choice(self.groups[key])
            result.append(self.rng.choice(self.pool[key][group]))
        return result


def training_records():
    return [dict(id=r['id'], group=r['group'], input=json.loads(r['input']),
        action=r['action'], tool_name=r['tool_name']) for r in data.training_rows()]


def encode_example(tokenizer, row, task, target=None):
    inputs, keys, ids = prompts.encode(tokenizer, row, task)
    value = dict(tokens={k:v[0].tolist() for k,v in inputs.items()}, keys=keys, ids=ids,
        id=row['id'], task=task)
    if target is not None:
        value['target'] = keys.index(target)
    return value


def batch_scores(tokenizer, model, examples):
    padded = tokenizer.pad([x['tokens'] for x in examples], padding=True, return_tensors='pt').to('cuda')
    logits = model(**padded, logits_to_keep=1, use_cache=False).logits[:, -1].float()
    return [logits[i, x['ids']] for i,x in enumerate(examples)]


def task_prediction(tokenizer, scorer, row, task):
    import torch
    torch.cuda.synchronize(); started = time.perf_counter()
    inputs, keys, ids = prompts.encode(tokenizer, row, task)
    count = inputs.input_ids.shape[1]
    scores = scorer.scores(inputs.to('cuda'), ids)[0]
    if not torch.isfinite(scores).all():
        raise FloatingPointError('Non-finite model scores')
    probabilities = scores.softmax(-1).cpu().tolist()
    logits = scores.cpu().tolist()
    torch.cuda.synchronize()
    return dict(choice=keys[max(range(len(keys)), key=probabilities.__getitem__)],
        probabilities=dict(zip(keys,probabilities)), logits=logits,
        input_tokens=count, elapsed_s=time.perf_counter()-started)


def predict_request(tokenizer, scorer, row, predict_task=task_prediction):
    started = time.perf_counter()
    action = predict_task(tokenizer, scorer, row, 'action')
    value = dict(id=row['id'], action=action['choice'], tool_name=None,
        action_prediction=action, input_tokens=action['input_tokens'],
        action_elapsed_s=action['elapsed_s'], tool_elapsed_s=None)
    if value['action']=='tool':
        tool = predict_task(tokenizer, scorer, row, 'tool')
        value.update(tool_name=tool['choice'], tool_prediction=tool, tool_elapsed_s=tool['elapsed_s'])
    value['processed_input_tokens'] = value['input_tokens']+value.get('tool_prediction',{}).get('input_tokens',0)
    value['elapsed_s'] = time.perf_counter()-started
    return value


def evaluation_prefix(rows, done):
    if len(done)>len(rows) or [r['id'] for r in done]!=[r['id'] for r in rows[:len(done)]]:
        raise ValueError('Development predictions must be an exact, nonduplicated ordered prefix')


def pause_requested(run):
    return run.control.exists() and read(run.control).get('state')=='pause_requested'


class Paused(Exception):
    pass


def confirm_pause(run, stage, checkpoint=None):
    record = dict(state='paused', paused_at=now(), interrupted_stage=stage,
        checkpoint=checkpoint.relative_to(ROOT).as_posix() if checkpoint else None,
        protocol_sha256=run.protocol_hash(), worker_pid=os.getpid(), safe_to_shutdown=False)
    durable_json(run.control,record)
    run.status('paused', interrupted_stage=stage, checkpoint=record['checkpoint'])
    raise Paused()


@contextmanager
def inference_scorer(model):
    from qwenlab.candidate_inference import CandidateScorer
    model.eval()
    base = model.get_base_model() if hasattr(model,'get_base_model') else model
    original = base.lm_head
    try:
        yield CandidateScorer(model)
    finally:
        base.lm_head = original


def evaluation_binding(run, variant):
    checkpoint = None if variant=='base' else run.checkpoints/variant
    if checkpoint is not None:
        validate_checkpoint(run,checkpoint)
    return dict(protocol_sha256=run.protocol_hash(),variant=variant,
        checkpoint_sha256=None if checkpoint is None else sha(checkpoint/'checkpoint.json'),
        split_sha256=sha(data.OUT/'evaluation/development.json'))


def finalize_evaluation(run, variant, protocol, rows, done):
    """Recover interrupted output finalization from complete durable predictions."""
    evaluation_prefix(rows,done)
    if len(done)!=len(rows):
        raise ValueError('Cannot finalize incomplete development predictions')
    folder = run.out/variant
    if read(folder/'binding.json')!=evaluation_binding(run,variant):
        raise ValueError('Completed evaluation binding changed')
    report = metrics.evaluate(rows,done,protocol['prompt_sha256'],run.protocol_hash())
    timing = dict(action_p50_s=metrics.percentile([x['action_elapsed_s'] for x in done],.5),
        action_p95_s=metrics.percentile([x['action_elapsed_s'] for x in done],.95),
        request_p50_s=report['latency']['p50_s'],request_p95_s=report['latency']['p95_s'],
        conditional_tool_requests=sum(x['action']=='tool' for x in done),
        total_measured_s=sum(x['elapsed_s'] for x in done),
        projection_counts=dict(Counter(x['projection'] for x in done)),
        scope='384 serial development requests; tokenization, transfers and predicted conditional tool included; '
              'loading/warmup excluded. Action token count versus total processed tokens separate. No backend calls.')
    for name,value in [('metrics.json',report),('timing.json',timing)]:
        path = folder/name
        if path.exists() and read(path)!=value:
            raise ValueError('Completed output differs from raw predictions: '+name)
        if not path.exists(): durable_json(path,value)
    return report


def evaluate_development(run, tokenizer, model, variant, protocol):
    rows = data.evaluation_rows('development')
    folder = run.out/variant
    folder.mkdir(exist_ok=True)
    binding_path = folder/'binding.json'
    binding = evaluation_binding(run,variant)
    if binding_path.exists() and read(binding_path)!=binding:
        raise ValueError('Evaluation variant/source binding changed')
    if not binding_path.exists():
        durable_json(binding_path,binding)
    path = folder/'predictions.jsonl'
    done = rows_file(path)
    evaluation_prefix(rows,done)
    if len(done)==len(rows):
        return finalize_evaluation(run,variant,protocol,rows,done)
    if (folder/'metrics.json').exists():
        raise ValueError('Incomplete predictions with completed metrics')
    if pause_requested(run):
        confirm_pause(run,'evaluation')
    with inference_scorer(model) as scorer:
        # Warm both letter layouts before measured requests, no gold action at inference.
        task_prediction(tokenizer,scorer,rows[0],'action')
        task_prediction(tokenizer,scorer,rows[0],'tool')
        for i in range(protocol['config']['speed']['warmup_requests']):
            predict_request(tokenizer,scorer,rows[i%len(rows)])
        warmup = dict(at=now(), projection=scorer.projection, fallback=scorer.fallback_reason,
            warmup_requests=protocol['config']['speed']['warmup_requests'], component_layout_warmups=2)
        append(folder/'warmup-sessions.jsonl',warmup)
        started = time.perf_counter()
        for row in rows[len(done):]:
            if pause_requested(run):
                confirm_pause(run,'evaluation')
            prediction = predict_request(tokenizer,scorer,row)
            prediction.update(projection=scorer.projection, projection_fallback=scorer.fallback_reason,
                measured_at=now())
            append(path,prediction); done.append(prediction)
            if len(done)%10==0:
                run.status('evaluation',variant=variant,done=len(done),total=len(rows),
                    session_elapsed_s=time.perf_counter()-started)
        report = finalize_evaluation(run,variant,protocol,rows,done)
    return report


def encoded_training(run, tokenizer, records):
    target = run.cache/'encoded-train.json'
    meta_path = run.cache/'manifest.json'
    if meta_path.exists():
        meta = read(meta_path)
        if meta['protocol_sha256']!=run.protocol_hash() or meta['file_sha256']!=sha(target):
            raise ValueError('Token cache changed')
        encoded = read(target)
        if [r['action']['id'] for r in encoded]!=[r['id'] for r in records]:
            raise ValueError('Token cache IDs differ from training')
        return encoded
    encoded = []
    for i,row in enumerate(records):
        if pause_requested(run):
            confirm_pause(run,'encoding_training')
        encoded.append(dict(action=encode_example(tokenizer,row,'action',row['action']),
            tool=encode_example(tokenizer,row,'tool',row['tool_name']) if row['action']=='tool' else None))
        if (i+1)%200==0:
            run.status('encoding_training',done=i+1,total=len(records))
    durable_json(target,encoded)
    durable_json(meta_path,dict(protocol_sha256=run.protocol_hash(),file_sha256=sha(target),
        rows=len(records), tool_examples=sum(x['tool'] is not None for x in encoded),
        max_tokens=max(len(x[t]['tokens']['input_ids']) for x in encoded for t in ['action','tool'] if x[t])))
    return encoded


def validate_checkpoint(run, path):
    path = Path(path)
    if path.resolve().parent!=run.checkpoints.resolve():
        raise ValueError('Checkpoint outside this experiment')
    meta = read(path/'checkpoint.json')
    if path.name!=f"step-{meta['step']}" or meta['protocol_sha256']!=run.protocol_hash():
        raise ValueError('Checkpoint step/protocol mismatch')
    if set(meta['files'])!={'adapter_model.safetensors','adapter_config.json','training-state.pt'}:
        raise ValueError('Checkpoint inventory mismatch')
    if any(sha(path/name)!=digest for name,digest in meta['files'].items()):
        raise ValueError('Incomplete or changed checkpoint')
    return meta


def latest_checkpoint(run):
    paths = [p for p in run.checkpoints.glob('step-*') if p.is_dir() and p.name[5:].isdigit()]
    for path in paths:
        validate_checkpoint(run,path)
    return max(paths,key=lambda p:int(p.name[5:]),default=None)


def save_checkpoint(run, model, optimizer, sampler, step, summary):
    import torch
    from qwenlab.joint_v5 import rng_state
    run.checkpoints.mkdir(parents=True,exist_ok=True)
    final = run.checkpoints/f'step-{step}'
    if final.exists():
        validate_checkpoint(run,final)
        return final
    staging = run.checkpoints/f'.step-{step}-{time.time_ns()}.pending'
    if staging.resolve().parent!=run.checkpoints.resolve() or final.resolve().parent!=run.checkpoints.resolve():
        raise ValueError('Unsafe checkpoint paths')
    staging.mkdir()
    model.save_pretrained(staging,safe_serialization=True)
    config = read(staging/'adapter_config.json')
    config['base_model_name_or_path'] = 'Qwen/Qwen3-VL-2B-Instruct'
    durable_json(staging/'adapter_config.json',config)
    torch.save(dict(step=step,optimizer=optimizer.state_dict(),rng=rng_state(),
        sampler_rng=sampler.rng.getstate(),summary=summary,protocol_sha256=run.protocol_hash()),
        staging/'training-state.pt')
    names = ['adapter_model.safetensors','adapter_config.json','training-state.pt']
    for name in names:
        with (staging/name).open('r+b') as stream:
            stream.flush(); os.fsync(stream.fileno())
    durable_json(staging/'checkpoint.json',dict(step=step,protocol_sha256=run.protocol_hash(),
        files={name:sha(staging/name) for name in names}))
    staging.rename(final)
    validate_checkpoint(run,final)
    durable_json(run.out/'latest-checkpoint.json',dict(step=step,path=final.relative_to(ROOT).as_posix()))
    return final


def prepared_base(config, training=False):
    from qwenlab.modeling import load_model
    from peft import prepare_model_for_kbit_training
    tok,base = load_model(config['precision'])
    tok.padding_side = 'left'
    base = prepare_model_for_kbit_training(base,use_gradient_checkpointing=training,
        gradient_checkpointing_kwargs={'use_reentrant':False})
    return tok,base


def dtype_summary(model):
    counts = Counter()
    for name,param in model.named_parameters():
        counts[str(param.dtype)] += param.numel()
    return dict(counts)


def fresh_model(config, checkpoint=None):
    from peft import PeftModel,LoraConfig,get_peft_model
    tok,base = prepared_base(config,training=True)
    if checkpoint:
        model = PeftModel.from_pretrained(base,checkpoint,is_trainable=True)
    else:
        lora = config['lora']
        targets = [n for n,_ in base.named_modules() if '.language_model.' in n
            and any(n.endswith('.'+suffix) for suffix in lora['targets'])]
        if not targets: raise ValueError('Missing language adapter targets')
        model = get_peft_model(base,LoraConfig(r=lora['r'],lora_alpha=lora['alpha'],lora_dropout=lora['dropout'],
            target_modules=targets,bias='none',task_type='CAUSAL_LM'))
    params = [(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if not params or any('lora_' not in n or '.language_model.' not in n or 'visual' in n for n,p in params):
        raise ValueError('Only language LoRA parameters may train')
    return tok,model


def micro_backward(tokenizer, model, block, config):
    import torch
    pilot = config['pilot']
    action_items = [x['action'] for x in block]
    action_scores = batch_scores(tokenizer,model,action_items)
    action_loss = sum(torch.nn.functional.cross_entropy(score[None,:],torch.tensor([x['target']],device='cuda'))
        for score,x in zip(action_scores,action_items))/len(block)
    if not torch.isfinite(action_loss):
        raise FloatingPointError('Non-finite action loss')
    (action_loss*pilot['action_loss_weight']/pilot['gradient_accumulation']).backward()
    tool_items = [x['tool'] for x in block if x['tool']]
    tool_value = 0.
    if tool_items:
        scores = batch_scores(tokenizer,model,tool_items)
        # Divide by ALL rows in this microbatch, not just tool rows.
        tool_loss = sum(torch.nn.functional.cross_entropy(s[None,:],torch.tensor([x['target']],device='cuda'))
            for s,x in zip(scores,tool_items))/len(block)
        if not torch.isfinite(tool_loss):
            raise FloatingPointError('Non-finite tool loss')
        (tool_loss*pilot['tool_loss_weight']/pilot['gradient_accumulation']).backward()
        tool_value = float(tool_loss.detach())
    return float(action_loss.detach()),tool_value,len(tool_items)


def preflight(run, tokenizer, model, encoded, config):
    import torch
    from qwenlab.joint_v5 import rng_state, restore_rng
    saved_rng = rng_state()
    params = [p for p in model.parameters() if p.requires_grad]
    # Long action inputs + real tool examples exercise both tasks without eval labels.
    ordered = sorted(encoded,key=lambda x:len(x['action']['tokens']['input_ids']),reverse=True)
    tools = sorted([x for x in encoded if x['tool']],key=lambda x:len(x['tool']['tokens']['input_ids']),reverse=True)
    started = time.perf_counter()
    model.train(); model.zero_grad(set_to_none=True)
    torch.cuda.reset_peak_memory_stats()
    try:
        for block in [ordered[:config['pilot']['micro_batch']],tools[:config['pilot']['micro_batch']]]:
            micro_backward(tokenizer,model,block,config)
            if any(not torch.isfinite(p.grad).all() for p in params if p.grad is not None):
                raise FloatingPointError('Non-finite preflight gradient')
            model.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        value = dict(status='pass',no_optimizer_updates=True,elapsed_s=time.perf_counter()-started,
            max_action_tokens=max(len(x['action']['tokens']['input_ids']) for x in encoded),
            max_tool_tokens=max(len(x['tool']['tokens']['input_ids']) for x in tools),
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
            trainable_parameters=sum(p.numel() for p in params))
        durable_json(run.out/'preflight.json',value)
    finally:
        model.zero_grad(set_to_none=True); restore_rng(saved_rng)


def training(run, protocol, checkpoint):
    import numpy as np
    import torch
    from qwenlab.joint_v5 import rng_state, restore_rng
    cfg,pilot = protocol['config'],protocol['config']['pilot']
    random.seed(pilot['seed']); np.random.seed(pilot['seed']); torch.manual_seed(pilot['seed'])
    run.status('loading_training',resumed_checkpoint=checkpoint.name if checkpoint else None)
    tokenizer,model = fresh_model(cfg,checkpoint)
    durable_json(run.out/'candidate-parameter-dtypes.json',dtype_summary(model))
    records = training_records()
    encoded = encoded_training(run,tokenizer,records)
    sampler = GroupSampler(records,pilot['seed'])
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params,lr=pilot['learning_rate'],weight_decay=pilot['weight_decay'])
    summary = dict(optimizer_steps=0,sampled_by_id={},sampled_by_stratum={},sampled_tools={},
        unique_rows=0,sample_positions=0,training_elapsed_s=0.,status='training',
        dataset_rows=len(records),number_strata=len(sampler.strata),
        trainable_parameters=sum(p.numel() for p in params),max_steps=pilot['max_steps'])
    if checkpoint:
        validate_checkpoint(run,checkpoint)
        saved = torch.load(checkpoint/'training-state.pt',map_location='cpu',weights_only=False)
        if saved['protocol_sha256']!=run.protocol_hash():
            raise ValueError('Resume state protocol changed')
        summary = saved['summary']
        if summary['optimizer_steps']!=saved['step']:
            raise ValueError('Checkpoint summary step mismatch')
        optimizer.load_state_dict(saved['optimizer']); sampler.rng.setstate(saved['sampler_rng']); restore_rng(saved['rng'])
        logged = rows_file(run.out/'train.jsonl')
        if any(x['step']>saved['step'] for x in logged):
            # Preserve interrupted tail; never silently accept it as checkpointed work.
            durable_json(run.out/f'uncheckpointed-tail-{time.time_ns()}.json',[x for x in logged if x['step']>saved['step']])
            (run.out/'train.jsonl').write_bytes(''.join(json.dumps(x,ensure_ascii=False)+'\n'
                for x in logged if x['step']<=saved['step']).encode('utf-8'))
    else:
        if (run.out/'train.jsonl').exists():
            raise ValueError('Uncheckpointed training log exists; inspect instead of silently restarting')
        run.status('preflight')
        preflight(run,tokenizer,model,encoded,cfg)
    sampled = Counter(summary['sampled_by_id'])
    strata = Counter(summary['sampled_by_stratum'])
    sampled_tools = Counter(summary['sampled_tools'])
    # Resume at a selection checkpoint finishes its development evaluation first.
    if checkpoint and summary['optimizer_steps'] in pilot['checkpoint_steps']:
        before = rng_state()
        evaluate_development(run,tokenizer,model,checkpoint.name,protocol)
        restore_rng(before)
    torch.cuda.reset_peak_memory_stats()
    for step in range(summary['optimizer_steps']+1,pilot['max_steps']+1):
        if pause_requested(run):
            current = save_checkpoint(run,model,optimizer,sampler,step-1,summary)
            confirm_pause(run,'training',current)
        run.status('training',step=step-1,total_steps=pilot['max_steps'])
        model.train(); optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize(); started = time.perf_counter()
        warm = pilot['warmup_steps']
        scale = min(step/max(1,warm),(pilot['max_steps']-step+1)/max(1,pilot['max_steps']-warm))
        for group in optimizer.param_groups:
            group['lr'] = pilot['learning_rate']*scale
        action_loss,tool_loss,tool_count = 0.,0.,0
        for _ in range(pilot['gradient_accumulation']):
            indices = sampler.draw(pilot['micro_batch'])
            block = [encoded[i] for i in indices]
            a,t,n = micro_backward(tokenizer,model,block,cfg)
            action_loss += a/pilot['gradient_accumulation']; tool_loss += t/pilot['gradient_accumulation']; tool_count += n
            for index in indices:
                row = records[index]
                sampled[row['id']] += 1
                strata[row['action']+'|'+row['input']['capability_profile']] += 1
                if row['action']=='tool': sampled_tools[row['tool_name']] += 1
        norm = torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm):
            raise FloatingPointError('Non-finite training gradient')
        optimizer.step(); optimizer.zero_grad(set_to_none=True); torch.cuda.synchronize()
        elapsed = time.perf_counter()-started
        summary.update(optimizer_steps=step,sampled_by_id=dict(sampled),sampled_by_stratum=dict(strata),
            sampled_tools=dict(sampled_tools),unique_rows=len(sampled),sample_positions=sum(sampled.values()),
            training_elapsed_s=summary['training_elapsed_s']+elapsed,
            repeated_positions=sum(sampled.values())-len(sampled),
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
            peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30)
        append(run.out/'train.jsonl',dict(step=step,action_loss=action_loss,tool_loss_per_sampled_row=tool_loss,
            weighted_loss=action_loss*pilot['action_loss_weight']+tool_loss*pilot['tool_loss_weight'],
            true_tool_rows=tool_count,lr=optimizer.param_groups[0]['lr'],gradient_norm=float(norm),
            step_elapsed_s=elapsed,training_elapsed_s=summary['training_elapsed_s'],sample_positions=summary['sample_positions']))
        durable_json(run.out/'training-summary.json',summary)
        if step%10==0:
            print(json.dumps(dict(step=step,loss=action_loss+.75*tool_loss,step_seconds=elapsed,
                unique_rows=len(sampled)),ensure_ascii=False),flush=True)
        current = None
        if step in pilot['checkpoint_steps'] or pause_requested(run):
            run.status('saving_checkpoint',step=step,total_steps=pilot['max_steps'])
            current = save_checkpoint(run,model,optimizer,sampler,step,summary)
        if pause_requested(run):
            confirm_pause(run,'training',current)
        if step in pilot['checkpoint_steps']:
            before = rng_state()
            evaluate_development(run,tokenizer,model,current.name,protocol)
            restore_rng(before)
    summary['status'] = 'pilot_training_complete'
    durable_json(run.out/'training-summary.json',summary)


def select(run, protocol):
    variants = ['step-'+str(n) for n in protocol['config']['pilot']['checkpoint_steps']]
    # Recompute every report from exact raw predictions before selection.
    rows = data.evaluation_rows('development')
    def verified(variant):
        folder = run.out/variant
        return finalize_evaluation(run,variant,protocol,rows,rows_file(folder/'predictions.jsonl'))
    base = verified('base')
    candidates = {v:verified(v) for v in variants}
    gates = {v:metrics.development_gate(base,m,protocol['config']['development_gate']) for v,m in candidates.items()}
    passing = [v for v in variants if gates[v]['passed']]
    winner = max(passing,key=lambda v:(candidates[v]['macro_f1'],candidates[v]['action_tool_joint_accuracy'],
        -int(v.split('-')[1]))) if passing else None
    decision = dict(selected=winner,gates=gates,passed=bool(passing),usage='development_candidate_only',
        default_provider_changed=False,calibration_evaluated=False,final_evaluated=False,
        protocol_sha256=run.protocol_hash())
    durable_json(run.out/'selection.json',decision)
    return base,candidates,decision


def report(run, protocol):
    base,candidates,decision = select(run,protocol)
    table = []
    for variant,m in [('base',base)]+list(candidates.items()):
        timing = read(run.out/variant/'timing.json')
        table.append(dict(variant=variant,accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],
            human_misses=len(m['human_misses']),false_refusals=len(m['false_refusals']),
            unavailable_retrievals=len(m['unavailable_knowledge_retrievals']),
            joint_tool_accuracy=m['action_tool_joint_accuracy'],status_tool_accuracy=m['status_tool_accuracy'],
            action_p50_ms=timing['action_p50_s']*1000,request_p50_ms=timing['request_p50_s']*1000,
            request_p95_ms=timing['request_p95_s']*1000))
    durable_json(run.out/'comparison.json',dict(table=table,selection=decision,
        per_action={v:m['per_action'] for v,m in [('base',base)]+list(candidates.items())}))
    lines = ['# 金融八动作200步开发试训结果','',
        '仅开发384条，同NF4与非量化参数FP32准备的无适配器基线和新LoRA同输入/提示/协议。没有校准、最终、Jev或后端端到端成绩。','',
        '|版本|动作准确率|宏F1|人工漏判|误拒绝|不可用检索|动作+工具|状态工具|动作P50(ms)|请求P50(ms)|请求P95(ms)|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in table:
        lines.append(f"|{x['variant']}|{x['accuracy']:.2%}|{x['macro_f1']:.4f}|{x['human_misses']}|"
            f"{x['false_refusals']}|{x['unavailable_retrievals']}|{x['joint_tool_accuracy']:.2%}|"
            f"{x['status_tool_accuracy']:.2%}|{x['action_p50_ms']:.1f}|{x['request_p50_ms']:.1f}|{x['request_p95_ms']:.1f}|")
    lines += ['',f"开发候选：{decision['selected'] or '无候选通过，结束本预算'}。",'',
        '各候选未通过项：']+[f"- {v}: {', '.join(g['failures']) or '全部通过'}" for v,g in decision['gates'].items()]
    summary = read(run.out/'training-summary.json')
    lines += ['',f"实际抽样位置{summary['sample_positions']}，不同训练行{summary['unique_rows']}，重复位置{summary['repeated_positions']}。",
        f"优化器计算累计{summary['training_elapsed_s']/60:.1f}分钟，不包含加载、编码、预热与开发评估。",'',
        '过拟合不能仅凭训练损失降低判断。这里只能观察开发泛化与训练覆盖；开发已用于选择，不能代替最终独立检验。',
        '原始模型与适配器分不同时间段测量，受笔记本功耗、温度和桌面占用影响；请求P50/P95为探索结果，非交替重复硬件控制实验。',
        '动作+工具联合正确率以全部真实tool为分母；不以真实标签启动第二次推理。参数生成未测，后端保护未计入模型成绩。',
        '八个宏故事/分区、合成非人类金标、校准无历史仍限制真实用户泛化；不报告未计算的置信区间。',
        '合格时下一步固定候选做校准和最终一次对照；失败时记录原因，不自动延长预算或训练最终错题。']
    (run.out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    durable_json(run.out/'completion.json',dict(status='pilot_complete',at=now(),selection=decision,
        protocol_sha256=run.protocol_hash(),model_api_requests=0,deployed=False))
    run.status('pilot_complete',selected=decision['selected'],gates=decision['gates'])


def worker(run, resume=False):
    from qwenlab.joint_v5 import exclusive_lock
    with exclusive_lock('financial-eight-actions-gpu.lock'):
        old = read(run.control) if run.control.exists() else {}
        if old.get('state') in ['paused','pause_requested'] and not resume:
            raise RuntimeError('Manual pause must not be restarted without --resume')
        if (run.out/'completion.json').exists():
            raise FileExistsError('Completed pilot is immutable; inspect report instead of rerunning')
        if resume and old.get('state')=='pause_requested':
            raise RuntimeError('Pause is still pending; do not race a second worker')
        # Clear the OLD pause before publishing this worker's PID. After that,
        # never overwrite control unconditionally: a concurrent pause must win.
        if resume:
            durable_json(run.control,dict(state='resuming',at=now(),phase='validating',
                protocol_sha256=run.protocol_hash() if (run.out/'protocol.json').exists() else None))
        # Readiness/status becomes visible before potentially slow hashing.
        run.status('checking_protocol')
        protocol = freeze(run,resume)
        if pause_requested(run):
            confirm_pause(run,'checking_protocol',latest_checkpoint(run))
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU unavailable; no CPU fallback or automatic download')
        durable_json(run.out/'environment.json',dict(gpu=torch.cuda.get_device_name(),
            total_gpu_gib=torch.cuda.get_device_properties(0).total_memory/2**30,
            torch=torch.__version__,cuda=torch.version.cuda,at=now()))
        development = data.evaluation_rows('development')
        baseline_done = rows_file(run.out/'base/predictions.jsonl')
        evaluation_prefix(development,baseline_done)
        if len(baseline_done)==len(development):
            finalize_evaluation(run,'base',protocol,development,baseline_done)
        else:
            run.status('loading_baseline')
            tok,model = prepared_base(protocol['config'])
            durable_json(run.out/'base-parameter-dtypes.json',dtype_summary(model))
            evaluate_development(run,tok,model,'base',protocol)
            del tok,model; torch.cuda.empty_cache()
        if pause_requested(run):
            confirm_pause(run,'before_training')
        training(run,protocol,latest_checkpoint(run))
        run.status('reporting')
        report(run,protocol)


def is_worker_alive(status):
    import psutil
    try:
        process = psutil.Process(status['pid'])
        args = process.cmdline()
        return (abs(process.create_time()-status['process_created'])<.001
            and '-m' in args and 'qwenlab.financial_train' in args and 'run' in args
            and Path(process.cwd()).resolve()==ROOT.resolve())
    except (psutil.NoSuchProcess,psutil.AccessDenied,KeyError):
        return False


def progress(run):
    path = run.out/'status.json'
    if not path.exists():
        return dict(run_name=run.name,stage='not_started')
    value = read(path)
    value['worker_alive'] = is_worker_alive(value)
    logged = rows_file(run.out/'train.jsonl')
    if logged:
        step = logged[-1]['step']
        value.update(completed_optimizer_steps=step,total_optimizer_steps=200,
            training_percent=step/200*100,last_loss=logged[-1]['weighted_loss'])
        durations = [r['step_elapsed_s'] for r in logged[-20:]]
        seconds = metrics.percentile(durations,.5)
        value['seconds_per_step_recent_median'] = seconds
        remaining = (200-step)*seconds
        base_timing = run.out/'base/timing.json'
        if base_timing.exists():
            pending = sum(not (run.out/f'step-{n}/metrics.json').exists() for n in [100,200])
            remaining += pending*read(base_timing)['total_measured_s']
        value['rough_remaining_minutes_train_and_dev'] = round(remaining/60,1)
        value['estimate_scope'] = 'recent step median + baseline evaluation estimate; excludes saves/loading/pause; not a deadline'
    return value


def pause(run, wait=False):
    path = run.out/'status.json'
    status = read(path) if path.exists() else {}
    if not is_worker_alive(status):
        if run.control.exists() and read(run.control).get('state')=='paused':
            old = read(run.control)
            if old.get('checkpoint'): validate_checkpoint(run,ROOT/old['checkpoint'])
            old['safe_to_shutdown'] = True; durable_json(run.control,old)
            print('训练已暂停、检查点通过且进程已退出，可以正常关机。',flush=True)
            return
        raise RuntimeError('No confirmed active worker; inspect progress instead of claiming a safe pause')
    if status.get('stage') in TERMINAL:
        raise RuntimeError('Worker is completing/exiting; inspect progress before another control request')
    durable_json(run.control,dict(state='pause_requested',requested_at=now(),worker_pid=status['pid'],
        process_created=status['process_created'],safe_to_shutdown=False))
    print('暂停请求已提交；等待当前优化步/预测结束并保存。看到“可以正常关机”后再关闭电脑。',flush=True)
    if wait:
        started = time.monotonic()
        while is_worker_alive(status):
            if time.monotonic()-started>7200:
                raise TimeoutError('Pause confirmation timed out; no shutdown confirmation')
            time.sleep(2)
        control = read(run.control)
        if (run.out/'completion.json').exists() and read(run.out/'completion.json')['status']=='pilot_complete':
            checkpoint = latest_checkpoint(run)
            durable_json(run.control,dict(state='completed',safe_to_shutdown=True,at=now(),
                checkpoint=checkpoint.relative_to(ROOT).as_posix() if checkpoint else None))
            print('试训已完成且进程已退出，可以正常关机。',flush=True)
            return
        if control.get('state')!='paused':
            raise RuntimeError('Worker exited without successful pause; inspect error/state')
        if control.get('checkpoint'): validate_checkpoint(run,ROOT/control['checkpoint'])
        control['safe_to_shutdown'] = True; durable_json(run.control,control)
        print('暂停成功：进程已退出，完整检查点校验通过，可以正常关机。',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','progress','pause'])
    parser.add_argument('--run-name')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--wait',action='store_true')
    args = parser.parse_args()
    run = Run(active_name(args.run_name) if args.command!='run' or args.resume else args.run_name or DEFAULT)
    if args.command=='progress':
        while True:
            value = progress(run)
            print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)
            if not args.watch or value.get('stage') in TERMINAL|{'not_started'} or value.get('worker_alive') is False: break
            time.sleep(20)
    elif args.command=='pause':
        pause(run,args.wait)
    else:
        try:
            worker(run,args.resume)
        except Paused:
            print('Worker paused safely; pause command confirms process exit.',flush=True)
        except Exception as exc:
            # Never overwrite a live/finished run's status due to duplicate launch rejection.
            old = read(run.out/'status.json') if (run.out/'status.json').exists() else {}
            if old.get('pid')==os.getpid():
                run.status('failed',error_type=type(exc).__name__,error=str(exc))
            raise


if __name__=='__main__':
    main()
