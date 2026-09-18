"""`AlphaInvestmentView` → `AnalystView`：**依消費者問句重新投影**，不重算任何東西。

## 這一支做什麼

`AlphaInvestmentView` 依資料結構排列（第 5 節共識、第 8 節橋、第 13 節估值、13a 報酬…）；
本模組把同一批 `Datum` **重新分組、重新排序、換上面向讀者的標籤**，讓打開一檔股票的人依序
讀到六個問句的答案。

## 這一支絕不做的事（`tests/test_analyst_view.py` 守著）

- **不新建任何 `Datum`。** panel 裡每一行的 `datum` 都是 read model 裡**同一個物件**（`is` 相等）。
  想在這裡「補一格」就必須先去 authority 補，這正是我們要的阻力。
- **沒有公式、沒有算術。** 全檔唯一的數值運算是排序鍵 `abs(既有敏感度)`——它不產生新值。
- **不判斷好壞。** `worst_status`／`readiness_class` 是宣告好的查表（`contracts.py`），
  這裡只呼叫它們。
- **不呼叫 LLM、不連 DB、不寫檔。** import 清單是這個承諾的可執行形式。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from briefing.alpha_view.contracts import (
    VALUELESS_STATUSES, AlphaInvestmentView, Datum, EvidenceItem, RefreshItem,
)

from .contracts import (
    BLOCKED, CORE_PANELS, OPTIONAL_PANELS, READY, READY_WITH_FLAGS, SCHEMA_VERSION, AnalystBlocker,
    AnalystLine, AnalystPanel, AnalystReadiness, AnalystView, RefreshSummary, WeakInput,
    readiness_class, worst_status,
)

#: refresh 引擎標成這些 state 的成果＝「還有事要做」。`current`／`superseded`／`missing` 不在此列
#: （`missing` 在這裡代表「這個視角下還沒建立」，由各 panel 自己的 status 表達，不重複告警）。
ATTENTION_STATES = ("recalculate", "review_required", "invalidated", "stale")

#: 直接餵進頭條那一串數字的成果種類——headline panel 只列這些的 attention，避免把整份 refresh 倒進頭條。
HEADLINE_ARTIFACTS = (
    "implied_return", "fair_value", "fair_value_gap", "horizon_assumption", "valuation_assumption",
)



def _absence_kinds(**metas: Any) -> dict[str, str | None]:
    """每個來源 section 的缺席語意——**照抄 `SectionMeta.effective_absence_kind`，不推論**。"""
    return {name: meta.effective_absence_kind for name, meta in metas.items()}


def _settled_by(**metas: Any) -> dict[str, str | None]:
    """每個來源 section 的 `settled_by`（`ab_*`）——同樣照抄，不推論（2026-09-13）。"""
    return {name: getattr(meta, "settled_by", None) for name, meta in metas.items()}


def _worst_reason(status: str, **metas: Any) -> str | None:
    """panel 的 reason 要來自**造成這個 status 的那一段**，不是固定綁某一段。

    事發（2026-09-13，HEXA-B.ST）：`earnings_bridge` 算成功、`valuation` 缺 target multiple，
    於是 `why` panel 的 status 是 `missing`（取三段最差）而 reason 取自 earnings_bridge ＝ `None`。
    使用者端看到的是「why：missing」沒有下文，而 `absence_kind` 明明宣告了 `not_yet_recorded`。
    ⚠ 這正是 `AGENTS.md` APP 呈現契約禁的形狀：**缺席由產生它的那段程式自己宣告**——
    固定取第一段等於讓 A 段替 B 段的缺席發言，而 A 段根本沒有缺席。
    ⚠ 這**不是**放寬：status 一個字都沒動，改的只是「這句話由誰說」（L12：先分開再各自定規則）。
    fallback 保留舊行為（任一段有 reason 就用它），因為「沒有任何理由」與「理由在別段」不同。
    """
    for meta in metas.values():
        if meta.status == status and meta.reason:
            return meta.reason
    for meta in metas.values():
        if meta.reason:
            return meta.reason
    return None


def _line(key: str, label: str, datum: Datum, role: str) -> AnalystLine:
    return AnalystLine(key=key, display_label=label, datum=datum, role=role)


def _lines(data: Iterable[Datum], role: str, *, prefix: str = "") -> tuple[AnalystLine, ...]:
    """一批既有 `Datum` 直接變成一批行；標籤沿用 `Datum.label`（authority 已經寫好的說法）。"""
    return tuple(_line(f"{prefix}{d.key}", d.label, d, role) for d in data)


def _attention(view: AlphaInvestmentView, *, artifact_types: Sequence[str] | None = None
               ) -> tuple[RefreshItem, ...]:
    """需要動作的研究成果。`artifact_types` 給定時只留那幾種——這是**篩選**，不是重新判定 state。"""
    items = [i for i in view.refresh_status.items if i.state in ATTENTION_STATES]
    if artifact_types is not None:
        items = [i for i in items if i.artifact_type in artifact_types]
    return tuple(items)


def _sensitivity_magnitude(datum: Datum) -> float:
    """排序鍵：既有敏感度的 |相對變動|。**只讀，不算**——沒有可讀的數就排在最後（不是 0，是「不參與排序」）。"""
    value = datum.value
    if isinstance(value, Mapping):
        for field_name in ("fair_value_relative", "delta_fair_value", "delta_eps"):
            candidate = value.get(field_name)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return abs(float(candidate))
    return float("-inf")


def _ordered_sensitivities(data: Sequence[Datum]) -> tuple[Datum, ...]:
    """依既有 |相對變動| 由大到小。排序不改變任何數字，也不是新的 attribution model。"""
    return tuple(sorted(data, key=_sensitivity_magnitude, reverse=True))


def _assumption_id(datum: Datum) -> str | None:
    deps = datum.dependencies or {}
    value = deps.get("assumption_id")
    return str(value) if value else None


def _evidence_for(view: AlphaInvestmentView, data: Iterable[Datum]) -> tuple[EvidenceItem, ...]:
    """這些格引用到的證據（依 evidence index 的原順序）。純查表，不重新評級。"""
    wanted: set[str] = set()
    for datum in data:
        wanted.update(datum.evidence_refs)
    return tuple(item for item in view.evidence.index if item.ref in wanted)


# ---------------------------------------------------------------------------
# 脆弱輸入：每一條都由一條**宣告好的列入規則**挑進來（見 `WEAK_INPUT_RULES`）
# ---------------------------------------------------------------------------

def _weak_inputs(view: AlphaInvestmentView, assumptions: Sequence[Datum],
                 sensitivities: Sequence[Datum]) -> tuple[WeakInput, ...]:
    out: list[WeakInput] = []
    seen: set[str] = set()

    def add(datum: Datum, rule: str, label: str | None = None) -> None:
        if datum.key in seen:
            return
        seen.add(datum.key)
        out.append(WeakInput(key=datum.key, display_label=label or datum.label, datum=datum, rule=rule))

    # 1) 既有敏感度中 |Δ| 最大的那一條 → 指回它所敏感的那條假設（指不回去就指自己）
    if sensitivities and _sensitivity_magnitude(sensitivities[0]) > float("-inf"):
        top = sensitivities[0]
        target_id = _assumption_id(top)
        target = next((a for a in assumptions if _assumption_id(a) == target_id), None) if target_id else None
        add(target or top, "largest_modeled_sensitivity")

    # 2) refresh 已標記需要動作的成果 → 對應的假設格
    flagged = {i.artifact_id for i in view.refresh_status.items if i.state in ATTENTION_STATES}
    for datum in assumptions:
        if _assumption_id(datum) in flagged:
            add(datum, "refresh_flagged")

    # 3)／4) 知識種類本身就弱的輸入（先粗略代理，再 session 判斷）
    for basis, rule in (("heuristic_proxy", "heuristic_proxy_input"),
                        ("session_judgment", "session_judgment_input")):
        for datum in assumptions:
            if datum.basis == basis:
                add(datum, rule)

    # 5) AlphaSignal 已算出的最弱軸／6) 未知軸——不是本層重算，是抄 `signal.weakest_axis` 與各軸 status
    weakest = view.identity.signal.weakest_axis
    for score in view.variant_view.scores:
        if weakest and score.key == f"{weakest}_score":
            add(score, "weakest_known_axis")
    for score in view.variant_view.scores:
        if not score.is_known:
            add(score, "unknown_axis")
    return tuple(out)


# ---------------------------------------------------------------------------
# 五個 panel
# ---------------------------------------------------------------------------

def _headline_panel(view: AlphaInvestmentView) -> AnalystPanel:
    ir, va, rs = view.implied_return, view.valuation, view.refresh_status
    numbers = (
        _line("current_price", "現價", ir.current_price, "headline_number"),
        _line("fair_value", "Future target value（fair value）", ir.fair_value, "headline_number"),
        _line("value_date", "target value 是哪一天的值", ir.value_date, "headline_number"),
        _line("horizon", "Horizon（判斷：何時實現）", ir.horizon, "headline_number"),
        _line("price_return", "隱含價格報酬（simple）", ir.price_return, "headline_number"),
        _line("annualized_price_return", "隱含價格報酬（年化）", ir.annualized_price_return, "headline_number"),
        # 2026-09-09 P2：兩桿拆解跟在總報酬旁邊——使用者要一眼分得出「負的是因為我們 EPS 比共識低，
        # 還是因為我們的倍數比市場低」。拆不出來就 missing，不影響前面幾格。
        _line("eps_contribution", "其中：EPS 差異貢獻（我們 vs 共識）", ir.eps_contribution, "headline_number"),
        _line("multiple_contribution", "其中：倍數差異貢獻（我們 vs 市場倍數）", ir.multiple_contribution, "headline_number"),
    )
    context_lines = (
        _line("return_attribution", "兩桿拆解整包（恆等式、市場倍數、原則提醒）", ir.attribution, "headline_context"),
        _line("return_convention", "報酬語意", ir.return_convention, "headline_context"),
        _line("horizon_window", "Horizon 區間", ir.horizon_window, "headline_context"),
        _line("fair_value_gap", "Fair value 與現價的差（不是報酬）", va.fair_value_gap, "headline_context"),
        _line("total_return", "總報酬（含股利）", ir.total_return, "headline_context"),
        _line("probability_weighted_return", "機率加權期望報酬", ir.probability_weighted_return, "headline_context"),
        # authority 自己組好的一句話住在 `epistemics.one_sentence`；consumer 只是把它挪到最前面呈現，
        # **不自己造句**——造句就是在 read model 之外生出第二種說法。
        _line("epistemics_one_sentence", "一句話（authority 自組）", ir.epistemics, "headline_context"),
    ) + ((_line("target_reached", ir.target_reached.label, ir.target_reached, "headline_context"),)
         if ir.target_reached is not None else ())
    statuses = {"implied_return": ir.meta.status, "valuation": va.meta.status}
    kinds = _absence_kinds(implied_return=ir.meta, valuation=va.meta)
    settled = _settled_by(implied_return=ir.meta, valuation=va.meta)
    return AnalystPanel(
        key="headline", title="頭條：現價 → future target value → 隱含報酬",
        questions=("q4_implied_return",),
        status=worst_status(list(statuses.values())), optional=False,
        source_sections=("implied_return", "valuation", "refresh_status"),
        source_statuses=statuses, source_absence_kinds=kinds, source_settled_by=settled,
        lines=numbers + context_lines,
        attention=_attention(view, artifact_types=HEADLINE_ARTIFACTS),
        attention_scope="只列頭條這幾格自己的成果（" + "、".join(HEADLINE_ARTIFACTS) + "）",
        attention_total=len(_attention(view)),
        notes=ir.is_not,
        context={"period": ir.period, "period_end": ir.period_end,
                 "accounting_basis": va.accounting_basis,
                 "refresh_overall": rs.overall, "refresh_counts": dict(rs.counts),
                 "capability": ir.meta.capability},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             implied_return=ir.meta, valuation=va.meta),
    )


def _fundamental_panel(view: AlphaInvestmentView) -> AnalystPanel:
    inf, cs, eg = view.internal_fundamentals, view.consensus, view.expectation_gap
    same_period_suffix = f"_{inf.period}" if inf.period else None
    same, other = [], []
    for datum in cs.fiscal_items:
        (same if same_period_suffix and datum.key.endswith(same_period_suffix) else other).append(datum)
    lines = (
        _lines(inf.items, "internal")
        + _lines(same, "consensus_same_period")
        + _lines(other, "consensus_other_period")
        + _lines(cs.items, "market_context")
        + _lines(eg.proxies, "market_proxy")
        + _lines(eg.numeric_comparisons, "comparison")
        + ((_line("opinion_stance", eg.opinion_stance.label, eg.opinion_stance, "comparison"),)
           if eg.opinion_stance is not None else ())
        + ((_line("reverse_bridge", eg.reverse_bridge.label, eg.reverse_bridge, "comparison"),)
           if eg.reverse_bridge is not None else ())
        + ((_line("multiple_derivation", eg.multiple_derivation.label,
                  eg.multiple_derivation, "comparison"),)
           if eg.multiple_derivation is not None else ())
        + ((_line("gap_closure", eg.gap_closure.label, eg.gap_closure, "comparison"),)
           if eg.gap_closure is not None else ())
        + ((_line("consensus_series", eg.consensus_series.label, eg.consensus_series, "market_context"),)
           if eg.consensus_series is not None else ())
        + (_line("internal_vs_consensus", eg.internal_vs_consensus.label, eg.internal_vs_consensus, "comparison"),
           _line("internal_vs_price_implied", eg.internal_vs_price_implied.label,
                 eg.internal_vs_price_implied, "comparison"))
    )
    statuses = {"internal_fundamentals": inf.meta.status, "consensus": cs.meta.status,
                "expectation_gap": eg.meta.status}
    kinds = _absence_kinds(internal_fundamentals=inf.meta, consensus=cs.meta, expectation_gap=eg.meta)
    return AnalystPanel(
        key="fundamental", title="基本面：我們預測什麼／市場預測什麼／差異在哪",
        questions=("q1_internal", "q2_market", "q3_gap"),
        status=worst_status(list(statuses.values())), optional=False,
        source_sections=("internal_fundamentals", "consensus", "expectation_gap"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        # ⚠ 共識段的 warnings 也要進來：「forward 是相對標籤不是會計年度身分」這條警告
        # 正是 2026-09-07 rollover 污染事故的判準，藏在 section 裡等於沒有（INV-3）。
        notes=(cs.coverage_note,) + inf.meta.warnings + cs.meta.warnings,
        context={"period": inf.period, "period_end": inf.period_end,
                 "base_period_end": inf.base_period_end, "accounting_basis": inf.accounting_basis,
                 "same_period_rule": "只有同期、同口徑、同幣別的共識才與內部相減；其他期間只呈現，不比較"},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             expectation_gap=eg.meta, internal_fundamentals=inf.meta,
                             consensus=cs.meta),
    )


def _why_panel(view: AlphaInvestmentView) -> AnalystPanel:
    eb, va, ir = view.earnings_bridge, view.valuation, view.implied_return
    assumptions = tuple(eb.assumptions) + tuple(va.assumptions) + (ir.horizon,)
    sensitivities = _ordered_sensitivities(va.sensitivities)
    lines = (
        _lines(assumptions, "assumption")
        + _lines(sensitivities, "sensitivity")
        + _lines(va.trace, "trace", prefix="valuation:")
        + _lines(ir.trace, "trace", prefix="implied_return:")
        + (_line("valuation_epistemics", "估值：多少是算術、多少是判斷", va.epistemics, "epistemics"),
           _line("implied_return_epistemics", "報酬：多少是算術、多少是判斷", ir.epistemics, "epistemics"))
    )
    statuses = {"earnings_bridge": eb.meta.status, "valuation": va.meta.status,
                "implied_return": ir.meta.status}
    kinds = _absence_kinds(earnings_bridge=eb.meta, valuation=va.meta, implied_return=ir.meta)
    return AnalystPanel(
        key="why", title="怎麼算到這裡：假設、敏感度、算式、證據",
        questions=("q5_fragile",),
        status=worst_status(list(statuses.values())), optional=False,
        source_sections=("earnings_bridge", "valuation", "implied_return"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        weak_inputs=_weak_inputs(view, assumptions, sensitivities),
        evidence=_evidence_for(view, assumptions + (ir.current_price, ir.fair_value, ir.price_return)),
        notes=va.meta.warnings + ir.meta.warnings,
        context={"period": va.period, "accounting_basis": va.accounting_basis,
                 "sensitivity_order": "依既有 |相對變動| 由大到小；排序不改變任何數字，也不是新的 attribution model",
                 "assumption_selection": None if eb.selection is None else {
                     "input": eb.selection.input_count, "accepted": eb.selection.accepted_count,
                     "filtered": eb.selection.filtered_count, "reasons": dict(eb.selection.reasons)}},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             earnings_bridge=eb.meta, valuation=va.meta,
                             implied_return=ir.meta),
    )


def _research_panel(view: AlphaInvestmentView) -> AnalystPanel:
    vv, fs, ct, rs = view.variant_view, view.falsification, view.catalysts, view.refresh_status
    signal = view.identity.signal
    lines = (
        (_line("thesis", "Thesis", vv.thesis, "thesis"),
         _line("variant_view", "Variant view（我們與市場的看法差在哪）", vv.variant_view, "thesis"),
         _line("direction", "方向", vv.direction, "thesis"),
         _line("confidence", "信心", vv.confidence, "thesis"),
         _line("expected_horizon", "研究判斷的預期期間", vv.expected_horizon, "thesis"),
         _line("decision_store_variant_perception", vv.decision_store_variant_perception.label,
               vv.decision_store_variant_perception, "thesis"))
        + _lines(vv.scores, "score")
        + (_line("thesis_status", "Thesis lifecycle", fs.thesis_status, "lifecycle"),
           _line("expiry_watch", "到期監看", fs.expiry_watch, "lifecycle"),
           _line("narrative_disproof", fs.narrative_disproof.label, fs.narrative_disproof, "lifecycle"),
           _line("automatic_invalidation", fs.automatic_invalidation.label,
                 fs.automatic_invalidation, "lifecycle"),
           _line("catalyst_watch_state", ct.watch_state.label, ct.watch_state, "lifecycle"),
           _line("catalyst_expiry", ct.expiry.label, ct.expiry, "lifecycle"),
           _line("catalyst_quantitative_link", ct.quantitative_link.label, ct.quantitative_link, "lifecycle"))
    )
    statuses = {"variant_view": vv.meta.status, "falsification": fs.meta.status,
                "catalysts": ct.meta.status, "refresh_status": rs.meta.status}
    kinds = _absence_kinds(variant_view=vv.meta, falsification=fs.meta, catalysts=ct.meta,
                           refresh_status=rs.meta)
    return AnalystPanel(
        key="research", title="研究現況：thesis、催化劑、什麼會推翻它、什麼需要重看",
        questions=("q6_change",),
        status=worst_status(list(statuses.values())), optional=False,
        source_sections=("variant_view", "falsification", "catalysts", "refresh_status"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        catalysts=ct.structured, checkpoints=ct.checkpoints, disproofs=fs.conditions,
        attention=_attention(view), attention_total=len(_attention(view)), risks=vv.risks,
        notes=tuple(ct.problems) + tuple(rs.notes),
        context={"has_signal": signal.has_signal, "judged_at": signal.judged_at,
                 "is_incomplete": signal.is_incomplete, "known_axes": list(signal.known_axes),
                 "weakest_axis": signal.weakest_axis, "context_matches": signal.context_matches,
                 "signal_refresh_state": signal.refresh_state,
                 "research_status": view.identity.lifecycle.research_status,
                 "thesis_lifecycle_status": view.identity.lifecycle.thesis_lifecycle_status,
                 "thesis_next_check": view.identity.lifecycle.thesis_next_check},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             variant_view=vv.meta, falsification=fs.meta,
                             catalysts=ct.meta, refresh_status=rs.meta),
    )


def _brief_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """投資人短評（optional）：七句＋一把尺＋一顆燈。**每一格都是 read model 的同一個 Datum**。"""
    ib = view.investor_brief
    lines = (tuple(_line(d.key, d.label, d, "brief") for d in ib.slots)
             + (_line("brief_scale", ib.scale.label, ib.scale, "brief"),
                _line("brief_status_light", ib.status_light.label, ib.status_light, "brief")))
    return AnalystPanel(
        key="brief", title="投資人短評：這檔在賭什麼（optional）",
        questions=("q0_story",),
        status=ib.meta.status, optional=True,
        source_sections=("investor_brief",), source_statuses={"investor_brief": ib.meta.status},
        source_absence_kinds=_absence_kinds(investor_brief=ib.meta),
        lines=lines, notes=ib.is_not,
        evidence=_evidence_for(view, ib.slots),
        context={"capability": ib.meta.capability, "brief_id": ib.brief_id,
                 "available": ib.meta.status not in VALUELESS_STATUSES,
                 "optional_rule": "短評是 optional：沒寫只表示「還沒寫短評」，不代表這檔研究不完整；"
                                  "文字是研究 session 的判斷（append-only），數字由既有 Datum 填入，不得手打"},
        reason=ib.meta.reason,
    )


def _argument_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """論證層（optional）：六段。**每一格都是 read model 的同一個 Datum**，本層不造句。"""
    ag = view.argument
    lines = tuple(_line(d.key, d.label, d, "paragraph") for d in ag.paragraphs)
    return AnalystPanel(
        key="argument", title="為什麼這樣想：鏈、數字、市場、賭注、風險、時間表（optional）",
        questions=("q0_argument",),
        status=ag.meta.status, optional=True,
        source_sections=("argument",), source_statuses={"argument": ag.meta.status},
        source_absence_kinds=_absence_kinds(argument=ag.meta),
        lines=lines, notes=ag.is_not,
        evidence=_evidence_for(view, ag.paragraphs),
        context={"capability": ag.meta.capability, "available": ag.meta.status not in VALUELESS_STATUSES,
                 "optional_rule": "論證層是投影：算術與圖的敘述由句型組、判斷的長文照抄；沒有它不影響判讀完不完整"},
        reason=ag.meta.reason,
    )


def _overlay_panel(ps, *, role: str, key_ns: str, value_ns: str) -> tuple:
    """一個 overlay scenario 的 lines。**賭注與下檔共用**（D2，2026-09-18）。

    ⚠ line 的 **key 前綴**（`payoff_*`／`variant_*` vs `downside_*`）是這一行的身分，
    APP 與 `PLAIN_LINE` 都以它為準；section 的**欄位名**在 2026-09-18 改成中性的
    `scenario_*`（一個型別、兩個 scenario）。兩者刻意脫鉤——否則改欄位名就會改到 APP 的 key。
    """
    return (
        _line(f"{key_ns}_scenario", ps.scenario.label, ps.scenario, role),
        _line(f"{value_ns}_internal_eps", ps.scenario_internal_eps.label, ps.scenario_internal_eps, role),
        _line(f"{value_ns}_fair_value", ps.scenario_fair_value.label, ps.scenario_fair_value, role),
        _line(f"{key_ns}_value_date", ps.value_date.label, ps.value_date, role),
        _line(f"{key_ns}_return", ps.payoff_return.label, ps.payoff_return, role),
        _line(f"annualized_{key_ns}_return", ps.annualized_payoff_return.label, ps.annualized_payoff_return, role),
        _line(f"{key_ns}_eps_contribution", ps.eps_contribution.label, ps.eps_contribution, role),
        _line(f"{key_ns}_multiple_contribution", ps.multiple_contribution.label, ps.multiple_contribution, role),
        _line(f"base_fair_value_for_{key_ns}", ps.base_fair_value.label, ps.base_fair_value, role),
        _line(f"base_price_return_for_{key_ns}", ps.base_price_return.label, ps.base_price_return, role),
        _line(f"{key_ns}_one_sentence", "一句話（authority 自組）", ps.epistemics, role),
    ) + _lines(ps.overrides, "override")


def _bet_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """賭注（optional）：variant scenario 的 payoff。**每一格都是 read model 的同一個 Datum**，本層不算。"""
    ps = view.payoff_scenario
    lines = _overlay_panel(ps, role="bet", key_ns="payoff", value_ns="variant")
    return AnalystPanel(
        key="bet", title="賭注：如果我們的差異看法對了（optional）",
        questions=("q7_payoff",),
        status=ps.meta.status, optional=True,
        source_sections=("payoff_scenario",), source_statuses={"payoff_scenario": ps.meta.status},
        source_absence_kinds=_absence_kinds(payoff_scenario=ps.meta),
        lines=lines, notes=ps.is_not,
        evidence=_evidence_for(view, ps.overrides),
        context={"capability": ps.meta.capability, "period": ps.period, "period_end": ps.period_end,
                 "available": ps.meta.status not in VALUELESS_STATUSES,
                 "override_count": len(ps.overrides),
                 "optional_rule": "賭注是 optional：沒寫 variant 假設只表示「還沒寫賭注」，不代表這檔研究不完整，"
                                  "也不得補一個 bull case；每條 variant 假設必須指得出 supporting 證據"},
        reason=ps.meta.reason,
    )


def _downside_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """判斷錯了值多少（optional，D2 2026-09-18）：downside scenario 走**同一條橋**的結果。

    ⚠ 它與 `bet` 逐格對稱、共用 `_overlay_panel`。兩份各自手寫的 panel 會在某次改動後
    悄悄長出不同的格，而使用者要把這兩個數字並排讀——那正是短評那把尺的兩端。
    """
    ds = view.downside
    lines = _overlay_panel(ds, role="bet", key_ns="downside", value_ns="downside")
    return AnalystPanel(
        key="downside", title="判斷錯了值多少：如果反證成真（optional）",
        questions=("q7_payoff",),
        status=ds.meta.status, optional=True,
        source_sections=("downside",), source_statuses={"downside": ds.meta.status},
        source_absence_kinds=_absence_kinds(downside=ds.meta),
        lines=lines, notes=ds.is_not,
        evidence=_evidence_for(view, ds.overrides),
        context={"capability": ds.meta.capability, "period": ds.period, "period_end": ds.period_end,
                 "available": ds.meta.status not in VALUELESS_STATUSES,
                 "override_count": len(ds.overrides),
                 "optional_rule": "下檔是 optional：沒寫 downside 假設只表示「還沒寫」，不代表這檔研究不完整，"
                                  "也**不得補一個 bear case**；每條 downside 假設必須指得出 supporting 證據"},
        reason=ds.meta.reason,
    )


def _wipeout_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """歸零旗標（optional，D2 2026-09-18）：四盞燈逐盞一行。

    ⚠ 這個 panel **一個顏色都不判**——顏色、理由句、規則與輸入全部照抄 `alpha.wipeout`
    經由 read model 帶過來的 `Datum`。呈現層自己判色就會立刻長出第二套規則（L16）。
    """
    wf = view.wipeout_flags
    lines = _lines(wf.lanes, "wipeout")
    return AnalystPanel(
        key="wipeout", title="會不會歸零：四盞燈（optional）",
        questions=("q7_payoff",),
        status=wf.meta.status, optional=True,
        source_sections=("wipeout_flags",), source_statuses={"wipeout_flags": wf.meta.status},
        source_absence_kinds=_absence_kinds(wipeout_flags=wf.meta),
        lines=lines, notes=wf.is_not,
        context={"capability": wf.meta.capability, "tally": dict(wf.tally),
                 "available": wf.meta.status not in VALUELESS_STATUSES,
                 "unlit_rule": "灰燈＝這一項沒量到，**不是**綠燈；每盞灰燈自己說了是哪一種沒有"
                               "（`absence_kind`），呈現層不得 parse 理由句去猜（L16）"},
        reason=wf.meta.reason,
    )


def _entry_panel(view: AlphaInvestmentView) -> AnalystPanel:
    el = view.entry_logic
    lines = (
        _line("criterion", "要求報酬判準（investor policy）", el.criterion, "entry"),
        _line("required_annualized_return", "要求年化報酬", el.required_annualized_return, "entry"),
        _line("entry_price", "Analytical entry threshold（門檻價）", el.entry_price, "entry"),
        _line("price_to_entry_gap", "現價相對門檻價", el.price_to_entry_gap, "entry"),
        _line("hurdle_comparison", "算術比較", el.hurdle_comparison, "entry"),
        _line("assessment", "這次評估能不能當 clean 讀", el.assessment, "entry"),
        _line("current_annualized_implied_return", "目前年化隱含報酬（照抄頭條）",
              el.current_annualized_implied_return, "entry"),
    )
    return AnalystPanel(
        key="entry", title="Entry threshold（optional）",
        questions=("q4_implied_return",),
        status=el.meta.status, optional=True,
        source_sections=("entry_logic",), source_statuses={"entry_logic": el.meta.status},
        source_absence_kinds=_absence_kinds(entry_logic=el.meta),
        lines=lines, notes=el.is_not,
        context={"capability": el.meta.capability,
                 "available": el.meta.status not in VALUELESS_STATUSES,
                 "optional_rule": "EntryCriterion 不是必填資料，也不是 research completeness gate："
                                  "沒有 hurdle 只表示 optional entry threshold unavailable，"
                                  "不代表這檔研究不完整，也不得補 10%／15%／20%"},
        reason=el.meta.reason,
    )


# ---------------------------------------------------------------------------
# readiness ＋ 整份 view
# ---------------------------------------------------------------------------

# ⚠ 兩份清單都**讀 SSOT**，不手寫（L16：分類有 SSOT 時要讓它跟著資料走）。
# 事發（2026-09-18）：這句話原本把 optional 逐字寫成「brief／argument／bet／entry」，
# 而 `OPTIONAL_PANELS` 在 D2 那輪就已經多了 `downside`——**畫面上少印一個 panel 名，
# 沒有任何東西會變紅**，它只是安靜地說了一句假話。
_READINESS_RULE = (
    f"只看核心 panel（{'／'.join(CORE_PANELS)}）："
    "全部有內容（available／partial）＝ready；"
    "有內容但至少一段被標為 stale／review_required／not_applicable＝ready_with_flags；"
    "至少一段缺內容（missing／invalidated／not_modeled／insufficient_evidence）＝blocked。"
    f"**optional panel（{'／'.join(OPTIONAL_PANELS)}）一律不參與**"
    "——沒有短評、沒有賭注、沒有下檔、沒有歸零旗標、沒有 entry criterion 都不會讓 readiness 變差。"
)


def _readiness(panels: Mapping[str, AnalystPanel]) -> AnalystReadiness:
    flags: list[str] = []
    blockers: list[str] = []
    blocker_details: list[AnalystBlocker] = []
    flag_details: list[AnalystBlocker] = []
    for name in CORE_PANELS:
        panel = panels[name]
        bucket = readiness_class(panel.status)
        detail = f"{name}：{panel.status}" + (f"（{panel.reason}）" if panel.reason else "")
        # 同一件事的兩種形式：字串給人讀，`AnalystBlocker` 給機器讀。**不是兩份判斷**——
        # 兩者都由同一個迴圈、同一個 bucket 決定，長度不同會在型別層被擋下。
        item = AnalystBlocker(panel=name, status=panel.status, absence_kind=panel.absence_kind,
                              settled=panel.absence_is_settled, reason=panel.reason)
        if bucket == BLOCKED:
            blockers.append(detail)
            blocker_details.append(item)
        elif bucket == READY_WITH_FLAGS:
            flags.append(detail)
            flag_details.append(item)
    unavailable = tuple(f"{name}：{panels[name].status}" for name in OPTIONAL_PANELS
                        if panels[name].status in VALUELESS_STATUSES)
    state = BLOCKED if blockers else (READY_WITH_FLAGS if flags else READY)
    return AnalystReadiness(
        state=state, core_panels=CORE_PANELS, optional_panels=OPTIONAL_PANELS,
        flags=tuple(flags), blockers=tuple(blockers), optional_unavailable=unavailable,
        rule=_READINESS_RULE, blocker_details=tuple(blocker_details), flag_details=tuple(flag_details),
    )


def _limits(view: AlphaInvestmentView) -> tuple[str, ...]:
    """「這份判讀不是什麼」——全部抄自各 authority 已經寫好的 `is_not`／`gap_is_not`，去重保序。"""
    fixed = (
        "不是 buy／sell：系統的終點是隱含報酬與（optional 的）門檻價，不是動作。",
        "不是部位尺寸或配置：買多少、什麼時候買由使用者自行判斷並手動下單。",
        "不是跨標的機會排序：本畫面只看一檔；瓶頸排序的唯一權威是 rank_bottlenecks。",
    )
    everything: list[str] = list(fixed)
    everything += list(view.implied_return.is_not)
    everything += list(view.valuation.gap_is_not)
    everything += list(view.entry_logic.is_not)
    everything += list(view.payoff_scenario.is_not)
    everything += list(view.investor_brief.is_not)
    everything += list(view.argument.is_not)
    # D2（2026-09-18）：`downside` 由 `NotModeledSection` 換成與賭注對稱的 overlay，
    # 所以「不是什麼」改從 `is_not` 取——`DOWNSIDE_IS_NOT` 第一句逐字就是「不是 bear case」。
    everything += list(view.downside.is_not)
    # D2（2026-09-18）：歸零旗標的四條「不是什麼」——尤其「綠燈不是查過都沒事的保證」。
    everything += list(view.wipeout_flags.is_not)
    return tuple(dict.fromkeys(everything))


def build_analyst_view(view: AlphaInvestmentView) -> AnalystView:
    """把 canonical read model 投影成 analyst 判讀畫面。純函式、確定性、可預先 materialize。"""
    panels = {
        "headline": _headline_panel(view),
        "fundamental": _fundamental_panel(view),
        "why": _why_panel(view),
        "research": _research_panel(view),
        "entry": _entry_panel(view),
        "bet": _bet_panel(view),
        "downside": _downside_panel(view),
        "wipeout": _wipeout_panel(view),
        "brief": _brief_panel(view),
        "argument": _argument_panel(view),
    }
    rs = view.refresh_status
    ident = view.identity
    return AnalystView(
        schema_version=SCHEMA_VERSION, source_schema_version=view.schema_version,
        ticker=ident.ticker, company_id=ident.company_id, company_label=ident.company_label,
        as_of=ident.as_of, point_in_time_mode=ident.point_in_time_mode,
        generated_on=ident.generated_on, research_context_digest=ident.research_context_digest,
        headline=panels["headline"], fundamental=panels["fundamental"], why=panels["why"],
        research=panels["research"], entry=panels["entry"], bet=panels["bet"],
        downside=panels["downside"], wipeout=panels["wipeout"], brief=panels["brief"],
        argument=panels["argument"],
        readiness=_readiness(panels),
        refresh=RefreshSummary(overall=rs.overall, counts=dict(rs.counts),
                               change_detection=rs.change_detection,
                               judged_context_matches=rs.judged_context_matches,
                               attention=_attention(view),
                               notes=rs.notes),
        limits=_limits(view), warnings=view.warnings,
    )


__all__ = ["ATTENTION_STATES", "build_analyst_view"]
