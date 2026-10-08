"""Read-only experiment audit and reusable Jev comparison. No API/GPU calls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

from qwenlab.common import ROOT
from qwenlab import financial_actions_metrics as metrics
from qwenlab import financial_jev_reference as jev
from qwenlab.financial_pilot_analysis import cluster_interval

RUN = ROOT/'results/financial-qwen35-v1'
OUT = ROOT/'results/financial-qwen35-review-v1'
PUBLIC = ROOT/'docs/evidence/financial-jev-reference-v1'
VARIANTS = ['base','step-200','step-744','step-1488','step-2232','step-2976']


def predictions(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def probability_metrics(rows, preds):
    by_id={p['id']:p for p in preds}
    bins=[[] for _ in range(10)];nll=[];brier=[];error_conf=[]
    for row in rows:
        p=by_id[row['id']];gold=row['annotation']['action'];probs=p['action_prediction']['probabilities']
        conf=probs[p['action']];correct=p['action']==gold
        bins[min(int(conf*10),9)].append((conf,int(correct)))
        nll.append(-math.log(max(probs[gold],1e-12)))
        brier.append(sum((probs[a]-int(a==gold))**2 for a in probs))
        if not correct:error_conf.append(conf)
    return dict(nll=statistics.mean(nll),brier_sum_over_classes=statistics.mean(brier),
        ece10=sum(len(b)/len(rows)*abs(statistics.mean(x[0] for x in b)-statistics.mean(x[1] for x in b)) for b in bins if b),
        errors=len(error_conf),errors_confidence_ge_09=sum(x>=.9 for x in error_conf),
        mean_error_confidence=statistics.mean(error_conf) if error_conf else None,
        limitation='Uncalibrated development diagnostics; ten fixed bins, eight correlated macro stories; no fitted temperature.')


def audit():
    protocol=jev.read(RUN/'protocol.json');completion=jev.read(RUN/'completion.json')
    if completion['status']!='complete' or completion['selection']['passed']:
        raise ValueError('This review is bound to the completed, unqualified V1 run')
    ph=jev.file_sha(RUN/'protocol.json')
    if ph!=completion['protocol_sha256']:raise ValueError('Protocol changed')
    for name,h in protocol['source_sha256'].items():
        if jev.file_sha(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    if jev.file_sha(jev.DATA/'manifest.json')!=protocol['dataset_manifest_sha256']:
        raise ValueError('Frozen data manifest changed')
    summary=jev.read(RUN/'training-summary.json');log=predictions(RUN/'train.jsonl')
    assert [r['step'] for r in log]==list(range(1,2977))
    assert summary['dataset_rows']==summary['unique_rows']==len(summary['sampled_by_id'])==11899
    assert set(summary['sampled_by_id'].values())=={2} and summary['sample_positions']==23798
    assert all(math.isfinite(r['loss']) and math.isfinite(r['gradient_norm']) for r in log)
    for variant in VARIANTS[1:]:
        ckpt=ROOT/'.local/checkpoints/financial-qwen35-v1'/variant
        meta=jev.read(ckpt/'checkpoint.json')
        assert meta['protocol_sha256']==ph
        for name,h in meta['files'].items():assert jev.file_sha(ckpt/name)==h
    rows=jev.source_rows('development');by_id={r['id']:r for r in rows}
    reports={};pred={}
    for v in VARIANTS:
        folder=RUN/'development'/v;pred[v]=predictions(folder/'predictions.jsonl')
        reports[v]=metrics.evaluate(rows,pred[v],protocol['prompt_sha256'],ph)
        if reports[v]!=jev.read(folder/'metrics.json'):raise ValueError('Stored metrics mismatch')
    gates={v:metrics.development_gate(reports['base'],reports[v],protocol['config']['development_gate']) for v in VARIANTS[1:]}
    assert gates==completion['selection']['gates']
    errors=[]
    diagnoses={
        'FIN-F2-E-0022':('否定与结束边界','明确还会继续咨询，标签answer合理；不是结束。'),
        'FIN-F2-E-0084':('否定与本人查询','要求查询本人，并明确排除室友账户，tool标签合理。'),
        'FIN-F2-E-0118':('否定与结束边界','明确不是结束咨询，answer标签合理。'),
        'FIN-F2-E-0131':('否定与本人查询','按场景本人为家长且已认证，明确排除孩子资料，tool合理；孤立措辞可更清楚，但不据此回改冻结标签。'),
        'FIN-F2-E-0143':('提示原文与追问','已提供“尚未选择”并只求字面含义，answer合理。'),
        'FIN-F2-E-0206':('工具可用性','申请列表工具已移除；应如实说明人工未接通，不能选不可用工具。'),
        'FIN-F2-E-0255':('工具可用性','申请明细工具已移除，其他工具不能替代该单明细；human合理。'),
        'FIN-F2-E-0358':('知识与产品查询','请求正式用途规则，可用知识库支持retrieve；目录工具未提供用途规则。'),
        'FIN-F2-E-0369':('人工诉求优先级','未认证不取消明确人工诉求；human表示下一步应升级，不宣称已经接通。')}
    for p in pred['step-2976']:
        row=by_id[p['id']]
        if p['action']!=row['annotation']['action']:
            category,note=diagnoses[p['id']]
            errors.append(dict(id=p['id'],input=row['input'],annotation=row['annotation'],prediction=p,
                diagnostic_category=category,review_note=note,reviewer='assistant',human_review=False,
                disposition='retain frozen labels; diagnostic only; never copy/rewrite into training'))
    assert len(errors)==9
    last=pred['step-2976'];prev=pred['step-1488'];prev_index={p['id']:p for p in prev}
    fixed=[p['id'] for p in last if p['action']==by_id[p['id']]['annotation']['action'] and prev_index[p['id']]['action']!=by_id[p['id']]['annotation']['action']]
    regressed=[p['id'] for p in last if p['action']!=by_id[p['id']]['annotation']['action'] and prev_index[p['id']]['action']==by_id[p['id']]['annotation']['action']]
    result=dict(protocol_sha256=ph,coverage=dict(rows=11899,epochs=2,positions=23798,all_rows_exactly_twice=True),
        checked_source_files=len(protocol['source_sha256']),checkpoint_hashes_passed=True,
        metrics_recomputed=True,gate_recomputed=True,selection_unchanged=True,
        training_minutes=summary['training_elapsed_s']/60,peak_allocated_gib=summary['peak_allocated_gib'],
        training_loss_means=dict(first50=statistics.mean(r['loss'] for r in log[:50]),
            epoch1_last50=statistics.mean(r['loss'] for r in log[1438:1488]),last50=statistics.mean(r['loss'] for r in log[-50:])),
        development_probability={v:probability_metrics(rows,pred[v]) for v in VARIANTS},
        epoch1_to_epoch2=dict(fixed=fixed,regressed=regressed),gates=gates,
        holdout_used=False,new_model_calls=0,diagnosis='Improvement with high-confidence boundary errors; synthetic development cannot rule out overfitting.')
    jev.write(OUT/'audit.json',result);jev.write(OUT/'error-review.json',errors)
    return rows,reports,pred,result,errors


def finish():
    rows,reports,pred,audit_result,errors=audit()
    done=jev.read(jev.OUT/'completion.json');protocol=jev.read(jev.OUT/'protocol.json')
    assert done['status']=='complete' and done['requests']==1152 and done['protocol_sha256']==jev.digest(protocol)
    # Each exported response is checked against the exact canonical input and policy.
    for split in jev.SPLITS:
        cached=jev.read(jev.OUT/(split+'-predictions.json'));source=jev.source_rows(split)
        assert [p['id'] for p in cached]==[r['id'] for r in source]
        assert jev.file_sha(jev.DATA/f'evaluation/{split}.json')==protocol['split_sha256'][split]
        for row,p in zip(source,cached):
            assert p['request_sha256']==jev.digest(jev.payload(row)) and p['model']==done['model']
            ledger=jev.use_cached(jev.OUT/'requests'/split/(row['id']+'.json'),p['request_sha256'])
            restored=jev.normalize(row['id'],split,ledger['body'],ledger['elapsed_s'],p['request_sha256'],done['model'])
            restored['measured_at']=p['measured_at'];assert restored==p
        jev.write(PUBLIC/(split+'-predictions.json'),cached)
    jp=jev.read(jev.OUT/'development-predictions.json')
    jm=metrics.evaluate(rows,jp,jev.digest(protocol['specification']),done['protocol_sha256'])
    table=[];historical={}
    old=ROOT/'results/financial-eight-actions-pilot-v2'
    for variant in ['base','step-200']:
        saved=jev.read(old/variant/'metrics.json')
        rebuilt=metrics.evaluate(rows,predictions(old/variant/'predictions.jsonl'),saved['prompt_sha256'],saved['protocol_sha256'])
        if rebuilt!=saved or saved['data_sha256']!=jm['data_sha256']:raise ValueError('Historical 2B comparison mismatch')
        historical['2B-'+variant]=saved
        table.append(dict(variant='2B-'+variant,accuracy=saved['action_accuracy'],macro_f1=saved['macro_f1'],
            joint_tool=saved['action_tool_joint_accuracy'],human_misses=len(saved['human_misses']),
            false_refusals=len(saved['false_refusals']),unavailable_retrievals=len(saved['unavailable_knowledge_retrievals']),
            p50_ms=saved['latency']['p50_s']*1000,p95_ms=saved['latency']['p95_s']*1000))
    for v in ['base','step-1488','step-2232','step-2976','Jev']:
        m=jm if v=='Jev' else reports[v]
        table.append(dict(variant=v,accuracy=m['action_accuracy'],macro_f1=m['macro_f1'],
            joint_tool=m['action_tool_joint_accuracy'],human_misses=len(m['human_misses']),
            false_refusals=len(m['false_refusals']),unavailable_retrievals=len(m['unavailable_knowledge_retrievals']),
            p50_ms=m['latency']['p50_s']*1000,p95_ms=m['latency']['p95_s']*1000))
    qi={p['id']:p for p in pred['step-2976']};ji={p['id']:p for p in jp};gold={r['id']:r['annotation']['action'] for r in rows}
    paired=dict(qwen_right_jev_wrong=[i for i in gold if qi[i]['action']==gold[i] and ji[i]['action']!=gold[i]],
        jev_right_qwen_wrong=[i for i in gold if ji[i]['action']==gold[i] and qi[i]['action']!=gold[i]],
        both_wrong=[i for i in gold if qi[i]['action']!=gold[i] and ji[i]['action']!=gold[i]],
        qwen_minus_jev_cluster_interval=cluster_interval(rows,ji,qi))
    for e in errors:e['jev_prediction']=ji[e['id']]
    strata={}
    for profile in sorted({r['input']['capability_profile'] for r in rows}):
        rr=[r for r in rows if r['input']['capability_profile']==profile]
        strata[profile]=dict(rows=len(rr),qwen_accuracy=sum(qi[r['id']]['action']==gold[r['id']] for r in rr)/len(rr),
            jev_accuracy=sum(ji[r['id']]['action']==gold[r['id']] for r in rr)/len(rr))
    result=dict(comparison=table,paired=paired,capability_strata=strata,
        jev_development_metrics=jm,historical_2b_metrics=historical,jev_development_probability=probability_metrics(rows,jp),
        qwen_audit=audit_result,jev_completion=done,final_scored=False,
        scope='Development component comparison, not backend deployment acceptance; Jev parallel two questions vs Qwen conditional second pass.')
    jev.write(OUT/'comparison.json',result);jev.write(OUT/'error-review.json',errors)
    jev.write(PUBLIC/'protocol.json',protocol);jev.write(PUBLIC/'completion.json',done)
    jev.write(PUBLIC/'comparison.json',result);jev.write(PUBLIC/'qwen-error-review.json',errors)
    manifest={p.name:jev.file_sha(p) for p in PUBLIC.iterdir() if p.is_file() and p.name!='manifest.json'}
    jev.write(PUBLIC/'manifest.json',dict(files=manifest,purpose='Evaluation only, never teacher/training data',
        cache_validity='Exact payload hash, action/tool/policy definitions, dataset version, provider model and call strategy',
        final_visibility='Predictions cached without labels/score; scoring requires future fixed eligible candidate'))
    write_document(result,errors,reports)
    print(json.dumps({'comparison':table,'jev_completion':done,'paired_counts':{k:len(v) for k,v in paired.items() if isinstance(v,list)}},ensure_ascii=False,indent=2))


def write_document(result,errors,reports):
    done=result['jev_completion'];a=result['qwen_audit'];paired=result['paired']
    lines=['# Qwen3.5-0.8B结果复核与Jev固定对照','',
        '2026-10-02。本轮完成训练审计、全部9条动作错例复核，以及用户授权的一次Jev固定基准缓存。没有修改原始训练、标签、检查点或验收门槛，没有追加训练或部署。',
        '', '## 结论', '',
        '0.8B微调明显学到了本套金融八动作任务，但最后两条误拒绝仍违反预先固定门槛。原实验保持“不合格、未选出候选”；不会因Jev对照分数或人工阅读错误后改写该结论。',
        '本报告的同集比较只针对384条开发集：Qwen见过同任务训练数据，Jev按本轮可见政策零样本作答。它不是两种模型通用能力的排名，也不是线上真实用户验收。',
        '', '## 开发集效果与速度', '',
        '|版本|动作准确率|宏F1|动作与工具联合|人工漏判/64|误拒绝|请求P50 / P95 ms|',
        '|---|---:|---:|---:|---:|---:|---:|']
    for t in result['comparison']:
        lines.append(f"|{t['variant']}|{t['accuracy']:.2%}|{t['macro_f1']:.4f}|{t['joint_tool']:.2%}|{t['human_misses']}|{t['false_refusals']}|{t['p50_ms']:.1f} / {t['p95_ms']:.1f}|")
    lines += ['', '`2B-*`为上一轮Qwen3-VL-2B的NF4原始/200步结果，逐条重算确认同一384条开发集；其余base/step为本轮Qwen3.5-0.8B BF16。不同架构、精度、训练覆盖和预算不能用于断言更小模型天然更强。V5等旧四路由模型不具备本轮同一八动作输出契约，未强行塞进此表。',
        '动作准确率按384条完整输入计算；动作与工具联合准确率只在64条真实查询需求上计分，必须动作与工具名都正确。非查询预测不借用正确工具答案。人工漏判是应选human却选其他动作；误拒绝是合法的非refuse请求被拒绝。',
        'Jev一次HTTPS请求并行回答动作和假设性工具问题，程序仅在其动作预测为tool时使用工具答案；Qwen先判断动作，只有tool再前向一次。两者共享业务政策、动作/工具定义和规范化可见输入，但接口和计算方案不同。',
        'Jev耗时包含本机到云端网络；Qwen包含分词、传输、动作及条件工具推理，排除模型加载与预热。分阶段实测没有交错，功耗/温度/系统负载可能不同；这里比较当前调用方案，不能把差值全归因于模型架构，也不能保证下一次网络延迟相同。',
        '此次Jev不沿用旧四路由/79条数据的高分。新八动作、合成状态、能力开关和可见提示均不同。尤其已给状态码仍要求调用解释工具、能力不足升级人工等标签体现本项目的决策约定；训练后的Qwen已反复接触这些约定，Jev只看到精简政策与候选说明。没有根据本次错题优化Jev提示并反复请求，因此当前Jev成绩不是供应商能力上限。',
        '', '### 分动作召回率', '', '|动作|样本数|Qwen最终步|Jev|','|---|---:|---:|---:|']
    qm=reports['step-2976'];jm=result['jev_development_metrics']
    for k,v in qm['per_action'].items():lines.append(f"|{k}|{v['support']}|{v['recall']:.2%}|{jm['per_action'][k]['recall']:.2%}|")
    lines += ['', '### 当前能力和规划能力', '', '|能力档位|条数|Qwen动作准确率|Jev动作准确率|','|---|---:|---:|---:|']
    for k,v in result['capability_strata'].items():lines.append(f"|{k}|{v['rows']}|{v['qwen_accuracy']:.2%}|{v['jev_accuracy']:.2%}|")
    ci=paired['qwen_minus_jev_cluster_interval']['interval95']
    lines += ['', f"成对结果：Qwen对/Jev错{len(paired['qwen_right_jev_wrong'])}条，Jev对/Qwen错{len(paired['jev_right_qwen_wrong'])}条，两者都错{len(paired['both_wrong'])}条。按8个宏故事重采样，Qwen−Jev动作准确率差的95%描述区间为{ci[0]*100:.2f}～{ci[1]*100:.2f}个百分点。合成故事组很少，该区间不是真实业务总体置信保证。",
        '', '## 九条错误复核', '', '|ID末四位|应选 → Qwen|Jev|复核说明|','|---|---|---|---|']
    for e in errors:
        lines.append(f"|{e['id'][-4:]}|{e['annotation']['action']} → {e['prediction']['action']}|{e['jev_prediction']['action']}|{e['review_note']}|")
    lines += ['', '复核者为本助手，不等于用户或外部专家人工验收。完整上下文、原始标签、概率与Jev回答在`docs/evidence/financial-jev-reference-v1/qwen-error-review.json`。所有错题仅用于解释局限，不直接或改写回填训练，不修改冻结标签。',
        '', '## 训练完整性与过拟合判断', '',
        f"2,976步日志连续，11,899条各见两次，共23,798次样本处理；24个冻结源码文件及全部候选检查点校验通过，指标和门槛从逐条预测重新计算一致。纯训练累计{a['training_minutes']:.1f}分钟，峰值allocated显存{a['peak_allocated_gib']:.2f}GiB。",
        f"前50步平均loss {a['training_loss_means']['first50']:.4f}，第一轮末50步{a['training_loss_means']['epoch1_last50']:.4f}，最终50步{a['training_loss_means']['last50']:.4f}。第一轮到第二轮改对{len(a['epoch1_to_epoch2']['fixed'])}条、改错{len(a['epoch1_to_epoch2']['regressed'])}条；整体开发准确率提高，但人工漏判由1条升到3条。不能仅用平均准确率掩盖局部回退。",
        '没有看到整体开发准确率随长训下降，但不能据此排除过拟合。开发集参与检查点评估，只有8个合成宏故事，训练与评估共享业务规则/模板风格；真实用户、多模态和完整后端行为都未检验。',
        '', '|概率诊断|Qwen原始|Qwen最终步|Jev|','|---|---:|---:|---:|']
    bp=a['development_probability']['base'];qp=a['development_probability']['step-2976'];jp=result['jev_development_probability']
    for key in ['nll','brier_sum_over_classes','ece10']:
        lines.append(f'|{key}|{bp[key]:.4f}|{qp[key]:.4f}|{jp[key]:.4f}|')
    lines += ['', f"Qwen最后9条错误中有{qp['errors_confidence_ge_09']}条预测概率≥90%。NLL（正确标签负对数概率）、Brier（各类概率平方误差和）和ECE（10个固定置信度桶的偏差）只是本开发集诊断；未在这里拟合温度。较低的平均ECE不代表不存在高置信度错误。",
        '', '## Jev缓存范围、费用与复用', '',
        f"完成{done['requests']}次请求：开发384、校准256、最终512。实际模型固定为`{done['model']}`，没有重试。输入用量{done['input_tokens']:,} token；按供应商公布输入$0.042/百万token、输出免费估算为 **${done['estimated_input_cost_usd']:.5f}**，实际账单以供应商为准。",
        '来源：[官方定价说明](https://typesafe.ai/blog/introducing-system-one-models-and-jev)、[官方并行问题说明](https://docs.typesafe.ai/introduction)。只请求已有合成评估数据，没有发送训练集或本地密钥文件内容。',
        '校准与最终集本轮仅存Jev概率/预测，不输出最终成绩，也不让未合格Qwen进入最终测试。未来通过开发门槛的固定候选可以直接与缓存比较，无需重付同一批Jev调用。缓存不允许作为教师蒸馏或训练标签。',
        '完整便携缓存：`docs/evidence/financial-jev-reference-v1/`，包含三个分区预测、业务政策、供应商实际版本、请求指纹、用量、耗时和文件清单。原始逐次请求状态仅保存在忽略目录`results/financial-jev-reference-v1/requests/`。',
        '缓存的有效条件：样本、标签版本、可见状态序列化、Jev提示/选项、动作与工具定义、调用方案一致。更换上述协议必须建立新基准，不能把旧缓存改名冒充新评测；供应商后来升级不会改变这份历史参考。缓存的速度是本次历史网络测量，不是以后训练时的实时Jev延迟。',
        '', '```powershell', '# 项目根目录：只读复核，不联网、不用GPU',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.financial_reference_report audit',
        '# 使用已导出缓存比较开发预测，API调用数为0',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.financial_jev_cache --predictions results/financial-qwen35-v1/development/step-2976/predictions.jsonl',
        '# 缓存进度；已经完成时无需再次启动付费命令',
        '.\\.venv\\Scripts\\python.exe -m qwenlab.financial_jev_reference progress',
        '```', '',
        '若只克隆仓库，可读取已上传的便携缓存与对照JSON；完整训练审计还需要本地权重、检查点和原始日志。新候选的开发预测应遵循现有id/action/tool_name/action_prediction/elapsed_s字段，不把校准或最终预测传给开发集比较命令。',
        '', '## 下一步建议', '',
        '保留此次检查点作研究对照，保持现有服务配置。下一轮优先补充独立来源的否定范围、本人/他人归属、工具可用性、人工优先级以及规则检索/目录查询边界；先写清规则，再做成组数据和独立验证，禁止复制本轮开发错题或改写后训练。暂不继续盲目加轮次。',
        '本轮“相对原始模型不得新增误拒绝”的门槛，在原始模型几乎不拒绝且整体准确率很低时具有不对称性。这是未来应预先讨论的验收设计问题，不是修改本轮失败结论的理由。未来可在新协议中联合约束违规请求召回和合法请求误拒率，并按业务成本预注册阈值。',
        '如需增强Jev的项目规则表现，应先从完整业务契约（而不是本次错题）明确冲突优先级，在新版本单独比较；本轮不会自动再付费调提示。模型判定与后端白名单/权限保护继续分开计分，知识检索和人工接通需要后续实际工程验收。', '']
    path=ROOT/'docs/40-Qwen3.5结果复核与Jev固定对照.md'
    path.write_text('\n'.join(lines),encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['audit','finish']);a=p.parse_args()
    if a.command=='audit':
        _,_,_,result,_=audit();print(json.dumps(result,ensure_ascii=False,indent=2))
    else:finish()
