# 许可与第三方来源

Copyright 2026 DrTonks and contributors.

本项目原创代码和文档采用 Apache License 2.0，完整条款见 [LICENSE](LICENSE)。由本项目另行发布并明确标注为 Apache-2.0 的 LoRA 适配器亦采用该许可；此声明不表示仓库已包含适配器权重。

基础模型、第三方数据、API 输出和依赖仍遵循各自许可证或服务条款，不因存放在本仓库而被重新授权为 Apache-2.0。公开数据的原文及其抽样、规范化、去重版本保留原许可与来源。API 输出的可用范围以服务条款为准，本项目不授予超出自身权利的许可。

- Qwen3-VL-2B-Instruct：[官方模型](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)、[官方 ModelScope](https://modelscope.cn/models/Qwen/Qwen3-VL-2B-Instruct)，Apache 2.0；文件 revision 和 SHA256 见 `configs/model_source.json`。
  本项目基于该模型进行文本决策 LoRA 微调，训练与评估过程见 `docs/06-扩大数据与联合训练.md` 和 `docs/09-效果与速度验证.md`。适配器是本项目的微调产物，不是 Qwen 官方发布的模型；使用时仍需加载基础模型。
- MASSIVE 1.1：Amazon Science，[官方仓库](https://github.com/alexa/massive)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。第一轮子集保留中文原文、意图和来源；第二轮由脚本重建，做了抽样、规范化和去重，预测及指标由本工程生成。
- CrossWOZ：清华 CoAI，[官方仓库和许可证](https://github.com/thu-coai/CrossWOZ)，Apache 2.0。第二至第四轮测试单领域子任务；第五轮另从官方 train 取领域训练样本、按对话划分官方 val，过滤并抽样，版本见 `data/crosswoz-training-source.json`。输入仅保留历史话语与当前问题，标注用于监督。不能与原任务榜单混淆。
- PyTorch、Transformers、PEFT、bitsandbytes 等依赖使用各自许可，没有复制到发布包。
- Jev：[API 文档](https://api.typesafe.ai/docs)、[服务协议](https://typesafe.ai/legal/mca)。输出与训练输入隔离，只用于采购选型评估，不用于训练、蒸馏或监督标签。
