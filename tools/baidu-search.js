#!/usr/bin/env node
/**
 * baidu-search.js — 百度搜索（curl 方式）
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const CACHE_TTL = 1800 * 1000;
const CACHE_DIR = path.join(process.env.HOME || '/tmp', '.openclaw', 'search-cache');
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
}

function cacheKey(q) {
    return path.join(CACHE_DIR, Buffer.from(q).toString('base64').replace(/\//g, '_') + '.json');
}

function getCache(q) {
    try {
        const f = cacheKey(q);
        if (fs.existsSync(f)) {
            const stat = fs.statSync(f);
            if (Date.now() - stat.mtimeMs < CACHE_TTL) {
                return JSON.parse(fs.readFileSync(f, 'utf8'));
            }
        }
    } catch (e) {}
    return null;
}

function setCache(q, data) {
    try {
        fs.writeFileSync(cacheKey(q), JSON.stringify(data, null, 2));
    } catch (e) {}
}

function stripTags(str) {
    return str.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\s+/g, ' ').trim();
}

function search(query) {
    const encoded = encodeURIComponent(query);
    const url = `https://www.baidu.com/s?wd=${encoded}&rn=10&ie=utf-8`;

    const html = execSync(
        `curl -s --noproxy '*' -L -A "${UA}" -H "Referer: https://www.baidu.com/" --max-time 15 "${url}"`,
        { timeout: 20000 }
    ).toString('utf8');

    const results = [];

    // 匹配 <h3 class="c-title"> 下的 <a href="...">标题</a>
    const titleMatches = html.match(/<h3[^>]*class="[^"]*c-title[^"]*"[^>]*>[\s\S]*?href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi) || [];
    
    // 匹配摘要 <span class="c-span-last"> 或 <div class="c-abstract">
    const abstractMatches = html.match(/<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>([\s\S]*?)<\/div>/gi) || [];

    for (let i = 0; i < Math.min(titleMatches.length, 10); i++) {
        const hrefMatch = /href="([^"]+)"/.exec(titleMatches[i]);
        const textMatch = />([^<]+)<\/a>/.exec(titleMatches[i]);
        const abstract = abstractMatches[i] ? stripTags(abstractMatches[i]) : '';

        if (hrefMatch && textMatch) {
            results.push({
                title: stripTags(textMatch[1]),
                url: hrefMatch[1],
                snippet: abstract.substring(0, 200)
            });
        }
    }

    // 备用：如果没匹配到，尝试更宽泛的匹配
    if (results.length === 0) {
        const simple = /<a[^>]+class="[^"]*c-title[^"]*"[^>]+>([^<]+)<\/a>/gi;
        let m;
        while ((m = simple.exec(html)) !== null && results.length < 10) {
            results.push({ title: stripTags(m[1]), url: '', snippet: '' });
        }
    }

    return results;
}

function main() {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log('用法: node baidu-search.js "<查询>"');
        return;
    }
    const query = args.join(' ');

    const cached = getCache(query);
    if (cached) {
        console.log(`[缓存] ${query}`);
        printResults(query, cached);
        return;
    }

    try {
        const results = search(query);
        setCache(query, results);
        printResults(query, results);
    } catch (e) {
        console.error('搜索失败:', e.message);
        process.exit(1);
    }
}

function printResults(query, results) {
    if (results.length === 0) {
        console.log(`未找到结果: ${query}`);
        return;
    }
    console.log(`搜索: ${query} (${results.length} 条)\n`);
    for (const r of results) {
        console.log(`【${r.title}】`);
        if (r.url) console.log(`链接: ${r.url}`);
        if (r.snippet) console.log(`摘要: ${r.snippet}`);
        console.log('');
    }
}

main();
