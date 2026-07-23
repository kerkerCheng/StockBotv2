"""pending_leads_digest SessionStart hook：安靜原則＋雙通道輸出。"""
from __future__ import annotations

import json

from crons import pending_leads_digest as digest


def test_silent_when_no_pending(monkeypatch, capsys) -> None:
    monkeypatch.setattr(digest, "_counts", lambda: {"applied": 3})
    assert digest.main() == 0
    assert capsys.readouterr().out == ""


def test_dual_channel_output_when_pending(monkeypatch, capsys) -> None:
    monkeypatch.setattr(digest, "_counts", lambda: {"pending": 5, "triaged_go": 2})
    assert digest.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    # systemMessage 給終端；additionalContext 進 context 讓手機／雲端也能轉述。
    assert "5 條待判斷" in payload["systemMessage"]
    assert "2 條 triaged_go" in payload["systemMessage"]
    assert "轉述" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_counts_failure_is_silent(monkeypatch, capsys) -> None:
    def boom():
        raise RuntimeError("no file")

    # _counts 內部已吞例外回 {}；此處確認 main 不因缺檔而噴錯。
    monkeypatch.setattr(digest, "_counts", lambda: {})
    assert digest.main() == 0
    assert capsys.readouterr().out == ""
