"""Phase 7 批次二 E1（failure log #81；使用者 2026-10-21 Q1 A）：名冊寫入完成時補新台股的 Engine C 歷史。

守：①只補台股、回補長度 54 個月／20 季；②`tickers=None`（入圖包）從資料判：一筆歷史都沒有、而且沒試過的；試過的不重打；
③任何失敗只寫進收據、不 raise（名冊已寫）；④收據逐檔寫補到幾個月、幾季、三年窗滿了沒，並 append 進嘗試紀錄；
⑤三年窗與三題同一個口徑（3 年、短缺 30 天內不算）。名冊兩條 complete 路徑的掛點由 test_registry_batch／test_engine_b_todo 守。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from engine_b import todo
from engine_c import new_listing_history as nlh

ORIGINAL_HOOK = todo._new_listing_history       # 收集時取得；conftest 的 autouse fixture 之後才換掉它
TODAY = date(2026, 10, 21)


def _conn() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema
    from engine_c.tw_share_capital import ensure_share_capital_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    ensure_share_capital_schema(conn)
    return conn


def _month(conn, ticker, month):
    conn.execute("INSERT INTO monthly_revenue_observations (observation_id, ticker, market, company_code, data_month, "
                 "currency, unit_scale, disclosure_deadline, published_at_basis, source, fetched_at, payload_digest, "
                 "created_at) VALUES (?, ?, 'twse', ?, ?, 'TWD', 1000, '2026-01-10', 'x', 'x', 'x', ?, 'x')",
                 (f"m-{ticker}-{month}", ticker, ticker[:4], month, f"m-{ticker}-{month}"))


def _quarter(conn, ticker, period_end, available_on, status="ok"):
    conn.execute("INSERT INTO tw_share_capital_observations (observation_id, ticker, market, company_code, fiscal_year, "
                 "quarter, period_end, template, par_value, cross_check_status, currency, unit_scale, available_on, "
                 "available_on_basis, source, fetched_at, payload_digest, created_at) VALUES "
                 "(?, ?, 'twse', ?, 2020, 1, ?, 'general', 10, ?, 'TWD', 1000, ?, 'x', 'x', 'x', ?, 'x')",
                 (f"q-{ticker}-{period_end}", ticker, ticker[:4], period_end, status, available_on,
                  f"q-{ticker}-{period_end}"))


def _months_back(n):
    out, year, month = [], TODAY.year, TODAY.month
    for _ in range(n):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        out.append(f"{year:04d}-{month:02d}")
    return out


def _fakes(conn, *, months=54, quarters=20, fail=None):
    seen = {}

    def monthly(c, n, *, tickers, today):
        seen["monthly"] = (n, list(tickers))
        if fail == "monthly":
            raise RuntimeError("MOPS 版型變了")
        for t in tickers:
            for m in _months_back(months):
                _month(c, t, m)
        return {"failed": []}

    def shares(c, n, *, tickers, today):
        seen["shares"] = (n, list(tickers))
        for t in tickers:
            for i in range(quarters):
                _quarter(c, t, f"20{20 + i // 4:02d}-{3 * (i % 4) + 3:02d}-28", f"20{20 + i // 4:02d}-{3 * (i % 4) + 3:02d}-28")
        return {"failed": [{"market": "otc", "quarter": "2026Q2", "reason": "還沒出表"}]}

    return monthly, shares, seen


def test_only_taiwan_listings_are_backfilled_for_the_full_window_and_the_attempt_is_logged(tmp_path) -> None:
    conn = _conn()
    monthly, shares, seen = _fakes(conn)
    log = tmp_path / "attempts.jsonl"
    receipt = nlh.backfill_new_listings(["4991.TWO", "TNCO", "3234.two", None], reason="registry_batch:abc",
                                        conn=conn, monthly=monthly, shares=shares, today=TODAY, log_path=log)
    assert seen == {"monthly": (54, ["3234.TWO", "4991.TWO"]), "shares": (20, ["3234.TWO", "4991.TWO"])}
    assert receipt["outcome"] == "backfilled" and receipt["tickers"] == ["3234.TWO", "4991.TWO"]
    assert receipt["per_ticker"]["4991.TWO"]["months"] == 54 and receipt["per_ticker"]["4991.TWO"]["monthly_full"]
    assert receipt["fetch_failures"] == {"monthly_revenue": 0, "tw_share_capital": 1}
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["tickers"] == ["3234.TWO", "4991.TWO"]
    assert nlh.backfill_new_listings(["AXTI", "5706.T"], reason="x", conn=conn, monthly=monthly, shares=shares,
                                     today=TODAY, log_path=log)["outcome"] == "nothing_to_do"


def test_a_failed_fetch_is_written_into_the_receipt_and_never_raised(tmp_path) -> None:
    conn = _conn()
    monthly, shares, _seen = _fakes(conn, fail="monthly")
    receipt = nlh.backfill_new_listings(["4991.TWO"], reason="r", conn=conn, monthly=monthly, shares=shares,
                                        today=TODAY, log_path=tmp_path / "a.jsonl")
    assert receipt["outcome"] == "error" and "版型變了" in receipt["errors"][0]
    assert receipt["per_ticker"]["4991.TWO"]["months"] == 0 and receipt["short_of_window"] == ["4991.TWO"]


def test_without_a_ticker_list_only_registered_listings_with_no_history_and_no_attempt_are_chosen(tmp_path) -> None:
    conn = _conn()
    for m in _months_back(54):
        _month(conn, "3081.TWO", m)
    _quarter(conn, "3081.TWO", "2026-06-30", "2026-08-14")
    log = tmp_path / "attempts.jsonl"
    log.write_text(json.dumps({"tickers": ["6213.TW"]}) + "\n", encoding="utf-8")
    registered = ["3081.TWO", "4991.TWO", "6213.TW", "AXTI"]
    assert nlh.candidates_without_history(conn, today=TODAY, registered=registered, log_path=log) == ["4991.TWO"]


def test_the_three_year_window_uses_the_first_ttm_availability_and_ok_shares_only() -> None:
    conn = _conn()
    for m in _months_back(40):                         # 10-18 的形狀：40 個月不夠
        _month(conn, "6274.TW", m)
    _quarter(conn, "6274.TW", "2022-06-30", "2022-08-14", status="mismatch")
    _quarter(conn, "6274.TW", "2023-12-31", "2024-03-31")
    short = nlh.history_window(conn, "6274.TW", today=TODAY)
    assert short == {"months": 40, "quarters": 1, "monthly_full": False, "shares_full": False}
    for m in _months_back(54):
        _month(conn, "8358.TWO", m)
    _quarter(conn, "8358.TWO", "2023-06-30", "2023-08-14")
    full = nlh.history_window(conn, "8358.TWO", today=TODAY)
    assert full["monthly_full"] and full["shares_full"]
    assert nlh.window_shortfall(conn, ["6274.TW", "8358.TWO", "9999.TW"], today=TODAY) == {
        "monthly": ["6274.TW"], "shares": ["6274.TW"]}


def test_the_completion_hook_swallows_any_error_so_the_registry_write_stands(monkeypatch) -> None:
    def boom(tickers, *, reason):
        raise RuntimeError("Engine C 開不起來")

    monkeypatch.setattr(nlh, "backfill_new_listings", boom)
    out = ORIGINAL_HOOK(["4991.TWO"], reason="registry_batch:x")
    assert out["outcome"] == "error" and "開不起來" in out["error"]
