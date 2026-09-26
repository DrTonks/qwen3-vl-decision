# 第三方来源

项目源码最终许可证由项目所有者确定。

- Qwen3-VL-2B-Instruct：[官方模型](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)、[官方 ModelScope](https://modelscope.cn/models/Qwen/Qwen3-VL-2B-Instruct)，Apache 2.0；文件 revision 和 SHA256 见 `configs/model_source.json`。
- MASSIVE 1.1：Amazon Science，[官方仓库](https://github.com/alexa/massive)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。第一轮子集保留中文原文、意图和来源；第二轮由脚本重建，做了抽样、规范化和去重，预测及指标由本工程生成。
- CrossWOZ：清华 CoAI，[官方仓库和许可证](https://github.com/thu-coai/CrossWOZ)，Apache 2.0。仅测试单领域子任务，不能与原任务榜单混淆。
- PyTorch、Transformers、PEFT、bitsandbytes 等依赖使用各自许可，没有复制到发布包。
- Jev：[API 文档](https://api.typesafe.ai/docs)、[服务协议](https://typesafe.ai/legal/mca)。输出与训练输入隔离，只用于采购选型评估，不用于训练、蒸馏或监督标签。