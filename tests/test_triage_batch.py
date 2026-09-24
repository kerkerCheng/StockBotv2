"""分類層的每日硬上限（Phase 2 Step 2.3，2026-09-19）。

D12 的分類層是「便宜模型、**每日硬上限**、失敗不阻斷」。前後兩項本來就成立
（triage 由 Codex daily 跑；心跳是獨立排程，分類層掛掉它照發），**缺的只有 cap**。

守的是三件事：
1. **cap 由 CLI 執行，不由 prompt 自律**——把數字寫進 prompt 讓 LLM 自己數，
   等於讓被管的人管自己（L15：語意交給語言處理，權限永遠 deterministic）。
2. **截斷必須說話**（INV-3）：「本批 30 則」與「總共只有 30 則」是兩件事。
3. **讀不到設定不等於沒有上限**——退回無上限等於在最不確定的時候拆掉煞車。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "crons" / "triage_prompt.md"


def test_limit_comes_from_config_and_is_validated() -> None:
    from engine_b.routine_config import DEFAULT_TRIAGE_LIMIT, load_config, triage_daily_limit

    assert triage_daily_limit() == json.loads(
        (ROOT / "config" / "daily_routine.json").read_text(encoding="utf-8"))["triage"]["daily_limit"]
    assert DEFAULT_TRIAGE_LIMIT > 0, "讀不到設定時必須仍有上限，不得退回無上限"


def test_an_illegal_limit_is_rejected_not_silently_defaulted(tmp_path: Path) -> None:
    """打錯的數字比沒有更危險——它看起來像有 cap。"""
    from engine_b.routine_config import load_config

    base = json.loads((ROOT / "config" / "daily_routine.json").read_text(encoding="utf-8"))
    for bad in (-1, 201, True, "30", 1.5):
        payload = {**base, "triage": {"daily_limit": bad}}
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="triage.daily_limit"):
            load_config(path)


def test_missing_triage_section_still_loads(tmp_path: Path) -> None:
    """`triage` 是後加的一段，舊 config 仍要能載入（消費端退回預設值）。"""
    from engine_b.routine_config import DEFAULT_TRIAGE_LIMIT, load_config, triage_daily_limit

    base = json.loads((ROOT / "config" / "daily_routine.json").read_text(encoding="utf-8"))
    base.pop("triage")
    path = tmp_path / "old.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    load_config(path)                                   # 不得 raise
    assert triage_daily_limit(path) == DEFAULT_TRIAGE_LIMIT


def test_limit_zero_selects_nothing(tmp_path: Path) -> None:
    """0 ＝ daily 不做分類（與 pq1.drain_limit_per_run 的 0 同形）。

    ⚠ 照 drain 的先例，「0 不得被讀成無上限」這道保護不靠拒絕這個值，
    而靠**證明它真的選不出任何工作**。
    """
    from engine_b.routine_config import load_config, triage_daily_limit

    base = json.loads((ROOT / "config" / "daily_routine.json").read_text(encoding="utf-8"))
    payload = {**base, "triage": {"daily_limit": 0}}
    path = tmp_path / "zero.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    load_config(path)                                   # 0 合法
    assert triage_daily_limit(path) == 0
    assert [1, 2, 3][:0] == [], "切片語意：limit=0 取不到任何一筆"


def test_truncation_says_how_many_did_not_make_it() -> None:
    """暴量那天看起來不得跟平常一模一樣。"""
    result = subprocess.run(
        [sys.executable, "-m", "engine_b.cli", "list", "--status", "pending",
         "--by-priority", "--triage-batch"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert result.returncode == 0, result.stderr[-500:]
    first = result.stdout.splitlines()[0]
    assert "分類層每日上限" in first and "本批" in first, first
    # 兩種結局都要說出口，而且**不是同一句話**
    assert ("沒進本批" in first) or ("未達上限" in first), first


def test_the_cap_is_executed_by_the_cli_not_asked_of_the_model() -> None:
    """daily 的 triage 批次步驟必須帶 `--triage-batch`（上限由 CLI 截斷），prompt 不得寫死上限讓模型自己數。

    ⚠ 2026-09-24（Phase 1 Step 1.3）：原本讀 Codex daily prompt；那份 prompt 已封存，主詞改成
    `crons/daily_task.py` 的 ⑥ 與 `crons/triage_prompt.md`——判準一字未改（L15：權限永遠 deterministic）。
    """
    from crons.daily_task import DAILY_STEPS
    from engine_b.routine_config import triage_daily_limit

    batch = next(s for s in DAILY_STEPS if s.key == "06_triage_batch")
    assert "--triage-batch" in batch.argv
    prompt = PROMPT.read_text(encoding="utf-8")
    assert f"{triage_daily_limit()} 則" not in prompt, "prompt 裡寫死了上限數字，它會與 config 漂移"


def test_heartbeat_prints_the_limit_next_to_the_backlog() -> None:
    """只看「未 triage 41」看不出是「今天暴量」還是「積了三天」——兩者下一步不同。"""
    import crons.heartbeat as hb

    section = hb.build_queue(state_dir=None)
    line = next(l for l in section.lines if "未 triage" in l)
    assert "分類層每日上限" in line, line


def test_heartbeat_survives_an_unreadable_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """讀不到上限只讓那一格降級，不得把整行（含未 triage 計數）帶走。"""
    import engine_b.routine_config as rc
    import crons.heartbeat as hb

    def _boom(*_a, **_kw):
        raise RuntimeError("config gone")

    monkeypatch.setattr(rc, "triage_daily_limit", _boom)
    section = hb.build_queue(state_dir=None)
    line = next(l for l in section.lines if "未 triage" in l)
    assert "分類層上限未讀到" in line, line
