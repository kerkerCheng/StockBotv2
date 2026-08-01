"""x_api.py — X (Twitter) API v2 唯讀 client，供 harvest 抓追蹤帳號的原創貼文。

**成本模型（2026-02 起 X 改 pay-per-use）：按「回傳貼文數」計費，約 $0.005/則、
無月費下限。** 因此本模組的設計以「少抓」為第一原則：

1. `since_id` 增量——只抓上次之後的新貼文（最大的成本槓桿）
2. `exclude=replies,retweets`——只要原創貼文（省錢且訊號更高）
3. `max_posts` 單輪硬上限＋`max_results` page size——分頁仍有成本天花板
4. `user_id` 快取——避免每次重複 user lookup

認證只需 Bearer Token（`X_BEARER_TOKEN`）；不需要 OAuth 1.0a 四把鑰匙。
Token 只從環境變數讀，絕不寫進 repo、log 或錯誤訊息。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.x.com/2"
_TIMEOUT = 20

# max_results 允許 5–100；預設 25 是成本天花板（正常增量遠低於此）
DEFAULT_MAX_RESULTS = 25
DEFAULT_MEDIA_MAX_BYTES = 20 * 1024 * 1024

_MEDIA_HOSTS = frozenset({"pbs.twimg.com"})
_MEDIA_SUFFIXES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_SAFE_MEDIA_STEM = re.compile(r"^[A-Za-z0-9_-]+$")


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
    """取某帳號的貼文（預設只要原創），含 long-post 全文與 media metadata。

    since_id 存在時只回更新的貼文——這是主要成本控制。
    """
    page = get_user_posts_page(
        user_id,
        since_id=since_id,
        max_results=max_results,
        exclude_replies=exclude_replies,
        exclude_retweets=exclude_retweets,
        token=token,
    )
    return page["posts"]


def get_user_posts_page(
    user_id: str,
    *,
    since_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    pagination_token: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    exclude_replies: bool = True,
    exclude_retweets: bool = True,
    token: str | None = None,
) -> dict[str, Any]:
    """取一頁 user timeline，保留 next_token 供 bounded backfill 使用。"""
    token = token or bearer_token()
    exclude = [
        name for name, on in (("replies", exclude_replies), ("retweets", exclude_retweets)) if on
    ]
    params: dict[str, Any] = {
        "max_results": max(5, min(100, int(max_results))),
        "tweet.fields": "created_at,public_metrics,note_tweet,attachments",
        "expansions": "attachments.media_keys",
        "media.fields": (
            "media_key,type,url,preview_image_url,alt_text,width,height,duration_ms"
        ),
    }
    if exclude:
        params["exclude"] = ",".join(exclude)
    if since_id:
        params["since_id"] = str(since_id)
    elif start_time:
        params["start_time"] = str(start_time)
    if end_time:
        params["end_time"] = str(end_time)
    if pagination_token:
        params["pagination_token"] = str(pagination_token)
    payload = _get(f"/users/{user_id}/tweets", params, token)
    next_token = ((payload.get("meta") or {}).get("next_token"))
    return {
        "posts": _hydrate_posts(payload),
        "next_token": str(next_token) if next_token else None,
    }


def get_user_posts_window(
    user_id: str,
    *,
    start_time: str,
    end_time: str | None = None,
    max_posts: int = 200,
    page_size: int = 100,
    exclude_replies: bool = True,
    exclude_retweets: bool = True,
    token: str | None = None,
    with_meta: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    """分頁取得 bounded 時間窗；max_posts 是 API 成本的硬上限。"""
    if not str(start_time or "").strip():
        raise XApiError("missing_start_time")
    cap = int(max_posts)
    if cap < 5:
        raise XApiError("max_posts_below_api_minimum")
    size = max(5, min(100, int(page_size)))
    token = token or bearer_token()
    output: list[dict[str, Any]] = []
    next_token: str | None = None
    while len(output) < cap:
        remaining = cap - len(output)
        if remaining < 5:
            break
        page = get_user_posts_page(
            user_id,
            start_time=start_time,
            end_time=end_time,
            pagination_token=next_token,
            max_results=min(size, remaining),
            exclude_replies=exclude_replies,
            exclude_retweets=exclude_retweets,
            token=token,
        )
        posts = list(page["posts"])
        output.extend(posts[:remaining])
        next_token = page.get("next_token")
        if not next_token or not posts:
            break
    result = {
        "posts": output,
        "truncated": bool(next_token),
        "next_token": next_token,
    }
    return result if with_meta else output


def get_user_posts_since(
    user_id: str,
    *,
    since_id: str,
    pagination_token: str | None = None,
    max_posts: int = 200,
    page_size: int = DEFAULT_MAX_RESULTS,
    exclude_replies: bool = True,
    exclude_retweets: bool = True,
    token: str | None = None,
    with_meta: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    """分頁取得 ``since_id`` 之後的貼文，並以 ``max_posts`` 鎖住單輪成本。

    ``pagination_token`` 讓 daily harvest 可以跨 scheduled runs 續抓同一個
    snapshot；只有最後一頁完成後，呼叫端才可推進 durable ``since_id``。
    """

    base = str(since_id or "").strip()
    if not base:
        raise XApiError("missing_since_id")
    cap = int(max_posts)
    if cap < 5:
        raise XApiError("max_posts_below_api_minimum")
    size = max(5, min(100, int(page_size)))
    token = token or bearer_token()
    output: list[dict[str, Any]] = []
    next_token = str(pagination_token).strip() if pagination_token else None
    while len(output) < cap:
        remaining = cap - len(output)
        if remaining < 5:
            break
        page = get_user_posts_page(
            user_id,
            since_id=base,
            pagination_token=next_token,
            max_results=min(size, remaining),
            exclude_replies=exclude_replies,
            exclude_retweets=exclude_retweets,
            token=token,
        )
        posts = list(page["posts"])
        output.extend(posts[:remaining])
        next_token = page.get("next_token")
        if not next_token or not posts:
            break
    result = {
        "posts": output,
        "truncated": bool(next_token),
        "next_token": next_token,
    }
    return result if with_meta else output


def get_posts_by_ids(
    post_ids: list[str],
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """精準重取既有貼文，供舊 lead 回填全文／圖片；最多 100 則。"""
    cleaned = [str(post_id).strip() for post_id in post_ids if str(post_id).strip()]
    if not cleaned:
        return []
    if len(cleaned) > 100 or any(not post_id.isdigit() for post_id in cleaned):
        raise XApiError("invalid_post_ids")
    token = token or bearer_token()
    payload = _get(
        "/tweets",
        {
            "ids": ",".join(cleaned),
            "tweet.fields": "created_at,public_metrics,note_tweet,attachments",
            "expansions": "attachments.media_keys",
            "media.fields": (
                "media_key,type,url,preview_image_url,alt_text,width,height,duration_ms"
            ),
        },
        token,
    )
    return _hydrate_posts(payload)


def _hydrate_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把 X includes.media 接回各貼文，並以 note_tweet.text 優先。"""
    media_by_key = {
        str(item.get("media_key")): item
        for item in ((payload.get("includes") or {}).get("media") or [])
        if item.get("media_key")
    }
    posts: list[dict[str, Any]] = []
    for row in payload.get("data") or []:
        if not row.get("id"):
            continue
        note_text = ((row.get("note_tweet") or {}).get("text"))
        media_keys = ((row.get("attachments") or {}).get("media_keys") or [])
        posts.append(
            {
                "id": str(row["id"]),
                "text": str(note_text if note_text is not None else row.get("text") or ""),
                "created_at": row.get("created_at"),
                "metrics": row.get("public_metrics") or {},
                "media": [
                    dict(media_by_key[str(media_key)])
                    for media_key in media_keys
                    if str(media_key) in media_by_key
                ],
            }
        )
    return posts


def _validate_media_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() not in _MEDIA_HOSTS:
        raise XApiError("untrusted_media_url")


def download_media_image(
    url: str,
    destination_dir: Path | str,
    stem: str,
    *,
    max_bytes: int = DEFAULT_MEDIA_MAX_BYTES,
) -> dict[str, Any]:
    """把 X 圖片／影片預覽存進指定 private 目錄，回可稽核 cache metadata。

    只接受 X 官方圖片 CDN、image Content-Type 與固定大小上限；失敗由 harvest
    fail-soft 處理，不會讓貼文本身消失。
    """
    if not _SAFE_MEDIA_STEM.fullmatch(stem):
        raise XApiError("invalid_media_key")
    _validate_media_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "StockBotv2-harvest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            _validate_media_url(resp.geturl())
            content_type = (resp.headers.get_content_type() or "").lower()
            if not content_type.startswith("image/"):
                raise XApiError("media_not_image")
            declared = resp.headers.get("Content-Length")
            if declared and int(declared) > int(max_bytes):
                raise XApiError("media_too_large")
            content = resp.read(int(max_bytes) + 1)
    except XApiError:
        raise
    except urllib.error.HTTPError as exc:
        raise XApiError(f"media_http_{exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise XApiError(f"media_transport_error:{type(exc).__name__}") from None
    if len(content) > int(max_bytes):
        raise XApiError("media_too_large")

    suffix = _MEDIA_SUFFIXES.get(content_type, ".img")
    directory = Path(destination_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{stem}{suffix}"
    handle = tempfile.NamedTemporaryFile(dir=directory, prefix=f".{stem}.", delete=False)
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    return {
        "path": str(destination),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "content_type": content_type,
    }


def post_url(username: str, post_id: str) -> str:
    return f"https://x.com/{username.lstrip('@')}/status/{post_id}"


def newest_id(posts: list[dict[str, Any]]) -> str | None:
    """X 的 id 是遞增字串；取數值最大者當下次 since_id。"""
    ids = [p["id"] for p in posts if str(p.get("id", "")).isdigit()]
    return max(ids, key=int) if ids else None
