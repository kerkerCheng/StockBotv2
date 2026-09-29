"""投資人短評（Investor Brief）：七格前因後果、文字由 session 寫、數字由 authority 填。見 `contracts.py`。"""
from __future__ import annotations

from .contracts import (
    BRIEF_FRAME, BRIEF_FRAME_V2, BRIEF_SLOTS, BRIEF_SLOTS_V2, FORBIDDEN_TERMS, PLACEHOLDERS, PLACEHOLDERS_V2,
    RECORD_VERSION, RECORD_VERSION_V1, RECORD_VERSION_V2, SLOT_KEYS, SLOT_KEYS_V2, SLOT_LABELS, SLOT_LABELS_V2,
    BriefSlot, InvestorBrief, brief_record, new_brief_id, parse_brief_record, placeholders_in, select_brief,
    slot_labels, validate_slot_text,
)
from .fill import ABSENT, fill_brief, format_value

__all__ = [
    "BRIEF_FRAME_V2", "BRIEF_SLOTS_V2", "PLACEHOLDERS_V2", "RECORD_VERSION_V1", "RECORD_VERSION_V2", "SLOT_KEYS_V2",
    "SLOT_LABELS_V2", "slot_labels",
    "ABSENT", "BRIEF_FRAME", "BRIEF_SLOTS", "FORBIDDEN_TERMS", "PLACEHOLDERS", "RECORD_VERSION", "SLOT_KEYS",
    "SLOT_LABELS", "BriefSlot", "InvestorBrief", "brief_record", "fill_brief", "format_value", "new_brief_id",
    "parse_brief_record", "placeholders_in", "select_brief", "validate_slot_text",
]
