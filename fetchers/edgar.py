"""
edgar.py — 依 ticker 從 SEC EDGAR 自動抓 10-K / 10-Q / 8-K。

輸出格式：
    library/raw/{doc_id}.txt       — 純文字（HTML strip 後）
    library/raw/{doc_id}.meta.json — doc metadata，接回 extract pipeline

EDGAR rate limit: < 10 req/s → 每個請求後 sleep 0.2s。
User-Agent header 必須帶聯絡信箱（讀 .env 的 EDGAR_CONTACT_EMAIL）。

用法:
    python fetchers/edgar.py --ticker SIVE --forms 10-K,10-Q --n 2
    python fetchers/edgar.py --ticker COHR --forms 10-K --n 1 --out library/raw
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Allow `python fetchers/edgar.py ...` (not just `-m fetchers.edgar`): put repo root
# on sys.path before the `from fetchers.utils import ...` below.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    print("需要 requests 套件: pip install requests", file=sys.stderr)
    sys.exit(1)

from fetchers.utils import make_doc_id, rate_sleep, write_raw

EDGAR_BASE = "https://data.sec.gov"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS = f"{EDGAR_BASE}/submissions"

# evidence_tier by form type
FORM_TIER: dict[str, int] = {
    "10-K": 1,
    "10-Q": 1,
    "8-K": 1,
    "S-1": 1,
    "20-F": 1,
    "DEF 14A": 2,
}

_REMOVE_TAGS = re.compile(r"<[^>]+>")
_COLLAPSE_WS = re.compile(r"[ \t]{2,}")
_COLLAPSE_NL = re.compile(r"\n{3,}")


def _build_headers() -> dict[str, str]:
    email = os.environ.get("EDGAR_CONTACT_EMAIL", "researcher@example.com")
    return {
        "User-Agent": f"StockBotv2 research tool {email}",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }


def _strip_html(html: str) -> str:
    text = _REMOVE_TAGS.sub(" ", html)
    text = _COLLAPSE_WS.sub(" ", text)
    text = _COLLAPSE_NL.sub("\n\n", text)
    return text.strip()


def get_cik(ticker: str) -> str | None:
    """ticker → CIK（10 位補零格式）。"""
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom"
    headers = _build_headers()
    headers["Host"] = "www.sec.gov"
    rate_sleep()
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        # Parse CIK from response
        match = re.search(r"CIK=(\d+)", resp.text)
        if match:
            return match.group(1).zfill(10)
    except Exception as e:
        print(f"[edgar] CIK lookup failed for {ticker}: {e}", file=sys.stderr)

    # Fallback: company_tickers JSON
    rate_sleep()
    try:
        headers2 = _build_headers()
        headers2["Host"] = "www.sec.gov"
        r2 = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers2, timeout=15
        )
        r2.raise_for_status()
        data = r2.json()
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                return str(entry["cik_str"]).zfill(10)
    except Exception as e:
        print(f"[edgar] company_tickers fallback failed: {e}", file=sys.stderr)

    return None


def get_filings(cik: str, form_types: list[str], n: int) -> list[dict]:
    """取最近 n 份指定 form_type 的 filing metadata。"""
    url = f"{EDGAR_SUBMISSIONS}/CIK{cik}.json"
    headers = _build_headers()
    rate_sleep()
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[edgar] submissions fetch failed for CIK {cik}: {e}", file=sys.stderr)
        return []

    filings = []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    company_name = data.get("name", "")

    form_types_upper = [f.upper() for f in form_types]
    for i, form in enumerate(forms):
        if form.upper() in form_types_upper and len(filings) < n:
            acc = accessions[i].replace("-", "")
            filings.append({
                "form_type": form,
                "filed_date": dates[i],
                "accession": acc,
                "primary_doc": primary_docs[i] if i < len(primary_docs) else "",
                "company_name": company_name,
                "cik": cik,
            })
    return filings


def fetch_filing_text(cik: str, accession: str, primary_doc: str) -> str | None:
    """下載 filing 主文件，strip HTML，回傳純文字。"""
    # Archives 路徑在 www.sec.gov，CIK 不補零：/Archives/edgar/data/{cik}/{accession}/
    cik_int = str(int(cik))
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}"
    if primary_doc:
        url = f"{base_url}/{primary_doc}"
    else:
        url = f"{base_url}/{accession}.txt"

    headers = _build_headers()
    headers["Host"] = "www.sec.gov"
    rate_sleep()
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        content = resp.text
        if "<html" in content.lower() or "<HTML" in content:
            return _strip_html(content)
        return content.strip()
    except Exception as e:
        print(f"[edgar] fetch failed for {url}: {e}", file=sys.stderr)
        return None


# 預設截斷：~50k chars ≈ ~12k tokens，10-K 全文常超過 300k chars
# extract.py 的 context window 大約 100k tokens，但整份 10-K 品質很差（法律條文噪音多）
# 建議只抓前 50k chars（Business + MD&A 段落），需要更多時手動 --max-chars
_DEFAULT_MAX_CHARS = 50_000


def fetch_ticker(
    ticker: str,
    form_types: list[str],
    n: int,
    out_dir: Path,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> list[dict]:
    """
    主入口：抓 ticker 的最近 n 份 filing，寫入 out_dir，回傳 meta 清單。

    max_chars: 每份文件的字符截斷上限（預設 50,000 ≈ 12k tokens）。
               10-K 全文通常 200k-400k chars，全部送給 extract.py 很貴且品質差。
               設 0 或負數 = 不截斷（危險：可能噴幾十萬 tokens）。
    """
    print(f"[edgar] looking up CIK for {ticker}...")
    cik = get_cik(ticker)
    if not cik:
        print(f"[edgar] ERROR: cannot find CIK for ticker '{ticker}'", file=sys.stderr)
        return []

    print(f"[edgar] CIK={cik}, fetching {n} filings of type {form_types}...")
    filings = get_filings(cik, form_types, n)
    if not filings:
        print(f"[edgar] no matching filings found for {ticker}", file=sys.stderr)
        return []

    results = []
    for f in filings:
        print(f"[edgar] downloading {f['form_type']} filed {f['filed_date']}...")
        text = fetch_filing_text(f["cik"], f["accession"], f["primary_doc"])
        if not text:
            print(f"[edgar] WARN: empty document, skipping", file=sys.stderr)
            continue

        original_len = len(text)
        if max_chars > 0 and original_len > max_chars:
            text = text[:max_chars]
            print(
                f"[edgar] ⚠ truncated {original_len:,} → {max_chars:,} chars "
                f"(~{max_chars//4:,} tokens). 若需完整文件加 --max-chars 0（不建議）",
                file=sys.stderr,
            )

        doc_id = make_doc_id(ticker, f["form_type"], f["filed_date"])
        meta = {
            "doc_id": doc_id,
            "source_type": "filing",
            "evidence_tier": FORM_TIER.get(f["form_type"].upper(), 2),
            "company": f["company_name"],
            "ticker": ticker.upper(),
            "form_type": f["form_type"],
            "filed_date": f["filed_date"],
            "cik": f["cik"],
            "accession": f["accession"],
            "truncated": original_len > max_chars > 0,
            "original_chars": original_len,
            "url": (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(f['cik'])}/{f['accession']}/{f['primary_doc']}"
            ),
        }
        txt_path, meta_path = write_raw(doc_id, text, meta, out_dir)
        print(f"[edgar] saved {txt_path.name} ({len(text):,} chars)")
        results.append(meta)

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch SEC EDGAR filings for a ticker")
    ap.add_argument("--ticker", required=True, help="股票代號，如 SIVE 或 COHR")
    ap.add_argument(
        "--forms", default="10-K,10-Q",
        help="逗號分隔的 form 類型，預設 10-K,10-Q"
    )
    ap.add_argument("--n", type=int, default=2, help="下載最近 N 份，預設 2")
    ap.add_argument(
        "--out", default="library/raw",
        help="輸出目錄，預設 library/raw"
    )
    ap.add_argument(
        "--max-chars", type=int, default=50_000,
        help="每份文件截斷上限（chars）。預設 50000 ≈ 12k tokens。0=不截斷（危險）",
    )
    args = ap.parse_args()

    form_types = [f.strip() for f in args.forms.split(",")]
    out_dir = Path(args.out)

    results = fetch_ticker(
        ticker=args.ticker,
        form_types=form_types,
        n=args.n,
        out_dir=out_dir,
        max_chars=args.max_chars,
    )

    if results:
        print(f"\n✓ 下載完成：{len(results)} 份文件")
        for m in results:
            print(f"  {m['doc_id']}  ({m['form_type']}, filed {m['filed_date']})")
        print(f"\n下一步（新公司 onboarding）:")
        print(f"  python extract.py --input library/raw/<doc_id>.txt \\")
        print(f"    --source-type filing --evidence-tier 1 \\")
        print(f"    --title '<描述>' --out extractions/<doc_id>.json")
        return 0
    else:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
