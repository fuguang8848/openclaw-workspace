#!/usr/bin/env bash
# v-vcp-watchdog.sh — SOP #39 实施
# VCPToolBox 健康深度检测 (6005 VCP server + 6006 admin)
# v-services-watchdog.sh 检 5 端口 UP/DOWN, 本脚本检 VCP 业务健康
# 每 60s 一圈 (比 v-services-watchdog 慢, 因为是深度检测)

set -e

LOG_PREFIX="[v-vcp-watchdog]"
LOG_FILE="/tmp/v-vcp-watchdog.log"

ADMIN_AUTH="admin:vcp_admin_2026"

# VCPToolBox 端口
VCP_PORT=6005
ADMIN_PORT=6006

echo "$(date +%H:%M:%S) ${LOG_PREFIX} started" >> "${LOG_FILE}"

# 失败计数 (连续失败 N 次才报警, 避免网络抖动误报)
FAIL_COUNT=0
ALERT_THRESHOLD=3

while true; do
    # 1. VCP server (6005) — 期望 401 (无 auth), 不期望 000/500/503
    vcp_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:${VCP_PORT}/ 2>/dev/null || echo "000")
    
    # 2. AdminPanel (6006) — 期望 302 (redirect to login), 不期望 000/500
    admin_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:${ADMIN_PORT}/ 2>/dev/null || echo "000")

    # 健康判定
    # 6005: 401 OK, 200 OK (e.g. open endpoints), 503/500 NOT OK
    # 6006: 302 OK (redirect), 200 OK (login page), 503/500 NOT OK
    vcp_ok=false
    [ "$vcp_code" = "401" ] || [ "$vcp_code" = "200" ] && vcp_ok=true
    
    admin_ok=false
    [ "$admin_code" = "302" ] || [ "$admin_code" = "200" ] && admin_ok=true

    if $vcp_ok && $admin_ok; then
        if [ "$FAIL_COUNT" -gt 0 ]; then
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} recovered (fail_count was $FAIL_COUNT)" >> "${LOG_FILE}"
        fi
        FAIL_COUNT=0
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "$(date +%H:%M:%S) ${LOG_PREFIX} FAIL vcp=${vcp_code} admin=${admin_code} (count=${FAIL_COUNT}/${ALERT_THRESHOLD})" >> "${LOG_FILE}"
        
        if [ "$FAIL_COUNT" -ge "$ALERT_THRESHOLD" ]; then
            # 连续失败 ≥ 阈值 → 触发 /admin_api/server/restart (它有 adminAuth)
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} ALERT: triggering admin restart" >> "${LOG_FILE}"
            restart_result=$(curl -s --max-time 5 -u "${ADMIN_AUTH}" \
                -X POST http://127.0.0.1:${VCP_PORT}/admin_api/server/restart \
                -H "Content-Type: application/json" -d '{}' 2>&1 || echo "restart_failed")
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} restart response: ${restart_result}" >> "${LOG_FILE}"
            FAIL_COUNT=0  # 重置, 让 watchdog 自己重新拉起
            sleep 30      # 给重启留时间
        fi
    fi

    sleep 60
done
