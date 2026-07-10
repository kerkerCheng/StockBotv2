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

工作表欄位格式（第一列為標題）:
    ticker/symbol | company(可選) | bucket | shares | avg_cost | currency | notes
    COHR          | Coherent      | CORE   | 100    | 45.00    | USD      | CPO thesis

ticker 欄名可為 "ticker" 或 "symbol"（自動偵測）。
bucket 值可為中文（CORE、大盤、積桿、觀察）或英文（core、ai_theme、cash）。
其他額外欄位（broker、cash_twd、market_usd 等）會原樣保留在 dict 中。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
SHEET_NAME = os.environ.get("GSHEETS_SHEET_NAME", "Portfolio")
SERVICE_ACCOUNT_FILE = os.environ.get("GSHEETS_SERVICE_ACCOUNT_JSON", "")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

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


def _get_service():
    """Build the Google Sheets API service object."""
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
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def fetch_portfolio() -> list[dict[str, Any]]:
    """
    讀取 Google Sheets 工作表，回傳 list of dicts。
    每個 dict 包含：ticker, company, bucket, shares, avg_cost, currency, notes
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
        except ValueError:
            item["shares"] = 0.0
        try:
            item["avg_cost"] = float(item.get("avg_cost", 0) or 0)
        except ValueError:
            item["avg_cost"] = 0.0

        portfolio.append(item)

    return portfolio


def get_position(ticker: str) -> dict[str, Any] | None:
    """回傳單一 ticker 的持倉資料，找不到回傳 None。"""
    portfolio = fetch_portfolio()
    ticker = ticker.upper()
    for item in portfolio:
        if item.get("ticker") == ticker:
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
        bucket = item.get("bucket", "unknown").strip()
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

    position = None
    ticker_upper = ticker.upper()
    for item in portfolio:
        if item.get("ticker") == ticker_upper:
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
