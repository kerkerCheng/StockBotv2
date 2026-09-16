"""
rns.py — 從 investegate 鏡像抓倫敦證交所 RNS（Regulatory News Service）公告全文。

RNS 是 LSE 的法定訊息揭露服務；investegate.co.uk 逐字鏡像每則公告（含 RNS 生成的 dateline），
先前 IQE 追源四次都是在這裡拿到原文。iqep.com 的 SSL 鏈與 investis 的 RSS 都壞過
（`crons/harvest_config.json` 的 rejected_candidates），所以這條路不走公司站。

輸出格式（與 mops.py／mfn.py 一致）：
    library/raw/{doc_id}.txt       — 公告全文（news-window 內的 RNS 本體，HTML 轉純文字）
    library/raw/{doc_id}.meta.json — doc metadata（含 published_at 與其依據）

四個實測事實（2026-09-16～17），每一個都曾讓人誤判：

1. **公司頁的公告清單是 AJAX 載入的。** `/company/IQE` 的 HTML 裡零筆公告連結；清單在
   `/company/IQE/announcements`（頁面用 jQuery `$.ajax` 打它），回一張四欄表（日期／時間／來源／標題）。
2. **日期不在頁面 metadata 裡。** JSON-LD 只是 WebPage、沒有 datePublished、沒有 `<time>`；
   一手日期是 RNS 本體開頭的 dateline（`<div>IQE PLC</div><div>12 August 2026</div>`），
   清單另有日期＋時間。兩者都記；沒有 dateline 就拒寫，不得用抓取日冒充（AGENTS.md 反向禁令）。
3. **頁面有「Summary by AI」區塊**——那不是一手，抽取只取 `news-window` 內的 RNS 本體。
4. **站點會整段時間回 502**（2026-09-16 晚間連續半小時）。5xx／timeout 是「站點暫時不可用」，
   404 才是「這則不存在」——兩者的下一步不同（等 vs 換 id），錯誤訊息必須分開講（L12）。
   ⚠ IQE 年報 PDF 的查核報告雙欄交錯、pdfplumber 也讀不出來；going concern 附註要抓
   **年度業績 RNS 全文**（HTML 的「2.2 Going concern」段完整可讀）——這才是該待辦卡住的真正原因。

用法:
    python -m fetchers.rns --company IQE --list
    python -m fetchers.rns --company IQE --list --match "results"
    python -m fetchers.rns --url https://www.investegate.co.uk/announcement/rns/iqe--iqe/<headline-slug>/<id>
    python -m fetchers.rns --company IQE --match "FY 2025 Financial Results" --latest
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:  # pragma: no cover - 環境問題，非邏輯
    print("需要 requests 套件: pip install requests", file=sys.stderr)
    sys.exit(1)

from fetchers.utils import build_headers, html_to_text, rate_sleep, write_raw

INVESTEGATE = "https://www.investegate.co.uk"
#: RNS 是交易所的法定揭露服務，dateline 就是申報／發布日。
PUBLISHED_AT_METHOD = "filing_metadata"
#: 5xx／timeout 的重試節奏（秒）；404 不重試。
RETRY_BACKOFF = (5, 15)

_ANNOUNCEMENT_PATH = re.compile(
    r"^/(?:index\.php/)?announcement/rns/([a-z0-9-]+)--([a-z0-9-]+)/[^/]+/(\d+)/?$")
_TICKER = re.compile(r"^[A-Za-z0-9.-]+$")
_MONTHS = {
    m: i for i, names in enumerate((
        ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"),
        ("may",), ("june", "jun"), ("july", "jul"), ("august", "aug"),
        ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"), ("december", "dec"),
    ), start=1) for m in names
}
_LONG_DATE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\.?\s+(20\d{2})\b")
_MAIN_TITLE = re.compile(r'<h1 id="main-title">(.*?)</h1>', re.S)
_NEWS_WINDOW_START = re.compile(r'<div class="art-board[^"]*news-window">', re.S)
_DATELINE = re.compile(r"<body[^>]*>.*?<div>(.*?)</div>\s*<div>(.*?)</div>", re.S)
_RNS_NUMBER = re.compile(r"RNS\s+Number\s*:?\s*([A-Z0-9]{4,6})")
_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_ANNOUNCEMENT_LINK = re.compile(r'<a class="announcement-link" href="([^"]+)">(.*?)</a>', re.S)


class RnsError(RuntimeError):
    """頁面缺了不能猜的東西（dateline、正文）、或站點狀態——拒寫而不是補預設值。"""


# ---------------------------------------------------------------------------
# URL 與 id
# ---------------------------------------------------------------------------

def parse_announcement_url(url: str) -> tuple[str, str, str]:
    """回 (company_slug, ticker_key, announcement_id)，例：('iqe', 'iqe', '9588930')。

    investegate 的公司鍵是 `<company-slug>--<ticker-slug>`；`/index.php/` 前綴是同一頁的舊寫法。
    """
    match = _ANNOUNCEMENT_PATH.match(urlsplit(url).path)
    if not match:
        raise RnsError(
            "URL 不是 investegate 公告頁形狀（/announcement/rns/<company>--<ticker>/<slug>/<id>）"
            f"——多半是 URL 被截斷：{url}")
    return match.group(1), match.group(2), match.group(3)


def make_rns_doc_id(ticker_key: str, announcement_id: str) -> str:
    """`rns_<ticker>_<id>`；id 是 investegate 的公告流水號，同一則重抓得到同一個 doc_id。"""
    return f"rns_{ticker_key.lower().replace('-', '_')}_{announcement_id}"


def listing_url(ticker: str) -> str:
    if not _TICKER.match(ticker or ""):
        raise RnsError(f"ticker 只能是英數與點／連字號：{ticker!r}")
    return f"{INVESTEGATE}/company/{ticker.upper()}/announcements"


# ---------------------------------------------------------------------------
# 日期
# ---------------------------------------------------------------------------

def parse_long_date(text: str) -> str | None:
    """`12 August 2026`／`07 Sep 2026` → `2026-08-12`；不是日期就回 None（由呼叫端決定拒寫）。"""
    match = _LONG_DATE.search(html_to_text(text) if "<" in text else text)
    if not match:
        return None
    month = _MONTHS.get(match.group(2).lower())
    if not month:
        return None
    return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(1)):02d}"


# ---------------------------------------------------------------------------
# 清單（/company/<TICKER>/announcements）
# ---------------------------------------------------------------------------

def parse_listing(html: str) -> list[dict[str, object]]:
    """四欄表 → 公告清單。`regulatory` 看來源欄的 class（`regulatory source-RNS`）。"""
    items: list[dict[str, object]] = []
    for row in _ROW.findall(html):
        cells = _TD.findall(row)
        if len(cells) < 4:
            continue
        link = _ANNOUNCEMENT_LINK.search(cells[3])
        if not link:
            continue
        url = link.group(1)
        try:
            _, ticker_key, announcement_id = parse_announcement_url(url)
        except RnsError:
            continue
        items.append({
            "published_at": parse_long_date(cells[0]),
            "time_local": html_to_text(cells[1]).strip(),
            "source": html_to_text(cells[2]).strip(),
            "regulatory": 'class="regulatory' in cells[2],
            "title": html_to_text(link.group(2)).strip(),
            "url": url,
            "ticker_key": ticker_key,
            "announcement_id": announcement_id,
        })
    return items


def select_announcements(
    items: list[dict[str, object]], *, match: str | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """挑公告；回 (picked, report)，report 逐項報 input／accepted／filtered／reasons（INV-3）。"""
    reasons = {"match": 0, "undated": 0}
    needle = (match or "").casefold()
    picked: list[dict[str, object]] = []
    for item in items:
        if needle and needle not in str(item.get("title", "")).casefold():
            reasons["match"] += 1
            continue
        if not item.get("published_at"):
            reasons["undated"] += 1
            continue
        picked.append(item)
    return picked, {
        "input": len(items), "accepted": len(picked), "filtered": len(items) - len(picked),
        "reasons": {k: v for k, v in reasons.items() if v},
    }


def latest_only(items: list[dict[str, object]]) -> list[dict[str, object]]:
    """只留最新一則（日期，再以流水號分勝負——同日多則時號碼大的較晚）。"""
    if not items:
        return []
    return [max(items, key=lambda i: (str(i.get("published_at") or ""), int(str(i.get("announcement_id") or 0))))]


# ---------------------------------------------------------------------------
# 公告頁
# ---------------------------------------------------------------------------

def _news_window(html: str) -> str:
    start = _NEWS_WINDOW_START.search(html)
    if not start:
        raise RnsError("公告頁沒有 news-window 正文容器——確認這是單則公告頁而不是列表或 502 頁")
    end = html.find("</html>", start.end())
    if end == -1:
        nxt = html.find('<div class="art-board', start.end())
        end = nxt if nxt != -1 else len(html)
    return html[start.end():end]


def parse_announcement(html: str) -> dict[str, object]:
    """公告頁 → title／company／published_at／text／rns_number。

    兩處會 raise 而不是回預設值：沒有 news-window、dateline 沒有日期。「Summary by AI」
    不在 news-window 裡，所以自然被排除；正文保留 dateline 與 RNS 版權尾巴（逐字）。
    """
    title_match = _MAIN_TITLE.search(html)
    title = html_to_text(title_match.group(1)).strip() if title_match else ""
    window = _news_window(html)
    dateline = _DATELINE.search(window)
    published_at = parse_long_date(dateline.group(2)) if dateline else None
    if not published_at:
        raise RnsError(
            "RNS 本體開頭沒有 dateline 日期（<div>公司</div><div>d Month yyyy</div>）——"
            "不得用抓取日冒充 published_at；先確認頁面完整（不是 502／截斷）")
    text = html_to_text(window)
    if not text.strip():
        raise RnsError("公告正文抽出來是空的")
    rns_number = _RNS_NUMBER.search(text)
    company = title.split(":", 1)[0].strip() if ":" in title else None
    return {
        "title": title,
        "company": company,
        "dateline_company": html_to_text(dateline.group(1)).strip(),
        "dateline_date": html_to_text(dateline.group(2)).strip(),
        "published_at": published_at,
        "rns_number": rns_number.group(1) if rns_number else None,
        "text": text,
    }


# ---------------------------------------------------------------------------
# 抓取
# ---------------------------------------------------------------------------

def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(build_headers())
    return session


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_with_retry(session: requests.Session, url: str, *, timeout: int = 60,
                   headers: dict[str, str] | None = None, sleep=time.sleep) -> requests.Response:
    """5xx／timeout 重試兩次後放棄並說「站點暫時不可用」；404 不重試並說「這則不存在」。

    兩句話對應兩個不同的下一步（等 vs 換 id）；壓成同一句就是 L12 一表兩義。
    """
    last: str = ""
    for attempt in range(len(RETRY_BACKOFF) + 1):
        try:
            resp = session.get(url, timeout=timeout, headers=headers)
        except requests.RequestException as exc:
            last = f"{type(exc).__name__}"
        else:
            rate_sleep()
            if resp.status_code == 404:
                raise RnsError(f"investegate 回 404：{url}——這則公告 id 不存在或 URL 被截斷（不是站點問題）")
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp
            last = f"HTTP {resp.status_code}"
        if attempt < len(RETRY_BACKOFF):
            print(f"[rns] ⚠ {last}，{RETRY_BACKOFF[attempt]}s 後重試（{attempt + 1}/{len(RETRY_BACKOFF)}）",
                  file=sys.stderr)
            sleep(RETRY_BACKOFF[attempt])
    raise RnsError(f"investegate 暫時不可用（最後一次：{last}）——這是站點狀態，不是公告不存在；稍後重試")


def fetch_listing(ticker: str, *, session: requests.Session | None = None) -> list[dict[str, object]]:
    session = session or _session()
    resp = get_with_retry(session, listing_url(ticker), timeout=60,
                          headers={"X-Requested-With": "XMLHttpRequest",
                                   "Referer": f"{INVESTEGATE}/company/{ticker.upper()}"})
    return parse_listing(resp.text)


def _kind_fields(regulatory: bool | None) -> dict[str, object]:
    """法定公告＝issuer 申報（tier 1）；非法定＝tier 2；查不到就保守記 2 並保留 None。"""
    if regulatory is True:
        return {"source_type": "filing", "evidence_tier": 1, "regulatory": True}
    if regulatory is False:
        return {"source_type": "news", "evidence_tier": 2, "regulatory": False}
    return {"source_type": "news", "evidence_tier": 2, "regulatory": None}


def fetch_announcement(
    url: str,
    *,
    out_dir: Path,
    listing_item: dict[str, object] | None = None,
    session: requests.Session | None = None,
) -> dict[str, object]:
    """抓一則公告寫進 out_dir，回傳寫入的 meta。"""
    session = session or _session()
    company_slug, ticker_key, announcement_id = parse_announcement_url(url)
    resp = get_with_retry(session, url, timeout=90)
    page = parse_announcement(resp.text)

    if listing_item is None:
        try:
            listing_item = next((i for i in fetch_listing(ticker_key, session=session)
                                 if i.get("announcement_id") == announcement_id), None)
        except (RnsError, requests.RequestException) as exc:
            print(f"[rns] ⚠ 清單查不到（{exc}）；是否法定公告未知", file=sys.stderr)
            listing_item = None
    regulatory = None if listing_item is None else bool(listing_item.get("regulatory"))
    if regulatory is None:
        print("[rns] ⚠ 這則不在公司清單視窗內，無法判定是否法定公告——"
              "source_type 暫記 news／tier 2，抽取時依內容改", file=sys.stderr)
    listed_date = (listing_item or {}).get("published_at")
    if listed_date and listed_date != page["published_at"]:
        print(f"[rns] ⚠ dateline {page['published_at']} 與清單日期 {listed_date} 不同；"
              "以 RNS 本體 dateline 為準並記錄兩者", file=sys.stderr)

    doc_id = make_rns_doc_id(ticker_key, announcement_id)
    basis = (f"RNS 本體 dateline「{page['dateline_company']} / {page['dateline_date']}」"
             "（investegate news-window 內由 RNS 生成的標頭）")
    if listing_item:
        basis += f"；investegate 清單 {listed_date} {listing_item.get('time_local')}"
    meta = {
        "doc_id": doc_id,
        **_kind_fields(regulatory),
        "market": "UK",
        "exchange": "London Stock Exchange",
        "channel": "RNS",
        "mirror": "investegate.co.uk",
        "company_key": f"{company_slug}--{ticker_key}",
        "ticker_key": ticker_key,
        "origin_entity": page["company"],
        "dateline_company": page["dateline_company"],
        "title": page["title"],
        "announcement_id": announcement_id,
        "rns_number": page["rns_number"],
        "url": url,
        "published_at": page["published_at"],
        "published_at_method": PUBLISHED_AT_METHOD,
        "published_at_basis": basis,
        "listed_at": (f"{listed_date} {listing_item.get('time_local')}" if listing_item else None),
        "retrieved_at": _today_utc(),
        "chars": len(page["text"]),
        "truncated": False,
    }
    text_path, _ = write_raw(doc_id, page["text"], meta, out_dir)
    print(f"[rns] {page['title'][:70]} → {text_path}（{len(page['text']):,} 字）")
    return meta


def fetch_company(
    ticker: str, *, out_dir: Path, match: str | None = None, latest: bool = False,
    session: requests.Session | None = None,
) -> list[dict[str, object]]:
    session = session or _session()
    items = fetch_listing(ticker, session=session)
    picked, report = select_announcements(items, match=match)
    print(f"[rns] {ticker.upper()} 清單 {report['input']} 則，符合 {report['accepted']} 則，"
          f"濾掉 {report['filtered']} 則 {report['reasons']}", file=sys.stderr)
    if latest:
        picked = latest_only(picked)
    return [fetch_announcement(str(i["url"]), out_dir=out_dir, listing_item=i, session=session)
            for i in picked]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="從 investegate 鏡像抓 LSE RNS 公告全文")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--company", help="investegate 的公司 ticker，如 IQE")
    target.add_argument("--url", help="單則公告頁 URL（/announcement/rns/<company>--<ticker>/<slug>/<id>）")
    parser.add_argument("--list", action="store_true", help="只列出清單視窗內符合的公告，不下載")
    parser.add_argument("--match", default=None, help="標題子字串（不分大小寫）")
    parser.add_argument("--latest", action="store_true", help="符合者只取最新一則")
    parser.add_argument("--out", default="library/raw", help="輸出目錄")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)

    try:
        if args.url:
            fetch_announcement(args.url, out_dir=out_dir)
            return 0
        if args.list:
            items = fetch_listing(args.company)
            picked, report = select_announcements(items, match=args.match)
            print(f"[rns] {args.company.upper()} 清單 {report['input']} 則，符合 {report['accepted']} 則，"
                  f"濾掉 {report['filtered']} 則 {report['reasons']}", file=sys.stderr)
            if not items:
                print(f"[rns] {args.company}：清單空——先確認 ticker（瀏覽 {INVESTEGATE}/company/{args.company.upper()}）",
                      file=sys.stderr)
                return 1
            if not picked:
                print("[rns] ⚠ 清單有公告但沒有一則符合——這是「條件沒命中」不是「查無公告」；換 --match",
                      file=sys.stderr)
                return 1
            for item in (latest_only(picked) if args.latest else picked):
                flag = "REG" if item.get("regulatory") else "pr "
                print(f"  {item['published_at']} {str(item['time_local']):>8} | {flag} | "
                      f"{str(item['title'])[:70]:72} | {item['url']}")
            return 0
        written = fetch_company(args.company, out_dir=out_dir, match=args.match, latest=args.latest)
        return 0 if written else 1
    except RnsError as exc:
        print(f"[rns] ✗ {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
