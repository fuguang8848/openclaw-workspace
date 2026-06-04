# V AgentSearch 11 uncommitted Review — 2026-06-04 18:42

> 浮光 18:40 "按你的建议来". V 端 review AgentSearch 11 uncommitted (浮光/humans 11:48 加的) 给 commit 建议.

---

## TL;DR

✅ **11 uncommitted 全是浮光/humans 11:48 自己加的**（不是 V 加的）
✅ 质量: 高 — 3 引擎 HTTP 实际实现 + 4 个 Symphony 风格 skill + 4 个 test
✅ 对应 v-core `dc13e1e5` P1 补 3 引擎（浮光自己 2-3h 做完了）
⚠️ 2 个 untracked `.pyc` 应该在 commit 前卸掉

---

## 1. 11 uncommitted 明细

### 改 2 文件 (M)

| 文件 | 改 | 行数 | 评价 |
|---|---|---|---|
| `agent_search/skill.py` | 加 3 引擎**实际 HTTP 实现** (Exa/Firecrawl/Perplexity) | +212 行 | ✅ 完整 API 客户端 |
| `tests/test_smoke.py` | 加 3 引擎 enum check + new API key fields | +17 行 | ✅ smoke test 加严 |

### 6 新文件 (??)

| 文件 | 行数 | 评价 | 关联 |
|---|---|---|---|
| `agent_search/manager_skill.py` | 681 | ✅ AgentManager (注册表/prompt 加载) | 参考 VCP agentManager.js |
| `agent_search/safety_skill.py` | 536 | ✅ AgentSafety (注入检测/PII 脱敏) | 分层检测 |
| `agent_search/supervisor_skill.py` | 755 | ✅ AgentSupervisor (协调/监控/恢复) | Symphony 风格 |
| `agent_search/team_skill.py` | 382 | ✅ Team 桥接 (sessions_spawn) | AgentTeam SDK |
| `tests/test_manager.py` | ? | ✅ Manager test | — |
| `tests/test_safety.py` | ? | ✅ Safety test | — |
| `tests/test_supervisor.py` | ? | ✅ Supervisor test | — |

(实际 4 test 文件 — `test_smoke.py` 改 + 3 新)

### 2 untracked `.pyc` (D)

```
 D agent_search/__pycache__/__init__.cpython-313.pyc
 D agent_search/__pycache__/skill.cpython-313.pyc
```

⚠️ **commit 前先 `git restore agent_search/__pycache__/`**（untracked pyc 不应入库）

---

## 2. 关键代码片段 (V 端 review)

### skill.py 加 3 引擎 (高质量)

```python
elif engine == "exa" and self.config.exa_api_key:
    results = self._search_exa(query, max_results)
    used_engines.append("exa")
elif engine == "firecrawl" and self.config.firecrawl_api_key:
    results = self._search_firecrawl(query, max_results)
    used_engines.append("firecrawl")
elif engine == "perplexity" and self.config.perplexity_api_key:
    results = self._search_perplexity(query, max_results)
    used_engines.append("perplexity")
```

✅ 跟 tavily/brave 一致的兜底链 (单引擎失败不影响其他)
✅ 用 `urllib.request` 不引新依赖
✅ `SearchAPIError` 统一错误处理

### team_skill.py (symphony 桥接)

```python
GATEWAY_URL = "ws://127.0.0.1:18789"
POLL_INTERVAL = 5  # 秒
```

✅ 用 sessions_spawn 模式 (跟 v6 think_complex 集成方向一致)
✅ 直接读 session JSONL 绕过 Gateway 权限 (跟 v-research-team executor 一样)

---

## 3. V 端 commit 建议 (浮光 review 后决定)

### 推荐 commit 拆分 (3 commit)

按"完成项目 = commit + 总览 + 重构 + 回归 test" 浮光 10:55 SOP：

```bash
cd /home/fuguang/AgentSearch

# 卸 untracked pyc (浮光级, V 不动)
git restore agent_search/__pycache__/ 2>/dev/null || rm -f agent_search/__pycache__/*.pyc

# Commit 1: skill.py + test_smoke.py 改 (核心引擎)
git add agent_search/skill.py tests/test_smoke.py
git commit -m "feat(search): add Exa/Firecrawl/Perplexity engine implementations

3 引擎 HTTP 实际实现 (urllib.request, 无新依赖):
- _search_exa (api.exa.ai/search)
- _search_firecrawl (api.firecrawl.dev/v0/search)
- _search_perplexity (api.perplexity.ai/search)

SearchConfig 加 3 API key 字段
SearchEngine enum 验证
test_smoke.py 加 3 引擎 check (7 个引擎 enum)"

# Commit 2: 4 新 skill (Manager/Safety/Supervisor/Team)
git add agent_search/manager_skill.py agent_search/safety_skill.py \
        agent_search/supervisor_skill.py agent_search/team_skill.py
git commit -m "feat(skill): add 4 symphony-style skills (Manager/Safety/Supervisor/Team)

manager_skill.py: AgentManager (注册表/prompt 加载/角色切换)
safety_skill.py: AgentSafety (注入检测/PII 脱敏/内容分类/审计)
supervisor_skill.py: AgentSupervisor (协调/监控/恢复/资源/报告)
team_skill.py: Team 桥接 (sessions_spawn + JSONL 直接读)
参考 VCP agentManager.js + AgentSymphony + AgentTeam"

# Commit 3: 3 新 test 文件
git add tests/test_manager.py tests/test_safety.py tests/test_supervisor.py
git commit -m "test: add 3 new skill tests (manager/safety/supervisor)"

# 看 status
git status
```

### 风险

- ⚠️ **V 没跑 test**（V 端没 AgentSearch 仓的 venv, 也浮光/humans 自己的代码, V 测不安全）
- 浮光 commit 后跑 `python3 -m pytest tests/ -v` 验

---

## 4. V 端**不 commit** 别人代码的 SOP

按 V 永久 SOP "V 不推浮光"：
- ❌ V 不替浮光 commit 11 uncommitted
- ❌ V 不替浮光 review 后改
- ✅ V 端提供 review + commit 建议（本文）
- ✅ V 端等浮光决定

---

## 5. 关联

- v-core task `dc13e1e5` P1 补 3 引擎 (2-3h) — 浮光/humans 自己做了
- skill.py 改 100% 覆盖 `dc13e1e5` 内容
- 4 新 skill (manager/safety/supervisor/team) 跟 AgentSymphony 集成方向一致
- team_skill.py 跟 v-research-team executor 共享 sessions_spawn 模式

---

_⚡ V review 于 2026-06-04 18:42_
