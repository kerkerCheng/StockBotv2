"""Base-case Implied Return v1（Phase 2 Step 2，2026-09-06）——**現價 ＋ fair value（含時點語意）＋ 明示 horizon → 確定性隱含價格報酬**。

```
alpha/valuation（fair value、value_date、input_dependency）─┐
HorizonAssumption（private append-only ledger，session 明示）┼─► build_implied_return ─► ImpliedReturnResult
Engine C 現價（A2，唯讀；含 bar_date）──────────────────────┘        price_return／annualized／holding period
```

## 這一層回答什麼、不回答什麼

回答：**從哪一天（現價 bar_date）到哪一天（horizon_end），在什麼假設下（內部 EPS 的營運假設＋目標倍數＋
value-date 語意＋realization horizon），現價走到 fair value 的 base-case 隱含價格報酬是多少。**
不回答：機率加權期望報酬（沒有機率）、總報酬（沒有股利預測）、進場價、買賣、部位、Valuation v2。

## 認識論分界

「fair value 於 2027-06-30 前實現」是 session 判斷（`HorizonAssumption.basis`）；「fair value 是 FY 期末的值」
是估值假設宣告的 `value_date_convention`；報酬與年化是確定性算術。每個輸出同時帶 `calculation="deterministic"`
與 `input_dependency`（所有輸入判斷中最弱者）。**沒有 hidden horizon**：ledger 沒有生效 horizon 就是 `missing`。

## 相依邊界

純邏輯層：零外部相依、不開連線、不讀檔。ledger I/O 在 `alpha/providers/horizon_assumptions.py`。
"""
from __future__ import annotations

from .assumptions import (
    RECORD_VERSION, horizon_assumption_record, new_horizon_assumption_id, parse_horizon_assumption_record,
    select_horizon_assumptions,
)
from .contracts import (
    ALIGNMENTS, ALIGNMENT_ALIGNED, ALIGNMENT_HORIZON_AFTER, ALIGNMENT_HORIZON_BEFORE, ALIGNMENT_SPOT,
    ANNUALIZED_RETURN_FORMULA, DAYS_PER_YEAR, HOLDING_PERIOD_FORMULA, HORIZON_DRIVER, HORIZON_START_FORMULA,
    MODEL_VERSION, PRICE_RETURN_FORMULA, RETURN_CONVENTIONS, RETURN_CONVENTION_BASE_CASE_PRICE, RETURN_STATUSES,
    TOTAL_RETURN_STATUSES, HorizonAssumption, ImpliedReturnResult, ReturnStep, combined_return_dependency,
)
from .model import build_implied_return

__all__ = [
    "ALIGNMENTS", "ALIGNMENT_ALIGNED", "ALIGNMENT_HORIZON_AFTER", "ALIGNMENT_HORIZON_BEFORE", "ALIGNMENT_SPOT",
    "ANNUALIZED_RETURN_FORMULA", "DAYS_PER_YEAR", "HOLDING_PERIOD_FORMULA", "HORIZON_DRIVER", "HORIZON_START_FORMULA",
    "MODEL_VERSION", "PRICE_RETURN_FORMULA", "RECORD_VERSION", "RETURN_CONVENTIONS",
    "RETURN_CONVENTION_BASE_CASE_PRICE", "RETURN_STATUSES", "TOTAL_RETURN_STATUSES", "HorizonAssumption",
    "ImpliedReturnResult", "ReturnStep", "build_implied_return", "combined_return_dependency",
    "horizon_assumption_record", "new_horizon_assumption_id", "parse_horizon_assumption_record",
    "select_horizon_assumptions",
]
