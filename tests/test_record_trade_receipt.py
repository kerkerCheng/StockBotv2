"""成交的研究收據（Phase 3 Step 3.8；資本路徑，使用者 2026-09-29 預先授權 #16）。

守的是 plan §9：
1. alpha／beta 只由 `risk/hard_caps.py` 的公開判別決定（賣出也判）；beta 不要收據、行為不變。
2. alpha 買進沒有現行 v2 敘事 → fail closed（exit 4）；`--no-narrative-override` 放行並留收據；v1 視同缺 v2；
   Sheet symbol 解析不到＝`unresolved`（不猜）。
3. **兩個放行互不放行**：缺敘事的放行不放行 >5%，硬擋的 override 不放行缺敘事。
4. 賣出缺 `--why` → fail closed；`--disproof-watch` 以**來源**歸屬驗（不以 entities）。
5. 收據分 declared／derived；derived 讀當天 artifact，缺席或過期記 `upstream_unavailable`、成交照走。
6. dry-run 也組收據、也印、也擋；dry-run 不寫 Sheet 也不寫 trade_log；收據路徑沒有對外連線。
全部用暫存 log、假 Sheet、暫存 ledger——不讀真實 Sheet、不寫真實 trade_log。
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.narrative import RECORD_VERSION_V2, brief_record
from tests.test_candidates import _slots

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 30)
SIVERS = "co:sivers_semiconductors"


def _module():
    spec = importlib.util.spec_from_file_location("record_trade", ROOT / "scripts" / "record_trade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sheet_rows(**extra) -> list[dict]:
    rows = [
        {"ticker": "FRA:2DG", "bucket": "觀察", "market_value_base": 1_000.0, "nav_base": 100_000.0,
         "base_currency": "USD", "currency": "EUR", "shares": 100.0},
        {"ticker": "7803.T", "bucket": "觀察", "market_value_base": 500.0, "nav_base": 100_000.0,
         "base_currency": "USD", "currency": "JPY", "shares": 10.0},
        {"ticker": "QQQ", "bucket": "BETA", "market_value_base": 20_000.0, "nav_base": 100_000.0,
         "base_currency": "USD", "currency": "USD", "shares": 30.0},
        {"ticker": "CASH", "bucket": "CASH", "market_value_base": 78_500.0, "nav_base": 100_000.0,
         "base_currency": "USD", "currency": "USD", "shares": 0.0},
    ]
    for ticker, value in extra.items():
        for row in rows:
            if row["ticker"] == ticker:
                row["market_value_base"] = value
    return rows


def _sive_brief(*, reading_id: str, version: str = RECORD_VERSION_V2, created: datetime | None = None,
                disproof=()) -> dict:
    created = created or datetime(2026, 9, 29, 3, tzinfo=timezone.utc)
    if version != RECORD_VERSION_V2:
        return brief_record(company_id=SIVERS, ticker="SIVE.ST", created_at=created,
                            slots={k: {"text": "x", "evidence_refs": ["e"]} for k in
                                   ("demand", "supply", "bottleneck", "market_view", "our_bet", "if_right_if_wrong",
                                    "when")})
    return brief_record(company_id=SIVERS, ticker="SIVE.ST", slots=_slots(), record_version=RECORD_VERSION_V2,
                        rides=[{"node": "prod:supernova", "unit": "socket", "reading_id": reading_id}],
                        disproof=list(disproof), answers={"priced_in": "yes", "in_numbers": "yes"},
                        candidate_state={"state": "missing", "watch_id": "ew_wait", "reason": "等客戶端一手"},
                        created_at=created)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """暫存的敘事 ledger（SIVE.ST v2）、讀圖 ledger（一份插槽讀圖）、watch、lifecycle、當天 artifact、假 Sheet。"""
    import alpha.providers.briefs as briefs_mod
    import engine_b.disproof as disproof
    import engine_b.event_watch as ew
    import webapp.store as store
    from alpha.providers import structure_readings as sr
    from alpha.providers.briefs import append_brief_record
    from fetchers import gsheets
    from tests.test_structure_reading_v3 import SOCKET, _quotes, _v3

    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", tmp_path / "briefs")
    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path / "readings")
    reading = _v3(SOCKET)
    sr.append_reading_record(reading, quotes=_quotes(SOCKET))
    state = {"reading": reading, "watches": [], "lifecycle": {}, "rows": _sheet_rows(), "writes": [],
             "candidates_today": TODAY.isoformat(), "analyst_generated": "2026-09-30T02:00:00+08:00",
             "analyst_as_of": None, "tq_panel": {"status": "partial", "absence_kind": None, "reason": "1／4 行缺席"}}
    append_brief_record(_sive_brief(reading_id=reading["reading_id"]), directory=tmp_path / "briefs")
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": state["watches"]})
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: state["lifecycle"])

    def read_state(self, kind):
        if state["candidates_today"] is None:
            raise store.ArtifactUnavailable(kind, "尚未 materialize")
        from alpha.providers.briefs import read_brief_records

        current = read_brief_records("SIVE.ST")[0]
        row = {"ticker": "SIVE.ST", "company_id": SIVERS,
               "brief_id": state.get("board_brief") or (current[-1].brief_id if current else None),
               "derived": "held", "group": "held", "declared": "missing", "preconditions": [], "rewrite": [],
               "three_words": {"will_it_die": "紅（灰 2）", "priced_in": "是", "in_numbers": "是"}}
        return {"today": state["candidates_today"], "generated_at": "2026-09-30T05:37:00+00:00",
                "groups": {"held": [row]}, "side_groups": {}, "holdings": {"unresolved": ["7803.T"]}}, None

    def read_view(self, ticker):
        line = {"datum": {"label": "已定價①", "value": 88.5, "status": "available", "absence_kind": None,
                          "as_of": "2026-09-28", "method": "百分位規則",
                          "dependencies": {"question": "priced_in", "row_key": "own_history_pctile",
                                           "source": "engine_c", "basis": "P/S", "detail": {"multiple_today": 38.5}}}}
        panel = {**state["tq_panel"], "lines": [line] if state["tq_panel"]["status"] != "missing" else []}
        return {"generated_at": state["analyst_generated"], "as_of": state["analyst_as_of"],
                "point_in_time_mode": "current" if state["analyst_as_of"] is None else "as_of",
                "view": {"three_questions": panel}}, None

    monkeypatch.setattr(store.StateArtifactStore, "read", read_state)
    monkeypatch.setattr(store.ArtifactStore, "read", read_view)
    monkeypatch.setattr(gsheets, "fetch_portfolio", lambda *, strict_operational=False, values=None: state["rows"])
    state["reads"] = []
    monkeypatch.setattr(gsheets, "read_portfolio_values",
                        lambda *, formulas=False, sheet=None: state["reads"].append(formulas) or [["symbol"]])
    cells = {"shares": {"a1": "B2", "current": "100"}, "avg_cost": {"a1": "C2", "current": "10"},
             "currency": {"a1": "F2", "current": "USD"}}
    monkeypatch.setattr(gsheets, "locate_portfolio_cells", lambda requests, values=None: [
        dict(cells.get(r["column"], {"a1": "D5", "current": "50000"})) for r in requests])

    def write(writes):
        state["writes"].append(writes)
        return {"written": [w["a1"] for w in writes]}

    monkeypatch.setattr(gsheets, "write_portfolio_cells", write)
    module = _module()
    module.TRADE_LOG = tmp_path / "trade_log.jsonl"
    module._today = lambda: TODAY
    state["module"] = module
    state["tmp"] = tmp_path
    return state


def _trade(symbol: str, side: str = "buy", *extra: str) -> list[str]:
    return ["--symbol", symbol, "--side", side, "--shares", "10", "--price", "10", "--currency", "USD",
            "--executed-at", "2026-09-30T09:00:00+02:00", "--broker", "IB", *extra]


def _entry(env) -> dict:
    return json.loads(env["module"].TRADE_LOG.read_text(encoding="utf-8").splitlines()[-1])


# ---------------------------------------------------------------------------
# 1. FRA:2DG → SIVE.ST：收據欄位齊全
# ---------------------------------------------------------------------------

def test_fra_2dg_buy_resolves_to_sive_and_the_receipt_has_both_halves(env, capsys) -> None:
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "插槽讀圖出現客戶端一手", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["company_id"] == SIVERS and receipt["research_ticker"] == "SIVE.ST"
    assert receipt["resolution"] == "execution_alias" and receipt["narrative"] == "present"
    declared = receipt["declared"]
    assert declared["brief_id"].startswith("ib_") and declared["candidate_state"]["state"] == "missing"
    assert declared["answers"] == {"priced_in": "yes", "in_numbers": "yes"}
    assert declared["rides"][0]["reading_id"] == env["reading"]["reading_id"]
    assert declared["rides"][0]["result_digest"] == env["reading"]["result_digest"], "讀圖寫入當時的 digest"
    derived = receipt["derived"]
    assert derived["status"] == "available" and derived["candidate_as_of"] == TODAY.isoformat()
    assert derived["candidate"]["derived"] == "held" and derived["three_questions"][0]["key"] == "own_history_pctile"
    row = derived["three_questions"][0]
    assert row["rule"] == "百分位規則" and row["detail"] == {"multiple_today": 38.5} and row["status"] == "available", \
        "稽核行照抄規則與支撐數字（收據是當時憑什麼的唯一 A5 留存）"
    assert derived["three_questions_panel"]["status"] == "partial"
    assert derived["sheet"] == {"held_before_this_row": True, "held_before_company": True, "sheet_state": "pre_trade"}
    assert receipt["input_problems"] == []
    assert receipt["why"] == "插槽讀圖出現客戶端一手"
    assert "hard_cap_check" in _entry(env), "收據不與 hard_cap_check 混，兩個 key 各自在"
    assert "研究收據（alpha buy）" in capsys.readouterr().out


def test_dry_run_builds_and_prints_the_receipt_but_writes_nothing(env, capsys) -> None:
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "dry-run")) == 0
    out = capsys.readouterr().out
    assert "研究收據" in out and "declared：敘事 ib_" in out
    assert env["writes"] == [] and not module.TRADE_LOG.exists()


# ---------------------------------------------------------------------------
# 2. 沒有 v2 敘事：fail closed，放行留收據
# ---------------------------------------------------------------------------

def test_no_narrative_fails_closed_and_the_override_records_absent(env, monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", env["tmp"] / "empty")
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == module.EXIT_NARRATIVE
    assert env["writes"] == [] and not module.TRADE_LOG.exists()
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply",
                              "--no-narrative-override", "小倉位試單，敘事下週補")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["narrative"] == "absent" and receipt["declared"] is None
    assert receipt["narrative_override_reason"] == "小倉位試單，敘事下週補"


def test_legacy_v1_narrative_counts_as_missing_v2(env, monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers.briefs import append_brief_record

    module = env["module"]
    ledger = env["tmp"] / "v1"
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", ledger)
    append_brief_record(_sive_brief(reading_id="sr_x", version="v1"), directory=ledger)
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x")) == module.EXIT_NARRATIVE
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply", "--no-narrative-override", "v1 舊敘事")) == 0
    assert _entry(env)["research_receipt"]["narrative"] == "legacy_v1"


def test_unresolved_symbol_is_unresolved_not_guessed(env) -> None:
    module = env["module"]
    assert module.main(_trade("7803.T", "buy", "--why", "x")) == module.EXIT_NARRATIVE
    assert module.main(_trade("7803.T", "buy", "--why", "x", "--apply", "--no-narrative-override", "registry 還沒登")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["narrative"] == "unresolved" and receipt["company_id"] is None
    assert "解析不到公司" in receipt["derived"]["reason"], "沒有個股頁可對≠讀不到（下一步是補 registry）"


def test_narrative_override_is_refused_when_a_v2_narrative_exists(env) -> None:
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--no-narrative-override", "多餘")) == 2


# ---------------------------------------------------------------------------
# 3. 兩個放行互不放行
# ---------------------------------------------------------------------------

def test_narrative_override_does_not_release_the_five_percent_cap(env, monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", env["tmp"] / "empty")
    env["rows"][0]["market_value_base"] = 4_950.0                           # 已持 4.95%，再買 100 → 超 5%
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply",
                              "--no-narrative-override", "理由")) == module.EXIT_HARD_CAP
    assert env["writes"] == [] and not module.TRADE_LOG.exists()


def test_hard_cap_override_does_not_release_a_missing_narrative(env, monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", env["tmp"] / "empty")
    env["rows"][0]["market_value_base"] = 4_950.0
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply",
                              "--override", "--reason", "分批")) == module.EXIT_NARRATIVE
    assert env["writes"] == [] and not module.TRADE_LOG.exists()
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply", "--override", "--reason", "分批",
                              "--no-narrative-override", "試單")) == 0, "兩個放行都給才過"
    entry = _entry(env)
    assert entry["override_reason"] == "分批" and entry["research_receipt"]["narrative_override_reason"] == "試單"


# ---------------------------------------------------------------------------
# 4. 輸入守門與賣出
# ---------------------------------------------------------------------------

def test_alpha_without_why_fails_before_touching_the_sheet(env, monkeypatch) -> None:
    from fetchers import gsheets

    def boom(*a, **k):
        raise AssertionError("不該碰 Sheet")

    monkeypatch.setattr(gsheets, "locate_portfolio_cells", boom)
    monkeypatch.setattr(gsheets, "fetch_portfolio", boom)
    monkeypatch.setattr(gsheets, "read_portfolio_values", boom)
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "sell")) == 2
    assert module.main(_trade("FRA:2DG", "buy", "--why", "   ")) == 2
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--no-narrative-override", "r")) == 2
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--disproof-watch", "ew_1")) == 2
    assert not module.TRADE_LOG.exists()


def test_sell_with_why_records_the_receipt_even_without_a_narrative(env, monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", env["tmp"] / "empty")
    assert module.main(_trade("FRA:2DG", "sell", "--why", "結構變了", "--apply")) == 0, "賣出不要求敘事"
    receipt = _entry(env)["research_receipt"]
    assert receipt["side"] == "sell" and receipt["narrative"] == "absent"


def test_disproof_watch_is_attributed_by_source_not_by_entities(env, tmp_path) -> None:
    from alpha.providers.briefs import read_brief_records

    module = env["module"]
    brief_id = read_brief_records("SIVE.ST")[0][0].brief_id
    env["watches"] = [
        {"watch_id": "ew_src", "kind": "semantic_condition", "status": "fired", "source_ref": f"brief:{brief_id}#1",
         "condition": "c" * 30, "entities": ["co:someone_else"], "expires": "2027-01-01"},
        {"watch_id": "ew_ent", "kind": "semantic_condition", "status": "active",
         "source_ref": "thesis:thesis/other.md#1", "condition": "d" * 30, "entities": [SIVERS], "expires": "2027-01-01"},
    ]
    assert module.main(_trade("FRA:2DG", "sell", "--why", "反證觸發", "--disproof-watch", "ew_src", "--apply")) == 0
    assert _entry(env)["research_receipt"]["disproof_watch"]["watch_id"] == "ew_src", "來源歸屬本檔、entities 不含 → 收"
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--disproof-watch", "ew_ent")) == 2, \
        "entities 含本檔但來源不歸屬 → 拒"
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--disproof-watch", "ew_nope")) == 2


# ---------------------------------------------------------------------------
# 5. beta 不變
# ---------------------------------------------------------------------------

def test_beta_needs_no_receipt_and_rejects_research_flags(env) -> None:
    module = env["module"]
    assert module.main(_trade("QQQ", "buy", "--apply")) == 0
    entry = _entry(env)
    assert "research_receipt" not in entry and entry["hard_cap_check"]["status"] == "pass"
    for flags in (["--why", "x"], ["--why", ""], ["--no-narrative-override", "r"], ["--disproof-watch", "ew_1"],
                  ["--disproof-watch", ""]):
        assert module.main(_trade("QQQ", "buy", *flags)) == 2, f"beta 給 {flags} 是誤會，照實拒絕而不是默默忽略"


# ---------------------------------------------------------------------------
# 6. derived：log-only、artifact 缺席／過期不擋成交
# ---------------------------------------------------------------------------

def test_log_only_marks_the_sheet_as_post_trade(env) -> None:
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--log-only")) == 0
    sheet = _entry(env)["research_receipt"]["derived"]["sheet"]
    assert sheet["held_before_this_row"] is None and sheet["held_before_company"] is None
    assert sheet["sheet_state"].startswith("post_trade")


@pytest.mark.parametrize("case", ["missing", "stale"])
def test_missing_or_stale_artifact_is_recorded_and_does_not_block(env, case) -> None:
    module = env["module"]
    env["candidates_today"] = None if case == "missing" else "2026-09-29"
    env["analyst_generated"] = "2026-09-28T02:00:00+08:00"
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    derived = _entry(env)["research_receipt"]["derived"]
    assert derived["status"] == "upstream_unavailable" and "candidate" not in derived
    assert ("讀不到" if case == "missing" else "不是今天") in derived["reason"] and "個股頁 artifact" in derived["reason"]


# ---------------------------------------------------------------------------
# 7. 資本路徑的邊界
# ---------------------------------------------------------------------------

def test_the_receipt_path_makes_no_network_connection(env, monkeypatch) -> None:
    """不連 Neo4j、不打行情或 FX：組收據期間把 socket 連線整個擋掉，照樣組得出來。"""
    import socket

    attempts: list = []

    class Refused(BaseException):
        """BaseException 子類：`except Exception` 吞不掉（3.8 R1：原本用 AssertionError，被 fail-soft 吞成一條 problem）。"""

    def refuse(*a, **k):
        attempts.append(a)
        raise Refused("收據路徑不得對外連線")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    assert attempts == [] and receipt["derived"]["status"] == "available" and receipt["input_problems"] == []


def test_alpha_beta_split_uses_the_public_hard_cap_function() -> None:
    source = (ROOT / "scripts" / "record_trade.py").read_text(encoding="utf-8")
    assert "from risk.hard_caps import is_beta_symbol" in source
    assert "_instrument_for" not in source, "不得用私有判別"
    order = source.split("def main(", 1)[1]
    assert order.index("locate_portfolio_cells(requests, values=sheet_values)") \
        < order.index("_hard_cap_verdict(args, sheet_rows, sheet_error)") \
        < order.index("research_receipt.build_receipt("), "順序：locate → 硬擋 → 收據"



# ---------------------------------------------------------------------------
# 8. R1 覆核補的（2026-09-30）
# ---------------------------------------------------------------------------

def test_reason_without_override_is_still_rejected(env) -> None:
    """§9 第 4 點：既有「--reason 無 --override 就 exit 2」的守門保留。"""
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--reason", "多餘")) == 2
    assert not module.TRADE_LOG.exists()


def test_empty_disproof_watch_is_rejected_not_ignored(env, monkeypatch) -> None:
    """空字串＝使用者以為給了——在碰 Sheet 之前就拒（不是等到歸屬檢查才順帶拒）。"""
    from fetchers import gsheets

    def boom(*a, **k):
        raise AssertionError("空的 --disproof-watch 要在碰 Sheet 之前就被拒")

    monkeypatch.setattr(gsheets, "locate_portfolio_cells", boom)
    monkeypatch.setattr(gsheets, "read_portfolio_values", boom)
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--disproof-watch", "", "--apply")) == 2
    assert env["writes"] == [] and not module.TRADE_LOG.exists()


def test_a_whole_three_questions_absence_is_declared_not_an_empty_list(env) -> None:
    """3.8 R1 blocking：三題取數失敗時面板整段缺席——收據不得記成 available＋空陣列。"""
    module = env["module"]
    env["tq_panel"] = {"status": "missing", "absence_kind": "upstream_unavailable", "reason": "三題取數失敗：locked"}
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0, "推導缺席不擋成交"
    derived = _entry(env)["research_receipt"]["derived"]
    assert derived["status"] == "upstream_unavailable" and "三題取數失敗：locked" in derived["reason"]
    assert derived["three_questions_panel"]["absence_kind"] == "upstream_unavailable"


def test_an_as_of_view_artifact_is_not_todays_derivation(env) -> None:
    module = env["module"]
    env["analyst_as_of"] = "2026-06-30"
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    derived = _entry(env)["research_receipt"]["derived"]
    assert derived["status"] == "upstream_unavailable" and "as-of 2026-06-30" in derived["reason"]
    assert "three_questions" not in derived


@pytest.mark.parametrize("case", ["raises", "bad_line"])
def test_an_unreadable_narrative_ledger_is_unreadable_not_absent(env, monkeypatch, case) -> None:
    """讀不到／有壞行≠沒有敘事（L11-5、L12）：買進 fail closed，賣出照記；有壞行時不得退回舊版而自動放行。"""
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    if case == "raises":
        def boom(*a, **k):
            raise PermissionError("locked")

        monkeypatch.setattr(briefs_mod, "read_brief_records", boom)
    else:
        with (env["tmp"] / "briefs" / "SIVE.ST.jsonl").open("a", encoding="utf-8") as fh:
            fh.write("{not json\n")
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x")) == module.EXIT_NARRATIVE
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--apply")) == 0, "讀不到研究原料不擋賣出"
    receipt = _entry(env)["research_receipt"]
    assert receipt["narrative"] == "unreadable" and receipt["declared"] is None
    assert any("敘事 ledger" in p for p in receipt["input_problems"])


def test_a_company_without_research_ticker_is_unreadable_not_absent(env, monkeypatch) -> None:
    from identity.registry import get_registry

    module = env["module"]
    registry = get_registry()
    monkeypatch.setattr(type(registry), "research_ticker", lambda self, cid: None)
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x")) == module.EXIT_NARRATIVE
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["narrative"] == "unreadable" and "research ticker" in " ".join(receipt["input_problems"])
    assert "解析不到公司" not in receipt["derived"]["reason"], "公司解析到了，只是沒有 research ticker"


def test_registry_failure_is_unresolved_and_does_not_crash(env, monkeypatch) -> None:
    import identity.registry as reg

    def boom():
        raise OSError("config 壞了")

    monkeypatch.setattr(reg, "get_registry", boom)
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["narrative"] == "unresolved" and any("registry" in p for p in receipt["input_problems"])


def test_lifecycle_unreadable_says_cannot_confirm_not_does_not_belong(env, capsys) -> None:
    env["lifecycle"] = None
    env["watches"] = [{"watch_id": "ew_th", "kind": "semantic_condition", "status": "fired",
                       "source_ref": "thesis:thesis/sive.md#1", "condition": "c" * 30, "entities": [SIVERS],
                       "expires": "2027-01-01"}]
    module = env["module"]
    assert module.main(_trade("FRA:2DG", "sell", "--why", "x", "--disproof-watch", "ew_th")) == 2
    err = capsys.readouterr().err
    assert "lifecycle 讀不到" in err and "無法確認" in err and "不歸屬" not in err.split("無法確認")[0]


def test_registry_ticker_and_sheet_company_id_paths_are_both_exercised(env, monkeypatch) -> None:
    """真實 Sheet 會帶 neo4j_id（`fetchers/gsheets.py` 的 enrichment）→ `sheet_company_id`；新建倉的公司走 registry。"""
    import alpha.providers.briefs as briefs_mod

    module = env["module"]
    env["rows"][0]["neo4j_id"] = SIVERS
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    assert _entry(env)["research_receipt"]["resolution"] == "sheet_company_id"
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", env["tmp"] / "empty")
    env["rows"].append({"ticker": "AXTI", "bucket": "觀察", "market_value_base": 100.0, "nav_base": 100_000.0,
                        "base_currency": "USD", "currency": "USD", "shares": 1.0})
    env["rows"][3]["market_value_base"] -= 100.0                           # 現金少 100，持股加總才等於 NAV
    assert module.main(_trade("AXTI", "buy", "--why", "x")) == module.EXIT_NARRATIVE, "registry 解析得到但沒有敘事"
    assert module.main(_trade("AXTI", "buy", "--why", "x", "--apply", "--no-narrative-override", "試單")) == 0
    receipt = _entry(env)["research_receipt"]
    assert receipt["resolution"] == "registry_ticker" and receipt["narrative"] == "absent"


def test_declared_watches_are_the_attributed_live_ones(env) -> None:
    from alpha.providers.briefs import read_brief_records

    module = env["module"]
    brief_id = read_brief_records("SIVE.ST")[0][0].brief_id
    env["watches"] = [
        {"watch_id": "ew_live", "kind": "semantic_condition", "status": "active", "source_ref": f"brief:{brief_id}#1",
         "condition": "c" * 30, "entities": [SIVERS], "expires": "2027-01-01"},
        {"watch_id": "ew_done", "kind": "semantic_condition", "status": "consumed", "source_ref": f"brief:{brief_id}#2",
         "condition": "d" * 30, "entities": [SIVERS], "expires": "2027-01-01"},
        {"watch_id": "ew_other", "kind": "semantic_condition", "status": "active", "source_ref": "brief:ib_other#1",
         "condition": "e" * 30, "entities": [SIVERS], "expires": "2027-01-01"},
    ]
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    assert [w["watch_id"] for w in _entry(env)["research_receipt"]["declared"]["watches"]] == ["ew_live"]


def test_board_row_from_an_older_narrative_version_is_flagged(env) -> None:
    """同一天寫了新敘事、候選板還是舊快照：宣告與推導講不同版本時要標出來（L12），不擋成交。"""
    module = env["module"]
    env["board_brief"] = "ib_" + "0" * 16                                  # 候選板那一列還是舊版
    assert module.main(_trade("FRA:2DG", "buy", "--why", "x", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    derived = receipt["derived"]
    assert derived["status"] == "upstream_unavailable" and "不是現行" in derived["reason"]
    assert receipt["declared"]["brief_id"] in derived["reason"] and "ib_" + "0" * 16 in derived["reason"]


def test_an_unreadable_schedule_timezone_never_blocks_the_trade(env, monkeypatch) -> None:
    """3.8 R2-b：排程時區設定讀不到（OSError）時，「今天」退回本機日期、artifact 的日期換算退回本機時區——賣出照記。"""
    from engine_b import event_watch as ew

    def boom(*a, **k):
        raise FileNotFoundError("config/daily_routine.json")

    monkeypatch.setattr(ew, "_local_timezone", boom)
    module = env["module"]
    module._today = boom
    assert module.main(_trade("FRA:2DG", "sell", "--why", "時區設定壞了也要記得下來", "--apply")) == 0
    receipt = _entry(env)["research_receipt"]
    assert any("排程時區讀不到" in p for p in receipt["input_problems"])
