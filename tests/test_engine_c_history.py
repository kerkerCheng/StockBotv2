"""Engine C 機械歷史表（Phase 3 Step 3.2）的守門測試。

守的是四件事，每一件都對應一個會靜默出錯、而且錯了就改不回判斷的坑：
① **T 時刻知道什麼**（INV-6）：財報可用日是 `filed`、月營收是法定期限，不是會計期末、更不是抓取日；
② **口徑**：yfinance 的 Close 已做分割調整——市值要用「當時的價×當時的股數」，兩者都要是當時的單位；
③ **不挑一個**：白名單歧異、多單位、多股類一律拒寫並列原因（沿用 `fetchers/edgar_xbrl.py` 的守則）；
④ **going concern 的值在發編號之前就驗**（2026-08-14 LITE 事故：只在 ledger 端驗 → 核准後才失敗）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from engine_c import history_backfill as hb
from engine_c.history import fundamental_series, monthly_revenue_as_of, price_series

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 9, 29)
FETCHED = "2026-09-29T03:00:00+00:00"


def _conn() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# 建表：雙後端對等、舊表不動
# ---------------------------------------------------------------------------

def test_sqlite_schema_creates_the_three_tables_and_is_idempotent() -> None:
    from engine_c.db import _ensure_sqlite_schema

    conn = _conn()
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"price_history", "corporate_actions", "fundamental_history"} <= names
    before = {t: conn.execute(f"PRAGMA table_info('{t}')").fetchall() for t in names}
    _ensure_sqlite_schema(conn)   # 第二次開庫：不得改任何一張表
    after = {t: conn.execute(f"PRAGMA table_info('{t}')").fetchall() for t in names}
    assert before == after


def test_metric_vocabulary_is_the_same_in_sqlite_postgres_and_schema_sql() -> None:
    """三處字彙一致。Postgres 的遷移檔是版本化的（已套用的檔不改）：建表那份＋之後每一份 CHECK 遷移的聯集
    （2026-10-01 Phase 4 Step 4.6 加 `20261001_add_equity_issued_value_metric.sql`；2026-10-08 個股頁 S3a 加
    `20261008_add_capex_metric.sql`）。**最新那一份 CHECK 遷移要列出完整字彙**（它是先刪再建）。"""
    migrations = ROOT / "engine_c" / "migrations"
    migration = (migrations / "20260929_add_history_tables.sql").read_text(encoding="utf-8")
    later = [(migrations / name).read_text(encoding="utf-8")
             for name in ("20261001_add_equity_issued_value_metric.sql", "20261008_add_capex_metric.sql")]
    schema = (ROOT / "engine_c" / "schema.sql").read_text(encoding="utf-8")
    for metric in hb.METRICS:
        assert f"'{metric}'" in schema and f"'{metric}'" in hb._SQLITE_DDL, metric
        assert f"'{metric}'" in (" ".join(later) if metric in hb.LATE_METRICS else migration), metric
        assert f"'{metric}'" in later[-1], f"最新的 CHECK 遷移要列出完整字彙（含舊的）：{metric}"
    for table in ("price_history", "corporate_actions", "fundamental_history"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert "PRIMARY KEY (ticker, metric, period_end, accession)" in migration


def test_postgres_migration_is_applied_by_the_versioned_runner() -> None:
    from engine_c.migrate import apply_migrations

    from tests.test_engine_c_migrations import FakeConnection

    conn = FakeConnection()
    applied = apply_migrations(conn)
    assert "20260929_add_history_tables.sql" in applied
    executed = "\n".join(str(sql) for sql, _ in conn.cursor_instance.executed)
    assert "CREATE TABLE IF NOT EXISTS fundamental_history" in executed


# ---------------------------------------------------------------------------
# ① point-in-time
# ---------------------------------------------------------------------------

def _row(metric="revenue_quarter", *, end="2026-03-31", filed="2026-05-10", accn="A1", value=100.0,
         start="2026-01-01", form="10-Q", currency="USD", derived=None) -> dict:
    return {"ticker": "XYZ", "metric": metric, "period_start": start, "period_end": end, "filed": filed,
            "accession": accn, "form": form, "value": value, "currency": currency, "unit_scale": 1,
            "derived": derived, "tag": "us-gaap:Revenues", "source": hb.SOURCE_EDGAR, "fetched_at": FETCHED}


def test_as_of_takes_the_latest_filing_known_at_t_not_the_latest_value() -> None:
    """同一期被後來的申報重編：T 落在兩次申報之間，拿到的必須是舊值（INV-6）。"""
    conn = _conn()
    hb.insert_fundamentals(conn, [_row(filed="2026-05-10", accn="A1", value=100.0),
                                  _row(filed="2027-05-10", accn="A2", value=90.0, form="10-Q")])
    assert fundamental_series(conn, "XYZ", "revenue_quarter", as_of="2026-05-09") == []
    between = fundamental_series(conn, "XYZ", "revenue_quarter", as_of=date(2026, 12, 31))
    assert [r["value"] for r in between] == [100.0]
    after = fundamental_series(conn, "XYZ", "revenue_quarter", as_of=date(2027, 6, 1))
    assert [r["value"] for r in after] == [90.0] and after[0]["accession"] == "A2"


def test_fetched_at_never_decides_availability() -> None:
    """抓取日是我們哪天抓的，不是市場哪天知道的：今天抓到的舊申報，過去照樣看得到；未來申報今天抓到也看不到。"""
    conn = _conn()
    hb.insert_fundamentals(conn, [_row(filed="2024-05-10", accn="OLD", end="2024-03-31", start="2024-01-01")])
    assert fundamental_series(conn, "XYZ", "revenue_quarter", as_of="2024-06-01")[0]["accession"] == "OLD"
    source = (ROOT / "engine_c" / "history.py").read_text(encoding="utf-8")
    assert "fetched_at <=" not in source and "fetched_at >=" not in source


def _mr(conn, month: str, deadline: str, fetched: str, revenue: int, source: str = "s") -> None:
    conn.execute(
        """INSERT INTO monthly_revenue_observations (observation_id, ticker, market, company_code, data_month,
               revenue_current, currency, unit_scale, disclosure_deadline, published_at_basis, source,
               fetched_at, payload_digest)
           VALUES (?, 'T.TW', 'twse', 'T', ?, ?, 'TWD', 1000, ?, 'statutory_deadline_only', ?, ?, ?)""",
        (f"mr_{month}_{revenue}_{source}", month, revenue, deadline, source, fetched, f"d_{month}_{revenue}_{source}"))


def test_monthly_revenue_is_available_on_the_statutory_deadline_not_on_fetch() -> None:
    conn = _conn()
    _mr(conn, "2026-07", "2026-08-10", "2026-09-17T13:00:00+00:00", 100)   # 今天才抓，但法定期限早過了
    _mr(conn, "2026-08", "2026-09-10", "2026-08-01T00:00:00+00:00", 200)   # 抓取日早於期限（不可能但要防）
    got = monthly_revenue_as_of(conn, "T.TW", as_of="2026-09-01")
    assert [m["data_month"] for m in got["months"]] == ["2026-07"]
    assert got["months"][0]["available_on"] == "2026-08-10"
    assert [m["data_month"] for m in monthly_revenue_as_of(conn, "T.TW", as_of="2026-09-10")["months"]] == \
        ["2026-07", "2026-08"]


def test_duplicate_months_agree_or_are_listed_as_conflicts_never_picked() -> None:
    conn = _conn()
    _mr(conn, "2026-08", "2026-09-10", "2026-09-17T13:00:00+00:00", 500, source="openapi")
    _mr(conn, "2026-08", "2026-09-10", "2026-09-17T13:01:00+00:00", 500, source="history_page")
    _mr(conn, "2026-07", "2026-08-10", "2026-09-17T13:00:00+00:00", 400, source="openapi")
    _mr(conn, "2026-07", "2026-08-10", "2026-09-17T13:01:00+00:00", 401, source="history_page")
    got = monthly_revenue_as_of(conn, "T.TW", as_of="2026-09-29")
    assert [m["data_month"] for m in got["months"]] == ["2026-08"]
    assert got["months"][0]["sources"] == ["history_page", "openapi"]
    assert got["conflicts"] == [{"data_month": "2026-07", "values": [400, 401],
                                 "sources": ["history_page", "openapi"]}]


def test_inserts_are_idempotent() -> None:
    conn = _conn()
    rows = [_row(accn="A1"), _row(accn="A2", filed="2026-08-10")]
    assert hb.insert_fundamentals(conn, rows) == 2
    assert hb.insert_fundamentals(conn, rows) == 0
    bars = [{"date": date(2026, 9, 25), "close": 10.0, "adj_close": 9.9, "split": 0.0}]
    prices, actions = hb.build_price_rows(bars, ticker="XYZ", quote_unit="USD", settlement_currency="USD",
                                          fetched_at=FETCHED)
    hb.upsert_prices(conn, prices, actions)
    hb.upsert_prices(conn, prices, actions)
    assert conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# ② 分割：raw 市值連續、adjusted 報酬連續
# ---------------------------------------------------------------------------

def test_split_rebuilds_raw_close_so_raw_market_cap_is_continuous() -> None:
    """NVDA 型：2024-06-10 一拆十。yfinance 的 Close 前後都已是拆後單位（120.89、121.79）；
    當天之前實際成交約 1,208.9。raw close × 當時股數（拆前 2.46B、拆後 24.6B）必須連續。"""
    bars = [
        {"date": date(2024, 6, 6), "close": 120.998, "adj_close": 120.654, "split": 0.0},
        {"date": date(2024, 6, 7), "close": 120.888, "adj_close": 120.544, "split": 0.0},
        {"date": date(2024, 6, 10), "close": 121.790, "adj_close": 121.444, "split": 10.0},
        {"date": date(2024, 6, 11), "close": 120.910, "adj_close": 120.576, "split": 0.0},
    ]
    rows, actions = hb.build_price_rows(bars, ticker="NVDA", quote_unit="USD", settlement_currency="USD",
                                        fetched_at=FETCHED)
    assert actions == [{"ticker": "NVDA", "action_date": "2024-06-10", "kind": "split", "ratio": 10.0,
                        "source": hb.SOURCE_PRICES, "fetched_at": FETCHED}]
    raw = {r["bar_date"]: r["close_raw"] for r in rows}
    assert raw["2024-06-07"] == pytest.approx(1208.88)
    assert raw["2024-06-10"] == pytest.approx(121.79)
    cap_before = raw["2024-06-07"] * 2.46e9
    cap_after = raw["2024-06-10"] * 24.6e9
    assert abs(cap_after / cap_before - 1) < 0.02            # 市值連續（只差當天漲跌）
    adj = [r["close_adjusted"] for r in rows]
    assert all(abs(b / a - 1) < 0.02 for a, b in zip(adj, adj[1:]))   # adjusted 報酬連續


# ---------------------------------------------------------------------------
# ③ companyfacts → 列：季度＋年度＋衍生 Q4、20-F 只有年度、歧異拒寫
# ---------------------------------------------------------------------------

def _fact(start, end, val, accn, form, filed, unit="USD"):
    item = {"end": end, "val": val, "accn": accn, "form": form, "filed": filed}
    if start:
        item["start"] = start
    return unit, item


def _companyfacts(entries: dict) -> dict:
    """{(namespace, tag): [(unit, item), ...]} → companyfacts 形狀。"""
    facts: dict = {}
    for (ns, tag), items in entries.items():
        units: dict = {}
        for unit, item in items:
            units.setdefault(unit, []).append(item)
        facts.setdefault(ns, {})[tag] = {"units": units}
    return {"facts": facts}


def _domestic_facts() -> dict:
    rev = "RevenueFromContractWithCustomerExcludingAssessedTax"
    return _companyfacts({
        ("us-gaap", rev): [
            _fact("2025-01-01", "2025-03-31", 100, "Q1", "10-Q", "2025-05-10"),
            _fact("2025-04-01", "2025-06-30", 110, "Q2", "10-Q", "2025-08-10"),
            _fact("2025-07-01", "2025-09-30", 120, "Q3", "10-Q", "2025-11-10"),
            _fact("2025-01-01", "2025-09-30", 330, "Q3", "10-Q", "2025-11-10"),     # 9M 累計
            _fact("2025-01-01", "2025-12-31", 460, "FY", "10-K", "2026-02-20"),     # 年度 → Q4＝130
            _fact("2026-01-01", "2026-03-31", 140, "Q126", "10-Q", "2026-05-10"),
            _fact("2026-01-01", "2026-03-31", 141, "Q126", "10-Q", "2026-05-10"),   # 同 tag 同期兩個數 → 拒寫
        ],
        ("us-gaap", "OperatingIncomeLoss"): [
            _fact("2025-01-01", "2025-03-31", -5, "Q1", "10-Q", "2025-05-10"),
            _fact("2025-01-01", "2025-12-31", 20, "FY", "10-K", "2026-02-20"),
        ],
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"): [
            _fact(None, "2025-03-31", 50, "Q1", "10-Q", "2025-05-10"),
            _fact(None, "2025-12-31", 70, "FY", "10-K", "2026-02-20"),
            _fact(None, "2025-12-31", 7000, "FY", "10-K", "2026-02-20", unit="TWD"),  # 同期兩種單位 → 拒寫
        ],
        ("dei", "EntityCommonStockSharesOutstanding"): [
            _fact(None, "2025-05-01", 1000, "Q1", "10-Q", "2025-05-10", unit="shares"),
            _fact(None, "2026-03-01", 1200, "FY", "10-K", "2026-02-20", unit="shares"),
            _fact(None, "2026-05-01", 500, "Q126", "10-Q", "2026-05-10", unit="shares"),   # 多股類
            _fact(None, "2026-05-01", 700, "Q126", "10-Q", "2026-05-10", unit="shares"),
        ],
    })


def test_domestic_filer_gets_quarters_annuals_derived_q4_and_rejections_with_reasons() -> None:
    rows, rejected = hb.build_fundamental_rows(_domestic_facts(), ticker="XYZ", filer="domestic_quarterly",
                                               today=TODAY, fetched_at=FETCHED)
    by = {(r["metric"], r["period_end"]): r for r in rows}
    assert by[("revenue_quarter", "2025-03-31")]["value"] == 100
    q4 = by[("revenue_quarter", "2025-12-31")]
    assert q4["value"] == 130 and q4["derived"].startswith("FY−9M") and q4["filed"] == "2026-02-20"
    assert q4["period_start"] == "2025-10-01" and q4["accession"] == "FY"
    assert by[("revenue_annual", "2025-12-31")]["value"] == 460
    assert by[("operating_income_quarter", "2025-03-31")]["value"] == -5
    assert ("operating_income_quarter", "2025-12-31") not in by      # 沒有 9M 營益 → 不衍生、不猜
    assert by[("cash", "2025-03-31")]["value"] == 50
    assert ("cash", "2025-12-31") not in by                           # 兩種單位 → 拒寫
    assert by[("shares_outstanding_cover", "2025-05-01")]["value"] == 1000
    assert ("shares_outstanding_cover", "2026-05-01") not in by       # 多股類 → 不加總
    assert ("revenue_quarter", "2026-03-31") not in by                # 同期兩個數 → 拒寫
    reasons = " ".join(r["reason"] for r in rejected)
    assert "多種計價單位" in reasons and "多股類" in reasons and "不同的數" in reasons
    assert all(r["filed"] and r["accession"] and r["fetched_at"] == FETCHED for r in rows)


def test_foreign_annual_filer_stores_only_annual_points_and_no_cover_shares() -> None:
    facts = _companyfacts({
        ("ifrs-full", "Revenue"): [
            _fact("2025-01-01", "2025-12-31", 900, "F25", "20-F", "2026-04-16", unit="EUR"),
            _fact("2025-07-01", "2025-09-30", 250, "K3", "6-K", "2025-11-01", unit="EUR"),   # 6-K 不收
        ],
        ("ifrs-full", "CashAndCashEquivalents"): [
            _fact(None, "2025-12-31", 80, "F25", "20-F", "2026-04-16", unit="EUR")],
        ("dei", "EntityCommonStockSharesOutstanding"): [
            _fact(None, "2025-12-31", 5_000, "F25", "20-F", "2026-04-16", unit="shares")],
    })
    rows, _ = hb.build_fundamental_rows(facts, ticker="ADR", filer="foreign_annual", today=TODAY,
                                        fetched_at=FETCHED)
    assert {r["metric"] for r in rows} == {"revenue_annual", "cash"}
    assert all(r["form"].startswith("20-F") and r["currency"] == "EUR" for r in rows)


def test_unknown_filer_produces_no_rows() -> None:
    assert hb.build_fundamental_rows(_domestic_facts(), ticker="X", filer="unknown", today=TODAY,
                                     fetched_at=FETCHED) == ([], [])
    with pytest.raises(hb.HistoryBackfillError):
        hb.build_fundamental_rows({}, ticker="X", filer="mystery", today=TODAY, fetched_at=FETCHED)


def test_classify_filer_is_one_rule_for_backfill_and_readers() -> None:
    today = date(2026, 9, 29)
    assert hb.classify_filer([("10-Q", date(2026, 8, 1)), ("10-K", date(2026, 2, 1))], today=today)[0] == \
        "domestic_quarterly"
    assert hb.classify_filer([("20-F", date(2026, 4, 1)), ("6-K", date(2026, 8, 1))], today=today)[0] == \
        "foreign_annual"
    assert hb.classify_filer([("10-Q", date(2024, 1, 1))], today=today)[0] == "unknown"   # 超過 18 個月
    # 讀取端從已存列判，得到同一個類別
    conn = _conn()
    rows, _ = hb.build_fundamental_rows(_domestic_facts(), ticker="XYZ", filer="domestic_quarterly",
                                        today=TODAY, fetched_at=FETCHED)
    hb.insert_fundamentals(conn, rows)
    assert hb.filer_class(conn, "XYZ", today=TODAY)[0] == "domestic_quarterly"
    assert hb.filer_class(conn, "NOPE", today=TODAY)[0] == "unknown"


# ---------------------------------------------------------------------------
# companyfacts 落後：lagging 不寫、unknown 照寫並標、20-F 也會被檢查
# ---------------------------------------------------------------------------

def test_lag_status_distinguishes_unknown_from_current_and_checks_20f(monkeypatch: pytest.MonkeyPatch) -> None:
    import fetchers.edgar as edgar
    from fetchers.edgar_xbrl import companyfacts_lag, companyfacts_lag_status

    facts = _companyfacts({("ifrs-full", "Revenue"): [
        _fact("2024-01-01", "2024-12-31", 1, "F24", "20-F", "2025-04-17", unit="TWD")]})
    monkeypatch.setattr(edgar, "get_filings",
                        lambda *_a, **_k: [{"filed_date": "2026-04-16", "form_type": "20-F"}])
    status = companyfacts_lag_status("1", facts, forms=("20-F", "40-F"))
    assert status["status"] == "lagging" and status["lag_days"] == (date(2026, 4, 16) - date(2025, 4, 17)).days

    def boom(*_a, **_k):
        raise ConnectionError("down")

    monkeypatch.setattr(edgar, "get_filings", boom)
    unknown = companyfacts_lag_status("1", facts, forms=("20-F",))
    assert unknown["status"] == "unknown" and unknown["warning"] is None
    # 舊介面行為不變：抓不到時照舊回 (snapshot, None, None)
    assert companyfacts_lag("1", facts) == (date(2025, 4, 17), None, None)


def test_a_20f_that_only_brought_cover_facts_is_lagging_not_silently_current(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-c（2026-09-29）找到的 TSM／UMC 形狀：最新一份 20-F 在 companyfacts 只收到封面 `dei`，財報 fact 停在前一年。
    看全部 namespace 的快照日會被封面 fact 推成 current → FY2025 營收靜默缺席、報告一個字都沒寫。"""
    import fetchers.edgar as edgar

    facts = _companyfacts({
        ("ifrs-full", "Revenue"): [_fact("2024-01-01", "2024-12-31", 100, "F24", "20-F", "2025-04-17", unit="USD")],
        ("dei", "EntityCommonStockSharesOutstanding"): [
            _fact(None, "2025-12-31", 5_000, "F25", "20-F", "2026-04-16", unit="shares")],
    })
    monkeypatch.setattr(edgar, "get_filings",
                        lambda *_a, **_k: [{"filed_date": "2026-04-16", "form_type": "20-F"}])
    conn = _conn()
    report = hb.backfill_ticker_edgar(conn, "TSMX", "0000000002", today=TODAY, incremental=False,
                                      fetched_at=FETCHED, fetch_facts=lambda _c: facts)
    assert report["outcome"] == "lagging" and "落後" in report["absence"]
    assert conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] == 0


def test_rejections_outside_the_lookback_window_are_not_counted() -> None:
    """窗外（> 5 年）的期間本來就不寫——把它們的歧異算進拒寫數會把數字灌大（R2-c non-blocking #1）。"""
    rev = "RevenueFromContractWithCustomerExcludingAssessedTax"
    facts = _companyfacts({("us-gaap", rev): [
        _fact("2015-01-01", "2015-03-31", 1, "OLD", "10-Q", "2015-05-01"),
        _fact("2015-01-01", "2015-03-31", 2, "OLD", "10-Q", "2015-05-01"),
        _fact("2026-01-01", "2026-03-31", 5, "NEW", "10-Q", "2026-05-01")]})
    rows, rejected = hb.build_fundamental_rows(facts, ticker="X", filer="domestic_quarterly", today=TODAY,
                                               fetched_at=FETCHED)
    assert rejected == [] and [r["period_end"] for r in rows] == ["2026-03-31"]


def test_the_window_only_decides_what_is_reported_not_what_can_derive_q4() -> None:
    """R2-c 覆核 non-blocking #1：窗邊界之前的 9M 累計仍要拿來衍生窗內的第四季（AMAT／AMD 那一型）。"""
    rev = "RevenueFromContractWithCustomerExcludingAssessedTax"
    facts = _companyfacts({("us-gaap", rev): [
        _fact("2020-11-01", "2021-07-31", 270, "Q3", "10-Q", "2021-08-20"),     # 9M 期末在窗外（< 2021-09-30）
        _fact("2020-11-01", "2021-10-31", 380, "FY", "10-K", "2021-12-10"),     # 年度期末在窗內
    ]})
    rows, _ = hb.build_fundamental_rows(facts, ticker="X", filer="domestic_quarterly", today=TODAY,
                                        fetched_at=FETCHED)
    q4 = [r for r in rows if r["metric"] == "revenue_quarter"]
    assert len(q4) == 1 and q4[0]["value"] == 110 and q4[0]["derived"]


def test_backfill_skips_lagging_writes_unknown_and_reports_every_outcome() -> None:
    conn = _conn()
    facts = _domestic_facts()
    lagging = hb.backfill_ticker_edgar(
        conn, "XYZ", "0000000001", today=TODAY, incremental=False, fetched_at=FETCHED,
        fetch_facts=lambda _c: facts,
        lag_status=lambda *_a, **_k: {"status": "lagging", "warning": "companyfacts 落後 90 天"})
    assert lagging["outcome"] == "lagging" and "落後" in lagging["absence"]
    assert conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] == 0

    unknown = hb.backfill_ticker_edgar(
        conn, "XYZ", "0000000001", today=TODAY, incremental=False, fetched_at=FETCHED,
        fetch_facts=lambda _c: facts, lag_status=lambda *_a, **_k: {"status": "unknown"})
    assert unknown["outcome"] == "written" and unknown["lag_unknown"] is True and unknown["rows_new"] > 0

    no_cik = hb.backfill_ticker_edgar(conn, "2330.TW", None, today=TODAY, incremental=False, fetched_at=FETCHED)
    assert no_cik["outcome"] == "no_cik" and no_cik["absence"]

    # 增量：submissions 沒有比已存更新的申報 → 不重抓 companyfacts
    def never(_c):
        raise AssertionError("不該重抓")

    # （已存最新 filed＝2026-02-20：2026-05-10 那份申報的營收與股數都被拒寫，所以沒有列）
    unchanged = hb.backfill_ticker_edgar(
        conn, "XYZ", "0000000001", today=TODAY, incremental=True, fetched_at=FETCHED, fetch_facts=never,
        submissions_latest=lambda _c, _f: date(2026, 2, 20))
    assert unchanged["outcome"] == "unchanged"
    # 有更新的申報就重抓（抓到的東西照樣經過落後檢查與拒寫守則）
    refetched = hb.backfill_ticker_edgar(
        conn, "XYZ", "0000000001", today=TODAY, incremental=True, fetched_at=FETCHED,
        fetch_facts=lambda _c: facts, lag_status=lambda *_a, **_k: {"status": "current"},
        submissions_latest=lambda _c, _f: date(2026, 5, 10))
    assert refetched["outcome"] == "written" and refetched["rows_new"] == 0   # 冪等：同一份 companyfacts 不多寫


def test_bars_without_any_close_are_not_observations() -> None:
    """2026-09-29 實測：歐股當天的列 yfinance 先回 NaN——寫進去就是一個「最後一點沒有價」的假觀測。"""
    bars = [{"date": date(2026, 9, 25), "close": 10.0, "adj_close": 9.9, "split": 0.0},
            {"date": date(2026, 9, 28), "close": None, "adj_close": None, "split": 0.0}]
    rows, _ = hb.build_price_rows(bars, ticker="IQE.L", quote_unit="GBp", settlement_currency="GBP",
                                  fetched_at=FETCHED)
    assert [r["bar_date"] for r in rows] == ["2026-09-25"]


def test_price_series_reads_as_of() -> None:
    conn = _conn()
    bars = [{"date": date(2026, 9, d), "close": float(d), "adj_close": float(d), "split": 0.0} for d in (24, 25, 28)]
    rows, actions = hb.build_price_rows(bars, ticker="XYZ", quote_unit="GBp", settlement_currency="GBP",
                                        fetched_at=FETCHED)
    hb.upsert_prices(conn, rows, actions)
    got = price_series(conn, "XYZ", as_of="2026-09-25")
    assert [r["bar_date"] for r in got] == ["2026-09-24", "2026-09-25"]
    assert got[0]["quote_unit"] == "GBp"      # 報價單位照交易所存，不改寫成 ISO


# ---------------------------------------------------------------------------
# ④ going_concern_opinion：提案層就拒收（不發編號）
# ---------------------------------------------------------------------------

GOOD_GC = json.dumps({"opinion": "substantial_doubt", "quote": "These conditions raise substantial doubt…",
                      "page": "F-2", "report_date": "2026-03-17"})


@pytest.mark.parametrize("value", [
    "not json",
    json.dumps(["substantial_doubt"]),
    json.dumps({"opinion": "maybe"}),
    json.dumps({"opinion": "substantial_doubt", "page": "F-2", "report_date": "2026-03-17"}),         # 缺 quote
    json.dumps({"opinion": "no_substantial_doubt", "quote": "q", "report_date": "2026-03-17"}),       # 缺 page
    json.dumps({"opinion": "no_substantial_doubt", "quote": "q", "page": 3, "report_date": "2026/03/17"}),
    json.dumps({"opinion": "not_reviewed", "extra": 1}),
])
def test_illegal_going_concern_values_are_refused_before_a_number_is_issued(
        value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from engine_c import pending_observations

    monkeypatch.setattr(pending_observations, "PENDING_DIR", tmp_path / "pending")
    with pytest.raises(pending_observations.ProposalError):
        pending_observations.propose(ticker="IQE.L", field_name="going_concern_opinion", value=value,
                                     source_ref="IQE plc Annual Report 2025 p.F-2", as_of="2026-03-17",
                                     author="session")
    assert not (tmp_path / "pending").exists() or not any((tmp_path / "pending").iterdir())


def test_valid_going_concern_value_passes_both_layers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from engine_c import pending_observations
    from engine_c.manual_observations import append_manual_observation

    monkeypatch.setattr(pending_observations, "PENDING_DIR", tmp_path / "pending")
    record = pending_observations.propose(ticker="IQE.L", field_name="going_concern_opinion", value=GOOD_GC,
                                          source_ref="IQE plc Annual Report 2025 p.F-2", as_of="2026-03-17",
                                          author="session")
    assert record["state"] == "pending"
    conn = _conn()
    append_manual_observation(conn, ticker="IQE.L", field_name="going_concern_opinion", value=GOOD_GC,
                              source_ref="IQE plc Annual Report 2025 p.F-2", as_of="2026-03-17", author="session")
    with pytest.raises(ValueError):
        append_manual_observation(conn, ticker="IQE.L", field_name="going_concern_opinion",
                                  value=json.dumps({"opinion": "maybe"}), source_ref="x", as_of="2026-03-18",
                                  author="session")


def test_going_concern_field_is_registered_as_judgment_and_not_a_gate_member() -> None:
    from engine_c.observation_fields import validate_field_name

    spec = validate_field_name("going_concern_opinion")
    assert spec.verifiability == "judgment" and spec.requires_user_approval and not spec.gate_member
