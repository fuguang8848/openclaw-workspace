# AgentSearch 升级 — 2026-06-04 10:42-10:50

> 浮光 10:42 让 V 按建议继续 + 永久记忆教训。
> V 端按 v-core task 6a2d2faa (P0 pyproject) + 1e8be5c2 (P2 Bing) 实施。
> 按浮光 10:42 元反思"多看一层"，多查多发现 3 个新问题并修。

---

## TL;DR

✅ AgentSearch 仓 commit `f310c7e`：
- pyproject.toml (1.1KB, 4 optional-deps)
- BING 引擎（V 端 search-v.py 集成）
- search_v_path 字段 + _search_bing 方法
- 修 agent_symphony 硬依赖（独立装包）
- .gitignore

✅ **5/5 check 通过**：import / BING enum / config 字段 / Bing 真搜 / 错路径降级
✅ v-core 2 task 标 completed（`6a2d2faa` + `1e8be5c2`）

---

## 1. pyproject.toml（v-core `6a2d2faa` P0）

- 包名 `agent-search` v1.0.0
- license MIT
- python ≥ 3.10
- 4 optional-dependencies: `bing` (httpx+lxml) / `symphony` / `team`
- **核心无依赖**（用 stdlib urllib）

按浮光"多看一层"，发现 README 说能装但实际 PEP 668 阻止 + 装包后 import 仍失败（agent_symphony 缺失）。**V 一并修了**。

---

## 2. Bing 引擎（v-core `1e8be5c2` P2）

### 改动
- `SearchEngine.BING = "bing"`
- `SearchConfig.search_v_path: str` 字段（env: `SEARCH_V_PATH`）
- `_search_bing()` 方法（importlib 动态加载 V 端 search-v.py）
- `_search` 主循环加 bing 分支

### 集成方式（V 端选）
- ✅ **方案 A（采用）**：importlib 动态加载 + SearchConfig.search_v_path
  - 不污染 sys.path
  - 不重复造轮子（search-v.py 是 V 端成熟实现）
  - 跨仓集成干净
- ❌ 方案 B：subprocess 跑 CLI（解析 JSON 慢、不优雅）
- ❌ 方案 C：内联实现（代码重复）

### 5/5 check
```
✓ Check 1: import SearchSkill/SearchConfig/SearchResult/SearchEngine
✓ Check 2: BING enum in SearchEngine
✓ Check 3: SearchConfig.search_v_path field
✓ Check 4: Bing 真搜: 2 results (OpenClaw)
✓ Check 5: search_v_path 错 → 降级 mock
```

### 实际效果
```python
config = SearchConfig(
    search_v_path="/home/fuguang/.openclaw/workspace/tools/search-v.py"
)
search = SearchSkill(config=config)
result = search.execute("search", {
    "query": "OpenClaw",
    "engines": ["bing"],
    "max_results": 3,
})
# success: True, engines: ['bing'], count: 3
# - OpenClaw - OpenClaw  | docs.openclaw.ai
# - OpenClaw | 能干活的 AI 助手  | openclaws.io
# - OpenClaw 入门指南  | 知乎
```

---

## 3. 浮光 10:42 元反思应用

> "V 说自己'5 分钟完成'验证，却在同一次验证中漏掉了 hermes 4.1 的伪修复"

**V 这次主动"多看一层"**：
- 看到 `pip install -e .` 失败 PEP 668 → 浮光级决策（不动）
- 看到装包后 `from agent_search import ...` 仍失败（agent_symphony 缺失）→ **V 主动修**
- 看到 `_search` 主循环 `else: mock` 吞掉所有错误 → 测错路径确认降级 ok
- 看到 __pycache__ 已 commit → 加 .gitignore

---

## 4. v-core 状态（10:48）

| ID | 任务 | 状态 |
|---|---|---|
| `c0ac9e7d` | P1.1 V ↔ AgentTeam 桥接 | ✅ completed |
| `62cdb62c` | P0 装上 AgentSymphony 5/5 check | ✅ completed |
| `6a2d2faa` | P0 AgentSearch 加 pyproject | ✅ completed |
| `1e8be5c2` | P2 AgentSearch 集成 search-v.py | ✅ completed |
| `dc13e1e5` | P1 补 3 引擎（Exa/Firecrawl/Perplexity） | ⏸ pending（2-3 小时） |
| `d7b6dd64` | P3 +AgentMemory 联动 | ⏸ pending |
| `9f75232b` | P1 AgentSymphony v2.3 升级 (M2) | ⏸ pending（1-2 周） |
| `0c8aec0e` | P2 5 仓联合 v1.0 大项目 | ⏸ pending（1-3 月） |

**4/8 completed** ✅ | 4 pending 需浮光决策（其中 3 个是大项目）

---

## 5. V 端永久记忆应用

`MEMORY.md` 已加：
- 6 次误判清单（V 5 + hermes 1）
- 5 件自我纠正
- **第 6 件（新）**：浮光 10:42 元反思 - 快速验证漏细粒度 → 多看一层
- V 主动 commit SOP
- V 报告生成 SOP

---

## 6. workspace commit

`5af6165` MEMORY 永久记忆 + `f310c7e` AgentSearch 仓升级

---

_⚡ V 写于 2026-06-04 10:50_
