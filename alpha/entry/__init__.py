"""Entry Logic v1（Phase 2 Step 3，2026-09-06）——**implied return ＋ 明示的要求報酬判準 → analytical entry threshold**。

```
alpha/implied_return（現價、fair value、value_date、horizon、年化隱含報酬）─┐
EntryCriterion（投資人政策；private append-only ledger）── select(as_of) ──┼─► build_entry_assessment ─► EntryAssessmentResult
                                                                            │   entry_price ＝ fair_value / (1 + h) ** (days / 365.25)
                                                                            └   gap／comparison／assessment
```

## 這一層回答什麼、不回答什麼

回答：**在明示的年化要求報酬下，什麼價格以下現價才滿足這個門檻；現價相對門檻價在哪裡。**
不回答：該不該買、買多少、何時下單、部位／配置／資本許可——型別裡沒有那些欄位（import 時掃描）。
`meets_analytical_hurdle` 只是「現價 ≤ 門檻價」的算術事實，不得翻譯成「應該買」。

## Authority

判準（hurdle）是**投資人政策**：不是公司事實（A1／A2）、不是研究對公司的信念（A3 內容）、不是資本決策（A5）。
本層把它當注入的輸入（與 A2 現價同一種地位）：只讀、不猜、不補預設、不自動改。沒有就是 `missing`，
理由明寫「缺的是投資門檻判斷，不是資料 ETL 失敗」。全文見 `contracts.py` docstring。

## 相依邊界

純邏輯層：零外部相依、不開連線、不讀檔。ledger I/O 在 `alpha/providers/entry_criteria.py`。
"""
from __future__ import annotations

from .contracts import (
    ASSESSMENT_CLEAN, ASSESSMENT_REVIEW_REQUIRED, ASSESSMENT_STATES, CLEAN_ALIGNMENTS, COMPARISON_ABOVE,
    COMPARISON_MEETS, CONVENTION_ANNUALIZED_PRICE_RETURN, CRITERION_BASES, CRITERION_BASIS_INVESTOR_POLICY,
    CRITERION_DRIVER, ENTRY_CONVENTIONS, ENTRY_PRICE_FORMULA, ENTRY_STATUSES, FORBIDDEN_ENTRY_TOKENS,
    HURDLE_COMPARISONS, HURDLE_COMPARISON_RULE, MODEL_VERSION, PRICE_TO_ENTRY_GAP_FORMULA, EntryAssessmentResult,
    EntryCriterion, EntryStep,
)
from .criteria import (
    RECORD_VERSION, entry_criterion_record, new_entry_criterion_id, parse_entry_criterion_record,
    select_entry_criteria,
)
from .model import THIS_IS_NOT, build_entry_assessment

__all__ = [
    "ASSESSMENT_CLEAN", "ASSESSMENT_REVIEW_REQUIRED", "ASSESSMENT_STATES", "CLEAN_ALIGNMENTS", "COMPARISON_ABOVE",
    "COMPARISON_MEETS", "CONVENTION_ANNUALIZED_PRICE_RETURN", "CRITERION_BASES", "CRITERION_BASIS_INVESTOR_POLICY",
    "CRITERION_DRIVER", "ENTRY_CONVENTIONS", "ENTRY_PRICE_FORMULA", "ENTRY_STATUSES", "FORBIDDEN_ENTRY_TOKENS",
    "HURDLE_COMPARISONS", "HURDLE_COMPARISON_RULE", "MODEL_VERSION", "PRICE_TO_ENTRY_GAP_FORMULA", "RECORD_VERSION",
    "THIS_IS_NOT", "EntryAssessmentResult", "EntryCriterion", "EntryStep", "build_entry_assessment",
    "entry_criterion_record", "new_entry_criterion_id", "parse_entry_criterion_record", "select_entry_criteria",
]
