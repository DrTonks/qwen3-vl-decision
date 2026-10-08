# 金融客服补充池扩展批次 B：作者说明

本批次为 AI 原创合成数据，不是真实客户会话。作者已在编写时逐条自查消息、动作、工具、能力与认证条件，并运行真实 Node 参数解析检查；截至本文件形成时，**尚未经过独立复核，不代表生产可用性或经过认证的评估质量**。应先交独立审核者审阅，再决定哪些条目可纳入补充池。

## 文件与来源范围

- 作者源：`batch-b.authoring.json`。
- 可复现编写脚本：`build-b.py`；输出目录由脚本自身位置推导，不含本机绝对路径。
- 仅据项目的 `configs/support-financial-v2.json`、相邻后端的 `services/customerSupport/tools.js` 和 `services/customerSupport/parameters.js` 确认范围、可见字段和解析约束。
- 首批 `data/financial-supplement-pilot-v1/authoring.json` 仅用于确认字段结构、历史消息形状和枚举，不复用场景。未读取 A 批文本，也未读取旧评估、挑战、预测、报告错例或盲筛内容。
- 未训练、未请求推理 API、未访问数据库、未调用真实业务工具、未修改后端或推送代码。

## 实际规模

共 760 条、191 个独立核心情境的来源组；189 组各 4 条、2 组各 2 条，每组不超过 4 条。ID 采用 `SEB-G001-1` 形式，来源组为 `SEB-G001` 形式。

| 维度 | 数量 |
| --- | ---: |
| current-service | 570 |
| current-service / node-projection | 428 |
| current-service / component-message-only | 142 |
| planned-retrieval / planned-capability-component | 114 |
| preauth-robustness / preauth-component | 76 |
| 含可见历史 | 200 |
| 含 pending 或 selectedApplicationId 状态 | 7 |
| 含显式工具可用性列表 | 96 |

当前服务输入层占比为 75.09% Node 投影、24.91% 组件消息。全部 191 组均包含不同动作的对照，超过 40% 下限；这只是设计对照，不等于独立审核通过率。

| 动作 | 数量 |
| --- | ---: |
| clarify | 137 |
| tool | 142 |
| answer | 178 |
| human | 155 |
| retrieve | 76 |
| redirect | 11 |
| refuse | 46 |
| close | 15 |

工具分布：`queryApplicationDetail` 80、`queryMyApplications` 23、`queryMyCreditScore` 17、`queryLoanProducts` 13、`explainApplicationStatus` 9。

## 情境与作者自查

每个来源组显式编写最多四条消息，没有通过模板笛卡尔积生成样本。侧重反复沟通、已知结果复述、用途与金额纠错、授权边界、争议凭证、收款信息、字段不可查、跨页面查询、资料副本与隐私请求；号码只是合成情境里的定位标识。少量缺工具对照与未认证对照用于区分“缺少认证”和“当前能力不存在”。公开联系方式中的 `.invalid` 地址是保留域名的合成示例，不代表平台真实联系方式。

逐条核对遵循下列边界：

- 当前环境没有 KB，未知规则只能说明限制，当前样本无 retrieve。
- 正式知识检索只放入 planned-capability-component；collection 仅填 `loan_service_docs` 或 `privacy_policy`，不向 context 添加知识库字段。
- 未认证上下文显式设 `availableTools: []`；76 条中没有工具动作。受支持查询缺认证为 clarify，合法但未实现个人业务为 human。
- component-message-only 的工具参数必须从消息正文解析；依赖 pending 或 selectedApplicationId 的工具例放在 node-projection。
- `state` 只含 pending、selectedApplicationId；上下文只含 message、authenticated、history、state 和可选 availableTools。
- 列表、明细、信用与产品字段均按现有实现限定；未补造申请时间、拒贷原因、合同、还款表、收款账户、实时利率或个人写入工具。
- 区分引用或报告违规文字、能力询问与实际实施禁止操作；明确人工请求优先进入 human；普通致谢不误标 close。

最后一次作者检查通过：760 个唯一 ID、760 条唯一正文；191 个唯一来源组；全部工具可用性和认证断言；所有详情/状态工具参数经过**实际运行现有 `parameters.js` 的 Node 解析器**验证，组件工具另以清空 state 的上下文重新验证。申请编号与状态码缺槽样本也检查了不能产生有效唯一参数。未进行数据库归属验证或业务执行，因此这里的“本人”是合成用例前提，不能声称查到了任何实际记录。

运行 `python data/financial-supplement-expansion-v1/build-b.py` 可重建作者源并重复结构与参数断言；应从项目根目录执行。该脚本只负责作者源，不替代独立语义审核或后续 materialize 投影检查。

## 局限与交接

暂无作者隔离条目；这不等于独立审核无需隔离。动作比例未硬贴目标：human 和 answer 偏多，tool 与 redirect 偏少，原因是本批次重点覆盖未实现个人字段和已知信息解释。没有为满足比例把合法业务错误标成工具或拒绝。

合成文字较整洁，若干能力询问和缺槽表述有意明确；自然噪声、极短口语和真实用户分布覆盖有限。标签理由采用“情境名 + 动作依据”，仍需独立审核逐条确认。来源组只是同一核心故事的变体边界，并不能证明与其他批次语义完全不重叠。应由合并方另外检查跨批次近重复、全输入标签冲突及真实 Node 投影，再决定发布、保留或隔离。
