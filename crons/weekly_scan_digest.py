"""
weekly_scan_digest.py — SessionStart hook: 開 session 時列出待審的 weekly-scan PR/Issue。

U7b（見 docs/plans/2026-07-10-006-...-plan.md）。這是 convenience recap，不是可靠性
保證——真正確保「使用者一定被通知到」的是 GitHub 本身的 email/手機通知（R10）。
本 hook 只是你剛好開了本機 session 時，順手把待審清單擺到眼前。

與 crons/thesis_freshness_check.py 同一種寫法：安靜原則（沒有待審項目就不輸出），
gh 未安裝/未登入/網路失敗都優雅跳過，不能讓 session 開不起來。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.intake import pending_intake_files

REPO = "kerkerCheng/StockBotv2"
LABEL = "weekly-scan"
LEDGER_PATHS = ["library/raw", "extractions", "library/intake"]


def _gh() -> str | None:
    """找 gh 執行檔；PATH 沒有就試預設安裝路徑。"""
    path = shutil.which("gh")
    if path:
        return path
    default = r"C:\Program Files\GitHub CLI\gh.exe"
    return default if shutil.os.path.exists(default) else None


def _list(kind: str, gh: str) -> list[dict]:
    """kind: 'pr' or 'issue'。回傳開著的 weekly-scan 項目。"""
    try:
        out = subprocess.run(
            [gh, kind, "list", "--repo", REPO, "--label", LABEL,
             "--state", "open", "--json", "number,title,url"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return []
        return json.loads(out.stdout or "[]")
    except Exception:
        return []


def _backlog_count(gh: str) -> int:
    """開著但沒有 weekly-scan label 的 issue 數（工程 backlog，如 #3/#4/#5）。"""
    try:
        out = subprocess.run(
            [gh, "issue", "list", "--repo", REPO, "--state", "open",
             "--json", "number,labels"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return 0
        items = json.loads(out.stdout or "[]")
        return sum(1 for i in items
                   if LABEL not in {l["name"] for l in i.get("labels", [])})
    except Exception:
        return 0


def _unpushed_intake_commits(root: Path = ROOT) -> int:
    """Count local-only commits that touch an intake ledger path."""

    try:
        result = subprocess.run(
            [
                "git",
                "rev-list",
                "origin/master..HEAD",
                "--",
                *LEDGER_PATHS,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            shell=False,
        )
        if result.returncode != 0:
            return 0
        return len([line for line in result.stdout.splitlines() if line.strip()])
    except Exception:
        return 0


def intake_pending_summary(root: Path = ROOT) -> dict:
    pending = pending_intake_files(root=root)
    untracked = pending.get("untracked") or []
    modified = pending.get("modified") or []
    commits = _unpushed_intake_commits(root)
    return {
        "untracked": untracked,
        "modified": modified,
        "unpushed_commits": commits,
        "total": len(untracked) + len(modified) + commits,
    }


def main() -> int:
    intake_summary = intake_pending_summary()
    gh = _gh()
    prs = _list("pr", gh) if gh else []
    issues = _list("issue", gh) if gh else []
    backlog = _backlog_count(gh) if gh else 0
    if not prs and not issues and not backlog and not intake_summary["total"]:
        return 0  # 什麼都沒有，安靜過去

    parts = []
    if prs or issues:
        lines = [f"PR #{p['number']} {p['title']}" for p in prs]
        lines += [f"Issue #{i['number']} {i['title']}" for i in issues]
        parts.append(
            f"📬 weekly-scan: {len(prs) + len(issues)} 件待審（"
            + "；".join(lines[:4]) + ("…" if len(lines) > 4 else "") + "）"
        )
    if backlog:
        parts.append(f"🔧 另有 {backlog} 個 backlog issue 開著（詳見 GitHub 或 plan 現況快照）")
    if intake_summary["total"]:
        parts.append(
            f"🗂 {intake_summary['total']} 筆遠端入圖待補 commit/push"
            "（開 session 後說「補提交入圖」即可處理）"
        )

    print(json.dumps({"systemMessage": " ".join(parts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
