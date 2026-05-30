#!/usr/bin/env node
/**
 * event-tracker.js — 事件追踪系统（参考 AgentTeam P35）
 * 
 * SQLite 持久化 + 异步订阅通知 + 40+ 事件类型
 * 支持查询 API、统计聚合、事件订阅
 * 
 * 使用方式：
 *   node event-tracker.js emit <event_type> <data_json>
 *   node event-tracker.js query [--type <type>] [--actor <actor>] [--limit 50]
 *   node event-tracker.js stats
 *   node event-tracker.js subscribe <event_type>
 *   node event-tracker.js pending
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const EventEmitter = require('events');

// ── 配置 ─────────────────────────────────────────────────────────────────
const DB_PATH = path.join(os.homedir(), '.openclaw', 'cache', 'event-tracker.db');
const POOL_SIZE = 3;

// ── 简单连接池（queue-based）────────────────────────────────────────────
class SimplePool {
  constructor(size) {
    this.size = size;
    this.connections = [];
    this.queue = [];
    this._init();
  }

  _init() {
    for (let i = 0; i < this.size; i++) {
      this.connections.push(this._createConn());
    }
  }

  _createConn() {
    // SQLite 连接（延迟加载，第一次使用时初始化）
    let sqlite3;
    try {
      sqlite3 = require('better-sqlite3');
    } catch {
      sqlite3 = null;
    }
    return { conn: null, sqlite3, inUse: false };
  }

  _getConn() {
    const available = this.connections.find(c => !c.inUse);
    if (available) {
      available.inUse = true;
      if (!available.conn) {
        // WAL 模式优化
        if (available.sqlite3) {
          available.conn = new available.sqlite3(DB_PATH);
          available.conn.pragma('journal_mode = WAL');
          available.conn.pragma('busy_timeout = 5000');
        }
      }
      return available;
    }
    return null;
  }

  _releaseConn(conn) {
    conn.inUse = false;
  }

  run(sql, params = []) {
    const conn = this._getConn();
    if (!conn) return null;
    try {
      if (conn.sqlite3 && conn.conn) {
        return conn.conn.prepare(sql).run(...params);
      }
      return null;
    } finally {
      this._releaseConn(conn);
    }
  }

  query(sql, params = []) {
    const conn = this._getConn();
    if (!conn) return [];
    try {
      if (conn.sqlite3 && conn.conn) {
        return conn.conn.prepare(sql).all(...params);
      }
      return [];
    } finally {
      this._releaseConn(conn);
    }
  }
}

// ── 数据库初始化 ─────────────────────────────────────────────────────────
function initDb(pool) {
  pool.run(`
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event TEXT NOT NULL,
      actor TEXT,
      target TEXT,
      data TEXT,
      timestamp REAL NOT NULL,
      processed INTEGER DEFAULT 0
    )
  `);
  pool.run(`CREATE INDEX IF NOT EXISTS idx_events_type ON events(event)`);
  pool.run(`CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)`);
  pool.run(`CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor)`);
}

// ── 事件类型定义（参考 AgentTeam 40+ 事件）────────────────────────────────
const EVENT_TYPES = {
  // Agent 生命周期
  AGENT_STARTED: { category: 'agent', priority: 'medium' },
  AGENT_COMPLETED: { category: 'agent', priority: 'medium' },
  AGENT_FAILED: { category: 'agent', priority: 'high' },
  AGENT_STOPPED: { category: 'agent', priority: 'low' },
  AGENT_PAUSED: { category: 'agent', priority: 'medium' },
  AGENT_RESUMED: { category: 'agent', priority: 'medium' },
  
  // 团队生命周期
  TEAM_CREATED: { category: 'team', priority: 'medium' },
  TEAM_DISSOLVED: { category: 'team', priority: 'medium' },
  
  // 任务生命周期
  TASK_CREATED: { category: 'task', priority: 'medium' },
  TASK_ASSIGNED: { category: 'task', priority: 'medium' },
  TASK_COMPLETED: { category: 'task', priority: 'low' },
  TASK_FAILED: { category: 'task', priority: 'high' },
  TASK_BLOCKED: { category: 'task', priority: 'medium' },
  TASK_UNBLOCKED: { category: 'task', priority: 'medium' },
  
  // 消息
  MESSAGE_SENT: { category: 'message', priority: 'low' },
  MESSAGE_RECEIVED: { category: 'message', priority: 'low' },
  
  // 系统
  SYSTEM_READY: { category: 'system', priority: 'high' },
  SYSTEM_ERROR: { category: 'system', priority: 'critical' },
  
  // 搜索
  SEARCH_EXECUTE: { category: 'search', priority: 'low' },
  SEARCH_RESULT: { category: 'search', priority: 'low' },
  SEARCH_CACHED: { category: 'search', priority: 'low' },
  
  // 记忆
  MEMORY_STORE: { category: 'memory', priority: 'medium' },
  MEMORY_RECALL: { category: 'memory', priority: 'medium' },
  MEMORY_INJECT: { category: 'memory', priority: 'medium' },
  
  // 上下文
  CONTEXT_UPDATE: { category: 'context', priority: 'medium' },
  STATE_TRANSITION: { category: 'context', priority: 'low' },
  
  // 技能
  SKILL_REGISTER: { category: 'skill', priority: 'medium' },
  SKILL_MATCH: { category: 'skill', priority: 'medium' },
  SKILL_CALL: { category: 'skill', priority: 'medium' },
  SKILL_RESULT: { category: 'skill', priority: 'medium' },
  
  // 用户交互
  USER_MESSAGE: { category: 'user', priority: 'medium' },
  USER_FEEDBACK: { category: 'user', priority: 'medium' }
};

// ── 事件发布 ─────────────────────────────────────────────────────────────
function emit(pool, eventType, data = {}, actor = 'openclaw', target = null) {
  const eventDef = EVENT_TYPES[eventType] || { category: 'unknown', priority: 'medium' };
  const timestamp = Date.now() / 1000;
  
  pool.run(
    `INSERT INTO events (event, actor, target, data, timestamp, processed) VALUES (?, ?, ?, ?, ?, 0)`,
    [eventType, actor, target || '', JSON.stringify(data), timestamp]
  );
  
  // 通知订阅者
  notifySubscribers(eventType, { event: eventType, actor, target, data, timestamp });
  
  return { event: eventType, actor, target, timestamp, id: Date.now() };
}

// ── 订阅者管理 ───────────────────────────────────────────────────────────
const subscribers = new Map(); // eventType -> [callback, ...]
const emitter = new EventEmitter();
emitter.setMaxListeners(100);

function subscribe(eventType, callback) {
  if (!subscribers.has(eventType)) {
    subscribers.set(eventType, []);
  }
  subscribers.get(eventType).push(callback);
  return () => {
    // unsubscribe
    const cbs = subscribers.get(eventType);
    if (cbs) {
      const idx = cbs.indexOf(callback);
      if (idx >= 0) cbs.splice(idx, 1);
    }
  };
}

function notifySubscribers(eventType, eventData) {
  const cbs = subscribers.get(eventType) || [];
  const wildcardCbs = subscribers.get('*') || [];
  
  [...cbs, ...wildcardCbs].forEach(cb => {
    try {
      // 5秒超时保护
      const timeout = setTimeout(() => {}, 5000);
      cb(eventData);
      clearTimeout(timeout);
    } catch (e) {
      console.error(`[EventTracker] subscriber error: ${e.message}`);
    }
  });
  
  emitter.emit(eventType, eventData);
}

// ── 查询 ─────────────────────────────────────────────────────────────────
function query(pool, options = {}) {
  const { eventType, actor, target, limit = 50, offset = 0 } = options;
  
  let sql = `SELECT * FROM events WHERE 1=1`;
  const params = [];
  
  if (eventType) {
    sql += ` AND event = ?`;
    params.push(eventType);
  }
  if (actor) {
    sql += ` AND actor = ?`;
    params.push(actor);
  }
  if (target) {
    sql += ` AND target = ?`;
    params.push(target);
  }
  
  sql += ` ORDER BY timestamp DESC LIMIT ? OFFSET ?`;
  params.push(limit, offset);
  
  const rows = pool.query(sql, params);
  return rows.map(row => ({
    ...row,
    data: row.data ? JSON.parse(row.data) : {}
  }));
}

// ── 统计 ─────────────────────────────────────────────────────────────────
function getStats(pool) {
  const total = pool.query(`SELECT COUNT(*) as count FROM events`)[0]?.count || 0;
  
  const byType = pool.query(`
    SELECT event, COUNT(*) as count 
    FROM events 
    GROUP BY event 
    ORDER BY count DESC 
    LIMIT 20
  `);
  
  const recent = pool.query(`
    SELECT event, timestamp 
    FROM events 
    ORDER BY timestamp DESC 
    LIMIT 10
  `);
  
  const byCategory = {};
  for (const [eventType, def] of Object.entries(EVENT_TYPES)) {
    const row = pool.query(`SELECT COUNT(*) as count FROM events WHERE event = ?`, [eventType])[0];
    if (row?.count > 0) {
      byCategory[def.category] = (byCategory[def.category] || 0) + row.count;
    }
  }
  
  return { total, byType, byCategory, recent };
}

// ── CLI ─────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  // 初始化连接池
  let pool;
  try {
    pool = new SimplePool(POOL_SIZE);
    initDb(pool);
  } catch (e) {
    console.error(JSON.stringify({ success: false, error: `DB init failed: ${e.message}` }));
    process.exit(1);
  }

  if (command === 'emit') {
    const [eventType, ...rest] = args.slice(1);
    if (!eventType) {
      console.error('Usage: event-tracker.js emit <event_type> [data_json]');
      process.exit(1);
    }
    
    let data = {};
    try {
      if (rest.length > 0) {
        data = JSON.parse(rest.join(' '));
      }
    } catch {
      // 忽略解析错误
    }
    
    const result = emit(pool, eventType, data, 'cli', null);
    console.log(JSON.stringify({ success: true, ...result }));
  } else if (command === 'query') {
    const options = { limit: 50 };
    for (let i = 1; i < args.length; i++) {
      switch (args[i]) {
        case '--type': options.eventType = args[++i]; break;
        case '--actor': options.actor = args[++i]; break;
        case '--target': options.target = args[++i]; break;
        case '--limit': options.limit = parseInt(args[++i]); break;
        case '--offset': options.offset = parseInt(args[++i]); break;
      }
    }
    
    const events = query(pool, options);
    console.log(JSON.stringify({ success: true, count: events.length, events }));
  } else if (command === 'stats') {
    const stats = getStats(pool);
    console.log(JSON.stringify({ success: true, ...stats }, null, 2));
  } else if (command === 'subscribe') {
    const eventType = args[1] || '*';
    console.log(`Listening for ${eventType} events...`);
    
    const unsub = subscribe(eventType, (eventData) => {
      console.log(JSON.stringify(eventData));
    });
    
    // 保持运行
    process.on('SIGINT', () => { unsub(); process.exit(0); });
  } else if (command === 'pending') {
    const events = query(pool, { limit: 100 });
    console.log(JSON.stringify({ success: true, count: events.length, events }, null, 2));
  } else if (command === 'types') {
    console.log(JSON.stringify({ success: true, types: Object.keys(EVENT_TYPES) }, null, 2));
  } else {
    console.log('Usage:');
    console.log('  event-tracker.js emit <event_type> [data_json]');
    console.log('  event-tracker.js query [--type <type>] [--actor <actor>] [--limit 50]');
    console.log('  event-tracker.js stats');
    console.log('  event-tracker.js subscribe <event_type>');
    console.log('  event-tracker.js pending');
    console.log('  event-tracker.js types');
  }
}

main();