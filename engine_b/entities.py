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
from dataclasses import dataclass
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

    return {base: ids[0] for base, ids in base_ticker_candidates(registry).items() if len(ids) == 1}


def base_ticker_candidates(registry) -> dict[str, tuple[str, ...]]:
    """交易所後綴去掉後的 ticker → **全部**對應的 company_id（排序、去重）。

    `_base_ticker_index` 只取唯一的那些；這一份把「多於一家」也留著，讓呼叫端能**列出候選**
    而不是安靜丟掉（INV-3）——歧義本身是一筆要人看的資訊，不是「查不到」。
    registry 沒有 `companies`（測試替身）時回空表：只剩嚴格比對，不猜。
    """

    counts: dict[str, set[str]] = {}
    for company in getattr(registry, "companies", ()) or ():
        ticker = str(getattr(company, "research_ticker", "") or "").upper()
        if not ticker or "." not in ticker:
            continue
        base = ticker.split(".", 1)[0]
        if base and base != ticker:
            counts.setdefault(base, set()).add(company.company_id)
    return {base: tuple(sorted(ids)) for base, ids in counts.items()}


@dataclass(frozen=True)
class TickerResolution:
    """一個 lead 裡的 ticker 字串解析成什麼。**只用於 lead 關聯與走圖問句，不用於資本歸屬。**

    `via`：`exact`（registry 嚴格比對，含 alias）｜`base`（去後綴後唯一對應）｜
    `ambiguous`（去後綴後對到多家——`company_id` 為 None，`candidates` 列出全部，不猜）｜`none`。
    """

    ticker: str
    company_id: str | None
    via: str
    candidates: tuple[str, ...] = ()


def resolve_lead_ticker(ticker: str, registry, *,
                        base_candidates: dict[str, tuple[str, ...]] | None = None) -> TickerResolution:
    """lead 關聯的 ticker 解析：先嚴格（`company_id_for_ticker`），再去後綴唯一對應。

    這是 `resolve_company_ids` 與走圖第 5 型（`query/graph_walk.py`）共用的**同一條規則**
    （Phase 3 Step 3.1b）：原本走圖另用嚴格查詢重算，把 `$SIVE`／`$SOI` 報成「registry 解析不到」，
    而同一則 lead 的 `company_ids` 早已由這裡解析出 Sivers／Soitec。
    ⚠ `registry.company_id_for_ticker` 本身**不放寬**（資本歸屬路徑，見本檔檔頭與 `_base_ticker_index`）。
    """

    raw = str(ticker).upper()
    exact = registry.company_id_for_ticker(raw)
    if exact:
        return TickerResolution(raw, exact, "exact")
    bases = base_ticker_candidates(registry) if base_candidates is None else base_candidates
    ids = bases.get(raw, ())
    if len(ids) == 1:
        return TickerResolution(raw, ids[0], "base")
    if len(ids) > 1:
        return TickerResolution(raw, None, "ambiguous", ids)
    return TickerResolution(raw, None, "none")


def resolve_company_ids(tickers: Iterable[str]) -> tuple[str, ...]:
    """把 ticker 反查成已登記的 company_id；查不到的直接略過（歧義的也不收——不猜）。"""

    try:
        from identity.registry import get_registry

        registry = get_registry()
    except Exception:
        return ()
    try:
        bases = base_ticker_candidates(registry)
    except Exception:
        bases = {}
    seen: dict[str, None] = {}
    for ticker in tickers:
        company_id = resolve_lead_ticker(ticker, registry, base_candidates=bases).company_id
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


#: 不帶 `$` 的代號：三個字元以上、大寫開頭的英數字（可帶 `.TW` 類後綴）；底線算分隔（舊停放常寫成 `no_retry_unless_POET_…`）。
_PLAIN_TICKER_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{2,5}(?:\.[A-Z]{1,3})?)(?![A-Za-z0-9])")


def lead_subject(lead: dict) -> tuple[str, ...]:
    """這則 lead 是**誰的**事：來源宣告的發文公司（`company_id`，harvest 登記當下寫的）；沒有宣告時，
    實體裡**恰好一家**已登記公司就取那一家（單一 cashtag 的推文）；兩家以上不猜（INV-1）。

    用途：停放的觸發條件常不寫主詞（「後續 10-Q 或 8-K 揭露實際出售股數」「同標的後續出現具名客戶」）——
    主詞就是這份文件的發文公司。
    """

    declared = lead.get("company_id")
    if isinstance(declared, str) and declared.startswith("co:"):
        return (declared,)
    companies = sorted(e for e in lead_entities(lead) if str(e).startswith("co:"))
    return (companies[0],) if len(companies) == 1 else ()


def trigger_entities(text: str | None, registry=None) -> tuple[str, ...]:
    """追源等待的觸發條件（`trace_next_trigger`）**具名**到的公司——停放時 watch 等的標的（failure log #1）。

    回傳 `co:*`（名冊名字寫法逐字出現、cashtag 解析得到、或不帶 `$` 的已登記代號**嚴格**相符）＋ 逐字 cashtag
    （未登記的也留，仍可對 lead）。名字比對只走 `query.bottleneck.quote_names_company`（唯一 owner；名冊宣告的寫法、
    整詞、兩家共用的寫法不算）——不是模糊比對、不呼叫 LLM。不帶 `$` 的代號只認 `company_id_for_ticker` 嚴格相符、
    三個字元以上的大寫字串（「AAOI 第三季 10-Q」）；去後綴的猜法不用在這裡——「SOI 晶圓」不是 Soitec。

    為什麼不用 lead 自己的實體：lead 是一則推文時，它的實體是推文裡**所有** cashtag（2026-10-04 一則停放等 27 家），
    而觸發條件寫的是「AXT 下一份 8-K」——等的是 AXT。2026-10-04～07 被排回的 11 次裡 9 次觸發跟原研究無關，
    多半就是這一格（另一半是預設等「任何提及」，見 `leads.advance`）。
    """

    raw = str(text or "")
    if not raw.strip():
        return ()
    try:
        from identity.registry import get_registry

        registry = registry if registry is not None else get_registry()
    except Exception:
        registry = None
    cashtags = extract_cashtags(raw)
    found: dict[str, None] = {token: None for token in cashtags}
    if registry is None:
        return tuple(sorted(found))
    from query.bottleneck import quote_names_company, shared_name_forms

    try:
        bases = base_ticker_candidates(registry)
    except Exception:
        bases = {}
    for token in cashtags:
        company_id = resolve_lead_ticker(token, registry, base_candidates=bases).company_id
        if company_id:
            found.setdefault(company_id, None)
    for token in _PLAIN_TICKER_RE.findall(raw):
        company_id = registry.company_id_for_ticker(token)
        if company_id:
            found.setdefault(company_id, None)
    shared = shared_name_forms(registry)
    for company in registry.companies:
        if quote_names_company(raw, company, shared=shared):
            found.setdefault(company.company_id, None)
    return tuple(sorted(found))


#: 人打字串裡的交易所前綴 → 研究代號後綴（2026-10-08，ROADMAP「名冊候選分層與批次登記」A①；failure log #45）。
#: 字彙只收資料撞到的寫法（10-08 的 32 個人打字串）；美股交易所沒有後綴。
_EXCHANGE_SUFFIX: dict[str, str] = {
    "NYSE": "", "NASDAQ": "", "NYSE AMERICAN": "", "AMEX": "",
    "TWSE": ".TW", "TPEX": ".TWO", "TSE": ".T", "TYO": ".T",
    "SZSE": ".SZ", "SSE": ".SS", "HKEX": ".HK", "KRX": ".KS", "KOSDAQ": ".KQ",
}
_PREFIXED_TICKER_RE = re.compile(
    r"\b(NYSE AMERICAN|NYSE|NASDAQ|AMEX|TWSE|TPEX|TSE|TYO|SZSE|SSE|HKEX|KRX|KOSDAQ)\s*:?\s*([A-Z]{1,5}|\d{4,6})\b",
    re.IGNORECASE)
_SUFFIXED_TICKER_RE = re.compile(
    r"(?<![A-Za-z0-9])((?:\d{4,6}|[A-Z]{1,6})\.(?:TWO|TW|T|KS|KQ|SZ|SS|HK|DE|PA|L|ST|AX|V|TO|SW|AS))(?![A-Za-z0-9])")
_PAREN_US_TICKER_RE = re.compile(r"\(([A-Z]{1,5})\)")


def manual_name_tickers(raw: str | None) -> tuple[str, ...]:
    """人打的公司字串裡**寫出來的**代號（依出現順序、去重）：`(TWSE: 3711)`→`3711.TW`、`(TPEx: 4979)`→`4979.TWO`、
    `(NYSE: FN)`→`FN`、`(3363.TW)`、`AIXA.DE`、`(AMZN)`。只轉寫法、不猜市場——字串沒寫交易所也沒寫後綴的數字代號不收。"""
    text = str(raw or "")
    found: dict[str, None] = {}
    for exchange, code in _PREFIXED_TICKER_RE.findall(text):
        suffix = _EXCHANGE_SUFFIX[" ".join(exchange.upper().split())]
        found.setdefault(f"{code.upper()}{suffix}", None)
    for ticker in _SUFFIXED_TICKER_RE.findall(text):
        found.setdefault(ticker.upper(), None)
    for ticker in _PAREN_US_TICKER_RE.findall(text):
        found.setdefault(ticker, None)
    return tuple(found)


def resolve_manual_name(raw: str | None, registry) -> tuple[str | None, tuple[str, ...]]:
    """人打的「未登記」字串 → (名冊裡的 co:*，字串寫出的代號)。三條路都是既有的確定性比對（不新造、不模糊）：
    寫出的代號先嚴格、再去後綴唯一對應（`3363.TW` 寫錯後綴也對得到名冊的 `3363.TWO`）；再用名冊名字（`trigger_entities`）。
    對到兩家以上回 None（不猜，INV-1）。事發：10-08 的 32 個人打字串裡 11 個其實已登記，只是寫法對不上（failure log #45）。"""
    tickers = manual_name_tickers(raw)
    try:
        bases = base_ticker_candidates(registry)
    except Exception:
        bases = {}
    by_ticker: set[str] = set()
    for ticker in tickers:
        hit = registry.company_id_for_ticker(ticker)
        if not hit:
            base = ticker.split(".", 1)[0]
            candidates = bases.get(base, ())
            hit = candidates[0] if len(candidates) == 1 else None
        if hit:
            by_ticker.add(hit)
    # 寫出的代號比名字具體：「Samsung Electro-Mechanics (009150.KS)」的名字也對得到三星電子，代號只對得到三星電機
    ids = by_ticker or {e for e in trigger_entities(raw, registry) if e.startswith("co:")}
    return (next(iter(ids)) if len(ids) == 1 else None), tickers


def lead_entities(lead: dict) -> set[str]:
    """取一筆 lead 已存的實體集合；未擷取過的即時由文字推導。

    ⚠ 2026-09-24（Phase 1 Step 1.4；C2）：另併入 lead 自己的 `company_id`（來源宣告：這份文件是誰發的）。
    `entities` 會被 `register` 的內容補強與 `backfill_entities(rescan=True)` 只從文字重算並覆寫，所以
    宣告的公司不住那一欄，而是在這裡——**所有 kind 共用的 T0 入口**——併入。這讓 Sivers 的 MFN 公告
    （全名對不上 cashtag 抽取）第一次叫得醒任何 watch；對實體含 Sivers／IQE 的非語意型 watch 同樣是
    宣告過的改善（它們原本同樣叫不醒），不是意外。
    """

    stored = lead.get("entities")
    if isinstance(stored, dict):
        out = set(stored.get("tickers") or ()) | set(stored.get("company_ids") or ())
    else:
        derived = extract_entities(
            title=lead.get("title"),
            raw_text=lead.get("raw_text"),
            source=lead.get("source"),
        )
        out = set(derived["tickers"]) | set(derived["company_ids"])
    declared = lead.get("company_id")
    if isinstance(declared, str) and declared.startswith("co:"):
        out.add(declared)
    return out


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


def backfill_entities(store: dict, *, rescan: bool = False) -> int:
    """替既有 lead 補上實體標記；回傳**實際改變**的筆數。

    ``rescan=False``（預設）只處理從未算過 entities 的 lead——原始行為。

    ``rescan=True`` 重算全部。需要它的原因：entities 是 harvest 當時算的衍生值，
    而 ticker→company_id 的解析依賴 registry。2026-08-20 一次登記 10 家公司後
    （含 Tesla、CCXI、SK Hynix 與 SIVEF／SKHY 這類 alias），舊 lead 仍全部對不上，
    因為上面那個 skip 條件讓它們永遠不重算——於是新登記的公司對 pq1 排序、
    `related` 查詢與瓶頸比對通通不存在。工具存在但只做一半（L13）。

    重算是安全的：entities 純粹由 title／raw_text／source 導出，不含人工判斷；
    輸入沒變、registry 沒變時結果相同。只有真的改變才計入回傳值，讓「跑完顯示 0」
    成為「確實沒有東西可更新」的可信訊號，而不是「跳過了所有東西」。
    """

    updated = 0
    for lead in (store.get("leads") or {}).values():
        if not rescan and isinstance(lead.get("entities"), dict):
            continue
        computed = extract_entities(
            title=lead.get("title"),
            raw_text=lead.get("raw_text"),
            source=lead.get("source"),
        )
        if lead.get("entities") == computed:
            continue
        lead["entities"] = computed
        updated += 1
    return updated
