#!/usr/bin/env node
/**
 * search-router.js — 搜索路由 + 缓存层 + EventBus
 *
 * 统一入口，根据问题类型路由到最优搜索引擎
 * 支持缓存 + fallback + 事件总线
 *
 * 事件：search.execute / search.result / search.cached / state.transition
 *
 * 用法：
 *   node search-router.js <query> [--engine tavily|local|all] [--max-results 5] [--answer]
 *   node search-router.js --stats
 *   node search-router.js --clear-cache
 */

const path = require('path');
const fs = require('fs');
const http = require('http');
const { getEventBus, getSharedContext, EVENTS } = require('./event-bus.js');

const TOOLS_DIR = path.join(process.env.HOME, '.openclaw', 'workspace', 'tools');
const CACHE_DIR  = path.join(process.env.HOME, '.openclaw', 'cache', 'search');
const CACHE_FILE = path.join(CACHE_DIR, 'router.json');
const MAX_CACHE_SIZE = 300;
const DEFAULT_TTL = 1800; // 30 min

const bus = getEventBus();
const ctx = getSharedContext('search-router');
let taskIdCounter = 0;
function nextTaskId() { return `search-task-${++taskIdCounter}`; }

// ── 缓存 ───────────────────────────────────────────────────────────────
function init() {
  if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });
  if (!fs.existsSync(CACHE_FILE)) fs.writeFileSync(CACHE_FILE, JSON.stringify({}));
}

function readCache() {
  try { return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch { return {}; }
}

function writeCache(data) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(data, null, 2));
}

function hashKey(query, engine) {
  const crypto = require('crypto');
  return crypto.createHash('md5').update(`${query}|${engine}`).digest('hex');
}

function cacheGet(key) {
  const data = readCache();
  const entry = data[key];
  if (!entry) return null;
  if (Date.now() > entry.expireAt) {
    delete data[key];
    writeCache(data);
    return null;
  }
  return entry.value;
}

function cacheSet(key, value, ttl = DEFAULT_TTL) {
  const data = readCache();
  const now = Date.now();
  if (Object.values(data).length >= MAX_CACHE_SIZE) {
    let oldestKey = null, oldestTime = Infinity;
    Object.keys(data).forEach(k => { if (data[k].createdAt < oldestTime) { oldestTime = data[k].createdAt; oldestKey = k; } });
    if (oldestKey) delete data[oldestKey];
  }
  data[key] = { value, createdAt: now, expireAt: now + ttl * 1000, ttl };
  writeCache(data);
}

function cacheStats() {
  const data = readCache();
  let valid = 0, expired = 0;
  const now = Date.now();
  Object.values(data).forEach(e => { e.expireAt < now ? expired++ : valid++; });
  console.log(`[router cache] valid=${valid} expired=${expired} total=${Object.keys(data).length}`);
  console.log(`[eventbus] ${JSON.stringify(bus.stats())}`);
}

// ── 路由判断 ────────────────────────────────────────────────────────────
function routeEngine(query, explicitEngine) {
  // 优先使用本地 Bing 搜索（search-v.py）
  if (explicitEngine && explicitEngine !== 'auto') return explicitEngine;
  const q = query.toLowerCase();
  // 国内内容优先走 local（search-v.py Bing）
  if (/百度|知乎|微博|36kr|微信文章|国内新闻|教程|文档|百科/.test(q)) return 'local';
  // 简短问答也走 local
  if (q.split(' ').length <= 4 && !/为什么|如何|怎么|是什么/.test(q)) return 'local';
  // 其他走 tavily（即 search-v.py）
  return 'tavily';
}

// ── 搜索执行（异步）──────────────────────────────────────────────────────
function runTavily(query, maxResults, includeAnswer) {
  // 使用本地 search-v.py (Bing HTML 搜索) 替代 Tavily API
  return new Promise((resolve, reject) => {
    const script = path.join(TOOLS_DIR, 'search-v.py');
    const { execSync } = require('child_process');
    try {
      const result = execSync(`python3 "${script}" ${JSON.stringify(query)} 2>/dev/null`, {
        encoding: 'utf8', timeout: 20000, env: { ...process.env, no_proxy: '*', NO_PROXY: '*' }
      });
      const parsed = JSON.parse(result);
      if (parsed.error) {
        reject(new Error(parsed.error));
        return;
      }
      // 转换为标准格式
      // URL 去重（参考 AgentSearch）
      const seenUrls = new Set();
      const results = (parsed.results || []).reduce((acc, r) => {
        if (!seenUrls.has(r.url)) {
          seenUrls.add(r.url);
          acc.push({ url: r.url, title: r.title, snippet: r.content || '' });
        }
        return acc;
      }, []);
      resolve({ results, answer: null });
    } catch (e) {
      reject(new Error(`search-v.py failed: ${e.message}`));
    }
  });
}

// 直接 HTTP 调用本地搜索代理（避免 local-search.js 模块级 argv 副作用）
function runLocal(query, maxResults) {
  // 使用本地 search-v.py (Bing HTML 搜索)
  return new Promise((resolve, reject) => {
    const script = path.join(TOOLS_DIR, 'search-v.py');
    const { execSync } = require('child_process');
    try {
      const result = execSync(`python3 "${script}" ${JSON.stringify(query)} 2>/dev/null`, {
        encoding: 'utf8', timeout: 20000, env: { ...process.env, no_proxy: '*', NO_PROXY: '*' }
      });
      const parsed = JSON.parse(result);
      if (parsed.error) {
        reject(new Error(parsed.error));
        return;
      }
      // URL 去重（参考 AgentSearch）
      const seenUrls = new Set();
      const results = (parsed.results || []).reduce((acc, r) => {
        if (!seenUrls.has(r.url)) {
          seenUrls.add(r.url);
          acc.push({ url: r.url, title: r.title, snippet: r.content || '' });
        }
        return acc;
      }, []);
      resolve({ results });
    } catch (e) {
      reject(new Error(`search-v.py failed: ${e.message}`));
    }
  });
}

// ── 主流程 ──────────────────────────────────────────────────────────────
async function main() {
  init();
  const args = process.argv.slice(2);

  let query = '', engine = 'auto', maxResults = 5, includeAnswer = false;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--engine': case '-e': engine = args[++i]; break;
      case '--max-results': case '-n': maxResults = parseInt(args[++i]); break;
      case '--answer': case '-a': includeAnswer = true; break;
      case '--stats': cacheStats(); return;
      case '--clear-cache':
        fs.writeFileSync(CACHE_FILE, JSON.stringify({}));
        console.log('[router] cache cleared'); return;
      default: if (!args[i].startsWith('-')) query = args[i];
    }
  }

  if (!query) {
    console.error('Usage: node search-router.js <query> [--engine tavily|local|auto] [--max-results 5] [--answer] [--stats] [--clear-cache]');
    process.exit(1);
  }

  // Strip common search prefixes
  const prefixes = ['帮我搜一下', '帮我找一下', '帮我查一下', '搜一下', '搜索', '查找', '帮我找', '帮我搜', '帮我查', 'look up', 'search', 'find', '研究一下', '调研'];
  for (const p of prefixes) {
    if (query.startsWith(p)) {
      query = query.slice(p.length).trim();
      break;
    }
  }

  if (!query) {
    console.error('[router] empty query after stripping');
    process.exit(1);
  }

  // ── 初始化状态 ───────────────────────────────────────────────────────
  const taskId = nextTaskId();
  ctx.update('task.id', taskId);
  ctx.update('task.description', query);
  ctx.update('task.status', 'pending');
  ctx.update('thinking.phase', 'understanding');
  ctx.update('search.query', query);
  ctx.update('search.engines', []);

  bus.emit(EVENTS.STATE_TRANSITION, ctx.transitionTask('clarifying'));
  bus.emit(EVENTS.CONTEXT_UPDATE, { path: 'task.id', value: taskId });
  bus.emit(EVENTS.CONTEXT_UPDATE, { path: 'search.query', value: query });

  // ── 路由 ─────────────────────────────────────────────────────────────
  const chosenEngine = routeEngine(query, engine);
  const cacheKey = hashKey(query, chosenEngine);
  ctx.update('search.engines', [chosenEngine]);

  bus.emit(EVENTS.STATE_TRANSITION, ctx.transitionTask('planning'));
  ctx.update('task.status', 'planning');
  ctx.update('thinking.phase', 'planning');

  // ── 缓存命中 ─────────────────────────────────────────────────────────
  const cached = cacheGet(cacheKey);
  if (cached) {
    bus.emit(EVENTS.SEARCH_CACHED, { query, engine: chosenEngine, taskId });
    bus.emit(EVENTS.CONTEXT_UPDATE, { path: 'search.cached', value: true });
    bus.emit(EVENTS.CONTEXT_UPDATE, { path: 'search.results', value: cached.results || [] });
    console.error(`[router:CACHE:HIT] engine=${chosenEngine} task=${taskId}`);
    console.log(JSON.stringify(cached));
    return;
  }

  console.error(`[router:CACHE:MISS] engine=${chosenEngine} task=${taskId}`);

  // ── 执行 ──────────────────────────────────────────────────────────────
  bus.emit(EVENTS.STATE_TRANSITION, ctx.transitionTask('executing'));
  ctx.update('task.status', 'executing');
  ctx.update('thinking.phase', 'executing');

  bus.emit(EVENTS.SEARCH_EXECUTE, { query, engines: [chosenEngine], maxResults, taskId, includeAnswer });

  let result;
  if (chosenEngine === 'all') {
    try {
      const [t, l] = await Promise.all([runTavily(query, maxResults, false), runLocal(query, maxResults)]);
      const seen = new Set();
      const merged = { query, results: [], answer: null };
      [t, l].forEach(r => {
        (r.results || []).forEach(item => { if (!seen.has(item.url)) { seen.add(item.url); merged.results.push(item); } });
        if (r.answer) merged.answer = r.answer;
      });
      result = merged;
    } catch (e) {
      console.error('[router] multi-engine fallback:', e.message);
      result = { query, results: [], error: e.message };
    }
  } else if (chosenEngine === 'tavily') {
    try {
      result = await runTavily(query, maxResults, includeAnswer);
    } catch (e) {
      console.error(`[router] Tavily failed, trying local: ${e.message}`);
      try {
        result = await runLocal(query, maxResults);
        result._fallback = 'local';
      } catch (e2) {
        result = { query, results: [], error: e2.message };
      }
    }
  } else {
    result = await runLocal(query, maxResults);
  }

  // ── 存储结果 ─────────────────────────────────────────────────────────
  bus.emit(EVENTS.SEARCH_RESULT, { query, engine: chosenEngine, results: result.results || [], cached: false, taskId });
  ctx.update('search.results', result.results || []);
  ctx.update('search.cached', false);

  // ── 完成 ─────────────────────────────────────────────────────────────
  bus.emit(EVENTS.STATE_TRANSITION, ctx.transitionTask('completed'));
  ctx.update('task.status', 'completed');
  ctx.update('task.result', result);
  ctx.update('task.completion_rate', 1.0);
  ctx.update('thinking.phase', 'reflection');

  cacheSet(cacheKey, result);
  console.log(JSON.stringify(result));
}

main().catch(e => { console.error('[router] fatal:', e.message); process.exit(1); });