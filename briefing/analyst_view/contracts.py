"""Analyst View（Phase 2 Step 3.5）——**消費端的呈現 DTO**，不是第二份研究 authority。

## 這一層是什麼

`AlphaInvestmentView`（canonical read model）回答「系統對這家公司知道什麼」，
但它是**依資料結構排列**的：共識住第 5 節、敘事住短評與論證那幾節。
使用者打開一檔股票時要在很短時間內看懂的是——**我們在賭什麼、憑什麼、什麼會推翻它、
現在多少錢、會不會歸零**——那幾件事橫跨上述所有 section。

Analyst View 就是把同一份 view **依消費者問句重新投影**成核心 panel 與 optional panel。
⚠ 2026-09-23（Phase 0）：原文寫「五件事」的第二、三件是「跟市場差在哪、怎麼算到這裡」，
那是估值鏈的問句，已隨它退役。

## 硬邊界（`tests/test_analyst_view.py` 逐條守著）

1. **不重算任何數字。** 每一行呈現都持有 `AlphaInvestmentView` 裡**同一個 `Datum` 物件的參照**
   （`is` 相等，不是複製、不是新建），所以「Consumer 重算了 EPS／估值／報酬」在型別層就不可能發生。
   本模組**沒有任何算術**：沒有公式、沒有加總、沒有百分比換算。唯一的數值運算是**排序鍵**
   （`abs(既有敏感度)`），它不產生任何新值，只決定列的先後。
2. **只組裝／排序／label。** panel 的 `status` 是既有 section `meta.status` 的**取最嚴**（`_WORST_FIRST`
   是宣告好的嚴重度序），不是新判斷；`readiness` 是同一組 status 的計數，不是新的研究完整度分數。
3. **Missing != Zero 免費繼承**：值都是原本的 `Datum`，`Datum.__post_init__` 的不變式照樣生效。
4. **沒有 LLM runtime。** 這一層是純函式，可預先 materialize 成 JSON 讓 APP 直接讀
   （`AnalystView.to_dict()`）；不得在讀取時重寫 thesis。
5. **沒有 authority write。** 不碰 ledger、不建 decision、不改 thesis、不寫任何檔案
   （CLI 的 `-o` 是使用者指定的輸出，不是 authority）。
6. **2026-09-23（Phase 0 Step 0b.1）：`why` 與 `entry` 兩個 panel 退役。**
   `why`（「怎麼算到這裡：假設、敏感度、算式、證據」）只吃估值鏈三個 section，它問的問題
   已被 G3 退役；`entry`（進場門檻）73 檔全 missing，從未用過。**進場靠判斷，出場靠 disproof**，
   系統不再有「門檻價」這個概念，也不再有「主流程終點是 implied return」這句話。
   在答「憑什麼」的是 `argument`（73 檔都有內容），所以它升為核心。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Sequence

from alpha.absence import ABSENCE_KINDS, SETTLED_ABSENCE_KINDS, check_absence_kind
from briefing.alpha_view.contracts import (
    CatalystItem, CheckpointItem, Datum, DisproofItem, EvidenceItem, RefreshItem, _jsonable,
)

SCHEMA_VERSION = "analyst-view/1"

#: 消費者的六個問句。panel 用 `questions` 指出自己回答哪幾個——這是**閱讀順序**的宣告，
#: 不是新的分類法：每個問句的答案都已經在 `AlphaInvestmentView` 裡，只是散在不同 section。
QUESTIONS: Mapping[str, str] = {
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`q1_internal`（我們預測什麼）與 `q3_gap`（差異在哪）退役
    #   ——它們的答案是 FY+1 因果橋與內部 vs 共識的數值 gap。「市場預測什麼」留著：那是 Engine C 的原始數字。
    "q2_market": "市場預測什麼？",
    "q6_change": "什麼 evidence 會改變答案？",
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：三個問句退役。
    #   `q4_implied_return`（現價對 future target 隱含什麼報酬）與 `q7_payoff`（賭注對了值多少）
    #   是估值鏈與四價尺的問句；`q5_fragile`（哪些假設最脆弱）是 `why` 面板的問句，
    #   而 `why` 已退役——「最脆弱」原本指的是估值假設的敏感度，那個模型不在了。
    #   風險與認錯條件由 `argument` 的 risks 段與 `research` 面板回答，**它們不是同一個問題**。
    # 2026-09-15：投資人的第零問——用人話講一遍前因後果。optional：沒寫短評不代表研究不完整。
    "q0_story": "這是什麼賭注、為什麼、值多少、什麼時候知道？",
    # 2026-09-15：論證層——把短評的七句展開成六段分析師報告體，附引文與長文。
    "q0_argument": "為什麼這樣想？證據在哪？",
}

#: 核心 panel（決定 `readiness`）與 optional panel（**不**決定 readiness）。
#:
#: ⚠ **2026-09-23（Phase 0 Step 0b.1）換過一次**（ROADMAP「個股頁」對照表＋使用者定案 A）：
#:   舊：`("headline", "fundamental", "why", "research")`，主流程是
#:       Evidence → Internal Forecast → Valuation → Horizon → Implied Return。
#:   新：短評與論證是核心，估值鏈整條退役。`fundamental` **降為選配**（它是稽核區的原始數字，
#:       不是判讀完整度的條件）；`why` 退役；`wipeout`（歸零旗標）升核心——AGENTS「歸零旗標是燈不是數字」
#:       把它列為量測，而量測缺席不該被讀成「沒事」。
#:   讀圖面板 Phase 2 才加，所以現在不在列（`brief` 的 70/73 missing 是真實 backlog，不是規則錯）。
CORE_PANELS: tuple[str, ...] = ("headline", "brief", "argument", "research", "wipeout")
#: `fundamental`：稽核區的原始數字（內部預測／共識／落差）。2026-09-23 由核心降選配。
#: `bet`：賭注。2026-09-23 起是**純文字**（讀 `our_bet`），不再是四個價格。optional——
#: 沒寫賭注的檔 readiness 不變差；它回答的是「值不值得看」，不是「研究完不完整」。
#: `downside`（D2，2026-09-18）：判斷錯了值多少。四價渲染在 Phase 0 批 4 退役，panel 留。
#: ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`downside` panel 隨 E 組（四價 overlay）退役。
OPTIONAL_PANELS: tuple[str, ...] = ("fundamental", "bet")

#: panel status 的嚴重度序（**由輕到重**）。取最嚴＝取這個序裡 index 最大的那一個。
#: 它只在既有 `SECTION_STATUSES` 上定義先後，不新增任何狀態字。
_WORST_FIRST: tuple[str, ...] = (
    "available", "partial", "not_applicable", "stale", "review_required",
    "insufficient_evidence", "not_modeled", "missing", "invalidated",
)

#: 哪些 panel status 代表「這一段沒有內容」——與 `alpha_view` 的 `VALUELESS_STATUSES` 同一組。
_VALUELESS_PANEL_STATUSES: frozenset[str] = frozenset(
    {"missing", "not_modeled", "not_applicable", "insufficient_evidence", "invalidated"})

#: readiness 三態。**只看核心 panel**。
READY = "ready"                        # 核心四段都有內容，且沒有被標記需要動作
READY_WITH_FLAGS = "ready_with_flags"  # 有內容，但至少一段 stale／review_required／not_applicable
BLOCKED = "blocked"                    # 至少一段核心缺內容（missing／invalidated／not_modeled／證據不足）
READINESS_STATES = frozenset({READY, READY_WITH_FLAGS, BLOCKED})

#: 哪些 status 算「有內容」／「有內容但要注意」／「缺內容」。這是一張**查表**，不是條件判斷。
_READINESS_CLASS: Mapping[str, str] = {
    "available": READY, "partial": READY,
    "stale": READY_WITH_FLAGS, "review_required": READY_WITH_FLAGS, "not_applicable": READY_WITH_FLAGS,
    "missing": BLOCKED, "invalidated": BLOCKED, "not_modeled": BLOCKED, "insufficient_evidence": BLOCKED,
}

#: 一行呈現在 panel 裡扮演什麼角色（封閉字彙；renderer 依此分組，不依值分組）。
LINE_ROLES = frozenset({
    "headline_number",         # 頭條那一格：現價
    "consensus_fiscal",        # 會計年度別共識（身分是 fiscal_period_end；只呈現，不與任何內部預測相減）
    "market_context",          # 非期間身分的市場觀測（分析師人數、目標價、PE…）與共識時序的量測
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：`assumption`／`sensitivity`／`trace`／`epistemics`
    # 四個 role 退役——它們**只由 `why` 面板產生**，而 `why` 已退役。`entry` 同理。
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`internal`（我們的預測）、`consensus_same_period`／
    # `consensus_other_period`（相對於內部預測期間的分類）、`comparison`（內部 vs 共識）、`market_proxy`
    # （PE 比值 proxy）、`headline_context`（隱含報酬的語意脈絡）退役；`override`（賭注覆蓋的假設）隨 E 組退役。
    # 留著沒有 producer 的 role 等於留一份會讓下個讀者以為還在用的字彙（L16）。
    "thesis",                  # 研究判斷本身
    "score",                   # Q1–Q5
    "lifecycle",               # thesis 狀態／到期／watch
    "bet",                     # optional：賭注（2026-09-23 起是純文字，不是四個價格）
    "brief",                   # optional：投資人短評的七句＋一顆燈
    "paragraph",               # optional：論證層的三段
    "wipeout",                 # optional：歸零旗標的一盞燈（D2；顏色＋一句話，數字在 dependencies）
})

#: 「為什麼這一格被列進脆弱清單」的封閉字彙。**每一條都是宣告好的列入規則**，
#: 不是本層對脆弱程度的新判斷——所以每個 `WeakInput` 都必須說出自己是被哪一條規則列進來的。
WEAK_INPUT_RULES: Mapping[str, str] = {
    "heuristic_proxy_input": "這格的知識種類是粗略代理（heuristic proxy），不是觀測也不是明示判斷",
    "session_judgment_input": "這格是 session 判斷——它可能對，但它不是事實",
    "largest_modeled_sensitivity": "既有敏感度（估值層已算好）中 |Δ| 最大的一條；排序不改變任何數字，也不是新的 attribution model",
    "refresh_flagged": "refresh 引擎已標記它需要動作（stale／review_required／invalidated／recalculate）",
    "weakest_known_axis": "AlphaSignal 已算出的最弱軸（不是本層重算）",
    "unknown_axis": "這一軸目前未知——缺席不是 0，也不是「沒問題」",
}


# ---------------------------------------------------------------------------
# 呈現別名：accounting_basis（Step 5）
# ---------------------------------------------------------------------------

#: `alpha` 的 `ACCOUNTING_BASES = ("gaap", "non_gaap", "not_applicable", "unverified")` 是
#: **contract identity**——它是三本 private append-only ledger 每一筆紀錄身分的一部分，
#: 改字彙等於改既有紀錄的身分（L10）。所以**不改字彙，加一層呈現別名**。
#:
#: ⚠ 這一層唯一的責任是**不要多說**。系統實際記錄的區別只有「as reported（法定財報）」
#: vs「公司自己調整後」；它**沒有**任何欄位知道那份法定財報是 US GAAP、IFRS、AASB、
#: 日本基準還是台灣 IFRS。2026-09-07 Coverage Pilot 實測：Lynas（AASB／IFRS）、
#: HDS（日本基準）、IQE（IFRS）三檔在 ledger 裡全都寫著 `gaap`——語意正確、字面錯誤。
#: **所以 label 一律不含準則名稱**，而 `raw` 永遠一併輸出讓稽核追得回 contract 值。
#: **面向使用者的顯示別名。字彙一個字不改**——`absence_kind`／panel key／line key 都是 read model
#: 與 private ledger 的身分（L10），改它們等於改紀錄。這裡只加「同一個東西怎麼講給人聽」。
#:
#: 判準（2026-08-31 使用者定案，2026-09-08 套到 APP）：**望文生義還是要查表？**
#: 望文生義的留著（`COHR`、`52 週高點`）；含縮寫或內部命名的要翻（`fair_value`、`absence_kind`、
#: `externally_corroborated`）。翻譯**不得宣稱 authority 沒有的東西**——同 `accounting_basis` 那條：
#: 「獨家供應」可以，因為那就是 `sole_source` 的意思；但不得順手加上「所以很安全」。
PLAIN_PANEL_TITLES: Mapping[str, Mapping[str, str]] = {
    "headline": {"title": "現在多少錢",
                 "hint": "現價與價格脈絡（52 週高低、最新交易日、幣別）。**這裡沒有目標價、沒有隱含報酬**"
                         "——那把尺已於 2026-09-23 退役；「已定價嗎」由財務三題回答（Phase 3）"},
    "fundamental": {"title": "市場預測什麼（原始數字，選配）",
                    "hint": "會計年度別共識與市場觀測，身分是 fiscal_period_end。"
                            "2026-09-23 起沒有內部預測、沒有「我們比市場」——那條鏈退役了；"
                            "這裡是稽核區的原始數字，不是判讀完整度的條件"},
    "research": {"title": "什麼會推翻它",
                 "hint": "出場靠這些條件，不是靠感覺；還有什麼時候會知道答案"},
    "argument": {"title": "為什麼這樣想",
                 "hint": "三段：這條鏈怎麼走、風險與認錯條件、時間表。圖的敘述由句型組；"
                         "風險、認錯條件是研究時寫的長文，逐字附在段後。"
                         "⚠ 2026-09-23 少了「數字怎麼算出來」「和市場差在哪」（讀估值鏈）與「賭注」（讀四價）三段"},
    "brief": {"title": "這檔在賭什麼",
              "hint": "七句話講前因後果：什麼在放量、這家公司供什麼、為什麼卡在它、市場怎麼看、我們賭什麼、"
                      "對了／錯了會怎樣、什麼時候知道。文字是研究時寫的判斷，數字由系統填"},
    "wipeout": {"title": "會不會歸零",
                "hint": "四盞燈：現金跑道、負債、稀釋、going concern。**只給顏色不給數字**——"
                        "算出顏色的數字在每盞燈自己的稽核格裡。灰燈不是綠燈：它表示這一項沒量到，"
                        "而「沒查」不等於「沒事」"},
    "bet": {"title": "我們賭什麼",
            "hint": "研究 session 寫下的那一句（短評的 our_bet）。沒有價格、沒有報酬、沒有機率加權——"
                    "四個價格已於 2026-09-23 退役。沒寫賭注的檔這裡是空的，不影響判讀完不完整"},
}

#: 逐格標籤的白話版。沒列到的沿用 read model 的 `display_label`（那些多半本來就看得懂）。
PLAIN_LINE_LABELS: Mapping[str, str] = {
    "current_price": "現在股價",
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：估值鏈（fair_value／value_date／horizon／price_return／年化／
    # 兩桿拆解／epistemics／internal_*）、進場門檻（criterion／required_annualized_return，F 組）、
    # 賭注與下檔的四價（payoff_*／variant_*／downside_*，E 組）、目標價到了沒（target_reached）
    # 的白話標籤全部退役——沒有 producer 的標籤不留（L16）。
    "thesis": "我們的看法",
    "variant_view": "我們和市場看法差在哪",
    "direction": "看多還看空",
    "confidence": "信心程度",
    "expected_horizon": "預期多久見分曉",
    "gap_closure": "市場承認了嗎",
    "consensus_series": "市場共識每股盈餘的歷史",
}

#: 缺席語意的短標籤（畫面寬度用）。完整說明仍是 `ABSENCE_KINDS`，兩者同一個家——
#: 前端**不維護第二份**（先前它是 app.js 裡的硬編碼表，那正是 L16 說的重造品）。
PLAIN_ABSENCE_SHORT: Mapping[str, str] = {
    "not_yet_recorded": "還沒做",
    "deliberate_abstention": "刻意不下判斷",
    "method_not_applicable": "這個方法不適用",
    "upstream_unavailable": "缺上游資料",
    "inputs_incompatible": "拿來比會出錯",
    "provider_missing": "資料源沒有",
    "capability_absent": "系統還沒這能力",
    "point_in_time_unavailable": "回看那天沒有這筆",
    "insufficient_evidence": "證據不夠",
    "invalidated": "已失效",
    "not_applicable_unspecified": "說了不適用但沒說哪一種",
}

#: 三個 readiness 狀態的白話版。**不得寫成能不能買**——它只描述「這份判讀讀不讀得成」。
PLAIN_READINESS: Mapping[str, Mapping[str, str]] = {
    "ready": {"label": "四段都讀得成", "note": "不是「可以買」的意思——這裡只講資料完不完整"},
    "ready_with_flags": {"label": "讀得成，但有幾格要留意",
                         "note": "有內容，但至少一段過期或需要重看"},
    "blocked": {"label": "有一段讀不成", "note": "看下面「卡在哪」——它會說是還沒做、刻意不做，還是缺上游"},
}

# ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`PLAIN_MULTIPLE_DERIVATION`（目標倍數的來源）退役——
# 它是估值假設的 `derivation` 白話層，估值鏈整條退役。

#: refresh overall 的白話燈號（2026-09-15，投資人短評首屏的那一顆燈）。**不判斷好壞**，只講狀態。
PLAIN_REFRESH_OVERALL: Mapping[str, str] = {
    "current": "判斷是最新的",
    "review_required": "有假設改過，判斷還沒重看",
    "recalculate": "有數字要重算",
    "invalidated": "有一條前提已被推翻",
    "stale": "太久沒核查",
    "superseded": "已被新判斷取代",
    "missing": "還沒有判斷",
}

# ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`PLAIN_DRIVER_LABELS`（driver 白話標籤，只服務論證層的
# 「數字怎麼算出來」與反推表）與 `PLAIN_STANCE`（我們有沒有形成自己的觀點——FY+1 模型對假設 `derivation`
# 的聚合）退役。「有沒有自己的觀點」這個問題沒有消失，它的新家是讀圖與敘事（Phase 2），不再由估值假設的來源推得。

#: 圖表用的一句話。價格是**脈絡不是訊號**：不排序、不決定尺寸、不產生任何建議。
PRICE_SERIES_NOTE = (
    "這是這檔自己的收盤價（provider 報價單位原值，未換算幣別）。"
    "它是**脈絡不是訊號**——系統不用它排序、不用它決定買多少，也不從中推導任何進出場建議。"
    "只取已收盤的交易日，所以不含今天的盤中價。"
)

ACCOUNTING_BASIS_DISPLAY: Mapping[str, Mapping[str, str]] = {
    "gaap": {
        "label": "As reported（法定財報口徑）",
        "note": "系統只記錄「法定財報 vs 公司調整後」這個區別，**不主張**它是 US GAAP／IFRS／"
                "AASB／日本基準——authority 裡沒有那一格，猜一個就是造一個沒人宣告過的事實。",
    },
    "non_gaap": {
        "label": "公司調整後（adjusted，非法定口徑）",
        "note": "由公司自己在財報中揭露的調整後數字；調整項目由公司定義，跨公司不可比。",
    },
    "not_applicable": {
        "label": "不適用（這一格沒有口徑語意）",
        "note": "這個數字不是損益表項目，沒有 as-reported／adjusted 的區別。",
    },
    "unverified": {
        "label": "口徑未確認",
        "note": "無法從一手來源判定這個數字是法定口徑還是公司調整後——**不猜**；"
                "與內部估計的比較因此不成立。",
    },
    # 2026-09-11：`unverified` 原本同時承載「口徑不同」與「換算率不同」，下游被迫二選一
    # 而兩邊都是錯的（L12）。拆開之後這兩個值**不得**在呈現層被壓回 gaap／non_gaap——
    # 它們明說「口徑認出來了，但這個數字帶著一個已知的換算誤差」。
    "gaap_fx_tolerated": {
        "label": "As reported（法定財報口徑；換算率與一手不同）",
        "note": "provider 與一手財報是同一個口徑，但用了不同的匯率換算（常見成因：provider 用"
                "年均價、年報印期末價）。差距在 3% 容差內才這樣認定；**同一個換算差會原樣進到"
                "下面的 gap**，所以 gap 小於這個殘差時不具意義。要消掉它得用同一條 FX 路徑重算"
                "共識，不是調容差。",
    },
    "non_gaap_fx_tolerated": {
        "label": "公司調整後（adjusted，非法定口徑；換算率與一手不同）",
        "note": "與上一項同理，只是對上的是公司自己揭露的調整後數字。調整項目由公司定義，"
                "跨公司不可比，再加上一個已知的換算誤差。",
    },
}


def accounting_basis_display(raw: str | None) -> dict[str, str | None]:
    """contract 值 → 面向使用者的三欄。**raw 永遠保留**；未登記的值原樣回傳、不編故事。"""
    if raw is None:
        return {"raw": None, "label": "未宣告", "note": "authority 沒有記錄這一格的口徑。"}
    entry = ACCOUNTING_BASIS_DISPLAY.get(raw)
    if entry is None:
        return {"raw": raw, "label": raw,
                "note": "未登記的口徑值——呈現層不翻譯未知字彙，原樣顯示以便稽核。"}
    return {"raw": raw, "label": entry["label"], "note": entry["note"]}


class AnalystViewContractViolation(ValueError):
    """Analyst View 的型別不變式被違反（例如某一行不是來自既有 read model 的 `Datum`）。"""


def _check(value: str, allowed, label: str) -> None:
    if value not in allowed:
        raise AnalystViewContractViolation(f"{label} 未登記：{value!r}；已知 {sorted(allowed)}")


@dataclass(frozen=True, slots=True)
class AnalystLine:
    """一行呈現＝**既有 `Datum` 的參照** ＋ 面向讀者的標籤 ＋ 它在 panel 裡的角色。

    刻意**沒有 `value` 欄位**：值只有一個住處，就是 `datum`。想在這裡放一個「已格式化的值」
    就是在建第二份真相，而那正是 L12（一個表示兩種語意）的起點。
    """

    key: str
    display_label: str
    datum: Datum
    role: str

    def __post_init__(self) -> None:
        if not isinstance(self.datum, Datum):
            raise AnalystViewContractViolation(
                f"AnalystLine[{self.key}].datum 必須是 read model 的 Datum"
                f"（拿到 {type(self.datum).__name__}）——consumer 不得自造數值格"
            )
        _check(self.role, LINE_ROLES, "AnalystLine.role")


@dataclass(frozen=True, slots=True)
class WeakInput:
    """一條「脆弱輸入」。`rule` 說出它是被哪一條**宣告好的列入規則**挑進來的。"""

    key: str
    display_label: str
    datum: Datum
    rule: str

    def __post_init__(self) -> None:
        if not isinstance(self.datum, Datum):
            raise AnalystViewContractViolation(f"WeakInput[{self.key}].datum 必須是既有 Datum")
        _check(self.rule, WEAK_INPUT_RULES, "WeakInput.rule")

    @property
    def why(self) -> str:
        return WEAK_INPUT_RULES[self.rule]


@dataclass(frozen=True, slots=True)
class AnalystPanel:
    """一個 panel＝一組消費者問句的答案。

    - `status`：來源 section `meta.status` 取最嚴（`worst_status`）。**抄，不算。**
    - `source_statuses`：逐個來源 section 的原始 status，讓讀者看得到取最嚴之前長什麼樣。
    - `context`：從 read model 直接抄來的純量（期間、口徑、overall refresh state…），不含新計算。
    """

    key: str
    title: str
    questions: tuple[str, ...]
    status: str
    optional: bool
    source_sections: tuple[str, ...]
    source_statuses: Mapping[str, str]
    #: 每個來源 section 的缺席語意（`alpha/absence.py`；有內容的 section 是 None）。**抄，不推論。**
    source_absence_kinds: Mapping[str, str | None] = field(default_factory=dict)
    #: 2026-09-13：每個來源 section 的 `settled_by`（`ab_*`）。**照抄，不推論。**
    source_settled_by: Mapping[str, str | None] = field(default_factory=dict)
    lines: tuple[AnalystLine, ...] = ()
    weak_inputs: tuple[WeakInput, ...] = ()
    catalysts: tuple[CatalystItem, ...] = ()
    checkpoints: tuple[CheckpointItem, ...] = ()
    disproofs: tuple[DisproofItem, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    attention: tuple[RefreshItem, ...] = ()
    #: `attention` 被篩過時，這裡逐字寫出**篩到剩下什麼**；`None`＝沒篩，就是全部。
    #: ⚠ 2026-09-07 實測到的呈現陷阱：headline 只列 `HEADLINE_ARTIFACTS`，卻印出
    #: 「需要重看的研究成果：無」——那是一句全域斷言配一個局部範圍，與同一畫面上的
    #: `overall=review_required` 直接矛盾（L12：一個表示兩種語意）。
    attention_scope: str | None = None
    #: 整份 view 有幾項需要動作（不分 section）。有 scope 時，讀者必須看得到「本節之外還有幾項」。
    attention_total: int | None = None
    risks: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    context: Mapping[str, Any] = field(default_factory=dict)
    reason: str | None = None

    def __post_init__(self) -> None:
        _check(self.status, set(_WORST_FIRST), "AnalystPanel.status")
        for question in self.questions:
            _check(question, set(QUESTIONS), "AnalystPanel.questions")
        for kind in self.source_absence_kinds.values():
            if kind is not None:
                check_absence_kind(kind, "AnalystPanel.source_absence_kinds")

    @property
    def absence_kind(self) -> str | None:
        """這個 panel 缺內容時**是哪一種缺席**。

        **宣告好的挑選規則，不是新判斷：** panel 的 status 已經是來源 section 的「取最嚴」；
        這裡取**第一個 status 等於 panel status 的來源 section**（依 `source_sections` 的宣告順序）
        的缺席語意。有內容的 panel 一律 None。
        """
        if self.status not in _VALUELESS_PANEL_STATUSES:
            return None
        for name in self.source_sections:
            if self.source_statuses.get(name) == self.status:
                return self.source_absence_kinds.get(name)
        return None

    @property
    def absence_is_settled(self) -> bool:
        """這一格的缺席**已經是答案**（刻意不主張／方法不適用／本層沒有這個能力）。

        ⚠ 它**不**讓 readiness 變好——blocked 還是 blocked。它只回答「使用者看到這格該不該去補」。

        ⚠⚠ **2026-09-13 補第二條路徑：`settled_by`。** 先前只看 `absence_kind`，於是
        「有 Abstention 但缺席理由來自上游」的標的（POET）會被歸成「要去補上游」，
        而那筆 Abstention 的內文正好在警告不要去補。兩個條件是 or：**任一成立就不是待辦**。
        """
        if self.settled_by is not None:
            return True
        return self.absence_kind in SETTLED_ABSENCE_KINDS

    @property
    def settled_by(self) -> str | None:
        """哪一筆 `Abstention` 宣告了這一格不必補（照抄 section 的 `settled_by`，不推論）。"""
        for name in self.source_sections:
            declared = self.source_settled_by.get(name)
            if declared:
                return declared
        return None


@dataclass(frozen=True, slots=True)
class AnalystBlocker:
    """一條 blocker 的**結構化**形式——`blockers` 那串字串的機器可讀版本。

    為什麼要有它：APP 必須分得出「6324.T 的估值是刻意不主張」與「IQE.L 的估值是上游缺料」，
    而那個區別在一句中文散文裡只能靠 parse 猜（L16 記過三次的形狀）。
    `blockers`（字串）保留原樣供人閱讀與既有消費端使用；這裡是同一件事的欄位化。
    """

    panel: str
    status: str
    absence_kind: str | None
    settled: bool
    reason: str | None

    def __post_init__(self) -> None:
        _check(self.status, set(_WORST_FIRST), "AnalystBlocker.status")
        if self.absence_kind is not None:
            check_absence_kind(self.absence_kind, "AnalystBlocker.absence_kind")


@dataclass(frozen=True, slots=True)
class AnalystReadiness:
    """**核心** consumer 是否讀得成一份完整判讀。Optional panel 一律不參與。

    `rule` 把判準逐字寫在資料裡，因為讀者不該需要翻程式碼才知道 `ready` 是什麼意思。
    """

    state: str
    core_panels: tuple[str, ...]
    optional_panels: tuple[str, ...]
    flags: tuple[str, ...]
    blockers: tuple[str, ...]
    optional_unavailable: tuple[str, ...]
    rule: str
    #: `blockers` 的欄位化版本（同一批項目、同一個順序）。**不是第二份判斷**，是同一份的機器可讀形式。
    blocker_details: tuple[AnalystBlocker, ...] = ()
    #: `flags` 的欄位化版本，規則同上。
    flag_details: tuple[AnalystBlocker, ...] = ()

    def __post_init__(self) -> None:
        _check(self.state, READINESS_STATES, "AnalystReadiness.state")
        if self.blocker_details and len(self.blocker_details) != len(self.blockers):
            raise AnalystViewContractViolation(
                "blocker_details 與 blockers 必須一一對應——兩份不同長度就是兩份判斷")


@dataclass(frozen=True, slots=True)
class RefreshSummary:
    """「什麼變了、還有什麼要重看」的摘要——**抄自** `refresh_status`，不重跑 refresh 引擎。"""

    overall: str
    counts: Mapping[str, int]
    change_detection: str
    judged_context_matches: bool | None
    attention: tuple[RefreshItem, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalystView:
    """一檔股票的 analyst 判讀畫面（可預先 materialize 的 canonical 投影）。"""

    schema_version: str
    source_schema_version: str
    ticker: str
    company_id: str | None
    company_label: str
    as_of: date | None
    point_in_time_mode: str
    generated_on: date
    research_context_digest: str | None
    headline: AnalystPanel
    fundamental: AnalystPanel
    research: AnalystPanel
    readiness: AnalystReadiness
    refresh: RefreshSummary
    limits: tuple[str, ...]
    warnings: tuple[str, ...]
    #: V0（2026-09-15）：賭注 panel（optional）。放在 headline 之後——投資人看完 base 的數字，
    #: 下一個問題就是「如果我們對了呢」。沒寫賭注也必須有一個 missing 的 bet panel（缺席要現形）。
    bet: AnalystPanel
    #: D2（2026-09-18）：與 `bet` 對稱的 optional panel。兩者並排就是短評那把尺的兩端。
    #: D2（2026-09-18）：歸零旗標 panel（optional）。緊接在 `downside` 之後——
    #: 「判斷錯了值多少」問的是 thesis 錯了會怎樣，這一個問的是公司本身會不會直接歸零。
    wipeout: AnalystPanel
    #: 2026-09-15：投資人短評 panel（optional）。APP 首屏只讀它；markdown 仍以 headline 開頭。
    brief: AnalystPanel
    #: 2026-09-15：論證層 panel（optional）：短評展開成六段，附引文與長文。
    argument: AnalystPanel

    #: ⚠ 新增 panel 必須同時登記在這裡與 `OPTIONAL_PANELS`／`CORE_PANELS`——**兩份都是封閉清單**。
    #: `downside` 緊接在 `bet` 後面：它們是同一把尺的兩端，讀的人要並排看。
    #: 事發（2026-09-18）：D2 的 panel 做好了但沒登記，於是 artifact 的 `absence_kind` 是 `None`
    #: （`to_dict` 只對 `PANEL_ORDER` 裡的 panel 寫出那個 property），readiness 也沒列它——
    #: 機制在、但分類沒跟著資料走到消費端（L16）。**materialize 一次就看得到，所以要驗 artifact。**
    #: ⚠ 2026-09-23（Phase 0 Step 0b.1）：`why` 與 `entry` 已從這份清單移除（兩個 panel 退役）。
    #: 順序即閱讀順序：短評 → 論證 → 賭注／下檔 → 歸零旗標 → 現價 → 稽核區的原始數字 → 什麼會推翻它。
    PANEL_ORDER = ("brief", "argument", "bet", "wipeout",
                   "headline", "fundamental", "research")

    @property
    def panels(self) -> tuple[AnalystPanel, ...]:
        return tuple(getattr(self, name) for name in self.PANEL_ORDER)

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(self)
        payload["questions"] = dict(QUESTIONS)
        payload["panel_order"] = list(self.PANEL_ORDER)
        # `absence_kind`／`absence_is_settled` 是 property（宣告好的挑選規則），不是欄位。
        # 序列化後的消費端沒有 property，所以在這裡一次寫出來——否則 APP 會自己再實作一次
        # 那條規則，而重造品會立刻開始偏離（L16）。
        for name in self.PANEL_ORDER:
            panel = getattr(self, name)
            payload[name]["absence_kind"] = panel.absence_kind
            payload[name]["absence_is_settled"] = panel.absence_is_settled
        payload["absence_kinds"] = dict(ABSENCE_KINDS)
        payload["settled_absence_kinds"] = sorted(SETTLED_ABSENCE_KINDS)
        payload["accounting_basis_display"] = {k: dict(v) for k, v in ACCOUNTING_BASIS_DISPLAY.items()}
        return payload


def worst_status(statuses: Sequence[str]) -> str:
    """取最嚴的 status。**不是新判斷**：`_WORST_FIRST` 是宣告好的嚴重度序，這裡只查表取 index 最大者。"""
    if not statuses:
        raise AnalystViewContractViolation("worst_status 需要至少一個 status——空集合不是 available")
    for status in statuses:
        _check(status, set(_WORST_FIRST), "worst_status 輸入")
    return max(statuses, key=_WORST_FIRST.index)


def readiness_class(status: str) -> str:
    """一個 status 對 readiness 的貢獻（查表；`missing` 與 `not_modeled` 都算缺內容，但理由不同）。"""
    _check(status, set(_READINESS_CLASS), "readiness_class 輸入")
    return _READINESS_CLASS[status]


__all__ = [
    "PLAIN_ABSENCE_SHORT",
    "PLAIN_LINE_LABELS",
    "PLAIN_PANEL_TITLES",
    "PLAIN_READINESS",
    "PRICE_SERIES_NOTE",
    "ACCOUNTING_BASIS_DISPLAY", "AnalystBlocker", "accounting_basis_display",
    "AnalystLine", "AnalystPanel", "AnalystReadiness", "AnalystView", "AnalystViewContractViolation",
    "BLOCKED", "CORE_PANELS", "LINE_ROLES", "OPTIONAL_PANELS", "QUESTIONS", "READINESS_STATES",
    "READY", "READY_WITH_FLAGS", "RefreshSummary", "SCHEMA_VERSION", "WEAK_INPUT_RULES", "WeakInput",
    "readiness_class", "worst_status",
]
