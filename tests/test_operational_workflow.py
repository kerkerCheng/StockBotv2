from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from decision_lab.workflow import EvaluationRequest, evaluate_signal, reassess
from decision_lab.workflow_ports import AuthoritySnapshot, IdentityAuthority
from tests.test_decision_context import complete_inputs
from tests.test_decision_execution import _store
from tests.test_probe_sizing import _assessment


NOW = "2026-07-21T12:00:00+00:00"


class FixtureProvider:
    def __init__(self, *, resolved: bool = True, inputs: dict | None = None):
        self.resolved = resolved
        self.inputs = deepcopy(inputs or complete_inputs())
        self.snapshot_calls = 0

    def resolve_identity(self, **_hints) -> IdentityAuthority:
        if not self.resolved:
            return IdentityAuthority(
                status="unresolved_identity",
                blockers=("unresolved_identity",),
            )
        identity = self.inputs["identity"]
        return IdentityAuthority(status="resolved", **identity)

    def snapshot(self, *, identity, evaluation_at) -> AuthoritySnapshot:
        del evaluation_at
        self.snapshot_calls += 1
        if not self.resolved:
            return AuthoritySnapshot(
                identity=identity,
                evidence={
                    "status": "unresolved_identity",
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                    "blockers": ["unresolved_identity"],
                },
                financial={"status": "missing"},
                market={"status": "missing"},
                fx={"status": "missing"},
                holdings={"status": "unavailable"},
                statuses={
                    "identity": "unresolved_identity",
                    "graph": "unresolved_identity",
                    "financial": "missing",
                    "market": "missing",
                    "fx": "missing",
                    "holdings": "unavailable",
                },
            )
        return AuthoritySnapshot(
            identity=identity,
            evidence=deepcopy(self.inputs["evidence"]),
            financial=deepcopy(self.inputs["financial"]),
            market=deepcopy(self.inputs["market"]),
            fx=deepcopy(self.inputs["fx"]),
            holdings=deepcopy(self.inputs["holdings"]),
            statuses={
                "identity": "resolved",
                "graph": "available",
                "financial": "observed",
                "market": "observed",
                "fx": "observed",
                "holdings": "available",
            },
        )

    def current_holdings(self, *, evaluation_at):
        del evaluation_at
        return deepcopy(self.inputs["holdings"])


def _request(**overrides) -> EvaluationRequest:
    payload = {
        "raw_signal": "aleabitoreddit：Sivers 的 CW laser 設計案可能進入量產。",
        "source_url": "https://aleabitoreddit.example/sivers-cw-laser",
        "ticker_hint": "SIVE.ST",
        "company_id_hint": "co:sivers_semiconductors",
        "thesis": "Sivers 的 CW laser 客戶設計案將轉為量產訂單。",
        "catalyst": "客戶公布量產訂單。",
        "disproof": "客戶 qualification 失敗。",
        "expiry": "2026-12-31T00:00:00+00:00",
        "as_of": NOW,
        "execution_intent": "paper",
        "direction": "long",
        "source_id": "aleabitoreddit",
        "source_traced": True,
        "evidence_tier": 3,
        "assessment": _assessment(),
    }
    payload.update(overrides)
    return EvaluationRequest(**payload)


def _partial_metadata_inputs() -> dict:
    """真實 registry 內有 ticker 但缺 execution metadata 的公司（co:broadcom/AVGO）。

    大多數 registry 條目都是這種狀態；U2 前這會在 context freeze 階段拋
    ValueError（context identity does not match cohort authority）。
    """
    inputs = deepcopy(complete_inputs(rows=[]))
    inputs["identity"] = {
        "company_id": "co:broadcom",
        "research_ticker": "AVGO",
        "execution_symbol": "AVGO",
        "market_currency": None,
        "execution_currency": None,
        "execution_venue": None,
    }
    inputs["financial"]["ticker"] = "AVGO"
    inputs["market"]["ticker"] = "AVGO"
    return inputs


def test_partial_execution_metadata_captures_without_crash(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider(inputs=_partial_metadata_inputs())
    try:
        # 缺 execution metadata 不得讓 evaluate-signal 崩潰——是 lane blocker，
        # 不是 identity 失敗（plan R14／KTD3）。
        result = evaluate_signal(
            store,
            provider,
            _request(
                ticker_hint="AVGO",
                company_id_hint="co:broadcom",
                execution_intent="research",
            ),
        )

        assert result["status"] == "completed_with_blockers"
        assert result["action_card"]["action"] == "REVIEW"
        # 核心 identity 存活（company_id 有綁定，coverage 不報 identity_unresolved）。
        bundle = store.get_context_bundle(result["context_digest"])
        frozen_identity = bundle.payload["identity"]
        assert frozen_identity["status"] == "resolved"
        assert frozen_identity["company_id"] == "co:broadcom"
        assert "identity_unresolved" not in result["blockers"]
        # execution metadata 缺失以 identity blocker 呈現、且封鎖資本 lane。
        assert "market_currency_missing" in frozen_identity["blockers"]
        assert result["action_card"]["paper"]["max_supported_position"] == 0
        assert result["action_card"]["live"]["supported_range"] == [0.0, 0.0]
    finally:
        store.close()


def test_sive_signal_runs_to_auditable_card_and_retry_is_idempotent(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        first = evaluate_signal(store, provider, _request())
        retry = evaluate_signal(store, provider, _request())

        assert first["decision_id"] == retry["decision_id"]
        assert first["context_digest"] == retry["context_digest"]
        assert first["paper_event_id"] == retry["paper_event_id"]
        assert first["paper_event_id"] is not None
        assert store.table_count("paper_events") == 1
        assert store.table_count("shadow_observations") == 1
        assert first["action_card"]["decision_id"] == first["decision_id"]
        assert first["action_card"]["paper"]["funded"] is True
        assert "execution_intent_paper_only" in first["blockers"]
    finally:
        store.close()


def test_raw_only_unresolved_signal_still_creates_zero_size_card_and_work_order(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        result = evaluate_signal(
            store,
            FixtureProvider(resolved=False),
            EvaluationRequest(raw_signal="UnknownCo may have a new optical product", as_of=NOW),
        )

        assert result["status"] == "completed_with_blockers"
        assert result["identity"]["status"] == "unresolved"
        assert result["paper_event_id"] is None
        assert result["action_card"]["paper"]["max_supported_position"] == 0
        assert result["action_card"]["live"]["supported_range"] == [0.0, 0.0]
        assert "identity_unresolved" in result["blockers"]
        assert result["work_orders"]
        assert store.table_count("decision_cohorts") == 1
        assert store.table_count("shadow_observations") == 1
        assert store.table_count("system_decisions") == 1
    finally:
        store.close()


def test_financial_manual_required_and_stale_states_fail_closed(tmp_path: Path) -> None:
    cases = (
        (
            "manual",
            {
                "customer_concentration": {"status": "manual_required"},
                "backlog": {"status": "manual_required"},
            },
            "financial_customer_concentration_manual_required",
        ),
        ("stale", None, "financial_stale"),
    )
    for name, checklist_patch, expected in cases:
        case_root = tmp_path / name
        case_root.mkdir()
        store = _store(case_root)
        inputs = complete_inputs()
        if checklist_patch:
            inputs["financial"]["checklist"].update(checklist_patch)
        else:
            inputs["financial"]["as_of"] = "2026-06-01T00:00:00+00:00"
        try:
            result = evaluate_signal(
                store,
                FixtureProvider(inputs=inputs),
                _request(raw_signal=f"case:{name}"),
            )
            assert expected in result["blockers"]
            assert result["paper_event_id"] is None
            assert result["action_card"]["paper"]["max_supported_position"] == 0
        finally:
            store.close()


def test_reassessment_creates_new_context_without_mutating_old_decision(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        first = evaluate_signal(store, provider, _request())
        old = deepcopy(store.get_decision(first["decision_id"]))
        provider.inputs["market"]["price"] = 3.0
        provider.inputs["market"]["as_of"] = "2026-07-22T10:00:00+00:00"
        provider.inputs["market"]["fetched_at"] = "2026-07-22T10:01:00+00:00"

        second = reassess(
            store,
            provider,
            first["decision_id"],
            as_of="2026-07-22T12:00:00+00:00",
            execution_intent="paper",
        )

        assert second["decision_id"] != first["decision_id"]
        assert second["context_digest"] != first["context_digest"]
        assert store.get_decision(first["decision_id"]) == old
        assert second["delta"]["automatic_repair"] is False
        assert second["delta"]["system_action"]["from"]
        assert store.table_count("system_decisions") == 2
    finally:
        store.close()


def test_reassessment_accepts_explicit_gap_research_overrides_without_mutating_signal(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        first = evaluate_signal(
            store,
            provider,
            _request(catalyst=None, disproof=None),
        )
        original_signal = deepcopy(store.latest_signal_payload(first["cohort_id"]))

        second = reassess(
            store,
            provider,
            first["decision_id"],
            as_of="2026-07-22T12:00:00+00:00",
            catalyst="customer qualification reaches volume production",
            disproof="qualification slips beyond the stated window",
            expiry="2026-08-22T12:00:00+00:00",
        )

        decision = store.get_decision(second["decision_id"])
        metadata = store.get_coverage_metadata(
            decision["payload"]["request"]["coverage"]["assessment_id"]
        )
        assert metadata["catalyst"] == "customer qualification reaches volume production"
        assert metadata["disproof"] == "qualification slips beyond the stated window"
        assert metadata["expiry"] == "2026-08-22T12:00:00+00:00"
        assert store.latest_signal_payload(first["cohort_id"]) == original_signal
    finally:
        store.close()


def test_fake_assessment_ref_cannot_fund_paper(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assessment = _assessment()
    assessment["source_reliability"]["evidence_refs"] = ["src:not-in-context"]
    try:
        result = evaluate_signal(
            store,
            FixtureProvider(),
            _request(raw_signal="fake ref", assessment=assessment),
        )

        assert "assessment_context_mismatch:source_reliability" in result["blockers"]
        assert result["paper_event_id"] is None
        assert result["action_card"]["paper"]["max_supported_position"] == 0
    finally:
        store.close()


def test_unresolved_cohort_can_bind_identity_on_explicit_reassessment(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        first = evaluate_signal(
            store,
            FixtureProvider(resolved=False),
            EvaluationRequest(raw_signal="Unknown optical supplier signal", as_of=NOW),
        )
        second = reassess(
            store,
            FixtureProvider(),
            first["decision_id"],
            as_of="2026-07-22T12:00:00+00:00",
            ticker_hint="SIVE.ST",
            company_id_hint="co:sivers_semiconductors",
        )

        assert second["cohort_id"] == first["cohort_id"]
        assert second["identity"]["status"] == "resolved"
        assert store.cohort_identity(first["cohort_id"]) == {
            "company_id": "co:sivers_semiconductors",
            "research_ticker": "SIVE.ST",
        }
        identity_events = [
            event
            for event in store.list_events(first["cohort_id"])
            if event.event_type == "identity_resolved"
        ]
        assert len(identity_events) == 1
    finally:
        store.close()
