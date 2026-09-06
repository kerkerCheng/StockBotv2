"""Dependency impact 的**規則表**——明示、版本化、可測。不是散落的 if-else。

## 為什麼是表不是程式

Step 0（2026-09-06）實測：完整 `ResearchContext.digest` 一變，variant view／Q4／
falsification／scenarios 全部一起 stale——**一個每日 price tick 讓整份研究判斷過期**。
修法不是把 digest 拆細，是把「哪一類變化影響哪一類成果、影響成什麼 state」寫成一張
可以整張被審的表。改一格要能答出「現有 N 個成果的 state 會變」（L14）。

## v1 的 materiality 立場（刻意保守，且明說）

- **價格變動只讓確定性的市場導出量 `recalculate`；任何研究判斷維持 `current`**，直到
  出現明確事件（共識修正、新指引、結構事件、disproof）或排程複查到期。
  理由：沒有任何經量測的門檻能說「漲 6.6% 就該重看 Q4、漲 0.6% 不用」；假裝有一個
  統計上站得住的門檻比誠實說「價格不觸發複查」更危險（AGENTS L14）。
- **共識修正**有一道 1% 的**雜訊地板**（`CONSENSUS_NOISE_FLOOR_REL`）——它擋的是
  yfinance 四捨五入的抖動，**不是** materiality 門檻，不得被讀成「1% 以上才重要」。
"""
from __future__ import annotations

from typing import Mapping

from .contracts import (
    COMPANY_GUIDANCE, CONSENSUS, CONTEXT_DIGEST, CURRENT, DISPROOF_SIGNAL, EVIDENCE,
    FINANCIAL_ACTUAL, FISCAL_PERIOD_ROLLOVER, GRAPH_CLAIM, GRAPH_EDGE, MARKET_PRICE,
    OPERATING_ASSUMPTION, RECALCULATE, REVIEW_REQUIRED, STALE, THESIS_REVIEW_DUE, VALUATION_ASSUMPTION,
)

POLICY_VERSION = "refresh-policy/v1"

#: 共識導出值（forward EPS／FY 估計）的雜訊地板：相對變化低於此值不視為 change。
#: ⚠ 這是資料抖動的地板，不是 materiality——見模組 docstring。
CONSENSUS_NOISE_FLOOR_REL = 0.01

#: 結構類 change：命中「被引用的 ref」才影響判斷型成果；Q1 是公司層級的確定性函數，
#: 這家公司任何結構事件都 recalculate。
STRUCTURAL_CHANGE_TYPES: frozenset[str] = frozenset({GRAPH_EDGE, GRAPH_CLAIM, EVIDENCE})

#: **公司層級**（不看引用）的軸影響表。key＝change class，value＝axis → state。
#: 沒列的組合＝`current`。
#:
#: 讀法舉例：`consensus` 只動 Q4；`financial_actual` 動 Q2（利潤率是價值攫取的直接輸入）、
#: Q3（分部組合）、Q5（財報本身是催化劑里程碑）；`company_guidance` 動 Q2（毛利指引）與
#: Q4（指引重設市場預期）；`operating_assumption` 動 Q4（內部觀點變了）。
#: `market_price` **一格都沒有**——這是 v1 的 materiality 立場，見模組 docstring。
AXIS_POLICY: Mapping[str, Mapping[str, str]] = {
    MARKET_PRICE: {},
    CONSENSUS: {"expectation_gap": REVIEW_REQUIRED},
    FINANCIAL_ACTUAL: {
        "value_capture": REVIEW_REQUIRED, "earnings_exposure": REVIEW_REQUIRED,
        "catalyst": REVIEW_REQUIRED,
    },
    COMPANY_GUIDANCE: {"value_capture": REVIEW_REQUIRED, "expectation_gap": REVIEW_REQUIRED},
    GRAPH_EDGE: {"structural": RECALCULATE},
    GRAPH_CLAIM: {"structural": RECALCULATE},
    EVIDENCE: {"structural": RECALCULATE},
    OPERATING_ASSUMPTION: {"expectation_gap": REVIEW_REQUIRED},
    VALUATION_ASSUMPTION: {},       # 估值判斷變了不動任何基本面判斷（Step 1 立場，明說）
    FISCAL_PERIOD_ROLLOVER: {},
    THESIS_REVIEW_DUE: {},          # 由排程規則統一處理（所有判斷型成果 stale）
    DISPROOF_SIGNAL: {},            # 由 target_artifact 指名處理
    CONTEXT_DIGEST: {
        "value_capture": REVIEW_REQUIRED, "earnings_exposure": REVIEW_REQUIRED,
        "expectation_gap": REVIEW_REQUIRED, "catalyst": REVIEW_REQUIRED,
    },
}

#: thesis／variant view／disproof（一份判斷的敘事層）的 class 規則。變動市場預期或基本面觀測的事件
#: 都會動到「市場隱含 X／本 thesis 認為 Y」的其中一半；價格本身不動它（v1 立場）。
THESIS_POLICY: Mapping[str, str] = {
    CONSENSUS: REVIEW_REQUIRED,
    FINANCIAL_ACTUAL: REVIEW_REQUIRED,
    COMPANY_GUIDANCE: REVIEW_REQUIRED,
    CONTEXT_DIGEST: REVIEW_REQUIRED,
}

#: 假設層級的 class 規則（不看引用）。value＝basis → state；`*`＝任何 basis。
ASSUMPTION_CLASS_POLICY: Mapping[str, Mapping[str, str]] = {
    MARKET_PRICE: {},
    CONSENSUS: {},                                   # 只透過 calibration ref 命中才影響
    # proxy／observation 型假設沿用較舊的觀測；新實際值到了就該重看。session 判斷型不因此重看
    # （會計年度推進另由 fiscal_period_rollover 處理；review_conditions 由條件對照處理）。
    FINANCIAL_ACTUAL: {"heuristic_proxy": REVIEW_REQUIRED, "observation": REVIEW_REQUIRED},
    COMPANY_GUIDANCE: {},                            # 透過 driver 相關性處理（GUIDANCE_FIELD_DRIVERS）
    OPERATING_ASSUMPTION: {},
    VALUATION_ASSUMPTION: {},
    CONTEXT_DIGEST: {},
}

#: 指引欄位（去掉 `_low`／`_high`／`_mid` 後綴）→ 受影響的 driver。`None`＝沒有直接對應的 driver。
GUIDANCE_FIELD_DRIVERS: Mapping[str, str | None] = {
    "revenue": "revenue_growth",
    "gross_margin": "operating_margin_delta",
    "opex": "operating_margin_delta",
    "operating_margin": "operating_margin_delta",
    "operating_income": "operating_margin_delta",
    "tax_rate": "tax_rate",
    "diluted_shares": "diluted_shares",
    "shares": "diluted_shares",
    "interest": "interest_and_other_net",
    "interest_and_other_net": "interest_and_other_net",
    "eps": None,
}

#: 確定性成果的 class 規則：這幾類 change 直接讓它們重算（不需判斷）。
DERIVED_CLASS_POLICY: Mapping[str, frozenset[str]] = {
    "market_implied": frozenset({MARKET_PRICE, CONSENSUS}),
    "expectation_comparison": frozenset({CONSENSUS}),
    "modeled_metric": frozenset({FINANCIAL_ACTUAL}),
    "fundamental_model": frozenset({FINANCIAL_ACTUAL}),
    # Step 1：fair value 只隨基期實際值與（經 assumption_ids 命中的）假設重算；**market_price 不在列**——
    # 價格不進 fair value。gap 才吃價格。
    "fair_value": frozenset({FINANCIAL_ACTUAL}),
    "fair_value_gap": frozenset({MARKET_PRICE, FINANCIAL_ACTUAL}),
}

#: L7 的核查頻率 → 天數。字串比對（含中英文），比不到＝不知道，不排程 stale（並列 note）。
CHECK_FREQUENCY_DAYS: Mapping[str, int] = {
    "daily": 1, "每日": 1, "weekly": 7, "每週": 7, "monthly": 31, "每月": 31,
    "quarterly": 92, "每季": 92, "semiannual": 183, "半年": 183, "annual": 366, "每年": 366,
}


def frequency_to_days(text: str | None) -> int | None:
    if not text:
        return None
    lowered = text.lower()
    for token, days in CHECK_FREQUENCY_DAYS.items():
        if token in lowered:
            return days
    return None


def guidance_driver(field_name: str) -> str | None:
    """`revenue_low` → `revenue_growth`；對不上的欄位回 None（不是「沒影響」，是「不知道影響誰」）。"""
    name = field_name.lower()
    for suffix in ("_low", "_high", "_mid", "_midpoint"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return GUIDANCE_FIELD_DRIVERS.get(name)


__all__ = [
    "ASSUMPTION_CLASS_POLICY", "AXIS_POLICY", "THESIS_POLICY", "CHECK_FREQUENCY_DAYS", "CONSENSUS_NOISE_FLOOR_REL",
    "DERIVED_CLASS_POLICY", "GUIDANCE_FIELD_DRIVERS", "POLICY_VERSION", "STRUCTURAL_CHANGE_TYPES",
    "frequency_to_days", "guidance_driver",
]
