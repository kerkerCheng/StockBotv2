"""日韓財報來源 S2（2026-10-21；使用者「日韓 AAA」）：日本 EDINET 半期・有價證券報告書 → fundamental_history。

守：①期間與 context 由 DEI 決定，docType 不參與（6594 S100UOHJ）；②只收不帶後綴的 context（分部資料帶 member）；
③白名單元素對同一期給出不同的數 → 那個指標拒寫；④股數只扣自己保有（相互保有不扣；3110：1,144,700 ≠ 1,142,300），
`－`＝0、那一行不在＝拒寫；⑤下半年＝年度−當時已知的上半年，filed＝觸發它的那份（T 之後才交的訂正不得用）；
⑥可知日＝submitDateTime，不是抓取日；⑦key 不得出現在任何例外訊息、報告、快取；⑧限流退避後中止、沒掃的日期照數；
⑨証券コード 0 筆或多筆就拒收；⑩CHECK 沒遷移就整輪不寫。fixture 全部在這裡合成（原檔 PDL1.0、不進 repo）。
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import zipfile
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from engine_c import edinet_history as eh
from engine_c import history_backfill as hb
from fetchers import edinet as fe

FETCHED = "2026-10-21T00:00:00+00:00"
KEY = "SECRETKEY0123456789abcdef"
SHARES = eh.SHARES_ISSUED
OWN = "_OrdinarySharesTreasurySharesSharesWithFullVotingRightsTreasurySharesEtcMember"
RECIPROCAL = "_OrdinarySharesReciprocalHoldingSharesWithFullVotingRightsTreasurySharesEtcMember"


def _csv(rows) -> bytes:
    lines = ["\t".join(f'"{c}"' for c in fe.CSV_COLUMNS)]
    for element, context, consolidation, unit, value in rows:
        lines.append("\t".join(f'"{c}"' for c in (element, "label", context, "当期", consolidation, "期間", unit, "", value)))
    return ("\n".join(lines) + "\n").encode("utf-16")


def make_zip(rows) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("XBRL_TO_CSV/jpaud-qrr-cc-001_E00542-000.csv",
                   _csv([("jppfs_cor:NetSales", "InterimDuration", "連結", "JPY", "1")]))  # 監査報告：不讀
        z.writestr("XBRL_TO_CSV/jpcrp040300-ssr-001_E00542-000_2025-09-30_01_2025-11-10.csv", _csv(rows))
    return buf.getvalue()


def dei(kind="HY", start="2025-04-01", end="2025-09-30", std="Japan GAAP", code="E00542", sec="31100",
        consolidated="true"):
    return [(f"jpdei_cor:{k}", "FilingDateInstant", "その他", "", v) for k, v in (
        ("TypeOfCurrentPeriodDEI", kind), ("CurrentFiscalYearStartDateDEI", start), ("CurrentPeriodEndDateDEI", end),
        ("AccountingStandardsDEI", std), ("WhetherConsolidatedFinancialStatementsArePreparedDEI", consolidated),
        ("EDINETCodeDEI", code), ("SecurityCodeDEI", sec))]


def hy_3110(revenue="57412000000", summary="57412000000", own="1142300", ctx=("InterimDuration", "InterimInstant"),
            **dei_kw):
    duration, instant = ctx
    return dei(**dei_kw) + [
        ("jppfs_cor:NetSales", duration, "連結", "JPY", revenue),
        ("jppfs_cor:NetSales", "Prior1" + duration, "連結", "JPY", "53051000000"),
        ("jppfs_cor:NetSales", duration + "_jpcrp040300-ssr_E00542-000ElectronicMaterialsBusinessReportableSegmentMember",
         "連結", "JPY", "29584000000"),
        ("jpcrp_cor:NetSalesSummaryOfBusinessResults", duration, "その他", "JPY", summary),
        ("jppfs_cor:OperatingIncome", duration, "連結", "JPY", "9454000000"),
        ("jppfs_cor:CashAndCashEquivalents", instant, "連結", "JPY", "29342000000"),
        ("jppfs_cor:CashAndCashEquivalents", "Prior1YearInstant", "連結", "JPY", "28387000000"),
        (SHARES, instant, "その他", "shares", "37723012"),
        (SHARES, instant + "_SharesWithRestrictedVotingRightsTreasurySharesEtcMember", "その他", "shares", "－"),
        *([(SHARES, instant + OWN, "その他", "shares", own)] if own is not None else []),
        (SHARES, instant + RECIPROCAL, "その他", "shares", "2400"),
        (eh.ISSUED_CROSS_CHECK, "FilingDateInstant", "その他", "shares", "37723012"),
        (eh.ISSUED_CROSS_CHECK, "FilingDateInstant_OrdinaryShareMember", "その他", "shares", "37723012"),
    ]


def build(rows, *, doc_type="160", filed=date(2025, 11, 10), code="E00542", ticker="3110.T"):
    doc = eh.extract(fe.parse_csv_zip(make_zip(rows)))
    return eh.build_doc_rows(doc, ticker=ticker, edinet_code=code, sec5=ticker[:4] + "0", doc_id="S100WZ3X",
                             doc_type=doc_type, filed=filed, fetched_at=FETCHED)


def by_metric(result):
    return {r["metric"]: r for r in result.rows}


# ---------------------------------------------------------------------------
# 一份書類 → 列
# ---------------------------------------------------------------------------

def test_a_half_year_report_gives_the_3110_numbers_and_ignores_segment_and_prior_contexts() -> None:
    skip, result = build(hy_3110())
    assert skip is None and result.rejected == []
    rows = by_metric(result)
    assert rows["revenue_half"]["value"] == 57_412_000_000 and rows["revenue_half"]["tag"] == "jppfs_cor:NetSales"
    assert (rows["revenue_half"]["period_start"], rows["revenue_half"]["period_end"]) == ("2025-04-01", "2025-09-30")
    assert rows["operating_income_half"]["value"] == 9_454_000_000
    assert rows["cash"]["value"] == 29_342_000_000 and rows["cash"]["period_start"] is None
    # 股數只扣自己保有株式：相互保有 2,400 不扣（扣「自己株式等合計」會得 36,578,312）
    assert rows["shares_outstanding_cover"]["value"] == 36_580_712
    assert rows["shares_outstanding_cover"]["currency"] == "shares"
    for row in result.rows:
        assert row["form"] == "EDINET-160" and row["source"] == hb.SOURCE_EDINET and row["filed"] == "2025-11-10"
        assert row["accession"] == "S100WZ3X" and row["currency"] in ("JPY", "shares")


def test_the_context_comes_from_dei_not_from_the_doc_type() -> None:
    """6594 S100UOHJ：列在 160（半期報告書），DEI 卻是 Q2、context 是 CurrentYTDDuration／CurrentQuarterInstant。"""
    rows = hy_3110(kind="Q2", ctx=("CurrentYTDDuration", "CurrentQuarterInstant"), start="2024-04-01", end="2024-09-30")
    skip, result = build(rows, doc_type="160")
    assert skip is None
    got = by_metric(result)
    assert got["revenue_half"]["value"] == 57_412_000_000 and got["shares_outstanding_cover"]["value"] == 36_580_712
    assert got["revenue_half"]["period_end"] == "2024-09-30"


def test_whitelisted_elements_that_disagree_reject_only_that_metric() -> None:
    skip, result = build(hy_3110(summary="57413000000"))
    assert skip is None
    rows = by_metric(result)
    assert "revenue_half" not in rows and "operating_income_half" in rows
    assert [r["metric"] for r in result.rejected] == ["revenue"]
    assert "不同的數" in result.rejected[0]["reason"]


def test_nil_own_treasury_is_zero_and_a_missing_own_treasury_line_rejects() -> None:
    _skip, nil = build(hy_3110(own="－"))
    assert by_metric(nil)["shares_outstanding_cover"]["value"] == 37_723_012          # 5016：明確為 0
    _skip, missing = build(hy_3110(own=None))
    assert "shares_outstanding_cover" not in by_metric(missing)
    assert any("不補 0" in r["reason"] for r in missing.rejected)


def test_a_cross_check_mismatch_or_another_share_class_rejects_the_shares() -> None:
    rows = [r if r[0] != eh.ISSUED_CROSS_CHECK else (*r[:4], "37723013") for r in hy_3110()]
    _skip, bad = build(rows)
    assert "shares_outstanding_cover" not in by_metric(bad)
    classes = hy_3110() + [(eh.ISSUED_CROSS_CHECK, "FilingDateInstant_ClassAPreferredSharesMember", "その他", "shares", "5")]
    _skip, multi = build(classes)
    assert "shares_outstanding_cover" not in by_metric(multi) and any("股類" in r["reason"] for r in multi.rejected)


@pytest.mark.parametrize("kw, outcome", [
    ({"kind": "Q1"}, "quarter_not_used"),
    ({"kind": "Q3"}, "quarter_not_used"),
    ({"kind": "XX"}, "unknown_period_type"),
    ({"std": "US GAAP"}, "unsupported_standard"),
    ({"consolidated": "false"}, "non_consolidated"),
    ({"start": "2025-01-01"}, "irregular_half"),
    ({"kind": "FY", "start": "2025-04-01", "end": "2025-12-31"}, "irregular_fiscal_year"),
])
def test_every_unusable_report_has_a_named_outcome(kw, outcome) -> None:
    skip, result = build(hy_3110(**kw))
    assert skip == outcome and result.rows == []


def test_a_dei_identity_mismatch_rejects_the_whole_report() -> None:
    skip, result = build(hy_3110(code="E99999"))
    assert skip is None and result.rows == [] and "INV-1" in result.rejected[0]["reason"]


# ---------------------------------------------------------------------------
# 下半年＝年度−上半年（PIT）
# ---------------------------------------------------------------------------

def _row(metric, start, end, filed, value, accn):
    return {"ticker": "6268.T", "metric": metric, "period_start": start, "period_end": end, "filed": filed,
            "accession": accn, "form": "EDINET-120", "value": value, "currency": "JPY", "unit_scale": 1, "derived": None,
            "tag": "jpigp_cor:NetSalesIFRS", "source": hb.SOURCE_EDINET, "fetched_at": FETCHED}


def test_the_second_half_uses_only_the_first_half_known_when_each_version_was_filed() -> None:
    rows = [_row("revenue_half", "2025-01-01", "2025-06-30", "2025-08-14", 100.0, "S100H1"),
            _row("revenue_annual", "2025-01-01", "2025-12-31", "2026-03-27", 250.0, "S100FY"),
            _row("revenue_half", "2025-01-01", "2025-06-30", "2026-09-30", 110.0, "S100H1A")]  # 年報之後才訂正上半年
    h2, missing = eh.derive_second_half(rows)
    assert missing == []
    assert [(r["filed"], r["value"], r["accession"]) for r in h2] == [("2026-03-27", 150.0, "S100FY"),
                                                                       ("2026-09-30", 140.0, "S100H1A")]
    assert all(r["period_start"] == "2025-07-01" and r["period_end"] == "2025-12-31" for r in h2)
    assert h2[0]["derived"].startswith("FY−H1：S100FY") and "S100H1（" in h2[0]["derived"]
    from shared.as_of import latest_known_by_period

    assert latest_known_by_period(h2, "2026-07-01")[date(2025, 12, 31)]["value"] == 150.0


def test_a_second_half_without_its_first_half_is_counted_not_estimated() -> None:
    rows = [_row("revenue_annual", "2024-04-01", "2025-03-31", "2025-06-20", 250.0, "S100FY")]
    h2, missing = eh.derive_second_half(rows)
    assert h2 == [] and len(missing) == 1 and "推不出來" in missing[0]["reason"]


def test_annual_rows_feed_the_derivation_but_are_never_written_and_the_window_applies() -> None:
    rows = [_row("revenue_half", "2025-01-01", "2025-06-30", "2025-08-14", 100.0, "S100H1"),
            _row("revenue_annual", "2025-01-01", "2025-12-31", "2026-03-27", 250.0, "S100FY"),
            _row("cash", None, "2019-12-31", "2020-03-27", 9.0, "S100OLD")]
    kept, info = eh.finalize_rows(rows, today=date(2026, 10, 21))
    assert sorted(r["metric"] for r in kept) == ["revenue_half", "revenue_half"]
    assert info["h2_derived"] == 1 and info["outside_window"] == 1


# ---------------------------------------------------------------------------
# 呼叫端：遮罩、節流、限流
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status=200, body=None, content=b"", ctype="application/json"):
        self.status_code, self._body, self.content = status, body, content
        self.headers = {"Content-Type": ctype}
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def _client(get, **kw):
    clock = iter(range(0, 10_000, 10))
    return fe.Client(KEY, sleep=lambda s: None, clock=lambda: next(clock), get=get, **kw)


def test_the_key_never_leaks_through_exceptions_or_error_bodies() -> None:
    def boom(url, params=None, **_kw):
        raise ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}?Subscription-Key={params['Subscription-Key']}")

    with pytest.raises(fe.EdinetUnavailable) as exc:
        _client(boom).list_documents(date(2025, 11, 10))
    assert KEY not in str(exc.value) and fe.REDACTED in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__

    def denied(url, params=None, **_kw):
        return _Resp(401, {"StatusCode": 401, "message": f"invalid key {params['Subscription-Key']}"})

    with pytest.raises(fe.EdinetAuthError) as auth:
        _client(denied).list_documents(date(2025, 11, 10))
    assert KEY not in str(auth.value)

    def soft_denied(url, params=None, **_kw):  # HTTP 200＋StatusCode 401
        return _Resp(200, {"StatusCode": 401, "message": f"Access denied {params['Subscription-Key']}"})

    with pytest.raises(fe.EdinetAuthError) as soft:
        _client(soft_denied).list_documents(date(2025, 11, 10))
    assert KEY not in str(soft.value)


def test_calls_are_spaced_by_the_minimum_interval() -> None:
    sleeps: list[float] = []
    now = [100.0]

    def get(url, params=None, **_kw):
        now[0] += 0.3
        return _Resp(200, {"metadata": {"status": "200"}, "results": []})

    client = fe.Client(KEY, sleep=lambda s: (sleeps.append(s), now.__setitem__(0, now[0] + s)),
                       clock=lambda: now[0], get=get)
    client.list_documents(date(2025, 11, 10))
    client.list_documents(date(2025, 11, 11))
    assert client.calls == 2 and len(sleeps) == 1 and sleeps[0] == pytest.approx(fe.MIN_INTERVAL_SECONDS - 0.3)


def test_rate_limiting_backs_off_then_aborts_and_counts_every_unscanned_date(tmp_path) -> None:
    sleeps: list[float] = []

    def limited(url, params=None, **_kw):
        return _Resp(429, {"message": "too many"})

    clock = iter(range(0, 10_000, 10))
    client = fe.Client(KEY, sleep=sleeps.append, clock=lambda: next(clock), get=limited, backoff=(60, 120))
    days = [date(2025, 11, 10) + timedelta(days=i) for i in range(5)]
    entries, report = eh.scan_lists(client, days, cache_dir=tmp_path, fetched_at=FETCHED)
    assert report["aborted"] and report["dates_unscanned"] == 5 and report["dates_fetched"] == 0
    assert client.calls == 3 and sleeps == [60, 120]
    assert entries == {}


def test_list_documents_keeps_only_periodic_reports_and_the_listed_fields() -> None:
    body = {"metadata": {"status": "200"}, "results": [
        {"docID": "S1", "edinetCode": "E00542", "docTypeCode": "160", "secCode": "31100", "submitDateTime": "2025-11-10 15:00",
         "filerName": "日東紡", "periodStart": "2025-04-01"},
        {"docID": "S2", "edinetCode": "E00542", "docTypeCode": "180"}]}
    got = _client(lambda url, params=None, **_kw: _Resp(200, body)).list_documents(date(2025, 11, 10))
    assert got["count_all"] == 2 and [r["docID"] for r in got["results"]] == ["S1"]
    assert set(got["results"][0]) == set(fe.LIST_FIELDS)


# ---------------------------------------------------------------------------
# コードリスト：0 筆或多筆就拒收（INV-1）
# ---------------------------------------------------------------------------

def _codelist(rows) -> bytes:
    out = io.StringIO()
    out.write("ダウンロード実行日,2026年10月21日現在,件数,3件\n")
    writer = csv.writer(out)
    writer.writerow(["ＥＤＩＮＥＴコード", "提出者種別", "提出者名", "証券コード"])
    writer.writerows(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("EdinetcodeDlInfo.csv", out.getvalue().encode("cp932"))
    return buf.getvalue()


def test_a_security_code_with_zero_or_many_edinet_codes_is_refused() -> None:
    rows = fe.codelist_rows(_codelist([["E00542", "内国法人", "日東紡績", "31100"], ["E1", "内国法人", "A", "99990"],
                                       ["E2", "内国法人", "B", "99990"], ["E3", "内国法人", "C", "130A0"]]))
    assert fe.edinet_code_for("3110", rows) == "E00542"
    assert fe.edinet_code_for("130A", rows) == "E3"          # 新制代號含英文字母：字串比對
    for sec in ("1234", "9999"):
        with pytest.raises(LookupError):
            fe.edinet_code_for(sec, rows)


# ---------------------------------------------------------------------------
# 編排：一輪從書類一覧到列（假的 client，不連網）
# ---------------------------------------------------------------------------

class FakeClient:
    def __init__(self, lists, docs):
        self.lists, self.docs, self.calls = lists, docs, 0

    def list_documents(self, day):
        self.calls += 1
        results = self.lists.get(day, [])
        return {"count_all": len(results), "results": results}

    def fetch_csv_zip(self, doc_id):
        self.calls += 1
        if doc_id not in self.docs:
            raise fe.EdinetDocMissing(f"{doc_id} 404")
        return self.docs[doc_id]


def _entry(doc_id, doc_type, submitted, *, withdrawn="0", csv_flag="1", code="E00542"):
    return {"docID": doc_id, "edinetCode": code, "secCode": "31100", "docTypeCode": doc_type,
            "submitDateTime": submitted, "parentDocID": None, "withdrawalStatus": withdrawn, "docInfoEditStatus": "0",
            "xbrlFlag": "1", "csvFlag": csv_flag}


def _fy_3110():
    rows = hy_3110(kind="FY", start="2025-04-01", end="2026-03-31", ctx=("CurrentYearDuration", "CurrentYearInstant"),
                   revenue="120000000000", summary="120000000000")
    return rows


def _scenario():
    h1 = date(2025, 11, 10)
    fy = date(2026, 6, 26)
    lists = {
        h1: [_entry("S100WZ3X", "160", "2025-11-10 15:00"), _entry("S100WD", "160", "2025-11-10 15:01", withdrawn="2"),
             _entry("S100NOCSV", "160", "2025-11-10 15:02", csv_flag="0")],
        fy: [_entry("S100FY26", "120", "2026-06-26 10:00"), _entry("S100Q1", "140", "2026-06-26 10:05")],
    }
    docs = {"S100WZ3X": make_zip(hy_3110()), "S100FY26": make_zip(_fy_3110()),
            "S100Q1": make_zip(hy_3110(kind="Q1", ctx=("CurrentYTDDuration", "CurrentQuarterInstant")))}
    return lists, docs, [h1, fy]


CODELIST = [{"ＥＤＩＮＥＴコード": "E00542", "証券コード": "31100"}]


def test_a_run_turns_listed_reports_into_rows_with_every_document_accounted_for(tmp_path) -> None:
    lists, docs, days = _scenario()
    client = FakeClient(lists, docs)
    out = eh.collect(client, tickers=["3110.T"], days=days, today=date(2026, 10, 21), cache_dir=tmp_path,
                     codelist=CODELIST, fetched_at=FETCHED)
    report = out["tickers"]["3110.T"]["report"]
    assert report["docs_seen_by_type"] == {"160": 3, "120": 1, "140": 1}
    assert report["skipped"] == {"withdrawn": 1, "no_csv": 1, "quarter_not_used": 1} and report["docs_used"] == 2
    rows = out["tickers"]["3110.T"]["rows"]
    halves = sorted((r["period_end"], r["value"], r["filed"]) for r in rows if r["metric"] == "revenue_half")
    # 可知日＝submitDateTime（JST 日期），不是抓取日（INV-6）
    assert halves == [("2025-09-30", 57_412_000_000.0, "2025-11-10"), ("2026-03-31", 62_588_000_000.0, "2026-06-26")]
    assert not any(r["metric"].endswith("_annual") for r in rows)
    assert report["h2_derived"] == 2 and report["h2_missing_h1"] == []
    # 第二輪全走快取：書類一覧已定案、文件只留白名單列
    again = FakeClient(lists, docs)
    eh.collect(again, tickers=["3110.T"], days=days, today=date(2026, 10, 21), cache_dir=tmp_path,
               codelist=CODELIST, fetched_at="2026-10-22T00:00:00+00:00")
    assert again.calls == 0
    cached = json.loads((tmp_path / "docs" / "S100WZ3X.json").read_text(encoding="utf-8"))
    assert {r[0] for r in cached["rows"]} <= eh.KEPT_ELEMENTS


def test_replace_refuses_a_narrow_window_and_never_wipes_on_an_empty_build(tmp_path) -> None:
    """R2-S3 #2 的對稱面：窄窗只建得出窗內的列——配 --replace 會刪光整檔；一列都沒建出來也不刪。"""
    with pytest.raises(eh.EdinetHistoryError, match="全窗"):
        eh.run(tickers=["3110.T"], mode="backfill", dry_run=False, replace=True, since=date(2025, 11, 1),
               client=FakeClient({}, {}), today=date(2026, 10, 21), cache_dir=tmp_path)
    conn = _conn()
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','cash',NULL,'2025-09-30','2025-11-10','S1',"
                 "'EDINET-160',1,'JPY',1,NULL,'t',?,?)", (hb.SOURCE_EDINET, FETCHED))
    result = eh.write(conn, {"tickers": {"3110.T": {"rows": [], "report": {}}}}, replace=True)
    assert result["replace_skipped_empty"] == ["3110.T"]
    assert conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] == 1


def test_a_document_relisted_on_a_later_day_is_handled_once_with_its_latest_status(tmp_path) -> None:
    """10-21 實測 6268 S100WHTQ 列在兩天：同一份處理兩次。以 docID 去重、留較晚那天的狀態（之後被取下就算取下）。"""
    lists, docs, days = _scenario()
    later = date(2026, 7, 1)
    lists[later] = [_entry("S100WZ3X", "160", "2025-11-10 15:00", withdrawn="2")]
    out = eh.collect(FakeClient(lists, docs), tickers=["3110.T"], days=[*days, later], today=date(2026, 10, 21),
                     cache_dir=tmp_path, codelist=CODELIST, fetched_at=FETCHED)
    report = out["tickers"]["3110.T"]["report"]
    assert out["run"]["docs_relisted"] == 1 and report["docs_seen_by_type"]["160"] == 3
    assert report["skipped"]["withdrawn"] == 2
    assert not any(r["accession"] == "S100WZ3X" for r in out["tickers"]["3110.T"]["rows"])


def test_an_unresolved_edinet_code_is_a_named_outcome_and_writes_nothing(tmp_path) -> None:
    lists, docs, days = _scenario()
    out = eh.collect(FakeClient(lists, docs), tickers=["3110.T"], days=days, today=date(2026, 10, 21),
                     cache_dir=tmp_path, codelist=[], fetched_at=FETCHED)
    report = out["tickers"]["3110.T"]["report"]
    assert report["outcome"] == "edinet_code_unresolved" and out["tickers"]["3110.T"]["rows"] == []


def test_the_key_never_reaches_the_report_or_the_caches(tmp_path) -> None:
    lists, docs, days = _scenario()
    body_with_key = {**lists}

    def get(url, params=None, **_kw):
        if url.endswith("/documents.json"):
            day = date.fromisoformat(params["date"])
            return _Resp(200, {"metadata": {"status": "200", "parameter": {"date": params["date"]}},
                               "results": body_with_key.get(day, [])})
        doc_id = url.rsplit("/", 1)[-1]
        if doc_id == "S100Q1":
            raise ConnectionError(f"reset by peer for {url}?Subscription-Key={params['Subscription-Key']}")
        return _Resp(200, None, content=docs[doc_id], ctype="application/octet-stream")

    out = eh.collect(_client(get), tickers=["3110.T"], days=days, today=date(2026, 10, 21), cache_dir=tmp_path,
                     codelist=CODELIST, fetched_at=FETCHED)
    assert out["run"]["docs_failed"] and fe.REDACTED in out["run"]["docs_failed"][0]["reason"]
    assert KEY not in json.dumps(out, ensure_ascii=False, default=str)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            text = (eh.gzip.decompress(data) if path.suffix == ".gz" else data).decode("utf-8")
            assert KEY not in text, path


# ---------------------------------------------------------------------------
# 寫入
# ---------------------------------------------------------------------------

def _conn(metrics=hb.METRICS) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(hb._SQLITE_DDL.replace(", ".join(f"'{m}'" for m in hb.METRICS),
                                              ", ".join(f"'{m}'" for m in metrics)))
    return conn


def test_nothing_is_written_until_the_check_knows_the_half_year_metrics(tmp_path) -> None:
    lists, docs, days = _scenario()
    collected = eh.collect(FakeClient(lists, docs), tickers=["3110.T"], days=days, today=date(2026, 10, 21),
                           cache_dir=tmp_path, codelist=CODELIST, fetched_at=FETCHED)
    old = _conn([m for m in hb.METRICS if m not in eh.HALF_METRICS])
    assert eh.write(old, collected)["outcome"] == "check_not_migrated"
    assert old.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] == 0
    conn = _conn()
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','cash',NULL,'2020-03-31','2020-06-26','OLD',"
                 "'EDINET-120',1,'JPY',1,NULL,'t',?,?)", (hb.SOURCE_EDINET, FETCHED))
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','cash',NULL,'2020-03-31','2020-06-26','SEC',"
                 "'10-K',1,'USD',1,NULL,'t',?,?)", (hb.SOURCE_EDGAR, FETCHED))
    result = eh.write(conn, collected, replace=True)
    assert result["outcome"] == "written" and result["rows_replaced"]["3110.T"] == 1
    sources = dict(conn.execute("SELECT source, COUNT(*) FROM fundamental_history GROUP BY source").fetchall())
    assert sources[hb.SOURCE_EDGAR] == 1 and sources[hb.SOURCE_EDINET] == result["rows_new"]["3110.T"] > 0
    assert eh.write(conn, collected)["rows_new"]["3110.T"] == 0          # 冪等
    from engine_c.history import fundamental_series

    # T 早於可知日看不到那一期（INV-6）
    assert fundamental_series(conn, "3110.T", "revenue_half", as_of="2025-11-09") == []
    assert [r["value"] for r in fundamental_series(conn, "3110.T", "revenue_half", as_of="2025-11-10")] == [57_412_000_000]
    assert hb.filer_class(conn, "3110.T", today=date(2026, 10, 21))[0] == "jp_semiannual"


# ---------------------------------------------------------------------------
# 路徑上各層：日本有營收、只是沒有季——不是「還沒接」（L11-5）
# ---------------------------------------------------------------------------

def test_a_semiannual_only_company_is_not_reported_as_missing_revenue() -> None:
    from alpha.providers.path_layers import _company_line, _RevenueCache
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','revenue_half','2025-04-01','2025-09-30',"
                 "'2025-11-10','S100WZ3X','EDINET-160',57412000000,'JPY',1,NULL,'jppfs_cor:NetSales',?,?)",
                 (hb.SOURCE_EDINET, FETCHED))
    registry = SimpleNamespace(company=lambda node: SimpleNamespace(research_ticker="3110.T", display_name="日東紡"))
    line = _company_line("co:nittobo", _RevenueCache(conn, date(2026, 10, 21)), registry, as_of=date(2026, 10, 21))
    assert line["absence"]["code"] == "company_semiannual_only" and line["absence"]["kind"] == "inputs_incompatible"


# ---------------------------------------------------------------------------
# 心跳段 1：落後（--sync 修得了）與營收不能用（修不了）分開
# ---------------------------------------------------------------------------

def _fresh_conn(rows) -> sqlite3.Connection:
    conn = _conn()
    for metric, end, filed, form in rows:
        conn.execute("INSERT INTO fundamental_history VALUES ('3110.T',?,NULL,?,?,?,?,1,'JPY',1,NULL,'t',?,?)",
                     (metric, end, filed, f"A-{metric}-{end}", form, hb.SOURCE_EDINET, FETCHED))
    return conn


def test_freshness_counts_lagging_against_the_statutory_deadline_and_unusable_separately() -> None:
    h1 = [("revenue_half", "2025-09-30", "2025-11-10", "EDINET-160"), ("cash", "2025-09-30", "2025-11-10", "EDINET-160")]
    conn = _fresh_conn(h1)
    on_time = eh.filing_freshness(conn, ["3110.T", "4062.T"], today=date(2026, 6, 30))
    assert on_time["have"] == ["3110.T"] and on_time["empty"] == ["4062.T"] and on_time["lagging"] == []
    late = eh.filing_freshness(conn, ["3110.T"], today=date(2026, 7, 1))          # 有報期限＝年度後 3 個月
    assert late["lagging"] == ["3110.T（2026-03-31 那一期，期限 2026-06-30）"]
    fy_no_h2 = _fresh_conn(h1 + [("cash", "2026-03-31", "2026-06-26", "EDINET-120")])
    got = eh.filing_freshness(fy_no_h2, ["3110.T"], today=date(2026, 10, 21))
    assert got["unusable"] == ["3110.T（2026-03-31 那一期營收沒收）"] and got["lagging"] == []   # 半期期限 11-14
    assert eh.filing_freshness(fy_no_h2, ["3110.T"], today=date(2026, 11, 15))["lagging"] == [
        "3110.T（2026-09-30 那一期，期限 2026-11-14）"]


def test_the_heartbeat_line_never_says_caught_up_when_nothing_is_there(monkeypatch) -> None:
    from datetime import datetime, timezone

    import crons.heartbeat as heartbeat
    from engine_c import dart_history as dh

    conn = _conn()
    monkeypatch.setattr("engine_c.db.get_conn", lambda: conn)
    monkeypatch.setattr(eh, "jp_universe", lambda: ["3110.T"])
    monkeypatch.setattr(dh, "kr_universe", lambda: [])
    monkeypatch.setattr(eh, "last_run_summary", lambda: None)
    line = heartbeat._jp_kr_filings_line(now=datetime(2026, 10, 21, tzinfo=timezone.utc))
    assert "已跟上" not in line and "1 檔一筆都沒有" in line and "edinet_history --backfill" in line
    assert "韓國" not in line


# ---------------------------------------------------------------------------
# R2-S2（2026-10-21）：F1 推算列在輸入不完整的一輪不寫、同主鍵不同值點名；F2 失敗看得見；F3 年報判定；F5–F8
# ---------------------------------------------------------------------------

class FlakyClient(FakeClient):
    def __init__(self, lists, docs, *, fail=()):
        super().__init__(lists, docs)
        self.fail = set(fail)

    def fetch_csv_zip(self, doc_id):
        if doc_id in self.fail:
            self.calls += 1
            raise fe.EdinetUnavailable(f"{doc_id} HTTP 500")
        return super().fetch_csv_zip(doc_id)


def _amended_scenario():
    """上半年原版 11-10、上半年訂正 2026-02-02（營收改了）、年報 2026-06-26——R2 F1 的反例形狀。"""
    lists, docs, days = _scenario()
    amend_day = date(2026, 2, 2)
    lists[amend_day] = [_entry("S100H1A", "170", "2026-02-02 10:00")]
    docs["S100H1A"] = make_zip(hy_3110(revenue="50000000000", summary="50000000000"))
    return lists, docs, sorted([*days, amend_day])


def test_a_run_with_a_failed_document_withholds_the_second_half_and_the_next_run_writes_it(tmp_path) -> None:
    """R2-S2 F1：訂正那份這一輪抓失敗——下半年用原版上半年算出來的錯值不得寫進去（之後重算會同鍵被吞掉）；
    下一輪抓到訂正，下半年＝年度−訂正後的上半年。"""
    lists, docs, days = _amended_scenario()
    conn = _conn()
    first = eh.collect(FlakyClient(lists, docs, fail={"S100H1A"}), tickers=["3110.T"], days=days,
                       today=date(2026, 10, 21), cache_dir=tmp_path, codelist=CODELIST, fetched_at=FETCHED)
    report = first["tickers"]["3110.T"]["report"]
    assert report["h2_withheld"]["rows"] == 2 and "本檔文件抓失敗 1 份" in report["h2_withheld"]["reason"]
    assert not any(r["metric"] == "revenue_half" and r.get("derived") for r in first["tickers"]["3110.T"]["rows"])
    eh.write(conn, first)
    second = eh.collect(FakeClient(lists, docs), tickers=["3110.T"], days=days, today=date(2026, 10, 21),
                        cache_dir=tmp_path, codelist=CODELIST, fetched_at=FETCHED)
    assert "h2_withheld" not in second["tickers"]["3110.T"]["report"]
    assert eh.write(conn, second).get("conflicts") is None
    from engine_c.history import fundamental_series

    h2 = [r for r in fundamental_series(conn, "3110.T", "revenue_half", as_of="2026-07-01") if r["period_end"] == "2026-03-31"]
    assert h2[0]["value"] == 120_000_000_000 - 50_000_000_000


def test_a_stored_row_with_the_same_key_and_another_value_is_named_not_swallowed(tmp_path) -> None:
    """R2-S2 F1 ②：DO NOTHING 會靜默留舊值——同主鍵不同值要點名、算進失敗（exit 1）。"""
    lists, docs, days = _scenario()
    collected = eh.collect(FakeClient(lists, docs), tickers=["3110.T"], days=days, today=date(2026, 10, 21),
                           cache_dir=tmp_path, codelist=CODELIST, fetched_at=FETCHED)
    conn = _conn()
    h2 = next(r for r in collected["tickers"]["3110.T"]["rows"] if r["metric"] == "revenue_half" and r.get("derived"))
    conn.execute("INSERT INTO fundamental_history VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?,?)",
                 (h2["ticker"], h2["metric"], h2["period_start"], h2["period_end"], h2["filed"], h2["accession"],
                  h2["form"], 1.0, h2["currency"], h2["derived"], h2["tag"], h2["source"], FETCHED))
    out = eh.write(conn, collected)
    assert [c["stored"] for c in out["conflicts"]["3110.T"]] == [1.0]
    report = {"write": out, "dates_failed": [], "docs_failed": []}
    assert eh.run_failures(report) == 1
    lines = eh._summary_lines({"mode": "backfill", "window": ["a", "b"], "dates_total": 1, "dates_cached": 0,
                               "dates_fetched": 1, "dates_failed": [], "dates_unscanned": 0, "docs_fetched": 1,
                               "docs_cached": 0, "docs_unfetched": 0, "docs_failed": [], "calls": 1,
                               "tickers": {"3110.T": collected["tickers"]["3110.T"]["report"]}, "write": out})
    assert any("同主鍵不同值" in line for line in lines)


def test_freshness_treats_a_period_as_annual_when_any_of_its_rows_is_the_annual_report() -> None:
    """R2-S2 F3：年報之後又交上半年訂正（EDINET-170）——字串 max 會挑到 170、把年報期當成半年，落後晚 46 天才亮。"""
    rows = [("revenue_half", "2025-09-30", "2025-11-10", "EDINET-160"), ("cash", "2026-03-31", "2026-06-26", "EDINET-120"),
            ("revenue_half", "2026-03-31", "2026-07-15", "EDINET-170")]
    got = eh.filing_freshness(_fresh_conn(rows), ["3110.T"], today=date(2026, 11, 15))
    assert got["lagging"] == ["3110.T（2026-09-30 那一期，期限 2026-11-14）"]


def test_the_error_body_is_redacted_before_it_is_truncated() -> None:
    """R2-S2 F5：截在 key 中間時前綴不等於 key、遮不掉——先遮罩再截。"""
    body = "x" * 190 + KEY

    def denied(url, params=None, **_kw):
        resp = _Resp(500, None)
        resp.text = body
        return resp

    with pytest.raises(fe.EdinetUnavailable) as exc:
        _client(denied).list_documents(date(2025, 11, 10))
    assert KEY[:10] not in str(exc.value)


def test_a_csv_with_short_rows_is_refused_not_silently_trimmed() -> None:
    """R2-S2 F6：欄數不足的列原本被丟掉（白名單元素那一列會變成「沒有」）——整份拒收。"""
    raw = _csv(hy_3110()).decode("utf-16") + '"jppfs_cor:NetSales"\t"売上高"\n'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("XBRL_TO_CSV/jpcrp040300-ssr-001_x.csv", raw.encode("utf-16"))
    with pytest.raises(fe.EdinetUnavailable, match="欄數不足"):
        fe.parse_csv_zip(buf.getvalue())


def test_shares_are_not_written_without_the_cross_check_element() -> None:
    """R2-S2 F7：沒有「事業年度末現在発行数」時，股類與發行數核對都會靜默跳過——拒寫。"""
    rows = [r for r in hy_3110() if r[0] != eh.ISSUED_CROSS_CHECK]
    _skip, result = build(rows)
    assert "shares_outstanding_cover" not in by_metric(result)
    assert any("事業年度末現在発行数」不在" in r["reason"] for r in result.rejected)


def test_a_japanese_filer_without_any_half_year_revenue_gets_a_japanese_reason() -> None:
    """R2-S2 F8：有 EDINET 申報、一列半年營收都沒有——理由不得印成「非美國申報人、非台股…」。"""
    from engine_c.three_question_inputs import get_three_question_inputs

    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','cash',NULL,'2026-03-31','2026-06-26','S1',"
                 "'EDINET-120',1,'JPY',1,NULL,'t',?,?)", (hb.SOURCE_EDINET, FETCHED))
    inp = get_three_question_inputs("3110.T", conn=conn, today=date(2026, 10, 21))
    assert inp["revenue_kind"] == "semiannual" and "EDINET 申報人" in inp["no_series_reason"]


def test_capture_declares_the_same_absence_kind_as_the_path_layers_for_semiannual_only() -> None:
    """R2-S2 F4：只有半年營收＝輸入不相容（有營收、對不上曆季），不是「還沒人記」——兩個畫面同一個 kind（L16）。"""
    from alpha.providers.capture import page_capture
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    conn.execute("INSERT INTO fundamental_history VALUES ('3110.T','revenue_half','2025-04-01','2025-09-30',"
                 "'2025-11-10','S1','EDINET-160',1,'JPY',1,NULL,'t',?,?)", (hb.SOURCE_EDINET, FETCHED))
    anchor = {"series": [{"key": "capex", "label": "雲端四大", "aggregation": "sum_calendar_quarter", "points": [1]}]}
    got = page_capture(conn, "3110.T", anchor, as_of=date(2026, 10, 21))
    assert got["absence"]["kind"] == "inputs_incompatible" and "半年" in got["absence"]["reason"]


class LimitedClient(FakeClient):
    """某一份文件撞限流（整輪中止）。"""

    def __init__(self, lists, docs, *, limited):
        super().__init__(lists, docs)
        self.limited = limited

    def fetch_csv_zip(self, doc_id):
        if doc_id == self.limited:
            self.calls += 1
            raise fe.EdinetRateLimited("429")
        return super().fetch_csv_zip(doc_id)


def test_an_abort_on_another_ticker_does_not_withhold_a_ticker_whose_documents_were_all_fetched(tmp_path) -> None:
    """R2 複審 HIGH：文件迴圈是全市場照日期排的——4062 的文件撞限流中止時，3110 的文件早已全部抓完，3110 的下半年照寫；
    4062 有文件沒抓，它的推算列才擋。"""
    lists, docs, days = _scenario()
    later = date(2026, 7, 1)
    lists[later] = [_entry("S100B4062", "120", "2026-07-01 09:00", code="E00775")]
    codelist = CODELIST + [{"ＥＤＩＮＥＴコード": "E00775", "証券コード": "40620"}]
    out = eh.collect(LimitedClient(lists, docs, limited="S100B4062"), tickers=["3110.T", "4062.T"],
                     days=sorted([*days, later]), today=date(2026, 10, 21), cache_dir=tmp_path, codelist=codelist,
                     fetched_at=FETCHED)
    assert out["run"]["aborted"] and out["tickers"]["4062.T"]["report"]["docs_unfetched"] == 1
    assert "h2_withheld" not in out["tickers"]["3110.T"]["report"]
    assert any(r["metric"] == "revenue_half" and r.get("derived") for r in out["tickers"]["3110.T"]["rows"])
