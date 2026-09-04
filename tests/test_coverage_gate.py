from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from shared.blocker_severity import severity_of
from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs


def _store(tmp_path: Path) -> DecisionStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    store = DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )
    store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    )
    return store


def _bundle(
    store: DecisionStore,
    *,
    evidence=None,
    financial=None,
    holdings=None,
    execution_market=None,
    execution_fx=None,
):
    inputs = complete_inputs()
    if evidence is not None:
        inputs["evidence"] = evidence
    if financial is not None:
        inputs["financial"] = financial
    if holdings is not None:
        inputs["holdings"] = holdings
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            inputs["holdings"]["rows"],
            nav_base=inputs["holdings"].get("nav_base"),
            base_currency=inputs["holdings"].get("base_currency"),
        ),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    cohort_id = store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    return build_context_bundle(
        store, cohort_id=cohort_id, evaluation_at=NOW,
        policy_version="probe-v1",
        execution_market=execution_market,
        execution_fx=execution_fx,
        **inputs,
    )


def _assess(store: DecisionStore, bundle, **overrides):
    kwargs = {
        "catalyst": "customer production order",
        "disproof": "qualified alternative wins socket",
        "expiry": "2026-10-21T00:00:00+00:00",
        "decision_relevance": 5,
        "falsifiability": 5,
        "information_value": 5,
    }
    kwargs.update(overrides)
    return assess_coverage(store, bundle, **kwargs)


def test_empty_graph_stays_pending_and_gets_bounded_work_order(tmp_path: Path) -> None:
    """圖裡沒有這家公司時，coverage 必須留在 pending 並開一張有界的 work order。

    U7（2026-08-28）：原測試另外斷言 `paper_supported_position == 0`／
    `live_supported_range == (0, 0)`，那兩個欄位已隨資本表達層從 `CoverageResult`
    移除——coverage 現在只回答「context 齊不齊」，不回答「能配多少」。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(
            store,
            evidence={
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            },
        )
        result = _assess(store, bundle)

        assert result.status == "coverage_pending"
        assert result.paper_context_ready is False
        assert result.work_order_id is not None
        assert "graph_company_missing" in result.blockers
        assert store.table_count("research_work_orders") == 1
    finally:
        store.close()


def test_complete_packet_becomes_analyzable_without_overwriting_old_event(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        pending = _assess(
            store,
            _bundle(
                store,
                evidence={
                    "focus_company": None,
                    "subject_origin_entity": "Unknown",
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                },
            ),
        )
        analyzable = _assess(store, _bundle(store))

        assert pending.status == "coverage_pending"
        assert analyzable.status == "analyzable"
        assert analyzable.blockers == ()
        assert store.table_count("coverage_assessments") == 2
    finally:
        store.close()


def test_supplier_only_source_and_manual_financial_items_are_explicit_blockers(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["evidence"]["sources"] = [
        {"id": "src:self", "origin_entity": "Sivers", "evidence_tier": 1}
    ]
    inputs["financial"]["checklist"]["backlog"] = {
        "status": "manual_required", "value": ""
    }
    try:
        result = _assess(
            store,
            _bundle(
                store,
                evidence=inputs["evidence"],
                financial=inputs["financial"],
            ),
        )

        assert "independent_source_missing" in result.blockers
        assert "financial_backlog_manual_required" in result.blockers
    finally:
        store.close()


def test_live_stale_does_not_destroy_paper_research_analyzability(tmp_path: Path) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["holdings"] = {"status": "available", "rows": inputs["holdings"]["rows"]}
    cohort_id = store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    try:
        bundle = build_context_bundle(
            store, cohort_id=cohort_id, evaluation_at=NOW,
            policy_version="probe-v1", **inputs
        )
        result = _assess(store, bundle)

        assert result.status == "analyzable"
        assert result.paper_context_ready is True
        assert result.live_context_ready is False
        assert "holdings_unconfirmed" in result.live_blockers
    finally:
        store.close()


def test_stale_financial_snapshot_reduces_size_without_closing_the_paper_lane(
    tmp_path: Path,
) -> None:
    """2026-08-13 行為變更：`financial_stale` 由「關閉 paper lane」改為只降強度。

    理由與 `market_stale` 同一條：**過期不等於錯**，而 `financial_resilience` 軸的
    authority 就是 Engine C——資料過期時該軸的證據自然變弱，該軸的 `effective_level`
    會反映它（U7 之前是由 `axis_ceiling` 反映）。再讓 blocker 關閉整個 lane 是同一件
    事罰兩次（D2：不確定性用強度承擔，不用 gate 禁止參與）。

    ⚠ 這條的相反意見值得記著：用過期資料形成的判斷會讓「系統當時相信什麼」失真。
    目前靠 context bundle 凍結 `as_of` 保持誠實——紀錄裡看得到用的是哪一天的財務。

    blocker 本身仍必須出現在 `paper_blockers`：會改變輸出的輸入要出現在輸出自己的
    證據欄位（L12 的相鄰判準）。
    """
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["financial"]["as_of"] = "2026-06-01T00:00:00+00:00"
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        result = _assess(
            store,
            _bundle(
                store,
                financial=inputs["financial"],
                holdings=inputs["holdings"],
                execution_market={
                    "status": "observed",
                    "ticker": "FRA:2DG",
                    "price": 10.0,
                    "currency": "EUR",
                    "adv20": 100.0,
                    "as_of": "2026-07-21T10:00:00+00:00",
                    "fetched_at": "2026-07-21T10:01:00+00:00",
                    "unit_status": "ok",
                    "source": "fixture://fra-market",
                },
                execution_fx={
                    "status": "observed",
                    "pair": "EUR/USD",
                    "rate": 1.2,
                    "as_of": "2026-07-21T10:00:00+00:00",
                    "fetched_at": "2026-07-21T10:01:00+00:00",
                    "source": "fixture://eur-usd",
                },
            ),
        )

        assert result.status == "analyzable"
        assert result.paper_context_ready is True
        assert result.live_context_ready is True
        # 仍必須現形，只是不再歸零。
        assert "financial_stale" in result.paper_blockers
        assert severity_of("financial_stale") == "sizing"
    finally:
        store.close()


def test_queue_capacity_preserves_backlog_and_stable_ranking(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        results = []
        for index in range(7):
            cohort = store.ensure_cohort(
                dedupe_key=f"empty-{index}",
                company_id="co:sivers_semiconductors",
                research_ticker="SIVE.ST",
            )
            inputs = complete_inputs()
            inputs["evidence"] = {
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            }
            bundle = build_context_bundle(
                store, cohort_id=cohort.cohort_id, evaluation_at=NOW,
                policy_version="probe-v1", **inputs
            )
            results.append(
                _assess(store, bundle, decision_relevance=7 - index)
            )

        # Coverage 只會提出 work order；明確 pq2 go 後才進可 drain 的 pq1。
        assert store.rank_work_orders(capacity=5)["selected"] == []
        for index, result in enumerate(results):
            store.transition_research_work_order(
                work_order_id=result.work_order_id,
                to_status="queued",
                operation_key=f"test-dispatch-{index}",
                receipt={"todo_n": index + 1},
                observed_at=NOW,
            )

        ranked_once = store.rank_work_orders(capacity=5)
        ranked_twice = store.rank_work_orders(capacity=5)
        assert ranked_once == ranked_twice
        assert len(ranked_once["selected"]) == 5
        assert len(ranked_once["backlog"]) == 2
        assert store.table_count("research_work_orders") == 7
        assert all(result.work_order_id for result in results)
    finally:
        store.close()


def _queued_work_order(store: DecisionStore, *, key: str) -> str:
    """建一張已 dispatch 的 work order，供 lifecycle 分流測試使用。

    `expiry` 用 `_assess` 的預設 2026-10-21；**不能在這裡直接塞過去的日期**——
    `assess_coverage` 會擋掉 expiry <= evaluation_at。production 的逾期是建立當下為
    未來、之後才走到期，因此測試改用 `rank_work_orders(today=...)` 推進時間。
    """
    result = _assess(
        store,
        _bundle(
            store,
            evidence={
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            },
        ),
    )
    store.transition_research_work_order(
        work_order_id=result.work_order_id,
        to_status="queued",
        operation_key=f"test-dispatch-{key}",
        receipt={"todo_n": 1},
        observed_at=NOW,
    )
    return result.work_order_id


def test_lapsed_expiry_without_structured_catalyst_is_kept_not_withheld(
    tmp_path: Path,
) -> None:
    """沒有結構化催化劑日期時，逾期無法判真假，必須保留（fail-safe）。

    反面就是 AXT 那次災難：`expiry` 被設在自己的催化劑之前，若直接當成逾期排除，
    會關掉一個還在跑的 thesis。
    """
    store = _store(tmp_path)
    try:
        work_order_id = _queued_work_order(store, key="unverifiable")
        ranked = store.rank_work_orders(
            capacity=5, checkpoints_by_ticker={}, today=date(2026, 11, 1)
        )

        assert [row["work_order_id"] for row in ranked["selected"]] == [work_order_id]
        assert ranked["withheld"] == []
        assert ranked["selected"][0]["lifecycle_state"] == "expired_unverifiable"
        assert any(
            "無法分辨真逾期" in note for note in ranked["selected"][0]["lifecycle_notes"]
        )
    finally:
        store.close()


def test_lapsed_expiry_after_its_catalyst_is_withheld_with_reason(tmp_path: Path) -> None:
    """催化劑已過、`expiry` 也到期＝真的逾期：該由人決定 close／extend，不是補 blocker。"""
    store = _store(tmp_path)
    try:
        work_order_id = _queued_work_order(store, key="lapsed")
        ranked = store.rank_work_orders(
            capacity=5,
            checkpoints_by_ticker={
                "SIVE.ST": [{"date": date(2026, 10, 1), "date_confidence": "confirmed"}]
            },
            today=date(2026, 11, 1),
        )

        assert ranked["selected"] == []
        assert [row["work_order_id"] for row in ranked["withheld"]] == [work_order_id]
        assert ranked["withheld"][0]["withheld_reason"] == "catalyst_window_lapsed"
    finally:
        store.close()


def test_expiry_set_before_its_own_catalyst_is_kept_as_config_broken(tmp_path: Path) -> None:
    """`expiry` 早於催化劑是設定錯誤，不是論點失效——必須保留並標記（AXT 實例）。"""
    store = _store(tmp_path)
    try:
        work_order_id = _queued_work_order(store, key="misconfigured")
        ranked = store.rank_work_orders(
            capacity=5,
            checkpoints_by_ticker={
                "SIVE.ST": [{"date": date(2026, 12, 1), "date_confidence": "confirmed"}]
            },
            today=date(2026, 11, 1),
        )

        assert [row["work_order_id"] for row in ranked["selected"]] == [work_order_id]
        assert ranked["withheld"] == []
        assert ranked["selected"][0]["lifecycle_state"] == "config_broken"
    finally:
        store.close()


def test_work_order_superseded_by_newer_decision_is_withheld(tmp_path: Path) -> None:
    """綁在舊 assessment 上的 work order 不再是 live 工作（COHR 實例）。"""
    store = _store(tmp_path)
    try:
        bundle = _bundle(
            store,
            evidence={
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            },
        )
        older = _assess(store, bundle, expiry="2026-10-21T00:00:00+00:00")
        newer = _assess(store, bundle, expiry="2026-11-21T00:00:00+00:00")
        store.transition_research_work_order(
            work_order_id=older.work_order_id,
            to_status="queued",
            operation_key="test-dispatch-superseded",
            receipt={"todo_n": 1},
            observed_at=NOW,
        )
        for decision_id, assessment_id, effective_at in (
            ("pd_older", older.assessment_id, "2026-08-01T00:00:00+00:00"),
            ("pd_newer", newer.assessment_id, "2026-09-01T00:00:00+00:00"),
        ):
            store._conn.execute(
                """
                INSERT INTO system_decisions (
                    decision_id, cohort_id, idempotency_key, request_digest,
                    decision_digest, context_digest, coverage_assessment_id,
                    policy_version, calculator_version, payload_json, effective_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'probe-v1', 'probe-limit-v3', '{}', ?)
                """,
                (
                    decision_id, bundle.cohort_id, f"idem_{decision_id}",
                    f"rq_{decision_id}", f"dg_{decision_id}", bundle.digest,
                    assessment_id, effective_at,
                ),
            )
        work_order_id = older.work_order_id
        ranked = store.rank_work_orders(capacity=5, checkpoints_by_ticker={})

        assert ranked["selected"] == []
        assert [r["work_order_id"] for r in ranked["withheld"]] == [work_order_id]
        assert ranked["withheld"][0]["withheld_reason"] == "superseded_by_newer_decision"
    finally:
        store.close()


def test_latest_work_order_is_none_when_newest_decision_has_no_gap(tmp_path: Path) -> None:
    """最新 decision 已無 coverage gap 時不得往回撈舊 work order（co:axt 實例）。

    原本的 INNER JOIN 會跳過沒有 work order 的較新 decision，於是 `todo dispatch`
    發出一張早已被補完的 work order，drain 立刻擋下——按了 go 卻什麼都沒發生。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(
            store,
            evidence={
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            },
        )
        gapped = _assess(store, bundle)
        # 較新的 decision 綁一份「已無 blocker」的 assessment，它本來就不會有 work order。
        clean_bundle = _bundle(store)
        clean = _assess(store, clean_bundle)
        assert gapped.work_order_id is not None
        assert clean.work_order_id is None

        for decision_id, assessment_id, digest, effective_at in (
            ("pd_gapped", gapped.assessment_id, bundle.digest, "2026-08-16T22:53:00+00:00"),
            ("pd_clean", clean.assessment_id, clean_bundle.digest, "2026-08-17T01:36:00+00:00"),
        ):
            store._conn.execute(
                """
                INSERT INTO system_decisions (
                    decision_id, cohort_id, idempotency_key, request_digest,
                    decision_digest, context_digest, coverage_assessment_id,
                    policy_version, calculator_version, payload_json, effective_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'probe-v1', 'probe-limit-v3', '{}', ?)
                """,
                (
                    decision_id, bundle.cohort_id, f"idem_{decision_id}",
                    f"rq_{decision_id}", f"dg_{decision_id}", digest,
                    assessment_id, effective_at,
                ),
            )

        # 舊的 INNER JOIN 會跳過 pd_clean、回傳 gapped 的 work order；LEFT JOIN 回 None。
        assert store.latest_research_work_order(bundle.cohort_id) is None
    finally:
        store.close()


def test_terminal_work_order_requires_explicit_pq2_receipt_to_redispatch(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        result = _assess(
            store,
            _bundle(
                store,
                evidence={
                    "focus_company": None,
                    "subject_origin_entity": "Unknown",
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                },
            ),
        )
        work_order_id = result.work_order_id
        assert work_order_id is not None
        store.transition_research_work_order(
            work_order_id=work_order_id,
            to_status="queued",
            operation_key="todo:64:go:first",
            receipt={"todo_n": 64, "prior_work_order_status": "proposed"},
            observed_at=NOW,
        )
        store.transition_research_work_order(
            work_order_id=work_order_id,
            to_status="researching",
            operation_key="todo:64:researching",
            receipt={"todo_n": 64, "reference": "research:first"},
            observed_at=NOW,
        )
        store.transition_research_work_order(
            work_order_id=work_order_id,
            to_status="completed",
            operation_key="todo:64:completed",
            receipt={"todo_n": 64, "reference": "research:done"},
            observed_at=NOW,
        )

        with pytest.raises(ValueError, match="illegal research work order transition"):
            store.transition_research_work_order(
                work_order_id=work_order_id,
                to_status="queued",
                operation_key="unsafe-reopen",
                receipt={"todo_n": 64},
                observed_at=NOW,
            )

        reopened = store.transition_research_work_order(
            work_order_id=work_order_id,
            to_status="queued",
            operation_key="todo:64:go:retry",
            receipt={"todo_n": 64, "prior_work_order_status": "completed"},
            observed_at=NOW,
        )
        assert reopened["status"] == "queued"
        assert store.rank_work_orders(capacity=5)["selected"][0]["work_order_id"] == work_order_id
    finally:
        store.close()


def test_reopen_lifecycle_epoch_restores_ability_to_record_outcome(tmp_path: Path) -> None:
    """非 revised 終態後仍能重新啟用並產出 outcome——L13：驗收是端到端有產出。

    事發（2026-08-19）：COHR 以 expired 結案後，使用者對它建立真實 live 部位並綁定
    新的 disproof；再次結案會拋「terminal epoch already has a different outcome」，
    等於新 disproof 觸發時拿不到 claim_correctness。
    """

    store = _store(tmp_path)
    try:
        cohort_id = store.ensure_cohort(
            dedupe_key="fixture", company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
        )
        cohort_id = cohort_id.cohort_id
        first = store.close_lifecycle_with_outcome(
            cohort_id=cohort_id,
            terminal_status="expired",
            outcome_payload={"claim_correctness": "unknown",
                             "market_return_status": "unavailable",
                             "reason": "到期未驗證", "evidence_refs": ()},
            effective_at="2026-07-25T00:00:00+00:00",
        )
        assert first.terminal_status == "expired"

        # 修復前：這裡會 raise，新 disproof 永遠拿不到 outcome
        with pytest.raises(ValueError, match="terminal epoch already has"):
            store.close_lifecycle_with_outcome(
                cohort_id=cohort_id,
                terminal_status="rejected",
                outcome_payload={"claim_correctness": "false",
                                 "market_return_status": "unavailable",
                                 "reason": "disproof 觸發", "evidence_refs": ()},
                effective_at="2027-03-01T00:00:00+00:00",
            )

        reopened = store.reopen_lifecycle_epoch(
            cohort_id=cohort_id,
            reason="使用者建立真實 live 部位並綁定新 disproof",
            effective_at="2026-08-19T00:00:00+00:00",
        )
        assert reopened.epoch == 2
        assert reopened.status == "active"

        second = store.close_lifecycle_with_outcome(
            cohort_id=cohort_id,
            terminal_status="rejected",
            outcome_payload={"claim_correctness": "false",
                             "market_return_status": "unavailable",
                             "reason": "disproof 觸發", "evidence_refs": ()},
            effective_at="2027-03-01T00:00:00+00:00",
        )
        assert second.epoch == 2
        assert second.claim_correctness == "false"

        # append 不是覆寫：epoch 1 與其 outcome 原封不動
        rows = store._conn.execute(
            "SELECT epoch, terminal_status, claim_correctness FROM outcome_envelopes"
            " WHERE cohort_id = ? ORDER BY epoch", (cohort_id,),
        ).fetchall()
        assert [(r["epoch"], r["terminal_status"], r["claim_correctness"]) for r in rows] == [
            (1, "expired", "unknown"), (2, "rejected", "false"),
        ]

        # 仍在進行中的 lifecycle 不得 reopen
        store.reopen_lifecycle_epoch(
            cohort_id=cohort_id, reason="再開一次以測試 guard",
            effective_at="2027-03-02T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="仍在進行中"):
            store.reopen_lifecycle_epoch(
                cohort_id=cohort_id, reason="重複 reopen",
                effective_at="2027-03-03T00:00:00+00:00",
            )
    finally:
        store.close()
