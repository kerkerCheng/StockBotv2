"""結構讀圖（Structure Reading）——「四條邊一起讀才讀得出來的東西」的 append-only 紀錄。

`contracts.py` 是純邏輯（紀錄與選取）、`staleness.py` 是分級（圖變了要不要重讀）；
檔案 I/O 在 `alpha/providers/structure_readings.py`；圖查詢在 `query/structure.py`。

**存輸入，不存結論**：紀錄的主體是當時那五條查詢回了什麼，判讀只是附帶——
因為只有結果集比對得出「多了一條我當初沒讀到的邊」。
"""
from .contracts import (
    ANGLE_KEYS, READING_KINDS, READING_UNITS, RECORD_VERSION, Citation, StructureReading,
    new_reading_id, parse_structure_reading_record, select_reading, select_readings, structure_reading_record,
)
from .staleness import (
    CHANGE_KINDS, DISPROOF_KINDS, READING_STATUSES, StructureChange,
    grade_changes, needs_reread, reading_status,
)

__all__ = [
    "ANGLE_KEYS", "CHANGE_KINDS", "Citation", "DISPROOF_KINDS", "READING_KINDS", "READING_STATUSES",
    "READING_UNITS", "RECORD_VERSION", "StructureChange", "StructureReading", "grade_changes", "needs_reread",
    "new_reading_id", "parse_structure_reading_record", "reading_status", "select_reading",
    "select_readings", "structure_reading_record",
]
