from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from decision_lab.action_card import build_action_card
from shared.private_backup import create_private_backup, restore_private_backup
from decision_lab.bootstrap import open_default_store
from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import assess_probe
from decision_lab.intake import capture_signal
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.outcomes import close_probe
from decision_lab.sizing import calculate_probe_limits
from decision_lab.store import DecisionStore
from engine_c.db import _ensure_sqlite_schema, upsert_snapshot
from engine_c.manual_observations import append_manual_observation
from paper_portfolio.ledger import replay_decision_store_events
from risk.policy import load_policy


FIXTURES = Path(__file__).parent / "fixtures" / "decision_lab"


class FixedMarket:
    def __init__(self, payload: dict):
        self._observation = MarketObservation(**payload)

    def observe(self, *_args) -> MarketObservation:
        return self._observation


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _store(tmp_path: Path) -> tuple[DecisionStore, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    private = repo / "library" / "private"
    return open_default_store(repo), repo, private


def _freeze_fixture_context(
    store: DecisionStore,
    fixture: dict,
    cohort_id: str,
    *,
    with_execution: bool = False,
):
    context = deepcopy(fixture["context"])
    holdings = context["holdings"]
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            holdings["rows"],
            nav_base=holdings.get("nav_base"),
            base_currency=holdings.get("base_currency"),
        ),
        confirmed_at=fixture["holdings_confirmed_at"],
    )
    return build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=fixture["evaluation_at"],
        policy_version=load_policy()["policy_version"],
        execution_market=fixture.get("execution_market") if with_execution else None,
        execution_fx=fixture.get("execution_fx") if with_execution else None,
        **context,
    )


def _run_sive(store: DecisionStore) -> tuple[dict, object, object, object]:
    fixture = _fixture("sive_reference_design.json")
    captured = capture_signal(
        store,
        SignalInput(**fixture["signal"]),
        market=FixedMarket(fixture["shadow_market"]),
    )
    bundle = _freeze_fixture_context(store, fixture, captured.cohort_id)
    coverage = assess_coverage(store, bundle, **fixture["coverage"])
    decision = assess_probe(
        store,
        bundle,
        coverage,
        fixture["assessment"],
        idempotency_key="e2e:sive:initial",
        effective_at=fixture["evaluation_at"],
    )
    return fixture, captured, bundle, decision


def test_sive_signal_produces_a_research_verdict_but_never_auto_adds_live(
    tmp_path: Path,
) -> None:
    """完整 e2e：Signal → Shadow → context → coverage → decision → Action Card。

    U7（2026-08-28）之前，本測試的終點是「資助了多少 paper、live 區間多寬」。
    資本表達層已移除，終點改成研究判斷本身：最弱軸是哪一軸、研究完整度到哪、
    以及 live 仍然 100% 由使用者手動決定（系統既不給尺寸也不連 broker）。
    """

    store, _, _ = _store(tmp_path)
    try:
        fixture, captured, _, decision = _run_sive(store)
        card = build_action_card(store, decision.decision_id, as_of=fixture["evaluation_at"])

        assert captured.company_id == "co:sivers_semiconductors"
        assert captured.research_ticker == "SIVE.ST"
        assert captured.execution_symbol == "FRA:2DG"
        assert store.get_shadow(captured.cohort_id).price == pytest.approx(2.5)
        assert store.get_probe(captured.cohort_id).evidence_admission_status == "lead_only"
        assert decision.research_status == "READY"
        assert card["weakest_link"]["axis"] == "commercial_maturity"
        assert any(
            "production order" in item
            for item in card["weakest_link"]["missing_data"]
        )
        assert card["research"] == {"status": "READY", "data_stale": False}
        # live 區塊只剩「使用者做了什麼」——沒有 status、也沒有 supported range／shares。
        assert card["live"] == {"user_choice": None, "fill_reported": False}
        assert store.table_count("paper_events") == 0
        assert store.table_count("live_choices") == 0
        assert store.table_count("live_execution_reports") == 0

        complete = deepcopy(fixture)
        live_bundle = _freeze_fixture_context(
            store, complete, captured.cohort_id, with_execution=True
        )
        live_coverage = assess_coverage(store, live_bundle, **fixture["coverage"])
        live_sizing = calculate_probe_limits(
            live_bundle, live_coverage, fixture["assessment"]
        )

        # 補上 execution 行情／FX 之後 live lane 沒有任何缺口，但系統仍不產生任何
        # live 選擇——「條件齊全」與「可以下單」在 U7 之後徹底脫鉤。
        assert live_sizing.research_status == "READY"
        assert live_sizing.live_blockers == ()
        # 這兩個數字不是建議尺寸，是使用者手動記錄 live 選擇時的既有部位與政策參考線。
        assert live_sizing.live_current_position == pytest.approx(0.003)
        assert live_sizing.single_position_nav_cap == pytest.approx(0.05)
        assert store.table_count("live_choices") == 0
    finally:
        store.close()


def test_empty_graph_company_stays_shadow_only_with_bounded_research_work(
    tmp_path: Path,
) -> None:
    store, _, _ = _store(tmp_path)
    fixture = _fixture("empty_graph_company.json")
    try:
        captured = capture_signal(
            store,
            SignalInput(**fixture["signal"]),
            market=FixedMarket(fixture["shadow_market"]),
        )
        bundle = _freeze_fixture_context(store, fixture, captured.cohort_id)
        coverage = assess_coverage(store, bundle, **fixture["coverage"])
        decision = assess_probe(
            store,
            bundle,
            coverage,
            fixture["assessment"],
            idempotency_key="e2e:empty-graph",
            effective_at=fixture["evaluation_at"],
        )
        frozen = store.get_decision(decision.decision_id)["payload"]["sizing"]
        card = build_action_card(
            store, decision.decision_id, as_of=fixture["evaluation_at"]
        )

        assert store.count_shadows(captured.cohort_id) == 1
        assert coverage.status == "coverage_pending"
        assert coverage.work_order_id is not None
        assert "graph_company_missing" in coverage.blockers
        assert "causal_path_missing" in coverage.blockers
        # U7 之前這裡斷言額度歸零（paper_max 0、live 區間 [0,0]）；同一件事現在由
        # 研究完整度表達，而缺口本身仍然要有一張 bounded work order 可以派工。
        #
        # 2026-08-29：判準改用嚴重度分類後，這個 cohort 的verdict 由 `DATA_NEEDED`
        # 變成 `INCOMPLETE`，而那是**更準確**的答案——空圖缺的是因果鏈與圖中公司
        # （`causal_path_missing` 是 fatal coverage blocker），不是行情或 FX 抓不到。
        # 兩者的下一步不同：`INCOMPLETE` 要人去補研究，`DATA_NEEDED` 只要重抓資料。
        assert decision.research_status == "INCOMPLETE"
        assert frozen["research_status"] == "INCOMPLETE"
        assert frozen["assessment_blockers"]
        assert store.table_count("paper_events") == 0
        assert store.table_count("research_work_orders") == 1
        assert card["attention"] == "REVIEW"
        assert card["research"]["status"] == "INCOMPLETE"
        assert card["live"] == {"user_choice": None, "fill_reported": False}
    finally:
        store.close()


def test_engine_c_rebuild_and_private_restore_preserve_frozen_decision_audit(
    tmp_path: Path,
) -> None:
    store, repo, private = _store(tmp_path)
    fixture, captured, bundle, decision = _run_sive(store)
    outcome = close_probe(
        store,
        captured.cohort_id,
        terminal_status="expired",
        claim_correctness="unknown",
        current_market={"status": "missing"},
        benchmark={"status": "missing"},
        reason="Fixture horizon ended without production-order confirmation.",
        evidence_refs=["fixture://sive/outcome-review"],
        effective_at="2026-10-21T12:00:00+00:00",
    )
    original = {
        "decision_digest": store.get_decision(decision.decision_id)["decision_digest"],
        "context_digest": bundle.digest,
        "outcome": store.get_outcome(outcome.outcome_id),
        "paper": replay_decision_store_events(
            store.list_paper_events(captured.cohort_id)
        ),
    }

    engine_path = private / "engine_c" / "rebuild-fixture.db"
    engine_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "ticker": "SIVE.ST",
        "snapshot_date": "2026-07-21",
        "gross_margin": 0.4,
        "operating_margin": -0.1,
        "revenue_ttm": 100,
        "shares_outstanding": 100,
        "cash_and_equivalents": 120.0,
        "total_debt": 20.0,
        "free_cash_flow_ttm": -60.0,
        "ev_revenue": 2.0,
        "pe_trailing": None,
        "pe_forward": None,
        "price": 2.5,
        "analyst_target_mean": None,
        "analyst_target_high": None,
        "analyst_target_low": None,
        "analyst_target_count": None,
        "fetched_at": "2026-07-21T10:00:00+00:00",
    }
    manual = {
        "ticker": "SIVE.ST",
        "field_name": "backlog",
        "value": "no named production order",
        "source_ref": "fixture://sivers/filing",
        "as_of": "2026-07-15T00:00:00+00:00",
        "author": "fixture",
    }
    engine = sqlite3.connect(engine_path)
    engine.row_factory = sqlite3.Row
    _ensure_sqlite_schema(engine)
    upsert_snapshot(engine, snapshot)
    append_manual_observation(engine, **manual)
    assert engine.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0] == 1
    assert engine.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1
    engine.close()

    # Rebuild Engine C from explicit ETL + manual-ledger inputs without touching
    # the frozen Decision Store. Production deletion still requires a recovery backup.
    engine_path.unlink()
    rebuilt = sqlite3.connect(engine_path)
    rebuilt.row_factory = sqlite3.Row
    _ensure_sqlite_schema(rebuilt)
    upsert_snapshot(rebuilt, snapshot)
    append_manual_observation(rebuilt, **manual)
    rebuilt_counts = (
        rebuilt.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0],
        rebuilt.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0],
        rebuilt.execute("SELECT COUNT(*) FROM manual_fields").fetchone()[0],
    )
    rebuilt_manual = rebuilt.execute(
        "SELECT value, source_note, updated_at FROM manual_fields"
    ).fetchone()
    rebuilt.close()
    assert rebuilt_counts == (1, 1, 1)
    assert tuple(rebuilt_manual) == (
        manual["value"],
        manual["source_ref"],
        manual["as_of"],
    )
    assert store.get_decision(decision.decision_id)["decision_digest"] == original[
        "decision_digest"
    ]

    store.close()
    backup = create_private_backup(
        sources={
            "decision_lab": private / "decision_lab" / "decision_lab.db",
            "engine_c": engine_path,
        },
        backup_id="20260721T120000Z",
        private_root=private,
        repo_root=repo,
    )
    mutated = open_default_store(repo)
    mutated.ensure_cohort(
        dedupe_key="post-backup-mutation",
        company_id="co:axt",
        research_ticker="AXTI",
    )
    mutated.close()
    engine_path.unlink()
    restore_private_backup(
        backup,
        targets={
            "decision_lab": private / "decision_lab" / "decision_lab.db",
            "engine_c": engine_path,
        },
        private_root=private,
        repo_root=repo,
    )
    restored = open_default_store(repo)
    try:
        recovered_engine = sqlite3.connect(engine_path)
        try:
            assert recovered_engine.execute(
                "SELECT COUNT(*) FROM manual_observations"
            ).fetchone()[0] == 1
        finally:
            recovered_engine.close()
        assert restored.get_decision(decision.decision_id)["decision_digest"] == original[
            "decision_digest"
        ]
        assert restored.get_context_bundle(original["context_digest"]).digest == original[
            "context_digest"
        ]
        assert restored.get_outcome(outcome.outcome_id) == original["outcome"]
        assert replay_decision_store_events(
            restored.list_paper_events(captured.cohort_id)
        ) == original["paper"]
        assert restored.lifecycle_invariant_violations() == []
        assert restored.table_count("decision_cohorts") == 1
    finally:
        restored.close()


def test_shadow_dedupes_tickerless_company_by_hint(monkeypatch) -> None:
    """2026-08-12 迴歸：未上市公司每次入圖都新建一個重複 cohort。

    bind_cohort_identity 要求 company_id 與 research_ticker 成對，未上市公司沒有
    ticker，於是 store 的 company_id 永遠是 None；而 ensure_shadow_for_company 只比對
    company_id，導致去重永不命中。實測 co:agility_robotics 累積四個重複 cohort。
    真正的意圖一直存在於 company_id_hint。
    """
    from decision_lab.workflow import ensure_shadow_for_company

    calls: list[str] = []

    class _Store:
        def list_operational_cohorts(self, *, as_of):
            return [
                # 終態 cohort：即使公司對得上也不能沿用，否則 handoff 指向死 cohort
                {
                    "cohort_id": "dc_dead",
                    "company_id": None,
                    "company_id_hint": "co:agility_robotics",
                    "lifecycle_status": "expired",
                },
                {
                    "cohort_id": "dc_live",
                    "company_id": None,
                    "company_id_hint": "co:agility_robotics",
                    "lifecycle_status": "active",
                },
            ]

    def _boom(*args, **kwargs):
        calls.append("evaluate_signal")
        raise AssertionError("不應為已存在的公司新建 cohort")

    monkeypatch.setattr("decision_lab.workflow.evaluate_signal", _boom)

    result = ensure_shadow_for_company(
        _Store(), object(), company_id="co:agility_robotics", as_of="2026-08-12T00:00:00+00:00"
    )
    assert result == {"created": False, "cohort_id": "dc_live"}
    assert calls == []


def test_shadow_skips_terminal_cohort_and_creates_new_one(monkeypatch) -> None:
    """終態 cohort 不得被當成「已在追蹤」——否則 handoff 指向不會再產生 decision 的死 cohort。"""
    from decision_lab.workflow import ensure_shadow_for_company

    class _Store:
        def list_operational_cohorts(self, *, as_of):
            return [{
                "cohort_id": "dc_dead",
                "company_id": "co:coherent",
                "company_id_hint": None,
                "lifecycle_status": "expired",
            }]

    monkeypatch.setattr(
        "decision_lab.workflow.evaluate_signal",
        lambda *a, **k: {"cohort_id": "dc_new", "decision_id": "pd_new"},
    )

    result = ensure_shadow_for_company(
        _Store(), object(), company_id="co:coherent", as_of="2026-08-12T00:00:00+00:00"
    )
    assert result["created"] is True
    assert result["cohort_id"] == "dc_new"
