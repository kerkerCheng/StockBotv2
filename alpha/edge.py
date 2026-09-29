"""邊緣判定（Phase 3 Step 3.3，使用者 2026-09-29 定案 #13）：**這一檔算不算倍率候選**——只回答這一件事。

門檻住 `config/alpha_screen.json`（`market_cap_max_usd` **AND** `analyst_count_max`，2026-09-19 由 16 檔實測斷點定）；
本檔**不新增門檻、不調數字**。它不排序、不打分、不給尺寸：候選板用它把「非邊緣」的檔放進「非倍率候選」組
（宣告 `open` 也不算可開），缺市值或覆蓋的放進「邊緣無法量」組（不靜默放行、不靜默濾掉，`_absence_policy`）。

純函式。取數（市值正規化：報價單位 → 結算幣別 → USD）在 `alpha/providers/edge.py`，materialize 時做一次；
**資本路徑只讀 artifact，不即時打 FX 或行情**（plan §4.3）。

⚠ 理由碼刻意不沿用 Phase 0 退役的那個 filter 的理由碼（殭屍 grep B 組會攔，`scripts/retired_mechanism_grep.py`）；
這裡的字是 `cap_over_edge`／`coverage_over_edge`——它只回答「算不算倍率候選」，不是 filter。
"""
from __future__ import annotations

from typing import Any, Mapping

#: 三態封閉字彙。
EDGE_STATES: tuple[str, ...] = ("edge", "not_edge", "unmeasurable")
#: 理由碼封閉字彙。
EDGE_REASONS: tuple[str, ...] = ("within_edge", "cap_over_edge", "coverage_over_edge",
                                 "market_cap_unavailable", "coverage_unavailable")
EDGE_LABELS: Mapping[str, str] = {"edge": "邊緣", "not_edge": "非邊緣", "unmeasurable": "邊緣無法量"}


def edge_state(*, market_cap_usd: float | None, analyst_count: int | None,
               thresholds: Mapping[str, Any], market_cap_absence: str | None = None) -> dict[str, Any]:
    """→ `{state, reasons[], market_cap_usd, analyst_count, thresholds, missing[]}`。

    兩條是 AND：市值 ≤ 上限**且**覆蓋 ≤ 上限才是邊緣（`_why_analyst_12`：TSM 覆蓋只有 13 位而市值 2.25 兆）。
    任一個超過就是非邊緣（兩個理由都列）；兩個都在上限內但缺一個輸入 → 無法量（缺哪一個照列）。
    """
    cap_max = float(thresholds["market_cap_max_usd"])
    cov_max = int(thresholds["analyst_count_max"])
    reasons: list[str] = []
    missing: list[str] = []
    if market_cap_usd is not None and market_cap_usd > cap_max:
        reasons.append("cap_over_edge")
    if analyst_count is not None and analyst_count > cov_max:
        reasons.append("coverage_over_edge")
    if market_cap_usd is None:
        missing.append("market_cap_unavailable")
    if analyst_count is None:
        missing.append("coverage_unavailable")
    if reasons:
        state = "not_edge"
    elif missing:
        state = "unmeasurable"
        reasons = list(missing)
    else:
        state = "edge"
        reasons = ["within_edge"]
    return {"state": state, "label": EDGE_LABELS[state], "reasons": reasons, "missing": missing,
            "market_cap_usd": market_cap_usd, "analyst_count": analyst_count,
            "market_cap_absence": market_cap_absence,
            "thresholds": {"market_cap_max_usd": cap_max, "analyst_count_max": cov_max}}


__all__ = ["EDGE_LABELS", "EDGE_REASONS", "EDGE_STATES", "edge_state"]
