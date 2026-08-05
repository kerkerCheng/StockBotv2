from __future__ import annotations

from datetime import datetime, timezone
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from engine_c.market_data import build_tradeability_snapshot, get_tradeability_snapshot


def test_tradeability_snapshot_uses_actual_latest_history_timestamp_and_adv20() -> None:
    rows = [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": float(day),
            "volume": float(day * 100),
        }
        for day in range(1, 22)
    ]

    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert result["as_of"] == "2026-07-21T16:00:00+00:00"
    assert result["price"] == 21.0
    assert result["adv20"] == pytest.approx(sum(day * 100 for day in range(2, 22)) / 20)


@pytest.mark.parametrize(
    "rows",
    [
        [{"as_of": "not-a-time", "close": 10.0, "volume": 100.0}],
        [{"as_of": "2026-07-21T16:00:00+00:00", "close": float("nan"), "volume": 1.0}],
        [{"as_of": "2026-07-21T16:00:00+00:00", "close": 10.0, "volume": -1.0}],
    ],
)
def test_tradeability_snapshot_quarantines_invalid_history(rows) -> None:
    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert result["blockers"]


def test_tradeability_snapshot_requires_twenty_unique_sessions() -> None:
    rows = [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": 10.0,
            "volume": 100.0,
        }
        for day in range(1, 20)
    ]
    rows.append(dict(rows[-1]))

    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_history_insufficient_sessions" in result["blockers"]


def _session_rows(days: range, *, close: float = 10.0) -> list[dict]:
    return [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": close,
            "volume": 100.0,
        }
        for day in days
    ]


def test_unsettled_trailing_bar_is_dropped_instead_of_quarantining_the_series() -> None:
    """非美國交易所的當日 bar 常常先開出來、close 還是 NaN。

    2026-08-05 實測：IQE.L／SIVE.ST／2DG.F 同時因為這一根而整份 quarantine，
    等於用 1 根未結算的 bar 廢掉 59 根有效資料；同時間美股沒有這個現象。
    """

    rows = _session_rows(range(1, 22))
    rows.append(
        {"as_of": "2026-07-22T16:00:00+00:00", "close": float("nan"), "volume": 207306.0}
    )

    result = build_tradeability_snapshot(
        ticker="IQE.L",
        currency="GBp",
        rows=rows,
        fetched_at="2026-07-22T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert result["blockers"] == []
    # as_of 停在最後一根「有結算」的 session，不是 provider 回傳的最後一根。
    assert result["as_of"] == "2026-07-21T16:00:00+00:00"
    assert result["unsettled_trailing_rows"] == 1


def test_hole_in_the_middle_of_the_series_still_quarantines() -> None:
    """序列中間缺值是資料錯誤，不是「還太年輕」——fail closed 不放寬。"""

    rows = _session_rows(range(1, 22))
    rows[10] = {
        "as_of": rows[10]["as_of"],
        "close": float("nan"),
        "volume": 100.0,
    }

    result = build_tradeability_snapshot(
        ticker="AXTI",
        currency="USD",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_history_row_invalid" in result["blockers"]


@pytest.mark.parametrize(
    "bad_tail",
    [
        {"as_of": "2026-07-22T16:00:00+00:00", "close": -1.0, "volume": 100.0},
        {"as_of": "2026-07-22T16:00:00+00:00", "close": 10.0, "volume": -5.0},
        {"as_of": "not-a-time", "close": float("nan"), "volume": 100.0},
    ],
)
def test_corrupt_or_unpositionable_tail_row_is_not_treated_as_unsettled(bad_tail) -> None:
    """只有「值缺席」才算未結算；寫出來但超出範圍、或無法定位，一律仍 quarantine。"""

    rows = _session_rows(range(1, 22))
    rows.append(bad_tail)

    result = build_tradeability_snapshot(
        ticker="AXTI",
        currency="USD",
        rows=rows,
        fetched_at="2026-07-22T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_history_row_invalid" in result["blockers"]


def test_dropping_unsettled_rows_still_respects_the_twenty_session_floor() -> None:
    """丟棄未結算 bar 不能變成繞過既有門檻的後門。"""

    rows = _session_rows(range(1, 20))
    rows.append(
        {"as_of": "2026-07-20T16:00:00+00:00", "close": float("nan"), "volume": 1.0}
    )

    result = build_tradeability_snapshot(
        ticker="AXTI",
        currency="USD",
        rows=rows,
        fetched_at="2026-07-20T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_history_insufficient_sessions" in result["blockers"]


def test_settled_row_supersedes_a_duplicate_unsettled_row_for_the_same_session() -> None:
    rows = _session_rows(range(1, 22))
    rows.append(
        {"as_of": "2026-07-21T16:00:00+00:00", "close": float("nan"), "volume": 100.0}
    )

    result = build_tradeability_snapshot(
        ticker="AXTI",
        currency="USD",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert "unsettled_trailing_rows" not in result


def test_execution_symbol_uses_yahoo_alias_but_preserves_canonical_ticker(
    monkeypatch,
) -> None:
    requested = []
    index = pd.date_range("2026-06-01", periods=25, freq="B", tz="Europe/Berlin")
    history = pd.DataFrame({
        "Close": [2.0 + i / 100 for i in range(25)],
        "Volume": [1000 + i for i in range(25)],
    }, index=index)

    class FakeTicker:
        def __init__(self, symbol):
            requested.append(symbol)

        def history(self, **_kwargs):
            return history

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))

    result = get_tradeability_snapshot("FRA:2DG", "EUR")

    assert requested == ["2DG.F"]
    assert result["status"] == "observed"
    assert result["ticker"] == "FRA:2DG"
    assert result["source"] == "yfinance://history/2DG.F"


def test_tradeability_failure_classifies_sandbox_block_as_retryable(monkeypatch) -> None:
    class BlockedTicker:
        def __init__(self, _symbol):
            pass

        def history(self, **_kwargs):
            raise PermissionError("sandbox network permission denied")

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=BlockedTicker))

    result = get_tradeability_snapshot("AXTI", "USD")

    assert result["status"] == "unavailable"
    assert result["failure_class"] == "access_blocked"
