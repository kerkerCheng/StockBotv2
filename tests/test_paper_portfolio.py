"""Prospective paper portfolio remains append-only, reproducible, and separate."""
from __future__ import annotations

import csv
import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from paper_portfolio.ledger import (
    EVENT_FIELDS,
    LedgerError,
    append_event,
    create_event,
    initialize_portfolio,
    read_events,
    replay,
    value_portfolio,
    write_review,
)
from thesis.investment_policy import calculate_position_limit, load_policy


def _root(tmp_path: Path, *, nav: float = 100.0, currency: str = "USD") -> Path:
    root = tmp_path / "paper"
    initialize_portfolio(base_currency=currency, initial_nav=nav, root=root)
    return root


def _decision(nav: float = 100.0) -> dict:
    return calculate_position_limit(
        total_nav=nav,
        high_risk_budget=nav,
        conviction=5,
        analyst_coverage_count=None,
    )


def _event(
    *,
    event_type: str,
    target: float,
    changed: float,
    price: float = 10,
    currency: str = "USD",
    fx: float = 1,
    fx_ref: str = "USD=USD",
    ticker: str = "TEST",
    timestamp: datetime | None = None,
    event_id: str | None = None,
    corrects: str | None = None,
    benchmark: str | None = None,
    decision_nav: float = 100.0,
) -> dict[str, str]:
    decision = _decision(decision_nav)
    event = create_event(
        ticker=ticker,
        event_type=event_type,
        target_weight=target,
        changed_weight=changed,
        price=price,
        price_currency=currency,
        fx_rate_to_base=fx,
        fx_ref=fx_ref,
        thesis_version="test-v1",
        thesis_hash="a" * 64,
        policy_version=load_policy()["policy_version"],
        policy_decision=decision,
        expected_horizon="12 months",
        disproof_condition="Customer cancels qualification.",
        disproof_ref="thesis/test.md#disproof",
        reason="Prospective test decision.",
        decision_author="test-suite",
        benchmark_ticker=benchmark,
        corrects_event_id=corrects,
    )
    if event_id is not None:
        event["event_id"] = event_id
    if timestamp is not None:
        event["timestamp_utc"] = timestamp.isoformat()
    return event


def test_init_requires_explicit_currency_and_virtual_nav(tmp_path: Path) -> None:
    with pytest.raises(LedgerError):
        initialize_portfolio(base_currency="", initial_nav=100, root=tmp_path / "a")
    with pytest.raises(LedgerError):
        initialize_portfolio(base_currency="USD", initial_nav=0, root=tmp_path / "b")

    config = initialize_portfolio(
        base_currency="USD", initial_nav=100, root=tmp_path / "standard"
    )

    assert config["initial_nav"] == 100
    assert "actual" not in json.dumps(config).lower()


def test_open_add_trim_close_replays_cash_and_realized_pnl(tmp_path: Path) -> None:
    root = _root(tmp_path)
    start = datetime(2026, 7, 16, tzinfo=timezone.utc)
    events = [
        _event(event_type="open", target=.03, changed=.03, price=10, timestamp=start),
        _event(event_type="add", target=.05, changed=.026, price=8,
               timestamp=start + timedelta(seconds=1)),
        _event(event_type="trim", target=.04, changed=-.0225, price=10,
               timestamp=start + timedelta(seconds=2)),
        _event(event_type="close", target=0, changed=-.048, price=12,
               timestamp=start + timedelta(seconds=3)),
    ]

    state = replay(events, root=root)

    assert state["positions"] == {}
    assert state["cash"] == pytest.approx(101.45)
    assert state["realized_pnl"] == pytest.approx(1.45)


def test_append_rejects_bad_transition_duplicate_and_policy_breach(tmp_path: Path) -> None:
    root = _root(tmp_path)
    first = _event(event_type="open", target=.03, changed=.03)
    append_event(first, root=root)

    with pytest.raises(LedgerError, match="duplicate event_id"):
        append_event(first, root=root)
    with pytest.raises(LedgerError, match="exceeds frozen policy"):
        replay([_event(event_type="open", target=.06, changed=.06)], root=root)
    empty = _root(tmp_path / "other")
    with pytest.raises(LedgerError, match="illegal state transition"):
        replay([_event(event_type="close", target=0, changed=0)], root=empty)


def test_append_rejects_forged_policy_decision(tmp_path: Path) -> None:
    root = _root(tmp_path)
    event = _event(event_type="open", target=.03, changed=.03)
    decision = json.loads(event["policy_decision"])
    decision["maximum_position"] = 99
    event["policy_decision"] = json.dumps(decision)

    with pytest.raises(LedgerError, match="does not reproduce"):
        append_event(event, root=root)


def test_replay_rejects_non_monotonic_time_and_insufficient_cash(tmp_path: Path) -> None:
    root = _root(tmp_path)
    start = datetime(2026, 7, 16, tzinfo=timezone.utc)
    later = _event(event_type="open", target=.03, changed=.03, timestamp=start)
    earlier = _event(
        event_type="add", target=.04, changed=.01, timestamp=start - timedelta(seconds=1)
    )
    with pytest.raises(LedgerError, match="timestamps must be monotonic"):
        replay([later, earlier], root=root)

    oversized = _decision()
    oversized["maximum_position"] = 100
    one = _event(event_type="open", target=.6, changed=.6, ticker="ONE")
    two = _event(event_type="open", target=.6, changed=.6, ticker="TWO")
    one["policy_decision"] = json.dumps(oversized)
    two["policy_decision"] = json.dumps(oversized)
    with pytest.raises(LedgerError, match="available cash"):
        replay([one, two], root=root)


def test_correction_and_reversal_preserve_original_rows(tmp_path: Path) -> None:
    root = _root(tmp_path)
    start = datetime(2026, 7, 16, tzinfo=timezone.utc)
    original = _event(event_type="open", target=.04, changed=.04, timestamp=start)
    correction = _event(
        event_type="correction",
        target=.03,
        changed=.03,
        timestamp=start + timedelta(seconds=1),
        corrects=original["event_id"],
    )

    corrected = replay([original, correction], root=root)
    reversed_state = replay(
        [
            original,
            _event(
                event_type="reversal",
                target=0,
                changed=0,
                timestamp=start + timedelta(seconds=1),
                corrects=original["event_id"],
            ),
        ],
        root=root,
    )

    assert corrected["positions"]["TEST"]["units"] == pytest.approx(.3)
    assert reversed_state["positions"] == {}
    assert reversed_state["cash"] == 100


def test_foreign_position_valuation_and_optional_benchmark(tmp_path: Path) -> None:
    root = _root(tmp_path)
    event = _event(
        event_type="open",
        target=.05,
        changed=.05,
        price=100,
        currency="SEK",
        fx=.1,
        fx_ref="2026-07-16 SEKUSD=0.1",
        ticker="SIVE.ST",
        benchmark="SOXX",
    )

    valued = value_portfolio(
        [event],
        prices={"SIVE.ST": {"price": 120, "currency": "SEK"}},
        fx_rates={"SEK": {"rate": .1, "ref": "latest"}},
        benchmark_prices={"SOXX": {"start": 100, "current": 110}},
        root=root,
    )
    unknown = value_portfolio(
        [event],
        prices={"SIVE.ST": {"price": 120, "currency": "SEK"}},
        fx_rates={},
        root=root,
    )

    assert valued["valuation_status"] == "available"
    assert valued["nav"] == pytest.approx(101)
    assert valued["unrealized_pnl"] == pytest.approx(1)
    assert valued["benchmark_context"]["SOXX"]["return"] == pytest.approx(.1)
    assert unknown["valuation_status"] == "unknown"
    assert unknown["missing_market_data"] == ["fx:SEK->USD"]


def test_foreign_open_review_close_is_fully_prospective(tmp_path: Path) -> None:
    root = _root(tmp_path)
    start = datetime(2026, 7, 16, tzinfo=timezone.utc)
    opened = _event(
        event_type="open",
        target=.05,
        changed=.05,
        price=100,
        currency="SEK",
        fx=.1,
        fx_ref="SEKUSD@open",
        ticker="SIVE.ST",
        timestamp=start,
    )
    review = write_review(
        ticker="SIVE.ST",
        review_date="2026-07-16",
        thesis_ref="thesis/sive-v1.md sha256:abc",
        evidence_manifest_ref="thesis/sive-v1.evidence.json",
        new_evidence="No disproof evidence since open.",
        disproof_status="not_triggered",
        would_open_today="yes",
        decision="close for synthetic verification",
        pnl_context="event-price gain pending close",
        benchmark_context="SOXX optional; omitted in this synthetic run",
        root=root,
    )
    closed = _event(
        event_type="close",
        target=0,
        changed=-.06,
        price=120,
        currency="SEK",
        fx=.1,
        fx_ref="SEKUSD@close",
        ticker="SIVE.ST",
        timestamp=start + timedelta(seconds=1),
    )

    state = replay([opened, closed], root=root)

    assert review.exists()
    assert "Would open today" in review.read_text(encoding="utf-8")
    assert state["positions"] == {}
    assert state["cash"] == pytest.approx(101)
    assert state["realized_pnl"] == pytest.approx(1)


def test_append_is_single_row_and_transactions_are_only_position_truth(tmp_path: Path) -> None:
    root = _root(tmp_path)
    event = _event(event_type="open", target=.03, changed=.03)

    append_event(event, root=root)

    assert len(read_events(root)) == 1
    with (root / "transactions.csv").open("r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == EVENT_FIELDS
    assert not (root / "positions.csv").exists()


def test_event_identity_and_timestamp_are_not_public_inputs() -> None:
    parameters = inspect.signature(create_event).parameters

    assert "event_id" not in parameters
    assert "timestamp_utc" not in parameters


def test_append_accepts_frozen_current_nav_instead_of_initial_nav(tmp_path: Path) -> None:
    root = _root(tmp_path)
    append_event(_event(event_type="open", target=.03, changed=.03), root=root)

    second = _event(
        event_type="open",
        target=.03,
        changed=.03,
        ticker="NEXT",
        decision_nav=97.0,
    )
    state = append_event(second, root=root)

    assert state["positions"]["NEXT"]["units"] == pytest.approx(.291)


def test_append_rejects_backdated_event(tmp_path: Path) -> None:
    root = _root(tmp_path)
    event = _event(event_type="open", target=.03, changed=.03)
    event["timestamp_utc"] = "2020-01-01T00:00:00+00:00"

    with pytest.raises(LedgerError, match="program-generated timestamp"):
        append_event(event, root=root)


def test_correction_retains_original_policy_after_policy_changes(
    tmp_path: Path, monkeypatch
) -> None:
    root = _root(tmp_path)
    original = _event(event_type="open", target=.04, changed=.04)
    append_event(original, root=root)
    correction = _event(
        event_type="correction",
        target=.03,
        changed=.03,
        corrects=original["event_id"],
    )
    correction["policy_version"] = original["policy_version"]
    correction["policy_decision"] = original["policy_decision"]
    monkeypatch.setattr(
        "thesis.investment_policy.load_policy",
        lambda: {**load_policy(), "policy_version": "future-policy"},
    )

    state = append_event(correction, root=root)

    assert state["positions"]["TEST"]["units"] == pytest.approx(.3)


def test_initialization_failure_does_not_publish_initialized_config(tmp_path: Path) -> None:
    root = tmp_path / "paper"
    root.mkdir()
    (root / "config.json").write_text('{"created_at": null}\n', encoding="utf-8")
    (root / "transactions.csv").write_text("bad,header\n", encoding="utf-8")

    with pytest.raises(LedgerError, match="header"):
        initialize_portfolio(base_currency="USD", initial_nav=100, root=root)

    assert json.loads((root / "config.json").read_text(encoding="utf-8")) == {
        "created_at": None
    }


def test_repository_legacy_note_is_not_a_transaction() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    note = repo_root / "paper_portfolio" / "reviews" / "2026-07-12-sive-legacy-decision.md"
    transactions = (repo_root / "paper_portfolio" / "transactions.csv").read_text(
        encoding="utf-8"
    )

    assert "legacy_observation" in note.read_text(encoding="utf-8")
    assert transactions.count("\n") == 1
    assert "SIVE" not in transactions
