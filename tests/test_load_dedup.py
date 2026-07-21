"""URL normalization for the cross-doc_id SourceDoc duplicate guard (pure, no Neo4j)."""

from __future__ import annotations

import pytest

from loader.load_to_neo4j import (
    DuplicateUrlError,
    check_duplicate_url,
    normalize_url,
)


class _FakeSession:
    """Minimal session stub: run() returns preset SourceDoc rows."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def run(self, *args, **kwargs):
        return list(self._rows)


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


# ── check_duplicate_url: 同文件多段例外 ──────────────────────────────────────────

_URL = "https://ex.com/annualreport_2025.pdf"


def test_same_url_no_section_raises() -> None:
    # 真重複：同 URL、既有無 section → fail closed。
    existing = [{"id": "doc_a", "url": _URL, "section": None}]
    with pytest.raises(DuplicateUrlError):
        check_duplicate_url({"doc_id": "doc_b", "url": _URL}, _FakeSession(existing))


def test_legit_multi_section_passes() -> None:
    # 合法多段：同 URL，新舊 section 都非空且不同 → 放行、不算 clash。
    existing = [{"id": "doc_fin", "url": _URL, "section": "financials"}]
    result = check_duplicate_url(
        {"doc_id": "doc_pho", "url": _URL, "section": "photonics"},
        _FakeSession(existing),
    )
    assert result == []


def test_multi_section_but_existing_missing_section_raises() -> None:
    # 新 doc 有 section，但既有同 URL doc 沒 section → 不算合法多段 → fail closed。
    existing = [{"id": "doc_a", "url": _URL, "section": None}]
    with pytest.raises(DuplicateUrlError):
        check_duplicate_url(
            {"doc_id": "doc_b", "url": _URL, "section": "photonics"},
            _FakeSession(existing),
        )


def test_same_section_value_raises() -> None:
    # section 相同 → 不是不同段 → fail closed。
    existing = [{"id": "doc_a", "url": _URL, "section": "financials"}]
    with pytest.raises(DuplicateUrlError):
        check_duplicate_url(
            {"doc_id": "doc_b", "url": _URL, "section": "financials"},
            _FakeSession(existing),
        )


def test_different_url_no_clash() -> None:
    existing = [{"id": "doc_a", "url": "https://ex.com/other.pdf", "section": None}]
    result = check_duplicate_url({"doc_id": "doc_b", "url": _URL}, _FakeSession(existing))
    assert result == []


def test_allow_dup_url_overrides_when_not_multi_section() -> None:
    # 沒有合法多段，但 --allow-dup-url 明示放行 → 回報 clash、不 raise。
    existing = [{"id": "doc_a", "url": _URL, "section": None}]
    result = check_duplicate_url(
        {"doc_id": "doc_b", "url": _URL}, _FakeSession(existing), allow_dup_url=True
    )
    assert result == ["doc_a"]
