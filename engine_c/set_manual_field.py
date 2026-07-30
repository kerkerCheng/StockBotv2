"""
set_manual_field.py — 手動填入 Engine C 的人工觀測欄位。

合法欄位名由 `config/engine_c_observation_fields.json` 界定（loader 見
`engine_c/observation_fields.py`），**未登記的名字一律拒絕**——開放寫入的風險不是
欄位不夠，而是同一概念被寫成不同名字造成同義詞漂移。要新增就先改那個 config。

欄位分兩種：
  - `gate_member=true` 的五項＝L9 前置條件 #3 的財務核驗清單，是 Watchlist 升格 gate；
    其中 customer_concentration 與 backlog 必須人工從一手 filing 填。
  - `gate_member=false` 的擴充欄位（或有請求權、covenant、通路結構、監管依賴…）
    不影響 gate_pass，但會進 Engine D 的 reference index，可被對應的 Confidence 軸引用。

value 一律要求非空字串，`--source` 與 `--as-of` 皆必填（traceability 是硬規則）。

⚠ 金額字串請勿經 PowerShell 傳參：`US$71.3M` 會被當變數前綴展開成 `US.3M`，
   在 append-only ledger 裡造成需要 supersede 才能更正的損毀。用 Python 或 heredoc。

用法:
    python engine_c/set_manual_field.py AMAT customer_concentration \
        "FY2025 兩大客戶約 19% 與 15%（合計 ~34%）" \
        --source "AMAT FY2025 10-K, Note 15 / Concentration" --as-of 2025-11-30
    python engine_c/set_manual_field.py --list AMAT       # 列出某 ticker 已填欄位
    python engine_c/set_manual_field.py --fields AMAT     # 列出所有已登記欄位（階層式）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_c.db import get_conn  # noqa: E402
from engine_c.manual_observations import append_manual_observation  # noqa: E402
from engine_c.observation_fields import (  # noqa: E402
    ObservationFieldError,
    get_observation_field_registry,
    validate_field_name,
)


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
    ap.add_argument(
        "--fields",
        dest="do_fields",
        action="store_true",
        help="列出所有已登記的觀測欄位（階層式 category → field_name）",
    )
    args = ap.parse_args()

    if args.do_fields:
        registry = get_observation_field_registry()
        print(f"config/engine_c_observation_fields.json v{registry.version}")
        print(registry.describe())
        return 0

    if args.do_list:
        return _list(args.ticker)

    if not args.field_name or args.value is None:
        ap.error("需要 field_name 與 value（或用 --list 只查詢）")
    try:
        spec = validate_field_name(args.field_name)
    except ObservationFieldError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    if spec.auto_source is not None:
        print(
            f"⚠ 提醒：'{spec.field_name}' 平常由 {spec.auto_source} 自動取得；"
            "手動覆寫只在自動來源不可用時才適當。",
            file=sys.stderr,
        )
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
