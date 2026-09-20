"""虧損公司的多年橋走 EV／Sales，不是本益比法（2026-09-20，Phase 7）。

## 事發

[633] 把 AXTI 的 `multiple_horizon` 寫成 FY2028 之後，多年橋說「2x 也做不到」——
而同一檔的 FY+1 反向橋說「2x available」（Step 7.1 實測）。**兩句話方向相反。**

原因不是結構，是儀器：AXT FY2025 非 GAAP diluted_eps −0.41，而多年錨點取的是
「沿用基期」（`carried_forward`），所以 FY2028 錨點 EPS ＝ −0.0789。**負錨點**之下，
四級階梯每一級都會是「拉到極限也做不到」——那句話說的是「從負數漲到正數要多少」，
不是「這個結構允不允許 N 倍」。兩種語意在輸出上同形（L12）。

## 修法為什麼不是新方法

**系統早就有這條路**：`alpha/valuation/contracts.py` 的 `method_applicability()`
逐字寫著本益比法對負 EPS 不適用、「虧損公司改用 `ev_to_sales`（寫一筆
`target_ev_to_sales` 估值假設，`accounting_basis=not_applicable`）」，而
`METHOD_EV_TO_SALES`／parameter／公式／輸入指標全都在，9 檔 ledger 已經在用。

**多年橋卻硬編了 `parameter == "target_pe"`，看不見那條路**——L16 的形狀
（分類有 SSOT，但沒跟著資料走到需要它的地方）。所以這裡測的是「接上去」，
不是「發明一個虧損期估值法」。

⚠ 目標區（市值 ≤ US$10B）6 檔裡有 5 檔是虧損或無 diluted_eps，所以這條路不是
邊緣案例——**它是目標區的常態**。
"""
from __future__ import annotations

import pytest

from alpha.errors import ContractViolation
from alpha.reverse import build_reverse_bridge
from tests.test_reverse_bridge import _actuals, _full_set, TARGET


#: ⚠ fixture 的數字要有經濟意義，否則測到的是假東西。基期營收 1e9、股數 1e6 →
#: 每股營收 1,000；目標 EV／Sales 4x ⇒ 合理股價約 4,000（市值 4e9 ＝ 4× 營收）。
#: 第一版寫 price=10 ⇒ 市值 1e7 ＝ **0.01× 營收**，於是「500 倍」只需要營收成長 25%，
#: 而那個 `solved` 看起來像通過，其實是 fixture 不成立。
def _ev_reverse(*, price: float = 4_000.0, ev_to_sales: float = 4.0,
                multiple_of_return: float = 1.0, net_debt: float | None = 0.0,
                shares: float | None = 1_000_000.0, growth: float = 0.10):
    return build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=_full_set(growth, 0.0), current_price=price,
        target_multiple=ev_to_sales, our_eps=None, consensus_eps=None,
        target_return_multiple=multiple_of_return,
        basis="ev_to_sales", net_debt=net_debt, diluted_shares=shares)


def test_required_revenue_inverts_the_valuation_layer_formula_exactly() -> None:
    """公式必須是估值層那一條**反過來**，不得另立一套算術。

    正向（`alpha/valuation/model.py`）：
        fair_value/share = (revenue × target_ev_to_sales − net_debt) / diluted_shares
    要 fair_value/share ＝ 現價 × 倍率，反解即：
        required_revenue = (現價 × 倍率 × diluted_shares + net_debt) / target_ev_to_sales
    """
    result = _ev_reverse(price=10.0, ev_to_sales=4.0, multiple_of_return=2.0,
                         net_debt=5_000_000.0, shares=1_000_000.0)
    expected = (10.0 * 2.0 * 1_000_000.0 + 5_000_000.0) / 4.0
    assert result.required_eps == pytest.approx(expected)
    assert result.basis == "ev_to_sales"
    assert result.metric_label == "營收"
    assert result.required_metric == result.required_eps


def test_net_debt_is_never_defaulted_to_zero() -> None:
    """**不補 0**——把「沒讀到負債」當成「零負債」會讓所需營收憑空少掉整個負債。"""
    result = _ev_reverse(net_debt=None)
    assert result.status == "missing"
    assert "不補 0" in (result.reason or "")


def test_share_count_is_never_guessed() -> None:
    """每股換總量需要股數；沒有就誠實 missing，不猜一個。"""
    result = _ev_reverse(shares=None)
    assert result.status == "missing"
    assert "稀釋股數" in (result.reason or "")


def test_margin_drivers_are_structurally_irrelevant_not_unreachable() -> None:
    """營益率對**營收**的影響是零——那是「無關」，不是「撐不起」（L12）。

    若併進 `no_sign_change`，輸出會變成「連營益率拉到極限都撐不起營收目標」：
    那句話沒有意義，而且它對**每一檔**都會亮（L14-4：恆亮＝零鑑別力）。
    """
    result = _ev_reverse(multiple_of_return=2.0)
    irrelevant = [s for s in result.solutions
                  if s.status == "driver_does_not_affect_metric"]
    assert irrelevant, "EV／Sales 下營益率必須落在「結構上無關」那一格"
    for solution in irrelevant:
        assert solution.implied_value is None            # 無關不是一個數字
        assert "在結構上無關" in (solution.reason or "")
        assert solution.driver != "revenue_growth"       # 營收成長當然有關
    # 而且它們**不得**被算成「解不出來」——否則 EV／Sales 永遠是 partial。
    assert not any(s.status == "no_sign_change" and s.driver == "operating_margin_delta"
                   for s in result.solutions)


def test_revenue_growth_still_solves_because_revenue_is_monotone_in_it() -> None:
    """營收對 `revenue_growth` 是單調的——**這正是 EV／Sales 比 EPS 橋乾淨的地方**。

    `model.py` 的 docstring 自己記著：虧損公司的 EPS 對 `revenue_growth` 可以非單調
    （營收增加但營益率為負 → EPS 更負）。營收沒有那個問題。
    """
    result = _ev_reverse(multiple_of_return=1.2)
    solved = [s for s in result.solutions
              if s.driver == "revenue_growth" and s.status in ("solved", "already_equal")]
    assert solved, "營收成長必須解得出來，否則這條路等於沒接上"


def test_an_unreachable_multiple_is_still_a_conclusion() -> None:
    """**這個機制必須會滅也必須會亮**（L14-4）：倍率大到做不到時照樣說得出口。"""
    result = _ev_reverse(multiple_of_return=500.0)
    assert result.unreachable_drivers, "拉到極限也達不到時必須現形，不得靜默給值"
    for solution in result.unreachable_drivers:
        assert solution.implied_value is None


def test_an_unregistered_basis_is_refused_not_defaulted() -> None:
    """估值方法的權威在 `METHOD_PARAMETERS`——反解不得自己發明第三種。"""
    with pytest.raises(ContractViolation, match="basis 未登記"):
        build_reverse_bridge(
            company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
            actuals=_actuals(), assumptions=_full_set(0.10, 0.0), current_price=10.0,
            target_multiple=4.0, our_eps=None, consensus_eps=None, basis="dcf")


def test_the_earnings_path_is_byte_for_byte_unchanged() -> None:
    """預設 basis 走本益比法，**既有消費者一筆都不該壞**（L11-6）。"""
    result = build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=_full_set(0.10, 0.0), current_price=40.0,
        target_multiple=20.0, our_eps=1.60, consensus_eps=None, target_return_multiple=5.0)
    assert result.basis == "forward_earnings_multiple"
    assert result.metric_label == "EPS"
    assert result.required_eps == pytest.approx(10.0)        # 40 × 5 ÷ 20
    assert result.net_debt is None and result.diluted_shares is None
