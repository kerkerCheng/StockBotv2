"""`python -m decision_lab` — 舊 Decision Store 的唯讀視窗（frozen 2026-09-22，G12）。

只有兩個子命令，都用 `mode=ro` 的 sqlite 連線、不開 `DecisionStore`（開店會在 DB 缺席時建一個空庫，
那是寫入）：

    python -m decision_lab status     # 每張表的筆數、schema 版本、檔案 sha256（與 Phase 0 基準對帳用）
    python -m decision_lab history    # live_choices／live_execution_reports 全部列出（歷史唯一一筆 live 收據住這裡）
    python -m decision_lab history --decisions   # 另列每個 cohort 最後一筆 decision（id／effective_at／attention）

研究側（evaluate-signal／reassess／today／card／references／record-choice／record-fill…）已於
Phase 0 Step 0b.4 退役。新成交收據住 `library/trades/trade_log.jsonl`（`scripts/record_trade.py`），
資本硬擋住 `risk/hard_caps.py`。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, TextIO

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = _ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"

FROZEN_BANNER = "Decision Store frozen 2026-09-22（G12）——唯讀歷史；研究側已退役，寫入請走 scripts/record_trade.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_lab",
        description="舊 Decision Store 的唯讀視窗（status／history）。",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="表筆數、schema 版本、檔案 sha256")
    status.add_argument("--json", action="store_true")
    history = sub.add_parser("history", help="live 選擇與成交回報的歷史（唯讀）")
    history.add_argument("--decisions", action="store_true", help="另列每個 cohort 最後一筆 decision")
    history.add_argument("--json", action="store_true")
    return parser


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def store_status(db: Path) -> dict[str, Any]:
    conn = _connect(db)
    try:
        tables = [
            str(row["name"]) for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        counts = {
            table: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
        version_row = conn.execute(
            "SELECT value FROM decision_store_meta WHERE key = 'schema_version'"
        ).fetchone()
    finally:
        conn.close()
    return {
        "frozen": FROZEN_BANNER,
        "database": str(db),
        "sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
        "schema_version": str(version_row["value"]) if version_row else None,
        "table_counts": counts,
    }


def store_history(db: Path, *, decisions: bool = False) -> dict[str, Any]:
    conn = _connect(db)
    try:
        choices = [dict(row) for row in conn.execute(
            "SELECT choice_id, decision_id, selected_weight, choice_type, reason, "
            "approved_action_id, system_supported_upper, decided_at "
            "FROM live_choices ORDER BY decided_at, choice_id"
        )]
        fills = [dict(row) for row in conn.execute(
            "SELECT fill_id, decision_id, choice_id, execution_ref, shares, price, currency, executed_at "
            "FROM live_execution_reports ORDER BY executed_at, fill_id"
        )]
        payload: dict[str, Any] = {
            "frozen": FROZEN_BANNER,
            "live_choices": choices,
            "live_execution_reports": fills,
        }
        if decisions:
            rows = conn.execute(
                """
                SELECT sd.cohort_id, co.company_id, co.research_ticker, sd.decision_id,
                       sd.effective_at, sd.payload_json
                  FROM system_decisions sd
                  JOIN decision_cohorts co ON co.cohort_id = sd.cohort_id
                 ORDER BY sd.cohort_id, sd.effective_at DESC, sd.decision_id DESC
                """
            ).fetchall()
            latest: dict[str, dict[str, Any]] = {}
            for row in rows:
                cohort = str(row["cohort_id"])
                if cohort in latest:
                    continue
                try:
                    attention = (json.loads(row["payload_json"]) or {}).get("attention")
                except (TypeError, ValueError):
                    attention = None
                latest[cohort] = {
                    "cohort_id": cohort,
                    "company_id": row["company_id"],
                    "research_ticker": row["research_ticker"],
                    "decision_id": row["decision_id"],
                    "effective_at": row["effective_at"],
                    "attention": attention,
                }
            payload["latest_decisions"] = list(latest.values())
    finally:
        conn.close()
    return payload


def _print_status(payload: dict[str, Any], out: TextIO) -> None:
    print(f"# {payload['frozen']}", file=out)
    print(f"- database：{payload['database']}", file=out)
    print(f"- sha256：{payload['sha256']}", file=out)
    print(f"- schema_version：{payload['schema_version']}", file=out)
    for table, count in payload["table_counts"].items():
        print(f"  {table:<28} {count}", file=out)


def _print_history(payload: dict[str, Any], out: TextIO) -> None:
    print(f"# {payload['frozen']}", file=out)
    print(f"## live_choices（{len(payload['live_choices'])}）", file=out)
    for row in payload["live_choices"]:
        print(f"  {row['decided_at']}  {row['choice_id']}  decision={row['decision_id']}  "
              f"weight={row['selected_weight']}  type={row['choice_type']}  reason={row['reason'] or '—'}",
              file=out)
    print(f"## live_execution_reports（{len(payload['live_execution_reports'])}）", file=out)
    for row in payload["live_execution_reports"]:
        print(f"  {row['executed_at']}  {row['fill_id']}  decision={row['decision_id']}  "
              f"{row['shares']} @ {row['price']} {row['currency']}  ref={row['execution_ref']}", file=out)
    if "latest_decisions" in payload:
        print(f"## 每個 cohort 最後一筆 decision（{len(payload['latest_decisions'])}）", file=out)
        for row in payload["latest_decisions"]:
            print(f"  {row['cohort_id']}  {row['company_id'] or '—'}／{row['research_ticker'] or '—'}  "
                  f"{row['decision_id']}  {row['effective_at']}  attention={row['attention'] or '—'}", file=out)


def run(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    out = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    db = Path(args.db)
    if not db.is_file():
        print(f"找不到 Decision Store：{db}（凍結唯讀，本命令不會建立空庫）", file=sys.stderr)
        return 2
    try:
        if args.command == "status":
            payload = store_status(db)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2), file=out)
            else:
                _print_status(payload, out)
        else:
            payload = store_history(db, decisions=bool(args.decisions))
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, default=str), file=out)
            else:
                _print_history(payload, out)
    except sqlite3.Error as exc:
        print(f"Decision Store 讀取失敗：{type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
