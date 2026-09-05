"""Apply versioned Engine C Postgres migrations exactly once."""
from __future__ import annotations

import argparse
from pathlib import Path

from engine_c import db


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
REQUIRED_MIGRATION = "20260716_add_consensus_coverage.sql"
REQUIRED_MIGRATIONS = (
    REQUIRED_MIGRATION,
    "20260721_add_manual_observations.sql",
    "20260721_add_probe_financial_baseline.sql",
    "20260728_add_technical_observations.sql",
    "20260729_add_technical_returns.sql",
    "20260905_add_consensus_estimates.sql",
)
REQUIRED_TABLES = (
    "consensus_coverage_observations",
    "manual_observations",
    "technical_observations",
    "consensus_estimates",
)
REQUIRED_FINANCIAL_COLUMNS = (
    "cash_and_equivalents",
    "total_debt",
    "free_cash_flow_ttm",
)


def apply_migrations(conn, *, migrations_dir: str | Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending .sql files transactionally and return their version names."""

    directory = Path(migrations_dir)
    if not directory.is_dir():
        raise RuntimeError(f"migration directory does not exist: {directory}")
    migration_paths = sorted(directory.glob("*.sql"))
    if not migration_paths:
        raise RuntimeError(f"no migration SQL files found in: {directory}")
    applied: list[str] = []
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS engine_c_schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("SELECT version FROM engine_c_schema_migrations")
            known = {row[0] for row in cursor.fetchall()}
            for path in migration_paths:
                if path.name in known:
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO engine_c_schema_migrations (version) VALUES (%s)",
                    (path.name,),
                )
                applied.append(path.name)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return applied


def verify_required_schema(conn) -> None:
    """Fail closed unless every required migration and target table is observable."""

    with conn.cursor() as cursor:
        for migration in REQUIRED_MIGRATIONS:
            cursor.execute(
                "SELECT version FROM engine_c_schema_migrations WHERE version = %s",
                (migration,),
            )
            if cursor.fetchone() != (migration,):
                raise RuntimeError(f"required migration is not recorded: {migration}")
        for table_name in REQUIRED_TABLES:
            cursor.execute("SELECT to_regclass(%s)", (table_name,))
            table = cursor.fetchone()
            if not table or table[0] is None:
                raise RuntimeError(f"{table_name} table is missing")
        for column_name in REQUIRED_FINANCIAL_COLUMNS:
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'financial_snapshots' AND column_name = %s
                """,
                (column_name,),
            )
            if cursor.fetchone() != (column_name,):
                raise RuntimeError(
                    f"financial_snapshots.{column_name} column is missing"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if not db._use_postgres():
        raise SystemExit("Set POSTGRES_DSN or POSTGRES_HOST before running migrations")
    conn = db.get_conn()
    try:
        applied = apply_migrations(conn)
        verify_required_schema(conn)
    finally:
        conn.close()
    print(f"applied {len(applied)} migration(s): {', '.join(applied) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
