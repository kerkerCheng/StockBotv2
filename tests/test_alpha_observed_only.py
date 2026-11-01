"""alpha 格只觀測（AGENTS「alpha 格只觀測、不設目標」2026-09-16 D1；2026-11-01 落地，使用者「兩點都照你建議吧」）。

守的事：①alpha 的實際佔比照印，state＝observed_only，不算差距；②不論 alpha 佔比多低或多高，「低於目標、新資金可優先補」
與「高於目標、新資金避開」都不出現 alpha——目標比例不得從配置頁的後門變回尺寸壓力；③報表的目標與容忍區間寫「不設」、
差距寫「不比」，不是「未知」（刻意不比與缺值是兩件事，L12）；④算不到時照舊是「算不到」，不壓成 0；
⑤全部有目標時總和仍必須等於 1.0（原本的嚴格檢查沒有放寬）；⑥beta 五格的判定照舊。
"""
from __future__ import annotations

import copy

import pytest

from portfolio.allocation import _allocation_gap_lines
from portfolio.policy import TargetAllocationError, load_target_allocation, validate_target_allocation
from test_beta_monitor import _gap


def _rows(alpha_value: float) -> list[dict]:
    """非現金 100：VWRA 填滿 beta_core 目標，剩下的一部分丟給 alpha 殘量（名冊外的持股），其餘放 2330。"""
    target = load_target_allocation()
    core = 100.0 * target["sleeves"]["beta_core"]["target"]
    return [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": 10.0, "nav_base": 110.0, "base_currency": "USD"},
        {"ticker": "LON:VWRA", "bucket": "大盤", "market_value_base": core, "nav_base": 110.0, "base_currency": "USD"},
        {"ticker": "UNMAPPED", "bucket": "觀察", "market_value_base": alpha_value, "nav_base": 110.0,
         "base_currency": "USD"},
        {"ticker": "2330.TW", "bucket": "個股", "market_value_base": 100.0 - core - alpha_value, "nav_base": 110.0,
         "base_currency": "USD"},
    ]


@pytest.mark.parametrize("alpha_value", [1.0, 40.0])        # 1%（舊規則判低於 5%）與 40%（舊規則判高於 15%）
def test_alpha_is_printed_but_never_compared_or_steered(alpha_value) -> None:
    gap = _gap(_rows(alpha_value))
    alpha = {item["sleeve"]: item for item in gap["sleeves"]}["alpha"]
    assert alpha["state"] == "observed_only" and alpha["observed_only"] is True
    assert alpha["actual"] == pytest.approx(alpha_value / 100.0)
    assert alpha["target"] is None and alpha["band"] is None and alpha["gap"] is None
    text = "\n".join(_allocation_gap_lines({"allocation_gap": gap}, "USD"))
    summary = next(line for line in text.splitlines() if line.startswith("- **"))
    assert "alpha" not in summary, summary                    # 不引導新資金往 alpha 補或避開
    row = next(line for line in text.splitlines() if line.startswith("| alpha"))
    assert "| 不設 | 不設 |" in row and "| 不比 |" in row and "未知" not in row
    assert "只觀測、不設目標" in row


def test_beta_sleeves_are_still_compared() -> None:
    gap = _gap(_rows(1.0))
    by = {item["sleeve"]: item for item in gap["sleeves"]}
    assert by["beta_core"]["state"] == "on_target" and by["beta_core"]["observed_only"] is False
    assert by["beta_leverage"]["state"] == "below_band"     # 空手的 beta 格照樣標低於目標


def test_unknown_stays_unknown_not_zero() -> None:
    gap = _gap(None)
    alpha = {item["sleeve"]: item for item in gap["sleeves"]}["alpha"]
    assert alpha["actual"] is None and alpha["state"] == "unknown"


def test_the_strict_sum_still_applies_when_every_sleeve_has_a_target() -> None:
    """只觀測沒有放寬原本的檢查：六格都有目標時總和仍必須是 1.0。"""
    target = copy.deepcopy(load_target_allocation())
    target["sleeves"]["alpha"] = {"target": 0.10, "band": 0.05, "role": "x"}
    assert validate_target_allocation(target)["sleeves"]["alpha"]["target"] == 0.10
    target["sleeves"]["alpha"]["target"] = 0.20
    with pytest.raises(TargetAllocationError, match="sum to 1.0"):
        validate_target_allocation(target)
