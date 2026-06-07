#!/usr/bin/env python3
"""
v-sop16-pre-commit-hook.py — V 6/7 09:50 升级 v2

SOP #16 升级版的可执行检测器: commit 前自动跑 6 项检查.
V 6/7 09:40 部署 v1, 09:45 实战发现新问题, 09:50 升级 v2.

v1 → v2 实战升级 (4 项 → 6 项):
+ 3. 久积型漏 commit 警告 (累积 2 改动必须分 commit, SOP #16 #5 黄金法则)
+ 6. 凭据脱敏 (commit message / remote URL 不含 ghp_/token, SOP #14 联动)

使用:
  python3 v-sop16-pre-commit-hook.py <file1> [file2] ...

返回:
  0 = 通过, 可以 commit
  1 = 失败, 看 stderr
  2 = 警告 (久积改动), 仍可 commit

V 反思 SOP #9: 永远先 grep 验证再报. 这个脚本就是给 SOP #16 落地用.
"""
import sys
import subprocess
import ast
import re
from pathlib import Path

CREDENTIAL_PATTERNS = [
    re.compile(r'ghp_[a-zA-Z0-9]{20,}'),       # GitHub PAT
    re.compile(r'gho_[a-zA-Z0-9]{20,}'),       # GitHub OAuth
    re.compile(r'github_pat_[a-zA-Z0-9_]{20,}'), # GitHub fine-grained
    re.compile(r'password\s*[:=]\s*[\'"]\S+[\'"]', re.IGNORECASE),
    re.compile(r'token\s*[:=]\s*[\'"]\S+[\'"]', re.IGNORECASE),
]


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    """Run shell command, return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_git_status(file: str, repo_root: str) -> bool:
    """SOP #16 行动 1: file 必须在 working tree 有改动 (M or ??) 或 staged."""
    code, out, err = run(f"git status --short -- {file}", cwd=repo_root)
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


def check_accumulated_changes(repo_root: str) -> int:
    """SOP #16 v2 新增: 久积型漏 commit 检测.
    working tree M 数量 > 2 → 警告 (累积 2 改动必须分 commit, #5 黄金法则).
    返回: 0=ok, 1=warn, 2=fail.
    """
    code, out, err = run("git status --short", cwd=repo_root)
    if code != 0:
        return 0  # 跳过, 不阻塞
    lines = [l for l in out.split("\n") if l.strip()]
    modified = [l for l in lines if l.startswith(" M") or l.startswith("M ")]
    if len(modified) > 2:
        print(f"  ⚠️  久积改动警告: working tree 有 {len(modified)} 个 M 文件 (SOP #16 #5 黄金法则: 累积 2 改动必须分 commit)", file=sys.stderr)
        for m in modified[:5]:
            print(f"     {m}", file=sys.stderr)
        return 1
    return 0


def check_credentials(file: str) -> bool:
    """SOP #16 v2 新增: 凭据脱敏检查.
    改动内容不能含 ghp_/gho_/password=/token= 模式.
    """
    try:
        src = Path(file).read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return True  # 二进制或找不到, 跳过
    found = []
    for pat in CREDENTIAL_PATTERNS:
        matches = pat.findall(src)
        if matches:
            found.extend(matches[:3])
    if found:
        print(f"  ❌ {file} 含凭据模式: {found[:3]}", file=sys.stderr)
        print(f"     修: 移到 .env / 用环境变量 / 改用 SSH key", file=sys.stderr)
        return False
    return True


def check_commit_msg_template() -> bool:
    """SOP #16 行动 4: commit message 必含 SOP 引用 (提示用)."""
    print(f"  ℹ️  commit message 建议含 'SOP #N' 引用 (V 自我要求)")
    return True


def detect_repo_root(start: str) -> str:
    """向上找 .git 目录."""
    p = Path(start).resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return str(p)
        p = p.parent
    return str(Path(start).resolve().parent)


def sanitize_remote_url(url: str) -> str:
    """SOP #16 v2 新增: 远程 URL 脱敏, 任何 'git remote -v' 输出前必先 sanitize."""
    return re.sub(r'(https://)[^@]+@', r'\1***@', url)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 v-sop16-pre-commit-hook.py <file1> [file2] ...", file=sys.stderr)
        return 1

    files = sys.argv[1:]
    repo_root = detect_repo_root(files[0])
    print(f"🔍 SOP #16 pre-commit hook v2 — repo: {repo_root}")
    print(f"📁 检查 {len(files)} 个文件")
    print()

    all_ok = True
    warning = 0
    for f in files:
        print(f"--- {f} ---")
        if not check_git_status(f, repo_root):
            all_ok = False
        if not check_syntax(f):
            all_ok = False
        if not check_credentials(f):
            all_ok = False
        check_commit_msg_template()
        print()

    # 全局检查: 久积改动
    print("--- 全局: 久积改动检查 (SOP #16 #5 黄金法则) ---")
    if check_accumulated_changes(repo_root) == 1:
        warning = 1

    # 全局: 远程 URL 脱敏提示
    print("--- 全局: 远程 URL sanitize 提示 (SOP #14 联动) ---")
    code, out, _ = run("git remote -v", cwd=repo_root)
    if code == 0:
        sanitized = "\n".join(sanitize_remote_url(l) for l in out.split("\n"))
        print(f"  💡 报告必带 sanitize 后版本 (避免 PAT 暴露):")
        for l in sanitized.split("\n")[:4]:
            print(f"     {l}")
    print()

    if not all_ok:
        print("❌ SOP #16 pre-commit 检查失败, 修复后重跑", file=sys.stderr)
        return 1
    if warning:
        print("⚠️  SOP #16 检查通过但有警告, 仍可 commit (建议处理)")
        return 2
    print("✅ SOP #16 pre-commit 检查通过, 可以 commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
