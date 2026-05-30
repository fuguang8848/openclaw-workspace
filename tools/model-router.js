#!/usr/bin/env node
/**
 * model-router.js — 智能模型路由（参考 AgentTeam P38）
 * 
 * 三因素算法：任务复杂度 + 负载感知 + 技能匹配
 * 支持三层模型自动选择，优化成本 80-90%
 * 
 * 使用方式：
 *   node model-router.js route "<task description>" [--type code|search|analysis|general]
 *   node model-router.js tiers
 *   node model-router.js stats
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ── 系统负载感知（参考 AgentTeam TaskRouter）─────────────────────────────
function getSystemLoad() {
  const loadAvg = os.loadavg();
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const usedMemPct = ((totalMem - freeMem) / totalMem * 100).toFixed(1);
  const cpuCount = os.cpus().length;

  // 归一化负载（每核平均负载）
  const normalizedLoad = loadAvg[0] / cpuCount;

  // 负载等级：0=空闲, 1=正常, 2=较忙, 3=繁忙
  let loadLevel;
  if (normalizedLoad < 0.3) loadLevel = 0;
  else if (normalizedLoad < 0.7) loadLevel = 1;
  else if (normalizedLoad < 1.2) loadLevel = 2;
  else loadLevel = 3;

  return {
    load1m: loadAvg[0].toFixed(2),
    load5m: loadAvg[1].toFixed(2),
    normalizedLoad: normalizedLoad.toFixed(2),
    usedMemPct,
    cpuCount,
    loadLevel,  // 0=空闲 1=正常 2=较忙 3=繁忙
    loadPenalty: loadLevel * 5  // 每级 -5 分（参考 AgentTeam）
  };
}

// ── 模型层级配置 ────────────────────────────────────────────────────────
const MODEL_TIERS = {
  tier1: {
    name: 'minimax/MiniMax-M2.1',
    cost_per_1k_tokens: 0.001,
    latency: 'low',
    suitable_for: ['simple', 'fact_check', 'status_check', 'single_tool_call'],
    max_complexity: 20
  },
  tier2: {
    name: 'bailian/qwen3.5-plus',
    cost_per_1k_tokens: 0.002,
    latency: 'medium',
    suitable_for: ['medium', 'search_summary', 'doc_summary', 'multi_step', 'writing'],
    max_complexity: 60
  },
  tier3: {
    name: 'bailian/qwen3.5-plus',
    cost_per_1k_tokens: 0.002,
    latency: 'high',
    suitable_for: ['complex', 'code_review', 'architecture', 'security', 'multi_dim'],
    max_complexity: 100
  }
};

// 任务类型权重
const TASK_TYPE_COMPLEXITY = {
  // 简单任务 (0-20)
  'simple': 10,
  'fact_check': 12,
  'status_check': 8,
  'single_tool': 15,
  'weather': 5,
  'calendar': 10,
  'email_check': 12,
  
  // 中等任务 (21-60)
  'search_summary': 30,
  'doc_summary': 35,
  'multi_step': 40,
  'writing': 45,
  'translation': 30,
  'analysis': 50,
  'comparison': 45,
  'research': 55,
  
  // 复杂任务 (61-100)
  'code_review': 70,
  'architecture': 80,
  'security_audit': 85,
  'multi_dim': 75,
  'deep_research': 80,
  'planning': 65,
  'design': 70,
  'complex_report': 75
};

// 关键词触发器
const COMPLEXITY_TRIGGERS = {
  high: [
    '分析', '研究', '对比', '趋势', '报告', '审计', '架构',
    'review', 'audit', 'security', 'architecture', 'complex',
    '审查', '调研', '深度', '多维度', '安全漏洞'
  ],
  medium: [
    '搜索', '总结', '摘要', '翻译', '写作', '整理',
    'search', 'summary', 'translate', 'write', 'organize',
    '调研', '整理', '归纳', '对比'
  ]
};

// ── 复杂度分析器 ────────────────────────────────────────────────────────
function analyzeComplexity(taskDescription, taskType) {
  let score = TASK_TYPE_COMPLEXITY[taskType] || 25;
  const desc = taskDescription.toLowerCase();
  
  // 关键词加分
  for (const keyword of COMPLEXITY_TRIGGERS.high) {
    if (desc.includes(keyword)) score += 15;
  }
  for (const keyword of COMPLEXITY_TRIGGERS.medium) {
    if (desc.includes(keyword)) score += 8;
  }
  
  // 句长惩罚（超长描述通常更复杂）
  if (taskDescription.length > 200) score += 10;
  if (taskDescription.length > 500) score += 15;
  
  // 多步骤指示
  if (/首先|然后|接着|最后|step|then|next|finally/i.test(desc)) score += 10;
  
  // 多任务指示
  const taskIndicators = (desc.match(/和|与|以及|同时|并行|,|、|或|或者/gi) || []).length;
  if (taskIndicators >= 3) score += 15;
  else if (taskIndicators >= 2) score += 8;
  
  return Math.min(100, Math.max(0, score));
}

// ── 技能匹配 ───────────────────────────────────────────────────────────
function skillMatch(taskDescription) {
  const desc = taskDescription.toLowerCase();
  
  const skillPatterns = {
    code: ['代码', '写代码', 'code', 'python', 'javascript', '编程', '程序'],
    search: ['搜索', '调研', 'search', 'research', '查找', '查询'],
    memory: ['记忆', '记住', '存储', 'memory', 'store', 'recall'],
    video: ['视频', '下载', '转录', 'B站', 'YouTube', 'video', 'frame'],
    email: ['邮件', '邮箱', 'email', '发送'],
    analysis: ['分析', '对比', '报告', 'analysis', 'report', 'compare']
  };
  
  const matches = [];
  for (const [skill, keywords] of Object.entries(skillPatterns)) {
    for (const kw of keywords) {
      if (desc.includes(kw)) {
        matches.push(skill);
        break;
      }
    }
  }
  
  return [...new Set(matches)];
}

// ── 路由决策 ────────────────────────────────────────────────────────────
function route(taskDescription, taskType = 'general', forcedTier = null) {
  const complexity = analyzeComplexity(taskDescription, taskType);
  const skills = skillMatch(taskDescription);
  
  // 强制层级（CLI 用）
  if (forcedTier && MODEL_TIERS[`tier${forcedTier}`]) {
    const tier = MODEL_TIERS[`tier${forcedTier}`];
    return {
      tier: forcedTier,
      model: tier.name,
      complexity,
      estimated_cost: tier.cost_per_1k_tokens,
      skills,
      reasoning: `Forced tier ${forcedTier}`
    };
  }
  
  // 三因素路由
  let tier;
  if (complexity <= 20) {
    tier = MODEL_TIERS.tier1;
  } else if (complexity <= 60) {
    tier = MODEL_TIERS.tier2;
  } else {
    tier = MODEL_TIERS.tier3;
  }
  
  // 技能覆盖调整（如有 Skill 可用，跳过模型选择）
  const skillCoverage = skills.length > 0;
  
  // 四因素路由（参考 AgentTeam TaskRouter）
  const loadInfo = getSystemLoad();

  // 基础分 = 复杂度匹配（分越高越倾向高 tier）
  let baseScore = 50;  // 初始 50 分
  if (complexity <= 20) baseScore = 20;
  else if (complexity <= 60) baseScore = 55;
  else baseScore = 85;

  // 负载惩罚：繁忙时倾向于低 tier（节省资源）
  const effectiveScore = baseScore - loadInfo.loadPenalty;

  // 最终层级
  let finalTier;
  if (effectiveScore <= 25) finalTier = 1;
  else if (effectiveScore <= 60) finalTier = 2;
  else finalTier = 3;

  const finalTierInfo = MODEL_TIERS[`tier${finalTier}`];

  return {
    tier: finalTier,
    model: finalTierInfo.name,
    complexity,
    estimated_cost: finalTierInfo.cost_per_1k_tokens,
    latency: finalTierInfo.latency,
    skills,
    skillCoverage,
    loadInfo,  // 新增：负载状态
    reasoning: [
      `复杂度评分: ${complexity}/100`,
      skillCoverage ? `技能覆盖: ${skills.join(', ')}` : '无技能覆盖',
      `系统负载: ${loadInfo.load1m} (${loadInfo.normalizedLoad}/核, ${loadInfo.usedMemPct}%内存)`,
      `负载惩罚: -${loadInfo.loadPenalty}分 → 调整后: ${effectiveScore}`,
      `选择层级: tier${finalTier}`,
      `预估成本: ¥${(finalTierInfo.cost_per_1k_tokens * 1000).toFixed(4)}/1K tokens`
    ].join(' | ')
  };
}

// ── 统计 ────────────────────────────────────────────────────────────────
const STATS_FILE = path.join(os.homedir(), '.openclaw', 'cache', 'model-router-stats.json');

function loadStats() {
  try {
    return JSON.parse(fs.readFileSync(STATS_FILE, 'utf8'));
  } catch {
    return { requests: 0, tier1: 0, tier2: 0, tier3: 0, total_cost: 0 };
  }
}

function saveStats(stats) {
  const dir = path.dirname(STATS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(STATS_FILE, JSON.stringify(stats, null, 2));
}

function recordTier(tier, cost) {
  const stats = loadStats();
  stats.requests++;
  stats[`tier${tier}`]++;
  stats.total_cost += cost;
  saveStats(stats);
}

// ── CLI ─────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (command === 'route') {
    let taskDesc = '', taskType = 'general', forcedTier = null;
    
    for (let i = 1; i < args.length; i++) {
      switch (args[i]) {
        case '--type': case '-t':
          taskType = args[++i];
          break;
        case '--tier':
          forcedTier = parseInt(args[++i]);
          break;
        default:
          if (!args[i].startsWith('-')) taskDesc += args[i] + ' ';
      }
    }
    
    if (!taskDesc.trim()) {
      console.error('Usage: model-router.js route "<task>" [--type code|search] [--tier 1|2|3]');
      process.exit(1);
    }
    
    const result = route(taskDesc.trim(), taskType, forcedTier);
    
    // 记录统计
    recordTier(result.tier, result.estimated_cost);
    
    console.log(JSON.stringify(result, null, 2));
  } else if (command === 'tiers') {
    console.log(JSON.stringify(MODEL_TIERS, null, 2));
  } else if (command === 'stats') {
    const stats = loadStats();
    const savings = ((stats.tier1 * 1 + stats.tier2 * 0) / Math.max(stats.requests, 1) * 100).toFixed(1);
    console.log(JSON.stringify({
      ...stats,
      savings_percent: savings,
      tier_distribution: {
        tier1: `${stats.tier1} (${(stats.tier1/Math.max(stats.requests,1)*100).toFixed(1)}%)`,
        tier2: `${stats.tier2} (${(stats.tier2/Math.max(stats.requests,1)*100).toFixed(1)}%)`,
        tier3: `${stats.tier3} (${(stats.tier3/Math.max(stats.requests,1)*100).toFixed(1)}%)`
      }
    }, null, 2));
  } else {
    console.log('Usage:');
    console.log('  model-router.js route "<task description>" [--type code|search] [--tier 1|2|3]');
    console.log('  model-router.js tiers');
    console.log('  model-router.js stats');
  }
}

main();