"""最弱軸的排序基準：level，不是 ceiling。

⚠ 這是 characterization，不是 red-first。`config/investment_policy.json` 的
`axis_ceilings` 是 level 到 ceiling 的嚴格單調映射（unknown 0.0 < bounded_hypothesis
0.002 < corroborated 0.005），所以舊的 ceiling 排序與新的 level 排序**結果完全相同**，
tie-break 也一樣落到 `AXES.index`。新測試在改動前就會通過。

那為什麼還要改？因為 ceiling 即將被移除（U7）。最弱軸的角色從「資本上限的決定者」
變成「該補哪一項證據」的指標，它不該再依賴一個資本欄位才算得出來。這些測試的作用是
在移除 ceiling 之前，先把行為釘住——U7 拔掉欄位後它們必須仍然全綠。
"""
from __future__ import annotations

from decision_lab.sizing import AXES, LEVELS, weakest_axis_of


def _axes(**levels: str) -> dict[str, dict[str, object]]:
    """建一組五軸；未指定者預設 corroborated（最強）。

    `effective_level` 預設等於宣告的 level——也就是「引用都成立」的正常情形。
    要模擬引用不成立，測試自行覆寫該欄位。
    """
    ceilings = {"unknown": 0.0, "bounded_hypothesis": 0.002, "corroborated": 0.005}
    return {
        axis: {
            "level": levels.get(axis, "corroborated"),
            "effective_level": levels.get(axis, "corroborated"),
            "ceiling": ceilings[levels.get(axis, "corroborated")],
        }
        for axis in AXES
    }


def test_returns_the_axis_with_the_lowest_level() -> None:
    axes = _axes(commercial_maturity="bounded_hypothesis")

    assert weakest_axis_of(axes) == "commercial_maturity"


def test_unknown_beats_bounded_hypothesis() -> None:
    axes = _axes(commercial_maturity="bounded_hypothesis", valuation_payoff="unknown")

    assert weakest_axis_of(axes) == "valuation_payoff"


def test_ties_fall_back_to_axes_declaration_order() -> None:
    """同 level 時取 AXES 中較前者——source_reliability 優先。

    level 只有三階，比 ceiling 粗，所以並列會很常見；tie-break 必須是確定性的，
    否則同一份資料在不同執行間可能給出不同的「該補什麼」。
    """
    axes = _axes(technical_causal_link="unknown", source_reliability="unknown")

    assert weakest_axis_of(axes) == "source_reliability"
    assert AXES.index("source_reliability") < AXES.index("technical_causal_link")


def test_all_corroborated_still_returns_a_definite_axis() -> None:
    """全部最強時仍要回傳確定值，不得回 None——下游拿它產生 pq2 項目文字。"""
    result = weakest_axis_of(_axes())

    assert result == AXES[0]


def test_unrecognised_level_sorts_weakest() -> None:
    """未登記的 level 視為最弱，不得靜默排到最強。

    寧可多提醒一次「這一軸有問題」，也不要讓一個拼錯的 level 讓該軸看起來已經佐證完整。
    """
    axes = _axes(commercial_maturity="bounded_hypothesis")
    axes["valuation_payoff"]["effective_level"] = "typo_level"

    assert weakest_axis_of(axes) == "valuation_payoff"


def test_effective_level_overrides_the_declared_level() -> None:
    """宣告 corroborated 但引用不成立時，該軸才是最弱的。

    實測（2026-08-28）：`_validate_assessment` 在 fatal_axis_blocker（例如
    evidence_missing）時把 ceiling 打成 0，卻**不動**宣告的 level——只有
    context_mismatch 才會把 level 降為 unknown。舊排序靠 ceiling 隱含吃到這個資訊；
    改用 raw level 會漏掉它。`effective_level` 是把它顯性化的欄位，排序必須優先用它。
    """
    axes = _axes(commercial_maturity="bounded_hypothesis")
    axes["valuation_payoff"]["effective_level"] = "unknown"  # 宣告 corroborated，引用不成立

    assert weakest_axis_of(axes) == "valuation_payoff"


def test_falls_back_to_level_when_effective_level_absent() -> None:
    """舊 payload 沒有 effective_level 時退回 level，不得因缺欄位而爆掉。"""
    axes = _axes(commercial_maturity="bounded_hypothesis")
    for entry in axes.values():
        entry.pop("effective_level", None)

    assert weakest_axis_of(axes) == "commercial_maturity"


def test_matches_the_previous_ceiling_based_ordering_when_ceiling_tracks_level() -> None:
    """characterization：ceiling 純由 level 決定時，新舊排序一致。

    ⚠ 這條的適用範圍比我最初以為的窄。我原本主張「U2 是零行為變化的純重構」，
    理由是 `axis_ceilings` 是 level 到 ceiling 的單調映射。那個推論漏了
    `_validate_assessment` 會覆寫 ceiling——`test_probe_sizing.py::...[missing_ref]`
    在改動後立刻紅，證明兩者並非同構。這條測試現在只涵蓋 ceiling 確實跟隨 level 的
    情形；引用不成立的情形由上面的 effective_level 測試涵蓋。
    """
    import itertools

    def legacy(axes):
        return min(AXES, key=lambda a: (axes[a]["ceiling"], AXES.index(a)))

    for combo in itertools.product(LEVELS, repeat=len(AXES)):
        axes = _axes(**dict(zip(AXES, combo)))
        assert weakest_axis_of(axes) == legacy(axes), combo
