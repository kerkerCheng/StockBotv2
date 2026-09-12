"""URL normalization for the cross-doc_id SourceDoc duplicate guard (pure, no Neo4j)."""

from __future__ import annotations

import pytest

from loader.load_to_neo4j import (
    DuplicateUrlError,
    check_duplicate_url,
    normalize_url,
    preserve_existing_node_fields,
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


# ── preserve_existing_node_fields：重載既有文件不得靜默覆蓋 ────────────────────


def _existing(name=None, attrs="{}", aliases=None):
    return {"name": name, "attrs": attrs, "aliases": aliases}


def test_new_node_keeps_declared_values() -> None:
    name, aliases, attrs, notes = preserve_existing_node_fields(
        "Tower Semiconductor", ["Tower", "TSEM"], {"ticker": "TSEM"}, None
    )
    assert (name, aliases, attrs, notes) == (
        "Tower Semiconductor", ["Tower", "TSEM"], {"ticker": "TSEM"}, []
    )


def test_aliases_union_instead_of_overwrite() -> None:
    # 真案例：[553] 的 RA 宣告 ['Tower','TSEM']，圖上是 ['TSEM','TowerJazz']。
    # 直接 SET 會丟掉 'TowerJazz'，而沒有任何東西會叫。
    _, aliases, _, notes = preserve_existing_node_fields(
        "Tower Semiconductor",
        ["Tower", "TSEM"],
        {},
        _existing(name="Tower Semiconductor", aliases=["TSEM", "TowerJazz"]),
    )
    assert aliases == ["TSEM", "TowerJazz", "Tower"]
    assert any("aliases 保留既有" in note for note in notes)


def test_aliases_union_is_quiet_when_nothing_would_be_dropped() -> None:
    _, aliases, _, notes = preserve_existing_node_fields(
        "GlobalFoundries", ["GF", "GFS"], {}, _existing(aliases=["GFS"])
    )
    assert aliases == ["GFS", "GF"]
    assert notes == []


def test_existing_name_and_attributes_win() -> None:
    name, _, attrs, notes = preserve_existing_node_fields(
        "VCSEL 940nm",
        [],
        {"ticker": "WRONG"},
        _existing(name="VCSEL", attrs='{"ticker": "RIGHT"}'),
    )
    assert name == "VCSEL"
    assert attrs["ticker"] == "RIGHT"
    assert len(notes) == 2
