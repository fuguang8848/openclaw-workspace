#!/usr/bin/env python3
"""
V-Search Bridge: 让 Node.js search-router.js 能调用 Bing 搜索
Output: JSON 格式结果，供 Node.js 解析
"""
import sys
import os
import json
import httpx
import urllib.parse
from lxml import html

os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'

# Watt Toolkit 本地代理使用自签名证书，跳过验证
# 现在已关闭，改回系统默认 CA
VERIFY = True


def search_bing(query, limit=8):
    params = {'q': query, 'adlt': 'off', 'mkt': 'zh-CN'}
    url = f"https://www.bing.com/search?{urllib.parse.urlencode(params)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    resp = httpx.get(url, timeout=12, verify=VERIFY, headers=headers, follow_redirects=True)
    if resp.status_code != 200:
        return [], f"Bing HTTP {resp.status_code}"
    dom = html.fromstring(resp.text)
    results = []
    for item in dom.xpath('//ol[@id="b_results"]/li[contains(@class, "b_algo")]')[:limit]:
        link_el = item.xpath('.//h2/a')
        if not link_el:
            continue
        link_el = link_el[0]
        href = link_el.attrib.get('href', '')
        title = ''.join(c for c in link_el.itertext() if isinstance(c, str)).strip()
        content = ''
        p_els = item.xpath('.//p')
        if p_els and hasattr(p_els[0], 'itertext'):
            content = ''.join(t for t in p_els[0].itertext() if isinstance(t, str)).strip()
        if href and title:
            results.append({'url': href, 'title': title, 'content': content[:150]})
    return results, None


if __name__ == '__main__':
    query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    if not query:
        print(json.dumps({'error': 'No query', 'results': []}))
        sys.exit(1)
    results, err = search_bing(query, 8)
    if err:
        print(json.dumps({'error': err, 'results': []}))
        sys.exit(1)
    print(json.dumps({'query': query, 'results': results}, ensure_ascii=False))
