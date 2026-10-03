"""Phase 4 Step 4.9：新管線 full chain（夾具版）。

一份 `origin_role=industry_report` 的層文件 request（`layer_enumerations` 2 家）→ prepare（層列舉核對）→ 池裡 `ra_admission`
→ 固定入口 `scripts/apply_ra_admission.py --pq2 --digest`（fake loader 把抽取的斷言寫進夾具圖）→ approval 戳記
→ `complete-ra`（比對戳記）→ 層計數 ② +1、① −1。另三條：引文不具名的 request 被拒、媒體 origin 文件不升級、
有現行層讀圖的節點走圖第 2 型不問。

⚠ `tests/test_full_chain_acceptance.py`（真 runtime 那份）不動——這支是新管線自己的夾具版。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from engine_b import todo
from intake import actions as research_actions
from intake import application
from intake import provenance as intake
from query.bottleneck import classify_evidence, collapse_assertions
from query.layer_stats import compute_layer_stats
from query.origin_resolution import PUBLISHER_KINDS, load_publishers
from query.sub_language import SubLanguage

ROOT = Path(__file__).resolve().parent.parent
BASIS = "Official public source retained for private research"
LANG = SubLanguage(version=1, variant="test", terms=("sole supplier", "qualified"))


class _Company:
    def __init__(self, cid, display_name, *aliases):
        self.company_id, self.display_name, self.name_aliases, self.aliases = cid, display_name, aliases, ()


class _Registry:
    def __init__(self):
        self._c = {c.company_id: c for c in (_Company("co:a", "Alpha Corp", "Alpha"),
                                              _Company("co:b", "Beta Inc.", "Beta"))}

    @property
    def companies(self):
        return tuple(self._c.values())

    def company(self, cid):
        return self._c.get(cid)

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return cid in self._c


def _entry():
    spec = importlib.util.spec_from_file_location("apply_ra_admission", ROOT / "scripts" / "apply_ra_admission.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apply_ra_admission"] = module
    spec.loader.exec_module(module)
    return module


def _layer_doc(doc_id: str, origin: str, quotes: dict[str, str], *, source_type: str = "industry_report") -> dict:
    nodes = [{"id": "mat:x", "type": "Material", "name": "X substrate", "abstraction_level": "materials_substrate",
              "confidence": 0.9, "source_ids": [f"{doc_id}_s1"]}]
    edges, sources = [], []
    for index, (supplier, quote) in enumerate(quotes.items(), start=1):
        sid = f"{doc_id}_s{index}"
        nodes.append({"id": supplier, "type": "Company", "name": supplier, "abstraction_level": "materials_substrate",
                      "confidence": 0.9, "source_ids": [sid]})
        edges.append({"id": f"e{index}", "src_id": supplier, "relation": "supplies_to", "dst_id": "mat:x",
                      "confidence": 0.8, "source_ids": [sid]})
        sources.append({"id": sid, "locator": f"p{index}", "quote": quote})
    return {"schema_version": "0.1",
            "source_doc": {"doc_id": doc_id, "title": "X substrate market", "source_type": source_type,
                           "evidence_tier": 3, "origin_entity": origin, "storage_permission": "repo_full",
                           "permission_basis": BASIS, "url": f"https://example.com/{doc_id}"},
            "sources": sources, "nodes": nodes, "edges": edges, "claims": []}


def _request(extraction: dict) -> dict:
    return {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "x-layer-document",
            "report": {"title": "X 基板層文件", "why_now": "w", "findings": "f", "search_summary": "s",
                       "l8_notes": "l8", "counterevidence_and_gaps": "c"},
            "layer_enumerations": [{"node": "mat:x", "suppliers": ["co:a", "co:b"], "relation": "supplies_to",
                                    "origin_role": "industry_report"}],
            "documents": [{"doc_id": extraction["source_doc"]["doc_id"], "extraction": extraction, "raw_payload": {},
                           "storage_permission": "repo_full", "permission_basis": BASIS, "validation_warnings": []}]}


#: 夾具圖：mat:x 只有 Alpha 一家、只有它自己說（① 命中）；凍結集合就是這一層。
BASE_ROWS = [{"assertion_id": "a1", "src": "co:a", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.8,
              "attributes": "{}", "origin": "Alpha Corp", "source_doc_id": "d_alpha", "source_type": "filing"}]
BASE_QUOTES = {"a1": ["Alpha ships X substrates"]}
BASELINE = {"frozen_nodes": frozenset({"mat:x"}), "frozen_assertions": frozenset({"a1"}),
            "sub_assertions": frozenset()}


@pytest.fixture()
def publishers(tmp_path: Path):
    path = tmp_path / "publishers.json"
    path.write_text(json.dumps({
        "schema_version": 1, "kinds": {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
        "publishers": [{"origin": "TrendForce", "kind": "industry_research", "corroborates": True, "seen_in": "d_tf"},
                       {"origin": "Reuters", "kind": "media", "corroborates": False, "seen_in": "d_rt"}],
    }), encoding="utf-8")
    return load_publishers(path)


def _classified(rows: list[dict], quotes: dict, publishers) -> list:
    reg = _Registry()
    edges = list(collapse_assertions(rows).values())
    for edge in edges:
        edge.evidence = classify_evidence(edge.src, edge.origins, reg, filing_origins=edge.filing_origins,
                                          quotes_by_assertion=quotes, origin_assertions=edge.origin_assertions,
                                          publishers=publishers)
    return edges


def _counters(rows: list[dict], quotes: dict, publishers) -> tuple[list[str], list[str]]:
    stats = compute_layer_stats(edges=_classified(rows, quotes, publishers), rows=rows, quotes_by_assertion=quotes,
                                layer_nodes=["mat:x"], baseline=BASELINE, registry=_Registry(), language=LANG,
                                publishers=publishers)
    return stats["supply"]["sole_self_reported_nodes"], stats["enumeration"]["named_by_non_supplier_layers"]


def _graph_loader(rows: list[dict], quotes: dict, *, action_id: str):
    """fake loader：把抽取檔的每條邊寫成夾具圖的一筆 assertion（取代 Neo4j），並照真實 loader 留收據。"""
    def load(extraction_json, storage_permission, permission_basis, *, root: Path, **raw_payload) -> dict:
        assert research_actions.read_action(action_id, root=root)["execution"].get("approval"), "apply 前就要有戳記"
        extraction = json.loads(extraction_json)
        doc = extraction["source_doc"]
        by_id = {s["id"]: s["quote"] for s in extraction["sources"]}
        for edge in extraction["edges"]:
            aid = f"{doc['doc_id']}:{edge['id']}"
            rows.append({"assertion_id": aid, "src": edge["src_id"], "relation": edge["relation"],
                         "dst": edge["dst_id"], "confidence": edge["confidence"], "attributes": "{}",
                         "origin": doc["origin_entity"], "source_doc_id": doc["doc_id"],
                         "source_type": doc["source_type"]})
            quotes[aid] = [by_id[s] for s in edge["source_ids"]]
        provenance = intake.publish_provenance(doc["doc_id"], extraction, raw_payload, root=root)
        intake.mark_graph_complete(doc["doc_id"], extraction, root=root)
        return {"status": "loaded_or_already_complete", "doc_id": doc["doc_id"],
                "resolved_paths": provenance["paths"], "open_conflict_ids": [], "stale_resolution_ids": [],
                "finalize_eligible": provenance["finalize_eligible"],
                "extraction_sha256": intake.canonical_extraction_hash(extraction),
                "counts": {"nodes": len(extraction["nodes"]), "edges": len(extraction["edges"]), "claims": 0},
                "warnings": []}

    return load


def test_a_layer_document_travels_the_whole_pipeline_and_moves_the_counters(tmp_path, monkeypatch, publishers) -> None:
    import identity.registry as registry_module

    monkeypatch.setattr(registry_module, "get_registry", lambda: _Registry())
    rows, quotes = [dict(r) for r in BASE_ROWS], dict(BASE_QUOTES)
    assert _counters(rows, quotes, publishers) == (["mat:x"], [])               # 改前：① 1 層、② 0 層

    # prepare：層列舉核對——兩家都被引文具名、發文者是登記的產業研究
    record = research_actions.create_action(_request(_layer_doc("d_tf", "TrendForce", {
        "co:a": "Alpha and Beta together supply most X substrates",
        "co:b": "Alpha and Beta together supply most X substrates"})), root=tmp_path)
    check = record["layer_enumeration_check"]
    assert check["status"] == "ok" and {r["status"] for r in check["results"][0]["suppliers"]} == {"named"}
    assert check["results"][0]["origins"][0]["origin_kind"] == "publisher"
    assert "→ 登記的發布者（industry_research）" in research_actions.render_review_packet(record)

    # 池裡 ra_admission → 固定入口 apply（戳記先於圖寫入）
    pool = todo.empty_pool()
    item = todo.upsert(pool, item_type="ra_admission", ref_id=record["action_id"], title=record["payload"]["report"]["title"])
    pool_path = tmp_path / "todo_pool.json"
    todo.save(pool, pool_path)
    monkeypatch.setattr(application, "_load_extraction_impl", _graph_loader(rows, quotes, action_id=record["action_id"]))
    entry = _entry()
    # 入口在蓋戳記前查圖上的屬性名 token（Phase 5 Step 5.1）——夾具圖不是 Neo4j，換成只記次數的假檢查（不連真圖）。
    token_checks: list[str] = []
    monkeypatch.setattr(entry, "check_property_tokens", lambda **_k: token_checks.append("checked"))
    assert entry.main(["--pool", str(pool_path), "--root", str(tmp_path), "--pq2", str(item["n"]),
                       "--digest", record["action_digest"]]) == 0
    assert token_checks == ["checked"]
    applied = research_actions.read_action(record["action_id"], root=tmp_path)
    assert applied["state"] == "applied"
    assert applied["execution"]["approval"]["pq2_n"] == item["n"]

    # complete-ra 比對入口蓋的戳記（publish 以 pushed 收據模擬；focus 由綁定的 lead 給）
    monkeypatch.setattr(todo, "_read_action_for_completion", lambda aid: {
        **research_actions.read_action(aid, root=tmp_path), "state": "pushed",
        "git": {"status": "pushed", "commit": "c" * 40}})
    monkeypatch.setattr(todo, "_lead_context_for_action",
                        lambda action_id, action_digest, leads_path: {"company_id": "co:a", "title": "X 層"})
    pool = todo.load(pool_path)
    result = todo.complete_ra_admission(pool, item["n"], action_digest=record["action_digest"], leads_path="ignored")
    assert todo.active_items(pool) == [] and result["receipt"].startswith(f"action:{record['action_id']}")

    # 計數器：mat:x 有了非供應商來源具名兩家（② +1），也不再只有一家自己說（① −1）
    assert _counters(rows, quotes, publishers) == ([], ["mat:x"])


def test_a_request_whose_quote_does_not_name_the_supplier_never_reaches_the_pool(tmp_path, monkeypatch) -> None:
    import identity.registry as registry_module

    monkeypatch.setattr(registry_module, "get_registry", lambda: _Registry())
    request = _request(_layer_doc("d_tf2", "TrendForce", {"co:a": "Alpha supplies X substrates",
                                                          "co:b": "a second vendor also supplies X"}))
    with pytest.raises(ValueError, match="引文沒有具名"):
        research_actions.create_action(request, root=tmp_path)
    assert not list((tmp_path / "library").rglob("ra_*.json")) if (tmp_path / "library").exists() else True


def test_a_media_origin_document_does_not_upgrade_the_edge(publishers) -> None:
    """媒體轉述（沒有宣告 independent）不算印證：Alpha→X 多一份 Reuters 也只到 media_relay；列舉照計（②），強弱另由證據欄說。"""
    rows = [dict(r) for r in BASE_ROWS] + [
        {"assertion_id": "m1", "src": "co:a", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.7,
         "attributes": "{}", "origin": "Reuters", "source_doc_id": "d_rt", "source_type": "news"},
        {"assertion_id": "m2", "src": "co:b", "relation": "supplies_to", "dst": "mat:x", "confidence": 0.7,
         "attributes": "{}", "origin": "Reuters", "source_doc_id": "d_rt", "source_type": "news"}]
    quotes = {**BASE_QUOTES, "m1": ["Alpha and Beta make X"], "m2": ["Alpha and Beta make X"]}
    before = next(e for e in _classified([dict(r) for r in BASE_ROWS], BASE_QUOTES, publishers)
                  if e.src == "co:a").evidence
    by_src = {e.src: e.evidence for e in _classified(rows, quotes, publishers)}
    assert by_src["co:a"] == before != "externally_corroborated"         # 多一份媒體轉述，等級不動
    assert by_src["co:b"] == "media_relay"                               # 只有媒體來源的那條：媒體轉述，不是印證
    assert _counters(rows, quotes, publishers)[1] == ["mat:x"]


def test_walk_type_two_does_not_ask_a_node_that_has_a_current_layer_reading() -> None:
    from query.graph_walk import layer_questions

    rows = [dict(r) for r in BASE_ROWS]
    edges = list(collapse_assertions(rows).values())
    for edge in edges:
        edge.evidence = "self_reported"
    demand = collapse_assertions([{**BASE_ROWS[0], "assertion_id": "d1", "src": "tech:mod", "relation": "depends_on",
                                   "dst": "mat:x", "attributes": json.dumps({"substitutability": 4})}])
    for edge in demand.values():
        edge.evidence = "externally_corroborated"
    all_edges = edges + list(demand.values())
    asked = layer_questions(all_edges, read_nodes=set(), current_layer_nodes=set(), stale_layer_readings={},
                            open_leads={})["sole_supplier_self_reported"]["hits"]
    assert [h["subject"] for h in asked] == ["mat:x"]
    quiet = layer_questions(all_edges, read_nodes={"mat:x"}, current_layer_nodes={"mat:x"}, stale_layer_readings={},
                            open_leads={})["sole_supplier_self_reported"]["hits"]
    assert quiet == []
