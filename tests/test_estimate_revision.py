"""Phase 4 Q4 原料：估計修正必須與股價變動**分開**。

原本 `ConsensusSnapshot.estimate_revision_30d` 取的是 `pe_forward` 的 30 日變化，
而倍數同時被「分析師改估計」與「股價漲跌」推動——一個表示兩種語意，下游無從
分辨（L12）。分開之後才問得出 Q4 的問題：「分析師上修了，而股價還沒反映」
正是 expectation gap 的形狀。

實測 2026-09-04（2026-07-08 起的每日快照）：COHR forward EPS **+68.3%** 而股價
**+0.6%**；同期 AAPL／GOOGL／TSM／MU 幾乎完全同步。**便宜不等於 gap，
估計與價格脫鉤才是**——這正是 exit criterion 的第二句。
"""
from __future__ import annotations

import pytest

from engine_c.estimates import forward_eps_from, revision_over


def _series(*pairs: tuple[str, float, float]) -> list[dict]:
    """`(as_of, price, pe_forward)` → provider 序列。"""
    return [
        {"as_of": d, "forward_eps": forward_eps_from(px, pe), "price": px}
        for d, px, pe in pairs
    ]


# ---------------------------------------------------------------------------
# forward_eps_from：導出，不是新欄位
# ---------------------------------------------------------------------------

def test_forward_eps_is_price_over_forward_pe() -> None:
    """實測 yfinance：`forwardPE` 恆等於 `price / forwardEps`（相對差 <1e-7）。

    這條釘住 Phase 4 的關鍵發現——原計畫要「擴充 Engine C 欄位補 forwardEps」，
    但那個數字**每天都已經存下來了**，只是沒有人導出來。新增欄位今天才開始有
    資料，導出立刻有兩個月歷史。
    """
    assert forward_eps_from(56.2, 25.24708) == pytest.approx(2.226, rel=1e-4)
    assert forward_eps_from(228.45, 14.778659) == pytest.approx(15.4581, rel=1e-4)


def test_negative_forward_pe_yields_a_negative_eps_not_none() -> None:
    """負的 forward PE 代表**虧損預估**，導出的負 EPS 是正確資訊，不得丟掉。

    SIVE.ST 與 IQE.L 都是這種情形。把它當成「算不出來」會讓兩檔實際持倉的
    標的在 Q4 原料上憑空消失。
    """
    assert forward_eps_from(25.46, -127.3) == pytest.approx(-0.2, rel=1e-3)


@pytest.mark.parametrize(
    "price,pe",
    [(None, 10.0), (10.0, None), (10.0, 0.0), (float("nan"), 10.0),
     (10.0, float("inf")), (True, 10.0), (10.0, True)],
)
def test_unusable_inputs_are_none_not_zero(price, pe) -> None:
    """算不出來要回 `None`，不得用 0 冒充——0 會被讀成「估計是零」。"""
    assert forward_eps_from(price, pe) is None


# ---------------------------------------------------------------------------
# revision_over：兩個數字，不是一個
# ---------------------------------------------------------------------------

def test_estimate_and_price_are_reported_separately() -> None:
    """核心行為：估計動了多少、股價動了多少，各自報。

    這組數字刻意仿 COHR 的實測形狀——估計大幅上修而股價沒動。用舊的
    `pe_forward` 變化只會得到一個混合數，看不出是哪一邊在動。
    """
    # 估計 ×2（EPS 5 → 10），股價不動 → 倍數腰斬，但那不是「變便宜」
    series = _series(("2026-07-08", 100.0, 20.0), ("2026-09-03", 100.0, 10.0))
    result = revision_over(series, sessions=30)

    assert result is not None
    assert result["eps_change"] == pytest.approx(1.0)
    assert result["price_change"] == pytest.approx(0.0)
    assert result["estimate_vs_price"] == pytest.approx(1.0)
    assert result["observations"] == 2
    assert result["from"] == "2026-07-08" and result["to"] == "2026-09-03"


def test_price_running_ahead_of_estimates_is_the_opposite_sign() -> None:
    """股價漲而估計沒動 → `estimate_vs_price` 為負。方向要讀得出來。"""
    series = _series(("2026-07-08", 100.0, 10.0), ("2026-09-03", 200.0, 20.0))
    result = revision_over(series, sessions=30)

    assert result is not None
    assert result["eps_change"] == pytest.approx(0.0)
    assert result["price_change"] == pytest.approx(1.0)
    assert result["estimate_vs_price"] < 0


def test_a_multiple_that_did_not_move_still_reports_both_legs() -> None:
    """⚠ 這條是舊 proxy 測不到的案例，也是它為什麼該被換掉。

    估計與股價**同倍數上升**時 `pe_forward` 完全不動——舊 proxy 回報「修正 0」，
    而事實是分析師把估計調高了一倍。一個表示兩種語意的代價就在這裡（L12）。
    """
    series = _series(("2026-07-08", 100.0, 20.0), ("2026-09-03", 200.0, 20.0))
    result = revision_over(series, sessions=30)

    assert result is not None
    assert result["eps_change"] == pytest.approx(1.0), "估計確實動了，不得回報 0"
    assert result["price_change"] == pytest.approx(1.0)
    assert result["estimate_vs_price"] == pytest.approx(0.0), "兩腿同幅＝沒有脫鉤"


def test_sign_crossing_is_unavailable_not_a_huge_number() -> None:
    """虧損轉盈利時比值沒有意義——回 `None`，不是一個看起來很大的數字。

    `-0.2 → +0.1` 若照算會得到 −150%，方向還是反的。這種數字進了 Q4 原料，
    session 會據此寫出一個完全錯誤的 variant perception。
    """
    series = _series(("2026-07-08", 100.0, -500.0), ("2026-09-03", 100.0, 1000.0))
    assert revision_over(series, sessions=30) is None


def test_too_short_a_series_is_unavailable() -> None:
    assert revision_over([], sessions=30) is None
    assert revision_over(_series(("2026-09-03", 100.0, 10.0)), sessions=30) is None


def test_the_window_takes_the_most_recent_observations() -> None:
    """`sessions=N` 取最近 N+1 個觀測，不是整條序列。"""
    series = _series(
        ("2026-01-01", 100.0, 100.0),   # EPS 1.0  ← 窗口外
        ("2026-08-01", 100.0, 20.0),    # EPS 5.0
        ("2026-09-01", 100.0, 10.0),    # EPS 10.0
    )
    result = revision_over(series, sessions=1)

    assert result is not None
    assert result["observations"] == 2
    assert result["from"] == "2026-08-01"
    assert result["eps_change"] == pytest.approx(1.0)      # 5 → 10
    # 整條序列會是 1.0 → 10.0＝+900%，取錯窗口會差一個數量級
    assert result["eps_change"] != pytest.approx(9.0)


# ---------------------------------------------------------------------------
# 單位陷阱：這是實際會咬人的那一條
# ---------------------------------------------------------------------------

def test_derived_eps_is_in_quote_units_so_only_ratios_are_safe() -> None:
    """⚠ 導出值的單位跟著**報價單位**走，不是結算幣別。

    實測 IQE.L（2026-09-04）：報價 `GBp`（便士）price=45、forwardPE=-229.6，
    導出 EPS = -0.196（便士）；而 yfinance 自己回報的 `forwardEps` 是 **-0.00196
    英鎊**——**差 100 倍**。這正是 AGENTS.md「報價單位 ≠ 結算幣別」記過的坑，
    也是「不得為了通過驗證把報價單位改寫成 ISO code——價格會差 100 倍」那條。

    所以本模組只保證**同一標的的時間序列比值**正確（單位在比值中消掉），
    這條測試就是那個保證：同一段行情用兩種單位表達，比值必須完全相同。
    """
    in_pence = _series(("2026-07-08", 45.0, -229.6), ("2026-09-03", 90.0, -229.6))
    in_pounds = _series(("2026-07-08", 0.45, -229.6), ("2026-09-03", 0.90, -229.6))

    pence = revision_over(in_pence, sessions=30)
    pounds = revision_over(in_pounds, sessions=30)

    assert pence is not None and pounds is not None
    assert pence["eps_change"] == pytest.approx(pounds["eps_change"])
    assert pence["price_change"] == pytest.approx(pounds["price_change"])
    assert pence["estimate_vs_price"] == pytest.approx(pounds["estimate_vs_price"])
    # 而絕對值**不**相同——所以它不得跨標的比大小。
    assert in_pence[0]["forward_eps"] != pytest.approx(in_pounds[0]["forward_eps"])
