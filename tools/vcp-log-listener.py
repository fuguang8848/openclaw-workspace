#!/usr/bin/env python3
"""
vcp-log-listener.py — VCP VCPLog WebSocket 监听器 (V 18:11 新增)

用途:
  监听 VCP VCPLog WS 端点, 接收 VCP 广播消息, 解析后写 daily memory
  error 级消息同步写桌面告警, 让浮光/Claude 能即时看到 VCP 异常

来源 (V 18:11):
  - 浮光 18:03 指示 "按建议来" (E 任务: vcp-log-listener.py WS 监听)
  - V 11:25 学习 hermes 对 VCP 思考报告发现 VCP archery/VCPLog/Fold 协议
  - 浮光 10:55 元反思 "多发现 + 第一时间解决不推"

VCP WS 协议:
  - URL: ws://127.0.0.1:6005/VCPlog/VCP_Key=vcp_websocket_2026
  - 客户端类型: VCPLog
  - server 不主动 push 普通日志, 只在 plugin callback 时 push
  - 接收格式: {"type": ..., "data": ...}

输出:
  - daily memory: ~/.openclaw/workspace/memory/vcp-logs/YYYY-MM-DD.jsonl
  - 桌面告警: ~/桌面/vcp-alerts.log (error 级)
  - 状态: ~/.openclaw/workspace/.cache/vcp-listener.status.json

使用:
  # 跑一次 (前台)
  python3 vcp-log-listener.py run --once

  # 后台守护
  nohup python3 vcp-log-listener.py daemon > /tmp/vcp-listener.log 2>&1 &

  # 看状态
  python3 vcp-log-listener.py status

  # 测试协议
  python3 vcp-log-listener.py test

副作用 (V 11:33 永久教训):
  - 必跑 5 端口 check: 11434/6005/8080/18081/18789
  - 后台启要 nohup + setsid, 别绑死 terminal
  - 必卸 /home/fuguang/.openclaw/workspace/tools/__pycache__/ (新增 .gitignore 已防)
"""
import argparse
import json
import os
import sys
import time
import signal
import socket
from datetime import datetime
from pathlib import Path

# VCP WS 配置 (V 11:25 永久 + V 18:11 实测)
VCP_WS_URL = os.environ.get("VCP_WS_URL", "ws://127.0.0.1:6005/VCPlog/VCP_Key=vcp_websocket_2026")
VCP_HTTP = "http://127.0.0.1:6005"

# 输出路径
WORKSPACE = Path("/home/fuguang/.openclaw/workspace")
LOG_DIR = WORKSPACE / "memory" / "vcp-logs"
CACHE_DIR = WORKSPACE / ".cache"
ALERT_FILE = Path("/home/fuguang/桌面/vcp-alerts.log")
STATUS_FILE = CACHE_DIR / "vcp-listener.status.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def classify_msg(msg: dict) -> str:
    """VCP 消息分类: info / warn / error"""
    t = (msg.get("type") or "").lower()
    if any(k in t for k in ["error", "fail", "exception", "fatal"]):
        return "error"
    if any(k in t for k in ["warn", "warning", "deprecat", "retry", "fallback"]):
        return "warn"
    return "info"


def save_daily(msg: dict, level: str):
    """写 daily memory (jsonl 格式)"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}.jsonl"
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "type": msg.get("type", "?"),
        "data": msg.get("data", msg),
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_alert(msg: dict, level: str, raw: str):
    """error/warn 级写桌面告警"""
    if level not in ("error", "warn"):
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level.upper()}] {raw[:500]}\n"
    with open(ALERT_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def save_status(state: str, last_msg=None, count=0):
    """状态文件 (PID + last message + count)"""
    status = {
        "state": state,
        "pid": os.getpid(),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "ws_url": VCP_WS_URL,
        "count": count,
        "last_msg": (last_msg or "")[:200],
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def vcp_health() -> bool:
    """VCP HTTP 端口健康检查"""
    try:
        with socket.create_connection(("127.0.0.1", 6005), timeout=2):
            return True
    except Exception:
        return False


def run_once(timeout: int = 5) -> dict:
    """跑一次: 连接 + 接收 timeout 秒 + 退出"""
    import websocket  # websocket-client

    print(f"[V 18:11] 试连 VCP WS: {VCP_WS_URL}")
    save_status("connecting")
    if not vcp_health():
        print(f"[V 18:11] ✗ VCP 6005 不在监听")
        save_status("vcp_down")
        return {"ok": False, "reason": "vcp_down"}

    try:
        ws = websocket.create_connection(VCP_WS_URL, timeout=timeout)
        print(f"[V 18:11] ✓ WS 连接 OK")
        save_status("connected")

        # 收 connection_ack
        ws.settimeout(2)
        try:
            ack = ws.recv()
            print(f"[V 18:11] 收到 ack: {ack[:100]}")
        except Exception:
            ack = None

        # 等 timeout 秒, 收 VCP 广播
        print(f"[V 18:11] 等待 {timeout}s VCP 广播...")
        count = 0
        deadline = time.time() + timeout
        ws.settimeout(1)
        while time.time() < deadline:
            try:
                raw = ws.recv()
                if raw:
                    count += 1
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        msg = {"type": "raw", "data": raw}
                    level = classify_msg(msg)
                    save_daily(msg, level)
                    save_alert(msg, level, raw)
                    print(f"  [{count}] [{level}] {raw[:120]}")
                    save_status("running", raw, count)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                print(f"[V 18:11] WS 收消息错: {e}")
                break

        ws.close()
        print(f"[V 18:11] ✓ 跑一次完成, 收 {count} 条消息")
        save_status("idle", count=count)
        return {"ok": True, "count": count, "ack": ack}
    except Exception as e:
        print(f"[V 18:11] ✗ WS 失败: {e}")
        save_status("error", str(e))
        return {"ok": False, "reason": str(e)}


def daemon_mode():
    """后台守护: 重连循环"""
    import websocket  # noqa
    print(f"[V 18:11] 启动 daemon 模式")
    print(f"[V 18:11] WS URL: {VCP_WS_URL}")
    print(f"[V 18:11] daily 写: {LOG_DIR}")
    print(f"[V 18:11] alert 写: {ALERT_FILE}")

    count = 0
    save_status("daemon_starting")

    while True:
        try:
            ws = websocket.create_connection(VCP_WS_URL, timeout=5)
            save_status("connected", count=count)
            print(f"[V 18:11] ✓ WS 连接 OK (累计 {count} 条)")

            try:
                ack = ws.recv()
            except Exception:
                ack = None

            while True:
                try:
                    raw = ws.recv()
                    if raw:
                        count += 1
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            msg = {"type": "raw", "data": raw}
                        level = classify_msg(msg)
                        save_daily(msg, level)
                        save_alert(msg, level, raw)
                        save_status("running", raw, count)
                        if count % 10 == 0:
                            print(f"  [daemon] 累计 {count} 条")
                except websocket.WebSocketTimeoutException:
                    # 1s 无消息, 继续等
                    pass
                except websocket.WebSocketConnectionClosedException:
                    print(f"[V 18:11] WS 断, 重连...")
                    break
                except Exception as e:
                    print(f"[V 18:11] WS 错: {e}")
                    break
            ws.close()
        except Exception as e:
            print(f"[V 18:11] WS 连接失败: {e}, 5s 后重试")
            save_status("reconnecting", str(e), count)
            time.sleep(5)


def show_status():
    """看状态"""
    if not STATUS_FILE.exists():
        print("[V 18:11] 状态文件不存在, 未启动过")
        return
    with open(STATUS_FILE) as f:
        status = json.load(f)
    print(json.dumps(status, ensure_ascii=False, indent=2))


def five_port_check():
    """副作用 5 端口 check (V 11:33 永久)"""
    ports = {
        11434: "Ollama",
        6005: "VCP",
        8080: "AgentTeam",
        18081: "AgentSymphony",
        18789: "OpenClaw",
    }
    print(f"[V 18:11] 5 端口副作用 check:")
    for port, name in ports.items():
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                print(f"  ✓ {port} {name} OK")
        except Exception as e:
            print(f"  ✗ {port} {name} FAIL: {e}")


def main():
    parser = argparse.ArgumentParser(description="VCP VCPLog WebSocket 监听器")
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="跑一次 (前台)")
    p_run.add_argument("--timeout", "-t", type=int, default=5, help="收消息秒数")
    p_run.add_argument("--once", action="store_true", help="run-once (测试用)")

    p_daemon = sub.add_parser("daemon", help="后台守护 (重连循环)")

    sub.add_parser("status", help="看状态")

    p_test = sub.add_parser("test", help="测试 VCP WS 协议")

    sub.add_parser("ports", help="5 端口副作用 check")

    args = parser.parse_args()

    if args.cmd == "run" or args.cmd == "test":
        result = run_once(timeout=args.timeout if hasattr(args, "timeout") else 5)
        sys.exit(0 if result.get("ok") else 1)
    elif args.cmd == "daemon":
        daemon_mode()
    elif args.cmd == "status":
        show_status()
    elif args.cmd == "ports":
        five_port_check()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
