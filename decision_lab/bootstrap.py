"""建立本機 private Decision Store。"""
from __future__ import annotations

from pathlib import Path

from storage.relational import initialize_private_root

from .store import DecisionStore


def open_default_store(repo_root: Path | None = None) -> DecisionStore:
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    private_root = initialize_private_root(
        root / "library" / "private",
        repo_root=root,
    )
    return DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=root,
    )
