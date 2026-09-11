"""隱含報酬的兩個桿：EPS 差異 × 倍數差異（2026-09-09 使用者定案；ROADMAP「研究閉環」P2）。

```
1 + price_return = fair_value / price
                 = (internal_eps × target_multiple) / price
                 = (internal_eps / consensus_eps) × (target_multiple / (price / consensus_eps))
                   └── eps_ratio ──┘   └───────── multiple_ratio ─────────┘
eps_contribution      = eps_ratio − 1        （我們的 EPS 比共識高／低多少）
multiple_contribution = multiple_ratio − 1   （我們的倍數比「市場對共識付的倍數」高／低多少）
interaction           = eps_contribution × multiple_contribution
恆等式：eps_contribution + multiple_contribution + interaction = price_return
```

## 為什麼要拆

2026-09-08 實測：僅有的兩檔 ready 標的隱含報酬 −20.7%／−36.3%，其中倍數折價貢獻約 −16%／−20%——
來源是「較市場折價約 17%」這個習慣，不是任何證據。兩個桿都往保守壓，任何公司都會是負的；
30 檔全負時仍分不出「方法偏空」與「市場太貴」。拆開之後：
- **EPS 差異**才是圖應該產生的東西（結構 edge → 營運假設 → 內部 EPS 與共識的差）。
- **倍數差異**依 `AGENTS.md`「隱含報酬的兩個桿」：沒有 re-rating 證據時預設等於校準倍數；任何折價／溢價
  必須指得出證據。本模組**不判斷證據夠不夠**（那是 rationale 的事），只把差距算出來、放到眼前。

## 這一層不做的事

- 不重算 fair value、不重算 price_return——只把估值層與比較層已有的數字做一次確定性恆等分解。
- 不補共識：沒有同期同口徑的 EPS 共識就是 `missing`（`absence_kind` 說是哪一種），**頭條的報酬不受影響**
  ——拆解缺席不會讓報酬缺席。
- 不排序、不比較標的。
"""
from __future__ import annotations

from typing import Any

from ..fundamental.contracts import ExpectationComparison
from ..valuation.contracts import CurrentPrice, ValuationResult
from .contracts import ATTRIBUTION_FORMULA, MULTIPLE_NEUTRAL_TOLERANCE, ReturnAttribution

#: 倍數差距小於此門檻視為「與市場倍數一致」。**唯一定義在 `contracts.py`**——
#: 2026-09-11 之前這裡是 0.02、品質計數器是 0.005，同一個問題兩個答案（見該處註解）。
_MULTIPLE_TOLERANCE = MULTIPLE_NEUTRAL_TOLERANCE
#: 倍數差距超過此門檻時，模型層另發一條 warning 提醒原則（只提醒，不阻擋、不改數字）。
MULTIPLE_WARNING_THRESHOLD = 0.05

#: `ExpectationComparison.status` → 缺席語意（`alpha/absence.py` 封閉字彙）。查表，不推論。
_COMPARISON_ABSENCE: dict[str, str] = {
    "consensus_missing": "provider_missing",
    "internal_missing": "upstream_unavailable",
    "incompatible_period": "inputs_incompatible",
    "incompatible_basis": "inputs_incompatible",
    "incompatible_unit": "inputs_incompatible",
    "unreconciled_base": "inputs_incompatible",
}


def _missing(reason: str, kind: str, *, comparison: ExpectationComparison | None = None) -> ReturnAttribution:
    return ReturnAttribution(
        status="missing", reason=reason, absence_kind=kind,
        consensus_eps=comparison.consensus if comparison is not None else None,
        internal_eps=comparison.internal if comparison is not None else None,
        analyst_count=comparison.analyst_count if comparison is not None else None,
        consensus_captured_at=comparison.consensus_captured_at if comparison is not None else None,
        consensus_refs=tuple(comparison.consensus_refs) if comparison is not None else (),
    )


def multiple_principle_note(multiple_contribution: float, *, target_multiple: float, market_multiple: float) -> str:
    """把倍數差距翻成一句面向使用者的話。**只陳述差距與原則，不判斷證據**。"""
    if abs(multiple_contribution) < _MULTIPLE_TOLERANCE:
        return (f"目標倍數 {target_multiple:.1f}x 與市場對共識付的 {market_multiple:.1f}x 一致（差 <{_MULTIPLE_TOLERANCE:.1%}）"
                "——倍數桿沒有貢獻，隱含報酬幾乎全來自 EPS 差異")
    direction = "折價" if multiple_contribution < 0 else "溢價"
    return (f"目標倍數 {target_multiple:.1f}x 較市場對共識付的 {market_multiple:.1f}x {direction} "
            f"{abs(multiple_contribution):.1%}——依 2026-09-09 原則，{direction}必須在估值假設的 rationale 指得出 "
            "re-rating 證據；說不出證據的保守選擇是偏差，不是審慎")


def noise_floor_note(
    *, fx_delta: float | None, eps_contribution: float, multiple_contribution: float
) -> str | None:
    """兩個桿有沒有小到落在換算殘差以下？有就明講——**不改數字，只擋住誤讀**。

    事發（2026-09-11 TSM）：3% 換算容差讓 TSM 的兩欄第一次算得出來，殘差 +2.11%，
    而算出來的倍數桿是 **+1.71%**——比殘差還小。畫面上它會被歸進「目標倍數＝校準倍數」，
    讀起來像一個發現，實際上在雜訊裡。**放寬識別的同時必須把雜訊下限一起印出來**，
    否則這條容差就是拿精度換覆蓋率而不說。
    """
    if fx_delta is None:
        return None
    floor = abs(fx_delta)
    inside = [name for name, value in (("EPS 桿", eps_contribution), ("倍數桿", multiple_contribution))
              if abs(value) < floor]
    if not inside:
        return None
    return (f"⚠ 共識 EPS 帶著 {fx_delta:+.1%} 的換算殘差，而{'、'.join(inside)}比它還小"
            "——這（些）桿落在雜訊裡，**不要當成發現**。要拿到有意義的數字得用同一條 FX 路徑"
            "重算共識，不是調容差。")


def attribute_price_return(
    *,
    valuation: ValuationResult,
    price: CurrentPrice,
    comparison: ExpectationComparison | None,
    price_return: float,
) -> ReturnAttribution:
    """把已算好的 price_return 拆成 EPS 差異 × 倍數差異。任何一段缺料都以 `missing`＋語意現形，不補 0。"""
    if comparison is None:
        return _missing("fundamental model 未提供 EPS 的內部 vs 共識比較——沒有共識就拆不出「倍數 vs 市場」",
                        "upstream_unavailable")
    if comparison.metric != "eps":
        return _missing(f"拆解只接受 EPS 比較，收到 {comparison.metric!r}", "inputs_incompatible", comparison=comparison)
    if comparison.status != "comparable":
        kind = _COMPARISON_ABSENCE.get(comparison.status, "upstream_unavailable")
        return _missing(f"內部 vs 共識 EPS 不可比（{comparison.status}）：{comparison.reason or '未附理由'}",
                        kind, comparison=comparison)
    assert comparison.internal is not None and comparison.consensus is not None  # comparable 契約保證
    if valuation.method != "forward_earnings_multiple" or not valuation.assumptions:
        return _missing("拆解只對 forward earnings multiple 有定義（v1 唯一方法），且需要生效的目標倍數",
                        "upstream_unavailable", comparison=comparison)
    fundamental = valuation.fundamental_input
    if fundamental is None or fundamental.value is None:
        return _missing("估值層沒有內部 EPS 輸入", "upstream_unavailable", comparison=comparison)
    scale = max(abs(fundamental.value), abs(comparison.internal), 1e-9)
    if abs(fundamental.value - comparison.internal) > 1e-6 * scale:
        return _missing(
            f"比較層的內部 EPS {comparison.internal:g} 與估值層的內部 EPS {fundamental.value:g} 不是同一個數——"
            "兩者必須同源，否則恆等式不成立", "inputs_incompatible", comparison=comparison)
    if comparison.consensus <= 0:
        return _missing(f"共識 EPS {comparison.consensus:g} 非正——市場對共識付的倍數無定義（與本益比法不適用同一條件）",
                        "method_not_applicable", comparison=comparison)
    if not price.is_known or not price.value or price.value <= 0:
        return _missing("現價缺席或非正，市場倍數無定義", "upstream_unavailable", comparison=comparison)

    target_multiple = float(valuation.assumptions[0].value)
    market_multiple = price.value / comparison.consensus
    eps_ratio = comparison.internal / comparison.consensus
    multiple_ratio = target_multiple / market_multiple
    eps_contribution = eps_ratio - 1.0
    multiple_contribution = multiple_ratio - 1.0
    interaction = eps_contribution * multiple_contribution
    # 恆等式自我核對：eps_c + mult_c + interaction == fair_value/price − 1（浮點容忍 1e-9）。
    # 不成立代表輸入不是同一組數（例如估值層與比較層的內部 EPS 分家），寧可 missing 也不印。
    if abs((eps_contribution + multiple_contribution + interaction) - price_return) > 1e-9 * max(1.0, abs(price_return)):
        return _missing(
            f"恆等式不成立：eps {eps_contribution:+.4f} + multiple {multiple_contribution:+.4f} + interaction "
            f"{interaction:+.4f} ≠ price_return {price_return:+.4f}——輸入不同源，拒印", "inputs_incompatible",
            comparison=comparison)
    fx_delta = comparison.fx_translation_delta
    return ReturnAttribution(
        status="available", reason=None, absence_kind=None,
        fx_translation_delta=fx_delta,
        noise_floor_note=noise_floor_note(
            fx_delta=fx_delta, eps_contribution=eps_contribution,
            multiple_contribution=multiple_contribution),
        consensus_eps=comparison.consensus, internal_eps=comparison.internal,
        target_multiple=target_multiple, market_multiple_on_consensus=market_multiple,
        eps_ratio=eps_ratio, multiple_ratio=multiple_ratio,
        eps_contribution=eps_contribution, multiple_contribution=multiple_contribution, interaction=interaction,
        price_return=price_return,
        analyst_count=comparison.analyst_count, consensus_captured_at=comparison.consensus_captured_at,
        consensus_refs=tuple(comparison.consensus_refs),
        formula=ATTRIBUTION_FORMULA,
        principle_note=multiple_principle_note(multiple_contribution, target_multiple=target_multiple,
                                               market_multiple=market_multiple),
    )


def attribution_payload(attribution: ReturnAttribution) -> dict[str, Any]:
    """機器可讀的整包（給 read model 的 `attribution` Datum 與 epistemics 用；純選取，不算）。"""
    return {
        "status": attribution.status,
        "internal_eps": attribution.internal_eps,
        "consensus_eps": attribution.consensus_eps,
        "analyst_count": attribution.analyst_count,
        "consensus_captured_at": (attribution.consensus_captured_at.isoformat()
                                  if attribution.consensus_captured_at else None),
        "target_multiple": attribution.target_multiple,
        "market_multiple_on_consensus": attribution.market_multiple_on_consensus,
        "eps_ratio": attribution.eps_ratio,
        "multiple_ratio": attribution.multiple_ratio,
        "eps_contribution": attribution.eps_contribution,
        "multiple_contribution": attribution.multiple_contribution,
        "interaction": attribution.interaction,
        "price_return": attribution.price_return,
        "principle_note": attribution.principle_note,
        "fx_translation_delta": attribution.fx_translation_delta,
        "noise_floor_note": attribution.noise_floor_note,
        "formula": attribution.formula,
        "reason": attribution.reason,
        "absence_kind": attribution.absence_kind,
    }


__all__ = ["MULTIPLE_WARNING_THRESHOLD", "attribute_price_return", "attribution_payload", "multiple_principle_note", "noise_floor_note"]
