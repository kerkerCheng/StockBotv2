"""從 lead 文字擷取具名標的，作為 lead 之間的確定性關聯鍵。

在此之前，lead 唯一的鍵是正規化 URL hash——同一個 URL 重抓會去重，但「不同 URL、
同一個標的」之間沒有任何連結。結果是 parked lead 與新進 lead 的關聯完全依賴 agent
每個 session 重讀 `trace-backlog` 並靠語意注意到，而且漏掉時是靜默的。

這裡只做確定性擷取，不做語意判斷：

- **Cashtag**（`$AAOI`、`$CCXI`）：X 貼文的既有慣例，逐字出現才算，符合 L6
  反幻覺鐵律（具體型號／公司名必須在原文逐字出現）。
- **已登記 ticker**：透過 `identity.registry` 反查得到 `co:*` company_id 的才登記，
  避免把任意大寫字串當成標的。

刻意**不**做的事：不猜測未登記的 ticker、不從公司名做模糊比對、不呼叫 LLM。
擷取結果只是注意力線索（跟 lead status 一樣），永遠不影響 evidence tier。
"""
from __future__ import annotations

import re
from typing import Iterable

# $TICKER：1-6 個英數字，允許 .TW 這類後綴的點與連字號後綴由 registry 決定。
# 邊界要求前面不是字元，避免誤抓 "US$49M" 這種金額寫法。
_CASHTAG_RE = re.compile(r"(?<![A-Za-z0-9])\$([A-Za-z][A-Za-z0-9.\-]{0,7})\b")


def extract_cashtags(*texts: str | None) -> tuple[str, ...]:
    """擷取文字中的 cashtag，正規化為大寫並去重保序。"""

    seen: dict[str, None] = {}
    for text in texts:
        if not text:
            continue
        for raw in _CASHTAG_RE.findall(str(text)):
            token = raw.upper().rstrip(".-")
            if token:
                seen.setdefault(token, None)
    return tuple(seen)


def _base_ticker_index(registry) -> dict[str, str]:
    """交易所後綴去掉後的 ticker → company_id；只收**唯一**對應。

    同一家公司在三個地方有三個字串：Google Sheet 用 execution symbol
    （`FRA:2DG`）、registry 用 research ticker（`SIVE.ST`）、推文用 base cashtag
    （`$SIVE`）。AGENTS.md 已載明「Sivers 三層 symbol 不可混用」——那是對的，
    **價格**不可混。但「價格不可混用」不等於「不可辨識為同一家公司」，而先前連
    辨識都做不到：2026-08-08 實測一則同時點名 AAOI／SIVE／LITE／AVGO／COHR 的推文，
    company_ids 解析出五家卻**漏掉 Sivers**，因為 cashtag 是 `SIVE`、registry 是
    `SIVE.ST`。

    ⚠ 只用於 **lead 關聯**（排序、related_entity_signal），**不用於資本歸屬**。
    `registry.company_id_for_ticker` 維持嚴格比對——holdings→company 的對應若放寬，
    會把部位歸錯公司。lead 關聯可以寬鬆，資本歸屬必須精確。

    base 有多於一家對應時整個丟棄（fail closed），不猜。

    ⚠ 已知的誤判風險（2026-08-08 掃過全表 53 家，13 家有後綴、無 base 衝突）：
    多數 base 是純數字代碼（`2455`／`005930`／`300308`…），cashtag 幾乎不可能誤指；
    但 **`ENA`（Enablence）與 `SOI`（Soitec）在美股／加密圈另有同名標的**
    （$ENA＝Ethena、$SOI＝Solaris Oilfield）。誤判的後果被上述邊界限制在
    **注意力分配**——最壞是某天 5 個 pq1 額度浪費一個，且 triage 通常會先擋掉
    內容明顯無關的推文；不會把部位歸錯公司。若日後這兩個真的造成雜訊，
    正解是在 registry 明列 alias／deny，而不是放棄整個 base 反查。
    """

    counts: dict[str, set[str]] = {}
    for company in registry.companies:
        ticker = str(getattr(company, "research_ticker", "") or "").upper()
        if not ticker or "." not in ticker:
            continue
        base = ticker.split(".", 1)[0]
        if base and base != ticker:
            counts.setdefault(base, set()).add(company.company_id)
    return {
        base: next(iter(ids)) for base, ids in counts.items() if len(ids) == 1
    }


def resolve_company_ids(tickers: Iterable[str]) -> tuple[str, ...]:
    """把 ticker 反查成已登記的 company_id；查不到的直接略過。"""

    try:
        from identity.registry import get_registry

        registry = get_registry()
    except Exception:
        return ()
    try:
        base_index = _base_ticker_index(registry)
    except Exception:
        base_index = {}
    seen: dict[str, None] = {}
    for ticker in tickers:
        raw = str(ticker).upper()
        company_id = registry.company_id_for_ticker(raw) or base_index.get(raw)
        if company_id:
            seen.setdefault(company_id, None)
    return tuple(seen)


# harvest source 的結構化前綴，例如 "edgar:AXTI"。這是零誤判的擷取來源——
# EDGAR lead 的標題寫「AXTI 8-K filed ...」沒有 cashtag，只靠文字會漏掉。
_SOURCE_TICKER_RE = re.compile(r"^(?:edgar|mops):([A-Za-z0-9.\-]{1,12})$")


def extract_source_ticker(source: str | None) -> str | None:
    """從 `edgar:AXTI` 這類結構化 source 取出 ticker。"""

    if not source:
        return None
    match = _SOURCE_TICKER_RE.match(str(source).strip())
    return match.group(1).upper() if match else None


def extract_entities(
    *,
    title: str | None = None,
    raw_text: str | None = None,
    source: str | None = None,
) -> dict[str, list[str]]:
    """回傳一筆 lead 的確定性實體標記。

    `tickers` 含逐字出現的 cashtag 與結構化 source ticker（未登記者也保留，
    仍可用於 lead 間比對）；`company_ids` 只含能反查到 registry 的，
    可用於跨 Engine A／D 比對。
    """

    tickers = list(extract_cashtags(title, raw_text))
    from_source = extract_source_ticker(source)
    if from_source and from_source not in tickers:
        tickers.insert(0, from_source)
    return {
        "tickers": tickers,
        "company_ids": list(resolve_company_ids(tickers)),
    }


def lead_entities(lead: dict) -> set[str]:
    """取一筆 lead 已存的實體集合；未擷取過的即時由文字推導。"""

    stored = lead.get("entities")
    if isinstance(stored, dict):
        return set(stored.get("tickers") or ()) | set(stored.get("company_ids") or ())
    derived = extract_entities(
        title=lead.get("title"),
        raw_text=lead.get("raw_text"),
        source=lead.get("source"),
    )
    return set(derived["tickers"]) | set(derived["company_ids"])


def related_leads(
    store: dict, lead_id: str, *, statuses: Iterable[str] = ("parked",)
) -> list[dict]:
    """找出與指定 lead 共用具名標的、且處於指定狀態的其他 lead。

    這是確定性比對——共用 cashtag 或 company_id 才算相關，不做語意推論。
    它不會取代 agent 的判斷，但保證「明明提到同一個 ticker 卻沒被看見」不會發生。
    """

    leads = store.get("leads") or {}
    target = leads.get(lead_id)
    if not target:
        raise KeyError(f"未知 lead：{lead_id}")
    wanted = lead_entities(target)
    if not wanted:
        return []
    allowed = set(statuses)
    matches: list[dict] = []
    for other_id, other in leads.items():
        if other_id == lead_id or other.get("status") not in allowed:
            continue
        shared = wanted & lead_entities(other)
        if shared:
            matches.append(
                {
                    "lead_id": other_id,
                    "status": other.get("status"),
                    "shared": sorted(shared),
                    "title": str(other.get("title") or "")[:120],
                    "url": other.get("url"),
                }
            )
    matches.sort(key=lambda m: (-len(m["shared"]), m["lead_id"]))
    return matches


def backfill_entities(store: dict) -> int:
    """替尚未擷取實體的既有 lead 補上標記；回傳更新筆數。"""

    updated = 0
    for lead in (store.get("leads") or {}).values():
        if isinstance(lead.get("entities"), dict):
            continue
        lead["entities"] = extract_entities(
            title=lead.get("title"),
            raw_text=lead.get("raw_text"),
            source=lead.get("source"),
        )
        updated += 1
    return updated
