# 八动作首批逐条复核

助手起草/重新标注；新版本未人工复核。所有条目仅为训练候选，不是测试金标。模型只读input，不读annotation/provenance/review。

## clarify

### FIN-P1-F13-A-01-base

状态码1或2是什么意思

- 来源：business_policy_migration / F13-A-01-base；同源组：business:F13
- 复核状态：needs_discussion；可能是在同时询问两个状态，而非缺少状态；旧澄清标签未必成立，暂不纳入可选训练候选。
- 历史：[]
- 状态：{"authenticated": true}
- 能力：{"knowledge_collections": ["loan_service_docs", "privacy_policy"], "handoff_connected": false}；工具：queryLoanProducts, queryMyApplications, queryApplicationDetail, queryMyCreditScore, explainApplicationStatus
- 标签：{"action": "clarify", "tool_name": null, "tool_arguments": {}, "retrieval_collection": null, "missing_slots": ["status_code"]}
- 依据：缺少或未明确必要查询对象、状态或问题细节，先补充信息。

## retrieve

## tool

## answer

## human

## redirect

## refuse

## close
