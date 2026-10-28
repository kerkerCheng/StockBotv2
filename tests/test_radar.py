"""Phase 7 Step 7.0f：外部雷達（使用者 2026-10-04 Q5）。

daily ①b 準備 → ①c `claude -p` **只開 WebSearch**（其餘與零工具步驟同一套白名單與能力檢查）→ ①d 保險檢查 → ①e 程式驗證後寫成
secondary lead。這裡守：argv 與放行最窄、能力檢查（恰為 WebSearch＋StructuredOutput）、權限被拒判失敗（2026-10-04 探針：
被拒時 CLI 照樣回 is_error false＋空結果）、網址只收 CLI 的搜尋結果、網址不在搜尋結果拒收、去重、每日上限、published_at、
prompt 不含持股（哨兵）、triage 批次裡排在最後、daily 的開關與心跳那一行。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from crons import llm_step
from engine_b import leads
from engine_b import radar

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_instruction_files_above_tmp(monkeypatch):
    """同 `tests/test_daily_task.py`：pytest 的 tmp 在 repo 裡、上層有 AGENTS.md——指令檔名換成不存在的（偵測本身另有測試）。"""
    from crons import daily_task as dt

    monkeypatch.setattr(dt, "INSTRUCTION_FILES", ("__no_such_instruction_file__.md",))


INIT_RADAR = json.loads((ROOT / "tests" / "fixtures" / "claude_init_radar_ok.json").read_text(encoding="utf-8"))
INIT_ZERO = json.loads((ROOT / "tests" / "fixtures" / "claude_init_ok.json").read_text(encoding="utf-8"))
RUN = "run-radar-1"
TODAY = date(2026, 10, 5)
URL_A = "https://www.example-news.com/2026/10/04/coherent-cw-laser-ramp"
URL_B = "https://www.globenewswire.com/news-release/2026/10/03/1/0/en/Sivers-order.html"
URL_C = "https://www.digitimes.com/news/a20261003PD201.html"


# ---------------------------------------------------------------------------
# argv、能力檢查、權限被拒、網址收集
# ---------------------------------------------------------------------------

def test_radar_argv_differs_from_the_zero_tool_one_in_exactly_two_values() -> None:
    zero = llm_step.llm_argv("C:/x/claude.exe", "sonnet", "{schema}", effort="high")
    argv = llm_step.radar_argv("C:/x/claude.exe", "sonnet", "{schema}", effort="high")
    assert argv[argv.index("--effort") + 1] == "high"                       # effort 跟著零工具那份走、不漏
    diff = [(z, a) for z, a in zip(zero, argv) if z != a]
    assert len(argv) == len(zero) and len(diff) == 2
    assert argv[argv.index("--tools") + 1] == "WebSearch"                    # 只開這一個
    settings = json.loads(argv[argv.index("--settings") + 1])
    assert settings == {"disableAllHooks": True, "autoMemoryEnabled": False, "permissions": {"allow": ["WebSearch"]}}
    for flag in llm_step.RADAR_FORBIDDEN_FLAGS:
        assert flag not in argv, flag
    assert set(llm_step.FORBIDDEN_LLM_FLAGS) < set(llm_step.RADAR_FORBIDDEN_FLAGS)


def test_the_recorded_radar_init_passes_only_with_the_radar_tool_set() -> None:
    assert llm_step.capability_violations(INIT_RADAR, tools=llm_step.RADAR_TOOLS) == []
    assert llm_step.capability_violations(INIT_RADAR)                      # 零工具步驟看到 WebSearch → 不符
    assert llm_step.capability_violations(INIT_ZERO, tools=llm_step.RADAR_TOOLS)   # 雷達沒拿到 WebSearch → 不符


@pytest.mark.parametrize("tools", [["StructuredOutput", "WebSearch", "WebFetch"], ["StructuredOutput", "WebSearch", "Bash"],
                                   ["WebSearch"], ["StructuredOutput", "WebSearch", "WebSearch"]])
def test_any_other_tool_set_is_a_radar_capability_violation(tools) -> None:
    init = {**INIT_RADAR, "tools": tools}
    assert any(v.startswith("tools") for v in llm_step.capability_violations(init, tools=llm_step.RADAR_TOOLS))


def _search_events(*, urls, tool_id="toolu_ws1", denied=False) -> list[dict]:
    """探針 B 的形狀：assistant tool_use(WebSearch) → user tool_result＋頂層 tool_use_result（dict＝搜尋結果；字串＝摘要）。"""
    use = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tool_id, "name": "WebSearch",
                                                         "input": {"query": "Coherent CW laser"}}]}}
    if denied:
        result = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": True,
                                                           "content": "Claude requested permissions to use WebSearch"}]},
                  "tool_use_result": "Error: Claude requested permissions to use WebSearch, but you haven't granted it yet."}
        return [use, {"type": "system", "subtype": "permission_denied"}, result]
    result = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "content": "Links: [...]"}]},
              "tool_use_result": {"query": "Coherent CW laser", "searchCount": 1, "durationSeconds": 3.0, "results": [
                  {"tool_use_id": "srvtoolu_1", "content": [{"title": f"title of {u}", "url": u} for u in urls]},
                  f"Based on the search results ... see also https://made-up-by-the-summary.example/{len(urls)}"]}}
    return [use, result]


def _structured(items, *, no_change=False) -> dict:
    return {"type": "result", "subtype": "success", "is_error": False, "num_turns": 3, "session_id": "sess-r",
            "structured_output": {"items": items, "no_material_change": no_change},
            "permission_denials": []}


def _run(events):
    from tests.test_daily_task import FakePopen

    collector = llm_step.SearchCollector()
    popen = FakePopen(events)
    outcome = llm_step.run_claude("prompt", argv=["claude", "-p"], cwd=Path("C:/cwd"), env={"PATH": "p"},
                                  timeout_minutes=1, popen=popen, kill=lambda proc: proc.kill(),
                                  tools=llm_step.RADAR_TOOLS, observe=collector.observe)
    return outcome, collector


def test_the_collector_takes_only_the_cli_search_results_not_urls_in_the_summary_text() -> None:
    other = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_so",
                                                     "content": "Structured output provided successfully"}]},
             "tool_use_result": {"results": [{"content": [{"title": "x", "url": "https://not-a-search.example/"}]}]}}
    outcome, collector = _run([INIT_RADAR, *_search_events(urls=[URL_A, URL_B]), other, _structured([])])
    assert outcome.status == "ok"
    record = collector.as_record()
    assert record["urls"] == sorted([URL_A, URL_B]) and record["searches"] == 1
    assert record["queries"] == ["Coherent CW laser"] and record["titles"][URL_A] == f"title of {URL_A}"
    assert not any("made-up" in u or "not-a-search" in u for u in record["urls"])   # 摘要文字與非搜尋工具的結果不收


def test_a_permission_denial_is_a_failure_even_though_the_cli_says_success() -> None:
    denied_result = {**_structured([]), "permission_denials": [{"tool_name": "WebSearch", "tool_use_id": "toolu_ws1",
                                                                 "tool_input": {"query": "x"}}]}
    outcome, collector = _run([INIT_RADAR, *_search_events(urls=[], denied=True), denied_result])
    assert outcome.status == "failed" and "權限被拒" in outcome.error and outcome.permission_denials == 1
    assert collector.as_record()["urls"] == []
    assert outcome.as_record()["permission_denials"] == 1


def test_a_zero_tool_init_kills_the_radar_before_any_search() -> None:
    outcome, _ = _run([INIT_ZERO, *_search_events(urls=[URL_A]), _structured([])])
    assert outcome.status == "capability_violation" and outcome.killed_before_result


# ---------------------------------------------------------------------------
# prepare：資料只來自主題與在盯的條件——不讀持股（哨兵）
# ---------------------------------------------------------------------------

THEMES = {"cpo": SimpleNamespace(description="CPO", tickers=("COHR",), keywords=("CPO",), counter_keywords=("LPO",)),
          "power": SimpleNamespace(description="電力", tickers=(), keywords=("power transformer",), counter_keywords=())}
REG = SimpleNamespace(company=lambda cid: SimpleNamespace(display_name={"co:coherent": "Coherent Corp."}.get(cid)),
                      companies=())
WATCHES = [
    {"watch_id": "ew_d1", "kind": "semantic_condition", "status": "active", "condition": "供給側出現第七家 CW 雷射供應商",
     "entities": ["co:coherent"], "source_ref": "reading:sr_x#1", "disproof_ref": "reading:sr_x#1"},
    {"watch_id": "ew_c1", "kind": "semantic_condition", "status": "active", "condition": "客戶具名量產",
     "entities": ["co:coherent"], "source_ref": "brief:ib_x#c1", "disproof_ref": "brief:ib_x#c1",
     "condition_role": "confirm"},
    {"watch_id": "ew_done", "kind": "semantic_condition", "status": "consumed", "condition": "已收的條件",
     "entities": ["co:coherent"]},
    {"watch_id": "ew_date", "kind": "date", "status": "active", "until": "2026-12-01"},
]


def _no_plan():
    raise RuntimeError("測試不載入輪替")


def test_prepare_sends_themes_and_watched_conditions_and_never_touches_holdings(tmp_path, monkeypatch) -> None:
    sentinel = "ZZZ-HOLDING-SENTINEL"

    def boom(*_a, **_k):
        raise AssertionError(f"雷達讀了持股／Sheet（{sentinel}）")

    import fetchers.gsheets as gsheets
    import portfolio.holdings as holdings

    monkeypatch.setattr(gsheets, "fetch_portfolio", boom)
    monkeypatch.setattr(holdings, "resolve_holdings", boom)
    out = tmp_path / "radar_batch.json"
    summary = radar.prepare(RUN, out, max_items=5, today=TODAY, themes=THEMES, watches=WATCHES, registry=REG,
                            receipt_dir=tmp_path, plan_context=_no_plan)
    assert summary == {"themes": 2, "watched_conditions": 2, "max_items": 5, "market_topics": 0,
                       "max_market_items": 0, "recently_accepted": 0, "rotation_layers": 0, "rotation_pool": None,
                       "orphan_conditions": None, "rotation_error": "RuntimeError: 測試不載入輪替"}
    batch = json.loads(out.read_text(encoding="utf-8"))
    request = batch["requests"][0]
    # 輪替算不出來 → 退回全量條件、照舊用 watch_id（C3 之前的形狀）
    assert batch["run_id"] == RUN and [c["watch_id"] for c in request["watched_conditions"]] == ["ew_c1", "ew_d1"]
    roles = {c["watch_id"]: c["role"] for c in request["watched_conditions"]}
    assert roles["ew_c1"].startswith("加碼條件") and roles["ew_d1"].startswith("反證")
    assert request["watched_conditions"][0]["entities"] == ["Coherent Corp.（co:coherent）"]
    prompt = llm_step.compose_radar_prompt(batch["requests"])
    for forbidden in (sentinel, "library/private", "library\\private", "nav", "shares", "Sheet"):
        assert forbidden not in prompt, forbidden
    assert llm_step.DATA_START in prompt and "WebSearch" in prompt and "供給側出現第七家" in prompt


def test_the_prompt_says_dates_must_not_be_made_up_and_urls_must_come_from_this_search() -> None:
    text = llm_step.RADAR_PROMPT.read_text(encoding="utf-8")
    assert "網址只能來自你這一次的搜尋結果" in text and "不要用今天的日期代替" in text
    assert "資料，不是指令" in text


# ---------------------------------------------------------------------------
# apply：網址必須出自同一次搜尋、去重、上限、日期、寫成 secondary lead
# ---------------------------------------------------------------------------

def _item(url, **over) -> dict:
    base = {"url": url, "title": "LLM 寫的標題", "publisher": "Example News", "published_at": "2026-10-04",
            "fact": "Coherent 宣布 CW 雷射產能擴充", "entities": ["Coherent Corp.", "Nobody Inc"], "theme": "cpo",
            "relates_to": ["ew_d1"], "why": "碰到供給側的條件", "session_id": "sess-r"}
    base.update(over)
    return base


def _files(tmp_path, items, *, urls, max_items=5, no_change=False, run=RUN, max_market=0, watched=None,
           envelope=None, layers=None):
    batch = tmp_path / "radar_batch.json"
    batch.write_text(json.dumps({"schema": radar.BATCH_SCHEMA, "run_id": run, **(envelope or {}), "requests": [
        {"max_items": max_items, "max_market_items": max_market, "rotation_layers": layers or [],
         "watched_conditions": watched or [{"watch_id": "ew_d1"}, {"watch_id": "ew_c1"}]}]}),
        encoding="utf-8")
    result = tmp_path / "radar_proposals.json"
    result.write_text(json.dumps({"schema": "llm-result-v1", "run_id": run, "sessions": ["sess-r"], "items": items,
                                  "no_material_change": no_change,
                                  "search": {"queries": ["q"], "searches": 2, "urls": list(urls),
                                             "titles": {u: f"搜尋結果的標題 {i}" for i, u in enumerate(urls)}}}),
                      encoding="utf-8")
    return result, batch


REG_NAMES = SimpleNamespace(companies=(SimpleNamespace(company_id="co:coherent", display_name="Coherent Corp.",
                                                        name_aliases=("Coherent",)),),
                            company=lambda cid: None)


def _apply(tmp_path, items, *, urls, store=None, **kw):
    store_path = tmp_path / "leads.json"
    if not store_path.exists():
        leads.save(store or leads.empty_store(), store_path)
    result, batch = _files(tmp_path, items, urls=urls, **kw)
    out = radar.apply(result, batch, RUN, store_path=store_path, receipt_dir=tmp_path / "receipts", today=TODAY,
                      registry=REG_NAMES, now=datetime(2026, 10, 5, 0, 5, tzinfo=timezone.utc))
    return out, leads.load(store_path)


def test_a_url_that_is_not_in_this_runs_search_results_is_rejected_and_not_written(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A), _item(URL_C)], urls=[URL_A])
    s = out["summary"]
    assert s["new"] == 1 and s["url_not_in_search"] == 1
    assert [r["reason"] for r in out["rejected"]] == ["url_not_in_search"] and out["rejected"][0]["url"] == URL_C
    assert leads.lead_id_for(URL_C) not in store["leads"]


def test_the_written_lead_is_secondary_with_the_search_title_and_the_llm_fact_kept_apart(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A)], urls=[URL_A])
    lead = store["leads"][leads.lead_id_for(URL_A)]
    assert lead["source"] == "web_radar:cpo" and lead["source_class"] == "secondary" and lead["status"] == "pending"
    assert lead["title"] == "搜尋結果的標題 0"                                # 標題來自搜尋工具，不是 LLM（L18）
    assert "raw_text" not in lead                                             # LLM 的摘要不冒充原文
    refs = lead["refs"]
    assert refs["radar_run"] == RUN and refs["radar_fact"].startswith("Coherent") and refs["relates_to"] == ["ew_d1"]
    assert refs["radar_entities"] == ["Coherent Corp.", "Nobody Inc"] and refs["radar_company_ids"] == ["co:coherent"]
    assert lead["published_at"] == "2026-10-04" and out["summary"]["related"] == 1
    receipt = json.loads((tmp_path / "receipts" / f"radar_{TODAY.isoformat()}.json").read_text(encoding="utf-8"))
    assert receipt["summary"]["new"] == 1 and receipt["accepted"][0]["url"] == URL_A


def test_an_already_registered_url_is_a_duplicate_and_the_existing_lead_is_not_touched(tmp_path) -> None:
    store = leads.empty_store()
    leads.register(store, source="rss:example", url=URL_A + "/", title="harvest 先登記的", seen_at="2026-10-04T01:00:00+00:00")
    out, after = _apply(tmp_path, [_item(URL_A), _item(URL_B), _item(URL_B)], urls=[URL_A, URL_B], store=store)
    s = out["summary"]
    assert s["new"] == 1 and s["duplicate"] == 2                              # 一則 registry 已有、一則同批重複
    kept = after["leads"][leads.lead_id_for(URL_A)]
    assert kept["source"] == "rss:example" and kept["refs"] == {}             # 誰先登記照實留著（7.5 要分得出）


def test_the_daily_cap_is_enforced_by_the_program_not_the_prompt(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A), _item(URL_B), _item(URL_C)], urls=[URL_A, URL_B, URL_C], max_items=2)
    s = out["summary"]
    assert s["new"] == 2 and s["over_cap"] == 1 and leads.lead_id_for(URL_C) not in store["leads"]


@pytest.mark.parametrize("given, expected, unparsed", [
    ("2026-10-04", "2026-10-04", 0), (None, None, 0), ("上週", None, 1), ("2026-12-31", None, 1)])
def test_published_at_is_null_when_unreadable_or_in_the_future_never_today(tmp_path, given, expected, unparsed) -> None:
    out, store = _apply(tmp_path, [_item(URL_A, published_at=given)], urls=[URL_A])
    assert store["leads"][leads.lead_id_for(URL_A)]["published_at"] == expected
    assert out["summary"]["published_unparsed"] == unparsed


def test_unknown_theme_becomes_new_and_unknown_watch_ids_are_dropped_and_counted(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A, theme="quantum", relates_to=["ew_d1", "ew_bogus"])], urls=[URL_A])
    lead = store["leads"][leads.lead_id_for(URL_A)]
    assert lead["source"] == "web_radar:new" and lead["refs"]["relates_to"] == ["ew_d1"]
    assert out["summary"]["theme_unknown"] == 1 and out["summary"]["relates_to_unknown"] == 1


def test_a_watch_id_with_its_date_suffix_cut_off_resolves_only_when_exactly_one_matches(tmp_path) -> None:
    """2026-10-20：production 的 id 是 `ew_NNNN_YYYY-MM-DD`，LLM 常只回 `ew_NNNN`——10-05 起 26 條全被當成對不上丟掉。"""
    watched = [{"watch_id": "ew_0421_2026-10-07"}, {"watch_id": "ew_0007_2026-10-01"}, {"watch_id": "ew_0007_2026-10-02"}]
    out, store = _apply(tmp_path, [_item(URL_A, relates_to=["ew_0421", "ew_0421_2026-10-07", "ew_0007", "ew_0999"])],
                        urls=[URL_A], watched=watched)
    assert store["leads"][leads.lead_id_for(URL_A)]["refs"]["relates_to"] == ["ew_0421_2026-10-07"]
    s = out["summary"]
    assert s["relates_to_resolved_prefix"] == 1 and s["relates_to_unknown"] == 2 and s["related"] == 1   # 兩條相符不猜


def test_a_malformed_url_in_the_search_results_is_left_out_without_breaking_the_run(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A), _item("http://[bad")], urls=[URL_A, "", "http://[bad"])
    assert out["summary"]["new"] == 1 and out["summary"]["search_urls"] == 1          # 壞網址不進允許清單
    assert out["summary"]["invalid"] == 1 and leads.lead_id_for(URL_A) in store["leads"]


def test_empty_or_malformed_items_are_rejected_as_invalid(tmp_path) -> None:
    out, _ = _apply(tmp_path, [_item(URL_A, fact=""), {"nope": 1}, "string"], urls=[URL_A])
    assert out["summary"]["invalid"] == 3 and out["summary"]["new"] == 0


def test_stale_files_from_another_run_are_refused(tmp_path) -> None:
    result, batch = _files(tmp_path, [_item(URL_A)], urls=[URL_A], run="run-old")
    with pytest.raises(ValueError, match="run_id"):
        radar.apply(result, batch, RUN, store_path=tmp_path / "leads.json", receipt_dir=tmp_path, today=TODAY,
                    registry=REG_NAMES)


def test_radar_leads_never_wake_a_semantic_watch() -> None:
    """語意 watch 的 T0 只認 `source_class=primary`——雷達寫 secondary，叫不醒（plan §6 第 2 項）。"""
    source = (ROOT / "engine_b" / "event_watch.py").read_text(encoding="utf-8")
    assert 'if lead.get("source_class") != "primary":' in source


# ---------------------------------------------------------------------------
# triage 批次：雷達排在所有非雷達 lead 之後才截上限
# ---------------------------------------------------------------------------

def test_the_triage_batch_puts_radar_leads_after_every_other_lead_before_the_cap(tmp_path, monkeypatch, capsys) -> None:
    from engine_b import cli
    import engine_b.routine_config as rc

    store = leads.empty_store()
    radar_id, _ = leads.register(store, source="web_radar:cpo", url=URL_A, title="Coherent $COHR laser",
                                 seen_at="2026-10-01T00:00:00+00:00", source_class="secondary")
    # 真實的雷達 lead 一定帶事實句（apply 拒收空的）；沒有它的話 #105 起會被當成無內文、根本不進批次
    store["leads"][radar_id]["refs"] = {"radar_fact": "Coherent 擴產 6 吋 InP 雷射"}
    for i in range(3):
        leads.register(store, source="rss:x", url=f"https://feed.example/{i}", title=f"plain {i}",
                       seen_at=f"2026-10-04T0{i}:00:00+00:00")
    path = tmp_path / "leads.json"
    leads.save(store, path)
    monkeypatch.setattr(cli, "_held", lambda strict=False: (frozenset({"COHR"}), frozenset()))
    monkeypatch.setattr(rc, "triage_daily_limit", lambda *a, **k: 3)
    code = cli.main(["--leads", str(path), "list", "--status", "pending", "--by-priority", "--triage-batch", "--json"])
    out = capsys.readouterr()
    rows = json.loads(out.out)
    assert code == 0 and [r["source"] for r in rows] == ["rss:x", "rss:x", "rss:x"]   # 提到持股也不擠掉 harvest 的
    assert "外部雷達 1 則排在最後（進本批 0 則）" in out.err and "還有 1 則沒進本批" in out.err   # R2-b：印實際進批數


# ---------------------------------------------------------------------------
# daily：開關與整條流程（假 LLM 照探針的事件形狀把搜尋結果餵給收集器）
# ---------------------------------------------------------------------------

RADAR_ON = {"enabled": True, "max_items": 5, "timeout_minutes": 10}


class RadarLlm:
    def __init__(self, items, urls) -> None:
        self.items, self.urls, self.calls = items, urls, []

    def __call__(self, prompt, *, argv, cwd, env, timeout_minutes, tools=None, observe=None):
        self.calls.append({"prompt": prompt, "argv": argv, "tools": tools, "timeout": timeout_minutes})
        for event in _search_events(urls=self.urls):
            observe(event)
        return llm_step.LlmOutcome(status="ok", structured={"items": self.items, "no_material_change": False},
                                   session_id="sess-r", init=dict(INIT_RADAR))


def _daily(tmp_path, *, radar_block, llm=None, executor="claude"):
    from crons.daily_task import DailyRun
    from tests.test_daily_task import SCHEDULE_XML, FakeRunner, _config

    config = _config(tmp_path, executor=executor)
    data = json.loads(config.read_text(encoding="utf-8"))
    if radar_block is not None:
        data["radar"] = radar_block
    config.write_text(json.dumps(data), encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    (repo / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    runner = FakeRunner(repo)

    def prepare(argv):          # ①b 是子行程；假 runner 不跑 python，這裡照真的形狀寫出這一輪的批次檔
        out = Path(argv[argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"schema": radar.BATCH_SCHEMA, "run_id": argv[argv.index("--run-id") + 1],
                                   "requests": [{"max_items": 5, "themes": [], "watched_conditions": []}]}),
                       encoding="utf-8")

    runner.hooks["engine_b.radar prepare"] = prepare
    runner.stdout["engine_b.radar apply"] = json.dumps({"summary": {"new": 1, "duplicate": 0, "url_not_in_search": 1,
                                                                    "over_cap": 0, "invalid": 0, "related": 1,
                                                                    "no_material_change": False, "searches": 1},
                                                        "rejected": [{"url": URL_C, "reason": "url_not_in_search"}]})
    run = DailyRun(root=repo, out_dir=tmp_path / "out", config_path=config, python="PY", runner=runner,
                   lock_path=tmp_path / "lock.json", schtasks_query=lambda _n: SCHEDULE_XML, llm_runner=llm)
    run.run()
    return run, runner


def test_daily_runs_the_radar_with_the_search_evidence_written_by_the_program(tmp_path) -> None:
    llm = RadarLlm([{"url": URL_A, "fact": "x"}, {"url": URL_C, "fact": "y"}], urls=[URL_A, URL_B])
    run, runner = _daily(tmp_path, radar_block=RADAR_ON, llm=llm)
    rows = {r["key"]: r for r in run.record["steps"]}
    assert [rows[k]["status"] for k in ("01b_radar_prepare", "01c_radar_propose", "01d_integrity_after_radar",
                                        "01e_radar_apply")] == ["ok", "ok", "ok", "ok"]
    call = next(c for c in llm.calls if c["tools"] == llm_step.RADAR_TOOLS)
    assert call["argv"][call["argv"].index("--tools") + 1] == "WebSearch" and call["timeout"] == 10
    result = json.loads((tmp_path / "out" / f"radar_proposals_{run.date}.json").read_text(encoding="utf-8"))
    assert result["run_id"] == run.run_id and result["search"]["urls"] == sorted([URL_A, URL_B])   # 程式收的，不是 LLM 報的
    assert rows["01c_radar_propose"]["search_urls"] == 2 and rows["01c_radar_propose"]["searches"] == 1
    assert rows["01e_radar_apply"]["summary"]["new"] == 1
    apply_call = next(c for c in runner.calls if "apply" in c and "engine_b.radar" in c)
    assert apply_call[apply_call.index("--run-id") + 1] == run.run_id
    order = [r["key"] for r in run.record["steps"]]
    assert order.index("01e_radar_apply") < order.index("06_triage_batch")   # 同一輪就進 triage 批次


@pytest.mark.parametrize("block, reason", [
    (None, "config 沒有 radar 區塊（＝關閉）"),
    ({**RADAR_ON, "enabled": False}, "radar.enabled=false"),
    ({**RADAR_ON, "max_items": 0}, "radar_config_error"),
])
def test_the_radar_switch_skips_all_three_steps_and_nothing_else(tmp_path, block, reason) -> None:
    run, runner = _daily(tmp_path, radar_block=block, llm=RadarLlm([], urls=[]))
    rows = {r["key"]: r for r in run.record["steps"]}
    for key in ("01b_radar_prepare", "01c_radar_propose", "01e_radar_apply"):
        assert rows[key]["status"] == "skipped" and rows[key]["reason"].startswith(reason), rows[key]
    assert not runner.ran("engine_b.radar prepare")
    assert rows["01_harvest"]["status"] == "ok" and rows["18_heartbeat"]["status"] == "ok"


def test_executor_none_also_stops_the_radar_proposal_and_apply(tmp_path) -> None:
    run, _ = _daily(tmp_path, radar_block=RADAR_ON, executor="none")
    rows = {r["key"]: r for r in run.record["steps"]}
    assert rows["01c_radar_propose"]["reason"] == "executor=none" and rows["01e_radar_apply"]["reason"] == "executor=none"


def test_the_radar_fits_the_daily_time_limit() -> None:
    from crons import daily_task as dt
    from engine_b.routine_config import load_llm, load_radar, load_schedule

    radar_cfg = load_radar()
    assert radar_cfg["configured"] and radar_cfg["enabled"] and radar_cfg["max_items"] == 5
    assert radar_cfg["max_market_items"] >= len(radar_cfg["market_topics"])      # prompt 要「每題挑一則」
    total = dt.total_timeout_minutes(dt.DAILY_STEPS, load_llm(), radar_cfg)
    assert total < load_schedule()["execution_time_limit_minutes"]


def test_a_market_cap_below_the_number_of_market_topics_is_refused(tmp_path) -> None:
    """2026-10-20：第 5 題加進來時上限只有 4——寫了做不到的數字。原本只擋「有題目卻是 0」那個特例。"""
    from engine_b.routine_config import load_radar

    cfg = tmp_path / "routine.json"
    cfg.write_text(json.dumps({"radar": {"enabled": True, "max_items": 5, "timeout_minutes": 10,
                                         "market_topics": ["甲", "乙", "丙"], "max_market_items": 2}}), encoding="utf-8")
    with pytest.raises(ValueError, match="少於 market_topics 題數"):
        load_radar(cfg)


# ---------------------------------------------------------------------------
# 心跳段 3 那一行與快照鍵
# ---------------------------------------------------------------------------

def _record(tmp_path, steps) -> Path:
    path = tmp_path / "daily_run.json"
    path.write_text(json.dumps({"run_id": "r1", "steps": steps}), encoding="utf-8")
    return path


def test_the_heartbeat_line_reads_the_apply_summary() -> None:
    from crons.heartbeat import radar_rejected

    assert radar_rejected({"invalid": 1, "url_not_in_search": 2, "over_cap": 3, "duplicate": 9}) == 6   # 重複另計


def test_the_heartbeat_prints_counts_or_says_why_it_did_not_run(tmp_path) -> None:
    from crons.heartbeat import _radar_line

    now = datetime(2026, 10, 5, 0, 30, tzinfo=timezone.utc)
    ok = _record(tmp_path, [{"key": "01b_radar_prepare", "status": "ok"},
                            {"key": "01e_radar_apply", "status": "ok", "summary": {
                                "new": 2, "duplicate": 1, "url_not_in_search": 1, "over_cap": 0, "invalid": 0,
                                "related": 1, "relates_to_unknown": 2, "no_material_change": False, "searches": 4}}])
    line = _radar_line(now=now, record_path=ok)
    assert line == ("外部雷達：新 2｜重複 1｜拒收 1（網址不在搜尋結果 1、超過上限 0、欄位不合法 0）｜提到在盯的條件 1"
                    "（條件 id 對不上 2）｜搜尋 4 次（只寫 secondary lead，不喚醒 watch）")
    off = _record(tmp_path, [{"key": "01b_radar_prepare", "status": "skipped", "reason": "radar.enabled=false"},
                             {"key": "01e_radar_apply", "status": "skipped", "reason": "radar.enabled=false"}])
    assert _radar_line(now=now, record_path=off) == "外部雷達：沒跑（01e_radar_apply skipped：radar.enabled=false）"
    quiet = _record(tmp_path, [{"key": "01b_radar_prepare", "status": "ok"},
                               {"key": "01e_radar_apply", "status": "ok", "summary": {
                                   "new": 0, "duplicate": 0, "url_not_in_search": 0, "over_cap": 0, "invalid": 0,
                                   "related": 0, "no_material_change": True, "searches": 3}}])
    assert "沒有重要變化" in _radar_line(now=now, record_path=quiet)
    assert _radar_line(now=now, record_path=_record(tmp_path, [])) == "外部雷達：執行紀錄裡沒有雷達步驟"


def test_the_snapshot_has_the_four_radar_keys() -> None:
    from crons.heartbeat import SNAPSHOT_KEYS

    assert {"radar.new", "radar.duplicate", "radar.rejected", "radar.related"} <= set(SNAPSHOT_KEYS)


# ---------------------------------------------------------------------------
# 市場大事（2026-10-07 使用者：「我們還是必須知道 AI CAPEX 整個市場的大事，不能見樹不見林」）
# ---------------------------------------------------------------------------

def test_prepare_carries_the_market_topics_from_config(tmp_path) -> None:
    out = tmp_path / "radar_batch.json"
    summary = radar.prepare(RUN, out, max_items=5, today=TODAY, themes=THEMES, watches=WATCHES, registry=REG,
                            market_topics=["AI 資料中心資本支出", "政策與管制"], max_market_items=3, receipt_dir=tmp_path,
                            plan_context=_no_plan)
    assert summary["market_topics"] == 2 and summary["max_market_items"] == 3
    request = json.loads(out.read_text(encoding="utf-8"))["requests"][0]
    assert request["market_topics"] == ["AI 資料中心資本支出", "政策與管制"] and request["max_market_items"] == 3
    assert "market_topics" in llm_step.compose_radar_prompt([request])


def test_the_titles_accepted_in_the_last_seven_days_go_to_the_llm_so_the_same_story_is_not_returned_again(tmp_path) -> None:
    """2026-10-20：網址去重擋不住同一件事換網址（回放 7 天 43 則裡至少 5 則重複）——前 7 天收下的標題交給 LLM。"""
    from datetime import timedelta

    def receipt(day, titles):
        (tmp_path / f"radar_{day.isoformat()}.json").write_text(json.dumps(
            {"accepted": [{"title": t, "url": f"https://x.example/{i}"} for i, t in enumerate(titles)]}), encoding="utf-8")

    receipt(TODAY, ["今天的不算"])
    receipt(TODAY - timedelta(days=1), ["昨天 A", "昨天 B"])
    receipt(TODAY - timedelta(days=7), ["七天前"])
    receipt(TODAY - timedelta(days=8), ["八天前不算"])
    (tmp_path / f"radar_{(TODAY - timedelta(days=3)).isoformat()}.json").write_text("{壞掉", encoding="utf-8")
    rows = radar.recently_accepted(tmp_path, today=TODAY)
    assert [r["title"] for r in rows] == ["昨天 A", "昨天 B", "七天前"]           # 新的在前、讀不到的略過
    assert len(radar.recently_accepted(tmp_path, today=TODAY, cap=2)) == 2
    out = tmp_path / "radar_batch.json"
    summary = radar.prepare(RUN, out, max_items=5, today=TODAY, themes=THEMES, watches=WATCHES, registry=REG,
                            receipt_dir=tmp_path, plan_context=_no_plan)
    request = json.loads(out.read_text(encoding="utf-8"))["requests"][0]
    assert summary["recently_accepted"] == 3 and request["recently_accepted"][0] == {
        "date": (TODAY - timedelta(days=1)).isoformat(), "title": "昨天 A"}
    assert "recently_accepted" in llm_step.RADAR_PROMPT.read_text(encoding="utf-8")


def test_market_events_and_followed_topics_have_separate_caps(tmp_path) -> None:
    """市場大事不擠掉在追的題目，反過來也一樣：兩層各算各的上限。"""
    items = [_item(URL_A, scope="market"), _item(URL_B, scope="market"), _item(URL_C, scope="theme")]
    out, store = _apply(tmp_path, items, urls=[URL_A, URL_B, URL_C], max_items=1, max_market=1)
    s = out["summary"]
    assert (s["new"], s["new_market"], s["new_theme"], s["over_cap"]) == (2, 1, 1, 1)
    assert leads.lead_id_for(URL_B) not in store["leads"]
    assert store["leads"][leads.lead_id_for(URL_A)]["refs"]["radar_scope"] == "market"
    (tmp_path / "zero").mkdir()
    zero, _ = _apply(tmp_path / "zero", [_item(URL_A, scope="market")], urls=[URL_A], max_market=0)
    assert zero["summary"]["new"] == 0 and zero["summary"]["over_cap"] == 1   # 沒開市場層就一則都不收


def test_an_unknown_scope_is_counted_and_kept_off_the_market_quota(tmp_path) -> None:
    out, store = _apply(tmp_path, [_item(URL_A, scope="headline"), _item(URL_B)], urls=[URL_A, URL_B], max_market=0)
    s = out["summary"]
    assert s["scope_unknown"] == 2 and s["new_theme"] == 2 and s["new_market"] == 0
    assert store["leads"][leads.lead_id_for(URL_A)]["refs"]["radar_scope"] == "theme"


def test_the_receipt_keeps_the_search_title_and_the_llm_fact_for_the_daily_brief(tmp_path) -> None:
    out, _store = _apply(tmp_path, [_item(URL_A, scope="watch")], urls=[URL_A])
    receipt = json.loads((tmp_path / "receipts" / f"radar_{TODAY.isoformat()}.json").read_text(encoding="utf-8"))
    row = receipt["accepted"][0]
    assert row["scope"] == "watch" and row["fact"] == "Coherent 宣布 CW 雷射產能擴充" and row["why"] == "碰到供給側的條件"
    assert row["publisher"] == "Example News"


# ---------------------------------------------------------------------------
# 讀過的層每日輪替（雷達精進 C3，2026-10-21；使用者 10-20：與 themes.txt 並存）
# ---------------------------------------------------------------------------

def _plan_ctx(n=10):
    nodes = [f"tech:n{i:02d}" for i in range(n)]
    sem = {"kind": "semantic_condition", "status": "active", "entities": ["co:coherent"]}
    watches = [
        {**sem, "watch_id": "ew_r", "source_ref": "reading:sr_1#1", "condition": "讀圖反證"},
        {**sem, "watch_id": "ew_n", "source_ref": "layer_note:ln_9#1", "condition": "層說明的條件"},
        {**sem, "watch_id": "ew_b", "source_ref": "brief:ib_aaa#1", "condition": "騎 n03 的敘事條件", "condition_role": "confirm"},
        {**sem, "watch_id": "ew_far", "source_ref": "reading:sr_8#1", "condition": "今天沒輪到的層"},
        {**sem, "watch_id": "ew_o", "source_ref": "brief:ib_zzz#1", "condition": "掛不到任何層"},
        {**sem, "watch_id": "ew_done", "status": "consumed", "source_ref": "reading:sr_1#2", "condition": "已收"},
    ]
    ctx = SimpleNamespace(
        readings={node: SimpleNamespace(reading_id=f"sr_{i}") for i, node in enumerate(nodes)},
        briefs=[SimpleNamespace(ticker="AAA", rides=(SimpleNamespace(node="tech:n03"),)), SimpleNamespace(ticker="ZZZ", rides=())],
        watches=watches, watch_owner={"ew_b": ["AAA"], "ew_o": ["ZZZ"]},
        reading_entities={"tech:n01": {"co:coherent": {"supply_side"}, "co:buyer": {"demand_side"}}},
        companies={"co:coherent": SimpleNamespace(display_name="Coherent Corp.")},
        node_names={"tech:n01": "CW DFB laser (CW DFB)"})
    return ctx, {"ln_9": "tech:n02"}


def _day_starting_at_zero():
    from datetime import timedelta

    return next(TODAY + timedelta(days=d) for d in range(5) if (TODAY + timedelta(days=d)).toordinal() % 5 == 0)


def test_the_rotation_takes_k_consecutive_layers_a_day_and_covers_every_layer_in_ceil_n_over_k_days() -> None:
    from datetime import timedelta

    nodes = [f"tech:l{i:02d}" for i in range(58)]
    days = [radar.rotation(nodes, TODAY + timedelta(days=d)) for d in range(8)]
    assert all(len(d) == radar.ROTATION_K for d in days)
    assert set().union(*days) == set(nodes)                                 # ⌈58/8⌉＝8 天輪完
    assert nodes.index(days[1][0]) == (nodes.index(days[0][-1]) + 1) % 58   # 相鄰兩天銜接
    assert radar.rotation(["b", "a"], TODAY) in (["a", "b"], ["b", "a"]) and radar.rotation([], TODAY) == []


def test_the_plan_sends_only_conditions_hung_on_todays_layers_with_short_ids_mapped_back() -> None:
    """條件掛在哪層：讀圖反證 → 那份讀圖的節點；層說明 → 那份說明的節點；敘事 → 它騎的層（歸屬問 watch_owner）。"""
    ctx, notes = _plan_ctx()
    plan = radar.layer_plan(ctx, today=_day_starting_at_zero(), registry=REG, note_node=notes)
    assert [r["node"] for r in plan["layers"]] == [f"tech:n{i:02d}" for i in range(8)]
    n01 = plan["layers"][1]
    assert n01 == {"node": "tech:n01", "name": "CW DFB laser (CW DFB)", "supply_side": ["Coherent Corp."], "more_supply": 0,
                   "conditions": 1}
    hung = {plan["condition_ids"][c["id"]]: c for c in plan["conditions"]}
    assert {"ew_b", "ew_n", "ew_r"} <= set(hung) and "ew_far" not in hung and "ew_done" not in hung
    assert hung["ew_b"]["layers"] == ["tech:n03"] and hung["ew_b"]["role"].startswith("加碼條件")
    assert all("watch_id" not in c for c in plan["conditions"]) and plan["conditions"][0]["id"] == "c01"
    assert plan["pool"] == 10 and plan["orphans"] == 1


def test_the_plan_widens_k_so_every_layer_is_searched_within_seven_days_as_the_pool_grows() -> None:
    """10-21 試跑：58 層、固定每天 8 層，7 天只輪到 56——K 改成 max(8, ⌈層數÷7⌉)。"""
    from datetime import timedelta

    for n in (10, 58, 100):
        ctx, notes = _plan_ctx(n)
        week = [radar.layer_plan(ctx, today=TODAY + timedelta(days=d), registry=REG, note_node=notes)
                for d in range(radar.ROTATION_DAYS)]
        assert set().union(*({r["node"] for r in p["layers"]} for p in week)) == set(ctx.readings), n


def test_a_condition_hung_on_no_layer_is_still_sent_once_every_seven_days() -> None:
    from datetime import timedelta

    ctx, notes = _plan_ctx()
    plans = [radar.layer_plan(ctx, today=TODAY + timedelta(days=d), registry=REG, note_node=notes)
             for d in range(radar.ROTATION_DAYS)]
    assert [p["orphans_today"] for p in plans].count(1) == 1
    assert sum("ew_o" in p["condition_ids"].values() for p in plans) == 1     # 真的交給 LLM，不只是計數


def test_prepare_with_the_plan_sends_layers_and_keeps_the_id_map_out_of_the_prompt(tmp_path) -> None:
    out = tmp_path / "radar_batch.json"
    summary = radar.prepare(RUN, out, max_items=5, today=_day_starting_at_zero(), themes=THEMES, watches=WATCHES,
                            registry=REG, receipt_dir=tmp_path, plan_context=_plan_ctx)
    assert (summary["rotation_layers"], summary["rotation_pool"], summary["rotation_error"]) == (8, 10, None)
    batch = json.loads(out.read_text(encoding="utf-8"))
    request = batch["requests"][0]
    assert batch["rotation_pool"] == 10 and set(batch["condition_ids"].values()) >= {"ew_b", "ew_n", "ew_r"}
    prompt = llm_step.compose_radar_prompt(batch["requests"])
    assert "rotation_layers" in prompt and "CW DFB laser" in prompt and "ew_r" not in prompt   # LLM 只看到短 id


def test_apply_maps_short_ids_back_checks_the_layer_and_counts_seven_day_coverage(tmp_path) -> None:
    from datetime import timedelta

    receipts = tmp_path / "receipts"
    receipts.mkdir()
    for back, nodes in ((1, ["tech:n05"]), (7, ["tech:too_old"])):
        (receipts / f"radar_{(TODAY - timedelta(days=back)).isoformat()}.json").write_text(
            json.dumps({"rotation": nodes}), encoding="utf-8")
    items = [_item(URL_A, relates_to=["c1"], layer="tech:n01"),            # c1 也認成 c01
             _item(URL_B, relates_to=["c09", "c02"], layer="tech:zz")]       # c09 不存在；層不是今天的
    out, store = _apply(tmp_path, items, urls=[URL_A, URL_B], watched=[{"id": "c01"}, {"id": "c02"}],
                        envelope={"condition_ids": {"c01": "ew_0762_2026-10-17", "c02": "ew_r"}, "rotation_pool": 10},
                        layers=[{"node": "tech:n01"}, {"node": "tech:n02"}])
    s = out["summary"]
    refs_a = store["leads"][leads.lead_id_for(URL_A)]["refs"]
    refs_b = store["leads"][leads.lead_id_for(URL_B)]["refs"]
    assert refs_a["relates_to"] == ["ew_0762_2026-10-17"] and refs_a["radar_layer"] == "tech:n01"
    assert refs_b["relates_to"] == ["ew_r"] and "radar_layer" not in refs_b
    assert (s["relates_to_unknown"], s["layer_unknown"], s["new_layer"]) == (1, 1, 1)
    assert (s["rotation_layers"], s["rotation_pool"], s["rotation_covered_7d"]) == (2, 10, 3)   # n01、n02＋昨天的 n05
    receipt = json.loads((receipts / f"radar_{TODAY.isoformat()}.json").read_text(encoding="utf-8"))
    assert receipt["rotation"] == ["tech:n01", "tech:n02"] and receipt["accepted"][0]["layer"] == "tech:n01"


def test_the_heartbeat_line_prints_the_rotation_or_why_it_fell_back(tmp_path) -> None:
    from crons.heartbeat import _radar_line

    now = datetime(2026, 10, 5, 0, 30, tzinfo=timezone.utc)
    base = {"new": 1, "duplicate": 0, "url_not_in_search": 0, "over_cap": 0, "invalid": 0, "related": 0,
            "relates_to_unknown": 0, "searches": 30}
    ok = _record(tmp_path, [{"key": "01e_radar_apply", "status": "ok", "summary": {
        **base, "rotation_layers": 8, "rotation_covered_7d": 50, "rotation_pool": 58, "new_layer": 1, "layer_unknown": 0}}])
    assert "｜輪替層 8（近 7 天輪到 50／58 層；從層收下 1、層 id 對不上 0）" in _radar_line(now=now, record_path=ok)
    broken = _record(tmp_path, [{"key": "01e_radar_apply", "status": "ok", "summary": {
        **base, "rotation_layers": 0, "rotation_error": "RuntimeError: x"}}])
    assert "輪替層沒算出來（RuntimeError: x；退回全量條件）" in _radar_line(now=now, record_path=broken)


def test_least_recently_rotated_first_keeps_gaps_bounded_when_the_pool_changes_or_a_day_is_skipped() -> None:
    """10-21 回放：日期序號取模在池大小一變時排列平移（400 次模擬 215 次空窗 10–12 天），沒跑的那天也不補。
    改成最久沒輪到的先：新讀的層隔天就輪到；空窗上限＝⌈n/k⌉＋沒跑的天數。"""
    import math
    from datetime import timedelta

    nodes = [f"tech:l{i:02d}" for i in range(58)]
    last, gaps = {}, []
    for d in range(40):
        day = TODAY + timedelta(days=d)
        if d == 10:
            nodes.append("tech:new_a")
        if d == 23:
            nodes.append("tech:new_b")
        if d == 20:
            nodes.remove("tech:l03")
        if d in (15, 16):                       # 雷達沒跑：沒有收據，last 不更新
            continue
        k = max(radar.ROTATION_K, math.ceil(len(nodes) / radar.ROTATION_DAYS))
        today_nodes = radar.rotation(nodes, day, k, last or None)
        if d == 10:
            assert "tech:new_a" in today_nodes
        if d == 23:
            assert "tech:new_b" in today_nodes
        for n in today_nodes:
            if n in last:
                gaps.append((day - last[n]).days)
            last[n] = day
    assert max(gaps) <= math.ceil(60 / 9) + 2                     # ⌈n/k⌉＋沒跑的 2 天


def test_last_rotated_reads_the_receipts_and_prepare_starts_with_what_waited_longest(tmp_path) -> None:
    from datetime import timedelta

    def receipt(back, nodes):
        (tmp_path / f"radar_{(TODAY - timedelta(days=back)).isoformat()}.json").write_text(
            json.dumps({"rotation": nodes}), encoding="utf-8")

    receipt(3, ["tech:n00", "tech:n08"])
    receipt(1, [f"tech:n{i:02d}" for i in range(8)])
    (tmp_path / f"radar_{(TODAY - timedelta(days=2)).isoformat()}.json").write_text("{壞掉", encoding="utf-8")
    last = radar.last_rotated(tmp_path, today=TODAY)
    assert last["tech:n00"] == TODAY - timedelta(days=1) and last["tech:n08"] == TODAY - timedelta(days=3)
    out = tmp_path / "radar_batch.json"
    radar.prepare(RUN, out, max_items=5, today=TODAY, themes=THEMES, watches=WATCHES, registry=REG,
                  receipt_dir=tmp_path, plan_context=_plan_ctx)
    nodes = [r["node"] for r in json.loads(out.read_text(encoding="utf-8"))["requests"][0]["rotation_layers"]]
    assert nodes[:2] == ["tech:n09", "tech:n08"] and "tech:n07" not in nodes   # 從沒輪到的先、昨天輪過的最後


def test_a_condition_hung_only_on_a_layer_without_a_current_reading_falls_back_to_the_orphans() -> None:
    """層說明指到的節點若讀圖已撤回（不在輪替池），那條條件不得每天都不出現又沒計數（INV-3）。"""
    ctx, _notes = _plan_ctx()
    plan = radar.layer_plan(ctx, today=_day_starting_at_zero(), registry=REG, note_node={"ln_9": "tech:gone"})
    assert plan["orphans"] == 2 and "ew_n" not in {plan["condition_ids"][c["id"]] for c in plan["conditions"]
                                                    if c["layers"]}


def test_the_schema_asks_for_the_layer_and_the_prompt_allows_32_searches() -> None:
    schema = json.loads(llm_step.RADAR_SCHEMA.read_text(encoding="utf-8"))
    assert "layer" in schema["properties"]["items"]["items"]["required"]
    text = llm_step.RADAR_PROMPT.read_text(encoding="utf-8")
    assert "總共 32 次以內" in text and "rotation_layers" in text
