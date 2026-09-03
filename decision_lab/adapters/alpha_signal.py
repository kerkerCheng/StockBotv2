"""`AlphaSignal` → Engine D 的 **coverage assessment payload**。

## 這是唯一一條 Alpha Research 進入 Engine D 的路

⚠ **Engine D 不 import `alpha/`**（`tests/test_layer_separation.py` 守著）。
本 adapter 吃的是**已經序列化好的 payload**（`dict`），不是 `AlphaSignal` 物件——
所以 Engine D 依然不知道 `alpha/` 存在，只知道「有人給了我一份研究結論」。

呼叫端（composition root 或 CLI）負責把 `AlphaSignal` 序列化後傳進來。

## 這不是 `legacy_axes.to_legacy()`

`alpha/legacy_axes.py` 明文寫著「沒有 `to_legacy()`，也不會有」——那指的是
**不得把新分數寫回歷史 payload**（268 筆 append-only 紀錄，L10）。

本 adapter 做的是**另一件事**：用 store 既有的 schema 寫**一筆新的** decision。
schema 不動、歷史不改、只往前追加。兩者的差別是「改寫過去」與「用舊格式記錄現在」。

## ⚠ 這是**有損**的轉換，而且損失必須現形

新五 score 與舊五軸不是同一組東西（`target-architecture.md` §5.0）。往回塞時：

| 新 | 舊 | 損失 |
|---|---|---|
| `structural` | `technical_causal_link` | — |
| `value_capture` | `commercial_maturity` | — |
| `earnings_exposure` | `financial_resilience` | 語意不同（見下） |
| `expectation_gap` | `valuation_payoff` | — |
| `evidence_quality`（上限） | `source_reliability` | 由「上限」壓回「分量」 |
| **`catalyst`（Q5）** | **無** | 🔴 **完全沒有家** |

**Q5 沒有落點，所以它被寫進 `_alpha_signal` 的完整鏡像裡**——payload 保留
`research_context_digest` 與五個 score 的原值，讓「往回塞損失了什麼」隨時可重建。
**不得靜默丟掉。**

這個有損轉換是**過渡措施**：Decision Store schema v10 應該直接吃 `AlphaSignal`，
屆時本 adapter 就沒有存在必要（見 ROADMAP Phase 3 剩餘項）。
"""
from __future__ import annotations

from typing import Any, Mapping

#: 新 score → 舊軸。**與 `alpha/legacy_axes.py::LEGACY_AXIS_TO_SCORE` 互為反向**，
#: 兩邊必須一致——`tests/test_alpha_signal_adapter.py` 對此有斷言。
SCORE_TO_LEGACY_AXIS: Mapping[str, str] = {
    "structural": "technical_causal_link",
    "value_capture": "commercial_maturity",
    "earnings_exposure": "financial_resilience",
    "expectation_gap": "valuation_payoff",
}

#: 沒有舊軸可去的新 score。**不得靜默丟掉**——它們進 `_alpha_signal` 鏡像。
SCORES_WITHOUT_LEGACY_AXIS: frozenset[str] = frozenset({"catalyst"})

#: 舊軸的三階序數。分數 → 等級用**閾值**，且刻意與 `alpha/levels.py` 的
#: `_LEVEL_TO_SCORE`（0.5／0.85）對齊，讓來回轉換不會漂移。
_CORROBORATED_FLOOR = 0.85
_BOUNDED_FLOOR = 0.01

LEGACY_AXES: tuple[str, ...] = (
    "source_reliability", "technical_causal_link", "commercial_maturity",
    "financial_resilience", "valuation_payoff",
)


class AlphaSignalAdapterError(ValueError):
    """`AlphaSignal` payload 無法安全地轉成 assessment。"""


def _level_for(effective: float | None) -> str:
    """生效值 → 舊軸等級。

    ⚠ **用 `effective` 不是 `declared`**（F-25）：宣告 corroborated 但引用不成立的
    分數，往回塞時必須帶著已被壓下去的事實，否則 Engine D 會看到一個假的強證據。
    """
    if effective is None:
        return "unknown"
    if effective >= _CORROBORATED_FLOOR:
        return "corroborated"
    if effective >= _BOUNDED_FLOOR:
        return "bounded_hypothesis"
    return "unknown"


def _axis_payload(
    score: Mapping[str, Any] | None,
    trace: Mapping[str, Any] | None,
    *,
    fallback_reason: str,
) -> dict[str, Any]:
    if score is None:
        return {
            "level": "unknown",
            "evidence_refs": [],
            "reason": fallback_reason,
            "missing_data": ["alpha_score_unknown"],
        }
    refs = [str(r.get("ref")) for r in ((trace or {}).get("evidence_refs") or [])
            if isinstance(r, Mapping) and r.get("ref")]
    missing: list[str] = []
    if score.get("downgrade_reason"):
        missing.append(str(score["downgrade_reason"]))
    return {
        "level": _level_for(score.get("effective")),
        "evidence_refs": refs,
        "reason": str((trace or {}).get("note") or fallback_reason)[:800],
        "missing_data": missing,
    }


def coverage_assessment_from_signal(payload: Mapping[str, Any]) -> dict[str, Any]:
    """把序列化的 `AlphaSignal` 轉成五軸 assessment payload。

    回傳 `{"assessment": {...五軸...}, "_alpha_signal": {...完整鏡像...}}`。

    ⚠ **`_alpha_signal` 不是裝飾。** 它承載這次轉換丟掉的東西（Q5 catalyst、
    declared vs effective 的差、evidence quality 的上限語意），讓
    「往回塞損失了什麼」隨時可重建（INV-3：no silent drop）。
    """
    if not isinstance(payload, Mapping):
        raise AlphaSignalAdapterError("payload 必須是序列化後的 AlphaSignal（dict）")
    traces = payload.get("model_components") or {}
    if not isinstance(traces, Mapping):
        raise AlphaSignalAdapterError("model_components 必須是 mapping")

    assessment: dict[str, dict[str, Any]] = {}
    for score_name, legacy_axis in SCORE_TO_LEGACY_AXIS.items():
        score = payload.get(f"{score_name}_score")
        trace = traces.get((score or {}).get("trace_id")) if isinstance(score, Mapping) else None
        assessment[legacy_axis] = _axis_payload(
            score if isinstance(score, Mapping) else None,
            trace if isinstance(trace, Mapping) else None,
            fallback_reason=f"AlphaSignal 的 {score_name} 為 unknown（不知道，不是 0）",
        )

    # `source_reliability` 由 evidence quality 反推——它在新架構是**上限**不是分量，
    # 往回塞時只能表達成一個等級，這是有損的（見 module docstring）。
    quality = payload.get("evidence_quality")
    if isinstance(quality, Mapping) and quality.get("level"):
        assessment["source_reliability"] = {
            "level": str(quality["level"]),
            "evidence_refs": [str(r.get("ref")) for r in (payload.get("evidence_refs") or [])
                              if isinstance(r, Mapping) and r.get("ref")][:20],
            "reason": f"由 AlphaSignal 的 evidence quality 反推：{quality.get('reason', '')}"[:800],
            "missing_data": [],
        }
    else:
        assessment["source_reliability"] = {
            "level": "unknown", "evidence_refs": [],
            "reason": "AlphaSignal 未帶 evidence_quality——證據上限未知",
            "missing_data": ["evidence_quality_missing"],
        }

    if set(assessment) != set(LEGACY_AXES):
        raise AlphaSignalAdapterError(
            f"轉換後的五軸不完整：{sorted(set(LEGACY_AXES) - set(assessment))}"
        )

    dropped = {
        name: payload.get(f"{name}_score")
        for name in sorted(SCORES_WITHOUT_LEGACY_AXIS)
    }
    return {
        "assessment": assessment,
        # ⚠ 完整鏡像：轉換丟掉的東西必須留在 payload 裡，不得靜默消失。
        "_alpha_signal": {
            "research_context_digest": payload.get("research_context_digest"),
            "scores": {
                name: payload.get(f"{name}_score")
                for name in (*SCORE_TO_LEGACY_AXIS, *sorted(SCORES_WITHOUT_LEGACY_AXIS))
            },
            "scores_without_legacy_axis": dropped,
            "variant_view": payload.get("variant_view"),
            "disproof_conditions": payload.get("disproof_conditions"),
            "catalysts": payload.get("catalysts"),
            "metadata": payload.get("metadata"),
            "_lossy": (
                "五軸 schema 裝不下 Q5 catalyst，也無法表達 evidence quality 的"
                "『上限』語意（只能壓成一個分量）。本鏡像保留原值，"
                "讓『往回塞損失了什麼』隨時可重建。schema v10 之後本 adapter 可移除"
            ),
        },
    }
