"""The remote source-trace manual endpoint fails readably."""

from __future__ import annotations

from pathlib import Path

from mcp_server.graph_mcp import (
    SOURCE_TRACE_MANUAL,
    _read_source_trace_manual,
    get_extraction_rules,
    mcp,
)


def test_source_trace_manual_returns_full_routing_table() -> None:
    content = _read_source_trace_manual()

    assert content == SOURCE_TRACE_MANUAL.read_text(encoding="utf-8")
    assert "路由鏈" in content
    assert "isolated_tier_3" in content


def test_missing_source_trace_manual_returns_error_without_raising(tmp_path) -> None:
    content = _read_source_trace_manual(tmp_path / "missing.md")

    assert "追源手冊目前不可用" in content
    assert "不要" in content


def test_extraction_rules_include_remote_intake_and_conflict_protocol() -> None:
    content = get_extraction_rules()

    assert "Storage permission" in content
    assert "`partial`" in content
    assert "open_conflict_ids" in content
    assert "prepare_research_action" in content
    assert "apply_research_action" in content
    assert "finalize_research_action(" not in content
    assert "scripts/commit_pending_intake.py" in content


def test_remote_tool_surface_has_ten_tools_and_no_git_finalize() -> None:
    tools = mcp._tool_manager._tools

    assert set(tools) == {
        "get_graph_context",
        "run_read_query",
        "get_financial_checklist",
        "get_decision_brief",
        "get_extraction_rules",
        "get_source_trace_manual",
        "load_extraction",
        "prepare_research_action",
        "get_research_action_status",
        "apply_research_action",
    }
    # 新增的決策 brief 工具必須是唯讀（不 freeze／不建 decision／不下單）。
    assert tools["get_decision_brief"].annotations.readOnlyHint is True
    assert tools["get_research_action_status"].annotations.readOnlyHint is True
    assert tools["prepare_research_action"].annotations.idempotentHint is False
    assert tools["apply_research_action"].annotations.idempotentHint is True
    assert tools["apply_research_action"].annotations.destructiveHint is False


def test_mcp_dependency_is_bounded_to_stable_v1() -> None:
    requirements = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert "mcp>=1.28,<2" in requirements
