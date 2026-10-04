# 八动作首批逐条复核

助手起草/重新标注；新版本未人工复核。所有条目仅为训练候选，不是测试金标。模型只读input，不读annotation/provenance/review。

## clarify

### FIN-P1-F06-B-01-base

查申请6000元的那笔

- 来源：business_policy_migration / F06-B-01-base；同源组：business:F06
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F06-B-02-base

我周一提交了申请，帮我看那笔详情

- 来源：business_policy_migration / F06-B-02-base；同源组：business:F06
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F09-A-01-base

查申请85011或85013的详情

- 来源：business_policy_migration / F09-A-01-base；同源组：business:F09
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F09-A-02-base

申请85011和85013，帮我查那笔

- 来源：business_policy_migration / F09-A-02-base；同源组：business:F09
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F13-A-01-base

状态码1或2是什么意思

- 来源：business_policy_migration / F13-A-01-base；同源组：business:F13
- 复核状态：needs_discussion；可能是在同时询问两个状态，而非缺少状态；旧澄清标签未必成立，暂不纳入可选训练候选。
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F13-A-02-base

页面状态是1/2，我没看清

- 来源：business_policy_migration / F13-A-02-base；同源组：business:F13
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F16-B-01-base

材料上传按钮是灰色的怎么回事

- 来源：business_policy_migration / F16-B-01-base；同源组：business:F16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F16-B-02-base

我点补交资料没有反应

- 来源：business_policy_migration / F16-B-02-base；同源组：business:F16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F22-B-01-base

那个不对，帮我处理一下

- 来源：business_policy_migration / F22-B-01-base；同源组：business:F22
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-F22-B-02-base

就是刚才那个，有问题

- 来源：business_policy_migration / F22-B-02-base；同源组：business:F22
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU04-01-fresh

选择图片以后没有出现上传结果，我没看清具体提示，先怎么排查？

- 来源：business_policy_migration / EU04-01-fresh；同源组：business:EU04
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU04-02-fresh

现在遇到选择图片以后没有出现上传结果，需要补充什么信息？

- 来源：business_policy_migration / EU04-02-fresh；同源组：business:EU04
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU05-01-fresh

个人信用页面一直显示加载中，我没看清具体提示，先怎么排查？

- 来源：business_policy_migration / EU05-01-fresh；同源组：business:EU05
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU05-02-fresh

现在遇到个人信用页面一直显示加载中，需要补充什么信息？

- 来源：business_policy_migration / EU05-02-fresh；同源组：business:EU05
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU06-01-fresh

申请详情页面打不开，我没看清具体提示，先怎么排查？

- 来源：business_policy_migration / EU06-01-fresh；同源组：business:EU06
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU06-02-fresh

现在遇到申请详情页面打不开，需要补充什么信息？

- 来源：business_policy_migration / EU06-02-fresh；同源组：business:EU06
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU10-01-fresh

申请表提交时跳出提示但我没记下内容，我没看清具体提示，先怎么排查？

- 来源：business_policy_migration / EU10-01-fresh；同源组：business:EU10
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU10-02-fresh

现在遇到申请表提交时跳出提示但我没记下内容，需要补充什么信息？

- 来源：business_policy_migration / EU10-02-fresh；同源组：business:EU10
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU16-01-fresh

申请页面的选项无法选择，我没看清具体提示，先怎么排查？

- 来源：business_policy_migration / EU16-01-fresh；同源组：business:EU16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-EU16-02-fresh

现在遇到申请页面的选项无法选择，需要补充什么信息？

- 来源：business_policy_migration / EU16-02-fresh；同源组：business:EU16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

### FIN-P1-massive-train-12123-loan-adaptation

我还没有说明要看哪份申请，请先帮我确认查询对象。

- 来源：public_loan_adaptation / massive-train-12123；同源组：massive:massive-train-12123
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：重写为对象缺失的贷款查询；缺的是申请对象。

### FIN-P1-contrast-login-1

把本账户已经记录的评分数值调给我。

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:login
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：未登录不能查个人评分；追问/引导完成认证。

### FIN-P1-contrast-object-1

请打开我刚才指定的那份借款申请明细。

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:object
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：没有历史与选中编号，无法落地单笔查询。

### FIN-P1-contrast-known-text-1

能说明当前页面那条材料格式提示的意思吗？

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:known-text
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少所指提示原文，先请用户提供文字。

### FIN-T2-A-clarify-detail-unselected-01

把我那张申请单的明细打开，具体号码我没说。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-detail-unselected
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：要求一笔明细却没有编号或可确认对象，不能随机选一笔。

### FIN-T2-A-clarify-detail-unselected-02

查那一笔的详细信息吧，我还没指定是哪笔。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-detail-unselected
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：要求一笔明细却没有编号或可确认对象，不能随机选一笔。

### FIN-T2-A-clarify-detail-unselected-03

想看某一条申请，先别随便替我选。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-detail-unselected
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：要求一笔明细却没有编号或可确认对象，不能随机选一笔。

### FIN-T2-A-clarify-detail-unselected-04

打开我说的那份借款详情，你先确认要查哪份。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-detail-unselected
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：要求一笔明细却没有编号或可确认对象，不能随机选一笔。

### FIN-T2-A-clarify-two-options-01

就看其中那一笔的详情。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-two-options
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我记下了本人申请号86121和86122，目前没有选定查询对象。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：两个候选对象均存在但未选择，单笔工具需要一个明确编号。

### FIN-T2-A-clarify-two-options-02

不用两笔一起看，挑我想查的那张。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-two-options
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我记下了本人申请号86121和86122，目前没有选定查询对象。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：两个候选对象均存在但未选择，单笔工具需要一个明确编号。

### FIN-T2-A-clarify-two-options-03

我说的是那份申请，你知道该打开哪条吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-two-options
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我记下了本人申请号86121和86122，目前没有选定查询对象。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：两个候选对象均存在但未选择，单笔工具需要一个明确编号。

### FIN-T2-A-clarify-two-options-04

先查一笔明细，但我还没决定是哪一份。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-two-options
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我记下了本人申请号86121和86122，目前没有选定查询对象。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：两个候选对象均存在但未选择，单笔工具需要一个明确编号。

### FIN-T2-A-clarify-time-reference-01

我要直接看前阵子交的那笔详细资料。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-time-reference
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：仅凭相对日期不能直接落地单笔编号，需要明确对象。

### FIN-T2-A-clarify-time-reference-02

帮我打开上个月那个申请，编号没带来。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-time-reference
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：仅凭相对日期不能直接落地单笔编号，需要明确对象。

### FIN-T2-A-clarify-time-reference-03

查我以前提交的那张单子详情，忘了号码。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-time-reference
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：仅凭相对日期不能直接落地单笔编号，需要明确对象。

### FIN-T2-A-clarify-time-reference-04

不是整份列表，我只想打开上次那一单。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-time-reference
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：仅凭相对日期不能直接落地单笔编号，需要明确对象。

### FIN-T2-A-clarify-bad-id-text-01

我的编号写成X8?，按这个查申请明细。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-bad-id-text
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：所给字符串不是有效正整数申请编号，不能自行修正。

### FIN-T2-A-clarify-bad-id-text-02

想查申请，记下来的号是八万多一点，你能直接开吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-bad-id-text
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：所给字符串不是有效正整数申请编号，不能自行修正。

### FIN-T2-A-clarify-bad-id-text-03

申请号中间两位看不清，像86??3，先查那笔。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-bad-id-text
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：所给字符串不是有效正整数申请编号，不能自行修正。

### FIN-T2-A-clarify-bad-id-text-04

我只记得单号末尾像27，要开那张明细。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-bad-id-text
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：所给字符串不是有效正整数申请编号，不能自行修正。

### FIN-T2-A-clarify-id-correction-01

刚才号码说错了，不是那笔，查另一张详情。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-id-correction
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "刚才我说想查本人申请86123。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：历史对象被用户明确否定且新对象未给出，不能沿用旧编号。

### FIN-T2-A-clarify-id-correction-02

先不要按前面的编号查，我其实想看另一个。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-id-correction
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "刚才我说想查本人申请86123。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：历史对象被用户明确否定且新对象未给出，不能沿用旧编号。

### FIN-T2-A-clarify-id-correction-03

上面那单不对，换成我真正要看的申请。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-id-correction
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "刚才我说想查本人申请86123。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：历史对象被用户明确否定且新对象未给出，不能沿用旧编号。

### FIN-T2-A-clarify-id-correction-04

把刚才的选择取消，我要查别的那笔，号码还没找出来。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-id-correction
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "刚才我说想查本人申请86123。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：历史对象被用户明确否定且新对象未给出，不能沿用旧编号。

### FIN-T2-A-clarify-guest-credit-01

我还没登账号，能先把属于我的信用分查来吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-credit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：未认证状态不能查询个人信用记录，先完成登录确认。

### FIN-T2-A-clarify-guest-credit-02

页面现在是游客，我想读取本人评分记录。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-credit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：未认证状态不能查询个人信用记录，先完成登录确认。

### FIN-T2-A-clarify-guest-credit-03

不记得自己有没有登录，先查我账户的信用分。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-credit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：未认证状态不能查询个人信用记录，先完成登录确认。

### FIN-T2-A-clarify-guest-credit-04

请调出我个人信用档位，当前还没有完成登录。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-credit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：未认证状态不能查询个人信用记录，先完成登录确认。

### FIN-T2-A-clarify-guest-list-01

游客状态能直接展开我的申请记录吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：个人申请列表需要认证，不能按用户自称绑定身份。

### FIN-T2-A-clarify-guest-list-02

我现在没有登录，想看本人提交过的那些单子。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：个人申请列表需要认证，不能按用户自称绑定身份。

### FIN-T2-A-clarify-guest-list-03

请查我的申请概览，账号还没登进去。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：个人申请列表需要认证，不能按用户自称绑定身份。

### FIN-T2-A-clarify-guest-list-04

先取本人的申请列表吧，登录这步我还没做。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：个人申请列表需要认证，不能按用户自称绑定身份。

### FIN-T2-A-clarify-guest-detail-01

我未登录，想看本人86124这笔明细。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-detail
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false, "application_id": 86124}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：申请编号已明确但认证缺失；不再重复索要编号。

### FIN-T2-A-clarify-guest-detail-02

号码是86124，登录尚未完成，先帮我查详情。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-detail
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false, "application_id": 86124}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：申请编号已明确但认证缺失；不再重复索要编号。

### FIN-T2-A-clarify-guest-detail-03

还在游客页面，我的申请86124能打开吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-detail
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false, "application_id": 86124}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：申请编号已明确但认证缺失；不再重复索要编号。

### FIN-T2-A-clarify-guest-detail-04

读取我的86124申请信息吧，我还没有认证账号。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-guest-detail
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false, "application_id": 86124}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：申请编号已明确但认证缺失；不再重复索要编号。

### FIN-T2-A-clarify-code-absent-01

页面那个审批数字到底什么意思？我还没告诉你数字。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-absent
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：询问某个状态值含义却没有给出值，需澄清代码。

### FIN-T2-A-clarify-code-absent-02

解释一下当前状态码，具体值我漏写了。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-absent
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：询问某个状态值含义却没有给出值，需澄清代码。

### FIN-T2-A-clarify-code-absent-03

想问一个审批状态的含义，数字该发给你吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-absent
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：询问某个状态值含义却没有给出值，需澄清代码。

### FIN-T2-A-clarify-code-absent-04

状态栏是个数字，帮我先确认需要提供什么才能解释。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-absent
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：询问某个状态值含义却没有给出值，需澄清代码。

### FIN-T2-A-clarify-code-unreadable-01

字有点糊，审批码像0也像2，我没看准。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unreadable
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：用户自己无法确认所见值，不能选其中一个状态解释。

### FIN-T2-A-clarify-code-unreadable-02

状态那个数字分不清是1还是2，怎么确认？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unreadable
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：用户自己无法确认所见值，不能选其中一个状态解释。

### FIN-T2-A-clarify-code-unreadable-03

我没读清数字，请先别把它当作确定的状态。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unreadable
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：用户自己无法确认所见值，不能选其中一个状态解释。

### FIN-T2-A-clarify-code-unreadable-04

页面太小看不清状态码，可能是0，也可能不是。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unreadable
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：用户自己无法确认所见值，不能选其中一个状态解释。

### FIN-T2-A-clarify-code-unsupported-01

审批状态显示8，这个码是什么意思？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unsupported
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：给出的代码超出当前解释工具的0/1/2范围，需核对字段和值。

### FIN-T2-A-clarify-code-unsupported-02

那个状态值写的是-1，能按审批状态解释吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unsupported
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：给出的代码超出当前解释工具的0/1/2范围，需核对字段和值。

### FIN-T2-A-clarify-code-unsupported-03

我看到状态是99，可能找错了栏，帮我确认。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unsupported
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：给出的代码超出当前解释工具的0/1/2范围，需核对字段和值。

### FIN-T2-A-clarify-code-unsupported-04

状态栏抄成了5，请说明这个数字代表什么。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-unsupported
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：给出的代码超出当前解释工具的0/1/2范围，需核对字段和值。

### FIN-T2-A-clarify-code-field-01

页面上是1。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-field
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：孤立数字没有请求与字段语义，不能假定它是状态或申请ID。

### FIN-T2-A-clarify-code-field-02

我看到一个2，接下来呢？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-field
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：孤立数字没有请求与字段语义，不能假定它是状态或申请ID。

### FIN-T2-A-clarify-code-field-03

那个框里就写着0。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-field
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：孤立数字没有请求与字段语义，不能假定它是状态或申请ID。

### FIN-T2-A-clarify-code-field-04

给你个数字1，你看看。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-code-field
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：孤立数字没有请求与字段语义，不能假定它是状态或申请ID。

### FIN-T2-A-clarify-ui-button-01

有个按钮按不了，但我忘了说是哪个。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-button
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：只说按钮不可用且没有按钮名称或提示，先获取可观察界面文字。

### FIN-T2-A-clarify-ui-button-02

界面下面那块灰着，能帮我看原因吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-button
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：只说按钮不可用且没有按钮名称或提示，先获取可观察界面文字。

### FIN-T2-A-clarify-ui-button-03

点那里没反应，我还没把页面名称发来。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-button
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：只说按钮不可用且没有按钮名称或提示，先获取可观察界面文字。

### FIN-T2-A-clarify-ui-button-04

那个操作是灰色的，要怎样才能点？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-button
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：只说按钮不可用且没有按钮名称或提示，先获取可观察界面文字。

### FIN-T2-A-clarify-ui-error-01

申请页面报了个错，我没记住文字。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-error
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：有故障描述但缺少错误提示内容，不能猜规则或账户结论。

### FIN-T2-A-clarify-ui-error-02

操作失败提示弹了一下，内容还没发给你。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-error
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：有故障描述但缺少错误提示内容，不能猜规则或账户结论。

### FIN-T2-A-clarify-ui-error-03

刚才提示不行，先帮我确认该提供哪些错误信息。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-error
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：有故障描述但缺少错误提示内容，不能猜规则或账户结论。

### FIN-T2-A-clarify-ui-error-04

出现一条红字，能判断什么问题吗？我还没贴原文。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-ui-error
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：有故障描述但缺少错误提示内容，不能猜规则或账户结论。

### FIN-T2-A-clarify-absent-image-01

按我那张截图看看怎么回事，图片好像没有发上来。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-absent-image
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：用户引用截图但输入没有图像或文字，先索取可用提示内容。

### FIN-T2-A-clarify-absent-image-02

就看图里的提示吧，我还没传成功。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-absent-image
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：用户引用截图但输入没有图像或文字，先索取可用提示内容。

### FIN-T2-A-clarify-absent-image-03

我想问截图那块按钮，先等等，附件现在是空的。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-absent-image
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：用户引用截图但输入没有图像或文字，先索取可用提示内容。

### FIN-T2-A-clarify-absent-image-04

图片里的问题能分析吗？这条消息还没附图。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-absent-image
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：用户引用截图但输入没有图像或文字，先索取可用提示内容。

### FIN-T2-A-clarify-pronoun-topic-01

就那个，帮我弄一下。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-pronoun-topic
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：没有相关历史，指代对象和处理目标均不明确。

### FIN-T2-A-clarify-pronoun-topic-02

还是之前说的事，你处理吧。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-pronoun-topic
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：没有相关历史，指代对象和处理目标均不明确。

### FIN-T2-A-clarify-pronoun-topic-03

它现在怎么样了？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-pronoun-topic
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：没有相关历史，指代对象和处理目标均不明确。

### FIN-T2-A-clarify-pronoun-topic-04

看看这个行不行，我先没说是什么。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-pronoun-topic
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：没有相关历史，指代对象和处理目标均不明确。

### FIN-T2-A-clarify-amount-category-01

想查一个额度，先不说哪种。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-amount-category
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：金额可能指产品上限、本人评分建议或申请金额，先确认所问类型。

### FIN-T2-A-clarify-amount-category-02

我问的就是金额，到底是多少？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-amount-category
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：金额可能指产品上限、本人评分建议或申请金额，先确认所问类型。

### FIN-T2-A-clarify-amount-category-03

能看看那笔钱的数字吗，我还没说明是哪项。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-amount-category
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：金额可能指产品上限、本人评分建议或申请金额，先确认所问类型。

### FIN-T2-A-clarify-amount-category-04

额度这块帮我查一下，具体查谁的还没定。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-amount-category
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：金额可能指产品上限、本人评分建议或申请金额，先确认所问类型。

### FIN-T2-A-clarify-known-prompt-missing-01

能解释我刚说的那句话吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-known-prompt-missing
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "申请页面有一段提示，我还没有把文字内容发过来。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：历史只说存在提示而未提供内容，不能按想象解释界面。

### FIN-T2-A-clarify-known-prompt-missing-02

它到底要求我做什么？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-known-prompt-missing
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "申请页面有一段提示，我还没有把文字内容发过来。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：历史只说存在提示而未提供内容，不能按想象解释界面。

### FIN-T2-A-clarify-known-prompt-missing-03

提示的含义帮我讲简单点。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-known-prompt-missing
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "申请页面有一段提示，我还没有把文字内容发过来。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：历史只说存在提示而未提供内容，不能按想象解释界面。

### FIN-T2-A-clarify-known-prompt-missing-04

我没理解那段文字，请你解释。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-known-prompt-missing
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "申请页面有一段提示，我还没有把文字内容发过来。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：历史只说存在提示而未提供内容，不能按想象解释界面。

### FIN-T2-A-clarify-choice-without-options-01

就选第二个，看看它的明细。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-choice-without-options
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：“第二个”没有可见候选列表，不能推断具体产品或申请。

### FIN-T2-A-clarify-choice-without-options-02

我说的是列表中间那个，你打开。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-choice-without-options
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：“第二个”没有可见候选列表，不能推断具体产品或申请。

### FIN-T2-A-clarify-choice-without-options-03

第三项怎么样？我没发列表。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-choice-without-options
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：“第二个”没有可见候选列表，不能推断具体产品或申请。

### FIN-T2-A-clarify-choice-without-options-04

还是第一条吧，帮我查查。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-choice-without-options
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：“第二个”没有可见候选列表，不能推断具体产品或申请。

### FIN-T2-A-clarify-switch-query-01

产品先不看了，我要查另外一项。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-switch-query
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "前面我们在说平台的上架贷款产品目录。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户终止旧话题改查未明内容，不应沿用旧工具。

### FIN-T2-A-clarify-switch-query-02

不是这个问题，换一个事情帮我查。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-switch-query
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "前面我们在说平台的上架贷款产品目录。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户终止旧话题改查未明内容，不应沿用旧工具。

### FIN-T2-A-clarify-switch-query-03

前面的目录不用了，我有别的要核对。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-switch-query
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "前面我们在说平台的上架贷款产品目录。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户终止旧话题改查未明内容，不应沿用旧工具。

### FIN-T2-A-clarify-switch-query-04

先把产品话题放一边，接下来我要问另一个记录。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:clarify-switch-query
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "前面我们在说平台的上架贷款产品目录。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户终止旧话题改查未明内容，不应沿用旧工具。

### FIN-T2-B-unspecified-change-01

我想把那个改一下，具体找你能弄吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unspecified-change
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户想处理某项信息但对象和目的均缺失，先补充事项，不推定为资料纠错或越权篡改。

### FIN-T2-B-unspecified-change-02

这边有一项不太对，帮我处理下可以吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unspecified-change
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户想处理某项信息但对象和目的均缺失，先补充事项，不推定为资料纠错或越权篡改。

### FIN-T2-B-unspecified-change-03

刚才提到的东西想调整，下一步怎么说？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unspecified-change
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户想处理某项信息但对象和目的均缺失，先补充事项，不推定为资料纠错或越权篡改。

### FIN-T2-B-unspecified-change-04

有个地方需要换掉，你先告诉我从哪开始。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unspecified-change
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户想处理某项信息但对象和目的均缺失，先补充事项，不推定为资料纠错或越权篡改。

### FIN-T2-B-thanks-new-object-01

谢谢，另外那一项还能帮我看看吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:thanks-new-object
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "本金和利息分别指什么？"}, {"role": "assistant", "content": "本金是借入资金本身，利息是按约定计收的资金使用费用。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史中旧问题已解答，但谢谢后提出新的含糊查询，缺少具体事项，不能直接结束。

### FIN-T2-B-thanks-new-object-02

多谢说明，我还想问另一件，可不可以处理？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:thanks-new-object
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "本金和利息分别指什么？"}, {"role": "assistant", "content": "本金是借入资金本身，利息是按约定计收的资金使用费用。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史中旧问题已解答，但谢谢后提出新的含糊查询，缺少具体事项，不能直接结束。

### FIN-T2-B-thanks-new-object-03

这个明白了，剩下那个怎么弄？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:thanks-new-object
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "本金和利息分别指什么？"}, {"role": "assistant", "content": "本金是借入资金本身，利息是按约定计收的资金使用费用。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史中旧问题已解答，但谢谢后提出新的含糊查询，缺少具体事项，不能直接结束。

### FIN-T2-B-thanks-new-object-04

谢谢，我还有个相关问题，就是之前那个地方。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:thanks-new-object
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "本金和利息分别指什么？"}, {"role": "assistant", "content": "本金是借入资金本身，利息是按约定计收的资金使用费用。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史中旧问题已解答，但谢谢后提出新的含糊查询，缺少具体事项，不能直接结束。

### FIN-T2-B-ambiguous-stop-01

那个先停一下，我不是说所有的。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:ambiguous-stop
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解申请材料准备，也想看一下产品说明。"}, {"role": "assistant", "content": "您想先了解材料准备，还是产品说明？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：多个正在讨论的普通事项之间的停止对象不明，不能擅自将其解释成关闭会话或撤回申请。

### FIN-T2-B-ambiguous-stop-02

先别继续刚刚那项，另一项还要的。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:ambiguous-stop
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解申请材料准备，也想看一下产品说明。"}, {"role": "assistant", "content": "您想先了解材料准备，还是产品说明？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：多个正在讨论的普通事项之间的停止对象不明，不能擅自将其解释成关闭会话或撤回申请。

### FIN-T2-B-ambiguous-stop-03

撤掉其中一个吧，剩下的先保留。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:ambiguous-stop
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解申请材料准备，也想看一下产品说明。"}, {"role": "assistant", "content": "您想先了解材料准备，还是产品说明？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：多个正在讨论的普通事项之间的停止对象不明，不能擅自将其解释成关闭会话或撤回申请。

### FIN-T2-B-ambiguous-stop-04

我想结束那个步骤，但不是全部不做了。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:ambiguous-stop
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解申请材料准备，也想看一下产品说明。"}, {"role": "assistant", "content": "您想先了解材料准备，还是产品说明？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：多个正在讨论的普通事项之间的停止对象不明，不能擅自将其解释成关闭会话或撤回申请。

### FIN-T2-B-unreadable-message-01

页面弹了一句没看清的提示，你能解释是什么吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unreadable-message
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少页面原文且没有正在发生的资金风险，先收集提示文字而不是编造原因或直接升级。

### FIN-T2-B-unreadable-message-02

屏幕上有几个字一闪而过，我不知道写了什么，下一步怎么办？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unreadable-message
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少页面原文且没有正在发生的资金风险，先收集提示文字而不是编造原因或直接升级。

### FIN-T2-B-unreadable-message-03

那个框的内容我还没记下来，你知道它想说什么吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unreadable-message
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少页面原文且没有正在发生的资金风险，先收集提示文字而不是编造原因或直接升级。

### FIN-T2-B-unreadable-message-04

我看不清提示的具体字，能先帮我弄懂那个提示吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:unreadable-message
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：缺少页面原文且没有正在发生的资金风险，先收集提示文字而不是编造原因或直接升级。

### FIN-T2-B-want-right-one-01

就查最需要的那个吧，我也说不清是哪个。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:want-right-one
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解账户里的情况。"}, {"role": "assistant", "content": "您是想查看已经提交的借款申请，还是查看当前记录的信用评分？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史同时提到不同业务目标，本轮仍未选定，先明确所需事项，不选任意工具。

### FIN-T2-B-want-right-one-02

你刚才说的有一项是我想看，但我没分清名称。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-b:want-right-one
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想了解账户里的情况。"}, {"role": "assistant", "content": "您是想查看已经提交的借款申请，还是查看当前记录的信用评分？"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：历史同时提到不同业务目标，本轮仍未选定，先明确所需事项，不选任意工具。

### FIN-T2-S-meaning-01

这行字是什么意思？

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:meaning
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["error_context"]}
- 依据：没有提供所指文字，需获取原文。

### FIN-T2-S-detail-01

那就查一下这笔吧。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:detail
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["application_id"]}
- 依据：没有选定对象或历史编号。

### FIN-T2-S-closing-02

那就把这个关掉吧。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:closing
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：不知关闭的是页面、会话或业务对象，不执行结束。

### FIN-T2-S-after-thanks-01

谢谢，不过我还有这个问题。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:after-thanks
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "前面那个问题解决了，另一个问题还没说出来。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["request_details"]}
- 依据：用户明确继续但尚未给出新问题，不结束会话。

### FIN-T2-S-authenticate-01

把我现在留在系统里的信用分给我看一下。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:authenticate
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["authentication"]}
- 依据：查询本人信息前需要认证。

## retrieve

## tool

## answer

## human

## redirect

## refuse

## close
