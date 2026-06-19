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

# 5. 5 仓 ahead 状态 (SOP #35 阈值 20)
for repo in Agent-superthinking AgentSearch AgentTeam AgentMemory-upgrade; do
  cd ~/$repo
  branch=$(git branch --show-current)
  ahead=$(git rev-list --count origin/${branch}..HEAD 2>/dev/null)
  [ -n "$ahead" ] && [ "$ahead" -gt 0 ] && echo "  $repo: ahead=$ahead"
done
```

### 触发级别 (6/19 18:30 更新)
- 端口 DOWN → 立即发 alert
- **watchdog DOWN** → 立即发 alert (systemd 24/7 跑, 不应 DOWN)
- 5 仓 ahead 累计 > 20 → 提醒推 (SOP #35, **当前 23 触发 2 PR 等 maintainer**)
- 2 PR 仍 open 超过 3 天 → 提醒浮光 merge (**当前 21h+ open, 维护者 0 回应**)
- workspace ahead > 0 超过 3 天 → 提醒推 (当前 0)
- 浮光 留 ORCHESTRATOR_COMPONENTS.md 没 commit → 提醒浮光 (AgentTeam dirty=1)
- 无事 → HEARTBEAT_OK

### 6/19 18:30 L1 状态
- workspace ahead: 0 (39 commit 推完 c0a3fca on origin, filter-branch 38 commit 重写 + 1 daily log)
- 5 仓 ahead 累计 23: superthinking 10 / AgentSearch 13 / AgentTeam 0 / AgentMemory-upgrade 0 (v3 仓 5 推完) / AgentSafety 0
- 2 PR: AgentSearch #2 + Agent-superthinking #5 (open 21h+, 维护者 0 回应)
- 5 端口 6/6 UP
- watchdog PID 2433 systemd 24/7 (1h+ uptime)
- 1 dirty: AgentTeam ORCHESTRATOR_COMPONENTS.md (浮光 写, V 不代 commit)
- SOP 应验累计: #15×8 + #29×4 + #32×2 + #33×2 + #34×5 + #35×2 + #36×2 + #37×1 + #38×2

### SOP 累计 (6/19 18:30)
- #15 (PAT 占位): **8 次应验** (6/7 + 6/19 V 自己)
- #29 (transcript 丢): **4 次应验** (6/15 83h + 6/18 8h38m + 6/18 1h + 6/19 20h)
- #32 (.bak 生命周期): **2 次应验**
- #33 (Detached HEAD): **2 次应验**
- #34 (V SOP 必 L1): **5 次应验**
- #35 (5 仓 ahead 推 origin): **2 次应验**
- #36 (升级必带 test): 2 次应验 (6/18 沿用)
- #37 (5 仓 git activity): 1 次应验 (6/18 实装, 6/19 静默期 0 commit)
- #38 (V 开 PR 流程 + 写权边界): **2 次应验**

## Related

- [Heartbeat config](/gateway/config-agents)
