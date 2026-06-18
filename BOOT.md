# BOOT.md - Gateway Startup Checklist (boot-md hook)

每次 gateway 重启时由 `🚀 boot-md` hook 自动执行。

目标：**让 V 失忆后能从快照快速恢复上下文**。

## 必跑项

```bash
# 1. 强制存一份最新 snapshot (transcript 可能丢了, 但服务状态是新鲜的)
python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py save

# 2. 健康检查
python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py status

# 3. SOP #37: 检查 5 仓 git activity since last snapshot
#    V 启动时报告 6/16-6/18 推了哪些 commit, 避免 SOP #29 起源的 83h 滞后
python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py activity --since "2026-06-15T22:00:00" --limit 20
```

## 检查项

- [ ] 5 个 V 服务 up (VCPToolBox / adminServer / symphony / agentteam / ollama)
- [ ] watchdog 在跑 (30s 循环)
- [ ] snapshot 写入成功
- [ ] memory 目录最新文件是今天
- [ ] **5 仓 git activity** — 自上次 snapshot 后谁推了什么 (SOP #37)

## 不跑项

- ❌ 不要重启任何服务（boot-md 只做状态，不是修复）
- ❌ 不要发任何消息给浮光（boot-md 是 silent 启动检查）
- ❌ 不要读 MEMORY.md（懒加载，按需）

## 失败处理

如果 snapshot save 失败：
- 检查 `.v-snapshot/` 目录权限
- 检查 workspace 是否可写
- 不阻塞 gateway 启动 — 警告即可

## SOP #37 设计

- `v-snapshot.py watch` — 30s/圈 检测 5 仓 HEAD SHA 变化, exit 1 = 活动
- `v-snapshot.py activity` — 读 git-activity.jsonl, `--since ISO --limit N`
- `v-snapshot.py git-state` — 当前 5 仓 SHA/branch/ahead 快照
- `tools/v-git-activity-watchdog.sh` — systemd / nohup 跑, grace 60s 防 race (同 SOP #30)
- 存储: `.v-snapshot/git-state.json` (last known) + `.v-snapshot/git-activity.jsonl` (append-only)
- V 启动: BOOT.md 自动查 activity since last snapshot, surface 给 浮光

