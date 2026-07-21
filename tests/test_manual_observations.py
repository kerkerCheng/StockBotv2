from __future__ import annotations

import sqlite3

import pytest

from engine_c.db import _ensure_sqlite_schema
from engine_c.manual_observations import (
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
