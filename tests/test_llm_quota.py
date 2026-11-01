"""ROADMAP「週額度常駐計數器」（2026-11-01 批次三 B）：每次呼叫把**每個窗**都記下、短版 ④ 每天一行、
心跳摘要行 ≥ 門檻加旗（只印不擋）、`python -m crons.llm_quota` 讀同一個數。

事發（ROADMAP 列）：雷達 10-04 起 24 天有 8 天沒跑，其中週額度用完 2 次共 6 天——用完之前沒有任何地方看得到「快用完了」。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crons import heartbeat as hb
from crons import llm_quota, llm_step

NOW = datetime(2026, 11, 1, 3, 30, tzinfo=timezone.utc)   # 台北 11:30
TAIPEI = timezone(timedelta(hours=8))
#: 2026-11-01 探針的原樣（`rate_limit_event.rate_limit_info`）：status allowed_warning 時兩個窗都在，各自帶 status。
REAL = {"status": "allowed_warning", "resetsAt": 1793631600, "rateLimitType": "seven_day", "utilization": 0.97,
        "overageStatus": "rejected", "isUsingOverage": False, "surpassedThreshold": 0.75,
        "unifiedWindows": {"five_hour": {"utilization": 0.53, "resetsAt": 1793518200, "status": "allowed"},
                           "seven_day": {"utilization": 0.97, "resetsAt": 1793631600, "status": "allowed_warning",
                                         "surpassedThreshold": 0.75}},
        "overageEnabled": False}
#: 2026-11-01 之前的執行紀錄只記 `rateLimitType` 指的那一窗（沒有 `windows`）。
OLD = {"status": "allowed_warning", "rateLimitType": "seven_day", "utilization": 0.86, "resetsAt": 1793631600}


def _calm(seven: float, five: float = 0.1) -> dict:
    return dict(REAL, status="allowed", utilization=seven,
                unifiedWindows={"five_hour": {"utilization": five, "resetsAt": 1793518200, "status": "allowed"},
                                "seven_day": {"utilization": seven, "resetsAt": 1793631600, "status": "allowed"}})


def _rows(*limits: dict | None) -> dict:
    return {"07a_triage_propose": {"calls": [{"rate_limit": limit} for limit in limits]}}


# ---------------------------------------------------------------------------
# ① 每次呼叫把每個窗都記進執行紀錄
# ---------------------------------------------------------------------------


def test_rate_limit_records_every_window_not_only_the_one_rate_limit_type_points_at() -> None:
    limit = llm_step._rate_limit(REAL)
    assert limit["rateLimitType"] == "seven_day" and limit["utilization"] == 0.97 and limit["resetsAt"] == 1793631600
    assert limit["windows"] == {
        "five_hour": {"utilization": 0.53, "resetsAt": 1793518200, "status": "allowed"},
        "seven_day": {"utilization": 0.97, "resetsAt": 1793631600, "status": "allowed_warning"},
    }
    # 沒有 unifiedWindows 的事件：windows 是空 dict，不補一個假窗（INV-3）
    assert llm_step._rate_limit({"status": "allowed", "rateLimitType": "five_hour"})["windows"] == {}
    # 窗底下缺欄位就是 None，不補 0
    partial = llm_step._rate_limit({"status": "allowed", "rateLimitType": "five_hour",
                                    "unifiedWindows": {"five_hour": {"utilization": 0.2}}})
    assert partial["windows"] == {"five_hour": {"utilization": 0.2, "resetsAt": None, "status": None}}


def test_quota_usage_reads_the_last_reporting_call_and_falls_back_to_the_single_window_of_old_records() -> None:
    usage = hb.quota_usage(_rows(OLD, llm_step._rate_limit(REAL)))
    assert usage["windows"]["seven_day"]["utilization"] == 0.97 and usage["windows"]["five_hour"]["utilization"] == 0.53
    assert usage["legacy"] is False and usage["calls"] == 2 and usage["step"] == "07a_triage_propose"
    legacy = hb.quota_usage(_rows(OLD))
    assert legacy["legacy"] is True and set(legacy["windows"]) == {"seven_day"}
    assert legacy["windows"]["seven_day"] == {"utilization": 0.86, "resetsAt": 1793631600, "status": "allowed_warning"}
    # 沒有任何呼叫回報 → None（不是 0%）
    assert hb.quota_usage({"07a_triage_propose": {"calls": [{"status": "ok"}]}}) is None
    assert hb.quota_usage({}) is None
    # 後面的呼叫沒回報時，用量仍是最後一次**有回報**的那一次
    assert hb.quota_usage(_rows(llm_step._rate_limit(REAL), None))["windows"]["seven_day"]["utilization"] == 0.97
    # 探針走同一個函式，只是 key 不同
    fresh = hb.quota_usage({"probe": {"calls": [{"rate_limit": llm_step._rate_limit(REAL)}]}}, keys=("probe",))
    assert fresh["windows"]["seven_day"]["utilization"] == 0.97


# ---------------------------------------------------------------------------
# ② 短版 ④ 每天一行；摘要行 ≥ 門檻加旗
# ---------------------------------------------------------------------------


def test_usage_line_prints_both_windows_in_taipei_time_bold_at_threshold_and_names_absences(monkeypatch) -> None:
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: TAIPEI)
    line = hb.quota_usage_line(hb.quota_usage(_rows(llm_step._rate_limit(REAL))), now=NOW)
    assert line == "LLM 額度：**7 天 97%**（11-02 23:00 重置；≥ 80% 只印不擋）｜5 小時 53%（11-01 15:30 重置）"
    calm = hb.quota_usage_line(hb.quota_usage(_rows(llm_step._rate_limit(_calm(0.5)))), now=NOW)
    assert calm == "LLM 額度：7 天 50%（11-02 23:00 重置）｜5 小時 10%（11-01 15:30 重置）"
    legacy = hb.quota_usage_line(hb.quota_usage(_rows({"status": "allowed", "rateLimitType": "five_hour",
                                                       "utilization": 0.2, "resetsAt": None})), now=NOW)
    assert legacy == "LLM 額度：7 天 未回報（舊格式只記一窗）｜5 小時 20%（重置 ?）"
    # 缺席要說出為什麼（INV-3），不印 0%
    assert hb.quota_usage_line(None, now=NOW, record=None, record_problem="今天沒有 daily 執行紀錄（daily 沒跑）") == \
        "LLM 額度：今天沒有 daily 執行紀錄（daily 沒跑）——沒有可讀的用量"
    skipped = hb.quota_usage_line(None, now=NOW, record={"steps": [
        {"key": "07a_triage_propose", "kind": "llm", "status": "skipped", "reason": "executor=none"},
        {"key": "01c_radar_propose", "kind": "llm", "status": "skipped", "reason": "executor=none"}]})
    assert skipped == "LLM 額度：這一輪的 LLM 步驟沒有呼叫回報用量（LLM 步驟 2 步：skipped 2）"
    assert hb.quota_usage_line(None, now=NOW, record={"steps": []}) == "LLM 額度：這一輪的 LLM 步驟沒有呼叫回報用量（沒有 LLM 步驟）"


def test_flag_only_at_or_above_the_threshold_and_only_for_the_seven_day_window() -> None:
    assert hb.QUOTA_FLAG_THRESHOLD == 0.80

    def usage(seven: float | None, five: float = 0.99) -> dict:
        windows = {"five_hour": {"utilization": five, "resetsAt": None, "status": None}}
        if seven is not None:
            windows["seven_day"] = {"utilization": seven, "resetsAt": None, "status": None}
        return {"windows": windows, "legacy": False, "calls": 1, "step": "x"}

    assert hb.quota_flag(usage(0.80)) == "週額度已用 80%"
    assert hb.quota_flag(usage(0.97)) == "週額度已用 97%"
    assert hb.quota_flag(usage(0.79)) is None, "5 小時 99% 也不加旗——旗只管週額度，5 小時的印在 ④ 那一行"
    assert hb.quota_flag(usage(None)) is None and hb.quota_flag(None) is None


def test_summary_line_flags_the_week_at_threshold_and_stays_quiet_below(tmp_path: Path, monkeypatch) -> None:
    import briefing.sources as sources

    monkeypatch.setattr(sources, "load_backup_status", lambda now=None: {"ok": True})
    monkeypatch.setattr(hb, "_backup_problems", lambda status: [])
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "t2_status", lambda watches, today: {"stale": False, "last_run_days": 0})
    monkeypatch.setattr(hb, "harvest_age_hours", lambda newest, now: 1.0)
    leads_path = tmp_path / "leads.json"
    leads_path.write_text(json.dumps({"harvest_log": []}), encoding="utf-8")

    def line_for(limit: dict) -> str:
        record = tmp_path / "run.json"
        record.write_text(json.dumps({"steps": [{"key": "01c_radar_propose", "kind": "llm", "status": "ok",
                                                 "calls": [{"rate_limit": limit}]}]}), encoding="utf-8")
        return hb.summary_line(now=NOW, snapshot={"pq2.actionable": 0}, run_record_path=record, leads_path=leads_path,
                               theme_nudge=False, theme_line="")

    assert "｜⚠ 週額度已用 97%" in line_for(llm_step._rate_limit(REAL))
    assert "週額度" not in line_for(llm_step._rate_limit(_calm(0.79, five=0.99)))
    assert "｜⚠ 週額度已用 86%" in line_for(OLD), "舊格式的紀錄（只有一窗）也要能加旗"


def test_the_brief_status_block_prints_the_quota_line_every_day_even_without_a_record(tmp_path: Path, monkeypatch) -> None:
    from crons import daily_brief

    monkeypatch.setattr(hb, "watch_today_counts", lambda **_kw: {"woken": 0, "expired": 0, "semantic_flagged": 0})
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    record = tmp_path / "run.json"
    record.write_text(json.dumps({"steps": [{"key": "07a_triage_propose", "kind": "llm", "status": "ok",
                                             "calls": [{"rate_limit": llm_step._rate_limit(REAL)}]}]}), encoding="utf-8")
    text = daily_brief.compose_brief(now=NOW, summary="Daily 2026-11-01｜球在你 0", snapshot={}, run_record_path=record,
                                     leads_path=leads_path, heartbeat_dir=tmp_path, state_dir=tmp_path)
    block = text.split("### ④ 狀態與健康度", 1)[1].split("### ⑤", 1)[0]
    assert "- LLM 額度：**7 天 97%**（" in block and "5 小時 53%" in block
    missing = daily_brief.compose_brief(now=NOW, summary="Daily 2026-11-01｜球在你 0", snapshot={},
                                        run_record_path=tmp_path / "nope.json", leads_path=leads_path,
                                        heartbeat_dir=tmp_path, state_dir=tmp_path)
    block = missing.split("### ④ 狀態與健康度", 1)[1].split("### ⑤", 1)[0]
    assert "- LLM 額度：今天沒有 daily 執行紀錄" in block and "沒有可讀的用量" in block


def test_the_full_heartbeat_section_3_prints_the_usage_line_after_the_warning(tmp_path: Path, monkeypatch) -> None:
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: TAIPEI)
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"steps": [{"key": "07a_triage_propose", "status": "ok",
                                           "calls": [{"rate_limit": llm_step._rate_limit(REAL)}]}]}), encoding="utf-8")
    lines = hb.quota_lines(now=NOW, record_path=path)
    assert len(lines) == 2
    assert lines[0].startswith("⚠ **LLM 額度接近上限**（allowed_warning）") and "7 天額度已用 97%" in lines[0]
    assert lines[1] == "LLM 額度：**7 天 97%**（11-02 23:00 重置；≥ 80% 只印不擋）｜5 小時 53%（11-01 15:30 重置）"
    # 平常（allowed）只有用量那一行——警告行不是 allowed 才印
    path.write_text(json.dumps({"steps": [{"key": "07a_triage_propose", "status": "ok",
                                           "calls": [{"rate_limit": llm_step._rate_limit(_calm(0.3))}]}]}), encoding="utf-8")
    assert hb.quota_lines(now=NOW, record_path=path) == ["LLM 額度：7 天 30%（11-02 23:00 重置）｜5 小時 10%（11-01 15:30 重置）"]


# ---------------------------------------------------------------------------
# ③ CLI：互動 session 開 workflow／大量 fan-out 前讀同一個數
# ---------------------------------------------------------------------------


def _record_dir(tmp_path: Path, limit: dict | None) -> Path:
    record_dir = tmp_path / "hb"
    record_dir.mkdir()
    day = datetime.now(timezone.utc).astimezone().date().isoformat()
    steps = [{"key": "01c_radar_propose", "kind": "llm", "status": "ok", "calls": [{"rate_limit": limit}]}] if limit else []
    (record_dir / f"daily_run_{day}.json").write_text(
        json.dumps({"finished_at": "2026-11-01T06:28:40+08:00", "steps": steps}), encoding="utf-8")
    return record_dir


def test_cli_reads_todays_record_and_the_probe_reads_the_live_number_with_the_daily_argv_shape(
        tmp_path: Path, capsys, monkeypatch) -> None:
    record_dir = _record_dir(tmp_path, llm_step._rate_limit(REAL))
    assert llm_quota.main(["--record-dir", str(record_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["record_date"] == datetime.now(timezone.utc).astimezone().date().isoformat()
    assert out["usage"]["windows"]["seven_day"]["utilization"] == 0.97 and out["flag"] == "週額度已用 97%"
    assert out["threshold"] == 0.80 and "probe" not in out

    import engine_b.routine_config as routine_config

    monkeypatch.setattr(routine_config, "load_llm", lambda: {
        "cwd_path": tmp_path / "cwd", "claude_path_resolved": "C:/x/claude.exe", "claude_model": "opus",
        "claude_effort": "xhigh"})
    seen: dict = {}

    def fake_run(prompt, *, argv, cwd, env, timeout_minutes, **_kw):
        seen.update(prompt=prompt, argv=list(argv), cwd=cwd, env=env, timeout=timeout_minutes)
        outcome = llm_step.LlmOutcome(status="ok")
        outcome.rate_limit = llm_step._rate_limit(_calm(0.98, five=0.6))
        return outcome

    monkeypatch.setattr(llm_step, "run_claude", fake_run)
    assert llm_quota.main(["--record-dir", str(record_dir), "--probe", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["probe"]["status"] == "ok" and out["probe"]["usage"]["windows"]["seven_day"]["utilization"] == 0.98
    assert out["probe"]["flag"] == "週額度已用 98%"
    argv = seen["argv"]
    assert argv[argv.index("--model") + 1] == "haiku" and argv[argv.index("--effort") + 1] == "low"
    assert argv[argv.index("--tools") + 1] == "" and "--setting-sources" in argv and "--strict-mcp-config" in argv
    assert argv[argv.index("--json-schema") + 1] == llm_quota.PROBE_SCHEMA_TEXT
    assert not any(flag in argv for flag in llm_step.FORBIDDEN_LLM_FLAGS)
    assert seen["cwd"] == tmp_path / "cwd" and seen["prompt"] == llm_quota.PROBE_PROMPT and seen["timeout"] == 2.0
    assert "ANTHROPIC_API_KEY" not in seen["env"]


def test_cli_probe_that_gets_rejected_still_reports_the_windows_it_saw(tmp_path: Path, capsys, monkeypatch) -> None:
    """額度用完時 CLI 回 is_error → `rate_limited`，但 rate_limit_event 在 result 之前就到了——兩個窗照印。"""
    record_dir = _record_dir(tmp_path, None)
    import engine_b.routine_config as routine_config

    monkeypatch.setattr(routine_config, "load_llm", lambda: {
        "cwd_path": tmp_path / "cwd", "claude_path_resolved": "C:/x/claude.exe", "claude_model": "opus",
        "claude_effort": "xhigh"})

    def rejected(prompt, *, argv, cwd, env, timeout_minutes, **_kw):
        outcome = llm_step.LlmOutcome(status="rate_limited", error="is_error=True")
        outcome.rate_limit = llm_step._rate_limit(dict(REAL, status="rejected", utilization=1.0, unifiedWindows={
            "five_hour": {"utilization": 0.7, "resetsAt": 1793518200, "status": "allowed"},
            "seven_day": {"utilization": 1.0, "resetsAt": 1793631600, "status": "rejected"}}))
        return outcome

    monkeypatch.setattr(llm_step, "run_claude", rejected)
    assert llm_quota.main(["--record-dir", str(record_dir), "--probe"]) == 0
    text = capsys.readouterr().out
    assert "探針（當下）：LLM 額度：**7 天 100%**" in text and "5 小時 70%" in text
    assert "這一輪的 LLM 步驟沒有呼叫回報用量" in text        # 紀錄裡沒有 LLM 呼叫：說出來，不印 0%


def test_cli_without_any_record_says_so_and_still_exits_zero(tmp_path: Path, capsys) -> None:
    assert llm_quota.main(["--record-dir", str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert "最近 7 天沒有任何 daily 執行紀錄" in text and "沒有可讀的用量" in text and "只印不擋" in text


def test_cli_falls_back_to_the_most_recent_record_and_says_which_day(tmp_path: Path, capsys) -> None:
    record_dir = tmp_path / "hb"
    record_dir.mkdir()
    two_days_ago = (datetime.now(timezone.utc).astimezone().date() - timedelta(days=2)).isoformat()
    (record_dir / f"daily_run_{two_days_ago}.json").write_text(json.dumps({"steps": [
        {"key": "07a_triage_propose", "kind": "llm", "status": "ok", "calls": [{"rate_limit": OLD}]}]}), encoding="utf-8")
    assert llm_quota.main(["--record-dir", str(record_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["record_date"] == two_days_ago and out["usage"]["legacy"] is True and out["flag"] == "週額度已用 86%"
