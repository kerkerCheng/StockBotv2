"""RNS fetcher（investegate 鏡像）的解析與挑選邏輯測試（不打網路）。

四個實測事實（2026-09-16～17）各鎖一條：清單是 AJAX 表格、日期只在 RNS dateline、
「Summary by AI」不是一手、5xx 與 404 是兩種不同的失敗。fixture 照 investegate 真實結構縮寫。
"""
from __future__ import annotations

import pytest

from fetchers import rns

URL = "https://www.investegate.co.uk/announcement/rns/iqe--iqe/iqe-plc-fy-2025-financial-results/9588930"

LISTING = """<table class="table-investegate"><thead><tr><th>Date</th><th>Time</th><th>Source</th><th>Announcement</th></tr></thead>
<tbody>
<tr><td>07 Sep 2026</td><td>07:00 AM</td><td><div class="text-center"><a class="regulatory source-RNS" title="supplier: Regulatory News Service (Regulatory)" href="https://www.investegate.co.uk/source/RNS">RNS</a></div></td>
<td><a class="announcement-link" href="https://www.investegate.co.uk/announcement/rns/iqe--iqe/iqe-plc-h1-2026-interim-results/9757485">IQE plc: H1 2026 Interim Results</a></td></tr>
<tr><td>28 May 2026</td><td>07:00 AM</td><td><div class="text-center"><a class="regulatory source-RNS" href="https://www.investegate.co.uk/source/RNS">RNS</a></div></td>
<td><a class="announcement-link" href="{url}">IQE plc: FY 2025 Financial Results</a></td></tr>
<tr><td>27 May 2026</td><td>04:30 PM</td><td><div class="text-center"><a class="source-RNS" title="supplier: Regulatory News Service (Non-Regulatory)" href="https://www.investegate.co.uk/source/RNS">RNS</a></div></td>
<td><a class="announcement-link" href="https://www.investegate.co.uk/announcement/rns/iqe--iqe/form-8-3-iqe-plc/9540356">Form 8.3 - IQE plc</a></td></tr>
</tbody></table>""".format(url=URL)

PAGE = """<!DOCTYPE html><html><head><title>IQE plc: FY 2025 Financial Results | Company Announcement | Investegate</title>
<script type="application/ld+json">{"@context":"http://schema.org/","@type":"WebPage","name":"IQE plc: FY 2025 Financial Results"}</script>
</head><body>
<div class="art-board py-3"><h1 id="main-title">IQE plc: FY 2025 Financial Results</h1></div>
<div class="art-board py-3" id="ai-summary"><h2 id="summary-header">Summary by AI</h2>
<div id="collapseSummary">IQE plc reported revenue of £97.3 million. Disclaimer*</div></div>
<div id="ad-rns-content"></div>
<div class="art-board py-3 news-window">
<html xmlns="http://www.w3.org/1999/xhtml"><head><meta name="generator" content="RNS" /><style>p.a{margin:0}</style></head>
<body><img src="https://tracker.live.rns-distribution.com/track.live-rns/1.png" width="1" height="1" />
<div style="text-align:left;"> <div>IQE PLC</div> <div>28 May 2026</div> <div>&#160;</div></div>
<div class="fr-view-element"><div class="p">
<p class="a"><span class="ak">IQE plc</span></p>
<p class="ao"><span>Cardiff, UK</span></p>
<p class="ap"><span>28 May 2026</span></p>
<p class="ar"><span><strong>2.2 Going concern</strong></span></p>
<p class="as"><span>The Directors have prepared forecasts and cash flow projections for a period of at least 12 months.</span></p>
<p class="at">This information is provided by RNS, the news service of the London Stock Exchange.</p>
</div></div></body></html>
</div>
<div class="art-board"><h2>Latest directors dealings</h2><ul><li><a href="/x">British Land Company</a></li></ul></div>
</body></html>"""


def test_listing_rows_carry_date_time_regulatory_flag_and_id() -> None:
    """清單是 AJAX 回的四欄表；來源欄的 class 才是「法定／非法定」的依據。"""
    items = rns.parse_listing(LISTING)
    assert [i["announcement_id"] for i in items] == ["9757485", "9588930", "9540356"]
    assert items[1]["published_at"] == "2026-05-28"
    assert items[1]["time_local"] == "07:00 AM"
    assert items[1]["regulatory"] is True and items[2]["regulatory"] is False
    assert items[1]["title"] == "IQE plc: FY 2025 Financial Results"
    assert items[1]["ticker_key"] == "iqe"


def test_select_reports_every_filter_reason_and_latest_uses_date_then_id() -> None:
    items = rns.parse_listing(LISTING)
    picked, report = rns.select_announcements(items, match="results")
    assert [i["announcement_id"] for i in picked] == ["9757485", "9588930"]
    assert report == {"input": 3, "accepted": 2, "filtered": 1, "reasons": {"match": 1}}
    assert rns.latest_only(picked)[0]["announcement_id"] == "9757485"
    assert rns.latest_only([]) == []


def test_page_date_comes_from_the_rns_dateline_not_page_metadata() -> None:
    """JSON-LD 只是 WebPage、沒有 datePublished；一手日期是 RNS 本體開頭的 dateline。"""
    page = rns.parse_announcement(PAGE)
    assert page["published_at"] == "2026-05-28"
    assert page["dateline_company"] == "IQE PLC"
    assert page["dateline_date"] == "28 May 2026"
    assert page["title"] == "IQE plc: FY 2025 Financial Results"
    assert page["company"] == "IQE plc"


def test_body_keeps_the_rns_text_and_drops_the_ai_summary_and_side_widgets() -> None:
    """「Summary by AI」與側欄都不是一手；正文只取 news-window 內的 RNS 本體（逐字，含尾巴）。"""
    page = rns.parse_announcement(PAGE)
    assert "2.2 Going concern" in page["text"]
    assert "cash flow projections for a period of at least 12 months" in page["text"]
    assert "Summary by AI" not in page["text"] and "£97.3 million" not in page["text"]
    assert "British Land" not in page["text"]
    assert "This information is provided by RNS" in page["text"]


def test_page_without_a_dateline_is_refused_not_dated_today() -> None:
    """沒有 dateline 就拒寫——ingest 日期冒充 published_at 是 AGENTS 的反向禁令。"""
    html = PAGE.replace("<div>28 May 2026</div>", "<div>&#160;</div>")
    with pytest.raises(rns.RnsError, match="dateline"):
        rns.parse_announcement(html)


def test_a_502_or_listing_page_has_no_news_window_and_is_refused() -> None:
    with pytest.raises(rns.RnsError, match="news-window"):
        rns.parse_announcement("<html><body><h1>502 Bad Gateway</h1></body></html>")


def test_long_date_parsing_accepts_full_and_abbreviated_months() -> None:
    assert rns.parse_long_date("12 August 2026") == "2026-08-12"
    assert rns.parse_long_date("07 Sep 2026") == "2026-09-07"
    assert rns.parse_long_date("<td>28 May 2026</td>") == "2026-05-28"
    assert rns.parse_long_date("Monday") is None


def test_doc_id_is_stable_from_the_url_including_the_legacy_index_php_form() -> None:
    legacy = URL.replace("/announcement/", "/index.php/announcement/")
    assert rns.parse_announcement_url(URL) == ("iqe", "iqe", "9588930")
    assert rns.parse_announcement_url(legacy) == ("iqe", "iqe", "9588930")
    assert rns.make_rns_doc_id("iqe", "9588930") == "rns_iqe_9588930"
    with pytest.raises(rns.RnsError, match="截斷"):
        rns.parse_announcement_url("https://www.investegate.co.uk/announcement/rns/iqe--iqe/")


class _Resp:
    def __init__(self, status: int, text: str = "") -> None:
        self.status_code, self.text = status, text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Session:
    def __init__(self, responses) -> None:
        self._responses, self.calls = list(responses), 0

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        return self._responses.pop(0)


def test_5xx_is_retried_and_reported_as_site_down_but_404_is_not_retried() -> None:
    """5xx＝站點暫時不可用（等）；404＝這則不存在（換 id）。一句話講兩種事就是 L12 的形狀。"""
    slept: list[int] = []
    down = _Session([_Resp(502), _Resp(502), _Resp(502)])
    with pytest.raises(rns.RnsError, match="暫時不可用"):
        rns.get_with_retry(down, "https://x", sleep=slept.append)
    assert down.calls == 3 and slept == list(rns.RETRY_BACKOFF)

    recovered = _Session([_Resp(502), _Resp(200, "ok")])
    assert rns.get_with_retry(recovered, "https://x", sleep=lambda s: None).text == "ok"

    missing = _Session([_Resp(404)])
    with pytest.raises(rns.RnsError, match="404"):
        rns.get_with_retry(missing, "https://x", sleep=lambda s: None)
    assert missing.calls == 1


def test_kind_fields_are_conservative_when_regulatory_status_is_unknown() -> None:
    assert rns._kind_fields(True) == {"source_type": "filing", "evidence_tier": 1, "regulatory": True}
    assert rns._kind_fields(None) == {"source_type": "news", "evidence_tier": 2, "regulatory": None}
