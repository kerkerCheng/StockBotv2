"""覆蓋崩塌不是共識變動（2026-09-19，七缺陷之 2）。

事發：LITE 的 +1y（FY2028）由 33.3012 → 39.70（**+19.2%**），於是 thesis 被標成
`review_required`。但同一筆共識的 `analyst_count` **由 22 崩到 1**、`low`＝`high`＝39.70
（區間寬度 0）；而 thesis 真正校準的 FY2027 只動了 **+0.13%**。
**base 完全沒有被推翻，訊號卻說它需要重做。**

判準本身系統裡早就有——POET 的 Abstention 逐字寫著「僅 1 位分析師，high＝low，區間寬度為零
——那不是共識，是一個人的看法」；packet 的 `valuation_market_implied.method` 也已對 rollover
fail closed。**同一個問題，估值層 fail closed、refresh 層照報**（L12／L16）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alpha.contracts import EvidenceRef
from alpha.fundamental.contracts import ConsensusEstimate, FiscalPeriod
from briefing.alpha_view import changes as ch

SINCE = datetime(2026, 9, 1, tzinfo=timezone.utc)
_REF = (EvidenceRef(ref="engine_c://consensus_estimate/LITE/eps/2028-06-30", kind="engine_c_observation"),)


def _estimate(value: float, *, count: int | None, low: float | None, high: float | None,
              label: str = "+1y") -> ConsensusEstimate:
    return ConsensusEstimate(
        metric="eps", period=FiscalPeriod(end=date(2028, 6, 30)), value=value,
        source="yfinance.earnings_estimate", evidence=_REF, low=low, high=high,
        analyst_count=count, captured_at=date(2026, 9, 18),
        fetched_at=datetime(2026, 9, 18, tzinfo=timezone.utc), relative_label=label)


def _snapshots(pe_before: float, pe_after: float) -> list[dict]:
    return [
        {"snapshot_date": "2026-09-08", "bar_date": "2026-09-08", "price": 1000.0,
         "pe_forward": pe_before, "fetched_at": "2026-09-08T00:00:00+00:00"},
        {"snapshot_date": "2026-09-18", "bar_date": "2026-09-18", "price": 1000.0,
         "pe_forward": pe_after, "fetched_at": "2026-09-18T00:00:00+00:00"},
    ]


def test_one_analyst_is_not_a_consensus() -> None:
    assert ch.single_analyst_view(1, 39.7, 39.7) is not None
    assert ch.single_analyst_view(22, 30.0, 45.0) is None
    assert ch.single_analyst_view(21, 39.7, 39.7) is not None          # 區間寬度 0 也算
    assert ch.single_analyst_view(None, None, None) is None            # 不知道就不判（不 fail open 成「崩塌」）


def test_collapsed_coverage_does_not_fire_a_consensus_event() -> None:
    """LITE 的實例：+1y 覆蓋 22 → 1，代理量跳 +19.2%。**不得發事件**，但要留 note（INV-3）。"""
    events, notes = ch.market_and_consensus_changes(
        _snapshots(30.0, 25.0), ticker="LITE", company_id="co:lumentum", since=SINCE,
        forward_coverage=_estimate(39.7, count=1, low=39.7, high=39.7))
    assert not [e for e in events if e.change_type == ch.CONSENSUS]
    assert any("未發事件" in n and "一個人的看法" in n for n in notes)
    assert [e for e in events if e.change_type == ch.MARKET_PRICE] == []   # 價格沒變


def test_healthy_coverage_still_fires() -> None:
    """AXTI 型對照組：覆蓋正常時照發——**這個 gate 必須會滅**（L14-4）。"""
    events, _notes = ch.market_and_consensus_changes(
        _snapshots(30.0, 25.0), ticker="AXTI", company_id="co:axt", since=SINCE,
        forward_coverage=_estimate(2.25, count=5, low=1.9, high=2.6))
    assert [e for e in events if e.change_type == ch.CONSENSUS]


def test_no_coverage_information_does_not_suppress() -> None:
    """拿不到覆蓋資訊時**照發**——fail open 的方向刻意：少報一個真變動比靜默吞掉更糟。"""
    events, _ = ch.market_and_consensus_changes(
        _snapshots(30.0, 25.0), ticker="AXTI", company_id="co:axt", since=SINCE)
    assert [e for e in events if e.change_type == ch.CONSENSUS]


def test_fiscal_consensus_event_says_which_year_and_how_many_analysts() -> None:
    """事件必須說得出「這是哪一年、幾個人」——否則 +1y 的變動看起來就像 base 被推翻了。"""
    old = [_estimate(33.3012, count=22, low=30.0, high=36.0)]
    new = [_estimate(35.0, count=21, low=31.0, high=38.0)]
    events, _ = ch.fiscal_consensus_changes(old, new, ticker="LITE", company_id="co:lumentum", since=SINCE)
    assert len(events) == 1
    assert "+1y" in events[0].detail and "覆蓋 22 → 21 人" in events[0].detail


def test_fiscal_consensus_suppresses_collapsed_coverage_too() -> None:
    old = [_estimate(33.3012, count=22, low=30.0, high=36.0)]
    new = [_estimate(39.7, count=1, low=39.7, high=39.7)]
    events, notes = ch.fiscal_consensus_changes(old, new, ticker="LITE", company_id="co:lumentum", since=SINCE)
    assert events == []
    assert any("22 → 1 人" in n for n in notes)
