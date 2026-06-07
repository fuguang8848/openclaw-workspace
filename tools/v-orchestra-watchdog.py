#!/usr/bin/env python3
"""
v-orchestra-watchdog.py — 交响乐技能家族持续监控 v2.1 (配置外置)

设计原则:
- 配置外置 (v-orchestra-watchdog.yaml) — 加端口/模块无需改代码
- 易修改: 改 yaml 一行就能加监控
- 可移植: 路径用 ${HOME} 占位, 别的机器改 yaml 即可
- 便于他人开发: 每个检查都标注 purpose, 失败 log 含 traceback
- 兼容原 v1 调用方式 (无参数跑 = 一次性检查; --daemon = 持续守护)

用法:
    python3 v-orchestra-watchdog.py             # 一次性健康检查
    python3 v-orchestra-watchdog.py --daemon    # 持续守护 (60s 间隔)
    python3 v-orchestra-watchdog.py --json      # 输出 JSON 报告 (给别的工具用)
    python3 v-orchestra-watchdog.py --lesson "问题描述"  # 手动写经验

环境变量:
    HOME   用于 ${HOME} 占位展开
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 默认配置路径 (与本脚本同目录)
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = _THIS_DIR / "v-orchestra-watchdog.yaml"

# ----------------------------------------------------------------------
# 配置加载
# ----------------------------------------------------------------------

def expand_env(text: str) -> str:
    """把 ${HOME} / ${USER} 这类占位展开为 os.environ 值"""
    if not isinstance(text, str):
        return text
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), text)


def expand_env_recursive(obj):
    """递归展开 dict/list/str 里的 ${ENV} 占位"""
    if isinstance(obj, dict):
        return {k: expand_env_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_recursive(v) for v in obj]
    if isinstance(obj, str):
        return expand_env(obj)
    return obj


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    """加载 YAML 配置. 不存在时返回最小默认配置 (兼容旧调用)."""
    if not path.exists():
        return _fallback_config()
    try:
        import yaml
    except ImportError:
        # 没 PyYAML — 用极简解析 (只支持 key: value 单层)
        return _parse_simple_yaml(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return _fallback_config()
        return expand_env_recursive(data)
    except Exception as e:
        print(f"[watchdog] 配置加载失败 {path}: {e}, 用 fallback", file=sys.stderr)
        return _fallback_config()


def _fallback_config() -> dict:
    """无 yaml 文件 / yaml 解析失败时的最小配置 (兼容老调用)"""
    home = os.environ.get("HOME", "/home/fuguang")
    return {
        "meta": {"version": "1.0", "description": "fallback config"},
        "paths": {
            "python_executable": sys.executable,
            "log_file": "/tmp/v-orchestra-watchdog.log",
            "lessons_file": f"{home}/桌面/v-orchestra-watchdog-经验记录.md",
            "agentmemory_src": f"{home}/AgentMemory-upgrade/src",
        },
        "services": [
            ("Ollama", "127.0.0.1", 11434, "curl -s http://127.0.0.1:11434/api/tags", []),
            ("VCP", "127.0.0.1", 6005, "curl -s http://127.0.0.1:6005/health", ["Unauthorized"]),
            ("VCP-Admin", "127.0.0.1", 6006, "curl -s http://127.0.0.1:6006/health", ["Redirecting", "Found"]),
            ("AgentTeam", "127.0.0.1", 8080, "curl -s http://127.0.0.1:8080/", ["<!DOCTYPE"]),
            ("AgentSymphony", "127.0.0.1", 18081, "curl -s http://127.0.0.1:18081/health", []),
        ],
        "python_modules": [],  # 留空, 由 test_python_modules 旧版逻辑填充
        "processes": [("OpenClaw", "openclaw")],
    }


def _parse_simple_yaml(path: Path) -> dict:
    """极简 YAML 解析 (仅顶层 key: value)"""
    cfg: dict = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                v = v.strip().strip('"').strip("'")
                cfg[k.strip()] = expand_env(v)
    return cfg


# ----------------------------------------------------------------------
# 监控函数
# ----------------------------------------------------------------------

def log(msg: str, log_file: str | None = None) -> None:
    """统一日志格式"""
    ts = datetime.now().strftime("%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """端口连通性检查"""
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def check_service(name: str, host: str, port: int, cmd: str, accept_warnings: list[str], timeout: float = 5.0) -> tuple[str, str]:
    """返回 (status, detail) - status ∈ {UP, WARN, DOWN}"""
    port_ok = check_port(host, port)
    if not port_ok:
        return "DOWN", f"端口 {port} 无响应"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout, text=True)
        out = (r.stdout or "").strip()
        if not out:
            return "WARN", "端口通但响应空"
        for pattern in accept_warnings or []:
            if pattern in out:
                return "WARN", f"端口通 + 匹配 WARN pattern: {pattern}"
        if out.startswith(("{", "<")):
            return "UP", out[:80]
        return "WARN", f"响应异常: {out[:60]}"
    except subprocess.TimeoutExpired:
        return "DOWN", f"健康检查命令超时 ({timeout}s)"
    except Exception as e:
        return "DOWN", f"命令执行失败: {type(e).__name__}: {e}"


def check_python_module(name: str, test_code: str | None, agentmemory_src: str) -> tuple[str, str]:
    """运行 Python 测试代码, 捕获异常. 返回 (status, detail)."""
    # 加 agentmemory src 到 sys.path 让 import 能找到
    if agentmemory_src and agentmemory_src not in sys.path:
        sys.path.insert(0, agentmemory_src)
    # 兼容老 watchdog 的 test_python_modules (无 test_code 时)
    if test_code is None:
        return _legacy_test_python_module(name, agentmemory_src)
    try:
        exec(test_code, {"__name__": f"_watchdog_{name}"})
        return "UP", "测试通过"
    except AssertionError as e:
        return "DOWN", f"断言失败: {str(e)[:80]}"
    except Exception as e:
        tb = traceback.format_exc(limit=2)
        return "DOWN", f"{type(e).__name__}: {str(e)[:60]}"


def _legacy_test_python_module(name: str, agentmemory_src: str) -> tuple[str, str]:
    """兼容原 watchdog 的硬编码测试 (当 yaml 配置无 test_code 时)"""
    if agentmemory_src and agentmemory_src not in sys.path:
        sys.path.insert(0, agentmemory_src)
    try:
        if name == "超级思考":
            from super_thinking.core.jury import Jury
            j = Jury()
            r = j.think("测试")
            return ("UP" if r.successful >= 1 else "DOWN", f"{r.successful}/18 专家")
        if name == "agentmemory":
            import agentmemory
            from agentmemory import Memory
            return ("UP", f"{sum(1 for x in dir(agentmemory) if not x.startswith('_'))} 个导出类")
        if name == "agent_safety":
            from agent_safety import SafetyEngine, SafetyAction, ActionType
            e = SafetyEngine()
            a = SafetyAction(action_id="t", action_type=ActionType.SHELL_EXECUTE,
                             agent_id="t", tool_name="rm", details={}, target="/")
            r = e.evaluate(a)
            return ("UP", f"拦截:{r.decision.value}")
        if name == "agent_supervisor":
            from agent_supervisor import SupervisorSkill
            s = SupervisorSkill()
            wf = s.create_workflow("t", [{"id":"s1","name":"s1","task_fn":lambda:"OK","deps":[]}])
            return ("UP", f"wf:{wf[:8]}")
        if name == "agent_manager":
            from agent_manager import ManagerSkill
            m = ManagerSkill()
            r = m.execute("register", {"alias":"watchdog","name":"W","role":"monitor","description":"x"})
            return ("UP", f"注册:{r.get('success')}")
        if name == "agent_search":
            from agent_search import SearchSkill
            return ("UP", "SearchSkill 正常")
        return "DOWN", "未知模块"
    except Exception as e:
        return "DOWN", f"{type(e).__name__}: {str(e)[:60]}"


def check_process(name: str, pgrep_pattern: str) -> tuple[str, str]:
    """pgrep 检查进程"""
    try:
        r = subprocess.run(["pgrep", "-f", pgrep_pattern], capture_output=True, timeout=3, text=True)
        if r.returncode == 0 and r.stdout.strip():
            pids = r.stdout.strip().split()
            return "UP", f"pids: {','.join(pids)}"
        return "DOWN", "pgrep 未匹配"
    except Exception as e:
        return "DOWN", str(e)


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------

def _norm_services(services: list) -> list[tuple]:
    """把 yaml 列表标准化为 (name, host, port, cmd, accept_warnings) tuples"""
    out = []
    for s in services:
        if isinstance(s, dict):
            out.append((
                s["name"], s["host"], s["port"],
                s["health_cmd"], s.get("accept_warnings", []) or [],
            ))
        elif isinstance(s, (list, tuple)):
            # 兼容 [name, host, port, cmd] 或 [name, host, port, cmd, [warns]]
            if len(s) == 4:
                out.append((s[0], s[1], s[2], s[3], []))
            elif len(s) >= 5:
                out.append(tuple(s[:5]))
            else:
                out.append(tuple(s) + (None,) * (5 - len(s)))
    return out


def _norm_processes(processes: list) -> list[tuple]:
    out = []
    for p in processes:
        if isinstance(p, dict):
            out.append((p["name"], p["pgrep_pattern"]))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            out.append(tuple(p[:2]))
    return out


def run_once(config: dict) -> dict:
    """跑一次完整健康检查. 返回报告 dict."""
    paths = config.get("paths", {})
    log_file = paths.get("log_file")
    agentmemory_src = paths.get("agentmemory_src", "")

    issues: list[str] = []
    services = _norm_services(config.get("services", []))
    py_modules = config.get("python_modules", [])
    processes = _norm_processes(config.get("processes", []))

    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "config_version": config.get("meta", {}).get("version", "?"),
        "services": [],
        "python_modules": [],
        "processes": [],
        "all_ok": True,
        "issues": [],
    }

    log("=" * 60, log_file)
    log(f"🎼 V-Orchestra Watchdog v{report['config_version']} 启动", log_file)
    log("=" * 60, log_file)

    # 1. 端口/服务
    log("\n=== 端口/服务检查 ===", log_file)
    for name, host, port, cmd, warns in services:
        status, detail = check_service(name, host, port, cmd, warns)
        icon = {"UP": "✅", "WARN": "⚠️", "DOWN": "❌"}.get(status, "?")
        log(f"  {icon} {name} ({port}): {status} — {detail}", log_file)
        report["services"].append({"name": name, "port": port, "status": status, "detail": detail})
        if status == "DOWN":
            issues.append(f"{name} DOWN: {detail}")
            report["all_ok"] = False

    # 2. Python 模块
    log("\n=== Python 模块健康检查 ===", log_file)
    for m in py_modules:
        if isinstance(m, dict):
            name = m["name"]
            test = m.get("test")
        else:
            name = m
            test = None
        status, detail = check_python_module(name, test, agentmemory_src)
        icon = "✅" if status == "UP" else "❌"
        log(f"  {icon} {name}: {status} — {detail}", log_file)
        report["python_modules"].append({"name": name, "status": status, "detail": detail})
        if status == "DOWN":
            issues.append(f"{name} DOWN: {detail}")
            report["all_ok"] = False

    # 3. 进程
    log("\n=== 关键进程检查 ===", log_file)
    for name, pattern in processes:
        status, detail = check_process(name, pattern)
        icon = "✅" if status == "UP" else "❌"
        log(f"  {icon} {name}: {status} — {detail}", log_file)
        report["processes"].append({"name": name, "status": status, "detail": detail})
        if status == "DOWN":
            issues.append(f"{name} DOWN: {detail}")
            report["all_ok"] = False

    # 4. 汇总
    log("\n=== 汇总 ===", log_file)
    if report["all_ok"]:
        log("  🎉 所有服务正常", log_file)
    else:
        log(f"  ❌ 发现 {len(issues)} 个问题:", log_file)
        for i in issues:
            log(f"     - {i}", log_file)
    log("", log_file)
    report["issues"] = issues
    return report


def write_lesson(config: dict, issue: str) -> None:
    """手动写一条经验"""
    paths = config.get("paths", {})
    lessons_file = paths.get("lessons_file", "/tmp/v-orchestra-lessons.md")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{ts}] {issue}\n\n**记录**: 手动\n**标签**: 手工记录\n\n---\n"
    Path(lessons_file).parent.mkdir(parents=True, exist_ok=True)
    if not Path(lessons_file).exists():
        Path(lessons_file).write_text("# V-Orchestra Watchdog 经验记录\n\n", encoding="utf-8")
    with open(lessons_file, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"✅ 经验已写入: {lessons_file}")


def daemon_loop(config: dict, interval: int = 60) -> None:
    """持续守护模式"""
    log_file = config.get("paths", {}).get("log_file")
    log(f"🐕 Daemon 模式启动, 间隔 {interval}s (Ctrl+C 停止)", log_file)
    try:
        while True:
            run_once(config)
            time.sleep(interval)
    except KeyboardInterrupt:
        log("🛑 Daemon 停止", log_file)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="V-Orchestra Watchdog — 端口/服务/Python 模块/进程 健康检查",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help=f"配置文件路径 (默认: {DEFAULT_CONFIG})")
    parser.add_argument("--daemon", action="store_true", help="持续守护模式 (60s 间隔)")
    parser.add_argument("--interval", type=int, default=60, help="daemon 间隔秒数")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    parser.add_argument("--lesson", type=str, default=None, help="手动写一条经验到 lessons_file")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.lesson:
        write_lesson(config, args.lesson)
        return 0

    if args.daemon:
        daemon_loop(config, args.interval)
        return 0

    report = run_once(config)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
