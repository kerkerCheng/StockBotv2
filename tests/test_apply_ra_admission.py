"""Research Action apply 固定入口 `scripts/apply_ra_admission.py`（Phase 4 Step 4.2d）。

釘住：四道 fail closed（且拒絕時**沒有任何寫入**）、戳記在 apply **之前**就在紀錄上、partial 只能由原編號重試、
不 publish 不結案、不在任何無人值守的 allowlist。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine_b import todo
from intake import actions as research_actions
from intake import application
from intake import provenance as intake

ROOT = Path(__file__).resolve().parent.parent
BASIS = "Official public filing retained for private research"


def _entry():
    spec = importlib.util.spec_from_file_location("apply_ra_admission", ROOT / "scripts" / "apply_ra_admission.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apply_ra_admission"] = module
    spec.loader.exec_module(module)
    return module


def _payload(doc_id: str = "entry_doc") -> dict:
    extraction = {"schema_version": "0.1",
                  "source_doc": {"doc_id": doc_id, "title": "Entry doc", "source_type": "filing", "evidence_tier": 1,
                                 "origin_entity": "Test Issuer", "storage_permission": "repo_full",
                                 "permission_basis": BASIS, "url": "https://example.com/entry"},
                  "sources": [], "nodes": [], "edges": [], "claims": []}
    return {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "entry-action",
            "report": {"title": "t", "why_now": "w", "findings": "f", "search_summary": "s", "l8_notes": "l",
                       "counterevidence_and_gaps": "c"},
            "documents": [{"doc_id": doc_id, "extraction": extraction, "raw_payload": {}, "storage_permission": "repo_full",
                           "permission_basis": BASIS, "validation_warnings": []}]}


@pytest.fixture()
def env(tmp_path: Path):
    record = research_actions.create_action(_payload(), root=tmp_path)
    pool = todo.empty_pool()
    item = todo.upsert(pool, item_type="ra_admission", ref_id=record["action_id"], title="RA")
    other = todo.upsert(pool, item_type="manual", ref_id="m1", title="手動項")
    pool_path = tmp_path / "todo_pool.json"
    todo.save(pool, pool_path)
    return {"root": tmp_path, "record": record, "n": item["n"], "manual_n": other["n"], "pool": pool_path,
            "digest": record["action_digest"], "module": _entry()}


def _fake_loader(calls: list[str], *, root: Path, action_id: str, fail_once: bool = False):
    state = {"failed": False}

    def load(extraction_json, storage_permission, permission_basis, *, root: Path, **raw_payload) -> dict:
        # 戳記必須在任何圖寫入之前就已經在紀錄上
        stamped = research_actions.read_action(action_id, root=root)["execution"].get("approval")
        assert stamped is not None, "apply 開始前就要有 approval 戳記"
        extraction = json.loads(extraction_json)
        doc_id = extraction["source_doc"]["doc_id"]
        calls.append(doc_id)
        if fail_once and not state["failed"]:
            state["failed"] = True
            return {"status": "pending_graph", "doc_id": doc_id, "error": "simulated outage", "resolved_paths": []}
        provenance = intake.publish_provenance(doc_id, extraction, raw_payload, root=root)
        intake.mark_graph_complete(doc_id, extraction, root=root)
        return {"status": "loaded_or_already_complete", "doc_id": doc_id, "resolved_paths": provenance["paths"],
                "open_conflict_ids": [], "stale_resolution_ids": [], "finalize_eligible": provenance["finalize_eligible"],
                "extraction_sha256": intake.canonical_extraction_hash(extraction),
                "counts": {"nodes": 0, "edges": 0, "claims": 0}, "warnings": []}

    return load


def _run(env, *args: str) -> int:
    return env["module"].main(["--pool", str(env["pool"]), "--root", str(env["root"]), *args])


def _unchanged(env) -> None:
    record = research_actions.read_action(env["record"]["action_id"], root=env["root"])
    assert record["revision"] == env["record"]["revision"] and "approval" not in record["execution"]


def test_refusals_write_nothing(env, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise AssertionError("refused apply must not reach the graph loader")

    monkeypatch.setattr(application, "_load_extraction_impl", boom)
    digest, n = env["digest"], env["n"]
    assert _run(env, "--pq2", "999", "--digest", digest) == 2                 # ① 編號不存在
    assert _run(env, "--pq2", str(env["manual_n"]), "--digest", digest) == 2  # ① 型別不是 ra_admission
    assert _run(env, "--pq2", str(n), "--digest", "b" * 64) == 2              # ③ digest 不符
    assert _run(env, "--pq2", str(n), "--digest", "not-a-digest") == 2
    _unchanged(env)
    pool = todo.load(env["pool"])
    todo.resolve(pool, n, "drop", reason="使用者 drop")
    todo.save(pool, env["pool"])
    assert _run(env, "--pq2", str(n), "--digest", digest) == 2                 # ① 已 drop：永久拒絕
    _unchanged(env)


def test_expired_record_is_refused_and_says_re_prepare(env, capsys) -> None:
    module = env["module"]
    later = datetime.now(timezone.utc) + research_actions.READY_TTL + timedelta(days=1)
    with pytest.raises(module.ApplyRefused, match="重跑 prepare"):
        module.check_and_stamp(env["n"], env["digest"], pool_path=env["pool"], root=env["root"], now=later)
    _unchanged(env)


def test_success_stamps_before_apply_and_neither_publishes_nor_resolves(env, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(application, "_load_extraction_impl",
                        _fake_loader(calls, root=env["root"], action_id=env["record"]["action_id"]))
    assert _run(env, "--pq2", str(env["n"]), "--digest", env["digest"]) == 0
    record = research_actions.read_action(env["record"]["action_id"], root=env["root"])
    assert record["state"] == "applied" and calls == ["entry_doc"]
    approval = record["execution"]["approval"]
    assert approval["pq2_n"] == env["n"] and approval["digest"] == env["digest"]
    assert record["git"]["status"] == "pending"                                # 不 publish
    assert [i["n"] for i in todo.active_items(todo.load(env["pool"]))] == [env["n"], env["manual_n"]]  # 不結案
    # 已 apply 的再跑一次 → 拒絕（請走 publish／complete-ra）
    assert _run(env, "--pq2", str(env["n"]), "--digest", env["digest"]) == 2


def test_partial_apply_can_only_be_retried_by_the_same_number(env, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(application, "_load_extraction_impl",
                        _fake_loader(calls, root=env["root"], action_id=env["record"]["action_id"], fail_once=True))
    assert _run(env, "--pq2", str(env["n"]), "--digest", env["digest"]) == 3
    record = research_actions.read_action(env["record"]["action_id"], root=env["root"])
    assert record["state"] == "partial" and record["execution"]["approval"]["pq2_n"] == env["n"]
    # 另一個 ra_admission 編號指到**同一筆紀錄**（原編號 drop 後重新掛號）→ 拒絕：同一筆紀錄不能被兩個編號核准
    other_pool = todo.load(env["pool"])
    todo.resolve(other_pool, env["n"], "drop", reason="模擬重新掛號")
    second = todo.upsert(other_pool, item_type="ra_admission", ref_id=env["record"]["action_id"], title="重掛")
    other_path = env["root"] / "other_pool.json"
    todo.save(other_pool, other_path)
    assert second["n"] != env["n"]
    with pytest.raises(env["module"].ApplyRefused, match="蓋過核准戳記"):
        env["module"].check_and_stamp(second["n"], env["digest"], pool_path=other_path, root=env["root"])
    # 原編號（原池子）重試 → 完成
    assert _run(env, "--pq2", str(env["n"]), "--digest", env["digest"]) == 0
    assert research_actions.read_action(env["record"]["action_id"], root=env["root"])["state"] == "applied"


def test_entry_is_interactive_only() -> None:
    """不進任何無人值守 allowlist：codex rules、daily 固定步驟、專案設定的 allow 清單（sandbox impact review 步驟 4）。"""
    rules = (ROOT / ".codex" / "rules" / "stockbot-automations.rules").read_text(encoding="utf-8")
    daily = (ROOT / "crons" / "daily_task.py").read_text(encoding="utf-8")
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "apply_ra_admission" not in rules
    assert "apply_ra_admission" not in daily
    assert "apply_ra_admission" not in json.dumps(settings.get("permissions") or {})
