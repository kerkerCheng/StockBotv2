"""`GraphResearchProvider` 的 Neo4j 實作。

## 它做什麼、不做什麼

**做**：把既有 `query/` 的輸出轉成 contract 型別，並替每一列補上 `EvidenceRef`。
**不做**：不新寫 Cypher 排序邏輯、不重算結構分、不另建平行排序。
`rank_bottlenecks()` 仍是唯一的結構排序權威（`AGENTS.md` 硬契約）。

## as-of：明確拒絕，不靜默降級

Engine A **今天沒有 point-in-time 能力**——canonical edge 完全沒有時間欄位，
屬性是對所有 assertion 的當前投影；唯一時間線索是 `CITES → SourceDoc.published_at`，
覆蓋率只有 **382/662（58%）**（`current-architecture.md` §4.2 實測）。

所以帶 `as_of` 呼叫時**一律拋 `PointInTimeUnsupported`**，不回傳當前資料。
L13：成功與失敗若在同一個訊號上同形，回測就會靜默看到未來。
as-of 投影是 Phase 6 的工作；在那之前這道保險絲必須響。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Mapping, Sequence

from ..causal import CausalPath, CompanyImpact, ImpactConfidence, StructuralEvent  # noqa: F401
from ..contracts import EvidenceRef, ScarcityInputs, StructuralContext
from ..errors import PointInTimeUnsupported
from ..identity import CompanyId, EntityId
from ..provider import BottleneckRow, SupplyExposure

#: `query.bottleneck` 的 evidence 等級 → `EvidenceRef.evidence_class`。
#: 直接沿用既有五級，不另創（L16：分類有 SSOT 時要讓它跟著資料走）。
_EVIDENCE_CLASS_TIER: Mapping[str, int] = {
    "externally_corroborated": 1,
    "counterparty_joint": 2,
    "self_reported_costly": 2,
    "needs_review": 3,
    "self_reported": 4,
}

#: 邊上的 `confidence` → 這條路徑的 link confidence。
#: ⚠ 只做序數轉換，不做內插——`confidence` 是「關係存在的信心」，
#: 不是「這條因果鏈有多強」（L12：兩件事不得共用一個數字）。
def _link_confidence(confidence: float | None) -> ImpactConfidence:
    if confidence is None:
        return ImpactConfidence.UNKNOWN
    if confidence >= 0.85:
        return ImpactConfidence.HIGH
    if confidence >= 0.6:
        return ImpactConfidence.MEDIUM
    return ImpactConfidence.LOW


def _reject_as_of(as_of: date | None) -> None:
    if as_of is not None:
        raise PointInTimeUnsupported(
            f"Engine A 目前無法回答 as_of={as_of} 的圖狀態："
            "canonical edge 沒有時間欄位，屬性是對所有 assertion 的當前投影。"
            "as-of 投影是 Phase 6 的工作；回傳當前資料會讓回測靜默看到未來"
        )


@dataclass(slots=True)
class Neo4jGraphResearchProvider:
    """唯讀 Neo4j provider。呼叫端負責提供 driver；本類別不管連線生命週期。"""

    driver: Any
    registry: Any = None
    min_substitutability: int = 4
    _ranked: Mapping[str, Any] | None = None

    # ---- 內部：取一次排序，快取在 instance 上（不落地成第二個 authority）----
    def _rank(self) -> Mapping[str, Any]:
        if self._ranked is None:
            from identity.registry import get_registry
            from query.bottleneck import fetch_assertions, rank_bottlenecks

            with self.driver.session() as session:
                assertions = fetch_assertions(session)
            self._ranked = rank_bottlenecks(
                assertions,
                self.registry or get_registry(),
                min_substitutability=self.min_substitutability,
            )
        return self._ranked

    def _row_evidence(self, row: Mapping[str, Any]) -> tuple[EvidenceRef, ...]:
        """由排序列組出 `EvidenceRef`。

        ⚠ **`documents` 是注意力指標，不參與排序**（`bottleneck.py` 已明文排除），
        但它**是 provenance**——每份文件都要能被列出來，否則 provider 就在隱藏證據。
        """
        evidence_class = str(row.get("evidence") or "")
        tier = _EVIDENCE_CLASS_TIER.get(evidence_class)
        refs = [
            EvidenceRef(
                ref=f"graph://edge/{row.get('company_id')}/{row.get('relation')}/"
                    f"{row.get('bottleneck')}",
                kind="graph_edge",
                # ⚠ **不得把被分析的公司填成 origin_entity。**
                # 第一版這樣做，於是 L8 獨立性永遠只看到 1 個來源，
                # 把 COHR 的 Q1 從 declared 0.9 壓成 effective 0.0——
                # 而該邊的 `evidence` 明明是 `externally_corroborated`。
                # 那是 F-22 的形狀：機械比對把真訊號歸零。
                # `origin_entity` 屬於 SourceDoc，排序列上沒有；留 None 才誠實。
                origin_entity=None,
                confidence=_finite(row.get("confidence")),
                evidence_class=evidence_class or None,
                evidence_tier=tier,
            )
        ]
        for source in (row.get("sources") or []):
            refs.append(EvidenceRef(
                ref=f"graph://source/{source}", kind="source_doc",
                source_doc_id=str(source), evidence_class=evidence_class or None,
                evidence_tier=tier,
            ))
        return tuple(refs)

    # ---- 9 個契約方法 ------------------------------------------------------
    def get_bottlenecks(
        self, *, sector: str | None = None, min_substitutability: int = 4,
        as_of: date | None = None,
    ) -> Sequence[BottleneckRow]:
        _reject_as_of(as_of)
        rows = self._rank().get("rows") or []
        out: list[BottleneckRow] = []
        for row in rows:
            if sector and str(row.get("demand_anchor") or "") != sector:
                continue
            substitutability = row.get("substitutability")
            if substitutability is not None and substitutability < min_substitutability:
                continue
            try:
                company = CompanyId(str(row["company_id"]))
                target = EntityId(str(row["bottleneck"]))
            except Exception:
                continue          # id 形狀不合規的列跳過，但不靜默：見下方 coverage
            anchor = row.get("demand_anchor")
            evidence = self._row_evidence(row)
            out.append(BottleneckRow(
                company_id=company,
                edge_key=f"{company}|{row.get('relation')}|{target}",
                relation=str(row.get("relation") or ""),
                target_id=target,
                inputs=ScarcityInputs(
                    substitutability=substitutability,
                    sole_source=row.get("sole_source"),
                    qualification_status=row.get("qualification_status"),
                    qualification_lead_time_weeks=row.get("lead_time_weeks"),
                    dependency_depth=row.get("demand_hops"),
                    demand_anchor=_entity_or_none(anchor),
                    evidence=evidence,
                ),
                demand_anchor=_entity_or_none(anchor),
                evidence=evidence,
            ))
        return tuple(out)

    def get_company_structural_context(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> StructuralContext:
        _reject_as_of(as_of)
        rows = [r for r in (self._rank().get("rows") or [])
                if str(r.get("company_id")) == str(company_id)]
        structural = [r for r in (self._rank().get("structural_rows") or [])
                      if str(r.get("company_id")) == str(company_id)]
        evidence: list[EvidenceRef] = []
        for row in rows:
            evidence.extend(self._row_evidence(row))
        return StructuralContext(
            company_id=company_id,
            edges=tuple({
                "relation": r.get("relation"), "target": r.get("bottleneck"),
                "substitutability": r.get("substitutability"),
                "sole_source": r.get("sole_source"),
                "qualification_status": r.get("qualification_status"),
                "demand_anchor": r.get("demand_anchor"),
                "demand_hops": r.get("demand_hops"),
                "evidence_class": r.get("evidence"),
            } for r in rows),
            claims=(),
            # ⚠ `structural_rows` 是**純結構排序**（完全不看證據），
            # 回答「該去補誰的證據」；與 `rows`（可行動）用途不同、不可互換。
            counter_paths=tuple({
                "relation": r.get("relation"), "target": r.get("bottleneck"),
                "purpose": "structural_only_not_actionable",
            } for r in structural if r not in rows),
            evidence=tuple(evidence),
        )

    def get_dependency_paths(
        self, company_id: CompanyId, *, max_hops: int = 3, as_of: date | None = None
    ) -> Sequence[CausalPath]:
        _reject_as_of(as_of)
        paths: list[CausalPath] = []
        for row in self._rank().get("rows") or []:
            if str(row.get("company_id")) != str(company_id):
                continue
            chain = [str(c) for c in (row.get("chain") or [])]
            if len(chain) < 2:
                continue
            paths.append(CausalPath(
                nodes=tuple(reversed(chain)),
                relations=tuple("supplies_to" for _ in range(len(chain) - 1)),
                link_confidences=tuple(
                    _link_confidence(_finite(row.get("confidence")))
                    for _ in range(len(chain) - 1)
                ),
                evidence=self._row_evidence(row),
            ))
        return tuple(paths[:max_hops * 4])

    def get_substitution_paths(
        self, company_id: CompanyId, *, as_of: date | None = None
    ) -> Sequence[CausalPath]:
        """反證路徑：**同一個 chokepoint 上的其他供應商**。

        ⚠ 這是 counter-path 的最小可行版本。供應商計數本身**不得**當瓶頸性證據
        （它反映「我們研究了幾家」不是「世界上有幾家」），但「有沒有第二家」
        對 disproof 是實質資訊。
        """
        _reject_as_of(as_of)
        rows = self._rank().get("rows") or []
        mine = {str(r.get("bottleneck")) for r in rows
                if str(r.get("company_id")) == str(company_id)}
        paths: list[CausalPath] = []
        for row in rows:
            target = str(row.get("bottleneck"))
            if target not in mine or str(row.get("company_id")) == str(company_id):
                continue
            paths.append(CausalPath(
                nodes=(str(company_id), target, str(row.get("company_id"))),
                relations=("supplies_to", "also_supplied_by"),
                link_confidences=(
                    _link_confidence(_finite(row.get("confidence"))),
                    _link_confidence(_finite(row.get("confidence"))),
                ),
                evidence=self._row_evidence(row),
            ))
        return tuple(paths)

    def get_supply_exposure(
        self, company_id: CompanyId, *,
        direction: Literal["upstream", "downstream"], as_of: date | None = None,
    ) -> Sequence[SupplyExposure]:
        _reject_as_of(as_of)
        out: list[SupplyExposure] = []
        for row in self._rank().get("rows") or []:
            if str(row.get("company_id")) != str(company_id):
                continue
            relation = str(row.get("relation") or "")
            is_upstream = relation in ("depends_on", "is_component_of")
            if (direction == "upstream") != is_upstream:
                continue
            try:
                counterparty = EntityId(str(row["bottleneck"]))
            except Exception:
                continue
            out.append(SupplyExposure(
                company_id=company_id, direction=direction,
                counterparty_id=counterparty, relation=relation,
                substitutability=row.get("substitutability"),
                evidence=self._row_evidence(row),
            ))
        return tuple(out)

    # ---- Phase 5 才實作的三個：明確拋，不回空集合 -------------------------
    def get_second_order_beneficiaries(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        raise NotImplementedError(
            "多跳因果傳播是 Phase 5。⚠ 回空集合會讓「還沒實作」與「查無受益者」"
            "在同一個訊號上同形（L13）"
        )

    def get_second_order_victims(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        raise NotImplementedError("多跳因果傳播是 Phase 5（同上，不回空集合）")

    def get_structural_changes_since(
        self, since: date, *, company_id: CompanyId | None = None
    ) -> Sequence[StructuralEvent]:
        raise NotImplementedError(
            "StructuralEvent 偵測是 Phase 5。需要 as-of 投影才知道「變了什麼」，"
            "而那是 Phase 6 的前置"
        )

    def get_claim_evidence(self, claim_id: str) -> Sequence[EvidenceRef]:
        from query.graph_context import _Q_COMPANY_CLAIMS  # noqa: F401  (存在性檢查)

        with self.driver.session() as session:
            rows = list(session.run(
                "MATCH (c:Claim {id: $cid})-[:CITES]->(d:SourceDoc) "
                "RETURN d.id AS doc_id, d.origin_entity AS origin, "
                "d.evidence_tier AS tier, d.published_at AS published, d.url AS url",
                cid=claim_id,
            ))
        return tuple(
            EvidenceRef(
                ref=f"graph://claim/{claim_id}#{r['doc_id']}",
                kind="graph_claim",
                source_doc_id=str(r["doc_id"]),
                origin_entity=r.get("origin"),
                url=r.get("url"),
                published_at=_date_or_none(r.get("published")),
                evidence_tier=_tier_or_none(r.get("tier")),
            ) for r in rows
        )

    # ---- coverage：provider 自己要能說出它看得到多少 ----------------------
    def coverage(self) -> Mapping[str, Any]:
        """`rank_bottlenecks` 自帶的覆蓋率摘要。

        ⚠ 這不是裝飾：`substitutability` 覆蓋率只有 15%，**排名必然偏向已被抽取過
        的邊，沒填的邊是隱形的**。消費端必須看得到這個數字才不會過度解讀排序。
        """
        return dict(self._rank().get("coverage") or {})


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if 0.0 <= parsed <= 1.0 else None


def _entity_or_none(value: Any) -> EntityId | None:
    if not value:
        return None
    try:
        return EntityId(str(value))
    except Exception:
        return None


def _date_or_none(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _tier_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed in (1, 2, 3, 4) else None


def open_default_provider(**kwargs: Any) -> Neo4jGraphResearchProvider:
    """用 `.env` 的連線資訊建 provider（本機互動用）。"""
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    return Neo4jGraphResearchProvider(driver=driver, **kwargs)
