# Weekly 審查 — Cloud Routine Prompt

> 這份 prompt 由 claude.ai 的 cloud routine 每週觸發執行（台北時間 06:00，避開互動 session 的用量窗口）。
> 執行環境是 Anthropic 雲端沙盒：有整份 repo 的 clone、有 web search、有 `stockbotv2-graph`
> MCP connector（讀寫知識圖譜的唯一管道）。**連不到使用者本機的任何東西**（Engine C SQLite、
> 本機檔案）——需要圖譜一律走 MCP 工具。
> 設計出處：`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` 的 U7，
> 2026-07-18 refine：研究降級為 topic discovery、併入 thesis 生命週期核查與系統健康審查。

## 定位（先讀這段）

本 routine 是**審查與發現**，不是研究。它做三件事：
1. **Topic discovery**——掃訊號、聚類成 topic、排序給使用者選；**絕不自行追源或抽取**。
   被選中的 topic 由使用者在本機 session 說「research topic N」才啟動完整
   lead-intake / source-trace 流程。
2. **Thesis 生命週期核查（L7）**——讀 `thesis/lifecycle.json`，只對到期的 thesis 跑
   disproof 檢查（到期制：active 每 90 天、watch 每 30 天、review_required 每週必列）。
3. **系統健康審查**——跑 `query/health_audit.py` 的 Cypher 常數 + repo 檔案檢查，
   回報圖譜／memo／管道的紅黃綠狀態。

## 執行流程

### Stage 0 — 前置與遺留維護

1. 讀 `config/themes.txt` 取得活躍主題清單（`#` 開頭與空行忽略）
2. 讀 `skills/signal-triage/SKILL.md`——Stage 2 的判斷標準全在裡面
3. 呼叫 MCP 工具 `get_graph_context` 或 `run_read_query` 任一，確認 MCP 連線正常；
   連不上時不要卡住——跳過所有需要圖的步驟、在報告開頭標明 MCP 不可用
4. **處理所有已核准但未入圖的週掃 PR，不限上週：**列出所有 `weekly-scan` label、
   `state=merged` 且沒有 `loaded` label 的 PR。PR merge 就是人工核准協定。逐份讀 PR 內
   extraction 草稿並呼叫 `load_extraction`；只有該 PR 所有草稿都成功／冪等 matching 後
   才加 `loaded` label，並留言記錄 doc_ids 與結果。部分失敗不加 label，下次 routine
   必須重試；已加 `loaded` 的 PR 永不重複處理。

> 這個 merged-PR gate 是明確保留的 legacy direct-load flow，服務舊 PR 裡的抽取草稿
> （2026-07-18 起本 routine 不再產新草稿，此步驟會自然清空）。不要在沒有 merged PR
> 的情況用手機 Research Action 規則繞過 Stage 0。

### Stage 1 — Harvest（廣撒網，輕量）

**主題面（theme-scoped）**——對每個活躍主題：
- 用 web search 搜尋過去 7 天內的新訊號：法說會提及、供應鏈/設計窗口/產能變化、
  競爭者動向、可能觸發 disproof_condition 的消息、下游客戶 M&A、新命名客戶
- 每個主題以 2–3 次搜尋為度；目標是「發現存在」，不是「查證內容」

**Engine B 策展面（full-feed，不受主題清單限制）**：
- 掃 aleabitoreddit 過去 7 天的**全部**貼文/文章（搜 `site:aleabitoreddit.substack.com` +
  近期推文；量少，帳號本身就是過濾器），**不管有沒有提到追蹤中的公司**
- 可優先試 RSS feed `https://aleabitoreddit.substack.com/feed`（channel 標題是
  "Serenity"、不是帳號名）。**解析失敗 ≠ 無新文**：失敗時必須退回上面的 `site:`
  搜尋，並在稽核紀錄註明用了 fallback；Substack 首頁需 JavaScript，不能直接爬
- 分流：講到已追蹤公司/主題 → 進 Stage 2；講到未追蹤的新公司/新主題 → **必列入
  「建議 onboard 候選」**，附「它為什麼值得看」一句話——當初 SIVE 就是這樣被這個
  帳號發現的，這條分流是 Engine B 存在的核心理由

### Stage 2 — Triage（初篩，照 signal-triage skill 執行）

對每則 harvest 到的原始材料跑五要素判斷（關聯性、新穎性、可引用性、潛在獨立性、
矛盾／反證價值）：
- 新穎性判斷用 MCP 工具 `get_graph_context` 或 `run_read_query` 比對圖中現有內容；
  MCP 連不上時跳過新穎性判斷、寬鬆放行、在稽核紀錄註明
- **公司 ID（`co:*`）不要憑公司名猜**：先查 repo clone 的 `loader/load_to_neo4j.py`
  `TICKER_MAP`，或用 `query/health_audit.py` 的 `COMPANY_IDS_CYPHER` 經 `run_read_query`
  列出圖中 Company 再比對（例：Sivers 是 `co:sivers_semiconductors`）。ID 未命中時
  在稽核紀錄區分「ID 沒解析對」與「圖中真無此公司」，不能默默跳過該公司的比對
- 寬鬆原則：軟指標（新穎性、獨立性）不確定時一律放行
- **每一則被篩掉的材料都要記錄摘要 + 理由**，寫進報告的稽核段落
- 原文反駁現有 thesis → 標 `contradicts`，在 Topic Digest 置頂並連到對應 thesis 的
  disproof_condition

### Stage 3 — Topic Digest（取代舊的追源與抽取）

把通過 triage 的訊號**聚類成 topic**（同一事件/主題的多條訊號合一），每個 topic 給：
- 一句摘要 + 來源連結（轉述/截圖就標明是轉述，不用追原文）
- 對圖中哪條 thesis / 哪條邊有影響（用 `run_read_query` 對照，答不出來就寫「新領域」）
- **值得 research 的理由**（一句話：能補什麼證據缺口、或威脅哪條 thesis）
- 建議動作：`research`（值得本機深挖）/ `onboard`（新公司候選）/ `FYI`（知道就好）

排序依「對 active thesis 的影響度 > 新穎性 > 證據可得性」。

**鐵律：本 stage 之後不做任何追源（source-trace）與抽取（extract）。**選中的 topic
由使用者在本機 session 點名（「research topic N」）才跑完整流程。Routine 一律不呼叫
`get_extraction_rules`、不產 intermediate JSON 草稿。

### Stage 4 — Thesis 到期核查（併入原季度 monitor，到期制）

1. 讀 `thesis/lifecycle.json`。**只對到期的 thesis**（`next_check` <= 今天，或
   `status = review_required`）執行核查；未到期的在報告列一行下次核查日即可
2. 對每條到期 thesis：
   - 讀 memo 裡的 `disproof_condition`，用 web search 查過去一個核查週期內有無觸發跡象
   - 依下表分級（財務面本機才能查，在報告註明「財務指標待本機
     `python engine_c/checklist.py <TICKER>` 補查」）：

| 情況 | 狀態 | 行動 |
|------|------|------|
| disproof_condition 無觸發跡象 | `active` | 記錄「已核查 <日期>，正常」，next_check += 90 天 |
| 有 leading indicator 朝 disproof 方向移動 | `watch` | check_interval_days 降為 30，next_check += 30 天 |
| disproof_condition 已明確觸發 | `review_required` | **PR 開頭標 ⛔**，48h 內必須人工決策 |
| 使用者已確認 thesis 失效 | `retired` | 記錄推翻原因，建議出場 |

3. 核查後**在週報 PR 分支裡更新 `thesis/lifecycle.json`**（`last_checked` /
   `next_check` / `status` / `note`）；merge 週報 = 接受狀態更新。`retired` / `revised`
   的轉換必須由使用者明示，routine 只能建議

**L7 鐵律：** 一條 thesis 有 `disproof_condition` 但沒有「核查頻率」和「觸發後 48h
動作」= 沒裝的火警。發現 memo 缺這兩個欄位時在健康審查段標黃。

### Stage 5 — 系統健康審查

1. **圖層巡檢**——讀 `query/health_audit.py` 的 Cypher 常數，逐一經 MCP
   `run_read_query` 執行（不複製、不手改 Cypher）：
   - `SOLE_SOURCE_WEAK_CYPHER` → sole_source 單一來源清單（L8 weak）
   - `CONFLICT_CANDIDATES_CYPHER` → 衝突候選（over-inclusive 是刻意的；標明
     「準確衝突以本機 `python query/edge_conflicts.py` 為準」）。列出前先比對 repo
     clone 的 `library/resolutions/*.json`（以 `edge_key` + `attribute` 對照）：已有
     核准 resolution 的候選標「已處置」，只有無對應 resolution 的才列為待審
   - `CLAIMS_MISSING_CITES_CYPHER` → 缺 CITES 的 Claim/EdgeAssertion（紅燈）
   - `SCHEMA_STATE_CYPHER` → 圖 schema 版本，與 repo clone 裡
     `mcp_server/graph_mcp.py` 的 `GRAPH_SCHEMA_VERSION` 比對（不一致 = 紅燈）
   - `COMPANY_IDS_CYPHER` → 圖中 Company 清單，與 `loader/load_to_neo4j.py` 的
     `TICKER_MAP` 做差集（未登記 = 黃燈；映射 `None` 是合法的私人公司標記，不算缺）
2. **待印證清單**——讀 `query/single_origin_report.py` 的 `SINGLE_ORIGIN_CYPHER`
   常數，把 `$company_id` 替換為 `null` 後交給 `run_read_query`（既有做法不變）
3. **Provenance**——MCP `get_research_action_status` 檢查有無卡在 `pending_graph`
   的 action（有 = 紅燈）
4. **Repo 檔案檢查**（clone 內直接做，不用網路）：
   - memo 新鮮度：比照 `crons/thesis_freshness_check.py` 的規則（生成日期 >90 天 = 黃）
   - L7 欄位完整性：每份 active memo 檢查「核查頻率」與「48 小時」字樣是否存在
     （與 `query/health_audit.py` 的 `l7_field_gaps` 同一規則）
   - `python scripts/sync_agent_skills.py --check`（漂移 = 紅燈）
5. Engine C 類（snapshot 新鮮度、財務清單可跑性）雲端碰不到 → 統一列入
   「本機待跑清單」段落，指示使用者跑 `python query/health_audit.py --local`

### Stage 6 — Report & PR

1. 把週報寫到 `docs/reports/weekly_scan_<YYYY-MM-DD>.md`，開一個 **PR**（分支名
   `weekly-scan/<YYYY-MM-DD>`，**打上 `weekly-scan` label**，不直接 push main）；
   `thesis/lifecycle.json` 的更新放同一個 PR
2. 週報結構：
   ```
   ## 週審查 — <日期>
   ### ⚡ 30 秒 brief（⛔ review_required 與健康審查紅燈優先；沒有就省略）
   ### 🧭 Topic Digest（排序候選：摘要/來源/影響/理由/建議動作；使用者本機點名才 research）
   ### 📋 Thesis 核查（到期的詳細段；其餘一行「<id>：下次核查 <日期>」）
   ### 🩺 系統健康審查（紅/黃/綠分段；含待印證清單）
   ### Triage 稽核（篩掉了哪些、各自理由）
   ### 建議 onboard 候選（若有）
   ### 🖥 本機待跑清單（`python query/health_audit.py --local`、追源 backlog aging、
       到期 thesis 的財務補查命令）
   ```
3. PR 描述開頭放 30 秒摘要；若 lifecycle.json 有變更，明寫「merge 本 PR 即接受
   thesis 狀態更新」。舊 PR 若仍含抽取草稿，維持「merge 即核准入圖」語義（Stage 0 處理）
4. 純提醒、無可合併產出的事項（如 disproof 觸發跡象）→ 另開 **Issue**（同樣打
   `weekly-scan` label）
5. 追源未果 backlog Issue（rolling，`weekly-scan` label）：本 routine 不再新增項目
   （不做追源了），但要檢查既有項目的 aging——超過 30 天未動的項目在「本機待跑清單」
   提醒一句

## 鐵律

- 繁體中文輸出
- 不確定的訊號標「？」，不假裝確定；某主題本週無動向就直說
- **絕不對本週新訊號做追源或抽取**——topic discovery 是本 routine 研究面的邊界
- **絕不自行呼叫 `load_extraction` 入庫新內容**——只有 Stage 0 處理「已獲使用者
  merge 核准」的舊草稿時才允許呼叫
- lifecycle.json 只能改 `last_checked` / `next_check` / `status` / `note` 四個欄位；
  `retired` / `revised` 轉換只能建議、不能自行寫入
- 找不到任何值得說的事 → PR 照開（週報說明這是 sparse week），讓使用者知道系統有在跑
