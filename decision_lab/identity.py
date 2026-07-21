"""組合 neutral company registry 與 live execution alias。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from identity.registry import IdentityRegistry, get_registry


@dataclass(frozen=True)
class ResolvedIdentity:
    company_id: str | None
    research_ticker: str | None
    execution_symbol: str | None
    blockers: tuple[str, ...]
    market_currency: str | None = None
    execution_currency: str | None = None
    execution_venue: str | None = None


def resolve_identity(
    *,
    company_id: str | None = None,
    research_ticker: str | None = None,
    execution_aliases: Mapping[str, str] | None = None,
    registry: IdentityRegistry | None = None,
) -> ResolvedIdentity:
    """Fail closed；絕不從公司名稱或相似 ticker 猜 identity。"""

    registry = registry or get_registry()
    aliases = execution_aliases or {}

    resolved_company = company_id
    resolved_ticker = research_ticker.strip().upper() if research_ticker else None
    if resolved_company:
        if not registry.has_company(resolved_company):
            return ResolvedIdentity(None, None, None, ("unresolved_company_identity",))
        canonical_ticker = registry.research_ticker(resolved_company)
        if resolved_ticker and canonical_ticker != resolved_ticker:
            return ResolvedIdentity(
                resolved_company,
                canonical_ticker,
                None,
                ("identity_mismatch",),
            )
        resolved_ticker = canonical_ticker
    elif resolved_ticker:
        resolved_company = registry.company_id_for_ticker(resolved_ticker)

    if not resolved_company:
        return ResolvedIdentity(None, resolved_ticker, None, ("unresolved_company_identity",))

    execution_symbol = aliases.get(resolved_ticker, resolved_ticker) if resolved_ticker else None
    blockers = () if resolved_ticker else ("research_ticker_unavailable",)
    company = registry.company(resolved_company)
    return ResolvedIdentity(
        company_id=resolved_company,
        research_ticker=resolved_ticker,
        execution_symbol=execution_symbol,
        blockers=blockers,
        market_currency=company.market_currency if company else None,
        execution_currency=company.execution_currency if company else None,
        execution_venue=company.execution_venue if company else None,
    )
