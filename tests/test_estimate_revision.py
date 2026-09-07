"""Phase 4 Q4 原料：估計修正必須與股價變動**分開**。

原本 `ConsensusSnapshot.estimate_revision_30d` 取的是 `pe_forward` 的 30 日變化，
而倍數同時被「分析師改估計」與「股價漲跌」推動——一個表示兩種語意，下游無從
分辨（L12）。分開之後才問得出 Q4 的問題：「分析師上修了，而股價還沒反映」
正是 expectation gap 的形狀。

⚠ **本檔原本引用的實測結論已於 2026-09-07 撤回。** 原文是「COHR forward EPS +68.3%
而股價 +0.6%——expectation gap 的原型」。實測後那個 +68.3% **不是分析師修正**：
COHR 在 2026-08-12 公布 FY2026 財報，yfinance 的 forward year 隔天由 FY2027 換成
FY2028，導出 EPS 一天跳 **+62.3%**（8.21 → 13.59）。整段窗口跨過了那個換尺點。

因此第二層契約在這裡：**forward 是相對標籤，不是會計年度身分。** 只有窗口兩端
`forward_period_end` 相同才叫修正；身分不明或不同一律 `comparable=False`，
`eps_change` 是 `None` 不是 0（L11-5：「我算不出來」與「它沒動」是兩個 claim）。
"""
from __future__ import annotations

import pytest

from engine_c.estimates import (
    FISCAL_IDENTITY_REL_TOL, attach_forward_period, forward_eps_from, resolve_forward_period,
    revision_over,
)


#: 測試序列的預設 forward 會計年度身分。**同一年**才是「修正」的前提；
#: 想測 rollover 就用 `_series(..., periods=(...))` 明示每一筆的身分。
SAME_YEAR = "2027-06-30"


def _series(*pairs: tuple[str, float, float], periods: tuple[str | None, ...] | None = None) -> list[dict]:
    """`(as_of, price, pe_forward)` → provider 序列（預設全部同一個 forward 會計年度）。"""
    ends = periods if periods is not None else (SAME_YEAR,) * len(pairs)
    assert len(ends) == len(pairs)
    return [
        {"as_of": d, "forward_eps": forward_eps_from(px, pe), "price": px, "forward_period_end": end}
        for (d, px, pe), end in zip(pairs, ends)
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

    assert result is not None and result["comparable"] is True
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


# ---------------------------------------------------------------------------
# Q3 原料：分部營收占比（Phase 4b 的機制，資料本身仍需逐檔 pq2）
# ---------------------------------------------------------------------------

def _provider_with(rows: list[tuple[str, str, str]]):
    """建一個只有兩張必要表的 in-memory Engine C，回傳 provider。"""
    import sqlite3

    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE financial_snapshots (ticker TEXT, snapshot_date TEXT, "
        "bar_date TEXT, price REAL, pe_forward REAL, pe_trailing REAL, "
        "gross_margin REAL, operating_margin REAL, revenue_ttm REAL, "
        "free_cash_flow_ttm REAL, cash_and_equivalents REAL, total_debt REAL, "
        "shares_outstanding REAL, ev_revenue REAL, analyst_target_mean REAL, "
        "analyst_target_count INTEGER, price_kind TEXT, fetched_at TEXT)"
    )
    conn.execute(
        "INSERT INTO financial_snapshots (ticker, snapshot_date, bar_date, price, "
        "pe_forward, revenue_ttm) VALUES ('TEST','2026-09-03','2026-09-03',100.0,10.0,1000.0)"
    )
    conn.execute(
        "CREATE TABLE manual_fields (ticker TEXT, field_name TEXT, value TEXT, "
        "updated_at TEXT, source_note TEXT)"
    )
    for ticker, field, value in rows:
        conn.execute(
            "INSERT INTO manual_fields (ticker, field_name, value) VALUES (?,?,?)",
            (ticker, field, value),
        )
    return EngineCFundamentalsProvider(conn=conn)


def test_segment_revenue_share_reaches_q3_when_it_has_been_recorded() -> None:
    """L14 的「哪個數字會變」：登記欄位 ＋ 接線之後，人工觀測真的到得了 Q3。

    這是 Phase 4b 唯一能在沒有 authority 核准下驗收的東西——**機制通了**。
    真實資料仍要逐檔從 10-K 分部附註讀入，而寫 Engine C manual ledger 是四個
    authority gate 之一，每一檔都要 pq2。
    """
    provider = _provider_with([
        ("TEST", "segment_revenue_share",
         '{"Networking": 0.61, "Materials": 0.23, "fiscal_period": "FY2025"}'),
    ])
    snapshot, _ = provider.fundamentals("TEST")

    assert snapshot.segment_revenue_share == {"Networking": 0.61, "Materials": 0.23}
    # `fiscal_period` 是說明欄位不是分部占比，不得混進來當成一個 61% 的分部。
    assert "fiscal_period" not in snapshot.segment_revenue_share


@pytest.mark.parametrize(
    "value",
    ["", "not json", "[1, 2, 3]", '"just a string"', '{"fiscal_period": "FY2025"}', "{}"],
)
def test_unusable_segment_payloads_are_none_not_empty_dict(value: str) -> None:
    """⚠ 讀不到／格式壞掉一律 `None`，**不得回 `{}`**。

    空 dict 會讓 Q3 看到「有分部資料，而每一塊都是 0」——那比誠實說不知道危險得多，
    因為它會通過「有沒有資料」的檢查，然後餵出一個結論說這塊業務不重要。
    """
    provider = _provider_with([("TEST", "segment_revenue_share", value)])
    snapshot, _ = provider.fundamentals("TEST")

    assert snapshot.segment_revenue_share is None


def test_absent_observation_stays_none_and_does_not_fall_back_to_margins() -> None:
    """沒有這筆觀測時 Q3 誠實回 `None`——不得用整體毛利率或 revenue_ttm 近似。

    `session_assessor` 的 `earnings_exposure.do_not` 明文寫了這條；這裡讓它可執行。
    """
    provider = _provider_with([])
    snapshot, _ = provider.fundamentals("TEST")

    assert snapshot.segment_revenue_share is None
    assert snapshot.revenue_ttm == 1000.0, "其餘欄位照常，缺的只有分部資料"


# ---------------------------------------------------------------------------
# forward year rollover：第二個一表兩義（2026-09-07 實測後補）
#
# yfinance 的 `forwardPE` 指「下一個會計年度」——那是**相對於抓取日的標籤**，公司一
# 報完年報就換一年，而序列本身完全看不出來。COHR 2026-08-13 一天跳 +62.3%。
# 這一組守的是：換尺不得被讀成修正，而且**不用幅度門檻去猜**（那本身是未經量測的
# gate，L14）——身分由 consensus_estimates 的值反查，查不到就 fail closed。
# ---------------------------------------------------------------------------

def test_a_window_that_crosses_the_forward_year_is_not_comparable() -> None:
    """跨 rollover 的窗口：`comparable=False`，`eps_change` 是 None 不是 +62%。"""
    series = _series(
        ("2026-08-12", 327.0, 39.88),        # forward EPS ≈ 8.2（FY2027）
        ("2026-08-13", 327.23, 24.08),       # forward EPS ≈ 13.6（FY2028）← 換尺
        periods=("2027-06-30", "2028-06-30"),
    )
    result = revision_over(series, sessions=30)

    assert result is not None
    assert result["comparable"] is False
    assert result["eps_change"] is None, "換一把尺不是修正——不得回報一個 +62% 的『上修』"
    assert result["estimate_vs_price"] is None
    assert "2027-06-30" in str(result["not_comparable_reason"])
    assert "2028-06-30" in str(result["not_comparable_reason"])
    # 股價沒有會計年度身分問題，那一腿仍然給
    assert result["price_change"] == pytest.approx(327.23 / 327.0 - 1.0)


def test_unknown_fiscal_identity_fails_closed_rather_than_assuming_no_rollover() -> None:
    """身分不明＝不知道有沒有換尺。**不得假設沒換**——那是拿沉默當同意。

    這正是 COHR 的實況：`consensus_estimates` 只從 2026-09-04 起有列，窗口起點
    2026-08-04 沒有可反查的身分，所以整個 +68.3% 是不可比的。
    """
    series = _series(
        ("2026-08-04", 288.0, 35.1),
        ("2026-09-04", 281.86, 20.2),
        periods=(None, "2028-06-30"),
    )
    result = revision_over(series, sessions=30)

    assert result is not None and result["comparable"] is False
    assert result["eps_change"] is None
    assert "2026-08-04" in str(result["not_comparable_reason"])
    assert "身分不明" in str(result["not_comparable_reason"])


def test_same_forward_year_is_still_a_real_revision() -> None:
    """收緊不得把真的修正也擋掉——同一個會計年度的兩點照常回報。"""
    series = _series(("2026-09-01", 100.0, 20.0), ("2026-09-04", 100.0, 10.0))
    result = revision_over(series, sessions=30)

    assert result is not None and result["comparable"] is True
    assert result["eps_change"] == pytest.approx(1.0)
    assert result["forward_period_from"] == result["forward_period_to"] == SAME_YEAR


def test_identity_is_resolved_by_matching_the_value_not_by_guessing() -> None:
    """身分反查是**值比對**：導出 EPS 必須等於某一年的共識估計才算命中。

    對不上任何一年 → None（不知道）。⚠ 刻意不做「最接近的那一年」——最接近永遠
    有一個答案，於是「不知道」這個狀態就消失了（L12：一個表示兩種語意）。
    """
    candidates = [("2027-06-30", 9.41634), ("2028-06-30", 13.95531)]
    assert resolve_forward_period(13.9553, candidates) == "2028-06-30"
    assert resolve_forward_period(9.4163, candidates) == "2027-06-30"
    assert resolve_forward_period(11.5, candidates) is None, "落在兩年中間＝不知道，不是就近取一年"
    assert resolve_forward_period(None, candidates) is None
    assert resolve_forward_period(13.9553, []) is None, "沒有候選＝身分不明"


def test_the_tolerance_absorbs_rounding_but_cannot_swap_two_adjacent_years() -> None:
    """容差只吸收四捨五入。COHR 相鄰兩年差 48%，遠大於 1e-3——不可能互相冒充。"""
    assert FISCAL_IDENTITY_REL_TOL <= 1e-2
    candidates = [("2027-06-30", 9.41634), ("2028-06-30", 13.95531)]
    nudged = 9.41634 * (1 + FISCAL_IDENTITY_REL_TOL * 0.5)
    assert resolve_forward_period(nudged, candidates) == "2027-06-30"
    assert resolve_forward_period(9.41634 * 1.05, candidates) is None


def test_attach_forward_period_leaves_unknown_days_as_none() -> None:
    """身分表沒有那天的列 → `None`，不是沿用前一天（沿用會讓 rollover 隱形）。"""
    series = [{"as_of": "2026-08-04", "forward_eps": 8.2, "price": 288.0},
              {"as_of": "2026-09-04", "forward_eps": 13.9553, "price": 281.86}]
    identity = {"2026-09-04": [("2027-06-30", 9.41634), ("2028-06-30", 13.95531)]}
    out = attach_forward_period(series, identity)
    assert out[0]["forward_period_end"] is None
    assert out[1]["forward_period_end"] == "2028-06-30"
