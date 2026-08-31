"""安全發布本機 daily routine 的兩個 tracked state files。

排程只准提交 pending leads 與穩定 pq2 編號池；不吃外部 path 參數、不碰使用者
已 staged 的內容，也不會把其他未推送的 master commits 一併推上去。
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STATE_PATHS = (
    "library/leads/pending_leads.json",
    "library/leads/todo_pool.json",
)
COMMIT_PREFIX = "chore(daily):"
# 本 publisher 提交時的**完整** subject。`writer_guard` 靠它辨認「這筆共用檔變更
# 是排程做的」——必須是完整字串而不是 prefix：互動 session 也會用 `chore(daily):`
# 這個房規慣例寫 pool sync，只比對 prefix 會把自己的 commit 判成排程（2026-08-31 實測）。
COMMIT_SUBJECT = f"{COMMIT_PREFIX} sync local approval state"


def _git(root: Path, *args: str, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return proc.returncode, (proc.stdout or "")


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _result(status: str, *, committed: bool = False, pushed: bool = False) -> dict[str, Any]:
    return {"status": status, "committed": committed, "pushed": pushed}


def publish_daily_state(root: Path | str = ROOT) -> dict[str, Any]:
    """Commit/push exact daily state paths，任何邊界不符都 fail closed。"""
    repo = Path(root)

    code, branch = _git(repo, "branch", "--show-current")
    if code != 0 or branch.strip() != "master":
        return _result("guard_wrong_branch")

    code, private_paths = _git(repo, "ls-files", "library/private")
    if code != 0 or _lines(private_paths):
        return _result("guard_private_tracked")

    code, staged = _git(repo, "diff", "--cached", "--name-only")
    if code != 0 or _lines(staged):
        return _result("guard_staged_changes")

    code, head = _git(repo, "rev-parse", "HEAD")
    if code != 0:
        return _result("guard_git_state")
    code, upstream = _git(repo, "rev-parse", "origin/master")
    if code != 0:
        return _result("guard_missing_upstream")

    # 不把使用者先前尚未 push 的工作一併送出。唯一例外是上一輪本腳本已 commit
    # 但 push 失敗；那種 commit 必須只碰 STATE_PATHS，且 subject 帶固定 prefix。
    if head.strip() != upstream.strip():
        code, ahead_paths = _git(repo, "diff", "--name-only", "origin/master..HEAD")
        if code != 0 or not set(_lines(ahead_paths)).issubset(set(STATE_PATHS)):
            return _result("guard_unpushed_commits")
        code, subjects = _git(repo, "log", "--format=%s", "origin/master..HEAD")
        if code != 0 or not _lines(subjects) or any(
            not subject.startswith(COMMIT_PREFIX) for subject in _lines(subjects)
        ):
            return _result("guard_unpushed_commits")

    code, changed = _git(repo, "status", "--porcelain", "--", *STATE_PATHS)
    if code != 0:
        return _result("status_failed")

    committed = False
    # porcelain 的第一欄可能是空白（例如 `` M path``），不可先 strip。
    status_lines = [line.rstrip() for line in changed.splitlines() if line.strip()]
    expected = {line[3:].strip().replace("\\", "/") for line in status_lines}
    if expected:
        if not expected.issubset(set(STATE_PATHS)):
            return _result("guard_pathset")
        code, _ = _git(
            repo,
            "commit",
            "-m",
            COMMIT_SUBJECT,
            "--",
            *STATE_PATHS,
        )
        if code != 0:
            return _result("commit_failed")
        committed = True

        code, committed_paths = _git(
            repo, "show", "--name-only", "--pretty=format:", "HEAD"
        )
        if code != 0 or set(_lines(committed_paths)) != expected:
            return _result("guard_commit_pathset", committed=True)

    # 即使本輪沒新變更，仍可補推上一輪由本腳本留下的安全 commit。
    code, head = _git(repo, "rev-parse", "HEAD")
    code2, upstream = _git(repo, "rev-parse", "origin/master")
    if code != 0 or code2 != 0:
        return _result("guard_git_state", committed=committed)
    if head.strip() == upstream.strip():
        return _result("no_change", committed=committed, pushed=False)

    code, _ = _git(repo, "push", "origin", "master", timeout=60)
    if code != 0:
        return _result("push_failed", committed=committed)
    return _result("pushed", committed=committed, pushed=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="發布本機 daily routine 的窄 state pathset")
    parser.parse_args()
    result = publish_daily_state()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"no_change", "pushed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
