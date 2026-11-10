"""研究讀燈的價格遮罩（failure log #152；ROADMAP「研究讀燈與讀敘事全文的出口遮價格欄」）。

驗：三題稽核區、research packet、敘事紀錄三個研究出口，預設不印價格（已定價的值與 detail、市值、目標價、本益比、
priced_at_write）；遮掉與缺席不同形（L12）；缺席與理由照印；加 --prices 拿原樣。重放 11-10 那一輪被點名的形狀：
3163.TWO 的「−32.9%」、2455.TW 的 priced_at_write、IQE.L 個股頁的市值。
"""
from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import pytest

from alpha.price_mask import (MASKED, PRICES_HINT, PRICES_SHOWN, mask_brief_record, mask_packet,
                              mask_three_questions)


def _tq() -> dict:
    """三題稽核區的形狀（`alpha.three_questions.evaluate`＋組別資訊；值照 11-10 被點名的那一類）。"""
    return {
        "today": "2026-11-10",
        "will_it_die": [
            {"key": "wipeout_cash_runway", "label": "會死嗎：現金跑道", "value": "green", "source": "engine_c",
             "absence_kind": None, "reason": None, "detail": {"runway_months": 40.0, "cash_and_equivalents": 1.2e9}},
            {"key": "wipeout_debt", "label": "會死嗎：負債", "value": "amber", "source": "engine_c",
             "absence_kind": None, "reason": None, "detail": {"borrowings": 3.0e8, "lease_basis": "separated"}},
            {"key": "wipeout_dilution", "label": "會死嗎：稀釋", "value": "amber", "source": "edgar",
             "absence_kind": None, "reason": None,
             "detail": {"issued": 1.5e7, "market_cap_usd": 5.568e8, "pct_of_market_cap": 0.027,
                        "market_cap_absence": None}},
            {"key": "wipeout_going_concern", "label": "會死嗎：繼續經營", "value": None, "source": None,
             "absence_kind": "not_yet_recorded", "reason": "查核報告還沒讀", "detail": {}},
        ],
        "priced_in": [
            {"key": "own_history_pctile", "label": "已定價①：自家歷史百分位", "value": 77.3, "basis": "P/S",
             "absence_kind": None, "reason": None, "detail": {"multiple_today": 20.3, "median": 9.1, "samples": 700}},
            {"key": "cohort_median", "label": "已定價②：主題等權組中位數", "value": None, "basis": None,
             "absence_kind": "insufficient_evidence", "reason": "同口徑成員不到 2 檔", "detail": {"n_same_basis": 1}},
            {"key": "rel_return_30d", "label": "已定價③：相對組 30 個交易日漲幅", "value": -0.329,
             "absence_kind": None, "reason": None, "detail": {"own_return": -0.41, "cohort_mean_return": -0.081}},
        ],
        "in_numbers": [
            {"key": "in_numbers_series", "label": "出現在數字裡了嗎：營收序列", "absence_kind": None, "reason": None,
             "basis": "台股月營收 YoY（可用日＝法定期限，非實際公告日）",
             "value": [{"data_month": "2026-09", "revenue_twd_thousand": 812345, "yoy": 0.153},
                       {"data_month": "2026-10", "revenue_twd_thousand": 900001, "yoy": 0.214}],
             "detail": {"currency": "TWD"}},
        ],
    }


def _price_numbers(obj) -> list:
    """遮過的畫面裡還看得到的價格數字（已定價的值與 detail、會死嗎的市值鍵）。"""
    found = []
    for row in obj.get("priced_in") or ():
        if isinstance(row.get("value"), (int, float)):
            found.append(row["key"])
        for key, value in (row.get("detail") or {}).items():
            if isinstance(value, (int, float)):
                found.append(f"{row['key']}.{key}")
    for row in obj.get("will_it_die") or ():
        for key in ("market_cap_usd", "pct_of_market_cap"):
            if isinstance((row.get("detail") or {}).get(key), (int, float)):
                found.append(f"{row['key']}.{key}")
    return found


# ---------------------------------------------------------------------------
# 三題稽核區
# ---------------------------------------------------------------------------

def test_three_questions_mask_hides_every_price_and_keeps_the_rest():
    raw = _tq()
    assert _price_numbers(raw)                       # 原樣有價格（否則這條測試沒在測東西）
    masked = mask_three_questions(raw)
    assert _price_numbers(masked) == []
    priced = {row["key"]: row for row in masked["priced_in"]}
    assert priced["own_history_pctile"]["value"] == MASKED and priced["own_history_pctile"]["basis"] == "P/S"
    assert priced["rel_return_30d"]["value"] == MASKED
    # 缺席照印：量不到是研究要知道的
    assert priced["cohort_median"]["value"] is None
    assert priced["cohort_median"]["absence_kind"] == "insufficient_evidence"
    assert priced["cohort_median"]["reason"] == "同口徑成員不到 2 檔"
    # 會死嗎：燈色與非市值的 detail 照印，市值鍵遮掉
    die = {row["key"]: row for row in masked["will_it_die"]}
    assert die["wipeout_dilution"]["value"] == "amber"
    assert die["wipeout_dilution"]["detail"]["issued"] == 1.5e7
    assert die["wipeout_dilution"]["detail"]["market_cap_usd"] == MASKED
    assert die["wipeout_dilution"]["detail"]["market_cap_absence"] is None
    assert die["wipeout_cash_runway"]["detail"]["runway_months"] == 40.0
    # 出現在數字裡了嗎整段照印
    assert masked["in_numbers"] == raw["in_numbers"]
    assert masked["prices_masked"] == PRICES_HINT
    assert raw["priced_in"][0]["value"] == 77.3      # 不改輸入


def test_masked_is_not_the_same_shape_as_absent():
    """遮掉與缺席不同形（L12）：遮掉的格不是 null，缺席的格不會被印成遮掉。"""
    assert MASKED is not None and isinstance(MASKED, str) and MASKED.strip()
    masked = mask_three_questions(_tq())
    states = {row["key"]: (row["value"], row["absence_kind"]) for row in masked["priced_in"]}
    assert states["own_history_pctile"] == (MASKED, None)
    assert states["cohort_median"] == (None, "insufficient_evidence")


# ---------------------------------------------------------------------------
# research packet 與敘事紀錄
# ---------------------------------------------------------------------------

def _packet() -> dict:
    return {"ticker": "IQE.L", "context_digest": "sha256:x", "deterministic": {
        "market": {"price": 31.1, "bar_date": "2026-11-09", "quote_unit": "GBp", "market_cap": 4.1e10,
                   "market_cap_absence_reason": None, "settlement_currency": "GBP", "price_kind": "close"},
        "consensus": {"analyst_count": 3, "target_mean": 40.0, "forward_pe": None, "trailing_pe": 55.0,
                      "ev_revenue": 2.2, "forward_eps": 0.4, "revenue_estimate_next_fy": 1.2e8,
                      "revenue_estimate_next_fy_growth": 0.1, "estimate_revision_30d": None},
        "valuation_market_implied": {"market_implied_growth": 0.3, "market_implied_margin": None,
                                     "internal_implied_growth": None, "internal_implied_margin": None,
                                     "method": "x"},
        "fundamentals": {"revenue_ttm": 1.1e8},
    }, "brief_frame": {"version": 2}}


def test_packet_mask_hides_price_cap_target_and_multiples():
    raw = _packet()
    masked = mask_packet(raw)
    det = masked["deterministic"]
    assert det["market"]["price"] == MASKED and det["market"]["market_cap"] == MASKED
    assert det["consensus"]["target_mean"] == MASKED
    assert det["consensus"]["trailing_pe"] == MASKED and det["consensus"]["ev_revenue"] == MASKED
    assert det["valuation_market_implied"]["market_implied_growth"] == MASKED
    # 不是價格的照印；本來就沒有的照舊是 null（缺席不印成遮掉）
    assert det["market"]["bar_date"] == "2026-11-09" and det["market"]["quote_unit"] == "GBp"
    assert det["consensus"]["analyst_count"] == 3 and det["consensus"]["revenue_estimate_next_fy"] == 1.2e8
    assert det["consensus"]["forward_pe"] is None and det["valuation_market_implied"]["market_implied_margin"] is None
    assert det["fundamentals"] == {"revenue_ttm": 1.1e8}
    assert masked["brief_frame"] == {"version": 2} and masked["prices_masked"] == PRICES_HINT
    assert raw["deterministic"]["market"]["price"] == 31.1        # 不改輸入
    assert "31.1" not in json.dumps(masked) and "40.0" not in json.dumps(masked)


def test_brief_record_mask_hides_priced_at_write_only():
    raw = {"brief_id": "ib_x", "slots": [{"key": "priced", "text": "10-29 收盤約 23 倍"}],
           "priced_at_write": {"recorded_on": "2026-11-10", "value": 77.3, "basis": "P/S"}}
    masked = mask_brief_record(raw)
    assert masked["priced_at_write"] == MASKED
    assert masked["slots"] == raw["slots"]            # 正文裡寫的字面價格不遮：那是當時寫下的判斷
    assert mask_brief_record({"brief_id": "ib_y", "priced_at_write": None})["priced_at_write"] is None
    assert raw["priced_at_write"]["value"] == 77.3


# ---------------------------------------------------------------------------
# 命令列：alpha lights／research／brief --show
# ---------------------------------------------------------------------------

def _lights_args(*tickers, prices=False, fmt="markdown"):
    return argparse.Namespace(tickers=list(tickers), prices=prices, format=fmt)


@pytest.fixture
def lights_env(monkeypatch):
    from alpha import cli
    from alpha.providers import candidates as cp

    monkeypatch.setattr(cli, "_resolve_company", lambda t: (t.upper(), f"co:{t.lower()}"))
    calls = []

    def fake_lights_for(ticker, *, today=None):
        calls.append(ticker)
        if ticker == "NOPE.TW":
            return None, "OperationalError: 正式庫讀不到"
        return _tq(), None

    monkeypatch.setattr(cp, "lights_for", fake_lights_for)
    return calls


def test_lights_default_prints_lights_and_numbers_but_no_prices(lights_env, capsys):
    from alpha.cli import cmd_lights

    assert cmd_lights(_lights_args("3163.TWO")) == 0
    out = capsys.readouterr().out
    assert PRICES_HINT in out and PRICES_SHOWN not in out
    assert "現金跑道：綠" in out and "稀釋：黃" in out
    assert "繼續經營：缺席 not_yet_recorded——查核報告還沒讀" in out
    assert "2026-10 年增 +21.4%" in out                       # 出現在數字裡了嗎照印
    assert "已定價①：自家歷史百分位：" + MASKED in out
    assert "已定價②：主題等權組中位數：缺席 insufficient_evidence——同口徑成員不到 2 檔" in out
    for leak in ("-32.9", "−32.9", "32.9%", "77.3", "20.3", "556", "-0.329"):
        assert leak not in out, leak


def test_lights_with_prices_shows_values_and_says_so(lights_env, capsys):
    from alpha.cli import cmd_lights

    assert cmd_lights(_lights_args("3163.TWO", prices=True)) == 0
    out = capsys.readouterr().out
    assert PRICES_SHOWN in out and MASKED not in out
    assert "77.3" in out and "-0.329" in out


def test_lights_json_is_masked_and_unread_is_named(lights_env, capsys):
    from alpha.cli import cmd_lights

    assert cmd_lights(_lights_args("3163.TWO", "NOPE.TW", fmt="json")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert _price_numbers(payload["3163.TWO"]["result"]) == []
    assert payload["NOPE.TW"] == {"result": None, "unread": "OperationalError: 正式庫讀不到"}


def test_lights_markdown_names_an_unread_ticker(lights_env, capsys):
    from alpha.cli import cmd_lights

    assert cmd_lights(_lights_args("NOPE.TW")) == 0
    assert "未讀到：OperationalError: 正式庫讀不到" in capsys.readouterr().out


def test_lights_for_uses_the_board_connection_point_and_narrative_history(monkeypatch):
    """與候選板同一個串接點、同一份 history_not_comparable（L16）。"""
    from alpha.providers import candidates as cp

    seen = {}

    def fake(ticker, *, today, history_not_comparable):
        seen.update(ticker=ticker, today=today, hnc=history_not_comparable)
        return {"priced_in": []}, None

    from datetime import date

    from alpha.narrative import RECORD_VERSION_V2

    monkeypatch.setattr(cp, "_wipeout_and_three_questions", fake)
    brief = SimpleNamespace(record_version=RECORD_VERSION_V2,
                            history_not_comparable=SimpleNamespace(as_dict=lambda: {"until": "2026-06-30"}))
    monkeypatch.setattr(cp, "_current_brief", lambda ticker, today: brief)
    result, note = cp.lights_for("AXTI", today=date(2026, 11, 10))
    assert result == {"priced_in": []} and note is None
    assert seen == {"ticker": "AXTI", "today": date(2026, 11, 10), "hnc": {"until": "2026-06-30"}}
    # 沒有現行敘事、或是舊版（v1）＝不帶 history_not_comparable——與候選板同一個判斷
    monkeypatch.setattr(cp, "_current_brief", lambda ticker, today: None)
    cp.lights_for("AXTI", today=date(2026, 11, 10))
    assert seen["hnc"] is None


def test_research_packet_is_masked_unless_prices(monkeypatch, capsys):
    import alpha.models as models
    from alpha import cli

    closed = []
    graph = SimpleNamespace(driver=SimpleNamespace(close=lambda: closed.append(1)))
    monkeypatch.setattr(cli, "_build", lambda ticker, as_of: (object(), graph))
    monkeypatch.setattr(models, "build_packet",
                        lambda build: SimpleNamespace(to_json=lambda: json.dumps(_packet()), context_digest="sha256:x"))
    args = argparse.Namespace(ticker="IQE.L", as_of=None, judgment=None, out=None, format="markdown", prices=False)
    assert cli.cmd_research(args) == 0
    masked = json.loads(capsys.readouterr().out)
    assert masked["deterministic"]["market"]["price"] == MASKED and masked["prices_masked"] == PRICES_HINT
    args.prices = True
    assert cli.cmd_research(args) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["deterministic"]["market"]["price"] == 31.1 and "prices_masked" not in shown
    assert closed == [1, 1]


def test_brief_show_prints_the_current_record_with_priced_at_write_masked(monkeypatch, tmp_path, capsys):
    from alpha import cli
    from alpha.providers import briefs as briefs_provider

    monkeypatch.setattr(cli, "_resolve_company", lambda t: ("2455.TW", "co:visual_photonics"))
    rows = [{"brief_id": "ib_old", "priced_at_write": {"value": 50.0}},
            {"brief_id": "ib_new", "priced_at_write": {"value": 88.8}, "slots": [{"key": "priced", "text": "照抄"}]}]
    monkeypatch.setattr(briefs_provider, "BRIEF_DIR", tmp_path)
    (tmp_path / "2455.TW.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(briefs_provider, "current_brief_id", lambda ticker: "ib_new")
    args = argparse.Namespace(ticker="2455.TW", add=None, retract=None, show="current", prices=False,
                              format="markdown", list=False, rationale=None)
    assert cli.cmd_brief(args) == 0
    out = capsys.readouterr().out
    assert '"ib_new"' in out and MASKED in out and PRICES_HINT in out
    assert "88.8" not in out and "50.0" not in out
    args.show, args.prices = "ib_old", True
    assert cli.cmd_brief(args) == 0
    out = capsys.readouterr().out
    assert '"ib_old"' in out and "50.0" in out and PRICES_SHOWN in out
    args.show = "ib_none"
    assert cli.cmd_brief(args) == 2
    monkeypatch.setattr(briefs_provider, "current_brief_id", lambda ticker: None)
    args.show = "current"
    assert cli.cmd_brief(args) == 2                    # 沒有現行敘事（沒寫過或最新一筆是撤回）
