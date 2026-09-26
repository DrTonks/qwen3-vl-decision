"""Publish reproducible aggregates and predictions without machine-specific paths."""
import argparse
import csv
import json
import shutil
from qwenlab.common import ROOT, sha
from qwenlab.summarize import summarize_file, paired_ci

def main():
    p=argparse.ArgumentParser(); p.add_argument('--runs',nargs='+',required=True)
    args=p.parse_args(); output=ROOT/'results/phase2'; output.mkdir(parents=True,exist_ok=True)
    metrics={}; rowsets={}; table=[]; mistakes=[]
    for run in args.runs:
        for path in sorted((ROOT/'results/runs'/run).glob('*-test.jsonl')):
            name=run+'/'+path.stem; result,rows=summarize_file(path); metrics[name]=result; rowsets[name]=rows
            result['source_sha256']=sha(path)
            if 'route' in result['tasks']:
                needed=[r for r in rows if r['labels']['route']=='tool']
                result['true_tool_required']={
                    'n':len(needed),
                    'joint_route_and_tool_correct':sum(not r.get('error') and r['predictions']['route']['choice']=='tool' and r['predictions']['tool']['choice']==r['labels']['tool'] for r in needed)}
            for row in rows:
                if row.get('error'): continue
                for task,pred in row['predictions'].items():
                    if pred['choice']!=row['labels'][task]:
                        mistakes.append({'run':run,'dataset':path.stem,'id':row['id'],'task':task,
                            'expected':row['labels'][task],'predicted':pred['choice'],
                            'confidence':max(pred.get('probabilities',{}).values(),default=None)})
            for task,value in result['tasks'].items():
                if not value['n']: continue
                value['accuracy_all_requests']=value['correct']/result['rows']
                table.append({'run':run,'dataset':path.stem,'task':task,'n':value['n'],'accuracy':value['accuracy'],
                    'macro_f1':value['macro_f1_gold_supported_classes'],'ece':value.get('ece_10_equal_width'),
                    'nll':value.get('nll'),'p50_s':result['latency_p50_s'],'p95_s':result['latency_p95_s']})
            target=output/'predictions'/run; target.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target/path.name)
        for filename in ('metadata.json','memory.json','temperatures.json','reused-results.json'):
            source=ROOT/'results/runs'/run/filename
            if source.exists():
                target=output/'provenance'/run; target.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target/filename)
    comparisons={}
    for dataset in ('massive','business','crosswoz'):
        ref='jev-v2/'+dataset+'-test'
        if ref not in rowsets: continue
        for run in args.runs:
            key=run+'/'+dataset+'-test'
            if key==ref or key not in rowsets: continue
            comparisons[key]={task:paired_ci(rowsets[key],rowsets[ref],task) for task in ('intent','route') if task in metrics[key]['tasks']}
    for dataset in ('massive','business','crosswoz'):
        left='qwen-qlora-v2/'+dataset+'-test'; right='qwen-nf4-v2/'+dataset+'-test'
        if left in rowsets and right in rowsets:
            comparisons['qlora-minus-nf4/'+dataset]={task:paired_ci(rowsets[left],rowsets[right],task) for task in ('intent','route') if task in metrics[left]['tasks']}
    (output/'metrics.json').write_text(json.dumps({'runs':metrics,'paired_comparisons':comparisons},ensure_ascii=False,indent=2),encoding='utf-8')
    with (output/'metrics.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0])); w.writeheader(); w.writerows(table)
    if mistakes:
        with (output/'mistakes.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(mistakes[0]));w.writeheader();w.writerows(mistakes)
    lines=['# 第二轮机器生成结果','','准确率按成功请求计算；失败数见 metrics.json，accuracy_all_requests 将失败算错。',
        '延迟为每条完整流程的热启动墙钟时间；API 含网络，本地不含模型加载。校准表复用原推理耗时，不是重新计时。','',
        '|运行|数据|任务|样本|准确率|宏 F1|P50 秒|P95 秒|','|---|---|---|---:|---:|---:|---:|---:|']
    for r in table:
        lines.append(f'|{r["run"]}|{r["dataset"]}|{r["task"]}|{r["n"]}|{r["accuracy"]:.2%}|{r["macro_f1"]:.3f}|{r["p50_s"]:.3f}|{r["p95_s"]:.3f}|')
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote results/phase2 metrics, predictions and provenance')

if __name__=='__main__': main()
