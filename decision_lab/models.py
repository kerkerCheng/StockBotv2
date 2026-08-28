"""Decision Lab v1 的 immutable domain records。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SignalInput:
    raw_text: str
    source_id: str
    source_uri: str
    origin_event: str
    observed_at: str
    atomic_claim: str
    direction: str
    expiry: str
    disproof: str
    evidence_tier: int
    company_id: str | None = None
    research_ticker: str | None = None
    capture_mode: str = "manual"
    source_traced: bool = False


@dataclass(frozen=True)
class MarketObservation:
    status: str
    ticker: str | None = None
    price: float | None = None
    currency: str | None = None
    source: str | None = None
    as_of: str | None = None
    fetched_at: str | None = None


@dataclass(frozen=True)
class ShadowBaseline:
    shadow_id: str
    cohort_id: str
    status: str
    ticker: str | None
    price: float | None
    currency: str | None
    source: str | None
    as_of: str | None
    fetched_at: str | None

    @property
    def market_return_status(self) -> str:
        return "pending" if self.status == "observed" and self.price is not None else "unknown"


@dataclass(frozen=True)
class ProbeRecord:
    cohort_id: str
    status: str
    evidence_admission_status: str
    source_registry_status: str
    research_priority: int


@dataclass(frozen=True)
class CaptureResult:
    cohort_id: str
    signal_event_id: str
    shadow_id: str
    shadow_created: bool
    source_status: str
    evidence_tier: int
    company_id: str | None
    research_ticker: str | None
    execution_symbol: str | None


@dataclass(frozen=True)
class ContextBundle:
    context_id: str
    cohort_id: str
    digest: str
    evaluation_at: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class CoverageResult:
    assessment_id: str
    cohort_id: str
    context_digest: str
    status: str
    blockers: tuple[str, ...]
    paper_blockers: tuple[str, ...]
    live_blockers: tuple[str, ...]
    paper_context_ready: bool
    live_context_ready: bool
    work_order_id: str | None


# 研究完整度的三態，取代先前的 `paper_status`／`live_status`（ELIGIBLE／SHADOW_ONLY／
# DATA_NEEDED）。舊字彙的 ELIGIBLE 意思是「可以配資本」，而系統已不再配資本；現在問的
# 是「這檔的研究做到什麼程度」，答案不帶額度語意。
#
# ⚠ 讀取端仍會遇到帶 `paper_status` 的舊 decision（Decision Store 是 append-only 的
# private authority，依 L10 不做破壞性 migration）。對應關係只有一條：
# 舊 `paper_status == "ELIGIBLE"` ≙ 新 `research_status == "READY"`。
RESEARCH_STATUSES: tuple[str, ...] = ("READY", "INCOMPLETE", "DATA_NEEDED")

# 舊 `paper_status` 的三個值到新三態的完整對應。
#
# ⚠ 這張表必須是**三對三**。首版只特判了 `ELIGIBLE`、其餘一律 `INCOMPLETE`，於是
# 131 筆歷史 decision 裡的 **85 筆 `DATA_NEEDED` 被靜默改寫成 `INCOMPLETE`**——而兩者
# 在新契約下的下一步不同（`INCOMPLETE` 要人去補研究，`DATA_NEEDED` 只要重抓資料），
# 且 `DATA_NEEDED` 會驅動 Action Card 的 REVIEW 分支、`INCOMPLETE` 不會。少一個 case
# 等於讓那 85 筆安靜退出待辦。`SHADOW_ONLY` 的語意是「資料齊但研究不足」＝ INCOMPLETE。
_LEGACY_PAPER_STATUS: dict[str, str] = {
    "ELIGIBLE": "READY",
    "SHADOW_ONLY": "INCOMPLETE",
    "DATA_NEEDED": "DATA_NEEDED",
}


def research_status_of(sizing: Mapping[str, Any]) -> str:
    """從 decision payload 的 `sizing` 取研究完整度，容忍 U7 之前的舊欄位。

    唯一的還原入口。先前 `action_card` 與 `store` 各寫一份，兩份都只特判 `ELIGIBLE`
    ——同一個分類在兩處被重造，正是 L16 要防的形狀，而重造品立刻開始偏離。
    """

    declared = sizing.get("research_status")
    if isinstance(declared, str) and declared in RESEARCH_STATUSES:
        return declared
    legacy = sizing.get("paper_status")
    return _LEGACY_PAPER_STATUS.get(str(legacy), "INCOMPLETE")

# Action Card 的注意力狀態，取代 U7 之前的四動作（`NO_ACTION`／`REVIEW`／`TRADE`／
# `HEDGE`）。`TRADE` 與 `HEDGE` 是資本動作，系統既不給尺寸也不連 broker，說出這兩個詞
# 等於宣稱一個它做不到的授權；它們原本的兩個情境（已接受 live 但未回報成交、投組曝險
# 超限）本質都是「請人看一下」，併入 `REVIEW`。
#
# 只剩兩態是刻意的：卡片唯一還能誠實回答的問題是「今天要不要看這一檔」。
ATTENTION_STATES: tuple[str, ...] = ("MONITOR", "REVIEW")


@dataclass(frozen=True)
class ProbeSizingResult:
    """五軸評估的結果：最弱軸、逐軸等級與 blocker。**不含任何資本欄位。**

    2026-08-28 起 `axis_ceiling`／`paper_target`／`live_supported_range`／
    `constraint_trace` 已移除——系統終點是瓶頸度排序，不是額度。留下的
    `live_current_position` 與 `single_position_nav_cap` 不是系統給的建議尺寸，
    是使用者手動記錄 live 選擇時的既有部位與政策參考線。
    """

    cohort_id: str
    context_digest: str
    policy_version: str
    rubric_version: str
    calculator_version: str
    identity_registry_version: int
    weakest_axis: str
    axis_results: Mapping[str, Mapping[str, Any]]
    assessment_blockers: tuple[str, ...]
    research_status: str
    paper_blockers: tuple[str, ...]
    live_blockers: tuple[str, ...]
    live_current_position: float
    single_position_nav_cap: float


@dataclass(frozen=True)
class DecisionExecutionResult:
    decision_id: str
    decision_digest: str
    research_status: str


@dataclass(frozen=True)
class PreparedAction:
    action_id: str
    action_type: str
    target_id: str
    digest: str
    expires_at: str


@dataclass(frozen=True)
class LifecycleResult:
    cohort_id: str
    epoch: int
    status: str
    review_due_at: str | None
    lifecycle_event_id: str | None


@dataclass(frozen=True)
class OutcomeResult:
    outcome_id: str
    cohort_id: str
    epoch: int
    terminal_status: str
    claim_correctness: str
    market_return_status: str
    absolute_return: float | None
    benchmark_adjusted_return: float | None


# Probe lifecycle 的**終態**集合。刻意不含 `revised`——它在 L7 語意是「修正後 thesis
# 繼續成立」，store 會為它開啟新 epoch，因此仍是進行中的 probe。誤把 revised 當終態
# 會讓已合併／已修正的 cohort 從佇列消失；反之誤把終態當進行中，會讓 handoff 指向一個
# 不會再產生 decision 的死 cohort。兩邊都踩過，故字彙集中在此，不在各模組各自複製。
TERMINAL_LIFECYCLE_STATUSES: frozenset[str] = frozenset(
    {"promoted", "rejected", "expired"}
)
