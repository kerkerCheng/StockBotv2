"""intake 的更正走廊（2026-09-11 使用者定案）。

事發：`inspect_provenance` 是 no-clobber——既有 doc_id 的 extraction 只要 hash 不同就
`conflict`，RA 直接 rejected。設計意圖正確（發布後不可竄改），但**沒有配對的更正路徑**：
2026-09-10 撞上時只能換一個 doc_id 指向同一個 URL，那會在圖裡產生兩份 SourceDoc、
同一個 origin_entity——正是 L8 要防的假交叉驗證形狀。

守的分界：**「更正」讓兩版並存且指得出來，「竄改」讓舊版消失。**
"""
from __future__ import annotations

import json

import pytest

from intake.provenance import (
    canonical_extraction_hash,
    inspect_provenance,
    publish_provenance,
)


def _doc(doc_id: str, *, quote: str, supersedes: str | None = None) -> dict:
    source_doc = {
        "doc_id": doc_id,
        "title": "t",
        "source_type": "news",
        "evidence_tier": 2,
        "origin_entity": "X",
        "published_at": "2026-01-01",
        "retrieved_at": "2026-01-02",
        "publisher": "P",
        "storage_permission": "repo_excerpt",
        "permission_basis": "b",
        "url": f"https://example.com/{doc_id}",
    }
    if supersedes:
        source_doc["supersedes_extraction_sha256"] = supersedes
    return {
        "schema_version": "0.1",
        "source_doc": source_doc,
        "sources": [{"id": f"{doc_id}_s1", "locator": "L", "quote": quote}],
        "nodes": [], "edges": [], "claims": [],
    }


def _raw(quote: str, doc_id: str) -> dict:
    return {"raw_url": f"https://example.com/{doc_id}", "raw_excerpt": quote}


def test_plain_rewrite_is_still_a_conflict(tmp_path) -> None:
    """沒有具名要取代哪一版時，照舊是 conflict——no-clobber 沒有被放寬。"""
    doc_id = "d1"
    first = _doc(doc_id, quote="原本這樣寫")
    publish_provenance(doc_id, first, _raw("原本這樣寫", doc_id), root=tmp_path)

    second = _doc(doc_id, quote="改成這樣寫")
    result = inspect_provenance(doc_id, second, _raw("改成這樣寫", doc_id), root=tmp_path)
    assert result["status"] == "conflict"
    with pytest.raises(ValueError, match="provenance conflict"):
        publish_provenance(doc_id, second, _raw("改成這樣寫", doc_id), root=tmp_path)


def test_supersede_must_name_the_exact_version_it_replaces(tmp_path) -> None:
    """必須指名取代的是**哪一版**，不能說「取代現在那份，不管它是什麼」。"""
    doc_id = "d2"
    first = _doc(doc_id, quote="原本這樣寫")
    publish_provenance(doc_id, first, _raw("原本這樣寫", doc_id), root=tmp_path)

    wrong = _doc(doc_id, quote="改成這樣寫", supersedes="0" * 64)
    assert inspect_provenance(
        doc_id, wrong, _raw("改成這樣寫", doc_id), root=tmp_path)["status"] == "conflict"


def test_named_supersede_publishes_and_keeps_both_versions(tmp_path) -> None:
    """合法更正：舊版歸檔保留，新版就位——兩份都在，指得出來。"""
    doc_id = "d3"
    first = _doc(doc_id, quote="原本這樣寫")
    publish_provenance(doc_id, first, _raw("原本這樣寫", doc_id), root=tmp_path)
    old_hash = canonical_extraction_hash(
        json.loads((tmp_path / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8")))

    second = _doc(doc_id, quote="更正後逐字", supersedes=old_hash)
    inspected = inspect_provenance(doc_id, second, _raw("更正後逐字", doc_id), root=tmp_path)
    assert inspected["status"] == "supersede"
    assert inspected["superseded_sha256"] == old_hash

    published = publish_provenance(doc_id, second, _raw("更正後逐字", doc_id), root=tmp_path)
    assert published["status"] == "published"

    archive = tmp_path / "extractions" / "superseded" / f"{doc_id}.{old_hash[:8]}.json"
    assert archive.is_file(), "舊版必須保留——沒保留就是竄改不是更正"
    assert "原本這樣寫" in archive.read_text(encoding="utf-8")
    current = (tmp_path / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8")
    assert "更正後逐字" in current and "原本這樣寫" not in current


def test_supersede_is_idempotent(tmp_path) -> None:
    """再跑一次不得把新版自己當成要被取代的舊版。"""
    doc_id = "d4"
    publish_provenance(doc_id, _doc(doc_id, quote="v1"), _raw("v1", doc_id), root=tmp_path)
    old_hash = canonical_extraction_hash(
        json.loads((tmp_path / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8")))
    second = _doc(doc_id, quote="v2", supersedes=old_hash)
    publish_provenance(doc_id, second, _raw("v2", doc_id), root=tmp_path)
    again = publish_provenance(doc_id, second, _raw("v2", doc_id), root=tmp_path)
    assert again["status"] in {"matching", "published"}
    archives = list((tmp_path / "extractions" / "superseded").glob(f"{doc_id}.*.json"))
    assert len(archives) == 1, "重跑不得產生第二份歸檔"
