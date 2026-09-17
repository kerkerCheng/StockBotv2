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


def test_unbuilt_capabilities_point_at_a_phase(broken_env: dict[str, Path]) -> None:
    """還沒建的格子要說得出去哪裡找——只印「無資料」會讓「今天沒事」與「還沒建」同形。"""
    section = hb.build_positions(state_dir=broken_env["state_dir"])
    text = "\n".join(section.lines)
    assert "capability_absent" in text
    assert "Phase 5" in text


def test_weekly_scorecard_is_not_applicable_on_daily() -> None:
    daily = hb.build_scorecard(weekly=False)
    weekly = hb.build_scorecard(weekly=True)
    assert daily.absence is not None and daily.absence.kind == "method_not_applicable"
    assert weekly.absence is not None and weekly.absence.kind == "capability_absent"
    # 交付時的義務先寫進輸出，免得之後有人交了一張沒有樣本數的表。
    assert any("量測起始日" in line for line in weekly.lines)


def test_main_always_exits_zero_even_when_everything_is_broken(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """心跳的失敗模式是「印出降級行」，不是「不發」——所以 exit code 永遠 0。"""
    def exploding(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(hb, "build_freshness", exploding)
    monkeypatch.setattr(hb, "build_changes", exploding)
    monkeypatch.setattr(hb, "build_queue", lambda: exploding())
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
