"""報表幣別 → 報價幣別的**可稽核**換算路徑（2026-09-13）。

## 為什麼需要這一層，以及它刻意不做什麼

`alpha/valuation/model.py::units_comparable` 在兩邊幣別不同時回 `incompatible_unit`，
報酬層據此 fail closed，**本層不換算**。那個設計是對的（L12：不得為了有數字而把兩個單位混成
一個；IQE.L 的 GBp／GBP 差 100 倍就是代價）。這個模組**不放寬它**——它補上它缺的那條路：
一條**帶日期、指得出來源、可被重算**的換算。

## 兩種完全不同的「幣別不同」，分開處理

| 情況 | 例 | 怎麼換 | 需要觀測嗎 |
|---|---|---|---|
| **同幣別、不同尺度**（minor unit） | IQE.L：fair value `GBP`、報價 `GBp` | `identity/currency.py` 的 registry **已經握著精確的 factor** | **不需要**——它是定義，不是市場價 |
| **真的跨幣別** | 6680.HK：報表 `CNY`、報價 `HKD` | 需要一筆**帶日期**的 FX 觀測 | **需要** |

⚠ 第一種先前被歸進「不得靠猜」，但**我們並沒有在猜**：registry 甚至把倍數印出來給人看。
知道答案卻不用，不是保守，是漏做（L15-1：這個 gate 攔下的不是它想攔的東西）。

## 三個契約決定（2026-09-13 交付時的選擇，寫下來讓它可被翻案）

1. **匯率從哪來** → **Engine C 的 `mechanical` 人工觀測**（`fx_rate` 欄位）。
   理由：它帶 `as_of`、帶 `source_ref`、append-only、任何人重查都得到同一個數（L10 的判準）。
   **不用 provider 快照**（今天沒有這個欄位，而加一個每天變的欄位會讓「當時用的是哪個匯率」
   又變成靠排序猜）；**不用 registry 常數**（常數沒有日期，那等於用今天的匯率換過去的價）。
2. **用哪一天的** → **`price.bar_date`**。那是唯一「兩邊都存在」的日期。
   ⚠ 不用 `horizon_end`：那等於要預測匯率，是另一種判斷（而且沒有人授權過）。
3. **`fair_value.currency` 怎麼處理** → **不改寫，另外給一組換算後的欄位**。
   丟掉「這個數字原本是人民幣」會讓下一個讀者無從分辨；多一組欄位的成本是消費端要跟上，
   而那個成本是一次性的。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from identity.currency import resolve_quote_unit

from .contracts import EvidenceRef
from .errors import ContractViolation

#: FX 觀測的 `as_of` 與現價 `bar_date` 最多容忍幾天。
#: **0 不可行**（匯率不是每天都有觀測：週末、假日、以及我們不會每天去抄），
#: 但容忍帶必須小到「不會跨過一次有意義的匯率變動」。3 天 ＝ 一個週末。
#: ⚠ 容忍是**天數**不是幅度：用幅度容忍等於自己決定「這個變動不重要」，那是判斷不是規則。
FX_AS_OF_TOLERANCE_DAYS = 3


@dataclass(frozen=True, slots=True)
class FxObservation:
    """一筆帶日期的匯率觀測：`1 base = rate quote`。

    ⚠ **方向寫在型別裡**，不靠命名慣例：`base` 是報表幣別、`quote` 是報價幣別，
    `rate` 是「一單位 base 換得幾單位 quote」。反了會差一個倒數，而那種錯不會報錯。
    """

    base: str
    quote: str
    rate: float
    as_of: date
    evidence: tuple[EvidenceRef, ...] = ()
    source: str | None = None

    def __post_init__(self) -> None:
        for name in ("base", "quote"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractViolation(f"FxObservation.{name} 必填")
        if not isinstance(self.rate, (int, float)) or self.rate <= 0:
            raise ContractViolation("FxObservation.rate 必須為正（它是「一單位 base 換幾單位 quote」）")
        if self.base.upper() == self.quote.upper():
            raise ContractViolation(
                "FxObservation 的 base 與 quote 相同——同幣別不需要匯率觀測，"
                "尺度差異由 identity/currency.py 的 registry 精確處理")


@dataclass(frozen=True, slots=True)
class Conversion:
    """一次換算的結果與它的全部依據。`factor` ＝ 乘在 fair value 上的那個數。"""

    value: float
    factor: float
    from_unit: str
    to_unit: str
    kind: str                        # "same_currency_scale" ｜ "fx_observation"
    formula: str
    as_of: date | None = None
    evidence_refs: tuple[str, ...] = ()


def convert_to_quote_unit(
    amount: float,
    *,
    from_currency: str | None,
    to_unit: str | None,
    bar_date: date | None,
    observations: Sequence[FxObservation] = (),
) -> tuple[Conversion | None, str | None]:
    """把報表幣別的金額換成報價單位。換不了就回 `(None, 理由)`——**絕不猜**。

    回傳的 `Conversion.factor` 是**乘數**，所以呼叫端只要 `amount * factor`，
    而 `formula` 字串把整條算術寫出來給人看。
    """
    if not from_currency or not to_unit:
        return None, "fair value 幣別或報價單位未知——不得假設同尺度"
    left = resolve_quote_unit(from_currency)
    right = resolve_quote_unit(to_unit)
    if left is None or right is None:
        unknown = from_currency if left is None else to_unit
        return None, (f"{unknown!r} 不在 quote unit registry（config/currency_units.json）"
                      "也不是 ISO-4217 形式——無法確定尺度，不猜")
    # ---- ①同幣別、不同尺度：registry 已經握著精確的 factor（不需要任何觀測）----
    if left.currency == right.currency:
        if left.factor == right.factor:
            return None, "兩邊本來就同單位，不需要換算"
        factor = left.factor / right.factor
        return Conversion(
            value=amount * factor, factor=factor, from_unit=from_currency, to_unit=to_unit,
            kind="same_currency_scale",
            formula=(f"{from_currency} → {to_unit}：同為 {left.currency}，"
                     f"尺度比 {left.factor:g} ÷ {right.factor:g} ＝ {factor:g}"
                     "（identity/currency.py 的 registry，定義值不是市場價）"),
        ), None
    # ---- ②真的跨幣別：需要一筆帶日期的 FX 觀測 ----
    if bar_date is None:
        return None, ("跨幣別換算需要一個日期，而現價快照沒有 bar_date"
                      "——不得用 ETL 日冒充行情交易日（F-27）")
    want = (left.currency.upper(), right.currency.upper())
    usable = [o for o in observations
              if (o.base.upper(), o.quote.upper()) == want
              and abs((o.as_of - bar_date).days) <= FX_AS_OF_TOLERANCE_DAYS]
    if not usable:
        have = sorted({f"{o.base}/{o.quote}@{o.as_of}" for o in observations})
        return None, (
            f"缺 {left.currency} → {right.currency} 的匯率觀測"
            f"（需要 as_of 在 {bar_date} 的 ±{FX_AS_OF_TOLERANCE_DAYS} 天內）。"
            + (f"ledger 現有：{'、'.join(have)}。" if have else "ledger 完全沒有這個標的的匯率觀測。")
            + "**這不是缺研究，是缺一筆 mechanical 觀測**"
            "（field=`fx_rate`，value 帶 base／quote／rate，source_ref 指得出公告匯率的來源）")
    chosen = min(usable, key=lambda o: (abs((o.as_of - bar_date).days), o.as_of))
    # 報價單位可能是 minor unit（GBp／ILA／ZAc）：先換幣別，再換尺度。
    factor = chosen.rate * (left.factor / right.factor)
    return Conversion(
        value=amount * factor, factor=factor, from_unit=from_currency, to_unit=to_unit,
        kind="fx_observation", as_of=chosen.as_of,
        evidence_refs=tuple(r.ref for r in chosen.evidence),
        formula=(f"{from_currency} → {to_unit}：1 {chosen.base} = {chosen.rate:g} {chosen.quote}"
                 f"（as_of {chosen.as_of}"
                 + (f"，{chosen.source}" if chosen.source else "")
                 + ("；現價 bar_date " + bar_date.isoformat()
                    + f"，差 {abs((chosen.as_of - bar_date).days)} 天）")
                 + (f" × 尺度 {left.factor:g}÷{right.factor:g}" if left.factor != right.factor else "")),
    ), None


def parse_fx_observation(payload: Mapping[str, object], *, as_of: date,
                         evidence: tuple[EvidenceRef, ...] = ()) -> FxObservation:
    """Engine C `fx_rate` 觀測的 payload → `FxObservation`。"""
    try:
        return FxObservation(
            base=str(payload["base"]), quote=str(payload["quote"]),
            rate=float(payload["rate"]),                     # type: ignore[arg-type]
            as_of=as_of, evidence=evidence,
            source=(str(payload["source"]) if payload.get("source") else None),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"fx_rate 觀測欄位不合法：{exc}") from None


__all__ = ["Conversion", "FX_AS_OF_TOLERANCE_DAYS", "FxObservation", "convert_to_quote_unit",
           "parse_fx_observation"]
