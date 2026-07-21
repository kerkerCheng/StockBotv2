from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


def _store(tmp_path: Path) -> tuple[DecisionStore, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    db_path = private_root / "decision_lab" / "decision_lab.db"
    return (
        DecisionStore.open(
            db_path,
            private_root=private_root,
            repo_root=repo,
        ),
        repo,
        db_path,
    )


def test_fresh_store_has_unified_cohort_paper_truth_and_projection_schema(
    tmp_path: Path,
) -> None:
    store, _repo, db_path = _store(tmp_path)
    try:
        tables = store.table_names()
    finally:
        store.close()

    assert db_path.is_file()
    assert {
        "decision_cohorts",
        "decision_events",
        "paper_events",
        "paper_position_projection",
        "decision_store_meta",
    } <= tables


def test_append_signal_uses_server_id_digest_and_is_idempotent(tmp_path: Path) -> None:
    store, _repo, _db_path = _store(tmp_path)
    payload = {
        "claim": "CW laser bottleneck is economically relevant",
        "source": "fixture://signal/1",
    }
    try:
        cohort = store.ensure_cohort(
            dedupe_key="claim:cw-laser",
            company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
        )
        first = store.append_event(
            cohort_id=cohort.cohort_id,
            event_type="qualified_signal",
            payload=payload,
            observed_at="2026-07-21T00:00:00+00:00",
        )
        retry = store.append_event(
            cohort_id=cohort.cohort_id,
            event_type="qualified_signal",
            payload=payload,
            observed_at="2026-07-21T00:00:00+00:00",
        )
    finally:
        store.close()

    assert cohort.cohort_id.startswith("dc_")
    assert first.event_id.startswith("de_")
    assert len(first.payload_digest) == 64
    assert retry == first


def test_failed_append_rolls_back_without_orphan_event(tmp_path: Path) -> None:
    store, _repo, db_path = _store(tmp_path)
    try:
        try:
            store.append_event(
                cohort_id="dc_" + "0" * 32,
                event_type="qualified_signal",
                payload={"claim": "orphan"},
                observed_at="2026-07-21T00:00:00+00:00",
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("foreign-key violation must fail")
    finally:
        store.close()

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM decision_events").fetchone()[0] == 0
    finally:
        conn.close()


def test_private_store_write_does_not_touch_tracked_runtime_paths(tmp_path: Path) -> None:
    store, repo, _db_path = _store(tmp_path)
    try:
        cohort = store.ensure_cohort(
            dedupe_key="claim:fixture",
            company_id="co:coherent",
            research_ticker="COHR",
        )
        store.append_event(
            cohort_id=cohort.cohort_id,
            event_type="qualified_signal",
            payload={"claim": "fixture"},
            observed_at="2026-07-21T00:00:00+00:00",
        )
    finally:
        store.close()

    assert not (repo / "engine_c" / "stockbot.db").exists()
    assert not (repo / "paper_portfolio" / "transactions.csv").exists()


def test_missing_initialized_authority_fails_closed_instead_of_creating_empty_db(
    tmp_path: Path,
) -> None:
    store, repo, db_path = _store(tmp_path)
    private_root = repo / "library" / "private"
    store.close()
    db_path.unlink()

    with pytest.raises(RuntimeError, match="authority is missing"):
        DecisionStore.open(
            db_path,
            private_root=private_root,
            repo_root=repo,
        )
    assert not db_path.exists()
