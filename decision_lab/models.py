"""Decision Lab v1 的 immutable domain records。"""
from __future__ import annotations

from dataclasses import dataclass


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
