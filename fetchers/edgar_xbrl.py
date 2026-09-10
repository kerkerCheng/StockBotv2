"""SEC XBRL companyfacts → `fiscal_year_results` 的**基期兩個數**（P7-a，2026-09-10）。

## 這支存在的理由

2026-09-10 實測：73 檔 materialize 過的標的裡，**68 檔的 blocker 完全同形**——
`headline=upstream_unavailable、fundamental/why/research=not_yet_recorded`，零例外。
`headline` 那一格的根因只有一個：Engine C 沒有該檔的 `fiscal_year_results` 觀測，
於是內部 EPS 缺席、fair value 缺席。也就是說 68 檔不是 68 個研究題目，是同一題乘 68。

而 causal bridge（`alpha/fundamental/bridge.py`）真正需要基期提供的**只有兩個數**：

| 誰提供 | 什麼 |
|---|---|
| **本模組（機械）** | `revenue`、`gaap.operating_income`（＋幣別、年度、申報日） |
| session 判斷（不在本模組） | revenue_growth、operating_margin_delta、interest_and_other_net、tax_rate、nci_attribution、diluted_shares |

所以這支拿掉的是每檔最花 token 的那一格（讀一份 10-K 定位兩個數字），**不是判斷**。
判斷段一格都沒少。

## 為什麼這仍然算 `mechanical`（不需 pq2）

判準是 `AGENTS.md`「這筆資料今天重新取一次拿得回來嗎」：值是結構化數字、指得出一手來源的
確切位置、任何人重讀都得到同一個數。XBRL fact 三者都滿足——`accn` 是不可變的 accession、
`tag` 是逐字的 XBRL 標籤、`end` 是會計期間。source_ref 會把三者都寫進去，任何人可以拿它
重跑一次得到同一個數。

## ⚠ 四條收緊，缺一這支就變成後門（L15：放行與收緊必須同時發生）

1. **tag 白名單，且歧異就拒絕。** 「哪個 tag 是 revenue」本身帶判讀成分——所以候選寫死在
   `REVENUE_TAGS`／`OPERATING_INCOME_TAGS`，白名單外一律不看；若兩個白名單 tag 對**同一期間**
   給出不同的數，**留 null 並列進報告**，不挑一個看起來對的（L11-5：「我找不到」與「它不存在」
   是兩個 claim；這裡是第三種——「我找到兩個」也不是「答案是其中一個」）。
2. **`source_filed_at` 永遠是該 accession 的 `filed` 日期，永遠不是今天。**
   `AGENTS.md` 的反向禁令：不得用 ingest／retrieval 日期冒充 published_at，否則回測會在每個
   歷史時點看到全部證據（INV-6）。
3. **只收年報期間。** `form` 必須以 `10-K` 開頭且 `start→end` 落在 300–400 天——否則一季的
   數字會被當成一年的基期，而那個錯誤靜默且昂貴。
4. **只收單一幣別單位。** `units` 有多於一種計價單位時拒絕，不做換算（報價單位 ≠ 結算幣別，
   `AGENTS.md`；差 100 倍那次的同一形狀）。

## 這支不做的事

不寫任何東西（純讀，回 payload 給呼叫端）、不碰非美股（沒有 CIK 就誠實回 reason）、
不推估任何缺的欄位、不填 0。缺就是缺。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

#: **年報**表單。20-F 是外國發行人的年報，與 10-K 同位階——2026-09-10 實測：只放行 10-K 時
#: TSM／GFS／TSEM／HIMX／POET／NBIS 六檔全被判成「沒有年度事實」，而它們各有 2,500–8,700 筆
#: 20-F fact。那不是「它不存在」，是「我沒去找」（L11-5）。6-K／10-Q 刻意不收（季度）。
ANNUAL_FORM_PREFIXES: tuple[str, ...] = ("10-K", "20-F")

#: 營收候選 tag，**依序**嘗試。順序是「新準則優先」——ASC 606 之後 `RevenueFromContractWith…`
#: 是主要標籤，`Revenues` 是舊案與少數採用者，`SalesRevenueNet` 是 2018 前的遺留。
REVENUE_TAGS: tuple[str, ...] = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)

#: 營業利益只有一個標準 tag。刻意不加 `OperatingIncomeLossBeforeX` 之類的變體——
#: 那些的定義各家不同，屬判讀不屬機械。
OPERATING_INCOME_TAGS: tuple[str, ...] = ("OperatingIncomeLoss",)

#: IFRS 發行人（TSM／GFS／HIMX…）的對應白名單。**刻意只放損益表本身的那一行**：
#: `Revenue` 是 IFRS 損益表的營收行；`RevenueFromContractsWithCustomers` 常常是附註的
#: 分解小計，兩者不必然相等——把它一起放進白名單，歧異守則就會把整批合法的檔擋掉，
#: 那就是 L15 記過的「gate 攔錯東西」。營業利益同理只收 `ProfitLossFromOperatingActivities`。
IFRS_REVENUE_TAGS: tuple[str, ...] = ("Revenue",)
IFRS_OPERATING_INCOME_TAGS: tuple[str, ...] = ("ProfitLossFromOperatingActivities",)

#: namespace → (營收白名單, 營業利益白名單)。**依序**嘗試：先 us-gaap 再 ifrs-full。
#: 同時有兩個 namespace 的公司（HIMX／POET 實測）以先命中的為準，並把 namespace 記進 provenance。
TAG_NAMESPACES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("us-gaap", REVENUE_TAGS, OPERATING_INCOME_TAGS),
    ("ifrs-full", IFRS_REVENUE_TAGS, IFRS_OPERATING_INCOME_TAGS),
)

#: 年報期間的容許長度（天）。52/53 週制（LITE 的 FY 到 6/27）也落在裡面。
_ANNUAL_MIN_DAYS, _ANNUAL_MAX_DAYS = 300, 400

#: 基期會計年度距今超過這麼多天就**拒寫**（18 個月）。
#: 事發（2026-09-10 實測）：TSM 在 companyfacts 的最新年度只到 FY2024（filed 2025-04-17，
#: 距今 618 天），而 FY2025 在世界上早就存在。照寫會得到一個**看起來完全正常**的基期，
#: 然後整條 forward view 從一個過期的年份長出來——沒有任何東西會變紅。
#: 合法案例的上界很寬鬆：FY 剛結束還沒申報的公司最多也只落在約 375 天。
_MAX_BASELINE_AGE_DAYS = 550


class XbrlUnavailable(RuntimeError):
    """companyfacts 取不到（網路、404、限流）。**呼叫端不得把它讀成「這家沒有財報」。**"""


@dataclass(frozen=True, slots=True)
class XbrlFact:
    """一個 XBRL 年度事實。每個欄位都來自 companyfacts 原文，沒有一個是推導出來的。"""

    tag: str
    namespace: str
    value: float
    unit: str
    start: date
    end: date
    accession: str
    filed: date
    form: str
    fiscal_year: int | None

    @property
    def citation(self) -> str:
        return (f"SEC XBRL companyfacts {self.namespace}:{self.tag} "
                f"[{self.start.isoformat()}→{self.end.isoformat()}] "
                f"accession {self.accession}（{self.form}, filed {self.filed.isoformat()}）")


def _headers() -> dict[str, str]:
    # SEC 要求 User-Agent 帶可聯絡的來源；沿用 fetchers/edgar.py 的同一個環境變數。
    agent = os.environ.get("SEC_USER_AGENT") or os.environ.get(
        "EDGAR_USER_AGENT", "StockBotv2 research (contact via repo owner)")
    return {"User-Agent": agent, "Accept-Encoding": "identity", "Host": "data.sec.gov"}


def fetch_companyfacts(cik: str | int, *, timeout: float = 30.0, retries: int = 2) -> dict[str, Any]:
    """抓一家公司的全部 XBRL facts。取不到就 raise——**不回空 dict**（空 dict 會被下游讀成「沒有財報」）。"""
    url = COMPANYFACTS_URL.format(cik=int(cik))
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise XbrlUnavailable(f"CIK {cik} 在 companyfacts 沒有資料（404）") from exc
            last = exc
        except Exception as exc:  # noqa: BLE001
            last = exc
        if attempt < retries:
            time.sleep(1.0 + attempt)   # SEC 限流 10 req/s；批次呼叫端另有間隔
    raise XbrlUnavailable(f"companyfacts 取不到（CIK {cik}）：{type(last).__name__}: {last}")


def _as_date(text: Any) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (TypeError, ValueError):
        return None


def annual_facts(facts: Mapping[str, Any], tag: str, *, namespace: str = "us-gaap") -> list[XbrlFact]:
    """某個 tag 的全部**年報年度**事實。非年報表單、非年度長度、無 accession 的一律不收。"""
    node = ((facts.get("facts") or {}).get(namespace) or {}).get(tag)
    if not node:
        return []
    units: Mapping[str, Any] = node.get("units") or {}
    out: list[XbrlFact] = []
    for unit, entries in units.items():
        for entry in entries or []:
            form = str(entry.get("form") or "")
            if not form.startswith(ANNUAL_FORM_PREFIXES):
                continue
            start, end, filed = (_as_date(entry.get("start")), _as_date(entry.get("end")),
                                 _as_date(entry.get("filed")))
            accession = str(entry.get("accn") or "")
            value = entry.get("val")
            if not (start and end and filed and accession) or not isinstance(value, (int, float)):
                continue
            if not (_ANNUAL_MIN_DAYS <= (end - start).days <= _ANNUAL_MAX_DAYS):
                continue
            fy = entry.get("fy")
            out.append(XbrlFact(tag=tag, namespace=namespace, value=float(value),
                                unit=str(unit), start=start, end=end,
                                accession=accession, filed=filed, form=form,
                                fiscal_year=int(fy) if isinstance(fy, int) else None))
    return out


def _latest_period_end(candidates: Iterable[XbrlFact]) -> date | None:
    ends = [f.end for f in candidates]
    return max(ends) if ends else None


def latest_annual_period(facts: Mapping[str, Any], namespace: str,
                         revenue_tags: Sequence[str]) -> date | None:
    """某個 namespace 底下最新的年報年度。**不看值、不看單位**——只回答「這裡最新報到哪一年」。"""
    return _latest_period_end([f for tag in revenue_tags
                               for f in annual_facts(facts, tag, namespace=namespace)])


def pick_for_period(facts: Mapping[str, Any], tags: Sequence[str], period_end: date,
                    *, namespace: str = "us-gaap") -> tuple[XbrlFact | None, str | None]:
    """取 `period_end` 這一年的值。**白名單內有兩個 tag 給出不同的數就拒絕**（回 reason）。

    同一個 tag 對同一期間有多筆（原申報 + 後續年報的比較欄）時取 `filed` 最新的那筆——
    那是重編後的現行數字，而它的 `filed` 日期會誠實記在 source_ref 裡。
    """
    per_tag: list[list[XbrlFact]] = []
    for tag in tags:
        same = [f for f in annual_facts(facts, tag, namespace=namespace) if f.end == period_end]
        if same:
            per_tag.append(same)
    if not per_tag:
        return None, f"白名單 tag（{'、'.join(tags)}）都沒有 {period_end.isoformat()} 的年報數字"

    # ⚠ **單位檢查必須在「每個 tag 收斂成一筆」之前**。
    # 2026-09-10 測試撞出來：先用 max(filed) 收斂再看單位的話，單一 tag 同期間有兩種幣別時
    # 會被靜默挑掉一個，而這道 guard 從頭到尾不會觸發——一道永遠不亮的煞車比沒有更糟（L14）。
    units = {f.unit for group in per_tag for f in group}
    if len(units) > 1:
        return None, f"同一期間出現多種計價單位 {sorted(units)}——不做換算，拒寫"
    hits = [max(group, key=lambda f: f.filed) for group in per_tag]
    distinct = {round(f.value, 2) for f in hits}
    if len(distinct) > 1:
        detail = "；".join(f"{f.namespace}:{f.tag}={f.value:,.0f}" for f in hits)
        return None, f"白名單 tag 對同一期間給出不同的數（{detail}）——留 null，不挑一個"
    return hits[0], None


def _build_for_namespace(ticker: str, facts: Mapping[str, Any], namespace: str,
                         revenue_tags: Sequence[str], operating_tags: Sequence[str],
                         ) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """在單一 namespace 下組一筆基期。找不到年度事實就回 reason，讓呼叫端試下一個 namespace。"""
    period_end = latest_annual_period(facts, namespace, revenue_tags)
    if period_end is None:
        return None, None, f"{namespace} 沒有任何白名單營收 tag 的年報年度事實"

    # ⚠ **陳舊檢查放在最前面，理由才會指向真正該做的下一步。**
    # 2026-09-10 實測：TSM／UMC 最新年度只到 FY2024，同時又有 TWD＋USD 兩種單位。
    # 幣別 guard 先觸發時，回報的是「多種計價單位」——讀者會去修幣別，修完仍然什麼都拿不到，
    # 因為真正的阻礙是 FY2025 根本不在 companyfacts 裡（L12：一則訊息兩個問題，
    # 而顯示出來的那個把人導向錯的方向）。
    age = (date.today() - period_end).days
    if age > _MAX_BASELINE_AGE_DAYS:
        return None, None, (
            f"{namespace} 最新年度只到 {period_end.isoformat()}（距今 {age} 天，超過 "
            f"{_MAX_BASELINE_AGE_DAYS} 天門檻）——**不寫過期基期**，改由 session 去抓一手年報。"
            "（照寫會得到一個看起來正常、實際上落後一整年的 forward view）")

    revenue, rev_reason = pick_for_period(facts, revenue_tags, period_end, namespace=namespace)
    if revenue is None:
        return None, None, f"營收：{rev_reason}"
    if revenue.value <= 0:
        return None, None, f"營收非正（{revenue.value}）——基期營益率無定義，留給 ROADMAP P6 的 EV/S"

    operating, op_reason = pick_for_period(facts, operating_tags, period_end, namespace=namespace)
    if operating is None:
        return None, None, f"營業利益：{op_reason}"

    payload: dict[str, Any] = {
        "fiscal_year_end": period_end.isoformat(),
        "currency": revenue.unit,
        "revenue": revenue.value,
        "gaap": {"operating_income": operating.value},
        "source_filed_at": max(revenue.filed, operating.filed).isoformat(),
        # ⚠ 這一段讓本筆可被任何人重導：拿這幾個座標重跑一次 companyfacts 必得同一個數。
        # 沒有它，「mechanical」就只是一個宣稱（L15）。
        "xbrl_provenance": {
            "namespace": namespace,
            "revenue": {"tag": f"{revenue.namespace}:{revenue.tag}", "accession": revenue.accession,
                        "form": revenue.form, "filed": revenue.filed.isoformat(),
                        "period": [revenue.start.isoformat(), revenue.end.isoformat()]},
            "operating_income": {"tag": f"{operating.namespace}:{operating.tag}",
                                 "accession": operating.accession, "form": operating.form,
                                 "filed": operating.filed.isoformat(),
                                 "period": [operating.start.isoformat(), operating.end.isoformat()]},
            "whitelist": {"revenue": list(revenue_tags), "operating_income": list(operating_tags)},
        },
        "coverage_note": (
            "本筆只含 causal bridge 需要的兩個基期數（revenue、gaap.operating_income），"
            "由 SEC XBRL companyfacts 機械取得。利息／稅／非控制權益／稀釋股數／non-GAAP 對帳"
            "**刻意未填**——它們在本系統裡是 session 判斷（OperatingAssumption），不是觀測。"
        ),
    }
    source_ref = f"{ticker}：{revenue.citation}；營業利益 {operating.citation}"
    return payload, source_ref, None


def build_fiscal_year_results(ticker: str, facts: Mapping[str, Any]
                              ) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """回 `(payload, source_ref, reason)`。payload 為 None 時 reason 說明為什麼——**永遠不補 0**。

    `TAG_NAMESPACES` 依序試（us-gaap → ifrs-full）。基期年度＝該 namespace 的營收 tag 裡最新的
    那個 `end`；營業利益必須落在**同一個** `end`，否則等於把兩個年度的數字兜在一起算營益率。

    ⚠ **一個 namespace 失敗不是結論**——外國發行人常常兩個 namespace 都有（HIMX／POET 實測），
    所以逐個試完才報告，且 reason 會把每個 namespace 各自的理由都列出來，不只列最後一個。
    """
    # 每個 namespace 各自最新報到哪一年——**先比年度再試組裝**。
    # 事發（2026-09-10 實測）：HIMX 的 `us-gaap` 停在 FY2017（該公司後來改報 IFRS），
    # `ifrs-full` 才是 FY2025。「先成功的那個贏」會拿到一個八年前的基期，
    # 而它長得跟正常的一模一樣——不會有任何東西變紅。
    seen: dict[str, str] = {}
    ordered: list[tuple[date, str, Sequence[str], Sequence[str]]] = []
    for namespace, revenue_tags, operating_tags in TAG_NAMESPACES:
        period = latest_annual_period(facts, namespace, revenue_tags)
        if period is None:
            continue
        seen[namespace] = period.isoformat()
        ordered.append((period, namespace, revenue_tags, operating_tags))
    ordered.sort(key=lambda item: item[0], reverse=True)

    reasons: list[str] = []
    for _period, namespace, revenue_tags, operating_tags in ordered:
        payload, source_ref, reason = _build_for_namespace(
            ticker, facts, namespace, revenue_tags, operating_tags)
        if payload is not None and source_ref is not None:
            if len(seen) > 1:
                payload["xbrl_provenance"]["namespaces_considered"] = dict(seen)
            return payload, source_ref, None
        reasons.append(f"[{namespace}] {reason}")
    if not reasons:
        for namespace, _rt, _ot in TAG_NAMESPACES:
            reasons.append(f"[{namespace}] 沒有任何白名單營收 tag 的年報年度事實")
    return None, None, "；".join(reasons)


__all__ = [
    "ANNUAL_FORM_PREFIXES", "COMPANYFACTS_URL", "OPERATING_INCOME_TAGS", "REVENUE_TAGS", "XbrlFact", "XbrlUnavailable",
    "annual_facts", "build_fiscal_year_results", "fetch_companyfacts",
    "latest_annual_period", "pick_for_period",
]
