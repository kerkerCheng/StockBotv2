"""Phase 7：`AlphaSignal[]` × 持股 → 候選目前佔 NAV 多少。

⚠ 本檔守的核心只有兩件事：
① **輸出裡不得出現任何部位尺寸**（`AGENTS.md` Alpha 呈現契約）；
② **「沒持有」與「持股讀不到」不得同形**（L12／L13）——後者會讓使用者看到
「你一檔都沒買」，而事實是「我沒讀到你買了什麼」，兩者導向相反的行動。
"""
from __future__ import annotations

import pytest

from portfolio.alpha_exposure import (
    build_alpha_candidate_exposure, render_alpha_candidate_exposure,
)


def _signal(ticker: str, company: str | None = None) -> dict:
    return {"ticker": ticker, "company_id": company}


def _nav(*positions, status: str = "available") -> dict:
    return {"status": status, "positions": list(positions),
            "cash_pct": 0.1, "buckets": {}, "groups": {}, "blockers": []}


def _pos(ticker: str, pct: float, lots: int = 1) -> dict:
    return {"ticker": ticker, "nav_pct": pct, "lots": lots}


# ---------------------------------------------------------------------------
# 1. join 本身
# ---------------------------------------------------------------------------

def test_candidates_are_joined_to_current_holdings() -> None:
    view = build_alpha_candidate_exposure(
        [_signal("COHR", "co:coherent"), _signal("AXTI", "co:axt")],
        _nav(_pos("COHR", 0.031), _pos("QQQ", 0.2)),
    )
    assert view["status"] == "available"
    assert [c["ticker"] for c in view["candidates"]] == ["COHR", "AXTI"]
    assert view["candidates"][0]["held"] is True
    assert view["candidates"][0]["nav_pct"] == 0.031
    assert view["candidates"][0]["company_id"] == "co:coherent"
    assert view["candidates"][1]["held"] is False
    assert view["held_count"] == 1 and view["unheld_count"] == 1


def test_incoming_order_is_preserved_because_ranking_lives_elsewhere() -> None:
    """唯一排序權威是 `rank_bottlenecks`；這一層不重排、不加權。

    空跑檢查：在 `build_alpha_candidate_exposure` 裡依 `nav_pct` 排序 → 這條會紅。
    """
    view = build_alpha_candidate_exposure(
        [_signal("AAA"), _signal("BBB"), _signal("CCC")],
        _nav(_pos("CCC", 0.9), _pos("BBB", 0.5)),
    )
    assert [c["ticker"] for c in view["candidates"]] == ["AAA", "BBB", "CCC"]


def test_duplicate_tickers_collapse_but_keep_first_position() -> None:
    view = build_alpha_candidate_exposure(
        [_signal("COHR"), _signal("AXTI"), _signal("COHR")], _nav())
    assert [c["ticker"] for c in view["candidates"]] == ["COHR", "AXTI"]


def test_ticker_match_is_case_insensitive() -> None:
    view = build_alpha_candidate_exposure([_signal("cohr")], _nav(_pos("COHR", 0.02)))
    assert view["candidates"][0]["held"] is True


# ---------------------------------------------------------------------------
# 2. 「沒持有」vs「讀不到」——本檔最重要的一組
# ---------------------------------------------------------------------------

def test_unavailable_holdings_do_not_emit_zero_percent_per_candidate() -> None:
    """⚠ 持股讀不到時**不得**逐檔輸出 0.0%。

    那會讓使用者看到「你一檔都沒買」，而事實是「我沒讀到你買了什麼」——
    兩者導向完全相反的行動（L12）。

    空跑檢查：把 `status not in _AVAILABLE` 那道 early return 拿掉 → 這條會紅
    （會冒出一串 `nav_pct: 0.0` 的候選）。
    """
    view = build_alpha_candidate_exposure(
        [_signal("COHR"), _signal("AXTI")],
        {"status": "unavailable", "positions": [], "blockers": ["holdings_unavailable"]},
    )
    assert view["candidates"] == []
    assert view["candidate_tickers"] == ("COHR", "AXTI")
    assert "holdings_unavailable" in view["blockers"]
    assert "held_count" not in view, "讀不到就不該報「已持有幾檔」"


def test_zero_percent_only_appears_when_holdings_really_were_read() -> None:
    view = build_alpha_candidate_exposure([_signal("AXTI")], _nav(_pos("QQQ", 0.5)))
    assert view["candidates"][0] == {
        "ticker": "AXTI", "company_id": None, "held": False,
        "nav_pct": 0.0, "sleeve": None, "lots": None,
    }


def test_upstream_failure_string_is_carried_through() -> None:
    """取得端的失敗原因要帶出來，否則下游只能猜（L12：因果不得被截斷）。"""
    view = build_alpha_candidate_exposure(
        [_signal("COHR")],
        {"status": "sheet_error", "positions": [], "blockers": [],
         "failure": "credentials_expired"},
    )
    assert view["failure"] == "credentials_expired"
    assert view["blockers"] == ["holdings_unavailable"]


def test_confirmed_empty_is_a_real_answer_not_a_failure() -> None:
    """「確認過、真的沒持股」與「讀不到」是兩件事——前者算讀到了。"""
    view = build_alpha_candidate_exposure(
        [_signal("COHR")], _nav(status="confirmed_empty"))
    assert view["candidates"][0]["held"] is False
    assert view["held_count"] == 0


# ---------------------------------------------------------------------------
# 3. 不得出現任何部位尺寸
# ---------------------------------------------------------------------------

_SIZE_TOKENS = (
    "target", "suggested", "recommended", "size", "shares", "order",
    "supported_range", "ceiling", "budget", "allocation_amount",
)


def test_output_contains_no_position_sizing_field() -> None:
    """`AGENTS.md`：系統不給 alpha 部位尺寸。

    ⚠ 參考線欄位刻意叫 `single_position_nav_cap_reference` 而不是 `..._cap`——
    名字要自己說出它不是 gate。

    空跑檢查：加一個 `suggested_shares` 欄位 → 這條會紅。
    """
    view = build_alpha_candidate_exposure([_signal("COHR")], _nav(_pos("COHR", 0.03)))
    keys = set(view) | {k for c in view["candidates"] for k in c}
    offenders = [
        k for k in keys
        for token in _SIZE_TOKENS
        if token in k.lower() and not k.endswith("_reference")
    ]
    assert not offenders, f"輸出長出了部位尺寸欄位：{offenders}"


def test_the_nav_cap_is_a_reference_line_not_a_gate() -> None:
    """超過 5% 不產生 blocker、不告警、不改變任何欄位——它只是印出來給人看。

    真正的硬擋在 `store.record_live_choice`，那裡一個字都沒放寬。
    """
    view = build_alpha_candidate_exposure(
        [_signal("COHR")], _nav(_pos("COHR", 0.42)),
        single_position_nav_cap=0.05,
    )
    assert view["candidates"][0]["nav_pct"] == 0.42
    assert view["blockers"] == []
    assert view["single_position_nav_cap_reference"] == 0.05


# ---------------------------------------------------------------------------
# 4. 不靜默丟棄（INV-3）
# ---------------------------------------------------------------------------

def test_signals_without_a_ticker_are_listed_not_dropped() -> None:
    view = build_alpha_candidate_exposure(
        [_signal("COHR"), {"company_id": "co:private"}, _signal("  ")], _nav())
    assert [c["ticker"] for c in view["candidates"]] == ["COHR"]
    assert view["unresolved_signal_indexes"] == (1, 2)


def test_sleeve_is_none_when_unmapped_never_guessed() -> None:
    view = build_alpha_candidate_exposure(
        [_signal("COHR"), _signal("QQQ")], _nav(), sleeves={"QQQ": "beta_core"})
    assert view["candidates"][0]["sleeve"] is None
    assert view["candidates"][1]["sleeve"] == "beta_core"


# ---------------------------------------------------------------------------
# 5. 呈現層的措辭
# ---------------------------------------------------------------------------

def test_render_makes_unreadable_holdings_look_unreadable() -> None:
    """措辭必須讓人看出「讀不到」，不能長得像「沒買」。

    空跑檢查：把那行改成「目前未持有下列候選」→ 這條會紅。
    """
    lines = render_alpha_candidate_exposure(build_alpha_candidate_exposure(
        [_signal("COHR")],
        {"status": "unavailable", "positions": [], "blockers": ["holdings_unavailable"]},
    ))
    text = "\n".join(lines)
    assert "讀不到" in text and "無法" in text
    assert "未持有" not in text


def test_render_uses_no_action_verbs() -> None:
    """呈現層不得出現建議動作——那是已拔除的四動作字彙。"""
    lines = render_alpha_candidate_exposure(build_alpha_candidate_exposure(
        [_signal("COHR"), _signal("AXTI")], _nav(_pos("COHR", 0.031)),
        single_position_nav_cap=0.05,
    ))
    text = "\n".join(lines)
    for banned in ("TRADE", "HEDGE", "NO_ACTION", "建議買", "可投入", "本輪"):
        assert banned not in text
    assert "COHR" in text and "3.10%" in text
    assert "參考線" in text


def test_render_handles_no_candidates() -> None:
    assert render_alpha_candidate_exposure(
        build_alpha_candidate_exposure([], _nav())) == ["目前沒有 alpha 候選。"]


@pytest.mark.parametrize("bad", [None, {}, {"status": "available"}])
def test_render_never_raises_on_degenerate_input(bad) -> None:
    assert isinstance(render_alpha_candidate_exposure(bad), list)
