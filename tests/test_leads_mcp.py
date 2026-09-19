"""MCP leads surface：唯讀佇列與本機 authority record 寫入（plan U2）。"""
from __future__ import annotations

from pathlib import Path

from engine_b import leads
from mcp_server import leads_tools, graph_mcp


# --- core 讀寫（可注入，無 git）------------------------------------------

def _seed(path: Path) -> str:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="edgar:COHR", url="https://x.io/1",
                                title="COHR 8-K")
    leads.save(store, path)
    return lead_id


def test_get_pending_leads_core_ranks_and_counts(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    a, _ = leads.register(store, source="edgar:AAOI", url="https://x.io/a")
    b, _ = leads.register(store, source="edgar:COHR", url="https://x.io/b")
    leads.triage(store, a, go=True, tier=4, reason="弱", classification={
        "content_type": "financial_fact", "decision_impact": "confidence_only",
    })
    leads.triage(store, b, go=True, tier=1, reason="強",
                 priority_flags={"contradiction": True}, classification={
                     "content_type": "structural_fact", "decision_impact": "exit_condition",
                 })
    leads.save(store, path)

    result = leads_tools.get_pending_leads_core(leads_path=path, tracked_tickers="COHR")
    assert result["counts"]["triaged_go"] == 2
    assert result["unresolved_harvest_failures"] == []
    assert result["leads"][0]["source"] == "edgar:COHR"  # 最高 priority 在前
    # `priority` 自 2026-08-21 起是說明「為什麼排在這裡」的標籤，不是可比較的分數——
    # 合併後的單一分數正是本次移除的東西（加權總分有補償性）。順序由回傳次序表達。
    assert result["classification_health"]["status"] == "ok"
    assert result["leads"][0]["priority"] == "出場條件·結構事實"
    assert result["leads"][1]["priority"] == "只是信心·財務事實"


def test_record_triage_persists_locally_without_git_sync(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="triage", go=True, tier=2, reason="有角度",
        content_type="structural_fact", decision_impact="ranking",
        leads_path=path,
    )
    assert result["status"] == "recorded"
    assert result["new_status"] == "triaged_go"
    assert result["sync"] == {
        "status": "local_authority", "committed": False, "pushed": False,
    }
    persisted = leads.load(path)["leads"][lead_id]
    assert persisted["status"] == "triaged_go"
    assert persisted["triage"]["classification"]["classified_by"] == "triage_semantic_v1"


def test_record_triage_rejects_pass_without_classification(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="triage", go=True, tier=2, reason="有角度",
        leads_path=path,
    )
    assert result["status"] == "invalid_request"
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"


def test_record_illegal_transition_is_safe(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="advance", to_status="applied",  # pending→applied 非法
        leads_path=path,
    )
    assert result["status"] == "illegal_transition"
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"


# --- graph_mcp wrapper 序列化 --------------------------------------------

def test_graph_mcp_wrappers_serialize(monkeypatch) -> None:
    monkeypatch.setattr(graph_mcp, "get_pending_leads_core",
                        lambda **k: {"counts": {"pending": 3}, "leads": []})
    monkeypatch.setattr(graph_mcp, "record_lead_decision_core",
                        lambda **k: {"status": "recorded", "new_status": "parked"})
    import json
    got = json.loads(graph_mcp.get_pending_leads())
    assert got["counts"]["pending"] == 3
    rec = json.loads(graph_mcp.record_lead_decision("lead_x", "advance", to_status="parked"))
    assert rec["status"] == "recorded"
