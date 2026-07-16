"""Session-start safety net for unfinished intake git work."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crons.weekly_scan_digest import intake_pending_summary


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)


def _ready(tmp_git_repo: Path, tmp_path: Path) -> Path:
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit(tmp_git_repo, "baseline")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    _git(tmp_git_repo, "remote", "add", "origin", str(remote))
    _git(tmp_git_repo, "push", "-u", "origin", "master")
    return remote


def test_digest_counts_only_pending_ledger_files(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "extractions").mkdir()
    tracked = tmp_git_repo / "extractions" / "tracked.json"
    tracked.write_text("{}", encoding="utf-8")
    (tmp_git_repo / "outside.txt").write_text("outside", encoding="utf-8")
    _commit(tmp_git_repo, "baseline")
    tracked.write_text('{"changed":true}', encoding="utf-8")
    (tmp_git_repo / "library" / "raw").mkdir(parents=True)
    (tmp_git_repo / "library" / "raw" / "new.txt").write_text("new", encoding="utf-8")
    (tmp_git_repo / "other.txt").write_text("ignore", encoding="utf-8")

    summary = intake_pending_summary(tmp_git_repo)

    assert summary["modified"] == ["extractions/tracked.json"]
    assert summary["untracked"] == ["library/raw/new.txt"]
    assert summary["total"] == 2


def test_digest_is_quiet_after_push_and_counts_unpushed_intake_commit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready(tmp_git_repo, tmp_path)
    assert intake_pending_summary(tmp_git_repo)["total"] == 0

    (tmp_git_repo / "extractions").mkdir()
    (tmp_git_repo / "extractions" / "new.json").write_text("{}", encoding="utf-8")
    _commit(tmp_git_repo, "local intake")

    summary = intake_pending_summary(tmp_git_repo)
    assert summary["untracked"] == []
    assert summary["modified"] == []
    assert summary["unpushed_commits"] == 1
    assert summary["total"] == 1
