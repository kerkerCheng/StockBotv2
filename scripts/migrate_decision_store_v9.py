"""Decision Store schema 8 → 9：新增 `cohort_thesis` 表（variant perception 的家）。

背景：2026-09-02 使用者定案「cohort 是終點，Watchlist 層除役」（AGENTS 報告產出段）。
variant perception 是原三級模板中唯一無家的 alpha 論證，收編為 cohort 的 thesis 欄位。

⚠ Decision Store 是 private append-only authority（L10）：本腳本

- 先做 recovery backup（backup_pre_v9_<timestamp>.db），失敗即中止；
- 只**新增**一張空表與索引，不觸碰任何既有表或列；
- 完成後驗證：表存在、既有表筆數逐一不變、foreign_key_check 乾淨；
- 任一驗證失敗即還原提示（backup 路徑印在輸出）。

用法：
    python scripts/migrate_decision_store_v9.py            # dry-run
    python scripts/migrate_decision_store_v9.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"

DDL = """
CREATE TABLE IF NOT EXISTS cohort_thesis (
    thesis_id           TEXT PRIMARY KEY,
    cohort_id           TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    variant_perception  TEXT NOT NULL,
    supersedes_id       TEXT REFERENCES cohort_thesis(thesis_id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
IDX = """
CREATE INDEX IF NOT EXISTS idx_cohort_thesis_cohort_time
    ON cohort_thesis (cohort_id, created_at, thesis_id);
"""


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not DB.exists():
        print(f"DB 不存在：{DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB)
    try:
        version = conn.execute(
            "SELECT value FROM decision_store_meta WHERE key='schema_version'"
        ).fetchone()
        print(f"目前 schema_version: {version[0] if version else '?'}")
        if version and version[0] == "9":
            print("已是 v9，無事可做。")
            return 0
        before = table_counts(conn)
        if not args.apply:
            print("dry-run：將新增 cohort_thesis 表＋索引、schema_version → 9。")
            print(f"既有 {len(before)} 表筆數已記錄，apply 後逐一比對。")
            return 0
    finally:
        conn.close()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = DB.with_name(f"backup_pre_v9_{stamp}.db")
    shutil.copy2(DB, backup)
    print(f"backup: {backup}")

    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            conn.executescript(DDL + IDX)
            conn.execute(
                "INSERT INTO decision_store_meta(key, value) VALUES('schema_version','9') "
                "ON CONFLICT(key) DO UPDATE SET value='9', updated_at=datetime('now')"
            )
        after = table_counts(conn)
        assert "cohort_thesis" in after, "cohort_thesis 未建立"
        for t, n in before.items():
            assert after.get(t) == n, f"表 {t} 筆數改變：{n} → {after.get(t)}"
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert not fk, f"foreign_key_check 失敗：{fk}"
        print("v9 完成：cohort_thesis 已建立，既有表筆數不變，FK 乾淨。")
    except AssertionError as exc:
        print(f"驗證失敗：{exc}；請自 {backup} 還原", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
