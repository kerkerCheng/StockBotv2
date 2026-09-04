"""
mops.py — 依台股代號從公開資訊觀測站（MOPS）電子書抓年報／財報／股東會文件。

輸出格式（與 edgar.py 一致）：
    library/raw/{doc_id}.txt       — PDF 抽取後的純文字
    library/raw/{doc_id}.meta.json — doc metadata，接回 extract pipeline

台股的 source-trace 入口。AGENTS.md 指定台股走公開資訊觀測站，但實務上有四個坑，
每一個都足以讓人誤判成「這家公司抓不到資料」：

1. **公司官網通常抓不到。** 多數台廠 IR 頁面的年報 PDF 連結是動態載入，靜態抓取
   只會拿到零散的附件（實測聯亞只拿到「前十大股東關係表」）。這曾讓 pq1 判定
   「可抽文字為 0」而 park。要走 MOPS，不要走公司網站。
2. **兩段式下載。** POST `t57sb01` 帶 `step=9` 不會直接回 PDF，而是回一個 HTML，
   裡面才有帶時戳的一次性路徑（`/pdf/{filename}_{timestamp}.pdf`）；要再 GET 那個路徑。
   直接猜 `https://doc.twse.com.tw/pdf/{filename}` 一律 404。
3. **列表頁是 big5。** 不設 `encoding` 會拿到亂碼，然後以為公司不存在。
4. **`year` 是民國年，而且指「查詢年度」不是「資料年度」。** 查 `year=115` 回的是
   114 年度（2025）的股東會年報。要最新年報就查當年民國年。

用法:
    python -m fetchers.mops --co-id 3081 --list
    python -m fetchers.mops --co-id 3081 --kind annual_report
    python -m fetchers.mops --co-id 2455 --year 115 --kind annual_report --out library/raw
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

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

from fetchers.utils import rate_sleep, write_raw

MOPS_DOC_BASE = "https://doc.twse.com.tw"
MOPS_QUERY = f"{MOPS_DOC_BASE}/server-java/t57sb01"

# MOPS「資料細節說明」欄的字樣 → 我們的文件種類。
# 這是 taxonomy（MOPS 會新增說明字樣），不是 contract：要支援新種類就加一項。
DOC_KINDS: dict[str, tuple[str, ...]] = {
    "annual_report": ("股東會年報",),
    "financial_report": ("財務報告", "財務報表"),
    "meeting_minutes": ("股東會議事錄",),
    "meeting_handbook": ("議事手冊",),
    # 2026-09-04 新增：**分部附註（IFRS 8）住這一區，不在股東會年報裡。**
    # 事發：3081 的股東會年報 112 頁抽得出 281,784 字，`部門`／`IFRS 8` 命中 0 次，
    # 於是被記成「小型單一部門公司」——但那份文件**根本不含財務報表附註**
    # （`Independent Auditor` 0 次）。從一份結構上不會有分部附註的文件得出「未揭露」
    # 是 L11-5 的教科書案例。要查分部，抓的是這兩種。
    "consolidated_financial_statement": ("合併財報",),
    "separate_financial_statement": ("個別財報",),
}

#: 每種文件住 MOPS 的哪一區。`t57sb01` 的 `mtype` 不是裝飾——列檔與下載必須用同一個，
#: 否則下載端拿不到路徑而錯誤訊息會說「檔名可能有誤」（見 `fetch_document` 坑 4）。
KIND_MTYPE: dict[str, str] = {
    "annual_report": "F",
    "financial_report": "F",
    "meeting_minutes": "F",
    "meeting_handbook": "F",
    "consolidated_financial_statement": "A",
    "separate_financial_statement": "A",
}

# 年報與財報都是 issuer 一手申報文件。
KIND_TIER: dict[str, int] = {
    "annual_report": 1,
    "financial_report": 1,
    "consolidated_financial_statement": 1,
    "separate_financial_statement": 1,
    "meeting_minutes": 2,
    "meeting_handbook": 2,
}

_TAG = re.compile(r"<[^>]+>")


def _build_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "StockBotv2 research (contact: "
            f"{__import__('os').getenv('EDGAR_CONTACT_EMAIL', 'research@example.com')})"
        )
    }


def _cell_text(html: str) -> str:
    return _TAG.sub("", html).replace("&nbsp;", "").strip()


def list_documents(co_id: str, year: str, *, mtype: str = "F") -> list[dict[str, str]]:
    """列出某公司某查詢年度的 MOPS 電子書檔案。

    `year` 是**民國年**且為查詢年度：查 115 會列出 114 年度的股東會年報。
    """
    session = requests.Session()
    session.headers.update(_build_headers())
    resp = session.post(
        MOPS_QUERY,
        data={"step": "1", "colorchg": "1", "co_id": co_id, "year": year,
              "seamon": "", "mtype": mtype},
        timeout=30,
    )
    resp.encoding = "big5"  # 坑 3
    rate_sleep()

    documents: list[dict[str, str]] = []
    for row in re.findall(r"<tr>(.*?)</tr>", resp.text, re.S):
        cells = [_cell_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        filename = next((c for c in cells if c.endswith(".pdf")), None)
        if not filename:
            continue
        detail = cells[5] if len(cells) > 5 else ""
        documents.append({
            "co_id": cells[0] if cells else co_id,
            "data_year": cells[1] if len(cells) > 1 else "",
            "category": cells[2] if len(cells) > 2 else "",
            "detail": detail,
            "filename": filename,
            "size": cells[8] if len(cells) > 8 else "",
            "uploaded_at": cells[9] if len(cells) > 9 else "",
        })
    return documents


def select_documents(
    documents: list[dict[str, str]], kind: str, *, include_english: bool = False
) -> list[dict[str, str]]:
    """依文件種類挑出候選；預設排除英文版（中文版為 issuer 正本）。"""
    patterns = DOC_KINDS.get(kind)
    if patterns is None:
        raise ValueError(f"未登記的文件種類：{kind}（可用：{sorted(DOC_KINDS)}）")
    picked = []
    for doc in documents:
        detail = doc.get("detail", "")
        if not any(p in detail for p in patterns):
            continue
        if not include_english and "英文版" in detail:
            continue
        picked.append(doc)
    return picked


def fetch_document(co_id: str, filename: str, *, mtype: str = "F") -> bytes:
    """兩段式下載（坑 2）：先取一次性時戳路徑，再 GET 實際 PDF。

    ⚠ **`mtype` 必須與列檔時用的同一個**（坑 4，2026-09-04）。這個參數原本寫死
    `"F"`，於是財報區（`mtype="A"`）的檔名一律拿不到下載路徑，錯誤訊息卻說
    「檔名可能有誤，或該文件已下架」——**一個表示兩種語意**（L12）：實際上檔名是對的、
    文件也在，只是查錯了區。那句誤導訊息讓「台股分部附註抓不到」被記成資料問題，
    而它其實是 fetcher 的整合缺口。
    """
    session = requests.Session()
    session.headers.update(_build_headers())
    resp = session.post(
        MOPS_QUERY,
        data={"step": "9", "kind": mtype, "co_id": co_id, "filename": filename},
        timeout=60,
    )
    resp.encoding = "big5"
    rate_sleep()

    match = re.search(r"href='(/pdf/[^']+\.pdf)'", resp.text)
    if not match:
        raise RuntimeError(
            f"MOPS 未回傳 {filename} 的下載路徑（mtype={mtype}）——"
            "先確認 mtype 與列檔時相同（財報在 A、股東會文件在 F），"
            "再懷疑檔名有誤或文件已下架"
        )
    pdf = session.get(MOPS_DOC_BASE + match.group(1), timeout=120)
    rate_sleep()
    if not pdf.content.startswith(b"%PDF"):
        raise RuntimeError(f"{filename} 下載結果不是 PDF（取得 {len(pdf.content)} bytes）")
    return pdf.content


def pdf_to_text(content: bytes) -> tuple[str, int]:
    """抽 PDF 全文，回傳 (text, page_count)。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - 環境問題
        raise RuntimeError("需要 pypdf 套件: pip install pypdf") from exc
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text, len(reader.pages)


def _form_code(filename: str) -> str:
    """取 MOPS 檔名尾端的表單碼（F04 原始版、F11 股東會後修訂本…）。"""
    match = re.search(r"([A-Z]+\d+)\.pdf$", filename)
    return match.group(1) if match else "unknown"


def make_mops_doc_id(
    co_id: str, kind: str, filename: str, *, disambiguate: bool = False
) -> str:
    """由 MOPS 檔名生成穩定 doc_id。

    例：2455 / annual_report / 2025_2455_...F04.pdf → `mops_2455_annual_report_2025`。
    檔名首段是資料年度（西元）。

    ⚠ 同一年度可能有多份同種文件（實測 IET-KY 114 年度同時有 F04 原始版與 F11
    股東會後修訂本）。只用年度當 doc_id 會讓後抓的那份**靜默覆蓋**前一份，輸出看起來
    抓了兩份、實際只留下一份。`disambiguate=True` 時附上表單碼以保留兩份。
    """
    year = filename.split("_", 1)[0]
    year = year if year.isdigit() else "unknown"
    doc_id = f"mops_{co_id}_{kind}_{year}"
    if disambiguate:
        doc_id = f"{doc_id}_{_form_code(filename).lower()}"
    return doc_id


def _sort_key(doc: dict[str, str]) -> str:
    """MOPS 上傳時間格式為 `115/08/27 17:07:55`（民國年），字串序即時間序。"""
    return doc.get("uploaded_at", "")


def latest_only(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    """同種文件只留上傳時間最新的一份（修訂本 supersede 原始版）。"""
    return sorted(documents, key=_sort_key)[-1:] if documents else []


def fetch_company(
    co_id: str,
    *,
    year: str,
    kind: str,
    out_dir: Path,
    include_english: bool = False,
    all_revisions: bool = False,
) -> list[dict[str, object]]:
    """抓某公司某種類的文件並寫入 out_dir。回傳已寫入的 meta 清單。

    預設只取最新一份修訂；`all_revisions=True` 時全取，並以表單碼區分 doc_id。
    """
    mtype = KIND_MTYPE.get(kind, "F")
    documents = list_documents(co_id, year, mtype=mtype)
    picked = select_documents(documents, kind, include_english=include_english)
    if not picked:
        print(f"[mops] {co_id} year={year} kind={kind}（mtype={mtype}）：無符合文件",
              file=sys.stderr)
        return []

    superseded: list[dict[str, str]] = []
    if not all_revisions and len(picked) > 1:
        newest = latest_only(picked)
        superseded = [d for d in picked if d is not newest[0]]
        for doc in superseded:
            print(
                f"[mops] ⚠ 略過較舊修訂：{doc['detail']}（{doc['filename']}，"
                f"上傳 {doc['uploaded_at']}）；--all-revisions 可一併保留",
                file=sys.stderr,
            )
        picked = newest

    written: list[dict[str, object]] = []
    for doc in picked:
        filename = doc["filename"]
        content = fetch_document(co_id, filename, mtype=mtype)
        text, pages = pdf_to_text(content)
        doc_id = make_mops_doc_id(co_id, kind, filename, disambiguate=all_revisions)
        meta = {
            "doc_id": doc_id,
            "source_type": "filing",
            "evidence_tier": KIND_TIER.get(kind, 2),
            "market": "TW",
            "co_id": co_id,
            "mops_filename": filename,
            "data_year_roc": doc.get("data_year", ""),
            "detail": doc.get("detail", ""),
            "uploaded_at": doc.get("uploaded_at", ""),
            "pages": pages,
            "chars": len(text),
            "truncated": False,
            "form_code": _form_code(filename),
            "superseded_revisions": [
                {"filename": d["filename"], "detail": d["detail"],
                 "uploaded_at": d["uploaded_at"]}
                for d in superseded
            ],
            "url": f"{MOPS_QUERY}?step=9&kind={mtype}&co_id={co_id}&filename={filename}",
            "retrieval_note": (
                "MOPS 電子書為兩段式下載，url 欄為查詢入口而非直連 PDF；"
                "實際 PDF 路徑帶一次性時戳，不可長期引用"
            ),
        }
        txt_path, _ = write_raw(doc_id, text, meta, out_dir)
        print(f"[mops] {co_id} {doc.get('detail')} → {txt_path}（{pages} 頁 / {len(text):,} 字）")
        written.append(meta)
    return written


def _default_roc_year() -> str:
    from datetime import date
    return str(date.today().year - 1911)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="從公開資訊觀測站（MOPS）抓台股年報／財報"
    )
    parser.add_argument("--co-id", required=True, help="台股代號，如 3081")
    parser.add_argument(
        "--year",
        default=None,
        help="民國年（查詢年度，非資料年度）。預設今年；查 115 會列出 114 年度年報",
    )
    parser.add_argument(
        "--kind",
        default="annual_report",
        choices=sorted(DOC_KINDS),
        help="文件種類，預設 annual_report",
    )
    parser.add_argument("--list", action="store_true", help="只列出可用文件，不下載")
    parser.add_argument("--include-english", action="store_true", help="一併抓英文版")
    parser.add_argument(
        "--all-revisions",
        action="store_true",
        help="同年度有多份修訂時全部保留（doc_id 附表單碼）；預設只取最新一份",
    )
    parser.add_argument("--out", default="library/raw", help="輸出目錄")
    args = parser.parse_args()

    year = args.year or _default_roc_year()

    if args.list:
        # ⚠ `--list` 必須用與 `--kind` 相同的 mtype，否則列的是另一區的文件。
        # 舊版寫死 F，於是「列出來沒有財報」被讀成「這家公司沒申報財報」。
        mtype = KIND_MTYPE.get(args.kind, "F")
        documents = list_documents(args.co_id, year, mtype=mtype)
        if not documents:
            print(f"[mops] {args.co_id} year={year}（mtype={mtype}）：查無文件",
                  file=sys.stderr)
            return 1
        for doc in documents:
            print(f"  {doc['data_year']:>6} | {doc['detail'][:34]:36} | "
                  f"{doc['filename']} | {doc['size']:>12} | {doc['uploaded_at']}")
        return 0

    written = fetch_company(
        args.co_id,
        year=year,
        kind=args.kind,
        out_dir=Path(args.out),
        include_english=args.include_english,
        all_revisions=args.all_revisions,
    )
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
