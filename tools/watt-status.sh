#!/bin/bash
# watt-status.sh — Watt Toolkit 状态检测（双检查：pgrep + 端口监听）
#
# 用法: ./watt-status.sh
# 退出码: 0=OK, 1=DOWN, 2=ZOMBIE
# 输出格式: 状态行 + 进程详情

set -e

USER_NAME=${SUDO_USER:-$USER}
PROXY_PORTS_REGEX=":(26561|44329|7890) "

# 1. Watt 主进程
WATT_PIDS=$(pgrep -u "$USER_NAME" -f "assemblies/Steam" 2>/dev/null | tr '\n' ' ' || true)
WATT_COUNT=$(echo "$WATT_PIDS" | wc -w)

# 2. Kestrel reverse proxy 端口（443/80 总是启的）
KESTREL_LISTEN=$(ss -tlnp 2>/dev/null | grep -cE ":(443|80) " || true)

# 3. 系统代理端口（26561/44329/7890，要 GUI 启"启用代理"才有）
PROXY_LISTEN=$(ss -tlnp 2>/dev/null | grep -cE "$PROXY_PORTS_REGEX" || true)

# 4. 判定
if [ "$WATT_COUNT" -eq 0 ]; then
  echo "DOWN: Watt 进程不在"
  echo "  → 启动: ./tools/watt-start.sh"
  exit 1
elif [ "$KESTREL_LISTEN" -gt 0 ] && [ "$PROXY_LISTEN" -gt 0 ]; then
  echo "OK: Watt 跑着 + Kestrel reverse proxy :443/:80 + 系统代理端口 $PROXY_LISTEN 个"
  ps -o pid,ppid,pcpu,pmem,etime,comm -p $WATT_PIDS 2>/dev/null | head -10
  exit 0
elif [ "$KESTREL_LISTEN" -gt 0 ]; then
  echo "ZOMBIE: Watt 跑着 (pid=$WATT_PIDS) + Kestrel listening, 但系统代理端口未开"
  echo "  → 在 Watt GUI 启用代理（托盘图标 → 启用代理）"
  ps -o pid,ppid,pcpu,pmem,etime,comm -p $WATT_PIDS 2>/dev/null | head -10
  exit 2
else
  echo "BOOTING: Watt 进程在但 Kestrel 还没 listening（等几秒）"
  ps -o pid,ppid,pcpu,pmem,etime,comm -p $WATT_PIDS 2>/dev/null | head -10
  exit 3
fi
