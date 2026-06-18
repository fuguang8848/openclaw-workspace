#!/usr/bin/env bash
# v-git-activity-watchdog.sh — SOP #37 实施
# 5 仓 git activity 检测 + activity log + 自动 save snapshot
# 每 30s 一圈, 跟 v-services-watchdog.sh 同周期 (防 systemd race, 用相同 GRACE_PERIOD_S)

set -e

LOG_PREFIX="[v-git-activity]"
LOG_FILE="/tmp/v-git-activity-watchdog.log"
SNAPSHOT_BIN="/home/fuguang/.openclaw/workspace/tools/v-snapshot.py"
MODE="${1:-normal}"  # grace | normal

echo "$(date +%H:%M:%S) ${LOG_PREFIX} started, mode=${MODE}" >> "${LOG_FILE}"

# Grace period: 启动后 60s 内只 check 不 save (防 systemd 拉起时子进程重启竞态)
# 跟 v-services-watchdog.sh 同步 (SOP #30 grace period)
GRACE_PERIOD_S=60
START_TS=$(date +%s)

while true; do
    ELAPSED=$(( $(date +%s) - START_TS ))
    if [ "${ELAPSED}" -lt "${GRACE_PERIOD_S}" ]; then
        if [ "${MODE}" != "grace" ]; then
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} grace period, check-only" >> "${LOG_FILE}"
            MODE="grace"
        fi
    else
        if [ "${MODE}" != "normal" ]; then
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} grace over, switch to normal" >> "${LOG_FILE}"
            MODE="normal"
        fi
    fi

    # 调用 v-snapshot.py watch
    # exit 0 = 无活动, exit 1 = 检测到活动
    if "${SNAPSHOT_BIN}" watch >> "${LOG_FILE}" 2>&1; then
        # no activity, sleep
        sleep 30
    else
        # activity detected, save full snapshot + notify
        echo "$(date +%H:%M:%S) ${LOG_PREFIX} activity detected, saving snapshot" >> "${LOG_FILE}"
        V_TRIGGER=git_activity "${SNAPSHOT_BIN}" save >> "${LOG_FILE}" 2>&1

        # 通知 V: 通过写 systemEvent 风格的 log + 推 snapshot
        # 当前 OpenClaw 没暴露 hook 给外部脚本, 用 tail 监控 log 文件
        # V 在 session 启动时读 git-activity.jsonl (via v-snapshot.py activity)
        if [ "${MODE}" = "normal" ]; then
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} 🚨 ALERT: git activity, snapshot saved" >> "${LOG_FILE}"
        fi

        sleep 30
    fi
done
