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


def _decision_row(ref_id: str = "dc_1") -> dict:
    return {"type": "decision_review", "ref_id": ref_id, "title": "REVIEW — co:x"}


def test_source_that_stops_producing_a_row_marks_it_as_done_candidate() -> None:
    """來源成功執行但不再產出該項＝很可能已完成，移出決策注意力。

    事發（2026-08-05）：[85] 與 [84] 在同一個 session 內先後變成殘留項。sync 只
    走訪 incoming，而 collect_from_decisions 會跳過不需要人看（U7 起是 `MONITOR`，
    先前寫作 NO ACTION）的 decision，所以
    項目一旦「做完」，它的來源 row 就消失、再也沒有任何分支碰得到它——項目越
    接近完成，池子越無法反映它。
    """

    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={"decisions"})
    assert not todo.get(pool, 1).get("source_cleared")

    result = todo.sync(pool, [], healthy_sources={"decisions"})

    assert result["source_cleared"] == 1
    assert todo.get(pool, 1)["source_cleared"]["source_healthy"] is True
    assert any(entry.get("verb") == "source_cleared" for entry in pool["log"])
    # 只是標記，絕不自動結案。
    assert todo.get(pool, 1).get("resolved_at") is None


def test_in_flight_work_order_is_never_marked_source_cleared() -> None:
    """awaiting exact gate 比 collector 缺席更有權威，不得提示使用者 drop。"""
    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={"decisions"})
    item = todo.get(pool, 1)
    item["dispatch_status"] = "awaiting_approval"
    item["dispatch_receipt"] = "observation-proposal:po_1"
    item["source_cleared"] = {
        "at": "2026-08-15T00:00:00+00:00",
        "source_healthy": True,
        "reason": "stale marker",
    }

    result = todo.sync(pool, [], healthy_sources={"decisions"})

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
              healthy_sources={"decisions"})

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

    result = todo.sync(pool, [], healthy_sources={"decisions"})

    assert result["source_cleared"] == 1
    assert todo.get(pool, 1)["source_cleared"]        # decision_review 被標記
    assert not todo.get(pool, 2).get("source_cleared")  # lifecycle 未判定


def test_returning_row_revokes_the_done_candidate_mark() -> None:
    """新證據把 decision 推回 REVIEW 時，標記要撤銷而不是留著誤導。"""

    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={"decisions"})
    todo.sync(pool, [], healthy_sources={"decisions"})
    assert todo.get(pool, 1)["source_cleared"]

    result = todo.sync(pool, [_decision_row()], healthy_sources={"decisions"})

    assert result["source_returned"] == 1
    assert "source_cleared" not in todo.get(pool, 1)
    assert any(entry.get("verb") == "source_returned" for entry in pool["log"])


def test_done_candidates_render_in_their_own_section_with_drop_hint() -> None:
    pool = todo.empty_pool()
    todo.sync(pool, [_decision_row()], healthy_sources={"decisions"})
    todo.sync(pool, [], healthy_sources={"decisions"})

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
    for name, attr in todo.SOURCE_COLLECTORS:
        if name == "decisions":
            continue
        monkeypatch.setattr(todo, attr, lambda: [])

    def boom():
        raise RuntimeError("Neo4j unreachable")

    monkeypatch.setattr(todo, "_collect_decision_rows", boom)

    collected = todo.collect_all_with_health()

    assert collected.rows == [], "所有 collector 都被 patch 成空，不得有真實資料漏進來"
    assert "decisions" not in collected.healthy
    expected_healthy = {name for name, _ in todo.SOURCE_COLLECTORS} - {"decisions"}
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
        lambda action_id, action_digest, leads_path: {
            "company_id": "co:axt",
            "title": "AXT／Casela 2027 InP 長約",
        },
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
        # lead title 必須傳到 Decision handoff：它會成為 cohort 的 atomic_claim。
        "thesis": "AXT／Casela 2027 InP 長約",
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
    # title 一併回傳：它會成為 cohort 的 atomic_claim，讓「當初我們認為這是什麼」
    # 有可回溯紀錄（先前 10/10 個 cohort 的 claim 都是空的）。
    ) == {"company_id": "co:axt", "title": ""}
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


def test_bare_decision_id_rejected_before_work_order_mutation() -> None:
    """ROADMAP 2026-09-02 清項（2026-08-19 [166] 實測）：裸 `pd_*` receipt 曾通過前半段
    驗證、先寫入 work order transition，才被 resolve 端拒絕——pool 與 work order 脫鉤，
    且重試撞 completed->completed 死鎖。修法：格式驗證先於任何副作用。"""
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    store = _WorkOrderStore()
    todo.dispatch_decision_review(pool, 1, store=store, at="2026-07-27T00:00:00+00:00")
    transitions_before = len(store.transitions)

    with pytest.raises(todo.TodoError, match="decision:pd_"):
        todo.checkpoint_decision_review(
            pool, 1, store=store, to_status="completed",
            receipt="pd_new", at="2026-07-27T01:00:00+00:00",
        )

    # work order 完全未被觸碰，pool 項目也還活著——可用正確格式重試。
    assert len(store.transitions) == transitions_before
    assert not pool["items"][0].get("resolved_at")
    result = todo.checkpoint_decision_review(
        pool, 1, store=store, to_status="completed",
        receipt="decision:pd_new", at="2026-07-27T01:00:00+00:00",
    )
    assert result["item"]["resolved_at"]


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
    from briefing import public_view as decision_tools

    # U7：brief 頂層的 `recommended_action` 已改為 `attention`，全域項標題固定寫「複查」。
    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "attention": "REVIEW",
        "reason": "Google Sheet current holdings 無法讀取。",
        "blockers": ["holdings_unavailable"],
        "items": [],
    })

    assert todo.collect_from_decisions() == [{
        "type": "decision_review",
        "ref_id": "global:holdings_unavailable",
        "title": "複查 — Google Sheet current holdings 無法讀取。",
        "hint": "修復全域 authority blocker 後重跑 decision_lab today",
        "source": "decision_lab",
    }]


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


def test_collect_from_decisions_keeps_sheet_only_items_without_cohort(
    monkeypatch,
) -> None:
    from briefing import public_view as decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": "co:nvidia",
                "ticker": "NVDA",
                "attention": "REVIEW",
                "sheet_only": True,
            },
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": "unresolved",
                "ticker": "QQQ",
                "attention": "REVIEW",
                "sheet_only": True,
            },
        ],
    })

    # 標的歸屬跟著 payload 走（L16，2026-09-11）：下游不必 parse `co:xxx：` 標題去猜。
    # `unresolved` 的那一筆刻意只有 ticker——不得把佔位字串當成 company_id 塞下去。
    assert todo.collect_from_decisions() == [
        {
            "type": "sheet_only_holding",
            "ref_id": "sheet:co:nvidia",
            "title": "複查 — co:nvidia",
            "source": "decision_lab",
            "company_id": "co:nvidia",
            "ticker": "NVDA",
        },
        {
            "type": "sheet_only_holding",
            "ref_id": "sheet:ticker:QQQ",
            "title": "複查 — QQQ",
            "source": "decision_lab",
            "ticker": "QQQ",
        },
    ]


def test_collect_from_decisions_uses_company_hint_only_as_display_label(
    monkeypatch,
) -> None:
    from briefing import public_view as decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [{
            "cohort_id": "dc_private",
            "decision_id": "pd_private",
            "company_id": "unresolved",
            "company_id_hint": "co:agility_robotics",
            "ticker": None,
            "attention": "REVIEW",
        }],
    })

    rows = todo.collect_from_decisions()
    assert len(rows) == 1
    row = rows[0]
    assert row["type"] == "decision_review"
    assert row["ref_id"] == "dc_private"
    # 本測試的斷言對象是**顯示標籤**：company_id 為 unresolved 時退回 hint 值。
    # U7 起沒有 weakest_axis 的項目一律寫「複查 — <label>」，不再冠上動作字樣。
    assert row["title"] == "複查 — co:agility_robotics"
    assert row["source"] == "decision_lab"
    # hint 自 2026-08-26 起依該 cohort 有無 research work order 動態決定，
    # 不再是固定字串；其正確性由 test_decision_review_hint_* 負責，這裡只確認存在。
    assert row["hint"]


def test_collect_material_decision_never_derives_waiting_from_system_blockers(
    monkeypatch,
) -> None:
    from briefing import public_view as decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [{
            "cohort_id": "dc_axt",
            "decision_id": "pd_axt",
            "company_id": "co:axt",
            "attention": "REVIEW",
            "evidence_delta": "material",
            "blockers": ["market_stale_since_decision"],
        }],
    })

    row = todo.collect_from_decisions()[0]
    assert "waiting_on" not in row
    assert row["event_link"]["receipt"] == "decision:pd_axt"


def test_collect_marks_pure_system_internal_decision_for_retirement(
    monkeypatch,
) -> None:
    """純 stale context 要交給 sync 留 audit，不可冒充「等事件」。"""

    from briefing import public_view as decision_tools

    monkeypatch.setattr(decision_tools, "get_decision_brief_core", lambda: {
        "action_needed": True,
        "items": [{
            "cohort_id": "dc_meta",
            "decision_id": "pd_meta",
            "company_id": "co:meta",
            "attention": "REVIEW",
            "evidence_delta": "none",
            "blockers": [
                "execution_fx_stale_since_decision",
                "execution_market_stale_since_decision",
                "fx_stale_since_decision",
                "market_stale_since_decision",
            ],
        }],
    })

    row = todo.collect_from_decisions()[0]
    assert row["system_internal_only"] is True
    assert "waiting_on" not in row


def test_sync_retires_existing_pure_system_internal_item_without_new_pq2() -> None:
    pool = todo.empty_pool()
    todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_meta",
        "title": "REVIEW — co:meta",
        "source": "decision_lab",
        "waiting_on": {
            "derived_from_blockers": True,
            "reason": "所有 blocker 都不需要使用者決定",
            "trigger": "市場資料問題",
            "until": None,
        },
    }], healthy_sources={"decisions"})

    result = todo.sync(pool, [{
        "type": "decision_review",
        "ref_id": "dc_meta",
        "title": "REVIEW — co:meta",
        "source": "decision_lab",
        "system_internal_only": True,
    }], healthy_sources={"decisions"})

    assert result["system_internal_retired"] == 1
    assert todo.active_items(pool) == []
    assert pool["items"][0]["resolution"] == "system_internal"
    assert pool["log"][-1]["verb"] == "system_internal_retired"

    fresh = todo.empty_pool()
    result = todo.sync(fresh, [{
        "type": "decision_review",
        "ref_id": "dc_meta",
        "title": "REVIEW — co:meta",
        "source": "decision_lab",
        "system_internal_only": True,
    }], healthy_sources={"decisions"})
    assert result["added"] == 0
    assert todo.active_items(fresh) == []


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
    assert "Decision handoff：co:meta" in rows[0]["hint"]
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


def test_same_decision_receipt_does_not_rewake_item_every_sync() -> None:
    """2026-08-11 迴歸：綁 event_type 後等待條件永遠黏不住。

    `reactivation_event` 先前只寫不讀，於是只要 collector 還回報同一筆 material
    delta，使用者每次設回等待、下一輪 sync 就被打回決策佇列——把「永遠不會醒」
    換成「永遠不睡」。同一筆 receipt 只該喚醒一次；換新 decision 仍要喚醒。
    """
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})

    def _row(receipt: str) -> dict:
        return {
            "type": "decision_review",
            "ref_id": "dc_1",
            "title": "REVIEW — co:agility_robotics",
            "event_link": {
                "type": "decision_evidence_delta",
                "value": "material",
                "receipt": receipt,
            },
        }

    def _wait(at: str) -> None:
        todo.resolve(
            pool, 1, "pending",
            trigger="等 S-4 公開",
            event_type="decision_evidence_delta",
            at=at,
        )

    _wait("2026-08-01T00:00:00+00:00")
    first = todo.sync(pool, [_row("decision:pd_a")], at="2026-08-02T00:00:00+00:00")
    assert first["reactivated"] == 1

    # 看過後設回等待；同一筆 receipt 再 sync 不得重新喚醒
    _wait("2026-08-03T00:00:00+00:00")
    again = todo.sync(pool, [_row("decision:pd_a")], at="2026-08-04T00:00:00+00:00")
    assert again["reactivated"] == 0, "同一筆 decision receipt 不應重複喚醒"
    assert "waiting_on" in todo.get(pool, 1)

    # 換一筆新 decision（新 receipt）仍必須喚醒
    fresh = todo.sync(pool, [_row("decision:pd_b")], at="2026-08-05T00:00:00+00:00")
    assert fresh["reactivated"] == 1
    assert "waiting_on" not in todo.get(pool, 1)


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


def test_decision_review_hint_distinguishes_dispatch_from_reassess() -> None:
    """`REVIEW` 有兩種成因，hint 必須說對是哪一種。

    事發（2026-08-26，本機 Codex 與 Claude Code 各自獨立撞到）：舊 hint 一律寫
    「核准 bounded gap research」，把「coverage 已清空、REVIEW 來自凍結 context
    過期」誤呈現成「存在可 dispatch 的研究缺口」。使用者照著下 `go`：
    `dispatch` 拒絕（沒有 work order），`resolve --verb go` 也拒絕
    （decision_review 不得 bare go），看起來像死結——正解其實是 `reassess`。

    這是 L12：一個表示承載兩種語意，下游被迫二選一，而兩邊都是錯的。
    """

    from engine_b.todo import _decision_review_hint

    with_gap = _decision_review_hint("dc_has_work_order", frozenset({"dc_has_work_order"}))
    without_gap = _decision_review_hint(
        "dc_no_work_order", frozenset({"dc_has_work_order"}), ["holdings_stale"]
    )

    assert "dispatch" in with_gap and "pq1" in with_gap
    # 沒有 work order 且只剩 context 過期類 blocker 時，指向 reassess。
    assert "reassess" in without_gap
    assert "不是 dispatch" in without_gap
    assert with_gap != without_gap


def test_hint_names_substantive_blockers_when_reassess_will_not_help() -> None:
    """只分 dispatch／reassess 兩類不夠——實測 [223] co:lumentum 兩者皆不成立。

    它沒有 work order（不是 dispatch），但 reassess 跑過之後仍是 REVIEW，
    因為 blocker 是 `financial_resilience_corroboration_incomplete`——要補證據，
    不是重跑評估。hint 只寫「請跑 reassess」會讓人跑第二次然後再問一次
    「那我到底要下什麼」。
    """

    from engine_b.todo import _decision_review_hint

    hint = _decision_review_hint(
        "dc_x",
        frozenset(),
        ["financial_resilience_corroboration_incomplete", "holdings_stale"],
    )

    assert "financial_resilience_corroboration_incomplete" in hint
    # context 過期類的不算實質 blocker，不該混進研究範圍。
    assert "holdings_stale" not in hint
    # 2026-08-30 使用者定案：介面只有一個 go。無 work order 的項目 go＝
    # dispatch 的 assessment_gap 路徑（reassess 後排入 pq1），hint 必須說得出
    # 這條路，不得再寫「go 不成立」。
    assert "go（大項）" in hint
    assert "assessment_gap" in hint
    assert "go 不成立" not in hint


def test_dispatchable_cohorts_fails_soft_without_store() -> None:
    """讀不到 store 只降級 hint，不得阻斷 sync，也不得謊報某條路可走。"""

    from engine_b.todo import _dispatchable_cohorts

    # 沒有 dc_ 前綴就不查 store，直接空集合。
    assert _dispatchable_cohorts([{"cohort_id": "sheet:co:x"}]) == frozenset()
    assert _dispatchable_cohorts([]) == frozenset()


def test_decision_review_hint_is_rendered_not_just_stored() -> None:
    """hint 存了但不顯示等於沒有——使用者只看得到區段標題然後下錯 verb。"""

    from engine_b.todo import _item_line

    line = _item_line({
        "n": 220,
        "title": "REVIEW — co:axt",
        "type": "decision_review",
        "hint": "coverage 已無 blocker……請跑 reassess",
    })
    assert "reassess" in line


class _FakeStore:
    """只提供 advance_decision_review 用到的窄 surface。"""

    def __init__(self, *, work_order=None, intent="paper"):
        self._work_order = work_order
        self._intent = intent
        self.closed = False

    def latest_research_work_order(self, cohort_id):
        return self._work_order

    def latest_decision_for_cohort(self, cohort_id):
        return {"payload": {"request": {"execution_intent": self._intent}}}

    def close(self):
        self.closed = True


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


def test_go_dispatches_when_work_order_exists(monkeypatch) -> None:
    """A 類：原行為不變。"""

    from engine_b import todo

    pool = _decision_pool()
    store = _FakeStore(work_order={"work_order_id": "wo_1", "status": "proposed",
                                   "decision_id": "pd_base"})
    monkeypatch.setattr(todo, "dispatch_decision_review",
                        lambda p, n, **kw: {"item": todo.get(p, n)})

    out = todo.advance_decision_review(pool, 1, store=store)
    assert out["outcome"] == "dispatched"


def test_go_reassesses_when_only_context_aged(monkeypatch) -> None:
    """B 類：先前會被拒絕，現在自動 reassess。

    實測 2026-08-26：9 個 REVIEW 有 3 個屬此類（aeva／AAOI／SIVE），
    使用者下 go 只會拿到「不得 bare go」。
    """

    from engine_b import todo

    pool = _decision_pool()
    store = _FakeStore(work_order=None, intent="paper")
    seen = {}

    def fake_reassess(_store, _provider, cohort_id, *, execution_intent):
        seen["intent"] = execution_intent
        return {"decision_id": "pd_new"}

    monkeypatch.setattr("decision_lab.workflow.reassess", fake_reassess)
    monkeypatch.setattr("engine_d_runtime.bootstrap.build_default_runtime_provider",
                        lambda: object())
    ref = todo.get(pool, 1)["ref_id"]
    # 2026-09-09 R2 起 advance 先確認 brief 讀得到且列了這個 cohort（fail closed），再判殘餘 blocker
    monkeypatch.setattr(todo, "_load_brief_items", lambda: [{"cohort_id": ref, "blockers": []}])
    monkeypatch.setattr(todo, "_substantive_blockers", lambda cohort_id, **kw: [])

    out = todo.advance_decision_review(pool, 1, store=store)
    assert out["outcome"] == "reassessed"
    # intent 必須沿用該 cohort 上一筆——套錯會讓 research_status 假性退化。
    assert seen["intent"] == "paper"


def test_go_queues_assessment_gap_when_blockers_remain(monkeypatch) -> None:
    """C 類：assessment 層缺口沒有 Decision Store work order，仍要能開工。"""

    from engine_b import todo

    pool = _decision_pool()
    store = _FakeStore(work_order=None, intent="research")
    monkeypatch.setattr("decision_lab.workflow.reassess",
                        lambda *a, **k: {"decision_id": "pd_new"})
    monkeypatch.setattr("engine_d_runtime.bootstrap.build_default_runtime_provider",
                        lambda: object())
    ref = todo.get(pool, 1)["ref_id"]
    monkeypatch.setattr(todo, "_load_brief_items",
                        lambda: [{"cohort_id": ref, "blockers": ["financial_resilience_corroboration_incomplete"]}])
    monkeypatch.setattr(todo, "_substantive_blockers",
                        lambda cohort_id, **kw: ["financial_resilience_corroboration_incomplete"])

    out = todo.advance_decision_review(pool, 1, store=store)
    assert out["outcome"] == "queued_assessment_gap"
    assert out["scope"] == ["financial_resilience_corroboration_incomplete"]
    item = todo.get(pool, 1)
    assert item["dispatch_ref"].startswith(todo.ASSESSMENT_GAP_PREFIX)
    assert item["dispatch_status"] == "queued"


def test_go_is_noop_when_already_in_flight() -> None:
    """已在 pq1 的不重複派工——否則同一份研究會被排兩次。"""

    from engine_b import todo

    pool = _decision_pool()
    todo.get(pool, 1)["dispatch_status"] = "researching"
    out = todo.advance_decision_review(pool, 1, store=_FakeStore())
    assert out["outcome"] == "already_in_flight"


def test_work_checkpoint_accepts_assessment_gap_ref() -> None:
    """assessment-gap dispatch 沒有 work order 可 transition，但仍必須留 receipt。"""

    from engine_b import todo

    pool = _decision_pool()
    item = todo.get(pool, 1)
    item["dispatch_status"] = "queued"
    item["dispatch_ref"] = f"{todo.ASSESSMENT_GAP_PREFIX}dc_abc"

    class _Store:
        def transition_research_work_order(self, **kw):  # pragma: no cover
            raise AssertionError("assessment-gap 不該去動 Decision Store work order")

    out = todo.checkpoint_decision_review(
        pool, 1, to_status="parked", receipt="research_packet:notes.md", store=_Store()
    )
    assert out["work_order"] is None
    # terminal checkpoint 仍照常 resolve pq2 編號並留下 receipt。
    assert pool["log"][-1]["receipt"] == "research_packet:notes.md"


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
        [{"type": "decision_review"}, {"type": "ra_admission"}]
    )

    assert rows[0]["go_authorizes"].startswith("bounded research")
    assert "入圖" in rows[0]["go_excludes"]
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


class _StoreStub:
    def __init__(self, work_orders: dict[str, object]):
        self._wo = work_orders

    def latest_research_work_order(self, cohort_id: str):
        return self._wo.get(cohort_id)


def test_reassess_only_items_requires_all_three_conditions() -> None:
    pool = _pool_with(
        {"type": "decision_review", "ref_id": "dc_stale", "title": "A"},       # 只因 context 過期
        {"type": "decision_review", "ref_id": "dc_has_wo", "title": "B"},      # 有 work order → dispatch
        {"type": "decision_review", "ref_id": "dc_user", "title": "C"},        # 有需人決定的 blocker
        {"type": "decision_review", "ref_id": "dc_unlisted", "title": "D"},    # brief 沒列 → 不判
        {"type": "manual", "ref_id": "m1", "title": "E"},
    )
    by_ref = {it["ref_id"]: it for it in todo.active_items(pool)}
    by_ref["dc_has_wo"]["dispatch_status"] = None
    # blocker 代碼用真的 registry 值（config/decision_blockers.json 的 resolution_mode）：
    # market_stale_since_decision＝system_internal；execution_fx_missing＝awaiting_external；
    # financial_resilience_corroboration_incomplete＝user_decision。
    brief = [
        {"cohort_id": "dc_stale", "blockers": ["market_stale_since_decision", "holdings_unconfirmed"]},
        {"cohort_id": "dc_has_wo", "blockers": ["market_stale_since_decision"]},
        {"cohort_id": "dc_user", "blockers": ["market_stale_since_decision",
                                             "financial_resilience_corroboration_incomplete"]},
        {"cohort_id": "dc_waiting", "blockers": ["market_stale_since_decision", "execution_fx_missing"]},
        {"cohort_id": "dc_empty", "blockers": []},
    ]
    todo.sync(pool, [
        {"type": "decision_review", "ref_id": "dc_waiting", "title": "F"},   # 帶 awaiting_external → 不算
        {"type": "decision_review", "ref_id": "dc_empty", "title": "G"},     # 零 blocker 的 REVIEW → 不算
    ])
    store = _StoreStub({"dc_has_wo": {"work_order_id": "wo_1"}})

    got = todo.reassess_only_items(pool, store, brief_items=brief)
    assert [it["ref_id"] for it in got] == ["dc_stale"]

    # in-flight 或已有 terminal receipt 的不算
    by_ref["dc_stale"]["dispatch_status"] = "queued"
    assert todo.reassess_only_items(pool, store, brief_items=brief) == []
    by_ref["dc_stale"]["dispatch_status"] = "completed"
    assert todo.reassess_only_items(pool, store, brief_items=brief) == []

    # brief 讀不到 → 一個都不判（不是全部都算）
    by_ref["dc_stale"]["dispatch_status"] = None
    assert todo.reassess_only_items(pool, store, brief_items=[]) == []


def test_reassess_stale_closes_only_when_new_decision_is_not_review(monkeypatch) -> None:
    pool = _pool_with(
        {"type": "decision_review", "ref_id": "dc_a", "title": "A"},
        {"type": "decision_review", "ref_id": "dc_b", "title": "B"},
        {"type": "decision_review", "ref_id": "dc_c", "title": "C"},
    )
    brief = [{"cohort_id": ref, "blockers": ["market_stale_since_decision"]} for ref in ("dc_a", "dc_b", "dc_c")]
    store = _StoreStub({})
    monkeypatch.setattr(todo, "_prior_execution_intent", lambda s, c: "paper")

    def fake_reassess(s, provider, cohort_id, *, execution_intent=None, **kw):
        if cohort_id == "dc_c":
            raise RuntimeError("provider 壞了")
        attention = "REVIEW" if cohort_id == "dc_b" else "MONITOR"
        return {"decision_id": f"pd_{cohort_id}", "action_card": {"attention": attention}}

    import decision_lab.workflow as wf
    monkeypatch.setattr(wf, "reassess", fake_reassess)

    dry = todo.reassess_stale(pool, store, None, dry_run=True, brief_items=brief)
    assert dry["dry_run"] is True and sorted(dry["candidates"]) == [1, 2, 3]
    assert len(todo.active_items(pool)) == 3            # dry-run 一個都不動

    out = todo.reassess_stale(pool, store, object(), at="2026-09-09T00:00:00+00:00", brief_items=brief)
    assert [row["n"] for row in out["closed"]] == [1]
    assert [row["n"] for row in out["still_review"]] == [2]
    assert [row["n"] for row in out["failed"]] == [3]
    remaining = {it["ref_id"] for it in todo.active_items(pool)}
    assert remaining == {"dc_b", "dc_c"}
    closed = next(it for it in pool["items"] if it["ref_id"] == "dc_a")
    assert closed["resolution"] == "reassessed" and closed["resolved_at"]
    verbs = [e["verb"] for e in pool["log"] if e["n"] == 1]
    assert verbs[-2:] == ["pq1_reassessed", "reassessed_closed"]
    assert pool["log"][-1]["receipt"].startswith("decision:pd_") or any(
        e["receipt"] == "decision:pd_dc_a" for e in pool["log"]
    )



# ---------------------------------------------------------------------------
# 2026-09-09 R2（P5）findings 的回歸測試
# ---------------------------------------------------------------------------

def test_load_brief_items_returns_none_when_brief_service_degrades(monkeypatch) -> None:
    """brief 服務把失敗吞成 status=unavailable 而不拋——讀不到不得變成空清單。"""
    import briefing.public_view as pv

    monkeypatch.setattr(pv, "get_decision_brief_core", lambda **kw: {"status": "unavailable", "as_of": "x"})
    assert todo._load_brief_items() is None
    monkeypatch.setattr(pv, "get_decision_brief_core", lambda **kw: {"status": "error", "as_of": "x"})
    assert todo._load_brief_items() is None
    monkeypatch.setattr(pv, "get_decision_brief_core", lambda **kw: {"status": "ok", "items": []})
    assert todo._load_brief_items() == []                      # 真的沒東西才是空
    monkeypatch.setattr(pv, "get_decision_brief_core", lambda **kw: {"status": "ok", "items": [{"cohort_id": "dc_1"}]})
    assert todo._load_brief_items() == [{"cohort_id": "dc_1"}]


def test_advance_decision_review_fails_closed_when_brief_is_unreadable(monkeypatch) -> None:
    """reassess 後 brief 讀不到 → 不得下「僅 context 老化已解決」的結論，也不排隊；留收據等下一輪。"""
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_x", "title": "X"})
    n = todo.active_items(pool)[0]["n"]

    class _Store:
        def latest_research_work_order(self, cohort_id):
            return None

    import decision_lab.workflow as wf
    import engine_d_runtime.bootstrap as bs

    monkeypatch.setattr(wf, "reassess", lambda s, p, c, *, execution_intent=None, **kw: {"decision_id": "pd_new", "action_card": {"attention": "REVIEW"}})
    monkeypatch.setattr(bs, "build_default_runtime_provider", lambda: object())
    monkeypatch.setattr(todo, "_prior_execution_intent", lambda s, c: "paper")
    monkeypatch.setattr(todo, "_load_brief_items", lambda: None)

    out = todo.advance_decision_review(pool, n, store=_Store(), at="2026-09-09T00:00:00+00:00")
    assert out["outcome"] == "reassessed_blockers_unknown"
    item = todo.get(pool, n)
    assert item.get("dispatch_status") is None                 # 沒排隊（不知道 scope）
    assert item.get("resolved_at") is None                     # 沒關掉
    assert "殘餘 blocker 未判定" in pool["log"][-1]["reason"]


def test_reassess_stale_has_a_cooldown_so_it_cannot_append_daily() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_cool", "title": "C"})
    n = todo.active_items(pool)[0]["n"]
    brief = [{"cohort_id": "dc_cool", "blockers": ["market_stale_since_decision"]}]
    store = _StoreStub({})
    assert [it["n"] for it in todo.reassess_only_items(pool, store, brief_items=brief)] == [n]
    pool["log"].append({"at": "2026-09-09T00:00:00+00:00", "n": n, "type": "decision_review", "ref_id": "dc_cool",
                        "verb": "pq1_reassessed", "reason": "x", "receipt": "decision:pd_1"})
    from datetime import datetime, timezone
    assert todo._recently_reassessed(pool, n, now=datetime(2026, 9, 10, tzinfo=timezone.utc))
    assert not todo._recently_reassessed(pool, n, now=datetime(2026, 9, 20, tzinfo=timezone.utc))


def test_assessment_gap_jobs_lists_pool_only_work_that_drain_would_otherwise_miss() -> None:
    pool = _pool_with(
        {"type": "decision_review", "ref_id": "dc_gap", "title": "G"},
        {"type": "decision_review", "ref_id": "dc_wo", "title": "W"},
        {"type": "decision_review", "ref_id": "dc_idle", "title": "I"},
    )
    by = {it["ref_id"]: it for it in todo.active_items(pool)}
    by["dc_gap"].update({"dispatch_status": "queued", "dispatch_ref": f"{todo.ASSESSMENT_GAP_PREFIX}dc_gap",
                         "dispatch_scope": ["financial_resilience_corroboration_incomplete"]})
    by["dc_wo"].update({"dispatch_status": "queued", "dispatch_ref": "wo_123"})     # 真 work order：drain 另有來源
    jobs = todo.assessment_gap_jobs(pool)
    assert [j["cohort_id"] for j in jobs] == ["dc_gap"]
    assert jobs[0]["scope"] == ["financial_resilience_corroboration_incomplete"]


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


def test_decision_review_hint_names_material_evidence_before_the_other_causes() -> None:
    """`REVIEW` 有第三種成因：證據有實質變動（evidence_delta=material）。

    事發（2026-09-11 實測 [512] co:iqe）：它的 blocker 全部不需要使用者決定，於是 hint
    落到「請跑 reassess」那一句。但 `reassess-stale` 不收它（段 2 的判準是
    `_only_system_internal_blockers`，比「無 user_decision」嚴得多），`standing-go` 又把它
    推回給 `reassess-stale`——使用者照著做只會白跑兩次。

    再往下追，它留在佇列的真正原因是 material evidence delta：collect 端刻意讓它蓋過
    `waiting_on` 推導與 system_internal 退休路徑。所以這一句必須**排在最前面**，
    它回答的是「為什麼這一筆在你眼前」，其餘兩種回答的是「為什麼自動化不碰它」。
    """

    from engine_b.todo import _decision_review_hint

    execution_only = [
        "execution_fx_missing", "execution_intent_research_only",
        "execution_market_stale_since_decision", "holdings_unconfirmed",
        "live_context_not_ready", "market_stale_since_decision",
    ]
    material = _decision_review_hint("dc_x", frozenset(), execution_only, material_event=True)
    assert "evidence_delta" in material and "missing_data" in material
    # 不得再叫人去跑那兩支不收它的東西
    assert "reassess-stale 與 standing-go 都不會自動處理" in material

    # 同一組 blocker、沒有 material 時，要說的是「在等世界」而不是「請跑 reassess」——
    # execution_fx_missing 是 awaiting_external，段 2 也不收它。
    waiting = _decision_review_hint("dc_x", frozenset(), execution_only, material_event=False)
    assert "execution_fx_missing" in waiting and "等世界" in waiting
    assert waiting != material


def test_decision_review_hint_fails_closed_when_blockers_are_unreadable() -> None:
    """讀不到 blocker 時不得落進任何一句有指示性的話——「查不到了」不是合法 lifecycle（INV-3）。"""

    from engine_b.todo import _decision_review_hint

    hint = _decision_review_hint("dc_x", frozenset(), [])
    assert "讀不到" in hint
    assert "reassess" not in hint


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
