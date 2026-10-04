# Phase 7 Step 7.2 — R3 漏網稽核第一窗（X3；窗口 2026 Q3）

> **性質：回放報告（評估檔）。** 規則照 [`registration.md`](registration.md) §5（母體 T0 定、看價格之前列）與 §0.1（第一次接觸日、偏差標註）；只引用 id、不改任何 ledger。
> 執行：2026-10-05（台北）。表格由程式從計算結果產生，程式碼逐字在附錄。

## 一句話

2026 Q3 母體 58 檔漲最多的前四分之一（15 檔）裡，**6 檔照官方比對法「系統沒有接觸」**：3653.TW、3324.TWO、3017.TW、2408.TW、3363.TWO、4971.TWO——
其中**散熱三家（健策 +101%、雙鴻 +51%、奇鋐 +32%）**正是 Q2 才選的散熱鏈（2026-10-04 開題），記憶體的南亞科 +24% 是「刻意不做 HBM／記憶體」的那一格；
**窗口內接觸過、卻沒有研究**的有 8 檔（2455.TW、3081.TWO、3006.TW、4979.TWO、LITE、AXTI、IQE.L、042700.KS），包括 X 帳號 08-27 起反覆點名、被 park 的晶豪科 +35%。

## 方法

- 窗口：2026-07-01 → 2026-09-30（§5.3 第 1 項）；報酬＝兩端「該日或之前最近的可用收盤」（`alpha.theme_cohort.series_return`），價格走追蹤表同一條序列。
- 母體：光通訊組 15 檔＋觀察名單 43 檔＝58 檔（電力、散熱組 7.1 才 append，不進第一窗）；有價格 58／58。
- 排名：同一個基準（光通訊組全體等權 Q3 報酬 **+1.0%**，15／15 成員有價），所以排名＝絕對報酬排名；前四分之一＝⌈58／4⌉＝**15** 檔。
- 第一次接觸（§0.1）：**名冊公司**以 lead 的 `company_id`／`entities.company_ids` 比對；沒有 lead → 讀圖或敘事第一次寫到它的 `created_at`；都沒有 →「系統沒有接觸」。
  **名冊以 git HEAD 已提交的版本為準**——2026-10-04 為 [693]／[695]／[696] staged、還沒核准的健策、奇鋐等不算在名冊（INV-6）。
  **名冊外**：`entities.tickers` → 標題逐字含英文名、中文名、帶上下文的代號（「(3653)」「$3653」「3653.TW」）。比對法逐列記在結果檔。
- ⚠ **lead registry 2026-07-22 才開機**（proposal §4.1）：窗口起點 07-01 早於它——「接觸早於窗口起點」**在第一窗無法觀測**，下表的 0 不是真的 0。

## 前四分之一（15 檔）

| 排名 | 代號 | Q3 報酬 | 來源 | 名冊（已提交） | 圖上 | 第一次接觸（官方比對） | 為什麼沒進研究（registry 原文節錄） | 備註 |
|---|---|---|---|---|---|---|---|---|
| 1 | 3653.TW | +101.2% | 觀察名單：散熱 | staged（[693]／[695]／[696] 待核准） | — | **系統沒有接觸** | 系統沒有接觸 |  |
| 2 | 2455.TW | +54.0% | 光通訊組 | ✅ | ✅ | lead 2026-09-17（`mops:2455.TW`，parked） | parked_reason: MOPS 一手已核對（tier-1 法定揭露），內容明確：公司行使轉換公司債贖回權、2026-11-18 終止櫃檯買賣。**不推進任何現有判斷**——①它是資本結構事件不是需求或瓶頸事件，對 [592] 全新那張工單（補獨立來源）沒有幫助；②全新（co:vpec）在 Phase 1 已判定 substitutability=2（四家台系磊晶廠在各自年報裡逐字互相指認對方是同層競爭者），不在投資候選內。⚠ 記 |  |
| 3 | 3324.TWO | +51.5% | 觀察名單：散熱 | — | — | **系統沒有接觸** | 系統沒有接觸 |  |
| 4 | 3081.TWO | +50.0% | 光通訊組 | ✅ | ✅ | 讀圖／敘事 2026-09-17（讀圖 sr_a6762186c7e8eb23（tech_cw_dfb_laser）） | 沒有 lead；讀圖／敘事最早 2026-09-17（讀圖 sr_a6762186c7e8eb23（tech_cw_dfb_laser）） | 字串比對另見 3 則：最早 2026-08-26 `udn:cna`「聯亞獲美客戶長約」（applied）——lead 上 company_id 與 entities 都是空的；07-17 已經 Reuters 那份進圖 |
| 5 | 3006.TW | +34.9% | 觀察名單：記憶體 | — | — | lead 2026-08-27（`x:aleabitoreddit`，parked） | parked_reason: 來源已誠實降級通過；不把未具名 engagement 推成 supplies_to，也不因容量 available now 推成 qualification 或出貨 |  |
| 6 | 3017.TW | +31.9% | 觀察名單：散熱 | staged（[693]／[695]／[696] 待核准） | — | **系統沒有接觸** | 系統沒有接觸 |  |
| 7 | 4979.TWO | +27.0% | 光通訊組 | ✅ | ✅ | lead 2026-09-24（`mops:4979.TWO`，parked） | parked_reason: 一手已逐字核對；內容純為時變財務數字（L4 不入圖），2026-08 月營收已由 monthly_revenue_observations 機械承載（兩列、兩個一手來源一致），季度／TTM 營收與既有 Engine C 對得上；無圖增量、無 Engine C consumer 缺口。 |  |
| 8 | 2408.TW | +23.7% | 觀察名單：記憶體 | — | — | **系統沒有接觸** | 系統沒有接觸 |  |
| 9 | LITE | +21.2% | 光通訊組 | ✅ | ✅ | lead 2026-07-22（`edgar:LITE`，triaged_no_go） | triage(no_go): 個別 Form 4 資訊量低；內部人交易應以彙總方式讀（Engine C 稀釋項），不逐筆進 pq1 |  |
| 10 | 3363.TWO | +20.9% | 光通訊組 | ✅ | ✅ | **系統沒有接觸** | 系統沒有接觸 | 字串比對另見 3 則：最早 2026-08-24 X 帳號、08-25 `system_decompose`（FAU 層）——lead 上沒有公司身分；08-30 進圖 |
| 11 | AXTI | +19.0% | 光通訊組 | ✅ | ✅ | lead 2026-07-22（`edgar:AXTI`，applied） | triage(go): 一個月內 5 張 8-K 密集叢集；AXT 是圖中 InP 基板節點，密集 8-K 常代表產能/訂單/融資重大事件 |  |
| 12 | CLF | +16.9% | 觀察名單：電力 | ✅ | ✅ | 讀圖／敘事 2026-10-04（讀圖 sr_a884792198990379（tech_large_power_transformer）） | 沒有 lead；讀圖／敘事最早 2026-10-04（讀圖 sr_a884792198990379（tech_large_power_transformer）） | 字串比對另見 2 則，都是 2026-10-04 電力鏈開題（窗口之後） |
| 13 | 4971.TWO | +14.3% | 光通訊組 | ✅ | ✅ | **系統沒有接觸** | 系統沒有接觸 | 沒有 lead、讀圖、敘事；但 2026-09-17 經 LandMark 與英特磊年報進圖、09-30 列入光通訊組——registration 的定義不含「進圖」與「入組」 |
| 14 | IQE.L | +4.6% | 光通訊組 | ✅ | ✅ | lead 2026-07-29（`x:aleabitoreddit`，triaged_no_go） | triage(no_go): Campaign 全量盤點後屬短回覆／績效或市場情緒、純作者推論、無法拆出可追查 atomic claim，或已由同一事件的代表 lead 覆蓋；保留原文供稽核但不重複消耗 pq1 | 另有 1 則只靠字串對得到 |
| 15 | 042700.KS | +4.1% | 觀察名單：先進封裝／測試 | — | — | lead 2026-07-29（`x:aleabitoreddit`，triaged_no_go） | triage(no_go): Campaign 全量盤點後屬短回覆／績效或市場情緒、純作者推論、無法拆出可追查 atomic claim，或已由同一事件的代表 lead 覆蓋；保留原文供稽核但不重複消耗 pq1 |  |

**歸類：** 系統沒有接觸 6（3653.TW、3324.TWO、3017.TW、2408.TW、3363.TWO、4971.TWO）｜窗口內接觸 8（2455.TW、3081.TWO、3006.TW、4979.TWO、LITE、AXTI、IQE.L、042700.KS）｜窗口後才接觸 1（CLF）｜接觸早於窗口 0（無法觀測，見上）。

## 官方比對法漏了什麼（→ failure log #13）

LandMark（#4）與上詮（#10）**照官方比對法是「沒有 lead」**，但字串比對找得到：LandMark 2026-08-26 中央社「聯亞獲美客戶長約」、上詮 08-24 X 帳號與 08-25 decompose——
這些 lead 的 `company_id` 與 `entities` 都是空的，名冊裡卻早有「聯亞」「FOCI」別名。原因：lead 的實體是 **harvest 當下依當時名冊算出的衍生值**，名冊之後新增公司，
舊 lead 不會重算（`engine_b/entities.py::backfill_entities` 的 docstring 寫明 2026-08-20 撞過同一件事；`--rescan` 存在，但沒有任何東西在名冊變動時觸發它）。
**結果：R3（與 S1 的「其他管道最早 first_seen」、計分表、related 比對）都會把「接觸過」算成「沒接觸」。** 本報告兩種都印；判讀用官方法，差異逐列記在備註。

## 7.5 failure log 候選（§2 X3：沒接觸的前四分之一逐檔進候選，不是條目）

健策、雙鴻、奇鋐（散熱；Q2 選題前沒有任何管道）、南亞科（記憶體；「刻意不做」的代價）——7.5 照「是不是同一個缺點撞到第二次」決定要不要寫成條目。
英特磊、上詮的「沒接觸」是比對法的問題（#13），不是發現管道的問題。

## 全體排名（58 檔）

| 排名 | 代號 | 來源 | Q3 報酬 | 對組（同一基準）超額 |
|---|---|---|---|---|
| 1 | 3653.TW | 觀察名單：散熱 | +101.2% | +100.2% |
| 2 | 2455.TW | 光通訊組 | +54.0% | +53.0% |
| 3 | 3324.TWO | 觀察名單：散熱 | +51.5% | +50.5% |
| 4 | 3081.TWO | 光通訊組 | +50.0% | +49.0% |
| 5 | 3006.TW | 觀察名單：記憶體 | +34.9% | +33.9% |
| 6 | 3017.TW | 觀察名單：散熱 | +31.9% | +30.9% |
| 7 | 4979.TWO | 光通訊組 | +27.0% | +25.9% |
| 8 | 2408.TW | 觀察名單：記憶體 | +23.7% | +22.7% |
| 9 | LITE | 光通訊組 | +21.2% | +20.2% |
| 10 | 3363.TWO | 光通訊組 | +20.9% | +19.8% |
| 11 | AXTI | 光通訊組 | +19.0% | +18.0% |
| 12 | CLF | 觀察名單：電力 | +16.9% | +15.9% |
| 13 | 4971.TWO | 光通訊組 | +14.3% | +13.3% |
| 14 | IQE.L | 光通訊組 | +4.6% | +3.6% |
| 15 | 042700.KS | 觀察名單：先進封裝／測試 | +4.1% | +3.0% |
| 16 | 8996.TW | 觀察名單：散熱 | +3.2% | +2.2% |
| 17 | MU | 觀察名單：記憶體 | +3.2% | +2.2% |
| 18 | 1519.TW | 觀察名單：電力 | +2.4% | +1.4% |
| 19 | 3450.TW | 觀察名單：光通訊 | +2.1% | +1.1% |
| 20 | FORM | 觀察名單：先進封裝／測試 | +1.5% | +0.5% |
| 21 | NVT | 觀察名單：散熱 | +0.4% | -0.6% |
| 22 | CAMT | 觀察名單：先進封裝／測試 | -0.1% | -1.2% |
| 23 | BE | 觀察名單：電力 | -4.3% | -5.3% |
| 24 | 2308.TW | 觀察名單：散熱 | -5.0% | -6.0% |
| 25 | 2344.TW | 觀察名單：記憶體 | -5.5% | -6.5% |
| 26 | 300394.SZ | 觀察名單：光通訊 | -8.3% | -9.3% |
| 27 | 5803.T | 觀察名單：光通訊 | -10.0% | -11.0% |
| 28 | ENR.DE | 觀察名單：電力 | -12.7% | -13.7% |
| 29 | SNDK | 觀察名單：記憶體 | -14.4% | -15.4% |
| 30 | 005930.KS | 觀察名單：記憶體 | -14.6% | -15.6% |
| 31 | 1503.TW | 觀察名單：電力 | -15.2% | -16.2% |
| 32 | GEV | 觀察名單：電力 | -16.2% | -17.2% |
| 33 | ENA.V | 光通訊組 | -17.7% | -18.7% |
| 34 | HPS-A.TO | 觀察名單：電力 | -18.6% | -19.6% |
| 35 | 6451.TW | 觀察名單：光通訊 | -19.7% | -20.7% |
| 36 | 3583.TW | 觀察名單：先進封裝／測試 | -21.2% | -22.2% |
| 37 | COHR | 光通訊組 | -21.9% | -22.9% |
| 38 | 010120.KS | 觀察名單：電力 | -22.2% | -23.2% |
| 39 | FN | 光通訊組 | -22.5% | -23.5% |
| 40 | VRT | 觀察名單：散熱 | -22.5% | -23.5% |
| 41 | POET | 光通訊組 | -22.9% | -23.9% |
| 42 | 6223.TWO | 觀察名單：先進封裝／測試 | -23.2% | -24.2% |
| 43 | MOD | 觀察名單：散熱 | -23.4% | -24.5% |
| 44 | CIEN | 觀察名單：光通訊 | -23.9% | -24.9% |
| 45 | CRDO | 觀察名單：光通訊 | -24.8% | -25.8% |
| 46 | 298040.KS | 觀察名單：電力 | -25.4% | -26.4% |
| 47 | AAOI | 光通訊組 | -28.6% | -29.6% |
| 48 | NVTS | 觀察名單：電力 | -29.8% | -30.8% |
| 49 | 3131.TWO | 觀察名單：先進封裝／測試 | -30.3% | -31.3% |
| 50 | POWL | 觀察名單：電力 | -30.3% | -31.3% |
| 51 | 000660.KS | 觀察名單：記憶體 | -30.6% | -31.6% |
| 52 | BESI.AS | 觀察名單：先進封裝／測試 | -31.9% | -32.9% |
| 53 | 300502.SZ | 觀察名單：光通訊 | -32.4% | -33.4% |
| 54 | 6515.TW | 觀察名單：先進封裝／測試 | -32.8% | -33.8% |
| 55 | 300308.SZ | 光通訊組 | -33.9% | -34.9% |
| 56 | 267260.KS | 觀察名單：電力 | -34.5% | -35.5% |
| 57 | 285A.T | 觀察名單：記憶體 | -38.4% | -39.4% |
| 58 | SIVE.ST | 光通訊組 | -48.2% | -49.2% |

## 偏差標註（registration §0.1）

| 偏差 | 本報告的情況 |
|---|---|
| ① discovery lookahead | 母體是 2026-10-04 T0 才列的名單（registration 記「列的時候沒有查任何價格」——是自述，無法另行驗證）；**但名單是在 Q3 已結束後列的**，所列的類別（散熱、記憶體）是 2026-06 前的公開知識 |
| ② 選樣偏差 | 不是全市場：只有預先列的 58 檔；名單外的大漲股不在稽核範圍 |
| ③ 超額基準回溯 | 光通訊組 2026-09-30 才定義——拿它當 Q3 的排名基準是回溯；第一窗只有這一組存在（§5.3 第 3 項） |

## 附錄：產生程式碼（逐字；`r3_audit.py`）

```python
"""Phase 7 Step 7.2 — R3 漏網稽核第一窗（X3；registration §5）。唯讀：yfinance（追蹤表同一支取價）、lead registry、名冊、Neo4j。

窗口 2026-07-01 → 2026-09-30（§5.3 第 1 項）；母體＝§5.1 光通訊組 15 檔＋§5.2 觀察名單 43 檔（窗口開始前已在名單上——
電力、散熱組 7.1 才 append，不進第一窗）。排名用同一個基準（光通訊組全體等權、不排除本檔），所以排名＝絕對報酬排名（§5.3 第 3 項）；
各檔對組超額另欄並列（成員排除本檔，追蹤表同一個 cohort_return）。前四分之一＝有完整價格的列數 × 1/4（無條件進位）。
比對法（§0.1）：名冊有 → lead 的 company_id 或 entities.company_ids；名冊沒有 → entities.tickers 字串相等，再退回標題逐字含代號或公司名。
輸出 r3_result.json（本檔同目錄）。
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
sys.path.insert(0, str(ROOT))

from alpha.providers.theme_cohorts import current_cohorts  # noqa: E402
from alpha.theme_cohort import close_on_or_before, cohort_return, series_return  # noqa: E402
from identity.registry import get_registry  # noqa: E402
from scripts.outcome_if_settled_today import _provider_close_series  # noqa: E402

OUT = Path(__file__).parent / "r3_result.json"
START, END = date(2026, 7, 1), date(2026, 9, 30)
COHORT_ID = "tc_35b0d5cd521656ea"
# §5.2 觀察名單（代號, 公司名逐字, 類別）——照 registration 抄，不增刪
WATCH = [
    ("CRDO", "Credo Technology", "光通訊"), ("300502.SZ", "Eoptolink", "光通訊"), ("300394.SZ", "TFC Optical", "光通訊"),
    ("5803.T", "Fujikura", "光通訊"), ("CIEN", "Ciena", "光通訊"), ("3450.TW", "Elite Advanced Laser", "光通訊"),
    ("6451.TW", "ShunSin", "光通訊"), ("267260.KS", "HD Hyundai Electric", "電力"), ("298040.KS", "Hyosung Heavy Industries", "電力"),
    ("010120.KS", "LS Electric", "電力"), ("1519.TW", "Fortune Electric", "電力"), ("1503.TW", "Shihlin Electric", "電力"),
    ("POWL", "Powell Industries", "電力"), ("HPS-A.TO", "Hammond Power Solutions", "電力"), ("CLF", "Cleveland-Cliffs", "電力"),
    ("GEV", "GE Vernova", "電力"), ("ENR.DE", "Siemens Energy", "電力"), ("BE", "Bloom Energy", "電力"),
    ("NVTS", "Navitas Semiconductor", "電力"), ("VRT", "Vertiv", "散熱"), ("3017.TW", "Asia Vital Components", "散熱"),
    ("3324.TWO", "Auras", "散熱"), ("2308.TW", "Delta Electronics", "散熱"), ("8996.TW", "Kaori", "散熱"),
    ("3653.TW", "Jentech", "散熱"), ("MOD", "Modine", "散熱"), ("NVT", "nVent", "散熱"),
    ("6515.TW", "WinWay", "先進封裝／測試"), ("6223.TWO", "MPI", "先進封裝／測試"), ("3131.TWO", "Grand Process", "先進封裝／測試"),
    ("3583.TW", "Scientech", "先進封裝／測試"), ("FORM", "FormFactor", "先進封裝／測試"), ("CAMT", "Camtek", "先進封裝／測試"),
    ("BESI.AS", "BE Semiconductor", "先進封裝／測試"), ("042700.KS", "Hanmi Semiconductor", "先進封裝／測試"),
    ("MU", "Micron", "記憶體"), ("000660.KS", "SK hynix", "記憶體"), ("005930.KS", "Samsung Electronics", "記憶體"),
    ("SNDK", "SanDisk", "記憶體"), ("285A.T", "Kioxia", "記憶體"), ("2408.TW", "Nanya Technology", "記憶體"),
    ("2344.TW", "Winbond", "記憶體"), ("3006.TW", "ESMT", "記憶體"),
]
assert len(WATCH) == 43


#: 中文名（registration §5.1／§5.2 表上的寫法）——台股與陸股的 lead 常只寫中文名或數字代號
ZH = {"3653.TW": "健策", "3017.TW": "奇鋐", "3324.TWO": "雙鴻", "2308.TW": "台達", "8996.TW": "高力", "3450.TW": "聯鈞",
      "6451.TW": "訊芯", "1519.TW": "華城", "1503.TW": "士林電機", "6515.TW": "穎崴", "6223.TWO": "旺矽", "3131.TWO": "弘塑",
      "3583.TW": "辛耘", "2408.TW": "南亞科", "2344.TW": "華邦電", "3006.TW": "晶豪科", "300502.SZ": "新易盛", "300394.SZ": "天孚",
      "5803.T": "藤倉", "298040.KS": "曉星", "042700.KS": "韓美", "4971.TWO": "英特磊", "2455.TW": "全新", "3081.TWO": "聯亞",
      "4979.TWO": "華星光", "3363.TWO": "上詮", "300308.SZ": "中際旭創", "267260.KS": "현대일렉트릭"}


def string_hits(leads: dict, *, ticker: str, name: str | None) -> tuple[list[dict], str]:
    """名冊外（以已提交的名冊為準）的比對：entities.tickers → 標題逐字含英文名／中文名／帶上下文的代號。"""
    hits = [l for l in leads.values()
            if ticker.upper() in [str(t).upper() for t in ((l.get("entities") or {}).get("tickers") or [])]]
    if hits:
        return hits, f"entities.tickers 含 {ticker}"
    base = ticker.split(".")[0].upper()
    pats, parts = [], []
    if name:
        pats.append(re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", re.I))
        parts.append(f"英文名「{name}」")
    if ZH.get(ticker):
        pats.append(re.compile(re.escape(ZH[ticker])))
        parts.append(f"中文名「{ZH[ticker]}」")
    if base.isdigit():   # 數字代號只認帶上下文的寫法，避免撞到任意數字
        pats.append(re.compile(rf"(\(\s*{base}\s*\)|\${base}(?!\d)|(?<!\d){base}\.(TW|TWO|KS|KQ|T|SZ|SS|HK)\b|(?<!\d){base}\s*(TT|KS|JP)\b)"))
        parts.append(f"代號（「({base})」「${base}」「{base}.交易所」）")
    elif len(base) >= 3:
        pats.append(re.compile(rf"\${re.escape(base)}(?![A-Za-z0-9])"))
        parts.append(f"cashtag「${base}」")
    hits = [l for l in leads.values() if any(p.search(str(l.get("title") or "")) for p in pats)]
    return hits, "標題逐字含 " + "、".join(parts)


def ledger_first_contact(company_id: str | None, ticker: str) -> tuple[str | None, str | None]:
    """沒有 lead 時的第一次接觸（registration §0.1）：讀圖或敘事第一次寫到它的 created_at。"""
    best: tuple[str, str] | None = None
    priv = ROOT / "library" / "private" / "alpha"
    for path in sorted((priv / "structure_readings").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            text = json.dumps(rec, ensure_ascii=False)
            if (company_id and company_id in text) or ticker.upper() in [str(t).upper() for t in rec.get("tickers") or []]:
                c = str(rec.get("created_at"))
                if best is None or c < best[0]:
                    best = (c, f"讀圖 {rec.get('reading_id')}（{path.stem}）")
    brief = priv / "briefs" / f"{ticker}.jsonl"
    if brief.exists():
        for line in brief.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                c = str(rec.get("created_at"))
                if best is None or c < best[0]:
                    best = (c, f"敘事 {rec.get('brief_id')}")
    return (best[0], best[1]) if best else (None, None)


def why_not(lead: dict) -> str:
    refs = lead.get("refs") or {}
    triage = lead.get("triage") if isinstance(lead.get("triage"), dict) else {}
    for key in ("parked_reason", "not_pursued_reason"):
        if refs.get(key):
            return f"{key}: {str(refs[key])[:260]}"
    if triage.get("reason"):
        return f"triage({triage.get('decision')}): {str(triage['reason'])[:260]}"
    return "（registry 沒有寫理由）"


def committed_registry() -> dict[str, str]:
    """已提交（git HEAD）的名冊：research_ticker → company_id。今晚為 [691]–[696] staged、未核准的項目不算（INV-6）。"""
    import subprocess
    raw = subprocess.run(["git", "show", "HEAD:config/company_identity.json"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    return {str(c["research_ticker"]).upper(): c["company_id"] for c in json.loads(raw)["companies"] if c.get("research_ticker")}


def main() -> None:
    reg = get_registry()
    committed = committed_registry()
    current, errors = current_cohorts()
    assert not errors
    cohort = next(c for c in current if c.cohort_id == COHORT_ID)
    population = [(m.ticker, m.company_id, None, "光通訊組") for m in cohort.members] + \
                 [(t, None, n, f"觀察名單：{k}") for t, n, k in WATCH]
    assert len(population) == 58
    tickers = sorted({p[0] for p in population})
    cache = Path(__file__).parent / "r3_series_cache.json"
    if cache.exists():
        raw_cache = json.loads(cache.read_text(encoding="utf-8"))
        series = {tk: {date.fromisoformat(d): v for d, v in s.items()} for tk, s in raw_cache["series"].items()}
        units = raw_cache["units"]
    else:
        series, units = {}, {}
        for tk in tickers:
            s, u = _provider_close_series(tk, date(2026, 6, 15))
            series[tk], units[tk] = s, u
        cache.write_text(json.dumps({"series": {tk: {d.isoformat(): v for d, v in s.items()} for tk, s in series.items()},
                                     "units": units}), encoding="utf-8")
    base = cohort_return(cohort, start=START, end=END, series=series)  # 同一個基準：全體成員、不排除本檔

    leads = json.loads((ROOT / "library" / "leads" / "pending_leads.json").read_text(encoding="utf-8"))["leads"]
    graph_ids: set[str] = set()
    try:
        from query.structure import _graph_driver
        drv = _graph_driver()
        with drv.session() as session:
            graph_ids = {r["id"] for r in session.run("MATCH (n:Entity) WHERE n.id STARTS WITH 'co:' RETURN n.id AS id")}
        drv.close()
        graph_ok = True
    except Exception as exc:  # noqa: BLE001
        graph_ok = f"讀不到圖：{type(exc).__name__}"

    rows = []
    for tk, cid, name, origin in population:
        staged_cid = reg.company_id_for_ticker(tk)
        cid = cid or committed.get(tk.upper())   # 已提交名冊才算「在名冊」
        staged_only = (cid is None and staged_cid is not None)
        ser = series.get(tk) or {}
        ret = series_return(ser, START, END)
        a, b = close_on_or_before(ser, START), close_on_or_before(ser, END)
        member_excess = None
        if ret is not None:
            own = cohort_return(cohort, start=START, end=END, series=series, exclude_company=cid, exclude_ticker=tk)
            member_excess = ret - own["return"] if own["return"] is not None else None
        display = None
        if cid:
            try:
                display = reg.company(cid).display_name
            except Exception:  # noqa: BLE001
                display = None
        rows.append({"ticker": tk, "company_id": cid, "staged_only_company_id": staged_cid if staged_only else None,
                     "name": name or display,
                     "origin": origin, "window_return": ret, "start_close_date": a[0].isoformat() if a else None,
                     "end_close_date": b[0].isoformat() if b else None,
                     "excess_vs_base": (ret - base["return"]) if (ret is not None and base["return"] is not None) else None,
                     "excess_vs_cohort_ex_self": member_excess, "quote_unit": units.get(tk)})
    priced = [r for r in rows if r["window_return"] is not None]
    k = math.ceil(len(priced) / 4)
    ranked = sorted(priced, key=lambda r: r["window_return"], reverse=True)
    top = ranked[:k]
    for r in top:
        cid = r["company_id"]
        if cid:   # 名冊公司（已提交）：官方比對法＝company_id
            hits = [l for l in leads.values() if l.get("company_id") == cid
                    or cid in ((l.get("entities") or {}).get("company_ids") or [])]
            method = f"company_id={cid}（lead 的 company_id 或 entities.company_ids）"
            aux_hits, aux_method = string_hits(leads, ticker=r["ticker"], name=r["name"])
        else:     # 名冊外（含今晚 staged、未核准的）：字串比對
            hits, method = string_hits(leads, ticker=r["ticker"], name=r["name"])
            aux_hits, aux_method = [], None
        hits = sorted(hits, key=lambda l: str(l.get("first_seen")))
        first = hits[0] if hits else None
        ledger_c, ledger_src = (None, None)
        if not first:
            ledger_c, ledger_src = ledger_first_contact(cid or r.get("staged_only_company_id"), r["ticker"])
        r.update({
            "rank": ranked.index(r) + 1, "match_method": method, "lead_count": len(hits),
            "aux_string_hits": len({l["lead_id"] for l in aux_hits} - {l["lead_id"] for l in hits}) if aux_method else None,
            "aux_method": aux_method,
            "first_seen": first.get("first_seen") if first else None, "first_lead": first.get("lead_id") if first else None,
            "first_source": first.get("source") if first else None, "first_status": first.get("status") if first else None,
            "first_title": str(first.get("title"))[:160] if first else None,
            "statuses": sorted({l.get("status") for l in hits}),
            "ledger_first_contact": ledger_c, "ledger_first_contact_source": ledger_src,
            "why_not_researched": why_not(first) if first else ("沒有 lead；讀圖／敘事最早 " + str(ledger_c)[:10] + "（" + str(ledger_src) + "）"
                                                               if ledger_c else "系統沒有接觸"),
            "in_registry": bool(cid), "in_graph": (cid in graph_ids) if (graph_ok is True and cid) else (False if graph_ok is True else graph_ok),
            "contact_before_window": (str(first.get("first_seen"))[:10] < START.isoformat()) if first else
                                     ((str(ledger_c)[:10] < START.isoformat()) if ledger_c else False),
            "contact_in_window": (START.isoformat() <= str(first.get("first_seen"))[:10] <= END.isoformat()) if first else
                                 ((START.isoformat() <= str(ledger_c)[:10] <= END.isoformat()) if ledger_c else False),
        })
    result = {"window": [START.isoformat(), END.isoformat()], "base_cohort_return": base, "n_population": len(rows),
              "n_priced": len(priced), "unmeasured": [r["ticker"] for r in rows if r["window_return"] is None],
              "top_k": k, "top": top, "all_ranked": [{"rank": i + 1, "ticker": r["ticker"], "origin": r["origin"],
                                                     "window_return": r["window_return"], "excess_vs_base": r["excess_vs_base"]}
                                                    for i, r in enumerate(ranked)],
              "graph_read": graph_ok}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"priced {len(priced)}/{len(rows)}  top_k {k}  base {base['return']:.3f} (used {base['members_used']}/{base['members_total']})  unmeasured {result['unmeasured']}")
    for r in top:
        print(f"#{r['rank']:>2} {r['ticker']:<10} {r['window_return']:+.2f}  {r['origin']:<14} reg={r['in_registry']}"
              f"{'(staged)' if r['staged_only_company_id'] else ''} graph={r['in_graph']} leads={r['lead_count']}"
              f"{'+aux' + str(r['aux_string_hits']) if r['aux_string_hits'] else ''} first={str(r['first_seen'])[:10]} "
              f"{r['first_status']} ledger={str(r['ledger_first_contact'])[:10]} | {r['match_method'][:34]}")


if __name__ == "__main__":
    main()
```
