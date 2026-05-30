#!/bin/bash
# OpenClaw Gateway 自动修复脚本
# 当 Gateway 反复崩溃时自动触发

set -e

LOG_DIR="/home/zetton/.openclaw/logs"
FIX_LOG="$LOG_DIR/fix-$(date +%Y-%m-%d_%H-%M-%S).log"
GATEWAY_SERVICE="openclaw-gateway.service"

echo "=== OpenClaw Gateway 自动修复 [$(date)] ===" | tee "$FIX_LOG"

# 1. 收集错误日志
echo -e "\n【收集错误日志】" | tee -a "$FIX_LOG"
journalctl --user -u "$GATEWAY_SERVICE" -n 50 --no-pager | tee -a "$FIX_LOG"

# 2. 检查常见问题
echo -e "\n【诊断问题】" | tee -a "$FIX_LOG"

# 检查端口占用
echo "检查端口 18789..." | tee -a "$FIX_LOG"
if lsof -i :18789 >/dev/null 2>&1; then
    echo "⚠️  端口 18789 被占用" | tee -a "$FIX_LOG"
    lsof -i :18789 | tee -a "$FIX_LOG"
else
    echo "✅ 端口 18789 空闲" | tee -a "$FIX_LOG"
fi

# 检查配置文件
echo -e "\n检查配置文件..." | tee -a "$FIX_LOG"
if [ -f /home/zetton/.openclaw/openclaw.json ]; then
    echo "✅ 配置文件存在" | tee -a "$FIX_LOG"
    # 验证 JSON 格式
    if python3 -c "import json; json.load(open('/home/zetton/.openclaw/openclaw.json'))" 2>/dev/null; then
        echo "✅ JSON 格式正确" | tee -a "$FIX_LOG"
    else
        echo "❌ JSON 格式错误！" | tee -a "$FIX_LOG"
    fi
else
    echo "❌ 配置文件不存在！" | tee -a "$FIX_LOG"
fi

# 检查 Node.js
echo -e "\n检查 Node.js..." | tee -a "$FIX_LOG"
if command -v node >/dev/null 2>&1; then
    NODE_PATH=$(which node)
    NODE_VERSION=$(node --version)
    echo "✅ Node.js: $NODE_VERSION ($NODE_PATH)" | tee -a "$FIX_LOG"
else
    echo "❌ Node.js 未安装！" | tee -a "$FIX_LOG"
fi

# 检查磁盘空间
echo -e "\n检查磁盘空间..." | tee -a "$FIX_LOG"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️  磁盘使用率：${DISK_USAGE}%（过高！）" | tee -a "$FIX_LOG"
else
    echo "✅ 磁盘使用率：${DISK_USAGE}%" | tee -a "$FIX_LOG"
fi

# 检查内存
echo -e "\n检查内存..." | tee -a "$FIX_LOG"
FREE_MEM=$(free -h | grep 内存 | awk '{print $7}')
echo "✅ 可用内存：$FREE_MEM" | tee -a "$FIX_LOG"

# 3. 尝试修复
echo -e "\n【尝试修复】" | tee -a "$FIX_LOG"

# 清理旧日志
echo "清理旧日志文件..." | tee -a "$FIX_LOG"
find /home/zetton/.openclaw/logs -name "*.log" -mtime +7 -delete 2>/dev/null && echo "✅ 已清理 7 天前的日志" | tee -a "$FIX_LOG"

# 清理临时文件
echo "清理临时文件..." | tee -a "$FIX_LOG"
rm -rf /tmp/openclaw/*.tmp 2>/dev/null && echo "✅ 已清理临时文件" | tee -a "$FIX_LOG"

# 4. 重启服务
echo -e "\n【重启服务】" | tee -a "$FIX_LOG"
systemctl --user daemon-reload
systemctl --user restart "$GATEWAY_SERVICE"

sleep 5

# 5. 检查服务状态
echo -e "\n【检查服务状态】" | tee -a "$FIX_LOG"
if systemctl --user is-active --quiet "$GATEWAY_SERVICE"; then
    echo "✅ Gateway 已成功重启！" | tee -a "$FIX_LOG"
    systemctl --user status "$GATEWAY_SERVICE" -l | head -10 | tee -a "$FIX_LOG"
else
    echo "❌ Gateway 重启失败！" | tee -a "$FIX_LOG"
    echo "请手动检查：systemctl --user status $GATEWAY_SERVICE" | tee -a "$FIX_LOG"
    exit 1
fi

echo -e "\n=== 修复完成 [$(date)] ===" | tee -a "$FIX_LOG"
echo "修复日志：$FIX_LOG" | tee -a "$FIX_LOG"
