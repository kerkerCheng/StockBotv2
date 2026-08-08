"""Engine D 的唯讀 default authority adapters。

Concrete Engine A/C、market 與 Google Sheet imports 刻意留在這個 composition
package；``decision_lab`` 只依賴 ``workflow_ports`` 的 normalized contract。
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from decision_lab.adapters.graph import Neo4jReadOnlyQueryPort
from decision_lab.identity import resolve_identity as resolve_registered_identity
from decision_lab.workflow_ports import (
    AuthoritySnapshot,
    AuthorityWorkOrder,
    IdentityAuthority,
)
from engine_c.checklist import get_checklist, get_probe_financial_baseline
from engine_c.market_data import (
    get_fx_snapshot,
    get_historical_tradeability_snapshot as get_historical_market_snapshot,
    get_tradeability_snapshot,
)
from fetchers.gsheets import fetch_portfolio, get_execution_aliases
from identity.currency import settlement_currency
from identity.registry import IdentityRegistry, get_registry


ExactRowsFetcher = Callable[[], Sequence[Mapping[str, Any]]]
FxFetcher = Callable[[str, str], Mapping[str, Any]]


def _fetch_operational_portfolio() -> Sequence[Mapping[str, Any]]:
    return fetch_portfolio(strict_operational=True)


_VOCAB_PATH = Path(__file__).resolve().parent.parent / "schema" / "vocab.json"


@lru_cache(maxsize=1)
def counter_path_relations() -> frozenset[str]:
    """哪些 relation 算 counter path；唯一權威是 schema/vocab.json。

    先前是對 relation 名稱做子字串比對（substitut／alternative／compete／counter）。
    那讓「哪些關係算反向路徑」這件事沒有明確登記處：它猜不到 constrained_by，
    也會誤命中未來任何名字裡剛好有 counter 的 relation。明列之後，新增 relation
    時就必須順便決定它算不算反向路徑——這正是應該被強迫回答的問題。
    """

    payload = json.loads(_VOCAB_PATH.read_text(encoding="utf-8"))
    values = payload.get("counter_path_relation")
    if not isinstance(values, list) or not values:
        raise ValueError("schema/vocab.json 缺少 counter_path_relation")
    return frozenset(str(value).casefold() for value in values)


# Sheet 的現金列標籤（大小寫與中英文皆可）。現金是 NAV 的一部分，但不是
# 可對應到 company／factor 的持股。
_CASH_BUCKET_LABELS = frozenset({"cash", "現金"})


_EXACT_COMPANY_QUERY = """
MATCH (company:Company)
WHERE toLower(trim(company.name)) = toLower(trim($company_name))
RETURN company.id AS company_id
ORDER BY company.id
LIMIT 2
""".strip()


# hop 上限是 literal：Cypher 不接受把 variable-length bound 參數化。值來自
# evidence_hops()，經 int 驗證後代入，不接受外部字串。
_BOUNDED_EVIDENCE_QUERY_TEMPLATE = """
OPTIONAL MATCH (any:Entity)
WITH count(any) AS graph_node_count
OPTIONAL MATCH (focus:Entity {id: $company_id})
WITH graph_node_count, focus
OPTIONAL MATCH path = (focus)-[*1..%(hops)d]-(:Entity)
UNWIND CASE WHEN path IS NULL THEN [NULL] ELSE relationships(path) END AS rel
WITH graph_node_count, focus, collect(DISTINCT rel) AS rels
UNWIND CASE WHEN size(rels) = 0 THEN [NULL] ELSE rels END AS rel
WITH graph_node_count, focus, rel,
     CASE
         WHEN rel IS NOT NULL AND toLower(type(rel)) IN $counter_relations THEN 1
         ELSE 0
     END AS is_counter,
     CASE
         WHEN rel IS NOT NULL
              AND (startNode(rel).id = $company_id OR endNode(rel).id = $company_id)
         THEN 1 ELSE 0
     END AS is_direct
// edge_limit 是取樣上限，排序決定誰先被犧牲。放寬 hop 之後兩件事都實測壞過：
//   1. co:axt 的 COMPETES_WITH（confidence 0.5）被遠處高信心邊擠掉 → gate 從
//      available 退回 graph_coverage_deficit。反證是 gate 唯一要看的東西，必須優先。
//   2. co:axt 自己 8 條直接因果邊被 2-hop 的遠處邊擠掉 → assessment 的 evidence_refs
//      集體失效。焦點公司的直接關係永遠比遠處鄰居重要。
// 因此排序是「反證 > 直接關係 > 信心」，距離不是靠 hop 上限來控制，是靠排序。
ORDER BY is_counter DESC, is_direct DESC,
         coalesce(rel.confidence, 0.0) DESC, coalesce(rel.edge_key, '')
LIMIT $edge_limit
OPTIONAL MATCH (claim:Claim)-[:ABOUT]->(focus)
OPTIONAL MATCH (claim)-[:CITES]->(claim_doc:SourceDoc)
OPTIONAL MATCH (assertion:EdgeAssertion)
WHERE rel IS NOT NULL AND assertion.edge_key = rel.edge_key
OPTIONAL MATCH (assertion)-[:CITES]->(assertion_doc:SourceDoc)
RETURN graph_node_count,
       focus.id AS focus_id,
       focus.name AS focus_name,
       collect(DISTINCT CASE WHEN rel IS NULL THEN NULL ELSE {
           edge_key: rel.edge_key,
           src_id: startNode(rel).id,
           dst_id: endNode(rel).id,
           relation: type(rel),
           confidence: rel.confidence,
           source_ids: coalesce(rel.source_ids, [])
       } END)[0..$edge_limit] AS edges,
       collect(DISTINCT CASE WHEN claim IS NULL THEN NULL ELSE {
           id: claim.id,
           statement: claim.statement,
           source_ids: coalesce(claim.source_ids, [])
       } END)[0..$claim_limit] AS claims,
       collect(DISTINCT CASE WHEN assertion IS NULL THEN NULL ELSE {
           id: assertion.id,
           edge_key: assertion.edge_key,
           source_ids: coalesce(assertion.source_ids, [])
       } END)[0..$assertion_limit] AS assertions,
       collect(DISTINCT CASE WHEN claim_doc IS NULL THEN NULL ELSE {
           id: claim_doc.id,
           origin_entity: claim_doc.origin_entity,
           evidence_tier: claim_doc.evidence_tier,
           source_type: claim_doc.source_type
       } END)[0..$source_limit] AS claim_sources,
       collect(DISTINCT CASE WHEN assertion_doc IS NULL THEN NULL ELSE {
           id: assertion_doc.id,
           origin_entity: assertion_doc.origin_entity,
           evidence_tier: assertion_doc.evidence_tier,
           source_type: assertion_doc.source_type
       } END)[0..$source_limit] AS assertion_sources
""".strip()


@lru_cache(maxsize=1)
def evidence_hops() -> int:
    """證據 bound 從 focus 公司往外走幾 hop；唯一權威是 investment_policy。

    先前寫死 1 hop，等於隱含「反證一定直接連到公司」。但 thesis 常常掛在產品上
    （co:meta -develops-> prod:vistara -constrained_by-> tech:cxl_memory_tiering），
    產品層級的反證因此對公司層級決策結構性隱形。

    ⚠ hop 數是「相關性」的代理指標，不是相關性本身。把它一路調大不會更正確，只會
    讓 edge_limit 被遠處的噪音佔滿。真正一般化的作法是讓 thesis 自己宣告它依賴哪些
    節點，用那個集合當 bound；在那之前，這個值應該保守，且每次調整都要重跑既有
    cohort 對照差異。
    """

    from thesis.investment_policy import load_policy

    hops = int(load_policy()["probe_lane"]["evidence_hops"])
    if not 1 <= hops <= 3:
        raise ValueError(f"evidence_hops 必須在 1..3：{hops}")
    return hops


@lru_cache(maxsize=1)
def bounded_evidence_query() -> str:
    return _BOUNDED_EVIDENCE_QUERY_TEMPLATE % {"hops": evidence_hops()}


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value.strip()) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or (non_negative and result < 0):
        return None
    return result


def _safe_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        if len(raw) == 10:
            parsed = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        else:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
    except ValueError:
        return None
    return parsed.isoformat()


def _safe_status(payload: Mapping[str, Any], default: str = "unavailable") -> str:
    value = payload.get("status")
    return str(value) if isinstance(value, str) and value else default


def _work_order(
    code: str,
    authority: str,
    missing_fields: Sequence[str],
    next_step: str,
) -> AuthorityWorkOrder:
    return AuthorityWorkOrder(
        code=code,
        authority=authority,
        missing_fields=tuple(sorted(set(missing_fields))),
        next_step=next_step,
    )


class DefaultRuntimeProvider:
    """唯讀組合 Engine A/C、market/FX 與 Sheet 的 default provider。"""

    def __init__(
        self,
        *,
        registry: IdentityRegistry | None = None,
        graph_port: Neo4jReadOnlyQueryPort | None = None,
        checklist_fetcher: Callable[[str], Mapping[str, Any]] = get_checklist,
        financial_fetcher: Callable[[str], Mapping[str, Any]] = get_probe_financial_baseline,
        market_fetcher: Callable[[str, str], Mapping[str, Any]] = get_tradeability_snapshot,
        fx_fetcher: FxFetcher | None = get_fx_snapshot,
        holdings_fetcher: ExactRowsFetcher = _fetch_operational_portfolio,
        aliases_fetcher: Callable[[], Mapping[str, str]] = get_execution_aliases,
    ) -> None:
        self._registry = registry or get_registry()
        self._graph = graph_port
        self._checklist_fetcher = checklist_fetcher
        self._financial_fetcher = financial_fetcher
        self._market_fetcher = market_fetcher
        self._fx_fetcher = fx_fetcher
        self._holdings_fetcher = holdings_fetcher
        self._aliases_fetcher = aliases_fetcher

    def resolve_identity(
        self,
        *,
        company_id_hint: str | None = None,
        ticker_hint: str | None = None,
        company_hint: str | None = None,
    ) -> IdentityAuthority:
        company_id = company_id_hint.strip() if isinstance(company_id_hint, str) else None
        ticker = ticker_hint.strip().upper() if isinstance(ticker_hint, str) else None
        company_name = company_hint.strip() if isinstance(company_hint, str) else None
        blockers: list[str] = []

        if not company_id and not ticker and company_name:
            if self._graph is None:
                return IdentityAuthority(
                    status="unresolved_identity",
                    blockers=("graph_unavailable", "unresolved_identity"),
                )
            try:
                rows = self._graph.query(
                    _EXACT_COMPANY_QUERY,
                    company_name=company_name,
                )
            except Exception:
                return IdentityAuthority(
                    status="unresolved_identity",
                    blockers=("graph_unavailable", "unresolved_identity"),
                )
            exact_ids = sorted(
                {
                    str(row["company_id"])
                    for row in rows
                    if isinstance(row, Mapping)
                    and isinstance(row.get("company_id"), str)
                }
            )
            if len(exact_ids) != 1:
                code = "identity_ambiguous" if len(exact_ids) > 1 else "unresolved_identity"
                return IdentityAuthority(status="unresolved_identity", blockers=(code,))
            company_id = exact_ids[0]

        try:
            aliases = dict(self._aliases_fetcher())
        except Exception:
            aliases = {}
            blockers.append("execution_aliases_unavailable")
        resolved = resolve_registered_identity(
            company_id=company_id,
            research_ticker=ticker,
            execution_aliases=aliases,
            registry=self._registry,
        )
        if resolved.company_id is None:
            return IdentityAuthority(
                status="unresolved_identity",
                research_ticker=resolved.research_ticker,
                blockers=tuple(sorted(set(blockers + ["unresolved_identity"]))),
            )

        blockers.extend(resolved.blockers)
        # 幣別解析不出來有兩種成因，修法完全不同：registry 根本沒填（補 config
        # 的 identity 那一列），或報價單位未登記（補 config/currency_units.json）。
        if resolved.market_currency is None:
            blockers.append(
                "market_quote_unit_unregistered"
                if resolved.market_quote_unit
                else "market_currency_missing"
            )
        if resolved.execution_currency is None:
            blockers.append(
                "execution_quote_unit_unregistered"
                if resolved.execution_quote_unit
                else "execution_currency_missing"
            )
        if resolved.execution_venue is None:
            blockers.append("execution_venue_missing")
        status = "resolved" if not blockers else "partial"
        return IdentityAuthority(
            status=status,
            company_id=resolved.company_id,
            research_ticker=resolved.research_ticker,
            execution_symbol=resolved.execution_symbol,
            market_currency=resolved.market_currency,
            execution_currency=resolved.execution_currency,
            execution_venue=resolved.execution_venue,
            market_quote_unit=resolved.market_quote_unit,
            execution_quote_unit=resolved.execution_quote_unit,
            blockers=tuple(sorted(set(blockers))),
        )

    def _read_graph(
        self,
        identity: IdentityAuthority,
    ) -> tuple[dict[str, Any], list[AuthorityWorkOrder]]:
        if identity.company_id is None:
            return (
                {
                    "status": "unresolved_identity",
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["unresolved_identity"],
                },
                [
                    _work_order(
                        "unresolved_identity",
                        "identity_registry",
                        ("company_id", "research_ticker"),
                        "提供 exact ticker 或先完成 company onboarding。",
                    )
                ],
            )
        if self._graph is None:
            return (
                {
                    "status": "graph_unavailable",
                    "focus_company": {"id": identity.company_id},
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["graph_unavailable"],
                },
                [
                    _work_order(
                        "graph_unavailable",
                        "engine_a",
                        ("bounded_graph_context",),
                        "設定 Engine D 專用 Neo4j read-only credentials 後重試。",
                    )
                ],
            )
        try:
            rows = self._graph.query(
                bounded_evidence_query(),
                company_id=identity.company_id,
                counter_relations=sorted(counter_path_relations()),
                edge_limit=24,
                claim_limit=24,
                assertion_limit=24,
                source_limit=32,
            )
        except Exception:
            return (
                {
                    "status": "graph_unavailable",
                    "focus_company": {"id": identity.company_id},
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["graph_unavailable"],
                },
                [
                    _work_order(
                        "graph_unavailable",
                        "engine_a",
                        ("bounded_graph_context",),
                        "確認 Neo4j read-only connection 後重試。",
                    )
                ],
            )
        row = rows[0] if rows and isinstance(rows[0], Mapping) else {}
        graph_count = row.get("graph_node_count")
        if not isinstance(graph_count, int) or graph_count <= 0:
            return (
                {
                    "status": "graph_empty",
                    "focus_company": {"id": identity.company_id},
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["graph_empty", "graph_coverage_deficit"],
                },
                [
                    _work_order(
                        "graph_empty",
                        "engine_a",
                        ("company", "evidence", "causal_path"),
                        "依 company-onboard 與 lead-intake 閘門建立 bounded evidence。",
                    )
                ],
            )
        if row.get("focus_id") != identity.company_id:
            return (
                {
                    "status": "graph_company_missing",
                    "focus_company": {"id": identity.company_id},
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["graph_company_missing", "graph_coverage_deficit"],
                },
                [
                    _work_order(
                        "graph_company_missing",
                        "engine_a",
                        (identity.company_id,),
                        "執行 company-onboard；不得以本次 assessment 自動寫圖。",
                    )
                ],
            )

        def clean_maps(value: Any) -> list[dict[str, Any]]:
            if not isinstance(value, list):
                return []
            return [dict(item) for item in value if isinstance(item, Mapping)]

        edges = clean_maps(row.get("edges"))
        claims = clean_maps(row.get("claims"))
        assertions = clean_maps(row.get("assertions"))
        source_by_id: dict[str, dict[str, Any]] = {}
        for source in clean_maps(row.get("claim_sources")) + clean_maps(
            row.get("assertion_sources")
        ):
            source_id = source.get("id")
            if isinstance(source_id, str) and source_id:
                source_by_id[source_id] = source
        causal_paths = sorted(
            {
                str(edge["edge_key"])
                for edge in edges
                if isinstance(edge.get("edge_key"), str)
            }
        )
        counter_relations = counter_path_relations()
        counter_paths = sorted(
            {
                str(edge["edge_key"])
                for edge in edges
                if isinstance(edge.get("edge_key"), str)
                and str(edge.get("relation") or "").casefold() in counter_relations
            }
        )
        sources = [source_by_id[key] for key in sorted(source_by_id)]
        blockers: list[str] = []
        if not sources or not causal_paths or not counter_paths:
            blockers.append("graph_coverage_deficit")
        evidence = {
            "status": "available" if not blockers else "graph_coverage_deficit",
            "focus_company": {
                "id": identity.company_id,
                "name": row.get("focus_name"),
            },
            "subject_origin_entity": row.get("focus_name"),
            "entities": [{"id": identity.company_id}],
            "edges": edges,
            "claims": claims,
            "assertions": assertions,
            "sources": sources,
            "causal_paths": causal_paths,
            "counter_paths": counter_paths,
            "blockers": blockers,
        }
        orders: list[AuthorityWorkOrder] = []
        if blockers:
            missing: list[str] = []
            if not sources:
                missing.append("independent_sources")
            if not causal_paths:
                missing.append("claim_to_economics_path")
            if not counter_paths:
                missing.append("counter_thesis_path")
            orders.append(
                _work_order(
                    "graph_coverage_deficit",
                    "engine_a",
                    missing,
                    "由 research agent 追一手來源；核准後再走既有 graph admission。",
                )
            )
        return evidence, orders

    def _read_financial(
        self,
        ticker: str | None,
    ) -> tuple[dict[str, Any], list[AuthorityWorkOrder]]:
        if not ticker:
            return (
                {"status": "missing", "blockers": ["financial_identity_missing"]},
                [
                    _work_order(
                        "financial_identity_missing",
                        "engine_c",
                        ("research_ticker",),
                        "先解析 canonical ticker。",
                    )
                ],
            )
        try:
            baseline = dict(self._financial_fetcher(ticker))
        except Exception:
            baseline = {"status": "unavailable"}
        try:
            checklist = dict(self._checklist_fetcher(ticker))
        except Exception:
            checklist = {"engine_c_available": False, "items": {}}
        status = _safe_status(baseline)
        if status in {"missing", "unavailable"}:
            return (
                {"status": status, "blockers": [f"financial_{status}"]},
                [
                    _work_order(
                        f"financial_{status}",
                        "engine_c",
                        ("financial_snapshot",),
                        "補齊可追溯 Engine C observation 後 reassess。",
                    )
                ],
            )
        as_of = _safe_timestamp(baseline.get("as_of"))
        fetched_at = _safe_timestamp(baseline.get("fetched_at"))
        if as_of is None or fetched_at is None or not baseline.get("source"):
            return (
                {"status": "malformed", "blockers": ["financial_malformed"]},
                [
                    _work_order(
                        "financial_malformed",
                        "engine_c",
                        ("as_of", "fetched_at", "source"),
                        "修正 Engine C observation provenance／timestamp。",
                    )
                ],
            )
        items = checklist.get("items") if isinstance(checklist.get("items"), Mapping) else {}
        normalized_checklist = {
            str(key): dict(item)
            for key, item in items.items()
            if isinstance(key, str) and isinstance(item, Mapping)
        }
        # 非 gate 的已登記人工觀測：開放讀取表面，每筆自帶 authorities，
        # 不參與 gate_pass，也不產生 work order（缺這些不算 coverage 缺口）。
        raw_observations = (
            checklist.get("observations")
            if isinstance(checklist.get("observations"), Mapping)
            else {}
        )
        normalized_observations = {
            str(key): dict(item)
            for key, item in raw_observations.items()
            if isinstance(key, str) and isinstance(item, Mapping)
        }
        result = {
            "status": status,
            "ticker": ticker,
            "as_of": as_of,
            "fetched_at": fetched_at,
            "source": str(baseline["source"]),
            "cash_and_equivalents": baseline.get("cash_and_equivalents"),
            "total_debt": baseline.get("total_debt"),
            "free_cash_flow_ttm": baseline.get("free_cash_flow_ttm"),
            "checklist": normalized_checklist,
            "observations": normalized_observations,
        }
        # yfinance 在財報後常暫時清空 free_cash_flow_ttm。derive_runway 接受人工
        # 補值並自行驗證 timestamp，但要有人把它帶過來才用得上。
        manual_runway = baseline.get("manual_runway")
        if isinstance(manual_runway, Mapping):
            result["manual_runway"] = dict(manual_runway)
        orders: list[AuthorityWorkOrder] = []
        if not checklist.get("engine_c_available"):
            orders.append(
                _work_order(
                    "financial_checklist_unavailable",
                    "engine_c",
                    ("financial_checklist",),
                    "確認 Engine C runtime 後重試。",
                )
            )
        for key, item in sorted(normalized_checklist.items()):
            item_status = item.get("status")
            if item_status in {"manual_required", "missing"}:
                orders.append(
                    _work_order(
                        f"financial_checklist_{item_status}:{key}",
                        "engine_c",
                        (key,),
                        "依 source-trace 取得一手來源並新增有 provenance 的 manual observation。",
                    )
                )
        return result, orders

    def _read_market(
        self,
        ticker: str | None,
        currency: str | None,
    ) -> tuple[dict[str, Any], list[AuthorityWorkOrder]]:
        if not ticker or not currency:
            missing = tuple(
                field
                for field, value in (("ticker", ticker), ("currency", currency))
                if not value
            )
            return (
                {"status": "missing", "blockers": ["market_missing"]},
                [
                    _work_order(
                        "market_missing",
                        "market",
                        missing,
                        "補齊 canonical market identity 或 price observation。",
                    )
                ],
            )
        try:
            raw = dict(self._market_fetcher(ticker, currency))
        except Exception:
            raw = {"status": "unavailable"}
        status = _safe_status(raw)
        if status not in {"observed", "available"}:
            normalized_status = status if status in {"missing", "unavailable"} else "malformed"
            return (
                {"status": normalized_status, "blockers": [f"market_{normalized_status}"]},
                [
                    _work_order(
                        f"market_{normalized_status}",
                        "market",
                        ("price", "adv20", "as_of"),
                        "取得同 ticker／currency 的可追溯市場快照。",
                    )
                ],
            )
        return (
            {
                key: raw[key]
                for key in (
                    "status",
                    "ticker",
                    "price",
                    "currency",
                    "adv20",
                    "as_of",
                    "fetched_at",
                    "unit_status",
                    "source",
                    "blockers",
                    # minor unit 換算留痕；只有 GBp／ILA 這類報價才會出現。
                    "quote_currency",
                    "quote_price",
                    "quote_factor",
                    # 丟棄了幾根未結算的 trailing bar；解釋 as_of 為何不是最新一根。
                    "unsettled_trailing_rows",
                )
                if key in raw
            },
            [],
        )

    def _read_fx(
        self,
        currency: str | None,
        base_currency: str,
        evaluation_at: str,
    ) -> tuple[dict[str, Any], list[AuthorityWorkOrder]]:
        if not currency:
            return (
                {"status": "missing", "blockers": ["fx_missing"]},
                [
                    _work_order(
                        "fx_missing",
                        "fx",
                        ("source_currency",),
                        "補齊 canonical market currency。",
                    )
                ],
            )
        pair = f"{currency}/{base_currency}"
        if currency == base_currency:
            return (
                {
                    "status": "observed",
                    "pair": pair,
                    "rate": 1.0,
                    "as_of": evaluation_at,
                    "fetched_at": evaluation_at,
                    "source": "identity://same-currency",
                },
                [],
            )
        if self._fx_fetcher is None:
            return (
                {"status": "missing", "pair": pair, "blockers": ["fx_missing"]},
                [
                    _work_order(
                        "fx_missing",
                        "fx",
                        (pair,),
                        "設定可回傳 exact pair／direction 的 FX provider。",
                    )
                ],
            )
        try:
            raw = dict(self._fx_fetcher(pair, evaluation_at))
        except Exception:
            raw = {"status": "unavailable"}
        status = _safe_status(raw)
        if status not in {"observed", "available"}:
            normalized_status = status if status in {"missing", "unavailable"} else "malformed"
            return (
                {"status": normalized_status, "pair": pair, "blockers": [f"fx_{normalized_status}"]},
                [
                    _work_order(
                        f"fx_{normalized_status}",
                        "fx",
                        (pair,),
                        "取得 exact direction 的可追溯 FX observation。",
                    )
                ],
            )
        safe = {
            key: raw[key]
            for key in ("status", "pair", "rate", "as_of", "fetched_at", "source")
            if key in raw
        }
        orders: list[AuthorityWorkOrder] = []
        if raw.get("pair") != pair:
            orders.append(
                _work_order(
                    "fx_direction_mismatch",
                    "fx",
                    (pair,),
                    "要求 provider 回傳 exact base/quote direction；不得倒數猜值。",
                )
            )
        return safe, orders

    def current_holdings(self, *, evaluation_at: str) -> Mapping[str, Any]:
        try:
            raw_rows = list(self._holdings_fetcher())
        except Exception:
            return {"status": "unavailable", "rows": [], "blockers": ["holdings_unavailable"]}
        if not raw_rows:
            return {
                "status": "available",
                "rows": [],
                "fetched_at": evaluation_at,
            }
        nav_values: set[float] = set()
        base_currencies: set[str] = set()
        for raw in raw_rows:
            if not isinstance(raw, Mapping):
                return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
            raw_nav = raw.get("nav_base")
            if raw_nav is not None and raw_nav != "":
                nav = _finite(raw_nav, non_negative=True)
                if nav is None or nav <= 0:
                    return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
                nav_values.add(nav)
            raw_base = raw.get("base_currency")
            if raw_base is not None and raw_base != "":
                base_settlement = settlement_currency(raw_base)
                if base_settlement is None:
                    return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
                base_currencies.add(base_settlement)
        if len(nav_values) != 1 or len(base_currencies) != 1:
            return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}

        normalized_rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            assert isinstance(raw, Mapping)
            ticker = raw.get("ticker")
            row_currency = settlement_currency(raw.get("currency"))
            shares = _finite(raw.get("shares"))
            market_value = _finite(raw.get("market_value_base"), non_negative=True)
            if (
                not isinstance(ticker, str)
                or not ticker.strip()
                or row_currency is None
                or shares is None
                or market_value is None
            ):
                return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
            row = {
                "ticker": ticker.strip().upper(),
                "shares": shares,
                "currency": row_currency,
                "market_value_base": market_value,
            }
            # 現金列計入 NAV，但沒有 company／factor 曝險可解析；不標記的話
            # 下游 live sizing 會把它當成對應不到公司的持股而 fail closed。
            bucket = raw.get("bucket")
            if isinstance(bucket, str) and bucket.strip().lower() in _CASH_BUCKET_LABELS:
                row["is_cash"] = True
            company_id = raw.get("company_id") or raw.get("neo4j_id")
            if company_id is not None:
                if not isinstance(company_id, str) or not self._registry.has_company(company_id):
                    return {
                        "status": "malformed",
                        "rows": [],
                        "blockers": ["holdings_company_id_invalid"],
                    }
                row["company_id"] = company_id
            normalized_rows.append(row)
        return {
            "status": "available",
            "rows": normalized_rows,
            "nav_base": next(iter(nav_values)),
            "base_currency": next(iter(base_currencies)),
            "fetched_at": evaluation_at,
        }

    def benchmark_return(
        self, *, symbol: str, since: str, evaluation_at: str
    ) -> float | None:
        """Benchmark 自 ``since`` 到現在的原始報酬（未做風險調整）。

        起點取「``since`` 之前最後一個完整交易日」，與 Shadow 回填同一條規則——
        用同日 bar 會拿到觀測者當時看不到的價格，使超額報酬被系統性高估。

        ⚠ 這是**原始**超額報酬。用一檔十天能漲 107%、也能跌 40% 的小型股贏過指數，
        不必然是技巧，可能只是承擔了更多波動；樣本夠長之前不做 beta 調整，但呈現層
        必須標明未調整。
        """

        del evaluation_at  # 現價一律取最新可得，不回溯到指定時刻
        start = get_historical_market_snapshot(symbol, "USD", before=since)
        end = self._market_fetcher(symbol, "USD")
        start_price = _finite(start.get("price"), non_negative=True)
        end_price = _finite(end.get("price"), non_negative=True)
        if (
            start.get("status") != "observed"
            or end.get("status") not in {"observed", "available"}
            or not start_price
            or end_price is None
        ):
            return None
        return end_price / start_price - 1.0

    def benchmark_snapshot(
        self, *, symbol: str, since: str
    ) -> dict[str, Any]:
        """組出 ``outcomes.close_probe`` 需要的 benchmark 區段。

        起點錨在 ``since``（＝Shadow inception）當日之前最後一個完整交易日，與
        Shadow 回填同一條規則；close_probe 只比對日期，不比對時戳（跨市場標的的
        bar 時戳帶各自交易所時區，比對時戳會讓跨市場歸因永久不可能）。
        """

        start = get_historical_market_snapshot(symbol, "USD", before=since)
        end = self._market_fetcher(symbol, "USD")
        if start.get("status") != "observed" or end.get("status") not in {
            "observed",
            "available",
        }:
            return {"status": "unavailable"}
        return {
            "status": "observed",
            "ticker": symbol,
            "start_price": start.get("price"),
            "start_as_of": since,
            "end_price": end.get("price"),
            "as_of": end.get("as_of"),
            "source": str(end.get("source") or "yfinance://history"),
        }

    def snapshot(
        self,
        *,
        identity: IdentityAuthority,
        evaluation_at: str,
    ) -> AuthoritySnapshot:
        evidence, graph_orders = self._read_graph(identity)
        financial, financial_orders = self._read_financial(identity.research_ticker)
        # 行情層要的是交易所報價單位（才知道要不要除 100）；FX 要的是結算幣別。
        market, market_orders = self._read_market(
            identity.research_ticker,
            identity.market_quote_unit or identity.market_currency,
        )
        fx, fx_orders = self._read_fx(identity.market_currency, "USD", evaluation_at)
        holdings = dict(self.current_holdings(evaluation_at=evaluation_at))
        holdings_orders: list[AuthorityWorkOrder] = []
        if holdings.get("status") != "available":
            status = str(holdings.get("status") or "unavailable")
            holdings_orders.append(
                _work_order(
                    f"holdings_{status}",
                    "google_sheet",
                    ("market_value_base", "nav_base", "base_currency"),
                    "確認 Sheet credentials 與 mark-to-market 欄位後重試。",
                )
            )

        execution_market: Mapping[str, Any] | None = None
        execution_fx: Mapping[str, Any] | None = None
        execution_orders: list[AuthorityWorkOrder] = []
        if (
            identity.execution_symbol
            and identity.execution_symbol != identity.research_ticker
        ):
            execution_market, orders = self._read_market(
                identity.execution_symbol,
                identity.execution_quote_unit or identity.execution_currency,
            )
            execution_orders.extend(orders)
        holdings_base = holdings.get("base_currency")
        if isinstance(holdings_base, str) and identity.execution_currency:
            if identity.execution_currency == holdings_base:
                execution_fx = None
            elif (
                identity.execution_currency == identity.market_currency
                and holdings_base == "USD"
            ):
                execution_fx = None
            else:
                execution_fx, orders = self._read_fx(
                    identity.execution_currency,
                    holdings_base,
                    evaluation_at,
                )
                execution_orders.extend(orders)

        work_orders = tuple(
            graph_orders
            + financial_orders
            + market_orders
            + fx_orders
            + holdings_orders
            + execution_orders
        )
        statuses = {
            "identity": identity.status,
            "graph": str(evidence.get("status") or "unavailable"),
            "financial": str(financial.get("status") or "unavailable"),
            "market": str(market.get("status") or "unavailable"),
            "fx": str(fx.get("status") or "unavailable"),
            "holdings": str(holdings.get("status") or "unavailable"),
        }
        if execution_market is not None:
            statuses["execution_market"] = str(
                execution_market.get("status") or "unavailable"
            )
        if execution_fx is not None:
            statuses["execution_fx"] = str(
                execution_fx.get("status") or "unavailable"
            )
        return AuthoritySnapshot(
            identity=identity,
            evidence=evidence,
            financial=financial,
            market=market,
            fx=fx,
            holdings=holdings,
            execution_market=execution_market,
            execution_fx=execution_fx,
            work_orders=work_orders,
            statuses=statuses,
        )

    def close(self) -> None:
        driver = getattr(self._graph, "_driver", None)
        close = getattr(driver, "close", None)
        if callable(close):
            close()


__all__ = [
    "DefaultRuntimeProvider",
    "bounded_evidence_query",
    "evidence_hops",
    "_EXACT_COMPANY_QUERY",
]
