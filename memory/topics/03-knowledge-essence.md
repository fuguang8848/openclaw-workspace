# 知识精华 - 系统架构与设计理念

> 来源：V-知识精华源码分析 + AgentMemory 四层记忆系统
> 时间：2026-05-29

---

## AgentMemory 四层闭环记忆系统

源码：`/home/fuguang/AgentMemory/`

### 架构图

```
用户消息
    ↓
L1: LCM 压缩层（对话 → 关键事实）
    └── LLM 提取事实，不存原始对话

L2: Graph 图谱层（事实 → 实体关系）
    └── 实体（人名/项目）+ 关系 + 属性

L3: Vector 向量层（混合检索）
    └── 向量语义(60%) + BM25(30%) + 重要性(10%)

L4: Files 持久化层（记忆归档）
    └── MEMORY.md + 每日日记 memory/

遗忘引擎：评分 = 访问频率×0.3 + 重要性×0.3 + 时效性×0.4
```

### L1: LCM 压缩层（LLM Compressor）

**核心思路**：对话内容不直接存储，通过 LLM 提取关键事实

**事实类型**（FactType）：
- `person` — 人物
- `project` — 项目
- `date` — 日期/时间
- `decision` — 决策
- `preference` — 偏好
- `fact` — 一般事实
- `location` — 地点
- `event` — 事件

**LLM 事实提取流程**：
1. 对话历史 → 百炼 API → 结构化事实 JSON
2. 实体识别（人名/项目名/日期）
3. 重要性评分（0.0~1.0）
4. 去重检测（embedding 相似度 > 0.88 视为重复）

**我们的现状**：无 L1 层，MENORY.md 是纯文本，事件靠人工同步

### L2: Graph 图谱层

**实体类型**：PERSON / PROJECT / CONCEPT / LOCATION / ORGANIZATION

**存储结构**：
```json
{
  "entities": [
    {"id": "e1", "name": "石榴籽", "type": "project", "properties": {...}}
  ],
  "relations": [
    {"from": "e1", "to": "e2", "relation": "团队成员"}
  ]
}
```

**查询**：BFS 最短路径 / 邻居实体遍历

**我们的现状**：完全缺失，MEMORY.md 是扁平文本

### L3: Vector 混合检索层

**混合检索权重**：
- 向量相似度 60%
- BM25 关键词 30%
- 重要性评分 10%

**BM25 公式**：
```
score = IDF × (tf × (k1+1)) / (tf + k1 × (1-b + b×dl/avgdl))
```

**我们的现状**：
- 有 `search-v.py` 直接调 Bing，外部搜索
- 无本地 BM25 索引
- 无向量检索

### L4: Files 持久化层

**文件结构**：
```
memory/
    └── YYYY-MM-DD.md    # 每日日记
src/data/
    ├── vectors.json      # 向量存储
    ├── graph_store.json  # 图谱存储
    └── archive/          # 归档目录
```

**我们的现状**：已有类似结构，但无归档机制

### 遗忘算法（Decay Engine）

```python
遗忘得分 = 访问频率得分 × 0.3 + 重要性 × 0.3 + 时效性 × 0.4

# 时效性衰减（半衰期14天）
decay_factor = 2^(-recency_days / half_life)

# 决策阈值
score < 0.3  → 永久删除
0.3 ≤ score < 0.5 → 归档
score ≥ 0.5 → 保留
```

**访问频率得分**：
- 无访问：0.0
- 1次：0.2
- 2-3次：0.4
- 4-10次：0.6-0.8
- 10次以上：0.8-1.0（对数增长）

**我们的现状**：无遗忘机制，所有记忆永久保留

---

## Skill 设计理念（V-知识精华）

**核心公式**：Skill = 固化 SOP，工具是执行单元

```
爬虫 + 分析 + 报告生成 = 一个 Skill
```

**Skill Registry**（26个，分6层）：
1. 执行层（pandoc, team-tasks, email...）
2. 搜索层（tavily_search, local_search...）
3. Agent编排（clarifying, router-agent...）
4. 记忆层（memory-store, memory-inject...）
5. 信息层（blogwatcher, daily-brief...）
6. 系统层（gateway-watchdog, backup...）

**路由方式**：关键词匹配，longest-prefix-first

---

## Model Router 三因素路由

**Tier 分层**：

| Tier | 模型 | 复杂度上限 | 适用场景 |
|------|------|-----------|----------|
| tier1 | MiniMax-M2.1 | 20 | 简单问答、状态查询 |
| tier2 | qwen3.5-plus | 60 | 中等任务、搜索摘要、多步操作 |
| tier3 | qwen3.5-plus | 100 | 复杂任务、代码审查、架构设计 |

**三因素**：
1. 复杂度评分（query 词数 + 关键词特征）
2. 技能匹配（从 Skill Registry 查找）
3. 成本优化（优先低 tier）

**CLI**：`node tools/model-router.js route "任务描述"`

---

## Clarifying 需求澄清工作流

**状态机**：`clarifying → planning → executing → completed`

**标准5问**：
1. goal — 你想达成什么？
2. constraint — 有什么限制条件？
3. audience — 受众是谁？
4. priority — 优先级是什么？
5. context — 需要什么背景？

**CLI**：
```bash
node tools/clarifying.js init
node tools/clarifying.js answer "..."
node tools/clarifying.js status
```

---

## Event Tracker 事件追踪

**SQLite WAL 模式**，32 种事件类型

**事件流**：
```
emit(type, msg) → 写入 events 表
query(filters) → 条件查询
stats() → 聚合统计
```

**CLI**：`node tools/event-tracker.js emit <type> <msg>`

---

## 博客追踪现状

**RSS 订阅**：
- MIT Tech Review：`https://www.technologyreview.com/feed/`
- Hacker News：`https://hnrrs.org/frontpage`

**追踪状态**（blog-state.json）：各10篇

**实现**：daily-brief.py 内置 fetch_feed()，无需 blogwatcher

---

## 本地 LLM 部署（待完成）

**目标**：Ollama + Qwen2.5，本地跑 7B 量化

**优势**：128GB 内存，Ollama 最简方案

**障碍**：
- Ollama 安装脚本需要 curl 到 ollama.com（国际网络阻塞）
- 需要手动下载模型

**备选方案**：
- 用 pip 安装 ollama-python SDK
- 直接通过 REST API 调用 Ollama

---

## 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-05-29 | 不整合 AgentMemory | 百炼 API 成本高，向量检索暂时不需要 |
| 2026-05-29 | blogwatcher 放弃 | Go proxy 阻塞，daily-brief.py 已覆盖需求 |
| 2026-05-29 | iptables 持久化用 systemd | libvirt network hook 不生效 |
| 2026-05-29 | pandoc 用 Lua filter | XeLaTeX 不识别 heading 里的 Unicode escape |

---

## 升级里程碑

| 日期 | 内容 |
|------|------|
| 2026-04-06 | 生物钟 / SOUL.md / HEARTBEAT.md |
| 2026-04-22 | cron 修复 / 知识库整理 |
| 2026-04-23 | Tavily / Memory拆分 / 搜索决策树 |
| 2026-05-25 | AgentSymphony + AgentTeam 整合 |
| 2026-05-29 | AgentMemory / Ollama / 知识精华整理 |

---

## claude-code-skills（安全护栏设计）

源码：`/home/fuguang/claude-code-skills/`

### 核心理念

```
用户 → 我（记忆中枢）→ 派发 coding agent
                  ↓
           coding agent 自己调用工具
                  ↓
           结果返回给我，我存记忆
```

### 工具权限三级制

| 级别 | 权限 | 工具 |
|------|------|------|
| ✅ 直接允许 | ALLOW | read, exec（模式限制）, web_fetch, web_search, browser_snapshot/screenshot |
| ⚠️ 需要审批 | APPROVE | write, edit |
| ❌ 禁止 | DENY | exec_elevated(sudo), gateway, message_send |

### exec 白名单模式（最关键）

**允许的命令模式**（正则匹配）：
```
# Python / 环境
python3?, pip, conda, uv

# Git 只读操作
git status/log/diff/show/clone/branch/tag

# 搜索
grep, find, rg, Select-String, Get-ChildItem

# 文件查看
cat, head, tail, wc, ls, dir, type

# 网络检查（只读）
curl -s --head, ping, nslookup

# 进程/系统
ps, top, df, free, du, uptime

# 测试
pytest, python -m pytest
```

**禁止的命令模式**（危险模式）：
```
rm -rf /, del /f/s/q, format, dd if=.*of=/dev/
curl.*-X POST.*--data, wget --post-data
nc -e, bash -i, python.*eval(, exec(
(api_key|password|secret|token)='...'
```

### Memory Bridge（降级模式）

```python
# 优先用 agentmemory，降级到文件存储
if agentmemory_available:
    await mh.execute("store", {...})
else:
    写入 .claude_code_cache/memory_YYYYMMDD_HHMMSS.json
```

### Session Cache（跨 Session 持久化）

- 缓存目录：`.claude_code_cache/session_cache.json`
- 默认 TTL：24小时
- 持久化到文件，重启保留
- 支持 namespace 隔离（task/file/git）

### 与我们的互补性

- **exec 白名单** → 移植到 exec-guard.js ✅ 已完成
- **Session Cache** → 可以独立成 `session-cache.js`
- **Memory Bridge 降级模式** → 通用模式，适用于所有可选依赖

---

## Agent-superthinking（超级思考框架）

源码：`/home/fuguang/Agent-superthinking/`

### 架构

```
用户问题 → INDEX 路由层（关键词匹配）
              ↓
         相关专家（1~5个）并行思考
              ↓
         冲突检测层（观点矛盾识别）
              ↓
         共识提炼（融合共同结论）
              ↓
         最终回答 + 推理路径公开
```

### 专家体系（52位）

**人物专家**：`philosophy/`、`psychology/`、`business/`、`science/`、`arts/`
- 尼采、芒格、孙子、乔布斯、马斯克、爱因斯坦、苏格拉底...

**方法论专家**：`methods/`
- 第一性原理、极限思考、反溯法、TRIZ、博弈论、孙子兵法...

### 索引路由机制

```yaml
# 触发条件：问题中包含关键词
# 例如："为什么"→ 归因分析，"如何"→ 方法执行
```

**INDEX 格式**（单文件）：包含所有专家的 meta + prompt + 触发词
- 单一文件，避免 YAML 多文件复杂性
- 同一关键词可触发多位专家（取最高权重 top-N）

### 冲突检测

```
观点A：X 是因为 Y
观点B：X 是因为 Z
     ↓
检测：A和B结论矛盾
     ↓
标记为"冲突对"，在回答中呈现双方
```

### 核心 SKILL.md 格式

```yaml
name: 专家名
role: perspective/practice
trigger_keywords: [关键词1, 关键词2]
trigger_questions: [典型问题模式]
default_prompt: |
  你是一位...，请从...角度分析以下问题...
reflection_prompt: |
  质疑自己的结论，找出一个可能的反例...
```

### 对我们的价值评估

**结论：暂不集成，存档备用**

**原因：**
- 52位专家 + 19种方法论 = 重量级框架，集成成本高
- 浮光偏好简洁直接，不需要"让尼采+芒格+孙子同时分析同一个问题"
- 现有的 clarifying.js（需求澄清）+ model-router.js（任务路由）已覆盖核心需求

**有价值的点：**
1. **INDEX 路由机制** — 关键词匹配 + 文件驱动，比硬编码灵活
2. **多专家并行 → 冲突检测 → 共识提炼** — 融合层思路可借鉴
3. **方法论框架的触发词设计** — 比关键词匹配更精准

---

## AgentTeam（多 Agent 协作框架）

源码：`/home/fuguang/AgentTeam/`

### 核心架构

```
CTTeam（团队容器）
  ├── CTAgent（运行在 OpenClaw Session）
  ├── CTTask（任务跟踪）
  └── CTMessage（Agent 间消息队列）

OpenClaw SDK Backend
  ├── sessions.create → 创建独立 Session
  ├── sessions.send → 发送任务 + 协作协议
  └── Session Keeper 线程 → 心跳保活 + 任务注入 + shutdown
```

### TaskRouter 三因素路由（比我们 model-router 多负载感知）

| 因素 | 权重 | 说明 |
|------|------|------|
| 主题匹配 | 0-50 | 关键词命中数 / 总关键词 |
| 历史成功率 | 0-30 | completed_tasks / total_tasks |
| 质量评分 | 0-20 | avg_score（0-10 映射到 0-20）|
| 负载惩罚 | -5/任务 | Busy Agent 分数降低 |

```python
total_score = topic_match + success_score + quality_score - load_penalty
# topic_match 最高 50，success_score 最高 30，quality_score 最高 20，load_penalty 最高 -15
```

**可移植点**：我们 model-router.js 加负载感知参数

### Session Keeper（Agent 持续运行的关键）

```python
# Agent 不是执行完任务就退出，而是：
while not shutdown_event.is_set():
    # 每 30 秒检查 inbox 有没有新任务
    task = check_inbox()
    if task:
        execute(task)
        report_completion()
    sleep(30)
```

**shutdown 协议**：leader 发 "shutdown" → 写 shutdown.txt → 调用 exit

### AlertSystem 告警机制

| 级别 | 说明 |
|------|------|
| LOW / MEDIUM | 观察 |
| HIGH | 需要处理 |
| CRITICAL | 立即处理 |

**告警类型**：`TASK_TIMEOUT` / `AGENT_FAILURE_RATE_HIGH` / `TEAM_INACTIVITY` / `RESOURCE_EXHAUSTION`

### MailboxManager（Agent 间消息传递）

- 每条消息是 JSON 文件（原子写入，写 tmp 再 rename）
- Transport 可插拔：`file` / `p2p`（ZeroMQ）/ `redis`
- 事件日志：每条消息同时写入 events 目录（只写不消费，用于审计）

### 与我们的互补性

| 模块 | 价值 | 行动 |
|------|------|------|
| TaskRouter 负载感知 | ⭐⭐⭐⭐ | 可融入 model-router.js |
| Session Keeper 模式 | ⭐⭐⭐ | 想做 specialist agent 时参考 |
| AlertSystem | ⭐⭐⭐ | 设计可参考 |
| Web Board | ⭐⭐ | 优先级不高，暂不做 |
| 完整 Python 包 | ❌ | 架构太重，不集成 |

---

## AgentSearch（多引擎搜索技能）

源码：`/home/fuguang/AgentSearch/`

### 核心设计

| 模块 | 说明 |
|------|------|
| 多引擎并行 | Tavily / Brave / Exa / Perplexity |
| URL 去重 | `seen_urls = set()` 按 URL 哈希去重 |
| 缓存 | `MD5(query:engines)` → TTL 1小时 |
| 过滤 | relevance / freshness / authority / languages |
| 排序权重 | 相关性40% + 时效性30% + 权威性20% + 综合10% |

### 排序公式

```python
rank_score = (
    relevance × 0.4 +
    authority × 0.2 +
    freshness × 0.3 +
    score × 0.1
)
```

### 可借鉴点

1. **URL 去重** → 我们的 search-router 目前没有去重，可以加
2. **结果结构化字段** → freshness / authority 我们搜索结果缺这两个字段
3. **多引擎 fallback** → 某引擎失败不影响其他引擎

### 局限

- Python 包，不能直接用
- Tavily/Brave API 国内访问困难
- 架构和 search-v.py（直接爬 Bing HTML）完全不同

*最后更新：2026-05-29*
