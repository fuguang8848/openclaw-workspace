#!/usr/bin/env python3
"""
v-memory-search.py — RAG-style memory search for V

Simple semantic search across V's long-term memory (MEMORY.md) and daily
files (memory/*.md). Uses TF-IDF + keyword boosting (no external API).

Why:
- memory_search 修真 修真 修真 修真 修真 (修真 修真 修真)
- V 修真 修真 修真 修真 修真 修真 修真, 修真 修真 修真 修真 修真 修真
- 修真 修真 修真 修真 修真 修真 (修真 修真 修真 修真 修真 修真)

Method:
- Tokenize 修真 修真 修真 (CJK 修真 修真 + 修真 修真 修真 修真)
- TF 修真 修真, IDF 修真 修真 修真 (修真 修真 修真)
- 修真 修真: query 修真 + 修真 修真 修真 (SOP 修真 修真 修真, 修真 修真 修真 修真)
- 修真 修真: TF-IDF 修真 + 修真 修真 修真

Usage:
  v-memory-search.py "query" [--top N] [--source memory|workspace|all]
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE = Path("/home/fuguang/.openclaw/workspace")
MEMORY_FILE = WORKSPACE / "MEMORY.md"
DAILY_GLOB = "memory/*.md"

CJK_CHAR = re.compile(r"[\u4e00-\u9fff]+")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")

def tokenize(text):
    """CJK character n-grams + latin words."""
    tokens = []
    # 修真 修真: 修真 2-gram (CJK 修真)
    for m in CJK_CHAR.finditer(text):
        chunk = m.group()
        for i in range(len(chunk) - 1):
            tokens.append(chunk[i:i+2])
        if len(chunk) >= 1:
            tokens.append(chunk[-1])
    # Latin
    tokens.extend(m.group().lower() for m in LATIN_WORD.finditer(text))
    return tokens

def load_documents():
    docs = []
    if MEMORY_FILE.exists():
        docs.append(("MEMORY.md", MEMORY_FILE.read_text(encoding="utf-8")))
    for p in sorted(WORKSPACE.glob(DAILY_GLOB)):
        docs.append((str(p.relative_to(WORKSPACE)), p.read_text(encoding="utf-8")))
    return docs

def chunk_document(name, text, chunk_size=300, overlap=60):
    """Split document into overlapping chunks for finer-grained search."""
    lines = text.split("\n")
    chunks = []
    current_lines = []
    current_len = 0
    for line in lines:
        current_lines.append(line)
        current_len += len(line) + 1
        if current_len >= chunk_size:
            chunk_text = "\n".join(current_lines)
            chunks.append({"source": name, "offset": len("\n".join(current_lines[:max(0, len(current_lines)-3)])), "text": chunk_text})
            # 修真 修真 修真
            current_lines = current_lines[-3:] if len(current_lines) > 3 else current_lines
            current_len = sum(len(l) + 1 for l in current_lines)
    if current_lines:
        chunks.append({"source": name, "offset": 0, "text": "\n".join(current_lines)})
    return chunks

def search(query, top_k=5, source_filter="all"):
    docs = load_documents()
    if source_filter != "all":
        docs = [(n, t) for n, t in docs if source_filter in n]
    
    chunks = []
    for name, text in docs:
        chunks.extend(chunk_document(name, text))
    
    # Tokenize all chunks
    chunk_tokens = [Counter(tokenize(c["text"])) for c in chunks]
    query_tokens = Counter(tokenize(query))
    
    if not query_tokens or not chunks:
        return []
    
    # Document frequency
    df = defaultdict(int)
    for ct in chunk_tokens:
        for tok in set(ct):
            df[tok] += 1
    
    n_chunks = len(chunks)
    
    # TF-IDF scores
    def score(chunk_token_counts):
        s = 0.0
        for tok, q_count in query_tokens.items():
            if tok not in chunk_token_counts:
                continue
            tf = 1 + math.log(chunk_token_counts[tok])
            idf = math.log((n_chunks + 1) / (df[tok] + 1)) + 1
            s += q_count * tf * idf
        return s
    
    scored = []
    for i, ct in enumerate(chunk_tokens):
        s = score(ct)
        if s > 0:
            scored.append((s, chunks[i]))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:top_k]

def main():
    parser = argparse.ArgumentParser(description="RAG-style memory search for V")
    parser.add_argument("query", help="search query")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--source", choices=["memory", "workspace", "all"], default="all")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    args = parser.parse_args()
    
    results = search(args.query, top_k=args.top, source_filter=args.source)
    
    if args.json:
        out = [{"score": s, "source": r["source"], "snippet": r["text"][:500]} for s, r in results]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"=== 修真 {len(results)} 修真 (query: {args.query}) ===\n")
        for i, (score, r) in enumerate(results, 1):
            print(f"--- [{i}] score={score:.2f} source={r['source']} ---")
            snippet = r["text"][:300].replace("\n", " ")
            print(snippet)
            print()

if __name__ == "__main__":
    main()
