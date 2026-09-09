"""Valuation Model v1（Phase 2 Step 1，2026-09-06）——**內部基本面 → 明示估值假設 → 確定性 fair value**。

```
alpha/fundamental（內部 FY 目標期間 EPS）─┐
ValuationAssumption（private append-only ledger，session 明示）┼─► build_valuation ─► ValuationResult
Engine C 現價（A2，唯讀）───────────────────────────────────────┘        fair_value／current_price／gap
```

## 這一層回答什麼、不回答什麼

回答：**根據我們自己的 EPS 與我們自己明示的目標倍數，這門生意值多少；跟現價差多少。**
不回答（Step 2 以後）：預期報酬、horizon、進場價、買賣、機率加權情境、部位。

## 認識論分界（與 `alpha/fundamental` 同一條）

「FY2027 non-GAAP 目標本益比 25x」是 session 判斷（`basis=session_judgment`），不是事實；
「fair value ＝ 內部 EPS × 25」是確定性算術。每個輸出都同時帶 `calculation="deterministic"` 與
`input_dependency`（所有輸入判斷中最弱的知識種類）。**沒有 hidden default multiple**：ledger 沒有
生效假設就是 `missing`，不由程式或 LLM 補。

## 相依邊界

純邏輯層：零外部相依、不開連線、不讀檔。ledger I/O 在 `alpha/providers/valuation_assumptions.py`；
現價由 `alpha/providers/fundamentals.py`（Engine C）取出後注入。
"""
from __future__ import annotations

from .assumptions import (
    RECORD_VERSION, new_valuation_assumption_id, parse_valuation_assumption_record,
    select_valuation_assumptions, valuation_assumption_record,
)
from .contracts import (
    FAIR_VALUE_FORMULA, GAP_FORMULA, GAP_STATUSES, IMPLIED_MULTIPLE_FORMULA,
    METHOD_ACCOUNTING_BASES, METHOD_EV_TO_SALES,
    METHOD_FORWARD_EARNINGS_MULTIPLE, METHOD_FUNDAMENTAL_INPUT, METHOD_PARAMETERS, MODEL_VERSION,
    VALUATION_ACCOUNTING_BASES, VALUATION_METHODS, VALUATION_STATUSES, VALUE_DATE_CONVENTIONS,
    BalanceSheetInput,
    VALUE_DATE_FORMULA, VALUE_DATE_SEMANTICS, VALUE_DATE_SPOT, VALUE_DATE_TARGET_PERIOD_END,
    VALUE_DATE_UNSPECIFIED, CurrentPrice, FairValueGap,
    FairValueSensitivity, FundamentalInput, ValuationAssumption, ValuationResult, ValuationStep,
    combined_input_dependency,
)
from .model import build_valuation, units_comparable

__all__ = [
    "FAIR_VALUE_FORMULA", "GAP_FORMULA", "GAP_STATUSES", "IMPLIED_MULTIPLE_FORMULA",
    "METHOD_ACCOUNTING_BASES", "METHOD_EV_TO_SALES", "BalanceSheetInput",
    "METHOD_FORWARD_EARNINGS_MULTIPLE", "METHOD_FUNDAMENTAL_INPUT", "METHOD_PARAMETERS", "MODEL_VERSION",
    "RECORD_VERSION", "VALUATION_ACCOUNTING_BASES", "VALUATION_METHODS", "VALUATION_STATUSES",
    "VALUE_DATE_CONVENTIONS", "VALUE_DATE_FORMULA", "VALUE_DATE_SEMANTICS", "VALUE_DATE_SPOT",
    "VALUE_DATE_TARGET_PERIOD_END", "VALUE_DATE_UNSPECIFIED",
    "CurrentPrice", "FairValueGap", "FairValueSensitivity", "FundamentalInput", "ValuationAssumption",
    "ValuationResult", "ValuationStep", "build_valuation", "combined_input_dependency",
    "new_valuation_assumption_id", "parse_valuation_assumption_record", "select_valuation_assumptions",
    "units_comparable", "valuation_assumption_record",
]
