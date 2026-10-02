"""External pause/resume control; never changes the frozen V8 training protocol."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import psutil
from qwenlab.common import ROOT, load_json, sha
from qwenlab.joint_v5 import atomic_json, exclusive_lock

OUT=ROOT/'results/support-v8'
CKPT=ROOT/'.local/checkpoints/support-v8'
CONTROL=ROOT/'.local/support-v8-pause.json'
MODULES={'qwenlab.support_v8_cycle':'cycle','qwenlab.support_train_v8':'train',
         'qwenlab.support_v8_finalize':'finalize'}


def write_state(stage, **values):
    atomic_json(CONTROL,{'state':stage,'updated_at':datetime.now(timezone.utc).isoformat(),**values})


def module_role(args):
    if '-m' not in args: return None
    i=args.index('-m')
    if len(args)<=i+1: return None
    module=args[i+1]
    if module=='qwenlab.support_train_v8' and (len(args)<=i+2 or args[i+2]!='run'): return None
    return MODULES.get(module)


def discover():
    records=[]
    for process in psutil.process_iter(['pid','name']):
        if 'python' not in (process.info['name'] or '').lower(): continue
        try:
            role=module_role(process.cmdline())
            if role and Path(process.cwd()).resolve()==ROOT.resolve():
                records.append({'pid':process.pid,'ppid':process.ppid(),'created':process.create_time(),'role':role})
        except (psutil.NoSuchProcess,psutil.AccessDenied): continue
    if records:
        ids={r['pid'] for r in records}
        if sum(r['ppid'] not in ids for r in records)!=1:
            raise RuntimeError('More than one process tree; refusing to stop ambiguous targets')
    return records


def same_process(record):
    try:
        p=psutil.Process(record['pid'])
        return (abs(p.create_time()-record['created'])<.001 and module_role(p.cmdline())==record['role']
                and Path(p.cwd()).resolve()==ROOT.resolve())
    except psutil.NoSuchProcess: return False


def latest():
    paths=[p for p in CKPT.glob('step-*') if p.is_dir() and p.name[5:].isdigit()]
    return max(paths,key=lambda p:int(p.name[5:]),default=None)


def verify_checkpoint(path, durable=False):
    path=Path(path).resolve()
    if path.parent!=CKPT.resolve() or not path.name.startswith('step-'):
        raise ValueError('Checkpoint outside V8 directory')
    meta=load_json(path/'checkpoint.json')
    expected={'adapter_model.safetensors','adapter_config.json','training-state.pt'}
    if set(meta['files'])!=expected or path.name!=f'step-{meta["step"]}':
        raise ValueError('Invalid checkpoint manifest')
    if meta['protocol_sha256']!=sha(OUT/'protocol.json'):
        raise ValueError('Checkpoint protocol changed')
    for name,digest in meta['files'].items():
        if sha(path/name)!=digest: raise ValueError('Checkpoint failed integrity: '+name)
    teacher=ROOT/'.local/cache/support-v8-teacher'
    teacher_meta=load_json(teacher/'manifest.json')
    if teacher_meta['protocol_sha256']!=meta['protocol_sha256'] or sha(teacher/'logits.jsonl')!=teacher_meta['logits_sha256']:
        raise ValueError('Teacher cache failed integrity')
    if durable:
        for p in [*(path/n for n in expected),path/'checkpoint.json',teacher/'manifest.json',teacher/'logits.jsonl',teacher/'identity.json',OUT/'protocol.json']:
            with p.open('r+b') as stream:
                stream.flush(); os.fsync(stream.fileno())
    return meta


def last_logged_step(lines, fallback):
    for i in range(len(lines)-1,-1,-1):
        if not lines[i].strip(): continue
        try: return json.loads(lines[i])['step']
        except json.JSONDecodeError:
            if i!=len(lines)-1: raise
    return fallback


def pause(immediate=False):
    records=discover()
    if not any(r['role']=='train' for r in records):
        old=load_json(CONTROL) if CONTROL.exists() else {}
        if not records and old.get('state')=='paused':
            verify_checkpoint(ROOT/old['checkpoint'],durable=True)
            print('已经暂停，检查点完好，可以正常关闭电脑。',flush=True)
            return
        raise RuntimeError('No active V8 training process; inspect progress before shutdown')
    initial=latest()
    if initial is None: raise RuntimeError('No completed checkpoint yet; cannot pause safely')
    initial_step=verify_checkpoint(initial)['step']
    write_state('waiting_checkpoint',requested_at=datetime.now(timezone.utc).isoformat(),
                after_step=initial_step,processes=records,automatic_restart_allowed=False)
    print(f'正在等待完整检查点（当前保存到第 {initial_step} 步）。通常不超过约10分钟；看到“可以关机”后再关闭电脑。',flush=True)
    started=time.monotonic(); last_report=0
    while True:
        if not any(same_process(r) for r in records if r['role']=='train'):
            raise RuntimeError('Training exited before controlled pause; inspect status')
        checkpoint=latest()
        if checkpoint and (immediate or int(checkpoint.name[5:])>initial_step):
            meta=verify_checkpoint(checkpoint,durable=True)
            # Stop the cycle supervisor first so it cannot start final evaluation.
            for record in sorted(records,key=lambda r:r['role']!='cycle'):
                if same_process(record): psutil.Process(record['pid']).terminate()
            until=time.monotonic()+30
            while any(same_process(r) for r in records) and time.monotonic()<until:
                time.sleep(.2)
            if any(same_process(r) for r in records): raise RuntimeError('A training process did not exit')
            if discover():
                raise RuntimeError('A new V8 process is active; shutdown is NOT confirmed')
            verify_checkpoint(checkpoint,durable=True)
            logs=(OUT/'train.jsonl').read_text(encoding='utf-8').splitlines()
            last=last_logged_step(logs,meta['step'])
            write_state('paused',checkpoint=checkpoint.relative_to(ROOT).as_posix(),step=meta['step'],
                        protocol_sha256=meta['protocol_sha256'],processes=records,
                        completed_steps_to_replay=max(0,last-meta['step']),safe_to_shutdown=True,
                        automatic_restart_allowed=False)
            # Also persist the small external-control record before confirming.
            with CONTROL.open('r+b') as stream: stream.flush(); os.fsync(stream.fileno())
            print(f'暂停成功：第 {meta["step"]} 步检查点校验通过，训练进程已全部退出。可以正常关机。',flush=True)
            print('明早恢复：& .\\scripts\\resume-support-v8.ps1',flush=True)
            return
        if time.monotonic()-started>last_report+30:
            last_report=time.monotonic()-started
            print(f'仍在等待下一完整检查点，已等待 {int(last_report)} 秒。',flush=True)
        time.sleep(2)


def resume_check():
    if discover(): raise RuntimeError('V8 process already running; will not start a duplicate')
    state=load_json(CONTROL) if CONTROL.exists() else {}
    if state.get('state') not in ('paused','resuming'):
        raise RuntimeError('Not a confirmed manual pause; inspect before resuming')
    checkpoint=ROOT/state['checkpoint']
    meta=verify_checkpoint(checkpoint)
    if latest().resolve()!=checkpoint.resolve(): raise ValueError('Latest checkpoint changed since pause')
    write_state('resuming',checkpoint=state['checkpoint'],step=meta['step'],
                resume_authorized_by_command=True,automatic_restart_allowed=True)
    print(f'第 {meta["step"]} 步检查点与教师缓存校验通过，准备继续。',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['pause','resume-check','status','check'])
    parser.add_argument('--immediate',action='store_true')
    args=parser.parse_args()
    if args.action=='status':
        control=load_json(CONTROL) if CONTROL.exists() else {'state':'not_requested'}
        print(json.dumps(control,ensure_ascii=False,indent=2))
        return
    with exclusive_lock('support-v8-control.lock'):
        if args.action=='check':
            p=latest()
            if p is None: raise RuntimeError('No checkpoint')
            meta=verify_checkpoint(p)
            print(json.dumps({'checkpoint_step':meta['step'],'processes':discover(),'changes_made':False},ensure_ascii=False,indent=2))
        elif args.action=='resume-check': resume_check()
        else:
            try: pause(args.immediate)
            except KeyboardInterrupt:
                write_state('cancelled',automatic_restart_allowed=False)
                print('暂停请求已取消；请查看训练进程状态，不要据此关机。',flush=True)
                raise
            except Exception as exc:
                old=load_json(CONTROL) if CONTROL.exists() else {}
                write_state('pause_failed',previous=old,error=type(exc).__name__,automatic_restart_allowed=False)
                raise


if __name__=='__main__': main()
