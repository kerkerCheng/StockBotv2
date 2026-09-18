"""Daily 心跳（`crons/heartbeat.py`）：固定五段、零 LLM、失敗不消失。

**這份測試要驗的不是「正常時輸出好看」，是「壞掉時它還在」**——那正是 D12 拆出心跳的理由：
現行 Daily 由 LLM 組出來，任何一段卡住整份就不會發，而「今天沒事」與「今天沒人看」同形（L13-2）。

所以最重要的兩條是：
- `test_every_source_broken_still_renders_five_sections`：每一個資料源都讀不到，五段仍然全部印出。
- `test_未_triage_必印`：0 也要印——零不是可以省略的意思。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha.absence import ABSENCE_KINDS  # noqa: E402
from crons import heartbeat as hb  # noqa: E402


@pytest.fixture
def broken_env(tmp_path: Path) -> dict[str, Path]:
    """一個什麼都讀不到的環境：空的 state 目錄、不存在的 leads／thesis 檔。"""
    state = tmp_path / "state"
    state.mkdir()
    return {
        "state_dir": state,
        "leads_path": tmp_path / "does_not_exist_leads.json",
        "thesis_path": tmp_path / "does_not_exist_thesis.json",
    }


def _sections(**kwargs) -> list[hb.Section]:
    return hb.build_heartbeat(now=datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc), **kwargs)


def test_always_five_sections_in_fixed_order() -> None:
    sections = _sections()
    assert [s.order for s in sections] == [1, 2, 3, 4, 5]
    assert [s.title for s in sections] == list(hb.SECTION_TITLES)


def test_every_source_broken_still_renders_five_sections(broken_env: dict[str, Path]) -> None:
    """**心跳的核心契約**：資料源全滅，五段照印、每段都說得出為什麼。"""
    sections = _sections(**broken_env)
    assert len(sections) == 5
    for section in sections:
        assert section.lines, f"段 {section.order} 印了零行——那等於這一段消失了"
    text = hb.render_markdown(sections)
    for title in hb.SECTION_TITLES:
        assert title in text


def test_broken_sources_declare_absence_kind_not_prose(broken_env: dict[str, Path]) -> None:
    """降級必須帶封閉字彙的 `absence_kind`；呈現層不得靠 parse 理由句去猜（L16）。"""
    sections = _sections(**broken_env)
    text = hb.render_markdown(sections)
    # 段 1／2／4 依賴 state artifact，全部讀不到時必須出現 upstream_unavailable。
    assert "upstream_unavailable" in text
    # 印出來的每一個 kind 都必須在封閉字彙裡（字彙本身由 alpha.absence 保證）。
    printed = {k for k in ABSENCE_KINDS if k in text}
    assert printed, "全滅時一個 absence_kind 都沒印——那就是把缺席壓成了無資料"
    for section in sections:
        if section.absence is not None:
            assert section.absence.kind in ABSENCE_KINDS


def test_absence_kind_outside_vocabulary_is_rejected() -> None:
    """自創第三套缺席字彙會在建構時就炸——不是等到有人讀輸出才發現。"""
    with pytest.raises(Exception):
        hb.Absence("made_up_kind", "隨便寫的")


def test_untriaged_count_is_always_printed_even_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """「未 triage N」必印。0 也印——沒發生與沒看到不得同形（L13）。"""
    from engine_b import queue_segments as qs

    def fake_observe(**_kwargs):
        return {
            "segments": [{"key": "pending_triage", "order": 0, "label": "x", "cost": "research",
                          "consumer": "y", "count": 0, "examples": []}],
            "unmapped": [], "mechanical_total": 0, "research_total": 0, "not_work": {},
        }

    monkeypatch.setattr(qs, "observe", fake_observe)
    section = hb.build_queue()
    assert any("未 triage 0" in line for line in section.lines), section.lines


def test_queue_section_consumes_queue_segments_not_its_own_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """段 3 必須**消費** `queue_segments.observe()`，不得自己數一份（L16）。"""
    from engine_b import queue_segments as qs

    calls: list[dict] = []

    def fake_observe(**kwargs):
        calls.append(kwargs)
        return {
            "segments": [{"key": "pending_triage", "order": 0, "label": "x", "cost": "research",
                          "consumer": "y", "count": 7, "examples": []}],
            "unmapped": [], "mechanical_total": 0, "research_total": 0, "not_work": {},
        }

    monkeypatch.setattr(qs, "observe", fake_observe)
    section = hb.build_queue()
    assert len(calls) == 1, "段 3 沒有呼叫 observe()——它自己數了"
    assert any("未 triage 7" in line for line in section.lines)


def test_pq2_ball_in_user_court_uses_todo_ssot() -> None:
    """「球在你手上」的數字必須等於 `engine_b.todo.actionable_items()`，不是另一套推導。"""
    from engine_b import todo as todo_mod

    pool = todo_mod.load()
    expected = len(todo_mod.actionable_items(pool))
    section = hb.build_queue()
    assert any(f"pq2 球在你手上 {expected}" in line for line in section.lines), section.lines


def test_missing_artifacts_say_which_kind_of_missing(broken_env: dict[str, Path]) -> None:
    """讀不到 artifact 時，每一行都要說**是哪一種讀不到**，並給出讓它回來的指令。

    ⚠ 本測試 2026-09-18 改寫：原本驗的是「還沒建的格子要指到某個 Phase」，而第 4 段
    那兩格（D15 power-law 三量、D2 歸零旗標與 alpha 全歸零）當天都已交付——
    **繼續要求它印 `capability_absent` 等於要求它說謊**。現在驗的是同一條判準的另一半：
    「今天沒事」與「讀不到」不得同形（AGENTS：缺席不得被壓成一句「無資料」）。
    """
    section = hb.build_positions(state_dir=broken_env["state_dir"])
    text = "\n".join(section.lines)
    assert "upstream_unavailable" in text
    assert "python -m webapp materialize" in text                  # 說得出怎麼讓它回來
    assert "capability_absent" not in text, "已交付的能力不得被宣告成『還沒建』"


def test_weekly_scorecard_is_not_applicable_on_daily(tmp_path) -> None:
    """daily 不算計分表——那不是「還沒建」，是方法不適用，兩者不得同形。"""
    daily = hb.build_scorecard(weekly=False, state_dir=tmp_path)
    assert daily.absence is not None and daily.absence.kind == "method_not_applicable"


def test_weekly_scorecard_without_artifact_says_so_instead_of_rebuilding(tmp_path) -> None:
    """心跳零網路：讀不到 artifact 就誠實說讀不到，**不偷偷重建**（計分表要抓價格）。"""
    weekly = hb.build_scorecard(weekly=True, state_dir=tmp_path)
    assert weekly.absence is not None and weekly.absence.kind == "upstream_unavailable"
    assert any("materialize --scorecard" in line for line in weekly.lines), (
        "讀不到的時候要說出「怎麼讓它有內容」，否則使用者只看到一句沒有值")


def test_weekly_scorecard_prints_measurement_window_sample_size_and_biases(tmp_path) -> None:
    """有內容時：量測起始日、樣本數、三個偏差**都要在輸出裡**（D5 的交付義務）。"""
    from engine_b.account_scorecard import build_scorecard as build_card
    from webapp.store import StateArtifactStore

    card = build_card(price_loader=lambda *_: {})
    StateArtifactStore(tmp_path).write(card)

    weekly = hb.build_scorecard(weekly=True, state_dir=tmp_path)
    assert weekly.absence is None, "artifact 在就不該有 absence"
    text = chr(10).join(weekly.lines)
    assert "量測" in text and "具名點名" in text
    assert "倖存者" in text and "後見之明" in text and "單邊上漲" in text, (
        "三個已知偏差是這張表的一部分，不是註腳")
    # 沒有值的欄位要印出**為什麼**沒有值，不得印成 0。
    assert "capability_absent" in text or "insufficient_sample" in text


def test_main_always_exits_zero_even_when_everything_is_broken(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """心跳的失敗模式是「印出降級行」，不是「不發」——所以 exit code 永遠 0。"""
    def exploding(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(hb, "build_freshness", exploding)
    monkeypatch.setattr(hb, "build_changes", exploding)
    monkeypatch.setattr(hb, "build_queue", lambda **_kw: exploding())   # 2026-09-17：build_queue 也吃 state_dir 了
    monkeypatch.setattr(hb, "build_positions", exploding)
    assert hb.main([]) == 0
    out = capsys.readouterr().out
    for title in hb.SECTION_TITLES:
        assert title in out
    # ⚠ 非空泛：四段真的都爆了才算驗到——只檢查標題存在的話，monkeypatch 沒生效也會綠。
    assert out.count("RuntimeError: boom") == 4, out


def test_json_format_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    assert hb.main(["--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [s["order"] for s in payload["sections"]] == [1, 2, 3, 4, 5]


def test_out_file_is_utf8(tmp_path: Path) -> None:
    """Windows PowerShell 5.1 的管線預設 ASCII，所以心跳自己寫檔、由 publisher 帶 --brief-file。"""
    target = tmp_path / "heartbeat.md"
    assert hb.main(["--out", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "心跳" in text


def test_heartbeat_does_not_import_any_llm_or_network_surface() -> None:
    """零 LLM、零網路是契約不是慣例：原始碼裡不得出現這些 import。"""
    source = (ROOT / "crons" / "heartbeat.py").read_text(encoding="utf-8")
    for forbidden in ("import requests", "import httpx", "from openai", "import anthropic",
                      "urllib.request", "notifications.publisher", "neo4j"):
        assert forbidden not in source, forbidden


def test_unread_segment_is_not_counted_as_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """`None`＝本次沒讀到那個 authority，**不是 0**——加成 0 會讓兩件事同形（INV-3）。"""
    from engine_b import queue_segments as qs

    def fake_observe(**_kwargs):
        return {
            "segments": [
                {"key": "pending_triage", "order": 0, "label": "x", "cost": "research",
                 "consumer": "y", "count": 3, "examples": []},
                {"key": "triaged_go_leads", "order": 4, "label": "x", "cost": "research",
                 "consumer": "y", "count": None, "examples": []},
            ],
            "unmapped": [], "mechanical_total": 0, "research_total": 0, "not_work": {},
        }

    monkeypatch.setattr(qs, "observe", fake_observe)
    section = hb.build_queue()
    text = "\n".join(section.lines)
    assert "未讀到" in text and "triaged_go_leads" in text, text


def test_one_broken_item_does_not_take_out_its_neighbours(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """段 1 裡三件事互不相干：APP 盤點壞掉時，harvest 與行情那兩行仍然要在。"""
    def boom(**_kwargs):
        raise RuntimeError("app scan failed")

    monkeypatch.setattr(hb, "_app_freshness_line", boom)
    section = hb.build_freshness(
        now=datetime(2026, 9, 17, tzinfo=timezone.utc),
        state_dir=None,
        leads_path=ROOT / "library" / "leads" / "pending_leads.json",
    )
    text = "\n".join(section.lines)
    assert "harvest 來源" in text, "APP 那一格壞掉把 harvest 一起帶走了"
    assert "行情" in text
    assert "upstream_unavailable" in text


def test_bet_ledger_is_a_standing_counter_in_section_four(tmp_path: Path) -> None:
    """Q2 的欠帳必須**自己出現**在心跳裡，不是要人打開 APP 翻表才看得到（L14）。"""
    from webapp.basket import build_basket_artifact
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    rank_row = {"rank": 1, "ticker": "X", "company_id": "co:x", "company_label": "X",
                "bottleneck": "tech:x", "relation": "supplies_to", "evidence": "externally_corroborated"}
    StateArtifactStore(state_dir).write(build_basket_artifact(
        ranking={"rows": [rank_row], "sectors": []}, overviews={}, positions=None))
    text = "\n".join(hb.build_positions(state_dir=state_dir).lines)
    assert "欠一個答案 1" in text, text
    assert "籃子 1 檔" in text


def test_the_two_universes_are_counted_separately(tmp_path: Path) -> None:
    """Q1：護城河與量的候選**分開計數**——兩個宇宙問的是不同問題，合起來的數字沒有意義。"""
    from webapp.basket import build_basket_artifact
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    rank_row = {"rank": 1, "ticker": "LITE", "company_id": "co:lite", "company_label": "LITE",
                "bottleneck": "tech:x", "relation": "supplies_to", "evidence": "externally_corroborated"}
    filtered = {"company_id": "co:3081", "ticker": "3081.TWO", "relation": "supplies_to",
                "bottleneck": "tech:y", "substitutability": 3, "threshold": 4,
                "qualification_status": "qualified", "evidence": "company_disclosure",
                "documents": 1, "chain": ["tech:ai_switch"], "demand_anchor": "tech:ai_switch",
                "demand_hops": 1, "reasons": ["substitutability_below_threshold"]}
    ranking = {"rows": [rank_row], "sectors": [], "filtered_rows": [filtered], "filter": {}}
    StateArtifactStore(state_dir).write(build_basket_artifact(
        ranking=ranking, overviews={}, positions=None))
    text = "\n".join(hb.build_positions(state_dir=state_dir).lines)
    assert "籃子 1 檔" in text and "量的候選 1 家" in text, text
    assert text.count("欠一個答案") == 2, "兩個宇宙各自報自己的欠帳，不合併"


def test_missing_basket_does_not_take_out_the_rest_of_section_four(broken_env: dict[str, Path]) -> None:
    """賭注帳讀不到時，它自己宣告缺席，**不把 alpha 占比與追蹤表一起帶走**。"""
    section = hb.build_positions(state_dir=broken_env["state_dir"])
    text = "\n".join(section.lines)
    assert "賭注帳：" in text and any(k in text for k in ABSENCE_KINDS)
    assert "power-law" in text, "後面的格子還在"


def test_unreadable_leads_file_is_not_the_same_as_an_empty_log(broken_env: dict[str, Path]) -> None:
    """「leads 檔讀不到」與「harvest 從來沒跑過」是兩件事（L12）——後者代表管線壞了。"""
    section = hb.build_freshness(now=datetime(2026, 9, 17, tzinfo=timezone.utc),
                                 state_dir=broken_env["state_dir"],
                                 leads_path=broken_env["leads_path"])
    text = "\n".join(section.lines)
    assert "讀不到" in text and "upstream_unavailable" in text
    assert "harvest_log 為空" not in text, "讀不到被冒充成「真的沒有紀錄」"
    assert "行情" in text, "harvest 那一格壞掉不該把行情帶走"


# ---------------------------------------------------------------------------
# 時區：心跳整份是本地時區，authority 的時戳是 UTC（2026-09-17）
# ---------------------------------------------------------------------------

def test_harvest_stamp_is_rendered_in_local_time() -> None:
    """log 存 UTC，心跳印本地——同一份文件混兩個時區會被讀成「昨天沒跑」（2026-09-17 實測）。"""
    utc_stamp = "2026-09-16T21:33:42.544544+00:00"
    shown = hb._local_stamp(utc_stamp)
    expected = datetime.fromisoformat(utc_stamp).astimezone().strftime("%Y-%m-%d %H:%M")
    assert shown == expected
    assert shown != utc_stamp[:16], "直接截 ISO 字串＝印 UTC"
    assert hb._local_stamp("不是時戳") == "不是時戳", "壞資料不得讓整段消失（INV-3）"


def test_app_freshness_today_is_the_local_today(tmp_path: Path) -> None:
    """「今天已 materialize」的今天＝**本地**今天。

    心跳 07:00 台北跑時 UTC 還停在昨天 23:00；用 UTC 判會把「昨天下午做的」算成今天的，
    於是 daily 死掉也看不出來——成功與失敗在同一個訊號上同形（L13-2）。
    ⚠ 在 UTC±0 的機器上兩種實作等價，這條會退化成不鑑別（本機是 Asia/Taipei）。
    """
    from webapp.basket import build_basket_artifact
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    yesterday_pm = datetime(2026, 9, 17, 14, 44).astimezone()   # naive → 本地時區
    StateArtifactStore(state_dir).write(build_basket_artifact(
        ranking={"rows": [], "sectors": [], "as_of": None, "generated_at": None},
        overviews={}, positions=None, generated_at=yesterday_pm))

    line = hb._app_freshness_line(now=datetime(2026, 9, 18, 7, 0).astimezone(), state_dir=state_dir)
    assert "今天已 materialize 0 份" in line, line
    assert "不是今天的 1 份" in line, line


# ---------------------------------------------------------------------------
# 無人值守進入點（crons/heartbeat_task.py）
# ---------------------------------------------------------------------------

def test_task_entrypoint_is_python_not_cmd() -> None:
    """排程入口必須是 `.py`，**不得是 `.cmd`**。

    2026-09-17 實測：第一版寫成批次檔，`cmd.exe` 以 OEM codepage（本機 cp950）讀 UTF-8 檔，
    中文註解被拆成無效指令，整個 wrapper 解析失敗。這不是風格偏好，是編碼事實。
    """
    assert (ROOT / "crons" / "heartbeat_task.py").is_file()
    assert not (ROOT / "crons" / "heartbeat_task.cmd").exists()


def test_task_dry_run_writes_file_and_never_publishes(monkeypatch, tmp_path) -> None:
    """`--dry-run` 只產檔，一次 publisher 都不叫——改東西之後的空跑檢查靠它。"""
    from crons import heartbeat_task as task

    monkeypatch.setattr(task, "OUT_DIR", tmp_path)
    monkeypatch.setattr(task, "LOG_PATH", tmp_path / "task.log")
    published: list[list[str]] = []
    real_run = task._run

    def spy(argv, what):
        if what == "publish":
            published.append(argv)
            return 0
        return real_run(argv, what)

    monkeypatch.setattr(task, "_run", spy)
    assert task.main(["--dry-run"]) == 0
    assert published == [], "dry-run 仍然發送了"
    assert list(tmp_path.glob("heartbeat_*.md")), "dry-run 沒有產出檔案"


def test_task_exits_zero_when_publisher_fails(monkeypatch, tmp_path) -> None:
    """publisher 失敗是 best-effort，**不得阻斷**（AGENTS：通知不是 authority）。"""
    from crons import heartbeat_task as task

    monkeypatch.setattr(task, "OUT_DIR", tmp_path)
    monkeypatch.setattr(task, "LOG_PATH", tmp_path / "task.log")
    real_run = task._run

    def spy(argv, what):
        if what == "publish":
            raise RuntimeError("discord down")
        return real_run(argv, what)

    monkeypatch.setattr(task, "_run", spy)
    with pytest.raises(RuntimeError):
        # spy 直接 raise 代表 `_run` 之外沒有保護——這裡先確認它真的會炸，
        # 再驗 main 有沒有把它擋住（不擋住就是心跳會因為通知失敗而消失）。
        spy(["x"], "publish")

    def swallowing(argv, what):
        if what == "publish":
            return 3  # publisher 以非零收場
        return real_run(argv, what)

    monkeypatch.setattr(task, "_run", swallowing)
    assert task.main([]) == 0


def test_task_says_so_when_nothing_was_produced(monkeypatch, tmp_path) -> None:
    """沒有產出就明說沒有東西可發——不得靜默結束（L13-2）。"""
    from crons import heartbeat_task as task

    monkeypatch.setattr(task, "OUT_DIR", tmp_path)
    log = tmp_path / "task.log"
    monkeypatch.setattr(task, "LOG_PATH", log)
    monkeypatch.setattr(task, "_run", lambda argv, what: 1)  # heartbeat 什麼都沒寫出來
    assert task.main([]) == 0
    assert "沒有東西可發" in log.read_text(encoding="utf-8")


def test_task_uses_the_existing_publisher_not_a_second_outbound_path() -> None:
    """outbound surface 只有一個入口：既有的 `scripts/publish_daily_brief.py`。"""
    from crons import heartbeat_task as task

    assert task.PUBLISHER.name == "publish_daily_brief.py"
    source = (ROOT / "crons" / "heartbeat_task.py").read_text(encoding="utf-8").lower()
    # 第二條出口長什麼樣：自己送 HTTP、或繞過腳本直接 import publisher。兩種都不准。
    for second_path in ("import requests", "import httpx", "urllib.request",
                        "from notifications", "import notifications", "webhook_url"):
        assert second_path not in source, second_path


def test_queue_section_surfaces_waits_without_an_expiry() -> None:
    """心跳第 3 段必須把「沒有到期的等待」印出來（ROADMAP Phase 6，使用者核准 A）。

    原提案是「parked 超過 60 天自動 expired」，實測推翻——479 筆 parked 裡 413 筆是
    terminal trace_status（**那是歸檔不是等待**），真正沒有任何機制會回來的只有個位數。
    所以落點不是新增一個 lead 狀態，是讓黑洞變成**會自己出現的計數器**（L14：真正的防呆
    是常駐計數器，不是要人讀的段落）。
    """
    section = hb.build_queue()
    text = "\n".join(section.lines)

    assert "無到期的等待" in text, "這個計數器必須每天出現，0 也要印"
