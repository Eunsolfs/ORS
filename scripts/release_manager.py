#!/usr/bin/env python3
"""ORS release update helper.

Features:
- Check whether origin/main or tags have newer versions
- Interactive upgrade by y/n/main/tag
- Run upgrade workflow: checkout target -> install deps -> migrate -> collectstatic -> check
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REPO_URL = "https://github.com/Eunsolfs/ORS.git"


@dataclass
class UpdateState:
    current_branch: str
    current_commit: str
    current_tag: Optional[str]
    remote_main_commit: str
    latest_tag: Optional[str]
    newer_tags: list[str]
    main_behind: bool


def is_git_repo() -> bool:
    return (ROOT_DIR / ".git").exists()


def run_git(args: list[str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def run_cmd(args: list[str], check: bool = True) -> int:
    print(f"[RUN] {shlex.join(args)}")
    proc = subprocess.run(args, cwd=ROOT_DIR, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {shlex.join(args)}")
    return proc.returncode


def parse_version(tag: str) -> tuple[int, ...]:
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?$", tag.strip())
    if not m:
        return tuple()
    parts = [int(x) for x in m.groups() if x is not None]
    return tuple(parts)


def sort_tags(tags: Iterable[str]) -> list[str]:
    with_ver: list[tuple[tuple[int, ...], str]] = []
    without_ver: list[str] = []
    for t in tags:
        ver = parse_version(t)
        if ver:
            with_ver.append((ver, t))
        else:
            without_ver.append(t)
    with_ver.sort(key=lambda x: x[0])
    without_ver.sort()
    return [t for _, t in with_ver] + without_ver


def ensure_clean_worktree() -> None:
    status = run_git(["status", "--porcelain"])
    if status.strip():
        raise RuntimeError("工作区有未提交改动，请先提交/清理后再升级。")


def ensure_remote_origin(repo_url: Optional[str]) -> None:
    existing = run_git(["remote", "get-url", "origin"], check=False)
    if existing:
        if repo_url and repo_url != existing:
            raise RuntimeError(f"检测到现有 origin={existing}，与 --repo-url={repo_url} 不一致。")
        return
    if not repo_url:
        raise RuntimeError("未检测到 git origin，请传入 --repo-url。")
    run_cmd(["git", "remote", "add", "origin", repo_url])


def bootstrap_repo_if_needed(repo_url: Optional[str]) -> bool:
    if is_git_repo():
        ensure_remote_origin(repo_url)
        return False
    if not repo_url:
        raise RuntimeError("当前目录没有 .git，请传入 --repo-url 以初始化仓库。")
    run_cmd(["git", "init"])
    run_cmd(["git", "remote", "add", "origin", repo_url])
    run_cmd(["git", "fetch", "--tags", "origin"])
    # First-time bootstrap in existing code directories may contain many
    # untracked files (because repository was not initialized yet). Force
    # checkout to align working tree to origin/main.
    run_cmd(["git", "checkout", "-f", "-B", "main", "origin/main"])
    return True


def detect_python_bins() -> tuple[Path, Path]:
    if sys.platform.startswith("win"):
        py = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
        pip = ROOT_DIR / ".venv" / "Scripts" / "pip.exe"
    else:
        py = ROOT_DIR / ".venv" / "bin" / "python"
        pip = ROOT_DIR / ".venv" / "bin" / "pip"
    if not py.exists() or not pip.exists():
        if sys.executable:
            return Path(sys.executable), Path(sys.executable)
        raise RuntimeError("未找到虚拟环境或系统 Python。")
    return py, pip


def collect_update_state() -> UpdateState:
    run_git(["fetch", "--tags", "origin"])

    current_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    current_commit = run_git(["rev-parse", "HEAD"])
    current_tag = run_git(["describe", "--tags", "--exact-match"], check=False) or None
    remote_main_commit = run_git(["rev-parse", "origin/main"])

    local_tags = [t for t in run_git(["tag", "--list"]).splitlines() if t.strip()]
    local_tags_sorted = sort_tags(local_tags)
    latest_tag = local_tags_sorted[-1] if local_tags_sorted else None

    newer_tags: list[str] = []
    if current_tag:
        current_ver = parse_version(current_tag)
        for t in local_tags_sorted:
            ver = parse_version(t)
            if current_ver and ver and ver > current_ver:
                newer_tags.append(t)
    else:
        newer_tags = local_tags_sorted

    main_behind = current_commit != remote_main_commit
    return UpdateState(
        current_branch=current_branch,
        current_commit=current_commit,
        current_tag=current_tag,
        remote_main_commit=remote_main_commit,
        latest_tag=latest_tag,
        newer_tags=newer_tags,
        main_behind=main_behind,
    )


def print_state(state: UpdateState) -> None:
    print("=== ORS 更新检查 ===")
    print(f"当前分支: {state.current_branch}")
    print(f"当前提交: {state.current_commit[:8]}")
    print(f"当前标签: {state.current_tag or '(无精确标签)'}")
    print(f"远端 main: {state.remote_main_commit[:8]}")
    print(f"最新标签: {state.latest_tag or '(无)'}")
    if state.newer_tags:
        print(f"可升级标签: {', '.join(state.newer_tags[-5:])}")
    else:
        print("可升级标签: (无)")
    print(f"main 是否有新提交: {'是' if state.main_behind else '否'}")
    print("")


def resolve_target(state: UpdateState, user_input: str) -> Optional[str]:
    v = user_input.strip()
    if not v or v.lower() == "n":
        return None
    if v.lower() == "y":
        if state.newer_tags:
            return state.newer_tags[-1]
        if state.main_behind:
            return "main"
        return None
    if v.lower() == "main":
        return "main"
    # tag input
    tag_exists = run_git(["rev-parse", "-q", "--verify", f"refs/tags/{v}"], check=False)
    if tag_exists:
        return v
    raise RuntimeError(f"标签不存在: {v}")


def checkout_target(target: str) -> None:
    if target == "main":
        run_cmd(["git", "checkout", "main"])
        run_cmd(["git", "pull", "--ff-only", "origin", "main"])
        return
    run_cmd(["git", "checkout", target])


def run_upgrade_steps(skip_test: bool) -> None:
    py, pip = detect_python_bins()
    if pip == py:
        run_cmd([str(py), "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        run_cmd([str(pip), "install", "-r", "requirements.txt"])
    run_cmd([str(py), "manage.py", "migrate", "--noinput"])
    run_cmd([str(py), "manage.py", "collectstatic", "--noinput"])
    run_cmd([str(py), "manage.py", "check"])
    if not skip_test:
        run_cmd([str(py), "manage.py", "test", "training"])


def main() -> int:
    parser = argparse.ArgumentParser(description="ORS 发布更新助手")
    parser.add_argument("--check", action="store_true", help="仅检查更新，不执行升级")
    parser.add_argument("--target", help="直接指定升级目标：main 或 tag（如 v1.2.0）")
    parser.add_argument("--yes", action="store_true", help="跳过交互确认（需搭配 --target）")
    parser.add_argument("--skip-test", action="store_true", help="升级时跳过 manage.py test training")
    parser.add_argument("--repo-url", help="远端仓库地址（默认: https://github.com/Eunsolfs/ORS.git）")
    args = parser.parse_args()

    try:
        repo_url = args.repo_url or DEFAULT_REPO_URL
        bootstrapped = bootstrap_repo_if_needed(repo_url)
        if bootstrapped:
            print("[INFO] 已初始化 git 仓库并对齐到 origin/main。")
        ensure_clean_worktree()
        state = collect_update_state()
        origin_url = run_git(["remote", "get-url", "origin"])
        print(f"当前远端: {origin_url}")
        print_state(state)

        if args.check:
            return 0

        target = args.target
        if not target:
            print("输入 y 自动升级到推荐目标（优先最新 tag，其次 main）")
            print("输入 main 升级到 origin/main")
            print("输入具体 tag（如 v1.2.0）升级到指定版本")
            print("输入 n 取消")
            choice = input("请选择 [y/main/tag/n]: ").strip()
            target = resolve_target(state, choice)
        else:
            target = resolve_target(state, target)

        if not target:
            print("未执行升级。")
            return 0

        if not args.yes:
            confirm = input(f"确认升级到 {target} ? [y/N]: ").strip().lower()
            if confirm != "y":
                print("已取消升级。")
                return 0

        checkout_target(target)
        run_upgrade_steps(skip_test=args.skip_test)
        print("")
        print(f"[OK] 升级完成，当前目标: {target}")
        print("[NEXT] 请在面板中重启 Gunicorn/Python 项目，并做页面冒烟验证。")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
