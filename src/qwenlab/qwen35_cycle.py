"""Bounded two-epoch Qwen3.5 financial decision experiment with safe resume."""
import argparse,copy,gc,hashlib,importlib.metadata,json,math,os,random,time
from pathlib import Path
from collections import Counter
from qwenlab.common import ROOT,sha
from qwenlab import financial_train as ft,qwen35_model as qm

DEFAULT='financial-qwen35-v1'
CONFIG=ROOT/'configs/financial-qwen35-v1.json'
SOURCES=list(dict.fromkeys(ft.SOURCES+['src/qwenlab/qwen35_model.py','src/qwenlab/qwen35_cycle.py',
    'scripts/start-qwen35.ps1','scripts/pause-qwen35.ps1','scripts/resume-qwen35.ps1']))
TERMINAL={'complete','failed','paused'}


class Run(ft.Run):
    def __init__(self,name=DEFAULT):
        super().__init__(name)
        if not name.startswith('financial-qwen35-'):raise ValueError('Dedicated experiment namespace required')
        self.control=ROOT/'.local/qwen35'/f'{name}-control.json'


def freeze(run,resume):
    ft.data.validate()
    cfg=ft.read(CONFIG)
    if cfg['epochs']!=2 or cfg['model_api_requests']!=0:raise ValueError('Fixed two-epoch local budget')
    source=ft.read(ROOT/'configs/qwen35-model-source.json')
    for f in source['files']:
        if sha(qm.MODEL/f['Path'])!=f['Sha256']:raise ValueError('Model checksum mismatch')
    protocol=dict(config=cfg,dataset_manifest_sha256=sha(ft.data.OUT/'manifest.json'),
        parent_manifest_sha256=sha(ft.data.BASE/'manifest.json'),model_source_sha256=sha(ROOT/'configs/qwen35-model-source.json'),
        source_sha256={p:sha(ROOT/p) for p in SOURCES},packages={p:importlib.metadata.version(p) for p in ft.PACKAGES+['tokenizers','huggingface-hub','safetensors']},
        prompt_sha256=sha(ROOT/'src/qwenlab/qwen35_model.py'),run_name=run.name,
        selection='fixed development checkpoints; passing highest macroF1, then joint tool, then lower step',
        inference='non-thinking candidate letters; tool only after predicted tool; no arguments/backend',
        preparation='BF16 frozen base both sides; FP32 LoRA parameters for candidate; no NF4',
        sampling='two independently shuffled full coverage epochs, no additional synthetic data or evaluation replay')
    path=run.out/'protocol.json'
    if path.exists():
        if not resume:raise FileExistsError('Existing experiment requires explicit resume')
        if ft.read(path)!=protocol:raise ValueError('Frozen execution or dependencies changed')
    else:
        if resume:raise FileNotFoundError('Nothing to resume')
        ft.durable_json(path,protocol)
    return protocol


def epoch_order(count,seed,epoch):
    order=list(range(count));random.Random(seed+epoch).shuffle(order);return order


def checkpoint(run,model,optimizer,step,summary):
    import torch
    from qwenlab.joint_v5 import rng_state
    destination=run.checkpoints/f'step-{step}'
    if destination.exists():ft.validate_checkpoint(run,destination);return destination
    run.checkpoints.mkdir(parents=True,exist_ok=True)
    temporary=run.checkpoints/f'.step-{step}-{time.time_ns()}.pending';temporary.mkdir()
    model.save_pretrained(temporary,safe_serialization=True)
    cfg=ft.read(temporary/'adapter_config.json');cfg['base_model_name_or_path']='Qwen/Qwen3.5-0.8B'
    ft.durable_json(temporary/'adapter_config.json',cfg)
    torch.save(dict(step=step,optimizer=optimizer.state_dict(),rng=rng_state(),summary=summary,
        protocol_sha256=run.protocol_hash()),temporary/'training-state.pt')
    names=['adapter_model.safetensors','adapter_config.json','training-state.pt']
    for name in names:
        with (temporary/name).open('r+b') as stream:stream.flush();os.fsync(stream.fileno())
    ft.durable_json(temporary/'checkpoint.json',dict(step=step,protocol_sha256=run.protocol_hash(),
        files={name:sha(temporary/name) for name in names}))
    temporary.rename(destination);ft.validate_checkpoint(run,destination)
    ft.durable_json(run.out/'latest-checkpoint.json',dict(step=step,path=destination.relative_to(ROOT).as_posix()))
    return destination


def pause_check(run,stage,model=None,optimizer=None,step=None,summary=None):
    if ft.pause_requested(run):
        saved=checkpoint(run,model,optimizer,step,summary) if model is not None else ft.latest_checkpoint(run)
        ft.confirm_pause(run,stage,saved)


def task_prediction(tokenizer,scorer,row,task):
    import torch
    torch.cuda.synchronize();start=time.perf_counter()
    ex=qm.encode(tokenizer,row,task)
    inputs={k:torch.tensor([v],device='cuda') for k,v in ex['tokens'].items()}
    scores=scorer.scores(inputs,ex['ids'])[0]
    if not torch.isfinite(scores).all():raise FloatingPointError('Invalid prediction scores')
    probs=scores.softmax(-1).cpu().tolist();logits=scores.cpu().tolist();torch.cuda.synchronize()
    return dict(choice=ex['keys'][max(range(len(probs)),key=probs.__getitem__)],
        probabilities=dict(zip(ex['keys'],probs)),logits=logits,
        input_tokens=len(ex['tokens']['input_ids']),elapsed_s=time.perf_counter()-start)


def eval_binding(run,variant,split):
    ckpt=None if variant=='base' else run.checkpoints/variant
    if ckpt:ft.validate_checkpoint(run,ckpt)
    return dict(protocol_sha256=run.protocol_hash(),variant=variant,split=split,
        checkpoint_sha256=sha(ckpt/'checkpoint.json') if ckpt else None,
        split_sha256=sha(ft.data.OUT/f'evaluation/{split}.json'))


def evaluate(run,tok,model,variant,protocol,split='development'):
    import torch
    if split!='development':
        selected=ft.read(run.out/'selection.json')
        if not selected['passed'] or selected['protocol_sha256']!=run.protocol_hash():raise ValueError('No accepted fixed candidate')
        if variant not in ['base',selected['selected']]:raise ValueError('Only selected candidate may enter holdout')
        if split=='final' and not (run.out/'calibration-policy.json').exists():raise ValueError('Freeze calibration before final')
    rows=ft.data.evaluation_rows(split,allow_final=split=='final')
    folder=run.out/split/variant;folder.mkdir(parents=True,exist_ok=True)
    binding=eval_binding(run,variant,split);bp=folder/'binding.json'
    if bp.exists() and ft.read(bp)!=binding:raise ValueError('Evaluation binding changed')
    if not bp.exists():ft.durable_json(bp,binding)
    done=ft.rows_file(folder/'predictions.jsonl');ft.evaluation_prefix(rows,done)
    if len(done)<len(rows):
        with ft.inference_scorer(model) as scorer:
            for task in ['action','tool']:task_prediction(tok,scorer,rows[0],task)
            for row in rows[:10]:ft.predict_request(tok,scorer,row,task_prediction)
            for row in rows[len(done):]:
                pause_check(run,'evaluation')
                pred=ft.predict_request(tok,scorer,row,task_prediction)
                pred.update(projection=scorer.projection,projection_fallback=scorer.fallback_reason,measured_at=ft.now())
                done.append(pred);ft.append(folder/'predictions.jsonl',pred)
                if len(done)%16==0:run.status('evaluation',variant=variant,split=split,done=len(done),total=len(rows))
    report=ft.metrics.evaluate(rows,done,protocol['prompt_sha256'],run.protocol_hash())
    timing=dict(action_p50_s=ft.metrics.percentile([r['action_elapsed_s'] for r in done],.5),
        request_p50_s=ft.metrics.percentile([r['elapsed_s'] for r in done],.5),
        request_p95_s=ft.metrics.percentile([r['elapsed_s'] for r in done],.95),
        total_measured_s=sum(r['elapsed_s'] for r in done),conditional_tool_requests=sum(r['action']=='tool' for r in done),
        scope='serial; tokenization + transfers + action + predicted conditional tool; excludes loading/warmup; no backend')
    for name,value in [('metrics.json',report),('timing.json',timing)]:
        path=folder/name
        if path.exists() and ft.read(path)!=value:raise ValueError('Result differs from original predictions')
        if not path.exists():ft.durable_json(path,value)
    return report


def encode_training(run,tok,rows):
    path=run.cache/'encoded.json'
    if path.exists():
        saved=ft.read(path)
        if saved['protocol_sha256']!=run.protocol_hash():raise ValueError('Cache protocol mismatch')
        return saved['rows']
    encoded=[]
    for row in rows:
        encoded.append(dict(action=qm.encode(tok,row,'action',row['action']),
            tool=qm.encode(tok,row,'tool',row['tool_name']) if row['action']=='tool' else None))
    ft.durable_json(path,dict(protocol_sha256=run.protocol_hash(),rows=encoded))
    return encoded


def train(run,protocol):
    import torch
    import numpy as np
    from qwenlab.joint_v5 import rng_state,restore_rng
    cfg=protocol['config'];rows=ft.training_records();n=len(rows);b=cfg['effective_batch'];per_epoch=math.ceil(n/b)
    if n!=cfg['train_rows'] or per_epoch*cfg['epochs']!=cfg['max_steps']:raise ValueError('Coverage budget mismatch')
    torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed']);random.seed(cfg['seed']);np.random.seed(cfg['seed'])
    saved=ft.latest_checkpoint(run)
    tok,model=qm.load(training=True,checkpoint=saved)
    ft.durable_json(run.out/'candidate-parameter-dtypes.json',ft.dtype_summary(model))
    encoded=encode_training(run,tok,rows)
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=cfg['learning_rate'],weight_decay=.01)
    summary=dict(step=0,sampled_by_id={},sampled_tools={},training_elapsed_s=0.,sample_positions=0,
        trainable_parameters=sum(p.numel() for p in params),dataset_rows=n)
    if saved:
        state=torch.load(saved/'training-state.pt',map_location='cpu',weights_only=False)
        if state['protocol_sha256']!=run.protocol_hash():raise ValueError('Training state protocol mismatch')
        summary=state['summary'];optimizer.load_state_dict(state['optimizer']);restore_rng(state['rng'])
        logs=ft.rows_file(run.out/'train.jsonl')
        if any(r['step']>summary['step'] for r in logs):
            ft.durable_json(run.out/f'uncheckpointed-{time.time_ns()}.json',logs)
            (run.out/'train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in logs if r['step']<=summary['step']),encoding='utf-8')
    elif (run.out/'train.jsonl').exists():raise ValueError('Uncheckpointed training log; refuse silent reset')
    if not saved:
        ft.preflight(run,tok,model,encoded,dict(pilot=dict(micro_batch=cfg['micro_batch'],
            gradient_accumulation=cfg['effective_batch']/cfg['micro_batch'],action_loss_weight=1.,tool_loss_weight=.75)))
    committed=ft.rows_file(run.out/'train.jsonl')
    if [r['step'] for r in committed]!=list(range(1,summary['step']+1)):
        raise ValueError('Missing or duplicate committed training steps')
    if summary['step'] in cfg['checkpoint_steps']:
        state=rng_state();evaluate(run,tok,model,f"step-{summary['step']}",protocol);restore_rng(state)
    counts=Counter(summary['sampled_by_id']);tools=Counter(summary['sampled_tools'])
    orders=[epoch_order(n,cfg['seed'],e) for e in range(cfg['epochs'])]
    torch.cuda.reset_peak_memory_stats()
    for step in range(summary['step']+1,cfg['max_steps']+1):
        pause_check(run,'training',model,optimizer,step-1,summary)
        epoch=(step-1)//per_epoch;offset=((step-1)%per_epoch)*b;indices=orders[epoch][offset:offset+b]
        run.status('training',step=step-1,total_steps=cfg['max_steps'],epoch=epoch+1)
        model.train();optimizer.zero_grad(set_to_none=True)
        rate=cfg['learning_rate']*min(step/cfg['warmup_steps'],(cfg['max_steps']-step+1)/(cfg['max_steps']-cfg['warmup_steps']))
        for group in optimizer.param_groups:group['lr']=rate
        torch.cuda.synchronize();start=time.perf_counter();loss=0.;tool_count=0
        for pos in range(0,len(indices),cfg['micro_batch']):
            chosen=indices[pos:pos+cfg['micro_batch']];block=[encoded[i] for i in chosen]
            micro=dict(pilot=dict(action_loss_weight=1.,tool_loss_weight=.75,gradient_accumulation=len(indices)/len(chosen)))
            a,t,c=ft.micro_backward(tok,model,block,micro);loss+=(a+.75*t)*len(chosen)/len(indices);tool_count+=c
        norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite gradient')
        optimizer.step();optimizer.zero_grad(set_to_none=True);torch.cuda.synchronize();elapsed=time.perf_counter()-start
        for i in indices:
            counts[rows[i]['id']]+=1
            if rows[i]['action']=='tool':tools[rows[i]['tool_name']]+=1
        summary.update(step=step,epoch=epoch+1,sampled_by_id=dict(counts),sampled_tools=dict(tools),
            sample_positions=sum(counts.values()),unique_rows=len(counts),training_elapsed_s=summary['training_elapsed_s']+elapsed,
            peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30)
        ft.append(run.out/'train.jsonl',dict(step=step,epoch=epoch+1,loss=loss,lr=rate,true_tools=tool_count,
            elapsed_s=elapsed,gradient_norm=float(norm),sample_positions=summary['sample_positions'],unique_rows=len(counts)))
        ft.durable_json(run.out/'training-summary.json',summary)
        if step%25==0:print(json.dumps(dict(step=step,total=cfg['max_steps'],loss=loss,elapsed_s=elapsed)),flush=True)
        if step in cfg['checkpoint_steps'] or step%cfg['save_every_steps']==0 or ft.pause_requested(run):
            run.status('saving',step=step);checkpoint(run,model,optimizer,step,summary)
        pause_check(run,'training',model,optimizer,step,summary)
        if step in cfg['checkpoint_steps']:
            state=rng_state();evaluate(run,tok,model,f'step-{step}',protocol);restore_rng(state)
    if len(counts)!=n or set(counts.values())!={cfg['epochs']}:
        raise ValueError('Full epoch coverage failed')
    del model,optimizer;gc.collect();torch.cuda.empty_cache()


def select(run,protocol):
    variants=['step-'+str(s) for s in protocol['config']['checkpoint_steps']]
    reports={}
    for v in ['base']+variants:
        folder=run.out/'development'/v
        rows=ft.data.evaluation_rows('development')
        if ft.read(folder/'binding.json')!=eval_binding(run,v,'development'):raise ValueError('Result/checkpoint binding mismatch')
        report=ft.metrics.evaluate(rows,ft.rows_file(folder/'predictions.jsonl'),protocol['prompt_sha256'],run.protocol_hash())
        if ft.read(folder/'metrics.json')!=report:raise ValueError('Metrics mismatch')
        reports[v]=report
    gates={v:ft.metrics.development_gate(reports['base'],reports[v],protocol['config']['development_gate']) for v in variants}
    passing=[v for v in variants if gates[v]['passed']]
    winner=max(passing,key=lambda v:(reports[v]['macro_f1'],reports[v]['action_tool_joint_accuracy'],-int(v[5:]))) if passing else None
    decision=dict(selected=winner,passed=bool(passing),gates=gates,protocol_sha256=run.protocol_hash(),usage='development_selection_only')
    path=run.out/'selection.json'
    if path.exists() and ft.read(path)!=decision:raise ValueError('Selection changed')
    ft.durable_json(path,decision)
    return decision,reports


def temperature_probs(logits,temperature):
    values=[x/temperature for x in logits];maximum=max(values);weights=[math.exp(x-maximum) for x in values];total=sum(weights)
    return [x/total for x in weights]


def calibrate(run,protocol,variant):
    rows=ft.data.evaluation_rows('calibration')
    predictions=ft.rows_file(run.out/'calibration'/variant/'predictions.jsonl');lookup={r['id']:r for r in rows}
    ft.metrics.evaluate(rows,predictions,protocol['prompt_sha256'],run.protocol_hash())
    candidates=protocol['config']['calibration']['temperatures']
    nll={t:-sum(math.log(max(temperature_probs(p['action_prediction']['logits'],t)[ft.prompts.ACTIONS.index(lookup[p['id']]['annotation']['action'])],1e-12)) for p in predictions)/len(rows) for t in candidates}
    temperature=min(candidates,key=lambda t:(nll[t],abs(t-1)))
    options=[]
    for threshold in protocol['config']['calibration']['thresholds']:
        kept=[p for p in predictions if max(temperature_probs(p['action_prediction']['logits'],temperature))>=threshold]
        correct=sum(p['action']==lookup[p['id']]['annotation']['action'] for p in kept)
        harmful=sum((lookup[p['id']]['annotation']['action']=='human' and p['action']!='human') or
            (lookup[p['id']]['annotation']['action']!='refuse' and p['action']=='refuse') or
            (p['action']=='retrieve' and not lookup[p['id']]['input']['capabilities']['knowledge_collections']) for p in kept)
        options.append(dict(threshold=threshold,accepted=len(kept),accuracy=correct/len(kept) if kept else None,harmful=harmful))
    valid=[o for o in options if o['accepted'] and o['accuracy']>=.95 and o['harmful']==0]
    chosen=max(valid,key=lambda o:(o['accepted'],-o['threshold'])) if valid else dict(threshold=1.01,accepted=0,accuracy=None,harmful=0)
    result=dict(protocol_sha256=run.protocol_hash(),variant=variant,temperature=temperature,**chosen,
        options=options,nll_by_temperature=nll,scope='action confidence only; defer is unexecuted fallback, not a correct answer',
        calibration_predictions_sha256=sha(run.out/'calibration'/variant/'predictions.jsonl'))
    path=run.out/'calibration-policy.json'
    if path.exists() and ft.read(path)!=json.loads(json.dumps(result)):raise ValueError('Frozen calibration policy changed')
    ft.durable_json(path,result);return result


def holdout(run,protocol,selected):
    import torch
    variant=selected['selected'];tok,model=qm.load(checkpoint=run.checkpoints/variant)
    evaluate(run,tok,model,variant,protocol,'calibration');policy=calibrate(run,protocol,variant)
    evaluate(run,tok,model,variant,protocol,'final')
    del model;gc.collect();torch.cuda.empty_cache()
    tok,model=qm.load();evaluate(run,tok,model,'base',protocol,'final')
    del model;gc.collect();torch.cuda.empty_cache()
    rows=ft.data.evaluation_rows('final',allow_final=True);pred=ft.rows_file(run.out/'final'/variant/'predictions.jsonl')
    kept={p['id'] for p in pred if max(temperature_probs(p['action_prediction']['logits'],policy['temperature']))>=policy['threshold']}
    ft.durable_json(run.out/'final/selective-summary.json',dict(coverage=len(kept)/len(rows),deferred=len(rows)-len(kept),
        accepted_metrics=ft.metrics.evaluate([r for r in rows if r['id'] in kept],[p for p in pred if p['id'] in kept],
            protocol['prompt_sha256'],run.protocol_hash()) if kept else None,
        note='Selective subset, denominator differs from full final; no fallback API was executed.',policy_sha256=sha(run.out/'calibration-policy.json')))


def report(run,decision,reports):
    table=[]
    for v,m in reports.items():
        timing=ft.read(run.out/'development'/v/'timing.json')
        table.append(dict(variant=v,accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],joint=m['action_tool_joint_accuracy'],
            human_misses=len(m['human_misses']),false_refusals=len(m['false_refusals']),unavailable_retrievals=len(m['unavailable_knowledge_retrievals']),
            request_p50_ms=timing['request_p50_s']*1000,request_p95_ms=timing['request_p95_s']*1000))
    ft.durable_json(run.out/'comparison.json',dict(development=table,selection=decision))
    lines=['# Qwen3.5-0.8B 金融决策完整实验','',
        '|版本|开发动作准确率|宏F1|动作+工具|人工漏判|误拒绝|不可用检索|请求P50毫秒|请求P95毫秒|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t in table:lines.append(f"|{t['variant']}|{t['accuracy']:.2%}|{t['macro_f1']:.4f}|{t['joint']:.2%}|{t['human_misses']}|{t['false_refusals']}|{t['unavailable_retrievals']}|{t['request_p50_ms']:.1f}|{t['request_p95_ms']:.1f}|")
    lines+=['',f"开发门槛通过：{decision['passed']}；选中：{decision['selected']}。",
        '原始0.8B与候选同BF16准备、同消息内容和关闭思考模板。旧2B为NF4/不同架构和采样协议，历史分数不证明模型大小的因果效应。',
        '只有8个合成开发宏故事；开发选型不能排除过拟合，不能等同真实业务验收。',
        '工具名仅在模型预测tool后判断；参数、数据库、知识检索和人工接通未实测。',
        '所有速度为本机串行分阶段实测，受功耗与桌面负载影响；无Jev调用，无默认服务切换。']
    if decision['passed']:
        for v in ['base',decision['selected']]:
            m=ft.read(run.out/'final'/v/'metrics.json')
            lines.append(f"最终512条 {v}：动作{m['action_accuracy']:.2%}，宏F1 {m['macro_f1']:.4f}，工具联合{m['action_tool_joint_accuracy']:.2%}；这是固定候选一次最终结果。")
        lines.append('校准温度/兜底策略另见calibration-policy.json，选择性覆盖与最终全量指标分开报告。')
    else:lines.append('无候选通过，结束本预算；校准/最终未运行，不追加训练。')
    (run.out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    ft.durable_json(run.out/'completion.json',dict(status='complete',at=ft.now(),protocol_sha256=run.protocol_hash(),selection=decision,
        calibration_evaluated=decision['passed'],final_evaluated=decision['passed'],model_api_requests=0,deployed=False))


def worker(run,resume):
    from qwenlab.joint_v5 import exclusive_lock
    with exclusive_lock('financial-eight-actions-gpu.lock'):
        if (run.out/'completion.json').exists():raise FileExistsError('Completed experiment is immutable')
        control=ft.read(run.control) if run.control.exists() else {}
        if control.get('state')=='pause_requested':raise RuntimeError('Pause still pending')
        if control.get('state')=='paused' and not resume:raise RuntimeError('Explicit resume required')
        if resume:ft.durable_json(run.control,dict(state='resuming',at=ft.now()))
        run.status('checking_protocol');protocol=freeze(run,resume);pause_check(run,'checking_protocol')
        import torch
        ft.durable_json(run.out/'hardware.json',dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__,cuda=torch.version.cuda))
        if not (run.out/'development/base/metrics.json').exists():
            run.status('loading_baseline');tok,model=qm.load()
            ft.durable_json(run.out/'base-parameter-dtypes.json',ft.dtype_summary(model))
            evaluate(run,tok,model,'base',protocol)
            del model;gc.collect();torch.cuda.empty_cache()
        train(run,protocol);decision,reports=select(run,protocol)
        if decision['passed']:holdout(run,protocol,decision)
        report(run,decision,reports);run.status('complete',selected=decision['selected'],passed=decision['passed'])


def alive(status):
    import psutil
    try:
        p=psutil.Process(status['pid']);args=p.cmdline()
        return abs(p.create_time()-status['process_created'])<.001 and 'qwenlab.qwen35_cycle' in args and 'run' in args and Path(p.cwd()).resolve()==ROOT.resolve()
    except (KeyError,psutil.NoSuchProcess,psutil.AccessDenied):return False


def progress(run):
    if not (run.out/'status.json').exists():return dict(stage='not_started',run_name=run.name)
    value=ft.read(run.out/'status.json');value['worker_alive']=alive(value)
    logs=ft.rows_file(run.out/'train.jsonl')
    if logs:
        total=ft.read(run.out/'protocol.json')['config']['max_steps'];step=logs[-1]['step']
        seconds=ft.metrics.percentile([r['elapsed_s'] for r in logs[-30:]],.5)
        value.update(step=step,total_steps=total,percent=round(step/total*100,2),recent_step_median_s=round(seconds,3),
            remaining_train_minutes_estimate=round((total-step)*seconds/60,1),unique_rows=logs[-1]['unique_rows'],
            estimate_scope='training only; excludes pending evaluation, saving, loading and future hardware fluctuation')
    return value


def pause(run):
    status=ft.read(run.out/'status.json')
    if not alive(status):
        control=ft.read(run.control) if run.control.exists() else {}
        if control.get('state')!='paused' and status.get('stage')!='complete':raise RuntimeError('No confirmed worker or safe pause')
    else:
        ft.durable_json(run.control,dict(state='pause_requested',at=ft.now(),safe_to_shutdown=False))
        print('等待当前步骤结束、保存并退出；确认后再关机。',flush=True)
        while alive(status):time.sleep(2)
        latest=ft.read(run.out/'status.json')
        if latest.get('stage') not in ['paused','complete']:raise RuntimeError('Worker exited without safe confirmation')
    ckpt=ft.latest_checkpoint(run)
    if ckpt:ft.validate_checkpoint(run,ckpt)
    ft.durable_json(run.control,dict(state='paused' if ft.read(run.out/'status.json')['stage']!='complete' else 'complete',
        safe_to_shutdown=True,checkpoint=ckpt.relative_to(ROOT).as_posix() if ckpt else None))
    print('已确认进程退出、检查点完整，可以正常关机。',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','progress','pause']);p.add_argument('--run-name',default=DEFAULT)
    p.add_argument('--resume',action='store_true');p.add_argument('--watch',action='store_true');args=p.parse_args();run=Run(args.run_name)
    if args.command=='progress':
        while True:
            value=progress(run);print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)
            if not args.watch or value.get('stage') in TERMINAL|{'not_started'} or not value.get('worker_alive'):break
            time.sleep(20)
    elif args.command=='pause':pause(run)
    else:
        try:worker(run,args.resume)
        except ft.Paused:print('已保存并退出训练；暂停命令将确认安全关机。',flush=True)
        except Exception as e:
            status=ft.read(run.out/'status.json') if (run.out/'status.json').exists() else {}
            if status.get('pid')==os.getpid():run.status('failed',error_type=type(e).__name__,error=str(e))
            raise


if __name__=='__main__':main()
