"""URL normalization for the cross-doc_id SourceDoc duplicate guard (pure, no Neo4j)."""

from __future__ import annotations

from loader.load_to_neo4j import normalize_url


def test_normalize_ignores_case_host_fragment_and_trailing_slash() -> None:
    a = normalize_url("https://Example.COM/path/to/doc/")
    b = normalize_url("https://example.com/path/to/doc#section-2")
    assert a == b == "https://example.com/path/to/doc"


def test_normalize_preserves_distinct_paths_and_query() -> None:
    assert normalize_url("https://sec.gov/a/exh_991.htm") != normalize_url(
        "https://sec.gov/b/exh_991.htm"
    )
    assert normalize_url("https://x.com/p?id=1") != normalize_url("https://x.com/p?id=2")


def test_normalize_returns_none_for_empty_or_nonstring() -> None:
    assert normalize_url(None) is None
    assert normalize_url("   ") is None
    assert normalize_url(123) is None


def test_same_sec_document_normalizes_equal_regardless_of_trailing_slash() -> None:
    # The real duplicate: same SEC 6-K exhibit under two different doc_ids.
    url = "https://www.sec.gov/Archives/edgar/data/1437424/000117184326002726/exh_991.htm"
    assert normalize_url(url) == normalize_url(url + "/")
