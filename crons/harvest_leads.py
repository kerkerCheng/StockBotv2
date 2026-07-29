"""harvest_leads.py — 每日 harvest：RSS feeds ＋ EDGAR watch filings → pending leads。

零 LLM token（純 HTTP＋解析）。X 保存全文、media metadata 與 private 圖片快取；
EDGAR 不下載 filing 全文。此步不 triage、不入圖（那些分別由 signal-triage、
使用者點名 research、Research Action 核准負責）。

誠實降級（plan R4）：每個 source 各記一筆 harvest_log（ok／fetch_failed／
parse_failed）；解析失敗 ≠ 無新文，brief 會據此提示 fallback。

用法:
    python crons/harvest_leads.py               # 用預設 config 與 leads store
    python crons/harvest_leads.py --dry-run     # 只印會註冊什麼，不寫檔
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from access_failures import classify_access_failure  # noqa: E402
from engine_b import leads  # noqa: E402

DEFAULT_CONFIG_PATH = ROOT / "crons" / "harvest_config.json"
DEFAULT_MEDIA_ROOT = ROOT / "library" / "private" / "lead_media"
_UA = "StockBotv2 daily-harvest (research; contact c3035281@gmail.com)"
_X_STATUS_URL = re.compile(r"^https://x\.com/([^/]+)/status/(\d+)$")


def load_local_env(path: Path | str = ROOT / ".env") -> None:
    """載入 repo-local secrets，讓無人值守 process 不依賴父 shell 注入。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(path), override=False)


load_local_env()


class HarvestParseError(Exception):
    """來源抓到了但內容無法解析（→ parse_failed，不是無新文）。"""


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    """讀 harvest config，缺必要欄位 fail closed（plan R3）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("harvest config 必須是 JSON object")
    feeds = data.get("feeds", [])
    watch = data.get("edgar_watch", {})
    if not isinstance(feeds, list) or not isinstance(watch, dict):
        raise ValueError("harvest config：feeds 必須是 list、edgar_watch 必須是 object")
    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("source") or not feed.get("url"):
            raise ValueError("每個 feed 必須有 source 與 url")
    if watch:
        if not isinstance(watch.get("tickers"), list) or not isinstance(
            watch.get("forms"), list
        ):
            raise ValueError("edgar_watch 必須有 tickers 與 forms list")
    x_section = data.get("x_accounts") or {}
    if x_section and not isinstance(x_section.get("handles"), list):
        raise ValueError("x_accounts 必須有 handles list")
    return data


def _localname(tag: str) -> str:
    """去掉 XML namespace，只留 local tag 名。"""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_rss(content: bytes, source: str) -> list[dict]:
    """解析 RSS 2.0 或 Atom，回傳 [{url, title, published_at}]。

    格式非法 raise HarvestParseError（呼叫端轉 parse_failed）。
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise HarvestParseError(f"{source}: XML 解析失敗：{exc}") from exc

    items: list[dict] = []
    for elem in root.iter():
        tag = _localname(elem.tag)
        if tag not in ("item", "entry"):
            continue
        url = ""
        title = ""
        published_at = None
        for child in elem:
            ctag = _localname(child.tag)
            if ctag == "title" and child.text:
                title = child.text.strip()
            elif ctag == "link":
                # RSS：link 的 text；Atom：link 的 href 屬性
                href = child.get("href")
                url = (href or child.text or "").strip()
            elif ctag in ("pubDate", "published", "updated") and child.text:
                published_at = published_at or child.text.strip()
        if url:
            items.append({"url": url, "title": title, "published_at": published_at})
    return items


def fetch_url(url: str, *, timeout: int = 20) -> bytes:
    """抓 URL 原始 bytes；網路層失敗 raise URLError（呼叫端轉 fetch_failed）。"""
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 (固定 https feed)
        return resp.read()


def filings_to_leads(ticker: str, cik: str, filings: list[dict]) -> list[dict]:
    """EDGAR filing metadata → lead dict list（純函式，只組 metadata）。"""
    out: list[dict] = []
    cik_int = str(int(cik))
    for f in filings:
        accession = f["accession"]
        primary = f.get("primary_doc") or ""
        base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}"
        url = f"{base}/{primary}" if primary else f"{base}/"
        out.append(
            {
                "source": f"edgar:{ticker.upper()}",
                "url": url,
                "title": f"{ticker.upper()} {f['form_type']} filed {f['filed_date']}",
                "published_at": f["filed_date"],
            }
        )
    return out


def _register_all(store: dict, source: str, items: list[dict], seen_at: str | None) -> int:
    new = 0
    for item in items:
        try:
            _lead_id, is_new = leads.register(
                store,
                source=source,
                url=item["url"],
                title=item.get("title", ""),
                raw_text=item.get("raw_text"),
                media=item.get("media"),
                published_at=item.get("published_at"),
                seen_at=seen_at,
            )
        except ValueError:
            continue  # 壞 URL 跳過，不讓單筆汙染整批
        if is_new:
            new += 1
    return new


def harvest_feeds(config: dict, store: dict, *, seen_at: str | None = None) -> None:
    for feed in config.get("feeds", []):
        source = feed["source"]
        try:
            content = fetch_url(feed["url"])
        except (URLError, OSError) as exc:
            leads.record_run(store, source=source, result="fetch_failed", new=0,
                             run_at=seen_at, failure_class=classify_access_failure(exc))
            print(f"[harvest] {source} fetch_failed: {exc}", file=sys.stderr)
            continue
        try:
            items = parse_rss(content, source)
        except HarvestParseError as exc:
            leads.record_run(store, source=source, result="parse_failed", new=0,
                             run_at=seen_at, failure_class="parse_error")
            print(f"[harvest] {source} parse_failed: {exc}", file=sys.stderr)
            continue
        new = _register_all(store, source, items, seen_at)
        leads.record_run(store, source=source, result="ok", new=new, run_at=seen_at)
        print(f"[harvest] {source} ok: {new} new / {len(items)} items")


def _cache_x_media(
    post_media: list[dict],
    *,
    lead_id: str,
    section: dict,
    x_api,
    existing_media: list[dict] | None = None,
) -> list[dict]:
    """保存 media metadata；啟用時把圖片／影片預覽 fail-soft 快取到 private。"""
    output: list[dict] = []
    cache_enabled = bool(section.get("cache_media", False))
    default_max = getattr(x_api, "DEFAULT_MEDIA_MAX_BYTES", 20 * 1024 * 1024)
    max_bytes = int(section.get("media_max_bytes", default_max))
    old_by_key = {
        str(item.get("media_key")): dict(item)
        for item in (existing_media or [])
        if item.get("media_key")
    }
    for raw in post_media:
        item = dict(old_by_key.get(str(raw.get("media_key"))) or {})
        item.update(raw)
        source_url = (
            item.get("url")
            if item.get("type") == "photo"
            else item.get("preview_image_url") or item.get("url")
        )
        cached_path = str((item.get("cache") or {}).get("local_path") or "")
        cache_exists = bool(cached_path and Path(cached_path).is_file())
        if (
            cache_enabled
            and source_url
            and item.get("media_key")
            and not cache_exists
        ):
            try:
                cache = x_api.download_media_image(
                    source_url,
                    DEFAULT_MEDIA_ROOT / lead_id,
                    str(item["media_key"]),
                    max_bytes=max_bytes,
                )
                cache_path = Path(cache.pop("path")).resolve()
                cache["local_path"] = cache_path.relative_to(ROOT.resolve()).as_posix()
                item["cache"] = cache
            except (x_api.XApiError, OSError, ValueError) as exc:
                print(
                    f"[harvest] x media cache_failed: {lead_id} "
                    f"{item.get('media_key')} {exc}",
                    file=sys.stderr,
                )
        output.append(item)
    return output


def _x_post_item(
    handle: str,
    post: dict,
    section: dict,
    x_api,
    *,
    existing_media: list[dict] | None = None,
) -> dict:
    url = x_api.post_url(handle, post["id"])
    raw_text = str(post.get("text") or "")
    lead_id = leads.lead_id_for(url)
    return {
        "url": url,
        # title 是可搜尋／可排序的單行全文，不再做 140 字截斷。
        "title": " ".join(raw_text.split()),
        # raw_text 保存 X 回傳的逐字內容與換行，供後續 atomic claim 拆解。
        "raw_text": raw_text,
        "media": _cache_x_media(
            list(post.get("media") or []),
            lead_id=lead_id,
            section=section,
            x_api=x_api,
            existing_media=existing_media,
        ),
        "published_at": post.get("created_at"),
    }


def harvest_x(config: dict, store: dict, *, seen_at: str | None = None) -> None:
    """抓追蹤 X 帳號的原創貼文（pay-per-use：只抓 since_id 之後的新貼文）。

    每個帳號一筆 harvest_log；缺 token／API 失敗都記 fetch_failed 不拋例外
    （與其他來源一致：解析／抓取失敗 ≠ 無新文）。
    """
    section = config.get("x_accounts") or {}
    handles = section.get("handles") or []
    if not handles:
        return
    try:
        from fetchers import x_api
    except ImportError as exc:
        for handle in handles:
            leads.record_run(store, source=f"x:{handle}", result="fetch_failed",
                             new=0, run_at=seen_at, failure_class="dependency_missing")
        print(f"[harvest] x api unavailable: {exc}", file=sys.stderr)
        return

    try:
        token = x_api.bearer_token()
    except x_api.XApiError as exc:
        for handle in handles:
            leads.record_run(store, source=f"x:{handle}", result="fetch_failed",
                             new=0, run_at=seen_at, failure_class="credentials_missing")
        print(f"[harvest] x api: {exc}（請在 .env 設 X_BEARER_TOKEN）", file=sys.stderr)
        return

    for handle in handles:
        source = f"x:{handle}"
        state = leads.get_source_state(store, source)
        try:
            user_id = state.get("user_id") or x_api.get_user_id(handle, token)
            posts = x_api.get_user_posts(
                user_id,
                since_id=state.get("since_id"),
                max_results=int(section.get("max_results", x_api.DEFAULT_MAX_RESULTS)),
                exclude_replies=bool(section.get("exclude_replies", True)),
                exclude_retweets=bool(section.get("exclude_retweets", True)),
                token=token,
            )
        except x_api.XApiError as exc:
            leads.record_run(store, source=source, result="fetch_failed", new=0,
                             run_at=seen_at,
                             failure_class=classify_access_failure(
                                 exc, default="provider_api_error"
                             ))
            print(f"[harvest] {source} fetch_failed: {exc}", file=sys.stderr)
            continue

        items = [_x_post_item(handle, post, section, x_api) for post in posts]
        new = _register_all(store, source, items, seen_at)
        leads.set_source_state(
            store, source,
            user_id=user_id,
            since_id=x_api.newest_id(posts) or state.get("since_id"),
        )
        leads.record_run(store, source=source, result="ok", new=new, run_at=seen_at)
        cost = len(posts) * 0.005
        print(f"[harvest] {source} ok: {new} new / {len(posts)} posts (~${cost:.3f})")


def backfill_x_handle(
    config: dict,
    store: dict,
    handle: str,
    *,
    days: int = 30,
    max_posts: int = 200,
    campaign_id: str | None = None,
    requeue_no_go: bool = False,
    include_replies: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> dict:
    """回補具名 X account 的 bounded 時間窗，不推進 daily since_id。"""
    section = config.get("x_accounts") or {}
    configured = {
        str(item).lstrip("@").lower() for item in (section.get("handles") or [])
    }
    cleaned_handle = str(handle or "").lstrip("@").strip()
    if cleaned_handle.lower() not in configured:
        raise ValueError(f"X handle 未列於 harvest config：{cleaned_handle}")
    if not 1 <= int(days) <= 90:
        raise ValueError("X backfill days 必須介於 1–90")
    if not 5 <= int(max_posts) <= 1000:
        raise ValueError("X backfill max_posts 必須介於 5–1000")

    from fetchers import x_api

    token = x_api.bearer_token()
    source = f"x:{cleaned_handle}"
    state = leads.get_source_state(store, source)
    user_id = state.get("user_id") or x_api.get_user_id(cleaned_handle, token)
    end = end_at or (datetime.now(timezone.utc) - timedelta(seconds=15))
    if end.tzinfo is None:
        raise ValueError("X backfill end_at 必須含 timezone")
    end = end.astimezone(timezone.utc)
    if start_at is not None and start_at.tzinfo is None:
        raise ValueError("X backfill start_at 必須含 timezone")
    start = (
        start_at.astimezone(timezone.utc)
        if start_at is not None
        else end - timedelta(days=int(days))
    )
    if start >= end:
        raise ValueError("X backfill start_at 必須早於 end_at")
    # X timeline 只接受 YYYY-MM-DDTHH:mm:ssZ；不得帶 microseconds。
    start_time = start.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_time = end.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    resolved_campaign = (
        str(campaign_id or "").strip()
        or f"x_{cleaned_handle}_{start:%Y%m%d}_{end:%Y%m%d}"
    )
    window = x_api.get_user_posts_window(
        user_id,
        start_time=start_time,
        end_time=end_time,
        max_posts=int(max_posts),
        page_size=int(section.get("backfill_page_size", 100)),
        exclude_replies=(
            False if include_replies else bool(section.get("exclude_replies", True))
        ),
        exclude_retweets=bool(section.get("exclude_retweets", True)),
        token=token,
        with_meta=True,
    )
    posts = list(window["posts"])

    new = 0
    requeued = 0
    for post in posts:
        url = x_api.post_url(cleaned_handle, post["id"])
        lead_id = leads.lead_id_for(url)
        existing = store.get("leads", {}).get(lead_id) or {}
        item = _x_post_item(
            cleaned_handle,
            post,
            section,
            x_api,
            existing_media=list(existing.get("media") or []),
        )
        registered_id, is_new = leads.register(
            store,
            source=source,
            url=item["url"],
            title=item["title"],
            raw_text=item["raw_text"],
            media=item["media"],
            published_at=item["published_at"],
        )
        new += int(is_new)
        leads.tag_campaign(store, registered_id, campaign_id=resolved_campaign)
        leads.annotate_refs(
            store,
            registered_id,
            refs={
                "campaign_window_start": start_time,
                "campaign_window_end": end_time,
            },
        )
        lead = store["leads"][registered_id]
        if requeue_no_go and lead["status"] == "triaged_no_go":
            leads.requeue_for_triage(
                store,
                registered_id,
                reason="使用者明確要求以新領域探索 campaign 重新 triage",
                campaign_id=resolved_campaign,
            )
            requeued += 1

    # 只補 user_id；歷史回補不得推進 daily since_id。
    leads.set_source_state(store, source, user_id=user_id)
    leads.record_run(store, source=source, result="ok", new=new)
    return {
        "campaign_id": resolved_campaign,
        "handle": cleaned_handle,
        "start_time": start_time,
        "end_time": end_time,
        "posts": len(posts),
        "new": new,
        "existing": len(posts) - new,
        "requeued_no_go": requeued,
        "include_replies": bool(include_replies),
        "estimated_post_read_cost_usd": round(len(posts) * 0.005, 3),
        "max_posts": int(max_posts),
        "truncated": bool(window.get("truncated")),
    }


def refresh_x_lead(config: dict, store: dict, lead_id: str) -> dict:
    """精準重抓一筆既有 X lead，補全文／media，不推進 since_id 或改狀態。"""
    lead = store.get("leads", {}).get(lead_id)
    if lead is None:
        raise ValueError(f"未知 lead：{lead_id}")
    match = _X_STATUS_URL.fullmatch(str(lead.get("url") or ""))
    if not match or not str(lead.get("source") or "").startswith("x:"):
        raise ValueError(f"不是可 refresh 的 X lead：{lead_id}")
    handle, post_id = match.groups()
    section = config.get("x_accounts") or {}

    from fetchers import x_api

    posts = x_api.get_posts_by_ids([post_id])
    if not posts:
        raise x_api.XApiError("post_not_found")
    item = _x_post_item(handle, posts[0], section, x_api)
    refreshed_id, _is_new = leads.register(
        store,
        source=lead["source"],
        url=item["url"],
        title=item["title"],
        raw_text=item["raw_text"],
        media=item["media"],
        published_at=item["published_at"],
    )
    if refreshed_id != lead_id:
        raise ValueError("refresh 後 lead identity 不一致")
    return store["leads"][lead_id]


def harvest_edgar(config: dict, store: dict, *, seen_at: str | None = None) -> None:
    watch = config.get("edgar_watch") or {}
    tickers = watch.get("tickers") or []
    forms = watch.get("forms") or []
    count = int(watch.get("lookback_count", 8))
    if not tickers:
        return
    try:
        from fetchers.edgar import get_cik, get_filings
    except ImportError as exc:
        for ticker in tickers:
            leads.record_run(store, source=f"edgar:{ticker.upper()}",
                             result="fetch_failed", new=0, run_at=seen_at,
                             failure_class="dependency_missing")
        print(f"[harvest] edgar unavailable: {exc}", file=sys.stderr)
        return
    for ticker in tickers:
        source = f"edgar:{ticker.upper()}"
        try:
            cik = get_cik(ticker)
            if not cik:
                raise RuntimeError(f"找不到 CIK：{ticker}")
            filings = get_filings(cik, forms, count)
        except Exception as exc:  # noqa: BLE001 網路／解析都算 fetch_failed
            leads.record_run(store, source=source, result="fetch_failed", new=0,
                             run_at=seen_at, failure_class=classify_access_failure(exc))
            print(f"[harvest] {source} fetch_failed: {exc}", file=sys.stderr)
            continue
        items = filings_to_leads(ticker, cik, filings)
        new = _register_all(store, source, items, seen_at)
        leads.record_run(store, source=source, result="ok", new=new, run_at=seen_at)
        print(f"[harvest] {source} ok: {new} new / {len(items)} filings")


def run(config: dict, store: dict, *, seen_at: str | None = None) -> dict:
    harvest_feeds(config, store, seen_at=seen_at)
    harvest_x(config, store, seen_at=seen_at)
    harvest_edgar(config, store, seen_at=seen_at)
    return store


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily harvest：RSS ＋ EDGAR watch → pending leads")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH))
    ap.add_argument("--dry-run", action="store_true", help="只印，不寫檔")
    ap.add_argument(
        "--refresh-x-lead",
        metavar="LEAD_ID",
        help="只重抓指定既有 X lead，補全文與圖片，不跑一般 harvest",
    )
    ap.add_argument(
        "--backfill-x-handle",
        metavar="HANDLE",
        help="分頁回補具名 X 帳號的 bounded 時間窗，不推進 daily since_id",
    )
    ap.add_argument("--days", type=int, default=30, help="X backfill 天數（1–90）")
    ap.add_argument(
        "--max-posts",
        type=int,
        default=200,
        help="X backfill 最多讀取貼文數＝成本硬上限（5–1000）",
    )
    ap.add_argument("--campaign-id", help="X backfill 研究 campaign ID")
    ap.add_argument("--start-at", help="覆寫 backfill 起點（RFC3339 UTC）")
    ap.add_argument("--end-at", help="覆寫 backfill 終點（RFC3339 UTC）")
    ap.add_argument(
        "--requeue-no-go",
        action="store_true",
        help="保留舊 triage receipt 後，把時間窗內 triaged_no_go 重新排入 triage",
    )
    ap.add_argument(
        "--include-replies",
        action="store_true",
        help="X backfill 納入 replies／thread continuations；仍排除 retweets",
    )
    args = ap.parse_args()

    config = load_config(args.config)
    store = leads.load(args.leads)
    if args.refresh_x_lead:
        if args.dry_run:
            config.setdefault("x_accounts", {})["cache_media"] = False
        try:
            refreshed = refresh_x_lead(config, store, args.refresh_x_lead)
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"[harvest] X lead refresh_failed: {exc}", file=sys.stderr)
            return 1
        if not args.dry_run:
            leads.save(store, args.leads)
        print(
            f"[harvest] X lead refreshed: {args.refresh_x_lead} "
            f"text={len(refreshed.get('raw_text') or '')} chars "
            f"media={len(refreshed.get('media') or [])}"
        )
        return 0

    if args.backfill_x_handle:
        if args.dry_run:
            config.setdefault("x_accounts", {})["cache_media"] = False
            print(
                "[harvest] 注意：X backfill --dry-run 仍會消耗 Post reads；"
                "僅不寫 leads／media。",
                file=sys.stderr,
            )
        try:
            start_at = (
                datetime.fromisoformat(args.start_at.replace("Z", "+00:00"))
                if args.start_at
                else None
            )
            end_at = (
                datetime.fromisoformat(args.end_at.replace("Z", "+00:00"))
                if args.end_at
                else None
            )
            receipt = backfill_x_handle(
                config,
                store,
                args.backfill_x_handle,
                days=args.days,
                max_posts=args.max_posts,
                campaign_id=args.campaign_id,
                requeue_no_go=args.requeue_no_go,
                include_replies=args.include_replies,
                start_at=start_at,
                end_at=end_at,
            )
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"[harvest] X backfill_failed: {exc}", file=sys.stderr)
            return 1
        if not args.dry_run:
            leads.save(store, args.leads)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0

    before = len(store["leads"])
    run(config, store)
    added = len(store["leads"]) - before

    if args.dry_run:
        print(f"[harvest] dry-run：會新增 {added} 筆 lead（未寫檔）")
        return 0
    leads.save(store, args.leads)
    print(f"[harvest] 完成：新增 {added} 筆 lead，總計 {len(store['leads'])} 筆")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
