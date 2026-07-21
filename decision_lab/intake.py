"""Signal → Probe／Shadow 的 deterministic intake。"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .adapters.holdings import execution_aliases
from .identity import resolve_identity
from .models import CaptureResult, MarketObservation, SignalInput
from .store import DecisionStore


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SOURCE_CONFIG = _ROOT / "config" / "signal_sources.json"
_SOURCE_STATUSES = {"candidate", "probation", "active", "suspended"}
_DIRECTIONS = {"long", "short", "neutral"}
_MARKET_STATUSES = {"observed", "missing", "unavailable"}


class MarketObserver(Protocol):
    def observe(self, company_id: str, research_ticker: str, observed_at: str) -> MarketObservation: ...


@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    status: str
    research_priority: int
    auto_capture: bool


class SignalSourceRegistry:
    """Versioned read-only attention policy；不是 evidence gate。"""

    def __init__(self, *, version: int, policies: tuple[SourcePolicy, ...]):
        if version < 1:
            raise ValueError("signal source registry version must be positive")
        by_id: dict[str, SourcePolicy] = {}
        for policy in policies:
            if policy.status not in _SOURCE_STATUSES:
                raise ValueError(f"invalid signal source status: {policy.status}")
            if policy.research_priority < 0:
                raise ValueError("research_priority must be non-negative")
            key = policy.source_id.strip().lower()
            if not key or key in by_id:
                raise ValueError(f"invalid or duplicate source_id: {policy.source_id!r}")
            by_id[key] = policy
        self.version = version
        self._by_id = by_id

    @classmethod
    def from_path(cls, path: Path = _DEFAULT_SOURCE_CONFIG) -> "SignalSourceRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=int(payload["version"]),
            policies=tuple(SourcePolicy(**item) for item in payload["sources"]),
        )

    def snapshot(self, source_id: str) -> SourcePolicy:
        return self._by_id.get(
            source_id.strip().lower(),
            SourcePolicy(
                source_id=source_id.strip().lower() or "unattributed",
                status="candidate",
                research_priority=0,
                auto_capture=False,
            ),
        )


def _parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _normalize_claim(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _validate_signal(signal: SignalInput) -> None:
    if not signal.raw_text.strip() or not signal.atomic_claim.strip():
        raise ValueError("raw_text and atomic_claim are required")
    if not signal.source_id.strip() or not signal.origin_event.strip():
        raise ValueError("source attribution and origin_event are required")
    if urlparse(signal.source_uri).scheme not in {"http", "https", "fixture"}:
        raise ValueError("source_uri must be an attributable URI")
    if signal.direction not in _DIRECTIONS:
        raise ValueError("direction must be long, short, or neutral")
    if not signal.disproof.strip():
        raise ValueError("disproof is required")
    if isinstance(signal.evidence_tier, bool) or signal.evidence_tier not in {1, 2, 3, 4}:
        raise ValueError("evidence_tier must be 1..4")
    observed = _parse_time(signal.observed_at, "observed_at")
    if _parse_time(signal.expiry, "expiry") <= observed:
        raise ValueError("expiry must be after observed_at")
    if signal.capture_mode not in {"manual", "automatic"}:
        raise ValueError("capture_mode must be manual or automatic")


def _validate_market(observation: MarketObservation) -> MarketObservation:
    if observation.status not in _MARKET_STATUSES:
        return MarketObservation(status="unavailable")
    if observation.status != "observed":
        return MarketObservation(status=observation.status)
    if (
        isinstance(observation.price, bool)
        or not isinstance(observation.price, (int, float))
        or not math.isfinite(float(observation.price))
        or float(observation.price) <= 0
        or not observation.currency
        or not observation.source
        or not observation.as_of
        or not observation.fetched_at
    ):
        return MarketObservation(status="unavailable")
    _parse_time(observation.as_of, "market.as_of")
    _parse_time(observation.fetched_at, "market.fetched_at")
    return MarketObservation(
        status="observed",
        price=float(observation.price),
        currency=observation.currency.upper(),
        source=observation.source,
        as_of=observation.as_of,
        fetched_at=observation.fetched_at,
    )


def _claim_key(signal: SignalInput, company_id: str) -> str:
    payload = json.dumps(
        {
            "company_id": company_id,
            "claim": _normalize_claim(signal.atomic_claim),
            "direction": signal.direction,
            "expiry": signal.expiry,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "claim:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def capture_signal(
    store: DecisionStore,
    signal: SignalInput,
    *,
    market: MarketObserver,
    source_registry: SignalSourceRegistry | None = None,
) -> CaptureResult:
    """Validate and atomically capture one signal plus immutable Shadow inception。"""

    _validate_signal(signal)
    registry = source_registry or SignalSourceRegistry.from_path()
    source_policy = registry.snapshot(signal.source_id)
    if signal.capture_mode == "automatic" and not (
        source_policy.status == "active" and source_policy.auto_capture
    ):
        raise ValueError("source is not authorized for automatic capture")

    identity = resolve_identity(
        company_id=signal.company_id,
        research_ticker=signal.research_ticker,
        execution_aliases=execution_aliases(),
    )
    if identity.blockers:
        raise ValueError(identity.blockers[0])
    assert identity.company_id and identity.research_ticker and identity.execution_symbol

    try:
        market_observation = market.observe(
            identity.company_id,
            identity.research_ticker,
            signal.observed_at,
        )
    except Exception:
        market_observation = MarketObservation(status="unavailable")
    market_observation = _validate_market(market_observation)

    evidence_admission = (
        "eligible_for_review"
        if signal.source_traced and signal.evidence_tier <= 3
        else "lead_only"
    )
    payload = {
        "raw_text": signal.raw_text,
        "source_id": signal.source_id,
        "source_uri": signal.source_uri,
        "origin_event": signal.origin_event,
        "observed_at": signal.observed_at,
        "atomic_claim": signal.atomic_claim,
        "direction": signal.direction,
        "expiry": signal.expiry,
        "disproof": signal.disproof,
        "evidence_tier": signal.evidence_tier,
        "source_traced": signal.source_traced,
        "source_registry": asdict(source_policy) | {"version": registry.version},
        "identity": asdict(identity),
    }
    captured = store.capture_signal_inception(
        dedupe_key=_claim_key(signal, identity.company_id),
        company_id=identity.company_id,
        research_ticker=identity.research_ticker,
        signal_payload=payload,
        observed_at=signal.observed_at,
        shadow=asdict(market_observation),
        evidence_admission_status=evidence_admission,
        source_registry_status=source_policy.status,
        research_priority=source_policy.research_priority,
    )
    return CaptureResult(
        cohort_id=captured["cohort_id"],
        signal_event_id=captured["signal_event_id"],
        shadow_id=captured["shadow_id"],
        shadow_created=captured["shadow_created"],
        source_status=source_policy.status,
        evidence_tier=signal.evidence_tier,
        company_id=identity.company_id,
        research_ticker=identity.research_ticker,
        execution_symbol=identity.execution_symbol,
    )
