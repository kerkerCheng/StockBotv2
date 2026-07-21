"""Google Sheet live authority 的薄唯讀 adapter。"""
from __future__ import annotations

from fetchers.gsheets import get_execution_aliases


def execution_aliases() -> dict[str, str]:
    return get_execution_aliases()
