# 01-配置 — 系统核心配置

## Gateway
```
ws://127.0.0.1:18789
systemd: openclaw-gateway.service
绑定: loopback
```

## 搜索配置
| 引擎 | URL | 用途 | 状态 |
|------|-----|------|------|
| 百度搜索 | www.baidu.com | 国内搜索 | ⚠️ 被安全验证拦截 |
| Tavily | api.tavily.com | 调研/分析 | ⚠️ 国际 HTTPS 不通 |
| SearXNG | localhost:8080 | 搜索聚合 | ⚠️ 未部署 |

**网络现状:**
- 国际 HTTPS 站点（GitHub、DuckDuckGo 等）全部超时
- Docker 因 Watt Toolkit 代理（127.0.0.1:26561）不通无法拉镜像
- 百度搜索触发安全验证

## 定时任务
| 名称 | 时间 | 触发 | 状态 |
|------|------|------|------|
| 每日简报 | 09:00 | systemEvent → main | ✅ |
| 每日记忆整理 | 23:00 | systemEvent → main | ✅ |
| 每周回顾 | 周一 09:00 | systemEvent → main | ✅ |
| 每周配置备份 | 周一 09:00 | agentTurn → isolated | ✅ |
