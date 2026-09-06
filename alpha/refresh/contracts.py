"""Research Refresh／Dependency Invalidation 的型別契約。**只有型別與驗證，零外部相依。**

## 這一層回答什麼

> 什麼變了？影響哪些研究成果？哪些只需重算？哪些需要重新研究？哪些已失效？

它是 **dependency／orchestration authority**，不是 analyst authority：

- 不產生新的事實（A1／A2 不動）。
- 不產生新的假設、不改 thesis、不改 judgment（A3 的內容不動）。
- 只決定每個既有研究成果**相對於它的依賴**處在哪一種 refresh state，並說出為什麼。
- **不自動呼叫 LLM。** 需要判斷的東西一律停在 `review_required`／`invalidated`，
  等 session／人接手；`tests/test_refresh_engine.py` 以 import 掃描守著。

## 兩條在型別層強制的規則

1. **state 是封閉字彙（contract）。** 每個 state 對應一種不同的下一步：重算不用判斷、
   複查要判斷、失效不得再當 current、stale 只是日曆到期。多一個 state ＝ 多一種下一步，
   必須有人設計；打開它是 bug。
2. **freshness 與 invalidation 分開。** `stale`（時間到了）與 `review_required`（有新證據
   動搖依據）與 `invalidated`（已知前提不成立）是三個 state，不得都叫 stale（L12）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from ..contracts import content_digest
from ..errors import ContractViolation

CONTRACT_VERSION = "refresh-contract/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙
# ---------------------------------------------------------------------------

CURRENT = "current"                    # 依賴沒有 materially changed
RECALCULATE = "recalculate"            # 輸入變了，下游是 deterministic——重算即可，不需判斷
REVIEW_REQUIRED = "review_required"    # 依據發生 material change；舊判斷只剩歷史價值，不得當 current
INVALIDATED = "invalidated"            # 已知前提不成立（證據撤回、關鍵邊移除、disproof 觸發）
STALE = "stale"                        # 純時間／schedule 到期，不隱含任何新證據
SUPERSEDED = "superseded"              # 已被較新的同 key 紀錄或同期實際值取代——只是歷史
MISSING = "missing"                    # 這個成果在此視角下不存在（as-of 之後才建立、或從未建立）

REFRESH_STATES: tuple[str, ...] = (
    CURRENT, RECALCULATE, REVIEW_REQUIRED, INVALIDATED, STALE, SUPERSEDED, MISSING,
)

#: 同一成果同時被多種 change 觸及時的合併順序（大者勝）。`superseded`／`missing` 是**終局**
#: state，由 artifact 自帶，不參與合併。
_PRECEDENCE: Mapping[str, int] = {
    CURRENT: 0, STALE: 1, RECALCULATE: 2, REVIEW_REQUIRED: 3, INVALIDATED: 4,
}

#: 每個 state 的固定下一步（機器可讀；消費端不得自己猜）。
REQUIRED_ACTION: Mapping[str, str] = {
    CURRENT: "none",
    RECALCULATE: "recompute deterministically from current inputs; no judgment needed",
    REVIEW_REQUIRED: "reassess in a session; do not auto-replace; old value is historical only",
    INVALIDATED: "do not use as current view; retire or re-establish with new evidence",
    STALE: "scheduled review is due; no new evidence implied",
    SUPERSEDED: "historical only; a newer record or the reported actual replaced it",
    MISSING: "not established at this point in time",
}

# change class 也是 contract：每一類對應 policy 表裡的一列規則。
MARKET_PRICE = "market_price"
CONSENSUS = "consensus"
FINANCIAL_ACTUAL = "financial_actual"
COMPANY_GUIDANCE = "company_guidance"
GRAPH_EDGE = "graph_edge"
GRAPH_CLAIM = "graph_claim"
EVIDENCE = "evidence"
OPERATING_ASSUMPTION = "operating_assumption"
FISCAL_PERIOD_ROLLOVER = "fiscal_period_rollover"
THESIS_REVIEW_DUE = "thesis_review_due"
DISPROOF_SIGNAL = "disproof_signal"
#: 殘餘：context digest 變了，但沒有任何 change class 能解釋——**必須現形**，不得吞掉。
CONTEXT_DIGEST = "context_digest"

CHANGE_TYPES: tuple[str, ...] = (
    MARKET_PRICE, CONSENSUS, FINANCIAL_ACTUAL, COMPANY_GUIDANCE, GRAPH_EDGE, GRAPH_CLAIM,
    EVIDENCE, OPERATING_ASSUMPTION, FISCAL_PERIOD_ROLLOVER, THESIS_REVIEW_DUE, DISPROOF_SIGNAL,
    CONTEXT_DIGEST,
)

# artifact 型別。判斷型（session 判斷／假設）與確定性型（模型輸出）在 policy 裡走不同 state。
ARTIFACT_AXIS = "axis"
ARTIFACT_THESIS = "thesis"
ARTIFACT_ASSUMPTION = "operating_assumption"
ARTIFACT_METRIC = "modeled_metric"
ARTIFACT_COMPARISON = "expectation_comparison"
ARTIFACT_MARKET_IMPLIED = "market_implied"
ARTIFACT_MODEL = "fundamental_model"

ARTIFACT_TYPES: tuple[str, ...] = (
    ARTIFACT_AXIS, ARTIFACT_THESIS, ARTIFACT_ASSUMPTION, ARTIFACT_METRIC, ARTIFACT_COMPARISON,
    ARTIFACT_MARKET_IMPLIED, ARTIFACT_MODEL,
)

#: 成果的「性質」：判斷型輸入變了要人複查；確定性型輸入變了重算就好。
KIND_JUDGMENT = "judgment"
KIND_DETERMINISTIC = "deterministic"

#: 依賴的角色。`supporting`＝支持這個判斷為真的證據；`calibration`＝用來校準數字的脈絡
#: （例：知道市場隱含 +67% 所以選 +60%）；`comparison`＝拿來比較的對象；`observation`＝
#: 算術的基期觀測；`input`＝上游假設；`legacy_unclassified`＝舊紀錄未宣告角色，**fail safe
#: 當 supporting**。
ROLE_SUPPORTING = "supporting"
ROLE_CALIBRATION = "calibration"
ROLE_COMPARISON = "comparison"
ROLE_OBSERVATION = "observation"
ROLE_INPUT = "input"
ROLE_LEGACY = "legacy_unclassified"
DEPENDENCY_ROLES: tuple[str, ...] = (
    ROLE_SUPPORTING, ROLE_CALIBRATION, ROLE_COMPARISON, ROLE_OBSERVATION, ROLE_INPUT, ROLE_LEGACY,
)

#: disproof／review 條件觸發後的 state（由條件自己宣告，引擎不猜）。
ON_TRIGGER_STATES: tuple[str, ...] = (REVIEW_REQUIRED, INVALIDATED)


def _check(value: str, allowed: Sequence[str], label: str) -> str:
    if value not in allowed:
        raise ContractViolation(f"{label} 未登記：{value!r}；已知 {list(allowed)}")
    return value


def _aware(value: datetime | None, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ContractViolation(f"{label} 必須是帶時區的 datetime：{value!r}")
    return value


def merge_states(states: Sequence[str]) -> str:
    """多個 state 合併：取優先序最高者；空集合＝current。終局 state 不在這裡合併。"""
    best = CURRENT
    for state in states:
        if state in (SUPERSEDED, MISSING):
            raise ContractViolation(f"{state} 是終局 state，不參與合併")
        if _PRECEDENCE[_check(state, REFRESH_STATES, "refresh state")] > _PRECEDENCE[best]:
            best = state
    return best


# ---------------------------------------------------------------------------
# 1. ChangeEvent——「什麼變了」的 canonical 表示
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """一件已經發生、可歸類的變化。

    ⚠ 它**不是** `digest changed`。每個事件必須說得出 class、哪個 authority、哪個物件、
    什麼時候知道的（`observed_at`）、事實屬於哪一天（`effective_at`）、哪些欄位變了。
    `observed_at` 是 PIT 的骨架：as-of T 只看得到 `observed_at <= T` 的事件。
    """

    change_type: str
    ticker: str
    authority: str
    changed_ref: str
    observed_at: datetime
    company_id: str | None = None
    effective_at: date | None = None
    #: 世界何時知道（一手文件的發表／申報日）。有值時，「判斷當時知不知道」用它而不是 `observed_at`：
    #: 8-K 在 08-12 發表、我們 09-05 才寫進 ledger，09-04 的 session 判斷**讀得到**那份 8-K——它不是新變化。
    #: 行情／共識沒有這個欄位：session 只看得到 packet 裡的快照，用 `observed_at`（fetched_at）。
    #: as-of 可見性一律用 `observed_at`（T 之前沒進系統的東西在 T 就是不知道，INV-6）。
    published_at: date | None = None
    old_version: str | None = None
    new_version: str | None = None
    material_fields: tuple[str, ...] = ()
    detail: str = ""
    related_refs: tuple[str, ...] = ()
    #: `disproof_signal`／`thesis_review_due` 專用：指名要影響的 artifact id。
    target_artifact: str | None = None
    #: `disproof_signal` 專用：條件宣告的觸發後 state。
    on_trigger: str | None = None

    def __post_init__(self) -> None:
        _check(self.change_type, CHANGE_TYPES, "ChangeEvent.change_type")
        if not self.ticker or not self.authority or not self.changed_ref:
            raise ContractViolation("ChangeEvent 的 ticker／authority／changed_ref 必須非空")
        _aware(self.observed_at, "ChangeEvent.observed_at")
        if self.on_trigger is not None:
            _check(self.on_trigger, ON_TRIGGER_STATES, "ChangeEvent.on_trigger")
        if self.change_type == DISPROOF_SIGNAL and not self.target_artifact:
            raise ContractViolation("disproof_signal 必須指名 target_artifact")

    @property
    def change_id(self) -> str:
        return "chg_" + content_digest(self)[7:23]

    def known_at(self) -> datetime:
        """成果「建立當時能不能知道」的比較時點。"""
        if self.published_at is not None:
            return datetime.combine(self.published_at, datetime.max.time().replace(microsecond=0),
                                    tzinfo=self.observed_at.tzinfo)
        return self.observed_at

    @property
    def refs(self) -> frozenset[str]:
        return frozenset((self.changed_ref, *self.related_refs))


# ---------------------------------------------------------------------------
# 2. ReviewCondition／MetricObservation——machine-readable 的觸發條件與可對照的觀測
# ---------------------------------------------------------------------------

REVIEW_OPERATORS: tuple[str, ...] = ("<", "<=", ">", ">=")
OBSERVATION_PERIOD_KINDS: tuple[str, ...] = ("fiscal_year", "fiscal_quarter")


@dataclass(frozen=True, slots=True)
class ReviewCondition:
    """假設自帶的可觀測觸發條件。**不是 parser 從 rationale 抽出來的**——由寫假設的人明示。

    `note` 是人寫的「觸發後打算怎麼做」（例：下修至 +45%）；引擎**只讀不做**——
    觸發後 state 變成 `on_trigger`，新的數值仍是下一個 session 的判斷。
    """

    metric: str
    scope: str
    period_end: date
    period_kind: str
    operator: str
    threshold: float
    on_trigger: str = REVIEW_REQUIRED
    note: str = ""

    def __post_init__(self) -> None:
        if not self.metric or not self.scope:
            raise ContractViolation("ReviewCondition.metric／scope 必須非空")
        if not isinstance(self.period_end, date) or isinstance(self.period_end, datetime):
            raise ContractViolation("ReviewCondition.period_end 必須是 date")
        _check(self.period_kind, OBSERVATION_PERIOD_KINDS, "ReviewCondition.period_kind")
        _check(self.operator, REVIEW_OPERATORS, "ReviewCondition.operator")
        if isinstance(self.threshold, bool) or not isinstance(self.threshold, (int, float)):
            raise ContractViolation("ReviewCondition.threshold 必須是數值")
        _check(self.on_trigger, ON_TRIGGER_STATES, "ReviewCondition.on_trigger")

    def holds(self, value: float) -> bool:
        if self.operator == "<":
            return value < self.threshold
        if self.operator == "<=":
            return value <= self.threshold
        if self.operator == ">":
            return value > self.threshold
        return value >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric, "scope": self.scope, "period_end": self.period_end.isoformat(),
            "period_kind": self.period_kind, "operator": self.operator,
            "threshold": float(self.threshold), "on_trigger": self.on_trigger, "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ReviewCondition":
        try:
            return cls(
                metric=str(raw["metric"]), scope=str(raw.get("scope") or "total"),
                period_end=date.fromisoformat(str(raw["period_end"])[:10]),
                period_kind=str(raw.get("period_kind") or "fiscal_quarter"),
                operator=str(raw["operator"]), threshold=float(raw["threshold"]),
                on_trigger=str(raw.get("on_trigger") or REVIEW_REQUIRED), note=str(raw.get("note") or ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractViolation(f"ReviewCondition 欄位不合法：{exc}") from None


@dataclass(frozen=True, slots=True)
class MetricObservation:
    """一筆可拿來對照 `ReviewCondition` 的觀測（由組裝層從 Engine C 觀測攤平而來）。"""

    metric: str
    scope: str
    period_end: date
    period_kind: str
    value: float
    ref: str
    observed_at: datetime

    def __post_init__(self) -> None:
        _check(self.period_kind, OBSERVATION_PERIOD_KINDS, "MetricObservation.period_kind")
        _aware(self.observed_at, "MetricObservation.observed_at")


# ---------------------------------------------------------------------------
# 3. ArtifactDependency——每個研究成果宣告它依賴什麼（由既有 provenance 導出，不另建一套）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArtifactDependency:
    """一個研究成果＋它的依賴。

    `refs` 的來源固定：session 軸＝`ComponentTrace.evidence_refs`；假設＝`evidence_refs`＋
    `dependency_roles`；模型輸出＝`assumption_ids`＋`observation_refs`；比較＝`consensus_refs`。
    這裡**不重新推導依賴**，只把既有 provenance 攤平成 ref → role。
    """

    artifact_type: str
    artifact_id: str
    label: str
    kind: str
    established_at: datetime | None
    refs: Mapping[str, str] = field(default_factory=dict)
    assumption_ids: tuple[str, ...] = ()
    basis: str | None = None
    driver: str | None = None
    scope: str | None = None
    period_end: date | None = None
    review_conditions: tuple[ReviewCondition, ...] = ()
    check_frequency_days: int | None = None
    #: 終局 state（`superseded`／`missing`／`invalidated`）由建構端直接宣告，附理由。
    preset_state: str | None = None
    preset_reason: str | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check(self.artifact_type, ARTIFACT_TYPES, "ArtifactDependency.artifact_type")
        _check(self.kind, (KIND_JUDGMENT, KIND_DETERMINISTIC), "ArtifactDependency.kind")
        if not self.artifact_id or not self.label:
            raise ContractViolation("ArtifactDependency.artifact_id／label 必須非空")
        _aware(self.established_at, "ArtifactDependency.established_at")
        for ref, role in self.refs.items():
            if not ref:
                raise ContractViolation("ArtifactDependency.refs 的 key 必須非空")
            _check(role, DEPENDENCY_ROLES, f"ArtifactDependency.refs[{ref}]")
        if self.preset_state is not None:
            _check(self.preset_state, REFRESH_STATES, "ArtifactDependency.preset_state")
            if not self.preset_reason:
                raise ContractViolation("preset_state 必須附 preset_reason（因果不得被截斷，L12）")

    @property
    def key(self) -> str:
        return f"{self.artifact_type}:{self.artifact_id}"

    def refs_with_role(self, *roles: str) -> frozenset[str]:
        return frozenset(r for r, role in self.refs.items() if role in roles)


# ---------------------------------------------------------------------------
# 4. AffectedArtifact／RefreshReport——輸出
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AffectedArtifact:
    artifact_type: str
    artifact_id: str
    label: str
    state: str
    reasons: tuple[str, ...] = ()
    changed_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    detected_at: datetime | None = None
    established_at: datetime | None = None
    required_action: str = ""
    propagated_from: tuple[str, ...] = ()
    kind: str = KIND_JUDGMENT

    def __post_init__(self) -> None:
        _check(self.state, REFRESH_STATES, "AffectedArtifact.state")
        if self.state != CURRENT and not self.reasons:
            raise ContractViolation(
                f"{self.artifact_type}:{self.artifact_id} state={self.state} 必須附 reasons（L12）")
        if not self.required_action:
            object.__setattr__(self, "required_action", REQUIRED_ACTION[self.state])

    @property
    def key(self) -> str:
        return f"{self.artifact_type}:{self.artifact_id}"

    @property
    def is_current(self) -> bool:
        return self.state == CURRENT


@dataclass(frozen=True, slots=True)
class RefreshReport:
    """一次 impact resolution 的完整輸出。**同一組輸入永遠得到同一個 digest。**"""

    ticker: str
    company_id: str | None
    as_of: date | None
    reference_day: date
    policy_version: str
    changes: tuple[ChangeEvent, ...]
    artifacts: tuple[AffectedArtifact, ...]
    excluded_changes: Mapping[str, int] = field(default_factory=dict)
    excluded_artifacts: Mapping[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    contract_version: str = CONTRACT_VERSION
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.digest:
            object.__setattr__(self, "digest", content_digest({
                "ticker": self.ticker, "company_id": self.company_id, "as_of": self.as_of,
                "reference_day": self.reference_day, "policy": self.policy_version,
                "changes": [c.change_id for c in self.changes],
                "artifacts": [(a.key, a.state, a.reasons) for a in self.artifacts],
            }))

    @property
    def counts(self) -> dict[str, int]:
        out = {state: 0 for state in REFRESH_STATES}
        for artifact in self.artifacts:
            out[artifact.state] += 1
        return out

    @property
    def overall(self) -> str:
        """整體＝最需要動作的那個 state（終局 state 不算）。"""
        live = [a.state for a in self.artifacts if a.state not in (SUPERSEDED, MISSING)]
        return merge_states(live)

    @property
    def attention(self) -> tuple[AffectedArtifact, ...]:
        """需要人或重算的項目（非 current、非終局）。"""
        return tuple(a for a in self.artifacts if a.state not in (CURRENT, SUPERSEDED, MISSING))

    def artifact(self, key: str) -> AffectedArtifact | None:
        for artifact in self.artifacts:
            if artifact.key == key or artifact.artifact_id == key:
                return artifact
        return None


__all__ = [
    "ARTIFACT_ASSUMPTION", "ARTIFACT_AXIS", "ARTIFACT_COMPARISON", "ARTIFACT_MARKET_IMPLIED",
    "ARTIFACT_METRIC", "ARTIFACT_MODEL", "ARTIFACT_THESIS", "ARTIFACT_TYPES", "AffectedArtifact",
    "ArtifactDependency", "CHANGE_TYPES", "COMPANY_GUIDANCE", "CONSENSUS", "CONTEXT_DIGEST",
    "CONTRACT_VERSION", "CURRENT", "ChangeEvent", "DEPENDENCY_ROLES", "DISPROOF_SIGNAL",
    "EVIDENCE", "FINANCIAL_ACTUAL", "FISCAL_PERIOD_ROLLOVER", "GRAPH_CLAIM", "GRAPH_EDGE",
    "INVALIDATED", "KIND_DETERMINISTIC", "KIND_JUDGMENT", "MARKET_PRICE", "MISSING",
    "MetricObservation", "ON_TRIGGER_STATES", "OPERATING_ASSUMPTION", "RECALCULATE",
    "REFRESH_STATES", "REQUIRED_ACTION", "REVIEW_REQUIRED", "ROLE_CALIBRATION", "ROLE_COMPARISON",
    "ROLE_INPUT", "ROLE_LEGACY", "ROLE_OBSERVATION", "ROLE_SUPPORTING", "RefreshReport",
    "ReviewCondition", "STALE", "SUPERSEDED", "THESIS_REVIEW_DUE", "merge_states",
]
