"""多跳因果的 confidence 規則。

**核心斷言只有一條：`CompanyImpact.confidence` 取路徑上最弱的一段，不取平均。**

為什麼這條值得一個測試檔：平均會讓「三段強＋一段完全沒證據」看起來比
「兩段中等」可靠——那正是 2026-08-21 pq1 排序踩過的補償性問題
（`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0` 壓過真正的資本承諾事件）。
多跳因果是這個病最容易復發的地方：跳數越多，可以互相補償的分量越多。
"""
from __future__ import annotations

import statistics
from datetime import date

import pytest

from alpha.causal import (
    CausalPath, CompanyImpact, ImpactConfidence, ImpactDirection, ImpactMagnitude,
    StructuralEvent, TimeHorizon,
)
from alpha.errors import ContractViolation
from alpha.identity import CompanyId, EntityId, Ticker
from alpha.testing import evidence

H, M, L, U = (ImpactConfidence.HIGH, ImpactConfidence.MEDIUM,
              ImpactConfidence.LOW, ImpactConfidence.UNKNOWN)


def _path(confidences: tuple[ImpactConfidence, ...]) -> CausalPath:
    nodes = tuple(f"n{i}" for i in range(len(confidences) + 1))
    return CausalPath(
        nodes=nodes,
        relations=tuple("supplies_to" for _ in confidences),
        link_confidences=confidences,
        evidence=(evidence(),),
    )


def _impact(path: CausalPath) -> CompanyImpact:
    return CompanyImpact(
        company_id=CompanyId("co:coherent"),
        ticker=Ticker("COHR"),
        direction=ImpactDirection.BENEFICIARY,
        magnitude=ImpactMagnitude.MEDIUM,
        time_horizon=TimeHorizon.QUARTERS,
        path=path,
        rationale=f"沿 {path.nodes[0]} 的供應鏈傳導到 {path.nodes[-1]}",
    )


# ---------------------------------------------------------------------------
# 最弱段，不是平均
# ---------------------------------------------------------------------------

def test_causal_confidence_is_weakest_link() -> None:
    """三段 HIGH ＋ 一段 UNKNOWN → confidence 必須是 UNKNOWN。"""
    path = _path((H, H, H, U))
    assert path.confidence is U
    assert _impact(path).confidence is U


def test_weakest_link_beats_the_average() -> None:
    """明確排除「取平均」的實作。

    (HIGH, HIGH, HIGH, UNKNOWN) 的平均是 2.25（≈ MEDIUM 偏上），
    而正確答案是 UNKNOWN。**兩者的下一步完全不同**：平均會說「這條鏈還行」，
    最弱段會說「先去補第四段的證據」。
    """
    confidences = (H, H, H, U)
    path = _path(confidences)
    mean = statistics.mean(c.value for c in confidences)
    assert mean > M.value                      # 平均看起來很不錯
    assert path.confidence.value < mean        # 但真實可信度低於平均
    assert path.confidence is U


def test_two_medium_links_beat_three_strong_plus_one_unknown() -> None:
    """補償性的直接反例：**多不等於強。**"""
    compensated = _path((H, H, H, U))          # 4 跳，看起來證據很多
    honest = _path((M, M))                     # 2 跳，每一段都中等
    assert honest.confidence.value > compensated.confidence.value


def test_no_link_confidence_means_unknown_not_high() -> None:
    """沒填就是不知道，不是「預設很好」——fail closed。"""
    path = CausalPath(nodes=("a", "b"), relations=("depends_on",),
                      evidence=(evidence(),))
    assert path.confidence is U


def test_weakest_link_is_reported_not_just_scored() -> None:
    """L12 末尾：**任何會改變輸出的輸入，都必須出現在該輸出自己的證據欄位裡。**

    只給一個 confidence 值而不說是哪一段最弱，下游只能猜該去補什麼。
    """
    path = _path((H, L, H))
    assert path.weakest_link_index == 1
    assert path.weakest_link == "n1 -supplies_to-> n2"


# ---------------------------------------------------------------------------
# 推論永遠是 derived
# ---------------------------------------------------------------------------

def test_company_impact_is_always_derived() -> None:
    """圖只存有逐字證據的關係；多跳推論要入圖必須另走 admission gate。"""
    with pytest.raises(ContractViolation, match="derived"):
        CompanyImpact(
            company_id=CompanyId("co:coherent"), ticker=None,
            direction=ImpactDirection.VICTIM, magnitude=ImpactMagnitude.LOW,
            time_horizon=TimeHorizon.YEARS, path=_path((M,)),
            rationale="n0 影響 n1", derived=False,
        )


def test_rationale_must_reference_the_path() -> None:
    """說不出經過哪裡的因果推論無法被檢查（L6 反幻覺的同一形狀）。"""
    with pytest.raises(ContractViolation, match="path"):
        CompanyImpact(
            company_id=CompanyId("co:coherent"), ticker=None,
            direction=ImpactDirection.BENEFICIARY, magnitude=ImpactMagnitude.HIGH,
            time_horizon=TimeHorizon.QUARTERS, path=_path((H,)),
            rationale="我覺得會漲",
        )


# ---------------------------------------------------------------------------
# 路徑形狀
# ---------------------------------------------------------------------------

def test_path_shape_is_validated() -> None:
    with pytest.raises(ContractViolation, match="兩個節點"):
        CausalPath(nodes=("a",), relations=())
    with pytest.raises(ContractViolation, match="nodes-1"):
        CausalPath(nodes=("a", "b", "c"), relations=("supplies_to",))
    with pytest.raises(ContractViolation, match="link_confidences"):
        CausalPath(nodes=("a", "b"), relations=("supplies_to",),
                   link_confidences=(H, M))


def test_structural_event_direction_is_closed() -> None:
    with pytest.raises(ContractViolation, match="tightening"):
        StructuralEvent(
            event_id="e", kind="capacity_constraint",
            subject_id=EntityId("mat:inp_substrate"), direction="sideways",
            observed_at=date(2026, 1, 1), evidence=(evidence(),),
        )
