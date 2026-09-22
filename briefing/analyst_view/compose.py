"""`AlphaInvestmentView` → `AnalystView`：**依消費者問句重新投影**，不重算任何東西。

## 這一支做什麼

`AlphaInvestmentView` 依資料結構排列；本模組把同一批 `Datum` **重新分組、重新排序、
換上面向讀者的標籤**，讓打開一檔股票的人依序讀到消費者問句的答案。

⚠ **2026-09-23（Phase 0 Step 0b.1）：`why` 與 `entry` 兩個 panel 退役、`headline` 換主詞。**
`why` 只吃估值鏈三個 section（1,910 行全是 assumption／sensitivity／trace／epistemics，零行敘事），
它問的「怎麼算到這裡」已隨估值鏈退役；`entry` 73 檔全 missing，從未用過。
`headline` 原本是「現價 → future target value → 隱含報酬」，**那正是 AGENTS 說要拿掉的那把尺**
——現在它只答「現在多少錢」（現價＋價格脈絡，73/73 檔有值），不答「划不划算」。
在答「憑什麼」的是 `argument`，所以它與短評、歸零旗標一起升為核心面板。

## 這一支絕不做的事（`tests/test_analyst_view.py` 守著）

- **不新建任何 `Datum`。** panel 裡每一行的 `datum` 都是 read model 裡**同一個物件**（`is` 相等）。
  想在這裡「補一格」就必須先去 authority 補，這正是我們要的阻力。
- **沒有公式、沒有算術。** 全檔唯一的數值運算是排序鍵 `abs(既有敏感度)`——它不產生新值。
- **不判斷好壞。** `worst_status`／`readiness_class` 是宣告好的查表（`contracts.py`），
  這裡只呼叫它們。
- **不呼叫 LLM、不連 DB、不寫檔。** import 清單是這個承諾的可執行形式。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from briefing.alpha_view.contracts import (
    VALUELESS_STATUSES, AlphaInvestmentView, Datum, EvidenceItem, RefreshItem,
)

from .contracts import (
    BLOCKED, CORE_PANELS, OPTIONAL_PANELS, READY, READY_WITH_FLAGS, SCHEMA_VERSION, AnalystBlocker,
    AnalystLine, AnalystPanel, AnalystReadiness, AnalystView, RefreshSummary,
    readiness_class, worst_status,
)

#: refresh 引擎標成這些 state 的成果＝「還有事要做」。`current`／`superseded`／`missing` 不在此列
#: （`missing` 在這裡代表「這個視角下還沒建立」，由各 panel 自己的 status 表達，不重複告警）。
ATTENTION_STATES = ("recalculate", "review_required", "invalidated", "stale")

#: 直接餵進頭條那一格的成果種類——headline panel 只列這些的 attention，避免把整份 refresh 倒進頭條。
#: ⚠ 2026-09-23（Step 0b.1）：原本是 implied_return／fair_value／fair_value_gap／
#: horizon_assumption／valuation_assumption 五種，全部隨估值鏈退役。headline 現在只有現價，
#: 它的新鮮度由 `market` 成果表達。
HEADLINE_ARTIFACTS = ("market",)



def _absence_kinds(**metas: Any) -> dict[str, str | None]:
    """每個來源 section 的缺席語意——**照抄 `SectionMeta.effective_absence_kind`，不推論**。"""
    return {name: meta.effective_absence_kind for name, meta in metas.items()}


def _settled_by(**metas: Any) -> dict[str, str | None]:
    """每個來源 section 的 `settled_by`（`ab_*`）——同樣照抄，不推論（2026-09-13）。"""
    return {name: getattr(meta, "settled_by", None) for name, meta in metas.items()}


def _worst_reason(status: str, **metas: Any) -> str | None:
    """panel 的 reason 要來自**造成這個 status 的那一段**，不是固定綁某一段。

    事發（2026-09-13，HEXA-B.ST）：`earnings_bridge` 算成功、`valuation` 缺 target multiple，
    於是 `why` panel 的 status 是 `missing`（取三段最差）而 reason 取自 earnings_bridge ＝ `None`。
    使用者端看到的是「why：missing」沒有下文，而 `absence_kind` 明明宣告了 `not_yet_recorded`。
    ⚠ 這正是 `AGENTS.md` APP 呈現契約禁的形狀：**缺席由產生它的那段程式自己宣告**——
    固定取第一段等於讓 A 段替 B 段的缺席發言，而 A 段根本沒有缺席。
    ⚠ 這**不是**放寬：status 一個字都沒動，改的只是「這句話由誰說」（L12：先分開再各自定規則）。
    fallback 保留舊行為（任一段有 reason 就用它），因為「沒有任何理由」與「理由在別段」不同。
    """
    for meta in metas.values():
        if meta.status == status and meta.reason:
            return meta.reason
    for meta in metas.values():
        if meta.reason:
            return meta.reason
    return None


def _line(key: str, label: str, datum: Datum, role: str) -> AnalystLine:
    return AnalystLine(key=key, display_label=label, datum=datum, role=role)


def _lines(data: Iterable[Datum], role: str, *, prefix: str = "") -> tuple[AnalystLine, ...]:
    """一批既有 `Datum` 直接變成一批行；標籤沿用 `Datum.label`（authority 已經寫好的說法）。"""
    return tuple(_line(f"{prefix}{d.key}", d.label, d, role) for d in data)


def _attention(view: AlphaInvestmentView, *, artifact_types: Sequence[str] | None = None
               ) -> tuple[RefreshItem, ...]:
    """需要動作的研究成果。`artifact_types` 給定時只留那幾種——這是**篩選**，不是重新判定 state。"""
    items = [i for i in view.refresh_status.items if i.state in ATTENTION_STATES]
    if artifact_types is not None:
        items = [i for i in items if i.artifact_type in artifact_types]
    return tuple(items)


def _evidence_for(view: AlphaInvestmentView, data: Iterable[Datum]) -> tuple[EvidenceItem, ...]:
    """這些格引用到的證據（依 evidence index 的原順序）。純查表，不重新評級。"""
    wanted: set[str] = set()
    for datum in data:
        wanted.update(datum.evidence_refs)
    return tuple(item for item in view.evidence.index if item.ref in wanted)


# ---------------------------------------------------------------------------
# 脆弱輸入：每一條都由一條**宣告好的列入規則**挑進來（見 `WEAK_INPUT_RULES`）
# ---------------------------------------------------------------------------

def _headline_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """現在多少錢（核心）：現價與價格脈絡。**沒有目標價、沒有隱含報酬。**

    ⚠ 2026-09-23（Phase 0 Step 0b.1）：這個 panel 原本是「現價 → future target value → 隱含報酬」
    共 8 格數字加 7 格脈絡，全部來自 `implied_return` 與 `valuation` 兩個 section。
    **那就是 AGENTS「首屏拿掉尺」指的那把尺**（現價／沒賭對／賭對／判斷錯了）。
    現在它只持有一個 `Datum`：現價。它是 A2 觀測（Engine C 快照），不是判斷、不是模型輸出。

    「已定價嗎」這個問題沒有消失，它換了答法：財務三題的第二題，主參照是自己的歷史百分位、
    主題籃子只當脈絡、**不設門檻**（Phase 3 落地）。在那之前這個 panel 不假裝回答它。
    """
    price = view.market.price
    rs = view.refresh_status
    lines = (_line("current_price", "現價", price, "headline_number"),)
    # status 直接取現價那一格自己的：它有值就 available，沒值就照它自己的缺席語意。
    # **不取 section 的 meta**——估值 section 的 status 反映的是估值算不算得出來，那與現價無關。
    # status 照抄 market section 的 meta——**不自己判**（測試逐 panel 驗這條）。
    status = view.market.meta.status
    return AnalystPanel(
        key="headline", title="現在多少錢：現價與價格脈絡",
        questions=(),
        status=status, optional=False,
        source_sections=("market",),
        source_statuses={"market": status},
        source_absence_kinds=_absence_kinds(market=view.market.meta),
        lines=lines,
        attention=_attention(view, artifact_types=HEADLINE_ARTIFACTS),
        attention_scope="只列現價自己的成果（" + "、".join(HEADLINE_ARTIFACTS) + "）",
        attention_total=len(_attention(view)),
        notes=(
            "這一格是 A2 觀測（Engine C 現價快照），不是判斷。",
            "**沒有目標價、沒有隱含報酬、沒有那把尺**——2026-09-23 Phase 0 退役；"
            "「已定價嗎」由財務三題回答（Phase 3），主參照是自己的歷史、不設門檻。",
        ),
        context={"quote_unit": (price.dependencies or {}).get("quote_unit") if price.dependencies else None,
                 "refresh_overall": rs.overall, "refresh_counts": dict(rs.counts)},
        reason=price.reason,
    )


def _fundamental_panel(view: AlphaInvestmentView) -> AnalystPanel:
    inf, cs, eg = view.internal_fundamentals, view.consensus, view.expectation_gap
    same_period_suffix = f"_{inf.period}" if inf.period else None
    same, other = [], []
    for datum in cs.fiscal_items:
        (same if same_period_suffix and datum.key.endswith(same_period_suffix) else other).append(datum)
    lines = (
        _lines(inf.items, "internal")
        + _lines(same, "consensus_same_period")
        + _lines(other, "consensus_other_period")
        + _lines(cs.items, "market_context")
        + _lines(eg.proxies, "market_proxy")
        + _lines(eg.numeric_comparisons, "comparison")
        + ((_line("opinion_stance", eg.opinion_stance.label, eg.opinion_stance, "comparison"),)
           if eg.opinion_stance is not None else ())
        + ((_line("multiple_derivation", eg.multiple_derivation.label,
                  eg.multiple_derivation, "comparison"),)
           if eg.multiple_derivation is not None else ())
        + ((_line("gap_closure", eg.gap_closure.label, eg.gap_closure, "comparison"),)
           if eg.gap_closure is not None else ())
        + ((_line("consensus_series", eg.consensus_series.label, eg.consensus_series, "market_context"),)
           if eg.consensus_series is not None else ())
        + (_line("internal_vs_consensus", eg.internal_vs_consensus.label, eg.internal_vs_consensus, "comparison"),
           _line("internal_vs_price_implied", eg.internal_vs_price_implied.label,
                 eg.internal_vs_price_implied, "comparison"))
    )
    statuses = {"internal_fundamentals": inf.meta.status, "consensus": cs.meta.status,
                "expectation_gap": eg.meta.status}
    kinds = _absence_kinds(internal_fundamentals=inf.meta, consensus=cs.meta, expectation_gap=eg.meta)
    return AnalystPanel(
        key="fundamental", title="基本面：我們預測什麼／市場預測什麼／差異在哪（選配）",
        questions=("q1_internal", "q2_market", "q3_gap"),
        # ⚠ 2026-09-23（Phase 0 Step 0b.1）：由核心**降為選配**（ROADMAP 稽核區：原始數字）。
        # 它回答的是「數字長什麼樣」，不是「判讀完不完整」。
        status=worst_status(list(statuses.values())), optional=True,
        source_sections=("internal_fundamentals", "consensus", "expectation_gap"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        # ⚠ 共識段的 warnings 也要進來：「forward 是相對標籤不是會計年度身分」這條警告
        # 正是 2026-09-07 rollover 污染事故的判準，藏在 section 裡等於沒有（INV-3）。
        notes=(cs.coverage_note,) + inf.meta.warnings + cs.meta.warnings,
        context={"period": inf.period, "period_end": inf.period_end,
                 "base_period_end": inf.base_period_end, "accounting_basis": inf.accounting_basis,
                 "same_period_rule": "只有同期、同口徑、同幣別的共識才與內部相減；其他期間只呈現，不比較"},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             expectation_gap=eg.meta, internal_fundamentals=inf.meta,
                             consensus=cs.meta),
    )


def _research_panel(view: AlphaInvestmentView) -> AnalystPanel:
    vv, fs, ct, rs = view.variant_view, view.falsification, view.catalysts, view.refresh_status
    signal = view.identity.signal
    lines = (
        (_line("thesis", "Thesis", vv.thesis, "thesis"),
         _line("variant_view", "Variant view（我們與市場的看法差在哪）", vv.variant_view, "thesis"),
         _line("direction", "方向", vv.direction, "thesis"),
         _line("confidence", "信心", vv.confidence, "thesis"),
         _line("expected_horizon", "研究判斷的預期期間", vv.expected_horizon, "thesis"),
         _line("decision_store_variant_perception", vv.decision_store_variant_perception.label,
               vv.decision_store_variant_perception, "thesis"))
        + _lines(vv.scores, "score")
        + (_line("thesis_status", "Thesis lifecycle", fs.thesis_status, "lifecycle"),
           _line("expiry_watch", "到期監看", fs.expiry_watch, "lifecycle"),
           _line("narrative_disproof", fs.narrative_disproof.label, fs.narrative_disproof, "lifecycle"),
           _line("automatic_invalidation", fs.automatic_invalidation.label,
                 fs.automatic_invalidation, "lifecycle"),
           _line("catalyst_watch_state", ct.watch_state.label, ct.watch_state, "lifecycle"),
           _line("catalyst_expiry", ct.expiry.label, ct.expiry, "lifecycle"),
           _line("catalyst_quantitative_link", ct.quantitative_link.label, ct.quantitative_link, "lifecycle"),
           _line("catalyst_shape", ct.shape.label, ct.shape, "lifecycle"))
    )
    statuses = {"variant_view": vv.meta.status, "falsification": fs.meta.status,
                "catalysts": ct.meta.status, "refresh_status": rs.meta.status}
    kinds = _absence_kinds(variant_view=vv.meta, falsification=fs.meta, catalysts=ct.meta,
                           refresh_status=rs.meta)
    return AnalystPanel(
        key="research", title="研究現況：thesis、催化劑、什麼會推翻它、什麼需要重看",
        questions=("q6_change",),
        status=worst_status(list(statuses.values())), optional=False,
        source_sections=("variant_view", "falsification", "catalysts", "refresh_status"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        catalysts=ct.structured, checkpoints=ct.checkpoints, disproofs=fs.conditions,
        attention=_attention(view), attention_total=len(_attention(view)), risks=vv.risks,
        notes=tuple(ct.problems) + tuple(rs.notes),
        context={"has_signal": signal.has_signal, "judged_at": signal.judged_at,
                 "is_incomplete": signal.is_incomplete, "known_axes": list(signal.known_axes),
                 "weakest_axis": signal.weakest_axis, "context_matches": signal.context_matches,
                 "signal_refresh_state": signal.refresh_state,
                 "research_status": view.identity.lifecycle.research_status,
                 "thesis_lifecycle_status": view.identity.lifecycle.thesis_lifecycle_status,
                 "thesis_next_check": view.identity.lifecycle.thesis_next_check},
        reason=_worst_reason(worst_status(list(statuses.values())),
                             variant_view=vv.meta, falsification=fs.meta,
                             catalysts=ct.meta, refresh_status=rs.meta),
    )


def _brief_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """投資人短評（optional）：七句＋一把尺＋一顆燈＋（有寫倍率射程時）一句「要翻倍需要什麼為真」。

    **每一格都是 read model 的同一個 Datum**。2026-09-20 起多一句：它**只在這一檔寫下了
    `multiple_horizon` 時才存在**——沒寫就沒有那一行（不是印「還沒寫」；71/73 檔都沒寫，
    逐檔印是噪音，全體缺口由心跳段 4 的常駐計數器負責）。
    """
    ib = view.investor_brief
    # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`brief_scale`（那把尺）與 `brief_multiple_question`
    # （要翻倍需要什麼為真）兩行退役。** 尺上是現價／沒賭對／賭對／判斷錯了，ROADMAP 首屏那一列
    # 明文「拿掉」；要翻倍那一句讀多年反向橋（D 組）。首屏剩下的是七句話與一顆狀態燈。
    lines = (tuple(_line(d.key, d.label, d, "brief") for d in ib.slots)
             + (_line("brief_status_light", ib.status_light.label, ib.status_light, "brief"),))
    return AnalystPanel(
        key="brief", title="投資人短評：這檔在賭什麼",
        questions=("q0_story",),
        # ⚠ 2026-09-23（Phase 0 Step 0b.1）：升為**核心**（ROADMAP「首屏的單位是句不是格」）。
        # 實測 70/73 檔還沒寫短評，所以升核心會讓 blocked 由 18 變 70——**那是真實 backlog
        # 不是規則錯**：新方向下沒有短評的檔就是沒有產出（AGENTS「產出若無法讓人分辨做了什麼
        # 與沒做，它就不算產出」）。缺席語意是 `not_yet_recorded`（不是 settled），所以它會一直
        # 出現在 forward_view_backlog 裡直到有人寫。
        status=ib.meta.status, optional=False,
        source_sections=("investor_brief",), source_statuses={"investor_brief": ib.meta.status},
        source_absence_kinds=_absence_kinds(investor_brief=ib.meta),
        lines=lines, notes=ib.is_not,
        evidence=_evidence_for(view, ib.slots),
        context={"capability": ib.meta.capability, "brief_id": ib.brief_id,
                 "available": ib.meta.status not in VALUELESS_STATUSES,
                 "optional_rule": "短評是 optional：沒寫只表示「還沒寫短評」，不代表這檔研究不完整；"
                                  "文字是研究 session 的判斷（append-only），數字由既有 Datum 填入，不得手打"},
        reason=ib.meta.reason,
    )


def _argument_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """論證層（optional）：六段。**每一格都是 read model 的同一個 Datum**，本層不造句。"""
    ag = view.argument
    lines = tuple(_line(d.key, d.label, d, "paragraph") for d in ag.paragraphs)
    return AnalystPanel(
        key="argument", title="為什麼這樣想：鏈、賭注、風險與認錯條件、時間表",
        questions=("q0_argument",),
        # ⚠ 2026-09-23（Phase 0 Step 0b.1）：由 optional 升為**核心**。它是在答「憑什麼」的面板，
        # 73/73 檔都有內容（實測 438 段）；原本站在核心位的 `why` 答的是「估值怎麼算」，已退役。
        status=ag.meta.status, optional=False,
        source_sections=("argument",), source_statuses={"argument": ag.meta.status},
        source_absence_kinds=_absence_kinds(argument=ag.meta),
        lines=lines, notes=ag.is_not,
        evidence=_evidence_for(view, ag.paragraphs),
        context={"capability": ag.meta.capability, "available": ag.meta.status not in VALUELESS_STATUSES,
                 "optional_rule": "論證層是投影：算術與圖的敘述由句型組、判斷的長文照抄；沒有它不影響判讀完不完整"},
        reason=ag.meta.reason,
    )


# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`_overlay_panel`（賭注／下檔共用的四價 lines）隨 E 組退役。


def _bet_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """賭注（optional）：**純文字**。2026-09-23（Phase 0 Step 0b.1）由四個價格改成一句話。

    原本這裡是 11 格數字（賭注目標價、報酬、年化、EPS 貢獻、倍數貢獻、base 對照…）＋ overrides。
    ROADMAP「個股頁」對照表把它們列進「拿掉」：`bet` 的四個價格退役，改成
    **型別、騎層或插槽、什麼必須為真**——那是文字，不是價格。

    今天能照抄的文字只有短評裡的 `our_bet`（研究 session 寫進 append-only ledger 的那一句）。
    「騎層或插槽」要等 Phase 2 的讀圖 kind 才有主詞，所以**現在不假裝有**：沒寫 `our_bet`
    就是 `not_yet_recorded`，不是 0、不是空白。**本層一個字都不造**（`our_bet` 是同一個 Datum）。
    """
    ib = view.investor_brief
    our_bet = next((d for d in ib.slots if d.key.endswith("our_bet")), None)
    lines = (_line("our_bet", "我們賭什麼（研究 session 寫下的那一句）", our_bet, "bet"),) if our_bet else ()
    status = ("available" if (our_bet is not None and our_bet.is_known)
              else ((our_bet.status if our_bet is not None else None) or "missing"))
    return AnalystPanel(
        key="bet", title="賭注：我們賭什麼（純文字，optional）",
        questions=(),
        status=status, optional=True,
        source_sections=("investor_brief",),
        source_statuses={"investor_brief": status},
        source_absence_kinds={"investor_brief": (our_bet.absence_kind if our_bet is not None else "not_yet_recorded")},
        lines=lines,
        notes=(
            "**沒有價格、沒有報酬、沒有機率加權**——四個價格已於 2026-09-23 Phase 0 退役。",
            "「騎哪一層或哪一個插槽」「什麼必須為真」要等 Phase 2 的讀圖落地才有主詞；"
            "在那之前這裡只有研究 session 寫下的那一句。",
        ),
        context={"available": status not in VALUELESS_STATUSES,
                 "optional_rule": "沒寫賭注只表示「還沒寫」，不代表這檔研究不完整；"
                                  "文字是研究判斷（append-only ledger），本層照抄不造句"},
        reason=(our_bet.reason if our_bet is not None else "短評裡沒有 our_bet 這一格"),
    )


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`_downside_panel` 退役（E 組）。**
# 「判斷錯了值多少」原本是四個價格。反證那一端沒有退役——它在 `research` 面板的 disproofs，
# 而 Phase 3 會讓每條反證連到一個 watch。


def _wipeout_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """歸零旗標（optional，D2 2026-09-18）：四盞燈逐盞一行。

    ⚠ 這個 panel **一個顏色都不判**——顏色、理由句、規則與輸入全部照抄 `alpha.wipeout`
    經由 read model 帶過來的 `Datum`。呈現層自己判色就會立刻長出第二套規則（L16）。
    """
    wf = view.wipeout_flags
    lines = _lines(wf.lanes, "wipeout")
    return AnalystPanel(
        # ⚠ 2026-09-23（Phase 0 Step 0b.1）：升為**核心**。AGENTS「量測、訊號、脈絡三分」把歸零旗標
        # 列為**量測**，而量測缺席不該被讀成「沒事」——灰燈不是綠燈。實測 3/73 檔還點不亮。
        key="wipeout", title="會不會歸零：四盞燈",
        questions=(),
        status=wf.meta.status, optional=False,
        source_sections=("wipeout_flags",), source_statuses={"wipeout_flags": wf.meta.status},
        source_absence_kinds=_absence_kinds(wipeout_flags=wf.meta),
        lines=lines, notes=wf.is_not,
        context={"capability": wf.meta.capability, "tally": dict(wf.tally),
                 "available": wf.meta.status not in VALUELESS_STATUSES,
                 "unlit_rule": "灰燈＝這一項沒量到，**不是**綠燈；每盞灰燈自己說了是哪一種沒有"
                               "（`absence_kind`），呈現層不得 parse 理由句去猜（L16）"},
        reason=wf.meta.reason,
    )


# ---------------------------------------------------------------------------
# readiness ＋ 整份 view
# ---------------------------------------------------------------------------

# ⚠ 兩份清單都**讀 SSOT**，不手寫（L16：分類有 SSOT 時要讓它跟著資料走）。
# 事發（2026-09-18）：這句話原本把 optional 逐字寫成「brief／argument／bet／entry」，
# 而 `OPTIONAL_PANELS` 在 D2 那輪就已經多了 `downside`——**畫面上少印一個 panel 名，
# 沒有任何東西會變紅**，它只是安靜地說了一句假話。
_READINESS_RULE = (
    f"只看核心 panel（{'／'.join(CORE_PANELS)}）："
    "全部有內容（available／partial）＝ready；"
    "有內容但至少一段被標為 stale／review_required／not_applicable＝ready_with_flags；"
    "至少一段缺內容（missing／invalidated／not_modeled／insufficient_evidence）＝blocked。"
    f"**optional panel（{'／'.join(OPTIONAL_PANELS)}）一律不參與**"
    "——沒有賭注、沒有下檔、沒有稽核區的基本面數字都不會讓 readiness 變差。"
    "⚠ 2026-09-23（Phase 0 Step 0b.1）：**短評與歸零旗標改為核心**，所以它們缺席會讓 readiness 變差"
    "——那是刻意的：新方向下沒寫短評的檔就是沒有產出，沒量到的燈不是綠燈。"
)


def _readiness(panels: Mapping[str, AnalystPanel]) -> AnalystReadiness:
    flags: list[str] = []
    blockers: list[str] = []
    blocker_details: list[AnalystBlocker] = []
    flag_details: list[AnalystBlocker] = []
    for name in CORE_PANELS:
        panel = panels[name]
        bucket = readiness_class(panel.status)
        detail = f"{name}：{panel.status}" + (f"（{panel.reason}）" if panel.reason else "")
        # 同一件事的兩種形式：字串給人讀，`AnalystBlocker` 給機器讀。**不是兩份判斷**——
        # 兩者都由同一個迴圈、同一個 bucket 決定，長度不同會在型別層被擋下。
        item = AnalystBlocker(panel=name, status=panel.status, absence_kind=panel.absence_kind,
                              settled=panel.absence_is_settled, reason=panel.reason)
        if bucket == BLOCKED:
            blockers.append(detail)
            blocker_details.append(item)
        elif bucket == READY_WITH_FLAGS:
            flags.append(detail)
            flag_details.append(item)
    unavailable = tuple(f"{name}：{panels[name].status}" for name in OPTIONAL_PANELS
                        if panels[name].status in VALUELESS_STATUSES)
    state = BLOCKED if blockers else (READY_WITH_FLAGS if flags else READY)
    return AnalystReadiness(
        state=state, core_panels=CORE_PANELS, optional_panels=OPTIONAL_PANELS,
        flags=tuple(flags), blockers=tuple(blockers), optional_unavailable=unavailable,
        rule=_READINESS_RULE, blocker_details=tuple(blocker_details), flag_details=tuple(flag_details),
    )


def _limits(view: AlphaInvestmentView) -> tuple[str, ...]:
    """「這份判讀不是什麼」——全部抄自各 authority 已經寫好的 `is_not`／`gap_is_not`，去重保序。"""
    fixed = (
        "不是 buy／sell：系統的終點是隱含報酬與（optional 的）門檻價，不是動作。",
        "不是部位尺寸或配置：買多少、什麼時候買由使用者自行判斷並手動下單。",
        "不是跨標的機會排序：本畫面只看一檔；瓶頸排序的唯一權威是 rank_bottlenecks。",
    )
    everything: list[str] = list(fixed)
    everything += list(view.implied_return.is_not)
    everything += list(view.valuation.gap_is_not)
    # ⚠ 2026-09-23（Step 0b.1b）：`entry_logic.is_not` 隨 F 組退役。
    everything += list(view.investor_brief.is_not)
    everything += list(view.argument.is_not)
    # ⚠ 2026-09-23（Step 0b.1b）：`downside` panel 隨 E 組退役。
    # 所以「不是什麼」改從 `is_not` 取——`DOWNSIDE_IS_NOT` 第一句逐字就是「不是 bear case」。
    # D2（2026-09-18）：歸零旗標的四條「不是什麼」——尤其「綠燈不是查過都沒事的保證」。
    everything += list(view.wipeout_flags.is_not)
    return tuple(dict.fromkeys(everything))


def build_analyst_view(view: AlphaInvestmentView) -> AnalystView:
    """把 canonical read model 投影成 analyst 判讀畫面。純函式、確定性、可預先 materialize。"""
    panels = {
        "headline": _headline_panel(view),
        "fundamental": _fundamental_panel(view),
        "research": _research_panel(view),
        "bet": _bet_panel(view),
        "wipeout": _wipeout_panel(view),
        "brief": _brief_panel(view),
        "argument": _argument_panel(view),
    }
    rs = view.refresh_status
    ident = view.identity
    return AnalystView(
        schema_version=SCHEMA_VERSION, source_schema_version=view.schema_version,
        ticker=ident.ticker, company_id=ident.company_id, company_label=ident.company_label,
        as_of=ident.as_of, point_in_time_mode=ident.point_in_time_mode,
        generated_on=ident.generated_on, research_context_digest=ident.research_context_digest,
        headline=panels["headline"], fundamental=panels["fundamental"],
        research=panels["research"], bet=panels["bet"],
        wipeout=panels["wipeout"], brief=panels["brief"],
        argument=panels["argument"],
        readiness=_readiness(panels),
        refresh=RefreshSummary(overall=rs.overall, counts=dict(rs.counts),
                               change_detection=rs.change_detection,
                               judged_context_matches=rs.judged_context_matches,
                               attention=_attention(view),
                               notes=rs.notes),
        limits=_limits(view), warnings=view.warnings,
    )


__all__ = ["ATTENTION_STATES", "build_analyst_view"]
