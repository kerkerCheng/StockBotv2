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
