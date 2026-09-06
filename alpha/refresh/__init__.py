"""Research Refresh／Dependency Invalidation v1（Step 0.5，2026-09-06）。

回答：**什麼變了？影響哪些研究成果？哪些只需重算？哪些需要重新研究？哪些已失效？**

```
ChangeEvent[]（組裝層由 authority 時序導出；不是 digest diff）
        ↓
resolve_refresh（policy 表 × 既有 provenance；不 cascade、不自動呼叫 LLM）
        ↓
RefreshReport → AffectedArtifact[]（state＋理由＋變了哪個依賴＋下一步）
```

它是 dependency／orchestration authority：不產生事實、不產生假設、不改 thesis；
只決定 impact state。純邏輯、零外部相依（`tests/test_refresh_engine.py` 守著）。
"""
from __future__ import annotations

from .artifacts import (
    AXIS_LABEL, THESIS_ARTIFACT_ID, artifacts_from_context, artifacts_from_model,
    artifacts_from_signal, build_instant, end_of_day, start_of_day,
)
from .contracts import (
    ARTIFACT_ASSUMPTION, ARTIFACT_AXIS, ARTIFACT_COMPARISON, ARTIFACT_MARKET_IMPLIED,
    ARTIFACT_METRIC, ARTIFACT_MODEL, ARTIFACT_THESIS, ARTIFACT_TYPES, CHANGE_TYPES,
    COMPANY_GUIDANCE, CONSENSUS, CONTEXT_DIGEST, CONTRACT_VERSION, CURRENT, DISPROOF_SIGNAL,
    EVIDENCE, FINANCIAL_ACTUAL, FISCAL_PERIOD_ROLLOVER, GRAPH_CLAIM, GRAPH_EDGE, INVALIDATED,
    KIND_DETERMINISTIC, KIND_JUDGMENT, MARKET_PRICE, MISSING, OPERATING_ASSUMPTION, RECALCULATE,
    REFRESH_STATES, REQUIRED_ACTION, REVIEW_REQUIRED, ROLE_CALIBRATION, ROLE_COMPARISON,
    ROLE_INPUT, ROLE_LEGACY, ROLE_OBSERVATION, ROLE_SUPPORTING, STALE, SUPERSEDED, THESIS_REVIEW_DUE,
    AffectedArtifact, ArtifactDependency, ChangeEvent, MetricObservation, RefreshReport,
    ReviewCondition, merge_states,
)
from .policy import (
    AXIS_POLICY, CONSENSUS_NOISE_FLOOR_REL, GUIDANCE_FIELD_DRIVERS, POLICY_VERSION,
    frequency_to_days, guidance_driver,
)
from .resolver import resolve_refresh

__all__ = [
    "ARTIFACT_ASSUMPTION", "ARTIFACT_AXIS", "ARTIFACT_COMPARISON", "ARTIFACT_MARKET_IMPLIED",
    "ARTIFACT_METRIC", "ARTIFACT_MODEL", "ARTIFACT_THESIS", "ARTIFACT_TYPES", "AXIS_LABEL",
    "AXIS_POLICY", "CHANGE_TYPES", "COMPANY_GUIDANCE", "CONSENSUS", "CONSENSUS_NOISE_FLOOR_REL",
    "CONTEXT_DIGEST", "CONTRACT_VERSION", "CURRENT", "DISPROOF_SIGNAL", "EVIDENCE",
    "FINANCIAL_ACTUAL", "FISCAL_PERIOD_ROLLOVER", "GRAPH_CLAIM", "GRAPH_EDGE",
    "GUIDANCE_FIELD_DRIVERS", "INVALIDATED", "KIND_DETERMINISTIC", "KIND_JUDGMENT",
    "MARKET_PRICE", "MISSING", "OPERATING_ASSUMPTION", "POLICY_VERSION", "RECALCULATE",
    "REFRESH_STATES", "REQUIRED_ACTION", "REVIEW_REQUIRED", "ROLE_CALIBRATION", "ROLE_COMPARISON",
    "ROLE_INPUT", "ROLE_LEGACY", "ROLE_OBSERVATION", "ROLE_SUPPORTING", "STALE", "SUPERSEDED",
    "THESIS_ARTIFACT_ID", "THESIS_REVIEW_DUE", "AffectedArtifact", "ArtifactDependency",
    "ChangeEvent", "MetricObservation", "RefreshReport", "ReviewCondition",
    "artifacts_from_context", "artifacts_from_model", "artifacts_from_signal", "build_instant", "end_of_day",
    "frequency_to_days", "guidance_driver", "merge_states", "resolve_refresh", "start_of_day",
]
