```markdown
# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

---

## 6/18 起 — V 主动检查 (SOP #34 L1 + 5 仓 git state)

每次 heartbeat 必跑:
```bash
# 1. SOP #28 L1: 5 端口
for p in 6005 6006 18081 8080 11434; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:$p/ 2>/dev/null || echo "000")
  [ "$code" = "000" ] && echo "🚨 port $p: DOWN"
done

# 2. SOP #37: 5 仓 HEAD activity (since last check)
python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py activity --since "$(date -d '6 hours ago' -Iseconds)" --limit 5

# 3. SOP #28 L1: workspace git state
cd /home/fuguang/.openclaw/workspace && git log --oneline -1
```

### 触发级别
- 端口 DOWN → 立即发 alert
- 5 仓 ahead 累计 > 20 → 提醒推 (SOP #35)
- workspace ahead > 0 超过 3 天 → 提醒推
- 无事 → HEARTBEAT_OK

## Related

- [Heartbeat config](/gateway/config-agents)
