# 公开训练语料金融客服改写：首批

全量整理53,860条原训练用户轮次；本批376条候选＝316条金融改写＋60条原文域外引导。另24条起草稿隔离。尚有46,308条待继续改造，**并非全量完成**，未训练或发布。

- [原句→金融客服对照](before-after.md)
- [按动作阅读](review.md)
- `cases.jsonl`：只包含本批候选；原句在provenance，不是模型输入。
- `manifest.json`：完整进度计数和校验基准。
- `inventory-summary.json`：全来源盘点、授权线索与源文件哈希。
- `review-revision.json`：独立agent审查后的修订记录；不是人工确认。
- [来源归属、许可与修改说明](NOTICE.md)
- [全量分流、文件位置与操作说明](../../docs/33-公开语料全量分流与金融客服改写.md)

完整版原文账本和pending队列位于仓库`.local/financial-public-rewrite-v1/`，不上传GitHub。MASSIVE CC-BY-4.0，CrossWOZ Apache-2.0（仓库层级）；作者归属、来源和修改说明见报告及逐条provenance。CFINCusSerC未参与本批改写。
