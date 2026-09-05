"""`AlphaInvestmentView` → Markdown。**純呈現**：排版、標籤、表格、缺席狀態、provenance。

## 這一支絕不做的事（`tests/test_alpha_view_render.py` 用 import 掃描與 token 掃描守著）

- 不算 expected return、不推 actionability、不重排、不重新解讀缺席資料、
  不跑查詢、不呼叫外部 API、不做任何 domain reasoning。
- **沒有 `if q4 > 3 and q5 > 2` 這種東西**：renderer 讀到的每個 status／basis 都是
  builder 已經標好的，這裡只查表把它變成中文。
- **缺席永遠印成「未知／尚未建模＋原因」，不印 0、不印 0%、不印空白格。**

## 為什麼 renderer 只依賴 `contracts` 與 `shared.markdown`

同一份 view 未來還會有 Web／API consumer；若 renderer 偷偷依賴 Engine C 或 Neo4j，
「view 已經是 presentation-independent」這句話就是假的。import 清單是這個承諾的可執行形式。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from shared.markdown import markdown_text

from .contracts import (
    BASIS_LABEL, STATUS_LABEL, AlphaInvestmentView, CatalystItem, CheckpointItem, Datum,
    DisproofItem, EventItem, ExposureItem, ImpactItem, PathItem, SectionMeta,
    StructuralEdgeItem,
)

__all__ = ["render_alpha_investment_view_markdown", "render_alpha_cards"]

_LEGEND = (
    "> 圖例——每一格後面的〔〕標的是**這是哪一種知識**："
    "〔確定性規則〕由既有規則算出／〔觀測值〕直接讀自 authority／〔粗略代理〕heuristic proxy／"
    "〔session 判斷〕LLM／session 的判斷／〔散文〕未結構化文字／〔結構推論〕圖上多跳推論。"
    "狀態字：有／部分／過期／缺料（有能力、這檔沒資料）／證據不足／**尚未建模**（系統還沒有這個能力）／不適用。"
    "**缺席一律不是 0。**"
)


# ---------------------------------------------------------------------------
# 格式化原語（只做格式，不做判斷）
# ---------------------------------------------------------------------------

def _pct(value: Any) -> str:
    return f"{value * 100:+.1f}%"


def _number(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        text = f"{value:,.4f}".rstrip("0").rstrip(".")
        return text or "0"
    return markdown_text(value)


def _scalar(value: Any, unit: str | None) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)) and unit:
        if unit.startswith("ratio") and unit != "ratio_by_segment":
            return _pct(value)
        if unit == "multiple":
            return f"{value:.1f}x"
        if unit.startswith("ordinal_0_1"):
            return f"{value:.2f}"
        if unit == "currency_per_share":
            return f"{value:,.2f}"
        if unit == "shares" or unit.startswith("reporting_currency"):
            return f"{value:,.0f}"
    if isinstance(value, (int, float)):
        return _number(value)
    return markdown_text(value)


def _dependency_lines(deps: Mapping[str, Any]) -> list[str]:
    """模型輸出的依賴：期間／口徑／輸入知識種類／假設 id。只排版，不解讀。"""
    parts: list[str] = []
    if deps.get("period"):
        period = markdown_text(deps["period"])
        if deps.get("fiscal_period_end"):
            period += f"（至 {markdown_text(deps['fiscal_period_end'])}）"
        parts.append(f"期間 {period}")
    if deps.get("accounting_basis"):
        parts.append(f"口徑 {markdown_text(deps['accounting_basis'])}")
    if deps.get("input_dependency"):
        parts.append(f"輸入知識種類 **{BASIS_LABEL.get(deps['input_dependency'], deps['input_dependency'])}**")
    ids = deps.get("assumption_ids") or ()
    if ids:
        shown = "、".join(f"`{i}`" for i in list(ids)[:6])
        more = f" 等 {len(ids)} 條" if len(ids) > 6 else ""
        parts.append(f"依賴假設 {shown}{more}")
    if deps.get("assumption_id"):
        parts.append(f"id `{deps['assumption_id']}`")
    if deps.get("created_at"):
        parts.append(f"寫於 {markdown_text(str(deps['created_at'])[:10])}")
    if deps.get("supersedes_id"):
        parts.append(f"取代 `{deps['supersedes_id']}`")
    if deps.get("kind"):
        parts.append(f"格的種類 {markdown_text(deps['kind'])}")
    return [f"  - 依賴：{'｜'.join(parts)}"] if parts else []


def _mapping_text(value: Mapping[str, Any], unit: str | None) -> str:
    parts = []
    for key, item in value.items():
        if item is None:
            parts.append(f"{markdown_text(key)}=—")
        elif isinstance(item, Mapping):
            parts.append(f"{markdown_text(key)}={{{_mapping_text(item, None)}}}")
        elif unit == "ratio_by_segment" and isinstance(item, (int, float)):
            parts.append(f"{markdown_text(key)} {_pct(item)}")
        else:
            parts.append(f"{markdown_text(key)}={_scalar(item, None)}")
    return "、".join(parts)


def _value_text(datum: Datum) -> str:
    if isinstance(datum.value, Mapping):
        return _mapping_text(datum.value, datum.unit)
    if isinstance(datum.value, (list, tuple)):
        return "、".join(_scalar(v, datum.unit) for v in datum.value)
    return _scalar(datum.value, datum.unit)


def _tag(basis: str, authority: str | None, as_of: date | None) -> str:
    bits = [BASIS_LABEL.get(basis, basis)]
    if authority:
        bits.append(f"`{authority}`")
    if as_of:
        bits.append(f"as-of {as_of.isoformat()}")
    return "〔" + "｜".join(bits) + "〕"


def _datum_line(datum: Datum) -> str:
    """一格一行。缺席 → **狀態字＋原因**，永遠不是數字。"""
    if not datum.is_known:
        reason = f"——{markdown_text(datum.reason)}" if datum.reason else ""
        return f"- {markdown_text(datum.label)}：**{STATUS_LABEL.get(datum.status, datum.status)}**{reason}"
    status = "" if datum.status == "available" else f"【{STATUS_LABEL.get(datum.status, datum.status)}】"
    line = (f"- {markdown_text(datum.label)}：{status}{_value_text(datum)} "
            f"{_tag(datum.basis, datum.authority, datum.as_of)}")
    if datum.unit:
        line += f"（單位：{markdown_text(datum.unit)}）"
    if datum.method:
        line += f"\n  - 方法：{markdown_text(datum.method)}"
    if datum.reason:
        line += f"\n  - 註：{markdown_text(datum.reason)}"
    if datum.evidence_refs:
        shown = "、".join(f"`{r}`" for r in datum.evidence_refs[:4])
        more = f" 等 {len(datum.evidence_refs)} 條" if len(datum.evidence_refs) > 4 else ""
        line += f"\n  - 證據：{shown}{more}"
    if datum.dependencies:
        line += "".join("\n" + dep for dep in _dependency_lines(datum.dependencies))
    return line


def _meta_lines(meta: SectionMeta) -> list[str]:
    head = (f"狀態：**{STATUS_LABEL.get(meta.status, meta.status)}**｜知識種類："
            f"{BASIS_LABEL.get(meta.basis, meta.basis)}")
    if meta.capability:
        head += f"｜capability：`{meta.capability}`"
    if meta.authority:
        head += f"｜authority：`{meta.authority}`"
    if meta.freshness:
        head += f"｜新鮮度：{meta.freshness}"
    lines = [head]
    if meta.reason:
        lines.append(f"原因：{markdown_text(meta.reason)}")
    for warning in meta.warnings:
        lines.append(f"⚠ {markdown_text(warning)}")
    lines.append("")
    return lines


def _path_line(path: PathItem) -> str:
    chain = " → ".join(
        f"{markdown_text(n)}" + (f" -{markdown_text(path.relations[i])}->" if i < len(path.relations) else "")
        for i, n in enumerate(path.nodes)
    )
    weakest = f"；最弱一段：{markdown_text(path.weakest_link)}" if path.weakest_link else ""
    return f"- {chain}（{path.hops} 跳，信心＝最弱段 {path.confidence}{weakest}）"


def _section(title: str, meta: SectionMeta) -> list[str]:
    return [f"## {title}", ""] + _meta_lines(meta)


# ---------------------------------------------------------------------------
# 完整卡片
# ---------------------------------------------------------------------------

def render_alpha_investment_view_markdown(view: AlphaInvestmentView) -> str:
    ident = view.identity
    lines: list[str] = [
        f"# Alpha Card — {markdown_text(ident.company_label)}",
        "",
        _LEGEND,
        "",
        f"- 生成日：{ident.generated_on.isoformat()}｜視角：{ident.point_in_time_mode}"
        + (f"（as-of {ident.as_of.isoformat()}）" if ident.as_of else "（當前）"),
        f"- ResearchContext digest：`{ident.research_context_digest}`",
        f"- 行情幣別／報價單位：{markdown_text(ident.market_currency or '未知')}／"
        f"{markdown_text(ident.market_quote_unit or '未知')}｜交易所：{markdown_text(ident.execution_venue or '未知')}",
    ]
    sig = ident.signal
    if sig.has_signal:
        match = "一致" if sig.context_matches else "**不一致（判斷是對舊 context 做的）**"
        lines.append(
            f"- session 判斷：有（{markdown_text(sig.judged_at or '日期未知')}）｜完整度："
            f"{'incomplete' if sig.is_incomplete else 'complete'}｜已知維度 {len(sig.known_axes)}/5"
            f"｜最弱：{markdown_text(sig.weakest_axis or '—')}｜與目前 context {match}"
        )
    else:
        lines.append(f"- session 判斷：**無**——{markdown_text(sig.reason or '')}")
    lc = ident.lifecycle
    cohorts = f"｜cohort {lc.cohort_count} 個" if lc.cohort_count else ""
    lines.append(
        f"- Engine D：research_status {markdown_text(lc.research_status or '—')}｜lifecycle "
        f"{markdown_text(lc.lifecycle_status or '—')}｜複查到期 {markdown_text(lc.review_due_at or '—')}"
        f"｜舊五軸最弱 {markdown_text(lc.legacy_weakest_axis or '—')}{cohorts}"
        + (f"｜（{markdown_text(lc.reason)}）" if lc.reason else "")
    )
    lines.append(
        f"- Thesis lifecycle：{markdown_text(lc.thesis_lifecycle_status or '無 lane memo thesis')}"
        + (f"｜下次檢查 {lc.thesis_next_check.isoformat()}（{markdown_text(lc.thesis_next_check_source)}）"
           if lc.thesis_next_check else "")
    )
    for warning in ident.warnings:
        lines.append(f"- ⚠ {markdown_text(warning)}")
    lines.append("")

    # 0. 能力地圖
    lines += ["## 0. 能力地圖——知道什麼／還不知道什麼", "",
              "| section | 狀態 | 知識種類 | capability |", "|---|---|---|---|"]
    for name, cap in view.capability_map().items():
        lines.append(
            f"| {name} | {STATUS_LABEL.get(cap['status'] or '', cap['status'])} | "
            f"{BASIS_LABEL.get(cap['basis'] or '', cap['basis'])} | {markdown_text(cap['capability'] or '—')} |"
        )
    lines.append("")

    # 1. Variant view
    vv = view.variant_view
    lines += _section("1. Variant view（研究判斷：我們相信什麼、憑什麼）", vv.meta)
    for datum in (vv.thesis, vv.variant_view, vv.direction, vv.confidence, vv.expected_horizon):
        lines.append(_datum_line(datum))
    lines.append("- 五個維度（Q1 確定性、Q2–Q5 session 判斷；`None`＝不知道，不是 0）：")
    for datum in vv.scores:
        lines.append("  " + _datum_line(datum).replace("\n  - ", "\n    - "))
    if vv.risks:
        lines.append("- 風險（session 列）：")
        lines += [f"  - {markdown_text(r)}" for r in vv.risks]
    lines.append(_datum_line(vv.decision_store_variant_perception))
    lines.append("")

    # 2. Structural thesis
    st = view.structural_thesis
    lines += _section("2. 結構 thesis（Engine A：已入圖事實與 Q1）", st.meta)
    lines.append(_datum_line(st.structural_score))
    for datum in st.scarcity_inputs:
        lines.append(_datum_line(datum))
    for datum in st.ranking:
        lines.append(_datum_line(datum))
    lines.append(_datum_line(st.evidence_quality))
    if st.edges:
        lines += ["", "| 關係 | 對象 | 替代難度 | 獨家 | 認證 | 需求錨點／跳數 | 證據等級 | 用途 |",
                  "|---|---|---|---|---|---|---|---|"]
        for e in st.edges:
            lines.append(_edge_row(e))
    if st.supply_exposure:
        lines.append("")
        lines.append("供應鏈曝險（結構依賴，不是 ownership）：")
        lines += [f"- {x.direction}：{markdown_text(x.relation)} {markdown_text(x.counterparty)}"
                  f"（替代難度 {x.substitutability if x.substitutability is not None else '未填'}）"
                  for x in st.supply_exposure]
    if st.substitution_paths:
        lines.append("")
        lines.append("反證路徑（同一 chokepoint 的其他供應商——供應商計數不是瓶頸性證據）：")
        lines += [_path_line(p) for p in st.substitution_paths]
    lines.append("")
    lines.append("覆蓋限制：")
    lines += [f"- {markdown_text(c)}" for c in st.coverage_caveats]
    lines.append("")

    # 3. Causal
    cp = view.causal_paths
    lines += _section("3. 因果路徑（structural causal model，不是 financial causal model）", cp.meta)
    if cp.dependency_paths:
        lines.append("依賴路徑：")
        lines += [_path_line(p) for p in cp.dependency_paths]
    if cp.impacts_on_company:
        lines.append("結構事件對本公司的二階影響（derived，不入圖）：")
        lines += [_impact_line(i) for i in cp.impacts_on_company]
    if cp.structural_events:
        lines.append("本公司邊上的結構事件：")
        lines += [_event_line(e) for e in cp.structural_events]
    lines.append(_datum_line(cp.financial_causal_model))
    lines.append("")

    # 4. Fundamentals
    fd = view.fundamentals
    lines += _section("4. 財務觀測（Engine C；PIT／captured-at／provenance 保留）", fd.meta)
    lines += [_datum_line(d) for d in fd.items]
    lines.append(_datum_line(fd.segment_revenue_share))
    lines.append("- 五項核驗清單（客戶集中度／毛利率／backlog／稀釋／估值壓力）：")
    lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in fd.checklist]
    lines.append("")

    # 5. Consensus
    cs = view.consensus
    lines += _section("5. 共識（partial：只有今天真的存在的欄位）", cs.meta)
    lines.append(f"覆蓋範圍：{markdown_text(cs.coverage_note)}")
    lines += [_datum_line(d) for d in cs.items]
    if cs.fiscal_items:
        lines.append("會計年度別共識（身分是 fiscal_period_end；同期比較只用這些）：")
        lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in cs.fiscal_items]
    lines.append("")

    # 6. Price-implied
    pi = view.price_implied_expectations
    lines += _section("6. 價格隱含預期（heuristic／proxy，不是 reverse DCF）", pi.meta)
    lines += [_datum_line(d) for d in pi.items]
    lines.append(_datum_line(pi.reverse_dcf))
    lines.append("")

    # 7. Internal fundamentals
    inf = view.internal_fundamentals
    lines += _section("7. 內部基本面（Internal Fundamental View）", inf.meta)
    if inf.period:
        lines.append(
            f"目標期間：{markdown_text(inf.period)}"
            + (f"（至 {inf.period_end.isoformat()}）" if inf.period_end else "")
            + (f"｜基期至 {inf.base_period_end.isoformat()}" if inf.base_period_end else "")
            + (f"｜口徑 {markdown_text(inf.accounting_basis)}" if inf.accounting_basis else ""))
    lines += [_datum_line(d) for d in inf.items]
    lines.append(f"插座：{markdown_text(inf.plug_in_note)}")
    lines.append("")

    # 8. Earnings bridge
    eb = view.earnings_bridge
    lines += _section("8. Earnings bridge（structural event → operating assumptions → revenue／margin／EPS）", eb.meta)
    if eb.period:
        lines.append(f"目標期間：{markdown_text(eb.period)}")
    if eb.steps:
        lines.append("橋（由上而下；每格標 observation／assumption／derived）：")
        lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in eb.steps]
    if eb.assumptions:
        lines.append("生效的營運假設（每條各自標知識種類；它們不是事實）：")
        lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in eb.assumptions]
    if eb.selection is not None:
        sel = eb.selection
        lines.append(
            f"假設選取：input {sel.input_count}／accepted {sel.accepted_count}／filtered {sel.filtered_count}"
            f"（{_mapping_text(sel.reasons, None) or '無過濾'}）")
    if eb.sensitivities:
        lines.append("敏感度（每條假設動一格，輸出動多少；確定性微擾，不是機率）：")
        lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in eb.sensitivities]
    lines.append("今天已存在、可接進 bridge 的原料：")
    lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in eb.inputs_available]
    lines.append("")

    # 9. Expectation gap
    eg = view.expectation_gap
    lines += _section("9. Expectation gap（session 判斷／proxy／數值 gap 分開講）", eg.meta)
    lines.append(_datum_line(eg.session_judgment))
    lines += [_datum_line(d) for d in eg.proxies]
    lines.append(_datum_line(eg.internal_vs_consensus))
    if eg.numeric_comparisons:
        lines.append("逐指標（只在同期、同口徑、同幣別時有數字）：")
        lines += ["  " + _datum_line(d).replace("\n  - ", "\n    - ") for d in eg.numeric_comparisons]
    lines.append(_datum_line(eg.internal_vs_price_implied))
    lines.append("")

    # 10. Catalysts
    ct = view.catalysts
    lines += _section("10. 催化劑", ct.meta)
    lines.append(_datum_line(ct.catalyst_score))
    if ct.structured:
        lines.append("結構化催化劑（session 判斷）：")
        lines += [_catalyst_line(c) for c in ct.structured]
    if ct.checkpoints:
        lines.append("結構化檢核點（thesis lifecycle／catalyst calendar）：")
        lines += [_checkpoint_line(c) for c in ct.checkpoints]
    lines.append(_datum_line(ct.narrative))
    lines.append(_datum_line(ct.watch_state))
    lines.append(_datum_line(ct.expiry))
    for problem in ct.problems:
        lines.append(f"- ⚠ 設定問題：{markdown_text(problem)}")
    lines.append(_datum_line(ct.quantitative_link))
    lines.append("")

    # 11. Falsification
    fs = view.falsification
    lines += _section("11. 證偽條件（進場靠判斷，出場靠 disproof）", fs.meta)
    if fs.conditions:
        lines += [_disproof_line(d) for d in fs.conditions]
    lines.append(_datum_line(fs.narrative_disproof))
    lines.append(_datum_line(fs.thesis_status))
    lines.append(_datum_line(fs.expiry_watch))
    lines.append(_datum_line(fs.automatic_invalidation))
    lines.append("")

    # 12. Scenarios
    sc = view.scenarios
    lines += _section(f"12. 情境（scenario_type={sc.scenario_type}）", sc.meta)
    for datum in (sc.bull, sc.base, sc.bear, sc.probabilities, sc.target_valuation):
        lines.append(_datum_line(datum))
    lines.append("")

    # 13. Not modeled trio
    for title, section in (("13a. 預期報酬", view.expected_return),
                           ("13b. 下檔", view.downside),
                           ("13c. 進場邏輯／可行動性", view.entry_logic)):
        lines += _section(title, section.meta)
        lines += [_datum_line(d) for d in section.items]
        lines.append("不要跟這些混淆：")
        lines += [f"- {markdown_text(x)}" for x in section.not_to_be_confused_with]
        lines.append("")

    # 14. Evidence
    ev = view.evidence
    lines += _section("14. 證據與 provenance", ev.meta)
    sel = ev.selection
    lines.append(
        f"- as-of 篩選：input {sel.input_count}／accepted {sel.accepted_count}／filtered {sel.filtered_count}"
        f"（{_mapping_text(sel.reasons, None)}）"
    )
    lines.append(_datum_line(ev.quality))
    lines += ["", "| ref | kind | 來源文件 | origin | tier | class | 發表日 | 取得日 |",
              "|---|---|---|---|---|---|---|---|"]
    for item in ev.index:
        lines.append(
            f"| `{item.ref}` | {markdown_text(item.kind)} | {markdown_text(item.source_doc_id or '—')} | "
            f"{markdown_text(item.origin_entity or '—')} | {item.evidence_tier if item.evidence_tier is not None else '—'} | "
            f"{markdown_text(item.evidence_class or '—')} | {item.published_at.isoformat() if item.published_at else '—'} | "
            f"{item.retrieved_at.isoformat() if item.retrieved_at else '—'} |"
        )
    lines.append("")

    # 15. Freshness ＋ warnings
    lines += ["## 15. 新鮮度總表", "", "| 來源 | 狀態 | as-of | 幾天前 | 註 |", "|---|---|---|---|---|"]
    for fr in view.freshness:
        age = "—" if fr.age_days is None else f"{fr.age_days:.0f}"
        lines.append(f"| {markdown_text(fr.source)} | {markdown_text(fr.status)} | "
                     f"{fr.as_of.isoformat() if fr.as_of else '—'} | {age} | {markdown_text(fr.reason or '')} |")
    lines += ["", "## ⚠ 警告", ""]
    lines += [f"- {markdown_text(w)}" for w in view.warnings]
    return "\n".join(lines)


def _edge_row(e: StructuralEdgeItem) -> str:
    def _cell(value: Any) -> str:
        if value is None:
            return "未填"
        if isinstance(value, bool):
            return "是" if value else "否"
        return markdown_text(value)

    anchor = f"{_cell(e.demand_anchor)}／{_cell(e.demand_hops)}"
    return (f"| {markdown_text(e.relation)} | {markdown_text(e.target)} | {_cell(e.substitutability)} | "
            f"{_cell(e.sole_source)} | {_cell(e.qualification_status)} | {anchor} | "
            f"{_cell(e.evidence_class)} | {markdown_text(e.purpose)} |")


def _impact_line(i: ImpactItem) -> str:
    when = i.observed_at.isoformat() if i.observed_at else "日期未知"
    return (f"- {markdown_text(i.event_kind or '事件')}（{markdown_text(i.event_direction or '?')}）"
            f"於 {markdown_text(i.subject or '?')}，{when} → 本公司 **{i.impact_direction}**"
            f"｜magnitude {i.magnitude}｜horizon {i.time_horizon}｜confidence {i.confidence}"
            f"\n  - 路徑：{' → '.join(markdown_text(n) for n in i.path.nodes)}"
            f"\n  - {markdown_text(i.rationale)}")


def _event_line(e: EventItem) -> str:
    return (f"- {e.observed_at.isoformat()} {markdown_text(e.kind)}／{markdown_text(e.direction)} "
            f"@ {markdown_text(e.subject)}：{markdown_text(e.description)}")


def _catalyst_line(c: CatalystItem) -> str:
    when = c.expected_at.isoformat() if c.expected_at else "日期未知"
    return (f"- {markdown_text(c.kind)}：{markdown_text(c.description)}（{when}，"
            f"date_confidence={c.date_confidence}）〔{BASIS_LABEL.get(c.basis, c.basis)}〕")


def _checkpoint_line(c: CheckpointItem) -> str:
    mark = "" if c.date_confidence == "confirmed" else "（推估）"
    decides = f" — 裁決：{markdown_text(c.decides)}" if c.decides else ""
    return f"- {c.date.isoformat()}{mark} {markdown_text(c.what)}{decides}〔`{c.source}`〕"


def _disproof_line(d: DisproofItem) -> str:
    return (f"- {markdown_text(d.condition)}｜核查 {markdown_text(d.check_frequency)}｜"
            f"48h：{markdown_text(d.action_within_48h)}〔{BASIS_LABEL.get(d.basis, d.basis)}〕")


# ---------------------------------------------------------------------------
# Daily Brief 的精簡摘要
# ---------------------------------------------------------------------------

_CARD_HEAD = [
    "| 標的 | Q1 結構 | Q2／Q3／Q4／Q5（session） | 市場隱含 EPS 成長 | 共識營收成長 | 內部 vs 共識 EPS（同期） | 催化劑／到期 | Disproof | 尚未建模 |",
    "|---|---|---|---|---|---|---|---|---|",
]


def _internal_gap_cell(card: Mapping[str, Any]) -> str:
    """內部假設推出的 EPS vs 同期共識。只看 builder 給的 status；缺席印原因，不印 0。"""
    block = card.get("internal_vs_consensus")
    if not isinstance(block, Mapping):
        return "未提供"
    eps = block.get("eps")
    if not isinstance(eps, Mapping):
        return "未知"
    if eps.get("status") == "available" and isinstance(eps.get("relative_gap"), (int, float)):
        text = f"{_pct(eps['relative_gap'])}"
        if eps.get("period"):
            text += f"（{markdown_text(eps['period'])}）"
        return text
    return f"未知（{markdown_text(eps.get('reason') or eps.get('status') or '—')}）"


def _score_cell(score: Mapping[str, Any]) -> str:
    if score.get("status") in ("available", "stale"):
        level = score.get("session_level")
        eff = score.get("effective")
        text = f"{eff:.2f}" if isinstance(eff, (int, float)) else "—"
        if level:
            text += f"（{markdown_text(level)}）"
        if score.get("status") == "stale":
            text += "⌛"
        return text
    return "未知"


def _card_row(card: Mapping[str, Any]) -> str:
    if card.get("status") == "unavailable":
        return (f"| {markdown_text(card.get('ticker') or '?')} | 讀不到 | 讀不到 | 讀不到 | 讀不到 | 讀不到 | 讀不到 | 讀不到 | "
                f"（{markdown_text(card.get('reason') or 'unavailable')}） |")
    scores = card.get("scores") or {}
    q1 = _score_cell(scores.get("structural") or {})
    others = "／".join(_score_cell(scores.get(a) or {})
                      for a in ("value_capture", "earnings_exposure", "expectation_gap", "catalyst"))
    # 每一格只看 builder 給的 status；不用「值在不在」反推缺席（那是 renderer 端的語意回復）。
    implied = card.get("market_implied_eps_growth") or {}
    if implied.get("status") in ("available", "stale") and isinstance(implied.get("value"), (int, float)):
        implied_text = f"{_pct(implied['value'])}（proxy）" + ("⌛" if implied.get("status") == "stale" else "")
    else:
        implied_text = f"未知（{markdown_text(implied.get('reason') or implied.get('status') or '—')}）"
    cons = card.get("consensus_revenue_growth") or {}
    n = cons.get("analyst_count")
    if cons.get("status") in ("available", "stale") and isinstance(cons.get("value"), (int, float)):
        cons_text = f"{_pct(cons['value'])}" + (f"（{n} 位）" if isinstance(n, int) else "")
    else:
        cons_text = f"未知（{markdown_text(cons.get('status') or '—')}）"
    cat = card.get("catalyst") or {}
    cat_text = markdown_text(cat.get("state_label") or ("未知" if not cat.get("state") else cat["state"]))
    if cat.get("next_checkpoint"):
        cat_text += f"｜下個 {cat['next_checkpoint']}" + ("（推估）" if cat.get("next_checkpoint_confidence") != "confirmed" else "")
    elif not cat.get("state"):
        cat_text = f"未知（{markdown_text(cat.get('reason') or '—')}）"
    dis = card.get("disproof") or {}
    signal = card.get("signal") or {}
    # 只查值：`condition_count` 是 None 代表 builder 已判定「不知道」（無判斷／無投影），
    # renderer 不自己用 has_signal 再解讀一次。
    count = dis.get("condition_count")
    dis_text = f"{count} 條結構化" if isinstance(count, int) else "結構化：未知"
    dis_text += "＋散文" if dis.get("narrative_present") else "；散文：無"
    if dis.get("problems"):
        dis_text += f"｜⚠ 設定問題 {len(dis['problems'])}"
    label = markdown_text(card.get("company_label") or card.get("ticker") or "?")
    if signal.get("has_signal") and signal.get("context_matches") is False:
        label += "（判斷過期⌛）"
    elif not signal.get("has_signal"):
        label += "（無 session 判斷）"
    nm = card.get("not_modeled") or []
    nm_text = f"{len(nm)} 區" if nm else "—"
    gap_text = _internal_gap_cell(card)
    return (f"| {label} | {q1} | {others} | {implied_text} | {cons_text} | {gap_text} | {cat_text} | "
            f"{dis_text} | {nm_text} |")


def render_alpha_cards(cards: Sequence[Mapping[str, Any]] | None, *, present: bool = True) -> list[str]:
    """Daily Brief 的「Alpha Card 摘要」區。

    - `present=False`（DTO 沒這個欄位，舊 surface）→ 整區不渲染。
    - `None`（呼叫端未注入）→ 渲染「未提供」，**不與**空 list 混用（L12）。
    - `[]` → 「無候選可摘要」。
    """
    if not present:
        return []
    lines = ["## Alpha Card 摘要（每檔一列；完整卡：`python -m briefing alpha-card <TICKER>`）", ""]
    if cards is None:
        lines += ["⚠ 本次未提供 Alpha Card 摘要（這個 surface 未注入，或整批讀取失敗）——不是「沒有候選」。", ""]
        return lines
    if not cards:
        lines += ["（無候選可摘要）", ""]
        return lines
    lines += _CARD_HEAD
    lines += [_card_row(card) for card in cards]
    lines += [
        "",
        "- 讀法：Q1 是確定性規則；Q2–Q5 是 session 判斷（括號內為 session 等級）；⌛＝判斷是對舊 context 做的；"
        "「未知」是不知道，不是 0。",
        "- 市場隱含 EPS 成長是 trailing／forward PE 的粗略代理，與共識**營收**成長分母不同，不得相減。",
        "- 「內部 vs 共識 EPS」是明示營運假設（session 判斷／heuristic）經確定性橋算出的 EPS 與**同期、同口徑**共識的相對差；"
        "假設不是事實，數字不是 Q4；不可比或缺料一律「未知」。",
        "- 「尚未建模」列的是 expected return／downside／entry logic 等系統還沒有的能力。",
        "",
    ]
    return lines
