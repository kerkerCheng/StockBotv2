"""公司 ID、研究 ticker 與 factor tags 的中立 registry。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "company_identity.json"


@dataclass(frozen=True)
class CompanyIdentity:
    """一家公司跨 Engine A/C 與市場資料的穩定 identity。"""

    company_id: str
    research_ticker: str | None
    market_currency: str | None = None
    execution_currency: str | None = None
    execution_venue: str | None = None
    factor_tags: tuple[str, ...] = ()


class IdentityRegistry:
    """只讀 identity lookup；缺值不猜測。"""

    def __init__(self, *, version: int, companies: tuple[CompanyIdentity, ...]):
        if version < 1:
            raise ValueError("identity registry version must be positive")
        by_id: dict[str, CompanyIdentity] = {}
        by_ticker: dict[str, str] = {}
        for company in companies:
            if not company.company_id.startswith("co:"):
                raise ValueError(f"invalid company_id: {company.company_id!r}")
            if company.company_id in by_id:
                raise ValueError(f"duplicate company_id: {company.company_id}")
            by_id[company.company_id] = company
            if company.research_ticker:
                key = company.research_ticker.upper()
                if key in by_ticker:
                    raise ValueError(f"duplicate research ticker: {company.research_ticker}")
                by_ticker[key] = company.company_id
        self.version = version
        self._by_id: Mapping[str, CompanyIdentity] = MappingProxyType(by_id)
        self._by_ticker: Mapping[str, str] = MappingProxyType(by_ticker)

    @classmethod
    def from_path(cls, path: Path) -> "IdentityRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_companies = payload.get("companies")
        if not isinstance(raw_companies, list):
            raise ValueError("identity registry companies must be a list")
        companies = tuple(
            CompanyIdentity(
                company_id=str(item["company_id"]),
                research_ticker=(
                    str(item["research_ticker"])
                    if item.get("research_ticker") is not None
                    else None
                ),
                market_currency=item.get("market_currency"),
                execution_currency=item.get("execution_currency"),
                execution_venue=item.get("execution_venue"),
                factor_tags=tuple(str(tag) for tag in item.get("factor_tags", [])),
            )
            for item in raw_companies
        )
        return cls(version=int(payload["version"]), companies=companies)

    @property
    def ticker_map(self) -> Mapping[str, str | None]:
        return MappingProxyType(
            {key: value.research_ticker for key, value in self._by_id.items()}
        )

    def research_ticker(self, company_id: str) -> str | None:
        company = self._by_id.get(company_id)
        return company.research_ticker if company else None

    def company_id_for_ticker(self, ticker: str) -> str | None:
        return self._by_ticker.get(ticker.strip().upper())

    def factor_tags(self, company_id: str) -> tuple[str, ...]:
        company = self._by_id.get(company_id)
        return company.factor_tags if company else ()

    def company(self, company_id: str) -> CompanyIdentity | None:
        return self._by_id.get(company_id)

    def has_company(self, company_id: str) -> bool:
        return company_id in self._by_id


@lru_cache(maxsize=1)
def get_registry() -> IdentityRegistry:
    """載入版本控制內的唯一 registry。"""

    return IdentityRegistry.from_path(_DEFAULT_REGISTRY_PATH)


# 相容既有 dict-like consumers；值只在此由 registry 生成一次。
TICKER_MAP: dict[str, str | None] = dict(get_registry().ticker_map)
