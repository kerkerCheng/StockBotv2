"""舊五軸 → 新五 score 的單向轉換。

使用者 2026-09-03 定案：**新五軸取代舊五軸，不並存。** 但 Decision Store 是
append-only 的 private authority，268 筆歷史 payload 永遠不改寫（L10），
所以「乾淨轉換」＝**只有一個前進方向 ＋ 一個唯讀的歷史橋**。

真實資料的 dual run 見 `scripts/dualrun_axis_conversion.py`
（41 個 cohort、0 個無法解釋的差異）。
"""
from __future__ import annotations

import pytest

from alpha import legacy_axes
from alpha.contracts import AXES, EvidenceQuality
from alpha.errors import ContractViolation
from alpha.evidence_quality import assess_evidence_quality, from_legacy_level
from alpha.legacy_axes import (
    LEGACY_AXIS_TO_SCORE, UNMAPPED_SCORES, convert_axis_results, legacy_weakest,
)
from alpha.testing import evidence


def _axis(level: str, refs=("cohr_10_q_20260506",), **extra) -> dict:
    payload = {"level": level, "effective_level": level,
               "evidence_refs": list(refs), "reason": "fixture", "missing_data": []}
    payload.update(extra)
    return payload


def _legacy(**overrides) -> dict:
    base = {
        "source_reliability": _axis("corroborated"),
        "technical_causal_link": _axis("bounded_hypothesis"),
        "commercial_maturity": _axis("corroborated"),
        "financial_resilience": _axis("bounded_hypothesis"),
        "valuation_payoff": _axis("bounded_hypothesis"),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 對應表本身
# ---------------------------------------------------------------------------

def test_mapping_covers_every_legacy_axis_exactly_once() -> None:
    """五個舊軸都要有明確去向——包含「刻意沒有對應」的那一個。"""
    # ⚠ 對 SSOT 斷言，不是再寫一份 literal set。原版把五個軸名第三次抄在這裡
    # （`shared/assessment_axes.py`、`LEGACY_AXIS_TO_SCORE` 的鍵、這裡），
    # 於是「對應表漏了新軸」與「測試也忘了更新」會一起發生而測不出來（L16）。
    from shared.assessment_axes import AXES as LEGACY_AXES

    assert set(LEGACY_AXIS_TO_SCORE) == set(LEGACY_AXES)
    targets = [v for v in LEGACY_AXIS_TO_SCORE.values() if v is not None]
    assert len(targets) == len(set(targets)), "一個新維度不得由兩個舊軸餵"
    assert set(targets) <= set(AXES)


def test_source_reliability_maps_to_nothing_on_purpose() -> None:
    """**`source_reliability` 不是第六個維度。**

    「你憑什麼相信前面那些答案」不是一個投資問題，它是套在所有維度上的上限。
    這條若被改成某個 score，等於讓一個與標的好壞無關的分量參與排序。
    """
    assert LEGACY_AXIS_TO_SCORE["source_reliability"] is None


def test_catalyst_has_no_legacy_source() -> None:
    """Q5 在舊系統沒有任何軸——它住在 `coverage_assessments.catalyst` 的自由文字裡。"""
    assert "catalyst" in UNMAPPED_SCORES
    assert "catalyst" not in set(LEGACY_AXIS_TO_SCORE.values())


def test_conversion_is_one_way_only() -> None:
    """沒有 `to_legacy()`，也不會有——那會製造兩份可寫的真相（L10）。"""
    assert not [n for n in dir(legacy_axes) if "to_legacy" in n]


# ---------------------------------------------------------------------------
# 轉換行為
# ---------------------------------------------------------------------------

def test_four_axes_convert_and_catalyst_stays_none() -> None:
    result = convert_axis_results(_legacy())
    for axis in ("structural", "value_capture", "earnings_exposure", "expectation_gap"):
        assert result.scores[axis] is not None, axis
    assert result.scores["catalyst"] is None
    assert "catalyst" in result.unmapped_scores
    assert any("Q5" in note for note in result.notes)


def test_unknown_level_stays_none_not_zero() -> None:
    """舊軸 `unknown` → 新 score `None`（不知道），**不是 0.0**（判斷它很弱）。"""
    result = convert_axis_results(
        _legacy(technical_causal_link=_axis("unknown"))
    )
    assert result.scores["structural"] is None
    assert any("不填 0" in note for note in result.notes)


def test_axis_without_evidence_produces_no_score() -> None:
    """算不出來就不出分數——沒有 evidence 的軸不得產生 score（INV-6）。"""
    result = convert_axis_results(
        _legacy(commercial_maturity=_axis("corroborated", refs=()))
    )
    assert result.scores["value_capture"] is None
    assert any("沒有 evidence_refs" in note for note in result.notes)


def test_earnings_exposure_is_marked_partial() -> None:
    """舊軸問「公司撐不撐得住」，新 Q3 問「對 EPS/FCF 多重要」——**不是同一件事**。

    缺 segment revenue share（Engine C 無此欄位），所以必須帶 partial 標記，
    不得假裝完整。
    """
    result = convert_axis_results(_legacy())
    score = result.scores["earnings_exposure"]
    assert score is not None
    assert "partial" in (score.downgrade_reason or "")
    assert "earnings_exposure" in result.partial_scores


def test_unknown_legacy_axis_is_reported_not_swallowed() -> None:
    """對應表過期時要**現形**，不是靜默忽略（INV-3）。"""
    result = convert_axis_results(_legacy(brand_new_axis=_axis("corroborated")))
    assert "brand_new_axis" in result.unmapped_axes
    assert any("轉換器可能過期" in note for note in result.notes)


# ---------------------------------------------------------------------------
# EvidenceQuality：上限，不是分量
# ---------------------------------------------------------------------------

def test_weak_source_reliability_caps_every_dimension() -> None:
    """舊語意：它是第五個被 `min()` 的分量。新語意：它是套在所有維度上的上限。"""
    result = convert_axis_results(
        _legacy(source_reliability=_axis("unknown"))
    )
    assert result.evidence_quality.ceiling == 0.0
    for axis in AXES:
        score = result.scores[axis]
        if score is None:
            continue
        assert score.effective == 0.0
        assert "evidence_quality_ceiling" in (score.downgrade_reason or "")


def test_ceiling_says_which_dimension_is_limited() -> None:
    """新語意多回答一個問題：**是哪個投資維度被證據拖住了。**

    舊語意只會說「證據不夠」，不會說「所以什麼看不清」。
    """
    result = convert_axis_results(_legacy(source_reliability=_axis("bounded_hypothesis")))
    capped = [a for a in AXES
              if result.scores[a] is not None
              and "evidence_quality_ceiling" in (result.scores[a].downgrade_reason or "")]
    # commercial_maturity 宣告 corroborated(0.85) 但上限只有 0.5 → 被壓
    assert "value_capture" in capped


def test_independent_origins_follow_l8_thresholds() -> None:
    """L8：多文件入圖前至少 3 個不同 `origin_entity`；供應商自報不算獨立佐證。"""
    three = assess_evidence_quality([
        evidence("a", origin_entity="co:coherent"),
        evidence("b", origin_entity="co:nvidia"),
        evidence("c", origin_entity="reuters"),
    ])
    assert three.level == "corroborated" and three.independent_origins == 3

    one = assess_evidence_quality([
        evidence("a", origin_entity="co:coherent"),
        evidence("b", origin_entity="co:coherent"),   # 同一來源不累加
    ])
    assert one.level == "unknown" and one.independent_origins == 1
    assert "自報" in one.reason


def test_refs_without_origin_are_counted_but_do_not_vouch() -> None:
    """沒有 `origin_entity` 的引用不計入獨立性，**也不因此被丟掉**（L11-5 的形狀）。"""
    quality = assess_evidence_quality([
        evidence("a", origin_entity=None),
        evidence("b", origin_entity=None),
    ])
    assert quality.independent_origins == 0
    assert quality.total_refs == 2          # 仍在帳上


def test_legacy_level_is_reused_not_recomputed() -> None:
    """轉換歷史 payload 時沿用當時的判斷，**不用今天的圖去改寫它**。"""
    quality = from_legacy_level("corroborated", "同一事件 3 個 origin_event")
    assert quality.independent_origins == -1     # -1 ＝ 未重算
    assert "沿用舊" in quality.reason


def test_downgrade_reason_must_match_the_numbers() -> None:
    """契約層強制：**宣稱被證據上限壓過，數值就必須真的被壓過。**

    ⚠ 這條取代了舊的「全域 ceiling 檢查」。舊版拿 context-wide 的證據品質去檢查
    **每一個**軸，結果是**一個弱軸把好軸一起拖下水**——實測：引用外部印證邊的
    `value_capture` 被行情快照的 origin 拉到 0（2026-09-03）。

    上限是**逐軸**的（`quality.apply()` 在 `structural_score` 與 `compose_signal`
    各自呼叫），生效證據留在 `Score.downgrade_reason`。契約層能檢查的、也該檢查的，
    是**理由與數值一致**（L12：因果不得被截斷），不是拿一個全域值當閘門。

    逐軸上限本身由 `test_weak_source_reliability_caps_every_dimension` 與
    `test_ceiling_is_applied_per_axis_not_globally` 守著。
    """
    from alpha.contracts import Score
    from tests.test_alpha_contracts import build_signal

    # 宣稱被上限壓過，但 effective == declared → 矛盾，必須拒收
    with pytest.raises(ContractViolation, match="降級理由與數值不一致"):
        build_signal(structural_score=Score(
            0.5, 0.5, "ct_structural",
            downgrade_reason="evidence_quality_ceiling"))


def test_context_wide_quality_is_informational_not_a_gate() -> None:
    """`AlphaSignal.evidence_quality` 是**整體摘要**，不是任何軸的閘門。

    把它當閘門就是同一個表示承載兩種語意（L12）——而且會產生上面那個
    「弱軸拖累好軸」的實測後果。
    """
    from tests.test_alpha_contracts import build_signal

    signal = build_signal(evidence_quality=EvidenceQuality(
        level="unknown", independent_origins=0, best_tier=None,
        total_refs=0, reason="沒有可辨識的獨立來源"))
    # ceiling 是 0，但各軸分數（0.94 等）**不受影響**——因為它們有自己的證據
    assert signal.evidence_quality.ceiling == 0.0
    assert signal.structural_score.effective == 0.94


# ---------------------------------------------------------------------------
# 舊語意的重算（dual-run 對照用）
# ---------------------------------------------------------------------------

def test_legacy_weakest_reproduces_min_over_axes() -> None:
    assert legacy_weakest(_legacy(source_reliability=_axis("unknown"))) == "source_reliability"
    assert legacy_weakest(_legacy()) == "financial_resilience" or legacy_weakest(
        _legacy()) in {"technical_causal_link", "financial_resilience", "valuation_payoff"}
