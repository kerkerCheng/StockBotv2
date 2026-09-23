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


def test_unconditional_pending_clears_stale_external_wait() -> None:
    """人工判讀不得因上一輪 trigger 繼續被藏在「等事件」。"""
    pool = _pool_with({"type": "manual", "ref_id": "x", "title": "A"})
    todo.resolve(pool, 1, "pending", trigger="等 Q3 guidance")
    assert todo.get(pool, 1)["waiting_on"]["trigger"] == "等 Q3 guidance"

    todo.resolve(pool, 1, "pending", reason="也可由使用者現在指定門檻")

    assert "waiting_on" not in todo.get(pool, 1)
    assert todo.get(pool, 1)["reason"] is None
    assert pool["log"][-1]["reason"] == "也可由使用者現在指定門檻"


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
    # 2026-09-23（Phase 0 Step 0b.4）：原本用 decision_review 當夾具；它已是 legacy 型、go 一律被拒，
    # 判準（resolve 不是永久黑名單）不變，改用 manual 型。
    pool = _pool_with({"type": "manual", "ref_id": "weekly:1", "title": "Weekly topic"})
    n1 = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n1, "go", receipt="authority:registry;ref:weekly:1")
    # 同一主題之後又被提出 → 應重新進池（resolve 不是永久黑名單）
    todo.sync(pool, [{"type": "manual", "ref_id": "weekly:1", "title": "Weekly topic 再現"}])
    items = todo.active_items(pool)
    assert len(items) == 1 and items[0]["n"] != n1


def test_legacy_kinds_cannot_be_resolved_with_go() -> None:
    """2026-09-23（Phase 0 Step 0b.4）：decision_review／sheet_only_holding 的 go 語意整組退役——
    池裡若還有歷史項目只能 drop。這是「退役真的生效」的可證偽斷言。"""
    for legacy in ("decision_review", "sheet_only_holding"):
        pool = _pool_with({"type": legacy, "ref_id": "dc_legacy", "title": "REVIEW"})
        with pytest.raises(todo.TodoError, match="legacy"):
            todo.resolve(pool, 1, "go", receipt="decision:pd_x")
        todo.resolve(pool, 1, "drop", reason="機制退役")
        assert todo.active_items(pool) == []


def test_awaiting_gate_and_in_flight_leave_the_decision_queue() -> None:
    """已 dispatch 的項目先前混在「回覆用編號 go｜drop｜pending」區裡，項目自己卻
    寫「無需再次 go」——區標與內容互相矛盾；而且 awaiting_approval（pq1 做完、等
    人工 gate）與 queued（還沒開始）長得一模一樣，對使用者的意義卻完全不同。
    """

    pool = todo.empty_pool()
    todo.upsert(pool, item_type="decision_review", ref_id="dc_gate", title="REVIEW — A")
    todo.upsert(pool, item_type="decision_review", ref_id="dc_run", title="REVIEW — B")
    todo.get(pool, 1).update(
        {"dispatch_status": "awaiting_approval", "dispatch_ref": "wo_gate"}
    )
    todo.get(pool, 2).update({"dispatch_status": "queued", "dispatch_ref": "wo_run"})
    pool["log"].append({
        "at": "2026-08-06T00:00:00+00:00",
        "n": 1,
        "verb": "pq1_awaiting_approval",
        "reason": "需 exact graph admission 後才能 reassess",
        "receipt": "research_packet:library/private/x.json",
    })

    rendered = todo._render(pool)

    assert "pq1 已交回，等人工 gate" in rendered
    assert "不吃 go／drop／pending" in rendered
    # checkpoint 自己寫的理由比任何泛用提示準確。
    assert "需 exact graph admission 後才能 reassess" in rendered
    assert "research_packet:library/private/x.json" in rendered
    assert "pq1 進行中" in rendered
    # 兩者都不得出現在決策佇列。
    assert "目前沒有需要你決定的項目" in rendered


def test_explicit_external_waiting_overrides_prior_awaiting_approval() -> None:
    """研究完成後若確認只能等外部 filing，不得因舊 dispatch 狀態繼續顯示人工 gate。"""

    pool = todo.empty_pool()
    item = todo.upsert(
        pool,
        item_type="decision_review",
        ref_id="dc_lite",
        title="REVIEW — co:lumentum",
    )
    item.update(
        {
            "dispatch_status": "awaiting_approval",
            "dispatch_ref": "wo_old_gate",
            "waiting_on": {
                "until": "2026-08-20",
                "trigger": "Lumentum FY2026 Form 10-K 公開完整 cash-flow statement",
                "reason": "現有 8-K 沒有 FCF；這是等外部文件，不是等人工判讀",
                "set_at": "2026-08-15T00:00:00+00:00",
            },
        }
    )

    rendered = todo._render(pool)

    assert "## 等事件（1 項，觸發前不需動作）" in rendered
    assert "Lumentum FY2026 Form 10-K" in rendered
    assert "pq1 已交回，等人工 gate" not in rendered
    assert todo.actionable_items(pool) == []


#: ⚠ 2026-09-22（Phase 0 Step 0a.4）：本組測試原本以 `decision_review` ＋ `"decisions"` 來源
#: 當測資。那個 type 已改 legacy 標記、collector 已從 `SOURCE_COLLECTORS` 移除，所以它**永遠
#: 不會出現在 `healthy`**，拿它當測資會讓 `_mark_source_cleared` 恆不觸發＝這組測試恆綠。
#: **被測的機制沒有退役**（「來源成功執行但不再產出這一項」仍適用於所有活的 type），
#: 所以改主詞為 `source_trace_review` ＋ `"source_trace"`，判準一字未改。
_CLEARED_SOURCE = "source_trace"


def _decision_row(ref_id: str = "dc_1") -> dict:
    return {"type": "source_trace_review", "ref_id": ref_id, "title": "追源 — co:x"}


def test_source_that_stops_producing_a_row_marks_it_as_done_candidate() -> None:
    """來源成功執行但不再產出該項＝很可能已完成，移出決策注意力。

    事發（2026-08-05）：[85] 與 [84] 在同一個 session 內先後變成殘留項。sync 只
    走訪 incoming，而 collect_from_decisions 會跳過不需要人看（U7 起是 `MONITOR`，
    先前寫作 NO ACTION）的 decision，所以
    項目一旦「做完」，它的來源 row 就消失、再也沒有任何分支碰得到它——項目越
    接近完成，池子越無法反映它。
    """

    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={_CLEARED_SOURCE})
    assert not todo.get(pool, 1).get("source_cleared")

    result = todo.sync(pool, [], healthy_sources={_CLEARED_SOURCE})

    assert result["source_cleared"] == 1
    assert todo.get(pool, 1)["source_cleared"]["source_healthy"] is True
    assert any(entry.get("verb") == "source_cleared" for entry in pool["log"])
    # 只是標記，絕不自動結案。
    assert todo.get(pool, 1).get("resolved_at") is None


def test_in_flight_work_order_is_never_marked_source_cleared() -> None:
    """awaiting exact gate 比 collector 缺席更有權威，不得提示使用者 drop。"""
    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={_CLEARED_SOURCE})
    item = todo.get(pool, 1)
    item["dispatch_status"] = "awaiting_approval"
    item["dispatch_receipt"] = "observation-proposal:po_1"
    item["source_cleared"] = {
        "at": "2026-08-15T00:00:00+00:00",
        "source_healthy": True,
        "reason": "stale marker",
    }

    result = todo.sync(pool, [], healthy_sources={_CLEARED_SOURCE})

    assert result["source_cleared"] == 0
    assert result["source_returned"] == 1
    assert "source_cleared" not in todo.get(pool, 1)


def test_unhealthy_source_never_marks_anything_even_with_zero_rows() -> None:
    """斷線與「全部做完」在 sync 眼中不可以長得一樣。

    四個 collector 都是 fail-soft（例外回空清單）。少了健康訊號，任何「來源消失
    就結案」的邏輯都會在 Neo4j／Sheet 斷線那一次把整個池安靜清空。
    """

    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row("dc_1"), _decision_row("dc_2")],
              healthy_sources={_CLEARED_SOURCE})

    result = todo.sync(pool, [], healthy_sources=set())  # collector 全掛

    assert result["source_cleared"] == 0
    assert not todo.get(pool, 1).get("source_cleared")
    assert not todo.get(pool, 2).get("source_cleared")


def test_healthy_source_does_not_clear_another_sources_items() -> None:
    """decisions 正常、lifecycle 掛掉時，不得把 thesis_lifecycle 判成完成。"""

    pool = todo.empty_pool()
    todo.sync(
        pool,
        [_decision_row(), {"type": "thesis_lifecycle", "ref_id": "t1", "title": "到期"}],
        healthy_sources={"decisions", "lifecycle"},
    )

    result = todo.sync(pool, [], healthy_sources={_CLEARED_SOURCE})

    assert result["source_cleared"] == 1
    assert todo.get(pool, 1)["source_cleared"]        # decision_review 被標記
    assert not todo.get(pool, 2).get("source_cleared")  # lifecycle 未判定


def test_returning_row_revokes_the_done_candidate_mark() -> None:
    """新證據把 decision 推回 REVIEW 時，標記要撤銷而不是留著誤導。"""

    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={_CLEARED_SOURCE})
    todo.sync(pool, [], healthy_sources={_CLEARED_SOURCE})
    assert todo.get(pool, 1)["source_cleared"]

    result = todo.sync(pool, [_decision_row()], healthy_sources={_CLEARED_SOURCE})

    assert result["source_returned"] == 1
    assert "source_cleared" not in todo.get(pool, 1)
    assert any(entry.get("verb") == "source_returned" for entry in pool["log"])


def test_done_candidates_render_in_their_own_section_with_drop_hint() -> None:
    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={_CLEARED_SOURCE})
    todo.sync(pool, [], healthy_sources={_CLEARED_SOURCE})

    rendered = todo._render(pool)

    assert "已完成，待確認關閉" in rendered
    assert "1 drop" in rendered
    # 不得混進「等事件」或決策佇列。
    assert "等事件" not in rendered


def test_manual_items_are_never_auto_marked_by_any_source() -> None:
    """`manual` 沒有 collector，缺席不代表完成。"""

    pool = todo.empty_pool()
    todo.upsert(pool, item_type="manual", ref_id="m1", title="手動待辦")

    result = todo.sync(pool, [], healthy_sources=set(todo.SOURCE_ITEM_TYPES))

    assert result["source_cleared"] == 0
    assert not todo.get(pool, 1).get("source_cleared")


def test_collect_all_with_health_reports_only_the_sources_that_ran(
    monkeypatch,
) -> None:
    # 由登記表導出要 patch 的 collector，不逐一手寫名稱。
    # 手寫的後果已經發生過：新增第 5、6 個 collector 時沒人記得更新這裡，
    # 那兩個未被 patch 的 collector 讀到**真實 private runtime 狀態**，
    # 於是本測試隨 daily 產出漂移而恆紅。恆紅＝整套 suite 失去鑑別力。
    # 2026-09-23（Phase 0 Step 0b.4）：失敗源原本是 decisions collector（已隨研究側退役、不在登記表上），
    # 改讓 lifecycle collector 炸——判準（失敗的來源不進 healthy）不變。
    for name, attr in todo.SOURCE_COLLECTORS:
        if name == "lifecycle":
            continue
        monkeypatch.setattr(todo, attr, lambda: [])

    def boom():
        raise RuntimeError("lifecycle.json unreadable")

    monkeypatch.setattr(todo, "_collect_lifecycle_rows", boom)

    collected = todo.collect_all_with_health()

    assert collected.rows == [], "所有 collector 都被 patch 成空，不得有真實資料漏進來"
    assert "lifecycle" not in collected.healthy
    assert "decisions" not in {name for name, _ in todo.SOURCE_COLLECTORS}
    expected_healthy = {name for name, _ in todo.SOURCE_COLLECTORS} - {"lifecycle"}
    assert collected.healthy == expected_healthy


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
    assert [item["n"] for item in todo.active_items(pool)] == []


def test_dropped_ra_admission_returns_under_a_fresh_action_id() -> None:
    """重跑 prepare 產生新 action_id 時仍要重新進池。"""
    pool = todo.empty_pool()
    todo.sync(pool, [{"type": "ra_admission", "ref_id": "ra_old", "title": "舊 RA"}])
    todo.resolve(pool, 1, "drop", reason="重複")

    todo.sync(pool, [{"type": "ra_admission", "ref_id": "ra_new", "title": "重做的 RA"}])

    assert [item["ref_id"] for item in todo.active_items(pool)] == ["ra_new"]


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
            receipt=f"action:ra_abc;digest:{digest};commit:{commit}",
        )


def test_complete_ra_validates_authorities_and_resolves(monkeypatch) -> None:
    """⚠ 2026-09-23（Phase 0 Step 0b.4）：Decision handoff 隨 decision_lab 研究側退役——
    receipt 只剩 action／digest／commit，complete-ra **不得**再碰 Decision Store（沒有 cohort 可建）。
    原測試名 `..._hands_off_and_resolves` 守的那個 handoff 呼叫已不存在，改守「沒有 handoff」。"""
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
        lambda action_id, action_digest, leads_path: {
            "company_id": "co:axt",
            "title": "AXT／Casela 2027 InP 長約",
        },
    )
    assert not hasattr(todo, "_ensure_shadow_for_completion"), "Decision handoff 已退役，不得再有這條路"

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
    assert result["receipt"] == f"action:ra_abc;digest:{digest};commit:{commit}"
    assert "handoff" not in result and "cohort" not in result["receipt"]
    assert pool["items"][0]["completion_authority"]["company_id"] == "co:axt"
    assert "cohort_id" not in pool["items"][0]["completion_authority"]
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
    # title 一併回傳：它會成為 cohort 的 atomic_claim，讓「當初我們認為這是什麼」
    # 有可回溯紀錄（先前 10/10 個 cohort 的 claim 都是空的）。
    ) == {"company_id": "co:axt", "title": ""}
    with pytest.raises(todo.TodoError, match="action_digest"):
        todo._lead_context_for_action(
            "ra_abc", action_digest="b" * 64, leads_path=path
        )


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


def test_collect_from_research_actions_recognizes_actual_ready_state(monkeypatch) -> None:
    from intake import actions as research_actions
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
                "核准 exact graph delta；focus company：co:agility_robotics。"
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
                "先回 pq1 補 focus company，不得先 apply。"
            ),
            "source": "research_action",
        },
    ]


def test_collect_from_research_actions_exposes_multiple_focus_blocker(monkeypatch) -> None:
    from intake import actions as research_actions
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


def _ready_action(action_id: str, *, focus: str | None = None) -> dict:
    payload: dict = {"report": {"title": "RA 標題"}}
    if focus is not None:
        payload["focus_company_id"] = focus
    return {"action_id": action_id, "state": "ready", "payload": payload}


def test_ra_can_declare_its_own_decision_handoff(monkeypatch) -> None:
    """從 decision gap work order 產出的 RA 沒有 lead 可綁。

    事發（2026-08-06）：focus_company_id 只從綁定 lead 的 refs 讀，所以任何不是
    從 lead 來的 RA 都被判成「未聲明 focus」而卡住——即使它的 cohort 早就指名了
    公司。RA 自己聲明是那條缺掉的走廊。
    """

    monkeypatch.setattr(
        todo, "iter_actions", lambda: [_ready_action("ra_x", focus="co:meta")],
        raising=False,
    )
    monkeypatch.setitem(
        __import__("sys").modules, "intake.actions",
        type("M", (), {"iter_actions": staticmethod(
            lambda: [_ready_action("ra_x", focus="co:meta")]
        )})(),
    )

    rows = todo._collect_research_action_rows()

    assert len(rows) == 1
    assert "focus company：co:meta" in rows[0]["hint"]
    assert "BLOCKER" not in rows[0]["hint"]


def test_ra_without_any_focus_still_blocks(monkeypatch) -> None:
    monkeypatch.setitem(
        __import__("sys").modules, "intake.actions",
        type("M", (), {"iter_actions": staticmethod(
            lambda: [_ready_action("ra_y")]
        )})(),
    )

    rows = todo._collect_research_action_rows()

    assert "BLOCKER" in rows[0]["hint"]
    assert "尚未聲明唯一 focus_company_id" in rows[0]["hint"]


def _trace_lead_applied(tmp_path, doc_id: str, *, stop_at_prepared: bool = False):
    """建一筆走 loader 入圖路徑（無 RA id）而 applied 的 trace lead。"""

    leads_path = tmp_path / "leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/transcript"
    )
    leads.triage(store, lead_id, go=True, tier=2, reason="追法說會逐字稿")
    leads.advance(store, lead_id, "parked", ref={
        "trace_status": "partial", "trace_requires_user": "true",
    })
    leads.save(store, leads_path)
    pool = _pool_with({
        "type": "source_trace_review",
        "ref_id": lead_id,
        "title": "追法說會逐字稿",
    })
    # dispatch 會把 parked lead requeue 回 pq1；之後才走到 applied，與真實流程一致。
    todo.dispatch_source_trace_review(pool, 1, leads_path=leads_path)
    resumed = leads.load(leads_path)
    if resumed["leads"][lead_id]["status"] != "researching":
        leads.advance(resumed, lead_id, "researching")
    leads.advance(resumed, lead_id, "action_prepared", ref={"source_doc": doc_id})
    if stop_at_prepared:
        leads.save(resumed, leads_path)
        return pool, leads_path
    leads.advance(resumed, lead_id, "applied", ref={"source_doc": doc_id})
    leads.save(resumed, leads_path)
    return pool, leads_path


def test_loader_graph_receipt_can_complete_a_trace_review(tmp_path) -> None:
    """正確的入圖路徑就該結得了案。

    事發（2026-08-15）：COHR 與 MTSI 兩場法說會逐字稿追到、抽取、validate、load 進
    Neo4j 全部完成，lead 也 applied，卻結不了案——完成規則只認 action:ra_*，而
    `loader.load_to_neo4j`（repo 內既有的正規入圖路徑）根本不產生 RA id。
    那是 gate 攔格式而不是攔風險（L15 第 1 條）。
    """

    doc_id = "cohr_q4fy26_earnings_call_2026_08_12"  # 真實存在於 extractions/
    pool, leads_path = _trace_lead_applied(tmp_path, doc_id)

    result = todo.checkpoint_source_trace_review(
        pool, 1, leads_path=leads_path,
        to_status="completed", receipt=f"graph:{doc_id}",
        at="2026-08-15T01:00:00+00:00",
    )

    assert result["item"]["resolved_at"]
    assert result["item"]["receipt"] == f"graph:{doc_id}"


def test_graph_receipt_requires_an_auditable_extraction_file(tmp_path) -> None:
    """放寬解析不等於放寬判準：receipt 必須指向可稽核的實體，不能只是字串。

    graph 路徑的門檻刻意比 RA 路徑高一項——extractions/<doc_id>.json 必須真的存在。
    否則「改成接受 graph:」就會變成「接受任何自稱入過圖的字串」（L15 第 5 條）。
    """

    doc_id = "never_extracted_doc_id"
    pool, leads_path = _trace_lead_applied(tmp_path, doc_id)

    with pytest.raises(todo.TodoError, match="無可稽核依據"):
        todo.checkpoint_source_trace_review(
            pool, 1, leads_path=leads_path,
            to_status="completed", receipt=f"graph:{doc_id}",
        )


def test_graph_receipt_must_match_the_lead_source_doc(tmp_path) -> None:
    """receipt 不得指向另一份文件——那會讓入圖紀錄與 pq2 收據脫鉤。"""

    pool, leads_path = _trace_lead_applied(
        tmp_path, "cohr_q4fy26_earnings_call_2026_08_12"
    )

    with pytest.raises(todo.TodoError, match="source_doc"):
        todo.checkpoint_source_trace_review(
            pool, 1, leads_path=leads_path,
            to_status="completed",
            receipt="graph:mtsi_q3fy26_earnings_call_2026_08_06",
        )


def test_graph_receipt_rejects_a_lead_that_was_never_loaded(tmp_path) -> None:
    """loader 路徑沒有 prepared 中間態：停在 action_prepared 就代表還沒真的載入。"""

    doc_id = "cohr_q4fy26_earnings_call_2026_08_12"
    pool, leads_path = _trace_lead_applied(tmp_path, doc_id, stop_at_prepared=True)

    with pytest.raises(todo.TodoError, match="applied"):
        todo.checkpoint_source_trace_review(
            pool, 1, leads_path=leads_path,
            to_status="completed", receipt=f"graph:{doc_id}",
        )


def _decision_pool(n=1, cohort="dc_abc"):
    return {
        "items": [{
            "n": n, "type": "decision_review", "ref_id": cohort,
            "title": "REVIEW — co:x", "hint": "", "source": "decision_lab",
            "reason": None, "resolution": None, "resolved_at": None,
            "added_at": "2026-08-26T00:00:00+00:00",
        }],
        "log": [], "next_n": n + 1, "schema_version": "1",
    }


def test_every_item_type_declares_its_go_authorization_boundary() -> None:
    """每個 pq2 類型都必須明講 `go` 授權什麼、不含什麼。

    `AGENTS.md` 反覆寫過同一件事（研究 `go` 不代表入圖、入圖 `go` 不代表 thesis
    mutation、任何 `go` 都不代表 live），但那些句子散在政策檔裡，每個消費端都得
    自己回想一次——而回想錯的方向永遠是「以為授權比較寬」。分類有 SSOT 就要跟著
    資料走到需要它的地方（L16）。

    鍵一致是這條的重點：新增類型時會被強迫決定它的授權邊界，而不是靜默繼承
    某個較寬的預設。
    """
    assert set(todo.ITEM_TYPES) == set(todo.GO_AUTHORIZATION)
    for item_type, (authorizes, excludes) in todo.GO_AUTHORIZATION.items():
        assert authorizes.strip(), item_type
        assert excludes.strip(), item_type


def test_collected_rows_carry_the_go_boundary_so_consumers_need_not_recall_it() -> None:
    """授權邊界掛在 row 上，brief 不必自己查——漏掉時的預設是「沒有邊界」。"""
    rows = todo._attach_go_authorization(
        [{"type": "source_trace_review"}, {"type": "ra_admission"}]
    )

    # ⚠ 2026-09-22 Step 0a.4：原本用 `decision_review`（現為 legacy 標記）。改用追源型，
    # 它的邊界句仍是活的；同時補一條斷言鎖住「legacy 的兩個 kind 不得長回授權語意」。
    assert rows[0]["go_authorizes"].startswith("bounded 追源")
    assert "入圖" in rows[0]["go_excludes"]
    for legacy in ("decision_review", "sheet_only_holding", "lead_research"):
        legacy_row = todo._attach_go_authorization([{"type": legacy}])[0]
        assert "legacy" in legacy_row["go_authorizes"], legacy
    assert "graph admission" in rows[1]["go_authorizes"]
    assert "live" in rows[1]["go_excludes"]


def test_graph_impact_reads_the_frozen_payload_not_only_the_draft() -> None:
    """圖影響一句話必須認 prepare 凍結後的 `extraction`，不只 draft 的 `extraction_json`。

    事發（2026-08-31，上線當天）：`_ra_graph_impact` 只讀字串欄位 `extraction_json`，
    但那是 `library/leads/action_drafts/*.json` 的 draft 格式；`prepare_research_action`
    凍結後會正規化成 dict 欄位 `extraction`。於是它對**每一個真實 RA** 都回空字串——
    實測池內 328 個項目 `graph_impact` 出現 0 次，使用者從來沒看過這行。

    這是 L13：機制回傳「成功」（fail-soft 回空字串不報錯），但產出從未出現在下游手上。
    驗收條件因此寫成「凍結格式也數得出來」，不是「函式不拋例外」。
    """
    extraction = {
        "source_doc": {"origin_entity": "Example Co", "evidence_tier": 3},
        "nodes": [{"id": "co:a"}, {"id": "co:b"}],
        "edges": [{"id": "e1"}],
        "claims": [{"id": "cl1"}],
    }

    frozen = {"documents": [{"doc_id": "d", "extraction": extraction}]}
    draft = {"documents": [{"doc_id": "d", "extraction_json": json.dumps(extraction)}]}

    expected = "+2 節點、1 邊、1 claims｜來源：Example Co（tier 3）"
    assert todo._ra_graph_impact(frozen) == expected
    assert todo._ra_graph_impact(draft) == expected
    assert todo._ra_graph_impact({"documents": [{"doc_id": "d"}]}) == ""


# ---------------------------------------------------------------------------
# 佇列段 1／段 2（2026-09-09 P1）
# ---------------------------------------------------------------------------

def test_check_event_watches_consumes_already_fired_pq2_watches(monkeypatch) -> None:
    """triage 路徑先把 pq2 型 watch 標成 fired 存檔 → 本函式再 check 時它已不是 active，
    先前永遠不會再收它（[134] 的 ew_0002 掛了一週）。修法：consumer 掃 status 本身。"""
    from engine_b import event_watch as ew

    pool = _pool_with({"type": "manual", "ref_id": "m", "title": "等 Q3 guidance"})
    n = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n, "pending", trigger="等 Q3 guidance")
    assert todo.get(pool, n).get("waiting_on")

    data = {"schema_version": 1, "watches": [
        {"watch_id": "ew_pre", "status": "fired", "kind": "fact_verification",
         "wake_pq2": n, "entities": ["AAOI"], "expires": "2027-01-01",
         "woken_by": {"kind": "fact_verification", "lead_id": "lead_x",
                      "shared_entities": ["AAOI"], "at": "2026-09-01T00:00:00+00:00"}},
    ]}
    saved: dict = {}
    monkeypatch.setattr(ew, "load_watches", lambda path=None: data)
    monkeypatch.setattr(ew, "save_watches", lambda d, path=None: saved.update(d))
    monkeypatch.setattr(ew, "check_watches", lambda d, leads=None, today=None: [])  # 本輪沒有新觸發

    woken, counters = todo._check_event_watches(pool, stamp="2026-09-09T00:00:00+00:00")

    assert woken == 1
    assert "waiting_on" not in todo.get(pool, n)
    assert data["watches"][0]["status"] == "consumed"
    assert counters["fired_unconsumed"] == 0
    assert pool["log"][-1]["verb"] == "watch_wake" and pool["log"][-1]["n"] == n


# ---------------------------------------------------------------------------
# 2026-09-09 R2（P5）findings 的回歸測試
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# `awaiting_approval` 的 gate pointer（2026-09-10）
# ---------------------------------------------------------------------------


def _gated_pool(*, gate_resolved: bool, pointer: str) -> tuple[dict, int, int]:
    """一張停在 awaiting_approval 的工單 ＋ 它在等的 pq2 編號。"""

    pool = _pool_with(
        {"type": "decision_review", "ref_id": "dc_x", "title": "工單"},
        {"type": "manual", "ref_id": "m_gate", "title": "它在等的 gate"},
    )
    work = next(i for i in todo.active_items(pool) if i["ref_id"] == "dc_x")
    gate = next(i for i in todo.active_items(pool) if i["ref_id"] == "m_gate")
    work["dispatch_ref"] = "wo_x"
    work["dispatch_status"] = "awaiting_approval"
    if pointer == "structured":
        todo.set_awaiting_gate(pool, work["n"], gate["n"])
    elif pointer == "legacy":
        work["dispatch_receipt"] = f"action:ra_abc;manual_todo:{gate['n']}"
    if gate_resolved:
        todo.resolve(pool, gate["n"], "go", reason="核准",
                     receipt="authority:registry;ref:test_gate")
    return pool, work["n"], gate["n"]


def test_gate_resolved_work_order_is_separated_from_really_waiting_on_you() -> None:
    """上游 gate 已 resolve ＝ 已經沒在等你了，不能和「真的在等你核准」同一句。

    事發（2026-09-10）：[311]／[411] 的 gate 在 08-31／09-02 就已核准並寫入
    authority，工單卻停在 awaiting_approval 十天沒有任何東西會動它。`awaiting_approval`
    同時承載兩種語意，呈現層被迫二選一而兩邊都錯（L12）。
    """

    pool, work_n, gate_n = _gated_pool(gate_resolved=True, pointer="structured")
    (row,) = todo.gated_items(pool)
    assert row["n"] == work_n
    assert row["state"] == "gate_resolved"
    assert row["gate_n"] == gate_n
    assert row["gate_resolution"] == "go"

    still, _, _ = _gated_pool(gate_resolved=False, pointer="structured")
    assert todo.gated_items(still)[0]["state"] == "waiting"


def test_work_order_without_a_pointer_is_reported_not_silently_accepted() -> None:
    """說不出在等哪個編號 ＝ 沒有到期，也沒有 consumer（INV-2／INV-4）。

    ⚠ 這一條刻意不放寬：缺 pointer 不擋寫入（既有工單沒有這個欄位），但一定要被報出來。
    安靜接受等於讓工單合法地永遠掛著，那正是這次要修的東西。
    """

    pool, _, _ = _gated_pool(gate_resolved=False, pointer="none")
    (row,) = todo.gated_items(pool)
    assert row["state"] == "no_pointer"
    assert row["gate_n"] is None


def test_legacy_receipt_pointer_is_read_but_marked_as_such() -> None:
    """既有資料的 pointer 寫在 receipt 自由字串裡——讀得到，但來源要誠實標記。"""

    pool, _, gate_n = _gated_pool(gate_resolved=True, pointer="legacy")
    (row,) = todo.gated_items(pool)
    assert row["gate_n"] == gate_n
    assert row["gate_origin"] == "legacy_receipt"
    assert row["state"] == "gate_resolved"

    structured, _, _ = _gated_pool(gate_resolved=True, pointer="structured")
    assert todo.gated_items(structured)[0]["gate_origin"] == "structured"


def test_pointer_must_resolve_and_cannot_point_at_itself() -> None:
    """pointer 指不到的編號要當場拋——一個解析不到的 pointer 比沒有更糟。"""

    pool, work_n, _ = _gated_pool(gate_resolved=False, pointer="none")
    with pytest.raises(todo.TodoError):
        todo.set_awaiting_gate(pool, work_n, 99999)
    with pytest.raises(todo.TodoError):
        todo.set_awaiting_gate(pool, work_n, work_n)


def test_leaving_awaiting_approval_clears_the_pointer() -> None:
    """離開 awaiting_approval 之後 pointer 就過期了——留著會讓下次判斷讀到舊事實。"""

    pool, work_n, gate_n = _gated_pool(gate_resolved=False, pointer="structured")
    item = todo.get(pool, work_n)
    assert item[todo.AWAITING_GATE_KEY]["n"] == gate_n

    item["dispatch_status"] = "researching"
    item.pop(todo.AWAITING_GATE_KEY, None)
    assert todo.gated_items(pool) == []


# ---------------------------------------------------------------------------
# complete-ra 自己記帳（2026-09-11）——孤兒不可能產生，而不是事後看得見
# ---------------------------------------------------------------------------

def _lead_ctx(monkeypatch, tmp_path, leads_payload, *, declared=None):
    """組一個最小 leads store，回傳 (path, store)。"""
    import json

    from engine_b import leads as L

    store = L.empty_store()
    store["leads"] = leads_payload
    path = tmp_path / "pending_leads.json"
    L.save(store, path)
    from engine_b import todo as T

    monkeypatch.setattr(T, "_declared_focus_for_action", lambda _a: declared)
    return path


def _lead(lead_id, status, *, digest=None, focus=None, action="ra_x"):
    refs = {"research_action_id": action}
    if digest:
        refs["action_digest"] = digest
    if focus:
        refs["focus_company_id"] = focus
    return {"lead_id": lead_id, "status": status, "title": "t", "refs": refs,
            "url": f"https://x.io/{lead_id}", "source": "edgar:X", "triage": None,
            "entities": {"company_ids": [], "tickers": []}, "themes": {},
            "first_seen": "2026-09-01T00:00:00+00:00"}


def test_complete_ra_advances_action_prepared_leads_instead_of_demanding_it(
        monkeypatch, tmp_path) -> None:
    """事發（2026-09-11）：三條 lead 卡在 action_prepared 十天，它們等的 pq2 早已結案。

    到這一步 digest、state、document／report receipt 都驗過了——RA 落地是既成事實，
    把它記進 lead 是**簿記**不是判斷。先前把簿記外包給呼叫端，於是漏掉就產生孤兒。
    """
    import json

    from engine_b import leads as L
    from engine_b import todo as T

    digest = "a" * 64
    payload = {"l1": _lead("l1", "action_prepared"), "l2": _lead("l2", "action_prepared")}
    path = _lead_ctx(monkeypatch, tmp_path, payload, declared="co:google")

    ctx = T._lead_context_for_action("ra_x", action_digest=digest, leads_path=path)
    assert ctx["company_id"] == "co:google"

    after = L.load(path)["leads"]
    assert {v["status"] for v in after.values()} == {"applied"}
    assert all(v["refs"]["action_digest"] == digest for v in after.values())
    assert all(v["refs"]["focus_company_id"] == "co:google" for v in after.values())


def test_complete_ra_refuses_to_advance_from_a_terminal_or_early_state(
        monkeypatch, tmp_path) -> None:
    """`parked` 是「我們決定不要」，`triaged_go` 是「還沒備妥」——兩者都不是簿記漏掉。"""
    from engine_b import todo as T

    for bad in ("parked", "triaged_go", "researching"):
        path = _lead_ctx(monkeypatch, tmp_path / bad, {"l1": _lead("l1", bad)},
                         declared="co:google")
        try:
            T._lead_context_for_action("ra_x", action_digest="b" * 64, leads_path=path)
        except T.TodoError as exc:
            assert "狀態不合法" in str(exc)
        else:
            raise AssertionError(f"{bad} 不該被自動推進")


def test_complete_ra_does_not_pick_a_focus_when_two_authorities_disagree(
        monkeypatch, tmp_path) -> None:
    """lead 與 RA 自報的 focus 打架時不得靜默挑一個（L15：authority laundering）。"""
    from engine_b import todo as T

    path = _lead_ctx(monkeypatch, tmp_path,
                     {"l1": _lead("l1", "applied", digest="c" * 64, focus="co:a")},
                     declared="co:b")
    try:
        T._lead_context_for_action("ra_x", action_digest="c" * 64, leads_path=path)
    except T.TodoError as exc:
        assert "不符" in str(exc) and "不猜" in str(exc)
    else:
        raise AssertionError("兩個 authority 矛盾時必須拒絕")


def test_complete_ra_never_overwrites_a_conflicting_digest(monkeypatch, tmp_path) -> None:
    """帶著「別的 digest」的 lead 是綁在另一個已核准版本上——衝突，不是漏記。

    第一版我寫成「digest 不符就補成正確的」，被既有測試
    `test_ra_lead_context_requires_matching_digest` 當場打臉。蓋過去就是讓引用去尋找
    能通過的權威（L15）。規則是**只補空白**。
    """
    from engine_b import todo as T

    path = _lead_ctx(monkeypatch, tmp_path,
                     {"l1": _lead("l1", "applied", digest="9" * 64, focus="co:a")},
                     declared="co:a")
    try:
        T._lead_context_for_action("ra_x", action_digest="c" * 64, leads_path=path)
    except T.TodoError as exc:
        assert "不覆寫" in str(exc)
    else:
        raise AssertionError("digest 衝突必須拒絕，不得覆寫")
