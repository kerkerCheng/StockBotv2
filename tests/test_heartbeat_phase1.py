"""Phase 1 Step 1.8 心跳改版：五段不增不減；新行在資料源缺席時印缺席分型；第一天 diff；題材門檻兩側；
pq2 逐筆的 go／不含字串等於 `GO_AUTHORIZATION`；Discord 摘要行組法；快照鍵是封閉清單且與各自的 SSOT 相等。"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from crons import heartbeat as hb

NOW = datetime(2026, 9, 25, 0, 30, tzinfo=timezone.utc)   # 台北 08:30
TODAY = NOW.astimezone().date()


# ---------------------------------------------------------------------------
# 快照與較昨變動
# ---------------------------------------------------------------------------

def test_snapshot_vocabularies_equal_their_ssot() -> None:
    from engine_b.event_watch import EXPIRY_RESOLUTION_KINDS
    from engine_b.leads import ALL_STATUSES
    from engine_b.signal_source_registry import TIERS
    from thesis.pending_lifecycle import ALLOWED_TRANSITIONS

    assert set(hb.LEAD_STATUSES) == set(ALL_STATUSES)
    assert set(hb.THESIS_STATUSES) == set(ALLOWED_TRANSITIONS)
    assert tuple(hb.SCORECARD_TIERS) == tuple(TIERS)
    assert set(hb.EXPIRY_KIND_LABELS) == set(EXPIRY_RESOLUTION_KINDS), "到期處置的每一格都要有標籤（L16）"


def test_first_day_says_there_is_no_previous_snapshot() -> None:
    values = {k: 1 for k in hb.SNAPSHOT_KEYS}
    lines = hb.snapshot_diff_lines(values, None, previous_date=None, today=TODAY)
    assert lines == ["較昨變動：尚無上一份快照（第一次產生；之後每天逐項比對，只印變了的）"]


def test_diff_prints_only_changed_keys_and_counts_the_rest() -> None:
    before = {k: 1 for k in hb.SNAPSHOT_KEYS}
    after = dict(before, **{"pq2.actionable": 3, "disproof.watching": None})
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    line = hb.snapshot_diff_lines(after, before, previous_date=yesterday, today=TODAY)[0]
    assert line.startswith("**較昨變動 2 項**")
    assert "pq2 球在你 1→3" in line and "反證在盯 1→未讀到" in line
    assert f"其餘 {len(hb.SNAPSHOT_KEYS) - 2} 項相同" in line
    older = hb.snapshot_diff_lines(before, before, previous_date="2026-09-20", today=TODAY)[0]
    assert older.startswith("較 2026-09-20 變動 0"), "中間斷了就寫出比的是哪一天"


def test_snapshot_is_written_kept_14_days_and_the_previous_one_is_found(tmp_path: Path) -> None:
    old = tmp_path / "2026-09-01.json"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(json.dumps({"values": {}}), encoding="utf-8")
    hb.write_snapshot(tmp_path, today=TODAY - timedelta(days=1), now=NOW, values={"pq2.actionable": 2})
    hb.write_snapshot(tmp_path, today=TODAY, now=NOW, values={"pq2.actionable": 5})
    assert not old.exists(), "超過 14 天的刪掉"
    previous, when = hb.load_previous_snapshot(tmp_path, today=TODAY)
    assert when == (TODAY - timedelta(days=1)).isoformat() and previous == {"pq2.actionable": 2}, "不拿今天的比今天"


def test_collect_snapshot_never_raises_and_unread_is_none(tmp_path: Path) -> None:
    values = hb.collect_snapshot(now=NOW, state_dir=tmp_path, leads_path=tmp_path / "nope.json",
                                 thesis_path=tmp_path / "nope.json", run_record_path=tmp_path / "nope.json",
                                 capture_dir=tmp_path)
    assert set(values) == set(hb.SNAPSHOT_KEYS)
    assert values["lead.parked"] is None and values["health.red"] is None and values["tier.trusted"] is None


# ---------------------------------------------------------------------------
# 段 1：備份、健康審查、invariants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status,expected", [
    (None, "method_not_applicable"),
    ({"status": "never"}, "從來沒有備份過"),
    ({"status": "invalid"}, "讀不懂"),
    ({"status": "ok", "age_days": 2, "backup_id": "b1", "drive_status": "skipped", "restore_verified": True,
      "unbacked_files": 3}, "最後 2 天前"),
    ({"status": "ok", "age_days": 9, "backup_id": "b1", "drive_status": "ok", "restore_verified": False,
      "unbacked_files": 0}, "超過 7 天"),
])
def test_backup_line_says_which_kind_of_state(monkeypatch, status, expected) -> None:
    import briefing.sources as sources

    monkeypatch.setattr(sources, "load_backup_status", lambda now=None: status)
    assert expected in hb._backup_line(now=NOW)


def _capture(tmp_path: Path, name: str, payload) -> None:
    path = tmp_path / f"{name}_{TODAY.isoformat()}.json"
    path.write_text(json.dumps({"schema": "daily-capture-v1", "payload": payload}, ensure_ascii=False),
                    encoding="utf-8")


def test_health_and_invariants_lines_read_todays_captures(tmp_path: Path) -> None:
    assert "今天沒有紀錄" in hb._health_line(now=NOW, capture_dir=tmp_path)
    assert "今天沒有紀錄" in hb._invariants_line(now=NOW, capture_dir=tmp_path)
    _capture(tmp_path, "health", {"sections": [{"title": "重複 SourceDoc", "level": "red"},
                                                {"title": "Graph schema", "level": "green"}]})
    _capture(tmp_path, "invariants", [{"check": "Identity", "status": "PASS"},
                                      {"check": "Expiry", "status": "FAIL"}])
    assert "🔴 1**：重複 SourceDoc" in hb._health_line(now=NOW, capture_dir=tmp_path)
    assert "FAIL 1**：Expiry" in hb._invariants_line(now=NOW, capture_dir=tmp_path)


# ---------------------------------------------------------------------------
# 段 3：題材掃描、pq2 逐筆、到期行、預篩
# ---------------------------------------------------------------------------

def test_theme_scan_last_date_ignores_attachments(tmp_path: Path) -> None:
    from engine_b.theme_scan import last_scan

    assert last_scan(reports_dir=tmp_path, today=TODAY) == {"date": None, "days": None, "file": None}
    for name in ("weekly_scan_2026-09-13.md", "theme_scan_2026-09-20.md",
                 "weekly_scan_2026-09-22_topic.proposal.json", "theme_scan_2026-09-21_notes.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    scan = last_scan(reports_dir=tmp_path, today=date(2026, 9, 25))
    assert scan == {"date": "2026-09-20", "days": 5, "file": "theme_scan_2026-09-20.md"}


@pytest.mark.parametrize("days,nudge", [(6, False), (7, True)])
def test_theme_scan_threshold_both_sides_and_banner(monkeypatch, days, nudge) -> None:
    import engine_b.theme_scan as ts

    monkeypatch.setattr(ts, "last_scan", lambda today=None, **k: {"date": "2026-09-18", "days": days, "file": "x"})
    line, flag = hb.theme_scan_line(now=NOW)
    assert flag is nudge and f"{days} 天" in line
    assert line.startswith("**") is nudge, "達門檻才粗體"
    text = hb.render_markdown([], now=NOW, banner=[line] if flag else [])
    assert (f"> ⚠ {line}" in text) is nudge, "達門檻時移到訊息第一行"


def test_theme_scan_never_scanned_is_a_nudge(monkeypatch) -> None:
    import engine_b.theme_scan as ts

    monkeypatch.setattr(ts, "last_scan", lambda today=None, **k: {"date": None, "days": None, "file": None})
    line, flag = hb.theme_scan_line(now=NOW)
    assert flag and "從來沒掃過" in line


def test_pq2_items_use_go_authorization_verbatim_and_cap_at_ten() -> None:
    from engine_b import todo

    items = [{"n": n, "type": "manual", "title": f"事項 {n}"} for n in range(1, 13)]
    items.append({"n": 20, "type": "watch_decision", "title": "等待到期、沒有對照到：x"})
    lines = hb._pq2_item_lines(items, todo_mod=todo)
    auth = todo.go_authorization("manual")
    assert lines[0] == f"  [1] 事項 1｜go＝{auth['go_authorizes']}｜不含：{auth['go_excludes']}"
    assert any("其餘 3 筆" in line for line in lines)
    batch = lines[-1]
    assert "watch_decision 20 在批次裡只能 drop" in batch and "--verb pending --until" in batch
    assert hb._pq2_item_lines([], todo_mod=todo) == []


def test_woken_today_counts_wakes_that_were_requeued_in_the_same_run(monkeypatch) -> None:
    """醒來後當場排回（`woken_by` 清成 null、紀錄進 `reactivations`）也是今天醒過——否則醒了印 0（L13）。
    昨天醒、今天才排回的不算今天；一個 watch 今天醒兩次只算一個。"""
    from engine_b import event_watch as ew

    today = NOW.isoformat()
    yesterday = (NOW - timedelta(days=1)).isoformat()
    watches = [
        {"watch_id": "cur", "status": "fired", "woken_by": {"at": today}},
        {"watch_id": "requeued", "status": "active", "woken_by": None,
         "reactivations": [{"at": today, "woken_by": {"at": today}}]},
        {"watch_id": "twice", "status": "active", "woken_by": {"at": today},
         "reactivations": [{"at": today, "woken_by": {"at": today}}]},
        {"watch_id": "late_requeue", "status": "active", "woken_by": None,
         "reactivations": [{"at": today, "woken_by": {"at": yesterday}}]},
        {"watch_id": "idle", "status": "active", "woken_by": None},
    ]
    monkeypatch.setattr(ew, "load_watches", lambda: {"watches": watches})
    monkeypatch.setattr(ew, "counters", lambda _d: {"fired_unconsumed": 0, "semantic_flagged": 0,
                                                    "semantic_pending_check": 0})
    assert "今日醒 3｜" in hb._watch_today_line(now=NOW)


def test_expiry_line_parts_add_up_to_the_cumulative_total() -> None:
    from engine_b import event_watch as ew

    today_iso = NOW.isoformat()
    watches = [
        {"status": "expired", "wake_lead": "L1", "expiry_resolution": {"kind": "trace_closed", "at": today_iso},
         "expired_at": today_iso},
        {"status": "expired", "wake_lead": "L2", "expiry_resolution": {"kind": "lead_already_terminal"},
         "expired_at": "2026-01-01T00:00:00+00:00"},
        {"status": "expired", "kind": "fact_verification", "hypothesis_ref": "oa_x", "expired_at": today_iso},
        {"status": "expired", "kind": ew.SEMANTIC_KIND, "source_ref": "thesis:m.md#1", "expired_at": today_iso},
        {"status": "fired", "kind": "fact_verification", "expiry_resolution": {"kind": "touched"},
         "expired_at": "2026-01-01T00:00:00+00:00"},
        {"status": "active"},
    ]
    line = hb._expiry_line(watches, now=NOW, event_watch=ew)
    assert "今日 3｜累計 5" in line
    assert "追源結案 1" in line and "lead 早已終局 1" in line and "判定已發生 1" in line
    assert "待決 watch_decision 1｜等 thesis 複查 1｜等重讀 0" in line


def test_prescreen_line_and_quota_come_from_the_run_record(tmp_path: Path) -> None:
    record = {"steps": [
        {"key": "10a_prescreen_prepare", "status": "ok"},
        {"key": "10c_prescreen_apply", "status": "ok", "summary": {
            "batch": 4, "flagged": 3, "rejected": 1, "no_text": 2, "no_fetcher": 5, "truncated": 0,
            "by_verdict": {"likely_touches": 1, "likely_unrelated": 1, "cannot_tell": 1}}},
        {"key": "07a_triage_propose", "status": "ok",
         "calls": [{"rate_limit": {"status": "allowed_warning", "rateLimitType": "five_hour", "resetsAt": 1}}]},
    ]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    lines = hb._prescreen_and_quota_lines(now=NOW, record_path=path)
    assert lines[0].startswith("預篩 4｜標旗 3（可能觸及 1／無關 1／看不出 1）｜無全文 2｜無 fetcher 5")
    assert "LLM 額度 allowed_warning" in lines[1]
    missing = hb._prescreen_and_quota_lines(now=NOW, record_path=tmp_path / "nope.json")
    assert "執行紀錄" in missing[0]


# ---------------------------------------------------------------------------
# 段 2、段 4、摘要行
# ---------------------------------------------------------------------------

def test_new_names_line_is_ordered_by_first_mention_and_only_today(monkeypatch) -> None:
    from engine_b import leads

    today_iso = NOW.isoformat()
    rows = [{"ticker": "NEWB", "first_seen": today_iso, "sample_title": "second"},
            {"ticker": "NEWA", "first_seen": (NOW - timedelta(minutes=5)).isoformat(), "sample_title": "first"},
            {"ticker": "OLD", "first_seen": "2026-09-01T00:00:00+00:00", "sample_title": "old"}]
    monkeypatch.setattr(leads, "load", lambda *a, **k: {"leads": {}})
    monkeypatch.setattr(leads, "onboard_candidates", lambda store: rows)
    line = hb._new_names_line(now=NOW, leads_path=None)
    assert "名字 2**：NEWA（first）、NEWB（second）" in line and "累計被點名但未登記 3" in line
    monkeypatch.setattr(leads, "onboard_candidates", lambda store: rows[2:])
    assert "名字 0" in hb._new_names_line(now=NOW, leads_path=None)


@pytest.mark.parametrize("nav,expected", [
    (None, "還沒有 nav_exposure"),
    ({"status": "unavailable", "failure": "ValueError", "blockers": []}, "不是「沒有持股」"),
    ({"status": "available", "buckets": {"BETA": 0.6, "ALPHA": 0.3, "CASH": 0.1}, "positions": 5,
      "largest": {"ticker": "VWRA", "nav_pct": 0.26}}, "BETA 60.0%、ALPHA 30.0%、CASH 10.0%｜最大單筆 VWRA 26.0%"),
    ({"status": "available", "buckets": {"大盤": 0.9, "槓桿": 0.1}, "positions": 2,
      "largest": {"ticker": "VWRA", "nav_pct": 0.9}}, "不是乘上倍數後的曝險"),   # AGENTS：兩個槓桿指標不得混用
])
def test_nav_line(nav, expected) -> None:
    assert expected in hb._nav_line(nav)


def test_nav_exposure_summary_is_pure_and_keeps_failures() -> None:
    from webapp.materialize import nav_exposure_summary

    summary = nav_exposure_summary({"status": "available", "buckets": {"ALPHA": 0.4}, "cash_pct": 0.1,
                                    "positions": [{"ticker": "A", "nav_pct": 0.1}, {"ticker": "B", "nav_pct": 0.3}]})
    assert summary["largest"]["ticker"] == "B" and summary["positions"] == 2
    failed = nav_exposure_summary({"status": "unavailable", "failure": "ValueError", "blockers": ["x"]})
    assert failed["status"] == "unavailable" and failed["largest"] is None and failed["blockers"] == ["x"]


def test_summary_line_flags(tmp_path: Path, monkeypatch) -> None:
    import briefing.sources as sources

    monkeypatch.setattr(sources, "load_backup_status", lambda now=None: {"status": "ok", "age_days": 9})
    leads_path = tmp_path / "leads.json"
    leads_path.write_text(json.dumps({"harvest_log": []}), encoding="utf-8")
    record = tmp_path / "run.json"
    record.write_text(json.dumps({"schedule_check": {"status": "mismatch"}, "steps": [
        {"key": "01_harvest", "status": "failed"},
        {"key": "07a_triage_propose", "kind": "llm", "status": "skipped", "reason": "executor=none"}]}),
        encoding="utf-8")
    line = hb.summary_line(now=NOW, snapshot={"pq2.actionable": 4, "disproof.touched_pending": 1, "health.red": 2},
                           run_record_path=record, leads_path=leads_path, theme_nudge=True,
                           theme_line="**距上次掃題材 9 天**（2026-09-16；門檻 7 天）")
    assert line.startswith(f"Daily {TODAY.isoformat()}｜球在你 4")
    for flag in ("harvest 沒跑", "daily 失敗 1 步", "LLM 關閉（executor=none）", "排程不一致",
                 "反證觸及待處置 1", "健康紅燈 2", "距上次掃題材 9 天", "備份過舊"):
        assert f"｜⚠ {flag}" in line, flag


def test_compose_returns_five_sections_snapshot_and_summary(tmp_path: Path) -> None:
    beat = hb.compose_heartbeat(now=NOW, state_dir=tmp_path, leads_path=tmp_path / "nope.json",
                                thesis_path=tmp_path / "nope.json", run_record_path=tmp_path / "nope.json",
                                capture_dir=tmp_path, snapshot_dir=tmp_path / "snap")
    assert [s.order for s in beat.sections] == [1, 2, 3, 4, 5]
    assert beat.sections[1].lines[0].startswith("較昨變動：尚無上一份快照")
    assert set(beat.snapshot) == set(hb.SNAPSHOT_KEYS) and beat.summary.startswith("Daily ")


def test_daily_summary_template_reads_the_heartbeat_summary_file(tmp_path: Path) -> None:
    from crons import daily_task as dt

    run = dt.DailyRun(out_dir=tmp_path, clock=lambda: NOW)
    assert run._templates()["summary"] == "每日心跳", "⑱ 沒寫出摘要行就退回固定字串"
    assert run._templates()["summary_file"].endswith(f"heartbeat_{run.date}.summary.txt")
    (tmp_path / f"heartbeat_{run.date}.summary.txt").write_text("Daily 2026-09-25｜球在你 3｜⚠ 健康紅燈 1\n",
                                                               encoding="utf-8")
    assert run._templates()["summary"] == "Daily 2026-09-25｜球在你 3｜⚠ 健康紅燈 1"


def test_theme_scan_config_is_validated(tmp_path: Path) -> None:
    from engine_b.routine_config import load_theme_scan

    path = tmp_path / "c.json"
    path.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")
    assert load_theme_scan(path) == {"nudge_after_days": 7}
    path.write_text(json.dumps({"theme_scan": {"nudge_after_days": 0}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_theme_scan(path)
    assert load_theme_scan()["nudge_after_days"] == 7, "repo 的 config 要合法"
