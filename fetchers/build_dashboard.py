"""Dashboard v6 — 從 Portfolio 分頁重建 Google Sheet 的 Dashboard 分頁；持股表由公式自己列出標的。

什麼時候要跑：**版面或公式要改**的時候。Portfolio 新增／移除一檔**不用跑**——v6 起持股表的標的清單是
`UNIQUE(FILTER(Portfolio!symbol…))` 動態列出來的，股數／均價／市值／成本／損益全是 ARRAYFORMULA，容量 57 檔。
怎麼跑：`python fetchers/build_dashboard.py`（讀 `.env` 的 service account；寫入 scope；互動專用）。

v5（2026-10-02）：可重跑（重建前刪舊條件格式與圖表——v4 每跑一次疊一層）；分母改含現金的 NAV（v4 的「% of Total」
五格加起來 107%；AGENTS：`bucket=CASH` 計入 NAV 不計曝險）；槓桿 ETF 印名目與有效曝險兩行（倍數讀 `config/beta_policy.json`，
AGENTS：兩個槓桿指標不得混用）；現金另列原幣；持股按 bucket 再按市值。
v6（2026-10-02）：持股表改動態（隱藏的 M:O 是輔助欄：不排序的標的清單、bucket 順序鍵、市值）；槓桿 ETF 列舉 beta_policy
裡全部倍數 > 1 的代號（Sheet 上沒有的算 0），日後買進也自動算進去。
這張表只呈現，不給任何建議、不排名（bucket 內按市值只是閱讀順序）。
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
#: Portfolio 的資料範圍上限（列）。公式用它、不用整欄（整欄的 SUMPRODUCT／MMULT 很慢）。
LAST_ROW = 100
#: 持股表容量（列數）。超過要改這裡重跑。
HOLDINGS_CAPACITY = 57
#: bucket 的閱讀順序；不在表上的排最後。
BUCKET_ORDER = ["大盤", "CORE", "槓桿", "觀察"]

meta = svc.spreadsheets().get(
    spreadsheetId=SID,
    fields="sheets(properties(sheetId,title,gridProperties),charts(chartId),conditionalFormats)").execute()
sheets = {s["properties"]["title"]: s for s in meta["sheets"]}
dashboard = sheets[DASHBOARD]
dashboard_id = dashboard["properties"]["sheetId"]
grid = dashboard["properties"].get("gridProperties", {})

# ── 讀 Portfolio 標題列（只為了把欄名換成欄字母——使用者調欄序不會寫錯欄）────────
header_row = svc.spreadsheets().values().get(
    spreadsheetId=SID, range=f"{PORTFOLIO}!A1:Z1").execute().get("values", [[]])[0]
headers = [str(h).strip().lower() for h in header_row]
print("Headers:", headers)


def col_letter(name: str) -> str:
    return chr(ord("A") + headers.index(name))


MKT, BKT, SYM = col_letter("market_usd"), col_letter("bucket"), col_letter("symbol")
SHR, COST, CUR, COMPANY = col_letter("shares"), col_letter("avg_cost"), col_letter("currency"), col_letter("company")
CASH_TWD, CASH_USD = col_letter("cash_twd"), col_letter("cash_usd")
print(f"market_usd→{MKT}  bucket→{BKT}  symbol→{SYM}  shares→{SHR}  avg_cost→{COST}  currency→{CUR}  company→{COMPANY}")


def rng(col: str) -> str:
    return f"{PORTFOLIO}!{col}2:{col}{LAST_ROW}"


# ── 槓桿 ETF 倍數（SSOT：config/beta_policy.json；全部列舉，Sheet 上沒有的算 0）──────
policy = json.loads((ROOT / "config" / "beta_policy.json").read_text(encoding="utf-8"))
leveraged: list[tuple[str, float]] = []          # (Sheet 別名, 倍數)——公式逐別名加總
leveraged_labels: list[str] = []                 # 標籤每個標的只印一次（別名不重複列）
for inst in policy.get("instruments", []):
    multiple = float(inst.get("leverage_multiple") or 1.0)
    if multiple > 1.0:
        leveraged_labels.append(f"{inst.get('ticker')} ×{multiple:g}")
        for alias in inst.get("sheet_aliases", []):
            leveraged.append((alias, multiple))
print("Leveraged aliases (beta_policy):", leveraged)

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


def add(cells: list, row: int | None = None, col: str = "A") -> int:
    r = row if row is not None else _r[0]
    batches.append({"range": f"{DASHBOARD}!{col}{r}", "values": [cells]})
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
add(["已投入的成本*（USD）", ""])          # 回填（要知道持股表的範圍）
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
for bkt in [*BUCKET_ORDER, "CASH"]:
    br = _r[0]
    add([bkt, f'=SUMIF({rng(BKT)},"{bkt}",{rng(MKT)})', f'=IF(B{NAV_ROW}=0,"",B{br}/B{NAV_ROW})'])
ALLOC_DATA_END = _r[0] - 1
LEV_END = ALLOC_DATA_END
if leveraged:
    nominal = "+".join(f'SUMIF({rng(SYM)},"{sym}",{rng(MKT)})' for sym, _m in leveraged)
    effective = "+".join(f'SUMIF({rng(SYM)},"{sym}",{rng(MKT)})*{m:g}' for sym, m in leveraged)
    labels = "、".join(leveraged_labels)
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

# ── Holdings（動態：標的清單與每一欄都是 ARRAYFORMULA；M:O 是隱藏的輔助欄）───────
HOLDINGS_HDR = _r[0]
add(["Symbol", "Company", "Bucket", "Shares", "Avg Cost", "Ccy", "Market USD", "Cost USD*", "P&L USD", "Return %", "% of NAV"])
S = _r[0]                              # 第一列資料
E = S + HOLDINGS_CAPACITY - 1          # 容量的最後一列
A, F = f"A{S}:A{E}", f"F{S}:F{E}"
M, N_, O = f"M{S}:M{E}", f"N{S}:N{E}", f"O{S}:O{E}"
order_list = ";".join(f'"{b}"' for b in BUCKET_ORDER)
# 輔助欄：M＝不排序的標的清單（非現金、非空、非「—」）；N＝bucket 順序鍵；O＝市值（排序用）
add([f'=IFERROR(UNIQUE(FILTER({rng(SYM)},{rng(BKT)}<>"CASH",{rng(SYM)}<>"",{rng(SYM)}<>"—")),"")'], row=S, col="M")
add([f'=ARRAYFORMULA(IF({M}="","",IFERROR(MATCH(VLOOKUP({M},{{{rng(SYM)},{rng(BKT)}}},2,FALSE),{{{order_list}}},0),9)))'],
    row=S, col="N")
add([f'=ARRAYFORMULA(IF({M}="","",SUMIF({rng(SYM)},{M},{rng(MKT)})))'], row=S, col="O")
# 主表：A 依 bucket 順序、再依市值由大到小
add([f'=IFERROR(SORT(FILTER({M},{M}<>""),FILTER({N_},{M}<>""),TRUE,FILTER({O},{M}<>""),FALSE),"")'], row=S, col="A")
add([f'=ARRAYFORMULA(IF({A}="","",IFERROR(VLOOKUP({A},{{{rng(SYM)},{rng(COMPANY)}}},2,FALSE),"")))'], row=S, col="B")
add([f'=ARRAYFORMULA(IF({A}="","",IFERROR(VLOOKUP({A},{{{rng(SYM)},{rng(BKT)}}},2,FALSE),"")))'], row=S, col="C")
add([f'=ARRAYFORMULA(IF({A}="","",SUMIF({rng(SYM)},{A},{rng(SHR)})))'], row=S, col="D")
# 加權平均成本＝Σ(股數×成本)／Σ股數；Σ(股數×成本) 用 MMULT 對每個標的一次算完（SUMPRODUCT 不能逐列展開）
weighted = (f"MMULT(({A}=TRANSPOSE({rng(SYM)}))*1,"
            f"IF(ISNUMBER({rng(SHR)}),{rng(SHR)},0)*IF(ISNUMBER({rng(COST)}),{rng(COST)},0))")
add([f'=ARRAYFORMULA(IF({A}="","",IFERROR({weighted}/D{S}:D{E},0)))'], row=S, col="E")
add([f'=ARRAYFORMULA(IF({A}="","",IFERROR(VLOOKUP({A},{{{rng(SYM)},{rng(CUR)}}},2,FALSE),"")))'], row=S, col="F")
add([f'=ARRAYFORMULA(IF({A}="","",SUMIF({rng(SYM)},{A},{rng(MKT)})))'], row=S, col="G")
fx = (f'IF({F}="USD",1,IF({F}="TWD",1/GOOGLEFINANCE("CURRENCY:USDTWD"),'
      f'IF({F}="EUR",GOOGLEFINANCE("CURRENCY:EURUSD"),IF({F}="JPY",1/GOOGLEFINANCE("CURRENCY:USDJPY"),1))))')
add([f'=ARRAYFORMULA(IF({A}="","",D{S}:D{E}*E{S}:E{E}*{fx}))'], row=S, col="H")
add([f'=ARRAYFORMULA(IF({A}="","",G{S}:G{E}-H{S}:H{E}))'], row=S, col="I")
add([f'=ARRAYFORMULA(IF({A}="","",IF(H{S}:H{E}=0,"",I{S}:I{E}/H{S}:H{E})))'], row=S, col="J")
add([f'=ARRAYFORMULA(IF({A}="","",IF($B${NAV_ROW}=0,"",G{S}:G{E}/$B${NAV_ROW})))'], row=S, col="K")
_r[0] = E + 2
NOTE_ROW = _r[0]
add(["* 成本以當前即時匯率折算 USD（非購入時匯率）；市值由 Portfolio 的 GOOGLEFINANCE 公式即時取得，抓不到價的標的在 Portfolio 的 notes 欄會註明。"
     f"　持股表最多 {HOLDINGS_CAPACITY} 檔，新標的會自動出現。",
     f'=IFERROR("⚠ 成本未換算幣別："&TEXTJOIN("、",TRUE,FILTER({A},{A}<>"",NOT(REGEXMATCH({F},"^(USD|TWD|EUR|JPY)$")))),"")'])
batches.append({"range": f"{DASHBOARD}!B{TOTAL_COST_ROW}", "values": [[f"=SUM(H{S}:H{E})"]]})

#: 圓餅圖放在摘要右邊（E3 起，摘要與配置表只用到 A–C 欄），不用往下捲就看得到。
PIE_ANCHOR_ROW, PIE_ANCHOR_COL = SUMMARY_HDR, 5
NEEDED_ROWS, NEEDED_COLS = NOTE_ROW + 3, 15
dims: list[dict] = []
if int(grid.get("rowCount") or 0) < NEEDED_ROWS:
    dims.append({"appendDimension": {"sheetId": dashboard_id, "dimension": "ROWS",
                                     "length": NEEDED_ROWS - int(grid.get("rowCount") or 0)}})
if int(grid.get("columnCount") or 0) < NEEDED_COLS:
    dims.append({"appendDimension": {"sheetId": dashboard_id, "dimension": "COLUMNS",
                                     "length": NEEDED_COLS - int(grid.get("columnCount") or 0)}})
if dims:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": dims}).execute()
    print(f"Grid → rows ≥ {NEEDED_ROWS}, cols ≥ {NEEDED_COLS}")

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
rc(NOTE_ROW, 1, NOTE_ROW, 2, "textFormat", textFormat={"italic": True, "fontSize": 9})

# 數字格式（持股表整個容量都套，列會自己長出來）
rc(NAV_ROW, 2, TOTAL_COST_ROW, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(PNL_ROW, 2, PNL_ROW, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"+$"#,##0;"-$"#,##0'})
rc(RET_ROW, 2, RET_ROW, 2, "numberFormat", numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(ALLOC_DATA_START, 2, LEV_END, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})
rc(ALLOC_DATA_START, 3, LEV_END, 3, "numberFormat", numberFormat={"type": "PERCENT", "pattern": "0.0%"})
rc(CASH_START, 2, CASH_END, 2, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0"})
rc(S, 4, E, 4, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0"})
rc(S, 5, E, 5, "numberFormat", numberFormat={"type": "NUMBER", "pattern": "#,##0.0000"})
rc(S, 7, E, 9, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0.00'})
rc(S, 10, E, 11, "numberFormat", numberFormat={"type": "PERCENT", "pattern": "0.00%"})
rc(S, 15, E, 15, "numberFormat", numberFormat={"type": "NUMBER", "pattern": '"$"#,##0'})


def cw(c1: int, c2: int, px: int) -> None:
    fmt.append({"updateDimensionProperties": {
        "range": {"sheetId": dashboard_id, "dimension": "COLUMNS", "startIndex": c1 - 1, "endIndex": c2},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}})


cw(1, 1, 150); cw(2, 2, 215); cw(3, 3, 110); cw(4, 4, 80)
cw(5, 5, 100); cw(6, 6, 45); cw(7, 8, 120); cw(9, 9, 110)
cw(10, 10, 80); cw(11, 11, 80)
# 輔助欄 M:O 隱藏（值仍在，公式讀得到）
fmt.append({"updateDimensionProperties": {
    "range": {"sheetId": dashboard_id, "dimension": "COLUMNS", "startIndex": 12, "endIndex": 15},
    "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})

# 條件格式：斑馬紋（只套有標的的列）、P&L（I）與 Return %（J）正綠負紅——重建前已清掉舊規則
rules: list[tuple[list[dict], dict, dict]] = [
    ([cr(S, 1, E, 11)], {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=AND($A{S}<>"",ISEVEN(ROW()))'}]},
     {"backgroundColor": rgb(245, 247, 250)}),
    ([cr(S, 9, E, 9)], {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
     {"backgroundColor": rgb(232, 245, 233), "textFormat": {"foregroundColor": rgb(27, 136, 70), "bold": True}}),
    ([cr(S, 9, E, 9)], {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
     {"backgroundColor": rgb(255, 235, 238), "textFormat": {"foregroundColor": rgb(183, 28, 28), "bold": True}}),
    ([cr(S, 10, E, 10)], {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
     {"textFormat": {"foregroundColor": rgb(27, 136, 70), "bold": True}}),
    ([cr(S, 10, E, 10)], {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
     {"textFormat": {"foregroundColor": rgb(183, 28, 28), "bold": True}}),
]
for index, (ranges, condition, style) in enumerate(rules):
    fmt.append({"addConditionalFormatRule": {"rule": {"ranges": ranges, "booleanRule": {"condition": condition, "format": style}},
                                             "index": index}})

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
      f"holdings {S}–{E}（動態，容量 {HOLDINGS_CAPACITY}）, note {NOTE_ROW}, pie at E{PIE_ANCHOR_ROW}")
print("持股表由公式自己列標的：Portfolio 新增／移除一檔不用重跑本腳本；只有版面或公式要改才跑。")
