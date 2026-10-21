"""日韓財報來源 S3（2026-10-21；使用者「日韓 AAA」）：韓國 OpenDART 定期報告 → fundamental_history。

守：①반기／3 分期的 thstrm 是單季（累計在 add）；第 1 分期兩欄必須相等；②IS 與 CIS 給不同的數 → 拒寫；③第四季＝年度−9 個月累計，
filed 取兩者較晚；④可知日＝list.json 裡那個 rcept_no 的接收日，對不到就拒寫；原件比更正版早知道的期數照數印（late_known）；
⑤股數只算普通股 distb_stock_co，並核對發行−庫藏（優先股不加，計畫 Q2 A）；⑥901（個人資料保留期滿）整輪中止並說要重新同意；
⑦key 不得出現在例外、報告、快取；⑧12 月決算以外的公司給具名結局，不猜報告代碼。fixture 全部在這裡合成。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

import pytest

from engine_c import dart_history as dh
from engine_c import history_backfill as hb
from fetchers import opendart as fo

FETCHED = "2026-10-21T00:00:00+00:00"
KEY = "DARTSECRET0123456789abcdefABCDEF0123"
TODAY = date(2026, 10, 21)


def fs_body(rcept, *, revenue=("100", "250"), oi=("10", "25"), cash="70", sj=("IS",), extra=()):
    rows = []
    for div in sj:
        rows.append({"rcept_no": rcept, "sj_div": div, "account_id": "ifrs-full_Revenue", "thstrm_amount": revenue[0],
                     "thstrm_add_amount": revenue[1], "currency": "KRW"})
        rows.append({"rcept_no": rcept, "sj_div": div, "account_id": "dart_OperatingIncomeLoss", "thstrm_amount": oi[0],
                     "thstrm_add_amount": oi[1], "currency": "KRW"})
    rows.append({"rcept_no": rcept, "sj_div": "BS", "account_id": "ifrs-full_CashAndCashEquivalents",
                 "thstrm_amount": cash, "thstrm_add_amount": None, "currency": "KRW"})
    rows.append({"rcept_no": rcept, "sj_div": "BS", "account_id": "ifrs-full_ShorttermBorrowings",
                 "thstrm_amount": "5", "thstrm_add_amount": None, "currency": "KRW"})
    return {"status": "000", "list": rows + list(extra)}


def shares_body(rcept, end, *, common=("5,846,278,608", "82,086,705", "5,764,191,903")):
    issued, treasury, distb = common
    return {"status": "000", "list": [
        {"rcept_no": rcept, "se": "보통주", "istc_totqy": issued, "tesstk_co": treasury, "distb_stock_co": distb,
         "stlm_dt": end},
        {"rcept_no": rcept, "se": "우선주", "istc_totqy": "802,371,203", "tesstk_co": "-",
         "distb_stock_co": "802,371,203", "stlm_dt": end},
        {"rcept_no": rcept, "se": "합계", "istc_totqy": "6,648,649,811", "tesstk_co": "82,086,705",
         "distb_stock_co": "6,566,563,106", "stlm_dt": end},
        {"rcept_no": rcept, "se": "비고", "istc_totqy": "-", "tesstk_co": "-", "distb_stock_co": "-", "stlm_dt": end}]}


def build(kind="H1", year=2026, fs=None, shares=None, filed_of=None):
    rcept = "20260814003699"
    _start, end = dh.period_of(kind, year)
    return dh.build_report_rows(fs or fs_body(rcept), shares if shares is not None else shares_body(rcept, end.isoformat()),
                                ticker="005930.KS", kind=kind, year=year,
                                filed_of=filed_of if filed_of is not None else {rcept: "20260814"}, fetched_at=FETCHED)


def by_metric(result):
    return {r["metric"]: r for r in result.rows}


def test_report_names_parse_with_correction_prefixes_and_map_to_periods() -> None:
    assert dh.parse_report_name("[기재정정]사업보고서 (2020.12)") == ("사업보고서", 2020, 12)
    assert dh.parse_report_name("반기보고서 (2026.06)") == ("반기보고서", 2026, 6)
    assert dh.parse_report_name("주요사항보고서(자기주식취득결정)") is None
    assert dh.period_of("H1", 2026) == (date(2026, 4, 1), date(2026, 6, 30))
    assert dh.period_of("FY", 2025) == (date(2025, 1, 1), date(2025, 12, 31))


def test_a_half_year_report_gives_the_second_quarter_alone_and_only_common_shares() -> None:
    result = build()
    assert result.rejected == []
    rows = by_metric(result)
    assert rows["revenue_quarter"]["value"] == 100 and rows["operating_income_quarter"]["value"] == 10   # 不是 6 個月累計
    assert (rows["revenue_quarter"]["period_start"], rows["revenue_quarter"]["period_end"]) == ("2026-04-01", "2026-06-30")
    assert rows["revenue_quarter"]["filed"] == "2026-08-14" and rows["revenue_quarter"]["form"] == "DART-11012"
    assert rows["revenue_quarter"]["source"] == hb.SOURCE_DART and rows["revenue_quarter"]["currency"] == "KRW"
    assert rows["cash"]["value"] == 70 and "total_debt" not in rows          # 只有分項借款：不加總（計畫 Q3 A）
    shares = rows["shares_outstanding_cover"]
    assert shares["value"] == 5_764_191_903 and shares["source"] == hb.SOURCE_DART_SHARES   # 三星優先股不加
    assert result.missing == []


def test_the_first_quarter_columns_must_agree_or_nothing_is_written() -> None:
    ok = build(kind="Q1", fs=fs_body("20260814003699", revenue=("100", "100"), oi=("10", "10")),
               shares=shares_body("20260814003699", "2026-03-31"))
    assert by_metric(ok)["revenue_quarter"]["value"] == 100
    bad = build(kind="Q1", fs=fs_body("20260814003699", revenue=("100", "160"), oi=("10", "10")),
                shares=shares_body("20260814003699", "2026-03-31"))
    assert "revenue_quarter" not in by_metric(bad) and any("語意" in r["reason"] for r in bad.rejected)


def test_income_statement_and_comprehensive_statement_disagreeing_rejects_the_metric() -> None:
    fs = fs_body("20260814003699", sj=("IS",))
    fs["list"].append({"rcept_no": "20260814003699", "sj_div": "CIS", "account_id": "ifrs-full_Revenue",
                       "thstrm_amount": "101", "thstrm_add_amount": "251", "currency": "KRW"})
    result = build(fs=fs)
    assert "revenue_quarter" not in by_metric(result) and "operating_income_quarter" in by_metric(result)
    assert [r["metric"] for r in result.rejected] == ["revenue"]
    agree = build(fs=fs_body("20260814003699", sj=("IS", "CIS")))
    assert by_metric(agree)["revenue_quarter"]["value"] == 100


def test_a_receipt_missing_from_the_list_or_with_a_wrong_date_is_refused() -> None:
    missing = build(filed_of={})
    assert missing.rows == [] and any("對不到" in r["reason"] for r in missing.rejected)
    wrong = build(filed_of={"20260814003699": "20260815"})
    assert wrong.rows == [] and any("前 8 碼" in r["reason"] for r in wrong.rejected)


@pytest.mark.parametrize("se, common", [
    ("보통주", True), ("보통주식", True), ("의결권이 있는\n주식(보통주)", True), ("의결권이 있는주식(보통주)", True),
    ("우선주", False), ("의결권이 없는\n주식(우선주)", False), ("배당우선\n주식\n(1종 종류주식)", False), ("합계", False),
    ("비고", False)])
def test_the_common_share_row_is_recognised_in_every_spelling_seen(se, common) -> None:
    """2026-10-21 實測四種寫法（三星、HD 현대일렉트릭、삼성전기）；只認 보통주 那一個寫法時兩檔股數整段缺席。"""
    assert dh.is_common_share(se) is common


def test_shares_must_reconcile_and_sit_at_the_period_end() -> None:
    bad = build(shares=shares_body("20260814003699", "2026-06-30", common=("100", "10", "95")))
    assert "shares_outstanding_cover" not in by_metric(bad)
    late = build(shares=shares_body("20260814003699", "2026-07-31"))
    assert "shares_outstanding_cover" not in by_metric(late) and any("結算日" in r["reason"] for r in late.rejected)


def test_the_fourth_quarter_is_the_year_minus_nine_months_filed_when_both_were_known() -> None:
    q3 = build(kind="Q3", year=2025, fs=fs_body("20251114001805", revenue=("24", "64"), oi=("11", "28")),
               shares=shares_body("20251114001805", "2025-09-30"), filed_of={"20251114001805": "20251114"})
    fy = build(kind="FY", year=2025, fs=fs_body("20260310000111", revenue=("90", ""), oi=("40", "")),
               shares=shares_body("20260310000111", "2025-12-31"), filed_of={"20260310000111": "20260310"})
    assert "revenue_annual" not in by_metric(fy)              # 年度只給推算用，不寫
    q4, missing = dh.derive_fourth_quarter(q3.internal + fy.internal)
    assert missing == []
    rev = next(r for r in q4 if r["metric"] == "revenue_quarter")
    assert (rev["value"], rev["period_start"], rev["period_end"], rev["filed"]) == (26, "2025-10-01", "2025-12-31", "2026-03-10")
    assert rev["derived"].startswith("FY−9M：20260310000111") and rev["accession"] == "20260310000111"
    lonely, gone = dh.derive_fourth_quarter(fy.internal)
    assert lonely == [] and len(gone) == 2
    # 3 分期在年報之後才更正（DART 只回最新更正版）：第四季要等兩者都知道了才算知道
    q3_late = build(kind="Q3", year=2025, fs=fs_body("20260401000333", revenue=("24", "64"), oi=("11", "28")),
                    shares=shares_body("20260401000333", "2025-09-30"), filed_of={"20260401000333": "20260401"})
    late, _ = dh.derive_fourth_quarter(q3_late.internal + fy.internal)
    assert {r["filed"] for r in late} == {"2026-04-01"}
    assert {r["accession"] for r in late} == {"20260401000333"}       # 主鍵跟著較晚那一份（R2-S3 #1）


def test_a_third_quarter_corrected_after_the_annual_report_writes_a_new_fourth_quarter() -> None:
    """R2-S3 #1：3 分期事後更正（新 rcept_no、9 個月累計改了）、年報沒動——新的第四季不得與舊的同鍵被靜默丟掉；
    as-of 更正日之前讀舊值、之後讀新值。"""
    def rows_for(q3_rcept, q3_dt, nine):
        q3 = build(kind="Q3", year=2025, fs=fs_body(q3_rcept, revenue=("24", nine), oi=("11", "28")),
                   shares=shares_body(q3_rcept, "2025-09-30"), filed_of={q3_rcept: q3_dt})
        fy = build(kind="FY", year=2025, fs=fs_body("20260310000111", revenue=("90", ""), oi=("40", "")),
                   shares=shares_body("20260310000111", "2025-12-31"), filed_of={"20260310000111": "20260310"})
        q4, _ = dh.derive_fourth_quarter(q3.internal + fy.internal)
        return [r for r in q4 if r["metric"] == "revenue_quarter"]

    conn = sqlite3.connect(":memory:")
    conn.executescript(hb._SQLITE_DDL)
    first = rows_for("20251114001805", "20251114", "64")
    second = rows_for("20260601000999", "20260601", "70")
    assert hb.insert_fundamentals(conn, first) == 1 and hb.insert_fundamentals(conn, second) == 1
    from engine_c.history import fundamental_series

    assert fundamental_series(conn, "005930.KS", "revenue_quarter", as_of="2026-05-31")[-1]["value"] == 26.0
    assert fundamental_series(conn, "005930.KS", "revenue_quarter", as_of="2026-06-01")[-1]["value"] == 20.0


def test_replace_never_wipes_a_ticker_when_this_run_built_no_rows(tmp_path) -> None:
    """R2-S3 #2：清單意外回空、一列都沒建出來時 --replace 不得先刪光再補 0 筆。"""
    conn = sqlite3.connect(":memory:")
    conn.executescript(hb._SQLITE_DDL)
    conn.execute("INSERT INTO fundamental_history VALUES ('005930.KS','cash',NULL,'2025-12-31','2026-03-10','R',"
                 "'DART-11011',1,'KRW',1,NULL,'t',?,?)", (hb.SOURCE_DART, FETCHED))
    empty = {"tickers": {"005930.KS": {"rows": [], "report": {}}}}
    result = dh.write(conn, empty, replace=True)
    assert result["replace_skipped_empty"] == ["005930.KS"]
    assert conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# 呼叫端
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, body=None, status=200, content=b""):
        self.status_code, self._body, self.content = status, body, content

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


def _client(get):
    clock = iter(range(0, 10_000, 10))
    return fo.Client(KEY, sleep=lambda s: None, clock=lambda: next(clock), get=get)


def test_consent_expiry_aborts_the_run_with_the_reason_and_no_data_is_not_an_error() -> None:
    expired = _client(lambda url, params=None, **_kw: _Resp({"status": "901", "message": "개인정보 보유기간 만료"}))
    with pytest.raises(fo.DartUnavailable) as exc:
        expired.single_account_all("00126380", 2026, "11012")
    assert exc.value.outcome == "consent_expired" and exc.value.aborts_run and "重新同意" in str(exc.value)
    empty = _client(lambda url, params=None, **_kw: _Resp({"status": "013", "message": "조회된 데이타가 없습니다."}))
    assert empty.single_account_all("00126380", 2026, "11014")["list"] == []
    missing = _client(lambda url, params=None, **_kw: _Resp({"status": "014", "message": "파일이 존재하지 않습니다"}))
    with pytest.raises(fo.DartUnavailable) as gone:
        missing.share_totals("00126380", 2026, "11014")
    assert gone.value.outcome == "file_missing" and not gone.value.aborts_run


def test_the_key_never_leaks_through_exceptions_or_messages() -> None:
    def boom(url, params=None, **_kw):
        raise ConnectionError(f"Max retries exceeded with url: {url}?crtfc_key={params['crtfc_key']}")

    with pytest.raises(fo.DartUnavailable) as exc:
        _client(boom).periodic_reports("00126380", "20210101", "20261021")
    assert KEY not in str(exc.value) and fo.REDACTED in str(exc.value) and exc.value.__suppress_context__
    echo = _client(lambda url, params=None, **_kw: _Resp({"status": "010", "message": f"bad key {params['crtfc_key']}"}))
    with pytest.raises(fo.DartUnavailable) as auth:
        echo.single_account_all("00126380", 2026, "11012")
    assert KEY not in str(auth.value) and auth.value.outcome == "auth_failed"


def test_corp_codes_with_zero_or_many_matches_are_refused() -> None:
    rows = [{"corp_code": "00126380", "stock_code": "005930"}, {"corp_code": "1", "stock_code": "111111"},
            {"corp_code": "2", "stock_code": "111111"}, {"corp_code": "3", "stock_code": ""}]
    assert fo.corp_code_for("005930", rows) == "00126380"
    for code in ("111111", "999999"):
        with pytest.raises(LookupError):
            fo.corp_code_for(code, rows)


# ---------------------------------------------------------------------------
# 編排（假的 client）
# ---------------------------------------------------------------------------

class FakeClient:
    def __init__(self, listed, fs, shares, *, fail_on=None):
        self.listed, self.fs, self.shares, self.fail_on, self.calls = listed, fs, shares, fail_on, 0

    def periodic_reports(self, corp, begin, end):
        self.calls += 1
        return self.listed

    def single_account_all(self, corp, year, code):
        self.calls += 1
        if self.fail_on == (year, code):
            raise fo.DartUnavailable(f"status 901（consent_expired）：{fo.CONSENT_EXPIRED_HINT}", outcome="consent_expired")
        return self.fs.get((year, code), {"status": "013", "list": []})

    def share_totals(self, corp, year, code):
        self.calls += 1
        return self.shares.get((year, code), {"status": "013", "list": []})


CORP_ROWS = [{"corp_code": "00126380", "stock_code": "005930"}]


def _scenario():
    listed = [
        {"report_nm": "분기보고서 (2025.09)", "rcept_no": "20251114001805", "rcept_dt": "20251114"},
        {"report_nm": "사업보고서 (2025.12)", "rcept_no": "20260310000111", "rcept_dt": "20260310"},
        {"report_nm": "[기재정정]사업보고서 (2025.12)", "rcept_no": "20260318000222", "rcept_dt": "20260318"},
        {"report_nm": "반기보고서 (2026.06)", "rcept_no": "20260814003699", "rcept_dt": "20260814"},
        {"report_nm": "분기보고서 (2026.09)", "rcept_no": "20261114000001", "rcept_dt": "20261114"},  # 還沒交：013
    ]
    fs = {(2025, "11014"): fs_body("20251114001805", revenue=("24", "64"), oi=("11", "28")),
          (2025, "11011"): fs_body("20260318000222", revenue=("90", ""), oi=("40", "")),   # 只回最新更正版
          (2026, "11012"): fs_body("20260814003699")}
    shares = {(2025, "11014"): shares_body("20251114001805", "2025-09-30"),
              (2025, "11011"): shares_body("20260318000222", "2025-12-31"),
              (2026, "11012"): shares_body("20260814003699", "2026-06-30")}
    return listed, fs, shares


def test_a_run_writes_quarters_derives_the_fourth_and_counts_late_known_corrections(tmp_path) -> None:
    listed, fs, shares = _scenario()
    out = dh.collect(FakeClient(listed, fs, shares), tickers=["005930.KS"], today=TODAY, cache_dir=tmp_path,
                     corp_rows=CORP_ROWS, fetched_at=FETCHED)
    report = out["tickers"]["005930.KS"]["report"]
    assert report["reports_listed"] == 4 and report["reports_used"] == 3 and report["skipped"] == {"no_data": 1}
    rows = out["tickers"]["005930.KS"]["rows"]
    quarters = sorted((r["period_end"], r["value"], r["filed"]) for r in rows if r["metric"] == "revenue_quarter")
    assert quarters == [("2025-09-30", 24.0, "2025-11-14"), ("2025-12-31", 26.0, "2026-03-18"),
                        ("2026-06-30", 100.0, "2026-08-14")]
    # 年報原件 03-10、更正版 03-18：只拿得到更正版——晚知道 8 天，照數印
    assert report["late_known"] == [{"report": "2025 FY", "original_rcept_dt": "20260310", "used_rcept_dt": "20260318"}]
    assert report["q4_derived"] == 2 and report["rejected"] == []
    again = FakeClient(listed, fs, shares)
    dh.collect(again, tickers=["005930.KS"], today=TODAY, cache_dir=tmp_path, corp_rows=CORP_ROWS, fetched_at=FETCHED)
    assert again.calls == 3            # 清單＋回 013 的那一期（不當定案，再問一次）；其餘報告走快取


def test_a_consent_expiry_mid_run_stops_and_counts_what_was_not_fetched(tmp_path) -> None:
    listed, fs, shares = _scenario()
    out = dh.collect(FakeClient(listed, fs, shares, fail_on=(2025, "11011")), tickers=["005930.KS"], today=TODAY,
                     cache_dir=tmp_path, corp_rows=CORP_ROWS, fetched_at=FETCHED)
    assert "重新同意" in out["run"]["aborted"] and out["run"]["reports_unfetched"] == 3


def test_a_non_december_fiscal_year_is_a_named_outcome(tmp_path) -> None:
    listed = [{"report_nm": "사업보고서 (2025.03)", "rcept_no": "20250620000001", "rcept_dt": "20250620"}]
    out = dh.collect(FakeClient(listed, {}, {}), tickers=["005930.KS"], today=TODAY, cache_dir=tmp_path,
                     corp_rows=CORP_ROWS, fetched_at=FETCHED)
    assert out["tickers"]["005930.KS"]["report"]["outcome"] == "non_december_fiscal_year"
    assert out["tickers"]["005930.KS"]["rows"] == []


def test_the_key_never_reaches_the_report_or_the_caches(tmp_path) -> None:
    listed, fs, shares = _scenario()

    def get(url, params=None, **_kw):
        path = url.rsplit("/", 1)[-1]
        if path == "list.json":
            return _Resp({"status": "000", "total_page": 1, "list": listed})
        key = (int(params["bsns_year"]), params["reprt_code"])
        if path == "fnlttSinglAcntAll.json":
            if key == (2026, "11012"):
                raise ConnectionError(f"reset {url}?crtfc_key={params['crtfc_key']}")
            return _Resp(fs.get(key, {"status": "013", "message": "없음"}))
        return _Resp(shares.get(key, {"status": "013", "message": "없음"}))

    out = dh.collect(_client(get), tickers=["005930.KS"], today=TODAY, cache_dir=tmp_path, corp_rows=CORP_ROWS,
                     fetched_at=FETCHED)
    assert out["run"]["failed"] and fo.REDACTED in out["run"]["failed"][0]["reason"]
    assert KEY not in json.dumps(out, ensure_ascii=False, default=str)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert KEY not in path.read_text(encoding="utf-8"), path


def test_written_rows_make_a_korean_quarterly_filer_and_replace_touches_only_dart(tmp_path) -> None:
    listed, fs, shares = _scenario()
    collected = dh.collect(FakeClient(listed, fs, shares), tickers=["005930.KS"], today=TODAY, cache_dir=tmp_path,
                           corp_rows=CORP_ROWS, fetched_at=FETCHED)
    conn = sqlite3.connect(":memory:")
    conn.executescript(hb._SQLITE_DDL)
    conn.execute("INSERT INTO fundamental_history VALUES ('005930.KS','cash',NULL,'2020-12-31','2021-03-10','SEC',"
                 "'20-F',1,'USD',1,NULL,'t',?,?)", (hb.SOURCE_EDGAR, FETCHED))
    result = dh.write(conn, collected, replace=True)
    assert result["outcome"] == "written" and result["rows_new"]["005930.KS"] > 0
    assert dh.write(conn, collected)["rows_new"]["005930.KS"] == 0
    assert conn.execute("SELECT COUNT(*) FROM fundamental_history WHERE source = ?", (hb.SOURCE_EDGAR,)).fetchone()[0] == 1
    assert hb.filer_class(conn, "005930.KS", today=TODAY)[0] == "kr_quarterly"
    from engine_c.history import fundamental_series

    assert fundamental_series(conn, "005930.KS", "revenue_quarter", as_of="2026-03-17")[-1]["period_end"] == "2025-09-30"
    assert fundamental_series(conn, "005930.KS", "revenue_quarter", as_of="2026-03-18")[-1]["value"] == 26.0


def test_freshness_uses_45_days_for_quarters_and_90_for_the_annual_report() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(hb._SQLITE_DDL)
    conn.execute("INSERT INTO fundamental_history VALUES ('005930.KS','revenue_quarter','2026-04-01','2026-06-30',"
                 "'2026-08-14','R1','DART-11012',1,'KRW',1,NULL,'t',?,?)", (hb.SOURCE_DART, FETCHED))
    assert dh.filing_freshness(conn, ["005930.KS"], today=date(2026, 11, 14))["lagging"] == []
    assert dh.filing_freshness(conn, ["005930.KS"], today=date(2026, 11, 15))["lagging"] == [
        "005930.KS（2026-09-30 那一期，期限 2026-11-14）"]
    conn.execute("INSERT INTO fundamental_history VALUES ('005930.KS','revenue_quarter','2026-07-01','2026-09-30',"
                 "'2026-11-13','R2','DART-11014',1,'KRW',1,NULL,'t',?,?)", (hb.SOURCE_DART, FETCHED))
    got = dh.filing_freshness(conn, ["005930.KS", "000660.KS"], today=date(2027, 3, 31))
    assert got["lagging"] == [] and got["empty"] == ["000660.KS"] and got["latest"] == "2026-09-30"
