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


def test_the_three_level_ordinal_has_exactly_one_definition() -> None:
    """`alpha` 與 Engine D 用的必須是**同一個物件**，不是逐字相同的兩份。

    ⚠ 用 `is` 而不是 `==`：`==` 對「有人抄了第二份、目前剛好一樣」也會過，
    而那正是 2026-09-04 之前的狀態——兩邊各存一份 tuple，靠 `alpha/levels.py`
    的一句註解（「與 `decision_lab/sizing.py::LEVELS` 逐字相同」）維持同步，
    **沒有任何測試守它**。

    漂掉的後果不會報錯：`legacy_axes.convert_axis_results` 讀 268 筆歷史 payload
    時會靜默誤轉，排序悄悄變了而沒有任何東西變紅（L16 第 3 點：字彙一旦有行為
    後果就必須被強制；L13：最危險的是成功與失敗在同一個訊號上同形）。
    """
    from alpha.levels import LEVELS as alpha_levels
    from shared.evidence_levels import LEVELS as shared_levels

    assert LEVELS is shared_levels, "Engine D 的 LEVELS 不是 shared 的那一份"
    assert alpha_levels is shared_levels, "alpha 的 LEVELS 不是 shared 的那一份"


def test_the_dual_run_comparator_breaks_ties_the_same_way() -> None:
    """對照器與權威**必須同意**，否則它報出來的「零差異」沒有意義。

    事發（2026-09-04）：`alpha.legacy_axes.legacy_weakest` 用 `min()` over
    `(rank, name)` tuple，同階時比**軸名字母序**；權威 `weakest_axis_of` 比的是
    `AXES` 的**宣告序**。五軸同階時前者回 `commercial_maturity`、後者回
    `source_reliability`。

    ⚠ 而 Phase 1 的 dual run 報告是「41 cohort、UNEXPECTED 0」——**那不是兩者
    一致，是那 41 筆剛好沒有並列最弱軸**。這正是 L13 第 2 點：最危險的是成功與
    失敗在同一個訊號上同形，要驗就驗那個會因為「真的成功」而改變的東西。
    所以這條刻意**只測平手**——單一最弱軸的案例本來就會過，測它等於沒測。
    """
    from alpha.legacy_axes import legacy_weakest

    all_tied = {
        axis: {"level": "bounded_hypothesis", "effective_level": "bounded_hypothesis"}
        for axis in AXES
    }
    assert legacy_weakest(all_tied) == weakest_axis_of(all_tied) == "source_reliability"

    # 宣告序上不相鄰的兩軸並列：字母序會挑 commercial_maturity，宣告序挑
    # source_reliability——兩種 tie-break 在這裡答案不同，所以它測得到。
    pair_tied = {
        axis: {"level": "corroborated", "effective_level": "corroborated"}
        for axis in AXES
    }
    for axis in ("source_reliability", "commercial_maturity"):
        pair_tied[axis] = {"level": "unknown", "effective_level": "unknown"}
    assert legacy_weakest(pair_tied) == weakest_axis_of(pair_tied) == "source_reliability"


def test_the_comparator_still_tolerates_missing_axes() -> None:
    """對照器讀的是歷史 payload，缺軸要容忍；權威要求五軸齊全，缺軸該 KeyError。

    兩者的容忍度**刻意不同**，所以對照器不能直接呼叫權威——只共用 tie-break。
    這條把那個差異釘住，否則下次有人「順手統一」就會讓 dual run 對半數歷史
    payload 拋例外。
    """
    import pytest

    from alpha.legacy_axes import legacy_weakest

    partial = {"valuation_payoff": {"level": "unknown"}}
    assert legacy_weakest(partial) == "valuation_payoff"
    assert legacy_weakest({}) is None
    with pytest.raises(KeyError):
        weakest_axis_of(partial)
