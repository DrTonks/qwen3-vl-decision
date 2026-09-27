# 数据集和划分

训练输入由 `src/qwenlab/prepare_v2.py` 构造，不读取 Jev 输出。种子 20260926，数据 SHA256 见 `results/phase2/data-manifest.json`。不要修改已发布结果对应的数据；新规则使用新版本。

|来源|用途|规模|标签含义|
|---|---|---:|---|
|MASSIVE 1.1 zh-CN 官方 train|训练候选池|1,715|原始 60 类通用助手意图，每类最多 30 条|
|MASSIVE 官方 dev|开发 / 温度校准|273 / 313|去重后按类分开；开发最多 5 条/类，校准最多 6 条/类|
|MASSIVE 官方 test|全量意图测试|2,974|固定 60 候选，测试标签实际支持 59 类|
|CrossWOZ 官方 test|多轮领域迁移|200|酒店、餐馆、景点、地铁、出租，各 40 个单领域用户轮次|
|自建业务开发集|训练 / 开发|48 / 16|从第一轮 64 条开发数据中按场景组隔离|
|自建业务校准 / 测试|校准 / 回归|56 / 72|第一轮已有、未经人工复核；不是新盲测|

MASSIVE 去重规则：去标点空白后转小写。训练删除与 dev/test 重合的 505 条、内部重复 284 条；dev 删除与 test 重合的 51 条、内部重复 10 条。保留官方 test 原貌。只排除完全规范化重复，不能排除语义近似或预训练泄漏。1,715 条是训练候选池，实际抽样数见训练记录，不能声称完整训练了一轮。

CrossWOZ 原始 `dialog_act` 元组为 intent/domain/slot/value。只保留当前用户轮次恰有一个有效领域的样本，排除多领域和纯寒暄，每类确定性抽取 40 条。输入只有当前文本和前 6 轮文本，不含未来回复、goal、dialog_act 或 state 标注。这是领域分类子任务，**不是原始 CrossWOZ 联合语义理解或完整任务成功率**。统计区间按对话分组。

业务样本 `business_zh.jsonl` 有 192 条、48 组，每组 4 条变体。开发/校准/测试组互斥；第二轮从开发集每个路由留出一个组验证，剩余组训练。标签为 `synthetic_unreviewed`，不能直接用于生产验收。`business_review.csv` 提供双人复核栏位，标签修改后创建新版本。

原始下载在 `raw/`，重建数据在 `processed/`，均忽略。公开结果包含来源、划分脚本、哈希、预测及汇总。第一轮 117 条 MASSIVE 子集保留原文标签供历史复现。

- [Amazon Science MASSIVE](https://github.com/alexa/massive)，CC BY 4.0；FitzGerald 等，*MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages*。
- [CrossWOZ](https://github.com/thu-coai/CrossWOZ)，原仓库 Apache 2.0；Zhu 等，*CrossWOZ: A Large-Scale Chinese Cross-Domain Task-Oriented Dialogue Dataset*，TACL 2020。

下一阶段应按真实业务抽样覆盖省略、多轮改口、方言、多个诉求、界面与后台冲突、越权请求、截图和未知产品。先定标注政策，不能按模型错例反复修改最终验收集。

## 第五轮扩展

`curriculum_v5.py` 新增客服状态与多轮组合，4,904 条训练 / 146 个表达组，开发、校准、测试各 402 条 / 21 组，均未经人工复核。核心训练表达和安全回放只使用 v4 train；新留出问法共享政策生成器，因此不算独立真实验收。MASSIVE 保留 v4 的 10,725 条完整去重训练样本。

CrossWOZ 新取官方 train 3,000 轮，每对话最多 3 轮；val 按对话划分后开发/校准各取 150 轮。固定来源见 `crosswoz-training-source.json`，用 `python -m qwenlab.download_v5` 下载校验；不将已分析的 test 加入训练。公开详细清单在 `results/joint-v5/data-manifest.json`，方案见 [第五轮文档](../docs/10-第五轮训练与动作决策.md)。独立 500 条人工验收当前仅建立采集模板，尚未收集完成。
