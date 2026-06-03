# V Design Guidelines

> **来源**：基于 `AgentMemory 2.0 设计稿 (draft)` §5.3 / §8 / §9 抽出的 4 个对 V 真正有用的模式。
> **目的**：V 写新工具 / 改旧工具时的设计参考，**不是必须迁移的清单**。
> **反原则**：能用就行，**别为了"上规范"硬套**。

---

## 0. TL;DR

| 模式 | 一句话 | V 适用场景 |
|---|---|---|
| 1. Protocol + ABC 双轨 | 接口 = Protocol，实现 = ABC | 新增 LLM/embedder/search provider |
| 2. EventBus + Middleware 洋葱 | 异步 pub/sub + 洋葱链处理 | 跨工具事件传递（如 search → observe → rate-limit） |
| 3. TOML 配置 + ENV 分层 | 优先级 CLI > ENV > config > defaults | 任何带配置的工具 |
| 4. MCP server 暴露 | 通过 Model Context Protocol 让外部 agent 调 | 工具要"被 V 之外的 agent 调"时 |

**不适用**：5 个存储层、Reflective Pipeline、Web Dashboard、TS SDK、Docker 镜像 —— V 用不上。

---

## 1. Protocol + ABC 双轨

### 1.1 何时用

- **要新增 / 替换 provider**（LLM、embedder、search engine、vector store）
- **多实现并存**（Ollama 本地 + OpenAI 云 + Anthropic）
- **要 mock 测试**（测试时注入 fake provider）

### 1.2 Python 模板

```python
from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod

# 接口契约 —— 给调用方用，鸭子类型
@runtime_checkable
class LLMProvider(Protocol):
    name: str
    async def chat(self, messages: list[dict], **kw) -> dict: ...

# 抽象基类 —— 给实现方用，强制方法签名
class LLMProviderBase(ABC):
    name: str = "abstract"
    @abstractmethod
    async def chat(self, messages: list[dict], **kw) -> dict: ...

# 具体实现
class OllamaProvider(LLMProviderBase):
    name = "ollama"
    async def chat(self, messages, **kw): ...
    # 满足 LLMProvider Protocol（自动）

# 调用方用 Protocol，工厂用 ABC
def make_provider(name: str) -> LLMProvider:
    if name == "ollama": return OllamaProvider()
    raise ValueError(name)
```

### 1.3 V 现状

| 工具 | 现状 | 是否要升级 |
|---|---|---|
| `search-router.js` | 隐式 adapter 模式（`engine: "tavily" \| "local" \| "bing"`） | ⚠️ 中优先级。改 Protocol 让加新引擎更容易 |
| `search-v.py` | 直连 Bing，0 抽象 | ❌ 太简单，不值得 |
| `model-router.js` | 字符串路由，没抽象 | ⚠️ 同上 |
| Ollama 调用 | 直接 HTTP | ⚠️ 写 Protocol 后多 provider 切换更快 |

### 1.4 反例

- 工具只会有 1 个实现 → 不用 Protocol，直接写
- 内部 helper 函数 → 不用

---

## 2. EventBus + Middleware 洋葱模型

### 2.1 何时用

- 多个独立工具要"互相通知"（如 search 完成 → notify → log → rate-limit）
- 想加 cross-cutting 关注点（日志/限流/脱敏）而不改业务代码
- 想给"事件流"加可观测性

### 2.2 核心代码

```python
import asyncio
from collections import deque
from typing import Callable, Awaitable
from dataclasses import dataclass, field

@dataclass
class Event:
    type: str
    payload: dict
    trace_id: str | None = None

class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable]] = {}
        self._history: deque = deque(maxlen=1000)
    
    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        self._subs.setdefault(event_type, []).append(handler)
    
    async def emit(self, event: Event):
        self._history.append(event)
        await asyncio.gather(
            *(h(event) for h in self._subs.get(event.type, [])),
            return_exceptions=True  # 错误隔离
        )

# Middleware 洋葱
class Middleware:
    name: str
    async def __call__(self, event, next_call) -> Event:
        # 进入：前处理
        result = await next_call(event)
        # 退出：后处理
        return result

# 链式调用
async def run_chain(event: Event, *chain: Middleware, core: Callable):
    async def make_next(idx):
        async def next(ev):
            if idx >= len(chain):
                return await core(ev)
            return await chain[idx](ev, lambda e: make_next(idx+1)(e))
        return next
    return await make_next(0)(event)
```

### 2.3 V 现状

| 工具 | 现状 | 迁移建议 |
|---|---|---|
| `event-tracker.js` | SQLite 事件表，cron 触发 | ✅ 已经做了一半，加 EventBus 抽象即可 |
| `cron jobs` | 每个 cron 独立 systemEvent | ⚠️ 想统一事件流时再用 |
| `memory-inject.js` | 注入记忆到 session，无事件 | ❌ 太简单 |

### 2.4 反例

- 只有 1 个生产者和 1 个消费者 → 直接调函数
- 同步流程（必须等结果）→ 不用 pub/sub

---

## 3. TOML 配置 + ENV 分层

### 3.1 何时用

- 任何带配置的工具（key, URL, threshold 等）
- 想要"不写配置文件就能跑"（ENV 默认值）
- 想要"项目级 / 用户级 / 临时覆盖"分层

### 3.2 优先级（高 → 低）

```
CLI 参数 > ENV 变量 > config.toml > 内置默认
```

### 3.3 Python 模板

```python
import os
import sys
from pathlib import Path
from typing import Any

# Python 3.11+
try:
    import tomllib
except ImportError:
    import tomli as tomllib

CONFIG_DEFAULTS = {
    "llm": {"provider": "ollama", "model": "qwen2.5-7b-q4", "timeout": 60},
    "search": {"engine": "tavily", "top_k": 5},
    "rate_limit": {"per_minute": 60},
}

def load_config(path: str | None = None) -> dict:
    cfg = CONFIG_DEFAULTS.copy()
    # 1. TOML 文件
    if path and Path(path).exists():
        with open(path, "rb") as f:
            file_cfg = tomllib.load(f)
        deep_merge(cfg, file_cfg)
    # 2. ENV 覆盖（AGENTMEMORY_LLM__PROVIDER 等）
    for k, v in os.environ.items():
        if k.startswith("V_") and "__" in k:
            section, key = k[2:].lower().split("__", 1)
            cfg.setdefault(section, {})[key] = coerce(v)
    return cfg

def deep_merge(base, overlay):
    for k, v in overlay.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            deep_merge(base[k], v)
        else:
            base[k] = v

def coerce(s: str) -> Any:
    if s.lower() in ("true", "false"): return s.lower() == "true"
    try: return int(s)
    except: pass
    try: return float(s)
    except: pass
    return s
```

### 3.4 V 现状

| 工具 | 现状 | 迁移建议 |
|---|---|---|
| `search-router.js` | JSON 配置 | ⚠️ 中优先级。改 TOML 后能 ENV 覆盖 |
| `model-router.js` | 硬编码 model 列表 | ✅ 应该改配置驱动 |
| `event-tracker.js` | 硬编码 schema | ⚠️ 同上 |
| `clarifying.js` | 硬编码 prompt 模板 | ✅ 同上 |

### 3.5 反例

- 工具完全无配置（如单文件脚本）→ 不需要
- 配置是"代码"（如 routes 表）→ 用 .ts/.js 不该用 TOML

---

## 4. MCP server 暴露

### 4.1 何时用

- 想让 V 之外的 agent（Claude Code / Cursor / Cline / Aider）调用 V 的工具
- 想给 V 的能力做"标准化接口"（不是 OpenClaw 私货）

### 4.2 现状

V 自身 0 个 MCP server。AgentMemory 2.0 §6.2 设计了 `agentmemory-mcp` 入口。

### 4.3 起步模板

```python
# 参考 mcp 官方 python SDK
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("v-tools")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="v_search",
            description="Search web for query",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="v_memory_search",
            description="Search V long-term memory",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "v_search":
        # delegate to search-router.js
        ...
    elif name == "v_memory_search":
        # delegate to MEMORY.md search
        ...
    return [TextContent(type="text", text="result")]
```

### 4.4 V 优先级

- **低**：V 目前 0 用户接 MCP 的需求（OpenClaw 内是 sub-agent，不走 MCP）
- **中-高**：等浮光想用 Claude Code / Cursor 直连 V 时再做
- **不要做**：为了"看起来专业"硬做

### 4.5 反例

- 工具只在 V 自己 session 用 → 不用 MCP
- 工具没有"被外部 agent 调"的需求 → 不用

---

## 5. 不适用的部分（V 跳过）

| AgentMemory 2.0 模式 | 原因 |
|---|---|
| 5 个存储层（L0-L4） | V 已经有 MEMORY.md + memory/ 简单模式，没必要 |
| Reflective Pipeline (M3) | 现有 heartbeat 每日整理就够 |
| Web Dashboard / TS SDK | V 不是产品 |
| Docker / PyInstaller | V 不打包分发 |
| Tenant 隔离 | V 是单用户 |
| Fernet 加密 / PII 脱敏 | MEMORY.md 是个人用，没 PII 强需求 |
| OpenTelemetry / Prometheus | V 不是分布式服务，结构化日志足够 |
| Fallback chain (provider 切换) | V 跑本地 Ollama，挂了切别的也是单测 |
| Hyrid Retrieval (vector + BM25 + graph) | V 用 `grep` + `read` 够了 |

---

## 6. 实用主义原则

1. **能用就行** —— 不要为了"上规范"重构已经在工作的工具
2. **新工具优先** —— 设计 guideline 只在写新工具时参考
3. **痛点驱动** —— 现有工具的痛点（如 search-router 改引擎要改代码）才触发升级
4. **不要 ALL-IN** —— 4 个模式是参考库，不是必做清单
5. **写之前问自己** —— "如果不上这个模式，写起来会多麻烦？多 5 分钟？多 30 分钟？"
   - 5 分钟 → 直接写
   - 30 分钟 → 看场景
   - 1 小时 → 用规范

---

## 7. 相关文件

- **源参考**：`~/AgentMemory/docs/ARCHITECTURE-2.0-draft.md`（3050 行原文）
- **V tools**：`~/.openclaw/workspace/tools/`（12 个现有工具）
- **V skills**：`~/.openclaw/plugin-skills/`（plugin-skills）
- **MCP 起步**：`https://modelcontextprotocol.io/`（待跟进）

---

*更新时机：V 写新工具 / 改旧工具遇到设计选择时回头看。*
*不更新时机：没事别动。*
