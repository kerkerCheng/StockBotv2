"""投資人短評（Investor Brief）：七格前因後果、文字由 session 寫、數字由 authority 填。見 `contracts.py`。"""
from __future__ import annotations

from .contracts import (
    BRIEF_FRAME, BRIEF_SLOTS, FORBIDDEN_TERMS, PLACEHOLDERS, RECORD_VERSION, SLOT_KEYS, SLOT_LABELS, BriefSlot,
    InvestorBrief, brief_record, new_brief_id, parse_brief_record, placeholders_in, select_brief,
    validate_slot_text,
)
from .fill import ABSENT, fill_brief, format_value

__all__ = [
    "ABSENT", "BRIEF_FRAME", "BRIEF_SLOTS", "FORBIDDEN_TERMS", "PLACEHOLDERS", "RECORD_VERSION", "SLOT_KEYS",
    "SLOT_LABELS", "BriefSlot", "InvestorBrief", "brief_record", "fill_brief", "format_value", "new_brief_id",
    "parse_brief_record", "placeholders_in", "select_brief", "validate_slot_text",
]
