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


def test_dry_run_flag_reaches_prepare_and_refuses_supersedes(tmp_path: Path, monkeypatch, capsys) -> None:
    """`--dry-run` 把 dry_run=True 交給 prepare、exit 0；和 `--supersedes` 一起用直接拒絕（乾跑不寫任何紀錄，取代不了誰）。"""
    import scripts.prepare_research_action as cli

    draft = tmp_path / "library" / "leads" / "action_drafts" / "lead.json"
    draft.parent.mkdir(parents=True)
    draft.write_text(json.dumps({"schema_version": "research-action/v1"}), encoding="utf-8")
    seen: list[dict] = []

    def fake_prepare(action_json: str, *, root: Path, dry_run: bool = False) -> dict:
        seen.append({"dry_run": dry_run})
        return {"status": "dry_run" if dry_run else "ready", "action_id": None if dry_run else "ra_x"}

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "prepare_from_file",
                        lambda path, dry_run=False: cli.__dict__["_orig_prepare_from_file"](
                            path, root=tmp_path, prepare=fake_prepare, dry_run=dry_run))
    monkeypatch.setitem(cli.__dict__, "_orig_prepare_from_file", prepare_from_file)
    assert cli.main(["--action-file", str(draft), "--dry-run"]) == 0
    assert seen == [{"dry_run": True}]
    assert '"status": "dry_run"' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["--action-file", str(draft), "--dry-run", "--supersedes", "ra_old"])
