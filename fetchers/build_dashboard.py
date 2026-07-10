"""Dashboard v4 — shares & WAC formula-driven from Portfolio (auto-updates on trade)."""
from __future__ import annotations
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path("C:/Users/Cheng/code/StockBotv2/.env"))
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    os.environ["GSHEETS_SERVICE_ACCOUNT_JSON"], scopes=SCOPES
)
svc  = build("sheets", "v4", credentials=creds)
SID  = os.environ["GSHEETS_SPREADSHEET_ID"]

meta         = svc.spreadsheets().get(spreadsheetId=SID).execute()
sheet_map    = {s["properties"]["title"]: s["properties"]["sheetId"]
                for s in meta["sheets"]}
dashboard_id = sheet_map["Dashboard"]
portfolio_id = sheet_map["Portfolio"]

# ── 讀 Portfolio（值）─────────────────────────────────────────────────────────
def read_vals(rng):
    return svc.spreadsheets().values().get(
        spreadsheetId=SID, range=rng,
        valueRenderOption="FORMATTED_VALUE").execute().get("values", [])

val_rows = read_vals("Portfolio!A:M")
headers  = [h.strip().lower() for h in val_rows[0]]
print("Headers:", headers)

def vi(name): return headers.index(name)
def colL(name): return chr(ord("A") + vi(name))

MKT_COL = colL("market_usd")   # G
BKT_COL = colL("bucket")       # B
SYM_COL = colL("symbol")       # C
print(f"market_usd → col {MKT_COL},  bucket → col {BKT_COL}")

# ── 收集各 ticker 的 metadata（bucket / currency / company）─────────────────
# Python still decides WHICH tickers appear and their display metadata.
# The actual shares + WAC will be computed live by formulas in Google Sheets.
tickers: dict[str, dict] = {}
for i, row in enumerate(val_rows[1:], start=2):
    padded = row + [""] * (len(headers) - len(row))
    sym    = padded[vi("symbol")].strip()
    bucket = padded[vi("bucket")].strip()
    if not sym or sym == "—" or bucket == "CASH":
        continue
    if sym not in tickers:
        tickers[sym] = {
            "symbol":   sym,
            "company":  padded[vi("company")],
            "bucket":   bucket,
            "currency": padded[vi("currency")],
        }

BUCKET_ORDER = {"大盤": 0, "CORE": 1, "槓桿": 2, "觀察": 3}
agg = sorted(
    tickers.values(),
    key=lambda x: (BUCKET_ORDER.get(x["bucket"], 9), x["symbol"])
)
print(f"Tickers: {len(agg)}")

# ── 公式生成 ──────────────────────────────────────────────────────────────────
PORT_SYM  = "Portfolio!$C$2:$C$100"
PORT_SHR  = "Portfolio!$D$2:$D$100"
PORT_COST = "Portfolio!$E$2:$E$100"

def shares_f(dr: int) -> str:
    """Live share count from Portfolio."""
    return f"=SUMIF({PORT_SYM},A{dr},{PORT_SHR})"

def wac_f(dr: int) -> str:
    """Live weighted average cost from Portfolio."""
    return (
        f"=IFERROR("
        f"SUMPRODUCT(({PORT_SYM}=A{dr})*{PORT_SHR}*{PORT_COST})"
        f"/D{dr},0)"
    )

def cost_usd_f(dr: int, ccy: str) -> str:
    sh, wac = f"D{dr}", f"E{dr}"
    if ccy == "USD": return f"={sh}*{wac}"
    if ccy == "TWD": return f'={sh}*{wac}/GOOGLEFINANCE("CURRENCY:USDTWD")'
    if ccy == "EUR": return f'={sh}*{wac}*GOOGLEFINANCE("CURRENCY:EURUSD")'
    if ccy == "JPY": return f'={sh}*{wac}/GOOGLEFINANCE("CURRENCY:USDJPY")'
    return f"={sh}*{wac}"

# ── 清空 Dashboard ────────────────────────────────────────────────────────────
svc.spreadsheets().values().clear(spreadsheetId=SID, range="Dashboard").execute()

# ── 組建資料 ──────────────────────────────────────────────────────────────────
batches = []
_r = [1]

def add(cells, row=None):
    r = row if row is not None else _r[0]
    batches.append({"range": f"Dashboard!A{r}", "values": [cells]})
    if row is None:
        _r[0] += 1
    return r

def skip(n=1):
    _r[0] += n

# Row 1: title
TITLE_ROW = _r[0]
add(["Portfolio Dashboard", "", "", "", "", "", "", "", "", "", "",
     '=TEXT(NOW(),"YYYY-MM-DD HH:MM")'])
skip()  # row 2 blank

# ── Summary ───────────────────────────────────────────────────────────────────
SUMMARY_HDR = _r[0]
add(["PORTFOLIO SUMMARY"])

TOTAL_MKT_ROW = _r[0]
add(["Total Market Value (USD)",
     f'=SUMIF(Portfolio!{BKT_COL}2:{BKT_COL}100,"<>CASH",Portfolio!{MKT_COL}2:{MKT_COL}100)'])

TOTAL_COST_ROW = _r[0]
add(["Total Cost Basis* (USD)", ""])

PNL_ROW = _r[0]
add(["Unrealized P&L (USD)", f"=B{TOTAL_MKT_ROW}-B{TOTAL_COST_ROW}"])

RET_ROW = _r[0]
add(["Return", f"=IF(B{TOTAL_COST_ROW}=0,\"\",B{PNL_ROW}/B{TOTAL_COST_ROW})"])
skip()

# ── Allocation ────────────────────────────────────────────────────────────────
ALLOC_HDR = _r[0]
add(["ALLOCATION BY BUCKET"])
ALLOC_COL_HDR = _r[0]
add(["Bucket", "Market USD", "% of Total"])
ALLOC_DATA_START = _r[0]
for bkt in ["大盤", "CORE", "槓桿", "觀察"]:
    br = _r[0]
    add([bkt,
         f'=SUMIF(Portfolio!{BKT_COL}2:{BKT_COL}100,"{bkt}",Portfolio!{MKT_COL}2:{MKT_COL}100)',
         f"=IF(B{TOTAL_MKT_ROW}=0,\"\",B{br}/B{TOTAL_MKT_ROW})"])
br = _r[0]
add(["CASH",
     f'=SUMIF(Portfolio!{BKT_COL}2:{BKT_COL}100,"CASH",Portfolio!{MKT_COL}2:{MKT_COL}100)',
     f"=IF(B{TOTAL_MKT_ROW}=0,\"\",B{br}/B{TOTAL_MKT_ROW})"])
ALLOC_DATA_END = _r[0] - 1
skip()

# ── Holdings ──────────────────────────────────────────────────────────────────
HOLDINGS_HDR = _r[0]
add(["Symbol", "Company", "Bucket", "Shares", "Avg Cost",
     "Ccy", "Market USD", "Cost USD*", "P&L USD", "Return %", "% Portfolio"])
HOLDINGS_DATA_START = _r[0]

for a in agg:
    dr    = _r[0]
    sym   = a["symbol"]
    mkt_f = (f'=SUMIF(Portfolio!{SYM_COL}2:{SYM_COL}100,"{sym}",'
             f'Portfolio!{MKT_COL}2:{MKT_COL}100)')
    cost_f = cost_usd_f(dr, a["currency"])
    add([
        sym,
        a["company"],
        a["bucket"],
        shares_f(dr),          # ← SUMIF from Portfolio (live)
        wac_f(dr),             # ← SUMPRODUCT from Portfolio (live)
        a["currency"],
        mkt_f,
        cost_f,
        f"=G{dr}-H{dr}",
        f"=IF(H{dr}=0,\"\",I{dr}/H{dr})",
        f"=IF($B${TOTAL_MKT_ROW}=0,\"\",G{dr}/$B${TOTAL_MKT_ROW})",
    ])

HOLDINGS_DATA_END = _r[0] - 1
skip()
add(["* 成本基礎以當前即時匯率折算 USD（非購入時匯率）",
     "⚠ DRAM/TYO:7803：GOOGLEFINANCE 無資料，市值欄可能不正確"])

# 回填 cost 加總
batches.append({
    "range": f"Dashboard!B{TOTAL_COST_ROW}",
    "values": [[f"=SUM(H{HOLDINGS_DATA_START}:H{HOLDINGS_DATA_END})"]]
})

svc.spreadsheets().values().batchUpdate(
    spreadsheetId=SID,
    body={"valueInputOption": "USER_ENTERED", "data": batches}
).execute()
print("Data written ✓")

# ── 格式化 ────────────────────────────────────────────────────────────────────
def rgb(r, g, b): return {"red": r/255, "green": g/255, "blue": b/255}

def cr(r1, c1, r2, c2):
    return {"sheetId": dashboard_id,
            "startRowIndex": r1-1, "endRowIndex": r2,
            "startColumnIndex": c1-1, "endColumnIndex": c2}

fmt = []

def rc(r1, c1, r2, c2, fields, **kw):
    fmt.append({"repeatCell": {
        "range": cr(r1, c1, r2, c2),
        "cell": {"userEnteredFormat": kw},
        "fields": "userEnteredFormat(" + fields + ")"
    }})

rc(TITLE_ROW, 1, TITLE_ROW, 12,
   "backgroundColor,textFormat",
   backgroundColor=rgb(30, 58, 95),
   textFormat={"bold": True, "fontSize": 13,
                "foregroundColor": {"red":1,"green":1,"blue":1}})

for sr in [SUMMARY_HDR, ALLOC_HDR]:
    rc(sr, 1, sr, 4,
       "backgroundColor,textFormat",
       backgroundColor=rgb(63, 81, 181),
       textFormat={"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}})

rc(ALLOC_COL_HDR, 1, ALLOC_COL_HDR, 3,
   "backgroundColor,textFormat",
   backgroundColor=rgb(197, 202, 233),
   textFormat={"bold": True})

rc(HOLDINGS_HDR, 1, HOLDINGS_HDR, 11,
   "backgroundColor,textFormat,horizontalAlignment",
   backgroundColor=rgb(55, 71, 79),
   textFormat={"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}},
   horizontalAlignment="CENTER")

for idx in range(HOLDINGS_DATA_END - HOLDINGS_DATA_START + 1):
    dr = HOLDINGS_DATA_START + idx
    bg = rgb(245, 247, 250) if idx % 2 == 0 else {"red":1,"green":1,"blue":1}
    fmt.append({"repeatCell": {
        "range": cr(dr, 1, dr, 11),
        "cell": {"userEnteredFormat": {"backgroundColor": bg}},
        "fields": "userEnteredFormat.backgroundColor"
    }})

# Number formats
rc(TOTAL_MKT_ROW, 2, TOTAL_COST_ROW, 2, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(PNL_ROW, 2, PNL_ROW, 2, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": '"+$"#,##0;"-$"#,##0'})
rc(RET_ROW, 2, RET_ROW, 2, "numberFormat",
   numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(ALLOC_DATA_START, 2, ALLOC_DATA_END, 2, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(ALLOC_DATA_START, 3, ALLOC_DATA_END, 3, "numberFormat",
   numberFormat={"type": "PERCENT", "pattern": "0.0%"})
rc(HOLDINGS_DATA_START, 7, HOLDINGS_DATA_END, 9, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": '"$"#,##0.00'})
rc(HOLDINGS_DATA_START, 10, HOLDINGS_DATA_END, 11, "numberFormat",
   numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(HOLDINGS_DATA_START, 4, HOLDINGS_DATA_END, 4, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": "#,##0"})
rc(HOLDINGS_DATA_START, 5, HOLDINGS_DATA_END, 5, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": "#,##0.0000"})

# Column widths
def cw(c1, c2, px):
    fmt.append({"updateDimensionProperties": {
        "range": {"sheetId": dashboard_id, "dimension": "COLUMNS",
                  "startIndex": c1-1, "endIndex": c2},
        "properties": {"pixelSize": px}, "fields": "pixelSize"
    }})
cw(1, 1, 110); cw(2, 2, 215); cw(3, 3, 65); cw(4, 4, 80)
cw(5, 5, 100); cw(6, 6, 45); cw(7, 8, 120); cw(9, 9, 110)
cw(10, 10, 80); cw(11, 11, 80)

# Conditional: P&L (col I = 9)
pnl_rng = [cr(HOLDINGS_DATA_START, 9, HOLDINGS_DATA_END, 9)]
fmt += [
    {"addConditionalFormatRule": {
        "rule": {"ranges": pnl_rng,
                 "booleanRule": {
                     "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                     "format": {"backgroundColor": rgb(232,245,233),
                                "textFormat": {"foregroundColor": rgb(27,136,70), "bold": True}}
                 }}, "index": 0}},
    {"addConditionalFormatRule": {
        "rule": {"ranges": pnl_rng,
                 "booleanRule": {
                     "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                     "format": {"backgroundColor": rgb(255,235,238),
                                "textFormat": {"foregroundColor": rgb(183,28,28), "bold": True}}
                 }}, "index": 1}},
]
# Conditional: Return % (col J = 10)
ret_rng = [cr(HOLDINGS_DATA_START, 10, HOLDINGS_DATA_END, 10)]
fmt += [
    {"addConditionalFormatRule": {
        "rule": {"ranges": ret_rng,
                 "booleanRule": {
                     "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                     "format": {"textFormat": {"foregroundColor": rgb(27,136,70), "bold": True}}
                 }}, "index": 2}},
    {"addConditionalFormatRule": {
        "rule": {"ranges": ret_rng,
                 "booleanRule": {
                     "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                     "format": {"textFormat": {"foregroundColor": rgb(183,28,28), "bold": True}}
                 }}, "index": 3}},
]

# ── 圓餅圖 ────────────────────────────────────────────────────────────────────
PIE_ANCHOR_ROW = HOLDINGS_DATA_END + 3
fmt.append({"addChart": {
    "chart": {
        "spec": {
            "title": "Allocation by Bucket",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "threeDimensional": False,
                "domain": {"sourceRange": {"sources": [{
                    "sheetId": dashboard_id,
                    "startRowIndex": ALLOC_DATA_START - 1, "endRowIndex": ALLOC_DATA_END,
                    "startColumnIndex": 0, "endColumnIndex": 1}]}},
                "series": {"sourceRange": {"sources": [{
                    "sheetId": dashboard_id,
                    "startRowIndex": ALLOC_DATA_START - 1, "endRowIndex": ALLOC_DATA_END,
                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
            }
        },
        "position": {
            "overlayPosition": {
                "anchorCell": {"sheetId": dashboard_id,
                               "rowIndex": PIE_ANCHOR_ROW - 1, "columnIndex": 0},
                "widthPixels": 420, "heightPixels": 280,
            }
        }
    }
}})

fmt.append({"updateSheetProperties": {
    "properties": {"sheetId": dashboard_id,
                   "gridProperties": {"frozenRowCount": 1}},
    "fields": "gridProperties.frozenRowCount"
}})

svc.spreadsheets().batchUpdate(
    spreadsheetId=SID, body={"requests": fmt}
).execute()
print(f"Done ✓  Holdings {HOLDINGS_DATA_START}–{HOLDINGS_DATA_END}, pie at row {PIE_ANCHOR_ROW}")
print()
print("Shares (D) and WAC (E) are now live formulas from Portfolio.")
print("Editing Portfolio updates Dashboard automatically — no rebuild needed.")
print()
print("Only case needing a rebuild: adding a brand-new ticker not yet in Dashboard.")
