"""台股年度財報地區別營收（個股頁 S3d 第二段，2026-10-14；`engine_c/tw_region_revenue.py`＋`alpha` 讀取端）。

守：①營收那一欄由「合計最接近那一年月營收加總」認出，不靠欄位順序（2 欄、4 欄交錯、年份倒過來都認得）；②各地區加起來要等於合計；
③同一欄對得上兩年＝不收（不猜哪欄是哪年）；④標籤不是地名的表（營收組成表）不收，「其他」不算地名；⑤依什麼分地區照年報原文標，
引文不吃進表格數字；⑥同一結果重抓只更新 fetched_at，A→B→A 讀到 A；⑦可知日前看不到；⑧讀取端：台股才有這一塊、分部占比的缺席
不因地區有值而消失（L12）；⑨頁面合約與前端只照抄。測試文字是照試抽觀察到的版面**合成**的，數字不是任何一家的。"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from alpha.providers.revenue_mix import revenue_mix
from alpha.revenue_mix import REGION_FIELD, region_mix
from briefing.analyst_view import page_schema as ps
from engine_c import tw_region_revenue as trr
from webapp.materialize import page_extra_for

APP = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")

# 兩欄、$ 在前、字與字之間有空白、基準句在表格後面緊貼（PDF 抽字後沒有句讀隔開）
TWO_COLUMNS = """（五）地區別資訊
A.來自外部客戶收入：
地 區 114年度 113年度
亞 洲 $100,000 $60,000
美 洲 30,000 10,000
其 他 2,000 1,000
合 計 $132,000 $71,000
收入以客戶所在地國家為基礎歸類。
"""
# 四欄交錯（收入、非流動資產各兩年）、$ 在後、合計列沒有標籤、基準句每個字之間都有空白
FOUR_COLUMNS = """地 區 別 資 訊
合 併 公 司 來 自 外 部 客 戶 之 收 入 依 營 運 地 點 區 分 與 非 流 動 資 產 按 資 產 所 在 地 區 分 。
收入 非流動資產 收入 非流動資產
台灣 50,000$ 9,000$ 40,000$ 8,000$
美國 30,000 1,000 20,000 900
中國大陸 20,000 500 25,000 400
100,000$ 10,500$ 85,000$ 9,300$
"""
# 地區表前面先有一張營收組成表，合計也等於營收（標籤不是地名，不收）
COMPOSITION_FIRST = """地區別資訊
114年度 113年度
銷貨收入淨額 1,800,000$ 1,300,000$
租賃收入 92,000 64,000
合計 1,892,000$ 1,364,000$
台灣 110,000$ 165,000$
中國大陸 132,000 42,000
美洲 1,506,000 1,061,000
其他 144,000 96,000
合計 1,892,000$ 1,364,000$
"""


def _expected(**years: float | None) -> dict[int, float | None]:
    return {int(k[1:]): v for k, v in years.items()}


def test_two_column_table_with_spaced_labels_and_the_customer_basis() -> None:
    out = trr.extract_regions(TWO_COLUMNS, _expected(y2025=132_000.0, y2024=71_000.0))
    assert out["status"] == "ok" and sorted(out["years"]) == [2024, 2025]
    assert out["years"][2025]["regions"] == [["亞洲", 100_000], ["美洲", 30_000], ["其他", 2_000]]
    assert out["years"][2024]["total"] == 71_000 and out["years"][2024]["monthly_total"] == 71_000
    assert out["basis"] == "customer_location" and out["basis_quotes"] == ["收入以客戶所在地國家為基礎歸類"]  # 沒吃進表格數字


def test_interleaved_four_columns_with_unlabeled_total_and_the_operating_basis() -> None:
    out = trr.extract_regions(FOUR_COLUMNS, _expected(y2025=100_000.0, y2024=85_000.0))
    assert out["status"] == "ok"
    assert out["years"][2025]["regions"] == [["台灣", 50_000], ["美國", 30_000], ["中國大陸", 20_000]]
    assert out["years"][2024]["regions"] == [["台灣", 40_000], ["美國", 20_000], ["中國大陸", 25_000]]   # 第三欄，不是第二欄
    assert out["basis"] == "operating_location" and "依營運地點區分" in out["basis_quotes"][0]


def test_a_composition_table_whose_total_also_matches_is_skipped_for_the_region_table() -> None:
    out = trr.extract_regions(COMPOSITION_FIRST, _expected(y2025=1_892_000.0, y2024=1_364_000.0))
    assert out["status"] == "ok" and [r[0] for r in out["years"][2025]["regions"]] == ["台灣", "中國大陸", "美洲", "其他"]
    assert out["basis"] == "unstated" and out["basis_quotes"] == []
    only = trr.extract_regions(COMPOSITION_FIRST.split("台灣")[0], _expected(y2025=1_892_000.0, y2024=1_364_000.0))
    assert only["status"] == "not_geographic" and "銷貨收入淨額" in only["reason"]


def test_other_is_not_evidence_of_a_region_table_and_does_not_count_against_one() -> None:
    text = "地區別資訊\n銷貨收入 90,000 50,000\n其他 10,000 5,000\n合計 100,000 55,000\n"
    assert trr.extract_regions(text, _expected(y2025=100_000.0, y2024=55_000.0))["status"] == "not_geographic"
    residuals = "地區別資訊\n台灣 60,000 30,000\n其他亞洲國家 30,000 20,000\n其他 10,000 5,000\n合計 100,000 55,000\n"
    assert trr.extract_regions(residuals, _expected(y2025=100_000.0, y2024=55_000.0))["status"] == "ok"


def test_year_columns_are_matched_by_total_not_by_order() -> None:
    text = "地區別資訊\n2024 2025\n台灣 40,000 70,000\n美國 20,000 30,000\n合計 60,000 100,000\n"   # 年份標題列自成一塊
    out = trr.extract_regions(text, _expected(y2025=100_050.0, y2024=59_990.0))
    assert out["status"] == "ok"
    assert out["years"][2025]["regions"] == [["台灣", 70_000], ["美國", 30_000]]
    assert out["years"][2024]["regions"] == [["台灣", 40_000], ["美國", 20_000]]


def test_a_column_matching_both_years_is_refused_not_guessed() -> None:
    text = "地區別資訊\n台灣 60,000 59,900\n美國 40,000 40,000\n合計 100,000 99,900\n"
    out = trr.extract_regions(text, _expected(y2025=100_000.0, y2024=99_900.0))
    assert out["status"] == "ambiguous_years" and out["years"] == {}


def test_regions_must_add_up_to_the_total() -> None:
    text = "地區別資訊\n台灣 60,000 50,000\n美國 30,000 10,000\n合計 100,000 60,000\n"
    out = trr.extract_regions(text, _expected(y2025=100_000.0, y2024=60_000.0))
    assert out["status"] == "total_mismatch" and "2025" in out["reason"]


def test_only_years_with_twelve_months_of_revenue_are_checked() -> None:
    one = trr.extract_regions(TWO_COLUMNS, _expected(y2025=132_000.0, y2024=None))
    assert one["status"] == "ok" and sorted(one["years"]) == [2025]
    none = trr.extract_regions(TWO_COLUMNS, _expected(y2025=None, y2024=None))
    assert none["status"] == "no_monthly_revenue" and none["years"] == {}
    off = trr.extract_regions(TWO_COLUMNS, _expected(y2025=140_000.0, y2024=80_000.0))     # 差 6%：不是這一欄
    assert off["status"] == "no_region_table"
    assert trr.extract_regions("沒有那一節", _expected(y2025=1.0))["status"] == "section_not_found"


def test_a_sentence_with_years_in_it_is_not_a_table_row() -> None:
    """「本公司民國 114 年及 113 年度…如下：」緊貼在表格上面：數字後面又有字的一行不是表格列，否則它會被算成一個地區。
    （句子裡不放「地區別資訊」——放了的話第二個標題會從句中接手，測不到這一條。）"""
    text = "地區別資訊\n本公司民國 114 年及 113 年度營收依地區列示如下：\n台灣 70,000 40,000\n美國 30,000 20,000\n合計 100,000 60,000\n"
    out = trr.extract_regions(text, _expected(y2025=100_000.0, y2024=60_000.0))
    assert out["status"] == "ok" and [r[0] for r in out["years"][2025]["regions"]] == ["台灣", "美國"]


def test_both_bases_written_in_the_section_is_its_own_word() -> None:
    basis, quotes = trr.revenue_basis("收入依客戶所在地區分，另依營運地點列示部門資訊。")
    assert basis == "both_found" and len(quotes) == 2
    assert trr.revenue_basis("地區別資訊如下：")[0] == "unstated"


def test_every_heading_is_tried_not_only_the_first() -> None:
    """2026-10-14 欣興：收入附註先有一句「地區別資訊如下」接一張年份當列、地區當欄的表；部門資訊那一節的地區表在三千字以外。"""
    text = ("地區別資訊如下：\n部門依營運地點管理。\n114年度 台灣 亞洲 合計\n合約收入 60,000$ 40,000$ 100,000$\n" + "其他說明文字。\n" * 600
            + "地區別資訊\n本集團地區別資訊如下：\n收入以客戶所在地國家為基礎歸類。\n台灣 60,000 30,000\n亞洲 40,000 25,000\n"
              "合計 100,000 55,000\n")
    out = trr.extract_regions(text, _expected(y2025=100_000.0, y2024=55_000.0))
    assert out["status"] == "ok" and out["years"][2024]["regions"] == [["台灣", 30_000], ["亞洲", 25_000]]
    assert out["basis"] == "customer_location"                        # 依什麼分只看收下的那一節


def test_stacked_tables_are_split_at_the_total_row() -> None:
    text = ("地區別資訊\n台灣 70,000 40,000\n美國 30,000 20,000\n合計 100,000 60,000\n"
            "台灣 9,000 8,000\n美國 1,000 900\n合計 10,000 8,900\n")
    out = trr.extract_regions(text, _expected(y2025=100_000.0, y2024=60_000.0))
    assert out["status"] == "ok" and out["years"][2025]["regions"] == [["台灣", 70_000], ["美國", 30_000]]


def _db() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


def _ok(year_total: int = 132_000) -> dict:
    return {"status": "ok", "reason": None, "basis": "customer_location", "basis_quotes": ["收入以客戶所在地國家為基礎歸類"],
            "years": {2025: {"regions": [["亞洲", year_total - 32_000], ["美洲", 32_000]], "total": year_total,
                             "monthly_total": year_total},
                      2024: {"regions": [["亞洲", 60_000], ["美洲", 11_000]], "total": 71_000, "monthly_total": 71_000}}}


def _write(conn, result, *, fetched: str, ticker: str = "9999.TW", report_year: int = 2025, uploaded: str | None = "2026-03-10"):
    trr.append_region_revenue(conn, trr.build_row(ticker, report_year, result, filename=f"{report_year}04_9999_AI1.pdf",
                                                  uploaded_on=uploaded, fetched_at=fetched))


def test_the_same_result_refetched_only_moves_fetched_at_so_a_b_a_reads_a() -> None:
    conn = _db()
    a, b = _ok(), {"status": "total_mismatch", "reason": "加起來不等於合計", "years": {}, "basis": "unstated", "basis_quotes": []}
    _write(conn, a, fetched="2026-10-14T01:00:00+00:00")
    _write(conn, b, fetched="2026-10-14T02:00:00+00:00")
    _write(conn, a, fetched="2026-10-14T03:00:00+00:00")
    assert conn.execute("SELECT COUNT(*) FROM tw_region_revenue_observations").fetchone()[0] == 2
    out = trr.region_revenue(conn, "9999.TW", as_of=date(2026, 10, 14))
    assert out["status"] == "ok" and out["years"][2025]["total"] == 132_000 and out["basis"] == "customer_location"


def test_nothing_is_seen_before_the_filing_and_the_latest_report_wins() -> None:
    conn = _db()
    _write(conn, _ok(), fetched="2026-10-14T01:00:00+00:00", report_year=2025, uploaded="2026-03-10")
    early = trr.region_revenue(conn, "9999.TW", as_of=date(2026, 3, 9))
    assert early["status"] == "not_yet_available" and "2026-03-10" in early["reason"]
    assert trr.region_revenue(conn, "9999.TW", as_of=date(2026, 3, 10))["status"] == "ok"
    older = {**_ok(), "years": {2024: _ok()["years"][2024]}}
    _write(conn, older, fetched="2026-10-14T01:00:00+00:00", report_year=2024, uploaded=None)   # 上傳時間解析不到：法定期限
    assert trr.region_revenue(conn, "9999.TW", as_of=date(2025, 12, 31))["report_year"] == 2024
    assert trr.region_revenue(conn, "9999.TW", as_of=date(2026, 4, 1))["report_year"] == 2025
    assert trr.region_revenue(conn, "8888.TW") is None
    assert trr.region_revenue(sqlite3.connect(":memory:"), "9999.TW") is None              # 表還沒建＝還沒有觀測


def test_rows_carry_the_filing_date_and_unregistered_words_are_refused() -> None:
    row = trr.build_row("9999.TW", 2025, _ok(), filename="f.pdf", uploaded_on=None, fetched_at="t")
    assert row["available_on"] == "2026-03-31" and row["available_on_basis"] == "statutory_deadline_only"
    assert trr.build_row("9999.TW", 2025, _ok(), filename="f.pdf", uploaded_on="2026-03-10",
                         fetched_at="t")["available_on_basis"] == "filing_metadata"
    with pytest.raises(trr.RegionRevenueError):
        trr.append_region_revenue(_db(), {**row, "check_status": "looks_fine"})
    with pytest.raises(trr.RegionRevenueError):
        trr.append_region_revenue(_db(), {**row, "revenue_basis": "customer"})


def test_monthly_totals_need_twelve_months_and_take_the_last_fetched_correction() -> None:
    conn = _db()
    for year in (2025, 2024):
        for month in range(1, 13):
            for fetched, revenue in (("2026-02-01", 1_000), ("2026-01-01", 999)):  # 較晚抓的那一列先寫進去：要靠排序不靠寫入順序
                conn.execute("INSERT INTO monthly_revenue_observations (observation_id, ticker, market, company_code, data_month, "
                             "revenue_current, currency, unit_scale, disclosure_deadline, published_at_basis, source, fetched_at, "
                             "payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (f"m{year}{month}{fetched}", "9999.TW", "twse", "9999", f"{year}-{month:02d}", revenue, "TWD", 1000,
                              "d", "b", "s", fetched, f"d{year}{month}{fetched}"))
    conn.execute("DELETE FROM monthly_revenue_observations WHERE data_month = '2024-01'")      # 2024 只剩十一個月
    totals = trr.monthly_totals(conn, "9999.TW", (2025, 2024))
    assert totals == {2025: 12_000.0, 2024: None}


def test_the_page_block_divides_by_the_reports_own_total_and_says_the_basis() -> None:
    found = trr.region_revenue(_seeded(), "9999.TW", as_of=date(2026, 10, 14))
    block = region_mix(found)
    assert block["field"] == REGION_FIELD and block["label"] == "地區"
    assert block["note"].startswith("依客戶所在地分") and "年報原文：「收入以客戶所在地國家為基礎歸類」" in block["note"]
    latest = block["points"][-1]
    assert latest["period"] == "2025 年度" and "2025 年度財報" in latest["source_ref"]
    assert latest["parts"][0] == {"name": "亞洲", "share": 100_000 / 132_000, "prev_share": 60_000 / 71_000}
    operating = region_mix({**found, "basis": "operating_location", "basis_quotes": []})
    assert "不是客戶在哪" in operating["note"]


def _seeded() -> sqlite3.Connection:
    conn = _db()
    _write(conn, _ok(), fetched="2026-10-14T01:00:00+00:00")
    return conn


def test_the_reader_only_adds_regions_for_taiwan_and_segment_absence_stays() -> None:
    conn = _seeded()
    tw = revenue_mix(conn, "9999.TW", as_of=date(2026, 10, 14))
    assert tw["regions"]["field"] == REGION_FIELD and "regions" not in tw["absences"]
    assert "占比" in tw["absences"]["shares"]["reason"]             # 地區有值，分部占比的缺席照印（不混成同一種）
    us = revenue_mix(conn, "AAPL")
    assert us["regions"] is None and "regions" not in us["absences"]
    missing = revenue_mix(conn, "8888.TWO")
    assert missing["absences"]["regions"]["kind"] == "not_yet_recorded"
    _write(conn, {"status": "total_mismatch", "reason": "加起來不等於合計", "years": {}, "basis": "unstated",
                  "basis_quotes": []}, fetched="2026-10-14T05:00:00+00:00", ticker="7777.TW")
    failed = revenue_mix(conn, "7777.TW", as_of=date(2026, 10, 14))
    assert failed["absences"]["regions"] == {"kind": "capability_absent", "reason": "加起來不等於合計"}


def test_the_page_contract_counts_regions_as_a_value() -> None:
    mix = {"shares": [], "regions": {"field": REGION_FIELD}, "customers": None, "backlog": None}
    extra = page_extra_for("X", None, revenue_mix=mix)
    assert extra["revenue_mix"] == [REGION_FIELD]
    rows = {r["element"]: r for r in ps.fill_table({}, extra=extra)}
    assert rows["B3.revenue_mix"]["state"] == "value"


def _body(name: str) -> str:
    start = APP.index(f"function {name}(")
    nxt = re.search(r"\n(?:async )?function |\nconst [A-Z_]+ =", APP[start + 10:])
    return APP[start: start + 10 + (nxt.start() if nxt else len(APP))]


def test_the_front_end_draws_regions_with_the_same_box_and_prints_the_basis() -> None:
    fig = _body("mixFigures")
    for copied in ("mix.regions", "s.note", "mix.absences.regions"):
        assert copied in fig, copied
    assert "mix.regions" in _body("mixDetail")


def test_the_heartbeat_line_counts_what_is_missing_behind_or_refused(monkeypatch) -> None:
    """一年一次、不排程：心跳每天印有幾檔有值、最新年度、沒收的、一筆都沒有的、落後法定期限的（L14：會自己出現的計數器）。"""
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
    monkeypatch.setattr("engine_c.monthly_revenue.registry_taiwan_tickers", lambda: ["9999.TW", "7777.TW", "8888.TWO"])
    now = datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)
    assert "**一筆都沒有**" in hb._tw_region_revenue_line(now=now) and "--year 2025" in hb._tw_region_revenue_line(now=now)
    _write(conn, _ok(), fetched="2026-10-14T01:00:00+00:00")
    _write(conn, {"status": "total_mismatch", "reason": "加起來不等於合計", "years": {}, "basis": "unstated", "basis_quotes": []},
           fetched="2026-10-14T01:00:00+00:00", ticker="7777.TW")
    line = hb._tw_region_revenue_line(now=now)
    assert "1/3 檔有值" in line and "最新 2025 年度" in line and "7777.TW（total_mismatch）" in line
    assert "**1 檔一筆都沒有**：8888.TWO" in line and "落後" in line
    later = hb._tw_region_revenue_line(now=datetime(2027, 4, 2, tzinfo=timezone.utc))
    assert "2026 年度年報已過期限" in later                              # 次年 3/31 過了還是 2025 年度＝落後


def test_the_parser_never_guesses_from_column_order_alone() -> None:
    """兩年營收都對不上（例：月營收缺了一年）時，不得因為「第一欄通常是今年」就收。"""
    out = trr.extract_regions(TWO_COLUMNS, _expected(y2025=None, y2024=71_000.0))
    assert sorted(out["years"]) == [2024] and json.dumps(out["years"][2024]["regions"], ensure_ascii=False).count("亞洲") == 1
