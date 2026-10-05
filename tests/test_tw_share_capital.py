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


def test_the_two_percent_threshold_itself_is_pinned() -> None:
    """R2 C2（2026-10-05）：門檻本身也要驗（L14-②）——權益÷每股淨值＝1 億股，股本換算差 2.5% 拒、差 1.5% 收。"""
    base = {"equity_total": 1_000_000, "bvps": 10.0}
    assert tsc.build_observation(_row(share_capital=1_025_000, **base))["cross_check_status"] == "mismatch"
    assert tsc.build_observation(_row(share_capital=1_015_000, **base))["cross_check_status"] == "ok"


def test_treasury_shares_shown_as_dashes_are_not_zero() -> None:
    """R2 N5：庫藏股欄「--」＝不知道，不是 0（Missing ≠ Zero）。"""
    obs = tsc.build_observation(_row(treasury_shares=None))
    assert obs["cross_check_status"] == "not_checkable" and obs["shares_outstanding"] is None
    assert "庫藏股" in obs["cross_check_reason"]                 # 理由要說出是哪一格不知道，不是泛稱「股本缺」


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


def _split(conn, ticker: str, day: str, ratio: float) -> None:
    conn.execute("INSERT INTO corporate_actions VALUES (?, ?, 'split', ?, 'fixture', '2026-10-05T00:00:00+00:00')",
                 (ticker, day, ratio))


def test_the_landmark_case_never_counts_the_stock_dividend_twice() -> None:
    """R2 C2（2026-10-05）：3081.TWO 的真實形狀——Q2 股本已含 10% 待分配股票股利、07-15 除權記成 1.1 的分割。
    Q2 必須被拒，08-14 之後的股數＝Q1 × 1.1（不是 × 1.1²）。"""
    conn = _db()
    tsc.append_share_capital(conn, tsc.build_observation(_row(quarter=1, share_capital=925_173, equity_total=3_881_853,
                                                              bvps=41.96)))
    q2 = tsc.build_observation(_row(share_capital=1_017_690, equity_total=3_881_853, bvps=41.96))
    assert q2["cross_check_status"] == "mismatch"
    tsc.append_share_capital(conn, q2)
    _split(conn, "3081.TWO", "2026-07-15", 1.1)
    got = tw_shares_as_of(conn, "3081.TWO", as_of="2026-09-01")
    assert [c["period_end"] for c in got["cover"]] == ["2026-03-31"]
    shares = tq.shares_on(got["cover"], [(date(2026, 7, 15), 1.1)], date(2026, 9, 1))
    assert shares == pytest.approx(92_517_300 * 1.1)


def test_a_small_stock_dividend_that_passes_the_check_is_still_not_counted_twice() -> None:
    """R2 N1：配股 1.5% 過得了 2% 核對——期末後、可知日前（含）有分割的季由讀取端整季不用，不靠門檻。"""
    conn = _db()
    tsc.append_share_capital(conn, tsc.build_observation(_row(quarter=1, share_capital=1_000_000, equity_total=1_000_000,
                                                              bvps=10.0)))
    q2 = tsc.build_observation(_row(share_capital=1_015_000, equity_total=1_000_000, bvps=10.0))
    assert q2["cross_check_status"] == "ok"
    tsc.append_share_capital(conn, q2)
    _split(conn, "3081.TWO", "2026-07-15", 1.015)
    got = tw_shares_as_of(conn, "3081.TWO", as_of="2026-09-01")
    assert [c["period_end"] for c in got["cover"]] == ["2026-03-31"]
    assert [(r["period_end"], r["status"]) for r in got["rejected"]] == [("2026-06-30", "split_in_window")]
    assert tq.shares_on(got["cover"], [(date(2026, 7, 15), 1.015)], date(2026, 9, 1)) == pytest.approx(101_500_000)


def test_split_window_boundaries_match_shares_on() -> None:
    """覆核非阻斷 #1：拒收窗 (期末, 可知日] 與 `shares_on` 的 (期末, d] 對稱——分割剛好在期末那天＝期末股本已含，收、不再乘；
    剛好在可知日那天＝在窗內，整季不用、由前一季乘分割比例接續。"""
    on_end = _db()
    tsc.append_share_capital(on_end, tsc.build_observation(_row(share_capital=1_000_000, equity_total=1_000_000, bvps=10.0)))
    _split(on_end, "3081.TWO", "2026-06-30", 1.05)
    got = tw_shares_as_of(on_end, "3081.TWO", as_of="2026-09-01")
    assert [c["period_end"] for c in got["cover"]] == ["2026-06-30"]
    assert tq.shares_on(got["cover"], [(date(2026, 6, 30), 1.05)], date(2026, 9, 1)) == pytest.approx(100_000_000)
    on_deadline = _db()
    tsc.append_share_capital(on_deadline, tsc.build_observation(_row(quarter=1, share_capital=1_000_000,
                                                                     equity_total=1_000_000, bvps=10.0)))
    tsc.append_share_capital(on_deadline, tsc.build_observation(_row(share_capital=1_000_000, equity_total=1_000_000,
                                                                     bvps=10.0)))
    _split(on_deadline, "3081.TWO", "2026-08-14", 1.05)
    got = tw_shares_as_of(on_deadline, "3081.TWO", as_of="2026-09-01")
    assert [c["period_end"] for c in got["cover"]] == ["2026-03-31"]
    assert tq.shares_on(got["cover"], [(date(2026, 8, 14), 1.05)], date(2026, 9, 1)) == pytest.approx(105_000_000)


def test_exactly_two_percent_is_accepted_and_just_above_is_not() -> None:
    """覆核非阻斷 #3：判準是「> 2%」——剛好 2.000% 收、2.01% 拒。"""
    base = {"equity_total": 1_000_000, "bvps": 10.0}
    assert tsc.build_observation(_row(share_capital=1_020_000, **base))["cross_check_status"] == "ok"
    assert tsc.build_observation(_row(share_capital=1_020_100, **base))["cross_check_status"] == "mismatch"


def test_securities_template_is_rejected_even_though_it_is_23_columns_with_current_assets() -> None:
    """R2 N2：證券期貨業的表頭與一般業只差四個措辭，但它的半年報期限是 8/31——必須拒收（實測 115Q2 上市三家、上櫃七家）。"""
    securities = ("公司代號", "公司名稱", "流動資產", "非流動資產", "資產總計", "流動負債", "非流動負債", "負債總計", "股本",
                  "權益－具證券性質之虛擬通貨", "資本公積", "保留盈餘（或累積虧損）", "其他權益", "庫藏股票", "歸屬於母公司業主權益合計",
                  "共同控制下前手權益", "合併前非屬共同控制股權", "非控制權益", "權益總計", "待註銷股本股數（單位：股）",
                  "預收股款（權益項下）之約當發行股數（單位：股）", "母公司暨子公司持有之母公司庫藏股股數（單位：股）", "每股參考淨值")
    assert securities not in mod.BALANCE_SHEET_TEMPLATES.values()
    rows, rejected = mod.parse_balance_sheet(_table(securities, [_cells(securities, **{"公司代號": "2855", "公司名稱": "統一證"})]),
                                             market="twse", year=2026, quarter=2, source_url="fixture://t163")
    assert rows == [] and rejected[0]["company_code"] == "2855"


def test_backfill_names_watched_tickers_missing_from_a_quarter(monkeypatch) -> None:
    """R2 N4（INV-3）：名冊上的標的在某一季兩張表都沒出現，回補報表要點名，不與「抓到了」同形。"""
    def fake(market, year, quarter):
        if market == "tpex":
            return [_row()], []
        return [], [{"ticker": "2801.TW", "template": "unregistered:61欄"}]

    monkeypatch.setattr(mod, "fetch_balance_sheet_quarter", fake)
    conn = _db()
    report = tsc.backfill(conn, 1, tickers=["3081.TWO", "4979.TWO", "2301.TW"], today=date(2026, 10, 5))
    assert report["quarters"][0]["missing"] == ["2301.TW", "4979.TWO"]
    assert report["seen"] == 1


def test_a_whole_market_failure_is_reported_once_not_also_as_missing_tickers(monkeypatch) -> None:
    """覆核非阻斷 #4：上櫃整張抓失敗——那個市場的標的只在 `failed` 出現一次，不再被點名成「表上沒有」。"""
    def fake(market, year, quarter):
        if market == "tpex":
            raise mod.MopsOpenDataError("fixture：上櫃逾時")
        return [], [{"ticker": "2801.TW", "template": "unregistered:61欄"}]

    monkeypatch.setattr(mod, "fetch_balance_sheet_quarter", fake)
    report = tsc.backfill(_db(), 1, tickers=["3081.TWO", "2301.TW"], today=date(2026, 10, 5))
    assert [f["market"] for f in report["failed"]] == ["tpex"]
    assert report["quarters"][0]["missing"] == ["2301.TW"]


def test_heartbeat_does_not_call_a_rejected_latest_quarter_a_lag(monkeypatch) -> None:
    """R2 C1：最新一季抓到了但被拒（3081.TWO 2026Q2）——不是落後、`--sync` 修不了，要另列；真的沒抓才叫落後。"""
    from datetime import datetime, timezone

    from crons import heartbeat as hb

    class _KeepOpen:                       # 心跳每次都會 close()；測試要在兩次呼叫之間共用同一個記憶體庫
        def __init__(self, inner):
            self._inner = inner

        def close(self) -> None:
            pass

        def __getattr__(self, name):
            return getattr(self._inner, name)

    conn = _KeepOpen(_db())
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: conn)
    monkeypatch.setattr("engine_c.monthly_revenue.registry_taiwan_tickers", lambda: ["3081.TWO"])
    now = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)
    tsc.append_share_capital(conn, tsc.build_observation(_row(quarter=1, share_capital=925_173, equity_total=3_881_853,
                                                              bvps=41.96)))
    behind = hb._tw_share_capital_line(now=now)
    assert "落後 1 季" in behind
    tsc.append_share_capital(conn, tsc.build_observation(_row(share_capital=1_017_690, equity_total=3_881_853, bvps=41.96)))
    line = hb._tw_share_capital_line(now=now)
    assert "落後" not in line and "已跟上法定期限" in line
    assert "最新一季不能用" in line and "3081.TWO 2026Q2" in line


def test_heartbeat_names_tickers_with_nothing_and_says_so_when_the_table_is_empty(monkeypatch) -> None:
    """覆核非阻斷 #2：一筆都沒有、部分檔沒有——兩種「沒有」都要自己說話（L14：會自己出現的計數器）。"""
    from datetime import datetime, timezone

    from crons import heartbeat as hb

    class _KeepOpen:
        def __init__(self, inner):
            self._inner = inner

        def close(self) -> None:
            pass

        def __getattr__(self, name):
            return getattr(self._inner, name)

    conn = _KeepOpen(_db())
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: conn)
    monkeypatch.setattr("engine_c.monthly_revenue.registry_taiwan_tickers", lambda: ["3081.TWO", "4979.TWO"])
    now = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)
    assert "**一筆都沒有**" in hb._tw_share_capital_line(now=now)
    tsc.append_share_capital(conn, tsc.build_observation(_row(quarter=1, share_capital=925_173, equity_total=3_881_853,
                                                              bvps=41.96)))
    line = hb._tw_share_capital_line(now=now)
    assert "1/2 檔" in line and "**1 檔一筆都沒有**：4979.TWO" in line and "落後 1 季" in line


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
    rejected = [{"period_end": "2025-06-30", "status": "mismatch", "reason": "fixture", "observation_id": "tsc_x"}]
    inp = {"price_bars": bars, "revenue_kind": "monthly", "monthly_revenue": months, "shares_cover": cover,
           "splits": [], "price_settlement_currency": "TWD", "price_to_settlement": 1.0, "source": "fixture",
           "shares_rejected": rejected}
    row = tq.own_history(inp, today=today)
    assert row["absence_kind"] is None and row["basis"] == "P/S"
    assert row["detail"]["shares_rejected"] == rejected          # R2 N11：被拒的季要走到稽核區（INV-3）
    days_before = sum(1 for d, _ in bars[:-1] if d < date(2026, 8, 14) and d >= today - timedelta(days=365 * 3))
    past = sum(1 for d, _ in bars[:-1] if d >= today - timedelta(days=365 * 3))
    assert row["value"] == round(100.0 * days_before / past, 1)
