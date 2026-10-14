"""
tw_region_revenue.py — 台股年度財報附註的「地區別資訊」：Engine C 的可重建觀測（個股頁 S3d 第二段，2026-10-14）。

**它回答的只有一件事：一家公司一年的營收，按地區分，各是多少——以及年報說它依什麼分地區。** 個股頁 B3「營收從哪來」的地區那一塊。

**來源：** MOPS 財報區（`fetchers.mops`，mtype=A）的**年度**合併財報（沒有合併就個別財報；修訂本取代原始版）PDF，
`pypdf` 抽字、NFC 正規化。IFRS 8 的全公司層級揭露（地區別）只在年度財報有——2026-10-14 試抽：12 家的年度財報 12 家都有、
第二季報 0 份有。一份年報給兩年（當年＋比較年）。

**怎麼認出營收那一欄（機械核對，L15 的補償控制）：** 版面不一（2 欄或 4 欄、收入與非流動資產交錯、`$` 在前或在後、
字與字之間有空白），所以**不靠欄位順序猜**：一塊表格裡，哪一欄的「合計」最接近那一年**月營收十二個月加總**（Engine C
`monthly_revenue_observations`；差 ≤ `TOTAL_TOLERANCE`），那一欄就是那一年的營收；各地區加起來還要等於合計。
試抽 12 家全部對得上（最大差 0.06%）。對不上、沒有月營收、兩年營收接近到同一欄對得上兩年、標籤不是地名（例：上詮在地區表
前面有一張「銷貨收入／租賃收入」的表，合計也等於營收）就**不收**，原因照寫（INV-3：不靜默丟、不猜）。

**依什麼分地區是年報自己的主張，照原文標（L11-1：措辭精度本身是 claim）：** 試抽 12 家裡 6 家寫「依客戶所在地」、
**高力（8996）寫「依營運地點區分」**——它的「美洲」是美洲據點認列的營收，不是賣給美洲客戶——另 5 家那一節沒寫。
所以不一律標成「客戶所在地」；`revenue_basis` 是封閉字彙，`basis_quotes` 是那一句原文（去掉 PDF 抽字的空白）。

**為什麼是 ETL 表不是 append-only ledger（L10）：** MOPS 年報永久可查，今天重抓拿得回來（與月營收、季報股數同類）。
一列＝一家公司的一份年報的抽取結果；同一結果重抓只更新 `fetched_at`（＝最後一次抓到這個結果），讀取端取最新的那次。

**可知日（INV-6）：** MOPS 列表的上傳時間（法定申報系統的申報時戳）；解析不到才退回法定期限（次年 3/31）。比較年那一欄也用
這份年報的可知日（往晚估）。⚠ 已知限制：抓到的是 MOPS **現在**的版本——修訂本的上傳時間較晚，往晚估不會偷看。

用法::

    python -m engine_c.tw_region_revenue --backfill            # 最近一個已過期限的年度、名冊裡全部台股
    python -m engine_c.tw_region_revenue --backfill --year 2025 --ticker 3017.TW
    python -m engine_c.tw_region_revenue --ticker 3017.TW      # 印這一檔讀到的
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

AVAILABLE_ON_BASES = ("filing_metadata", "statutory_deadline_only")
#: 抽取結果（封閉字彙）：只有 `ok` 給讀取端畫。
CHECK_STATUSES = ("ok", "no_monthly_revenue", "ambiguous_years", "total_mismatch", "not_geographic", "no_region_table",
                  "section_not_found", "document_missing")
#: 年報說收入依什麼分地區（封閉字彙）。
REVENUE_BASES = ("customer_location", "operating_location", "both_found", "unstated")
#: 營收欄的合計 vs 月營收十二個月加總的相對差上限（試抽最大 0.06%；月營收是自結數，年報是查核數）。
TOTAL_TOLERANCE = 0.003
UNIT_SCALE = 1000          # 財報附註是新台幣仟元
CURRENCY = "TWD"
SOURCE = "mops_annual_financial_report"

HEADING = re.compile(r"地\s*區\s*別\s*資\s*訊|地\s*理\s*(?:區\s*域\s*)?資\s*訊|地\s*區\s*資\s*訊")
WINDOW_CHARS = 3000
#: 認得的地名（判斷一塊表格是不是「地區」表；認不得的地名照收，只要「其他」以外的標籤一半以上認得）。
GEO_WORDS = frozenset("""台灣 臺灣 中國 中國大陸 大陸 美國 美洲 北美 北美洲 南美 南美洲 中南美洲 亞洲 亞太 亞太地區 歐洲 日本 韓國 南韓 德國
英國 法國 荷蘭 愛爾蘭 義大利 西班牙 瑞士 瑞典 以色列 泰國 新加坡 香港 越南 印度 馬來西亞 菲律賓 印尼 墨西哥 加拿大 澳洲 紐西蘭
中東 非洲 大洋洲 東南亞 美加 國內 國外 內銷 外銷""".split())
TOTAL_LABELS = frozenset({"合計", "總計", "總額", ""})
_DASHES = frozenset({"-", "－", "—", "–"})
_BASIS_PATTERNS = {"customer_location": re.compile(r"客戶所在"), "operating_location": re.compile(r"營運地點")}
#: 原文句：前後遇到句讀或數字就停（去掉空白後表格數字緊貼在句子前面，不能吃進來）。
_BASIS_QUOTE = re.compile(r"[^。；：，\d,$＄]{0,60}(?:客戶所在|營運地點)[^。；：，\d,$＄]{0,60}")


class RegionRevenueError(RuntimeError):
    pass


def annual_deadline(year: int) -> str:
    """一般業年報的法定期限：次年 3/31。"""
    return f"{year + 1}-03-31"


def latest_due_year(today: date) -> int:
    return today.year - 1 if today >= date(today.year, 3, 31) else today.year - 2


def _number(token: str) -> int | None | str:
    """一個字詞 → 整數（括號＝負）、None（破折號＝沒有）、"skip"（單獨的 $）、或 "text"（不是數字）。"""
    raw = token.strip()
    if raw in _DASHES:
        return None
    if raw in {"$", "＄"}:
        return "skip"
    negative = "(" in raw or ")" in raw
    digits = raw.replace("$", "").replace("＄", "").replace("(", "").replace(")", "")
    if not re.fullmatch(r"\d{1,3}(?:,\d{3})+|\d+", digits):
        return "text"
    value = int(digits.replace(",", ""))
    return -value if negative else value


def parse_line(line: str) -> tuple[str, list[int | None]] | None:
    """一行 → (標籤, 數字們)；至少兩個數字才算表格的一列。標籤去掉字與字之間的空白（「亞  洲」→「亞洲」）。"""
    label_parts: list[str] = []
    values: list[int | None] = []
    for token in line.split():
        parsed = _number(token)
        if parsed == "skip":
            continue
        if parsed == "text":
            if values:                      # 數字之後又出現文字：不是一列乾淨的表格
                return None
            label_parts.append(token)
            continue
        values.append(parsed)               # type: ignore[arg-type]
    return ("".join(label_parts), values) if len(values) >= 2 else None


def blocks(window: str) -> list[list[tuple[str, list[int | None]]]]:
    """視窗裡連續的表格列各成一塊：不是表格列的一行斷開，合計列（含沒有標籤的一列）收尾——
    兩張表上下緊貼（營收表接著非流動資產表）也拆得開，年份標題列（`2025 2024`）自成一塊不混進地區。"""
    out: list[list[tuple[str, list[int | None]]]] = []
    current: list[tuple[str, list[int | None]]] = []
    for line in window.splitlines():
        row = parse_line(line)
        if row is None:
            if current:
                out.append(current)
                current = []
            continue
        current.append(row)
        if row[0] in TOTAL_LABELS:
            out.append(current)
            current = []
    if current:
        out.append(current)
    return out


def _is_geo(label: str) -> bool:
    return label in GEO_WORDS or label.startswith(("亞洲", "歐洲", "美洲", "中國", "北美"))


def revenue_basis(window: str) -> tuple[str, list[str]]:
    """那一節說收入依什麼分地區 → (REVENUE_BASES 之一, 原文句)。原文去掉 PDF 抽字的空白（「營 運 地 點」→「營運地點」）。"""
    compact = re.sub(r"\s+", "", window)
    found = [basis for basis, pattern in _BASIS_PATTERNS.items() if pattern.search(compact)]
    quotes = list(dict.fromkeys(m.group(0) for m in _BASIS_QUOTE.finditer(compact)))[:2]
    if not found:
        return "unstated", []
    return (found[0] if len(found) == 1 else "both_found"), quotes


def extract_regions(text: str, expected: Mapping[int, float | None]) -> dict[str, Any]:
    """年報全文＋每一年的月營收合計（千元）→ `{status, reason, years: {年: {regions: [[地區, 千元]], total, monthly_total}},
    basis, basis_quotes}`。

    一塊表格要過四關才收：①最後一列是合計（「合計」或沒有標籤的一列）；②某一欄的合計最接近那一年月營收加總（差 ≤ 0.3%），
    而且**同一欄不能同時對得上兩年**（兩年營收接近到分不出哪欄是哪年＝不收，不猜）；③各地區加起來等於合計
    （對得上營收的欄有一欄加不起來＝整塊不收）；
    ④「其他」以外的標籤一半以上是地名。兩年都對得上就兩年都收。

    **標題出現幾次就看幾次**，取第一個過關的（2026-10-14 欣興 3037：收入附註裡先有一句「地區別資訊如下」接一張年份當列、
    地區當欄的表，部門資訊那一節的地區表在後面——只看第一個標題就整份不收）。依什麼分地區只看收下那一節。"""
    matches = list(HEADING.finditer(text))
    if not matches:
        return {"status": "section_not_found", "reason": "年報裡找不到「地區別資訊」這一節", "years": {},
                "basis": "unstated", "basis_quotes": []}
    usable = {y: t for y, t in expected.items() if t}
    if not usable:
        basis, quotes = revenue_basis(text[matches[0].start(): matches[0].start() + WINDOW_CHARS])
        return {"basis": basis, "basis_quotes": quotes, "status": "no_monthly_revenue", "years": {},
                "reason": "Engine C 沒有那兩年完整十二個月的月營收——認不出哪一欄是營收，不收"}
    misses: list[tuple[str, str]] = []
    for match in matches:
        window = text[match.start(): match.start() + WINDOW_CHARS]
        years = _window_regions(window, usable, misses)
        if years:
            basis, quotes = revenue_basis(window)
            return {"basis": basis, "basis_quotes": quotes, "status": "ok", "reason": None, "years": years}
    basis, quotes = revenue_basis(text[matches[0].start(): matches[0].start() + WINDOW_CHARS])
    out: dict[str, Any] = {"basis": basis, "basis_quotes": quotes}
    if misses:
        return {**out, "status": misses[0][0], "years": {}, "reason": "；".join(dict.fromkeys(reason for _, reason in misses))}
    return {**out, "status": "no_region_table", "years": {},
            "reason": "「地區別資訊」後面沒有一塊表格的合計等於那一年月營收加總"}


def _window_regions(window: str, usable: Mapping[int, float], misses: list[tuple[str, str]]) -> dict[int, Any] | None:
    """一個標題後面的視窗：第一塊過四關的表格 → 每一年的地區；沒有就 None（沒過的原因記進 `misses`）。"""
    for block in blocks(window):
        total_row, regions = block[-1], block[:-1]
        if total_row[0] not in TOTAL_LABELS or not regions:
            continue
        candidates: list[tuple[float, int, int]] = []
        ambiguous = False
        for col, total in enumerate(total_row[1]):
            if total is None or total <= 0:
                continue
            matched = [(abs(total - m) / m, year) for year, m in usable.items() if abs(total - m) / m <= TOTAL_TOLERANCE]
            if len(matched) > 1:
                ambiguous = True
            candidates.extend((diff, col, year) for diff, year in matched)
        if ambiguous:
            misses.append(("ambiguous_years", "兩年的月營收差不到 0.6%，同一欄對得上兩年——認不出哪一欄是哪一年，不收"))
            continue
        years: dict[int, Any] = {}
        used: set[int] = set()
        for _diff, col, year in sorted(candidates):
            if year in years or col in used:
                continue
            column = [vals[col] if col < len(vals) else None for _, vals in regions]
            total = total_row[1][col]
            if abs(sum(v or 0 for v in column) - total) > max(2, len(column)):   # 千元四捨五入，每列容 1
                # 同一塊有一欄加不起來＝這塊的列可能抽錯了（漏列、斷行），另一欄也不信：整塊不收
                misses.append(("total_mismatch", f"{year} 年那一欄合計對得上月營收，但各地區加起來不等於合計"))
                years = {}
                break
            years[year] = {"regions": [[label, value or 0] for (label, _), value in zip(regions, column)],
                           "total": total, "monthly_total": round(usable[year])}
            used.add(col)
        if not years:
            continue
        specific = [label for label, _ in regions if not label.startswith("其他")]
        if not specific or sum(1 for label in specific if _is_geo(label)) * 2 < len(specific):
            misses.append(("not_geographic", f"合計對得上營收的那一塊，標籤不是地名（{'、'.join(l for l, _ in regions[:4])}）——不收"))
            continue
        return years
    return None


# ---------------------------------------------------------------------------
# 表與寫入
# ---------------------------------------------------------------------------

def ensure_region_revenue_schema(conn) -> None:
    """非破壞性建表（SQLite；由 `engine_c.db._ensure_sqlite_schema` 呼叫）。Postgres 對等表在
    `engine_c/migrations/20261014_add_tw_region_revenue.sql`。一列＝一家公司的一份年報的抽取結果（兩年都在 `years_json`）。"""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tw_region_revenue_observations (
            observation_id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            company_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            years_json TEXT NOT NULL,
            check_status TEXT NOT NULL,
            check_reason TEXT,
            revenue_basis TEXT NOT NULL,
            basis_quotes_json TEXT NOT NULL,
            currency TEXT NOT NULL,
            unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
            source_filename TEXT,
            available_on TEXT NOT NULL,
            available_on_basis TEXT NOT NULL,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_digest TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tw_region_revenue_ticker
            ON tw_region_revenue_observations (ticker, report_year DESC, fetched_at DESC);
        """
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_row(ticker: str, report_year: int, result: Mapping[str, Any], *, filename: str | None, uploaded_on: str | None,
              fetched_at: str) -> dict[str, Any]:
    """一份年報的抽取結果 → 一列。可知日：MOPS 上傳日（解析得到才用），否則法定期限。"""
    years = {str(year): data for year, data in sorted(result.get("years", {}).items())}
    return {"ticker": ticker, "company_code": ticker.split(".")[0], "report_year": report_year,
            "years_json": json.dumps(years, ensure_ascii=False, sort_keys=True),
            "check_status": result["status"], "check_reason": result.get("reason"),
            "revenue_basis": result.get("basis") or "unstated",
            "basis_quotes_json": json.dumps(result.get("basis_quotes") or [], ensure_ascii=False),
            "currency": CURRENCY, "unit_scale": UNIT_SCALE, "source_filename": filename,
            "available_on": uploaded_on or annual_deadline(report_year),
            "available_on_basis": AVAILABLE_ON_BASES[0] if uploaded_on else AVAILABLE_ON_BASES[1],
            "source": SOURCE, "fetched_at": fetched_at}


def append_region_revenue(conn, row: Mapping[str, Any], *, commit: bool = True) -> str:
    """寫入；同一結果（digest 不含 fetched_at）只把 `fetched_at` 更新成這一次——讀取端取最新的那次，
    結果 A→B→A 時讀到的是 A 不是 B。"""
    payload = dict(row)
    for key, vocabulary in (("check_status", CHECK_STATUSES), ("revenue_basis", REVENUE_BASES),
                            ("available_on_basis", AVAILABLE_ON_BASES)):
        if payload.get(key) not in vocabulary:
            raise RegionRevenueError(f"{key} 未登記：{payload.get(key)!r}（可用：{vocabulary}）")
    digest = _digest({k: v for k, v in payload.items() if k != "fetched_at"})
    params = {"observation_id": "trr_" + digest[:32], **payload, "payload_digest": digest}
    ensure_region_revenue_schema(conn)
    columns = list(params)
    conn.execute(f"INSERT INTO tw_region_revenue_observations ({','.join(columns)}) "
                 f"VALUES ({','.join('?' for _ in columns)}) "
                 f"ON CONFLICT(payload_digest) DO UPDATE SET fetched_at = excluded.fetched_at",
                 tuple(params[c] for c in columns))
    if commit:
        conn.commit()
    return params["observation_id"]


def monthly_totals(conn, ticker: str, years: Iterable[int]) -> dict[int, float | None]:
    """那幾年月營收十二個月加總（千元）；不滿十二個月＝None（不用半年冒充一年）。同一個月有更正：最後抓到的那一列。"""
    out: dict[int, float | None] = {}
    for year in years:
        rows = conn.execute("SELECT data_month, revenue_current, unit_scale FROM monthly_revenue_observations "
                            "WHERE ticker = ? AND data_month LIKE ? ORDER BY fetched_at", (ticker, f"{year}-%")).fetchall()
        months: dict[str, float] = {}
        for month, revenue, scale in rows:
            if revenue is not None:
                months[str(month)[:7]] = float(revenue) * float(scale or 1) / UNIT_SCALE
        out[year] = sum(months.values()) if len(months) == 12 else None
    return out


def backfill(conn, report_year: int, *, tickers: Iterable[str] | None = None) -> dict[str, Any]:
    """抓這一年度的年度財報、抽地區別、寫入。回 INV-3 報表（看了幾家、收了幾家、各種沒收的原因）。"""
    from engine_c.monthly_revenue import registry_taiwan_tickers
    from fetchers.mops import fetch_document, latest_only, list_documents, pdf_to_text, roc_upload_time_to_iso_date
    from fetchers.mops import select_documents

    watched = list(tickers) if tickers is not None else registry_taiwan_tickers()
    stamp = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {"report_year": report_year, "input": len(watched), "accepted": 0, "filtered": {}, "rows": []}
    for ticker in watched:
        co_id = ticker.split(".")[0]
        filename = uploaded_on = None
        try:
            docs = [d for d in list_documents(co_id, str(report_year - 1911), mtype="A")
                    if d["filename"].startswith(f"{report_year}04")]
            pick = latest_only(select_documents(docs, "consolidated_financial_statement")
                               or select_documents(docs, "separate_financial_statement"))
            if not pick:
                result: dict[str, Any] = {"status": "document_missing", "reason": f"MOPS 財報區沒有 {report_year} 年度財報",
                                          "years": {}}
            else:
                filename, uploaded_on = pick[0]["filename"], roc_upload_time_to_iso_date(pick[0].get("uploaded_at", ""))
                text, _pages = pdf_to_text(fetch_document(co_id, filename, mtype="A"))
                result = extract_regions(text, monthly_totals(conn, ticker, (report_year, report_year - 1)))
        except Exception as exc:  # noqa: BLE001 — 一家抓不到只記那一家（不靜默、不擋其他家）
            report["filtered"].setdefault("fetch_failed", []).append(f"{ticker}：{type(exc).__name__}: {str(exc)[:120]}")
            continue
        append_region_revenue(conn, build_row(ticker, report_year, result, filename=filename, uploaded_on=uploaded_on,
                                              fetched_at=stamp))
        if result["status"] == "ok":
            report["accepted"] += 1
            report["rows"].append(f"{ticker}：{sorted(result['years'])}｜{result.get('basis')}")
        else:
            report["filtered"].setdefault(result["status"], []).append(f"{ticker}：{result['reason']}")
    return report


def region_revenue(conn, ticker: str, *, as_of: date | None = None) -> dict[str, Any] | None:
    """讀取端：as-of T 已過可知日的最新一份年報、最後一次抓到的結果。沒有任何列（不是台股、或還沒抓）＝None；
    有列但 T 時都還沒到可知日＝`not_yet_available`。表不存在＝None。"""
    try:
        rows = conn.execute(
            "SELECT report_year, years_json, check_status, check_reason, revenue_basis, basis_quotes_json, source_filename, "
            "available_on, fetched_at FROM tw_region_revenue_observations WHERE ticker = ?", (ticker,)).fetchall()
    except Exception:  # noqa: BLE001 — 表還沒建：還沒有觀測
        return None
    if not rows:
        return None
    cutoff = (as_of or date.today()).isoformat()
    known = [r for r in rows if str(r[7]) <= cutoff]
    if not known:
        return {"status": "not_yet_available", "years": {},
                "reason": f"這個時點還沒有已公告的年度財報地區別（最早 {min(str(r[7]) for r in rows)} 公告）"}
    r = max(known, key=lambda row: (row[0], str(row[8])))
    years = {int(year): data for year, data in json.loads(r[1]).items()}
    return {"report_year": r[0], "status": r[2], "reason": r[3], "years": years, "basis": r[4],
            "basis_quotes": json.loads(r[5]), "source_filename": r[6], "available_on": str(r[7])}


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="台股年度財報地區別營收（Engine C 可重建觀測）")
    parser.add_argument("--backfill", action="store_true", help="抓年度財報、抽地區別、寫入")
    parser.add_argument("--year", type=int, help="哪一年度（預設：最近一個已過 3/31 期限的年度）")
    parser.add_argument("--ticker", action="append", help="只做（或只印）這幾檔；可重複")
    args = parser.parse_args(argv)
    from engine_c.db import get_conn

    conn = get_conn()
    try:
        if args.backfill:
            year = args.year or latest_due_year(date.today())
            print(json.dumps(backfill(conn, year, tickers=args.ticker), ensure_ascii=False, indent=1))
            return 0
        for ticker in args.ticker or ():
            print(ticker, json.dumps(region_revenue(conn, ticker), ensure_ascii=False, indent=1))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
