"""公司 ID 與研究／執行市場識別的中立 registry。"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from identity.currency import resolve_quote_unit


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "company_identity.json"


@dataclass(frozen=True)
class ListedUnitRatio:
    """研究用主掛牌的一個交易單位＝幾股普通股，從哪天起（2026-11-03 批次三 E，使用者「E 1A」）。

    SEC companyfacts 的封面股數（`dei:EntityCommonStockSharesOutstanding`）是**普通股**；掛牌的若是 ADS（HIMX：1 ADS＝2 股），
    市值＝掛牌單位的價格 × 普通股 ÷ 比率。比率是 mechanical——任何人重讀那份申報都得到同一個數——所以住名冊、帶出處；
    **沒登記＝不算**（`alpha.three_questions.own_history` 照舊 `inputs_incompatible`，不猜）。直接掛牌普通股的登記 1。
    """

    effective_from: date | None   # None＝從掛牌起（只有第一段可以）
    ordinary_shares: float
    source: str                   # 哪份申報的哪一句（逐字）


_LISTED_UNIT_KEYS = frozenset({"effective_from", "ordinary_shares", "source"})


def _listed_unit_ratios(company_id: str, raw: Any) -> tuple[ListedUnitRatio, ...]:
    """名冊的 `ordinary_per_listed_unit`：形狀封閉，錯一格就整份名冊拒載——同 alias 衝突：寧可啟動失敗，不要算錯市值。"""

    if raw is None:
        return ()
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{company_id}：ordinary_per_listed_unit 必須是非空的 list")
    out: list[ListedUnitRatio] = []
    for index, item in enumerate(raw):
        where = f"{company_id}：ordinary_per_listed_unit[{index}]"
        if not isinstance(item, dict) or set(item) != _LISTED_UNIT_KEYS:
            raise ValueError(f"{where} 的鍵必須恰好是 {sorted(_LISTED_UNIT_KEYS)}")
        shares = item["ordinary_shares"]
        if isinstance(shares, bool) or not isinstance(shares, (int, float)) or not math.isfinite(shares) or shares <= 0:
            raise ValueError(f"{where}.ordinary_shares 必須是大於 0 的有限數（給的是 {shares!r}）")
        source = item["source"]
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"{where}.source 必須寫出處（哪份申報的哪一句）")
        start = item["effective_from"]
        if start is None:
            if index:
                raise ValueError(f"{where}.effective_from 只有第一段可以是 null（從掛牌起）")
            day = None
        else:
            try:
                day = date.fromisoformat(str(start))
            except ValueError as exc:
                raise ValueError(f"{where}.effective_from 不是 ISO 日期：{start!r}") from exc
            if out and out[-1].effective_from is not None and day <= out[-1].effective_from:
                raise ValueError(f"{where}.effective_from 必須比前一段晚")
        out.append(ListedUnitRatio(day, float(shares), source.strip()))
    return tuple(out)


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
    # 面向人的公司名稱（Step 5）。**只是名字，不是新的知識主張**——它可重新取得、
    # 任何人讀一次公司自己的財報封面都得到同一個字串（AGENTS 的 mechanical 判準）。
    # 沒登記就是 None：呈現層改用 `company_id（ticker）`，**不從 ID 猜名字**
    # （`co:iqe` → 「Iqe」是編出來的，不是公司的名字）。
    display_name: str | None = None
    # 名字的其他寫法：短名、中文名、引文常用的品牌名（2026-10-01 Phase 4 Step 4.1c）。
    # **只給名字比對用**（`query.bottleneck.company_name_forms`／`quote_names_company`）；
    # ⚠ **不進 `by_ticker`**：`company_id_for_ticker` 是資本歸屬路徑，不得被名字放寬（plan 不可越線 12）。
    # 與 `aliases` 不同：那是交易代號（SIVEF），這是名字（「華星光」「Sumitomo」）。
    name_aliases: tuple[str, ...] = ()
    # 執行代號：Sheet／券商用的寫法（Sivers 的 `FRA:2DG`）。`identity.execution.get_execution_aliases()`
    # 由它派生（2026-10-01 Phase 4 Step 4.1c；原本寫死在 `identity/execution.py`）。**不進 `by_ticker`**：
    # 持股解析走 execution 別名反查那一條規則（`portfolio/holdings.py`），不是 ticker 比對。
    execution_symbol: str | None = None
    # 主掛牌一個交易單位＝幾股普通股（`ListedUnitRatio`，帶生效日與出處；2026-11-03 批次三 E）。空＝沒登記。
    ordinary_per_listed_unit: tuple[ListedUnitRatio, ...] = ()

    def ordinary_per_listed_unit_on(self, day: date) -> ListedUnitRatio | None:
        """`day` 那天生效的比率；比第一段的生效日還早、或沒登記＝None（呼叫端不猜）。"""

        hit = None
        for entry in self.ordinary_per_listed_unit:
            if entry.effective_from is None or entry.effective_from <= day:
                hit = entry
        return hit


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
        # 執行代號在 by_ticker 建完之後才比：後面才登記的公司的 research_ticker 也算衝突。
        # ⚠ 衝突即 raise——寧可啟動失敗，也不要讓一個執行代號被反查成兩家之一（INV-1）。
        by_execution: dict[str, str] = {}
        for company in companies:
            symbol = (company.execution_symbol or "").strip().upper()
            if not symbol:
                continue
            if symbol in by_ticker:
                raise ValueError(
                    f"execution_symbol {symbol} of {company.company_id} collides with "
                    f"research ticker／alias of {by_ticker[symbol]}"
                )
            if symbol in by_execution:
                raise ValueError(
                    f"execution_symbol {symbol} already belongs to {by_execution[symbol]}"
                )
            by_execution[symbol] = company.company_id
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
                display_name=(str(item["display_name"]).strip() or None
                              if item.get("display_name") is not None else None),
                aliases=tuple(
                    str(a).strip().upper()
                    for a in (item.get("aliases") or ())
                    if str(a).strip()
                ),
                # 名字保留原本的大小寫（比對規則分大小寫，見 `query.bottleneck._form_pattern`）。
                name_aliases=tuple(
                    str(a).strip()
                    for a in (item.get("name_aliases") or ())
                    if str(a).strip()
                ),
                execution_symbol=(str(item["execution_symbol"]).strip().upper() or None
                                  if item.get("execution_symbol") is not None else None),
                ordinary_per_listed_unit=_listed_unit_ratios(
                    str(item["company_id"]), item.get("ordinary_per_listed_unit")),
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

    def execution_aliases(self) -> dict[str, str]:
        """`{research_ticker: execution_symbol}`——`identity.execution.get_execution_aliases()` 的唯一來源。"""

        return {
            company.research_ticker: company.execution_symbol
            for company in self._by_id.values()
            if company.execution_symbol and company.research_ticker
        }


@lru_cache(maxsize=1)
def get_registry() -> IdentityRegistry:
    """載入版本控制內的唯一 registry。"""

    return IdentityRegistry.from_path(_DEFAULT_REGISTRY_PATH)


# 相容既有 dict-like consumers；值只在此由 registry 生成一次。
TICKER_MAP: dict[str, str | None] = dict(get_registry().ticker_map)
