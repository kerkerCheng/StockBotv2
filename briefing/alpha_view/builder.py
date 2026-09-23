"""`build_alpha_investment_view()`——把既有 authority 的輸出**組裝**成 canonical read model。

## 這裡只做五件事：選取、正規化、語意標註、組裝、序列化

- **不重算**：Q1 來自 `alpha.context.structural_score`、Q2–Q5 來自 `session_assessor`、
  瓶頸排序來自 `rank_bottlenecks()`（經 provider）、估值 proxy 來自 `alpha.context`、
  催化劑狀態來自 `shared.catalyst_state.assess_entry`、thesis 到期來自
  `thesis.lifecycle_schedule`。本檔沒有任何一條業務公式。
- **語意標註不是判斷**：`basis` 由**來源路徑**決定（Q1 走 deterministic 規則、Q2–Q5 走
  session、`market_implied_growth` 在 `alpha/context.py` 自己註明是 proxy），不是本檔對
  內容的評價。
- **純函式**：所有輸入由 `sources.py` 取好注入，本檔不開 Neo4j／SQLite／檔案。

## 缺口一律標 `not_modeled`，不用預設值補

downside／probability-weighted expected return／total return 今天 runtime 上**沒有任何程式路徑產生**。
這些格仍然存在於 view 裡，好讓下一階段有明確的插座，但值一律 `None`、status 一律 `not_modeled`——
**不得**拿 Q3 分數、分析師目標價、fair value gap、implied return 或 bull/base 散文冒充。
⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：估值鏈整條退役。** internal fundamentals／earnings bridge／
numeric gap（FY+1 因果橋）、valuation（fair value）、implied return（隱含報酬）、price-implied proxy 六個
section 與它們的模型一起拿掉；本檔不再 import `alpha.valuation`／`alpha.implied_return`／`alpha.fundamental` 的模型半邊。
留下的財務數字只有 Engine C 的觀測與共識（A2），與 Phase 3 三題要用的會計年度別共識。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from alpha.causal import CausalPath, CompanyImpact, StructuralEvent
from alpha.context import ContextBuild
from alpha.contracts import AXES, AlphaSignal, EvidenceRef, Score
from alpha.fundamental.assumptions import select_assumptions
from alpha.provider import SupplyExposure
from alpha.wipeout import LANE_LABELS as WIPEOUT_LANE_LABELS, WIPEOUT_LANES, tally as wipeout_tally
from alpha.refresh import (
    CONTEXT_DIGEST, CURRENT, INVALIDATED, MISSING, RECALCULATE, REVIEW_REQUIRED, STALE, SUPERSEDED,
    THESIS_ARTIFACT_ID, AffectedArtifact, ChangeEvent, MetricObservation, artifacts_from_assumptions,
    artifacts_from_context, artifacts_from_signal, build_instant, resolve_refresh,
)
from shared.catalyst_state import STATE_LABEL, assess_entry
from thesis.lifecycle_schedule import CATALYST, effective_next_check

from alpha.gap_closure import consensus_progress
from alpha.narrative import ABSENT, SLOT_LABELS, fill_brief, format_value, select_brief
from alpha.narrative.argument import chain_paragraph, closure_phrase, timeline_paragraph
from briefing.analyst_view.contracts import PLAIN_REFRESH_OVERALL

from .contracts import (
    CAP_ARGUMENT, ArgumentSection,
    CAP_INVESTOR_BRIEF, InvestorBriefSection,
    CAP_AUTOMATIC_INVALIDATION, CAP_CATALYST_UNLINKED,
    CAP_DEPENDENCY_IMPACT, CAP_NARRATIVE_SCENARIOS, CAP_QUANTITATIVE_SCENARIOS, CAP_STRUCTURAL_CAUSAL,
    CAP_STRUCTURED_DISPROOF, SCHEMA_VERSION, STATUS_LABEL, AlphaInvestmentView, CatalystItem,
    CatalystSection, CausalPathSection, ChangeItem, CheckpointItem, ConsensusSection, Datum,
    DisproofItem, EventItem, EvidenceItem, EvidenceSection,
    EvidenceSelectionCounts, ExpectationGapSection, ExposureItem, FalsificationSection,
    FreshnessItem, FundamentalsSection, IdentitySection, ImpactItem,
    LifecycleFacts, MarketSection, PathItem,
    RefreshItem, RefreshStatusSection, ScenarioSection, SectionMeta,
    SignalCompleteness, StructuralEdgeItem, StructuralThesisSection, VariantViewSection,
    CAP_WIPEOUT_FLAGS, WipeoutFlagsSection,
    missing, not_modeled,
)

# ---------------------------------------------------------------------------
# authority 的邏輯 URI（不是路徑）。改名要連 docs/ARCHITECTURE.md 的 authority map 一起改。
# ---------------------------------------------------------------------------
A_RANK = "engine_a://rank_bottlenecks"
A_GRAPH = "engine_a://graph_research_provider"
A_Q1 = "alpha://context/structural_score"
A_SESSION = "alpha://session_assessor"
A_EVQ = "alpha://evidence_quality"
A_SNAP = "engine_c://financial_snapshots"
A_LEDGER = "engine_c://manual_observations"
A_CHECKLIST = "engine_c://checklist"
A_ESTIMATES = "engine_c://estimates"
A_COVERAGE = "decision_lab://coverage_assessments"
A_THESIS_VP = "decision_lab://cohort_thesis"
A_DECISION = "decision_lab://system_decisions"
A_LIFECYCLE = "decision_lab://probe_lifecycle"
A_THESIS_FILE = "thesis://lifecycle.json"
A_CATALYST_STATE = "shared://catalyst_state.assess_entry"
# Causal Fundamental Model（Phase 2，2026-09-05）：假設、橋、比較各自是 authority，read model 只選取。
A_REFRESH = "alpha://refresh/resolver"

#: refresh state → Datum status。`current`／`recalculate` 在 read model 裡都是「有、可用」（確定性成果每次
#: build 都重算）；`stale`／`review_required`／`invalidated` 各自是一個 status（L12：不壓成一個 stale）。
_REFRESH_TO_STATUS: Mapping[str, str] = {
    CURRENT: "available", RECALCULATE: "available", STALE: "stale",
    REVIEW_REQUIRED: "review_required", INVALIDATED: "invalidated",
}


def _refresh_status(artifact: AffectedArtifact | None, *, fallback: str = "available") -> str:
    if artifact is None or artifact.state in (SUPERSEDED, MISSING):
        return fallback
    return _REFRESH_TO_STATUS[artifact.state]


def _refresh_deps(artifact: AffectedArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {"refresh_state": None}
    return {"refresh_state": artifact.state, "refresh_reasons": list(artifact.reasons),
            "refresh_changed_refs": list(artifact.changed_refs),
            "refresh_required_action": artifact.required_action,
            "refresh_propagated_from": list(artifact.propagated_from)}
A_CONSENSUS_FY = "engine_c://consensus_estimates"

#: 本圖標的高度集中的固定提醒（`AGENTS.md` Alpha 呈現契約：每次都講，不因一樣而省略）。
#: ⚠ 措辭在 2026-09-07 Coverage Pilot 修正過：舊句「本圖標的高度集中於 AI 光互連：列出 N 檔
#: 不等於 N 個獨立機會」是**無條件**掛在每一檔的單檔 view 上的，於是它對 LYC.AX（稀土）與
#: 6324.T（機器人減速機）變成一句假話——這兩檔不在那個群裡。要按產業條件化就得有一份
#: 「這檔屬於哪個群」的分類，而系統**沒有**那個 SSOT，在這裡自己猜一份正是 L16 記過的形狀。
#: 因此改成把主詞明確放回「這份圖的組成」，讓它對任何一檔都為真，且不對本檔的產業下斷言。
CORRELATION_WARNING = (
    "相關性：本圖收錄的標的高度集中於 AI 光互連。把本檔與圖中其他標的並列時，"
    "列出 N 檔不等於 N 個獨立機會，全買可能是同一賭注下 N 次。"
    "⚠ 這是對**這份圖的組成**的提醒，不是對本檔所屬產業的斷言。"
)
JUDGMENT_WARNING = "本 view 內的排序與分數是研究判斷，不是回測或統計勝率；系統不給部位尺寸。"
_CONSENSUS_METRIC_LABEL: Mapping[str, str] = {"eps": "EPS", "revenue": "營收"}


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：FY+1 因果橋整組退役。**
# 原本這裡是 NEXT_PHASE_NOTE／FUNDAMENTAL_EPISTEMIC_WARNING／_INTERNAL_METRIC_LABELS／
# _COMPARISON_LABELS／_COMPARISON_STATUS_TO_DATUM／_multiple_derivation_datum／_FundamentalParts／
# _fundamental_parts（約 350 行）：把 `FundamentalModelResult` 選取成 internal_fundamentals／
# earnings_bridge／numeric_comparisons／opinion_stance 四組 Datum。模型（`alpha/fundamental/{model,bridge}.py`）
# 已刪；假設 ledger 的資料留著（L10）但沒有任何東西再拿它算數字。
# **留下的只有會計年度別共識**（Engine C `consensus_estimates`，A2）——ROADMAP：三題「已定價」要用。


def _fiscal_consensus_items(consensus: Sequence[Any], bases: Mapping[str, str] | None, *,
                            reporting_unit: str) -> tuple[Datum, ...]:
    """會計年度別共識 → 逐筆 Datum。**純選取，一個數都不算。**

    這一段原本住在 `_fundamental_parts()` 裡，跟著 FY+1 因果橋一起產出；橋退役後把它獨立出來。
    `bases` 是每筆共識的會計口徑核實結果（`alpha.fundamental.compare.verify_consensus_basis`：
    provider 的去年實際值與一手財報稀釋 EPS 機械比對），key＝`f"{metric}:{period_end}"`；
    沒核實出來就是 `unverified`——它是資料層的宣告，不是判斷。
    """
    items: list[Datum] = []
    for c in consensus:
        basis = (bases or {}).get(f"{c.metric}:{c.period.end.isoformat()}", "unverified")
        metric_label = _CONSENSUS_METRIC_LABEL.get(c.metric, c.metric)
        if c.value is None:
            items.append(missing(f"consensus_{c.metric}_{c.period.label}",
                                 f"{c.period.label} {metric_label} 共識", "provider 該期無估計值",
                                 authority=A_CONSENSUS_FY))
            continue
        items.append(Datum(
            key=f"consensus_{c.metric}_{c.period.label}",
            label=f"{c.period.label} {metric_label} 共識（至 {c.period.end.isoformat()}）",
            value={"avg": c.value, "low": c.low, "high": c.high, "analyst_count": c.analyst_count,
                   "year_ago_actual": c.year_ago_actual, "growth": c.growth, "currency": c.currency,
                   "relative_label": c.relative_label, "accounting_basis": basis},
            status="available", basis="observation", authority=A_CONSENSUS_FY,
            unit=("currency_per_share" if c.metric == "eps" else reporting_unit),
            as_of=c.captured_at, evidence_refs=c.refs,
            method=f"{c.source}；provider 相對標籤 {c.relative_label} 於抓取日解析成 fiscal_period_end",
            reason=(f"口徑 {basis}：EPS 以 year_ago_actual 與一手財報稀釋 EPS 核對"
                    if c.metric == "eps" else "營收無口徑之分"),
        ))
    return tuple(items)


# ---------------------------------------------------------------------------
# 現價（A2 觀測）。⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：這裡原本是估值 section
# （A_VALUATION／GAP_IS_NOT／VALUATION_EPISTEMIC_WARNING／`_valuation_section`，約 200 行，
# 只選取 `alpha.valuation.build_valuation` 的輸出）。fair value 整條退役；現價自己的家是 `_market_section`。
# ---------------------------------------------------------------------------


def _market_section(build: Any, *, reference_day: date) -> "MarketSection":
    """現價 section（2026-09-23 Phase 0 Step 0b.1 新增）。

    **直接讀 `build.context.market`**，與 `sources._current_price` 同一個來源，
    **不經過估值鏈**——這一節存在的整個理由就是「估值退役後現價還在」。
    這裡沒有任何算術：值、報價單位、bar 日期、證據全部照抄。
    """
    market = getattr(build.context, "market", None)
    value = getattr(market, "price", None) if market is not None else None
    unit = getattr(market, "quote_unit", None) if market is not None else None
    bar_date = getattr(market, "bar_date", None) if market is not None else None
    refs = tuple(r.ref for r in (getattr(market, "evidence", ()) or ())) if market is not None else ()
    if value is None:
        why = "Engine C 無現價快照"
        return MarketSection(
            meta=SectionMeta(status="missing", basis="none", authority=A_SNAP,
                             capability="engine_c_market_snapshot", reason=why, as_of=reference_day),
            price=missing("current_price", "現價（Engine C）", why, authority=A_SNAP),
        )
    return MarketSection(
        meta=SectionMeta(status="available", basis="observation", authority=A_SNAP,
                         capability="engine_c_market_snapshot", reason=None, as_of=reference_day),
        price=Datum(
            key="current_price", label="現價（Engine C）", value=value, status="available",
            basis="observation", authority=A_SNAP, unit=unit or "currency_per_share",
            as_of=bar_date or reference_day, evidence_refs=refs,
            dependencies={"quote_unit": unit, "bar_date": bar_date.isoformat() if bar_date else None},
            reason=None,
        ),
    )


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`_valuation_section` 與 base-case implied return
# 整組退役**（A_IMPLIED_RETURN／A_HORIZON_ASSUMPTIONS／RETURN_IS_NOT／RETURN_EPISTEMIC_WARNING／
# `_implied_return_section`，約 420 行）。「已定價嗎」由財務三題回答（Phase 3），主參照是自己的歷史、不設門檻。


# ---------------------------------------------------------------------------
# Payoff scenario（V0，2026-09-15）：**賭注**——variant scenario 的 fair value 對現價的隱含報酬。
# 只選取 variant 那條鏈（fundamental／valuation／implied_return 各對 variant 跑一次，同一套算術）的輸出；
# 本檔不算任何數：payoff、兩桿拆解、年化全部照抄 `alpha.implied_return` 對 variant 的執行。
# ---------------------------------------------------------------------------
WIPEOUT_IS_NOT: tuple[str, ...] = (
    "不是評分也不是排序鍵：四盞燈**不參與 `rank_bottlenecks`**、不決定尺寸——"
    "它與總曝險倍數、追繳門檻同屬量測（AGENTS「須區分量測、訊號與脈絡」）",
    "不是進出場訊號：黃燈不讀成「減碼」、紅燈不讀成「賣出」；出場只認反證（D3）",
    "不是合成分數：四盞燈刻意不相加、不加權——加起來就必須決定誰比較重要，而那是沒有根據的",
    "綠燈不是「查過都沒事」的保證：它只說**被量到的那一項**沒事；沒量到的一律是灰，不是綠",
)

A_WIPEOUT = "alpha://wipeout_flags/v1"


def _wipeout_section(flags: Mapping[str, Mapping[str, Any]] | None, *, reason: str | None,
                     reference_day: date) -> WipeoutFlagsSection:
    """四盞燈 → 四個 `Datum`。**亮不亮由 `alpha.wipeout` 決定，這裡只轉型別。**

    亮著的燈是 `available`；沒亮的是缺席＋上游宣告的 `absence_kind`——型別層因此讓
    「這盞是綠的」與「這盞沒點亮」不可能同形（L12）。
    """
    if not flags:
        why = reason or "沒有取到 Engine C 的財務觀測"
        meta = SectionMeta(status="missing", basis="none", authority=A_WIPEOUT,
                           capability=CAP_WIPEOUT_FLAGS, reason=why, as_of=reference_day,
                           absence_kind="upstream_unavailable")
        lanes = tuple(missing(f"wipeout_{lane}", f"歸零旗標：{WIPEOUT_LANE_LABELS[lane]}", why,
                              authority=A_WIPEOUT, absence_kind="upstream_unavailable")
                      for lane in WIPEOUT_LANES)
        return WipeoutFlagsSection(meta=meta, lanes=lanes,
                                   tally={"red": 0, "amber": 0, "green": 0, "unlit": len(WIPEOUT_LANES)},
                                   is_not=WIPEOUT_IS_NOT)
    lanes = []
    for lane in WIPEOUT_LANES:
        flag = dict(flags.get(lane) or {})
        label = f"歸零旗標：{WIPEOUT_LANE_LABELS[lane]}"
        if flag.get("colour"):
            lanes.append(Datum(
                key=f"wipeout_{lane}", label=label, value=flag, status="available",
                basis="deterministic", authority=A_WIPEOUT, as_of=reference_day,
                method="alpha.wipeout（符號比較＋兩個外部錨定常數；零憑空門檻）",
                reason=flag.get("reason"),
                dependencies={"rule": flag.get("rule"), "inputs": flag.get("inputs")}))
        else:
            lanes.append(missing(f"wipeout_{lane}", label, str(flag.get("reason") or "這盞燈沒點亮"),
                                 authority=A_WIPEOUT, absence_kind=flag.get("absence_kind")))
    counts = wipeout_tally(flags)
    lit = counts["red"] + counts["amber"] + counts["green"]
    meta = SectionMeta(
        status=("available" if lit == len(WIPEOUT_LANES) else ("partial" if lit else "missing")),
        basis=("deterministic" if lit else "none"), authority=A_WIPEOUT,
        capability=CAP_WIPEOUT_FLAGS, as_of=reference_day,
        absence_kind=(None if lit else "upstream_unavailable"),
        reason=(None if lit == len(WIPEOUT_LANES) else f"{len(WIPEOUT_LANES) - lit} 盞沒點亮，逐盞說了是哪一種沒有"),
        warnings=("燈只給顏色與一句話（D2「紅黃綠不給數字」）；算出它的數字在稽核層的 inputs",))
    return WipeoutFlagsSection(meta=meta, lanes=tuple(lanes), tally=counts, is_not=WIPEOUT_IS_NOT)

# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：A_PAYOFF／A_DOWNSIDE／PAYOFF_IS_NOT／DOWNSIDE_IS_NOT
# 隨 E 組（賭注四價 overlay）退役。

# ---------------------------------------------------------------------------
# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：E 組（賭注四價 overlay）整組退役。**
# 原本這裡是 `_OverlayCopy`／`_override_datum`／`_VARIANT_COPY`／`_DOWNSIDE_COPY`／
# `_payoff_section`／PAYOFF・DOWNSIDE_EPISTEMIC_WARNING 共約 250 行：把整條估值鏈**再跑兩次**，
# 算出「賭對了值多少／判斷錯了值多少」那四個價格。ROADMAP「個股頁」對照表把 `bet` 的四個價格
# 列進「拿掉」；`bet` 面板已於 0b.1a 改成純文字（讀短評的 `our_bet`）。
# ⚠ **`bet/variant.overlay` ledger 的資料留著**（L10）——退役的是「拿它算四個價格」。
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Investor brief（2026-09-15）：七格前因後果。文字照抄 ledger，數字**選取**既有 Datum 後格式化填入。
# 本檔不算任何數：所有值都來自別的 section 已經算好的格；缺值印「（尚無）」並標 missing。
# ---------------------------------------------------------------------------
A_BRIEF = "alpha://brief/ledger"

BRIEF_IS_NOT: tuple[str, ...] = (
    "不是 thesis 的替代：thesis／五軸／disproof 照舊；短評是給人讀的投影，每一句都指得回它的引用",
    "不是新的數字：它一個數都不產生，placeholder 全部由既有 Datum 填入；填不到的印「（尚無）」",
    "不是 buy／sell：「現在不是加碼點」這類句子是 session 的判斷，不是系統的動作建議；買多少由使用者決定",
)


def _brief_values(*, price: Datum, consensus: ConsensusSection,
                  catalysts: CatalystSection, today: date,
                  gap: ExpectationGapSection | None = None) -> dict[str, str | None]:
    """placeholder → 已格式化字串。**純選取＋格式化**：每個值都指得回一個既有 Datum。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`base_target`／`base_return`／`value_date` 的來源
    （implied return）與帶參數的 `{assumption:driver[scope]}`（橋的生效假設）隨估值鏈退役。
    **placeholder 本身留在 `PLACEHOLDERS`／`PARAM_PLACEHOLDER` 封閉字彙裡**（append-only 短評紀錄
    引用它們，L10），值改為 `None` → `fill_brief` 印「（尚無）」並把那一格標 partial，**不補 0**。
    """
    unit = (price.dependencies or {}).get("quote_unit") if price.dependencies else None
    by_key = {d.key: d for d in consensus.items}
    market_multiple = by_key["forward_pe"].value if by_key.get("forward_pe") is not None else None
    analyst_count = by_key["analyst_count"].value if by_key.get("analyst_count") is not None else None
    dates: list[date] = []
    for item in catalysts.checkpoints:
        if isinstance(item.date, date) and item.date >= today:
            dates.append(item.date)
    for item in catalysts.structured:
        expected = getattr(item, "expected_at", None)
        if isinstance(expected, date) and expected >= today:
            dates.append(expected)
    values: dict[str, str | None] = {
        "price": format_value("price", price.value, unit=unit),
        "base_target": None,
        "base_return": None,
        "sell_side_target": format_value("price", by_key["target_mean"].value if "target_mean" in by_key else None, unit=unit),
        "market_multiple": format_value("multiple", market_multiple),
        "analyst_count": format_value("count", analyst_count),
        "value_date": None,
        "next_checkpoint_date": format_value("date", min(dates) if dates else None),
    }
    ql = catalysts.quantitative_link.value if isinstance(catalysts.quantitative_link.value, Mapping) else None
    counts = ql.get("counts") if ql else None
    values["ripeness"] = (f"{counts['resolved']}／{counts['linked']}" if counts and counts.get("linked") else None)
    closure_value = (gap.gap_closure.value if gap is not None and gap.gap_closure is not None
                     and isinstance(gap.gap_closure.value, Mapping) else None)
    values["gap_closure"] = closure_phrase(closure_value)
    return values


def _investor_brief_section(
    records: Sequence[Any], parse_errors: Sequence[str], *,
    as_of: date | None, today: date, reference_day: date,
    price: Datum, consensus: ConsensusSection, catalysts: CatalystSection,
    refresh_overall: str, gap: ExpectationGapSection | None = None,
) -> InvestorBriefSection:
    # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：那把尺（現價／沒賭對／賭對／判斷錯了）整格退役。**
    # ROADMAP「個股頁／首屏」那一列明文「拿掉」。它是這個 section 唯一讀 `ir`／`payoff`／`downside`
    # 的地方，所以拿掉它同時讓短評 section 不再依賴估值鏈——首屏從此只有句子與燈。
    light = Datum(key="brief_status_light", label="狀態燈",
                  value={"state": refresh_overall, "label": PLAIN_REFRESH_OVERALL.get(refresh_overall, refresh_overall)},
                  status="available", basis="deterministic", authority=A_REFRESH, as_of=reference_day,
                  reason="refresh overall 的白話版；不判斷好壞")
    brief = select_brief([r for r in records], as_of=as_of, today=today)
    if brief is None:
        why = ("短評 ledger 有 " + str(len(parse_errors)) + " 行解析失敗" if parse_errors and not records else
               "還沒寫投資人短評（不拿 thesis 硬截——那些句子是分析師欄位，不是給人讀的）")
        meta = SectionMeta(status="missing", basis="none", authority=A_BRIEF, capability=CAP_INVESTOR_BRIEF,
                           reason=why, as_of=reference_day, absence_kind="not_yet_recorded")
        slots = tuple(missing(f"brief:{key}", label, why, authority=A_BRIEF, absence_kind="not_yet_recorded")
                      for key, label in SLOT_LABELS.items())
        return InvestorBriefSection(meta=meta, slots=slots, status_light=light,
                                    brief_id=None, is_not=BRIEF_IS_NOT)
    values = _brief_values(price=price, consensus=consensus, catalysts=catalysts, today=today, gap=gap)
    filled, absent = fill_brief(brief, values)
    slots: list[Datum] = []
    for slot in brief.slots:
        gaps = absent.get(slot.key, [])
        slots.append(Datum(
            key=f"brief:{slot.key}", label=SLOT_LABELS[slot.key], value=filled[slot.key],
            status="partial" if gaps else "available", basis="session_judgment", authority=A_BRIEF,
            as_of=brief.created_on, evidence_refs=tuple(slot.evidence_refs),
            reason=(f"有 {len(gaps)} 個數字尚無：{'、'.join(gaps)}（印成{ABSENT}，不補 0）" if gaps else None),
            dependencies={"raw_text": slot.text, "placeholders": list(slot.placeholders), "missing": gaps,
                          "brief_id": brief.brief_id, "author": brief.author}))
    status = "partial" if absent else "available"
    meta = SectionMeta(status=status, basis="session_judgment", authority=A_BRIEF, capability=CAP_INVESTOR_BRIEF,
                       reason=(f"{len(absent)} 格有數字尚無" if absent else None), as_of=reference_day,
                       warnings=("短評文字是 session 判斷（append-only ledger），數字由既有 Datum 填入；"
                                 "每一句的引用見各格 evidence_refs",))
    return InvestorBriefSection(meta=meta, slots=tuple(slots), status_light=light,
                                brief_id=brief.brief_id, is_not=BRIEF_IS_NOT,
                                )


# ---------------------------------------------------------------------------
# Argument（2026-09-15）：論證層。算術與圖的敘述用封閉句型（alpha.narrative.argument）；判斷的長文照抄。
# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：「數字怎麼算出來」「和市場差在哪」（C／H 組）與「賭注」（E 組）
# 三段退役——它們讀的是估值鏈。剩三段：鏈、風險與認錯條件、時間表。
# 本檔只**選取**既有 Datum 的值、格式化、組句；一個數都不算。
# ---------------------------------------------------------------------------
A_ARGUMENT = "alpha://narrative/argument"
ARGUMENT_KEYS: tuple[tuple[str, str], ...] = (
    ("chain", "這條鏈怎麼走"), ("risks", "風險與認錯條件"), ("timeline", "時間表"),
)
ARGUMENT_IS_NOT: tuple[str, ...] = (
    "不是新的判斷：算術與圖的敘述是句型，判斷的長文逐字來自 session 寫的假設理由、賭注理由、風險與推翻條件",
    "不是引文的替代：每段的 citations 是圖裡 claim 的 statement 與來源文件，不是本層改寫",
)


def _citations(narrative: Mapping[str, Any], about: Sequence[str], *, limit: int = 6) -> list[dict[str, Any]]:
    """關於這幾個節點的 claim 引文（照抄 provider；由新到舊，取前幾條）。"""
    wanted = {str(a) for a in about if a}
    out = []
    # 關於這家公司本身的 claim 排前面（`about` 的最後一個是公司 id），再依 provider 給的新→舊。
    subject = str(about[-1]) if about else None
    ordered = sorted(narrative.get("claims") or (), key=lambda c: 0 if subject and subject in (c.get("about") or ()) else 1)
    for claim in ordered:
        if wanted and not (set(claim.get("about") or ()) & wanted):
            continue
        out.append({"statement": claim.get("statement"), "who": claim.get("origin"), "date": claim.get("published_at"),
                    "title": claim.get("title"), "doc_id": claim.get("doc_id"), "claim_id": claim.get("claim_id"),
                    "level": claim.get("level"), "url": claim.get("url")})
        if len(out) >= limit:
            break
    return out


def _argument_section(*, company_label: str, company_id: str | None, structural: StructuralThesisSection,
                      variant: VariantViewSection,
                      falsification: FalsificationSection, catalysts: CatalystSection, lifecycle: LifecycleFacts,
                      narrative: Mapping[str, Any], reporting_currency: str | None, reference_day: date) -> ArgumentSection:
    names = dict(narrative.get("node_names") or {})
    # 公司名字：圖的 name 優先；registry 沒有 display name 時 identity 會給 `co:xxx（TICKER）`，那不是人話——退回 id 尾巴。
    company_name = names.get(company_id or "") or (
        company_label if "co:" not in company_label else (company_id or company_label).split(":", 1)[-1])
    paragraphs: list[Datum] = []

    def _para(key: str, text: str | None, *, citations: list[dict[str, Any]] = (), long_form: list[dict[str, Any]] = (),
              basis: str = "deterministic", refs: Sequence[str] = (), why: str | None = None) -> None:
        label = dict(ARGUMENT_KEYS)[key]
        if not text:
            paragraphs.append(missing(f"argument:{key}", label, why or "缺料，這一段寫不出來", authority=A_ARGUMENT))
            return
        paragraphs.append(Datum(key=f"argument:{key}", label=label, value=text, status="available", basis=basis,
                                authority=A_ARGUMENT, as_of=reference_day, evidence_refs=tuple(refs),
                                dependencies={"citations": list(citations), "long_form": list(long_form)}))

    # 1. 鏈
    anchor = next((d.value for d in structural.scarcity_inputs if d.key == "demand_anchor"), None)
    edges = [{"relation": e.relation, "target": e.target, "evidence_class": e.evidence_class,
              "sole_source": e.sole_source, "qualification_status": e.qualification_status}
             for e in structural.edges if e.purpose == "actionable"]
    chain_about = [str(e["target"]) for e in edges] + ([str(anchor)] if anchor else [])
    _para("chain", chain_paragraph(company=company_name, anchor_id=anchor, edges=edges, names=names),
          citations=_citations(narrative, chain_about + ([company_id] if company_id else [])), refs=[])

    # ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：「數字怎麼算出來」與「和市場差在哪」兩段退役。**
    # 前者由橋的 steps／假設／敏感度組句，後者由內部 vs 共識的數值比較、目標倍數與反向橋組句——
    # 全部是估值鏈的輸出。實測拿掉後 73/73 檔的 argument 都還有內容（鏈 73／時間表 73／風險 63）。

    # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：論證層的「賭注」段退役（E 組）。**
    # 它由四個價格組句（賭注目標價／payoff／EPS 貢獻／倍數貢獻）。`bet` **面板**已於 0b.1a
    # 改成純文字（讀短評的 `our_bet`）——那是 ROADMAP「bet 改純文字」指的東西；論證層這一段是
    # 另一回事（拿四個價格造句），整段拿掉。論證層剩三段：鏈、風險與認錯條件、時間表。

    # 5. 風險與認錯（全部是 session 長文，照抄）
    risk_text = None
    risk_items = [{"title": "風險", "text": r} for r in variant.risks]
    risk_items += [{"title": "認錯條件", "text": f"{c.condition}｜多久看一次：{c.check_frequency}｜觸發後：{c.action_within_48h}"}
                   for c in falsification.conditions]
    if risk_items:
        risk_text = f"研究時寫下 {len(variant.risks)} 條風險與 {len(falsification.conditions)} 條認錯條件；全文在下方，一個字沒改。"
    _para("risks", risk_text, long_form=risk_items, basis="session_judgment", why="還沒寫下風險或推翻條件")

    # 6. 時間表
    _para("timeline", timeline_paragraph(
        checkpoints=[{"date": c.date, "what": c.what, "decides": c.decides} for c in catalysts.checkpoints],
        catalysts=[{"expected_at": c.expected_at, "description": c.description, "state": c.state}
                   for c in catalysts.structured],
        thesis_next_check=lifecycle.thesis_next_check),
        basis="session_judgment")

    known = [p for p in paragraphs if p.is_known]
    status = "available" if len(known) == len(paragraphs) else ("partial" if known else "missing")
    meta = SectionMeta(status=status, basis="session_judgment", authority=A_ARGUMENT, capability=CAP_ARGUMENT,
                       reason=(None if status == "available" else "；".join(p.reason or p.key for p in paragraphs if not p.is_known)),
                       as_of=reference_day,
                       warnings=(("圖來源的 claim 引文取不到：" + str(narrative.get("error")),) if narrative.get("error") else ()))
    return ArgumentSection(meta=meta, paragraphs=tuple(paragraphs), is_not=ARGUMENT_IS_NOT)


# ---------------------------------------------------------------------------
# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：F 組（entry logic）整組退役。**
# 原本這裡是 A_ENTRY／ENTRY_IS_NOT／ENTRY_EPISTEMIC_WARNING／`_entry_logic_section`
# （要求報酬判準 → 門檻價 → 現價比較）共約 210 行。73 檔全 missing、從未用過；
# ROADMAP 個股頁那一列列為「拿掉」。**進場靠判斷，出場靠 disproof**——不再有門檻價。
# `_worst_status` 只有那一段用，一併移除。
# ---------------------------------------------------------------------------


_SESSION_LEVEL_LABEL = {
    "unknown": "不知道", "weak": "弱", "moderate": "中等", "strong": "強", "very_strong": "很強",
}


@dataclass(frozen=True, slots=True)
class DecisionFacts:
    """Engine D 對這家公司的**公開** cohort 事實切片（由 `sources.py` 取，這裡只讀）。

    ⚠ 刻意沒有任何部位／NAV／尺寸欄位。`AlphaSignal != Position`，read model 也一樣。
    """

    cohort_id: str | None = None
    cohort_count: int | None = None
    selection_rule: str | None = None
    #: Engine D 唯讀查詢回報的時點：`current` 或 `as_of`＋日期。builder 在 as-of 模式下
    #: **只接受標記與 context.as_of 相符的事實**，其餘一律拒收（INV-6）。
    point_in_time_mode: str | None = None
    point_in_time_as_of: str | None = None
    research_status: str | None = None
    rubric_version: str | None = None
    lifecycle_status: str | None = None
    review_due_at: str | None = None
    decision_effective_at: str | None = None
    legacy_weakest_axis: str | None = None
    legacy_axis_levels: Mapping[str, str] | None = None
    catalyst: str | None = None
    disproof: str | None = None
    expiry: str | None = None
    coverage_created_at: str | None = None
    variant_perception: str | None = None
    variant_perception_created_at: str | None = None


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

def _refs(refs: Sequence[EvidenceRef]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(r.ref for r in refs))


def _absent(key: str, label: str, reason: str, *, status: str = "missing",
            authority: str | None = None) -> Datum:
    """缺席格。`status` 區分 `missing`（有能力沒資料）與 `not_applicable`
    （這個視角下不該回答，例如 as-of 模式對沒有時點投影的來源）。"""
    return Datum(key=key, label=label, value=None, status=status, basis="none",
                 authority=authority, reason=reason)


AXIS_LABEL: Mapping[str, str] = {
    "structural": "Q1 結構稀缺（確定性規則）",
    "value_capture": "Q2 價值攫取（session 判斷）",
    "earnings_exposure": "Q3 盈餘曝險（session 判斷）",
    "expectation_gap": "Q4 預期落差（session 判斷，ordinal）",
    "catalyst": "Q5 催化劑（session 判斷）",
}


def _q1_datum(build: ContextBuild) -> Datum:
    """Q1 由已入圖事實確定性算出，**不依賴 session**；權威是 `alpha.context.structural_score`。"""
    score = build.structural
    trace = build.structural_trace
    if score is None:
        return missing("structural_score", AXIS_LABEL["structural"],
                       "Q1 無法計算：缺 substitutability 或缺 evidence → None（不是 0）",
                       authority=A_Q1)
    return Datum(
        key="structural_score", label=AXIS_LABEL["structural"],
        value={"declared": score.declared, "effective": score.effective,
               "downgrade_reason": score.downgrade_reason},
        status="available", basis="deterministic", authority=A_Q1,
        method=trace.rule_version if trace else None, unit="ordinal_0_1",
        as_of=build.context.as_of,
        evidence_refs=_refs(trace.evidence_refs) if trace else (),
        reason=trace.note if trace else None,
    )


def _session_score_datum(
    signal: AlphaSignal | None, axis: str, *, signal_reason: str | None, stale: bool,
    judged_on: date | None = None, absent_status: str = "missing", status: str | None = None,
    refresh: AffectedArtifact | None = None,
) -> Datum:
    """Q2–Q5 的一格：session 判斷，`None` 分數＝不知道，不是 0。"""
    label = AXIS_LABEL[axis]
    if signal is None:
        return _absent(f"{axis}_score", label,
                       signal_reason or "尚無 session 判斷（AlphaSignal 未組成）",
                       status=absent_status, authority=A_SESSION)
    score: Score | None = signal.score_for(axis)
    if score is None:
        return missing(f"{axis}_score", label, "session 回答 unknown——不知道，不是 0",
                       authority=A_SESSION)
    trace = signal.model_components.get(score.trace_id)
    inputs = dict(trace.inputs) if trace else {}
    level = str(inputs.get("session_level") or "")
    value: dict[str, Any] = {
        "declared": score.declared, "effective": score.effective,
        "downgrade_reason": score.downgrade_reason,
        "session_level": level or None,
        "session_level_label": _SESSION_LEVEL_LABEL.get(level),
    }
    note = trace.note if trace else None
    if refresh is not None and refresh.state != CURRENT:
        note = f"[refresh={refresh.state}] {refresh.reasons[0]}" + (f"｜{note}" if note else "")
    return Datum(
        key=f"{axis}_score", label=label, value=value,
        status=status or ("stale" if stale else "available"), basis="session_judgment", authority=A_SESSION,
        method=(trace.rule_version if trace else None), unit="ordinal_0_1",
        as_of=judged_on or signal.as_of, evidence_refs=_refs(trace.evidence_refs) if trace else (),
        reason=note, dependencies=(_refresh_deps(refresh) if refresh is not None else None),
    )


def _text_datum(
    key: str, label: str, text: str | None, *, basis: str, authority: str,
    stale: bool, as_of: date | None, missing_reason: str, absent_status: str = "missing",
    status: str | None = None,
) -> Datum:
    if not text or not str(text).strip():
        return _absent(key, label, missing_reason, status=absent_status, authority=authority)
    return Datum(key=key, label=label, value=str(text), status=status or ("stale" if stale else "available"),
                 basis=basis, authority=authority, as_of=as_of)


def _observation(
    key: str, label: str, value: Any, *, authority: str, unit: str | None,
    as_of: date | None, freshness: str | None, evidence_refs: tuple[str, ...],
    method: str | None = None, missing_reason: str = "authority 無此值",
    reason: str | None = None,
) -> Datum:
    if value is None:
        return missing(key, label, missing_reason, authority=authority)
    status = "stale" if freshness == "stale" else "available"
    return Datum(key=key, label=label, value=value, status=status, basis="observation",
                 authority=authority, method=method, unit=unit, as_of=as_of,
                 evidence_refs=evidence_refs, reason=reason)


def _path_item(path: CausalPath) -> PathItem:
    return PathItem(
        nodes=tuple(path.nodes), relations=tuple(path.relations), hops=path.hops,
        confidence=path.confidence.name.lower(), weakest_link=path.weakest_link,
        evidence_refs=_refs(path.evidence),
    )


def _freshness_status(build: ContextBuild, key: str) -> str | None:
    state = build.context.freshness.get(key)
    return state.status if state else None


def _freshness_as_of(build: ContextBuild, key: str) -> date | None:
    state = build.context.freshness.get(key)
    return state.as_of if state else None


# ---------------------------------------------------------------------------
# 主函式
# ---------------------------------------------------------------------------

def build_alpha_investment_view(
    *,
    build: ContextBuild,
    signal: AlphaSignal | None = None,
    signal_reason: str | None = None,
    dependency_paths: Sequence[CausalPath] = (),
    substitution_paths: Sequence[CausalPath] = (),
    supply_exposure: Sequence[SupplyExposure] = (),
    impacts: Sequence[CompanyImpact] = (),
    structural_events: Sequence[StructuralEvent] = (),
    causal_reason: str | None = None,
    ranking_position: Mapping[str, Any] | None = None,
    estimate_revision: Mapping[str, Any] | None = None,
    decision_facts: DecisionFacts | None = None,
    decision_facts_reason: str | None = None,
    catalyst_checkpoints: Sequence[Mapping[str, Any]] = (),
    checkpoint_source: str | None = None,
    thesis_lifecycle: Mapping[str, Any] | None = None,
    checklist: Mapping[str, Any] | None = None,
    identity: Mapping[str, Any] | None = None,
    #: 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：估值鏈退役後，builder 收的財務輸入只剩 Engine C 的
    #: 基期觀測（報表幣別的身分來源）與會計年度別共識（三題「已定價」要用）。**沒有任何模型輸出進來。**
    base_actuals: Any | None = None,
    fiscal_consensus: Sequence[Any] = (),
    consensus_bases: Mapping[str, str] | None = None,
    #: 取數層取不到（provider 沒能力／讀取失敗／PIT 拒用）的原因——沒有列時要印出來，不得靜默（INV-3）。
    financials_reason: str | None = None,
    #: 基期觀測／共識／指引／期中實績的 evidence ref——只用來讓假設的引用解析得到，並進卡片的 evidence index。
    financial_evidence: Sequence[Any] = (),
    #: 目標期間（最近已報導年度的下一年）。只用來選取假設（as-of／期間／supersede／證據解析）——不推任何數字。
    target_period: Any | None = None,
    today: date | None = None,
    refresh_changes: Sequence[ChangeEvent] | None = None,
    assumption_records: Sequence[Any] = (),
    abstention_records: Sequence[Any] = (),
    metric_observations: Sequence[MetricObservation] = (),
    change_detection: str | None = None,
    refresh_notes: Sequence[str] = (),
    #: D2（2026-09-18）：歸零旗標。`alpha.wipeout.wipeout_flags()` 的輸出，由取數層算好帶進來——
    #: builder 不連 DB、不自己判色。
    wipeout: Mapping[str, Mapping[str, Any]] | None = None,
    wipeout_reason: str | None = None,
    brief_records: Sequence[Any] = (),
    brief_parse_errors: Sequence[str] = (),
    narrative_context: Mapping[str, Any] | None = None,
    consensus_history: Sequence[tuple[date, float, Any]] = (),
) -> AlphaInvestmentView:
    """組裝一家公司的 `AlphaInvestmentView`。所有參數都是已取好的既有 authority 輸出。

    `assumption_records`（營運假設 ledger，A3）今天只餵兩個地方：催化劑熟成度（`resolves` 指名的假設
    有沒有重看過）與 refresh 的假設 artifact——**沒有任何模型再拿它算數字**（2026-09-23 Phase 0）。
    """
    today = today or date.today()
    context = build.context
    ticker = str(context.ticker)
    company_id = str(context.company_id) if context.company_id else None
    identity = dict(identity or {})
    quote_unit = identity.get("market_quote_unit")
    market_currency = identity.get("market_currency")
    # ⚠ **報表幣別 ≠ 報價幣別**（`AGENTS.md`「報價單位 ≠ 結算幣別」）。
    # 2026-09-13 實測：`reporting_currency（…）` 這個單位標籤一直是用 `market_currency` 組的，
    # 而它掛的是**法定財報幣別**的數字（內部營收／營業利益／淨利／fair value）。
    # 兩者相同的美股看不出來；不同的 5 檔全部標錯：XFAB.PA（USD 財報／EUR 報價）、
    # HEXA-B.ST（EUR／SEK）、6680.HK（CNY／HKD）、XPEV（CNY／USD）、
    # **IQE.L（GBP／GBp）——那是 minor unit，讀成報表幣別會差 100 倍**。
    # 身分來源只能是財報自己：基期觀測宣告的 currency，其次是快照的 financial_currency。
    # ⚠ **不得回退到 `market_currency`**——那正是這個 bug；答不出來就寫「未知」（L12 先分開再各自定規則）。
    reporting_currency = (
        (getattr(base_actuals, "currency", None) if base_actuals is not None else None)
        or getattr(context.fundamentals, "currency", None)
    )

    # as-of 模式：Engine A／C 有時點投影，Decision Store 與 thesis 檔沒有。沒有投影的來源
    # 一律 `not_applicable` 並說明，不拿當前值冒充 T 時刻（INV-6）。builder 自己強制，
    # 不靠 sources 記得不要傳。
    as_of_mode = context.as_of is not None
    as_of_iso = context.as_of.isoformat() if context.as_of else None
    reference_day = context.as_of or today
    pit_reason = (
        f"as-of {as_of_iso} 模式：這個來源沒有時點投影，不以當前值冒充 T 時刻的知識（INV-6）"
        if as_of_mode else None
    )
    decision_refused = False
    if as_of_mode:
        # Decision Store 是 append-only 且帶時間戳，`company_decision_facts(as_of=…)` 能做真正的
        # 歷史過濾——所以允許**帶著相符 as-of 標記**的事實進來；沒有標記或標記不符的一律拒收，
        # 否則呼叫端傳錯就會把當前值混進歷史卡。
        if decision_facts is not None and decision_facts.point_in_time_as_of != as_of_iso:
            decision_refused = True
            decision_facts_reason = (
                f"as-of {as_of_iso} 模式：傳入的 Engine D 事實沒有相符的 as-of 過濾標記"
                f"（point_in_time_as_of={decision_facts.point_in_time_as_of!r}），拒收以免把當前值混進歷史卡（INV-6）"
            )
            decision_facts = None
        elif decision_facts is None and not decision_facts_reason:
            decision_refused = True
            decision_facts_reason = pit_reason
        # thesis/lifecycle.json 與 catalyst_calendar.json 是當前狀態檔，沒有歷史。
        thesis_lifecycle = None
        catalyst_checkpoints = ()
    #: 沒有時點語意的來源在 as-of 下是 not_applicable；authority 回答「T 時刻沒有」則是 missing。
    thesis_absent_status = "not_applicable" if as_of_mode else "missing"
    decision_absent_status = "not_applicable" if (as_of_mode and decision_refused) else "missing"
    # ---- 判斷新鮮度：判斷是對哪一份 context 做的 ---------------------------
    mismatch = None
    if signal is not None:
        mismatch = (signal.metadata or {}).get("context_mismatch")
    signal_stale = bool(mismatch)
    judged_digest = (
        str(mismatch.get("judged_context_digest")) if isinstance(mismatch, Mapping)
        else (signal.research_context_digest if signal else None)
    )
    stale_reason = (
        "判斷是對舊的 ResearchContext 做的（行情／證據已更新，判斷尚未重做）"
        if signal_stale else None
    )
    # 判斷的日期：判斷檔自報的 `_produced_at`（經 compose_signal 進 metadata），沒有才退回
    # `signal.as_of`。⚠ 後者在當前視角下是「今天」——那是 context 的日期，不是判斷的日期。
    judged_on: date | None = None
    if signal is not None:
        judged_on = _as_date((signal.metadata or {}).get("judged_at")) or signal.as_of
    # as-of 模式的 lookahead 防線：判斷寫於 T 之後就是 T 之後的知識，就算標 stale 也不得
    # 出現在歷史卡上（INV-6）。拒用後 Q2–Q5／thesis／情境全部 not_applicable 並說明。
    signal_absent_status = "missing"
    if as_of_mode and signal is not None and judged_on is not None and judged_on > context.as_of:
        signal_reason = (
            f"as-of {as_of_iso} 模式：session 判斷寫於 {judged_on.isoformat()}，晚於 as_of，"
            "屬 lookahead；歷史卡拒用（INV-6）"
        )
        signal = None
        signal_stale = False
        mismatch = None
        judged_digest = None
        stale_reason = None
        judged_on = None
        signal_absent_status = "not_applicable"

    # ---- Refresh／dependency impact：單一 authority（alpha.refresh），這裡只消費 -------------
    # digest mismatch 只是「判斷對的是舊 context」這個**事實**（留在 identity.signal.context_matches）；
    # 它**不再**自動讓 Q2–Q5／thesis／情境全部 stale——那是 Step 0（2026-09-06）抓到的 over-invalidation。
    # 判斷型成果的 status 改由 resolver 依變化的種類決定；呼叫端沒跑變更偵測（refresh_changes=None）時
    # 退回舊行為（digest 不符即 stale）並在 refresh section 標 change_detection=not_run。
    build_at = build_instant(reference_day)
    judged_at = build_instant(judged_on) if judged_on else None
    artifacts = artifacts_from_signal(signal, judged_at=judged_at,
                                      structural_trace=build.structural_trace, build_at=build_at)
    # ---- 假設 ledger 的選取語意（as-of／期間／supersede／證據解析）：這是 ledger 的判準，不是模型的 ----
    # 模型退役前它跑在 `build_fundamental_model` 裡；拒收原因決定假設 artifact 的終局（unresolved_evidence →
    # invalidated、other_period／created_after_as_of → missing、superseded／retracted → superseded）。
    # 沒有目標期間（沒有基期觀測也沒有共識）就不選取，只依 ledger 時序判撤回／取代。
    # ⚠ 只登記 base 鏈：variant／downside overlay 紀錄（E 組退役後只剩 ledger 資料）不進 refresh——退役前
    # 也只登記模型那一條 scenario（base），overlay 進來會把同一條件重複印成「等待中」好幾次。
    base_records = [r for r in assumption_records if str(getattr(r, "scenario", "base") or "base") == "base"]
    assumption_rejections: dict[str, str] = {}
    if target_period is not None and base_records:
        evidence_index: dict[str, Any] = {ref.ref: ref for ref in context.evidence_refs}
        for ref in financial_evidence:
            evidence_index.setdefault(ref.ref, ref)
        _accepted, assumption_selection = select_assumptions(
            base_records, target=target_period, as_of=context.as_of, today=today,
            evidence_index=evidence_index)
        assumption_rejections = dict(assumption_selection.rejected)
    artifacts += artifacts_from_assumptions(
        base_records, build_at=build_at, rejection=assumption_rejections,
        base_period_end=(getattr(getattr(base_actuals, "period", None), "end", None) if base_actuals is not None else None))
    artifacts += artifacts_from_context(context, build_at=build_at)
    detection = change_detection or ("not_run" if refresh_changes is None else "authority_time_series")
    changes = list(refresh_changes or ())
    if (refresh_changes is not None and signal_stale and judged_at is not None
            and not any(c.observed_at > judged_at for c in changes)):
        # 殘餘：digest 變了但沒有任何已分類的變化——必須現形，不得靜默當 current（保守：review_required）。
        changes.append(ChangeEvent(
            change_type=CONTEXT_DIGEST, ticker=ticker, company_id=company_id, authority=A_SESSION,
            changed_ref=context.digest, observed_at=build_at,
            old_version=judged_digest, new_version=context.digest,
            material_fields=("research_context_digest",),
            detail="ResearchContext digest 已變，但變更偵測沒有任何已分類的變化能解釋——殘餘差異未分類"))
    report = resolve_refresh(ticker=ticker, company_id=company_id, artifacts=artifacts, changes=changes,
                             observations=metric_observations, as_of=context.as_of, today=today)
    refresh_by_key = {a.key: a for a in report.artifacts}
    thesis_refresh = refresh_by_key.get(f"thesis:{THESIS_ARTIFACT_ID}")
    axis_refresh = {axis: refresh_by_key.get(f"axis:{axis}") for axis in AXES}
    if refresh_changes is None:
        judgment_status = "stale" if signal_stale else "available"
        axis_status = {axis: judgment_status for axis in AXES}
    else:
        judgment_status = _refresh_status(thesis_refresh)
        axis_status = {axis: _refresh_status(axis_refresh[axis]) for axis in AXES}
        if signal is not None:
            if judgment_status != "available":
                stale_reason = "；".join(thesis_refresh.reasons[:2]) if thesis_refresh else stale_reason
            elif signal_stale:
                kinds = sorted({c.change_type for c in report.changes})
                stale_reason = ("判斷對的是舊 context（digest 已變），但已分類的變化不動搖這份判斷"
                                f"（{', '.join(kinds) or '無變化'}）")
            else:
                stale_reason = None
    judgment_not_current = judgment_status != "available"

    market_section = _market_section(build, reference_day=reference_day)
    reporting_unit = f"reporting_currency（{reporting_currency or '未知'}；未正規化）"
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`payoff_section` 與 `downside_section` 隨 E 組退役。

    # ---- Evidence index：context ＋ 路徑／事件的引用，去重 -------------------
    evidence_pool: dict[str, EvidenceRef] = {}
    for ref in context.evidence_refs:
        evidence_pool.setdefault(ref.ref, ref)
    for path in (*dependency_paths, *substitution_paths):
        for ref in path.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    for exposure in supply_exposure:
        for ref in exposure.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    for impact in impacts:
        for ref in impact.path.evidence:
            evidence_pool.setdefault(ref.ref, ref)
        if impact.event is not None:
            for ref in impact.event.evidence:
                evidence_pool.setdefault(ref.ref, ref)
    for event in structural_events:
        for ref in event.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    if signal is not None:
        for ref in signal.evidence_refs:
            evidence_pool.setdefault(ref.ref, ref)
    # Phase 2 驗收（2026-09-06）抓到：假設引用的 engine_c://manual_observation／consensus_estimate
    # 在模型端解析得到，卡片自己的 evidence index 卻沒有——讀者拿著卡片對不回引用。
    # 2026-09-23 起模型沒了，基期觀測與會計年度別共識的 evidence 直接進來（取數層已在 as-of 下過濾）。
    for ref in financial_evidence:
        evidence_pool.setdefault(ref.ref, ref)

    fund_fresh = _freshness_status(build, "fundamentals")
    market_fresh = _freshness_status(build, "market")
    cons_fresh = _freshness_status(build, "consensus")
    snapshot_refs = _refs(context.fundamentals.evidence)
    market_refs = _refs(context.market.evidence)
    consensus_refs = _refs(context.consensus.evidence)

    # =======================================================================
    # A. Identity / State
    # =======================================================================
    data_completeness = tuple(
        Datum(
            key=f"freshness_{name}", label=f"{label} 新鮮度",
            value={"status": state.status, "as_of": state.as_of, "age_days": state.age_days,
                   "reason": state.reason},
            status="available", basis="observation", authority=A_SNAP, as_of=state.as_of,
        )
        for name, label in (("fundamentals", "財務"), ("market", "行情"), ("consensus", "共識"))
        for state in (context.freshness.get(name),)
        if state is not None
    )
    thesis_status = str(thesis_lifecycle.get("status")) if thesis_lifecycle else None
    next_check, next_source, _cp = (
        effective_next_check(thesis_lifecycle, today=today) if thesis_lifecycle
        else (None, None, None)
    )
    lifecycle = LifecycleFacts(
        research_status=decision_facts.research_status if decision_facts else None,
        lifecycle_status=decision_facts.lifecycle_status if decision_facts else None,
        review_due_at=decision_facts.review_due_at if decision_facts else None,
        decision_effective_at=decision_facts.decision_effective_at if decision_facts else None,
        legacy_weakest_axis=decision_facts.legacy_weakest_axis if decision_facts else None,
        legacy_axis_levels=(dict(decision_facts.legacy_axis_levels)
                            if decision_facts and decision_facts.legacy_axis_levels else None),
        cohort_count=decision_facts.cohort_count if decision_facts else None,
        cohort_selection_rule=decision_facts.selection_rule if decision_facts else None,
        decision_facts_as_of=decision_facts.point_in_time_as_of if decision_facts else None,
        thesis_lifecycle_status=thesis_status,
        thesis_next_check=next_check,
        thesis_next_check_source=next_source,
        authority=(A_LIFECYCLE if decision_facts else None),
        reason=(
            (decision_facts_reason or "Engine D 無此公司的 cohort，或本次未讀 Decision Store")
            if decision_facts is None else
            (f"同公司 {decision_facts.cohort_count} 個 cohort，只呈現規則 "
             f"{decision_facts.selection_rule} 選出的那個"
             if (decision_facts.cohort_count or 0) > 1 else None)
        ),
    )
    completeness = SignalCompleteness(
        has_signal=signal is not None,
        is_incomplete=signal.is_incomplete if signal else None,
        known_axes=tuple(signal.known_axes) if signal else (),
        weakest_axis=signal.weakest if signal else None,
        judged_at=judged_on.isoformat() if judged_on else None,
        judged_context_digest=judged_digest,
        current_context_digest=context.digest,
        context_matches=(None if signal is None else not signal_stale),
        reason=(signal_reason if signal is None else stale_reason),
        refresh_state=(thesis_refresh.state if (signal is not None and thesis_refresh) else None),
    )
    identity_warnings: list[str] = []
    if quote_unit and market_currency and quote_unit != market_currency:
        identity_warnings.append(
            f"報價單位 {quote_unit} ≠ 結算幣別 {market_currency}：以報價單位計的欄位"
            "（price／forward_eps／market_cap）與結算幣別差 100 倍，跨標的比較前必須正規化"
        )
    identity_section = IdentitySection(
        ticker=ticker, company_id=company_id,
        # 面向人的標籤。registry 有 `display_name` 就用它，沒有就退回 `co:*（ticker）`——
        # **不從 company_id 猜名字**（`co:iqe` → 「Iqe」是編出來的）。AGENTS 的判準是
        # 「不得假設使用者能從 co:* ID 或內部術語自行還原主詞」，而缺名字時誠實露出 ID
        # 比編一個像模像樣的名字安全。
        company_label=(str(identity.get("display_name")) if identity.get("display_name")
                       else (f"{company_id}（{ticker}）" if company_id else ticker)),
        market_currency=market_currency, market_quote_unit=quote_unit,
        execution_venue=identity.get("execution_venue"),
        as_of=context.as_of,
        point_in_time_mode="as_of" if context.as_of else "current",
        generated_on=today,
        research_context_digest=context.digest,
        signal=completeness, data_completeness=data_completeness, lifecycle=lifecycle,
        warnings=tuple(identity_warnings),
    )

    # =======================================================================
    # B. Variant View（thesis／variant view／方向／信心／期間：全部 session 判斷）
    # =======================================================================
    no_signal = signal_reason or "尚無 session 判斷（AlphaSignal 未組成）"
    q1 = _q1_datum(build)
    session_scores = {
        axis: _session_score_datum(signal, axis, signal_reason=signal_reason, stale=signal_stale,
                                   judged_on=judged_on, absent_status=signal_absent_status,
                                   status=axis_status[axis],
                                   refresh=(axis_refresh[axis] if refresh_changes is not None else None))
        for axis in AXES if axis != "structural"
    }
    all_scores = tuple(q1 if axis == "structural" else session_scores[axis] for axis in AXES)
    vp_as_of = None
    if decision_facts and decision_facts.variant_perception_created_at:
        vp_as_of = _as_date(decision_facts.variant_perception_created_at)
    variant_section = VariantViewSection(
        meta=SectionMeta(
            status=judgment_status if signal else signal_absent_status,
            basis="session_judgment" if signal else "none",
            authority=A_SESSION if signal else None,
            reason=(stale_reason if signal else no_signal),
            as_of=judged_on,
            freshness=("stale" if judgment_not_current else "available") if signal else "missing",
            warnings=("thesis／variant view／bull-base-bear 是 session（LLM）判斷，"
                      "不是 deterministic model output；引用皆已解析到 ResearchContext 內的證據",),
        ),
        thesis=_text_datum("thesis", "Thesis", signal.thesis if signal else None,
                           basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                           as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status, status=judgment_status),
        variant_view=_text_datum("variant_view", "Variant perception（市場隱含 X／本 thesis 認為 Y／催化劑 Z）",
                                 signal.variant_view if signal else None,
                                 basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                                 as_of=judged_on, missing_reason=no_signal,
                                 absent_status=signal_absent_status, status=judgment_status),
        direction=(Datum(key="direction", label="方向", value=signal.direction,
                         status=judgment_status,
                         basis="session_judgment", authority=A_SESSION, as_of=judged_on)
                   if signal else _absent("direction", "方向", no_signal,
                                          status=signal_absent_status, authority=A_SESSION)),
        confidence=(Datum(key="confidence", label="信心（session 自評）", value=signal.confidence,
                          status=judgment_status,
                          basis="session_judgment", authority=A_SESSION, unit="confidence_0_1",
                          as_of=judged_on,
                          reason="session 自評的信心（0..1），不是量測的勝率")
                    if signal else _absent("confidence", "信心（session 自評）", no_signal,
                                           status=signal_absent_status, authority=A_SESSION)),
        expected_horizon=_text_datum("expected_horizon", "預期期間",
                                     signal.expected_horizon if signal else None,
                                     basis="session_judgment", authority=A_SESSION,
                                     stale=signal_stale, as_of=judged_on,
                                     missing_reason=no_signal, absent_status=signal_absent_status,
                                     status=judgment_status),
        scores=all_scores,
        risks=tuple(signal.risks) if signal else (),
        decision_store_variant_perception=_text_datum(
            "decision_store_variant_perception", "Decision Store 的 variant perception",
            decision_facts.variant_perception if decision_facts else None,
            basis="session_judgment", authority=A_THESIS_VP, stale=False, as_of=vp_as_of,
            missing_reason=("cohort 從未寫過 variant perception（None＝未寫，現形不隱藏）"
                            if decision_facts else
                            decision_facts_reason or "本次未讀 Decision Store"),
            absent_status=decision_absent_status,
        ),
    )

    # =======================================================================
    # C. Structural Thesis（Q1 ＋ 已入圖事實 ＋ 排序位置）
    # =======================================================================
    scarcity = context.structural
    scarcity_refs = _refs(scarcity.evidence)
    graph_as_of = context.as_of
    scarcity_inputs = tuple(
        _observation(key, label, value, authority=A_RANK, unit=unit, as_of=graph_as_of,
                     freshness=None, evidence_refs=scarcity_refs,
                     method="已經 graph admission gate 核准的邊屬性；provider 取最強的一條邊，不平均",
                     missing_reason="圖上這條邊沒有這個屬性（未填≠否；rank_bottlenecks 自 2026-09-05 起保留三態）")
        for key, label, value, unit in (
            ("substitutability", "替代難度", scarcity.substitutability, "ordinal_1_5"),
            ("sole_source", "獨家供應", scarcity.sole_source, "bool"),
            ("qualification_status", "認證狀態", scarcity.qualification_status, "vocab"),
            ("qualification_lead_time_weeks", "認證前置時間（週）",
             scarcity.qualification_lead_time_weeks, "weeks"),
            ("dependency_depth", "距需求端跳數", scarcity.dependency_depth, "hops"),
            ("demand_anchor", "需求錨點",
             str(scarcity.demand_anchor) if scarcity.demand_anchor else None, "entity_id"),
        )
    )
    ranking_items: list[Datum] = []
    if ranking_position:
        for key, label in (("actionable_rank", "可行動排序名次（rank_bottlenecks rows）"),
                           ("actionable_total", "可行動候選總數")):
            value = ranking_position.get(key)
            ranking_items.append(
                Datum(key=key, label=label, value=value, status="available",
                      basis="deterministic", authority=A_RANK,
                      method="讀 rank_bottlenecks() 的既有順序，本 view 不重排", unit="rank")
                if value is not None else
                missing(key, label, "這家公司不在 rows（可行動排序）內", authority=A_RANK)
            )
    else:
        ranking_items.append(missing("actionable_rank", "可行動排序名次",
                                     "本次未注入排序位置", authority=A_RANK))
    edges = tuple(
        StructuralEdgeItem(
            relation=str(e.get("relation") or ""), target=str(e.get("target") or ""),
            substitutability=e.get("substitutability"), sole_source=e.get("sole_source"),
            qualification_status=e.get("qualification_status"),
            demand_anchor=e.get("demand_anchor"), demand_hops=e.get("demand_hops"),
            evidence_class=e.get("evidence_class"), purpose="actionable",
        ) for e in context.graph.edges
    ) + tuple(
        StructuralEdgeItem(
            relation=str(e.get("relation") or ""), target=str(e.get("target") or ""),
            substitutability=None, sole_source=None, qualification_status=None,
            demand_anchor=None, demand_hops=None, evidence_class=None,
            purpose=str(e.get("purpose") or "structural_only_not_actionable"),
        ) for e in context.graph.counter_paths
    )
    coverage = dict(build.coverage or {})
    caveats: list[str] = []
    if coverage.get("canonical_edges") and coverage.get("edges_with_substitutability") is not None:
        share = coverage.get("substitutability_coverage")
        caveats.append(
            f"substitutability 覆蓋 {coverage['edges_with_substitutability']}/"
            f"{coverage['canonical_edges']}"
            f"（{share:.1%}）——排名必然偏向已被抽取過的邊，沒填的邊是隱形的"
            if isinstance(share, (int, float)) else "substitutability 覆蓋率未知"
        )
    if coverage.get("edges_with_lead_time") is not None:
        caveats.append(f"本排名不含 lead time（有值的邊只有 {coverage['edges_with_lead_time']} 條）")
    caveats.append("同一 chokepoint 的供應商計數反映的是我們研究了幾家，不是世界上有幾家")
    caveats.append("evidence 等級是研究深度的函數，不得單獨當瓶頸性證據")
    evq = build.evidence_quality
    evidence_quality = Datum(
        key="evidence_quality", label="證據品質（整體摘要，L8 獨立性）",
        value={"level": evq.level, "independent_origins": evq.independent_origins,
               "best_tier": evq.best_tier, "total_refs": evq.total_refs, "reason": evq.reason},
        status="available", basis="deterministic", authority=A_EVQ,
        method=f"alpha.evidence_quality.assess_evidence_quality（{evq.scale_version}）",
        reason="整體摘要，不是任何一軸的上限；上限逐軸算",
    )
    if build.structural is not None:
        struct_status, struct_reason = "available", None
    elif context.graph.edges or context.graph.counter_paths:
        struct_status, struct_reason = "insufficient_evidence", "有邊但 Q1 算不出來：" + "；".join(build.notes)
    else:
        struct_status, struct_reason = "missing", "圖中沒有這家公司的可行動瓶頸邊（可能是 substitutability 未填，不代表它不是瓶頸）"
    structural_section = StructuralThesisSection(
        meta=SectionMeta(
            status=struct_status,
            basis="deterministic" if struct_status == "available" else "none",
            authority=A_RANK, reason=struct_reason, as_of=graph_as_of,
            warnings=("結構重要 ≠ 可投資；瓶頸 ≠ 買進訊號。Q1 只是五分之一。",),
        ),
        structural_score=q1, scarcity_inputs=scarcity_inputs, ranking=tuple(ranking_items),
        edges=edges,
        supply_exposure=tuple(
            ExposureItem(direction=x.direction, counterparty=str(x.counterparty_id),
                         relation=x.relation, substitutability=x.substitutability,
                         evidence_refs=_refs(x.evidence))
            for x in supply_exposure
        ),
        substitution_paths=tuple(_path_item(p) for p in substitution_paths),
        evidence_quality=evidence_quality, coverage_caveats=tuple(caveats),
    )

    # =======================================================================
    # D. Causal Path（structural causal model，不是 financial causal model）
    # =======================================================================
    impact_items = tuple(
        ImpactItem(
            event_id=i.event.event_id if i.event else None,
            event_kind=i.event.kind if i.event else None,
            event_direction=i.event.direction if i.event else None,
            subject=str(i.event.subject_id) if i.event else None,
            observed_at=i.event.observed_at if i.event else None,
            impact_direction=i.direction.value, magnitude=i.magnitude.value,
            time_horizon=i.time_horizon.value, confidence=i.confidence.name.lower(),
            path=_path_item(i.path), rationale=i.rationale,
        ) for i in impacts
    )
    event_items = tuple(
        EventItem(event_id=e.event_id, kind=e.kind, subject=str(e.subject_id),
                  direction=e.direction, observed_at=e.observed_at, description=e.description,
                  evidence_refs=_refs(e.evidence))
        for e in structural_events
    )
    has_causal = bool(dependency_paths or substitution_paths or impact_items or event_items)
    causal_section = CausalPathSection(
        meta=SectionMeta(
            status="available" if has_causal else "missing",
            basis="structural_inference" if has_causal else "none",
            authority=A_GRAPH, capability=CAP_STRUCTURAL_CAUSAL,
            reason=(None if has_causal else
                    (causal_reason or "provider 沒有回傳這家公司的依賴／替代路徑或結構事件")),
            as_of=graph_as_of,
            warnings=(
                "這是 structural causal model：structural change → beneficiary／victim → "
                "direction／magnitude／horizon。它不是 financial causal model——"
                "沒有 volume／ASP／utilization／mix → revenue → margin → EPS／FCF 的橋。",
                "多跳結論永遠是 derived，不入圖；confidence 取路徑最弱的一段，不取平均；"
                "二階 magnitude 最高只到 medium。",
            ),
        ),
        dependency_paths=tuple(_path_item(p) for p in dependency_paths),
        substitution_paths=tuple(_path_item(p) for p in substitution_paths),
        impacts_on_company=impact_items, structural_events=event_items,
    )

    # =======================================================================
    # E. Fundamentals（Engine C 觀測；PIT／captured-at／provenance 全保留）
    # =======================================================================
    f = context.fundamentals
    m = context.market
    fund_as_of = _freshness_as_of(build, "fundamentals")
    market_as_of = m.bar_date or _freshness_as_of(build, "market")
    quote_price_unit = f"quote_unit（{quote_unit or '未知'}）"
    fundamentals_items = (
        _observation("price", "價格", m.price, authority=A_SNAP, unit=quote_price_unit,
                     as_of=market_as_of, freshness=market_fresh, evidence_refs=market_refs,
                     method=f"price_kind={m.price_kind or '未知'}；bar_date 是交易日、snapshot_date 是 ETL 日（兩者分開，F-27）",
                     missing_reason="Engine C 無這檔的行情快照"),
        _observation("bar_date", "行情交易日（bar_date）", m.bar_date, authority=A_SNAP,
                     unit="date", as_of=market_as_of, freshness=market_fresh,
                     evidence_refs=market_refs,
                     missing_reason="快照沒有 bar_date（舊列覆蓋不全），不得用 ETL 日冒充"),
        _observation("market_cap", "市值（price × shares，未正規化）", m.market_cap,
                     authority=A_SNAP, unit=f"{quote_price_unit} × shares", as_of=market_as_of,
                     freshness=market_fresh, evidence_refs=market_refs,
                     method="provider 導出：price × shares_outstanding；報價單位≠結算幣別時會差 100 倍",
                     missing_reason="缺 price 或 shares_outstanding"),
        _observation("gross_margin", "毛利率（TTM）", f.gross_margin, authority=A_SNAP,
                     unit="ratio", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("operating_margin", "營益率（TTM）", f.operating_margin, authority=A_SNAP,
                     unit="ratio", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("revenue_ttm", "營收（TTM）", f.revenue_ttm, authority=A_SNAP,
                     unit=reporting_unit, as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("free_cash_flow_ttm", "自由現金流（TTM）", f.free_cash_flow_ttm,
                     authority=A_SNAP, unit=reporting_unit, as_of=fund_as_of,
                     freshness=fund_fresh, evidence_refs=snapshot_refs,
                     missing_reason="yfinance 在財報後常暫時清空 FCF；缺席不是 0"),
        _observation("cash_and_equivalents", "現金與約當現金", f.cash_and_equivalents,
                     authority=A_SNAP, unit=reporting_unit, as_of=fund_as_of,
                     freshness=fund_fresh, evidence_refs=snapshot_refs),
        _observation("total_debt", "總負債", f.total_debt, authority=A_SNAP,
                     unit=reporting_unit, as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("shares_outstanding", "流通股數", f.shares_outstanding, authority=A_SNAP,
                     unit="shares", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
    )
    segment = _observation(
        "segment_revenue_share", "分部營收占比", dict(f.segment_revenue_share) if f.segment_revenue_share else None,
        authority=A_LEDGER, unit="ratio_by_segment", as_of=None, freshness=None,
        evidence_refs=snapshot_refs,
        method="Engine C 人工 ledger（verifiability=mechanical，自年報分部附註逐字讀入）；"
               "⚠ provider 目前只帶 value，不帶該筆觀測的 as_of／source_ref",
        missing_reason="Engine C 人工 ledger 無這檔的分部觀測（None，不是空 dict）",
    )
    checklist_items: list[Datum] = []
    if checklist and checklist.get("engine_c_available"):
        for key, item in (checklist.get("items") or {}).items():
            status = str(item.get("status") or "missing")
            label = str(item.get("label") or key)
            if status in ("ok", "manual_reviewed"):
                value = {k: v for k, v in item.items() if k not in ("label", "status")}
                checklist_items.append(Datum(
                    key=f"checklist_{key}", label=label, value=value or {"status": status},
                    status="available", basis="observation",
                    authority=A_LEDGER if status == "manual_reviewed" else A_CHECKLIST,
                    method="人工填入（manual ledger）" if status == "manual_reviewed" else "由 financial_snapshots 導出",
                ))
            else:
                checklist_items.append(missing(
                    f"checklist_{key}", label,
                    "需人工填入（manual_required）——未知，不是 0" if status == "manual_required"
                    else "Engine C 無資料",
                    authority=A_CHECKLIST,
                ))
        checklist_items.append(Datum(
            key="checklist_gate_pass", label="五項核驗清單是否齊備", value=bool(checklist.get("gate_pass")),
            status="available", basis="deterministic", authority=A_CHECKLIST,
            method="engine_c.checklist.get_checklist：五項皆 ok／manual_reviewed",
        ))
    else:
        checklist_items.append(missing("checklist", "五項財務核驗清單",
                                       (checklist or {}).get("note") or "本次未讀 Engine C checklist",
                                       authority=A_CHECKLIST))
    fund_status = fund_fresh or "missing"
    fundamentals_section = FundamentalsSection(
        meta=SectionMeta(
            status=fund_status if fund_status in ("available", "stale", "missing") else "missing",
            basis="observation" if fund_status in ("available", "stale") else "none",
            authority=A_SNAP, as_of=fund_as_of, freshness=fund_fresh,
            reason=(context.freshness.get("fundamentals").reason
                    if context.freshness.get("fundamentals") else None),
            warnings=("金額欄位以報表幣別計、行情欄位以報價單位計，兩者都未做 FX 正規化，不得跨標的直接比大小。",),
        ),
        items=fundamentals_items, segment_revenue_share=segment, checklist=tuple(checklist_items),
    )

    # =======================================================================
    # F. Consensus（真正存在的只有 next-FY 營收＋倍數＋目標價；標 partial）
    # =======================================================================
    c = context.consensus
    cons_as_of = _freshness_as_of(build, "consensus")
    # ⚠ 刻意不算 target_vs_price：view 只讀 authority，不長第二份算式（審計 2026-09-05 第 5 條）；
    # 原本產出那個比值的 scripts/alpha_expectation_gap.py 已於 2026-09-23（Phase 0 Step 0b.2）退役。
    consensus_items = (
        _observation("analyst_count", "分析師目標價家數", c.analyst_count, authority=A_SNAP,
                     unit="count", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs),
        _observation("target_mean", "賣方目標價均值（不是本系統的預期報酬）", c.target_mean,
                     authority=A_SNAP, unit=quote_price_unit, as_of=cons_as_of,
                     freshness=cons_fresh, evidence_refs=consensus_refs,
                     missing_reason="無分析師目標價"),
        _observation("forward_pe", "forward P/E", c.forward_pe, authority=A_SNAP, unit="multiple",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs),
        _observation("trailing_pe", "trailing P/E", c.trailing_pe, authority=A_SNAP,
                     unit="multiple", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs,
                     missing_reason="無 trailing PE——公司目前無正的 trailing EPS（多半在虧損）"),
        _observation("ev_revenue", "EV／營收", c.ev_revenue, authority=A_SNAP, unit="multiple",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs),
        _observation("forward_eps", "forward EPS（導出）", c.forward_eps, authority=A_ESTIMATES,
                     unit=f"{quote_price_unit}／share", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs,
                     method="price / pe_forward（≡ yfinance forwardEps）；以報價單位計，只能當同一標的的時間序列比值用"),
        _observation("revenue_estimate_next_fy", "「下一會計年度」營收共識（yfinance +1y，絕對值）",
                     c.revenue_estimate_next_fy, authority=A_SNAP, unit=reporting_unit,
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="yfinance revenue_estimate +1y avg；不得跨標的比大小",
                     reason="⚠ +1y 是相對於抓取日的標籤，不是會計年度身分（COHR 在 FY2026 財報後它指 FY2028）；"
                            "要與內部估計同期比較請用 fiscal_items（帶 fiscal_period_end）"),
        _observation("revenue_estimate_next_fy_growth", "下一會計年度營收共識成長",
                     c.revenue_estimate_next_fy_growth, authority=A_SNAP, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="營收成長；⚠ 不是 EPS 成長，分母不同，不得相減成 gap"),
        _observation("estimate_revision_30d", "forward EPS 30 個觀測修正幅度",
                     c.estimate_revision_30d, authority=A_ESTIMATES, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="engine_c.estimates.revision_over：同一標的、**同一個 forward 會計年度**"
                            "導出 forward EPS 的序列比值",
                     missing_reason="序列太短、起點為 0、跨越正負號，或窗口兩端的 forward 會計年度"
                                    "身分不明／不相同（rollover）——算不出來不是沒修正"),
    )
    cons_has_snapshot = cons_fresh in ("available", "stale")
    fiscal_items = _fiscal_consensus_items(fiscal_consensus, consensus_bases, reporting_unit=reporting_unit)
    fiscal_periods = sorted({d.dependencies.get("period") if d.dependencies else d.key.rsplit("_", 1)[-1]
                             for d in fiscal_items})
    consensus_section = ConsensusSection(
        meta=SectionMeta(
            status=("stale" if cons_fresh == "stale" else "partial") if cons_has_snapshot else "missing",
            basis="observation" if cons_has_snapshot else "none",
            authority=A_SNAP, as_of=cons_as_of, freshness=cons_fresh,
            reason=("Engine C 無這檔的共識快照" if not cons_has_snapshot else
                    "快照欄位覆蓋到 next-FY 營收共識、forward／trailing PE、EV/營收、目標價均值與導出 forward EPS；"
                    + (f"會計年度別 EPS／營收共識（fiscal_items）覆蓋 {'、'.join(fiscal_periods)}" if fiscal_items
                       else ("會計年度別 EPS／營收共識（consensus_estimates）尚無列"
                             + (f"（{financials_reason}）" if financials_reason else "")))),
            warnings=((f"Engine C 會計年度別資料：{financials_reason}",) if financials_reason else ())
            + ("這不是 multi-year consensus earnings model：fiscal_items 只到 provider 的 0y／+1y 兩個年度，"
                      "沒有目標價高低區間、沒有逐位分析師分布；修正歷史只有由 price/pe_forward 導出的序列。",
                      "快照裡的 forward_eps 是 price/pe_forward 導出、revenue_estimate_next_fy 是相對標籤 +1y——"
                      "兩者都不是會計年度身分明確的共識；同期比較只用 fiscal_items。")
            + ((f"⚠ 估計修正不可比：{estimate_revision.get('not_comparable_reason')}"
                f"（同窗口股價 {estimate_revision.get('price_change', 0):+.1%}）。"
                "forward year rollover 不是 analyst estimate revision，不得當 Q4 正向證據。",)
               if estimate_revision and not estimate_revision.get("comparable") else ()),
        ),
        items=consensus_items,
        coverage_note=("partial：snapshot（next-FY revenue estimate ＋ forward／trailing PE ＋ EV/Rev ＋ target mean ＋ "
                       "derived forward EPS）＋ fiscal_items（FY-identified EPS／revenue avg／low／high／n／year_ago，"
                       "只到 0y 與 +1y）；缺 multi-year EPS（第三年起）、target high/low、per-analyst distribution、"
                       "margin consensus"),
        fiscal_items=fiscal_items,
    )

    # =======================================================================
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：G（price-implied proxy）、H（internal fundamentals）、
    #   I（earnings bridge）三個 section 整組退役；J 只剩 session 判斷（Q4）與共識時序的量測。
    # J. Expectation Gap（session 判斷 ＋ 量測；沒有任何數值 gap）
    # =======================================================================
    q4 = session_scores["expectation_gap"]
    # ---- V2 gap closure：共識自判斷日以來的移動（量測不是訊號）--------------------------------
    # ⚠ 2026-09-23：內部 EPS 隨 FY+1 因果橋退役，所以 `our_value=None`——沒有「朝我們移了幾成」的分母，
    # `closed_fraction` 是 None（不是 0）；量到的只有共識本身從起點到現值的移動。賭注那條線（variant）
    # 已於 E 組退役，恆 None。
    points = [(d, float(v)) for d, v, _n in consensus_history]
    progress_base = consensus_progress(points, since=judged_on, our_value=None)
    if progress_base.get("status") == "available":
        gap_closure_datum = Datum(
            key="gap_closure", label="市場承認了嗎：自判斷日以來共識 EPS 移了多少",
            value={"base": progress_base, "variant": None, "since": judged_on, "bet_since": None},
            status="available", basis="deterministic", authority=A_CONSENSUS_FY, as_of=today,
            method=progress_base["rule"],
            reason=("量測不是訊號：只回答共識自判斷日以來移了多少；不排序、不決定尺寸。"
                    "⚠ 2026-09-23 Phase 0：內部 EPS 已退役，所以沒有「朝我們移了幾成」的比例"
                    "（closed_fraction 為 None，不是 0）；「已定價嗎」由財務三題接手（Phase 3）"
                    + ("；判斷日未知，起點取序列第一筆" if judged_on is None else "")))
    else:
        gap_closure_datum = missing("gap_closure", "市場承認了嗎：自判斷日以來共識 EPS 移了多少",
                                    progress_base.get("reason") or "沒有共識序列", authority=A_CONSENSUS_FY)
    consensus_series_datum = (
        Datum(key="consensus_series", label="目標期間共識 EPS 的抓取時序", status="available", basis="observation",
              authority=A_CONSENSUS_FY, as_of=today, unit="currency_per_share",
              value=[{"date": d, "value": v, "analyst_count": n} for d, v, n in consensus_history],
              reason=f"{len(consensus_history)} 個抓取日；身分是 fiscal_period_end，不是 +1y 標籤")
        if consensus_history else
        missing("consensus_series", "目標期間共識 EPS 的抓取時序", "consensus_estimates 沒有這個期間的時序", authority=A_CONSENSUS_FY))

    gap_has = q4.is_known or gap_closure_datum.is_known
    expectation_gap_section = ExpectationGapSection(
        meta=SectionMeta(
            status=((q4.status if q4.status in ("stale", "review_required", "invalidated") else "partial")
                    if gap_has else "missing"),
            basis=("session_judgment" if q4.is_known else ("deterministic" if gap_closure_datum.is_known else "none")),
            authority=(A_SESSION if q4.is_known else A_CONSENSUS_FY),
            capability=None,
            reason=("Q4 是 session 的 ordinal 判斷；gap_closure 是共識時序的量測——兩者並存、各自標示。"
                    "⚠ 內部 vs 共識的數值 gap 已於 2026-09-23 Phase 0 隨 FY+1 因果橋退役"
                    if gap_has else "無 session 判斷、無共識時序"),
            warnings=(
                "Q4 的 ordinal 等級不是 internal EPS − consensus EPS——那個數值差已退役，本 section 沒有任何數值 gap。",
                "gap_closure 是量測不是訊號：正值只代表共識上修，不是可行動的 gap。",
            ),
        ),
        session_judgment=q4, gap_closure=gap_closure_datum, consensus_series=consensus_series_datum,
    )

    # =======================================================================
    # K. Catalyst（結構化催化劑／檢核點／散文／到期狀態；量化連結未建模）
    # =======================================================================
    q5 = session_scores["catalyst"]
    # V1（2026-09-15）熟成度：一條催化劑「裁決了沒」是機械判定——事件日期已過，且它指名的每條假設在那之後
    # 都有新的 ledger 紀錄（同 key 的 append）。不解析散文、不判真假。
    ledger_records = list(assumption_records)
    by_id = {r.assumption_id: r for r in ledger_records}

    def _catalyst_state(cat: Any) -> tuple[str, tuple[str, ...]]:
        if not cat.resolves:
            return "unlinked", ()
        unknown = tuple(i for i in cat.resolves if i not in by_id)
        if cat.expected_at is None or cat.expected_at > reference_day:
            return "pending", unknown
        for aid in cat.resolves:
            target = by_id.get(aid)
            if target is None:
                continue
            rejudged = any(r.key == target.key and r.scenario == getattr(target, "scenario", "base")
                           and r.created_at.date() > cat.expected_at for r in ledger_records)
            if not rejudged:
                return "due", unknown
        return "resolved", unknown

    structured = tuple(
        CatalystItem(kind=cat.kind, description=cat.description, expected_at=cat.expected_at,
                     date_confidence=cat.date_confidence, basis="session_judgment",
                     evidence_refs=_refs(cat.evidence_refs), resolves=tuple(cat.resolves),
                     state=_catalyst_state(cat)[0], unresolved_ids=_catalyst_state(cat)[1])
        for cat in (signal.catalysts if signal else ())
    )
    linked = [c for c in structured if c.state != "unlinked"]
    ripeness_counts = {"total": len(structured), "linked": len(linked),
                       "resolved": sum(1 for c in linked if c.state == "resolved"),
                       "due": sum(1 for c in linked if c.state == "due"),
                       "pending": sum(1 for c in linked if c.state == "pending")}
    if linked:
        quantitative_link_datum = Datum(
            key="quantitative_link", label="催化劑 → 假設的連結與熟成度",
            value={"counts": ripeness_counts,
                   "links": [{"description": c.description, "expected_at": c.expected_at, "resolves": list(c.resolves),
                              "state": c.state, "unresolved_ids": list(c.unresolved_ids)} for c in linked],
                   "rule": "resolved＝事件日期已過且每條被指名的假設在那之後都有新紀錄；due＝已過但還沒重看；pending＝未到"},
            status="available", basis="deterministic", authority=A_SESSION, as_of=reference_day,
            method="機械計數：只看催化劑日期與 ledger 的 created_at；不解析散文、不判真假、不算它會讓 EPS 變多少",
            reason=(f"{ripeness_counts['resolved']}/{ripeness_counts['linked']} 條已裁決"
                    + (f"；{ripeness_counts['due']} 條到期待重看" if ripeness_counts['due'] else "")),
            dependencies={"unlinked": ripeness_counts["total"] - ripeness_counts["linked"]})
    else:
        quantitative_link_datum = not_modeled(
            "quantitative_link", "催化劑 → 假設的連結與熟成度",
            "沒有任何催化劑指名它會裁決哪條假設（judgment 的 catalysts[].resolves）——有日期與散文，但算不進熟成度")
    # 催化劑那一格**為什麼沒進熟成度**的機械計數（2026-09-19，七缺陷之 1）。
    # ⚠ 這一格永遠 available：`quantitative_link` 在沒有 linked 催化劑時是 `not_modeled`，
    # 而型別層禁止無值狀態帶值——於是「有催化劑但沒填 resolves」「有 resolves 但日期晚」
    # 「根本沒有催化劑」在下游長得一模一樣，全部變成一句「沒有指名假設的催化劑」（L12）。
    # 形狀由**產生它的這一段**宣告，呈現層不得 parse 理由句去猜（L16）。
    unlinked_items = [c for c in structured if c.state == "unlinked"]
    unlinked_dates = sorted(str(c.expected_at) for c in unlinked_items if c.expected_at is not None)
    catalyst_shape_datum = Datum(
        key="catalyst_shape", label="催化劑那一格的形狀（為什麼沒進熟成度）",
        value={"total": len(structured), "linked": len(linked),
               "unlinked": len(unlinked_items),
               "unlinked_dated": len(unlinked_dates),
               "unlinked_undated": len(unlinked_items) - len(unlinked_dates),
               "earliest_unlinked_date": (unlinked_dates[0] if unlinked_dates else None),
               "rule": ("unlinked＝`catalysts[].resolves` 沒填（有散文、可能也有日期，"
                        "但指不出它會裁決哪一條假設）。**這是資料沒填，不是系統沒能力**——"
                        "2026-09-19 實測 62 個判斷檔、104 條催化劑，填寫數 0。")},
        status="available", basis="deterministic", authority=A_SESSION, as_of=reference_day,
        method="機械計數：只數 catalysts[] 的條數、有沒有 resolves、有沒有日期；不解析散文")

    checkpoint_items = tuple(
        CheckpointItem(date=cp["date"], what=str(cp.get("what") or ""), decides=str(cp.get("decides") or ""),
                       date_confidence=str(cp.get("date_confidence") or "estimated"),
                       source=checkpoint_source or A_THESIS_FILE)
        for cp in catalyst_checkpoints if cp.get("date")
    )
    watch_state_datum = _absent("watch_state", "到期／催化劑狀態",
                                decision_facts_reason or "本次未讀 Decision Store",
                                status=decision_absent_status, authority=A_CATALYST_STATE)
    expiry_datum = _absent("expiry", "decision 有效期（expiry）",
                           decision_facts_reason or "本次未讀 Decision Store",
                           status=decision_absent_status, authority=A_COVERAGE)
    problems: tuple[str, ...] = ()
    if decision_facts is not None:
        # as-of 模式：以 as_of 當「今天」判到期；檢核點來自沒有歷史的 thesis 檔，已被清空。
        assessed = assess_entry(
            {"company_id": company_id, "ticker": ticker, "catalyst": decision_facts.catalyst,
             "disproof": decision_facts.disproof, "expiry": decision_facts.expiry},
            today=reference_day,
            checkpoints=[{"date": cp.date.isoformat(), "date_confidence": cp.date_confidence}
                         for cp in checkpoint_items],
        )
        problems = tuple(assessed["problems"])
        watch_state_datum = Datum(
            key="watch_state", label="到期／催化劑狀態",
            value={"state": assessed["state"], "label": STATE_LABEL.get(assessed["state"]),
                   "days_to_expiry": assessed["days_to_expiry"],
                   "next_catalyst": assessed["next_catalyst"],
                   "next_catalyst_confidence": assessed["next_catalyst_confidence"]},
            status="available", basis="deterministic", authority=A_CATALYST_STATE,
            method=("shared.catalyst_state.assess_entry（與 scripts/catalyst_watch.py 同一支；只判日期，不解析散文）"
                    + (f"；as-of 模式以 {as_of_iso} 為今天、無檢核點" if as_of_mode else "")),
            as_of=reference_day,
            reason="它是條件檢查不是訊號：只回答「你寫下的到期日今天到了沒」",
        )
        expiry_datum = _observation("expiry", "decision 有效期（expiry）", decision_facts.expiry,
                                    authority=A_COVERAGE, unit="timestamp",
                                    as_of=_as_date(decision_facts.coverage_created_at), freshness=None,
                                    evidence_refs=(), missing_reason="coverage assessment 無 expiry")
    narrative_catalyst = _text_datum(
        "narrative_catalyst", "Decision Store 的 catalyst 原文（散文）",
        decision_facts.catalyst if decision_facts else None, basis="narrative", authority=A_COVERAGE,
        stale=False, as_of=_as_date(decision_facts.coverage_created_at) if decision_facts else None,
        missing_reason=("cohort 的 catalyst 未填（L7：expiry 因此是沒有內容的鬧鐘）" if decision_facts
                        else decision_facts_reason or "本次未讀 Decision Store"),
        absent_status=decision_absent_status,
    )
    has_catalyst = bool(structured or checkpoint_items or narrative_catalyst.is_known or q5.is_known)
    # 「已研究、結論是沒有可監看事件」只能來自 append-only 的 Abstention，不能在呈現層打標籤
    # （AGENTS「APP 呈現契約」）。它**不讓 readiness 變好**——status 仍是 missing；
    # 變的只有 absence_kind，也就是「該不該花力氣去補」。
    catalyst_abstention = None
    if not has_catalyst and abstention_records:
        from alpha.abstention.contracts import select_abstention

        catalyst_abstention = select_abstention(
            list(abstention_records), layer="research", subject="axis.catalyst",
            period_end=None, as_of=context.as_of, today=today)
    catalyst_section = CatalystSection(
        meta=SectionMeta(
            status="partial" if has_catalyst else "missing",
            absence_kind=("deliberate_abstention" if catalyst_abstention is not None else None),
            # 檢核點是人手填進 thesis JSON 的結構化紀錄（含 estimated 標記），是 observation
            # 不是 deterministic；deterministic 的是 assess_entry 算出來的 watch_state。
            basis=("session_judgment" if structured or q5.is_known else
                   "observation" if checkpoint_items else
                   "narrative" if narrative_catalyst.is_known else "none"),
            authority=A_SESSION if structured else (checkpoint_source or A_COVERAGE),
            capability=CAP_CATALYST_UNLINKED,
            reason=("催化劑有結構化日期與狀態，但尚未量化連結到盈餘／重定價（partial capability）"
                    if has_catalyst else
                    (f"刻意不主張：{catalyst_abstention.reason}｜什麼會改寫："
                     f"{catalyst_abstention.revisit_when}｜宣告於 "
                     f"{catalyst_abstention.created_on.isoformat()}（{catalyst_abstention.abstention_id}）"
                     if catalyst_abstention is not None else "沒有任何來源提供催化劑")),
            as_of=reference_day,
            warnings=("推估（estimated）日期照樣排程但必須標明；散文裡的日期不猜。",),
        ),
        catalyst_score=q5, structured=structured, checkpoints=checkpoint_items,
        narrative=narrative_catalyst, watch_state=watch_state_datum, expiry=expiry_datum,
        problems=problems,
        quantitative_link=quantitative_link_datum,
        shape=catalyst_shape_datum,
    )

    # =======================================================================
    # L. Falsification（結構化條件＋到期監看；自動失效引擎未建模）
    # =======================================================================
    conditions = tuple(
        DisproofItem(condition=d.condition, check_frequency=d.check_frequency,
                     action_within_48h=d.action_within_48h, basis="session_judgment",
                     evidence_refs=_refs(d.evidence_refs))
        for d in (signal.disproof_conditions if signal else ())
    )
    narrative_disproof = _text_datum(
        "narrative_disproof", "Decision Store 的 disproof 原文（散文）",
        decision_facts.disproof if decision_facts else None, basis="narrative", authority=A_COVERAGE,
        stale=False, as_of=_as_date(decision_facts.coverage_created_at) if decision_facts else None,
        missing_reason=("cohort 的 disproof 未填（L7：沒有證偽條件的警報永遠不會響）" if decision_facts
                        else decision_facts_reason or "本次未讀 Decision Store"),
        absent_status=decision_absent_status,
    )
    thesis_status_datum = (
        Datum(key="thesis_lifecycle_status", label="thesis lifecycle 狀態", value={
                  "status": thesis_status, "next_check": next_check,
                  "next_check_source": next_source,
                  "next_check_is_catalyst": next_source == CATALYST},
              # `status` 是人在 lifecycle.json 手動維護的紀錄（observation）；
              # 只有 next_check 是 lifecycle_schedule 算出來的，寫在 method 裡。
              status="available", basis="observation", authority=A_THESIS_FILE,
              method="status 由人維護於 thesis/lifecycle.json；next_check 由 "
                     "thesis.lifecycle_schedule.effective_next_check 算出（cadence 與催化劑取較早者）",
              as_of=reference_day)
        if thesis_lifecycle else
        _absent("thesis_lifecycle_status", "thesis lifecycle 狀態",
                pit_reason or "這檔沒有 lane memo thesis（thesis/lifecycle.json 只涵蓋有 memo 的 thesis）",
                status=thesis_absent_status, authority=A_THESIS_FILE)
    )
    has_falsification = bool(conditions or narrative_disproof.is_known)
    falsification_section = FalsificationSection(
        meta=SectionMeta(
            status=(judgment_status if conditions else "available") if has_falsification else "missing",
            basis="session_judgment" if conditions else ("narrative" if narrative_disproof.is_known else "none"),
            authority=A_SESSION if conditions else A_COVERAGE,
            capability=CAP_STRUCTURED_DISPROOF,
            reason=(None if has_falsification else "沒有任何 disproof 條件——L7 要求每條 thesis 必帶"),
            warnings=("L7 三件套（條件／核查頻率／48 小時動作）由 alpha.contracts.DisproofCondition 強制；"
                      "runtime 只監看 expiry 與催化劑日期，不會自動判定條件是否已被觸發。",),
        ),
        conditions=conditions, narrative_disproof=narrative_disproof, thesis_status=thesis_status_datum,
        expiry_watch=watch_state_datum,
        automatic_invalidation=Datum(
            key="automatic_invalidation", label="依賴失效引擎（refresh／dependency impact）",
            value={"capability": CAP_DEPENDENCY_IMPACT, "overall": report.overall,
                   "evaluates": ["已分類的 ChangeEvent（authority 時序）", "假設自帶的 machine-readable review_conditions",
                                 "Event Watch 喚醒（disproof_signal）", "L7 核查頻率到期（stale）"],
                   "does_not": ["解析自然語言的 disproof 條件", "改 thesis／假設／判斷", "自動呼叫 LLM"]},
            status="partial", basis="deterministic", authority=A_REFRESH, as_of=reference_day,
            method="alpha.refresh.resolve_refresh（" + report.policy_version + "）",
            reason=("它決定 impact state（review_required／invalidated／recalculate／stale），不決定真假；"
                    "自然語言條件仍由人在核查頻率時判讀（capability＝" + CAP_DEPENDENCY_IMPACT
                    + "，非 " + CAP_AUTOMATIC_INVALIDATION + "）"),
        ),
    )

    # =======================================================================
    # M. Scenario（narrative，不是 quantitative scenario model）
    # =======================================================================
    def _scenario(key: str, label: str, text: str | None) -> Datum:
        return _text_datum(key, label, text, basis="narrative", authority=A_SESSION,
                           stale=signal_stale, as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status, status=judgment_status)

    scenario_section = ScenarioSection(
        meta=SectionMeta(
            status=judgment_status if signal else signal_absent_status,
            basis="narrative" if signal else "none", authority=A_SESSION if signal else None,
            capability=CAP_NARRATIVE_SCENARIOS, as_of=judged_on,
            reason=("bull／base／bear 是 session 寫的散文，沒有機率、沒有目標估值" if signal else no_signal),
            warnings=(f"scenario_type={CAP_NARRATIVE_SCENARIOS}，不是 {CAP_QUANTITATIVE_SCENARIOS}。",),
        ),
        scenario_type=CAP_NARRATIVE_SCENARIOS,
        bull=_scenario("bull_case", "Bull case（散文）", signal.bull_case if signal else None),
        base=_scenario("base_case", "Base case（散文）", signal.base_case if signal else None),
        bear=_scenario("bear_case", "Bear case（散文）", signal.bear_case if signal else None),
        probabilities=not_modeled("scenario_probabilities", "情境機率", "沒有任何機率加權"),
        # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`target_valuation`（照抄 valuation.fair_value）隨估值鏈退役。
    )

    # =======================================================================
    # N. Downside——2026-09-18（D2）起**已建模**：`downside_section` 在 payoff 旁邊就組好了，
    #    走的是同一個 `_payoff_section`。implied return／entry logic 已於上方由
    #    alpha.implied_return／alpha.entry 組裝。
    # =======================================================================
    # ⚠ 這裡原本有一個區域函式 `_not_modeled_section(...)`，唯一的呼叫端就是下檔那一段
    # （「系統不產生下檔估計：沒有 bear case 的數值、沒有最大回撤模型。」）。D2 定案後那句話
    # 已經是假的，所以**連同那段程式碼一起移除**——留著一個沒有呼叫端的產生器，下一個人
    # 會以為下檔還走它。`NotModeledSection` 型別本身留在 contracts 給真正沒有能力的東西用。
    # 舊語意的去向：「不是 bear case」「不是出場訊號」進了 `DOWNSIDE_IS_NOT`，由 section 帶著走。

    # =======================================================================
    # O. Evidence / Provenance
    # =======================================================================
    selection = context.evidence_selection
    evidence_section = EvidenceSection(
        meta=SectionMeta(
            status="available" if evidence_pool else "missing",
            basis="observation" if evidence_pool else "none", authority=A_GRAPH,
            reason=(None if evidence_pool else "沒有任何 EvidenceRef"),
            warnings=("published_at＝世界知道的時間；retrieved_at＝我們抓到的時間；recorded_at＝寫進系統的時間。"
                      "as-of 模式下未標日期的證據一律排除並計數，不當成 T 之前。",),
        ),
        index=tuple(
            EvidenceItem(ref=r.ref, kind=r.kind, source_doc_id=r.source_doc_id,
                         origin_entity=r.origin_entity, url=r.url, quote=r.quote,
                         published_at=r.published_at, retrieved_at=r.retrieved_at,
                         recorded_at=r.recorded_at, evidence_tier=r.evidence_tier,
                         evidence_class=r.evidence_class, confidence=r.confidence,
                         corroborating_origins=tuple(r.corroborating_origins))
            for r in evidence_pool.values()
        ),
        selection=EvidenceSelectionCounts(
            input_count=selection.input_count, accepted_count=selection.accepted_count,
            filtered_count=selection.filtered_count, reasons=dict(selection.reasons()),
        ),
        quality=evidence_quality,
    )

    # ---- freshness 總表 ----------------------------------------------------
    freshness_items = [
        FreshnessItem(source=name, status=state.status, as_of=state.as_of,
                      age_days=state.age_days, reason=state.reason)
        for name, state in context.freshness.items()
    ]
    dated = [r.published_at for r in evidence_pool.values() if r.published_at]
    if dated:
        newest = max(dated)
        freshness_items.append(FreshnessItem(
            source="graph_evidence_latest_published", status="available", as_of=newest,
            age_days=float((today - newest).days),
            reason="最新一份引用文件的發表日；圖本身沒有「最後載入」時間"))
    else:
        freshness_items.append(FreshnessItem(source="graph_evidence_latest_published", status="missing",
                                             as_of=None, age_days=None, reason="沒有任何帶 published_at 的引用"))
    freshness_items.append(FreshnessItem(
        source="session_judgment",
        status=("stale" if judgment_not_current else "available") if signal else "missing",
        as_of=judged_on,
        age_days=float((today - judged_on).days) if judged_on else None,
        reason=(f"refresh={thesis_refresh.state}：{stale_reason}" if (thesis_refresh and judgment_not_current)
                else stale_reason) if signal else no_signal))
    dec_as_of = _as_date(decision_facts.coverage_created_at) if decision_facts else None
    freshness_items.append(FreshnessItem(
        source="decision_store_coverage",
        status="available" if decision_facts and dec_as_of else "missing",
        as_of=dec_as_of, age_days=float((reference_day - dec_as_of).days) if dec_as_of else None,
        reason=(None if dec_as_of else (decision_facts_reason or "無 coverage assessment"))
        if not (dec_as_of and as_of_mode) else f"距 as-of {as_of_iso} 的天數；事實已依 as_of 歷史過濾"))

    # =======================================================================
    # P. Refresh／dependency status（只組裝 alpha.refresh 的輸出）
    # =======================================================================
    attention = report.attention
    refresh_section = RefreshStatusSection(
        meta=SectionMeta(
            status="available" if report.artifacts else "missing",
            basis="deterministic" if report.artifacts else "none", authority=A_REFRESH,
            capability=CAP_DEPENDENCY_IMPACT, as_of=reference_day,
            reason=(f"overall={report.overall}；需要動作 {len(attention)} 項；變更偵測={detection}"
                    if report.artifacts else "沒有任何研究成果可評估（無判斷、無模型）"),
            warnings=("state 只回答「相對於依賴，這個成果還能不能當 current」——不是新事實、不是新判斷、不改 thesis。",
                      "recalculate＝確定性輸入變了（不需判斷）；review_required＝依據 material change（要人重看）；"
                      "invalidated＝前提不成立；stale＝只是排程到期；superseded＝歷史。",
                      "price-only 變化不觸發任何研究判斷複查（v1 materiality 立場，見 alpha/refresh/policy.py）。"),
        ),
        overall=report.overall, policy_version=report.policy_version, counts=report.counts,
        items=tuple(RefreshItem(
            artifact_type=a.artifact_type, artifact_id=a.artifact_id, label=a.label, state=a.state,
            reasons=a.reasons, changed_refs=a.changed_refs, dependency_refs=a.dependency_refs,
            detected_at=a.detected_at, established_at=a.established_at,
            required_action=a.required_action, propagated_from=a.propagated_from, kind=a.kind,
        ) for a in report.artifacts),
        changes=tuple(ChangeItem(
            change_id=c.change_id, change_type=c.change_type, authority=c.authority,
            changed_ref=c.changed_ref, observed_at=c.observed_at, effective_at=c.effective_at,
            old_version=c.old_version, new_version=c.new_version, material_fields=c.material_fields,
            detail=c.detail, target_artifact=c.target_artifact,
        ) for c in report.changes),
        excluded_changes=dict(report.excluded_changes), excluded_artifacts=dict(report.excluded_artifacts),
        notes=tuple(refresh_notes) + report.notes, digest=report.digest, change_detection=detection,
        judged_context_matches=(None if signal is None else not signal_stale),
    )

    warnings = [JUDGMENT_WARNING, CORRELATION_WARNING]
    if as_of_mode:
        warnings.append(
            f"as-of 視角（{as_of_iso}）：Engine A 投影、Engine C 時序、Decision Store 事實皆已依 as_of "
            "歷史過濾（cohort／decision／coverage／lifecycle 事件／variant perception 的時間戳）；"
            "thesis/*.json 與檢核點沒有歷史，一律 not_applicable；到期狀態以 as_of 為今天判定")
    if signal is not None and judgment_not_current:
        warnings.append(f"session 判斷 {STATUS_LABEL.get(judgment_status, judgment_status)}：{stale_reason}")
    if attention:
        counts = report.counts
        warnings.append(
            f"⚠ {len(attention)} 項研究成果需要動作（review_required {counts['review_required']}／"
            f"invalidated {counts['invalidated']}／recalculate {counts['recalculate']}／stale {counts['stale']}）"
            "——見 refresh_status；引擎不改任何判斷，只標 state")
    if detection == "not_run":
        warnings.append("refresh：本次未執行 authority 變更偵測，只評估了 core 可導出的變化"
                        "（排程到期、review 條件、會計期間推進）；digest 不符時沿用整份 stale 的舊語意")
    if signal is None:
        warnings.append("尚無 session 判斷：Q2–Q5、thesis、variant view、情境、disproof 條件皆缺；"
                        "跑 `python -m alpha research " + ticker + " -o packet.json` 產研究包後由 session 判斷")
    warnings.extend(identity_warnings)
    if problems:
        warnings.append("Decision Store 的 catalyst／disproof／expiry 設定不完整：" + "；".join(problems))
    # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`target_reached`（目標價到了沒）退役。**
    # 它比的是現價 vs base／賭注目標價，兩個目標價都隨估值鏈與 E 組退役。
    # **AGENTS D3 的判準沒有退役**（`realized` 只提醒、不觸發出場）——它現在的家是候選狀態
    # 「已定價等回落」（Phase 3 的五值封閉字彙），而不是一個由目標價算出來的布林。
    argument_section = _argument_section(
        company_label=identity_section.company_label, company_id=identity_section.company_id,
        structural=structural_section, variant=variant_section, falsification=falsification_section,
        catalysts=catalyst_section, lifecycle=identity_section.lifecycle, narrative=dict(narrative_context or {}),
        reporting_currency=reporting_currency, reference_day=reference_day)
    brief_section = _investor_brief_section(
        brief_records, brief_parse_errors,
        as_of=context.as_of, today=today, reference_day=reference_day,
        price=market_section.price, consensus=consensus_section, catalysts=catalyst_section,
        refresh_overall=refresh_section.overall, gap=expectation_gap_section,
        )

    return AlphaInvestmentView(
        schema_version=SCHEMA_VERSION,
        identity=identity_section, variant_view=variant_section,
        structural_thesis=structural_section, causal_paths=causal_section,
        fundamentals=fundamentals_section, consensus=consensus_section,
        expectation_gap=expectation_gap_section, catalysts=catalyst_section,
        falsification=falsification_section, scenarios=scenario_section,
        market=market_section,
        wipeout_flags=_wipeout_section(wipeout, reason=wipeout_reason, reference_day=reference_day),
        evidence=evidence_section,
        freshness=tuple(freshness_items), refresh_status=refresh_section,
        investor_brief=brief_section, argument=argument_section, warnings=tuple(warnings),
    )


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Daily Brief 用的精簡摘要（純選取，不重算）
# ---------------------------------------------------------------------------

def compact_card(view: AlphaInvestmentView) -> dict[str, Any]:
    """每檔一列的摘要，給 Daily Brief 首屏之後的「Alpha Card 摘要」用。

    ⚠ 只做選取：所有值直接取自 view 的 Datum；缺席就帶 reason，不填 0。
    """
    def _val(d: Datum) -> Any:
        return d.value if d.is_known else None

    q = {d.key.removesuffix("_score"): _score_summary(d) for d in view.variant_view.scores}
    cons_growth = next(d for d in view.consensus.items if d.key == "revenue_estimate_next_fy_growth")
    analysts = next(d for d in view.consensus.items if d.key == "analyst_count")
    watch = view.catalysts.watch_state
    next_cp = view.catalysts.checkpoints[0] if view.catalysts.checkpoints else None
    not_modeled_keys = [name for name, cap in view.capability_map().items() if cap["status"] == "not_modeled"]
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`market_implied_eps_growth`／`internal_vs_consensus`／
    # `valuation`／`implied_return`／`internal_fundamentals_status` 五格隨估值鏈退役，卡片上整格移除。
    return {
        "ticker": view.identity.ticker,
        "company_id": view.identity.company_id,
        "company_label": view.identity.company_label,
        "as_of": view.identity.as_of.isoformat() if view.identity.as_of else None,
        "scores": q,
        "signal": {
            "has_signal": view.identity.signal.has_signal,
            "context_matches": view.identity.signal.context_matches,
            "weakest_axis": view.identity.signal.weakest_axis,
            "reason": view.identity.signal.reason,
        },
        "consensus_revenue_growth": {
            "value": _val(cons_growth), "status": cons_growth.status, "basis": cons_growth.basis,
            "analyst_count": _val(analysts),
        },
        "catalyst": {
            "state": (watch.value or {}).get("state") if watch.is_known else None,
            "state_label": (watch.value or {}).get("label") if watch.is_known else None,
            "days_to_expiry": (watch.value or {}).get("days_to_expiry") if watch.is_known else None,
            "next_checkpoint": next_cp.date.isoformat() if next_cp else None,
            "next_checkpoint_confidence": next_cp.date_confidence if next_cp else None,
            # None＝不知道（沒有 session 判斷／as-of 模式沒有投影），不是 0
            "structured_count": (len(view.catalysts.structured)
                                 if view.identity.signal.has_signal else None),
            "checkpoint_count": (len(view.catalysts.checkpoints)
                                 if view.identity.point_in_time_mode == "current" else None),
            "reason": None if watch.is_known else watch.reason,
        },
        "disproof": {
            "condition_count": (len(view.falsification.conditions)
                                if view.identity.signal.has_signal else None),
            "narrative_present": view.falsification.narrative_disproof.is_known,
            "problems": list(view.catalysts.problems),
        },
        "research_status": view.identity.lifecycle.research_status,
        "point_in_time_mode": view.identity.point_in_time_mode,
        # Step 0.5：refresh 摘要——只抄 refresh_status，不重算 impact
        "refresh": {
            "overall": view.refresh_status.overall,
            "change_detection": view.refresh_status.change_detection,
            "counts": {k: view.refresh_status.counts.get(k, 0)
                       for k in ("review_required", "invalidated", "recalculate", "stale")},
            "attention": [{"artifact": f"{i.artifact_type}:{i.artifact_id}", "state": i.state,
                           "reason": (i.reasons[0] if i.reasons else None)}
                          for i in view.refresh_status.items
                          if i.state in ("review_required", "invalidated", "recalculate", "stale")][:6],
        },
        "not_modeled": not_modeled_keys,
        "warnings": list(view.warnings),
    }


def _score_summary(datum: Datum) -> dict[str, Any]:
    value = datum.value if datum.is_known and isinstance(datum.value, dict) else {}
    return {"status": datum.status, "basis": datum.basis,
            "effective": value.get("effective"),
            "session_level": value.get("session_level"),
            "reason": None if datum.is_known else datum.reason}


__all__ = ["DecisionFacts", "build_alpha_investment_view", "compact_card",
           "CORRELATION_WARNING", "JUDGMENT_WARNING"]
