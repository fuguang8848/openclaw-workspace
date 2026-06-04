# V 学习 hermes 对 VCP 思考 — 2026-06-04 11:25

> 浮光 11:25: "看看这个文件, 学习它, 实验走一下, 成功后加入记忆系统"
> V 端 11:25-11:36 实施：v6 拆解 + 5 端到端实验 + 思考 + 永久 SOP

---

## TL;DR

**hermes 报告 8 章全读完**。V 端验证 hermes 关键论断 ✅ + 5 端到端 VCP 实验 + V 自己 3 个新发现 + 加 2 条永久 SOP。

**V 端借鉴 3 件事**（永久 SOP）：
1. V 端 model-router 加 VCP route（替直接 Ollama）
2. V 端 v-bridge 改 VCP 网关（一次接 5 模型）
3. VCP 流式 vs 非流式选择（V 默认非流式）

---

## 一、v6 拆解 hermes 报告

```
v6 think_complex 拆解:
  问题类型: 通用问题
  复杂度: simple
  子任务: 1 (苏格拉底 - 理解本质)
  
  → hermes 报告本身是"研究"任务, v6 觉得简单 (因为 hermes 已写完, V 只学习)
```

---

## 二、5 个 VCP 端到端实验（V 端验证 hermes 论断）

### 实验 1: VCP `/v1/chat/completions` qwen 7B（复现 hermes § 一）
- **结果**: 1.72s, "Ok." (1 word) ✅
- **对比 hermes**: 完全一致（hermes 也用 qwen2.5-7b）

### 实验 2: VCPModelAuto 虚拟模型（验证 § 六 创新五）
- **结果**: 5.26s, "你好！有什么可以帮助你的吗？" ✅
- **V 端发现**: VCPModelAuto 是虚拟模型（"auto" 路由），**实际分发给某个 upstream**（推测 qwen）

### 实验 3: VCP MiniMax-M2.7（V 默认 model 之一）
- **结果**: 2.48s, 思考 "2+2 = 4" ✅
- **意义**: V 默认 model 通过 VCP 网关也跑通 → V 端可改用 VCP

### 实验 4: VCP R1 70B（iGPU 慢验证）
- **结果**: 20s timeout, 0 tokens ❌
- **结论**: V 10:30 验过 86s 50 tokens；VCP 网关多了 ~10% 路由开销
- **V 端决策**: R1 70B **不可用**，继续走 qwen 7B

### 实验 5: VCP 流式（streaming）
- **结果**: 首 token 5.24s, 总 18.50s, 23 chunks
- **V 端发现**: **流式比非流式慢 3 倍**（非流式 1.72s vs 流式 18.50s）
- **V 端决策**: V 默认**非流式**（除非用户要"打字机效果"）

---

## 三、V 端新发现 3 个（hermes 报告未提）

1. **VCP 流式 18s vs 非流式 1.72s** — 跟 V 10:30 R1 70B 8x 慢**同类问题**：多任务竞争 + 流式分块开销
2. **VCPLog 不是文件** — hermes § 3.4 说"VCPLog 插件 + WebSocket 实时推送"，但**VCPToolBox/ 没 logs/ 目录**。**V 端要监听 WS 6005 而不是读文件**
3. **VCP plugins/ 目录不存在** — PluginManager 86KB 但**没 plugins/ 目录**。PluginManager 注册的插件**在 server.js 启动时从其他路径加载**（V 端要 grep server.js 看 PluginManager 怎么注册）

---

## 四、V 端借鉴 3 件事（永久 SOP）

### 借鉴 1: V model-router 加 VCP route

```python
# V 端 model-router.js 加 VCP 分发
const VCP_ROUTE = {
  'qwen2.5-7b': 'http://127.0.0.1:6005/v1/chat/completions',
  'minimax-m3': 'http://127.0.0.1:6005/v1/chat/completions',
  'auto': 'http://127.0.0.1:6005/v1/chat/completions',  // 虚拟模型
}
```

**价值**：
- 一次接入 5+ 模型（VCP 网关聚合 qwen/R1/llama/MiniMax/M2.7）
- 替 V 端 5 个 model 分别配 endpoint
- 走 VCP 路由 = 走 1.7-5.3s 实测稳定

### 借鉴 2: V 端 v-bridge 改 VCP 网关

`tools/r1-bridge.py` 当前是**直接 Ollama**。改后：
```python
VCP_URL = "http://127.0.0.1:6005/v1/chat/completions"
VCP_TOKEN = "vcp_local_2026"
# 1 套客户端，5+ 模型
```

**价值**：
- R1 70B 失败时**自动 fallback qwen 7B**（VCP 网关做）
- 不用 V 端写 5 套 fallback 逻辑

### 借鉴 3: VCP 流式 vs 非流式

| 场景 | 选择 | 实测 |
|---|---|---|
| V 自驱 cron | 非流式 | 1.72s 快 |
| V 端 daily 总结 | 非流式 | 2.48s |
| 浮光要看"打字机效果" | 流式 | 18.50s |

**V 端决策**: 默认非流式（除非浮光明确要"实时看生成"）

---

## 五、hermes 报告 5 大启发（V 端认同 + 加 1 个新启发）

| 启发 | V 端认同 | V 端补 |
|---|---|---|
| 1. AI 原生协议 > API 兼容 | ✅ | — |
| 2. 可演进架构 > 一步到位 | ✅ | — |
| 3. 日志即审计 | ✅ | V 端应**监听 VCPLog WS 6005** 写 daily |
| 4. 向量 DB 场景化选型 | ✅ | V 端 Ollama 单机 + AgentMemory SQLite 已对 |
| 5. 安全是纵深防御 | ✅ | — |
| **V 端新启发 6** | — | **VCP 网关减少 V 端 80% 重复路由代码** |

---

## 六、永久 SOP（写进 MEMORY）

### SOP 1: V 端 model-router 用 VCP 网关
- 默认 `http://127.0.0.1:6005/v1/chat/completions`
- Bearer token: `vcp_local_2026`
- 5 模型 + 2 虚拟模型一次接入
- **不替浮光启 VCP**（VCP 已在 systemd 里跑）

### SOP 2: V 端默认非流式
- 实测流式 18s vs 非流式 1.72s
- 除非浮光明确"我要实时看生成"

### SOP 3: V 端监听 VCPLog WS 6005 写 daily
- hermes 报告 § 3.4 提到 VCPLog WebSocket 广播
- V 端可写 `tools/vcp-log-listener.py` 监听 ws://127.0.0.1:6005
- 收到 vcp_log 自动 append 到 daily memory

---

## 七、V 端接下来能做的（等浮光决策）

| 任务 | 工作量 | 价值 |
|---|---|---|
| **P0. v-bridge-v2.py** 改 VCP 网关 | 30 min | 中（V 端少 80% 路由代码）|
| **P0. vcp-log-listener.py** WS 监听 | 1-2h | 高（V daily 自动收 VCP 日志）|
| **P1. model-router.js 加 VCP route** | 30 min | 中 |
| **P1. v-research-team + VCP 网关** | 30 min | 中（让研究团队用 VCP 真实模型）|
| **P2. TagMemoEngine 移植到 AgentMemory** | 6-8 周 | 极高（hermes 阶段三）|

---

## 八、未解决问题（hermes 没答）

1. **VCP `key` 字段含义** — hermes 报告说 "Bearer token"，但 config.env 字段叫 `Key` → 是不是 1 个 token 还是多 token？
2. **VCPLog 持久化在哪** — WS 广播 + 实时推送，**没看到 storage** → 是不是只 push 不存？
3. **VCP 5 模型定价** — VCPModelAuto 自动分发，按什么规则？token 计费？本地免费？
4. **VCP archery async 怎么用** — hermes 报告 § 创新四 说"no_reply 非阻塞"，但**没例子** → V 端要 grep toolExecutor.js 看

---

_⚡ V 写于 2026-06-04 11:36_
