# 补充扩展批次 A：作者说明

本文件是作者自查记录，不是独立复核结论。输出为 `data/financial-supplement-expansion-v1/batch-a.authoring.json`，正式可复现作者脚本为 `data/financial-supplement-expansion-v1/build-a.cjs`。脚本以自身位置的 `../..` 推导工作根目录，不依赖机器绝对路径。整理正式脚本时只调整根目录推导，未执行覆盖已稳定的来源 JSON。

## 实际规模

- 760 条、191 个来源组，ID 为 `SEA-G001-1` 至 `SEA-G191-4`。每组最多 4 条，两组为 2 条。
- current-service：552 条，涉及 143 组；其中 node-projection 420 条、component-message-only 132 条，约 76.1% / 23.9%。
- planned-retrieval：114 条，29 组，均为 planned-capability-component。
- preauth-robustness：94 条，涉及 33 组，均为 preauth-component，可信 authenticated 均为 false。
- 依照构建器的认证一致性约束，将原 current-service 中 18 条真实未登录场景改归 preauth-robustness，并仅同步 input_layer 为 preauth-component。认证值、消息、标签和参数均未改变。14 个来源组同时包含已登录与未登录对照，因此各 cohort 涉及组数不可相加。总计仍为 191 组、760 条。
- 190 / 191 个组具有动作或认证/工具可用条件对照；最后一个计划层组以不同正式集合的公开联系方式问题作对照。

| 动作 | 条数 |
| --- | ---: |
| clarify | 127 |
| tool | 168 |
| answer | 140 |
| human | 135 |
| retrieve | 78 |
| redirect | 30 |
| refuse | 49 |
| close | 33 |

未为了逼近目标比例改写正确动作。clarify 与 tool 略少于指导比例，human、refuse、close 略多。组内对照保持实际业务含义，不采用后缀、数字或问候的笛卡尔积扩增。

## 来源与创作范围

依据 `configs/support-financial-v2.json` 的策略与动作定义，以及相邻项目 `../uestc_Integrated_Design/后端/services/customerSupport/tools.js` 和 `parameters.js` 的工具字段、认证和参数边界创作。首批 `data/financial-supplement-pilot-v1/authoring.json` 仅用于确认字段结构、集合名、history 结构和 missing_slots 词表，不作为场景来源。

没有读取旧评估、挑战、预测、失败报告、48 错例或盲筛内容；没有调用模型 API、训练、数据库或远程业务服务。所有经营主体、采购内容和编号均为合成情境，不表示真实客户记录。

每个组在作者脚本中有独立标题及明确写出的消息。覆盖金额和用途核对、待审批与到账区别、额度空值、列表截断、产品 ID 与名称、真实材料补交、正式规则与实际办理、签约与个人信息权利、引用和否定违规文本、游客自称授权及域外事项等。职业和采购物品不同不是独立性证明；若独立审核认为同一决策模式仍高度重复，应保留整组边界进行降权或隔离。

## 作者自查

逐条核对动作、参数、认证、工具可用性、消息自身所含槽值和情境含义。自动检查结果：

- 760 个唯一 ID；字段顺序与原 FIELDS 一致；context 只有 message、authenticated、history、state 和可选 availableTools。
- state 仅使用 pending、selectedApplicationId；消息最大 47 字，history 不超过 4 条且单条不超过 800 字。
- 工具动作均已认证且不超出可见 availableTools。所有工具动作使用原 `parameters.js` 做参数核验，0 个不一致。
- 对 component-message-only 的工具行移除 state、history 后，正文仍可独立解析唯一必要参数，0 个隐藏参数问题。
- current-service 没有 retrieve，preauth-robustness 没有 tool。retrieve 仅使用 loan_service_docs 或 privacy_policy。
- missing_slots 沿用 applicationId、statusCode、request_intent、authentication 命名。
- 无同一输入重复或标签冲突；每组最多 4 条；190 组具有不同动作或认证/能力条件。

计划层不在 context 添加知识集合字段。正式集合可用性需由现有 materialize 流程按 retrieval_collection 投影；非 retrieve 的计划层样本采用该流程的默认正式业务集合。

## 局限与交接

本批采用清晰短消息为主，复杂长对话、口语省略和错别字覆盖较少；业务表达中会重复出现同一策略边界，不能把 760 条当作 760 个完全独立的政策问题。来源组是作者的合成情境组，不是独立采集的外部真实会话。

本地自查没有替代真实导出器的逐层重放，也不是模型效果测试。请独立审核者结合原始消息及实际投影检查标签；有分歧的条目先隔离，避免作者自证。所有组应整体进入或退出同一数据分区，防止相邻对照泄漏。
