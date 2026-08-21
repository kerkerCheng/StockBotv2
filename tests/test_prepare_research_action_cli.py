"""Daily pq1 research-action staging CLI 的窄路徑契約。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_research_action import prepare_from_file


def test_prepare_only_accepts_ignored_action_draft_directory(tmp_path: Path) -> None:
    outside = tmp_path / "action.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="action_drafts"):
        prepare_from_file(outside, root=tmp_path, prepare=lambda *_a, **_k: {})


def test_prepare_delegates_to_server_validation_without_applying(
    tmp_path: Path,
) -> None:
    draft = tmp_path / "library" / "leads" / "action_drafts" / "lead.json"
    draft.parent.mkdir(parents=True)
    draft.write_text(json.dumps({"schema_version": "research-action/v1"}), encoding="utf-8")
    calls: list[tuple[dict, Path]] = []

    def fake_prepare(action_json: str, *, root: Path) -> dict:
        calls.append((json.loads(action_json), root))
        return {"status": "ready", "action_id": "ra_test"}

    result = prepare_from_file(draft, root=tmp_path, prepare=fake_prepare)

    assert result == {"status": "ready", "action_id": "ra_test"}
    assert calls == [({"schema_version": "research-action/v1"}, tmp_path)]
