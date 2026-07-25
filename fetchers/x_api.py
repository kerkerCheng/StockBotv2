"""x_api.py — X (Twitter) API v2 唯讀 client，供 harvest 抓追蹤帳號的原創貼文。

**成本模型（2026-02 起 X 改 pay-per-use）：按「回傳貼文數」計費，約 $0.005/則、
無月費下限。** 因此本模組的設計以「少抓」為第一原則：

1. `since_id` 增量——只抓上次之後的新貼文（最大的成本槓桿）
2. `exclude=replies,retweets`——只要原創貼文（省錢且訊號更高）
3. `max_results` 上限——即使 since_id 失效也有成本天花板
4. `user_id` 快取——避免每次重複 user lookup

認證只需 Bearer Token（`X_BEARER_TOKEN`）；不需要 OAuth 1.0a 四把鑰匙。
Token 只從環境變數讀，絕不寫進 repo、log 或錯誤訊息。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.x.com/2"
_TIMEOUT = 20

# max_results 允許 5–100；預設 25 是成本天花板（正常增量遠低於此）
DEFAULT_MAX_RESULTS = 25


class XApiError(RuntimeError):
    """X API 呼叫失敗；訊息只含穩定 code，絕不含 token。"""


def bearer_token() -> str:
    token = (os.environ.get("X_BEARER_TOKEN") or "").strip()
    if not token:
        raise XApiError("missing_x_bearer_token")
    return token


def _get(path: str, params: dict[str, Any], token: str) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "StockBotv2-harvest/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 只回穩定 code，不回 body（可能含帳號資訊）也不回 token
        raise XApiError(f"http_{exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise XApiError(f"transport_error:{type(exc).__name__}") from None


def get_user_id(username: str, token: str | None = None) -> str:
    """username → numeric user id。呼叫端應快取結果以免重複計費。"""
    token = token or bearer_token()
    handle = username.lstrip("@").strip()
    if not handle:
        raise XApiError("empty_username")
    payload = _get(f"/users/by/username/{handle}", {}, token)
    user_id = ((payload or {}).get("data") or {}).get("id")
    if not user_id:
        raise XApiError("user_not_found")
    return str(user_id)


def get_user_posts(
    user_id: str,
    *,
    since_id: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    exclude_replies: bool = True,
    exclude_retweets: bool = True,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """取某帳號的貼文（預設只要原創）。回 [{id, text, created_at}]，新到舊。

    since_id 存在時只回更新的貼文——這是主要成本控制。
    """
    token = token or bearer_token()
    exclude = [
        name for name, on in (("replies", exclude_replies), ("retweets", exclude_retweets)) if on
    ]
    params: dict[str, Any] = {
        "max_results": max(5, min(100, int(max_results))),
        "tweet.fields": "created_at,public_metrics",
    }
    if exclude:
        params["exclude"] = ",".join(exclude)
    if since_id:
        params["since_id"] = str(since_id)
    payload = _get(f"/users/{user_id}/tweets", params, token)
    data = payload.get("data") or []
    return [
        {
            "id": str(row.get("id")),
            "text": str(row.get("text") or ""),
            "created_at": row.get("created_at"),
            "metrics": row.get("public_metrics") or {},
        }
        for row in data
        if row.get("id")
    ]


def post_url(username: str, post_id: str) -> str:
    return f"https://x.com/{username.lstrip('@')}/status/{post_id}"


def newest_id(posts: list[dict[str, Any]]) -> str | None:
    """X 的 id 是遞增字串；取數值最大者當下次 since_id。"""
    ids = [p["id"] for p in posts if str(p.get("id", "")).isdigit()]
    return max(ids, key=int) if ids else None
