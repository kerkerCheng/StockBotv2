"""技術示意圖的載入與檢查（個股頁 S5b 第二段，2026-10-08）：檢查不過就不嵌、理由照實列出；涵蓋節點的頁才拿得到；
沒有通過的量測紀錄（規則 9：字不重疊、不出框、不壓框線）也不嵌。"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from webapp.diagrams import (CHECK_VERSION, diagrams_for_nodes, load_diagrams, meta_problems, receipt_path,
                             svg_digest, svg_problems)

CLEAN = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 200">'
         '<defs><marker id="arrow"><path d="M0 0L6 3L0 6Z"/></marker></defs>'
         '<rect x="10" y="10" width="120" height="40"/><text x="20" y="35">交換器</text>'
         '<line x1="70" y1="50" x2="70" y2="90" marker-end="url(#arrow)"/></svg>')
META = {"title": "示意", "caption": "示意：交換器到雷射", "nodes_shown": ["tech:cw_dfb_laser"],
        "sources": [{"ref": "raw:doc_a.txt", "what": "雷射層"}], "drawn_at": "2026-10-08"}


def _receipt(svg: str, **override) -> dict:
    return {"check_version": CHECK_VERSION, "svg_sha256": svg_digest(svg), "measured_at": "2026-10-08T00:00:00+00:00",
            "texts": 1, "overlaps": [], "outside": [], "crossing": [], **override}


def _write(dir_: Path, name: str, svg: str, meta: dict, *, receipt: dict | None = None, measured: bool = True) -> None:
    (dir_ / f"{name}.svg").write_text(svg, encoding="utf-8")
    (dir_ / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    if measured:
        receipt_path(dir_, name).write_text(json.dumps(receipt or _receipt(svg), ensure_ascii=False), encoding="utf-8")


def test_a_clean_svg_passes_and_internal_references_are_allowed() -> None:
    assert svg_problems(CLEAN) == []


def test_anything_that_executes_or_loads_outside_is_rejected() -> None:
    cases = {
        "script": CLEAN.replace("</svg>", "<script>alert(1)</script></svg>"),
        "事件屬性": CLEAN.replace("<rect ", '<rect onclick="x()" '),
        "外部連結": CLEAN.replace("</svg>", '<a href="https://example.com"><text>x</text></a></svg>'),
        "外部 url()": CLEAN.replace('marker-end="url(#arrow)"', 'fill="url(https://example.com/x.png)"'),
        "foreignObject": CLEAN.replace("</svg>", "<foreignObject><div>x</div></foreignObject></svg>"),
        "image": CLEAN.replace("</svg>", '<image href="#local"/></svg>'),
    }
    for label, svg in cases.items():
        assert svg_problems(svg), label
    assert svg_problems("<svg") and svg_problems('<g xmlns="http://www.w3.org/2000/svg"/>')
    assert any("viewBox" in p for p in svg_problems('<svg xmlns="http://www.w3.org/2000/svg"/>'))


def test_a_diagram_without_sources_or_nodes_is_not_embedded_and_says_why(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text("x", encoding="utf-8")
    assert meta_problems(META, raw_dir=raw) == []
    assert any("sources" in p for p in meta_problems({**META, "sources": []}, raw_dir=raw))
    assert any("nodes_shown" in p for p in meta_problems({**META, "nodes_shown": []}, raw_dir=raw))
    assert any("co:x" in p for p in meta_problems({**META, "nodes_shown": ["co:x"]}, raw_dir=raw))
    assert any("找不到" in p for p in meta_problems({**META, "sources": [{"ref": "raw:missing.txt"}]}, raw_dir=raw))


def test_loading_embeds_the_good_ones_as_data_uri_and_lists_the_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text("x", encoding="utf-8")
    d = tmp_path / "diagrams"
    d.mkdir()
    _write(d, "optics_chain", CLEAN, META)
    _write(d, "bad_one", CLEAN.replace("</svg>", "<script/></svg>"), META)
    loaded = load_diagrams(d, raw_dir=raw)
    assert [x["id"] for x in loaded["diagrams"]] == ["optics_chain"]
    assert loaded["rejected"][0]["id"] == "bad_one" and loaded["rejected"][0]["problems"]
    src = loaded["diagrams"][0]["src"]
    assert src.startswith("data:image/svg+xml;base64,") and base64.b64decode(src.split(",", 1)[1]).decode() == CLEAN
    assert diagrams_for_nodes(loaded, ["tech:cw_dfb_laser", "co:x"])[0]["id"] == "optics_chain"
    assert diagrams_for_nodes(loaded, ["tech:cpo"]) == []
    assert load_diagrams(tmp_path / "absent") == {"diagrams": [], "rejected": []}


def test_only_a_passing_measurement_of_this_exact_svg_lets_a_diagram_in(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text("x", encoding="utf-8")
    d = tmp_path / "diagrams"
    d.mkdir()
    _write(d, "measured", CLEAN, META)
    _write(d, "never_measured", CLEAN, META, measured=False)
    _write(d, "edited_after", CLEAN, META, receipt=_receipt(CLEAN.replace("交換器", "改過")))
    _write(d, "overlapping", CLEAN, META, receipt=_receipt(CLEAN, overlaps=["甲 ↔ 乙"]))
    _write(d, "on_the_border", CLEAN, META, receipt=_receipt(CLEAN, crossing=["圖上：… ↔ 框線"]))
    _write(d, "old_checker", CLEAN, META, receipt=_receipt(CLEAN, check_version=CHECK_VERSION - 1))
    _write(d, "blank_page", CLEAN, META, receipt=_receipt(CLEAN, texts=0))
    loaded = load_diagrams(d, raw_dir=raw)
    assert [x["id"] for x in loaded["diagrams"]] == ["measured"]
    why = {r["id"]: " ".join(r["problems"]) for r in loaded["rejected"]}
    assert set(why) == {"never_measured", "edited_after", "overlapping", "on_the_border", "old_checker", "blank_page"}
    assert "沒有量測紀錄" in why["never_measured"] and "圖改過" in why["edited_after"]
    assert "字疊字 1" in why["overlapping"] and "壓框線 1" in why["on_the_border"]
    assert "舊版" in why["old_checker"] and "0 段字" in why["blank_page"]
    # 量測紀錄本身不被當成一張圖（不會多出 id 為 xxx.check 的拒收）
    assert not any(r["id"].endswith(".check") for r in loaded["rejected"])


BOX = {"title": "雷射", "nodes": ["tech:cw_dfb_laser"], "top": 10, "height": 40, "left": 10, "span": 120}


def _geometry(svg: str, boxes: list) -> dict:
    return {"svg_sha256": svg_digest(svg), "boxes": boxes}


def test_the_position_table_must_belong_to_this_svg_and_cover_exactly_the_nodes_shown(tmp_path: Path) -> None:
    """2026-10-08 使用者：「我想知道它出現在示意圖的哪一個地方」——畫圖器寫的位置表讓個股頁標「在這裡」。位置表綁 SVG：
    圖改過沒重畫、格子落在圖外、一個節點兩格、節點和 nodes_shown 對不上——標記會標錯地方，整張不嵌。沒有位置表（手畫）照嵌、
    `boxes` 是 None（個股頁照實說標不出），不是空清單。"""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text("x", encoding="utf-8")
    d = tmp_path / "diagrams"
    d.mkdir()
    _write(d, "placed", CLEAN, {**META, "geometry": _geometry(CLEAN, [BOX, {**BOX, "title": "框外的說明", "nodes": []}])})
    _write(d, "hand_drawn", CLEAN, META)
    _write(d, "stale", CLEAN, {**META, "geometry": _geometry(CLEAN.replace("交換器", "改過"), [BOX])})
    _write(d, "extra_node", CLEAN, {**META, "geometry": _geometry(CLEAN, [{**BOX, "nodes": ["tech:cw_dfb_laser", "tech:eml"]}])})
    _write(d, "outside", CLEAN, {**META, "geometry": _geometry(CLEAN, [{**BOX, "top": 190}])})
    _write(d, "twice", CLEAN, {**META, "geometry": _geometry(CLEAN, [BOX, {**BOX, "title": "又一格"}])})
    _write(d, "untitled", CLEAN, {**META, "geometry": _geometry(CLEAN, [{**BOX, "title": " "}])})
    loaded = load_diagrams(d, raw_dir=raw)
    by_id = {x["id"]: x for x in loaded["diagrams"]}
    assert set(by_id) == {"placed", "hand_drawn"}
    placed = by_id["placed"]
    assert (placed["width"], placed["height"]) == (360.0, 200.0)              # 寬高照 SVG 的 viewBox，不另存一份
    assert [b["title"] for b in placed["boxes"]] == ["雷射", "框外的說明"] and placed["boxes"][0]["nodes"] == ["tech:cw_dfb_laser"]
    assert by_id["hand_drawn"]["boxes"] is None
    why = {r["id"]: " ".join(r["problems"]) for r in loaded["rejected"]}
    assert "位置表沒跟著重畫" in why["stale"] and "對不上" in why["extra_node"] and "圖外" in why["outside"]
    assert "兩格" in why["twice"] and "沒有名字" in why["untitled"]
