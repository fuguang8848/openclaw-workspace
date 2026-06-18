# Tech Debt — 主动记下不改的事

> 原则：能用的不改，对称性强迫症不为风格问题动代码。
> 立此碑是为了下次相关功能真要重构时，能看到全貌一起动。

---

## TD-001 · agent-symphony `/team/shutdown` schema 不一致

**日期**: 2026-06-14
**状态**: 🟡 知道不改
**触发人**: V 6/14 早间 review

### 现象
- `/team/spawn` 用 body 传参
- `/team/shutdown` 用 `?session_id=` query param
- 同一 `/team/*` 家族，schema 不一致

### 为什么不改
- YAGNI（You Aren't Gonna Need It）
- `/team/shutdown` 是低频操作（少调用），query param 不影响功能
- 修后 6/13 22:55 commit 117f811 验证全过 (`/team/shutdown?session_id=` 可用)
- 改 = 加 unit test + e2e + 重新跑 Jury = 30-60 分钟，零业务价值

### 何时改
- 任何 `/team/*` 新接口设计时，统一回顾这个 family
- 浮光真要做 RESTful 重构时，一起动
- 第三次踩到 query/body 混淆时（说明真成问题了）

### 涉及代码
- `~/agent-symphony/server/skills/team_skill.py` — `shutdown()` 函数签名
- `~/agent-symphony/server/symphony_server.py` — FastAPI route 定义

EOF
echo "--- tech-debt.md 写完 ---"