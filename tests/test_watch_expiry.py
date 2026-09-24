"""到期處置（Phase 1 Step 1.7；A3、INV-2「到期是重問不是丟」、定案 #3／#4；R2-b 修訂）。

守的機制：
- 語意型／假設型到期 → 恰好一個 `watch_decision`（重跑 sync 不重鑄；到期當天收集時 watch 還是 active 也照日期認，
  標記前後 ref_id 相同；續等後再到期是新事件、新編號）。
- **對帳是真的在跑**（R2-b B1：舊版測試把對帳 monkeypatch 掉才沒抓到）：thesis 在暫存目錄、sidecar 帶結構化反證，
  到期的條件不被重登、drop 之後由「未盯」現形、壞掉的條目不拖垮整輪。
- 三個動詞：續等（watch 回 active、編號結案、不掛 waiting_on；來源非現行拒收）、drop、go＝研究結論「條件已被觸及」
  （outcome＋研究結果＋原文；接手路徑與 judge 同形：thesis_lifecycle／needs_reread／假設的 woken_by）。
- 過時的到期事件只准 drop（stale_event、不動 registry）。
- pq2 型翻回球在你；追源型轉終局＋計數、不覆寫既有終局、在路上時到期之後再 park 會建新等待；讀圖型只記處置。
- 常規授權永不碰這一型；處置 kind 是封閉字彙。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine_b import disproof
from engine_b import event_watch as ew
from engine_b import leads
from engine_b import todo
from thesis.memo_structure import memo_text_sha256

SIVERS = "co:sivers_semiconductors"
CONDITION = "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產"
MEMO = "thesis/x_v1_lane_memo.md"
REF = f"thesis:{MEMO}#1"
PAST = (date.today() - timedelta(days=3)).isoformat()
FUTURE = (date.today() + timedelta(days=120)).isoformat()
REPORT = "docs/reports/2026-09-24-phase1-baseline.md"   # docs/reports/ 之下一份真實存在的報告


@pytest.fixture
def env(tmp_path, monkeypatch):
    """暫存的 thesis（現行 memo＋sidecar）、lifecycle、leads；`todo._reconcile_disproof` 用真的對帳邏輯跑在暫存目錄上。"""
    from crons import thesis_freshness_check as tfc

    state = {"structured": [], "life": {"x": {"status": "active", "memo": MEMO, "check_interval_days": 90,
                                               "last_checked": "2026-09-01", "next_check": "2099-01-01"}},
             "leads": {}}

    def write_memo(conditions, *, memo=MEMO, sidecar_conditions=None):
        text = "# memo\n\n## 6. 什麼會推翻這個 thesis\n\n" + "".join(f"- {c}\n" for c in conditions)
        path = tmp_path / memo
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        sidecar = {"memo_sha256": memo_text_sha256(text)}
        if sidecar_conditions is not None:
            sidecar["disproof_conditions"] = sidecar_conditions
        path.with_suffix(".evidence.json").write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")

    def reconcile():
        data = ew.load_watches()
        summary = disproof.reconcile_thesis_disproof(data, lifecycle=state["life"], root=tmp_path)
        ew.save_watches(data)
        return summary

    def save_life():
        path = tmp_path / "lifecycle.json"
        path.write_text(json.dumps(state["life"], ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(tfc, "LIFECYCLE", path)

    write_memo([CONDITION])
    save_life()
    monkeypatch.setattr(todo, "_reconcile_disproof", reconcile)
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: state["life"])
    real_load = leads.load
    monkeypatch.setattr(leads, "load", lambda path=None: real_load(path) if path else {"leads": state["leads"]})
    state.update(write_memo=write_memo, save_life=save_life, tmp=tmp_path)
    return state


def _semantic(data, *, expires=PAST, ref=REF, node=""):
    watch = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref, expires=FUTURE,
                         entities=[SIVERS], condition=CONDITION, check_frequency="每季財報後",
                         action_48h="重讀 thesis 並決定 revise", node=node)
    watch["expires"] = expires   # 測試 fixture：直接給過去的到期日（真實資料不造假，plan §0.3 #10）
    return watch


def _expired(ref=REF, node=""):
    data = ew.load_watches()
    watch = _semantic(data, ref=ref, node=node)
    ew.mark_expired(data)
    ew.save_watches(data)
    return watch["watch_id"]


def _pool():
    return {"items": [], "log": [], "next_n": 1}


def _sync(pool):
    return todo.sync(pool, todo._collect_watch_expiry_rows())


def _open(pool, item_type="watch_decision"):
    return [i for i in pool["items"] if i["type"] == item_type and not i.get("resolved_at")]


def _watch(watch_id):
    return next(w for w in ew.load_watches()["watches"] if w["watch_id"] == watch_id)


def _for_ref(ref=REF):
    return [w for w in ew.load_watches()["watches"] if w.get("source_ref") == ref]


# ---------------------------------------------------------------------------
# 收集：恰好一個編號
# ---------------------------------------------------------------------------

def test_expired_semantic_watch_mints_exactly_one_decision_and_resync_does_not_remint(env) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1
    assert items[0]["ref_id"] == f"{watch_id}@{PAST}"
    assert CONDITION[:20] in items[0]["title"] and REF in items[0]["title"], "標題要寫出條件與來源，不得只寫 co:* 或 watch_id"
    assert "--verb pending --until" in items[0]["hint"], "續等要給真的能跑的完整命令"


def test_expiry_day_row_before_marking_keeps_the_same_ref_id(env) -> None:
    data = ew.load_watches()
    _semantic(data)
    ew.save_watches(data)
    pool = _pool()
    _sync(pool)                                   # 到期當天：收集時還是 active，sync 之後才被標 expired
    before = _open(pool)
    _sync(pool)
    after = _open(pool)
    assert len(before) == len(after) == 1 and after[0]["n"] == before[0]["n"], "標記前後不得換 key 重鑄"


def test_hypothesis_watch_expiry_also_mints_a_decision(env) -> None:
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="fact_verification", hypothesis_ref="hyp_1", expires=PAST,
                         entities=[SIVERS], fact="客戶端會具名第二家供應商")
    ew.mark_expired(data)
    ew.save_watches(data)
    rows = todo._collect_watch_expiry_rows()
    assert [r["ref_id"] for r in rows] == [f"{watch['watch_id']}@{PAST}"]
    assert "假設 watch 到期" in rows[0]["title"] and "hyp_1" in rows[0]["title"]


def test_other_expiry_classes_do_not_mint_decisions(env) -> None:
    data = ew.load_watches()
    ew.add_watch(data, kind="related_entity_signal", wake_lead="lead_x", expires=PAST, entities=[SIVERS])
    ew.add_watch(data, kind="entity_filing_signal", wake_reading="tech:cw_dfb_laser", expires=PAST,
                 entities=["co:nvidia"])
    ew.add_watch(data, kind="date", wake_pq2=7, until=PAST, expires=PAST)
    ew.mark_expired(data)
    ew.save_watches(data)
    assert todo._collect_watch_expiry_rows() == []


# ---------------------------------------------------------------------------
# B1：對帳真的在跑——到期的條件不重登
# ---------------------------------------------------------------------------

def _structured(env, **extra):
    cond = {"condition": CONDITION, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀 thesis",
            **extra}
    env["write_memo"]([CONDITION], sidecar_conditions=[cond])


def _expire_all(ref=REF):
    data = ew.load_watches()
    for watch in data["watches"]:
        if watch.get("source_ref") == ref and watch["status"] == "active":
            watch["expires"] = PAST
    ew.mark_expired(data)
    ew.save_watches(data)


def test_expired_structured_condition_is_not_re_registered_by_reconcile(env) -> None:
    _structured(env)
    pool = _pool()
    _sync(pool)                                   # 對帳登記一筆
    assert [w["status"] for w in _for_ref()] == ["active"]
    _expire_all()
    _sync(pool)
    _sync(pool)
    assert [w["status"] for w in _for_ref()] == ["expired"], "同一條件只能有一筆非 consumed（不得同時住 pq2 與 registry）"
    assert len(_open(pool)) == 1
    counts = disproof.disproof_counts(ew.load_watches()["watches"], lifecycle=env["life"], root=env["tmp"])
    assert (counts["expired_pending"], counts["unwatched"]) == (1, 0), \
        "到期待決不是未盯（試跑發現：原本在 pq2 等你決定的條件被算成沒人盯）"


def test_drop_leaves_the_condition_unwatched_and_it_shows_up_as_such(env) -> None:
    _structured(env)
    pool = _pool()
    _sync(pool)
    _expire_all()
    _sync(pool)
    todo.resolve(pool, _open(pool)[0]["n"], "drop", reason="這條不再重要")
    _sync(pool)
    assert [w["status"] for w in _for_ref()] == ["expired"], "drop 不得被對帳悄悄重登回 active"
    counts = disproof.disproof_counts(ew.load_watches()["watches"], lifecycle=env["life"], root=env["tmp"])
    assert counts["expected"] == 1 and counts["unwatched"] == 1, "放棄的等待由「未盯」現形"


def test_renew_keeps_one_watch_and_re_expiry_is_one_new_number(env) -> None:
    _structured(env)
    pool = _pool()
    _sync(pool)
    _expire_all()
    _sync(pool)
    first = _open(pool)[0]["n"]
    todo.resolve(pool, first, "pending", until=FUTURE)
    _sync(pool)
    assert [w["status"] for w in _for_ref()] == ["active"], "續等後同一條件仍只有一筆"
    _expire_all()
    _sync(pool)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1 and items[0]["n"] != first
    assert len(_for_ref()) == 1


def test_a_broken_sidecar_entry_does_not_take_down_the_whole_reconcile(env) -> None:
    good = {"condition": CONDITION, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀"}
    other = "另一條件：任一客戶以正式文件宣布第二家外部雷射供應商通過認證"
    bad = dict(good, condition=other, expires=PAST)   # 過去的到期日：add_watch 會拒收
    env["write_memo"]([CONDITION, other], sidecar_conditions=[good, bad])
    summary = todo._reconcile_disproof()
    assert len(summary["registered"]) == 1 and len(summary["errors"]) == 1
    assert summary["errors"][0]["ref"] == f"thesis:{MEMO}#2"


# ---------------------------------------------------------------------------
# 三個動詞
# ---------------------------------------------------------------------------

def test_renew_reactivates_watch_closes_item_and_never_parks_it_in_pq2(env) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    item = todo.resolve(pool, n, "pending", until=FUTURE, reason="下一季再看")
    assert item["resolution"] == "renewed" and item["receipt"] == f"renewed_until:{FUTURE}"
    assert "waiting_on" not in item and "deferred_at" not in item, "等待只住 registry，不得同時掛在 pq2"
    watch = _watch(watch_id)
    assert watch["status"] == "active" and watch["expires"] == FUTURE
    assert watch["renewals"][0]["previous_expires"] == PAST and watch["renewals"][0]["n"] == n
    assert todo._collect_watch_expiry_rows() == [] and todo.actionable_items(pool) == []


@pytest.mark.parametrize("kwargs", [{}, {"trigger": "等下一季"}, {"until": FUTURE, "event_type": "decision_evidence_delta",
                                                               "trigger": "x"}])
def test_bare_trigger_and_event_type_pending_are_rejected(env, kwargs) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    with pytest.raises(todo.TodoError, match="--until"):
        todo.resolve(pool, n, "pending", **kwargs)
    assert _open(pool)[0]["n"] == n and not _open(pool)[0].get("waiting_on")
    assert _watch(watch_id)["status"] == "expired"


def test_renew_date_must_be_in_the_future(env) -> None:
    _expired()
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match="晚於今天"):
        todo.resolve(pool, _open(pool)[0]["n"], "pending", until=date.today().isoformat())


def test_renew_is_refused_when_the_source_is_no_longer_current(env, monkeypatch) -> None:
    watch_id = _expired()
    pool = _pool()
    monkeypatch.setattr(todo, "_reconcile_disproof", lambda: None)   # 模擬「sync 之後 memo 才換版」
    _sync(pool)
    env["life"]["x"]["memo"] = "thesis/x_v2_lane_memo.md"
    with pytest.raises(todo.TodoError, match="不是現行"):
        todo.resolve(pool, _open(pool)[0]["n"], "pending", until=FUTURE)
    assert _watch(watch_id)["status"] == "expired"


def test_drop_records_a_closed_vocabulary_resolution(env) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    todo.resolve(pool, n, "drop", reason="條件已不重要")
    resolution = _watch(watch_id)["expiry_resolution"]
    assert resolution["kind"] == "dropped" and resolution["n"] == n and resolution["reason"] == "條件已不重要"
    assert todo._collect_watch_expiry_rows() == []


# ---------------------------------------------------------------------------
# B2：go＝研究結論「條件已被觸及」，接手路徑接得到
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("receipt,quote,match", [
    ("", "x", "必須附研究結論"),
    (f"report:{REPORT}", "x", "outcome:touched"),
    (f"outcome:not_touched;report:{REPORT}", "x", "續等"),
    ("outcome:touched", "x", "研究結果"),
    (f"outcome:touched;report:{REPORT}", "", "--quote"),
    ("outcome:touched;action:ra_x", "x", "不認得"),
    ("outcome:touched;report:AGENTS.md", "x", "report"),
    ("outcome:touched;report:docs/reports/nope.md", "x", "report"),
    ("outcome:touched;report:../outside.md", "x", "report"),
    ("outcome:touched;lead:lead_ghost", "x", "lead 不存在"),
    ("outcome:touched;watch:ew_9999", "x", "watch"),
])
def test_go_receipt_rules(env, receipt, quote, match) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match=match):
        todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=receipt, quote=quote)
    assert "expiry_resolution" not in _watch(watch_id)


def test_go_evidence_must_come_after_this_expiry(env) -> None:
    watch_id = _expired()
    env["leads"]["lead_old"] = {"first_seen": "2026-01-01T00:00:00+00:00", "triage": {"decided_at": "2026-01-02"}}
    env["leads"]["lead_new"] = {"first_seen": datetime.now(timezone.utc).isoformat(), "triage": None}
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    with pytest.raises(todo.TodoError, match="早於這次到期"):
        todo.resolve(pool, n, "go", receipt="outcome:touched;lead:lead_old", quote="x")
    with pytest.raises(todo.TodoError, match="自己"):
        todo.resolve(pool, n, "go", receipt=f"outcome:touched;watch:{watch_id}", quote="x")
    item = todo.resolve(pool, n, "go", receipt="outcome:touched;lead:lead_new", quote="entered volume production",
                        reason="客戶 8-K 已宣布")
    assert item["resolution"] == "go"


def test_go_touched_on_a_thesis_condition_hands_off_to_thesis_lifecycle(env) -> None:
    from crons import thesis_freshness_check as tfc

    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    todo.resolve(pool, n, "go", receipt=f"outcome:touched;report:{REPORT}", quote="entered volume production",
                 reason="研究：客戶 8-K 宣布量產")
    watch = _watch(watch_id)
    assert watch["status"] == "consumed" and watch["expiry_resolution"]["kind"] == "touched"
    assert watch["judgment"]["touches"] == "yes" and watch["judgment"]["via"] == f"watch_decision:{n}"
    assert watch["judgment"]["handled"] is None
    detail = tfc.lifecycle_due_detail()
    assert [(tid, ids) for tid, _why, ids in detail] == [("x", [watch_id])], "觸及後由 thesis_lifecycle 接住（INV-2）"


def test_go_touched_on_a_reading_condition_lists_the_node_for_reread(env) -> None:
    from alpha.providers.structure_readings import reread_reasons

    watch_id = _expired(ref="reading:sr_x#1", node="tech:cw_dfb_laser")
    pool = _pool()
    todo.sync(pool, todo._collect_watch_expiry_rows())
    todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;report:{REPORT}", quote="x")
    reasons = reread_reasons("tech:cw_dfb_laser", ew.load_watches()["watches"])
    assert any("反證被判觸及" in r for r in reasons), watch_id


def test_go_touched_on_a_hypothesis_watch_records_a_wake(env) -> None:
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="fact_verification", hypothesis_ref="oa_x", expires=PAST,
                         entities=[SIVERS], fact="客戶端會具名第二家供應商")
    ew.mark_expired(data)
    ew.save_watches(data)
    pool = _pool()
    _sync(pool)
    todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;report:{REPORT}", quote="named")
    stored = _watch(watch["watch_id"])
    assert stored["status"] == "consumed" and stored["woken_by"]["kind"] == "watch_decision"


def test_go_with_a_newly_registered_watch_is_accepted(env) -> None:
    _expired()
    pool = _pool()
    _sync(pool)
    data = ew.load_watches()
    new = ew.add_watch(data, kind="entity_filing_signal", wake_pq2=99, expires=FUTURE, entities=[SIVERS])
    ew.save_watches(data)
    item = todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;watch:{new['watch_id']}",
                        quote="x")
    assert item["resolution"] == "go"


# ---------------------------------------------------------------------------
# NB-3：過時的到期事件
# ---------------------------------------------------------------------------

def test_stale_event_only_accepts_drop_and_leaves_the_registry_alone(env) -> None:
    watch_id = _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    data = ew.load_watches()
    ew.renew(data, watch_id, until=FUTURE)        # 另一條路先續等了（例如 registry 存了、pool 沒存）
    ew.save_watches(data)
    before = json.dumps(_watch(watch_id), sort_keys=True)
    for verb, kwargs in (("go", {"receipt": f"outcome:touched;report:{REPORT}", "quote": "x"}),
                         ("pending", {"until": FUTURE})):
        with pytest.raises(todo.TodoError, match="過時"):
            todo.resolve(pool, n, verb, **kwargs)
    item = todo.resolve(pool, n, "drop")
    assert item["resolution"] == "stale_event" and item["resolved_at"]
    assert json.dumps(_watch(watch_id), sort_keys=True) == before


def test_superseded_memo_on_expiry_day_is_resolved_before_collection(env) -> None:
    """CLI 先對帳再收集：到期當天 memo 換版 → 不鑄號（偏差 #12、R2-b NB-3）。"""
    watch_id = _expired()
    env["life"]["x"]["memo"] = "thesis/x_v2_lane_memo.md"
    env["write_memo"]([CONDITION], memo="thesis/x_v2_lane_memo.md")
    reconciled = todo._reconcile_disproof()
    pool = _pool()
    todo.sync(pool, todo._collect_watch_expiry_rows(), reconciled=reconciled)
    assert _open(pool) == []
    assert _watch(watch_id)["expiry_resolution"]["kind"] == "source_superseded"


def test_superseded_reading_resolves_its_expired_conditions(env) -> None:
    from alpha.providers.structure_readings import register_reading_watches
    from alpha.structure_reading.contracts import structure_reading_record

    old = "sr_0123456789abcdef"
    watch_id = _expired(ref=f"reading:{old}#1", node="tech:cw_dfb_laser")
    record = structure_reading_record(
        node="tech:cw_dfb_laser", structure={"result_digest": "d" * 16, "angles": {}, "anchor_chain": []},
        kind="volume", reading="重讀：供給側大家差不多，賭的是產能一時補不上——判讀不變。",
        expires=date.today() + timedelta(days=30),
        created_at=datetime.now(timezone.utc), author="test", supersedes_id=old,
        disproof=[{"condition": CONDITION, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀"}])
    summary = register_reading_watches(record)
    assert watch_id in summary["consumed"]
    assert _watch(watch_id)["expiry_resolution"]["kind"] == "source_superseded"
    assert todo._collect_watch_expiry_rows() == []


# ---------------------------------------------------------------------------
# 批次語法、常規授權、授權字串、封閉字彙
# ---------------------------------------------------------------------------

def test_batch_syntax_rejects_bare_go_and_pending_but_accepts_drop(env) -> None:
    _expired()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    assert todo.apply_batch(pool, {"go": [n]})["failed"] == [n]
    assert todo.apply_batch(pool, {"pending": [n]})["failed"] == [n]
    assert todo.apply_batch(pool, {"drop": [n]}, reason="批次放棄")["applied"] == [n]


def test_standing_go_never_touches_watch_decision(env) -> None:
    from engine_b import standing_authorization

    auth = standing_authorization.load()
    assert not auth.is_authorized("watch_decision")
    _expired()
    pool = _pool()
    _sync(pool)
    candidates, _skipped = todo.standing_go_candidates(pool, authorization=auth)
    assert candidates == []


def test_go_authorization_row_says_what_go_records_and_excludes_every_authority() -> None:
    go_means, excludes = todo.GO_AUTHORIZATION["watch_decision"]
    assert "研究結論" in go_means and "條件已被觸及" in go_means
    for word in ("入圖", "Engine C", "thesis mutation", "live", "不得 go"):
        assert word in excludes


def test_r2b_rerun_rollback_collector_is_not_wired_into_sync() -> None:
    """R2-b 重審 NO_GO（RB-1、RB-2）的回滾守衛：修好前 sync 不得呼叫 watch_decision 收集器。
    重新啟用時改回「已接上」的測試——那是一個要被看見的決定，不是順手改回。"""
    assert "watch_expiry" not in {name for name, _ in todo.SOURCE_COLLECTORS}
    assert "watch_expiry" not in todo.SOURCE_ITEM_TYPES


def test_quote_is_only_for_watch_decision(env) -> None:
    pool = _pool()
    item = todo.upsert(pool, item_type="manual", ref_id="m1", title="x", hint="", source="manual")
    with pytest.raises(todo.TodoError, match="--quote"):
        todo.resolve(pool, item["n"], "drop", quote="x")


def test_expiry_resolution_kind_is_a_closed_vocabulary() -> None:
    data = {"schema_version": 1, "watches": [{"watch_id": "ew_a", "status": "expired", "kind": "date",
                                              "expires": PAST}]}
    with pytest.raises(ew.EventWatchError, match="未知的到期處置"):
        ew.resolve_expiry(data, "ew_a", {"kind": "lead_triaged_go"})


# ---------------------------------------------------------------------------
# pq2 型、追源型、讀圖型
# ---------------------------------------------------------------------------

def test_pq2_watch_expiry_returns_its_item_to_the_user(env) -> None:
    pool = _pool()
    expiring = todo.upsert(pool, item_type="manual", ref_id="m1", title="等 S-4 公開", hint="", source="manual")
    expiring["waiting_on"] = {"until": PAST, "trigger": None, "reason": None, "set_at": "x"}
    expiring["deferred_at"] = "x"
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
    assert _watch(gone["watch_id"])["expiry_resolution"]["kind"] == "requeued_to_pq2"
    todo._check_event_watches(pool, stamp="2026-09-25T00:00:00+00:00")
    assert sum(1 for e in pool["log"] if e["verb"] == "watch_expired") == 1, "同一次到期只翻一次"


def test_reading_watch_expiry_only_records_a_resolution(env) -> None:
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="entity_filing_signal", wake_reading="tech:cw_dfb_laser", expires=PAST,
                         entities=["co:nvidia"])
    ew.save_watches(data)
    pool = _pool()
    todo._check_event_watches(pool, stamp="2026-09-24T00:00:00+00:00")
    stored = _watch(watch["watch_id"])
    assert stored["status"] == "expired" and stored["expiry_resolution"]["kind"] == "reading_expiry"
    assert pool["items"] == [] and todo._collect_watch_expiry_rows() == []


def _park(store, *, trace_status="isolated_tier_3"):
    lead_id, _ = leads.register(store, source="x:old", url=f"https://x.com/old/status/{len(store['leads'])}",
                                title="Waiting for $AXTI primary source")
    leads.triage(store, lead_id, go=True, tier=4, reason="需要追原文", decided_at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={
        "parked_reason": "目前只有 tier 3 轉述", "trace_status": trace_status,
        "trace_next_trigger": "下一份一手文件", "trace_requires_user": "false"})
    return lead_id


def _trace_watch(data, lead_id):
    return next(w for w in data["watches"] if w.get("wake_lead") == lead_id)


def test_trace_watch_expiry_closes_the_lead_and_is_counted() -> None:
    store = leads.empty_store()
    lead_id = _park(store)
    data = ew.load_watches()
    watch = _trace_watch(data, lead_id)
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
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store)), "終局 trace_status 不是黑洞"
    assert all(row.get("lead_id") != lead_id for row in leads.trace_backlog(store)), "終局不再留在 backlog"
    assert todo._collect_watch_expiry_rows() == [], "追源型不佔 pq2"


def test_trace_expiry_never_overwrites_an_existing_terminal_status() -> None:
    """NB-2：`contradicts` 被蓋成 `watch_expired` 等於丟失「原主張被推翻」。"""
    store = leads.empty_store()
    lead_id = _park(store)
    leads.annotate_refs(store, lead_id, refs={"trace_status": "contradicts"})
    data = ew.load_watches()
    _trace_watch(data, lead_id)["expires"] = PAST
    ew.mark_expired(data)
    closed = leads.close_expired_trace_watches(store, data)
    assert closed[0]["outcome"] == "lead_already_terminal"
    assert store["leads"][lead_id]["refs"]["trace_status"] == "contradicts"


def test_in_flight_expiry_then_re_park_gets_a_fresh_wait() -> None:
    """NB-1：lead 在路上時 watch 到期，之後研究完再 park——不得沿用那筆到期的 watch 變成沒有到期的等待。"""
    store = leads.empty_store()
    lead_id = _park(store)
    data = ew.load_watches()
    old = _trace_watch(data, lead_id)
    leads.advance(store, lead_id, "pending")
    leads.triage(store, lead_id, go=True, tier=4, reason="被叫醒重查")
    old["expires"] = PAST
    ew.mark_expired(data)
    assert leads.close_expired_trace_watches(store, data)[0]["outcome"] == "lead_in_flight"
    ew.save_watches(data)
    leads.advance(store, lead_id, "parked", ref={
        "parked_reason": "重查仍未果", "trace_status": "isolated_tier_3",
        "trace_next_trigger": "下一份一手文件", "trace_requires_user": "false"})
    watches = [w for w in ew.load_watches()["watches"] if w.get("wake_lead") == lead_id]
    assert sorted(w["status"] for w in watches) == ["active", "expired"], "再 park 要建新一輪的等待"
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store))


def test_expired_but_unresolved_trace_wait_still_counts_as_waiting() -> None:
    """⑩ 標到期到隔天 ⑨ 結案之間，不得在心跳的「無到期的等待」裡閃一天。"""
    store = leads.empty_store()
    lead_id = _park(store)
    data = ew.load_watches()
    _trace_watch(data, lead_id)["expires"] = PAST
    ew.mark_expired(data)
    ew.save_watches(data)
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store))


def test_consume_fired_cli_closes_expired_trace_watches(tmp_path, capsys) -> None:
    from engine_b import cli

    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    lead_id = _park(store)
    leads.save(store, path)
    data = ew.load_watches()
    _trace_watch(data, lead_id)["expires"] = PAST
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
    assert closed[0]["outcome"] == "lead_in_flight"
    assert data["watches"][0]["expiry_resolution"]["lead_status"] == "triaged_go"
    assert "trace_status" not in (store["leads"][lead_id].get("refs") or {})


def test_watch_expired_is_a_registered_terminal_trace_status() -> None:
    from engine_b import lead_refs

    registry = json.loads(open("config/lead_trace_status.json", encoding="utf-8").read())
    assert registry["statuses"]["watch_expired"]["terminal"] is True
    assert lead_refs.validate_ref_updates({"trace_status": "watch_expired"})["trace_status"] == "watch_expired"
