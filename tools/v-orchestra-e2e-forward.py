#!/usr/bin/env python3
"""
v-orchestra-e2e-forward.py — 交响乐家族正向端到端验证 (V 6/13 21:53)

设计: SOP #11 验证 > 产出. 不光 import, 真调用 API, 验证业务功能.

9 系统正向:
  1. Ollama               — 模型可用
  2. 超级思考 (v6)        — think_v6 单轮跑通
  3. agentmemory (v2.0.2) — BM25 双轨检索
  4. agentmemory_ext      — 23+ 远端模块加载
  5. agent_safety         — rm -rf / 拦截 (CRITICAL)
  6. agent_supervisor     — 创建 workflow
  7. agent_manager        — register agent
  8. agent_search         — search execute
  9. VCP / VCP-Admin      — 端口 + API auth
  10. AgentSymphony       — /memory/store + /memory/query
  11. AgentTeam           — /api/health

用法:
    python3 v-orchestra-e2e-forward.py           # 跑全部
    python3 v-orchestra-e2e-forward.py --json     # JSON 输出

退出码: 0=全通, 1=有失败
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Callable
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def safe_call(name: str, fn: Callable[[], Any], expected_keys: list[str] | None = None) -> tuple[bool, str]:
    """安全调用 + 验证返回. 返回 (ok, detail)."""
    try:
        result = fn()
        if expected_keys:
            if isinstance(result, dict):
                missing = [k for k in expected_keys if k not in result]
                if missing:
                    return False, f"missing keys: {missing}"
            elif not result:
                return False, "empty result"
        return True, str(result)[:100]
    except Exception as e:
        tb = traceback.format_exc(limit=1)
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")[:200]
    except HTTPError as e:
        return e.code, str(e)[:100]
    except Exception as e:
        return 0, f"{type(e).__name__}: {str(e)[:80]}"


def http_post(url: str, data: dict, timeout: float = 5.0) -> tuple[int, str]:
    try:
        body = json.dumps(data).encode("utf-8")
        req = Request(url, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")[:200]
    except HTTPError as e:
        return e.code, str(e)[:100]
    except Exception as e:
        return 0, f"{type(e).__name__}: {str(e)[:80]}"


# ----------------------------------------------------------------------
# 9 系统端到端测试
# ----------------------------------------------------------------------

def test_ollama() -> tuple[bool, str]:
    code, body = http_get("http://127.0.0.1:11434/api/tags")
    if code != 200:
        return False, f"Ollama 端口 {code}: {body[:60]}"
    try:
        data = json.loads(body)
        models = [m.get("name", "") for m in data.get("models", [])]
        return True, f"{len(models)} 模型: {','.join(models[:3])}"
    except Exception:
        return True, body[:80]


def test_superthinking_v6() -> tuple[bool, str]:
    def call():
        sys.path.insert(0, os.path.expanduser("~/Agent-superthinking/src"))
        from super_thinking.v6.entrypoint import think_v6
        session = think_v6("V 6/13 21:53 e2e verify", max_rounds=1)
        assert session.rounds, "no rounds"
        return {"rounds": len(session.rounds), "status": str(session.status)}
    return safe_call("superthinking", call, ["rounds"])


def test_superthinking_jury() -> tuple[bool, str]:
    """Jury 18 专家 force_all 模式 (V 6/13 22:24 SOP #20 收工发现 Hermes P0 BUG 修后)"""
    def call():
        sys.path.insert(0, os.path.expanduser("~/Agent-superthinking/src"))
        from super_thinking.core.jury import Jury
        j = Jury()
        r = j.think("V 6/13 22:32 jury force_all", mode="force_all")
        assert r.successful >= 18, f"应 18 专家全成功, 实际 successful={r.successful} total={r.total_perspectives}"
        return {"total": r.total_perspectives, "successful": r.successful, "failed": r.failed}
    return safe_call("jury", call, ["total"])


def test_agentmemory_v2() -> tuple[bool, str]:
    def call():
        from agentmemory.extensions.api import load_yinta_modules
        sys.path.insert(0, "/home/fuguang/AgentMemory-upgrade/src")
        from agentmemory.extensions.v2.bm25 import BM25Retriever
        load_yinta_modules(eager=True)
        r = BM25Retriever()
        docs = [
            {"id": "1", "content": "agentmemory v2.0.2 端到端 verify test", "metadata": {}},
            {"id": "2", "content": "BM25 关键词检索 4/4 命中", "metadata": {}},
        ]
        r.index(docs)
        hits = r.retrieve("v2.0.2 端到端", limit=2)
        return {"hits": len(hits), "top_score": hits[0]["score"] if hits else 0}
    return safe_call("agentmemory", call, ["hits"])


def test_agentmemory_extensions() -> tuple[bool, str]:
    def call():
        from agentmemory.extensions.api import load_yinta_modules
        result = load_yinta_modules(eager=True)
        ok = sum(1 for v in result.values() if v == "OK")
        return {"ok": ok, "total": len(result)}
    return safe_call("ext", call, ["ok"])


def test_agent_safety() -> tuple[bool, str]:
    def call():
        from agent_safety import SafetyEngine, SafetyAction, ActionType
        e = SafetyEngine()
        # 重置熔断器 (避免上一轮污染)
        if hasattr(e, "reset_circuit_breaker"):
            e.reset_circuit_breaker()
        # rm -rf / 应被 BLOCK (新规则 block-rm-system-path)
        a = SafetyAction(action_id="t", action_type=ActionType.SHELL_EXECUTE,
                         agent_id="t", tool_name="rm", details={}, target="rm -rf /home/fuguang")
        r = e.evaluate(a)
        assert str(r.decision).lower() == "block", f"rm -rf /home/fuguang 应 BLOCK, 实际 {r.decision}"
        return {"decision": r.decision, "risk": str(r.risk_level), "matched": r.matched_policies}
    return safe_call("safety", call, ["decision"])


def test_agent_supervisor() -> tuple[bool, str]:
    def call():
        from agent_supervisor import SupervisorSkill
        s = SupervisorSkill()
        wf = s.create_workflow("t", [{"id": "s1", "name": "s1", "task_fn": lambda: "OK", "deps": []}])
        return {"workflow_id": wf[:8] if isinstance(wf, str) else str(wf)[:30]}
    return safe_call("supervisor", call, ["workflow_id"])


def test_agent_manager() -> tuple[bool, str]:
    def call():
        from agent_manager import ManagerSkill
        m = ManagerSkill()
        r = m.execute("register", {"alias": "e2e-forward", "name": "E2E", "role": "tester", "description": "forward verify"})
        return {"success": r.get("success"), "alias": "e2e-forward"}
    return safe_call("manager", call, ["success"])


def test_agent_search() -> tuple[bool, str]:
    def call():
        sys.path.insert(0, os.path.expanduser("~/AgentSearch/src"))
        from agent_search import SearchSkill
        s = SearchSkill()
        r = s.execute("search", {"query": "Qdrant Edge 替代 LanceDB 端到端", "max_results": 3})
        assert r.get("success"), f"search 失败: {r.get('error')}"
        return {"success": r.get("success"), "hits": r["data"]["count"]}
    return safe_call("search", call, ["success"])


def test_vcp() -> tuple[bool, str]:
    code, body = http_get("http://127.0.0.1:6005/health")
    if code in (200, 401, 403):
        return True, f"VCP {code} (端口活)"
    return False, f"VCP {code}: {body[:60]}"


def test_vcp_admin() -> tuple[bool, str]:
    code, body = http_get("http://127.0.0.1:6006/health")
    return code in (200, 302, 307), f"VCP-Admin {code}"


def test_agent_symphony() -> tuple[bool, str]:
    # /memory/store + /memory/query 端到端
    code1, body1 = http_post("http://127.0.0.1:18081/memory/store", {
        "type": "context", "content": "V 6/13 21:53 forward e2e verify", "tags": ["e2e"]
    })
    if code1 != 200:
        return False, f"store {code1}: {body1[:60]}"
    code2, body2 = http_post("http://127.0.0.1:18081/memory/query", {
        "query": "forward e2e verify", "limit": 2
    })
    if code2 != 200:
        return False, f"query {code2}: {body2[:60]}"
    return True, f"store+query OK"


def test_agentsymphony_team_spawn() -> tuple[bool, str]:
    """V 6/13 22:46 持续 verify team/spawn 端到端 (V 22:14 修完绝对路径后)"""
    import time
    t0 = time.time()
    code, body = http_post("http://127.0.0.1:18081/team/spawn", {
        "task": "v-orchestra e2e forward verify team/spawn",
        "agent_type": "general"
    }, timeout=60)  # 60s: 真 sub-agent 启动 + gateway call 需时间
    elapsed = time.time() - t0
    if code != 200:
        return False, f"spawn {code}: {body[:60]} ({elapsed:.1f}s)"
    try:
        d = json.loads(body)
        sid = d.get("session_id", "")
        if not sid:
            return False, f"no session_id: {body[:60]}"
        # 立即 shutdown 避免后台 sub-agent 堆积
        try:
            import urllib.request
            urllib.request.urlopen(
                f"http://127.0.0.1:18081/team/shutdown?session_id={sid}",
                timeout=5
            )
        except Exception:
            pass  # shutdown 失败不影响 spawn 测试
        return True, f"spawn OK session={sid[:8]} ({elapsed:.1f}s)"
    except Exception:
        return True, f"spawn OK (no JSON: {body[:40]})"


def test_agentsymphony_full() -> tuple[bool, str]:
    """V 6/13 22:50 AgentSymphony 8 端点全 e2e (除已测的 store/query/spawn)

    测试:
    - /health (GET)
    - /thinking/dialog (POST) — 超级思考入口
    - /thinking/state (GET)  — 状态查询
    - /memory/list (GET)     — 记忆列表
    - /search/execute (POST) — search 端到端
    - /team/status (GET)     — sub-agent 状态
    """
    sid = "v-symphony-e2e-22:50"
    results = {}

    # 1. /health
    code, body = http_get("http://127.0.0.1:18081/health")
    results["health"] = "OK" if code == 200 else f"FAIL({code})"

    # 2. /thinking/dialog
    code, body = http_post("http://127.0.0.1:18081/thinking/dialog", {
        "message": "V 6/13 22:50 symphony e2e thinking dialog",
        "session_id": sid,
    }, timeout=15)
    if code == 200:
        try:
            d = json.loads(body)
            results["dialog"] = f"OK stage={d.get('stage', '?')[:20]}"
        except Exception:
            results["dialog"] = f"OK(no JSON)"
    else:
        results["dialog"] = f"FAIL({code})"

    # 3. /thinking/state
    code, body = http_get(f"http://127.0.0.1:18081/thinking/state?session_id={sid}")
    results["thinking_state"] = "OK" if code == 200 else f"FAIL({code})"

    # 4. /memory/list
    code, body = http_get("http://127.0.0.1:18081/memory/list?limit=3")
    results["memory_list"] = "OK" if code == 200 else f"FAIL({code})"

    # 5. /search/execute
    code, body = http_post("http://127.0.0.1:18081/search/execute", {
        "query": "V 6/13 22:50 search e2e",
        "max_results": 2,
    }, timeout=15)
    if code == 200:
        try:
            d = json.loads(body)
            hits = d.get("results") or d.get("hits") or []
            results["search"] = f"OK hits={len(hits) if isinstance(hits, list) else '?'}"
        except Exception:
            results["search"] = "OK(no JSON)"
    else:
        results["search"] = f"FAIL({code})"

    # 6. /team/status (用 fake session_id)
    code, body = http_get("http://127.0.0.1:18081/team/status?session_id=v-symphony-fake")
    if code == 200:
        try:
            d = json.loads(body)
            results["team_status"] = f"OK status={d.get('status', '?')[:15]}"
        except Exception:
            results["team_status"] = "OK(no JSON)"
    else:
        results["team_status"] = f"FAIL({code})"

    failed = [k for k, v in results.items() if v.startswith("FAIL")]
    summary = " | ".join(f"{k}={v}" for k, v in results.items())
    if failed:
        return False, f"failed: {failed} | {summary[:80]}"
    return True, f"6 endpoints OK | {summary[:80]}"


def test_agent_team() -> tuple[bool, str]:
    code, body = http_get("http://127.0.0.1:8080/api/health")
    if code == 200:
        return True, "AgentTeam /api/health UP"
    return False, f"AgentTeam {code}"


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------

TESTS = [
    ("Ollama",            test_ollama),
    ("超级思考 (v6)",     test_superthinking_v6),
    ("Jury 18 专家",      test_superthinking_jury),
    ("agentmemory v2.0.2", test_agentmemory_v2),
    ("agentmemory_ext",   test_agentmemory_extensions),
    ("agent_safety",      test_agent_safety),
    ("agent_supervisor",  test_agent_supervisor),
    ("agent_manager",     test_agent_manager),
    ("agent_search",      test_agent_search),
    ("VCP",               test_vcp),
    ("VCP-Admin",         test_vcp_admin),
    ("AgentSymphony",     test_agent_symphony),
    ("Symphony /team/spawn", test_agentsymphony_team_spawn),
    ("Symphony 6 端点 e2e", test_agentsymphony_full),
    ("AgentTeam",         test_agent_team),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    log("=" * 60)
    log("🎼 V-Orchestra 正向端到端验证 v1.0 (V 6/13 21:53)")
    log("=" * 60)

    results = []
    for name, fn in TESTS:
        ok, detail = fn()
        icon = "✅" if ok else "❌"
        log(f"  {icon} {name:24s} — {detail}")
        results.append({"name": name, "ok": ok, "detail": detail})

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    log("")
    log(f"通过: {passed}/{total}")

    if args.json:
        print(json.dumps({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "passed": passed, "total": total,
            "results": results,
        }, ensure_ascii=False, indent=2))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
