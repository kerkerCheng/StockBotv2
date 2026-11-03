"""買得到嗎（盲點修法第 19 條，2026-11-03；`identity.execution_access`、`config/execution_access.json`）。

使用者 2026-11-02「我基本上是台股+IB，IB有就有」、2026-11-03「IB這些都可以下」。一個市場一條規則、個別代號可例外；
買不到的不進 paper lane（追蹤表那一半測在 `tests/test_measurement_lanes.py`）。
"""
from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from identity.execution_access import (CONFIG_PATH, ExecutionAccessError, access, load, market_of, validate)

ROOT = Path(__file__).resolve().parents[1]
DAY = date(2026, 11, 3)


def _registry_markets() -> dict[str, list[str]]:
    companies = json.loads((ROOT / "config" / "company_identity.json").read_text(encoding="utf-8"))["companies"]
    out: dict[str, list[str]] = {}
    for company in companies:
        ticker = company.get("research_ticker")
        if ticker:
            out.setdefault(market_of(ticker), []).append(ticker)
    return out


def test_every_market_in_the_registry_has_a_rule() -> None:
    """剎車：名冊出現表上沒有的市場就紅——先問使用者買不買得到，再在 config 加一格（不得為了變綠自己填「IB」）。

    變異：從 config 拿掉 VI → 這條紅（ATS.VI）。"""
    rules = load()["markets"]
    missing = {market: tickers for market, tickers in _registry_markets().items() if market not in rules}
    assert not missing, f"名冊裡這些市場沒登記買不買得到——問使用者後補進 config/execution_access.json：{missing}"


def test_market_of_reads_the_exchange_suffix_and_us_has_none() -> None:
    assert market_of("688836.SS") == "SS" and market_of("3081.two") == "TWO" and market_of("HEXA-B.ST") == "ST"
    assert market_of("AXTI") == "US" and market_of("") == "US"


def test_shipped_config_marks_the_two_a_shares_off_the_connect_list() -> None:
    """11-03 對 HKEX 合資格名單：名冊 26 檔 A 股 24 在、2 不在。其餘照市場規則。"""
    data = load()
    unitree = access("688836.SS", today=DAY, data=data)
    assert unitree.buyable is False and "滬股通" in unitree.why and unitree.channel == "IB（滬股通）"
    assert access("688818.ss", today=DAY, data=data).buyable is False                 # 查的時候轉大寫
    assert access("688498.SS", today=DAY, data=data).buyable is True
    assert (access("AXTI", today=DAY, data=data).channel, access("3081.TWO", today=DAY, data=data).channel) == (
        "IB", "台灣券商")
    assert access("XYZ.ZZ", today=DAY, data=data).buyable is None                      # 不在表上＝不知道，不猜


def test_an_exception_lapses_after_its_recheck_day_and_says_so() -> None:
    """重查日當天仍有效；過了就照市場規則算回來、`exception_expired` 讓呼叫端印出來（重問，不是丟）。

    變異：過期照樣回 False → 第二條紅；不標過期 → 第三條紅。"""
    data = load()
    assert access("688836.SS", today=date(2026, 12, 21), data=data).buyable is False
    later = access("688836.SS", today=date(2026, 12, 22), data=data)
    assert later.buyable is True and later.why is None
    assert later.exception_expired is True and access("688498.SS", today=date(2026, 12, 22), data=data).exception_expired is False


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["exceptions"]["688836.SS"].pop("recheck_by"), "欄位必須恰好是"),
    (lambda d: d["exceptions"]["688836.SS"].update(recheck_by="2026-11-03"), "recheck_by 必須晚於 checked"),
    (lambda d: d["exceptions"]["688836.SS"].update(checked="11/03"), "不是 YYYY-MM-DD"),
    (lambda d: d["exceptions"]["688836.SS"].update(buyable="no"), "buyable 必須是 true／false"),
    (lambda d: d["exceptions"]["688836.SS"].update(why=" "), "why、source 不得空白"),
    (lambda d: d["exceptions"].update({"688000.ss": d["exceptions"]["688818.SS"]}), "代號要大寫"),
    (lambda d: d["exceptions"].update({"1234.ZZ": d["exceptions"]["688818.SS"]}), "不在 markets"),
    (lambda d: d["markets"]["VI"].update(extra="x"), "欄位必須恰好是"),
    (lambda d: d["markets"]["VI"].update(channel=""), "不得空白"),
    (lambda d: d.update(markets={}), "非空"),
])
def test_validate_rejects_shapes_that_would_silently_misread(mutate, message) -> None:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate(copy.deepcopy(data))                         # 出貨的那份要過
    broken = copy.deepcopy(data)
    mutate(broken)
    with pytest.raises(ExecutionAccessError, match=message):
        validate(broken)
