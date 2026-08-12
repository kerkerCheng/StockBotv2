"""Daily routine 的 deterministic budget 與 tracked-universe 設定。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "daily_routine.json"
DEFAULT_LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1":
        raise ValueError("daily routine config schema_version 必須是 1")
    pq1 = payload.get("pq1")
    if not isinstance(pq1, dict):
        raise ValueError("daily routine config 缺少 pq1")
    limit = pq1.get("drain_limit_per_run")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("pq1.drain_limit_per_run 必須是 1..20 的整數")
    sources = pq1.get("tracked_ticker_sources")
    if not isinstance(sources, dict):
        raise ValueError("pq1.tracked_ticker_sources 必須是 object")
    for key in ("thesis_lifecycle", "decision_cohorts", "theme_core_companies"):
        if not isinstance(sources.get(key), bool):
            raise ValueError(f"tracked_ticker_sources.{key} 必須是 boolean")
    return payload


def lifecycle_tickers(path: Path = DEFAULT_LIFECYCLE) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    tickers: set[str] = set()
    for entry in payload.values() if isinstance(payload, dict) else ():
        if not isinstance(entry, Mapping) or entry.get("status") == "retired":
            continue
        ticker = str(entry.get("ticker") or "").strip().upper()
        if ticker:
            tickers.add(ticker)
    return frozenset(tickers)


def theme_core_tickers() -> frozenset[str]:
    """`config/themes.txt` 每個主題的「核心公司」。

    加這個來源的理由：先前 tracked 只由 thesis lifecycle ＋ 未結案 cohort 導出，
    於是 COHR／LITE 這種「已列為 cpo 主題核心公司、EDGAR watch 也在抓它們的 filing」
    的標的，因為沒有 active cohort 而在排序上等於未追蹤——2026-08-12 實測，Lumentum
    當日的 tier-1 8-K 因此只拿到 6 分，被一則已兩度判定無用的總體評論（12 分）擠出
    當輪 pq1。harvest 花錢抓進來、排序又把它壓下去，是兩個 authority 互相矛盾。
    """
    try:
        from engine_b.themes import load_themes

        return frozenset(
            ticker.strip().upper()
            for theme in load_themes().values()
            for ticker in theme.tickers
            if ticker.strip()
        )
    except Exception:
        # themes.txt 缺失或格式錯誤時安全降級；其餘來源仍可提供 tracked universe。
        return frozenset()


def cohort_tickers(rows: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    terminal = {"promoted", "rejected", "expired"}
    return frozenset(
        ticker
        for row in rows
        if str(row.get("lifecycle_status") or "") not in terminal
        if (ticker := str(row.get("research_ticker") or "").strip().upper())
    )


def discover_tracked_tickers(
    config: Mapping[str, Any],
    *,
    lifecycle_path: Path = DEFAULT_LIFECYCLE,
) -> frozenset[str]:
    sources = config["pq1"]["tracked_ticker_sources"]
    tickers: set[str] = set()
    if sources["thesis_lifecycle"]:
        tickers.update(lifecycle_tickers(lifecycle_path))
    if sources["decision_cohorts"]:
        try:
            from decision_lab.bootstrap import open_default_store

            store = open_default_store()
            try:
                rows = store.list_operational_cohorts(
                    as_of=datetime.now(timezone.utc).isoformat()
                )
            finally:
                store.close()
            tickers.update(cohort_tickers(rows))
        except Exception:
            # Private store 尚未建立或暫時不可讀時，lifecycle 仍可提供安全降級。
            pass
    if sources["theme_core_companies"]:
        tickers.update(theme_core_tickers())
    return frozenset(tickers)
