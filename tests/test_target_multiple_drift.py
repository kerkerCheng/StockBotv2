"""目標倍數背離偵測必須**攔對東西**（2026-09-19，七缺陷之 6）。

事發：LITE 的假設逐字宣告「零折溢價」，11 天後同一筆假設印出 +9.6% 的倍數差異貢獻，
而沒有任何機制在盯兩者背離。修法是加一個常駐計數器；但這個 gate 本身也要被驗證（L14-2），
而實測 49 筆裡**兩個最大的「背離」都不是背離**：一個是拿 `ev_to_sales` 去跟本益比比，
一個是把 SEK 的股價除以 EUR 的 EPS。**攔錯東西的 gate 不會因為它更嚴格就變得正當**（L15-1）。
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from alpha.providers.valuation_drift import DRIFT_THRESHOLD, live_target_pe_records, scan
from engine_c.db import _ensure_sqlite_schema


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _market(conn: sqlite3.Connection, ticker: str, *, price: float, eps: float,
            period_end: str, currency: str) -> None:
    conn.execute(
        "INSERT INTO financial_snapshots (ticker, snapshot_date, bar_date, price, price_kind, "
        "shares_outstanding, fetched_at) VALUES (?, '2026-09-18', '2026-09-18', ?, 'close', 1000, "
        "'2026-09-18T00:00:00+00:00')", (ticker, price))
    conn.execute(
        "INSERT INTO consensus_estimates (ticker, snapshot_date, metric, period_kind, relative_label, "
        "fiscal_period_end, fiscal_label, estimate_avg, currency, source, fetched_at) "
        "VALUES (?, '2026-09-18', 'eps', 'fiscal_year', '0y', ?, 'FY2026', ?, ?, 'test', "
        "'2026-09-18T00:00:00+00:00')", (ticker, period_end, eps, currency))
    conn.commit()


def _record(tmp_path, ticker: str, **over) -> None:
    payload = {
        "assumption_id": over.pop("assumption_id", f"va_{ticker.lower().replace('.', '_')}"),
        "ticker": ticker, "company_id": "co:test", "parameter": "target_pe",
        "method": "forward_earnings_multiple", "derivation": "calibrated_to_market",
        "value": 40.0, "period_end": "2026-12-31", "retracted": False, "supersedes_id": None,
    }
    payload.update(over)
    with (tmp_path / f"{ticker}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def test_drift_beyond_threshold_is_flagged(tmp_path) -> None:
    conn = _conn()
    _market(conn, "LITE", price=1000.0, eps=20.0, period_end="2026-12-31", currency="USD")
    _record(tmp_path, "LITE", value=40.0)          # 市場 50x，背離 −20%
    row = scan(directory=tmp_path, conn=conn)["rows"][0]
    assert row.status == "drift_exceeds"
    assert row.drift == pytest.approx(-0.2)


def test_within_band_is_not_flagged(tmp_path) -> None:
    conn = _conn()
    _market(conn, "LITE", price=1000.0, eps=20.0, period_end="2026-12-31", currency="USD")
    _record(tmp_path, "LITE", value=51.0)          # 市場 50x，背離 +2%
    row = scan(directory=tmp_path, conn=conn)["rows"][0]
    assert row.status == "within_band" and abs(row.drift) < DRIFT_THRESHOLD


def test_a_different_parameter_is_never_compared_against_a_pe(tmp_path) -> None:
    """SOI.PA 型：生效假設是 `target_ev_to_sales=7.25`，拿去跟 price/eps 比得出 −96.5%。

    ⚠ 那個數字沒有任何意義——**它們不是同一個量**。
    """
    conn = _conn()
    _market(conn, "SOI.PA", price=141.0, eps=0.69156, period_end="2027-03-31", currency="EUR")
    _record(tmp_path, "SOI.PA", parameter="target_ev_to_sales", method="ev_to_sales",
            value=7.25, period_end="2027-03-31")
    result = scan(directory=tmp_path, conn=conn)
    assert result["input"] == 0            # 連進場都不該進——它不是 target_pe
    assert live_target_pe_records(tmp_path) == []


def test_intentional_premium_is_not_woken_up(tmp_path) -> None:
    """`derivation=independent` 的背離是**有意的**（實測 COHR −25.8%、LYC.AX −13.4%）。"""
    conn = _conn()
    _market(conn, "COHR", price=1000.0, eps=20.0, period_end="2026-12-31", currency="USD")
    _record(tmp_path, "COHR", value=25.0, derivation="independent")
    row = scan(directory=tmp_path, conn=conn)["rows"][0]
    assert row.status == "not_applicable" and "independent" in row.reason


def test_currency_mismatch_is_cannot_compare_not_drift(tmp_path) -> None:
    """HEXA-B.ST 型：報價 SEK、共識 EPS 是 EUR。95.56 ÷ 0.31346 ＝ 304.9 **不是本益比**。

    ⚠ 反向同樣重要：6680.HK 報 HKD、共識 CNY，相除後看起來是 +0.9%「幾乎完美校準」
    ——**假的沒問題比假警報更危險**，因為沒有人會去看它。
    """
    conn = _conn()
    _market(conn, "HEXA-B.ST", price=95.56, eps=0.31346, period_end="2026-12-31", currency="EUR")
    _record(tmp_path, "HEXA-B.ST", value=26.6351)
    row = scan(directory=tmp_path, conn=conn)["rows"][0]
    assert row.status == "cannot_compare"
    assert "SEK" in row.reason and "EUR" in row.reason
    assert row.drift is None               # 不得給一個數字——那會被讀成「量過了」


def test_minor_unit_quote_is_cannot_compare(tmp_path) -> None:
    """IQE.L 報 GBp、EPS 是 GBP——差 100 倍。缺陷 7 讓單位跟著資料走，這裡是第一個消費者。"""
    conn = _conn()
    _market(conn, "IQE.L", price=42.70, eps=0.02, period_end="2026-12-31", currency="GBP")
    _record(tmp_path, "IQE.L", value=30.0)
    row = scan(directory=tmp_path, conn=conn)["rows"][0]
    assert row.status == "cannot_compare" and "GBp" in row.reason


def test_superseded_and_retracted_records_do_not_count(tmp_path) -> None:
    conn = _conn()
    _market(conn, "LITE", price=1000.0, eps=20.0, period_end="2026-12-31", currency="USD")
    _record(tmp_path, "LITE", assumption_id="va_old", value=10.0)
    _record(tmp_path, "LITE", assumption_id="va_new", value=51.0, supersedes_id="va_old")
    _record(tmp_path, "LITE", assumption_id="va_dead", value=99.0, retracted=True)
    result = scan(directory=tmp_path, conn=conn)
    assert result["input"] == 1 and result["rows"][0].target == 51.0


def test_counts_cover_every_status_so_nothing_is_silently_dropped(tmp_path) -> None:
    conn = _conn()
    _market(conn, "LITE", price=1000.0, eps=20.0, period_end="2026-12-31", currency="USD")
    _record(tmp_path, "LITE", value=40.0)
    result = scan(directory=tmp_path, conn=conn)
    assert sum(result["counts"].values()) == result["input"]      # INV-3
    assert set(result["counts"]) == set(result["status_labels"])
