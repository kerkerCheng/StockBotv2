"""個股頁 schema v1.0 的程式合約（2026-10-08，個股頁 plan `docs/plans/2026-10-05-003-feat-stock-page-schema-proposal.md` S2）。

設計與盤點住 `docs/brainstorms/2026-10-05-stock-page-schema.md`（§5 十三塊、§5.6 十一條規則、§15.4 v1.0 凍結）；這裡把它寫成
**封閉字彙**，經 `.meta.json` 給 APP（`webapp.materialize.write_vocabularies`），app.js 不留第二份（L16）。

三件事：
1. **十三塊 × 元素**：每個元素宣告掛在哪個單位（§5.1）、資料源類別（機械／圖／研究／共識／市場／等待 registry）、
   由 analyst view 的哪幾條 line 承載，以及**沒有的時候印什麼、在哪裡找過**（規則 2、L11-5）。
2. **填得滿表**（`fill_table`）：每次 materialize 逐檔算——元素有值（承載它的 line 有值），或具名缺席：缺席的 kind
   **照抄產生那條 line 的程式自己宣告的**（`datum.absence_kind`；L16），沒有任何 line 承載的元素用合約宣告的預設缺席。
   不存在第三種狀態（驗收：七檔 × 元素有值或具名缺席 100%）。
3. **證據等級對照表**（`EVIDENCE_LEVEL_MAP`）：圖外字彙（層說明、讀法：一手／學理／產業報告／推一步／共識／媒體／沒有，
   SSOT `alpha.layer_note.contracts.EVIDENCE_LEVELS`）↔ 圖上的 `evidence_class`（SSOT `query.bottleneck.EVIDENCE_RANK`）。
   兩套回答不同的問題（圖外：來源是哪一類；圖上：誰的來源、有沒有外部印證），所以對照是「哪幾格對得上、哪幾格圖上沒有」，
   不是把一套換算成另一套。

⚠ 這一層**不放閘、不排序、不給尺寸**：填得滿表只回答「頁上這一格有沒有東西、沒有的話為什麼」。
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any, Mapping, Sequence

from alpha.absence import ABSENCE_KINDS, default_absence_kind

PAGE_SCHEMA_VERSION = "stock-page-schema/1.0"

#: 單位（§5.1）：每塊、每個元素都要宣告掛在哪個單位。
UNITS: Mapping[str, str] = {
    "theme_anchor": "題材錨", "path": "路徑", "layer": "層／轉換", "socket": "插槽", "company": "公司", "event": "事件",
}
#: 資料源類別（§5.2）。
SOURCES: Mapping[str, str] = {
    "mechanical": "機械", "graph": "圖", "research": "研究", "consensus": "共識", "market": "市場",
    "registry": "等待 registry",
}
#: 有值的 line 狀態（`datum.status`）：有東西可印——旗標（review_required／stale）照印，不是缺席。
VALUE_STATUSES = frozenset({"available", "partial", "review_required", "stale"})
#: 合約宣告的預設缺席只收這幾種（「沒有 line 承載」能誠實說的只有這些）。
DECLARABLE_ABSENCES = frozenset({"capability_absent", "not_yet_recorded", "upstream_unavailable", "provider_missing"})


@dataclass(frozen=True)
class PageBlock:
    key: str
    title: str
    question: str
    unit: str
    writer: str


@dataclass(frozen=True)
class PageElement:
    key: str
    block: str
    label: str
    unit: str
    source: str
    #: 承載這個元素的 analyst view line：`<panel>/<line key 的 glob>`；`@<extra 鍵>`＝頁外的輸入（例：層說明連結）。
    lines: tuple[str, ...]
    #: 沒有任何 line 承載時的缺席（`DECLARABLE_ABSENCES`）與「在哪裡找過」（缺席時印，L11-5）。
    absence: str
    looked: str


BLOCKS: tuple[PageBlock, ...] = (
    PageBlock("B0", "頁首與一行狀態", "這是誰、現在在哪", "company", "機械"),
    PageBlock("B1", "押什麼（三句話）", "五題①：押哪一層、要變大的是哪個量、為什麼卡在它", "company", "研究"),
    PageBlock("B2", "需求傳導", "AI 的錢有沒有流到這一層", "path", "機械＋研究"),
    PageBlock("B3", "營收從哪來", "現在和之後的錢從哪來", "company", "機械"),
    PageBlock("B4", "技術鏈", "這一層為什麼難、轉換時會變什麼", "layer", "研究"),
    PageBlock("B5", "事件與影響多大", "這件事該不該改變信心", "event", "機械＋研究"),
    PageBlock("B6", "怎麼被定價", "五題②的脈絡：已定價嗎", "company", "機械＋研究"),
    PageBlock("B7", "押對了夠大嗎", "五題②：翻倍要什麼為真", "company", "研究"),
    PageBlock("B8", "錯了怎麼知道", "五題③：反證、在盯或觸及、下一個裁決日", "company", "研究＋registry"),
    PageBlock("B9", "會不會死", "五題④：錢夠不夠、怕不怕還債、會不會一直增資、會計師有沒有警告", "company", "機械"),
    PageBlock("B10", "是不是新賭注", "五題⑤：和持股共用的需求錨與層", "company", "機械"),
    PageBlock("B11", "接下來看什麼", "哪天要回來看", "company", "機械＋registry"),
    PageBlock("B12", "量 → 錢 → 價", "會長到幾倍、價格要的是什麼（不乘倍數算價格，規則 11）", "company", "機械＋研究"),
)

_S3 = "個股頁 S3（機械資料）尚未做"
_S3_ANCHOR = f"{_S3}：需求錨序列（SEC 四家現金資本支出＋NVIDIA 營收）、同業營收季化"

ELEMENTS: tuple[PageElement, ...] = (
    # B0 頁首與一行狀態
    PageElement("B0.what_it_does", "B0", "它是做什麼的一句", "company", "mechanical", (),
                "capability_absent", f"{_S3}；現在只有研究寫的「在系統哪一格」（B1）"),
    PageElement("B0.candidate_state", "B0", "候選狀態", "company", "research", ("candidate/candidate:state",),
                "not_yet_recorded", "候選板（敘事的候選狀態）"),
    PageElement("B0.revenue_yoy", "B0", "最近營收年增", "company", "mechanical",
                ("three_questions/tq:in_numbers:*:in_numbers_series",), "upstream_unavailable", "Engine C 營收序列（三題③）"),
    PageElement("B0.priced_pctile", "B0", "已定價百分位", "company", "market",
                ("three_questions/tq:priced_in:*:own_history_pctile",), "upstream_unavailable", "Engine C 價格與股數（三題②①）"),
    PageElement("B0.structure_reading", "B0", "結構判讀（坐的層的讀圖）", "layer", "graph",
                ("readings/reading:*",), "not_yet_recorded", "結構讀圖 ledger（坐的層與插槽）"),
    PageElement("B0.will_it_die", "B0", "會不會死（一行）", "company", "mechanical",
                ("three_questions/tq:will_it_die:*",), "upstream_unavailable", "歸零旗標（三題①）"),
    # B1 押什麼
    PageElement("B1.position", "B1", "它做什麼：實體產品、在系統哪一格、占營收多少", "company", "research",
                ("brief/brief:position",), "not_yet_recorded", "v2 敘事的「在系統哪一格」"),
    PageElement("B1.our_bet", "B1", "我們賭什麼：押哪一層、要變大的是哪個量", "layer", "research",
                ("brief/brief:our_bet", "bet/our_bet"), "not_yet_recorded", "v2 敘事的「我們賭什麼」"),
    PageElement("B1.why_stuck", "B1", "為什麼卡在它：量還是換不掉（附證據等級）", "layer", "research",
                ("brief/brief:bottleneck",), "not_yet_recorded", "v2 敘事的「為什麼卡在它」"),
    # B2 需求傳導（§5.4）
    PageElement("B2.anchor_change", "B2", "錨的變化：題材錨序列的季度值與年增", "theme_anchor", "mechanical", (),
                "capability_absent", _S3_ANCHOR),
    PageElement("B2.path_layers", "B2", "路徑上各層：從錨到公司坐的層，每層一條年增", "path", "mechanical", (),
                "capability_absent", f"{_S3_ANCHOR}；結構表的鏈有，層的同業序列沒有"),
    PageElement("B2.capture_ratio", "B2", "吃到多少：公司當季營收 ÷ 當季錨", "company", "mechanical", (),
                "capability_absent", f"{_S3}：吃到多少（換美元）"),
    PageElement("B2.share_now", "B2", "份額（現在）：同階段同業的營收堆疊、覆蓋率必印", "layer", "research", (),
                "capability_absent", f"{_S3}；同階段同業的宣告在層說明（S4）"),
    PageElement("B2.peer_changes", "B2", "同層各家變化：最近一季年增，依名稱排、標階段", "layer", "mechanical", (),
                "capability_absent", f"{_S3}：同業營收季化"),
    PageElement("B2.demand_reading", "B2", "一句讀法：什麼在放量、誰在花錢", "path", "research",
                ("brief/brief:demand",), "not_yet_recorded", "v2 敘事的「什麼在放量、誰在花錢」"),
    # B3 營收從哪來
    PageElement("B3.revenue_mix", "B3", "產品、地區、客戶比例與變化", "company", "mechanical", (),
                "capability_absent", f"{_S3}：台股季報附註地區別抽取；Engine C 既有觀測接進 B3（資料有、頁沒位置）"),
    PageElement("B3.backlog", "B3", "backlog 與長約（金額、期間、預付）", "company", "mechanical", (),
                "capability_absent", f"{_S3}；長約在圖上（供貨邊），頁上還沒位置"),
    PageElement("B3.bet_share", "B3", "押的那一塊占營收多少", "company", "mechanical", (),
                "capability_absent", f"{_S3}；多數公司不拆分部（照實印量不到）"),
    # B4 技術鏈（§5.5）
    PageElement("B4.layer_note", "B4", "坐的層的層說明（物理與變體、各家階段、客戶為什麼選、主張的 watch）", "layer",
                "research", ("@layer_notes",), "not_yet_recorded", "層說明 ledger（S4a）：引用這一頁的層說明"),
    PageElement("B4.diagram", "B4", "示意圖（從終端系統到這一層）", "layer", "research", (),
                "capability_absent", "個股頁 S5（版面與示意圖）尚未做"),
    # B5 事件
    PageElement("B5.catalyst", "B5", "事件：碰到哪一塊營收、多大、何時進營收", "event", "research",
                ("research/catalyst_shape", "research/catalyst_quantitative_link"), "not_yet_recorded",
                "thesis 的催化劑（lifecycle）"),
    PageElement("B5.relative_reaction", "B5", "相對同組的 1／5／20 日反應", "event", "market", (),
                "capability_absent", f"{_S3}：事件相對反應（依主題等權組）"),
    # B6 怎麼被定價
    PageElement("B6.own_history", "B6", "自家三年百分位", "company", "market",
                ("three_questions/tq:priced_in:*:own_history_pctile",), "upstream_unavailable", "三題②①"),
    PageElement("B6.cohort_median", "B6", "組中位（只認正式主題等權組；印組名與檔數）", "company", "market",
                ("three_questions/tq:priced_in:*:cohort_median",), "upstream_unavailable", "三題②②（主題等權組 ledger）"),
    PageElement("B6.relative_return", "B6", "相對組的 30／90 日報酬", "company", "market",
                ("three_questions/tq:priced_in:*:rel_return_*",), "upstream_unavailable", "三題②③"),
    PageElement("B6.consensus", "B6", "EPS 實績與共識、本益比兩個年度", "company", "consensus",
                ("fundamental/consensus_eps_*", "fundamental/forward_pe", "fundamental/trailing_pe"),
                "provider_missing", "Engine C 共識快照"),
    PageElement("B6.what_price_assumes", "B6", "價格已經假設了什麼（一句）", "company", "research",
                ("brief/brief:priced_in",), "not_yet_recorded", "v2 敘事的「已定價嗎」那一格"),
    # B7 押對了夠大嗎
    PageElement("B7.what_must_be_true", "B7", "翻倍要什麼為真（營收、出貨、產能、毛利到多少、何時）", "company", "research",
                ("brief/brief:what_must_be_true", "bet/what_must_be_true"), "not_yet_recorded", "v2 敘事"),
    PageElement("B7.rides", "B7", "押在哪一種單位上（層或插槽）", "company", "research", ("bet/rides",),
                "not_yet_recorded", "v2 敘事的 rides"),
    # B8 錯了怎麼知道
    PageElement("B8.disproof", "B8", "反證逐條、在盯或觸及、下一個裁決日", "company", "registry",
                ("downside/downside:*",), "not_yet_recorded", "敘事與讀圖登記的反證 watch（等待 registry）"),
    # B9 會不會死
    PageElement("B9.cash_runway", "B9", "錢夠不夠", "company", "mechanical", ("wipeout/wipeout_cash_runway",),
                "upstream_unavailable", "歸零旗標：現金跑道"),
    PageElement("B9.debt", "B9", "怕不怕還債", "company", "mechanical", ("wipeout/wipeout_debt",),
                "upstream_unavailable", "歸零旗標：負債"),
    PageElement("B9.dilution", "B9", "會不會一直增資", "company", "mechanical", ("wipeout/wipeout_dilution",),
                "upstream_unavailable", "歸零旗標：稀釋"),
    PageElement("B9.going_concern", "B9", "會計師有沒有警告", "company", "mechanical", ("wipeout/wipeout_going_concern",),
                "upstream_unavailable", "歸零旗標：繼續經營疑慮"),
    # B10 是不是新賭注
    PageElement("B10.shared_with_holdings", "B10", "和持股共用的需求錨與層", "company", "mechanical", (),
                "capability_absent", "首屏「是不是新賭注」的格在 analyst view 首屏五題，這張合約還沒有承載它的 line（S5 版面）"),
    # B11 接下來看什麼
    PageElement("B11.dates", "B11", "法定期限、財報日、watch 到期、重看日", "company", "registry",
                ("research/expiry_watch", "research/catalyst_expiry"), "not_yet_recorded", "thesis lifecycle 的到期與催化劑到期"),
    # B12 量 → 錢 → 價
    PageElement("B12.volume_ladder", "B12", "量：營收階梯（共識 vs 產能撐得起的營收）", "company", "mechanical", (),
                "capability_absent", f"{_S3}：營收階梯"),
    PageElement("B12.money", "B12", "錢：毛利率歷史含週期低點、共識隱含的淨利率", "company", "mechanical",
                ("three_questions/tq:in_numbers:*",), "upstream_unavailable", "三題③（出現在數字裡了嗎）"),
    PageElement("B12.price", "B12", "價：本益比買的是哪一年、參考尺", "company", "market",
                ("three_questions/tq:priced_in:*:own_history_pctile", "three_questions/tq:priced_in:*:cohort_median"),
                "upstream_unavailable", "三題②"),
)


#: 證據等級對照表（§5.2 S2）：圖外字彙 ↔ `evidence_class`。值是「圖上對得上的 evidence_class」；空 tuple＝圖上沒有這一類
#: （共識是時變數字，不入圖——L4；學理、推一步、沒有不是文件來源）。
EVIDENCE_LEVEL_MAP: Mapping[str, Mapping[str, Any]] = {
    "primary": {"label": "一手", "graph": ("externally_corroborated", "counterparty_joint", "self_reported_costly",
                                          "self_reported"),
                "note": "一手在圖上的等級由「誰寫的」決定：客戶或第三方＝外部印證、雙方聯合公告＝雙方聯合、被評公司自己的 filing＝自報·filing、"
                        "自己的新聞稿或簡報＝供應商自報"},
    "industry_report": {"label": "產業報告", "graph": ("externally_corroborated", "media_relay"),
                        "note": "登記的發布者：逐份過了 publisher_lifts、引文具名主詞且不是轉述句＝外部印證；否則媒體轉述"},
    "media": {"label": "媒體", "graph": ("media_relay", "needs_review"),
              "note": "登記的媒體＝媒體轉述；發布者解析不到＝待判定"},
    "theory": {"label": "學理", "graph": (), "note": "綜述或教科書：圖上不收（不是對某條邊的主張）"},
    "inference": {"label": "推一步", "graph": (), "note": "研究的推論：圖上不收，要寫出從哪裡推的"},
    "consensus": {"label": "共識", "graph": (), "note": "時變數字，住 Engine C，不入圖（L4）"},
    "none": {"label": "沒有", "graph": (), "note": "照實寫沒有"},
}


# ---------------------------------------------------------------------------
# 合約自檢（封閉性；測試與 materialize 都跑）
# ---------------------------------------------------------------------------

def check_schema() -> list[str]:
    """合約自己的不變式。空 list＝通過。拿掉任何一個元素的缺席宣告、單位或資料源都會在這裡現形。"""
    from alpha.layer_note.contracts import EVIDENCE_LEVELS
    from query.bottleneck import EVIDENCE_RANK

    problems: list[str] = []
    block_keys = [b.key for b in BLOCKS]
    if len(set(block_keys)) != len(block_keys):
        problems.append("塊的 key 重複")
    for block in BLOCKS:
        if block.unit not in UNITS:
            problems.append(f"{block.key} 的單位 {block.unit!r} 不在 UNITS")
        if not any(e.block == block.key for e in ELEMENTS):
            problems.append(f"{block.key} 沒有任何元素")
    seen: set[str] = set()
    for element in ELEMENTS:
        label = element.key
        if element.key in seen:
            problems.append(f"{label} 重複")
        seen.add(element.key)
        if element.block not in block_keys or not element.key.startswith(element.block + "."):
            problems.append(f"{label} 的塊 {element.block!r} 不對")
        if element.unit not in UNITS:
            problems.append(f"{label} 的單位 {element.unit!r} 不在 UNITS")
        if element.source not in SOURCES:
            problems.append(f"{label} 的資料源 {element.source!r} 不在 SOURCES")
        if element.absence not in ABSENCE_KINDS or element.absence not in DECLARABLE_ABSENCES:
            problems.append(f"{label} 的缺席宣告 {element.absence!r} 不在可宣告的缺席裡")
        if not element.looked.strip():
            problems.append(f"{label} 沒寫「在哪裡找過」（規則 2）")
        if not element.label.strip():
            problems.append(f"{label} 沒寫要看到什麼")
        for spec in element.lines:
            if not (spec.startswith("@") or "/" in spec):
                problems.append(f"{label} 的 line 宣告 {spec!r} 要寫成 <panel>/<key glob> 或 @<extra>")
    if set(EVIDENCE_LEVEL_MAP) != set(EVIDENCE_LEVELS):
        problems.append(f"證據等級對照表的圖外字彙與 EVIDENCE_LEVELS 不一致：{sorted(set(EVIDENCE_LEVEL_MAP) ^ set(EVIDENCE_LEVELS))}")
    covered = {cls for row in EVIDENCE_LEVEL_MAP.values() for cls in row["graph"]}
    if covered != set(EVIDENCE_RANK):
        problems.append(f"證據等級對照表沒有涵蓋全部 evidence_class：{sorted(set(EVIDENCE_RANK) ^ covered)}")
    unknown = covered - set(EVIDENCE_RANK)
    if unknown:
        problems.append(f"對照表寫了不存在的 evidence_class：{sorted(unknown)}")
    return problems


# ---------------------------------------------------------------------------
# 填得滿表（materialize 每次算；純函式）
# ---------------------------------------------------------------------------

def _matching_lines(view: Mapping[str, Any], spec: str) -> list[Mapping[str, Any]]:
    panel_key, _, pattern = spec.partition("/")
    panel = view.get(panel_key) or {}
    return [line for line in panel.get("lines") or () if fnmatchcase(str(line.get("key") or ""), pattern)]


def fill_table(view: Mapping[str, Any], *, extra: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """一檔的填得滿表：每個元素一列，`state` 只有 `value`／`absent` 兩種。

    缺席的 kind：承載它的 line 有、但沒值 → 照抄那條 line 的 `datum.absence_kind`（沒宣告就用 `default_absence_kind(status)`
    查表）；沒有任何 line 承載 → 合約宣告的預設。`extra`：頁外的輸入（`@layer_notes`＝引用這一頁的層說明節點；
    沒給＝這一輪沒讀到 → `upstream_unavailable`，不是「沒有」）。"""
    rows: list[dict[str, Any]] = []
    for element in ELEMENTS:
        row: dict[str, Any] = {"element": element.key, "block": element.block}
        extra_keys = [spec[1:] for spec in element.lines if spec.startswith("@")]
        carried = [line for spec in element.lines if not spec.startswith("@") for line in _matching_lines(view, spec)]
        unread = [key for key in extra_keys if extra is None or key not in extra]
        extra_hit = any(extra[key] for key in extra_keys if extra is not None and key in extra)
        valued = [line for line in carried if str((line.get("datum") or {}).get("status")) in VALUE_STATUSES]
        if valued or extra_hit:
            row.update(state="value", lines=[str(line.get("key")) for line in valued][:8])
        elif carried:
            datum = carried[0].get("datum") or {}
            kind = datum.get("absence_kind") or default_absence_kind(str(datum.get("status") or "missing")) \
                or element.absence
            row.update(state="absent", absence_kind=kind, looked=element.looked,
                       lines=[str(line.get("key")) for line in carried][:8])
        elif unread:
            # 頁外的輸入這一輪沒讀到：不是「沒有」（INV-3）
            row.update(state="absent", absence_kind="upstream_unavailable",
                       looked=f"{element.looked}——這一輪沒讀到（{'、'.join(unread)}）")
        else:
            row.update(state="absent", absence_kind=element.absence, looked=element.looked)
        rows.append(row)
    return rows


def fill_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """一檔的填得滿計數：有值幾格、缺席依 kind 分格（呈現用；不放閘）。"""
    counts: dict[str, int] = {}
    for row in rows:
        if row.get("state") == "absent":
            counts[str(row.get("absence_kind"))] = counts.get(str(row.get("absence_kind")), 0) + 1
    valued = sum(1 for row in rows if row.get("state") == "value")
    return {"elements": len(rows), "value": valued, "absent": len(rows) - valued, "absent_by_kind": counts,
            "unnamed": sum(1 for row in rows if row.get("state") not in ("value", "absent")
                           or (row.get("state") == "absent" and not row.get("absence_kind")))}


def schema_payload() -> dict[str, Any]:
    """`.meta.json` 的 `page_schema`（APP 照抄；app.js 不留第二份）。"""
    return {
        "version": PAGE_SCHEMA_VERSION,
        "units": dict(UNITS),
        "sources": dict(SOURCES),
        "blocks": [{"key": b.key, "title": b.title, "question": b.question, "unit": b.unit, "writer": b.writer}
                   for b in BLOCKS],
        "elements": [{"key": e.key, "block": e.block, "label": e.label, "unit": e.unit, "source": e.source,
                      "absence": e.absence, "looked": e.looked} for e in ELEMENTS],
        "evidence_level_map": {k: {"label": v["label"], "graph": list(v["graph"]), "note": v["note"]}
                               for k, v in EVIDENCE_LEVEL_MAP.items()},
    }


__all__ = ["BLOCKS", "DECLARABLE_ABSENCES", "ELEMENTS", "EVIDENCE_LEVEL_MAP", "PAGE_SCHEMA_VERSION", "PageBlock",
           "PageElement", "SOURCES", "UNITS", "VALUE_STATUSES", "check_schema", "fill_summary", "fill_table",
           "schema_payload"]
