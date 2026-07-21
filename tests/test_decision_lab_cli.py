from __future__ import annotations

import io
import json
from pathlib import Path

from decision_lab.cli import build_parser, run
from decision_lab.coverage import assess_coverage
from decision_lab.execution import assess_probe
from tests.test_decision_execution import _bundle, _store
from tests.test_probe_sizing import _assessment


def _persisted_coverage(store, key="cli"):
    bundle, _ = _bundle(store, key)
    coverage = assess_coverage(
        store,
        bundle,
        catalyst="Named production order",
        disproof="Customer qualification fails",
        expiry="2026-12-31T00:00:00+00:00",
        decision_relevance=9,
        falsifiability=8,
        information_value=8,
    )
    return bundle, coverage


def _args(store, command):
    private_root = store.path.parents[1]
    repo_root = private_root.parents[1]
    return [
        "--store",
        str(store.path),
        "--private-root",
        str(private_root),
        "--repo-root",
        str(repo_root),
        *command,
    ]


def test_cli_assess_matches_application_primitive_and_retry_is_idempotent(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _persisted_coverage(store)
        direct = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="cli:same",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        payload = {
            "context_digest": bundle.digest,
            "coverage_assessment_id": coverage.assessment_id,
            "assessment": _assessment(),
            "idempotency_key": "cli:same",
            "effective_at": "2026-07-21T12:00:00+00:00",
        }
        stdout = io.StringIO()
        code = run(
            _args(store, ["assess", "--input", "-"]),
            stdin=io.StringIO(json.dumps(payload)),
            stdout=stdout,
        )
        result = json.loads(stdout.getvalue())

        assert code == 0
        assert result["decision_id"] == direct.decision_id
        assert result["decision_digest"] == direct.decision_digest
        assert result["paper_target"] == direct.paper_target
        assert store.table_count("paper_events") == 1
    finally:
        store.close()


def test_cli_card_is_read_only_and_returns_same_structured_contract(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _persisted_coverage(store, "cli-card")
        decision = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="cli:card",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        before = store.table_count("paper_events")
        stdout = io.StringIO()

        code = run(
            _args(store, ["card", decision.decision_id]),
            stdin=io.StringIO(),
            stdout=stdout,
        )
        card = json.loads(stdout.getvalue())

        assert code == 0
        assert card["decision_id"] == decision.decision_id
        assert card["action"] in {"NO_ACTION", "REVIEW", "TRADE", "HEDGE"}
        assert store.table_count("paper_events") == before
    finally:
        store.close()


def test_cli_redacts_errors_and_never_echoes_canary_secret(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        stdout = io.StringIO()
        code = run(
            _args(store, ["assess", "--input", "-"]),
            stdin=io.StringIO(
                json.dumps({"api_token": "CANARY-DO-NOT-LEAK"})
            ),
            stdout=stdout,
        )

        assert code == 2
        assert "CANARY-DO-NOT-LEAK" not in stdout.getvalue()
        assert json.loads(stdout.getvalue())["status"] == "error"
    finally:
        store.close()


def test_public_help_only_promotes_assess_and_card() -> None:
    help_text = build_parser().format_help()

    assert "assess" in help_text
    assert "card" in help_text
    assert "correction" not in help_text
    assert "record-decision" not in help_text
