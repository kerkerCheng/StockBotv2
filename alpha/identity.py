"""Identifier 型別——**ticker 不是 entity identity**（INV-1）。

## 為什麼要分型別，而不是統一用 `str`

`historical-failure-matrix.md` 的 F-IDENT 有 5 筆事故，全部是同一個形狀：
四種語意不同的識別字串共用 `str`，於是可以互相賦值而不報錯。

- **F-01**：憑公司名猜 `co:sivers`（實際是 `co:sivers_semiconductors`），週掃靜默漏掉。
- **F-02**：`currency` 同時是報價單位（`GBp`）與結算幣別（`GBP`）→ LSE 標的永久
  quarantine；而「修正」成 ISO code 會通過所有驗證卻餵出**差 100 倍**的價格。
- **F-03**：registry 缺 `market_currency` → identity 判 partial → 整段 market/fx
  被跳過，被誤診成「ETL universe 缺 TSM」。
- **F-05**：Sivers 三層 symbol（研究 `SIVE.ST`／Sheet `FRA:2DG`／provider `2DG.F`）。

**用 `str` 時這些只能靠人記得；分成型別後 runtime 就擋得住。**

## 這裡刻意**不**做的事

不做 identity resolution。`identity/registry.py` 是唯一的 resolution authority
（INV-1：禁止 downstream module 自建 ticker normalization）。本模組只提供
**型別與格式驗證**，把「這個字串是哪一種 identifier」變成可檢查的事實。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from .errors import IdentityError


# 圖節點 id 的前綴字彙。與 `schema/vocab.json` 的 type 對應，但這裡只驗形狀，
# 不驗該節點是否存在——存在與否是 registry／圖的問題，不是型別的問題。
ENTITY_PREFIXES: frozenset[str] = frozenset(
    {"co", "tech", "mat", "prod", "std", "person"}
)

_ENTITY_RE = re.compile(r"^(?P<prefix>[a-z]+):(?P<slug>[a-z0-9][a-z0-9_]*)$")
# ticker 允許字母數字、點（`SIVE.ST`／`6324.T`）、連字號（`BRK-B`）。
# **刻意不允許冒號**——冒號是 entity id 與 venue-qualified 執行代號的分隔符，
# 讓 `co:axt` 與 `FRA:2DG` 都無法冒充 research ticker。
_TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]*$")
_VENUE_RE = re.compile(r"^[A-Z0-9]{2,12}$")


@dataclass(frozen=True, slots=True, order=True)
class EntityId:
    """圖節點的全域 id，格式 `<prefix>:<slug>`（例 `tech:cpo`、`mat:inp_substrate`）。"""

    value: str
    _allowed_prefixes: ClassVar[frozenset[str]] = ENTITY_PREFIXES

    def __post_init__(self) -> None:
        match = _ENTITY_RE.match(self.value)
        if match is None:
            raise IdentityError(
                f"EntityId 必須是 '<prefix>:<slug>' 小寫格式：{self.value!r}"
            )
        prefix = match.group("prefix")
        if prefix not in type(self)._allowed_prefixes:
            raise IdentityError(
                f"EntityId 前綴 {prefix!r} 未登記；已知：{sorted(type(self)._allowed_prefixes)}"
            )

    @property
    def prefix(self) -> str:
        return self.value.split(":", 1)[0]

    @property
    def slug(self) -> str:
        return self.value.split(":", 1)[1]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class CompanyId(EntityId):
    """公司的 canonical、永久 id（`co:*`）。

    ⚠ 這是 entity identity；**它不是 ticker**。公司改名、換交易所、ticker 被回收，
    `CompanyId` 都不變。唯一 authority 是 `config/company_identity.json`。
    """

    _allowed_prefixes: ClassVar[frozenset[str]] = frozenset({"co"})


@dataclass(frozen=True, slots=True, order=True)
class Ticker:
    """研究用的 external identifier（`COHR`、`SIVE.ST`、`6324.T`）。

    ⚠ **可變**：會被改名、會被回收給另一家公司。任何把它當永久身分的用法都是 F-01 的形狀。
    """

    value: str

    def __post_init__(self) -> None:
        if not _TICKER_RE.match(self.value):
            raise IdentityError(
                f"Ticker 不得含冒號或空白（那是 EntityId／venue 代號的形狀）：{self.value!r}"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class Exchange:
    """交易所／venue 代號（`NASDAQ`、`FRA`、`TWSE`）——Ticker 的命名空間。"""

    value: str

    def __post_init__(self) -> None:
        if not _VENUE_RE.match(self.value):
            raise IdentityError(f"Exchange 必須是 2–12 位大寫英數：{self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class InstrumentId:
    """可交易標的＝`Exchange` ＋ `Ticker`（例 `FRA:2DG`）。

    一個 `CompanyId` 可對應多個 `InstrumentId`（Sivers 同時有 `STO:SIVE` 與 `FRA:2DG`）。
    **研究用哪一個、執行用哪一個，是兩個不同的問題**（F-05）。
    """

    exchange: Exchange
    ticker: Ticker

    @classmethod
    def parse(cls, value: str) -> "InstrumentId":
        if ":" not in value:
            raise IdentityError(
                f"InstrumentId 必須是 '<EXCHANGE>:<TICKER>'：{value!r}"
            )
        venue, symbol = value.split(":", 1)
        return cls(Exchange(venue), Ticker(symbol))

    def __str__(self) -> str:
        return f"{self.exchange}:{self.ticker}"


@dataclass(frozen=True, slots=True, order=True)
class Alias:
    """歷史或別名 ticker。保留 `retired_at` 讓 point-in-time 解析成為可能。"""

    ticker: Ticker
    retired_at: str | None = None

    def __str__(self) -> str:
        return str(self.ticker)


@dataclass(frozen=True, slots=True, order=True)
class ExternalProviderId:
    """provider 專屬識別（`yfinance:2DG.F`、`sec:0001045810`、`mops:3081`）。

    ⚠ 與 `InstrumentId` 分開的理由：provider 的 symbol 語法是**該 provider 的實作細節**，
    不是市場事實。`identity/execution.py` 已經在做這層正規化，這裡只給它一個型別。
    """

    provider: str
    value: str

    def __post_init__(self) -> None:
        if not self.provider or ":" in self.provider:
            raise IdentityError(f"provider 名稱不合法：{self.provider!r}")
        if not self.value:
            raise IdentityError("ExternalProviderId.value 不得為空")

    def __str__(self) -> str:
        return f"{self.provider}:{self.value}"


#: 這些型別在語意上是**純量識別字串**，只是被包成型別以免互相賦值（INV-1）。
#: 序列化時應渲染成字串（`"COHR"`）而不是物件（`{"value": "COHR"}`）——
#: 否則 digest payload 與 fixture 會被無意義的巢狀結構淹沒。
SCALAR_IDENTIFIERS: tuple[type, ...] = (
    EntityId, CompanyId, Ticker, Exchange, InstrumentId, Alias, ExternalProviderId,
)
