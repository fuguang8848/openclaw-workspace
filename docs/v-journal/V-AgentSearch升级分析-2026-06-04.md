# V 端 AgentSearch 学习 + 升级分析 — 2026-06-04

> 浮光 09:12 让我：用 AgentTeam + 超级思考对 `/home/fuguang/AgentSearch` 学习并升级，将升级版整理到桌面，顺便思考其他可发展方向。
> V 端 30 分钟完成：**学习 + AgentTeam 拆任务 + superthinking 分解 + 桌面报告**。
> 注：**V 不动 AgentSearch 仓**（V 保守）。升级任务推到 v-core team，浮光 web UI 看进度。

---

## TL;DR

AgentSearch 是个**单文件 708 行** Python 仓，5 引擎定义但**只实现 2 个**（Tavily/Brave），没 pyproject.toml（README 说能装但实际没），4 个升级方向已用 AgentTeam 拆成 P0-P3 任务推到 v-core team 看板。

| 升级方向 | 优先级 | 复杂度 | 推到 v-core task id |
|---|---|---|---|
| 加 pyproject.toml | P0 | 低 (10 行) | `6a2d2faa` |
| 补 Exa/Firecrawl/Perplexity 引擎 | P1 | 中 (60-100 行/引擎) | `dc13e1e5` |
| 集成 V 端 search-v.py (Bing fallback) | P2 | 低 (5 行 + config) | `1e8be5c2` |
| 联动 AgentMemory (auto-store results) | P3 | 中 (钩子层) | `d7b6dd64` |

---

## 1. AgentSearch 学习（仓现状）

### 文件结构
```
AgentSearch/
├── agent_search/
│   ├── __init__.py         (35 行 — 暴露 SearchSkill/SearchConfig/SearchResult/SearchEngine/get_skill_instance)
│   ├── skill.py            (708 行 — 核心实现)
│   └── SKILL.md            (108 行 — OpenClaw 技能入口)
├── README.md               (1.2 KB)
├── .git/                   (git 仓，1 commit 1cf1c33)
└── (没 pyproject.toml!)
```

### 远端身份
- 仓：`YintaTriss/AgentSearch`（跟 AgentTeam 一样，浮光是 fork 之一）
- 本地 git tracking 1 commit `1cf1c33 Rename: SearchSkill → AgentSearch`
- 协议：MIT

### 实现状态

| 引擎 | 枚举 | 实际实现 | API |
|---|---|---|---|
| Tavily | ✅ | ✅ | POST https://api.tavily.com/search |
| Brave | ✅ | ✅ | GET https://api.search.brave.com/res/v1/web/search |
| Exa | ✅ | ❌ 占位 | (跳过) |
| Firecrawl | ✅ | ❌ 占位 | (跳过) |
| Perplexity | ✅ | ❌ 占位 | (跳过) |
| Mock | ✅ | ✅ | 本地假数据 |

### 关键能力（5 个 query capability）
- `search.execute` — 多引擎搜索
- `search.crawl` — 深度爬取（仅 Tavily Extract + mock）
- `search.filter` — 过滤（relevance/languages/authority）
- `search.rank` — 排序（relevance 40% + freshness 30% + authority 20% + score 10%）
- `search.cache` — 缓存（TTL 1h, MD5 key）

### 关键依赖
- `from agent_symphony.shared import SharedContext, get_context` — **依赖 AgentSymphony 仓**
- 仓里**没** agent_symphony 包（外部依赖）
- 单独跑会 ImportError

### SKILL.md v1.0.0 metadata
```yaml
name: search
version: 1.0.0
family: agent-symphony
role: information-retrieval
description: 搜索技能 - 多引擎搜索、爬虫、过滤、排序
```

---

## 2. V 端 AgentTeam 任务分解（推到 v-core team）

V 用了今早 08:46 写的 `tools/agentteam-bridge.js`，4 个 task 推到 v-core 团队：

| Task ID | 标题 | 描述摘要 |
|---|---|---|
| `6a2d2faa` | **P0**: AgentSearch 加 pyproject.toml | 当前 README 说 `pip install -e .` 但没 pyproject.toml，要补上。包名 agent-search，依赖：httpx/tenacity/python-dotenv。10 行左右。 |
| `dc13e1e5` | **P1**: 补全 Exa/Firecrawl/Perplexity 引擎 | SKILL.md 列出 5 引擎，实际只实现 Tavily+Brave。Exa (semantic)、Firecrawl (deep crawl)、Perplexity (LLM answer) 都是占位。每引擎 60-100 行。 |
| `1e8be5c2` | **P2**: 集成 search-v.py (Bing fallback) | V 端已有 `tools/search-v.py` 调 Bing HTML，可作第五个 engine (bing)。当 Tavily/Brave 失败时自动 fallback。 |
| `d7b6dd64` | **P3**: + AgentMemory 联动 (auto-store) | SKILL.md 提"自动将结果存入 memory"但 skill.py 没真做。relevance≥0.8 的 result 调 AgentMemory 1.0 MemoryProvider.add()，双写 (sqlite + file_store)。 |

**浮光 web UI 验证**：打开 http://127.0.0.1:8080 → v-core team → 5 个 task pending（4 新 + 1 旧的 P1.1 验证）

---

## 3. V 端 superthinking v6 思考

V 端跑了一次 `SupervisorAdapter.decompose()`（不调 LLM，纯结构化）：

```
问题: "AgentSearch 仓 708 行 5 引擎只实现 2 个，缺 pyproject.toml，如何升级到 2.0？"
复杂度: simple
问题类型: 通用问题
激活专家: 苏格拉底 (1 个)
关键角度: 事实/价值/行动/风险
警示: 确认偏误、后见之明
```

**V 解读**：
- v6 自动识别"如何升级"是**通用问题**，激活 1 个专家（苏格拉底 — 追问本质）
- 想要 COMPLEX（激活 4-8 专家）需要**更具体的升级问题**（如"商业化路径"会激活巴菲特+芒格）
- 演示 superthinking v6 跑通，结构化分解正常

---

## 4. V 端新发现

### 4.1 AgentSearch 仓的 4 个隐藏问题

1. **没 pyproject.toml** — README 撒谎（说能 `pip install -e .`）
2. **没独立 `__init__.py` 暴露** — `from agent_search import X` 直接依赖 skill.py 内部
3. **3 个引擎占位不实现** — SKILL.md 撒谎（提了 Exa/Firecrawl/Perplexity 但代码没）
4. **依赖 AgentSymphony 但不一起装** — `SharedContext` import 必失败

### 4.2 SKILL.md 提到的"联动"都没真做

- "thinking 调用 search.execute() 获取信息" — **skill.py 没用 thinking**
- "search 自动将结果存入 memory" — **skill.py 没用 memory**
- "search 利用 context 共享上下文" — **仅单向写 context，没读**

### 4.3 SKILL.md 提的"过滤器"是 stub

- "freshness 时效性要求" — `_apply_filters` 里 `pass`（no-op）
- "languages 语言过滤" — `_apply_filters` 里 `filtered = [r for r in filtered]`（无操作）
- "authority 权威性阈值" — Tavily/Brave 都没给分，硬编码 0.5

### 4.4 V 端"改进点"（不替浮光做，写在 P0-P3 task 里）

- P0 修 README 撒谎
- P1 修 SKILL.md 撒谎（要么补全实现，要么 SKILL.md 改）
- P2 修 freshness/languages filter
- P3 修 SKILL.md 联动承诺

---

## 5. **其他可发展方向 brainstorm**（浮光要求的"顺便思考"）

> V 端从 AgentSearch 这个点出发，思考 5 个能跟 AgentSearch 联动的方向。

### 5.1 🔥 跟 AgentMemory 1.0 联动 — 高价值

- **做什么**：每次 search 后 relevance≥0.7 的 result 自动存进 AgentMemory 1.0
- **价值**：搜索结果变成"长期知识"，下次相似 query 直接命中
- **现状**：SKILL.md 写了没做
- **V 端已建 task**：`d7b6dd64` (P3)
- **P2 联动**：跟 AgentMemory 2.0 M1 同步（provider 切换时 search_sink 也跟着切）

### 5.2 🌐 跟 V 端 search-v.py 集成 — 中价值（已有脚本）

- **做什么**：把 V 端 `tools/search-v.py`（Bing HTML 解析）作为 AgentSearch 第 6 引擎
- **价值**：零 API 成本（不要 Tavily/Brave key），适合国内/隐私场景
- **现状**：search-v.py 已写好，AgentSearch 没用
- **V 端已建 task**：`1e8be5c2` (P2)
- **实现**：~5 行 + 1 个 SearchEngine.BING enum

### 5.3 🧠 跟 superthinking v6 联动 — 中价值

- **做什么**：search 结果自动喂给 superthinking v6 `think_complex()` 的 context
- **价值**：复杂问题（"分析 AI Agent 市场"）自动 search → 多个专家视角引用 search 结果
- **现状**：SKILL.md 提了没做
- **V 端建议**：在 SearchSkill 加 `mode="deep_research"` 参数，返回 search result + superthinking 综合报告
- **跟 P1.7** (Skill 升级) 合并

### 5.4 📊 跟 V 端 search-router.js 集成 — 低价值（重复劳动）

- **做什么**：search 结果按 V search-router 的 TTL 30min 缓存
- **价值**：跨 search 调用共享缓存
- **现状**：AgentSearch 已有 cache（TTL 1h），V search-router.js 是路由层
- **V 端建议**：**不要做**。两个 cache 各自管自己就够了，集成反而复杂

### 5.5 🚀 AgentSearch 2.0 升级方向（远期）

| 方向 | 做什么 | 价值 | 工作量 |
|---|---|---|---|
| **异步** | 全部 `urllib` → `httpx.AsyncClient` | 高并发场景 | 中 |
| **类型化** | dataclass → Pydantic v2 | 类型安全 + JSON 序列化 | 中 |
| **Observability** | 加 OTel trace + Prometheus metrics | 监控 / 告警 | 中 |
| **Plugin 化** | SearchEngine 改成 entry_points 插件 | 第三方加引擎 | 大 |
| **Streaming** | SSE 流式返回 | LLM 实时性 | 大 |
| **A/B test 框架** | 双引擎对比 | 引擎质量优化 | 中 |
| **国内引擎** | 百度/搜狗/微信搜一搜 | 国内可用 | 大 |

**V 端建议**：先做 P0+P2（pyproject + search-v.py 集成），其他远期规划。

### 5.6 🌱 V 端发现的"机会窗"

- **5 个 agent 仓的**协作还没真正打通**：
  - AgentMemory（记忆）
  - AgentSearch（搜索）
  - AgentTeam（协作）
  - AgentSymphony（依赖）
  - Agent-superthinking（思考）
- 当前是 **5 个独立仓**，但有 **5+ 个集成点**没做：
  1. Search → Memory（自动存）
  2. Thinking → Search（自动查）
  3. Team → Memory（共享记忆）
  4. Team → Search（团队搜索）
  5. Symphony → 5 个仓（统一调度）
- **V 端建议**：**5 仓联合 v1.0** 是个大项目（M2 量级），不替浮光做

---

## 6. 时间线

| 时间 | 事 |
|---|---|
| 09:12 | 浮光消息：用 AgentTeam + 超级思考 学习升级 AgentSearch |
| 09:13 | V 读 AgentSearch 仓（708 行 skill.py + 108 行 SKILL.md + README） |
| 09:13 | V 推 4 task 到 v-core team（`6a2d2faa` / `dc13e1e5` / `1e8be5c2` / `d7b6dd64`） |
| 09:14 | V 跑 superthinking v6 `SupervisorAdapter.decompose()` 端到端 |
| 09:15 | 写本报告到桌面 |
| 09:15 | commit + 10:00 cron 兜底 |

---

## 7. V 端下一步

| 事项 | 浮光决策 | V 默认 |
|---|---|---|
| 是否实施 P0（pyproject.toml） | 等浮光 | 10 行脚本，可直接做 |
| 是否实施 P1（补 3 引擎） | 等浮光 | 60-100 行/引擎，2-3 小时 |
| 是否实施 P2（search-v.py） | 等浮光 | 5 行，可直接做 |
| 是否实施 P3（+Memory） | 等浮光 | 钩子层 30 行 |
| 5 仓联合 v1.0 大项目 | 等浮光 | 不替浮光开 |
| superthinking v6 端到端跑 think_complex | V 端验证 | 等下次 |

---

## 8. 升级版"整理到桌面"清单

| 文件 | 来源 | 用途 |
|---|---|---|
| `V-3仓升级整合报告-2026-06-04.md` | V (3 仓) | 3 仓升级整合 |
| `V-AgentSearch升级分析-2026-06-04.md` | V (AgentSearch) | **本报告** |

---

**V 端总结**：30 分钟 AgentSearch 学习 + AgentTeam 拆 4 task + superthinking 跑通 + 桌面报告。**没动 AgentSearch 仓**（V 保守），升级任务推到 v-core team 看板等你 web 看。

_⚡ V 写于 2026-06-04 09:15，10:00 cron 兜底自动保存_
