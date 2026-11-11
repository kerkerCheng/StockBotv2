"""Form 4 code P 從 auto no_go 拿出來（盲點修法 plan 2026-11-02-001 §2 第 15 條後半；審查：分析師初評、指數納入、內部人公開市場
買進是小型股重評價常見的觸發，Form 4 卻全部 auto no_go）。

守的事：①原始 XML 的網址、交易代碼只認 non-derivative 那一表 ②新的 Form 4 先讀代碼、記進 refs：含 P 的留在 pending 交給分類層，
其餘照舊 auto no_go，讀不到也照舊 auto no_go、但數得出來（INV-3）③沒給讀代碼的呼叫端行為不變 ④harvest log 帶這個 filter 的報告、
心跳段 1 印一行，讀不到非 0 才標粗。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from crons import harvest_leads
from crons import heartbeat as hb
from engine_b import leads
from fetchers import edgar

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)

FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <nonDerivativeTable>
    <nonDerivativeTransaction><transactionCoding><transactionFormType>4</transactionFormType>
      <transactionCode>P</transactionCode></transactionCoding></nonDerivativeTransaction>
    <nonDerivativeTransaction><transactionCoding><transactionCode>s</transactionCode></transactionCoding></nonDerivativeTransaction>
  </nonDerivativeTable>
  <derivativeTable>
    <derivativeTransaction><transactionCoding><transactionCode>M</transactionCode></transactionCoding></derivativeTransaction>
  </derivativeTable>
</ownershipDocument>"""


def test_raw_xml_url_and_only_non_derivative_codes() -> None:
    url = "https://www.sec.gov/Archives/edgar/data/707549/000196546226000002/xslF345X06/wk-form4_1793642873.xml"
    assert edgar.form4_raw_xml_url(url) == \
        "https://www.sec.gov/Archives/edgar/data/707549/000196546226000002/wk-form4_1793642873.xml"
    assert edgar.form4_transaction_codes(FORM4) == ["P", "S"]                  # 衍生性那一表的 M 不算；小寫照樣認
    assert edgar.form4_transaction_codes("<ownershipDocument/>") == []
    with pytest.raises(ValueError):
        edgar.form4_transaction_codes("<not xml")


FORM4_FULL = """<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <periodOfReport>2026-10-28</periodOfReport>
  <issuer><issuerName>TTM TECHNOLOGIES INC</issuerName><issuerTradingSymbol>TTMI</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Ali Wajid</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-10-28</value></transactionDate>
      <transactionCoding><transactionFormType>4</transactionFormType><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>89.8571</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
      <postTransactionAmounts><sharesOwnedFollowingTransaction><value>30835</value></sharesOwnedFollowingTransaction>
      </postTransactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <footnotes><footnote id="F1">Weighted average price.</footnote></footnotes>
</ownershipDocument>"""


def test_form4_text_copies_the_filing_fields_without_judging() -> None:
    """2026-11-11：含 P 的 Form 4 留在 pending 交給分類層，分類器卻看不到它——一批 28 則全落到互動 session。
    給分類器的是申報欄位照抄（誰、什麼身分、哪天、什麼代碼、幾股、多少錢、之後持多少、註腳），不加判讀。"""
    text = edgar.form4_text(FORM4_FULL)
    assert text.startswith("Form 4（") and "TTM TECHNOLOGIES INC（TTMI）" in text
    assert "申報人：Ali Wajid（董事）" in text
    assert "2026-10-28｜代碼 P｜A 5000 股｜每股 89.8571｜交易後持股 30835｜D" in text
    assert "註腳 F1：Weighted average price." in text
    with pytest.raises(ValueError):
        edgar.form4_text("<not xml")
    assert edgar.is_ownership_xsl_url(
        "https://www.sec.gov/Archives/edgar/data/1116942/000119312526436557/xslF345X06/ownership.xml")
    assert not edgar.is_ownership_xsl_url("https://www.sec.gov/Archives/edgar/data/1/000000000026000001/x8k.htm")
    assert not edgar.is_ownership_xsl_url("https://example.com/xslF345X06/ownership.xml")


def _items() -> list[dict]:
    base = "https://www.sec.gov/Archives/edgar/data/1/00000000012600000{n}/xslF345X06/form4.xml"
    return [{"url": base.format(n=n), "title": f"X {form} filed 2026-11-02 [{n}]", "published_at": "2026-11-02",
             "form_type": form} for n, form in ((1, "4"), (2, "4"), (3, "4"), (4, "8-K"))]


def test_purchases_stay_pending_and_everything_else_keeps_the_old_auto_no_go() -> None:
    items = _items()
    lookup = {items[0]["url"]: ["P", "S"], items[1]["url"]: ["F"], items[2]["url"]: None}
    store = leads.empty_store()
    report: dict[str, int] = {}
    new = harvest_leads._register_all(store, "edgar:X", items, NOW.isoformat(), auto_no_go_forms=frozenset({"4"}),
                                      insider_codes=lookup.get, insider_report=report)
    by_url = {lead["url"]: lead for lead in store["leads"].values()}
    bought, granted, unread, eight_k = (by_url[item["url"]] for item in items)
    assert new == 4
    assert bought["status"] == "pending" and bought["refs"]["insider_transaction_codes"] == ["P", "S"]
    assert granted["status"] == "triaged_no_go" and granted["refs"]["insider_transaction_codes"] == ["F"]
    assert unread["status"] == "triaged_no_go" and "insider_transaction_codes" not in (unread.get("refs") or {})
    assert eight_k["status"] == "pending"                                      # 不在 auto no_go 的型別，本來就進 triage
    assert report == {"form4_new": 3, "form4_purchase": 1, "form4_unread": 1}


def test_callers_without_the_code_reader_keep_the_old_behaviour() -> None:
    store = leads.empty_store()
    harvest_leads._register_all(store, "edgar:X", _items(), NOW.isoformat(), auto_no_go_forms=frozenset({"4"}))
    statuses = sorted(lead["status"] for lead in store["leads"].values())
    assert statuses == ["pending", "triaged_no_go", "triaged_no_go", "triaged_no_go"]


def test_harvest_edgar_writes_the_filter_report_into_the_log(monkeypatch) -> None:
    filings = [{"accession": "000000000126000001", "primary_doc": "xslF345X06/form4.xml", "form_type": "4",
                "filed_date": "2026-11-02"},
               {"accession": "000000000126000002", "primary_doc": "x8k.htm", "form_type": "8-K",
                "filed_date": "2026-11-02"}]
    monkeypatch.setattr(harvest_leads, "_edgar_watch_tickers", lambda watch: ["X"])
    monkeypatch.setattr(harvest_leads, "_registry_company", lambda ticker: None)
    monkeypatch.setattr(edgar, "get_cik", lambda ticker: "1")
    monkeypatch.setattr(edgar, "get_filings", lambda cik, forms, count: filings)
    monkeypatch.setattr(edgar, "fetch_form4_transaction_codes", lambda url: ["P"])
    store = leads.empty_store()
    harvest_leads.harvest_edgar({"edgar_watch": {"forms": ["4", "8-K"], "auto_no_go_forms": ["4"]}}, store,
                                seen_at=NOW.isoformat())
    entry = next(e for e in store["harvest_log"] if e["source"] == "edgar:X")
    assert entry["result"] == "ok" and entry["new"] == 2
    assert entry["filter"] == {"form4_new": 1, "form4_purchase": 1}


def test_section_one_line_sums_the_latest_runs_and_bolds_only_unread() -> None:
    latest = {"edgar:A": {"result": "ok", "filter": {"form4_new": 2, "form4_purchase": 1}},
              "edgar:B": {"result": "ok", "filter": {"form4_new": 1, "form4_unread": 1}},
              "edgar:C": {"result": "ok"},                                       # 最後一輪沒有新 Form 4
              "mops:3081.TWO": {"result": "ok", "filter": {"form4_new": 9}}}     # 不是 EDGAR 的不算
    assert hb.form4_line(latest) == ("EDGAR Form 4（各檔最後一輪，2 檔有新申報）：新 3｜公開市場買進 1（留給分類層，"
                                     "不 auto no_go）｜**交易代碼讀不到 1**")
    assert hb.form4_line({"edgar:A": {"result": "ok", "filter": {"form4_new": 1}}}).endswith("｜交易代碼讀不到 0")
    assert hb.form4_line({"edgar:C": {"result": "ok"}}) is None


def test_section_one_prints_the_form4_line(tmp_path: Path) -> None:
    log = [{"run_at": NOW.isoformat(), "source": "edgar:AXTI", "result": "ok", "new": 1,
            "filter": {"form4_new": 1, "form4_purchase": 1}}]
    path = tmp_path / "pending_leads.json"
    path.write_text(json.dumps({"leads": {}, "harvest_log": log}), encoding="utf-8")
    lines = hb.build_freshness(now=NOW, state_dir=tmp_path, leads_path=path).lines
    assert any(x.startswith("EDGAR Form 4（各檔最後一輪，1 檔有新申報）：新 1｜公開市場買進 1") for x in lines), lines
