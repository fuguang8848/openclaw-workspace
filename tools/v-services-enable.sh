#!/bin/bash
# v-services-enable.sh — V 端帮浮光 enable systemd 持久化 (V 18:42 写)
#
# 用途: 浮光 sudo 跑这个脚本, 一次性 enable 5 服务的 systemd 守护
# 之前 V 17:50 误判"浮光 09:00 enable 了" — 实际 disabled, 5h 内 ollama/agentteam 死了
# 现在浮光 sudo 跑, V 端验证 (V 没 sudo)
#
# 用法:
#   sudo bash tools/v-services-enable.sh         # 真 enable
#   sudo bash tools/v-services-enable.sh --dry-run  # 试跑
#   bash tools/v-services-enable.sh --verify      # 不 sudo, 只 verify (V 端用)

set -e

UNIT_NAME="v-services-restart.service"
UNIT_PATH="/etc/systemd/system/${UNIT_NAME}"
UNIT_SOURCE="/home/fuguang/.openclaw/workspace/tools/systemd-units/${UNIT_NAME}"

DRY_RUN=false
VERIFY_ONLY=false
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true; shift ;;
    --verify) VERIFY_ONLY=true; shift ;;
  esac
done

echo "════════════════════════════════════════════════════════════"
echo "  V 18:42 systemd enable helper"
echo "  Unit: $UNIT_NAME"
echo "════════════════════════════════════════════════════════════"
echo

# 1. 检查 unit 文件存在
echo "=== 1. unit 文件存在? ==="
if [[ ! -f "$UNIT_SOURCE" ]]; then
  echo "  ✗ unit 源不存在: $UNIT_SOURCE"
  exit 1
fi
echo "  ✓ 源存在: $UNIT_SOURCE"

if [[ ! -f "$UNIT_PATH" ]]; then
  echo "  ✗ /etc/systemd/system/${UNIT_NAME} 不存在, 需要 cp"
  if [[ "$DRY_RUN" == false && "$VERIFY_ONLY" == false ]]; then
    sudo cp "$UNIT_SOURCE" "$UNIT_PATH"
    echo "  ✓ cp OK"
  else
    echo "  (dry-run/verify 跳过 cp)"
  fi
else
  echo "  ✓ /etc/systemd/system/${UNIT_NAME} 存在"
fi
echo

if [[ "$VERIFY_ONLY" == true ]]; then
  echo "=== verify 模式: 不 enable, 只查当前状态 ==="
elif [[ "$DRY_RUN" == true ]]; then
  echo "=== dry-run 模式: 不真启 ==="
else
  # 2. daemon-reload
  echo "=== 2. daemon-reload ==="
  sudo systemctl daemon-reload
  echo "  ✓ daemon-reload OK"
  echo

  # 3. enable (开机自启)
  echo "=== 3. enable --now (开机自启 + 立即启动) ==="
  sudo systemctl enable --now "$UNIT_NAME"
  echo "  ✓ enable --now OK"
  echo

  # 4. start (立即拉起服务)
  echo "=== 4. start (立即拉起 ollama/vcp/agentteam) ==="
  sudo systemctl start "$UNIT_NAME"
  echo "  ✓ start OK"
  echo
fi

# 5. 验证
echo "=== 5. verify (V 11:33 永久教训: 必查) ==="
if command -v systemctl >/dev/null 2>&1; then
  state=$(systemctl is-enabled "$UNIT_NAME" 2>/dev/null || echo "unknown")
  active=$(systemctl is-active "$UNIT_NAME" 2>/dev/null || echo "unknown")
  echo "  is-enabled: $state"
  echo "  is-active: $active"

  if [[ "$state" != "enabled" ]]; then
    echo "  ⚠ Unit 仍非 enabled, 浮光 sudo 可能失败"
  else
    echo "  ✓ Unit 已 enabled"
  fi
fi
echo

# 6. 副作用 5 端口 check
echo "=== 6. 副作用 5 端口 check ==="
for port in 11434 6005 8080 18081 18789; do
  if ss -tln 2>/dev/null | grep -q ":$port "; then
    echo "  ✓ $port OK"
  else
    echo "  ✗ $port FAIL (本脚本会拉起)"
  fi
done

echo
echo "════════════════════════════════════════════════════════════"
echo "  V systemd enable helper 完成 (${TIMESTAMP})"
echo "════════════════════════════════════════════════════════════"
