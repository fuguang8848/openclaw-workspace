#!/usr/bin/env python3
"""
r1-bridge.py — R1 70B (或任意 Ollama model) + tool use bridge (prompt injection 协议)

让 R1 70B 通过 Ollama API 调 V 的 tool set。
协议：prompt 注入（不用 Ollama 原生 tools，因为 Q4 量化后 model 丢 tool 能力）。

用法:
  ./r1-bridge.py deepseek-r1:70b-q4 "列出当前目录"
  ./r1-bridge.py qwen2.5-7b-q4 "今天 daily memory 几号"
  echo "退出"

工具集:
  exec   - shell 执行（30s timeout + capture）
  read   - 读文件
  write  - 写文件
  search - Bing 搜索（调 search-v.py）

设计:
  - System prompt 描述 tool 调用格式
  - Model 输出 <tool_call>name(arg=value)</tool_call>
  - V regex 解析 + 执行 + 把 result 喂回
  - max_iter 限制（防死循环）
"""
import sys
import os
import json
import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
TOOL_CALL_TIMEOUT = 30
MAX_ITER = 8  # R1 70B 推理链长

# ---------- Tool implementations ----------
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
                lines.append(f"   {item.get('snippet', '')[:200]}")
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

# ---------- Tool-call parsing ----------
TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(?P<name>\w+)\s*(?P<args>.*?)\s*</tool_call>",
    re.DOTALL,
)
ARG_RE = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"|(\w+)\s*=\s*(\S+)")

VALID_TOOLS = {"exec", "read", "write", "search"}

def infer_tool_from_args(args):
    """从 args dict 推断 tool name（用于 qwen 'name(args)' 格式）"""
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
    """从 model 输出中提取 1 个 tool call. Returns (name, args) or (None, None)
    支持 3 种格式:
      1. 标准: <tool_call>exec cmd="ls"</tool_call>  (Llama 训练模板)
      2. JSON args: <tool_call>exec({"cmd": "ls"})</tool_call>  (Qwen 部分输出)
      3. qwen 风格: <tool_call>name({"cmd": "ls"})</tool_call>  (Q4 量化后简化)
         → 自动从 args 推断 tool: cmd→exec, path+content→write, path→read, query→search
    """
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
    # qwen 'name(args)' 风格: 推断 tool
    if name not in VALID_TOOLS:
        inferred = infer_tool_from_args(args)
        if inferred:
            name = inferred
    return name, args

def strip_tool_call(content):
    """把 <tool_call>...</tool_call> 块从文本中移除（用于最终回答）"""
    return TOOL_CALL_RE.sub("", content).strip()

# ---------- Ollama chat ----------
SYSTEM_PROMPT = """你是 V，一个 AI 私人助理。当前使用本地 Ollama 模型。

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
drwxr-xr-x 3 user user 4096 Jun  3 20:00 .
drwxr-xr-x 5 user user 4096 Jun  3 20:00 ..
-rw-r--r-- 1 user user 100 Jun  3 20:00 README.md
Assistant: 当前目录有 1 个文件 README.md。

# 规则
1. **调用工具时**，用 `<tool_call><name> key="value"</tool_call>` 格式。**name 必须是 exec/read/write/search 之一**
2. 工具结果会原样回你。**总结后回答**，不要 echo
3. 工具 error → 换方法，**不要重复 retry**
4. **最终回答 ≤ 200 字**
5. **最终回答不要包含 <tool_call> 块**
6. 中文回答
"""

def ollama_chat(model, messages):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"ollama request failed: {e}"}
    except Exception as e:
        return {"error": str(e)}

def chat_loop(model, user_query, verbose=True):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for i in range(MAX_ITER):
        if verbose:
            print(f"\n[iter {i+1}/{MAX_ITER}] 调 {model}...", file=sys.stderr, flush=True)
        resp = ollama_chat(model, messages)
        if "error" in resp:
            return f"❌ {resp['error']}"

        msg = resp.get("message", {})
        content = msg.get("content", "")
        messages.append(msg)

        # 解析 tool call
        name, args = parse_tool_call(content)

        if not name:
            # 没 tool call → final answer
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

        # 工具结果以 user role 喂回（很多 model 不原生支持 tool role）
        messages.append({
            "role": "user",
            "content": f"[Tool result for {name}]\n{result}\n\n继续思考。如果要调更多工具，再次用 <tool_call> 格式。",
        })

    return f"(max iterations {MAX_ITER} reached, no final answer)"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: r1-bridge.py <model> [query]", file=sys.stderr)
        print("  model: deepseek-r1:70b-q4 | qwen2.5-7b-q4 | llama3.2:1b", file=sys.stderr)
        sys.exit(1)

    model = sys.argv[1]
    if len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        result = chat_loop(model, query)
        print()
        print("=" * 60)
        print(result)
    else:
        print(f"r1-bridge 启动, model={model}", file=sys.stderr)
        print("输入 'exit' 退出\n", file=sys.stderr)
        while True:
            try:
                q = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye", file=sys.stderr)
                break
            if not q or q.lower() in ("exit", "quit"):
                break
            print(chat_loop(model, q))
            print()
