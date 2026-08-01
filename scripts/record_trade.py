"""記錄一筆手動成交：append 不可變事件紀錄，並更新 Google Sheet 持股與現金。

設計約束（2026-08-01 使用者定案，來由見對話與 `docs/brainstorms/`）：

1. **Sheet 仍是持股唯一權威**，本腳本只改「從券商通知逐字可讀」的數字
   （股數、現金）與由它們算出的 `avg_cost`；不碰市值、不碰 NAV、不碰其他欄位。
2. **人工編輯與程式寫入必須共存。** 因此按欄名定位（使用者會調欄序）、
   按內容比對定位列、且寫入前重讀確認現值——不符即整批中止。
   永遠只寫指定儲存格，絕不寫整列或範圍。
3. **預設 dry-run。** 要實際寫入必須加 `--apply`，且會先印出完整 diff。
4. **事件紀錄與持股狀態分開。** `library/trades/trade_log.jsonl` 是 append-only
   事件流（發生了什麼），不是持股真相（現在有多少）——後者永遠只有 Sheet。

用法：
    python scripts/record_trade.py --symbol QQQ --side buy --shares 10 \\
        --price 687.79 --executed-at 2026-07-31T13:04:53-04:00 \\
        --broker IB --note "IB Trade notification ..." [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

TRADE_LOG = _ROOT / "library" / "trades" / "trade_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _number(value: str) -> float:
    """Sheet 的數字可能帶千分位或空白；空字串視為 0。"""
    cleaned = str(value).replace(",", "").strip()
    return float(cleaned) if cleaned else 0.0


def _trade_id(payload: dict) -> str:
    canonical = json.dumps(
        {k: payload[k] for k in ("executed_at", "broker", "symbol", "side", "shares", "price")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "tr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _already_recorded(trade_id: str) -> bool:
    if not TRADE_LOG.exists():
        return False
    for line in TRADE_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("trade_id") == trade_id:
            return True
    return False


def _append_trade(entry: dict) -> None:
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRADE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="記錄成交並更新 Google Sheet")
    ap.add_argument("--symbol", required=True, help="Sheet 的 symbol 欄值，如 QQQ")
    ap.add_argument("--side", required=True, choices=("buy", "sell"))
    ap.add_argument("--shares", required=True, type=float)
    ap.add_argument("--price", required=True, type=float)
    ap.add_argument("--executed-at", required=True, help="成交時間（ISO-8601，含時區）")
    ap.add_argument("--broker", default="IB", help="Sheet 的 broker 欄值")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--cash-column", default="cash_usd", help="要扣款／入帳的現金欄名")
    ap.add_argument("--account-ref", default="", help="遮蔽後的帳號，如 U****1599")
    ap.add_argument("--note", default="", help="券商通知逐字內容，供稽核")
    ap.add_argument("--apply", action="store_true", help="實際寫入；省略則只顯示 diff")
    ap.add_argument(
        "--log-only",
        action="store_true",
        help="只記事件、不碰 Sheet。用於「已手動更新過 Sheet」的成交——"
        "腳本無法自行判斷這件事，必須由使用者明確聲明。",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from fetchers.gsheets import locate_portfolio_cells, write_portfolio_cells

    gross = round(args.shares * args.price, 2)
    signed_shares = args.shares if args.side == "buy" else -args.shares

    cells = locate_portfolio_cells(
        [
            {"match": {"symbol": args.symbol}, "column": "shares"},
            {"match": {"symbol": args.symbol}, "column": "avg_cost"},
            {"match": {"broker": args.broker, "bucket": "CASH"}, "column": args.cash_column},
        ]
    )
    shares_cell, cost_cell, cash_cell = cells
    old_shares = _number(shares_cell["current"])
    old_cost = _number(cost_cell["current"])
    old_cash = _number(cash_cell["current"])

    new_shares = old_shares + signed_shares
    if new_shares < 0:
        print(f"✗ 賣出 {args.shares} 股會使持股變成 {new_shares}，中止", file=sys.stderr)
        return 2
    if args.side == "buy":
        # 加權平均成本只在買進時變動；賣出不改變成本基礎。
        new_cost = (
            round((old_shares * old_cost + args.shares * args.price) / new_shares, 2)
            if new_shares > 0
            else 0.0
        )
    else:
        new_cost = old_cost
    new_cash = round(old_cash - gross if args.side == "buy" else old_cash + gross, 2)

    payload = {
        "executed_at": args.executed_at,
        "broker": args.broker,
        "symbol": args.symbol,
        "side": args.side,
        "shares": args.shares,
        "price": args.price,
    }
    trade_id = _trade_id(payload)

    print(f"成交：{args.side.upper()} {args.shares:g} {args.symbol} @ {args.price} "
          f"{args.currency}　總額 {gross:,.2f}")
    print(f"trade_id：{trade_id}")
    print("\n將變更的儲存格（僅此三格，其餘欄位不動）：")
    print(f"  {shares_cell['a1']:<16} shares          {old_shares:g} → {new_shares:g}")
    print(f"  {cost_cell['a1']:<16} avg_cost        {old_cost} → {new_cost}"
          f"   ← 由本腳本計算，非通知逐字值")
    print(f"  {cash_cell['a1']:<16} {args.cash_column:<15} {old_cash:,.2f} → {new_cash:,.2f}")

    if _already_recorded(trade_id):
        print("\n⚠ 這筆成交已在 trade_log.jsonl 中；重複執行不會再寫事件紀錄。")

    if args.log_only:
        if _already_recorded(trade_id):
            print("\n這筆成交已在事件紀錄中，未重複寫入。")
            return 0
        _append_trade(
            {
                "trade_id": trade_id,
                **payload,
                "currency": args.currency,
                "gross_amount": gross,
                "account_ref": args.account_ref,
                "note": args.note,
                "recorded_at": _now(),
                "sheet_writes": [],
                "sheet_update": "manual_by_user",
            }
        )
        print(f"\n✓ 事件已記於 {TRADE_LOG.relative_to(_ROOT)}；"
              "Sheet 未被改動（已由使用者手動更新）。")
        print("  上方 diff 僅供對照，不是待執行的變更。")
        return 0

    if not args.apply:
        print("\n（dry-run）確認無誤後加 --apply 實際寫入。")
        print("  若這筆你已手動改過 Sheet，改用 --log-only 只記事件、不重複計算。")
        return 0

    result = write_portfolio_cells(
        [
            {"a1": shares_cell["a1"], "expected": shares_cell["current"], "value": new_shares},
            {"a1": cost_cell["a1"], "expected": cost_cell["current"], "value": new_cost},
            {"a1": cash_cell["a1"], "expected": cash_cell["current"], "value": new_cash},
        ]
    )
    if not _already_recorded(trade_id):
        _append_trade(
            {
                "trade_id": trade_id,
                **payload,
                "currency": args.currency,
                "gross_amount": gross,
                "account_ref": args.account_ref,
                "note": args.note,
                "recorded_at": _now(),
                "sheet_writes": result["written"],
            }
        )
    print(f"\n✓ 已寫入 {len(result['written'])} 格，事件已記於 {TRADE_LOG.relative_to(_ROOT)}")
    print("  Sheet 仍是持股唯一權威；市值與 NAV 未被本腳本改動。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
