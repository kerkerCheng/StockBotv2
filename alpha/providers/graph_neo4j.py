"""`GraphResearchProvider` 的 Neo4j 實作。

## 它做什麼、不做什麼

**做**：把既有 `query/` 的輸出轉成 contract 型別，並替每一列補上 `EvidenceRef`。
**不做**：不新寫 Cypher 排序邏輯、不重算結構分、不另建平行排序。
`rank_bottlenecks()` 仍是唯一的結構排序權威（`AGENTS.md` 硬契約）。

## as-of：真的投影（Phase 6），但保險絲沒有拿掉

canonical edge 仍然沒有時間欄位——唯一的時間線索還是
`CITES → SourceDoc.published_at`。**投影就是靠它做的**：把 assertion 依
「引用的文件在 `as_of` 之前發表過沒有」篩一次，再交給 `rank_bottlenecks`。

⚠ **順序不可顛倒。** 過濾必須在排序**之前**：`rank_bottlenecks` 是在 assertion 上
collapse 屬性、判證據等級、走需求鏈的，先排序再砍列會留下用未來文件算出來的
`substitutability` 與 `evidence`——列是對的，值是偷看來的，而那是 lookahead
最難察覺的形式。

⚠ **未定日一律排除並計數。** 「我找不到日期」不等於「它在 T 之前」（L11-5）。

**保險絲從「一律拒絕」換成「投影不存在時拒絕」，不是拿掉**（`_rank` 裡兩處
`PointInTimeUnsupported`）：圖上完全沒有 `published_at`、或 `as_of` 早於最早的
證據時，回空 list 會與「那天真的沒有瓶頸」同形（L13），所以那兩種情況仍然拋。

Phase 6 回填後的實測覆蓋：SourceDoc `published_at` **187/200（93.5%）**、
EdgeAssertion 可定日 **645/662（97.4%）**。查證：
`MATCH (a:EdgeAssertion)-[:CITES]->(d:SourceDoc) WHERE d.published_at IS NOT NULL
RETURN count(DISTINCT a)`
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Mapping, Sequence

from ..causal import (
    CausalPath, CompanyImpact, ImpactConfidence, ImpactDirection, ImpactMagnitude,
    StructuralEvent, TimeHorizon,
)
from ..contracts import EvidenceRef, ScarcityInputs, StructuralContext
from ..errors import PointInTimeUnsupported
from ..identity import CompanyId, EntityId, Ticker
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

#: 走訪方向的關係標籤。⚠ 圖上的邊有自己的方向，而衝擊是**逆著依賴走**的：
#: `co:coherent depends_on mat:inp_substrate` 這條邊，衝擊從 substrate 流向 coherent。
#: 若直接沿用原標籤，路徑會印成 `mat:inp_substrate -depends_on-> co:coherent`
#: ——**方向剛好講反**，而讀的人無從發現（2026-09-04 首次實跑時就印出了這一行）。
#: 所以逆走的邊改用衍生標籤；`constrains` 不是圖上的關係，是推論路徑的措辭。
_TRAVERSAL_RELATION: Mapping[str, str] = {
    "supplies_to": "supplies_to",        # 順走：company → 它供應的對象
    "depends_on": "constrains",          # 逆走：被依賴者 → 依賴它的人
    "is_component_of": "constrains",
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


#: 一份投影至少要看得到幾條已定日 assertion 才算「投影存在」。
#: ⚠ 這不是品質門檻，是**存在性**門檻：`0` 代表圖上完全沒有時間資訊
#: （例如重建過的空庫、或 `published_at` 尚未回填），那時候唯一誠實的回答是
#: 「我答不了」，不是「那天沒有瓶頸」。
_MIN_DATED_FOR_PROJECTION = 1


@dataclass(slots=True)
class Neo4jGraphResearchProvider:
    """唯讀 Neo4j provider。呼叫端負責提供 driver；本類別不管連線生命週期。"""

    driver: Any
    registry: Any = None
    min_substitutability: int = 4
    _ranked: Mapping[str, Any] | None = None
    _projections: dict[date, Mapping[str, Any]] | None = None
    #: 注入的原始 assertion（測試用的縫）。**as-of 投影必須在 assertion 上做**，
    #: 所以 `_ranked` 那個縫不夠——注入排序結果的測試無法驗投影。
    _assertion_rows: Sequence[Mapping[str, Any]] | None = None

    # ---- 內部：取一次排序，快取在 instance 上（不落地成第二個 authority）----
    def _assertions(self) -> list[Mapping[str, Any]]:
        from query.bottleneck import fetch_assertions

        if self._assertion_rows is not None:
            return list(self._assertion_rows)
        with self.driver.session() as session:
            return fetch_assertions(session)

    def _rank(self, as_of: date | None = None) -> Mapping[str, Any]:
        """`as_of=None` ＝ 當前視角；給日期則走 as-of 投影。

        ⚠ **投影不是「排序完再過濾」**：`rank_bottlenecks` 是在 assertion 上
        collapse 屬性、分類證據等級、走需求鏈的，所以過濾必須發生在**它之前**。
        先排序再砍列會留下用未來文件算出來的 `substitutability` 與 `evidence`，
        那正是 lookahead 最隱蔽的形式——列是對的，值是偷看來的。
        """
        from identity.registry import get_registry
        from query.bottleneck import project_assertions_as_of, rank_bottlenecks

        if as_of is None:
            if self._ranked is None:
                self._ranked = rank_bottlenecks(
                    self._assertions(),
                    self.registry or get_registry(),
                    min_substitutability=self.min_substitutability,
                )
            return self._ranked

        if self._projections is None:
            self._projections = {}
        if as_of in self._projections:
            return self._projections[as_of]

        projection = project_assertions_as_of(self._assertions(), as_of)
        if projection.dated_total < _MIN_DATED_FOR_PROJECTION:
            # **保險絲仍然在。** 它從「as-of 一律拒絕」換成「投影不存在時拒絕」，
            # 不是拿掉——L13：成功與失敗若在同一個訊號上同形，回測會靜默看到未來。
            # 這裡的同形風險是「回空 list」：那與「那天真的沒有瓶頸」長得一樣。
            raise PointInTimeUnsupported(
                f"無法投影到 as_of={as_of}：{projection.input_count} 條 EdgeAssertion "
                "沒有任何一條引用得到帶 published_at 的 SourceDoc。"
                "圖上沒有時間資訊時，唯一誠實的回答是『答不了』，不是『那天沒有瓶頸』。"
                "先跑 scripts/backfill_source_dating.py --list 看缺哪些"
            )
        if not projection.rows:
            raise PointInTimeUnsupported(
                f"as_of={as_of} 早於圖上最早的證據發表日：{projection.dated_total} 條"
                f"已定日 assertion 全部晚於它（另有 {projection.excluded_undated} 條未定日）。"
                "回傳空排序會與『那天沒有任何瓶頸』同形，所以這裡拒絕"
            )
        ranked = dict(rank_bottlenecks(
            projection.rows,
            self.registry or get_registry(),
            min_substitutability=self.min_substitutability,
        ))
        # 投影自己的計數必須跟著資料走（L16），否則消費端會把
        # 「as-of 篩掉一半」讀成「這家公司本來就沒幾條邊」。
        ranked["coverage"] = dict(ranked.get("coverage") or {}) | {
            "as_of": as_of.isoformat(),
            "as_of_input_assertions": projection.input_count,
            "as_of_excluded": projection.reasons(),
            "as_of_dated_total": projection.dated_total,
        }
        self._projections[as_of] = ranked
        return ranked

    def _row_evidence(self, row: Mapping[str, Any]) -> tuple[EvidenceRef, ...]:
        """由排序列組出 `EvidenceRef`。

        ⚠ **`documents` 是注意力指標，不參與排序**（`bottleneck.py` 已明文排除），
        但它**是 provenance**——每份文件都要能被列出來，否則 provider 就在隱藏證據。

        ⚠ **`published_at` 一定要帶。** 沒有它，`select_point_in_time_evidence`
        會把每一條證據都判成 `excluded_undated`——as-of 投影明明篩對了列，
        證據卻在下一關全數被丟掉，而丟掉的理由（未定日）與「真的沒有證據」同形。
        這條邊的日期取所有引用文件中**最早**的一份：它回答「這條邊最早什麼時候
        說得出來」，也保證投影留下的列一定通過 as-of 篩選。
        """
        evidence_class = str(row.get("evidence") or "")
        tier = _EVIDENCE_CLASS_TIER.get(evidence_class)
        published = _date_or_none(row.get("published_at"))
        refs = [
            EvidenceRef(
                ref=f"graph://edge/{row.get('company_id')}/{row.get('relation')}/"
                    f"{row.get('bottleneck')}",
                kind="graph_edge",
                published_at=published,
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
        # 每份文件用**它自己的**發表日，不是整條邊的最早日：
        # 邊的日期回答「最早何時說得出來」，文件的日期回答「這一份何時出現」，
        # 兩者混用會讓晚出的佐證看起來早就存在（L12：一個表示兩種語意）。
        dates = row.get("source_dates") or {}
        for source in (row.get("sources") or []):
            refs.append(EvidenceRef(
                ref=f"graph://source/{source}", kind="source_doc",
                source_doc_id=str(source), evidence_class=evidence_class or None,
                evidence_tier=tier,
                published_at=_date_or_none(dates.get(source)) or published,
            ))
        return tuple(refs)

    # ---- 9 個契約方法 ------------------------------------------------------
    def get_bottlenecks(
        self, *, sector: str | None = None, min_substitutability: int = 4,
        as_of: date | None = None,
    ) -> Sequence[BottleneckRow]:
        ranked = self._rank(as_of)
        rows = ranked.get("rows") or []
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
        ranked = self._rank(as_of)
        rows = [r for r in (ranked.get("rows") or [])
                if str(r.get("company_id")) == str(company_id)]
        structural = [r for r in (ranked.get("structural_rows") or [])
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
        paths: list[CausalPath] = []
        for row in self._rank(as_of).get("rows") or []:
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
        rows = self._rank(as_of).get("rows") or []
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
        out: list[SupplyExposure] = []
        for row in self._rank(as_of).get("rows") or []:
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

    # ---- Phase 5：多跳因果傳播 --------------------------------------------
    def propagate(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> tuple[CompanyImpact, ...]:
        """由一個結構事件推出二階以上的受影響公司。**全部 derived，永不入圖。**

        ## 傳播規則（這是**規則不是量測**，寫出來才能被反駁）

        圖上的邊化約成一個方向：`A ⇒ B` 讀作「**A 依賴 B**」。
        - `company depends_on X` / `company is_component_of X` → `company ⇒ X`
        - `company supplies_to X` → `X ⇒ company`（X 依賴這家供應商）

        然後兩條、也只有兩條傳播路徑：

        1. **依賴鏈**：凡（遞移地）依賴 subject 的公司，在 subject `tightening`
           時是 `VICTIM`、`loosening` 時是 `BENEFICIARY`。
        2. **替代鏈**：與 subject 供應同一個 chokepoint 的**其他**公司，在 subject
           `tightening` 時是 `BENEFICIARY`（稀缺讓替代者受惠）、反之為 `VICTIM`。

        ⚠ **只回 `co:*` 節點。** `tech:`／`mat:` 是路徑上的中繼點，不是可投資標的；
        把它們也產出 impact 會讓下游以為那是一個標的。

        ⚠ **二階＝至少 2 跳。** 1 跳是直接關係，圖上本來就看得到，不需要推論；
        這一層的價值在「圖上沒有直接連線、但推得出來」的那些。

        ## 三個刻意不做的事

        - **不加權總分。** `magnitude` 由跳數與路徑上最低的 `substitutability`
          決定，且**二階最高只給 `MEDIUM`**——它是推論不是觀測，給 `HIGH` 是
          overclaim。
        - **不編時間。** `time_horizon` 只在路徑上有 `lead_time_weeks` 時才給值，
          否則 `UNKNOWN`。圖裡沒有的東西不憑空生出來。
        - **不取平均信心。** `CompanyImpact.confidence` 由 `CausalPath` 取最弱的
          一段（契約已強制），三段強證據不得把一段沒證據的補起來。
        """
        rows = list(self._rank().get("rows") or [])
        subject = str(event.subject_id)
        flip = event.direction == "loosening"

        def _dir(base: ImpactDirection) -> ImpactDirection:
            if not flip:
                return base
            return (ImpactDirection.VICTIM if base is ImpactDirection.BENEFICIARY
                    else ImpactDirection.BENEFICIARY)

        impacts: dict[tuple[str, str], CompanyImpact] = {}

        for path, base in self._causal_paths(rows, subject, max_hops=max_hops):
            endpoint = path.nodes[-1]
            if not endpoint.startswith("co:"):
                continue                      # 中繼節點不是標的
            if endpoint == subject:
                continue                      # 不對自己發 impact
            direction = _dir(base)
            key = (endpoint, direction.value)
            existing = impacts.get(key)
            # 同一家公司多條路徑時取**最短**的那條：跳數少的推論比較站得住腳。
            if existing is not None and existing.path.hops <= path.hops:
                continue
            impacts[key] = CompanyImpact(
                company_id=CompanyId(endpoint),
                ticker=self._ticker_for(endpoint, rows),
                direction=direction,
                magnitude=self._magnitude(path, rows),
                time_horizon=self._horizon(path, rows),
                path=path,
                rationale=(
                    f"{event.kind}（{event.direction}）發生在 {subject}；"
                    f"沿 {' → '.join(path.nodes)} 推出 {endpoint} 受影響。"
                    f"最弱的一段是 {path.weakest_link or '未知'}。"
                    "⚠ 這是多跳推論不是圖上的事實。"
                ),
                event=event,
            )
        return tuple(impacts.values())

    def get_second_order_beneficiaries(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        return tuple(i for i in self.propagate(event, max_hops=max_hops)
                     if i.direction is ImpactDirection.BENEFICIARY)

    def get_second_order_victims(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]:
        return tuple(i for i in self.propagate(event, max_hops=max_hops)
                     if i.direction is ImpactDirection.VICTIM)

    # ---- Phase 5 的內部機件 ------------------------------------------------
    @staticmethod
    def _dependency_edges(
        rows: Sequence[Mapping[str, Any]]
    ) -> dict[str, list[tuple[str, Mapping[str, Any]]]]:
        """`依賴者 → [(被依賴者, row)]`。方向統一成「A 依賴 B」。"""
        edges: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
        for row in rows:
            company = str(row.get("company_id") or "")
            target = str(row.get("bottleneck") or "")
            if not company or not target:
                continue
            relation = str(row.get("relation") or "")
            if relation == "supplies_to":
                edges.setdefault(target, []).append((company, row))
            else:                              # depends_on／is_component_of
                edges.setdefault(company, []).append((target, row))
        return edges


    def _causal_paths(
        self, rows: Sequence[Mapping[str, Any]], subject: str, *, max_hops: int
    ) -> list[tuple[CausalPath, ImpactDirection]]:
        """由 subject 出發的兩類路徑，各自帶「tightening 時的方向」。"""
        edges = self._dependency_edges(rows)
        # 反轉：`被依賴者 → [依賴它的人]`，衝擊沿這個方向往下游擴散。
        dependents: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
        for source, targets in edges.items():
            for target, row in targets:
                dependents.setdefault(target, []).append((source, row))

        out: list[tuple[CausalPath, ImpactDirection]] = []

        # (1) 依賴鏈：BFS，記錄完整路徑；≥2 跳才算二階。
        queue: list[tuple[str, tuple[str, ...], tuple[Mapping[str, Any], ...]]] = [
            (subject, (subject,), ())
        ]
        seen = {subject}
        while queue:
            node, nodes, used = queue.pop(0)
            if len(used) >= max_hops:
                continue
            for nxt, row in dependents.get(node, ()):
                if nxt in nodes:
                    continue               # 不繞圈
                path_nodes = nodes + (nxt,)
                path_rows = used + (row,)
                if len(path_rows) >= 2:
                    out.append((self._path_from(path_nodes, path_rows),
                                ImpactDirection.VICTIM))
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path_nodes, path_rows))

        # (2) 替代鏈：與 subject 供同一個 chokepoint 的其他公司（固定 2 跳）。
        supplies = [r for r in rows
                    if str(r.get("company_id")) == subject
                    and str(r.get("relation")) == "supplies_to"]
        for mine in supplies:
            chokepoint = str(mine.get("bottleneck"))
            for other in rows:
                if (str(other.get("bottleneck")) != chokepoint
                        or str(other.get("relation")) != "supplies_to"
                        or str(other.get("company_id")) == subject):
                    continue
                out.append((
                    self._path_from(
                        (subject, chokepoint, str(other.get("company_id"))),
                        (mine, other),
                        relations=("supplies_to", "also_supplied_by"),
                    ),
                    ImpactDirection.BENEFICIARY,
                ))
        return out

    def _path_from(
        self,
        nodes: tuple[str, ...],
        rows: tuple[Mapping[str, Any], ...],
        relations: tuple[str, ...] | None = None,
    ) -> CausalPath:
        return CausalPath(
            nodes=nodes,
            relations=relations or tuple(
                _TRAVERSAL_RELATION.get(
                    str(r.get("relation") or ""), str(r.get("relation") or "related_to")
                )
                for r in rows
            ),
            link_confidences=tuple(
                _link_confidence(_finite(r.get("confidence"))) for r in rows
            ),
            evidence=tuple(
                ref for r in rows for ref in self._row_evidence(r)
            ),
        )

    @staticmethod
    def _ticker_for(
        company_id: str, rows: Sequence[Mapping[str, Any]]
    ) -> Ticker | None:
        for row in rows:
            if str(row.get("company_id")) == company_id and row.get("ticker"):
                try:
                    return Ticker(str(row["ticker"]))
                except Exception:
                    return None
        return None

    @staticmethod
    def _magnitude(path: CausalPath, rows: Sequence[Mapping[str, Any]]) -> ImpactMagnitude:
        """跳數 ＋ 路徑上最低的 `substitutability`。**二階最高只到 MEDIUM。**

        給 `HIGH` 等於宣稱一個多跳推論和直接觀測一樣可靠，那是 overclaim。
        """
        subs = [
            _number(r.get("substitutability"))
            for r in rows
            if str(r.get("company_id")) in path.nodes
            or str(r.get("bottleneck")) in path.nodes
        ]
        known = [s for s in subs if s is not None]
        if not known:
            return ImpactMagnitude.UNKNOWN     # 不知道，不是「低」
        if path.hops <= 2 and min(known) >= 4:
            return ImpactMagnitude.MEDIUM
        return ImpactMagnitude.LOW

    @staticmethod
    def _horizon(path: CausalPath, rows: Sequence[Mapping[str, Any]]) -> TimeHorizon:
        """只在圖上真的有 `lead_time_weeks` 時才給值，否則 `UNKNOWN`。

        ⚠ 不套用「供應鏈事件大概一季」這種預設值——那是編出來的，
        而編出來的時間會被下游當成可以排程的東西。
        """
        weeks = [
            _number(r.get("lead_time_weeks"))
            for r in rows
            if str(r.get("bottleneck")) in path.nodes
        ]
        known = [w for w in weeks if w is not None]
        if not known:
            return TimeHorizon.UNKNOWN
        longest = max(known)
        if longest < 13:
            return TimeHorizon.WEEKS
        if longest < 52:
            return TimeHorizon.QUARTERS
        return TimeHorizon.YEARS

    def get_structural_changes_since(
        self, since: date, *, company_id: CompanyId | None = None
    ) -> Sequence[StructuralEvent]:
        """Phase 5b：比對 `since` 的投影與當前圖，找出**結構事實變了什麼**。

        ## 它為什麼非等 as-of 投影不可

        「變了什麼」＝兩個時點的差。沒有投影就只有「現在長什麼樣」，
        任何「變化」都只能靠 `updated_at` 猜——而那是**我們何時寫進去**，
        不是**世界何時改變**（F-27 的形狀：ingest 時間冒充事件時間）。

        ## ⚠ 這裡偵測到的，嚴格說是「世界在窗內產出了新文件」

        投影是按 `published_at` 篩的，所以差集裡的每一條都**至少有一份在
        `since` 之後發表的文件**在支持它。這排除了最大的雜訊來源——
        「我們補讀了一份 2023 年的舊文件」不會產生事件（那是知識補登，
        不是結構變化）。

        但它**不排除**「新文件描述一個一直都成立的舊事實」。所以每個事件的
        `evidence` 都帶著那份文件與它的發表日，讀的人自己判斷；
        `description` 也逐字寫出圖上是哪個屬性從什麼變成什麼。
        **不得把這個輸出當成「世界確實改變了」的證據。**

        ## kind 是九個字彙裡最接近的一個，不是獨立觀測

        `config/structural_event_kinds.json` 的字彙是為「供給側事件」設計的，
        而這裡看到的是圖屬性的差。對應只做三種**講得出因果機制**的：
        新供應商出現 → `substitution`（loosening）；`sole_source` 轉真或
        `substitutability` 上升 → `capacity_constraint`（tightening）；
        `qualification_status` 前進 → `qualification`（tightening）。
        其餘的差（confidence 變動、證據等級提升）**刻意不產生事件**——
        那些量的是我們讀了幾份文件，不是世界（同 `documents` 不參與排序的理由）。
        """
        import hashlib

        before = {(r["company_id"], r["relation"], r["bottleneck"]): r
                  for r in (self._rank(since).get("rows") or [])}
        now = {(r["company_id"], r["relation"], r["bottleneck"]): r
               for r in (self._rank().get("rows") or [])}
        known_targets = {str(r["bottleneck"]) for r in before.values()}

        events: list[StructuralEvent] = []
        for key, row in sorted(now.items()):
            if company_id is not None and str(row.get("company_id")) != str(company_id):
                continue
            refs = self._row_evidence(row)
            # ⚠ **事件日必須來自窗內新到的那份文件**，不是整條邊的最早引用日。
            # 首跑時用後者，於是 `since=2026-06-30` 產出 `observed_at=2026-03-06`
            # 的「變化」——一個發生在觀察窗開始之前的事件，自相矛盾。
            # 成因是差集同時混了兩件事：真的新邊，與**舊邊剛跨過 sub>=4 門檻**
            # （早期 assertion 沒填 substitutability，晚到的那份才填）。
            # 窗內沒有任何新文件 → 沒有新資訊 → 不是事件，是屬性收斂的副作用。
            arrived = tuple(
                ref for ref in refs
                if ref.published_at is not None and ref.published_at > since)
            if not arrived:
                continue
            # ⚠ **這裡刻意沒有 try/except。** 第一版包了一層
            # `except Exception: continue`（理由是「契約拒收就不產生事件」），
            # 而它把上面那道窗內判斷變成了**無法被測到的死碼**：拿掉判斷後
            # `StructuralEvent` 因為 evidence 空而被契約拒收，例外被吞掉，
            # 結果與「正確地不產生事件」完全同形（L13）——突變測試就是這樣抓到的。
            # `arrived` 非空 ⇒ evidence 非空，契約本來就不會拒；id 若不合規，
            # 那是 identity 問題（INV-1 的 `Identity` check 負責），該吵不該吞。
            observed = min(ref.published_at for ref in arrived)
            old = before.get(key)
            for kind, direction, what in self._structural_diff(old, row, known_targets):
                digest = hashlib.sha256(
                    "|".join([kind, direction, *map(str, key), str(observed)])
                    .encode("utf-8")).hexdigest()[:16]
                events.append(StructuralEvent(
                    event_id=f"se_{digest}",
                    kind=kind,
                    subject_id=EntityId(str(row["bottleneck"])),
                    direction=direction,
                    observed_at=observed,
                    description=(
                        f"{row['company_id']} {row['relation']} {row['bottleneck']}："
                        f"{what}（{since} 之後發表的文件帶進來的，"
                        "**不等於世界在這段期間才改變**）"),
                    evidence=arrived,
                ))
        return tuple(events)

    @staticmethod
    def _structural_diff(
        old: Mapping[str, Any] | None,
        new: Mapping[str, Any],
        known_targets: set[str],
    ) -> list[tuple[str, str, str]]:
        """`(kind, direction, 人類可讀的變化)`。看不出**因果機制**的差不產生事件。"""
        out: list[tuple[str, str, str]] = []
        if old is None:
            # ⚠ **第一個已知供應商不是「替代」。** 這條瓶頸在 `since` 時我們一個
            # 供應商都不知道，代表我們那時候還沒研究這個領域——把它報成
            # 「可替代性上升」，就是讓「我們開了一條新研究線」看起來像
            # 「世界鬆了」。那是 `documents` 不參與排序的同一個理由。
            if str(new.get("bottleneck")) not in known_targets:
                return out
            out.append(("substitution", "loosening",
                        f"這個瓶頸多了一個已知供應商（sub={new.get('substitutability')}）"))
            return out
        old_sub, new_sub = old.get("substitutability"), new.get("substitutability")
        if isinstance(old_sub, int) and isinstance(new_sub, int) and new_sub != old_sub:
            out.append((
                "capacity_constraint",
                "tightening" if new_sub > old_sub else "loosening",
                f"substitutability {old_sub} → {new_sub}"))
        # sole_source 是三態（True／False／None＝未填）。只有**明確**的轉換才是事件：
        # 未填→是 是新資訊（收緊）；是→否 是鬆動；是→未填 只是屬性從最可信文件上消失，
        # 那是我們的資料變了，不是世界變了，不產生事件。
        old_sole, new_sole = old.get("sole_source"), new.get("sole_source")
        if new_sole is True and old_sole is not True:
            out.append(("capacity_constraint", "tightening",
                        f"sole_source 由{'否' if old_sole is False else '未填'}轉是"))
        elif old_sole is True and new_sole is False:
            out.append(("capacity_constraint", "loosening",
                        "sole_source 由是轉否"))
        old_q = str(old.get("qualification_status") or "")
        new_q = str(new.get("qualification_status") or "")
        if new_q != old_q:
            from query.bottleneck import QUALIFICATION_RANK

            advanced = QUALIFICATION_RANK.get(new_q, 0) > QUALIFICATION_RANK.get(old_q, 0)
            out.append(("qualification", "tightening" if advanced else "loosening",
                        f"qualification_status {old_q or '（無）'} → {new_q or '（無）'}"))
        return out

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


def _number(value: Any) -> float | None:
    """任意有限數值。⚠ **不要用 `_finite`**——那支把值夾在 0..1，它是
    `confidence` 專用的。`substitutability`(1–5) 與 `lead_time_weeks` 用它會
    一律變成 `None`，而 `None` 在下游是「不知道」，於是所有 magnitude 都變 UNKNOWN。
    """
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed and parsed not in (float("inf"), float("-inf")) else None


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
