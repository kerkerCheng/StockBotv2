"""短評 v2（Phase 3 Step 3.4）：契約、寫入當下的前提、敘事來源的 watch。

每一條拒收規則都有一條會紅的測試；登記 hook 的每一種路徑（新登、連結、換版、撤回、處置）都有夾具。
寫入當下才成立的檢查（讀圖現行、供給側、watch active、稽核行有值）住寫入端——這裡用注入的 `WriteContext`，
不連圖、不讀真實 ledger、不寫 `event_watches.json`。
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V1, RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.briefs import WriteContext, read_brief_records, write_brief
from engine_b import event_watch as ew
from engine_b.narrative_watches import attributed_watches
from engine_b.queue_segments import SEGMENT_BY_KEY, classify_watch

TODAY = date.today()
FAR = (TODAY + timedelta(days=200)).isoformat()
CO, T = "co:axt", "AXTI"
OTHER = "co:coherent"
READ = "sr_" + "a" * 16


def _slots(priced="已定價：自家三年 {own_history_basis} 的第 {own_history_pctile} 百分位。",
           position="坐在 InP 基板這一層，最新一季營收年增 {in_numbers_latest}（{in_numbers_as_of}）。",
           wmbt="必須為真：六吋良率拉上來；錯的訊號是客戶改用住友。") -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "Coherent 預付產能。", "evidence_refs": ev},
            "position": {"text": position, "evidence_refs": ev},
            "bottleneck": {"text": "三家供應、產能同時補不上。", "evidence_refs": ev},
            "priced_in": {"text": priced, "evidence_refs": ev},
            "our_bet": {"text": "賭層的量：InP 基板供給補不上。", "evidence_refs": ev},
            "what_must_be_true": {"text": wmbt, "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 的財報。", "evidence_refs": ev}}


def _disproof(condition="若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，本敘事的量的賭注不成立", **over) -> dict:
    item = {"condition": condition, "check_frequency": "每季", "action_48h": "重寫敘事並重看讀圖",
            "entities": [CO], "expires": FAR, "source": "self", "link_source_ref": None}
    item.update(over)
    return item


def _record(*, state="open", watch_id=None, reason=None, rides=None, disproof=None, answers=None, slots=None,
            supersedes=None, acks=(), stamp=None, **kw) -> dict:
    return brief_record(
        company_id=CO, ticker=T, slots=slots or _slots(), record_version=RECORD_VERSION_V2,
        rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}] if rides is None else rides,
        disproof=[_disproof()] if disproof is None else disproof,
        answers=answers or {"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": state, "watch_id": watch_id, "reason": reason},
        supersedes_id=supersedes, acknowledged_touched=list(acks),
        created_at=stamp or datetime.now(timezone.utc), **kw)


def _reading(supply=(CO,), demand=(OTHER,)):
    return SimpleNamespace(angles={"supply_side": [(c, "supplies_to", "tech:x") for c in supply],
                                   "demand_side": [(c, "depends_on", "tech:x") for c in demand]})


def _tq(**absent) -> dict:
    def row(key, value=1.0):
        kind = absent.get(key)
        return {"key": key, "value": None if kind else value, "absence_kind": kind}
    return {"priced_in": [row("own_history_pctile", 88.0), row("cohort_median"), row("rel_return_30d"),
                          row("rel_return_90d")],
            "in_numbers": [row("in_numbers_series", [{"yoy": 1.0}])]}


def _ctx(*, status="current", kind="volume", watches=None, tq=None, reading=None, lifecycle=None) -> WriteContext:
    return WriteContext(
        today=TODAY,
        reading_rows=[{"node": "tech:x", "unit": "layer", "reading_id": READ, "status": status, "kind": kind}],
        readings_by_id={READ: reading or _reading()},
        three_questions=tq if tq is not None else _tq(cohort_median="not_yet_recorded", rel_return_30d="not_yet_recorded",
                                                      rel_return_90d="not_yet_recorded"),
        watches={"schema_version": 1, "watches": list(watches or [])}, lifecycle=lifecycle or {})


def _write(tmp_path: Path, record: dict, ctx: WriteContext) -> dict:
    return write_brief(record, ctx=ctx, directory=tmp_path / "briefs", watches_path=tmp_path / "w.json")


def _wake_brief(ctx: WriteContext, company=CO, *, kind="date") -> dict:
    extra = {"until": (TODAY + timedelta(days=30)).isoformat()} if kind == "date" else {"entities": [company]}
    return ew.add_watch(ctx.watches, kind=kind, wake_brief=company, expires=FAR, **extra)


# ---------------------------------------------------------------------------
# 契約（靜態）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mutate, message", [
    (lambda kw: kw.update(slots=_slots(priced="已定價：session_judgment {own_history_pctile}")), "禁字"),
    (lambda kw: kw.update(slots=_slots(priced="{own_history_pctile} 對了值 {payoff}")), "未登記"),
    (lambda kw: kw.update(slots=_slots(priced="{own_history_pctile} {assumption:revenue_growth[total]}")), "v2 沒有帶參數"),
    (lambda kw: kw.update(slots=_slots(priced="已經漲很多了，市場都知道")), "own_history_pctile"),
    (lambda kw: kw.update(slots=_slots(position="坐在 InP 基板這一層")), "in_numbers_latest"),
    (lambda kw: kw.update(slots=_slots(wmbt="現價 {price} 以下才成立")), "不得有價格"),
    (lambda kw: kw.update(disproof=[_disproof(entities=["AXTI"])]), "co:"),
    (lambda kw: kw.update(disproof=[_disproof(expires=None)]), "expires"),
    (lambda kw: kw.update(state="missing"), "watch_id"),
    (lambda kw: kw.update(state="pass"), "reason"),
    (lambda kw: kw.update(state="held"), "held"),
    (lambda kw: kw.update(rides=[]), "rides"),
])
def test_v2_content_rules_refuse_at_the_type_layer(mutate, message) -> None:
    kw: dict = {}
    mutate(kw)
    with pytest.raises(ContractViolation, match=message):
        _record(**kw)


def test_v2_id_covers_the_structured_fields_and_v1_ids_ignore_them() -> None:
    stamp = datetime(2026, 9, 30, tzinfo=timezone.utc)
    a = _record(stamp=stamp)
    b = _record(stamp=stamp, disproof=[_disproof(check_frequency="每月")])
    assert a["brief_id"] != b["brief_id"]
    assert a["record_version"] == RECORD_VERSION_V2 and "candidate_state" in a
    v1 = brief_record(company_id=CO, ticker=T, created_at=stamp,
                      slots={k: {"text": "x", "evidence_refs": ["e"]} for k in
                             ("demand", "supply", "bottleneck", "market_view", "our_bet", "if_right_if_wrong", "when")})
    assert v1["record_version"] == RECORD_VERSION_V1 and "candidate_state" not in v1
    assert parse_brief_record(v1).candidate_state is None


# ---------------------------------------------------------------------------
# 寫入當下
# ---------------------------------------------------------------------------

def test_a_valid_open_brief_writes_and_registers_its_disproof(tmp_path: Path) -> None:
    ctx = _ctx()
    out = _write(tmp_path, _record(), ctx)
    assert len(out["registered"]) == 1
    watch = ctx.watches["watches"][0]
    assert watch["source_ref"] == f"brief:{out['brief_id']}#1" and ew.expiry_class(watch) == "rewrite"
    assert (tmp_path / "w.json").exists()


@pytest.mark.parametrize("ctx_kw, message", [
    ({"status": "stale"}, "只有 current／stale_low"),
    ({"kind": "undecided"}, "護城河或量"),
    ({"reading": _reading(supply=(OTHER,), demand=(CO,))}, "需求側"),
    ({"tq": _tq()}, "cohort_median"),
])
def test_write_time_preconditions_refuse_with_the_reason(tmp_path: Path, ctx_kw, message) -> None:
    with pytest.raises(ContractViolation, match=message):
        _write(tmp_path, _record(), _ctx(**ctx_kw))
    assert not (tmp_path / "briefs").exists()


_LATER = (TODAY + timedelta(days=400)).isoformat()


@pytest.mark.parametrize("record_kw, message", [
    ({"disproof": [_disproof(condition=f"若 JX 在 {_LATER} 前宣布新產能投產則供給缺口消失，本敘事的量的賭注不成立",
                             expires=(TODAY + timedelta(days=30)).isoformat())]}, "早於條件自己寫的日期"),
    ({"disproof": [_disproof(entities=[CO, "co:no_such_company_xyz"])]}, "registry 解析不到"),
    ({"disproof": [_disproof(link_source_ref="reading:sr_" + "c" * 16 + "#9")]}, "沒有在盯的 watch"),
    ({"disproof": [_disproof(source="sr_" + "c" * 16)]}, "不是任何讀圖 id"),
    ({"rides": [{"node": "tech:x", "unit": "layer", "reading_id": "sr_" + "b" * 16}]}, "現行讀圖不是"),
])
def test_write_time_disproof_and_ride_checks_refuse_with_the_reason(tmp_path: Path, record_kw, message) -> None:
    """R2-a N7：寫入端這幾條原本只有手動驗過。"""
    with pytest.raises(ContractViolation, match=message):
        _write(tmp_path, _record(**record_kw), _ctx())
    assert not (tmp_path / "briefs").exists()


def test_retracting_a_v2_closes_its_active_watches(tmp_path: Path) -> None:
    ctx = _ctx()
    first = _write(tmp_path, _record(), ctx)
    watch = ctx.watches["watches"][0]
    target = read_brief_records(T, directory=tmp_path / "briefs")[0][0]
    retract = brief_record(company_id=CO, ticker=T, created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
                           slots=[{"key": s.key, "text": s.text, "evidence_refs": list(s.evidence_refs)} for s in target.slots],
                           supersedes_id=first["brief_id"], retracted=True, record_version=target.record_version,
                           rides=[r.as_dict() for r in target.rides], disproof=[d.as_dict() for d in target.disproof],
                           answers=target.answers.as_dict(), candidate_state=target.candidate_state.as_dict())
    _write(tmp_path, retract, ctx)
    assert watch["status"] == "consumed" and watch["closed"]["note"].startswith("retracted by")


def test_stale_low_counts_as_current(tmp_path: Path) -> None:
    _write(tmp_path, _record(), _ctx(status="stale_low"))


def test_unmeasurable_only_when_the_audit_lines_are_all_absent(tmp_path: Path) -> None:
    rec = _record(answers={"priced_in": "unmeasurable", "in_numbers": "yes"})
    with pytest.raises(ContractViolation, match="量得到就要答"):
        _write(tmp_path, rec, _ctx())
    all_absent = _tq(own_history_pctile="upstream_unavailable", cohort_median="not_yet_recorded",
                     rel_return_30d="not_yet_recorded", rel_return_90d="not_yet_recorded")
    _write(tmp_path, rec, _ctx(tq=all_absent))


def test_declared_history_not_comparable_is_what_the_writer_checks_unmeasurable_against(tmp_path: Path) -> None:
    """R2-a N3（Step 3.6 接上）：宣告「歷史不可比」→ 寫入端用宣告後重算的三題驗 unmeasurable。"""
    rec = _record(answers={"priced_in": "unmeasurable", "in_numbers": "yes"},
                  history_not_comparable={"since": "2026-01-01", "reason": "剛轉型：營收結構換了", "source": "self"})
    plain = _ctx()                                                    # 自家歷史那一行有值、沒有重算 → 拒收
    with pytest.raises(ContractViolation, match="量得到就要答"):
        _write(tmp_path, rec, plain)
    seen = []
    declared = _ctx()
    declared.three_questions_reload = lambda hnc: (seen.append(hnc), _tq(
        own_history_pctile="insufficient_evidence", cohort_median="not_yet_recorded",
        rel_return_30d="not_yet_recorded", rel_return_90d="not_yet_recorded"))[1]
    _write(tmp_path, rec, declared)
    assert seen and seen[0]["since"] == "2026-01-01"


def test_missing_must_point_at_this_companys_active_wake_brief_watch(tmp_path: Path) -> None:
    ctx = _ctx()
    mine = _wake_brief(ctx)
    other = _wake_brief(ctx, company=OTHER)
    thesis = ew.add_watch(ctx.watches, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:m.md#1", source_ref="thesis:m.md#1",
                          expires=FAR, entities=[CO], condition="x" * 30, check_frequency="每季", action_48h="複查")
    for wid, message in ((other["watch_id"], "wake_brief=co:axt"), (thesis["watch_id"], "wake_brief=co:axt"),
                         ("ew_nope", "不存在")):
        with pytest.raises(ContractViolation, match=message):
            _write(tmp_path, _record(state="missing", watch_id=wid), ctx)
    mine["status"] = "consumed"
    with pytest.raises(ContractViolation, match="不是 active"):
        _write(tmp_path, _record(state="missing", watch_id=mine["watch_id"]), ctx)
    fresh = _wake_brief(ctx)
    _write(tmp_path, _record(state="missing", watch_id=fresh["watch_id"]), ctx)


def test_a_condition_already_watched_is_linked_not_registered_twice(tmp_path: Path) -> None:
    ctx = _ctx()
    cond = "若客戶在 2026-12-31 前改用第二家基板供應商則單一來源的論點不成立並需要重讀"
    existing = ew.add_watch(ctx.watches, kind=ew.SEMANTIC_KIND, disproof_ref=f"reading:{READ}#1",
                            source_ref=f"reading:{READ}#1", expires=FAR, entities=[CO], condition=cond,
                            check_frequency="每季", action_48h="重讀", node="tech:x")
    with pytest.raises(ContractViolation, match="只填 link_source_ref"):
        _write(tmp_path, _record(disproof=[_disproof(condition=cond, source=READ)]), ctx)
    out = _write(tmp_path, _record(disproof=[_disproof(condition=cond, source=READ,
                                                       link_source_ref=existing["source_ref"])]), ctx)
    assert out["registered"] == [] and out["linked"] == [existing["source_ref"]]
    assert len(ctx.watches["watches"]) == 1          # 搬讀圖反證不產生第二筆 watch


def test_open_is_refused_while_an_attributed_watch_waits_for_judgment(tmp_path: Path) -> None:
    ctx = _ctx()
    w = ew.add_watch(ctx.watches, kind=ew.SEMANTIC_KIND, disproof_ref=f"reading:{READ}#2",
                     source_ref=f"reading:{READ}#2", expires=FAR, entities=[OTHER],
                     condition="讀圖反證：客戶端出現第二家供應商並通過驗證", check_frequency="每季",
                     action_48h="重讀", node="tech:x")
    w["status"] = "fired"
    with pytest.raises(ContractViolation, match="醒來待判"):
        _write(tmp_path, _record(), ctx)


# ---------------------------------------------------------------------------
# 換版、撤回、處置
# ---------------------------------------------------------------------------

def test_supersede_closes_only_active_watches_and_the_next_write_must_acknowledge(tmp_path: Path) -> None:
    ctx = _ctx()
    first = _write(tmp_path, _record(disproof=[_disproof(), _disproof(condition="若住友在 2026-12-31 前宣布六吋 InP 量產則量的論點削弱")]), ctx)
    w1, w2 = ctx.watches["watches"]
    w2["status"] = "fired"                                   # 第二條醒了
    assert classify_watch(w2) == "narrative_rewrite"
    with pytest.raises(ContractViolation, match="acknowledged_touched 沒處置"):
        _write(tmp_path, _record(supersedes=first["brief_id"]), ctx)
    second = _write(tmp_path, _record(supersedes=first["brief_id"], acks=[
        {"watch_id": w2["watch_id"], "disposition": "thesis_changed", "note": "住友 9/30 公告量產，已改寫量的賭注"}]), ctx)
    assert w1["status"] == "consumed" and w1["closed"]["note"].startswith("superseded")
    assert w2["status"] == "consumed" and w2["judgment"]["handled"]["verb"] == "thesis_changed"
    assert "quote" not in w2["judgment"]                      # R2-a C5：作者 note 不是文件逐字，不得進 quote（L12／L18）
    assert w2["judgment"]["note"].startswith("住友")
    assert second["registered"]


def test_a_past_expiry_brief_watch_not_yet_marked_by_daily_is_not_swallowed_by_supersede(tmp_path: Path) -> None:
    """R2-a C4：daily 還沒跑時，已過 expires 的 `brief:` watch 仍是 active——換版不得把它當「還在等」收掉。"""
    ctx = _ctx()
    first = _write(tmp_path, _record(), ctx)
    watch = ctx.watches["watches"][0]
    watch["expires"] = (TODAY - timedelta(days=1)).isoformat()
    assert watch["status"] == "active"
    with pytest.raises(ContractViolation, match="acknowledged_touched 沒處置"):
        _write(tmp_path, _record(supersedes=first["brief_id"]), ctx)
    _write(tmp_path, _record(supersedes=first["brief_id"], acks=[
        {"watch_id": watch["watch_id"], "disposition": "retired", "note": "條件已過期、本版不再依賴"}]), ctx)
    assert watch["status"] == "expired" and watch["expiry_resolution"]["kind"] == "narrative_rewritten"
    assert "closed" not in watch                              # 不是被換版 consumed 掉的


@pytest.mark.parametrize("change", ["until_arrived", "past_expiry"])
def test_candidate_state_refuses_a_wait_that_has_already_woken_or_expired_by_date(tmp_path: Path, change) -> None:
    """R2-a C4：`candidate_state` 不得指向一筆照日期已醒／已到期、只是 daily 還沒標記的 watch。"""
    ctx = _ctx()
    w = _wake_brief(ctx)
    if change == "until_arrived":
        w["until"] = TODAY.isoformat()
    else:
        w["expires"] = (TODAY - timedelta(days=1)).isoformat()
    with pytest.raises(ContractViolation, match="不是 active"):
        _write(tmp_path, _record(state="missing", watch_id=w["watch_id"]), ctx)


def test_retract_does_not_swallow_a_touched_watch_and_rewriting_after_retract_still_acknowledges(tmp_path: Path) -> None:
    ctx = _ctx()
    first = _write(tmp_path, _record(), ctx)
    watch = ctx.watches["watches"][0]
    watch["status"] = "consumed"
    watch["judgment"] = {"touches": "yes", "handled": None, "note": "n", "quote": "q"}
    target = read_brief_records(T, directory=tmp_path / "briefs")[0][0]
    retract = brief_record(company_id=CO, ticker=T, created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
                           slots=[{"key": s.key, "text": s.text, "evidence_refs": list(s.evidence_refs)} for s in target.slots],
                           supersedes_id=first["brief_id"], retracted=True, record_version=target.record_version,
                           rides=[r.as_dict() for r in target.rides], disproof=[d.as_dict() for d in target.disproof],
                           answers=target.answers.as_dict(), candidate_state=target.candidate_state.as_dict())
    _write(tmp_path, retract, ctx)
    assert watch["judgment"]["handled"] is None               # 撤回不吞觸及
    with pytest.raises(ContractViolation, match="acknowledged_touched 沒處置"):
        _write(tmp_path, _record(stamp=datetime.now(timezone.utc) + timedelta(seconds=2)), ctx)
    _write(tmp_path, _record(stamp=datetime.now(timezone.utc) + timedelta(seconds=3), acks=[
        {"watch_id": watch["watch_id"], "disposition": "still_holds", "note": "判定後確認條件其實沒發生"}]), ctx)
    assert watch["judgment"]["handled"]["verb"] == "still_holds"


def test_a_watch_registration_failure_is_refused_before_the_ledger_is_touched(tmp_path: Path) -> None:
    """R2-a C1：條件不到 20 字的反證過得了契約與寫入前提，但 `add_watch` 會拒——必須在 append 之前拒收。"""
    ctx = _ctx()
    before = copy.deepcopy(ctx.watches)
    with pytest.raises(ContractViolation, match="預演失敗"):
        _write(tmp_path, _record(disproof=[_disproof(condition="JX 宣布新產能投產")]), ctx)
    assert read_brief_records(T, directory=tmp_path / "briefs")[0] == []
    assert ctx.watches == before and not (tmp_path / "w.json").exists()
    _write(tmp_path, _record(), ctx)                          # 修好之後同一家照常寫得進去


def test_open_fails_closed_when_the_thesis_lifecycle_cannot_be_read(tmp_path: Path) -> None:
    """R2-a C3：lifecycle 讀不到＝thesis 來源的 watch 歸屬不到本檔，醒來待判也擋不住——可開要 fail closed。"""
    ctx = _ctx()
    ctx.lifecycle = None
    with pytest.raises(ContractViolation, match="lifecycle 讀不到"):
        _write(tmp_path, _record(), ctx)
    _write(tmp_path, _record(state="pass", reason="非邊緣"), ctx)   # 只擋可開


def test_rerunning_the_same_record_does_not_register_twice(tmp_path: Path) -> None:
    ctx = _ctx()
    rec = _record()
    _write(tmp_path, rec, ctx)
    with pytest.raises(ContractViolation, match="重複"):
        _write(tmp_path, rec, ctx)
    assert len(ctx.watches["watches"]) == 1


def test_new_v1_writes_are_refused(tmp_path: Path) -> None:
    v1 = brief_record(company_id=CO, ticker=T, slots={k: {"text": "x", "evidence_refs": ["e"]} for k in
                      ("demand", "supply", "bottleneck", "market_view", "our_bet", "if_right_if_wrong", "when")})
    with pytest.raises(ContractViolation, match="一律 v2"):
        _write(tmp_path, v1, _ctx())


# ---------------------------------------------------------------------------
# wake_brief 的兩條路、歸屬
# ---------------------------------------------------------------------------

def test_a_wake_brief_date_watch_fires_into_narrative_rewrite_not_hypothesis_check() -> None:
    data = {"watches": []}
    w = ew.add_watch(data, kind="date", wake_brief=CO, until=TODAY.isoformat(), expires=FAR)
    fired = ew.check_watches(data, today=TODAY)
    assert fired and w["status"] == "fired"
    assert classify_watch(w) == "narrative_rewrite" != "fired_hypothesis_check"
    assert ew.wake_target(w)["kind"] == "brief"


def test_an_expired_wake_brief_is_rewrite_class_and_never_mints_a_watch_decision() -> None:
    data = {"watches": []}
    w = ew.add_watch(data, kind="entity_filing_signal", wake_brief=CO, entities=[CO],
                     expires=(TODAY - timedelta(days=1)).isoformat())
    ew.mark_expired(data, today=TODAY)
    assert w["status"] == "expired" and ew.expiry_class(w) == "rewrite" != "decision"
    assert classify_watch(w) == "narrative_rewrite"
    assert ew.expiry_counters(data, today=TODAY)["expiry_rewrite_pending"] == 1


def test_wake_brief_is_exclusive_and_limited_to_its_kinds() -> None:
    data = {"watches": []}
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", wake_brief=CO, wake_pq2=5, until=FAR, expires=FAR)
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="fact_verification", wake_brief=CO, fact="x", entities=[CO], expires=FAR)
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", wake_brief="co:not_a_company", until=FAR, expires=FAR)


def test_attribution_is_by_source_not_by_entities_or_candidate_state() -> None:
    watches = [
        {"watch_id": "a", "source_ref": "thesis:thesis/axt.md#3", "entities": ["co:jx_advanced_metals"]},
        {"watch_id": "b", "source_ref": "reading:sr_other#1", "entities": [CO]},        # entities 有本檔、來源不是
        {"watch_id": "c", "wake_brief": CO},
        {"watch_id": "d", "wake_brief": OTHER},
        {"watch_id": "e", "source_ref": "brief:ib_x#1"},
    ]
    lifecycle = {"axt_inp": {"ticker": T, "memo": "thesis/axt.md", "status": "active"}}
    got = {w["watch_id"] for w in attributed_watches(CO, T, watches=watches, lifecycle=lifecycle, brief_ids=["ib_x"])}
    assert got == {"a", "c", "e"}


def test_the_narrative_rewrite_segment_has_a_consumer_that_mentions_it() -> None:
    seg = SEGMENT_BY_KEY["narrative_rewrite"]
    assert seg.cost == "research" and "research-drain" in seg.consumer
    skill = (Path(__file__).resolve().parents[1] / "skills" / "research-drain" / "SKILL.md").read_text(encoding="utf-8")
    assert "narrative_rewrite" in skill and "acknowledged_touched" in skill


def test_disproof_counts_counts_new_narrative_conditions_once_and_links_not_at_all() -> None:
    from engine_b.disproof import disproof_counts

    brief = parse_brief_record(_record(disproof=[_disproof(), _disproof(
        condition="讀圖反證：客戶改用第二家供應商並通過驗證（連結既有）", link_source_ref=f"reading:{READ}#1")]))
    watches = [{"watch_id": "w1", "kind": ew.SEMANTIC_KIND, "status": "active",
                "source_ref": f"brief:{brief.brief_id}#1", "condition": brief.disproof[0].condition}]
    counts = disproof_counts(watches, lifecycle={}, readings={}, briefs=[brief])
    assert counts["expected"] == 1 and counts["watching"] == 1 and counts["unwatched"] == 0
