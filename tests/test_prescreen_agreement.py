"""語意判定的「預篩 vs 互動」一致率（盲點修法 plan 2026-11-02-001 §1 第 6 條；INV-5：先量測後放閘）。

叫醒判定（`judge_wake`）早就附當時的預篩 verdict、量「預篩判無關」準不準；語意判定（`judge`）沒有——478 筆判定、0 筆記了
預篩說什麼，預篩準不準從沒量過。守的事：①`judge` 記下叫醒它的那一則的標旗 verdict（別則的舊標旗不算、沒標記 None）；
②一致率逐格數：一致、預篩說觸及判無關、預篩說無關判觸及、看不出、沒標旗；③更早的判定只在現存標旗正是叫醒那一則、
而且標在判定之前時對回去，另計「對回去」幾筆；④counters 印一行。"""
from __future__ import annotations

from datetime import date

from engine_b import event_watch as ew

from test_semantic_watch import _fresh, _lead, _semantic


def _fired(data, lead_id="L1", *, flag=None, source_n=1):
    watch = _semantic(data, source_ref=f"thesis:thesis/sivers_v4_lane_memo.md#{source_n}",
                      disproof_ref=f"thesis:thesis/sivers_v4_lane_memo.md#{source_n}")
    ew.check_watches(data, leads={lead_id: _lead()}, today=date(2026, 9, 25))
    assert watch["status"] == "fired" and watch["woken_by"]["lead_id"] == lead_id
    if flag is not None:
        watch["semantic_flag"] = {"lead_id": flag[0], "at": "2026-09-25T07:00:00+00:00", "verdict": flag[1]}
    return watch


def test_judge_records_the_verdict_of_the_lead_that_woke_it() -> None:
    data = _fresh()
    no = _fired(data, flag=("L1", "likely_unrelated"))
    assert ew.judge(data, no["watch_id"], touches=False, note="只是股權變動")["prescreen_verdict"] == "likely_unrelated"
    data = _fresh()
    yes = _fired(data, flag=("L1", "likely_touches"))
    judgment = ew.judge(data, yes["watch_id"], touches=True, note="量產了", quote="entered volume production")
    assert judgment["prescreen_verdict"] == "likely_touches"


def test_a_flag_for_another_lead_or_no_flag_is_recorded_as_none() -> None:
    data = _fresh()
    stale = _fired(data, flag=("L0", "likely_touches"))                       # 上一次別則叫醒時標的
    assert ew.judge(data, stale["watch_id"], touches=False, note="無關")["prescreen_verdict"] is None
    data = _fresh()
    bare = _fired(data)
    assert ew.judge(data, bare["watch_id"], touches=False, note="無關")["prescreen_verdict"] is None


def _judged(verdict, touches, *, at="2026-11-02T00:00:00+00:00", lead="L1"):
    entry = {"at": at, "touches": touches, "lead_id": lead, "note": "n"}
    if verdict != "absent":
        entry["prescreen_verdict"] = verdict
    return entry


def test_agreement_counts_every_cell() -> None:
    watches = [{"kind": ew.SEMANTIC_KIND, "judgments": [_judged("likely_unrelated", "no"),     # 一致
                                                         _judged("likely_touches", "no"),       # 說觸及、判無關
                                                         _judged("likely_touches", "no"),       # （兩個方向數字不同才分得出對調）
                                                         _judged("cannot_tell", "no"),
                                                         _judged(None, "no")]},                  # 判定時沒有標旗
               {"kind": ew.SEMANTIC_KIND, "judgment": _judged("likely_unrelated", "yes")},       # 說無關、判觸及
               {"kind": ew.SEMANTIC_KIND, "judgment": _judged("likely_touches", "yes")},         # 一致
               {"kind": "date", "judgments": [_judged("likely_touches", "no")]},                 # 不是語意型
               {"kind": ew.SEMANTIC_KIND, "judgments": [_judged("likely_touches", "no", at="2026-09-01T00:00:00+00:00")]}]
    c = ew.prescreen_agreement({"watches": watches}, today=date(2026, 11, 3))
    assert (c["judged"], c["agreed"], c["said_touches_judged_no"], c["said_unrelated_judged_yes"],
            c["cannot_tell"], c["unflagged"], c["backfilled"]) == (7, 2, 2, 1, 1, 1, 0)


def test_older_judgments_are_matched_to_the_surviving_flag_only_when_it_is_theirs() -> None:
    flag = {"lead_id": "L1", "at": "2026-11-01T00:00:00+00:00", "verdict": "likely_unrelated"}
    mine = {"kind": ew.SEMANTIC_KIND, "semantic_flag": flag, "judgments": [_judged("absent", "no")]}
    other_lead = {"kind": ew.SEMANTIC_KIND, "semantic_flag": dict(flag, lead_id="L9"),
                  "judgments": [_judged("absent", "no")]}
    flagged_after = {"kind": ew.SEMANTIC_KIND, "semantic_flag": dict(flag, at="2026-11-02T05:00:00+00:00"),
                     "judgments": [_judged("absent", "no")]}
    c = ew.prescreen_agreement({"watches": [mine, other_lead, flagged_after]}, today=date(2026, 11, 3))
    assert (c["judged"], c["agreed"], c["unflagged"], c["backfilled"]) == (3, 1, 2, 1)


def test_counters_prints_the_line(monkeypatch, capsys) -> None:
    data = {"schema_version": 1, "watches": [
        {"watch_id": "ew_1", "kind": ew.SEMANTIC_KIND, "status": "active", "expires": "2027-01-01",
         "judgments": [_judged("likely_touches", "no", at="2026-11-02T00:00:00+00:00")]}]}
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: data)
    monkeypatch.setattr(ew, "primary_coverage", lambda: frozenset())
    monkeypatch.setattr(ew, "_today", lambda: date(2026, 11, 3))
    assert ew.main(["counters"]) == 0
    out = capsys.readouterr().out
    assert "預篩 vs 互動（近 30 天語意判定 1 筆）" in out and "**不一致 1**" in out
