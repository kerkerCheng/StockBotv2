"""歸零旗標的**唯一串接點**：Engine C 取數 → 市值正規化 → `alpha.wipeout` 判色（2026-10-01 Phase 4 Step 4.6a）。

原本候選板（`alpha/providers/candidates.py`）與個股頁（`briefing/alpha_view/sources.py`）各寫一份
`get_wipeout_inputs → wipeout_flags`（closeout §5 #19）——兩份會在第一次改輸入時開始偏離（L16），4.6 的稀釋燈
就要多接一個輸入，所以先合一。

分工照舊：取數在 Engine C（`engine_c.checklist.get_wipeout_inputs`，一個顏色都不判）；市值在研究層的正規化
（只為印「占市值 %」，不參與判色——資料層不往下游引用，所以在這裡接）；判色在 `alpha.wipeout`（純函式）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping


def wipeout_for(ticker: str, *, today: date) -> tuple[Mapping[str, Mapping[str, Any]] | None, str | None]:
    """→ `(四盞燈, None)`，或取不到時 `(None, 理由)`——理由要帶出去，燈滅與燈綠不得同形（L12、INV-3）。"""
    from alpha.wipeout import wipeout_flags
    from engine_c.checklist import get_wipeout_inputs

    raw = get_wipeout_inputs(ticker)
    if raw.get("status") != "ok":
        return None, str(raw.get("reason") or "Engine C 觀測不可用")
    issuance = dict(raw.get("issuance") or {})
    if issuance.get("status") == "ok":
        try:
            from .market_normalization import screen_inputs

            cap = screen_inputs([ticker]).get(ticker) or {}
            issuance.update(market_cap_usd=cap.get("market_cap_usd"), market_cap_absence=cap.get("market_cap_absence"))
        except Exception as exc:  # noqa: BLE001 — 市值只是脈絡：取不到照實寫，不擋燈
            issuance.update(market_cap_usd=None, market_cap_absence=f"市值取數失敗：{type(exc).__name__}")
    flags = wipeout_flags(runway=raw.get("runway"), shares_series=raw.get("shares_series"),
                          going_concern=raw.get("going_concern"), today=today,
                          shares_source=raw.get("shares_source"), issuance=issuance)
    return flags, None


__all__ = ["wipeout_for"]
