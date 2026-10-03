"""Phase 6 新管線的 full chain（Step 6.9；plan 2026-10-02-002 §10）：夾具輸入 → 真的分類與組裝函式 → state artifact →
心跳文字／個股頁。**斷言的是數字與標籤出現在下游**（結構表的列、插槽視角的旁註、層計數器、走圖第 2 型、心跳那兩行、
讀圖引用核對、個股頁那一格），不是函式會動（L13）。

兩條鏈：
1. 證據鏈：夾具 assertion 涵蓋五種情形——客戶 origin 引文不具名、發布者轉述、發布者具名非轉述、名冊新寫法、身分合併前後。
   同一份圖用「6.0 的名冊」與「補完寫法、合併身分之後的名冊」各跑一次：`query.structure._classify_edges` → 層視角與
   `build_socket_view` → `structure_table` → `query.layer_stats`（`corroboration_withheld`、`ec_without_naming_quote` 恆 0、
   對前一次的升降）→ `query.graph_walk.walk` 第 2 型 → graph_walk artifact → 心跳段 3 的「層：」「走圖：」→
   `verify_citations` 對不具名的 independent 引用拒收、補完寫法後收下。
2. 稀釋燈鏈：夾具 companyfacts 發行金額＋夾具募資文件表（正式寫入路徑 `store_offerings`）→ `_equity_issuance` →
   `wipeout_flags` → `alpha.three_questions.evaluate`（會死嗎那一題）→ read model → `build_analyst_view` →
   `materialize_view` → 個股頁首屏那一格（overview 的燈）與稽核區那一列（三題面板；APP 的 `threeQuestionsCard` 印它）。

外部世界（Neo4j、EDGAR、名冊與發布者設定檔）一律以夾具替換，不打網路；既有三支 full chain 測試不動。
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import crons.heartbeat as hb
import query.origin_resolution as origin_resolution
import query.structure as qs
from query.bottleneck import EVIDENCE_LABEL, structure_table
from query.graph_walk import walk
from query.layer_stats import compute_layer_stats
from query.origin_resolution import PUBLISHER_KINDS, load_publishers
from query.sub_language import SubLanguage
from webapp.materialize import build_graph_walk_artifact
from webapp.store import StateArtifactStore

NOW = datetime(2026, 10, 3, 4, 0, tzinfo=timezone.utc)
LANG = SubLanguage(version=1, variant="test", terms=("sole supplier", "no alternative"))
LAYERS = ("mat:x", "mat:z", "mat:q")


# ---------------------------------------------------------------------------
# 夾具：名冊（6.0 那一版／補完之後）、發布者、assertion 與逐字
# ---------------------------------------------------------------------------

class _Company:
    """形狀照真的 `CompanyIdentity`：名字只在 `display_name`／`name_aliases`，`aliases` 是交易代號（L17 的教訓）。"""

    def __init__(self, cid, display_name, *name_aliases):
        self.company_id, self.display_name, self.name_aliases, self.aliases = cid, display_name, name_aliases, ()


class _Registry:
    def __init__(self, *, after: bool):
        companies = [
            # 名冊新寫法（6.3a 的形狀）：客戶的引文寫「SPX」，6.0 的名冊沒有這個寫法
            _Company("co:supp", "Suppco Holdings Inc.", *(("Suppco", "SPX") if after else ("Suppco",))),
            _Company("co:cust", "Customer Corp"),
            _Company("co:other", "Otherco Ltd.", "Otherco"),
            # 身分合併前後（6.2 OpenLight 的形狀）：同一家兩個代號、每個寫法都共用 → 名冊無名可比；合併後只剩一個
            _Company("co:dup_a", "Dupe Labs"),
            _Company("co:maker", "Maker Co"),
        ]
        if not after:
            companies.append(_Company("co:dup_b", "Dupe Labs"))
        self._c = {c.company_id: c for c in companies}

    @property
    def companies(self):
        return tuple(self._c.values())

    def company(self, cid):
        return self._c.get(cid)

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return cid in self._c

    def research_ticker(self, cid):
        return None


@pytest.fixture()
def publishers(tmp_path: Path):
    path = tmp_path / "publishers.json"
    path.write_text(json.dumps({
        "schema_version": 1, "kinds": {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
        "publishers": [{"origin": "TrendForce", "kind": "industry_research", "corroborates": True, "seen_in": "d_tf"}],
    }), encoding="utf-8")
    return load_publishers(path)


def _row(aid, src, rel, dst, origin, doc, *, sub=None, source_type="news"):
    return {"assertion_id": aid, "src": src, "relation": rel, "dst": dst, "confidence": 0.8,
            "attributes": json.dumps({"substitutability": sub} if sub is not None else {}),
            "origin": origin, "source_doc_id": doc, "source_type": source_type}


ROWS = [
    # mat:x——Suppco 一家：自己說、客戶不具名（寫的是新寫法 SPX）、TrendForce 轉述
    _row("a1", "co:supp", "supplies_to", "mat:x", "Suppco Holdings Inc.", "d_self", source_type="transcript"),
    _row("a2", "co:supp", "supplies_to", "mat:x", "Customer Corp", "d_cust"),
    _row("a3", "co:supp", "supplies_to", "mat:x", "TrendForce", "d_tf", source_type="industry_report"),
    _row("x1", "tech:y", "depends_on", "mat:x", "Customer Corp", "d_cust", sub=5),
    # mat:z——Otherco 一家：TrendForce 具名、不是轉述 → 外部印證（對照組，兩次都一樣）
    _row("b1", "co:other", "supplies_to", "mat:z", "Otherco Ltd.", "d_other", source_type="transcript"),
    _row("b2", "co:other", "supplies_to", "mat:z", "TrendForce", "d_tf2", source_type="industry_report"),
    _row("z1", "tech:w", "depends_on", "mat:z", "Customer Corp", "d_cust4", sub=5),
    # mat:q——Dupe Labs（兩個代號）：客戶寫「Dupe Labs」
    _row("c1", "co:dup_a", "supplies_to", "mat:q", "Customer Corp", "d_cust2"),
    _row("q1", "tech:v", "depends_on", "mat:q", "Customer Corp", "d_cust2", sub=5),
    # prod:s——插槽：客戶不具名（新寫法）、TrendForce 轉述；Maker 是製造者
    _row("s1", "co:supp", "supplies_to", "prod:s", "Customer Corp", "d_cust3"),
    _row("s2", "co:supp", "supplies_to", "prod:s", "TrendForce", "d_tf3", source_type="industry_report"),
    _row("s3", "co:maker", "develops", "prod:s", "Maker Co", "d_maker"),
]
QUOTES = {
    "a1": ["Suppco ships X substrates to every module maker"],
    "a2": ["We expanded our X order with SPX this quarter"],
    "a3": ["Suppco said its X shipments doubled"],
    "x1": ["Y requires X and has no alternative"],
    "b1": ["We make Z in two fabs"],
    "b2": ["Otherco holds 60% of Z supply"],
    "z1": ["W cannot ship without Z, there is no alternative"],
    "c1": ["Dupe Labs ships Q to our fabs"],
    "q1": ["V depends on Q, no alternative qualified"],
    "s1": ["We source the S laser from SPX"],
    "s2": ["Suppco announced S laser shipments"],
    "s3": ["Maker develops the S module"],
}
BASELINE = {"frozen_nodes": frozenset(LAYERS), "frozen_assertions": frozenset(QUOTES), "sub_assertions": frozenset()}


def _edge_quotes():
    """`build_socket_view`／`verify_citations` 吃的形狀：邊 → 逐段（同一次查詢的逐字＋origin＋文件）。"""
    out: dict = {}
    for row in ROWS:
        for quote in QUOTES[row["assertion_id"]]:
            out.setdefault((row["src"], row["relation"], row["dst"]), []).append(
                {"quote": quote, "doc": row["source_doc_id"], "origin": row["origin"], "origin_linkage": None})
    return out


def _chain(tmp_path: Path, monkeypatch, publishers, *, after: bool, evidence_baseline=None) -> dict:
    """整條證據鏈用正式函式跑一次，回每一段的產出。"""
    registry = _Registry(after=after)
    monkeypatch.setattr(qs, "get_registry", lambda: registry)
    monkeypatch.setattr(origin_resolution, "get_publishers", lambda: publishers)
    edges = qs._classify_edges(ROWS, QUOTES)
    by_key = {(e.src, e.relation, e.dst): e for e in edges}
    table = structure_table(ROWS, registry, quotes_by_assertion=QUOTES)
    socket = qs.build_socket_view("prod:s", edges, _edge_quotes(), registry, publishers=publishers)
    stats = compute_layer_stats(edges=edges, rows=ROWS, quotes_by_assertion=QUOTES, layer_nodes=LAYERS,
                                baseline=BASELINE, registry=registry, language=LANG, publishers=publishers,
                                evidence_baseline=evidence_baseline)
    nodes = sorted({n for r in ROWS for n in (r["src"], r["dst"])})
    result = walk(edges=edges, graph_nodes=nodes, reading_rows=[], leads={}, registry=registry, coverage_rows=[],
                  duplicate_buckets={}, duplicate_node_total=0, anchors=())
    result["layer_stats"] = stats
    state = tmp_path / ("state_after" if after else "state_before")
    StateArtifactStore(state).write(build_graph_walk_artifact(result, generated_at=NOW))
    lines = hb.build_queue(state_dir=state, now=NOW).lines
    return {"registry": registry, "edges": by_key, "table": table, "socket": socket, "stats": stats,
            "walk": {q["key"]: q for q in result["questions"]},
            "layer_line": next(line for line in lines if line.startswith("層：")),
            "walk_line": next(line for line in lines if line.startswith("走圖："))}


def _row_evidence(table, src, dst):
    return next(r["evidence"] for r in table["rows"] if (r["company_id"], r["bottleneck"]) == (src, dst))


# ---------------------------------------------------------------------------
# 1｜證據鏈
# ---------------------------------------------------------------------------

def test_the_evidence_labels_and_counters_travel_from_quotes_to_the_heartbeat(tmp_path, monkeypatch, publishers) -> None:
    """6.0 的名冊：客戶寫「SPX」比不到 Suppco（未具名 2：mat:x、prod:s）、TrendForce 那兩段是轉述（2）、Dupe Labs 兩個代號
    共用每個寫法（名冊無名 1）；只有 Otherco 那條被 TrendForce 具名而且不是轉述 → 外部印證。走圖第 2 型：mat:x、mat:q 命中、
    mat:z 不命中 → 2／3。補完寫法、合併身分之後：三條都升外部印證、三格都歸零、第 2 型 0／3、對前一次升 3。"""
    before = _chain(tmp_path, monkeypatch, publishers, after=False)

    # 結構表的列（下游第一站）
    assert _row_evidence(before["table"], "co:other", "mat:z") == "externally_corroborated"
    for src, dst in (("co:supp", "mat:x"), ("co:supp", "prod:s"), ("co:dup_a", "mat:q")):
        assert _row_evidence(before["table"], src, dst) != "externally_corroborated", (src, dst)
    # 層視角與結構表是同一個 owner 給的等級（不各算一份）
    for key, edge in before["edges"].items():
        if key[0].startswith("co:") and key[1] == "supplies_to" and key[2] in LAYERS:
            assert _row_evidence(before["table"], key[0], key[2]) == edge.evidence

    # 插槽視角：客戶端原文照印、旁註沒具名；發布者那段過了 publisher_lifts 才列、旁註轉述
    quotes = {(q["origin"], q["quote"]): q for q in before["socket"].customer_quotes}
    assert quotes[("Customer Corp", "We source the S laser from SPX")]["withheld"] == "unnamed"
    assert quotes[("TrendForce", "Suppco announced S laser shipments")]["withheld"] == "relay"

    # 層計數器：三種理由分開、違反恆 0
    withheld = before["stats"]["corroboration_withheld"]
    assert {k: len(v) for k, v in withheld.items()} == {"unnamed": 2, "no_name_forms": 1, "relay": 2}
    assert before["stats"]["ec_without_naming_quote"] == []

    # 走圖第 2 型
    sole = before["walk"]["sole_supplier_self_reported"]
    assert sorted(h["subject"] for h in sole["hits"]) == ["mat:q", "mat:x"] and sole["scope_n"] == 3

    # 心跳段 3 的兩行（讀 artifact、不查圖）
    assert "外部印證違反 0｜沒升外部印證：未具名 2／名冊無名 1／轉述 2" in before["layer_line"], before["layer_line"]
    assert "獨家且自報 2／3" in before["walk_line"], before["walk_line"]

    # 補完寫法（SPX）、合併身分（Dupe Labs 一個代號）之後，同一份圖重跑；基準＝前一次的等級
    baseline = {" ".join(k): str(e.evidence) for k, e in before["edges"].items()}
    after = _chain(tmp_path, monkeypatch, publishers, after=True, evidence_baseline=baseline)
    for src, dst in (("co:supp", "mat:x"), ("co:supp", "prod:s"), ("co:dup_a", "mat:q"), ("co:other", "mat:z")):
        assert _row_evidence(after["table"], src, dst) == "externally_corroborated", (src, dst)
    quotes = {(q["origin"], q["quote"]): q for q in after["socket"].customer_quotes}
    assert quotes[("Customer Corp", "We source the S laser from SPX")]["withheld"] is None
    assert {k: len(v) for k, v in after["stats"]["corroboration_withheld"].items()} == {
        "unnamed": 0, "no_name_forms": 0, "relay": 0}
    assert after["stats"]["ec_without_naming_quote"] == []
    up = sorted(c["edge"] for c in after["stats"]["evidence_vs_baseline"]["up"])
    assert up == ["co:dup_a supplies_to mat:q", "co:supp supplies_to mat:x", "co:supp supplies_to prod:s"]
    assert after["walk"]["sole_supplier_self_reported"]["hits"] == []
    assert "未具名 0／名冊無名 0／轉述 0" in after["layer_line"], after["layer_line"]
    assert "證據等級較 6.0：升 3／降 0／同級互換 0" in after["layer_line"], after["layer_line"]
    assert "獨家且自報 0／3" in after["walk_line"], after["walk_line"]
    # 標籤的人話跟著走（同一張字表）
    assert EVIDENCE_LABEL["externally_corroborated"] == "外部印證"


def _layer_record(registry_after: bool, structure: dict):
    """mat:x 的 v3 層讀圖：供給側那條標 independent、引的是客戶那段（寫的是 SPX）。"""
    from alpha.structure_reading.contracts import structure_reading_record

    citations = [
        {"angle": "demand_side", "edge": ["tech:y", "depends_on", "mat:x"], "quote": "Y requires X and has no alternative",
         "source_id": "d_cust", "independent": False},
        {"angle": "supply_side", "edge": ["co:supp", "supplies_to", "mat:x"],
         "quote": "We expanded our X order with SPX this quarter", "source_id": "d_cust", "independent": True},
    ]
    disproof = [{"condition": "任一家 Y 廠在正式文件宣布改用不需要 X 的設計並量產", "entities": ["co:supp"],
                 "check_frequency": "每季", "action_48h": "重讀這一層", "source": "self"}]
    return structure_reading_record(
        node="mat:x", structure=structure, unit="layer", kind="moat",
        reading=f"全鏈測試（名冊{'補完之後' if registry_after else ' 6.0 版'}）：供給側引用客戶那段。",
        expires=date(2026, 12, 31), created_at=NOW, author="test", citations=citations, disproof=disproof)


def test_an_independent_citation_whose_quote_does_not_name_the_supplier_is_refused_until_the_name_is_known(
        tmp_path, monkeypatch, publishers) -> None:
    """讀圖引用核對與邊的等級問同一個 owner：6.0 的名冊比不到「SPX」→ 拒收（未具名）；名冊補了寫法 → 收下。"""
    from alpha.providers.structure_readings import verify_citations

    for after in (False, True):
        chain = _chain(tmp_path, monkeypatch, publishers, after=after)
        structure = qs.build_structure("mat:x", list(chain["edges"].values())).as_dict()
        problems = verify_citations(_layer_record(after, structure), _edge_quotes(), registry=chain["registry"],
                                    publishers=publishers)
        independence = [p for p in problems if "第 2 條引用" in p]
        if after:
            assert independence == [], problems
        else:
            assert independence and any("具名" in p for p in independence), problems


# ---------------------------------------------------------------------------
# 2｜稀釋燈鏈
# ---------------------------------------------------------------------------

TODAY = date(2026, 9, 29)


def _issuance(*filings):
    """夾具 Engine C：兩季營收當窗尾、窗內兩季有新股發行金額（50＋600）；募資文件清單走正式寫入路徑。"""
    from engine_c.checklist import _equity_issuance
    from engine_c.offerings import store_offerings
    from tests.test_engine_c_equity_issuance import FETCHED, _domestic_rows, _reader_conn, _row as fact_row

    conn = _reader_conn(_domestic_rows(
        fact_row("equity_issued_value_quarter", end="2026-06-30", start="2026-04-01", filed="2026-08-01",
                 accn="Q2-26", value=600.0),
        fact_row("equity_issued_value_quarter", end="2025-09-30", start="2025-07-01", filed="2025-11-01",
                 accn="Q3-25", value=50.0)))
    store_offerings(conn, [*filings, {"form_type": "10-K", "filed_date": "2020-01-01", "accession_dashed": "OLD"}],
                    ticker="XYZ", cik="0000000009", fetched_at=FETCHED)
    return _equity_issuance(conn, "XYZ", today=TODAY)


def _stock_page(issuance):
    """四盞燈 → 三題（`evaluate`，正式路徑同一支）→ read model → analyst view → materialize（個股頁 artifact）。
    回首屏那一格與稽核區那一列——APP 的稽核區印的是三題面板（`threeQuestionsCard`），算出顏色的數字在那一列的
    `dependencies.detail`；wipeout 面板只畫顏色與一句話（D2）。"""
    from alpha import three_questions as tq
    from alpha.wipeout import wipeout_flags
    from briefing.analyst_view import build_analyst_view
    from tests.test_alpha_investment_view import _view
    from webapp.materialize import materialize_view

    flags = wipeout_flags(runway={"status": "manual_required"}, shares_series=[(date(2025, 9, 1), 100.0), (TODAY, 100.0)],
                          going_concern=None, today=TODAY, issuance=issuance)
    view = _view(today=TODAY, wipeout=flags, three_questions=tq.evaluate({}, today=TODAY, wipeout=flags))
    payload = materialize_view(build_analyst_view(view).to_dict(), generated_at=NOW)
    lane = next(x for x in payload["overview"]["wipeout"]["lanes"] if x["lane"] == "dilution")
    audit = next(line["datum"] for line in payload["view"]["three_questions"]["lines"]
                 if (line["datum"].get("dependencies") or {}).get("row_key") == "wipeout_dilution")
    return lane, audit


def test_the_dilution_lamp_needs_an_offering_document_all_the_way_to_the_stock_page() -> None:
    """窗內有發行金額（650）：①窗內一份 424B5 → 個股頁那一格黃、理由不帶數字（D2）、稽核層指得出那份文件；
    ②窗內只有 S-8（員工計畫登記）→ 不上色，`insufficient_evidence`，理由說員工計畫登記不算募資、S-8 照印在稽核層。"""
    amber_lane, amber_audit = _stock_page(_issuance(
        {"form_type": "424B5", "filed_date": "2026-04-20", "accession_dashed": "0000000009-26-000420"}))
    assert amber_lane["colour"] == "amber", amber_lane
    assert not re.search(r"\d", amber_lane["reason"] or ""), amber_lane["reason"]          # D2：紅黃綠不給數字
    assert amber_audit["value"] == "amber" and amber_audit["dependencies"]["question"] == "will_it_die"
    offerings = amber_audit["dependencies"]["detail"]["offerings"]
    assert [d["accession"] for d in offerings["documents"]] == ["0000000009-26-000420"]
    assert offerings["documents"][0]["form"] == "424B5"
    assert offerings["window"] == {"start": "2025-07-01", "end": "2026-08-01"}     # 發行那幾季的期初到窗尾那份報告的申報日

    grey_lane, grey_audit = _stock_page(_issuance(
        {"form_type": "S-8", "filed_date": "2026-03-02", "accession_dashed": "0000000009-26-000302"}))
    assert grey_lane["colour"] is None and grey_lane["absence_kind"] == "insufficient_evidence", grey_lane
    assert "員工計畫登記" in grey_lane["reason"] and not re.search(r"\d", grey_lane["reason"]), grey_lane["reason"]
    # 窗內有哪些申報在稽核區：沒點亮的那一列值是 None（缺席≠0）、缺席分型照抄，S-8 照印在 detail、不算募資文件
    assert grey_audit["value"] is None and grey_audit["absence_kind"] == "insufficient_evidence", grey_audit
    grey_offerings = grey_audit["dependencies"]["detail"]["offerings"]
    assert grey_offerings["documents"] == []
    assert [(d["form"], d["accession"]) for d in grey_offerings["context"]] == [("S-8", "0000000009-26-000302")]
    assert "S-8" in grey_audit["method"]                                                    # 規則寫明 S-8 不算
