# -*- coding: utf-8 -*-
"""段 5 每檔閉環的取料探針：一次印出一檔要開工前需要知道的全部現況。

**只讀，不寫任何 authority。** 它不是新的判斷來源——每一格都標明出處，
讓 session 不必為了「現在狀態是什麼」而分四五次查詢（research-drain Step 0
要求每個項目開始前重讀狀態，而分散查詢正是那一步最容易被跳過的原因）。

用法：python scripts/closure_probe.py ANET [--xbrl]
`--xbrl` 另外抓 SEC companyfacts 的年度／季度損益數（只對有 CIK 的美股有用）。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# 這支腳本會被直接執行（python scripts/closure_probe.py），此時 sys.path[0] 是 scripts/，
# repo root 不在路徑上——fetchers 匯入會 ModuleNotFoundError。加一行讓它與 `python -m` 等價。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB = Path("library/private/engine_c/stockbot-engine-c-private-v1-458db5270ee2.db")
ARTIFACTS = Path("library/private/app/analyst_view")


def _conn() -> sqlite3.Connection:
    # **機械上唯讀**，不是口頭承諾：走 URI 的 mode=ro，任何 INSERT/UPDATE 都會直接
    # raise sqlite3.OperationalError。這支腳本讀的是 Engine C 的 append-only ledger
    # （L10：沒有第二份來源、Git 救不回），所以「它只讀」這件事要由連線本身保證。
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _consensus_self_check(rows) -> None:
    """`0y 的估計` 應該等於 `+1y 的 year_ago_actual`——它們講的是同一個會計年度。

    對不上就代表**這兩列不是同一串數字**。2026-09-12 實測 CDNS：0y EPS 4.80568（13 位分析師）
    是 GAAP、+1y EPS 9.54363（25 位）是 non-GAAP，兩列相除會得到「一年成長 +98.6%」——
    **完全是口徑切換的假象，而沒有任何欄位會報錯**。全庫 144 組 0y 列裡有 3 組是這個形狀
    （CDNS 的 eps 69.4%、6680.HK 的 eps 20.5% 與 revenue 5.0%）。

    ⚠ 這裡只報告、不判定口徑：要知道是 GAAP 還是 non-GAAP，得拿 `year_ago_actual` 去對
    一手財報（`alpha.fundamental.compare.verify_consensus_basis` 做的就是那件事）。
    """
    by = {(r["metric"], r["relative_label"]): r for r in rows}
    for metric in sorted({r["metric"] for r in rows}):
        cur, nxt = by.get((metric, "0y")), by.get((metric, "+1y"))
        if not cur or not nxt or cur["estimate_avg"] in (None, 0) or nxt["year_ago_actual"] is None:
            continue
        drift = abs(float(nxt["year_ago_actual"]) / float(cur["estimate_avg"]) - 1)
        if drift > 0.02:
            print(f"   ⚠⚠ {metric}：0y 估計 {cur['estimate_avg']}（{cur['analyst_count']} 位）"
                  f" vs +1y 的 year_ago_actual {nxt['year_ago_actual']}（{nxt['analyst_count']} 位）"
                  f" 差 {drift * 100:.1f}% —— **這兩列很可能不是同一串數字（口徑或樣本不同）**。"
                  f"不得相除當成成長率；先拿 year_ago_actual 去對一手財報確認口徑。")


def _snapshot_self_check(snap) -> None:
    """營益率不可能大於毛利率——營業費用不會是負的。

    2026-09-12 實測：73 份行情快照有 **3 份**違反（MU 80.37% vs 72.57%、SNDK 78.47% vs 71.47%、
    000660.KS 76.33% vs 76.27%），**三家全是記憶體廠**。以 SNDK 對一手 10-K 核過：
    毛利率 71.47% 正確（14,472 ÷ 20,248），但營益率應為 **61.19%**（12,389 ÷ 20,248），
    provider 給的 78.47% 錯了 17 個百分點。

    ⚠ 它不進橋（橋用的是 Engine C 的人工觀測），但它**進 research packet 的 deterministic 區塊**，
    也就是 session 在寫四軸判斷前會讀到的那一份。判斷裡若引用了它，錯誤就落進 append-only 的判斷檔。
    """
    gross, operating = snap.get("gross_margin"), snap.get("operating_margin")
    if gross is None or operating is None or operating <= gross:
        return
    print(f"   ⚠⚠ 營益率 {operating:.2%} **大於**毛利率 {gross:.2%}——營業費用不會是負的，"
          "provider 這兩格至少有一格是錯的。寫判斷前先用 10-K／10-Q 的營業利益 ÷ 營收自己算一次；"
          "**不要引用快照的 operating_margin**。")


def probe(ticker: str) -> None:
    art = ARTIFACTS / f"{ticker}.json"
    if art.exists():
        payload = json.loads(art.read_text(encoding="utf-8"))
        readiness = payload.get("readiness") or {}
        print(f"# {ticker} readiness={readiness.get('state')}")
        for blocker in readiness.get("blocker_details") or []:
            print(f"  - {blocker['panel']:<12} {blocker['absence_kind']:<22} {blocker['reason'][:120]}")
    else:
        print(f"# {ticker} 沒有 analyst view artifact")

    conn = _conn()
    print("\n## 共識（最新 snapshot）")
    rows = conn.execute(
        "SELECT relative_label, metric, fiscal_period_end, fiscal_label, estimate_avg,"
        " analyst_count, year_ago_actual, growth, currency FROM consensus_estimates"
        " WHERE ticker = ? AND snapshot_date = (SELECT MAX(snapshot_date) FROM consensus_estimates WHERE ticker = ?)"
        " ORDER BY fiscal_period_end, metric", (ticker, ticker)).fetchall()
    for row in rows:
        print("  ", dict(row))
    if not rows:
        print("   （無共識——沒有同期 EPS 共識的檔走不了本益比法）")
    _consensus_self_check(rows)

    print("\n## 行情快照")
    row = conn.execute(
        "SELECT * FROM financial_snapshots WHERE ticker = ? ORDER BY rowid DESC LIMIT 1", (ticker,)).fetchone()
    if row is None:
        print("   （無）")
    else:
        snap = dict(row)
        keep = ("bar_date", "price", "price_kind", "currency", "market_cap", "shares_outstanding",
                "gross_margin", "operating_margin", "revenue_ttm", "trailing_pe", "forward_pe")
        print("  ", {k: snap[k] for k in keep if k in snap})
        _snapshot_self_check(snap)

    print("\n## Engine C 人工觀測")
    for row in conn.execute(
            "SELECT observation_id, field_name, as_of, author, supersedes_id, length(value) AS n"
            " FROM manual_observations WHERE ticker = ? ORDER BY recorded_at", (ticker,)):
        print("  ", dict(row))

    print("\n## 既有假設 ledger")
    for kind, folder in (("operating", "assumptions"), ("valuation", "valuation"), ("horizon", "horizon")):
        path = Path("library/private/alpha") / folder / f"{ticker}.jsonl"
        if not path.exists():
            print(f"   {kind}: —")
            continue
        live = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"   {kind}: {len(live)} 筆；最新 driver/parameter："
              f"{sorted({r.get('driver') or r.get('parameter') or 'horizon' for r in live})}")
    judgment = Path("library/private/alpha/judgments") / f"{ticker}.json"
    print(f"   判斷檔: {'有' if judgment.exists() else '—'}")


def probe_xbrl(ticker: str) -> None:
    from fetchers.edgar import get_cik
    from fetchers.edgar_xbrl import companyfacts_lag, fetch_companyfacts

    cik = get_cik(ticker)
    if not cik:
        print(f"\n## XBRL：{ticker} 在 SEC ticker 對照表查不到 CIK（非美股或未登記）")
        return
    facts = fetch_companyfacts(cik)
    snapshot, newest, warning = companyfacts_lag(cik, facts)
    if warning:
        print(f"\n⚠⚠ {warning}")
        print("   → 少掉的那幾期要改用 10-Q／8-K EX-99.1 逐字取，不要以為 XBRL 就是全部。")
    else:
        print(f"\n## companyfacts 新鮮度：快照 {snapshot}／EDGAR 最新定期報告 {newest}——一致")
    us = (facts.get("facts") or {}).get("us-gaap") or {}
    tags = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "GrossProfit",
            "OperatingIncomeLoss", "NonoperatingIncomeExpense",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeTaxExpenseBenefit", "NetIncomeLoss", "ProfitLoss",
            "NetIncomeLossAttributableToNoncontrollingInterest",
            "WeightedAverageNumberOfDilutedSharesOutstanding", "EarningsPerShareDiluted")
    print(f"\n## XBRL companyfacts（CIK {cik}）——只列 2025-01 之後結束的期間")
    for tag in tags:
        entry = us.get(tag)
        if not entry:
            print(f"   ## {tag}: 無此 tag")
            continue
        seen = set()
        for unit, items in entry["units"].items():
            for item in items:
                start, end = item.get("start"), item.get("end")
                if not start or not end or end < "2025-01-01":
                    continue
                seen.add((start, end, item["val"], unit, item.get("accn"), item.get("form"), item.get("fp")))
        print(f"   ## {tag}")
        for row in sorted(seen):
            print("      ", row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument("--xbrl", action="store_true")
    args = parser.parse_args()
    probe(args.ticker.upper())
    if args.xbrl:
        probe_xbrl(args.ticker.upper())
    return 0


if __name__ == "__main__":
    sys.exit(main())
