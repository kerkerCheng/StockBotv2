"""Phase 6：排序前段 vs 後段的等權報酬。

## 它回答什麼、不回答什麼

**回答**：把 `rank_bottlenecks` 在歷史時點 T 產出的排序切成前段／後段，
各自等權持有到 T+h，前段的報酬有沒有比後段好。

**不回答**：這個排序有沒有統計上的預測力。樣本是**個位數期數 × 十來檔高度相關的
標的**，任何 t 統計量都會是噪音。輸出必須標成研究判斷的檢核，不是回測勝率
（`AGENTS.md` Alpha 呈現契約：排序是研究判斷，必須明標它不是回測或統計勝率）。

## 三個刻意的限制

1. **等權，不含部位尺寸。** 系統不給 alpha 尺寸（`AGENTS.md`）；這裡量的是
   「排序有沒有資訊」，不是「這樣配置賺多少」。比較基準是等權，不是 NAV。
2. **本地幣別報酬，不折匯率。** 報酬是比值，報價單位在分子分母消掉——所以
   `IQE.L` 的 `GBp` 不會像價格那樣差 100 倍（那個坑見 `identity/currency.py`）。
   但**匯率變動因此也沒被計入**，跨市場標的的比較只在本地報酬層成立。
3. **沒有價格的標的排除並列名。** 靜默丟棄會讓「排序沒用」與「資料缺一半」
   同形（L13）。

## ⚠ 前段與後段不是兩個獨立的賭注

本圖的標的高度集中在 AI 光互連。前段 N 檔不是 N 個獨立機會，後段也不是；
兩段之間的相關性也很高。所以「價差 > 0」的訊息量遠小於它看起來的樣子。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

__all__ = [
    "EpochResult", "equal_weight_return", "evaluate_epoch", "summarise_epochs",
]

#: 一期至少要有幾檔**有價格**的標的才切得動前後段。
#: 少於這個數，前段與後段各不到 2 檔，價差等於在比兩檔個股——那不是排序的檢定。
MIN_TICKERS_FOR_SPLIT = 4


@dataclass(frozen=True, slots=True)
class EpochResult:
    """一期的結果。**每個被排除的標的都要列得出來與說得出理由。**"""

    as_of: date
    horizon_end: date
    ranked: tuple[str, ...]
    top: tuple[str, ...] = ()
    bottom: tuple[str, ...] = ()
    top_return: float | None = None
    bottom_return: float | None = None
    #: 逐檔報酬。**不是裝飾**：前後段各三、四檔時，一檔的極端值就能決定整期的
    #: 結論，而只看平均完全看不出來（實測 2026-03-01 那期 `SOI.PA` +334%
    #: 一檔撐起 +97.8% 的價差）。要能被質疑，就得看得到成分。
    contributions: tuple[tuple[str, float], ...] = ()
    missing_price: tuple[str, ...] = ()
    skipped_reason: str | None = None

    @property
    def spread(self) -> float | None:
        if self.top_return is None or self.bottom_return is None:
            return None
        return self.top_return - self.bottom_return

    @property
    def dominant_name(self) -> tuple[str, float] | None:
        """偏離該期均值最遠的一檔，以及它偏離多少。

        ⚠ 這不是在挑離群值剔除——**是把它現形**。剔除會讓結果更好看，
        現形才讓讀的人知道這一期的結論其實由誰決定。
        """
        if not self.contributions:
            return None
        mean = sum(r for _, r in self.contributions) / len(self.contributions)
        ticker, ret = max(self.contributions, key=lambda kv: abs(kv[1] - mean))
        return ticker, ret - mean

    @property
    def usable(self) -> bool:
        return self.skipped_reason is None and self.spread is not None


def _price_on_or_before(series: Sequence[Mapping[str, object]], when: date) -> float | None:
    """`when` 當天或之前**最近**一個收盤。

    ⚠ 只往回找，永遠不往前補。往前補一天就是拿未來的價格當進場價——
    在一份專門檢查 lookahead 的模組裡，這是最不能犯的錯。
    """
    best: float | None = None
    best_day: str | None = None
    target = when.isoformat()
    for row in series:
        day = str(row.get("session_date") or "")
        if not day or day > target:
            continue
        if best_day is None or day > best_day:
            best_day, best = day, float(row.get("close") or 0.0)
    return best if best else None


def equal_weight_return(
    tickers: Sequence[str],
    prices: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    start: date,
    end: date,
) -> tuple[float | None, tuple[str, ...]]:
    """等權報酬，以及**沒有價格因而被排除的標的**。

    回傳 `(報酬, 缺價的 ticker)`。一檔都算不出來時報酬是 `None`，不是 0.0——
    「沒資料」與「持平」是兩件事（L12）。
    """
    returns: list[float] = []
    missing: list[str] = []
    for ticker in tickers:
        series = prices.get(ticker) or ()
        opening = _price_on_or_before(series, start)
        closing = _price_on_or_before(series, end)
        if opening is None or closing is None or opening <= 0:
            missing.append(ticker)
            continue
        returns.append(closing / opening - 1.0)
    if not returns:
        return None, tuple(missing)
    return sum(returns) / len(returns), tuple(missing)


def evaluate_epoch(
    *,
    as_of: date,
    horizon_end: date,
    ranked: Sequence[str],
    prices: Mapping[str, Sequence[Mapping[str, object]]],
) -> EpochResult:
    """把一期的排序切成前後兩半並算等權報酬。

    ⚠ **先剔除沒有價格的，再切前後段。** 反過來做（先切再剔）會讓兩段的檔數
    不對稱且不可控——實測上缺價的多半是非美股，它們在排序裡不是均勻分布的。
    """
    ranked = tuple(dict.fromkeys(str(t) for t in ranked if str(t).strip()))
    priced = tuple(
        t for t in ranked
        if _price_on_or_before(prices.get(t) or (), as_of) is not None
        and _price_on_or_before(prices.get(t) or (), horizon_end) is not None
    )
    missing = tuple(t for t in ranked if t not in priced)
    if len(priced) < MIN_TICKERS_FOR_SPLIT:
        return EpochResult(
            as_of=as_of, horizon_end=horizon_end, ranked=ranked,
            missing_price=missing,
            skipped_reason=(
                f"只有 {len(priced)} 檔有價格（門檻 {MIN_TICKERS_FOR_SPLIT}）——"
                "切成前後段後每段不到 2 檔，那是在比個股不是在檢定排序"),
        )
    half = len(priced) // 2
    top, bottom = priced[:half], priced[-half:]
    top_return, _ = equal_weight_return(top, prices, start=as_of, end=horizon_end)
    bottom_return, _ = equal_weight_return(bottom, prices, start=as_of, end=horizon_end)
    contributions = tuple(
        (ticker, _single_return(prices.get(ticker) or (), as_of, horizon_end))
        for ticker in (*top, *bottom)
    )
    return EpochResult(
        as_of=as_of, horizon_end=horizon_end, ranked=ranked,
        top=top, bottom=bottom,
        top_return=top_return, bottom_return=bottom_return,
        contributions=tuple((t, r) for t, r in contributions if r is not None),
        missing_price=missing,
    )


def _single_return(
    series: Sequence[Mapping[str, object]], start: date, end: date
) -> float | None:
    opening = _price_on_or_before(series, start)
    closing = _price_on_or_before(series, end)
    if opening is None or closing is None or opening <= 0:
        return None
    return closing / opening - 1.0


def summarise_epochs(results: Sequence[EpochResult]) -> dict[str, object]:
    """跨期彙總。**不算 t 統計量、不算勝率**——期數是個位數，那些會誤導。"""
    usable = [r for r in results if r.usable]
    spreads = [r.spread for r in usable if r.spread is not None]
    return {
        "epochs_requested": len(results),
        "epochs_usable": len(usable),
        "spreads": [round(s, 4) for s in spreads],
        "mean_spread": round(sum(spreads) / len(spreads), 4) if spreads else None,
        "positive_epochs": sum(1 for s in spreads if s > 0),
        # 每期由誰決定的。⚠ 沒有這一欄，「平均價差 +36.9%」會被讀成一個穩定的
        # 現象，而實測它幾乎全來自一期裡的一檔（`SOI.PA` +334%）。
        "dominant_names": [
            {"as_of": r.as_of.isoformat(), "ticker": name,
             "excess_vs_epoch_mean": round(excess, 4)}
            for r in usable
            for name, excess in [r.dominant_name or ("—", 0.0)]
        ],
        "skipped": [
            {"as_of": r.as_of.isoformat(), "reason": r.skipped_reason}
            for r in results if r.skipped_reason
        ],
        "_interpretation": (
            "這是研究判斷的檢核，**不是回測勝率**：期數個位數、標的十來檔且高度集中在"
            "AI 光互連，前段與後段都不是獨立賭注。價差為正不構成統計證據；"
            "價差為負也不構成排序無效的證明。它的用途是讓排序至少被**看過一次**"
            "後續報酬，而不是永遠不出手所以永遠沒有 outcome。"
        ),
    }
