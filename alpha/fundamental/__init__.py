"""會計期間、營運假設 ledger 邏輯、Engine C 觀測與共識的型別——**沒有模型**。

⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：Causal Fundamental Model（FY+1 因果橋）退役。**
原本這個套件是「明示假設 → 確定性財務橋 → 內部基本面 → 同期共識 → 數值落差」整條鏈
（`bridge.py`／`model.py`／`compare.compare_metric`）。ROADMAP Phase 0（G3）：財務只回答三個是非題
（會死嗎／已定價嗎／出現在數字裡了嗎），**不得長回估值模型**——FY+1 預測正是那條鏈的第一節。

留下來的三樣東西各有各的活消費端：

- `contracts.py`：`FiscalPeriod`／`OperatingAssumption`／`FiscalYearActuals`／`ConsensusEstimate`／
  `GuidanceObservation`／`InterimPeriodResults`——Engine C provider（`alpha/providers/fundamentals.py`）
  與 read model 的共識 section 讀它們；`ASSUMPTION_DRIVERS` 是 `DisproofCondition.invalidates` 的封閉字彙。
- `assumptions.py`：營運假設 ledger 紀錄的解析、選取、supersede——ledger 是 A3 append-only authority（L10），
  催化劑熟成度與 refresh 的假設 artifact 仍讀它；只是沒有任何模型再拿它算數字。
- `compare.py`：共識口徑核實（`verify_consensus_basis`）與基期對帳（`reconcile_consensus_base`）——
  資料層的機械比對，三題「已定價」要用。

相依邊界不變：純邏輯層，零外部相依、不開連線、不讀檔。I/O 在 `alpha/providers/`。
"""
from __future__ import annotations

from .assumptions import (
    assumption_record, new_assumption_id, parse_assumption_record, select_assumptions,
    select_scenario_assumptions,
)
from .compare import fx_tolerated_delta, reconcile_consensus_base, verify_consensus_basis
from .contracts import (
    ACCOUNTING_BASES, ASSUMPTION_BASES, ASSUMPTION_DRIVERS, ASSUMPTION_SCENARIOS, BASE_SCENARIO,
    VARIANT_SCENARIO, DOWNSIDE_SCENARIO, OVERLAY_SCENARIOS, SCENARIO_LABELS,
    FISCAL_PERIOD_KINDS, PERIOD_MATCH_TOLERANCE_DAYS, TOTAL_SCOPE,
    AssumptionSelection, ConsensusEstimate, DriverSpec,
    FiscalPeriod, FiscalYearActuals, GuidanceObservation, InterimPeriodResults, OperatingAssumption,
)

__all__ = [
    "ACCOUNTING_BASES", "ASSUMPTION_BASES", "ASSUMPTION_DRIVERS", "ASSUMPTION_SCENARIOS",
    "BASE_SCENARIO", "VARIANT_SCENARIO", "DOWNSIDE_SCENARIO", "OVERLAY_SCENARIOS",
    "SCENARIO_LABELS", "select_scenario_assumptions",
    "FISCAL_PERIOD_KINDS", "PERIOD_MATCH_TOLERANCE_DAYS", "TOTAL_SCOPE", "AssumptionSelection",
    "ConsensusEstimate", "DriverSpec", "FiscalPeriod",
    "FiscalYearActuals", "GuidanceObservation", "InterimPeriodResults",
    "OperatingAssumption", "assumption_record", "fx_tolerated_delta", "new_assumption_id",
    "parse_assumption_record", "reconcile_consensus_base", "select_assumptions", "verify_consensus_basis",
]
