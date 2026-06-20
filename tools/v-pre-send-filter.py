#!/usr/bin/env python3
"""V pre-send filter: detect placeholder/codeword leaks from user-facing messages.

V2 (6/20 16:18) — defense in depth after 修真→▢▢ rename.

Problem: V's auto-pilot leaks multiple placeholders/codewords when writing
Chinese output. The original codeword was 修真 (2-char Chinese word), which
auto-pilot started using as a translation target for English terms (commit,
service, status, pipeline). Renamed to ▢▢ (Unicode white square) but:

1. ▢▢ is the NEW placeholder. Filter must catch it.
2. 修真 is the OLD placeholder. Auto-pilot may still write it. Filter MUST also
   catch it (defense in depth: if auto-pilot defaults to old name, still block).
3. pinyin forms (xiuzhen, xiūzhēn, xiu zhen) should also be caught in case
   auto-pilot writes pinyin.

NEW STRATEGY (after 浮光 10:58 + 16:18 feedback):
- If ANY placeholder appears in user-facing text, FAIL (exit 2) and force V
  to rewrite. Don't translate, don't replace — rewrite in real Chinese.
- Filter is a safety net, not a translator.

For INTERNAL docs (MEMORY.md, HEARTBEAT.md, daily memory, SOP-43-draft.md),
the placeholders are allowed — they stay in the SOP #42/#43 meta-discussion
sections. Filter only runs on user-facing output (webchat replies, PR
descriptions, commit messages sent to 浮光).
"""
import re
import sys
from pathlib import Path

# All placeholder/codeword patterns to block
PATTERNS = [
    (r"▢▢", "▢▢ (current placeholder)"),
    (r"修真", "修真 (OLD codeword, must be fully retired)"),
    (r"xiū\s*zhēn", "xiū zhēn (pinyin)"),
    (r"xiu\s*zhen", "xiu zhen (pinyin)"),
]


def detect_all(text: str) -> list[dict]:
    """Return list of {pattern, label, count, contexts}."""
    results = []
    for pattern, label in PATTERNS:
        contexts = []
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - 5)
            end = min(len(text), m.end() + 5)
            contexts.append(text[start:end].replace("\n", " "))
        if contexts:
            results.append({
                "pattern": pattern,
                "label": label,
                "count": len(contexts),
                "contexts": contexts,
            })
    return results


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        text = sys.stdin.read()
    elif len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        print("Usage: v-pre-send-filter.py <file> | --stdin", file=sys.stderr)
        sys.exit(1)

    results = detect_all(text)
    total = sum(r["count"] for r in results)

    if total > 0:
        print(f"\n[BLOCK] {total} placeholder/codeword instances detected.", file=sys.stderr)
        print("[BLOCK] Don't translate, don't replace. REWRITE without the codeword.", file=sys.stderr)
        print("[BLOCK] Use real Chinese: 部署/处理/整理/核对/写/改/查/检查/推送/完成", file=sys.stderr)
        for r in results:
            print(f"\n  Pattern: {r['label']} ({r['count']} instances)", file=sys.stderr)
            for i, ctx in enumerate(r["contexts"][:5], 1):
                print(f"    {i}. ...{ctx}...", file=sys.stderr)
        sys.exit(2)  # Fail - DO NOT SEND

    print(text)
    print(f"\n[OK] No placeholders/codewords detected. Safe to send.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
