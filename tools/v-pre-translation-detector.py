#!/usr/bin/env python3
"""
v-pre-translation-detector.py - Detect English-to-placeholder translation patterns

V's auto-pilot bug: when writing Chinese output, it sometimes translates English
technical terms (commit, service, status, pipeline, deploy, etc.) into a
2-character placeholder word. The placeholder was 'xiuzhen' (cultivation), but
after the bug surfaced we renamed it to '▢▢' (visually distinct, not a real
Chinese character).

This detector finds phrases that look like English→placeholder translations:
- "▢▢ commit" / "commit ▢▢" (English term adjacent to placeholder)
- "▢▢ 5 仓" / "▢▢ 5 仓" (placeholder + count + measure word, classic pattern)
- "▢▢ ▢▢ ▢▢" (placeholder stacking, gibberish pattern)
- English term in list without Chinese explanation

Usage:
  v-pre-translation-detector.py <file> | --stdin
  Exit 0 = clean, Exit 1 = issues found

Pairs with:
- v-pre-send-filter.py (catches placeholder)
- v-pre-send-guard plugin (catches at gateway)
"""

import re
import sys
from pathlib import Path

# Common English technical terms that V's auto-pilot might try to "translate"
ENGLISH_TECH_TERMS = [
    "commit", "push", "pull", "merge", "branch", "rebase", "checkout",
    "deploy", "build", "test", "release", "tag",
    "service", "status", "health", "endpoint", "request", "response",
    "pipeline", "workflow", "queue", "stream", "batch", "job",
    "container", "image", "registry", "cluster", "node", "pod",
    "database", "schema", "migration", "index", "query", "transaction",
    "cache", "session", "token", "cookie", "header", "payload",
    "error", "warning", "info", "debug", "trace", "log",
    "thread", "process", "lock", "mutex", "semaphore", "deadlock",
    "config", "setting", "option", "flag", "env", "var",
    "import", "export", "module", "package", "library", "framework",
    "function", "method", "class", "object", "instance", "interface",
    "agent", "tool", "skill", "plugin", "extension", "addon",
    "memory", "storage", "disk", "cpu", "ram", "network",
    "user", "admin", "guest", "role", "permission", "scope",
]

# Suspicious patterns: placeholder + measure word (仓, 个, 项, 次, etc.)
MEASURE_WORDS = r"[个项种次遍回步条笔份片块台架艘辆门间层篇章首幅帧集队组]"


def detect_translations(text: str) -> list[dict]:
    """Find patterns that suggest English→placeholder translation."""
    issues = []

    # Pattern 1: placeholder + count + measure word (▢▢ 5 仓)
    for m in re.finditer(rf"▢▢\s*\d+\s*{MEASURE_WORDS}", text):
        ctx_start = max(0, m.start() - 10)
        ctx_end = min(len(text), m.end() + 10)
        issues.append({
            "type": "placeholder+count+measure",
            "match": m.group(0),
            "context": text[ctx_start:ctx_end].replace("\n", " "),
        })

    # Pattern 2: English term adjacent to placeholder (either side)
    for term in ENGLISH_TECH_TERMS:
        pattern = rf"\b{term}\b.{{0,3}}▢▢|▢▢.{{0,3}}\b{term}\b"
        for m in re.finditer(pattern, text, re.IGNORECASE):
            ctx_start = max(0, m.start() - 10)
            ctx_end = min(len(text), m.end() + 10)
            issues.append({
                "type": f"english-adjacent:{term}",
                "match": m.group(0),
                "context": text[ctx_start:ctx_end].replace("\n", " "),
            })

    # Pattern 3: placeholder stacking (▢▢ ▢▢ ▢▢ or ▢▢▢▢)
    for m in re.finditer(r"(▢▢\s*){2,}", text):
        ctx_start = max(0, m.start() - 5)
        ctx_end = min(len(text), m.end() + 5)
        issues.append({
            "type": "placeholder-stacking",
            "match": m.group(0)[:30],
            "context": text[ctx_start:ctx_end].replace("\n", " "),
        })

    # Pattern 4: bare English term in what should be Chinese (CRUD verbs)
    bare_english_pattern = r"\b(push|pull|merge|rebase|commit|deploy|build|test)\s+[一二三四五六七八九十0-9]+\s+[个项种次遍回步条笔份片块台]"
    for m in re.finditer(bare_english_pattern, text, re.IGNORECASE):
        ctx_start = max(0, m.start() - 10)
        ctx_end = min(len(text), m.end() + 10)
        issues.append({
            "type": "bare-english-verb",
            "match": m.group(0),
            "context": text[ctx_start:ctx_end].replace("\n", " "),
        })

    return issues


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        text = sys.stdin.read()
    elif len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        print("Usage: v-pre-translation-detector.py <file> | --stdin", file=sys.stderr)
        sys.exit(1)

    issues = detect_translations(text)

    if not issues:
        print("[OK] No suspicious English→placeholder translation patterns.")
        sys.exit(0)

    print(f"\n[WARN] Found {len(issues)} suspicious pattern(s):", file=sys.stderr)
    for i, issue in enumerate(issues[:20], 1):
        print(f"  {i}. [{issue['type']}] '{issue['match']}' in: ...{issue['context']}...",
              file=sys.stderr)
    print("\n[ACTION] Rewrite in clean Chinese. Keep English terms if they are real "
          "technical names (commit message, REST API, etc.).", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
