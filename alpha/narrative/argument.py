"""論證層（2026-09-15）：把既有的數字與圖，用**封閉句型**組成分析師報告體的段落。

## 分工

- **文字由程式組**的只有兩種：算術的敘述（「數字怎麼算出來」「和市場差在哪」）與圖的敘述（「這條鏈怎麼走」）。
  它們不需要判斷，而且每次 materialize 都要跟數字同步——所以是句型不是 session。
- **判斷的長文照抄 session 寫的**：假設的理由、賭注的理由、風險、推翻條件。本檔不改寫、不摘要。
- **本檔不算任何數**：所有輸入都是別的 section 已算好的值；這裡只格式化、只選詞。

## 禁止

不出現內部名詞（跳、邊、sub=5、tier、sole_source、session_judgment…）——`FORBIDDEN_TERMS` 同一張表守著；
`tests/test_argument_layer.py` 對每個句型的輸出掃一次。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .fill import format_value

#: 邊的證據等級 → 誰說的。key 集合必須與 `query.bottleneck.EVIDENCE_LABEL` 相同（測試守著，不 import 以維持零相依）。
EVIDENCE_CLASS_PLAIN: Mapping[str, str] = {
    "counterparty_joint": "雙方一起說的",
    "externally_corroborated": "有客戶或第三方印證",
    "self_reported_costly": "公司自己說的，但寫在正式申報文件裡",
    "self_reported": "只有公司自己說",
    "needs_review": "還沒判定誰說的",
}
RELATION_PLAIN: Mapping[str, str] = {
    "supplies_to": "供應", "depends_on": "依賴", "also_supplied_by": "也由別人供應", "partnership_with": "合作",
}
QUALIFICATION_PLAIN: Mapping[str, str] = {
    "designed_in": "已被設計進客戶產品", "qualified": "已通過客戶驗證", "qualifying": "驗證中", "unqualified": "尚未驗證",
}
WEAK_CLASSES: frozenset[str] = frozenset({"self_reported", "needs_review"})


def _name(node_id: str | None, names: Mapping[str, str]) -> str:
    if not node_id:
        return "（未知）"
    return names.get(node_id) or node_id.split(":", 1)[-1].replace("_", " ")


def chain_paragraph(*, company: str, anchor_id: str | None, edges: Sequence[Mapping[str, Any]],
                    names: Mapping[str, str]) -> str:
    """「這條鏈怎麼走」：需求端→公司的每一段連結各一句，再點出證據最薄的那段。"""
    if not edges:
        return f"圖裡還沒有 {company} 的供應鏈連結，所以說不出它在哪條鏈上。"
    anchor = _name(anchor_id, names)
    parts: list[str] = [f"需求端是「{anchor}」。"]
    strong = [e for e in edges if str(e.get("evidence_class") or "") not in WEAK_CLASSES]
    weak = [e for e in edges if str(e.get("evidence_class") or "") in WEAK_CLASSES]
    # 有印證的連結逐條講（唯一來源與設計進客戶產品的排前面）；只有公司自己說的合成一句，不逐條佔版面。
    strong.sort(key=lambda e: (not bool(e.get("sole_source")), e.get("qualification_status") != "designed_in"))
    for edge in strong:
        target = _name(edge.get("target"), names)
        relation = RELATION_PLAIN.get(str(edge.get("relation") or ""), str(edge.get("relation") or ""))
        bits = [f"{company}{relation}「{target}」"]
        if edge.get("sole_source"):
            bits.append("目前是唯一來源")
        qual = QUALIFICATION_PLAIN.get(str(edge.get("qualification_status") or ""))
        if qual:
            bits.append(qual)
        bits.append(EVIDENCE_CLASS_PLAIN.get(str(edge.get("evidence_class") or ""), "證據等級未知"))
        parts.append("；".join(bits) + "。")
    if weak:
        names_text = "、".join(f"「{_name(e.get('target'), names)}」" for e in weak)
        parts.append(f"另外 {len(weak)} 條連結（{names_text}）只有公司自己在講，還沒有客戶或第三方印證——"
                     "那是整條鏈最薄的地方。")
    elif strong:
        parts.append("每一段連結都有客戶或第三方印證。")
    return "".join(parts)


# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`numbers_paragraph`（數字怎麼算出來：基期 → 假設 → 結果）與
# `market_paragraph`（和市場差在哪：逐指標相減、倍數、反推）退役（C／H 組）；`bet_paragraph`（四個價格組句）
# 隨 E 組退役。它們的輸入全是估值鏈。


def closure_phrase(closure: Mapping[str, Any] | None) -> str | None:
    """「市場承認了嗎」一句：共識自判斷日以來的移動，對照我們的 base 與賭注。無資料回 None。"""
    if not closure:
        return None
    base = closure.get("base") or {}
    if base.get("status") != "available":
        return None
    start, now = base.get("start_value"), base.get("now_value")
    text = f"自 {format_value('date', base.get('start_date'))} 以來，市場共識每股盈餘從 {format_value('price', start)} 到 {format_value('price', now)}"
    if base.get("moved") == 0:
        text += "，沒有動"
    else:
        frac = base.get("closed_fraction")
        if isinstance(frac, (int, float)):
            direction = "朝我們的看法移了" if frac > 0 else "反向移了"
            text += f"，{direction} {abs(frac) * 100:.0f}%"
    variant = closure.get("variant") or {}
    frac_v = variant.get("closed_fraction") if variant else None
    if isinstance(frac_v, (int, float)) and base.get("moved") != 0:
        text += f"（對賭注而言是 {frac_v * 100:+.0f}%）"
    return text + f"（{base.get('n_points')} 次抓取）。"


def timeline_paragraph(*, checkpoints: Sequence[Mapping[str, Any]], catalysts: Sequence[Mapping[str, Any]],
                       thesis_next_check: Any) -> str:
    """「時間表」：裁決點與催化劑各一句，再加下次例行核查日。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`value_date`／`horizon_end`（目標價是哪一天的值、市場最晚何時定價到那裡）
    與 `reached`（現價已高於目標價）三個輸入隨估值鏈退役。
    """
    items: list[tuple[str, str]] = []
    for cp in checkpoints:
        if cp.get("date"):
            items.append((format_value("date", cp["date"]) or "", f"{cp.get('what') or ''}（看的是：{cp.get('decides') or '未說明'}）"))
    state_text = {"resolved": "（已裁決：事件過了、假設也重看過）", "due": "（到期，假設還沒重看）",
                  "pending": "（未到）", "unlinked": ""}
    for ct in catalysts:
        when = format_value("date", ct.get("expected_at")) if ct.get("expected_at") else "日期未定"
        items.append((when or "", str(ct.get("description") or "") + state_text.get(str(ct.get("state") or "unlinked"), "")))
    items.sort(key=lambda t: t[0])
    parts = [f"{when}：{what}" for when, what in items if what]
    text = "；".join(parts) + "。" if parts else "還沒有寫下任何裁決點。"
    if thesis_next_check:
        text += f"這條判斷下次例行核查是 {format_value('date', thesis_next_check)}。"
    return text


__all__ = [
    "EVIDENCE_CLASS_PLAIN", "QUALIFICATION_PLAIN", "RELATION_PLAIN", "WEAK_CLASSES",
    "chain_paragraph", "closure_phrase", "timeline_paragraph",
]
