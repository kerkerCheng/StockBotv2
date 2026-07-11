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

REPO = "kerkerCheng/StockBotv2"
LABEL = "weekly-scan"


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


def main() -> int:
    gh = _gh()
    if gh is None:
        return 0  # gh 不在，安靜跳過

    prs = _list("pr", gh)
    issues = _list("issue", gh)
    if not prs and not issues:
        return 0  # 沒有待審項目，安靜過去

    lines = []
    for p in prs:
        lines.append(f"PR #{p['number']} {p['title']}")
    for i in issues:
        lines.append(f"Issue #{i['number']} {i['title']}")

    msg = (
        f"📬 weekly-scan: {len(prs) + len(issues)} 件待審（"
        + "；".join(lines[:4])
        + ("…" if len(lines) > 4 else "")
        + "）— 要現在看嗎？"
    )
    print(json.dumps({"systemMessage": msg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
