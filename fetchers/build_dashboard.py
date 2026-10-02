"""Dashboard v5 — 從 Portfolio 分頁重建 Google Sheet 的 Dashboard 分頁（股數／均價／市值全是即時公式）。

什麼時候要跑：Portfolio **新增或移除一檔**之後（標的清單是建表時寫死的，股數與市值才是即時公式）。
怎麼跑：`python fetchers/build_dashboard.py`（讀 `.env` 的 service account；寫入 scope）。

v5（2026-10-02）改了什麼：
- **可重跑**：重建前先刪掉 Dashboard 既有的圖表與條件格式——v4 每跑一次就疊一層（實測 20 條條件格式、多張圓餅圖）。
- **分母改含現金的 NAV**：v4 的「% of Total」分母只算非現金、CASH 列又算進去，五格加起來 107%。AGENTS：`bucket=CASH` 計入 NAV 不計曝險。
- 槓桿 ETF 印**名目**與**有效曝險**兩行（倍數讀 `config/beta_policy.json`，AGENTS：兩個槓桿指標不得混用、不得寫成模糊的「名目槓桿」）。
- 現金另列原幣（USD／TWD）；持股表按 bucket 再按市值排；列數不夠自動加列。
- 這張表只呈現，不給任何建議、不排名（bucket 內按市值只是閱讀順序）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    os.environ["GSHEETS_SERVICE_ACCOUNT_JSON"], scopes=SCOPES
)
svc = build("sheets", "v4", credentials=creds)
SID = os.environ["GSHEETS_SPREADSHEET_ID"]
PORTFOLIO = os.environ.get("GSHEETS_SHEET_NAME", "Portfolio")
DASHBOARD = "Dashboard"
#: Portfolio 的資料範圍上限（列）。公式用它，不用整欄：整欄會把 Dashboard 自己的格也算進去的風險沒有，但 SUMPRODUCT 整欄很慢。
LAST_ROW = 100

meta = svc.spreadsheets().get(
    spreadsheetId=SID,
    fields="sheets(properties(sheetId,title,gridProperties),charts(chartId),conditionalFormats)").execute()
sheets = {s["properties"]["title"]: s for s in meta["sheets"]}
dashboard = sheets[DASHBOARD]
dashboard_id = dashboard["properties"]["sheetId"]


# ── 讀 Portfolio（UNFORMATTED：數字是數字、字串是字串）────────────────────────
def read_vals(rng: str) -> list[list]:
    return svc.spreadsheets().values().get(
        spreadsheetId=SID, range=rng, valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])


val_rows = read_vals(f"{PORTFOLIO}!A1:Z{LAST_ROW}")
headers = [str(h).strip().lower() for h in val_rows[0]]
print("Headers:", headers)


def vi(name: str) -> int:
    return headers.index(name)


def col_letter(name: str) -> str:
    return chr(ord("A") + vi(name))


MKT = col_letter("market_usd")
BKT = col_letter("bucket")
SYM = col_letter("symbol")
SHR = col_letter("shares")
COST = col_letter("avg_cost")
CASH_TWD = col_letter("cash_twd")
CASH_USD = col_letter("cash_usd")
print(f"market_usd→{MKT}  bucket→{BKT}  symbol→{SYM}  shares→{SHR}  avg_cost→{COST}")


def rng(col: str, absolute: bool = False) -> str:
    c = f"${col}$" if absolute else col
    return f"{PORTFOLIO}!{c}2:{c}{LAST_ROW}" if absolute else f"{PORTFOLIO}!{col}2:{col}{LAST_ROW}"


# ── 收集各 ticker 的 metadata（哪些標的出現、顯示用的 bucket／幣別／公司名）──────
# 股數、均價、市值由 Sheet 公式即時算；這裡只決定「有哪些列」。
tickers: dict[str, dict] = {}
for row in val_rows[1:]:
    padded = list(row) + [""] * (len(headers) - len(row))
    sym = str(padded[vi("symbol")]).strip()
    bucket = str(padded[vi("bucket")]).strip()
    if not sym or sym == "—" or bucket.upper() == "CASH":
        continue
    try:
        market = float(padded[vi("market_usd")] or 0)
    except (TypeError, ValueError):
        market = 0.0
    entry = tickers.setdefault(sym, {"symbol": sym, "company": str(padded[vi("company")]), "bucket": bucket,
                                     "currency": str(padded[vi("currency")]).strip().upper(), "market": 0.0})
    entry["market"] += market

BUCKET_ORDER = {"大盤": 0, "CORE": 1, "槓桿": 2, "觀察": 3}
agg = sorted(tickers.values(), key=lambda x: (BUCKET_ORDER.get(x["bucket"], 9), -x["market"], x["symbol"]))
print(f"Tickers: {len(agg)}")

# ── 槓桿 ETF 倍數（SSOT：config/beta_policy.json；只取 Sheet 上真的有的）────────
policy = json.loads((ROOT / "config" / "beta_policy.json").read_text(encoding="utf-8"))
leveraged: list[tuple[str, float]] = []
for inst in policy.get("instruments", []):
    multiple = float(inst.get("leverage_multiple") or 1.0)
    if multiple <= 1.0:
        continue
    for alias in inst.get("sheet_aliases", []):
        if alias in tickers:
            leveraged.append((alias, multiple))
print("Leveraged on sheet:", leveraged)


# ── 公式 ──────────────────────────────────────────────────────────────────────
def sumif_symbol(sym: str, col: str) -> str:
    return f'=SUMIF({rng(SYM)},"{sym}",{rng(col)})'


def shares_f(dr: int) -> str:
    return f"=SUMIF({rng(SYM, True)},A{dr},{rng(SHR, True)})"


def wac_f(dr: int) -> str:
    return f"=IFERROR(SUMPRODUCT(({rng(SYM, True)}=A{dr})*{rng(SHR, True)}*{rng(COST, True)})/D{dr},0)"


def cost_usd_f(dr: int, ccy: str) -> str:
    sh, wac = f"D{dr}", f"E{dr}"
    if ccy == "TWD":
        return f'={sh}*{wac}/GOOGLEFINANCE("CURRENCY:USDTWD")'
    if ccy == "EUR":
        return f'={sh}*{wac}*GOOGLEFINANCE("CURRENCY:EURUSD")'
    if ccy == "JPY":
        return f'={sh}*{wac}/GOOGLEFINANCE("CURRENCY:USDJPY")'
    return f"={sh}*{wac}"       # USD；其他幣別也照 USD 算並在備註點名


# ── 清掉上一版：值、條件格式、圖表（v4 沒清，會疊層）────────────────────────────
cleanup: list[dict] = []
for index in range(len(dashboard.get("conditionalFormats", [])) - 1, -1, -1):
    cleanup.append({"deleteConditionalFormatRule": {"sheetId": dashboard_id, "index": index}})
for chart in dashboard.get("charts", []):
    cleanup.append({"deleteEmbeddedObject": {"objectId": chart["chartId"]}})
svc.spreadsheets().values().clear(spreadsheetId=SID, range=DASHBOARD).execute()
if cleanup:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": cleanup}).execute()
print(f"Cleared: {len(dashboard.get('conditionalFormats', []))} conditional formats, {len(dashboard.get('charts', []))} charts")

# ── 組建資料 ──────────────────────────────────────────────────────────────────
batches: list[dict] = []
_r = [1]


def add(cells: list, row: int | None = None) -> int:
    r = row if row is not None else _r[0]
    batches.append({"range": f"{DASHBOARD}!A{r}", "values": [cells]})
    if row is None:
        _r[0] += 1
    return r


def skip(n: int = 1) -> None:
    _r[0] += n


TITLE_ROW = _r[0]
add(["Portfolio Dashboard", "", "", "", "", "", "", "", "", "", "", '=TEXT(NOW(),"YYYY-MM-DD HH:MM")'])
skip()

# ── Summary（分母＝含現金的 NAV）──────────────────────────────────────────────
SUMMARY_HDR = _r[0]
add(["PORTFOLIO SUMMARY"])
NAV_ROW = _r[0]
add(["NAV（含現金，USD）", f"=SUM({rng(MKT)})"])
INVESTED_ROW = _r[0]
add(["已投入（非現金，USD）", f'=SUMIF({rng(BKT)},"<>CASH",{rng(MKT)})'])
CASH_ROW = _r[0]
add(["現金（USD 等值）", f'=SUMIF({rng(BKT)},"CASH",{rng(MKT)})'])
TOTAL_COST_ROW = _r[0]
add(["已投入的成本*（USD）", ""])
PNL_ROW = _r[0]
add(["未實現損益（USD）", f"=B{INVESTED_ROW}-B{TOTAL_COST_ROW}"])
RET_ROW = _r[0]
add(["報酬（損益／成本）", f'=IF(B{TOTAL_COST_ROW}=0,"",B{PNL_ROW}/B{TOTAL_COST_ROW})'])
skip()

# ── Allocation（% of NAV 含現金，五格加起來 100%）───────────────────────────────
ALLOC_HDR = _r[0]
add(["ALLOCATION BY BUCKET"])
ALLOC_COL_HDR = _r[0]
add(["Bucket", "Market USD", "% of NAV（含現金）"])
ALLOC_DATA_START = _r[0]
for bkt in ["大盤", "CORE", "槓桿", "觀察", "CASH"]:
    br = _r[0]
    add([bkt, f'=SUMIF({rng(BKT)},"{bkt}",{rng(MKT)})', f'=IF(B{NAV_ROW}=0,"",B{br}/B{NAV_ROW})'])
ALLOC_DATA_END = _r[0] - 1
# 槓桿 ETF：名目（投入的錢）與有效曝險（乘倍數）分兩行，不混。
LEV_START = _r[0]
if leveraged:
    nominal = "+".join(f'SUMIF({rng(SYM)},"{sym}",{rng(MKT)})' for sym, _m in leveraged)
    effective = "+".join(f'SUMIF({rng(SYM)},"{sym}",{rng(MKT)})*{m:g}' for sym, m in leveraged)
    labels = "、".join(f"{sym} ×{m:g}" for sym, m in leveraged)
    lr = _r[0]
    add([f"槓桿 ETF 名目占 NAV（{labels}）", f"={nominal}", f'=IF(B{NAV_ROW}=0,"",B{lr}/B{NAV_ROW})'])
    lr = _r[0]
    add(["槓桿 ETF 有效曝險占 NAV（名目 × 倍數）", f"={effective}", f'=IF(B{NAV_ROW}=0,"",B{lr}/B{NAV_ROW})'])
LEV_END = _r[0] - 1
CASH_START = _r[0]
add(["現金 USD（原幣）", f'=SUMIF({rng(BKT)},"CASH",{rng(CASH_USD)})'])
add(["現金 TWD（原幣）", f'=SUMIF({rng(BKT)},"CASH",{rng(CASH_TWD)})'])
CASH_END = _r[0] - 1
skip()

# ── Holdings ──────────────────────────────────────────────────────────────────
HOLDINGS_HDR = _r[0]
add(["Symbol", "Company", "Bucket", "Shares", "Avg Cost", "Ccy", "Market USD", "Cost USD*", "P&L USD", "Return %", "% of NAV"])
HOLDINGS_DATA_START = _r[0]
for a in agg:
    dr = _r[0]
    add([
        a["symbol"], a["company"], a["bucket"],
        shares_f(dr), wac_f(dr), a["currency"],
        sumif_symbol(a["symbol"], MKT),
        cost_usd_f(dr, a["currency"]),
        f"=G{dr}-H{dr}",
        f'=IF(H{dr}=0,"",I{dr}/H{dr})',
        f'=IF($B${NAV_ROW}=0,"",G{dr}/$B${NAV_ROW})',
    ])
HOLDINGS_DATA_END = _r[0] - 1
skip()
odd = sorted(a["symbol"] for a in agg if a["currency"] not in {"USD", "TWD", "EUR", "JPY"})
NOTE_ROW = _r[0]
add(["* 成本以當前即時匯率折算 USD（非購入時匯率）；市值由 Portfolio 的 GOOGLEFINANCE 公式即時取得，抓不到價的標的在 Portfolio 的 notes 欄會註明。",
     ("⚠ 成本未換算幣別：" + "、".join(odd)) if odd else ""])
# 回填成本加總
batches.append({"range": f"{DASHBOARD}!B{TOTAL_COST_ROW}",
                "values": [[f"=SUM(H{HOLDINGS_DATA_START}:H{HOLDINGS_DATA_END})"]]})

#: 圓餅圖放在摘要右邊（E3 起，摘要與配置表只用到 A–C 欄），不用往下捲就看得到——沿用使用者原本手放的位置。
PIE_ANCHOR_ROW, PIE_ANCHOR_COL = SUMMARY_HDR, 5
NEEDED_ROWS = HOLDINGS_DATA_END + 6
current_rows = int(dashboard["properties"].get("gridProperties", {}).get("rowCount") or 0)
if current_rows < NEEDED_ROWS:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": [{"appendDimension": {
        "sheetId": dashboard_id, "dimension": "ROWS", "length": NEEDED_ROWS - current_rows}}]}).execute()
    print(f"Rows {current_rows} → {NEEDED_ROWS}")

svc.spreadsheets().values().batchUpdate(
    spreadsheetId=SID, body={"valueInputOption": "USER_ENTERED", "data": batches}).execute()
print("Data written ✓")


# ── 格式化 ────────────────────────────────────────────────────────────────────
def rgb(r: int, g: int, b: int) -> dict:
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def cr(r1: int, c1: int, r2: int, c2: int) -> dict:
    return {"sheetId": dashboard_id, "startRowIndex": r1 - 1, "endRowIndex": r2,
            "startColumnIndex": c1 - 1, "endColumnIndex": c2}


fmt: list[dict] = []


def rc(r1: int, c1: int, r2: int, c2: int, fields: str, **kw) -> None:
    fmt.append({"repeatCell": {"range": cr(r1, c1, r2, c2), "cell": {"userEnteredFormat": kw},
                               "fields": "userEnteredFormat(" + fields + ")"}})


WHITE = {"red": 1, "green": 1, "blue": 1}
# 先把整頁格式歸零（上一版的底色、數字格式不會因 clear 而消失）
fmt.append({"repeatCell": {"range": {"sheetId": dashboard_id}, "cell": {"userEnteredFormat": {}}, "fields": "userEnteredFormat"}})
rc(TITLE_ROW, 1, TITLE_ROW, 12, "backgroundColor,textFormat",
   backgroundColor=rgb(30, 58, 95), textFormat={"bold": True, "fontSize": 13, "foregroundColor": WHITE})
for sr in (SUMMARY_HDR, ALLOC_HDR):
    rc(sr, 1, sr, 4, "backgroundColor,textFormat",
       backgroundColor=rgb(63, 81, 181), textFormat={"bold": True, "foregroundColor": WHITE})
rc(ALLOC_COL_HDR, 1, ALLOC_COL_HDR, 3, "backgroundColor,textFormat",
   backgroundColor=rgb(197, 202, 233), textFormat={"bold": True})
rc(NAV_ROW, 1, NAV_ROW, 2, "textFormat", textFormat={"bold": True})
rc(HOLDINGS_HDR, 1, HOLDINGS_HDR, 11, "backgroundColor,textFormat,horizontalAlignment",
   backgroundColor=rgb(55, 71, 79), textFormat={"bold": True, "foregroundColor": WHITE}, horizontalAlignment="CENTER")
for idx in range(HOLDINGS_DATA_END - HOLDINGS_DATA_START + 1):
    dr = HOLDINGS_DATA_START + idx
    bg = rgb(245, 247, 250) if idx % 2 == 0 else WHITE
    fmt.append({"repeatCell": {"range": cr(dr, 1, dr, 11), "cell": {"userEnteredFormat": {"backgroundColor": bg}},
                               "fields": "userEnteredFormat.backgroundColor"}})
rc(NOTE_ROW, 1, NOTE_ROW, 2, "textFormat", textFormat={"italic": True, "fontSize": 9})

# 數字格式
rc(NAV_ROW, 2, TOTAL_COST_ROW, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(PNL_ROW, 2, PNL_ROW, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"+$"#,##0;"-$"#,##0'})
rc(RET_ROW, 2, RET_ROW, 2, "numberFormat", numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(ALLOC_DATA_START, 2, LEV_END if leveraged else ALLOC_DATA_END, 2, "numberFormat",
   numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(ALLOC_DATA_START, 3, LEV_END if leveraged else ALLOC_DATA_END, 3, "numberFormat",
   numberFormat={"type": "PERCENT", "pattern": "0.0%"})
rc(CASH_START, 2, CASH_END, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0"})
rc(HOLDINGS_DATA_START, 7, HOLDINGS_DATA_END, 9, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0.00'})
rc(HOLDINGS_DATA_START, 10, HOLDINGS_DATA_END, 11, "numberFormat", numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(HOLDINGS_DATA_START, 4, HOLDINGS_DATA_END, 4, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0"})
rc(HOLDINGS_DATA_START, 5, HOLDINGS_DATA_END, 5, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0.0000"})


def cw(c1: int, c2: int, px: int) -> None:
    fmt.append({"updateDimensionProperties": {
        "range": {"sheetId": dashboard_id, "dimension": "COLUMNS", "startIndex": c1 - 1, "endIndex": c2},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}})


cw(1, 1, 150); cw(2, 2, 215); cw(3, 3, 110); cw(4, 4, 80)
cw(5, 5, 100); cw(6, 6, 45); cw(7, 8, 120); cw(9, 9, 110)
cw(10, 10, 80); cw(11, 11, 80)

# 條件格式：P&L（I）與 Return %（J）正綠負紅——重建前已清掉舊規則，所以只會有這四條
pnl_rng = [cr(HOLDINGS_DATA_START, 9, HOLDINGS_DATA_END, 9)]
ret_rng = [cr(HOLDINGS_DATA_START, 10, HOLDINGS_DATA_END, 10)]
for index, (ranges, kind, style) in enumerate([
    (pnl_rng, "NUMBER_GREATER", {"backgroundColor": rgb(232, 245, 233), "textFormat": {"foregroundColor": rgb(27, 136, 70), "bold": True}}),
    (pnl_rng, "NUMBER_LESS", {"backgroundColor": rgb(255, 235, 238), "textFormat": {"foregroundColor": rgb(183, 28, 28), "bold": True}}),
    (ret_rng, "NUMBER_GREATER", {"textFormat": {"foregroundColor": rgb(27, 136, 70), "bold": True}}),
    (ret_rng, "NUMBER_LESS", {"textFormat": {"foregroundColor": rgb(183, 28, 28), "bold": True}}),
]):
    fmt.append({"addConditionalFormatRule": {"rule": {"ranges": ranges, "booleanRule": {
        "condition": {"type": kind, "values": [{"userEnteredValue": "0"}]}, "format": style}}, "index": index}})

# 圓餅圖：五個 bucket（含 CASH）占 NAV
fmt.append({"addChart": {"chart": {
    "spec": {"title": "Allocation by Bucket（% of NAV）", "pieChart": {
        "legendPosition": "RIGHT_LEGEND", "threeDimensional": False,
        "domain": {"sourceRange": {"sources": [{"sheetId": dashboard_id, "startRowIndex": ALLOC_DATA_START - 1,
                                                 "endRowIndex": ALLOC_DATA_END, "startColumnIndex": 0, "endColumnIndex": 1}]}},
        "series": {"sourceRange": {"sources": [{"sheetId": dashboard_id, "startRowIndex": ALLOC_DATA_START - 1,
                                                 "endRowIndex": ALLOC_DATA_END, "startColumnIndex": 1, "endColumnIndex": 2}]}},
    }},
    "position": {"overlayPosition": {"anchorCell": {"sheetId": dashboard_id, "rowIndex": PIE_ANCHOR_ROW - 1,
                                                    "columnIndex": PIE_ANCHOR_COL - 1},
                                     "widthPixels": 420, "heightPixels": 300}},
}}})
fmt.append({"updateSheetProperties": {"properties": {"sheetId": dashboard_id, "gridProperties": {"frozenRowCount": 1}},
                                      "fields": "gridProperties.frozenRowCount"}})

svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": fmt}).execute()
print(f"Done ✓  Summary {SUMMARY_HDR}–{RET_ROW}, allocation {ALLOC_DATA_START}–{CASH_END}, "
      f"holdings {HOLDINGS_DATA_START}–{HOLDINGS_DATA_END}, pie at E{PIE_ANCHOR_ROW}")
print("Shares／WAC／market 是對 Portfolio 的即時公式；只有新增或移除一檔時才需要重跑本腳本。")
