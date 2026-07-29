"""網路／provider 失敗的 bounded 分類，供各引擎一致判斷是否必須重試。"""
from __future__ import annotations

from urllib.error import HTTPError


FAILURE_CLASSES: frozenset[str] = frozenset(
    {
        "access_blocked",
        "credentials_missing",
        "dependency_missing",
        "not_found",
        "parse_error",
        "provider_api_error",
        "timeout",
        "tls_failure",
        "transport_failure",
        "unknown",
    }
)


def classify_access_failure(
    exc: BaseException,
    *,
    default: str = "transport_failure",
) -> str:
    """把例外縮成不含 secret 的 failure class，避免 blocked 被當成無資料。"""

    if default not in FAILURE_CLASSES:
        raise ValueError(f"unknown default failure class: {default}")
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return "not_found"
        if exc.code in {401, 403, 407}:
            return "access_blocked"
        if 400 <= exc.code < 600:
            return "provider_api_error"
    message = str(exc).casefold()
    if any(token in message for token in ("certificate", "ssl", "tls")):
        return "tls_failure"
    if any(token in message for token in ("timed out", "timeout")):
        return "timeout"
    if any(
        token in message
        for token in (
            "403",
            "forbidden",
            "permission denied",
            "proxy",
            "sandbox",
            "temporary failure in name resolution",
        )
    ):
        return "access_blocked"
    if "404" in message or "not found" in message:
        return "not_found"
    return default


__all__ = ["FAILURE_CLASSES", "classify_access_failure"]
