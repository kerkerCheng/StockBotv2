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
    """快照的 `operating_margin` 與 `gross_margin` **期間不同**，而沒有任何欄位宣告這件事。

    ## 確認過的機制（不是「資料錯了」）

    yfinance 的 `grossMargins` 是年度／TTM，`operatingMargins` 是**最近一季**。
    兩次獨立實測：
    - 000660.KS（2026-09-11 的判斷檔已記）：快照 0.76328003 逐位等於 **Q2-2026 單季**營益率
      （60,542,608 ÷ 79,318,746），而 TTM 實為 68.0%——差 8.3pp。
    - SNDK（2026-09-12）：快照 0.78472 ≈ **Q4 FY2026 單季** GAAP 營益率 7,037 ÷ 8,965 = 0.78494，
      而全年是 61.19%（12,389 ÷ 20,248）——差 17.3pp。同一份快照的 gross_margin 0.71474
      則精確等於**全年**毛利 14,472 ÷ 20,248。

    **兩個相鄰欄位、兩種期間、零宣告**——L12 的形狀（一個表示承載兩種語意）。

    ## 為什麼不只在不等式成立時才警告

    `operating_margin > gross_margin` 只在「最近一季特別好」時才成立（全庫 73 份只有 3 份，
    且三家全是記憶體廠）。**其餘 70 份同樣有期間錯配，只是看不出來**——
    只在看得出來時才警告，等於只擋住最無害的那一批。所以這裡對**每一檔**都印。

    ⚠ 它不進橋（橋用 Engine C 的人工觀測），但**進 research packet 的 deterministic 區塊**，
    也就是 session 寫四軸判斷前會讀到的那一份。
    """
    gross, operating = snap.get("gross_margin"), snap.get("operating_margin")
    if operating is None:
        return
    impossible = gross is not None and operating > gross
    flag = "⚠⚠" if impossible else "⚠"
    print(f"   {flag} 快照的 operating_margin={operating:.4f} 是 **provider 的最近一季**，"
          f"而 gross_margin={gross if gross is None else format(gross, '.4f')} 是**年度／TTM**——"
          "兩欄期間不同且沒有欄位宣告。**寫判斷時營益率一律取法定文件自己算**，不要引用這一格。")
    if impossible:
        print("      （本檔連不等式都破了：營益率 > 毛利率，營業費用不會是負的——"
              "那只是期間錯配在這一檔剛好看得出來，不是另一種錯。）")


def _share_count_check(conn, ticker: str, snapshot_shares) -> None:
    """財報的稀釋加權平均股數與快照的流通在外股數差太多 ＝ 至少一邊是錯的。

    兩者本來就不同（加權平均 vs 期末、稀釋 vs 流通），但差距應該在個位數百分比；
    **差到 2 倍以上就不是口徑差異，是資料錯誤**。

    2026-09-12 實測 3105.TWO（穩懋）：財報 H1 2026 的基本 EPS 3.56 與歸屬母公司淨利
    1,510,391 仟元 → **424,267 仟股**，而快照的 shares_outstanding 是 **80,825,000**
    ——差 **5.25 倍**。packet 的 market_cap 直接由 price x shares_outstanding 算，
    所以那一格也跟著錯 5.25 倍（35.4B vs 實際約 185.6B 新台幣）。

    容忍區刻意開到 [0.5, 2.0]：全庫 40 檔可比的只有 AXTI 落在 0.6700（現金增資使稀釋
    加權平均低於期末流通股數，是**合理**差異）。先用 1.5 當上界時它會誤報一次——
    **會誤報的防呆本身就是過度工程（L16-4），所以把界線放到誤報為 0 的地方**；
    而 3105 的 5.25 倍離新界線仍有兩倍以上的餘裕，鑑別力沒有損失。
    """
    import json as _json
    rows = conn.execute(
        "SELECT observation_id, value, supersedes_id FROM manual_observations"
        " WHERE ticker = ? AND field_name = 'fiscal_year_results' ORDER BY recorded_at", (ticker,)).fetchall()
    if not rows or not snapshot_shares:
        return
    superseded = {r["supersedes_id"] for r in rows if r["supersedes_id"]}
    live = [r for r in rows if r["observation_id"] not in superseded]
    if not live:
        return
    try:
        payload = _json.loads(live[-1]["value"])
    except (TypeError, ValueError):
        return
    block = payload.get("gaap") or payload.get("non_gaap") or {}
    filed = block.get("diluted_shares")
    if not filed:
        return
    ratio = filed / snapshot_shares
    if 0.5 <= ratio <= 2.0:
        return
    print(f"   !! 財報稀釋股數 {filed:,.0f} vs 快照流通股數 {snapshot_shares:,.0f}（比值 {ratio:.2f}）"
          "——差到這個程度不是口徑差異，是**至少一邊錯了**。"
          "EPS 分母一律用財報的加權平均；packet 的 market_cap = price x shares_outstanding，"
          "所以快照錯的話**市值那一格也同樣錯**。")


def _live_base(conn, ticker: str):
    """該檔目前生效的 fiscal_year_results 觀測（已 supersede 的排掉）。"""
    import json as _json
    rows = conn.execute(
        "SELECT observation_id, value, supersedes_id FROM manual_observations"
        " WHERE ticker = ? AND field_name = 'fiscal_year_results' ORDER BY recorded_at", (ticker,)).fetchall()
    if not rows:
        return None
    superseded = {r["supersedes_id"] for r in rows if r["supersedes_id"]}
    live = [r for r in rows if r["observation_id"] not in superseded]
    if not live:
        return None
    try:
        return _json.loads(live[-1]["value"])
    except (TypeError, ValueError):
        return None


def _consensus_base_check(conn, ticker: str, rows) -> None:
    """共識的 `year_ago_actual` 應該等於我們自己記下來的基期實績——不等就代表口徑不同。

    這一條與 `_consensus_self_check` 互補：那一條比的是**共識自己的兩列**
    （0y 的估計 vs +1y 的 year_ago_actual），這一條比的是**共識 vs 一手財報**。

    ## ⚠ 這裡不是 authority，只是提前看得到

    營收那一側的判定權威是 **`alpha/fundamental/compare.py` 的 `unreconciled_base`**
    （2026-09-07 Coverage Pilot 補），它已經會在 analyst view 裡印出同一句話。
    本函式**不做新的判斷、也不得被當成第二個真相來源**（L16：分類要跟著資料走，
    不是每個消費端各造一份）——它只把那個判定搬到**開工前**：
    probe 的用途是「這一檔動手之前要先知道什麼」，而 `compare.py` 的版本要等到
    基期觀測、六格假設、估值都寫完並 materialize 之後才看得到。
    2026-09-13 實測 5016.T 就是這樣：先手動察覺 revenue_ttm 與共識基期差 2.06 倍，
    寫完整條 bridge 之後才看到 analyst view 印出同一件事。

    2026-09-13 實測 5016.T（ＪＸ金属）：provider 的 revenue `year_ago_actual` 是
    **461,843,000,000**，逐位等於決算短信「(参考) 個別業績」的売上高 461,843 百万円，
    而**連結**是 **884,638 百万円**——**兩條共識序列踩在不同的合併範圍上**
    （同一份快照的 EPS year_ago_actual 112.94 則是連結的基本 EPS，是對的）。
    provider 因此算出 revenue growth +130.58%，那是「連結預估 ÷ 個別實績」。

    EPS 那一側刻意只印**資訊**不報警：本輪已知有兩種合法的不相等——
    ①股票股利使 provider 依 IAS 33 追溯調整基期（3081.TWO：共識 4.20909 ＝ 財報稀釋 4.63 ÷ 1.10）；
    ②共識是 non-GAAP 而財報是 GAAP。把它做成警報會誤報，而會誤報的防呆本身就是過度工程（L16-4）。
    所以這裡只回答一個問題：**共識的基期對上的是基本、稀釋、還是都對不上？**

    ## 誤報率（2026-09-13 全庫實測，40 檔有基期觀測）

    - **revenue 報警 2 檔，兩檔都是真的**：5016.T（0.5221）與 6324.T（0.5614），
      **兩檔都是日股、都是 provider 把「(参考) 個別業績」當成基期**。
    - **TSM 不報警**：共識 TWD、基期觀測 USD，比值 31.37 只是匯率——加了幣別 guard。
    - **eps 側一律不報警**：實測 20 檔對不上，絕大多數是已知且合法的 GAAP vs non-GAAP。
      恆亮的警報等於零鑑別力（L14-4），所以那一側只印資訊。
    """
    base = _live_base(conn, ticker)
    if base is None or not rows:
        return
    zero = [r for r in rows if r["relative_label"] == "0y"]
    if not zero:
        return
    gaap = base.get("gaap") or base.get("non_gaap") or {}
    printed = False
    for row in zero:
        actual = row["year_ago_actual"]
        if not actual:
            continue
        if row["metric"] == "revenue":
            filed = base.get("revenue")
            if not filed:
                continue
            # 幣別不同就不可比——TSM 的共識是 TWD、基期觀測記的是 USD，比值 31.37 只是匯率。
            # 這種情況不報警（它不是資料錯誤），但要印出來，否則「沒警報」會被誤讀成「已核對」。
            cons_ccy, base_ccy = row["currency"], base.get("currency")
            if cons_ccy and base_ccy and cons_ccy != base_ccy:
                printed = True
                print(f"   ·  共識 revenue 的幣別是 {cons_ccy}、基期觀測是 {base_ccy}——"
                      "**本檢查跳過**（差異是匯率不是口徑）。要核對得先用同一條 FX 路徑換算。")
                continue
            ratio = actual / filed
            if 0.97 <= ratio <= 1.03:
                continue
            printed = True
            print(f"   !! 共識的 revenue year_ago_actual {actual:,.0f} vs 基期觀測的 {filed:,.0f}"
                  f"（比值 {ratio:.4f}）——**營收沒有合法的口徑差異**，"
                  "所以這不是 GAAP／non-GAAP，而是**合併範圍或年度對錯了**。"
                  "⚠ 不要用 provider 的 growth 欄位（它是「估計 ÷ 這個錯的基期」）。")
        elif row["metric"] == "eps":
            b, d = gaap.get("basic_eps"), gaap.get("diluted_eps")
            cands = [(lbl, v) for lbl, v in (("基本", b), ("稀釋", d)) if v]
            if not cands:
                continue
            best = min(cands, key=lambda kv: abs(actual / kv[1] - 1))
            gap = actual / best[1] - 1
            printed = True
            if abs(gap) <= 0.01:
                print(f"   ·  共識的 eps year_ago_actual {actual} 對上基期的**{best[0]}**每股盈餘 {best[1]}"
                      f"（差 {gap:+.2%}）——口徑已識別，後續比較用這一邊。")
            else:
                # 刻意**不報警**：全庫實測 20 檔落在這一支，而其中絕大多數是已知且合法的
                # GAAP vs non-GAAP（TSLA 1.66 vs 1.08、ORCL、GXO、MSFT…）。
                # 把它做成 `!!` 會讓警報恆亮，那就是 L14-4 的「恆亮＝零鑑別力」。
                print(f"   ·  共識的 eps year_ago_actual {actual} 與基期的基本 {b}／稀釋 {d} 都不一致"
                      f"（最接近的是{best[0]}，差 {gap:+.2%}）——**這一格是要你去識別口徑，不是錯誤**。"
                      "三個候選：①股票股利使 provider 依 IAS 33 追溯調整基期（除以配股倍數試試）；"
                      "②共識是 non-GAAP 而基期記的是 GAAP；③合併範圍不同。"
                      "**在釐清之前，內部 EPS 與共識的差距不可讀成觀點差距。**")
    if not printed:
        return


def probe(ticker: str) -> None:
    art = ARTIFACTS / f"{ticker}.json"
    if art.exists():
        payload = json.loads(art.read_text(encoding="utf-8"))
        readiness = payload.get("readiness") or {}
        print(f"# {ticker} readiness={readiness.get('state')}")
        for blocker in readiness.get("blocker_details") or []:
            # reason／absence_kind 都可能是 null——「沒給理由」本身要看得見，不能讓 probe 掛掉（L12：缺席不得與 0 同形）。
            kind = blocker.get("absence_kind") or "«absence_kind 為 null»"
            reason = blocker.get("reason") or "«reason 為 null——產生缺席的那段程式沒宣告理由»"
            print(f"  - {str(blocker.get('panel')):<12} {kind:<22} {reason[:120]}")
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
    _consensus_base_check(conn, ticker, rows)

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

    _share_count_check(conn, ticker, (snap.get("shares_outstanding") if row is not None else None))

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
