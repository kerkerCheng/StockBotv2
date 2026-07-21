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
    company_id: str
    research_ticker: str
    execution_symbol: str


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
    paper_supported_position: float
    live_supported_range: tuple[float, float]
    work_order_id: str | None


@dataclass(frozen=True)
class ProbeSizingResult:
    cohort_id: str
    context_digest: str
    policy_version: str
    rubric_version: str
    calculator_version: str
    identity_registry_version: int
    weakest_axis: str
    axis_ceiling: float
    axis_results: Mapping[str, Mapping[str, Any]]
    assessment_blockers: tuple[str, ...]
    paper_status: str
    paper_target: float
    paper_max_supported_position: float
    paper_current_position: float
    paper_blockers: tuple[str, ...]
    live_status: str
    live_supported_range: tuple[float, float]
    live_supported_shares: tuple[float, float] | None
    live_current_position: float
    live_blockers: tuple[str, ...]
    constraint_trace: tuple[Mapping[str, Any], ...]
    action: str


@dataclass(frozen=True)
class DecisionExecutionResult:
    decision_id: str
    decision_digest: str
    paper_event_id: str | None
    paper_funded: bool
    paper_target: float
    paper_max_supported_position: float
    action: str


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
