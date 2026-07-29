"""統一待辦池（廣義 pq2）：持久編號、批次 dispatch、稽核 log。"""
from __future__ import annotations

import json

import pytest

from engine_b import todo
from engine_b import leads
from engine_b.batch import parse_batch_reply


def _pool_with(*rows):
    pool = todo.empty_pool()
    todo.sync(pool, rows)
    return pool


def test_numbers_are_assigned_and_persist_across_resync() -> None:
    rows = [
        {"type": "lead_research", "ref_id": "lead_a", "title": "A"},
        {"type": "ra_admission", "ref_id": "ra_b", "title": "B"},
    ]
    pool = _pool_with(*rows)
    first = {i["ref_id"]: i["n"] for i in todo.active_items(pool)}

    # 再同步一次（順序顛倒、且多一筆）——既有項目編號不得改變
    todo.sync(pool, [rows[1], rows[0], {"type": "manual", "ref_id": "m1", "title": "C"}])
    second = {i["ref_id"]: i["n"] for i in todo.active_items(pool)}

    assert second["lead_a"] == first["lead_a"]
    assert second["ra_b"] == first["ra_b"]
    assert second["m1"] not in (first["lead_a"], first["ra_b"])


def test_upsert_is_idempotent_and_updates_title_only() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "x", "title": "舊"})
    n_before = todo.active_items(pool)[0]["n"]
    todo.sync(pool, [{"type": "lead_research", "ref_id": "x", "title": "新"}])
    items = todo.active_items(pool)
    assert len(items) == 1
    assert items[0]["n"] == n_before
    assert items[0]["title"] == "新"


def test_resolve_go_removes_from_active_and_logs() -> None:
    pool = _pool_with({"type": "manual", "ref_id": "x", "title": "A"})
    n = todo.active_items(pool)[0]["n"]
    todo.resolve(
        pool, n, "go", reason="值得深挖", receipt="authority:engine_c;ref:mo_1"
    )
    assert todo.active_items(pool) == []
    entry = pool["log"][-1]
    assert entry["verb"] == "go" and entry["reason"] == "值得深挖" and entry["n"] == n


def test_pending_defers_but_keeps_item_active() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "x", "title": "A"})
    n = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n, "pending")
    items = todo.active_items(pool)
    assert len(items) == 1 and items[0]["deferred_at"]
    assert pool["log"][-1]["verb"] == "pending"


def test_batch_applies_and_reports_failures() -> None:
    pool = _pool_with(
        {"type": "lead_research", "ref_id": "a", "title": "A"},
        {"type": "lead_research", "ref_id": "b", "title": "B"},
        {"type": "ra_admission", "ref_id": "c", "title": "C"},
    )
    parsed = parse_batch_reply("1 3 go 2 drop 99 pending")
    outcome = todo.apply_batch(pool, parsed)
    assert outcome["applied"] == [2]
    assert outcome["failed"] == [1, 3, 99]  # bare go 與未知編號不中斷其餘
    assert [item["n"] for item in todo.active_items(pool)] == [1, 3]


def test_unknown_number_and_verb_rejected() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "a", "title": "A"})
    with pytest.raises(todo.TodoError):
        todo.resolve(pool, 999, "go")
    with pytest.raises(todo.TodoError):
        todo.resolve(pool, 1, "nonsense")


def test_unknown_type_rejected() -> None:
    pool = todo.empty_pool()
    with pytest.raises(todo.TodoError):
        todo.upsert(pool, item_type="not_a_type", ref_id="x", title="X")


def test_resolved_item_can_reenter_pool_with_new_number() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    n1 = todo.active_items(pool)[0]["n"]
    item = todo.active_items(pool)[0]
    item["dispatch_status"] = "completed"
    item["dispatch_receipt"] = "decision:pd_new"
    todo.resolve(pool, n1, "go", receipt="decision:pd_new")
    # 同一 cohort 之後又有新 evidence-delta → 應重新進池（resolve 不是永久黑名單）
    todo.sync(pool, [{"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW 再現"}])
    items = todo.active_items(pool)
    assert len(items) == 1 and items[0]["n"] != n1


class _WorkOrderStore:
    def __init__(self) -> None:
        self.status = "proposed"
        self.transitions = []

    def latest_research_work_order(self, cohort_id):
        assert cohort_id == "dc_1"
        return {
            "work_order_id": "wo_1",
            "decision_id": "pd_old",
            "status": self.status,
        }

    def transition_research_work_order(self, **kwargs):
        self.status = kwargs["to_status"]
        self.transitions.append(kwargs)
        return {"work_order_id": kwargs["work_order_id"], "status": self.status}

    def get_decision(self, decision_id):
        if decision_id != "pd_new":
            raise KeyError(decision_id)
        return {"decision_id": decision_id, "cohort_id": "dc_1"}


def test_decision_review_go_dispatches_pq1_without_resolving() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    store = _WorkOrderStore()

    result = todo.dispatch_decision_review(
        pool, 1, store=store, at="2026-07-27T00:00:00+00:00"
    )

    assert result["item"]["dispatch_status"] == "queued"
    assert result["item"]["dispatch_ref"] == "wo_1"
    assert todo.active_items(pool)[0]["n"] == 1
    assert todo.actionable_items(pool) == []
    assert pool["log"][-1]["verb"] == "pq1_queued"


def test_batch_cannot_bare_go_a_decision_review() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})

    outcome = todo.apply_batch(pool, parse_batch_reply("1 go"))

    assert outcome == {"applied": [], "failed": [1]}
    assert todo.active_items(pool)[0]["n"] == 1


def test_source_trace_review_go_dispatches_back_to_pq1(tmp_path) -> None:
    leads_path = tmp_path / "leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/paywall"
    )
    leads.triage(store, lead_id, go=True, tier=4, reason="追原報告")
    leads.advance(store, lead_id, "parked", ref={
        "trace_status": "isolated_tier_3",
        "trace_requires_user": "true",
    })
    leads.save(store, leads_path)
    pool = _pool_with({
        "type": "source_trace_review",
        "ref_id": lead_id,
        "title": "追原報告",
    })

    with pytest.raises(todo.TodoError, match="不得 bare go"):
        todo.resolve(pool, 1, "go", receipt="action:ra_fake")

    result = todo.dispatch_source_trace_review(
        pool,
        1,
        leads_path=leads_path,
        at="2026-07-29T00:00:00+00:00",
    )

    assert result["item"]["dispatch_status"] == "queued"
    assert todo.actionable_items(pool) == []
    assert leads.load(leads_path)["leads"][lead_id]["status"] == "triaged_go"


def test_source_trace_review_resolves_only_after_terminal_trace_receipt(tmp_path) -> None:
    leads_path = tmp_path / "leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/paywall"
    )
    leads.triage(store, lead_id, go=True, tier=4, reason="追原報告")
    leads.advance(store, lead_id, "parked", ref={
        "trace_status": "isolated_tier_3",
        "trace_requires_user": "true",
    })
    leads.save(store, leads_path)
    pool = _pool_with({
        "type": "source_trace_review",
        "ref_id": lead_id,
        "title": "追原報告",
    })
    todo.dispatch_source_trace_review(pool, 1, leads_path=leads_path)

    resumed = leads.load(leads_path)
    leads.advance(resumed, lead_id, "parked", ref={
        "trace_status": "isolated_tier_3",
    })
    leads.save(resumed, leads_path)
    result = todo.checkpoint_source_trace_review(
        pool,
        1,
        leads_path=leads_path,
        to_status="parked",
        receipt="trace:isolated_tier_3",
        at="2026-07-29T01:00:00+00:00",
    )

    assert result["item"]["resolved_at"]
    assert result["item"]["receipt"] == "trace:isolated_tier_3"


def test_collect_source_trace_review_only_when_human_authority_required(
    monkeypatch,
) -> None:
    monkeypatch.setattr(leads, "load", lambda: {
        "leads": {
            "lead_manual": {
                "lead_id": "lead_manual",
                "status": "parked",
                "title": "IBK report",
                "url": "https://example.com/ibk",
                "refs": {
                    "trace_status": "isolated_tier_3",
                    "trace_requires_user": "true",
                    "trace_review_title": "追原報告 — IBK supplier map",
                    "trace_review_hint": "有合法 excerpt 才 go；不含購買核准。",
                },
            },
            "lead_event": {
                "lead_id": "lead_event",
                "status": "parked",
                "title": "FCC rule",
                "url": "https://example.com/fcc",
                "refs": {
                    "trace_status": "isolated_tier_3",
                    "trace_next_trigger": "official_rule_published",
                },
            },
        }
    })

    assert todo.collect_from_source_trace_reviews() == [{
        "type": "source_trace_review",
        "ref_id": "lead_manual",
        "title": "追原報告 — IBK supplier map",
        "hint": "有合法 excerpt 才 go；不含購買核准。",
        "source": "source_trace",
    }]


def test_ra_admission_cannot_resolve_without_verified_completion() -> None:
    digest = "a" * 64
    commit = "b" * 40
    pool = _pool_with({"type": "ra_admission", "ref_id": "ra_abc", "title": "RA"})

    with pytest.raises(todo.TodoError, match="complete-ra"):
        todo.resolve(
            pool,
            1,
            "go",
            receipt=f"action:ra_abc;digest:{digest};commit:{commit};cohort:dc_1",
        )


def test_complete_ra_validates_authorities_hands_off_and_resolves(monkeypatch) -> None:
    digest = "a" * 64
    commit = "b" * 40
    pool = _pool_with({"type": "ra_admission", "ref_id": "ra_abc", "title": "RA"})
    monkeypatch.setattr(todo, "_read_action_for_completion", lambda action_id: {
        "action_id": action_id,
        "action_digest": digest,
        "state": "pushed",
        "git": {"status": "pushed", "commit": commit},
        "execution": {
            "documents": [{"doc_id": "doc_1", "status": "complete"}],
            "report": {"status": "complete"},
        },
    })
    monkeypatch.setattr(
        todo,
        "_lead_context_for_action",
        lambda action_id, action_digest, leads_path: {"company_id": "co:axt"},
    )
    shadow_calls = []

    def _handoff(**kwargs):
        shadow_calls.append(kwargs)
        return {"created": True, "cohort_id": "dc_new", "decision_id": "pd_new"}

    monkeypatch.setattr(todo, "_ensure_shadow_for_completion", _handoff)

    result = todo.complete_ra_admission(
        pool,
        1,
        action_digest=digest,
        company_id="co:axt",
        ticker="AXTI",
        leads_path="ignored.json",
        at="2026-07-29T00:00:00+00:00",
    )

    assert todo.active_items(pool) == []
    assert result["receipt"] == (
        f"action:ra_abc;digest:{digest};commit:{commit};cohort:dc_new"
    )
    assert shadow_calls == [{
        "company_id": "co:axt",
        "ticker": "AXTI",
        "as_of": "2026-07-29T00:00:00+00:00",
    }]
    assert pool["log"][-1]["receipt"] == result["receipt"]


def test_ra_lead_context_requires_matching_digest(tmp_path) -> None:
    path = tmp_path / "leads.json"
    path.write_text(json.dumps({
        "schema_version": "2",
        "leads": {
            "lead_1": {
                "status": "applied",
                "refs": {
                    "research_action_id": "ra_abc",
                    "action_digest": "a" * 64,
                    "focus_company_id": "co:axt",
                },
            },
        },
        "harvest_log": [],
        "source_state": {},
    }), encoding="utf-8")

    assert todo._lead_context_for_action(
        "ra_abc", action_digest="a" * 64, leads_path=path
    ) == {"company_id": "co:axt"}
    with pytest.raises(todo.TodoError, match="action_digest"):
        todo._lead_context_for_action(
            "ra_abc", action_digest="b" * 64, leads_path=path
        )


def test_decision_review_cannot_complete_with_baseline_decision() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    store = _WorkOrderStore()
    todo.dispatch_decision_review(
        pool, 1, store=store, at="2026-07-27T00:00:00+00:00"
    )

    with pytest.raises(todo.TodoError, match="有效 decision"):
        todo.checkpoint_decision_review(
            pool, 1, store=store, to_status="completed",
            receipt="decision:pd_old", at="2026-07-27T01:00:00+00:00",
        )

    result = todo.checkpoint_decision_review(
        pool, 1, store=store, to_status="completed",
        receipt="decision:pd_new", reason="gap 補齊後 reassess",
        at="2026-07-27T01:00:00+00:00",
    )
    assert result["item"]["resolved_at"]
    assert result["item"]["receipt"] == "decision:pd_new"


def test_save_load_round_trip(tmp_path) -> None:
    path = tmp_path / "sub" / "todo_pool.json"
    pool = _pool_with({"type": "manual", "ref_id": "m", "title": "手動項"})
    todo.resolve(pool, 1, "pending")
    todo.save(pool, path)
    again = todo.load(path)
    assert todo.active_items(again)[0]["title"] == "手動項"
    assert again["log"][-1]["verb"] == "pending"
    assert again["next_n"] == pool["next_n"]


def test_load_missing_returns_empty_pool(tmp_path) -> None:
    assert todo.load(tmp_path / "nope.json") == todo.empty_pool()


def test_collect_from_decisions_keeps_global_blocker_without_items(monkeypatch) -> None:
    from mcp_server import decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "recommended_action": "REVIEW",
        "reason": "Google Sheet current holdings 無法讀取。",
        "blockers": ["holdings_unavailable"],
        "items": [],
    })

    assert todo.collect_from_decisions() == [{
        "type": "decision_review",
        "ref_id": "global:holdings_unavailable",
        "title": "REVIEW — Google Sheet current holdings 無法讀取。",
        "hint": "修復全域 authority blocker 後重跑 decision_lab today",
        "source": "decision_lab",
    }]


def test_collect_from_research_actions_recognizes_actual_ready_state(monkeypatch) -> None:
    from mcp_server import research_actions

    monkeypatch.setattr(research_actions, "iter_actions", lambda: iter([
        {
            "action_id": "ra_ready",
            "state": "ready",
            "payload": {"report": {"title": "可核准"}},
        },
        {"action_id": "ra_partial", "state": "partial", "title": "可續跑"},
        {"action_id": "ra_done", "state": "pushed", "title": "已完成"},
    ]))

    assert todo.collect_from_research_actions() == [
        {
            "type": "ra_admission",
            "ref_id": "ra_ready",
            "title": "可核准",
            "source": "research_action",
        },
        {
            "type": "ra_admission",
            "ref_id": "ra_partial",
            "title": "可續跑",
            "source": "research_action",
        },
    ]


def test_collect_from_decisions_keeps_sheet_only_items_without_cohort(
    monkeypatch,
) -> None:
    from mcp_server import decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": "co:nvidia",
                "ticker": "NVDA",
                "recommended_action": "REVIEW",
                "sheet_only": True,
            },
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": "unresolved",
                "ticker": "QQQ",
                "recommended_action": "REVIEW",
                "sheet_only": True,
            },
        ],
    })

    assert todo.collect_from_decisions() == [
        {
            "type": "sheet_only_holding",
            "ref_id": "sheet:co:nvidia",
            "title": "REVIEW — co:nvidia",
            "source": "decision_lab",
        },
        {
            "type": "sheet_only_holding",
            "ref_id": "sheet:ticker:QQQ",
            "title": "REVIEW — QQQ",
            "source": "decision_lab",
        },
    ]


def test_collect_from_decisions_uses_company_hint_only_as_display_label(
    monkeypatch,
) -> None:
    from mcp_server import decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [{
            "cohort_id": "dc_private",
            "decision_id": "pd_private",
            "company_id": "unresolved",
            "company_id_hint": "co:agility_robotics",
            "ticker": None,
            "recommended_action": "REVIEW",
        }],
    })

    assert todo.collect_from_decisions() == [{
        "type": "decision_review",
        "ref_id": "dc_private",
        "title": "REVIEW — co:agility_robotics",
        "hint": "核准 bounded gap research；完成後才 reassess",
        "source": "decision_lab",
    }]


def test_raw_leads_are_not_pq2_and_legacy_items_migrate_with_audit() -> None:
    pool = _pool_with(
        {"type": "lead_research", "ref_id": "lead_a", "title": "raw lead"},
        {"type": "manual", "ref_id": "weekly:1", "title": "Weekly topic：Sivers"},
    )

    assert todo.collect_from_leads() == []
    assert todo.retire_legacy_pq1_items(pool, at="2026-07-26T00:00:00+00:00") == 2
    assert todo.active_items(pool) == []
    assert pool["items"][0]["resolution"] == "migrated_to_pq1"
    assert pool["log"][-1]["verb"] == "migrated_to_pq1"


def test_cli_add_and_batch(tmp_path, capsys) -> None:
    path = str(tmp_path / "todo_pool.json")
    assert todo.main(["--pool", path, "add", "查 COHR 客戶集中度", "--hint", "本機查"]) == 0
    capsys.readouterr()
    assert todo.main(["--pool", path, "batch", "1 drop"]) == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["applied"] == [1] and out["failed"] == []
    assert todo.active_items(todo.load(path)) == []
