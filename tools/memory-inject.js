#!/usr/bin/env node
/**
 * memory-inject.js — 主动记忆注入工具
 * 
 * 从 OpenClaw 长期记忆中检索相关内容，注入当前会话
 * 策略：
 *   1. 优先直接读取文件（MEMORY.md + daily notes）— 最可靠
 *   2. Gateway RPC 作为备用（WebSocket 协议）
 * 
 * 使用方式：
 *   node memory-inject.js <query> [--max 5]
 *   node memory-inject.js "浮光" --max 3
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── 直接文件读取（主路径）────────────────────────────────────────────────
function searchFiles(query, maxResults = 5) {
  const workspace = path.join(os.homedir(), '.openclaw', 'workspace');
  const results = [];

  // 搜索 MEMORY.md
  const memPath = path.join(workspace, 'MEMORY.md');
  if (fs.existsSync(memPath)) {
    const content = fs.readFileSync(memPath, 'utf8');
    const score = content.includes(query) ? 0.9 : 0;
    if (score > 0) {
      results.push({
        content: content.slice(0, 2000),
        type: 'context',
        importance: score,
        source: 'MEMORY.md'
      });
    }
  }

  // 搜索 daily notes
  const memDir = path.join(workspace, 'memory');
  if (fs.existsSync(memDir)) {
    const files = fs.readdirSync(memDir)
      .filter(f => /^\d{4}-\d{2}-\d{2}\.md$/.test(f))
      .sort()
      .reverse()
      .slice(0, 7); // 最近7天

    for (const file of files) {
      const content = fs.readFileSync(path.join(memDir, file), 'utf8');
      if (content.includes(query)) {
        results.push({
          content: content.slice(0, 1500),
          type: 'context',
          importance: 0.6,
          source: file
        });
      }
    }
  }

  return results.slice(0, maxResults);
}

// ── 记忆类型推断 ────────────────────────────────────────────────────────
function inferMemoryType(query) {
  const q = query.toLowerCase();
  if (/偏好|喜欢|讨厌|风格/.test(q)) return 'preference';
  if (/项目|任务|工作/.test(q)) return 'project';
  if (/人|名字|谁/.test(q)) return 'entity';
  if (/决定|选择|方案/.test(q)) return 'decision';
  return 'context';
}

// ── 主流程 ──────────────────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);
  let query = '', maxResults = 5;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--max': case '-n': maxResults = parseInt(args[++i]); break;
      default: if (!args[i].startsWith('-')) query = args[i];
    }
  }

  if (!query) {
    console.error('Usage: memory-inject.js <query> [--max 5]');
    process.exit(1);
  }

  try {
    const items = searchFiles(query, maxResults);
    const memType = inferMemoryType(query);

    const injected = items.map((item, idx) => ({
      index: idx + 1,
      content: item.content,
      type: item.type || memType,
      importance: item.importance || 0.5,
      source: item.source || 'unknown'
    }));

    console.log(JSON.stringify({
      query,
      injected_count: injected.length,
      memories: injected,
      success: true
    }, null, 2));
  } catch (e) {
    console.error(JSON.stringify({ success: false, error: e.message }));
    process.exit(1);
  }
}

main();