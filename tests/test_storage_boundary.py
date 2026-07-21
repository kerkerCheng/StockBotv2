from __future__ import annotations

import os
from pathlib import Path

import pytest

from storage.relational import (
    PrivateStorageError,
    initialize_private_root,
    validate_private_destination,
    verify_owner_only,
)


def test_private_root_is_created_owner_only_and_accepts_ignored_enclave(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"

    initialize_private_root(private_root, repo_root=repo)

    assert private_root.is_dir()
    assert verify_owner_only(private_root)
    validate_private_destination(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )


@pytest.mark.parametrize("relative", ["decision.db", "config/decision.db"])
def test_repo_public_destination_fails_closed(tmp_path: Path, relative: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = tmp_path / "private"
    initialize_private_root(private_root, repo_root=repo)

    with pytest.raises(PrivateStorageError, match="repository"):
        validate_private_destination(
            repo / relative,
            private_root=private_root,
            repo_root=repo,
        )


def test_public_and_reparse_destinations_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    public = tmp_path / "public"
    public.mkdir()
    private_root = tmp_path / "private"
    initialize_private_root(private_root, repo_root=repo)

    with pytest.raises(PrivateStorageError, match="public"):
        validate_private_destination(
            public / "decision.db",
            private_root=private_root,
            repo_root=repo,
            public_roots=(public,),
        )

    monkeypatch.setattr("storage.relational._is_reparse_point", lambda _path: True)
    with pytest.raises(PrivateStorageError, match="reparse"):
        validate_private_destination(
            private_root / "decision.db",
            private_root=private_root,
            repo_root=repo,
        )

def test_non_owner_only_existing_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = tmp_path / "private"
    private_root.mkdir()
    monkeypatch.setattr("storage.relational.verify_owner_only", lambda _path: False)

    with pytest.raises(PrivateStorageError, match="owner-only"):
        validate_private_destination(
            private_root / "decision.db",
            private_root=private_root,
            repo_root=repo,
        )
