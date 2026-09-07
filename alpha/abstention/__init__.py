"""刻意不主張（Abstention）——「這一格沒有值，而那已經是答案」的 append-only authority。

`contracts.py` 是純邏輯；檔案 I/O 在 `alpha/providers/abstentions.py`。
消費端語意見 `alpha/absence.py` 的 `deliberate_abstention`。
"""
from .contracts import (
    ABSTENTION_LAYERS, ABSTENTION_SUBJECTS, RECORD_VERSION, Abstention, abstention_record,
    new_abstention_id, parse_abstention_record, select_abstention,
)

__all__ = [
    "ABSTENTION_LAYERS", "ABSTENTION_SUBJECTS", "RECORD_VERSION", "Abstention",
    "abstention_record", "new_abstention_id", "parse_abstention_record", "select_abstention",
]
