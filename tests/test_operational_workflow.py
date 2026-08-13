from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from decision_lab.blocker_severity import severity_of
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
        # 核心 identity 存活（company_id 有綁定，coverage 不報 identity_unresolved）。
        bundle = store.get_context_bundle(result["context_digest"])
        frozen_identity = bundle.payload["identity"]
        assert frozen_identity["status"] == "resolved"
        assert frozen_identity["company_id"] == "co:broadcom"
        assert "identity_unresolved" not in result["blockers"]
        assert "market_currency_missing" in frozen_identity["blockers"]

        # 2026-08-13 行為變更：execution metadata 缺失只封鎖 **live**，不再連坐 paper。
        # 缺的是執行匯率、使用者 NAV 與投組槓桿——那是「能不能真的下單」需要的東西，
        # 一筆 0.5% 的 paper probe 不需要它們。先前 `if live_blockers: paper_max = 0`
        # 式的無條件連坐，正是讓 2026-08-02 嚴重度分類變成 no-op 的那一行。
        assert result["action_card"]["live"]["supported_range"] == [0.0, 0.0]
        assert result["action_card"]["paper"]["max_supported_position"] > 0

        # 但擋住 live 的理由必須看得見：會改變輸出的輸入要出現在輸出自己的證據欄位。
        for blocker in ("execution_fx_missing", "live_nav_missing", "portfolio_leverage_unavailable"):
            assert blocker in result["action_card"]["blockers"]
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


def test_financial_manual_required_and_stale_states_reduce_size_not_zero(
    tmp_path: Path,
) -> None:
    """2026-08-13：本測試先前斷言的是一個 bug 的行為，且與另一個測試互相矛盾。

    `tests/test_coverage_severity.py::test_financial_checklist_gaps_only_reduce_size`
    早就斷言 `financial_customer_concentration_manual_required` 是**非致命**的，
    而本測試斷言同一個 blocker 會讓 `max_supported_position == 0`。**兩者同時是綠的**，
    因為當時嚴重度分類只套用在 `coverage_cap`，而 `sizing` 另有一行
    `if paper_blockers: paper_max = 0.0` 無條件歸零——兩條路徑各自回答，
    於是兩個相反的斷言都成立。這正是 L12 在測試層的簽名。

    現在只有一套分類：核驗清單缺漏與過期都只降尺寸，blocker 仍必須現形。

    ⚠ `manual` 那一格的可承受尺寸仍是 0，但**成因換了**：不再是 blocker 把 lane 打成
    零，而是 `assessment_context_mismatch:commercial_maturity` 讓該軸被改寫成
    `unknown` → `axis_ceiling = 0`（`sizing.py` 的 `_validate_assessment`）。
    也就是它現在走的是信心維度而不是閘門。那條改寫本身是配線問題冒充信心不足，
    列在 `docs/brainstorms/2026-08-13-capital-expression-direction-requirements.md`
    §4 第 4 項；等該項落地後，這一格的期望值要改成 > 0。
    """
    cases = (
        # (名稱, checklist patch, 預期 blocker, 期望可承受尺寸是否 > 0)
        (
            "manual",
            {
                "customer_concentration": {"status": "manual_required"},
                "backlog": {"status": "manual_required"},
            },
            "financial_customer_concentration_manual_required",
            False,
        ),
        ("stale", None, "financial_stale", True),
    )
    for name, checklist_patch, expected, expect_positive_size in cases:
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
            # research intent 不 request paper lane，因此仍不建立 paper 部位。
            assert result["paper_event_id"] is None
            # 關鍵斷言：這兩個 blocker 本身不再有歸零的權力。
            assert severity_of(expected) == "sizing"
            size = result["action_card"]["paper"]["max_supported_position"]
            if expect_positive_size:
                # 過期只降尺寸，不禁止參與。
                assert size > 0, f"{name}: 過期不該把可承受尺寸打成零"
            else:
                # 仍為 0，但成因是軸而非閘門（見 docstring）。
                assert size == 0
                assert "assessment_context_mismatch:commercial_maturity" in result["blockers"]
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


def test_reassessment_carries_forward_disproof_and_catalyst_when_not_overridden(
    tmp_path: Path,
) -> None:
    """reassess 不得靜默清空 disproof condition。

    事發（2026-08-05）：disproof 與 catalyst 同樣存在 coverage metadata，但 reassess
    只替 catalyst 準備了 fallback，disproof 卻只從 signal 讀。凡是在 evaluate 階段
    用 --disproof 提供的 thesis，reassess 後都會退化成空字串，只在 decision payload
    留下 disproof_missing（不進 action card）。co:axt 與 co:applied_optoelectronics
    的 decision 歷史顯示 disproof 反覆 150→0→348→0，其中數對相隔僅數十秒——那是有人
    發現不見了、手動帶 --disproof 重跑。可證偽是一等公民（L7），不得因為換一次
    context 就掉。
    """

    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        # 觸發序列必須是「disproof 只存在 coverage metadata、不在 signal 上」。
        # reassess 的 explicit override 依契約不回寫 signal，所以第二次 reassess
        # 就再也讀不到它——這正是 0→N→0→N 那個形狀的來源。
        first = evaluate_signal(store, provider, _request(disproof=None))
        supplied = reassess(
            store,
            provider,
            first["decision_id"],
            as_of="2026-07-22T11:00:00+00:00",
            disproof="Q3 毛利率跌回 35% 以下即視為 step-function 未成為 run-rate。",
        )
        assert not str(
            store.latest_signal_payload(first["cohort_id"]).get("disproof") or ""
        )

        third = reassess(
            store,
            provider,
            supplied["decision_id"],
            as_of="2026-07-22T12:00:00+00:00",
        )

        metadata = store.get_coverage_metadata(
            store.get_decision(third["decision_id"])["payload"]["request"]["coverage"][
                "assessment_id"
            ]
        )
        assert (
            metadata["disproof"]
            == "Q3 毛利率跌回 35% 以下即視為 step-function 未成為 run-rate。"
        )
        assert metadata["catalyst"] == "客戶公布量產訂單。"
    finally:
        store.close()


def test_explicit_disproof_override_still_wins_over_carried_forward_value(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        first = evaluate_signal(store, provider, _request())

        second = reassess(
            store,
            provider,
            first["decision_id"],
            as_of="2026-07-22T12:00:00+00:00",
            disproof="新的反證條件取代舊的。",
        )

        metadata = store.get_coverage_metadata(
            store.get_decision(second["decision_id"])["payload"]["request"]["coverage"][
                "assessment_id"
            ]
        )
        assert metadata["disproof"] == "新的反證條件取代舊的。"
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
