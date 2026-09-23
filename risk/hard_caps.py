"""成交路徑的兩道資本硬擋：5% 單筆 NAV 上限與 ETF 槓桿 cap（Phase 0 Step 0b.4，G12）。

## 前身與為什麼搬家

這條規則原本住在 `decision_lab/store.py::_assert_user_sized_within_capital_caps`，讀的是
Engine D 凍結的 sizing 快照（`live_blockers`／`live_current_position`／`single_position_nav_cap`）。
那條鏈（cohort → context → coverage → decision → live_choice）在 Phase 0 整段退役、舊店凍結唯讀，
而實際在用的成交路徑 `scripts/record_trade.py` **從來不查上限**——煞車裝在沒有人走的路上
（`AGENTS.md`「煞車仍在，而且必須住在真的有人走的路上」）。這裡把**規則**搬到成交路徑，
輸入改成部位真相本身（Google Sheet 持股列），不再依賴任何凍結快照。

## 規則（Numeric SSOT 不在本檔）

- **5% 單筆 NAV 上限**：`config/investment_policy.json` 的 `single_position_nav_cap`。只管 alpha
  （不在 `config/beta_policy.json` `instruments` 裡的標的）：beta ETF 本來就會超過 5%，對它們套這條
  只會讓每筆定投都要 override，煞車變噪音後就會被忽略（L14）。
- **ETF 槓桿 cap**：`beta_policy.json` `risk.leveraged_nominal_cap`／`leveraged_effective_cap`。
  只在成交標的是 `leverage_multiple > 1` 的 instrument 時比；nominal＝投入槓桿 ETF 的資金占 NAV，
  effective＝乘上倍數後的曝險占 NAV（兩個指標不得混用，`AGENTS.md`）。
- **賣出不檢查**：它不增加任何曝險，`not_applicable`。
- **量不到就 fail closed**（INV-6／L12「持有 0% 與量不到不是同一件事」）：NAV 缺席或不一致、
  持股列讀不到、成交幣別 ≠ NAV 基準幣別而沒有匯率——一律 `unmeasurable`，呼叫端當成擋下。

## 這裡不做什麼

不算建議尺寸、不給區間、不對 warning 級門檻做任何事（warning 只住 `risk/snapshot.py` 的觀測）。
override 的收據由呼叫端（`record_trade.py`）寫進 trade_log，本模組只回 verdict。
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from portfolio.policy import load_beta_policy
from risk.policy import load_policy
from risk.snapshot import build_portfolio_components

__all__ = [
    "HardCapVerdict",
    "check_trade_hard_caps",
    "gross_in_base_currency",
]

#: verdict 的封閉字彙。`blocked` 與 `unmeasurable` 對呼叫端都是「不放行」，分開是為了讓收據
#: 說得出是「超過上限」還是「量不到」——兩者導向的修法不同（前者改尺寸，後者修 Sheet／匯率）。
VERDICTS = ("pass", "blocked", "unmeasurable", "not_applicable")


@dataclass(frozen=True)
class HardCapVerdict:
    status: str
    breaches: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    measures: dict[str, Any] = field(default_factory=dict)

    @property
    def allows(self) -> bool:
        return self.status in ("pass", "not_applicable")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["breaches"] = list(self.breaches)
        payload["reasons"] = list(self.reasons)
        return payload


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def gross_in_base_currency(
    *,
    gross: float,
    trade_currency: str,
    base_currency: str | None,
    fx_to_base: float | None,
) -> tuple[float | None, str | None]:
    """成交總額換成 NAV 基準幣別。回 (金額, 失敗理由)；幣別不同又沒匯率 → (None, 理由)。

    匯率由呼叫端明確給（`--fx-to-base`，1 成交幣 = X 基準幣）。刻意不偷讀任何行情源：
    這是資本 gate，輸入必須是使用者看得到、答得出來源的數字（INV-6）。
    """
    trade_ccy = str(trade_currency or "").strip().upper()
    base_ccy = str(base_currency or "").strip().upper()
    if not base_ccy:
        return None, "Sheet 沒有 NAV 基準幣別（base_currency）"
    if trade_ccy == base_ccy:
        return float(gross), None
    rate = _finite(fx_to_base)
    if rate is None or rate <= 0:
        return None, (
            f"成交幣別 {trade_ccy} ≠ NAV 基準幣別 {base_ccy}，且未提供 --fx-to-base"
            f"（1 {trade_ccy} = ? {base_ccy}）"
        )
    return float(gross) * rate, None


def _instrument_for(symbol: str, beta_policy: Mapping[str, Any]) -> Mapping[str, Any] | None:
    key = symbol.strip().upper()
    for instrument in beta_policy["instruments"]:
        if key in {str(alias).upper() for alias in instrument["sheet_aliases"]}:
            return instrument
    return None


def _held_value_for_symbol(rows: Sequence[Mapping[str, Any]], symbol: str) -> float:
    key = symbol.strip().upper()
    total = 0.0
    for row in rows:
        if str(row.get("ticker") or "").strip().upper() != key:
            continue
        value = _finite(row.get("market_value_base"))
        if value is not None:
            total += value
    return total


def check_trade_hard_caps(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    symbol: str,
    side: str,
    gross_base: float | None,
    gross_reason: str | None = None,
    already_in_sheet: bool = False,
    investment_policy: Mapping[str, Any] | None = None,
    beta_policy: Mapping[str, Any] | None = None,
) -> HardCapVerdict:
    """對一筆成交回 verdict。

    - `rows`：`fetchers.gsheets.fetch_portfolio(strict_operational=True)` 的持股列；`None`＝讀不到。
    - `gross_base`：成交總額（NAV 基準幣別）；`None` 時帶 `gross_reason` 說明為何換不出來。
    - `already_in_sheet`：`--log-only`（使用者已手動改過 Sheet）時為 True——Sheet 已是成交後狀態，
      不再把總額加一次。
    """
    if side == "sell":
        return HardCapVerdict(
            status="not_applicable",
            reasons=("賣出不增加曝險，硬擋不適用",),
        )
    if side != "buy":
        return HardCapVerdict(status="unmeasurable", reasons=(f"未知的 side：{side!r}",))

    investment_policy = investment_policy or load_policy()
    beta_policy = beta_policy or load_beta_policy()

    if rows is None:
        return HardCapVerdict(
            status="unmeasurable",
            reasons=("Google Sheet 持股列讀不到，NAV 量不到",),
        )
    components = build_portfolio_components(rows, beta_policy)
    # 每一個 blocker 都讓分母（NAV）或分子（市值）不可信；含 market_value 與 NAV 對不上
    # （2026-09-23 實測 live Sheet 對得上——`library/private/app/state/beta.json` 的
    # `risk.snapshot.blockers` 為空——所以這條不會對正常 Sheet 恆亮）。
    fatal = [
        code for code in components["blockers"]
        if code in ("holdings_unavailable", "holdings_nav_missing", "holdings_nav_inconsistent",
                    "holdings_base_currency_inconsistent", "holdings_malformed",
                    "holdings_market_value_nav_mismatch")
    ]
    if fatal:
        return HardCapVerdict(
            status="unmeasurable",
            reasons=tuple(f"持股列不可用於量測：{code}" for code in fatal),
            measures={"blockers": list(components["blockers"])},
        )
    nav = float(components["nav_base"])
    if gross_base is None:
        return HardCapVerdict(
            status="unmeasurable",
            reasons=(gross_reason or "成交總額換不成 NAV 基準幣別",),
            measures={"nav_base": nav, "base_currency": components["base_currency"]},
        )
    delta = 0.0 if already_in_sheet else float(gross_base)

    single_cap = float(investment_policy["single_position_nav_cap"])
    risk = beta_policy["risk"]
    nominal_cap = float(risk["leveraged_nominal_cap"])
    effective_cap = float(risk["leveraged_effective_cap"])

    instrument = _instrument_for(symbol, beta_policy)
    breaches: list[str] = []
    reasons: list[str] = []
    measures: dict[str, Any] = {
        "nav_base": nav,
        "base_currency": components["base_currency"],
        "gross_base": float(gross_base),
        "already_in_sheet": already_in_sheet,
        "symbol": symbol.strip().upper(),
    }

    if instrument is None:
        held = _held_value_for_symbol(rows, symbol)
        weight = (held + delta) / nav
        measures.update({
            "rule": "single_position_nav_cap",
            "held_base": held,
            "post_trade_weight": weight,
            "single_position_nav_cap": single_cap,
        })
        if weight > single_cap + 1e-12:
            breaches.append("single_position_nav_cap_reached")
            reasons.append(
                f"成交後 {symbol.upper()} 占 NAV {weight:.2%}，超過單筆上限 {single_cap:.0%}"
            )
    else:
        leverage = float(instrument["leverage_multiple"])
        measures.update({
            "rule": "etf_leverage_caps" if leverage > 1 else "beta_unlevered_no_hard_cap",
            "instrument": str(instrument["ticker"]),
            "leverage_multiple": leverage,
        })
        if leverage > 1:
            nominal = (float(components["leveraged_nominal_base"]) + delta) / nav
            effective = (float(components["leveraged_effective_base"]) + delta * leverage) / nav
            measures.update({
                "post_trade_nominal_weight": nominal,
                "post_trade_effective_weight": effective,
                "leveraged_nominal_cap": nominal_cap,
                "leveraged_effective_cap": effective_cap,
            })
            if nominal > nominal_cap + 1e-12:
                breaches.append("etf_leverage_nominal_cap_reached")
                reasons.append(
                    f"成交後槓桿 ETF 資金占 NAV {nominal:.2%}（nominal_weight），"
                    f"超過 cap {nominal_cap:.0%}"
                )
            if effective > effective_cap + 1e-12:
                breaches.append("etf_leverage_effective_cap_reached")
                reasons.append(
                    f"成交後換算槓桿曝險 {effective:.2%}（effective_weight），"
                    f"超過 cap {effective_cap:.0%}"
                )
        else:
            reasons.append("beta 未槓桿 instrument：band 是容忍區間不是 gate，無硬擋")

    if breaches:
        return HardCapVerdict(
            status="blocked", breaches=tuple(breaches), reasons=tuple(reasons), measures=measures,
        )
    return HardCapVerdict(status="pass", reasons=tuple(reasons), measures=measures)
