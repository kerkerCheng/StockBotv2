"""EDGAR filing 的 HTML → 文字不拆字、還原 entity、表格不黏數字（2026-10-08，Phase 7 failure log #5；plan 2026-10-08-001 D5）。

事發兩次：MRVL Q1 FY27 10-Q 的「u nder the capacity reservation agreements」「preced ing table」「$ 870.0 &#160;million」；
CCXI S-4/A 的 `full<span class="nobreak">-scale</span>` 變成「full -scale」——舊的 `_strip_html` 把**每個**標籤都換成空格、
也不還原 entity，從 library/raw 複製的引文不是原文件的字（L6／L18）。改走共用的 `fetchers.utils.html_to_text`。
"""
from __future__ import annotations

from pathlib import Path

from fetchers import edgar
from fetchers.utils import html_to_text

MRVL = ('<html><body><p>Purchases u<span style="font-weight:bold">nder</span> the capacity reservation agreements '
        'are shown in the preced<span>ing</span> table: $<span> </span>870.0&#160;million.</p></body></html>')
CCXI = ('<html><body><div>a full<span class="nobreak">-scale</span> plant with long<span>-term</span> and '
        'real<span>-world</span> deployments &amp; tests</div></body></html>')
TABLE = ('<html><body><table><tr><th>Year</th><th>2025</th><th>2024</th></tr>'
         '<tr><td>Revenue</td><td>1,234</td><td>987</td></tr></table><p>Next paragraph.</p></body></html>')


def test_inline_tags_do_not_split_words_and_entities_are_restored() -> None:
    text = edgar._strip_html(MRVL)
    assert "under the capacity reservation agreements" in text
    assert "preceding table" in text
    assert "$ 870.0 million" in text and "&#160;" not in text
    ccxi = edgar._strip_html(CCXI)
    assert "full-scale" in ccxi and "long-term" in ccxi and "real-world" in ccxi and "& tests" in ccxi


def test_table_cells_stay_separated_and_blocks_get_their_own_lines() -> None:
    text = edgar._strip_html(TABLE)
    assert "2025 2024" in text and "1,234 987" in text and "20252024" not in text
    assert "Next paragraph." in text.splitlines()


def test_other_fetchers_output_is_unchanged_by_the_cell_separator() -> None:
    """MFN／RNS 的既有 raw 是已入圖引文的出處：預設不補儲存格分隔，輸出一字不變。"""
    assert "20252024" in html_to_text(TABLE)


def test_refetching_a_different_text_never_overwrites_an_existing_raw(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "mrvl_10_q_20260528.txt"
    raw.write_text("old text that quotes in the graph point to", encoding="utf-8")
    monkeypatch.setattr(edgar, "get_cik", lambda _t: "0001835632")
    monkeypatch.setattr(edgar, "get_filings", lambda *_a, **_k: [{
        "cik": "0001835632", "accession": "000183563226000010", "primary_doc": "mrvl.htm", "form_type": "10-Q",
        "filed_date": "2026-05-28", "company_name": "Marvell Technology"}])
    monkeypatch.setattr(edgar, "fetch_filing_text", lambda *_a: "new text from the new stripping")
    monkeypatch.setattr(edgar, "make_doc_id", lambda *_a: "mrvl_10_q_20260528")
    results = edgar.fetch_ticker("MRVL", ["10-Q"], 1, tmp_path)
    assert raw.read_text(encoding="utf-8") == "old text that quotes in the graph point to"
    assert results[0]["kept_existing_raw"] is True
    # 內容相同就照常寫（冪等）
    monkeypatch.setattr(edgar, "fetch_filing_text", lambda *_a: "old text that quotes in the graph point to")
    assert "kept_existing_raw" not in edgar.fetch_ticker("MRVL", ["10-Q"], 1, tmp_path)[0]
