#!/usr/bin/env node
/**
 * event-bus.js — 简化版事件总线
 * 
 * 为 search-router.js 提供必要的接口
 * 完整版见 zetton 机器原版
 */

const { EventEmitter } = require('events');
const fs = require('fs');
const path = require('path');

const CTX_FILE = path.join(process.env.HOME || '/tmp', '.openclaw', 'cache', 'event-bus-ctx.json');

// ── 事件常量 ──────────────────────────────────────────────────────────
const EVENTS = {
    // 用户事件
    USER_MESSAGE: 'user.message',
    
    // 搜索事件
    SEARCH_EXECUTE: 'search.execute',
    SEARCH_RESULT: 'search.result',
    SEARCH_CACHED: 'search.cached',
    
    // 记忆事件
    MEMORY_STORE: 'memory.store',
    MEMORY_QUERY: 'memory.query',
    MEMORY_RECALL: 'memory.recall',
    MEMORY_RESULT: 'memory.result',
    
    // 任务事件
    TASK_EXECUTE: 'task.execute',
    TASK_COMPLETED: 'task.completed',
    TASK_FAILED: 'task.failed',
    
    // 状态事件
    STATE_TRANSITION: 'state.transition',
    
    // 系统事件
    SYSTEM_READY: 'system.ready',
    SYSTEM_ERROR: 'system.error',
};

// ── SharedContext ─────────────────────────────────────────────────────
class SharedContext {
    constructor(name) {
        this.name = name;
        this.data = {};
        this._load();
    }
    
    _load() {
        try {
            if (fs.existsSync(CTX_FILE)) {
                const all = JSON.parse(fs.readFileSync(CTX_FILE, 'utf8'));
                if (all[this.name]) {
                    this.data = all[this.name];
                }
            }
        } catch (e) {}
    }
    
    _save() {
        try {
            const dir = path.dirname(CTX_FILE);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            let all = {};
            if (fs.existsSync(CTX_FILE)) {
                all = JSON.parse(fs.readFileSync(CTX_FILE, 'utf8'));
            }
            all[this.name] = this.data;
            fs.writeFileSync(CTX_FILE, JSON.stringify(all, null, 2));
        } catch (e) {}
    }
    
    get(key) { return this.data[key]; }
    set(key, value) {
        this.data[key] = value;
        this._save();
    }
    update(data) {
        this.data = { ...this.data, ...data };
        this._save();
    }
    clear() {
        this.data = {};
        this._save();
    }

    transitionTask(phase) {
        // Stub: 返回当前状态对象，供 STATE_TRANSITION 事件使用
        return {
            from: this.data['task.status'] || 'idle',
            to: phase,
            taskId: this.data['task.id'] || null,
            phase
        };
    }
}

// ── EventBus ──────────────────────────────────────────────────────────
class EventBus extends EventEmitter {
    constructor() {
        super();
        this._handlers = {}; // skillName -> { event: handler }
    }

    register(skillName, handlers) {
        // handlers: { eventType: handlerFn }
        this._handlers[skillName] = handlers;
    }

    emit(event, data, targetSkill) {
        const e = { ...data, _event: event, _target: targetSkill, _ts: Date.now() };
        // Call registered handler if targetSkill matches
        if (targetSkill && this._handlers[targetSkill]?.[event]) {
            const handler = this._handlers[targetSkill][event];
            try {
                const result = handler({ data: e, ctx: null });
                e._result = result;
            } catch (err) {
                e._error = err.message;
            }
        }
        super.emit(event, e);
        return e; // Return event object so callers can access e._result
    }

    emitSync(event, data, targetSkill) {
        const e = { ...data, _event: event, _target: targetSkill, _ts: Date.now() };
        const handlers = this.listeners(event);
        if (handlers.length === 0) return null;
        return handlers[0](e);
    }

    stats() {
        return {
            registeredSkills: Object.keys(this._handlers).length,
            handlerCount: Object.values(this._handlers).reduce((n, h) => n + Object.keys(h).length, 0),
            eventsEmitted: 0,
            handlersCalled: 0
        };
    }
}

const _bus = new EventBus();
const _contexts = {};

function getEventBus() { return _bus; }
function getSharedContext(name) {
    if (!_contexts[name]) _contexts[name] = new SharedContext(name);
    return _contexts[name];
}

module.exports = { getEventBus, getSharedContext, EVENTS };
