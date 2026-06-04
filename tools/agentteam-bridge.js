#!/usr/bin/env node
/**
 * agentteam-bridge.js — V ↔ AgentTeam 桥接层
 * 
 * 目的：让 V 接到任务时能"借力"AgentTeam（多 agent 协作），同时保留 V 自己的轻量路由
 * 原则：集成不替换。V model-router 仍负责单次决策；本桥接负责"分发到 team"
 * 
 * 命令：
 *   init                                — 初始化 v-core team（一次性）
 *   post-task <subject> [desc]          — V → AgentTeam 推一个 task
 *   update-task <task-id> <status>      — 更新 task 状态（pending/in_progress/completed）
 *   list-tasks [status]                 — 列出 v-core team 的 task
 *   recommend <task description>        — V 决策辅助：是否分发到 AgentTeam
 *   status                              — 团队状态总览
 * 
 * 设计：
 *   - 单一团队 v-core（V 的"虚拟团队"），所有 V 创建的 task 都进这里
 *   - 浮光通过 AgentTeam Web UI (http://127.0.0.1:8080) 看到 v-core 看板
 *   - 浮光作为 leader / 决策者，V 作为 task creator
 */

const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// ── 配置 ────────────────────────────────────────────────────────────────
const TEAM_NAME = 'v-core';
const TEAM_DESC = 'V 的虚拟协作团队（model-router / spring-cleanup / 自驱巡检 等任务）';
const AT_BIN = '/home/fuguang/.local/bin/agentteam';
const STATE_FILE = path.join(os.homedir(), '.openclaw', 'cache', 'agentteam-bridge-state.json');

// ── AgentTeam CLI 包装 ──────────────────────────────────────────────────
function at(...args) {
  return new Promise((resolve, reject) => {
    execFile(AT_BIN, args, { cwd: '/home/fuguang/AgentTeam', maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) {
        // AgentTeam 很多命令会在无 team / 无 task 时返回非 0 — 但 stdout 仍有信息
        if (stdout && stdout.trim().length > 0) {
          return resolve({ ok: false, stdout: stdout.trim(), stderr: (stderr || '').trim(), code: err.code });
        }
        return reject(new Error(`agentteam ${args[0]} failed: ${err.message}\nstderr: ${stderr}`));
      }
      resolve({ ok: true, stdout: stdout.trim(), stderr: (stderr || '').trim(), code: 0 });
    });
  });
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); }
  catch { return { teamCreated: false, lastInit: null, taskCounter: 0 }; }
}
function saveState(s) {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
}

// ── 子命令 ──────────────────────────────────────────────────────────────
async function init() {
  const state = loadState();
  if (state.teamCreated) {
    return { ok: true, message: `team "${TEAM_NAME}" already initialized at ${state.lastInit}`, state };
  }
  const r = await at('team', 'create', TEAM_NAME, '--description', TEAM_DESC);
  // 重复创建会报错但不影响 — 标记为已初始化
  state.teamCreated = true;
  state.lastInit = new Date().toISOString();
  saveState(state);
  return { ok: true, message: `team "${TEAM_NAME}" ready`, cliOutput: r.stdout || r.stderr, state };
}

async function postTask(subject, description = '') {
  await ensureInit();
  const state = loadState();
  state.taskCounter++;
  saveState(state);
  const r = await at('task', 'create', TEAM_NAME, subject, '--description', description);
  return { ok: true, subject, description, cliOutput: r.stdout || r.stderr };
}

async function updateTask(taskId, status) {
  await ensureInit();
  const valid = ['pending', 'in_progress', 'completed', 'blocked'];
  if (!valid.includes(status)) {
    return { ok: false, error: `invalid status: ${status}. valid: ${valid.join(',')}` };
  }
  const r = await at('task', 'update', TEAM_NAME, taskId, '--status', status);
  return { ok: true, taskId, status, cliOutput: r.stdout || r.stderr };
}

async function listTasks(status = null) {
  await ensureInit();
  const args = ['task', 'list', TEAM_NAME];
  if (status) args.push('--status', status);
  const r = await at(...args);
  return { ok: true, tasks: r.stdout };
}

async function status() {
  const r = await at('team', 'status', TEAM_NAME);
  return { ok: true, team: TEAM_NAME, status: r.stdout };
}

// ── V 决策辅助：是否分发到 AgentTeam ─────────────────────────────────────
// 触发条件（任一）：
//   1. 描述里含"多 agent / 团队 / 并行 / 协作 / 调研 + 报告 / 部署"
//   2. 复杂度 > 60（V 自己的 model-router 给出的）
//   3. 涉及 3+ 子任务（逗号 / "和" / "以及"）
// 命中 → recommend = "launch-team"
function recommend(taskDescription, complexityScore = null) {
  const desc = (taskDescription || '').toLowerCase();
  const triggers = {
    explicitTeam: /多\s*agent|团队协作|并行|协作|launch\s*team|spawn\s*team/i.test(desc),
    multiStep: /调研.{0,8}报告|搜索.{0,8}总结|分析.{0,8}对比|部署.{0,8}测试/i.test(desc),
    manySubtasks: (desc.match(/[、，,；;]|以及|和|与|然后|接着|最后/gi) || []).length >= 3,
    highComplexity: complexityScore !== null && complexityScore > 60
  };
  const shouldLaunch = Object.values(triggers).some(Boolean);
  return {
    shouldLaunch,
    triggers,
    suggestion: shouldLaunch
      ? `建议分发到 AgentTeam：${TEAM_NAME}。调用 \`agentteam-bridge post-task "<subject>" "<desc>"\` 创建 task，浮光可在 web UI 看到。`
      : 'V 单独处理（无需多 agent 协作）',
    fallback: shouldLaunch ? 'launch' : 'solo'
  };
}

async function ensureInit() {
  const state = loadState();
  if (!state.teamCreated) {
    await init();
  }
}

// ── CLI ────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  try {
    if (cmd === 'init') {
      console.log(JSON.stringify(await init(), null, 2));
    } else if (cmd === 'post-task') {
      const subject = args[1];
      const description = args.slice(2).join(' ') || '';
      if (!subject) throw new Error('Usage: post-task <subject> [description]');
      console.log(JSON.stringify(await postTask(subject, description), null, 2));
    } else if (cmd === 'update-task') {
      const taskId = args[1], status = args[2];
      if (!taskId || !status) throw new Error('Usage: update-task <task-id> <status>');
      console.log(JSON.stringify(await updateTask(taskId, status), null, 2));
    } else if (cmd === 'list-tasks') {
      console.log(JSON.stringify(await listTasks(args[1]), null, 2));
    } else if (cmd === 'status') {
      console.log(JSON.stringify(await status(), null, 2));
    } else if (cmd === 'recommend') {
      const desc = args.slice(1).join(' ');
      const complexity = parseInt(process.env.COMPLEXITY || '0') || null;
      if (!desc) throw new Error('Usage: recommend <task description> [COMPLEXITY=score]');
      console.log(JSON.stringify(recommend(desc, complexity), null, 2));
    } else {
      console.log('Usage:');
      console.log('  init                            — 初始化 v-core team');
      console.log('  post-task <subject> [desc]      — V → AgentTeam 推 task');
      console.log('  update-task <id> <status>       — 更新 task 状态');
      console.log('  list-tasks [status]             — 列出 v-core tasks');
      console.log('  status                          — 团队状态');
      console.log('  recommend <desc> [COMPLEXITY=N] — V 决策辅助');
    }
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
}

main();
