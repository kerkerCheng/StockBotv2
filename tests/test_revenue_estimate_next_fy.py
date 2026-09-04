"""Phase 4c：下一會計年度的營收共識。

⚠ **這個欄位之所以拖到 2026-09-04，是因為 ROADMAP 寫著一句假話。**
原文：「yfinance 只有 `revenueGrowth`（成長率）與 `epsCurrentYear`，沒有絕對營收估計」。
實測 `yf.Ticker().revenue_estimate` 直接給 `+1y` 的 avg／low／high／growth／
numberOfAnalysts，**73/73 檔全覆蓋**（含 `000660.KS`／`002472.SZ`／`2301.TW`）。
這是「引用自家文件的現況陳述前先跑查證命令」第三次抓到同型錯誤（L11-6）。

本檔守兩件事：
① **兩個成長率不得混用**——營收成長 vs EPS 隱含成長是不同的量；
② **取不到回 `None` 不回 0**——「沒有共識」與「共識是零成長」是兩件事（L12）。
"""
from __future__ import annotations

import pytest

from alpha.contracts import ConsensusSnapshot, ValuationSnapshot


# ---------------------------------------------------------------------------
# 1. 兩個成長率是不同的量——本檔最重要的一條
# ---------------------------------------------------------------------------

def test_revenue_growth_and_implied_eps_growth_are_separate_fields() -> None:
    """⚠ `revenue_estimate_next_fy_growth` 是**營收**成長；
    `ValuationSnapshot.market_implied_growth` 是由 `trailing_pe/forward_pe` 導出的
    **EPS** 隱含成長。**兩者不得相減當成 expectation gap**——差額裡混著利潤率變化。

    實測（2026-09-04 COHR）：市場隱含 +244.6% vs 共識營收成長 +38.2%。
    那個 206 個百分點的差**不是** gap，它同時包含「市場預期利潤率大幅擴張」。

    空跑檢查：把兩者合併成一個 `growth_gap` 欄位 → 這條會紅。
    """
    consensus = ConsensusSnapshot(
        trailing_pe=65.29, forward_pe=18.95,
        revenue_estimate_next_fy=14_674_707_350.0,
        revenue_estimate_next_fy_growth=0.382,
    )
    valuation = ValuationSnapshot(market_implied_growth=2.4458)

    assert consensus.revenue_estimate_next_fy_growth == 0.382
    assert valuation.market_implied_growth == pytest.approx(2.4458)
    # 契約層不得長出把兩者合併的欄位
    for field in ("growth_gap", "revenue_vs_eps_gap", "expectation_gap"):
        assert not hasattr(valuation, field), (
            f"ValuationSnapshot 長出了 {field}——營收成長與 EPS 隱含成長不同口徑，"
            "合併成一個數字會讓下游無從分辨（L12）")


def test_the_absolute_estimate_is_in_reporting_currency_not_usd() -> None:
    """⚠ 絕對值以**該標的的報表幣別**計，不是 USD。

    實測 SK Hynix（`000660.KS`）的 `+1y` 是 534,449,639,210,000（KRW）。
    與 `forward_eps` 同一個單位陷阱：只保證同一標的的時間序列比值有意義，
    **不得跨標的比絕對值**；`..._growth` 無單位，那一欄才可以跨標的比。
    """
    krw = ConsensusSnapshot(revenue_estimate_next_fy=534_449_639_210_000.0,
                            revenue_estimate_next_fy_growth=0.5311)
    usd = ConsensusSnapshot(revenue_estimate_next_fy=14_674_707_350.0,
                            revenue_estimate_next_fy_growth=0.382)
    # 絕對值差 36000 倍，但那只是幣別，不代表 SK Hynix 比 COHR 大 36000 倍
    assert krw.revenue_estimate_next_fy / usd.revenue_estimate_next_fy > 30_000
    # 成長率才是可比的：兩者同一個尺度
    assert 0 < usd.revenue_estimate_next_fy_growth < krw.revenue_estimate_next_fy_growth < 1


# ---------------------------------------------------------------------------
# 2. 取不到回 None 不回 0
# ---------------------------------------------------------------------------

class _FailingTicker:
    @property
    def revenue_estimate(self):
        raise RuntimeError("provider down")


class _EmptyTicker:
    revenue_estimate = None


class _NoNextYearTicker:
    class _Frame:
        index = ("0q", "+1q", "0y")
    revenue_estimate = _Frame()


@pytest.mark.parametrize("obj", [_FailingTicker(), _EmptyTicker(), _NoNextYearTicker()])
def test_missing_consensus_is_none_not_zero(obj) -> None:
    """「沒有共識」與「共識是零成長」是兩件事（L12）。

    空跑檢查：把 `empty` 的三個值改成 `0` → 這條會紅。
    """
    from engine_c.etl_yfinance import _next_fy_revenue_estimate

    got = _next_fy_revenue_estimate(obj, "TEST")
    assert got == {"avg": None, "growth": None, "analysts": None}


def test_default_snapshot_has_no_consensus() -> None:
    """沒有資料時預設就是 None——不得預設成 0 讓下游以為「共識是不成長」。"""
    empty = ConsensusSnapshot()
    assert empty.revenue_estimate_next_fy is None
    assert empty.revenue_estimate_next_fy_growth is None


# ---------------------------------------------------------------------------
# 3. schema 與 migration 對齊
# ---------------------------------------------------------------------------

def test_sqlite_and_postgres_write_the_same_three_columns() -> None:
    """SQLite 的 `ALTER TABLE` 補欄與 Postgres migration 必須列出同樣三欄。

    ⚠ 兩端漂掉不會報錯——SQLite 端照樣寫得進去，Postgres 端靜默少三欄。
    """
    import pathlib

    columns = ("revenue_estimate_next_fy", "revenue_estimate_next_fy_growth",
               "revenue_estimate_next_fy_analysts")
    db_py = pathlib.Path("engine_c/db.py").read_text(encoding="utf-8")
    migration = pathlib.Path(
        "engine_c/migrations/20260904_add_revenue_estimate_next_fy.sql"
    ).read_text(encoding="utf-8")
    for column in columns:
        assert column in db_py, f"engine_c/db.py 缺 {column}"
        assert column in migration, f"migration 缺 {column}"
    # 三欄都要出現在 INSERT 的兩種方言裡，否則寫不進去
    assert db_py.count("revenue_estimate_next_fy_growth") >= 4


def test_the_roadmap_claim_that_blocked_this_is_recorded_as_false() -> None:
    """⚠ 拔掉一個假前提時，必須把「它是假的」寫下來，否則下次會被原樣加回來。

    這與 beta 訊號、luna-reviewer 的處理方式一致：移除／推翻的理由要留下實測。
    """
    import pathlib

    migration = pathlib.Path(
        "engine_c/migrations/20260904_add_revenue_estimate_next_fy.sql"
    ).read_text(encoding="utf-8")
    assert "73/73" in migration
    assert "假的" in migration
