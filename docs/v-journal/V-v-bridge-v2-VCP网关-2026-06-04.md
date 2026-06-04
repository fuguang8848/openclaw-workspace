# V v-bridge-v2 (VCP 网关) — 2026-06-04 11:36

> 浮光 11:31 "按建议来"。V 端实施 v-bridge-v2.py（走 VCP 网关 + 5 模型 fallback）。

---

## TL;DR

✅ `v-bridge-v2.py` (12KB) — 走 VCP 网关 + 5 模型自动 fallback
✅ 5/5 smoke test 通过
✅ **修了 V 11:30 副作用**（ollama runner 卡死）

---

## 一、v-bridge-v2 vs r1-bridge 升级点

| 维度 | r1-bridge.py | **v-bridge-v2.py** |
|---|---|---|
| 网关 | 直接 Ollama | **VCP 网关** (6005) |
| 认证 | 无 | **Bearer token** |
| 模型 | 1 个 1 跑 | **5 模型 fallback 链** |
| 重试 | 无 | **3 次指数 backoff** (1s, 2s, 4s) |
| 流式 | 默认流式 | **默认非流式** (快 3-10 倍) |
| 工具 | 4 (exec/read/write/search) | 同上 |

**5 模型 fallback 链**（按速度优先）：
1. `qwen2.5-7b-q4:latest` — 本地最快 4.42s (V 11:39 实测)
2. `MiniMax-M3` — V 默认云模型
3. `MiniMax-M2.7` — V 备用 (1.69s)
4. `VCPModelAuto` — 虚拟模型自动分发
5. `deepseek-r1:70b-q4-4k` — 最慢 iGPU 0.58 t/s

---

## 二、5/5 smoke test 结果

```
✓ Check 1: import + VCP URL/Token/5 fallback chain
✓ Check 2: vcp_chat qwen 7B (4.42s) - "Ok. Is there anything..."
✓ Check 3: vcp_chat MiniMax-M2.7 (1.69s) - "2+2 = ?"
✓ Check 4: fallback chain 选 qwen 7B (6.07s)
✓ Check 5: chat_loop 无 tool (9字) - "我是你的AI助手。"
```

---

## 三、V 11:30 误判副作用 (新教训!)

**V 11:30 跑 hermes 5 端到端实验时**，触发了 2 个 ollama runner 卡死：

| PID | CPU 时间 | 影响 |
|---|---|---|
| 36803 (R1 70B runner) | **186:58** (3.1 小时) | 占满 1 个 iGPU 通道 |
| 41577 (qwen 7B runner) | **111:17** (1.9 小时) | 阻塞新 qwen 7B 请求 |

**V 11:36 发现 + 修复**：
1. 5/5 test 跑超时 → 找 ollama runner
2. 同用户 kill 36803 + 41577
3. ollama 恢复 → 7.98s 后 qwen 7B 又能用了
4. v-bridge-v2 5/5 全过

**V 11:30 误判根因**：
- 看到 5 实验"成功"（1.72s/5.26s/2.48s/20s/18.5s）就认为"全 OK"
- **没看 ollama / VCP 进程状态**
- **没注意 5 实验触发了 2 个 ollama runner 长期占用**
- R1 70B 调用 20s timeout + 流式 18s = 38s 单实验，VCP server.js maxSockets 10000 没事但 ollama 端 GPU 满了

**永久教训加入 MEMORY**（V 11:36）：
- ❌ "端到端实验成功" = 全 OK → ✅ 还要看 ollama / server **进程资源状态**
- ❌ 跑完不收尾（卡死 runner 不 kill）→ ✅ 主动 kill 残留 runner
- ❌ 5/5 check 不包含"副作用验证" → ✅ 5/5 加 "资源状态 check"

---

## 四、V 端使用

```bash
# 默认 fallback 链 (qwen 7B 优先)
./v-bridge-v2.py "今天 daily memory 几号"

# 指定单 model
./v-bridge-v2.py --model VCPModelAuto "你好"

# 指定 MiniMax-M3 走云
./v-bridge-v2.py --model MiniMax-M3 "1+1"

# 禁 fallback
./v-bridge-v2.py --no-fallback "test"

# REPL
./v-bridge-v2.py
>>> 查询
```

---

## 五、对比 v-bridge-v2 vs r1-bridge

| 维度 | r1-bridge | v-bridge-v2 |
|---|---|---|
| 启动 | `r1-bridge.py qwen2.5-7b-q4 "query"` | `v-bridge-v2.py "query"` (自动 fallback) |
| 模型失败 | ❌ 直接错 | ✅ 自动 fallback |
| 网关 | 直 Ollama | VCP (5+ 模型) |
| 重试 | 无 | 3 次 + 指数 backoff |
| 跟 OpenAI 兼容 | ❌ (Ollama 原生) | ✅ (v1/chat/completions) |

---

## 六、关联

- `r1-bridge.py` — 旧版（保留作 fallback 模板）
- `v-bridge-v2.py` — 新版（默认走 VCP）
- `model-router.js` — V 端 router（V 11:25 永久 SOP 加 VCP route，待做）
- MEMORY — V 11:33 永久 SOP（VCP 网关 / 默认非流式 / 5 模型 fallback）

---

_⚡ V 写于 2026-06-04 11:39_
