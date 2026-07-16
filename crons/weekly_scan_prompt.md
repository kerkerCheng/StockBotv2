# Weekly Signal Scan — Cloud Routine Prompt

> 這份 prompt 由 claude.ai 的 cloud routine 每週觸發執行。執行環境是 Anthropic 雲端沙盒：
> 有整份 repo 的 clone、有 web search、有 `stockbotv2-graph` MCP connector（讀寫知識圖譜的唯一管道）。
> **連不到使用者本機的任何東西**（Engine C SQLite、本機檔案）——需要圖譜一律走 MCP 工具。
> 設計出處：`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` 的 U7。

## 你的任務（四階段 pipeline）

### Stage 0 — 前置

1. 讀 `config/themes.txt` 取得活躍主題清單（`#` 開頭與空行忽略）
2. 讀 `skills/signal-triage/SKILL.md`——Stage 2 的判斷標準全在裡面
3. 讀 `skills/source-trace/SKILL.md`——Stage 2.5 的共同追源規則；不要在本 prompt 自創第二套分路
4. 呼叫 MCP 工具 `get_extraction_rules` 取得抽取規則書（Stage 3 用；也順便確認 MCP 連線正常）
5. **處理所有已核准但未入圖的週掃 PR，不限上週：**列出所有 `weekly-scan` label、
   `state=merged` 且沒有 `loaded` label 的 PR。PR merge 就是人工核准協定，不再解析留言中的
   「核准 #N」。逐份讀 PR 內 extraction 草稿並呼叫 `load_extraction`；只有該 PR 所有草稿都
   成功／冪等 matching 後才加 `loaded` label，並留言記錄 doc_ids 與結果。部分失敗不加 label，
   下次 routine 必須重試；已加 `loaded` 的 PR 永不重複處理。

> 這個 merged-PR gate 暫時是明確保留的 legacy direct-load flow。不要把本週新草稿改呼叫
> `apply_research_action`，也不要在沒有 merged PR 的情況用手機 Research Action 規則繞過 Stage 0；
> weekly scan 會在另一個 migration slice 才切換。

### Stage 1 — Harvest（廣撒網）

**主題面（theme-scoped）**——對每個活躍主題：
- 用 web search 搜尋過去 7 天內的新訊號：法說會提及、供應鏈/設計窗口/產能變化、競爭者動向、可能觸發 disproof_condition 的消息、下游客戶 M&A、新命名客戶

**Engine B 策展面（full-feed，不受主題清單限制）**：
- 掃 aleabitoreddit 過去 7 天的**全部**貼文/文章（搜 `site:aleabitoreddit.substack.com` + 近期推文；量少，帳號本身就是過濾器），**不管有沒有提到追蹤中的公司**
- 分流：講到已追蹤公司/主題 → 進正常 pipeline（Stage 2 起）；講到未追蹤的新公司/新主題 → 不抽取（R13），但**必列入週報「建議 onboard 候選」**，附「它為什麼值得看」一句話——當初 SIVE 就是這樣被這個帳號發現的，這條分流是 Engine B 存在的核心理由

**共通**：所有轉發、截圖、搜尋摘要與二手報導都必須進 Stage 2.5；完整處置以
`skills/source-trace/SKILL.md` 為準。不要沿用舊的「追不到也一律放行」捷徑。

### Stage 2 — Triage（初篩，照 signal-triage skill 執行）

對每則 harvest 到的原始材料跑五要素判斷（關聯性、新穎性、可引用性、潛在獨立性、矛盾／反證價值）：
- 新穎性判斷用 MCP 工具 `get_graph_context` 或 `run_read_query` 比對圖中現有內容；**MCP 連不上時不要卡住——跳過新穎性判斷、寬鬆放行、在稽核紀錄註明**
- 寬鬆原則：軟指標（新穎性、獨立性）不確定時一律放行
- **每一則被篩掉的材料都要記錄摘要 + 理由**，寫進最終報告的稽核段落

### Stage 2.5 — Trace（逐條追回原文）

對每則 PASS 材料，先拆 atomic claims，再逐條依 `skills/source-trace/SKILL.md` 的市場路由追源：

- 每條都保存手冊規定的 `attempts`：實際查過的登記表／query／URL、結果與 note；不能只寫「沒找到」
- 找到原文 → Stage 3 只從原文逐字抽取，轉述保留為 discovery lead，不算獨立 origin
- tier 1–2 文件本身可逐字取得、但它引用的上游事件拿不到 → 可誠實標記
  `tier_1_2_honest_passthrough` 後進草稿；不得冒充上游 origin
- tier 3–4 且原文未果 → **不產 extraction 草稿**，分別標 `isolated_tier_3`／
  `lead_only_tier_4`，進本週「追源未果清單」
- 原文反駁現有 thesis → 不丟棄；標 `contradicts`，以 signal-triage 第五要素高優先送 Stage 3

### Stage 3 — Extract（對通過 triage 的每一則做完整抽取）

- 嚴格依照 `get_extraction_rules` 回傳的規則書執行（尤其 L6：具體型號/公司名必須逐字出現在 quote；L4：屬性歸位三問）
- `origin_entity` = 真正發出本次實際取得文件的人。追到原文 → 使用原文機構；
  `tier_1_2_honest_passthrough` → 使用目前文件的發出者並標上游未獨立取得；不得虛構組合 origin 名稱
- 產出完整的 intermediate-format JSON 草稿（不呼叫 load_extraction——入圖必須等使用者核准）
- **全新公司（不在 `config/themes.txt` 或 `loader/load_to_neo4j.py` 的 TICKER_MAP）不做抽取**，只在報告中列為「建議 onboard 候選」（R13）

### Stage 4 — Report & Approve（開 PR，等人工核准）

1. 把週報寫到 `docs/reports/weekly_scan_<YYYY-MM-DD>.md`，開一個 **PR**（分支名 `weekly-scan/<YYYY-MM-DD>`，**打上 `weekly-scan` label**，不直接 push main）
2. 週報結構：
   ```
   ## 本週訊號掃描 — <日期>
   ### ⚡ 30 秒 brief（若有高訊號事件才寫；沒有就整段省略）
   ### 各主題發現（每主題一段；無動向就一句話說明，不湊字數）
   ### 抽取草稿（每份完整 JSON + 一句「這份能為 L8 帶來什麼」）
   ### Triage 稽核（篩掉了哪些、各自理由）
   ### 追源未果清單（claim、tier、嘗試路徑、卡點、下一步；沒有就寫「無」）
   ### 待印證清單（由圖即時導出 single-origin／orphan evidence；不得手工維護）
   ### 建議 onboard 候選（若有）
   ### 可能觸發 disproof 的訊號（若有，標 ⚠ 並引述對應 thesis 的 disproof_condition）
   ```
3. PR 描述開頭放 30 秒摘要 + 草稿 doc_id 清單，明寫「**merge 本 PR 即核准清單內全部草稿入圖**；
   不核准的草稿請在 merge 前從 PR 移除或關閉 PR」。不要再要求留言「核准 #N」。
4. 純提醒、無可合併產出的事項（如 disproof 觸發跡象）→ 另開 **Issue**（同樣打 `weekly-scan` label）
5. 讀 `query/single_origin_report.py` 的 `SINGLE_ORIGIN_CYPHER` 常數，將其中
   `$company_id` 文字替換為 `null` 後交給 MCP `run_read_query`，把結果整理進「待印證清單」。
   不複製／手改另一份 Cypher。
6. 把本週新的 tier 3–4 追源未果項目 append 到單一 open Issue「追源未果 backlog」
   （`weekly-scan` label；無則建立）。每項用 canonical lead URL + atomic claim 當去重 key；已存在只追加
   新 attempt／狀態，不重複貼一筆。這個 rolling Issue 會由既有 SessionStart digest 自動浮現。

## 鐵律

- 繁體中文輸出
- 不確定的訊號標「？」，不假裝確定；某主題本週無動向就直說
- **絕不自行呼叫 `load_extraction` 入庫本週新抽取的草稿**——只有 Stage 0 處理「上週已獲使用者核准」的項目時才允許呼叫
- 找不到任何值得說的事 → PR 照開（週報說明這是 sparse week），讓使用者知道系統有在跑
