"""邊緣門檻的遲滯與「在門檻上」計數器（ROADMAP 2026-11-01；failure log #110 第 4 次：LYC.AX 10-22 撤、10-31 發、11-01 再撤）。

守：①撤回建議只在今天與前一次（**輸入日前一天**的判定）都判非邊緣時出現；前一次是邊緣／無法量／沒有更早的／沒讀到 → 待確認；
②翻回來不加遲滯（回放函式：有敘事時連續 K 次非邊緣 → 撤回建議；沒敘事時判邊緣 → 重寫）；
③在門檻上＝上限 ±1 家或 ±10%，只計數、不改判定；
④前一次判定用 `as_of` 重算、同一個輸入日的檔一次查完、同一個 FX 快取；同一天第二次 materialize 不被數成連續兩次；
⑤心跳、短版、閉環母體、closure-gate 讀同一格；舊 artifact 印「未算」不印 0。
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from alpha import edge as edge_mod
from alpha.edge import band_label, edge_state, not_edge_confirmed, on_threshold, replay_retraction_suggestions
from alpha.providers import edge as provider

TH = {"market_cap_max_usd": 1e10, "analyst_count_max": 12, "effective_from": "2026-09-19", "version": 1}


# ---- 純函式：帶、確認、回放 ----

def test_on_threshold_is_the_band_around_both_limits_and_does_not_change_the_state() -> None:
    assert on_threshold(market_cap_usd=9.5e9, analyst_count=13, thresholds=TH) == ["market_cap", "analyst_count"]
    assert on_threshold(market_cap_usd=7e9, analyst_count=5, thresholds=TH) == []
    assert on_threshold(market_cap_usd=None, analyst_count=11, thresholds=TH) == ["analyst_count"]
    assert on_threshold(market_cap_usd=1.1e10, analyst_count=14, thresholds=TH) == ["market_cap"]
    assert on_threshold(market_cap_usd=8.99e9, analyst_count=10, thresholds=TH) == []
    row = edge_state(market_cap_usd=1.049e10, analyst_count=10, thresholds=TH)
    assert row["state"] == "not_edge" and row["on_threshold"] == ["market_cap"]            # AMKR 10-29：帶內翻出去
    assert band_label(TH) == "分析師 11–13 家或市值 9.0B–11.0B USD"
    assert band_label(None) is None and band_label({"market_cap_max_usd": 1e10}) is None


def test_not_edge_is_confirmed_only_when_the_prior_judgment_was_also_not_edge() -> None:
    assert not_edge_confirmed({"state": "not_edge", "prior": {"state": "not_edge"}}) is True
    assert not_edge_confirmed({"state": "not_edge", "prior": {"state": "edge"}}) is False
    assert not_edge_confirmed({"state": "not_edge", "prior": {"state": "unmeasurable"}}) is False
    assert not_edge_confirmed({"state": "not_edge", "prior": None, "prior_absence": "x"}) is False
    assert not_edge_confirmed({"state": "not_edge"}) is False                              # 舊形狀：沒有 prior 鍵
    assert not_edge_confirmed({"state": "edge"}) is None and not_edge_confirmed(None) is None


def _days(start: date, states: str) -> list[tuple[date, str]]:
    words = {"E": "edge", "N": "not_edge", "U": "unmeasurable"}
    return [(date.fromordinal(start.toordinal() + i), words[s]) for i, s in enumerate(states)]


def test_replay_lyc_like_sequence_counts_suggestions_per_confirm_runs() -> None:
    """LYC.AX 10-16～11-01：邊緣 6 天、非邊緣 9 天、邊緣 1 天、非邊緣 1 天。現行（K=1）撤回 2／重寫 1；K=2 撤回 1、期末待確認。"""
    seq = _days(date(2026, 10, 16), "EEEEEE" + "NNNNNNNNN" + "E" + "N")
    k1 = replay_retraction_suggestions(seq, confirm_runs=1)
    assert [d.isoformat() for d in k1["suggestions"]] == ["2026-10-22", "2026-11-01"]
    assert [d.isoformat() for d in k1["rewrites"]] == ["2026-10-31"] and k1["pending_at_end"] is False
    k2 = replay_retraction_suggestions(seq, confirm_runs=2)
    assert [d.isoformat() for d in k2["suggestions"]] == ["2026-10-23"]
    assert [d.isoformat() for d in k2["rewrites"]] == ["2026-10-31"] and k2["pending_at_end"] is True
    k3 = replay_retraction_suggestions(seq, confirm_runs=3)
    assert [d.isoformat() for d in k3["suggestions"]] == ["2026-10-24"] and k3["pending_at_end"] is True
    assert [(s, a.isoformat(), b.isoformat()) for s, a, b in k2["runs"]][:2] == [
        ("edge", "2026-10-16", "2026-10-21"), ("not_edge", "2026-10-22", "2026-10-30")]


def test_replay_a_two_day_excursion_and_an_unmeasurable_gap() -> None:
    """AMKR 10-23～11-01：邊緣 6、非邊緣 2、邊緣 2——K=2 仍撤回一次（10-30）、K=3 完全不翻；無法量中斷連續計數。"""
    amkr = _days(date(2026, 10, 23), "EEEEEE" + "NN" + "EE")
    assert [d.day for d in replay_retraction_suggestions(amkr, confirm_runs=2)["suggestions"]] == [30]
    k3 = replay_retraction_suggestions(amkr, confirm_runs=3)
    assert k3["suggestions"] == [] and k3["rewrites"] == [] and k3["pending_at_end"] is False
    gap = _days(date(2026, 10, 1), "NUN")
    assert replay_retraction_suggestions(gap, confirm_runs=2)["suggestions"] == []       # 無法量把連續計數歸零
    assert replay_retraction_suggestions([], confirm_runs=2) == {"suggestions": [], "rewrites": [], "pending_at_end": False,
                                                                 "runs": [], "confirm_runs": 2}


# ---- provider：前一次判定（as_of）、分組、快取、失敗 ----

def _fake_states(calls: list):
    def fake(tickers, *, db_path=None, thresholds=None, as_of=None, fx_cache=None):
        calls.append((tuple(tickers), as_of, id(fx_cache)))
        prior = {"A": "not_edge", "B": "edge"}
        # 今天那一趟（as_of=None）：A 判非邊緣、輸入日 11-01；C 判邊緣。前一次那一趟照 as_of 回答。
        return {t: {"state": prior.get(t, "unmeasurable") if as_of else ("not_edge" if t == "A" else "edge"),
                    "label": "x", "reasons": [], "market_cap_usd": 1.0,
                    "analyst_count": 13 if t == "A" else 12, "as_of": as_of.isoformat() if as_of else None,
                    "inputs_as_of": as_of.isoformat() if as_of else "2026-11-01"} for t in tickers}
    return fake


def test_prior_judgments_are_read_as_of_the_day_before_the_input_day_grouped_per_day(monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(provider, "edge_states", _fake_states(calls))
    edges = {"A": {"state": "not_edge", "inputs_as_of": "2026-11-01"},
             "B": {"state": "not_edge", "inputs_as_of": "2026-10-28"},
             "C": {"state": "edge", "inputs_as_of": "2026-11-01"},
             "D": {"state": "not_edge", "inputs_as_of": "2026-11-01"}}
    cache: dict = {}
    provider.attach_prior_judgments(edges, thresholds=TH, fx_cache=cache)
    assert sorted((set(t), a) for t, a, _c in calls) == [({"A", "D"}, date(2026, 10, 31)), ({"B"}, date(2026, 10, 27))]
    assert all(c == id(cache) for _t, _a, c in calls)                                     # 同一個 FX 快取
    assert edges["A"]["prior"]["state"] == "not_edge" and edges["A"]["prior"]["as_of"] == "2026-10-31"
    assert edges["B"]["prior"]["state"] == "edge" and edges["B"]["prior_absence"] is None
    assert "prior" not in edges["C"]                                                      # 邊緣的檔不需要前一次
    assert set(edges["A"]["prior"]) == {"state", "label", "reasons", "market_cap_usd", "analyst_count", "as_of", "inputs_as_of"}


def test_prior_judgment_absence_is_written_not_swallowed(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(provider, "edge_states", boom)
    edges = {"A": {"state": "not_edge", "inputs_as_of": "2026-11-01"}, "B": {"state": "not_edge", "inputs_as_of": None}}
    provider.attach_prior_judgments(edges, thresholds=TH)
    assert edges["A"]["prior"] is None and "OperationalError" in edges["A"]["prior_absence"]
    assert edges["B"]["prior"] is None and "沒有輸入日" in edges["B"]["prior_absence"]
    assert not_edge_confirmed(edges["A"]) is False and not_edge_confirmed(edges["B"]) is False


def test_edge_states_with_prior_runs_today_then_the_prior_pass_on_one_cache(monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(provider, "edge_states", _fake_states(calls))
    out = provider.edge_states_with_prior(["A", "C"], thresholds=TH)
    assert [set(t) for t, _a, _c in calls] == [{"A", "C"}, {"A"}] and calls[0][1] is None
    assert len({c for _t, _a, c in calls}) == 1
    assert out["A"]["prior"]["state"] == "not_edge" and "prior" not in out["C"]


def test_as_of_judgment_reads_only_rows_fetched_by_that_day(tmp_path: Path) -> None:
    """同一天第二次 materialize（plan 四問④）：前一次＝輸入日前一天的列——今天的快照不算進去。"""
    from engine_c.db import _ensure_sqlite_schema

    db = tmp_path / "c.db"
    conn = sqlite3.connect(db)
    _ensure_sqlite_schema(conn)
    for day, count in (("2026-10-30", 12), ("2026-10-31", 12), ("2026-11-01", 13)):
        conn.execute("INSERT INTO financial_snapshots (ticker, snapshot_date, price, shares_outstanding, analyst_target_count, "
                     "analyst_target_mean, fetched_at) VALUES ('AXTI', ?, 100.0, 48000000, ?, 10.0, ?)", (day, count, day))
    conn.commit()
    conn.close()
    today = provider.edge_states(["AXTI"], db_path=db, thresholds=TH)["AXTI"]
    assert today["state"] == "not_edge" and today["inputs_as_of"] == "2026-11-01" and today["as_of"] is None
    prior = provider.edge_states(["AXTI"], db_path=db, thresholds=TH, as_of=date(2026, 10, 31))["AXTI"]
    assert prior["state"] == "edge" and prior["analyst_count"] == 12 and prior["inputs_as_of"] == "2026-10-31"
    edges = {"AXTI": today}
    provider.attach_prior_judgments(edges, db_path=db, thresholds=TH)
    assert edges["AXTI"]["prior"]["state"] == "edge" and not_edge_confirmed(edges["AXTI"]) is False
    series = provider.replay_edge_states(["AXTI"], start=date(2026, 10, 29), end=date(2026, 11, 1), db_path=db, thresholds=TH)
    assert [(d.day, e["state"]) for d, e in series["AXTI"]] == [(29, "unmeasurable"), (30, "edge"), (31, "edge"), (1, "not_edge")]
    with pytest.raises(ValueError):
        provider.replay_edge_states(["AXTI"], start=date(2026, 11, 2), end=date(2026, 11, 1), db_path=db, thresholds=TH)


# ---- 候選板的在門檻上名單、心跳、短版、閉環、closure-gate ----

def _entry(ticker="LYC.AX", state="not_edge", which=("analyst_count",), analysts=13, cap=8.57e9, narrated=True):
    return {"ticker": ticker, "state": state, "label": {"not_edge": "非邊緣", "edge": "邊緣"}[state],
            "analyst_count": analysts, "market_cap_usd": cap, "market_cap_label": f"{cap / 1e9:.1f}B USD",
            "which": list(which), "has_narrative": narrated}


def test_on_threshold_entries_list_the_universe_in_ticker_order_with_the_numbers() -> None:
    from alpha.candidates import on_threshold_entries, on_threshold_line

    edges = {"LYC.AX": {"state": "not_edge", "label": "非邊緣", "on_threshold": ["analyst_count"], "analyst_count": 13,
                        "market_cap_usd": 8.57e9},
             "AMKR": {"state": "edge", "label": "邊緣", "on_threshold": ["market_cap"], "analyst_count": 10,
                      "market_cap_usd": 9.79e9},
             "AXTI": {"state": "edge", "label": "邊緣", "on_threshold": [], "analyst_count": 5, "market_cap_usd": 4.8e9},
             "NONE": None}
    got = on_threshold_entries(edges, narrated={"LYC.AX"})
    assert [e["ticker"] for e in got] == ["AMKR", "LYC.AX"]
    assert got[1]["has_narrative"] is True and got[0]["has_narrative"] is False
    assert on_threshold_line(got[1]) == "LYC.AX（非邊緣；分析師 13 家）"
    assert on_threshold_line(got[0]) == "AMKR（邊緣；市值 9.8B USD）"
    assert on_threshold_entries({}, narrated=set()) == []


def _board(**over):
    from test_webapp_candidates import fake_candidates_payload

    payload = fake_candidates_payload()
    board = {k: payload[k] for k in ("groups", "side_groups", "oldest_stall_days", "narrative_rewrite", "ledger",
                                     "rollup", "universe", "today", "holdings", "no_narrative")}
    board["counts"] = dict(payload["counts"])
    board.update(over)
    return board


def test_heartbeat_counts_pending_apart_from_unmeasurable_and_prints_the_band(tmp_path: Path) -> None:
    from crons import daily_brief
    from crons import heartbeat as hb
    from webapp.materialize import build_candidates_artifact
    from webapp.store import StateArtifactStore

    from test_webapp_candidates import _ROW

    pending_open = {**_ROW, "ticker": "LYC.AX", "declared": "open", "derived": "edge_unmeasurable", "group": None,
                    "side": "edge_unmeasurable", "edge": {"state": "not_edge", "label": "非邊緣"},
                    "edge_pending": {"prior_state": "edge", "prior_inputs_as_of": "2026-10-31", "prior_absence": None},
                    "edge_note": "非邊緣待確認：…"}
    unmeasured_open = {**pending_open, "ticker": "ZZZ", "edge": {"state": "unmeasurable", "label": "邊緣無法量"},
                       "edge_pending": None, "edge_note": "邊緣無法量：缺分析師家數"}
    board = _board(side_groups={**_board()["side_groups"], "edge_unmeasurable": [pending_open, unmeasured_open]},
                   on_threshold=[_entry()], on_threshold_band="分析師 11–13 家或市值 9.0B–11.0B USD")
    board["counts"].update(edge_unmeasurable=2, not_edge_pending=1, on_threshold=1)
    c = hb.candidate_counts(board)
    assert (c["edge_unmeasurable"], c["open_unmeasurable"], c["not_edge_pending"], c["on_threshold"]) == (1, 1, 1, 1)
    StateArtifactStore(tmp_path).write(build_candidates_artifact(board))
    lines = hb._candidate_lines(tmp_path)
    assert "｜非邊緣待確認 1｜" in lines[0] and "邊緣無法量 1（其中宣告可開、不放行 1）" in lines[0]
    assert lines[1] == ("在門檻上 1（分析師 11–13 家或市值 9.0B–11.0B USD；只計數、不排序、不改門檻）："
                        "LYC.AX（非邊緣；分析師 13 家）")
    cover = daily_brief.candidate_short_lines(tmp_path)[1]
    assert "｜非邊緣待確認 1" in cover and "｜在門檻上 1" in cover
    snap = hb.collect_snapshot(now=__import__("datetime").datetime(2026, 11, 1, tzinfo=__import__("datetime").timezone.utc),
                               state_dir=tmp_path, leads_path=tmp_path / "nope.json", thesis_path=tmp_path / "nope2.json",
                               run_record_path=None, capture_dir=None)
    assert snap["candidate.not_edge_pending"] == 1 and snap["candidate.on_threshold"] == 1


def test_an_old_artifact_prints_not_computed_instead_of_zero(tmp_path: Path) -> None:
    from crons import daily_brief
    from crons import heartbeat as hb
    from webapp.materialize import build_candidates_artifact
    from webapp.store import StateArtifactStore

    board = _board()                                                   # 10-30 之前的板：沒有 on_threshold、沒有 not_edge_pending
    StateArtifactStore(tmp_path).write(build_candidates_artifact(board))
    c = hb.candidate_counts(board)
    assert c["not_edge_pending"] is None and c["on_threshold"] is None
    lines = hb._candidate_lines(tmp_path)
    assert "｜非邊緣待確認 未算｜" in lines[0] and lines[1].startswith("在門檻上：未算（候選板沒有這一格")
    assert "在門檻上" not in daily_brief.candidate_short_lines(tmp_path)[1]              # 短版：沒有就不印，不印 0


def test_closure_population_keeps_a_pending_not_edge_in_and_copies_the_flag_from_the_board() -> None:
    from alpha import closure
    from alpha.providers import closure as cprov

    f = closure.population_for
    assert f(held=False, has_thesis=False, candidate_state="pass", edge_state="not_edge", has_seat=True,
             edge_pending=True) == ("in", "not_edge_pending")
    assert f(held=False, has_thesis=False, candidate_state="pass", edge_state="not_edge", has_seat=True,
             edge_pending=False) == ("non_multiple", "not_edge")
    assert f(held=False, has_thesis=False, candidate_state="pass", edge_state="not_edge", has_seat=True) == \
        ("non_multiple", "not_edge")                                                      # 舊板沒有這一格：照舊
    payload = {"today": "2026-11-01",
               "groups": {"pass": [{"ticker": "LYC.AX", "edge": {"state": "not_edge"}, "declared": "pass",
                                    "edge_pending": {"prior_state": "edge"}}],
                          "missing": [{"ticker": "AXTI", "edge": {"state": "edge"}}]},
               "side_groups": {}, "no_narrative": [{"ticker": "AMKR", "edge": {"state": "not_edge"}}]}
    got, _day = cprov.board_inputs(payload)
    assert got["LYC.AX"]["edge_pending"] is True and got["LYC.AX"]["edge_state"] == "not_edge"
    assert got["AXTI"]["edge_pending"] is False and got["AMKR"]["edge_pending"] is False


def test_closure_gate_line_copies_the_board_and_says_not_computed_when_absent(tmp_path: Path) -> None:
    from alpha import closure
    from alpha.providers import closure as cprov
    from webapp.materialize import build_candidates_artifact
    from webapp.store import StateArtifactStore

    assert closure.render_on_threshold({"entries": None, "absence": "候選板 state 讀不到：OSError"}) == \
        ["在門檻上：未算（候選板 state 讀不到：OSError）"]
    assert closure.render_on_threshold(None)[0].startswith("在門檻上：未算（")
    assert closure.render_on_threshold({"entries": [], "band": "分析師 11–13 家或市值 9.0B–11.0B USD"})[0].startswith(
        "在門檻上 0 檔（分析師 11–13 家或市值 9.0B–11.0B USD；")
    line = closure.render_on_threshold({"entries": [_entry(), _entry("AMKR", "edge", ("market_cap",), 10, 9.79e9, False)],
                                        "band": "b"})[0]
    assert line.endswith("：LYC.AX（非邊緣；分析師 13 家）、AMKR（邊緣；市值 9.8B USD）") and "2 檔" in line
    store = StateArtifactStore(tmp_path)
    assert cprov.on_threshold_inputs(store)["entries"] is None                           # 沒有 artifact
    store.write(build_candidates_artifact(_board()))
    got = cprov.on_threshold_inputs(store)
    assert got["entries"] is None and "舊 artifact" in got["absence"]
    store.write(build_candidates_artifact(_board(on_threshold=[_entry()], on_threshold_band="b")))
    got = cprov.on_threshold_inputs(store)
    assert [e["ticker"] for e in got["entries"]] == ["LYC.AX"] and got["band"] == "b" and got["absence"] is None


def test_cli_replay_prints_counts_per_confirm_runs(monkeypatch, capsys) -> None:
    from alpha import cli

    def fake_replay(tickers, *, start, end, db_path=None, thresholds=None):
        seq = _days(start, "EENNE")
        return {t: [(d, {"state": s, "analyst_count": 13 if s == "not_edge" else 12, "market_cap_usd": 8.5e9,
                         "inputs_as_of": d.isoformat(), "on_threshold": ["analyst_count"]}) for d, s in seq] for t in tickers}

    monkeypatch.setattr(provider, "replay_edge_states", fake_replay)
    assert cli.main(["edge", "LYC.AX", "--replay", "--from", "2026-10-28", "--to", "2026-11-01"]) == 0
    out = capsys.readouterr().out
    assert "## LYC.AX" in out and "K=1：撤回建議 1（2026-10-30）／重寫 1（2026-11-01）" in out
    assert "K=2：撤回建議 1（2026-10-31）／重寫 1（2026-11-01）" in out
    assert "K=3：撤回建議 0（—）／重寫 0（—）" in out
    assert cli.main(["edge", "LYC.AX", "--replay"]) == 2                                 # 沒給 --from
    assert "--from" in capsys.readouterr().err
    assert cli.main(["edge", "LYC.AX", "--replay", "--from", "2026-10-28", "--to", "2026-11-01", "--format", "json"]) == 0
    import json

    report = json.loads(capsys.readouterr().out)
    assert report["LYC.AX"]["by_confirm_runs"]["2"]["suggestions"] == ["2026-10-31"]
    assert report["LYC.AX"]["days"][2]["on_threshold"] == ["analyst_count"]
