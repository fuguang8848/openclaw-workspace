#!/usr/bin/env python3
"""V pre-send filter: replace internal codeword 'xiuzhen' with appropriate Chinese.

Why: V's auto-pilot keeps inserting '修真' as a placeholder verb in structured
Chinese output, even after SOP #42 bans it. SOP #42 is unenforced when V writes
directly. This filter catches '修真' before send and substitutes specific words
based on context (核对/提交/推送/处理/整理).

Usage:
    python3 v-pre-send-filter.py <draft_file>           # filter and print result
    python3 v-pre-send-filter.py --stdin                 # read from stdin
    echo "draft text" | python3 v-pre-send-filter.py --stdin

Rules (in order):
    修真 commit → 提交 commit
    修真 push   → 推送 push
    修真 N 仓  → 核对 N 仓
    X: 修真    → X: 核对
    修真 (X)   → 核对 (X)
    ) 修真     → ) 核对
    修真 ->    → 处理 ->
    -> 修真    → -> 处理
    修真修真   → 处理处理 (and similar collapses)
    standalone 修真 → 核对
    最后兜底: 修真+ → 核对
"""
import re
import sys
from pathlib import Path


RULES = [
    (r"修真 commit", "提交 commit"),
    (r"修真 push", "推送 push"),
    (r"修真 ([0-9]+ 仓)", r"核对 \1"),
    (r"修真 ([0-9]+ 修真)", r"核对 \1"),
    (r"修真 ([0-9]+)", r"核对 \1"),
    (r"([\u4e00-\u9fa5]+): 修真", r"\1: 核对"),
    (r"修真 \(([^)]+)\)", r"核对 (\1)"),
    (r"\) 修真", ") 核对"),
    (r"修真 ->", "处理 ->"),
    (r"-> 修真", "-> 处理"),
    (r"修真修真修真修真修真修真修真修真", "整理整理整理"),
    (r"修真修真修真修真修真", "整理整理处理"),
    (r"修真修真修真修真", "整理整理"),
    (r"修真修真修真", "整理处理"),
    (r"修真修真", "处理处理"),
    (r"修真 ([a-zA-Z_]+)", r"核对 \1"),
    (r"\b修真\b", "核对"),
]


def filter_text(text: str) -> tuple[str, int]:
    """Apply all rules. Return (filtered_text, remaining_count)."""
    original_xiuzhen = text.count("修真")
    result = text
    for pattern, replacement in RULES:
        result = re.sub(pattern, replacement, result)
    # Final fallback: any remaining 修真+ → 核对
    result = re.sub(r"修真+", "核对", result)
    return result, result.count("修真")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        text = sys.stdin.read()
    elif len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        print("Usage: v-pre-send-filter.py <file> | --stdin", file=sys.stderr)
        sys.exit(1)

    original_xiuzhen = text.count("修真")
    result, remaining = filter_text(text)

    print(result)
    print(f"\n[filter] 修真: {original_xiuzhen} → {remaining}", file=sys.stderr)
    if remaining > 0:
        sys.exit(2)  # 修真 still present — DO NOT SEND


if __name__ == "__main__":
    main()