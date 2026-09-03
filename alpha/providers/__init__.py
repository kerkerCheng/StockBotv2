"""Concrete provider——**唯一被允許碰外部世界的 `alpha/` 子套件**。

`alpha/` 的其餘模組維持零外部相依（契約與模型層要能離線測試）；
Neo4j／Engine C／行情的 import 全部關在這裡。
`tests/test_layer_separation.py::test_alpha_has_no_external_or_engine_dependencies`
對本目錄開了明確例外，**不是整條檢查被關掉**。

⚠ **provider 包既有的 `query/`／`engine_c/`，不新寫查詢。**
`rank_bottlenecks()` 仍是唯一的結構排序權威（`AGENTS.md` 硬契約）；
這一層只做型別轉換與 provenance 附加，不重算、不加權、不另建平行排序。
"""
from __future__ import annotations

from .fundamentals import EngineCFundamentalsProvider
from .graph_neo4j import Neo4jGraphResearchProvider

__all__ = ["EngineCFundamentalsProvider", "Neo4jGraphResearchProvider"]
