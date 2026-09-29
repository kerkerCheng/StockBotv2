"""持股身分解析：Sheet 列 → `co:*`（Phase 3 Step 3.6）。

**一份解析、兩個消費者、各自保留自己的語意**：

- `engine_b/cli.py::_held`（pq1 排序的「持股關聯」鍵）：**全部持股**，含 beta；Sheet 讀不到時 fail closed。
- 候選板的「已持有」（`alpha/providers/candidates.py`）：**alpha、股數 > 0**；beta 由 `risk/hard_caps.py` 的公開
  判別函式排除（同一條 alpha／beta 界線，不另抄一份——L16）。

解析順序（INV-1：ticker 不是 identity，**不猜**）：
1. Sheet 列自己帶的 `company_id`／`neo4j_id`（registry 查得到才算）；
2. execution 別名反查（`identity/execution.py`：`FRA:2DG` → `SIVE.ST`），再經 registry 嚴格比對；
3. Sheet 的 ticker 直接經 registry 嚴格比對（`company_id_for_ticker`）。
三條都不中＝**解析不到**，列進計數、不猜。`bucket=CASH` 的列是現金，不是「解析不到」。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from shared.buckets import CASH_BUCKET_LABELS

#: 解析來源的封閉字彙（寫進每一列，指得回是哪一條規則解出來的——L18）。
RESOLUTION_SOURCES: tuple[str, ...] = ("sheet_company_id", "execution_alias", "registry_ticker")


def _registry(registry: Any) -> Any:
    if registry is not None:
        return registry
    from identity.registry import get_registry

    return get_registry()


def _reverse_execution_aliases() -> dict[str, str]:
    from identity.execution import get_execution_aliases

    return {str(symbol).upper(): str(research).upper() for research, symbol in get_execution_aliases().items()}


def is_cash_row(row: Mapping[str, Any]) -> bool:
    return str(row.get("bucket") or "").strip().lower() in CASH_BUCKET_LABELS


def _shares(row: Mapping[str, Any]) -> float | None:
    try:
        return float(row.get("shares"))
    except (TypeError, ValueError):
        return None


def resolve_holding(row: Mapping[str, Any], *, registry: Any = None,
                    reverse_aliases: Mapping[str, str] | None = None) -> dict[str, Any]:
    """一列 Sheet → `{ticker, company_id, research_ticker, source, shares, bucket, cash}`；解析不到 `company_id=None`。"""
    reg = _registry(registry)
    aliases = _reverse_execution_aliases() if reverse_aliases is None else reverse_aliases
    ticker = str(row.get("ticker") or "").strip().upper()
    out: dict[str, Any] = {"ticker": ticker, "company_id": None, "research_ticker": None, "source": None,
                           "shares": _shares(row), "bucket": row.get("bucket"), "cash": is_cash_row(row)}
    declared = row.get("company_id") or row.get("neo4j_id")
    if declared and reg.has_company(str(declared)):
        out.update(company_id=str(declared), source="sheet_company_id")
    elif ticker in aliases and reg.company_id_for_ticker(aliases[ticker]):
        out.update(company_id=reg.company_id_for_ticker(aliases[ticker]), source="execution_alias")
    elif ticker and reg.company_id_for_ticker(ticker):
        out.update(company_id=reg.company_id_for_ticker(ticker), source="registry_ticker")
    if out["company_id"]:
        out["research_ticker"] = reg.research_ticker(out["company_id"])
    return out


def resolve_holdings(rows: Sequence[Mapping[str, Any]], *, registry: Any = None) -> dict[str, Any]:
    """整張 Sheet → `{rows, unresolved, cash_rows}`。`unresolved` 不含現金列（現金不是「解析不到」）。"""
    reg = _registry(registry)
    aliases = _reverse_execution_aliases()
    resolved = [resolve_holding(row, registry=reg, reverse_aliases=aliases) for row in rows
                if str(row.get("ticker") or "").strip() and str(row.get("ticker")).strip() != "—"]
    unresolved = sorted({r["ticker"] for r in resolved if not r["company_id"] and not r["cash"]})
    return {"rows": resolved, "unresolved": unresolved, "cash_rows": sum(1 for r in resolved if r["cash"])}


__all__ = ["RESOLUTION_SOURCES", "is_cash_row", "resolve_holding", "resolve_holdings"]
