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
    local name=$1 port=$2 cmd=$3 cwd=$4
    if ss -tln | grep -q ":${port} "; then
        echo "$(date +%H:%M:%S) ${LOG_PREFIX} ${name} :${port} UP"
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
}

while true; do
    check_and_start ollama ${OLLAMA_PORT} "/home/fuguang/bin/ollama serve" /home/fuguang
    check_and_start vcp ${VCP_PORT} "node server.js" /home/fuguang/VCPToolBox
    check_and_start vcp-admin ${VCP_ADMIN_PORT} "node adminServer.js" /home/fuguang/VCPToolBox
    check_and_start agentteam ${AGENTTEAM_PORT} "/home/fuguang/.local/bin/agentteam board serve --port 8080" /home/fuguang/AgentTeam
    check_and_start symphony ${SYMPHONY_PORT} "python3 -m server.symphony_server" /home/fuguang/agent-symphony
    sleep 30
done
