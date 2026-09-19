"""Reverse Bridge 的型別（2026-09-10；ROADMAP「Post-MVP Alpha Edge」§B 的落地）。

## 這一層在問什麼

正向：我們的假設 → 內部 EPS → fair value → 跟現價比。
**反向：現價要成立，某個 driver 必須是多少？**（其餘假設固定成我們自己的）

為什麼要反過來問——資深買方普遍不信「目標倍數法」，因為倍數的自由度會吃掉一切：
把目標本益比從 20x 改成 25x 是 +25%，而讓內部 EPS 比共識高 5% 需要一整條證據鏈。
**一個沒有證據的倍數念頭可以蓋過五條紮實的營運假設。** 反推法不需要你給一個新的倍數，
所以那個自由度根本不存在。

## 三條刻意的限制

1. **一次只解一個 driver，其餘固定成我們的假設。** 共識只給總量，反推的分項本來就是
   欠定的——ROADMAP §B 原文：「不得假造市場沒有提供的精確 driver」。所以這裡給的每一個
   數字都是**條件解**（conditional on 其他假設），不是唯一解，`method` 逐字說出這件事。
2. **不新增任何倍數自由度。** 目標倍數照抄 `ValuationAssumption`，這一層不碰它。
3. **不需要 peer 樣本。** 2026-09-10 實測：`sector_anchors` 的需求鏈分組拿來比估值不堪用
   （最大一組正值 P/E 9.9x–33.2x，離散 3.3 倍；4 組有 3 組 n≤2）。反推只需要這一檔自己的
   價格與假設，繞開了那個牆。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..errors import ContractViolation
from ..fundamental.contracts import FiscalPeriod

#: 一個 driver 的反解結果。每一種失敗各有自己的名字，**不合併成一個 unavailable**。
#: - `solved`：在合法範圍內解出來了。
#: - `already_equal`：我們的假設已經等於市場隱含（差 < 容忍）——常見於 `consensus_inverted`，
#:   而那正是誠實的答案：我們的預測就是市場的預測。
#: - `no_sign_change`：在 driver 的合法範圍兩端，EPS 都在目標的同一側——**即使把這個 driver
#:   拉到極限也撐不起（或壓不到）現價**。這是強結論，不是缺料。
#: - `bridge_failed`：擾動後橋算不出 EPS（缺其他假設、口徑衝突）。
#: - `missing_inputs`：沒有基期／目標倍數／現價／這個 driver 的假設。
SOLVE_STATUSES: tuple[str, ...] = (
    "solved", "already_equal", "no_sign_change", "bridge_failed", "missing_inputs",
)

#: **要問的倍率清單**（Phase 7 Step 7.1，2026-09-19）。
#:
#: ⚠ 這是**問句**不是**門檻**：AGENTS.md「刻意不寫死比值」禁的是 gate 的比值
#: （「payoff 必須 > X%」那一類），不是「我們要問幾倍」。目標區間是 2–10 倍（D0），
#: 所以四個問句剛好是那個區間的兩端與中間。**加一個倍率不改變任何判定，只多問一句。**
RETURN_MULTIPLE_LADDER: tuple[float, ...] = (2.0, 3.0, 5.0, 10.0)

#: 整份反解的狀態。
REVERSE_STATUSES: tuple[str, ...] = ("available", "partial", "missing")

#: 我們的值與市場隱含值視為相同的相對容忍。**與尺度無關**（同 `compare.py` 的教訓：
#: 絕對容忍在便士級 EPS 上會把兩個候選一起放進來）。
EQUAL_REL_TOL = 1e-4


@dataclass(frozen=True, slots=True)
class DriverSolution:
    """「這個 driver 要是多少，現價才成立」——其餘假設固定成我們的。"""

    driver: str
    scope: str
    assumption_id: str
    unit: str
    our_value: float
    implied_value: float | None
    status: str
    reason: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self) -> None:
        if self.status not in SOLVE_STATUSES:
            raise ContractViolation(
                f"DriverSolution.status 未登記：{self.status!r}；已知 {SOLVE_STATUSES}")
        if self.status == "solved" and self.implied_value is None:
            raise ContractViolation("status=solved 必須帶 implied_value")
        if self.status != "solved" and self.status != "already_equal" and self.implied_value is not None:
            raise ContractViolation(f"status={self.status} 不得帶 implied_value（缺席不是數字）")
        if self.status != "solved" and not self.reason:
            raise ContractViolation(f"status={self.status} 必須說出為什麼（INV-3：不得靜默）")

    @property
    def gap(self) -> float | None:
        """市場隱含 − 我們的。正值＝市場比我們樂觀。"""
        if self.implied_value is None:
            return None
        return self.implied_value - self.our_value


@dataclass(frozen=True, slots=True)
class ReverseBridgeResult:
    company_id: str
    ticker: str
    as_of: date | None
    target_period: FiscalPeriod | None
    status: str
    current_price: float | None
    target_multiple: float | None
    #: **倍率＝1 時的值，語意永遠是「市場隱含」**（現價 ÷ 目標倍數）。
    #: ⚠ 問「五倍要什麼為真」時**不得讀這一格**——那是 `required_eps`。
    #: 兩格分開是因為一個表示不該承載兩種語意（L12）：倍率 1 問的是「市場在想什麼」，
    #: 倍率 5 問的是「要漲五倍需要什麼」，**那是兩個不同的問題，只是共用同一條橋**。
    market_implied_eps: float | None
    our_eps: float | None
    consensus_eps: float | None
    #: **這次反解問的是幾倍**（2026-09-19，Phase 7 Step 7.1）。`1.0`＝原本的「市場隱含」問法。
    #: ⚠ 刻意**不寫死**任何比值（AGENTS.md「刻意不寫死比值」）：它是參數，一次可以問多個。
    target_return_multiple: float = 1.0
    #: **要讓股價達到 `現價 × 倍率`，在目標倍數下所需的 EPS。** 倍率 1 時等於 `market_implied_eps`。
    required_eps: float | None = None
    solutions: tuple[DriverSolution, ...] = ()
    reason: str | None = None
    warnings: tuple[str, ...] = ()
    method: str = (
        "required_eps ＝ 現價 × 倍率 ÷ 目標倍數；每個 driver 各解一次，**其餘假設固定成我們的**"
        "——所以每個值都是條件解，不是唯一解（共識只給總量，分項本來就欠定）。"
        "求根用二分法，區間就是該 driver 在 ASSUMPTION_DRIVERS 裡宣告的合法上下限。"
        "⚠ 倍率＝1 時 required_eps 就是市場隱含 EPS，這條路徑的行為與 2026-09-19 之前完全相同。"
    )

    def __post_init__(self) -> None:
        if self.status not in REVERSE_STATUSES:
            raise ContractViolation(
                f"ReverseBridgeResult.status 未登記：{self.status!r}；已知 {REVERSE_STATUSES}")
        if self.status != "available" and not self.reason:
            raise ContractViolation(f"status={self.status} 必須說出為什麼")

    @property
    def eps_gap(self) -> float | None:
        """市場隱含 EPS 比我們的高多少（相對）。正值＝市場比我們樂觀。

        ⚠ 這一格**永遠用 `market_implied_eps`**（倍率 1），不跟著 `target_return_multiple` 走：
        「市場比我們樂觀多少」與「要漲 N 倍還差多少」是兩個問題（L12）。後者看 `required_gap`。
        """
        if self.market_implied_eps is None or not self.our_eps:
            return None
        return self.market_implied_eps / self.our_eps - 1.0

    @property
    def required_gap(self) -> float | None:
        """要達到那個倍率，EPS 得比我們現在的假設高多少（相對）。"""
        if self.required_eps is None or not self.our_eps:
            return None
        return self.required_eps / self.our_eps - 1.0

    @property
    def unreachable_drivers(self) -> tuple[DriverSolution, ...]:
        """**即使把這個 driver 拉到合法極限也達不到**的那些（`no_sign_change`）。

        ⚠ 這是 Phase 7 真正想要的輸出：問「五倍要什麼為真」時，
        **回答「這一格即使拉到極限也做不到」比回答「需要成長 340%」有用得多**——
        前者是一個結論，後者只是一個數字。
        """
        return tuple(s for s in self.solutions if s.status == "no_sign_change")


__all__ = ["EQUAL_REL_TOL", "REVERSE_STATUSES", "SOLVE_STATUSES", "DriverSolution",
           "ReverseBridgeResult"]
