"""Phase 3 Step 3.9 — **新管線 full chain（夾具版）**：圖 → 讀圖 → v2 敘事 → 三題 → 候選狀態 → 個股頁 → 心跳段 2 → 收據。

每一段斷言的是**產出到了下一段手上**（L13：驗收是「產出出現在下游消費者手上」，不是「元件會動」），用的都是正式入口：
- 讀圖：`append_reading_record`＋`register_reading_watches`（暫存 ledger、暫存 watch 檔）；
- 三題：`three_questions_for`（記憶體 Engine C、夾具四盞燈、空的主題等權組）；
- 敘事：`write_brief`（寫入當下的前提檢查、反證自動登記到暫存 watch 檔）；
- 候選：`load_board` → `build_candidates_artifact` → 暫存 state store；
- 個股頁：`seat_readings_context`／`page_input`／`build_analyst_view`（read model 以夾具為底、換上本公司身分）；
- 心跳段 2：`crons.heartbeat._candidate_lines` 讀 artifact；
- 收據：`scripts/record_trade.py` 的 dry-run 與 `--apply`（假 Sheet、暫存 trade log）。
另有兩條「中間一段缺席時，下一段印缺席而不是空白」。不連圖、不讀真實 ledger、不寫真實 registry／Sheet／trade_log。

真 runtime 的那一份（`tests/test_full_chain_acceptance.py`，本機 Neo4j＋Engine C＋凍結 Decision Store）照留，兩份互不取代。
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.narrative import RECORD_VERSION_V2, brief_record
from tests.test_candidates import _slots
from tests.test_record_trade_receipt import _sheet_rows
from tests.test_structure_reading_v3 import SIVERS, SOCKET, _canonical, _quotes, _row, _v3

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 9, 30)
TICKER = "SIVE.ST"
GENERATED = datetime(2026, 9, 30, 4, 0, tzinfo=timezone.utc)
RUNWAY = {"status": "calculated", "runway_months": 9.0, "cash_and_equivalents": 50e6, "total_debt": 80e6,
          "free_cash_flow_ttm": -60e6, "as_of": "2026-09-29", "source": "fixture"}
DISPROOF = ("Ayar Labs 的一手文件具名另一家雷射陣列供應商進入 SuperNova 量產——插槽賭注不成立，重寫敘事")


def _record_trade():
    spec = importlib.util.spec_from_file_location("record_trade", ROOT / "scripts" / "record_trade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def chain(monkeypatch, tmp_path):
    """把整條鏈用正式入口跑一次，回每一段的產出（下一段讀的就是它）。"""
    import alpha.providers.briefs as briefs_mod
    import alpha.providers.candidates as cand
    import alpha.providers.edge as edge_mod
    import alpha.providers.theme_cohorts as cohorts
    import engine_b.disproof as disproof
    import query.structure as qs
    from alpha.providers import structure_readings as sr
    from alpha.providers.briefs import WriteContext, read_brief_records, write_brief
    from alpha.providers.three_questions import three_questions_for
    from alpha.wipeout import wipeout_flags
    from engine_b import event_watch as ew
    from engine_c.db import _ensure_sqlite_schema
    from webapp.materialize import build_candidates_artifact
    from webapp.store import StateArtifactStore

    out: dict = {"tmp": tmp_path}
    # 0. 夾具圖：Sivers 供貨給 SuperNova 插槽；需求側有一家具名公司（Ayar Labs）
    edges = _canonical([_row(SIVERS, "supplies_to", SOCKET), _row("prod:teraphy_chiplet", "depends_on", SOCKET),
                        _row("co:ayar_labs", "depends_on", SOCKET)])
    monkeypatch.setattr(qs, "_load_edges", lambda: edges)

    # 1. 讀圖：暫存 ledger；它的反證登記到（conftest 隔離的）暫存 watch 檔
    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path / "readings")
    reading = _v3(SOCKET, structure=qs.build_structure(SOCKET, edges).as_dict())
    sr.append_reading_record(reading, quotes=_quotes(SOCKET))
    sr.register_reading_watches(reading)
    out["reading"] = reading

    # 2. 三題：記憶體 Engine C（空表）＋夾具四盞燈；主題等權組目錄是空的
    monkeypatch.setattr(cohorts, "THEME_COHORT_DIR", tmp_path / "cohorts")
    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    lamps = wipeout_flags(runway=RUNWAY, shares_series=None, going_concern=None, today=TODAY)
    out["tq"] = three_questions_for(TICKER, today=TODAY, wipeout=lamps, conn=conn)

    # 3. v2 敘事：正式寫入入口；反證寫入即登記、缺 X 在等的 date watch 先登記
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", tmp_path / "briefs")
    watches = ew.load_watches()
    wait = ew.add_watch(watches, kind="date", wake_brief=SIVERS, until="2026-11-26", expires="2027-01-31")
    rows, _errors = sr.reading_status_rows(edges, today=TODAY, watches=watches.get("watches") or ())
    ctx = WriteContext(today=TODAY, reading_rows=rows,
                       readings_by_id={r.reading_id: r for r in sr.read_reading_records(SOCKET)[0]},
                       three_questions=out["tq"], watches=watches, lifecycle={})
    record = brief_record(
        company_id=SIVERS, ticker=TICKER, slots=_slots(), record_version=RECORD_VERSION_V2,
        rides=[{"node": SOCKET, "unit": "socket", "reading_id": reading["reading_id"]}],
        disproof=[{"condition": DISPROOF, "check_frequency": "每季", "action_48h": "重寫敘事", "entities": [SIVERS],
                   "expires": "2027-03-01", "source": "self", "link_source_ref": None}],
        answers={"priced_in": "unmeasurable", "in_numbers": "unmeasurable"},
        candidate_state={"state": "missing", "watch_id": wait["watch_id"], "reason": "等客戶端一手具名"},
        created_at=datetime(2026, 9, 30, 1, tzinfo=timezone.utc))
    out["write"] = write_brief(record, ctx=ctx, watches_path=ew.WATCHES_PATH)
    out["brief"] = read_brief_records(TICKER)[0][-1]
    out["wait"] = wait

    # 4. 候選狀態：整板推導 → artifact（邊緣判定與四盞燈的取數換成夾具；三題就是第 2 段那一份）
    monkeypatch.setattr(edge_mod, "edge_states", lambda tickers: {t: {"state": "edge", "label": "邊緣", "reasons": [],
                                                                     "market_cap_usd": 1e9, "analyst_count": 1}
                                                                  for t in tickers})
    monkeypatch.setattr(cand, "_wipeout_and_three_questions",
                        lambda ticker, *, today, history_not_comparable: (out["tq"], None))
    monkeypatch.setattr(disproof, "load_lifecycle", lambda *a, **k: {})
    cash_only = [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}]
    board = cand.load_board([TICKER], today=TODAY, holdings_loader=lambda: cash_only)
    state_dir = tmp_path / "state"
    StateArtifactStore(state_dir).write(build_candidates_artifact(board, generated_at=GENERATED))
    out.update(board=board, state_dir=state_dir, cash_only=cash_only)
    return out


def _page(chain):
    """第 5 段：個股頁（讀圖 context 與候選 context 各載一次，與 materialize 同一條組法）。"""
    from alpha.providers import candidates as cand
    from alpha.providers.structure_readings import seat_readings_context, seat_readings_for
    from briefing.alpha_view.sources import _chain_readings
    from briefing.analyst_view import build_analyst_view
    from tests.test_alpha_investment_view import _view

    readings_ctx = seat_readings_context(today=TODAY)
    page = cand.page_input(cand.candidate_context([TICKER], today=TODAY, holdings_loader=lambda: chain["cash_only"],
                                                  board=False), TICKER, SIVERS, three_questions=chain["tq"])
    view = _view(today=TODAY, three_questions=chain["tq"], brief_records=[chain["brief"]],
                 chain_readings=_chain_readings(readings_ctx, SIVERS, chain["brief"]),
                 narrative_context={"node_names": {SOCKET: "SuperNova light source", "co:ayar_labs": "Ayar Labs"}})
    # read model 以夾具（COHR 的建構）為底，身分換成本公司——鏈要驗的是注入與三題、讀圖這幾段的交接，
    # 不是重建一整份 SIVE.ST 的 read model（那要 Neo4j，是真 runtime 那一份的事）。
    view = replace(view, identity=replace(view.identity, ticker=TICKER, company_id=SIVERS, company_label="Sivers"))
    return view, build_analyst_view(view, readings=seat_readings_for(readings_ctx, SIVERS), candidate=page)


# ---------------------------------------------------------------------------
# 一條鏈：每一段的產出到了下一段手上
# ---------------------------------------------------------------------------

def test_the_new_pipeline_hands_each_stage_output_to_the_next(chain, monkeypatch, tmp_path, capsys) -> None:
    from engine_b import event_watch as ew

    rid, brief = chain["reading"]["reading_id"], chain["brief"]
    registry = {w["watch_id"]: w for w in ew.load_watches()["watches"]}

    # 讀圖 → watch registry：讀圖的反證登記成 reading:<id>#1
    reading_watch = next(w for w in registry.values() if w.get("source_ref") == f"reading:{rid}#1")
    # 三題 → 敘事寫入：稽核行缺席才准答「無法量」（寫入端讀的就是第 2 段那一份）
    tq = chain["tq"]
    assert all(r["absence_kind"] for r in tq["priced_in"] + tq["in_numbers"])
    assert {r["value"] for r in tq["will_it_die"]} >= {"red"}, "夾具跑道 9 個月＋淨負債燒錢 → 紅燈"
    # 敘事 → watch registry：自己的反證寫入即登記
    brief_watch = next(w for w in registry.values() if w.get("source_ref") == f"brief:{brief.brief_id}#1")
    assert brief_watch["status"] == "active" and chain["write"]["registered"]

    # 敘事＋讀圖＋三題 → 候選板：缺 X，騎的讀圖現行，三個字抄自三題與敘事
    board = chain["board"]
    row = board["groups"]["missing"][0]
    assert row["ticker"] == TICKER and row["brief_id"] == brief.brief_id and row["watch"]["watch_id"] == chain["wait"]["watch_id"]
    assert row["rides"] == [{"node": SOCKET, "unit": "socket", "reading_id": rid, "kind": "volume", "status": "current",
                             "unit_label": "插槽", "kind_label": "B：量的賭注"}]
    assert row["three_words"]["will_it_die"].startswith("紅") and row["three_words"]["priced_in"] == "無法量"

    # 候選板 artifact → 心跳段 2：計數與三題 rollup 讀得到
    from crons.heartbeat import _candidate_lines

    lines = _candidate_lines(chain["state_dir"])
    assert "缺 X 1" in lines[0] and "可開 0" in lines[0]
    assert any(line.startswith("三題（1 檔）") and "會死嗎" in line for line in lines)

    # 讀圖＋候選＋三題 → 個股頁
    view, analyst = _page(chain)
    by_key = {line.key: line.datum for line in analyst.candidate.lines}
    assert by_key["candidate:state"].value["brief_id"] == brief.brief_id
    assert by_key["candidate:state"].value["derived"] == "missing" and by_key["candidate:priced_in"].value == "無法量"
    assert [line.datum.dependencies["reading_id"] for line in analyst.readings.lines] == [rid]
    assert [line.datum for line in analyst.three_questions.lines] == list(view.three_questions.lines)
    downside = {line.datum.value["watch_id"]: line.datum.value for line in analyst.downside.lines}
    assert brief_watch["watch_id"] in downside and reading_watch["watch_id"] in downside
    chain_para = next(p for p in view.argument.paragraphs if p.key == "argument:chain")
    assert chain_para.dependencies["demand"]["readings"][0]["reading_id"] == rid
    assert chain_para.dependencies["demand"]["basis"] == "rides", "有 v2 敘事就讀它騎的那一格，不是退回坐的層"
    assert "Ayar Labs" in chain_para.value and chain_para.value.startswith("押的"), "需求端讀騎的讀圖的需求側（具名客戶）"

    # 個股頁 artifact＋候選板 artifact＋敘事＋讀圖 → 收據（dry-run 印出、--apply 寫進暫存 log）
    from webapp.materialize import materialize_view
    from webapp.store import ArtifactStore

    av = tmp_path / "av"
    ArtifactStore(av).write(materialize_view(analyst.to_dict(), generated_at=GENERATED))
    monkeypatch.setenv("STOCKBOT_APP_ARTIFACT_DIR", str(av))
    monkeypatch.setenv("STOCKBOT_APP_STATE_DIR", str(chain["state_dir"]))
    from fetchers import gsheets

    monkeypatch.setattr(gsheets, "fetch_portfolio", lambda *, strict_operational=False, values=None: _sheet_rows())
    monkeypatch.setattr(gsheets, "read_portfolio_values", lambda *, formulas=False, sheet=None: [["symbol"]])
    cells = {"shares": {"a1": "B2", "current": "100"}, "avg_cost": {"a1": "C2", "current": "10"},
             "currency": {"a1": "F2", "current": "USD"}}
    monkeypatch.setattr(gsheets, "locate_portfolio_cells",
                        lambda requests, values=None: [dict(cells[r["column"]]) for r in requests])
    monkeypatch.setattr(gsheets, "write_portfolio_cells", lambda writes: {"written": [w["a1"] for w in writes]})
    module = _record_trade()
    module._today = lambda: TODAY
    module.TRADE_LOG = tmp_path / "trade_log.jsonl"
    trade = ["--symbol", "FRA:2DG", "--side", "buy", "--shares", "10", "--price", "10", "--currency", "USD",
             "--cash-column", "none", "--executed-at", "2026-09-30T09:00:00+02:00", "--broker", "IB",
             "--why", "鏈測試"]
    assert module.main(trade) == 0
    printed = capsys.readouterr().out
    assert brief.brief_id in printed and "推導 missing" in printed and not module.TRADE_LOG.exists(), "dry-run 不寫"
    assert module.main(trade + ["--apply"]) == 0
    receipt = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[-1])["research_receipt"]
    assert receipt["declared"]["brief_id"] == brief.brief_id
    assert receipt["declared"]["rides"][0]["result_digest"] == chain["reading"]["result_digest"]
    assert {w["watch_id"] for w in receipt["declared"]["watches"]} >= {brief_watch["watch_id"], reading_watch["watch_id"]}
    derived = receipt["derived"]
    assert derived["status"] == "available", derived.get("reason")
    assert derived["candidate"]["brief_id"] == brief.brief_id and derived["candidate"]["derived"] == "missing"
    assert len(derived["three_questions"]) == len(analyst.three_questions.lines)


# ---------------------------------------------------------------------------
# 中間一段缺席：下一段印缺席，不是空白
# ---------------------------------------------------------------------------

def test_a_missing_candidates_artifact_is_printed_as_absent_downstream(chain, monkeypatch, tmp_path) -> None:
    from crons.heartbeat import _candidate_lines
    from portfolio.research_receipt import derived_half

    empty = tmp_path / "no_state"
    lines = _candidate_lines(empty)
    assert lines and all("（" in line and "）" in line for line in lines), "心跳段 2 說讀不到，不是空白也不是 0"
    assert "候選：" not in "".join(lines)
    derived = derived_half(TICKER, today=TODAY, candidates=None, candidates_error="尚未 materialize", analyst=None,
                           analyst_error=None, held_before=True, log_only=False, company_id=SIVERS)
    assert derived["status"] == "upstream_unavailable" and "候選板 artifact 讀不到（尚未 materialize）" in derived["reason"]


def test_a_missing_reading_ledger_is_printed_as_absent_on_the_board_the_page_and_the_downside(chain, monkeypatch,
                                                                                              tmp_path) -> None:
    """讀圖 ledger 這次讀不到（整個目錄不見）：候選板那一列 rides 印 not_found、個股頁讀圖面板說還沒讀、
    鏈段說騎的已不是現行、downside 說讀圖列這次沒有——四處都說得出是哪一種沒有。"""
    import alpha.providers.candidates as cand
    from alpha.providers import structure_readings as sr

    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path / "gone")
    board = cand.load_board([TICKER], today=TODAY, holdings_loader=lambda: chain["cash_only"])
    row = board["groups"]["missing"][0]
    assert row["rides"][0]["status"] == "not_found"
    view, analyst = _page(chain)
    assert analyst.readings.absence_kind == "not_yet_recorded" and SOCKET in (analyst.readings.reason or "")
    chain_para = next(p for p in view.argument.paragraphs if p.key == "argument:chain")
    assert "已不是現行" in chain_para.value and chain_para.dependencies["demand"]["gone"]
    notes = " ".join(analyst.downside.notes)
    assert "這次沒有那一格的讀圖列" in notes and "先修讀取" in notes
