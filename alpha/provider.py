"""`GraphResearchProvider` — Alpha Research 讀圖的唯一介面。

Neo4j／Cypher 是 implementation detail：**Cypher 不得出現在 `alpha/` 裡**
（`tests/test_layer_separation.py` 掃描守住）。concrete 實作在 Phase 2 的
`alpha/providers/graph_neo4j.py`，它包既有的 `query/`，不新寫查詢——
這樣 `rank_bottlenecks()` 仍是唯一的結構排序權威。

## 三條硬規則

1. **provenance 不得被隱藏。** 每個回傳型別都必須有非空 `evidence`。
   provider 的價值是「不用寫 Cypher」，不是「不用知道證據來自哪」。
2. **`as_of` 是一等參數，不是選配。** 即使 concrete 實作暫不支援，
   簽名從第一天就有它，且 `as_of` 非 None 時**必須拋 `PointInTimeUnsupported`**——
   不得靜默回傳當前資料（L13：成功與失敗不得在同一個訊號上同形）。
3. **provider 不做判斷。** 它回傳結構事實與證據；「這算不算瓶頸」是
   `alpha/scarcity.py` 的事。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol, Sequence, runtime_checkable

from .causal import CausalPath, CompanyImpact, StructuralEvent
from .contracts import EvidenceRef, ScarcityInputs, StructuralContext
from .errors import ContractViolation
from .identity import CompanyId, EntityId


@dataclass(frozen=True, slots=True)
class BottleneckRow:
    """`rank_bottlenecks()` 的一列，轉成 contract 型別。

    ⚠ 這一層是**純轉換**：排序本身的唯一權威仍是 `query/bottleneck.py`。
    本型別不重算、不加權、不另建平行排序。
    """

    company_id: CompanyId
    edge_key: str
    relation: str
    target_id: EntityId
    inputs: ScarcityInputs
    demand_anchor: EntityId | None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ContractViolation(
                f"BottleneckRow({self.edge_key}) 沒有 evidence——"
                "provider 的價值是不用寫 Cypher，不是不用知道證據來自哪"
            )


@dataclass(frozen=True, slots=True)
class SupplyExposure:
    """某家公司在某個方向上的供應鏈曝險（**結構依賴，不是 ownership**）。

    ⚠ 不得與 Engine D 的 `issuer_loads`（ownership look-through）混用——
    「AAOI 使用台積電產能」是 Engine A 的因果依賴，不是持股穿透。
    """

    company_id: CompanyId
    direction: Literal["upstream", "downstream"]
    counterparty_id: EntityId
    relation: str
    substitutability: int | None = None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ContractViolation(f"SupplyExposure({self.counterparty_id}) 沒有 evidence")


@runtime_checkable
class GraphResearchProvider(Protocol):
    """Alpha Research 讀圖的唯一出口。9 個方法，全部帶 `as_of`。"""

    def get_company_structural_context(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> StructuralContext: ...

    def get_bottlenecks(
        self,
        *,
        sector: str | None = None,
        min_substitutability: int = 4,
        as_of: date | None = None,
    ) -> Sequence[BottleneckRow]: ...

    def get_dependency_paths(
        self, company_id: CompanyId, *, max_hops: int = 3, as_of: date | None = None
    ) -> Sequence[CausalPath]: ...

    def get_substitution_paths(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> Sequence[CausalPath]: ...

    def get_supply_exposure(
        self,
        company_id: CompanyId,
        *,
        direction: Literal["upstream", "downstream"],
        as_of: date | None = None,
    ) -> Sequence[SupplyExposure]: ...

    def get_second_order_beneficiaries(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]: ...

    def get_second_order_victims(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]: ...

    def get_claim_evidence(self, claim_id: str) -> Sequence[EvidenceRef]: ...

    def get_structural_changes_since(
        self, since: date, *, company_id: CompanyId | None = None
    ) -> Sequence[StructuralEvent]: ...


#: 契約測試會逐一呼叫這 9 個方法。放成常數是為了讓「新增方法卻忘了測」變成會紅的事。
PROVIDER_METHODS: tuple[str, ...] = (
    "get_company_structural_context",
    "get_bottlenecks",
    "get_dependency_paths",
    "get_substitution_paths",
    "get_supply_exposure",
    "get_second_order_beneficiaries",
    "get_second_order_victims",
    "get_claim_evidence",
    "get_structural_changes_since",
)

#: 帶 `as_of` 參數的方法。`get_second_order_*` 與 `get_claim_evidence` 不帶——
#: 前兩者的時點由 `StructuralEvent.observed_at` 決定，後者是對既有 id 的查詢。
AS_OF_METHODS: tuple[str, ...] = (
    "get_company_structural_context",
    "get_bottlenecks",
    "get_dependency_paths",
    "get_substitution_paths",
    "get_supply_exposure",
)
