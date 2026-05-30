# 02-工具集 — 本地工具说明

## 工具目录
`~/.openclaw/workspace/tools/`

## 核心工具

| 工具 | 类型 | 功能 |
|------|------|------|
| `clarifying.js` | Node | 需求澄清状态机 |
| `memory-inject.js` | Node | 主动记忆注入 |
| `model-router.js` | Node | 智能模型路由（四因素：复杂度+技能+负载+成本）|
| `event-tracker.js` | Node | 事件追踪（SQLite 持久化）|
| `search-router.js` | Node | 搜索路由 + 缓存 + EventBus + URL去重 |
| `router-agent.js` | Node | 意图分类 + 事件路由层 |
| `skill-handler.js` | Node | 4个内置 Handler |
| `daily-brief.py` | Python | 每日简报（天气/系统/博客/邮箱）|
| `daily-check.sh` | Bash | 系统检查脚本 |
| `backup-workspace.sh` | Bash | 配置备份（自动清理7天前）|
| `openclaw-fix.sh` | Bash | Gateway 自动修复 |
| `baidu-search.js` | Node | 百度搜索（备用）|

## 用法速查

```bash
# 需求澄清
node tools/clarifying.js init "<需求>"
node tools/clarifying.js answer "<回答>"
node tools/clarifying.js status

# 模型路由
node tools/model-router.js route "<任务>" [--type code|search|analysis]
node tools/model-router.js stats

# 记忆注入
node tools/memory-inject.js "<关键词>" --max 3

# 事件追踪
node tools/event-tracker.js emit <type> [data]
node tools/event-tracker.js query --type <type> --limit 50
node tools/event-tracker.js stats

# 每日检查
bash tools/daily-check.sh
python3 tools/daily-brief.py

# 备份
bash tools/backup-workspace.sh
```

## 依赖

| 包 | 状态 |
|-----|------|
| better-sqlite3 | 未安装（event-tracker 有 fallback）|
| httpx | ✅ 已安装 |

## 缓存目录
- 搜索缓存: `~/.openclaw/cache/search/`
- 事件追踪: `~/.openclaw/cache/event-tracker.db`
- 备份: `~/.openclaw/backup/`
