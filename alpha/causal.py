"""多跳因果的 domain objects。

## 為什麼需要它

圖裡有 529 條 canonical domain edge（`DEPENDS_ON` 49、`CONSTRAINED_BY` 8），
但**沒有任何物件表達「A 卡住 → B 受害 → C 受益」**。真正的 graph alpha 多半在
second/third-order effects，而現行排序只能回答「誰是瓶頸」。

## 兩條硬規則

1. **`CompanyImpact.confidence` 取路徑上最弱的一段，不取平均。**
   平均會讓「三段強＋一段完全沒證據」看起來比「兩段中等」可靠——那正是
   2026-08-21 pq1 排序踩過的補償性問題（`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`
   壓過真正的資本承諾事件）。
2. **多跳結論永遠標 derived，不入圖。** 圖只存有逐字證據的關係；`CompanyImpact`
   是推論，住 `alpha/`。要入圖必須另走 admission gate（四個人工 gate 之一）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from .contracts import EvidenceRef
from .errors import ContractViolation
from .identity import CompanyId, EntityId, Ticker


class ImpactDirection(Enum):
    BENEFICIARY = "beneficiary"
    VICTIM = "victim"
    AMBIGUOUS = "ambiguous"


class ImpactMagnitude(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ImpactConfidence(Enum):
    """⚠ 次序有意義：`UNKNOWN` 是**最弱**，不是「中性」。"""

    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def __lt__(self, other: "ImpactConfidence") -> bool:
        return self.value < other.value


class TimeHorizon(Enum):
    WEEKS = "weeks"
    QUARTERS = "quarters"
    YEARS = "years"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StructuralEvent:
    """圖上某個結構事實發生了變化。`kind` 是封閉字彙（taxonomy），
    權威在 `config/structural_event_kinds.json`。"""

    event_id: str
    kind: str
    subject_id: EntityId
    direction: str  # tightening | loosening
    observed_at: date
    description: str = ""
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        from .vocabulary import structural_event_kinds, validate_kind

        validate_kind(self.kind, structural_event_kinds(), "StructuralEvent.kind")
        if self.direction not in ("tightening", "loosening"):
            raise ContractViolation(
                f"StructuralEvent.direction 必須是 tightening／loosening：{self.direction!r}"
            )
        if not self.evidence:
            raise ContractViolation(
                "StructuralEvent 必須帶 evidence——結構事件是 claim，不是感覺"
            )


@dataclass(frozen=True, slots=True)
class CausalPath:
    """圖上的一條因果路徑，以及**它最弱的那一段**。"""

    nodes: tuple[str, ...]
    relations: tuple[str, ...]
    link_confidences: tuple[ImpactConfidence, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if len(self.nodes) < 2:
            raise ContractViolation("CausalPath 至少要有兩個節點")
        if len(self.relations) != len(self.nodes) - 1:
            raise ContractViolation(
                f"relations 長度必須是 nodes-1：{len(self.relations)} vs {len(self.nodes)}"
            )
        if self.link_confidences and len(self.link_confidences) != len(self.relations):
            raise ContractViolation("link_confidences 長度必須等於 relations")

    @property
    def hops(self) -> int:
        return len(self.relations)

    @property
    def weakest_link_index(self) -> int | None:
        if not self.link_confidences:
            return None
        return min(range(len(self.link_confidences)),
                   key=lambda i: self.link_confidences[i].value)

    @property
    def weakest_link(self) -> str | None:
        """最弱那一段的可讀描述（`src -relation-> dst`）。"""
        idx = self.weakest_link_index
        if idx is None:
            return None
        return f"{self.nodes[idx]} -{self.relations[idx]}-> {self.nodes[idx + 1]}"

    @property
    def confidence(self) -> ImpactConfidence:
        """**取最弱的一段，不取平均。**

        一條鏈的可信度不會高於它最不可信的那一環；取平均等於讓三段強的證據
        把一段完全沒證據的補起來，那是補償性（2026-08-21 實測的同一個病）。
        """
        if not self.link_confidences:
            return ImpactConfidence.UNKNOWN
        return min(self.link_confidences, key=lambda c: c.value)


@dataclass(frozen=True, slots=True)
class CompanyImpact:
    """某個結構事件對某家公司的推論影響。**永遠是 derived，不入圖。**"""

    company_id: CompanyId
    ticker: Ticker | None
    direction: ImpactDirection
    magnitude: ImpactMagnitude
    time_horizon: TimeHorizon
    path: CausalPath
    rationale: str
    event: StructuralEvent | None = None
    derived: bool = field(default=True)

    def __post_init__(self) -> None:
        if not self.derived:
            raise ContractViolation(
                "CompanyImpact 永遠是 derived——它是推論不是圖上的事實，"
                "要入圖必須另走 graph admission gate"
            )
        if not self.rationale.strip():
            raise ContractViolation("CompanyImpact.rationale 不得為空")
        unknown = [n for n in self.path.nodes if n not in self.rationale]
        if len(unknown) == len(self.path.nodes):
            raise ContractViolation(
                "rationale 必須至少引用 path 上的一個節點——"
                "說不出經過哪裡的因果推論無法被檢查"
            )

    @property
    def confidence(self) -> ImpactConfidence:
        """**由 path 上最弱的一段決定**，不是平均、也不是自報。"""
        return self.path.confidence
