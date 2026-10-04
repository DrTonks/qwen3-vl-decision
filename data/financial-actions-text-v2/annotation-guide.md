# v2 标注与编辑

八动作边界沿用[试点标注指南](../financial-actions-text-pilot-v1/annotation-guide.md)。本次只扩充文本候选，旧试点文件保持不变。

## 重点复核

先看同句对照（ID前缀`FIN-T2-S-`），再查看各动作阅读文件。观察历史和能力后判断下一步，不只看当前一句；不能根据是否出现“谢谢”“人工”“诈骗”直接选择动作。

工具只能读取项目已有字段，申请明细必须有完整ID并由后端验证归属。检索是假定规划中的正式知识集合可用，不能虚构文档答案。human只是推荐需要专业人工协助，未接通时不能声称已转接或建单，用户拒绝转接时也不强制执行。

`answer`不是自由编造，也不必总走大语言模型；它包含已知信息解释和诚实说明能力不足。单纯域外请求用redirect；越权、不当操作请求用refuse。多请求或标签不确定时标记`needs_discussion`并写明原因，暂缓使用。

## 编辑方法

1. 最方便的复核方式是记录样本ID、建议动作/参数和理由，再统一修改主数据。
2. 如直接修改，编辑`cases.jsonl`对应行的input或annotation；阅读版是自动生成的，修改Markdown不会更新数据。
3. 保留原ID、来源和场景组；新改写用新ID并和原文同组，不更改来源来掩盖助手起草。不要把公开测试/开发样本移入这里。
4. 当前review.status可为`assistant_draft`或`needs_discussion`。人审标志必须仍为false；后续收到具体人工确认再建立确认记录与新发布版本。agent复审不代替人工确认。
5. 运行下面命令验证结构和隔离，更新阅读版。报告/manifest是初始快照；修改后看到哈希不匹配表示待重新复核，不代表应该撤回正确修改。

```powershell
# 在qwen仓库根目录
. .\scripts\use-env.ps1
.\.venv\Scripts\python.exe -m qwenlab.financial_expansion validate
.\.venv\Scripts\python.exe -m qwenlab.financial_expansion render-review
```

本次允许的缺失槽位：`application_id`、`status_code`、`error_context`、`request_details`、`authentication`。新增槽位需先修改契约和校验，不能任意拼写。整数参数不接受布尔值。已有目录不要重新build覆盖。

将来切分按关联场景/来源对话分组，不能随机拆散四条同家族改写。443个记录组不是已证明的独立场景，语义相关但当前ID不同的组也需要继续合并。全目录当前仅train_candidate，不是新独立测试。
