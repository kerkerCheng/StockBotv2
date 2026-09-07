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

    def __post_init__(self) -> None:
        _check(self.state, READINESS_STATES, "AnalystReadiness.state")


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
    "AnalystLine", "AnalystPanel", "AnalystReadiness", "AnalystView", "AnalystViewContractViolation",
    "BLOCKED", "CORE_PANELS", "LINE_ROLES", "OPTIONAL_PANELS", "QUESTIONS", "READINESS_STATES",
    "READY", "READY_WITH_FLAGS", "RefreshSummary", "SCHEMA_VERSION", "WEAK_INPUT_RULES", "WeakInput",
    "readiness_class", "worst_status",
]
