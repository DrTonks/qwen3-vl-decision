"""Deterministic metrics from saved predictions. Never reads credentials."""
import argparse
import json
import math
import csv
import random
from collections import Counter,defaultdict
from qwenlab.common import ROOT,load_rows

def percentile(values,p):
    if not values:return None
    a=sorted(values); x=(len(a)-1)*p; lo=int(x); hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(x-lo)
def wilson(correct,n):
    if not n:return None
    z=1.96; phat=correct/n; den=1+z*z/n
    mid=(phat+z*z/(2*n))/den
    half=z*math.sqrt(phat*(1-phat)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]
def metric(rows,task):
    usable=[r for r in rows if not r.get('error') and task in r['predictions']]
    pairs=[(r['labels'][task],r['predictions'][task]) for r in usable]
    n=len(pairs)
    if not n:return {'n':0}
    classes=sorted({y for y,_ in pairs}); correct=sum(y==p['choice'] for y,p in pairs)
    f1=[]
    for label in classes:
        tp=sum(y==label and p['choice']==label for y,p in pairs)
        fp=sum(y!=label and p['choice']==label for y,p in pairs)
        fn=sum(y==label and p['choice']!=label for y,p in pairs)
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    out={'n':n,'correct':correct,'accuracy':correct/n,'accuracy_wilson_95_descriptive':wilson(correct,n),
        'macro_f1_gold_supported_classes':sum(f1)/len(f1),'supported_classes':classes,
        'invalid':sum(p['choice']=='__invalid__' for _,p in pairs),
        'confusion':dict(Counter(y+' -> '+p['choice'] for y,p in pairs))}
    if all('probabilities' in p for _,p in pairs):
        bins=defaultdict(list); brier=[]; nll=[]
        for y,p in pairs:
            probs=p['probabilities']; total=sum(probs.values()); probs={k:v/total for k,v in probs.items()}
            brier.append(sum((v-(k==y))**2 for k,v in probs.items()))
            nll.append(-math.log(max(probs.get(y,0),1e-12)))
            confidence=max(probs.values()); bins[min(int(confidence*10),9)].append((confidence,float(y==p['choice'])))
        ece=sum(len(v)/n*abs(sum(x for x,_ in v)/len(v)-sum(y for _,y in v)/len(v)) for v in bins.values())
        out.update({'brier_multiclass_sum':sum(brier)/n,'nll':sum(nll)/n,'ece_10_equal_width':ece,
            'selective':{str(t):{'coverage':sum(max(p['probabilities'].values())>=t for _,p in pairs)/n,
                'accepted':sum(max(p['probabilities'].values())>=t for _,p in pairs),
                'errors':sum(max(p['probabilities'].values())>=t and y!=p['choice'] for y,p in pairs)} for t in (.5,.7,.9,.95)}})
    return out

def summarize_file(path):
    rows=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
    good=[r for r in rows if not r.get('error')]
    tasks=sorted({t for r in rows for t in r.get('labels',{})})
    out={'rows':len(rows),'successful':len(good),'errors':len(rows)-len(good),
        'tasks':{t:metric(rows,t) for t in tasks},'latency_p50_s':percentile([r['elapsed_s'] for r in good],.5),
        'latency_p95_s':percentile([r['elapsed_s'] for r in good],.95),
        'all_fields_correct':sum(all(r['labels'][k]==v['choice'] for k,v in r['predictions'].items()) for r in good),
        'usage_input_tokens':sum(r.get('usage',{}).get('input_tokens',0) for r in good),
        'usage_output_tokens':sum(r.get('usage',{}).get('output_tokens',0) for r in good)}
    if 'route' in tasks:
        human=[r for r in good if r['labels']['route']=='human']
        out['human_required']=len(human)
        out['human_route_missed']=sum(r['predictions']['route']['choice']!='human' for r in human)
        out['human_flag_missed']=sum(r['predictions']['needs_human']['choice']!='yes' for r in human)
        out['route_tool_inconsistent']=sum((r['predictions']['route']['choice']=='tool')!=(r['predictions']['tool']['choice']!='none') for r in good)
        out['route_human_inconsistent']=sum((r['predictions']['route']['choice']=='human')!=(r['predictions']['needs_human']['choice']=='yes') for r in good)
    return out,rows

def paired_ci(left,right,task):
    a={r['id']:r for r in left if not r.get('error')}; b={r['id']:r for r in right if not r.get('error')}
    groups=defaultdict(list)
    for key in sorted(a.keys()&b.keys()):
        ar,br=a[key],b[key]
        if task not in ar['labels']:continue
        groups[ar['group']].append(int(ar['predictions'][task]['choice']==ar['labels'][task])-int(br['predictions'][task]['choice']==br['labels'][task]))
    if not groups:return None
    rng=random.Random(20260926); keys=sorted(groups); boot=[]
    for _ in range(2000):
        values=[v for k in rng.choices(keys,k=len(keys)) for v in groups[k]]
        boot.append(sum(values)/len(values))
    values=[v for vs in groups.values() for v in vs]
    return {'n':len(values),'groups':len(keys),'accuracy_difference':sum(values)/len(values),'group_bootstrap_95':[percentile(boot,.025),percentile(boot,.975)]}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',default='baseline-v1'); args=p.parse_args()
    folder=ROOT/'results'/args.run; metrics={}; allrows={}; mistakes=[]
    for path in sorted(folder.glob('*.jsonl')):
        result,rows=summarize_file(path); metrics[path.stem]=result; allrows[path.stem]=rows
        for r in rows:
            if r.get('error'):continue
            for task,pred in r['predictions'].items():
                if pred['choice']!=r['labels'][task]:mistakes.append({'run':path.stem,'id':r['id'],'task':task,'expected':r['labels'][task],'predicted':pred['choice'],'confidence':max(pred.get('probabilities',{}).values(),default=None)})
    comparisons={}
    for dataset in ('business','massive'):
        left=f'qwen-first-{dataset}-test'; right=f'jev-{dataset}-test'
        if left in allrows and right in allrows:
            comparisons[dataset]={t:paired_ci(allrows[left],allrows[right],t) for t in ('intent','route') if t in metrics[left]['tasks']}
    (folder/'metrics.json').write_text(json.dumps({'runs':metrics,'paired_comparisons':comparisons},ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'mistakes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['run','id','task','expected','predicted','confidence']); writer.writeheader(); writer.writerows(mistakes)
    lines=['# 自动汇总','', '|实验|成功/总数|意图准确率|路由准确率|工具准确率|必须人工漏转|p50秒|p95秒|', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,m in metrics.items():
        def acc(k):return f"{m['tasks'][k]['accuracy']:.1%}" if k in m['tasks'] and m['tasks'][k]['n'] else '—'
        lines.append(f"|{name}|{m['successful']}/{m['rows']}|{acc('intent')}|{acc('route')}|{acc('tool')}|{m.get('human_route_missed','—')}/{m.get('human_required','—')}|{m['latency_p50_s'] or 0:.3f}|{m['latency_p95_s'] or 0:.3f}|")
    lines+=['','业务样本是助手编写、未人工复核的合成规则测试；公开样本是MASSIVE中文原始标签。两者不得混合计算总准确率。',
        '本地业务一条样本含4次独立前向/生成，Jev一条请求并行输出4个问题。延迟是当前串行实现的观测结果，并非模型架构公平速度结论。',
        'Wilson区间仅描述条目层面不确定性；同组表达相关，模型差异采用场景组bootstrap。',
        '工具准确率包含大量none，正式选型需另看混淆矩阵、工具必要场景及错误明细。',
        '首token置信度是候选归一化概率，生成式不提供可靠概率，因此不为生成式计算ECE/Brier。',
        '查看 metrics.json 获取混淆矩阵、Brier/NLL/ECE、选择性覆盖及配对差异；mistakes.csv 保存全部错误。']
    (folder/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:len(metrics)+4]))
if __name__=='__main__': main()
