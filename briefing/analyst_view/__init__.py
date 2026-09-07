"""Analyst Consumer（Phase 2 Step 3.5）：把 canonical read model 投影成 analyst 判讀畫面。

入口：`python -m briefing analyst-view <TICKER> [--as-of] [--format markdown|json]`。
**純消費端**：不重算、不新增公式、不寫任何 authority、不呼叫 LLM。
"""
from .compose import build_analyst_view
from .contracts import (
    CORE_PANELS, OPTIONAL_PANELS, QUESTIONS, SCHEMA_VERSION, AnalystLine, AnalystPanel,
    AnalystReadiness, AnalystView, AnalystViewContractViolation, RefreshSummary, WeakInput,
)
from .render import render_analyst_view_markdown

__all__ = [
    "CORE_PANELS", "OPTIONAL_PANELS", "QUESTIONS", "SCHEMA_VERSION", "AnalystLine", "AnalystPanel",
    "AnalystReadiness", "AnalystView", "AnalystViewContractViolation", "RefreshSummary", "WeakInput",
    "build_analyst_view", "render_analyst_view_markdown",
]
