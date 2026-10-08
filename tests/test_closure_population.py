"""閉環母體（Phase 7 Step 7.0g-2；plan A4、failure log #22 選項②）：誰在段 5 的佇列裡、誰在母體外、母體外的怎麼回來。

守的三件事：①每一檔各自判的是非題，不跨檔比較（G2）；②讀不到就留在母體，不因為讀不到而退出（INV-3）；
③母體外不是「做完了」，要逐檔列名，邊緣沒座位那一類有到期（INV-2）。
"""
from __future__ import annotations

from datetime import date

from alpha import closure
from alpha.closure import BacklogRow
from alpha.providers import closure as provider


def _row(ticker, **kw):
    kw.setdefault("readiness", "blocked")
    kw.setdefault("open_panels", ("brief",))
    kw.setdefault("settled_panels", ())
    return BacklogRow(ticker=ticker, **kw)


# ---- population_for：真值表 ----

def test_population_truth_table() -> None:
    f = closure.population_for
    assert f(held=True, has_thesis=False, candidate_state=None, edge_state="not_edge", has_seat=False)[0] == "in"
    assert f(held=False, has_thesis=True, candidate_state=None, edge_state="not_edge", has_seat=False)[0] == "in"
    for state in ("missing", "priced_wait", "open"):
        assert f(held=False, has_thesis=False, candidate_state=state, edge_state="not_edge", has_seat=False)[0] == "in"
    assert f(held=False, has_thesis=False, candidate_state="pass", edge_state="not_edge", has_seat=True) == \
        ("non_multiple", "not_edge")
    assert f(held=False, has_thesis=False, candidate_state=None, edge_state="edge", has_seat=True) == ("in", "seat")
    assert f(held=False, has_thesis=False, candidate_state=None, edge_state="edge", has_seat=False) == \
        ("edge_no_seat", "no_supply_seat")
    assert f(held=False, has_thesis=False, candidate_state=None, edge_state="unmeasurable", has_seat=False)[0] == \
        "edge_no_seat"


def test_unreadable_inputs_keep_the_ticker_in_the_population() -> None:
    """讀不到不是「否」：邊緣判定或座位讀不到 → 留在母體（寧可多排一檔，INV-3）。"""
    f = closure.population_for
    assert f(held=None, has_thesis=None, candidate_state=None, edge_state=None, has_seat=None) == ("in", "edge_unknown")
    assert f(held=None, has_thesis=None, candidate_state=None, edge_state="edge", has_seat=None) == ("in", "seat_unknown")


def test_already_priced_is_not_a_population_rule() -> None:
    """「已定價」不設門檻（AGENTS）：等回落的候選留在母體，不因為已定價就退出。"""
    assert closure.population_for(held=False, has_thesis=False, candidate_state="priced_wait",
                                  edge_state="edge", has_seat=False)[0] == "in"


# ---- 佇列：queued ----

def test_non_multiple_never_queues_even_when_unfinished() -> None:
    row = _row("GOOGL", population="non_multiple", population_reason="非邊緣")
    assert row.terminal is None and row.queued is False
    assert closure.rank_backlog([row]) == []


def test_edge_without_seat_queues_only_when_its_short_check_is_due() -> None:
    due = _row("XFAB.PA", population="edge_no_seat", short_check_due=True)
    done = _row("6481.T", population="edge_no_seat", short_check_due=False)
    assert [r.ticker for r in closure.rank_backlog([due, done])] == ["XFAB.PA"]
    # 即使它的個股頁已經 ready，短檢查到期仍要排——「坐哪一層」和個股頁完不完整是兩件事
    assert _row("X", readiness="ready", open_panels=(), population="edge_no_seat", short_check_due=True).queued


def test_gate_and_summary_list_the_outside_by_name() -> None:
    rows = [
        _row("COHR", readiness="ready", open_panels=()),
        _row("SILEX.ST"),
        _row("GOOGL", population="non_multiple", population_reason="非邊緣：2.0 兆美元、分析師 53 位"),
        _row("6481.T", population="edge_no_seat", short_check_due=False, population_reason="上次短檢查 2026-10-05"),
        _row("XFAB.PA", population="edge_no_seat", short_check_due=True, population_reason="從沒做過短檢查"),
    ]
    gate = closure.closure_gate(rows)
    assert set(gate.actionable) == {"SILEX.ST", "XFAB.PA"}
    s = closure.summarize(rows)
    assert s["terminal_count"] == 1 and s["open_count"] == 2
    assert s["outside"]["non_multiple"] == [["GOOGL", "非邊緣：2.0 兆美元、分析師 53 位"]]
    assert s["outside"]["edge_no_seat_checked"] == [["6481.T", "上次短檢查 2026-10-05"]]
    lines = closure.render_outside(s)
    assert "非倍率 1 檔" in lines[0] and "GOOGL" in lines[0]
    assert "6481.T" in lines[1]
    assert "母體外 2" in closure.render_summary(s)


def test_outside_lines_print_even_at_zero() -> None:
    """0 也印——「沒有人退出」與「沒算」不得同形（L13）。"""
    lines = closure.render_outside(closure.summarize([_row("A")]))
    assert len(lines) == 4 and "非倍率 0 檔" in lines[0] and "已做過短檢查 0 檔" in lines[1]
    assert "等入圖 0 檔" in lines[2]                      # 2026-10-08（failure log #51）
    assert "等主題組 0 檔" in lines[3]                    # 2026-10-08（failure log #26）


# ---- 等主題組（2026-10-08，failure log #26）：組要在這條鏈第一份敘事之前定義 ----

def _pool(*items: dict) -> dict:
    return {"items": list(items)}


def test_pending_cohort_members_read_only_open_frozen_theme_cohort_specs() -> None:
    spec = {"kind": "theme_cohort", "spec": {"members": [{"ticker": "3017.tw"}, {"ticker": "3653.TW"}]}}
    pool = _pool({"n": 701, "frozen_spec": spec},
                 {"n": 650, "frozen_spec": {"kind": "theme_cohort", "spec": {"members": [{"ticker": "AXTI"}]}},
                  "resolved_at": "2026-09-30"},                                   # 已落地／已結案：不算
                 {"n": 702, "frozen_spec": {"kind": "other", "spec": {"members": [{"ticker": "X"}]}}})
    assert closure.pending_cohort_members(pool) == {"3017.TW": 701, "3653.TW": 701}


def test_awaiting_cohort_rows_are_not_queued_and_are_listed_with_their_number() -> None:
    from dataclasses import replace

    rows = [replace(_row("3017.TW"), awaiting_cohort=701), _row("AXTI")]
    assert [r.ticker for r in closure.rank_backlog(rows)] == ["AXTI"]
    summary = closure.summarize(rows)
    assert summary["awaiting_cohort"] == [["3017.TW", 701]] and summary["open_count"] == 1
    assert "3017.TW（[701]）" in closure.render_outside(summary)[3]


# ---- 等入圖（2026-10-08，failure log #51）：短檢查結論①補供貨邊、入圖包還在 pq2 ----

def test_pending_admission_focus_reads_open_ra_admissions_through_their_focus() -> None:
    focus = {"ra_a": "AAON", "ra_b": "MTRS.ST", "ra_old": "KLIC", "ra_unreadable": None, "ra_c": "XFAB.PA"}
    pool = _pool({"n": 748, "type": "ra_admission", "ref_id": "ra_a"},
                 {"n": 747, "type": "ra_admission", "ref_id": "ra_b"},
                 {"n": 760, "type": "ra_admission", "ref_id": "ra_a"},                    # 同一檔第二包：取小的
                 {"n": 700, "type": "ra_admission", "ref_id": "ra_old", "resolved_at": "2026-10-01"},   # 已結案
                 {"n": 749, "type": "ra_admission", "ref_id": "ra_unreadable"},          # 讀不到 focus：不猜
                 {"n": 750, "type": "manual", "ref_id": "ra_c"})                         # 不是入圖包
    assert closure.pending_admission_focus(pool, focus.get) == {"AAON": 748, "MTRS.ST": 747}


def test_edge_without_seat_waiting_on_its_admission_is_not_queued_and_is_listed() -> None:
    """①掛了 pq2 之後原本仍顯示「短檢查到期」→ 下一個 session 會重做同一個短檢查（5 檔同時撞到）。"""
    rows = [_row("AAON", population="edge_no_seat", short_check_due=True, awaiting_admission=748),
            _row("ENS", population="edge_no_seat", short_check_due=True)]
    assert [r.ticker for r in closure.rank_backlog(rows)] == ["ENS"]
    assert set(closure.closure_gate(rows).actionable) == {"ENS"}
    summary = closure.summarize(rows)
    assert summary["outside"]["edge_no_seat_awaiting_admission"] == [["AAON", 748]]
    assert "AAON（[748]）" in closure.render_outside(summary)[2]
    assert "等入圖 1" in closure.render_summary(summary)
    # 只認邊緣沒座位：母體內的列帶了編號也照舊排（它的出口是自己的終局，不是這一號）
    assert _row("SILEX.ST", awaiting_admission=748).queued


def test_the_narrative_writer_refuses_a_first_narrative_whose_cohort_has_not_landed(monkeypatch) -> None:
    from alpha.providers import closure as provider

    monkeypatch.setattr(provider, "_last_brief_day", lambda _t: None)
    monkeypatch.setattr("engine_b.todo.load", lambda *a, **k: _pool(
        {"n": 701, "frozen_spec": {"kind": "theme_cohort", "spec": {"members": [{"ticker": "3017.TW"}]}}}))
    assert provider.first_narrative_awaiting_cohort("3017.tw") == 701
    assert provider.first_narrative_awaiting_cohort("AXTI") is None
    # 已經寫過敘事的檔：之後的重寫不是「第一份」，不擋
    from datetime import date

    monkeypatch.setattr(provider, "_last_brief_day", lambda _t: date(2026, 10, 5))
    assert provider.first_narrative_awaiting_cohort("3017.TW") is None


def test_alpha_brief_add_stops_before_reading_the_spec(monkeypatch, tmp_path, capsys) -> None:
    """寫入端：`python -m alpha brief <T> --add` 對「第一份、組提案還在 pq2」的檔整筆拒收，什麼都不寫。"""
    from alpha import cli

    monkeypatch.setattr(provider, "first_narrative_awaiting_cohort", lambda _t: 701)
    missing_spec = tmp_path / "never_read.json"            # 不存在：拒收發生在讀 spec 之前
    assert cli.main(["brief", "AXTI", "--add", str(missing_spec)]) == 2
    assert "[701]" in capsys.readouterr().err


# ---- provider：照抄 artifact、不重算 ----

def test_board_inputs_copy_the_candidates_artifact() -> None:
    payload = {"today": "2026-10-07",
               "groups": {"held": [{"ticker": "COHR", "edge": {"state": "not_edge"}}],
                          "missing": [{"ticker": "IQE.L", "edge": {"state": "edge"}}],
                          "pass": [{"ticker": "TXN", "edge": {"state": "not_edge"}, "declared": "pass"}]},
               "side_groups": {"edge_unmeasurable": [{"ticker": "CCXI", "declared": "pass",
                                                      "edge": {"state": "unmeasurable"}}]},
               "no_narrative": [{"ticker": "XFAB.PA", "edge": {"state": "edge", "market_cap_label": "1.0B USD"}},
                                {"ticker": "OLDART"}]}
    got, day = provider.board_inputs(payload)
    assert day == "2026-10-07"
    assert got["COHR"]["held"] is True
    assert got["IQE.L"]["candidate_state"] == "missing"
    assert got["TXN"]["candidate_state"] == "pass" and got["TXN"]["edge_state"] == "not_edge"
    assert got["CCXI"]["candidate_state"] == "pass" and got["CCXI"]["edge_state"] == "unmeasurable"
    assert got["XFAB.PA"]["edge_state"] == "edge"
    assert got["OLDART"]["edge_state"] is None        # 舊 artifact 沒有 edge → None → 留在母體


def test_supply_seat_counts_only_supplies_to() -> None:
    class _Reg:
        def research_ticker(self, cid):
            return {"co:silex": "SILEX.ST", "co:google": "GOOGL", "co:dover": "DOV"}.get(cid)

    payload = {"rows": [{"company_id": "co:silex", "relation": "supplies_to"},
                        {"company_id": "co:google", "relation": "depends_on"},          # 買方，不算座位
                        {"company_id": "co:dover", "relation": "constrained_by"},
                        {"company_id": "co:private", "relation": "supplies_to"}]}
    assert provider.supply_seats(payload, _Reg()) == frozenset({"SILEX.ST"})


def test_short_check_due_after_ninety_days() -> None:
    today = date(2026, 10, 7)
    reason, due = provider.population_detail("edge_no_seat", "no_supply_seat", {}, board_day="2026-10-07",
                                             last_brief=None, today=today)
    assert due is True and "從沒做過" in reason
    reason, due = provider.population_detail("edge_no_seat", "no_supply_seat", {}, board_day="2026-10-07",
                                             last_brief=date(2026, 9, 1), today=today)
    assert due is False and "2026-11-30" in reason
    reason, due = provider.population_detail("edge_no_seat", "no_supply_seat", {}, board_day="2026-10-07",
                                             last_brief=date(2026, 6, 1), today=today)
    assert due is True and "到期重問" in reason


def test_non_multiple_reason_prints_the_number_when_the_row_has_no_label() -> None:
    """沒有敘事的列只有 market_cap_usd、沒有 label——不得印成「市值未知」（2026-10-07 真資料：002837.SZ 103 億美元）。"""
    info = {"edge": {"market_cap_usd": 10310058668.7, "analyst_count": 2}}
    reason, _due = provider.population_detail("non_multiple", "not_edge", info, board_day="2026-10-07",
                                              last_brief=None, today=date(2026, 10, 7))
    assert "10.3B USD" in reason and "市值未知" not in reason


def test_non_multiple_reason_carries_the_numbers() -> None:
    info = {"edge": {"market_cap_label": "2032.8B USD", "analyst_count": 53}}
    reason, due = provider.population_detail("non_multiple", "not_edge", info, board_day="2026-10-07",
                                             last_brief=None, today=date(2026, 10, 7))
    assert due is None and "2032.8B USD" in reason and "53" in reason and "2026-10-07" in reason
