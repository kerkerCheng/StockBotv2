"""Alpha Research Core — investment reasoning engine。

## 這一層回答什麼

**「我們認為未來會怎樣，跟市場現在 pricing 的未來有多不一樣？」**

五個問題（`AlphaSignal` 的五個維度）：
1. Structural Scarcity — 這家公司在產業結構上有多難被替代？
2. Economic Value Capture — 即使重要，它能不能把重要性轉成 economic rent？
3. Earnings / FCF Exposure — 這個優勢對上市公司的 EPS／FCF 到底多重要？
4. **Expectation Gap** — 我們預期的未來，跟市場定價的未來差多少？（系統最重要的一層）
5. Catalyst — 是 mispriced，還是 likely to reprice soon？

## 這一層**絕不**做的事

- **不算部位、不碰資本。** `AlphaSignal != Position`；sizing 歸 `portfolio/`，
  hard limits 歸 `risk/`，資本許可歸 Engine D。系統對 alpha **不給部位尺寸**。
- **不寫 Engine A。** 多跳推論永遠是 derived，要入圖必須另走 admission gate。
- **不成為第二個 current-state authority。** provider 是唯讀 view，不落地快取表。
- **不做加權總分。** 排序用 `AlphaSignal.ordering_key()` 的字典序。

## 相依邊界（`tests/test_layer_separation.py` 守住）

`alpha/` 本身**不 import** `decision_lab.store`、`neo4j`、`yfinance`、`anthropic`、
`mcp_server`，也不得出現 Cypher 字串。concrete provider 住 `alpha/providers/`
（Phase 2），它們才碰外部世界。
"""
from __future__ import annotations

from .errors import AlphaError, ContractViolation, IdentityError, PointInTimeUnsupported
from .identity import (
    Alias, CompanyId, EntityId, Exchange, ExternalProviderId, InstrumentId, Ticker,
)
from .contracts import (
    AXES, DEFAULT_ORDERING_RULE, AlphaModel, AlphaSignal, Catalyst, ComponentTrace,
    ConsensusSnapshot, DisproofCondition, EvidenceQuality, EvidenceRef, EvidenceSelection,
    FreshnessState, FundamentalsSnapshot, MarketSnapshot, OrderingRule, RankedList,
    ResearchContext, ScarcityInputs, Score, StructuralContext, ValuationSnapshot,
    content_digest, select_point_in_time_evidence,
)
from .causal import (
    CausalPath, CompanyImpact, ImpactConfidence, ImpactDirection, ImpactMagnitude,
    StructuralEvent, TimeHorizon,
)
from .provider import (
    AS_OF_METHODS, PROVIDER_METHODS, BottleneckRow, GraphResearchProvider, SupplyExposure,
)
from .evidence_quality import assess_evidence_quality, from_legacy_level
from .legacy_axes import LEGACY_AXIS_TO_SCORE, ConversionResult, convert_axis_results
from .levels import LEVELS, LEVEL_SCALE_VERSION, level_to_ceiling, level_to_score

__all__ = [
    "AXES", "AS_OF_METHODS", "DEFAULT_ORDERING_RULE", "PROVIDER_METHODS",
    "Alias", "AlphaError", "AlphaModel", "AlphaSignal", "BottleneckRow", "CausalPath",
    "Catalyst", "CompanyId", "CompanyImpact", "ComponentTrace", "ConsensusSnapshot",
    "ContractViolation", "ConversionResult", "DisproofCondition", "EntityId",
    "EvidenceQuality", "EvidenceRef",
    "EvidenceSelection", "Exchange", "ExternalProviderId", "FreshnessState",
    "FundamentalsSnapshot", "GraphResearchProvider", "IdentityError", "ImpactConfidence",
    "ImpactDirection", "ImpactMagnitude", "InstrumentId", "MarketSnapshot",
    "OrderingRule", "PointInTimeUnsupported", "RankedList", "ResearchContext",
    "ScarcityInputs", "Score", "StructuralContext", "StructuralEvent", "SupplyExposure",
    "LEGACY_AXIS_TO_SCORE", "LEVELS", "LEVEL_SCALE_VERSION",
    "Ticker", "TimeHorizon", "ValuationSnapshot", "assess_evidence_quality",
    "content_digest", "convert_axis_results", "from_legacy_level",
    "level_to_ceiling", "level_to_score", "select_point_in_time_evidence",
]
