"""互動補跑分類（scripts/triage_catchup.py）：與 daily ⑥⑦a⑦b 同一條路；沒持互動 writer lock 就不跑（⑦b 會寫 lead registry）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load():
    spec = importlib.util.spec_from_file_location("triage_catchup", ROOT / "scripts" / "triage_catchup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refuses_to_run_without_the_interactive_writer_lock(tmp_path, monkeypatch, capsys):
    from engine_b import writer_lock

    catchup = _load()
    monkeypatch.setattr(writer_lock, "holder", lambda *a, **k: None)
    assert catchup.main(["--out", str(tmp_path)]) == 2
    assert "writer lock" in capsys.readouterr().err
    monkeypatch.setattr(writer_lock, "holder", lambda *a, **k: {"owner": "scheduled", "expires_at": "2999-01-01T00:00:00+00:00"})
    assert catchup.main(["--out", str(tmp_path)]) == 2


def test_it_uses_the_same_llm_path_as_the_daily():
    """同一組零工具 argv、同一個 prompt 與 schema、同一個套用入口——不是另一套分類。"""
    source = (ROOT / "scripts" / "triage_catchup.py").read_text(encoding="utf-8")
    for token in ("llm_step.llm_argv", "llm_step.compose_triage_prompt", "llm_step.TRIAGE_SCHEMA",
                  "\"triage-apply\"", "\"--triage-batch\"", "claude-p:"):
        assert token in source, token
