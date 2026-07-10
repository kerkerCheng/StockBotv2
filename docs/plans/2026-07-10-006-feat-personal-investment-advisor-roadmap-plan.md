---
title: "feat: StockBotv2 Personal Investment Advisor — Full Roadmap"
date: 2026-07-10
status: active
type: feat
depth: deep
origin: docs/brainstorms/2026-07-10-investment-advisor-repositioning-requirements.md
supersedes:
  - docs/plans/2026-07-08-004-feat-investment-query-gap-audit-plan.md
references:
  - docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md
---

# feat: StockBotv2 Personal Investment Advisor — Full Roadmap

**Scope:** 將 StockBotv2 從「批次研究工具」升級為「個人 AI 主題投資顧問」——能自動取得可信文件、強制來源品質門檻、整合個人資產組合、主動推送訊號、並在 L9 前置條件滿足後開放個人化投資建議。

---

## Summary

目前系統的根本問題：研究品質被來源品質卡住（L8 自我報告偏誤），且每一步都需要人工。解法不是換架構，而是在現有三層架構上加四個能力：**品質閘道**（拒絕偏誤資料）、**自動取件**（省去搜尋剪貼）、**資產組合層**（個人化建議）、**注意力機制**（不要求用戶定時回來）。

本計畫取代 Plan 004 的里程碑框架，成為唯一的工作起點。Plan 005（第二垂直切片）保持 active，作為 M2 內容里程碑的執行指南。

---

## Problem Frame

**現在問 "SIVE 值得投資嗎" 的失敗路徑：**
1. 圖裡只有 SIVE 自家 2025 overview，答案必然正面（L8 偏誤）
2. 沒有個人資產 context，建議沒有「你能買多少」的維度
3. 如果你忙著做別的事，沒有人提醒你市場有了新動態

**成功後的路徑：**
- 系統發現 SIVE 相關新訊號 → 主動推送 30 秒 brief
- 你說「研究 SIVE」→ 系統自動找文件、你確認後自動入庫
- Lane Memo 需要 ≥3 個不同 origin_entity 才能生成，系統拒絕偏誤
- 你問「要買多少」→ 系統從 Google Sheets 知道你的 bucket 大小，給出有根據的建議

---

## Requirements

來源：`docs/brainstorms/2026-07-10-investment-advisor-repositioning-requirements.md`

- **R1** 一家公司的分析必須有 ≥3 個不同 `origin_entity` 才能生成 Lane Memo
- **R2** 文件發現 + 入庫 pipeline 的人工步驟只剩「確認來源獨立性」
- **R3** 系統知道用戶的高風險 bucket 大小和當前持倉（來自 Google Sheets）
- **R4** 投資建議包含針對 bucket 的 position sizing 建議
- **R5** SNS/新聞訊號在 ≤3 個 conversation turn 內完成 go/no-go 評估
- **R6** 每週自動掃描活躍主題，輸出可在 5 分鐘內讀完的週報
- **R7** 高訊號事件觸發 30 秒 brief，用戶一句話決定是否繼續
- **R8** 每季自動提醒 thesis 核查（disproof_condition 追蹤）
- **R9** 所有新能力在 L9 preconditions 未通過前，投資建議標籤維持 [Research Note]

---

## High-Level Technical Design

### 新增數據流

```mermaid
graph TD
    SNS["SNS/新聞訊號<br/>(你 or Cron)"] --> LT["U6: Lead Triage<br/>lead-intake skill 快速模式"]
    LT -->|go| DD["U3: Document Discovery<br/>company-onboard skill"]
    LT -->|no-go| END1["結束"]

    DD --> EDGAR["fetchers/edgar.py<br/>(已有)"]
    DD --> WEB["WebSearch tool<br/>(Claude 原生)"]
    EDGAR --> RAW["library/raw/"]
    WEB --> RAW
    RAW --> PIPE["現有 pipeline<br/>extract → validate → load"]
    PIPE --> NEO["Engine A<br/>Neo4j"]

    NEO --> INV["investment-research skill"]
    GS["U4: Google Sheets<br/>fetchers/gsheets.py"] --> PS["U5: Position Sizing<br/>skill 更新"]
    INV --> PS
    PS --> ADV["個人化投資建議"]

    CRON1["U7: Weekly Scan<br/>CronCreate job"] --> L30["last30days skill"]
    L30 --> RPT["週報 / 30秒 brief"]

    CRON2["U8: Thesis Monitor<br/>CronCreate job"] --> DC["disproof_condition 檢查"]
    DC --> ALERT["季度提醒"]
```

### 品質閘道位置

```
extract.py → validate.py → [U1: origin_entity 多樣性檢查] → load_to_neo4j.py
                                        ↓ (失敗)
                            "需要更多獨立來源才能繼續"

thesis/generate_lane_memo.py → [U1: Lane Memo 硬阻擋]
                                        ↓ (未達標)
                            "Company X 目前只有 1 個 origin_entity，需要 ≥3"
```

### 資產層接入點

```
fetchers/gsheets.py (U4)
    ↓ 回傳 dict: {total_assets, high_risk_budget, positions}
investment-research SKILL.md (U5)
    → 注入到 Lane Memo / advice 生成時的 context
```

---

## Scope Boundaries

### In scope
- U1–U8 八個實作單元（見下方）
- M1 CPO Depth Sprint（內容里程碑，非程式碼）
- M2 第二垂直切片（follow Plan 005）

### Deferred to Follow-Up Work
- Engine B SNS API 直接串接（X/Threads API 成本過高）
- 自動判斷來源獨立性（L8 人工確認是設計，不是缺口）
- 跨公司 sector map 報告模板（深度先於廣度）
- Underwrite Sheet（Watchlist 有足夠深度再說）
- 全自動 thesis 更新（人工入庫 + 觸發是設計選擇）

### Outside this product's identity
- 完全自動的投資決策
- 個人 X feed 爬蟲
- 即時股價追蹤 / 技術分析

---

## Key Technical Decisions

**KTD1 — Agentic Document Discovery 以 skill 實現，不另寫 Python script**
Claude 在對話中用現有工具（fetchers/edgar.py via Bash、WebSearch、Write）完成取件 + 入庫。不增加新的 Python 程式碼，降低維護成本。實作為新的 `company-onboard` skill（SKILL.md）。

**KTD2 — Source Quality Gate 分兩層**
(a) `loader/validate.py` 加 origin_entity 多樣性警告（warn，不 hard block，允許繼續入庫）；
(b) `thesis/generate_lane_memo.py` 加硬阻擋（error，不允許生成 Lane Memo）。
原因：入庫不阻擋允許積累資料；出報告阻擋才是真正保護投資建議品質的地方。

**KTD3 — A→C Ticker Patch：在 load 時寫入 + 一次性 migration**
`load_to_neo4j.py` 已有 TICKER_MAP；修法是在 `_build_node_params()` 對 Company node 時，把 `TICKER_MAP.get(node_id)` 加入 `attributes` dict。既有節點跑一次 migration Cypher。

**KTD4 — Google Sheets 以 fetchers/gsheets.py 實現，每 session 快取**
GCP Service Account credentials 存在 `.env`（`GSHEETS_CREDENTIALS_JSON` + `PORTFOLIO_SHEET_ID`）。每次 session 第一次呼叫時取資料、後續 cache dict 在 process 生命週期內，避免 API quota 問題。

**KTD5 — U7/U8 拆成「cloud routine」與「session-start 檢查」兩種機制（2026-07-10 修訂）**
執行時發現原設計（CronCreate jobs 輸出到本機 memory 檔）不成立：`CronCreate` 是 session-only、recurring 最多存活 7 天，關掉這個 CLI 視窗工作就消失，無法做到真正的「每週/每季背景執行」。改用 `schedule` skill 建的 cloud routine 雖然能持久排程，但跑在 Anthropic 雲端 sandbox，連不到本機 Neo4j（`bolt://localhost:7687`）、本機 SQLite/Postgres、或本機 `.env` 密鑰。

修訂後的分工：
- **U7（週報）→ cloud routine**：這個任務本來就只需要外部資源（`/last30days` web search + `config/themes.txt` 靜態清單），適合放雲端。Routine clone repo → 掃描 → 把週報寫成 `docs/reports/weekly_scan_<date>.md` → 開 PR（不直接 push main，維持人工確認）。下次開本機 session 時，Claude 看到新 PR/檔案即可提示「有 N 份週報待讀」。
- **U8（thesis 核查）→ session-start 檢查，不用排程**：厚重依賴本機 Engine C 財務查詢，改成寫進 `skills/investment-research/SKILL.md`：每次 session 開始時檢查各 active thesis 的 Lane Memo 日期，若距上次核查 > 90 天則主動提醒，用戶開口才觸發本機查詢。不需要任何雲端或背景基礎設施。

前提：cloud routine 需要 GitHub 連接 `kerkerCheng/StockBotv2`（建立時尚未連接，需先執行 `/web-setup` 或安裝 Claude GitHub App）。

**KTD6 — 主題清單為 repo 內的純文字檔**
`config/themes.txt`：每行一個主題名稱 + 關鍵字，cron job 讀取並逐主題呼叫 last30days。格式簡單，user 可直接編輯。

---

## Content Milestones（非程式碼，追蹤用）

### M1: CPO Depth Sprint

**目標：** SIVE、Coherent、Lumentum、＋ 2 家客戶端公司（如 Arista、Nvidia）各達到 ≥3 個不同 `origin_entity`，SIVE 的 `gate_override` 移除。

**觸發條件：** U1、U3 完成後執行（品質閘道 + 自動取件都到位）。

**完成標準：** `python loader/validate.py` 在這 5 家公司的 JSON 上不再回報 "sole source L8 weak"；`python thesis/preconditions.py` 的 financial_checklist 可通過（SIVE.ST 資料在 SQLite 中）。

### M2: 第二垂直切片

**目標：** 依 Plan 005 執行 AMAT/LRCX mature node segment 切片，產出 Lane Memo，使 `_check_second_slice()` 回傳 True。

**觸發條件：** M1 完成後（方法論在 CPO 上驗證過再切新主題）。

**完成標準：** `thesis/preconditions.py` 全部通過 → 投資建議標籤升格為 [Investment Note]。

---

## Implementation Units

### U1. Source Quality Gate

**Goal:** 在兩個層次強制執行 ≥3 origin_entity 規則：validate.py 警告層 + generate_lane_memo.py 硬阻擋層。

**Requirements:** R1, R9

**Dependencies:** 無

**Files:**
- `loader/validate.py` — 新增 `_check_origin_diversity()` 函式
- `thesis/generate_lane_memo.py` — 新增 gate check（呼叫 Neo4j 查 origin_entity 數量）

**Approach:**
- `validate.py`：在現有三層驗證後，加第四層：從 JSON 的 `sources[]` 提取所有 `origin_entity`，若 distinct count < 3，append WARN（不是 error，允許入庫）
- `generate_lane_memo.py`：生成前呼叫 `query/graph_context.py` 取得 company 的 sources，若 distinct origin_entity < 3，raise `QualityGateError` 並印出缺少的來源類型建議（例：「目前只有供應商自我報告，需要客戶端文件或第三方報告」）
- gate_override 需要：明確的 `--force` flag + 終端警告，不能靜默繞過

**Test scenarios:**
- 3 個不同 origin_entity 的 JSON → validate.py 無 WARN，generate_lane_memo.py 正常執行
- 1 個 origin_entity（如只有 Sivers 自家 IR）→ validate.py 出 WARN，generate_lane_memo.py 拒絕並說明缺少什麼
- 使用 `--force` 繞過 → 輸出 Lane Memo 並在頂部插入 `⚠️ gate_override: L8 偏誤風險` 標記
- 同一 origin_entity 的 3 份文件（如 3 份 Sivers IR）→ 仍視為 1 個 origin_entity，警告

**Verification:** `python loader/validate.py samples/single_source.json` 輸出 WARN；`python thesis/generate_lane_memo.py --company-id co:sivers_semiconductors` 回傳 QualityGateError。

---

### U2. A→C Ticker Patch

**Goal:** 在 Neo4j Company 節點的 `attributes` 中寫入 `ticker`，使 Engine C 能用 graph 資料 join 財務數據。

**Requirements:** R3, R4（財務數據查詢的前提）

**Dependencies:** 無

**Files:**
- `loader/load_to_neo4j.py` — `_build_node_params()` 加 ticker 注入邏輯
- `loader/migrate_add_ticker.py` — 一次性 migration script（新建）

**Approach:**
- `load_to_neo4j.py`：在 `_build_node_params()` 中，如果 `node.type == "Company"` 且 `node.id` 在 TICKER_MAP，把 `{"ticker": TICKER_MAP[node.id]}` merge 進 `attributes` dict 後再序列化為 JSON
- 私人公司（ticker=None）也寫入：`{"ticker": null}`，明確標記「已知無 ticker」
- `migrate_add_ticker.py`：執行一次 Cypher `MATCH (n:Company) WHERE n.attributes IS NOT NULL ...` 對每個已存在節點補 ticker 屬性

**Test scenarios:**
- load 一個 Coherent JSON → 之後查 Neo4j：`MATCH (n:Company {id: "co:coherent"}) RETURN n.attributes` 包含 `"ticker": "COHR"`
- load 一個 Anthropic JSON → attributes 包含 `"ticker": null`
- `migrate_add_ticker.py --dry-run` → 印出 plan 但不執行
- Engine C smoke test：`python engine_c/checklist.py COHR` 在 patch 後仍正常執行

**Verification:** `python loader/migrate_add_ticker.py` 執行無 error；之後 `python engine_c/checklist.py COHR` 回傳有值的結果。

---

### U3. Company Onboarding Skill

**Goal:** 新的 skill SKILL.md，定義 Claude 執行 "研究這家公司" 的完整工作流——自動搜尋文件、格式化、呈現 shortlist、用戶確認後自動跑 pipeline。

**Requirements:** R2

**Dependencies:** U1（需要品質閘道到位，onboarding 才有意義）

**Files:**
- `skills/company-onboard/SKILL.md` — 新建

**Approach:**

Skill 定義以下操作流程（Claude 在對話中執行，不需要另一個 Python script）：

1. **Discover**：接收公司名稱 → 呼叫 `fetchers/edgar.py --company <NAME>` 取 SEC filings + 用 WebSearch 找近期新聞/分析報告/學術論文（各不超過 3 份）
2. **Curate**：把找到的文件列成 shortlist，每份標明：標題、來源類型（自家 IR / 客戶端 / 第三方 / 學術）、origin_entity、抓到的關鍵 quotes
3. **Gate check**：在 shortlist 上標記「這批文件的 origin_entity 多樣性是否達到 ≥3？」若否，提示缺少什麼
4. **User confirm**：「以上 N 份文件，要全部入庫嗎？」（逐份可排除）
5. **Ingest**：對每份確認的文件，用 Write tool 寫入 `library/raw/`，然後 Bash 跑 `extract.py → validate.py → load_to_neo4j.py`
6. **Summary**：「已載入 X 份文件，新增 Y 個節點，Z 條 edge。當前 origin_entity 數量：N。」

觸發詞：「研究 X 公司」、「onboard X」、「把 X 加進知識庫」、「找 X 的文件」。

法說會逐字稿不在 EDGAR 內，需要走 WebSearch 找 Seeking Alpha / 公司 IR 網站；SKILL.md 需明確說明此差異並優先搜尋客戶端文件（比供應商 IR 更高價值）。

**Test scenarios:**
- "研究 SIVE" → skill 找到 SEC 文件（SIVE 是瑞典股，EDGAR 無資料）+ WebSearch 結果，shortlist 至少 3 份
- SIVE shortlist 全部是 Sivers 自家文件 → gate check 標出「未達 ≥3 origin_entity」並建議找客戶文件
- 用戶排除某份文件後確認 → 只有被確認的文件被寫入 library/raw/
- pipeline 跑完 → `python query/graph_context.py --company-id co:sivers_semiconductors` 回傳非空結果

**Verification:** 跑完 onboarding 後 Neo4j Browser 能查到新節點；`loader/validate.py` 對產出 JSON 無 schema error。

---

### U4. Google Sheets Portfolio Connector

**Goal:** 新的 fetcher 從 Google Sheets 取用戶的資產分布，供 position sizing 使用。

**Requirements:** R3

**Dependencies:** U2（ticker 需要在圖裡才能做 position join）

**Files:**
- `fetchers/gsheets.py` — 新建
- `.env.example` — 新增 `GSHEETS_CREDENTIALS_JSON` 和 `PORTFOLIO_SHEET_ID` 兩個 key

**Approach:**
- 用 Google Sheets API v4（用戶已有 GCP API 經驗）；credentials 走 Service Account JSON 路徑，`GSHEETS_CREDENTIALS_JSON` 環境變數存 JSON 字串或檔案路徑
- 目標：讀一個固定結構的 Sheet（欄位：total_assets, high_risk_budget, positions list），回傳 dict
- 每次 process 生命週期只 call API 一次，cached in module-level `_PORTFOLIO_CACHE`
- 若未設定 env var → graceful fallback，回傳 `{"available": False}` 而非 crash
- `get_portfolio()` 為主要 API；`refresh_portfolio()` 強制清快取重取

**Test scenarios:**
- env var 設定 + valid sheet → 回傳包含 `total_assets`, `high_risk_budget`, `positions` 的 dict
- env var 未設定 → 回傳 `{"available": False, "reason": "GSHEETS_CREDENTIALS_JSON not set"}`
- sheet 格式不符（欄位缺失）→ 回傳 `{"available": False, "reason": "missing column: high_risk_budget"}`
- 第二次呼叫 → 使用快取，不再 call API（可從 log 確認）

**Verification:** `python fetchers/gsheets.py` 直接執行時印出 portfolio dict；`.env.example` 有明確說明格式。

---

### U5. Personalized Advice Mode

**Goal:** 更新 investment-research skill，當 Google Sheets 資料可用時，自動在 Lane Memo 和 advice 回答中加入 position sizing 建議。

**Requirements:** R3, R4, R9

**Dependencies:** U4（需要 portfolio data）、U1（需要品質閘道）

**Files:**
- `skills/investment-research/SKILL.md` — 更新

**Approach:**

在 SKILL.md 的「生成 Lane Memo / 投資建議」段落新增：

1. **Portfolio context injection**：生成建議前，在 SKILL.md 中明確指示 Claude 呼叫 `python fetchers/gsheets.py`；若 `available=True` 則把 `high_risk_budget` 和 `positions` 注入到 prompt context
2. **Position sizing 框架**（寫在 SKILL.md 中，Claude 直接執行）：
   - thesis conviction level（1-5，基於 Lane Memo 評分）
   - bucket 使用率（現有持倉 / high_risk_budget）
   - 建議比例：conviction 5 + 低使用率 → 可至 bucket 的 15%；conviction 3 → ≤8%；conviction <3 → 不建議建倉
3. **L9 Gate 整合**：在 SKILL.md 中明確：`python thesis/preconditions.py` 不通過時，position sizing 建議改為「目前無法給建議，L9 前置條件未達標」
4. **Entry framing**：不是「現在買」，而是「當 X 發生時建倉是合理的」（符合長持 + thesis-based 風格）

**Test scenarios:**
- 問 "SIVE 買多少" + L9 未通過 → 回答包含 L9 未通過說明，無 sizing 數字
- 問 "SIVE 買多少" + L9 通過 + gsheets available + SIVE Lane Memo 存在 → 回答包含 bucket 百分比建議和進場條件
- 問 "SIVE 買多少" + gsheets unavailable → 回答包含 "Google Sheets 未設定，無法個人化建議" + 請用戶設定
- 問 "SIVE 買多少" + quality gate 未過（SIVE 仍 gate_override）→ 回答包含品質風險警告

**Verification:** 問 "SIVE 值得投資嗎？我該買多少？" 時，回答結構包含：thesis 評估 + L9 狀態 +（若可用）portfolio-aware sizing 建議。

---

### U6. Lead Triage Fast Path

**Goal:** 更新 lead-intake skill，在現有完整驗證流程前加一個 ≤3 turn 的快速 go/no-go 層。

**Requirements:** R5

**Dependencies:** 無

**Files:**
- `skills/lead-intake/SKILL.md` — 更新（在現有 SOP 前加 Fast Path 段落）

**Approach:**

在 SKILL.md 最前面加「Fast Path」段落（完整 SOP 不變，只是加前置快速層）：

**Fast Path 觸發條件：** 用戶貼的是 1-3 句話 / 一則標題 / 一條推文，而非完整文件。

**Fast Path 三步驟（≤3 turns）：**
1. **分類**（Turn 1）：訊號類型（產品新聞 / 供應鏈 / 財報 / 市場情緒 / 不相關）+ 與現有圖的關聯（哪些已有節點受影響？）
2. **評估**（Turn 1 或 2）：go / no-go / need-more-info。Go = 建議開完整研究；No-go = 說明為什麼不入庫（tier 4 / 無新資訊 / 與現有 thesis 不矛盾）
3. **行動**（Turn 2 或 3）：Go → 自動呼叫 company-onboard skill（U3）；No-go → 結束；Need-more-info → 一個問題

**特殊情境：** 若訊號可能觸發現有 thesis 的 disproof_condition → 快路徑中明確標出「⚠ 可能觸發 [COMPANY] thesis 的 disproof condition：[條件文字]」，不論 go/no-go 都要說。

**Test scenarios:**
- 貼一則「Nvidia 法說會提到 CPO 量產加速」推文 → Turn 1 分類為「供應鏈 / 產品」，標出 NVDA/COHR 相關節點，Turn 2 給 go 建議
- 貼一則 tier 4 論壇「$SIVE 要爆了」 → Turn 1 標為 tier 4 情緒，Turn 2 給 no-go 且說明原因
- 貼一則客戶法說會提到 "replacing our current laser supplier" → 標出可能觸發 SIVE/Lumentum 的 sole_source disproof condition
- 貼完整 PDF 文件 → 跳過 Fast Path，直接走現有完整 SOP

**Verification:** 貼一則 CPO 相關推文後，3 個 turn 內得到分類 + go/no-go + 行動建議。

---

### U7. Weekly Scan Cloud Routine（2026-07-10 修訂：改用 schedule skill 的 cloud routine，取代 CronCreate）

**Goal:** 每週自動掃描活躍主題，產出週報（5 分鐘可讀）+ 高訊號事件觸發 30 秒 brief。

**Requirements:** R6, R7

**Dependencies:** 無（需先連接 GitHub repo `kerkerCheng/StockBotv2`，見 KTD5）

**Files:**
- `config/themes.txt` — 已建（活躍主題清單）
- `crons/weekly_scan_prompt.md` — 已建，內容需調整為 cloud routine 的自包含 prompt（無法假設能存取本機路徑）
- 新增：`docs/reports/`（cloud routine 輸出目錄，routine 對此開 PR）

**Approach:**

改用 `schedule` skill 建立 cloud routine（`RemoteTrigger` action: create），而非 `CronCreate`：
- routine 每週觸發一次（cron 最小間隔 1 小時，選一個非整點時間，如週五 UTC 10:07 對應台灣週五 18:07）
- prompt 內容：讀 `config/themes.txt` → 對每個主題做 web search（cloud sandbox 連不到 `/last30days` 本機 skill，需直接用 WebSearch/等效工具重現同樣邏輯）→ 合成週報 markdown
- 輸出：寫入 `docs/reports/weekly_scan_<date>.md`，**開 PR 而非直接 push main**（維持人工確認這一關，不讓雲端 agent 靜默改變 repo 主線）
- 不做本機依賴的步驟（不查 Neo4j、不查 Engine C）——那些留給你下次開本機 session 時，我看到新 PR 再接手判斷是否要 onboard 新公司

**Test scenarios:**
- 手動 `RemoteTrigger` run now → PR 內容包含結構化週報 + 主題 section
- themes.txt 有 comment 行 → 被正確忽略，不搜尋
- 發現高訊號事件 → PR 描述或週報開頭有 30 秒 brief 標記
- 下次開本機 Claude Code session → 見 U7b，我用 `gh pr list` 主動列出待審 PR

**Verification:** Routine 手動觸發一次後，GitHub 出現新 PR，內容包含主題 section + actionable items。

---

### U7b. Session-Start PR Digest（U7 的消費端，2026-07-11 補設計，尚未實作）

**Goal:** U7 的 cloud routine 只負責「生產」PR；U7b 負責「你開 session 時主動看到有哪些待審週報 PR」，讓完整迴圈接起來——你看完簡報後決定要研究哪個主題，才觸發 `company-onboard` 找文件 + 跑入庫流程。沒有這一段，U7 開的 PR 只會安靜躺在 GitHub，等你自己想到才去看。

**Requirements:** R6, R7（跟 U7 共用）

**Dependencies:** U7 必須先建好（有 routine 在開 PR，這個 hook 才有東西可查）；GitHub 需已連接 `kerkerCheng/StockBotv2`；本機需有 `gh` CLI 且已認證

**Files:**
- 新增：`crons/weekly_scan_digest.py`（`SessionStart` hook script，跟 `crons/thesis_freshness_check.py`同一種寫法）
- `.claude/settings.local.json` — 在既有 `hooks.SessionStart` 陣列裡追加一筆（不覆蓋 U8 那筆）

**Approach:**

- Script 執行 `gh pr list --repo kerkerCheng/StockBotv2 --label weekly-scan --json number,title,url,body`（或用 U7 routine 固定的分支/標籤慣例過濾出週報 PR，避免跟其他手動 PR 混在一起——U7 建立時要記得幫 PR 打上 `weekly-scan` label）
- 若有開著的週報 PR → 印出 `{"systemMessage": "..."}`，內容是每個 PR 的主題摘要 + PR 連結，格式跟 U7 週報本身的「30 秒 brief」一致
- 若沒有開著的 PR → 安靜過去（同 U8 的「都新鮮就不輸出」原則）
- 純讀 `gh pr list` 的輸出，不碰 Neo4j/Engine C；跟 U8 的 hook 各自獨立，互不呼叫

**Test scenarios:**
- 手動跑 `gh pr list --label weekly-scan` 有結果時 → script 輸出正確格式的 systemMessage
- 沒有開著的週報 PR → 無輸出
- `gh` 未安裝或未認證 → script 需優雅失敗（`2>/dev/null || true`），不能讓 session 開不起來
- 使用者看到簡報後說「研究 X」→ 走 `company-onboard` skill，不是這個 hook 自己去跑

**Verification:** 待 U7 routine 建好、實際產出至少一個 PR 後，開新 session 應看到該 PR 的摘要主動出現。

---

### U8. Thesis Lifecycle Check — 已完成（2026-07-10 修訂並實作：從 CronCreate 排程改為真正的 `SessionStart` hook，不用背景基礎設施）

**Goal:** thesis 距上次核查超過 90 天時，開新 session 就主動提醒，格式為「N 份 thesis 已超過 90 天未核查（公司 N天, ...）」。

**Requirements:** R8

**Dependencies:** 無

**Files:**
- `crons/thesis_freshness_check.py` — 新建。純 stdlib，掃描 `thesis/*_lane_memo.md`，抓 `**生成日期：**` 欄位（沒有的話退回檔案 mtime，相容舊格式檔案），同公司多版本取最新，>90 天輸出 `{"systemMessage": "..."}`，都新鮮則不輸出（安靜）
- `.claude/settings.local.json` — 新增 `hooks.SessionStart`，每次開 session 執行此腳本
- `crons/thesis_monitor_prompt.md` — 保留為「用戶同意核查後」的完整核查邏輯參考（讀 disproof_condition → WebSearch → `engine_c/checklist.py` → L7 狀態分級），不再假設有背景排程呼叫它

**Approach（實際採用，比原設計更直接）：**

不用任何雲端或需要本機常駐的排程基礎設施——原因：完整核查需要 `engine_c/checklist.py`（本機 SQLite/Postgres），cloud routine 連不到；`CronCreate` 又是 session-only、撐不了 13 週。改用 Claude Code 本身的 `SessionStart` hook 機制（跟現有 `/last30days` 啟動提示同一種），比原計畫寫的「skill 內邏輯」更可靠：hook 是 harness 保證觸發的，不依賴使用者剛好觸發到 investment-research skill 的關鍵字。

- Hook 只做「該不該問」——純讀本機 markdown 檔案比日期，不碰 Neo4j/Engine C
- 使用者看到提醒後同意才觸發完整核查（讀 `crons/thesis_monitor_prompt.md` 的核查格式）

**Test scenarios（已驗證）：**
- 手動跑 `python crons/thesis_freshness_check.py`，目前全部 thesis 在 90 天內 → 無輸出（quiet）✓
- Monkeypatch 模擬 2 份逾期 thesis → 輸出 `{"systemMessage": "📋 thesis-monitor: 2 份 thesis 已超過 90 天未核查（sivers 92天, cpo 45天）— 要現在核查嗎？"}` ✓
- `.claude/settings.local.json` JSON 格式驗證通過 ✓
- Hook 在 `SessionStart` 觸發（本輪對話外），需要開新 session 或 `/hooks` 重新載入才會實際發動——尚待下次開 session 驗證實際觸發

**Verification:** 手動執行後 memory 目錄有 `thesis_review_YYYY-MM-DD.md`；對 active thesis 各有一段核查摘要。

---

## Risks & Dependencies

| 風險 | 可能性 | 緩解 |
|------|--------|------|
| GCP API 認證重新設定複雜 | 中 | 用戶有先例，`.env.example` 提供明確步驟；gsheets.py 有 graceful fallback |
| CronCreate 在 Windows 本機需要 Claude Code daemon 常駐 | 高 | KTD5：cron 輸出到 memory 檔，就算 cron 沒跑，下次對話手動觸發也能補 |
| last30days skill 的 3 個來源不涵蓋足夠的 CPO 訊號 | 中 | Weekly scan prompt 設計為「結果少時出 sparse week 提示」，不假裝有訊號 |
| SIVE 是瑞典股，yfinance SIVE.ST 資料可能不完整 | 中 | checklist.py 的 `manual_required` status 已處理此情況；不 crash，標 manual |
| 法說會逐字稿抓取：非 EDGAR，依賴 WebSearch 品質 | 中 | company-onboard skill 明確說明此限制，優先推薦用戶直接提供 IR 頁面 URL |

---

## Open Questions

- ~~**CronCreate 設定細節**~~ — 已於執行時解決（見 KTD5）：`CronCreate` 是 session-only 且 recurring 最多 7 天，不適合本用途。U7 改用 `schedule` skill 的 cloud routine（輸出走 PR，不碰本機資源）；U8 改成 session-start 檢查，不用背景排程。
- ~~**Google Sheets 結構**~~ — 已於 U4 實作時對齊：欄位為 `ticker/symbol | company | bucket | shares | avg_cost | currency | notes`，bucket 用中文標籤（見 `fetchers/gsheets.py` docstring）。
- **themes.txt 的初始內容**：已建立 `config/themes.txt`，含 `cpo` 和 `sivers` 兩個主題；U7 cloud routine 上線後可依需要擴充。

---

## Implementation Sequence（建議執行順序）

1. **U1 + U2**（無相依，可同 session 完成）— 修好資料品質閘道和 ticker
2. **U3**（依賴 U1）— Onboarding skill 到位後做 M1 CPO Depth Sprint
3. **M1 CPO Depth Sprint**（內容任務）— U3 到位後執行，讓 CPO 主題達到可信標準
4. **U4 + U5**（U4 先，U5 依賴 U4）— 個人化建議層
5. **U6 + U7 + U7b + U8**（U8 已完成；U6 已完成；U7 需先連接 GitHub 才能建，U7b 需 U7 先建好）— 注意力層
6. **M2 Second Vertical Slice**（follow Plan 005）— M1 完成後
7. **L9 Gate 自動通過** — M2 完成 + investment-sop.md + Engine C 可用 → `preconditions.py` 全通過

---

## Sources & Research

- `docs/brainstorms/2026-07-10-investment-advisor-repositioning-requirements.md` — 本計畫 origin
- `docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md` — M2 執行指南（仍 active）
- `thesis/preconditions.py` — L9 gate 現有實作
- `loader/load_to_neo4j.py` — TICKER_MAP 確認存在，gap D6 分析
- `engine_c/checklist.py` — 財務清單現有實作確認
