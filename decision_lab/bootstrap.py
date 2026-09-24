"""舊 Decision Store 的唯讀入口（frozen 2026-09-22，G12）。

Phase 1 Step 1.1：原本的 `open_default_store()` 回可寫 handle（新庫會建表、會寫 authority marker、
連線是 `mode=rwc`），凍結後已無任何合法的寫入呼叫端，所以整支換成連線層強制唯讀——
「讀取端不會寫」從靠用法變成靠連線（L15）。要建新庫的只剩測試，直接用 `DecisionStore.open`。
"""
from __future__ import annotations

from pathlib import Path

from .store import DecisionStore, DecisionStoreAbsent

__all__ = ["DecisionStoreAbsent", "default_store_path", "open_readonly_store"]


def default_store_path(repo_root: Path | None = None) -> Path:
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    return root / "library" / "private" / "decision_lab" / "decision_lab.db"


def open_readonly_store(repo_root: Path | None = None) -> DecisionStore:
    """`mode=ro` 開舊店；DB 不存在 → `DecisionStoreAbsent`（明確缺席，不建空庫）。"""
    return DecisionStore.open_readonly(default_store_path(repo_root))
