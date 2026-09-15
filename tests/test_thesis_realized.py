"""`realized` 生命週期狀態（2026-09-15 使用者定案）：對了也要有出場觸發，與 disproof 對稱。

守的是三件事：
1. 狀態機：active／watch → realized → retired／revised；realized 不能直接回 active（要經 revised），也不能跳過 review 就消失。
2. 到期：realized 與 review_required 一樣恆視為到期，理由講清楚它不是賣出指令。
3. 進入由人提案（thesis mutation gate）：`target_reached` 只是 read model 的提醒，這裡沒有任何自動轉移。
"""
from __future__ import annotations

from datetime import date

from thesis.lifecycle_schedule import REALIZED, is_due
from thesis.pending_lifecycle import ALLOWED_TRANSITIONS


def test_realized_is_a_reviewed_exit_symmetric_to_disproof() -> None:
    assert "realized" in ALLOWED_TRANSITIONS["active"] and "realized" in ALLOWED_TRANSITIONS["watch"]
    assert ALLOWED_TRANSITIONS["realized"] == ALLOWED_TRANSITIONS["review_required"] == frozenset({"retired", "revised"})
    assert "active" not in ALLOWED_TRANSITIONS["realized"], "兌現後不得不經 review 直接回 active"
    assert "realized" not in ALLOWED_TRANSITIONS["retired"] and "realized" not in ALLOWED_TRANSITIONS["review_required"]


def test_realized_is_always_due_and_says_it_is_not_a_sell_order() -> None:
    due, why = is_due({"status": REALIZED, "next_check": "2099-01-01", "ticker": "X"}, today=date(2026, 9, 15))
    assert due and why.startswith("realized") and "不是自動賣出" in why
    due2, _ = is_due({"status": "active", "next_check": "2099-01-01", "ticker": "X"}, today=date(2026, 9, 15))
    assert not due2


def test_no_module_flips_a_thesis_to_realized_by_itself() -> None:
    """機械提醒（target_reached）與狀態轉移是兩件事：repo 裡不得有程式把 status 寫成 realized。"""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in list((root / "alpha").rglob("*.py")) + list((root / "briefing").rglob("*.py")) + list((root / "webapp").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"""status["']?\s*[:=]\s*["']realized["']""", text):
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], offenders
