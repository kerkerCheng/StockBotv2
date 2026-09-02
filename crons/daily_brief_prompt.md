# Daily Approval Brief — Codex 本機排程 Prompt（v1.7）

> 現行執行端是 Codex desktop 的 standalone local scheduled task，每日台北 06:30 直接在
> `C:\Users\Cheng\code\StockBotv2` 的 `master` working tree 執行。電腦需保持開機、Codex App
> 保持運行。不要建立 branch／worktree，也不要使用 Claude cloud clone 或遠端 MCP 降級路徑。
> 本檔同時是本機 Claude Code session 的手動共用 runbook；若由 Claude Code 執行，「Claude」指本機
> session，仍直接讀同一 repo／private authorities，不需也不得依賴 Codex automation memory。

## 任務

明確使用 `$daily-brief` 與 `$alpha-status` skill，產出一份繁體中文、action-first、穩定 pq2 編號，
並含完整 Alpha 四個 pane 的 Daily Brief。
這個本機 task 可直接讀 repo、`.env`、Neo4j、Engine C private runtime、Decision Store 與 Google Sheet；
X／EDGAR、Engine C ETL、today 與 todo pool 都在同一次執行完成。

## 執行契約

1. 先讀 `AGENTS.md`、`skills/daily-brief/SKILL.md` 與 `skills/alpha-status/SKILL.md`。確認目前 branch 是 `master`；若不是就停止並回報，不自行切 branch。若 working tree 有與本 routine
   無關的使用者變更，保留不碰。
2. Windows 一律使用專案 interpreter：`.venv\Scripts\python.exe`，不得用 bare `python`。
   Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox；Daily 的唯一權限來源是
   `.codex/rules/stockbot-automations.rules` 的窄 fixed entry。下列連外命令第一次呼叫就用
   `require_escalated` 命中 exact outside-sandbox rule，不得先在 sandbox 製造可預期失敗再升權重重跑，也不得放行整個 PowerShell、
   Python、Git 或 working tree。fixed entry 是 `crons\harvest_leads.py`、`engine_c\etl_yfinance.py`、
   `fetchers\edgar.py`、`fetchers\mops.py`、`scripts\daily_beta_snapshot.py`、`engine_b.cli list`、`engine_b.cli drain`、
   `scripts\catalyst_watch.py`、`scripts\alpha_purity_snapshot.py`、`scripts\outcome_if_settled_today.py`、`scripts\prepare_research_action.py --action-file`、`decision_lab today`、
   `engine_b.todo sync`、`engine_b.todo work`、`scripts\publish_daily_state.py`、`scripts\publish_daily_brief.py`。
   十六條 rule 是單一 authority，不是 primary＋fallback 兩套權限。`engine_b.todo work` 只 checkpoint 已由使用者
   exact `go` 且已有 `dispatch_ref` 的 decision-review work order；不得用它代替 `dispatch`／`resolve`／`reassess`。
   若 exact rule 未匹配、升權限被拒或命令
   仍回 `access_blocked`，保留 failure 並 fail closed，不得改用更寬 rule 或手動重跑。權限正確後若仍發生
   暫時性 transport error，只讓該命令既有的 bounded、idempotent retry 跑完作最後一步；不得在 routine
   層重跑整個 fixed entry、整份 Daily Brief 或已 checkpoint 的工作。retry 用盡後照樣 fail closed。
   `harvest-health`、queue list／count、JSON 檢查等純本機唯讀命令維持 sandbox。
3. 依序執行：
   - `.venv\Scripts\python.exe crons\harvest_leads.py`（X＋EDGAR；以 `since_id`／URL hash 去重）
     ⚠ **writer lock（2026-09-02）：** harvest 開跑會 acquire 排程側 writer lock
     （`library/leads/.writer_lock.json`，嵌在既有命令內、非新 entry）。若 exit 3 且 stderr 出現
     `writer_lock_held`＝互動 session 正在寫共用檔——**整輪 Daily 立即中止並保留該結構化 failure**，
     不得跳過 harvest 繼續執行後續會寫 `pending_leads.json`／`todo_pool.json` 的命令（那會繞過鎖）。
     鎖有 90 分鐘 TTL，過期自動可接手；收尾的 `publish_daily_state.py` 會釋放。
   - `.venv\Scripts\python.exe -m engine_b.cli harvest-health`（列出最新仍未恢復的來源失敗）
   - `.venv\Scripts\python.exe engine_c\etl_yfinance.py`（35 檔 Engine C daily snapshot）
   - `.venv\Scripts\python.exe scripts\daily_beta_snapshot.py --format markdown --risk-view changes`（固定 ETF／權值股 technical refresh
     ＋ Engine D 單一 shared cash pool beta monitor；JSON 只保留 `self_funded_supported_range`，計算固定為
     `Portfolio CASH − cash floor`，且 2026-08-29 起它就是**可部署現金本身**、不再乘任何 pace 或單輪比例。
     cash floor 以上由 Alpha／Beta 共用，sleeve 分配另由 `config/target_allocation.json` 的目標配置比例、
     Decision sizing、單筆上限與風控決定；不得推導 operating／alpha reserve、planned outflows 或雙 cash view。
     Engine C 保存 adjusted-close 1／5／20-session return；`contingent_credit_available` 顯示未動用額度、
     已借款與估計利息但不算自有現金，`loan_funded_supported_range` 固定人工 review；只呈現、不推定
     draw／choice／fill）。**beta 不回答「今天該不該投」**，只回答各 sleeve 距目標配置多遠、每檔在什麼水位；
     訊號（三態動作／RSI／MACD／tier／pace／每 5 個交易日的例行提醒）已於 2026-08-29 整組移除，不得復刻。
     台股 `.TW` 的最新交易日另由 TWSE 官方 `STOCK_DAY_ALL` OpenAPI 校驗；
     Yahoo 落後、TWSE 代碼缺列或 freshness 校驗不可用時，該標的行情必須 fail closed 標 `quarantined`
     並現形，不得靜默消失。TWSE 未還權 OHLC 只作最新日期與當日漲跌 reference，不混入 adjusted-close 長期序列。
     主力逐檔表是每日心跳：即使所有 sleeve 都「到位（區間內、無偏好）」、今天沒有任何配置缺口，
     也必須保留。每列明示商品自身的「最新完整交易日 `YYYY-MM-DD`：1日 ±X%」；stale／
     quarantined 時改列 TWSE 等官方 reference 日期、當日漲跌與降級原因，不得把最近收盤寫成即時行情。
   - `.venv\Scripts\python.exe -m engine_b.cli list --status pending --by-priority`，再對今日新增 pending leads
     套 `skills/signal-triage/SKILL.md`，用本機 CLI 原子寫回 triage＋classification。PASS 命令必須帶
     `--content-type`＋`--decision-impact`，`capital_commitment` 另帶 `--payment-direction`；不得只把分類塞進
     `--reason` 自由文字。FILTER 不寫 classification。完成後執行
     `.venv\Scripts\python.exe -m engine_b.cli classification-health`；非零時逐筆列出 active gap，這些 lead
     會由 drain 標為 `withheld_unclassified_lead`，不得以 unknown 排序，也不得安靜 FILTER。default store 的持股／瓶頸 context 任一讀取失敗
     必須 exit 2、fail closed，不得以空集合繼續排序。
   - `.venv\Scripts\python.exe -m engine_b.cli trace-backlog`（顯示 parked 追源未果及下一 trigger；不把一般 backlog 全塞 pq2）
     ⚠ `auto_trigger_reachable=false` 的項目**必須逐筆列出並附 `unreachable_reason`**，不得只回報總數。
     那代表它既不需人工 authority、又沒有任何具名標的可比對，兩種 trace_trigger_kind 都永遠不會命中——
     它看起來在「等事件」，實際上沒有任何機制會讓它前進。這種項目只有三種誠實處置，擇一並寫明理由：
     (a) 主體其實有登記但沒填進機器欄位 → 補 `trace_trigger_entities`；
     (b) 根本沒有可追的 claim（原文即該貼文本身）→ 改 `trace_status=original_obtained` 豁免重排；
     (c) 真的需要人工 access／付費／改優先權 → 設 `trace_requires_user=true` 進 pq2。
     不得原樣留著——那是安靜沉底，而漏掉時沒有人會發現。
   - `.venv\Scripts\python.exe -m decision_lab today --format markdown`
   - `.venv\Scripts\python.exe scripts\catalyst_watch.py`
   - `.venv\Scripts\python.exe -m query.bottleneck`（Alpha Pane 1／2；已可在 sandbox 讀本機 Neo4j，不需要 outside-sandbox rule）
   - `.venv\Scripts\python.exe scripts\alpha_purity_snapshot.py --format markdown --tickers <Pane 1 前段候選 tickers>`（Alpha Pane 1 標的純度；固定 outside-sandbox 唯讀 consumer，正規化市值並讀 analyst_count；不寫 Engine C）
   - `.venv\Scripts\python.exe -m query.coverage_gaps`（Alpha Pane 3；區分真正 chokepoint 缺口與產品名詞）
   - `.venv\Scripts\python.exe scripts\outcome_if_settled_today.py`（Alpha Pane 4；唯讀真實 fill、最新已收盤價與報酬，不 close 或寫 authority）
   - `.venv\Scripts\python.exe -m engine_b.todo sync`
   - `.venv\Scripts\python.exe -m engine_b.todo list`
   - `.venv\Scripts\python.exe -m engine_b.event_watch sweep`（T2 主動輪詢，2026-08-31 sandbox review 後放行：
     命令只讀寫 repo 內 watch registry、無網路無憑證，在 workspace-write sandbox 內、不需 escalation。
     對回傳的每個 watch（上限由 `config/event_watch.json` 的 `sweep_budget_per_run` 決定，現值即 cap）
     用 query hint 執行**一次** WebSearch；命中＝找到 watch 等的事件的可引用來源→依 lead-intake 慣例
     register lead（下輪 triage 處理），**不直接喚醒 pq2、不寫任何 authority**；查完（無論命中）跑
     `.venv\Scripts\python.exe -m engine_b.event_watch sweep --mark-checked` 標記。搜尋失敗 fail-soft
     記入健康段，不阻斷 brief；budget=0 或 config 缺席時本步驟整段跳過。）
4. 任何來源失敗都要誠實列出 `fetch_failed`／`parse_failed` 與結構化 `failure_class`；若 exact rule 未匹配，
   或命令遭 sandbox／proxy／本機網路權限阻擋，保留 `access_blocked` 並讓受影響資料 fail closed，
   不得以第二套 network rule、較寬 prefix 或手動 replay 事後補跑，也不得寫成「零筆新資料」或 `no_result`。
   同一來源後續成功才算 recovered（後續新一輪成功才算，不得把當次 blocked 寫成零筆）；本輪研究追源可另依 `$source-trace` 嘗試一條已在 profile 內的官方替代路徑。
   beta 行情的 `insufficient_history`／
   `unavailable`／`stale` 也必須列在健康段落，該商品的相對水位標為不可信但不阻斷其他商品；
   單檔行情降級**不歸零**共用 supported range。Capital Authority
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
   `.venv\Scripts\python.exe -m engine_b.cli drain`（首次呼叫命中 exact rule）。每輪上限由 `config/daily_routine.json` 控制；
   使用者已 `go` 且有 dispatch receipt 的 Decision gap work order 優先；對選中的 work order，第一次 checkpoint
   `researching` 就以 `require_escalated` 呼叫 exact `.venv\Scripts\python.exe -m engine_b.todo work ...` rule，
   不得先在 sandbox 製造 owner-only verification failure，再以剩餘 budget 處理 leads；
   tracked tickers 由非 retired lifecycle 與 non-terminal Decision cohorts 自動導出。對最高 priority leads 逐則
   source-trace＋extract，checkpoint `researching` → `action_prepared`。SEC 原文需要 repo fetcher 時使用
   `.venv\Scripts\python.exe fetchers\edgar.py ...` 的 exact rule；**台股原文改用 `.venv\Scripts\python.exe fetchers\mops.py --co-id <代號> --kind annual_report`**（公司 IR 網頁是動態載入抓不到，客戶集中度只在 MOPS 年報揭露）；一般公開頁仍可使用 WebSearch／Browser surface。
   有可核准 graph delta 才把 request JSON 寫到 ignored `library/leads/action_drafts/<lead>.json`，再執行
   `.venv\Scripts\python.exe scripts\prepare_research_action.py --action-file library\leads\action_drafts\<lead>.json`；
   這一步只凍結 private staging，不 apply、不寫 Neo4j。prepare 成功後才 checkpoint `action_prepared`；
   追源未果、原主張被否定或僅屬 Engine C 時變 observation 時 park 並記 outcome，不製造空 RA。
   追源未果的 park 必須帶 `trace_status`／`trace_attempts_ref`／`trace_next_trigger`／`trace_requires_user`；
   一般 event／scheduled retry 留 pq1，只有需要合法 access／付費／人工優先權時才進 `source_trace_review` pq2。
   只有 prepared RA 才進 pq2；triage PASS 與 pq1 自動研究都不代表入圖核准。
   `drain` 本身只列 bounded jobs，不執行研究；brief 必須分開寫出本輪已研究、因 cap／同分 tie-break 延後、
   以及尚未 harvest／triage 的 lead，並在延後項目附 score、排序理由與 `first_seen`，不可只說「沒看到」。
   Decision work order 必須 checkpoint researching；若純唯讀研究即可補齊，產 assessment 後才跑
   `--intent paper` reassess，並以新 decision receipt 結案。intent 不再產生任何模擬部位（2026-08-28
   資本表達層已移除）；它現在只決定要不要要求該 lane 的資料完整度，進而影響 `research_status`。
   「系統準不準」改由等權重報酬回答，錨點是 Shadow observation，與 intent 無關。
   只有標的正處於使用者設定的 hold 期間才改回 `--intent research`。
   `--disproof` 必填且必須可觀測、有門檻、有日期（L7 另需核查頻率與觸發後 48h 動作）；它由 agent 起草，
   但必須隨 packet 進 pq2 由使用者確認，不得自我核准。`--expiry` 由催化劑的預期時點決定（催化劑日 ＋1～2 週），
   **不得早於催化劑本身**。若需入圖、Engine C manual observation、thesis
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
9. Daily Brief 的**最終完整 Markdown 已組成後**，先以 UTF-8 寫入 ignored private brief file，再呼叫
   `.venv\Scripts\python.exe scripts\publish_daily_brief.py --brief-file <private-brief.md> --summary "<摘要>"`，必要時附
   `--claude-share-url`、`--claude-session-id`、`--codex-thread-id`。這是 Codex／本機 Claude Code 共用的
   provider-neutral outbound publisher；它只傳送，不接受 Discord 指令，不寫 todo／Decision／Graph／Sheet。
   `NOTIFY_DISCORD_TAG_USER_ID` 只用於摘要 mention；`NOTIFY_DISCORD_WEBHOOK_URL` 只從本機 `.env` 讀取。
   publisher 會以 `brief_digest + channel_alias` 去重、每天建立一個 Forum 討論串並把摘要／完整 Markdown 分段送入同一串，保存 private delivery receipt，
   Windows PowerShell 5.1 的 `$OutputEncoding` 預設為 ASCII，不得用 `Get-Content <private-brief.md> | ... --stdin`
   傳送含中文的 brief；若使用 stdin，必須先明確設定 UTF-8。每段最多重試 3 次。通知失敗必須列 `delivery_failed`／`not_configured` 但不能阻斷 brief；不要用
   `--strict` 於排程流程。
10. task 最終回覆必須原樣輸出第 9 步送入 publisher 的 canonical Markdown，不得在 receipt 回來後另寫
    精簡版、摘要版或刪除 Beta 表格。delivery receipt 可附在完整 brief 後方，但不能取代或重寫任何 section。

## 輸出

只用 `library/leads/todo_pool.json` 的既有穩定編號；不得依 section 或當日排序重新編號。

每個 active pq2 item 的**第一行必須是決策行**：一行寫完「做什麼 — 為什麼是現在 ｜ go 授權什麼，
不含什麼」，使用者不展開下面也能決定要不要展開。⚠ 內容密度不減——決策行是**改閱讀順序**，不是
刪內容：先給一句 TL;DR，再寫完整公司／ticker、誰供應誰、產品／材料／技術、事件成熟度、投資意義、
證據與反證邊界，以及 `go` 實際授權的 action type，全部原樣收在決策行下面。
不得只列短標題或 `co:*` ID。queued／researching／awaiting_approval 改列狀態更新，不重複要求 `go`。

**同型項打包（2026-09-02 使用者定案）：** action type、授權／不含邊界與圖影響句**完全相同**的
多個 item（最常見：一批補證據的 bounded research），共用欄位提升到組層級寫一次，每項只留
一行決策行（公司＋ticker＋具體找什麼＋補哪個分組）；邊界有任何差異就不得併組。
**每個編號整份 brief 只完整出現一次**：四段是編號唯一的家，「無事項目」不得複述已出現的
編號；收尾建議摘要照舊列編號＋一句理由，但不重述內文。

決策行的「不含」欄不是修辭：`go` 一律只授權該項自己的 action type，最相鄰的下一步
（研究 `go` 不含入圖、入圖 `go` 不含 thesis mutation、任何 `go` 都不含 live）必須逐項寫出來，
否則使用者要靠記憶區分授權邊界。

決策行下第二行固定是**圖影響一句話**（2026-08-31）：`ra_admission` 直接取 `todo list` 的
`圖影響：` 行（+N 節點、M 邊、K claims＋來源 tier）；其他類型一句話回答「核准後圖／authority
多了什麼」。`decision_impact` 字彙（`出場條件`/`候選集合`/`排序`/`只是信心`）**不論出現在
pq1 佇列標籤還是排序 pane 的「答案會改變」欄**，該節開頭固定放一行圖例：
`「答案會改變 X」＝該列附帶的下一個研究題，其答案回來時會改變什麼：出場條件（觸發 disproof）>候選集合（清單多/少名字）>排序（誰第一會變）>只是信心（只是更確定）`；
pq1 複合標籤另加後段說明：`後段＝材料是什麼（資本承諾/結構事實/財務事實/內部人/情緒）`。

輸出第一行**必須**是帶執行日期的標題 `# Daily Brief YYYY-MM-DD (Asia/Taipei)`，日期取本機
Asia/Taipei 當日；沒有日期的 brief 視為未完成輸出（多份 brief 並排時要能一眼分辨是哪一天）。

```text
# Daily Brief <YYYY-MM-DD> (Asia/Taipei)
<首屏固定第二行＝watch 計數器（2026-08-31 定案，L14 常駐計數器）：把 `todo sync` 摘要的
「watch N 筆（T1 a／T0 b／可輪詢 c，本輪喚醒 w）」原樣照抄；「等事件」區有項目卻沒有對應
watch 的要逐項點名——那是回到純靠人記得的狀態，必須現形。>

## 需要你動作
[N] <動詞＋主詞：這次 go 會讓誰去做什麼> — <為什麼是現在，一個子句> ｜ go = <action type>，不含 <最相鄰但未授權的動作>
    TL;DR：<誰、對誰、做了什麼>
    公司／ticker：<完整名稱與代碼，不得只給 co:* ID>
    成熟度／投資意義：<announcement／sampling／qualification／capacity／volume／revenue>
    證據邊界：<一手來源、反證、不能推論什麼>

<決策行範例——一行即可決定要不要展開：>
[14] 補 COHR 的 counter-path 證據 — 最弱軸 technical_causal_link，counter_paths 為空 ｜ go = bounded research，不含入圖

## 新 leads（依 priority）
<僅列 pq1 進度／失敗；raw lead 不占 pq2 編號。每筆 `parked` 必列完整主詞／ticker、`parked_reason`
與是否產生 prepared RA；trace 三欄**只在非預設值時展開**（2026-09-02 定案）——
`original_obtained`＋無 trigger＋不需使用者＝一句「已取一手，無後續等待」收掉；
有 trigger、需要使用者、或 `partial`／`isolated_tier_3` 的才逐欄列並說明缺哪份一手。
同發行人同類文件（如一批 Form 4）彙總一行列數量與唯一例外，不逐筆點名。>

## Alpha 現況（完整四 pane｜無 pq2 編號）
### Pane 1 — 現在要投哪一檔
<`rank_bottlenecks().rows` 的有序清單、明確首選、四維度、相關性警告、每檔 disproof；明標研究判斷且不給尺寸。
**同公司多條邊壓成一列**（2026-09-02 定案）：列最高名次那條邊，其餘瓶頸併同格一句帶過。>
<末尾附產業別分組（2026-08-31 定案）：`python -m query.bottleneck --by-sector` 的每產業 top-3
＋開頭兩條需求錨重疊警告原樣照印；分組解決可視性、分數不可跨組比較，單一排序仍是唯一權威；
「🔴 無需求錨」與空產業組（如記憶體/機器人/稀土——sub 覆蓋未及）要現形，那是研究缺口不是省略對象。>
### Pane 2 — 該去補誰的證據
<同一次輸出的 `structural_rows`；點出與 Pane 1 的排名差異及最高 ROI 補證據題目。
**已在「需要你動作」出現過的研究題只引用編號**（2026-09-02 定案），不重述理由；
本 pane 的價值是沒有 pq2 編號的結構缺口。>
### Pane 3 — 哪裡還是空白
<`query.coverage_gaps`；分開真正 chokepoint 研究缺口與抽取產生的產品名詞，只把前者轉成研究題目。
**缺口清單改「計數＋較昨變動」**（2026-09-02 定案），有變動才點名節點；完整清單附查證命令，不逐日重印。>
### Pane 4 — 部位與問責
<上線標的／可量測／結案歸因計數器、真實 fill／現價／損益／epoch／disproof、錨點樣本效度與 alpha live 監控覆蓋缺口>
<四個 pane 每列都標答案會改變 `候選集合`／`排序`／`出場條件`／`只是信心`；即使全部 `MONITOR` 或無新事件也不得省略。>

## Beta capital observation（無 pq2 編號）
<**輕量版面（2026-09-02 使用者定案：投入頻率約半年一次）——無 TL;DR 段**，目標句收斂為本行：
約 30 年後 `retirement_net_terminal_wealth` 最大化；本報告不判斷「今天該不該投」、不給金額或時間表。固定四塊：
① 一行資本狀態：「自有現金可部署 <Portfolio CASH − cash floor；Alpha／Beta 共用> ｜ 未動用貸款額度 <amount>／已借款 <amount>／月息約 <amount>（不算自有現金；**貸款 tranche 不適用配置建議**，仍 manual_review_required）」。
② 「目標配置差距」表（讀 `config/target_allocation.json`）：欄位「Sleeve｜目標｜容忍區間｜實際｜差距｜狀態」，分母是已投入的非現金部位，band 是容忍區間不是 gate，區間內即「到位」。**不加**「低於目標可優先補」複述行（狀態欄已講）。只給差距不給金額；再平衡只用新錢補低格、不賣出。
③ 兩條相關性警告每天講一次、各一行：(a) alpha 與 beta 是同一個 AI 賭注，分 sleeve 不代表風險獨立；(b) TSMC look-through 已知至少約 28%，高於 0.25 warning，`issuer_loads` 恆 partial。
④ 主力逐檔表 QQQ／TQQQ／LON:VWRA／SOXX／00631L.TW／2330.TW／00981A.TW，欄位固定「標的｜行情狀態｜行情心跳（自身價格）｜相對水位（自身價格）｜sleeve 狀態」；心跳寫「最新完整交易日 YYYY-MM-DD：1日 ±X%」再加 5／20 日，相對水位列 52 週區間位置（主要）、距 52 週高點、距 SMA200（2026-09-02 使用者定案：表格橫向可滑，欄位保留完整；輕量化砍的是段落與重複敘述，不是表格欄位）。主力表在沒有任何配置缺口、全部 sleeve 到位時仍強制保留。燈號只表達資料狀態、不表達投入建議（🟢行情正常／🔴資料不足／⚪歷史不足；🟡 與「可評估／冷卻／暫停新增」等舊語意已於 2026-08-29 廢止，不得回填）。52 週區間位置取自商品**自身**價格序列（TQQQ 不冒用 QQQ、00631L／006208 不冒用 0050）；水位**只呈現、不參與排序、不換算金額**，不得用 RSI／MACD 等動能指標表達水位；表末固定一行「長期上漲的標的多數時間落在高位是正確資訊，不是該等回檔的訊號」。stale／quarantined 改列官方 reference 日期、當日漲跌與降級原因。portfolio risk threshold 只在實際跨越時出現一行，沒跨越整句省略（drawn loan 等既有 warning 照常）。>

## 健康／資料降級
<本次 harvest、Engine C、beta technical、Neo4j、Sheet 的失敗或缺口；無則寫正常>

## 無事項目
<`MONITOR` 類別——今天不需要複查，依 review 日曆追蹤即可。**不得複述已在四段出現的編號**
（2026-09-02 定案）；沒有四段未涵蓋的獨有內容時整段省略。>

## 建議摘要（收尾必附；AGENTS.md「建議只由 pool ground truth 導出」）
<go／drop／pending／不動 各一行，列編號＋每個編號一句理由。推薦 go 前必須答得出
「go 會讓哪個數字變」（L14）——receipt 已判定 bounded research 解不了的不得列入 go，
改列 pending＋trigger 或把 scope 問題直接問出來；推薦 drop 前必須讀 pool 實值
（source_cleared／waiting_on／deferred_at），collector 仍會重新推導的不得建議 drop。
**最後一行單獨給可直接複製的批次指令**（如 `252 253 256 257 go 255 pending`）。>

回覆：`<編號…> go｜drop｜pending`（例：`13 17 go 10 16 pending`）
```

Codex desktop 若支援 inline mobile visualization，Beta 區依「自有現金可部署／未動用貸款額度 →
目標配置差距 → 相關性警告 → 風險燈號 → 標的行情狀態」層級呈現；不支援時輸出等價 Markdown。不得輸出模糊的「名目槓桿」：
內部 `nominal_weight` 顯示為「槓桿 ETF 資金占比」，乘上 2x／3x 的 `effective_weight` 顯示為
「換算槓桿曝險」。Issuer look-through coverage 為 partial 時顯示「已知至少 X%」。不得用未解釋的斜線並列兩個 cash view。

即使無新事項，也輸出 `MONITOR + 日期` 心跳。Daily brief 不另存 report；稽核由 todo log、leads
狀態機、Decision Store 與窄 state commit 承擔。
