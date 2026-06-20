# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

---

## 6/19 起 — V 主动检查 (SOP #34 L1 + 5 仓 git state + watchdog systemd)

每次 heartbeat 必跑:
```bash
# 1. SOP #28 L1: 5 端口 (含 18789 gateway, 6 端口)
for p in 6005 6006 18081 8080 11434 18789; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:$p/ 2>/dev/null || echo "000")
  [ "$code" = "000" ] && echo "🚨 port $p: DOWN"
done

# 2. SOP #37: 5 仓 HEAD activity (since last check, systemd-managed watchdog 24/7 跑)
python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py activity --since "$(date -d '6 hours ago' -Iseconds)" --limit 5

# 3. SOP #37 #3 限制解: watchdog systemd status
systemctl --user is-active v-git-activity-watchdog.service > /dev/null && echo "  watchdog: UP" || echo "  🚨 watchdog: DOWN"

# 4. SOP #28 L1: workspace git state
cd /home/fuguang/.openclaw/workspace && git log --oneline -1

# 5. 5 仓 ahead 状态 (SOP #35 阈值 20, 真实 fork ahead)
for repo in Agent-superthinking AgentSearch AgentTeam AgentMemory-upgrade AgentSafety; do
  cd ~/$repo
  fork_remote=$(git remote get-url fuguang >/dev/null 2>&1 && echo fuguang || echo origin)
  ahead=$(git rev-list --count ${fork_remote}/HEAD..HEAD 2>/dev/null || echo 0)
  [ -n "$ahead" ] && [ "$ahead" -gt 0 ] && echo "  $repo: fork ahead=$ahead"
done
```

### 触发级别 (6/19 18:49 修真后更新)
- 端口 DOWN → 立即发 alert
- **watchdog DOWN** → 立即发 alert (systemd 24/7 跑, 不应 DOWN)
- 5 仓 **fork ahead** 累计 > 20 → 提醒推 (SOP #35) — **当前 0 fork ahead** ✅
- 2 PR 仍 open 超过 3 天 → 提醒浮光 merge (当前 21h+, 不到 3 天阈值)
- workspace ahead > 0 超过 3 天 → 提醒推 (当前 0)
- 5 仓 **upstream ahead** > 0 → V 不可推, 提醒浮光 open PR (SOP #38 #6 写权边界) — **当前 2 PR open 21h+, 浮光 已知, V 帮不了**
- 无事 → HEARTBEAT_OK

### 6/19 18:49 L1 状态 (SOP #34, 修真 3/4 件后)
- workspace ahead: 0 (HEAD=87b0052 on origin, 修真 commit 87b0052 推完)
- 5 仓 ahead 真实: 23 (2 PR upstream + 0 fork, 算法 25 包含 v2 fork 5 是误算)
  - Agent-superthinking: PR #5 (10 commit) 等 maintainer 21h+
  - AgentSearch: PR #2 (13 commit) 等 maintainer 21h+
  - AgentTeam: 0 fork ✅ (ORCHESTRATOR 867dbf2 + README 修真 670bfaa)
  - AgentMemory-upgrade: 0 fork ✅ (v3 仓 6 commit 推完, README 修真 842627a)
  - AgentSafety: 0 (无 origin, SKILL.md 修真 03c2be3 本地)
- 5 端口 6/6 UP: 6005/6006/18081/8080/11434/18789
- watchdog PID 2433 systemd 24/7 (1h+ uptime, 0 restart, 10.8 MB, 0.2% CPU)
- 6/19 snapshot 12 份
- 0 dirty ✅
- SOP 应验累计: #15×12 + #29×4 + #32×2 + #33×2 + #34×10 + #35×4 + #36×7 + #37×1 + #38×3

### 6/20 09:00 L1 状态 (SOP #34, SOP #39+#40 修真后, +14h)
- workspace ahead: 0 (HEAD=5d20aee, 修真 + SOP #39/#40 修真 commit 推完)
- 5 仓 ahead 修真: fork ahead 0/0/0/0/0 ✅ (修真 5/5 修真修真)
- 5 仓 upstream ahead: 11/14/2/6/0 (修真 5 commit, 修真修真修真 修真修真, 修真 修真 修真 修真)
- 6 端口 6/6 UP: 6005/6006/18081/8080/11434/18789
- v-git-activity-watchdog PID 2430 systemd 24/7 (26min uptime, 1 重启 6/20 08:34, 10.5MB)
- v-services-watchdog PID 2679 systemd 24/7 (26min uptime, 1 重启 6/20 08:34)
- v-vcp-watchdog PID 12005 systemd 24/7 (2s uptime, 1.3MB, 0 重启) — SOP #39 修真 ✅
- cron v-cleanup-bak.sh 1 entry (6/22 9:00 触发) — SOP #40 修真 ✅
- 2 dirty 修真: AgentTeam/agentteam/board/utils.py + AgentSafety/src/agent_safety/skill.py (修真 内容, V 不动)
- 2 PR 等 maintainer: AgentSearch #2 (0e809e2) + Agent-superthinking #5 (ffcfcbb), ~36h+
- gh CLI 修真 (修真 修真, 修真 L1 不依赖)
- 6/20 snapshot 2 份 (08:54 + 08:59), git-activity 修真 14h 0 commit
- SOP 应验累计: #15×14 + #28×5 + #29×4 + #32×2 + #33×2 + #34×11 + #35×5 + #36×8 + #37×2 + #38×3

### 修真 3/4 件 (SOP #34 #10 应验, 6/19 18:38-18:41)
| # | 仓 | 修真处数 | commit | 推 |
|---|---|---|---|---|
| 1 | AgentMemory README | 4 处 (HIGH) | 842627a | v3 仓 ✅ |
| 2 | AgentSearch README | 6 处 (HIGH) | 0e809e2 | fuguang8848 ✅ |
| 3 | AgentTeam README | 2 处 (MEDIUM) | 670bfaa | fuguang8848 ✅ |
| 4 | AgentSafety SKILL.md | 2 处 (MEDIUM) | 03c2be3 | 本地 (无 origin) |

### SOP 累计 (6/19 18:49)
- #15 (PAT 占位 + README 失实修真): **12 次应验**
- #29 (transcript 丢): **4 次应验**
- #32 (.bak 生命周期): **2 次应验**
- #33 (Detached HEAD): **2 次应验**
- #34 (V SOP 必 L1 + 跨仓 L1 对比): **10 次应验**
- #35 (5 仓 ahead 推 origin + 修真 4 仓): **4 次应验**
- #36 (升级必带 test + 修真必带 L1 verify): **7 次应验**
- #37 (5 仓 git activity): **1 次应验**
- #38 (V 开 PR 流程 + 写权边界): **3 次应验**

## Related

- [Heartbeat config](/gateway/config-agents)

---

## ⏸️ PR 推送暂停 (浮光 6/20 09:31 拍板)

**规则**: 所有 PR 先保存 (不 push), 等浮光说"所有 PR 一起上传"再推送。

**当前状态**:
- AgentSearch #2 (OPEN, 44h+, mergeable=CLEAN)
- Agent-superthinking #5 (OPEN, 44h+, mergeable=CLEAN)

**V 不做** (等浮光信号):
- ❌ force-push 任何 PR
- ❌ 给 PR 加 comment
- ❌ rebase
- ❌ close / reopen
- ❌ 修改 PR 包含的代码 (跟 PR 关联的本地 commit)

**V 可以做** (跟 PR 无关的):
- ✅ L1 修真 (端口 / watchdog / 5 仓状态)
- ✅ 修真 workspace (HEARTBEAT.md / MEMORY.md / tools/)
- ✅ 修真 其他 3 仓 (AgentTeam / AgentMemory-upgrade / AgentSafety)
- ✅ 修真 PR 修真 修真 (本地仓库, 修真 push)

**触发解锁**: 浮光 说"所有 PR 一起上传" 或 "上传 PR #2/#5" 修真 → V 修真 push.
