"""Refresh／dependency status × read model：變更偵測（組裝層）與 view 整合。

守的是 Step 0.5 的消費端契約：builder 只消費 `alpha.refresh` 的輸出、不自己判 impact；
price-only 變化不再讓 Q2–Q5／thesis／情境整份 stale；沒跑偵測時誠實標 `not_run`；
「第一次出現」不是變化；一手文件日早於判斷的 ledger 列不是新變化；精簡卡與 daily brief 看得到計數。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.fundamental.assumptions import assumption_record, parse_assumption_record
from alpha.identity import CompanyId
from alpha.refresh import (
    COMPANY_GUIDANCE, CONSENSUS, DISPROOF_SIGNAL, FINANCIAL_ACTUAL, GRAPH_EDGE, MARKET_PRICE,
    OPERATING_ASSUMPTION, THESIS_ARTIFACT_ID, THESIS_REVIEW_DUE,
)
from alpha.testing import FakeGraphResearchProvider
from briefing.alpha_view import changes as ch
from briefing.alpha_view import compact_card, render_alpha_cards, render_alpha_investment_view_markdown
from briefing.alpha_view.contracts import CAP_DEPENDENCY_IMPACT, REFRESH_STATUSES, SECTION_STATUSES
from tests.test_alpha_investment_view import COMPANY, TODAY, _CORROBORATED, _FakeFundamentals, _judgment, _view
from tests.test_fundamental_model import ACT_REF, TARGET, _run

UTC = timezone.utc
SINCE = datetime(2026, 9, 4, 23, 59, 59, tzinfo=UTC)


def _row(bar: str, snap: str, fetched: str, price: float, pe: float, target: float = 415.0) -> dict:
    return {"bar_date": bar, "snapshot_date": snap, "fetched_at": fetched, "price": price,
            "pe_forward": pe, "analyst_target_mean": target}


# ---------------------------------------------------------------------------
# 變更偵測：每個 class 都指得出 authority／物件／時間／欄位
# ---------------------------------------------------------------------------

def test_market_and_consensus_changes_separate_price_from_forward_eps() -> None:
    rows = [
        _row("2026-09-03", "2026-09-04", "2026-09-04 11:50:00+00:00", 264.41, 18.94691),   # fwd EPS 13.955
        _row("2026-09-04", "2026-09-05", "2026-09-05 11:53:40+00:00", 281.86, 20.197329),  # fwd EPS 13.955（不變）
        _row("2026-09-05", "2026-09-06", "2026-09-06 11:53:40+00:00", 281.86, 19.000000, 440.0),  # fwd EPS 14.83（+6.3%）
    ]
    events, _notes = ch.market_and_consensus_changes(rows, ticker="COHR", company_id="co:coherent", since=SINCE)
    kinds = [(e.change_type, tuple(e.material_fields)) for e in events]
    assert (MARKET_PRICE, ("price",)) in kinds
    assert (CONSENSUS, ("forward_eps",)) in kinds and (CONSENSUS, ("target_mean",)) in kinds
    price = next(e for e in events if e.change_type == MARKET_PRICE)
    assert price.old_version == "264.41" and price.new_version == "281.86"
    assert price.observed_at == datetime(2026, 9, 5, 11, 53, 40, tzinfo=UTC)     # fetched_at，不是 bar_date
    assert price.effective_at == date(2026, 9, 4)
    # 09-04 → 09-05：價格變了但 forward EPS 沒變 → 只有 market_price，沒有 consensus
    first_day = [e for e in events if e.observed_at.date() == date(2026, 9, 5)]
    assert {e.change_type for e in first_day} == {MARKET_PRICE}


def test_fiscal_consensus_first_appearance_is_a_note_not_a_change() -> None:
    from tests.test_fundamental_model import _consensus

    new = (_consensus("eps", 9.42, year_ago=5.61, captured=date(2026, 9, 5)),
           _consensus("revenue", 10.618e9, captured=date(2026, 9, 5)))
    events, notes = ch.fiscal_consensus_changes((), new, ticker="COHR", company_id="co:coherent", since=SINCE)
    assert events == [] and any("首次出現" in n for n in notes)
    revised = (_consensus("eps", 10.00, year_ago=5.61, captured=date(2026, 9, 10)), new[1])
    events, _ = ch.fiscal_consensus_changes(new, revised, ticker="COHR", company_id="co:coherent", since=SINCE)
    assert len(events) == 1 and events[0].change_type == CONSENSUS and events[0].old_version == "9.42"


def test_ledger_changes_use_the_filing_date_for_novelty_but_recorded_at_for_visibility() -> None:
    rows = [{"observation_id": "mo_fy26", "as_of": date(2026, 6, 30),
             "recorded_at": datetime(2026, 9, 5, 11, 53, tzinfo=UTC), "supersedes_id": None,
             "payload": {"fiscal_year_end": "2026-06-30", "source_filed_at": "2026-08-12", "revenue": 7.1e9,
                         "segment_revenue": {"Datacenter & Communications": 5.27e9},
                         "exit_quarter": {"period_end": "2026-06-30", "revenue": 2.05e9,
                                          "segment_revenue": {"Datacenter & Communications": 1.615e9}}}}]
    events = ch.ledger_changes(rows, field_name="fiscal_year_results", ticker="COHR", company_id="co:coherent",
                               since=SINCE)
    assert len(events) == 1
    event = events[0]
    assert event.change_type == FINANCIAL_ACTUAL and event.published_at == date(2026, 8, 12)
    assert event.observed_at == datetime(2026, 9, 5, 11, 53, tzinfo=UTC)
    assert event.known_at() < SINCE                         # 08-12 就發表——09-04 的判斷讀得到，不是新變化
    obs = ch.metric_observations(rows)
    assert {(o.metric, o.scope, o.period_kind) for o in obs} == {
        ("revenue", "total", "fiscal_year"), ("segment_revenue", "Datacenter & Communications", "fiscal_year"),
        ("revenue", "total", "fiscal_quarter"), ("segment_revenue", "Datacenter & Communications", "fiscal_quarter")}
    guidance = ch.ledger_changes([{
        "observation_id": "mo_g", "as_of": date(2026, 11, 10), "recorded_at": datetime(2026, 11, 11, tzinfo=UTC),
        "supersedes_id": None,
        "payload": {"period_label": "Q2 FY2027", "period_kind": "fiscal_quarter", "period_end": "2026-12-31",
                    "issued_at": "2026-11-10", "revenue_low": 2.4e9, "revenue_high": 2.6e9, "tax_rate_low": 0.18}}],
        field_name="company_guidance", ticker="COHR", company_id="co:coherent", since=SINCE)
    assert guidance[0].change_type == COMPANY_GUIDANCE
    assert set(guidance[0].material_fields) == {"revenue_high", "revenue_low", "tax_rate_low"}


def test_assumption_lifecycle_and_watch_changes() -> None:
    old = parse_assumption_record(assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="tax_rate", scope="total",
        value=0.19, basis="heuristic_proxy", rationale="r", evidence_refs=[ACT_REF.ref],
        created_at=datetime(2026, 9, 5, 8, 0, tzinfo=UTC), derivation="carried_forward"))
    new = parse_assumption_record(assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="tax_rate", scope="total",
        value=0.18, basis="heuristic_proxy", rationale="r2", evidence_refs=[ACT_REF.ref],
        supersedes_id=old.assumption_id, created_at=datetime(2026, 9, 8, 8, 0, tzinfo=UTC),
        derivation="carried_forward"))
    events = ch.assumption_changes([old, new], ticker="COHR", company_id="co:coherent", since=SINCE)
    assert [e.change_type for e in events] == [OPERATING_ASSUMPTION, OPERATING_ASSUMPTION]
    assert events[1].related_refs == (old.assumption_id,) and "取代" in events[1].detail

    watches = [
        {"watch_id": "ew_x", "kind": "fact_verification", "status": "fired", "entities": ["COHR", "co:coherent"],
         "hypothesis_ref": old.assumption_id, "fact": "Q2 FY27 D&C < 1.85B",
         "woken_by": {"kind": "fact_verification", "at": "2026-11-12T10:00:00+00:00", "lead_id": "lead_1"}},
        {"watch_id": "ew_y", "kind": "fact_verification", "status": "fired", "entities": ["AXTI"],
         "hypothesis_ref": "hy_0001", "woken_by": {"at": "2026-11-12T10:00:00+00:00"}},
        {"watch_id": "ew_z", "kind": "date", "status": "active", "entities": ["COHR"], "hypothesis_ref": old.assumption_id},
    ]
    fired = ch.watch_changes(watches, ticker="COHR", company_id="co:coherent", assumption_ids=[old.assumption_id])
    assert len(fired) == 1 and fired[0].change_type == DISPROOF_SIGNAL
    assert fired[0].target_artifact == old.assumption_id and fired[0].related_refs == ("lead_1",)

    due = ch.lifecycle_due_changes({"ticker": "COHR", "status": "active", "next_check": "2026-09-01",
                                    "last_checked": "2026-06-01"}, ticker="COHR", company_id="co:coherent",
                                   today=date(2026, 9, 6))
    assert len(due) == 1 and due[0].change_type == THESIS_REVIEW_DUE and due[0].target_artifact == THESIS_ARTIFACT_ID
    assert ch.lifecycle_due_changes(None, ticker="COHR", company_id=None, today=date(2026, 9, 6)) == []


# ---------------------------------------------------------------------------
# view 整合：price-only 不再整份 stale；not_run 誠實退回舊語意；精簡卡帶計數
# ---------------------------------------------------------------------------

def _stale_judgment() -> dict:
    return _judgment(_packet_digest="sha256:0000000000000000000000000000")


def _price_change(at: datetime = datetime(2026, 9, 5, 23, 59, 59, tzinfo=UTC)):
    """build 之後（23:59:58 之後）、cutoff 之內的價格變化——對今天 build 的市場導出量是新變化。"""
    from alpha.refresh import ChangeEvent

    return ChangeEvent(change_type=MARKET_PRICE, ticker="COHR", company_id="co:coherent",
                       authority="engine_c://financial_snapshots", changed_ref="engine_c://financial_snapshot/COHR",
                       observed_at=at, old_version="264.41", new_version="281.86", material_fields=("price",))


def test_price_only_change_keeps_session_axes_available_in_the_view() -> None:
    view = _view(judgment=_stale_judgment(), allow_stale=True, refresh_changes=[_price_change()])
    assert view.identity.signal.context_matches is False               # 事實仍在
    assert view.identity.signal.refresh_state == "current"
    q2 = next(d for d in view.variant_view.scores if d.key == "value_capture_score")
    assert q2.status == "available" and q2.dependencies["refresh_state"] == "current"
    assert view.variant_view.meta.status == "available"
    assert view.falsification.meta.status == "available"
    assert view.scenarios.meta.status == "available"
    assert view.refresh_status.overall == "recalculate"                 # 只有市場導出量重算
    assert view.refresh_status.change_detection == "authority_time_series"
    assert any(i.artifact_id == "market_implied_eps_growth" and i.state == "recalculate"
               for i in view.refresh_status.items)
    assert "判斷對的是舊 context" in (view.identity.signal.reason or "")
    assert not any("session 判斷過期" in w for w in view.warnings)
    assert view.capability_map()["refresh_status"]["capability"] == CAP_DEPENDENCY_IMPACT


def test_without_change_detection_the_old_digest_stale_semantics_remain_and_are_labelled() -> None:
    view = _view(judgment=_stale_judgment(), allow_stale=True)
    assert view.variant_view.meta.status == "stale"
    assert view.refresh_status.change_detection == "not_run"
    assert any("未執行 authority 變更偵測" in w for w in view.warnings)


def test_structural_change_marks_citing_axis_review_required_and_price_free_axes_stay() -> None:
    from alpha.refresh import ChangeEvent

    edge = ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", company_id="co:coherent",
                       authority="engine_a://graph_research_provider", changed_ref=_CORROBORATED.ref,
                       observed_at=datetime(2026, 9, 5, 12, tzinfo=UTC), material_fields=("substitutability",),
                       detail="substitutability 5 → 3")
    view = _view(judgment=_stale_judgment(), allow_stale=True, refresh_changes=[edge])
    scores = {d.key: d for d in view.variant_view.scores}
    assert scores["value_capture_score"].status == "review_required"      # 引用了那條邊
    assert scores["expectation_gap_score"].status == "review_required"    # fixture 的 Q4 也引用同一條邊
    assert scores["structural_score"].status == "available"               # Q1 每次重算
    assert view.variant_view.meta.status == "review_required"             # thesis 引用聯集含那條邊
    assert "review_required" in SECTION_STATUSES and "invalidated" in SECTION_STATUSES
    assert REFRESH_STATUSES <= SECTION_STATUSES
    text = render_alpha_investment_view_markdown(view)
    assert "## 15. Refresh／dependency status" in text and "需複查" in text


def test_assumption_states_flow_into_bridge_datums_and_compact_card() -> None:
    from alpha.refresh import ChangeEvent

    model = _run()
    guidance = ChangeEvent(change_type=COMPANY_GUIDANCE, ticker="COHR", company_id="co:coherent",
                           authority="engine_c://manual_observations", changed_ref="engine_c://manual_observation/g2",
                           observed_at=datetime(2026, 11, 11, tzinfo=UTC), published_at=date(2026, 11, 10),
                           material_fields=("tax_rate_low", "tax_rate_high"), detail="Q2 FY27 稅率指引")
    view = _view(judgment=_stale_judgment(), allow_stale=True, fundamental_model=model, refresh_changes=[guidance],
                 today=date(2026, 11, 12))
    by_key = {d.key: d for d in view.earnings_bridge.assumptions}
    assert by_key["assumption:tax_rate:total"].status == "review_required"
    assert by_key["assumption:tax_rate:total"].dependencies["refresh_state"] == "review_required"
    assert by_key["assumption:tax_rate:total"].dependencies["provenance_semantics"] in ("v2", "legacy")
    assert by_key["assumption:tax_rate:total"].dependencies["requires_review_on_support_change"] is True
    assert by_key["assumption:diluted_shares:total"].status == "available"
    eps = next(d for d in view.internal_fundamentals.items if d.key == "internal_eps")
    assert eps.status == "review_required" and eps.dependencies["refresh_propagated_from"]
    card = compact_card(view)
    assert card["refresh"]["counts"]["review_required"] >= 2
    row = next(l for l in render_alpha_cards([card]) if l.startswith("| co:coherent"))
    assert "⚠ 複查" in row
    payload = json.loads(json.dumps(view.to_dict(), ensure_ascii=False))
    assert payload["refresh_status"]["overall"] == "review_required"
    assert all(item["state"] in ("current", "recalculate", "review_required", "invalidated", "stale",
                                 "superseded", "missing") for item in payload["refresh_status"]["items"])


def test_fetch_view_runs_detection_with_injected_providers_and_scenarios(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from briefing.alpha_view import sources

    monkeypatch.setattr(sources, "DECISION_DB", tmp_path / "nope.db")
    monkeypatch.setattr(sources, "LIFECYCLE_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(sources, "JUDGMENT_DIR", tmp_path / "judgments")
    monkeypatch.setattr(sources, "LEGACY_JUDGMENT_DIR", tmp_path / "legacy")
    import engine_c.checklist as checklist_mod

    monkeypatch.setattr(checklist_mod, "get_checklist", lambda ticker: {"engine_c_available": False})
    judgment_path = tmp_path / "j.json"
    judgment_path.write_text(json.dumps(_stale_judgment(), ensure_ascii=False), encoding="utf-8")

    class _Series(_FakeFundamentals):
        def snapshot_series(self, ticker, *, since, as_of=None):
            return [_row("2026-09-03", "2026-09-04", "2026-09-04 11:50:00+00:00", 264.41, 18.94691),
                    _row("2026-09-04", "2026-09-05", "2026-09-05 11:53:40+00:00", 281.86, 20.197329)]

        def observation_history(self, ticker, field_name, *, as_of=None):
            return []

    view = sources.fetch_alpha_investment_view(
        "COHR", today=date(2026, 9, 5), judgment_path=judgment_path,
        graph_provider=FakeGraphResearchProvider(company_id=COMPANY, evidence_pool=(_CORROBORATED,)),
        fundamentals_provider=_Series(), watches=[])
    kinds = {c.change_type for c in view.refresh_status.changes}
    assert MARKET_PRICE in kinds
    # FakeGraphResearchProvider 固定回一個 since 當天的結構事件；Q2 若引用它就 review_required——這是引擎在運作，
    # 不是 digest：identity 仍說 context 不一致，但 status 來自分類後的變化。
    assert view.refresh_status.change_detection == "authority_time_series"
    assert view.identity.signal.context_matches is False
    scenario = sources.fetch_alpha_investment_view(
        "COHR", today=date(2026, 9, 5), judgment_path=judgment_path, scenario="price_only",
        graph_provider=FakeGraphResearchProvider(company_id=COMPANY, evidence_pool=(_CORROBORATED,)),
        fundamentals_provider=_Series(), watches=[], detect_refresh=False)
    assert scenario.refresh_status.change_detection == "scenario"
    assert any(c.authority == "scenario://market_price" for c in scenario.refresh_status.changes)
    with pytest.raises(Exception, match="未知情境"):
        sources.fetch_alpha_investment_view("COHR", scenario="vibes", graph_provider=FakeGraphResearchProvider(company_id=COMPANY),
                                            fundamentals_provider=_Series())
