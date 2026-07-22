"""harvest_leads.py — 每日 harvest：RSS feeds ＋ EDGAR watch filings → pending leads。

零 LLM token（純 HTTP＋解析）。只註冊 metadata，不下載 filing 全文、不 triage、
不入圖（那些分別由 signal-triage、使用者點名 research、Research Action 核准負責）。

誠實降級（plan R4）：每個 source 各記一筆 harvest_log（ok／fetch_failed／
parse_failed）；解析失敗 ≠ 無新文，brief 會據此提示 fallback。

用法:
    python crons/harvest_leads.py               # 用預設 config 與 leads store
    python crons/harvest_leads.py --dry-run     # 只印會註冊什麼，不寫檔
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine_b import leads  # noqa: E402

DEFAULT_CONFIG_PATH = ROOT / "crons" / "harvest_config.json"
_UA = "StockBotv2 daily-harvest (research; contact c3035281@gmail.com)"


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
                             run_at=seen_at)
            print(f"[harvest] {source} fetch_failed: {exc}", file=sys.stderr)
            continue
        try:
            items = parse_rss(content, source)
        except HarvestParseError as exc:
            leads.record_run(store, source=source, result="parse_failed", new=0,
                             run_at=seen_at)
            print(f"[harvest] {source} parse_failed: {exc}", file=sys.stderr)
            continue
        new = _register_all(store, source, items, seen_at)
        leads.record_run(store, source=source, result="ok", new=new, run_at=seen_at)
        print(f"[harvest] {source} ok: {new} new / {len(items)} items")


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
                             result="fetch_failed", new=0, run_at=seen_at)
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
                             run_at=seen_at)
            print(f"[harvest] {source} fetch_failed: {exc}", file=sys.stderr)
            continue
        items = filings_to_leads(ticker, cik, filings)
        new = _register_all(store, source, items, seen_at)
        leads.record_run(store, source=source, result="ok", new=new, run_at=seen_at)
        print(f"[harvest] {source} ok: {new} new / {len(items)} filings")


def run(config: dict, store: dict, *, seen_at: str | None = None) -> dict:
    harvest_feeds(config, store, seen_at=seen_at)
    harvest_edgar(config, store, seen_at=seen_at)
    return store


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily harvest：RSS ＋ EDGAR watch → pending leads")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH))
    ap.add_argument("--dry-run", action="store_true", help="只印，不寫檔")
    args = ap.parse_args()

    config = load_config(args.config)
    store = leads.load(args.leads)
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
