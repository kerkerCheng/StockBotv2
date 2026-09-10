"""Reverse Bridge（`alpha/reverse`）——從現價反推市場隱含的營運假設。

守四件事：

1. **一次只解一個 driver，其餘固定。** 共識只給總量，分項本來就欠定（ROADMAP §B：
   「不得假造市場沒有提供的精確 driver」）。所以每個值都是條件解，`method` 必須說出來。
2. **不新增倍數自由度。** 沒有目標倍數就是 `missing`——**不得補市場倍數**，那會讓
   market_implied_eps 恆等於共識 EPS，整層變成一面鏡子。
3. **解不出來各有各的名字。** `no_sign_change`（拉到極限也撐不起）是結論不是缺料；
   `already_equal` 是答案不是失敗。
4. **反解不得有第二套算術。** 它走的是真正的 `build_bridge`，所以正向算不出來的，
   反解也算不出來——不會出現「只有反解才成立」的數字。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental.assumptions import assumption_record, parse_assumption_record
from alpha.contracts import EvidenceRef
from alpha.fundamental.contracts import FiscalPeriod, FiscalYearActuals
from alpha.reverse import build_reverse_bridge, solve_driver

UTC = timezone.utc
TARGET = FiscalPeriod(end=date(2027, 6, 30))
BASE = FiscalPeriod(end=date(2026, 6, 30))
REF = EvidenceRef(ref="graph://edge/x", kind="graph_edge")


def _actuals(**over) -> FiscalYearActuals:
    base = dict(
        period=BASE, currency="USD", revenue=1_000_000_000.0, segment_revenue={},
        gaap={"operating_income": 200_000_000.0, "diluted_eps": 1.00,
              "diluted_shares": 100_000_000.0},
        non_gaap=None, evidence=(REF,), recorded_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    base.update(over)
    return FiscalYearActuals(**base)


def _assume(driver: str, scope: str, value: float, *, basis: str = "session_judgment",
            derivation: str = "independent"):
    return parse_assumption_record(assumption_record(
        company_id="co:test", ticker="TEST", period_end=TARGET.end, driver=driver, scope=scope,
        value=value, basis=basis, rationale=f"test {driver}", evidence_refs=[REF.ref],
        created_at=datetime(2026, 9, 5, 8, 0, tzinfo=UTC), derivation=derivation))


def _full_set(growth: float = 0.10, margin_delta: float = 0.0):
    return [
        _assume("revenue_growth", "total", growth),
        _assume("operating_margin_delta", "operating_leverage", margin_delta),
        _assume("interest_and_other_net", "total", 0.0, basis="heuristic_proxy",
                derivation="carried_forward"),
        _assume("tax_rate", "total", 0.20, basis="heuristic_proxy", derivation="carried_forward"),
        _assume("nci_attribution", "total", 0.0, basis="observation", derivation="carried_forward"),
        _assume("diluted_shares", "total", 100_000_000.0, basis="observation",
                derivation="carried_forward"),
    ]


def _reverse(price: float, multiple: float, *, growth: float = 0.10, margin_delta: float = 0.0):
    assumptions = _full_set(growth, margin_delta)
    return build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=assumptions, current_price=price,
        target_multiple=multiple, our_eps=None, consensus_eps=None)


# ---------------------------------------------------------------------------
# 1. 反解本身
# ---------------------------------------------------------------------------

def test_market_implied_eps_is_price_over_our_multiple() -> None:
    result = _reverse(price=40.0, multiple=20.0)
    assert result.market_implied_eps == pytest.approx(2.0)


def test_solved_driver_actually_reproduces_the_target_eps() -> None:
    """反解出的值餵回**正向**的橋，必須算出目標 EPS——否則那是第二套算術。"""
    from alpha.fundamental.bridge import build_bridge
    from dataclasses import replace

    result = _reverse(price=40.0, multiple=20.0)      # 目標 EPS = 2.0
    growth = next(s for s in result.solutions if s.driver == "revenue_growth")
    assert growth.status == "solved"
    assumptions = [replace(a, value=growth.implied_value)
                   if a.assumption_id == growth.assumption_id else a
                   for a in _full_set(0.10, 0.0)]
    eps = build_bridge(_actuals(), assumptions, TARGET).metrics["eps"].value
    assert eps == pytest.approx(2.0, rel=1e-6)


def test_each_driver_is_solved_with_the_others_held_at_our_values() -> None:
    """兩個 driver 各自解出來的值，都是「其他假設不動」時的條件解。

    它們**不能同時成立**——同時套用兩個解會超過目標 EPS。這正是為什麼 method 必須逐字
    說「條件解，不是唯一解」：共識只給一個總量，分項欠定（ROADMAP §B）。
    """
    result = _reverse(price=40.0, multiple=20.0)
    assert {s.driver for s in result.solutions} == {"revenue_growth", "operating_margin_delta"}
    assert all(s.status == "solved" for s in result.solutions)
    assert "條件解" in result.method and "不是唯一解" in result.method


def test_our_value_equal_to_market_is_an_answer_not_a_failure() -> None:
    """`already_equal`：我們的預測就是市場的預測——`consensus_inverted` 的檔會長這樣。"""
    # 橋：營收 1.0e9 ×1.10 ＝ 1.10e9；營益率 20% → 2.20e8；稅 20% → 1.76e8；÷1e8 股 ＝ EPS 1.76。
    # ⚠ 不是基期印出的 diluted_eps 1.00——橋是從營收一路算下來的，不沿用印出的 EPS。
    result = _reverse(price=35.2, multiple=20.0)      # 目標 EPS = 1.76 ＝ 我們自己的預測
    for solution in result.solutions:
        assert solution.status == "already_equal"
        assert solution.implied_value == solution.our_value
        assert "不是失敗" in (solution.reason or "")
    assert result.status == "available"


def test_unreachable_price_is_a_conclusion_not_missing_data() -> None:
    """把 driver 拉到合法上限也撐不起現價 → `no_sign_change`，並說出兩端的值。"""
    result = _reverse(price=100_000.0, multiple=20.0)   # 目標 EPS = 5,000
    growth = next(s for s in result.solutions if s.driver == "revenue_growth")
    assert growth.status == "no_sign_change"
    assert growth.implied_value is None                 # 缺席不是數字
    assert "撐不起現價" in (growth.reason or "")
    assert "不是缺料" in (growth.reason or "")


# ---------------------------------------------------------------------------
# 2. 不新增倍數自由度
# ---------------------------------------------------------------------------

def test_missing_multiple_is_missing_and_never_falls_back_to_the_market_multiple() -> None:
    """沒有目標倍數就是 missing。

    補市場倍數（＝現價÷共識 EPS）會讓 market_implied_eps 恆等於共識 EPS，整層變成
    一面鏡子——那是「看起來有輸出」的最壞形式（L12：成功與失敗同形）。
    """
    result = build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=_full_set(), current_price=40.0,
        target_multiple=None, our_eps=1.10, consensus_eps=1.05)
    assert result.status == "missing"
    assert result.market_implied_eps is None
    assert "不補市場倍數" in (result.reason or "")


def test_missing_inputs_each_name_themselves() -> None:
    for kwargs, token in (
        ({"current_price": None}, "沒有現價"),
        ({"actuals": None}, "沒有基期觀測"),
    ):
        args = dict(company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
                    actuals=_actuals(), assumptions=_full_set(), current_price=40.0,
                    target_multiple=20.0, our_eps=None, consensus_eps=None)
        args.update(kwargs)
        result = build_reverse_bridge(**args)
        assert result.status == "missing" and token in (result.reason or "")


def test_no_opinion_bearing_assumptions_is_named_not_silently_empty() -> None:
    mechanical = [a for a in _full_set()
                  if a.driver not in ("revenue_growth", "operating_margin_delta")]
    result = build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=mechanical, current_price=40.0,
        target_multiple=20.0, our_eps=None, consensus_eps=None)
    assert result.status == "missing"
    assert "還沒開始做" in (result.reason or "")
    assert result.market_implied_eps == pytest.approx(2.0)   # 起點算得出來就照給


# ---------------------------------------------------------------------------
# 3. 契約：缺席不得攜帶數字
# ---------------------------------------------------------------------------

def test_absent_solution_cannot_carry_a_number() -> None:
    from alpha.reverse.contracts import DriverSolution

    with pytest.raises(ContractViolation, match="不得帶 implied_value"):
        DriverSolution(driver="revenue_growth", scope="total", assumption_id="oa_x", unit="ratio",
                       our_value=0.1, implied_value=0.5, status="no_sign_change", reason="r")
    with pytest.raises(ContractViolation, match="必須說出為什麼"):
        DriverSolution(driver="revenue_growth", scope="total", assumption_id="oa_x", unit="ratio",
                       our_value=0.1, implied_value=None, status="bridge_failed")


def test_eps_gap_is_relative_and_absent_when_either_side_is_missing() -> None:
    result = _reverse(price=44.0, multiple=20.0)     # 目標 EPS 2.2 vs 我們 1.10
    assert result.our_eps is None and result.eps_gap is None
    filled = build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=_full_set(), current_price=44.0,
        target_multiple=20.0, our_eps=1.10, consensus_eps=1.05)
    assert filled.eps_gap == pytest.approx(1.0)      # 市場隱含比我們高 100%


# ---------------------------------------------------------------------------
# 4. 到得了使用者眼前（L13：驗收是「產出出現在下游消費者手上」）
# ---------------------------------------------------------------------------

def test_driver_labels_cover_every_driver_and_are_not_a_second_source() -> None:
    """反推表印的是 driver，而 PLAIN_LINE_LABELS 的 key 是 line key——混用會露出內部代號。

    這份短標籤與 `ASSUMPTION_DRIVERS` 的 key 集合必須完全相同：少一個，使用者就會在某一列
    看到 `nci_attribution`；多一個，代表有人加了一個不存在的 driver。
    """
    from alpha.fundamental.contracts import ASSUMPTION_DRIVERS
    from briefing.analyst_view.contracts import PLAIN_DRIVER_LABELS

    assert set(PLAIN_DRIVER_LABELS) == set(ASSUMPTION_DRIVERS)
    for driver, label in PLAIN_DRIVER_LABELS.items():
        assert label and driver not in label, f"{driver} 的標籤不該是代號本身"


def test_reverse_bridge_reaches_the_app(tmp_path) -> None:
    """字彙隨 materialize 出門，前端用得到；而且前端不硬編 driver 名。"""
    import json
    from pathlib import Path

    from alpha.fundamental.contracts import ASSUMPTION_DRIVERS
    from webapp.materialize import write_vocabularies
    from webapp.store import ArtifactStore

    payload = json.loads(write_vocabularies(ArtifactStore(tmp_path)).read_text(encoding="utf-8"))
    assert set(payload["plain_driver_labels"]) == set(ASSUMPTION_DRIVERS)

    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(
        encoding="utf-8")
    assert "VOCAB.plain_driver_labels" in source
    assert "reverseBridgeBlock" in source
    # 「條件解」這句話必須跟表在一起——沒有它，讀者會把兩列當成可以同時成立
    assert "條件解" in source
