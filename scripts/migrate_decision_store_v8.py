"""Decision Store schema 7 → 8：`live_choices` 新增 `user_sized` 與 `system_supported_upper`。

背景見 `docs/brainstorms/2026-08-18-alpha-live-user-sized-requirements.md`。

⚠ **Decision Store 是 private append-only authority**（`AGENTS.md` L10 的 ⚠ 適用範圍）：
沒有第二份來源、Git 救不回。本腳本因此：

- 先做 recovery backup（`backup_pre_v8_<timestamp>.db`），失敗即中止；
- 只改 `live_choices` 一張表，其餘表原封不動；
- 用 SQLite 官方的 12 步 table-rebuild 程序搬移**既有列**（`CHECK` 約束無法 ALTER），
  搬完逐列比對筆數與 digest；
- `PRAGMA foreign_keys` 在交易外關閉、完成後重開並跑 `foreign_key_check`；
- 任一驗證失敗就 rollback，DB 維持 schema 7 可用。

用法：
    python scripts/migrate_decision_store_v8.py            # dry-run，只報告
    python scripts/migrate_decision_store_v8.py --apply
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
# ⚠ marker 住在 private root，**不是** decision_lab/ 之下（見 `store.py::open` 的
# `private_root / "decision_lab_authority.json"`）。首版寫成 decision_lab/ 底下，於是
# `MARKER.is_file()` 恆為 False、整段同步被**靜默跳過**——成功與失敗長得一模一樣（L13）。
# 因此下方改成：找不到 marker 就報錯，不當作沒事。
MARKER = ROOT / "library" / "private" / "decision_lab_authority.json"

FROM_VERSION = "7"
TO_VERSION = "8"

NEW_TABLE = """
CREATE TABLE live_choices_v8 (
    choice_id          TEXT PRIMARY KEY,
    decision_id        TEXT NOT NULL REFERENCES system_decisions(decision_id),
    selected_weight    REAL NOT NULL CHECK (selected_weight >= 0),
    choice_type        TEXT NOT NULL CHECK (choice_type IN ('accepted', 'skipped', 'below_range', 'override', 'user_sized')),
    reason             TEXT,
    approved_action_id TEXT,
    system_supported_upper REAL,
    decided_at         TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (decision_id, selected_weight, decided_at)
)
"""

COPY = """
INSERT INTO live_choices_v8 (
    choice_id, decision_id, selected_weight, choice_type,
    reason, approved_action_id, system_supported_upper, decided_at, created_at
)
SELECT choice_id, decision_id, selected_weight, choice_type,
       reason, approved_action_id, NULL, decided_at, created_at
FROM live_choices
"""

INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_choices_approved_action
    ON live_choices (approved_action_id)
    WHERE approved_action_id IS NOT NULL
"""


def _fingerprint(conn: sqlite3.Connection, table: str) -> tuple[int, str]:
    """(筆數, 內容指紋)。搬移前後必須相同——空表也要驗，避免『成功』與『沒搬到』同形。"""
    rows = conn.execute(
        f"SELECT choice_id, decision_id, selected_weight, choice_type, "  # noqa: S608
        f"reason, approved_action_id, decided_at FROM {table} ORDER BY choice_id"
    ).fetchall()
    return len(rows), repr([tuple(r) for r in rows])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="實際寫入；預設只 dry-run")
    args = ap.parse_args()

    if not DB.is_file():
        print(f"✗ 找不到 Decision Store：{DB}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        version = conn.execute(
            "SELECT value FROM decision_store_meta WHERE key = 'schema_version'"
        ).fetchone()
        current = str(version["value"]) if version else "?"
        before_n, before_fp = _fingerprint(conn, "live_choices")
        has_col = any(
            r["name"] == "system_supported_upper"
            for r in conn.execute("PRAGMA table_info(live_choices)")
        )
        print(f"目前 schema_version = {current}｜live_choices {before_n} 列"
              f"｜system_supported_upper 欄位{'已存在' if has_col else '不存在'}")

        if current == TO_VERSION and has_col:
            # DB 已經是 v8，但 marker 可能還停在舊版（首版腳本的 marker 路徑寫錯，
            # 導致同步被靜默跳過）。中途重跑必須能把剩下那一半補完，不能直接宣告完成
            # ——那正是「成功與失敗同形」的形狀。
            print("✓ DB 已是 v8")
            return _sync_marker(apply=args.apply)
        if current != FROM_VERSION:
            print(f"✗ 預期 schema_version={FROM_VERSION}，實際 {current}；中止", file=sys.stderr)
            return 2

        if not args.apply:
            print("\n(dry-run) 將執行：備份 → rebuild live_choices → 驗證 → bump 至 v8")
            print("實際執行請加 --apply")
            return 0

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = DB.with_name(f"backup_pre_v8_{stamp}.db")
        conn.close()
        shutil.copy2(DB, backup)
        print(f"✓ recovery backup：{backup.name}")

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        # foreign_keys 必須在交易「外」關閉，否則 pragma 靜默無效（SQLite 12 步程序第 1 步）。
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(NEW_TABLE)
            conn.execute(COPY)
            conn.execute("DROP TABLE live_choices")
            conn.execute("ALTER TABLE live_choices_v8 RENAME TO live_choices")
            conn.execute(INDEX)

            after_n, after_fp = _fingerprint(conn, "live_choices")
            if (after_n, after_fp) != (before_n, before_fp):
                raise RuntimeError(
                    f"搬移前後內容不一致（{before_n} → {after_n} 列）；rollback"
                )
            conn.execute(
                "UPDATE decision_store_meta SET value = ? WHERE key = 'schema_version'",
                (TO_VERSION,),
            )
            fk = conn.execute("PRAGMA foreign_key_check").fetchall()
            if fk:
                raise RuntimeError(f"foreign_key_check 失敗：{[tuple(r) for r in fk]}")
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if str(integrity[0]) != "ok":
                raise RuntimeError(f"integrity_check 失敗：{integrity[0]}")
            conn.commit()
        except BaseException as exc:
            conn.rollback()
            print(f"✗ migration 失敗已 rollback：{exc}", file=sys.stderr)
            print(f"  DB 維持 schema {FROM_VERSION}；備份仍在 {backup.name}", file=sys.stderr)
            return 1
        finally:
            conn.execute("PRAGMA foreign_keys=ON")

        print(f"✓ schema {FROM_VERSION} → {TO_VERSION}，live_choices {after_n} 列已保留")

        return _sync_marker(apply=True)
    finally:
        conn.close()


def _sync_marker(*, apply: bool) -> int:
    """把 authority marker 的 schema_version 對齊 DB。

    marker 記著 schema_version；留著舊值會讓下一個 session 讀到與 DB 不符的版本。
    找不到或內容沒變都是異常，必須出聲——不得靜默跳過（L13）。
    """

    if not MARKER.is_file():
        print(f"✗ 找不到 authority marker：{MARKER}", file=sys.stderr)
        return 1
    text = MARKER.read_text(encoding="utf-8")
    if f'"schema_version":"{TO_VERSION}"' in text or f'"schema_version": "{TO_VERSION}"' in text:
        print("✓ authority marker 已是 v8")
        return 0
    if not apply:
        print("(dry-run) authority marker 仍是舊版，--apply 會同步")
        return 0
    updated = text.replace(
        f'"schema_version":"{FROM_VERSION}"', f'"schema_version":"{TO_VERSION}"'
    ).replace(f'"schema_version": "{FROM_VERSION}"', f'"schema_version": "{TO_VERSION}"')
    if updated == text:
        print(f"✗ marker 未含 schema_version={FROM_VERSION}，無法同步：{MARKER}", file=sys.stderr)
        return 1
    MARKER.write_text(updated, encoding="utf-8")
    print("✓ authority marker 已同步至 v8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
