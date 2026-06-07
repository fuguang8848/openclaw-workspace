#!/usr/bin/env bash
# v-push-origin-helper.sh — 5 仓 ahead 推 origin 一键脚本
# V 6/7 07:43 pre-flight verify 后生成
# 
# 前提: 浮光提供 YintaTriss PAT (有 YintaTriss 仓的写权限)
# 用法:
#   1. export YINTA_PAT=ghp_xxxxx (浮光提供)
#   2. bash v-push-origin-helper.sh [repo1 repo2 ...]
#   3. 不传参数 = 默认推 3 仓 (AgentSymphony/AgentSearch/Agent-superthinking)
#
# 风险:
#   - Agent-superthinking 有 8 dirty 文件未提交 (需先 commit 或 stash)
#   - AgentSearch 有 1 untracked: memory/ (需先 .gitignore 或 commit)
#   - 推送是破坏性操作, push 前请 review ahead commits

set -uo pipefail

YINTA_PAT="${YINTA_PAT:-}"
if [ -z "$YINTA_PAT" ]; then
    echo "❌ YINTA_PAT env not set"
    echo "   浮光: export YINTA_PAT=ghp_xxx (YintaTriss 写权限 PAT)"
    echo "   临时测试: export YINTA_PAT=dummy (会得到 403 但能验证流程)"
    exit 1
fi

# 默认推 3 仓
REPOS="${@:-AgentSymphony AgentSearch Agent-superthinking}"

# 路径
WORKSPACE="/home/fuguang"
PUSH_LOG="/tmp/v-push-origin-$(date +%Y%m%d-%H%M).log"

echo "=== v-push-origin-helper.sh ===" | tee "$PUSH_LOG"
echo "  目标仓: $REPOS"
echo "  PAT 前 8 字符: ${YINTA_PAT:0:8}..."
echo "  日志: $PUSH_LOG"
echo "" | tee -a "$PUSH_LOG"

# 1. Pre-flight: dirty 警告
echo "=== Pre-flight: dirty 检查 ===" | tee -a "$PUSH_LOG"
for repo in $REPOS; do
    DIR="$WORKSPACE/$repo"
    if [ ! -d "$DIR" ]; then
        echo "  ❌ $repo: 目录不存在 ($DIR)"
        continue
    fi
    cd "$DIR"
    dirty=$(git status --short 2>/dev/null | wc -l)
    ahead=$(git rev-list --count origin/master..HEAD 2>/dev/null || echo "?")
    local_sha=$(git rev-parse --short HEAD 2>/dev/null)
    origin_sha=$(git rev-parse --short origin/master 2>/dev/null)
    echo "  $repo: HEAD=$local_sha origin=$origin_sha ahead=$ahead dirty=$dirty"
    if [ "$dirty" -gt 0 ]; then
        echo "    ⚠️  $dirty dirty files, push 不会包含, 但建议先 commit/stash:"
        git status --short 2>/dev/null | head -5 | sed 's/^/      /'
    fi
done

# 2. 推
echo "" | tee -a "$PUSH_LOG"
echo "=== Push 阶段 ===" | tee -a "$PUSH_LOG"
for repo in $REPOS; do
    DIR="$WORKSPACE/$repo"
    [ ! -d "$DIR" ] && continue
    cd "$DIR"
    
    # 临时改 origin URL (注入 YINTA_PAT)
    ORIGIN_URL=$(git remote get-url origin)
    # 用 Python 改 URL (避免 sed 对 user:pass@ 路径出错)
    NEW_URL=$(/usr/bin/python3 -c "
import re
url = '''$ORIGIN_URL'''
pat = '''$YINTA_PAT'''
# 移走现有 user:pass@
m = re.match(r'https://(?:[^@]+@)?(.+)', url)
if m:
    rest = m.group(1)
    if 'ghproxy.net' in rest:
        # ghproxy: PAT 作为 user
        new = f'https://{pat}@{rest}'
    else:
        # 直连 GitHub: x-access-token:PAT
        new = f'https://x-access-token:{pat}@{rest}'
    print(new)
else:
    print(url)
")
    
    echo "" | tee -a "$PUSH_LOG"
    echo "--- $repo ---" | tee -a "$PUSH_LOG"
    echo "  old: $ORIGIN_URL" | tee -a "$PUSH_LOG"
    echo "  new: $NEW_URL" | tee -a "$PUSH_LOG"
    
    # 临时改 URL, push 完恢复
    git remote set-url origin "$NEW_URL"
    
    PUSH_RC=0
    git push origin master 2>&1 | tee -a "$PUSH_LOG" || PUSH_RC=${PIPESTATUS[0]}
    if [ "$PUSH_RC" -eq 0 ]; then
        echo "  ✅ $repo pushed" | tee -a "$PUSH_LOG"
    else
        echo "  ❌ $repo push failed (rc=$PUSH_RC)" | tee -a "$PUSH_LOG"
    fi
    
    # 恢复 URL (PAT 不留)
    git remote set-url origin "$ORIGIN_URL"
done

# 3. 后置 verify
echo "" | tee -a "$PUSH_LOG"
echo "=== Post-push verify ===" | tee -a "$PUSH_LOG"
for repo in $REPOS; do
    DIR="$WORKSPACE/$repo"
    [ ! -d "$DIR" ] && continue
    cd "$DIR"
    local_sha=$(git rev-parse --short HEAD 2>/dev/null)
    origin_sha=$(git rev-parse --short origin/master 2>/dev/null)
    ahead=$(git rev-list --count origin/master..HEAD 2>/dev/null)
    if [ "$local_sha" = "$origin_sha" ] && [ "$ahead" = "0" ]; then
        echo "  ✅ $repo: local=$local_sha = origin, ahead=0"
    else
        echo "  ⚠️  $repo: local=$local_sha origin=$origin_sha ahead=$ahead"
    fi
done

echo "" | tee -a "$PUSH_LOG"
echo "=== 完 ===" | tee -a "$PUSH_LOG"
echo "  日志: $PUSH_LOG"
