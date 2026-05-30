#!/bin/bash
# OpenClaw Workspace 备份脚本
# 备份频率：每日一次
# 备份内容：memory/*.md, MEMORY.md, AGENTS.md, SOUL.md

BACKUP_DIR="$HOME/.openclaw/backup"
WORKSPACE="$HOME/.openclaw/workspace"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/backup.log"

# 目标文件
FILES=(
    "MEMORY.md"
    "AGENTS.md"
    "SOUL.md"
    "USER.md"
    "IDENTITY.md"
    "TOOLS.md"
)

echo "[$(date)] Starting backup..." >> "$LOG_FILE"

# 创建带时间戳的备份目录
mkdir -p "${BACKUP_DIR}/${TIMESTAMP}"

# 备份根目录文件
for file in "${FILES[@]}"; do
    if [ -f "${WORKSPACE}/${file}" ]; then
        cp "${WORKSPACE}/${file}" "${BACKUP_DIR}/${TIMESTAMP}/"
        echo "  ✓ Backed up ${file}" >> "$LOG_FILE"
    fi
done

# 备份 memory 目录
if [ -d "${WORKSPACE}/memory" ]; then
    mkdir -p "${BACKUP_DIR}/${TIMESTAMP}/memory"
    find "${WORKSPACE}/memory" -name "*.md" -exec cp {} "${BACKUP_DIR}/${TIMESTAMP}/memory/" \; 2>/dev/null
    echo "  ✓ Backed up memory/*.md" >> "$LOG_FILE"
fi

# 清理 7 天前的备份
find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
echo "  ✓ Cleaned old backups (>7 days)" >> "$LOG_FILE"

echo "[$(date)] Backup completed: ${TIMESTAMP}" >> "$LOG_FILE"
echo "Backup done: ${TIMESTAMP}"