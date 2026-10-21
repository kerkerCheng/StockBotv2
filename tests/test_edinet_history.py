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
