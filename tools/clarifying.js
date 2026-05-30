#!/usr/bin/env node
/**
 * clarifying.js — 需求澄清工作流
 * 
 * 当用户需求不明确时，通过多轮提问明确需求
 * 状态机：clarifying → planning → executing → completed
 * 
 * 使用方式：
 *   node clarifying.js init "<task description>"
 *   node clarifying.js answer "<user answer>"
 *   node clarifying.js status
 *   node clarifying.js plan "<plan description>"
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── 状态文件 ──────────────────────────────────────────────────────────────
const STATE_FILE = path.join(process.env.HOME, '.openclaw', 'cache', 'clarifying-state.json');

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch {
    return { phase: 'idle', task: null, questions: [], answers: {}, context: {} };
  }
}

function saveState(state) {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// ── 标准澄清问题库 ──────────────────────────────────────────────────────
const CLARIFYING_QUESTIONS = {
  goal: {
    question: '你最终想达成什么目标？',
    key: 'goal',
    required: true
  },
  constraint: {
    question: '有什么约束条件吗？（时间/预算/技术限制等）',
    key: 'constraint',
    required: false
  },
  audience: {
    question: '这个需求的受众是谁？',
    key: 'audience',
    required: false
  },
  priority: {
    question: '你最看重哪一点？质量/速度/成本',
    key: 'priority',
    required: false
  },
  context: {
    question: '有什么背景信息我需要知道的吗？',
    key: 'context',
    required: false
  }
};

// ── 动作 ─────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const action = args[0];

  if (action === 'init') {
    const taskDesc = args.slice(1).join(' ');
    const state = {
      phase: 'clarifying',
      task: { description: taskDesc, id: `clar-${Date.now()}` },
      questions: [],
      answers: {},
      context: {}
    };
    saveState(state);

    // 输出开场白 + 第一个问题
    const response = `好的，让我先了解一下你的需求。

**需求：** ${taskDesc}

为了更好地帮你，我需要问几个问题：

${CLARIFYING_QUESTIONS.goal.question}`;

    console.log(JSON.stringify({
      success: true,
      response,
      phase: 'clarifying',
      next_question: CLARIFYING_QUESTIONS.goal,
      state
    }));
  } else if (action === 'answer') {
    const answer = args.slice(1).join(' ');
    const state = loadState();
    
    if (state.phase !== 'clarifying') {
      console.log(JSON.stringify({ success: false, error: 'Not in clarifying phase' }));
      return;
    }

    // 找上一个未回答的问题
    const questionKeys = Object.keys(CLARIFYING_QUESTIONS);
    const lastAnsweredIdx = state.questions.length;
    const nextKey = questionKeys[lastAnsweredIdx];

    if (nextKey) {
      const q = CLARIFYING_QUESTIONS[nextKey];
      state.answers[q.key] = answer;
      state.questions.push({ key: q.key, question: q.question, answered: answer });
    }

    // 检查是否还有下一个问题
    const nextNextKey = questionKeys[state.questions.length];
    if (nextNextKey) {
      const nextQ = CLARIFYING_QUESTIONS[nextNextKey];
      saveState(state);
      console.log(JSON.stringify({
        success: true,
        response: nextQ.question,
        phase: 'clarifying',
        next_question: nextQ,
        progress: `${state.questions.length}/${Object.keys(CLARIFYING_QUESTIONS).length}`,
        state
      }));
    } else {
      // 所有问题已回答，进入 planning
      state.phase = 'planning';
      saveState(state);
      const summary = Object.entries(state.answers)
        .map(([k, v]) => `• ${k}: ${v}`)
        .join('\n');
      console.log(JSON.stringify({
        success: true,
        response: `好的，我已经了解你的需求：

${summary}

现在我来制定执行计划...`,
        phase: 'planning',
        answers: state.answers,
        state
      }));
    }
  } else if (action === 'status') {
    const state = loadState();
    console.log(JSON.stringify({ success: true, state }));
  } else if (action === 'reset') {
    saveState({ phase: 'idle', task: null, questions: [], answers: {}, context: {} });
    console.log(JSON.stringify({ success: true, message: 'State reset' }));
  } else {
    console.log('Usage:');
    console.log('  clarifying.js init "<task>"     — 初始化澄清流程');
    console.log('  clarifying.js answer "<ans>"   — 回答当前问题');
    console.log('  clarifying.js status           — 查看当前状态');
    console.log('  clarifying.js reset            — 重置状态');
  }
}

main();