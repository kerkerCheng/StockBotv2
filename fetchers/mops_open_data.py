"""
mops_open_data.py — 公開資訊觀測站（MOPS）的**結構化開放資料**：每月營收與重大訊息。

與 `fetchers/mops.py` 的分工（兩者都叫 MOPS，但拿的東西不同）：

- `mops.py` 抓**電子書 PDF**（年報／財報／議事錄），輸出 `library/raw/*.txt` 接 extract
  pipeline，最後走 RA 入圖。
- **本檔**抓的是**已經結構化的數字與公告**，不經 LLM 抽取：月營收是帶時戳的財務觀測，
  依 A1「圖不含時變數字」直接進 Engine C；重訊是 Engine B 的 lead 原料。

三個來源（全部於 2026-09-17 實測過，不是照文件抄的）：

1. 當期月營收（上市）`https://openapi.twse.com.tw/v1/opendata/t187ap05_L`
2. 當期月營收（上櫃）`https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O`
3. 歷史月營收        `https://mopsov.twse.com.tw/nas/t21/{sii|otc}/t21sc03_{roc_year}_{month}_0.html`
4. 當日重大訊息      `.../t187ap04_L`（上市）與 `.../mopsfin_t187ap04_O`（上櫃）

**五個坑，每一個都實測撞過：**

1. **兩個交易所的 JSON 欄位名不一樣。** 上市用中文鍵（`公司代號`、`主旨 `——注意
   `主旨 ` 尾端那個空格是官方欄名的一部分，不是筆誤），上櫃用英文鍵
   （`SecuritiesCompanyCode`、`CompanyName`、`Date`）。只照一份鍵名寫死，另一邊會
   **靜默回空集合**——而空集合與「今天真的沒有重訊」同形（L13-2）。
2. **兩個 opendata endpoint 都只有「當期」**：月營收是最新一個月、重訊是最近一兩天。
   要**序列**只能走來源 3（一個年月一個 HTML 檔）。
3. **歷史頁是 big5（cp950），且上市版比上櫃版多一個前置欄位。** 欄位不能按位置數，
   要先找到「4 位數字代號」那一格再往後對齊。
4. **單位是新台幣千元，不是元。** 差 1000 倍。本檔一律原樣回傳千元，並由呼叫端把
   `unit_scale=1000` 寫進 authority——不在這裡先乘開，避免精度與語意各丟一次。
5. **`出表日期` 是 MOPS 產表的日期，不是公司的公告日。** 依 `AGENTS.md`（不得用
   ingest／retrieval 日期冒充 `published_at`）本檔把它命名為 `report_date`，
   **絕不寫進 `published_at`**。真正的公告日這三個來源都沒有，留 null；
   可機械推導的只有法定公告期限（次月 10 日，見 `disclosure_deadline`）。

用法::

    python -m fetchers.mops_open_data --revenue --market tpex
    python -m fetchers.mops_open_data --revenue --market tpex --year 2026 --month 7
    python -m fetchers.mops_open_data --announcements
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import requests
except ImportError:  # pragma: no cover - 環境問題，非邏輯
    print("需要 requests 套件: pip install requests", file=sys.stderr)
    sys.exit(1)

from fetchers.utils import build_headers, rate_sleep

#: 兩個市場的封閉字彙。`.TW` → 上市（sii）、`.TWO` → 上櫃（otc）。
#: 這不是 taxonomy——台灣只有這兩個板，新增第三個要先有一個真的板。
MARKETS: tuple[str, ...] = ("twse", "tpex")

_SUFFIX_MARKET: dict[str, str] = {".TW": "twse", ".TWO": "tpex"}
_MARKET_SUFFIX: dict[str, str] = {"twse": ".TW", "tpex": ".TWO"}
_MARKET_SEGMENT: dict[str, str] = {"twse": "sii", "tpex": "otc"}

REVENUE_CURRENT_URL: dict[str, str] = {
    "twse": "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
    "tpex": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
}
ANNOUNCEMENT_URL: dict[str, str] = {
    "twse": "https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
    "tpex": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O",
}
REVENUE_HISTORY_URL = "https://mopsov.twse.com.tw/nas/t21/{segment}/t21sc03_{year}_{month}_{kind}.html"

#: 歷史頁末尾那個數字是**註冊地**，不是流水號：`0` 本國企業、`1` 外國企業（KY 股）。
#: 事發（2026-09-17）：只抓 `_0` 時 4971.TWO（IET-KY）在 24 個月回補裡一筆都沒有，
#: 而當期 API 有它——**同一家公司在兩個來源一個有一個沒有**，正是 L17「機制只認得
#: 我當初那個案例」的形狀。兩份都抓，合併後由呼叫端過濾。
REVENUE_HISTORY_KINDS: tuple[str, ...] = ("0", "1")

_CODE = re.compile(r"^\d{4,6}$")
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


class MopsOpenDataError(RuntimeError):
    """來源拿不到或回傳的形狀不是我們認得的。**不靜默回空集合。**"""


# ---------------------------------------------------------------------------
# identity / 單位 / 日期
# ---------------------------------------------------------------------------

def market_for_ticker(ticker: str) -> str | None:
    """`3081.TWO` → `tpex`。認不出來回 None，**不猜**（INV-1）。"""

    symbol = str(ticker or "").strip().upper()
    for suffix, market in _SUFFIX_MARKET.items():
        if symbol.endswith(suffix):
            return market
    return None


def company_code(ticker: str) -> str | None:
    """`3081.TWO` → `3081`。"""

    symbol = str(ticker or "").strip().upper()
    for suffix in _SUFFIX_MARKET:
        if symbol.endswith(suffix):
            code = symbol[: -len(suffix)].strip()
            return code if _CODE.fullmatch(code) else None
    return None


def ticker_for(market: str, code: str) -> str | None:
    """`tpex` + `3081` → `3081.TWO`。市場不認得就回 None。"""

    suffix = _MARKET_SUFFIX.get(str(market or "").strip().lower())
    cleaned = str(code or "").strip()
    if suffix is None or not _CODE.fullmatch(cleaned):
        return None
    return f"{cleaned}{suffix}"


def roc_date_to_iso(value: Any) -> str | None:
    """民國日期 `1150917` → `2026-09-17`。長度或內容不對一律 None。"""

    text = str(value or "").strip()
    if not text.isdigit() or len(text) not in (6, 7):
        return None
    year = int(text[:-4]) + 1911
    month = int(text[-4:-2])
    day = int(text[-2:])
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def roc_month_to_iso(value: Any) -> str | None:
    """民國年月 `11508` → `2026-08`。"""

    text = str(value or "").strip()
    if not text.isdigit() or len(text) not in (5, 6):
        return None
    year = int(text[:-2]) + 1911
    month = int(text[-2:])
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def _text(value: Any) -> str:
    """去 tag、去 &nbsp;、NFC 正規化（`mops.py` 坑 5：相容表意文字害逐字比對失敗）。"""

    raw = _TAG.sub("", str(value or ""))
    raw = raw.replace("&nbsp;", " ").replace("\xa0", " ")
    return unicodedata.normalize("NFC", raw).strip()


def _int(value: Any) -> int | None:
    """`"  520,469 "` → `520469`；`-`／空字串 → None（缺料不是 0）。"""

    text = _text(value).replace(",", "")
    if not text or text in {"-", "--"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _float(value: Any) -> float | None:
    text = _text(value).replace(",", "").replace("%", "")
    if not text or text in {"-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first(row: Mapping[str, Any], *keys: str) -> Any:
    """兩個交易所的鍵名不同（坑 1），逐個試；`主旨 ` 的尾空格也在候選裡。"""

    for key in keys:
        if key in row:
            return row[key]
    return None


# ---------------------------------------------------------------------------
# 抓取
# ---------------------------------------------------------------------------

def _get(url: str, *, timeout: int = 40) -> requests.Response:
    try:
        response = requests.get(url, headers=build_headers(), timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - 網路
        raise MopsOpenDataError(f"{url} 取得失敗：{type(exc).__name__}: {exc}") from exc
    if response.status_code != 200:
        raise MopsOpenDataError(f"{url} 回應 {response.status_code}")
    # backfill 會連打幾十個歷史頁；對公開站台維持與其他抓取器一致的節流。
    rate_sleep(0.5)
    return response


def _validate_market(market: str) -> str:
    cleaned = str(market or "").strip().lower()
    if cleaned not in MARKETS:
        raise MopsOpenDataError(f"未知市場：{market}（只有 {'／'.join(MARKETS)}）")
    return cleaned


def _revenue_row(
    row: Mapping[str, Any],
    *,
    market: str,
    source_url: str,
    fallback_month: str | None = None,
    report_date: str | None = None,
) -> dict[str, Any] | None:
    code = _text(_first(row, "公司代號", "SecuritiesCompanyCode", "Code"))
    if not _CODE.fullmatch(code):
        return None
    data_month = roc_month_to_iso(_first(row, "資料年月", "YearMonth")) or fallback_month
    if not data_month:
        return None
    stamped = report_date or roc_date_to_iso(_first(row, "出表日期", "Date"))
    return {
        "market": market,
        "company_code": code,
        "ticker": ticker_for(market, code),
        "company_name": _text(_first(row, "公司名稱", "CompanyName")),
        "data_month": data_month,
        "revenue_current": _int(_first(row, "營業收入-當月營收", "RevenueOfCurrentMonth")),
        "revenue_prev_month": _int(_first(row, "營業收入-上月營收", "RevenueOfLastMonth")),
        "revenue_year_ago": _int(
            _first(row, "營業收入-去年當月營收", "RevenueOfLastYearMonth")),
        "change_mom_pct": _float(
            _first(row, "營業收入-上月比較增減(%)", "ComparedRateOfLastMonth")),
        "change_yoy_pct": _float(
            _first(row, "營業收入-去年同月增減(%)", "ComparedRateOfLastYearMonth")),
        "cumulative_current": _int(
            _first(row, "累計營業收入-當月累計營收", "AccumulatedRevenueOfCurrentMonth")),
        "cumulative_year_ago": _int(
            _first(row, "累計營業收入-去年累計營收", "AccumulatedRevenueOfLastYearMonth")),
        "change_cumulative_pct": _float(
            _first(row, "累計營業收入-前期比較增減(%)", "ComparedRateOfAccumulatedRevenue")),
        "note": _text(_first(row, "備註", "Remark")) or None,
        "report_date": stamped,
        "source_url": source_url,
    }


def fetch_monthly_revenue_current(market: str) -> list[dict[str, Any]]:
    """當期（最新一個月）全市場月營收。**只有一期**，序列要走 `fetch_monthly_revenue_month`。"""

    market = _validate_market(market)
    url = REVENUE_CURRENT_URL[market]
    payload = _get(url).json()
    if not isinstance(payload, list):
        raise MopsOpenDataError(f"{url} 回傳的不是陣列")
    rows = [_revenue_row(item, market=market, source_url=url)
            for item in payload if isinstance(item, Mapping)]
    return [row for row in rows if row is not None]


def fetch_monthly_revenue_month(market: str, year: int, month: int) -> list[dict[str, Any]]:
    """歷史月營收（一個年月一份 HTML）。這是**唯一**能建序列的來源（坑 2）。"""

    market = _validate_market(market)
    if not 1 <= int(month) <= 12:
        raise MopsOpenDataError(f"月份不合法：{month}")
    roc_year = int(year) - 1911
    if roc_year <= 0:
        raise MopsOpenDataError(f"年份不合法：{year}")
    data_month = f"{int(year):04d}-{int(month):02d}"
    out: list[dict[str, Any]] = []
    failures: list[str] = []
    for kind in REVENUE_HISTORY_KINDS:
        url = REVENUE_HISTORY_URL.format(
            segment=_MARKET_SEGMENT[market], year=roc_year, month=int(month), kind=kind)
        try:
            body = _get(url).content.decode("cp950", errors="replace")
        except MopsOpenDataError as exc:
            failures.append(str(exc))
            continue
        for raw_row in _ROW.findall(body):
            cells = [_text(cell) for cell in _CELL.findall(raw_row)]
            # 坑 3：上市版多一個前置欄位，所以先找代號那一格再往後對齊，不按位置數。
            index = next((i for i, cell in enumerate(cells) if _CODE.fullmatch(cell)), None)
            if index is None or len(cells) - index < 10:
                continue
            window = cells[index:index + 11]
            out.append({
                "market": market,
                "company_code": window[0],
                "ticker": ticker_for(market, window[0]),
                "company_name": window[1],
                "data_month": data_month,
                "revenue_current": _int(window[2]),
                "revenue_prev_month": _int(window[3]),
                "revenue_year_ago": _int(window[4]),
                "change_mom_pct": _float(window[5]),
                "change_yoy_pct": _float(window[6]),
                "cumulative_current": _int(window[7]),
                "cumulative_year_ago": _int(window[8]),
                "change_cumulative_pct": _float(window[9]),
                "note": (window[10] if len(window) > 10 and window[10] not in {"-", ""} else None),
                # 歷史頁沒有出表日期欄位——**留 null，不拿抓取日期頂替**（坑 5）。
                "report_date": None,
                "source_url": url,
            })
    if not out:
        detail = "；".join(failures) or "版型可能變了"
        raise MopsOpenDataError(
            f"{market} {data_month} 兩份歷史頁都解析不到任何公司列（{detail}）")
    return out


def _announcement_row(
    row: Mapping[str, Any], *, market: str, source_url: str,
) -> dict[str, Any] | None:
    code = _text(_first(row, "公司代號", "SecuritiesCompanyCode", "Code"))
    if not _CODE.fullmatch(code):
        return None
    spoke_date = roc_date_to_iso(_first(row, "發言日期", "SpokenDate"))
    raw_time = _text(_first(row, "發言時間", "SpokenTime"))
    spoke_time = None
    if raw_time.isdigit() and len(raw_time) <= 6:
        padded = raw_time.zfill(6)
        hour, minute, second = padded[:2], padded[2:4], padded[4:]
        if int(hour) < 24 and int(minute) < 60 and int(second) < 60:
            spoke_time = f"{hour}:{minute}:{second}"
    return {
        "market": market,
        "company_code": code,
        "ticker": ticker_for(market, code),
        "company_name": _text(_first(row, "公司名稱", "CompanyName")),
        # 坑 1：上市的欄名是 `主旨 `（尾端有一個空格），上櫃是 `主旨`。
        "subject": _text(_first(row, "主旨 ", "主旨", "Subject")),
        "clause": _text(_first(row, "符合條款", "Clause")) or None,
        "fact_date": roc_date_to_iso(_first(row, "事實發生日", "FactDate")),
        "spoke_date": spoke_date,
        "spoke_time": spoke_time,
        "detail": _text(_first(row, "說明", "Description")) or None,
        "report_date": roc_date_to_iso(_first(row, "出表日期", "Date")),
        "source_url": source_url,
    }


def fetch_material_announcements(market: str) -> list[dict[str, Any]]:
    """當日重大訊息。**只有當天那一批**——漏抓一天就真的漏了（坑 2）。"""

    market = _validate_market(market)
    url = ANNOUNCEMENT_URL[market]
    payload = _get(url).json()
    if not isinstance(payload, list):
        raise MopsOpenDataError(f"{url} 回傳的不是陣列")
    rows = [_announcement_row(item, market=market, source_url=url)
            for item in payload if isinstance(item, Mapping)]
    return [row for row in rows if row is not None]


def select_tickers(
    rows: Iterable[Mapping[str, Any]], tickers: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """在全市場列中挑出我們追蹤的標的，並回報 INV-3 的四個計數。

    回傳 `(accepted, report)`，`report` 含 `input`／`accepted`／`filtered`／
    `filtered_not_watched`／`filtered_unresolved_ticker`——**「沒有你的公司」與
    「代號解析不出來」是兩件事**，壓成一個數字就看不出來源版型變了。
    """

    watched = {str(t or "").strip().upper() for t in tickers if str(t or "").strip()}
    accepted: list[dict[str, Any]] = []
    unresolved = 0
    not_watched = 0
    total = 0
    for row in rows:
        total += 1
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            unresolved += 1
            continue
        if ticker not in watched:
            not_watched += 1
            continue
        accepted.append(dict(row))
    return accepted, {
        "input": total,
        "accepted": len(accepted),
        "filtered": total - len(accepted),
        "filtered_not_watched": not_watched,
        "filtered_unresolved_ticker": unresolved,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MOPS 開放資料：月營收與重大訊息")
    parser.add_argument("--revenue", action="store_true", help="抓月營收")
    parser.add_argument("--announcements", action="store_true", help="抓當日重大訊息")
    parser.add_argument("--market", choices=MARKETS, help="不給就兩個市場都抓")
    parser.add_argument("--year", type=int, help="歷史月營收的西元年（要配 --month）")
    parser.add_argument("--month", type=int, help="歷史月營收的月份")
    parser.add_argument("--ticker", action="append", default=[], help="只印這些標的（可重複）")
    args = parser.parse_args(argv)

    if not args.revenue and not args.announcements:
        parser.error("至少要有 --revenue 或 --announcements")
    markets = [args.market] if args.market else list(MARKETS)
    out: dict[str, Any] = {}
    for market in markets:
        if args.revenue:
            if args.year and args.month:
                rows = fetch_monthly_revenue_month(market, args.year, args.month)
            elif args.year or args.month:
                parser.error("--year 與 --month 必須同時給")
            else:
                rows = fetch_monthly_revenue_current(market)
            if args.ticker:
                rows, report = select_tickers(rows, args.ticker)
                print(f"[{market}] revenue filter {report}", file=sys.stderr)
            out.setdefault("revenue", {})[market] = rows
        if args.announcements:
            rows = fetch_material_announcements(market)
            if args.ticker:
                rows, report = select_tickers(rows, args.ticker)
                print(f"[{market}] announcement filter {report}", file=sys.stderr)
            out.setdefault("announcements", {})[market] = rows
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
