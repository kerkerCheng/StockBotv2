"""`AnalystView` → Markdown。**純呈現**：分節、標籤、表格、缺席狀態。

## 這一支絕不做的事（`tests/test_analyst_view.py` 用 import 掃描與 token 掃描守著）

- 不算報酬、不比較價格、不判斷 actionability、不重排（順序由 `compose.py` 決定）、
  不把缺席印成 0、不把 `hurdle_comparison` 翻譯成 buy／sell。
- 數字格式化與「缺席怎麼印」**重用** `briefing.alpha_view.render` 的原語，不自己再寫一份
  （L12：同一件事兩份實作 ⇒ 兩種語意）。
- 沒有 `if 報酬 > 0` 這種東西：唯一的分支是 `datum.is_known`（有沒有值）與 `role`／`status`
  這些 **builder 已經標好的封閉字彙**。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from briefing.alpha_view.contracts import BASIS_LABEL, CatalystItem, CheckpointItem, Datum, DisproofItem, EvidenceItem, RefreshItem
from briefing.alpha_view.render import format_datum_value, render_datum_line, status_label
from shared.markdown import markdown_text

from .contracts import QUESTIONS, AnalystLine, AnalystPanel, AnalystView, WeakInput

__all__ = ["render_analyst_view_markdown"]

_LEGEND = (
    "> **讀法：** 每個值後面的〔〕是**這是哪一種知識**——〔確定性規則〕由既有規則算出／〔觀測值〕直接讀自 "
    "authority／〔粗略代理〕heuristic proxy／〔session 判斷〕研究判斷／〔投資人政策〕使用者自己宣告的要求。"
    "狀態字：有／部分／過期／缺料（有能力、這檔沒資料）／**尚未建模**（系統還沒有這個能力）。"
    "**缺席一律不是 0。** 本畫面不給買賣建議、不給部位尺寸。"
)

_READINESS_LABEL = {
    "ready": "ready——核心四段都有內容",
    "ready_with_flags": "ready_with_flags——核心有內容，但有段落被標記需要重看",
    "blocked": "blocked——核心有段落缺內容",
}

#: `context` 的 key → 面向讀者的說法（純 label 對照表）。
_CONTEXT_LABEL = {
    "period": "目標期間", "period_end": "期間結束日", "base_period_end": "基期結束日",
    "accounting_basis": "會計口徑",
}


# ---------------------------------------------------------------------------
# 呈現原語
# ---------------------------------------------------------------------------

def _value_cell(datum: Datum) -> str:
    """一格的值。缺席 → 狀態字（不是 0、不是空白）。"""
    if not datum.is_known:
        return f"**{status_label(datum.status)}**"
    prefix = "" if datum.status == "available" else f"【{status_label(datum.status)}】"
    return prefix + format_datum_value(datum)


def _tag_cell(datum: Datum) -> str:
    return BASIS_LABEL.get(datum.basis, datum.basis) if datum.is_known else "—"


def _reason_cell(datum: Datum) -> str:
    return markdown_text(datum.reason) if datum.reason else "—"


def _compact_table(lines: Sequence[AnalystLine], *, reason_column: bool = True) -> list[str]:
    """一組行 → 一張緊湊表。缺席的行照樣佔一列——**看不見的缺口等於沒有缺口**（INV-3）。"""
    if not lines:
        return []
    head = "| 項目 | 值 | 知識種類 | 來源 |" + (" 說明 |" if reason_column else "")
    rule = "|---|---|---|---|" + ("---|" if reason_column else "")
    out = [head, rule]
    for line in lines:
        datum = line.datum
        row = (f"| {markdown_text(line.display_label)} | {_value_cell(datum)} | {_tag_cell(datum)} | "
               f"{('`' + datum.authority + '`') if datum.authority else '—'} |")
        if reason_column:
            row += f" {_reason_cell(datum)} |"
        out.append(row)
    out.append("")
    return out


def _by_role(panel: AnalystPanel, *roles: str) -> tuple[AnalystLine, ...]:
    """依 builder 標好的 `role` 取出一組行（順序沿用 compose 給的順序，不重排）。"""
    return tuple(line for line in panel.lines if line.role in roles)


def _line_by_key(panel: AnalystPanel, key: str) -> AnalystLine | None:
    return next((line for line in panel.lines if line.key == key), None)


def _slot(panel: AnalystPanel, key: str) -> str:
    line = _line_by_key(panel, key)
    if line is None:
        return "—"
    return _value_cell(line.datum)


def _attention_lines(items: Sequence[RefreshItem], *, header: str | None = "需要重看的研究成果") -> list[str]:
    prefix = f"{header}：" if header else ""
    if not items:
        return [f"- {prefix}**無**（其餘成果 current 或屬歷史）", ""]
    out = [f"- **{prefix}**"] if header else []
    for item in items:
        out.append(f"  - **{item.state}** {markdown_text(item.label)}"
                   f"（`{item.artifact_type}:{item.artifact_id}`）→ {markdown_text(item.required_action)}")
        for reason in item.reasons[:2]:
            out.append(f"    - {markdown_text(reason)}")
        if item.propagated_from:
            out.append(f"    - 傳播自：{markdown_text('、'.join(item.propagated_from))}")
    out.append("")
    return out


def _weak_table(weak: Sequence[WeakInput]) -> list[str]:
    if not weak:
        return ["（沒有任何輸入被列入——這通常代表上游還沒有假設，不是「假設都很穩」。）", ""]
    out = ["| 輸入 | 目前值 | 知識種類 | 為什麼被列進來 |", "|---|---|---|---|"]
    for item in weak:
        out.append(f"| {markdown_text(item.display_label)} | {_value_cell(item.datum)} | "
                   f"{_tag_cell(item.datum)} | {markdown_text(item.why)} |")
    out.append("")
    return out


def _evidence_table(items: Sequence[EvidenceItem]) -> list[str]:
    if not items:
        return ["（這幾格沒有掛任何 evidence ref。）", ""]
    out = ["| ref | kind | origin | tier | 發表日 |", "|---|---|---|---|---|"]
    for item in items:
        out.append(f"| `{item.ref}` | {markdown_text(item.kind)} | {markdown_text(item.origin_entity or '—')} | "
                   f"{item.evidence_tier if item.evidence_tier is not None else '—'} | "
                   f"{item.published_at.isoformat() if item.published_at else '—'} |")
    out.append("")
    return out


def _catalyst_lines(catalysts: Sequence[CatalystItem], checkpoints: Sequence[CheckpointItem]) -> list[str]:
    out: list[str] = []
    if catalysts:
        for item in catalysts:
            when = item.expected_at.isoformat() if item.expected_at else "日期未知"
            out.append(f"- {markdown_text(item.kind)}：{markdown_text(item.description)}"
                       f"（{when}，date_confidence={item.date_confidence}）")
    if checkpoints:
        for point in checkpoints:
            mark = "" if point.date_confidence == "confirmed" else "（推估）"
            out.append(f"- {point.date.isoformat()}{mark} {markdown_text(point.what)}"
                       f" — 裁決：{markdown_text(point.decides)}〔`{point.source}`〕")
    if not out:
        out.append("- **無結構化催化劑與檢核點**——不是「沒有催化劑」，是這檔還沒有人把它們寫成結構化紀錄。")
    out.append("")
    return out


def _disproof_lines(conditions: Sequence[DisproofItem]) -> list[str]:
    if not conditions:
        return ["- **無結構化 disproof**——出場靠 disproof，這一格空著就等於沒有出場條件。", ""]
    out: list[str] = []
    for item in conditions:
        out.append(f"- {markdown_text(item.condition)}")
        out.append(f"  - 核查頻率：{markdown_text(item.check_frequency)}｜"
                   f"觸發後 48 小時：{markdown_text(item.action_within_48h)}")
    out.append("")
    return out


def _context_line(context: Mapping[str, Any], *keys: str) -> str:
    parts = [f"{_CONTEXT_LABEL.get(key, key)} {markdown_text(context[key])}" for key in keys
             if context.get(key) is not None]
    return "｜".join(parts)


def _one_sentence(line: AnalystLine | None) -> str | None:
    """authority 自己組出的一句話（`epistemics.one_sentence`）。**只取，不改寫、不自己造句。**"""
    if line is None or not line.datum.is_known or not isinstance(line.datum.value, Mapping):
        return None
    text = line.datum.value.get("one_sentence")
    return str(text) if text else None


# ---------------------------------------------------------------------------
# 完整畫面
# ---------------------------------------------------------------------------

def render_analyst_view_markdown(view: AnalystView) -> str:
    head = view.headline
    lines: list[str] = [
        f"# Analyst View — {markdown_text(view.company_label)}",
        "",
        _LEGEND,
        "",
        f"- 生成日 {view.generated_on.isoformat()}｜視角 {markdown_text(view.point_in_time_mode)}"
        + (f"（as-of {view.as_of.isoformat()}）" if view.as_of else "（當前）")
        + f"｜read model `{markdown_text(view.source_schema_version)}`",
        f"- **Core readiness：{markdown_text(_READINESS_LABEL.get(view.readiness.state, view.readiness.state))}**"
        f"（核心＝{markdown_text('／'.join(view.readiness.core_panels))}；"
        f"optional＝{markdown_text('／'.join(view.readiness.optional_panels))}，不參與）",
    ]
    for flag in view.readiness.flags:
        lines.append(f"  - ⚠ {markdown_text(flag)}")
    for blocker in view.readiness.blockers:
        lines.append(f"  - ⛔ {markdown_text(blocker)}")
    for item in view.readiness.optional_unavailable:
        lines.append(f"  - ○ optional 未設定：{markdown_text(item)}（**不影響 core readiness**）")
    refresh = view.refresh
    counts = "、".join(f"{key} {value}" for key, value in refresh.counts.items() if value)
    lines += [
        f"- Refresh：overall **{markdown_text(refresh.overall)}**｜{markdown_text(counts or '無成果')}"
        f"｜變更偵測 {markdown_text(refresh.change_detection)}"
        + ("｜判斷與目前 context：" + ("一致" if refresh.judged_context_matches else "**不一致**")
           if refresh.judged_context_matches is not None else ""),
        "",
    ]

    # ---- 頭條 ------------------------------------------------------------
    lines += [f"## 頭條 — {QUESTIONS['q4_implied_return']}", ""]
    lines.append(
        f"**{_slot(head, 'current_price')}**（{_slot(head, 'value_date')} 的目標值："
        f"**{_slot(head, 'fair_value')}**）→ horizon **{_slot(head, 'horizon')}** → "
        f"**{_slot(head, 'price_return')}** simple ／ **{_slot(head, 'annualized_price_return')}** 年化"
    )
    sentence = _one_sentence(_line_by_key(head, "epistemics_one_sentence"))
    if sentence:
        lines += ["", f"> {markdown_text(sentence)}",
                  ">", "> （這句話由 `alpha://implied_return/model` 自己組出，consumer 只是把它放到最前面。）"]
    lines += ["", f"- {_context_line(head.context, 'period', 'period_end', 'accounting_basis') or '目標期間未知'}",
              f"- 狀態：**{markdown_text(head.status)}**"
              f"（來源 {markdown_text('、'.join(f'{k}={v}' for k, v in head.source_statuses.items()))}）"
              + (f"｜{markdown_text(head.reason)}" if head.reason else ""), ""]
    lines += _compact_table(_by_role(head, "headline_number", "headline_context"))
    lines += _attention_lines(head.attention)
    lines += ["- **這個數字不是什麼：**"] + [f"  - {markdown_text(x)}" for x in head.notes] + [""]

    # ---- 基本面（Q1／Q2／Q3）---------------------------------------------
    fund = view.fundamental
    lines += [f"## 1. {QUESTIONS['q1_internal']}（Internal forecast）", "",
              f"- {_context_line(fund.context, 'period', 'period_end', 'base_period_end', 'accounting_basis') or '目標期間未知'}",
              ""]
    lines += _compact_table(_by_role(fund, "internal"))
    lines += [f"## 2. {QUESTIONS['q2_market']}", ""]
    lines += ["**同期、同口徑的共識**（只有這些能與內部相減）：", ""]
    lines += _compact_table(_by_role(fund, "consensus_same_period")) or ["（無同期共識。）", ""]
    lines += ["其他期間的共識與市場觀測（**只呈現，不與內部相減**）：", ""]
    lines += _compact_table(_by_role(fund, "consensus_other_period", "market_context", "market_proxy"),
                            reason_column=False)
    lines += [f"## 3. {QUESTIONS['q3_gap']}", ""]
    lines += _compact_table(_by_role(fund, "comparison"))
    lines += [f"- 狀態：**{markdown_text(fund.status)}**"
              f"（來源 {markdown_text('、'.join(f'{k}={v}' for k, v in fund.source_statuses.items()))}）"
              + (f"｜{markdown_text(fund.reason)}" if fund.reason else "")]
    lines += [f"- 註：{markdown_text(note)}" for note in fund.notes] + [""]

    # ---- 怎麼算到這裡 ＋ 最脆弱的假設 ------------------------------------
    why = view.why
    lines += [f"## 4. 怎麼算到這裡｜{QUESTIONS['q5_fragile']}", "",
              "### 4.1 最脆弱的輸入", "",
              "> 列入規則是**宣告好的**（見下表最後一欄），不是本層對脆弱程度的新判斷；"
              "敏感度是估值層既有的確定性微擾，不是機率、也不是 attribution model。", ""]
    lines += _weak_table(why.weak_inputs)
    lines += ["### 4.2 生效的假設（它們不是事實）", ""]
    lines += _compact_table(_by_role(why, "assumption"))
    lines += ["### 4.3 既有敏感度（每條假設動一格，fair value 動多少）", ""]
    lines.append(f"> 排序：{markdown_text(why.context.get('sensitivity_order') or '—')}")
    lines.append("")
    lines += _compact_table(_by_role(why, "sensitivity"), reason_column=False)
    lines += ["### 4.4 算式（每一格都指得出上一格）", ""]
    for line in _by_role(why, "trace"):
        lines.append(render_datum_line(line.datum))
    lines.append("")
    lines += ["### 4.5 多少是算術、多少是判斷", ""]
    for line in _by_role(why, "epistemics"):
        lines.append(render_datum_line(line.datum))
    lines.append("")
    lines += ["### 4.6 這幾格引用到的證據", ""]
    lines += _evidence_table(why.evidence)
    lines += [f"- 註：{markdown_text(note)}" for note in why.notes] + [""]

    # ---- 什麼會改變答案 --------------------------------------------------
    research = view.research
    lines += [f"## 5. {QUESTIONS['q6_change']}", "",
              f"- 研究判斷：{'有' if research.context.get('has_signal') else '**無**'}"
              + (f"（寫於 {markdown_text(research.context.get('judged_at') or '日期未知')}）" if research.context.get("has_signal") else "")
              + f"｜已知維度 {len(research.context.get('known_axes') or [])}/5"
              + f"｜最弱 {markdown_text(research.context.get('weakest_axis') or '—')}"
              + f"｜thesis lifecycle {markdown_text(research.context.get('thesis_lifecycle_status') or '—')}"
              + f"｜Engine D research_status {markdown_text(research.context.get('research_status') or '—')}",
              ""]
    lines += ["### 5.1 Thesis 與 variant view", ""]
    lines += _compact_table(_by_role(research, "thesis"))
    lines += ["### 5.2 Q1–Q5", ""]
    lines += _compact_table(_by_role(research, "score"), reason_column=False)
    lines += ["### 5.3 催化劑與檢核點", ""]
    lines += _catalyst_lines(research.catalysts, research.checkpoints)
    lines += ["### 5.4 什麼會推翻它（出場靠 disproof）", ""]
    lines += _disproof_lines(research.disproofs)
    lines += ["### 5.5 生命週期與到期", ""]
    lines += _compact_table(_by_role(research, "lifecycle"))
    lines += ["### 5.6 需要重看的研究成果", ""]
    lines += _attention_lines(research.attention, header=None)
    if research.risks:
        lines += ["### 5.7 研究判斷列出的風險", ""]
        lines += [f"- {markdown_text(risk)}" for risk in research.risks] + [""]
    if research.notes:
        lines += ["### 5.8 註記", ""]
        lines += [f"- {markdown_text(note)}" for note in research.notes] + [""]

    # ---- Entry（optional）------------------------------------------------
    entry = view.entry
    lines += [f"## {markdown_text(entry.title)}", ""]
    if entry.context.get("available"):
        lines += _compact_table(_by_role(entry, "entry"))
    else:
        lines += [f"**Not set (optional)** — {markdown_text(entry.reason or '尚未宣告要求報酬判準')}", "",
                  "上游照抄值仍然看得見（要先知道現在隱含幾 %，才知道自己該不該宣告 hurdle）：", ""]
        lines += _compact_table(_by_role(entry, "entry"), reason_column=False)
    lines += [f"- {markdown_text(entry.context.get('optional_rule') or '')}",
              "- 要宣告判準：`python -m alpha entry-criterion <TICKER> --add <spec.json>`；"
              "只想試算不落地：`python -m briefing entry <TICKER> --sandbox-hurdle 0.15`。", ""]
    lines += ["- **Entry 不是什麼：**"] + [f"  - {markdown_text(x)}" for x in entry.notes] + [""]

    # ---- 邊界與警告 ------------------------------------------------------
    lines += ["## 這份判讀不是什麼", ""]
    lines += [f"- {markdown_text(x)}" for x in view.limits] + [""]
    lines += ["## ⚠ 警告", ""]
    lines += [f"- {markdown_text(w)}" for w in view.warnings]
    lines.append("")
    lines.append(f"（readiness 判準：{markdown_text(view.readiness.rule)}）")
    return "\n".join(lines)
