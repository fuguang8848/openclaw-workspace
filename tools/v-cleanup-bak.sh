#!/bin/bash
# v-cleanup-bak.sh — SOP #32 候选配套
# 清 7 天前 .bak-pre-sop16 文件 (dry-run 优先)

set -e
DAYS=${1:-7}
DRY_RUN=${2:-true}

echo "=== v-cleanup-bak.sh ==="
echo "目标: $DAYS 天前的 .bak-pre-sop16 文件"
echo "模式: $([ "$DRY_RUN" = "true" ] && echo "DRY-RUN (加 'false' 真删)" || echo "真删")"
echo ""

# 扫 /home/fuguang 下所有 .bak-pre-sop16 文件
files=$(find /home/fuguang -name "*.bak-pre-sop16*" -mtime +$DAYS 2>/dev/null)
count=$(echo "$files" | grep -c . || echo 0)

echo "找到 $count 个 $DAYS 天前的 .bak-pre-sop16 文件"
echo ""

if [ "$count" -eq 0 ]; then
  echo "无需清理 ✅"
  exit 0
fi

echo "=== 列表 ==="
echo "$files" | head -20
echo ""
[ "$count" -gt 20 ] && echo "... 还有 $((count-20)) 个"
echo ""

if [ "$DRY_RUN" = "true" ]; then
  echo "DRY-RUN 模式, 不会真删"
  echo "真删: bash $0 $DAYS false"
else
  echo "=== 真删中... ==="
  echo "$files" | while read f; do
    [ -f "$f" ] && rm -v "$f"
  done
  echo "✅ 删完"
fi
