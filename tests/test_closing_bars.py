"""排除未收盤的 K 棒（Phase 6 Step 6.7c；plan 2026-10-02-002 §8 c，Phase 5 #12）。

事發：在台北白天互動跑追蹤表，歐股與台股取到盤中尚未收盤的當日 K 棒（yfinance 回進行中的值）；
`fetch_close_series` 原本只丟「日期＝台北今天」那根，美股盤中（台北凌晨）的當日 K 棒日期是美東昨天，照樣混進來。
守四件事：
1. 唯一 owner `alpha.providers.close_series.bar_state`／`closed_points`：日期＝**交易所當地**今天、且現在早於
   `currentTradingPeriod.regular.end` → 拿掉；收盤後 → 保留；拿不到交易時段 → 保留並計數「收盤狀態未知」（不靜默丟）。
2. NaN 先跳過（既有規則），再判最後一根。
3. 追蹤表三支取價、計分表、`fetch_close_series` 都走它，逐檔記狀態。
4. 計數跟著輸出走：`price_budget.closing_bars`（追蹤表 collect、計分表、APP），報告那一行兩邊共用同一句。
"""
from __future__ import annotations

import sys
import types
from datetime import date, datetime, time, timedelta, timezone

import pytest

from alpha.providers import close_series as cs
from alpha.providers.close_series import (
    BAR_STATE_LABELS, bar_state, closed_points, closing_bars_line, summarize_bar_states,
)
from tests.test_account_scorecard import scorecard_env  # noqa: F401 — pytest 依名字找 fixture

TPE = timezone(timedelta(hours=8))
ET = timezone(timedelta(hours=-4))


def _ts(day: date, tz) -> datetime:
    return datetime.combine(day, time(0, 0), tz)


def _period(day: date, tz, start_hm=(9, 0), end_hm=(13, 30)) -> dict:
    start = datetime.combine(day, time(*start_hm), tz).timestamp()
    end = datetime.combine(day, time(*end_hm), tz).timestamp()
    return {"currentTradingPeriod": {"regular": {"start": int(start), "end": int(end)}}}


MON = date(2026, 10, 5)


# ---------------------------------------------------------------------------
# 1｜owner 的規則
# ---------------------------------------------------------------------------

def test_during_the_session_the_last_bar_is_unfinished() -> None:
    now = datetime.combine(MON, time(10, 30), TPE)                     # 台股盤中
    assert bar_state(_ts(MON, TPE), _period(MON, TPE), now=now) == "dropped_unfinished"


def test_after_the_close_the_last_bar_stays() -> None:
    now = datetime.combine(MON, time(14, 0), TPE)
    assert bar_state(_ts(MON, TPE), _period(MON, TPE), now=now) == "closed"


def test_today_is_the_exchange_local_today_not_taipeis() -> None:
    """美股盤中＝台北凌晨：當日 K 棒的日期是美東「今天」、台北「昨天」——舊規則（比台北今天）會讓它混進來。"""
    now = datetime(2026, 10, 3, 1, 0, tzinfo=TPE)                      # 美東 10-02 13:00，盤中
    us_bar = _ts(date(2026, 10, 2), ET)
    assert bar_state(us_bar, _period(date(2026, 10, 2), ET, (9, 30), (16, 0)), now=now) == "dropped_unfinished"
    # 同一刻，台股最後一根（10-02）不是台北今天 → 那個交易日已經過去
    assert bar_state(_ts(date(2026, 10, 2), TPE), _period(date(2026, 10, 2), TPE), now=now) == "closed"


def test_the_live_observation_after_the_us_close_keeps_fridays_bar() -> None:
    """2026-10-03 03:51 UTC 實測（美東週五 23:51）：AAPL 的交易時段仍是週五 13:30–20:00 UTC，沒有提早滾到週一。"""
    now = datetime(2026, 10, 3, 3, 51, tzinfo=timezone.utc)
    metadata = {"currentTradingPeriod": {"regular": {
        "start": int(datetime(2026, 10, 2, 13, 30, tzinfo=timezone.utc).timestamp()),
        "end": int(datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp())}}}
    assert bar_state(_ts(date(2026, 10, 2), ET), metadata, now=now) == "closed"


def test_without_a_trading_period_the_bar_is_kept_and_called_unknown() -> None:
    now = datetime.combine(MON, time(10, 30), TPE)
    assert bar_state(_ts(MON, TPE), None, now=now) == "close_unknown"
    assert bar_state(_ts(MON, TPE), {"currentTradingPeriod": {}}, now=now) == "close_unknown"


def test_a_period_rolled_forward_means_today_closed_and_an_older_one_is_unknown() -> None:
    now = datetime.combine(MON, time(20, 0), TPE)
    assert bar_state(_ts(MON, TPE), _period(MON + timedelta(days=1), TPE), now=now) == "closed"
    assert bar_state(_ts(MON, TPE), _period(MON - timedelta(days=3), TPE), now=now) == "close_unknown"


def test_a_stamp_without_a_timezone_cannot_say_whose_today_it_is() -> None:
    now = datetime.combine(MON, time(10, 30), TPE)
    assert bar_state(datetime(2026, 10, 5), _period(MON, TPE), now=now) == "close_unknown"


def test_nan_is_skipped_before_the_last_bar_is_judged() -> None:
    """歐股盤中常回一根 NaN 的當日 K 棒：先跳過它（既有規則），剩下的最後一根是昨天、已收盤。"""
    now = datetime.combine(MON, time(10, 30), TPE)
    points = [(_ts(MON - timedelta(days=3), TPE), 10.0), (_ts(MON, TPE), float("nan"))]
    kept, state = closed_points(points, _period(MON, TPE), now=now)
    assert [p[1] for p in kept] == [10.0] and state == "closed"


def test_an_unfinished_bar_is_removed_and_an_empty_series_has_no_state() -> None:
    now = datetime.combine(MON, time(10, 30), TPE)
    points = [(_ts(MON - timedelta(days=3), TPE), 10.0), (_ts(MON, TPE), 11.0)]
    kept, state = closed_points(points, _period(MON, TPE), now=now)
    assert [p[1] for p in kept] == [10.0] and state == "dropped_unfinished"
    assert closed_points([], None, now=now) == ([], None)


def test_the_summary_names_the_symbols_and_one_sentence_serves_both_reports() -> None:
    summary = summarize_bar_states({"2330.TW": "dropped_unfinished", "SIVE.ST": "close_unknown", "AAPL": "closed",
                                    "NONE": None})
    assert summary["checked"] == 3 and summary["dropped_unfinished"] == ["2330.TW"]
    assert summary["close_unknown"] == ["SIVE.ST"] and summary["labels"] == dict(BAR_STATE_LABELS)
    line = closing_bars_line(summary)
    assert "拿掉 1 檔（2330.TW）" in line and "收盤狀態未知 1 檔（SIVE.ST" in line
    assert closing_bars_line(summarize_bar_states({"AAPL": "closed"})) is None
    assert closing_bars_line(None) is None


# ---------------------------------------------------------------------------
# 2｜每個取價點都走同一個 owner（假的 yfinance；時間相對於真的現在）
# ---------------------------------------------------------------------------

class _Column:
    def __init__(self, points):
        self._points = points

    def items(self):
        return iter(self._points)

    def dropna(self):
        return self


class _Frame:
    empty = False

    def __init__(self, points):
        self._points = points

    def __contains__(self, key):
        return key == "Close"

    def __getitem__(self, key):
        return _Column(self._points)


def _fake_yfinance(monkeypatch, *, unfinished: bool):
    """每一檔都是「三天前收盤 10、今天（交易所當地）11」；`unfinished` 決定交易時段的結束是一小時後還是一分鐘前。"""
    now = datetime.now(TPE)
    today = now.date()
    points = [(_ts(today - timedelta(days=3), TPE), 10.0), (_ts(today, TPE), 11.0)]
    start = int(datetime.combine(today, time(0, 0, 1), TPE).timestamp())
    end = int(now.timestamp()) + (3600 if unfinished else -60)
    metadata = {"currency": "TWD", "currentTradingPeriod": {"regular": {"start": start, "end": max(end, start + 1)}}}
    handle = types.SimpleNamespace(history=lambda **kw: _Frame(points), history_metadata=metadata)
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=lambda symbol: handle))
    return today


def _oist():
    from tests.test_measurement_lanes import OIST

    return OIST


@pytest.mark.parametrize("unfinished", [True, False])
def test_every_fetcher_drops_only_an_unfinished_bar_and_records_the_state(monkeypatch, unfinished) -> None:
    import engine_b.account_scorecard as sc

    today = _fake_yfinance(monkeypatch, unfinished=unfinished)
    oist = _oist()
    expect_state = "dropped_unfinished" if unfinished else "closed"
    expect_days = {today - timedelta(days=3)} | (set() if unfinished else {today})
    start = today - timedelta(days=30)

    states: dict = {}
    assert set(oist._provider_series("A", start, states=states)) == expect_days
    series, unit = oist._provider_close_series("B", start, states=states)
    assert set(series) == expect_days and unit == "TWD"
    assert set(oist._benchmark_series(["C"], start, today, states=states)["C"]) == expect_days
    assert set(sc._yfinance_closes(["D"], start, today, states=states)["D"]) == expect_days
    rows = cs.fetch_close_series(["E"], sessions=10, states=states)["E"]
    assert {date.fromisoformat(r["session_date"]) for r in rows} == expect_days
    assert states == {s: expect_state for s in "ABCDE"}


# ---------------------------------------------------------------------------
# 3｜計數跟著輸出走：追蹤表 collect／render、計分表 build／render、APP
# ---------------------------------------------------------------------------

def test_the_tracker_counts_what_its_default_fetchers_dropped(tmp_path, monkeypatch) -> None:
    import engine_b.event_watch as ew
    import tests.test_measurement_lanes as ML

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    oist = ML.OIST

    def fake_close(symbol, start, *, states=None):
        states[symbol] = "dropped_unfinished" if symbol == "AAA" else "closed"
        return ML._loader(symbol, start)

    def fake_bench(symbols, start, end, *, states=None):
        states.update({s: ("close_unknown" if s == "QQQ" else "closed") for s in symbols})
        return {s: ML.BENCH[s] for s in symbols}

    monkeypatch.setattr(oist, "_provider_close_series", fake_close)
    monkeypatch.setattr(oist, "_benchmark_series", fake_bench)
    collected = ML._collect(tmp_path, price_loader=None, benchmark_loader=None)
    bars = collected["price_budget"]["closing_bars"]
    assert bars["dropped_unfinished"] == ["AAA"] and bars["close_unknown"] == ["QQQ"] and bars["checked"] >= 3
    text = "\n".join(oist.render_lanes(collected))
    assert "未收盤 K 棒：拿掉 1 檔（AAA）" in text and "收盤狀態未知 1 檔（QQQ" in text
    # 注入的 loader 不記：計數是空的、那一行不印（daily 05:30 各市場都已收盤時也是這個樣子）
    plain = ML._collect(tmp_path)
    assert plain["price_budget"]["closing_bars"]["checked"] == 0
    assert "未收盤 K 棒" not in "\n".join(oist.render_lanes(plain))


def test_the_scorecard_counts_what_its_default_fetcher_dropped(scorecard_env, monkeypatch) -> None:  # noqa: F811
    import engine_b.account_scorecard as sc

    def fake_closes(symbols, start, end, *, states=None):
        states.update({s: ("dropped_unfinished" if s == "AAA" else "closed") for s in symbols})
        return scorecard_env["loader"](symbols, start, end)

    monkeypatch.setattr(sc, "_yfinance_closes", fake_closes)
    card = sc.build_scorecard(leads_path=scorecard_env["leads"], today=date(2026, 10, 31))
    assert card["price_budget"]["closing_bars"]["dropped_unfinished"] == ["AAA"]
    assert "未收盤 K 棒：拿掉 1 檔（AAA）" in sc.render(card)


def test_the_app_prints_the_count_on_both_pages_only_when_something_happened() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    body = source.split("function closingBarsNote(budget)", 1)[1].split("\n}\n", 1)[0]
    assert "if (!dropped.length && !unknown.length) return null;" in body
    assert "bars.labels" in body                                          # 字彙跟著 artifact，前端不另存
    assert source.count("closingBarsNote(budget)") == 3                   # 定義一次、部位頁與計分表頁各一次
