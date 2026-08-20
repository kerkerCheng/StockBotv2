"""公司 ID 與研究／執行市場識別的中立 registry。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from identity.currency import resolve_quote_unit


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "company_identity.json"


def _quote_code(raw: Any) -> str | None:
    """保留 config 原始報價單位字串；未填為 None。"""

    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _settlement(raw: Any) -> str | None:
    """把 config 的報價單位正規化成 ISO 結算幣別；未登記則 None。"""

    unit = resolve_quote_unit(_quote_code(raw))
    return unit.currency if unit is not None else None


@dataclass(frozen=True)
class CompanyIdentity:
    """一家公司跨 Engine A/C 與市場資料的穩定 identity。

    ``config`` 寫的是交易所實際報價的單位（LSE 的 IQE 是 ``GBp``）；本 dataclass
    對外一律以 ISO 結算幣別呈現 ``*_currency``，原始報價單位另存 ``*_quote_unit``
    供行情層換算。未登記且非 ISO 形式的報價單位會讓 ``*_currency`` 為 None
    （fail closed），由 identity 解析層轉成可行動的 blocker。
    """

    company_id: str
    research_ticker: str | None
    # 同一家公司的其他交易代號。research_ticker 是**研究用主掛牌**（Sivers 是瑞典
    # 的 SIVE.ST），但同一家公司常有第二個公開代號：SIVEF 是 Sivers 的美國 OTC、
    # SKHY 是 SK Hynix 的美國 OTC。這些代號會出現在推文 cashtag 裡，而
    # `engine_b/entities.py` 的 base 反查只去交易所後綴（SIVE→SIVE.ST 可解，
    # SIVEF 不可解），於是同一家公司的 lead 有一部分永遠解析不到 company_id。
    # 該檔第 64 行的註解早已寫下「正解是在 registry 明列 alias／deny」——這就是它。
    # ⚠ alias 不得與任何公司的 research_ticker 或其他 alias 衝突，衝突即 raise：
    # registry 是 identity authority，寧可啟動失敗也不要靜默指向錯的公司。
    aliases: tuple[str, ...] = ()
    market_currency: str | None = None
    execution_currency: str | None = None
    execution_venue: str | None = None
    market_quote_unit: str | None = None
    execution_quote_unit: str | None = None
    # Alpha 歸因的比較基準。缺省是 QQQ：alpha 標的目前全是科技／半導體，拿含金融、
    # 能源、公用事業的全球指數（VWRA）當基準會系統性美化結果；而 QQQ 家族換算曝險
    # 約佔 NAV 24%，是這筆錢真實的替代去處。VWRA 仍是 beta sleeve 的基準，不是
    # alpha 歸因的基準——兩者角色不同。半導體標的可覆寫成 SOXX，回答「在對的產業
    # 裡有沒有選對股」。值必須是系統已在抓行情的 symbol，否則歸因會靜默失效。
    benchmark_symbol: str = "QQQ"


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
            for alias in company.aliases:
                alias_key = str(alias).strip().upper()
                if not alias_key:
                    continue
                if alias_key in by_ticker and by_ticker[alias_key] != company.company_id:
                    raise ValueError(
                        f"alias {alias_key} already maps to {by_ticker[alias_key]}"
                    )
                by_ticker[alias_key] = company.company_id
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
                market_currency=_settlement(item.get("market_currency")),
                execution_currency=_settlement(item.get("execution_currency")),
                execution_venue=item.get("execution_venue"),
                market_quote_unit=_quote_code(item.get("market_currency")),
                execution_quote_unit=_quote_code(item.get("execution_currency")),
                benchmark_symbol=str(item.get("benchmark_symbol") or "QQQ").strip().upper(),
                aliases=tuple(
                    str(a).strip().upper()
                    for a in (item.get("aliases") or ())
                    if str(a).strip()
                ),
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

    def company(self, company_id: str) -> CompanyIdentity | None:
        return self._by_id.get(company_id)

    def has_company(self, company_id: str) -> bool:
        return company_id in self._by_id

    @property
    def companies(self) -> tuple[CompanyIdentity, ...]:
        """全部已登記公司；只讀，供需要掃描整份 registry 的呼叫端使用。"""

        return tuple(self._by_id.values())


@lru_cache(maxsize=1)
def get_registry() -> IdentityRegistry:
    """載入版本控制內的唯一 registry。"""

    return IdentityRegistry.from_path(_DEFAULT_REGISTRY_PATH)


# 相容既有 dict-like consumers；值只在此由 registry 生成一次。
TICKER_MAP: dict[str, str | None] = dict(get_registry().ticker_map)
