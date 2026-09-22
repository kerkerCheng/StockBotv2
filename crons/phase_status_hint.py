"""phase_status_hint.py — SessionStart hook：開 session 就說現在該 /phase-run 還是 /phase-plan。

只讀兩份 tracked 文件：`docs/plans/README.md` 的「Phase ↔ plan」對照表，與 active plan 的 §0.5 進度表。
不寫入、不連外；任何解析失敗都安靜跳過（不能讓 session 開不起來）。
雙通道輸出同 `pending_leads_digest.py`：systemMessage 給終端、additionalContext 進 agent context。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS_README = ROOT / "docs" / "plans" / "README.md"

_ROW = re.compile(r"^\|\s*(?P<phase>[^|]+?)\s*\|\s*(?P<plan>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*$")
_LINK = re.compile(r"\]\(([^)]+)\)")
_STEP = re.compile(r"^\|\s*(?P<step>[^|]+?)\s*\|\s*(?P<what>[^|]+?)\s*\|\s*(?P<state>[^|]+?)\s*\|")


def _phase_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Phase |") and "plan 檔" in line:
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            m = _ROW.match(line)
            if not m or set(m.group("phase")) <= {"-"}:
                continue
            link = _LINK.search(m.group("plan"))
            rows.append({
                "phase": m.group("phase").strip(),
                "plan": link.group(1) if link else "",
                "status": m.group("status").strip(),
            })
    return rows


def _next_step(plan_path: Path) -> str | None:
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError:
        return None
    seen_header = False
    for line in text.splitlines():
        if line.startswith("| Step |"):
            seen_header = True
            continue
        if seen_header:
            if not line.startswith("|"):
                break
            m = _STEP.match(line)
            if not m or set(m.group("step")) <= {"-"}:
                continue
            if "✅" not in m.group("state"):
                return f"{m.group('step')}（{m.group('what')}）"
    return None


def main() -> int:
    try:
        rows = _phase_rows(PLANS_README.read_text(encoding="utf-8"))
    except OSError:
        return 0
    if not rows:
        return 0
    active = [r for r in rows if r["status"] == "active"]
    if len(active) == 1:
        plan = active[0]
        step = _next_step(ROOT / "docs" / "plans" / plan["plan"]) if plan["plan"] else None
        msg = (
            f"🧭 Phase {plan['phase']} 執行中｜下一個 Step：{step or '（進度表讀不到，看 git log）'}"
            "｜建議模型：便宜｜貼 /phase-run"
        )
    elif len(active) > 1:
        msg = "🧭 對照表有兩份以上 active plan——先修 docs/plans/README.md 再開工"
    else:
        pending = [r for r in rows if "尚無" in r["plan"] or r["status"] in {"—", ""}]
        if pending:
            msg = f"🧭 沒有 active plan｜Phase {pending[0]['phase']} 待寫 plan｜建議模型：fable｜貼 /phase-plan"
        else:
            msg = "🧭 所有 Phase 都有 plan 且無 active——看 docs/ROADMAP.md 決定下一步"
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "【Phase 狀態——請在第一則回覆開頭轉述】" + msg,
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001 — hook 絕不能讓 session 開不起來
        sys.exit(0)
