"""Phase 7 批次二 E10（failure log #64；使用者 2026-10-21 Q4 A）：覆蓋家數取 EPS 0y、營收 0y、目標價三者最大，門檻 12 照舊。

守：①三者取最大（10-16 XPEV：EPS 0y 3、營收 0y 25、目標價 25 → 25，非邊緣）；②家數 0 而估值也是 0 的空殼列當缺值（3163.TWO 等 6 檔
不得由「無法量」變「邊緣」）；③三個都沒有＝無法量；④三個數與各自來源跟著邊緣判定走到候選板。
"""
from __future__ import annotations

import sqlite3

import pytest

from alpha.edge import edge_state
from alpha.providers import market_normalization as mn

TH = {"market_cap_max_usd": 1e10, "analyst_count_max": 12}


def _conn() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _estimate(conn, ticker, metric, count, avg=1.0, day="2026-10-21"):
    conn.execute("INSERT INTO consensus_estimates (ticker, snapshot_date, bar_date, metric, period_kind, relative_label, "
                 "fiscal_period_end, fiscal_label, estimate_avg, analyst_count, source, fetched_at) "
                 "VALUES (?, ?, ?, ?, 'fiscal_year', '0y', '2026-12-31', 'FY2026', ?, ?, 'test', ?)",
                 (ticker, day, day, metric, avg, count, day))


def _target(conn, ticker, count, mean=10.0, day="2026-10-21"):
    conn.execute("INSERT INTO financial_snapshots (ticker, snapshot_date, analyst_target_count, analyst_target_mean, "
                 "fetched_at) VALUES (?, ?, ?, ?, ?)", (ticker, day, count, mean, day))


def test_coverage_is_the_largest_of_the_three_sources() -> None:
    conn = _conn()
    _estimate(conn, "XPEV", "eps", 3)
    _estimate(conn, "XPEV", "revenue", 25)
    _target(conn, "XPEV", 24)
    assert mn.coverage_counts("XPEV", conn) == {"eps_0y": 3, "revenue_0y": 25, "target_price": 24}
    assert mn.analyst_count("XPEV", conn) == 25
    assert edge_state(market_cap_usd=5e9, analyst_count=25, thresholds=TH)["state"] == "not_edge"


def test_a_zero_count_with_a_zero_estimate_is_a_placeholder_not_zero_coverage() -> None:
    """2026-10-21 實測：營收 0y 的 avg／low／high 全 0.0、家數 0——provider 的空殼列，不是「零位分析師」（L11-5）。"""
    conn = _conn()
    _estimate(conn, "3163.TWO", "revenue", 0, avg=0.0)
    assert mn.coverage_counts("3163.TWO", conn) == {"eps_0y": None, "revenue_0y": None, "target_price": None}
    assert mn.analyst_count("3163.TWO", conn) is None
    assert edge_state(market_cap_usd=5e8, analyst_count=None, thresholds=TH)["state"] == "unmeasurable"


def test_the_three_counts_travel_with_the_edge_state(monkeypatch) -> None:
    from alpha.providers import edge

    monkeypatch.setattr(mn, "screen_inputs", lambda tickers, db_path=None: {
        "SOI.PA": {"market_cap_usd": 5.8e9, "analyst_count": 19,
                   "coverage_counts": {"eps_0y": 6, "revenue_0y": 16, "target_price": 19}}})
    got = edge.edge_states(["SOI.PA"], thresholds=TH)["SOI.PA"]
    assert got["state"] == "not_edge"
    assert [(c["source"], c["count"]) for c in got["coverage_counts"]] == [
        ("eps_0y", 6), ("revenue_0y", 16), ("target_price", 19)]
    assert all(c["label"] for c in got["coverage_counts"])
