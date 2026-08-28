from __future__ import annotations

import io
import json
from pathlib import Path

from decision_lab.cli import build_parser, run
from decision_lab.coverage import assess_coverage
from decision_lab.execution import assess_probe
from decision_lab.models import ATTENTION_STATES
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
        assert result["research_status"] == direct.research_status
        # CLI 輸出就是 `DecisionExecutionResult` 的 asdict；U7 之後只剩三個欄位，
        # 任何資本欄位重新長回來都會在這裡現形。
        assert set(result) == {"decision_id", "decision_digest", "research_status"}
        assert store.table_count("paper_events") == 0
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
        # `attention` 取代 U7 之前的 `action`：`TRADE`／`HEDGE` 是資本動作，
        # 系統既不給尺寸也不連 broker，說出那兩個詞等於宣稱做不到的授權。
        assert "action" not in card
        assert card["attention"] in ATTENTION_STATES
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


def test_public_help_promotes_operational_workflow() -> None:
    help_text = build_parser().format_help()

    for command in (
        "evaluate-signal",
        "reassess",
        "today",
        "card",
        "record-choice",
        "record-fill",
    ):
        assert command in help_text
    assert "correction" not in help_text
    assert "record-decision" not in help_text


def test_record_choice_still_exposes_user_sized_and_reason() -> None:
    """U7 只改了 help 文字：`--user-sized` 是使用者自訂尺寸的唯一入口，必須還在。

    系統不再輸出建議尺寸之後，這條路徑就是所有真實下單紀錄的走法；
    它若消失，唯一剩下的入口會是設計成例外的 `override`（L12 已踩過一次）。
    """

    args = build_parser().parse_args([
        "record-choice", "pd_x",
        "--selected-weight", "0.01",
        "--confirmation-ref", "manual:broker-1",
        "--decided-at", "2026-08-28T12:00:00+00:00",
        "--explicit",
        "--user-sized",
        "--reason", "依自己的判斷定尺寸",
    ])
    assert args.user_sized is True
    assert args.explicit is True
    assert args.reason == "依自己的判斷定尺寸"


def test_reassess_parser_exposes_gap_research_overrides() -> None:
    args = build_parser().parse_args([
        "reassess", "pd_old",
        "--catalyst", "volume production",
        "--disproof", "qualification slips",
        "--expiry", "2026-08-22T12:00:00+00:00",
    ])
    assert args.catalyst == "volume production"
    assert args.disproof == "qualification slips"
    assert args.expiry == "2026-08-22T12:00:00+00:00"
