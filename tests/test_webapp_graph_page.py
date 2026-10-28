"""「圖」頁（2026-10-28 使用者照推薦：讀圖、走圖、層說明、結構表併成一頁；brainstorm 2026-10-28 定案 6：骨架＝層）。

守四件事：
1. **三區只有一份、每一種判讀恰好一區**：押得下去＝候選「可開」騎得上的那兩種判讀（`OPEN_READING_KINDS`，L16）；
   新增判讀種類沒進任何一區就紅——不會從圖頁安靜消失（INV-3）。
2. **`/api/v1/graph` 只接不算**：區內照讀圖 artifact 的列序；坐在這一層＝結構表 `supplies_to`（買方那一側不算，L12）；
   層內公司照首頁組序再代號、沒有個股頁的排後面；「錢在變多嗎」照抄個股頁的層序列；讀圖另外關聯的標的分開印。
3. **讀不到的分開說**：讀圖讀不到＝503；結構表／層說明／走圖讀不到＝那一格寫讀不到、別格照出；字彙表沒有分區＝整頁一區、一層不少。
4. **畫面**：四個舊路徑落到圖頁、`#/graph/<node>` 打開那一層、圖預測對錯表搬到成績單（原追蹤表）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from alpha.providers.briefs import OPEN_READING_KINDS
from alpha.structure_reading.contracts import READING_KIND_SHORT, READING_KINDS
from webapp.api import GRAPH_RESEARCH_HOLES, _graph_suppliers, create_app
from webapp.contracts import canonical_digest
from webapp.materialize import reading_zones, write_vocabularies
from webapp.store import ArtifactStore, StateArtifactStore
from webapp.structure_readings import build_structure_readings_artifact

from test_webapp_graph_walk_watches import fake_graph_walk_payload
from test_webapp_home_cards import _payload
from test_webapp_structure_table import fake_table_payload

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. 三區
# ---------------------------------------------------------------------------

def test_every_reading_kind_lands_in_exactly_one_zone() -> None:
    zones = reading_zones()
    placed = [kind for zone in zones for kind in zone["kinds"]]
    assert sorted(placed) == sorted(READING_KINDS)                     # 一種不少、一種不重
    assert set(zones[0]["kinds"]) == set(OPEN_READING_KINDS)           # 押得下去＝可開騎得上的那兩種（同一份）
    assert [z["key"] for z in zones] == ["bettable", "undecided", "not_opportunity"]
    assert set(READING_KIND_SHORT) == set(READING_KINDS)               # 短名與長句同一組鍵


# ---------------------------------------------------------------------------
# 2. 只接不算
# ---------------------------------------------------------------------------

def test_suppliers_are_the_supply_side_only_and_the_chain_is_copied() -> None:
    table = {"rows": [
        {"company_id": "co:meta", "relation": "depends_on", "bottleneck": "tech:x", "ticker": "META",
         "company_label": "Meta", "bottleneck_name": "X", "anchor_basis": "row", "chain": ["tech:a", "tech:x"],
         "chain_names": ["A", "X"]},
        {"company_id": "co:b", "relation": "supplies_to", "bottleneck": "tech:x", "ticker": "BBB", "company_label": "Bee"},
        {"company_id": "co:b", "relation": "supplies_to", "bottleneck": "tech:x", "ticker": "BBB", "company_label": "Bee"},
        {"company_id": "co:a", "relation": "supplies_to", "bottleneck": "tech:x", "ticker": None, "company_label": "Ay"},
    ]}
    suppliers, chains, names = _graph_suppliers(table)
    assert [s["company_id"] for s in suppliers["tech:x"]] == ["co:b", "co:a"]   # 買方不算、重複只留一筆、列序照表
    assert chains["tech:x"] == [("tech:a", "A"), ("tech:x", "X")] and names["tech:x"] == "X"
    assert _graph_suppliers(None) == ({}, {}, {})


READING_ROWS = [
    {"node": "mat:aaa", "unit": "layer", "kind": "undecided", "reading_id": "sr_1", "status": "current",
     "read_on": "2026-10-20", "expires": "2027-03-31", "tickers": [], "reading": "判不出：缺供給側", "citations": [],
     "disproof": [], "needs_reread": False, "reread_reasons": []},
    {"node": "mat:zzz", "unit": "socket", "kind": "moat", "reading_id": "sr_2", "status": "stale", "read_on": "2026-10-01",
     "expires": "2027-03-31", "tickers": [], "reading": "換不掉", "citations": [], "disproof": [],
     "needs_reread": True, "reread_reasons": ["供給側多了一家"]},
    {"node": "tech:ai_switch", "unit": "layer", "kind": "volume", "reading_id": "sr_3", "status": "current",
     "read_on": "2026-10-21", "expires": "2027-03-31", "tickers": ["NVDA", "META"], "reading": "**量**：產能補不上",
     "citations": [{"angle": "demand_side", "quote": "q" * 30, "edge": ["co:nvidia", "supplies_to", "tech:ai_switch"],
                    "source_id": "doc_1", "independent": True}],
     "disproof": [{"condition": "第二家量產", "source": "doc_1", "watch_id": "ew_1", "watch_status": "active"}],
     "needs_reread": False, "reread_reasons": []},
    {"node": "tech:nnn", "unit": "layer", "kind": "neither", "reading_id": "sr_4", "status": "current",
     "read_on": "2026-10-22", "expires": "2027-03-31", "tickers": [], "reading": "不卡", "citations": [],
     "disproof": [], "needs_reread": False, "reread_reasons": []},
    {"node": "mat:gone", "unit": None, "reading_id": None, "status": None},
    # 節點另有現行的層讀圖、插槽讀圖全部撤回：撤回那一行要帶單位，否則讀起來像整層撤回
    {"node": "mat:aaa", "unit": "socket", "reading_id": None, "status": None},
]
RIDE = {"node": "tech:ai_switch", "node_name": "Data-center switch", "unit_label": "層", "kind_label": "B：量的賭注"}
GROWTH = {"kind": "layer", "basis_label": "代表公司同一曆季營收加總（換美元）的年增",
          "latest": {"yoy": 0.3139, "period": "2026Q3", "members": ["co:nvidia"]}}


def _page(ticker, group, *, rides=(), growth=None, company_id=None, short=None):
    payload = _payload(ticker, group, rides=rides, short=short)
    payload["company_id"] = company_id or f"co:{ticker.lower()}"
    if growth:
        payload["path_layers"] = {"hops": {"tech:ai_switch": growth}}
    payload["content_digest"] = canonical_digest({k: v for k, v in payload.items() if k != "content_digest"})
    return payload


def _app(tmp_path, *, table=True, walk=True, vocab=True, readings=READING_ROWS):
    store = ArtifactStore(tmp_path)
    for payload in (_page("NVDA", "missing", rides=[RIDE], growth=GROWTH, company_id="co:nvidia", short="輝達"),
                    _page("ZZZ", "pass")):
        store.write(payload)
    if vocab:
        write_vocabularies(store)
    state = StateArtifactStore(tmp_path / "state")
    if readings is not None:
        state.write(build_structure_readings_artifact(rows=readings))
    if table:
        state.write(fake_table_payload())
    if walk:
        state.write(fake_graph_walk_payload())
    return TestClient(create_app(tmp_path))


def test_zones_follow_the_vocabulary_and_keep_the_artifact_order(tmp_path) -> None:
    body = _app(tmp_path).get("/api/v1/graph").json()
    zones = {z["key"]: z for z in body["zones"]}
    assert [z["key"] for z in body["zones"]] == ["bettable", "undecided", "not_opportunity"]
    assert [layer["node"] for layer in zones["bettable"]["layers"]] == ["mat:zzz", "tech:ai_switch"]   # 讀圖列序
    assert [layer["node"] for layer in zones["undecided"]["layers"]] == ["mat:aaa"]
    assert zones["not_opportunity"]["expanded"] is False and zones["bettable"]["kinds"] == ["moat", "volume"]
    assert body["counts"]["by_kind"] == {"undecided": 1, "moat": 1, "volume": 1, "neither": 1}
    assert body["withdrawn"] == ["mat:gone", "mat:aaa（插槽）"]                 # 撤回的照列，不消失；單位撤回帶單位
    socket = zones["bettable"]["layers"][0]
    assert socket["unit_label"] == "插槽" and socket["kind_label"] == READING_KIND_SHORT["moat"]
    assert socket["needs_reread"] is True and socket["reread_reasons"] == ["供給側多了一家"]


def test_a_layer_copies_who_sits_there_the_money_line_and_the_reading(tmp_path) -> None:
    body = _app(tmp_path).get("/api/v1/graph").json()
    layer = next(layer for z in body["zones"] for layer in z["layers"] if layer["node"] == "tech:ai_switch")
    # 坐在這一層＝結構表 supplies_to：NVDA 有個股頁（短名、狀態、主清單）排前面；Lumentum 沒有代號、排後面，
    # 夾具的名冊沒有它的名字——照印 id，不猜（INV-1）
    assert [(c["name"], c["page"], c["main"]) for c in layer["companies"]] == [("輝達", True, True),
                                                                              ("co:lumentum", False, False)]
    assert layer["companies"][0]["state"] == "missing"
    assert layer["also_linked"] == ["META"]                                     # 讀圖另外關聯、不是供應商——分開印
    assert layer["waiting"] == ["輝達"]                                          # 押在這一層的缺 X
    assert layer["growth"]["yoy"] == 0.3139 and layer["growth"]["members"] == ["輝達"]   # 照抄、成員印名字
    assert layer["reading"]["citations"][0]["source_id"] == "doc_1" and layer["reading"]["disproof"][0]["watch_id"] == "ew_1"
    others = [layer for z in body["zones"] for layer in z["layers"] if layer["node"] != "tech:ai_switch"]
    assert all(layer["growth"] is None and layer["companies"] == [] for layer in others)   # 量不到就不印、圖上沒有就空
    assert body["counts"]["growth_measured"] == 1


def test_holes_split_research_gaps_from_upkeep(tmp_path) -> None:
    holes = _app(tmp_path).get("/api/v1/graph").json()["holes"]
    walk = fake_graph_walk_payload()
    assert [q["key"] for q in holes["research"]] == [q["key"] for q in walk["questions"] if q["key"] in GRAPH_RESEARCH_HOLES]
    assert [q["key"] for q in holes["upkeep"]] == [q["key"] for q in walk["questions"] if q["key"] not in GRAPH_RESEARCH_HOLES]
    by_key = {q["key"]: q for q in walk["questions"]}
    assert all(q["hit_n"] == by_key[q["key"]]["hit_n"] for q in holes["research"] + holes["upkeep"])   # 照抄
    assert set(GRAPH_RESEARCH_HOLES) <= set(by_key)                         # 走圖改名了這裡會紅，不會安靜變空


# ---------------------------------------------------------------------------
# 3. 讀不到的分開說
# ---------------------------------------------------------------------------

def test_missing_inputs_say_so_and_the_rest_still_renders(tmp_path) -> None:
    body = _app(tmp_path, table=False, walk=False).get("/api/v1/graph").json()
    assert "structure_table 讀不到" in body["absences"]["structure_table"]["reason"]
    assert body["holes"]["absence"]["kind"] == "upstream_unavailable" and body["holes"]["research"] == []
    assert sum(len(z["layers"]) for z in body["zones"]) == 4                   # 骨架照出
    unread = _app(tmp_path / "none", readings=None).get("/api/v1/graph")
    assert unread.status_code == 503 and unread.json()["error"]["state_kind"] == "structure_readings"


def test_without_zone_vocabulary_every_layer_is_still_on_the_page(tmp_path) -> None:
    body = _app(tmp_path, vocab=False).get("/api/v1/graph").json()
    assert [z["key"] for z in body["zones"]] == ["all"] and len(body["zones"][0]["layers"]) == 4


def test_a_kind_the_vocabulary_does_not_know_gets_its_own_zone(tmp_path) -> None:
    rows = READING_ROWS[:3] + [dict(READING_ROWS[3], kind="brand_new_kind")]
    body = _app(tmp_path, readings=rows).get("/api/v1/graph").json()
    assert body["zones"][-1]["key"] == "unzoned" and body["zones"][-1]["layers"][0]["node"] == "tech:nnn"


# ---------------------------------------------------------------------------
# 4. 畫面
# ---------------------------------------------------------------------------

def test_the_four_pages_are_one_graph_page() -> None:
    static = ROOT / "webapp" / "static"
    source = (static / "app.js").read_text(encoding="utf-8")
    html = (static / "index.html").read_text(encoding="utf-8")
    for gone in ("function renderStructureTable", "function renderGraphWalk", "function renderStructureReadings",
                 "function renderLayerNotes(", "function walkHitList", "function readingRow"):
        assert gone not in source, gone
    labels = re.findall(r'<a href="#/[^"]*" data-view="[^"]+"[^>]*>([^<]+)</a>', html)
    assert "圖" in labels               # 導覽列幾頁、什麼順序只在一個地方數：`tests/test_webapp_report_card.py`
    for old in ("#/structure-table", "#/graph-walk", "#/structure-readings", "#/layer-notes"):
        assert f'href="{old}"' not in html
    assert "['structure-table', 'graph-walk', 'structure-readings', 'layer-notes'].includes(target)" in source
    assert "target.startsWith('graph/')" in source and "layer-focus" in source      # 打開那一層
    assert "renderPredictions(payload.predictions, payload.prediction_groups)" in source   # 預測表搬到成績單
    assert "back.href = '#/graph/' + encodeURIComponent(node)" in source            # 層說明回到圖頁那一層
    graph = source[source.index("async function renderGraph("):source.index("/* 圖預測對錯表")]
    assert ".sort(" not in graph and "payload.zones" in graph                       # 區與順序照抄 API
