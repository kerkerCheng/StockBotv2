"""層說明（layer note）——一個薄層或一個技術轉換一份的研究說明，同層每一頁共用（個股頁 plan S4a）。

`contracts.py` 是純邏輯（紀錄形狀、id、現行選取）；檔案 I/O、出處核對與 watch 登記在 `alpha/providers/layer_notes.py`。
"""
from .contracts import (
    CITATION_PREFIXES, EVIDENCE_LABELS, EVIDENCE_LEVELS, RECORD_VERSION, SECTION_KEYS, SECTION_LABELS, UNITS,
    Citation, Claim, LayerNote, Section, layer_note_record, new_note_id, parse_layer_note_record, select_current,
)

__all__ = [
    "CITATION_PREFIXES", "EVIDENCE_LABELS", "EVIDENCE_LEVELS", "RECORD_VERSION", "SECTION_KEYS", "SECTION_LABELS",
    "UNITS", "Citation", "Claim", "LayerNote", "Section", "layer_note_record", "new_note_id",
    "parse_layer_note_record", "select_current",
]
