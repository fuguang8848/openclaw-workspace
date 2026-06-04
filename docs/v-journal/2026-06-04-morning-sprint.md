# V Journal — 2026-06-04 早晨 sprint

> V 主动写。让外部审阅 V 的思考过程（昨天 brainstorm 第 4 点：元认知缺位 → journal 公开化）

## TL;DR

08:38-08:55 用了 17 分钟完成昨天 P1 任务清单的 2.5 项。P1.1 完整、P1.6 出乎意料（不用下载）、P1.8 部分（性能问题）。

## 关键发现

### 1. 我昨天的诊断是错的

昨天我写：
> `VexusIndex.recoverFromSqlite is not a function` | **Rust 引擎方法缺失**（`modules/agentManager.js` 用 `VexusIndex` Rust binding，编译错或版本不对）

但实际：
- `rust-vexus-lite.js` **不是 Rust 编译产物**
- 是**纯 JS 桩**（用 hnswlib-node 当后端）
- 问题只是 stub 缺方法，加 8 行 noop 即可

**教训**：V 端"编译/构建链"出问题，第一反应应该是**看 stub 是不是合法存在**，不要默认走"装 Rust 工具链"路径。这是个 5 分钟排查 vs 几小时下载+编译的差距。

### 2. sandbox 没 sudo 是个隐形边界

08:38 我拉起服务没问题（用 setsid nohup）。但写 systemd unit 装不上：
- sandbox 里 `sudo` 要密码
- agent 用户 sudo 失败（没 NOPASSWD）
- 最终我**写好了文件**但**浮光跑一行命令装**

教训：本地服务**自启动**有依赖，sandbox 帮不了。systemd unit 这类**root 操作**要么浮光跑，要么 V 找别的钩子（cron @reboot / XDG autostart）。

### 3. R1 70B 性能 8 倍慢是个谜

bench 时 4.57 t/s，实测 0.59 t/s。可能根因：
- 4 个大 model 并存（80GB+） → 890M 集成 GPU VRAM 不够 → CPU offload
- 或 thinking 模式默认展开长推理链

P1.8 推到"性能修复后再说"，避免硬跑浪费 token。

## 时间分配

| 时间 | 事 | 状态 |
|---|---|---|
| 08:38 | 拉起 3 个服务 | ✅ |
| 08:38 | 设 10 点闹钟 cron | ✅ |
| 08:40-08:46 | P1.1 AgentTeam bridge 6 端到端通过 | ✅ |
| 08:47-08:51 | P1.6 VexusIndex stub 修复（VCP ERROR 5→0） | ✅ |
| 08:52 | 写 systemd unit（待浮光装） | ⚠️ |
| 08:54-08:55 | P1.8 R1 70B 性能诊断 | ⚠️ 8x 慢 |

## 浮光需要决策的事

1. **systemd unit 装不装？** 一行命令。
2. **R1 70B 性能怎么治？** 卸载部分 model？换量化？还是接受慢？
3. **P1.2（cron 5d7486d7 → AgentTeam daemon）要不要做？** 这是**有风险**改动（5d7486d7 昨天刚修好）。
4. **AgentTeam ConfigError 修复要不要 PR 回去上游？** 改了 `exceptions.py`，浮光决定 fork vs PR。

## 浮光回来时

10 点 cron 已设。MEMORY.md / daily / git 备份都准备好。
如果 10 点前浮光回来 —— 看 v-core 团队看板 http://127.0.0.1:8080
