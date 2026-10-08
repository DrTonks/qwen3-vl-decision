# 金融客服采样对照：CPU冻结产物

本目录用于准备两臂有限预算采样实验。没有训练、模型权重加载、API请求或部署；全部`training_enabled/training_eligible=false`。

- `pool-v1/train.json`：同一13,242条拟训练池，继承旧11,756和新1,486候选；旧数据与新补充原包不变。
- `pool-v1/manifest.json`、`blind-heldout.json`、`summary.json`：来源链、保留集盲筛与实际统计。新包`split=train`只是用途分区，不能绕过训练准入。
- `schedule-v1/uniform-plan.json`、`stratified-plan.json`：固定种子20261004、每臂400步×8条，完整ID顺序及前200步曝光。
- `schedule-v1/exposure-ledger.json`：每次曝光的行指纹、来源组、层、步数、microbatch与重复次数。
- `schedule-v1/token-lengths.json`：全池真实tokenizer长度，所有action及真实tool，非tool没有虚构的工具监督。
- `schedule-v1/summary.json`：每臂200/400步的任务数量、监督权重、非padding及实际microbatch补齐token预算。
- `schedule-v1/manifest.json`：源码、配置、池、tokenizer依赖和输出文件的字节指纹。默认校验不能替代实际分词重放。

全部派生产物不可直接编辑或覆盖。修改配额、种子、来源、标签、提示或分词器需要新版本并重新审核，不得删除历史后重用同版本名。

完整设计、局限和复现命令见[报告52](../../docs/52-金融客服分层采样对照与训练前冻结.md)。新的GPU执行器尚待实现，旧两轮训练命令不能加载本目录；本轮没有可供部署的新模型。
