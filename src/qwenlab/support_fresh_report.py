"""Publish compact evidence from completed offline and loopback acceptance runs."""
from collections import defaultdict
from qwenlab.common import ROOT, load_json, sha
from qwenlab.joint_v5 import atomic_json
from qwenlab.prepare_v2 import read_rows
from qwenlab.support_fresh_eval import OUT, DATA


def build():
    assert load_json(OUT/'status.json')['stage']=='complete'
    m=load_json(OUT/'metrics.json'); paired=load_json(OUT/'paired.json')
    live=load_json(OUT/'live-classifier.json'); backend=load_json(OUT/'backend-integration.json')
    classes=load_json(OUT/'route-classes.json'); errors=load_json(OUT/'errors.json')
    order=load_json(OUT/'live-tool-order.json')
    dataset=read_rows(DATA/'cases.jsonl'); pred=read_rows(OUT/'step-2801/predictions.jsonl')
    group=defaultdict(list)
    for r in pred:group[r['group']].append(r['labels']['route']==r['predictions']['route']['choice'])
    missed=[e for e in errors if e['input']['labels']['route']=='human' and 'route' in e['wrong_tasks']]
    names={'base':'原始Qwen','v5-reference':'V5','step-200':'V8第200步','step-2801':'V8第2801步'}
    lines=['# 第2801步新增场景与真实服务接入验证','',
        '2026-09-29。固定第2801步候选，新增合成场景在模型评分前编写、独立agent复核并冻结；本轮未训练、未增加Jev请求、未修改默认模型或部署。',
        '', '## 1. 新场景效果', '',
        '128条、64个场景组，每组两种措辞，tool/clarify/llm/human各32条。评估的是意图、四路由和只读工具选择，不是八动作分类器。', '',
        '|版本|意图准确率|路由准确率|工具字段（含none）|三字段全对|人工漏判|','|---|---:|---:|---:|---:|---:|']
    for v,x in m.items():
        lines.append(f"|{names[v]}|{x['tasks']['intent']['accuracy']:.2%}|{x['tasks']['route']['accuracy']:.2%}（{x['tasks']['route']['correct']}/128）|{x['tasks']['tool']['accuracy']:.2%}|{x['all_fields_correct']}/128|{x['human_missed']}/{x['human_required']}|")
    lines+=['','|2801相对对照的路由变化|改对|改错|净变化|组重采样95%描述区间|','|---|---:|---:|---:|---:|']
    for v,c in paired.items():
        low,high=c['group_bootstrap_95_descriptive']
        lines.append(f"|{names[v]}|{c['fixed']}|{c['regressed']}|{c['accuracy_delta']*100:+.2f}个百分点|{low*100:+.2f}～{high*100:+.2f}个百分点|")
    lines+=['','|真实路由|第2801步答对|召回率|','|---|---:|---:|']
    for k,c in classes['step-2801'].items():lines.append(f"|{k}|{c['correct']}/{c['support']}|{c['recall']:.2%}|")
    lines += ['', f"两种措辞路由均正确的场景组：{sum(all(x) for x in group.values())}/64。组内两条并非独立样本。",
        '', '评分前声明的诊断目标为路由≥95%、人工漏判0、三个任务相对200步下降均不超过3个百分点。该目标仅用于本组场景诊断，不替换旧门槛，不构成上线验收。未通过项：'+str([k for k,v in load_json(OUT/'diagnostics.json').items() if not v])+'。',
        '', '第2801步相对第200步仅净多答对1条路由，意图少答对6条（下降4.69个百分点），三字段全对少3条；相对V5三字段全对少4条。组重采样区间跨零，不能声称新场景路由稳定优于两个对照。人工漏判0/32是本组观察结果，不抹掉旧挑战仍有1条漏判。缺编号时误转人工、not_found后直接回答等边界仍薄弱。', '', '### 路由错例（保留，不回填训练）','', '|ID|最新输入|应选|实际|','|---|---|---|---|']
    for e in errors:
        if 'route' in e['wrong_tasks']:
            r=e['input'];lines.append(f"|{r['id']}|{r['message']}|{r['labels']['route']}|{e['predictions']['route']['choice']}|")
    lines += ['', '完整上下文、预构造state、可用工具以及意图错误见本地`results/support-fresh-v1/errors.json`，不能只根据上表单句判错。',
        '', '## 2. 泛化、过拟合与Jev比较的边界','',
        '新输入与完整V4/V5训练、V8回放、专项候选和旧业务测试进行了规范化字符串去重，匹配0；近似匹配阈值0.78也没有命中。字符去重不证明语义独立。作者已看过旧实验，全部样本仍为助手起草、agent复核，未经过本次人工复核，也不是真实用户或外部盲测。',
        '四路由均衡配比是评测设计，不等于产品真实流量。旧79条挑战曾多次观察，其94.94%与本套成绩不能直接比较为性能升降。Jev没有评本套新数据，因此没有同集Jev差距结论；历史97.47%只属于旧79条。',
        '新措辞验证有助于检查是否只记住旧句子，但仍无法排除场景模板过拟合。旧报告中公共MASSIVE意图较V5下降1.31个百分点、旧业务意图macro-F1下降2.95个百分点，仍需保留为能力取舍证据；不能因本套得分好就宣称无过拟合。',
        '', '## 3. Flask服务与输出层裁剪','',
        f"同128条通过HTTP送入第2801步candidate裁剪服务，检查协议/政策哈希、适配器、projection和无回退。与离线完整输出层相比，原始意图/路由/工具共384次选择中差异{len(live['raw_choice_differences_vs_offline'])}项。差异列表见原始JSON。",
        f"服务路由准确率：{live['metrics']['tasks']['route']['accuracy']:.2%}。HTTP总耗时P50={live['http_ms']['p50']:.1f}ms，P95={live['http_ms']['p95']:.1f}ms。",
        '这里是一遍128条长短不等场景的本机HTTP实测，包含编码、推理、序列化及本地传输；服务返回的inferenceMs不含编码。不能用它直接对照此前32条×3次的594ms或历史Jev721ms，裁剪的加速幅度仍以已有同输入对照实验为准。零分类差异不代表浮点分数逐位相同或所有未来输入绝对等价。',
        '', '## 4. 真实后端链路与能力缺口','',
        f"集成验收用例通过{backend['passed']}/{backend['total']}。真实Node HTTP路由→Qwen provider→Flask→模型；真实鉴权、会话仓储和五个工具运行于SQLite内存样本库，回复使用模板。无MySQL/前端浏览器/回复大模型实测，不能称整站验收或模型准确率。",'',
        '|集成用例|结果|','|---|---|']
    for r in backend['rows']:lines.append(f"|{r['name']}|{'通过' if r['passed'] else '失败：'+r['error'].replace('|','/')}|")
    lines += ['', '### 基础验收以外的定向错例探查', '',
        '以下5条是在离线错例分析后追加的诊断，不是盲测，不合并进19项基础验收或准确率。', '',
        '|探查|期望动作|实际动作|符合预期|','|---|---|---|---|']
    for p in backend['diagnosticProbes']:lines.append(f"|{p['name']}|{p['expected']}|{p['actual']}|{'是' if p['matched'] else '否'}|")
    lines += ['', '两个非法状态码虽然模型原始route选tool，后端实际改为clarify；这是参数保护生效，不是模型判断正确。要求重新获取本人申请清单时最终answer，仍未执行应有查询，是基础链路测试通过后仍暴露的业务错误。',
        '', '### 工具顺序单变量对照', '',
        f"固定同一128条及模型，只将available_tools按当前后端注册表顺序排列，其余输入不改。路由准确率从{live['metrics']['tasks']['route']['accuracy']:.2%}变为{order['metrics']['tasks']['route']['accuracy']:.2%}；原始三字段选择差异{len(order['raw_choice_differences_vs_offline'])}/384。",
        '工具集合相同但顺序改变仍能影响分类，说明模型对输入表示敏感。此结果是事后诊断，仍是预构造state，不能称128条完整后端验收；也不能挑得分更高的顺序当新成绩。应在后续独立版本统一离线/服务/后端的确定性序列化协议并重新验证，不能暗改本次冻结实验。']
    lines += ['', '普通模型案例强制检查provider=qwen-v1、local-qwen审计和实际适配器；policy-guard-v1命中独立列出，不算模型答对。失败provider以retryable返回，不偷偷切规则或其他厂商。后端25项CPU契约/隔离测试、Flask5项CPU接口测试另行通过。',
        '', '|范围|当前状态|','|---|---|',
        '|tool / clarify / answer|模型四路由经后端转换，参数提取、校验与归属由后端执行|',
        '|human|支持决策及真实“人工未接通”提示，尚无工单转接|',
        '|refuse / close|后端守卫提供，不是四路由模型独立预测的两个类别|',
        '|retrieve / redirect|当前契约不支持，尚未实现，不能声称八动作全链路完成|',
        '|知识检索|health明确retrievalAvailable=false；后续新增检索执行器、文档版本与引用，再定义路由和标注政策|',
        '|多模态|本轮仅文本，接口拒绝图片；Qwen3-VL底座能力不等于当前服务已支持图片|',
        '', '## 5. 复现命令','',
        '在qwen目录中（有本机权重和已安装环境）：','', '```powershell',
        '.\\scripts\\evaluate-support-fresh.ps1',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.support_fresh_eval progress',
        '# 离线评分完成后，另开终端启动显式候选服务；此终端保持运行',
        '. .\\scripts\\use-env.ps1',
        '$env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.serve --profile support-v1 --adapter .local/checkpoints/support-v8-observe/step-2801 --projection candidate --port 8021',
        '```','', '本轮隔离验收使用无鉴权的127.0.0.1服务；不要暴露到外网。若当前终端设置了QWEN_DECISION_KEY，应另开未设置该变量的验收终端。服务ready后另开终端：','', '```powershell',
        '# qwen目录', '.\\.venv\\Scripts\\python.exe -m qwenlab.support_live_verify --url http://127.0.0.1:8021/decide',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.support_live_verify --url http://127.0.0.1:8021/decide --tool-order backend',
        '# 项目的后端目录', 'node scripts/verify-local-qwen.cjs http://127.0.0.1:8021/decide ../../qwen/results/support-fresh-v1/backend-integration.json',
        '# 回到qwen目录生成本报告', '.\\.venv\\Scripts\\python.exe -m qwenlab.support_fresh_report', '```',
        '', '训练、离线评估、Flask服务共享GPU锁，不能同时启动；验收结束Ctrl+C关闭自己启动的服务。离线评估已完成时run不会重复推理；HTTP验收命令再次执行会重测并覆盖本地验收结果。',
        '', '## 6. 下一步建议','',
        '默认保留Jev，第2801步作为本地对照候选。本轮结果不触发继续长训、重选检查点或自动上线。先根据错例类型评估是否存在稳定的决策边界缺口，再为后续数据准备另外的训练来源；本套及既有测试错题不直接或改写回填训练。',
        '眼前优先统一实验、Flask与后端的输入序列化协议，并明确缺编号、查询失败和未知状态应如何追问；先排除输入表示差异，再规划新训练版本。知识检索与人工受理作为后续独立工程模块推进，届时制定retrieve/redirect及风险优先级的新契约。之后用固定输入、相同版本政策对Jev和Qwen做同集比较；Jev新付费评测须单独安排预算。当前无证据仅靠延长训练就能补齐这些问题。',
        '', '## 7. 证据与变更范围','',
        '数据与冻结证据：`data/support-fresh-holdout-v1/`。完整预测/逐条耗时/接入审计：`results/support-fresh-v1/`（gitignore忽略）。可随报告提交的紧凑数值与哈希：`docs/evidence/support-fresh-v1-summary.json`。测试生成数据不允许作为训练输入。',
        '新增离线评估、HTTP复核和隔离接入脚本，没有修改冻结训练协议、模型权重、生产provider默认值或App页面。本轮没有Git提交、推送或部署。']
    (ROOT/'docs/28-新增场景与真实服务接入验证.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=[OUT/n for n in ['protocol.json','metrics.json','paired.json','route-classes.json','errors.json','diagnostics.json','live-classifier.json','live-tool-order.json','backend-integration.json']]
    evidence={'metrics':m,'paired_route':paired,'route_classes':classes,'groups_both_route_correct':sum(all(x) for x in group.values()),
        'human_missed_ids':[e['input']['id'] for e in missed],
        'live':{k:live[k] for k in ['metadata','n','metrics','raw_choice_differences_vs_offline','http_ms','timing_limitation']},
        'backend':{k:backend[k] for k in ['createdAt','adapter','database','responseProvider','passed','total','rows']},
        'tool_order_diagnostic':{k:order[k] for k in ['tool_order','backend_order','purpose','metrics','raw_choice_differences_vs_offline']},'diagnostic_probes':backend['diagnosticProbes'],
        'new_jev_calls':0,'data_freeze_sha256':sha(DATA/'freeze.json'),'result_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files}}
    atomic_json(ROOT/'docs/evidence/support-fresh-v1-summary.json',evidence)


if __name__=='__main__':build()
