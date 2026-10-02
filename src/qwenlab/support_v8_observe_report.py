"""Reproducible paired comparisons and Markdown report for the fixed V8 candidate."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import random
from qwenlab.common import ROOT, load_json, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows
from qwenlab.summarize import percentile
from qwenlab.support_v8_observe_eval import OUT, CACHE, SELECTED

LABELS={'base':'原始Qwen','v5-reference':'V5','step-200':'V8 / 200步',SELECTED:'V8 / 2801步','jev':'Jev（历史）'}


def paired(left,right,task='route',repeats=10000):
    if [(x['id'],x['group'],x['labels']) for x in left]!=[(x['id'],x['group'],x['labels']) for x in right]:
        raise ValueError('Paired populations differ')
    counts=Counter(); groups=defaultdict(lambda:[0,0]); transitions=Counter()
    for a,b in zip(left,right):
        gold=a['labels'][task]
        old=a['predictions'][task]['choice']; new=b['predictions'][task]['choice']
        good_old=old==gold; good_new=new==gold
        key=('both_correct' if good_old and good_new else 'fixed' if good_new else 'regressed' if good_old else 'both_wrong')
        counts[key]+=1
        groups[a['group']][0]+=int(good_new)-int(good_old)
        groups[a['group']][1]+=1
        if old!=new: transitions[f'{gold}: {old} -> {new}']+=1
    rng=random.Random(20260929); units=list(groups.values()); draws=[]
    for _ in range(repeats):
        chosen=[units[rng.randrange(len(units))] for _ in units]
        draws.append(sum(x[0] for x in chosen)/sum(x[1] for x in chosen))
    return {'n':len(left),'groups':len(groups),**{k:counts[k] for k in ['both_correct','fixed','regressed','both_wrong']},
            'accuracy_delta':(counts['fixed']-counts['regressed'])/len(left),
            'group_bootstrap_95_descriptive':[percentile(draws,.025),percentile(draws,.975)],
            'bootstrap_repeats':repeats,'seed':20260929,'transitions':dict(transitions),
            'limitation':'descriptive cluster resampling; synthetic groups and adaptive experiment, not a deployment guarantee'}


def route_classes(rows):
    classes=sorted({r['labels']['route'] for r in rows})
    out={}
    for c in classes:
        gold=[r for r in rows if r['labels']['route']==c]
        pred=[r for r in rows if r['predictions']['route']['choice']==c]
        tp=sum(r['predictions']['route']['choice']==c for r in gold)
        out[c]={'support':len(gold),'correct':tp,'recall':tp/len(gold),
                'precision':tp/len(pred) if pred else 0.,'predicted_count':len(pred)}
    return out


def pc(x): return f'{x:.2%}'
def pp(x): return f'{100*x:+.2f}'


def build():
    if load_json(OUT/'status.json')['stage']!='complete':
        raise RuntimeError('Evaluation is not complete; do not report partial results as final')
    protocol=load_json(OUT/'protocol.json')
    for p,h in protocol['cached_files'].items():
        if sha(ROOT/p)!=h: raise ValueError('Cached comparison changed')
    m=load_json(OUT/'metrics.json'); speed=load_json(OUT/'speed.json'); checks=load_json(OUT/'checks.json')
    datasets=load_json(ROOT/'configs/support-v8.json')['final_evaluation']['datasets']
    challenge={v:read_rows((OUT if v==SELECTED else CACHE)/v/'challenge.jsonl') for v in LABELS if v!='jev'}
    challenge['jev']=[r for r in read_rows(CACHE/'jev/responses.jsonl') if r['kind']=='challenge']
    candidate=challenge[SELECTED]
    comparisons={v:paired(rows,candidate) for v,rows in challenge.items() if v!=SELECTED}
    legacy_new=read_rows(OUT/SELECTED/'legacy.jsonl')
    legacy_pairs={v:paired(read_rows(CACHE/v/'legacy.jsonl'),legacy_new) for v in ['v5-reference','step-200']}
    classes={v:route_classes(rows) for v,rows in challenge.items()}
    source=read_rows(ROOT/datasets['challenge']); input_map={r['id']:r for r in source}
    lookup={v:{r['id']:r for r in rows} for v,rows in challenge.items()}
    errors=[]
    for row in candidate:
        tasks=[t for t in ('intent','route','tool') if row['predictions'][t]['choice']!=row['labels'][t]]
        if tasks:
            raw=input_map[row['id']]
            errors.append({'id':row['id'],'group':row['group'],'wrong_tasks':tasks,
                'message':raw['message'],'history':raw.get('history',[]),'state':raw.get('state',{}),
                'available_tools':raw.get('available_tools',[]),'labels':row['labels'],
                'predictions':{v:{t:lookup[v][row['id']]['predictions'][t]['choice'] for t in ('intent','route','tool')} for v in lookup},
                'candidate_route_probabilities':row['predictions']['route']['probabilities']})
    atomic_json(OUT/'paired-comparison.json',{'challenge':comparisons,'legacy':legacy_pairs})
    atomic_json(OUT/'route-classes.json',classes)
    atomic_json(OUT/'error-review.json',errors)
    # Evaluator hashes were frozen before scoring. Report implementation is recorded now.
    atomic_json(OUT/'report-provenance.json',{'report_source_sha256':sha(ROOT/'src/qwenlab/support_v8_observe_report.py'),
        'inputs':{p.name:sha(p) for p in [OUT/'protocol.json',OUT/'metrics.json',OUT/'speed.json',OUT/'checks.json']},
        'candidate_predictions':{p.name:sha(p) for p in (OUT/SELECTED).glob('*.jsonl')},
        'new_jev_requests':0})
    new=m[SELECTED]['challenge']; old=m['step-200']['challenge']; jev=m['jev']['challenge']
    a=lambda v,d,t:m[v][d]['tasks'][t]['accuracy']
    lines=['# 第2801步候选评估：效果、回归与速度','',
        '2026-09-29。候选在读取本轮测试结果前固定为第2801步；未依据测试重新选模型。本轮没有训练、部署或新增Jev请求。','',
        f"业务挑战路由：{new['tasks']['route']['correct']}/{new['n']}（{pc(a(SELECTED,'challenge','route'))}）；相对第200步{pp(a(SELECTED,'challenge','route')-a('step-200','challenge','route'))}个百分点，相对Jev{pp(a(SELECTED,'challenge','route')-a('jev','challenge','route'))}个百分点。",
        f"原定比较检查未通过项：{', '.join(k for k,v in checks.items() if not v) or '无'}。本轮是已观察数据上的回归验证，不是全新独立盲测；不能据此宣称已可上线替代Jev。",
        '', '## 1. 样本与可比口径','',
        '|集合|条数|用途|限制|','|---|---:|---|---|',
        '|新业务开发集|120|训练期间选检查点|已参与选择，不作为最终泛化成绩|',
        '|旧业务开发集|402|保留旧能力与人工漏判门槛|已反复观察|',
        '|业务校准集|110|只拟合正温度|不改变分类argmax、不调拒答阈值|',
        '|业务挑战集|79|本轮固定候选的业务回归|合成、未新增人工复核，过去已观察|',
        '|旧业务测试集|402|历史业务回归|过去已观察，不是全新盲测|',
        '|MASSIVE中文测试|2974|公共意图保留|过去已观察|',
        '|CrossWOZ测试|200|公共对话意图保留|过去已观察|',
        '', '原始Qwen、V5和第200步准确率从原V8预测重新计算；核验了追加训练前保存的文件哈希、原协议链、输入/标签及原结果指标。第2801步预测本次新计算。四个本地版本速度均本次重测；Jev准确率和速度复用此前缓存。',
        f"Jev记录版本：{', '.join(protocol['jev_versions'])}。文本任务均为意图、四类路由、工具三个字段，不等于八业务动作完整端到端验收。",
        '', '## 2. 业务挑战集总表','',
        '|模型|意图准确率|路由准确率|路由macro-F1|工具准确率¹|工具调用联合正确²|三个字段全对|人工漏判|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for v in LABELS:
        x=m[v]['challenge']; t=x['tasks']
        lines.append(f"|{LABELS[v]}|{pc(t['intent']['accuracy'])}|{pc(t['route']['accuracy'])} ({t['route']['correct']}/{x['n']})|{pc(t['route']['macro_f1_gold_supported_classes'])}|{pc(t['tool']['accuracy'])}|{x['joint_tool_correct']}/{x['tool_required']}|{x['all_fields_correct']}/{x['n']}|{x['human_missed']}/{x['human_required']}|")
    lines += ['', '¹ 工具准确率包含不调用工具的none，不能单独代表实际工具执行成功。² 在确需工具的样本中，路由选tool且工具名正确；不包含鉴权、参数和真实业务执行。',
              '', '## 3. 具体改对与改错','',
              '|对照模型→第2801步|改对|改错|双方都错|准确率差值（百分点）|按group重采样95%描述区间|',
              '|---|---:|---:|---:|---:|---:|']
    for v,d in comparisons.items():
        lo,hi=d['group_bootstrap_95_descriptive']
        lines.append(f"|{LABELS[v]}→2801|{d['fixed']}|{d['regressed']}|{d['both_wrong']}|{pp(d['accuracy_delta'])}|[{pp(lo)}, {pp(hi)}]|")
    lines += ['', f"挑战集共{comparisons['step-200']['groups']}个group，按group抽样10000次（种子20260929），避免把同组变体当成完全独立样本。此区间只描述当前合成样本的不确定性，不修正适应性实验偏差，也不是线上效果保证。", '',
              '|真实路由|样本数|第200步召回率|第2801步召回率|Jev召回率|','|---|---:|---:|---:|---:|']
    for c,d in classes[SELECTED].items():
        lines.append(f"|{c}|{d['support']}|{pc(classes['step-200'][c]['recall'])}|{pc(d['recall'])}|{pc(classes['jev'][c]['recall'])}|")
    lines += ['', '|剩余路由错误ID|输入|标注路由|第2801步|第200步|Jev|',
              '|---|---|---|---|---|---|']
    for e in errors:
        if 'route' in e['wrong_tasks']:
            message=e['message'].replace('|','／').replace('\n',' ')
            lines.append(f"|{e['id']}|{message}|{e['labels']['route']}|{e['predictions'][SELECTED]['route']}|{e['predictions']['step-200']['route']}|{e['predictions']['jev']['route']}|")
    lines += ['', '逐条错误、状态上下文及各模型预测保存在`error-review.json`。这些条目仅用于评估解释；不得直接或改写后回填训练集。','',
              '## 4. 旧业务与公共能力','',
              '|模型|旧业务意图|旧业务路由|旧业务工具|旧业务人工漏判|MASSIVE意图|CrossWOZ意图|',
              '|---|---:|---:|---:|---:|---:|---:|']
    for v in VARIANT_ORDER:
        x=m[v]['legacy']
        lines.append(f"|{LABELS[v]}|{pc(a(v,'legacy','intent'))}|{pc(a(v,'legacy','route'))}|{pc(a(v,'legacy','tool'))}|{x['human_missed']}/{x['human_required']}|{pc(a(v,'massive','intent'))}|{pc(a(v,'crosswoz','intent'))}|")
    lines += ['', '公共集衡量公共意图分类，不能替代客服状态理解、人工转接或工具选择的验证。以下列出相对V5的变化；原门槛对accuracy与macro-F1分别检查，而非只看平均分。','',
              '|集合/任务|V5 accuracy|2801 accuracy|变化pp|V5 macro-F1|2801 macro-F1|变化pp|',
              '|---|---:|---:|---:|---:|---:|---:|']
    for dataset in ['legacy','massive','crosswoz']:
        for task,base in m['v5-reference'][dataset]['tasks'].items():
            current=m[SELECTED][dataset]['tasks'][task]
            k='macro_f1_gold_supported_classes'
            lines.append(f"|{dataset}/{task}|{pc(base['accuracy'])}|{pc(current['accuracy'])}|{pp(current['accuracy']-base['accuracy'])}|{pc(base[k])}|{pc(current[k])}|{pp(current[k]-base[k])}|")
    lines += ['', '|旧业务路由：对照→2801|改对|改错|净增加正确数|', '|---|---:|---:|---:|']
    for v,d in legacy_pairs.items():
        lines.append(f"|{LABELS[v]}→2801|{d['fixed']}|{d['regressed']}|{d['fixed']-d['regressed']}|")
    lines += ['', '旧业务总体改善不代表每条都改善；成对结果中的新增错题仍需保留。其按group重采样区间见paired-comparison.json，不把小幅净增直接推断为真实用户分布上的显著提高。']
    lines += ['', '## 5. 同输入速度','',
              '|模型|来源|请求数|P50毫秒|P95毫秒|均值毫秒|','|---|---|---:|---:|---:|---:|']
    for v in VARIANT_ORDER+['jev']:
        x=speed['jev-historical' if v=='jev' else v]
        lines.append(f"|{LABELS[v]}|{'历史API，含网络' if v=='jev' else '本轮本地重测'}|{x['requests']}|{x['p50_s']*1000:.1f}|{x['p95_s']*1000:.1f}|{x['mean_s']*1000:.1f}|")
    s=speed[SELECTED]
    lines += ['', f"第2801步P50耗时相对本轮第200步变化{(s['p50_s']/speed['step-200']['p50_s']-1)*100:+.2f}%，相对历史Jev变化{(s['p50_s']/speed['jev-historical']['p50_s']-1)*100:+.2f}%。负值表示耗时降低；不能把非同期网络/硬件差异全部归因于模型。",
              '四个本地版本均NF4、batch=1、常驻GPU、3次预热；固定32个校准输入重复3次，每请求计算完整三任务，计入编码与GPU同步，不计加载、后端工具执行或回答生成。本地三个任务分别串行前向，Jev一次API返回三个选择；比较的是当前调用方案，而非同硬件下模型架构的固有速度。按版本顺序测量，未交错，存在温度/功耗/系统负载漂移；hardware-history.jsonl记录评估启动。','',
              '## 6. 校准与过拟合判断','']
    cal=load_json(OUT/'calibration.json')
    lines += ['|任务|拟合温度|校准样本数|挑战NLL：前→后|挑战ECE：前→后|','|---|---:|---:|---:|---:|']
    for task in ['intent','route']:
        fit=cal['temperatures'][task]; raw=cal['raw']['tasks'][task]; after=cal['calibrated']['tasks'][task]
        lines.append(f"|{task}|{fit['temperature']:.3f}|{fit['n']}|{raw['nll']:.4f} → {after['nll']:.4f}|{raw['ece_10_equal_width']:.4f} → {after['ece_10_equal_width']:.4f}|")
    route_before=cal['raw']['tasks']['route']; route_after=cal['calibrated']['tasks']['route']
    if route_after['ece_10_equal_width']>route_before['ece_10_equal_width']:
        lines += ['', '本轮路由ECE在温度校准后变差，因此不能概括为“校准全面改善置信度”。应保留原始与校准两套结果；未据此修改服务默认概率或自动回退阈值。']
    lines += ['', '温度只从110条校准样本拟合，保持argmax不变，所以不能修复路由错误。NLL是正确标签的负对数概率，越低越好；ECE是置信度与实际正确率的分桶差异，越低越好，但小样本ECE不稳定。','',
              '第2401步的一条人工漏判在2801步恢复，支持为单次轻微回退设置观察窗口；第3201步又出现旧业务意图macro-F1回退，说明更长训练不保证更好。第2801步通过开发门槛不代表没有过拟合，开发集参与选模、样本合成且测试集反复观察都限制了结论。应同时看本报告的挑战、历史回归及公共集结果，不能用训练loss很低证明泛化。','',
              '## 7. 结论与后续','',
              ('本轮已通过原定数值比较检查，但这只是已观察测试集上的结果，不等于独立验收通过。' if all(checks.values()) else
               '本轮未通过全部原定数值比较检查，默认继续Jev。未通过项见报告开头与checks.json。'),
              '这里的最终测试人工漏判条件是“相对V5不增加”：V5在挑战集也漏判1条，所以候选漏判1条仍通过该项，并不代表零漏判或追平Jev。训练开发门槛中的零新增与最终测试的基线比较应分别理解。',
              f"旧业务意图macro-F1相对V5变化{pp(m[SELECTED]['legacy']['tasks']['intent']['macro_f1_gold_supported_classes']-m['v5-reference']['legacy']['tasks']['intent']['macro_f1_gold_supported_classes'])}个百分点；这项距离3个百分点回退上限很近，不能把数值过线描述为保留旧能力毫无风险。",
              '本轮只评价已经冻结的第2801步，不根据测试错题选其他检查点或启动新训练。默认仍保留Jev；第2801步保留为本地候选，待新的独立业务留出及后端八动作端到端验收后再决定是否切换。',
              '下一阶段优先冻结业务规范并构建未见过的场景组，独立核验标签；现有错误用来描述能力边界，不直接作为训练监督。模型与后端权限/状态保护的效果应分开计分。','',
              '## 复现与文件','',
              '```powershell', '.\\scripts\\evaluate-support-v8-observe.ps1',
              '.\\.venv\\Scripts\\python.exe -m qwenlab.support_v8_observe_eval progress',
              '.\\.venv\\Scripts\\python.exe -m qwenlab.support_v8_observe_report', '```','',
              '完整结果：`results/support-v8-observe/final/`。`protocol.json`固定输入与缓存；`metrics.json`为准确率与概率指标；`speed.json`为耗时；`checks.json`为原定比较条件；`paired-comparison.json`为成对改正/回退；`route-classes.json`为分类召回；`error-review.json`为逐条复查；`calibration.json`为温度及前后指标。重新执行已完成评估不会再次跑GPU或调用API。']
    text='\n'.join(lines)+'\n'
    (OUT/'report.md').write_text(text,encoding='utf-8')
    (ROOT/'docs/27-V8第2801步效果与速度评估.md').write_text(text,encoding='utf-8')
    status=load_json(OUT/'status.json')
    status.update(report_pending=False,report='results/support-v8-observe/final/report.md',
                  report_generated_at=datetime.now(timezone.utc).isoformat())
    atomic_json(OUT/'status.json',status)
    print(json.dumps({'candidate':SELECTED,'route_accuracy':new['tasks']['route']['accuracy'],
        'route_delta_vs_200':a(SELECTED,'challenge','route')-a('step-200','challenge','route'),
        'route_delta_vs_jev':a(SELECTED,'challenge','route')-a('jev','challenge','route'),
        'human_missed':new['human_missed'],'p50_ms':speed[SELECTED]['p50_s']*1000,
        'failed_checks':[k for k,v in checks.items() if not v]},ensure_ascii=False,indent=2))


VARIANT_ORDER=['base','v5-reference','step-200',SELECTED]
if __name__=='__main__': build()
