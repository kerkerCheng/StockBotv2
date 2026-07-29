"""Postgres migrations are versioned, idempotent, and transactional."""
from __future__ import annotations

from pathlib import Path

import pytest

from engine_c.migrate import (
    REQUIRED_MIGRATION,
    REQUIRED_MIGRATIONS,
    apply_migrations,
    verify_required_schema,
)


class FakeCursor:
    def __init__(self, known=(), fetchone_values=()):
        self.known = list(known)
        self.fetchone_values = list(fetchone_values)
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return [(name,) for name in self.known]

    def fetchone(self):
        return self.fetchone_values.pop(0) if self.fetchone_values else None


class FakeConnection:
    def __init__(self, known=(), fetchone_values=()):
        self.cursor_instance = FakeCursor(known, fetchone_values)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_coverage_migration_is_applied_once(tmp_path: Path) -> None:
    migration = tmp_path / "001_coverage.sql"
    migration.write_text("CREATE TABLE coverage(id INTEGER);", encoding="utf-8")
    conn = FakeConnection()

    assert apply_migrations(conn, migrations_dir=tmp_path) == [migration.name]
    assert conn.commits == 1
    assert any(params == (migration.name,) for _, params in conn.cursor_instance.executed)

    already = FakeConnection(known=[migration.name])
    assert apply_migrations(already, migrations_dir=tmp_path) == []
    assert not any(
        "CREATE TABLE coverage" in sql for sql, _ in already.cursor_instance.executed
    )


def test_repository_coverage_migration_has_idempotent_postgres_ddl() -> None:
    path = Path(__file__).resolve().parents[1] / "engine_c" / "migrations" / (
        "20260716_add_consensus_coverage.sql"
    )
    sql = path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS consensus_coverage_observations" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_coverage_ticker_date" in sql
    assert "manual_required' AND analyst_count IS NULL" in sql


def test_repository_manual_observation_migration_has_idempotent_postgres_ddl() -> None:
    path = Path(__file__).resolve().parents[1] / "engine_c" / "migrations" / (
        "20260721_add_manual_observations.sql"
    )
    sql = path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS manual_observations" in sql
    assert "payload_digest VARCHAR(64) NOT NULL UNIQUE" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_manual_observation_field_time" in sql


def test_repository_technical_migration_has_append_only_postgres_ddl() -> None:
    path = Path(__file__).resolve().parents[1] / "engine_c" / "migrations" / (
        "20260728_add_technical_observations.sql"
    )
    sql = path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS technical_observations" in sql
    assert "payload_digest VARCHAR(64) NOT NULL UNIQUE" in sql
    assert "idx_technical_benchmark_session" in sql


def test_repository_technical_returns_migration_is_idempotent() -> None:
    path = Path(__file__).resolve().parents[1] / "engine_c" / "migrations" / (
        "20260729_add_technical_returns.sql"
    )
    sql = path.read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS return_1d" in sql
    assert "ADD COLUMN IF NOT EXISTS return_5d" in sql
    assert "ADD COLUMN IF NOT EXISTS return_20d" in sql


def test_missing_or_empty_migration_directory_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="does not exist"):
        apply_migrations(FakeConnection(), migrations_dir=tmp_path / "missing")
    with pytest.raises(RuntimeError, match="no migration SQL"):
        apply_migrations(FakeConnection(), migrations_dir=tmp_path)


def test_required_migration_and_table_are_verified() -> None:
    healthy = FakeConnection(
        fetchone_values=[
            *((migration,) for migration in REQUIRED_MIGRATIONS),
            ("consensus_coverage_observations",),
            ("manual_observations",),
            ("technical_observations",),
            ("cash_and_equivalents",),
            ("total_debt",),
            ("free_cash_flow_ttm",),
        ]
    )
    verify_required_schema(healthy)

    missing = FakeConnection(fetchone_values=[None])
    with pytest.raises(RuntimeError, match="required migration"):
        verify_required_schema(missing)

    missing_table = FakeConnection(
        fetchone_values=[
            *((migration,) for migration in REQUIRED_MIGRATIONS),
            ("consensus_coverage_observations",),
            None,
        ]
    )
    with pytest.raises(RuntimeError, match="manual_observations table"):
        verify_required_schema(missing_table)

    missing_column = FakeConnection(
        fetchone_values=[
            *((migration,) for migration in REQUIRED_MIGRATIONS),
            ("consensus_coverage_observations",),
            ("manual_observations",),
            ("technical_observations",),
            None,
        ]
    )
    with pytest.raises(RuntimeError, match="cash_and_equivalents"):
        verify_required_schema(missing_column)

    assert REQUIRED_MIGRATION == REQUIRED_MIGRATIONS[0]
