"""Google Sheet live authority 的薄唯讀 adapter。"""
from __future__ import annotations

from identity.execution import get_execution_aliases


def execution_aliases() -> dict[str, str]:
    return get_execution_aliases()
