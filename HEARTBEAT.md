```markdown
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

### 触发级别 (6/19 更新)
- 端口 DOWN → 立即发 alert
- **watchdog DOWN** → 立即发 alert (systemd 24/7 跑, 不应 DOWN)
- 5 仓 ahead 累计 > 20 → 提醒推 (SOP #35)
- 2 PR 仍 open 超过 3 天 → 提醒浮光 merge
- workspace ahead > 0 超过 3 天 → 提醒推
- 无事 → HEARTBEAT_OK

### SOP 累计 (6/18 收尾)
- #32 (.bak 生命周期): 立碑
- #33 (Detached HEAD): 立碑
- #34 (V SOP 必 L1): 10 次应验
- #35 (5 仓 ahead 推 origin): 立碑
- #36 (升级必带 test): 6 test minimum
- #37 (5 仓 git activity): 3 次应验, systemd 限制解
- #38 (V 开 PR 流程): 3 次应验, 6 步流程

## Related

- [Heartbeat config](/gateway/config-agents)
