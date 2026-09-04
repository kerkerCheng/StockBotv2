"""Phase 6：排序前段 vs 後段的等權報酬。

全部用注入的價格序列測，不連 Neo4j 也不連 yfinance。

⚠ 這裡守的不是「數字算對」——那太容易。守的是**三種會讓結果變好看的偏差**：
往前補價格（看到未來）、靜默丟掉缺價的標的、以及讓一檔極端值決定結論而不現形。
"""
from __future__ import annotations

from datetime import date

from alpha.backtest import (
    MIN_TICKERS_FOR_SPLIT, equal_weight_return, evaluate_epoch, summarise_epochs,
)

START = date(2026, 3, 1)
END = date(2026, 5, 30)


def _series(*pairs) -> list[dict]:
    return [{"session_date": day, "close": close} for day, close in pairs]


def _prices(**kwargs) -> dict:
    return {ticker: _series(*pairs) for ticker, pairs in kwargs.items()}


def test_equal_weight_is_the_mean_not_a_weighted_sum() -> None:
    """系統不給部位尺寸，所以基準是等權（`AGENTS.md` Alpha 呈現契約）。"""
    prices = _prices(
        AAA=(("2026-03-01", 100.0), ("2026-05-30", 120.0)),   # +20%
        BBB=(("2026-03-01", 10.0), ("2026-05-30", 11.0)),     # +10%（市值小得多）
    )
    got, missing = equal_weight_return(["AAA", "BBB"], prices, start=START, end=END)
    assert missing == ()
    assert round(got, 6) == 0.15


def test_prices_are_never_carried_forward_from_the_future() -> None:
    """只往回找最近一個收盤，**永遠不往前補**。

    往前補一天就是拿未來的價格當進場價。空跑檢查：把 `_price_on_or_before`
    改成「找不到就取之後最近的」→ 這條會紅（會算出 +20% 而不是缺價）。
    """
    prices = _prices(AAA=(("2026-03-05", 100.0), ("2026-05-30", 120.0)))
    got, missing = equal_weight_return(["AAA"], prices, start=START, end=END)
    assert got is None, "3/1 之前沒有收盤就是沒有進場價，不得用 3/5 的價格頂替"
    assert missing == ("AAA",)


def test_a_stale_price_before_the_start_is_usable() -> None:
    """往回找是正確的——停牌／連假時最近一個收盤就是當時的價。"""
    prices = _prices(AAA=(("2026-02-26", 100.0), ("2026-05-28", 110.0)))
    got, _ = equal_weight_return(["AAA"], prices, start=START, end=END)
    assert round(got, 6) == 0.1


def test_missing_prices_are_named_not_silently_dropped() -> None:
    """「排序沒用」與「資料缺一半」不得同形（L13）。"""
    prices = _prices(AAA=(("2026-03-01", 100.0), ("2026-05-30", 120.0)))
    got, missing = equal_weight_return(["AAA", "GHOST"], prices, start=START, end=END)
    assert round(got, 6) == 0.2
    assert missing == ("GHOST",)


def test_no_data_is_none_not_zero() -> None:
    """「沒資料」與「持平」是兩件事（L12）。"""
    got, missing = equal_weight_return(["GHOST"], {}, start=START, end=END)
    assert got is None
    assert missing == ("GHOST",)


# ---------------------------------------------------------------------------
# 切前後段
# ---------------------------------------------------------------------------

def _six_names() -> dict:
    return _prices(
        A=(("2026-03-01", 100.0), ("2026-05-30", 130.0)),    # +30
        B=(("2026-03-01", 100.0), ("2026-05-30", 120.0)),    # +20
        C=(("2026-03-01", 100.0), ("2026-05-30", 110.0)),    # +10
        D=(("2026-03-01", 100.0), ("2026-05-30", 105.0)),    # +5
        E=(("2026-03-01", 100.0), ("2026-05-30", 100.0)),    # 0
        F=(("2026-03-01", 100.0), ("2026-05-30", 95.0)),     # -5
    )


def test_top_and_bottom_halves_split_the_priced_universe() -> None:
    result = evaluate_epoch(as_of=START, horizon_end=END,
                            ranked=["A", "B", "C", "D", "E", "F"],
                            prices=_six_names())
    assert result.top == ("A", "B", "C")
    assert result.bottom == ("D", "E", "F")
    assert round(result.top_return, 6) == 0.2
    assert round(result.bottom_return, 6) == 0.0
    assert round(result.spread, 6) == 0.2


def test_unpriced_names_are_removed_before_the_split_not_after() -> None:
    """⚠ 先切再剔會讓兩段檔數不對稱——實測缺價的多半是非美股，
    而它們在排序裡不是均勻分布的。

    空跑檢查：把 `evaluate_epoch` 改成先切半再剔除 → 這條會紅。
    """
    result = evaluate_epoch(as_of=START, horizon_end=END,
                            ranked=["A", "GHOST1", "B", "C", "GHOST2", "D"],
                            prices=_six_names())
    assert result.top == ("A", "B")
    assert result.bottom == ("C", "D")
    assert set(result.missing_price) == {"GHOST1", "GHOST2"}


def test_too_few_priced_names_is_skipped_with_a_reason() -> None:
    """前後段各不到 2 檔就是在比個股，不是在檢定排序。"""
    result = evaluate_epoch(as_of=START, horizon_end=END, ranked=["A", "B", "C"],
                            prices=_six_names())
    assert result.spread is None
    assert result.usable is False
    assert str(MIN_TICKERS_FOR_SPLIT) in result.skipped_reason


def test_duplicate_tickers_collapse_to_the_best_rank() -> None:
    """同一家公司可能有多條瓶頸邊；它在前段只算一次。"""
    result = evaluate_epoch(as_of=START, horizon_end=END,
                            ranked=["A", "B", "A", "C", "D"], prices=_six_names())
    assert result.ranked == ("A", "B", "C", "D")
    assert result.top == ("A", "B")


# ---------------------------------------------------------------------------
# 讓極端值現形（而不是剔除它）
# ---------------------------------------------------------------------------

def test_the_dominant_name_is_surfaced_not_removed() -> None:
    """實測 2026-03-01 那期 `SOI.PA` +334% 一檔撐起 +97.8% 的價差。

    剔除離群值會讓結果更好看；現形才讓讀的人知道結論其實由誰決定。
    空跑檢查：拿掉 `dominant_name` → 這條會紅。
    """
    prices = _prices(
        A=(("2026-03-01", 100.0), ("2026-05-30", 434.0)),    # +334%
        B=(("2026-03-01", 100.0), ("2026-05-30", 110.0)),
        C=(("2026-03-01", 100.0), ("2026-05-30", 112.0)),
        D=(("2026-03-01", 100.0), ("2026-05-30", 121.0)),
    )
    result = evaluate_epoch(as_of=START, horizon_end=END,
                            ranked=["A", "B", "C", "D"], prices=prices)
    assert result.spread > 0
    name, excess = result.dominant_name
    assert name == "A"
    assert excess > 2.0
    assert dict(result.contributions)["A"] == 3.34


# ---------------------------------------------------------------------------
# 跨期彙總：刻意不算 t 統計量與勝率
# ---------------------------------------------------------------------------

def test_summary_reports_epochs_and_refuses_to_compute_a_win_rate() -> None:
    """期數個位數時，勝率與 t 統計量都是噪音，但看起來像證據。"""
    results = [
        evaluate_epoch(as_of=START, horizon_end=END,
                       ranked=["A", "B", "C", "D"], prices=_six_names()),
        evaluate_epoch(as_of=START, horizon_end=END, ranked=["A", "B"],
                       prices=_six_names()),
    ]
    summary = summarise_epochs(results)

    assert summary["epochs_requested"] == 2
    assert summary["epochs_usable"] == 1
    assert len(summary["skipped"]) == 1
    assert "不是回測勝率" in summary["_interpretation"]
    assert not any("win_rate" in k or "t_stat" in k for k in summary)


def test_skipped_epochs_are_listed_with_reasons() -> None:
    """略過的期數必須說得出理由，否則「沒跑」與「跑了沒結果」同形。"""
    summary = summarise_epochs([
        evaluate_epoch(as_of=START, horizon_end=END, ranked=["A"],
                       prices=_six_names()),
    ])
    assert summary["epochs_usable"] == 0
    assert summary["mean_spread"] is None
    assert summary["skipped"][0]["as_of"] == START.isoformat()
