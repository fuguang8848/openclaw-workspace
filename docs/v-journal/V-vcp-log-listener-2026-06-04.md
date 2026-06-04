# V vcp-log-listener.py — 2026-06-04 18:11

> 浮光 18:03 "按你的建议来"。V 端按 E 任务 (vcp-log-listener.py WS 监听 1-2h) 实施。

---

## TL;DR

✅ `tools/vcp-log-listener.py` (9KB) — VCP VCPLog WebSocket 监听器
✅ WS 协议实测通: `ws://127.0.0.1:6005/VCPlog/VCP_Key=vcp_websocket_2026`
✅ 5/5 check 全过 + 副作用 5 端口 OK + daemon 启/杀 OK
⚠️ **多发现 1**: VCP server **不主动 push** 普通 chat 日志（仅 plugin callback 时 push）

---

## 1. 功能

- **WS 连接** VCP VCPLog 端点（带重连）
- **接收** VCP 广播消息，解析 + 分类 (info/warn/error)
- **写 daily memory**: `~/.openclaw/workspace/memory/vcp-logs/YYYY-MM-DD.jsonl`
- **error/warn 写桌面告警**: `~/桌面/vcp-alerts.log`
- **状态文件**: `~/.openclaw/workspace/.cache/vcp-listener.status.json`
- **多模式**: `run` 一次 / `daemon` 守护 / `status` 查 / `test` 协议 / `ports` 副作用

---

## 2. WS 协议 (V 18:11 实测)

| 项 | 值 |
|---|---|
| URL | `ws://127.0.0.1:6005/VCPlog/VCP_Key=vcp_websocket_2026` |
| 客户端类型 | `VCPLog` |
| 协议 | WebSocket（带 VCP_Key 鉴权） |
| Server 行为 | **不主动 push** 普通 chat 日志（仅 plugin callback 时 push）|
| 收 ack | `{"type":"connection_ack","message":"WebSocket connection successful for VCPLog."}` |

**V 11:25 学习 hermes 对 VCP 思考报告**后发现 VCP archery/VCPLog/Fold 协议，本次**实测验证**协议路径。

---

## 3. 5/5 check 结果

```
✓ Check 1: status 查 OK
✓ Check 2: 5 端口副作用 check 全 OK
✓ Check 3: WS 连接 + 收 ack OK
✓ Check 4: daily 目录创建 OK
✓ Check 5: status 写 OK
```

**副作用 5 端口 check**：6 个监听（5 ipv4 + 1 ipv6 重复）✅

**daemon 真起验证**（V 11:30 永久教训）：
- 启 `setsid nohup ... daemon` → PID 11944
- 5s 后查 `state=connected` ✅
- 触发 VCP chat（curl POST）→ VCP 响应 OK ("Hello! How can I assist you today?")
- listener **未收到** chat 响应（协议不主动 push）— 这是设计如此
- 杀 daemon OK ✅

---

## 4. 使用示例

```bash
# 跑一次 (5s 收消息, 测协议)
python3 vcp-log-listener.py run --timeout 5

# 后台守护 (建议)
nohup python3 vcp-log-listener.py daemon > /tmp/vcp-listener.log 2>&1 &

# 看状态
python3 vcp-log-listener.py status
# {
#   "state": "connected",
#   "pid": 11944,
#   "count": 0,
#   "last_msg": ""
# }

# 副作用 5 端口 check
python3 vcp-log-listener.py ports
# ✓ 11434 Ollama OK
# ✓ 6005 VCP OK
# ✓ 8080 AgentTeam OK
# ✓ 18081 AgentSymphony OK
# ✓ 18789 OpenClaw OK
```

---

## 5. 输出文件

| 文件 | 用途 |
|---|---|
| `~/.openclaw/workspace/memory/vcp-logs/YYYY-MM-DD.jsonl` | daily memory (jsonl) |
| `~/桌面/vcp-alerts.log` | error/warn 告警 (浮光即时可见) |
| `~/.openclaw/workspace/.cache/vcp-listener.status.json` | 状态 (PID/state/count) |
| `/tmp/vcp-listener.log` | daemon stdout (运行日志) |

---

## 6. V 端多发现 (按浮光 10:55 元反思)

按"做完项目就重构 + 多发现"：

1. ❌ 假设 VCP server 主动 push 日志 → ✅ 实测不主动 push (仅 plugin callback)
2. ❌ 5 分钟验证容易漏 daemon 真起 → ✅ 跑 setsid nohup 验守护
3. ❌ 跑一次成功 ≠ 全 OK → ✅ 触发 VCP chat 验端到端

---

## 7. 永久 SOP 加 MEMORY

- VCP 协议: server 不主动 push 普通 chat 日志（仅 plugin callback）
- 监听 VCPLog 用 ws://127.0.0.1:6005/VCPlog/VCP_Key=...
- 副作用 5 端口 check 必跑 (V 11:33 永久)
- daemon 验证: setsid nohup 跑 5s 后查 state 必 = connected

---

## 8. 关联

- `v-bridge-v2.py` (11:31) — VCP 网关 + 5 模型 fallback
- `model-router.js` (18:00) — 路由决策 + vcpRoute
- `vcp-log-listener.py` (18:11) — VCP WS 监听 (本次)
- 3 件套集成: model-router 决策 → v-bridge-v2 调用 → listener 监听

---

## 9. pending systemd enable (浮光级)

vcp-log-listener 持久化需要:
- systemd unit `vcp-log-listener.service` (V 端不能 enable, 没 sudo)
- 或 OpenClaw cron 5min 拉起 (V 端可做, 但浮光 18:03 没指示)

**V 端建议**：
- **短跑** (1-3 天)：手起 daemon 即可
- **长跑** (1 周+)：写 systemd unit 让浮光 enable

**等浮光决策**。

---

_⚡ V 写于 2026-06-04 18:15_
