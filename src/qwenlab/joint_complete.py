"""Local completion worker for the already-running GPU pipeline.

No scheduler, recurring job, remote publication or extra API requests.
Run once after joint_v4 run and joint_jev have been started.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from qwenlab.common import ROOT, load_json, sha
from qwenlab.joint_v4 import OUT, dump


def last_progress():
    path=OUT/'train.jsonl'
    if not path.exists(): return None
    # Writer may be between bytes: inspect only the last complete JSON record.
    for line in reversed(path.read_text(encoding='utf-8').splitlines()[-3:]):
        try: return json.loads(line)
        except json.JSONDecodeError: pass
    return None


def result_document():
    m=load_json(OUT/'metrics.json'); train=load_json(OUT/'training-summary.json'); selected=m['selected']
    best=m['runs'][selected+'/business']; base=m['runs']['base/business']; vendor=m['runs'].get('jev/business')
    lines=['# 第四轮运行结果','','状态：训练、开发选择、校准、挑战与迁移评估已完成。',
        '**业务集仍为未人工复核的合成数据，不代表产品准确率。**','',
        '完整的准确率、迁移短板、速度实验、校准和标签歧义说明见后续生成的 [效果与速度总表](09-效果与速度验证.md)。完整开发阅读顺序见 [导航](00-阅读导航.md)。','',
        f'开发集选择：`{selected}`。训练 {train["optimizer_steps"]} 步，{train["elapsed_s"]/3600:.2f} 小时，峰值分配显存 {train["peak_allocated_gib"]:.3f} GiB。',
        '完整训练遍历数：'+json.dumps(train['sampled'],ensure_ascii=False)+'。','',
        '|新合成挑战|基础模型|所选模型|Jev|','|---|---:|---:|---:|']
    for task,label in [('intent','意图'),('route','路由'),('tool','工具（含 none）')]:
        values=[f'{r["tasks"][task]["accuracy_all_requests"]:.2%}' if r else '未获得' for r in (base,best,vendor)]
        lines.append('|'+label+'|'+'|'.join(values)+'|')
    for field,total,label in [('joint_tool_correct','tool_required','真正需要工具时联合正确'),('human_missed','human_required','必须人工漏转')]:
        values=[f'{r[field]}/{r[total]}' if r else '未获得' for r in (base,best,vendor)]
        lines.append('|'+label+'|'+'|'.join(values)+'|')
    lines+=['','公共意图、旧业务 72 条与 CrossWOZ 的完整对照见 [机器汇总](../results/joint-v4/summary.md)。',
        '分组置信区间、校准和逐条错误见 [JSON 指标](../results/joint-v4/metrics.json) 与 [业务错例](../results/joint-v4/business-mistakes.json)。',
        '单请求延迟见各模型目录的 latency.json，使用逐任务单样本推理，未将批量平均时间当作请求延迟。','',
        '这轮只有一个种子、一轮完整遍历；四个检查点不是四种数据规模。未验证真实工具参数/执行和图像能力。',
        '下一步需结合错例、人工复核和新场景决定 8k/20k，不能仅凭合成挑战高分自动宣布接近 Jev 或发布到业务系统。']
    (ROOT/'docs/07-第四轮运行结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--log',default='.local/joint-v4-console-v2.txt'); p.add_argument('--max-hours',type=float,default=8)
    args=p.parse_args(); log=ROOT/args.log; start=time.monotonic()
    status={'status':'waiting','started_utc':datetime.now(timezone.utc).isoformat(),'scope':'local one-shot completion worker'}
    statusfile=OUT/'completion.json'
    if statusfile.exists() and load_json(statusfile).get('status')=='complete': raise FileExistsError('Completion already recorded')
    dump(statusfile,status)
    try:
        while True:
            text=log.read_text(encoding='utf-8-sig',errors='replace') if log.exists() else ''
            if 'Traceback (most recent call last)' in text: raise RuntimeError('GPU pipeline failed; inspect private log')
            progress=last_progress(); status['training_progress']=progress
            if progress:
                total=load_json(OUT/'training-summary.json')['total_steps']
                remaining=(total-progress['step'])*progress['elapsed_s']/max(1,progress['step'])
                (OUT/'status.md').write_text(f'# 第四轮当前进度\n\n训练 {progress["step"]}/{total} 步；已运行 {progress["elapsed_s"]/60:.1f} 分钟。\n\n'
                    f'按当前速度估计剩余训练 {remaining/60:.1f} 分钟，另需开发选择和完整评估时间。\n\n'
                    '后台本地流程会继续生成校准、对照指标和结果文档；状态不代表训练收益。\n',encoding='utf-8')
            dump(statusfile,status)
            if 'Completed local joint experiment' in text: break
            if time.monotonic()-start>args.max_hours*3600: raise TimeoutError('Completion wait exceeded budget; training is not terminated')
            time.sleep(30)
        status['status']='finalizing'; dump(statusfile,status)
        vendor=load_json(OUT/'jev/metadata.json')
        if vendor['status']!='complete': raise RuntimeError('Vendor reference incomplete')
        subprocess.run([sys.executable,'-m','qwenlab.joint_finalize','all'],cwd=ROOT,check=True)
        # Check source integrity and exact one-pass coverage before publishing.
        protocol=load_json(OUT/'protocol.json')
        if not all(sha(ROOT/k)==v for k,v in protocol['source_sha256'].items()): raise AssertionError('Protocol source changed')
        train=load_json(OUT/'training-summary.json')
        if train['status']!='complete' or train['sampled']!=train['examples']: raise AssertionError('Training coverage mismatch')
        result_document()
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','*.py','-v'],cwd=ROOT,check=True)
        (OUT/'status.md').write_text('# 第四轮当前进度\n\n训练和全部评估已完成。详见 summary.md、metrics.json 和 docs/07-第四轮运行结果.md。\n\n业务数据未人工复核，不代表生产验收通过。\n',encoding='utf-8')
        status.update(status='complete',finished_utc=datetime.now(timezone.utc).isoformat()); dump(statusfile,status)
        subprocess.run([sys.executable,'-m','qwenlab.publish','--export'],cwd=ROOT,check=True)
        print('Completed reports and publication audit/export',flush=True)
    except Exception as exc:
        status.update(status='failed',error=type(exc).__name__); dump(statusfile,status)
        (OUT/'status.md').write_text('# 第四轮当前进度\n\n后续流程未完成。错误类型：'+type(exc).__name__+'。检查 completion.json 和本地日志；不能将该状态视为实验成功。\n',encoding='utf-8')
        raise


if __name__=='__main__': main()
