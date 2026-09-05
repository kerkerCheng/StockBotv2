"""Causal Fundamental Model——**明示假設 → 確定性財務橋 → 內部基本面 → 同期共識 → 數值落差**。

## 這一層回答什麼

Phase 1 的 read model 回答「StockBot 目前知道什麼」；這一層開始回答：

> 根據我們知道的，我們對這門生意**明確假設**了什麼；那些假設**推得出**什麼財務數字；
> 那些數字跟市場共識**差多少**。

```
Structural / causal evidence（Engine A、Engine C）
        ↓ 引用
OperatingAssumption（明示、帶 basis／provenance／as-of；住 private append-only ledger）
        ↓ 確定性算術
FinancialBridge（revenue → margin → operating income → EPS，每一步可追溯）
        ↓
InternalFundamentalEstimate（每個數字都指得回假設與觀測）
        ↓ 只在同一會計期間、同一口徑時
ExpectationComparison（internal vs consensus，數值 gap）
```

## 最重要的一條認識論分界：**假設的判斷 ≠ 算術的確定性**

「FY2027 datacom 營收成長 +60%」是 session 的判斷（`basis=session_judgment`），
不是事實；「FY2027 分部營收 ＝ 基期 × (1 + 成長)」是確定性算術。兩者**分開標**：
每個模型輸出的 `calculation` 是 deterministic，而它的 `input_dependency` 帶著最弱那條
輸入假設的知識種類。消費端不得因為輸出是公式算出來的，就把底下的假設讀成事實。

## 刻意不做的事

- **不讓 LLM 直接吐 EPS。** session 只能寫 `OperatingAssumption`；數字由 `bridge.py` 算。
- **不猜缺席。** 少一條假設就是 `missing`（不是 0 成長、不是 0% 利潤率）。
- **不硬減。** 期間不同、口徑不同（GAAP vs non-GAAP）、幣別不同一律 `incompatible_*`。
- **不做估值。** 沒有 DCF、目標價、預期報酬、進場價——那是下一階段。
- **不碰部位。** `AlphaSignal != Position` 在這裡同樣成立。
- **不成為 Engine C 的第二份 current-state authority。** 觀測與共識只從 Engine C 讀。

## 相依邊界

本套件是 `alpha/` 的純邏輯層：零外部相依、不開連線、不讀檔。假設 ledger 的 I/O 在
`alpha/providers/assumptions.py`，Engine C 的觀測／共識 I/O 在 `alpha/providers/fundamentals.py`。
"""
from __future__ import annotations

from .assumptions import (
    assumption_record, new_assumption_id, parse_assumption_record, select_assumptions,
)
from .bridge import BRIDGE_VERSION, BridgeResult, build_bridge
from .compare import compare_metric, verify_consensus_basis
from .contracts import (
    ACCOUNTING_BASES, ASSUMPTION_BASES, ASSUMPTION_DRIVERS, COMPARISON_STATUSES,
    FISCAL_PERIOD_KINDS, MODEL_VERSION, PERIOD_MATCH_TOLERANCE_DAYS, TOTAL_SCOPE,
    AssumptionSelection, BridgeStep, ConsensusEstimate, DriverSpec, ExpectationComparison,
    FiscalPeriod, FiscalYearActuals, FundamentalModelResult, GuidanceObservation,
    ModeledMetric, OperatingAssumption, Sensitivity,
)
from .model import build_fundamental_model

__all__ = [
    "ACCOUNTING_BASES", "ASSUMPTION_BASES", "ASSUMPTION_DRIVERS", "BRIDGE_VERSION",
    "COMPARISON_STATUSES", "FISCAL_PERIOD_KINDS", "MODEL_VERSION",
    "PERIOD_MATCH_TOLERANCE_DAYS", "TOTAL_SCOPE", "AssumptionSelection", "BridgeResult",
    "BridgeStep", "ConsensusEstimate", "DriverSpec", "ExpectationComparison", "FiscalPeriod",
    "FiscalYearActuals", "FundamentalModelResult", "GuidanceObservation", "ModeledMetric",
    "OperatingAssumption", "Sensitivity", "assumption_record", "build_bridge",
    "build_fundamental_model", "compare_metric", "new_assumption_id",
    "parse_assumption_record", "select_assumptions", "verify_consensus_basis",
]
