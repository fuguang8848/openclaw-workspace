#!/usr/bin/env bash
# sync-skills-md.sh — SOP #25 #3 永久教训
# 
# 改完 ~/.openclaw/plugin-skills/$skill/SKILL.md 后, 必须同步到
# ~/.openclaw/skills/$skill/SKILL.md (OpenClaw 实际 scan 路径).
# 
# 背景: OpenClaw 2026.5.22 scan 路径是 ~/.openclaw/skills (managed) + 
# ~/.agents/skills (personal), plugin-skills/ 是 V 自建, OpenClaw 不读.
# 
# 用法:
#   ./sync-skills-md.sh           # 同步全部
#   ./sync-skills-md.sh agent-safety  # 同步单个
#   ./sync-skills-md.sh --check   # 检查差异不复制

set -euo pipefail

PLUGIN_DIR="$HOME/.openclaw/plugin-skills"
SKILLS_DIR="$HOME/.openclaw/skills"

if [ ! -d "$PLUGIN_DIR" ] || [ ! -d "$SKILLS_DIR" ]; then
    echo "❌ plugin-skills 或 skills 目录不存在"
    exit 1
fi

CHECK_ONLY=false
TARGET=""

if [ "${1:-}" = "--check" ]; then
    CHECK_ONLY=true
    shift
fi

if [ -n "${1:-}" ]; then
    TARGET="$1"
fi

synced=0
diff_count=0
missing_count=0

for src in "$PLUGIN_DIR"/*/SKILL.md; do
    [ -f "$src" ] || continue
    skill=$(basename "$(dirname "$src")")
    [ -n "$TARGET" ] && [ "$skill" != "$TARGET" ] && continue

    dst="$SKILLS_DIR/$skill/SKILL.md"

    if [ ! -d "$SKILLS_DIR/$skill" ]; then
        echo "  ⚠️  $skill: skills/ 目录不存在, 跳过"
        missing_count=$((missing_count + 1))
        continue
    fi

    if [ ! -f "$dst" ]; then
        if $CHECK_ONLY; then
            echo "  ❌ $skill: skills/ 缺 SKILL.md"
            missing_count=$((missing_count + 1))
        else
            cp "$src" "$dst"
            echo "  ✅ $skill: 已创建 (plugin-skills → skills)"
            synced=$((synced + 1))
        fi
        continue
    fi

    if diff -q "$src" "$dst" > /dev/null 2>&1; then
        echo "  ✓ $skill: 一致 ($(wc -l < "$src") 行)"
    else
        if $CHECK_ONLY; then
            echo "  ⚠️  $skill: 不一致"
            diff_count=$((diff_count + 1))
        else
            cp "$src" "$dst"
            echo "  ✅ $skill: 同步 ($(wc -l < "$src") 行)"
            synced=$((synced + 1))
        fi
    fi
done

echo ""
if $CHECK_ONLY; then
    echo "检查: 不一致=$diff_count 缺失=$missing_count"
    [ $((diff_count + missing_count)) -gt 0 ] && exit 2
else
    echo "同步完成: 同步=$synced  检查一致=$(($(ls "$PLUGIN_DIR"/*/SKILL.md | wc -l) - synced))"
fi
