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
    tmp_path.mkdir(parents=True, exist_ok=True)
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


def test_unregistered_basis_is_rejected(tmp_path) -> None:
    """`basis` 是封閉字彙，寫入端連沒登記過的值都要拒絕——自由字串會讓寫的人
    以為表達了一個沒被記錄的區別（L16-3）。"""

    path = _registry(tmp_path, {
        "tech:nand": {"name": "NAND", "aliases": ["tech:nand_flash"], "basis": "semantic_judgment"},
    })
    with pytest.raises(entities.EntityAliasError):
        entities.load(path)


def test_semantic_basis_requires_an_approval_receipt(tmp_path) -> None:
    """語意判斷可以登記，但**沒有核准 receipt 就不行**。

    2026-09-10 由「只接受機械依據」放寬到接受 `semantic_reviewed`；放行與收緊必須
    同時發生（AGENTS），補償控制就是這道 receipt 強制。少了它，registry 會慢慢變成
    「某個 agent 當時覺得它們是同一個」的堆積場，而那正是 canonical identity 最不該
    有的東西（L15）。
    """

    base = {"name": "NAND", "aliases": ["tech:nand_flash"], "basis": "semantic_reviewed"}

    # 沒有 receipt → 擋
    with pytest.raises(entities.EntityAliasError):
        entities.load(_registry(tmp_path / "a", {"tech:nand": dict(base)}))

    # receipt 格式不對（口頭同意不是授權載體）→ 擋
    with pytest.raises(entities.EntityAliasError):
        entities.load(_registry(
            tmp_path / "b", {"tech:nand": {**base, "approval_receipt": "使用者說可以"}}
        ))

    # 指向 pq2 編號 → 收
    ok = entities.load(_registry(
        tmp_path / "c", {"tech:nand": {**base, "approval_receipt": "todo:505"}}
    ))
    assert ok["tech:nand"]["approval_receipt"] == "todo:505"


def test_mechanical_basis_needs_no_receipt(tmp_path) -> None:
    """機械依據不必帶 receipt——它本來就任何人重跑都得到同一組，沒有判斷可核准。"""

    path = _registry(tmp_path, {
        "tech:eml": {"name": "EML", "aliases": ["tech:eml_laser"], "basis": "name_identical"},
    })
    assert entities.load(path)["tech:eml"]["basis"] == "name_identical"


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
        # 語意登記一律附得出核准編號——這是本 registry 與「某人的意見」的分界
        if entry["basis"] in entities._BASIS_REQUIRES_RECEIPT:
            assert entities._RECEIPT_PATTERN.match(entry["approval_receipt"])


#: 刻意保留舊 id 的 config：凍結的歷史基準（point-in-time，不隨合併改寫）。
_FROZEN_CONFIGS = {"entity_aliases.json", "graph_baselines.json"}


def test_live_config_node_ids_are_canonical() -> None:
    """活的 config 寫死的非公司節點 id 必須是名冊的 canonical，寫成已併走的別名就紅。

    事發（2026-10-22 research-drain）：[506] 把 tech:dram_production 併進 tech:dram_manufacturing 之後，
    config/sector_anchors.json「記憶體」仍寫舊 id，而 query/bottleneck.load_demand_anchors 讀原字串、不經名冊——
    那個錨從 [506] 起默默失效（INV-3）。合併改了名冊卻沒改 config，沒有任何東西會叫。
    """
    import re
    from pathlib import Path

    node_id = re.compile(r"^(?:tech|mat|prod|std):[A-Za-z0-9_]+$")
    entities._load.cache_clear()
    stale: list[tuple[str, str, str]] = []

    def walk(obj, name: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                walk(key, name)
                walk(value, name)
        elif isinstance(obj, list):
            for value in obj:
                walk(value, name)
        elif isinstance(obj, str) and node_id.match(obj) and entities.resolve(obj) != obj:
            stale.append((name, obj, entities.resolve(obj)))

    root = Path(__file__).resolve().parent.parent / "config"
    for path in sorted(root.glob("*.json")):
        if path.name not in _FROZEN_CONFIGS:
            walk(json.loads(path.read_text(encoding="utf-8")), path.name)
    assert stale == [], f"config 寫了已併走的別名 id（改成 canonical）：{stale}"


# ---------------------------------------------------------------------------
# 批次二 E13 ③：刻意不併（keep_separate，要 receipt）與留待（pending）結構化
# ---------------------------------------------------------------------------

def _registry_with(entry_extra: dict) -> dict:
    return {"schema_version": "entity-aliases-v1", "canonical": {
        "tech:nand": {"name": "NAND", "aliases": ["tech:nand_flash"], "basis": "name_identical", **entry_extra}}}


def test_keep_separate_needs_a_pq2_receipt_like_a_semantic_merge() -> None:
    from identity.entities import EntityAliasError, _validate

    ok = {"keep_separate": [{"id": "tech:3d_nand_manufacturing", "reason": "證據不足", "approval_receipt": "todo:505"}]}
    _validate(_registry_with(ok))
    for bad in ({"id": "tech:3d_nand_manufacturing", "reason": "證據不足", "approval_receipt": None},
                {"id": "tech:3d_nand_manufacturing", "reason": "證據不足", "approval_receipt": "口頭同意"},
                {"id": "tech:nand_flash", "reason": "本組成員", "approval_receipt": "todo:505"},
                {"id": "tech:3d_nand_manufacturing", "reason": " ", "approval_receipt": "todo:505"},
                {"id": "tech:3d_nand_manufacturing", "approval_receipt": "todo:505"}):
        with pytest.raises(EntityAliasError):
            _validate(_registry_with({"keep_separate": [bad]}))


def test_pending_is_a_record_with_ids_and_a_reason() -> None:
    from identity.entities import EntityAliasError, _validate

    _validate(_registry_with({"pending": [{"ids": ["tech:dram", "tech:dram_technology"], "reason": "留待研究判斷"}]}))
    for bad in ({"ids": [], "reason": "x"}, {"ids": ["co:x"], "reason": "x"}, {"ids": ["tech:dram"], "reason": ""}):
        with pytest.raises(EntityAliasError):
            _validate(_registry_with({"pending": [bad]}))


def test_only_keep_separate_leaves_the_question_and_pending_rides_along() -> None:
    from query.duplicate_nodes import bucketize

    canonical = {
        "tech:nand": {"aliases": ["tech:nand_flash"], "basis": "name_identical",
                      "note": "tech:3d_nand_manufacturing 刻意不併",
                      "keep_separate": [{"id": "tech:3d_nand_manufacturing", "reason": "證據不足",
                                         "approval_receipt": "todo:505"}]},
        "tech:dram_manufacturing": {"aliases": ["tech:dram_production"], "basis": "name_identical",
                                    "note": "tech:dram／tech:dram_technology 名稱不同，留待研究判斷。",
                                    "pending": [{"ids": ["tech:dram", "tech:dram_technology"], "reason": "留待"}]},
        "tech:near_package_optics": {"aliases": ["tech:npo"], "basis": "semantic_reviewed",
                                     "approval_receipt": "todo:752",
                                     "pending": [{"ids": ["tech:cpo"], "reason": "不含 tech:cpo"}]},
    }
    pairs = [{"pair": ["tech:3d_nand_manufacturing", "tech:nand_flash"]},
             {"pair": ["tech:dram", "tech:dram_technology"]},
             {"pair": ["tech:cpo", "tech:near_package_optics"]},
             {"pair": ["tech:cpo", "tech:glass_cpo"]}]
    buckets = bucketize(pairs, canonical)
    assert [p["pair"] for p in buckets["kept_separate"]] == [["tech:3d_nand_manufacturing", "tech:nand_flash"]]
    assert [p["pair"] for p in buckets["mentioned"]] == [["tech:dram", "tech:dram_technology"]]
    assert buckets["mentioned"][0]["pending"][0]["reason"] == "留待"
    unmentioned = {tuple(p["pair"]): p for p in buckets["unmentioned"]}
    assert unmentioned[("tech:cpo", "tech:near_package_optics")]["pending"][0]["reason"] == "不含 tech:cpo"
    # 留待只貼在它說的那一對：cpo 與它其他變體的那一對不帶 NPO 那筆的留待
    assert unmentioned[("tech:cpo", "tech:glass_cpo")]["pending"] == []


def test_the_real_registry_still_loads_with_the_structured_fields() -> None:
    from identity import entities

    canonical = entities.load()
    assert canonical["tech:nand"]["keep_separate"][0]["approval_receipt"] == "todo:505"
    # 2026-10-23 [842]：tech:dram 由「留待」變成別名（使用者 go）；留待的只剩 tech:dram_technology（要逐邊更正）
    assert "tech:dram" in canonical["tech:dram_manufacturing"]["aliases"]
    assert canonical["tech:dram_manufacturing"]["approval_receipt"] == "todo:842"
    assert any("tech:dram_technology" in item["ids"] for item in canonical["tech:dram_manufacturing"]["pending"])
    assert canonical["tech:uhp_laser"]["keep_separate"][0]["approval_receipt"] == "todo:840"
