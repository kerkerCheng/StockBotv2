"""需求錨序列的取數（個股頁 S3a，2026-10-08）：讀 `config/demand_anchor_series.json`、名冊與 Engine C `fundamental_history`，
交給 `alpha.demand_anchor` 的純函式組成序列。

時點（INV-6）：每一家 as-of T 每期取 `filed ≤ T` 的最新一列（`engine_c.history.fundamental_series`），另取每期最早的申報日
（`first_filed_by_period`）——可知日用最早的、值用最新的版本。成分在名冊裡找不到代號 → 整條缺席（INV-1：不猜代號）。
讀不到設定或庫 → `{"absence": …}`（呼叫端印這一輪沒讀到，不是「沒有成長」）。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from alpha.demand_anchor import assemble_series, validate_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "demand_anchor_series.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    return validate_config(json.loads((path or CONFIG_PATH).read_text(encoding="utf-8")))


def _ticker_for(company_id: str, registry: Any) -> str | None:
    company = registry.company(company_id)
    return getattr(company, "research_ticker", None) if company is not None else None


def build_series(conn: Any, key: str, config: Mapping[str, Any], *, as_of: date, registry: Any = None) -> dict[str, Any]:
    """一條錨序列 as-of T（組法見 `alpha.demand_anchor.assemble_series`）。"""
    from engine_c.history import first_filed_by_period, fundamental_series

    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    spec = (config.get("series") or {})[key]
    tickers: list[tuple[str, str]] = []
    for company_id in spec["components"]:
        ticker = _ticker_for(company_id, registry)
        if not ticker:
            return {"key": key, "label": spec.get("label") or key, "proxy": spec.get("proxy") or "",
                    "aggregation": spec["aggregation"], "metric": spec["metric"], "currency": spec.get("currency") or "USD",
                    "as_of": as_of.isoformat(), "components": [], "points": [], "gaps": [],
                    "absence": {"kind": "upstream_unavailable",
                                "reason": f"成分 {company_id} 在名冊裡沒有代號——這條序列組不起來（INV-1：不猜代號）"}}
        tickers.append((company_id, ticker))
    rows = {t: fundamental_series(conn, t, spec["metric"], as_of=as_of) for _cid, t in tickers}
    first = {t: first_filed_by_period(conn, t, spec["metric"], as_of=as_of) for _cid, t in tickers}
    out = assemble_series(key, spec, rows, first, as_of=as_of)
    ids = dict((t, cid) for cid, t in tickers)
    for component in out["components"]:
        component["company_id"] = ids.get(component["ticker"])
    return out


def anchor_context(conn: Any, *, as_of: date, config: Mapping[str, Any] | None = None,
                   registry: Any = None) -> dict[str, Any]:
    """一次 materialize 用的需求錨輸入：設定檔＋每條序列（as-of T）。讀不到設定 → `{"absence": …}`。"""
    try:
        cfg = dict(config) if config is not None else load_config()
    except (OSError, ValueError) as exc:
        return {"absence": {"kind": "upstream_unavailable", "reason": f"需求錨設定讀不到（{exc}）"}}
    series: dict[str, Any] = {}
    for key in cfg.get("series") or {}:
        try:
            series[key] = build_series(conn, key, cfg, as_of=as_of, registry=registry)
        except Exception as exc:  # noqa: BLE001 — 一條序列組不起來只讓那一條說讀不到
            series[key] = {"key": key, "label": (cfg["series"][key] or {}).get("label") or key, "points": [], "gaps": [],
                           "absence": {"kind": "upstream_unavailable", "reason": f"{type(exc).__name__}: {str(exc)[:160]}"}}
    return {"config": cfg, "series": series, "as_of": as_of.isoformat()}


__all__ = ["CONFIG_PATH", "anchor_context", "build_series", "load_config"]
