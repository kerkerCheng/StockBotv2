"""測試用的 in-memory provider 與 fixture builder。

⚠ 這支檔案是 `alpha/` 唯一被生產碼以外的地方依賴的模組，**它不得有外部相依**——
契約測試要能在沒有 Neo4j／沒有網路的環境跑。

`FakeGraphResearchProvider` 刻意做兩件事：
1. **預設不支援 as-of**（`supports_as_of=False`）→ 帶 `as_of` 呼叫會拋
   `PointInTimeUnsupported`。這是 Phase 6 的保險絲：concrete provider 在補上
   as-of 投影之前，任何回測嘗試都會**大聲失敗**而不是靜默看到未來。
2. **支援 as-of 時真的篩**（`supports_as_of=True`）→ 用 `published_at` 過濾證據，
   讓 anti-lookahead 測試有東西可驗。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal, Sequence

from .causal import (
    CausalPath, CompanyImpact, ImpactConfidence, ImpactDirection, ImpactMagnitude,
    StructuralEvent, TimeHorizon,
)
from .contracts import (
    EvidenceRef, ScarcityInputs, StructuralContext, select_point_in_time_evidence,
)
from .errors import PointInTimeUnsupported
from .identity import CompanyId, EntityId, Ticker
from .provider import BottleneckRow, SupplyExposure


def evidence(
    ref: str = "graph://assertion/fixture",
    *,
    kind: str = "graph_assertion",
    published_at: date | None = date(2026, 1, 1),
    origin_entity: str | None = "fixture_origin",
    **kwargs,
) -> EvidenceRef:
    """建一條最小合法 `EvidenceRef`。預設**有**日期——沒日期是需要明說的例外。"""
    return EvidenceRef(
        ref=ref, kind=kind, published_at=published_at,
        origin_entity=origin_entity, **kwargs,
    )


@dataclass(slots=True)
class FakeGraphResearchProvider:
    """deterministic、零相依的 `GraphResearchProvider` 實作。"""

    supports_as_of: bool = False
    company_id: CompanyId = field(default_factory=lambda: CompanyId("co:coherent"))
    evidence_pool: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence_pool:
            self.evidence_pool = (
                evidence("graph://assertion/e1", published_at=date(2026, 5, 1)),
                evidence("graph://assertion/e2", published_at=date(2026, 6, 30)),
                evidence("sec://0001-2026-07-05", kind="source_doc",
                         published_at=date(2026, 7, 5)),
                evidence("graph://claim/undated", kind="graph_claim", published_at=None),
            )

    # ---- as-of 保險絲 -----------------------------------------------------
    def _evidence(self, as_of: date | None) -> tuple[EvidenceRef, ...]:
        """⚠ 不支援 as-of 時**拋例外**，不回傳當前資料（L13／INV-6）。"""
        if as_of is not None and not self.supports_as_of:
            raise PointInTimeUnsupported(
                "此 provider 無法回答『T 時刻我知道什麼』；"
                "回傳當前資料會讓回測靜默看到未來"
            )
        selection = select_point_in_time_evidence(
            self.evidence_pool, as_of=as_of if self.supports_as_of else None
        )
        return selection.kept or (evidence("graph://assertion/e1"),)

    # ---- 9 個方法 ---------------------------------------------------------
    def get_company_structural_context(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> StructuralContext:
        refs = self._evidence(as_of)
        return StructuralContext(
            company_id=company_id,
            edges=({"edge_key": "edge:fixture", "relation": "supplies_to"},),
            claims=({"id": "claim:fixture", "statement": "fixture claim"},),
            counter_paths=({"relation": "competes_with"},),
            evidence=refs,
        )

    def get_bottlenecks(
        self, *, sector: str | None = None, min_substitutability: int = 4,
        as_of: date | None = None,
    ) -> Sequence[BottleneckRow]:
        refs = self._evidence(as_of)
        return (
            BottleneckRow(
                company_id=self.company_id,
                edge_key="edge:fixture",
                relation="supplies_to",
                target_id=EntityId("co:nvidia"),
                inputs=ScarcityInputs(substitutability=5, sole_source=True,
                                      qualification_status="designed_in", evidence=refs),
                demand_anchor=EntityId("tech:ai_switch"),
                evidence=refs,
            ),
        )

    def get_dependency_paths(
        self, company_id: CompanyId, *, max_hops: int = 3, as_of: date | None = None
    ) -> Sequence[CausalPath]:
        self._evidence(as_of)
        return (
            CausalPath(
                nodes=(str(company_id), "mat:inp_substrate"),
                relations=("depends_on",),
                link_confidences=(ImpactConfidence.HIGH,),
                evidence=self._evidence(as_of),
            ),
        )

    def get_substitution_paths(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> Sequence[CausalPath]:
        return (
            CausalPath(
                nodes=(str(company_id), "co:lumentum"),
                relations=("competes_with",),
                link_confidences=(ImpactConfidence.MEDIUM,),
                evidence=self._evidence(as_of),
            ),
        )

    def get_supply_exposure(
        self, company_id: CompanyId, *,
        direction: Literal["upstream", "downstream"], as_of: date | None = None,
    ) -> Sequence[SupplyExposure]:
        return (
            SupplyExposure(
                company_id=company_id,
                direction=direction,
                counterparty_id=EntityId("mat:inp_substrate"),
                relation="depends_on",
                substitutability=5,
                evidence=self._evidence(as_of),
            ),
        )

    def get_second_order_beneficiaries(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        return (self._impact(event, ImpactDirection.BENEFICIARY),)

    def get_second_order_victims(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        return (self._impact(event, ImpactDirection.VICTIM),)

    def get_claim_evidence(self, claim_id: str) -> Sequence[EvidenceRef]:
        return self._evidence(None)

    def get_structural_changes_since(
        self, since: date, *, company_id: CompanyId | None = None
    ) -> Sequence[StructuralEvent]:
        return (
            StructuralEvent(
                event_id="se_fixture",
                kind="capacity_constraint",
                subject_id=EntityId("mat:inp_substrate"),
                direction="tightening",
                observed_at=since,
                description="fixture 供給收緊",
                evidence=self._evidence(None),
            ),
        )

    # ---- helper -----------------------------------------------------------
    def _impact(self, event: StructuralEvent, direction: ImpactDirection) -> CompanyImpact:
        path = CausalPath(
            nodes=(str(event.subject_id), str(self.company_id)),
            relations=("supplies_to",),
            link_confidences=(ImpactConfidence.MEDIUM,),
            evidence=self._evidence(None),
        )
        return CompanyImpact(
            company_id=self.company_id,
            ticker=Ticker("COHR"),
            direction=direction,
            magnitude=ImpactMagnitude.MEDIUM,
            time_horizon=TimeHorizon.QUARTERS,
            path=path,
            rationale=f"{event.subject_id} 收緊會沿 supplies_to 影響 {self.company_id}",
            event=event,
        )


def as_of_capable(provider: FakeGraphResearchProvider) -> FakeGraphResearchProvider:
    """回一個支援 as-of 的副本（給 anti-lookahead 測試用）。"""
    return replace(provider, supports_as_of=True)
