#!/bin/bash
# daily-check.sh — 每日检查脚本

echo "=== 系统检查 $(date '+%Y-%m-%d %H:%M') ==="

# 磁盘
DISK=$(df -h / --output=used,size,pcent 2>/dev/null | tail -1)
echo "💾 磁盘: $DISK"

# 内存
MEM=$(free -h 2>/dev/null | grep Mem | awk '{print $3 "/" $2}')
echo "🧠 内存: $MEM"

# Gateway 状态
if curl -s --max-time 3 http://127.0.0.1:18789 >/dev/null 2>&1; then
    echo "✅ Gateway: 在线"
else
    echo "❌ Gateway: 离线"
fi

# WinApps VM 状态
VM_STATE=$(sudo -u agent virsh --connect qemu:///system list --state-running 2>/dev/null | grep WinApps || echo "")
if [ -n "$VM_STATE" ]; then
    echo "🪟 WinApps: 运行中"
else
    echo "🪟 WinApps: 未运行"
fi

echo "---"
python3 ~/.openclaw/workspace/tools/daily-brief.py
