#!/bin/bash
# v-push-helper.sh — V 端帮浮光 push 4 仓 force-with-lease (V 18:42 写)
#
# 用途: 浮光不能手敲 4 仓 push 命令, 这个脚本一键做完
# 安全: --force-with-lease (不强推, 看远端是否有新 commit 阻止)
# 备份: push 前自动 tag local 仓, 万一错能回滚
#
# 用法:
#   bash tools/v-push-helper.sh              # 推 4 仓
#   bash tools/v-push-helper.sh --dry-run    # 试跑, 不真推
#   bash tools/v-push-helper.sh --only workspace  # 只推 workspace
#   bash tools/v-push-helper.sh --skip-tag   # 不打 tag (紧急时)

set -e

REPOS=(
  "workspace:/home/fuguang/.openclaw/workspace"
  "superthinking:/home/fuguang/Agent-superthinking"
  "AgentMemory:/home/fuguang/AgentMemory"
  "AgentSymphony:/home/fuguang/AgentSymphony"
)

DRY_RUN=false
ONLY=""
SKIP_TAG=false
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true; shift ;;
    --only) ONLY="$2"; shift 2 ;;
    --skip-tag) SKIP_TAG=true; shift ;;
  esac
done

echo "════════════════════════════════════════════════════════════"
echo "  V 18:42 push helper — ${DRY_RUN:+DRY-RUN }${#REPOS[@]} 仓"
echo "════════════════════════════════════════════════════════════"
echo

# 仓状态预览
for entry in "${REPOS[@]}"; do
  name="${entry%%:*}"
  path="${entry##*:}"
  if [[ -n "$ONLY" && "$name" != "$ONLY" ]]; then continue; fi
  ahead=$(git -C "$path" rev-list --count origin/master..HEAD 2>/dev/null || echo "?")
  mod=$(git -C "$path" status -s 2>/dev/null | wc -l)
  branch=$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null)
  echo "  $name (branch=$branch): ahead=$ahead uncommitted=$mod"
done
echo

if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY-RUN] 不真推, 上面是预览"
  exit 0
fi

# 推前 tag backup
if [[ "$SKIP_TAG" == false ]]; then
  echo "=== 1. 打 tag 备份 (pre-push-${TIMESTAMP}) ==="
  for entry in "${REPOS[@]}"; do
    name="${entry%%:*}"
    path="${entry##*:}"
    if [[ -n "$ONLY" && "$name" != "$ONLY" ]]; then continue; fi
    cd "$path"
    if git tag "pre-push-${TIMESTAMP}" 2>/dev/null; then
      echo "  ✓ $name tagged: pre-push-${TIMESTAMP}"
    else
      echo "  ⚠ $name tag 失败 (可能 tag 已存在)"
    fi
  done
  echo
fi

# 推
echo "=== 2. force-with-lease push 4 仓 ==="
for entry in "${REPOS[@]}"; do
  name="${entry%%:*}"
  path="${entry##*:}"
  if [[ -n "$ONLY" && "$name" != "$ONLY" ]]; then continue; fi
  cd "$path"
  branch=$(git rev-parse --abbrev-ref HEAD)
  ahead=$(git rev-list --count origin/${branch}..HEAD 2>/dev/null || echo "?")
  if [[ "$ahead" == "0" ]]; then
    echo "  - $name: ahead=0, 跳过"
    continue
  fi
  echo "  → $name (branch=$branch, ahead=$ahead) ..."
  if git push origin "$branch" --force-with-lease 2>&1; then
    echo "  ✓ $name pushed"
  else
    echo "  ✗ $name push 失败 (远端有新 commit? 用 git fetch 看)"
  fi
  echo
done

# 副作用 5 端口 check
echo "=== 3. 副作用 5 端口 check (V 11:33 永久) ==="
for port in 11434 6005 8080 18081 18789; do
  if ss -tln 2>/dev/null | grep -q ":$port "; then
    echo "  ✓ $port OK"
  else
    echo "  ✗ $port FAIL"
  fi
done

echo
echo "════════════════════════════════════════════════════════════"
echo "  V push helper 完成 (${TIMESTAMP})"
echo "════════════════════════════════════════════════════════════"
