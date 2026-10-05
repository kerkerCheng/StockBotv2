"""台股季報股數（Phase 7 旁支開發「台股歷史股數」，2026-10-05）。

守四件事：①只收已登記版型——金融業的半年報期限比一般業晚，套一般業期限會提早看到（INV-6）；
②股數換算有交叉核對——面額不是 10 元的公司 fail closed，不被「股本 ÷ 10」靜默算錯十倍；
③可知日＝法定期限，as-of 回放看不到期限之後的股數，核對不過或同季兩個數字的整季不用（不挑一個）；
④三題的台股已定價①不再寫死缺席——有觀測就算，沒有觀測才缺席。
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from alpha import three_questions as tq
from engine_c import tw_share_capital as tsc
from engine_c.history import tw_shares_as_of
from engine_c.three_question_inputs import get_three_question_inputs
from fetchers import mops_open_data as mod

GENERAL = mod.BALANCE_SHEET_TEMPLATES["general"]
CONGLOMERATE = mod.BALANCE_SHEET_TEMPLATES["conglomerate"]
BANK_HEAD = ("公司代號", "公司名稱", "現金及約當現金", "股本", "權益總計", "每股參考淨值")
TREASURY = "母公司暨子公司所持有之母公司庫藏股股數（單位：股）"


def _table(head, rows) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def _cells(head, **values) -> list[str]:
    cells = dict.fromkeys(head, "--")
    cells.update(values)
    return [cells[h] for h in head]


def _general(code, name, capital, parent, nci, total, treasury, bvps) -> list[str]:
    return _cells(GENERAL, **{"公司代號": code, "公司名稱": name, "股本": capital, "歸屬於母公司業主之權益合計": parent,
                              "非控制權益": nci, "權益總計": total, TREASURY: treasury, "每股參考淨值": bvps})


BODY = "".join([
    "<table><tr><td>上市公司第二季資料</td></tr></table>",
    _table(BANK_HEAD, [("2801", "彰銀", "1", "100,000", "200,000", "20.00")]),
    _table(GENERAL, [_general("3081", "聯亞", "925,214", "--", "--", "3,881,853", "0", "41.96"),
                     _general("2301", "光寶科", "23,161,078", "95,803,594", "808,372", "96,611,966", "47,004,221", "42.22")]),
    _table(CONGLOMERATE, [_cells(CONGLOMERATE, **{"公司代號": "2207", "公司名稱": "和泰車", "股本": "5,461,940",
                                                   "權益總額": "100", "每股參考淨值": "1.00"})]),
])


def test_only_registered_templates_are_parsed_and_the_rest_are_reported() -> None:
    rows, rejected = mod.parse_balance_sheet(BODY, market="twse", year=2026, quarter=2, source_url="fixture://t163")
    assert [(r["company_code"], r["template"]) for r in rows] == [("3081", "general"), ("2301", "general"),
                                                                   ("2207", "conglomerate")]
    assert rows[0]["equity_parent"] is None and rows[0]["equity_total"] == 3_881_853     # 「--」不是 0
    assert rows[1]["treasury_shares"] == 47_004_221 and rows[1]["bvps"] == 42.22
    assert rows[2]["equity_total"] == 100                                                 # 異業的「權益總額」
    assert [(r["company_code"], r["template"]) for r in rejected] == [("2801", "unregistered:6欄")]


def test_a_header_changed_by_one_character_is_not_the_registered_template() -> None:
    head = tuple("權益-具證券性質之虛擬通貨" if h.startswith("權益─") else h for h in GENERAL)
    rows, rejected = mod.parse_balance_sheet(_table(head, [_general("3081", "聯亞", "1", "--", "--", "1", "0", "1")]),
                                             market="tpex", year=2026, quarter=2, source_url="fixture://t163")
    assert rows == [] and rejected[0]["template"] == "unregistered:23欄"


def test_fetch_never_returns_an_empty_set_when_the_general_table_is_missing(monkeypatch) -> None:
    class _Resp:
        content = _table(BANK_HEAD, [("2801", "彰銀", "1", "1", "1", "1")]).encode("utf-8")

    monkeypatch.setattr(mod, "_post", lambda url, data, timeout=60: _Resp())
    with pytest.raises(mod.MopsOpenDataError, match="已登記版型"):
        mod.fetch_balance_sheet_quarter("twse", 2026, 2)


def _row(**over) -> dict:
    base = {"market": "tpex", "company_code": "3081", "ticker": "3081.TWO", "company_name": "聯亞", "fiscal_year": 2026,
            "quarter": 2, "template": "general", "share_capital": 925_214, "equity_parent": None,
            "equity_total": 3_881_853, "non_controlling": None, "treasury_shares": 0, "bvps": 41.96,
            "source_url": "fixture://t163"}
    base.update(over)
    return base


def test_shares_are_capital_over_par_minus_treasury_and_cross_checked() -> None:
    obs = tsc.build_observation(_row())
    assert obs["shares_outstanding"] == 92_521_400 and obs["cross_check_status"] == "ok"
    assert (obs["period_end"], obs["available_on"]) == ("2026-06-30", "2026-08-14")
    lite = tsc.build_observation(_row(ticker="2301.TW", market="twse", share_capital=23_161_078,
                                      equity_parent=95_803_594, non_controlling=808_372, equity_total=96_611_966,
                                      treasury_shares=47_004_221, bvps=42.22))
    assert lite["shares_outstanding"] == 2_316_107_800 - 47_004_221 and lite["cross_check_status"] == "ok"


def test_a_par_value_that_is_not_ten_dollars_fails_closed_instead_of_scaling_by_ten() -> None:
    obs = tsc.build_observation(_row(share_capital=92_521))
    assert obs["cross_check_status"] == "mismatch" and "面額" in obs["cross_check_reason"]


def test_without_a_usable_book_value_nothing_is_checkable() -> None:
    assert tsc.build_observation(_row(bvps=None))["cross_check_status"] == "not_checkable"
    # 歸屬母公司業主權益是「--」卻有非控制權益：權益總計不是每股淨值的分子
    assert tsc.build_observation(_row(non_controlling=5_000))["cross_check_status"] == "not_checkable"


def test_statutory_deadlines_and_the_latest_due_quarter() -> None:
    assert [tsc.statutory_deadline(2026, q) for q in (1, 2, 3)] == ["2026-05-15", "2026-08-14", "2026-11-14"]
    assert tsc.statutory_deadline(2025, 4) == "2026-03-31"
    assert tsc.latest_due_quarter(date(2026, 10, 5)) == (2026, 2)
    assert tsc.latest_due_quarter(date(2026, 11, 14)) == (2026, 3)
    assert tsc.latest_due_quarter(date(2026, 3, 30)) == (2025, 3)


def _db() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


def test_writes_are_idempotent_and_a_quarter_is_seen_only_from_its_deadline() -> None:
    conn = _db()
    q1 = tsc.build_observation(_row(quarter=1, share_capital=900_000, equity_total=3_600_000, bvps=40.0))
    q2 = tsc.build_observation(_row())
    for obs in (q1, q2, q2):
        tsc.append_share_capital(conn, obs)
    assert conn.execute("SELECT COUNT(*) FROM tw_share_capital_observations").fetchone()[0] == 2
    before = tw_shares_as_of(conn, "3081.TWO", as_of="2026-08-13")
    assert [c["period_end"] for c in before["cover"]] == ["2026-03-31"]
    after = tw_shares_as_of(conn, "3081.TWO", as_of="2026-08-14")
    assert [(c["period_end"], c["filed"], c["value"]) for c in after["cover"]] == [
        ("2026-03-31", "2026-05-15", 90_000_000.0), ("2026-06-30", "2026-08-14", 92_521_400.0)]


def test_quarters_that_fail_the_check_or_disagree_are_never_used() -> None:
    conn = _db()
    tsc.append_share_capital(conn, tsc.build_observation(_row(quarter=1, share_capital=90_000, equity_total=3_600_000,
                                                              bvps=40.0)))
    tsc.append_share_capital(conn, tsc.build_observation(_row()))
    tsc.append_share_capital(conn, tsc.build_observation(_row(share_capital=925_300, equity_total=3_882_000)))
    got = tw_shares_as_of(conn, "3081.TWO", as_of="2026-10-05")
    assert got["cover"] == []
    assert [(r["period_end"], r["status"]) for r in got["rejected"]] == [("2026-03-31", "mismatch"),
                                                                         ("2026-06-30", "conflict")]


def test_a_readonly_connection_without_the_table_means_no_observations(tmp_path) -> None:
    path = tmp_path / "engine_c.db"
    sqlite3.connect(path).close()
    ro = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    assert tw_shares_as_of(ro, "3081.TWO", as_of="2026-10-05") == {"cover": [], "rejected": []}


def test_taiwan_inputs_carry_quarterly_shares_and_gate_only_without_them() -> None:
    conn = _db()
    empty = get_three_question_inputs("3081.TWO", conn=conn, today=date(2026, 10, 5), company_id=None)
    assert empty["gate"]["absence_kind"] == "upstream_unavailable" and "季報股數" in empty["gate"]["reason"]
    tsc.append_share_capital(conn, tsc.build_observation(_row()))
    got = get_three_question_inputs("3081.TWO", conn=conn, today=date(2026, 10, 5), company_id=None)
    assert "gate" not in got and got["shares_cover"][0]["value"] == 92_521_400.0


def test_own_history_for_a_taiwan_ticker_switches_shares_on_the_deadline_not_the_quarter_end() -> None:
    """價格與營收不變、股數在 2026Q2 加倍：倍數要從法定期限 08-14 才加倍，不是期末 06-30。"""
    today = date(2026, 10, 2)
    start = today - timedelta(days=365 * 3 + 10)
    bars = [(start + timedelta(days=i), 100.0) for i in range((today - start).days + 1)]
    months = []
    y, m = start.year - 1, start.month
    while (y, m) <= (2026, 8):
        nxt = (y + 1, 1) if m == 12 else (y, m + 1)
        months.append({"data_month": f"{y:04d}-{m:02d}", "revenue": 1_000, "unit_scale": 1000,
                       "available_on": date(nxt[0], nxt[1], 10).isoformat()})
        y, m = nxt
    cover = [{"period_end": "2023-03-31", "filed": "2023-05-15", "value": 10_000_000.0},
             {"period_end": "2026-06-30", "filed": "2026-08-14", "value": 20_000_000.0}]
    inp = {"price_bars": bars, "revenue_kind": "monthly", "monthly_revenue": months, "shares_cover": cover,
           "splits": [], "price_settlement_currency": "TWD", "price_to_settlement": 1.0, "source": "fixture"}
    row = tq.own_history(inp, today=today)
    assert row["absence_kind"] is None and row["basis"] == "P/S"
    days_before = sum(1 for d, _ in bars[:-1] if d < date(2026, 8, 14) and d >= today - timedelta(days=365 * 3))
    past = sum(1 for d, _ in bars[:-1] if d >= today - timedelta(days=365 * 3))
    assert row["value"] == round(100.0 * days_before / past, 1)
