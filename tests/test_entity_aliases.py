"""非公司實體 canonical-id registry（`config/entity_aliases.json`）。

事發（2026-09-10 實測）：圖裡 NAND 有 6 個 id、DRAM 4 個、advanced_packaging 3 個。
根因是抽取端 LLM 看到的「既有實體清單」只有手寫範例檔裡的 9 個 node，而圖中光是
chokepoint 前綴就有 196 個——它不是在無視規則，它是不知道那些 id 存在（L16：分類
有 SSOT，但沒跟著資料送到需要它的地方）。
"""
from __future__ import annotations

import json

import pytest

from identity import entities


def _registry(tmp_path, canonical: dict):
    path = tmp_path / "aliases.json"
    path.write_text(
        json.dumps({"schema_version": entities.SCHEMA_VERSION, "canonical": canonical}),
        encoding="utf-8",
    )
    entities._load.cache_clear()
    return path


def test_alias_resolves_to_canonical_and_unknown_ids_pass_through(tmp_path) -> None:
    """未登記的 id **原樣放行**——擋下來等於停掉自動抽取，世界一直在長新的 tech 節點。"""

    path = _registry(tmp_path, {
        "tech:eml": {"name": "EML", "aliases": ["tech:eml_laser"], "basis": "name_identical"},
    })
    assert entities.resolve("tech:eml_laser", path=path) == "tech:eml"
    assert entities.resolve("tech:eml", path=path) == "tech:eml"
    assert entities.resolve("tech:brand_new", path=path) == "tech:brand_new"


def test_放行必須配一個看得見的補償控制(tmp_path) -> None:
    """放行未登記 id 的代價，是它必須有地方會說話（AGENTS：放行與收緊同時發生）。"""

    path = _registry(tmp_path, {
        "tech:eml": {"name": "EML", "aliases": ["tech:eml_laser"], "basis": "name_identical"},
    })
    unregistered = entities.unregistered_entity_ids(
        ["tech:eml", "tech:eml_laser", "tech:brand_new", "co:nvidia"], path=path
    )
    # 已登記的不報；公司不歸這個 registry 管，也不報。
    assert unregistered == ["tech:brand_new"]


def test_one_id_cannot_have_two_canonicals(tmp_path) -> None:
    """互相打架的 registry 比沒有 registry 更糟——載入時就要 raise。"""

    path = _registry(tmp_path, {
        "tech:a": {"name": "A", "aliases": ["tech:x"], "basis": "name_identical"},
        "tech:b": {"name": "B", "aliases": ["tech:x"], "basis": "name_identical"},
    })
    with pytest.raises(entities.EntityAliasError):
        entities.load(path)


def test_company_ids_are_rejected_by_this_registry(tmp_path) -> None:
    """公司走 company_identity.json（INV-1）。兩套 identity authority 混在一起，
    同一家公司就會在兩個地方有不同答案。"""

    path = _registry(tmp_path, {
        "co:nvidia": {"name": "NVIDIA", "aliases": ["co:nvda"], "basis": "name_identical"},
    })
    with pytest.raises(entities.EntityAliasError):
        entities.load(path)


def test_semantic_basis_is_not_accepted_here(tmp_path) -> None:
    """「這兩個名字不同的東西其實一樣」是研究判斷，載體是 pq2，不是這個檔（L15）。

    ⚠ 這一條刻意收緊：`basis` 是封閉字彙，寫入端連沒登記過的值都要拒絕——
    自由字串會讓寫的人以為表達了一個沒被記錄的區別（L16-3）。
    """

    path = _registry(tmp_path, {
        "tech:nand": {"name": "NAND", "aliases": ["tech:nand_flash"], "basis": "semantic_judgment"},
    })
    with pytest.raises(entities.EntityAliasError):
        entities.load(path)


def test_document_rewrite_covers_nodes_edges_and_node_claims(tmp_path) -> None:
    """三處必須一起改——節點合併了但邊還指著舊 id，會產生指不到的端點，比不合併更糟。"""

    path = _registry(tmp_path, {
        "tech:eml": {"name": "EML", "aliases": ["tech:eml_laser"], "basis": "name_identical"},
    })
    doc = {
        "nodes": [{"id": "tech:eml_laser"}],
        "edges": [{"id": "e1", "src_id": "co:x", "dst_id": "tech:eml_laser"}],
        "claims": [
            {"id": "c1", "subject_id": "tech:eml_laser"},
            {"id": "c2", "subject_id": "e1"},
        ],
    }
    result = entities.resolve_document(doc, path=path)

    assert doc["nodes"][0]["id"] == "tech:eml"
    assert doc["edges"][0]["dst_id"] == "tech:eml"
    assert doc["claims"][0]["subject_id"] == "tech:eml"
    # claim 的 subject 也可能是 edge 的 local id——那個不是實體 id，不得改寫
    assert doc["claims"][1]["subject_id"] == "e1"
    assert result["remapped"] == {"tech:eml_laser": "tech:eml"}


def test_shipped_registry_loads_and_only_registers_mechanical_basis() -> None:
    """實際出貨的 registry 必須載入得起來，且每一筆都是機械可驗的依據。"""

    entities._load.cache_clear()
    canonical = entities.load()
    assert canonical, "registry 不應為空"
    for entry in canonical.values():
        assert entry["basis"] in entities.ALLOWED_BASIS
