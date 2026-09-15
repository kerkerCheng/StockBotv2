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


def numbers_paragraph(*, base_period: str | None, target_period: str | None, currency: str | None,
                      base_revenue: float | None, base_margin: float | None,
                      growth: Sequence[tuple[str, float]], margin_delta: float | None,
                      internal_revenue: float | None, internal_margin: float | None, internal_eps: float | None,
                      consensus_eps: float | None, top_sensitivity: Mapping[str, Any] | None,
                      driver_labels: Mapping[str, str]) -> str:
    """「數字怎麼算出來」：基期 → 假設 → 結果，一段話。缺料就說缺什麼，不補。"""
    if base_revenue is None or base_margin is None:
        return "還沒有上一個年度的實際數字，所以算不出明年的獲利。"
    unit = currency or ""
    parts = [f"{base_period or '上一年度'}營收 {format_value('money', base_revenue)} {unit}、營益率 {format_value('ratio', base_margin).lstrip('+')}。"]
    if not growth and margin_delta is None:
        parts.append("還沒寫下任何假設，所以停在這裡。")
        return "".join(parts)
    assumptions = [f"「{scope}」業務成長 {format_value('ratio', value)}" for scope, value in growth]
    if margin_delta is not None:
        assumptions.append(f"營益率{'提高' if margin_delta >= 0 else '降低'} {abs(margin_delta) * 100:.1f} 個百分點")
    parts.append("我們假設：" + "、".join(assumptions) + "。")
    if internal_eps is not None:
        parts.append(f"走完這幾步，{target_period or '明年'}營收 {format_value('money', internal_revenue)} {unit}、"
                     f"營益率 {format_value('ratio', internal_margin).lstrip('+')}、每股盈餘 {format_value('price', internal_eps)}")
        parts.append(f"；市場共識 {format_value('price', consensus_eps)}。" if consensus_eps is not None else "。")
    else:
        parts.append("但有一格缺假設，所以每股盈餘算不出來。")
    if top_sensitivity:
        label = driver_labels.get(str(top_sensitivity.get("driver") or ""), str(top_sensitivity.get("driver") or ""))
        delta = top_sensitivity.get("delta_fair_value")
        rel = top_sensitivity.get("fair_value_relative")
        bump_unit = top_sensitivity.get("bump_unit")
        step = "每差 1 個百分點" if bump_unit == "absolute_ratio" else "每差 1%"
        if isinstance(delta, (int, float)) and isinstance(rel, (int, float)):
            parts.append(f"最敏感的是{label}：{step}，目標價差約 {format_value('price', abs(delta))} {unit}（{abs(rel) * 100:.1f}%）。")
    return "".join(parts)


def market_paragraph(*, comparisons: Sequence[Mapping[str, Any]], market_multiple: float | None,
                     our_multiple: float | None, multiple_rationale: str | None,
                     reverse: Mapping[str, Any] | None, driver_labels: Mapping[str, str]) -> str:
    """「和市場差在哪」：逐指標一句、倍數一句、要撐起現價需要什麼一句。"""
    parts: list[str] = []
    said = 0
    for item in comparisons:
        rel = item.get("relative_gap")
        label = str(item.get("label") or item.get("metric") or "")
        if isinstance(rel, (int, float)):
            direction = "高" if rel > 0 else "低"
            parts.append(f"{label}我們比市場{direction} {abs(rel) * 100:.1f}%")
            said += 1
    text = ("、".join(parts) + "。") if parts else "目前沒有一項可以跟市場相減（期間或口徑對不上）。"
    if market_multiple is not None and our_multiple is not None:
        text += f"市場對明年獲利付 {format_value('multiple', market_multiple)}，我們給 {format_value('multiple', our_multiple)}"
        text += f"（理由：{multiple_rationale.strip()}）。" if multiple_rationale else "。"
    if reverse and reverse.get("solutions"):
        needs = []
        for sol in reverse["solutions"]:
            if sol.get("status") != "solved":
                continue
            driver = str(sol.get("driver") or "")
            label = driver_labels.get(driver, driver)
            scope = sol.get("scope")
            implied = sol.get("implied_value")
            if not isinstance(implied, (int, float)):
                continue
            if driver == "operating_margin_delta":
                needs.append(f"營益率要多提高 {implied * 100:.1f} 個百分點")
            else:
                who = f"「{scope}」業務的{label}" if scope and scope != "total" else label
                needs.append(f"{who}要到 {format_value('ratio', implied)}")
        if needs:
            text += "要撐起現在的股價，其他假設不動的話，" + "，或者".join(needs[:2]) + "。"
    return text


def bet_paragraph(*, has_bet: bool, overrides: Sequence[Mapping[str, Any]], bet_target: float | None,
                  price: float | None, payoff: float | None, eps_part: float | None, multiple_part: float | None,
                  currency: str | None, driver_labels: Mapping[str, str]) -> str:
    if not has_bet:
        return "還沒寫下賭注：我們和市場的差異看法還沒被寫成一條可以算的假設。"
    unit = currency or ""
    parts: list[str] = []
    for item in overrides:
        driver = str(item.get("driver") or "")
        label = driver_labels.get(driver, driver)
        scope = item.get("scope")
        base = item.get("base_value")
        value = item.get("value")
        if driver == "operating_margin_delta":
            base_text = f"{base * 100:.1f} 個百分點" if isinstance(base, (int, float)) else "（沒有基準）"
            parts.append(f"營益率提高幅度從 {base_text} 改成 {value * 100:.1f} 個百分點")
            continue
        kind = "ratio" if item.get("unit") == "ratio" else "currency"
        who = f"「{scope}」業務的{label}" if scope and scope != "total" else label
        parts.append(f"{who}從 {format_value(kind, base) if base is not None else '（沒有基準）'} 改成 {format_value(kind, value)}")
    text = "賭注只改這幾條：" + "；".join(parts) + "。" if parts else "賭注只改倍數，獲利面沿用保守版。"
    if bet_target is not None and price is not None and payoff is not None:
        text += f"賭對了值 {format_value('price', bet_target)} {unit}，對現價 {format_value('price', price)} {unit} 是 {format_value('ratio', payoff)}"
        if eps_part is not None and multiple_part is not None:
            text += f"；其中獲利面貢獻 {format_value('ratio', eps_part)}、倍數面貢獻 {format_value('ratio', multiple_part)}"
        text += "。"
    return text


def timeline_paragraph(*, checkpoints: Sequence[Mapping[str, Any]], catalysts: Sequence[Mapping[str, Any]],
                       value_date: Any, horizon_end: Any, thesis_next_check: Any) -> str:
    items: list[tuple[str, str]] = []
    for cp in checkpoints:
        if cp.get("date"):
            items.append((format_value("date", cp["date"]) or "", f"{cp.get('what') or ''}（看的是：{cp.get('decides') or '未說明'}）"))
    for ct in catalysts:
        when = format_value("date", ct.get("expected_at")) if ct.get("expected_at") else "日期未定"
        items.append((when or "", str(ct.get("description") or "")))
    items.sort(key=lambda t: t[0])
    parts = [f"{when}：{what}" for when, what in items if what]
    text = "；".join(parts) + "。" if parts else "還沒有寫下任何裁決點。"
    tail = []
    if value_date:
        tail.append(f"目標價指的是 {format_value('date', value_date)} 那一天的值")
    if horizon_end:
        tail.append(f"我們假設市場最晚在 {format_value('date', horizon_end)} 前定價到那裡")
    if thesis_next_check:
        tail.append(f"這條判斷下次例行核查是 {format_value('date', thesis_next_check)}")
    if tail:
        text += "；".join(tail) + "。"
    return text


__all__ = [
    "EVIDENCE_CLASS_PLAIN", "QUALIFICATION_PLAIN", "RELATION_PLAIN", "WEAK_CLASSES", "bet_paragraph",
    "chain_paragraph", "market_paragraph", "numbers_paragraph", "timeline_paragraph",
]
