"""
set_manual_field.py — 手動填入 Engine C 財務核驗清單中 yfinance 無法自動取得的欄位。

清單 5 項裡有 2 項一定要人工從一手 filing 填：
  - customer_concentration  客戶集中度（前幾大客戶佔營收 %）
  - backlog                 訂單能見度（backlog 金額；若公司停揭露則填替代指標並註明）

填入即成 checklist 的 `manual_reviewed`，是 Watchlist 升格 / L9 前置 #3 的必要條件。
value 一律要求非空字串，且強烈建議帶 --source 指明依據的 filing（traceability 是硬規則）。

用法:
    python engine_c/set_manual_field.py AMAT customer_concentration \
        "FY2025 兩大客戶約 19% 與 15%（合計 ~34%）" \
        --source "AMAT FY2025 10-K, Note 15 / Concentration"
    python engine_c/set_manual_field.py --list AMAT      # 列出某 ticker 已填欄位
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_c.db import get_conn  # noqa: E402
from engine_c.manual_observations import append_manual_observation  # noqa: E402

_MANUAL_FIELDS = ("customer_concentration", "backlog")


def _list(ticker: str) -> int:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT field_name, value, source_note, updated_at "
            "FROM manual_fields WHERE ticker = ? ORDER BY field_name",
            (ticker.upper().strip(),),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        print(f"{ticker.upper()}: 尚無 manual_fields")
        return 0
    for r in rows:
        fn, val, note, ts = (r[0], r[1], r[2], r[3])
        print(f"  {fn:24} = {val}")
        print(f"  {'':24}   源: {note or '(未註明)'}  更新: {ts}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="設定 Engine C 人工財務欄位（manual_fields）。")
    ap.add_argument("ticker", help="股票代號，如 AMAT")
    ap.add_argument("field_name", nargs="?", help="欄位名（customer_concentration / backlog）")
    ap.add_argument("value", nargs="?", help="值（非空字串；backlog 停揭露時填替代指標並註明）")
    ap.add_argument("--source", required=False, help="依據的 filing（必填）")
    ap.add_argument("--as-of", dest="as_of", help="觀測日期／時間（必填，ISO-8601）")
    ap.add_argument("--author", default="user", help="輸入者識別（預設 user）")
    ap.add_argument("--list", dest="do_list", action="store_true", help="列出該 ticker 已填欄位")
    args = ap.parse_args()

    if args.do_list:
        return _list(args.ticker)

    if not args.field_name or args.value is None:
        ap.error("需要 field_name 與 value（或用 --list 只查詢）")
    if args.field_name not in _MANUAL_FIELDS:
        print(f"⚠ 提醒：'{args.field_name}' 不在標準人工欄位 {_MANUAL_FIELDS}；"
              "仍會寫入，但 checklist 只讀這兩個。", file=sys.stderr)
    if not args.source or not args.as_of:
        ap.error("manual observation 必須同時提供 --source 與 --as-of")

    conn = get_conn()
    try:
        observation_id = append_manual_observation(
            conn,
            ticker=args.ticker,
            field_name=args.field_name,
            value=args.value,
            source_ref=args.source,
            as_of=args.as_of,
            author=args.author,
        )
    finally:
        conn.close()
    print(f"✓ 已追加 {observation_id}：{args.ticker.upper()} / {args.field_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
