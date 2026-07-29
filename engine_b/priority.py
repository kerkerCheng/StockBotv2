"""Lead priority 計分：決定貴的 pq1 預算先花在哪幾則（可重算，不凍結）。

priority 是**衍生值**，查詢時計算、不存進 leads.json——這樣它能隨圖狀態
（哪些公司已入圖/入 probe）重新排序（plan R1/KTD1）。成分取自 signal-triage
五要素：tier、矛盾/反證價值、thesis 影響度、新穎性、來源獨立性。

pq1 定義見 CONCEPTS.md「PQ1（研究佇列）」。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

# 權重為 v0 拍腦袋值，可隨真實流量調（plan RISK1）。矛盾/反證最關鍵（可能推翻
# thesis）；thesis 影響次之（閉環：更新既有 probe）；來源獨立性推進 L8 gate。
PRIORITY_WEIGHTS: dict[str, float] = {
    "contradiction": 5.0,
    "thesis_impact": 4.0,
    "independent_source": 3.0,
    "novelty": 2.0,
    # 使用者明確指定的 bounded campaign 是 pq1 排程 authority，但仍不授權 pq2。
    "user_requested": 5.0,
    "campaign_focus": 5.0,
}

_EDGAR_SOURCE = re.compile(r"^edgar:([A-Z0-9.^_-]+)$")
_CASHTAG = re.compile(r"(?<![A-Z0-9_])\$([A-Z][A-Z0-9.]{0,9})\b", re.IGNORECASE)


def lead_ticker(lead: Mapping[str, Any]) -> str | None:
    """從 edgar: source 或標題 cashtag 取第一個 ticker。"""
    m = _EDGAR_SOURCE.match(str(lead.get("source") or ""))
    if m:
        return m.group(1)
    title_match = _CASHTAG.search(str(lead.get("title") or ""))
    return title_match.group(1).upper() if title_match else None


def score_lead(lead: Mapping[str, Any], *, thesis_impact: bool = False) -> float:
    """單則 lead 的 priority 分數；高＝pq1 先處理。"""
    triage = lead.get("triage") or {}
    try:
        tier = int(triage.get("tier"))
    except (TypeError, ValueError):
        tier = 4
    tier = min(4, max(1, tier))
    # tier base：tier1（最強來源）=4 … tier4=1
    score = float(5 - tier)
    flags = triage.get("priority_flags") or {}
    if flags.get("contradiction"):
        score += PRIORITY_WEIGHTS["contradiction"]
    if thesis_impact:
        score += PRIORITY_WEIGHTS["thesis_impact"]
    if flags.get("independent_source"):
        score += PRIORITY_WEIGHTS["independent_source"]
    if flags.get("novelty"):
        score += PRIORITY_WEIGHTS["novelty"]
    if flags.get("user_requested"):
        score += PRIORITY_WEIGHTS["user_requested"]
    if (lead.get("refs") or {}).get("campaign_focus") == "primary":
        score += PRIORITY_WEIGHTS["campaign_focus"]
    return score


def rank_leads(
    leads: Iterable[Mapping[str, Any]],
    *,
    tracked_tickers: frozenset[str] = frozenset(),
) -> list[tuple[float, dict[str, Any]]]:
    """回 [(score, lead)] 依 score 由高到低（tie-break lead_id 穩定）。

    thesis_impact 由 lead 的 ticker 是否在 tracked_tickers 推得——tracked 由
    caller 注入（如已入圖/已入 probe 的公司），保持 priority 模組不硬耦合
    Engine A/D。
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for lead in leads:
        ticker = lead_ticker(lead)
        impact = ticker is not None and ticker.upper() in tracked_tickers
        scored.append((score_lead(lead, thesis_impact=impact), dict(lead)))
    scored.sort(key=lambda item: (-item[0], item[1].get("lead_id", "")))
    return scored
