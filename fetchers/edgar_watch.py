"""EDGAR 申報自動偵測——registry 內美股公司的新 filing 自己變成 pending lead。

ROADMAP 交付（2026-09-02 使用者核准）：此前 EDGAR 抓取只在 pq1 被動觸發，新
10-Q／8-K 要等 harvest 剛好撞到或人想起來（Lumentum OCS backlog $400M 的 8-K
是 2 月出的，我們 9 月才因工單翻到）。本模組對 registry 內有純美股 ticker 的
公司輪詢 EDGAR submissions，最近 N 天內的目標 form 註冊成 pending lead。

去重：lead_id 由 filing index URL 決定（`engine_b.leads.register` 既有機制），
同一 accession 重跑天然 no-op。

⚠ 目前定位是**互動／loop 工具**（research-drain 閉包工作的一部分）。要掛進
daily unattended 排程屬 executable surface 變更，必須另走 sandbox impact review
（`.codex/rules` 的「SEC EDGAR pq1 fetch」rule 是否涵蓋本入口需逐字比對）——
不在本次交付範圍。
"""
from __future__ import annotations

import argparse
import sys

from fetchers.edgar import FORM_TIER, get_cik, get_filings, rate_sleep

DEFAULT_FORMS = ("10-K", "10-Q", "8-K", "20-F", "6-K")
_FOREIGN_SUFFIXES = (
    ".T", ".TW", ".TWO", ".AX", ".ST", ".DE", ".PA", ".HK", ".SS", ".SZ", ".F",
)


def registry_us_tickers() -> dict[str, str]:
    """company_id → research_ticker，只取純美股形式（無交易所後綴）。"""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "config" / "company_identity.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for c in data.get("companies") or []:
        ticker = c.get("research_ticker")
        if not ticker:
            continue
        if any(str(ticker).endswith(sfx) for sfx in _FOREIGN_SUFFIXES):
            continue
        out[str(c["company_id"])] = str(ticker)
    return out


def filing_index_url(cik: str, accession: str) -> str:
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/"


def watch(
    *,
    days: int,
    forms: tuple[str, ...],
    dry_run: bool,
) -> dict[str, int]:
    from datetime import date, timedelta

    from engine_b import leads as leads_mod

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    tickers = registry_us_tickers()
    store = leads_mod.load()
    stats = {"companies": len(tickers), "filings_seen": 0, "new": 0, "existing": 0}
    for company_id, ticker in sorted(tickers.items()):
        cik = get_cik(ticker)
        if not cik:
            print(f"[edgar-watch] WARN: CIK not found for {ticker}", file=sys.stderr)
            continue
        filings = get_filings(cik, list(forms), n=8)
        rate_sleep()
        for f in filings:
            if str(f.get("filed_date") or "") < cutoff:
                continue
            stats["filings_seen"] += 1
            url = filing_index_url(f["cik"], f["accession"])
            title = (
                f"[edgar-watch] {ticker} {f['form_type']} filed {f['filed_date']}"
                f"（{company_id}，accession {f['accession']}，tier "
                f"{FORM_TIER.get(str(f['form_type']).upper(), 2)}）——新申報自動偵測，"
                "triage 判是否深挖"
            )
            existing = leads_mod.lead_id_for(url) in store["leads"]
            if existing:
                stats["existing"] += 1
                continue
            if dry_run:
                print(f"[edgar-watch] would register: {title}")
                stats["new"] += 1
                continue
            leads_mod.register(
                store,
                source=f"edgar-watch:{ticker}",
                url=url,
                title=title,
            )
            stats["new"] += 1
            print(f"[edgar-watch] registered: {ticker} {f['form_type']} {f['filed_date']}")
    if not dry_run and stats["new"]:
        leads_mod.save(store)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="registry 美股公司的新 EDGAR 申報自動註冊成 pending lead"
    )
    ap.add_argument("--days", type=int, default=8, help="回看天數，預設 8")
    ap.add_argument(
        "--forms", default=",".join(DEFAULT_FORMS),
        help=f"逗號分隔 form 類型，預設 {','.join(DEFAULT_FORMS)}",
    )
    ap.add_argument("--dry-run", action="store_true", help="只列出、不註冊")
    args = ap.parse_args(argv)
    stats = watch(
        days=args.days,
        forms=tuple(s.strip().upper() for s in args.forms.split(",") if s.strip()),
        dry_run=args.dry_run,
    )
    print(
        f"[edgar-watch] companies={stats['companies']} filings_seen={stats['filings_seen']} "
        f"new={stats['new']} existing={stats['existing']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
