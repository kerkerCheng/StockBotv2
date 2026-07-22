from __future__ import annotations

import io
import json
from pathlib import Path

from decision_lab.cli import run
from decision_lab.execution import apply_live_override, prepare_managed_action
from tests.test_action_card import _decision
from tests.test_decision_execution import _store
from tests.test_operational_workflow import FixtureProvider, NOW


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


def _evaluate_args(format_name: str) -> list[str]:
    return [
        "evaluate-signal",
        "aleabitoreddit：Sivers CW laser 設計案可能量產",
        "--source-url",
        "https://aleabitoreddit.example/sivers",
        "--ticker",
        "SIVE.ST",
        "--company-id",
        "co:sivers_semiconductors",
        "--thesis",
        "Sivers 的 CW laser 設計案將轉為量產訂單。",
        "--catalyst",
        "客戶公布量產訂單。",
        "--disproof",
        "客戶 qualification 失敗。",
        "--expiry",
        "2026-12-31T00:00:00+00:00",
        "--as-of",
        NOW,
        "--intent",
        "paper",
        "--format",
        format_name,
    ]


def test_cli_evaluate_signal_json_and_markdown_share_audit_ids(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        json_out = io.StringIO()
        markdown_out = io.StringIO()
        assert run(
            _args(store, _evaluate_args("json")),
            stdout=json_out,
            provider=provider,
        ) == 0
        payload = json.loads(json_out.getvalue())
        assert run(
            _args(store, _evaluate_args("markdown")),
            stdout=markdown_out,
            provider=provider,
        ) == 0

        markdown = markdown_out.getvalue()
        assert payload["decision_id"] in markdown
        assert payload["context_digest"] in markdown
        assert payload["coverage_assessment_id"] in markdown
        assert "context_digest" not in " ".join(_evaluate_args("json"))
        assert "coverage_assessment_id" not in " ".join(_evaluate_args("json"))
        assert str(store.path) not in json_out.getvalue()
        assert str(store.path) not in markdown
    finally:
        store.close()


def test_cli_today_is_directly_executable_and_safe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        stdout = io.StringIO()
        code = run(
            _args(store, ["today", "--as-of", NOW, "--format", "json"]),
            stdout=stdout,
            provider=FixtureProvider(),
        )
        brief = json.loads(stdout.getvalue())

        assert code == 0
        assert brief["recommended_action"] in {"NO ACTION", "REVIEW", "TRADE", "HEDGE"}
        assert "action_needed" in brief
        assert str(store.path) not in stdout.getvalue()
    finally:
        store.close()


def test_cli_live_choice_and_fill_require_explicit_commands(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="operational-cli-fill")
        prepared = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.001, "reason": "使用者明確接受探索部位"},
            prepared_at="2026-07-21T12:00:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )

        missing_explicit = io.StringIO()
        assert run(
            _args(
                store,
                [
                    "record-fill",
                    decision.decision_id,
                    "--execution-ref",
                    "manual:no-explicit",
                    "--shares",
                    "10",
                    "--price",
                    "2",
                    "--currency",
                    "EUR",
                ],
            ),
            stdout=missing_explicit,
        ) != 0

        filled = io.StringIO()
        assert run(
            _args(
                store,
                [
                    "record-fill",
                    decision.decision_id,
                    "--execution-ref",
                    "manual:reported-fill",
                    "--shares",
                    "10",
                    "--price",
                    "2",
                    "--currency",
                    "EUR",
                    "--executed-at",
                    "2026-07-21T12:10:00+00:00",
                    "--explicit",
                ],
            ),
            stdout=filled,
        ) == 0
        assert json.loads(filled.getvalue())["fill_id"].startswith("lf_")
    finally:
        store.close()


def test_cli_choice_persists_confirmation_reference_as_an_audit_fact(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="operational-cli-choice")
        stdout = io.StringIO()
        assert run(
            _args(
                store,
                [
                    "record-choice",
                    decision.decision_id,
                    "--selected-weight",
                    "0",
                    "--decided-at",
                    "2026-07-21T12:10:00+00:00",
                    "--confirmation-ref",
                    "user:explicit-skip",
                    "--explicit",
                ],
            ),
            stdout=stdout,
        ) == 0
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        confirmations = [
            event
            for event in store.list_events(cohort_id)
            if event.event_type == "live_choice_confirmation"
        ]

        assert len(confirmations) == 1
        assert json.loads(stdout.getvalue())["choice_id"].startswith("lc_")
    finally:
        store.close()


def test_cli_redacts_sensitive_signal_and_provider_errors(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        stdout = io.StringIO()
        code = run(
            _args(
                store,
                [
                    "evaluate-signal",
                    "Authorization: Bearer CANARY-SECRET",
                    "--as-of",
                    NOW,
                    "--format",
                    "json",
                ],
            ),
            stdout=stdout,
            provider=FixtureProvider(resolved=False),
        )

        assert code == 2
        assert "CANARY-SECRET" not in stdout.getvalue()
        assert json.loads(stdout.getvalue())["status"] == "error"
    finally:
        store.close()
