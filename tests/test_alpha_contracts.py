"""`AlphaSignal`／`EvidenceRef`／`Score`／`RankedList` 的契約測試。

每條斷言都對應 `docs/refactor/historical-failure-matrix.md` 的一筆歷史事故或一條
hard invariant；註解裡標出是哪一筆，讓未來的人知道**刪掉這條會放回什麼 bug**。
"""
from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from alpha import contracts
from alpha.contracts import (
    AXES, AlphaSignal, Catalyst, ComponentTrace, DisproofCondition, EvidenceRef,
    OrderingRule, RankedList, Score, content_digest,
)
from alpha.errors import ContractViolation
from alpha.identity import CompanyId, Ticker
from alpha.testing import evidence


def _trace(trace_id: str = "ct_1") -> ComponentTrace:
    return ComponentTrace(
        trace_id=trace_id, rule_version="v1", evidence_refs=(evidence(),)
    )


def _disproof() -> DisproofCondition:
    return DisproofCondition(
        condition="Q3 毛利率跌破 40.2%",
        check_frequency="quarterly",
        action_within_48h="強制 review → retire 或 revise thesis",
    )


def build_signal(**overrides) -> AlphaSignal:
    """一個最小合法 `AlphaSignal`（五軸齊全）。"""
    traces = {f"ct_{axis}": _trace(f"ct_{axis}") for axis in AXES}
    payload = dict(
        ticker=Ticker("COHR"),
        company_id=CompanyId("co:coherent"),
        as_of=date(2026, 6, 30),
        structural_score=Score(0.94, 0.94, "ct_structural"),
        value_capture_score=Score(0.82, 0.82, "ct_value_capture"),
        earnings_exposure_score=Score(0.79, 0.79, "ct_earnings_exposure"),
        expectation_gap_score=Score(0.31, 0.31, "ct_expectation_gap"),
        catalyst_score=Score(0.55, 0.55, "ct_catalyst"),
        direction="long",
        confidence=0.78,
        expected_horizon="2-4 quarters",
        thesis="CPO 外部光源的結構瓶頸",
        variant_view="市場隱含 X／本 thesis 認為 Y／催化劑 Z",
        bull_case="...", base_case="...", bear_case="...",
        disproof_conditions=(_disproof(),),
        model_components=traces,
    )
    payload.update(overrides)
    return AlphaSignal(**payload)


# ---------------------------------------------------------------------------
# AlphaSignal 的形狀（import 時就強制）
# ---------------------------------------------------------------------------

def test_alpha_signal_has_no_position_fields() -> None:
    """`AlphaSignal != Position`。研究觀點不得攜帶部位語意。

    空跑檢查：把 `weight` 加進 `AlphaSignal` → `import alpha` 直接失敗。
    """
    names = {f.name for f in dataclasses.fields(AlphaSignal)}
    for field_name in names:
        parts = set(field_name.lower().split("_"))
        assert not (parts & contracts.FORBIDDEN_POSITION_TOKENS), field_name


def test_alpha_signal_has_no_composite_scalar() -> None:
    """v1 **不產生 scalar `value`／`alpha`**（2026-09-03 使用者定案）。

    依據是 2026-08-21 pq1 實測：`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`——
    三個各自成立的弱理由相加就壓過真正的資本承諾事件。**加權總分有補償性，
    字典序沒有。** 五個 score 有完全相同的形狀，所以套用同一結論。
    """
    names = {f.name.lower() for f in dataclasses.fields(AlphaSignal)}
    assert not (names & contracts.FORBIDDEN_COMPOSITE_FIELDS)


def test_shape_guard_is_not_vacuous() -> None:
    """守衛本身要會紅——否則上面兩條只是在描述現況，不是在守住它。"""

    @dataclasses.dataclass(frozen=True)
    class WithPosition:
        target_weight: float

    @dataclasses.dataclass(frozen=True)
    class WithComposite:
        value: float

    for cls in (WithPosition, WithComposite):
        with pytest.raises(ContractViolation):
            contracts.assert_alpha_signal_shape(cls)


# ---------------------------------------------------------------------------
# score ↔ trace ↔ evidence 的鏈不得斷（INV-6）
# ---------------------------------------------------------------------------

def test_score_without_trace_is_rejected() -> None:
    """算不出來就不出分數，不是出一個沒有推導過程的分數。"""
    with pytest.raises(ContractViolation, match="model_components"):
        build_signal(structural_score=Score(0.9, 0.9, "ct_missing"))


def test_trace_without_evidence_is_rejected() -> None:
    """所有重要 conclusion 必須可回溯至 evidence（INV-6）。"""
    traces = {f"ct_{axis}": _trace(f"ct_{axis}") for axis in AXES}
    traces["ct_structural"] = ComponentTrace("ct_structural", "v1", evidence_refs=())
    with pytest.raises(ContractViolation, match="EvidenceRef"):
        build_signal(model_components=traces)


def test_disproof_requires_frequency_and_action() -> None:
    """L7：欄位有填但沒有後續流程＝貼了一個永遠不會響的火警警報。"""
    with pytest.raises(ContractViolation, match="check_frequency"):
        DisproofCondition(condition="x", check_frequency="  ", action_within_48h="y")
    with pytest.raises(ContractViolation, match="action_within_48h"):
        DisproofCondition(condition="x", check_frequency="quarterly", action_within_48h="")


def test_signal_requires_at_least_one_disproof() -> None:
    with pytest.raises(ContractViolation, match="disproof"):
        build_signal(disproof_conditions=())


# ---------------------------------------------------------------------------
# Score：declared vs effective（F-25）
# ---------------------------------------------------------------------------

def test_effective_may_not_exceed_declared() -> None:
    with pytest.raises(ContractViolation):
        Score(declared=0.4, effective=0.9, trace_id="t")


def test_downgrade_requires_a_reason() -> None:
    """因果不得被截斷（L12）：生效值低於宣告值必須說得出為什麼。"""
    with pytest.raises(ContractViolation, match="downgrade_reason"):
        Score(declared=0.9, effective=0.4, trace_id="t")


def test_weakest_uses_effective_not_declared() -> None:
    """F-25 的第一個出口：`weakest`（＝「該補什麼」）必須讀生效值。

    ⚠ 刻意設計成**兩種讀法給出不同答案**：
    `structural` 宣告 0.94 但引用不成立（effective 0.10）；
    `expectation_gap` 宣告與生效都是 0.31。
    讀 effective → weakest 是 structural（0.10）；讀 declared → 會變成
    expectation_gap（0.31 < 0.94）。第一版測試沒有這個對比，於是**它是空跑的**
    ——突變工具在 2026-09-03 當場抓到。
    """
    signal = build_signal(
        structural_score=Score(0.94, 0.10, "ct_structural",
                               downgrade_reason="evidence_ref_unresolved"),
    )
    assert signal.structural_score.declared > signal.expectation_gap_score.declared
    assert signal.structural_score.effective < signal.expectation_gap_score.effective
    assert signal.weakest == "structural"


def test_tiebreak_uses_effective_not_declared() -> None:
    """F-25 的第二個出口：排序的 tie-break 分量也必須讀生效值。

    ⚠ 這一組**刻意讓 `weakest` 在兩筆之間完全相同**（都是 expectation_gap 0.20），
    好讓差異只可能來自 tie-break 分量。第一版測試的差異被 `weakest` 吸收掉，
    所以就算 `_rank_component` 改讀 declared 也不會紅。
    """
    base = dict(
        expectation_gap_score=Score(0.20, 0.20, "ct_expectation_gap"),
        value_capture_score=Score(0.50, 0.50, "ct_value_capture"),
        earnings_exposure_score=Score(0.50, 0.50, "ct_earnings_exposure"),
        catalyst_score=Score(0.50, 0.50, "ct_catalyst"),
    )
    intact = build_signal(structural_score=Score(0.90, 0.90, "ct_structural"), **base)
    downgraded = build_signal(
        structural_score=Score(0.90, 0.60, "ct_structural",
                               downgrade_reason="evidence_ref_unresolved"),
        **base,
    )
    # 兩筆的 weakest 與宣告值都一樣——差異只在生效值
    assert intact.weakest == downgraded.weakest == "expectation_gap"
    assert (intact.structural_score.declared
            == downgraded.structural_score.declared == 0.90)
    assert intact.ordering_key() != downgraded.ordering_key()
    assert intact.ordering_key() < downgraded.ordering_key()  # 升冪＝最佳在前


# ---------------------------------------------------------------------------
# None 不是 0
# ---------------------------------------------------------------------------

def test_none_is_not_zero() -> None:
    """`None`＝不知道（排最後並標 incomplete）；`0.0`＝我判斷它很弱。

    把 `None` 當 0 會讓「沒研究」看起來像「研究過但很弱」——兩者的下一步完全不同。
    """
    unknown = build_signal(expectation_gap_score=None)
    weak = build_signal(expectation_gap_score=Score(0.0, 0.0, "ct_expectation_gap"))

    assert unknown.is_incomplete and not weak.is_incomplete
    assert unknown.ordering_key() != weak.ordering_key()
    # incomplete 一律排在 complete 之後，不論其他維度多強
    assert weak.ordering_key() < unknown.ordering_key()
    assert unknown.weakest != "expectation_gap"  # None 不參與 weakest
    assert weak.weakest == "expectation_gap"

    # ⚠ 直接隔離排序分量。上面幾條的差異會被 `is_incomplete` 這個第一鍵吸收，
    # 所以就算 `_rank_component` 把 None 當成 0 也不會紅——突變工具當場抓到。
    assert contracts._rank_component(None) != contracts._rank_component(
        Score(0.0, 0.0, "t")
    )
    assert contracts._rank_component(None) == float("inf")
    assert contracts._rank_component(Score(0.0, 0.0, "t")) == 0.0
    # 而且 None 必須以 inf 出現在排序鍵裡，不得靜默變成 0
    assert float("inf") in unknown.ordering_key()
    assert float("inf") not in weak.ordering_key()


def test_all_unknown_signal_has_no_weakest() -> None:
    signal = build_signal(**{f"{axis}_score": None for axis in AXES})
    assert signal.weakest is None
    assert signal.known_axes == ()


# ---------------------------------------------------------------------------
# EvidenceRef：五套強度並列，三個時間欄位齊備
# ---------------------------------------------------------------------------

def test_evidence_ref_keeps_five_strength_vocabularies_separate() -> None:
    """L12 的相反錯誤：把五種不同的問題壓成一個答案，下游只能二選一。"""
    names = {f.name for f in dataclasses.fields(EvidenceRef)}
    assert {"evidence_tier", "demand_proof_level", "confidence",
            "evidence_class", "corroborating_origins"} <= names
    assert not (names & {"strength", "evidence_score", "quality"})


def test_evidence_ref_has_three_distinct_time_fields() -> None:
    """F-27：`snapshot_date`（我們何時取得）與 `bar_date`（事實屬於哪天）被壓成一欄。"""
    names = {f.name for f in dataclasses.fields(EvidenceRef)}
    assert {"published_at", "retrieved_at", "recorded_at"} <= names


def test_evidence_kind_is_a_closed_contract() -> None:
    """`EvidenceRef.kind` 是 contract 不是 taxonomy——打開它是 bug。"""
    with pytest.raises(ContractViolation, match="未登記"):
        EvidenceRef(ref="x", kind="whatever_i_want")


def test_catalyst_kind_is_a_registered_taxonomy() -> None:
    """F-18：自由字串卻決定行為，打錯不報錯、只是靜默沉底。"""
    assert Catalyst(kind="design_win", description="x").kind == "design_win"
    with pytest.raises(ContractViolation, match="未登記"):
        Catalyst(kind="desgin_win", description="x")  # 故意拼錯


# ---------------------------------------------------------------------------
# RankedList：截斷集合不得被當成全集（F-20）
# ---------------------------------------------------------------------------

def _ranked() -> RankedList[str]:
    rule = OrderingRule(name="test", version="v1", keys=("a",))
    return RankedList(
        rows=("co:coherent", "co:lumentum"),
        row_ids=("co:coherent", "co:lumentum"),
        full_ids=("co:coherent", "co:lumentum", "co:axt", "co:iqe"),
        ordering_rule=rule,
        truncated_at=2,
    )


def test_ranked_list_membership_reads_full_ids_not_rows() -> None:
    """F-20 實測：只帶前 N 名，於是排 11 名之後的公司被誤判成「不在排序裡」。"""
    ranked = _ranked()
    assert ranked.is_truncated
    assert len(ranked) == 2                      # rows 只有前兩名
    assert ranked.contains("co:axt")             # 但第三名確實在排序裡
    assert "co:iqe" in ranked
    assert not ranked.contains("co:nowhere")


def test_ranked_list_rejects_rows_outside_full_ids() -> None:
    rule = OrderingRule(name="test", version="v1", keys=("a",))
    with pytest.raises(ContractViolation, match="子集"):
        RankedList(rows=("x",), row_ids=("x",), full_ids=("y",), ordering_rule=rule)


# ---------------------------------------------------------------------------
# digest 穩定性
# ---------------------------------------------------------------------------

def test_content_digest_is_order_independent_and_stable() -> None:
    assert content_digest({"a": 1, "b": 2}) == content_digest({"b": 2, "a": 1})
    assert content_digest({"a": 1}) != content_digest({"a": 2})


# ---------------------------------------------------------------------------
# Identity：ticker 不是 entity identity（INV-1）
# ---------------------------------------------------------------------------

def test_company_id_and_ticker_are_not_interchangeable() -> None:
    """F-01～F-05 的型別層防線。

    用 `str` 時這四種識別字串可以互相賦值而不報錯，只能靠人記得；
    分成型別後 **runtime 就擋得住**。
    """
    from alpha.errors import IdentityError
    from alpha.identity import Exchange, InstrumentId, Ticker as T

    company = CompanyId("co:axt")
    ticker = T("AXTI")

    assert str(company) != str(ticker)
    assert company != ticker
    assert type(company) is not type(ticker)

    # entity id 不得被當成 ticker（F-01：憑名字猜 co:sivers）
    with pytest.raises(IdentityError):
        T("co:axt")
    # ticker 不得被當成 entity id
    with pytest.raises(IdentityError):
        CompanyId("AXTI")
    # 非公司的 entity id 不得被當成 CompanyId
    with pytest.raises(IdentityError):
        CompanyId("tech:cpo")
    # venue-qualified 執行代號不得冒充 research ticker（F-05：FRA:2DG vs SIVE.ST）
    with pytest.raises(IdentityError):
        T("FRA:2DG")
    assert str(InstrumentId(Exchange("FRA"), T("2DG"))) == "FRA:2DG"


def test_identifiers_serialise_as_scalars() -> None:
    """identifier 是純量，digest payload 不該被 `{"value": ...}` 淹沒。"""
    assert contracts._canonical(CompanyId("co:axt")) == "co:axt"
    assert contracts._canonical(Ticker("AXTI")) == "AXTI"
