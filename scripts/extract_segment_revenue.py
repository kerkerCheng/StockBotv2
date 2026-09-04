"""從 SEC 年報定位分部營收表，**印出供人核對**——不寫入任何 authority。

## 為什麼抽取與寫入是兩支腳本

抽取是語意工作（哪張表才是分部營收、哪一欄是本期、名稱怎麼對應），會出錯；
寫入是確定性的（JSON 數值＋provenance＋append-only）。L15：**語意交給語言處理，
權限永遠 deterministic**；把兩者混在一支裡，等於讓一個會猜的東西直接落庫。

所以本支只負責把**候選區塊**攤出來給人看，抄不抄、抄哪一欄由讀的人決定，
再走 `scripts/record_mechanical_observation.py` 寫入。

用法：
    python scripts/extract_segment_revenue.py --ticker COHR
    python scripts/extract_segment_revenue.py --ticker AAOI AXTI LITE --chars 900

⚠ 只涵蓋 SEC 申報人（10-K／20-F）。台股走公開資訊觀測站、日股走 TDnet、
歐股各自的 URD／Annual Report——那些沒有統一 API，要逐檔人工。
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fetchers.edgar import fetch_filing_text, get_cik, get_filings  # noqa: E402

#: 分部營收表的入口詞。刻意寬——寧可多印幾段讓人看，也不要漏掉正確那張表。
#: 這裡的錯誤成本是「多讀 300 字」，而漏掉的成本是「以為公司沒揭露」（L11-5）。
_ANCHORS = (
    r"disaggregat\w+ revenue",
    r"revenue by (?:market|segment|product)",
    r"segment (?:information|reporting|data)",
    r"reportable segments?",
    r"operating segments?",
)

#: 看起來像金額的數字：至少四位、帶千分位或連續數字。
_MONEY = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{5,}\b")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text))


def dump(ticker: str, *, chars: int, forms: tuple[str, ...]) -> int:
    cik = get_cik(ticker)
    if not cik:
        print(f"  ✗ {ticker}: EDGAR 查不到 CIK（可能不是 SEC 申報人）")
        return 1
    filings = get_filings(cik, list(forms), 1)
    if not filings:
        print(f"  ✗ {ticker}: 找不到 {'/'.join(forms)}")
        return 1
    f = filings[0]
    text = fetch_filing_text(cik, f["accession"], f["primary_doc"])
    if not text:
        print(f"  ✗ {ticker}: 全文抓不到")
        return 1

    print(f"\n{'=' * 78}")
    print(f"{ticker} | {f['form_type']} | filed {f['filed_date']} | "
          f"accession {f['accession']} | 全文 {len(text):,}")
    print("=" * 78)

    seen: set[int] = set()
    hits = 0
    for pattern in _ANCHORS:
        for m in re.finditer(pattern, text, re.I):
            block = _plain(text[m.start(): m.start() + chars])
            # 只印**有金額**的區塊——純敘述段落對抄表沒用。
            if len(_MONEY.findall(block)) < 3:
                continue
            if any(abs(m.start() - s) < chars // 2 for s in seen):
                continue
            seen.add(m.start())
            hits += 1
            print(f"\n--- 命中 #{hits}（{pattern}）@ {m.start()} ---")
            print(block)
            if hits >= 3:
                break
        if hits >= 3:
            break
    if not hits:
        print("  ⚠ 找不到帶金額的分部區塊。**這不等於公司沒揭露**——")
        print("    可能是表格被轉成純文字後數字與標題分離（L11-5：找不到 ≠ 不存在）。")
        print("    下一步：直接開 primary_doc 的 HTML 看 Note，或改用 R-file。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", nargs="+", required=True)
    parser.add_argument("--chars", type=int, default=1100)
    parser.add_argument("--forms", nargs="+", default=["10-K", "20-F"])
    args = parser.parse_args()
    for ticker in args.ticker:
        try:
            dump(ticker, chars=args.chars, forms=tuple(args.forms))
        except Exception as exc:  # noqa: BLE001 — 一檔失敗不擋其他檔
            print(f"  ✗ {ticker}: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
