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
    """市場預測什麼（選配）：會計年度別共識與市場觀測的**原始數字**。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：這個 panel 原本是「我們預測什麼／市場預測什麼／差異在哪」
    三問——internal／comparison／market_proxy 三組 line 與 opinion_stance／multiple_derivation 兩格全部讀
    FY+1 因果橋與估值鏈，整組退役。留下的是稽核區的原始數字：共識（身分是 fiscal_period_end）、市場脈絡
    （分析師人數、目標價、PE）、共識時序的量測。**沒有內部預測，所以也沒有「同期可比」這個分類。**
    """
    cs, eg = view.consensus, view.expectation_gap
    lines = (
        _lines(cs.fiscal_items, "consensus_fiscal")
        + _lines(cs.items, "market_context")
        + ((_line("gap_closure", eg.gap_closure.label, eg.gap_closure, "market_context"),)
           if eg.gap_closure is not None else ())
        + ((_line("consensus_series", eg.consensus_series.label, eg.consensus_series, "market_context"),)
           if eg.consensus_series is not None else ())
    )
    statuses = {"consensus": cs.meta.status, "expectation_gap": eg.meta.status}
    kinds = _absence_kinds(consensus=cs.meta, expectation_gap=eg.meta)
    periods = sorted({str((d.dependencies or {}).get("period") or d.key.rsplit("_", 1)[-1]) for d in cs.fiscal_items})
    return AnalystPanel(
        key="fundamental", title="基本面：市場預測什麼（原始數字，選配）",
        questions=("q2_market",),
        # ⚠ 2026-09-23（Phase 0 Step 0b.1）：由核心**降為選配**（ROADMAP 稽核區：原始數字）。
        status=worst_status(list(statuses.values())), optional=True,
        source_sections=("consensus", "expectation_gap"),
        source_statuses=statuses, source_absence_kinds=kinds, lines=lines,
        # ⚠ 共識段的 warnings 也要進來：「forward 是相對標籤不是會計年度身分」這條警告
        # 正是 2026-09-07 rollover 污染事故的判準，藏在 section 裡等於沒有（INV-3）。
        notes=(cs.coverage_note,) + cs.meta.warnings + eg.meta.warnings,
        context={"consensus_periods": periods,
                 "rule": "會計年度別共識的身分是 fiscal_period_end（不是 +1y 標籤）。本面板只呈現原始數字；"
                         "內部預測與「我們比市場」已於 2026-09-23 Phase 0 退役，這裡沒有任何相減"},
        reason=_worst_reason(worst_status(list(statuses.values())), expectation_gap=eg.meta, consensus=cs.meta),
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
    """投資人短評（核心）：七句＋一顆燈。**每一格都是 read model 的同一個 Datum。**

    ⚠ 2026-09-23（Phase 0）：那把尺（0b.1a）與「要翻倍需要什麼為真」那一句（D 組，讀 `multiple_horizon`）已退役。
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
        # ⚠ 2026-09-30（Step 3.7）：標題原本是「鏈、賭注、風險與認錯條件、時間表」——「賭注」段早在 0b.1b 退役，
        # 標題還留著它，讀的人會去找一段不存在的東西。改成三段各自回答的問句。
        key="argument", title="憑什麼這樣想：它在哪條鏈上、錯了怎麼知道、什麼時候知道",
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
    """賭注（optional）：**純文字**——`our_bet` 那一句＋騎的層或插槽＋什麼必須為真（ROADMAP「bet 改純文字」）。

    2026-09-23（Phase 0 Step 0b.1）由四個價格改成一句話；2026-09-30（Phase 3 Step 3.7）補齊另外兩件：
    「騎層或插槽」照抄敘事的 `rides[]`（read model 的 `investor_brief.rides`），「什麼必須為真」照抄短評那一格
    （`brief:what_must_be_true`）。**三格都是 read model 的同一個 Datum，本層一個字都不造；沒有任何價格。**
    status 仍取 `our_bet` 那一格——賭注那一句沒寫，另外兩格寫了也不構成「有賭注」。
    """
    ib = view.investor_brief
    our_bet = next((d for d in ib.slots if d.key.endswith("our_bet")), None)
    must = next((d for d in ib.slots if d.key.endswith("what_must_be_true")), None)
    rides = getattr(ib, "rides", None)
    lines = tuple(
        _line(key, label, datum, "bet")
        for key, label, datum in (("our_bet", "我們賭什麼（研究 session 寫下的那一句）", our_bet),
                                  ("rides", "騎哪一層或插槽（敘事宣告）", rides),
                                  ("what_must_be_true", "什麼必須為真、錯的訊號是什麼", must))
        if datum is not None)
    status = ("available" if (our_bet is not None and our_bet.is_known)
              else ((our_bet.status if our_bet is not None else None) or "missing"))
    return AnalystPanel(
        key="bet", title="賭注：我們賭什麼、騎在哪、什麼必須為真（純文字，optional）",
        questions=(),
        status=status, optional=True,
        source_sections=("investor_brief",),
        source_statuses={"investor_brief": status},
        source_absence_kinds={"investor_brief": (our_bet.absence_kind if our_bet is not None else "not_yet_recorded")},
        lines=lines,
        notes=(
            "**沒有價格、沒有報酬、沒有機率加權**——四個價格已於 2026-09-23 Phase 0 退役。",
            "「騎哪一層或插槽」是寫的人宣告的；那一份讀圖**現在**還是不是現行，看讀圖面板與候選狀態（前提失效會現形）。",
        ),
        context={"available": status not in VALUELESS_STATUSES,
                 "optional_rule": "沒寫賭注只表示「還沒寫」，不代表這檔研究不完整；"
                                  "文字是研究判斷（append-only ledger），本層照抄不造句"},
        reason=(our_bet.reason if our_bet is not None else "短評裡沒有 our_bet 這一格"),
    )


#: 讀圖狀態 → 這一格的 Datum status（宣告好的查表，不是新判斷）。`stale_low`（只有證據等級變）不要人重看；
#: `stale`（圖變了、可能翻 A/B）＝依據有 material change → review_required；`expired`＝時間到期 → stale。
#: 讀不到比對結果（None）不得印成現行（L13-2）→ review_required。
_READING_DATUM_STATUS: Mapping[str | None, str] = {
    "current": "available", "stale_low": "available", "stale": "review_required", "expired": "stale",
    None: "review_required",
}


def _readings_panel(readings: Mapping[str, Any] | None) -> AnalystPanel:
    """讀圖（**核心**，Phase 2 Step 2.7；2026-09-30 Step 3.7 升核心）：這家公司坐的層與插槽的現行讀圖，**每一份印狀態**。

    升核心＝接回 Phase 0 偏差 #16「review_required 的路」：讀圖 stale 時這個面板自己是 `review_required`，readiness
    因此 `ready_with_flags`。**狀態只由讀圖對圖決定，不吃 `refresh.overall`**（那一格今天全是退役估值鏈的殘留）。
    沒有讀圖＝`not_yet_recorded` blocker；它的下一步是寫讀圖（research-drain 段 5），**不得**為了收斂標成 settled。

    `readings` 由 materialize 組好（圖推這家公司 `supplies_to`／`develops` 到的節點 → 那些節點的現行讀圖；
    INV-1：由 `co:*` 推，不靠讀圖紀錄裡的 ticker）。標籤（判讀、單位、狀態的中文）由那一端從讀圖字彙附上——
    本層**一個字都不造**，也不 import 讀圖模組（import 白名單）。
    缺席分型由產生缺席的那一端宣告（L16）：`not_yet_recorded`＝坐的層與插槽都還沒有讀圖；
    `upstream_unavailable`＝這次沒讀到圖或 ledger。兩者不得壓成同一句。
    """
    title = "讀圖：它坐的那一層結構變了沒"
    base = dict(key="readings", title=title, questions=(), optional=False, source_sections=("structure_readings",))
    notes = ("讀圖是研究判斷（A3）：不 gate、不排序、不給尺寸；判讀由寫的人宣告，本層照抄。",
             "狀態只回答「讀圖跟圖還一不一致」，不回答「讀圖對不對」——對不對要靠 outcome 量測。")
    if readings is None:
        readings = {"absence": {"kind": "upstream_unavailable",
                                "reason": "這次 materialize 沒有給讀圖輸入（沒讀到圖或讀圖 ledger）"}}
    absence = readings.get("absence")
    seats = list(readings.get("seats") or ())
    rows = list(readings.get("readings") or ())
    if absence or not rows:
        # 缺席分型照抄產生端（`seat_readings_for` 的 `absence`／`empty`）；舊輸入沒有 `empty` 時退回「還沒讀」。
        declared = absence or readings.get("empty") or {}
        kind = declared.get("kind") or "not_yet_recorded"
        reason = (declared.get("reason")
                  or ("這家公司坐的層與插槽都還沒有讀圖（圖上它供貨或開發的節點："
                      + ("、".join(seats) if seats else "無") + "）"))
        return AnalystPanel(**base, status="missing", source_statuses={"structure_readings": "missing"},
                            source_absence_kinds={"structure_readings": kind}, notes=notes,
                            context={"available": False, "seats": seats}, reason=reason)
    lines = []
    for row in rows:
        status = _READING_DATUM_STATUS.get(row.get("status"), "review_required")
        datum = Datum(
            key=f"reading:{row['node']}:{row.get('unit')}", label=f"{row['node']}（{row.get('unit_label')}）",
            value=f"{row.get('kind_label')}｜{row.get('status_label')}", status=status, basis="session_judgment",
            authority="alpha://structure_reading", method="讀圖 ledger（研究 session 寫；append-only）＋ 與現在的圖確定性比對",
            reason=row.get("reason"),
            dependencies={"reading_id": row.get("reading_id"), "unit": row.get("unit"), "kind": row.get("kind"),
                          "status": row.get("status"), "read_on": row.get("read_on"), "expires": row.get("expires"),
                          "reading": row.get("reading"), "needs_reread": row.get("needs_reread")},
        )
        lines.append(_line(datum.key, datum.label, datum, "reading"))
    status = worst_status([line.datum.status for line in lines])
    return AnalystPanel(**base, status=status, source_statuses={"structure_readings": status},
                        source_absence_kinds={"structure_readings": None}, lines=tuple(lines), notes=notes,
                        context={"available": True, "seats": seats,
                                 "core_rule": "核心面板（3.7 起）：讀圖 stale／過期會讓 readiness 變成「讀得成但要留意」；"
                                              "狀態只由讀圖對圖決定，不看 refresh 燈"},
                        reason=None)


#: 候選狀態與 downside 的 authority（邏輯 URI）：兩者都是 materialize 注入的推導結果，不是 read model。
A_CANDIDATES = "alpha://candidates/v1"
A_DOWNSIDE = "engine_b://event_watch/downside"
#: 首屏三個字的題目（字彙與判定住 `alpha.candidates.three_words`；這裡只是行的標籤）。
_THREE_WORD_LABELS = (("will_it_die", "會死嗎"), ("priced_in", "已定價嗎"), ("in_numbers", "出現在數字裡了嗎"))


def _candidate_panel(candidate: Mapping[str, Any] | None) -> AnalystPanel:
    """首屏末行（optional，Phase 3 Step 3.7）：候選狀態＋財務三題三個字。

    `candidate` 由 materialize 組好（`alpha.providers.candidates.page_input`——**與候選板同一個 `derive_row`**）；
    字（可開／缺 X…、紅黃綠灰、是／否／無法量／未答）全由那一端給，本層照抄、不判、不 import 候選模組。
    status 取「候選狀態」那一格：沒有敘事也沒有持有＝不上板（`not_yet_recorded`），三個字照印。"""
    base = dict(key="candidate", title="這檔現在在哪一格：候選狀態與三題三個字", questions=(), optional=True,
                source_sections=("candidates",))
    notes = ("候選狀態與候選板是同一個推導、每天重算；它不是分數、不是名次、不給尺寸。",
             "會死嗎＝四盞燈最差的那一盞（灰＝沒量到，不是綠）；已定價嗎／出現在數字裡了嗎＝寫敘事的人宣告，沒宣告印「未答」。")
    if candidate is None:
        candidate = {"absence": {"kind": "upstream_unavailable",
                                 "reason": "這次沒有給候選狀態輸入（CLI 單檔不讀 Sheet；APP 的 materialize 才載）——不是「不上板」"}}
    absence = candidate.get("absence")
    if absence:
        return AnalystPanel(**base, status="missing", source_statuses={"candidates": "missing"},
                            source_absence_kinds={"candidates": absence.get("kind") or "upstream_unavailable"},
                            notes=notes, context={"available": False}, reason=absence.get("reason"))
    row = candidate.get("row")
    words = dict(candidate.get("three_words") or {})
    if row is not None:
        state = Datum(key="candidate:state", label="候選狀態", value=dict(row), status="available",
                      basis="deterministic", authority=A_CANDIDATES,
                      method="alpha.providers.candidates.derive_row（候選板同一個推導）",
                      reason=row.get("note"))
    else:
        # 不上板是哪一種不上板由產生端宣告（`page_input` 的 `row_absence`）：Sheet 讀不到時「也沒有持有」是沒驗過的否定。
        declared = candidate.get("row_absence") or {"kind": "not_yet_recorded",
                                                    "reason": "沒有敘事、也沒有持有——不上候選板（寫敘事才有候選狀態）"}
        state = Datum(key="candidate:state", label="候選狀態", status="missing", authority=A_CANDIDATES,
                      absence_kind=declared.get("kind") or "not_yet_recorded", reason=declared.get("reason"))
    lines = [_line(state.key, state.label, state, "candidate")]
    for key, label in _THREE_WORD_LABELS:
        word = words.get(key) or "未讀到"
        datum = Datum(key=f"candidate:{key}", label=label, value=word, status="available", basis="deterministic",
                      authority=A_CANDIDATES, method="alpha.candidates.three_words")
        lines.append(_line(datum.key, label, datum, "candidate"))
    status = state.status
    return AnalystPanel(**base, status=status, source_statuses={"candidates": status},
                        source_absence_kinds={"candidates": state.absence_kind}, lines=tuple(lines), notes=notes,
                        context={"available": row is not None, "today": candidate.get("today"),
                                 "sheet": dict(candidate.get("sheet") or {})},
                        reason=state.reason)


def _three_questions_panel(view: AlphaInvestmentView) -> AnalystPanel:
    """財務三題稽核區（optional，Phase 3 Step 3.7）：三題每一行的值、來源、as_of、口徑、rule，或缺席分型。

    **每一行是 read model 的同一個 Datum**（`three_questions.lines`，builder 與原始行一起組）；本層不判、不比、不設門檻。"""
    tq = view.three_questions
    base = dict(key="three_questions", title="財務三題的數字：會死嗎、已定價嗎、出現在數字裡了嗎（稽核區）",
                questions=(), optional=True, source_sections=("three_questions",))
    if tq is None:
        return AnalystPanel(**base, status="missing", source_statuses={"three_questions": "missing"},
                            source_absence_kinds={"three_questions": "upstream_unavailable"},
                            context={"available": False}, reason="這份 read model 沒有接三題")
    return AnalystPanel(**base, status=tq.meta.status, source_statuses={"three_questions": tq.meta.status},
                        source_absence_kinds=_absence_kinds(three_questions=tq.meta),
                        lines=_lines(tq.lines, "three_question"), notes=tq.is_not,
                        context={"available": tq.meta.status not in VALUELESS_STATUSES, "filer_class": tq.filer_class},
                        reason=tq.meta.reason)


def _downside_panel(candidate: Mapping[str, Any] | None) -> AnalystPanel:
    """錯了怎麼知道（optional，Phase 3 Step 3.7）：每一條反證 → 盯它的 watch id 與狀態；沒有 watch 印「未盯」。

    輸入由 materialize 組好（`engine_b.disproof.downside_rows`：歸屬＝`attributed_watches`、條件落格＝`watch_category`，
    與心跳段 2 的反證計數同一套）。本層照抄，一個字都不造。"""
    base = dict(key="downside", title="錯了怎麼知道：每條反證與盯它的 watch", questions=(), optional=True,
                source_sections=("downside",))
    notes = ("「未盯」＝條件寫了，但沒有 watch 會在它成真時叫醒你；舊判讀（session assessor）的反證不在反證登記範圍，一律未盯。",
             "反證用來決定何時認錯，不是進場的前置條件；觸及後要不要改 thesis 由你決定（thesis mutation 是人工 gate）。")
    if candidate is None:
        candidate = {"absence": {"kind": "upstream_unavailable",
                                 "reason": "這次沒有給 watch 輸入（CLI 單檔不載；APP 的 materialize 才載）——不是「沒有反證」"}}
    absence = candidate.get("absence")
    if absence:
        return AnalystPanel(**base, status="missing", source_statuses={"downside": "missing"},
                            source_absence_kinds={"downside": absence.get("kind") or "upstream_unavailable"},
                            notes=notes, context={"available": False}, reason=absence.get("reason"))
    downside = dict(candidate.get("downside") or {})
    rows = list(downside.get("rows") or ())
    extra = tuple(downside.get("notes") or ())
    if not rows:
        # 空的是哪一種空由產生端宣告（`downside_rows` 的 `empty`）：來源讀不到時是 upstream_unavailable，不是「還沒有反證」。
        declared = downside.get("empty") or {"kind": "not_yet_recorded", "reason": "這家公司名下還沒有任何反證"}
        return AnalystPanel(**base, status="missing", source_statuses={"downside": "missing"},
                            source_absence_kinds={"downside": declared.get("kind") or "not_yet_recorded"},
                            notes=extra + notes,
                            context={"available": False, "counts": dict(downside.get("counts") or {})},
                            reason=declared.get("reason"))
    lines = []
    for index, row in enumerate(rows):
        datum = Datum(key=f"downside:{index}", label=str(row.get("source_label") or row.get("source")),
                      value=dict(row), status="available", basis="deterministic", authority=A_DOWNSIDE,
                      method="engine_b.disproof.downside_rows（歸屬＝narrative_watches.attributed_watches）")
        lines.append(_line(datum.key, datum.label, datum, "downside"))
    return AnalystPanel(**base, status="available", source_statuses={"downside": "available"},
                        source_absence_kinds={"downside": None}, lines=tuple(lines), notes=extra + notes,
                        context={"available": True, "counts": dict(downside.get("counts") or {})}, reason=None)


# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：舊的 `_downside_panel`（「判斷錯了值多少」四個價格，E 組）退役；
# 2026-09-30（Phase 3 Step 3.7）同名函式（上面那一個）是新的「錯了怎麼知道」——每條反證連到 watch，不是四價復活。


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
    "⚠ 2026-09-30（Phase 3 Step 3.7）：**讀圖升核心**——讀圖 stale 會讓 readiness 變成 ready_with_flags"
    "（狀態只由讀圖對圖決定，不看 refresh 燈）；還沒有讀圖的檔多一個「還沒做」的 blocker。"
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
        "不是 buy／sell：系統不給動作；進場靠判斷，出場靠 disproof（隱含報酬與門檻價已於 2026-09-23 退役）。",
        "不是部位尺寸或配置：買多少、什麼時候買由使用者自行判斷並手動下單。",
        "不是跨標的機會排序：本畫面只看一檔；跨檔排序已於 2026-09-23 退役，結構事實住 query/bottleneck.py 的結構表。",
    )
    everything: list[str] = list(fixed)
    # ⚠ 2026-09-23（Step 0b.1b）：`implied_return.is_not`／`valuation.gap_is_not`（C／H 組）與
    # `entry_logic.is_not`（F 組）隨各自的 section 退役。
    everything += list(view.investor_brief.is_not)
    everything += list(view.argument.is_not)
    # ⚠ 2026-09-23（Step 0b.1b）：`downside` panel 隨 E 組退役。
    # 所以「不是什麼」改從 `is_not` 取——`DOWNSIDE_IS_NOT` 第一句逐字就是「不是 bear case」。
    # D2（2026-09-18）：歸零旗標的四條「不是什麼」——尤其「綠燈不是查過都沒事的保證」。
    everything += list(view.wipeout_flags.is_not)
    return tuple(dict.fromkeys(everything))


def build_analyst_view(view: AlphaInvestmentView, *, readings: Mapping[str, Any] | None = None,
                       candidate: Mapping[str, Any] | None = None) -> AnalystView:
    """把 canonical read model 投影成 analyst 判讀畫面。純函式、確定性、可預先 materialize。

    `readings`（Phase 2 Step 2.7）：讀圖面板的輸入，由 materialize 組好；沒給＝這次沒讀到（`upstream_unavailable`），
    不是「沒有讀圖」。
    `candidate`（Phase 3 Step 3.7）：候選狀態＋三個字＋downside 的輸入（`alpha.providers.candidates.page_input`），
    由 materialize 一次載入 context 後逐檔組好；沒給＝這次沒讀到，兩個面板都說 `upstream_unavailable`。
    """
    panels = {
        "headline": _headline_panel(view),
        "fundamental": _fundamental_panel(view),
        "research": _research_panel(view),
        "bet": _bet_panel(view),
        "wipeout": _wipeout_panel(view),
        "brief": _brief_panel(view),
        "argument": _argument_panel(view),
        "readings": _readings_panel(readings),
        "candidate": _candidate_panel(candidate),
        "three_questions": _three_questions_panel(view),
        "downside": _downside_panel(candidate),
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
        argument=panels["argument"], readings=panels["readings"],
        candidate=panels["candidate"], three_questions=panels["three_questions"], downside=panels["downside"],
        readiness=_readiness(panels),
        refresh=RefreshSummary(overall=rs.overall, counts=dict(rs.counts),
                               change_detection=rs.change_detection,
                               judged_context_matches=rs.judged_context_matches,
                               attention=_attention(view),
                               notes=rs.notes),
        limits=_limits(view), warnings=view.warnings,
    )


__all__ = ["ATTENTION_STATES", "build_analyst_view"]
