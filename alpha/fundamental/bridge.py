"""確定性財務橋：基期觀測 ＋ 明示假設 → 營收 → 營益率 → 營業利益 → 稅前 → 淨利 → EPS。

## 每一步的三個要求

- **explicit**：每格是 `BridgeStep`，帶 `kind`（observation／assumption／derived）與公式。
- **traceable**：每個 derived 值列出它用到的 `assumption_ids` 與 `observation_refs`。
- **deterministic given inputs**：同一組輸入永遠算出同一個數；沒有隨機、沒有預設值。

## 缺席不補零

少一條假設（例如某個分部沒有成長假設、沒有稅率）就是該步 `missing`，並向下游傳播；
**不得**用 0 成長、0% 利潤率、0 稅率補上（Missing != Zero）。要「沿用上一年」也必須是
一條寫下來的假設（`basis=heuristic_proxy`）。

## 口徑

基期若有 `non_gaap` 區塊就走 non-GAAP（分析師 EPS 共識是這個口徑），否則走 GAAP；
輸出的每個數字都帶 `accounting_basis`，比較端據此判可不可比。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..errors import ContractViolation
from .contracts import (
    BRIDGE_VERSION, TOTAL_SCOPE, BridgeStep, FiscalPeriod, FiscalYearActuals, ModeledMetric,
    OperatingAssumption, weakest_basis,
)

#: 分部基期合計與公司營收的容忍差（四捨五入）。超過就在步驟上標 warning，不靜默。
_SEGMENT_SUM_TOLERANCE = 0.005

#: 這幾個 driver 的值本身有 GAAP／non-GAAP 之分（稅、利息、NCI、營益率變化）；假設若自帶口徑，
#: 必須與橋口徑一致，否則不得套用——non-GAAP 的 254M 所得稅套到 GAAP 基期是混算，不是估計。
#: 營收成長與稀釋股數沒有口徑之分，不在此列。
_BASIS_BEARING_DRIVERS: frozenset[str] = frozenset(
    {"operating_margin_delta", "interest_and_other_net", "tax_rate", "nci_attribution"})


@dataclass(frozen=True, slots=True)
class BridgeResult:
    accounting_basis: str
    steps: tuple[BridgeStep, ...]
    metrics: Mapping[str, ModeledMetric]
    warnings: tuple[str, ...]
    version: str = BRIDGE_VERSION


def _by_key(assumptions: Sequence[OperatingAssumption]) -> dict[tuple[str, str], OperatingAssumption]:
    out: dict[tuple[str, str], OperatingAssumption] = {}
    for item in assumptions:
        if item.key in out:
            raise ContractViolation(
                f"同一個 driver／scope 有兩條生效假設：{item.key}——選取層應已 supersede，這是 bug")
        out[item.key] = item
    return out


def _missing_step(key: str, label: str, unit: str, reason: str, *, kind: str = "derived") -> BridgeStep:
    return BridgeStep(key=key, label=label, kind=kind, value=None, unit=unit, basis="none",
                      reason=reason)


def _assumption_step(key: str, label: str, item: OperatingAssumption) -> BridgeStep:
    return BridgeStep(key=key, label=label, kind="assumption", value=item.value, unit=item.unit,
                      basis=item.basis, assumption_ids=(item.assumption_id,),
                      observation_refs=tuple(item.evidence_refs), scope=item.scope,
                      reason=item.rationale[:200])


def build_bridge(
    actuals: FiscalYearActuals,
    assumptions: Sequence[OperatingAssumption],
    target: FiscalPeriod,
) -> BridgeResult:
    """把基期觀測與假設算成目標期間的內部估計。"""
    steps: list[BridgeStep] = []
    warnings: list[str] = []
    base_refs = actuals.refs

    basis = "non_gaap" if (actuals.non_gaap and actuals.non_gaap.get("operating_income") is not None) else "gaap"
    block = actuals.block(basis) or {}

    # 假設自帶的 accounting_basis 必須與橋口徑一致（或 not_applicable）。不符的不是「缺假設」，
    # 是「有假設但口徑不同」——理由要說清楚，且絕不靜默套用（Phase 2 驗收 2026-09-06 補）。
    basis_mismatch: dict[tuple[str, str], OperatingAssumption] = {}
    compatible: list[OperatingAssumption] = []
    for item in assumptions:
        if item.driver in _BASIS_BEARING_DRIVERS and item.accounting_basis not in (basis, "not_applicable"):
            basis_mismatch[item.key] = item
            warnings.append(
                f"假設 {item.assumption_id}（{item.driver}[{item.scope}]）口徑 {item.accounting_basis} "
                f"與橋口徑 {basis} 不符，未套用——口徑不同不得混算")
        else:
            compatible.append(item)
    by_key = _by_key(compatible)

    def _absent(driver: str, default: str) -> str:
        hit = [a for k, a in basis_mismatch.items() if k[0] == driver]
        if hit:
            return (f"{driver} 假設口徑 {hit[0].accounting_basis} 與橋口徑 {basis} 不符，未套用"
                    "（不是缺假設，是口徑不同）")
        return default

    def _metric(name: str, value: float | None, unit: str, formula: str | None,
                assumption_ids: Sequence[str], reason: str | None = None,
                accounting_basis: str = basis) -> ModeledMetric:
        used = [by_key_id[a] for a in assumption_ids if a in by_key_id]
        dependency = weakest_basis([a.basis for a in used]) if value is not None else None
        if value is not None and dependency is None:
            dependency = "observation"
        return ModeledMetric(
            metric=name, period=target, value=value, unit=unit,
            accounting_basis=accounting_basis, input_dependency=dependency, formula=formula,
            assumption_ids=tuple(assumption_ids), observation_refs=base_refs, reason=reason,
        )

    by_key_id = {a.assumption_id: a for a in assumptions}
    metrics: dict[str, ModeledMetric] = {}

    # ---- 1. 營收 -----------------------------------------------------------
    total_growth = by_key.get(("revenue_growth", TOTAL_SCOPE))
    segment_growth = {k[1]: v for k, v in by_key.items()
                      if k[0] == "revenue_growth" and k[1] != TOTAL_SCOPE}
    if total_growth is not None and segment_growth:
        raise ContractViolation(
            "revenue_growth 同時有 total 與分部 scope——兩者不得並存，請撤回其中一組")

    steps.append(BridgeStep(key="base_revenue", label=f"基期營收（{actuals.period.label}）",
                            kind="observation", value=actuals.revenue, unit="currency",
                            basis="observation", observation_refs=base_refs))
    revenue: float | None = None
    revenue_ids: list[str] = []
    revenue_reason: str | None = None
    if total_growth is not None:
        steps.append(_assumption_step("revenue_growth:total", "營收成長假設（total）", total_growth))
        revenue = actuals.revenue * (1.0 + total_growth.value)
        revenue_ids = [total_growth.assumption_id]
        revenue_formula = "base_revenue × (1 + revenue_growth[total])"
    elif actuals.segment_revenue:
        segment_total = sum(actuals.segment_revenue.values())
        if actuals.revenue and abs(segment_total / actuals.revenue - 1.0) > _SEGMENT_SUM_TOLERANCE:
            warnings.append(
                f"分部基期合計 {segment_total:,.0f} 與公司營收 {actuals.revenue:,.0f} 差超過 "
                f"{_SEGMENT_SUM_TOLERANCE:.1%}——分部表可能不含某個 division")
        missing_segments: list[str] = []
        running = 0.0
        for name, base in actuals.segment_revenue.items():
            steps.append(BridgeStep(key=f"base_segment_revenue:{name}", label=f"基期分部營收：{name}",
                                    kind="observation", value=base, unit="currency",
                                    basis="observation", observation_refs=base_refs, scope=name))
            item = segment_growth.get(name)
            if item is None:
                missing_segments.append(name)
                steps.append(_missing_step(
                    f"segment_growth_contribution:{name}", f"分部成長貢獻：{name}", "currency",
                    f"缺 revenue_growth[{name}] 假設——沒有假設不等於零成長", kind="assumption"))
                continue
            steps.append(_assumption_step(f"revenue_growth:{name}", f"營收成長假設：{name}", item))
            contribution = base * item.value
            steps.append(BridgeStep(
                key=f"segment_growth_contribution:{name}", label=f"分部成長貢獻：{name}",
                kind="derived", value=contribution, unit="currency", basis="deterministic",
                formula=f"base_segment_revenue[{name}] × revenue_growth[{name}]",
                assumption_ids=(item.assumption_id,), observation_refs=base_refs, scope=name))
            running += base + contribution
            revenue_ids.append(item.assumption_id)
        if missing_segments:
            revenue_reason = f"分部 {missing_segments} 沒有成長假設；營收無法組成（缺席不是 0）"
        else:
            revenue = running
        revenue_formula = "Σ base_segment_revenue[s] × (1 + revenue_growth[s])"
    else:
        revenue_reason = "沒有 revenue_growth 假設（total 或分部）——沒有假設不等於零成長"
        revenue_formula = None
    if revenue is not None:
        steps.append(BridgeStep(key="internal_revenue", label=f"內部營收（{target.label}）",
                                kind="derived", value=revenue, unit="currency",
                                basis="deterministic", formula=revenue_formula,
                                assumption_ids=tuple(revenue_ids), observation_refs=base_refs))
    else:
        steps.append(_missing_step("internal_revenue", f"內部營收（{target.label}）", "currency",
                                   revenue_reason or "未知"))
    metrics["revenue"] = _metric("revenue", revenue, "currency", revenue_formula, revenue_ids,
                                 reason=revenue_reason, accounting_basis="not_applicable")

    # ---- 2. 營益率 ---------------------------------------------------------
    base_oi = block.get("operating_income")
    base_om = (base_oi / actuals.revenue) if base_oi is not None else None
    if base_om is not None:
        steps.append(BridgeStep(key="base_operating_margin", label=f"基期營益率（{basis}）",
                                kind="observation", value=base_om, unit="ratio",
                                basis="observation", observation_refs=base_refs,
                                formula=f"{basis}.operating_income / revenue"))
    else:
        steps.append(_missing_step("base_operating_margin", f"基期營益率（{basis}）", "ratio",
                                   f"基期觀測缺 {basis}.operating_income", kind="observation"))
    deltas = [v for k, v in by_key.items() if k[0] == "operating_margin_delta"]
    for item in deltas:
        steps.append(_assumption_step(f"operating_margin_delta:{item.scope}",
                                      f"營益率變化假設：{item.scope}", item))
    margin: float | None = None
    margin_ids = [d.assumption_id for d in deltas]
    margin_reason: str | None = None
    if base_om is None:
        margin_reason = f"基期觀測缺 {basis}.operating_income，算不出基期營益率"
    elif not deltas:
        margin_reason = _absent(
            "operating_margin_delta",
            "沒有 operating_margin_delta 假設——沿用基期也必須是一條寫下來的假設（值可為 0）")
    else:
        margin = base_om + sum(d.value for d in deltas)
    margin_formula = "base_operating_margin + Σ operating_margin_delta[scope]"
    if margin is not None:
        steps.append(BridgeStep(key="internal_operating_margin", label=f"內部營益率（{basis}）",
                                kind="derived", value=margin, unit="ratio", basis="deterministic",
                                formula=margin_formula, assumption_ids=tuple(margin_ids),
                                observation_refs=base_refs))
    else:
        steps.append(_missing_step("internal_operating_margin", f"內部營益率（{basis}）", "ratio",
                                   margin_reason or "未知"))
    metrics["operating_margin"] = _metric("operating_margin", margin, "ratio", margin_formula,
                                          margin_ids, reason=margin_reason)

    # ---- 3. 營業利益 -------------------------------------------------------
    oi = revenue * margin if (revenue is not None and margin is not None) else None
    oi_ids = revenue_ids + margin_ids
    oi_reason = None if oi is not None else "缺內部營收或內部營益率"
    _emit(steps, "internal_operating_income", f"內部營業利益（{basis}）", oi, "currency",
          "internal_revenue × internal_operating_margin", oi_ids, base_refs, oi_reason)
    metrics["operating_income"] = _metric("operating_income", oi, "currency",
                                          "internal_revenue × internal_operating_margin", oi_ids,
                                          reason=oi_reason)

    # ---- 4. 利息與其他 → 稅前 ---------------------------------------------
    interest = by_key.get(("interest_and_other_net", TOTAL_SCOPE))
    if interest is not None:
        steps.append(_assumption_step("interest_and_other_net", "利息與其他費用淨額假設", interest))
    pretax = (oi - interest.value) if (oi is not None and interest is not None) else None
    pretax_ids = oi_ids + ([interest.assumption_id] if interest else [])
    pretax_reason = (None if pretax is not None else
                     (_absent("interest_and_other_net", "缺 interest_and_other_net 假設")
                      if interest is None else oi_reason))
    _emit(steps, "internal_pretax_income", f"內部稅前利益（{basis}）", pretax, "currency",
          "internal_operating_income − interest_and_other_net", pretax_ids, base_refs, pretax_reason)

    # ---- 5. 稅 → 淨利 ------------------------------------------------------
    tax_rate = by_key.get(("tax_rate", TOTAL_SCOPE))
    if tax_rate is not None:
        steps.append(_assumption_step("tax_rate", "有效稅率假設", tax_rate))
    tax = (pretax * tax_rate.value) if (pretax is not None and tax_rate is not None) else None
    tax_ids = pretax_ids + ([tax_rate.assumption_id] if tax_rate else [])
    tax_reason = (None if tax is not None else
                  (_absent("tax_rate", "缺 tax_rate 假設") if tax_rate is None else pretax_reason))
    _emit(steps, "internal_income_taxes", f"內部所得稅（{basis}）", tax, "currency",
          "internal_pretax_income × tax_rate", tax_ids, base_refs, tax_reason)
    net_income = (pretax - tax) if (pretax is not None and tax is not None) else None
    _emit(steps, "internal_net_income", f"內部淨利（{basis}，歸屬前）", net_income, "currency",
          "internal_pretax_income − internal_income_taxes", tax_ids, base_refs, tax_reason)

    # ---- 6. 非控制權益 → 歸屬母公司 ---------------------------------------
    nci = by_key.get(("nci_attribution", TOTAL_SCOPE))
    if nci is not None:
        steps.append(_assumption_step("nci_attribution", "非控制權益調整假設", nci))
    attributable = (net_income + nci.value) if (net_income is not None and nci is not None) else None
    attributable_ids = tax_ids + ([nci.assumption_id] if nci else [])
    attributable_reason = (None if attributable is not None else
                           (_absent("nci_attribution", "缺 nci_attribution 假設")
                            if nci is None else tax_reason))
    _emit(steps, "internal_net_income_attributable", f"內部歸屬母公司淨利（{basis}）", attributable,
          "currency", "internal_net_income + nci_attribution", attributable_ids, base_refs,
          attributable_reason)
    metrics["net_income"] = _metric("net_income", attributable, "currency",
                                    "internal_net_income + nci_attribution", attributable_ids,
                                    reason=attributable_reason)

    # ---- 7. 稀釋股數 → EPS -------------------------------------------------
    shares = by_key.get(("diluted_shares", TOTAL_SCOPE))
    if shares is not None:
        steps.append(_assumption_step("diluted_shares", "稀釋股數假設", shares))
    eps: float | None = None
    eps_reason: str | None = None
    if attributable is None:
        eps_reason = attributable_reason
    elif shares is None:
        eps_reason = "缺 diluted_shares 假設"
    elif shares.value <= 0:
        eps_reason = "diluted_shares 假設非正"
    else:
        eps = attributable / shares.value
    eps_ids = attributable_ids + ([shares.assumption_id] if shares else [])
    _emit(steps, "internal_eps", f"內部稀釋 EPS（{basis}）", eps, "currency_per_share",
          "internal_net_income_attributable / diluted_shares", eps_ids, base_refs, eps_reason)
    metrics["eps"] = _metric("eps", eps, "currency_per_share",
                             "internal_net_income_attributable / diluted_shares", eps_ids,
                             reason=eps_reason)

    return BridgeResult(accounting_basis=basis, steps=tuple(steps), metrics=metrics,
                        warnings=tuple(warnings))


def _emit(steps: list[BridgeStep], key: str, label: str, value: float | None, unit: str,
          formula: str, assumption_ids: Sequence[str], refs: tuple[str, ...],
          reason: str | None) -> None:
    if value is None:
        steps.append(_missing_step(key, label, unit, reason or "上游缺料"))
        return
    steps.append(BridgeStep(key=key, label=label, kind="derived", value=value, unit=unit,
                            basis="deterministic", formula=formula,
                            assumption_ids=tuple(assumption_ids), observation_refs=refs))


__all__ = ["BRIDGE_VERSION", "BridgeResult", "build_bridge"]
