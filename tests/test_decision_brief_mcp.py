"""Engine D `get_decision_brief` 遠端唯讀工具：pass-through、安全錯誤、關 store。"""
from __future__ import annotations

import json

from briefing.public_view import get_decision_brief_core
from mcp_server import graph_mcp


_FAKE_PRIVATE_PATH = "C:/Users/x/library/private/decision_lab/store.db"


class _FakeStore:
    def __init__(self, *, cohorts=None, raise_on_list=False):
        self._cohorts = cohorts or []
        self._raise = raise_on_list
        self.closed = False

    def list_operational_cohorts(self, *, as_of):
        del as_of
        if self._raise:
            raise RuntimeError(f"boom at {_FAKE_PRIVATE_PATH}")
        return list(self._cohorts)

    def capital_expression_counters(self):
        # brief 的 store contract 是窄 duck-type；這裡實作它是為了讓契約寫在測試裡，
        # 而不是靠 build_today_brief 的 getattr 靜默降級。真正沒有這個方法的
        # surface（遠端受限）會拿到 capital_expression=None，由 renderer 略過。
        return {
            "decisions": 0,
            "live_range_nonzero": 0,
            "outcomes": 0,
            "measured_outcomes": 0,
            "calculator_version": None,
            "decisions_current_calculator": 0,
            "live_range_nonzero_current": 0,
        }

    def close(self):
        self.closed = True


class _FakeProvider:
    def current_holdings(self, *, evaluation_at):
        del evaluation_at
        # confirmed-empty Sheet：可讀取、零列 → 乾淨的 MONITOR 基準。
        return {"status": "available", "rows": []}


# U7：四動作字彙已由兩態 `attention` 取代（見 decision_lab.models.ATTENTION_STATES）。
_VALID_ATTENTION = {"MONITOR", "REVIEW"}


def test_core_passes_through_redacted_public_dto() -> None:
    store = _FakeStore(cohorts=[])
    result = get_decision_brief_core(
        as_of="2026-07-23T00:00:00+00:00",
        store_factory=lambda: store,
        provider_factory=lambda: _FakeProvider(),
    )

    # 空 cohort → MONITOR，但仍具 attention-first 的欄位契約。
    assert result["attention"] == "MONITOR"
    assert result["action_needed"] is False
    for field in (
        "reason",
        "alpha_thesis_changes",
        "beta_portfolio_risk",
        "blockers",
        "next_review_at",
        "user_response_needed",
    ):
        assert field in result
    # `supported_sizing_range` 隨資本表達層於 U7 移除；遠端 surface 不得再看到它。
    assert "supported_sizing_range" not in result
    assert store.closed is True


def test_store_unavailable_is_explicit_without_leaking_private_path() -> None:
    def boom():
        raise RuntimeError(f"cannot open {_FAKE_PRIVATE_PATH}")

    result = get_decision_brief_core(store_factory=boom)

    assert result["status"] == "unavailable"
    # 錯誤只回型別名，絕不夾帶私有路徑或 str(exc)。
    assert "library/private" not in json.dumps(result, ensure_ascii=False)
    assert _FAKE_PRIVATE_PATH not in json.dumps(result, ensure_ascii=False)
    assert "RuntimeError" in result["note"]


def test_brief_generation_failure_is_safe_and_closes_store() -> None:
    store = _FakeStore(raise_on_list=True)
    result = get_decision_brief_core(
        store_factory=lambda: store,
        provider_factory=lambda: _FakeProvider(),
    )

    assert result["status"] == "error"
    assert "library/private" not in json.dumps(result, ensure_ascii=False)
    assert _FAKE_PRIVATE_PATH not in json.dumps(result, ensure_ascii=False)
    # store 即使在 build 失敗時也必須關閉。
    assert store.closed is True


def test_provider_unavailable_still_produces_brief() -> None:
    store = _FakeStore(cohorts=[])
    result = get_decision_brief_core(
        as_of="2026-07-23T00:00:00+00:00",
        store_factory=lambda: store,
        provider_factory=lambda: (_ for _ in ()).throw(RuntimeError("no sheet")),
    )

    # provider 壞掉不該讓整份 brief 失敗——holdings 缺失是狀態，不是 crash。
    assert result.get("attention") in _VALID_ATTENTION
    assert store.closed is True


def test_graph_mcp_wrapper_serializes_core_result(monkeypatch) -> None:
    monkeypatch.setattr(
        graph_mcp,
        "get_decision_brief_core",
        lambda: {"attention": "REVIEW", "action_needed": True, "items": []},
    )

    result = json.loads(graph_mcp.get_decision_brief())

    assert result["attention"] == "REVIEW"
    assert result["action_needed"] is True
