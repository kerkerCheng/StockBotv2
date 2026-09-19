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


def _horizon_from_judgment(ticker: str) -> tuple[date | None, str | None, str]:
    """從 session 判斷檔讀 `multiple_horizon`。**讀不到就是沒有**，不猜。

    回 `(horizon, reason, kind)`。⚠ **`kind` 由這裡宣告，呼叫端不得 parse 理由句去猜**
    （L16：分類有 SSOT 就要跟著資料走到需要它的地方）。2026-09-19 實測到的代價：
    16 檔裡 14 檔非 available，counts 卻只有一格 `no_horizon`，於是「還沒有人寫下來」
    （13 檔，我們的待辦）與「連判斷檔都沒有」（1 檔，更前面的缺口）被壓成同一個數字，
    而心跳、APP、CLI 三個消費端都把它印成「還沒寫下目標年度」——**其中一檔並不是**。
    """
    import json

    from .alpha_view.sources import locate_judgment

    path = locate_judgment(ticker)
    if path is None:
        return None, "找不到 session 判斷檔——多年橋要先知道這個 thesis 在講哪一年", "no_judgment"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"判斷檔無法讀取：{type(exc).__name__}", "judgment_unreadable"
    value = raw.get("multiple_horizon")
    if not value:
        return None, NO_HORIZON_REASON, "no_horizon"
    try:
        return date.fromisoformat(str(value)[:10]), None, "available"
    except ValueError:
        return None, f"`multiple_horizon` 不是合法日期：{value!r}", "horizon_invalid"


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

    horizon, why, kind = _horizon_from_judgment(ticker)
    if horizon is None:
        # status 直接用宣告出來的 kind——**不另外壓成 "missing"**，否則下游又要 parse 理由句。
        return MultiYearView(horizon=None, status=kind, reason=why, **common)

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

    # ⚠ 虧損基期：錨點 EPS ≤ 0 時，反解在算術上仍然有答案，但**那個答案的語意不是
    # 「這個結構允不允許 N 倍」**——它只是「從一個負數漲到一個正數要多少」。兩者在
    # 今天的輸出裡長得一模一樣（L12：一個表示承載兩種語意，而下游被迫二選一）。
    # 實測（2026-09-19，[633] 寫入 AXTI 的 FY2028 錨點當天）：AXT FY2025 非 GAAP 營益率
    # −21.2%，`carried_forward`（成長歸 0）＝沿用那個虧損 → 錨點 EPS −0.0789，於是四級
    # 階梯全部印「拉到極限也做不到」——**與同一檔 FY+1 反向橋的「2x available」方向相反**。
    # 那不是結構結論，是儀器在虧損期失效。改用封閉字彙裡既有的 `method_not_applicable`
    # 現形（AGENTS.md：使用者必須分得出還沒做／刻意不主張／**方法不適用**／上游缺料）。
    # ⚠ 這不是放寬 gate：被擋的檔數一個沒少，只是「做不到」與「量不了」不再同形。
    # 研究層早就指名過這個缺口——Abstention ledger 有三筆逐字寫著要「虧損期 method」。
    if anchor_eps is not None and anchor_eps <= 0:
        return MultiYearView(
            horizon=horizon, status="method_not_applicable", base_period=actuals.period,
            span_years=bridge.span_years, target_multiple=multiple, multiple_source=source,
            current_price=price, anchor_eps=anchor_eps, bridge_warnings=bridge.warnings,
            reason=(f"錨點 EPS 是 {anchor_eps:,.4f}（≤ 0）——**基期在虧損，而錨點取的是"
                    "「沿用基期」**，所以這一年的錨點也是負的。反解此時問的是「從負數漲到"
                    "正數要多少」，**那不是「這個結構允不允許 N 倍」**。⚠ 不印階梯：印出來"
                    "每一級都會是「拉到極限也做不到」，而那句話會被讀成結構結論。"
                    "**要讓這一檔算得出來，需要的是一個虧損期適用的錨點方法**（例如 mid-cycle "
                    "利潤率），不是改倍率也不是放寬 driver 上下限"), **common)

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
        # ⚠ 「算不出來」與「這個方法不適用」是兩件事，不得同形（AGENTS.md 的四種缺席）。
        # 前者是缺料（補了就算得出來）；後者是**已經算了、而且知道答案沒有意義**。
        head = ("**這個方法在這一檔不適用**" if view.status == "method_not_applicable"
                else "**算不出來**")
        out.append(f"{head}：{view.reason}")
        if view.horizon:
            out.append(f"（目標年度：{view.horizon.isoformat()}"
                       + (f"｜基期 {view.base_period.label}｜距離 {view.span_years} 年"
                          if view.base_period and view.span_years is not None else "")
                       + "）")
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


__all__ = ["NO_HORIZON_REASON", "MultiYearView", "build_multi_year_artifact",
           "build_multi_year_view", "render_multi_year"]


def build_multi_year_artifact(
    tickers: Sequence[str], *, generated_at: Any = None,
) -> dict[str, Any]:
    """所有標的的多年階梯 → `multi_year` state artifact（Phase 7 Step 7.4，2026-09-19）。

    ⚠ **它必須是 materialize 出來的，不能在 request path 算**：多年橋是金融模型，
    而 APP 呈現契約明文禁止 request path 跑模型（`tests/test_webapp_request_path.py`）。

    ⚠ **每一檔都進 rows，包括算不出來的**——「還沒有人寫下 `multiple_horizon`」
    與「artifact 讀不到」是兩件事，也與「這一檔沒有多年主張」是兩件事（INV-3）。
    """
    from datetime import datetime, timezone

    stamp = (generated_at or datetime.now(timezone.utc))
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            view = build_multi_year_view(ticker)
        except Exception as exc:  # noqa: BLE001 — 單檔失敗不讓整份 artifact 失敗
            rows.append({"ticker": ticker, "status": "missing",
                         "reason": f"{type(exc).__name__}: {str(exc)[:160]}"})
            continue
        rows.append({
            "ticker": view.ticker, "company_id": view.company_id,
            "horizon": view.horizon.isoformat() if view.horizon else None,
            "status": view.status, "reason": view.reason,
            "base_period": view.base_period.label if view.base_period else None,
            "span_years": view.span_years, "target_multiple": view.target_multiple,
            "multiple_source": view.multiple_source, "current_price": view.current_price,
            "anchor_eps": view.anchor_eps,
            "bridge_warnings": [w for w in view.bridge_warnings if "累積值" in w],
            "ladder": [
                {"multiple": r.target_return_multiple, "required_eps": r.required_eps,
                 "required_gap": r.required_gap, "status": r.status,
                 "unreachable": [s.driver for s in r.unreachable_drivers],
                 "solutions": [{"driver": s.driver, "scope": s.scope,
                                "our_value": s.our_value, "implied_value": s.implied_value,
                                "status": s.status} for s in r.solutions]}
                for r in view.ladder
            ],
        })
    # ⚠ 五格**互斥且窮盡**（INV-3）：available ＋ no_horizon ＋ no_judgment ＋
    # method_not_applicable ＋ other_missing == input。2026-09-19 之前只有
    # `no_horizon` 一格而它其實是「所有非 available」，於是三個消費端都把
    # 「連判斷檔都沒有」與「錨點是負的」一起印成「還沒寫下目標年度」——**都不是**。
    # 判準一句話：**這一格是「我們還沒做」，還是「做了而方法不適用」？** 兩者不得同形。
    _known = {"available", "no_horizon", "no_judgment", "method_not_applicable"}
    counts = {
        "input": len(rows),
        "available": sum(1 for r in rows if r["status"] == "available"),
        "no_horizon": sum(1 for r in rows if r["status"] == "no_horizon"),
        "no_judgment": sum(1 for r in rows if r["status"] == "no_judgment"),
        "method_not_applicable": sum(1 for r in rows if r["status"] == "method_not_applicable"),
        # 其餘缺料（沒基期觀測／沒那一年的假設／沒現價／沒 target_pe／判斷檔壞了／日期非法）。
        # 這一格**不是垃圾桶**：它每長大一次就代表有一種缺席還沒有自己的名字。
        "other_missing": sum(1 for r in rows if r["status"] not in _known),
    }
    payload: dict[str, Any] = {
        "kind": "multi_year",
        "schema_version": "stockbot-app/multi_year/1",
        "title": "要幾倍，哪一格得為真",
        "generated_at": stamp.isoformat(),
        "as_of": stamp.date().isoformat(),
        # 多年橋**沒有 as-of 投影**：它問的是「從今天的基期出發，要 N 倍需要什麼」，
        # 那個問題本身沒有歷史視角。不假裝有。
        "point_in_time": {"as_of": None, "mode": "current"},
        "authority": {
            "function": "briefing.multi_year.build_multi_year_artifact",
            "command": "python -m webapp materialize --multi-year",
            "note": ("目標年度來自各檔 judgment 的 `multiple_horizon`（judgment，走 pq2）；"
                     "假設來自 private ledger；倍數沿用 FY+1 的 target_pe 並逐檔標明。"
                     "**這不是預測**——它問「要 N 倍，某個 driver 得是多少」。"),
        },
        "materializer": {
            "version": "multi-year/1",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
        "return_multiples": list(RETURN_MULTIPLE_LADDER),
        "counts": counts,
        "rows": rows,
        "this_is_not": (
            "這不是預測，也不是目標價。「需要 EPS 25.39」的意思是「**要兩倍的話** EPS 得是那個數」，"
            "而那個數合不合理由人判斷。⚠「拉到極限也做不到」是結論不是缺料，"
            "但它的強度取決於 `ASSUMPTION_DRIVERS` 宣告的上下限。"
        ),
    }
    from webapp.contracts import canonical_digest, state_freshness_identity

    # 認知狀態＝每一檔的「目標年度、算不算得出來、每一級的結論」。
    # ⚠ `required_eps` 的小數變動**不算**認知變化——它每天跟著股價動，
    # 但「2 倍需要營收成長 4.65 倍、3 倍以上做不到」這個結論不會（同 account_scorecard 的取捨）。
    payload["freshness_identity"] = state_freshness_identity(
        kind="multi_year", as_of=payload["as_of"],
        identity={"rows": [[r["ticker"], r.get("horizon"), r["status"],
                            [[x["multiple"], x["status"], sorted(x["unreachable"])]
                             for x in (r.get("ladder") or ())]]
                           for r in rows]})
    payload["content_digest"] = canonical_digest(payload)
    return payload
