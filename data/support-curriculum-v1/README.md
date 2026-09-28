# 客服专项数据 v1

**全部由AI生成，不要求组员试玩或人工标注。仅用于离线实验，尚未训练新模型。**

先读 [专项数据构建说明](../../docs/18-客服专项数据构建与下一轮实验.md)；浏览 [60张场景卡](场景卡.md)。

## 数量与边界

- 主集600条输入：60张卡、30个场景族、300个起草位置，规范化后272种不同消息。
- 每个问法带原始上下文和一组无关前置历史；标点、指代对照和历史变体不是独立用户。
- 原始划分：训练360、开发120、校准120；按完整场景族隔离。
- 过滤后的四路由监督候选：训练298、开发120、校准110。正确人工守卫样本保留，但记录 `runtime_path=guard`。
- 另写90条/18组挑战样本，只评测；当前四路由模型候选79条。其余仍留在完整业务组件挑战中，不能静默去掉难题。
- 这是起步种子数据，尚未达到可直接证明大规模训练有效的规模或独立性。

## 文件说明

`cases.jsonl` 保留全部主集AI标签；三个 `*-cases.jsonl` 是原始池；三个 `*-candidates.jsonl` 是可表达且通过重复检查的监督候选。`challenge-cases.jsonl`、`challenge-model-candidates.jsonl` 均不得进入训练、模型选择或温度拟合。

`eligibility.jsonl` 逐条记录暂缓原因；`runtime-inputs.jsonl` 是真实后端规范化输入及强制建议标签映射，**不是模型预测**。数据只模拟决策上下文，不访问数据库或调用真实工具。

`review.csv` 仅供查看，不是必填流程。旧通用CSV导入器不保留本轮split/扩增元数据，不能据其输出直接训练；应修改来源代码并生成新目录。

数据构造来源：

- `src/qwenlab/support_scenario_catalog.py`：主集场景和问法。
- `src/qwenlab/support_challenge_catalog.py`：单独起草的挑战集。
- `src/qwenlab/support_curriculum.py`：分组隔离、生产适配检查、旧集去重、覆盖检查和版本冻结。

## 校验与重建

在实验仓库根目录：

```powershell
.\.venv\Scripts\python.exe -m qwenlab.support_curriculum check --output data/support-curriculum-v1
.\.venv\Scripts\python.exe -m qwenlab.support_curriculum check --output data/support-curriculum-v1 --project ../uestc_Integrated_Design
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_support_curriculum.py
```

修改来源后生成新版本，不覆盖已冻结文件：

```powershell
.\.venv\Scripts\python.exe -m qwenlab.support_curriculum build --project ../uestc_Integrated_Design --output data/support-curriculum-v2
```

构建依赖相邻后端的Node依赖、旧139条和已准备好的第五轮402条测试原文。缺失时失败，不跳过重复检查。哈希明确按CRLF转LF后计算；该规则仅适用于本版本，不修改历史报告的字节哈希定义。

## 不能据此宣称什么

没有人工金标、线上流量、实际转人工或回复质量验收；同一AI作者和业务政策可能带来共享偏差。字段检查和另一个agent审查不等于真实用户测试。未拟合校准温度，未得出新模型准确率或速度结论。

已知工程问题仍保留：否定人工/否定代扣可能被规则误判，较自然的结束表达尚未覆盖。它们不会被错误标注来迁就代码。后续训练只能改善模型路径，不能直接修复这些守卫与协议问题。
