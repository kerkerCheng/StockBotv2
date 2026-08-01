"""
gsheets.py — 從 Google Sheets 讀取使用者投資組合資料。

使用 GCP Service Account（JSON 金鑰）或 OAuth2 存取 Google Sheets API v4。
輸出標準化的 portfolio dict，供 investment-research skill 做倉位建議用。

用法:
    python fetchers/gsheets.py                        # 印出整個 portfolio
    python fetchers/gsheets.py --ticker COHR          # 查單一標的
    python fetchers/gsheets.py --summary              # 印 bucket 匯總

Env vars（任選一種認證方式）:
    GSHEETS_SERVICE_ACCOUNT_JSON  — Service Account 金鑰 JSON 的檔案路徑
    GSHEETS_SPREADSHEET_ID        — Google Sheets 的 spreadsheet ID（URL 中段）
    GSHEETS_SHEET_NAME            — 工作表名稱，預設 "Portfolio"
    GSHEETS_CAPITAL_SHEET_NAME    — cash floor／貸款工作表，預設 "Capital Authority"

工作表欄位格式（第一列為標題）:
    ticker/symbol | company(可選) | bucket | shares | avg_cost | currency | notes
    COHR          | Coherent      | CORE   | 100    | 45.00    | USD      | CPO thesis

ticker 欄名可為 "ticker" 或 "symbol"（自動偵測）。
bucket 值可為中文（CORE、大盤、槓桿、觀察）或英文（core、index、leverage、ai_theme、cash）；
summarize_buckets() 會透過 _BUCKET_ALIASES 正規化成後者 ——「觀察」= 個股高信念持倉 = ai_theme。
其他額外欄位（broker、cash_twd、market_usd 等）會原樣保留在 dict 中。
跨掛牌 ticker（如圖裡的 SIVE.ST vs. portfolio 的 FRA:2DG）由 _TICKER_ALIASES 處理。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# 允許文件所列的 ``python fetchers/gsheets.py`` 直接入口；模組入口仍可照常使用。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from identity.execution import get_execution_aliases as _neutral_execution_aliases

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
SHEET_NAME = os.environ.get("GSHEETS_SHEET_NAME", "Portfolio")
CAPITAL_AUTHORITY_SHEET_NAME = os.environ.get(
    "GSHEETS_CAPITAL_SHEET_NAME", "Capital Authority"
)
SERVICE_ACCOUNT_FILE = os.environ.get("GSHEETS_SERVICE_ACCOUNT_JSON", "")

# 讀取用唯讀 scope；寫入另外要求 read/write，兩者分開建立 client。
# 分開的理由：日常 routine（daily brief、beta snapshot、Engine D）全部只讀，
# 不應該在流程中持有可寫 token。只有明確的人工記帳動作才走 WRITE_SCOPES。
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
WRITE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CAPITAL_AUTHORITY_HEADERS = (
    "record_id",
    "as_of",
    "capital_type",
    "currency",
    "amount",
    "limit_amount",
    "drawn_amount",
    "annual_rate_pct",
    "interest_accrual",
    "facility_term_years",
    "repayment_structure",
    "notes",
)

# Neutral registry research ticker → actual portfolio
# ticker, for names cross-listed on a different exchange than the graph uses.
# Sivers: graph tracks SIVE.ST (Stockholm), portfolio holds the Frankfurt listing.
_TICKER_ALIASES: dict[str, str] = _neutral_execution_aliases()


def get_execution_aliases() -> dict[str, str]:
    """回傳 copy，避免 consumer 改寫 Google Sheet 的 execution alias authority。"""

    return _neutral_execution_aliases()

# Portfolio bucket labels (whatever the sheet actually uses) → canonical bucket
# used for allocation math. "觀察" (watchlist / high-conviction individual picks)
# is this portfolio's alpha/thesis bucket — treated as "ai_theme" for sizing advice.
_BUCKET_ALIASES: dict[str, str] = {
    "觀察": "ai_theme", "ai_theme": "ai_theme", "watch": "ai_theme",
    "core": "core", "大盤": "index", "index": "index",
    "槓桿": "leverage", "leverage": "leverage",
    "cash": "cash",
}

# Tickers that need enrichment — company name + Neo4j node ID (if in graph)
# Exchange-prefixed tickers (FRA:, LON:, TYO:) are not self-explanatory.
_TICKER_ENRICHMENT: dict[str, dict] = {
    "FRA:2DG":    {"company": "Sivers Semiconductors AB",              "neo4j_id": "co:sivers_semiconductors"},
    "TYO:7803":   {"company": "Bushiroad Inc",                         "neo4j_id": None},
    "LON:VWRA":   {"company": "Vanguard FTSE All-World UCITS ETF (Acc)", "neo4j_id": None},
    "00981A.TW":  {"company": "主動統一台股增長 ETF (統一投信)",          "neo4j_id": None},
    "00631L.TW":  {"company": "元大台灣50正2 ETF",                      "neo4j_id": None},
    "006208.TW":  {"company": "富邦台50 ETF",                           "neo4j_id": None},
    "0050.TW":    {"company": "元大台灣50 ETF",                         "neo4j_id": None},
    "2330.TW":    {"company": "台灣積體電路製造 (TSMC)",                  "neo4j_id": None},
    "NVDA":       {"company": "NVIDIA Corporation",                    "neo4j_id": None},
    "GOOGL":      {"company": "Alphabet Inc",                          "neo4j_id": None},
    "MU":         {"company": "Micron Technology",                     "neo4j_id": None},
    "TSLA":       {"company": "Tesla Inc",                             "neo4j_id": None},
    "DRAM":       {"company": "Roundhill Memory ETF",                   "neo4j_id": None},
    "QQQ":        {"company": "Invesco QQQ Trust (Nasdaq-100)",        "neo4j_id": None},
    "SOXX":       {"company": "iShares Semiconductor ETF",             "neo4j_id": None},
    "TQQQ":       {"company": "ProShares UltraPro QQQ (3x)",           "neo4j_id": None},
}


def _get_service(*, writable: bool = False):
    """Build the Google Sheets API service object.

    `writable=True` 才要求 read/write scope。預設唯讀，確保任何忘記標註的
    呼叫端拿到的都是不能寫的 token。
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "需要 google-auth 和 google-api-python-client:\n"
            "  pip install google-auth google-auth-httplib2 google-api-python-client"
        )

    if not SERVICE_ACCOUNT_FILE:
        raise ValueError(
            "請設定 GSHEETS_SERVICE_ACCOUNT_JSON 環境變數，"
            "指向 Service Account 金鑰 JSON 檔路徑。\n"
            "參考：https://cloud.google.com/iam/docs/creating-managing-service-accounts"
        )

    if not Path(SERVICE_ACCOUNT_FILE).exists():
        raise FileNotFoundError(f"Service Account JSON 不存在: {SERVICE_ACCOUNT_FILE}")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=WRITE_SCOPES if writable else SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def _column_letter(index: int) -> str:
    """0-based 欄索引 → A1 欄字母。讀取範圍是 A:Z，超過即拒絕。"""
    if not 0 <= index < 26:
        raise ValueError(f"欄索引 {index} 超出 A:Z 範圍")
    return chr(ord("A") + index)


def locate_portfolio_cells(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """依「欄名 + 列比對條件」定位儲存格，回傳 A1 位址與目前值。

    **絕不使用欄位位置索引** —— 使用者會調整欄序（2026-08-01 實際發生過），
    位置索引會讓寫入靜默落到錯的欄。列同樣以內容比對（ticker／broker＋bucket）
    定位，不用列號。

    request 格式：``{"match": {"ticker": "QQQ"}, "column": "shares"}``
    """
    service = _get_service()
    rows = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A:Z")
        .execute()
        .get("values", [])
    )
    if not rows:
        raise ValueError("Portfolio 工作表是空的")
    headers = [h.strip().lower() for h in rows[0]]
    located: list[dict[str, Any]] = []
    for request in requests:
        column = str(request["column"]).strip().lower()
        if column not in headers:
            raise ValueError(f"找不到欄位 {column!r}；現有欄位：{headers}")
        col_index = headers.index(column)
        match = {str(k).strip().lower(): str(v) for k, v in request["match"].items()}
        hits = []
        for offset, row in enumerate(rows[1:], start=2):
            padded = row + [""] * (len(headers) - len(row))
            item = dict(zip(headers, padded))
            if all(
                str(item.get(key, "")).strip().casefold() == value.strip().casefold()
                for key, value in match.items()
            ):
                hits.append((offset, padded))
        if len(hits) != 1:
            raise ValueError(
                f"比對條件 {match} 命中 {len(hits)} 列，必須恰好 1 列才可寫入"
            )
        row_number, padded = hits[0]
        located.append(
            {
                "a1": f"{SHEET_NAME}!{_column_letter(col_index)}{row_number}",
                "column": column,
                "match": match,
                "current": padded[col_index],
            }
        )
    return located


def write_portfolio_cells(writes: list[dict[str, Any]]) -> dict[str, Any]:
    """逐格寫入，且寫入前必須通過「現值仍等於 expected」檢查。

    這道檢查是為了讓人工編輯與程式寫入安全共存：若使用者在定位與寫入之間
    改動了同一格，整批中止而不是覆蓋。**只寫指定儲存格，永不寫整列或範圍**
    ——批次覆蓋範圍會把使用者手填的欄位一併清掉。
    """
    if not writes:
        return {"status": "noop", "written": []}
    service = _get_service(writable=True)
    values = service.spreadsheets().values()
    # 先全部重讀確認，再全部寫入；任何一格不符即中止且不寫任何一格。
    for write in writes:
        current = values.get(
            spreadsheetId=SPREADSHEET_ID, range=write["a1"]
        ).execute().get("values", [[""]])
        actual = (current[0][0] if current and current[0] else "")
        if str(actual).strip() != str(write["expected"]).strip():
            raise ValueError(
                f"{write['a1']} 現值為 {actual!r}，與預期的 {write['expected']!r} 不符"
                "——可能是同時被手動編輯過。整批中止，未寫入任何儲存格。"
            )
    written = []
    for write in writes:
        values.update(
            spreadsheetId=SPREADSHEET_ID,
            range=write["a1"],
            valueInputOption="USER_ENTERED",
            body={"values": [[write["value"]]]},
        ).execute()
        written.append({"a1": write["a1"], "from": write["expected"], "to": write["value"]})
    return {"status": "written", "written": written}


def fetch_portfolio(*, strict_operational: bool = False) -> list[dict[str, Any]]:
    """
    讀取 Google Sheets 工作表，回傳 list of dicts。
    每個 dict 包含：ticker, company, bucket, shares, avg_cost, currency, notes

    strict_operational=True 時優先要求 market_value_base、nav_base、base_currency；
    舊表可完整退回 market_usd（逐列 mark-to-market），由 adapter 統一成 USD NAV。
    兩種契約都會嚴格驗證，欄位半套或格式錯誤直接失敗。
    """
    if not SPREADSHEET_ID:
        raise ValueError(
            "請設定 GSHEETS_SPREADSHEET_ID 環境變數（Google Sheets URL 中段的 ID）。"
        )

    service = _get_service()
    # Read all columns — sheet may have broker, symbol, cash_twd, market_usd, etc.
    range_name = f"{SHEET_NAME}!A:Z"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
        .execute()
    )

    rows = result.get("values", [])
    if not rows:
        return []

    # First row = headers; normalise to lowercase
    headers = [h.strip().lower() for h in rows[0]]

    operational_mode: str | None = None
    if strict_operational:
        canonical_fields = {"market_value_base", "nav_base", "base_currency"}
        present_canonical = canonical_fields.intersection(headers)
        if present_canonical == canonical_fields:
            operational_mode = "canonical"
        elif not present_canonical and "market_usd" in headers:
            operational_mode = "legacy_market_usd"
        else:
            raise ValueError(
                "Google Sheet operational holdings 欄位不完整：需完整提供 "
                "market_value_base/nav_base/base_currency，或提供 market_usd"
            )

    # Accept "symbol" as an alias for "ticker"
    ticker_col = "ticker" if "ticker" in headers else "symbol"

    portfolio = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        item = dict(zip(headers, padded))

        # Normalise ticker — works whether column is named ticker or symbol
        ticker = item.get(ticker_col, "").strip().upper()
        if not ticker:
            continue
        item["ticker"] = ticker

        # Enrich with company name and Neo4j ID where known
        enrichment = _TICKER_ENRICHMENT.get(ticker, {})
        if "company" not in item or not item.get("company"):
            item["company"] = enrichment.get("company", "")
        item["neo4j_id"] = enrichment.get("neo4j_id")

        # Type conversions
        try:
            item["shares"] = float(item.get("shares", 0) or 0)
        except (TypeError, ValueError):
            if strict_operational:
                raise ValueError("Google Sheet shares 欄位格式錯誤") from None
            item["shares"] = 0.0
        try:
            item["avg_cost"] = float(item.get("avg_cost", 0) or 0)
        except (TypeError, ValueError):
            if strict_operational:
                raise ValueError("Google Sheet avg_cost 欄位格式錯誤") from None
            item["avg_cost"] = 0.0

        if strict_operational:
            assert operational_mode is not None
            numeric_fields = (
                ("market_value_base", "nav_base")
                if operational_mode == "canonical"
                else ("market_usd",)
            )
            for field in numeric_fields:
                try:
                    item[field] = float(item.get(field, ""))
                except (TypeError, ValueError):
                    raise ValueError(f"Google Sheet {field} 欄位格式錯誤") from None
            item["currency"] = str(item.get("currency") or "").strip().upper()
            if operational_mode == "legacy_market_usd":
                item["market_value_base"] = item["market_usd"]
                item["base_currency"] = "USD"
            else:
                item["base_currency"] = str(
                    item.get("base_currency") or ""
                ).strip().upper()
            if (
                len(item["currency"]) != 3
                or len(item["base_currency"]) != 3
                or item["market_value_base"] < 0
                or (
                    operational_mode == "canonical"
                    and item["nav_base"] <= 0
                )
            ):
                raise ValueError("Google Sheet operational holdings 欄位格式錯誤")

        portfolio.append(item)

    if strict_operational and operational_mode == "legacy_market_usd":
        nav_base = sum(item["market_value_base"] for item in portfolio)
        if nav_base <= 0:
            raise ValueError("Google Sheet market_usd 合計必須大於 0")
        for item in portfolio:
            item["nav_base"] = nav_base

    return portfolio


def fetch_capital_authority() -> list[dict[str, Any]]:
    """唯讀取得 cash floor 與貸款資料；schema 不完整時拒絕猜測。"""

    if not SPREADSHEET_ID:
        raise ValueError(
            "請設定 GSHEETS_SPREADSHEET_ID 環境變數（Google Sheets URL 中段的 ID）。"
        )
    service = _get_service()
    range_name = f"{CAPITAL_AUTHORITY_SHEET_NAME}!A:L"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        raise ValueError("Capital Authority 工作表為空或不存在")
    headers = tuple(str(value).strip().lower() for value in rows[0])
    if headers != CAPITAL_AUTHORITY_HEADERS:
        raise ValueError("Capital Authority 欄位不符合 shared-cash-pool exact schema")

    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        if len(row) > len(headers):
            raise ValueError("Capital Authority 資料列超出 schema")
        padded = list(row) + [""] * (len(headers) - len(row))
        if not any(str(value).strip() for value in padded):
            continue
        record = dict(zip(headers, padded))
        if not str(record.get("record_id") or "").strip():
            raise ValueError("Capital Authority 非空資料列缺少 record_id")
        records.append(record)
    if not records:
        raise ValueError("Capital Authority 沒有 authority records")
    return records


def get_position(ticker: str) -> dict[str, Any] | None:
    """
    回傳單一 ticker 的持倉資料，找不到回傳 None。
    接受圖裡的 canonical ticker（如 SIVE.ST），會自動轉換成 portfolio 實際
    掛牌的 ticker（如 FRA:2DG）再查詢——見 _TICKER_ALIASES。
    """
    portfolio = fetch_portfolio()
    ticker = ticker.upper()
    lookup_ticker = _TICKER_ALIASES.get(ticker, ticker)
    for item in portfolio:
        if item.get("ticker") == lookup_ticker:
            return item
    return None


def summarize_buckets(portfolio: list[dict] | None = None) -> dict[str, Any]:
    """
    回傳各 bucket 的匯總（以持股成本計算）：
    {
        "buckets": {
            "ai_theme": {"count": 3, "cost_basis_usd": 15000, "tickers": ["COHR", "LITE", "SIVE.ST"]},
            "core": {...},
        },
        "total_cost_basis_usd": 50000,
        "ai_theme_utilization": 0.30,  # 佔總成本的比例
    }
    """
    if portfolio is None:
        portfolio = fetch_portfolio()

    buckets: dict[str, dict] = {}
    for item in portfolio:
        raw_bucket = item.get("bucket", "unknown").strip()
        bucket = _BUCKET_ALIASES.get(raw_bucket, _BUCKET_ALIASES.get(raw_bucket.lower(), raw_bucket))
        cost = item["shares"] * item["avg_cost"]
        if bucket not in buckets:
            buckets[bucket] = {"count": 0, "cost_basis": 0.0, "tickers": []}
        buckets[bucket]["count"] += 1
        buckets[bucket]["cost_basis"] += cost
        buckets[bucket]["tickers"].append(item["ticker"])

    total = sum(b["cost_basis"] for b in buckets.values())
    ai_theme_cost = buckets.get("ai_theme", {}).get("cost_basis", 0.0)

    return {
        "buckets": buckets,
        "total_cost_basis": total,
        "ai_theme_pct": (ai_theme_cost / total) if total > 0 else 0.0,
    }


def format_position_for_advice(ticker: str) -> str:
    """
    回傳給投資建議 skill 用的持倉摘要文字。
    若無持倉，說明當前 ai_theme bucket 使用率。
    """
    try:
        portfolio = fetch_portfolio()
    except Exception as e:
        return f"⚠ 無法讀取 Google Sheets 持倉資料：{e}\n投資建議將不包含個人倉位資訊。"

    ticker_upper = ticker.upper()
    lookup_ticker = _TICKER_ALIASES.get(ticker_upper, ticker_upper)
    position = None
    for item in portfolio:
        if item.get("ticker") == lookup_ticker:
            position = item
            break

    summary = summarize_buckets(portfolio)
    ai_pct = summary["ai_theme_pct"]
    ai_bucket = summary["buckets"].get("ai_theme", {})

    lines = ["## 持倉資料（Google Sheets）"]

    if position:
        cost_basis = position["shares"] * position["avg_cost"]
        lines.append(f"**{ticker_upper} 已持倉**")
        lines.append(f"- 股數：{position['shares']:.0f}")
        lines.append(f"- 平均成本：{position['avg_cost']:.2f} {position.get('currency', 'USD')}")
        lines.append(f"- 成本基礎：{cost_basis:,.0f} {position.get('currency', 'USD')}")
        lines.append(f"- Bucket：{position.get('bucket', 'unknown')}")
        if position.get("notes"):
            lines.append(f"- 備註：{position['notes']}")
    else:
        lines.append(f"**{ticker_upper} 尚未持倉**")

    lines.append(f"\nAI 主題 bucket 使用率：{ai_pct:.0%}（{ai_bucket.get('count', 0)} 檔，"
                 f"成本基礎 {ai_bucket.get('cost_basis', 0):,.0f}）")
    lines.append(f"目前 ai_theme 持倉：{', '.join(ai_bucket.get('tickers', [])) or '(無)'}")

    return "\n".join(lines)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Google Sheets Portfolio Reader")
    ap.add_argument("--ticker", help="查詢單一 ticker 持倉")
    ap.add_argument("--summary", action="store_true", help="印 bucket 匯總")
    args = ap.parse_args()

    try:
        if args.ticker:
            pos = get_position(args.ticker)
            if pos:
                print(json.dumps(pos, ensure_ascii=False, indent=2))
            else:
                print(f"找不到 {args.ticker.upper()} 的持倉記錄")
        elif args.summary:
            s = summarize_buckets()
            print(json.dumps(s, ensure_ascii=False, indent=2))
        else:
            portfolio = fetch_portfolio()
            print(json.dumps(portfolio, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
