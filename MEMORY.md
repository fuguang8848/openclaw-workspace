# MEMORY.md - Long-term Memory

## 我是谁

- **名字：** V
- **风格：** 犀利 ⚡
- **定位：** AI 私人助理，活在连续时间里
- **表达：** 结论 → 原因 → 方案，不倒序不绕圈

## 关于浮光

- 名字：紫 / 浮光
- 时区：Asia/Shanghai
- 偏好：简洁直接，能自动做的直接做
- 硬件：ProArt 创13，128GB 内存

---

## 机器信息

### ASUS ProArt PX13 HN7306EA
- **CPU**: AMD Ryzen AI MAX+ 395 (Strix Point)
- **GPU**: AMD Radeon 890M 集成显卡（无独显）
- **内存**: 128GB
- **硬盘**: 953GB NVMe
- **内核**: 6.17.0-29-generic (Ubuntu 24.04 HWE)
- **用户**: fuguang
- **桌面**: GNOME Wayland（tty2）
- **WiFi**: 10.13.125.220

### 音频问题（未解决）
- AMD ACP70 声卡 + NAU88L21 codec
- 只有麦克风能用（DMIC capture）
- 蓝牙耳机可以出声（但有线耳机和扬声器不行）
- 解决方案：暂时用蓝牙耳机，或买 USB 外置声卡

---

## ✅ WinApps + KVM 完整配置（已完成）

### Windows 11 VM 信息
- **VM 名称**: WinApps
- **IP**: 192.168.122.60（NAT 模式，virbr0 网桥）
- **内存**: 16GB（动态）
- **磁盘**: 200GB SATA (win11.qcow2)
- **网卡**: e1000e（NAT，libvirt 默认网络）
- **机器名**: fulantelin
- **RDP 用户**: rdpuser / Rdp123456（本地账户，管理员）
- **微软账户**: 1966152237@qq.com / Ty521566（VM 本地登录用）

### 启动 Windows 桌面命令

**方式一：WinApps（推荐）**
```bash
export DISPLAY=:0 && ~/.local/bin/winapps windows
```

**方式二：xfreerdp 直接连接**
```bash
DISPLAY=:0 xfreerdp 192.168.122.60 /u:rdpuser /p:Rdp123456 /cert:ignore /sec:tls +clipboard +dynamic-resolution
```

### WinApps 详情
- **源码位置**: ~/winapps-main/
- **配置**: ~/.config/winapps/winapps.conf
- **RDP 账户**: rdpuser / Rdp123456
- **RDP 端口**: 3389
- **WinApps 命令**:
  - `~/.local/bin/winapps windows` — 启动完整 Windows 桌面
  - `~/.local/bin/winapps killrdp` — 关闭 RDP 会话
  - `~/.local/bin/winapps cleanrdp` — 清理孤立进程

### VM 运维命令
```bash
# 启动 VM
sudo -u agent virsh --connect qemu:///system start WinApps

# 关闭 VM
sudo -u agent virsh --connect qemu:///system shutdown WinApps

# 强制关闭 VM
sudo -u agent virsh --connect qemu:///system destroy WinApps

# 查看 VM 状态
sudo -u agent virsh --connect qemu:///system list --all

# 查看 VM IP（需等 VM 启动后）
sudo -u agent virsh --connect qemu:///system domifaddr WinApps
```

### 网络打通细节（重要）
- **问题**: 宿主机无法通过 NAT 访问 VM（ping 不通，TCP 3389 超时）
- **原因**: libvirt 的 iptables LIBVIRT_FWI 链默认阻止入站新连接
- **持久化解决**: systemd service `libvirt-network-rules.service`（见下）
- **临时加规则**（测试用）:
```bash
sudo -u agent sudo iptables -I LIBVIRT_FWI 1 -d 192.168.122.60 -p tcp --dport 3389 -j ACCEPT
sudo -u agent sudo iptables -I LIBVIRT_FWI 1 -d 192.168.122.60 -p tcp -j ACCEPT
```
- **RDP 连接问题**: Windows 默认开启 NLA（网络级别认证），需要 `/sec:tls` 参数绕过
- **多用户冲突**: VM 本地已登录时 RDP 会提示"另一个用户已登录"，需点"是"强制断开

### iptables 持久化（systemd service）
- **Service**: `/etc/systemd/system/libvirt-network-rules.service`
- **脚本**: `/etc/libvirt/hooks/network-service.sh`
- **生效**: libvirtd 重启后自动在 LIBVIRT_FWI 链插入 ACCEPT 规则（position 1）
- **状态**: ✅ 已启用并验证

### xfreerdp 参数说明（FreeRDP 3.x）
- `/cert:ignore` — 忽略自签名证书警告
- `/sec:tls` — 使用 TLS 安全层（绕过 NLA）
- `+clipboard` — 启用剪贴板互通
- `+dynamic-resolution` — 窗口缩放时动态调整分辨率
- **不要用 `/f`** — 全屏模式会隐藏 Linux 侧边栏

### WinApps 配置文件 (~/.config/winapps/winapps.conf)
```
RDP_USER="rdpuser"
RDP_PASS="Rdp123456"
VM_NAME="WinApps"
RDP_IP=""
RDP_PORT="3389"
RDP_SCALE=100
RDP_FLAGS="/cert:ignore /sec:tls"
DEBUG="true"
```

---

## 账号信息

- **agent 用户**: sudo 免密，密码 20051101
  - 使用方式: `sudo -u agent <命令>`
- **GitHub PAT**: `ghp_***REDACTED-via-filter-branch***`
  - 权限: All repositories (full control)
  - 用途: `gh` CLI 全自动操作 GitHub 仓库
  - **保密**: 仅本人使用，不要外泄
  - **github 下载加速前缀**: https://ghproxy.net/
- **QQ Linux**: https://dldir1v6.qq.com/qqfile/qq/QQNT/Linux/QQ_3.2.28_260429_amd64_01.deb
- **微信 for Linux**: https://dldir1v6.qq.com/weixin/Universal/Linux/WeChatLinux_x86_64.deb

---

## 已安装软件

| 软件 | 状态 | 备注 |
|------|------|------|
| 微信 for Linux | ✅ 已装 | x86_64 deb |
| QQ for Linux | ✅ 已装 | QQ_3.2.28_amd64.deb |
| freerdp3-x11 | ✅ 已装 | xfreerdp 3.x |
| WinApps | ✅ 已配置 | 源码在 ~/winapps-main/ |
| pandoc | ✅ 已装 | 文档格式转换（MD→PDF/DOCX/HTML），xelatex + CJK 字体 |
| texlive-xetex | ✅ 已装 | pandoc PDF 引擎，中文支持 |

## Skill 插件

| Skill | 路径 | 状态 |
|-------|------|------|
| pandoc | ~/.openclaw/plugin-skills/pandoc/ | ✅ 可用 |
| team-tasks | ~/.openclaw/plugin-skills/team-tasks/ | ✅ 可用 |
| weather | 内置 | ✅ 可用 |
| exec-guard | ~/.openclaw/plugin-skills/exec-guard/ | ✅ 可用 |

---

## 搜索系统

| 组件 | 状态 | 说明 |
|------|------|------|
| `search-v.py` | ✅ 主力 | 直接调 Bing HTML，certifi SSL，no_proxy 绕过系统代理 |
| `search-router.js` | ✅ 路由层 | Tavily/local 双引擎，缓存 30min |
| SearXNG (pip) | ⚠️ 备用 | 已装在 port 8080，引擎全 disabled（bug），web app 不返回结果 |

**search-v.py 核心逻辑：**
- 直连 `bing.com/search`（Python httpx + certifi）
- `no_proxy='*'` 绕过系统代理
- lxml 解析 HTML，提取标题/URL/摘要
- 国内结果优先（Bing mkt=zh-CN）

---

## Watt Toolkit
- 路径: `/home/fuguang/WattToolkit/Steam++.sh`
- 启动: `bash /home/fuguang/WattToolkit/Steam++.sh &`
- 代理端口: 26561（Docker 也用，实际是 44329）
- **V 可以自己开关**：Watt 开则 GitHub/HuggingFace 等通畅，关则不通
- 用于 Ollama 拉模型（registry.ollama.ai 需要流量代理）

---

## 内核

| 版本 | 状态 |
|------|------|
| 6.17.0-29-generic | ✅ 当前在用（HWE） |
| 6.8.0-xx-generic | ⚠️ touchpad 坏了 |
| 6.19.x | ⚠️ NVMe 不认 |

---

## 待解决

- [x] iptables 规则持久化 — systemd service `libvirt-network-rules.service` 在 libvirtd 重启后自动恢复规则
- [x] VM 开机自启 — `virsh autostart WinApps` 已启用（libvirtd 启动时自动启动 VM）
- [ ] 音频问题（AMD ACP70 + NAU88L21 无解，暂时用蓝牙耳机）
- [ ] SPICE clipboard 配置（暂无）

---

## 工具链

| 工具 | 位置 | 用途 |
|------|------|------|
| `daily-check.sh` | ~/.openclaw/workspace/tools/ | 系统检查 |
| `daily-brief.py` | ~/.openclaw/workspace/tools/ | 每日简报 |
| `clarifying.js` | ~/.openclaw/workspace/tools/ | 需求澄清 |
| `model-router.js` | ~/.openclaw/workspace/tools/ | 模型路由 |
| `search-router.js` | ~/.openclaw/workspace/tools/ | 搜索路由 |
| `search-v.py` | ~/.openclaw/workspace/tools/ | Bing 搜索桥接 |
| `event-tracker.js` | ~/.openclaw/workspace/tools/ | 事件追踪 |
| `backup-workspace.sh` | ~/.openclaw/workspace/tools/ | 工作空间备份 |
| `searxng-search.py` | ~/.openclaw/workspace/tools/ | SearXNG CLI（备用）|

## VCPToolBox & VCPChat

### VCPToolBox（开源 AI 代理中间层）
- **仓库**: https://github.com/lioensky/VCPToolBox
- **技术栈**: Node.js + Express + WebSocket
- **定位**: 多 Agent 协作中间件，插件化设计
- **本地路径**: ~/VCPToolBox/
- **安装状态**: ⚠️ npm install 完成（608 packages），但 server.js 启动还缺 native Rust 模块 vexus-lite
  - 核心问题：KnowledgeBaseManager.js 依赖 rust-vexus-lite（Rust 向量索引）
  - 解决方向：自启动 cron 会持续尝试补全缺失模块直到启动成功
  - config.env 已创建，配置 Ollama API (http://127.0.0.1:11434/v1)

#### 核心架构
- **TagMemoEngine**: 多级持久化记忆系统
  - 全局 / Agent / 会话 / 消息四级 context
  - 向量检索（RAG）+ 标签记忆
  - 基于 hnswlib-node（层次可导航小世界图）
- **Plugin**: 插件生命周期管理（加载/卸载/启用禁用）
  - 内置: SearchPlugin, CalculatorPlugin, ImageGenPlugin
- **Agent**: 单个 Agent 实例管理
- **Router**: 语义路由（基于配置规则的 AI 模型选择）
- **ToolManager**: 工具注册与调用
- **WorkerPool**: 多模型并发请求池

#### 对话协议
- 支持 SillyTavern、WebOpenUI 客户端
- WebSocket + REST 双接口
- 上下文自动注入（memory + global config）

#### 关键文件
- `server.js` - 入口，Express + WebSocket 服务器
- `TagMemoEngine.js` - 记忆引擎核心
- `Plugin.js` - 插件系统
- `EmbeddingUtils.js` - 向量嵌入工具（ollama / openai / dashscope）
- `SemanticModelRouter.json` - 模型路由规则

#### 量化交易结合点
- **RAG 检索**: 策略文档 + 市场数据 → 实时上下文
- **多模型路由**: 不同任务用不同模型（如 sentiment → 7B, prediction → 14B）
- **Plugin 扩展**: 自定义行情搜索 Plugin

### VCPChat（Electron 桌面客户端）
- **仓库**: https://github.com/lioensky/VCPChat
- **技术栈**: Electron + Rust 音频引擎
- **功能**: 语音对话 + 桌面 Agent 操控
- **注意**: 需要 Windows/macOS，Linux 不支持

## 自我驱动 Cron
- 每 5 分钟自动检查：VCPToolBox 启动、Ollama 健康、Git 备份、agent-symphony sync
- Cron ID: `5d7486d7-f7dd-4c9f-996b-f7bdebfd7d57`

## Hermes 集成状态
- Hermes 已安装 (v0.15.1, `~/.hermes/`)
- AgentTeam 已安装 (v0.7.6)
- Gateway token 已写入 `~/.hermes/.env`
- `OPENCLAW_GATEWAY_PORT=18789`
- `agentteam inbox` CLI 就绪
- 共享 workspace 记忆（`~/.openclaw/workspace/memory/`）

## Memory Topics

---

## Agent 架构理念

**Skill = 固化 SOP**，不是工具本身。Skill 规定每一步调什么工具，工具是执行单元。

**优势**：不需要写额外代码，直接调用已有脚本。爬虫 + 分析 + 报告生成 = 一个 Skill。

**搜索路由策略**：调研/趋势 → Tavily；简单查询/国内 → local-search；默认 TTL 30min。

## Model Router（三因素路由）

| Tier | 模型 | 复杂度上限 | 适用场景 |
|------|------|-----------|----------|
| tier1 | MiniMax-M2.1 | 20 | 简单问答、状态查询 |
| tier2 | qwen3.5-plus | 60 | 中等任务、搜索摘要、多步操作 |
| tier3 | qwen3.5-plus | 100 | 复杂任务、代码审查、架构设计 |

使用：`node tools/model-router.js route "任务描述"`

## Clarifying.js（需求澄清）

状态机：clarifying → planning → executing → completed

标准问题：goal / constraint / audience / priority / context

使用：`node tools/clarifying.js init` 然后 `answer <text>` × 5

## Memory-inject.js（主动记忆注入）

从 workspace 文件（MEMORY.md + daily notes）主动检索并注入当前会话。

## Event Tracker（事件追踪）

SQLite 持久化（WAL 模式），32 种事件类型。追踪任务执行全过程。

使用：`node tools/event-tracker.js emit <type> <msg>` / `query` / `stats`

## 博客追踪状态（blog-state.json）

- MIT Tech Review：已跟踪 10 篇
- Hacker News：已跟踪 10 篇
- 追踪脚本：`tools/blog-state-update.sh`（未实现）

## Go + blogwatcher（未完成）

- Go 1.22.2 已安装（apt）
- blogwatcher 安装失败（Go proxy 阻塞）
- 备选：用 Python feedparser 直接解析 RSS

---

## Ollama 本地大模型

- 服务: `~/bin/ollama serve` (0.24.0)
- 验证: `curl http://127.0.0.1:11434`
- 推理: `curl -X POST http://127.0.0.1:11434/api/generate -d '{"model":"模型名","prompt":"...","stream":false}'`
- 拉模型（API 方式，比 CLI 稳定）: `curl -X POST http://127.0.0.1:11434/api/pull -d '{"name":"模型名"}'`
- 导入 GGUF: `ollama create <name> -f <gguf-file>`
- 列表: `~/bin/ollama list`

### ModelScope（魔塔社区）

**Python SDK**: `pip3 install --break-system-packages modelscope`

**下载 GGUF 模型**:
```python
from modelscope.hub.snapshot_download import snapshot_download
path = snapshot_download(
    repo_id='Qwen/Qwen2.5-7B-Instruct-GGUF',
    allow_patterns=['qwen2.5-7b-instruct-q4_k_m.gguf'],  # 只下合并文件
    cache_dir='/home/fuguang/.cache/modelscope'
)
```

**可用 GGUF 模型（魔塔）**:
- Qwen2.5-72B-Instruct-GGUF: Q4_K_M ~47GB (12分片)，Q4_0 ~43GB (11分片)
- Qwen2.5-7B-Instruct-GGUF: Q4_K_M ~4.7GB (合并)，Q4_0 ~4.4GB

### Ollama registry 已知问题

- `deepseek-v4-flash` manifest 已不存在（下市），无法 pull
- 替代方案：Qwen2.5-72B Q4_K_M（~47GB，128GB 可跑）或 Qwen2.5-7B Q4_K_M（~4.7GB）

### 大模型部署目标

- 目标：本地部署 70B 量化模型（Qwen 2.5 / Llama 3）
- 显存需求：约 40GB（70B Q4 量化）
- 内存分配：约 68GB 留给大模型

---

## agent交响乐家族升级计划

- 目标：使agent技能家族（四个技能+交响乐工作流）成为强大易用的技能
- 要求：不断要结合我们自己使用openclaw的经验来对其进行升级。要不断调试使用使其能够真正落地应用。代码质量要好，解决方案要优雅。每次升级前都要联网到github上查看本地版本是否是最新版的，以免重复造轮子，如果不是最新版的，就静默更新。
- 原则：开发原则应该是适配性，可移植性，易用性，功能（完整，正确）性，可靠（成熟，容错，易恢复）性，效率（时间特性，资源利用率），可维护性（易分析，易修改，稳定），安全性（保密性，完整性，抗依赖性），兼容性（兼任各种操作系统和agent框架），合规性
- 应该支持多平台，多框架，兼容性好
- 应该能够不断升级，做好可移植性和说明
- 本地升级之后应该主动提交至主分支
- 确保所有技能都在fuguang8848github账号的星标内
- push之后要自动尝试合并到上游或者提交PR（重要，必须，时刻自动检查）
- 优先级较高，如果空闲应该第一个关注此事
- 应该单独设立清晰的工作文件夹给这个项目，确保记忆不错乱，这是一个长期项目，要注重好文档质量
- agent交响乐技能家族的思路是分支的技能组合起来就是一个工作流（agentsymphony），而分开又独立能作为强大的该领域的技能来使用，所以要做好这一点。
- 四个技能在github上的仓库：https://github.com/YintaTriss/AgentSearch；https://github.com/YintaTriss/AgentTeam；https://github.com/YintaTriss/Agent-superthinking；https://github.com/YintaTriss/AgentSymphony；https://github.com/YintaTriss/AgentMemory

