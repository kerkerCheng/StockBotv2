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
    {"operating_margin_delta", "interest_and_other_net", "tax_rate", "tax_expense_absolute",
     "nci_attribution", "preferred_dividends", "diluted_eps_numerator_adjustment"})

#: 結果營益率的上限。**這是經濟不變量，不是參數**：營業利益不可能超過營收。
#: 2026-09-13 從 `operating_margin_delta` 的 per-record 界搬到這裡——per-record 的界管不到總和，
#: 而總和才是有意義的那個數（實測全庫 55 檔最高 0.7629，無一超過 1.0）。
_MAX_OPERATING_MARGIN = 1.0


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


def _select_basis(actuals: FiscalYearActuals, consensus_basis: str | None) -> tuple[str, str | None]:
    """橋要算哪一種口徑的內部 EPS。

    ## 為什麼不能只看「基期有沒有 non_gaap 區塊」

    舊規則是 `basis = non_gaap if 基期有 non_gaap.operating_income else gaap`，
    而它**只認得 COHR 那個案例**（共識是 non-GAAP，基期也填了 non-GAAP）。
    2026-09-12 撞到相反的一例：**CDNS 的 0y 共識是 GAAP**
    （`year_ago_actual` 4.06 ＝ 10-K 的 GAAP 稀釋 EPS，13 位分析師），
    若基期照實填 non_gaap 區塊，橋會算出 non-GAAP 的內部 EPS 再去對一串 GAAP 共識，
    得到約 **+70% 的假差距**——而 `verify_consensus_basis` 其實**已經知道**共識是 GAAP，
    只是那個結論沒有送到橋手上（L16：分類要跟著資料走，不是讓每個消費端各猜一份）。

    ## 規則

    1. 共識口徑已核實且基期有對應區塊（含 `operating_income`）→ **跟著共識**。
    2. 共識口徑已核實但基期沒有那個區塊 → 退回可用的那一邊，並**把這件事寫進 warnings**
       （它是真的缺料，不是選擇）。
    3. 共識口徑未核實（`unverified`／`not_applicable`／None）→ 舊規則。
       ⚠ **不 fail closed**：營收沒有口徑之分，而很多標的的共識就是無從核實；
       在那些檔上要求核實會讓整條橋停掉，那是這個 gate 攔錯東西（L15-1）。
    """
    def usable(name: str) -> bool:
        blk = actuals.block(name) or {}
        return blk.get("operating_income") is not None

    legacy = "non_gaap" if usable("non_gaap") else "gaap"
    if consensus_basis not in ("gaap", "non_gaap"):
        return legacy, None
    if usable(consensus_basis):
        if consensus_basis != legacy:
            return consensus_basis, (
                f"橋口徑跟著**已核實的共識口徑** {consensus_basis} 走（舊規則會選 {legacy}）"
                "——內部 EPS 最後要對的就是那一串共識，口徑不同的比較是假差距")
        return consensus_basis, None
    other = "gaap" if consensus_basis == "non_gaap" else "non_gaap"
    return (other if usable(other) else legacy), (
        f"已核實的共識口徑是 {consensus_basis}，但基期觀測的 {consensus_basis} 區塊沒有 "
        "operating_income——橋只能用另一邊算，**這個比較因此帶著口徑差，不是純預期差**")


def build_bridge(
    actuals: FiscalYearActuals,
    assumptions: Sequence[OperatingAssumption],
    target: FiscalPeriod,
    *,
    consensus_basis: str | None = None,
) -> BridgeResult:
    """把基期觀測與假設算成目標期間的內部估計。

    `consensus_basis`（2026-09-13 新增）＝**已核實的共識口徑**
    （`alpha/fundamental/compare.py::verify_consensus_basis` 的結論，`gaap`／`non_gaap`）。
    給了就照它選橋的口徑，因為內部 EPS 最後要去對的就是那一串共識。
    不給（或給的口徑在基期裡沒有可用區塊）就退回舊規則。
    """
    steps: list[BridgeStep] = []
    warnings: list[str] = []
    base_refs = actuals.refs

    basis, basis_why = _select_basis(actuals, consensus_basis)
    if basis_why:
        warnings.append(basis_why)
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
    if base_om is None and actuals.income_statement_shape == "no_operating_income":
        # ⚠⚠ **這不是缺料，是這條鏈對這家公司不成立**（2026-09-13）。
        # 實測 APO／BX：SEC XBRL companyfacts 裡 `OperatingIncomeLoss` 與 `GrossProfit`
        # 兩個 tag 都不存在。硬用「稅前 ÷ 營收」當營益率會得到一個**隨市場評價擺動、
        # 沒有任何人管理的比率**——L14 明文禁止讓未量測的機制決定數字。
        # 缺席的**種類**因此不同：說「去補 operating_income」會送人去找一個不存在的東西。
        margin_reason = (
            f"基期觀測宣告 `income_statement_shape=no_operating_income`——"
            f"這家公司的損益表上**沒有 operating income 這一行**（{basis} 區塊也因此沒有），"
            "而橋是一條乘法鏈（營收 × 營益率 → 稅前 → EPS）。"
            "**這不是缺料，補資料解不掉**：硬用「稅前 ÷ 營收」當營益率會得到一個隨市場評價"
            "擺動、沒有任何人管理的比率。"
            "要讓這一類可估需要的是**能表達 ANI／DE 的加法鏈**"
            "（FRE ＝ 費用收入 − 費用相關支出；SRE ＝ 淨投資收益 − 資金成本；"
            "ANI ＝ FRE ＋ SRE ＋ 本金投資收益 − 稅），而那條鏈還不存在（見 ROADMAP）。"
            "**在那之前這一檔維持 blocked 是正確的，不是漏做。**")
    elif base_om is None:
        margin_reason = f"基期觀測缺 {basis}.operating_income，算不出基期營益率"
    elif not deltas:
        margin_reason = _absent(
            "operating_margin_delta",
            "沒有 operating_margin_delta 假設——沿用基期也必須是一條寫下來的假設（值可為 0）")
    else:
        margin = base_om + sum(d.value for d in deltas)
        if margin > _MAX_OPERATING_MARGIN:
            # 加總後才看得出來的單位錯誤（例：把 +25% 寫成 25）。per-record 的界攔不到這個，
            # 因為它可以被拆成多條 component 分攤——所以檢查在這裡，而且檢查的是**結果**。
            margin_reason = (
                f"內部營益率 {margin:.2%} 超過 100%（基期 {base_om:.2%} ＋ "
                f"{len(deltas)} 條 operating_margin_delta 合計 {margin - base_om:+.2%}）"
                "——營業利益不可能超過營收，這個組合不是估計而是單位錯誤"
                "（⚠ 每一條紀錄各自都在 ±10.0 的界內，是**加總**越界；要修的是那幾條假設，不是界）")
            margin = None
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
    tax_abs = by_key.get(("tax_expense_absolute", TOTAL_SCOPE))
    if tax_rate is not None:
        steps.append(_assumption_step("tax_rate", "有效稅率假設", tax_rate))
    if tax_abs is not None:
        steps.append(_assumption_step("tax_expense_absolute", "所得稅費用假設（絕對金額）", tax_abs))
    tax_formula = "internal_pretax_income × tax_rate"
    if tax_rate is not None and tax_abs is not None:
        # 兩個都寫＝一格兩義（L12）。不挑一個用，也不相加——直接拒絕並說出要刪哪一條。
        tax, tax_ids = None, pretax_ids + [tax_rate.assumption_id, tax_abs.assumption_id]
        tax_reason = ("同時有 tax_rate 與 tax_expense_absolute 假設——兩者二擇一，"
                      "不得並存也不得相加（同一筆稅會被算兩次）。"
                      "稅前接近零或有一次性稅務項目時用絕對金額，其餘用比率；"
                      "要換就 append 一筆 retracted 撤回不要的那一條")
    elif tax_abs is not None:
        # 絕對金額優先於比率的理由不是偏好，是**它不依賴稅前**：稅前接近零時比率會爆掉
        # （XFAB.PA FY2026 實效稅率 681.6%），而絕對金額仍然是一個有意義的數。
        tax = tax_abs.value if pretax is not None else None
        tax_ids = pretax_ids + [tax_abs.assumption_id]
        tax_formula = "tax_expense_absolute（絕對金額，不乘稅前）"
        tax_reason = None if tax is not None else pretax_reason
    else:
        tax = (pretax * tax_rate.value) if (pretax is not None and tax_rate is not None) else None
        tax_ids = pretax_ids + ([tax_rate.assumption_id] if tax_rate else [])
        tax_reason = (None if tax is not None else
                      (_absent("tax_rate", "缺 tax_rate 假設（或 tax_expense_absolute——二擇一）")
                       if tax_rate is None else pretax_reason))
    _emit(steps, "internal_income_taxes", f"內部所得稅（{basis}）", tax, "currency",
          tax_formula, tax_ids, base_refs, tax_reason)
    net_income = (pretax - tax) if (pretax is not None and tax is not None) else None
    _emit(steps, "internal_net_income", f"內部淨利（{basis}，歸屬前）", net_income, "currency",
          "internal_pretax_income − internal_income_taxes", tax_ids, base_refs, tax_reason)

    # ---- 6. 非控制權益 → 歸屬母公司 ---------------------------------------
    nci = by_key.get(("nci_attribution", TOTAL_SCOPE))
    if nci is not None:
        steps.append(_assumption_step("nci_attribution", "非控制權益調整假設", nci))
    # 2026-09-13：稅後的分子有**四種**東西要進，先前只有一格（L12：一個表示承載多種語意）。
    # ①NCI（加或扣）②特別股股息（扣）③稀釋 EPS 分子調整（IAS 33，加回）
    # ④停業單位——④刻意**沒有** driver：它不是「調整」而是「另一段損益」，
    # 硬塞進來會讓「繼續營業 EPS」與「含停業單位 EPS」在同一條鏈上分不開；
    # 正確做法是基期整筆採繼續營業口徑（NBIS 2026-09-13 的處理），
    # 而基期自己的 EPS 對帳不上時由 `closure-gate` 的常駐計數器指出來。
    preferred = by_key.get(("preferred_dividends", TOTAL_SCOPE))
    if preferred is not None:
        steps.append(_assumption_step("preferred_dividends", "特別股股息假設", preferred))
    numerator_adj = by_key.get(("diluted_eps_numerator_adjustment", TOTAL_SCOPE))
    if numerator_adj is not None:
        steps.append(_assumption_step("diluted_eps_numerator_adjustment",
                                      "稀釋 EPS 分子調整假設（IAS 33）", numerator_adj))
    attributable = (net_income + nci.value) if (net_income is not None and nci is not None) else None
    if attributable is not None and preferred is not None:
        attributable -= preferred.value
    if attributable is not None and numerator_adj is not None:
        attributable += numerator_adj.value
    attributable_ids = tax_ids + ([nci.assumption_id] if nci else [])         + ([preferred.assumption_id] if preferred else [])         + ([numerator_adj.assumption_id] if numerator_adj else [])
    attributable_reason = (None if attributable is not None else
                           (_absent("nci_attribution", "缺 nci_attribution 假設")
                            if nci is None else tax_reason))
    attributable_formula = ("internal_net_income + nci_attribution"
                            + (" − preferred_dividends" if preferred is not None else "")
                            + (" + diluted_eps_numerator_adjustment" if numerator_adj is not None else ""))
    _emit(steps, "internal_net_income_attributable", f"內部歸屬母公司淨利（{basis}）", attributable,
          "currency", attributable_formula, attributable_ids, base_refs,
          attributable_reason)
    metrics["net_income"] = _metric("net_income", attributable, "currency",
                                    attributable_formula, attributable_ids,
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
