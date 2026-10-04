# 八动作首批逐条复核

助手起草/重新标注；新版本未人工复核。所有条目仅为训练候选，不是测试金标。模型只读input，不读annotation/provenance/review。

## clarify

## retrieve

### FIN-P1-F15-A-01-base

提前还款的入口在哪

- 来源：business_policy_migration / F15-A-01-base；同源组：business:F15
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-F15-A-02-base

我自己想提前还款，要怎么点

- 来源：business_policy_migration / F15-A-02-base；同源组：business:F15
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-F16-A-01-base

收入证明要从哪里补交

- 来源：business_policy_migration / F16-A-01-base；同源组：business:F16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-F16-A-02-base

补充材料页面在哪个入口

- 来源：business_policy_migration / F16-A-02-base；同源组：business:F16
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-F29-B-01-base

如果我自己想查看产品列表，应该去哪

- 来源：business_policy_migration / F29-B-01-base；同源组：business:F29
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-F29-B-02-base

告诉我浏览贷款产品页面的操作路径

- 来源：business_policy_migration / F29-B-02-base；同源组：business:F29
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台特定操作流程未在输入中给出；新政策要求从可用的正式文档集合检索。

### FIN-P1-kb-file-format-1

申请附件可以交哪些文件格式？请依据平台公布的上传说明答复。

- 来源：assistant_authored / 新起草；同源组：new:kb-file-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-file-format-2

平台对证明材料的文件类型有限制吗，帮我查一下正式说明。

- 来源：assistant_authored / 新起草；同源组：new:kb-file-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-file-size-1

我准备上传收入证明，想先查平台规定的单个附件大小限制。

- 来源：assistant_authored / 新起草；同源组：new:kb-file-size
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-file-size-2

查一下材料提交指南，上传文件最大能有多大？

- 来源：assistant_authored / 新起草；同源组：new:kb-file-size
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-supplement-window-1

申请要求补充证明后，平台给的提交期限按哪份规定执行？

- 来源：assistant_authored / 新起草；同源组：new:kb-supplement-window
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-supplement-window-2

想查本平台补交材料的时限规则，先给我有效的说明依据。

- 来源：assistant_authored / 新起草；同源组：new:kb-supplement-window
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-privacy-policy-1

本平台的借款资料保存多久，请查当前隐私政策里的说明。

- 来源：assistant_authored / 新起草；同源组：new:kb-privacy-policy
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-privacy-policy-2

贷款申请附件如何保存和使用，帮我找平台现行隐私条款。

- 来源：assistant_authored / 新起草；同源组：new:kb-privacy-policy
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-complaint-channel-1

目前没有争议，想预先查平台公布的投诉受理渠道。

- 来源：assistant_authored / 新起草；同源组：new:kb-complaint-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-complaint-channel-2

仅了解流程：平台正式公布的投诉途径在哪里？

- 来源：assistant_authored / 新起草；同源组：new:kb-complaint-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-prepayment-rule-1

先不处理个人贷款，帮我查平台现行的提前结清申请规则。

- 来源：assistant_authored / 新起草；同源组：new:kb-prepayment-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-prepayment-rule-2

我需要本平台提前还款的正式流程说明，请从有效文档查找。

- 来源：assistant_authored / 新起草；同源组：new:kb-prepayment-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-product-disclosure-1

平台对贷款产品费用的公示方式有什么正式说明？

- 来源：assistant_authored / 新起草；同源组：new:kb-product-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-kb-product-disclosure-2

请检索平台关于贷款费用披露的现行说明，我只问公开规则。

- 来源：assistant_authored / 新起草；同源组：new:kb-product-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问平台特定规则，未提供充分文档事实；模拟配置已开放相应知识集合。

### FIN-P1-massive-train-87-loan-adaptation

我准备提交一份借款申请，请查平台公布的资料准备清单。

- 来源：public_loan_adaptation / massive-train-87；同源组：massive:massive-train-87
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：将准备事项改写为平台申请材料规则查询，不假设具体规则内容。

### FIN-P1-massive-train-6453-loan-adaptation

请找平台现行文档说明，贷款产品对申请年龄有什么要求。

- 来源：public_loan_adaptation / massive-train-6453；同源组：massive:massive-train-6453
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：重写为平台规则查询；不凭通用常识编造年龄门槛。

### FIN-P1-massive-train-9911-loan-adaptation

按平台规定，补交收入证明的处理时限如何说明？

- 来源：public_loan_adaptation / massive-train-9911；同源组：massive:massive-train-9911
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：保留询问时限的结构，重写为需查正式文档的业务问题。

### FIN-P1-contrast-kb-availability-1

这里上传申请材料允许哪些文件后缀？

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:kb-availability
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：规则依赖平台文档，模拟检索能力可用。

### FIN-P1-contrast-public-doc-login-1

平台正式的附件上传流程能查给我吗？

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:public-doc-login
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": false}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：模拟知识集合为公开业务文档，不要求登录。

### FIN-P1-contrast-public-doc-login-2

平台正式的附件上传流程能查给我吗？

- 来源：assistant_authored_state_pair / 新起草；同源组：new-contrast:public-doc-login
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：已登录也应检索未知平台流程，不能改为查询个人记录。

### FIN-T2-A-doc-material-list-01

没开始申请，想先看你们正式要求准备哪些资料。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-material-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请材料清单依赖正式业务文档，用户并未请求个人提交记录。

### FIN-T2-A-doc-material-list-02

你们这边借款材料清单在哪里，按官方说明查给我。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-material-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请材料清单依赖正式业务文档，用户并未请求个人提交记录。

### FIN-T2-A-doc-material-list-03

我想提前备齐文件，检索平台规定的申请资料。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-material-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请材料清单依赖正式业务文档，用户并未请求个人提交记录。

### FIN-T2-A-doc-material-list-04

不是查我的材料，问的是平台要求提交的标准清单。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-material-list
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请材料清单依赖正式业务文档，用户并未请求个人提交记录。

### FIN-T2-A-doc-accepted-format-01

申请附件能用哪些格式？要你们自己的上传说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accepted-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：查询平台附件格式约束，不能从通用文件常识推出平台要求。

### FIN-T2-A-doc-accepted-format-02

我手里的扫描件后缀不一样，查平台允许的文件类型。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accepted-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：查询平台附件格式约束，不能从通用文件常识推出平台要求。

### FIN-T2-A-doc-accepted-format-03

别凭常见做法回答，看看官方文档对附件格式怎么写。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accepted-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：查询平台附件格式约束，不能从通用文件常识推出平台要求。

### FIN-T2-A-doc-accepted-format-04

要准备电子材料了，你们接收什么格式的文件？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accepted-format
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：查询平台附件格式约束，不能从通用文件常识推出平台要求。

### FIN-T2-A-doc-size-limit-01

申请文件单个允许多大，查你们的上传限制。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-size-limit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：材料体积上限属于平台具体上传约束，需检索。

### FIN-T2-A-doc-size-limit-02

我还没上传，先确认平台规定的附件大小上限。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-size-limit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：材料体积上限属于平台具体上传约束，需检索。

### FIN-T2-A-doc-size-limit-03

打包材料前想知道，你们有没有公布单文件体积要求？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-size-limit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：材料体积上限属于平台具体上传约束，需检索。

### FIN-T2-A-doc-size-limit-04

文件太大可能传不了，帮我找平台关于大小的说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-size-limit
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：材料体积上限属于平台具体上传约束，需检索。

### FIN-T2-A-doc-upload-steps-01

现在查正式步骤，我该从哪个入口开始传？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-upload-steps
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想提前了解如何上传借款申请材料，还没有开始提交。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：在已有话题下请求平台公开上传流程，不是在汇报正在发生的故障。

### FIN-T2-A-doc-upload-steps-02

请找一份平台上传流程，不用根据我的界面猜。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-upload-steps
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想提前了解如何上传借款申请材料，还没有开始提交。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：在已有话题下请求平台公开上传流程，不是在汇报正在发生的故障。

### FIN-T2-A-doc-upload-steps-03

我只是提前熟悉操作，检索官方的提交附件指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-upload-steps
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想提前了解如何上传借款申请材料，还没有开始提交。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：在已有话题下请求平台公开上传流程，不是在汇报正在发生的故障。

### FIN-T2-A-doc-upload-steps-04

按公开文档说明材料上传的顺序就好。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-upload-steps
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我想提前了解如何上传借款申请材料，还没有开始提交。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：在已有话题下请求平台公开上传流程，不是在汇报正在发生的故障。

### FIN-T2-A-doc-correction-process-01

如果发现申请材料填错，平台公布的更正流程是什么？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-correction-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：咨询平台修改申请材料的标准流程，尚无个人记录操作请求。

### FIN-T2-A-doc-correction-process-02

想提前了解材料更正需要走什么步骤，请查官方说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-correction-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：咨询平台修改申请材料的标准流程，尚无个人记录操作请求。

### FIN-T2-A-doc-correction-process-03

不是让你直接改记录，我问你们如何申请材料更正。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-correction-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：咨询平台修改申请材料的标准流程，尚无个人记录操作请求。

### FIN-T2-A-doc-correction-process-04

查一下你们对提交后纠错的正式处理指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-correction-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：咨询平台修改申请材料的标准流程，尚无个人记录操作请求。

### FIN-T2-A-doc-withdraw-process-01

先别撤销任何东西，查平台写的撤回申请办法。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-withdraw-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解撤回申请的公开规则，不执行撤销动作也不结束会话。

### FIN-T2-A-doc-withdraw-process-02

你们的申请撤回说明在哪，能检索出来吗？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-withdraw-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解撤回申请的公开规则，不执行撤销动作也不结束会话。

### FIN-T2-A-doc-withdraw-process-03

我只问标准流程：提交之后怎样按规定申请撤回？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-withdraw-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解撤回申请的公开规则，不执行撤销动作也不结束会话。

### FIN-T2-A-doc-withdraw-process-04

咨询还没结束，想看看官方的申请撤回指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-withdraw-process
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解撤回申请的公开规则，不执行撤销动作也不结束会话。

### FIN-T2-A-doc-prepayment-01

以后想提前结清，你们正式公布的办理流程是什么？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-prepayment
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解提前还款公开流程，不涉及当前扣款争议或实时账单查询。

### FIN-T2-A-doc-prepayment-02

还没有操作提前还款，先查平台对应的说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-prepayment
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解提前还款公开流程，不涉及当前扣款争议或实时账单查询。

### FIN-T2-A-doc-prepayment-03

帮我找一下你们提前归还借款的业务指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-prepayment
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解提前还款公开流程，不涉及当前扣款争议或实时账单查询。

### FIN-T2-A-doc-prepayment-04

不是问我的账单，只想看官方提前还款步骤。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-prepayment
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：了解提前还款公开流程，不涉及当前扣款争议或实时账单查询。

### FIN-T2-A-doc-fee-disclosure-01

你们的服务费用说明在哪份文档里，帮我检索。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-fee-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：要求查收费披露文档，现有产品工具不提供实时费用。

### FIN-T2-A-doc-fee-disclosure-02

借款前想读收费披露，不要给我估算一个数字。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-fee-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：要求查收费披露文档，现有产品工具不提供实时费用。

### FIN-T2-A-doc-fee-disclosure-03

请按官方资料找费用项目的说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-fee-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：要求查收费披露文档，现有产品工具不提供实时费用。

### FIN-T2-A-doc-fee-disclosure-04

平台公布了哪些收费说明？我想先看原文依据。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-fee-disclosure
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：要求查收费披露文档，现有产品工具不提供实时费用。

### FIN-T2-A-doc-age-rule-01

你们产品申请年龄范围有公开规定吗，找出来看看。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-age-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请年龄范围需正式准入文档，不能用一般年龄概念回答。

### FIN-T2-A-doc-age-rule-02

先不用判我能不能过，查询平台公布的年龄条件。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-age-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请年龄范围需正式准入文档，不能用一般年龄概念回答。

### FIN-T2-A-doc-age-rule-03

想了解本平台的年龄准入要求，依据文档回答。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-age-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请年龄范围需正式准入文档，不能用一般年龄概念回答。

### FIN-T2-A-doc-age-rule-04

查正式申请条件里关于年龄那一项。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-age-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台申请年龄范围需正式准入文档，不能用一般年龄概念回答。

### FIN-T2-A-doc-purpose-rule-01

哪些借款用途在你们这里允许，查官方规则。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-purpose-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台允许的借款用途是具体业务规则，不能以一般用途解释替代。

### FIN-T2-A-doc-purpose-rule-02

申请前想看本平台对资金用途的书面要求。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-purpose-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台允许的借款用途是具体业务规则，不能以一般用途解释替代。

### FIN-T2-A-doc-purpose-rule-03

不问用途这个词的意思，要你们允许和限制的范围。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-purpose-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台允许的借款用途是具体业务规则，不能以一般用途解释替代。

### FIN-T2-A-doc-purpose-rule-04

请检索平台公布的借款用途规范。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-purpose-rule
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台允许的借款用途是具体业务规则，不能以一般用途解释替代。

### FIN-T2-A-doc-review-time-01

平台有没有公布审核处理时效？以正式说明为准。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-review-time
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问公开处理时效，不是要求预测指定个人申请通过时间。

### FIN-T2-A-doc-review-time-02

不查我那笔，想知道你们文档里写的通常处理时间。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-review-time
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问公开处理时效，不是要求预测指定个人申请通过时间。

### FIN-T2-A-doc-review-time-03

申请前看下官方时效说明，别替我保证什么时候通过。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-review-time
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问公开处理时效，不是要求预测指定个人申请通过时间。

### FIN-T2-A-doc-review-time-04

请找你们关于审核等待时间的公开文档。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-review-time
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：询问公开处理时效，不是要求预测指定个人申请通过时间。

### FIN-T2-A-doc-contact-channel-01

我现在不需要转接，只想查官方公布的客服联系入口。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-contact-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解公开客服联系渠道，不是请求立即转人工。

### FIN-T2-A-doc-contact-channel-02

先收藏联系方式，找一下平台正式的客服渠道说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-contact-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解公开客服联系渠道，不是请求立即转人工。

### FIN-T2-A-doc-contact-channel-03

请检索你们的联系指引，不用发起人工会话。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-contact-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解公开客服联系渠道，不是请求立即转人工。

### FIN-T2-A-doc-contact-channel-04

想知道以后有事从哪联系平台，按公开文档查。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-contact-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解公开客服联系渠道，不是请求立即转人工。

### FIN-T2-A-doc-appeal-channel-01

如果以后对结果有疑问，平台申诉流程怎么写？现在没有争议。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-appeal-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解申诉公开流程，与正在发生的争议升级区分。

### FIN-T2-A-doc-appeal-channel-02

想了解官方申诉指引，暂时不发起投诉。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-appeal-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解申诉公开流程，与正在发生的争议升级区分。

### FIN-T2-A-doc-appeal-channel-03

先查平台公布的意见反馈和申诉步骤。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-appeal-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解申诉公开流程，与正在发生的争议升级区分。

### FIN-T2-A-doc-appeal-channel-04

我在熟悉功能，看看正式的申诉入口说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-appeal-channel
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：预先了解申诉公开流程，与正在发生的争议升级区分。

### FIN-T2-A-doc-account-close-01

想读你们的账号注销指引，不是结束这段对话。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-account-close
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：账号注销涉及平台个人信息处理和权利行使流程，不能误标结束当前咨询。

### FIN-T2-A-doc-account-close-02

请检索隐私说明里怎么申请注销账号。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-account-close
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：账号注销涉及平台个人信息处理和权利行使流程，不能误标结束当前咨询。

### FIN-T2-A-doc-account-close-03

我先了解规则，平台公开的注销账户流程是什么？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-account-close
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：账号注销涉及平台个人信息处理和权利行使流程，不能误标结束当前咨询。

### FIN-T2-A-doc-account-close-04

暂时不操作注销，查一下官方相关条款。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-account-close
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：账号注销涉及平台个人信息处理和权利行使流程，不能误标结束当前咨询。

### FIN-T2-A-doc-privacy-retention-01

申请资料会保存多久？请查你们的隐私政策。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-privacy-retention
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：平台个人信息保存期限需查隐私文档，不虚构期限。

### FIN-T2-A-doc-privacy-retention-02

我想知道平台怎么规定个人资料留存时间，找原文。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-privacy-retention
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：平台个人信息保存期限需查隐私文档，不虚构期限。

### FIN-T2-A-doc-privacy-retention-03

提交的材料保存年限有没有说明，以平台文档为准。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-privacy-retention
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：平台个人信息保存期限需查隐私文档，不虚构期限。

### FIN-T2-A-doc-privacy-retention-04

请检索你们关于申请数据保存期限的条款。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-privacy-retention
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：平台个人信息保存期限需查隐私文档，不虚构期限。

### FIN-T2-A-doc-data-collection-01

你们申请过程中会收集哪些个人信息？查正式清单。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-collection
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台收集范围，须以具体隐私政策为依据。

### FIN-T2-A-doc-data-collection-02

只想了解平台的数据采集范围，请找隐私说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-collection
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台收集范围，须以具体隐私政策为依据。

### FIN-T2-A-doc-data-collection-03

开通服务之前，看看官方列出的信息收集项目。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-collection
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台收集范围，须以具体隐私政策为依据。

### FIN-T2-A-doc-data-collection-04

不要泛泛讲隐私保护，我问的是你们实际公布的收集范围。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-collection
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：询问平台收集范围，须以具体隐私政策为依据。

### FIN-T2-A-doc-data-sharing-01

隐私政策对向第三方共享资料怎么写，帮我定位。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-sharing
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：公开第三方共享声明属于平台特定隐私政策。

### FIN-T2-A-doc-data-sharing-02

平台公开说会与哪些类别机构共享信息？按文档查。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-sharing
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：公开第三方共享声明属于平台特定隐私政策。

### FIN-T2-A-doc-data-sharing-03

我想读你们的第三方信息共享说明，不查某个用户。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-sharing
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：公开第三方共享声明属于平台特定隐私政策。

### FIN-T2-A-doc-data-sharing-04

请找到本平台数据共享规则的原文依据。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-data-sharing
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：公开第三方共享声明属于平台特定隐私政策。

### FIN-T2-A-doc-permission-withdraw-01

如果不想继续授权某项信息，官方撤回授权步骤是什么？

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-permission-withdraw
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：撤回授权流程需查平台政策，不等于请求绕过必要授权。

### FIN-T2-A-doc-permission-withdraw-02

想按正常渠道管理授权，查平台隐私指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-permission-withdraw
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：撤回授权流程需查平台政策，不等于请求绕过必要授权。

### FIN-T2-A-doc-permission-withdraw-03

请检索你们如何处理用户撤回同意的说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-permission-withdraw
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：撤回授权流程需查平台政策，不等于请求绕过必要授权。

### FIN-T2-A-doc-permission-withdraw-04

不是要绕过认证，我只想知道平台公布的授权管理办法。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-permission-withdraw
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：撤回授权流程需查平台政策，不等于请求绕过必要授权。

### FIN-T2-A-doc-policy-version-01

现在生效的是哪一版隐私政策？查一下公布的信息。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-policy-version
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：用户询问当前有效隐私政策版本，需检索正式版本资料。

### FIN-T2-A-doc-policy-version-02

我保存的是旧条款，找你们目前有效的隐私说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-policy-version
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：用户询问当前有效隐私政策版本，需检索正式版本资料。

### FIN-T2-A-doc-policy-version-03

请核对当前公开隐私政策的版本和更新信息。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-policy-version
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：用户询问当前有效隐私政策版本，需检索正式版本资料。

### FIN-T2-A-doc-policy-version-04

要读最新有效的隐私文本，帮我从正式文档里找。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-policy-version
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "privacy_policy", "missing_slots": []}
- 依据：用户询问当前有效隐私政策版本，需检索正式版本资料。

### FIN-T2-A-doc-accessibility-help-01

资料填写按钮太多，想查你们正式的新手操作指引。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accessibility-help
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台具体界面操作指引需查正式文档，不按想象描述按钮位置。

### FIN-T2-A-doc-accessibility-help-02

不是报故障，我想看平台有没有申请页面的使用说明。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accessibility-help
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台具体界面操作指引需查正式文档，不按想象描述按钮位置。

### FIN-T2-A-doc-accessibility-help-03

找一下官方帮助文档，讲申请页面各入口怎么用的。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accessibility-help
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台具体界面操作指引需查正式文档，不按想象描述按钮位置。

### FIN-T2-A-doc-accessibility-help-04

先给我检索你们公开的借款申请操作手册。

- 来源：assistant_authored_expansion / 新起草；同源组：fin-t2-a:doc-accessibility-help
- 复核状态：assistant_draft
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台具体界面操作指引需查正式文档，不按想象描述按钮位置。

### FIN-T2-S-latest-02

我想看最新的。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:latest
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我问的是平台附件上传的正式规范，手里那版已经过期。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：明确要求现行平台文档，须检索有效版本。

### FIN-T2-S-rules-01

帮我找一下规则。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:rules
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我问你们借款材料的补交期限，以平台说明为准。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：平台材料规则属于可用业务文档集合。

### FIN-T2-S-general-or-specific-02

先解释这个，不要查我的账户。

- 来源：assistant_authored_state_pair_expansion / 新起草；同源组：fin-t2-state:general-or-specific
- 复核状态：assistant_draft
- 历史：[{"role": "user", "content": "我问你们平台对“补交材料时限”这一条到底怎么规定的。"}]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "retrieve", "tool_name": null, "tool_arguments": {}, "retrieval_collection": "loan_service_docs", "missing_slots": []}
- 依据：不查个人账户并不等于不检索；平台条款仍需正式文档。

## tool

## answer

## human

## redirect

## refuse

## close
