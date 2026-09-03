"""Shared high-confidence secret detection for persisted and rendered payloads。"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_SENSITIVE_KEY = re.compile(
    r"password|passwd|token|secret|credential|service.?account|dsn|private.?key"
    r"|api.?key|access.?key",
    re.IGNORECASE,
)
_SENSITIVE_VALUE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|\bAuthorization\s*:\s*Bearer\s+\S+"
    r"|\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?)://[^\s:/]+:[^\s/@]+@"
    r"|\b(?:password|passwd|token|secret|api[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]{8,}",
    re.IGNORECASE,
)


def sensitive_payload_path(value: Any, path: str = "root") -> str | None:
    """Return the first high-confidence secret location, otherwise ``None``。"""

    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _SENSITIVE_KEY.search(str(key)):
                return child_path
            found = sensitive_payload_path(child, child_path)
            if found is not None:
                return found
    elif isinstance(value, str):
        if _SENSITIVE_VALUE.search(value):
            return path
    elif isinstance(value, Sequence) and not isinstance(value, bytes):
        for index, child in enumerate(value):
            found = sensitive_payload_path(child, f"{path}[{index}]")
            if found is not None:
                return found
    return None
