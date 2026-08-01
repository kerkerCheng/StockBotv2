"""TWSE 官方最新日行情 freshness oracle。"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Callable, Mapping
from urllib.request import urlopen


TWSE_STOCK_DAY_ALL_URL = (
    "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
)
_ROC_DATE = re.compile(r"^(?P<year>\d{3})(?P<month>\d{2})(?P<day>\d{2})$")


def twse_code(provider_symbol: str) -> str | None:
    """Return the TWSE code for a Yahoo-style ``CODE.TW`` symbol."""

    if not isinstance(provider_symbol, str):
        return None
    symbol = provider_symbol.strip().upper()
    if not symbol.endswith(".TW"):
        return None
    code = symbol[:-3].strip()
    return code or None


def _parse_roc_date(value: Any) -> str | None:
    match = _ROC_DATE.fullmatch(str(value or "").strip())
    if match is None:
        return None
    try:
        return date(
            int(match.group("year")) + 1911,
            int(match.group("month")),
            int(match.group("day")),
        ).isoformat()
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "--", "N/A", "nan"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    code = str(row.get("Code") or "").strip().upper()
    session_date = _parse_roc_date(row.get("Date"))
    close = _number(row.get("ClosingPrice"))
    change = _number(row.get("Change"))
    if not code or session_date is None or close is None or close <= 0:
        return None
    previous_close = close - change if change is not None else None
    change_pct = (
        round(change / previous_close, 12)
        if previous_close is not None and previous_close > 0
        else None
    )
    return {
        "code": code,
        "session_date": session_date,
        "close_raw": close,
        "change_raw": change,
        "change_pct": change_pct,
        "source": TWSE_STOCK_DAY_ALL_URL,
    }


def fetch_twse_latest_rows(
    *,
    opener: Callable[..., Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, dict[str, Any]]:
    """Fetch the latest official row for every listed TWSE security.

    This endpoint is deliberately used only as a freshness/reference source.
    It does not provide the adjusted-close history required by the technical
    indicator builder.
    """

    open_fn = opener or urlopen
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response = open_fn(TWSE_STOCK_DAY_ALL_URL, timeout=timeout)
            with response:
                payload = json.loads(response.read().decode("utf-8-sig"))
            if not isinstance(payload, list):
                raise ValueError("TWSE latest payload is not a list")
            result: dict[str, dict[str, Any]] = {}
            for row in payload:
                if not isinstance(row, Mapping):
                    continue
                parsed = _parse_row(row)
                if parsed is not None:
                    result[parsed["code"]] = parsed
            if not result:
                raise ValueError("TWSE latest payload has no valid rows")
            return result
        except Exception as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


__all__ = ["TWSE_STOCK_DAY_ALL_URL", "fetch_twse_latest_rows", "twse_code"]
