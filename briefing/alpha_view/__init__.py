"""Alpha Investment View——單一公司投資理解的 canonical read model（`briefing/` 的組裝子套件）。

```
GraphResearchProvider ─┐
Engine C ──────────────┼─► build_research_context ─► ContextBuild ─┐
session judgment ──────┴─► compose_signal ────────► AlphaSignal ───┤
Engine D（公開 cohort 事實）／thesis lifecycle ─────────────────────┼─► build_alpha_investment_view
                                                                   │        │
                                                                   ▼        ▼
                                                    AlphaInvestmentView（canonical DTO）
                                                          │             │            │
                                                     Daily Brief       CLI       未來 Web／API
```

- `contracts.py`：型別與兩個語意軸（`status`／`basis`）。純 stdlib。
- `builder.py`：純函式組裝；所有 authority 輸出由參數注入。
- `render.py`：Markdown renderer；只依賴 `contracts` 與 `shared.markdown`。
- `sources.py`：唯一碰 I/O 的地方（Neo4j／Engine C／Decision Store／thesis JSON）。

⚠ 刻意不在這裡 re-export `sources`：import 本套件不應觸發任何 I/O 相依。
"""
from __future__ import annotations

from .builder import DecisionFacts, build_alpha_investment_view, compact_card
from .contracts import (
    SCHEMA_VERSION, AlphaInvestmentView, Datum, SectionMeta, ViewContractViolation,
)
from .render import render_alpha_cards, render_alpha_investment_view_markdown

__all__ = [
    "AlphaInvestmentView", "Datum", "DecisionFacts", "SCHEMA_VERSION", "SectionMeta",
    "ViewContractViolation", "build_alpha_investment_view", "compact_card",
    "render_alpha_cards", "render_alpha_investment_view_markdown",
]
