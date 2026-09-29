"""三題與稀釋燈的 Engine C 取數端（Phase 3 Step 3.3）。

守：①稀釋燈逐檔**單一來源**——國內季度申報人用 SEC 封面股數（分割調整到最新基準），其餘不動；
②going concern 讀結構化欄位的**生效**紀錄，同日多筆生效不挑一個；③取數這一層就知道算不了的（台股歷史股數、
非美非台）由它自己宣告 gate（L16），不讓判定層去猜。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from engine_c import history_backfill as hb
from engine_c.checklist import _cover_shares_series, _going_concern_record
from engine_c.manual_observations import append_manual_observation
from engine_c.three_question_inputs import get_three_question_inputs

TODAY = date(2026, 9, 29)
FETCHED = "2026-09-29T00:00:00+00:00"


def _conn() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


def _row(metric, end, filed, value, *, accn=None, form="10-Q", start=None, currency="USD"):
    return {"ticker": "XYZ", "metric": metric, "period_start": start, "period_end": end, "filed": filed,
            "accession": accn or f"A-{end}", "form": form, "value": value, "currency": currency, "unit_scale": 1,
            "derived": None, "tag": "dei:EntityCommonStockSharesOutstanding", "source": hb.SOURCE_EDGAR,
            "fetched_at": FETCHED}


def test_domestic_filer_dilution_uses_sec_cover_shares_split_adjusted() -> None:
    conn = _conn()
    hb.insert_fundamentals(conn, [
        _row("shares_outstanding_cover", "2025-05-01", "2025-05-14", 1_000.0),
        _row("shares_outstanding_cover", "2025-11-01", "2025-11-13", 1_050.0),
        _row("shares_outstanding_cover", "2026-08-01", "2026-08-13", 4_300.0),
        _row("revenue_quarter", "2026-06-30", "2026-08-13", 5.0, start="2026-04-01"),
    ])
    conn.execute("INSERT INTO corporate_actions VALUES ('XYZ', '2026-01-15', 'split', 4.0, 's', ?)", (FETCHED,))
    series = _cover_shares_series(conn, "XYZ", today=TODAY)
    assert series == [(date(2025, 5, 1), 4_000.0), (date(2025, 11, 1), 4_200.0), (date(2026, 8, 1), 4_300.0)]


def test_non_domestic_or_single_point_falls_back_to_the_snapshot_series() -> None:
    conn = _conn()
    hb.insert_fundamentals(conn, [_row("shares_outstanding_cover", "2026-08-01", "2026-08-13", 1.0),
                                  _row("revenue_quarter", "2026-06-30", "2026-08-13", 5.0, start="2026-04-01")])
    assert _cover_shares_series(conn, "XYZ", today=TODAY) is None           # 只有一點
    foreign = _conn()
    hb.insert_fundamentals(foreign, [_row("revenue_annual", "2025-12-31", "2026-04-16", 9.0, form="20-F",
                                          start="2025-01-01")])
    assert _cover_shares_series(foreign, "XYZ", today=TODAY) is None        # 20-F 不用封面股數


def _gc(conn, opinion, as_of, *, supersedes=None, parallel=False):
    return append_manual_observation(
        conn, ticker="XYZ", field_name="going_concern_opinion",
        value=json.dumps({"opinion": opinion, "quote": "q", "page": "F-2", "report_date": as_of}),
        source_ref="annual report", as_of=as_of, author="session", supersedes_id=supersedes,
        allow_parallel=parallel)


def test_going_concern_reads_the_live_record_and_never_picks_between_two() -> None:
    conn = _conn()
    assert _going_concern_record(conn, "XYZ") is None
    first = _gc(conn, "no_substantial_doubt", "2025-03-01")
    assert _going_concern_record(conn, "XYZ")["value"]["opinion"] == "no_substantial_doubt"
    _gc(conn, "substantial_doubt", "2026-03-01")
    assert _going_concern_record(conn, "XYZ")["value"]["opinion"] == "substantial_doubt"   # 最新 as_of
    _gc(conn, "no_substantial_doubt", "2026-03-01", parallel=True)                          # 同日兩筆生效
    record = _going_concern_record(conn, "XYZ")
    assert record.get("conflict") and len(record["conflict"]) == 2
    assert first.startswith("mo_")


def test_taiwan_and_non_us_gates_are_declared_where_the_absence_is_known() -> None:
    conn = _conn()
    tw = get_three_question_inputs("3081.TWO", conn=conn, today=TODAY, company_id=None)
    assert tw["revenue_kind"] == "monthly" and tw["gate"]["absence_kind"] == "upstream_unavailable"
    assert "台股歷史股數" in tw["gate"]["reason"]
    eu = get_three_question_inputs("IQE.L", conn=conn, today=TODAY)
    assert eu["filer_class"] == "unknown" and "非美國" in eu["gate"]["reason"]
    assert eu["price_quote_unit"] == "GBp" and eu["price_to_settlement"] == 0.01   # minor unit 由 registry 解析
