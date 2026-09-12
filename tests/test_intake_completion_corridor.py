# -*- coding: utf-8 -*-
"""入圖完成收據的更正走廊，以及「圖變了沒」這個分類。

事發（2026-09-12，使用者已 go 的 pq2 [542]）：2026-09-11 給 `extractions/<doc_id>.json`
開了具名更正走廊，但同一條 publish 路徑寫的第二個檔
（`library/private/intake_state/<doc_id>.json`）沒有配對的出口。後果是走廊**對它自己
的目標案例完全不可用**——凡是先前已經入圖過的 doc_id，更正一定卡在 no-clobber。
實跑結果：Neo4j 的邊寫成功、extraction 與 raw 都更正並歸檔，然後停在收據，
RA 留在 `partial`，使用者已經核准的編號關不掉。

驗收條件寫成「**同一個 doc_id 第二次入圖真的走得完，而且舊版兩份都還在**」，
不是「函式回得出 dict」——後者在修好之前就已經成立。
"""

from __future__ import annotations

import json

import pytest

from intake import provenance
from intake.application import GRAPH_STAGES


def _extraction(doc_id: str, *, revision: int, supersedes: str | None = None) -> dict:
    source_doc = {
        "doc_id": doc_id,
        "title": f"Test filing r{revision}",
        "url": "https://www.sec.gov/Archives/edgar/data/1/test.htm",
        "publisher": "U.S. Securities and Exchange Commission (EDGAR)",
        "published_at": "2026-06-25",
        "retrieved_at": "2026-09-12",
        "source_type": "filing",
        "storage_permission": "repo_full",
        "permission_basis": "public domain government record",
    }
    if supersedes:
        source_doc["supersedes_extraction_sha256"] = supersedes
    return {
        "source_doc": source_doc,
        "nodes": [{"id": "co:test", "type": "Company", "name": f"Test {revision}"}],
        "edges": [],
        "claims": [],
    }


def _receipt(root, doc_id: str) -> dict:
    return json.loads(
        (root / "library" / "private" / "intake_state" / f"{doc_id}.json").read_text(
            encoding="utf-8"
        )
    )


def test_receipt_rewrite_is_refused_without_the_archived_old_extraction(tmp_path) -> None:
    """沒有歸檔證據就不給走廊——fail closed。

    這是放行條件的**收緊面**：允許改寫收據的唯一理由是「舊版可證已保存」，
    所以沒有那份歸檔時，改寫必須照樣被擋下。少了這條，走廊就是一道後門。
    """
    doc_id = "test_doc_20260912"
    provenance.mark_graph_complete(doc_id, _extraction(doc_id, revision=1), root=tmp_path)

    with pytest.raises(ValueError, match="not archived under superseded"):
        provenance.mark_graph_complete(doc_id, _extraction(doc_id, revision=2), root=tmp_path)


def test_receipt_follows_the_extraction_through_a_legal_correction(tmp_path) -> None:
    """走廊的目標案例：已入圖的文件要能被更正一次，而且兩版都留得下來。"""
    doc_id = "test_doc_20260912"
    first = _extraction(doc_id, revision=1)
    old_hash = provenance.canonical_extraction_hash(first)

    provenance.publish_provenance(doc_id, first, None, root=tmp_path)
    provenance.mark_graph_complete(doc_id, first, root=tmp_path)
    assert _receipt(tmp_path, doc_id)["extraction_sha256"] == old_hash

    second = _extraction(doc_id, revision=2, supersedes=old_hash)
    published = provenance.publish_provenance(doc_id, second, None, root=tmp_path)
    assert published["archived_previous"], "extraction 走廊本身要先成立"

    result = provenance.mark_graph_complete(doc_id, second, root=tmp_path)

    new_hash = provenance.canonical_extraction_hash(second)
    assert _receipt(tmp_path, doc_id)["extraction_sha256"] == new_hash, "收據要跟上新版"
    assert result["archived_previous_receipt"], "舊收據要留下來，不是被覆蓋掉"
    archived = tmp_path / "library" / "private" / "intake_state" / "superseded" / f"{doc_id}.{old_hash[:8]}.json"
    assert archived.is_file(), "兩份都留：竄改讓舊版消失，更正讓兩版並存"
    assert json.loads(archived.read_text(encoding="utf-8"))["extraction_sha256"] == old_hash

    # 而且 verify 現在要認得新版——這才是「產出到了下游消費者手上」（L13-1）。
    provenance.verify_graph_complete(doc_id, second, root=tmp_path)


def test_same_extraction_twice_is_idempotent_and_archives_nothing(tmp_path) -> None:
    """冪等路徑不得被走廊改壞：同一版重寫一次，不該產生假的 superseded 檔。"""
    doc_id = "test_doc_20260912"
    doc = _extraction(doc_id, revision=1)
    provenance.mark_graph_complete(doc_id, doc, root=tmp_path)
    result = provenance.mark_graph_complete(doc_id, doc, root=tmp_path)

    assert "archived_previous_receipt" not in result
    assert not (tmp_path / "library" / "private" / "intake_state" / "superseded").exists()


def test_graph_stage_vocabulary_is_ordered_and_closed() -> None:
    """`merged` 必須排在 `not_started` 之後——這個順序就是「檔案還能不能復原」的分界。

    ⚠ 這條測的不是字串長相，是**分界存在**：只要有人把 merged 排到第一個，
    或把它從字彙裡拿掉，復原程序就會重新失去判斷依據。
    """
    assert GRAPH_STAGES[0] == "not_started"
    assert GRAPH_STAGES.index("merged") == 1
    assert GRAPH_STAGES[-1] == "receipt_written"
    assert len(set(GRAPH_STAGES)) == len(GRAPH_STAGES)
