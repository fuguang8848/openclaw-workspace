#!/usr/bin/env node
/**
 * router-agent.js — 意图分类 + 事件路由层
 *
 * 职责：
 *  1. 接收用户消息，分类意图
 *  2. 调用 skill-handler 处理
 *  3. 返回结构化结果 + 决定是否继续
 *
 * 意图类型：
 *  - search    → Tavily / 本地搜索
 *  - memory    → 存储 / 检索记忆
 *  - task      → 创建 / 更新任务
 *  - conversation → 直接回复（不经过事件总线）
 *  - unknown   → 降级到 general-search
 */

const { routeIntent, getRegistryStatus } = require('./skill-handler.js');
const { getSharedContext, EVENTS } = require('./event-bus.js');

// ── 意图分类规则 ────────────────────────────────────────────────────

const INTENT_PATTERNS = {
  search: [
    /(?:搜?|搜索|查找|帮我找|look up|search|find)/i,
    /(?:最新|新闻|动态|趋势)/i,
    /(?:调研|研究|research)/i,
  ],
  memory_store: [
    /(?:记住|记一下|存储|保存|save|remember|store)/i,
    /(?:重要|值得记住)/i,
  ],
  memory_recall: [
    /(?:之前|上次|记得|回忆|recall|还记得)/i,
  ],
  task_create: [
    /(?:创建任务|新建任务|待办|todo|安排)/i,
    /(?:task|任务)/i,
  ],
  conversation: [
    /(?:你好|hi|hello|早上好|下午好|晚上好)/i,
    /[？\\?]$/,
  ],
};

/**
 * 分类用户消息意图
 * @param {string} message
 * @returns {string} intent type
 */
function classifyIntent(message) {
  const lower = message.toLowerCase();

  // Priority order: most specific first
  const priority = ['memory_store', 'task_create', 'memory_recall', 'search', 'conversation'];

  for (const intent of priority) {
    const patterns = INTENT_PATTERNS[intent];
    if (!patterns) continue;
    for (const pattern of patterns) {
      if (pattern.test(lower)) return intent;
    }
  }

  return 'unknown';
}

/**
 * 复杂度判断：是否需要深度搜索
 * @param {string} query
 * @returns {boolean}
 */
function needsDeepSearch(query) {
  const deepPatterns = [
    /分析|对比|研究|趋势|报告|review/i,
    /测评|评测|比较|comparison/i,
    /如何|怎么|why|how to/i,
    /最佳|最好|推荐|top|best/i,
  ];
  return deepPatterns.some(p => p.test(query));
}

/**
 * 主路由函数
 * @param {string} message - 用户原始消息
 * @param {object} context - 额外上下文 { sessionId, userId, ... }
 * @returns {object} { intent, skill, success, response, data, nextAction }
 */
function router(message, context = {}) {
  const sessionId = context.sessionId || 'default';
  const ctx = getSharedContext(sessionId);

  // 更新会话上下文
  ctx.update('session.lastMessage', message);
  ctx.update('session.timestamp', Date.now());

  // 分类意图
  const intent = classifyIntent(message);

  let result;

  switch (intent) {
    case 'search':
    case 'unknown': {
      // 提取搜索 query
      const query = extractSearchQuery(message);
      const maxResults = needsDeepSearch(query) ? 5 : 3;

      result = routeIntent('general-search', { query, maxResults });

      ctx.update('search.query', query);
      ctx.update('search.count', result.result?.results?.length || 0);

      return buildResponse('search', result, {
        query,
        results: result.result?.results || [],
        nextAction: 'continue'
      });
    }

    case 'memory_store': {
      const { category, content } = extractMemoryData(message);
      result = routeIntent('store-memory', { category, content, importance: 0.7 });

      return buildResponse('memory', result, {
        stored: result.result?.stored,
        category,
        nextAction: 'continue'
      });
    }

    case 'task_create': {
      const { description, plan } = extractTaskData(message);
      result = routeIntent('create-task', { taskDescription: description, plan });

      return buildResponse('task', result, {
        taskId: result.result?.taskId,
        description,
        nextAction: 'continue'
      });
    }

    case 'conversation':
    default: {
      // 不走事件总线，直接标记为对话
      ctx.update('task.status', 'idle');

      return {
        intent: 'conversation',
        skill: null,
        success: false,
        response: null,
        data: {},
        nextAction: 'conversation'
      };
    }
  }
}

/**
 * 构建标准响应结构
 */
function buildResponse(intent, routeResult, extra = {}) {
  return {
    intent,
    skill: routeResult.skill,
    success: routeResult.success,
    response: formatResults(intent, routeResult.result, extra),
    data: extra,
    nextAction: routeResult.nextAction || 'continue'
  };
}

/**
 * 格式化结果为可读文本
 */
function formatResults(intent, result, extra) {
  if (!result) return null;

  switch (intent) {
    case 'search': {
      const results = result.results || [];
      if (!results.length) return '未找到相关结果';
      return results.map((r, i) => `${i + 1}. ${r.title}\n   ${r.url || ''}`).join('\n\n');
    }
    case 'memory':
      return `✅ 已存储：${extra.category}`;
    case 'task':
      return `✅ 任务已创建：${extra.description}`;
    default:
      return null;
  }
}

/**
 * 从消息中提取搜索 query
 */
function extractSearchQuery(message) {
  let query = message.replace(/[。！??\?]$/, '').trim();

  const prefixes = ['帮我搜一下', '帮我找一下', '帮我查一下', '搜一下', '搜索', '查找', '帮我找', '帮我搜', '帮我查', 'look up', 'search', 'find', '研究一下', '调研'];
  for (const p of prefixes) {
    if (query.startsWith(p)) {
      query = query.slice(p.length).trim();
    }
  }

  return query || message;
}

/**
 * 从消息中提取记忆数据
 */
function extractMemoryData(message) {
  const match = message.match(/(?:记住|记一下|存储|save)\s*(?:到|到)?([\w]+)?:?\s*(.+)/i);
  return {
    category: match?.[1] || 'fact',
    content: match?.[2] || message
  };
}

/**
 * 从消息中提取任务数据
 */
function extractTaskData(message) {
  const match = message.match(/(?:创建|新建|添加)\s*(?:任务)?:?\s*(.+)/i);
  return {
    description: match?.[1] || message,
    plan: null
  };
}

// ── 统计信息 ────────────────────────────────────────────────────────

function getRouterStats() {
  return getRegistryStatus();
}

// ── CLI 测试 ──────────────────────────────────────────────────────────

if (require.main === module) {
  const args = process.argv.slice(2).filter(a => !a.startsWith('--'));
  const isJson = process.argv.includes('--json');
  const msg = args[0] || '搜索 AI 最新动态';

  const intent = classifyIntent(msg);
  const r = router(msg, { sessionId: 'cli-test' });

  if (isJson) {
    console.log(JSON.stringify(r));
  } else {
    console.log('\nRouter Test: "' + msg + '"');
    console.log('-'.repeat(40));
    console.log('Intent:', intent);
    console.log('Skill:', r.skill || '(conversation)');
    console.log('Success:', r.success);
    if (r.response) console.log('Result:\n' + r.response);
  }
}

module.exports = { router, classifyIntent, getRouterStats };