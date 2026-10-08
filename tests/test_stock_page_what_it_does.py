"""個股頁頁首「做什麼」（schema B0；2026-10-08 使用者：「這個公司在做甚麼東西是我們關注的…像 COHR 就寫個 CW DFB 雷射，
一目了然」「我想知道它出現在示意圖的哪一個地方」）。

`webapp.materialize.what_it_does`：敘事宣告的押的格優先；沒宣告時列圖上它供貨或開發的節點並說敘事還沒宣告（兩個來源分開寫，L12）；
在示意圖的哪一格照畫圖器的位置表對。圖這一輪讀不到不是「圖上沒有」（INV-3）。"""
from __future__ import annotations

from briefing.analyst_view import page_schema as ps
from webapp.materialize import page_extra_for, what_it_does

DIAGRAM = {"id": "optics", "title": "光", "boxes": [
    {"title": "雷射晶片", "nodes": ["tech:cw_dfb_laser", "tech:eml"]},
    {"title": "光模組", "nodes": ["tech:pluggable_transceiver"]},
]}
CW = {"node": "tech:cw_dfb_laser", "node_name": "High-power CW DFB laser", "unit": "layer", "unit_label": "層",
      "reading_id": "sr_x"}


def _view(rides: list | None = None) -> dict:
    datum = ({"status": "available", "value": rides} if rides
             else {"status": "missing", "absence_kind": "not_yet_recorded", "value": None})
    return {"bet": {"lines": [{"key": "rides", "datum": datum}]}}


def test_the_declared_bet_comes_first_and_only_its_boxes_are_named() -> None:
    what = what_it_does(_view([CW]), ["tech:eml", "tech:cw_dfb_laser", "tech:pluggable_transceiver"], {}, [DIAGRAM])
    assert what["source"] == "rides" and what["line"] == "押在：High-power CW DFB laser（層）"
    assert what["focus"] == ["tech:cw_dfb_laser"]
    # 光模組也是它坐的格，但頁首講的是押的那一格（技術鏈那一塊的圖會把其他坐的格用細虛線標出來）
    assert what["where_line"] == "示意圖上在「雷射晶片」（往下「技術鏈」有圖）"
    assert what["where"] == [{"diagram": "optics", "title": "光", "boxes": ["雷射晶片"]}]


def test_without_a_declared_bet_it_lists_the_graph_nodes_and_says_the_bet_is_not_declared() -> None:
    seats = ["tech:a", "tech:b", "tech:c", "tech:pluggable_transceiver"]
    what = what_it_does(_view(), seats, {"tech:a": "Alpha node"}, [DIAGRAM])
    assert what["source"] == "seats"
    assert what["line"] == "圖上它供貨或開發：Alpha node、tech:b、tech:c 等共 4 個（敘事還沒宣告押哪一格）"
    assert what["where_line"] == "示意圖上在「光模組」（往下「技術鏈」有圖）"
    few = what_it_does(_view(), ["tech:a"], {"tech:a": "Alpha node"}, None)
    assert few["line"] == "圖上它供貨或開發：Alpha node（敘事還沒宣告押哪一格）" and few["where_line"] is None


def test_nothing_known_is_a_named_absence_and_an_unread_graph_is_not_nothing() -> None:
    nothing = what_it_does(_view(), [], {}, [DIAGRAM])
    assert nothing["line"] is None and nothing["absence"]["kind"] == "not_yet_recorded"
    unread = what_it_does(_view(), None, {}, None)
    assert unread["line"] is None and unread["absence"]["kind"] == "upstream_unavailable" and "讀不到" in unread["absence"]["reason"]
    # 圖讀不到但敘事有押的格：押的格照印（rides 不靠這一輪的圖）
    assert what_it_does(_view([CW]), None, {}, None)["line"] == "押在：High-power CW DFB laser（層）"


def test_the_fill_table_cell_reads_the_same_three_ways() -> None:
    """填得滿表的 B0「做什麼」：有押的格或圖上有節點＝有值；讀到、兩個都沒有＝還沒寫；圖這一輪沒讀到＝這一輪沒讀到
    （承載它的敘事那一格說「還沒寫」也一樣——沒讀到的那一半可能有值）。"""
    def cell(view: dict, what: dict) -> dict:
        extra = page_extra_for("X", None, what=what) or {}
        return {r["element"]: r for r in ps.fill_table(view, extra=extra)}["B0.what_it_does"]

    assert cell(_view([CW]), what_it_does(_view([CW]), [], {}, None))["state"] == "value"
    assert cell(_view(), what_it_does(_view(), ["tech:a"], {}, None))["state"] == "value"
    assert cell(_view(), what_it_does(_view(), [], {}, None))["absence_kind"] == "not_yet_recorded"
    assert cell(_view(), what_it_does(_view(), None, {}, None))["absence_kind"] == "upstream_unavailable"


def test_a_hand_drawn_diagram_without_a_position_table_places_nothing() -> None:
    what = what_it_does(_view(), ["tech:eml"], {}, [{"id": "hand", "title": "手畫", "boxes": None}])
    assert what["line"].startswith("圖上它供貨或開發") and what["where"] == [] and what["where_line"] is None
