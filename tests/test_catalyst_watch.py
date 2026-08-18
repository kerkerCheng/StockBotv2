"""賣出側每日檢查：條件檢查而非訊號，所以判準必須是確定性的。"""
from __future__ import annotations

from datetime import date, timedelta

from decision_lab.catalyst_watch import DUE_SOON_DAYS, assess_entry, render_markdown

TODAY = date(2026, 8, 18)


def _entry(**kw):
    base = {
        "company_id": "co:axt",
        "ticker": "AXTI",
        "catalyst": "Q3 10-Q",
        "disproof": "毛利率跌破 30%",
        "expiry": "2026-11-24T00:00:00+00:00",
    }
    base.update(kw)
    return base


def test_missing_disproof_is_config_broken_not_merely_watch() -> None:
    """L7：欄位有填但沒有流程，等於貼了永遠不會響的火警警報。

    空的 disproof 不得只是「監控中」——那會讓一個沒有內容的鬧鐘看起來正常。
    """
    result = assess_entry(_entry(disproof=""), today=TODAY)
    assert result["state"] == "config_broken"
    assert any("disproof" in p for p in result["problems"])


def test_missing_catalyst_flags_the_expiry_as_meaningless() -> None:
    result = assess_entry(_entry(catalyst=""), today=TODAY)
    assert result["state"] == "config_broken"
    assert any("鬧鐘" in p for p in result["problems"])


def test_expiry_earlier_than_catalyst_is_config_broken() -> None:
    """`expiry` 早於催化劑保證產生一次假到期——催化劑不可能在有效期內發生。"""
    result = assess_entry(
        _entry(expiry="2026-11-30T00:00:00+00:00"),
        today=TODAY,
        checkpoints=[{"date": "2026-12-01", "date_confidence": "estimated"}],
    )
    assert result["state"] == "config_broken"
    assert any("早於最近的催化劑" in p for p in result["problems"])
    # 順序正確就不該報。
    ok = assess_entry(
        _entry(expiry="2026-12-15T00:00:00+00:00"),
        today=TODAY,
        checkpoints=[{"date": "2026-12-01", "date_confidence": "confirmed"}],
    )
    assert ok["state"] == "watch"


def test_expired_and_due_soon_are_distinct_states() -> None:
    expired = assess_entry(_entry(expiry="2026-08-18T00:00:00+00:00"), today=TODAY)
    assert expired["state"] == "expired"
    assert expired["days_to_expiry"] == 0

    # ⚠ 用真的日期運算，不要用字串拼месяц——`f"2026-08-{18+14}"` 會拼出不存在的
    # 08-32，被 `_as_date` 判成無法解析 → config_broken，測試會以為程式壞了。
    edge = TODAY + timedelta(days=DUE_SOON_DAYS)
    soon = assess_entry(_entry(expiry=f"{edge.isoformat()}T00:00:00+00:00"), today=TODAY)
    assert soon["state"] == "due_soon"

    beyond = TODAY + timedelta(days=DUE_SOON_DAYS + 1)
    later = assess_entry(_entry(expiry=f"{beyond.isoformat()}T00:00:00+00:00"), today=TODAY)
    assert later["state"] == "watch"


def test_config_broken_outranks_expired_in_the_report() -> None:
    """設定壞掉的項目排在最前面：它的到期提醒本身就是假的，先修它才有意義。"""
    rows = [
        assess_entry(_entry(ticker="A", expiry="2026-08-01T00:00:00+00:00"), today=TODAY),
        assess_entry(_entry(ticker="B", disproof=""), today=TODAY),
    ]
    text = "\n".join(render_markdown(sorted(rows, key=lambda r: r["state"] != "config_broken")))
    assert "設定不完整" in text
    assert text.index("| B |") < text.index("| A |")


def test_prose_dates_are_never_parsed_into_checkpoints() -> None:
    """散文裡的日期不猜（L15：語意可交給語言處理，狀態必須 deterministic）。

    catalyst 寫著「預計 2026 年 11 月初」但沒有結構化 checkpoint 時，
    `next_catalyst` 必須是 None——不得從散文推一個看起來很像的日期出來。
    """
    result = assess_entry(
        _entry(catalyst="AXT 2026 Q3 10-Q（預計 2026 年 11 月初）"), today=TODAY
    )
    assert result["next_catalyst"] is None
    assert result["state"] == "watch"
