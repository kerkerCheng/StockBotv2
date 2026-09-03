"""研究模型。**不接 LLM API——LLM 就是 session 本身。**

`session_assessor` 提供 packet builder ＋ judgment 驗證；
判斷由 Claude Code／Codex session 產生，程式只負責解析與權限（L15）。
"""
from __future__ import annotations

from .session_assessor import (
    AXIS_PROMPTS, JUDGMENT_SCHEMA, SESSION_AXES, JudgmentPacket, build_packet,
    compose_signal,
)

__all__ = [
    "AXIS_PROMPTS", "JUDGMENT_SCHEMA", "SESSION_AXES", "JudgmentPacket",
    "build_packet", "compose_signal",
]
