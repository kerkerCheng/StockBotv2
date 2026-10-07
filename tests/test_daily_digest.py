"""每日摘要與 Discord 那一則（2026-10-07 使用者指示：「心跳太雜……Lead 抓了哪些 TL;DR、Websearch 大事件 TL;DR、
幾件事待我決定、健康度」「心跳沒有不能跑 LLM，必要就跑」）。

守的事：①LLM 只寫兩段 TL;DR，每一句都要指得回這一輪的 lead——指不回去的整句丟、照數（INV-3、L18）；②資料只來自 lead 與
雷達收據，不讀持股（哨兵）；③LLM 沒產生時短版照發、說出為什麼、退回程式組的內容（L13）；④待你決定、健康度、下一次研究
都是程式組的計數，0 也印、讀不到印「未讀到」（L14、INV-3）；⑤額度的重置時間印排程時區。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine_b import digest

NOW = datetime(2026, 10, 7, 21, 40, tzinfo=timezone.utc)          # 台北 10-08 05:40
TODAY = NOW.astimezone().date()


def _lead(lid, *, seen, status="pending", source="x:jukan05", title="某則貼文", triage_at=None, refs=None,
          source_class="secondary"):
    lead = {"lead_id": lid, "first_seen": seen.isoformat(), "source": source, "status": status, "title": title,
            "raw_text": "正文" * 300, "refs": refs or {}, "published_at": None, "source_class": source_class}
    if triage_at is not None:
        lead["triage"] = {"decision": "go" if status == "triaged_go" else "no_go", "decided_at": triage_at.isoformat(),
                          "reason": "碰到散熱 CDU 那一層"}
    return lead


def _store():
    return {"leads": {
        "lead_new": _lead("lead_new", seen=NOW - timedelta(hours=3)),
        "lead_old_triaged": _lead("lead_old_triaged", seen=NOW - timedelta(days=9), status="triaged_go",
                                  triage_at=NOW - timedelta(hours=2)),
        "lead_old": _lead("lead_old", seen=NOW - timedelta(days=3)),
        "lead_radar": _lead("lead_radar", seen=NOW - timedelta(hours=1), source="web_radar:cooling",
                            refs={"radar_fact": "LG 與 AIR 簽冷水機長約", "radar_scope": "market", "radar_why": "機房冷卻長約化"}),
    }}


# ---- prepare ----

def test_this_rounds_leads_are_new_or_just_triaged_and_nothing_older() -> None:
    picked = {lead["lead_id"] for lead in digest.select_leads(_store(), now=NOW)}
    assert picked == {"lead_new", "lead_old_triaged", "lead_radar"}


def test_prepare_reads_leads_and_the_radar_receipt_and_never_holdings(tmp_path, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise AssertionError("每日摘要讀了持股／Sheet")

    import fetchers.gsheets as gsheets
    import portfolio.holdings as holdings

    monkeypatch.setattr(gsheets, "fetch_portfolio", boom)
    monkeypatch.setattr(holdings, "resolve_holdings", boom)
    receipt = {"accepted": [{"lead_id": "lead_radar", "scope": "market", "title": "LG lands deal", "fact": "LG 簽約",
                             "why": "長約化", "publisher": "JoongAng"}]}
    (tmp_path / f"radar_{TODAY.isoformat()}.json").write_text(json.dumps(receipt), encoding="utf-8")
    out = tmp_path / "batch.json"
    summary = digest.prepare("run-1", out, now=NOW, store=_store(), receipt_dir=tmp_path)
    assert summary == {"leads_total": 3, "leads_given": 3, "internal_total": 0, "radar_items": 1, "radar_receipt": True}
    request = json.loads(out.read_text(encoding="utf-8"))["requests"][0]
    row = next(r for r in request["leads"] if r["lead_id"] == "lead_old_triaged")
    assert row["triage"] == {"decision": "go", "reason": "碰到散熱 CDU 那一層"}
    assert len(row["excerpt"]) <= digest.EXCERPT_CHARS + 1
    assert request["radar"][0]["scope"] == "market"
    from crons import llm_step

    prompt = llm_step.compose_digest_prompt([request])
    assert llm_step.DATA_START in prompt and "lead_ids" in prompt


def test_an_empty_round_writes_an_empty_batch_so_the_model_is_not_called(tmp_path) -> None:
    out = tmp_path / "batch.json"
    digest.prepare("run-1", out, now=NOW, store={"leads": {}}, receipt_dir=tmp_path)
    assert json.loads(out.read_text(encoding="utf-8"))["requests"] == []


# ---- apply ----

def _files(tmp_path, bullets, *, run="run-1"):
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"schema": digest.BATCH_SCHEMA, "run_id": run, "requests": [
        {"leads": [{"lead_id": "lead_a"}, {"lead_id": "lead_b"}], "radar": [{"lead_id": "lead_r"}],
         "leads_total": 2, "leads_given": 2}]}), encoding="utf-8")
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"schema": "llm-result-v1", "run_id": run, "sessions": ["s1"],
                                  "bullets": bullets}), encoding="utf-8")
    return result, batch


def test_every_kept_sentence_points_back_to_this_rounds_leads(tmp_path) -> None:
    bullets = [
        {"section": "leads", "text": "富世達：法說說 Rubin 快接頭認證中", "lead_ids": ["lead_a"]},
        {"section": "events", "text": "LG 拿到冷水機多年期長約", "lead_ids": ["lead_r"]},
        {"section": "events", "text": "憑空的一句", "lead_ids": ["lead_ghost"]},          # 指不回去
        {"section": "leads", "text": "沒有引用", "lead_ids": []},                       # 沒有根據
        {"section": "gossip", "text": "段別不對", "lead_ids": ["lead_a"]},
        {"section": "leads", "text": "長" * (digest.MAX_TEXT_CHARS + 1), "lead_ids": ["lead_b"]},
    ]
    result, batch = _files(tmp_path, bullets)
    out = digest.apply(result, batch, "run-1", out_dir=tmp_path, today=TODAY)
    s = out["summary"]
    assert (s["proposed"], s["kept"], s["unknown_ref"], s["invalid"], s["too_long"]) == (6, 2, 1, 2, 1)
    saved = digest.load_digest(TODAY, out_dir=tmp_path)
    assert [b["text"] for b in saved["leads"]] == ["富世達：法說說 Rubin 快接頭認證中"]
    assert saved["events"][0]["lead_ids"] == ["lead_r"] and "提議" in saved["note"]


def test_each_section_has_a_cap_and_extra_sentences_are_counted(tmp_path) -> None:
    bullets = [{"section": "events", "text": f"第 {i} 件", "lead_ids": ["lead_r"]} for i in range(5)]
    result, batch = _files(tmp_path, bullets)
    s = digest.apply(result, batch, "run-1", out_dir=tmp_path, today=TODAY)["summary"]
    assert s["kept"] == digest.SECTION_CAPS["events"] and s["over_cap"] == 5 - digest.SECTION_CAPS["events"]


def test_old_files_are_refused_and_a_missing_digest_reads_as_none(tmp_path) -> None:
    result, batch = _files(tmp_path, [], run="run-old")
    with pytest.raises(ValueError, match="run_id"):
        digest.apply(result, batch, "run-1", out_dir=tmp_path, today=TODAY)
    assert digest.load_digest(TODAY, out_dir=tmp_path) is None
    (tmp_path / f"digest_{TODAY.isoformat()}.json").write_text('{"schema": "something-else"}', encoding="utf-8")
    assert digest.load_digest(TODAY, out_dir=tmp_path) is None


def test_the_daily_wires_the_digest_as_one_zero_tool_call() -> None:
    from crons import daily_task, llm_step

    step = next(s for s in daily_task.DAILY_STEPS if s.key == "11c_digest_propose")
    assert step.llm_task == "digest" and step.requires == "11b_digest_prepare"
    assert daily_task.max_llm_calls(step, {"triage_chunk_size": 30}) == 1
    schema = json.loads(llm_step.DIGEST_SCHEMA.read_text(encoding="utf-8"))
    item = schema["properties"]["bullets"]["items"]
    assert schema["additionalProperties"] is False and set(item["required"]) == {"section", "text", "lead_ids"}
    assert item["properties"]["section"]["enum"] == list(digest.SECTIONS)


# ---- Discord 那一則 ----

def test_the_brief_prints_the_llm_sentences_when_there_are_some(tmp_path) -> None:
    from crons.daily_brief import events_block, leads_block

    saved = {"leads": [{"text": "富世達：快接頭認證中", "lead_ids": ["lead_a"]}],
             "events": [{"text": "LG 拿到冷水機長約", "lead_ids": ["lead_r"]}]}
    todays = [_lead("lead_a", seen=NOW), _lead("lead_r", seen=NOW, source="web_radar:cooling")]
    lines = leads_block(digest=saved, todays=todays, digest_problem=None)
    assert lines[0] == "**① Lead 抓了什麼**（外面新進 2 則：X 帳號 1、外部雷達 1）"
    assert lines[1] == "- 富世達：快接頭認證中"
    # ② 有收據就列收據收下的每一則（2026-10-08 起），不用 LLM 的「市場大事」那幾句
    receipt = {"summary": {"searches": 11, "new": 1, "new_market": 1, "new_theme": 0, "new_watch": 0},
               "accepted": [{"scope": "market", "title": "LG lands deal", "fact": "LG 與 AIR 簽冷水機長約", "lead_id": "lead_r"}]}
    lines = events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None)
    assert "雷達搜 11 次、收 1 則——市場 1" in lines[0] and lines[1] == "- [市場] LG 與 AIR 簽冷水機長約"
    assert "LG 拿到冷水機長約" not in "\n".join(lines)


def test_without_a_digest_the_brief_says_why_and_falls_back_to_program_content() -> None:
    from crons.daily_brief import events_block, leads_block

    todays = [_lead("lead_a", seen=NOW, status="triaged_go", title="穩懋 CW 雷射代工量產")]
    lines = leads_block(digest=None, todays=todays, digest_problem="LLM 摘要今天沒產生（11c rate_limited）")
    assert "11c rate_limited" in lines[1] and lines[2] == "- 穩懋 CW 雷射代工量產"
    receipt = {"summary": {"searches": 9, "new": 1, "new_market": 1},
               "accepted": [{"scope": "market", "title": "LG lands deal", "fact": "LG 簽冷水機長約"}]}
    lines = events_block(digest=None, receipt=receipt, digest_problem="沒產生", radar_problem=None)
    assert lines[-1] == "- [市場] LG 簽冷水機長約"
    lines = events_block(digest=None, receipt=None, digest_problem="沒產生", radar_problem="01c rate_limited")
    assert "沒有收據：01c rate_limited" in lines[0] and lines[-1] == "- 今天沒有收下任何一則"


def test_market_events_list_every_item_the_radar_took_say_what_it_left_and_flag_a_likely_repeat() -> None:
    """2026-10-08 使用者：「tldr 只有三則，但你說收四則……如果沒收但想讓我知道的就再註明」。真實那天：收 4 則（LLM 摘要只寫 3 句，
    其中一句是前一天收的台積電）、沒收 1 則（Sivers 股東會通知，lead 已有同一網址）、LG 冷水機合約前一天換個網址收過。"""
    from crons.daily_brief import events_block

    receipt = {"summary": {"searches": 34, "new": 4, "new_market": 2, "new_theme": 2, "new_watch": 0},
               "accepted": [
                   {"scope": "market", "title": "Google signs 3.6GW deal with Constellation", "fact": "Google 與 Constellation 簽 3.6GW"},
                   {"scope": "market", "title": "LG Electronics Secures Supply Agreement to Advance AI Data Center Cooling Business",
                    "fact": "LG 與 AIR 簽冷水機多年期供應協議"},
                   {"scope": "theme", "title": "奇鋐9月營收首破200億大關 連3月創新高", "fact": "奇鋐 9 月營收 210.18 億元"},
                   {"scope": "theme", "title": "Agility Robotics & Fort Robotics Expand Partnership", "fact": "Agility 與 FORT 擴大合作"}],
               "rejected": [{"url": "https://www.sivers-semiconductors.com/press/notice-egm", "reason": "duplicate"}]}
    recent = [{"title": "AIR AND LG SUPPLY AGREEMENT AIMS TO ADVANCE AI DATA CENTER COOLING BUSINESS IN NORTH AMERICA",
               "_date": "2026-10-07"},
              {"title": "TSMC hits another record but Nvidia and Apple demand may become its next problem", "_date": "2026-10-07"}]
    digest_saved = {"events": [{"text": "台積電 2 奈米訂單上調", "lead_ids": ["lead_tsmc_yesterday"]}]}
    lines = events_block(digest=digest_saved, receipt=receipt, digest_problem=None, radar_problem=None, recent_accepted=recent)
    assert "收 4 則" in lines[0] and "沒收 1 則" in lines[0] and "收下的都進 lead" in lines[0]
    body = lines[1:]
    assert len([x for x in body if x.startswith("- [")]) == 4                       # 收下的每一則都列
    assert not any("台積電" in x for x in body)                                       # 前一天收的不會被夾進來
    lg = next(x for x in body if "LG" in x)
    assert "可能跟 10-07 收過的是同一件事" in lg
    assert not any("可能跟" in x for x in body if "Google" in x or "奇鋐" in x)        # 不像的不標
    assert body[-1].startswith("- 沒收：") and "lead 裡已經有這個網址" in body[-1]
    receipt["rejected"][0]["lead_id"] = "lead_sivers"
    titled = events_block(digest=None, receipt=receipt, digest_problem=None, radar_problem=None,
                          lead_titles={"lead_sivers": "Sivers 臨時股東會通知"})
    assert titled[-1] == "- 沒收：Sivers 臨時股東會通知——lead 裡已經有這個網址"


def test_health_folds_the_quota_into_one_line_and_names_other_failures() -> None:
    from crons.daily_brief import health_block

    record = {"steps": [
        {"key": "01c_radar_propose", "status": "rate_limited", "label": "外部雷達提議"},
        {"key": "07a_triage_propose", "status": "rate_limited", "label": "分類提議"},
        {"key": "16_backup", "status": "failed", "exit": "1", "label": "本機備份＋Drive 異地",
         "stderr_tail": "Traceback…\nStateFileError: 不安全的 raw evidence 引用"},
        {"key": "13_materialize", "status": "ok"},
    ]}
    quota = [{"status": "rejected", "status_words": "已用完", "window_words": " 5 小時", "used_text": "已用 100%",
              "reset_text": "10-08 07:40", "steps": ["01c_radar_propose", "07a_triage_propose"]}]
    lines = health_block(record=record, record_problem=None, quota=quota, snapshot={"invariants.fail": 0})
    assert lines[0] == "- 健康度：2 個問題"
    assert "10-08 07:40 重置——這一輪沒跑：外部雷達、分類" in lines[1]
    assert lines[2] == "  - ⚠ 本機備份＋Drive 異地：failed（exit 1；StateFileError: 不安全的 raw evidence 引用）"
    ok = health_block(record={"steps": [{"key": "a", "status": "ok"}, {"key": "b", "status": "skipped"}]},
                      record_problem=None, quota=[], snapshot={})
    assert ok == ["- 健康度：正常（daily 1/2 步 ok；invariants、健康審查無紅）"]


def test_a_quota_warning_does_not_hide_a_real_failure_and_does_not_claim_the_steps_were_skipped() -> None:
    """2026-10-08 真實那天：額度 68%（allowed_warning，照跑），T2 輪詢 5 次呼叫 1 次逾時——舊版把逾時併進額度那行、還寫「這一輪沒跑」，
    使用者問「看起來還有額度，但為啥你說 error」。"""
    from crons.daily_brief import health_block

    record = {"steps": [
        {"key": "01c_radar_propose", "status": "ok", "label": "外部雷達提議"},
        {"key": "10e_poll_propose", "status": "timeout", "label": "T2 輪詢提議", "error": "超過 3 分鐘",
         "calls": [{"status": "ok"}, {"status": "ok"}, {"status": "ok"}, {"status": "ok"}, {"status": "timeout"}]},
        {"key": "10g_poll_apply", "status": "skipped", "label": "T2 輪詢套用", "reason": "llm_not_ok：10e_poll_propose 沒有成功"},
    ]}
    quota = [{"status": "allowed_warning", "status_words": "接近上限", "window_words": " 7 天", "used_text": "已用 68%",
              "reset_text": "10-12 23:00", "steps": ["01c_radar_propose", "10e_poll_propose"]}]
    lines = health_block(record=record, record_problem=None, quota=quota, snapshot={})
    assert lines[0] == "- 健康度：2 個問題"
    assert "這一輪照跑" in lines[1] and "這一輪沒跑" not in lines[1]
    assert lines[2].startswith("  - ⚠ T2 輪詢提議：timeout（超過 3 分鐘；5 次呼叫：ok 4、timeout 1；任一次沒過整步不寫結果）")
    assert lines[2].endswith("——連帶跳過：T2 輪詢套用")


def test_the_research_counters_print_zero_and_say_when_they_could_not_be_read() -> None:
    """AGENTS：「未 triage N」「未檢 N」必印（L13）——字照 AGENTS 寫，0 也印，讀不到印「未讀到」不印 0。"""
    from crons.daily_brief import TODO_COUNTERS, todo_block

    snapshot = {key: 0 for key, _label in TODO_COUNTERS}
    snapshot["lead.pending"] = 102
    snapshot["semantic.pending_check"] = None
    line = todo_block(snapshot)[1]
    assert "未 triage 102" in line and "未檢 未讀到" in line and "讀圖該重讀 0" in line


def test_status_lines_always_print_the_basic_counters_even_on_a_quiet_day() -> None:
    """2026-10-07 使用者：「daily 心跳基本重要的 status 還是要印」——④ 的上半每天都印：daily 步數、較昨變動、
    心跳自己的候選／watch 行、反證與加碼條件（快照同一份數字，L16）。讀不到的格印「未讀到」，不印 0（INV-3）。"""
    from crons.daily_brief import disproof_line, status_lines

    record = {"steps": [{"key": "a", "status": "ok"}, {"key": "b", "status": "skipped"}, {"key": "c", "status": "failed"}]}
    lines = status_lines(record=record, diff_lines=["較昨變動 0（120 項都相同）"],
                         status=["候選：可開 0｜缺 X 2（最老 3 天）", "watch：今日醒 0｜今日到期 0"])
    assert lines == ["- daily 1/3 步完成｜跳過 1｜沒完成 1", "- 較昨變動 0（120 項都相同）",
                     "- 候選：可開 0｜缺 X 2（最老 3 天）", "- watch：今日醒 0｜今日到期 0"]
    assert status_lines(record=None, diff_lines=[], status=[]) == []      # 沒有紀錄：健康度那一行會說，這裡不編數字
    line = disproof_line({"disproof.watching": 41, "disproof.touched_pending": 0, "disproof.expired_pending": 2,
                          "disproof.unwatched": None, "confirm.watching": 3, "confirm.touched_pending": 0})
    assert line == ("反證：在盯 41｜**觸及待處置 0**｜到期待複查 2｜未盯 未讀到｜加碼條件 在盯 3／觸及 0")


def test_the_brief_prints_the_status_block_and_each_line_degrades_alone(tmp_path, monkeypatch) -> None:
    """compose_brief 的 ④：標題固定是「狀態與健康度」；候選板讀不到時只有那一行說讀不到，watch／反證照印（各自降級）。"""
    from crons import daily_brief
    from crons import heartbeat as hb

    def broken(_state_dir):
        raise OSError("candidates artifact gone")

    monkeypatch.setattr(hb, "_candidate_lines", broken)
    monkeypatch.setattr(hb, "_watch_today_line", lambda **_kw: "watch：今日醒 1｜今日到期 0")
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    text = daily_brief.compose_brief(now=datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc), summary="Daily 2026-10-08｜球在你 0",
                                     snapshot={"disproof.watching": 5}, run_record_path=tmp_path / "missing.json",
                                     leads_path=leads_path, heartbeat_dir=tmp_path,
                                     diff_lines=["較昨變動 1 項：反證在盯 4→5"])
    block = text.split("**④ 狀態與健康度**", 1)[1].split("**⑤", 1)[0]
    assert "- 較昨變動 1 項：反證在盯 4→5" in block
    assert "- 候選：讀不到（OSError）" in block
    assert "- watch：今日醒 1｜今日到期 0" in block
    assert "- 反證：在盯 5｜**觸及待處置 未讀到**" in block
    assert "- 無到期的等待 0" in block
    assert "- 今天第一次被點名、registry 沒有的名字 0｜累計被點名但未登記 0" in block   # 命令提示不進短版
    assert "onboard-candidates" not in block
    assert "今天沒有 daily 執行紀錄" in block


def test_decisions_reuse_the_heartbeat_list_and_say_none_when_empty() -> None:
    from crons.daily_brief import decisions_block
    from engine_b import todo

    assert decisions_block(actionable=[], problem=None, todo_mod=todo) == ["**③ 待你決定**（0）", "- 沒有"]
    item = {"n": 715, "type": "ra_admission", "title": "InP 磊晶片層建層"}
    lines = decisions_block(actionable=[item], problem=None, todo_mod=todo)
    assert lines[0] == "**③ 待你決定**（1）" and lines[1].startswith("- [715] InP 磊晶片層建層｜go＝")
    assert "批次回覆" in lines[-1]
    assert "讀不到" in decisions_block(actionable=None, problem="OSError", todo_mod=todo)[0]


def test_the_decisions_end_with_one_copyable_line_built_from_the_recommendations_on_the_items() -> None:
    """2026-10-08 使用者：「待我決定的批次回覆 一樣就要給我單行可複製建議的操作」。建議是鑄號的 session 寫在編號上的，
    daily 只照抄；沒寫建議的另列、不進那一行；watch_decision 的 go／pending 進不了批次。"""
    from crons.daily_brief import decisions_block
    from engine_b import todo

    items = [
        {"n": 736, "type": "manual", "title": "載板鏈對照組", "recommendation": {"verb": "go", "reason": "日東紡敘事要先有對照組"}},
        {"n": 739, "type": "ra_admission", "title": "分接開關層補華明", "recommendation": {"verb": "go", "reason": "供給側 0→1"}},
        {"n": 741, "type": "manual", "title": "舊題目", "recommendation": {"verb": "drop", "reason": "pool 現值已無對應（todo list 查過）"}},
        {"n": 742, "type": "manual", "title": "沒寫建議的"},
        {"n": 743, "type": "watch_decision", "title": "到期", "recommendation": {"verb": "pending", "reason": "等 Q3"}},
    ]
    lines = decisions_block(actionable=items, problem=None, todo_mod=todo)
    assert "｜建議 go：日東紡敘事要先有對照組" in lines[1]
    assert lines[-1] == "- 建議（鑄號時寫的；可直接複製）：`736 739 go 741 drop`"
    assert any(x.startswith("- 沒寫建議：[742]、[743]") for x in lines)
    assert not any("批次回覆" in x for x in lines)


def test_the_quota_reset_time_is_printed_in_the_schedule_timezone(monkeypatch) -> None:
    """daily 傳進心跳的 now 是 UTC；重置時間要印台北（排程時區），不跟著 now 走——2026-10-07 前印成「10-06 23:40」。"""
    from crons import heartbeat as hb
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    rows = {"07a_triage_propose": {"calls": [{"rate_limit": {"status": "rejected", "rateLimitType": "five_hour",
                                                            "utilization": 1, "resetsAt": 1791330000}}]}}
    entry = hb.quota_entries(rows, now=NOW)[0]
    expected = datetime.fromtimestamp(1791330000, timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
    assert entry["reset_text"] == expected and entry["steps"] == ["07a_triage_propose"]


def test_the_heartbeat_writes_the_brief_and_falls_back_to_the_summary_if_it_breaks(tmp_path, monkeypatch) -> None:
    from crons import daily_brief
    from crons import heartbeat as hb

    def broken(**_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(daily_brief, "compose_brief", broken)
    out = tmp_path / "brief.md"
    assert hb.main(["--out", str(tmp_path / "hb.md"), "--brief-out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("Daily ") and "短版組不出來：RuntimeError" in text


def test_our_own_research_topics_are_counted_but_never_summarised(tmp_path) -> None:
    """2026-10-07 第一輪試跑：①有兩句在講我們自己登記的研究題（拆層、指定研究），那不是今天抓到的新東西。
    外部來的一定帶 `source_class`；研究題沒有——只計數、不送給 LLM、短版另列一個數。"""
    from crons.daily_brief import leads_block

    store = _store()
    store["leads"]["lead_topic"] = _lead("lead_topic", seen=NOW - timedelta(hours=2), source="decompose:aibio",
                                         status="triaged_go", source_class=None)
    out = tmp_path / "batch.json"
    summary = digest.prepare("run-1", out, now=NOW, store=store, receipt_dir=tmp_path)
    assert summary["internal_total"] == 1 and summary["leads_total"] == 3
    request = json.loads(out.read_text(encoding="utf-8"))["requests"][0]
    assert "lead_topic" not in {r["lead_id"] for r in request["leads"]}
    lines = leads_block(digest=None, todays=digest.select_leads(store, now=NOW), digest_problem="沒產生")
    assert "外面新進 3 則" in lines[0] and "另有我們自己登記的研究題 1 則，不摘要" in lines[0]
    assert all("lead_topic" not in line for line in lines)


def test_processing_line_counts_what_we_did_in_the_window() -> None:
    """2026-10-07 使用者：「Lead 抓了什麼 我們做了哪些處理的數字也要印」——分類（go／no-go、LLM／互動）、
    研究到終局（轉移紀錄在窗內轉到入圖包／已入圖／停放）、還沒分類、待深挖；窗外的不算。"""
    from crons.daily_brief import processing_line

    recent = (NOW - timedelta(hours=3)).isoformat()
    old = (NOW - timedelta(days=3)).isoformat()

    def tri(decision, at, who, by=None):
        return {"decision": decision, "decided_at": at, "decided_by": by, "classification": {"classified_by": who}}

    store = {"leads": {
        "a": {"status": "triaged_go", "triage": tri("go", recent, "triage_semantic_v1", by="claude-p:s1")},
        "b": {"status": "triaged_no_go", "triage": tri("no_go", recent, "interactive:directed")},
        "c": {"status": "triaged_no_go", "triage": tri("no_go", old, "triage_semantic_v1", by="claude-p:s0")},
        "i": {"status": "triaged_no_go", "triage": tri("no_go", recent, "triage_semantic_v1", by="harvest:auto_no_go_forms")},
        "d": {"status": "parked", "triage": tri("go", old, "llm:daily"),
              "transitions": [{"at": recent, "from": "triaged_go", "to": "parked"}]},
        "e": {"status": "action_prepared", "triage": tri("go", old, "llm:daily"),
              "transitions": [{"at": old, "from": "triaged_go", "to": "researching"},
                              {"at": recent, "from": "researching", "to": "action_prepared"}]},
        "f": {"status": "parked", "transitions": [{"at": old, "from": "triaged_go", "to": "parked"}]},
        "g": {"status": "pending"}, "h": {"status": "pending"},
    }}
    line = processing_line(store, now=NOW)
    assert line == ("- 處理：分類 3（go 1／no-go 2；LLM 1／互動 1／機械或舊資料 1）｜研究到終局 2（入圖包 1／已入圖 0／停放 1）"
                    "｜還沒分類 2｜待深挖 1")


def test_the_brief_puts_document_requests_in_their_own_block(tmp_path, monkeypatch) -> None:
    """③ 只列要你決定的；向你要文件在 ③b，寫明提供文件才算 go，不在批次 go 的例子裡。"""
    from crons import daily_brief
    from crons import heartbeat as hb
    from engine_b import todo

    pool = todo.empty_pool()
    todo.sync(pool, [{"type": "ra_admission", "ref_id": "ra_x", "title": "InP 磊晶片層建層"},
                     {"type": "source_trace_review", "ref_id": "lead_doc", "title": "向你要文件：全新光電券商報告"}])
    monkeypatch.setattr(todo, "load", lambda *a, **k: pool)
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    text = daily_brief.compose_brief(now=NOW, summary="Daily｜球在你 1｜等你給文件 1", snapshot={},
                                     run_record_path=tmp_path / "missing.json", leads_path=leads_path,
                                     heartbeat_dir=tmp_path)
    decisions = text.split("**③ 待你決定**", 1)[1].split("**③b", 1)[0]
    documents = text.split("**③b 等你提供的文件**", 1)[1].split("**④", 1)[0]
    assert "InP 磊晶片層建層" in decisions and "全新光電" not in decisions
    assert "全新光電券商報告" in documents and "提供文件才算 go" in documents and "drop" in documents
    assert "- 處理：" in text.split("**② 市場大事**", 1)[0]
