"""`fundamental_history.metric` 的 CHECK 遷移（SQLite；2026-10-01 Phase 4 Step 4.6）。

## 為什麼要遷移

SQLite 不能 `ALTER` 一個 CHECK 約束：`ensure_history_schema` 只 `CREATE TABLE IF NOT EXISTS`，所以已經存在的
正式庫永遠停在舊字彙——新指標（`equity_issued_value_quarter／_annual`）寫進去會撞 CHECK。唯一的辦法是
**重建這張表**：建新表（新 CHECK）→ 整表複製 → 對帳 → 換名。

## 怎麼做才不會丟資料

1. **先備份**：用 SQLite backup API（`Connection.backup`）——正式庫是 WAL 模式，直接複製 `.db` 檔會漏掉還在
   `-wal` 裡的頁；backup API 拿的是一致的快照。備份檔 `quick_check` 通過、列數相同才往下走。
2. **一個交易做完**：`BEGIN IMMEDIATE` → 建新表 → 逐欄複製 → 列數與內容摘要（逐列排序後的 sha256）相同 →
   刪舊表 → 新表換名 → 重建索引 → `COMMIT`。任何一步不對就 `ROLLBACK`，正式庫一字不動。
3. **取 writer lock**（互動 owner）：daily 05:30 也取同一把鎖，所以遷移不會與 daily 同時跑。
4. **冪等**：CHECK 已經認得全部 `METRICS` 就什麼都不做。

可重建投影（L10：今天重取一次拿得回來），不是 append-only ledger；但備份照做——重抓要打 SEC 幾十次，
備份只要一秒。

用法::

    python -m engine_c.migrate_fundamental_metrics            # dry-run：印現在的 CHECK 缺哪幾個、列數
    python -m engine_c.migrate_fundamental_metrics --apply    # 備份 → 遷移 → 對帳 → 印收據
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TABLE = "fundamental_history"
COLUMNS: tuple[str, ...] = ("ticker", "metric", "period_start", "period_end", "filed", "accession", "form",
                            "value", "currency", "unit_scale", "derived", "tag", "source", "fetched_at")
_CHECK = re.compile(r"metric\s+TEXT\s+NOT\s+NULL\s+CHECK\s*\(\s*metric\s+IN\s*\(([^)]*)\)\s*\)", re.IGNORECASE)


class MigrationError(RuntimeError):
    """對帳不符或前提不成立——正式庫沒有被改動（交易已 rollback）。"""


def current_metrics(conn: sqlite3.Connection) -> frozenset[str]:
    """這個庫的 `fundamental_history` CHECK 現在認得哪些 metric（讀 `sqlite_master` 的建表語句）。"""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).fetchone()
    if not row or not row[0]:
        raise MigrationError(f"這個庫沒有 {TABLE} 表")
    match = _CHECK.search(str(row[0]))
    if not match:
        raise MigrationError(f"{TABLE} 的建表語句裡找不到 metric 的 CHECK——形狀不是預期的，不動它")
    return frozenset(m.strip().strip("'\"") for m in match.group(1).split(",") if m.strip())


def missing_metrics(conn: sqlite3.Connection) -> list[str]:
    from engine_c.history_backfill import METRICS

    have = current_metrics(conn)
    return [m for m in METRICS if m not in have]


def table_fingerprint(conn: sqlite3.Connection, table: str = TABLE) -> tuple[int, str]:
    """(列數, 逐列排序後的 sha256)——遷移前後必須完全相同。"""
    digest = hashlib.sha256()
    count = 0
    cols = ", ".join(COLUMNS)
    for row in conn.execute(f"SELECT {cols} FROM {table} ORDER BY ticker, metric, period_end, accession"):
        digest.update(json.dumps(list(row), ensure_ascii=False, default=str).encode("utf-8"))
        count += 1
    return count, digest.hexdigest()


def backup_database(db_path: Path, destination: Path) -> dict[str, Any]:
    """SQLite backup API 做一致的快照（WAL 裡的頁也在）；`quick_check` 與列數對得上才算數。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise MigrationError(f"備份檔已存在：{destination}——不覆寫")
    source = sqlite3.connect(str(db_path))
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target)
        if target.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise MigrationError("備份檔 quick_check 沒有通過")
        original = table_fingerprint(source)
        copied = table_fingerprint(target)
        if original != copied:
            raise MigrationError(f"備份檔的 {TABLE} 與正式庫不一致：{copied} ≠ {original}")
    finally:
        target.close()
        source.close()
    return {"path": str(destination), "rows": original[0], "sha256": original[1]}


def migrate(conn: sqlite3.Connection) -> dict[str, Any]:
    """在一個交易裡重建表、換上新 CHECK。已經是新字彙就什麼都不做（冪等）。"""
    from engine_c.history_backfill import METRICS

    missing = missing_metrics(conn)
    before = table_fingerprint(conn)
    if not missing:
        return {"status": "already_current", "rows": before[0], "sha256": before[1], "added": []}
    checklist = ", ".join(f"'{m}'" for m in METRICS)
    cols = ", ".join(COLUMNS)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(f"""CREATE TABLE {TABLE}__new (
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL CHECK (metric IN ({checklist})),
    period_start TEXT,
    period_end TEXT NOT NULL,
    filed TEXT NOT NULL,
    accession TEXT NOT NULL,
    form TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT NOT NULL,
    unit_scale INTEGER NOT NULL DEFAULT 1 CHECK (unit_scale > 0),
    derived TEXT,
    tag TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, metric, period_end, accession)
)""")
        conn.execute(f"INSERT INTO {TABLE}__new ({cols}) SELECT {cols} FROM {TABLE}")
        copied = table_fingerprint(conn, f"{TABLE}__new")
        if copied != before:
            raise MigrationError(f"複製後列數或內容不符：{copied} ≠ {before}")
        conn.execute(f"DROP TABLE {TABLE}")
        conn.execute(f"ALTER TABLE {TABLE}__new RENAME TO {TABLE}")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_fundamental_history_asof "
                     f"ON {TABLE} (ticker, metric, period_end, filed)")
        after = table_fingerprint(conn)
        if after != before or missing_metrics(conn):
            raise MigrationError(f"換名後對帳不符或 CHECK 仍缺：{after} ≠ {before}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"status": "migrated", "rows": before[0], "sha256": before[1], "added": missing}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fundamental_history.metric 的 CHECK 遷移（SQLite；備份 → 重建 → 對帳）")
    parser.add_argument("--db", help="SQLite 路徑（省略＝runtime pointer 指的正式庫）")
    parser.add_argument("--apply", action="store_true", help="真的遷移（預設 dry-run，只印）")
    args = parser.parse_args(argv)

    from engine_c.db import sqlite_path

    db_path = Path(args.db) if args.db else sqlite_path()
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        missing = missing_metrics(conn)
        rows, digest = table_fingerprint(conn)
        print(f"{db_path}｜{TABLE} {rows} 列｜CHECK 缺 {missing or '無'}")
        if not args.apply:
            print("（dry-run；加 --apply 才備份並遷移）")
            return 0
        if not missing:
            print("✓ 已是新字彙，不需要遷移")
            return 0
    finally:
        conn.close()

    from engine_b.writer_lock import INTERACTIVE_OWNER, WriterLockHeld, acquire, release

    try:
        acquire(INTERACTIVE_OWNER, ttl_minutes=15, purpose="Engine C fundamental_history CHECK 遷移（Phase 4 Step 4.6）")
    except WriterLockHeld as exc:
        print(f"✗ 拒絕：writer lock 被占用（daily 正在跑？）——{exc}", file=sys.stderr)
        return 2
    try:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = backup_database(db_path, db_path.parent / "backups" / f"{db_path.stem}.pre-metrics-{stamp}.db")
        conn = sqlite3.connect(str(db_path), isolation_level=None)
        try:
            result = migrate(conn)
        finally:
            conn.close()
        receipt = {"migrated_at": stamp, "db": str(db_path), "backup": backup, "result": result}
        (db_path.parent / "backups" / f"{db_path.stem}.pre-metrics-{stamp}.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except MigrationError as exc:
        print(f"✗ 遷移中止（正式庫未改動）：{exc}", file=sys.stderr)
        return 3
    finally:
        release(INTERACTIVE_OWNER)


if __name__ == "__main__":
    raise SystemExit(main())
