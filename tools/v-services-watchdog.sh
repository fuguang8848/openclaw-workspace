#!/usr/bin/env bash
# V services watchdog — 常驻守护, 任何服务挂掉就拉起
# 14:21 替换原 systemd unit 内嵌的 curl + setsid 逻辑
# 14:21 根因: 之前用 root 跑, 缺 user pip 路径 → agentteam/fastapi 找不到

set -u

LOG_PREFIX="[v-watchdog]"
OLLAMA_PORT=11434
VCP_PORT=6005
VCP_ADMIN_PORT=6006
AGENTTEAM_PORT=8080
SYMPHONY_PORT=18081

check_and_start() {
    local name=$1 port=$2 cmd=$3 cwd=$4 mode="${5:-normal}"
    if ss -tln | grep -q ":${port} "; then
        echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} UP"
    else
        if [ "${mode}" = "grace" ]; then
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} DOWN, grace-skip (let systemd settle)"
        else
            echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} DOWN, restarting..."
            cd "${cwd}"
            setsid nohup ${cmd} > "/tmp/v-${name}.log" 2>&1 < /dev/null &
            disown
            sleep 2
            if ss -tln | grep -q ":${port} "; then
                echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} restarted ✅"
            else
                echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} FAILED to restart, see /tmp/v-${name}.log"
            fi
        fi
    fi
}

# Grace period: 启动后 60s 内只 check 不 restart (防 systemd 拉起时子进程重启竞态)
GRACE_PERIOD_S=60
START_TS=$(date +%s)

# 每 N 圈 save 一次 v-snapshot (5 分钟一次，30s/圈 × 10 = 300s)
SNAPSHOT_EVERY_N=10
SNAPSHOT_COUNTER=0

while true; do
    ELAPSED=$(( $(date +%s) - START_TS ))
    if [ "${ELAPSED}" -lt "${GRACE_PERIOD_S}" ]; then
        MODE="grace"
    else
        MODE="normal"
    fi

    check_and_start ollama ${OLLAMA_PORT} "/home/fuguang/bin/ollama serve" /home/fuguang ${MODE}
    check_and_start vcp ${VCP_PORT} "node server.js" /home/fuguang/VCPToolBox ${MODE}
    check_and_start vcp-admin ${VCP_ADMIN_PORT} "node adminServer.js" /home/fuguang/VCPToolBox ${MODE}
    check_and_start agentteam ${AGENTTEAM_PORT} "/home/fuguang/.local/bin/agentteam board serve --port 8080" /home/fuguang/AgentTeam ${MODE}
    check_and_start symphony ${SYMPHONY_PORT} "python3 -m server.symphony_server" /home/fuguang/agent-symphony ${MODE}

    # v-snapshot 被动收集 (防 transcript 丢失 → V 失忆)
    SNAPSHOT_COUNTER=$((SNAPSHOT_COUNTER + 1))
    if [ "${SNAPSHOT_COUNTER}" -ge "${SNAPSHOT_EVERY_N}" ]; then
        SNAPSHOT_COUNTER=0
        V_TRIGGER=watchdog_5min python3 /home/fuguang/.openclaw/workspace/tools/v-snapshot.py save >> /tmp/v-snapshot.log 2>&1
    fi

    sleep 30
done
