"""`AlphaSignal` → Engine D 的 adapter。

這是研究→決策那條線接起來的地方，也是**最容易靜默丟資訊**的地方：
新五 score 與舊五軸不是同一組東西，往回塞必然有損。
本組測試的重點不是「轉得成功」，是**「損失有沒有現形」**。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.contracts import _canonical
from alpha.legacy_axes import LEGACY_AXIS_TO_SCORE
from decision_lab.adapters.alpha_signal import (
    LEGACY_AXES, SCORE_TO_LEGACY_AXIS, SCORES_WITHOUT_LEGACY_AXIS,
    AlphaSignalAdapterError, coverage_assessment_from_signal,
)
from tests.test_alpha_contracts import build_signal


def _payload(**overrides):
    return _canonical(build_signal(**overrides))


# ---------------------------------------------------------------------------
# 對應表兩邊必須一致
# ---------------------------------------------------------------------------

def test_forward_and_reverse_maps_agree() -> None:
    """`alpha/legacy_axes.py`（舊→新）與本 adapter（新→舊）必須是同一組對應。

    ⚠ 兩份對應表分屬不同 package，是**最典型會漂移的東西**（「清單會腐壞」）。
    這條把它們釘在一起。
    """
    forward = {axis: score for axis, score in LEGACY_AXIS_TO_SCORE.items()
               if score is not None}
    reverse = {score: axis for score, axis in SCORE_TO_LEGACY_AXIS.items()}
    assert forward == {axis: score for score, axis in reverse.items()}


def test_catalyst_has_no_legacy_home_in_either_direction() -> None:
    """Q5 兩個方向都沒有家——舊系統沒有這一軸，新系統塞不回去。"""
    assert "catalyst" in SCORES_WITHOUT_LEGACY_AXIS
    assert "catalyst" not in SCORE_TO_LEGACY_AXIS
    assert "catalyst" not in LEGACY_AXIS_TO_SCORE.values()


# ---------------------------------------------------------------------------
# 轉換結果符合 Engine D 的既有 schema
# ---------------------------------------------------------------------------

def test_produces_exactly_the_five_legacy_axes() -> None:
    """`sizing._validate_assessment` 要求**恰好**五軸——多一個少一個都拋。"""
    result = coverage_assessment_from_signal(_payload())
    assert set(result["assessment"]) == set(LEGACY_AXES)
    for axis in LEGACY_AXES:
        payload = result["assessment"][axis]
        assert {"level", "evidence_refs", "reason", "missing_data"} <= set(payload)
        assert payload["level"] in ("unknown", "bounded_hypothesis", "corroborated")


def test_the_result_passes_engine_d_validation() -> None:
    """**真正的驗收：Engine D 自己的 validator 收得下。**

    這條比「欄位齊全」強——它跑的是 production 那支 `_validate_assessment`。
    """
    from decision_lab.sizing import _validate_assessment

    result = coverage_assessment_from_signal(_payload())
    index = {ref: {"authorities": ("graph_source_assertion",)}
             for axis in result["assessment"].values()
             for ref in axis["evidence_refs"]}
    normalized, _ = _validate_assessment(result["assessment"], index)
    assert set(normalized) == set(LEGACY_AXES)


def test_unknown_score_becomes_unknown_axis_not_a_weak_one() -> None:
    """`None`（不知道）不得被塞成 `bounded_hypothesis`（判斷它很弱）。"""
    result = coverage_assessment_from_signal(_payload(expectation_gap_score=None))
    axis = result["assessment"]["valuation_payoff"]
    assert axis["level"] == "unknown"
    assert "alpha_score_unknown" in axis["missing_data"]


def test_effective_not_declared_drives_the_legacy_level() -> None:
    """F-25 的第三個出口：**往回塞時也必須用生效值**。

    宣告 corroborated 但引用不成立的分數，若用 `declared` 換算，
    Engine D 會看到一個假的強證據——而它是資本閘門的輸入。
    """
    from alpha.contracts import Score

    strong = coverage_assessment_from_signal(_payload())
    downgraded = coverage_assessment_from_signal(_payload(
        structural_score=Score(0.94, 0.10, "ct_structural",
                               downgrade_reason="evidence_ref_unresolved")))
    assert strong["assessment"]["technical_causal_link"]["level"] == "corroborated"
    assert downgraded["assessment"]["technical_causal_link"]["level"] == "bounded_hypothesis"
    assert "evidence_ref_unresolved" in (
        downgraded["assessment"]["technical_causal_link"]["missing_data"])


# ---------------------------------------------------------------------------
# 損失必須現形（INV-3：no silent drop）
# ---------------------------------------------------------------------------

def test_the_lossy_conversion_keeps_a_full_mirror() -> None:
    """轉換丟掉的東西**留在 payload 裡**，隨時可重建。"""
    result = coverage_assessment_from_signal(_payload())
    mirror = result["_alpha_signal"]
    assert mirror["research_context_digest"] is not None
    assert set(mirror["scores"]) == set(SCORE_TO_LEGACY_AXIS) | SCORES_WITHOUT_LEGACY_AXIS
    assert mirror["variant_view"]
    assert mirror["disproof_conditions"]
    assert "_lossy" in mirror


def test_catalyst_survives_in_the_mirror_even_though_it_has_no_axis() -> None:
    """Q5 沒有落點，**但不得因此消失**。"""
    result = coverage_assessment_from_signal(_payload())
    assert "catalyst" in result["_alpha_signal"]["scores_without_legacy_axis"]
    assert result["_alpha_signal"]["scores"]["catalyst"] is not None
    # 而且它**不在**五軸裡——沒有假裝有家
    assert all("catalyst" not in axis for axis in result["assessment"])


def test_evidence_quality_becomes_source_reliability_with_its_reason() -> None:
    """證據上限往回塞成分量是有損的——理由必須跟著，否則下游無從還原。"""
    from alpha.contracts import EvidenceQuality, Score

    # ⚠ 分數必須先壓到上限之下——否則 `AlphaSignal` 自己就會拒收
    # （契約在建構時就擋，不等 adapter）。這一條本身就是那道防線的旁證。
    capped = {f"{axis}_score": Score(0.5, 0.5, f"ct_{axis}") for axis in
              ("structural", "value_capture", "earnings_exposure",
               "expectation_gap", "catalyst")}
    result = coverage_assessment_from_signal(_payload(
        evidence_quality=EvidenceQuality(
            level="bounded_hypothesis", independent_origins=2, best_tier=2,
            total_refs=4, reason="僅 2 個獨立 origin_entity"),
        **capped))
    axis = result["assessment"]["source_reliability"]
    assert axis["level"] == "bounded_hypothesis"
    assert "2 個獨立" in axis["reason"]


def test_missing_evidence_quality_is_unknown_not_assumed_good() -> None:
    """沒有證據上限資訊時 fail closed——不得假設它很強。"""
    result = coverage_assessment_from_signal(_payload(evidence_quality=None))
    axis = result["assessment"]["source_reliability"]
    assert axis["level"] == "unknown"
    assert "evidence_quality_missing" in axis["missing_data"]


# ---------------------------------------------------------------------------
# Engine D 仍然不認識 alpha/
# ---------------------------------------------------------------------------

def test_adapter_takes_a_dict_not_an_alpha_object() -> None:
    """**Engine D 不 import `alpha/`。**

    adapter 吃序列化後的 payload，所以 Engine D 只知道「有人給了我一份研究結論」，
    不知道 `alpha/` 存在。序列化由呼叫端（composition root）負責。
    """
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "decision_lab" / "adapters" / "alpha_signal.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    imported = {
        (n.module or "").split(".")[0]
        for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
    } | {
        a.name.split(".")[0] for n in ast.walk(tree)
        if isinstance(n, ast.Import) for a in n.names
    }
    assert "alpha" not in imported


def test_non_mapping_payload_is_rejected() -> None:
    with pytest.raises(AlphaSignalAdapterError):
        coverage_assessment_from_signal("not a dict")  # type: ignore[arg-type]
