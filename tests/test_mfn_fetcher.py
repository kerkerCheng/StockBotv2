"""MFN fetcher 的解析與挑選邏輯測試（不打網路）。

三個實測事實（2026-09-16）各鎖一條：瑞典文／英文孿生同一時戳、日期只認 JSON-LD、
附件只掛在左欄。fixture 照 mfn.se 真實結構縮寫。
"""
from __future__ import annotations

import pytest

from fetchers import mfn

EN_URL = ("https://mfn.se/cis/a/sivers-semiconductors/"
          "sivers-semiconductors-reports-q2-2026-results-6543505f")
SV_URL = ("https://mfn.se/cis/a/sivers-semiconductors/"
          "sivers-semiconductors-rapporterar-resultat-for-q2-2026-866b28e6")

RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel xmlns:x="https://mfn.se/schemas/rss-ns-x/">
<title>MFN</title>
<item>
  <title>Sivers Semiconductors Reports Q2 2026 Results</title>
  <link>{EN_URL}</link>
  <pubDate>Thu, 27 Aug 2026 16:01:48 +0000</pubDate>
  <x:newsId>6543505f-a903-539b-b10f-5fe06c5e9d4a</x:newsId>
  <x:language>en</x:language>
  <x:tag>:regulatory</x:tag>
  <x:scope>SE</x:scope>
</item>
<item>
  <title>Sivers Semiconductors rapporterar resultat för Q2 2026</title>
  <link>{SV_URL}</link>
  <pubDate>Thu, 27 Aug 2026 16:01:48 +0000</pubDate>
  <x:newsId>866b28e6-b24b-5e78-93c9-4158d34b64bd</x:newsId>
  <x:language>sv</x:language>
  <x:tag>:regulatory</x:tag>
</item>
<item>
  <title>Invitation to Presentation of Sivers Semiconductors' Q2 2026 Report</title>
  <link>https://mfn.se/cis/a/sivers-semiconductors/invitation-e04eed67</link>
  <pubDate>Thu, 20 Aug 2026 05:00:00 +0000</pubDate>
  <x:newsId>e04eed67-0000-0000-0000-000000000000</x:newsId>
  <x:language>en</x:language>
</item>
</channel></rss>"""

PAGE = """<!DOCTYPE html><html lang="en"><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"NewsArticle",
"headline":"Sivers Semiconductors Reports Q2 2026 Results","datePublished":"2026-08-27T16:01:48Z"}</script>
<meta property="article:published_time" content="2026-08-27T16:01:48Z">
</head><body>
<div id="content-body" class="body"><div class="grid-g">
<div class="grid-u-1 grid-u-lg-1-4 iframe-full-width"><div class="entity-info">
 <div class="tray company"><label class="heading-1"><a href="/all/a/sivers-semiconductors">Sivers Semiconductors</a></label></div>
 <div class="tray"><label class="heading-2">Bifogade filer</label>
  <div class="documents"><div><a
      class="" href="https://mb.cision.com/Main/11695/4388331/4236264.pdf"
      target="_blank" rel="noopener noreferrer nofollow"><img class="file-icon"> PDF</a></div></div>
 </div>
</div></div>
<div class="grid-u-1 grid-u-lg-3-4 iframe-full-width">
<article class="full-item" id="6543505f-a903-539b-b10f-5fe06c5e9d4a">
 <h1 class="title"><a href="/cis/a/sivers-semiconductors/x-6543505f">Sivers Semiconductors Reports Q2 2026 Results</a></h1>
 <div class="publish-date"> 2026-08-27 18:01:48 </div>
 <div class="content s-cis"><p><span><strong>Kista, Sweden - August 27, 2026</strong></span><span> </span><span>-</span><span> </span><a href="https://www.sivers-semiconductors.com/"><span><u>Sivers Semiconductors</u></span></a><span> </span><span>AB</span><span> </span><span>(STO:SIVE) today announced its interim report.</span></p>
 <ul><li><span>Net sales amounted to SEK 53.8 m (61.4).</span></li></ul>
 <p><a href="https://example.com/not-an-attachment.pdf">body link</a></p></div>
</article></div></div></div>
<div class="footer">Modular Finance</div></body></html>"""


def test_feed_twins_share_one_timestamp_but_differ_in_language_and_id() -> None:
    """瑞典文與英文孿生：同一 pubDate、不同 newsId——這是「兩則」不是「兩份來源」。"""
    releases = mfn.parse_feed(RSS)
    en, sv = releases[0], releases[1]
    assert en["published_at_time"] == sv["published_at_time"] == "2026-08-27T16:01:48Z"
    assert en["published_at"] == sv["published_at"] == "2026-08-27"
    assert (en["language"], sv["language"]) == ("en", "sv")
    assert en["release_id"] == "6543505f" and sv["release_id"] == "866b28e6"
    assert en["regulatory"] is True and releases[2]["regulatory"] is False


def test_select_defaults_to_english_and_reports_every_filter_reason() -> None:
    """預設只留英文；濾掉的逐項報 reasons（INV-3），不是靜默少一則。"""
    releases = mfn.parse_feed(RSS)
    picked, report = mfn.select_releases(releases, match="q2 2026 results")
    assert [r["release_id"] for r in picked] == ["6543505f"]
    assert report == {"input": 3, "accepted": 1, "filtered": 2,
                      "reasons": {"language": 1, "match": 1}}
    both, _ = mfn.select_releases(releases, match="q2 2026", language="all")
    assert {r["language"] for r in both} == {"en", "sv"}


def test_undated_feed_items_are_filtered_and_counted_not_backfilled() -> None:
    """沒有 pubDate 的項目不得補抓取日；它被濾掉且被計數。"""
    undated = RSS.replace("<pubDate>Thu, 20 Aug 2026 05:00:00 +0000</pubDate>", "")
    releases = mfn.parse_feed(undated)
    assert releases[2]["published_at"] is None
    _, report = mfn.select_releases(releases, match="invitation")
    assert report["reasons"]["undated"] == 1


def test_page_date_comes_from_json_ld_in_utc_not_the_local_publish_date() -> None:
    """頁面上的 publish-date 是斯德哥爾摩時間（18:01）；published_at 只認 JSON-LD 的 UTC（16:01）。"""
    page = mfn.parse_release_page(PAGE)
    assert page["published_at_time"] == "2026-08-27T16:01:48Z"
    assert page["published_at"] == "2026-08-27"
    assert page["headline"] == "Sivers Semiconductors Reports Q2 2026 Results"
    assert page["company"] == "Sivers Semiconductors"
    assert page["language"] == "en"


def test_page_with_offset_timestamp_normalizes_to_utc_date() -> None:
    """跨日案例：斯德哥爾摩 00:30 CEST 是前一天 22:30 UTC，日期必須取 UTC 那天。"""
    html = PAGE.replace("2026-08-27T16:01:48Z", "2026-08-28T00:30:00+02:00")
    page = mfn.parse_release_page(html)
    assert page["published_at_time"] == "2026-08-27T22:30:00Z"
    assert page["published_at"] == "2026-08-27"


def test_page_without_json_ld_date_is_refused_not_dated_today() -> None:
    """沒有 datePublished 就拒寫——ingest 日期冒充 published_at 是 AGENTS 的反向禁令。"""
    html = PAGE.replace('"datePublished":"2026-08-27T16:01:48Z"', '"x":"y"')
    with pytest.raises(mfn.MfnError, match="datePublished"):
        mfn.parse_release_page(html)


def test_body_text_joins_inline_spans_without_line_breaks_and_drops_nav() -> None:
    """正文的每個字組各包一個 <span>；抽出來必須是一句話，不是十行。"""
    page = mfn.parse_release_page(PAGE)
    assert "Kista, Sweden - August 27, 2026 - Sivers Semiconductors AB (STO:SIVE) today announced" in page["text"]
    assert "- Net sales amounted to SEK 53.8 m (61.4)." in page["text"]
    assert "Bifogade filer" not in page["text"]
    assert "Modular Finance" not in page["text"]


def test_attachments_come_from_the_left_column_only() -> None:
    """附件只掛在 entity-info 的「Bifogade filer」；正文裡的 PDF 連結不是附件。

    fixture 的 <a> 刻意把屬性跨行、href 放第二個——2026-09-17 第一次 smoke 一份附件都沒抓到，
    就是因為 regex 只認單行的 `<a href=`，而 fixture 當時寫成單行所以是綠的。
    """
    page = mfn.parse_release_page(PAGE)
    assert page["attachments"] == ["https://mb.cision.com/Main/11695/4388331/4236264.pdf"]


def test_doc_id_is_stable_from_the_url_and_attachments_do_not_collide() -> None:
    assert mfn.release_id_from_url(EN_URL) == "6543505f"
    assert mfn.company_slug_from_url(EN_URL) == "sivers-semiconductors"
    assert mfn.make_mfn_doc_id("sivers-semiconductors", "6543505f") == "mfn_sivers_semiconductors_6543505f"
    assert mfn.make_mfn_doc_id("sivers-semiconductors", "6543505f", attachment_index=1) == (
        "mfn_sivers_semiconductors_6543505f_att1")


def test_truncated_url_is_rejected_instead_of_fetching_a_404() -> None:
    """上一輪探到 404 是 URL 被截斷；沒有 8 碼 id 的 URL 直接報錯，不去打網路。"""
    with pytest.raises(mfn.MfnError, match="截斷"):
        mfn.release_id_from_url("https://mfn.se/cis/a/sivers-semiconductors/sivers-semiconductors-reports")


def test_kind_fields_are_conservative_when_regulatory_status_is_unknown() -> None:
    """法定公告 tier 1；查不到就記 news／tier 2 並保留 regulatory=None——不把「不知道」寫成「是」。"""
    assert mfn._kind_fields(True) == {"source_type": "filing", "evidence_tier": 1, "regulatory": True}
    assert mfn._kind_fields(None) == {"source_type": "news", "evidence_tier": 2, "regulatory": None}


def test_latest_only_uses_the_utc_timestamp() -> None:
    releases = mfn.parse_feed(RSS)
    picked, _ = mfn.select_releases(releases, language="all")
    assert mfn.latest_only(picked)[0]["release_id"] == "6543505f"
    assert mfn.latest_only([]) == []
