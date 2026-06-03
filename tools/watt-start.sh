#!/bin/bash
# watt-start.sh — 启 Watt Toolkit GUI 模式（带 Xwayland XAUTHORITY 修复）
#
# 用法: ./watt-start.sh
# 前置: GNOME Wayland session 浮光已登录（display :0, session 4）
# 已知坑:
#   - Watt 走 Avalonia X11（不走 Wayland 原生），必须给 XAUTHORITY
#   - GNOME Wayland 下 Xauthority 在 /run/user/1000/.mutter-Xwaylandauth.* 临时文件
#   - 没 XAUTHORITY 时 .NET 抛 XOpenDisplay failed
#   - MinimizeOnStartup=true (默认) 启后窗口最小化到托盘，看不到不一定是没启
#   - 不要用 pkill -f "Steam++" 自杀模式——会匹配到自己的 exec 命令行

set -e

USER_NAME=${SUDO_USER:-$USER}
HOME_DIR=$(getent passwd "$USER_NAME" | cut -d: -f6)

echo "[watt-start] user=$USER_NAME home=$HOME_DIR"

# 1. 找 Xwayland Xauthority
XAUTH_FILE=$(ls -t /run/user/1000/.mutter-Xwaylandauth.* 2>/dev/null | head -1)
if [ -z "$XAUTH_FILE" ]; then
  echo "[watt-start] ✗ 找不到 /run/user/1000/.mutter-Xwaylandauth.*"
  echo "[watt-start]   → 检查 GNOME Wayland session 是否正常 (loginctl show-session)"
  exit 1
fi
echo "[watt-start] XAUTHORITY=$XAUTH_FILE"

# 2. 杀旧 Watt（精准 pid，避免自杀）
KILLED=0
for p in $(pgrep -u "$USER_NAME" -f "Steam\+\+\.sh|assemblies/Steam" 2>/dev/null || true); do
  cmdline=$(cat /proc/$p/cmdline 2>/dev/null | tr '\0' ' ' || true)
  if echo "$cmdline" | grep -qE "Steam\+\+\.sh|assemblies/Steam"; then
    kill -9 "$p" 2>/dev/null && KILLED=$((KILLED+1)) && echo "[watt-start]   killed pid $p"
  fi
done
sleep 1

# 3. 启新 Watt（pty/setsid + 完整 env）
nohup "$HOME_DIR/WattToolkit/Steam++.sh" \
  </dev/null >"$HOME_DIR/WattToolkit/watt-gui.log" 2>&1 &
disown
echo "[watt-start] 启动中... 3 秒后检查"

sleep 3

# 4. 验证
WATT_PIDS=$(pgrep -u "$USER_NAME" -f "Steam\+\+" 2>/dev/null | tr '\n' ' ')
if [ -n "$WATT_PIDS" ]; then
  echo "[watt-start] ✓ Watt 进程:"
  ps -o pid,ppid,pcpu,pmem,etime,comm -p $WATT_PIDS 2>/dev/null | head -10
  echo ""
  echo "[watt-start] 提示:"
  echo "  - 窗口默认最小化到托盘（MinimizeOnStartup=true）"
  echo "  - 系统托盘找 Watt 图标（或按 Super 键看 Running Apps）"
  echo "  - 在 GUI 里点 '启用代理' 才会监听 :26561"
  echo "  - 检查代理端口: ./tools/watt-status.sh"
else
  echo "[watt-start] ✗ Watt 进程没起来，看日志:"
  tail -20 "$HOME_DIR/WattToolkit/watt-gui.log" 2>/dev/null
  exit 1
fi
