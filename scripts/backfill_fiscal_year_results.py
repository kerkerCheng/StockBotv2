"""批次把段 5 backlog 的基期實績從 SEC XBRL 補進 Engine C（P7-a，2026-09-10）。

## 它做什麼

對每一個「還沒到終局、且 `headline` 卡在缺基期實績」的美股標的，用
`fetchers/edgar_xbrl.py` 取 `revenue` 與 `gaap.operating_income`，寫成一筆
`fiscal_year_results` mechanical 觀測。

**這支不寫任何判讀。** 營運假設、倍數、horizon、判斷檔全部留給 session（那是段 5 的
研究部分）。它只拿掉每檔最花 token 的那一格。

## 三條安全設計

1. **預設 dry-run。** 寫入 append-only authority 要顯式 `--write`——寫錯了只能用
   correction record supersede，兩筆都留在 ledger 裡（L10）。
2. **既有觀測預設不覆寫。** 已經有 `fiscal_year_results` 的檔直接跳過（`--force` 才重寫）。
   人工寫的那幾筆（LITE 有完整損益表、分部與逐字 segment_note）**比本支豐富得多**，
   蓋掉它們是淨損失。
3. **非美股不碰。** 沒有 CIK 就記 `no_cik` 並列進報告——TWSE／EDINET／DART／KIND 各有各的
   格式，硬套會在 source_ref 上造假。

## 報告是產出的一部分，不是附帶

每一檔都必須落到一個具名結局（`written`／`skipped_existing`／`no_cik`／`unavailable`／
`refused`），且 `refused` 一定附 XBRL 給的理由原文。**「查不到了」不是合法 lifecycle**
（INV-3）——所以沒有靜默跳過這個選項。

用法：
    python scripts/backfill_fiscal_year_results.py                    # dry-run 全 backlog
    python scripts/backfill_fiscal_year_results.py --write
    python scripts/backfill_fiscal_year_results.py --tickers MP AAOI --write
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIELD = "fiscal_year_results"
#: 只補這一種缺席：`headline` 因上游缺基期實績而倒。其他 absence_kind 不是本支的事。
TARGET_PANEL = "headline"


def _backlog_tickers() -> list[str]:
    """段 5 未到終局、且 headline 卡在上游缺料的檔。**清單來自 closure，不自己另列一份**（L16）。"""
    from alpha.closure import rank_backlog
    from alpha.providers.closure import collect_backlog

    rows, _notes = collect_backlog()
    return [r.ticker for r in rank_backlog(rows)
            if r.absence_kinds.get(TARGET_PANEL) == "upstream_unavailable"]


def _existing(conn, ticker: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM manual_observations WHERE ticker = ? AND field_name = ? LIMIT 1",
        (ticker, FIELD)).fetchone()
    return row is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tickers", nargs="*", help="指定標的；省略則取段 5 backlog")
    parser.add_argument("--write", action="store_true", help="真的寫入（預設只 dry-run）")
    parser.add_argument("--force", action="store_true", help="已有觀測也重寫（預設跳過）")
    parser.add_argument("--limit", type=int, help="最多處理幾檔")
    parser.add_argument("--sleep", type=float, default=0.4, help="每次 SEC 呼叫之間的間隔秒數")
    parser.add_argument("--author", default="xbrl_backfill")
    args = parser.parse_args()

    from engine_c.db import get_conn
    from engine_c.manual_observations import (
        append_manual_observation,
        ensure_manual_observation_schema,
    )
    from fetchers.edgar import get_cik
    from fetchers.edgar_xbrl import (
        XbrlUnavailable,
        build_fiscal_year_results,
        fetch_companyfacts,
    )

    tickers = args.tickers or _backlog_tickers()
    if args.limit:
        tickers = tickers[: args.limit]
    if not tickers:
        print("段 5 backlog 沒有 headline=upstream_unavailable 的檔——沒有工作。")
        return 0

    conn = get_conn()
    ensure_manual_observation_schema(conn)

    outcomes: Counter[str] = Counter()
    refused: list[tuple[str, str]] = []
    written: list[tuple[str, str, float]] = []

    mode = "寫入" if args.write else "dry-run"
    print(f"# 基期實績 XBRL 補值（{mode}）：{len(tickers)} 檔\n")
    for ticker in tickers:
        if not args.force and _existing(conn, ticker):
            outcomes["skipped_existing"] += 1
            print(f"- {ticker}：已有 {FIELD} 觀測，跳過（--force 才覆寫）")
            continue
        try:
            cik = get_cik(ticker)
        except Exception:  # noqa: BLE001
            cik = None
        if not cik:
            outcomes["no_cik"] += 1
            print(f"- {ticker}：無 CIK（非美股或未在 SEC 註冊）——本支不處理")
            continue
        time.sleep(args.sleep)
        try:
            facts = fetch_companyfacts(cik)
        except XbrlUnavailable as exc:
            outcomes["unavailable"] += 1
            print(f"- {ticker}：✗ {exc}")
            continue
        payload, source_ref, reason = build_fiscal_year_results(ticker, facts)
        if payload is None:
            outcomes["refused"] += 1
            refused.append((ticker, reason or "未知"))
            print(f"- {ticker}：✗ 拒寫——{reason}")
            continue
        as_of = payload["fiscal_year_end"]
        if not args.write:
            outcomes["would_write"] += 1
            print(f"- {ticker}：（dry-run）FY{as_of} 營收 {payload['revenue']:,.0f} "
                  f"{payload['currency']}／營業利益 {payload['gaap']['operating_income']:,.0f}"
                  f"（filed {payload['source_filed_at']}）")
            continue
        try:
            observation_id = append_manual_observation(
                conn, ticker=ticker, field_name=FIELD, value=json.dumps(payload, ensure_ascii=False),
                source_ref=source_ref, as_of=as_of, author=args.author)
        except ValueError as exc:
            outcomes["refused"] += 1
            refused.append((ticker, f"寫入端拒絕：{exc}"))
            print(f"- {ticker}：✗ 寫入端拒絕——{exc}")
            continue
        outcomes["written"] += 1
        written.append((ticker, as_of, float(payload["revenue"])))
        print(f"- {ticker}：✓ {observation_id} FY{as_of}")

    print(f"\n## 結局分佈（每一檔都有具名結局，沒有靜默跳過）")
    for key in ("written", "would_write", "skipped_existing", "no_cik", "unavailable", "refused"):
        if outcomes[key]:
            print(f"- {key}：{outcomes[key]}")
    if refused:
        print("\n## 拒寫明細（留 null 並列出來，不猜、不補 0）")
        for ticker, reason in refused:
            print(f"- {ticker}：{reason}")
    print("\n下一步：`python -m webapp materialize <TICKER>` 讓 headline 那一格重新計算；"
          "\n        `python -m webapp closure-gate` 看段 5 還剩幾檔。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
