"""複查排程：固定週期與催化劑取較早者。

L7 要求 disproof 條件附核查頻率，但決定「什麼時候會知道答案」的往往是催化劑。
2026-08-13 實測：催化劑寫在 memo 與 lifecycle 的散文 note 裡，卻沒有欄位承載，
於是 next_check 退化成 last_checked + check_interval_days 的機械日曆——AXT 被排到
2026-11-15，而它的裁決點（Q3 財報）在那之前。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from thesis.lifecycle_schedule import (
    CADENCE,
    CATALYST,
    catalyst_checkpoints,
    effective_next_check,
    is_due,
)

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 8, 14)


def _entry(**over):
    base = {
        "status": "active",
        "last_checked": "2026-08-04",
        "next_check": "2026-11-15",
        "check_interval_days": 90,
    }
    base.update(over)
    return base


def test_catalyst_earlier_than_cadence_wins() -> None:
    entry = _entry(
        catalyst_checkpoints=[
            {"date": "2026-10-30", "what": "Q3 財報", "decides": "毛利率", "date_confidence": "estimated"}
        ]
    )
    when, source, checkpoint = effective_next_check(entry, today=TODAY)
    assert when == date(2026, 10, 30)
    assert source == CATALYST
    assert checkpoint["what"] == "Q3 財報"


def test_cadence_wins_when_catalyst_is_later() -> None:
    entry = _entry(
        next_check="2026-10-15",
        catalyst_checkpoints=[{"date": "2026-12-01", "what": "產能倍增檢核"}],
    )
    when, source, _ = effective_next_check(entry, today=TODAY)
    assert when == date(2026, 10, 15)
    assert source == CADENCE


def test_catalyst_already_covered_by_last_check_does_not_reschedule() -> None:
    """已在上次複查之前發生的催化劑不再喚醒——否則每次 sync 都會重新觸發。

    這是 2026-08-12 已記錄過的 reactivation 迴圈形狀（只寫不讀、等待條件永遠黏不住）。
    """
    entry = _entry(
        last_checked="2026-08-04",
        catalyst_checkpoints=[{"date": "2026-07-01", "what": "已過的舊催化劑"}],
    )
    when, source, _ = effective_next_check(entry, today=TODAY)
    assert source == CADENCE, "早於 last_checked 的催化劑不該再排程"


def test_passed_catalyst_after_last_check_is_overdue() -> None:
    """催化劑到了卻沒人去看＝逾期，不因日期在過去就安靜跳過。"""
    entry = _entry(
        last_checked="2026-06-01",
        next_check="2026-12-31",
        catalyst_checkpoints=[
            {"date": "2026-08-01", "what": "Q2 財報", "date_confidence": "confirmed"}
        ],
    )
    due, reason = is_due(entry, today=TODAY)
    assert due is True
    assert "催化劑 2026-08-01" in reason
    assert "（日期為推估）" not in reason, "confirmed 不該標成推估"


def test_estimated_dates_still_schedule_but_are_labelled() -> None:
    """推估日期照樣排程——提早看一次的成本遠低於錯過裁決點——但必須標明。"""
    entry = _entry(
        last_checked="2026-06-01",
        next_check="2026-12-31",
        catalyst_checkpoints=[{"date": "2026-08-01", "what": "推估的財報日"}],
    )
    due, reason = is_due(entry, today=TODAY)
    assert due is True
    assert "（日期為推估）" in reason


def test_review_required_is_always_due() -> None:
    entry = _entry(status="review_required", next_check="2099-01-01")
    due, reason = is_due(entry, today=TODAY)
    assert due is True
    assert reason == "review_required"


def test_unparseable_checkpoints_are_skipped_not_crashing() -> None:
    entry = _entry(catalyst_checkpoints=[{"what": "沒有日期"}, "不是物件", {"date": "not-a-date"}])
    assert catalyst_checkpoints(entry) == []
    when, source, _ = effective_next_check(entry, today=TODAY)
    assert source == CADENCE


def test_real_lifecycle_axt_moves_from_cadence_to_catalyst() -> None:
    """實檔驗收：AXT 的生效複查日必須早於機械算出的 next_check。"""
    data = json.loads((ROOT / "thesis" / "lifecycle.json").read_text(encoding="utf-8"))
    axt = data["axt_inp"]
    when, source, checkpoint = effective_next_check(axt, today=TODAY)
    assert source == CATALYST
    assert when < date.fromisoformat(axt["next_check"])
    assert "Q3" in checkpoint["what"]
    # 推估日期必須帶依據，不得憑空給一個看起來精確的日子。
    assert checkpoint["date_confidence"] == "estimated"
    assert axt["catalyst_checkpoints"][0]["basis"]
