"""thesis_freshness_check 讀 lifecycle.json 到期（plan U5/R17）。"""
from __future__ import annotations

import json
from pathlib import Path

from crons import thesis_freshness_check as hook


def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "lifecycle.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_review_required_and_overdue_are_flagged(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", _write(tmp_path, {
        "sivers": {"status": "review_required", "next_check": "2099-01-01"},
        "coherent_cpo": {"status": "active", "next_check": "2000-01-01"},  # 早已到期
        "fresh": {"status": "active", "next_check": "2099-12-31"},          # 未到期
    }))
    due = dict(hook.lifecycle_due())
    assert "sivers" in due and "review_required" in due["sivers"]
    assert "coherent_cpo" in due  # next_check 過了
    assert "fresh" not in due


def test_missing_or_malformed_lifecycle_is_silent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", tmp_path / "nope.json")
    assert hook.lifecycle_due() == []
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(hook, "LIFECYCLE", bad)
    assert hook.lifecycle_due() == []
