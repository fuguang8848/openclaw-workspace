#!/usr/bin/env python3
"""
v-snapshot.py — V's session-state snapshot tool

捕获当前 V 的工作环境状态（服务、cwd、git、active context）写到盘上，
用于 gateway restart 后 session 失忆时恢复上下文。

用法:
  v-snapshot.py collect     # 收集当前状态到 stdout (JSON)
  v-snapshot.py save        # 收集 + atomic write 到 ~/.openclaw/workspace/.v-snapshot/
  v-snapshot.py status      # 读 latest.json 并人类可读打印
  v-snapshot.py load        # 读 latest.json 返 raw JSON
  v-snapshot.py history     # 列历史快照文件
  v-snapshot.py clean       # 只保留最近 7 天快照
  v-snapshot.py watch       # SOP #37: 5 仓 HEAD 变化检测 (exit 1=活动, 0=无)
  v-snapshot.py activity    # 读 git-activity.jsonl (--since ISO --limit N)
  v-snapshot.py git-state   # 5 仓当前 HEAD/branch/ahead 快照
"""
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/home/fuguang/.openclaw/workspace")
SNAPSHOT_DIR = WORKSPACE / ".v-snapshot"
LATEST = SNAPSHOT_DIR / "latest.json"
GIT_STATE = SNAPSHOT_DIR / "git-state.json"
GIT_ACTIVITY = SNAPSHOT_DIR / "git-activity.jsonl"
SCHEMA_VERSION = "1.0.0"
CST = timezone(timedelta(hours=8))

# 监控的服务：(name, port, expected_process_hint)
SERVICES = [
    ("vcp_6005", 6005, "VCPToolBox 主服务"),
    ("vcp_admin_6006", 6006, "adminServer"),
    ("symphony_18081", 18081, "agent-symphony"),
    ("agentteam_8080", 8080, "agentteam board"),
    ("ollama_11434", 11434, "ollama"),
]

# SOP #37 — 5 仓 git activity 监控
# 注意: VCPToolBox 不是 git 仓 (workspace 6/18 验证), 排除
GIT_REPOS = [
    ("Agent-superthinking", "/home/fuguang/Agent-superthinking"),
    ("AgentSearch", "/home/fuguang/AgentSearch"),
    ("AgentTeam", "/home/fuguang/AgentTeam"),
    ("AgentSafety", "/home/fuguang/AgentSafety"),
    ("AgentMemory-upgrade", "/home/fuguang/AgentMemory-upgrade"),
]


def now_iso():
    return datetime.now(CST).isoformat(timespec="seconds")


def tcp_check(port, timeout=0.5):
    """Quick TCP port check. Returns 'up' | 'down' | 'timeout'."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return "up"
    except socket.timeout:
        return "timeout"
    except (ConnectionRefusedError, OSError):
        return "down"


def curl_status(port, timeout=1.0):
    """curl 端口返 HTTP 状态码 (无 body)."""
    try:
        r = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", str(timeout), f"http://127.0.0.1:{port}/"],
            capture_output=True, text=True, timeout=timeout + 0.5,
        )
        return r.stdout.strip() or "ERR"
    except Exception as e:
        return f"ERR:{e.__class__.__name__}"


def pid_for_port(port):
    """通过 ss 找监听 127.0.0.1:port 的进程 PID."""
    try:
        r = subprocess.run(
            ["ss", "-tlnp", f"sport = :{port}"],
            capture_output=True, text=True, timeout=1.0,
        )
        for line in r.stdout.splitlines():
            if f":{port} " in line and "users:" in line:
                # pid=XXXX,fd=...
                m = line.split("pid=")
                if len(m) > 1:
                    pid = m[1].split(",")[0].split(")")[0].strip()
                    if pid.isdigit():
                        return int(pid)
    except Exception:
        pass
    return None


def cmd_output(cmd, timeout=2.0, cwd=None):
    """Run a command, return (rc, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def collect_services():
    out = []
    for name, port, hint in SERVICES:
        tcp = tcp_check(port)
        http = curl_status(port) if tcp == "up" else None
        pid = pid_for_port(port)
        # uptime from /proc/PID/stat
        uptime = None
        if pid:
            try:
                stat = Path(f"/proc/{pid}/stat").read_text()
                # field 22 = starttime in clock ticks
                parts = stat.split()
                if len(parts) >= 22:
                    start_ticks = int(parts[21])
                    clk_tck = os.sysconf("SC_CLK_TCK")
                    btime_rc, btime_out, _ = cmd_output(["awk", "/btime/{print $2}", "/proc/stat"])
                    if btime_rc == 0 and btime_out:
                        boot_time = int(btime_out)
                        proc_start = boot_time + start_ticks / clk_tck
                        uptime = int(time.time() - proc_start)
            except Exception:
                pass
        out.append({
            "name": name,
            "port": port,
            "hint": hint,
            "tcp": tcp,
            "http": http,
            "pid": pid,
            "uptime_s": uptime,
            "status": "up" if tcp == "up" and (http is None or http.startswith("2") or http.startswith("3") or http.startswith("4")) else "degraded" if tcp == "up" else "down",
        })
    return out


def collect_workspace():
    cwd = WORKSPACE
    out = {"cwd": str(cwd), "git": None, "memory_files": [], "uncommitted": []}

    # git status
    rc, stdout, _ = cmd_output(["git", "status", "--porcelain"], cwd=cwd)
    if rc == 0:
        dirty = []
        untracked = []
        for line in stdout.splitlines():
            if not line:
                continue
            status = line[:2]
            path = line[3:].strip().strip('"')
            if status.startswith("??"):
                untracked.append(path)
            else:
                dirty.append(f"{status} {path}")
        # ahead/behind
        rc2, out_ab, _ = cmd_output(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=cwd,
        )
        ahead, behind = None, None
        if rc2 == 0 and out_ab:
            parts = out_ab.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
        # last commit
        rc3, last_sha, _ = cmd_output(["git", "rev-parse", "--short", "HEAD"], cwd=cwd)
        rc4, last_msg, _ = cmd_output(
            ["git", "log", "-1", "--pretty=%s"], cwd=cwd,
        )
        out["git"] = {
            "dirty": dirty,
            "untracked": untracked,
            "ahead": ahead,
            "behind": behind,
            "last_sha": last_sha if rc3 == 0 else None,
            "last_msg": last_msg if rc4 == 0 else None,
        }

    # memory files
    mem_dir = cwd / "memory"
    if mem_dir.is_dir():
        files = sorted(mem_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        out["memory_files"] = [
            {
                "path": str(f.relative_to(cwd)),
                "size": f.stat().st_size,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime, CST).isoformat(timespec="seconds"),
            }
            for f in files[:5]
        ]
    return out


def collect_v_state():
    """当前 V session 自己的状态."""
    sessions_dir = Path("/home/fuguang/.openclaw/agents/main/sessions")
    out = {"active_session": None, "session_count_today": 0}
    if not sessions_dir.is_dir():
        return out
    now_ts = time.time()
    today_count = 0
    newest = None
    newest_mtime = 0
    for f in sessions_dir.glob("*.jsonl"):
        if f.name.endswith(".lock"):
            continue
        mtime = f.stat().st_mtime
        size = f.stat().st_size
        if mtime > newest_mtime:
            newest_mtime = mtime
            newest = f
        # count sessions started today (rough: mtime in last 24h)
        if now_ts - mtime < 86400:
            today_count += 1
    if newest:
        out["active_session"] = {
            "path": str(newest),
            "name": newest.name,
            "size": newest.stat().st_size,
            "mtime": datetime.fromtimestamp(newest.stat().st_mtime, CST).isoformat(timespec="seconds"),
        }
    out["session_count_today"] = today_count
    return out


def collect_active_context():
    """从最近的 memory 文件中提 '下一步' / 'in-progress' / '决策' 等 hints."""
    mem_dir = WORKSPACE / "memory"
    if not mem_dir.is_dir():
        return {"hints": [], "last_decisions": [], "next_actions": []}
    # 找今天 / 最近的 memory 文件
    today = datetime.now(CST).strftime("%Y-%m-%d")
    candidates = [mem_dir / f"{today}.md"]
    # 最近 3 个 md
    for f in sorted(mem_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
        if f not in candidates:
            candidates.append(f)
    hints, decisions, nexts = [], [], []
    for f in candidates:
        if not f.is_file():
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        in_section = None
        for line in content.splitlines():
            ls = line.strip()
            low = ls.lower()
            if low.startswith("## ") or low.startswith("# "):
                title = ls[2:].strip() if low.startswith("## ") else ls[1:].strip()
                in_section = title
                continue
            if not ls:
                continue
            # heuristic: 决策 / 待 / next / 继续
            if any(k in low for k in ["决定", "决策", "decision", "拍板", "确认"]):
                if len(decisions) < 10:
                    decisions.append({"file": f.name, "section": in_section, "text": ls[:200]})
            if any(k in low for k in ["下一步", "next", "继续", "待办", "todo", "p0", "p1"]):
                if len(nexts) < 10:
                    nexts.append({"file": f.name, "section": in_section, "text": ls[:200]})
    return {"last_decisions": decisions[:5], "next_actions": nexts[:5], "hints": hints}


def collect_all(trigger="manual"):
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "saved_at": now_iso(),
        "saved_ts": time.time(),
        "saved_by": "v-snapshot",
        "trigger": trigger,
        "hostname": socket.gethostname(),
        "v_state": collect_v_state(),
        "services": collect_services(),
        "workspace": collect_workspace(),
        "active_context": collect_active_context(),
    }
    return snapshot


def save_snapshot(trigger="manual"):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = collect_all(trigger=trigger)
    # atomic write: write to .tmp then rename
    ms = int(time.time() * 1000)
    tmp = SNAPSHOT_DIR / f".tmp.{os.getpid()}.{ms}"
    tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    tmp.replace(LATEST)
    # timestamped copy for history (ms 后缀防同秒覆盖 — 多 watchdog 并行时)
    ts = datetime.now(CST).strftime("%Y-%m-%d-%H%M%S")
    hist = SNAPSHOT_DIR / f"{ts}-{ms % 1000:03d}.json"
    hist.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    return snap, hist


def load_latest():
    if not LATEST.is_file():
        return None
    try:
        return json.loads(LATEST.read_text())
    except Exception as e:
        return {"error": str(e)}


def list_history():
    if not SNAPSHOT_DIR.is_dir():
        return []
    return sorted(
        [p for p in SNAPSHOT_DIR.glob("*.json") if p.name != "latest.json"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def clean_old(days=7):
    cutoff = time.time() - days * 86400
    removed = 0
    for f in list_history():
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed


# === SOP #37 — git activity 监控 ===

def collect_git_activity_state():
    """读 5 仓当前 HEAD SHA + branch + ahead/behind + commit msg."""
    state = {}
    for name, path in GIT_REPOS:
        p = Path(path)
        if not (p / ".git").exists():
            state[name] = {"exists": False, "path": path}
            continue
        rc, sha, _ = cmd_output(["git", "rev-parse", "HEAD"], cwd=path, timeout=1.0)
        rc2, branch, _ = cmd_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, timeout=1.0)
        rc3, msg, _ = cmd_output(["git", "log", "-1", "--pretty=%s"], cwd=path, timeout=1.0)
        rc4, ab, _ = cmd_output(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...HEAD@{{u}}"],
            cwd=path, timeout=1.0,
        )
        ahead, behind = None, None
        if rc4 == 0 and ab:
            parts = ab.split()
            if len(parts) == 2:
                try:
                    ahead, behind = int(parts[0]), int(parts[1])
                except ValueError:
                    pass
        state[name] = {
            "exists": True,
            "path": path,
            "sha": sha if rc == 0 else None,
            "branch": branch if rc2 == 0 else None,
            "msg": msg if rc3 == 0 else None,
            "ahead": ahead,
            "behind": behind,
            "checked_at": now_iso(),
        }
    return state


def load_git_state():
    if not GIT_STATE.is_file():
        return {}
    try:
        return json.loads(GIT_STATE.read_text())
    except Exception:
        return {}


def save_git_state(state):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    # atomic write
    ms = int(time.time() * 1000)
    tmp = SNAPSHOT_DIR / f".tmp.gitstate.{os.getpid()}.{ms}"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(GIT_STATE)


def append_activity(entries):
    """append 一批 activity entry 到 .jsonl."""
    if not entries:
        return
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with GIT_ACTIVITY.open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def watch_git_activity():
    """检测 5 仓 HEAD 变化, 返回 (activity_count, current_state, new_entries).

    逻辑:
    1. 读 5 仓当前状态
    2. 跟 git-state.json 对比
    3. 变化了的仓 写 git-activity.jsonl
    4. 更新 git-state.json
    """
    current = collect_git_activity_state()
    previous = load_git_state()
    new_entries = []
    for name, info in current.items():
        prev = previous.get(name, {})
        prev_sha = prev.get("sha")
        curr_sha = info.get("sha")
        if prev_sha and curr_sha and prev_sha != curr_sha:
            entry = {
                "ts": now_iso(),
                "repo": name,
                "path": info.get("path"),
                "branch": info.get("branch"),
                "old_sha": prev_sha[:8] if prev_sha else None,
                "new_sha": curr_sha[:8] if curr_sha else None,
                "msg": (info.get("msg") or "")[:120],
                "ahead": info.get("ahead"),
                "behind": info.get("behind"),
            }
            new_entries.append(entry)
    append_activity(new_entries)
    save_git_state(current)
    return len(new_entries), current, new_entries


def read_activity(since_ts=None, limit=50):
    """读 git-activity.jsonl. since_ts 是 ISO 字符串 或 epoch 秒."""
    if not GIT_ACTIVITY.is_file():
        return []
    if since_ts is not None:
        try:
            if isinstance(since_ts, str):
                cutoff = datetime.fromisoformat(since_ts).timestamp()
            else:
                cutoff = float(since_ts)
        except Exception:
            cutoff = 0
    else:
        cutoff = 0
    out = []
    with GIT_ACTIVITY.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            try:
                e_ts = datetime.fromisoformat(e.get("ts", "1970-01-01T00:00:00")).timestamp()
            except Exception:
                e_ts = 0
            if e_ts >= cutoff:
                out.append(e)
    return out[-limit:]


def fmt_activity(entries):
    if not entries:
        return "📭 no git activity recorded"
    lines = [f"📬 git activity: {len(entries)} entries"]
    for e in entries:
        lines.append(
            f"  • {e.get('ts', '?')[:19]} {e.get('repo', '?')}: "
            f"{e.get('old_sha', '?')} → {e.get('new_sha', '?')} "
            f"({(e.get('msg') or '')[:60]})"
            f" ahead={e.get('ahead')} behind={e.get('behind')}"
        )
    return "\n".join(lines)


def fmt_status(snap):
    if snap is None:
        return "❌ no snapshot yet"
    if "error" in snap:
        return f"❌ snapshot load error: {snap['error']}"
    lines = []
    lines.append(f"📸 snapshot @ {snap.get('saved_at', '?')} ({snap.get('trigger', '?')})")
    lines.append(f"   schema={snap.get('schema_version', '?')} host={snap.get('hostname', '?')}")
    lines.append("")
    # services
    lines.append("🔌 Services:")
    for s in snap.get("services", []):
        icon = {"up": "✅", "degraded": "⚠️ ", "down": "❌"}.get(s["status"], "❓")
        pid = f" PID={s['pid']}" if s.get("pid") else ""
        up = f" up={s['uptime_s']}s" if s.get("uptime_s") else ""
        http = f" http={s['http']}" if s.get("http") else ""
        lines.append(f"   {icon} {s['name']:<18} :{s['port']:<6}{pid}{up}{http}")
    lines.append("")
    # workspace
    ws = snap.get("workspace", {})
    git = ws.get("git") or {}
    lines.append(f"📂 workspace: {ws.get('cwd', '?')}")
    if git:
        dirty_n = len(git.get("dirty") or [])
        untracked_n = len(git.get("untracked") or [])
        ab = f" ahead={git.get('ahead')} behind={git.get('behind')}" if git.get("ahead") is not None else ""
        sha = git.get("last_sha") or "?"
        msg = (git.get("last_msg") or "")[:50]
        lines.append(f"   git: {sha} {msg!r}{ab} dirty={dirty_n} untracked={untracked_n}")
    lines.append("")
    # v_state
    vs = snap.get("v_state", {})
    sess = vs.get("active_session") or {}
    if sess:
        lines.append(f"🧠 active session: {sess.get('name')} ({sess.get('size')} bytes, {sess.get('mtime')})")
        lines.append(f"   sessions today: {vs.get('session_count_today', 0)}")
    # active context
    ctx = snap.get("active_context", {})
    if ctx.get("last_decisions"):
        lines.append("📋 last decisions:")
        for d in ctx["last_decisions"][:3]:
            lines.append(f"   • [{d.get('file', '?')}] {d.get('text', '')[:120]}")
    if ctx.get("next_actions"):
        lines.append("🎯 next actions:")
        for n in ctx["next_actions"][:3]:
            lines.append(f"   • [{n.get('file', '?')}] {n.get('text', '')[:120]}")
    # memory files
    mems = ws.get("memory_files", [])
    if mems:
        lines.append("📝 recent memory:")
        for m in mems[:3]:
            lines.append(f"   • {m['path']} ({m['size']} bytes)")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        cmd = "status"
    else:
        cmd = sys.argv[1]
    if cmd == "collect":
        snap = collect_all(trigger=os.environ.get("V_TRIGGER", "manual"))
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    elif cmd == "save":
        snap, hist = save_snapshot(trigger=os.environ.get("V_TRIGGER", "manual"))
        print(f"✅ saved {hist.name} ({hist.stat().st_size} bytes)")
    elif cmd == "status":
        snap = load_latest()
        print(fmt_status(snap))
    elif cmd == "load":
        snap = load_latest()
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    elif cmd == "history":
        files = list_history()
        print(f"{len(files)} historical snapshots:")
        for f in files[:20]:
            print(f"  {f.name} ({f.stat().st_size} bytes, mtime={datetime.fromtimestamp(f.stat().st_mtime, CST).isoformat(timespec='seconds')})")
    elif cmd == "clean":
        n = clean_old()
        print(f"✅ removed {n} old snapshots")
    elif cmd == "path":
        print(SNAPSHOT_DIR)
        print(LATEST)
    elif cmd == "watch":
        # SOP #37: 5 仓 HEAD 变化检测
        n, current, new_entries = watch_git_activity()
        if n > 0:
            for e in new_entries:
                print(
                    f"🚨 {e['ts'][:19]} {e['repo']}: "
                    f"{e['old_sha']} → {e['new_sha']} "
                    f"({e['msg'][:60]}) ahead={e['ahead']}"
                )
            print(f"   {n} repo(s) changed, .jsonl updated, state saved")
            sys.exit(1)  # exit 1 = activity detected (for watchdog script to react)
        else:
            print(f"✅ 5 仓无活动 ({now_iso()[:19]})")
            sys.exit(0)
    elif cmd == "activity":
        # 读 git-activity.jsonl
        since = None
        limit = 50
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--since" and i + 1 < len(sys.argv):
                since = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        entries = read_activity(since_ts=since, limit=limit)
        print(fmt_activity(entries))
    elif cmd == "git-state":
        # 列 5 仓当前状态
        state = collect_git_activity_state()
        for name, info in state.items():
            if not info.get("exists"):
                print(f"  ❌ {name}: .git not found at {info.get('path')}")
                continue
            print(
                f"  {name}: {info.get('sha', '?')[:8] if info.get('sha') else 'NO-COMMIT'} "
                f"({info.get('branch', '?')}) "
                f"ahead={info.get('ahead')} behind={info.get('behind')}"
            )
            print(f"    {info.get('msg', '')[:80]}")
    else:
        print(f"unknown cmd: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
