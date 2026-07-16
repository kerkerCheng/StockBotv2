"""Test-suite smoke coverage."""

from pathlib import Path


def test_pytest_and_tmp_git_repo_fixture(tmp_git_repo: Path) -> None:
    assert (tmp_git_repo / ".git").is_dir()
