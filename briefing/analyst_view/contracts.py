"""Analyst View（Phase 2 Step 3.5）——**消費端的呈現 DTO**，不是第二份研究 authority。

## 這一層是什麼

`AlphaInvestmentView`（canonical read model，18 個 section）回答「系統對這家公司知道什麼」，
但它是**依資料結構排列**的：估值住第 13 節、報酬住 13a、共識住第 5 節、假設住第 8 節。
使用者打開一檔股票時要在很短時間內看懂五件事——**我們相信什麼、跟市場差在哪、怎麼算到這裡、
最弱的假設是什麼、什麼事會讓結論需要重看**——那五件事橫跨上述所有 section。

Analyst View 就是把同一份 view **依消費者問句重新投影**成四個核心 panel ＋ 一個 optional panel。

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
6. **Entry 是 optional capability，不是研究完整度 gate。** 主流程終點是 implied return；
   沒有 `EntryCriterion` 時只表示「optional entry threshold unavailable」，
   **不得讓 `readiness` 變差、不得把股票標成研究不完整、不得補 10%／15%／20%**。
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
    "q1_internal": "我們預測什麼？",
    "q2_market": "市場預測什麼？",
    "q3_gap": "差異在哪？",
    "q4_implied_return": "現價對我們的 future target 隱含什麼報酬？",
    "q5_fragile": "哪些假設最脆弱？",
    "q6_change": "什麼 evidence 會改變答案？",
}

#: 核心 panel（決定 `readiness`）與 optional panel（**不**決定 readiness）。
#: 主流程：Evidence → Internal Forecast → Valuation／Future Target Value → Horizon → Implied Return。
#: Entry threshold 是 optional analytical capability，刻意不在 CORE_PANELS 裡。
CORE_PANELS: tuple[str, ...] = ("headline", "fundamental", "why", "research")
OPTIONAL_PANELS: tuple[str, ...] = ("entry",)

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
    "headline_number",         # 頭條那一串數字的其中一格
    "headline_context",        # 頭條的語意脈絡（convention／horizon window／gap）
    "internal",                # 我們的預測
    "consensus_same_period",   # 同期、可比的市場預測
    "consensus_other_period",  # 其他期間的市場預測（**不可與內部相減**）
    "market_context",          # 非期間身分的市場觀測（分析師人數、目標價、PE…）
    "market_proxy",            # 價格隱含的粗略代理
    "comparison",              # 內部 vs 共識的數值落差
    "assumption",              # 生效的假設（營運／估值／horizon）
    "sensitivity",             # 既有敏感度（估值層算好的，不是本層新建的 attribution）
    "trace",                   # 算式的每一格
    "epistemics",              # 「多少是算術、多少是判斷」的分解
    "thesis",                  # 研究判斷本身
    "score",                   # Q1–Q5
    "lifecycle",               # thesis 狀態／到期／watch
    "entry",                   # optional entry threshold
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
    "headline": {"title": "結論：現在的價格划不划算",
                 "hint": "現價、我們算出的未來目標價、以及兩者之間要漲跌多少"},
    "fundamental": {"title": "我們和市場，預期差在哪",
                    "hint": "同一個會計期間、同一種口徑才拿來比；不可比的一律標「不可比」"},
    "why": {"title": "這個結論最脆弱的地方",
            "hint": "哪幾個假設最經不起挑戰——它們錯了，上面的數字就跟著錯"},
    "research": {"title": "什麼會推翻它",
                 "hint": "出場靠這些條件，不是靠感覺；還有什麼時候會知道答案"},
    "entry": {"title": "進場門檻（選配）",
              "hint": "你自己設的要求報酬換算成的價格。沒設不代表這檔研究不完整"},
}

#: 逐格標籤的白話版。沒列到的沿用 read model 的 `display_label`（那些多半本來就看得懂）。
PLAIN_LINE_LABELS: Mapping[str, str] = {
    "current_price": "現在股價",
    "fair_value": "我們算出的未來目標價",
    "value_date": "目標價是哪一天的值",
    "horizon": "多久之後",
    "price_return": "從現價到目標價，要漲跌多少",
    "annualized_price_return": "換算成一年多少",
    "epistemics_one_sentence": "一句話說明這個數字怎麼來的",
    "internal_revenue": "我們估的營收",
    "internal_operating_margin": "我們估的營益率",
    "internal_eps": "我們估的每股盈餘",
    "internal_gross_margin": "我們估的毛利率",
    "thesis": "我們的看法",
    "variant_view": "我們和市場看法差在哪",
    "direction": "看多還看空",
    "confidence": "信心程度",
    "expected_horizon": "預期多久見分曉",
    "criterion": "你要求的報酬",
    "required_annualized_return": "要求的年化報酬",
    "entry_price": "換算出來的門檻價",
    "price_to_entry_gap": "現價離門檻價多遠",
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
        """
        return self.absence_kind in SETTLED_ABSENCE_KINDS


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
    why: AnalystPanel
    research: AnalystPanel
    entry: AnalystPanel
    readiness: AnalystReadiness
    refresh: RefreshSummary
    limits: tuple[str, ...]
    warnings: tuple[str, ...]

    PANEL_ORDER = ("headline", "fundamental", "why", "research", "entry")

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
