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
    # 實際持有的標的優先於「有在追但沒部位」的。tracked_tickers 由 lifecycle ＋
    # 未結案 cohort 導出，不含 Google Sheet 持股——因此在此之前，一檔你真的有
    # 部位、卻還沒建 cohort 的標的在研究排序上等於不存在。權重刻意低於
    # contradiction（反證仍最優先）但高於 novelty。
    "holdings_impact": 4.0,
    # 該 lead 提到的公司是否**位於已知 chokepoint 上**（`query/bottleneck.py` 的
    # rank_bottlenecks 認定的瓶頸邊端點）。2026-08-20 使用者提問「它們應該會因為
    # 瓶頸性排到 pq1 前面？」——實測答案當時是不會：本表原本七項權重全部不含瓶頸性，
    # 於是「AXT 供應 COHR 的 InP」與「某公司財報季總評」在排序上只由 tier 與 flags
    # 區分，而系統整個定位就是找瓶頸。
    # 權重取 3.5：高於 independent_source（3.0）與 novelty（2.0），但低於
    # thesis_impact／holdings_impact（4.0）與 contradiction（5.0）——結構上重要不等於
    # 比「已有部位」或「可能推翻 thesis」更急。同樣套 focus 稀釋，否則提到十幾檔的
    # 總體評論只要碰巧掃到一家瓶頸公司就拿滿分，正是 FOCUS_TICKER_CAP 要防的事。
    "chokepoint_impact": 3.5,
    "independent_source": 3.0,
    "novelty": 2.0,
    # 使用者明確指定的 bounded campaign 是 pq1 排程 authority，但仍不授權 pq2。
    "user_requested": 5.0,
    "campaign_focus": 5.0,
}

# thesis／holdings impact 的**聚焦上限**：命中與否原本是 bool，一則貼文只要提到任一
# 已追蹤 ticker 就拿滿分。於是「提到越多 ticker」＝「越容易同時命中 tracked 與 held」
# ＝分數越高——而提到十幾檔正是「這是總體評論、不是具體供應鏈事件」的特徵，排序等於
# 獎勵了恰好該扣分的東西。2026-08-12 實測：一則提到 12 檔的財報季總評（已兩度被判定
# 無可入圖內容）拿 12 分，把同日 tier-1 的 Lumentum 8-K（6 分）擠出當輪 pq1 預算。
# 因此改為依聚焦度稀釋：命中權重乘上 min(1, FOCUS_TICKER_CAP / 提及檔數)。
# 供應鏈事件通常牽涉 1–3 家（供應商、客戶、材料），故 cap 取 3——3 檔以內不打折，
# 12 檔打到四分之一。這只調整 pq1 注意力排序，不影響 evidence tier 或任何 gate。
FOCUS_TICKER_CAP = 3.0

_EDGAR_SOURCE = re.compile(r"^edgar:([A-Z0-9.^_-]+)$")
_CASHTAG = re.compile(r"(?<![A-Z0-9_])\$([A-Z][A-Z0-9.]{0,9})\b", re.IGNORECASE)


def lead_tickers(lead: Mapping[str, Any]) -> frozenset[str]:
    """這則 lead 提到的**所有** ticker（大寫）。

    先前只取標題第一個 cashtag，於是一則同時點名五家的推文只用第一家判定重要性。
    2026-08-08 實例：「gem after gem in $AAOI earnings for $SIVE + other laser
    player readthrough」——第一個是 $AAOI，但該則的實質重點是使用者實際持有的
    SIVE，且同時提到 LITE／AVGO／COHR／NVDA。而 `engine_b/entities.py` 的抽取
    **早就把五家都解析出來了**：抽取抓到五個，排序只用一個。

    優先用抽取結果（`entities.tickers`）；沒有時退回舊的單一 ticker 推導，
    確保尚未被 entity 抽取處理過的舊 lead 行為不變。
    """

    entities = lead.get("entities") or {}
    tickers = {
        str(item).upper()
        for item in (entities.get("tickers") or [])
        if str(item).strip()
    }
    if tickers:
        return frozenset(tickers)
    single = lead_ticker(lead)
    return frozenset({single.upper()}) if single else frozenset()


def lead_company_ids(lead: Mapping[str, Any]) -> frozenset[str]:
    """這則 lead 解析得到的所有 registry company_id。"""

    entities = lead.get("entities") or {}
    return frozenset(
        str(item) for item in (entities.get("company_ids") or []) if str(item).strip()
    )


def lead_ticker(lead: Mapping[str, Any]) -> str | None:
    """從 edgar: source 或標題 cashtag 取第一個 ticker（保留給既有呼叫端）。"""
    m = _EDGAR_SOURCE.match(str(lead.get("source") or ""))
    if m:
        return m.group(1)
    title_match = _CASHTAG.search(str(lead.get("title") or ""))
    return title_match.group(1).upper() if title_match else None


def focus_factor(mentioned_tickers: int) -> float:
    """提及檔數 → impact 權重的聚焦係數（1.0 表示不打折）。

    只用於 thesis／holdings impact；tier、反證、新穎性等與「提到幾檔」無關的成分不受影響。
    """
    if mentioned_tickers <= 0:
        return 1.0
    return min(1.0, FOCUS_TICKER_CAP / float(mentioned_tickers))


def score_lead(
    lead: Mapping[str, Any],
    *,
    thesis_impact: bool = False,
    holdings_impact: bool = False,
    chokepoint_impact: bool = False,
    mentioned_tickers: int = 0,
) -> float:
    """單則 lead 的 priority 分數；高＝pq1 先處理。

    ``mentioned_tickers`` 是該 lead 提及的具名標的總數，用來稀釋 impact 權重
    （見 FOCUS_TICKER_CAP）。0 表示呼叫端未提供，維持不打折的舊行為。

    ``chokepoint_impact`` 由呼叫端判定該 lead 是否提到位於已知瓶頸上的公司；
    與 tracked/held 一樣採注入而非在此查圖，以保持本模組不依賴 Neo4j。
    """
    triage = lead.get("triage") or {}
    try:
        tier = int(triage.get("tier"))
    except (TypeError, ValueError):
        tier = 4
    tier = min(4, max(1, tier))
    # tier base：tier1（最強來源）=4 … tier4=1
    score = float(5 - tier)
    flags = triage.get("priority_flags") or {}
    focus = focus_factor(mentioned_tickers)
    if flags.get("contradiction"):
        score += PRIORITY_WEIGHTS["contradiction"]
    if thesis_impact:
        score += PRIORITY_WEIGHTS["thesis_impact"] * focus
    if holdings_impact:
        score += PRIORITY_WEIGHTS["holdings_impact"] * focus
    if chokepoint_impact:
        score += PRIORITY_WEIGHTS["chokepoint_impact"] * focus
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
    held_tickers: frozenset[str] = frozenset(),
    held_company_ids: frozenset[str] = frozenset(),
    chokepoint_tickers: frozenset[str] = frozenset(),
    chokepoint_company_ids: frozenset[str] = frozenset(),
) -> list[tuple[float, dict[str, Any]]]:
    """回 [(score, lead)] 依 score 由高到低（tie-break lead_id 穩定）。

    比對用 lead 提到的**所有** ticker，不是第一個——抽取已經把它們都解析出來，
    排序沒有理由只看一個。

    `tracked_tickers`（有在追）與 `held_tickers`／`held_company_ids`（真的有部位）
    分開注入：兩者語意不同，且先前只有前者，導致實際持股在排序上零加權。
    `chokepoint_tickers`／`chokepoint_company_ids` 是位於已知瓶頸上的公司，
    由 caller 從 `query/bottleneck.py` 的排序結果導出；本模組不查圖。

    priority 模組仍不硬耦合 Engine A/C/D——四者都由 caller 注入。
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for lead in leads:
        tickers = lead_tickers(lead)
        company_ids = lead_company_ids(lead)
        impact = bool(tickers & tracked_tickers)
        held = bool(tickers & held_tickers) or bool(company_ids & held_company_ids)
        choke = bool(tickers & chokepoint_tickers) or bool(
            company_ids & chokepoint_company_ids
        )
        scored.append(
            (
                score_lead(
                    lead,
                    thesis_impact=impact,
                    holdings_impact=held,
                    chokepoint_impact=choke,
                    mentioned_tickers=len(tickers),
                ),
                dict(lead),
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1].get("lead_id", "")))
    return scored
