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
    from engine_b import impact as im

    empty = im.Context(briefs=[], readings={}, watches=[], companies={}, shared=frozenset(), node_names={})
    summary = digest.prepare("run-1", out, now=NOW, store=_store(), receipt_dir=tmp_path, impact_context=lambda: empty)
    assert summary == {"leads_total": 3, "leads_given": 3, "internal_total": 0, "radar_items": 1, "radar_receipt": True,
                       "impact_touched": 0, "impact_candidates": 0, "impact_truncated": 0, "impact_error": None}
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
    digest.prepare("run-1", out, now=NOW, store={"leads": {}}, receipt_dir=tmp_path, impact_context=lambda: _ctx_ns([]))
    assert json.loads(out.read_text(encoding="utf-8"))["requests"] == []


# ---- 影響對照（雷達精進 C2，2026-10-21）----

def _ctx_ns(briefs):
    from types import SimpleNamespace as NS

    return NS(briefs=[NS(ticker=t, slots=tuple(NS(key=k, text=v) for k, v in slots)) for t, slots in briefs])


def _row(lead_id, *, narratives=None, watches=(), readings=None, absence=None):
    return {"lead_id": lead_id, "narratives": narratives or {}, "readings": readings or {}, "absence_kind": absence,
            "watches": [{"watch_id": w, "role": role, "condition": f"{w} 的條件原文"} for w, role in watches],
            "hub_entities": [], "hub_only_counts": {}, "language_gap": False}


def _fake_impact(monkeypatch, rows):
    from engine_b import impact as im

    monkeypatch.setattr(im, "impact", lambda lead, ctx: rows[str(lead["lead_id"])])


BRIEFS_NS = [("8996.TW", (("demand", "最大客戶是 Bloom Energy"), ("our_bet", "賭熱交換器"))), ("FORM", (("demand", "HBM 探針卡"),))]


def test_candidates_follow_a_fixed_order_radar_first_then_disproof_confirm_own_slot_rides_and_are_capped(monkeypatch) -> None:
    """次序是固定規則、不是分數：雷達收下的先 → 反證 → 加碼條件 → 公司本身 → 某一格具名 → 只靠騎讀圖。"""
    rows = {"lead_new": _row("lead_new", narratives={"FORM": ["rides:tech:hbm"], "8996.TW": ["slot:demand<co:bloom>"]},
                             watches=[("ew_2", "加碼條件"), ("ew_1", "反證")]),
            "lead_radar": _row("lead_radar", narratives={"8996.TW": ["own"]})}
    _fake_impact(monkeypatch, rows)
    leads = [_store()["leads"]["lead_new"], _store()["leads"]["lead_radar"]]
    _rows, cands, cut = digest.impact_bundle(leads, {"lead_radar"}, _ctx_ns(BRIEFS_NS))
    assert [(c["lead_id"], c["target"]) for c in cands] == [
        ("lead_radar", "8996.TW#our_bet"),                         # 雷達收下的先；本身 → 附「我們的賭注」那一格
        ("lead_new", "ew_1"), ("lead_new", "ew_2"),               # 反證先於加碼條件
        ("lead_new", "8996.TW#demand"), ("lead_new", "FORM#demand")]   # 某一格具名先於只靠騎
    assert cands[3]["text"] == "最大客戶是 Bloom Energy" and cands[1]["text"] == "ew_1 的條件原文" and cut == 0
    monkeypatch.setattr(digest, "IMPACT_CAP", 2)
    _rows, cands, cut = digest.impact_bundle(leads, {"lead_radar"}, _ctx_ns(BRIEFS_NS))
    assert len(cands) == 2 and cut == 3
    # 沒交給 LLM 的 lead（超過 MAX_LEADS）照算對照列、不出候選——沒給原文就沒得逐字引用
    rows_all, cands, _ = digest.impact_bundle(leads, set(), _ctx_ns(BRIEFS_NS), eligible={"lead_radar"})
    assert len(rows_all) == 2 and {c["lead_id"] for c in cands} == {"lead_radar"}


def test_one_lead_touching_many_watches_does_not_eat_the_cap_each_lead_takes_turns(monkeypatch) -> None:
    """10-21 試跑：一則雷達新聞碰到 8 條反證，照純次序會吃掉 15 對的一半——改成每則輪流取。"""
    rows = {"lead_new": _row("lead_new", watches=[(f"ew_{i}", "反證") for i in range(5)]),
            "lead_radar": _row("lead_radar", watches=[("ew_9", "反證"), ("ew_8", "加碼條件")])}
    _fake_impact(monkeypatch, rows)
    leads = [_store()["leads"]["lead_new"], _store()["leads"]["lead_radar"]]
    _rows, cands, _ = digest.impact_bundle(leads, set(), _ctx_ns(BRIEFS_NS))
    assert [c["target"] for c in cands[:4]] == ["ew_0", "ew_9", "ew_1", "ew_8"]


def test_prepare_writes_the_impact_file_and_a_broken_context_does_not_block_the_digest(tmp_path, monkeypatch) -> None:
    rows = {"lead_new": _row("lead_new", watches=[("ew_1", "反證")]), "lead_old_triaged": _row("lead_old_triaged", absence="untouched"),
            "lead_radar": _row("lead_radar", absence="hub_only")}
    _fake_impact(monkeypatch, rows)
    out = tmp_path / "batch.json"
    s = digest.prepare("run-1", out, now=NOW, store=_store(), receipt_dir=tmp_path, impact_context=lambda: _ctx_ns(BRIEFS_NS))
    assert (s["impact_touched"], s["impact_candidates"], s["impact_error"]) == (1, 1, None)
    doc = digest.load_impact(TODAY, out_dir=tmp_path)
    assert doc["counts"] == {"leads": 3, "narratives": 0, "readings": 0, "watches": 1, "hub_only": 1, "untouched": 1,
                             "language_gap": 0}
    request = json.loads(out.read_text(encoding="utf-8"))["requests"][0]
    assert request["impact_candidates"][0]["target"] == "ew_1" and request["impact_cap"] == digest.IMPACT_CAP

    def broken():
        raise RuntimeError("讀圖壞了")

    s = digest.prepare("run-2", out, now=NOW, store=_store(), receipt_dir=tmp_path, impact_context=broken)
    assert s["impact_error"].startswith("RuntimeError") and s["leads_given"] == 3
    assert digest.load_impact(TODAY, out_dir=tmp_path)["error"].startswith("RuntimeError")
    assert json.loads(out.read_text(encoding="utf-8"))["requests"][0]["impact_candidates"] == []


def _impact_files(tmp_path, impacts):
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"schema": digest.BATCH_SCHEMA, "run_id": "run-1", "requests": [{
        "leads": [{"lead_id": "lead_a", "title": "Kaori wins  Bloom order", "excerpt": "高力 拿到 Bloom 的熱交換器訂單…"}],
        "radar": [{"lead_id": "lead_r", "title": "LG lands chiller deal", "fact": "LG 簽冷水機長約"}],
        "impact_candidates": [{"lead_id": "lead_a", "target": "8996.TW#demand"}, {"lead_id": "lead_r", "target": "ew_1"}],
        "impact_truncated": 2, "leads_total": 1, "leads_given": 1}]}), encoding="utf-8")
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"schema": "llm-result-v1", "run_id": "run-1", "bullets": [], "impacts": impacts}),
                      encoding="utf-8")
    return result, batch


def test_an_impact_sentence_is_kept_only_for_a_given_pair_with_a_verbatim_quote(tmp_path) -> None:
    """L15：LLM 不得自己配新的對；L18：quote 必須是交給它的原文逐字片段（空白正規化）；不合的照數。"""
    ok = {"lead_id": "lead_a", "target": "8996.TW#demand", "verdict": "may_touch", "quote": "Kaori wins Bloom order",
          "sentence": "最大客戶加單，需求格的集中度更高"}
    impacts = [
        ok,
        {**ok, "sentence": "同一對第二句"},                                                         # 重複
        {**ok, "target": "8996.TW#position"},                                                        # 不在候選
        {"lead_id": "lead_r", "target": "ew_1", "verdict": "may_touch", "quote": "LG 簽下冷水機", "sentence": "x"},  # 改過字
        {**ok, "lead_id": "lead_r", "target": "ew_1", "quote": "LG lands", "verdict": "maybe"},     # 字彙外
        {**ok, "sentence": "長" * (digest.IMPACT_SENTENCE_CHARS + 1), "target": "ew_1", "lead_id": "lead_r",
         "quote": "chiller deal"},
        {"lead_id": "lead_r", "target": "ew_1", "verdict": "unrelated", "quote": "LG 簽冷水機長約", "sentence": "講冷水機"},
    ]
    result, batch = _impact_files(tmp_path, impacts)
    s = digest.apply(result, batch, "run-1", out_dir=tmp_path, today=TODAY)["summary"]["impact"]
    assert (s["proposed"], s["kept"], s["invalid"], s["unknown_pair"], s["quote_not_verbatim"], s["too_long"]) == (7, 2, 2, 1, 1, 1)
    assert s["candidates"] == 2 and s["truncated"] == 2
    saved = digest.load_digest(TODAY, out_dir=tmp_path)
    assert [(i["lead_id"], i["verdict"]) for i in saved["impacts"]] == [("lead_a", "may_touch"), ("lead_r", "unrelated")]


def test_the_heartbeat_file_lists_every_touched_lead_with_the_proposal_and_its_quote(tmp_path) -> None:
    from crons.heartbeat import _impact_lines

    assert _impact_lines(now=NOW, out_dir=tmp_path) == ["影響對照：今天沒有對照檔（⑪b 沒跑或讀不到）"]
    doc = {"schema": digest.IMPACT_SCHEMA, "error": None, "counts": {"leads": 2, "watches": 1, "untouched": 1},
           "rows": [{**_row("lead_r", watches=[("ew_1", "反證")]), "title": "LG chiller"}, _row("lead_q", absence="untouched")]}
    digest.impact_path(TODAY, out_dir=tmp_path).write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / f"digest_{TODAY.isoformat()}.json").write_text(json.dumps({"schema": digest.DIGEST_SCHEMA, "impacts": [
        {"lead_id": "lead_r", "target": "ew_1", "verdict": "unrelated", "sentence": "講冷水機", "quote": "LG"}],
        "summary": {"impact": {"kept": 1, "candidates": 1}}}), encoding="utf-8")
    lines = _impact_lines(now=NOW, out_dir=tmp_path)
    assert lines[0].startswith("影響對照：外部 2 則裡") and lines[1] == "lead_r｜LG chiller"
    assert "  ↳ 提議［unrelated］（ew_1）：講冷水機｜原文「LG」" in lines and not any("lead_q" in x for x in lines)


def test_the_daily_passes_the_impacts_list_through_and_the_schema_matches_the_vocabulary() -> None:
    from crons import llm_step

    schema = json.loads(llm_step.DIGEST_SCHEMA.read_text(encoding="utf-8"))
    item = schema["properties"]["impacts"]["items"]
    assert set(item["properties"]["verdict"]["enum"]) == set(digest.IMPACT_VERDICTS)
    assert set(item["required"]) == {"lead_id", "target", "verdict", "quote", "sentence"}
    import inspect

    from crons import daily_task

    assert '"side_lists": ("impacts",)' in inspect.getsource(daily_task.DailyRun._llm_task)


def test_the_brief_prints_one_line_per_radar_item_with_what_happened_after() -> None:
    """2026-10-22 使用者：「可不可以短一點 讓我知道你有在做事就好 我怕的是撈進來然後什麼也沒發生」——每則一行
    「事實首句 → 處置｜LLM 看過的結果」，判「無關」的不再藏起來（藏了就只看得到碰到、看不到後來）。"""
    from crons.daily_brief import events_block, impact_total_line

    receipt = {"summary": {"new": 2}, "accepted": [{"lead_id": "lead_r", "scope": "market", "fact": "LG 簽冷水機長約"},
                                                   {"lead_id": "lead_q", "scope": "theme", "fact": "沒碰到的一則"}]}
    impact = {"counts": {"leads": 5, "narratives": 1, "readings": 0, "watches": 1, "hub_only": 1, "untouched": 3},
              "rows": [{**_row("lead_r", narratives={"AAON": ["slot:demand<co:lg>"], "X": ["own"], "Y": ["rides:a"], "Z": ["own"]},
                               watches=[("ew_1", "反證")]),
                        "hub_entities": ["co:nvidia"], "hub_only_counts": {"narratives": 12, "watches": 3}},
                       _row("lead_q", absence="untouched")]}
    saved = {"events": [], "impacts": [
        {"lead_id": "lead_r", "target": "ew_1", "verdict": "may_touch", "sentence": "冷水機長約化碰到反證第 1 條"},
        {"lead_id": "lead_r", "target": "AAON#demand", "verdict": "unrelated", "sentence": "不相關"}],
        "summary": {"impact": {"kept": 2, "candidates": 4, "truncated": 0, "unknown_pair": 1}}}
    lines = events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None, impact=impact,
                         lead_states={"lead_r": "triaged_go", "lead_q": "triaged_no_go"})
    # 2026-10-28 排版：一則一項「事實 → 處置」（go 寫成 ⑤ 的格名「待深挖」），下一行小字是 LLM 看過的結果
    assert lines[0] == "### ② 市場大事"
    assert lines[2] == "- LG 簽冷水機長約 → 待深挖"
    assert lines[3] == "-# LLM 提議：可能碰到 在盯條件 ew_1；無關 1 格；判定在研究時做"
    assert lines[4] == "- 沒碰到的一則 → 篩掉" and lines[5] == "-# 沒碰到我們"
    assert not any("↳" in x or "go 的已算進" in x for x in lines)           # 細節在完整心跳段 3，不在短版
    assert impact_total_line(impact, saved) == ("- 對照：外部 5 則裡碰到敘事 1、讀圖 0、在盯條件 1 則；只經樞紐 1、沒碰到 3"
                                                "｜LLM 提議 2 句（候選 4 對、丟 1）")
    many = [{"lead_id": "lead_r", "target": f"ew_{i}", "verdict": "unclear", "sentence": f"第 {i} 句"} for i in range(4)]
    capped = events_block(digest={**saved, "impacts": many}, receipt=receipt, digest_problem=None, radar_problem=None,
                          impact=impact)
    assert capped[2:4] == ["- LG 簽冷水機長約 → lead 不在", "-# LLM 提議：看不出 4 格"]
    blind = events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None, impact=None)
    assert blind[5] == "-# 影響對照今天沒跑（不是沒碰到）"                    # 沒跑 ≠ 沒碰到（INV-3）
    assert impact_total_line(None, saved).startswith("- 對照：今天沒有對照檔")
    assert "沒算出來" in impact_total_line({"error": "RuntimeError: x"}, None)
    assert impact_total_line(impact, None).endswith("｜LLM 提議：摘要今天沒產生")


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
    lines = leads_block(digest=saved, todays=todays, since=NOW - timedelta(hours=digest.WINDOW_HOURS), digest_problem=None)
    assert lines[:2] == ["### ① Lead 抓了什麼", "-# 外面新進 2（X 帳號 1、外部雷達 1）"]
    assert lines[3:5] == ["**今天的重點**", "- 富世達：快接頭認證中"] and lines[-1].startswith("-# 重點是 LLM 寫的摘要")
    # ② 有收據就列收據收下的每一則（2026-10-08 起），不用 LLM 的「市場大事」那幾句
    receipt = {"summary": {"searches": 11, "new": 1, "new_market": 1, "new_theme": 0, "new_watch": 0},
               "accepted": [{"scope": "market", "title": "LG lands deal", "fact": "LG 與 AIR 簽冷水機長約", "lead_id": "lead_r"}]}
    lines = events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None)
    assert lines[1] == "-# 雷達搜 11 次、收 1 則（市場 1、主題 0、在盯 0）" and lines[2].startswith("- LG 與 AIR 簽冷水機長約 →")
    assert "LG 拿到冷水機長約" not in "\n".join(lines)
    # 過去兩週每天收幾則（2026-10-28：一天只收 1 則，只看今天看不出是不是異常）——低於區間多一個 ⚠，只印不判
    low = events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None, baseline=(4, 8))
    assert low[1].endswith("｜⚠ 過去兩週每天收 4–8 則")
    assert events_block(digest=saved, receipt=receipt, digest_problem=None, radar_problem=None,
                        baseline=(1, 3))[1].endswith("）｜過去兩週每天收 1–3 則")


def test_the_radar_baseline_reads_the_past_receipts_and_does_not_invent_a_range(tmp_path) -> None:
    from crons.daily_brief import radar_baseline

    assert radar_baseline(tmp_path, TODAY) is None                                   # 一份都沒有：不編區間
    for back, new in ((1, 6), (2, 4), (9, 9)):
        day = TODAY - timedelta(days=back)
        (tmp_path / f"radar_{day.isoformat()}.json").write_text(json.dumps({"summary": {"new": new}}), encoding="utf-8")
    (tmp_path / f"radar_{TODAY.isoformat()}.json").write_text(json.dumps({"summary": {"new": 0}}), encoding="utf-8")
    assert radar_baseline(tmp_path, TODAY) == (4, 9)                                 # 今天自己不算進基準


def test_radar_fact_is_not_cut_at_a_thousands_separator() -> None:
    """2026-10-28：「收窄為 1,350 億至 1,450 億美元（原下限…）」在短版被切成「收窄為 1」。半形逗號後面接數字是千分位。"""
    from crons.daily_brief import events_block

    fact = "Meta 將資本支出指引收窄為 1,350 億至 1,450 億美元, 並未給出 2027 年指引"
    receipt = {"summary": {"searches": 11, "new": 1, "new_market": 1, "new_theme": 0, "new_watch": 0},
               "accepted": [{"scope": "market", "title": "Meta", "fact": fact, "lead_id": "lead_m"}]}
    lines = events_block(digest=None, receipt=receipt, digest_problem=None, radar_problem=None)
    assert lines[2].startswith("- Meta 將資本支出指引收窄為 1,350 億至 1,450 億美元 →")   # 千分位不切；「, 並」照切


def test_long_lines_are_clipped_at_punctuation_not_inside_a_number_or_word() -> None:
    """2026-10-28 第一版新排版：雷達那則被切成「（原下限為 1,300…」、建議理由被切成「tech:ai_context_m…」。"""
    from crons.daily_brief import _clip

    fact = "Meta 於第三季財報將 2026 年資本支出指引區間收窄為 1,350 億至 1,450 億美元（原下限為 1,300 億）"
    assert _clip(fact, 60) == "Meta 於第三季財報將 2026 年資本支出指引區間收窄為 1,350 億至 1,450 億美元…"
    assert _clip("短句", 60) == "短句"
    assert _clip("a" * 80, 60) == "a" * 60 + "…"                              # 沒有斷點才硬切


def test_without_a_digest_the_brief_says_why_and_falls_back_to_program_content() -> None:
    from crons.daily_brief import events_block, leads_block

    todays = [_lead("lead_a", seen=NOW, status="triaged_go", title="穩懋 CW 雷射代工量產")]
    lines = leads_block(digest=None, todays=todays, since=NOW - timedelta(hours=digest.WINDOW_HOURS),
                        digest_problem="LLM 摘要今天沒產生（11c rate_limited）")
    assert lines[-2] == "- 穩懋 CW 雷射代工量產" and "11c rate_limited" in lines[-1] and lines[-1].startswith("-# ")
    receipt = {"summary": {"searches": 9, "new": 1, "new_market": 1},
               "accepted": [{"scope": "market", "title": "LG lands deal", "fact": "LG 簽冷水機長約"}]}
    lines = events_block(digest=None, receipt=receipt, digest_problem="沒產生", radar_problem=None)
    assert lines[2].startswith("- LG 簽冷水機長約 →")
    lines = events_block(digest=None, receipt=None, digest_problem="沒產生", radar_problem="01c rate_limited")
    assert "沒有收據：01c rate_limited" in lines[1] and lines[-1] == "- 今天沒有收下任何一則"


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
    assert "收 4 則" in lines[1] and "沒收 1" in lines[1]
    body = lines[2:]
    assert len([x for x in body if x.startswith("- ") and " → " in x]) == 4          # 收下的每一則都列
    assert not any("台積電" in x for x in body)                                       # 前一天收的不會被夾進來
    lg = next(x for x in body if "LG" in x)
    assert "可能跟 10-07 收過的是同一件事" in lg
    assert not any("可能跟" in x for x in body if "Google" in x or "奇鋐" in x)        # 不像的不標
    assert body[-1].startswith("-# 沒收：") and "lead 裡已經有這個網址" in body[-1]
    receipt["rejected"][0]["lead_id"] = "lead_sivers"
    titled = events_block(digest=None, receipt=receipt, digest_problem=None, radar_problem=None,
                          lead_titles={"lead_sivers": "Sivers 臨時股東會通知"})
    assert titled[-1] == "-# 沒收：Sivers 臨時股東會通知——lead 裡已經有這個網址"


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
    assert lines[0] == "- daily 1/4 步" and len(lines) == 3
    assert "10-08 07:40 重置——這一輪沒跑：外部雷達、分類" in lines[1]
    assert lines[2] == "  - ⚠ 本機備份＋Drive 異地：failed（exit 1；StateFileError: 不安全的 raw evidence 引用）"
    ok = health_block(record={"steps": [{"key": "a", "status": "ok"}, {"key": "b", "status": "skipped"}]},
                      record_problem=None, quota=[], snapshot={})
    assert ok == ["- daily 1/2 步（跳過 1）｜健康度正常（invariants、健康審查無紅）"]
    none = health_block(record=None, record_problem="今天沒有 daily 執行紀錄（daily 沒跑）", quota=[], snapshot={})
    assert none == ["- daily：沒有執行紀錄", "  - ⚠ 今天沒有 daily 執行紀錄（daily 沒跑）"]


def test_one_cause_is_printed_once_and_names_what_failed() -> None:
    """2026-10-28：同一個 SourceDocSync 誤報在短版印成兩行（「六條 invariant：failed」＋「invariants FAIL 1」），
    健康紅燈只印數字——使用者分不出是兩件事還是一件。invariant 那一步失敗＝快照的 FAIL，併一行並寫出是哪幾條；紅燈寫出哪一節。"""
    from crons.daily_brief import health_block

    record = {"steps": [{"key": "14_health_audit", "status": "ok"},
                        {"key": "15_invariants", "status": "failed", "exit": "1", "label": "六條 invariant"}]}
    lines = health_block(record=record, record_problem=None, quota=[], snapshot={"invariants.fail": 1, "health.red": 1},
                         invariant_fails=["SourceDocSync"], red_sections=["SourceDoc 與抽取 JSON"])
    assert lines == ["- daily 1/2 步", "  - ⚠ invariant FAIL 1：SourceDocSync", "  - ⚠ 健康紅燈 1：SourceDoc 與抽取 JSON"]
    # invariant 那一步沒失敗、快照卻有 FAIL（例如手動重跑過）：照樣印一行，不因為步驟 ok 就藏起來
    quiet = health_block(record={"steps": [{"key": "15_invariants", "status": "ok"}]}, record_problem=None, quota=[],
                         snapshot={"invariants.fail": 2})
    assert quiet == ["- daily 1/1 步", "  - ⚠ invariant FAIL 2"]


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
    assert lines[0] == "- daily 1/3 步（跳過 1）" and len(lines) == 3
    assert "這一輪照跑" in lines[1] and "這一輪沒跑" not in lines[1]
    assert lines[2].startswith("  - ⚠ T2 輪詢提議：timeout（超過 3 分鐘；5 次呼叫：ok 4、timeout 1；任一次沒過整步不寫結果）")
    assert lines[2].endswith("——連帶跳過：T2 輪詢套用")


def test_the_research_counters_print_zero_and_say_when_they_could_not_be_read() -> None:
    """AGENTS：「未 triage N」「未檢 N」必印（L13）——字照 AGENTS 寫，0 也印，讀不到印「未讀到」不印 0。
    2026-10-28 排版：非 0 一格一行；0 的格名字印在小字（每一格都還在）；未讀到另列警告。"""
    from crons.daily_brief import TODO_COUNTERS, todo_block

    # 2026-10-22 起 ⑤ 讀 engine_b.todo_ledger（ledger 組不出來時退回快照計數，仍是這一行）
    snapshot = {key: 0 for key, _label in TODO_COUNTERS}
    snapshot["todo.pending_triage"] = 102
    snapshot["todo.semantic"] = None
    line = todo_block(snapshot)[1]
    assert "未 triage 102" in line and "未檢 未讀到" in line and "讀圖該重讀 0" in line
    from engine_b.todo_ledger import LedgerCount

    rows = [LedgerCount(key, label, 0) for key, label in TODO_COUNTERS]
    rows[0].count, rows[3].count = 102, None
    lines = todo_block(snapshot, rows, next_line="`/research-drain`")
    assert lines[0] == "### ⑤ 下一次研究" and lines[1].startswith("- 未 triage 102 ")
    assert lines[2] == "- ⚠ 未讀到（不是 0）：未檢"
    zero = lines[3]
    assert zero.startswith("-# 0 的格：") and "讀圖該重讀" in zero and "未 triage" not in zero
    assert all(label in zero for _key, label in TODO_COUNTERS if label not in ("未 triage", "未檢"))  # 每一格都還在
    assert lines[-1] == "-# 下一步貼：`/research-drain`"
    quiet = todo_block(snapshot, [LedgerCount(key, label, 0) for key, label in TODO_COUNTERS])
    assert quiet[1] == "- 每一格都是 0" and "未 triage" in quiet[2] and "未檢" in quiet[2]


def test_the_disproof_line_always_prints_watching_touched_and_unwatched() -> None:
    """AGENTS 短版狀態塊：反證在盯與未盯數每天印；觸及待處置不是 0 就加粗；到期待複查、加碼條件觸及不是 0（或讀不到）才印。"""
    from crons.daily_brief import disproof_line

    quiet = {"disproof.watching": 41, "disproof.touched_pending": 0, "disproof.expired_pending": 0,
             "disproof.unwatched": 0, "confirm.watching": 3, "confirm.touched_pending": 0}
    assert disproof_line(quiet) == "反證：在盯 41｜觸及待處置 0｜未盯 0"
    loud = {**quiet, "disproof.touched_pending": 2, "disproof.expired_pending": 1, "disproof.unwatched": None}
    assert disproof_line(loud) == "反證：在盯 41｜**觸及待處置 2**｜未盯 未讀到｜**到期待複查 1**"
    assert disproof_line({}) == ("反證：在盯 未讀到｜**觸及待處置 未讀到**｜未盯 未讀到"
                                 "｜**到期待複查 未讀到**｜**加碼條件觸及 未讀到**")     # 讀不到不是 0（INV-3）


def test_the_brief_prints_the_status_block_and_each_line_degrades_alone(tmp_path, monkeypatch) -> None:
    """compose_brief 的 ④：標題固定是「狀態與健康度」；候選板讀不到時只有那一行說讀不到，watch／反證照印（各自降級）。
    較昨變動與新點名不進短版（2026-10-28：一行塞 47 項；完整心跳段 2 照印）。"""
    from crons import daily_brief
    from crons import heartbeat as hb

    def broken(_state_dir, _kind):
        raise OSError("candidates artifact gone")

    monkeypatch.setattr(hb, "_load_state", broken)
    monkeypatch.setattr(hb, "watch_today_counts", lambda **_kw: {"woken": 1, "expired": 0, "semantic_flagged": 2})
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    text = daily_brief.compose_brief(now=datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc), summary="Daily 2026-10-08｜球在你 0",
                                     snapshot={"disproof.watching": 5}, run_record_path=tmp_path / "missing.json",
                                     leads_path=leads_path, heartbeat_dir=tmp_path,
                                     diff_lines=["較昨變動 1 項：反證在盯 4→5"])
    block = text.split("### ④ 狀態與健康度", 1)[1].split("### ⑤", 1)[0]
    assert "較昨變動" not in block
    assert "- 候選：讀不到（OSError）" in block
    assert "- 等回落：讀不到（OSError）" in block
    assert "- watch：今日醒 1｜到期 0｜語意標旗 2" in block
    assert "- 反證：在盯 5｜**觸及待處置 未讀到**" in block
    assert "- 無到期的等待 0" in block
    assert "registry 沒有的名字" not in block and "onboard-candidates" not in block
    assert "- daily：沒有執行紀錄" in block and "今天沒有 daily 執行紀錄" in block


def test_the_brief_opens_with_the_summary_flags_unchanged_and_ends_with_the_copy_line() -> None:
    """開頭＝心跳摘要行換排版（討論串標題＋紅旗小字），旗一個不增不減；最後一則＝批次指令單獨一行 inline code
    （2026-10-28 使用者：「最後給我一次複製的指令可以用回以前的格式 那樣我一次點就可以複製」）。"""
    from crons.daily_brief import brief_header, copy_line

    summary = "Daily 2026-10-28｜球在你 5｜等你給文件 1｜⚠ daily 失敗 2 步｜⚠ LLM model 變了｜⚠ 健康紅燈 1"
    assert brief_header(summary) == ["## 10-28 Daily｜球在你 5｜等你給文件 1｜⚠ 3",
                                     "-# ⚠ daily 失敗 2 步｜LLM model 變了｜健康紅燈 1"]
    assert brief_header("Daily 2026-10-28｜球在你 0") == ["## 10-28 Daily｜球在你 0"]       # 沒旗就沒有小字
    assert copy_line("878 879 go 880 drop") == ["`878 879 go 880 drop`"] and copy_line(None) == []


def test_decisions_reuse_the_heartbeat_list_and_say_none_when_empty() -> None:
    from crons.daily_brief import decisions_block
    from engine_b import todo

    assert decisions_block(actionable=[], problem=None, todo_mod=todo) == (["### ③ 待你決定（0）", "- 沒有"], None)
    item = {"n": 715, "type": "ra_admission", "title": "InP 磊晶片層建層：IQE 供 6 吋",
            "graph_impact": "新增 1 節點、2 邊、2 claims（另 2 筆已在圖上或逐字保留）｜來源：NVIDIA（tier 1）、Micron Technology（tier 1）"}
    lines, batch = decisions_block(actionable=[item], problem=None, todo_mod=todo)
    # 一條一塊：粗體主詞、細節、go＝、不含（白話，取自 todo.GO_PLAIN）、圖會變
    assert lines[:6] == ["### ③ 待你決定（1）", "**[715] InP 磊晶片層建層**", "- IQE 供 6 吋", "- go＝把這一包寫進圖",
                         "- 不含：改敘事或 thesis、下單",
                         "- 圖會變：新增 1 節點、2 邊、2 claims｜來源 NVIDIA、Micron Technology（tier 1）"]
    assert batch is None and "都沒寫建議" in lines[-1]
    assert "讀不到" in decisions_block(actionable=None, problem="OSError", todo_mod=todo)[0][0]


def test_the_decisions_end_with_one_copyable_line_built_from_the_recommendations_on_the_items() -> None:
    """2026-10-08 使用者：「待我決定的批次回覆 一樣就要給我單行可複製建議的操作」。建議是鑄號的 session 寫在編號上的，
    daily 只照抄；沒寫建議的另列、不進那一行；watch_decision 的 go／pending 進不了批次。2026-10-28 起那一行是最後一則。"""
    from crons.daily_brief import decisions_block
    from engine_b import todo

    items = [
        {"n": 736, "type": "manual", "title": "載板鏈對照組", "recommendation": {"verb": "go", "reason": "日東紡敘事要先有對照組"}},
        {"n": 739, "type": "ra_admission", "title": "分接開關層補華明", "recommendation": {"verb": "go", "reason": "供給側 0→1"}},
        {"n": 741, "type": "manual", "title": "舊題目", "recommendation": {"verb": "drop", "reason": "pool 現值已無對應（todo list 查過）"}},
        {"n": 742, "type": "manual", "title": "沒寫建議的"},
        {"n": 743, "type": "watch_decision", "title": "到期", "recommendation": {"verb": "pending", "reason": "等 Q3"}},
    ]
    lines, batch = decisions_block(actionable=items, problem=None, todo_mod=todo)
    assert batch == "736 739 go 741 drop"
    assert "- 建議 go：日東紡敘事要先有對照組" in lines
    assert any(x.startswith("-# 沒寫建議：[742]、[743]") for x in lines)
    assert any("[743] 是到期的等待：批次裡只能 drop" in x for x in lines)
    assert not any("`736" in x for x in lines)                                  # 批次指令不在 ③ 裡，是最後一則


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
    lines = leads_block(digest=None, todays=digest.select_leads(store, now=NOW), digest_problem="沒產生",
                        since=NOW - timedelta(hours=digest.WINDOW_HOURS))
    assert lines[1].startswith("-# 外面新進 2（") and lines[1].endswith("＋我們自己登記的研究題 1（不摘要）")
    assert all("lead_topic" not in line for line in lines)


def test_headline_splits_new_arrivals_from_backlog_triaged_this_round() -> None:
    """2026-10-16：10-13 標題寫「外面新進 125 則」，其中 82 則是 10-10～10-12 積下來、那天才分類的（L12：一個數字裝兩種意思）。
    窗內首見的才叫新進、來源家族只數它們；首見在窗前、這輪才分類的另印一個數；沒有首見時間的也算前者之外。"""
    from crons.daily_brief import leads_block

    store = _store()
    store["leads"]["lead_no_seen"] = {**_lead("lead_no_seen", seen=NOW, status="triaged_go",
                                              triage_at=NOW - timedelta(hours=1)), "first_seen": None}
    lines = leads_block(digest=None, todays=digest.select_leads(store, now=NOW), digest_problem="沒產生",
                        since=NOW - timedelta(hours=digest.WINDOW_HOURS))
    assert lines[1] == "-# 外面新進 2（外部雷達 1、X 帳號 1）＋前幾天進來、這輪才分類 2"


def test_processing_line_counts_what_we_did_in_the_window() -> None:
    """2026-10-07 使用者：「Lead 抓了什麼 我們做了哪些處理的數字也要印」——分類（go／no-go、LLM／互動）、
    研究到終局（轉移紀錄在窗內轉到入圖包／已入圖／停放）、還沒分類（其中無內文）、待深挖；窗外的不算。
    2026-10-28 起一事一行；「其中無內文」使用者在短版找不到（failure log #105 的計數器只在完整心跳）。"""
    from crons.daily_brief import processing_lines

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
        "g": {"status": "pending", "source_class": "social"},
        "h": {"status": "pending", "source_class": "social", "raw_text": "原文在這裡"},
    }}
    lines = processing_lines(store, now=NOW, held=1)
    assert lines == ["- 分類 3：go 1｜no-go 2（LLM 1／互動 1／機械或舊資料 1）",
                     "- 還沒分類 2（其中**無內文 1**：daily 不送分類，互動 session 讀全文後分類）",
                     "- 研究到終局 2：入圖包 1｜已入圖 0｜停放 1",
                     "- 待深挖 1"]
    assert processing_lines(store, now=NOW, held=0)[1] == "- 還沒分類 2（其中無內文 0）"
    # 不給 held 就就地盤點（`lead_text.held_pending`，不連網）：g 什麼內文都沒有、h 有原文 → 1
    assert processing_lines(store, now=NOW)[1].startswith("- 還沒分類 2（其中**無內文 1**")


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
    decisions = text.split("### ③ 待你決定", 1)[1].split("**③b", 1)[0]
    documents = text.split("**③b 等你提供的文件", 1)[1].split("### ④", 1)[0]
    assert "InP 磊晶片層建層" in decisions and "全新光電" not in decisions
    assert "全新光電券商報告" in documents and "提供文件才算 go" in documents and "drop" in documents
    assert "- 分類 0：" in text.split("### ② 市場大事", 1)[0]
    # 六個 `###` 段與開頭都在（每塊一定出現——INV-3）；沒有建議就沒有最後那一則
    assert text.startswith("## Daily｜球在你 1｜等你給文件 1\n")
    assert [line for line in text.splitlines() if line.startswith("### ")] == [
        "### ① Lead 抓了什麼", "### ② 市場大事", "### ③ 待你決定（1）", "### ④ 狀態與健康度", "### ⑤ 下一次研究"]
    assert not text.rstrip().splitlines()[-1].startswith("`")


def test_the_window_starts_at_the_previous_heartbeat_not_26_hours_back(tmp_path) -> None:
    """2026-10-22：固定 26 小時每天把前一天那一輪（05:30）包進來——10-21 重算 48 則、10-22 重算 41 則。"""
    import json
    from datetime import datetime, timedelta, timezone

    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    now = datetime(2026, 10, 21, 22, 24, tzinfo=timezone.utc)                  # 台北 10-22 06:24
    assert digest.window_start(now, snapshot_dir=snaps) == now - timedelta(hours=digest.WINDOW_HOURS)
    (snaps / "2026-10-21.json").write_text(json.dumps({"generated_at": "2026-10-20T22:08:00+00:00"}), encoding="utf-8")
    (snaps / "2026-10-22.json").write_text(json.dumps({"generated_at": "2026-10-21T22:24:00+00:00"}), encoding="utf-8")
    start = digest.window_start(now, snapshot_dir=snaps)
    assert start == datetime(2026, 10, 20, 22, 8, tzinfo=timezone.utc)        # 昨天那一份，不是今天自己
    store = {"leads": {"old": {"lead_id": "old", "first_seen": "2026-10-20T21:30:00+00:00"},
                       "new": {"lead_id": "new", "first_seen": "2026-10-21T21:30:00+00:00"}}}
    assert [l["lead_id"] for l in digest.select_leads(store, now=now, since=start)] == ["new"]
    later = now + timedelta(days=5)                                           # daily 停了幾天：不讓窗無限張開
    assert digest.window_start(later, snapshot_dir=snaps) == later - timedelta(hours=digest.WINDOW_HOURS)
