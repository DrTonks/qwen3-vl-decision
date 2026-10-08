# 可信状态成对覆盖：训练来源阅读版

仅为结构审计；不改标签、不产生训练发布。完整输入/原标签见JSON。

## PAIR-39f1828fc43ced4e / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0159",
  "input": {
    "message": "工薪贷当前产品记录上的标签是什么？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0160",
  "input": {
    "message": "工薪贷当前产品记录上的标签是什么？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-021869eca6e8ecda / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0187",
  "input": {
    "message": "查我已有申请清单中的产品编号。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0188",
  "input": {
    "message": "查我已有申请清单中的产品编号。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-bd59b809ef617657 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3795-1",
  "input": {
    "message": "我目前的信用评分和档位是什么？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3795",
  "input": {
    "message": "我目前的信用评分和档位是什么？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "score与band为信用工具支持字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-cc116ed2eec2f2f9 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3795-2",
  "input": {
    "message": "我目前的信用评分和档位是什么？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3795",
  "input": {
    "message": "我目前的信用评分和档位是什么？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "score与band为信用工具支持字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-b46fe517e8c920b4 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0195",
  "input": {
    "message": "我要查看已有的本账户评分数值。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0196",
  "input": {
    "message": "我要查看已有的本账户评分数值。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-ec7a6a02be0d0049 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0139",
  "input": {
    "message": "把已经入库的我的申请编号列出来。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0140",
  "input": {
    "message": "把已经入库的我的申请编号列出来。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-573345a89224cd6e / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0662-1",
  "input": {
    "message": "想确认自己提交过哪些申请，请查询当前账户列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0662",
  "input": {
    "message": "想确认自己提交过哪些申请，请查询当前账户列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且申请列表工具可用，明确查询本人已有申请列表，无需知识检索，不扩展为写入或完整历史保证。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-c357ee937caccc42 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0662-2",
  "input": {
    "message": "想确认自己提交过哪些申请，请查询当前账户列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0662",
  "input": {
    "message": "想确认自己提交过哪些申请，请查询当前账户列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且申请列表工具可用，明确查询本人已有申请列表，无需知识检索，不扩展为写入或完整历史保证。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6da9181fa5401544 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-301-1",
  "input": {
    "message": "我这边借款申请的情况怎么样，先帮我查名下记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-301",
  "input": {
    "message": "我这边借款申请的情况怎么样，先帮我查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "目标为当前可用只读查询，用户已登录；所需对象在输入中明确。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-4a74bce78c5fe01c / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-301-2",
  "input": {
    "message": "我这边借款申请的情况怎么样，先帮我查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-301",
  "input": {
    "message": "我这边借款申请的情况怎么样，先帮我查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "目标为当前可用只读查询，用户已登录；所需对象在输入中明确。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-2994faf9aca531cc / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0125",
  "input": {
    "message": "请列出这个账号已经提交的借款申请。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0126",
  "input": {
    "message": "请列出这个账号已经提交的借款申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a5806dbb46c860bd / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=True, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-11737-1",
  "input": {
    "message": "我的贷款账户现在信用分是多少、属于什么档位，查一下。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-11737",
  "input": {
    "message": "我的贷款账户现在信用分是多少、属于什么档位，查一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "信用查询工具支持分数与档位。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-d36bd1141583642b / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-11737-2",
  "input": {
    "message": "我的贷款账户现在信用分是多少、属于什么档位，查一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-11737",
  "input": {
    "message": "我的贷款账户现在信用分是多少、属于什么档位，查一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "信用查询工具支持分数与档位。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-886a124cd583df0b / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0157",
  "input": {
    "message": "帮我读出产品目录里的审批难度分，不要预测通过率。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0158",
  "input": {
    "message": "帮我读出产品目录里的审批难度分，不要预测通过率。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-c259e55336837b42 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3171-1",
  "input": {
    "message": "看一下本人登录账号的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3171",
  "input": {
    "message": "看一下本人登录账号的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，queryMyApplications提供编号、金额、产品ID和当前状态。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a8683ba0cbbbec0d / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3171-2",
  "input": {
    "message": "看一下本人登录账号的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3171",
  "input": {
    "message": "看一下本人登录账号的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，queryMyApplications提供编号、金额、产品ID和当前状态。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-13aecde0a4289846 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-4451-1",
  "input": {
    "message": "我有提交过借款申请吗？先查当前账号里的记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-4451",
  "input": {
    "message": "我有提交过借款申请吗？先查当前账号里的记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表能核实本人记录有无。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-1e8f846a3aae112a / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-4451-2",
  "input": {
    "message": "我有提交过借款申请吗？先查当前账号里的记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-4451",
  "input": {
    "message": "我有提交过借款申请吗？先查当前账号里的记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表能核实本人记录有无。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a189b4d54c3e5cd1 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0131",
  "input": {
    "message": "帮我调取本账户的申请清单。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0132",
  "input": {
    "message": "帮我调取本账户的申请清单。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-4183499ec801794d / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-557-1",
  "input": {
    "message": "我名下总共有多少条贷款申请记录啊？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-557",
  "input": {
    "message": "我名下总共有多少条贷款申请记录啊？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表能支持统计本人申请条数。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-26152c1e9bd64bc8 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-557-2",
  "input": {
    "message": "我名下总共有多少条贷款申请记录啊？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-557",
  "input": {
    "message": "我名下总共有多少条贷款申请记录啊？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表能支持统计本人申请条数。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-b54eeebab0e66ef0 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0129",
  "input": {
    "message": "查我的全部借款申请和列表中的状态。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0130",
  "input": {
    "message": "查我的全部借款申请和列表中的状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-ae46441814da4f89 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0149",
  "input": {
    "message": "贷款产品资料里的标签都有哪些？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0150",
  "input": {
    "message": "贷款产品资料里的标签都有哪些？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-10bc61db1f4a8953 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0193",
  "input": {
    "message": "读取本账号的信用分和建议额度记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0194",
  "input": {
    "message": "读取本账号的信用分和建议额度记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-8575cdbc6aeaf42d / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7478-1",
  "input": {
    "message": "告诉我待审核的贷款申请有哪些。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7478",
  "input": {
    "message": "告诉我待审核的贷款申请有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表status可用于筛选实际返回记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6d76ea41f2fb5bba / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7478-2",
  "input": {
    "message": "告诉我待审核的贷款申请有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7478",
  "input": {
    "message": "告诉我待审核的贷款申请有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "申请列表status可用于筛选实际返回记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-cb160004384bfa1e / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0123",
  "input": {
    "message": "先告诉我个人评分记录中的建议额度。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0124",
  "input": {
    "message": "先告诉我个人评分记录中的建议额度。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-842f72e4c417faf2 / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=True

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0678-1",
  "input": {
    "message": "无需知识库，只读查看我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0678",
  "input": {
    "message": "无需知识库，只读查看我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户明确查询本人列表，不是未知规则或需要单笔编号，可使用只读列表工具并保留返回范围限制。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-3252e01fd34ad169 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0678-2",
  "input": {
    "message": "无需知识库，只读查看我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0678",
  "input": {
    "message": "无需知识库，只读查看我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户明确查询本人列表，不是未知规则或需要单笔编号，可使用只读列表工具并保留返回范围限制。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-11e345db0117b5fc / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0189",
  "input": {
    "message": "列出我本人提交的申请，暂不新增申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0190",
  "input": {
    "message": "列出我本人提交的申请，暂不新增申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9c62053bf51fda9b / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0111",
  "input": {
    "message": "请查本账户保存的信用评分数值。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0112",
  "input": {
    "message": "请查本账户保存的信用评分数值。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-4ab0664e5f326b92 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0135",
  "input": {
    "message": "请展示本人名下的申请列表，不查询别人的。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0136",
  "input": {
    "message": "请展示本人名下的申请列表，不查询别人的。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6191ff131776a895 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3981-1",
  "input": {
    "message": "请打开我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3981",
  "input": {
    "message": "请打开我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确查询本人列表且已认证。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-2aa858aeba1ec503 / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3981-2",
  "input": {
    "message": "请打开我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3981",
  "input": {
    "message": "请打开我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确查询本人列表且已认证。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-d9bcc2af2c1ec94e / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0113",
  "input": {
    "message": "我的当前信用分和评分档位能查到吗？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0114",
  "input": {
    "message": "我的当前信用分和评分档位能查到吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-76a7e9b70a8403ca / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2139-1",
  "input": {
    "message": "我名下那几笔贷款申请现在咋样，查个列表给我。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2139",
  "input": {
    "message": "我名下那几笔贷款申请现在咋样，查个列表给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，查询本人申请列表的编号、金额或状态；无需指定单笔编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-26036d344f39f44b / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2139-2",
  "input": {
    "message": "我名下那几笔贷款申请现在咋样，查个列表给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2139",
  "input": {
    "message": "我名下那几笔贷款申请现在咋样，查个列表给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，查询本人申请列表的编号、金额或状态；无需指定单笔编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-73bd8ca94e42a6f6 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-13520-1",
  "input": {
    "message": "我名下还有哪些贷款申请记录，列出来我看一下。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-13520",
  "input": {
    "message": "我名下还有哪些贷款申请记录，列出来我看一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "查询本人申请列表在现有能力内。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-dfebc08528a835b7 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-13520-2",
  "input": {
    "message": "我名下还有哪些贷款申请记录，列出来我看一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-13520",
  "input": {
    "message": "我名下还有哪些贷款申请记录，列出来我看一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "查询本人申请列表在现有能力内。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-ac927ef5740f8efc / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0147",
  "input": {
    "message": "各产品目前保存的审批难度分是多少？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0148",
  "input": {
    "message": "各产品目前保存的审批难度分是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-4a2f7fed27d0a1d0 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0121",
  "input": {
    "message": "读取一下当前账号的信用评分和档位。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0122",
  "input": {
    "message": "读取一下当前账号的信用评分和档位。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-fe67305cf0a247cb / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0119",
  "input": {
    "message": "系统记下来的我的分值是多少，不要重新预测。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0120",
  "input": {
    "message": "系统记下来的我的分值是多少，不要重新预测。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-51759a19a09fb234 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=True, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3925-1",
  "input": {
    "message": "这部分讲完后，马上查我名下的申请列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3925",
  "input": {
    "message": "这部分讲完后，马上查我名下的申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确后续读取本人申请列表，模拟状态已认证。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-676e04be62f2089d / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3925-2",
  "input": {
    "message": "这部分讲完后，马上查我名下的申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3925",
  "input": {
    "message": "这部分讲完后，马上查我名下的申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确后续读取本人申请列表，模拟状态已认证。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-59a831ce08b177a2 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1975-1",
  "input": {
    "message": "我有没有已经提交过的贷款申请？帮我查查名下记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1975",
  "input": {
    "message": "我有没有已经提交过的贷款申请？帮我查查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "请求本人已有申请是否存在，可查询列表。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-da25e2b8e790d6cc / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1975-2",
  "input": {
    "message": "我有没有已经提交过的贷款申请？帮我查查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1975",
  "input": {
    "message": "我有没有已经提交过的贷款申请？帮我查查名下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "请求本人已有申请是否存在，可查询列表。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-35cdc004bffa0da8 / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-12169-0-1",
  "input": {
    "message": "你好，我想看看自己除了申请7623之外，还提交过哪些借款申请。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-12169-0",
  "input": {
    "message": "你好，我想看看自己除了申请7623之外，还提交过哪些借款申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户请求自己申请集合并排除7623，已登录可通过本人申请列表确认其他记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-1030293dc2cb8961 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-12169-0-2",
  "input": {
    "message": "你好，我想看看自己除了申请7623之外，还提交过哪些借款申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-12169-0",
  "input": {
    "message": "你好，我想看看自己除了申请7623之外，还提交过哪些借款申请。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户请求自己申请集合并排除7623，已登录可通过本人申请列表确认其他记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-0642749f75c56801 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0141",
  "input": {
    "message": "请查询平台当前的贷款产品目录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0142",
  "input": {
    "message": "请查询平台当前的贷款产品目录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-c3f4f3116ce34fe8 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0127",
  "input": {
    "message": "我想看我的申请列表里有哪些记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0128",
  "input": {
    "message": "我想看我的申请列表里有哪些记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-276ff80628ef765b / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-TR1-S-0863-1",
  "input": {
    "message": "不是解释提示，请查询我这个账号当前的信用评分。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-S-0863",
  "input": {
    "message": "不是解释提示，请查询我这个账号当前的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且明确要求当前本人评分，使用只读评分工具。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-336e17c06ae6f7ba / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-TR1-S-0863-2",
  "input": {
    "message": "不是解释提示，请查询我这个账号当前的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-S-0863",
  "input": {
    "message": "不是解释提示，请查询我这个账号当前的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且明确要求当前本人评分，使用只读评分工具。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e2e767d32db50c21 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7271-1",
  "input": {
    "message": "看看我的借款申请列表，现在分别处在哪个审核阶段。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7271",
  "input": {
    "message": "看看我的借款申请列表，现在分别处在哪个审核阶段。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录且先请求本人申请列表，工具支持编号、金额和当前状态；没有声称支持提交时间或还款流水。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-b912c78b34f39355 / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7271-2",
  "input": {
    "message": "看看我的借款申请列表，现在分别处在哪个审核阶段。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7271",
  "input": {
    "message": "看看我的借款申请列表，现在分别处在哪个审核阶段。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录且先请求本人申请列表，工具支持编号、金额和当前状态；没有声称支持提交时间或还款流水。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-89c262d961956db8 / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0137",
  "input": {
    "message": "当前账户有哪些申请记录及金额？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0138",
  "input": {
    "message": "当前账户有哪些申请记录及金额？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-39d18d7fba8955b2 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0155",
  "input": {
    "message": "平台现有产品有哪些金额上限？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0156",
  "input": {
    "message": "平台现有产品有哪些金额上限？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-779bcaa207daff48 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0153",
  "input": {
    "message": "我需要实时产品清单里的名称和编号。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0154",
  "input": {
    "message": "我需要实时产品清单里的名称和编号。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-f009dbf8fcbb0073 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2294-1",
  "input": {
    "message": "当前账号里保存的信用评分和档位能帮我读出来吗？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2294",
  "input": {
    "message": "当前账号里保存的信用评分和档位能帮我读出来吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，读取本人已有的信用评分及摘要，不重新评估信用。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9be1bd7e09be3716 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2294-2",
  "input": {
    "message": "当前账号里保存的信用评分和档位能帮我读出来吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2294",
  "input": {
    "message": "当前账号里保存的信用评分和档位能帮我读出来吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，读取本人已有的信用评分及摘要，不重新评估信用。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-00a605c003c9423a / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7282-1",
  "input": {
    "message": "我手头还有多少贷款申请在审批，先列出你当前能查到的那部分。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7282",
  "input": {
    "message": "我手头还有多少贷款申请在审批，先列出你当前能查到的那部分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录且先请求本人申请列表，工具支持编号、金额和当前状态；没有声称支持提交时间或还款流水。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-14e492c0d1be97e1 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7282-2",
  "input": {
    "message": "我手头还有多少贷款申请在审批，先列出你当前能查到的那部分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7282",
  "input": {
    "message": "我手头还有多少贷款申请在审批，先列出你当前能查到的那部分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录且先请求本人申请列表，工具支持编号、金额和当前状态；没有声称支持提交时间或还款流水。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a5667d1ad54c984d / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-12583-1",
  "input": {
    "message": "目前贷款申请939583的金额和期数是多少？",
    "history": [],
    "state": {
      "authenticated": false,
      "application_id": 939583,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-12583",
  "input": {
    "message": "目前贷款申请939583的金额和期数是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 939583,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 939583
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号明确，详情支持amount/months。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-913c1faa47a9578f / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-12583-2",
  "input": {
    "message": "目前贷款申请939583的金额和期数是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 939583,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-12583",
  "input": {
    "message": "目前贷款申请939583的金额和期数是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 939583,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 939583
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号明确，详情支持amount/months。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6a8a66be88082c3a / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2857-1",
  "input": {
    "message": "今儿想核对所有借款申请，给我看当前账号的列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2857",
  "input": {
    "message": "今儿想核对所有借款申请，给我看当前账号的列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-12ebbb51dffd7548 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2857-2",
  "input": {
    "message": "今儿想核对所有借款申请，给我看当前账号的列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2857",
  "input": {
    "message": "今儿想核对所有借款申请，给我看当前账号的列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-1c47772655d55fe5 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5310-1",
  "input": {
    "message": "客服，查询我当前账号的借款申请，列出每笔金额和状态。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5310",
  "input": {
    "message": "客服，查询我当前账号的借款申请，列出每笔金额和状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，明确先看本人申请列表；工具返回编号、产品ID、金额和当前状态，不输出提交日期或频次排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9680dae2bfbf5888 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5310-2",
  "input": {
    "message": "客服，查询我当前账号的借款申请，列出每笔金额和状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5310",
  "input": {
    "message": "客服，查询我当前账号的借款申请，列出每笔金额和状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，明确先看本人申请列表；工具返回编号、产品ID、金额和当前状态，不输出提交日期或频次排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-7f94f6c61a104049 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1447-1",
  "input": {
    "message": "把我的申请列表按你查到的顺序展示就行，不用随机给我挑一笔。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1447",
  "input": {
    "message": "把我的申请列表按你查到的顺序展示就行，不用随机给我挑一笔。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e67063e8b978eb0a / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1447-2",
  "input": {
    "message": "把我的申请列表按你查到的顺序展示就行，不用随机给我挑一笔。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1447",
  "input": {
    "message": "把我的申请列表按你查到的顺序展示就行，不用随机给我挑一笔。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-ecf01c89fbada547 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1437-1",
  "input": {
    "message": "让我看看本人账号里的申请记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1437",
  "input": {
    "message": "让我看看本人账号里的申请记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a11b44edd19d5762 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1437-2",
  "input": {
    "message": "让我看看本人账号里的申请记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1437",
  "input": {
    "message": "让我看看本人账号里的申请记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6820ed7f609d6ac9 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-10819-1",
  "input": {
    "message": "告诉我贷款申请929819的金额、期数和用途。",
    "history": [],
    "state": {
      "authenticated": false,
      "application_id": 929819,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-10819",
  "input": {
    "message": "告诉我贷款申请929819的金额、期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 929819,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 929819
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号完整，详情支持所需三字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-da8ae0ded7a96a4a / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-10819-2",
  "input": {
    "message": "告诉我贷款申请929819的金额、期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 929819,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-10819",
  "input": {
    "message": "告诉我贷款申请929819的金额、期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 929819,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 929819
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号完整，详情支持所需三字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6db7b377602077b2 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0191",
  "input": {
    "message": "当前个人评分档位请帮我从记录里查。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0192",
  "input": {
    "message": "当前个人评分档位请帮我从记录里查。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6ac204322d794718 / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7673-1",
  "input": {
    "message": "看看贷款申请923673的期数和用途。",
    "history": [],
    "state": {
      "authenticated": false,
      "application_id": 923673,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7673",
  "input": {
    "message": "看看贷款申请923673的期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923673,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 923673
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号明确，详情支持months及usage。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-1bd4b87cee7436d3 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7673-2",
  "input": {
    "message": "看看贷款申请923673的期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923673,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7673",
  "input": {
    "message": "看看贷款申请923673的期数和用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923673,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 923673
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "编号明确，详情支持months及usage。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-8176302d95ffd347 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0133",
  "input": {
    "message": "我提交过哪些贷款申请，先列出来。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0134",
  "input": {
    "message": "我提交过哪些贷款申请，先列出来。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-44d0b5a490ba141b / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0115",
  "input": {
    "message": "账户里记录的建议额度是多少？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0116",
  "input": {
    "message": "账户里记录的建议额度是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-761a2e4af19d09e0 / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0197",
  "input": {
    "message": "请核对本人信用评分记录对应的档位。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0198",
  "input": {
    "message": "请核对本人信用评分记录对应的档位。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-46cf1350da2eec59 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3479-1",
  "input": {
    "message": "把我当前账号所有借款申请编号和状态列给我。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3479",
  "input": {
    "message": "把我当前账号所有借款申请编号和状态列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-606ef17ec224c907 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3479-2",
  "input": {
    "message": "把我当前账号所有借款申请编号和状态列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3479",
  "input": {
    "message": "把我当前账号所有借款申请编号和状态列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e71790c08e6fb119 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-6508-1",
  "input": {
    "message": "把当前账号的贷款申请记录列给我。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-6508",
  "input": {
    "message": "把当前账号的贷款申请记录列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人申请列表支持读取。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a4f0bf3d9db99213 / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-6508-2",
  "input": {
    "message": "把当前账号的贷款申请记录列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-6508",
  "input": {
    "message": "把当前账号的贷款申请记录列给我。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人申请列表支持读取。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-bd18246d790a4776 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-15188-1",
  "input": {
    "message": "查看一下我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-15188",
  "input": {
    "message": "查看一下我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "直接请求本人申请列表，可用列表工具。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-7cfc44f2852ae3b2 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-15188-2",
  "input": {
    "message": "查看一下我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-15188",
  "input": {
    "message": "查看一下我的贷款申请列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "直接请求本人申请列表，可用列表工具。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-bf38033b6fde6755 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3105-1",
  "input": {
    "message": "现在我的账号里保存的信用分是多少？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3105",
  "input": {
    "message": "现在我的账号里保存的信用分是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，只读本人已有评分或档位，queryMyCreditScore提供相关字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-f4c3571d8b65c808 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3105-2",
  "input": {
    "message": "现在我的账号里保存的信用分是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3105",
  "input": {
    "message": "现在我的账号里保存的信用分是多少？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，只读本人已有评分或档位，queryMyCreditScore提供相关字段。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-2041d0b00f398722 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-10000-0-1",
  "input": {
    "message": "你好，想先查自己有哪些贷款申请，帮我列一下吧。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-10000-0",
  "input": {
    "message": "你好，想先查自己有哪些贷款申请，帮我列一下吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "认证用户请求本人申请列表，无需单笔编号，可用列表工具。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-812aafab20430ed2 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-10000-0-2",
  "input": {
    "message": "你好，想先查自己有哪些贷款申请，帮我列一下吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-10000-0",
  "input": {
    "message": "你好，想先查自己有哪些贷款申请，帮我列一下吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "认证用户请求本人申请列表，无需单笔编号，可用列表工具。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e3f09f1d4b292b81 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1645-1",
  "input": {
    "message": "我名下到底有没有贷款申请记录？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1645",
  "input": {
    "message": "我名下到底有没有贷款申请记录？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确查询本人申请存在性，可获取申请列表。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e4ea2d29da3580e7 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1645-2",
  "input": {
    "message": "我名下到底有没有贷款申请记录？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1645",
  "input": {
    "message": "我名下到底有没有贷款申请记录？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确查询本人申请存在性，可获取申请列表。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-70f4f6232477e503 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0185",
  "input": {
    "message": "我需要核对个人借款申请的列表状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0186",
  "input": {
    "message": "我需要核对个人借款申请的列表状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-e53f977ad7c7fdcd / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0692-1",
  "input": {
    "message": "我不是要你加分，只查看自己的信用评估。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0692",
  "input": {
    "message": "我不是要你加分，只查看自己的信用评估。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "请求本人当前评估记录而非公式、原因或规则，缺少知识库不妨碍可用只读评分查询。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-437b25078d308fdd / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-F2-T-0692-2",
  "input": {
    "message": "我不是要你加分，只查看自己的信用评估。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-F2-T-0692",
  "input": {
    "message": "我不是要你加分，只查看自己的信用评估。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "请求本人当前评估记录而非公式、原因或规则，缺少知识库不妨碍可用只读评分查询。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-03723ba99f357f83 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0145",
  "input": {
    "message": "想比较当前产品记录里的最高金额。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0146",
  "input": {
    "message": "想比较当前产品记录里的最高金额。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-3082e0666a23ef0c / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3488-1",
  "input": {
    "message": "先从我名下的贷款申请列表看起。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3488",
  "input": {
    "message": "先从我名下的贷款申请列表看起。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-16af453c08e804d8 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3488-2",
  "input": {
    "message": "先从我名下的贷款申请列表看起。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3488",
  "input": {
    "message": "先从我名下的贷款申请列表看起。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-8606da53c1754d3f / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0151",
  "input": {
    "message": "查一下当前产品列表里的极速贷最高额度。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0152",
  "input": {
    "message": "查一下当前产品列表里的极速贷最高额度。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-90da00920cc3344f / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0199",
  "input": {
    "message": "本账户现存的推荐额度记录帮我查询一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0200",
  "input": {
    "message": "本账户现存的推荐额度记录帮我查询一下。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a0d9462ccc39117a / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7359-1",
  "input": {
    "message": "我得把贷款申请记录整理出来，帮我查各笔现在的状态。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7359",
  "input": {
    "message": "我得把贷款申请记录整理出来，帮我查各笔现在的状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "列表可返回各笔status，范围限实际返回记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-bffbcc816fb13890 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7359-2",
  "input": {
    "message": "我得把贷款申请记录整理出来，帮我查各笔现在的状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7359",
  "input": {
    "message": "我得把贷款申请记录整理出来，帮我查各笔现在的状态。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "列表可返回各笔status，范围限实际返回记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6d39d058efe361b6 / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0117",
  "input": {
    "message": "我想查看属于我自己的评分记录。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0118",
  "input": {
    "message": "我想查看属于我自己的评分记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-290b65671aa77a22 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0143",
  "input": {
    "message": "现有借款产品各自叫什么名字？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "当前未认证；按现有后端所有工具要求登录的契约先完成认证，不执行查询。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0144",
  "input": {
    "message": "现有借款产品各自叫什么名字？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryLoanProducts",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已认证且只读工具可用；查询已有记录，不承诺贷款审批或额度资格。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-baad4e981a7e0897 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-7722-0-1",
  "input": {
    "message": "你好，请帮我查询自己账户里当前已有的信用评分。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-7722-0",
  "input": {
    "message": "你好，请帮我查询自己账户里当前已有的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "认证有效，请求本人已有评分，信用查询工具支持。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9eb4b313eae41391 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-7722-0-2",
  "input": {
    "message": "你好，请帮我查询自己账户里当前已有的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-7722-0",
  "input": {
    "message": "你好，请帮我查询自己账户里当前已有的信用评分。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "认证有效，请求本人已有评分，信用查询工具支持。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-c7e24c5d97f2949d / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5866-1",
  "input": {
    "message": "我账户里还有贷款申请记录吗？",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5866",
  "input": {
    "message": "我账户里还有贷款申请记录吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人申请列表可读取现有记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-38696b5c3e71c66c / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5866-2",
  "input": {
    "message": "我账户里还有贷款申请记录吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5866",
  "input": {
    "message": "我账户里还有贷款申请记录吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人申请列表可读取现有记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-1cdb14af5c1284ce / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7428-1",
  "input": {
    "message": "能帮我查一下贷款申请923428当前的期数和用途吗？",
    "history": [],
    "state": {
      "authenticated": false,
      "application_id": 923428,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7428",
  "input": {
    "message": "能帮我查一下贷款申请923428当前的期数和用途吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923428,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 923428
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "详情含months及usage且编号齐全。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-972db1960d35851e / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-7428-2",
  "input": {
    "message": "能帮我查一下贷款申请923428当前的期数和用途吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923428,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-7428",
  "input": {
    "message": "能帮我查一下贷款申请923428当前的期数和用途吗？",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 923428,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 923428
    },
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "详情含months及usage且编号齐全。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9a7af74f72e254e4 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-TR1-S-0957-1",
  "input": {
    "message": "能力说明听懂了，接下来请查本账号的申请列表，不要结束对话。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-S-0957",
  "input": {
    "message": "能力说明听懂了，接下来请查本账号的申请列表，不要结束对话。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户明确继续并请求可用只读列表查询，不关闭咨询。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-6c0a9467aac647f7 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-TR1-S-0957-2",
  "input": {
    "message": "能力说明听懂了，接下来请查本账号的申请列表，不要结束对话。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-S-0957",
  "input": {
    "message": "能力说明听懂了，接下来请查本账号的申请列表，不要结束对话。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "用户明确继续并请求可用只读列表查询，不关闭咨询。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-806585f1bf941694 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-356-1",
  "input": {
    "message": "我想找最近提交的那笔，但忘了编号，先把我的申请列表调出来。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-356",
  "input": {
    "message": "我想找最近提交的那笔，但忘了编号，先把我的申请列表调出来。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "目标为当前可用只读查询，用户已登录；所需对象在输入中明确。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-bc1b4c14e3862c66 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-356-2",
  "input": {
    "message": "我想找最近提交的那笔，但忘了编号，先把我的申请列表调出来。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-356",
  "input": {
    "message": "我想找最近提交的那笔，但忘了编号，先把我的申请列表调出来。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "目标为当前可用只读查询，用户已登录；所需对象在输入中明确。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-3613921dba96875f / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0181",
  "input": {
    "message": "请读出我这个账户的最新申请清单。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0182",
  "input": {
    "message": "请读出我这个账户的最新申请清单。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-878388716bbaf513 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-6278-1",
  "input": {
    "message": "帮我算一下，我目前这些申请的借款金额加起来多少。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-6278",
  "input": {
    "message": "帮我算一下，我目前这些申请的借款金额加起来多少。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "列表有amount，可汇总实际返回的记录，须尊重不完整标记。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-9bf161d9ea569c7b / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-6278-2",
  "input": {
    "message": "帮我算一下，我目前这些申请的借款金额加起来多少。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-6278",
  "input": {
    "message": "帮我算一下，我目前这些申请的借款金额加起来多少。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "列表有amount，可汇总实际返回的记录，须尊重不完整标记。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-78e811d6a5d3942c / authentication

变动字段：state.authenticated
两侧均入选：uniform=True, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1456-1",
  "input": {
    "message": "我这边贷款申请现在咋样了？先拉一下名下列表吧。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1456",
  "input": {
    "message": "我这边贷款申请现在咋样了？先拉一下名下列表吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-70224d3fe5ee11e8 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1456-2",
  "input": {
    "message": "我这边贷款申请现在咋样了？先拉一下名下列表吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1456",
  "input": {
    "message": "我这边贷款申请现在咋样了？先拉一下名下列表吧。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-ca6650e2d39d292d / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3684-1",
  "input": {
    "message": "我的历史借款申请列表调出来，不用猜哪种申请次数最多。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3684",
  "input": {
    "message": "我的历史借款申请列表调出来，不用猜哪种申请次数最多。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-509a6f1483751aeb / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-3684-2",
  "input": {
    "message": "我的历史借款申请列表调出来，不用猜哪种申请次数最多。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-3684",
  "input": {
    "message": "我的历史借款申请列表调出来，不用猜哪种申请次数最多。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，请求本人申请列表，列表工具可返回申请编号、产品ID、金额及状态，不声称提交时间或频率排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-eecda430750e44a8 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2377-1",
  "input": {
    "message": "打开我的贷款申请列表，登录账号就是本人。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2377",
  "input": {
    "message": "打开我的贷款申请列表，登录账号就是本人。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，查询本人申请列表的编号、金额或状态；无需指定单笔编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-cf91961c96bf3b7f / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-2377-2",
  "input": {
    "message": "打开我的贷款申请列表，登录账号就是本人。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-2377",
  "input": {
    "message": "打开我的贷款申请列表，登录账号就是本人。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，查询本人申请列表的编号、金额或状态；无需指定单笔编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-fd778e7717cf72da / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5096-1",
  "input": {
    "message": "把本人账号的借款申请全列出来，我逐笔看。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5096",
  "input": {
    "message": "把本人账号的借款申请全列出来，我逐笔看。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，明确先看本人申请列表；工具返回编号、产品ID、金额和当前状态，不输出提交日期或频次排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-974399e89d5934a1 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-5096-2",
  "input": {
    "message": "把本人账号的借款申请全列出来，我逐笔看。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-5096",
  "input": {
    "message": "把本人账号的借款申请全列出来，我逐笔看。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录，明确先看本人申请列表；工具返回编号、产品ID、金额和当前状态，不输出提交日期或频次排行。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-8823e541e4f95bb2 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-TR1-C-0183",
  "input": {
    "message": "本账户有哪些申请编号和金额，查一下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "本人已认证且白名单工具可用，可以只读查询当前账户记录。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-TR1-C-0184",
  "input": {
    "message": "本账户有哪些申请编号和金额，查一下记录。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人查询工具不可用，建议人工协助；handoff未接通，不声称已创建工单或已接通人工。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-d2069b8c43636cc5 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1307-1",
  "input": {
    "message": "我今天想看名下申请的办理情况，帮忙查一下列表。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1307",
  "input": {
    "message": "我今天想看名下申请的办理情况，帮忙查一下列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-a227febabe1ebfaa / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-massive-train-1307-2",
  "input": {
    "message": "我今天想看名下申请的办理情况，帮忙查一下列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-massive-train-1307",
  "input": {
    "message": "我今天想看名下申请的办理情况，帮忙查一下列表。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "已登录；查询本人申请列表中的编号、产品编号、金额或状态，无须单笔申请编号。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-27006caede69a6a4 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-10233-0-1",
  "input": {
    "message": "你好，想把我之前提交的贷款申请查出来，帮我看看有哪些。",
    "history": [],
    "state": {
      "authenticated": false,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [
      "authentication"
    ],
    "reason": "查询仍需认证；此语境没有独立人工/违规诉求，先完成登录。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-10233-0",
  "input": {
    "message": "你好，想把我之前提交的贷款申请查出来，帮我看看有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确本人已提交申请集合，已登录状态可用列表工具，无需单笔ID。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-c8c29fa63cd5bed6 / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=False, preauth400=False

```json
{
  "id": "FIN-BC1-query-FIN-R4-crosswoz-train-10233-0-2",
  "input": {
    "message": "你好，想把我之前提交的贷款申请查出来，帮我看看有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "所需个人记录工具缺失，不能用其他工具伪装同一能力；人工动作不代表已接通。",
    "evidence_paths": [
      "input.message"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "FIN-R4-crosswoz-train-10233-0",
  "input": {
    "message": "你好，想把我之前提交的贷款申请查出来，帮我看看有哪些。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "planned-kb",
    "capabilities": {
      "knowledge_collections": [
        "loan_service_docs",
        "privacy_policy"
      ],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyApplications",
    "tool_arguments": {},
    "retrieval_collection": null,
    "missing_slots": [],
    "reason": "明确本人已提交申请集合，已登录状态可用列表工具，无需单笔ID。",
    "evidence_paths": [
      "input.message",
      "input.history",
      "input.state",
      "input.capabilities",
      "input.available_tools"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-0aaab6c9a412dc2b / tool_availability

变动字段：available_tools
两侧均入选：uniform=True, stratified=True, preauth400=True

```json
{
  "id": "SEA-G043-1",
  "input": {
    "message": "帮我查已存建议额度，我要核对夜市桌椅预算。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryMyCreditScore",
    "tool_arguments": {},
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "夜市桌椅信用查看能力撤除：要求读取本人已经保存的信用记录，可用工具提供评分、档位或建议额度。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "SEA-G043-2",
  "input": {
    "message": "帮我查已存建议额度，我要核对夜市桌椅预算。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "夜市桌椅信用查看能力撤除：要求实际办理、人工处理或读取现有工具未提供的个人业务内容，应交人工。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-fc050da78a5757dd / tool_availability

变动字段：available_tools
两侧均入选：uniform=False, stratified=True, preauth400=True

```json
{
  "id": "SEA-G044-1",
  "input": {
    "message": "申请310927，我要查渔具绑钩机那笔的期数。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 310927,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 310927
    },
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "渔具绑钩机编号存在而详情工具缺席：本人目标申请已唯一明确，所问字段由可用明细工具提供。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "SEA-G044-2",
  "input": {
    "message": "申请310927，我要查渔具绑钩机那笔的期数。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 310927,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryMyApplications"
    ],
    "images": []
  },
  "annotation": {
    "action": "human",
    "tool_name": null,
    "tool_arguments": {},
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "渔具绑钩机编号存在而详情工具缺席：要求实际办理、人工处理或读取现有工具未提供的个人业务内容，应交人工。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-89ea5dca1d8927b0 / authentication

变动字段：state.authenticated
两侧均入选：uniform=False, stratified=False, preauth400=True

```json
{
  "id": "SEA-G048-1",
  "input": {
    "message": "申请311018，请查编织材料那笔的借款用途。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 311018,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 311018
    },
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "编织工作室重新认证：本人目标申请已唯一明确，所问字段由可用明细工具提供。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "SEA-G048-2",
  "input": {
    "message": "申请311018，请查编织材料那笔的借款用途。",
    "history": [],
    "state": {
      "authenticated": false,
      "application_id": 311018,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "missing_slots": [
      "authentication"
    ],
    "retrieval_collection": null,
    "reason": "编织工作室重新认证：可见输入缺少完成下一步所需的认证、唯一业务目标或有效槽值，需要先补齐。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

## PAIR-5f96c023a5d3b2bc / application_id

变动字段：state.application_id
两侧均入选：uniform=False, stratified=True, preauth400=True

```json
{
  "id": "SEA-G088-1",
  "input": {
    "message": "那单的用途请再读一次。",
    "history": [],
    "state": {
      "authenticated": true,
      "application_id": 311712,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "tool",
    "tool_name": "queryApplicationDetail",
    "tool_arguments": {
      "applicationId": 311712
    },
    "missing_slots": [],
    "retrieval_collection": null,
    "reason": "农机轮胎编号代词：本人目标申请已唯一明确，所问字段由可用明细工具提供。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

```json
{
  "id": "SEA-G088-2",
  "input": {
    "message": "那单的用途请再读一次。",
    "history": [],
    "state": {
      "authenticated": true,
      "handoff_status": "none"
    },
    "service_scope": "loan_platform",
    "capability_profile": "current-node-no-kb",
    "capabilities": {
      "knowledge_collections": [],
      "handoff_available": false
    },
    "available_tools": [
      "queryLoanProducts",
      "queryMyApplications",
      "queryApplicationDetail",
      "queryMyCreditScore",
      "explainApplicationStatus"
    ],
    "images": []
  },
  "annotation": {
    "action": "clarify",
    "tool_name": null,
    "tool_arguments": {},
    "missing_slots": [
      "applicationId"
    ],
    "retrieval_collection": null,
    "reason": "农机轮胎编号代词：可见输入缺少完成下一步所需的认证、唯一业务目标或有效槽值，需要先补齐。",
    "evidence_paths": [
      "input.message",
      "input.state",
      "input.capabilities",
      "input.history"
    ],
    "policy_version": "support-financial-v2"
  }
}
```

