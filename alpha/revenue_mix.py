"""營收從哪來（個股頁 S3d，2026-10-14；B3）——**純函式**。取數住 `alpha/providers/revenue_mix.py`。

把 Engine C 人工觀測（研究從年報、申報表填的）整理成頁面照印的形狀：
- **分部／產品線占比**（`segment_revenue_share`／`product_line_revenue_share`）：頂層數值鍵就是占比（0..1；寫入端已擋超範圍）。
  `_` 開頭的鍵（例 `_amounts_eur_m`、`_note`）與 `total*`（總額）不是占比，照列在 `ignored`、不畫。同一欄位有前一次觀測時，
  每一塊帶前一次的占比（名稱逐字對得上才帶）。兩種切法（分部、產品線）口徑不同，不混在一起（L12）。
- **客戶集中度**、**backlog 與長約**：多數是研究寫的文字（2026-10-14：客戶 38 筆裡 34 筆、backlog 39 筆裡 37 筆）——照抄全文，
  頁面先印第一句；少數是 JSON，組成一句（只挑寫明的欄位，不推算）。
- **台股年報地區別**（S3d 第二段，`engine_c.tw_region_revenue`）：機械抽取的金額，占比＝地區金額÷那份年報自己的合計
  （同一家公司自己的數字相除，不跨公司）。**依什麼分地區照年報原文標**——客戶所在地、營運地點、沒寫，意思不同（L11-1）。
  與人工記的分部占比分開放（`regions` 不混進 `shares`，L12）：一邊有值不讓另一邊的缺席消失。
- **押的那一塊**（`bet_share`）：敘事押的層 × 層代表公司宣告 × 分部占比——對得上才印，對不上照說哪一段沒有。

不排序公司、不打分、不跨公司算比例（一家公司自己的分部依占比由大到小列是呈現，不是名次）。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SHARE_LABELS: Mapping[str, str] = {"segment_revenue_share": "分部", "product_line_revenue_share": "產品線"}
HEADLINE_CHARS = 120
_NOTE_KEYS = ("judgment_note", "disclosure_translation_zh", "why_it_matters", "verbatim_note", "note")
#: 客戶集中度 JSON 裡寫明的合計占比欄位 → 白話（認不得的照原名印，L16）。
PCT_LABELS: Mapping[str, str] = {
    "top_two_combined_pct": "前兩大合計", "top_three_combined_pct": "前三大合計", "top_two_named_pct_2025": "前兩大（具名）合計",
    "top_five_end_customers_pct_net_revenue": "前五大終端客戶合計", "distributor_share_pct_net_revenue": "經銷商占營收",
    "top_ten_pct_wafer_shipment_volume": "前十大占晶圓出貨量", "top_ten_pct_trade_receivables": "前十大占應收帳款",
}


def _is_share(key: str, value: Any) -> bool:
    return (not str(key).startswith(("_", "total")) and isinstance(value, (int, float)) and not isinstance(value, bool)
            and -1.0 <= float(value) <= 1.0)


def share_parts(value: Mapping[str, Any], previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """一次占比觀測 → `{parts: [{name, share, prev_share}], ignored: [鍵], period}`；parts 依占比由大到小（呈現用）。"""
    prev = {str(k): float(v) for k, v in (previous or {}).items() if _is_share(k, v)}
    parts = [{"name": str(k), "share": float(v), "prev_share": prev.get(str(k))}
             for k, v in value.items() if _is_share(k, v)]
    parts.sort(key=lambda p: (-p["share"], p["name"]))
    ignored = sorted(str(k) for k, v in value.items() if not _is_share(k, v) and k != "fiscal_period")
    return {"parts": parts, "ignored": ignored, "period": value.get("fiscal_period")}


def headline(text: str) -> str:
    """研究寫的一段文字 → 頁面先印的第一句（到第一個句號或分號；太長就截）。全文另外照抄。"""
    clean = " ".join(str(text).split())
    cut = clean.find("。")
    if 0 < cut <= HEADLINE_CHARS:
        return clean[:cut + 1]
    if len(clean) <= HEADLINE_CHARS:
        return clean
    # 第一句太長：切在放得下的最後一個分號或逗號（多帶幾家客戶，不只第一家），再不行才硬切
    cut = max(clean.rfind(mark, 0, HEADLINE_CHARS) for mark in ("；", "，"))
    return clean[:cut + 1] + "…" if cut > HEADLINE_CHARS // 3 else clean[:HEADLINE_CHARS] + "…"


def _pct(value: Any) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):g}%"
    return None


def customers_text(value: Any) -> str:
    """客戶集中度：文字照抄；JSON 組成一句——期間、逐家（名稱＋占比）、寫明的合計占比、研究的判讀註記。"""
    if not isinstance(value, Mapping):
        return " ".join(str(value).split())
    bits: list[str] = []
    if value.get("period"):
        bits.append(f"{value['period']}：")
    for item in value.get("customers") or ():
        if not isinstance(item, Mapping):
            continue
        share = next((_pct(v) for k, v in item.items() if str(k).startswith("pct")), None)
        bits.append(f"{item.get('label') or '客戶'} {share or '占比沒寫'}；")
    for key, v in value.items():
        if "pct" in str(key) and not isinstance(v, (list, dict)) and _pct(v):
            bits.append(f"{PCT_LABELS.get(str(key), key)} {_pct(v)}；")
    for key in _NOTE_KEYS:
        if value.get(key):
            bits.append(str(value[key]))
    return " ".join("".join(bits).split()) or "（這筆觀測沒有可印的欄位）"


def backlog_text(value: Any) -> str:
    """backlog 與長約：文字照抄；JSON 組成一句——有沒有在手訂單揭露、長約剩餘承諾、研究的判讀註記。"""
    if not isinstance(value, Mapping):
        return " ".join(str(value).split())
    bits: list[str] = []
    if value.get("period"):
        bits.append(f"{value['period']}：")
    if value.get("has_order_book") is False:
        bits.append("沒有揭露在手訂單（backlog）；")
    if isinstance(value.get("lta_remaining_revenue_commitment_usd"), (int, float)):
        bits.append(f"長約剩餘的營收承諾 {value['lta_remaining_revenue_commitment_usd']:,.0f} 美元；")
    for key in _NOTE_KEYS:
        if value.get(key):
            bits.append(str(value[key]))
    return " ".join("".join(bits).split()) or "（這筆觀測沒有可印的欄位）"


def share_series(points: Sequence[Mapping[str, Any]], *, keep: int = 4) -> list[dict[str, Any]]:
    """同一欄位的觀測（as_of 升序）→ 最近 `keep` 次，每次帶前一次的占比。"""
    out = []
    for index, point in enumerate(points):
        previous = points[index - 1]["value"] if index else None
        out.append({"as_of": point["as_of"], "source_ref": point.get("source_ref"),
                    **share_parts(point["value"], previous)})
    return out[-keep:]


REGION_FIELD = "tw_region_revenue"
#: 年報說收入依什麼分地區（`engine_c.tw_region_revenue.REVENUE_BASES`）→ 頁面上那一句。認不得的字彙照原名印（L16）。
REGION_BASIS_NOTES: Mapping[str, str] = {
    "customer_location": "依客戶所在地分",
    "operating_location": "依公司營運地點分——是哪個據點認列的營收，不是客戶在哪",
    "both_found": "這一節同時寫了客戶所在地與營運地點——看原文",
    "unstated": "年報這一節沒寫收入依什麼分地區（客戶所在地、出貨地、營運地點意思不同）",
}


def region_mix(found: Mapping[str, Any]) -> dict[str, Any]:
    """台股年報地區別（`engine_c.tw_region_revenue.region_revenue` 讀到的 `ok` 結果）→ 跟分部占比同一個形狀的一塊：
    `{field, label, note, points}`。每一年一個 point：占比＝金額÷年報自己的合計，帶前一年的占比（名稱逐字對得上才帶）。"""
    basis = str(found.get("basis") or "unstated")
    note = REGION_BASIS_NOTES.get(basis, basis)
    quotes = found.get("basis_quotes") or []
    if quotes:
        note += f"（年報原文：「{quotes[0]}」）"
    source = (f"MOPS {found.get('report_year')} 年度財報附註「地區別資訊」"
              f"（{found.get('source_filename') or '檔名沒記'}；{found.get('available_on')} 公告）")
    points: list[dict[str, Any]] = []
    previous: dict[str, float] = {}
    for year in sorted(found.get("years") or {}):
        data = found["years"][year]
        total = float(data["total"])
        shares: dict[str, float] = {}
        for name, value in data["regions"]:
            shares.setdefault(str(name), float(value) / total)
        parts = [{"name": name, "share": share, "prev_share": previous.get(name)} for name, share in shares.items()]
        parts.sort(key=lambda p: (-p["share"], p["name"]))
        points.append({"as_of": found.get("available_on"), "period": f"{year} 年度", "source_ref": source,
                       "parts": parts, "ignored": []})
        previous = shares
    return {"field": REGION_FIELD, "label": "地區", "note": note, "points": points}


#: 層代表公司宣告的 `scope=segment`＝分部營收：只對分部占比，不拿產品線占比湊（兩種切法口徑不同，L12）。
BET_SHARE_FIELD = "segment_revenue_share"


def bet_share(rides: Sequence[str], declarations: Mapping[str, Any] | None, company_id: str,
              shares: Sequence[Mapping[str, Any]], *, node_names: Mapping[str, str] | None = None) -> dict[str, Any]:
    """押的那一塊占營收多少（B3；2026-10-14）：敘事押的層裡，研究宣告這家當代表公司的那幾層（層代表公司宣告，S3c）——
    宣告用分部營收 → 那個分部在**最新一次**分部占比裡的占比（名稱逐字對得上才算；最新一次沒有同名的就照說，不拿舊的一次湊）；
    宣告用全公司營收 → 整家公司。押的層沒宣告它、宣告的分部沒有占比觀測 → 具名缺席。不推算、不跨公司。

    `rides`：敘事押的節點（`what_it_does` 的 focus，只在來源是 rides 時）；`declarations`：節點 → 現行宣告（None＝這一輪沒讀到）；
    `shares`：`revenue_mix` 的 `shares`（已是生效、as-of 過的）。"""
    names = node_names or {}
    if not rides:
        return {"items": [], "absence": {"kind": "not_yet_recorded", "reason": "敘事還沒宣告押哪一層，說不出押的那一塊"}}
    if declarations is None:
        return {"items": [], "absence": {"kind": "upstream_unavailable", "reason": "層代表公司宣告這一輪沒讀到"}}
    points = next((list(s.get("points") or ()) for s in shares if s.get("field") == BET_SHARE_FIELD), [])
    latest = points[-1] if points else None
    items: list[dict[str, Any]] = []
    for node in rides:
        label = names.get(node) or node
        declaration = declarations.get(node)
        rep = next((r for r in (declaration.representatives if declaration else ()) if r.company_id == company_id), None)
        if rep is None:
            # 句子由前端接在「押的那一塊：」後面——理由只寫哪一段沒有，不重複主詞（10-14 首屏：兩層就重複兩次）
            reason = (f"「{label}」宣告的代表公司不含這一家" if declaration is not None
                      else f"「{label}」還沒宣告代表公司")
            items.append({"node": node, "node_name": label, "scope": None, "value": None, "reason": reason})
            continue
        base = {"node": node, "node_name": label, "scope": rep.scope, "segment": rep.segment, "why": rep.why,
                "rep_id": declaration.rep_id}
        if rep.scope == "whole_company":
            items.append({**base, "value": "whole_company", "reason": None})
            continue
        part = next((p for p in (latest or {}).get("parts") or () if p.get("name") == rep.segment), None)
        if part is None:
            have = [str(p.get("name")) for p in (latest or {}).get("parts") or ()]
            when = (latest or {}).get("period") or (latest or {}).get("as_of")
            reason = (f"宣告的分部「{rep.segment}」在最新一次分部占比（{when}）裡沒有同名的一塊（有的是：{'、'.join(have)}）"
                      if latest else f"宣告的分部「{rep.segment}」還沒有分部占比觀測")
            items.append({**base, "value": None, "reason": reason})
            continue
        items.append({**base, "value": "share", "share": part.get("share"), "prev_share": part.get("prev_share"),
                      "period": latest.get("period") or latest.get("as_of"), "as_of": latest.get("as_of"),
                      "source_ref": latest.get("source_ref"), "reason": None})
    valued = [item for item in items if item.get("value")]
    absence = None if valued else {"kind": "not_yet_recorded",
                                   "reason": "；".join(str(item["reason"]) for item in items if item.get("reason"))}
    return {"items": items, "absence": absence}


__all__ = ["BET_SHARE_FIELD", "HEADLINE_CHARS", "PCT_LABELS", "REGION_BASIS_NOTES", "REGION_FIELD", "SHARE_LABELS",
           "backlog_text", "bet_share", "customers_text", "headline", "region_mix", "share_parts", "share_series"]
