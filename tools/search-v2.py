#!/usr/bin/env python3
"""
search-v2.py - V 6/7 17:04 多源搜索路由 (国内优先 + 国外尽量)

SOP #21 任务 1 工作流 - V 眼睛
3 源路由:
1. Bing China (cn.bing.com) - 主力, 浮光 6/7 search-v.py 在用
2. arxiv (export.arxiv.org/api) - 学术权威
3. 搜狗微信 (weixin.sogou.com) - 中文文章

按浮光 17:04 拍板: "权威资料可以是国内的, 国外的尽量去做"
"""
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re
from html.parser import HTMLParser
from typing import List, Dict, Any

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _request(url, headers=None, timeout=15):
    """统一 HTTP 请求."""
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.status


# ============================================================
# 源 1: Bing China (主力, 浮光 6/7 search-v.py 在用)
# ============================================================
def search_bing_china(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """Bing China 搜索 (cn.bing.com) - 浮光 系统主力."""
    url = f"https://cn.bing.com/search?q={urllib.parse.quote(query)}&setmkt=zh-CN&count={count}"
    try:
        html, code = _request(url, timeout=10)
        if code != 200:
            return []
    except Exception as e:
        return [{"_error": f"bing_china: {type(e).__name__}: {str(e)[:200]}"}]

    results = []
    # V 6/7 17:10 修: Bing China HTML 结构改了 (h2 class="" + b_caption div)
    # 旧: <li class="b_algo"><h2><a href="...">title</a></h2><p>snippet</p>
    # 新: <li class="b_algo"...><h2 class=""><a href="...">title</a></h2><div class="b_caption"><p>snippet</p>
    pattern = r'<li class="b_algo"[^>]*>.*?<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>\s*</h2>.*?<div class="b_caption"[^>]*>\s*<p[^>]*>(.*?)</p>'
    for m in re.finditer(pattern, html, re.DOTALL):
        url, title, snippet = m.group(1), m.group(2), m.group(3)
        # 清理 HTML 标签 + 实体
        title = re.sub(r"<[^>]+>", "", title).strip()
        title = re.sub(r"&[a-z]+;", " ", title)
        snippet = re.sub(r"<[^>]+>", "", snippet).strip()
        snippet = re.sub(r"&[a-z]+;", " ", snippet)
        if title and url.startswith("http"):
            results.append({
                "title": title[:200],
                "url": url[:500],
                "snippet": snippet[:300],
                "source": "bing_china",
            })
        if len(results) >= count:
            break
    return results


# ============================================================
# 源 2: arxiv (学术权威, 无 key)
# ============================================================
def search_arxiv(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """arxiv 学术搜索 (export.arxiv.org/api) - 国外权威."""
    # arxiv API: 简单 search_query = all:keyword
    url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results={count}"
    try:
        xml, code = _request(url, timeout=15)
        if code != 200:
            return []
    except Exception as e:
        return [{"_error": f"arxiv: {type(e).__name__}: {str(e)[:200]}"}]

    results = []
    # arxiv 返回 Atom XML
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
    for entry in entries:
        title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        id_m = re.search(r"<id>(.*?)</id>", entry)
        summary_m = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        author_m = re.findall(r"<author>\s*<name>(.*?)</name>", entry)
        if title_m and id_m:
            results.append({
                "title": re.sub(r"\s+", " ", title_m.group(1)).strip()[:200],
                "url": id_m.group(1).strip()[:500],
                "snippet": (re.sub(r"\s+", " ", summary_m.group(1)).strip()[:300] if summary_m else ""),
                "source": "arxiv",
                "authors": author_m[:3],
            })
    return results


# ============================================================
# 源 3: 搜狗微信 (中文文章, 微信生态)
# ============================================================
def search_sogou_weixin(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """搜狗微信搜索 (weixin.sogou.com) - 中文行业文章."""
    url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(query)}"
    try:
        html, code = _request(url, timeout=10)
        if code != 200:
            return []
    except Exception as e:
        return [{"_error": f"sogou_weixin: {type(e).__name__}: {str(e)[:200]}"}]

    results = []
    # 微信结果: <div class="txt-box"><h3><a href="...">title</a></h3><p>snippet
    pattern = r'<div class="txt-box">\s*<h3>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>\s*<p[^>]*>(.*?)</p>'
    for m in re.finditer(pattern, html, re.DOTALL):
        url, title, snippet = m.group(1), m.group(2), m.group(3)
        title = re.sub(r"<[^>]+>", "", title).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet).strip()
        if title and url:
            results.append({
                "title": title[:200],
                "url": url[:500],
                "snippet": snippet[:300],
                "source": "sogou_weixin",
            })
        if len(results) >= count:
            break
    return results


# ============================================================
# 多源路由 (V 拍板)
# ============================================================
SOURCES = {
    "bing_china": search_bing_china,
    "arxiv": search_arxiv,
    "sogou_weixin": search_sogou_weixin,
}


def search(query: str, sources: List[str] = None, count: int = 5) -> Dict[str, Any]:
    """多源并行搜索 (国内优先 + 国外尽量)."""
    if sources is None:
        sources = ["bing_china", "arxiv", "sogou_weixin"]
    out = {
        "query": query,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "results": {},
        "summary": {},
    }
    for src in sources:
        if src not in SOURCES:
            out["results"][src] = [{"_error": f"unknown source: {src}"}]
            continue
        try:
            t0 = time.time()
            results = SOURCES[src](query, count=count)
            elapsed = time.time() - t0
            out["results"][src] = results
            out["summary"][src] = {
                "count": len(results) if not (results and "_error" in results[0]) else 0,
                "elapsed_s": round(elapsed, 2),
                "status": "ok" if results and "_error" not in results[0] else "error",
            }
        except Exception as e:
            out["results"][src] = [{"_error": f"{type(e).__name__}: {str(e)[:200]}"}]
            out["summary"][src] = {"count": 0, "elapsed_s": 0, "status": "error", "error": str(e)[:100]}
    return out


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: search-v2.py <query> [sources=bing_china,arxiv,sogou_weixin] [count=5]", file=sys.stderr)
        sys.exit(1)
    query = sys.argv[1]
    sources = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    result = search(query, sources, count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
