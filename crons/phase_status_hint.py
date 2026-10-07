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
_STEP = re.compile(r"^\|\s*(?P<step>[^|]+?)\s*\|\s*(?P<what>[^|]+?)\s*\|\s*(?P<state>[^|]+?)\s*\|(?:\s*(?P<who>[^|]*?)\s*\|)?")
#: 狀態格裡「續工指標」之後那一段就是下一個 session 該做的事（2026-10-07：hook 原本只印定義欄，
#: 7.1 定義寫的「InP 磊晶層說明（排第一件）」已做完，新 session 會照著做一件做過的事）。
_RESUME = "續工指標"
_RESUME_MAX = 400
#: 狀態欄以封閉字彙開頭、後面常接括號註記（「active（2026-10-01；…）」）。
#: ⚠ 2026-10-01 事發：原本比對 `== "active"`，Phase 4 那一列帶了註記就被當成「沒有 active plan」，
#: hook 叫人去寫 Phase 5 的 plan——執行者照做就會停在一份其實在跑的 plan 前面。
_ACTIVE_STATUS = re.compile(r"^active(?![A-Za-z_])")


def _is_active(status: str) -> bool:
    return bool(_ACTIVE_STATUS.match(status.strip()))


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


def _resume_pointer(state: str) -> str | None:
    i = state.find(_RESUME)
    if i < 0:
        return None
    text = state[i + len(_RESUME):].lstrip("*：: ")
    text = text.split("〔")[0].strip()
    return (text[:_RESUME_MAX] + "…") if len(text) > _RESUME_MAX else (text or None)


def _next_step(plan_path: Path) -> dict[str, str] | None:
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
                return {"step": m.group("step"), "what": m.group("what"), "state": m.group("state"),
                        "who": m.group("who") or ""}
    return None


def _step_text(step: dict[str, str] | None) -> str:
    if not step:
        return "（進度表讀不到，看 git log）"
    pointer = _resume_pointer(step["state"])
    return f"{step['step']}（續工：{pointer}）" if pointer else f"{step['step']}（{step['what']}）"


def _model_text(step: dict[str, str] | None, note: str) -> str:
    # 進度表的「執行者」欄優先：研究 Step 是強模型，便宜模型跑 /phase-run 做到這裡會停下交回——建議便宜等於白跑一趟。
    if step and "強模型" in step.get("who", ""):
        return "強模型（這個 Step 的執行者欄；便宜模型做到這裡會停下交回）"
    return f"便宜（對照表註記優先{'：' + note if note else ''}）"


def main() -> int:
    try:
        rows = _phase_rows(PLANS_README.read_text(encoding="utf-8"))
    except OSError:
        return 0
    if not rows:
        return 0
    active = [r for r in rows if _is_active(r["status"])]
    if len(active) == 1:
        plan = active[0]
        step = _next_step(ROOT / "docs" / "plans" / plan["plan"]) if plan["plan"] else None
        # 狀態欄的註記照抄（例：Phase 4「執行者全程強模型」）——「建議模型：便宜」是對照表的預設分工，註記優先。
        note = plan["status"].strip()[len("active"):].strip()
        msg = (
            f"🧭 Phase {plan['phase']} 執行中｜下一個 Step：{_step_text(step)}"
            f"｜建議模型：{_model_text(step, note)}｜貼 /phase-run"
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
