"""舊五軸 → 新五 score 的**單向**轉換（讀歷史用，不回寫）。

## 為什麼是單向

Decision Store 是 append-only 的 private authority，268 筆歷史 decision 的
`sizing.axis_results` **永遠不改寫**（L10：拿不回來的資料只能 append）。
所以轉換只有一個方向：**讀舊 payload → 產生新 score**。
沒有 `to_legacy()`，也不會有——那會製造兩份可寫的真相。

## 對應關係是「輸入」不是「改名」

2026-09-03 用 COHR 真實資料實測後確認（使用者當日定案：**新五軸取代舊五軸，不並存**）：

| 舊軸（問「證據多強」） | 新 score（問投資問題） | 備註 |
|---|---|---|
| `technical_causal_link` | `structural`（Q1 結構稀缺） | 因果鏈強度就是結構位置的證據 |
| `commercial_maturity` | `value_capture`（Q2 價值攫取） | 客戶端商業承諾＝能不能收租 |
| `financial_resilience` | `earnings_exposure`（Q3 盈餘曝險） | ⚠ **只是部分**，見下 |
| `valuation_payoff` | `expectation_gap`（Q4 預期落差） | 舊軸的 reason 本來就在寫 variant perception |
| `source_reliability` | **無** | 它是 meta 軸 → `EvidenceQuality` 上限 |
| **無** | `catalyst`（Q5 催化劑） | 舊系統沒有這一軸 → 轉換後恆為 `None` |

## 兩個誠實的缺口（**不得用預設值填掉**）

1. **Q3 只轉得到一半。** 舊 `financial_resilience` 問的是「公司撐不撐得住」
   （runway／負債），新 Q3 問的是「這個結構優勢對 EPS／FCF 有多重要」——
   後者需要 **segment revenue share**，而 Engine C **沒有這個欄位**
   （`current-architecture.md` §8 缺口 #1）。所以轉換出來的 Q3 帶
   `downgrade_reason` 明說它是部分轉換，不是完整答案。
2. **Q5 沒有來源。** catalyst 住在 `coverage_assessments.catalyst` 的自由文字裡，
   `catalyst_watch.py` 明文「刻意不解析散文日期」。轉換後 `catalyst_score is None`
   ——**那是正確答案**，不是缺陷。填一個預設值會讓「沒有結構化催化劑」看起來像
   「催化劑很弱」，正是 `None ≠ 0` 要防的事。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import AXES, ComponentTrace, EvidenceRef, Score
from .errors import ContractViolation
from .evidence_quality import EvidenceQuality, from_legacy_level
from .levels import LEVEL_SCALE_VERSION, level_to_score

#: 舊軸 → 新 score。`None` 代表刻意沒有對應。
LEGACY_AXIS_TO_SCORE: Mapping[str, str | None] = {
    "technical_causal_link": "structural",
    "commercial_maturity": "value_capture",
    "financial_resilience": "earnings_exposure",
    "valuation_payoff": "expectation_gap",
    "source_reliability": None,          # meta 軸 → EvidenceQuality
}

#: 舊系統完全沒有來源的新維度。轉換後必為 `None`。
UNMAPPED_SCORES: frozenset[str] = frozenset({"catalyst"})

#: 只轉得到一半的維度，以及原因。
PARTIAL_SCORES: Mapping[str, str] = {
    "earnings_exposure": (
        "partial:legacy_financial_resilience_only"
        "（舊軸問公司撐不撐得住，新 Q3 問對 EPS/FCF 多重要；"
        "缺 segment revenue share，Engine C 無此欄位）"
    ),
}

CONVERTER_VERSION = f"legacy-axes-to-scores/{LEVEL_SCALE_VERSION}"


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """轉換結果 ＋ **被丟掉或降級的東西的完整帳**（INV-3：no silent drop）。"""

    scores: Mapping[str, Score | None]
    traces: Mapping[str, ComponentTrace]
    evidence_quality: EvidenceQuality
    unmapped_axes: tuple[str, ...]
    unmapped_scores: tuple[str, ...]
    partial_scores: tuple[str, ...]
    notes: tuple[str, ...]

    def as_signal_kwargs(self) -> dict[str, Any]:
        """展開成 `AlphaSignal(**kwargs)` 用的 score 欄位。"""
        return {f"{axis}_score": self.scores.get(axis) for axis in AXES}


def _classify(raw: str) -> str:
    """把舊的自由格式 evidence_ref 字串歸到一個 `EvidenceRef.kind`。

    ⚠ 舊 `evidence_refs` 是**異質**的：doc id、URI、entity id、edge key，
    以及整段帶逐字引文的散文（實測 3/10 屬最後一種）。這裡刻意寬鬆——
    分類錯誤只影響可讀性，而**丟掉引用會讓 score 失去 provenance**，那嚴重得多。
    """
    text = raw.strip()
    if text.startswith("edge:"):
        return "graph_edge"
    if text.startswith(("co:", "tech:", "mat:", "prod:", "std:", "person:")):
        return "graph_claim"
    if text.startswith("yfinance://"):
        return "market_series"
    if text.startswith("engine_c://"):
        return "engine_c_observation"
    if " " in text or "：" in text:      # 散文型引用
        return "external_document"
    return "source_doc"


def convert_axis_results(
    axis_results: Mapping[str, Mapping[str, Any]],
    *,
    rubric_version: str = "unknown",
) -> ConversionResult:
    """把一筆歷史 `sizing.axis_results` 轉成新的五個 score。

    **不猜、不填預設值。** 轉不出來的維度是 `None`，並列進 `unmapped_scores`。
    """
    scores: dict[str, Score | None] = {axis: None for axis in AXES}
    traces: dict[str, ComponentTrace] = {}
    unmapped_axes: list[str] = []
    notes: list[str] = []

    legacy_source = axis_results.get("source_reliability") or {}
    quality = from_legacy_level(
        str(legacy_source.get("effective_level")
            or legacy_source.get("level") or "unknown"),
        str(legacy_source.get("reason") or ""),
    )

    for axis_name, payload in axis_results.items():
        if axis_name not in LEGACY_AXIS_TO_SCORE:
            unmapped_axes.append(axis_name)
            notes.append(f"舊軸 {axis_name} 不在對應表中——轉換器可能過期")
            continue
        target = LEGACY_AXIS_TO_SCORE[axis_name]
        if target is None:
            notes.append(
                f"{axis_name} 是 meta 軸 → 轉成 EvidenceQuality（ceiling={quality.ceiling}）"
            )
            continue

        declared = level_to_score(str(payload.get("level") or "unknown"))
        stated_effective = level_to_score(
            str(payload.get("effective_level") or payload.get("level") or "unknown")
        )
        if declared is None or stated_effective is None:
            notes.append(f"{axis_name} → {target}：等級為 unknown，維持 None（不填 0）")
            continue

        refs = tuple(
            EvidenceRef(ref=str(raw), kind=_classify(str(raw)))
            for raw in (payload.get("evidence_refs") or [])
            if str(raw).strip()
        )
        if not refs:
            notes.append(
                f"{axis_name} → {target}：沒有 evidence_refs，"
                "依契約 score 不得存在（算不出來就不出分數）"
            )
            continue

        reasons: list[str] = []
        effective = min(stated_effective, declared)
        if effective < declared:
            reasons.append(
                ",".join(str(m) for m in (payload.get("missing_data") or []))
                or "legacy_effective_level_lower"
            )
        capped, ceiling_reason = quality.apply(effective)
        if ceiling_reason:
            reasons.append(ceiling_reason)
        effective = capped
        if target in PARTIAL_SCORES:
            reasons.append(PARTIAL_SCORES[target])

        trace_id = f"ct_{target}"
        traces[trace_id] = ComponentTrace(
            trace_id=trace_id,
            rule_version=f"{CONVERTER_VERSION}|rubric={rubric_version}",
            inputs={
                "legacy_axis": axis_name,
                "legacy_level": payload.get("level"),
                "legacy_effective_level": payload.get("effective_level"),
                "evidence_ceiling": quality.ceiling,
            },
            evidence_refs=refs,
            note=str(payload.get("reason") or "")[:400] or None,
        )
        scores[target] = Score(
            declared=declared,
            effective=effective,
            trace_id=trace_id,
            downgrade_reason="；".join(r for r in reasons if r) or None,
        )

    unmapped_scores = tuple(
        axis for axis in AXES if scores.get(axis) is None
    )
    for axis in sorted(UNMAPPED_SCORES & set(unmapped_scores)):
        notes.append(
            f"{axis}（Q5）：舊系統沒有這一軸——catalyst 住在 "
            "coverage_assessments.catalyst 的自由文字裡。維持 None 是正確答案，"
            "填預設值會讓「沒有結構化催化劑」看起來像「催化劑很弱」"
        )

    return ConversionResult(
        scores=scores,
        traces=traces,
        evidence_quality=quality,
        unmapped_axes=tuple(unmapped_axes),
        unmapped_scores=unmapped_scores,
        partial_scores=tuple(a for a in PARTIAL_SCORES if scores.get(a) is not None),
        notes=tuple(notes),
    )


def legacy_weakest(axis_results: Mapping[str, Mapping[str, Any]]) -> str | None:
    """重算舊語意的 `weakest_axis`（`min()` over 五軸）——供 dual-run 對照用。"""
    from .levels import level_rank

    ranked = [
        (level_rank(str(p.get("effective_level") or p.get("level") or "unknown")), name)
        for name, p in axis_results.items()
    ]
    if not ranked:
        return None
    return min(ranked)[1]
