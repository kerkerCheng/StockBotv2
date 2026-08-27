"""MCP leads surface：唯讀佇列、record 寫入、窄 pathset commit/push（plan U2）。"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from engine_b import leads
from mcp_server import leads_tools, leads_git, graph_mcp


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


def test_record_triage_calls_committer_and_advances(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    calls = []

    def fake_commit(root, *, message):
        calls.append(message)
        return {"status": "committed", "committed": True, "pushed": True}

    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="triage", go=True, tier=2, reason="有角度",
        content_type="structural_fact", decision_impact="ranking",
        leads_path=path, committer=fake_commit,
    )
    assert result["status"] == "recorded"
    assert result["new_status"] == "triaged_go"
    assert result["sync"]["pushed"] is True
    assert len(calls) == 1 and "triage" in calls[0]
    persisted = leads.load(path)["leads"][lead_id]
    assert persisted["status"] == "triaged_go"
    assert persisted["triage"]["classification"]["classified_by"] == "triage_semantic_v1"


def test_record_triage_rejects_pass_without_classification(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="triage", go=True, tier=2, reason="有角度",
        leads_path=path, committer=lambda *a, **k: {"status": "unexpected"},
    )
    assert result["status"] == "invalid_request"
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"


def test_record_illegal_transition_is_safe(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    result = leads_tools.record_lead_decision_core(
        lead_id=lead_id, op="advance", to_status="applied",  # pending→applied 非法
        leads_path=path, committer=lambda *a, **k: {"status": "no_change"},
    )
    assert result["status"] == "illegal_transition"
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"


# --- 窄 pathset commit/push（真實 temp git repo，安全宣稱的核心）----------

def _git(work: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", str(work)], check=True, capture_output=True)
    _git(work, "config", "user.email", "t@t")
    _git(work, "config", "user.name", "t")
    _git(work, "remote", "add", "origin", str(remote))
    (work / "library" / "leads").mkdir(parents=True)
    (work / "library" / "leads" / "pending_leads.json").write_text("{}\n", encoding="utf-8")
    (work / "other.txt").write_text("x\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "init")
    _git(work, "push", "origin", "HEAD")
    return work


def test_commit_push_only_touches_leads_json(tmp_path) -> None:
    work = _init_repo(tmp_path)
    # 同時改 leads.json 與另一個檔——commit 必須只含 leads.json
    (work / "library" / "leads" / "pending_leads.json").write_text('{"x":1}\n', encoding="utf-8")
    (work / "other.txt").write_text("MODIFIED\n", encoding="utf-8")

    result = leads_git.commit_and_push_leads(work, message="chore(leads): test")
    assert result["status"] == "committed" and result["pushed"] is True

    # HEAD commit 只碰 leads.json
    show = subprocess.run(
        ["git", "-C", str(work), "show", "--name-only", "--pretty=format:", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    touched = {l.strip() for l in show.stdout.splitlines() if l.strip()}
    assert touched == {"library/leads/pending_leads.json"}

    # other.txt 仍是未提交的 modified（沒被掃進去）
    status = subprocess.run(
        ["git", "-C", str(work), "status", "--porcelain", "--", "other.txt"],
        capture_output=True, text=True, check=True,
    )
    assert "other.txt" in status.stdout


def test_commit_no_change_is_idempotent(tmp_path) -> None:
    work = _init_repo(tmp_path)
    result = leads_git.commit_and_push_leads(work, message="noop")
    assert result["status"] == "no_change" and result["committed"] is False


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
