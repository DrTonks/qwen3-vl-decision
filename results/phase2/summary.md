# 第二轮机器生成结果

准确率按成功请求计算；失败数见 metrics.json，accuracy_all_requests 将失败算错。
延迟为每条完整流程的热启动墙钟时间；API 含网络，本地不含模型加载。校准表复用原推理耗时，不是重新计时。

|运行|数据|任务|样本|准确率|宏 F1|P50 秒|P95 秒|
|---|---|---|---:|---:|---:|---:|---:|
|jev-v2|business-test|intent|72|93.06%|0.909|0.491|0.543|
|jev-v2|business-test|needs_human|72|98.61%|0.982|0.491|0.543|
|jev-v2|business-test|route|72|97.22%|0.971|0.491|0.543|
|jev-v2|business-test|tool|72|97.22%|0.945|0.491|0.543|
|jev-v2|crosswoz-test|intent|200|87.00%|0.870|0.493|0.558|
|jev-v2|massive-test|intent|2972|78.06%|0.781|0.492|0.559|
|qwen-bf16-v2|business-test|intent|72|59.72%|0.560|0.185|0.207|
|qwen-bf16-v2|business-test|needs_human|72|55.56%|0.556|0.185|0.207|
|qwen-bf16-v2|business-test|route|72|37.50%|0.294|0.185|0.207|
|qwen-bf16-v2|business-test|tool|72|70.83%|0.207|0.185|0.207|
|qwen-bf16-v2|crosswoz-test|intent|200|76.00%|0.750|0.050|0.069|
|qwen-bf16-v2|massive-test|intent|2974|58.64%|0.564|0.088|0.092|
|qwen-nf4-v2|business-test|intent|72|59.72%|0.598|0.223|0.327|
|qwen-nf4-v2|business-test|needs_human|72|51.39%|0.514|0.223|0.327|
|qwen-nf4-v2|business-test|route|72|43.06%|0.374|0.223|0.327|
|qwen-nf4-v2|business-test|tool|72|75.00%|0.531|0.223|0.327|
|qwen-nf4-v2|crosswoz-test|intent|200|59.00%|0.538|0.077|0.087|
|qwen-nf4-v2|massive-test|intent|2974|55.01%|0.538|0.104|0.109|
|qwen-qlora-v2|business-test|intent|72|66.67%|0.612|0.234|0.356|
|qwen-qlora-v2|business-test|needs_human|72|75.00%|0.729|0.234|0.356|
|qwen-qlora-v2|business-test|route|72|44.44%|0.423|0.234|0.356|
|qwen-qlora-v2|business-test|tool|72|75.00%|0.380|0.234|0.356|
|qwen-qlora-v2|crosswoz-test|intent|200|64.50%|0.591|0.080|0.091|
|qwen-qlora-v2|massive-test|intent|2974|65.47%|0.628|0.113|0.119|
|qwen-nf4-v2-calibrated|business-test|intent|72|59.72%|0.598|0.223|0.327|
|qwen-nf4-v2-calibrated|business-test|needs_human|72|51.39%|0.514|0.223|0.327|
|qwen-nf4-v2-calibrated|business-test|route|72|43.06%|0.374|0.223|0.327|
|qwen-nf4-v2-calibrated|business-test|tool|72|75.00%|0.531|0.223|0.327|
|qwen-nf4-v2-calibrated|massive-test|intent|2974|55.01%|0.538|0.104|0.109|
|qwen-qlora-v2-calibrated|business-test|intent|72|66.67%|0.612|0.234|0.356|
|qwen-qlora-v2-calibrated|business-test|needs_human|72|75.00%|0.729|0.234|0.356|
|qwen-qlora-v2-calibrated|business-test|route|72|44.44%|0.423|0.234|0.356|
|qwen-qlora-v2-calibrated|business-test|tool|72|75.00%|0.380|0.234|0.356|
|qwen-qlora-v2-calibrated|massive-test|intent|2974|65.47%|0.628|0.113|0.119|
