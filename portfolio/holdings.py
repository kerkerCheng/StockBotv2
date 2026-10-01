"""持股身分解析：Sheet 列 → `co:*`（Phase 3 Step 3.6）。

**一份解析、兩個消費者、各自保留自己的語意**：

- `engine_b/cli.py::_held`（pq1 排序的「持股關聯」鍵）：**全部持股**，含 beta；Sheet 讀不到時 fail closed。
- 候選板的「已持有」（`alpha/providers/candidates.py`）：**alpha、股數 > 0**；beta 由 `risk/hard_caps.py` 的公開
  判別函式排除（同一條 alpha／beta 界線，不另抄一份——L16）。

解析順序（INV-1：ticker 不是 identity，**不猜**）：
1. Sheet 列自己帶的 `company_id`／`neo4j_id`（registry 查得到才算）——⚠ **今天的 Sheet 沒有這兩欄**：
   2026-10-01（Phase 4 Step 4.1d）之前 `fetchers/gsheets.py` 的 enrichment 表會替 FRA:2DG 注入 `neo4j_id`，
   所以這條看起來有人走；拿掉注入後只有「Sheet 自己加了 company_id 欄」才會走到（測試會模擬這種 Sheet）；
2. execution 別名反查（名冊 `execution_symbol` 派生的 `identity.execution.get_execution_aliases()`：
   `FRA:2DG` → `SIVE.ST`），再經 registry 嚴格比對——FRA:2DG 現在走這條；
3. Sheet 的 ticker 直接經 registry 嚴格比對（`company_id_for_ticker`）。
三條都不中＝**解析不到**，列進計數、不猜。`bucket=CASH` 的列是現金，不是「解析不到」。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from shared.buckets import CASH_BUCKET_LABELS

#: 解析來源的封閉字彙（寫進每一列，指得回是哪一條規則解出來的——L18）。
RESOLUTION_SOURCES: tuple[str, ...] = ("sheet_company_id", "execution_alias", "registry_ticker")

#: 使用者明確決定不做 alpha 研究的持股（Phase 4 Step 4.7b 接上讀者）：Sheet 代號在這裡的列不算「解析不到」，
#: 改列「使用者決定不研究」——那不是要人決定的 identity 問題，使用者已經決定過了。
HOLDINGS_COVERAGE_PATH = Path(__file__).resolve().parents[1] / "config" / "holdings_coverage.json"
HOLDINGS_COVERAGE_SCHEMA = "holdings-coverage-v1"


def load_ignored(path: Path | None = None) -> tuple[dict[str, dict[str, Any]], str | None]:
    """→ `({Sheet 代號（大寫）: 那一筆登記}, 讀取問題或 None)`。

    每筆要有 `sheet_ticker`、`reason`、`decided_at`（ISO 日期）。檔案讀不到、版本不對或任何一筆形狀不對 →
    **整份不採用**、回空表＋理由（fail safe：什麼都不藏，全部照列「解析不到」——寧可多問一次，不可把該問的藏起來）。
    """
    path = HOLDINGS_COVERAGE_PATH if path is None else path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"{path.name} 讀不到（{type(exc).__name__}）"
    if not isinstance(data, Mapping) or data.get("schema_version") != HOLDINGS_COVERAGE_SCHEMA:
        return {}, f"{path.name} 的 schema_version 不是 {HOLDINGS_COVERAGE_SCHEMA}"
    entries = data.get("ignored")
    if not isinstance(entries, list):
        return {}, f"{path.name} 的 ignored 不是清單"
    out: dict[str, dict[str, Any]] = {}
    for n, entry in enumerate(entries, 1):
        if not isinstance(entry, Mapping):
            return {}, f"{path.name} 第 {n} 筆不是物件"
        ticker = str(entry.get("sheet_ticker") or "").strip().upper()
        reason = str(entry.get("reason") or "").strip()
        try:
            decided = date.fromisoformat(str(entry.get("decided_at") or "")[:10])
        except ValueError:
            decided = None
        if not ticker or not reason or decided is None:
            return {}, f"{path.name} 第 {n} 筆缺 sheet_ticker／reason／decided_at（ISO 日期）"
        out[ticker] = {"sheet_ticker": ticker, "reason": reason, "decided_at": decided.isoformat()}
    return out, None


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


__all__ = ["HOLDINGS_COVERAGE_PATH", "HOLDINGS_COVERAGE_SCHEMA", "RESOLUTION_SOURCES", "is_cash_row", "load_ignored",
           "resolve_holding", "resolve_holdings"]
