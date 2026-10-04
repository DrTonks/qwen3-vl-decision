# 金融客服八动作文本候选 v2

1,020条草稿：1,019条候选、1条待讨论。子agent协作起草与复审，未进行当前版本人工复核，尚未训练。来源与能力边界见[本轮报告](../../docs/32-金融客服文本扩充与子Agent复审.md)。

|动作|逐条阅读|
|---|---|
|澄清|[clarify](review-by-action/clarify.md)|
|检索|[retrieve](review-by-action/retrieve.md)|
|查询工具|[tool](review-by-action/tool.md)|
|直接响应|[answer](review-by-action/answer.md)|
|人工协助|[human](review-by-action/human.md)|
|引导回服务|[redirect](review-by-action/redirect.md)|
|拒绝操作|[refuse](review-by-action/refuse.md)|
|结束咨询|[close](review-by-action/close.md)|

也可阅读[全集](review.md)、[待讨论项](pending-review.md)、[标注编辑指南](annotation-guide.md)和[子agent审查记录](agent-review.md)。主数据为`cases.jsonl`；manifest与validation为本次交付时快照。模型只读取input，不读取标注、理由、来源或审核状态。

MASSIVE公开部分使用原训练分区，CC-BY-4.0；原作者归属、官方链接见sources.json，重新标注与改写记录在各条provenance。其余合成来源明确保留。此目录无模型权重或私有数据库记录。
