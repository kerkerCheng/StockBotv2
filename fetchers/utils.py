"""共用工具：rate limiter、doc_id 生成、meta.json 寫入。"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path


def make_doc_id(ticker: str, form_type: str, filed_date: str) -> str:
    """生成唯一 doc_id，格式：{ticker}_{form}_{date}，全小寫、特殊字元替換為底線。"""
    safe_ticker = re.sub(r"[^a-z0-9]", "_", ticker.lower())
    safe_form = re.sub(r"[^a-z0-9]", "_", form_type.lower())
    safe_date = filed_date.replace("-", "")[:8]
    return f"{safe_ticker}_{safe_form}_{safe_date}"


def write_raw(doc_id: str, text: str, meta: dict, out_dir: Path) -> tuple[Path, Path]:
    """把文件文字與 meta 寫入 library/raw/。回傳 (txt_path, meta_path)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = out_dir / f"{doc_id}.txt"
    meta_path = out_dir / f"{doc_id}.meta.json"
    txt_path.write_text(text, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return txt_path, meta_path


def rate_sleep(seconds: float = 0.2) -> None:
    """EDGAR 要求 < 10 req/s，每次請求後 sleep 0.2s。"""
    time.sleep(seconds)


def build_headers() -> dict[str, str]:
    """公開文件抓取器共用的 User-Agent（與 edgar.py／mops.py 同一個聯絡信箱慣例）。"""
    import os

    return {
        "User-Agent": (
            "StockBotv2 research (contact: "
            f"{os.getenv('EDGAR_CONTACT_EMAIL', 'research@example.com')})"
        )
    }


_BLOCK_TAGS = (
    "p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
    "tr", "table", "thead", "tbody", "section", "article", "header", "footer",
    "blockquote", "pre", "hr", "dt", "dd",
)


def html_to_text(fragment: str) -> str:
    """HTML 片段 → 純文字（給 MFN／RNS 這類把全文放在頁面裡的來源）。

    ⚠ 刻意**不**用 `get_text("\n")`：MFN 的正文把每個字組包在獨立的 `<span>` 裡，
    以換行當分隔會把一句話拆成十行。做法是 inline 元素直接相連（原文的空白已在
    `<span> </span>` 裡）、只有區塊元素前後補換行，最後把連續空白壓成一個、空行最多留一個。
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(fragment, "html.parser")
    for tag in soup(["script", "style", "img", "noscript"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
        if tag.name == "li":
            tag.insert(0, "- ")
    text = soup.get_text("")
    lines = [re.sub(r"[ \t\r\f\v\xa0]+", " ", line).strip() for line in text.splitlines()]
    out: list[str] = []
    blank = False
    for line in lines:
        if line:
            out.append(line)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip() + "\n"
