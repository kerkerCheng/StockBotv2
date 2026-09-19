"""`MarketSnapshot` 的報價單位必須**跟著市值走**（2026-09-19，七缺陷之 7）。

事發：packet 的 `deterministic.market.market_cap` 是裸數字、`currency` 恆為 `None`
（實測 16/16 從未被賦值），於是 IQE.L 的 56.8B（**GBp**）與 LITE 的 83.5B（USD）
並排比較。IQE.L 真實市值只有約 0.57B GBP——**任何「市值上限 10B」的門檻都會把本籃子裡
最像「邊緣小公司」的那一檔當成超大型股擋掉**，而那正是 D11 最想找的那一類。

判準：`identity/registry.py` 早就把 `market_currency` 拆成報價單位與 ISO 結算幣別兩個欄位
（L12 先分開再各自定規則）；缺的不是分類，是**把分類帶到 packet 上**（L16）。
"""
from __future__ import annotations

import sqlite3

import pytest

from alpha.contracts import MarketSnapshot
from alpha.identity import Ticker
from alpha.providers.fundamentals import EngineCFundamentalsProvider
from engine_c.db import _ensure_sqlite_schema


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _snapshot(conn: sqlite3.Connection, ticker: str, *, price: float, shares: float) -> None:
    conn.execute(
        "INSERT INTO financial_snapshots (ticker, snapshot_date, bar_date, price, price_kind, "
        "shares_outstanding, fetched_at) VALUES (?, '2026-09-18', '2026-09-18', ?, 'close', ?, "
        "'2026-09-18T00:00:00+00:00')",
        (ticker, price, shares),
    )
    conn.commit()


def test_minor_unit_ticker_carries_its_quote_unit_and_is_not_converted() -> None:
    """IQE.L 報 GBp：單位要說出來，**值不換算**（換算需要 FX，那是比較層的事）。"""
    conn = _conn()
    _snapshot(conn, "IQE.L", price=42.70, shares=1_331_090_000)
    market, _ = EngineCFundamentalsProvider(conn=conn).market(Ticker("IQE.L"))
    assert market.quote_unit == "GBp"                    # 報價單位（minor unit）
    assert market.settlement_currency == "GBP"           # ISO-4217 結算幣別
    assert market.market_cap == pytest.approx(42.70 * 1_331_090_000)
    assert market.market_cap_absence_reason is None
    # 兩者不得被壓成同一個字串——那正是 2026-08-05 讓 LSE 行情永遠 quarantine 的形狀。
    assert market.quote_unit != market.settlement_currency


def test_usd_ticker_gets_a_unit_too_so_downstream_never_has_to_assume() -> None:
    conn = _conn()
    _snapshot(conn, "AXTI", price=70.03, shares=65_573_000)
    market, _ = EngineCFundamentalsProvider(conn=conn).market(Ticker("AXTI"))
    assert market.quote_unit == "USD" and market.settlement_currency == "USD"
    assert market.market_cap_absence_reason is None


def test_unresolvable_ticker_refuses_to_output_market_cap() -> None:
    """fail closed：不知道單位就不給數字，理由和股數那側對稱（缺席不是 0，是拒答）。"""
    conn = _conn()
    _snapshot(conn, "ZZZZ.XX", price=100.0, shares=1_000_000)
    market, _ = EngineCFundamentalsProvider(conn=conn).market(Ticker("ZZZZ.XX"))
    assert market.market_cap is None
    assert market.market_cap_absence_reason is not None
    assert "company_id" in market.market_cap_absence_reason
    assert market.price == 100.0            # 價格本身仍照給——缺的是「可跨標的比較的市值」


def test_the_one_representation_two_meanings_field_is_gone() -> None:
    """舊的 `currency` 欄位不得回來：它同時被讀成報價單位與結算幣別（L12）。"""
    assert not hasattr(MarketSnapshot(), "currency")
    assert hasattr(MarketSnapshot(), "quote_unit")
    assert hasattr(MarketSnapshot(), "settlement_currency")
