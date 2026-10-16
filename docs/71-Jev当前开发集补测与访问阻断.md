# 当前协议 Jev 补测：首请求 HTTP 451 停止

2026-10-16 16:52（北京时间）。用户授权补测当前 128 条开发集，以便 README 展示同一测试集的五行模型对比。**已完成配置与验证；首请求及用户授权的两次重试均收到 HTTP 451，尚未获得成绩。** 重试响应明确说明当前地区不可用。未自动重试、未提交或推送。

## 已准备的评测

- 固定 `data/financial-service-v2/development.json` 的 128 条开发样本，不读取校准或最终集。
- 政策与候选来自 `support-financial-v2`，与当前 Qwen 输入保持一致；标签、标注理由和预期工具不会进入请求。
- 串行判断 action，只有预测为 tool 时才发出 tool 请求；最多 256 次，固定报告输入 token 上限 500,000，每次发送前检查累计用量。这个上限不是供应商侧精确金额封顶。
- 本次测原始决策组件，未登录或工具不可用不由后端预先改答案；保留模型错误供指标判断。
- 首次返回后固定供应商实际版本，后续版本漂移即停止。请求耗时包含网络，不含业务后端和回答生成。
- 请求发送前持久化 pending，成功保存响应和指纹；pending、失败或结果不确定均禁止自动重试。

5 项 CPU 测试通过：输入与候选对齐、标签隔离、版本与响应校验、缓存防重试、拒绝非开发分区。原有 Jev 缓存和模型实验未修改。

## 实际执行结果

| 项目 | 结果 |
|---|---|
| 尝试请求 | 共 3 次：第一条样本的原请求＋两次用户授权重试 |
| HTTP 状态 | 451 |
| 有效响应 / 完成样本 | 0 / 0 |
| 自动重试 | 0 |
| 供应商实际模型版本 | 未取得 |
| token 用量 / 计费 | 未取得，不宣称零费用 |
| 模型准确率 / 有效请求延迟 | 无，不把失败请求耗时当推理性能 |

首次请求只有状态码，未保留错误正文。用户明确要求“重新尝试”后，于 2026-10-16 16:55（北京时间）进行一次授权重试；接口再次返回 HTTP 451，正文为：

```json
{"title":"Typesafe is not available in your region.","status":451}
```

这明确指向供应商的地区可用性限制，不是模型推理错误。已停止后续请求，没有修改地区、代理或身份信息尝试绕过限制。README 保留旧 384 条 Jev 历史结果，当前 128 条仍标“未测”，不能代填旧分数。

## 证据与复现

- [固定协议](evidence/financial-jev-current-v1/protocol.json)
- [首次失败记录](evidence/financial-jev-current-v1/failure.json)
- [用户授权重试及地区限制响应](evidence/financial-jev-current-v1/authorized-retry-1.json)
- [CPU 验证](evidence/financial-jev-current-v1/cpu-verification.json)
- [执行代码](../src/qwenlab/financial_jev_current.py)

```powershell
# 查看状态，不调用 API
.\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_jev_current progress
# 验证本轮输入和冻结配置，不调用 API
.\.venv-qwen35\Scripts\python.exe -m qwenlab.financial_jev_current prepare
```

原始请求账本在忽略目录 `results/financial-jev-current-v1/requests/`，三次尝试和授权记录另保存在 `results/financial-jev-current-v1/authorized-retries/`。当前直接运行 run 会因失败缓存停止，不会重发。地区可用性限制未解决前不继续重复请求；应向供应商确认官方支持的使用条件，或评估其他可用服务。后续如获得合法可用的服务，再明确安排新的恢复尝试；保留全部历史记录。只有获得完整结果后才重算指标并替换首页对比表。

## 第三次请求

用户明确回复“允许”后，于 2026-10-16 16:59:38（北京时间）执行第三次单条请求，仍收到 HTTP 451：`Typesafe is not available in your region.` 已按约定停止；累计 3 次尝试、0 条有效预测、0 次自动重试。[第三次请求记录](evidence/financial-jev-current-v1/authorized-retry-2.json)。本轮未继续发送其他开发样本，未提交或推送。

## 历史请求链路与本地 7890 核对

用户提出代理可能性后，只读检查确认：

- 2026-10-02 成功完成 1,152 次请求的执行器使用 `urllib.request.ProxyHandler({})`，源码归一化 SHA256 与当时冻结协议一致。
- 当前执行器和两次重试脚本同样显式禁用应用层 HTTP/HTTPS 代理；不会读取系统代理或 HTTP_PROXY/HTTPS_PROXY 来连接 7890。
- 本机 `127.0.0.1:7890` 可建立 TCP 连接，但本轮没有验证它的代理协议或公网出口，也没有通过它请求 Jev。
- 历史与当前 API 域名/路径相同；旧基准将动作和工具作为并行问题发送，当前先动作后按需工具。该调用差异不能解释地区限制响应。

结论：当前请求确实没有显式走 7890，但历史成功请求也如此，不能直接断言“新代码漏配代理”就是原因。应用直连仍可能被系统 TUN/VPN 路由接管；历史未记录出口 IP，无法还原当时出口或确定供应商访问策略是否变化。供应商已明确返回地区不可用，应核实其官方支持的使用条件；本次没有切换代理绕过该限制。

[只读链路核验证据](evidence/financial-jev-current-v1/network-path-review.json)。本轮新增模型请求为 0。
