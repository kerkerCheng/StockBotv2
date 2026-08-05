"""報價單位（quote unit）與 ISO-4217 結算幣別的中立 registry。

交易所報價單位不等於結算幣別：LSE 以便士（GBp）報價、TASE 以 agorot（ILA）、
JSE 以 cents（ZAc），而 Yahoo 等 provider 直接把報價單位當成 ``currency`` 回傳。
把兩者混成同一個欄位有兩種壞法，而且都很安靜：

* 驗證器只收 3 碼大寫 ISO code 時，整份行情被 quarantine（IQE.L 即如此）。
* 為了通過驗證硬把 registry 改成 ``GBP``，價格會差 100 倍。

本模組是唯一的正規化入口。新市場只有兩種情況：以 ISO code 報價（TWD／SEK／
JPY…）不必登記就能用；以 minor unit 報價則在 ``config/currency_units.json``
加一列。都不命中時 fail closed，不猜測。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_UNITS_PATH = _ROOT / "config" / "currency_units.json"

_ISO_CODE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class QuoteUnit:
    """一個報價單位，以及換算回結算幣別所需的乘數。"""

    quote_code: str
    currency: str
    factor: float

    @property
    def is_minor_unit(self) -> bool:
        return self.factor != 1.0

    def to_settlement(self, amount: float) -> float:
        """把以 quote unit 計價的金額換算成結算幣別金額。"""

        return amount * self.factor


class QuoteUnitRegistry:
    """只讀 quote unit lookup；未登記且非 ISO 形式一律回 None。"""

    def __init__(self, *, version: int, units: tuple[QuoteUnit, ...]):
        if version < 1:
            raise ValueError("currency unit registry version must be positive")
        by_code: dict[str, QuoteUnit] = {}
        for unit in units:
            if not unit.quote_code.strip():
                raise ValueError("quote_code must not be empty")
            if unit.quote_code in by_code:
                raise ValueError(f"duplicate quote_code: {unit.quote_code}")
            if not _ISO_CODE.match(unit.currency):
                raise ValueError(f"settlement currency must be ISO-4217: {unit.currency!r}")
            if not (0 < unit.factor <= 1):
                raise ValueError(f"factor must be in (0, 1]: {unit.factor!r}")
            by_code[unit.quote_code] = unit
        self.version = version
        self._by_code: Mapping[str, QuoteUnit] = MappingProxyType(by_code)

    @classmethod
    def from_path(cls, path: Path) -> "QuoteUnitRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_units = payload.get("quote_units")
        if not isinstance(raw_units, list):
            raise ValueError("currency unit registry quote_units must be a list")
        units = tuple(
            QuoteUnit(
                quote_code=str(item["quote_code"]),
                currency=str(item["currency"]),
                factor=float(item["factor"]),
            )
            for item in raw_units
        )
        return cls(version=int(payload["version"]), units=units)

    @property
    def minor_units(self) -> Mapping[str, QuoteUnit]:
        return self._by_code

    def resolve(self, code: Any) -> QuoteUnit | None:
        """把任意報價單位／幣別字串正規化成 QuoteUnit；無法確定時回 None。

        比對順序刻意是大小寫敏感的 registry 優先：``GBp`` 與 ``GBP`` 只差一個
        字母大小寫，先折疊大小寫會讓結算幣別 GBP 被當成便士而多除 100。
        """

        if not isinstance(code, str):
            return None
        text = code.strip()
        if not text:
            return None
        registered = self._by_code.get(text)
        if registered is not None:
            return registered
        upper = text.upper()
        if _ISO_CODE.match(upper):
            return QuoteUnit(quote_code=text, currency=upper, factor=1.0)
        return None


@lru_cache(maxsize=1)
def get_quote_unit_registry() -> QuoteUnitRegistry:
    """載入版本控制內的唯一 quote unit registry。"""

    return QuoteUnitRegistry.from_path(_DEFAULT_UNITS_PATH)


def resolve_quote_unit(code: Any) -> QuoteUnit | None:
    """模組級捷徑；語意同 :meth:`QuoteUnitRegistry.resolve`。"""

    return get_quote_unit_registry().resolve(code)


def settlement_currency(code: Any) -> str | None:
    """回傳該報價單位對應的 ISO 結算幣別；無法確定時回 None。"""

    unit = resolve_quote_unit(code)
    return unit.currency if unit is not None else None


def is_settlement_currency(code: Any) -> bool:
    """該字串本身是否已經是 canonical ISO-4217 結算幣別。

    刻意嚴格：``"GBP"`` 為真，``"gbp"``（未正規化）與 ``"GBp"``（minor unit）
    皆為偽。需要容錯正規化的呼叫點請改用 :func:`settlement_currency`。
    """

    unit = resolve_quote_unit(code)
    return (
        unit is not None
        and not unit.is_minor_unit
        and isinstance(code, str)
        and code.strip() == unit.currency
    )
