"""NAV 比例呈現：純數字，零門檻。

這是「反向監控」——系統終點是瓶頸排序，不給額度；NAV 呈現只回答「我現在持有什麼、
各佔多少」，失衡與否由使用者自己看數字判斷。因此本模組**不得**產生任何門檻、警示或
建議欄位（R13）；那正是本次重構要從系統終點移除的東西。
"""
from __future__ import annotations

import pytest

from decision_lab.nav_exposure import build_nav_exposure

NAV = 1000.0


def _row(symbol, bucket, value, **extra):
    row = {
        "symbol": symbol,
        "ticker": symbol,
        "bucket": bucket,
        "market_value_base": value,
        "nav_base": NAV,
        "base_currency": "USD",
    }
    row.update(extra)
    return row


ROWS = [
    _row("COHR", "CORE", 300.0),
    _row("LITE", "CORE", 200.0),
    _row("QQQ", "大盤", 250.0),
    _row("USD", "CASH", 250.0),
]


def test_positions_and_cash_sum_to_one() -> None:
    """分母正確性：非現金部位佔比加上現金佔比等於 1.0。

    ⚠ 這兩者刻意分開：現金**計入 NAV 分母**（它是你的錢），但**不是標的曝險**
    （它沒有 issuer 風險）。把兩者混在同一個清單裡會讓「最大部位是誰」這個問題
    在有大額現金時給出誤導答案。
    """
    result = build_nav_exposure(ROWS)

    total = sum(p["nav_pct"] for p in result["positions"]) + result["cash_pct"]
    assert total == pytest.approx(1.0)


def test_cash_is_excluded_from_positions_and_order_is_by_weight() -> None:
    """現金不進 positions；其餘依佔比降序——最大部位在最上面。

    排序是這份輸出的重點：它唯一的用途是讓人一眼看出失衡，而失衡永遠是從最大的
    那一筆開始看。ROWS 的原始順序是 COHR/LITE/QQQ，佔比是 0.30/0.20/0.25。
    """
    result = build_nav_exposure(ROWS)

    assert [p["ticker"] for p in result["positions"]] == ["COHR", "QQQ", "LITE"]
    assert result["cash_pct"] == pytest.approx(0.25)


def test_position_percentages_are_relative_to_nav_base() -> None:
    result = build_nav_exposure(ROWS)
    by_ticker = {p["ticker"]: p["nav_pct"] for p in result["positions"]}

    assert by_ticker["COHR"] == pytest.approx(0.30)
    assert by_ticker["LITE"] == pytest.approx(0.20)


def test_bucket_distribution_covers_every_row_including_cash() -> None:
    """bucket 分布是全景，含 CASH——它回答「錢分布在哪些籃子」。"""
    result = build_nav_exposure(ROWS)

    assert result["buckets"]["CORE"] == pytest.approx(0.50)
    assert result["buckets"]["大盤"] == pytest.approx(0.25)
    assert result["buckets"]["CASH"] == pytest.approx(0.25)
    assert sum(result["buckets"].values()) == pytest.approx(1.0)


def test_missing_bucket_becomes_unclassified_not_dropped() -> None:
    """bucket 缺漏不得讓該列消失——那會讓分母悄悄變小。"""
    rows = ROWS + [_row("MYSTERY", None, 0.0)]
    result = build_nav_exposure(rows)

    assert "未分類" in result["buckets"]
    assert any(p["ticker"] == "MYSTERY" for p in result["positions"])


def test_unavailable_holdings_propagate_failure_not_zero_exposure() -> None:
    """holdings 取得失敗時不得回空結果假裝零曝險。

    上游的 failure marker（本日新增於 adapters.current_holdings）要一路帶到這裡，
    否則使用者看到的是「你什麼都沒持有」而不是「持股讀不到」。
    """
    result = build_nav_exposure(
        None,
        upstream={"status": "unavailable", "blockers": ["holdings_unavailable"], "failure": "TimeoutError"},
    )

    assert result["status"] == "unavailable"
    assert result["positions"] == []
    assert result["failure"] == "TimeoutError"
    assert "holdings_unavailable" in result["blockers"]


def test_correlation_groups_fall_back_to_ungrouped() -> None:
    """取不到圖鏈路時標「未分組」，不猜測。"""
    result = build_nav_exposure(ROWS, groups={"COHR": "AI 光互連"})

    assert result["groups"]["AI 光互連"] == pytest.approx(0.30)
    assert result["groups"]["未分組"] == pytest.approx(0.45)


def test_output_carries_no_threshold_or_warning_fields() -> None:
    """R13 零門檻：這個模組是呈現，不是閘門。

    禁止 cap／limit／warning／breach／threshold 等欄位——系統終點已經不給額度，
    NAV 呈現若偷偷長出門檻，等於讓資本語意從另一個門回來（KTD5）。
    """
    result = build_nav_exposure(ROWS)

    rendered = repr(result).lower()
    for forbidden in ("cap", "limit", "warning", "breach", "threshold", "supported_range"):
        assert forbidden not in rendered
