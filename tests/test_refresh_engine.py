"""Research Refresh／Dependency Invalidation v1（`alpha/refresh`）的純邏輯測試。

守的是 Step 0（2026-09-06）暴露的那組問題：**一個 price tick 不得讓整份研究判斷 stale**；
結構事件必須動到引用它的假設；假設不得因為「證據物件還在」就永遠 current；會計期間推進
必須有名字；freshness（stale）與 invalidation（review_required／invalidated）分開；
歷史視角不得被未來的 contradiction 滲入；相同輸入永遠得到相同 report；引擎不碰 LLM。
"""
from __future__ import annotations

import ast
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental.assumptions import assumption_record, parse_assumption_record
from alpha.refresh import (
    ARTIFACT_ASSUMPTION, ARTIFACT_AXIS, COMPANY_GUIDANCE, CONSENSUS, CURRENT,
    DISPROOF_SIGNAL, FINANCIAL_ACTUAL, GRAPH_EDGE, INVALIDATED, KIND_DETERMINISTIC, KIND_JUDGMENT,
    MARKET_PRICE, MISSING, OPERATING_ASSUMPTION, RECALCULATE, REFRESH_STATES, REVIEW_REQUIRED,
    ROLE_CALIBRATION, ROLE_SUPPORTING, STALE, SUPERSEDED, THESIS_ARTIFACT_ID, THESIS_REVIEW_DUE,
    AffectedArtifact, ArtifactDependency, ChangeEvent, MetricObservation, ReviewCondition,
    artifacts_from_assumptions, end_of_day, merge_states, resolve_refresh,
)
from tests.fixtures_fundamental import (
    ACT_REF, CONSENSUS as FY_CONSENSUS, GRAPH_REF, INDEX, TARGET, TODAY, _assumption, _full_set,
)

# ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：FY+1 因果橋退役，refresh 不再登記模型輸出
# （modeled_metric／expectation_comparison／fundamental_model 三種 artifact）。本檔守的判準一字未改
# ——price tick 不 stale 判斷、結構事件只動引用它的、假設不因證據物件還在就永遠 current、
# freshness 與 invalidation 分開、歷史視角不被未來滲入——只是「下游確定性輸出跟著傳播」那幾條
# 斷言沒有主詞了，隨機制退役；`test_fiscal_rollover_is_named_and_old_assumptions_are_not_reused`
# 整條退役（它跑的就是模型）。

UTC = timezone.utc
JUDGED_AT = datetime(2026, 9, 4, 23, 59, 59, tzinfo=UTC)
BUILD_AT = end_of_day(TODAY)
EDGE = GRAPH_REF.ref                                           # graph://edge/co:coherent/supplies_to/co:nvidia
SNAP = "engine_c://financial_snapshot/COHR"
CONS_REV = "engine_c://consensus_estimate/COHR/revenue/2027-06-30"
CONS_EPS = "engine_c://consensus_estimate/COHR/eps/2027-06-30"
LATER = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)                # build 之後才發生的變化
RESOLVE_DAY = date(2026, 9, 7)                                 # 解析日（晚於 LATER，事件才看得到）


def _event(change_type: str, changed_ref: str, *, at: datetime = LATER, **kw) -> ChangeEvent:
    base = dict(change_type=change_type, ticker="COHR", company_id="co:coherent",
                authority="test://authority", changed_ref=changed_ref, observed_at=at)
    base.update(kw)
    return ChangeEvent(**base)


def _axis(axis: str, refs: dict[str, str], *, kind: str = KIND_JUDGMENT,
          established: datetime = JUDGED_AT) -> ArtifactDependency:
    return ArtifactDependency(artifact_type=ARTIFACT_AXIS, artifact_id=axis, label=axis, kind=kind,
                              established_at=established, refs=refs, basis="session_judgment")


def _dc_assumption(**kw):
    """D&C +60%：supporting＝NVIDIA 邊＋基期觀測；calibration＝同期營收共識（v2 角色）。"""
    record = assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="revenue_growth",
        scope="Datacenter & Communications", value=0.60, basis="session_judgment",
        rationale="test D&C", evidence_refs=[EDGE, ACT_REF.ref], calibration_refs=[CONS_REV],
        created_at=datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
        **{"derivation": "independent", **kw})
    return parse_assumption_record(record)


def _index():
    return {**INDEX, ACT_REF.ref: ACT_REF,
            CONS_REV: FY_CONSENSUS[1].evidence[0], CONS_EPS: FY_CONSENSUS[0].evidence[0]}


def _industrial():
    """Industrial −3%：真實 ledger 只引用基期觀測，不引用 NVIDIA 邊（fixture 預設會引用，改掉）。"""
    return _assumption("revenue_growth", "Industrial", -0.03, refs=(ACT_REF.ref,))


def _assumptions():
    rest = [a for a in _full_set() if a.driver != "revenue_growth"]
    return [_dc_assumption(), _industrial(), *rest]


def _artifacts(*, records=None):
    records = list(records) if records is not None else _assumptions()
    axes = [
        _axis("structural", {EDGE: ROLE_SUPPORTING}, kind=KIND_DETERMINISTIC, established=BUILD_AT),
        _axis("value_capture", {EDGE: ROLE_SUPPORTING, SNAP: ROLE_SUPPORTING}),
        ArtifactDependency(artifact_type=ARTIFACT_AXIS, artifact_id="earnings_exposure", label="Q3",
                           kind=KIND_JUDGMENT, established_at=JUDGED_AT, preset_state=MISSING,
                           preset_reason="unknown"),
        _axis("expectation_gap", {SNAP: ROLE_SUPPORTING}),
        ArtifactDependency(artifact_type="thesis", artifact_id=THESIS_ARTIFACT_ID, label="thesis",
                           kind=KIND_JUDGMENT, established_at=JUDGED_AT,
                           refs={EDGE: ROLE_SUPPORTING, SNAP: ROLE_SUPPORTING}, check_frequency_days=92),
    ]
    market = [ArtifactDependency(artifact_type="market_implied", artifact_id="market_implied_eps_growth",
                                 label="implied", kind=KIND_DETERMINISTIC, established_at=BUILD_AT,
                                 refs={SNAP: "observation"})]
    return records, axes + artifacts_from_assumptions(records, build_at=BUILD_AT) + market


def _resolve(changes=(), *, artifacts=None, observations=(), as_of=None, today=RESOLVE_DAY):
    if artifacts is None:
        _records, artifacts = _artifacts()
    return resolve_refresh(ticker="COHR", company_id="co:coherent", artifacts=artifacts, changes=changes,
                           observations=observations, as_of=as_of, today=today)


def _state(report, key: str) -> str:
    artifact = report.artifact(key)
    assert artifact is not None, f"{key} 不在 report：{[a.key for a in report.artifacts]}"
    return artifact.state


def _dc_id(report) -> str:
    return next(a.artifact_id for a in report.artifacts
                if a.artifact_type == ARTIFACT_ASSUMPTION and "Datacenter" in a.label and a.state != SUPERSEDED)


# ---------------------------------------------------------------------------
# 0. 契約
# ---------------------------------------------------------------------------

def test_state_vocabulary_is_closed_and_precedence_is_explicit() -> None:
    assert set(REFRESH_STATES) == {"current", "recalculate", "review_required", "invalidated",
                                   "stale", "superseded", "missing"}
    assert merge_states([]) == CURRENT
    assert merge_states([STALE, RECALCULATE]) == RECALCULATE
    assert merge_states([REVIEW_REQUIRED, STALE, RECALCULATE]) == REVIEW_REQUIRED
    assert merge_states([INVALIDATED, REVIEW_REQUIRED]) == INVALIDATED
    with pytest.raises(ContractViolation):
        merge_states([SUPERSEDED])                     # 終局 state 不參與合併
    with pytest.raises(ContractViolation, match="必須附 reasons"):
        AffectedArtifact(artifact_type=ARTIFACT_AXIS, artifact_id="x", label="x", state=REVIEW_REQUIRED)
    with pytest.raises(ContractViolation, match="change_type 未登記"):
        _event("digest_changed", "x")
    with pytest.raises(ContractViolation, match="target_artifact"):
        _event(DISPROOF_SIGNAL, "x")


def test_no_change_means_everything_current() -> None:
    report = _resolve()
    live = [a for a in report.artifacts if a.state not in (SUPERSEDED, MISSING)]
    assert live and all(a.state == CURRENT for a in live)
    assert report.overall == CURRENT and report.attention == ()


# ---------------------------------------------------------------------------
# 1. price-only：確定性的市場導出量重算，研究判斷與假設全部 current
# ---------------------------------------------------------------------------

def test_price_only_change_does_not_stale_research_judgment() -> None:
    report = _resolve([_event(MARKET_PRICE, SNAP, old_version="264.41", new_version="281.86",
                              material_fields=("price",), detail="price 264.41 → 281.86")])
    assert _state(report, "market_implied:market_implied_eps_growth") == RECALCULATE
    for key in ("axis:structural", "axis:value_capture", "axis:expectation_gap",
                f"thesis:{THESIS_ARTIFACT_ID}"):
        assert _state(report, key) == CURRENT, key
    assert all(a.state == CURRENT for a in report.artifacts
               if a.artifact_type == ARTIFACT_ASSUMPTION and a.state not in (SUPERSEDED, MISSING))
    assert report.overall == RECALCULATE


# ---------------------------------------------------------------------------
# 2. consensus revision：數值 gap 重算、Q4 複查、Q1／Q2 不動；calibration 依賴的假設複查並說明
# ---------------------------------------------------------------------------

def test_consensus_revision_recalculates_gap_and_reviews_q4_only() -> None:
    report = _resolve([_event(CONSENSUS, CONS_EPS, old_version="9.42", new_version="10.00",
                              material_fields=("eps",), detail="FY27 EPS 共識 9.42 → 10.00")])
    assert _state(report, "axis:expectation_gap") == REVIEW_REQUIRED
    assert _state(report, "axis:structural") == CURRENT
    assert _state(report, "axis:value_capture") == CURRENT
    # 營收假設沒有引用 EPS 共識 → current；稅率當然 current
    dc = report.artifact(f"{ARTIFACT_ASSUMPTION}:{_dc_id(report)}")
    assert dc.state == CURRENT
    # 換成營收共識：D&C 假設把它列為 calibration → review_required，理由必須明說
    report2 = _resolve([_event(CONSENSUS, CONS_REV, material_fields=("revenue",), detail="FY27 營收共識修正")])
    dc2 = report2.artifact(f"{ARTIFACT_ASSUMPTION}:{_dc_id(report2)}")
    assert dc2.state == REVIEW_REQUIRED
    assert any("calibrated relative to market consensus" in r for r in dc2.reasons)
    tax = next(a for a in report2.artifacts if "tax_rate" in a.label)
    assert tax.state == CURRENT


# ---------------------------------------------------------------------------
# 3. structural edge：Q1 重算、引用它的 Q2 與 D&C 假設複查、無關 heuristic 不動
# ---------------------------------------------------------------------------

def test_structural_edge_change_reviews_only_what_cites_it() -> None:
    report = _resolve([_event(GRAPH_EDGE, EDGE, material_fields=("substitutability",),
                              detail="substitutability 5 → 3")])
    assert _state(report, "axis:structural") == RECALCULATE
    assert _state(report, "axis:value_capture") == REVIEW_REQUIRED        # 引用了這條邊
    assert _state(report, "axis:expectation_gap") == CURRENT              # 沒引用
    dc = report.artifact(f"{ARTIFACT_ASSUMPTION}:{_dc_id(report)}")
    assert dc.state == REVIEW_REQUIRED and EDGE in dc.dependency_refs
    for label in ("tax_rate", "diluted_shares", "nci_attribution", "interest_and_other_net", "Industrial"):
        artifact = next(a for a in report.artifacts if label in a.label and a.state != SUPERSEDED)
        assert artifact.state == CURRENT, label


def test_single_edge_change_does_not_cascade_to_everything() -> None:
    report = _resolve([_event(GRAPH_EDGE, EDGE, detail="sole_source true → false")])
    live = [a for a in report.artifacts if a.state not in (SUPERSEDED, MISSING)]
    untouched = [a for a in live if a.state == CURRENT]
    assert len(untouched) >= 6, [(a.key, a.state) for a in live]


# ---------------------------------------------------------------------------
# 4. new guidance：只有 driver 直接相關的假設複查
# ---------------------------------------------------------------------------

def test_new_guidance_reviews_only_driver_relevant_assumptions() -> None:
    report = _resolve([_event(COMPANY_GUIDANCE, "engine_c://manual_observation/mo_guidance_q2",
                              effective_at=date(2026, 11, 10),
                              material_fields=("revenue_low", "revenue_high", "tax_rate_low", "tax_rate_high"),
                              detail="Q2 FY27 指引：營收與稅率")])
    by_label = {a.label: a for a in report.artifacts if a.artifact_type == ARTIFACT_ASSUMPTION
                and a.state != SUPERSEDED}
    assert by_label[next(k for k in by_label if "Datacenter" in k)].state == REVIEW_REQUIRED
    assert by_label[next(k for k in by_label if "Industrial" in k)].state == REVIEW_REQUIRED
    assert by_label[next(k for k in by_label if "tax_rate" in k)].state == REVIEW_REQUIRED
    assert by_label[next(k for k in by_label if "operating_margin_delta" in k)].state == CURRENT
    assert by_label[next(k for k in by_label if "diluted_shares" in k)].state == CURRENT
    assert by_label[next(k for k in by_label if "nci_attribution" in k)].state == CURRENT
    # 缺指引 ≠ 指引變了：沒有事件就沒有影響
    assert all(a.state == CURRENT for a in _resolve().artifacts if a.artifact_type == ARTIFACT_ASSUMPTION
               and a.state not in (SUPERSEDED, MISSING))


# ---------------------------------------------------------------------------
# 5. new actual：確定性輸出重算、heuristic proxy 複查、session 判斷型假設不因此重看
# ---------------------------------------------------------------------------

def test_new_actual_recalculates_bridge_and_reviews_heuristic_proxies() -> None:
    report = _resolve([_event(FINANCIAL_ACTUAL, "engine_c://manual_observation/mo_q1fy27",
                              effective_at=date(2026, 9, 30), material_fields=("revenue", "interest_and_other_net"),
                              detail="Q1 FY27 實際數")])
    for label in ("interest_and_other_net", "diluted_shares", "tax_rate", "nci_attribution"):
        artifact = next(a for a in report.artifacts if label in a.label and a.state != SUPERSEDED)
        assert artifact.state == REVIEW_REQUIRED, label
    dc = report.artifact(f"{ARTIFACT_ASSUMPTION}:{_dc_id(report)}")
    assert dc.state == CURRENT                       # session 判斷不因新實際數自動重看（那是 review condition 的事）
    assert _state(report, "axis:earnings_exposure") == MISSING          # unknown 沒有可推翻的判斷
    assert _state(report, "axis:value_capture") == REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# 6. assumption superseded：舊的 superseded、新的 current、下游重算、無關判斷 current
# ---------------------------------------------------------------------------

def test_superseded_assumption_is_historical_and_downstream_recalculates() -> None:
    old = _dc_assumption()
    new = parse_assumption_record(assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="revenue_growth",
        scope="Datacenter & Communications", value=0.50, basis="session_judgment", rationale="下修",
        evidence_refs=[EDGE, ACT_REF.ref], supersedes_id=old.assumption_id,
        created_at=datetime(2026, 9, 6, 9, 0, tzinfo=UTC), derivation="independent"))
    records = [old, new, _industrial(), *[a for a in _full_set() if a.driver != "revenue_growth"]]
    _r, artifacts = _artifacts(records=records)
    report = _resolve([_event(OPERATING_ASSUMPTION, new.assumption_id, related_refs=(old.assumption_id,),
                              at=new.created_at, material_fields=("revenue_growth",), detail="D&C 60% → 50%")],
                      artifacts=artifacts, today=date(2026, 9, 6))
    assert _state(report, f"{ARTIFACT_ASSUMPTION}:{old.assumption_id}") == SUPERSEDED
    assert _state(report, f"{ARTIFACT_ASSUMPTION}:{new.assumption_id}") == CURRENT
    assert _state(report, "axis:value_capture") == CURRENT
    assert _state(report, "axis:structural") == CURRENT
    assert _state(report, "axis:expectation_gap") == REVIEW_REQUIRED    # 內部觀點變了，Q4 要重看
    later = _resolve([_event(OPERATING_ASSUMPTION, "oa_future", related_refs=(new.assumption_id,), at=LATER,
                             detail="再次取代")], artifacts=artifacts, today=date(2026, 9, 6))
    tax = next(a for a in later.artifacts if "tax_rate" in a.label)
    assert tax.state == CURRENT


# ---------------------------------------------------------------------------
# 7. evidence removed／invalid：supporting evidence 撤回 → invalidated；解析不到 → invalidated
# ---------------------------------------------------------------------------

def test_retracted_supporting_evidence_invalidates_dependents() -> None:
    report = _resolve([_event(GRAPH_EDGE, EDGE, material_fields=("retracted",), detail="邊已撤回")])
    dc = report.artifact(f"{ARTIFACT_ASSUMPTION}:{_dc_id(report)}")
    assert dc.state == INVALIDATED
    assert _state(report, "axis:value_capture") == INVALIDATED
    assert _state(report, "axis:expectation_gap") == CURRENT             # 沒引用那條邊
    # 解析不到證據的假設由 ledger 選取（`select_assumptions`，不是模型）計數，refresh 把它標成 invalidated（前提不成立）
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：這一半原本靠 `build_fundamental_model` 跑選取；模型退役後由
    # builder 直接跑 `select_assumptions`，拒收原因經 `rejection` 交給 `artifacts_from_assumptions`。
    from alpha.fundamental.assumptions import select_assumptions

    broken = _assumption("tax_rate", "total", 0.19, basis="heuristic_proxy", refs=("graph://gone",))
    records = [broken, *[a for a in _assumptions() if a.driver != "tax_rate"]]
    _acc, selection = select_assumptions(records, target=TARGET, as_of=None, today=TODAY, evidence_index=_index())
    artifacts = artifacts_from_assumptions(records, build_at=BUILD_AT, rejection=dict(selection.rejected))
    report2 = _resolve(artifacts=artifacts)
    assert _state(report2, f"{ARTIFACT_ASSUMPTION}:{broken.assumption_id}") == INVALIDATED
    # 對照：證據解析得到的那幾條不受影響
    assert _state(report2, f"{ARTIFACT_ASSUMPTION}:{_dc_id(report2)}") == CURRENT


# ---------------------------------------------------------------------------
# 8. disproof signal：machine-readable review condition 對照觀測 → 不 current；不自動寫新假設
# ---------------------------------------------------------------------------

def test_review_condition_fires_from_observation_and_never_replaces_the_value() -> None:
    condition = {"metric": "segment_revenue", "scope": "Datacenter & Communications",
                 "period_end": "2026-12-31", "period_kind": "fiscal_quarter", "operator": "<",
                 "threshold": 1.85e9, "on_trigger": "review_required", "note": "下修至 +45%"}
    dc = _dc_assumption(review_conditions=[condition])
    assert dc.review_conditions and isinstance(dc.review_conditions[0], ReviewCondition)
    records = [dc, _industrial(), *[a for a in _full_set() if a.driver != "revenue_growth"]]
    _r, artifacts = _artifacts(records=records)
    # 尚無觀測 → 等待中，current
    waiting = _resolve(artifacts=artifacts)
    assert _state(waiting, f"{ARTIFACT_ASSUMPTION}:{dc.assumption_id}") == CURRENT
    assert any("等待中" in n for n in waiting.notes)
    # 觀測到 1.70B < 1.85B → review_required，理由帶人寫的下一步，值本身不變
    obs = MetricObservation(metric="segment_revenue", scope="Datacenter & Communications",
                            period_end=date(2026, 12, 31), period_kind="fiscal_quarter", value=1.70e9,
                            ref="engine_c://manual_observation/mo_q2fy27", observed_at=LATER)
    fired = _resolve(artifacts=artifacts, observations=[obs])
    hit = fired.artifact(f"{ARTIFACT_ASSUMPTION}:{dc.assumption_id}")
    assert hit.state == REVIEW_REQUIRED and any("下修至 +45%" in r for r in hit.reasons)
    assert dc.value == 0.60                                            # 值本身不變：引擎只標 state
    assert fired.changes and fired.changes[-1].change_type == DISPROOF_SIGNAL
    # 觀測不滿足條件 → current
    calm = _resolve(artifacts=artifacts, observations=[MetricObservation(
        metric="segment_revenue", scope="Datacenter & Communications", period_end=date(2026, 12, 31),
        period_kind="fiscal_quarter", value=1.95e9, ref="x", observed_at=LATER)])
    assert _state(calm, f"{ARTIFACT_ASSUMPTION}:{dc.assumption_id}") == CURRENT
    # on_trigger=invalidated 由條件自己宣告
    strict = _dc_assumption(review_conditions=[{**condition, "on_trigger": "invalidated"}])
    records2 = [strict, _industrial(), *[a for a in _full_set() if a.driver != "revenue_growth"]]
    _r2, artifacts2 = _artifacts(records=records2)
    assert _state(_resolve(artifacts=artifacts2, observations=[obs]),
                  f"{ARTIFACT_ASSUMPTION}:{strict.assumption_id}") == INVALIDATED


def test_external_disproof_signal_targets_the_named_artifact_only() -> None:
    report = _resolve([_event(DISPROOF_SIGNAL, "library://event_watches/ew_0099", target_artifact=THESIS_ARTIFACT_ID,
                              on_trigger="review_required", detail="第二家 CPO 外部光源供應商出現")])
    assert _state(report, f"thesis:{THESIS_ARTIFACT_ID}") == REVIEW_REQUIRED
    assert _state(report, "axis:value_capture") == REVIEW_REQUIRED      # thesis 級 disproof 動所有 session 軸
    assert all(a.state == CURRENT for a in report.artifacts
               if a.artifact_type == ARTIFACT_ASSUMPTION and a.state not in (SUPERSEDED, MISSING))


# ---------------------------------------------------------------------------
# 9. fiscal rollover：新目標期間被辨識、舊假設不沿用、理由說明需要新假設
# ---------------------------------------------------------------------------

# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`test_fiscal_rollover_is_named_and_old_assumptions_are_not_reused` 退役
# ——它跑 `build_fundamental_model` 看模型怎麼標會計期間推進；模型已刪。


# ---------------------------------------------------------------------------
# 10. historical as-of：未來的變化不得滲入過去；當時它是 current
# ---------------------------------------------------------------------------

def test_as_of_view_does_not_see_future_invalidation() -> None:
    change = _event(GRAPH_EDGE, EDGE, material_fields=("retracted",), at=datetime(2026, 9, 10, tzinfo=UTC))
    now = _resolve([change], today=date(2026, 9, 12))
    assert _state(now, "axis:value_capture") == INVALIDATED
    then = _resolve([change], as_of=date(2026, 9, 6), today=date(2026, 9, 12))
    assert _state(then, "axis:value_capture") == CURRENT
    assert then.excluded_changes == {"observed_after_as_of": 1}
    # as-of 早於判斷日 → 判斷不存在（excluded，不是 current）
    before = _resolve([change], as_of=date(2026, 9, 1), today=date(2026, 9, 12))
    assert before.artifact("axis:value_capture") is None
    assert before.excluded_artifacts["established_after_as_of"] >= 1


def test_assumptions_created_after_as_of_do_not_exist_at_that_time() -> None:
    """INV-6：T 之後才寫的假設在 T 的視角上不存在——由 `select_assumptions` 拒收（created_after_as_of），
    refresh 端把它預設成 missing，而不是拿當前假設冒充。"""
    from alpha.fundamental.assumptions import select_assumptions

    records = _assumptions()                                              # 全部寫於 2026-09-05
    _acc, selection = select_assumptions(records, target=TARGET, as_of=date(2026, 9, 1), today=TODAY,
                                         evidence_index=_index())
    assert selection.reasons.get("created_after_as_of") == len(records)
    artifacts = artifacts_from_assumptions(records, build_at=BUILD_AT, rejection=dict(selection.rejected))
    assert artifacts and all(a.preset_state == MISSING and "INV-6" in (a.preset_reason or "") for a in artifacts)
    # 對照：as-of 在寫入之後 → 全部可用
    _acc2, selection2 = select_assumptions(records, target=TARGET, as_of=date(2026, 9, 6), today=TODAY,
                                           evidence_index=_index())
    assert not selection2.reasons.get("created_after_as_of")


def test_changes_known_before_the_judgment_are_not_new_changes() -> None:
    earlier = _event(MARKET_PRICE, SNAP, at=JUDGED_AT - timedelta(days=1))
    report = _resolve([earlier])
    # market_implied 是 build 時點錨定，判斷前的變化早已納入 → current
    assert _state(report, "market_implied:market_implied_eps_growth") == CURRENT


# ---------------------------------------------------------------------------
# 11. freshness vs invalidation：stale 與 review_required 分得開，理由各自現形
# ---------------------------------------------------------------------------

def test_stale_is_schedule_and_review_required_is_evidence() -> None:
    late = date(2026, 12, 20)                                   # 判斷 09-04 ＋ 92 天已過
    stale = _resolve(today=late)
    thesis = stale.artifact(f"thesis:{THESIS_ARTIFACT_ID}")
    assert thesis.state == STALE and any("核查週期" in r for r in thesis.reasons)
    assert _state(stale, "axis:value_capture") == STALE
    assert all(a.state == CURRENT for a in stale.artifacts if a.artifact_type == ARTIFACT_ASSUMPTION
               and a.state not in (SUPERSEDED, MISSING))           # 假設沒有排程，不 stale
    both = _resolve([_event(GRAPH_EDGE, EDGE, detail="sub 5 → 3", at=datetime(2026, 12, 1, tzinfo=UTC))], today=late)
    q2 = both.artifact("axis:value_capture")
    assert q2.state == REVIEW_REQUIRED
    assert any(r.startswith("[stale]") for r in q2.reasons) and any(r.startswith("[review_required]") for r in q2.reasons)
    assert any(c.change_type == THESIS_REVIEW_DUE for c in both.changes)


# ---------------------------------------------------------------------------
# 12. determinism
# ---------------------------------------------------------------------------

def test_same_inputs_produce_identical_report() -> None:
    changes = [_event(GRAPH_EDGE, EDGE, detail="sub 5 → 3"), _event(MARKET_PRICE, SNAP), _event(CONSENSUS, CONS_EPS)]
    a = _resolve(changes)
    b = _resolve(list(reversed(changes)))
    assert a.digest == b.digest
    assert [(x.key, x.state, x.reasons) for x in a.artifacts] == [(x.key, x.state, x.reasons) for x in b.artifacts]


# ---------------------------------------------------------------------------
# 契約層：consensus 不得是 supporting；legacy 紀錄仍可讀且標 legacy
# ---------------------------------------------------------------------------

def test_same_period_consensus_cannot_be_supporting_evidence_but_legacy_records_still_parse() -> None:
    with pytest.raises(ContractViolation, match="provenance 循環"):
        assumption_record(company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="revenue_growth",
                          scope="Datacenter & Communications", value=0.6, basis="session_judgment", rationale="r",
                          evidence_refs=[EDGE, CONS_REV], created_at=datetime(2026, 9, 6, tzinfo=UTC),
                          derivation="independent")
    with pytest.raises(ContractViolation, match="至少要有一條 supporting"):
        assumption_record(company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="revenue_growth",
                          scope="Datacenter & Communications", value=0.6, basis="session_judgment", rationale="r",
                          evidence_refs=[], calibration_refs=[CONS_REV],
                          created_at=datetime(2026, 9, 6, tzinfo=UTC), derivation="independent")
    # 2026-09-05 的原始形狀：沒有角色欄位 → legacy；共識 ref 依前綴當 calibration，其餘當 supporting
    legacy_raw = {"record_version": "operating-assumption/v1", "company_id": "co:coherent", "ticker": "COHR",
                  "period_end": "2027-06-30", "period_kind": "fiscal_year", "driver": "revenue_growth",
                  "scope": "Datacenter & Communications", "value": 0.6, "unit": "ratio",
                  "basis": "session_judgment", "accounting_basis": "not_applicable", "rationale": "r",
                  "evidence_refs": [EDGE, CONS_REV], "created_at": "2026-09-05T11:55:05+00:00",
                  "author": "session", "supersedes_id": None, "retracted": False, "assumption_id": "oa_legacy0000000001"}
    legacy = parse_assumption_record(legacy_raw)
    assert legacy.provenance_semantics == "legacy"
    assert legacy.calibration_refs == (CONS_REV,) and legacy.supporting_refs == (EDGE,)
    v2 = _dc_assumption()
    assert v2.provenance_semantics == "v2" and v2.role_of(CONS_REV) == "calibration"


def test_guidance_and_missing_data_are_not_review_required() -> None:
    """AH／AI：缺指引不是變化——沒有事件就不得變成 review_required。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b）：「缺共識是 missing data（comparison 沒有 state）」那一半隨
    內部 vs 共識的數值比較退役；refresh 裡從此沒有 comparison 成果可言。
    """
    _r, artifacts = _artifacts()
    report = _resolve(artifacts=artifacts)
    assert report.artifact("expectation_comparison:eps") is None       # 退役的成果不得復活
    assert report.overall == CURRENT


# ---------------------------------------------------------------------------
# AD. 引擎不得 import 任何 LLM／搜尋／session 寫入
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_ROOTS = {"anthropic", "openai", "google", "requests", "httpx", "urllib", "neo4j", "yfinance",
                    "engine_b", "engine_c", "decision_lab", "sqlite3", "subprocess"}
_FORBIDDEN_TOKENS = ("WebSearch", "web_search", "session_assessor", "compose_signal", "anthropic", "openai",
                     "append_assumption_record", "save_watches", "Anthropic(")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def test_refresh_engine_never_imports_llm_clients_or_writers() -> None:
    """空跑檢查：在 alpha/refresh/resolver.py 加 `import anthropic` → 這條會紅。"""
    for path in (_ROOT / "alpha" / "refresh").glob("*.py"):
        assert not (_imports(path) & _FORBIDDEN_ROOTS), path
        source = path.read_text(encoding="utf-8")
        hits = [t for t in _FORBIDDEN_TOKENS if t in source]
        assert not hits, (path, hits)
