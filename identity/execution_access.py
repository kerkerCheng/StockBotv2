"""買得到嗎（盲點修法第 19 條，2026-11-03）——一個市場一條規則、個別代號可例外；判法只有這一份（L16）。

使用者 2026-11-02「我基本上是台股+IB，IB有就有」、2026-11-03「IB這些都可以下」。買不到的只當層證據與主題組成員：
不寫個股敘事、不進 paper lane（`scripts/outcome_if_settled_today.paper_lane_plan`）。

- 表上的市場＝買得到（台股走台灣券商、其餘 IB）；市場不在表上＝不知道（`buyable=None`），不猜。
- 例外帶出處、查核日、重查日；過了重查日例外失效、照市場規則算——`exception_expired=True`，呼叫端要印出來
  （重問，不是丟；INV-2）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "execution_access.json"
#: 美股研究代號沒有交易所後綴。
US_MARKET = "US"
MARKET_FIELDS = frozenset({"channel", "basis"})
EXCEPTION_FIELDS = frozenset({"buyable", "why", "source", "checked", "recheck_by"})
_SUFFIX = re.compile(r"\.([A-Z]+)$")


class ExecutionAccessError(ValueError):
    """config 形狀不對——整份不用（呼叫端記成「沒算」，不當成都買得到）。"""


@dataclass(frozen=True, slots=True)
class Access:
    ticker: str
    market: str
    #: True＝買得到、False＝買不到（例外）、None＝市場不在表上（不知道）。
    buyable: bool | None
    channel: str | None
    #: 例外的理由；照市場規則判的是 None。
    why: str | None
    #: 有例外、但過了重查日——照市場規則算了，要有人重查。
    exception_expired: bool


def market_of(ticker: str) -> str:
    match = _SUFFIX.search(str(ticker or "").strip().upper())
    return match.group(1) if match else US_MARKET


def load(path: Path | None = None) -> dict[str, Any]:
    data = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: Mapping[str, Any]) -> None:
    markets = data.get("markets")
    if not isinstance(markets, Mapping) or not markets:
        raise ExecutionAccessError("markets 必須是非空的 mapping")
    for market, rule in markets.items():
        if (not isinstance(rule, Mapping) or set(rule) != MARKET_FIELDS
                or not all(isinstance(rule[k], str) and rule[k].strip() for k in MARKET_FIELDS)):
            raise ExecutionAccessError(f"市場 {market}：欄位必須恰好是 {sorted(MARKET_FIELDS)}、而且不得空白")
    exceptions = data.get("exceptions") or {}
    if not isinstance(exceptions, Mapping):
        raise ExecutionAccessError("exceptions 必須是 mapping")
    for ticker, entry in exceptions.items():
        if ticker != ticker.strip().upper():
            raise ExecutionAccessError(f"例外 {ticker!r}：代號要大寫、不帶空白（查的時候一律轉大寫）")
        if not isinstance(entry, Mapping) or set(entry) != EXCEPTION_FIELDS:
            raise ExecutionAccessError(f"例外 {ticker}：欄位必須恰好是 {sorted(EXCEPTION_FIELDS)}")
        if not isinstance(entry["buyable"], bool):
            raise ExecutionAccessError(f"例外 {ticker}：buyable 必須是 true／false")
        if not all(isinstance(entry[k], str) and entry[k].strip() for k in ("why", "source")):
            raise ExecutionAccessError(f"例外 {ticker}：why、source 不得空白")
        if _day(entry["recheck_by"], ticker, "recheck_by") <= _day(entry["checked"], ticker, "checked"):
            raise ExecutionAccessError(f"例外 {ticker}：recheck_by 必須晚於 checked（每個等待都要有到期，INV-2）")
        if market_of(ticker) not in markets:
            raise ExecutionAccessError(f"例外 {ticker}：市場 {market_of(ticker)} 不在 markets——先登記市場規則")


def _day(value: Any, ticker: str, key: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ExecutionAccessError(f"例外 {ticker}：{key} 不是 YYYY-MM-DD：{value!r}") from exc


def access(ticker: str, *, today: date, data: Mapping[str, Any]) -> Access:
    """`data` 是 `load()` 驗過的那份。"""
    key = str(ticker or "").strip().upper()
    market = market_of(key)
    rule = (data.get("markets") or {}).get(market)
    channel = str(rule["channel"]) if rule else None
    entry = (data.get("exceptions") or {}).get(key)
    expired = bool(entry) and date.fromisoformat(str(entry["recheck_by"])) < today
    if entry and not expired:
        return Access(key, market, bool(entry["buyable"]), channel, str(entry["why"]), False)
    return Access(key, market, True if rule else None, channel, None, expired)
