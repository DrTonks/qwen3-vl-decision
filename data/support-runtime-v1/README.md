# 当前客服决策场景集 v1：AI 预标注，待人工复核

这份数据用于验证当前项目“用户输入 → Jev/Qwen 决策 → 后端动作与参数校验”的表现。它覆盖当前五个只读工具和六个后端动作，独立保留合理业务期望，**不会为了让当前实现通过而修改答案**。

共 **139 条、38 个场景组**。标签由 AI 在调用模型前预先填写，尚未人工确认；结果只能称为“AI 预标注场景上的测试”，不能称为真实业务准确率或人工金标。旧 `data/support-design-v1/` 的 400 条讨论稿保持不变。

## 文件

|文件|用途|
|---|---|
|`cases.jsonl`|评测输入及预期标签；一行一个 JSON 对象，当前评测读取此文件。|
|`review.csv`|与案例对应的人工编辑表，UTF-8 BOM，适合用 Excel 打开；修改后需要合并回 JSONL 才会影响评测。|
|`deferred-cases.jsonl`|9组未来能力说明，含 retrieve/redirect、知识证据、页面状态、合同材料查询、人工受理等，不计当前总分。|
|`manifest.json`|数量、范围、fixture约定与冻结时文件哈希。|
|`authoring.py`|本版 AI 起草场景的生成来源；输出存在时会拒绝覆盖，避免抹掉成员修改。不是日常编辑入口。|

本版冻结的 `cases.jsonl` SHA256：

```text
f6c67a9af3cbea4c2ec49e1a58fd8294e4edfb8ad8417317a48c760d4530c1d4
```

## 测什么，以及不代表什么

当前工具：`queryLoanProducts`、`queryMyApplications`、`queryApplicationDetail`、`queryMyCreditScore`、`explainApplicationStatus`。

当前最终动作：`tool / clarify / answer / human / refuse / close`。决策模型仍是 `tool / clarify / llm / human` 四路由；`llm` 映射为 `answer`，部分人工、拒绝和关闭动作由后端规则处理。`expected.route` 或 `intent` 为 null 的样本只验最终业务行为，不强行编造旧模型中不存在的类别。真正调用了模型多少次、被规则直接处理多少次，必须分别报告。

- 这是**决策组件评测**，不执行真实数据库查询、支付或审批。输入中没有账号密钥、手机号或登录令牌；登录身份由真实后端鉴权，不能由模型决定。
- 76001、76003 是同一构造用户的申请；76002 是他人申请，仅用于拒绝越权。不得将编号直接套进其他数据库并假设归属相同。
- `state.pending`、`state.selectedApplicationId` 是由同条 `history` 可解释的服务端状态夹具；不会因为把这些字段写进 App 请求就自动接通。真正端到端测试需先执行历史轮次，验证系统能建立相同状态。
- `pending=statusCode` 场景验证明确追问后的数字补槽。若后端没有产生、保存或传递此状态，应登记为流程缺口；不能据组件通过宣称完整会话链路已实现。
- 本版没有模拟 facts/ui/knowledge/retry_count 等目前未传入模型的字段。已有查询结果解释、页面事实解释、检索后回答等放入未来能力文件。
- 普通申请、还款流程及范围外咨询当前归 `answer/llm`，期望回复层仅解释已知情况或引回服务范围。**选中 answer 不等于已完成知识检索，更不代表模型可以编造利率、费用或审批承诺。** 回复内容正确性需要单独验收。
- human 只验应交人工处理的判断及当前诚实降级；当前没有真实工单/转接能力，不能称为转接成功。
- 同组口语变体相关，不能把139条当139个独立业务场景。应同时按案例和38组统计；以后训练数据不能混入同组测试变体。

## 人工如何编辑

建议先复制整个目录为新的审核版本，或把 `review.csv` 复制到 `.local/review/`，保留本版冻结数据和已出测试结果。请勿修改旧文件却继续使用旧哈希解释结果。

用 Excel 打开 `review.csv`，每行检查以下内容：

|列|如何调整|
|---|---|
|`id` / `group`|已有案例不要改ID；同一原始场景的改写保持同组。新增案例使用新ID，有不同业务边界时建立新组。|
|`message`|改成用户自然表达，避免只写能被现有关键词识别的句式。不要填真实身份证、手机号、合同或银行卡信息。|
|`history_json`|最多保留当前所需的短上下文，内容使用标准JSON数组，角色为 user/assistant。|
|`state_json`|只使用 pending 与 selectedApplicationId；字段需能从历史解释，不能暗中加入正确意图或答案。|
|`expected_action`|填六种当前动作之一；未来 retrieve/redirect 放入 deferred，不直接混进当前总分。|
|`expected_tool`|只有 tool 动作填写工具名，其他动作留空。|
|`expected_arguments_json`|详情为 `{"applicationId":76001}`；状态释义为 `{"status":2}`；其他工具和非工具动作为 `{}`。|
|`expected_route`|模型应选的 tool/clarify/llm/human；只验后端守卫的场景可留空。|
|`expected_intent`|下方11种意图之一；无法明确或仅验守卫时可留空。|
|`rationale`|写业务理由，不写“模型预测是这个所以选这个”。|
|`review_status`|AI初稿为 ai_preannotated；人工确认可用 accepted，修改后 revised，有分歧 needs_discussion，剔除 excluded。|
|`reviewer` / `notes`|填审核者代号和具体理由。公开版本不要保留个人敏感信息。|
|`taxonomy_approved`|团队已确认这条动作边界才填 true；未确认保持 false。|

意图枚举：

```text
products, applications, application_detail, credit, status_code,
ui_issue, repayment, payment_dispute, security, handoff, general
```

示例：用户写“同事说可以查信用分，帮我查我的信用分”，应根据“我”确定查询本人，不能因为出现“同事”就拒绝。反之，“帮我查同事的信用分”应拒绝越权。编号解析、安全守卫和模型分类可能各有问题，验收时应区分错误发生在哪一层。

**CSV 只是编辑视图，不会自动覆盖 `cases.jsonl`。** 保存修改后，用下面的导入命令生成新版本。不要直接修改 manifest 伪装旧数据未变；也不要运行 authoring.py 试图保留修改后重新生成。

若直接编辑 JSONL，所有 `expected` 与输入字段含义同上；null 使用 JSON 的 `null`，不能用空字符串替代。一行完整 JSON，不能跨行展开或加注释。

## 把人审CSV导入可运行版本

在 `qwen` 仓库根目录运行。先创建审核副本，已有副本时不要重复覆盖：

```powershell
New-Item -ItemType Directory -Force .local/review | Out-Null
if (Test-Path .local/review/support-runtime-v1-team.csv) { throw '审核副本已存在，请直接编辑它，不要覆盖。' }
Copy-Item data/support-runtime-v1/review.csv .local/review/support-runtime-v1-team.csv
```

使用 Excel 或文本编辑器修改副本，保存为 **CSV UTF-8**，然后导入：

```powershell
.\.venv\Scripts\python.exe -m qwenlab.support_review import `
  --source data/support-runtime-v1 `
  --csv .local/review/support-runtime-v1-team.csv `
  --output .local/review/support-runtime-reviewed-v1
```

导入工具会检查原始数据哈希、ID是否完整且唯一、JSON是否合法、动作与工具参数是否一致、历史长度和角色、状态字段与基本上下文、枚举值。ID、group、source_ids必须与原始集对应；这一步不支持新增案例，新增场景另建版本。

- `ai_preannotated / accepted / revised` 写入新版本 `cases.jsonl`，可用于评测。
- `needs_discussion / excluded` 写入 `review-holdouts.jsonl`，不计当前总分；仍保留在完整 `review.csv` 中，不会丢掉。
- 未决或排除记录的字段仍需符合当前格式；未来动作请写入 notes 或 deferred 文件，不要把 retrieve 填成当前六动作标签。
- `review-changes.jsonl` 记录哪些ID改了哪些字段；manifest记录来源数据、审核CSV及新数据的哈希和状态数量，不包含本机绝对路径。
- 新目录已存在时拒绝覆盖。下次使用新的输出目录名；也可将已导入版本作为 source 继续审核，未决记录仍可以重新纳入。
- AI标注不能同时声明 `taxonomy_approved=true`。人工确认后先把状态改为 accepted/revised，再按团队是否确认动作规范填写 true/false。

新版本的评测输入是 `.local/review/support-runtime-reviewed-v1/cases.jsonl`。评测时指向这个新目录，并在报告中记录它的 manifest 哈希；仍运行原目录只会评测旧标签。全部记录被排除时会生成空的active集并明确提示，不应计算准确率。

导入校验只能发现格式和部分约束问题，不能替成员判断业务标签是否正确。例如登录归属、是否真的需要人工，以及历史是否足以支撑状态，仍需要人工审核。

## 阅读顺序与复核重点

先看 R05–R21 的编号、金额、状态、补槽及改口，再看 R27–R35 的安全规则误拒与必要升级，最后看 R36–R38 的结束和重开。R23–R26 的回复质量需要后续知识检索/回复模型单独评估；本版只验证路由。

正确结果应区分最终动作准确率、工具加参数联合正确率、模型调用子集路由/意图结果，以及按场景组的错误分布。不要把守卫直接处理的样本全算成 Jev 或 Qwen 的分类功劳。
