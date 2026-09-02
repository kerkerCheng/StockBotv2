"""arXiv 論文抓取器——把「一篇論文」變成可進 extract 流程的 raw＋meta。

ROADMAP 交付（2026-09-02 使用者核准）：TPU（2304.01433／2208.10041）與 Unitree G1
（2606.15915）兩輪 decompose 都在手寫同一段 requests＋pypdf 樣板。本模組與
`fetchers/edgar.py` 同構：下載 PDF → 抽全文 → `write_raw` 產出
`library/raw/<doc_id>.txt` ＋ `<doc_id>.meta.json`。

純互動工具，不掛排程；arXiv 論文屬公開 preprint，抓取無 paywall 議題。
evidence tier 預設 2（未經同儕審查的 preprint；已發表版本由研究者在 extraction
覆寫）——tier 判斷是研究者的事，fetcher 只帶預設。
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from fetchers.utils import write_raw

_UA = "StockBotv2 research fetcher (contact: c3035281@gmail.com)"
_ATOM = "{http://www.w3.org/2005/Atom}"


def normalize_arxiv_id(raw: str) -> str:
    """接受 `2304.01433`、`arXiv:2304.01433v2`、abs/pdf URL，回裸 id（保留版本號）。"""
    s = raw.strip()
    s = re.sub(r"^arxiv:", "", s, flags=re.I)
    m = re.search(r"(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?", s):
        return s
    raise ValueError(f"無法解析 arXiv id：{raw!r}")


def fetch_metadata(arxiv_id: str) -> dict:
    """arXiv Atom API 取 title／authors／published——逐字 metadata，不猜。

    429 時退避重試一次；仍失敗則降級回空 metadata（title=None 現形，
    不擋 PDF 全文抓取——metadata 可之後補，全文才是 extract 的主體）。
    """
    import time

    resp = None
    for attempt in (1, 2):
        resp = requests.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": arxiv_id, "max_results": 1},
            headers={"User-Agent": _UA},
            timeout=60,
        )
        if resp.status_code != 429:
            break
        if attempt == 1:
            time.sleep(15)
    if resp is not None and resp.status_code == 429:
        print(
            "[arxiv] WARN: metadata API 429（rate limited），"
            "降級為無 metadata——title/authors 留空待補",
            file=sys.stderr,
        )
        return {
            "title": None,
            "authors": [],
            "published": "",
            "updated": "",
            "summary": "",
        }
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entry = root.find(f"{_ATOM}entry")
    if entry is None:
        raise RuntimeError(f"arXiv API 查無此 id：{arxiv_id}")
    title = re.sub(r"\s+", " ", (entry.findtext(f"{_ATOM}title") or "").strip())
    authors = [
        (a.findtext(f"{_ATOM}name") or "").strip()
        for a in entry.findall(f"{_ATOM}author")
    ]
    return {
        "title": title,
        "authors": [a for a in authors if a],
        "published": (entry.findtext(f"{_ATOM}published") or "")[:10],
        "updated": (entry.findtext(f"{_ATOM}updated") or "")[:10],
        "summary": re.sub(
            r"\s+", " ", (entry.findtext(f"{_ATOM}summary") or "").strip()
        ),
    }


def fetch_pdf_text(arxiv_id: str) -> str:
    from pypdf import PdfReader

    resp = requests.get(
        f"https://arxiv.org/pdf/{arxiv_id}",
        headers={"User-Agent": _UA},
        timeout=180,
    )
    resp.raise_for_status()
    if resp.content[:4] != b"%PDF":
        raise RuntimeError(
            f"arXiv 回傳的不是 PDF（前 4 bytes: {resp.content[:4]!r}）"
        )
    reader = PdfReader(io.BytesIO(resp.content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def doc_id_for(arxiv_id: str) -> str:
    return "arxiv_" + re.sub(r"[.v]", "_", arxiv_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="從 arXiv 抓論文全文＋metadata，產出可進 extract 流程的 raw 檔"
    )
    parser.add_argument("--id", required=True, help="arXiv id 或 abs/pdf URL")
    parser.add_argument("--out", default="library/raw", help="輸出目錄，預設 library/raw")
    args = parser.parse_args(argv)

    arxiv_id = normalize_arxiv_id(args.id)
    try:
        meta_api = fetch_metadata(arxiv_id)
    except Exception as exc:  # noqa: BLE001 — metadata 可補，全文才是主體
        print(f"[arxiv] WARN: metadata API 失敗（{exc}），降級為無 metadata", file=sys.stderr)
        meta_api = {"title": None, "authors": [], "published": "", "updated": "", "summary": ""}
    text = fetch_pdf_text(arxiv_id)
    doc_id = doc_id_for(arxiv_id)
    meta = {
        "doc_id": doc_id,
        "source_type": "paper",
        "evidence_tier": 2,
        "arxiv_id": arxiv_id,
        "title": meta_api["title"],
        "authors": meta_api["authors"],
        "published": meta_api["published"],
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "original_chars": len(text),
    }
    txt_path, meta_path = write_raw(doc_id, text, meta, Path(args.out))
    print(f"[arxiv] saved {txt_path.name} ({len(text):,} chars)")
    print(f"[arxiv] meta  {meta_path.name} — {(meta_api['title'] or '(metadata 降級,title 待補)')[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
