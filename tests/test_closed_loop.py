"""閉環（plan U3）：自動 Shadow、evidence-delta 精度、Shadow-first 變化%。"""
from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab import build_today_brief, ensure_shadow_for_company, evaluate_signal
from tests.test_operational_workflow import FixtureProvider, _request
from tests.test_decision_execution import _store


NOW = "2026-07-21T12:00:00+00:00"
_HOLDINGS = {"status": "available", "rows": []}


def _item(brief, company_id="co:sivers_semiconductors"):
    for it in brief["items"]:
        if it.get("company_id") == company_id:
            return it
    return None


def test_ensure_shadow_creates_then_reuses(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        first = ensure_shadow_for_company(
            store, provider,
            company_id="co:sivers_semiconductors", ticker="SIVE.ST", as_of=NOW,
        )
        assert first["created"] is True
        # 已有 probe → 不重複建，回既有
        second = ensure_shadow_for_company(
            store, provider,
            company_id="co:sivers_semiconductors", ticker="SIVE.ST", as_of=NOW,
        )
        assert second["created"] is False
        assert second["cohort_id"] == first["cohort_id"]
    finally:
        store.close()


def test_new_causal_evidence_is_material_and_flags_reassess(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        evaluate_signal(store, provider, _request(execution_intent="research"))
        # 圖出現觸及 thesis 因果結構的新證據
        provider.inputs["evidence"]["causal_paths"] = ["edge:cw-laser", "edge:new-order"]
        brief = build_today_brief(store, as_of=NOW, current_holdings=_HOLDINGS, provider=provider)
        item = _item(brief)
        assert item["evidence_delta"] == "material"
        # U7：item 的 `recommended_action` 改為 `attention`（MONITOR／REVIEW）。
        assert item["attention"] == "REVIEW"
        assert "reassess" in item["user_response_needed"]
    finally:
        store.close()


def test_source_only_change_is_peripheral_not_material(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        evaluate_signal(store, provider, _request(execution_intent="research"))
        # 只是這家公司多了一條 source，因果結構沒變 → peripheral，不強制 reassess
        provider.inputs["evidence"]["sources"] = [
            {"id": "src:new", "origin_entity": "X", "evidence_tier": 3}
        ]
        brief = build_today_brief(store, as_of=NOW, current_holdings=_HOLDINGS, provider=provider)
        item = _item(brief)
        assert item["evidence_delta"] == "peripheral"
    finally:
        store.close()


def test_terminal_probe_leaves_the_daily_queue(tmp_path: Path) -> None:
    """已結案（expired/rejected/promoted）的 probe 不該永遠留在每日待辦。"""
    from decision_lab.outcomes import close_probe

    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        result = evaluate_signal(store, provider, _request(execution_intent="research"))
        before = build_today_brief(store, as_of=NOW, current_holdings=_HOLDINGS,
                                   provider=provider)
        assert _item(before) is not None

        close_probe(
            store, result["cohort_id"],
            terminal_status="expired",
            claim_correctness="unknown",
            current_market={"status": "unavailable"},
            benchmark={"status": "unavailable"},
            reason="測試：probe 結案後不應再出現在每日待辦",
            evidence_refs=["admin:test"],
            effective_at=NOW,
        )
        after = build_today_brief(store, as_of=NOW, current_holdings=_HOLDINGS,
                                  provider=provider)
        assert _item(after) is None
    finally:
        store.close()


def test_price_move_alone_is_not_material(tmp_path: Path) -> None:
    store = _store(tmp_path)
    provider = FixtureProvider()
    try:
        evaluate_signal(store, provider, _request(execution_intent="research"))
        # 只動價格：evidence_delta 應為 none（價格波動 ≠ thesis 變，plan R12）
        provider.inputs["market"]["price"] = 3.0  # 2.5 → +20%
        brief = build_today_brief(store, as_of=NOW, current_holdings=_HOLDINGS, provider=provider)
        item = _item(brief)
        assert item["evidence_delta"] == "none"
        # Shadow-first：自追蹤變化% 應反映 3.0/2.5-1
        assert item["performance_since_tracked"] == pytest.approx(0.2)
    finally:
        store.close()
