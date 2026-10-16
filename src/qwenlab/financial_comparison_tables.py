"""Rebuild percentage-based comparison from published observations; no GPU/API needed."""
import json
import hashlib
import math
from pathlib import Path
from statistics import mean

from qwenlab.common import ROOT
from qwenlab.financial_actions_metrics import percentile
from qwenlab.financial_service_v2_metrics import basic

PUBLIC = ROOT / 'docs/evidence/financial-five-model-comparison-v1'
DATA = ROOT / 'data/financial-service-v2/development.json'
ACTIONS = ['clarify', 'retrieve', 'tool', 'answer', 'human', 'redirect', 'refuse', 'close']
NAMES = ['追问', '检索', '工具', '回答', '人工', '引导', '拒绝', '结束']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(value):
    return '—' if value is None else f'{value * 100:.2f}%'


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|---|' + '---:|' * (len(headers) - 1)] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def calculate(rows, predictions, original):
    m = basic(rows, predictions, original['prompt_sha256'], original['protocol_sha256'])
    # Independently recompute published figures from per-sample decisions.
    for field in ('data_sha256', 'action_accuracy', 'macro_f1', 'per_action', 'human_misses',
                  'false_refusals', 'action_tool_joint_accuracy', 'status_tool_accuracy',
                  'latency', 'unauthenticated_tool_actions', 'unavailable_tool_choices',
                  'unavailable_knowledge_retrievals'):
        if m[field] != original[field]:
            raise ValueError('Published metric mismatch: ' + field)
    lookup = {p['id']: p for p in predictions}
    supports = [m['per_action'][a]['support'] for a in ACTIONS]
    elapsed = [p['elapsed_s'] for p in predictions]
    if any(not math.isfinite(v) or v < 0 for v in elapsed):
        raise ValueError('Invalid elapsed time')
    unauth = sum(not r['input']['state']['authenticated'] for r in rows)
    no_kb = sum(not r['input']['capabilities']['knowledge_collections'] for r in rows)
    tool_predictions = sum(p['action'] == 'tool' for p in predictions)
    m['derived'] = dict(
        macro_precision=mean(m['per_action'][a]['precision'] for a in ACTIONS),
        balanced_accuracy=mean(m['per_action'][a]['recall'] for a in ACTIONS),
        weighted_f1=sum(m['per_action'][a]['f1'] * n for a, n in zip(ACTIONS, supports)) / len(rows),
        human_miss_rate=len(m['human_misses']) / m['per_action']['human']['support'],
        false_refusal_rate=len(m['false_refusals']) / (len(rows) - m['per_action']['refuse']['support']),
        unauth_tool_rate=ratio(len(m['unauthenticated_tool_actions']), unauth),
        unavailable_retrieval_rate=ratio(len(m['unavailable_knowledge_retrievals']), no_kb),
        unavailable_tool_rate=ratio(len(m['unavailable_tool_choices']), tool_predictions),
        predicted_tool_rate=tool_predictions / len(rows),
        denominators=dict(non_refuse=len(rows) - m['per_action']['refuse']['support'],
            unauthenticated=unauth, no_knowledge=no_kb, predicted_tool=tool_predictions),
        latency_ms=dict(mean=mean(elapsed) * 1000,
            **{f'p{q}': percentile(elapsed, q / 100) * 1000 for q in (50, 90, 95, 99)}))
    m['cohort_accuracy'] = {cohort: mean(lookup[r['id']]['action'] == r['annotation']['action']
        for r in rows if r['cohort'] == cohort) for cohort in sorted({r['cohort'] for r in rows})}
    return m


def run():
    manifest = read(PUBLIC / 'sources.json')
    if sha(DATA) != manifest['dataset_sha256']:
        raise ValueError('Frozen development data changed')
    rows = read(DATA)
    models = []
    for source in manifest['models']:
        for filename, expected in source['files'].items():
            if sha(PUBLIC / filename) != expected:
                raise ValueError('Published source changed: ' + filename)
        original = read(PUBLIC / source['metrics'])
        predictions = read(PUBLIC / source['observations'])
        models.append(dict(name=source['name'], metrics=calculate(rows, predictions, original)))
    summary = dict(scope='128 synthetic development samples; not final or production test',
        models=models, sources_sha256=sha(PUBLIC / 'sources.json'), code_sha256=sha(Path(__file__)))
    (PUBLIC / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    sections = []
    main = table(['模型', '动作准确率 ↑', '宏平均 F1 ↑', '工具联合准确率 ↑', '人工召回率 ↑', '误拒绝率 ↓'],
        [[x['name'], pct(m['action_accuracy']), pct(m['macro_f1']), pct(m['action_tool_joint_accuracy']),
          pct(m['per_action']['human']['recall']), pct(m['derived']['false_refusal_rate'])]
         for x in models for m in [x['metrics']]])
    sections += ['## 总体决策质量', main,
        '工具联合准确率以真实需要工具的 18 条为分母，动作和工具名必须都正确；人工召回率以应转人工的 27 条为分母。误拒绝率以不应拒绝的 110 条为分母。']
    quality = table(['模型', '宏平均精确率 ↑', '平衡准确率 ↑', '加权 F1 ↑', '漏转人工率 ↓', '状态解释工具准确率 ↑'],
        [[x['name'], *[pct(m['derived'][k]) for k in ('macro_precision', 'balanced_accuracy', 'weighted_f1', 'human_miss_rate')],
          pct(m['status_tool_accuracy'])] for x in models for m in [x['metrics']]])
    sections += ['## 补充质量指标', quality,
        '宏平均精确率和宏平均 F1 对八类等权；平衡准确率为八类召回率的平均；加权 F1 按真实类别样本数加权。状态解释工具只有 3 条，100% 也不能推导为稳定可靠。']
    speed = table(['模型', '平均耗时', 'P50', 'P90', 'P95', 'P99', '触发工具二次判断比例'],
        [[x['name'], *[f"{m['derived']['latency_ms'][k]:.0f} ms" for k in ('mean','p50','p90','p95','p99')],
          pct(m['derived']['predicted_tool_rate'])] for x in models for m in [x['metrics']]])
    sections += ['## 请求耗时', speed,
        '耗时保留毫秒单位，不强行换算为百分比。P50/P90/P95/P99 分别是耗时分布的分位数；128 条下 P99 仅描述本次尾部。Jev 含代理网络且本表排除失败重试，Qwen 为本地历史测量；均包括按需的第二次工具判断，不含业务执行/回答生成，不能据此推导纯模型加速或并发吞吐。Jev 计入所有失败与退避后的 P50/P95 为 324/1,414 ms。']
    cohorts = [('current-service', '当前服务（64 条）'), ('planned-retrieval', '规划检索（32 条）'), ('preauth-robustness', '登录前健壮性（32 条）')]
    sections += ['## 分业务场景准确率', table(['模型']+[title+' ↑' for _,title in cohorts],
        [[x['name']]+[pct(x['metrics']['cohort_accuracy'][key]) for key,_ in cohorts] for x in models]),
        '规划检索指标只验证动作选择，不表示知识库或检索问答已完成。']
    sections += ['## 能力与权限约束错误率', table(['模型','未认证仍调用工具 ↓','无知识库仍检索 ↓','选择不可用工具 ↓'],
        [[x['name']]+[pct(x['metrics']['derived'][k]) for k in ('unauth_tool_rate','unavailable_retrieval_rate','unavailable_tool_rate')] for x in models]),
        '分母分别为未认证样本、无可用知识集合样本、模型预测为 tool 的样本；具体分母保留在 summary.json。这里测模型原始决策，未加入后端拦截；0% 不代表系统不存在权限风险。']
    support = models[0]['metrics']['per_action']
    for metric, title in [('recall','召回率'),('precision','精确率'),('f1','F1')]:
        sections += [f'## 八动作{title}', table(['模型']+[n+' ↑' for n in NAMES],
            [[x['name']]+[pct(x['metrics']['per_action'][a][metric]) for a in ACTIONS] for x in models])]
    sections += ['召回率：该动作的真实样本有多少被找回；精确率：预测为该动作的结果有多少正确；F1 综合两者。没有预测某类时，沿用既有评估器将精确率记为 0%。真实支持数：'+
        '、'.join(f"{n} {support[a]['support']} 条" for a,n in zip(ACTIONS,NAMES))+'。引导只有 4 条，勿将单个百分比视为稳健泛化结论。']
    (PUBLIC / 'tables.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    (PUBLIC / 'readme-tables.md').write_text(main+'\n\n'+speed+'\n',encoding='utf-8')
    print('Verified five models and generated percentage tables without API calls.')


if __name__ == '__main__':
    run()
