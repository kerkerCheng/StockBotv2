"""The remote source-trace manual endpoint fails readably."""

from __future__ import annotations

from mcp_server.graph_mcp import SOURCE_TRACE_MANUAL, _read_source_trace_manual


def test_source_trace_manual_returns_full_routing_table() -> None:
    content = _read_source_trace_manual()

    assert content == SOURCE_TRACE_MANUAL.read_text(encoding="utf-8")
    assert "路由鏈" in content
    assert "isolated_tier_3" in content


def test_missing_source_trace_manual_returns_error_without_raising(tmp_path) -> None:
    content = _read_source_trace_manual(tmp_path / "missing.md")

    assert "追源手冊目前不可用" in content
    assert "不要" in content
