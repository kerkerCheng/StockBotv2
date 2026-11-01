"""邊緣判定（Phase 3 Step 3.3，使用者 2026-09-29 定案 #13）：**這一檔算不算倍率候選**——只回答這一件事。

門檻住 `config/alpha_screen.json`（`market_cap_max_usd` **AND** `analyst_count_max`，2026-09-19 由 16 檔實測斷點定）；
本檔**不新增門檻、不調數字**。它不排序、不打分、不給尺寸：候選板用它把「非邊緣」的檔放進「非倍率候選」組
（宣告 `open` 也不算可開），缺市值或覆蓋的：宣告 `open` 的放進「可開但邊緣無法量」組（不靜默放行、不靜默濾掉，
`_absence_policy`），其餘照敘事分組、列上帶標記（2026-10-30：缺的是篩選的輸入，不是敘事的 X）。

純函式。取數（市值正規化：報價單位 → 結算幣別 → USD）在 `alpha/providers/edge.py`，materialize 時做一次；
**資本路徑只讀 artifact，不即時打 FX 或行情**（plan §4.3）。

⚠ 理由碼刻意不沿用 Phase 0 退役的那個 filter 的理由碼（殭屍 grep B 組會攔，`scripts/retired_mechanism_grep.py`）；
這裡的字是 `cap_over_edge`／`coverage_over_edge`——它只回答「算不算倍率候選」，不是 filter。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

#: 三態封閉字彙。
EDGE_STATES: tuple[str, ...] = ("edge", "not_edge", "unmeasurable")
#: 理由碼封閉字彙。
EDGE_REASONS: tuple[str, ...] = ("within_edge", "cap_over_edge", "coverage_over_edge",
                                 "market_cap_unavailable", "coverage_unavailable")
EDGE_LABELS: Mapping[str, str] = {"edge": "邊緣", "not_edge": "非邊緣", "unmeasurable": "邊緣無法量"}

#: 「在門檻上」的帶寬（ROADMAP「邊緣門檻的遲滯與在門檻上計數器」，2026-11-01；failure log #110 的四檔都在這個帶內翻轉：
#: 英維克、THK 13 家 ↔ 12 家，LYC.AX 12 ↔ 13 家，AMKR 97.9 億 ↔ 104.9 億美元）：分析師在上限 ±1 家、市值在上限 ±10%。
#: **只計數、不排序、不改門檻**——門檻值本身仍只住 `config/alpha_screen.json`；這兩個數只決定「印不印在名單上」。
THRESHOLD_BAND_ANALYSTS = 1
THRESHOLD_BAND_CAP_RATIO = 0.10
#: 撤回建議要連續幾次判定都非邊緣（含今天）：2 ＝今天與前一次（輸入日前一天的判定）都判非邊緣。
#: 翻回來（非邊緣 → 邊緣）**不加遲滯**——翻回來就該有敘事（ROADMAP ③）。
NOT_EDGE_CONFIRM_RUNS = 2
#: `on_threshold[]` 的封閉字彙（順序固定：先市值、再分析師）。
ON_THRESHOLD_KEYS: tuple[str, ...] = ("market_cap", "analyst_count")


def on_threshold(*, market_cap_usd: float | None, analyst_count: int | None,
                 thresholds: Mapping[str, Any]) -> list[str]:
    """哪幾個輸入落在門檻帶內（`ON_THRESHOLD_KEYS` 的子集；缺值的輸入不算）。純函式。"""
    cap_max = float(thresholds["market_cap_max_usd"])
    cov_max = int(thresholds["analyst_count_max"])
    out: list[str] = []
    if market_cap_usd is not None and abs(float(market_cap_usd) - cap_max) <= cap_max * THRESHOLD_BAND_CAP_RATIO:
        out.append("market_cap")
    if analyst_count is not None and abs(int(analyst_count) - cov_max) <= THRESHOLD_BAND_ANALYSTS:
        out.append("analyst_count")
    return out


def band_label(thresholds: Mapping[str, Any] | None) -> str | None:
    """帶寬的人話（產生端給字，畫面與心跳照抄——L16）：「分析師 11–13 家或市值 9.0B–11.0B USD」。沒有門檻 → None。"""
    if not thresholds or thresholds.get("market_cap_max_usd") is None or thresholds.get("analyst_count_max") is None:
        return None
    cap_max = float(thresholds["market_cap_max_usd"])
    cov_max = int(thresholds["analyst_count_max"])
    lo, hi = cap_max * (1 - THRESHOLD_BAND_CAP_RATIO), cap_max * (1 + THRESHOLD_BAND_CAP_RATIO)
    return (f"分析師 {cov_max - THRESHOLD_BAND_ANALYSTS}–{cov_max + THRESHOLD_BAND_ANALYSTS} 家"
            f"或市值 {lo / 1e9:.1f}B–{hi / 1e9:.1f}B USD")


def not_edge_confirmed(edge: Mapping[str, Any] | None) -> bool | None:
    """今天判非邊緣時，前一次（`edge["prior"]`，輸入日前一天的判定）也判非邊緣嗎？

    True＝連續兩次非邊緣（撤回建議可以出現）；False＝前一次是邊緣／無法量／沒有更早的判定／沒讀到——都當「待確認」
    （讀不到往不撤回那一邊倒：撤回是使用者的動作、多等一天便宜，INV-3 的「沒讀到」由 `edge_note` 寫明）；
    None＝今天不是非邊緣（這個問題不成立）。"""
    if (edge or {}).get("state") != "not_edge":
        return None
    prior = (edge or {}).get("prior") or {}
    return prior.get("state") == "not_edge"


def replay_retraction_suggestions(states: Sequence[tuple[date, str]], *, confirm_runs: int = NOT_EDGE_CONFIRM_RUNS,
                                  narrative_at_start: bool = True) -> dict[str, Any]:
    """純函式回放（驗收用）：一檔逐日的邊緣判定 → 「撤回建議」與「重寫」各在哪幾天出現。

    規則與候選板同一套：有敘事時**連續 `confirm_runs` 次**判非邊緣 → 當天出現撤回建議（之後當作敘事已撤回）；
    沒有敘事時判邊緣 → 當天重寫（不加遲滯，ROADMAP ③）；無法量中斷非邊緣的連續計數、不撤回也不重寫。
    `confirm_runs=1` 就是遲滯之前的現行規則。回 `runs`（連續段）讓人看得到序列長什麼樣。"""
    ordered = sorted(((d, str(s)) for d, s in states), key=lambda x: x[0])
    narrative = bool(narrative_at_start)
    run_state: str | None = None
    run_len = 0
    suggestions: list[date] = []
    rewrites: list[date] = []
    runs: list[tuple[str, date, date]] = []
    for day, state in ordered:
        if state == run_state:
            run_len += 1
            runs[-1] = (state, runs[-1][1], day)
        else:
            run_state, run_len = state, 1
            runs.append((state, day, day))
        if state == "not_edge" and narrative and run_len >= int(confirm_runs):
            suggestions.append(day)
            narrative = False
        elif state == "edge" and not narrative:
            rewrites.append(day)
            narrative = True
    pending = bool(ordered) and ordered[-1][1] == "not_edge" and narrative and run_len < int(confirm_runs)
    return {"suggestions": suggestions, "rewrites": rewrites, "pending_at_end": pending, "runs": runs,
            "confirm_runs": int(confirm_runs)}


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
            # 在門檻上（2026-11-01）：哪幾個輸入落在上限 ±1 家／±10% 的帶內——只計數、不改判定
            "on_threshold": on_threshold(market_cap_usd=market_cap_usd, analyst_count=analyst_count,
                                         thresholds={"market_cap_max_usd": cap_max, "analyst_count_max": cov_max}),
            "thresholds": {"market_cap_max_usd": cap_max, "analyst_count_max": cov_max}}


__all__ = ["EDGE_LABELS", "EDGE_REASONS", "EDGE_STATES", "NOT_EDGE_CONFIRM_RUNS", "ON_THRESHOLD_KEYS",
           "THRESHOLD_BAND_ANALYSTS", "THRESHOLD_BAND_CAP_RATIO", "band_label", "edge_state", "not_edge_confirmed",
           "on_threshold", "replay_retraction_suggestions"]
