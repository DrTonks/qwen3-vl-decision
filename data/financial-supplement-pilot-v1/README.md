# 金融客服补充候选：首批160条

当前入口：`reviewed-v1/accepted.json`，独立AI复核接受158条，仍为候选、`training_eligible=false`；`reviewed-v1/quarantine.json`隔离2条，禁止混入训练。没有新增模型成绩，也未人工复核。

## 文件分工

|文件|用途|
|---|---|
|`authoring.json`|**唯一人工编辑入口**，160条场景、可信服务上下文、预期动作/工具/参数/理由|
|`build-v2/REVIEW.md`|按ID逐条阅读当前消息、历史、服务端state与模型state、工具名单和标注理由|
|`build-v2/candidates.json`|真实Node投影及明确组件变换后的全部160条，保存作者标注快照|
|`build-v2/node-contexts.jsonl`、`node-projections.jsonl`|预处理前后可核验记录；不是客户端授权数据|
|`build-v2/audit.json`|结构、内部词面重复与本地token长度检查|
|`build-v2/blind-overlap.json`|隔离脚本对旧集合做词面筛查，仅输出新候选标识，不暴露旧题面|
|`reviewed-v1/manifest.json`|最终审核分流与文件/双审SHA绑定，不是训练许可|
|`build-v1/`|首稿历史；不得混入最新版，不能用当前作者源假装复现旧版|
|`history/authoring-v1.json`|首稿作者源的归档，160条行哈希及原文件SHA均与v1记录一致|

独立标签、代码及包装审核保存在仓库`docs/evidence/financial-supplement-pilot-*-review*.json`。`build-v2`中的“pending”表示构建当时的作者快照；当前审核状态以`reviewed-v1`及对应独立报告为准。

## 怎么编辑

1. 在`authoring.json`搜索样本ID。先读`context.message/history/state/authenticated/availableTools`，再决定标签。
2. `expected_action`取八动作之一；只有tool可填`expected_tool/tool_arguments`；只有retrieve可填正式集合；缺槽只用于clarify。写清`label_reason`，不要只按关键词标注。
3. 不要在服务端context手填`application_id/status_code`，参数由真实Node提取。当前服务没有知识库；未来知识输入在独立层模拟，不能改成“已上线”。同一`source_group`连同变体一起划分数据，不能跨训练/评估拆散。
4. 修改后重新构建**新目录**，旧审核SHA会失效，需要独立复核修订和相关组。不要直接改`accepted.json`、Markdown复查页或旧manifest来宣布通过。

在qwen仓库根目录执行：

```powershell
. .\scripts\use-env.ps1
# 当前版本验证：需实际相邻后端代码，离线，无模型/API/数据库。
.\.venv\Scripts\python.exe -m qwenlab.financial_supplement_pilot verify --backend ../uestc_Integrated_Design/后端 --output data/financial-supplement-pilot-v1/build-v2
# 编辑后新建版本，示例v3；已存在目录会拒绝覆盖。
.\.venv\Scripts\python.exe -m qwenlab.financial_supplement_pilot build --backend ../uestc_Integrated_Design/后端 --output data/financial-supplement-pilot-v1/build-v3
.\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_supplement_pilot audit --backend ../uestc_Integrated_Design/后端 --output data/financial-supplement-pilot-v1/build-v3 --tokenize
```

候选构建不自动进行评估集筛查、独立复核、训练或发布；后三者不可因结构检查通过而跳过。完整方法、局限、筛查命令和下一阶段看[报告50](../../docs/50-金融客服首批160条补充候选与独立复核.md)。
