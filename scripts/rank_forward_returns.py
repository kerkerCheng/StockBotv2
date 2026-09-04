"""排序前段 vs 後段的等權報酬（Phase 6 驗收）。

把 `rank_bottlenecks` 在**歷史時點**的排序（走 as-of 投影，不偷看未來）接上收盤
序列，看前段的後續報酬有沒有比後段好。判準與限制寫在 `alpha/backtest.py`，
那裡是權威；這支只負責取資料。

⚠ **排序必須來自 as-of 投影。** 用今天的排序去看過去的報酬是最經典的 lookahead：
排在前面的之所以在前面，正是因為後來發生的事被寫進了圖裡。

用法：
    python scripts/rank_forward_returns.py                       # 預設 3 期、90 天
    python scripts/rank_forward_returns.py --epochs 2026-03-01 2026-05-01 --horizon 60
    python scripts/rank_forward_returns.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alpha.backtest import evaluate_epoch, summarise_epochs  # noqa: E402
from alpha.errors import PointInTimeUnsupported  # noqa: E402

#: 預設的觀察時點。刻意選在圖上證據夠密的區間；更早的時點 as-of 投影會拒絕，
#: 那是保險絲正常運作，不是錯誤。
DEFAULT_EPOCHS = ("2026-03-01", "2026-04-15", "2026-06-01")
DEFAULT_HORIZON_DAYS = 90


def _ranked_tickers(provider, registry, as_of: date) -> list[str]:
    """as-of 排序 → 去重後的 ticker 序列（保持排序，取每家公司最好的名次）。"""
    seen: set[str] = set()
    tickers: list[str] = []
    for row in provider.get_bottlenecks(as_of=as_of):
        company = str(row.company_id)
        if company in seen:
            continue
        seen.add(company)
        ticker = registry.research_ticker(company)
        if ticker:
            tickers.append(str(ticker))
    return tickers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epochs", nargs="+", default=list(DEFAULT_EPOCHS))
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON_DAYS,
                        help="持有天數（日曆日）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from alpha.providers.close_series import fetch_close_series
    from alpha.providers.graph_neo4j import open_default_provider
    from identity.registry import get_registry

    registry = get_registry()
    provider = open_default_provider()
    epochs = [date.fromisoformat(e) for e in args.epochs]
    horizon = timedelta(days=args.horizon)

    try:
        plans: list[tuple[date, date, list[str]]] = []
        refused: list[str] = []
        for as_of in epochs:
            try:
                plans.append((as_of, as_of + horizon,
                              _ranked_tickers(provider, registry, as_of)))
            except PointInTimeUnsupported as exc:
                # 保險絲響了是正確行為，但**必須現形**：靜默跳過會讓
                # 「這期沒資料」與「這期排序沒用」同形（L13）。
                refused.append(f"{as_of}：{exc}")
    finally:
        provider.driver.close()

    universe = sorted({t for _, _, tickers in plans for t in tickers})
    oldest = min((p[0] for p in plans), default=date.today())
    sessions = max((date.today() - oldest).days, 30) + args.horizon
    prices = fetch_close_series(universe, sessions=sessions)

    results = [
        evaluate_epoch(as_of=as_of, horizon_end=end, ranked=tickers, prices=prices)
        for as_of, end, tickers in plans
    ]
    summary = summarise_epochs(results)
    summary["refused_by_fuse"] = refused
    summary["universe"] = universe
    summary["price_series_available"] = sorted(prices)

    if args.json:
        print(json.dumps({
            "summary": summary,
            "epochs": [{
                "as_of": r.as_of.isoformat(), "horizon_end": r.horizon_end.isoformat(),
                "ranked": list(r.ranked), "top": list(r.top), "bottom": list(r.bottom),
                "top_return": r.top_return, "bottom_return": r.bottom_return,
                "spread": r.spread, "missing_price": list(r.missing_price),
                "contributions": [{"ticker": t, "return": v} for t, v in r.contributions],
                "skipped_reason": r.skipped_reason,
            } for r in results],
        }, ensure_ascii=False, indent=2))
        return 0

    print("排序前段 vs 後段·等權報酬（**研究判斷的檢核，不是回測勝率**）\n")
    for r in results:
        print(f"as_of {r.as_of} → {r.horizon_end}｜排序 {len(r.ranked)} 檔")
        if r.skipped_reason:
            print(f"   ⨯ 略過：{r.skipped_reason}")
        else:
            print(f"   前段 {list(r.top)}  {_pct(r.top_return)}")
            print(f"   後段 {list(r.bottom)}  {_pct(r.bottom_return)}")
            print(f"   價差 {_pct(r.spread)}")
            print("   逐檔 " + "  ".join(f"{t} {v:+.1%}" for t, v in r.contributions))
            dominant = r.dominant_name
            if dominant:
                print(f"   ⚠ 這期主要由 {dominant[0]} 決定"
                      f"（偏離本期均值 {dominant[1]:+.1%}）")
        if r.missing_price:
            print(f"   ⚠ 無價格而排除：{list(r.missing_price)}")
    for line in refused:
        print(f"\n⚠ as-of 保險絲拒絕了 {line[:160]}")
    print(f"\n可用期數 {summary['epochs_usable']}/{summary['epochs_requested']}"
          f"｜各期價差 {summary['spreads']}｜平均 {_pct(summary['mean_spread'])}"
          f"｜為正 {summary['positive_epochs']} 期")
    print(f"\n{summary['_interpretation']}")
    return 0


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2%}"


if __name__ == "__main__":
    raise SystemExit(main())
