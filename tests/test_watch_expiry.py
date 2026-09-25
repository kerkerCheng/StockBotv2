"""到期處置（Phase 1 Step 1.7；A3、INV-2「到期是重問不是丟」、定案 #3／#4；R2-b 兩輪修訂；到期成批選 B）。

守的機制：
- **設計 B**：thesis 來源的反證到期不鑄號，併進那份 thesis 的複查項目；go／drop 那一筆後自動續到下一個核查點、
  觸及的標 handled 並續盯（結構化與手動登記一致）。讀圖來源的列進節點重讀理由。`watch_decision` 只給假設型等
  沒有自己複查週期的等待——恰好一個編號、續等只住 registry、go＝研究結論已發生（回 fired 交假設對照）。
- **對帳真的在跑**（暫存 thesis＋結構化 sidecar）：到期的條件不重登（B1）；lifecycle 讀不到就什麼都不動（RB-1）；
  條件以文字認位置——對調、刪中間、手動登記都 relink 不重複（RB-2／NB2-14）；A→B→A 換回來會重登（NB2-6）。
- 過時的到期事件只准 drop；pq2 型翻回冪等（NB2-13）；追源型轉終局＋計數、不覆寫既有終局、再 park 建新等待。
- 常規授權永不碰 watch_decision；處置 kind 是封閉字彙。
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
#: v3 讀圖（Phase 2 Step 2.3）的兩半引用——本檔只用到契約層，不寫 ledger。
_V3_CITATIONS = [
    {"angle": "demand_side", "edge": ["co:nvidia", "depends_on", "tech:cw_dfb_laser"],
     "quote": "每一個 CPO 光引擎都需要外部 CW 雷射光源才能運作", "source_id": "doc_demand"},
    {"angle": "supply_side", "edge": [SIVERS, "supplies_to", "tech:cw_dfb_laser"],
     "quote": "Sivers 出貨 CW DFB 雷射陣列給 CPO 客戶並擴充產能", "source_id": "doc_supply"},
]
C1 = "Sivers 期中報告揭露 CW DFB 雷射陣列進入量產並具名客戶"
C2 = "任一 hyperscaler 在正式文件宣布改用不經外部雷射的整合方案"
C3 = "任一 hyperscaler 在正式文件宣布第二家外部雷射供應商通過認證"
MEMO = "thesis/x_v1_lane_memo.md"
REF = f"thesis:{MEMO}#1"
PAST = (date.today() - timedelta(days=3)).isoformat()
FUTURE = (date.today() + timedelta(days=120)).isoformat()
HORIZON = (date(2099, 1, 1) + timedelta(days=90)).isoformat()   # fixture 的 next_check＋一個核查週期


@pytest.fixture
def env(tmp_path, monkeypatch):
    """暫存的 thesis（現行 memo＋可選 sidecar）、lifecycle、leads；`todo._reconcile_disproof` 用真的對帳邏輯跑在暫存目錄上。"""
    from crons import thesis_freshness_check as tfc

    state = {"life": {"x": {"status": "active", "memo": MEMO, "check_interval_days": 90,
                            "last_checked": "2026-09-01", "next_check": "2099-01-01"}},
             "leads": {}, "tmp": tmp_path}

    def write_memo(conditions, *, memo=MEMO, structured=False, sidecar_conditions=None):
        text = "# memo\n\n## 6. 什麼會推翻這個 thesis\n\n" + "".join(f"- {c}\n" for c in conditions)
        path = tmp_path / memo
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        sidecar = {"memo_sha256": memo_text_sha256(text)}
        if structured and sidecar_conditions is None:
            sidecar_conditions = [{"condition": c, "entities": [SIVERS], "check_frequency": "每季",
                                   "action_48h": "重讀 thesis"} for c in conditions]
        if sidecar_conditions is not None:
            sidecar["disproof_conditions"] = sidecar_conditions
        path.with_suffix(".evidence.json").write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")

    def reconcile():
        data = ew.load_watches()
        summary = disproof.reconcile_thesis_disproof(data, root=tmp_path)   # lifecycle 走被換掉的 load_lifecycle
        ew.save_watches(data)
        return summary

    def save_life():
        path = tmp_path / "lifecycle.json"
        path.write_text(json.dumps(state["life"], ensure_ascii=False) if state["life"] is not None else "{broken,",
                        encoding="utf-8")
        monkeypatch.setattr(tfc, "LIFECYCLE", path)

    write_memo([CONDITION])
    save_life()
    state["real_reconcile_wrapper"] = todo._reconcile_disproof   # NB3-2：要測正式包裝的存檔條件
    monkeypatch.setattr(todo, "_reconcile_disproof", reconcile)
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: state["life"])
    real_load = leads.load
    monkeypatch.setattr(leads, "load", lambda path=None: real_load(path) if path else {"leads": state["leads"]})
    monkeypatch.setattr(todo, "_ROOT", tmp_path)   # go 的 report: 收據在暫存 repo 裡找
    state.update(write_memo=write_memo, save_life=save_life, reconcile=reconcile)
    return state


def _semantic(data, *, expires=PAST, ref=REF, node="", condition=CONDITION):
    watch = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref, expires=FUTURE,
                         entities=[SIVERS], condition=condition, check_frequency="每季財報後",
                         action_48h="重讀 thesis 並決定 revise", node=node)
    watch["expires"] = expires   # 測試 fixture：直接給過去的到期日（真實資料不造假，plan §0.3 #10）
    return watch


def _expired(ref=REF, node="", condition=CONDITION):
    data = ew.load_watches()
    watch = _semantic(data, ref=ref, node=node, condition=condition)
    ew.mark_expired(data)
    ew.save_watches(data)
    return watch["watch_id"]


def _hyp(*, expires=PAST, ref="oa_x", fact="客戶端會具名第二家外部雷射供應商"):
    data = ew.load_watches()
    watch = ew.add_watch(data, kind="fact_verification", hypothesis_ref=ref, expires=expires,
                         entities=[SIVERS], fact=fact)
    ew.mark_expired(data)
    ew.save_watches(data)
    return watch["watch_id"]


def _pool():
    return {"items": [], "log": [], "next_n": 1}


def _sync(pool):
    return todo.sync(pool, todo._collect_watch_expiry_rows())


def _sync_lifecycle(pool):
    return todo.sync(pool, todo._collect_lifecycle_rows())


def _open(pool, item_type="watch_decision"):
    return [i for i in pool["items"] if i["type"] == item_type and not i.get("resolved_at")]


def _watch(watch_id):
    return next(w for w in ew.load_watches()["watches"] if w["watch_id"] == watch_id)


def _live_for(condition, memo=MEMO):
    return [w for w in ew.load_watches()["watches"] if w.get("kind") == ew.SEMANTIC_KIND
            and disproof.memo_ref(w.get("source_ref") or "") == memo and w.get("condition") == condition
            and disproof._live(w)]


def _report(env, watch_id, name="r.md"):
    path = env["tmp"] / "docs" / "reports" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# 研究\n\n{watch_id}：客戶 8-K 已宣布量產。\n", encoding="utf-8")
    return f"docs/reports/{name}"


# ---------------------------------------------------------------------------
# 設計 B：哪一型進 pq2
# ---------------------------------------------------------------------------

def test_thesis_and_reading_conditions_never_mint_a_decision(env) -> None:
    thesis_id = _expired()
    reading_id = _expired(ref="reading:sr_x#1", node="tech:cw_dfb_laser")
    assert ew.expiry_class(_watch(thesis_id)) == "thesis_review"
    assert ew.expiry_class(_watch(reading_id)) == "reread"
    pool = _pool()
    _sync(pool)
    assert _open(pool) == [] and todo._collect_watch_expiry_rows() == []
    counts = ew.expiry_counters(ew.load_watches())
    assert (counts["expiry_thesis_review_pending"], counts["expiry_reread_pending"],
            counts["expiry_decision_pending"]) == (1, 1, 0)


def test_hypothesis_expiry_mints_exactly_one_decision_with_a_readable_title(env) -> None:
    watch_id = _hyp(fact="**InP substrate ASP 大幅上調**（截圖稱史上最大漲價）")
    pool = _pool()
    _sync(pool)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1 and items[0]["ref_id"] == f"{watch_id}@{PAST}"
    assert "**" not in items[0]["title"] and "InP substrate ASP" in items[0]["title"] and "oa_x" in items[0]["title"]
    assert "--verb pending --until" in items[0]["hint"]


def test_expiry_day_row_before_marking_keeps_the_same_ref_id(env) -> None:
    data = ew.load_watches()
    ew.add_watch(data, kind="fact_verification", hypothesis_ref="oa_x", expires=PAST, entities=[SIVERS], fact="x" * 20)
    ew.save_watches(data)
    pool = _pool()
    _sync(pool)
    before = _open(pool)
    _sync(pool)
    after = _open(pool)
    assert len(before) == len(after) == 1 and after[0]["n"] == before[0]["n"], "標記前後不得換 key 重鑄"


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
# 設計 B：thesis 條件併進 thesis 複查
# ---------------------------------------------------------------------------

def test_expired_thesis_condition_folds_into_the_thesis_review_item(env) -> None:
    from crons import thesis_freshness_check as tfc

    watch_id = _expired()
    detail = tfc.lifecycle_due_detail()
    assert [(tid, ids) for tid, _why, ids in detail] == [("x", [watch_id])]
    assert "反證等滿一輪都沒發生 1 條" in detail[0][1]
    pool = _pool()
    _sync_lifecycle(pool)
    items = _open(pool, "thesis_lifecycle")
    assert len(items) == 1 and items[0]["disproof_watch_ids"] == [watch_id]


@pytest.mark.parametrize("verb,receipt", [("drop", ""), ("go", "lifecycle:x;commit:" + "a" * 40)])
def test_thesis_review_renews_expired_conditions_to_the_next_checkpoint(env, verb, receipt) -> None:
    from crons import thesis_freshness_check as tfc

    watch_id = _expired()
    pool = _pool()
    _sync_lifecycle(pool)
    todo.resolve(pool, _open(pool, "thesis_lifecycle")[0]["n"], verb, receipt=receipt, reason="複查：memo 不改")
    watch = _watch(watch_id)
    assert watch["status"] == "active" and watch["expires"] == HORIZON
    assert watch["renewals"][0]["previous_expires"] == PAST
    assert tfc.lifecycle_due_detail() == [], "續盯之後不再列進複查"
    assert len(_live_for(CONDITION)) == 1


def test_review_after_touch_rewatches_manual_and_structured_alike(env) -> None:
    """NB2-5：判定觸及、複查完之後，手動與結構化登記都恰好續盯一筆。"""
    data = ew.load_watches()
    watch = _semantic(data, expires=FUTURE)
    watch["status"] = "fired"
    watch["woken_by"] = {"lead_id": "L1"}
    ew.judge(data, watch["watch_id"], touches=True, note="量產了", quote="entered volume production")
    ew.save_watches(data)
    pool = _pool()
    _sync_lifecycle(pool)
    todo.resolve(pool, _open(pool, "thesis_lifecycle")[0]["n"], "drop", reason="複查：不改")
    assert _watch(watch["watch_id"])["judgment"]["handled"]["verb"] == "drop"
    live = _live_for(CONDITION)
    assert len(live) == 1 and live[0]["status"] == "active" and live[0]["expires"] == HORIZON
    env["write_memo"]([CONDITION], structured=True)   # 同一條件現在也在 sidecar 裡：對帳不得再登一筆
    assert env["reconcile"]()["registered"] == []
    assert len(_live_for(CONDITION)) == 1


def test_expired_structured_condition_is_not_re_registered_by_reconcile(env) -> None:
    env["write_memo"]([CONDITION], structured=True)
    env["reconcile"]()
    data = ew.load_watches()
    for w in data["watches"]:
        w["expires"] = PAST
    ew.mark_expired(data)
    ew.save_watches(data)
    env["reconcile"]()
    env["reconcile"]()
    assert [w["status"] for w in ew.load_watches()["watches"]] == ["expired"], "到期待複查的條件不得被重登（B1）"


# ---------------------------------------------------------------------------
# 設計 B：讀圖條件併進重讀
# ---------------------------------------------------------------------------

def test_expired_reading_condition_is_a_reread_reason(env) -> None:
    from alpha.providers.structure_readings import reread_reasons

    _expired(ref="reading:sr_x#1", node="tech:cw_dfb_laser")
    reasons = reread_reasons("tech:cw_dfb_laser", ew.load_watches()["watches"])
    assert any("反證等滿一輪都沒發生" in r for r in reasons)


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
        disproof=[{"condition": CONDITION, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀",
                   "source": "self"}], unit="layer", citations=_V3_CITATIONS)
    summary = register_reading_watches(record)
    assert watch_id in summary["consumed"]
    assert _watch(watch_id)["expiry_resolution"]["kind"] == "source_superseded"


# ---------------------------------------------------------------------------
# RB-1：lifecycle 讀不到 → 什麼都不動
# ---------------------------------------------------------------------------

def test_unreadable_lifecycle_freezes_reconcile(env) -> None:
    data = ew.load_watches()
    active = _semantic(data, expires=FUTURE)
    ew.save_watches(data)
    _expired(condition=C1)
    before = json.dumps(ew.load_watches(), sort_keys=True)
    env["life"] = None                       # 手改留下語法錯
    summary = env["reconcile"]()
    assert summary["lifecycle_unreadable"] is True and summary["consumed"] == []
    assert json.dumps(ew.load_watches(), sort_keys=True) == before
    assert disproof.source_is_current(_watch(active["watch_id"])) is False, "讀不到就不放行"


def test_lifecycle_collector_is_not_a_healthy_source_when_unreadable(env, monkeypatch) -> None:
    from crons import thesis_freshness_check as tfc

    env["life"] = None
    env["save_life"]()
    with pytest.raises(tfc.LifecycleUnreadable):
        todo._collect_lifecycle_rows()
    monkeypatch.setattr(todo, "SOURCE_COLLECTORS", (("lifecycle", "_collect_lifecycle_rows"),))
    assert "lifecycle" not in todo.collect_all_with_health().healthy, "讀不到不得被當成「沒有到期」"


# ---------------------------------------------------------------------------
# RB-2：條件以文字認位置
# ---------------------------------------------------------------------------

def _refs():
    return sorted((w["condition"], w["source_ref"]) for w in ew.load_watches()["watches"] if disproof._live(w))


def test_swapped_conditions_are_relinked_not_duplicated(env) -> None:
    env["write_memo"]([C1, C2], structured=True)
    assert len(env["reconcile"]()["registered"]) == 2
    env["write_memo"]([C2, C1], structured=True)
    summary = env["reconcile"]()
    assert summary["registered"] == [] and len(summary["relinked"]) == 2
    assert _refs() == sorted([(C1, f"thesis:{MEMO}#2"), (C2, f"thesis:{MEMO}#1")])


def test_deleting_a_middle_condition_retires_it_and_relinks_the_rest(env) -> None:
    env["write_memo"]([C1, C2, C3], structured=True)
    env["reconcile"]()
    env["write_memo"]([C1, C3], structured=True)
    summary = env["reconcile"]()
    assert len(summary["consumed"]) == 1 and len(summary["relinked"]) == 1 and summary["registered"] == []
    assert _refs() == sorted([(C1, f"thesis:{MEMO}#1"), (C3, f"thesis:{MEMO}#2")])


def test_manual_registrations_are_relinked_too(env) -> None:
    env["write_memo"]([C1])
    data = ew.load_watches()
    _semantic(data, expires=FUTURE, condition=C1)
    ew.save_watches(data)
    env["write_memo"]([C2, C1])
    summary = env["reconcile"]()
    assert summary["no_structured"] == ["x"] and len(summary["relinked"]) == 1
    assert _refs() == [(C1, f"thesis:{MEMO}#2")]


def test_memo_switched_back_re_registers(env) -> None:
    """NB2-6：A→B→A；已處置的到期不擋重登。"""
    env["write_memo"]([C1], structured=True)
    env["reconcile"]()
    data = ew.load_watches()
    data["watches"][0]["expires"] = PAST
    ew.mark_expired(data)
    ew.save_watches(data)
    env["life"]["x"]["memo"] = "thesis/x_v2_lane_memo.md"
    env["write_memo"]([C2], memo="thesis/x_v2_lane_memo.md", structured=True)
    env["reconcile"]()
    assert ew.load_watches()["watches"][0]["expiry_resolution"]["kind"] == "source_superseded"
    env["life"]["x"]["memo"] = MEMO
    env["reconcile"]()
    assert len(_live_for(C1)) == 1


def test_sidecar_condition_not_in_memo_and_unparsable_memo_are_fail_closed(env) -> None:
    env["write_memo"]([C1], sidecar_conditions=[{"condition": C2, "entities": [SIVERS], "check_frequency": "每季",
                                                 "action_48h": "重讀"}])
    summary = env["reconcile"]()
    assert summary["registered"] == [] and "不在 memo" in summary["errors"][0]["error"]
    data = ew.load_watches()
    _semantic(data, expires=FUTURE, condition=C1)
    ew.save_watches(data)
    (env["tmp"] / MEMO).write_text("# memo\n\n沒有推翻那一節\n", encoding="utf-8")
    summary = env["reconcile"]()
    assert summary["consumed"] == [] and "解析不到" in summary["errors"][0]["error"]
    assert len(_live_for(C1)) == 1


def test_a_broken_sidecar_entry_does_not_take_down_the_whole_reconcile(env) -> None:
    good = {"condition": C1, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀"}
    bad = dict(good, condition=C2, expires=PAST)   # 過去的到期日：add_watch 會拒收
    env["write_memo"]([C1, C2], sidecar_conditions=[good, bad])
    summary = env["reconcile"]()
    assert len(summary["registered"]) == 1 and len(summary["errors"]) == 1
    assert summary["errors"][0]["ref"] == f"thesis:{MEMO}#2"


# ---------------------------------------------------------------------------
# watch_decision（假設型）的三個動詞
# ---------------------------------------------------------------------------

def test_renew_reactivates_watch_closes_item_and_never_parks_it_in_pq2(env) -> None:
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    item = todo.resolve(pool, n, "pending", until=FUTURE, reason="下一季再看")
    assert item["resolution"] == "renewed" and item["receipt"] == f"renewed_until:{FUTURE}"
    assert "waiting_on" not in item and "deferred_at" not in item, "等待只住 registry，不得同時掛在 pq2"
    watch = _watch(watch_id)
    assert watch["status"] == "active" and watch["expires"] == FUTURE and watch["renewals"][0]["n"] == n
    assert todo._collect_watch_expiry_rows() == [] and todo.actionable_items(pool) == []


def test_renewed_watch_expiring_again_says_so_in_the_title(env) -> None:
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    todo.resolve(pool, _open(pool)[0]["n"], "pending", until=FUTURE)
    data = ew.load_watches()
    # 「今天」取程式用的那一個（UTC 日期）：台北 00:00–08:00 本地日期比它多一天，「昨天」會變成 UTC 的今天而不到期
    later = (ew._today() - timedelta(days=1)).isoformat()
    next(w for w in data["watches"] if w["watch_id"] == watch_id)["expires"] = later
    ew.mark_expired(data)
    ew.save_watches(data)
    _sync(pool)
    items = _open(pool)
    assert len(items) == 1 and items[0]["ref_id"].endswith("@" + later) and "第 2 次到期" in items[0]["title"]


@pytest.mark.parametrize("kwargs", [{}, {"trigger": "等下一季"}, {"until": FUTURE, "event_type": "decision_evidence_delta",
                                                               "trigger": "x"}])
def test_bare_trigger_and_event_type_pending_are_rejected(env, kwargs) -> None:
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    with pytest.raises(todo.TodoError, match="--until"):
        todo.resolve(pool, n, "pending", **kwargs)
    assert not _open(pool)[0].get("waiting_on") and _watch(watch_id)["status"] == "expired"


def test_renew_date_must_be_in_the_future(env) -> None:
    _hyp()
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match="晚於今天"):
        todo.resolve(pool, _open(pool)[0]["n"], "pending", until=ew._today().isoformat())   # 同上：程式的今天


def test_drop_records_a_closed_vocabulary_resolution(env) -> None:
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    todo.resolve(pool, n, "drop", reason="條件已不重要")
    resolution = _watch(watch_id)["expiry_resolution"]
    assert resolution["kind"] == "dropped" and resolution["n"] == n and resolution["reason"] == "條件已不重要"
    assert todo._collect_watch_expiry_rows() == []


@pytest.mark.parametrize("receipt,quote,match", [
    ("", "x", "必須附研究結論"),
    ("report:{r}", "x", "outcome:touched"),
    ("outcome:not_touched;report:{r}", "x", "續等"),
    ("outcome:touched", "x", "研究結果"),
    ("outcome:touched;report:{r}", "", "--quote"),
    ("outcome:touched;action:ra_x", "x", "不認得"),
    ("outcome:touched;report:AGENTS.md", "x", "report"),
    ("outcome:touched;report:docs/reports/nope.md", "x", "report"),
    ("outcome:touched;report:../outside.md", "x", "report"),
    ("outcome:touched;report:docs/reports/unrelated.md", "x", "沒有提到"),
    ("outcome:touched;lead:lead_ghost", "x", "lead 不存在"),
    ("outcome:touched;watch:ew_9999", "x", "watch"),
])
def test_go_receipt_rules(env, receipt, quote, match) -> None:
    watch_id = _hyp()
    report = _report(env, watch_id)
    (env["tmp"] / "docs" / "reports" / "unrelated.md").write_text("別的研究", encoding="utf-8")
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match=match):
        todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=receipt.format(r=report), quote=quote)
    assert "expiry_resolution" not in _watch(watch_id)


def test_go_evidence_must_come_after_this_expiry(env) -> None:
    watch_id = _hyp()
    # 追源重排改寫過 decided_at 的舊 lead 不得冒充「剛研究過」（NB2-3）
    env["leads"]["lead_old"] = {"first_seen": "2026-01-01T00:00:00+00:00",
                                "triage": {"decided_at": datetime.now(timezone.utc).isoformat()}}
    env["leads"]["lead_new"] = {"first_seen": datetime.now(timezone.utc).isoformat(), "triage": None}
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    with pytest.raises(todo.TodoError, match="早於這次到期"):
        todo.resolve(pool, n, "go", receipt="outcome:touched;lead:lead_old", quote="x")
    with pytest.raises(todo.TodoError, match="自己"):
        todo.resolve(pool, n, "go", receipt=f"outcome:touched;watch:{watch_id}", quote="x")
    assert todo.resolve(pool, n, "go", receipt="outcome:touched;lead:lead_new", quote="named")["resolution"] == "go"


def test_go_on_a_hypothesis_watch_hands_back_to_the_hypothesis_path(env) -> None:
    """NB2-2：回 fired（woken_by＝watch_decision），假設對照照原本的路 consume。"""
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;report:{_report(env, watch_id)}",
                 quote="named in the 10-K")
    stored = _watch(watch_id)
    assert stored["status"] == "fired" and stored["woken_by"]["kind"] == "watch_decision"
    assert stored["expiry_resolution"]["kind"] == "touched"
    assert ew.counters(ew.load_watches())["fired_unconsumed"] == 1


def test_go_with_a_newly_registered_watch_is_accepted(env) -> None:
    _hyp()
    pool = _pool()
    _sync(pool)
    data = ew.load_watches()
    new = ew.add_watch(data, kind="entity_filing_signal", wake_pq2=99, expires=FUTURE, entities=[SIVERS])
    ew.save_watches(data)
    item = todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;watch:{new['watch_id']}",
                        quote="x")
    assert item["resolution"] == "go"


def test_stale_event_only_accepts_drop_and_leaves_the_registry_alone(env) -> None:
    watch_id = _hyp()
    pool = _pool()
    _sync(pool)
    n = _open(pool)[0]["n"]
    data = ew.load_watches()
    ew.renew(data, watch_id, until=FUTURE)        # 另一條路先續等了（例如 registry 存了、pool 沒存）
    ew.save_watches(data)
    before = json.dumps(_watch(watch_id), sort_keys=True)
    for verb, kwargs in (("go", {"receipt": "outcome:touched;watch:ew_x", "quote": "x"}), ("pending", {"until": FUTURE})):
        with pytest.raises(todo.TodoError, match="過時"):
            todo.resolve(pool, n, verb, **kwargs)
    item = todo.resolve(pool, n, "drop")
    assert item["resolution"] == "stale_event" and item["resolved_at"]
    assert json.dumps(_watch(watch_id), sort_keys=True) == before


def test_source_is_current_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: None)
    assert disproof.source_is_current({"source_ref": "thesis:x.md#1"}) is False, "讀不到 lifecycle 不放行"
    life = {"x": {"memo": "x.md", "status": "retired"}}
    assert disproof.source_is_current({"source_ref": "thesis:x.md#1"}, lifecycle=life) is False
    assert disproof.source_is_current({"hypothesis_ref": "oa_x"}) is True


# ---------------------------------------------------------------------------
# 批次語法、常規授權、授權字串、封閉字彙
# ---------------------------------------------------------------------------

def test_batch_syntax_rejects_bare_go_and_pending_but_accepts_drop(env) -> None:
    _hyp()
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
    _hyp()
    pool = _pool()
    _sync(pool)
    candidates, _skipped = todo.standing_go_candidates(pool, authorization=auth)
    assert candidates == []


def test_go_authorization_row_says_what_go_records_and_excludes_every_authority() -> None:
    go_means, excludes = todo.GO_AUTHORIZATION["watch_decision"]
    assert "研究結論" in go_means and "假設對照" in go_means
    for word in ("入圖", "Engine C", "thesis mutation", "live", "不得 go"):
        assert word in excludes


def test_collector_is_wired_into_sync() -> None:
    assert ("watch_expiry", "_collect_watch_expiry_rows") in todo.SOURCE_COLLECTORS
    assert todo.SOURCE_ITEM_TYPES["watch_expiry"] == frozenset({"watch_decision"})


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


def test_condition_label_strips_markers_and_leads_in() -> None:
    assert ew.condition_label("**ELS 時間表**：2026 年底前未確認") == "ELS 時間表：2026 年底前未確認"
    assert ew.condition_label("【disproof（本輪未觸發）】①供給側出現第七家——現況 6 家") == "①供給側出現第七家——現況 6 家"
    assert ew.condition_label("圖外三條要人看：…⑤中國 InP 出口管制解除") == "⑤中國 InP 出口管制解除"
    assert ew.condition_label("圖外三條要人看：④任一家的擴產進度提前或再加碼") == "④任一家的擴產進度提前或再加碼"


# ---------------------------------------------------------------------------
# pq2 型、追源型、讀圖型
# ---------------------------------------------------------------------------

def test_pq2_watch_expiry_returns_its_item_to_the_user(env) -> None:
    pool = _pool()
    expiring = todo.upsert(pool, item_type="manual", ref_id="m1", title="等 S-4 公開", hint="", source="manual")
    expiring["waiting_on"] = {"until": PAST, "trigger": None, "reason": None, "set_at": "2026-01-01T00:00:00+00:00"}
    expiring["deferred_at"] = "2026-01-01T00:00:00+00:00"
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


def test_pq2_requeue_is_idempotent_on_item_state(env) -> None:
    """NB2-13：registry 已記 requeued、pool 沒存到（崩潰）→ 下一輪照樣翻回；使用者到期之後自己又 pending 的不動。"""
    pool = _pool()
    lost = todo.upsert(pool, item_type="manual", ref_id="m1", title="等 A", hint="", source="manual")
    lost["waiting_on"] = {"until": PAST, "trigger": None, "reason": None, "set_at": "2026-01-01T00:00:00+00:00"}
    later = todo.upsert(pool, item_type="manual", ref_id="m2", title="等 B", hint="", source="manual")
    later["waiting_on"] = {"until": FUTURE, "trigger": None, "reason": None, "set_at": "2099-01-01T00:00:00+00:00"}
    data = ew.load_watches()
    for item in (lost, later):
        watch = ew.add_watch(data, kind="entity_filing_signal", wake_pq2=item["n"], expires=PAST, entities=[SIVERS])
        watch["status"] = "expired"
        watch["expired_at"] = "2026-06-01T00:00:00+00:00"
        watch["expiry_resolution"] = {"kind": "requeued_to_pq2", "n": item["n"], "at": "2026-06-01T00:00:00+00:00"}
    ew.save_watches(data)
    todo._check_event_watches(pool, stamp="2026-09-24T00:00:00+00:00")
    assert "waiting_on" not in lost
    assert later.get("waiting_on"), "到期之後使用者自己設的等待不得被清掉"


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
    counts = ew.expiry_counters(data)
    assert counts["trace_expired_closed"] == 1 and counts["trace_expired_closed_today"] == 1
    assert counts["expiry_unresolved"] == 0
    assert leads.close_expired_trace_watches(store, data) == [], "冪等"
    ew.save_watches(data)
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store)), "終局 trace_status 不是黑洞"
    assert all(row.get("lead_id") != lead_id for row in leads.trace_backlog(store)), "終局不再留在 backlog"


def test_trace_expiry_never_overwrites_an_existing_terminal_status() -> None:
    store = leads.empty_store()
    lead_id = _park(store)
    leads.annotate_refs(store, lead_id, refs={"trace_status": "contradicts"})
    data = ew.load_watches()
    _trace_watch(data, lead_id)["expires"] = PAST
    ew.mark_expired(data)
    assert leads.close_expired_trace_watches(store, data)[0]["outcome"] == "lead_already_terminal"
    assert store["leads"][lead_id]["refs"]["trace_status"] == "contradicts"


def test_in_flight_expiry_then_re_park_gets_a_fresh_wait() -> None:
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
    assert sorted(w["status"] for w in watches) == ["active", "expired"]
    assert all(h["lead_id"] != lead_id for h in leads.parked_without_expiry(store))


def test_expired_but_unresolved_trace_wait_still_counts_as_waiting() -> None:
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


def test_watch_expired_is_a_registered_terminal_trace_status() -> None:
    from engine_b import lead_refs

    registry = json.loads(open("config/lead_trace_status.json", encoding="utf-8").read())
    assert registry["statuses"]["watch_expired"]["terminal"] is True
    assert lead_refs.validate_ref_updates({"trace_status": "watch_expired"})["trace_status"] == "watch_expired"


# ---------------------------------------------------------------------------
# R2-b 第三輪（GO）的 NB3 處置
# ---------------------------------------------------------------------------

def _touch(data, watch):
    watch["status"] = "fired"
    watch["woken_by"] = {"lead_id": "L1"}
    ew.judge(data, watch["watch_id"], touches=True, note="量產了", quote="entered volume production")


def test_review_with_unreadable_lifecycle_leaves_the_touch_for_the_next_item(env) -> None:
    """NB3-1(a)：lifecycle 讀不到時不標 handled——標了就不會再列出、續盯又做不了。"""
    data = ew.load_watches()
    watch = _semantic(data, expires=FUTURE)
    _touch(data, watch)
    ew.save_watches(data)
    pool = _pool()
    _sync_lifecycle(pool)
    env["life"] = None
    todo.resolve(pool, _open(pool, "thesis_lifecycle")[0]["n"], "drop", reason="複查")
    assert not _watch(watch["watch_id"])["judgment"].get("handled"), "讀不到 lifecycle 時觸及要留給下一筆"


def test_rewatch_never_expires_before_the_date_written_in_the_condition(env) -> None:
    """NB3-1(b)：續盯的到期不早於條件原文寫的完整日期＋30 天（否則 add_watch 拒收、條件掉進未盯）。"""
    dated = "若客戶在 2099-06-30 前正式宣布改用不經這個節點的替代路徑並量產"
    env["write_memo"]([dated])
    data = ew.load_watches()
    watch = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref=REF, source_ref=REF, expires="2099-08-01",
                         entities=[SIVERS], condition=dated, check_frequency="每季", action_48h="重讀")
    _touch(data, watch)
    ew.save_watches(data)
    pool = _pool()
    _sync_lifecycle(pool)
    todo.resolve(pool, _open(pool, "thesis_lifecycle")[0]["n"], "drop", reason="複查")
    live = _live_for(dated)
    assert len(live) == 1 and live[0]["expires"] >= "2099-07-30"


def test_relink_is_saved_by_the_real_reconcile_wrapper(env, monkeypatch) -> None:
    """NB3-2：只換位置時正式包裝也要存檔（fixture 的替身每次都存，蓋掉過這個 bug）。"""
    env["write_memo"]([C1])
    data = ew.load_watches()
    _semantic(data, expires=FUTURE, condition=C1)
    ew.save_watches(data)
    env["write_memo"]([C2, C1])
    real = disproof.reconcile_thesis_disproof
    monkeypatch.setattr(disproof, "reconcile_thesis_disproof", lambda d, **k: real(d, root=env["tmp"]))
    summary = env["real_reconcile_wrapper"]()
    assert len(summary["relinked"]) == 1
    assert _refs() == [(C1, f"thesis:{MEMO}#2")], "relink 要落地"


def test_scheduled_review_carries_conditions_that_would_expire_within_a_cycle(env) -> None:
    """NB3-3：準時複查時快到期的條件同一次續盯，不會隔天各自到期、另開一筆。"""
    from crons import thesis_freshness_check as tfc

    env["life"]["x"]["next_check"] = (date.today() - timedelta(days=1)).isoformat()   # 排程到期
    env["save_life"]()
    data = ew.load_watches()
    soon = _semantic(data, expires=(date.today() + timedelta(days=10)).isoformat())
    later = _semantic(data, expires=(date.today() + timedelta(days=400)).isoformat(), condition=C1)
    ew.save_watches(data)
    detail = tfc.lifecycle_due_detail()
    assert detail[0][2] == [soon["watch_id"]] and "一併續盯 1 條" in detail[0][1]
    pool = _pool()
    _sync_lifecycle(pool)
    env["life"]["x"]["next_check"] = (date.today() + timedelta(days=90)).isoformat()   # 複查後移到下一個核查點
    todo.resolve(pool, _open(pool, "thesis_lifecycle")[0]["n"], "drop", reason="複查")
    assert _watch(soon["watch_id"])["expires"] == (date.today() + timedelta(days=180)).isoformat()
    assert _watch(soon["watch_id"])["extensions"][0]["n"] == 1
    assert _watch(later["watch_id"])["expires"] == (date.today() + timedelta(days=400)).isoformat(), "只延不縮"


def test_new_reading_retires_every_older_reading_of_the_node(env, monkeypatch) -> None:
    """NB3-4：重讀忘了帶 supersedes_id，也要以節點收掉舊讀圖的條件——不留新舊兩筆。"""
    from alpha.providers import structure_readings as sr
    from alpha.structure_reading.contracts import structure_reading_record

    old = "sr_0123456789abcdef"
    watch_id = _expired(ref=f"reading:{old}#1", node="tech:cw_dfb_laser")

    class _R:
        def __init__(self, rid):
            self.reading_id = rid
            self.unit = "layer"

    monkeypatch.setattr(sr, "read_reading_records", lambda node, **k: ([_R(old)], []))
    record = structure_reading_record(
        node="tech:cw_dfb_laser", structure={"result_digest": "d" * 16, "angles": {}, "anchor_chain": []},
        kind="volume", reading="重讀：供給側大家差不多，賭的是產能一時補不上——判讀不變。",
        expires=date.today() + timedelta(days=30), created_at=datetime.now(timezone.utc), author="test",
        disproof=[{"condition": CONDITION, "entities": [SIVERS], "check_frequency": "每季", "action_48h": "重讀",
                   "source": "self"}], unit="layer", citations=_V3_CITATIONS)
    assert record.get("supersedes_id") is None
    summary = sr.register_reading_watches(record)
    assert watch_id in summary["consumed"]
    assert _watch(watch_id)["expiry_resolution"]["kind"] == "source_superseded"


def test_reading_sourced_semantic_watch_requires_a_node(env) -> None:
    data = ew.load_watches()
    with pytest.raises(ew.EventWatchError, match="node"):
        ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="reading:sr_x#1", source_ref="reading:sr_x#1",
                      expires=FUTURE, entities=[SIVERS], condition=CONDITION, check_frequency="每季", action_48h="重讀")


def test_expiry_attaches_to_a_deferred_review_but_only_a_touch_pulls_it_back(env) -> None:
    """NB3-5a：使用者明示延後的複查，單純到期只附掛、不叫回；判定觸及才叫回。"""
    pool = _pool()
    todo.sync(pool, [{"type": "thesis_lifecycle", "ref_id": "x", "title": "thesis x：到期", "source": "lifecycle"}])
    n = pool["items"][0]["n"]
    todo.resolve(pool, n, "pending", until=FUTURE)
    expired_id = _expired()
    _sync_lifecycle(pool)
    item = pool["items"][0]
    assert item.get("waiting_on") and expired_id in item["disproof_watch_ids"]
    data = ew.load_watches()
    watch = _semantic(data, expires=FUTURE, condition=C1)
    _touch(data, watch)
    ew.save_watches(data)
    env["write_memo"]([CONDITION, C1])
    _sync_lifecycle(pool)
    assert not pool["items"][0].get("waiting_on")
    assert pool["log"][-1]["verb"] == "disproof_touch" and watch["watch_id"] in pool["log"][-1]["reason"]


def test_passed_until_wakes_the_item(env) -> None:
    """NB3-5b：`pending --until` 的日期過了要重問，不能永遠躺在「等事件」。"""
    pool = _pool()
    item = todo.upsert(pool, item_type="manual", ref_id="m1", title="等 S-4", hint="", source="manual")
    item["waiting_on"] = {"until": PAST, "trigger": None, "reason": None, "set_at": "x"}
    item["deferred_at"] = "x"
    keep = todo.upsert(pool, item_type="manual", ref_id="m2", title="等 10-K", hint="", source="manual")
    keep["waiting_on"] = {"until": FUTURE, "trigger": None, "reason": None, "set_at": "x"}
    todo.sync(pool, [])
    assert "waiting_on" not in item and item in todo.actionable_items(pool)
    assert keep.get("waiting_on")
    assert [e["verb"] for e in pool["log"]].count("waiting_until_passed") == 1


@pytest.mark.parametrize("path", ["library/private/app/state/watches.json", "docs/reports/r.txt"])
def test_report_receipt_is_only_a_research_markdown(env, path) -> None:
    """NB3-6：state 檔含所有 watch_id，不得當研究結果。"""
    watch_id = _hyp()
    target = env["tmp"] / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{watch_id}", encoding="utf-8")
    pool = _pool()
    _sync(pool)
    with pytest.raises(todo.TodoError, match="report"):
        todo.resolve(pool, _open(pool)[0]["n"], "go", receipt=f"outcome:touched;report:{path}", quote="x")


def test_counts_do_not_call_thesis_touches_orphans_when_lifecycle_is_unreadable(env) -> None:
    """NB3-8：lifecycle 讀不到時 thesis 的觸及是「沒算」，不是孤兒；memo 解析不到要現形。"""
    data = ew.load_watches()
    watch = _semantic(data, expires=FUTURE)
    _touch(data, watch)
    env["life"] = None                                   # load_lifecycle（被 fixture 換掉）回 None＝讀不到
    c = disproof.disproof_counts(data["watches"], readings={}, root=env["tmp"])
    assert c["lifecycle_unreadable"] is True and c["orphan_touched"] == 0
    env["life"] = {"x": {"status": "active", "memo": MEMO}}
    (env["tmp"] / MEMO).write_text("# memo\n\n沒有推翻那一節\n", encoding="utf-8")
    c = disproof.disproof_counts(data["watches"], readings={}, root=env["tmp"])
    assert c["memo_unreadable"] == ["x"]


def test_register_disproof_refuses_a_duplicate(env, capsys) -> None:
    """NB3-9：同一來源、同一條件已有處理中的等待 → 拒收（否則同一份 lead 叫醒兩次）。"""
    argv = ["register-disproof", "--condition", CONDITION, "--entities", SIVERS, "--source-ref", REF,
            "--check-frequency", "每季", "--action-48h", "重讀", "--expires", FUTURE]
    assert ew.main(argv) == 0
    assert ew.main([*argv[:6], f"thesis:{MEMO}#2", *argv[7:]]) == 2, "換了 #n 也是同一條件"
    assert "不重複登記" in capsys.readouterr().err
    assert len([w for w in ew.load_watches()["watches"] if w.get("kind") == ew.SEMANTIC_KIND]) == 1
