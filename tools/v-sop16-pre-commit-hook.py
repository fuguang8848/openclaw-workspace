#!/usr/bin/env python3
"""
v-sop16-pre-commit-hook.py — V 6/7 09:40 部署

SOP #16 升级版的可执行检测器: commit 前自动跑 4 项检查.
按 SOP #16 行动 6 步, 把第 1-2 步 (diff + 语法) 自动化,
避免 V / 任何 sub-agent 改完漏 commit 或语法错.

使用:
  python3 v-sop16-pre-commit-hook.py <file1> [file2] ...

返回:
  0 = 通过, 可以 commit
  1 = 失败, 看 stderr

V 反思 SOP #9: 永远先 grep 验证再报. 这个脚本就是给 SOP #16 落地用.
"""
import sys
import subprocess
import ast
import re
from pathlib import Path


SOP_REFERENCE_PATTERN = re.compile(r'SOP\s*#\d+', re.IGNORECASE)


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    """Run shell command, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_git_status(file: str, repo_root: str) -> bool:
    """SOP #16 行动 1: file 必须在 working tree 有改动 (M or ??) 或 staged."""
    code, out, err = run(
        f"git status --short -- {file}", cwd=repo_root
    )
    if code != 0:
        print(f"  ❌ git status 失败: {err}", file=sys.stderr)
        return False
    if not out:
        print(f"  ⚠️  {file} 在 working tree 无改动 (没改? 已 commit?)", file=sys.stderr)
        return False
    print(f"  ✅ {file} 改动状态: {out}")
    return True


def check_syntax(file: str) -> bool:
    """SOP #16 行动 2: Python 文件 AST 解析必须通过."""
    if not file.endswith(".py"):
        print(f"  ⏭️  {file} 非 .py, 跳语法检查")
        return True
    try:
        src = Path(file).read_text(encoding="utf-8")
        ast.parse(src)
        print(f"  ✅ {file} AST 解析 OK ({len(src)} bytes, {src.count(chr(10))+1} 行)")
        return True
    except SyntaxError as e:
        print(f"  ❌ {file} AST 解析失败: {e}", file=sys.stderr)
        return False


def check_commit_msg_template() -> bool:
    """SOP #16 行动 4: commit message 必含 SOP 引用. (提示用, 实际 commit 时 V 守)"""
    print(f"  ℹ️  commit message 建议含 'SOP #N' 引用 (V 自我要求)")
    return True


def check_ahead_remote(file: str, repo_root: str, remote: str = "origin") -> bool:
    """SOP #16 行动 6: file commit 后, 检查是否推到 {remote}."""
    # 这一步在 commit 后跑, 这里是占位
    code, out, err = run(
        f"git rev-list --count {remote}/$(git rev-parse --abbrev-ref HEAD)..HEAD",
        cwd=repo_root
    )
    if code != 0:
        print(f"  ⚠️  {remote} 远端无匹配 (本地仓?), 跳 ahead check", file=sys.stderr)
        return True
    ahead = int(out) if out else 0
    if ahead > 0:
        print(f"  ⚠️  本地领先 {remote} {ahead} commit, 待 push (SOP #16 行动 6)")
        return True  # 警告而非失败
    print(f"  ✅ 本地与 {remote} 同步 (ahead=0)")
    return True


def detect_repo_root(start: str) -> str:
    """向上找 .git 目录."""
    p = Path(start).resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return str(p)
        p = p.parent
    return str(Path(start).resolve().parent)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 v-sop16-pre-commit-hook.py <file1> [file2] ...", file=sys.stderr)
        return 1

    files = sys.argv[1:]
    repo_root = detect_repo_root(files[0])
    print(f"🔍 SOP #16 pre-commit hook — repo: {repo_root}")
    print(f"📁 检查 {len(files)} 个文件")
    print()

    all_ok = True
    for f in files:
        print(f"--- {f} ---")
        if not check_git_status(f, repo_root):
            all_ok = False
        if not check_syntax(f):
            all_ok = False
        check_commit_msg_template()
        print()

    if not all_ok:
        print("❌ SOP #16 pre-commit 检查失败, 修复后重跑", file=sys.stderr)
        return 1

    print("✅ SOP #16 pre-commit 检查通过, 可以 commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
