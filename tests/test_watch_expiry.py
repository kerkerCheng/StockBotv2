"""到期處置（Phase 1 Step 1.7；A3、INV-2「到期是重問不是丟」、定案 #3／#4）。

守的機制：
- 語意型／假設型到期 → 恰好一個 `watch_decision`（重跑 sync 不重鑄；到期當天收集時 watch 還是 active 也照日期認，
  標記前後 ref_id 相同；續等後再到期是新事件、新編號）。
- 三個動詞：`pending --until` 續等（watch 回 active、歷史附加、編號結案 `renewed`、**不掛 waiting_on**）；
  bare `pending`／`--trigger` 拒收；`go` 要指得回研究結果（lead／report／watch 都查得到）；`drop` 記處置。
- 批次語法：bare go、bare pending 對這一型必失敗，drop 可用。
- pq2 型到期 → 指向的編號翻回球在你；追源型 → lead 轉終局 `watch_expired`＋計數；讀圖型 → 只記處置。
- 常規授權永不碰這一型。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from engine_b import event_watch as ew
from engine_b import leads
from engine_b import todo

SIVERS = "co:sivers_semiconductors"
CONDITION = "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產"
PAST = (date.today() - timedelta(days=3)).isoformat()
FUTURE = (date.today() + timedelta(days=120)).isoformat()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """`todo.sync` 內含 thesis 反證對帳（讀真的 lifecycle，會把指向非現行 memo 的測試 watch 收掉）與
    watch 比對（讀真的 leads，可能叫醒測試 watch）——兩者都隔離，否則測試會因錯的理由通過。"""
    monkeypatch.setattr(todo, "_reconcile_disproof", lambda: None)
    real_load = leads.load
    monkeypatch.setattr(leads, "load", lambda path=None: real_load(path) if path else {"leads": {}})


def _semantic(data, *, expires=PAST):
    watch = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/x_v1_lane_memo.md#1",
                         source_ref="thesis:thesis/x_v1_lane_memo.md#1", expires=FUTURE, entities=[SIVERS],
                         condition=CONDITION, check_frequency="每季財報後", action_48h="重讀 thesis 並決定 revise")
    watch["expires"] = expires   # 測試 fixture：直接給過去的到期日（真實資料不造假，見 plan §0.3 #10）
    return watch


def _pool():
    return {"items": [], "log": [], "next_n": 1}


def _sync(pool):
    return todo.sync(pool, todo._collect_watch_expiry_rows())


def _open(pool, item_type="watch_decision"):
    return [i for i in pool["items"] if i["type"] == item_type and not i.get("resolved_at")]


@pytest.fixture
def expired_semantic():
    data = ew.load_watches()
    watch = _semantic(data)
    ew.mark_expired(data)
    ew.save_watches(data)
    return watch["watch_id"]


# ---------------------------------------------------------------------------
# 收集：恰好一個編號
# ---------------------------------------------------------------------------

def test_expired_semantic_watch_mints_exactly_one_decision_and_resync_does_not_remint(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1
    item = items[0]
    assert item["ref_id"].startswith(expired_semantic + "@")
    assert CONDITION[:20] in item["title"] and "thesis:thesis/x_v1_lane_memo.md#1" in item["title"], \
        "標題要寫出條件與來源，不得只寫 co:* 或 watch_id"
    assert "--verb pending --until" in item["hint"], "續等要給真的能跑的完整命令"


def test_expiry_day_row_before_marking_keeps_the_same_ref_id() -> None:
    data = ew.load_watches()
    watch = _semantic(data)
    ew.save_watches(data)
    assert watch["status"] == "active"
    pool = _pool()
    _sync(pool)                                   # 到期當天：還沒被 check_watches 標 expired
    before = _open(pool)
    assert len(before) == 1
    data = ew.load_watches()
    ew.mark_expired(data)
    ew.save_watches(data)
    _sync(pool)
    after = _open(pool)
    assert len(after) == 1 and after[0]["n"] == before[0]["n"], "標記前後不得換 key 重鑄"


def test_hypothesis_watch_expiry_also_mints_a_decision() -> None:
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="fact_verification", hypothesis_ref="hyp_1", expires=PAST,
                         entities=[SIVERS], fact="客戶端會具名第二家供應商")
    ew.mark_expired(data)
    ew.save_watches(data)
    rows = todo._collect_watch_expiry_rows()
    assert [r["ref_id"] for r in rows] == [f"{watch['watch_id']}@{PAST}"]
    assert "假設 watch 到期" in rows[0]["title"] and "hyp_1" in rows[0]["title"]


def test_other_expiry_classes_do_not_mint_decisions() -> None:
    data = ew.load_watches()
    ew.add_watch(data, kind="related_entity_signal", wake_lead="lead_x", expires=PAST, entities=[SIVERS])
    ew.add_watch(data, kind="entity_filing_signal", wake_reading="tech:cw_dfb_laser", expires=PAST,
                 entities=["co:nvidia"])
    ew.add_watch(data, kind="date", wake_pq2=7, until=PAST, expires=PAST)
    ew.mark_expired(data)
    ew.save_watches(data)
    assert todo._collect_watch_expiry_rows() == []


# ---------------------------------------------------------------------------
# 三個動詞
# ---------------------------------------------------------------------------

def test_renew_reactivates_watch_closes_item_and_never_parks_it_in_pq2(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    item = todo.resolve(pool, n, "pending", until=FUTURE, reason="下一季再看")
    assert item["resolution"] == "renewed" and item["receipt"] == f"renewed_until:{FUTURE}"
    assert item["resolved_at"] and "waiting_on" not in item and "deferred_at" not in item, \
        "等待只住 registry，不得同時掛在 pq2"
    watch = ew.load_watches()["watches"][0]
    assert watch["status"] == "active" and watch["expires"] == FUTURE
    assert watch["renewals"][0]["previous_expires"] == PAST and watch["renewals"][0]["n"] == n
    assert todo._collect_watch_expiry_rows() == []
    assert todo.actionable_items(pool) == []


def test_renewed_watch_expiring_again_is_a_new_event_with_a_new_number(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    first = _open(pool)[0]["n"]
    todo.resolve(pool, first, "pending", until=FUTURE)
    data = ew.load_watches()
    later_past = (date.today() - timedelta(days=1)).isoformat()
    data["watches"][0]["expires"] = later_past    # 模擬續等後的到期日也過了
    ew.mark_expired(data)
    ew.save_watches(data)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1 and items[0]["n"] != first and items[0]["ref_id"].endswith("@" + later_past)
    watch = ew.load_watches()["watches"][0]
    assert len(watch["renewals"]) == 1, "續等歷史附加、不覆寫"


@pytest.mark.parametrize("kwargs", [{}, {"trigger": "等下一季"}])
def test_bare_pending_and_trigger_pending_are_rejected(expired_semantic, kwargs) -> None:
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    with pytest.raises(todo.TodoError, match="--until"):
        todo.resolve(pool, n, "pending", **kwargs)
    assert _open(pool)[0]["n"] == n and not _open(pool)[0].get("waiting_on")
    assert ew.load_watches()["watches"][0]["status"] == "expired"


def test_renew_date_must_be_in_the_future(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match="晚於今天"):
        todo.resolve(pool, _open(pool)[0]["n"], "pending", until=date.today().isoformat())


def test_drop_records_expiry_resolution(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    todo.resolve(pool, n, "drop", reason="條件已不重要")
    resolution = ew.load_watches()["watches"][0]["expiry_resolution"]
    assert resolution["verb"] == "drop" and resolution["n"] == n and resolution["reason"] == "條件已不重要"
    assert ew.load_watches()["watches"][0]["status"] == "expired"
    assert todo._collect_watch_expiry_rows() == []


def test_go_requires_a_research_result_that_exists(expired_semantic, monkeypatch) -> None:
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    monkeypatch.setattr(leads, "load", lambda *a, **k: {"leads": {"lead_real": {}}})
    for receipt, match in [("", "必須附研究結果"), ("lead:lead_ghost", "lead 不存在"),
                           ("report:../outside.md", "report"), ("report:docs/nope.md", "report"),
                           ("watch:ew_9999", "watch 不存在"), ("action:ra_x", "只接受")]:
        with pytest.raises(todo.TodoError, match=match):
            todo.resolve(pool, n, "go", receipt=receipt)
    assert "expiry_resolution" not in ew.load_watches()["watches"][0]
    item = todo.resolve(pool, n, "go", receipt="lead:lead_real;report:AGENTS.md")
    assert item["resolution"] == "go"
    resolution = ew.load_watches()["watches"][0]["expiry_resolution"]
    assert resolution["verb"] == "go" and resolution["receipt"] == "lead:lead_real;report:AGENTS.md"


def test_go_with_a_newly_registered_watch_is_accepted(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    data = ew.load_watches()
    new = _semantic(data, expires=FUTURE)
    ew.save_watches(data)
    item = todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"watch:{new['watch_id']}")
    assert item["resolution"] == "go"


def test_batch_syntax_rejects_bare_go_and_pending_but_accepts_drop(expired_semantic) -> None:
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    assert todo.apply_batch(pool, {"go": [n]})["failed"] == [n]
    assert todo.apply_batch(pool, {"pending": [n]})["failed"] == [n]
    assert todo.apply_batch(pool, {"drop": [n]}, reason="批次放棄")["applied"] == [n]


def test_standing_go_never_touches_watch_decision(expired_semantic) -> None:
    from engine_b import standing_authorization

    auth = standing_authorization.load()
    assert not auth.is_authorized("watch_decision")
    pool = _pool()
    _sync(pool)
    candidates, _skipped = todo.standing_go_candidates(pool, authorization=auth)
    assert candidates == []


def test_r2b_rollback_collector_is_not_wired_into_sync() -> None:
    """R2-b NO_GO（2026-09-24）的回滾守衛：B1／B2 修好前，sync 不得呼叫 watch_decision 收集器。
    重新啟用時連同這條測試一起拿掉——那是一個要被看見的決定，不是順手改回。"""
    assert "watch_expiry" not in {name for name, _ in todo.SOURCE_COLLECTORS}
    assert "watch_expiry" not in todo.SOURCE_ITEM_TYPES


def test_go_authorization_row_excludes_every_authority_mutation() -> None:
    go_means, excludes = todo.GO_AUTHORIZATION["watch_decision"]
    assert "bounded research" in go_means
    for word in ("入圖", "Engine C", "thesis mutation", "live"):
        assert word in excludes


# ---------------------------------------------------------------------------
# pq2 型、追源型、讀圖型
# ---------------------------------------------------------------------------

def _pq2_item(pool, *, waiting_until):
    item = todo.upsert(pool, item_type="manual", ref_id="m1", title="等 S-4 公開", hint="", source="manual")
    item["waiting_on"] = {"until": waiting_until, "trigger": None, "reason": None, "set_at": "x"}
    item["deferred_at"] = "x"
    return item


def test_pq2_watch_expiry_returns_its_item_to_the_user(monkeypatch) -> None:
    monkeypatch.setattr(leads, "load", lambda *a, **k: {"leads": {}})
    pool = _pool()
    expiring = _pq2_item(pool, waiting_until=PAST)
    still = todo.upsert(pool, item_type="manual", ref_id="m2", title="等 10-K", hint="", source="manual")
    still["waiting_on"] = {"until": FUTURE, "trigger": None, "reason": None, "set_at": "x"}
    data = ew.load_watches()
    gone = ew.add_watch(data, kind="entity_filing_signal", wake_pq2=expiring["n"], expires=PAST, entities=[SIVERS])
    ew.add_watch(data, kind="entity_filing_signal", wake_pq2=still["n"], expires=FUTURE, entities=[SIVERS])
    ew.save_watches(data)
    before_still = json.dumps(still, sort_keys=True)

    todo._check_event_watches(pool, stamp="2026-09-24T00:00:00+00:00")

    assert "waiting_on" not in expiring and "deferred_at" not in expiring
    assert expiring in todo.actionable_items(pool)
    assert pool["log"][-1]["verb"] == "watch_expired" and pool["log"][-1]["n"] == expiring["n"]
    assert json.dumps(still, sort_keys=True) == before_still, "未到期的項目逐筆不變"
    watch = next(w for w in ew.load_watches()["watches"] if w["watch_id"] == gone["watch_id"])
    assert watch["expiry_resolution"]["kind"] == "requeued_to_pq2"
    todo._check_event_watches(pool, stamp="2026-09-25T00:00:00+00:00")
    assert sum(1 for e in pool["log"] if e["verb"] == "watch_expired") == 1, "同一次到期只翻一次"


def test_reading_watch_expiry_only_records_a_resolution(monkeypatch) -> None:
    monkeypatch.setattr(leads, "load", lambda *a, **k: {"leads": {}})
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="entity_filing_signal", wake_reading="tech:cw_dfb_laser", expires=PAST,
                         entities=["co:nvidia"])
    ew.save_watches(data)
    pool = _pool()
    todo._check_event_watches(pool, stamp="2026-09-24T00:00:00+00:00")
    stored = next(w for w in ew.load_watches()["watches"] if w["watch_id"] == watch["watch_id"])
    assert stored["status"] == "expired" and stored["expiry_resolution"]["kind"] == "reading_expiry"
    assert pool["items"] == [] and todo._collect_watch_expiry_rows() == []


def _park(store):
    lead_id, _ = leads.register(store, source="x:old", url="https://x.com/old/status/1",
                                title="Waiting for $AXTI primary source")
    leads.triage(store, lead_id, go=True, tier=4, reason="需要追原文", decided_at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={
        "parked_reason": "目前只有 tier 3 轉述", "trace_status": "isolated_tier_3",
        "trace_next_trigger": "下一份一手文件", "trace_requires_user": "false"})
    return lead_id


def test_trace_watch_expiry_closes_the_lead_and_is_counted() -> None:
    store = leads.empty_store()
    lead_id = _park(store)
    data = ew.load_watches()
    watch = next(w for w in data["watches"] if w.get("wake_lead") == lead_id)
    watch["expires"] = PAST
    assert ew.mark_expired(data) == [watch["watch_id"]]
    closed = leads.close_expired_trace_watches(store, data)
    assert closed == [{"watch_id": watch["watch_id"], "lead_id": lead_id, "outcome": "trace_closed"}]
    assert store["leads"][lead_id]["refs"]["trace_status"] == "watch_expired"
    assert store["leads"][lead_id]["status"] == "parked"
    counts = ew.expiry_counters(data)
    assert counts["trace_expired_closed"] == 1 and counts["trace_expired_closed_today"] == 1
    assert counts["expiry_unresolved"] == 0 and counts["expiry_decision_pending"] == 0
    assert leads.close_expired_trace_watches(store, data) == [], "冪等"
    ew.save_watches(data)
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store)), \
        "終局 trace_status 不是黑洞"
    assert all(row.get("lead_id") != lead_id for row in leads.trace_backlog(store)), "終局不再留在 backlog"
    assert todo._collect_watch_expiry_rows() == [], "追源型不佔 pq2"


def test_consume_fired_cli_closes_expired_trace_watches(tmp_path, capsys) -> None:
    from engine_b import cli

    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    lead_id = _park(store)
    leads.save(store, path)
    data = ew.load_watches()
    next(w for w in data["watches"] if w.get("wake_lead") == lead_id)["expires"] = PAST
    ew.save_watches(data)

    assert cli.main(["--leads", str(path), "consume-fired", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["trace_expired_closed"][0]["outcome"] == "trace_closed"
    assert leads.load(path)["leads"][lead_id]["refs"]["trace_status"] == "isolated_tier_3", "dry-run 不寫"

    assert cli.main(["--leads", str(path), "consume-fired"]) == 0
    capsys.readouterr()
    assert leads.load(path)["leads"][lead_id]["refs"]["trace_status"] == "watch_expired"
    assert ew.load_watches()["watches"][0]["expiry_resolution"]["kind"] == "trace_closed"


def test_trace_expiry_on_an_in_flight_lead_only_records_the_resolution() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="edgar:LITE", url="https://x.io/f")
    leads.triage(store, lead_id, go=True, tier=1, reason="一手")
    data = {"schema_version": 1, "watches": [
        {"watch_id": "ew_a", "status": "expired", "kind": "related_entity_signal", "wake_lead": lead_id,
         "entities": ["LITE"], "expires": PAST}]}
    closed = leads.close_expired_trace_watches(store, data)
    assert closed[0]["outcome"] == "lead_triaged_go"
    assert "trace_status" not in (store["leads"][lead_id].get("refs") or {})


def test_watch_expired_is_a_registered_terminal_trace_status() -> None:
    from engine_b import lead_refs

    registry = json.loads(open("config/lead_trace_status.json", encoding="utf-8").read())
    assert registry["statuses"]["watch_expired"]["terminal"] is True
    assert lead_refs.validate_ref_updates({"trace_status": "watch_expired"})["trace_status"] == "watch_expired"


def test_expired_condition_of_a_superseded_memo_is_resolved_not_asked(tmp_path) -> None:
    """到期待決的 thesis 條件，它的 memo 已被取代 → 對帳記處置，不鑄 watch_decision 問一個沒有對象的問題。"""
    from engine_b import disproof

    data = ew.load_watches()
    watch = _semantic(data)
    ew.mark_expired(data)
    memo = tmp_path / "thesis" / "x_v2_lane_memo.md"
    memo.parent.mkdir(parents=True)
    memo.write_text("# memo\n", encoding="utf-8")
    life = {"x": {"status": "active", "memo": "thesis/x_v2_lane_memo.md", "check_interval_days": 90}}
    summary = disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path, today=date.today())
    assert watch["watch_id"] in summary["consumed"]
    assert watch["status"] == "expired" and watch["expiry_resolution"]["kind"] == "source_superseded"
    ew.save_watches(data)
    assert todo._collect_watch_expiry_rows() == []
