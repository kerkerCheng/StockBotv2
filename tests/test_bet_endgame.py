"""Q2（2026-09-17 使用者核准）：**籃子的每一列強制「有賭注 或 Abstention」，不准空白。**

## 為什麼這一條是籃子層最要緊的

2026-09-17 實測：籃子 16 檔 `accepted 0`，其中 **15 檔卡在「沒人寫賭注」**，
**沒有一檔**是因為 substitutability 或證據強度被擋。開別的門、擴別的宇宙，
如果進來的東西一樣沒人替它寫賭注，籃子還是空的。

## 這份測試守三件

1. **兩種「沒有賭注」不得同形**：「還沒有人寫」與「已研究、結論是不下注」分屬
   `not_yet_recorded` 與 `deliberate_abstention`（L12 一表兩義的修法：先分開再各自定規則）。
2. **估值層那筆不得頂替賭注層**：`valuation/target_pe` 的 abstention 說的是
   「本益比法沒有可校準的對象」——虧損年照樣可以寫「如果 X 為真它值 Y」。
   把它讀成「沒有可辯護的賭注」，等於用 `SETTLED_ABSENCE_KINDS` 把待辦冒充成答案。
   ⚠ 這正是本修法**如果錯了最先壞掉的那幾筆**：2026-09-17 實測籃子 16 檔有 5 檔
   （SOI.PA／IQE.L／MP／POET／6324.T）已宣告估值層 abstention 而賭注格仍是 `not_yet_recorded`。
3. **`unanswered` 會被計數、不會安靜消失**：0 也要印（INV-3）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.abstention.contracts import ABSTENTION_SUBJECTS, abstention_record
from alpha.providers.abstentions import append_abstention_record, read_abstention_records
from briefing.alpha_view.sources import variant_absence
from webapp.basket import BET_STATES, FILTER_REASONS, build_basket_artifact, build_basket_row

TODAY = date(2026, 9, 17)


def _abstention(tmp_path: Path, *, layer: str, subject: str, ticker: str = "X") -> None:
    record = abstention_record(
        company_id="co:x", ticker=ticker, layer=layer, subject=subject,
        reason="已研究：這一檔今天沒有可辯護的賭注，硬寫一個 variant 只會是編出來的數字。",
        revisit_when="下一份年報揭露瓶頸業務的產能與客戶承諾時重看",
        created_at=datetime(2026, 9, 16, tzinfo=timezone.utc), author="test")
    append_abstention_record(record, directory=tmp_path)


def _records(tmp_path: Path, ticker: str = "X"):
    records, errors = read_abstention_records(ticker, directory=tmp_path)
    assert not errors
    return records


# ---------------------------------------------------------------------------
# 取數層：沒有 variant 假設時，這是哪一種「沒有」
# ---------------------------------------------------------------------------

def test_no_bet_and_no_declaration_is_still_not_yet_recorded() -> None:
    reason, kind = variant_absence([], as_of=None, today=TODAY)
    assert kind == "not_yet_recorded"
    assert "還沒寫" in reason


def test_a_declared_bet_abstention_is_a_conclusion_not_a_todo(tmp_path: Path) -> None:
    _abstention(tmp_path, layer="bet", subject="variant.overlay")
    reason, kind = variant_absence(_records(tmp_path), as_of=None, today=TODAY)
    assert kind == "deliberate_abstention"
    assert "刻意不主張賭注" in reason and "ab_" in reason, "理由要指得出是哪一筆紀錄"


def test_a_valuation_abstention_must_not_stand_in_for_a_bet_abstention(tmp_path: Path) -> None:
    """**第 ④ 問的守門測試**：估值層那筆不得頂替賭注層（實測 5 檔會被冒充成答案）。"""
    _abstention(tmp_path, layer="valuation", subject="forward_earnings_multiple.target_pe")
    reason, kind = variant_absence(_records(tmp_path), as_of=None, today=TODAY)
    assert kind == "not_yet_recorded", "「本益比法沒有可校準的對象」不等於「沒有可辯護的賭注」"
    assert "刻意" not in reason


def test_a_retracted_abstention_stops_counting(tmp_path: Path) -> None:
    _abstention(tmp_path, layer="bet", subject="variant.overlay")
    existing = _records(tmp_path)[0]
    append_abstention_record(abstention_record(
        company_id="co:x", ticker="X", layer="bet", subject="variant.overlay",
        reason="撤回", revisit_when="撤回", created_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        supersedes_id=existing.abstention_id, retracted=True), directory=tmp_path)
    _reason, kind = variant_absence(_records(tmp_path), as_of=None, today=TODAY)
    assert kind == "not_yet_recorded", "撤回之後就回到欠一個答案"


def test_bet_layer_is_registered_as_a_closed_vocabulary() -> None:
    assert ABSTENTION_SUBJECTS["bet"] == ("variant.overlay",)
    with pytest.raises(Exception):
        abstention_record(company_id="co:x", ticker="X", layer="bet", subject="variant.whatever",
                          reason="x" * 30, revisit_when="y" * 20)


# ---------------------------------------------------------------------------
# 籃子層：每一列的賭注終局
# ---------------------------------------------------------------------------

def _rank_row(rank=1, ticker="X"):
    return {"rank": rank, "ticker": ticker, "company_id": "co:x", "company_label": ticker,
            "bottleneck": "tech:x", "relation": "supplies_to", "evidence": "externally_corroborated"}


def _ov(*, payoff=None, absence_kind="not_yet_recorded", reason="賭注還沒寫"):
    return {"payoff": {"status": "available" if payoff is not None else "missing",
                       "absence_kind": None if payoff is not None else absence_kind,
                       "reason": None if payoff is not None else reason,
                       "simple": {"value": payoff}},
            "price": {"value": 100.0}, "future_target": {"value_date": {"value": "2027-06-30"}},
            "brief": {"our_bet": {"value": None}}}


def test_three_bet_states_and_nothing_else() -> None:
    written = build_basket_row(_rank_row(), _ov(payoff=0.8), None, sector="s")
    abstained = build_basket_row(_rank_row(), _ov(absence_kind="deliberate_abstention",
                                                  reason="刻意不主張賭注（ab_1）：錨不住"), None, sector="s")
    owed = build_basket_row(_rank_row(), _ov(), None, sector="s")
    assert written["bet_state"] == "bet"
    assert abstained["bet_state"] == "abstained"
    assert owed["bet_state"] == "unanswered"
    for row in (written, abstained, owed):
        assert row["bet_state"] in BET_STATES, "bet_state 是封閉字彙，不得長出第四種"


def test_the_two_kinds_of_missing_bet_get_different_filter_reasons() -> None:
    """兩者都不通過 filter（abstention 不是賭注），但**理由必須分得出來**。"""
    abstained = build_basket_row(_rank_row(), _ov(absence_kind="deliberate_abstention"), None, sector="s")
    owed = build_basket_row(_rank_row(), _ov(), None, sector="s")
    assert "bet_abstained" in abstained["filter_reasons"] and "no_bet" not in abstained["filter_reasons"]
    assert "no_bet" in owed["filter_reasons"] and "bet_abstained" not in owed["filter_reasons"]
    assert not abstained["passes_filter"] and not owed["passes_filter"]
    assert {"no_bet", "bet_abstained"} <= set(FILTER_REASONS)


def test_a_row_with_no_overview_is_owed_an_answer_not_silently_dropped() -> None:
    out = build_basket_artifact(ranking={"rows": [_rank_row()], "sectors": []}, overviews={}, positions=None)
    assert out["rows"][0]["bet_state"] == "unanswered"
    assert out["bet_ledger"]["unanswered"] == 1


def test_bet_ledger_prints_every_state_including_zero() -> None:
    ranking = {"rows": [_rank_row(1, "A"), _rank_row(2, "B")], "sectors": []}
    out = build_basket_artifact(ranking=ranking, overviews={"A": _ov(payoff=0.5)}, positions=None)
    ledger = out["bet_ledger"]
    assert set(BET_STATES) <= set(ledger), "0 也要印——「欠 0 個答案」與「這一格沒算」不得同形"
    assert ledger["bet"] == 1 and ledger["unanswered"] == 1 and ledger["abstained"] == 0
    assert ledger["input"] == 2 and ledger["owed"] == ["B"]


def test_bet_state_is_part_of_the_cognitive_identity() -> None:
    """賭注終局變了＝使用者看到的是另一份判讀，freshness identity 必須跟著變。"""
    ranking = {"rows": [_rank_row()], "sectors": []}
    owed = build_basket_artifact(ranking=ranking, overviews={"X": _ov()}, positions=None)
    abstained = build_basket_artifact(ranking=ranking, overviews={"X": _ov(absence_kind="deliberate_abstention")},
                                      positions=None)
    assert owed["freshness_identity"] != abstained["freshness_identity"]
