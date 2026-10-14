"""人工觀測的取代／並存關係（2026-10-14 取代鏈 A；ROADMAP「人工觀測的取代鏈收多值」，使用者選 A）。

守：①一筆可以關掉多筆（`supersedes_id` 單值合併不了的兩條鏈）、as-of 看得到關係寫下之前的樣子；②「哪幾筆生效」只有一條
規則，讀取端（營收結構、基期與它的「已被取代」引用、APP 計數器、投影）都跟著它；③寫入端拒收不合法的關係，判斷欄位要 pq2；
④刻意並存留紀錄、不算重複；⑤判斷欄位的關係走同一道 Engine C 判讀寫入 gate（提案→鑄號→go→complete），drop 會把提案收掉；
⑥投影的勝出者只從生效列挑（較早記錄的那筆被留下時，投影不得留著被取代的那筆）。
測試資料用直接插入模擬真實資料裡「沒連上的舊重複」——那正是這一版要合併的形狀。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from engine_b import todo
from engine_c import pending_observations
from engine_c import manual_observations as mo

A, B, C = ("mo_" + ch * 32 for ch in "abc")


def _open(path: Path | str = ":memory:") -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _legacy(conn, oid: str, value: object, *, field: str = "fiscal_year_results", ticker: str = "AXTI",
            as_of: str = "2025-12-31T00:00:00+00:00", recorded: str = "2026-09-10 08:26:00", author: str = "xbrl_backfill",
            supersedes: str | None = None) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    conn.execute("INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, as_of, author, "
                 "supersedes_id, recorded_at, payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (oid, ticker, field, text, f"src-{oid}", as_of, author, supersedes, recorded,
                  hashlib.sha256(oid.encode()).hexdigest()))
    conn.commit()


def _three_unlinked(conn) -> None:
    _legacy(conn, A, {"currency": "USD", "revenue": 1.0})
    _legacy(conn, B, {"currency": "USD", "revenue": 1.0, "gaap": {"operating_income": -2.0}}, recorded="2026-09-10 10:41:00",
            author="claude-code")
    _legacy(conn, C, {"currency": "USD", "revenue": 1.0}, recorded="2026-09-11 09:00:00", author="session")


def test_one_record_closes_two_unlinked_chains_and_as_of_still_sees_the_old_state() -> None:
    conn = _open()
    _three_unlinked(conn)
    assert mo.live_observation_ids(conn, "AXTI", "fiscal_year_results", "2025-12-31") == [A, B, C]
    ids = mo.append_relation(conn, observation_id=B, target_ids=[A, C], relation="supersedes",
                             reason="完整版取代 xbrl 最小組合與重複的一筆", author="test")
    assert len(ids) == 2 and all(i.startswith("mr_") for i in ids)
    assert mo.live_observation_ids(conn, "AXTI", "fiscal_year_results", "2025-12-31") == [B]
    # 關係是今天寫的：as-of 十月一日時三筆都還生效（INV-6：T 以後才寫的更正在 T 時不算數）
    assert mo.live_observation_ids(conn, "AXTI", "fiscal_year_results", "2025-12-31", recorded_by="2026-10-01") == [A, B, C]
    assert mo.duplicate_live_groups(conn) == {}
    # ledger 一筆都沒改
    assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 3


@pytest.mark.parametrize("change, message", [
    (dict(relation="replaces"), "relation 未登記"),
    (dict(reason="太短"), "reason 至少"),
    (dict(author=" "), "author 必填"),
    (dict(target_ids=["mo_" + "z" * 32]), "ledger 裡沒有"),
    (dict(target_ids=[B]), "不得包含自己"),
    (dict(target_ids=[]), "至少要一個目標"),
])
def test_bad_relations_are_refused_and_nothing_is_written(change, message) -> None:
    conn = _open()
    _three_unlinked(conn)
    kwargs = dict(observation_id=B, target_ids=[A], relation="supersedes", reason="完整版取代最小組合（測試）", author="test")
    kwargs.update(change)
    with pytest.raises(mo.RelationError, match=message):
        mo.append_relation(conn, **kwargs)
    assert conn.execute("SELECT COUNT(*) FROM manual_observation_relations").fetchone()[0] == 0


def test_relations_stay_inside_one_company_and_field_and_only_between_live_rows() -> None:
    conn = _open()
    _three_unlinked(conn)
    _legacy(conn, "mo_" + "d" * 32, {"currency": "USD", "revenue": 3.0}, ticker="LITE")
    with pytest.raises(mo.RelationError, match="同一家公司同一個欄位"):
        mo.append_relation(conn, observation_id=B, target_ids=["mo_" + "d" * 32], relation="supersedes",
                           reason="跨公司不得取代（測試）", author="test")
    mo.append_relation(conn, observation_id=B, target_ids=[A], relation="supersedes", reason="完整版取代 xbrl 最小組合（測試）", author="t")
    with pytest.raises(mo.RelationError, match="已經不生效"):            # 已被取代的不得再去取代別人（會復活）
        mo.append_relation(conn, observation_id=A, target_ids=[C], relation="supersedes", reason="復活測試：已失效的不得去取代別人",
                           author="t")
    with pytest.raises(mo.RelationError, match="已經不生效"):            # 已被取代的不得再被取代一次（鏈會分岔）
        mo.append_relation(conn, observation_id=C, target_ids=[A], relation="supersedes", reason="分岔測試：已失效的不得再被取代",
                           author="t")


def test_judgment_fields_need_the_pq2_receipt_but_mechanical_fields_do_not() -> None:
    conn = _open()
    _legacy(conn, A, "原本那一句", field="backlog", author="claude-code")
    _legacy(conn, B, "錯字更正後的那一句", field="backlog", recorded="2026-09-11 09:00:00", author="claude-code")
    with pytest.raises(mo.RelationError, match="判斷欄位"):
        mo.append_relation(conn, observation_id=B, target_ids=[A], relation="supersedes", reason="錯字更正：前一筆把金額寫錯（測試）",
                           author="test")
    mo.append_relation(conn, observation_id=B, target_ids=[A], relation="supersedes", reason="錯字更正：前一筆把金額寫錯（測試）",
                       author="test", approval_ref="proposal:pr_x;pq2:[1]")
    assert mo.live_observation_ids(conn, "AXTI", "backlog", "2025-12-31") == [B]


def test_the_projection_winner_comes_from_live_rows_only() -> None:
    """AXTI runway：閘門測試列晚一天寫、內容相同——留下較早那筆時，投影不得留著被取代的測試列（以前投影不看取代鏈）。"""
    conn = _open()
    runway = {"cash_and_equivalents": 1.0, "total_debt": 0.0, "free_cash_flow_ttm": -1.0}
    _legacy(conn, A, runway, field="runway_inputs", as_of="2026-06-30T00:00:00+00:00", recorded="2026-08-05 14:22:00")
    _legacy(conn, B, {**runway, "note": "gate 驗證用"}, field="runway_inputs", as_of="2026-06-30T00:00:00+00:00",
            recorded="2026-08-06 12:45:00")
    mo.rebuild_manual_projection(conn)
    source = "SELECT source_note FROM manual_fields WHERE ticker = 'AXTI' AND field_name = 'runway_inputs'"
    assert conn.execute(source).fetchone()[0] == f"src-{B}"            # 以前：最晚記錄的勝出（閘門測試列）
    first = mo.append_relation(conn, observation_id=A, target_ids=[B], relation="supersedes",
                               reason="閘門端到端驗證的重複列，不是觀測", author="test")
    assert conn.execute(source).fetchone()[0] == f"src-{A}"
    assert mo.rebuild_manual_projection(conn) == 1 and conn.execute(source).fetchone()[0] == f"src-{A}"
    again = mo.append_relation(conn, observation_id=A, target_ids=[B], relation="supersedes",
                               reason="閘門端到端驗證的重複列，不是觀測", author="test")
    assert again == first and conn.execute("SELECT COUNT(*) FROM manual_observation_relations").fetchone()[0] == 1


def test_parallel_is_recorded_and_is_not_a_duplicate() -> None:
    conn = _open()
    _legacy(conn, A, {"currency": "TWD", "revenue": 3809054.0}, ticker="TSM")
    _legacy(conn, B, {"currency": "USD", "revenue": 121423.0}, ticker="TSM", recorded="2026-09-10 09:50:00")
    assert list(mo.duplicate_live_groups(conn)) == [("TSM", "fiscal_year_results", "2025-12-31")]
    mo.append_relation(conn, observation_id=A, target_ids=[B], relation="parallel",
                       reason="台幣報表與 20-F 美元換算：同一年度兩種表達", author="test")
    assert mo.live_observation_ids(conn, "TSM", "fiscal_year_results", "2025-12-31") == [A, B]   # 兩筆都算數
    assert mo.declared_parallel(conn, [A, B]) and mo.duplicate_live_groups(conn) == {}
    assert mo.declared_parallel(conn, [A, B], recorded_by="2026-10-01") is False             # as-of：那時還沒登記


def test_an_allow_parallel_write_leaves_a_parallel_relation() -> None:
    conn = _open()
    kw = dict(ticker="X", field_name="backlog", source_ref="s", as_of="2026-03-31", author="t")
    first = mo.append_manual_observation(conn, value="甲口徑的 backlog", **kw)
    second = mo.append_manual_observation(conn, value="乙口徑的 backlog", allow_parallel=True, **kw)
    assert mo.declared_parallel(conn, [first, second]) and mo.duplicate_live_groups(conn) == {}


def test_fundamentals_follow_relations_for_the_live_row_and_the_superseded_refs() -> None:
    from alpha.contracts import Ticker
    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    conn = _open()
    _three_unlinked(conn)
    actuals, reason = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("AXTI"))
    assert reason is None and actuals.observation_id == B                      # 以前：同幣別取最完整的、附衝突註記
    assert "同一年度有 3 筆生效觀測" in (actuals.coverage_note or "")
    mo.append_relation(conn, observation_id=B, target_ids=[A, C], relation="supersedes",
                       reason="完整版取代 xbrl 最小組合與重複的一筆", author="test")
    actuals, reason = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("AXTI"))
    assert reason is None and actuals.observation_id == B and not actuals.coverage_note   # 衝突註記消失：已宣告
    refs = {r.ref: r.quote or "" for r in actuals.evidence}
    assert f"已被 {B} 取代" in refs[f"engine_c://manual_observation/{A}"]       # 關係關掉的兩筆都還解析得到
    assert f"已被 {B} 取代" in refs[f"engine_c://manual_observation/{C}"]
    past, _ = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("AXTI"), as_of=date(2026, 10, 1))
    assert "同一年度有 3 筆生效觀測" in (past.coverage_note or "")              # as-of：那時關係還沒寫，三筆都生效


def test_a_declared_parallel_with_two_currencies_says_so_instead_of_asking_for_a_correction() -> None:
    from alpha.contracts import Ticker
    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    conn = _open()
    _legacy(conn, A, {"currency": "TWD", "revenue": 3809054.0}, ticker="TSM")
    _legacy(conn, B, {"currency": "USD", "revenue": 121423.0}, ticker="TSM", recorded="2026-09-10 09:50:00")
    _, reason = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("TSM"))
    assert "請 append 一筆 correction record" in reason
    mo.append_relation(conn, observation_id=A, target_ids=[B], relation="parallel",
                       reason="台幣報表與 20-F 美元換算：同一年度兩種表達", author="test")
    actuals, reason = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("TSM"))
    assert actuals is None and "登記過的刻意並存" in reason and "correction" not in reason


def test_the_revenue_mix_reader_uses_the_same_rule() -> None:
    from alpha.providers.revenue_mix import live_observations

    conn = _open()
    share = {"Mobile Communications": 0.522, "Edge & Cloud AI": 0.3615}
    _legacy(conn, A, {**share, "Automotive & Industrial": 0.1165}, field="segment_revenue_share", ticker="SOI.PA",
            as_of="2026-03-31T00:00:00+00:00", recorded="2026-09-04 08:27:00", author="session")
    _legacy(conn, B, {**share, "Automotive & Industrial": 0.1166}, field="segment_revenue_share", ticker="SOI.PA",
            as_of="2026-03-31T00:00:00+00:00", recorded="2026-09-04 08:27:00", author="session")
    live, conflicts = live_observations(conn, "SOI.PA")
    assert conflicts and conflicts[0]["declared_parallel"] is False and "segment_revenue_share" not in live
    mo.append_relation(conn, observation_id=B, target_ids=[A], relation="supersedes",
                       reason="更正：前一筆為了湊整把 0.1166 寫成 0.1165", author="test")
    live, conflicts = live_observations(conn, "SOI.PA")
    assert conflicts == [] and live["segment_revenue_share"][0]["observation_id"] == B
    early, early_conflicts = live_observations(conn, "SOI.PA", as_of=date(2026, 10, 1))      # 那時還沒寫關係
    assert early_conflicts and "segment_revenue_share" not in early


def test_the_counter_line_counts_declared_parallels_separately() -> None:
    from alpha import closure

    assert closure.render_duplicate_live_observations((), parallel=1)[0] == "同一期間有多筆生效觀測：0 組（另有 1 組是登記過的刻意並存，不算）"
    line = closure.render_duplicate_live_observations((("LYC.AX", "backlog", "2026-03-10", (A, B)),))[0]
    assert "1 組" in line and "observation_relations add" in line and "無法合併" not in line


@pytest.fixture
def pending_root(tmp_path, monkeypatch):
    monkeypatch.setattr(pending_observations, "PENDING_DIR", tmp_path / "pending")
    return tmp_path


def test_a_judgment_relation_goes_through_the_one_engine_c_gate(pending_root, monkeypatch, capsys) -> None:
    from engine_c import observation_relations as cli

    db = pending_root / "engine_c.db"
    seed = _open(db)
    _legacy(seed, A, "US-349.31B（錯字）", field="backlog", ticker="META", author="user")
    _legacy(seed, B, "US$349.31B", field="backlog", ticker="META", author="user", recorded="2026-09-10 08:26:01")
    seed.close()
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: _open(db))
    assert cli.main(["add", B, "--supersedes", A, "--reason", "錯字更正：US- 改成 US$"]) == 0
    assert "只建了提案" in capsys.readouterr().out
    with _open(db) as check:                                             # 提案不是寫入
        assert check.execute("SELECT COUNT(*) FROM manual_observation_relations").fetchone()[0] == 0
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    item = todo.get(pool, 1)
    assert item["type"] == "engine_c_observation" and "Engine C 取代關係：META / backlog" in item["title"]
    with pytest.raises(todo.TodoError, match="不得 bare go"):
        todo.resolve(pool, 1, "go", receipt="relations:mr_x")
    result = todo.complete_engine_c_observation(pool, 1)
    assert result["receipt"].startswith("relations:mr_")
    with _open(db) as check:
        approval = check.execute("SELECT approval_ref FROM manual_observation_relations").fetchone()[0]
        assert approval.startswith("proposal:pr_") and ";pq2:[1]" in approval
        assert mo.live_observation_ids(check, "META", "backlog", "2025-12-31") == [B]
    assert pending_observations.read(item["ref_id"])["state"] == "applied"


def test_dropping_a_relation_proposal_closes_it_so_sync_does_not_remint(pending_root, monkeypatch) -> None:
    db = pending_root / "engine_c.db"
    seed = _open(db)
    _legacy(seed, A, "一句", field="backlog", ticker="MP", author="claude-code")
    _legacy(seed, B, "同一件事的 JSON", field="backlog", ticker="MP", author="claude-code", recorded="2026-09-11 09:00:00")
    record = pending_observations.propose_relation(seed, observation_id=B, target_ids=[A], relation="supersedes",
                                                   reason="JSON 版取代文字版（測試）", author="t")
    seed.close()
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    todo.resolve(pool, 1, "drop", reason="兩筆都留著")
    assert pending_observations.read(record["proposal_id"])["state"] == "dropped"
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    assert todo.active_items(pool) == []


def test_a_proposal_is_checked_before_a_number_is_minted(pending_root) -> None:
    conn = _open(pending_root / "engine_c.db")
    _legacy(conn, A, "一句", field="backlog", author="t")
    with pytest.raises(pending_observations.ProposalError, match="ledger 裡沒有"):
        pending_observations.propose_relation(conn, observation_id=A, target_ids=["mo_" + "9" * 32], relation="supersedes",
                                              reason="不存在的目標（測試）", author="t")
    assert list(pending_observations.iter_pending()) == []
