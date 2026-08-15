"""Blocker 字彙登記表與「等決定／等事件」分類的迴歸測試。

這是讀側分類層：只描述既有 blocker code 的意義，不改變產生方式，因此不影響已凍結的
decision payload。兩道剎車：

1. **字彙漂移**：codebase 裡實際會產生的 blocker literal 必須都能在 registry 命中。
   新增 blocker 卻忘了登記，會讓它掉進 UNKNOWN，然後（依保守預設）被當成需要使用者
   決定——那正是待辦池噪音的來源。
2. **保守分類**：只要有一個 blocker 需要人決定，整個項目就必須留在決策佇列。
   寧可多問一次，也不要安靜地把需要決定的事藏進「等事件」。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from decision_lab.blockers import (
    RESOLUTION_MODES,
    UNKNOWN,
    BlockerRegistry,
    BlockerRegistryError,
    describe_blocker,
    get_blocker_registry,
)

ROOT = Path(__file__).resolve().parent.parent


def test_registry_loads() -> None:
    registry = get_blocker_registry()
    assert registry.version >= 1


def test_every_blocker_literal_in_the_codebase_is_registered() -> None:
    """漂移剎車：實際會產生的 blocker literal 必須都命中 registry。"""
    sources = [
        ROOT / "decision_lab" / "coverage.py",
        ROOT / "decision_lab" / "sizing.py",
        ROOT / "engine_d_runtime" / "adapters.py",
    ]
    # 只擷取真正 append 到 blocker 清單的 literal；work order 的 missing_fields
    # 也用 .append("...")，但那不是 blocker 字彙。
    pattern = re.compile(r'\bblockers\.append\(\s*"([a-z][a-z0-9_]*)"')
    literals: set[str] = set()
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            literals.add(match.group(1))
    assert literals, "應至少擷取到一些 blocker literal，否則此測試失去意義"
    unregistered = sorted(
        code for code in literals if describe_blocker(code) is UNKNOWN
    )
    assert not unregistered, (
        f"以下 blocker 未登記於 config/decision_blockers.json：{unregistered}"
    )


def test_parameterised_blockers_resolve_via_longest_prefix() -> None:
    registry = get_blocker_registry()
    # financial_checklist_ 必須勝過較短的 financial_
    assert (
        registry.describe("financial_checklist_manual_required:AAOI").next_step
        != registry.describe("financial_backlog_missing").next_step
    )
    assert registry.describe("assessment_context_mismatch:valuation_payoff").needs_user


def test_axis_unknown_suffix_is_recognised() -> None:
    spec = describe_blocker("commercial_maturity_unknown")
    assert spec is not UNKNOWN
    assert spec.resolution_mode == "user_decision"


def test_unknown_blocker_defaults_to_needing_a_human() -> None:
    """未登記一律當成需要人看——安靜吞掉才是危險的。"""
    spec = describe_blocker("a_code_that_does_not_exist")
    assert spec is UNKNOWN
    assert spec.needs_user


def test_research_intent_noise_is_not_treated_as_a_gap() -> None:
    """research intent 的必然結果不該被呈現為缺口。"""
    for code in (
        "execution_intent_research_only",
        "paper_context_not_ready",
        "live_context_not_ready",
        "holdings_unconfirmed",
    ):
        assert describe_blocker(code).resolution_mode == "system_internal", code


def test_needs_user_decision_is_conservative() -> None:
    registry = get_blocker_registry()
    # 一堆等外部 + 一個需決定 → 仍須留在決策佇列
    assert registry.needs_user_decision(
        ["financial_missing", "market_missing", "identity_unresolved"]
    )
    # 全部真的等外部 → 可轉為等待
    assert not registry.needs_user_decision(
        ["financial_missing", "market_missing", "research_ticker_unavailable"]
    )


def test_agent_research_gaps_are_not_hidden_as_external_events() -> None:
    """人工判讀／bounded research 是可立即 dispatch 的工作，不是世界事件。"""

    for code in (
        "counter_path_missing",
        "research_assessment_missing",
        "financial_runway_manual_required",
        "financial_checklist_manual_required:backlog",
        "financial_resilience_corroboration_incomplete",
        "commercial_maturity_unknown",
    ):
        assert describe_blocker(code).resolution_mode == "user_decision", code


def test_waiting_reasons_are_deduplicated_and_human_readable() -> None:
    registry = get_blocker_registry()
    reasons = registry.waiting_reasons(
        ["financial_backlog_missing", "financial_dilution_missing", "market_missing"]
    )
    assert reasons
    assert len(reasons) == len(set(reasons))
    assert all(not r.startswith(("financial_", "market_")) for r in reasons)


def test_classify_partitions_every_blocker() -> None:
    registry = get_blocker_registry()
    codes = ["identity_unresolved", "market_missing", "live_context_not_ready"]
    grouped = registry.classify(codes)
    assert set(grouped) == set(RESOLUTION_MODES)
    assert sum(len(v) for v in grouped.values()) == len(codes)


def test_registry_rejects_entry_with_both_code_and_prefix() -> None:
    with pytest.raises(BlockerRegistryError, match="exactly one"):
        BlockerRegistry.from_payload(
            {
                "version": 1,
                "blockers": [
                    {
                        "code": "x",
                        "prefix": "x_",
                        "label": "L",
                        "category": "c",
                        "resolution_mode": "user_decision",
                        "next_step": "n",
                    }
                ],
            }
        )


def test_registry_rejects_unknown_resolution_mode() -> None:
    with pytest.raises(BlockerRegistryError, match="unknown resolution_mode"):
        BlockerRegistry.from_payload(
            {
                "version": 1,
                "blockers": [
                    {
                        "code": "x",
                        "label": "L",
                        "category": "c",
                        "resolution_mode": "maybe",
                        "next_step": "n",
                    }
                ],
            }
        )


def test_shipped_config_is_valid_json_with_all_required_fields() -> None:
    payload = json.loads(
        (ROOT / "config" / "decision_blockers.json").read_text(encoding="utf-8")
    )
    for entry in payload["blockers"]:
        assert entry["resolution_mode"] in RESOLUTION_MODES
        assert entry["label"].strip()
        assert entry["next_step"].strip()
