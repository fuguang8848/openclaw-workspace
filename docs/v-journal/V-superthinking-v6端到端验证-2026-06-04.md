# superthinking v6 端到端验证 — 2026-06-04

> 浮光 10:00 让 V 跑 superthinking v6 端到端。V 11:37 跑通。

---

## TL;DR

**v6 `Jury.think_complex()` 端到端跑通** ✅
- 输入: "40岁要不要创业？"
- 输出: 4 keys dict (decomposed_plan / team_session / synthesis / learnings)
- 问题类型: **创业商业**（v6 自动识别）
- 复杂度: **complex**（激活多专家）
- 子任务数: **5**（DAG 分解）

---

## 跑通验证

```python
# 配置 qwen 7B 本地（不用 R1 70B 慢）
os.environ['LLM_MODEL'] = 'qwen2.5-7b-q4'
os.environ['OLLAMA_URL'] = 'http://127.0.0.1:11434'

jury = get_jury(profile_manager=pm)
team = TeamIntegration()
learnings = LearningsIntegration()

plan = jury.think_complex(
    question="40岁要不要创业？",
    user_id="default",
    team=team,
    learnings=learnings,
)
# plan = {decomposed_plan, team_session, synthesis, learnings}
# decomposed_plan.question_type = "创业商业"
# decomposed_plan.complexity = "complex"
# decomposed_plan.subtasks = 5 个
```

---

## v6 跟 v5 区别

| | v5 (think) | v6 (think_complex) |
|---|---|---|
| 输入 | 单 question | question + user_id + team + learnings |
| 输出 | JuryResult | dict (4 keys) |
| 复杂度 | 单层 | 3 层：Supervisor + Team + Learnings |
| 适用 | 中等问题 | 复杂问题（创业/转型/人生） |

---

## V 端观察

1. **v5 Jury.think 返回 outputs=[]**：可能 v5 路径没真激活专家（v6 才激活）
2. **v6 think_complex 真激活了 5 子任务** —— DAG 分解正常
3. **用 qwen 7B 5.88 t/s 跑**：v6 think_complex 实际用多久？未测（要 LLM 调 N 次）
4. **profile 数据**：仓有 `profiles/default.json`（V commit 时加入）

---

## 后续（待浮光决策）

1. **V 端 superthinking 触发逻辑**：基于 model-router complexity 自动调 v6（task `9f75232b` 已建）
2. **profile 初始化脚本**：为 70 专家生成 profile（hermes 提示）
3. **learnings 闭环验证**：跑 5+ 次 v6 看晋升高价值经验到 SOUL.md

---

_⚡ V 写于 2026-06-04 10:37_
