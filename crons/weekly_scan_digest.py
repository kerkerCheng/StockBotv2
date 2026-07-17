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
from mcp_server.research_actions import count_action_states, iter_actions

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


def pending_onboard_companies(root: Path = ROOT) -> list[str]:
    """抽取語料裡的 Company id，凡 TICKER_MAP 沒有登記（含明確 None）就算待 onboard 決定。"""
    try:
        from loader.load_to_neo4j import TICKER_MAP
    except Exception:
        return []
    company_ids: set[str] = set()
    for path in (root / "extractions").glob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        for node in doc.get("nodes", []):
            if (
                isinstance(node, dict)
                and node.get("type") == "Company"
                and isinstance(node.get("id"), str)
            ):
                company_ids.add(node["id"])
    return sorted(company_ids - set(TICKER_MAP))


def intake_pending_summary(root: Path = ROOT) -> dict:
    pending = pending_intake_files(root=root)
    action_paths = {
        path
        for record in iter_actions(root=root)
        if record.get("state") in {"applied", "committed_not_pushed"}
        and record.get("git", {}).get("status")
        in {"pending", "committed_not_pushed"}
        for path in (record.get("git", {}).get("eligible_paths") or [])
    }
    untracked = sorted(set(pending.get("untracked") or []) - action_paths)
    modified = sorted(set(pending.get("modified") or []) - action_paths)
    action_counts = count_action_states(root=root)
    all_commits = _unpushed_intake_commits(root)
    legacy_commits = max(0, all_commits - action_counts["committed_not_pushed"])
    return {
        "untracked": untracked,
        "modified": modified,
        "unpushed_commits": legacy_commits,
        "research_actions": action_counts,
        "total": (
            len(untracked)
            + len(modified)
            + legacy_commits
            + action_counts["total"]
        ),
    }


def main() -> int:
    intake_summary = intake_pending_summary()
    onboard_pending = pending_onboard_companies()
    gh = _gh()
    prs = _list("pr", gh) if gh else []
    issues = _list("issue", gh) if gh else []
    backlog = _backlog_count(gh) if gh else 0
    if (
        not prs
        and not issues
        and not backlog
        and not intake_summary["total"]
        and not onboard_pending
    ):
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
    actions = intake_summary["research_actions"]
    action_parts = []
    if actions["ready_for_approval"]:
        action_parts.append(f"{actions['ready_for_approval']} 待核准")
    if actions["partial_apply"]:
        action_parts.append(f"{actions['partial_apply']} 部分入圖待續跑")
    if actions["uncommitted"]:
        action_parts.append(f"{actions['uncommitted']} 待本機 commit")
    if actions["committed_not_pushed"]:
        action_parts.append(f"{actions['committed_not_pushed']} 已 commit 待 push")
    if action_parts:
        parts.append(
            "🧭 Research Actions: " + "；".join(action_parts)
            + "（可說「查看待辦入圖」或「補提交入圖」）"
        )
    if onboard_pending:
        parts.append(
            f"🏷 {len(onboard_pending)} 家公司待 onboard 決定（TICKER_MAP 未登記）："
            + "、".join(onboard_pending[:5])
            + ("…" if len(onboard_pending) > 5 else "")
            + "（說「onboard <公司>」收尾；決定不追的在 TICKER_MAP 填 None）"
        )
    legacy_total = (
        len(intake_summary["untracked"])
        + len(intake_summary["modified"])
        + intake_summary["unpushed_commits"]
    )
    if legacy_total:
        parts.append(
            f"🗂 {legacy_total} 筆舊版 intake ledger 待補 commit/push"
            "（可說「補提交入圖」）"
        )

    print(json.dumps({"systemMessage": " ".join(parts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
