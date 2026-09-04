"""舊五軸 assessment 的軸名、研究提示與最弱軸判定——**唯一定義**。

## 為什麼在 shared

與 `shared/evidence_levels.py` 同一個理由，且是同一天（2026-09-04）被同一條線索
牽出來的：軸名有三份拷貝（`decision_lab/sizing.py::AXES`、
`alpha/legacy_axes.py::LEGACY_AXIS_TO_SCORE` 的鍵、以及測試裡的 literal set），
而最弱軸的**判定**有兩份實作。

⚠ 兩份實作的 tie-break 不一樣，實測（2026-09-04）：五軸同階時
`weakest_axis_of` 回 `source_reliability`（`AXES` 宣告序），
`alpha.legacy_axes.legacy_weakest` 回 `commercial_maturity`（軸名字母序，
因為它用 `min()` over `(rank, name)` tuple）。

**而 Phase 1 的 dual run 報告是「41 cohort、UNEXPECTED 0」。** 那不是兩者一致，
是那 41 筆剛好沒有並列最弱軸——L13 的形狀：檢查通過是因為案例沒發生，不是因為
邏輯相同。一個「對照用」的重算若與被對照者不同意，它報出來的 0 差異沒有意義。

修法是讓對照者用同一個宣告序（見 `legacy_weakest`），而要讓 `alpha/` 拿得到
`AXES`，它就只能住 shared——`alpha` 不得 import Engine D，Engine D 不得 import
`alpha`（L16 第 1 點的第 (b) 層：SSOT 有了，但沒送到需要它的地方）。

## 這是 contract 不是 taxonomy

`AXES` 的**次序有行為後果**（tie-break），且已凍進所有既有 decision payload。
新增一軸不是「加一列設定」，是改變 268 筆歷史紀錄的可比性。
"""
from __future__ import annotations

from typing import Any, Mapping

from .evidence_levels import LEVELS

__all__ = ["AXES", "AXIS_RESEARCH_PROMPT", "axis_sort_key", "weakest_axis_of"]

AXES = (
    "source_reliability",
    "technical_causal_link",
    "commercial_maturity",
    "financial_resilience",
    "valuation_payoff",
)

# 每一軸對應的「該補什麼」。最弱軸是排序的瓶頸，也是提高排序的唯一路徑，所以這句話
# 就是 pq2 項目的內容——使用者要看到的是「補 COHR 的 counter-path」，不是
# 「REVIEW — co:coherent」那種沒有成因的文字。
#
# ⚠ 與 AXES 綁在一起放，是為了讓新增一軸時被強迫決定它的研究動作（同
# schema/vocab.json 的 counter_path_relation 模式）。`tests/test_weakest_axis.py`
# 斷言兩者的鍵完全一致。
AXIS_RESEARCH_PROMPT: dict[str, str] = {
    "source_reliability": "補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證",
    "technical_causal_link": "補 counter-path：什麼會讓這條因果鏈斷掉（第二供應源、客戶自製、技術替代）",
    "commercial_maturity": "補客戶端商業承諾：訂單、產能協議或預付款等付錢方向的證據",
    "financial_resilience": "補 Engine C 財務觀測：客戶集中度、backlog、runway 等人工欄位",
    "valuation_payoff": "補估值錨點：市值、分析師覆蓋與隱含假設，回答股價已經定價了什麼",
}


def axis_sort_key(axis: str, level: str) -> tuple[int, int]:
    """最弱軸排序鍵：`(等級序, AXES 宣告序)`。**tie-break 的唯一定義。**

    未登記的等級視為最弱（寧可多提醒一次，也不要讓拼錯的值看起來佐證完整）；
    未登記的軸名排在所有已登記軸之後（它是資料問題，不該搶到「最該補」的位置）。
    """
    order = LEVELS.index(level) if level in LEVELS else -1
    declared = AXES.index(axis) if axis in AXES else len(AXES)
    return (order, declared)


def weakest_axis_of(axes: Mapping[str, Mapping[str, Any]]) -> str:
    """回傳證據最弱的那一軸。**要求五軸齊全**（缺軸是資料缺陷，應 KeyError 而非猜）。

    以 `effective_level` 次序為主鍵，同階時退到 `AXES` 的宣告次序
    （`source_reliability` 優先）。

    ⚠ 不能改用宣告的 `level`：`_validate_assessment` 在 `fatal_axis_blocker`
    （例如 evidence_missing）時把該軸判為失效卻**不動 level**，所以一個宣告
    corroborated 但引用不成立的軸，raw level 仍是 corroborated。用 raw level 排序
    會漏掉它，`test_probe_sizing.py::...[missing_ref]` 立刻紅。`effective_level`
    就是把那個隱含資訊顯性化的欄位。
    """

    return min(
        AXES,
        key=lambda axis: axis_sort_key(
            axis, str(axes[axis].get("effective_level") or axes[axis]["level"])
        ),
    )
