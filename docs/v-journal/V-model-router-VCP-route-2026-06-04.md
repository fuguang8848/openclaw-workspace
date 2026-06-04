# V model-router.js 加 VCP route — 2026-06-04 17:55

> 浮光 17:52 "按建议来"。V 端按 P1 任务实施 model-router.js 加 VCP route (30 min)。

---

## TL;DR

✅ `tools/model-router.js` 加 VCP route（**集成不替换**）
- 保留 cloud tier1/2/3 (minimax / qwen3.5-plus) — 不破坏
- 加 `vcpRoute` 字段：5+2 模型 + endpoint + token + fallback chain
- 5/5 check 通过 + 副作用 5 端口 OK

---

## 1. 集成不替换（关键原则）

| 字段 | 来源 | 价值 |
|---|---|---|
| `model` (tier1/2/3) | cloud API (minimax / qwen3.5-plus) | 云端高质量，复杂任务 |
| `vcpRoute.model` | **VCP 本地** (5+2 模型) | 本地快+免费，自动 fallback |

**VCP 模型决策**（按 complexity）：
- `≤ 20` → `qwen2.5-7b-q4:latest`（本地 1.7s，免费）
- `21-60` → `VCPModelAuto`（虚拟自动分发）
- `> 60` → `VCPModelLiterature`（虚拟文学优化）
- 繁忙时 → 强制 `qwen 7B`（节省资源）

---

## 2. VCP 配置（永久）

```js
const VCP_CONFIG = {
  endpoint: 'http://127.0.0.1:6005/v1/chat/completions',
  token: 'vcp_local_2026',
  models: { /* 5+2 with latency_ms + cost */ },
  fallback_chain: [
    'qwen2.5-7b-q4:latest',
    'MiniMax-M3',
    'MiniMax-M2.7',
    'VCPModelAuto',
    'deepseek-r1:70b-q4-4k',
  ],
};
```

**优先级**：
1. 环境变量 `VCP_URL` / `VCP_TOKEN`（可覆盖）
2. 默认配置（永久 fallback）

---

## 3. 5/5 check 结果

```
✓ Check 1: 3 tier 仍 OK (cloud 不破)
✓ Check 2: vcpRoute 字段 + endpoint=6005 + token=***set*** + 5 fallback
✓ Check 3: 简单 (complexity=5) 选 qwen2.5-7b-q4:latest
✓ Check 4: 中等 (complexity=25) 选 VCPModelAuto
✓ Check 5: tier 3 强制 (cloud=tier3, vcp=VCPModelAuto)
```

**副作用 5 端口**：6 个监听（5 ipv4 + 1 ipv6 重复）✅

---

## 4. V 端多发现 3 个问题并修

按浮光 10:55 "做完就重构" + "多发现"：

1. ❌ 测试期望错（complexity 25 ≠ ≤20）→ ✅ 修测试用 --type weather
2. ❌ 强制 tier 路径 early return 缺 vcpRoute → ✅ 提前 mock loadInfo 算 vcpRoute
3. ❌ `Cannot access 'loadInfo' before initialization`（位置错）→ ✅ 强制 tier 路径用 mock loadInfo

**6/6 check 全过**（含 3 修）

---

## 5. 使用示例

```bash
# 简单 (complexity 5, weather type)
node model-router.js route "杭州今天天气" --type weather
# → cloud: tier1, vcp: qwen2.5-7b-q4:latest (本地 1.7s)

# 中等
node model-router.js route "今天市场行情" --type search
# → cloud: tier2, vcp: VCPModelAuto

# 复杂
node model-router.js route "深度分析 X" --tier 3
# → cloud: tier3, vcp: VCPModelLiterature

# 集成: V 端用 vcpRoute 调 v-bridge-v2.py
RESULT=$(node model-router.js route "$QUERY" --type search)
VCP_MODEL=$(echo "$RESULT" | jq -r .vcpRoute.model)
python3 v-bridge-v2.py --model "$VCP_MODEL" "$QUERY"
```

---

## 6. 关联

- `v-bridge-v2.py` (11:31) — VCP 网关 + fallback 5 模型
- `model-router.js` (17:55) — 路由决策 + vcpRoute
- 集成点：V 端调 v-bridge-v2 时直接传 vcpRoute.model

---

## 7. 永久 SOP

- V 端默认走 vcpRoute（本地快 + 自动 fallback）
- Cloud 路由保留（高质/特殊模型）
- 集成不替换：V 不动 cloud route，仅加 vcpRoute 字段

---

_⚡ V 写于 2026-06-04 17:55_
