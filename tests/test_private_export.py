from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.export import ExportError, export_full_sqlite, export_redacted_summary
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


def _store(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    private = repo / "library" / "private"
    initialize_private_root(private, repo_root=repo)
    store = DecisionStore.open(
        private / "decision_lab" / "decision_lab.db",
        private_root=private,
        repo_root=repo,
    )
    return store, repo, private


def test_redacted_export_contains_only_allowlisted_aggregate_contract(tmp_path: Path) -> None:
    store, repo, private = _store(tmp_path)
    try:
        cohort = store.ensure_cohort(
            dedupe_key="canary", company_id="co:test", research_ticker="TEST"
        )
        store.append_event(
            cohort_id=cohort.cohort_id,
            event_type="fixture",
            payload={"raw_text": "CANARY-DO-NOT-LEAK"},
            observed_at="2026-07-21T00:00:00+00:00",
        )
        target = export_redacted_summary(
            store, repo / "diagnostics" / "summary.json", repo_root=repo
        )
        text = target.read_text(encoding="utf-8")

        assert "CANARY-DO-NOT-LEAK" not in text
        assert "raw_text" not in text
        assert "counts" in text
    finally:
        store.close()


def test_full_export_is_rejected_outside_private_root(tmp_path: Path) -> None:
    store, repo, private = _store(tmp_path)
    try:
        with pytest.raises(Exception):
            export_full_sqlite(
                store.path,
                repo / "tracked-full.db",
                private_root=private,
                repo_root=repo,
            )
        target = export_full_sqlite(
            store.path,
            private / "exports" / "decision-lab.db",
            private_root=private,
            repo_root=repo,
        )
        assert target.is_file()
    finally:
        store.close()
