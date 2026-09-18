"""`enables` 的方向矛盾：抽取當下就擋，而不是載入之後靠人發現。

事發（2026-09-18）：`schema/vocab.json` 與 `prompts/extract_system.md` 對 `enables`
的定義只有一個——**A's adoption drives demand for B**（A 的採用帶動 B 的需求
⇒ B 被 A 需要）。但圖裡有一批邊是照相反的讀法寫的（A 是 B 的必要投入），
而 `query/bottleneck.py` 的走訪也實作了相反那一邊，於是**兩種意思長期並存且無人察覺**。

最硬的證據是一份文件自己就矛盾：`coherent_q2fy26_cpo` 同時寫出
`tech:ai_switch enables tech:cpo` 與 `tech:cpo enables tech:ai_switch`，
而 `tech:cpo is_component_of tech:ai_switch` 早就在圖裡——同一對節點三條邊、
其中一條純重複，載入時**零訊號**（L13-2：沒發生與沒看到同形）。

實測鑑別力：239 份既有抽取只命中 2 份（0.8%）。逐條重判是 pq2 [607]。
"""
from __future__ import annotations

import json
from pathlib import Path

from loader.validate import validate


def _doc(doc_id: str, edges: list[tuple[str, str, str]]) -> dict:
    sid = f"{doc_id}_s1"
    node_ids = sorted({n for e in edges for n in (e[0], e[2])})
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id, "title": doc_id, "source_type": "filing",
            "evidence_tier": 1, "origin_entity": doc_id,
        },
        "sources": [{"id": sid, "locator": "p.1", "quote": "Example quote"}],
        "nodes": [
            {"id": n, "type": "Technology", "name": n, "abstraction_level": "device_chip",
             "role": "bottleneck_supplier", "aliases": [], "attributes": {},
             "confidence": 0.8, "source_ids": [sid]}
            for n in node_ids
        ],
        "edges": [
            {"id": f"e{i}", "src_id": s, "dst_id": d, "relation": r,
             "attributes": {}, "confidence": 0.7, "source_ids": [sid]}
            for i, (s, r, d) in enumerate(edges, 1)
        ],
        "claims": [],
    }


def _errors(tmp_path: Path, doc: dict) -> list[str]:
    path = tmp_path / f"{doc['source_doc']['doc_id']}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return [e for e in validate(str(path)) if "因果相反" in e]


def test_enables_against_a_necessary_input_edge_is_rejected(tmp_path: Path) -> None:
    """`A enables B` ＋「A 是 B 的必要投入」＝ 因果相反，不可能同時為真。"""
    for edges in (
        [("tech:a", "enables", "tech:b"), ("tech:b", "depends_on", "tech:a")],
        [("tech:a", "enables", "tech:b"), ("tech:a", "is_component_of", "tech:b")],
        [("tech:a", "enables", "tech:b"), ("tech:b", "enables", "tech:a")],
    ):
        errs = _errors(tmp_path, _doc("new_doc", edges))
        assert errs, f"{edges} 應該被擋下"
        assert all(not e.startswith("WARN") for e in errs), "新文件必須是硬擋，不是 WARN"


def test_the_legitimate_coexistence_is_not_flagged(tmp_path: Path) -> None:
    """規則必須是**方向感知**的——這一組兩條都對，不得誤傷。

    `cpo is_component_of ai_switch`（CPO 是 AI switch 裡的零件）
    ＋ `ai_switch enables cpo`（AI switch 的採用帶動 CPO 的需求）
    ——兩者相容，而且正是 `enables` 該有的用法。
    只看「這兩個節點之間有兩條邊」的規則會把它一起抓走，那就變成恆亮（L14-4）。
    """
    errs = _errors(tmp_path, _doc("ok_doc", [
        ("tech:cpo", "is_component_of", "tech:ai_switch"),
        ("tech:ai_switch", "enables", "tech:cpo"),
    ]))
    assert errs == [], f"合法共存不得被抓：{errs}"


def test_the_grandfather_list_is_empty_and_the_corpus_is_clean() -> None:
    """例外清單是個**常駐計數器**，它的出口是歸零——而 2026-09-18 它到了。

    設立時它有兩筆（`coherent_q2fy26_cpo` 的 `ai_switch ⇄ cpo` 雙向、
    `gfs_20_f_20260227` 的 `sme enables globalfoundries` 與 `globalfoundries depends_on sme`
    並存）。pq2 [607]／[608] 把那些邊改掉之後，全庫 239 份掃描命中 **0 條**。

    ⚠ 本測試鎖兩件事：①清單確實空了——所以從今天起沒有任何文件享有豁免；
    ②既有語料乾淨——**若有人日後又載進一條矛盾邊，這裡會紅**，而不是靜悄悄多一筆豁免。
    """
    from loader.validate import validate

    from pathlib import Path as _P
    import inspect
    import loader.validate as _v

    source = inspect.getsource(_v.validate)
    assert "_KNOWN_ENABLES_CONTRADICTIONS: dict[str, set[tuple[str, str]]] = {}" in source, (
        "例外清單不得再長出新條目——要加得先解釋為什麼那筆不能直接修掉")

    root = _P(__file__).resolve().parent.parent / "extractions"
    hits = [(f.name, e) for f in sorted(root.glob("*.json"))
            for e in validate(str(f)) if "因果相反" in e]
    assert hits == [], f"語料裡又出現 enables 方向矛盾：{hits[:3]}"
