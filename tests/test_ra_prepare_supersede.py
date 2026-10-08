"""prepare 冪等、指名取代舊版、focus 只判一次（2026-10-08，Phase 7 failure log #3；plan 2026-10-08-001 D2）。

事發四次：[679]／[680]（更正 L8 備註後重 prepare，兩版並存）、[687]／[688]（第一版沒宣告 focus，prepare 放行、sync 才擋）、
[697]／[698]（為了看 packet 重跑 prepare，同一份內容鑄兩號）、[704]／[705]（三文件包換成一文件包，舊的還在 staging）——
多出來的號都只能請使用者 drop；更糟的是 go 到舊號會套用舊版內容。
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
from intake.focus import resolve_focus

ROOT = Path(__file__).resolve().parent.parent
BASIS = "Official public filing retained for private research"


def _payload(doc_id: str = "sup_doc", *, marker: str = "v1") -> dict:
    extraction = {"schema_version": "0.1",
                  "source_doc": {"doc_id": doc_id, "title": f"Doc {marker}", "source_type": "filing", "evidence_tier": 1,
                                 "origin_entity": "Test Issuer", "storage_permission": "repo_full",
                                 "permission_basis": BASIS, "url": "https://example.com/sup"},
                  "sources": [], "nodes": [], "edges": [], "claims": []}
    return {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "sup-action",
            "report": {"title": f"t {marker}", "why_now": "w", "findings": "f", "search_summary": "s",
                       "l8_notes": f"l8 {marker}", "counterevidence_and_gaps": "c"},
            "focus_company_id": "co:axt",
            "documents": [{"doc_id": doc_id, "extraction": extraction, "raw_payload": {}, "storage_permission": "repo_full",
                           "permission_basis": BASIS, "validation_warnings": []}]}


def _entry():
    spec = importlib.util.spec_from_file_location("apply_ra_admission", ROOT / "scripts" / "apply_ra_admission.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apply_ra_admission"] = module
    spec.loader.exec_module(module)
    return module


# --- 冪等 -----------------------------------------------------------------------

def test_the_same_content_prepared_twice_returns_the_first_record(tmp_path: Path) -> None:
    first = research_actions.create_action(_payload(), root=tmp_path)
    again = research_actions.create_action(_payload(), root=tmp_path)
    assert again["action_id"] == first["action_id"] and again.get("deduplicated") is True
    assert len(list(research_actions.iter_actions(root=tmp_path))) == 1
    # 內容不同（L8 備註改了）＝新的一筆
    other = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    assert other["action_id"] != first["action_id"] and not other.get("deduplicated")


def test_a_superseded_or_expired_record_is_not_reused(tmp_path: Path) -> None:
    old = research_actions.create_action(_payload(), root=tmp_path)
    newer = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    research_actions.mark_superseded(old["action_id"], by=newer["action_id"], root=tmp_path)
    again = research_actions.create_action(_payload(), root=tmp_path)
    assert again["action_id"] not in (old["action_id"], newer["action_id"])


# --- 取代 -----------------------------------------------------------------------

def test_supersede_marks_only_untouched_ready_records(tmp_path: Path) -> None:
    old = research_actions.create_action(_payload(), root=tmp_path)
    newer = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    marked = research_actions.mark_superseded(old["action_id"], by=newer["action_id"], root=tmp_path)
    assert marked["superseded_by"]["action_id"] == newer["action_id"]
    assert marked["state"] == "ready" and marked["action_digest"] == old["action_digest"]   # 不改 state、不進 digest
    # 冪等；換一個取代者要拒收；不能自己取代自己
    research_actions.mark_superseded(old["action_id"], by=newer["action_id"], root=tmp_path)
    third = research_actions.create_action(_payload(marker="v3"), root=tmp_path)
    with pytest.raises(ValueError, match="已被"):
        research_actions.mark_superseded(old["action_id"], by=third["action_id"], root=tmp_path)
    with pytest.raises(ValueError, match="自己"):
        research_actions.mark_superseded(third["action_id"], by=third["action_id"], root=tmp_path)
    # 已蓋核准戳記的（apply 在路上）不能被取代
    record = research_actions.read_action(third["action_id"], root=tmp_path)
    record["execution"]["approval"] = {"pq2_n": 7, "digest": record["action_digest"], "at": record["created_at"]}
    research_actions.save_action(record, root=tmp_path)
    with pytest.raises(ValueError, match="核准戳記"):
        research_actions.mark_superseded(third["action_id"], by=newer["action_id"], root=tmp_path)


def test_apply_refuses_a_superseded_record_even_when_its_number_gets_go(tmp_path: Path, monkeypatch) -> None:
    old = research_actions.create_action(_payload(), root=tmp_path)
    newer = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    pool = todo.empty_pool()
    item = todo.upsert(pool, item_type="ra_admission", ref_id=old["action_id"], title="舊版")
    pool_path = tmp_path / "todo_pool.json"
    todo.save(pool, pool_path)
    research_actions.mark_superseded(old["action_id"], by=newer["action_id"], root=tmp_path)
    module = _entry()
    monkeypatch.setattr(module, "check_property_tokens", lambda **_k: None)
    with pytest.raises(module.ApplyRefused, match="已被 .* 取代"):
        module.check_and_stamp(item["n"], old["action_digest"], pool_path=pool_path, root=tmp_path)
    assert "approval" not in research_actions.read_action(old["action_id"], root=tmp_path)["execution"]

    def boom(*_a, **_k):
        raise AssertionError("superseded record must not reach the loader")

    monkeypatch.setattr(application, "_load_extraction_impl", boom)
    result = application._apply_research_action_impl(old["action_id"], old["action_digest"], root=tmp_path)
    assert result["status"] == "rejected" and "取代" in result["error"]


def test_sync_marks_the_superseded_number_and_recommends_drop(tmp_path: Path, monkeypatch) -> None:
    old = research_actions.create_action(_payload(), root=tmp_path)
    newer = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    research_actions.mark_superseded(old["action_id"], by=newer["action_id"], root=tmp_path)
    monkeypatch.setattr(research_actions, "iter_actions",
                        lambda *, root=tmp_path, _orig=research_actions.iter_actions: _orig(root=tmp_path))
    rows = {row["ref_id"]: row for row in todo._collect_research_action_rows()}
    assert rows[old["action_id"]]["superseded_by"] == newer["action_id"]
    assert "已被" in rows[old["action_id"]]["hint"] and "drop" in rows[old["action_id"]]["hint"]
    assert "superseded_by" not in rows[newer["action_id"]]

    pool = todo.empty_pool()
    todo.sync(pool, list(rows.values()), reconciled={})
    by_ref = {item["ref_id"]: item for item in pool["items"]}
    assert by_ref[old["action_id"]]["recommendation"]["verb"] == "drop"
    assert "recommendation" not in by_ref[newer["action_id"]]


# --- focus 只判一次 ----------------------------------------------------------------

def test_resolve_focus_is_the_one_rule_for_prepare_and_sync() -> None:
    assert resolve_focus("co:axt") == ("co:axt", None)
    assert resolve_focus(None, ["co:axt"]) == ("co:axt", None)
    assert resolve_focus("co:axt", ["co:axt"]) == ("co:axt", None)
    focus, blocker = resolve_focus("co:axt", ["co:iqe"])
    assert focus is None and "綁定 lead 卻是" in blocker
    assert "多個" in resolve_focus(None, ["co:axt", "co:iqe"])[1]
    assert "尚未聲明" in resolve_focus(None)[1]


def test_prepare_rejects_a_draft_without_focus_before_sync_ever_sees_it(tmp_path: Path) -> None:
    """[687] 的形狀：第一版沒宣告 focus——之前 prepare 放行、sync 鑄出帶 BLOCKER 的編號。"""
    request = json.loads(json.dumps(_payload()))
    request.pop("focus_company_id")
    request["documents"] = [{"extraction_json": json.dumps(request["documents"][0]["extraction"]),
                             "storage_permission": "repo_full", "permission_basis": BASIS}]
    result = application._prepare_research_action_impl(json.dumps(request), root=tmp_path)
    assert result["status"] == "rejected" and "focus_company_id 必填" in result["error"]
    assert list(research_actions.iter_actions(root=tmp_path)) == []


def test_the_prepare_entry_writes_a_receipt_for_each_named_old_version(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("prepare_research_action", ROOT / "scripts" / "prepare_research_action.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old = research_actions.create_action(_payload(), root=tmp_path)
    newer = research_actions.create_action(_payload(marker="v2"), root=tmp_path)
    receipt = module.supersede([old["action_id"], "ra_" + "0" * 32], new_id=newer["action_id"], root=tmp_path)
    assert receipt[0] == {"action_id": old["action_id"], "status": "superseded", "by": newer["action_id"]}
    assert receipt[1]["status"] == "not_superseded" and receipt[1]["error"]       # 標不上照實寫，不擋新版
