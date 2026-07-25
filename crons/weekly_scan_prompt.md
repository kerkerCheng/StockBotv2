# Weekly 審查 — Cloud Routine Prompt

> 這份 prompt 由 claude.ai 的 cloud routine 每週觸發執行（台北時間 06:00，避開互動 session 的用量窗口）。
> 執行環境是 Anthropic 雲端沙盒：有整份 repo 的 clone、有 web search、有 `stockbotv2-graph`
> MCP connector（讀寫知識圖譜的唯一管道）。**連不到使用者本機的任何東西**（Engine C SQLite、
> 本機檔案）——需要圖譜一律走 MCP 工具。
> 設計出處：`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` 的 U7，
> 2026-07-18 refine：研究降級為 topic discovery、併入 thesis 生命週期核查與系統健康審查。

## 定位（先讀這段）

本 routine 是**審查與發現**，不是研究。它做三件事：
1. **Topic discovery（發現未知）**——掃訊號、聚類成 topic、排序給使用者選；**絕不自行追源或抽取**。
   這是 daily 做不到的：daily 只處理**設定好的來源**（RSS/EDGAR watch），weekly 掃你**還沒在 watch
   清單裡**的新公司/新題材。被選中的 topic 由使用者本機說「research topic N」才啟動完整流程。
2. **系統健康審查**——跑 `query/health_audit.py` 的 Cypher 常數 + repo 檔案檢查，
   回報圖譜／memo／管道的紅黃綠狀態。
3. **唯讀 lifecycle 到期提醒（backstop）**——讀 `thesis/lifecycle.json` 比對到期（next_check<=今天 或
   review_required），在報告列出提醒。**只讀不寫**：正式的 disproof 評估與 `last_checked`／`next_check`／
   `status` 更新需人工判斷（retired/revised 只能使用者明示），由使用者**本機手動**複查更新——weekly 與
   daily 都**不寫** lifecycle.json（plan v1.1 R17/R18）。

> **與 daily routine 的分工（v1.1，2026-07-24）：** 每日 harvest／triage／pq1 drain／今日決策佇列
> （MCP `get_decision_brief`）／等 apply 的 RA／到期 thesis 唯讀 surface 已移交
> `crons/daily_brief_prompt.md`（每日 06:30，**輸出到 Claude app、無 GitHub UI、批次語法核准**）。
> Weekly＝**發現未知（topic discovery）＋系統健康審查＋Stage 0 legacy PR gate＋唯讀 lifecycle 到期
> 提醒**。lifecycle 正式狀態更新**不再由 weekly PR 寫入**——改由 SessionStart hook＋本 weekly 雙重
> 提醒到期，使用者本機手動複查更新（判斷留人）。

## 執行流程

### Stage 0 — 前置與遺留維護

1. 讀 `config/themes.txt` 取得活躍主題清單（`#` 開頭與空行忽略）
2. 讀 `skills/signal-triage/SKILL.md`——Stage 2 的判斷標準全在裡面
3. 呼叫 MCP 工具 `get_graph_context` 或 `run_read_query` 任一，確認 MCP 連線正常；
   連不上時不要卡住——跳過所有需要圖的步驟、在報告開頭標明 MCP 不可用
4. **（已退場，2026-07-25）** 原本的「merged-PR 即核准入圖」gate 已隨 GitHub UI 一起退場：
   本 routine 自 2026-07-18 起就不產抽取草稿，且入圖核准已改為對話式（daily brief 的
   `go <編號>` → `apply_research_action`）。**不要再掃 PR、不要再呼叫 `load_extraction`。**
   殘留的舊 `weekly-scan` PR（如 #6）是純報告、無草稿，由使用者自行關閉即可。

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

### Stage 4 — Thesis 到期提醒（唯讀 backstop；不寫 lifecycle.json）

> v1.1（2026-07-24）：本 stage **只讀不寫**。SessionStart hook（`crons/thesis_freshness_check.py`）
> 已在使用者開任何 session 時提示 lifecycle 到期；本 weekly stage 是**backstop**——萬一某週沒開
> session，週報也提醒一次。**lifecycle 的正式狀態更新（disproof 評估、`last_checked`／`next_check`／
> `status`、retired/revised）需人工判斷，由使用者本機手動做——weekly 不再寫 lifecycle.json。**

1. 讀 `thesis/lifecycle.json`。列出到期的 thesis（`next_check` <= 今天，或 `status = review_required`）；
   未到期的列一行下次核查日即可
2. 對每條到期 thesis 可做一次**輕量** disproof web search，把發現寫進報告（供使用者本機複查時參考）；
   `review_required` 在報告開頭標 ⛔
3. **不修改 `thesis/lifecycle.json`**——只在報告提醒「以下 thesis 到期，請本機手動複查更新」。

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

### Stage 6 — Report（輸出到對話，不開 PR）

> **v1.1（2026-07-25）：不再開 PR。** 使用者已決定不透過 GitHub PR/Issue 介面看東西——
> 週報的**主要輸出就是本次 session 的回覆內容**（呈現在 Claude app，與 daily brief 一致）。
> 同時把週報**直接 commit 到 master** 的 `docs/reports/weekly_scan_<YYYY-MM-DD>.md` 留存
> （push 照常，只是不走 PR review）。**不再開分支、不再打 label、不再有 merge 即核准的語義。**
> 本 routine 不寫 `thesis/lifecycle.json`（見 Stage 4）。

1. 週報內容作為本次 session 的回覆完整輸出；同時寫入
   `docs/reports/weekly_scan_<YYYY-MM-DD>.md` 並直接 commit/push 到 master（僅此報告檔）
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
3. 回覆開頭放 30 秒摘要（⛔ 與紅燈優先）。**不開 Issue、不打 label**——需要使用者動作的
   提醒（如 disproof 觸發跡象、追源 backlog aging 超過 30 天）直接列在週報的
   「本機待跑清單」段，使用者在對話中處理
4. 追源未果 backlog：本 routine 不新增項目（不做追源），但檢查既有項目 aging 並在
   「本機待跑清單」提醒

## 鐵律

- 繁體中文輸出
- 不確定的訊號標「？」，不假裝確定；某主題本週無動向就直說
- **絕不對本週新訊號做追源或抽取**——topic discovery 是本 routine 研究面的邊界
- **絕不自行呼叫 `load_extraction` 入庫新內容**——入圖一律由使用者明確核准
- **不寫 `thesis/lifecycle.json`**（見 Stage 4）：到期只做唯讀提醒，狀態更新由使用者本機手動
- 只 commit 週報檔本身（`docs/reports/weekly_scan_<日期>.md`），不碰其他檔
- 找不到任何值得說的事 → 週報照出（說明這是 sparse week），讓使用者知道系統有在跑
