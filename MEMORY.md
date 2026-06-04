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
- **GitHub PAT**: `ghp_ei…r7jz` *(完整 token 仅在本地 `~/.openclaw/.secrets/github.pat` 备份，MEMORY 不存明文)*
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
- 替代方案：DeepSeek R1-Distill 系列（推荐）或 Qwen2.5-7B Q4_K_M（~4.7GB）

### 已验证可用的本地模型

| 模型 | 大小 | 量化 | 状态 | 备注 |
|------|------|------|------|------|
| qwen2.5-7b-q4 | ~4.7GB | Q4_K_M | ✅ 可用 | ModelScope下载，Ollama导入，CPU推理~4.6s/token |
| llama3.2:1b | ~1.3GB | - | ✅ 可用 | Ollama官方registry拉取 |
| deepseek-r1:14b | ~9GB | Q4_K_M | 待拉取 | 推理能力强，推荐 |
| deepseek-r1:7b | ~4.7GB | Q4_K_M | 待拉取 | 最轻量R1 |

### DeepSeek R1-Distill 系列（推理能力强）

- R1-Distill-Qwen-7B: 4.7GB Q4，最轻量
- R1-Distill-Qwen-14B: 9GB Q4，推荐
- R1-Distill-Llama-14B: 9GB Q4，推荐
- R1-Distill-Llama-70B: ~70GB Q4，128GB可跑但慢

拉取命令：`curl -X POST http://127.0.0.1:11434/api/pull -d '{"name":"deepseek-r1:14b"}'`

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
- 五个仓库在github：AgentSearch、AgentTeam、Agent-superthinking、AgentSymphony、AgentMemory（均为 YintaTriss/fuguang8848）
- **2026-06-01 同步状态**：AgentSymphony ✅、AgentTeam ✅、AgentSearch ✅ 已与上游同步；Agent-superthinking 和 AgentMemory 各有 1 个本地 commit 已推送并提 PR（PR#2）


---

## 2026-05-31 凌晨补充

### DeepSeek R1-Distill-Llama-70B 已下载 ✅
- 路径: `~/.cache/modelscope/hub/models/deepseek-ai/DeepSeek-R1-Distill-Llama-70B/`
- 132GB BF16 safetensors（17分片）
- 下一步: llama.cpp 转换 + Q4_K_M 量化 → import Ollama

### VCPToolBox 实际状态（2026-05-30）
- 服务跑在 6005 端口 ✅
- routes/chat.js 缺失（GitHub 404）⚠️
- config.env 已配置 Ollama API
- 启动: cd ~/VCPToolBox && node server.js

### Hermes
- Dashboard: `hermes dashboard`（端口 9119）
- agentteam inbox CLI 就绪

### Watt Toolkit
- 路径: `/home/fuguang/WattToolkit/Steam++.sh`
- bash /home/fuguang/WattToolkit/Steam++.sh &

### 关键教训
- npm registry 极慢但最终能通（79秒/包）
- gateway 重启 kill exec，长任务用 sessions_spawn
- workspace 备份被分支保护阻止

---

## NLLB-200 东乡语翻译训练项目

### 项目背景
- **目标**：用亲缘语言迁移（蒙古语→东乡语）训练 NLLB-200 模型
- **技术路线**：蒙古语（khk_Cyrl）作为源语言代理，蒙古语族亲缘关系做迁移
- **资料包来源**：楚灵整理，`~/下载/石榴籽项目NLLB训练资料包.zip`

### 项目工作区
- **路径**: `~/nllb-project/`
- **语料**: 
  - 蒙古语: `data/train_mongolian.jsonl`（105万条）✅
  - 东乡语: `data/train_train_dongxiang.jsonl`（9311条）+ `val_train_dongxiang.jsonl`（1034条）✅
- **脚本**: `scripts/`
  - `preprocess_mongolian.py` — 蒙古语语料预处理 ✅
  - `preprocess_dongxiang.py` — 东乡语语料预处理 ✅
  - `train_stage1_mongolian.py` — 第一阶段：蒙古语预训练
  - `train_stage2_dongxiang.py` — 第二阶段：东乡语微调
  - `evaluate.py` — 评估脚本

### NLLB 模型
- **模型**: facebook/nllb-200-distilled-600M（615M参数）
- **缓存路径**: `~/.cache/huggingface/hub/models--facebook--nllb-200-distilled-600M/snapshots/f8d333a098d19b4fd9a8b18f94170487ad3f821d/`
- **状态**: ✅ 已下载（约 2.3GB）

### PyTorch ROCm 环境
- **torch**: `2.5.1+rocm6.2` ✅ GPU 驱动正常
- **GPU**: AMD Radeon 8060S（gfx1151），128GB 统一内存
- **ROCm**: 6.2.2（系统默认）+ 7.2.4（已安装）
- **关键环境变量**: 
  ```
  LD_LIBRARY_PATH=/opt/rocm-6.2.2/lib:/opt/rocm-6.2.2/lib/llvm/lib:$LD_LIBRARY_PATH
  HSA_OVERRIDE_GFX_VERSION=11.5.1
  ```
- **验证命令**: `LD_LIBRARY_PATH=/opt/rocm-6.2.2/lib:/opt/rocm-6.2.2/lib/llvm/lib:$LD_LIBRARY_PATH HSA_OVERRIDE_GFX_VERSION=11.5.1 python3 -c "import torch; print(torch.cuda.is_available())"`

### ⚠️ 待解决
- **GPU 推理 segfault**: `model.generate()` 在 GPU 上 segfault，需进一步调试 ROCm 版本兼容性
- **训练尚未开始**: 预处理完成，GPU 环境就绪但推理 segfault 待修复

### 踩坑记录摘要（详见资料包 docs/踩坑记录.md）
- ❌ 不用 `eng_Latn`（土耳其语代理，不是英文）
- ❌ 不用 `add_tokens()`（不重建 SentencePiece，新增字符仍被拆分）
- ❌ NumPy 必须 < 2.0（2.x 与 PyTorch 2.1 不兼容）
- ❌ HF_ENDPOINT 必须在 Python 启动前 export

### 下载协作规则（2026-06-01 确立）
- **大型下载都让浮光来下**：本机下载不稳定（代理延迟、githHub 不通、各种问题）
- **V 不自己抢着下**：除非是小文件或快速测试，否则直接问浮光
- **完整 PyTorch v2.5.1 源码（含 submodule）**：`~/下载/pytorch-v2.5.1.tar.gz`（286MB，92956 文件）由浮光下
- **之前问题回顾**：
  - `git clone --recurse-submodules` 在 ghproxy 下会卡死（71 个 submodule 一个一个拉）
  - 代理 `ghproxy.cxkpro.top` 不支持 codeload 下载 tarball（返回 HTML）
  - ghproxy.net 速度慢且不稳定
  - 解决办法：让浮光下，V 负责解压、编译、验证

---

## 🌱 V 春季大扫除（2026-06-03）

**触发**：浮光"启动超级大脑，全面思考改进点"。V 主动做 3 件事 + 写 1 篇 V journal。

### 主动改进

1. **workspace 卫生**：17 个 ROCm `.deb` 挪到 `~/下载/roc-debs/`（腾出 2.5GB）；bench 脚本归档 `tools/bench/`；vm.png 删；install_helper.py → `archive/`；3 个 `/tmp` 临时 bench 脚本 → `archive/`
2. **Watt 启动/状态脚本**：
   - `tools/watt-start.sh`（2.0KB）—— 一键 GUI 启，自动找 `/run/user/1000/.mutter-Xwaylandauth.*` XAUTHORITY（GNOME Wayland X11 兼容坑）
   - `tools/watt-status.sh`（1.3KB）—— 4 态机：`DOWN(1) / ZOMBIE(2) / BOOTING(3) / OK(0)`
   - 关键：Watt 走 Avalonia X11，必须给 XAUTHORITY（仅 `DISPLAY=:0` 抛 `XOpenDisplay failed`）
3. **V journal 目录**：`docs/v-journal/` 建立，首篇 `2026-06-03-spring-cleanup.md` 推到 `fuguang8848/Agent-superthinking`（YintaTriss 上游 403，浮光 fork 路径）

### Watt 状态机（重要）

| 状态 | 退出码 | 含义 | 处理 |
|------|------|------|------|
| OK | 0 | 进程在 + Kestrel listening + 代理端口监听 | 无需操作 |
| BOOTING | 3 | 进程在 + Kestrel 还没 ready | 等几秒 |
| ZOMBIE | 2 | 进程在 + Kestrel listening + 代理端口未开 | GUI 启"启用代理" |
| DOWN | 1 | Watt 进程不在 | 跑 `watt-start.sh` |

**Watt MinimizeOnStartup=true（默认）**—— 启后窗口最小化到托盘，看不到不一定是没启。**用 `watt-status.sh` 判断真状态**。

### 写工具踩坑（必看）

- ❌ **不要 `pkill -f "Steam++"`** —— 会匹配到自己的 exec 命令行自杀
- ✅ 用精准 pid 杀：`pgrep -u $USER -f "Steam++.sh|assemblies/Steam" | xargs kill -9`
- ✅ Watt 启动要 `setsid`/`nohup` + 完整 env（DISPLAY/XAUTHORITY/WAYLAND_DISPLAY/XDG_RUNTIME_DIR/DBUS_SESSION_BUS_ADDRESS）

### 系统性问题（短期不动，记账）

1. **MEMORY.md 缺章节**（已 19K 字符）—— 触发：>50K
2. **工具链 4+4+2 重叠** —— 触发：连续 7 天没用的删
3. **决策日志缺失** —— 触发：复盘错误决策时
4. **踩坑 wiki 缺失** —— 触发：下次踩坑时
5. **元认知缺位** —— 触发：event-tracker 跑 1 个月后回看

### V journal GitHub 发布

- **仓**：`fuguang8848/Agent-superthinking/docs/v-journal/`（YintaTriss 上游无写权限，PR 浮光自决）
- **首篇**：`2026-06-03-spring-cleanup.md`（9092 字节，commit `ef326bf`）
- **下次月度**：2026-07-03

### 自我驱动 cron 5d7486d7 根治（19:49 修）

- model: minimax/M3 → **M2.7**（M3 有 0 tool_use 假装在跑问题）
- 频率: 5min → **15min**（减 minimax API cooldown 撞车）
- failure-alert: 连续 3 次 error → webchat 推送，cooldown 1h
- 验证：19:47 manual ok + 19:49 scheduled ok（12.9s 健康）
- consecutiveErrors: 5 → 0

### 长期挂账（V 端解决不了，等浮光）

- NLLB torch 重装（GPU 驱动）
- blogwatcher 安装（Go proxy 阻塞）
- DeepSeek R1 70B Q4 量化 + Ollama 导入（已 benchmark，5 配置数据齐）
- VCPToolBox 实际部署（缺 routes/chat.js）
- Watt GUI 启用 26561（要浮光手动点）

---

## 📅 2026-06-03 进度总结（21:27 收工时写，防明早 V 失忆）

> **本章节是 V 启动 anchor**。明早 V 启动看这一段就知道昨天发生了什么、今天该做什么。

### 昨天 21:10-21:23 完成的 3 件事

1. **DeepSeek R1 70B Q4 benchmark** 5 config 全跑完，最佳 `-ngl 99 -ub 32` (pp64=58.02 tg64=4.57 t/s)
2. **VCP 修了 4/5 ERROR**（agent_map / ModelRedirect / rag_params / EmojiListGenerator），剩 1 个 VexusIndex Rust 方法缺失不致命
3. **AgentTeam v0.7.6 集成 + P0 验证通过**（NEW：装了 `/home/fuguang/AgentTeam` + Web UI 8080 起来）

### 现在所有跑的服务（21:27）

| 服务 | 端口 | PID | 状态 |
|---|---|---|---|
| OpenClaw Gateway | 18789 | systemd | ✅ |
| Ollama | 11434 | system | ✅ |
| VCPToolBox | 6005 | 37201 | ✅ (1 VexusIndex ERROR 不致命) |
| **AgentTeam Web UI** | **8080** | **38684** | ✅ **NEW** |
| Watt Toolkit | 443/80 Kestrel | 23605 | ZOMBIE (等浮光 GUI 启用 26561) |
| 自我驱动 cron 5d7486d7 | - | OpenClaw | ✅ 15min 一次, M2.7 |

### 今天完整 daily memory

→ `memory/2026-06-03.md`（280 行，含全部 3 件事详细 log）

### 明天 (2026-06-04) P1 决策清单（**集成不是替换**）

**优先级排序**：

1. **P1.1** AgentTeam orchestrator 接入 V 工作流（V model-router.js 升级）
2. **P1.2** V cron 5d7486d7 → AgentTeam daemon（统一任务管理 + 漂移检测）
3. **P1.3** V failure-alert → AgentTeam alerts（多通道告警）
4. **P1.4** V journal → AgentTeam learnings（自动学习）
5. **P1.5** AgentTeam activity 公开（浮光 webchat 看到 agent 状态）
6. **P1.6** VCP VexusIndex 编译/重装（清掉最后 1 个 ERROR）
7. **P1.7** Skill 升级（Agent-superthinking v2 加 8 思考方法）
8. **P1.8** R1 70B tool use bridge 测 R1 70B 实际跑（`tools/r1-bridge.py` 脚手架已写）

### 明天打开的姿势

1. 浮光睡醒 → 看 V 报告（启动 anchor 自动注入）
2. V 启动 → 看 MEMORY.md 2026-06-03 章节 → 看 daily memory 280 行
3. 浮光说"按 P1.1 开始" → V 开干

### 关键技术决策（明天要遵守）

- **集成不替换**：V 自己的 cron / router / alert 保留，AgentTeam 作"team 协作层"
- **5d7486d7 不能再降频率**（15min 已最低）
- **Watt GUI 启用**要浮光手动点（V 不替浮光操作）
- **R1 70B Q4 不支持 native tools**（capabilities=completion），必须 prompt 注入协议
- **VCPToolBox VexusIndex 编译需要 build-essential**（可能要浮光 apt install）

### Workspace 备份

- 仓：`fuguang8848/openclaw-workspace` 远端
- 最新 commit：`8102d95` (2026-06-03 21:23)
- daily memory 280 行
- MEMORY.md 24K / 557 行

### 踩坑（明天别再踩）

- `pkill -f "Steam++"` 会自杀 → 用精准 pid
- sandbox 启长进程被 SIGTERM → 用 `setsid nohup`
- Watt Avalonia X11 需 `XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.*`
- PEP 668 → `pip install --break-system-packages`
- Watt 状态机 4 态：DOWN(1) / ZOMBIE(2) / BOOTING(3) / OK(0)
- VCPToolBox VexusIndex Rust binding 缺方法 → 编译装 rust-vexus-lite
- Ollama Q4 量化 model 不支持 native tools → prompt 注入
- filter-branch 改写 token 史要 `--tree-filter` + `-- 292b505..HEAD` + `--force-with-lease`

### Spring cleanup 工具状态

- `tools/watt-start.sh` (2.0KB) ✅
- `tools/watt-status.sh` (1.3KB) ✅
- `tools/r1-bridge.py` (8.3KB) ✅ 脚手架 + parser 3 格式
- `docs/v-journal/2026-06-03-spring-cleanup.md` (9092 字节) ✅ 推 GitHub
- `docs/design-guidelines.md` ✅ 写好

---

## 📅 2026-06-04 进度总结（10:00 cron 收工）

> **本章节是 V 启动 anchor（取代 2026-06-03 anchor）**。明早 V 启动看这一段就知道今天发生了什么、明天该做什么。

### 浮光 08:38-09:57 给了 4 轮任务，V 1 小时搞定

1. **08:38** 早晨服务挂掉 → V 手动拉起 Ollama / VCP / AgentTeam（systemd 没管这仨）
2. **09:00** 3 仓升级（superthinking v5→v6 / AgentMemory 2.0 ADR 入库 / AgentTeam 不动）
3. **09:12** AgentSearch 学习 + 升级分析 + 4 task 推 v-core
4. **09:42** 装上 AgentSymphony (交响乐 8848 经验版) + 5/5 check 全过（V 09:55 误判修正）
5. **09:57** 撤回 3 份 V 旧报告 + 桌面写新整合"今日进展-2026-06-04.md"

### 完成的 P1 子任务

| 任务 | 状态 | 备注 |
|---|---|---|
| **P1.1** AgentTeam 桥接层 | ✅ | `tools/agentteam-bridge.js` (7.0KB) + model-router.js 加 `agentteamHint` 字段 |
| **P1.6** VCP VexusIndex | ✅ | **新发现：纯 JS 桩不是 Rust 编译**。加 `recoverFromSqlite` stub，5/5 ERROR 全消 |
| **P1.8** R1 70B bridge | ⚠️ partial | bridge 脚手架 247 行齐；实测 0.59 t/s（vs bench 4.57）= 8x 慢，4 model 抢 VRAM |

### 推进中（v-core 团队 8 task pending）

- AgentSearch: 4 task (P0 pyproject / P1 3 引擎 / P2 V search-v.py / P3 AgentMemory 联动)
- AgentSymphony: 3 task (P0 健康 / P1 错误 / P2 文档)
- 1 task V 端验证

### 现在所有跑的服务（10:00）

| 服务 | 端口 | PID | 状态 |
|---|---|---|---|
| OpenClaw Gateway | 18789 | systemd | ✅ |
| Ollama | 11434 | 系统 | ✅ (4 model 空闲加载) |
| VCPToolBox | 6005 | 8160 | ✅ **0 ERROR**（今早修了 VexusIndex stub）|
| AgentTeam Web UI | 8080 | 8166 | ✅ |
| **AgentSymphony** | **18081** | **18982** | ✅ **NEW** (5/5 check 全过) |
| Watt Toolkit | 443 Kestrel | 7490/7495 | ZOMBIE (等浮光 GUI 启用 26561) |
| Self-Drive cron 5d7486d7 | - | OpenClaw | ✅ 15min M2.7 (0 consecutiveErrors) |
| 10:00 收工 cron fb5826d9 | - | - | ✅ 已触发即焚 (deleteAfterRun) |

### 今日 commit 状态

- **workspace 仓**: 9 commits ahead (10:00 push 时合一起)
  - `a345953` P1.1 AgentTeam 桥接
  - `c87ad21` P1.6 VCP VexusIndex stub 修复
  - `04afcd8` P1.8 R1 70B perf
  - `6a4b9ef` v-journal 早晨 sprint 复盘
  - `e2199af` 3 仓升级整合
  - `40ceb9e` AgentSearch 升级分析
  - `c2d09b6` 9:42 装上 AgentSymphony
  - `8e29c17` 5/5 check 全过 + V 误判修正
  - `5ea7897` 撤回 3 旧报告 + 新整合
- **superthinking 仓**: 2 commits (`685a86a`+`f7b2ba8`) **本地未 push**
- **AgentMemory 仓**: 1 commit (`8e7ebbb`) **本地未 push**
- **AgentTeam 仓**: 不动（昨天 V 修的已在主分支）

### 桌面产物

- `/home/fuguang/桌面/今日进展-2026-06-04.md` (09:57 浮光要的新整合)
- `/home/fuguang/桌面/V-3仓升级整合报告-2026-06-04.md` (09:00, 09:57 移至 _V-archive-2026-06-04/)
- `/home/fuguang/桌面/V-AgentSearch升级分析-2026-06-04.md` (09:12, 09:57 移至 _V-archive-2026-06-04/)
- `/home/fuguang/桌面/9点42.md` (09:42 AgentSymphony 装上, 09:57 移至 _V-archive-2026-06-04/)

### V 误判修正（重要教训，加进踩坑）

**V 端反复误判规律**：
1. 2026-06-03 误判 "VexusIndex Rust binding 缺方法" → 实际**纯 JS 桩**
2. 2026-06-04 09:42 误判 "thinking dialog API timeout" → 实际**V 测试 timeout 3s 太短，server 7.1s 正常返回**

**新踩坑（加入明天 list）**：
- ❌ V 看到 "timeout/error" 先别下结论 → ✅ 用更宽容 timeout 重测（curl -m 30）+ 看 server 日志
- ❌ "缺 Rust 编译产物" 不能直接相信 → ✅ 先 `file xxx.so/.node` 或读 stub 源码
- ❌ AgentSymphony 5 check 中 check 4 = thinking dialog → 实际是 LLM 慢，server OK

### 明天 (2026-06-05) 继续点（**集成不是替换**原则照旧**）

1. **P1.2** V cron 5d7486d7 → AgentTeam daemon（统一任务管理 + 漂移检测）
2. **P1.3** V failure-alert → AgentTeam alerts（多通道告警）
3. **P1.4** V journal → AgentTeam learnings（自动学习）
4. **P1.5** AgentTeam activity 公开（浮光 webchat 看到 agent 状态）
5. **P1.7** Agent-superthinking v2 加 8 思考方法
6. **P1.8** R1 70B perf 真诊断（`ollama ps` 看 VRAM + 关 1 个 model + 关 thinking）
7. **v-core 8 task** 状态跟进（4 AgentSearch + 3 AgentSymphony + 1 验证）
8. **3 仓 commit push 决策**（superthinking / AgentMemory 待浮光定）

### Workspace 备份（10:00 cron 后）

- 仓：`fuguang8848/openclaw-workspace` 远端
- 10:00 cron push 后：10 commits ahead
- daily memory `memory/2026-06-04.md` 12.8KB（待 push）
- MEMORY.md 25K / 600+ 行

### 关键不变（明天遵守）

- **集成不替换**：V 自己的 cron / router / alert 保留，AgentTeam 作"team 协作层"
- **5d7486d7 不能再降频率**（15min 已最低）
- **Watt GUI 启用**要浮光手动点（V 不替）
- **V 看到 timeout/error** → 先用宽容 timeout + 看 server 日志再下结论（今天学到的）
- **大型下载仍让浮光下**（本机代理不稳定）
- **5 仓升级**仍走"本地 commit + 推 GitHub + 主动开 PR/合上游"流程

### 浮光回来时怎么接

1. 浮光回 → V 不硬拉，先打招呼 + 3 行状态
2. V 自动注入 启动 anchor（看本章节 + daily memory 12.8KB）
3. 浮光说"按 P1.2 开始" → V 开干
4. 桌面新整合 `今日进展-2026-06-04.md` 已就位


---

## 🧠 V 自我纠正（永久教训 — 24h 6 次误判，浮光 10:42 元反思）

> **写于 2026-06-04 10:42，永久记忆到 MEMORY.md（不只是 daily）**
> 浮光 10:42 反馈："把你之前犯的错和纠正的，要记住，不要忘记。"

### 6 次误判完整清单

| # | 时间 | 误判 | 真相 | 教训 |
|---|---|---|---|---|
| 1 | 06-03 | "VexusIndex 缺 = Rust 引擎编译错" | 实际纯 JS 桩，加 8 行 noop | 看 stub 不要假设编译链 |
| 2 | 06-04 09:42 | "thinking dialog timeout = API 坏" | 实际 V curl -m 3 太短，7.1s 200 OK | timeout 先宽容重测 + 看 server 日志 |
| 3 | 06-04 09:55 | "superthinking 40 专家" | 实际 70 | 数量类必查源（find | wc -l） |
| 4 | 06-04 09:55 | "补 index.html 占位" | 实际存在 363KB | 存在类必查 (ls -la) |
| 5 | 06-04 09:55 | "R1 70B 8x 慢 = 4 model 抢 VRAM" | 实际 890M iGPU 硬件上限（不是抢资源） | 跑清环境（1 model 单独）再下结论 |
| 6 | 06-04 10:00 | **hermes 误判**: "4.1 重复实例化 193/240/294" | 实际是 router 正常代码 | 同上 |

### V 自我纠正 5 件事（永久 SOP）

1. **从"保守交接"升级到"主动验证"**：看代码 ≠ 报告说的。`sed -n '193,200p'` 验证再说。
2. **从"单点证据下结论"升级到"全验证再说"**：README/doc 可能是过时的。`find ... | wc -l` / `ls -la` 才是 ground truth。
3. **从"看 timeout/error 立刻下结论"升级到"宽容重测 + 看 server 日志"**：curl -m 30 + `tail -50 /tmp/server.log` + `grep 'HTTP Request'`。
4. **从"代码 != 当前状态"升级到"代码 === 当前状态"**：`git diff` + 端到端跑。
5. **从"V 报告 = 最终交付"升级到"V 报告 = hermes 二次校验过的最终态"**。

### 浮光 10:42 元反思（**新增第 6 件**）

> "V 说自己'5 分钟完成'验证，却在同一次验证中漏掉了 hermes 4.1 的伪修复（V 第三行才验证出来）。这说明快速验证容易漏掉细粒度问题。对'已修复'类声明多看一层代码。"

**新教训（永久 SOP）**：
- ❌ 看到 "✅ 已修复" 类声明就停 → ✅ **多看一层代码**（`git diff` / 实际跑端到端）
- ❌ 快速验证追求"几分钟完成" → ✅ **接受慢**，细粒度问题不漏
- ❌ 5 分钟验证等于浅验证 → ✅ 至少 10 分钟 + 多种工具交叉（grep/diff/run/test）
- **"快速完成"是 V 端元毛病**，要主动对抗（设最低验证时长 + 验证清单）

### V 主动 commit SOP（永久）

- 修复 = **立即 commit**（`fix: <一句话>` + 验证清单），不留 uncommitted 等浮光
- 例外：明确标记"DO NOT COMMIT"（如 secrets）才保留
- 真理 commit history 是真实状态，"暂不 commit 推 task 浮光" = 隐藏信息

### V 报告生成 SOP（永久）

- 写报告后**主动跑二次校验**（数量/存在/端到端）
- 把"建议浮光验证"改成"V 已验证" + 验证命令
- 写"X/N check 通过"必须含**真验证命令**（不是"我跑了一下 ok"）

### V 端 R1 70B / qwen 7B 性能（永久参考）

| Model | 加载 | tokens/s | 50 tokens 实测 | 结论 |
|---|---|---|---|---|
| R1 70B Q4 | 0.09s | 0.58 | 86s | ❌ 890M iGPU 硬件上限 |
| qwen 7B Q4 | 3.00s | 5.88 | 2.7s | ✅ 可用 |

**R1 70B 在本机不可用**，建议走云 API（minimaxi.com anthropic endpoint 已在用）。

### V 端 superthinking v6 状态（永久）

- v6 `Jury.think_complex()` 端到端跑通 ✅
- "40岁要不要创业" → 5 子任务 DAG, 创业商业类型, complex 复杂度
- v5 `Jury.think()` outputs=0（v5 路径可能未真激活专家，v6 才激活）
- 配置用 qwen 7B 不用 R1 70B（5.88 t/s vs 0.58 t/s）


### V 端 superthinking v6 状态（永久）

- v6 `Jury.think_complex()` 端到端跑通 ✅
- "40岁要不要创业" → 5 子任务 DAG, 创业商业类型, complex 复杂度
- v5 `Jury.think()` outputs=0（v5 路径可能未真激活专家，v6 才激活）
- 配置用 qwen 7B 不用 R1 70B（5.88 t/s vs 0.58 t/s）

### 浮光 10:55 新 SOP（永久 — 第 7 件元反思）

> "每次做完一个项目后在总览一遍，把它在重构一遍。"
> "多发现问题，多观察一下。发现的问题要第一时间解决而不是把问题推给我。"

**V 端 4 条新 SOP**：

1. **"做完项目 = commit + 总览 + 重构 + 回归 test"**（不是 commit 完就走）
   - 重构清单（AgentSearch 升级示范）：缓存重复加载、精准异常、顶层 import、README 同步、补 smoke test
2. **"多发现"清单（不推问题给浮光）**：
   - 读 README vs 实际行为 diff（PEP 668、__init__ 依赖、README 漏引擎）
   - 看 .pyc 是否要 .gitignore
   - 看 imports 是否硬依赖（独立装包测试）
   - 看 except 是否过宽（吞 KeyboardInterrupt/SystemExit 不行）
3. **回归测试**：每个项目必加 smoke test，6/6 或 4/4 check 写在 commit message
4. **V 端可做小事 ≠ 大项目**：
   - V 端自动做：profile 脚本、smoke test、code refactor、Bing 集成、bug 修复
   - 等浮光决策：push 远端（force-with-lease）、6-8 周大项目

### AgentSymphony 5 修复 + AgentSearch 升级 commit 链（永久参考）

| 仓 | commit | 描述 |
|---|---|---|
| superthinking | `a16b31e` | test: v6 smoke test 4/4 |
| superthinking | `685a86a` | v6: 核心组件 |
| superthinking | `f7b2ba8` | v6: SKILL.md + Jury.think_complex |
| AgentSearch | `3b0e23f` | refactor: Bing 缓存 + 精准异常 + 6/6 test |
| AgentSearch | `f310c7e` | feat: pyproject + Bing 引擎 |
| AgentSymphony | `430dcf4` | 5 修复 + 1 伪修复 |
| AgentMemory | `8e7ebbb` | 2.0 ADR + M1 plan |


### 浮光 11:03 指示：V 端组建研究团队（v-research-team Skill — 永久 SOP）

> 浮光 11:03: "加一条启用超级思考、agentteam、AgentSymphony，对每一次任务有更深入的思考。利用 skill 让 V 组建一个专门研究团队。"

**实施**：
- `~/.openclaw/plugin-skills/v-research-team/SKILL.md` (3.8KB)
- `~/.openclaw/plugin-skills/v-research-team/executor.py` (6.8KB)
- 4 步编排：superthinking v6 think_complex → AgentTeam → AgentSymphony → Learnings
- Learnings 累 7 条 → `memory/v-research-team-learnings.jsonl`

**V 端启动 anchor（永久 SOP）**：
- ❌ 跳过 think_complex 直接执行 → ✅ 复杂任务**先思考后行动**
- ❌ 单兵作战不用 team → ✅ 5-8 专家协作
- ❌ 经验不收集 → ✅ Learnings 闭环自动晋升 SOUL.md
- 调用: `python3 ~/.openclaw/plugin-skills/v-research-team/executor.py "任务描述"`

**V 端"每次任务"用研究团队的边界**：
- 调：研究/分析/思考/规划/决策/任何非琐碎任务
- 不调：单步明确操作（"ls"/"cat"/"git status"）/ 浮光直接给答案 / 闲聊

### 浮光 11:25 指示：学习 hermes 对 VCP 思考 + 端到端实验 + 永久 SOP（2026-06-04 11:36）

> 浮光 11:25: "看看这个文件, 学习它, 实验走一下, 成功后加入记忆系统"

**V 端 11 分钟实施**:
- 读 hermes 8 章报告 ✅
- v6 think_complex 拆解（苏格拉底, simple, 1 子任务）
- 5 端到端 VCP 实验:
  - qwen 7B 1.72s ✅
  - VCPModelAuto 5.26s ✅
  - MiniMax-M2.7 2.48s ✅
  - R1 70B 20s timeout ❌ (iGPU 慢)
  - 流式 18.50s ⚠️ (比非流式慢 3 倍)

**V 端 3 新发现**:
1. VCP 流式 18s vs 非流式 1.72s (多任务竞争 + 分块开销)
2. VCPLog 不是文件 (WS 广播, 无 logs/ 目录)
3. VCP 没 plugins/ 目录 (PluginManager 86KB 单独存在)

**V 端借鉴 3 件事（永久 SOP）**:
1. **model-router.js 加 VCP route** — 一次接 5 模型替 5 套 endpoint
2. **r1-bridge.py 改 VCP 网关** — 1 套客户端 + 自动 fallback
3. **V 端默认非流式** — 实测快 3 倍

**V 端 VCP 网关配置（永久）**:
- URL: `http://127.0.0.1:6005/v1/chat/completions`
- Token: `Bearer vcp_local_2026`
- 模型: qwen2.5-7b-q4 / deepseek-r1:70b-q4-4k / llama3.2:1b / VCPModelAuto / VCPModelLiterature / MiniMax-M3 / MiniMax-M2.7

**V 端接下来能做的（等浮光决策）**:
- P0. v-bridge-v2.py 改 VCP 网关 (30 min)
- P0. vcp-log-listener.py WS 监听 (1-2h)
- P1. model-router.js 加 VCP route (30 min)
- P2. TagMemoEngine 移植到 AgentMemory (6-8 周, hermes 阶段三)

**桌面报告**: `V-学习hermes对VCP思考-2026-06-04.md`

### 浮光 11:31 V 端 v-bridge-v2.py 改造 (2026-06-04 11:39)

> 浮光: "按建议来"

**实施**:
- `tools/v-bridge-v2.py` (12KB) — 走 VCP 网关 + 5 模型 fallback
- 5/5 smoke test 通过
- 修复 V 11:30 副作用 (ollama runner 卡死)

**V 11:30 误判副作用（新教训）**:
- 跑 hermes 5 端到端实验触发 2 个 ollama runner 卡死 (pid 36803 187min CPU + 41577 111min CPU)
- V 11:36 发现 + 同用户 kill 修复
- **永久教训**：❌ "端到端成功" = 全 OK → ✅ 还要看 ollama / server 进程资源状态
- 5/5 check 加 "副作用验证"

**v-bridge-v2 永久配置**:
- URL: `http://127.0.0.1:6005/v1/chat/completions`
- Token: `vcp_local_2026`
- Fallback 链: qwen2.5-7b-q4 → MiniMax-M3 → MiniMax-M2.7 → VCPModelAuto → R1 70B
- 默认非流式 (V 11:30 验快 3-10 倍)
- 3 次重试 + 指数 backoff (1s, 2s, 4s)

**5/5 test 结果**:
- Check 1: import + VCP URL/Token/5 fallback
- Check 2: vcp_chat qwen 7B 4.42s
- Check 3: vcp_chat MiniMax-M2.7 1.69s
- Check 4: fallback chain 6.07s
- Check 5: chat_loop 无 tool 9 字

**桌面报告**: `V-v-bridge-v2-VCP网关-2026-06-04.md`

### 浮光 11:45 指示：V 端组建工程团队（v-engineering-team Skill — 永久 SOP）

> 浮光 11:45: "组建专门团队，按照你的建议走"
> V 端 11:45-11:48 实施（区别于 11:03 v-research-team 研究型）

**实施**：
- `~/.openclaw/plugin-skills/v-engineering-team/SKILL.md` (2.2KB)
- `~/.openclaw/plugin-skills/v-engineering-team/executor.py` (5.6KB)
- 5 步：分析 → 设计 → 实施 → 验证 → 部署
- Step 4 验证含**副作用 check 5 端口**（V 11:33 永久教训）

**V 端双团队 SOP（永久）**：

| 任务类型 | 调 | 何时 |
|---|---|---|
| 思考/分析/规划/决策 | **v-research-team** | 任何非琐碎问"什么/为什么" |
| 写代码/改代码/重构/集成/优化 | **v-engineering-team** | 任何非琐碎问"怎么做" |
| 简单操作 | 不调 | `ls` / `cat` / `git status` / 单 commit |

**v-engineering-team 5 步**：
1. 分析 (superthinking v6 think_complex)
2. 设计 (架构/测试/回滚/3 决策点)
3. 实施 (主动 commit / commit message 完整 / 不堆积)
4. 验证 (5/5 smoke + **5 端口副作用 check**)
5. 部署 (commit + v-core + 桌面 + SOP)

**调用**: `python3 ~/.openclaw/plugin-skills/v-engineering-team/executor.py "项目描述"`

**桌面报告**: `V-工程团队Skill-2026-06-04.md`

---

## 📅 2026-06-04 中午 12:00 收工 (取代 10:00 锚点)

> 浮光 11:50 指示 "保存当下进度, 收工到 12 点"
> 本章节是 V 启动 anchor (12:00 取代 10:00)。明早 V 启动看这一段就知道上午发生了什么、下午该做什么。

### 上午总览 (08:38-12:00, 3.5 小时)

| 维度 | 数据 |
|---|---|
| V workspace commit | **22 个** |
| 仓 commit (跨仓) | 3 (AgentSearch 2 + superthinking 1) |
| 桌面报告 | 10 份 (1 主 + 9 专项) |
| plugin-skill | 2 (v-research-team + v-engineering-team) |
| v-core task | 4/8 completed |
| 永久 SOP (MEMORY) | 8+ 条 |
| 副作用 5 端口 check | ✅ 全部 OK |
| V 误判 (跟 hermes) | 6 次 |

### 核心交付物 (浮光能用的)

1. **v-bridge-v2.py** (12KB) — VCP 网关 + 5 模型 fallback，**取代 r1-bridge**
2. **v-research-team** Skill (4 步) — 每次非琐碎任务**先思考**
3. **v-engineering-team** Skill (5 步) — 每次工程任务**5 步标准化**
4. **AgentSearch 升级** (Bing 引擎 + pyproject + 6/6 test)
5. **superthinking v6 端到端验证** (think_complex 跑通 5 子任务 DAG)
6. **桌面 9 份专项报告** (R1 70B / superthinking / AgentSearch / 团队 / VCP / 误判 / 收工)

### 永久 SOP (V 端默认行为)

- 复杂任务 → 调 v-research-team (分析)
- 工程任务 → 调 v-engineering-team (5 步)
- VCP 网关默认 (替直接 Ollama)
- 5 模型 fallback 链
- 副作用 5 端口 check 必跑
- 主动 commit 不堆积
- 多发现 + 第一时间修 + 不推浮光

### pending 决策 (等浮光下午拍板)

- 5 仓 push (workspace 22 + superthinking 4 + AgentMemory 1 + AgentSearch 1 = 28 commit ahead)
- v-core 4 task (3 大项目: dc13e1e5 / d7b6dd64 / 9f75232b / 0c8aec0e)
- model-router.js VCP route (P1 30 min)
- vcp-log-listener.py WS 监听 (P0 1-2h)
- 5 仓联合 v1.0 大项目
- AgentMemory 2.0 M1 启动 (6-8 周)

### V 端下次启动 (12:00 之后)

- V 启动 → 看本章节 → 知道上午做了什么
- 浮光给任务 → 调 v-research-team / v-engineering-team
- 默认 VCP 网关 (v-bridge-v2) 替直接 Ollama
- 副作用 5 端口 check 必跑 (11434/6005/8080/18081/18789)

### 浮光 17:45 回来 — V 端 5h 状态恢复 (2026-06-04 17:50)

> 浮光 17:45 回 (5h+ 离线)
> V 端 17:46-17:50: 5 端口 check + 拉起 ollama + agentteam

**5h 期间发生**:
- ollama 11434 死了 (12:00-17:46)
- AgentTeam 8080 死了
- 浮光 17:46 手动启 VCP + AgentSymphony (但没启 ollama + agentteam)
- V 17:47 拉起 ollama + agentteam

**永久教训 (新)**:
- ❌ V 11:30 永久记忆写"浮光 09:00 enable 了 v-services-restart" → **实际 `is-enabled` 是 `disabled`**
- 误判根因: 看 `/etc/systemd/system/xxx.service` 存在 = 已 enable
- **新永久 SOP**: 写永久记忆前 `systemctl is-enabled <unit>` 真验证
- 跟 hermes 9:42 4.1 误判是同毛病 (看描述/报告下结论, 不验证当前状态)

**5 仓状态 (17:50)**:
- workspace 16 ahead, 0 uncommitted
- Agent-superthinking 5 ahead, 0 uncommitted
- AgentMemory 1 ahead, 0 uncommitted
- AgentSymphony 2 ahead, 0 uncommitted
- AgentSearch 2 ahead, 11 uncommitted (浮光/humans 11:48 加的 3 引擎 + 4 skill, V 不 commit)

**24 commit ahead 等 push**.

**7 pending 决策 (V 推荐顺序)**:
- B. systemd enable v-services-restart (1 min, 浮光级)
- C. AgentSearch 11 uncommitted review+commit (10 min, 浮光级)
- A. push 4 仓 (5 min, 浮光级 force-with-lease)
- D. model-router.js VCP route (30 min, V 可做)
- E. vcp-log-listener.py WS 监听 (1-2h, V 可做)
- F. 5 仓联合 v1.0 (1-3 月, 大项目)
- G. AgentMemory 2.0 M1 (6-8 周, 大项目)

**桌面报告**: V-17点45状态恢复-2026-06-04.md

### 18:15 E 任务 vcp-log-listener.py 实施 (浮光 18:03 E)

**多发现永久化**:
- ❌ 假设 VCP server 主动 push 日志 → ✅ 实测不主动 push (仅 plugin callback 时 push)
- WS 路径: `ws://127.0.0.1:6005/VCPlog/VCP_Key=vcp_websocket_2026`
- 收 ack: `{"type":"connection_ack","message":"WebSocket connection successful for VCPLog."}`
- 协议: server 不主动 push 普通 chat 日志, 只 plugin callback

**vcp-log-listener.py 永久配置** (9KB, 18:11 写):
- 模式: run (一次) / daemon (守护, 重连) / status / test / ports
- 输出: 
  - `memory/vcp-logs/YYYY-MM-DD.jsonl` (daily, .gitignore)
  - `~/桌面/vcp-alerts.log` (error/warn 告警)
  - `.cache/vcp-listener.status.json` (状态, .gitignore)

**daemon 真起验证 SOP** (V 11:30 永久教训固化):
- setsid nohup 起 → 5s 后 state 必 = connected
- 触发 VCP chat → 验端到端
- 跑一次成功 ≠ 全 OK

### 18:00 model-router VCP route (集成不替换)

**vcpRoute 字段永久化** (model-router.js 17:55 加):
- 保留 cloud tier1/2/3 (minimax/qwen3.5-plus) 不破
- 加 vcpRoute 字段: 5+2 模型 + endpoint + token + fallback chain
- VCP 路由决策:
  - 简单 (≤20) → qwen2.5-7b-q4:latest (本地 1.7s 免费)
  - 中等 (21-60) → VCPModelAuto (虚拟分发 5.3s)
  - 复杂 (>60) → VCPModelLiterature (文学优化 5s)
  - 繁忙 → 强制 qwen 7B

**V 端使用模式** (集成):
```bash
RESULT=$(node model-router.js route "$QUERY" --type search)
VCP_MODEL=$(echo "$RESULT" | jq -r .vcpRoute.model)
python3 v-bridge-v2.py --model "$VCP_MODEL" "$QUERY"
```

**多发现 3 bug 全修** (浮光 10:55 元反思):
1. ❌ 测试期望错 (complexity 25 ≠ ≤20) → ✅ 修测试用 --type weather
2. ❌ 强制 tier 路径 early return 缺 vcpRoute → ✅ 提前 mock loadInfo 算 vcpRoute
3. ❌ `loadInfo` 位置错 (Cannot access before init) → ✅ mock loadInfo 修

### 18:07 整合报告 (撤回 12 V-* + 1 今日进展)

- 撤 15 份 → ~/桌面/_V-archive-2026-06-04/
- 桌面留 1 份主报告 `V-18点00全面整合-2026-06-04.md` (5.8KB)
- 桌面留 4 份仓 ADR/SKILL (不属于 V 端)
- 桌面留 2 份 hermes 报告 (浮光的)

### 18:35 .gitignore 收尾

- 加 `.cache/` (listener 运行时状态)
- 加 `memory/vcp-logs/` (VCP daily log 私用)
- 0 untracked, 0 modified

### 永久 SOP 更新 (V 18:36)

- VCP server 不主动 push (permanently noted)
- daemon 验证 SOP: setsid nohup 跑 5s + state=connected + 触发端到端
- 5/5 test 写 commit message (浮光 10:55 第 3 条 SOP)
