"""多年視角：「要 N 倍，哪一格得為真」（Phase 7 Step 7.3，2026-09-19）。

## 它為什麼是一條**獨立**的路徑，不是主 view 多一格

`build_fundamental_model` 的目標期間永遠是 `actuals.period.shifted(1)`——**主 view 結構上
到不了 FY+4**，而那是對的：FY+1 那條鏈要對的是分析師共識，共識只到 FY+1／+2。
多年橋問的是另一個問題（「要幾倍，需要什麼為真」），它**沒有共識可對**，
所以它不該混進同一張表。

⚠ **兩條路徑共用同一條橋、同一套二分法、同一組合法上下限**——差別只有目標期間與起點價格。
不共用的是「要對誰」：FY+1 對共識，多年對倍率。

## 三件刻意誠實的事

1. **`multiple_horizon` 沒填就 missing**，不套統一年期、不從 `expected_horizon` 換算
   （後者測的是「多久會被驗證」，2026-09-19 實測 62 檔全部落在 1–8 季）。
2. **目標倍數沿用 FY+1 的那一個，並且說出來**——沒有人知道四年後市場付幾倍，
   沿用等於假設「那時市場付一樣的倍數」。**那是一個假設，不是一個觀測。**
3. **`no_sign_change` 是答案不是失敗**：「即使把這個 driver 拉到合法極限也撐不起 N 倍」
   是一個結論，比「需要成長 340%」這個數字有用得多。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Sequence

from alpha.fundamental.bridge import build_bridge
from alpha.fundamental.contracts import FiscalPeriod
from alpha.identity import Ticker
from alpha.providers import assumptions as assumption_ledger
from alpha.providers import valuation_assumptions as valuation_ledger
from alpha.providers.fundamentals import EngineCFundamentalsProvider
from alpha.reverse import RETURN_MULTIPLE_LADDER, ReverseBridgeResult, build_reverse_bridge


#: `multiple_horizon` 沒填時的理由。**抽成常數是為了讓實作與守門測試共用同一份字串**——
#: 測試寫死一份就會各自腐壞（這條測試 2026-09-19 第一次跑就抓到我自己的 fixture 寫錯）。
NO_HORIZON_REASON = (
    "判斷檔沒有 `multiple_horizon`——**還沒有人寫下這個 thesis 主張的倍率在哪一年實現**。"
    "⚠ 不從 `expected_horizon` 換算：那測的是「多久會被驗證」，不是「多久兌現」"
)


@dataclass(frozen=True)
class MultiYearView:
    ticker: str
    company_id: str
    horizon: date | None
    status: str
    reason: str | None = None
    base_period: FiscalPeriod | None = None
    span_years: int | None = None
    target_multiple: float | None = None
    multiple_source: str | None = None
    current_price: float | None = None
    anchor_eps: float | None = None
    bridge_warnings: tuple[str, ...] = ()
    ladder: tuple[ReverseBridgeResult, ...] = ()


def _horizon_from_judgment(ticker: str) -> tuple[date | None, str | None]:
    """從 session 判斷檔讀 `multiple_horizon`。**讀不到就是沒有**，不猜。"""
    import json

    from .alpha_view.sources import locate_judgment

    path = locate_judgment(ticker)
    if path is None:
        return None, "找不到 session 判斷檔——多年橋要先知道這個 thesis 在講哪一年"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"判斷檔無法讀取：{type(exc).__name__}"
    value = raw.get("multiple_horizon")
    if not value:
        return None, NO_HORIZON_REASON
    try:
        return date.fromisoformat(str(value)[:10]), None
    except ValueError:
        return None, f"`multiple_horizon` 不是合法日期：{value!r}"


def _live(records: Sequence[Any], *, period_end: date) -> list[Any]:
    superseded = {r.supersedes_id for r in records if getattr(r, "supersedes_id", None)}
    return [r for r in records
            if not r.retracted and r.assumption_id not in superseded
            and getattr(r, "period", None) is not None and r.period.end == period_end
            and getattr(r, "scenario", "base") == "base"]


def build_multi_year_view(
    ticker: str, *, multiples: Sequence[float] = RETURN_MULTIPLE_LADDER,
    provider: Any = None,
) -> MultiYearView:
    """一檔的多年階梯。**每一段缺料都以 `missing`＋理由現形，不補預設值。**"""
    from .alpha_view.sources import resolve_company

    resolved, company_id = resolve_company(ticker)
    ticker = str(resolved)
    common = dict(ticker=ticker, company_id=str(company_id))

    horizon, why = _horizon_from_judgment(ticker)
    if horizon is None:
        return MultiYearView(horizon=None, status="missing", reason=why, **common)

    prov = provider or EngineCFundamentalsProvider()
    actuals, actuals_reason = prov.fiscal_year_results(Ticker(ticker))
    if actuals is None:
        return MultiYearView(horizon=horizon, status="missing",
                             reason=f"沒有基期觀測——沒有橋就無從反解（{actuals_reason}）", **common)

    records, _errors = assumption_ledger.read_assumption_records(ticker)
    live = _live(records, period_end=horizon)
    if not live:
        return MultiYearView(
            horizon=horizon, status="missing", base_period=actuals.period,
            reason=(f"ledger 裡沒有 {horizon.isoformat()} 的生效假設——"
                    "**多年橋需要那一年的假設集合**（即使只是「沿用基期」的錨點）。"
                    "⚠ 不得沿用 FY+1 那一組：它的成長率是一年的，套到多年就變成另一個意思"), **common)

    bridge = build_bridge(actuals, live, FiscalPeriod(end=horizon))
    eps = bridge.metrics.get("eps")
    anchor_eps = eps.value if eps is not None and eps.is_known else None

    market, _fresh = prov.market(Ticker(ticker))
    price = market.price

    val_records, _val_errors = valuation_ledger.read_valuation_assumption_records(ticker)
    val_superseded = {r.supersedes_id for r in val_records if r.supersedes_id}
    target_pe = next((r for r in val_records
                      if r.parameter == "target_pe" and not r.retracted
                      and r.assumption_id not in val_superseded), None)
    multiple = target_pe.value if target_pe is not None else None
    # ⚠ 倍數沿用 FY+1 的那一條，**而且要說出來**：沒有人知道四年後市場付幾倍。
    source = (f"沿用 {target_pe.period.label} 的 target_pe（{target_pe.assumption_id}）"
              "——⚠ **這不是對目標年度的主張**，是「假設那時市場付一樣的倍數」"
              if target_pe is not None else None)

    if price is None or multiple is None:
        return MultiYearView(
            horizon=horizon, status="missing", base_period=actuals.period,
            span_years=bridge.span_years, anchor_eps=anchor_eps,
            bridge_warnings=bridge.warnings, current_price=price,
            target_multiple=multiple, multiple_source=source,
            reason=("沒有現價" if price is None else
                    "沒有生效的 target_pe——反解問的是「在我們的倍數下 EPS 要多少」，"
                    "沒有倍數就沒有那個問題（**不補市場倍數**，那會讓答案恆等於共識）"), **common)

    ladder = tuple(
        build_reverse_bridge(
            company_id=str(company_id), ticker=ticker, as_of=None,
            target_period=FiscalPeriod(end=horizon), actuals=actuals, assumptions=live,
            current_price=price, target_multiple=multiple, our_eps=anchor_eps,
            consensus_eps=None, target_return_multiple=float(m))
        for m in multiples
    )
    return MultiYearView(
        horizon=horizon, status="available", base_period=actuals.period,
        span_years=bridge.span_years, target_multiple=multiple, multiple_source=source,
        current_price=price, anchor_eps=anchor_eps, bridge_warnings=bridge.warnings,
        ladder=ladder, **common)


def render_multi_year(view: MultiYearView) -> str:
    """Markdown。**照抄**，不重算、不挑掉解不出來的那些（INV-3）。"""
    out: list[str] = [f"# 多年視角：要幾倍，哪一格得為真 — {view.ticker}", ""]
    out.append("> **這不是預測。** 它問的是「要 N 倍，某個 driver 得是多少」，"
               "然後由人判斷那個數合不合理。")
    out.append("> ⚠ 與 FY+1 主 view **共用同一條橋**，差別只有目標期間與起點價格；"
               "不共用的是「要對誰」——FY+1 對共識，多年對倍率。")
    out.append("")
    if view.status != "available":
        out.append(f"**算不出來**：{view.reason}")
        if view.horizon:
            out.append(f"（目標年度：{view.horizon.isoformat()}）")
        return "\n".join(out)

    out.append(f"- 目標年度 **{view.horizon.isoformat()}**｜基期 {view.base_period.label}"
               f"｜距離 **{view.span_years} 年**")
    out.append(f"- 現價 {view.current_price:,.2f}｜目標倍數 {view.target_multiple:g}x")
    if view.multiple_source:
        out.append(f"  - {view.multiple_source}")
    if view.anchor_eps is not None:
        out.append(f"- 錨點 EPS（目標年度，照假設算出來的）{view.anchor_eps:,.4f}"
                   "——⚠ **錨點不是預測**，反解用二分法找根，它的值不影響答案")
    for warning in view.bridge_warnings:
        if "累積值" in warning:
            out.append(f"- {warning}")
    out.append("")
    out.append("| 倍率 | 需要 EPS | 比錨點高 | 狀態 | 解得出來的 | 拉到極限也做不到 |")
    out.append("|---|---|---|---|---|---|")
    for result in view.ladder:
        solved = "；".join(
            f"`{s.driver}[{s.scope}]` = {s.implied_value:.4g}"
            for s in result.solutions if s.status == "solved") or "—"
        unreachable = "、".join(f"`{s.driver}`" for s in result.unreachable_drivers) or "—"
        gap = f"{result.required_gap:+.0%}" if result.required_gap is not None else "—"
        out.append(f"| **{result.target_return_multiple:g}x** | {result.required_eps:,.2f} | {gap} "
                   f"| {result.status} | {solved} | {unreachable} |")
    out.append("")
    out.append("⚠ **「拉到極限也做不到」是結論不是缺料**——它說的是「即使把這個 driver 推到"
               "合法區間的端點，EPS 也達不到那個倍率」。強度取決於 `ASSUMPTION_DRIVERS` 宣告的"
               "上下限，而那些當初是為「正向假設的合理範圍」設的。")
    return "\n".join(out)


__all__ = ["NO_HORIZON_REASON", "MultiYearView", "build_multi_year_view", "render_multi_year"]
