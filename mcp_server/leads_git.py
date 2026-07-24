"""窄 pathset commit/push：只准 `library/leads/pending_leads.json`（plan U2/R9）。

這是對既有「遠端無 Git」邊界的**刻意窄例外**：chat 經 MCP 改 leads 狀態後，
本機 MCP server 把 leads.json commit+push，讓 cloud routine 每天讀 pushed clone
看到最新狀態。pathspec **寫死**、不吃使用者輸入；commit 後驗證只碰了這一個檔；
只准動 attention metadata，**永不** commit 圖/碼/extraction（那些走本機 publisher）。

錯誤只回穩定 status，不外洩絕對路徑或 git stderr repr。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

LEADS_RELPATH = "library/leads/pending_leads.json"


def _git(repo_root: Path, *args: str, timeout: int = 20) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return proc.returncode, (proc.stdout or "")


def commit_and_push_leads(repo_root: Path | str, *, message: str) -> dict[str, Any]:
    """對 leads.json（唯一 pathspec）scoped commit + push。冪等：無變更回 no_change。

    回傳 {status, committed, pushed}；status ∈ no_change/committed/commit_failed/
    push_failed/guard_failed。不 raise、不外洩路徑。
    """
    root = Path(repo_root)

    # 1. 該檔相對 HEAD 是否有變更（porcelain 針對單一 path）
    code, out = _git(root, "status", "--porcelain", "--", LEADS_RELPATH)
    if code != 0:
        return {"status": "commit_failed", "committed": False, "pushed": False}
    if not out.strip():
        return {"status": "no_change", "committed": False, "pushed": False}

    # 2. scoped commit：git commit -m <msg> -- <path> 只提交這一個 path，忽略
    #    index 其他內容（-m 必須在 -- pathspec 之前）
    code, _ = _git(root, "commit", "-m", message, "--", LEADS_RELPATH)
    if code != 0:
        return {"status": "commit_failed", "committed": False, "pushed": False}

    # 3. 防禦：驗證這個 commit 只碰了 leads.json（belt-and-suspenders）
    code, changed = _git(root, "show", "--name-only", "--pretty=format:", "HEAD")
    touched = {line.strip() for line in changed.splitlines() if line.strip()}
    if touched != {LEADS_RELPATH}:
        # 不該發生（scoped commit 應只含此檔）；回 guard_failed 讓上層停用此路徑
        return {"status": "guard_failed", "committed": True, "pushed": False}

    # 4. push（best-effort；失敗不 corrupt，本機 commit 已成立，下次同步補）
    code, _ = _git(root, "push", "origin", "HEAD")
    if code != 0:
        return {"status": "push_failed", "committed": True, "pushed": False}
    return {"status": "committed", "committed": True, "pushed": True}
