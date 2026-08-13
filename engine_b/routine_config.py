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


def us_edgar_candidates(tickers: Iterable[str]) -> frozenset[str]:
    """從 tracked universe 篩出「SEC EDGAR 可能有申報」的 ticker。

    EDGAR 只有美國註冊人；外國發行人（IQE.L、SIVE.ST、2330.TW）放進 watch 只會每天
    產生一筆找不到 CIK 的 fetch_failed。兩個確定性排除訊號：

    1. 交易所後綴（含 `.`）——Yahoo／provider 對非美國掛牌一律加後綴。
    2. registry 的 `market_currency` 非 USD。

    刻意不用 `execution_venue`：registry 中 AVGO／NVDA／TSLA／CCXI 等美股該欄皆為
    None，拿它當判準會把真正的美股全部濾掉。

    已知限制：美股本身帶 `.` 的（如 BRK.B）會被誤排除。目前 universe 沒有這種標的；
    真的需要時走 `extra_tickers` 手動補，而不是放寬這條規則。
    """
    from identity.registry import get_registry

    registry = get_registry()
    out: set[str] = set()
    for raw in tickers:
        ticker = str(raw or "").strip().upper()
        if not ticker or "." in ticker:
            continue
        company_id = registry.company_id_for_ticker(ticker)
        company = registry.company(company_id) if company_id else None
        currency = str(getattr(company, "market_currency", None) or "").upper()
        if currency and currency != "USD":
            continue
        out.add(ticker)
    return frozenset(out)


def edgar_watch_tickers(
    watch: Mapping[str, Any],
    *,
    tracked: frozenset[str] = frozenset(),
) -> list[str]:
    """EDGAR watch 的實際監看清單。

    `derive_from_tracked` 開啟時，把 tracked universe 中的美股**併入**手動清單，而不是
    取代它。理由是 fail-safe：derivation 的上游（thesis lifecycle、Decision store、
    themes.txt）任何一個暫時讀不到都會讓 tracked 縮小，若採取代語意就會靜默停止監看
    既有標的——而漏掉的 filing 不會有人發現。手動清單因此是**下限**，derivation 只補
    「已追蹤卻沒 watcher」這一側的漂移（CCXI 與 META 就是這樣漏掉的，見 §10.11）。
    """
    manual = {str(t).strip().upper() for t in (watch.get("tickers") or []) if str(t).strip()}
    if not watch.get("derive_from_tracked"):
        return sorted(manual)
    return sorted(manual | us_edgar_candidates(tracked))


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
