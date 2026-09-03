"""Phase 2 vertical slice：`ResearchContext` 組裝、Q1 計分、session judgment 驗證。

不需要 Neo4j／Engine C——全部跑在 fake provider 上。
真實資料的端到端見 `python -m alpha research COHR`（本檔末尾有一條可選的整合測試）。
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from alpha.context import build_research_context, structural_score
from alpha.contracts import (
    ConsensusSnapshot, EvidenceRef, FreshnessState, FundamentalsSnapshot, MarketSnapshot,
    ScarcityInputs,
)
from alpha.errors import ContractViolation
from alpha.evidence_quality import assess_evidence_quality
from alpha.identity import CompanyId, EntityId, Ticker
from alpha.models import build_packet, compose_signal
from alpha.testing import FakeGraphResearchProvider, evidence

COMPANY = CompanyId("co:coherent")
TICKER = Ticker("COHR")


def _graph_ref(evidence_class: str = "externally_corroborated") -> EvidenceRef:
    return EvidenceRef(ref=f"graph://edge/x/{evidence_class}", kind="graph_edge",
                       evidence_class=evidence_class, evidence_tier=1)


def _measurement() -> EvidenceRef:
    return EvidenceRef(ref="engine_c://financial_snapshot/COHR/2026-09-02",
                       kind="engine_c_snapshot", origin_entity="yfinance",
                       published_at=date(2026, 9, 2))


class _FakeFundamentals:
    """Engine C 的 in-memory 替身。"""

    def fundamentals(self, ticker, *, as_of=None):
        if ticker is None:
            return FundamentalsSnapshot(), FreshnessState(None, None, "missing", "未上市")
        return (
            FundamentalsSnapshot(gross_margin=0.375, revenue_ttm=7.1e9,
                                 segment_revenue_share=None,
                                 evidence=(_measurement(),)),
            FreshnessState(date(2026, 9, 2), 1.0, "available"),
        )

    def market(self, ticker, *, as_of=None):
        if ticker is None:
            return MarketSnapshot(), FreshnessState(None, None, "missing", "未上市")
        return (
            MarketSnapshot(price=268.64, bar_date=date(2026, 9, 2),
                           evidence=(_measurement(),)),
            FreshnessState(date(2026, 9, 2), 1.0, "available"),
        )

    def consensus(self, ticker, *, as_of=None):
        if ticker is None:
            return ConsensusSnapshot(), FreshnessState(None, None, "missing", "未上市")
        return (
            ConsensusSnapshot(analyst_count=22, forward_pe=19.25, trailing_pe=65.36,
                              evidence=(_measurement(),)),
            FreshnessState(date(2026, 9, 2), 1.0, "available"),
        )


#: fake 的圖證據刻意帶 `evidence_class`——真實 provider 就是這樣填的
#: （排序列不帶 origin_entity，L8 判定由 `evidence_class` 承載）。
#: 不帶的話 fake 會退化成「1 個 origin ＝ 供應商自報」，測到的是 fixture 不是程式。
_CORROBORATED = EvidenceRef(
    ref="graph://assertion/e1", kind="graph_edge",
    evidence_class="externally_corroborated", evidence_tier=1,
    published_at=date(2026, 5, 1),
)
_SELF_REPORTED = EvidenceRef(
    ref="graph://assertion/weak", kind="graph_edge",
    evidence_class="self_reported", evidence_tier=4,
    published_at=date(2026, 5, 1),
)


def _build():
    return build_research_context(
        ticker=TICKER, company_id=COMPANY,
        graph_provider=FakeGraphResearchProvider(
            company_id=COMPANY, evidence_pool=(_CORROBORATED, _SELF_REPORTED)),
        fundamentals_provider=_FakeFundamentals(),
    )


# ---------------------------------------------------------------------------
# Q1：deterministic，且佐證項不得跨階
# ---------------------------------------------------------------------------

def test_structural_score_is_deterministic_from_admitted_facts() -> None:
    """判斷已經在入圖時做過了——Q1 是已核准事實的函數，不是新的判斷。"""
    inputs = ScarcityInputs(substitutability=5, sole_source=True,
                            qualification_status="designed_in",
                            evidence=(_graph_ref(),))
    score, trace = structural_score(inputs)
    assert score is not None and trace is not None
    assert score.declared == 0.98                 # 0.90 基階 ＋ 0.04 ＋ 0.04
    assert trace.rule_version.startswith("structural-scarcity/")


def test_bonus_budget_is_structurally_smaller_than_half_a_band() -> None:
    """**不做加權總分的機械保證，不是靠人記得。**

    所有佐證項加起來的上限必須小於半個階距——否則「很多個弱理由」就能
    合成一個假的強理由（2026-08-21 pq1：`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`
    壓過真正的資本承諾事件）。

    ⚠ 這條斷言的對象是**常數本身**，不是某一個 case。第一版只測了
    「sub=4 全加成 vs sub=5 裸值」，而在那個 case 上限根本不 binding——
    突變工具當場抓到它是空跑的。
    """
    from alpha import context as ctx

    max_possible_bonus = ctx._SOLE_SOURCE_BONUS + max(ctx._QUALIFICATION_BONUS.values())
    budget = min(ctx._MAX_ADJUSTMENT, max_possible_bonus)
    bands = sorted(ctx._SUBSTITUTABILITY_BAND.values())
    smallest_gap = min(b - a for a, b in zip(bands, bands[1:]))
    assert budget < smallest_gap / 2, (
        f"佐證項預算 {budget} 必須小於最小階距的一半 {smallest_gap / 2}"
    )


@pytest.mark.parametrize("qualification", ["designed_in", "qualified", "qualifying",
                                           "sampling", "none", None])
@pytest.mark.parametrize("sole_source", [True, False, None])
@pytest.mark.parametrize("substitutability", [1, 2, 3, 4, 5])
def test_no_combination_of_bonuses_can_cross_a_band(
    substitutability: int, sole_source: bool | None, qualification: str | None
) -> None:
    """**掃過整個狀態空間**（5 × 3 × 6 = 90 組），不是只測當初想到的那一組。

    `historical-failure-matrix.md` §5：多維 gate 不得只做 regression example——
    「修掉已知組合，但另一個組合仍可繞過 invariant」是這類事故的標準形狀。

    這裡的 invariant：**任何加成組合都不得讓低一階的替代難度贏過高一階的裸值。**
    """
    from alpha import context as ctx

    loaded, _ = structural_score(ScarcityInputs(
        substitutability=substitutability, sole_source=sole_source,
        qualification_status=qualification, evidence=(_graph_ref(),)))
    if substitutability >= 5:
        return                          # 已是最高階，沒有更高的可比
    bare_higher, _ = structural_score(ScarcityInputs(
        substitutability=substitutability + 1, evidence=(_graph_ref(),)))
    assert loaded.declared < bare_higher.declared, (
        f"sub={substitutability} 加滿（sole_source={sole_source}, "
        f"qualification={qualification}）＝{loaded.declared} "
        f"不得贏過 sub={substitutability + 1} 裸值＝{bare_higher.declared}"
    )


def test_missing_substitutability_yields_none_not_zero() -> None:
    score, trace = structural_score(ScarcityInputs(evidence=(_graph_ref(),)))
    assert score is None and trace is None


def test_score_without_evidence_is_refused() -> None:
    """沒有 provenance 的分數不得存在（INV-6）。"""
    score, _ = structural_score(ScarcityInputs(substitutability=5, evidence=()))
    assert score is None


# ---------------------------------------------------------------------------
# 量測 ≠ 佐證（2026-09-03 第一條 vertical slice 撞出來的類別錯誤）
# ---------------------------------------------------------------------------

def test_measurements_do_not_count_toward_l8_independence() -> None:
    """**行情快照不是「一個獨立來源」。**

    L8 問的是「這個**主張**有幾個獨立的人說」；一份股價快照是**量測**不是說法。
    混在一起會讓「引用了財務資料」變成「證據變弱了」——完全反了。

    實測後果：COHR 的 `value_capture` 引用「NVIDIA 供應邊（externally_corroborated）」
    ＋「Engine C 快照（origin=yfinance）」，第一版把 declared 0.75 壓成 **0.0**。
    """
    mixed = assess_evidence_quality([_graph_ref(), _measurement()])
    graph_only = assess_evidence_quality([_graph_ref()])
    assert mixed.level == graph_only.level == "corroborated"
    assert mixed.ceiling > 0.0
    assert mixed.independent_origins == 0        # 量測不計入
    assert mixed.total_refs == 2                 # 但仍在帳上（不靜默丟棄）


def test_measurement_only_evidence_supports_a_bounded_hypothesis() -> None:
    """只有量測時撐得起 bounded hypothesis，撐不起「已被獨立印證」。"""
    quality = assess_evidence_quality([_measurement()])
    assert quality.level == "bounded_hypothesis"
    assert "量測" in quality.reason


def test_no_evidence_at_all_is_unknown() -> None:
    assert assess_evidence_quality([]).level == "unknown"


# ---------------------------------------------------------------------------
# ResearchContext 組裝
# ---------------------------------------------------------------------------

def test_context_build_produces_q1_and_records_notes() -> None:
    build = _build()
    assert build.context.digest.startswith("sha256:")
    assert build.structural is not None
    assert build.notes, "組裝過程的取捨要現形（例如 Q1 取了哪一條邊）"
    assert any("不做平均" in n for n in build.notes)


def test_context_takes_the_strongest_edge_not_the_average() -> None:
    """多條邊不會讓一條弱的邊變強——**不平均、不加總**（補償性）。"""
    build = _build()
    assert build.context.structural.substitutability == 5


def test_packet_tells_the_session_not_to_re_judge_q1() -> None:
    """Q1 已過 admission gate；讓 session 再判一次＝開第二個沒有 gate 的入口。"""
    packet = build_packet(_build())
    note = packet.deterministic["structural_score_q1"]["_note"]
    assert "不要重新判斷" in note
    assert "structural" not in packet.axis_prompts


# ---------------------------------------------------------------------------
# session judgment 的驗證（L15：先解析身分，再查權限）
# ---------------------------------------------------------------------------

def _judgment(**overrides):
    ref = _CORROBORATED.ref
    weak_ref = _SELF_REPORTED.ref
    base = {
        "axes": {
            # 引用外部印證的邊 → 不該被壓
            "value_capture": {"level": "strong", "reason": "客戶端資本承諾",
                              "evidence": [ref]},
            "earnings_exposure": {"level": "unknown",
                                  "reason": "Engine C 無 segment revenue", "evidence": []},
            # 只引用供應商自報的邊 → **該軸**被壓到 0，但不得波及上面那一軸
            "expectation_gap": {"level": "strong", "reason": "只有自報證據",
                                "evidence": [weak_ref]},
            "catalyst": {"level": "unknown", "reason": "無結構化催化劑來源",
                         "evidence": []},
        },
        "direction": "long", "confidence": 0.45, "expected_horizon": "2-4 quarters",
        "thesis": "…", "variant_view": "市場隱含 X／本 thesis Y／催化劑 Z",
        "bull_case": "…", "base_case": "…", "bear_case": "…",
        "disproof_conditions": [{
            "condition": "毛利率連兩季低於 40.2%", "check_frequency": "quarterly",
            "action_within_48h": "強制 review",
        }],
    }
    base.update(overrides)
    return base


def test_session_judgment_composes_a_signal() -> None:
    signal = compose_signal(_build(), _judgment())
    assert signal.structural_score is not None          # 由程式算
    assert signal.value_capture_score is not None       # 由 session 判
    assert signal.earnings_exposure_score is None       # unknown ≠ 0
    assert signal.catalyst_score is None
    assert signal.is_incomplete
    assert signal.weakest == "expectation_gap"      # 被自報證據壓到 0


def test_session_cannot_override_the_deterministic_axis() -> None:
    """structural 不接受 session 覆寫——admission gate 之後不得再開判斷入口。"""
    judgment = _judgment()
    judgment["axes"]["structural"] = {"level": "very_strong", "reason": "我說了算",
                                      "evidence": []}
    with pytest.raises(ContractViolation, match="structural"):
        compose_signal(_build(), judgment)


def test_unresolvable_evidence_reference_is_rejected() -> None:
    """**引用必須解析得到 `ResearchContext` 內的物件。**

    放寬解析等於讓引用去尋找能通過的權威——那正是 L8／L15 要防的
    authority laundering，也是 F-22（22 次資本歸零）的反面教訓：
    修法是**在源頭消除歧義**，不是放寬比對。
    """
    judgment = _judgment()
    judgment["axes"]["value_capture"]["evidence"] = ["graph://assertion/i_made_this_up"]
    with pytest.raises(ContractViolation, match="不在 ResearchContext"):
        compose_signal(_build(), judgment)


def test_level_without_evidence_is_rejected() -> None:
    """給了分數卻沒有引用 → reject。答不出來要填 unknown，不是給一個空分數。"""
    judgment = _judgment()
    judgment["axes"]["value_capture"]["evidence"] = []
    with pytest.raises(ContractViolation, match="evidence"):
        compose_signal(_build(), judgment)


def test_reason_is_mandatory() -> None:
    judgment = _judgment()
    judgment["axes"]["expectation_gap"]["reason"] = "   "
    with pytest.raises(ContractViolation, match="reason"):
        compose_signal(_build(), judgment)


def test_unregistered_level_is_rejected() -> None:
    judgment = _judgment()
    judgment["axes"]["value_capture"]["level"] = "pretty_good"
    with pytest.raises(ContractViolation, match="未登記"):
        compose_signal(_build(), judgment)


def test_ceiling_is_applied_per_axis_not_globally() -> None:
    """**「這組證據能撐多高」的「這組」是該軸自己引用的那組。**

    用 context-wide 的品質當所有軸的上限，會讓一個弱軸把好軸一起拖下水。
    """
    build = _build()
    signal = compose_signal(build, _judgment())
    # 兩軸宣告值相同（strong=0.75），但引用的證據品質不同 →
    # 生效值必須不同。若上限是全域的，兩者會一起被壓或一起不被壓。
    assert (signal.value_capture_score.declared
            == signal.expectation_gap_score.declared == 0.75)
    assert signal.value_capture_score.effective == 0.75          # 外部印證 → 不壓
    assert signal.value_capture_score.downgrade_reason is None
    assert signal.expectation_gap_score.effective == 0.0         # 自報 → 壓到 0
    assert (signal.expectation_gap_score.downgrade_reason
            == "evidence_quality_ceiling")


def test_signal_carries_the_context_digest() -> None:
    """`AlphaSignal` **引用** ResearchContext，不複製它（§4 的銜接方式）。"""
    build = _build()
    signal = compose_signal(build, _judgment())
    assert signal.research_context_digest == build.context.digest


# ---------------------------------------------------------------------------
# as-of 保險絲在 concrete provider 上也要響
# ---------------------------------------------------------------------------

def test_concrete_graph_provider_refuses_as_of() -> None:
    """Engine A 沒有 as-of 能力——**明確拒絕，不靜默回傳當前資料**（F-31）。"""
    from alpha.errors import PointInTimeUnsupported
    from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider

    provider = Neo4jGraphResearchProvider(driver=object())
    with pytest.raises(PointInTimeUnsupported, match="沒有時間欄位"):
        provider.get_bottlenecks(as_of=date(2026, 6, 30))


def test_phase5_methods_raise_instead_of_returning_empty() -> None:
    """回空集合會讓「還沒實作」與「查無結果」在同一個訊號上同形（L13）。"""
    from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider

    provider = Neo4jGraphResearchProvider(driver=object())
    with pytest.raises(NotImplementedError, match="Phase 5"):
        provider.get_structural_changes_since(date(2026, 1, 1))
