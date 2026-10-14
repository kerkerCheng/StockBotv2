"""營收從哪來（個股頁 S3d，2026-10-14；B3）——**純函式**。取數住 `alpha/providers/revenue_mix.py`。

把 Engine C 人工觀測（研究從年報、申報表填的）整理成頁面照印的形狀：
- **分部／產品線占比**（`segment_revenue_share`／`product_line_revenue_share`）：頂層數值鍵就是占比（0..1；寫入端已擋超範圍）。
  `_` 開頭的鍵（例 `_amounts_eur_m`、`_note`）與 `total*`（總額）不是占比，照列在 `ignored`、不畫。同一欄位有前一次觀測時，
  每一塊帶前一次的占比（名稱逐字對得上才帶）。兩種切法（分部、產品線）口徑不同，不混在一起（L12）。
- **客戶集中度**、**backlog 與長約**：多數是研究寫的文字（2026-10-14：客戶 38 筆裡 34 筆、backlog 39 筆裡 37 筆）——照抄全文，
  頁面先印第一句；少數是 JSON，組成一句（只挑寫明的欄位，不推算）。

不排序公司、不打分、不算比例（占比照抄；一家公司自己的分部依占比由大到小列是呈現，不是名次）。
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


__all__ = ["HEADLINE_CHARS", "PCT_LABELS", "SHARE_LABELS", "backlog_text", "customers_text", "headline", "share_parts", "share_series"]
