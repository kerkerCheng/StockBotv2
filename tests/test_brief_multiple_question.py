"""首屏多一句「要翻倍需要什麼為真」（2026-09-20，Phase 7 選項 a）。

## 為什麼是**另外一句**，不是換掉那把尺

Phase 7 原本的驗收行寫「首屏的『賭對了值多少』**由多年視角回答**」。落地時比對形狀
才發現換不掉：**那把尺要的是四個價格**（COHR：317.36／223.60／243.97／197.54），
**而多年橋產生的是「要 2 倍，資料中心分部營收得成長 465%」**——不是價格。

⚠ 但原本要修的錯位是真的，而且比那句話更精確：**錯的不是數字，是結論的期間**。
系統算出 payoff −23.1%（**FY2027**），研究者據此在首屏寫「所以今天不是加碼點」，
而同一份 thesis 講的是 **FY2030** 的六吋產能倍增。

兩句並存、各答各的——與 Step 7.1 當初分開 `market_implied_eps`（市場在想什麼）與
`required_eps`（要漲 N 倍需要什麼）是同一個理由（L12）。
"""
from __future__ import annotations

from datetime import date

from briefing.alpha_view.builder import _multiple_question, _multiple_sentence


class _Sol:
    def __init__(self, driver, scope, implied_value, status="solved"):
        self.driver, self.scope, self.implied_value, self.status = driver, scope, implied_value, status


class _Step:
    def __init__(self, multiple, solutions, unreachable=(), status="partial"):
        self.target_return_multiple, self.solutions, self.status = multiple, solutions, status
        self.unreachable_drivers = tuple(unreachable)


class _View:
    def __init__(self, *, status="available", horizon=date(2030, 6, 30), span_years=4,
                 ladder=(), reason=None, basis="forward_earnings_multiple"):
        self.status, self.horizon, self.span_years = status, horizon, span_years
        self.ladder, self.reason, self.basis = ladder, reason, basis
        self.metric_label = "營收" if basis == "ev_to_sales" else "EPS"


REF = date(2026, 9, 20)


def test_no_horizon_means_the_line_is_not_printed_at_all() -> None:
    """**沒寫倍率射程就不印那一句**——不是印「還沒寫」。

    71/73 檔都沒寫，逐檔印是噪音。全體缺口由心跳段 4 的常駐計數器負責
    （「還沒寫下目標年度 N」）：**首屏印這一檔的事，心跳印全體的帳。**
    """
    assert _multiple_question(None, reference_day=REF) is None
    assert _multiple_question(_View(status="no_horizon", horizon=None), reference_day=REF) is None
    assert _multiple_question(_View(status="no_judgment", horizon=None), reference_day=REF) is None


def test_method_not_applicable_is_an_absence_with_a_declared_kind() -> None:
    """「已經算過、知道答案沒有意義」≠「還沒做」——`absence_kind` 由產生它的程式宣告（L16）。"""
    datum = _multiple_question(
        _View(status="method_not_applicable", reason="錨點 EPS 是 -0.0789（≤ 0）"),
        reference_day=REF)
    assert datum is not None
    assert datum.status == "missing"
    assert datum.absence_kind == "method_not_applicable"
    assert datum.value is None, "缺席不得帶值——缺席與 0 不得同形（型別層也擋）"


def test_the_sentence_says_percent_and_multiple_not_the_misleading_phrase() -> None:
    """⚠ **措辭精度本身就是一個 claim**（L11-1）。

    橋的公式是 `base × (1 + growth)`，所以 `revenue_growth = 4.651` 的語意是
    **成長 465%、變成 5.65 倍**。寫成「成長 4.65 倍」會被讀成「變成 4.65 倍」——
    差了整整一倍的量級。2026-09-20 發現 ROADMAP 與啟動 prompt 多處就是那個寫法。
    """
    view = _View(ladder=(
        _Step(2.0, [_Sol("revenue_growth", "Datacenter & Communications", 4.651)]),
        _Step(3.0, [], unreachable=[_Sol("revenue_growth", "total", None, "no_sign_change")]),
    ))
    sentence = _multiple_sentence(view)
    assert "465%" in sentence, "要說出成長率"
    assert "5.65 倍" in sentence, "要說出「變成幾倍」，因為那才是人腦裡的單位"
    assert "成長 4.65 倍" not in sentence, "這個寫法會被讀成「變成 4.65 倍」，差一倍量級"
    assert "3 倍" in sentence and "做不到" in sentence, "做不到的那幾級也要說"
    assert "不是預測" in sentence, "它是可行性不是預測——這句話不能省"


def test_a_margin_driver_is_phrased_in_percentage_points() -> None:
    """營益率是**變化量**，單位是百分點，不是倍數。"""
    view = _View(ladder=(_Step(2.0, [_Sol("operating_margin_delta", "mix_and_utilization", 0.085)]),))
    assert "8.5 個百分點" in _multiple_sentence(view)


def test_the_builder_does_not_fetch_it_itself() -> None:
    """**builder 是組裝器不是取料器。**

    第一版寫成讓 builder 自己 `build_multi_year_view(ticker)`，於是它開始讀檔案系統
    並跑金融模型——守門測試當場抓到（一個本來不碰真實資料的 fixture 算出了 COHR 的
    FY2030）。取料住 `sources.py`，與 `payoff`／`downside`／`fundamental_model` 一致。
    """
    import inspect
    import pathlib as _pl

    from briefing.alpha_view import builder

    # ① 本質斷言：它吃的是**已經算好的 view**，不是 ticker。
    #    哪天有人改回自己取料，第一個參數會變回 ticker，這條就會紅。
    params = list(inspect.signature(builder._multiple_question).parameters)
    assert params[0] == "view", f"第一個參數應該是已算好的 view，收到 {params[0]!r}"
    assert "ticker" not in params, "吃 ticker 就代表它要自己去查——那是取料不是組裝"

    # ② 取料住在 sources.py（materialize 路徑），不在 builder。
    src = _pl.Path("briefing/alpha_view/sources.py").read_text(encoding="utf-8")
    assert "build_multi_year_view" in src, "取料應該住在 sources.py"


def test_the_ladder_is_copied_whole_including_the_unreachable_levels() -> None:
    """INV-3：解不出來的那幾級**照抄**，不挑掉。問「五倍要什麼為真」時，
    「拉到極限也做不到」才是答案。"""
    view = _View(ladder=(
        _Step(2.0, [_Sol("revenue_growth", "total", 1.0)]),
        _Step(10.0, [], unreachable=[_Sol("revenue_growth", "total", None, "no_sign_change")]),
    ))
    datum = _multiple_question(view, reference_day=REF)
    assert datum is not None and datum.status == "available"
    assert len(datum.value["steps"]) == 2, "每一級都要在，包括做不到的"
    assert datum.value["sentence"], "首屏印的是句子"
