#!/bin/bash
# v-push-helper.sh — V 端帮浮光 push 6 仓 force-with-lease (V 6/5 改)
#
# 用途: 浮光不能手敲 6 仓 push 命令, 这个脚本一键做完
# 安全: --force-with-lease (不强推, 看远端是否有新 commit 阻止)
# 备份: push 前自动 tag local 仓, 万一错能回滚
# non-interactive: GIT_TERMINAL_PROMPT=0 避免卡在 username
#
# 用法:
#   bash tools/v-push-helper.sh              # 推 6 仓
#   bash tools/v-push-helper.sh --dry-run    # 试跑, 不真推
#   bash tools/v-push-helper.sh --only workspace  # 只推 1 仓
#   bash tools/v-push-helper.sh --skip-tag   # 不打 tag (紧急时)
#
# V 6/5 修复:
#   1) 4 仓 → 6 仓 (加 AgentSearch / AgentTeam)
#   2) 每个仓指定 push_remote (origin / fuguang)
#   3) non-interactive (ghproxy 推 anonymous 不卡 username)
#   4) workspace 远端查不出的 fallback
#   5) V 11:22 ahead=? 误判改: 显式报 "无 upstream" 而非 ?

set -e
export GIT_TERMINAL_PROMPT=0  # 关键: ghproxy 推时不卡 username

# 仓列表: name:path:push_remote
# push_remote: 默认 origin, 错指上游时用 fuguang (浮光 fork remote)
REPOS=(
  "workspace:/home/fuguang/.openclaw/workspace:origin"
  "superthinking:/home/fuguang/Agent-superthinking:fuguang"
  "AgentMemory:/home/fuguang/AgentMemory:fuguang"
  "AgentSymphony:/home/fuguang/AgentSymphony:fuguang"
  "AgentSearch:/home/fuguang/AgentSearch:fuguang"
  "AgentTeam:/home/fuguang/AgentTeam:origin"
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
echo "  V 6/5 push helper — ${DRY_RUN:+DRY-RUN }${#REPOS[@]} 仓"
echo "════════════════════════════════════════════════════════════"
echo

# 仓状态预览
for entry in "${REPOS[@]}"; do
  name="${entry%%:*}"
  rest="${entry#*:}"
  path="${rest%%:*}"
  push_remote="${rest##*:}"
  [[ -n "$ONLY" && "$name" != "$ONLY" ]] && continue

  if [[ ! -d "$path" ]]; then
    echo "  ✗ $name: 路径不存在 ($path)"
    continue
  fi

  branch=$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null)
  remote_url=$(git -C "$path" remote get-url "$push_remote" 2>/dev/null || echo "NO_REMOTE")
  if [[ "$remote_url" == "NO_REMOTE" ]]; then
    echo "  ✗ $name: 缺 $push_remote remote (run: git remote add $push_remote <url>)"
    continue
  fi

  # V 6/5 修复: 显式报 "无 upstream" 而非 ?
  upstream=$(git -C "$path" rev-parse --abbrev-ref "@{u}" 2>/dev/null || echo "")
  if [[ -z "$upstream" ]]; then
    ahead="NO_UPSTREAM"
  else
    ahead=$(git -C "$path" rev-list --count "@{u}..HEAD" 2>/dev/null || echo "?")
  fi
  mod=$(git -C "$path" status -s 2>/dev/null | wc -l)
  echo "  $name (branch=$branch, push=$push_remote): ahead=$ahead uncommitted=$mod"
done
echo

[[ "$DRY_RUN" == true ]] && { echo "[DRY-RUN] 不真推, 上面是预览"; exit 0; }

# 推前 tag backup
if [[ "$SKIP_TAG" == false ]]; then
  echo "=== 1. 打 tag 备份 (pre-push-${TIMESTAMP}) ==="
  for entry in "${REPOS[@]}"; do
    name="${entry%%:*}"
    rest="${entry#*:}"
    path="${rest%%:*}"
    [[ -n "$ONLY" && "$name" != "$ONLY" ]] && continue
    [[ ! -d "$path" ]] && continue
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
echo "=== 2. force-with-lease push 6 仓 ==="
for entry in "${REPOS[@]}"; do
  name="${entry%%:*}"
  rest="${entry#*:}"
  path="${rest%%:*}"
  push_remote="${rest##*:}"
  [[ -n "$ONLY" && "$name" != "$ONLY" ]] && continue
  [[ ! -d "$path" ]] && continue
  cd "$path"

  remote_url=$(git remote get-url "$push_remote" 2>/dev/null || echo "")
  if [[ -z "$remote_url" ]]; then
    echo "  ✗ $name: 缺 $push_remote remote, 跳过"
    continue
  fi

  branch=$(git rev-parse --abbrev-ref HEAD)
  upstream=$(git rev-parse --abbrev-ref "@{u}" 2>/dev/null || echo "")
  if [[ -z "$upstream" ]]; then
    echo "  - $name: 无 upstream, 跳过 (用 git push -u $push_remote $branch 首次推送)"
    continue
  fi

  ahead=$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo "?")
  if [[ "$ahead" == "0" ]]; then
    echo "  - $name: ahead=0, 跳过"
    continue
  fi

  echo "  → $name (branch=$branch, push=$push_remote, ahead=$ahead) ..."
  if git push "$push_remote" "$branch" --force-with-lease 2>&1 | tail -3; then
    echo "  ✓ $name pushed"
  else
    echo "  ✗ $name push 失败 (远端有新 commit? 用 git fetch $push_remote 看)"
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
