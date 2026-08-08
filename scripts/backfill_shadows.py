"""把遺失的 Shadow 錨點以歷史收盤補回。

Shadow 是「訊號進來那一刻的價格錨點」，它回答的是**資訊價值**——從我們知道
這件事開始，股價走了多少。這跟 paper（有 weight 的模擬部位，量的是 sizing／
timing 的決策品質）是兩件事：訊號可以是對的而系統把它 size 成 0，只有 shadow
記得住「我們看到了但沒動作」。

2026-08-08 實測 9 個 cohort 有 7 個沒有錨點，成因至少四種（registry entry 當時
缺 market_currency、as_of 語意造成 timestamp_future、報價單位未正規化、真正的
抓取失敗），全部與 sandbox 無關。因為 shadow 只是某個已知時刻的最後一個完整
交易日收盤價——**可重建的事實**，不是必須 point-in-time 凍結的真相——所以正解
是回填，不是重試（LITE／META 重試一百次都會失敗，缺的是 config 那一列）。

預設 dry-run；要真的寫入必須明確加 ``--apply``。已是 ``observed`` 的錨點永不覆寫。

    python scripts/backfill_shadows.py
    python scripts/backfill_shadows.py --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from decision_lab.cli import open_default_store  # noqa: E402
from engine_c.market_data import get_historical_tradeability_snapshot  # noqa: E402
from identity.registry import get_registry  # noqa: E402


def _signal_observed_at(store, cohort_id: str) -> str | None:
    """錨點時刻＝該 cohort 的 signal inception，不是今天。"""

    row = store._conn.execute(
        """
        SELECT observed_at FROM decision_events
        WHERE cohort_id = ? AND event_type IN ('qualified_signal', 'shadow_inception')
        ORDER BY observed_at LIMIT 1
        """,
        (cohort_id,),
    ).fetchone()
    return str(row["observed_at"]) if row else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill missing Shadow anchors")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="實際寫入；未指定時只列出將要回填的內容。",
    )
    args = parser.parse_args(argv)

    store = open_default_store()
    registry = get_registry()
    now = datetime.now(timezone.utc).isoformat()
    planned = 0
    skipped: list[str] = []
    try:
        for cohort in store.list_operational_cohorts(as_of=now):
            cohort_id = str(cohort["cohort_id"])
            label = str(cohort.get("company_id") or cohort_id[:14])
            try:
                shadow = store.get_shadow(cohort_id)
            except KeyError:
                skipped.append(f"{label}: 沒有 shadow 列")
                continue
            if shadow.status == "observed":
                continue

            company_id = cohort.get("company_id")
            if not company_id:
                skipped.append(f"{label}: identity 未解析，無法定位標的")
                continue
            company = registry.company(str(company_id))
            ticker = getattr(company, "research_ticker", None) if company else None
            quote_unit = getattr(company, "market_quote_unit", None) if company else None
            currency = quote_unit or (
                getattr(company, "market_currency", None) if company else None
            )
            if not ticker or not currency:
                # 正是 LITE／META 當初壞掉的原因；現在 registry 補齊了就能回填。
                skipped.append(f"{label}: registry 缺 research_ticker／market_currency")
                continue

            observed_at = _signal_observed_at(store, cohort_id)
            if not observed_at:
                skipped.append(f"{label}: 找不到 signal inception 時刻")
                continue

            snapshot = get_historical_tradeability_snapshot(
                str(ticker), str(currency), before=observed_at
            )
            if snapshot.get("status") != "observed":
                skipped.append(
                    f"{label}: 重建失敗 {snapshot.get('status')} {snapshot.get('blockers')}"
                )
                continue

            print(
                f"{label:30} {ticker:8} 錨點 {str(snapshot['as_of'])[:10]} "
                f"= {snapshot['price']:.4f} {snapshot['currency']}"
                f"  (原 status={shadow.status})"
            )
            planned += 1
            if args.apply:
                store.backfill_shadow(
                    cohort_id,
                    snapshot,
                    inception_at=observed_at,
                    backfilled_at=now,
                    reason="shadow inception 當時行情不可用；以觀測時刻前最後一個完整交易日收盤重建",
                )
    finally:
        store.close()

    for note in skipped:
        print(f"  跳過 — {note}")
    verb = "已回填" if args.apply else "可回填（dry-run，加 --apply 才寫入）"
    print(f"\n{verb}：{planned} 筆；跳過 {len(skipped)} 筆")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
