"""
mfn.py — 從 MFN（Modular Finance News）抓 Nasdaq Stockholm／First North 上市公司的公告全文與附件。

MFN 是瑞典上市公司法定訊息揭露（regulatory information）的發布管道；
`crons/harvest_config.json` 的 `mfn:sivers-semiconductors` feed 已經在 daily harvest 監看它的 RSS，
但 lead 進了池子之後從沒有可重用的抓取器——既有入庫的 Sivers 文件全是 session 手抓。

輸出格式（與 mops.py／edgar.py 一致）：
    library/raw/{doc_id}.txt       — 公告正文（HTML 轉純文字）
    library/raw/{doc_id}.meta.json — doc metadata（含 published_at 與其依據）
    附件 PDF 各自成一份 doc：{doc_id}_att{N}.txt／.meta.json（期中報告本體通常在這裡）

三個實測事實（2026-09-16），每一個都曾讓人誤判：

1. **同一事件發兩則。** 瑞典文與英文各一則、`pubDate` 完全相同、`x:newsId` 不同。
   預設只取英文版（`--lang en`）；兩則都入庫會把同一份文件算成兩個來源（L8）。
2. **日期在 JSON-LD 的 `datePublished`（＝RSS `pubDate`，UTC）。** 頁面上的 `publish-date` 是
   斯德哥爾摩當地時間，跨日時會差一天；一律以 UTC 時戳為準，並把整個時戳寫進 `published_at_basis`。
   ⚠ 沒有 datePublished 就拒寫，不得用抓取日冒充（AGENTS.md 反向禁令）。
3. **附件不在 RSS 裡。** 期中報告本體是 mb.cision.com 的 PDF，只掛在公告頁的「Bifogade filer」；
   RSS 的 `x:content` 只有正文。所以「RSS 抓得到」不等於「報告抓得到」。
   ⚠ 上一輪探到 404 是 URL 被截斷造成的，不是路由不通。

用法:
    python -m fetchers.mfn --company sivers-semiconductors --list
    python -m fetchers.mfn --company sivers-semiconductors --list --match "Q2 2026"
    python -m fetchers.mfn --url https://mfn.se/cis/a/sivers-semiconductors/<headline-slug>-<id>
    python -m fetchers.mfn --company sivers-semiconductors --match "reports q2 2026" --latest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

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

MFN_BASE = "https://mfn.se"
MFN_NS = "https://mfn.se/schemas/rss-ns-x/"
#: MFN 是交易所認可的法定揭露管道，公告的 datePublished 就是申報時戳。
PUBLISHED_AT_METHOD = "filing_metadata"
#: 附件 PDF 掛在 Cision 的檔案主機；抓取器只連這兩個主機。
ATTACHMENT_HOSTS = ("mb.cision.com",)

_SLUG = re.compile(r"^[a-z0-9-]+$")
_RELEASE_ID = re.compile(r"-([0-9a-f]{8})/?$")
_COMPANY_IN_PATH = re.compile(r"^/cis/a/([a-z0-9-]+)/")


class MfnError(RuntimeError):
    """頁面或 feed 缺了不能猜的東西（日期、正文、公司）——拒寫而不是補預設值。"""


# ---------------------------------------------------------------------------
# URL 與 id
# ---------------------------------------------------------------------------

def feed_url(company_slug: str) -> str:
    if not _SLUG.match(company_slug or ""):
        raise MfnError(f"MFN 公司 slug 只能是小寫英數與連字號：{company_slug!r}")
    return f"{MFN_BASE}/all/a/{company_slug}.rss"


def release_id_from_url(url: str) -> str:
    """公告 URL 尾端的 8 碼 hex 是 MFN 的公告 id（newsId 的首段）。"""
    match = _RELEASE_ID.search(urlsplit(url).path)
    if not match:
        raise MfnError(f"URL 尾端沒有 8 碼公告 id——多半是 URL 被截斷：{url}")
    return match.group(1)


def company_slug_from_url(url: str) -> str:
    match = _COMPANY_IN_PATH.match(urlsplit(url).path)
    if not match:
        raise MfnError(f"URL 不是 MFN 公告頁形狀（/cis/a/<company>/...）：{url}")
    return match.group(1)


def make_mfn_doc_id(company_slug: str, release_id: str, *, attachment_index: int | None = None) -> str:
    """`mfn_<company>_<id>`；附件加 `_att<N>`。id 來自 URL，所以同一則公告重抓得到同一個 doc_id。"""
    doc_id = f"mfn_{company_slug.replace('-', '_')}_{release_id}"
    if attachment_index is not None:
        doc_id = f"{doc_id}_att{attachment_index}"
    return doc_id


# ---------------------------------------------------------------------------
# 日期
# ---------------------------------------------------------------------------

def _to_utc_stamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise MfnError(f"時戳沒有時區，無法轉 UTC：{moment!r}")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rfc822_to_utc(value: str) -> str:
    """RSS pubDate（RFC 822）→ `YYYY-MM-DDTHH:MM:SSZ`。"""
    return _to_utc_stamp(parsedate_to_datetime(value.strip()))


def iso_to_utc(value: str) -> str:
    """JSON-LD datePublished（ISO 8601，`Z` 或帶時差）→ `YYYY-MM-DDTHH:MM:SSZ`。"""
    return _to_utc_stamp(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))


# ---------------------------------------------------------------------------
# RSS
# ---------------------------------------------------------------------------

def parse_feed(xml_text: str) -> list[dict[str, object]]:
    """把 MFN RSS 解成公告清單。

    每則帶 `language`（en／sv）、`regulatory`（`x:tag` 含 `:regulatory`）、`published_at_time`（UTC）。
    沒有 pubDate 的項目 `published_at` 留 None——由挑選端列進報告，不在這裡補。
    """
    root = ET.fromstring(xml_text)
    releases: list[dict[str, object]] = []
    for item in root.iter("item"):
        url = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        stamp = rfc822_to_utc(pub) if pub else None
        tags = [t.text.strip() for t in item.findall(f"{{{MFN_NS}}}tag") if t.text]
        language = (item.findtext(f"{{{MFN_NS}}}language") or "").strip() or None
        releases.append({
            "title": (item.findtext("title") or "").strip(),
            "url": url,
            "release_id": release_id_from_url(url) if _RELEASE_ID.search(urlsplit(url).path) else None,
            "news_id": (item.findtext(f"{{{MFN_NS}}}newsId") or "").strip() or None,
            "language": language,
            "regulatory": ":regulatory" in tags,
            "tags": tags,
            "published_at": stamp[:10] if stamp else None,
            "published_at_time": stamp,
        })
    return releases


def select_releases(
    releases: list[dict[str, object]],
    *,
    match: str | None = None,
    language: str = "en",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """挑公告；回 (picked, report)。report 逐項報 input／accepted／filtered／reasons（INV-3）。

    `language="all"` 才會把瑞典文孿生留下；預設只留英文——同一事件兩則不是兩份來源。
    """
    reasons: dict[str, int] = {"language": 0, "match": 0, "undated": 0}
    picked: list[dict[str, object]] = []
    needle = (match or "").casefold()
    for release in releases:
        if language != "all" and release.get("language") != language:
            reasons["language"] += 1
            continue
        if needle and needle not in str(release.get("title", "")).casefold():
            reasons["match"] += 1
            continue
        if not release.get("published_at"):
            reasons["undated"] += 1
            continue
        picked.append(release)
    report = {
        "input": len(releases),
        "accepted": len(picked),
        "filtered": len(releases) - len(picked),
        "reasons": {k: v for k, v in reasons.items() if v},
    }
    return picked, report


def latest_only(releases: list[dict[str, object]]) -> list[dict[str, object]]:
    """只留最新一則（依 UTC 時戳；同秒時保留 feed 順序的第一則）。"""
    if not releases:
        return []
    return [max(releases, key=lambda r: str(r.get("published_at_time") or ""))]


# ---------------------------------------------------------------------------
# 公告頁
# ---------------------------------------------------------------------------

_LD_JSON = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_HTML_LANG = re.compile(r'<html[^>]*\blang="([A-Za-z-]+)"')
_COMPANY_LABEL = re.compile(r'<label class="heading-1"[^>]*>\s*<a href="/all/a/[^"]+">(.*?)</a>', re.S)
_ARTICLE = re.compile(r"<article\b.*?</article>", re.S)
_CONTENT_DIV = re.compile(r'<div class="content[^"]*">(.*)', re.S)
#: ⚠ 原始 HTML 的 <a> 屬性跨行、href 不一定是第一個屬性——2026-09-17 第一次 smoke 就因此
#: 一份附件都沒抓到（測試 fixture 寫成單行所以是綠的）。
_PDF_HREF = re.compile(r'<a\s[^>]*?href="(https?://[^"]+\.pdf)"', re.S)


def _json_ld(html: str) -> dict[str, object]:
    for block in _LD_JSON.finditer(html):
        try:
            data = json.loads(block.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("datePublished"):
            return data
    return {}


def parse_release_page(html: str) -> dict[str, object]:
    """公告頁 → headline／published_at（UTC）／language／company／text／attachments。

    三處會 raise 而不是回預設值：沒有 JSON-LD datePublished、沒有 `<article>` 正文、
    正文抽出來是空的。它們都代表「這頁不是我以為的那種頁」，補預設值只會讓錯的東西入庫。
    """
    ld = _json_ld(html)
    date_published = str(ld.get("datePublished") or "")
    if not date_published:
        raise MfnError(
            "公告頁沒有 JSON-LD datePublished——不得用抓取日冒充 published_at；"
            "先確認 URL 是單則公告頁（/cis/a/<company>/<slug>-<id>）而不是列表頁"
        )
    stamp = iso_to_utc(date_published)
    article = _ARTICLE.search(html)
    if not article:
        raise MfnError("公告頁沒有 <article> 正文容器")
    content = _CONTENT_DIV.search(article.group(0))
    text = html_to_text(content.group(1) if content else article.group(0))
    if not text.strip():
        raise MfnError("公告正文抽出來是空的")
    lang = _HTML_LANG.search(html)
    company = _COMPANY_LABEL.search(html)
    # 附件只掛在左欄 entity-info（article 之前）；右欄正文裡的連結不算附件。
    head = html[: article.start()]
    attachments: list[str] = []
    for href in _PDF_HREF.findall(head):
        if href not in attachments:
            attachments.append(href)
    return {
        "headline": str(ld.get("headline") or "").strip(),
        "published_at": stamp[:10],
        "published_at_time": stamp,
        "date_published_raw": date_published,
        "language": lang.group(1).lower() if lang else None,
        "company": html_to_text(company.group(1)).strip() if company else None,
        "text": text,
        "attachments": attachments,
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


def _lookup_feed_item(company_slug: str, release_id: str, session: requests.Session) -> dict[str, object] | None:
    """用 RSS 補「這則是不是法定公告」；RSS 視窗（約 48 則）外的公告會查不到 → None。"""
    resp = session.get(feed_url(company_slug), timeout=30)
    resp.raise_for_status()
    rate_sleep()
    for item in parse_feed(resp.text):
        if item.get("release_id") == release_id:
            return item
    return None


def _kind_fields(regulatory: bool | None) -> dict[str, object]:
    """法定公告＝issuer 申報（tier 1）；一般新聞稿＝tier 2；查不到就保守記 2 並印出來。"""
    if regulatory is True:
        return {"source_type": "filing", "evidence_tier": 1, "regulatory": True}
    if regulatory is False:
        return {"source_type": "news", "evidence_tier": 2, "regulatory": False}
    return {"source_type": "news", "evidence_tier": 2, "regulatory": None}


def fetch_release(
    url: str,
    *,
    out_dir: Path,
    with_attachments: bool = True,
    feed_item: dict[str, object] | None = None,
    session: requests.Session | None = None,
) -> list[dict[str, object]]:
    """抓一則公告（＋附件）寫進 out_dir，回傳寫入的 meta 清單（公告在前、附件在後）。"""
    session = session or _session()
    company_slug = company_slug_from_url(url)
    release_id = release_id_from_url(url)
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    rate_sleep()
    page = parse_release_page(resp.text)

    if feed_item is None:
        try:
            feed_item = _lookup_feed_item(company_slug, release_id, session)
        except requests.RequestException as exc:
            print(f"[mfn] ⚠ RSS 查不到（{exc}）；是否法定公告未知", file=sys.stderr)
            feed_item = None
    regulatory = None if feed_item is None else bool(feed_item.get("regulatory"))
    if regulatory is None:
        print("[mfn] ⚠ 這則不在 RSS 視窗內，無法判定是否法定公告——"
              "source_type 暫記 news／tier 2，抽取時依內容改", file=sys.stderr)
    if feed_item and feed_item.get("published_at_time") and page["published_at_time"] != feed_item["published_at_time"]:
        # 兩個一手時戳不一致是要人看的事，不是靜默取其一。
        print(f"[mfn] ⚠ JSON-LD datePublished={page['published_at_time']} 與 RSS pubDate="
              f"{feed_item['published_at_time']} 不同；以頁面 JSON-LD 為準並記錄兩者", file=sys.stderr)

    doc_id = make_mfn_doc_id(company_slug, release_id)
    retrieved_at = _today_utc()
    base_meta = {
        **_kind_fields(regulatory),
        "market": "SE",
        "exchange": "Nasdaq Stockholm / First North",
        "channel": "MFN",
        "company_slug": company_slug,
        "origin_entity": page["company"],
        "language": page["language"] or (feed_item or {}).get("language"),
        "release_id": release_id,
        "news_id": (feed_item or {}).get("news_id"),
        "published_at": page["published_at"],
        "published_at_time": page["published_at_time"],
        "published_at_method": PUBLISHED_AT_METHOD,
        "retrieved_at": retrieved_at,
    }
    meta = {
        "doc_id": doc_id,
        **base_meta,
        "title": page["headline"],
        "url": url,
        "rss_pub_date": (feed_item or {}).get("published_at_time"),
        "published_at_basis": (
            f"MFN 公告頁 JSON-LD datePublished={page['date_published_raw']}"
            "（UTC；與 RSS pubDate 同源）"
        ),
        "attachments": [],
        "chars": len(page["text"]),
        "truncated": False,
    }
    written: list[dict[str, object]] = []
    text_path, _ = write_raw(doc_id, page["text"], meta, out_dir)
    print(f"[mfn] {company_slug} {page['headline'][:70]} → {text_path}（{len(page['text']):,} 字）")
    written.append(meta)

    if not with_attachments:
        return written
    from fetchers.mops import pdf_to_text

    for index, att_url in enumerate(page["attachments"], start=1):
        host = urlsplit(att_url).hostname or ""
        if host not in ATTACHMENT_HOSTS:
            print(f"[mfn] ⚠ 略過非登記主機的附件：{att_url}", file=sys.stderr)
            continue
        pdf = session.get(att_url, timeout=120)
        pdf.raise_for_status()
        rate_sleep()
        if not pdf.content.startswith(b"%PDF"):
            print(f"[mfn] ⚠ 附件不是 PDF（{len(pdf.content)} bytes）：{att_url}", file=sys.stderr)
            continue
        att_text, pages = pdf_to_text(pdf.content)
        att_id = make_mfn_doc_id(company_slug, release_id, attachment_index=index)
        att_meta = {
            "doc_id": att_id,
            **base_meta,
            "title": f"{page['headline']}（附件 {index}）",
            "url": att_url,
            "parent_doc_id": doc_id,
            "parent_url": url,
            "attachment_index": index,
            "published_at_basis": (
                f"公告 {doc_id} 的附件；日期取自該公告 JSON-LD datePublished="
                f"{page['date_published_raw']}"
            ),
            "pages": pages,
            "chars": len(att_text),
            "truncated": False,
        }
        att_path, _ = write_raw(att_id, att_text, att_meta, out_dir)
        meta["attachments"].append({"doc_id": att_id, "url": att_url, "pages": pages, "chars": len(att_text)})
        print(f"[mfn]   附件 {index} → {att_path}（{pages} 頁 / {len(att_text):,} 字）")
        written.append(att_meta)
    # 附件清單寫進公告 meta（重寫一次，附件 doc 已各自落地）
    write_raw(doc_id, page["text"], meta, out_dir)
    return written


def fetch_company(
    company_slug: str,
    *,
    out_dir: Path,
    match: str | None = None,
    language: str = "en",
    latest: bool = False,
    with_attachments: bool = True,
    session: requests.Session | None = None,
) -> list[dict[str, object]]:
    session = session or _session()
    resp = session.get(feed_url(company_slug), timeout=30)
    resp.raise_for_status()
    rate_sleep()
    releases = parse_feed(resp.text)
    picked, report = select_releases(releases, match=match, language=language)
    print(f"[mfn] {company_slug} RSS {report['input']} 則，符合 {report['accepted']} 則，"
          f"濾掉 {report['filtered']} 則 {report['reasons']}", file=sys.stderr)
    if latest:
        picked = latest_only(picked)
    written: list[dict[str, object]] = []
    for release in picked:
        written.extend(fetch_release(
            str(release["url"]), out_dir=out_dir, with_attachments=with_attachments,
            feed_item=release, session=session,
        ))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="從 MFN 抓 Nasdaq Stockholm 上市公司公告全文與附件")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--company", help="MFN 公司 slug，如 sivers-semiconductors（RSS 路徑那一段）")
    target.add_argument("--url", help="單則公告頁 URL（/cis/a/<company>/<slug>-<id>）")
    parser.add_argument("--list", action="store_true", help="只列出 RSS 視窗內符合的公告，不下載")
    parser.add_argument("--match", default=None, help="標題子字串（不分大小寫）")
    parser.add_argument("--lang", default="en", help="en／sv／all；預設只取英文版")
    parser.add_argument("--latest", action="store_true", help="符合者只取最新一則")
    parser.add_argument("--no-attachments", action="store_true", help="不下載附件 PDF")
    parser.add_argument("--out", default="library/raw", help="輸出目錄")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)

    if args.url:
        written = fetch_release(args.url, out_dir=out_dir, with_attachments=not args.no_attachments)
        return 0 if written else 1

    if args.list:
        session = _session()
        resp = session.get(feed_url(args.company), timeout=30)
        resp.raise_for_status()
        releases = parse_feed(resp.text)
        picked, report = select_releases(releases, match=args.match, language=args.lang)
        print(f"[mfn] {args.company} RSS {report['input']} 則，符合 {report['accepted']} 則，"
              f"濾掉 {report['filtered']} 則 {report['reasons']}", file=sys.stderr)
        if not releases:
            print(f"[mfn] {args.company}：RSS 空——先確認 slug（瀏覽 {feed_url(args.company)}）", file=sys.stderr)
            return 1
        if not picked:
            print("[mfn] ⚠ RSS 有公告但沒有一則符合——這是「條件沒命中」不是「查無公告」；"
                  "換 --match 或 --lang all", file=sys.stderr)
            return 1
        for release in (latest_only(picked) if args.latest else picked):
            flag = "REG" if release.get("regulatory") else "pr "
            print(f"  {release['published_at']} | {flag} | {release['language']} | "
                  f"{str(release['title'])[:70]:72} | {release['url']}")
        return 0

    written = fetch_company(
        args.company, out_dir=out_dir, match=args.match, language=args.lang,
        latest=args.latest, with_attachments=not args.no_attachments,
    )
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
