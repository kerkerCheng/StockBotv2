"""Engine D 的唯讀 default authority adapters。

Concrete Engine A/C、market 與 Google Sheet imports 刻意留在這個 composition
package；``decision_lab`` 只依賴 ``workflow_ports`` 的 normalized contract。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from decision_lab.adapters.graph import Neo4jReadOnlyQueryPort
from decision_lab.identity import resolve_identity as resolve_registered_identity
from decision_lab.workflow_ports import (
    AuthoritySnapshot,
    AuthorityWorkOrder,
    IdentityAuthority,
)
from engine_c.checklist import get_checklist, get_probe_financial_baseline
from engine_c.market_data import get_fx_snapshot, get_tradeability_snapshot
from fetchers.gsheets import fetch_portfolio, get_execution_aliases
from identity.registry import IdentityRegistry, get_registry


ExactRowsFetcher = Callable[[], Sequence[Mapping[str, Any]]]
FxFetcher = Callable[[str, str], Mapping[str, Any]]


def _fetch_operational_portfolio() -> Sequence[Mapping[str, Any]]:
    return fetch_portfolio(strict_operational=True)


_EXACT_COMPANY_QUERY = """
MATCH (company:Company)
WHERE toLower(trim(company.name)) = toLower(trim($company_name))
RETURN company.id AS company_id
ORDER BY company.id
LIMIT 2
""".strip()


_BOUNDED_EVIDENCE_QUERY = """
OPTIONAL MATCH (any:Entity)
WITH count(any) AS graph_node_count
OPTIONAL MATCH (focus:Entity {id: $company_id})
WITH graph_node_count, focus
OPTIONAL MATCH (focus)-[rel]-(neighbor:Entity)
WITH graph_node_count, focus, rel, neighbor
ORDER BY coalesce(rel.confidence, 0.0) DESC, coalesce(rel.edge_key, '')
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
           claim_type: claim.claim_type,
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
        if resolved.market_currency is None:
            blockers.append("market_currency_missing")
        if resolved.execution_currency is None:
            blockers.append("execution_currency_missing")
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
                _BOUNDED_EVIDENCE_QUERY,
                company_id=identity.company_id,
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
        counter_paths = sorted(
            {
                str(edge["edge_key"])
                for edge in edges
                if isinstance(edge.get("edge_key"), str)
                and any(
                    token in str(edge.get("relation") or "").casefold()
                    for token in ("substitut", "alternative", "compete", "counter")
                )
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
        }
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
                if not isinstance(raw_base, str) or len(raw_base.strip()) != 3:
                    return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
                base_currencies.add(raw_base.strip().upper())
        if len(nav_values) != 1 or len(base_currencies) != 1:
            return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}

        normalized_rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            assert isinstance(raw, Mapping)
            ticker = raw.get("ticker")
            currency = raw.get("currency")
            shares = _finite(raw.get("shares"))
            market_value = _finite(raw.get("market_value_base"), non_negative=True)
            if (
                not isinstance(ticker, str)
                or not ticker.strip()
                or not isinstance(currency, str)
                or len(currency.strip()) != 3
                or shares is None
                or market_value is None
            ):
                return {"status": "malformed", "rows": [], "blockers": ["holdings_malformed"]}
            row = {
                "ticker": ticker.strip().upper(),
                "shares": shares,
                "currency": currency.strip().upper(),
                "market_value_base": market_value,
            }
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

    def snapshot(
        self,
        *,
        identity: IdentityAuthority,
        evaluation_at: str,
    ) -> AuthoritySnapshot:
        evidence, graph_orders = self._read_graph(identity)
        financial, financial_orders = self._read_financial(identity.research_ticker)
        market, market_orders = self._read_market(
            identity.research_ticker,
            identity.market_currency,
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
                identity.execution_currency,
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
    "_BOUNDED_EVIDENCE_QUERY",
    "_EXACT_COMPANY_QUERY",
]
