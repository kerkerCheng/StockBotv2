"""邊緣判定的取數（Phase 3 Step 3.3）：讀 `config/alpha_screen.json` 的兩個數＋正規化市值與覆蓋家數。

判定本身住 `alpha/edge.py`（純函式）；市值正規化住 `alpha/providers/market_normalization.py`（Phase 0 註明
「Phase 3 候選板接手時仍從這裡取」）。**一輪只打一次外部**（同一個 FX 快取），所以只在 materialize 呼叫——
request path 與資本路徑一律讀 artifact（plan §4.3）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..edge import edge_state

_ROOT = Path(__file__).resolve().parents[2]
ALPHA_SCREEN_PATH = _ROOT / "config" / "alpha_screen.json"


def load_edge_thresholds(path: Path | None = None) -> dict[str, Any]:
    """兩個數（AND）。讀不到或不合法就 raise——**不猜一個預設值**（缺門檻時的「邊緣」是假的）。"""
    payload = json.loads(Path(path or ALPHA_SCREEN_PATH).read_text(encoding="utf-8"))
    cap = payload.get("market_cap_max_usd")
    cov = payload.get("analyst_count_max")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not isinstance(cov, int) or isinstance(cov, bool):
        raise ValueError("config/alpha_screen.json 缺 market_cap_max_usd／analyst_count_max 或型別不對")
    return {"market_cap_max_usd": float(cap), "analyst_count_max": int(cov),
            "effective_from": payload.get("effective_from"), "version": payload.get("version")}


def edge_states(tickers: Sequence[str], *, db_path: Path | None = None,
                thresholds: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """一批標的的邊緣判定（每檔都回值；取不到的輸入落 `unmeasurable`，不丟檔）。"""
    from .market_normalization import screen_inputs

    limits = dict(thresholds or load_edge_thresholds())
    inputs = screen_inputs(list(tickers), db_path=db_path)
    out: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        row = inputs.get(ticker) or {}
        out[ticker] = edge_state(market_cap_usd=row.get("market_cap_usd"), analyst_count=row.get("analyst_count"),
                                 thresholds=limits, market_cap_absence=row.get("market_cap_absence"))
        out[ticker]["threshold_version"] = {"effective_from": limits.get("effective_from"),
                                            "version": limits.get("version")}
    return out


def _yfinance_info(ticker: str) -> Mapping[str, Any]:
    import yfinance as yf

    return yf.Ticker(ticker).info or {}


def _yfinance_inputs(ticker: str, info: Mapping[str, Any], fx_cache: dict[str, float | None]) -> dict[str, Any]:
    """名冊外的取數：市值＝價格×股數（報價單位照 `identity/currency.py` 換成結算幣別，再換美元——同
    `market_normalization.normalized_market_cap` 的兩步，只是價格與股數改取 yfinance）；家數＝yfinance 的分析師人數。
    ⚠ 不用 yfinance 的 marketCap 欄：小單位報價（GBp 等）時它的單位不保證，價格×股數才跟著報價單位走。"""
    from identity.currency import resolve_quote_unit

    from .market_normalization import to_usd

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
    unit_code = info.get("currency")
    cap, absence = None, None
    if not price or not shares:
        absence = "yfinance 沒有價格或股數"
    else:
        unit = resolve_quote_unit(unit_code)
        if unit is None:
            absence = f"報價單位 {unit_code!r} 未登記於 currency_units.json（fail closed）"
        else:
            cap = to_usd(unit.to_settlement(float(price) * float(shares)), unit.currency, fx_cache)
            if cap is None:
                absence = f"取不到 {unit.currency}/USD 匯率"
    analysts = info.get("numberOfAnalystOpinions")
    return {"market_cap_usd": cap, "market_cap_absence": absence,
            "analyst_count": int(analysts) if isinstance(analysts, (int, float)) and not isinstance(analysts, bool) else None}


def adhoc_edge_states(tickers: Sequence[str], *, fetch_info: Any = None, fx_cache: dict[str, float | None] | None = None,
                      thresholds: Mapping[str, Any] | None = None, registry_inputs: Any = None) -> dict[str, dict[str, Any]]:
    """研究時判邊緣（failure log #43，使用者 2026-10-07「可以 做掉」）：**名冊外的代號也能判**，不再目測市值。

    判定仍是同一個純函式 `alpha/edge.py::edge_state`、同一份門檻；只有取數不同：名冊內而且 Engine C 有值的欄位照用
    `screen_inputs`（候選板同一條路），缺的欄位才用 yfinance 補，**每個欄位標來源**。唯讀：不寫任何 authority。
    取數失敗（含限流）照實落 `unmeasurable` 並寫理由（INV-3）。"""
    from .market_normalization import screen_inputs

    limits = dict(thresholds or load_edge_thresholds())
    fetch = fetch_info or _yfinance_info
    cache: dict[str, float | None] = fx_cache if fx_cache is not None else {}
    canonical = registry_inputs(list(tickers)) if registry_inputs is not None else screen_inputs(list(tickers))
    out: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        base = dict(canonical.get(ticker) or {})
        sources = {"market_cap": "名冊＋Engine C" if base.get("market_cap_usd") is not None else None,
                   "analyst_count": "Engine C 共識（0y）" if base.get("analyst_count") is not None else None}
        if base.get("market_cap_usd") is None or base.get("analyst_count") is None:
            try:
                extra = _yfinance_inputs(ticker, fetch(ticker), cache)
            except Exception as exc:  # noqa: BLE001 — 取不到就照實寫，不中斷整批
                extra = {"market_cap_usd": None, "market_cap_absence": f"yfinance 取不到：{str(exc)[:80]}",
                         "analyst_count": None}
            if base.get("market_cap_usd") is None:
                base["market_cap_usd"] = extra["market_cap_usd"]
                base["market_cap_absence"] = extra["market_cap_absence"]
                sources["market_cap"] = "yfinance（價格×股數，報價單位換算）" if extra["market_cap_usd"] is not None else None
            if base.get("analyst_count") is None:
                base["analyst_count"] = extra["analyst_count"]
                sources["analyst_count"] = "yfinance numberOfAnalystOpinions" if extra["analyst_count"] is not None else None
        out[ticker] = edge_state(market_cap_usd=base.get("market_cap_usd"), analyst_count=base.get("analyst_count"),
                                 thresholds=limits, market_cap_absence=base.get("market_cap_absence"))
        out[ticker]["sources"] = sources
        out[ticker]["threshold_version"] = {"effective_from": limits.get("effective_from"), "version": limits.get("version")}
    return out


__all__ = ["ALPHA_SCREEN_PATH", "adhoc_edge_states", "edge_states", "load_edge_thresholds"]
