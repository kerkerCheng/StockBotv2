"""V4 賭注收斂（`alpha/gap_closure.py` 三個純函式＋outcome 腳本那一段，2026-09-19）。

守的是**四個會靜默偏掉、而且偏向都固定對我們有利**的地方：

1. **起算日是賭注寫下那天，不是判斷日。** 判斷日恆早於賭注寫下日（實測三檔沒有一檔同日），
   用它當起點會把「賭注當時還不存在」那段期間的共識變動算成朝我們移動（INV-6）。
2. **一個賭注由多條 override 組成時取最晚那條。** 取最早＝主張還沒成形就開始記分。
3. **`scanned` ≠ `n_bets`。** 用掃描檔數當分母會把「大部分人沒下注」稀釋成「大部分賭注沒動」。
4. **`unchanged` ≠ `not_yet_observable`。** 前者是市場看過沒改，後者是還沒輪到市場說話。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from alpha.gap_closure import bet_convergence, bet_recorded_on, consensus_progress


@dataclass(frozen=True)
class _Assumption:
    created_at: datetime


@dataclass(frozen=True)
class _Model:
    overrides: tuple[_Assumption, ...]


def test_bet_recorded_on_takes_the_latest_override_not_the_earliest() -> None:
    """賭注在最後一條 override 寫下時才完整——取最早等於提前開始記分。"""
    model = _Model((
        _Assumption(datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)),
        _Assumption(datetime(2026, 9, 18, 2, 0, tzinfo=timezone.utc)),
    ))
    assert bet_recorded_on(model) == date(2026, 9, 18)
    assert bet_recorded_on(_Model(())) is None
    assert bet_recorded_on(None) is None
    # 字串時戳也認得（artifact 往返後是 ISO 字串），認不得的原樣跳過而不是整個炸掉
    assert bet_recorded_on(_Model((_Assumption("2026-09-16T00:00:00+00:00"),))) == date(2026, 9, 16)
    assert bet_recorded_on(_Model((_Assumption("not-a-date"),))) is None


def test_progress_exposes_the_denominator_so_a_blown_up_ratio_is_readable() -> None:
    """分母趨近 0 時比例會被放大到不可讀——分母必須跟著輸出（實測 5802.T −7175.7）。"""
    points = [(date(2026, 9, 8), 9.0), (date(2026, 9, 18), 10.347)]
    out = consensus_progress(points, since=date(2026, 9, 8), our_value=9.000188)
    assert out["gap_at_start"] is not None
    # 比例本身照算（不設門檻、不引入憑空參數），但讀者看得到它的分母有多小
    assert abs(out["closed_fraction"]) > 1000 and abs(out["gap_at_start"]) < 0.001
    assert "gap_at_start" in out["rule"]


def test_direction_is_toward_us_even_when_we_are_below_consensus() -> None:
    """我們比共識悲觀時分母為負；共識下修仍然是「朝我們移動」。"""
    below = consensus_progress([(date(2026, 9, 8), 9.0), (date(2026, 9, 18), 8.5)],
                               since=date(2026, 9, 8), our_value=8.0)
    conv = bet_convergence([("T", {"variant": below, "bet_since": date(2026, 9, 8)})])
    assert conv["rows"][0]["state"] == "toward_us" and below["gap_at_start"] < 0
    up = consensus_progress([(date(2026, 9, 8), 9.0), (date(2026, 9, 18), 9.5)],
                            since=date(2026, 9, 8), our_value=8.0)
    assert bet_convergence([("T", {"variant": up, "bet_since": date(2026, 9, 8)})])["rows"][0]["state"] == "away_from_us"


def test_scanned_and_n_bets_are_not_the_same_number() -> None:
    """掃了 3 份 artifact 但只有 1 份有賭注——分母是後者。"""
    moved = consensus_progress([(date(2026, 9, 15), 9.0), (date(2026, 9, 18), 9.0)],
                               since=date(2026, 9, 15), our_value=9.5)
    conv = bet_convergence([
        ("A", {"variant": moved, "bet_since": date(2026, 9, 15)}),
        ("B", {"variant": None, "bet_since": None}),
        ("C", {}),
    ])
    assert conv["scanned"] == 3 and conv["n_bets"] == 1 and conv["no_bet"] == 2
    # 沒下注的檔只進計數不進 rows——19 筆空列會把 3 筆真資料淹掉
    assert [r["ticker"] for r in conv["rows"]] == ["A"]


def test_not_yet_observable_is_never_folded_into_unchanged() -> None:
    """「賭注寫下後還沒有共識抓取」與「共識沒動」是相反的結論，不得同形（L12）。"""
    still = consensus_progress([(date(2026, 9, 15), 9.0), (date(2026, 9, 18), 9.0)],
                               since=date(2026, 9, 15), our_value=9.5)
    未來 = consensus_progress([(date(2026, 9, 15), 9.0), (date(2026, 9, 18), 9.0)],
                             since=date(2026, 9, 19), our_value=9.5)
    assert 未來["status"] == "missing"
    conv = bet_convergence([("A", {"variant": still, "bet_since": date(2026, 9, 15)}),
                            ("B", {"variant": 未來, "bet_since": date(2026, 9, 19)})],
                           today=date(2026, 9, 19))
    assert conv["unchanged"] == 1 and conv["not_yet_observable"] == 1
    assert conv["measurable"] == 1                      # 沒算進分母
    assert conv["toward_us"] == 0 and conv["away_from_us"] == 0


def test_window_length_and_biases_always_travel_with_the_numbers() -> None:
    """窗短時「沒動」幾乎是必然；不印窗長等於邀請人把「還沒發生」讀成「不會發生」。"""
    still = consensus_progress([(date(2026, 9, 15), 9.0), (date(2026, 9, 18), 9.0)],
                               since=date(2026, 9, 15), our_value=9.5)
    conv = bet_convergence([("A", {"variant": still, "bet_since": date(2026, 9, 15)})])
    assert conv["longest_window_days"] == 3 and conv["shortest_window_days"] == 3
    assert len(conv["known_biases"]) >= 3
    assert any("window_days" in b for b in conv["known_biases"])


def test_days_waiting_never_enters_the_observed_window_range() -> None:
    """「已觀測 3 天」與「等了 0 天還沒抓到」混算會讓「窗 0–3 天」同時意味兩件事（L12）。"""
    still = consensus_progress([(date(2026, 9, 15), 9.0), (date(2026, 9, 18), 9.0)],
                               since=date(2026, 9, 15), our_value=9.5)
    未來 = consensus_progress([(date(2026, 9, 18), 9.0)], since=date(2026, 9, 19), our_value=9.5)
    conv = bet_convergence([("A", {"variant": still, "bet_since": date(2026, 9, 15)}),
                            ("B", {"variant": 未來, "bet_since": date(2026, 9, 19)})],
                           today=date(2026, 9, 19))
    assert conv["shortest_window_days"] == 3 and conv["longest_window_days"] == 3
    assert conv["longest_days_waiting"] == 0
    waiting_row = next(r for r in conv["rows"] if r["state"] == "not_yet_observable")
    assert "window_days" not in waiting_row and waiting_row["days_waiting"] == 0


def test_empty_is_reported_as_no_one_has_bet_not_as_zero_percent() -> None:
    """沒有賭注時印「還沒有分子也沒有分母」，不是一個假的 0%（同 power-law 的取捨）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_oist", "scripts/outcome_if_settled_today.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = chr(10).join(module.render_bet_convergence(bet_convergence([])))
    # 文案刻意逐字否定那個 0%——「還沒有分母」與「分母有但分子是 0」是相反的結論
    assert "還沒有任何一檔寫下賭注" in text and "這不是 0%" in text
    # V4 之前產的 artifact 不得長得像一個誠實的空集合
    stale = module.render_bet_convergence({"n_bets": 0, "stale_artifacts": ["COHR"], "rows": []})
    assert "materialize" in chr(10).join(stale)
