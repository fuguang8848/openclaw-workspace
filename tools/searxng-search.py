#!/usr/bin/env python3
"""
V-Search: Direct search using Bing HTML
Usage: searxng-search.py <query> [--limit N]
"""
import sys
import os
import ssl
import certifi
import httpx
import argparse
import urllib.parse
from lxml import html

os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'


def search_bing(query, limit=8):
    """Direct Bing search"""
    ctx = ssl.create_default_context(cafile=certifi.where())

    params = {
        'q': query,
        'adlt': 'off',
        'mkt': 'zh-CN'
    }
    url = f"https://www.bing.com/search?{urllib.parse.urlencode(params)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    resp = httpx.get(url, timeout=12, verify=ctx, headers=headers, follow_redirects=True)

    if resp.status_code != 200:
        return [], f"Bing returned {resp.status_code}"

    dom = html.fromstring(resp.text)
    results = []

    for item in dom.xpath('//ol[@id="b_results"]/li[contains(@class, "b_algo")]')[:limit]:
        link_el = item.xpath('.//h2/a')
        if not link_el:
            continue
        link_el = link_el[0]
        href = link_el.attrib.get('href', '')
        title = ''.join(c for c in link_el.itertext() if isinstance(c, str))
        title = title.strip()

        # Content
        content = ''
        p_els = item.xpath('.//p')
        if p_els and hasattr(p_els[0], 'itertext'):
            content = ''.join(t for t in p_els[0].itertext() if isinstance(t, str))
            content = content.strip()

        if href and title:
            results.append({'url': href, 'title': title, 'content': content[:150]})

    return results, None


def main():
    parser = argparse.ArgumentParser(description='V-Search: Bing-based search')
    parser.add_argument('query', nargs='+', help='Search query')
    parser.add_argument('--limit', '-n', type=int, default=8, help='Max results (default: 8)')
    args = parser.parse_args()

    query = ' '.join(args.query)
    limit = args.limit

    print(f"\n🔍 {query}\n")

    results, err = search_bing(query, limit)

    if err:
        print(f"⚠️ Error: {err}\n")
        sys.exit(1)

    if not results:
        print("⚠️ No results found.\n")
        sys.exit(0)

    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['title']}")
        print(f"     → {r['url']}")
        if r['content']:
            print(f"     {r['content'][:120]}")
        print()

    print(f"  ({len(results)} results)")
    print()


if __name__ == '__main__':
    main()
