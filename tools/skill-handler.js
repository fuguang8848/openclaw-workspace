#!/usr/bin/env node
/**
 * skill-handler.js — Skill Handler 抽象层
 *
 * 标准化 Skill Handler 接口：
 *   handle(event, context) → { success, result, nextAction }
 *
 * 注册格式：
 *   bus.register('skill-name', {
 *     'event.type': ({ data, ctx }) => ({ success, result, nextAction })
 *   })
 *
 * nextAction: null=结束, continue=继续, next=下一个技能, wait=等待响应, escalate=升级
 */

const { getEventBus, getSharedContext, EVENTS } = require('./event-bus.js');

const bus = getEventBus();

// ── 内置 Handler ───────────────────────────────────────────────────────
const builtInHandlers = {

  // ── 搜索技能 ──────────────────────────────────────────────────────
  'openclaw-tavily-search': {
    [EVENTS.SEARCH_EXECUTE]: ({ data }) => {
      const { execSync } = require('child_process');
      const path = require('path');
      const { query, maxResults } = data;

      const script = path.join(process.env.HOME, '.openclaw', 'workspace', 'tools', 'search-v.py');
      const cmd = `python3 "${script}" ${JSON.stringify(query)} 2>/dev/null`;
      const result = execSync(cmd, { encoding: 'utf8', timeout: 20000, env: { ...process.env, no_proxy: '*', NO_PROXY: '*' } });
      const parsed = JSON.parse(result);
      if (parsed.error) throw new Error(parsed.error);
      return { success: true, result: { results: parsed.results || [] }, nextAction: null };
    }
  },

  // ── 本地搜索 ──────────────────────────────────────────────────────
  'local-search': {
    [EVENTS.SEARCH_EXECUTE]: ({ data }) => {
      const { execSync } = require('child_process');
      const path = require('path');
      const { query, maxResults } = data;

      const script = path.join(process.env.HOME, '.openclaw', 'workspace', 'tools', 'search-v.py');
      const cmd = `python3 "${script}" ${JSON.stringify(query)} 2>/dev/null`;
      const result = execSync(cmd, { encoding: 'utf8', timeout: 20000, env: { ...process.env, no_proxy: '*', NO_PROXY: '*' } });
      const parsed = JSON.parse(result);
      if (parsed.error) throw new Error(parsed.error);
      return { success: true, result: { results: parsed.results || [] }, nextAction: null };
    }
  },

  // ── 记忆存储 ──────────────────────────────────────────────────────
  'memory-store': {
    [EVENTS.MEMORY_STORE]: ({ data }) => {
      const { category, content, importance } = data;
      const fs = require('fs');
      const path = require('path');
      const date = new Date().toISOString().split('T')[0];
      const memFile = path.join(process.env.HOME, '.openclaw', 'workspace', 'memory', `${date}.md`);
      const entry = `\n## ${new Date().toISOString()} (${category})\n\n${content}\n`;

      let existing = '';
      if (fs.existsSync(memFile)) existing = fs.readFileSync(memFile, 'utf8');
      fs.writeFileSync(memFile, existing + entry);

      return { success: true, result: { stored: true, category }, nextAction: null };
    }
  },

  // ── 任务创建 ──────────────────────────────────────────────────────
  'task-create': {
    [EVENTS.TASK_CREATE]: ({ data }) => {
      const { description, plan } = data;
      const taskId = `task-${Date.now()}`;
      return { success: true, result: { taskId, description }, nextAction: 'continue' };
    }
  }
};

// ── 注册内置 Handler ───────────────────────────────────────────────────
function registerBuiltInHandlers() {
  for (const [skillName, handlers] of Object.entries(builtInHandlers)) {
    bus.register(skillName, handlers);
  }
  console.error(`[skill-handler] registered ${Object.keys(builtInHandlers).length} built-in handlers`);
}

// ── 路由主函数 ────────────────────────────────────────────────────────
function routeIntent(intent, context) {
  const sessionId = context?.sessionId || 'default';
  const ctx = getSharedContext(sessionId);

  if (context?.query) ctx.update('search.query', context.query);
  if (context?.userMessage) ctx.update('session.lastMessage', context.userMessage);

  const intentMap = {
    'web-search':        { event: EVENTS.SEARCH_EXECUTE, skill: 'openclaw-tavily-search' },
    'local-search':      { event: EVENTS.SEARCH_EXECUTE, skill: 'local-search' },
    'store-memory':      { event: EVENTS.MEMORY_STORE,   skill: 'memory-store' },
    'create-task':       { event: EVENTS.TASK_CREATE,    skill: 'task-create' },
    'general-search':   { event: EVENTS.SEARCH_EXECUTE, skill: 'openclaw-tavily-search' },
  };

  const mapping = intentMap[intent] || intentMap['general-search'];

  ctx.update('task.status', 'executing');
  ctx.update('task.id', `intent-${intent}-${Date.now()}`);

  const eventData = mapping.event === EVENTS.SEARCH_EXECUTE
    ? { query: context?.query || '', maxResults: context?.maxResults || 5, includeAnswer: false }
    : mapping.event === EVENTS.MEMORY_STORE
    ? { category: context?.category || 'fact', content: context?.content || '', importance: context?.importance || 0.7 }
    : mapping.event === EVENTS.TASK_CREATE
    ? { description: context?.taskDescription || '', plan: context?.plan || null }
    : {};

  const result = bus.emit(mapping.event, eventData, mapping.skill);

  // event._result is set by event-bus _wrapHandler after handler runs
  const handlerResult = result?._result;
  const actualResult = handlerResult?.result || (handlerResult !== undefined ? handlerResult : result || {});

  return {
    success: handlerResult !== undefined ? (handlerResult?.success ?? true) : result !== null,
    result: actualResult,
    skill: mapping.skill,
    nextAction: handlerResult?.nextAction ?? null
  };
}

// ── 注册表状态 ─────────────────────────────────────────────────────────
function getRegistryStatus() {
  const stats = bus.stats();
  return {
    registeredSkills: stats.registeredSkills,
    handlerCount: stats.handlerCount,
    eventsEmitted: stats.eventsEmitted,
    handlersCalled: stats.handlersCalled,
    builtInCount: Object.keys(builtInHandlers).length
  };
}

// ── 初始化 ───────────────────────────────────────────────────────────
registerBuiltInHandlers();

module.exports = { routeIntent, getRegistryStatus, registerBuiltInHandlers };