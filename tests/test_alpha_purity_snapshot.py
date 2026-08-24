from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

from identity.registry import CompanyIdentity, IdentityRegistry
from scripts.alpha_purity_snapshot import build_snapshot, run
from storage.relational import PrivateStorageVerificationUnavailable


def _registry() -> IdentityRegistry:
    return IdentityRegistry(
        version=1,
        companies=(
            CompanyIdentity(
                company_id="co:iqe",
                research_ticker="IQE.L",
                market_currency="GBP",
                market_quote_unit="GBp",
            ),
            CompanyIdentity(
                company_id="co:poet",
                research_ticker="POET",
                market_currency="USD",
                market_quote_unit="USD",
            ),
        ),
    )


def _database(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE financial_snapshots (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            snapshot_date TEXT,
            price REAL,
            shares_outstanding INTEGER,
            analyst_target_count INTEGER,
            fetched_at TEXT
        );
        CREATE TABLE consensus_coverage_observations (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            observation_date TEXT,
            analyst_count INTEGER,
            source TEXT,
            data_status TEXT,
            fetched_at TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO financial_snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "IQE.L", "2026-08-24", 44.95, 1_331_032_836, 3, "2026-08-24T01:00:00Z"),
            (2, "POET", "2026-08-24", 8.25, 173_058_088, None, "2026-08-24T01:00:00Z"),
        ],
    )
    conn.executemany(
        "INSERT INTO consensus_coverage_observations VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "IQE.L", "2026-08-24", 3, "yfinance", "observed", "2026-08-24T01:00:00Z"),
            (2, "POET", "2026-08-24", None, "yfinance", "manual_required", "2026-08-24T01:00:00Z"),
        ],
    )
    conn.commit()
    return conn


def test_snapshot_normalizes_gbp_minor_unit_and_preserves_manual_required(
    tmp_path: Path,
) -> None:
    conn = _database(tmp_path / "engine-c.db")

    payload = build_snapshot(conn, ["IQE.L", "POET"], registry=_registry())

    iqe, poet = payload["rows"]
    assert iqe["settlement_price"] == "0.4495"
    assert iqe["market_cap"] == {
        "amount": "598299259.7820",
        "currency": "GBP",
    }
    assert iqe["analyst_count"] == 3
    assert iqe["status"] == "ok"
    assert poet["analyst_count"] is None
    assert poet["analyst_status"] == "manual_required"
    assert "analyst_count_manual_required" in poet["blockers"]
    conn.close()


def test_cli_reads_sqlite_in_ro_mode_without_exposing_authority_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-secret-engine-c.db"
    _database(path).close()
    stdout = io.StringIO()

    exit_code = run(
        ["--format", "json", "--tickers", "IQE.L"],
        stdout=stdout,
        path_resolver=lambda: path,
        registry_resolver=_registry,
    )

    assert exit_code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["rows"][0]["market_cap"]["currency"] == "GBP"
    assert str(path) not in stdout.getvalue()


def test_cli_distinguishes_acl_verification_unavailable_from_invalid_acl() -> None:
    stdout = io.StringIO()

    def unavailable() -> Path:
        raise PrivateStorageVerificationUnavailable("sandbox cannot inspect ACL")

    exit_code = run(
        ["--format", "json", "--tickers", "IQE.L"],
        stdout=stdout,
        path_resolver=unavailable,
        registry_resolver=_registry,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 2
    assert payload["failure_class"] == "private_acl_verification_unavailable"
    assert "未判定 ACL 不合格" in payload["message"]
    assert "sandbox cannot inspect ACL" not in stdout.getvalue()
