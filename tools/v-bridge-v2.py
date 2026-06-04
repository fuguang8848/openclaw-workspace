#!/usr/bin/env python3
"""
v-bridge-v2.py — VCP 网关版 r1-bridge (V 端 11:30 升级)

【升级点（vs r1-bridge.py）】
1. 走 VCP 网关 (http://127.0.0.1:6005) — 一次接 5 模型 + 2 虚拟模型
2. Bearer token 认证 (vcp_local_2026)
3. 5 模型自动 fallback: qwen 7B → MiniMax-M3 → MiniMax-M2.7 → VCPModelAuto → R1 70B
4. 3 次重试 + 指数 backoff (1s, 2s, 4s)
5. 默认非流式（V 11:30 验: 非流式比流式快 3-10 倍）
6. 保留 4 个工具 (exec/read/write/search)

【用法】
  ./v-bridge-v2.py "今天 daily memory 几号"     # 默认 qwen 7B
  ./v-bridge-v2.py --model VCPModelAuto "你好"   # 虚拟模型自动选
  ./v-bridge-v2.py --model deepseek-r1:70b-q4-4k "1+1"

【来源】浮光 11:25 指示学习 hermes 对 VCP 思考报告, V 端借鉴 VCP 模型网关
【v-journal】V-学习hermes对VCP思考-2026-06-04.md
"""
import sys
import os
import json
import re
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

# === VCP 网关配置 (永久) ===
VCP_URL = os.environ.get("VCP_URL", "http://127.0.0.1:6005")
# V 11:33 多看一层: 占位 "***" 不能用 (VCP 返 401), 改默认真值
# 优先级: 环境变量 VCP_TOKEN > config.env > 硬编码
_VCP_TOKEN_DEFAULT = "vcp_local_2026"
VCP_TOKEN = os.environ.get("VCP_TOKEN") or _VCP_TOKEN_DEFAULT

# === Fallback 模型链 (按速度优先) ===
DEFAULT_FALLBACK = [
    "qwen2.5-7b-q4:latest",        # 本地最快 1.72s (V 11:30 实测)
    "MiniMax-M3",            # V 默认云模型
    "MiniMax-M2.7",          # V 备用
    "VCPModelAuto",          # 虚拟模型自动分发 (V 11:30 5.26s)
    "deepseek-r1:70b-q4-4k", # 最慢, iGPU 0.58 t/s
]

TOOL_CALL_TIMEOUT = 30
MAX_ITER = 8
MAX_RETRY = 3

# ---------- Tool implementations (跟 r1-bridge 一样) ----------
def tool_exec(cmd):
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=TOOL_CALL_TIMEOUT, cwd=os.getcwd(),
        )
        out = r.stdout
        err = r.stderr
        if len(out) > 4000:
            out = out[:4000] + f"\n... (truncated, total {len(r.stdout)} chars)"
        return f"returncode: {r.returncode}\nstdout: {out}\nstderr: {err}"
    except subprocess.TimeoutExpired:
        return f"error: command timeout ({TOOL_CALL_TIMEOUT}s)"
    except Exception as e:
        return f"error: {e}"


def tool_read(path):
    try:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.exists():
            return f"error: file not found: {p}"
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 8000:
            text = text[:8000] + f"\n... (truncated, total {len(text)} chars)"
        return text
    except Exception as e:
        return f"error: {e}"


def tool_write(path, content):
    try:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"written {len(content)} bytes to {p}"
    except Exception as e:
        return f"error: {e}"


def tool_search(query):
    try:
        sv = Path.home() / ".openclaw" / "workspace" / "tools" / "search-v.py"
        if not sv.exists():
            return f"error: search-v.py not found at {sv}"
        r = subprocess.run(
            ["python3", str(sv), query],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return f"error: search-v.py failed: {r.stderr[:500]}"
        try:
            results = json.loads(r.stdout)
            lines = []
            for i, item in enumerate(results[:5], 1):
                lines.append(f"{i}. {item.get('title', '')}")
                lines.append(f"   {item.get('url', '')}")
                lines.append(f"   {item.get('snippet', '')}")
            return "\n".join(lines) if lines else "no results"
        except json.JSONDecodeError:
            return r.stdout[:3000]
    except subprocess.TimeoutExpired:
        return "error: search timeout (20s)"
    except Exception as e:
        return f"error: {e}"


TOOL_MAP = {
    "exec":   lambda a: tool_exec(a.get("cmd", "")),
    "read":   lambda a: tool_read(a.get("path", "")),
    "write":  lambda a: tool_write(a.get("path", ""), a.get("content", "")),
    "search": lambda a: tool_search(a.get("query", "")),
}

# ---------- Tool-call parsing (跟 r1-bridge 一样) ----------
TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(?P<name>\w+)\s*(?P<args>.*?)\s*</tool_call>",
    re.DOTALL,
)
ARG_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"|(\w+)\s*=\s*(\S+)')
VALID_TOOLS = {"exec", "read", "write", "search"}


def infer_tool_from_args(args):
    if not isinstance(args, dict):
        return None
    if "cmd" in args and "path" not in args:
        return "exec"
    if "path" in args and "content" in args:
        return "write"
    if "path" in args:
        return "read"
    if "query" in args:
        return "search"
    return None


def parse_tool_call(content):
    m = TOOL_CALL_RE.search(content)
    if not m:
        return None, None
    name = m.group("name")
    args_str = m.group("args").strip()
    args = {}
    if args_str.startswith("{"):
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            inner = args_str.strip("{} ")
            for am in ARG_RE.finditer(inner):
                key = am.group(1) or am.group(3)
                val = am.group(2) if am.group(2) is not None else am.group(4)
                if val is not None:
                    args[key] = val
    else:
        for am in ARG_RE.finditer(args_str):
            key = am.group(1) or am.group(3)
            val = am.group(2) if am.group(2) is not None else am.group(4)
            if val is not None:
                args[key] = val
    if name not in VALID_TOOLS:
        inferred = infer_tool_from_args(args)
        if inferred:
            name = inferred
    return name, args


def strip_tool_call(content):
    return TOOL_CALL_RE.sub("", content).strip()


# ---------- VCP 网关调用 (v-bridge-v2 升级点) ----------
SYSTEM_PROMPT = """你是 V，一个 AI 私人助理。当前通过 VCP 网关调用本地/云模型。

# 工具集（4 个）
- exec(cmd="shell命令") - 执行 shell，30s timeout
- read(path="文件路径") - 读文件
- write(path="路径", content="内容") - 写文件
- search(query="搜索词") - Bing 搜索

# 调用工具的**唯一**格式
**严格按这个格式调用**。所有参数用 `key="value"`，value 用双引号。

<tool_call>exec cmd="ls -la"</tool_call>
<tool_call>read path="/etc/hostname"</tool_call>
<tool_call>write path="/tmp/x.txt" content="hello"</tool_call>
<tool_call>search query="V是什么意思"</tool_call>

# 完整示例（**逐字照做**）
User: 列出当前目录有什么文件？
Assistant: 我用 exec 调 ls。
<tool_call>exec cmd="ls -la"</tool_call>
[Tool result]
total 12
Assistant: 当前目录有 1 个文件 README.md。

# 规则
1. **调用工具时**，用 `<tool_call><name> key="value"</tool_call>` 格式
2. 工具结果会原样回你。**总结后回答**
3. 工具 error → 换方法
4. **最终回答 ≤ 200 字**
5. **最终回答不要包含 <tool_call> 块**
6. 中文回答
"""


def vcp_chat(model, messages, timeout=120):
    """调 VCP 网关 /v1/chat/completions (v-bridge-v2 核心)"""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,  # V 11:30: 非流式快 3-10 倍
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{VCP_URL}/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VCP_TOKEN}",
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - t0
            return json.loads(resp.read().decode("utf-8")), elapsed
    except urllib.error.HTTPError as e:
        return {"error": f"VCP HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"}, time.time() - t0
    except urllib.error.URLError as e:
        return {"error": f"VCP URL error: {e.reason}"}, time.time() - t0
    except Exception as e:
        return {"error": f"VCP request failed: {e}"}, time.time() - t0


def vcp_chat_with_fallback(messages, models=None, timeout=120, verbose=True):
    """V 端模型自动 fallback (1 套客户端接 5 模型)

    按 models 列表依次尝试, 任一成功就返回。
    返回 (model_used, response_dict, elapsed_total)
    """
    if models is None:
        models = DEFAULT_FALLBACK

    errors = []
    total_t0 = time.time()
    for model in models:
        for retry in range(MAX_RETRY):
            resp, elapsed = vcp_chat(model, messages, timeout=timeout)
            if "error" not in resp:
                if verbose:
                    print(f"[vcp] {model} OK ({elapsed:.1f}s)", file=sys.stderr)
                return model, resp, time.time() - total_t0
            err = resp.get("error", "unknown")[:200]
            errors.append(f"{model} retry {retry+1}: {err}")
            if verbose:
                print(f"[vcp] {model} 失败 ({elapsed:.1f}s): {err}", file=sys.stderr)
            if retry < MAX_RETRY - 1:
                time.sleep(2 ** retry)  # 1s, 2s, 4s
    return None, {"error": f"all models failed: {'; '.join(errors[:3])}"}, time.time() - total_t0


def chat_loop(model_or_fallback, user_query, verbose=True):
    """V 端 chat loop (v-bridge-v2)

    model_or_fallback: str (单 model) 或 list (fallback 链)
    """
    models = model_or_fallback if isinstance(model_or_fallback, list) else [model_or_fallback]
    use_fallback = len(models) > 1

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for i in range(MAX_ITER):
        if verbose:
            tag = "fallback chain" if use_fallback else models[0]
            print(f"\n[iter {i+1}/{MAX_ITER}] {tag}...", file=sys.stderr, flush=True)

        if use_fallback:
            model_used, resp, _ = vcp_chat_with_fallback(messages, models=models, verbose=verbose)
            if model_used is None:
                return f"❌ {resp.get('error', 'unknown')}"
        else:
            resp, _ = vcp_chat(models[0], messages)
            if "error" in resp:
                return f"❌ {resp['error']}"

        # VCP OpenAI 格式: choices[0].message.content
        msg = resp.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "")
        messages.append({"role": "assistant", "content": content})

        # 解析 tool call
        name, args = parse_tool_call(content)
        if not name:
            return strip_tool_call(content)

        # 调工具
        if verbose:
            print(f"[tool_call] {name}({json.dumps(args, ensure_ascii=False)[:200]})", file=sys.stderr, flush=True)
        try:
            result = TOOL_MAP.get(name, lambda a: f"unknown tool: {name}")(args)
        except Exception as e:
            result = f"tool error: {e}"
        if verbose:
            result_preview = result[:300].replace("\n", " ")
            print(f"[tool_result] {result_preview}...", file=sys.stderr, flush=True)

        messages.append({
            "role": "user",
            "content": f"[Tool result for {name}]\n{result}\n\n继续思考。如果要调更多工具, 再次用 <tool_call> 格式。",
        })

    return f"(max iterations {MAX_ITER} reached, no final answer)"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="V 端 VCP 网关 chat bridge")
    parser.add_argument("query", nargs="*", help="用户查询 (空则进 REPL)")
    parser.add_argument("--model", "-m", help="指定单 model (默认 fallback 链)")
    parser.add_argument("--no-fallback", action="store_true", help="禁用 fallback")
    args = parser.parse_args()

    if args.model:
        model_or_chain = [args.model]
    elif args.no_fallback:
        model_or_chain = [DEFAULT_FALLBACK[0]]
    else:
        model_or_chain = DEFAULT_FALLBACK

    query_args = " ".join(args.query) if args.query else None
    if query_args:
        result = chat_loop(model_or_chain, query_args)
        print()
        print("=" * 60)
        print(result)
    else:
        chain_name = args.model if args.model else "fallback:" + "→".join(DEFAULT_FALLBACK)
        print(f"v-bridge-v2 启动, 链路: {chain_name}", file=sys.stderr)
        print("输入 'exit' 退出\n", file=sys.stderr)
        while True:
            try:
                q = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye", file=sys.stderr)
                break
            if not q or q.lower() in ("exit", "quit"):
                break
            print(chat_loop(model_or_chain, q))
            print()
