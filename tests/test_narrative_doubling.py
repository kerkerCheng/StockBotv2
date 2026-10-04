"""Phase 7 Step 7.0c：敘事「要翻倍需要什麼」、翻倍的起點兩個 placeholder、重押讀圖時格層引用跟著換。

使用者 2026-10-04 定案（plan §0.1 Q6／A1）：五題的第②題「押對了夠大嗎」住在 `what_must_be_true` 那一格——
要翻倍，營業數字要到多少、在什麼時候；**不寫目標價**（G3）。起點由 authority 填（市值、近四季營收），條件由人寫。
「已定價」白話的測試在 `tests/test_webapp_api.py`（它走 `.meta.json` → API）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import BRIEF_FRAME_V2, PLACEHOLDERS_V2, WHAT_MUST_BE_TRUE_FORBIDDEN
from briefing.alpha_view.builder import _dated_money
from briefing.alpha_view.contracts import Datum
from tests.test_alpha_investment_view import _view
from tests.test_narrative_v2 import READ, _ctx, _record, _slots, _write

OLD = "sr_" + "0" * 16          # 同一節點、同一單位、已被 READ 取代的讀圖
SOCKET = "sr_" + "5" * 16       # 同一節點、另一個單位（插槽）的現行讀圖


# ---------------------------------------------------------------------------
# 範本與字彙
# ---------------------------------------------------------------------------

def test_what_must_be_true_asks_what_doubling_takes_and_still_refuses_a_price() -> None:
    frame = BRIEF_FRAME_V2["what_must_be_true"]
    assert "要翻倍需要什麼" in frame["question"]
    assert "{market_cap}" in frame["do_not"] and "不寫目標價" in frame["do_not"]
    assert "倍數回到三年中位數" in frame["do_not"]          # 那一步會把贏家說服走（proposal §13）
    assert {"market_cap", "revenue_ttm"} <= set(PLACEHOLDERS_V2)
    assert WHAT_MUST_BE_TRUE_FORBIDDEN == {"price", "own_history_pctile", "cohort_median"}   # 型別層的禁令不動
    ok = _slots(wmbt="要翻倍：市值 {market_cap} 的兩倍，營收要從 {revenue_ttm} 做到兩倍、在 2028 年前；錯的訊號是擴產提前。")
    assert parse_brief_record(_record(slots=ok)).slot("what_must_be_true") is not None
    for token in ("{price}", "{own_history_pctile}", "{cohort_median}"):
        with pytest.raises(ContractViolation, match="不得有價格"):
            _record(slots=_slots(wmbt=f"要翻倍：{token} 要到兩倍。"))


# ---------------------------------------------------------------------------
# 起點的值：只選取既有 Datum，報價單位換成結算幣別，沒有幣別就不給值
# ---------------------------------------------------------------------------

def _cap(view):
    items = {d.key: d for d in view.fundamentals.items}
    return items["market_cap"], items["market_cap_settlement"]


def test_sources_look_up_the_quote_unit_conversion_from_the_registry_vocabulary() -> None:
    """換算係數由 sources 從 `identity.currency` 查（builder 是純函式，不碰 identity）；未登記就是 None，不猜。"""
    from types import SimpleNamespace

    from briefing.alpha_view.sources import identity_mapping

    lse = identity_mapping(SimpleNamespace(market_currency="GBP", market_quote_unit="GBp"))
    assert lse["settlement_currency"] == "GBP" and lse["quote_to_settlement_factor"] == pytest.approx(0.01)
    usd = identity_mapping(SimpleNamespace(market_currency="USD", market_quote_unit="USD"))
    assert usd["settlement_currency"] == "USD" and usd["quote_to_settlement_factor"] == 1.0
    unknown = identity_mapping(SimpleNamespace(market_currency="GBP", market_quote_unit="Xq"))
    assert unknown["settlement_currency"] is None and unknown["quote_to_settlement_factor"] is None


def test_market_cap_is_converted_from_the_quote_unit_to_the_settlement_currency_without_fx() -> None:
    raw, cap = _cap(_view(identity={"market_currency": "GBP", "market_quote_unit": "GBp", "execution_venue": "LSE",
                                    "settlement_currency": "GBP", "quote_to_settlement_factor": 0.01}))
    assert cap.value == pytest.approx(raw.value / 100) and cap.unit == "GBP"       # GBp 是 minor unit，差 100 倍
    raw, cap = _cap(_view())
    assert cap.value == pytest.approx(raw.value) and cap.unit == "USD"


def test_an_unregistered_quote_unit_fails_closed_instead_of_guessing() -> None:
    _raw, cap = _cap(_view(identity={"market_currency": "GBP", "market_quote_unit": "Xq",
                                     "settlement_currency": None, "quote_to_settlement_factor": None}))
    assert cap.value is None and cap.status == "missing" and "未登記" in (cap.reason or "")


def test_a_starting_point_prints_amount_currency_and_date_or_nothing() -> None:
    d = Datum(key="x", label="x", value=3.76e9, status="available", basis="observation", as_of=date(2026, 10, 2))
    assert _dated_money(d, "USD") == "37.6 億 USD（2026-10-02）"
    assert _dated_money(d, "SEK", basis="近四季，快照") == "37.6 億 SEK（近四季，快照 2026-10-02）"
    assert _dated_money(d, None) is None              # 沒有幣別的金額會差 100 倍——寧可印（尚無）
    assert _dated_money(None, "USD") is None


def test_the_brief_fills_the_starting_points_and_old_records_are_untouched() -> None:
    def brief(wmbt: str):
        slots = _slots(wmbt=wmbt)
        rec = brief_record(company_id="co:coherent", ticker="COHR", slots=slots, record_version=RECORD_VERSION_V2,
                           rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=[],
                           answers={"priced_in": "yes", "in_numbers": "yes"},
                           candidate_state={"state": "pass", "watch_id": None, "reason": "非邊緣"},
                           created_at=datetime(2026, 9, 1, tzinfo=timezone.utc))
        return parse_brief_record(rec)

    view = _view(brief_records=[brief("要翻倍：市值 {market_cap}；營收 {revenue_ttm} 要做到兩倍。")])
    wmbt = next(d for d in view.investor_brief.slots if d.key == "brief:what_must_be_true")
    assert "億 USD（2026-09-04）" in wmbt.value              # 市值有值（夾具的快照日）
    assert "營收 （尚無）" in wmbt.value                      # 夾具沒有財報幣別 → 不給值，不猜
    plain = brief("擴產沒提前。")
    old = _view(brief_records=[plain])
    assert next(d for d in old.investor_brief.slots if d.key == "brief:what_must_be_true").value == "擴產沒提前。"


# ---------------------------------------------------------------------------
# 重押讀圖時格層引用跟著換（Phase 6 待決 #16）
# ---------------------------------------------------------------------------

def _ctx_with_history():
    ctx = _ctx()
    for rid, unit in ((READ, "layer"), (OLD, "layer"), (SOCKET, "socket")):
        reading = ctx.readings_by_id.get(rid) or type(ctx.readings_by_id[READ])(angles=ctx.readings_by_id[READ].angles)
        reading.node, reading.unit = "tech:x", unit
        ctx.readings_by_id[rid] = reading
    return ctx


def test_a_rewrite_that_rides_the_new_reading_must_not_cite_the_superseded_one(tmp_path: Path) -> None:
    slots = _slots()
    slots["bottleneck"]["evidence_refs"] = [OLD, "graph://x"]
    slots["our_bet"]["evidence_refs"] = [OLD]
    with pytest.raises(ContractViolation) as exc:
        _write(tmp_path, _record(slots=slots), _ctx_with_history())
    message = str(exc.value)
    assert "bottleneck" in message and "our_bet" in message and "已被取代的讀圖" in message
    assert f"這版押的是 {READ}" in message and "不自動改寫" in message
    assert not (tmp_path / "briefs").exists()


def test_citing_the_current_reading_or_another_units_reading_is_fine(tmp_path: Path) -> None:
    slots = _slots()
    slots["bottleneck"]["evidence_refs"] = [READ]
    slots["position"]["evidence_refs"] = [SOCKET, "graph://x"]     # 插槽讀圖不是這一格押的層讀圖的舊版
    out = _write(tmp_path, _record(slots=slots), _ctx_with_history())
    assert out["brief_id"].startswith("ib_")
