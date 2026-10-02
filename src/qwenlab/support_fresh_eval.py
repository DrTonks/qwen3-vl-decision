"""Score pre-frozen new synthetic episodes. Never train, select a model, or call Jev."""
import argparse
from datetime import datetime, timezone
import gc
import json
import os
import time
from qwenlab.common import ROOT, append_json, load_json, sha
from qwenlab.joint_v4 import metrics
from qwenlab.joint_v5 import atomic_json, exclusive_lock, predict_one, read_resumable_rows
from qwenlab.modeling import load_model
from qwenlab.prepare_v2 import read_rows
from qwenlab.support_curriculum import digest
from qwenlab import support_v8_observe as observation
from qwenlab.support_v8_observe_eval import validate_rows, VARIANTS
from qwenlab.support_v8_observe_report import paired, route_classes

DATA=ROOT/'data/support-fresh-holdout-v1'
OUT=ROOT/'results/support-fresh-v1'


def state(stage,**values):
    atomic_json(OUT/'status.json',{'stage':stage,'updated_at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),**values})


def prepare():
    observation.prepare()
    selection=load_json(observation.OUT/'selection.json')
    if selection['selected']!='step-2801': raise ValueError('Selected checkpoint changed')
    freeze=load_json(DATA/'freeze.json')
    for name,h in freeze['files'].items():
        if sha(DATA/name)!=h: raise ValueError('Frozen holdout changed: '+name)
    rows=read_rows(DATA/'cases.jsonl')
    if len(rows)!=128 or len({r['id'] for r in rows})!=128: raise ValueError('Holdout population changed')
    observation.verify_checkpoint(ROOT/VARIANTS['step-2801'],sha(observation.OUT/'protocol.json'))
    observation.verify_checkpoint(ROOT/VARIANTS['step-200'],sha(observation.PARENT/'protocol.json'))
    protocol={'holdout_freeze_sha256':sha(DATA/'freeze.json'),'selection_sha256':sha(observation.OUT/'selection.json'),
        'variants':VARIANTS,'adapter_hashes':{v:sha(ROOT/p/'adapter_model.safetensors') for v,p in VARIANTS.items() if p},
        'policy_sha256':sha(ROOT/'configs/decision-v5.json'),
        'source_hashes':{name:digest(ROOT/name) for name in ['src/qwenlab/support_fresh_eval.py','src/qwenlab/support_v8_observe_report.py','src/qwenlab/support_v8_observe_eval.py','src/qwenlab/summarize.py']},
        'precision':'nf4','batch':1,'tasks':['intent','route','tool'],'new_jev_calls':0,'no_training':True,
        'diagnostic_targets':{'candidate_route_accuracy':.95,'candidate_human_missed':0,'max_task_accuracy_drop_vs_200':.03},
        'target_limitation':'New scenario diagnostics, not deployment acceptance or Jev comparison',
        'author_seen_previous_experiments':True,'new_inputs_frozen_before_scoring':True,'external_blind_test':False}
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocol.json').exists() and load_json(OUT/'protocol.json')!=protocol: raise ValueError('Evaluation protocol changed')
    if not (OUT/'protocol.json').exists(): atomic_json(OUT/'protocol.json',protocol)
    return rows


def report(results):
    scores={v:metrics(r) for v,r in results.items()}
    selected='step-2801'
    comparisons={v:paired(r,results[selected]) for v,r in results.items() if v!=selected}
    classes={v:route_classes(r) for v,r in results.items()}
    source={r['id']:r for r in read_rows(DATA/'cases.jsonl')}
    errors=[]
    for row in results[selected]:
        wrong=[t for t in ['intent','route','tool'] if row['labels'][t]!=row['predictions'][t]['choice']]
        if wrong:
            errors.append({'input':source[row['id']],'wrong_tasks':wrong,'predictions':row['predictions']})
    atomic_json(OUT/'metrics.json',scores);atomic_json(OUT/'paired.json',comparisons)
    atomic_json(OUT/'route-classes.json',classes);atomic_json(OUT/'errors.json',errors)
    current=scores[selected];base=scores['step-200']
    checks={'route_at_least_95_percent':current['tasks']['route']['accuracy']>=.95,
        'zero_human_misses':current['human_missed']==0,
        **{f'{t}_no_more_than_3pp_drop_vs_200':current['tasks'][t]['accuracy']>=base['tasks'][t]['accuracy']-.03 for t in ['intent','route','tool']}}
    atomic_json(OUT/'diagnostics.json',checks)
    lines=['# 第2801步新增场景验证','',
        '128条/64个新增合成场景组，四路由各32条。模型和标签在评分前冻结，未使用本次错题训练；非真实用户数据，也非外部盲测。Jev未在这组数据上评分，不能移用旧79条成绩进行比较。','',
        '|模型|意图|路由|工具字段（含none）|三字段全对|转人工漏判|',
        '|---|---:|---:|---:|---:|---:|']
    for v,m in scores.items():
        lines.append(f"|{v}|{m['tasks']['intent']['accuracy']:.2%}|{m['tasks']['route']['accuracy']:.2%} ({m['tasks']['route']['correct']}/128)|{m['tasks']['tool']['accuracy']:.2%}|{m['all_fields_correct']}/128|{m['human_missed']}/{m['human_required']}|")
    lines += ['', '|对照→2801 路由|改对|改错|准确率变化pp|','|---|---:|---:|---:|']
    for v,c in comparisons.items(): lines.append(f"|{v}|{c['fixed']}|{c['regressed']}|{c['accuracy_delta']*100:+.2f}|")
    lines += ['', '|真实路由|样本数|2801召回率|','|---|---:|---:|']
    for k,c in classes[selected].items(): lines.append(f"|{k}|{c['support']}|{c['recall']:.2%}|")
    lines += ['', '诊断目标未满足项：'+str([k for k,v in checks.items() if not v]),'',
        '同组两条是措辞变体而非独立场景；新旧文本去重不能排除语义接近，作者已观察旧实验。标签独立agent复核不等于人工或外部专家标注。准确率受本套人工设计的类别比例影响，不能当真实服务流量准确率。',
        '本结果仅是模型三个分类字段；后端guard、参数归属校验、SQLite隔离工具和HTTP协议另行测试。新增错误仅用于评价边界，不直接或改写后回填训练。']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    state('complete',candidate=selected,failed_diagnostics=[k for k,v in checks.items() if not v],new_jev_calls=0)


def run():
    rows=prepare()
    if (OUT/'status.json').exists() and load_json(OUT/'status.json')['stage']=='complete': return
    results={}
    import torch
    for variant,adapter in VARIANTS.items():
        folder=OUT/variant;folder.mkdir(exist_ok=True)
        path=folder/'predictions.jsonl';done=read_resumable_rows(path);validate_rows(done,rows)
        if len(done)<len(rows):
            state('loading',variant=variant)
            tok,model=load_model('nf4',adapter);tok.padding_side='left';model.eval()
            for row in rows[len(done):]:
                result=predict_one(tok,model,row);append_json(path,result);done.append(result)
                if len(done)%8==0: state('evaluating',variant=variant,done=len(done),total=len(rows))
            del model,tok;gc.collect();torch.cuda.empty_cache()
        results[variant]=done
    report(results)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','progress']);a=p.parse_args()
    if a.action=='progress': print(json.dumps(load_json(OUT/'status.json') if (OUT/'status.json').exists() else {'stage':'not_started'},ensure_ascii=False,indent=2))
    elif a.action=='prepare':prepare()
    else:
        with exclusive_lock('support-fresh-eval.lock'),exclusive_lock('joint-v5-gpu.lock'):
            try:run()
            except BaseException as e:state('failed',error=type(e).__name__,message=str(e));raise


if __name__=='__main__':main()
