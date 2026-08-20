from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import cast

import pytest

from storage.relational import (
    PrivateStorageError,
    _windows_owner,
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


def test_windows_owner_isolates_windows_powershell_module_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_root = r"C:\WINDOWS"
    polluted_module_path = (
        r"C:\codex-primary-runtime\dependencies\native\powershell\Modules;"
        r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\Modules"
    )
    monkeypatch.setenv("SystemRoot", system_root)
    monkeypatch.setenv("PSModulePath", polluted_module_path)
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="DESKTOP-A69ECLJ\\Cheng\n",
            stderr="",
        )

    monkeypatch.setattr("storage.relational.subprocess.run", fake_run)

    assert _windows_owner(tmp_path) == "DESKTOP-A69ECLJ\\Cheng"

    powershell_root = (
        Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0"
    )
    captured_args = cast(list[str], captured["args"])
    child_env = cast(dict[str, str], captured["env"])
    assert captured_args[0] == str(powershell_root / "powershell.exe")
    assert child_env["PSModulePath"] == str(powershell_root / "Modules")
    assert "codex-primary-runtime" not in child_env["PSModulePath"]


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


def test_nonexistent_child_does_not_skip_existing_reparse_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = tmp_path / "private"
    initialize_private_root(private_root, repo_root=repo)
    junction = private_root / "junction"
    junction.mkdir()
    monkeypatch.setattr(
        "storage.relational._is_reparse_point",
        lambda path: path == junction,
    )

    with pytest.raises(PrivateStorageError, match="reparse"):
        validate_private_destination(
            junction / "not-created" / "decision.db",
            private_root=private_root,
            repo_root=repo,
        )
