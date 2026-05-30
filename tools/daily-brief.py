#!/usr/bin/env python3
"""
每日简报生成器
用法:
  python3 daily-brief.py                    # 标准 Markdown 输出
  python3 daily-brief.py --json             # 结构化 JSON 输出
  python3 daily-brief.py --compact         # 紧凑单行格式
"""
import sys
import json
import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ── 固定配置 ──────────────────────────────────────────────────────────
CITY = "Shanghai"
STATE_FILE = Path("/home/fuguang/.openclaw/workspace/memory/blog-state.json")
FEEDS = [
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "tags": ["AI", "技术"]},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "tags": ["编程", "科技"]},
]

# ── 天气 ──────────────────────────────────────────────────────────────
async def get_weather():
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://wttr.in/{CITY}?format=j1")
            data = resp.json()
            c = data["current_condition"][0]
            return {
                "temp": c["temp_C"],
                "condition": c["weatherDesc"][0]["value"],
                "humidity": c["humidity"],
                "wind": c["windspeedKmph"],
                "feels": c["FeelsLikeC"],
            }
    except Exception:
        return {"temp": "?", "condition": "?", "humidity": "?", "wind": "?", "feels": "?"}

# ── 系统状态 ──────────────────────────────────────────────────────────
def get_system_status():
    try:
        with open("/proc/meminfo") as f:
            mem_lines = f.readlines()
        total_kb = int(mem_lines[0].split()[1])
        avail_kb = int(mem_lines[2].split()[1])
        used_kb = total_kb - avail_kb
        mem_pct = int(used_kb / total_kb * 100)

        import subprocess
        disk = subprocess.check_output(
            "df -h /home | tail -1 | awk '{print $5}'", shell=True
        ).strip().decode()
        return {"mem_pct": mem_pct, "disk_used": disk}
    except Exception:
        return {"mem_pct": "?", "disk_used": "?"}

# ── RSS 博客监控 ──────────────────────────────────────────────────────
def fetch_feed(feed):
    try:
        import httpx
        resp = httpx.get(feed["url"], timeout=10, follow_redirects=True)
        resp.raise_for_status()
        root = ET.fromstring(resp.text.encode("utf-8"))
        entries = []
        if root.tag.endswith("feed"):
            for entry in root.findall(".//entry")[:10]:
                title = entry.find("title")
                link = entry.find("link")
                updated = entry.find("updated") or entry.find("published")
                entries.append({
                    "title": title.text if title is not None else "",
                    "link": link.attrib.get("href", "") if link is not None else "",
                    "updated": updated.text if updated is not None else "",
                })
        elif root.tag.endswith("rss") or root.tag == "rss":
            for item in root.findall(".//item")[:10]:
                title = item.find("title")
                link = item.find("link")
                pubdate = item.find("pubDate")
                entries.append({
                    "title": title.text if title is not None else "",
                    "link": link.text if link is not None else "",
                    "updated": pubdate.text if pubdate is not None else "",
                })
        return entries
    except Exception:
        return []

def load_state():
    if STATE_FILE.exists():
        import json
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    import json
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def check_blog_updates():
    state = load_state()
    new_items = []
    for feed in FEEDS:
        entries = fetch_feed(feed)
        if not entries:
            continue
        known = set(state.get(feed["name"], []))
        fresh = [e for e in entries if e["link"] and e["link"] not in known]
        if fresh:
            new_items.append({"feed": feed["name"], "tags": feed["tags"], "items": fresh[:5]})
        all_links = [e["link"] for e in entries if e["link"]][:20]
        state[feed["name"]] = all_links
    save_state(state)
    return new_items

# ── 邮箱状态（无敏感操作）──────────────────────────────────────────────
def get_email_status():
    """返回邮箱状态占位（实际需要授权码），不做任何登录操作"""
    return {
        "status": "需要重新授权",
        "hint": "QQ 邮箱授权码已过期，请在 QQ 邮箱设置中重新生成",
        "account": "1966152237@qq.com",
    }

# ── 格式化输出 ────────────────────────────────────────────────────────
def format_markdown(weather, system, blog_updates, email_status, news_titles):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"📋 **每日简报** | {now}",
        "",
        f"🌤️ **天气** — 上海",
        f"温度: {weather['temp']}°C | {weather['condition']}",
        f"体感: {weather['feels']}°C | 湿度: {weather['humidity']}% | 风速: {weather['wind']} km/h",
        "",
        f"💻 **系统** — 内存 {system['mem_pct']}% / 磁盘已用 {system['disk_used']}",
        "",
        "📬 **邮箱**",
        f"`{email_status['account']}` — {email_status['status']}",
        f"💡 {email_status['hint']}",
        "",
        "📰 **博客更新**",
    ]

    if not blog_updates:
        lines.append("_暂无新增_")
    else:
        for feed_data in blog_updates:
            tag_str = "/".join(feed_data["tags"])
            lines.append(f"\n**{feed_data['feed']}** ({tag_str})")
            for item in feed_data["items"]:
                title = item["title"].strip()
                link = item["link"].strip()
                if title:
                    lines.append(f"- [{title}]({link})")

    if news_titles:
        lines.append("\n📊 **科技新闻（The Verge）**")
        for n in news_titles[:5]:
            lines.append(f"- {n}")

    total_new = sum(len(f["items"]) for f in blog_updates) if blog_updates else 0
    lines.append(f"\n---\n共 {total_new} 条博客更新")

    return "\n".join(lines)

def format_compact(weather, system, blog_updates, email_status):
    new_count = sum(len(f["items"]) for f in blog_updates) if blog_updates else 0
    return (
        f"📋 {datetime.now().strftime('%H:%M')} | "
        f"🌤️ {weather['temp']}°C {weather['condition']} | "
        f"💻 {system['mem_pct']}%/{system['disk_used']} | "
        f"📰 {new_count}条更新 | "
        f"📬 {'✅' if email_status['status'] == 'ok' else '❌'}"
    )

# ── 主程序 ────────────────────────────────────────────────────────────
def main():
    is_json = "--json" in sys.argv
    is_compact = "--compact" in sys.argv

    weather = asyncio.run(get_weather())
    system = get_system_status()
    blog_updates = check_blog_updates()
    email_status = get_email_status()
    news_titles = []  # 保留接口

    # 结构化数据
    data = {
        "weather": weather,
        "system": system,
        "email": email_status,
        "blog_updates": blog_updates,
        "news": news_titles,
        "generated_at": datetime.now().isoformat(),
    }

    if is_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif is_compact:
        print(format_compact(weather, system, blog_updates, email_status))
    else:
        print(format_markdown(weather, system, blog_updates, email_status, news_titles))

if __name__ == "__main__":
    main()