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
  - docs/brainstorms/2026-07-11-automation-reliability-workflow-requirements.md
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

補充來源（2026-07-11）：`docs/brainstorms/2026-07-11-automation-reliability-workflow-requirements.md`

- **R10** 系統必須能在使用者未開啟本機 session 的情況下仍主動觸及使用者（GitHub/email/手機通知），不能只靠 `SessionStart` hook
- **R11** 入圖前的人工核准是不可繞過的關卡，跟抽取成本高低無關
- **R12** 訊號初篩（triage）寧可寬鬆放行也不能悄悄篩掉線索，且每次都要回報篩選結果供稽核
- **R13** 新公司/新主題的入庫決策永遠由使用者主動觸發（「研究 X」），routine 只能建議、不能自動擴大追蹤範圍
- **R14** 引用轉發型來源（如策展帳號轉發的第三方分析）時，`origin_entity` 需追溯到真正源頭；追不到時要誠實標註為未追溯轉發，不能當作第一手來源

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

**KTD5 — U7/U8 拆成「cloud routine」與「session-start 檢查」兩種機制（2026-07-10 修訂，2026-07-11 深化）**
執行時發現原設計（CronCreate jobs 輸出到本機 memory 檔）不成立：`CronCreate` 是 session-only、recurring 最多存活 7 天，關掉這個 CLI 視窗工作就消失，無法做到真正的「每週/每季背景執行」。改用 `schedule` skill 建的 cloud routine 雖然能持久排程，但跑在 Anthropic 雲端 sandbox，連不到本機 Neo4j（`bolt://localhost:7687`）、本機 SQLite/Postgres、或本機 `.env` 密鑰。

2026-07-11 brainstorm（`docs/brainstorms/2026-07-11-automation-reliability-workflow-requirements.md`）進一步發現：使用者開本機 session 的頻率不穩定（可能連續數週不開），代表 `SessionStart` hook 本身也不能當作「確保訊息傳達到使用者」的機制——它只在使用者剛好開 session 時才觸發，等於用「使用者會不會回來」去補「使用者可能不會回來」這件事。真正的可靠層必須換到跟本機 session 完全無關的管道：**cloud routine + GitHub 通知（PR/Issue → email/手機）**。本機 `SessionStart` hook（U7b、U8）保留，但降級成「你剛好開了 session 時的順手摘要」，不是安全網本身。

另外發現使用者本機的 Neo4j 是自架的（Docker/Desktop），不是 Neo4j Aura 這種託管服務，沒有閒置暫停/刪除風險，而且使用者的電腦幾乎全天候開著——這代表原本設想的「把 Neo4j/Engine C 搬去雲端」不是唯一解法，優先驗證的是「讓 cloud routine 連到這台本來就開著的本機」（見 U7a）。

修訂後的分工：
- **U7a（前置驗證，新）**：先確認 cloud routine 連不連得到本機通道，此結果決定 U7 能做到多完整
- **U7（週報 + 訊號 pipeline）→ cloud routine**：不只是週報，擴充成「harvest → triage → extract → 開 PR/Issue 待核准」完整 pipeline（見下方 U7 重寫版）
- **U7c（triage skill，新）**：U7 pipeline 中間的判斷層，獨立成一個 skill.md
- **U7b（session-start PR digest）→ 維持，但重新定位為 convenience，不是可靠性保證**
- **U8（thesis 核查）→ session-start hook，已完成** —— 同樣重新定位為 convenience recap，可靠性不靠它

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

### U7a. Network Reachability & Credential Security Validation — 已完成，驗證結論：直連不通，改走 MCP（2026-07-11 執行）

**Goal:** 在建 U7 完整 pipeline 之前，先驗證 cloud routine 到底連不連得到使用者這台本來就開著的本機。

**Requirements:** R10（可靠性層的地基）

**執行結果（2026-07-11）：**

安全整備已完成：
- Neo4j admin 密碼已換成強隨機密碼（存 `.env`，不進 git）
- 已建 `cloud_routine` 專用帳號 + `routine_writer` 角色（MATCH + CREATE + SET PROPERTY + SET LABEL，無 DELETE/schema/admin）；用真實 `loader/load_to_neo4j.py` 驗證過能正常載入、且確認 DELETE 和 CREATE USER 都被正確拒絕

通道已建成且從公網可達：
- Cloudflare Tunnel（`stockbotv2-neo4j`，網域 `neo4j.minatoyukina.uk`）→ 本機 Neo4j HTTP Query API（port 7474，非 Bolt——HTTP 對 tunnel 友善得多）
- 從公網用 admin 帳密查詢成功（HTTP 202，回傳正確節點數）

**Cloud routine 直連驗證：四次測試全部失敗，判定「此路不通」：**

| 測試 | 設定 | 結果 |
|------|------|------|
| v1 | 預設環境（Trusted 白名單） | `curl (56) CONNECT tunnel failed, response 403`——Anthropic 出站 proxy 直接拒絕 |
| v2 | Capabilities 加 Additional allowed domains | 請求未到達（tunnel 計數器無變化） |
| v3 | 同上，排除設定延遲（20+ 分鐘後重測） | 請求未到達 |
| v4 | Capabilities 切到 All domains | 請求未到達 |

**結論：** Pro 方案上，claude.ai Capabilities 的網路設定（含 All domains）完全不影響 Claude Code cloud routine 的 sandbox——那是聊天 code-execution 的沙盒設定，兩者是獨立體系。另外用 `ANTHROPIC_API_KEY` 走 Managed Agents API 建的 limited-networking 環境，routine 系統看不到（`environment_not_found`），也不通。「指定網域白名單」作為受支援功能是 Enterprise 層級的東西。

**替代路線（已定案，見 U7d）：** MCP connector 的流量走 Anthropic 伺服器轉發，不受 sandbox 網域白名單限制——在本機包一個小 MCP server（暴露窄工具：查圖、載入已驗證抽取），走同一條 tunnel 暴露，掛成 custom connector。此路線不只救 routine，還讓手機 App 對話也能直接讀寫圖，功能上完全等價於（甚至優於）原直連設計。今日建成的 tunnel/帳號/密碼基礎設施全部重用。

---

### U7. Signal Harvest → Triage → Extract → Approve Pipeline（2026-07-11 大幅重寫，取代原本單純的「週報」設計）

**Goal:** 每週自動從已追蹤主題 + Engine B 策展信號源收集線索，初篩後直接抽取成結構化草稿，開 PR/Issue 讓使用者核准是否入圖——不管使用者有沒有開本機 session 都能觸及到人。

**Requirements:** R6, R7, R10, R11, R12, R13, R14

**Dependencies:** U7d（graph MCP server 已上線並掛成 connector——U7a 驗證直連不通後的替代路線）；U7c（triage skill 已完成）；GitHub 連接

**Files:**
- `config/themes.txt` — 已建（活躍主題清單）
- `crons/weekly_scan_prompt.md` — 需整份改寫為 cloud routine 的自包含 prompt，涵蓋四階段 pipeline，不只是週報
- 新增：`docs/reports/`（週報類輸出，routine 對此開 PR）

**（2026-07-11 修訂）圖的讀寫一律走 U7d 的 MCP connector**，不是直連 tunnel HTTP：triage 的新穎性比對用「查圖」工具、核准後的 load 用「載入抽取」工具。

**Approach（四階段）：**

1. **Harvest（廣撒網，便宜）：** 對 `config/themes.txt` 每個主題做 web search；同時檢查 Engine B 的策展信號源（如 aleabitoreddit 的 RSS/貼文）。若某則線索是「轉發第三方研究」的形式（如截圖某券商筆記），額外搜一次嘗試追到原始文件——追不到是常態，不是阻擋條件（R14）
2. **Triage（初篩，交給 U7c 定義的 skill）：** 對每則 harvest 到的原始材料跑輕量判斷：是否關聯已追蹤主題/公司、是否新資訊、是否有可逐字引用的具體內容、是否可能是新的 `origin_entity`。判斷刻意寬鬆，且每次都記錄篩掉了什麼、為什麼（R12）
3. **Extract（抽取，不再卡人工核准）：** 對通過 triage 的每一則，直接跑完整結構化抽取（比照 `extract.py`/`prompts/extract_system.md` 的規則），產出實際的 node/edge/quote 草稿——使用者用的是訂閱方案，這一步不再是成本考量，是品質考量：讓使用者審的是真正的草稿，不是一段摘要
4. **Approve（人工核准，永遠保留）：**
   - 有實際報告產出（週報）→ 開 **PR**
   - 純粹是提醒、沒有可合併產出（例如某訊號可能觸發某 thesis 的 disproof_condition）→ 開 **Issue**
   - 使用者核准後，**下週例行 routine 順便處理 load**，不建立即時 webhook 觸發（保持簡單，見 brainstorm 文件的 Scope Boundaries）
   - 發現全新公司/主題（不在 `config/themes.txt` 或 `TICKER_MAP` 裡）→ 只在報告裡建議，不自動抽取或入庫，等使用者主動說「研究 X」（R13）

**Test scenarios:**
- 手動 `RemoteTrigger` run now → PR/Issue 內容包含 harvest 到的項目、triage 篩選結果（含被篩掉的）、通過項目的抽取草稿
- themes.txt 有 comment 行 → 被正確忽略，不搜尋
- Engine B 來源（如 aleabitoreddit 貼文轉發某券商筆記）→ 若追到原始文件，`origin_entity` 標成原始機構；追不到 → 標成「未追溯轉發」，不當作第一手引用
- 使用者上週核准的項目 → 這次 routine 執行 load 進 Neo4j（用 U7a 建立的最小權限帳號）
- 發現一個全新的、未追蹤的公司 → 報告裡出現建議，沒有自動抽取

**Verification:** Routine 手動觸發一次後，GitHub 出現新 PR/Issue，內容包含實際草稿（不只是摘要）+ 篩選稽核紀錄。

---

### U7d. Graph MCP Server（2026-07-11 新增——U7a 驗證直連不通後的正式替代路線，也是「手機對話讀寫圖」的基礎設施）

**Goal:** 在本機（常開機器）跑一個小 MCP server，把 Neo4j 的讀寫包成窄工具，走已建成的 Cloudflare Tunnel 暴露，掛成 claude.ai custom connector——讓 cloud routine、手機 App 對話、網頁對話都能安全地讀寫知識圖譜。

**Requirements:** R10、R11（入圖核准仍是人工，只是核准的「地點」從電腦前解放到任何 Claude 介面）

**Dependencies:** U7a 已完成（tunnel、`cloud_routine` 最小權限帳號、強密碼都已就緒）

**Files:**
- 新增：`mcp_server/graph_mcp.py`（MCP server 本體，Python）
- 修改：`C:\Users\Cheng\.cloudflared\config.yml`（加一個 hostname ingress，如 `mcp.minatoyukina.uk`）
- 修改：`requirements.txt`（加 MCP SDK 依賴）
- `.env` 新增 MCP 認證 token（不進 git）

**Approach:**
1. **工具設計（窄面原則）——只暴露三個工具，不暴露原始 Cypher 寫入：**
   - `get_graph_context(company_id)`：包 `query/graph_context.py` 的邏輯，回傳公司子圖摘要
   - `run_read_query(cypher)`：唯讀查詢（用 `cloud_routine` 帳號連 Neo4j，該帳號本身就無 DELETE 權限，雙重保險）
   - `load_extraction(extraction_json)`：先跑 `loader/validate.py` 的驗證邏輯，通過才呼叫 `loader/load_to_neo4j.py` 的 load——**schema 驗證是內建的，不合格的 JSON 進不來**
2. **認證：** URL 路徑內嵌強隨機 token（custom connector 表單只有 URL + 選填 OAuth，path-token 是個人自用場景的務實選擇）；tunnel 之外再疊 Neo4j 帳號權限這層
3. **暴露：** cloudflared `config.yml` 加 `mcp.minatoyukina.uk → localhost:<mcp_port>` ingress + DNS route
4. **掛載：** 使用者在 claude.ai Settings → Connectors → Add custom connector 填入 URL
5. **永久化：** cloudflared 和 MCP server 都設成開機自動啟動（Windows 服務或工作排程器，需一次 admin 權限）——沒有這步，機器重開後雲端就斷線

**Test scenarios:**
- 本機直打 MCP endpoint → 工具清單正確回傳
- 走 tunnel 打 MCP endpoint（帶 token）→ 同樣結果；不帶 token → 拒絕
- 從手機 App 對話呼叫「查 SIVE 的圖 context」→ 回傳真實子圖資料
- `load_extraction` 餵一份不合 schema 的 JSON → 被驗證擋下，不寫圖
- 機器重開機 → tunnel 和 MCP server 自動恢復，App 對話仍可查圖

**Verification:** 手機 App 對話成功查到圖內真實資料 + 一次成功的 `load_extraction`（用測試 JSON，事後刪除）。

---

### U7c. Signal Triage Skill — 已完成（2026-07-11，`skills/signal-triage/SKILL.md`）

**Goal:** 定義一個獨立的 skill.md，把「這則原始材料值不值得往下跑抽取」的判斷邏輯講清楚，讓 cloud routine 能自動執行，同時保留給使用者事後稽核的空間。

**Requirements:** R12

**Dependencies:** 無，但 U7 依賴它

**Files:**
- 新增：`skills/signal-triage/SKILL.md`

**Approach:**

Skill 定義判斷四要素（呼應 lead-intake 既有的 Fast Path 判斷邏輯，但是自動執行版）：
1. **關聯性**：這則材料是否關聯 `config/themes.txt` 或 `TICKER_MAP` 裡已追蹤的公司/主題
2. **新穎性**：是否是圖裡已有的事實的第 N 次重複，還是真的有新資訊
3. **可引用性**：有沒有具體、逐字可查核的內容（呼應 CLAUDE.md L6 反幻覺鐵律：型號/公司名必須逐字出現）
4. **潛在獨立性**：這則材料看起來像不像一個跟現有來源不同的 `origin_entity`（直接影響 L8 gate 的進展，是最有價值的篩選條件）

判斷結果只有兩種：放行進 Stage 3（Extract）、或篩掉但記錄理由。刻意不做「模糊地帶再問一次」的第三種結果——寧可寬鬆放行，也不要讓 routine 卡住等一個當下不在場的人。

**Test scenarios:**
- 一則跟已追蹤公司無關的內容 → 篩掉，記錄「不關聯任何已追蹤主題」
- 一則已經在圖裡出現過的事實的第 5 次重述 → 篩掉，記錄「非新資訊」
- 一則具體、可逐字引用、且來源機構跟現有來源不同的材料 → 放行
- 一則模糊、有點像新資訊但拿不準的材料 → 依「寧可寬鬆」原則放行，不卡在 triage 這一關

**Verification:** 對一批混合了「明顯該放行」「明顯該篩掉」「模糊地帶」的測試材料跑一次，篩選結果符合「寬鬆但可稽核」的設計原則。

---

### U7b. Session-Start PR Digest（U7 的消費端，2026-07-11 補設計，尚未實作；2026-07-11 brainstorm 後重新定位為 convenience，不是可靠性保證）

**Goal:** U7 的 cloud routine 只負責「生產」PR；U7b 負責「你開 session 時主動看到有哪些待審週報 PR」，讓完整迴圈接起來——你看完簡報後決定要研究哪個主題，才觸發 `company-onboard` 找文件 + 跑入庫流程。**這是 convenience，不是可靠性保證**——真正確保你會被通知到的是 U7 的 PR/Issue + GitHub 本身的 email/手機通知（R10），U7b 只是「你剛好開 session 時多一層方便」。

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
- **2026-07-11 brainstorm 後重新定位：** 這也是 convenience，不是可靠性保證——使用者開 session 的頻率不穩定，真正的可靠性交給 U7 的 cloud+GitHub 通知層（R10）

**Test scenarios（已驗證）：**
- 手動跑 `python crons/thesis_freshness_check.py`，目前全部 thesis 在 90 天內 → 無輸出（quiet）✓
- Monkeypatch 模擬 2 份逾期 thesis → 輸出 `{"systemMessage": "📋 thesis-monitor: 2 份 thesis 已超過 90 天未核查（sivers 92天, cpo 45天）— 要現在核查嗎？"}` ✓
- `.claude/settings.local.json` JSON 格式驗證通過 ✓
- Hook 在 `SessionStart` 觸發（本輪對話外），需要開新 session 或 `/hooks` 重新載入才會實際發動——尚待下次開 session 驗證實際觸發

**Verification:** 開一個新 session 後，若有 thesis 逾期，`systemMessage` 主動出現；若都新鮮，安靜無輸出（已用 monkeypatch 驗證訊息格式，實際 hook 觸發待下次真實 session 確認）。

---

## Risks & Dependencies

| 風險 | 可能性 | 緩解 |
|------|--------|------|
| GCP API 認證重新設定複雜 | 中 | 用戶有先例，`.env.example` 提供明確步驟；gsheets.py 有 graceful fallback |
| Cloud routine 連不到本機通道（U7a 驗證可能失敗，平台已知有自訂白名單網域的 bug）| 中高 | U7a 是硬性前置驗證；若不通，U7 退回「只發現+通知」版本，或改走託管雲端（Aura/Neon，需評估月費） |
| last30days skill 的 3 個來源不涵蓋足夠的 CPO 訊號 | 中 | Weekly scan prompt 設計為「結果少時出 sparse week 提示」，不假裝有訊號 |
| SIVE 是瑞典股，yfinance SIVE.ST 資料可能不完整 | 中 | checklist.py 的 `manual_required` status 已處理此情況；不 crash，標 manual |
| 法說會逐字稿抓取：非 EDGAR，依賴 WebSearch 品質 | 中 | company-onboard skill 明確說明此限制，優先推薦用戶直接提供 IR 頁面 URL |
| Cloud routine 沒有官方密鑰保管機制，憑證只能放在 routine 設定裡 | 中 | U7a 要求開最小權限帳號 + 換強密碼，降低外洩時的影響範圍 |

---

## Open Questions

- ~~**CronCreate 設定細節**~~ — 已於執行時解決（見 KTD5）：`CronCreate` 是 session-only 且 recurring 最多 7 天，不適合本用途。U7 改用 `schedule` skill 的 cloud routine（輸出走 PR，不碰本機資源）；U8 改成 session-start 檢查，不用背景排程。
- ~~**Google Sheets 結構**~~ — 已於 U4 實作時對齊：欄位為 `ticker/symbol | company | bucket | shares | avg_cost | currency | notes`，bucket 用中文標籤（見 `fetchers/gsheets.py` docstring）。
- **themes.txt 的初始內容**：已建立 `config/themes.txt`，含 `cpo` 和 `sivers` 兩個主題；U7 cloud routine 上線後可依需要擴充。
- **Cloud routine 能不能連到本機通道**：2026-07-11 brainstorm 判定為「先當假設，繼續規劃，實際驗證留給 U7a 執行時做」——不是本計畫階段要解決的問題，見 `docs/brainstorms/2026-07-11-automation-reliability-workflow-requirements.md` 的 Outstanding Questions。

---

## Implementation Sequence（建議執行順序）

1. **U1 + U2**（無相依，可同 session 完成）— 修好資料品質閘道和 ticker
2. **U3**（依賴 U1）— Onboarding skill 到位後做 M1 CPO Depth Sprint
3. **M1 CPO Depth Sprint**（內容任務）— U3 到位後執行，讓 CPO 主題達到可信標準
4. **U4 + U5**（U4 先，U5 依賴 U4）— 個人化建議層
5. **U6 + U7a + U7c + U7d + U7 + U7b + U8**（U6、U7a、U7c、U8 已完成；U7d 是 U7a 驗證直連不通後的替代路線，也是手機對話讀寫圖的基礎；U7 依賴 U7d + GitHub 連接；U7b 需 U7 先建好）— 注意力層
6. **M2 Second Vertical Slice**（follow Plan 005）— M1 完成後
7. **L9 Gate 自動通過** — M2 完成 + investment-sop.md + Engine C 可用 → `preconditions.py` 全通過

---

## Sources & Research

- `docs/brainstorms/2026-07-10-investment-advisor-repositioning-requirements.md` — 本計畫 origin
- `docs/brainstorms/2026-07-11-automation-reliability-workflow-requirements.md` — U7/U7a/U7b/U7c/U8 可靠性架構的深化來源
- `docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md` — M2 執行指南（仍 active）
- `thesis/preconditions.py` — L9 gate 現有實作
- `loader/load_to_neo4j.py` — TICKER_MAP 確認存在，gap D6 分析
- `engine_c/checklist.py` — 財務清單現有實作確認
