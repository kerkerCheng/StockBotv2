"""寫入 `verifiability=mechanical` 的 Engine C 觀測——**不需 pq2 核准**。

## 為什麼需要一個獨立入口

2026-09-04 使用者定案把 Engine C 人工 ledger 的 gate 改成按「可否確定性重導」分之後，
`mechanical` 欄位不再需要人工核准。但當時唯一的寫入路徑是
`engine_b/todo.py::complete_engine_c_observation`——它是 **pq2 核准後**才呼叫的收尾
動作。判準改了而走廊沒改，等於改了個寂寞。

## ⚠ 這支**拒絕** judgment 欄位，那是它最重要的行為

若它什麼都寫得進去，它就是一條繞過 pq2 的後門，而那道 gate 正是為了擋
「誰算客戶」「這算不算或有請求權」這類無法被複查的判讀。放行與收緊必須同時發生
（L15：分開之後兩邊都要更嚴）。

要寫 judgment 欄位請走既有的 pq2 提案流程（`engine_c.pending_observations`
→ 使用者 `go` → `engine_b.todo complete`）。

用法：
    python scripts/record_mechanical_observation.py \\
        --ticker COHR --field segment_revenue_share \\
        --value '{"Datacenter & Communications": 0.741, "Industrial": 0.259}' \\
        --source-ref "COHR FY2026 10-K (EDGAR 0000820318-26-000020, filed 2026-08-14) Note 20" \\
        --as-of 2026-06-30

`--dry-run` 只驗證不寫入。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine_c.observation_fields import (  # noqa: E402
    get_observation_field_registry,
    validate_field_name,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--value", required=True, help="JSON（mechanical 欄位必須含數值）")
    parser.add_argument("--source-ref", required=True, help="一手文件與定位，必填")
    parser.add_argument("--as-of", required=True, help="這筆事實屬於哪一天（財報期末）")
    parser.add_argument("--author", default="session")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry = get_observation_field_registry()
    try:
        spec = validate_field_name(args.field)
    except Exception as exc:
        print(f"✗ {exc}", file=sys.stderr)
        print(f"\n已登記欄位：\n{registry.describe()}", file=sys.stderr)
        return 2

    # ⚠ 這是本腳本存在的理由，不是防禦性程式碼。
    if spec.requires_user_approval:
        print(
            f"✗ `{args.field}` 是 verifiability={spec.verifiability} 欄位，"
            "**必須走 pq2 核准**，不能用這支寫入。\n"
            f"  可用本支寫入的欄位：{', '.join(registry.mechanical_field_names)}\n"
            "  judgment 欄位請走：engine_c.pending_observations 提案 → 使用者 go → "
            "engine_b.todo complete",
            file=sys.stderr,
        )
        return 3

    from engine_c.db import get_conn  # noqa: E402
    from engine_c.manual_observations import (  # noqa: E402
        append_manual_observation,
        ensure_manual_observation_schema,
    )

    conn = get_conn()
    ensure_manual_observation_schema(conn)
    if args.dry_run:
        # 只跑寫入端的驗證（JSON＋數值），不落庫。
        from engine_c.manual_observations import (
            _require_machine_comparable_if_mechanical as _check,
        )

        try:
            _check(args.field, args.value)
        except ValueError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            return 4
        print(f"✓ dry-run 通過：{args.ticker} {args.field}（未寫入）")
        return 0

    try:
        observation_id = append_manual_observation(
            conn,
            ticker=args.ticker,
            field_name=args.field,
            value=args.value,
            source_ref=args.source_ref,
            as_of=args.as_of,
            author=args.author,
        )
    except ValueError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 4
    print(f"✓ 已寫入 {observation_id}：{args.ticker} {args.field} @ {args.as_of}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
