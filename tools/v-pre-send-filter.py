#!/usr/bin/env python3
"""V pre-send filter: detect & remove 'xiuzhen' leaks from user-facing messages.

Problem: V's auto-pilot defaults to '▢▢' (xiū zhēn) as a placeholder verb when
writing structured Chinese output. SOP #42 (ban) was unenforced when V writes
directly. This filter catches 'xiuzhen' patterns in messages intended for 浮光.

NEW STRATEGY (after 浮光 10:58 feedback):
- Don't blindly replace ▢▢ with 核对. That just produces "核对 核对 核对" gibberish.
- If ▢▢ appears in user-facing text, FAIL (exit 2) and force V to rewrite.
- V must write natural Chinese directly. The filter is a safety net, not a translator.

For INTERNAL docs (MEMORY.md, HEARTBEAT.md, daily memory), ▢▢ is allowed —
it stays in the SOP #42 meta-discussion section. Filter only runs on user-facing
output (webchat replies, PR descriptions, commit messages sent to 浮光).
"""
import re
import sys
from pathlib import Path


def detect_xiuzhen(text: str) -> tuple[int, list[str]]:
    """Return (count, list of matches with surrounding context)."""
    matches = []
    for m in re.finditer(r"▢▢", text):
        start = max(0, m.start() - 5)
        end = min(len(text), m.end() + 5)
        ctx = text[start:end].replace("\n", " ")
        matches.append(ctx)
    return len(matches), matches


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        text = sys.stdin.read()
    elif len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        print("Usage: v-pre-send-filter.py <file> | --stdin", file=sys.stderr)
        sys.exit(1)

    count, matches = detect_xiuzhen(text)

    if count > 0:
        print(f"\n[BLOCK] '▢▢' detected: {count} instances.", file=sys.stderr)
        print("[BLOCK] Don't translate, don't replace. REWRITE without the codeword.", file=sys.stderr)
        print("[BLOCK] Use real Chinese: 部署/处理/整理/核对/写/改/查/检查/推送/完成", file=sys.stderr)
        for i, m in enumerate(matches[:10], 1):
            print(f"  {i}. ...{m}...", file=sys.stderr)
        sys.exit(2)  # Fail - DO NOT SEND

    print(text)
    print(f"\n[OK] No '▢▢' detected. Safe to send.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()