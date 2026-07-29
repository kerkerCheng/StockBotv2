from __future__ import annotations

from urllib.error import HTTPError

import pytest

from access_failures import classify_access_failure


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (PermissionError("sandbox network permission denied"), "access_blocked"),
        (TimeoutError("connection timed out"), "timeout"),
        (OSError("TLS certificate verify failed"), "tls_failure"),
        (OSError("connection reset"), "transport_failure"),
        (HTTPError("https://example.com", 403, "Forbidden", None, None), "access_blocked"),
        (HTTPError("https://example.com", 502, "Bad Gateway", None, None), "provider_api_error"),
    ],
)
def test_classify_access_failure(error, expected) -> None:
    assert classify_access_failure(error) == expected
