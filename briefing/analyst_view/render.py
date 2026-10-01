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

from briefing.alpha_view.contracts import BASIS_LABEL, CatalystItem, CheckpointItem, Datum, EvidenceItem, RefreshItem
from briefing.alpha_view.render import format_datum_value, render_datum_line, status_label
from shared.markdown import markdown_text

from .contracts import QUESTIONS, AnalystLine, AnalystPanel, AnalystView

__all__ = ["render_analyst_view_markdown"]

_LEGEND = (
    "> **讀法：** 每個值後面的〔〕是**這是哪一種知識**——〔確定性規則〕由既有規則算出／〔觀測值〕直接讀自 "
    "authority／〔粗略代理〕heuristic proxy／〔session 判斷〕研究判斷／〔投資人政策〕使用者自己宣告的要求。"
    "狀態字：有／部分／過期／缺料（有能力、這檔沒資料）／**尚未建模**（系統還沒有這個能力）。"
    "**缺席一律不是 0。** 本畫面不給買賣建議、不給部位尺寸。"
)

_READINESS_LABEL = {
    "ready": "ready——核心各段都有內容",
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

def _absent_line(panel: AnalystPanel) -> str:
    """面板沒有內容時的一行：狀態字＋缺席分型＋產生端給的理由（不是 0、不是空白；INV-3）。"""
    kind = f"（`{markdown_text(panel.absence_kind)}`）" if panel.absence_kind else ""
    return f"**{status_label(panel.status)}**{kind} — {markdown_text(panel.reason or '沒有理由句')}"


def _plain_text(value: Any) -> str:
    """巢狀值攤成人讀的一句（字典逐鍵、清單逐項），**不印 Python repr**（3.7 覆核：AEHR 的分部金額子字典）。"""
    if isinstance(value, Mapping):
        return "、".join(f"{k} {_plain_text(v)}" for k, v in value.items() if v is not None)
    if isinstance(value, (list, tuple)):
        return "；".join(_plain_text(v) for v in value)
    return str(value)


def _plain_value(datum: Datum) -> str:
    """稽核區一格的值：清單印期數與最新一點、字典逐鍵、其餘沿用共用格式。缺席 → 狀態字（不是 None）。"""
    if not datum.is_known:
        return _value_cell(datum)
    value = datum.value
    if isinstance(value, list):
        return f"{len(value)} 期（最新一點：{_plain_text(value[-1]) if value else '—'}）"
    if isinstance(value, Mapping):
        return _plain_text(value)
    return format_datum_value(datum)

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


def _attention_lines(items: Sequence[RefreshItem], *, header: str | None = "需要重看的研究成果",
                     scope: str | None = None, total: int | None = None) -> list[str]:
    """⚠ **「無」是一句斷言，它的範圍必須跟著它一起印。**

    2026-09-07 實測：headline 只看 `HEADLINE_ARTIFACTS`，卻印出「需要重看的研究成果：無」，
    而同一畫面上方寫著 `overall=review_required`——讀者看到的是兩句互相否定的話（L12）。
    有 `scope` 就一定要寫出範圍，並在有全域計數時寫出「本節之外還有幾項」。
    """
    prefix = f"{header}：" if header else ""
    scope_note = f"（範圍：{scope}）" if scope else ""
    elsewhere = (total - len(items)) if (total is not None) else None
    tail = (f"；本節之外另有 **{elsewhere}** 項需要動作——見「5.6 需要重看的研究成果」"
            if elsewhere else "")
    if not items:
        return [f"- {prefix}**無**{scope_note}（本節其餘成果 current 或屬歷史）{tail}", ""]
    out = [f"- **{prefix}**{scope_note}{tail}"] if header else []
    for item in items:
        out.append(f"  - **{item.state}** {markdown_text(item.label)}"
                   f"（`{item.artifact_type}:{item.artifact_id}`）→ {markdown_text(item.required_action)}")
        for reason in item.reasons[:2]:
            out.append(f"    - {markdown_text(reason)}")
        if item.propagated_from:
            out.append(f"    - 傳播自：{markdown_text('、'.join(item.propagated_from))}")
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


def _context_line(context: Mapping[str, Any], *keys: str) -> str:
    parts = [f"{_CONTEXT_LABEL.get(key, key)} {markdown_text(context[key])}" for key in keys
             if context.get(key) is not None]
    return "｜".join(parts)


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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：頭條原本是「現價 →（目標值）→ horizon → simple／年化報酬
    # ＋兩桿拆解」，那正是 AGENTS「首屏拿掉尺」指的那把尺。現在只印現價。
    lines += ["## 現在多少錢", ""]
    lines.append(f"**{_slot(head, 'current_price')}**")
    lines += ["", f"- {_context_line(head.context, 'quote_unit') or '報價單位未知'}",
              f"- 狀態：**{markdown_text(head.status)}**"
              f"（來源 {markdown_text('、'.join(f'{k}={v}' for k, v in head.source_statuses.items()))}）"
              + (f"｜{markdown_text(head.reason)}" if head.reason else ""), ""]
    lines += _compact_table(_by_role(head, "headline_number", "headline_context"))
    lines += _attention_lines(head.attention, scope=head.attention_scope,
                              total=head.attention_total)
    lines += ["- **這個數字不是什麼：**"] + [f"  - {markdown_text(x)}" for x in head.notes] + [""]

    # ---- 基本面（Q1／Q2／Q3）---------------------------------------------
    fund = view.fundamental
    # ---- 投資人短評（optional）-------------------------------------------
    brief = view.brief
    lines += [f"## 短評 — {QUESTIONS['q0_story']}（optional）", ""]
    if brief.context.get("available"):
        for line in _by_role(brief, "brief"):
            if line.key.startswith("brief:"):
                lines.append(f"- **{markdown_text(line.display_label)}**：{markdown_text(str(line.datum.value))}")
        lines.append("")
    else:
        lines += [f"**Not set (optional)** — {markdown_text(brief.reason or '還沒寫短評')}", ""]

    # ---- 首屏末行：候選狀態＋三題三個字（Phase 3 Step 3.7；optional、注入）----------
    # 字全由產生端給（候選板同一個 derive_row）；本層只排版。不上板也印三個字。
    cand = view.candidate
    lines += ["## 這檔現在在哪一格：候選狀態與三題三個字（optional）", ""]
    by_key = {line.key: line.datum for line in cand.lines}
    state = by_key.get("candidate:state")
    if state is not None and state.is_known and isinstance(state.value, Mapping):
        row = state.value
        head_line = f"- 候選狀態：**{markdown_text(str(row.get('derived_label') or row.get('derived') or '—'))}**"
        if row.get("declared") and row.get("declared") != row.get("derived"):
            head_line += f"（敘事宣告：{markdown_text(str(row.get('declared_label') or row.get('declared')))}）"
        if row.get("stall_days") is not None:
            head_line += f"｜滯留 {row.get('stall_days')} 天"
        lines.append(head_line)
        lines += [f"  - 前提失效：{markdown_text(str(t))}" for t in row.get("preconditions") or ()]
        lines += [f"  - {markdown_text(str(t))}" for t in row.get("rewrite") or ()]
        if row.get("note"):
            lines.append(f"  - {markdown_text(str(row.get('note')))}")
    else:
        lines.append(f"- 候選狀態：{_absent_line(cand)}")
    words = [f"{markdown_text(by_key[k].label)}　**{markdown_text(str(by_key[k].value))}**"
             for k in ("candidate:will_it_die", "candidate:priced_in", "candidate:in_numbers") if k in by_key]
    if words:
        lines.append("- " + "｜".join(words))
    lines.append("")

    # ---- 論證層（optional）-----------------------------------------------
    arg = view.argument
    lines += [f"## 論證 — {QUESTIONS['q0_argument']}（optional）", ""]
    for line in _by_role(arg, "paragraph"):
        if line.datum.value:
            lines.append(f"**{markdown_text(line.display_label)}**　{markdown_text(str(line.datum.value))}")
            for item in (line.datum.dependencies or {}).get("long_form") or []:
                lines.append(f"  - {markdown_text(str(item.get('title') or ''))}：{markdown_text(str(item.get('text') or ''))}")
            for cite in (line.datum.dependencies or {}).get("citations") or []:
                lines.append(f"  - 引文（{markdown_text(str(cite.get('who') or '?'))}，{markdown_text(str(cite.get('date') or '?'))}）：{markdown_text(str(cite.get('statement') or ''))}")
        else:
            lines.append(f"**{markdown_text(line.display_label)}**　（{markdown_text(line.datum.reason or '缺料')}）")
        lines.append("")

    # ---- 讀圖（核心，Phase 3 Step 3.7 升核心）------------------------------
    rd = view.readings
    lines += ["## 讀圖：它坐的那一層結構變了沒（核心）", ""]
    if rd.lines:
        for line in rd.lines:
            deps = line.datum.dependencies or {}
            lines.append(f"- **{markdown_text(line.display_label)}**：{markdown_text(str(line.datum.value))}"
                         f"｜{status_label(line.datum.status)}"
                         f"｜讀於 {markdown_text(str(deps.get('read_on') or '—'))}"
                         f"｜到期 {markdown_text(str(deps.get('expires') or '—'))}"
                         + (f"｜{markdown_text(line.datum.reason)}" if line.datum.reason else ""))
            if deps.get("reading"):
                lines.append(f"  - {markdown_text(str(deps.get('reading')))}")
    else:
        lines.append(_absent_line(rd))
    lines.append("")

    # ---- 錯了怎麼知道：每條反證與盯它的 watch（Phase 3 Step 3.7；optional、注入）------
    ds = view.downside
    lines += ["## 錯了怎麼知道：每條反證與盯它的 watch（optional）", ""]
    if ds.lines:
        counts = ds.context.get("counts") or {}
        lines.append(f"在盯 {counts.get('active', 0)}｜醒來待判 {counts.get('fired', 0)}｜觸及待處置 {counts.get('touched', 0)}"
                     f"｜到期待複查 {counts.get('expired', 0)}｜**未盯 {counts.get('unwatched', 0)}**")
        lines.append("")
        for line in ds.lines:
            r = line.datum.value if isinstance(line.datum.value, Mapping) else {}
            watch = (f"watch `{markdown_text(str(r.get('watch_id')))}`：{markdown_text(str(r.get('state_label')))}"
                     if r.get("watch_id") else f"**{markdown_text(str(r.get('state_label') or '未盯'))}**")
            lines.append(f"- {markdown_text(str(r.get('condition') or ''))}（{markdown_text(str(r.get('source_label') or ''))}｜{watch}）")
    else:
        lines.append(_absent_line(ds))
    lines += [""] + [f"- {markdown_text(note)}" for note in ds.notes] + [""]

    # ---- 賭注（optional；V0）---------------------------------------------
    bet = view.bet
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：賭注由四個價格改成**一句話**（讀 `our_bet`）。
    lines += ["## 賭注：我們賭什麼、押在哪一層、什麼必須為真（optional）", ""]
    if bet.context.get("available"):
        # Step 3.7：三格（our_bet／騎的層或插槽／什麼必須為真）。rides 是清單——印成「節點（層／插槽）」；
        # 缺席的格印狀態字與理由，不印 None（本檔 legend：缺席一律不是 0）。
        for line in _by_role(bet, "bet"):
            datum = line.datum
            if isinstance(datum.value, list):
                text = "、".join(f"「{r.get('node_name') or r.get('node')}」（{r.get('unit_label') or r.get('unit')}）"
                                for r in datum.value if isinstance(r, Mapping))
                lines.append(f"- **{markdown_text(line.display_label)}**：{markdown_text(text)}")
            elif datum.is_known:
                lines.append(f"- **{markdown_text(line.display_label)}**：{markdown_text(str(datum.value))}")
            else:
                lines.append(f"- **{markdown_text(line.display_label)}**：{_value_cell(datum)}"
                             + (f" — {markdown_text(datum.reason)}" if datum.reason else ""))
        lines.append("")
    else:
        lines += [f"**Not set (optional)** — {markdown_text(bet.reason or '還沒寫短評裡的 our_bet')}", ""]
    lines += [f"- {markdown_text(bet.context.get('optional_rule') or '')}", ""]

    # ---- 會不會歸零（optional；D2 2026-09-18）-----------------------------
    # 緊接在賭注之後：賭注問「對了值多少」，這一段問「這家公司會不會直接沒了」。
    wipe = view.wipeout
    tally = wipe.context.get("tally") or {}
    lines += ["## 會不會歸零：四盞燈（optional）", "",
              f"紅 **{tally.get('red', 0)}**｜黃 **{tally.get('amber', 0)}**｜綠 **{tally.get('green', 0)}**"
              f"｜**灰（沒量到）{tally.get('unlit', 0)}**　——⚠ 灰不是綠", ""]
    for line in _by_role(wipe, "wipeout"):
        datum = line.datum
        value = datum.value if isinstance(datum.value, dict) else {}
        colour = {"red": "🔴 紅", "amber": "🟡 黃", "green": "🟢 綠"}.get(str(value.get("colour")), "⬜ 灰")
        why = value.get("reason") or datum.reason or "—"
        lines.append(f"- **{markdown_text(line.display_label)}**：{colour} — {markdown_text(str(why))}")
    lines += ["", f"- {markdown_text(wipe.context.get('unlit_rule') or '')}", ""]

    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：「## 1. 我們預測什麼」與「## 3. 差異在哪」隨
    # FY+1 因果橋退役；「## 2. 市場預測什麼」留著——那是 Engine C 的原始數字。
    lines += [f"## 2. {QUESTIONS['q2_market']}", "",
              f"- 會計年度別共識覆蓋：{markdown_text('、'.join(fund.context.get('consensus_periods') or []) or '無')}", ""]
    lines += ["**會計年度別共識**（身分是 fiscal_period_end；只呈現，不與任何內部預測相減）：", ""]
    lines += _compact_table(_by_role(fund, "consensus_fiscal")) or ["（無會計年度別共識。）", ""]
    lines += ["市場脈絡與共識時序：", ""]
    lines += _compact_table(_by_role(fund, "market_context"), reason_column=False)
    lines += [f"- 狀態：**{markdown_text(fund.status)}**"
              f"（來源 {markdown_text('、'.join(f'{k}={v}' for k, v in fund.source_statuses.items()))}）"
              + (f"｜{markdown_text(fund.reason)}" if fund.reason else "")]
    lines += [f"- 註：{markdown_text(note)}" for note in fund.notes] + [""]

    # ---- 財務三題的數字（稽核區；Phase 3 Step 3.7）-------------------------
    # 每一行＝值＋來源＋as of＋口徑，或缺席分型與理由；**沒有門檻**（幾分算已定價由寫敘事的人判斷）。
    tq = view.three_questions
    lines += ["## 財務三題的數字：會死嗎、已定價嗎、出現在數字裡了嗎（稽核區）", ""]
    if tq.lines:
        for line in tq.lines:
            datum, deps = line.datum, (line.datum.dependencies or {})
            detail = deps.get("detail") or {}
            where = "｜".join(x for x in (
                f"來源 {deps.get('source')}" if deps.get("source") else "",
                f"as of {datum.as_of.isoformat()}" if datum.as_of else "",
                f"口徑 {deps.get('basis')}" if deps.get("basis") else "",
                # 自家歷史百分位的覆蓋率（Phase 4 Step 4.7c）：只印，不設門檻
                (f"樣本 {detail.get('samples')}／窗內交易日 {detail['trading_days_in_window']}"
                 f"（覆蓋率 {detail.get('coverage')}）") if detail.get("trading_days_in_window") else "") if x)
            reason = (f" — `{markdown_text(datum.absence_kind)}`：{markdown_text(datum.reason or '')}"
                      if not datum.is_known else "")
            lines.append(f"- **{markdown_text(line.display_label)}**：{markdown_text(_plain_value(datum)) if datum.is_known else _plain_value(datum)}"
                         + (f"（{markdown_text(where)}）" if where else "") + reason)
    else:
        lines.append(_absent_line(tq))
    lines += [""] + [f"- 不是：{markdown_text(note)}" for note in tq.notes] + [""]

    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本這裡是「## 4. 怎麼算到這裡｜哪些假設最脆弱」，
    # 四個子節（最脆弱的輸入／生效的假設／既有敏感度／算式）全部讀估值鏈。`why` panel 已退役，
    # 這一節一併移除。**「什麼會推翻它」沒有退役**，它在下一節（research panel）。

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
    # 2026-10-01 Phase 4 Step 4.7a：舊 session 判讀的反證退役（恆「未盯」）。反證只列反證登記涵蓋的來源，住 downside 面板。
    lines += ["- 反證與盯它的 watch 在個股頁「錯了怎麼知道」面板（APP；本 CLI 不載 watch）。", ""]
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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：`entry`（進場門檻）panel 退役，這一節一併移除。
    # 73 檔全 missing、從未用過；**進場靠判斷，出場靠 disproof**。

    lines += ["## 這份判讀不是什麼", ""]
    lines += [f"- {markdown_text(x)}" for x in view.limits] + [""]
    lines += ["## ⚠ 警告", ""]
    lines += [f"- {markdown_text(w)}" for w in view.warnings]
    lines.append("")
    lines.append(f"（readiness 判準：{markdown_text(view.readiness.rule)}）")
    return "\n".join(lines)
