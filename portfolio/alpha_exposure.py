"""把 `AlphaSignal[]` 接到投組現況上——**只回答「這些候選我現在持有多少」**。

## 它為什麼存在

Phase 6 之前，`portfolio/` 與 alpha 之間**一條線都沒有**（實測：`portfolio/`／`risk/`
對 `AlphaSignal` 的引用是 0）。於是研究端排出了候選、投組端知道持有什麼，
但**沒有任何地方把兩者放在一起**——使用者要自己在兩份輸出之間對照 ticker。

`target-architecture.md` §9 的分工：`portfolio/` 的輸入是
`AlphaSignal[]` ＋ 現有持股 ＋ `config/target_allocation.json`，
輸出是 target exposure、配置差距、相對水位；**不形成 view、不排序標的**。

## ⚠ 這支不產生任何部位尺寸

`AGENTS.md` Alpha 呈現契約：**系統不給 alpha 部位尺寸。**
所以這裡輸出的每一個數字都是**已經發生的事實**（目前佔 NAV 多少），
不是建議。5% 單筆上限在這裡只作**參考線**，不進入任何 gate 判定——
真正的硬擋在 `store.record_live_choice`，那裡一個字都沒放寬。

排序也不在這裡做：候選的先後**原樣沿用** `AlphaSignal` 進來的順序
（唯一排序權威是 `query/bottleneck.py::rank_bottlenecks`）。本模組不重排、不加權。

## ⚠ 「沒持有」與「持股讀不到」不得同形（L12／L13）

持股讀不到時**不得**把每一檔的佔比填成 0.0%——那會讓使用者看到「你一檔都沒買」，
而事實是「我沒讀到你買了什麼」。這兩種情況會導向完全相反的行動，所以
`status != available` 時整份回傳降級並帶出 `blockers`，**不逐檔輸出 0**。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

__all__ = ["build_alpha_candidate_exposure", "render_alpha_candidate_exposure"]

#: `build_nav_exposure` 回傳中代表「持股真的讀到了」的狀態。
#: 其餘（`unavailable`／`holdings_unavailable`／upstream 失敗）一律降級。
_AVAILABLE = frozenset({"available", "confirmed", "confirmed_empty"})


def _ticker_of(signal: Any) -> str:
    """從 `AlphaSignal` 或等價 mapping 取 ticker。

    ⚠ 接受 mapping 是為了讓落地的 JSON signal 也能餵進來（`library/private/alpha/`），
    不是為了容忍缺欄位——取不到 ticker 的項目會被列進 `unresolved`，不是靜默丟掉。
    """
    if isinstance(signal, Mapping):
        return str(signal.get("ticker") or "").strip()
    return str(getattr(signal, "ticker", "") or "").strip()


def _company_of(signal: Any) -> str | None:
    value = (signal.get("company_id") if isinstance(signal, Mapping)
             else getattr(signal, "company_id", None))
    text = str(value or "").strip()
    return text or None


def build_alpha_candidate_exposure(
    signals: Sequence[Any] | None,
    nav_exposure: Mapping[str, Any] | None,
    *,
    sleeves: Mapping[str, str] | None = None,
    single_position_nav_cap: float | None = None,
) -> dict[str, Any]:
    """`AlphaSignal[]` × 持股 → 每個候選目前佔 NAV 多少。

    `nav_exposure` 是 `portfolio.exposure.build_nav_exposure()` 的回傳。
    `sleeves` 是 ticker → sleeve 的對照（未列出的標 `None`，**不猜**）。
    `single_position_nav_cap` 只作參考線，**不 gate、不告警、不阻擋任何動作**。

    回傳的 `candidates` **保持傳入順序**——排序權威不在這一層。
    """
    signals = list(signals or [])
    nav = dict(nav_exposure or {})
    status = str(nav.get("status") or "unavailable")

    ordered: list[str] = []
    unresolved: list[int] = []
    company_by_ticker: dict[str, str | None] = {}
    for index, signal in enumerate(signals):
        ticker = _ticker_of(signal)
        if not ticker:
            # 沒有 ticker 的 signal 不可能 join 到持股。列出來，不靜默丟棄（INV-3）。
            unresolved.append(index)
            continue
        if ticker not in company_by_ticker:
            ordered.append(ticker)
            company_by_ticker[ticker] = _company_of(signal)

    base: dict[str, Any] = {
        "status": status,
        "candidates": [],
        "unresolved_signal_indexes": tuple(unresolved),
        "blockers": list(nav.get("blockers") or []),
        # ⚠ 這裡刻意**沒有** target／suggested size 之類的欄位。
        "single_position_nav_cap_reference": single_position_nav_cap,
    }

    if status not in _AVAILABLE:
        # **不逐檔輸出 0.0%。** 「沒持有」與「持股讀不到」導向相反的行動（L12）。
        base["candidate_tickers"] = tuple(ordered)
        failure = nav.get("failure")
        if isinstance(failure, str) and failure:
            base["failure"] = failure
        if not base["blockers"]:
            base["blockers"] = ["holdings_unavailable"]
        return base

    held: dict[str, Mapping[str, Any]] = {}
    for position in (nav.get("positions") or ()):
        if not isinstance(position, Mapping):
            continue
        ticker = str(position.get("ticker") or "").strip()
        if ticker:
            held[ticker.upper()] = position

    sleeve_map = {str(k).upper(): str(v) for k, v in (sleeves or {}).items()}
    candidates: list[dict[str, Any]] = []
    for ticker in ordered:
        position = held.get(ticker.upper())
        pct = _pct_of(position)
        candidates.append({
            "ticker": ticker,
            "company_id": company_by_ticker.get(ticker),
            "held": position is not None,
            # 真的沒持有才是 0.0——這條路徑只在 status 可用時才走得到。
            "nav_pct": pct if position is not None else 0.0,
            "sleeve": sleeve_map.get(ticker.upper()),
            "lots": position.get("lots") if isinstance(position, Mapping) else None,
        })

    base["candidates"] = candidates
    base["held_count"] = sum(1 for c in candidates if c["held"])
    base["unheld_count"] = sum(1 for c in candidates if not c["held"])
    base["candidate_nav_pct_total"] = round(
        sum(float(c["nav_pct"] or 0.0) for c in candidates), 6)
    return base


def _pct_of(position: Mapping[str, Any] | None) -> float:
    if not isinstance(position, Mapping):
        return 0.0
    for key in ("nav_pct", "pct", "weight"):
        raw = position.get(key)
        try:
            value = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        return value
    return 0.0


def render_alpha_candidate_exposure(view: Mapping[str, Any] | None) -> list[str]:
    """人類可讀的幾行。**不出現任何建議尺寸或動作詞。**"""
    view = dict(view or {})
    status = str(view.get("status") or "unavailable")
    if status not in _AVAILABLE:
        blockers = "／".join(str(b) for b in (view.get("blockers") or ())) or status
        tickers = ", ".join(view.get("candidate_tickers") or ()) or "（無候選）"
        # ⚠ 這一行的措辭很重要：它必須讓人看出「讀不到」而不是「沒買」。
        return [f"⚠ 持股讀不到（{blockers}），因此**無法**判斷這些候選目前的佔比："
                f"{tickers}"]

    candidates = list(view.get("candidates") or ())
    if not candidates:
        return ["目前沒有 alpha 候選。"]
    cap = view.get("single_position_nav_cap_reference")
    lines = [
        f"alpha 候選 {len(candidates)} 檔｜已持有 {view.get('held_count', 0)}｜"
        f"未持有 {view.get('unheld_count', 0)}｜合計佔 NAV "
        f"{float(view.get('candidate_nav_pct_total') or 0.0):.2%}"
    ]
    for item in candidates:
        sleeve = item.get("sleeve") or "未分組"
        if item.get("held"):
            lines.append(f"  {item['ticker']:<10} {float(item['nav_pct']):.2%}｜{sleeve}")
        else:
            lines.append(f"  {item['ticker']:<10} 未持有｜{sleeve}")
    if cap:
        lines.append(
            f"（單筆 NAV 上限 {float(cap):.0%} 是參考線，不在這裡 gate；"
            "真正的硬擋在記錄 live choice 時）")
    unresolved = view.get("unresolved_signal_indexes") or ()
    if unresolved:
        lines.append(f"⚠ {len(unresolved)} 個 signal 沒有 ticker，無法對照持股")
    return lines
