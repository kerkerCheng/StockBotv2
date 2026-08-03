# Daily Approval Brief — Codex 本機排程 Prompt（v1.5）

> 現行執行端是 Codex desktop 的 standalone local scheduled task，每日台北 06:30 直接在
> `C:\Users\Cheng\code\StockBotv2` 的 `master` working tree 執行。電腦需保持開機、Codex App
> 保持運行。不要建立 branch／worktree，也不要使用 Claude cloud clone 或遠端 MCP 降級路徑。
> 本檔同時是本機 Claude Code session 的手動共用 runbook；若由 Claude Code 執行，「Claude」指本機
> session，仍直接讀同一 repo／private authorities，不需也不得依賴 Codex automation memory。

## 任務

明確使用 `$daily-brief` skill，產出一份繁體中文、action-first、穩定 pq2 編號的 Daily Brief。
這個本機 task 可直接讀 repo、`.env`、Neo4j、Engine C private runtime、Decision Store 與 Google Sheet；
X／EDGAR、Engine C ETL、today 與 todo pool 都在同一次執行完成。

## 執行契約

1. 先讀 `AGENTS.md` 與 `skills/daily-brief/SKILL.md`。確認目前 branch 是 `master`；若不是就停止並回報，不自行切 branch。若 working tree 有與本 routine
   無關的使用者變更，保留不碰。
2. Windows 一律使用專案 interpreter：`.venv\Scripts\python.exe`，不得用 bare `python`。
3. 依序執行：
   - `.venv\Scripts\python.exe crons\harvest_leads.py`（X＋EDGAR；以 `since_id`／URL hash 去重）
   - `.venv\Scripts\python.exe -m engine_b.cli harvest-health`（列出最新仍未恢復的來源失敗）
   - `.venv\Scripts\python.exe engine_c\etl_yfinance.py`（35 檔 Engine C daily snapshot）
   - `.venv\Scripts\python.exe scripts\daily_beta_snapshot.py --format markdown --risk-view changes`（固定 ETF／權值股 technical refresh
     ＋ Engine D 單一 shared cash pool beta monitor；JSON 只保留 `self_funded_supported_range`，計算固定為
     `Portfolio CASH − cash floor`。cash floor 以上由 Alpha／Beta 共用，sleeve 分配另由 campaign budget、
     Decision sizing、單筆上限與風控決定；不得推導 operating／alpha reserve、planned outflows 或雙 cash view。
     Engine C 保存 adjusted-close 1／5／20-session return；`contingent_credit_available` 顯示未動用額度、
     已借款與估計利息但不算自有現金，`loan_funded_supported_range` 固定人工 review；只呈現、不推定
     draw／choice／fill）。自有現金 baseline 每 5 個完整交易日固定提醒一次，以 Engine C distinct observed
     session count 定錨、不綁 technical signal；貸款不在例行提醒內，提款時間表留待另案人工核准。
     台股 `.TW` 的最新交易日另由 TWSE 官方 `STOCK_DAY_ALL` OpenAPI 校驗；
     Yahoo 落後、TWSE 代碼缺列或 freshness 校驗不可用時，該標的 technical signal／supported range 必須
     fail closed。TWSE 未還權 OHLC 只作最新日期與當日漲跌 reference，不混入 adjusted-close 長期序列。
   - 對今日新增 pending leads 套 `skills/signal-triage/SKILL.md`，用本機 CLI 寫回 triage
   - `.venv\Scripts\python.exe -m engine_b.cli trace-backlog`（顯示 parked 追源未果及下一 trigger；不把一般 backlog 全塞 pq2）
   - `.venv\Scripts\python.exe -m decision_lab today --format markdown`
   - `.venv\Scripts\python.exe -m engine_b.todo sync`
   - `.venv\Scripts\python.exe -m engine_b.todo list`
4. 任何來源失敗都要誠實列出 `fetch_failed`／`parse_failed` 與結構化 `failure_class`；若 fixed entry
   疑似被 sandbox／proxy／本機網路權限擋住，必須以**完全相同的命令**在允許本機網路的權限下重跑一次，
   不得把第一次 `access_blocked` 寫成「零筆新資料」或 `no_result`。同一來源後續成功才算 recovered；
   重跑仍失敗則保留在 `harvest-health` 與健康段落，研究追源另依 `$source-trace` 嘗試一條官方替代路徑。
   beta technical 的 `insufficient_history`／
   `unavailable`／`stale` 也必須列在健康段落，該商品 supported range 歸零但不阻斷其他商品。Capital Authority
   的 cash floor 缺失／stale／FX 錯誤時，單一 self-funded range fail closed 歸零；不得回退到百分比 reserve
   或另一條 cash path。
   routine 的 Google Sheet credential scope 維持 `spreadsheets.readonly`，不得建立或修改 tab／cell。單一來源失敗不
   阻斷其他段落。X token
   只從本機 `.env` 讀取，不得輸出或搬移 token。Beta monitor 的 aggregate risk snapshot 會 append 到
   ignored private JSONL；Daily 只顯示門檻跨越或狀態翻轉，沒有變化就保持靜默。ETF 槓桿 cap／5% 單筆
   上限是 hard block；issuer concentration、alpha 總量與 drawn loan leverage 只 warning。`issuer_loads`
   coverage 必須標 partial，不能宣稱完整 ETF look-through。若命令輸出 `event_search_requests`，以 packet
   的 exact query 執行一次 WebSearch，最多列三個可能原因、對應 direct／indirect 曝險與「未經查證」
   標籤；不註冊 lead、不進 pq1／pq2、不寫任何 Engine authority。使用者要深挖時才另走
   `$lead-intake`／`$source-trace`。
5. 先組出不會因研究失敗而消失的心跳 snapshot，再 best-effort 執行
   `.venv\Scripts\python.exe -m engine_b.cli drain`。每輪上限由 `config/daily_routine.json` 控制；
   使用者已 `go` 且有 dispatch receipt 的 Decision gap work order 優先，再以剩餘 budget 處理 leads；
   tracked tickers 由非 retired lifecycle 與 non-terminal Decision cohorts 自動導出。對最高 priority leads 逐則
   source-trace＋extract，checkpoint `researching` → `action_prepared`。有可核准 graph delta 才 prepare；
   追源未果、原主張被否定或僅屬 Engine C 時變 observation 時 park 並記 outcome，不製造空 RA。
   追源未果的 park 必須帶 `trace_status`／`trace_attempts_ref`／`trace_next_trigger`／`trace_requires_user`；
   一般 event／scheduled retry 留 pq1，只有需要合法 access／付費／人工優先權時才進 `source_trace_review` pq2。
   只有 prepared RA 才進 pq2；triage PASS 與 pq1 自動研究都不代表入圖核准。
   `drain` 本身只列 bounded jobs，不執行研究；brief 必須分開寫出本輪已研究、因 cap／同分 tie-break 延後、
   以及尚未 harvest／triage 的 lead，並在延後項目附 score、排序理由與 `first_seen`，不可只說「沒看到」。
   Decision work order 必須 checkpoint researching；若純唯讀研究即可補齊，產 assessment 後才跑
   research-intent reassess，並以新 decision receipt 結案。若需入圖、Engine C manual observation、thesis
   revise／retire 或其他 authority mutation，先 checkpoint awaiting_approval，完整 packet 回 pq2；不得拿舊
   assessment bare reassess。
6. Graph admission、thesis retire／revise、Google Sheet 真實持倉值、`record-choice`／`record-fill` 永遠
   保留人工 gate；不得因 routine recommendation 推定使用者核准。本機 Codex／Claude Code 是可互換
   executor；任一方收到使用者對 exact pq2 item 的明確核准後都可完成全套 type-aware 動作，但權限與
   完成狀態只認 underlying authority／receipt，不認 agent 身分、memory 或 transcript。
7. 批次回覆中的 `decision_review go` 執行
   `.venv\Scripts\python.exe -m engine_b.todo dispatch <編號>`：只排入 gap pq1、不先 resolve。原項目在
   queued／researching／awaiting_approval 時不重複詢問；只有 parked outcome receipt 或補缺口後的新
   decision receipt 才能結案。`ra_admission go` 必須先完成 apply、把來源 lead 標為 `applied` 並留下
   `research_action_id`／`action_digest`／`focus_company_id`、跑 `scripts\commit_pending_intake.py`，最後執行
   `.venv\Scripts\python.exe -m engine_b.todo complete-ra <todo_n> --digest <完整 action_digest>`；此命令驗證
   durable publication、建立或沿用 Decision cohort 並留下組合 receipt。一般 `todo batch` 不得用 bare go
   先清項目。
   `source_trace_review go` 同樣執行 `.venv\Scripts\python.exe -m engine_b.todo dispatch <編號>`；只將
   exact lead 排回 pq1，不接受 claim、不提高 evidence tier，也不授權購買報告。pq1 prepare 出 RA 後，
   graph admission 仍是另一個 `ra_admission` pq2。
8. 收尾執行 `.venv\Scripts\python.exe scripts\publish_daily_state.py`。這支固定 publisher 只准提交
   `library/leads/pending_leads.json` 與 `library/leads/todo_pool.json`；若 guard 拒絕，保留檔案並在 brief
   回報，不要改用廣泛 `git add/commit/push` 繞過。
9. Daily Brief 的**最終完整 Markdown 已組成後**，以同一份文字呼叫
   `.venv\Scripts\python.exe scripts\publish_daily_brief.py --stdin --summary "<摘要>"`，必要時附
   `--claude-share-url`、`--claude-session-id`、`--codex-thread-id`。這是 Codex／本機 Claude Code 共用的
   provider-neutral outbound publisher；它只傳送，不接受 Discord 指令，不寫 todo／Decision／Graph／Sheet。
   `NOTIFY_DISCORD_TAG_USER_ID` 只用於摘要 mention；`NOTIFY_DISCORD_WEBHOOK_URL` 只從本機 `.env` 讀取。
   publisher 會以 `brief_digest + channel_alias` 去重、分段傳完整 Markdown、保存 private delivery receipt，
   每段最多重試 3 次。通知失敗必須列 `delivery_failed`／`not_configured` 但不能阻斷 brief；不要用
   `--strict` 於排程流程。

## 輸出

只用 `library/leads/todo_pool.json` 的既有穩定編號；不得依 section 或當日排序重新編號。

每個 active pq2 item 不得只列短標題或 `co:*` ID。先給一句 TL;DR，再寫完整公司／ticker、誰供應誰、
產品／材料／技術、事件成熟度、投資意義、證據與反證邊界，以及 `go` 實際授權的 action type。
queued／researching／awaiting_approval 改列狀態更新，不重複要求 `go`。

輸出第一行**必須**是帶執行日期的標題 `# Daily Brief YYYY-MM-DD (Asia/Taipei)`，日期取本機
Asia/Taipei 當日；沒有日期的 brief 視為未完成輸出（多份 brief 並排時要能一眼分辨是哪一天）。

```text
# Daily Brief <YYYY-MM-DD> (Asia/Taipei)

## 需要你動作
[N] <type> — <完整公司／ticker 與主題>
TL;DR：<誰、對誰、做了什麼>
成熟度／投資意義：<announcement／sampling／qualification／capacity／volume／revenue>
證據邊界：<一手來源、反證、不能推論什麼>
go 授權：<bounded research／exact graph admission／manual observation／thesis review>

## 新 leads（依 priority）
<僅列 pq1 進度／失敗；raw lead 不占 pq2 編號。每筆 `parked` 必須列完整主詞／ticker、`parked_reason`、
`trace_status`、`trace_next_trigger`、`trace_requires_user`、是否產生 prepared RA；`original_obtained` 要說明
已取得原文但屬時變 observation／無唯一 graph delta，`isolated_tier_3`／截圖／paywall 要說明缺哪份一手原文。>

## Beta capital observation（無 pq2 編號）
TL;DR：<約 30 年後 retirement_net_terminal_wealth 目標；今日哪些標的可人工評估；最重要的動態風控 warning>
例行提醒：<每 5 個完整交易日一次；本期是否到期；只涵蓋自有現金，貸款不在提醒內>
自有現金可部署：<Portfolio CASH − cash floor；Alpha／Beta 共用>
本輪可評估上限：<同一主路徑經 technical 節奏與 risk caps 後的 ceiling；不是下單金額>
未動用貸款額度：<另列已借款與估計利息；明標不算自有現金、未納入本輪上限；不在例行提醒內，貸款投入仍 manual_review_required>
<先直接回答「今天是否應啟動人工投入評估」，再列一次全局例行日期、自有現金與投組 hard caps。表格逐列比較主力 QQQ／TQQQ／LON:VWRA／SOXX／00631L.TW／2330.TW／00981A.TW；欄位固定為「標的｜系統動作｜每檔 TL;DR（商品自身價格）｜相對結論｜個別例外／上限」。若全部只有 baseline，明說沒有證據可排首選。個別欄只放 freshness、單輪預算、槓桿容量與重疊排序等確實因商品而異的條件。pace 仍須說明是該 sleeve 單輪 campaign budget 比例。系統動作只能用 `CONTRIBUTE REVIEW`（可新增評估，不是買進）、`HOLD`（維持／等待）、`PAUSE CONTRIBUTION`（暫停新增）。每列 TL;DR 必須包含 🟢可評估／🟡冷卻／⚪觀察／🔴資料不足文字燈號、商品自身 RSI、1／5／20 日漲跌、距高點或趨勢／回檔；signal benchmark 與商品不同時須明寫，例如 TQQQ 自身價格但節奏訊號看 QQQ。不得只列 raw 數字；個股與其他仍可縮成摘要，但每檔保留一列焦點>

## 健康／資料降級
<本次 harvest、Engine C、beta technical、Neo4j、Sheet 的失敗或缺口；無則寫正常>

## 無事項目
<NO ACTION 類別>

回覆：`<編號…> go｜drop｜pending`（例：`13 17 go 10 16 pending`）
```

Codex desktop 若支援 inline mobile visualization，Beta 區依「自有現金可部署／本輪可評估上限／未動用
貸款額度 → 風險燈號 → 標的燈號」層級呈現；不支援時輸出等價 Markdown。不得輸出模糊的「名目槓桿」：
內部 `nominal_weight` 顯示為「槓桿 ETF 資金占比」，乘上 2x／3x 的 `effective_weight` 顯示為
「換算槓桿曝險」。Issuer look-through coverage 為 partial 時顯示「已知至少 X%」。不得用未解釋的斜線並列兩個 cash view。

即使無新事項，也輸出 `NO ACTION + 日期` 心跳。Daily brief 不另存 report；稽核由 todo log、leads
狀態機、Decision Store 與窄 state commit 承擔。
