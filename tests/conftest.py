"""Shared pytest fixtures for StockBotv2."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create an isolated Git repository with a deterministic identity."""

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=master"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "StockBotv2 Tests"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@stockbot.invalid"],
        cwd=repo,
        check=True,
    )
    return repo
