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


def test_material_decision_event_reactivates_waiting_stable_item() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    todo.resolve(
        pool,
        1,
        "pending",
        trigger="下一份公司 filing",
        event_type="decision_evidence_delta",
        at="2026-08-01T00:00:00+00:00",
    )

    result = todo.sync(
        pool,
        [{
            "type": "decision_review",
            "ref_id": "dc_1",
            "title": "REVIEW — co:axt",
            "event_link": {
                "type": "decision_evidence_delta",
                "value": "material",
                "receipt": "decision:pd_new",
            },
        }],
        at="2026-08-02T00:00:00+00:00",
    )

    item = todo.get(pool, 1)
    assert result["reactivated"] == 1
    assert "waiting_on" not in item
    assert "deferred_at" not in item
    assert item["reactivation_event"]["receipt"] == "decision:pd_new"
    assert pool["log"][-1]["verb"] == "event_reactivated"


def test_material_event_does_not_guess_unbound_human_trigger() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    todo.resolve(pool, 1, "pending", trigger="只等 S-4 公開")

    result = todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "event_link": {
            "type": "decision_evidence_delta",
            "value": "material",
            "receipt": "decision:pd_other",
        },
    }])

    assert result["reactivated"] == 0
    assert todo.get(pool, 1)["waiting_on"]["trigger"] == "只等 S-4 公開"


def test_sync_persists_derived_waiting_and_clears_it_when_mode_changes() -> None:
    waiting = {
        "until": None,
        "trigger": "等下一份 filing",
        "reason": "所有 blocker 都不需要使用者決定",
        "set_at": "2026-08-01T00:00:00+00:00",
        "derived_from_blockers": True,
    }
    pool = todo.empty_pool()
    todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "waiting_on": waiting,
    }])
    assert todo.get(pool, 1)["waiting_on"] == waiting

    result = todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW — needs choice",
    }])
    assert result["reactivated"] == 1
    assert "waiting_on" not in todo.get(pool, 1)


def test_sync_refreshes_a_stale_derived_waiting_reason() -> None:
    """blocker mode 沒變、但等的東西變了時，顯示文字必須跟著更新。

    事發（2026-08-05）：co:applied_optoelectronics 的市場資料問題早已修好，池子卻
    仍顯示「執行面 context 缺失／市場資料問題」——因為舊寫法只在 `waiting_on`
    不存在時才填。結果是待辦池叫使用者去修一個已經修好的東西。
    """

    pool = todo.empty_pool()
    todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "waiting_on": {
            "until": None,
            "trigger": "市場資料問題",
            "reason": "所有 blocker 都不需要使用者決定",
            "set_at": "2026-08-01T00:00:00+00:00",
            "derived_from_blockers": True,
        },
    }])

    result = todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "waiting_on": {
            "until": None,
            "trigger": "財務核驗清單欄位缺失或待人工填入",
            "reason": "所有 blocker 都不需要使用者決定",
            "set_at": "2026-08-05T00:00:00+00:00",
            "derived_from_blockers": True,
        },
    }])

    assert result["waiting_refreshed"] == 1
    assert result["reactivated"] == 0  # 仍在等事件區，沒有回到決策佇列
    assert todo.get(pool, 1)["waiting_on"]["trigger"] == "財務核驗清單欄位缺失或待人工填入"
    assert any(
        entry.get("verb") == "waiting_reason_refreshed" for entry in pool["log"]
    )


def test_sync_never_overwrites_a_user_set_waiting_reason() -> None:
    """使用者用 --until/--trigger 明確設定的等待條件優先於自動推導。"""

    pool = todo.empty_pool()
    todo.sync(pool, [{"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"}])
    todo.resolve(
        pool, 1, "pending", until="2026-08-27", trigger="SIVE Q2 財報"
    )

    result = todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "waiting_on": {
            "until": None,
            "trigger": "市場資料問題",
            "reason": "所有 blocker 都不需要使用者決定",
            "set_at": "2026-08-05T00:00:00+00:00",
            "derived_from_blockers": True,
        },
    }])

    assert result["waiting_refreshed"] == 0
    assert todo.get(pool, 1)["waiting_on"]["trigger"] == "SIVE Q2 財報"
    assert todo.get(pool, 1)["waiting_on"]["until"] == "2026-08-27"


def test_identical_derived_waiting_reason_is_not_rewritten_every_sync() -> None:
    """set_at 每次推導都會變；只有語意欄位改變才算改變，否則會產生 log 噪音。"""

    pool = todo.empty_pool()
    base = {
        "until": None,
        "trigger": "市場資料問題",
        "reason": "所有 blocker 都不需要使用者決定",
        "derived_from_blockers": True,
    }
    todo.sync(pool, [{
        "type": "decision_review", "ref_id": "dc_1", "title": "REVIEW",
        "waiting_on": {**base, "set_at": "2026-08-01T00:00:00+00:00"},
    }])

    result = todo.sync(pool, [{
        "type": "decision_review", "ref_id": "dc_1", "title": "REVIEW",
        "waiting_on": {**base, "set_at": "2026-08-05T00:00:00+00:00"},
    }])

    assert result["waiting_refreshed"] == 0
    assert todo.get(pool, 1)["waiting_on"]["set_at"] == "2026-08-01T00:00:00+00:00"


def test_dropped_ra_admission_is_not_rebuilt_by_sync() -> None:
    """apply 永遠失敗的 RA 被 drop 後不得每次 sync 都取得新編號。"""
    row = {
        "type": "ra_admission",
        "ref_id": "ra_dup",
        "title": "撞 DuplicateUrlError 的 RA",
    }
    pool = todo.empty_pool()
    todo.sync(pool, [row])
    todo.resolve(pool, 1, "drop", reason="與既有 doc 重複，apply 不可能成功")

    result = todo.sync(pool, [row])

    assert result["added"] == 0
    assert result["reactivated"] == 0
    assert [item["n"] for item in todo.active_items(pool)] == []


def test_dropped_ra_admission_returns_under_a_fresh_action_id() -> None:
    """重跑 prepare 產生新 action_id 時仍要重新進池。"""
    pool = todo.empty_pool()
    todo.sync(pool, [{"type": "ra_admission", "ref_id": "ra_old", "title": "舊 RA"}])
    todo.resolve(pool, 1, "drop", reason="重複")

    todo.sync(pool, [{"type": "ra_admission", "ref_id": "ra_new", "title": "重做的 RA"}])

    assert [item["ref_id"] for item in todo.active_items(pool)] == ["ra_new"]


def test_dropped_decision_review_still_reactivates() -> None:
    """drop 的例外只限 ra_admission；decision_review 仍可因新 delta 回池。"""
    row = {"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"}
    pool = todo.empty_pool()
    todo.sync(pool, [row])
    todo.resolve(pool, 1, "drop", reason="本次略過")

    result = todo.sync(pool, [row])

    assert result["added"] == 1
    assert [item["ref_id"] for item in todo.active_items(pool)] == ["dc_1"]


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

    repeated = todo.dispatch_decision_review(pool, 1, store=store)
    assert repeated["work_order"]["status"] == "queued"
    assert len(store.transitions) == 1
    assert len([row for row in pool["log"] if row["verb"] == "pq1_queued"]) == 1


def test_dispatch_clears_waiting_metadata_and_sync_does_not_restore_it() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    todo.resolve(pool, 1, "pending", trigger="等 filing")
    store = _WorkOrderStore()

    todo.dispatch_decision_review(pool, 1, store=store)
    assert "waiting_on" not in todo.get(pool, 1)
    todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_1",
        "title": "REVIEW",
        "waiting_on": {
            "trigger": "系統狀態待更新",
            "derived_from_blockers": True,
        },
    }])
    assert "waiting_on" not in todo.get(pool, 1)


@pytest.mark.parametrize("terminal_status", ["completed", "parked"])
def test_decision_review_go_carries_explicit_terminal_redispatch_receipt(
    terminal_status: str,
) -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    store = _WorkOrderStore()
    store.status = terminal_status

    todo.dispatch_decision_review(
        pool, 1, store=store, at="2026-07-30T00:00:00+00:00"
    )

    receipt = store.transitions[-1]["receipt"]
    assert receipt["todo_n"] == 1
    assert receipt["prior_work_order_status"] == terminal_status
    assert store.status == "queued"


def test_same_todo_can_redispatch_after_work_order_becomes_terminal() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    store = _WorkOrderStore()

    todo.dispatch_decision_review(pool, 1, store=store)
    store.status = "completed"
    todo.dispatch_decision_review(pool, 1, store=store)

    assert [row["operation_key"] for row in store.transitions] == [
        "todo:1:go:1",
        "todo:1:go:2",
    ]
    assert pool["log"][-1]["receipt"] == "wo_1"
    assert todo.get(pool, 1)["dispatch_attempt"] == 2


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
    from engine_b import leads

    monkeypatch.setattr(research_actions, "iter_actions", lambda: iter([
        {
            "action_id": "ra_ready",
            "state": "ready",
            "payload": {"report": {"title": "可核准"}},
        },
        {"action_id": "ra_partial", "state": "partial", "title": "可續跑"},
        {"action_id": "ra_done", "state": "pushed", "title": "已完成"},
    ]))
    monkeypatch.setattr(leads, "load", lambda: {"leads": {
        "lead_ready": {
            "refs": {
                "research_action_id": "ra_ready",
                "focus_company_id": "co:agility_robotics",
            }
        }
    }})

    assert todo.collect_from_research_actions() == [
        {
            "type": "ra_admission",
            "ref_id": "ra_ready",
            "title": "可核准",
            "hint": (
                "核准 exact graph delta；Decision handoff：co:agility_robotics。"
                "RA 內其他公司只作 evidence／relationship context，不自動建 cohort。"
            ),
            "source": "research_action",
        },
        {
            "type": "ra_admission",
            "ref_id": "ra_partial",
            "title": "可續跑",
            "hint": (
                "BLOCKER：Research Action 尚未聲明唯一 focus_company_id；"
                "先回 pq1 補 Decision handoff，不得先 apply。"
            ),
            "source": "research_action",
        },
    ]


def test_collect_from_research_actions_exposes_multiple_focus_blocker(monkeypatch) -> None:
    from mcp_server import research_actions
    from engine_b import leads

    monkeypatch.setattr(research_actions, "iter_actions", lambda: iter([{
        "action_id": "ra_multi",
        "state": "ready",
        "title": "多公司 action",
    }]))
    monkeypatch.setattr(leads, "load", lambda: {"leads": {
        "lead_a": {"refs": {
            "research_action_id": "ra_multi",
            "focus_company_id": "co:a",
        }},
        "lead_b": {"refs": {
            "research_action_id": "ra_multi",
            "focus_company_id": "co:b",
        }},
    }})

    row = todo.collect_from_research_actions()[0]
    assert row["hint"].startswith("BLOCKER：Research Action 有多個 focus_company_id")
    assert "co:a, co:b" in row["hint"]


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


def test_collect_material_decision_never_derives_waiting_from_system_blockers(
    monkeypatch,
) -> None:
    from mcp_server import decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [{
            "cohort_id": "dc_axt",
            "decision_id": "pd_axt",
            "company_id": "co:axt",
            "recommended_action": "REVIEW",
            "evidence_delta": "material",
            "blockers": ["market_stale_since_decision"],
        }],
    })

    row = todo.collect_from_decisions()[0]
    assert "waiting_on" not in row
    assert row["event_link"]["receipt"] == "decision:pd_axt"


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
