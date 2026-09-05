"""Engine C 的會計年度別共識（`consensus_estimates`）與兩個 mechanical 欄位的讀取端。

守三件事：
1. **身分在抓取當下解析**：`0y`／`+1y` 是相對標籤，寫進表的是 `fiscal_period_end`。
2. **缺料是沒有列，不是 0**：估計值取不到、會計行事曆解不出來，都不寫。
3. **PIT**：provider 讀取只回 as-of 之前最新一次抓取；ledger 觀測依 `recorded_at`／`as_of` 過濾。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.identity import Ticker
from alpha.providers.fundamentals import EngineCFundamentalsProvider
from engine_c.db import CONSENSUS_ESTIMATE_COLUMNS, _ensure_sqlite_schema, upsert_consensus_estimate
from engine_c.etl_yfinance import _fiscal_estimates
from engine_c.manual_observations import append_manual_observation
from shared.fiscal import add_years, epoch_to_date, fiscal_label, resolve_fiscal_year_end

ROOT = Path(__file__).resolve().parent.parent
LAST = date(2026, 6, 30)
NEXT = date(2027, 6, 30)


# ---------------------------------------------------------------------------
# 1. 會計行事曆解析
# ---------------------------------------------------------------------------

def test_relative_labels_resolve_to_absolute_fiscal_year_ends() -> None:
    assert resolve_fiscal_year_end("0y", last_fiscal_year_end=LAST, next_fiscal_year_end=NEXT) == NEXT
    assert resolve_fiscal_year_end("+1y", last_fiscal_year_end=LAST, next_fiscal_year_end=NEXT) == date(2028, 6, 30)
    assert fiscal_label(NEXT) == "FY2027"


@pytest.mark.parametrize("label,last,nxt", [
    ("0y", None, NEXT),                          # 缺一個日期
    ("0y", LAST, None),
    ("0y", LAST, date(2026, 12, 31)),            # 兩者相距不像一年
    ("0y", LAST, date(2029, 6, 30)),
    ("+2y", LAST, NEXT),                         # 未登記的標籤
    ("0q", LAST, NEXT),                          # v1 不做季度
])
def test_unresolvable_calendar_is_none_not_a_guess(label, last, nxt) -> None:
    assert resolve_fiscal_year_end(label, last_fiscal_year_end=last, next_fiscal_year_end=nxt) is None


def test_add_years_and_epoch_helpers() -> None:
    assert add_years(date(2024, 2, 29), 1) == date(2025, 2, 28)
    assert epoch_to_date(1782777600) == date(2026, 6, 30)
    assert epoch_to_date(None) is None and epoch_to_date(True) is None and epoch_to_date("x") is None


# ---------------------------------------------------------------------------
# 2. ETL 投影
# ---------------------------------------------------------------------------

class _Row(dict):
    def get(self, key, default=None):  # pandas Series 相容
        return super().get(key, default)


class _Frame:
    def __init__(self, rows: dict[str, dict]):
        self._rows = {k: _Row(v) for k, v in rows.items()}
        self.index = tuple(rows)

    @property
    def loc(self):
        return self._rows


class _TickerObj:
    def __init__(self, earnings=None, revenue=None, fail: bool = False):
        self._earnings, self._revenue, self._fail = earnings, revenue, fail

    @property
    def earnings_estimate(self):
        if self._fail:
            raise RuntimeError("provider down")
        return self._earnings

    @property
    def revenue_estimate(self):
        return self._revenue


INFO = {"lastFiscalYearEnd": 1782777600, "nextFiscalYearEnd": 1814313600}   # 2026-06-30／2027-06-30
FETCHED = datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc)


def _rows(ticker_obj, info=INFO):
    return _fiscal_estimates(ticker_obj, info, "COHR", snapshot_date=date(2026, 9, 5),
                             bar_date="2026-09-04", fetched_at=FETCHED)


def test_etl_projects_fy_identified_rows_for_both_metrics() -> None:
    earnings = _Frame({"0q": {"avg": 1.96}, "0y": {"avg": 9.41634, "low": 8.26, "high": 10.26,
                                                   "numberOfAnalysts": 22, "yearAgoEps": 5.61,
                                                   "growth": 0.6785, "currency": "USD"},
                       "+1y": {"avg": 13.955, "numberOfAnalysts": 19, "yearAgoEps": 9.41634}})
    revenue = _Frame({"0y": {"avg": 10_618_193_080, "numberOfAnalysts": 21, "yearAgoRevenue": 7_118_200_000,
                             "currency": "USD"}})
    rows = _rows(_TickerObj(earnings, revenue))
    keyed = {(r["metric"], r["relative_label"]): r for r in rows}
    assert set(keyed) == {("eps", "0y"), ("eps", "+1y"), ("revenue", "0y")}
    assert keyed[("eps", "0y")]["fiscal_period_end"] == "2027-06-30"
    assert keyed[("eps", "0y")]["fiscal_label"] == "FY2027"
    assert keyed[("eps", "+1y")]["fiscal_period_end"] == "2028-06-30"
    assert keyed[("eps", "0y")]["year_ago_actual"] == 5.61 and keyed[("eps", "0y")]["analyst_count"] == 22
    assert keyed[("revenue", "0y")]["year_ago_actual"] == 7_118_200_000
    assert all(set(CONSENSUS_ESTIMATE_COLUMNS) <= set(r) for r in rows)
    assert all(r["source"].startswith("yfinance.") for r in rows)


def test_missing_estimate_writes_no_row_not_zero() -> None:
    """估計值缺、行事曆解不出來、provider 失敗——三種都是「沒有列」，不是一列 0（L12）。"""
    no_avg = _Frame({"0y": {"avg": None, "numberOfAnalysts": 3}})
    assert _rows(_TickerObj(no_avg, None)) == []
    good = _Frame({"0y": {"avg": 9.4}})
    assert _rows(_TickerObj(good, None), info={}) == []                 # 沒有會計行事曆
    assert _rows(_TickerObj(None, None, fail=True)) == []               # provider 失敗
    assert _rows(_TickerObj(None, None)) == []                          # frame 為 None
    rows = _rows(_TickerObj(good, None))
    assert len(rows) == 1 and rows[0]["estimate_avg"] == 9.4
    assert all(r["estimate_avg"] != 0.0 for r in rows)


# ---------------------------------------------------------------------------
# 3. 表的寫入與 provider 讀取（真 SQLite，暫存）
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _row(**over) -> dict:
    base = dict(ticker="COHR", snapshot_date="2026-09-05", bar_date="2026-09-04", metric="eps",
                period_kind="fiscal_year", relative_label="0y", fiscal_period_end="2027-06-30",
                fiscal_label="FY2027", estimate_avg=9.41634, estimate_low=8.26, estimate_high=10.26,
                analyst_count=22, year_ago_actual=5.61, growth=0.6785, currency="USD",
                source="yfinance.earnings_estimate", fetched_at=FETCHED)
    base.update(over)
    return base


def test_upsert_is_idempotent_and_validates_identity() -> None:
    conn = _conn()
    upsert_consensus_estimate(conn, _row())
    upsert_consensus_estimate(conn, _row(estimate_avg=9.5))            # 同鍵 → 更新不重複
    rows = conn.execute("SELECT estimate_avg FROM consensus_estimates").fetchall()
    assert len(rows) == 1 and rows[0][0] == 9.5
    with pytest.raises(ValueError, match="missing keys"):
        upsert_consensus_estimate(conn, _row(fiscal_period_end=None))
    with pytest.raises(ValueError, match="eps or revenue"):
        upsert_consensus_estimate(conn, _row(metric="ebitda"))
    with pytest.raises(ValueError, match="fiscal_year"):
        upsert_consensus_estimate(conn, _row(period_kind="fiscal_quarter"))
    with pytest.raises(ValueError, match="analyst_count"):
        upsert_consensus_estimate(conn, _row(analyst_count=-1))


def test_provider_reads_latest_capture_and_respects_as_of() -> None:
    conn = _conn()
    upsert_consensus_estimate(conn, _row(snapshot_date="2026-08-20", bar_date="2026-08-19", estimate_avg=8.3))
    upsert_consensus_estimate(conn, _row())
    upsert_consensus_estimate(conn, _row(metric="revenue", source="yfinance.revenue_estimate",
                                         estimate_avg=10_618_193_080.0, year_ago_actual=7_118_200_000.0))
    upsert_consensus_estimate(conn, _row(relative_label="+1y", fiscal_period_end="2028-06-30",
                                         fiscal_label="FY2028", estimate_avg=13.955, year_ago_actual=9.41634))
    provider = EngineCFundamentalsProvider(conn=conn)
    current, reason = provider.fiscal_consensus(Ticker("COHR"))
    assert reason is None and len(current) == 3                       # 只回最新一次抓取
    eps = next(c for c in current if c.metric == "eps" and c.period.end == date(2027, 6, 30))
    assert eps.value == 9.41634 and eps.year_ago_actual == 5.61 and eps.captured_at == date(2026, 9, 4)
    assert eps.evidence[0].ref == "engine_c://consensus_estimate/COHR/eps/2027-06-30"
    assert eps.evidence[0].published_at == date(2026, 9, 4)
    earlier, _ = provider.fiscal_consensus(Ticker("COHR"), as_of=date(2026, 8, 25))
    assert len(earlier) == 1 and earlier[0].value == 8.3                # as-of 之前那次抓取
    none, reason = provider.fiscal_consensus(Ticker("COHR"), as_of=date(2026, 8, 1))
    assert none == () and "截至 2026-08-01" in reason
    missing, reason = provider.fiscal_consensus(Ticker("NOPE"))
    assert missing == () and "尚無列" in reason
    assert provider.fiscal_consensus(None)[0] == ()


def test_schema_and_migration_agree_on_the_table() -> None:
    db_py = (ROOT / "engine_c" / "db.py").read_text(encoding="utf-8")
    migration = (ROOT / "engine_c" / "migrations" / "20260905_add_consensus_estimates.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS consensus_estimates" in db_py
    assert "CREATE TABLE IF NOT EXISTS consensus_estimates" in migration
    for column in CONSENSUS_ESTIMATE_COLUMNS:
        assert column in migration, column
        assert db_py.count(column) >= 3, column                          # DDL ＋ 兩種方言的 INSERT
    from engine_c.migrate import REQUIRED_MIGRATIONS, REQUIRED_TABLES

    assert "20260905_add_consensus_estimates.sql" in REQUIRED_MIGRATIONS
    assert "consensus_estimates" in REQUIRED_TABLES


# ---------------------------------------------------------------------------
# 4. fiscal_year_results／company_guidance 的 ledger 讀取（PIT 靠 recorded_at）
# ---------------------------------------------------------------------------

FY_RESULTS = {
    "fiscal_year_end": "2026-06-30", "currency": "USD", "revenue": 7_118_200_000,
    "segment_revenue": {"Datacenter & Communications": 5_274_600_000, "Industrial": 1_843_600_000},
    "gaap": {"operating_income": 897_900_000, "diluted_eps": 4.12, "diluted_shares": 195_400_000,
             "note": "文字不是損益項目"},
    "non_gaap": {"operating_income": 1_456_900_000, "diluted_eps": 5.61, "diluted_shares": 195_400_000},
    "exit_quarter": {"period_end": "2026-06-30", "diluted_shares": 202_200_000},
    "source_filed_at": "2026-08-12",
}


def test_fiscal_year_results_are_read_from_the_ledger_with_pit_semantics() -> None:
    conn = _conn()
    observation_id = append_manual_observation(
        conn, ticker="COHR", field_name="fiscal_year_results", value=json.dumps(FY_RESULTS),
        source_ref="COHR 8-K EX-99.1 (EDGAR 0001193125-26-346860) Tables 2/5/6/8", as_of="2026-06-30",
        author="test")
    provider = EngineCFundamentalsProvider(conn=conn)
    actuals, reason = provider.fiscal_year_results(Ticker("COHR"))
    assert reason is None and actuals is not None
    assert actuals.period.end == date(2026, 6, 30) and actuals.currency == "USD"
    assert actuals.revenue == 7_118_200_000 and actuals.segment_revenue["Industrial"] == 1_843_600_000
    assert actuals.gaap["diluted_eps"] == 4.12 and "note" not in actuals.gaap
    assert actuals.non_gaap["operating_income"] == 1_456_900_000
    assert actuals.exit_quarter["diluted_shares"] == 202_200_000
    assert actuals.source_filed_at == date(2026, 8, 12)
    assert actuals.evidence[0].ref == f"engine_c://manual_observation/{observation_id}"
    assert actuals.evidence[0].published_at == date(2026, 8, 12)
    assert actuals.recorded_at is not None
    # PIT：recorded_at 是今天，問 2026-08-20 就是「當時不知道」
    before, reason = provider.fiscal_year_results(Ticker("COHR"), as_of=date(2026, 8, 20))
    assert before is None and "截至 2026-08-20" in reason
    nobody, reason = provider.fiscal_year_results(Ticker("NOPE"))
    assert nobody is None and "record_mechanical_observation" in reason


def test_company_guidance_is_an_observation_of_what_the_company_said() -> None:
    conn = _conn()
    guidance = {"period_label": "Q1 FY2027", "period_kind": "fiscal_quarter", "period_end": "2026-09-30",
                "basis": "non_gaap", "issued_at": "2026-08-12", "revenue_low": 2.2e9, "revenue_high": 2.4e9,
                "gross_margin_low": 0.395, "gross_margin_high": 0.415, "eps_low": 1.85, "eps_high": 2.05}
    append_manual_observation(conn, ticker="COHR", field_name="company_guidance", value=json.dumps(guidance),
                              source_ref="COHR 8-K EX-99.1 Business Outlook", as_of="2026-08-12", author="test")
    provider = EngineCFundamentalsProvider(conn=conn)
    items, reason = provider.company_guidance(Ticker("COHR"))
    assert reason is None and len(items) == 1
    item = items[0]
    assert item.period_label == "Q1 FY2027" and item.basis == "non_gaap"
    assert item.values["revenue_low"] == 2.2e9 and "period_label" not in item.values
    assert item.issued_at == date(2026, 8, 12) and item.evidence[0].published_at == date(2026, 8, 12)
    assert provider.company_guidance(Ticker("COHR"), as_of=date(2026, 8, 1))[0] == ()


def test_mechanical_fields_are_registered_without_touching_the_gate() -> None:
    from engine_c.observation_fields import get_observation_field_registry

    registry = get_observation_field_registry()
    for name in ("fiscal_year_results", "company_guidance"):
        spec = registry.get(name)
        assert spec is not None and spec.verifiability == "mechanical" and not spec.gate_member
    with pytest.raises(ValueError, match="mechanical"):
        append_manual_observation(_conn(), ticker="COHR", field_name="fiscal_year_results",
                                  value="FY2026 was great", source_ref="x", as_of="2026-06-30", author="t")
