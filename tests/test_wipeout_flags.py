"""歸零旗標（D2，2026-09-18）的純邏輯測試——不需要 Neo4j／Engine C。

**這份測試守的是一句話：綠燈只能由「量到了而且沒事」產生。**
把「沒查」塗成綠是這個機制唯一會造成實害的失敗——它給出一個憑空的安心，而那正是歸零旗標
要防的東西。所以下面每一條都圍著它轉：

1. **灰不是綠**：沒量到的燈沒有顏色，而且自己宣告是哪一種沒有（`absence_kind`）。
2. **型別層擋得住**：有顏色的燈不得帶缺席語意；沒顏色的燈不得沒有缺席語意。
3. **零憑空門檻**：兩個常數都指得出外部出處；除此之外只有符號比較。
4. **稀釋那盞的窗規則**：窗不滿一個完整會計年度就不判色——連「沒增加」也不判綠。
5. **燈不參與排序、不進 filter**：它是量測不是訊號（INV-5／L14）。
6. **交付一項能力就要把它從心跳的「還沒建」清單拿掉**：留著不會有任何東西變紅，
   它只會每天安靜印一句假話（事發 2026-09-18，見 `crons/heartbeat.py::build_positions`）。
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from alpha.absence import ABSENCE_KINDS
from alpha.wipeout import (
    FLAG_COLOURS, FULL_YEAR_DAYS, GOING_CONCERN_HORIZON_MONTHS, WIPEOUT_LANES,
    cash_runway_flag, debt_flag, dilution_flag, going_concern_flag, tally, wipeout_flags,
)

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 18)


def _runway(cash=100.0, debt=50.0, fcf=-10.0, status="calculated", months=120.0):
    return {"cash_and_equivalents": cash, "total_debt": debt, "free_cash_flow_ttm": fcf,
            "status": status, "runway_months": months, "source": "test", "as_of": "2026-09-18"}


def _series(days: int, *, change: float = 0.0):
    """一條同口徑股數序列：跨度 `days` 天、期末相對期初變動 `change`。"""
    start = TODAY.fromordinal(TODAY.toordinal() - days)
    return [(start, 1_000_000.0), (TODAY, 1_000_000.0 * (1 + change))]


# ---------------------------------------------------------------------------
# 1＋2. 灰不是綠；型別層擋得住兩種同形
# ---------------------------------------------------------------------------

def test_an_unlit_lamp_has_no_colour_and_declares_which_kind_of_absence() -> None:
    """沒量到的燈**沒有顏色**，而且自己說是哪一種沒有——呈現層不必 parse 理由句（L16）。"""
    flag = cash_runway_flag({"status": "manual_required", "runway_months": None})
    assert flag["colour"] is None
    assert flag["absence_kind"] in ABSENCE_KINDS
    assert flag["absence_kind"] == "upstream_unavailable"


def test_missing_inputs_never_produce_a_green_lamp() -> None:
    """**這是整個機制的重點**：輸入缺席時，四盞燈裡不得有任何一盞是綠的。"""
    flags = wipeout_flags(runway={"status": "manual_required"}, shares_series=[],
                          going_concern=None, today=TODAY)
    assert all(lane["colour"] != "green" for lane in flags.values())
    assert tally(flags)["green"] == 0
    assert tally(flags)["unlit"] == len(WIPEOUT_LANES)


def test_a_lit_lamp_cannot_carry_an_absence_kind_and_vice_versa() -> None:
    """有顏色卻帶缺席語意（或反過來）在建構時就要炸——不留到序列化之後才發現。"""
    from alpha.wipeout import _flag

    with pytest.raises(ValueError):
        _flag("green", "有顏色卻說自己缺席", rule="r", inputs={}, absence_kind="not_yet_recorded")
    with pytest.raises(ValueError):
        _flag(None, "沒顏色又沒說是哪一種沒有", rule="r", inputs={})
    with pytest.raises(ValueError):
        _flag("grey", "灰不是一個顏色——它是「沒有顏色」", rule="r", inputs={})


def test_grey_is_not_one_of_the_colours() -> None:
    """灰刻意**不在** `FLAG_COLOURS` 裡：讓「這盞是綠的」與「這盞沒點亮」型別上不可能同形。"""
    assert set(FLAG_COLOURS) == {"red", "amber", "green"}
    assert "grey" not in FLAG_COLOURS and "unlit" not in FLAG_COLOURS


# ---------------------------------------------------------------------------
# 3. 零憑空門檻
# ---------------------------------------------------------------------------

def test_cash_runway_uses_the_going_concern_horizon_and_nothing_else() -> None:
    """唯一的數字門檻是 12 個月——IFRS／UK 的 going-concern 最短評估期，不是我們挑的。"""
    assert GOING_CONCERN_HORIZON_MONTHS == 12
    assert cash_runway_flag(_runway(fcf=5.0, status="self_funding", months=None))["colour"] == "green"
    assert cash_runway_flag(_runway(months=GOING_CONCERN_HORIZON_MONTHS - 0.1))["colour"] == "red"
    assert cash_runway_flag(_runway(months=GOING_CONCERN_HORIZON_MONTHS))["colour"] == "amber"


def test_debt_lamp_is_pure_sign_comparison_without_any_threshold() -> None:
    """負債那盞一個門檻都沒有：淨現金→綠、淨負債且自籌→黃、淨負債且燒錢→紅。"""
    assert debt_flag(_runway(cash=100.0, debt=50.0))["colour"] == "green"
    assert debt_flag(_runway(cash=50.0, debt=100.0, fcf=10.0))["colour"] == "amber"
    assert debt_flag(_runway(cash=50.0, debt=100.0, fcf=-10.0))["colour"] == "red"
    assert debt_flag(_runway(cash=100.0, debt=100.0))["colour"] == "green"   # 相等＝還得出來


def test_debt_lamp_refuses_rather_than_guessing_when_an_input_is_missing() -> None:
    """缺一個輸入就不判——回一個看起來合理的顏色比不判危險得多（INV-6 fail closed）。"""
    assert debt_flag({"cash_and_equivalents": 100.0})["colour"] is None
    assert debt_flag(_runway(cash=50.0, debt=100.0, fcf=None))["colour"] is None


# ---------------------------------------------------------------------------
# 4. 稀釋：窗不滿一個完整會計年度就不判色
# ---------------------------------------------------------------------------

def test_dilution_never_turns_green_on_a_short_window() -> None:
    """**沒看到增發不等於沒有增發。** 窗不滿一年時「沒增加」也不得判綠。"""
    flag = dilution_flag(_series(FULL_YEAR_DAYS - 1, change=0.0), _runway(), today=TODAY)
    assert flag["colour"] is None
    assert flag["absence_kind"] == "insufficient_evidence"
    assert flag["inputs"]["colour_available_on"] > TODAY        # 有到期的等待（INV-2）


def test_dilution_colours_only_after_a_full_year_and_does_not_split_by_cash_burn() -> None:
    """滿一年才判色；而且**不拿燒錢與否把黃切成紅**——那需要分辨員工股酬與真增發，
    而那是量級問題，今天沒有非憑空的門檻可用（首版就是這樣被真實資料推翻的）。"""
    burning = _runway(fcf=-10.0)
    assert dilution_flag(_series(FULL_YEAR_DAYS, change=0.0), burning, today=TODAY)["colour"] == "green"
    assert dilution_flag(_series(FULL_YEAR_DAYS, change=0.15), burning, today=TODAY)["colour"] == "amber"
    # 燒不燒錢都一樣是黃：顏色不因現金流符號而改變。
    assert dilution_flag(_series(FULL_YEAR_DAYS, change=0.15), _runway(fcf=10.0),
                         today=TODAY)["colour"] == "amber"


def test_dilution_keeps_the_observed_change_in_inputs_even_when_it_refuses_to_colour() -> None:
    """不判色**不等於丟掉觀測**：窗內看到的變化照樣進稽核層，只是不拿它上色（INV-3）。"""
    flag = dilution_flag(_series(60, change=0.153), _runway(), today=TODAY)
    assert flag["colour"] is None
    assert flag["inputs"]["change"] == pytest.approx(0.153)
    assert flag["inputs"]["span_days"] == 60
    # 觀測窗與「這條序列還活著嗎」分開印：ETL 停掉時空白不得混進窗長（L12）。
    assert flag["inputs"]["days_since_last"] == 0


def test_going_concern_refuses_to_read_a_colour_out_of_free_text() -> None:
    """逐字的審計意見是 judgment 欄位；機械比對不得從自由文字推顏色（L15-2）。

    ⚠ 有逐字紀錄時**理由句要變**（它不是「沒有資料」，是「沒有能判色的欄位」），
    但顏色仍然不亮——否則就是讓一個字串比對決定一個 claim。
    """
    without = going_concern_flag(None)
    withtext = going_concern_flag({"value": "KPMG：material uncertainty related to going concern"})
    assert without["colour"] is None and withtext["colour"] is None
    assert without["absence_kind"] == withtext["absence_kind"] == "capability_absent"
    assert without["reason"] != withtext["reason"]


# ---------------------------------------------------------------------------
# 5. 燈是量測不是訊號
# ---------------------------------------------------------------------------

def test_flags_do_not_participate_in_ranking_or_filtering() -> None:
    """排序權威與籃子 filter **都不得**讀到歸零旗標——它一旦能擋掉候選就變回訊號（INV-5）。"""
    ranking = (ROOT / "query" / "bottleneck.py").read_text(encoding="utf-8")
    assert "wipeout" not in ranking, "排序權威讀到了歸零旗標——燈不得參與排序"
    basket = (ROOT / "webapp" / "basket.py").read_text(encoding="utf-8")
    row_fn = basket.split("def build_basket_row", 1)[1].split("def ", 1)[0]
    # 列上可以**帶著**燈（呈現），但不得把它塞進 filter_reasons（判定去留）。
    reasons_block = row_fn.split("reasons: list[str] = []", 1)[1].split("return {", 1)[0]
    assert "wipeout" not in reasons_block, "歸零旗標進了 filter_reasons——量測不得決定去留"


def test_lamp_count_and_company_count_are_not_collapsed_into_one_number() -> None:
    """「一檔亮四盞」與「四檔各亮一盞」是兩件事，籃子帳必須分開算。"""
    basket = (ROOT / "webapp" / "basket.py").read_text(encoding="utf-8")
    assert '"lamps"' in basket and '"companies"' in basket and '"red_tickers"' in basket


# ---------------------------------------------------------------------------
# 6. 交付一項能力就要把它從心跳的「還沒建」清單拿掉
# ---------------------------------------------------------------------------

def test_heartbeat_does_not_claim_a_delivered_capability_is_still_missing() -> None:
    """事發 2026-09-18：D15 當天 09:31 交付，而心跳仍把它宣告成「還沒建」。

    **不會有任何東西變紅**——它只是每天安靜印一句假話（L17：不會壞、不會報錯的那一類）。
    所以這裡反過來驗：第 4 段不得再出現 `capability_absent`，而且那兩項真的有被印出來。
    """
    source = (ROOT / "crons" / "heartbeat.py").read_text(encoding="utf-8")
    positions = source.split("def build_positions(", 1)[1].split("\ndef ", 1)[0]
    # 找的是**機制**（真的去建一個 capability_absent），不是散文裡提到這個詞——
    # 否則這條測試會被自己的註解絆倒，而那種測試下次會被人用刪註解的方式「修好」。
    assert 'Absence("capability_absent"' not in positions, (
        "第 4 段還在宣告某個能力『還沒建』——D15 與 D2 都已交付，那一行每天都在說假話")
    # 而且它們真的有被印出來（不是刪掉了事）。
    assert "power-law：籃子總報酬" in positions
    assert "alpha 全歸零淨值少" in positions
    assert "歸零旗標 " in positions
    # 那張沒有 consumer 的集中表已經移除（INV-4：producer 指得出 consumer）。
    assert "PENDING_PHASE: Mapping" not in source


def test_every_lane_is_reported_even_when_it_cannot_be_coloured() -> None:
    """四盞燈**每盞都回值**——少一盞與「那盞是綠的」不得同形（INV-3：沒有 silent drop）。"""
    flags = wipeout_flags(runway=_runway(), shares_series=_series(30), going_concern=None, today=TODAY)
    assert tuple(flags) == WIPEOUT_LANES
    counts = tally(flags)
    assert sum(counts.values()) == len(WIPEOUT_LANES)


def test_lamp_reasons_do_not_leak_company_numbers() -> None:
    """D2：**紅黃綠不給數字**。理由句不得帶該公司的數值——數字住 `inputs`（稽核層）。"""
    flags = wipeout_flags(runway=_runway(cash=41_596_000.0, debt=53_939_000.0, fcf=-1_265_250.0),
                          shares_series=_series(44, change=0.0004), going_concern=None, today=TODAY)
    for lane, flag in flags.items():
        assert not re.search(r"\d", str(flag["reason"])), f"{lane} 的理由句帶了數字：{flag['reason']}"
        assert flag["inputs"] is not None
