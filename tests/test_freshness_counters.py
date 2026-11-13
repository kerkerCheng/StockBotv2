"""兩個「新不新」的常駐計數器（failure log #108 第 2 次；使用者 2026-11-13「照你推薦做」）。

1. daily 每一步離時限多遠：⑬ 10-31～11-11 每天用掉 77–80%，沒有一行印出來，11-12 起逾時。
2. 候選板比它讀的事件舊：11-13 00:21 物化的板子，05:52 NVIDIA 8-K 叫醒 45 條反證、⑬ 逾時沒重寫——心跳只比日期，
   短版印「可開待你選 33」，當天實際 14。
"""
from __future__ import annotations

import itertools
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alpha.providers import candidates as cand
from crons import daily_brief
from crons import daily_task as dt
from crons import heartbeat as hb
from crons.daily_task import DAILY_STEPS
from engine_b import event_watch as ew

GENERATED = datetime(2026, 11, 12, 16, 21, tzinfo=timezone.utc)          # 11-13 00:21 台北
WAKE = datetime(2026, 11, 12, 21, 52, tzinfo=timezone.utc)               # 11-13 05:52 台北
HEARTBEAT = datetime(2026, 11, 12, 22, 49, tzinfo=timezone.utc)          # 11-13 06:49 台北


def _iso(moment: datetime) -> str:
    return moment.isoformat()


# ---------------------------------------------------------------------------
# daily 紀錄：每一步記下實際用的時限
# ---------------------------------------------------------------------------

def test_each_command_step_records_the_timeout_it_ran_with(tmp_path: Path) -> None:
    from test_daily_task import _run

    run, _runner = _run(tmp_path)
    rows = {r["key"]: r for r in run.record["steps"]}
    ran = [s for s in DAILY_STEPS if rows[s.key]["status"] == "ok" and s.kind not in ("llm", "integrity")]
    assert ran and rows["13_materialize"]["status"] == "ok"
    for step in ran:
        assert rows[step.key]["timeout_seconds"] == round(dt.step_timeout_minutes(step, run.llm, run.radar) * 60, 1)
    assert rows["13_materialize"]["timeout_seconds"] == 2700.0


def test_a_step_near_the_deadline_records_the_clamped_timeout_not_the_listed_one(tmp_path: Path) -> None:
    """接近 deadline 時非必要步驟的時限被夾短——紀錄寫實際用的那個（分母錯了，「用掉幾成」就錯）。"""
    from test_daily_task import _run

    start = datetime(2026, 11, 13, 5, 30, tzinfo=timezone.utc)
    near = start + timedelta(minutes=240 - dt.essential_reserve_minutes(DAILY_STEPS) - 2)
    ticks = itertools.chain([start], itertools.repeat(near))
    run, _runner = _run(tmp_path, clock=lambda: next(ticks))
    row = next(r for r in run.record["steps"] if r["key"] == "13_materialize")
    assert row["status"] == "ok" and row["timeout_seconds"] == 120.0


# ---------------------------------------------------------------------------
# 離時限多遠（timeout_headroom）
# ---------------------------------------------------------------------------

def _record(day: str, steps: list[dict]) -> dict:
    return {"run_id": "r" * 12, "date": day, "steps": steps}


def _write(directory: Path, record: dict) -> Path:
    path = directory / f"daily_run_{record['date']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return path


def test_headroom_ranks_steps_and_names_only_ok_steps_over_the_bar(tmp_path: Path) -> None:
    _write(tmp_path, _record("2026-11-10", [{"key": "13_materialize", "seconds": 2000.0}]))
    record = _record("2026-11-11", [
        {"key": "13_materialize", "label": "APP materialize", "status": "ok", "seconds": 2160.0,
         "timeout_seconds": 2700.0},
        {"key": "16_backup", "label": "本機備份＋Drive 異地（上傳失敗 exit 3，本機照留）", "status": "ok",
         "seconds": 90.0, "timeout_seconds": 900.0},
        {"key": "01_harvest", "label": "harvest（X／EDGAR／MOPS／feeds）", "status": "timeout", "seconds": 1200.0,
         "timeout_seconds": 1200.0},
        {"key": "07a_triage_propose", "kind": "llm", "status": "skipped"},          # 沒有秒數：不算
    ])
    headroom = hb.timeout_headroom(record, record_dir=tmp_path)
    assert [r["key"] for r in headroom["rows"]] == ["01_harvest", "13_materialize", "16_backup"]
    # 逾時那一步已在失敗清單——不重複進 near
    assert [r["key"] for r in headroom["near"]] == ["13_materialize"]
    top = headroom["near"][0]
    assert (top["ratio"], top["previous"], top["source"], top["label"]) == (0.8, 2000.0, "紀錄", "APP materialize")
    assert headroom["rows"][2]["label"] == "本機備份＋Drive 異地"                     # 括號後的說明不進一行字
    line = hb.headroom_line(headroom)
    assert line.startswith("⚠ **貼近時限 1 步**（用掉 ≥ 75%，再慢就逾時）：")
    assert "APP materialize 2,160／2,700 秒＝80%（上一輪 2,000 秒）" in line


def test_an_old_record_without_the_field_falls_back_to_the_listed_timeout_and_says_so(tmp_path: Path) -> None:
    record = _record("2026-11-11", [{"key": "13_materialize", "label": "APP materialize", "status": "ok",
                                     "seconds": 966.0}])
    headroom = hb.timeout_headroom(record, record_dir=tmp_path)
    row = headroom["rows"][0]
    assert (row["timeout"], row["source"], row["previous"], headroom["near"]) == (2700.0, "清單", None, [])
    assert hb.headroom_line(headroom) == "離時限最近：APP materialize 966／2,700 秒＝36%，時限照清單"


def test_headroom_says_it_cannot_compute_instead_of_printing_nothing(tmp_path: Path) -> None:
    assert hb.timeout_headroom(None) is None
    assert hb.timeout_headroom(_record("2026-11-11", [{"key": "x", "status": "ok"}]), record_dir=tmp_path) is None
    assert hb.headroom_line(None) == "離時限：這一輪沒有一步算得出（紀錄沒有秒數或時限）"


def test_the_full_heartbeat_section_one_prints_the_headroom_every_day(tmp_path: Path) -> None:
    path = _write(tmp_path, _record("2026-11-11", [{"key": "13_materialize", "label": "APP materialize",
                                                    "status": "ok", "seconds": 966.0, "timeout_seconds": 2700.0}]))
    lines = hb._daily_run_lines(now=HEARTBEAT, record_path=path)
    assert lines[1] == "離時限最近：APP materialize 966／2,700 秒＝36%"


def test_the_summary_line_and_the_short_version_flag_the_same_step(tmp_path: Path) -> None:
    day = HEARTBEAT.astimezone().date().isoformat()
    path = _write(tmp_path, _record(day, [{"key": "13_materialize", "label": "APP materialize", "status": "ok",
                                           "seconds": 2160.0, "timeout_seconds": 2700.0}]))
    summary = hb.summary_line(now=HEARTBEAT, snapshot={"pq2.actionable": 0}, run_record_path=path,
                              leads_path=tmp_path / "nope.json", theme_nudge=False, theme_line="")
    assert "｜⚠ APP materialize 用掉時限 80%" in summary
    record, _problem = hb._load_run_record(path, now=HEARTBEAT)
    block = daily_brief.health_block(record=record, record_problem=None, quota=(), snapshot={},
                                     headroom=hb.timeout_headroom(record, record_dir=tmp_path))
    assert block[0] == "- daily 1/1 步｜最貼時限 80%（APP materialize）"
    assert block[1] == "  - ⚠ APP materialize 用掉時限 80%（2,160／2,700 秒）——再慢就逾時"
    calm = dict(record, steps=[dict(record["steps"][0], seconds=966.0)])
    assert daily_brief.health_block(record=calm, record_problem=None, quota=(), snapshot={},
                                    headroom=hb.timeout_headroom(calm, record_dir=tmp_path)) == [
        "- daily 1/1 步｜最貼時限 36%（APP materialize）｜健康度正常（invariants、健康審查無紅）"]


# ---------------------------------------------------------------------------
# 候選板比它讀的事件舊
# ---------------------------------------------------------------------------

def _watch(kind: str = ew.SEMANTIC_KIND, **fields) -> dict:
    return {"watch_id": "ew_x", "kind": kind, "status": "active", "created_at": _iso(GENERATED - timedelta(days=3)),
            **fields}


def test_board_input_events_count_only_what_the_board_reads(tmp_path: Path) -> None:
    after = _iso(GENERATED + timedelta(hours=1))
    watches = [
        _watch(woken_by={"at": _iso(WAKE)}),                                        # 語意條件醒來：算
        _watch(judgments=[{"at": after}], reactivations=[{"at": after}]),          # 判定＋判回：兩筆
        _watch(kind="trace", woken_by={"at": _iso(WAKE)}),                           # 追源：板子不讀，不算
        _watch(kind="date", source_ref="brief:AAA@x", consumed_at=after),            # 敘事來源：算
        _watch(kind="date", wake_brief="AAA", expired_at="不是時間"),                # 時間讀不到：跳過、不丟例外
    ]
    (tmp_path / "AAA.jsonl").write_text("\n".join([
        json.dumps({"created_at": _iso(GENERATED - timedelta(hours=1))}),          # 板子之前：不算
        json.dumps({"created_at": after}),
        "[]", "不是 json", "",
    ]), encoding="utf-8")
    events = cand.board_input_events(watches=watches, brief_dir=tmp_path)
    since = cand.board_inputs_since(GENERATED, until=HEARTBEAT, events=events)
    assert (since["watch"], since["brief"], since["latest"]) == (4, 1, WAKE)
    assert since["not_compared"] == ["讀圖", "Sheet 持股", "三題稽核區"]               # 沒比的照印，不讓它看起來像沒變
    assert cand.board_inputs_since(GENERATED, until=GENERATED + timedelta(minutes=30), events=events)["watch"] == 0


def test_staleness_text_tells_stale_fresh_and_unknown_apart() -> None:
    board = {"generated_at": _iso(GENERATED)}
    stale = hb.candidate_board_staleness(board, until=HEARTBEAT, events=[(WAKE, "watch")] * 45)
    assert stale["stale"] and stale["watch"] == 45
    text = hb.board_staleness_text(stale, short=True)
    when = GENERATED.astimezone().strftime("%m-%d %H:%M")
    assert text.startswith(f"⚠ **候選板比它讀的事件舊**：{when} 產生，之後反證 watch 變動 45 筆、敘事寫入 0 份")
    assert text.endswith("重跑 `python -m webapp materialize --candidates`")
    fresh = hb.candidate_board_staleness(board, until=HEARTBEAT, events=[(GENERATED - timedelta(hours=2), "brief")])
    assert not fresh["stale"] and hb.board_staleness_text(fresh, short=True) is None
    assert hb.board_staleness_text(fresh).endswith("之後它讀的反證 watch 與敘事沒變（讀圖、Sheet 持股、三題稽核區沒比）")
    # 比不了不是沒變（INV-3）：短版也照說
    assert hb.candidate_board_staleness({"generated_at": "壞掉"}) is None
    assert hb.board_staleness_text(None, short=True) == "候選板依賴比對：讀不到板子或產生時間"


def _board_state(tmp_path: Path) -> Path:
    from test_webapp_candidates import fake_candidates_payload
    from webapp.store import StateArtifactStore

    StateArtifactStore(tmp_path).write(fake_candidates_payload())                   # generated_at 2026-09-29
    return tmp_path


def test_the_short_version_and_the_snapshot_read_the_same_staleness(monkeypatch, tmp_path: Path) -> None:
    state = _board_state(tmp_path)
    kw = dict(now=HEARTBEAT, state_dir=state, leads_path=tmp_path / "nope.json", thesis_path=tmp_path / "nope2.json",
              run_record_path=None, capture_dir=None)
    calm = daily_brief.candidate_short_lines(state)
    assert calm[0].startswith("- 候選：") and hb.collect_snapshot(**kw)["candidate.board_stale_events"] == 0
    monkeypatch.setattr(cand, "board_input_events", lambda **_: [(datetime(2026, 9, 30, tzinfo=timezone.utc), "watch")])
    lines = daily_brief.candidate_short_lines(state)
    assert lines[0].startswith("- ⚠ **候選板比它讀的事件舊**") and lines[1:] == calm
    assert hb.collect_snapshot(**kw)["candidate.board_stale_events"] == 1
    assert hb._board_staleness_line(state_dir=state).startswith("⚠ **候選板比它讀的事件舊**")


def test_the_summary_line_and_the_open_choice_block_say_the_board_is_stale(tmp_path: Path) -> None:
    kw = dict(now=HEARTBEAT, run_record_path=tmp_path / "nope.json", leads_path=tmp_path / "nope.json",
              theme_nudge=False, theme_line="")
    stale = hb.summary_line(snapshot={"pq2.actionable": 0, "candidate.open_undecided": 33,
                                      "candidate.board_stale_events": 45}, **kw)
    assert "｜可開待你選 33" in stale and "｜⚠ 候選板比 45 筆事件舊（可開數是舊的）" in stale
    assert "候選板比" not in hb.summary_line(snapshot={"pq2.actionable": 0, "candidate.board_stale_events": 0}, **kw)
    block = daily_brief.open_choice_block(["- AAA"], None, stale=True)
    assert block[0].endswith("——⚠ 候選板比它讀的事件舊，這份名單可能過期（見 ④）")
    assert "過期" not in daily_brief.open_choice_block(["- AAA"], None)[0]
