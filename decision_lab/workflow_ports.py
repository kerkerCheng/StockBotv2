"""Engine D operational workflow 的外部 authority ports。

本模組只定義 normalized contract，不匯入 Engine A/C、Google Sheet 或市場
provider 的 concrete implementation。這讓 workflow 可以在測試中注入 deterministic
fixtures，也避免 Decision Lab domain package 反向依賴 current-state authorities。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class AuthorityWorkOrder:
    """外部 authority 缺口的 bounded、可公開下一步。"""

    code: str
    authority: str
    missing_fields: tuple[str, ...]
    next_step: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "authority": self.authority,
            "missing_fields": list(self.missing_fields),
            "next_step": self.next_step,
        }


@dataclass(frozen=True)
class IdentityAuthority:
    """Neutral registry 驗證後的 canonical identity；unresolved 也可傳入 workflow。"""

    status: str
    company_id: str | None = None
    research_ticker: str | None = None
    execution_symbol: str | None = None
    market_currency: str | None = None
    execution_currency: str | None = None
    execution_venue: str | None = None
    blockers: tuple[str, ...] = ()
    # 報價單位只給行情層換算用，不進 frozen context identity——結算幣別才是
    # 決策語意，換算事實由 market payload 的 quote_* 欄位留痕。
    market_quote_unit: str | None = None
    execution_quote_unit: str | None = None

    def as_context_input(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "company_id": self.company_id,
            "research_ticker": self.research_ticker,
            "execution_symbol": self.execution_symbol,
            "market_currency": self.market_currency,
            "execution_currency": self.execution_currency,
            "execution_venue": self.execution_venue,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class AuthoritySnapshot:
    """一次 evaluation 實際取得的 normalized current-state authority slice。"""

    identity: IdentityAuthority
    evidence: Mapping[str, Any]
    financial: Mapping[str, Any]
    market: Mapping[str, Any]
    fx: Mapping[str, Any]
    holdings: Mapping[str, Any]
    execution_market: Mapping[str, Any] | None = None
    execution_fx: Mapping[str, Any] | None = None
    work_orders: tuple[AuthorityWorkOrder, ...] = ()
    statuses: Mapping[str, str] = field(default_factory=dict)

    def as_context_inputs(self) -> dict[str, Any]:
        """回傳可直接交給 context builder 的 private normalized payload。"""

        return {
            "identity": self.identity.as_context_input(),
            "evidence": dict(self.evidence),
            "financial": dict(self.financial),
            "market": dict(self.market),
            "fx": dict(self.fx),
            "holdings": dict(self.holdings),
            "execution_market": (
                dict(self.execution_market)
                if self.execution_market is not None
                else None
            ),
            "execution_fx": (
                dict(self.execution_fx) if self.execution_fx is not None else None
            ),
        }

    def public_statuses(self) -> dict[str, str]:
        """只公開 authority/status，不公開持股 rows 或 provider payload。"""

        return {str(key): str(value) for key, value in sorted(self.statuses.items())}


@runtime_checkable
class WorkflowDataProvider(Protocol):
    """Operational workflow 唯一依賴的 authority composition seam。"""

    def resolve_identity(
        self,
        *,
        company_id_hint: str | None = None,
        ticker_hint: str | None = None,
        company_hint: str | None = None,
    ) -> IdentityAuthority:
        """只做 exact lookup；不得 fuzzy match 或自行建 company ID。"""

    def snapshot(
        self,
        *,
        identity: IdentityAuthority,
        evaluation_at: str,
    ) -> AuthoritySnapshot:
        """取得一次 evaluation 的 bounded authority slice。"""

    def current_holdings(self, *, evaluation_at: str) -> Mapping[str, Any]:
        """供 today brief 唯讀取得 current Sheet snapshot。"""

