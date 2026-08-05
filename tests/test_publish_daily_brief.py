from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_daily_brief.py"
SPEC = importlib.util.spec_from_file_location("publish_daily_brief_cli", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


def test_brief_file_is_read_as_utf8_before_publishing(tmp_path: Path, monkeypatch, capsys) -> None:
    brief = "# Daily Brief 2026-08-05 (Asia/Taipei)\n\n需要你動作：檢查台積電供應鏈。"
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(brief, encoding="utf-8")
    captured: dict[str, str] = {}

    def fake_publish(brief_text: str, *, summary: str, **kwargs):
        captured["brief_text"] = brief_text
        captured["summary"] = summary
        return SimpleNamespace(as_dict=lambda: {"status": "sent"})

    monkeypatch.setattr(CLI, "load_dotenv", None)
    monkeypatch.setattr(CLI, "publish_daily_brief", fake_publish)

    assert CLI.run([
        "--brief-file",
        str(brief_file),
        "--summary",
        "今日有一個待處理項目",
    ]) == 0
    capsys.readouterr()

    assert captured == {
        "brief_text": brief,
        "summary": "今日有一個待處理項目",
    }
