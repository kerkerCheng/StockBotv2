from __future__ import annotations

import sqlite3

import pytest

from engine_c.db import _ensure_sqlite_schema
from engine_c.manual_observations import (
    live_observation_ids,
    append_manual_observation,
    rebuild_manual_projection,
)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def test_manual_observation_is_append_only_and_projection_is_rebuildable() -> None:
    conn = _conn()
    first = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$10m",
        source_ref="TEST 10-K",
        as_of="2026-07-01T00:00:00+00:00",
        author="user",
    )
    second = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$12m",
        source_ref="TEST 10-Q",
        as_of="2026-08-01T00:00:00+00:00",
        author="user",
        supersedes_id=first,
    )

    assert first != second
    assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 2
    conn.execute("DELETE FROM manual_fields")
    assert rebuild_manual_projection(conn) == 2
    projected = conn.execute(
        "SELECT value, source_note, updated_at FROM manual_fields"
    ).fetchone()
    assert tuple(projected) == (
        "$12m",
        "TEST 10-Q",
        "2026-08-01T00:00:00+00:00",
    )


def test_manual_observation_requires_provenance_as_of_and_author() -> None:
    conn = _conn()
    try:
        append_manual_observation(
            conn,
            ticker="TEST",
            field_name="backlog",
            value="$10m",
            source_ref="",
            as_of="2026-07-01",
            author="user",
        )
    except ValueError as exc:
        assert "provenance" in str(exc)
    else:
        raise AssertionError("missing source must fail closed")


def test_late_delivery_of_older_observation_does_not_rewind_projection() -> None:
    conn = _conn()
    latest = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$12m",
        source_ref="TEST 10-Q",
        as_of="2026-08-01T00:00:00+00:00",
        author="user",
    )
    older = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$10m",
        source_ref="TEST 10-K",
        as_of="2026-07-01T00:00:00+00:00",
        author="user",
    )

    assert latest != older
    projected = conn.execute(
        "SELECT value, source_note, updated_at FROM manual_fields"
    ).fetchone()
    assert tuple(projected) == (
        "$12m",
        "TEST 10-Q",
        "2026-08-01T00:00:00+00:00",
    )
    assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 2


def test_manual_observation_normalizes_timezone_before_ordering_and_digest() -> None:
    conn = _conn()
    first = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$10m",
        source_ref="TEST filing",
        as_of="2026-07-01T10:00:00-05:00",
        author="user",
    )
    duplicate = append_manual_observation(
        conn,
        ticker="TEST",
        field_name="backlog",
        value="$10m",
        source_ref="TEST filing",
        as_of="2026-07-01T15:00:00+00:00",
        author="user",
    )

    assert duplicate == first
    assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1
    assert conn.execute(
        "SELECT updated_at FROM manual_fields WHERE ticker = 'TEST'"
    ).fetchone()[0] == "2026-07-01T15:00:00+00:00"


def test_manual_observation_rejects_secret_in_ordinary_source_field() -> None:
    conn = _conn()
    with pytest.raises(ValueError, match="secret-bearing"):
        append_manual_observation(
            conn,
            ticker="TEST",
            field_name="backlog",
            value="$10m",
            source_ref="Authorization: Bearer CANARY-DO-NOT-LEAK",
            as_of="2026-07-01T00:00:00+00:00",
            author="user",
        )
    assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 0


def test_second_unlinked_observation_for_the_same_period_is_rejected() -> None:
    """同一個 (ticker, field, as_of) 已經有生效紀錄時，新的一筆必須說出關係（2026-09-13）。

    ⚠ 為什麼不給預設：`supersedes_id` 是**單值**欄位（而且帶 FK），所以一旦長出兩條互不相干的
    鏈就**在資料模型上無法合併**，讀取端只能靠 `ORDER BY as_of DESC, recorded_at DESC` 猜哪一筆
    算數——猜不是宣告（L17-3②）。2026-09-13 實測全庫已經有 **14 組**這樣的紀錄。
    """
    conn = _conn()
    first = append_manual_observation(
        conn, ticker="TEST", field_name="backlog", value="$10m", source_ref="filing A",
        as_of="2026-07-01T00:00:00+00:00", author="user")
    with pytest.raises(ValueError, match="必須說出新紀錄與它們的關係|已經有 1 筆生效紀錄"):
        append_manual_observation(
            conn, ticker="TEST", field_name="backlog", value="$12m", source_ref="filing B",
            as_of="2026-07-01T00:00:00+00:00", author="user")
    # ①更正：指向舊的那一筆就放行。
    second = append_manual_observation(
        conn, ticker="TEST", field_name="backlog", value="$12m", source_ref="filing B",
        as_of="2026-07-01T00:00:00+00:00", author="user", supersedes_id=first)
    assert second != first
    assert live_observation_ids(conn, "TEST", "backlog", "2026-07-01") == [second]
    # ②並存：明示 allow_parallel 才可以（兩筆都算數，讀取端要自己處理）。
    third = append_manual_observation(
        conn, ticker="TEST", field_name="backlog", value="$13m", source_ref="filing C",
        as_of="2026-07-01T00:00:00+00:00", author="user", allow_parallel=True)
    assert set(live_observation_ids(conn, "TEST", "backlog", "2026-07-01")) == {second, third}


def test_different_as_of_is_not_a_duplicate() -> None:
    """不同期間的同一個欄位本來就該同時生效——把 as_of 漏掉會把它誤判成重複。

    ⚠ 實測（2026-09-13）：鍵不含 as_of 時全庫掃出 21 組「重複」，含 as_of 之後是 **14 組**
    ——那 7 組只是不同期間。
    """
    conn = _conn()
    fy24 = append_manual_observation(
        conn, ticker="TEST", field_name="backlog", value="$8m", source_ref="FY2024",
        as_of="2025-12-31T00:00:00+00:00", author="user")
    fy25 = append_manual_observation(
        conn, ticker="TEST", field_name="backlog", value="$10m", source_ref="FY2025",
        as_of="2026-12-31T00:00:00+00:00", author="user")
    assert fy24 != fy25
    assert live_observation_ids(conn, "TEST", "backlog", "2025-12-31") == [fy24]
    assert live_observation_ids(conn, "TEST", "backlog", "2026-12-31") == [fy25]
