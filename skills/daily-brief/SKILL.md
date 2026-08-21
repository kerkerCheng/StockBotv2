---
name: daily-brief
description: >
  每日核准迴路：把 harvest → triage → pq1 自動研究 → 今日決策 → 到期 thesis 聚合成一份
  action-first 的 Daily Approval Brief，使用者用一行批次語法（`1 3 7 go 4 drop 5 6 pending`）
  核准。當使用者說「daily brief」「今天有什麼要處理」「跑每日摘要」「有哪些待判斷」「今天需要
  動作嗎」時使用。三道閘門不放寬：graph admission 必經核准、深挖由 priority/使用者驅動但入圖仍
  核准、live 資本永遠人工。Scheduled run 可自動 pq1 到 prepared，但不建 decision、不下單、不自動入圖。觸發詞：daily brief、
  每日摘要、今天有什麼、待判斷、今天需要動作嗎。
---

# Daily Approval Brief Skill（v1.6）

## 定位一句話

**每天一份 action-first brief；routine 先把 PASS 線索研究成 prepared RA，使用者只核准完整 pq2。**

系統做便宜的 harvest／triage，再依 priority 自動 drain pq1 到 prepared；人工判斷要不要入圖。
無事時 brief 是一行 `NO ACTION`。三道閘門永不自動：graph
admission 必經核准 exact 對象、深挖由 priority 排序但入圖仍核准、live 資本永遠人工。

> **介面是對話，不用 GitHub UI。** 現行排程是 Codex desktop local scheduled task；本機 Claude Code
> session 也可手動執行同一流程，直接讀 repo、private runtime 與 `todo_pool.json`。本階段提到 Claude
> 預設就是 Claude Code 本機；cloud session＋MCP 是備援，只保留
> `get_decision_brief`／`record_lead_decision` 等既有受限路徑，不要求與本機完全等權。
> 決策與 private authority 寫入只在本機；所有需要使用者決策的項目一律先進統一待辦池，brief
> 不自行重編號。pq1／pq2 定義見 CONCEPTS.md。

---

## 執行流程

### Step 1 — 本機資料更新（零 token）

```powershell
& '.venv\Scripts\python.exe' crons\harvest_leads.py
& '.venv\Scripts\python.exe' -m engine_b.cli harvest-health
& '.venv\Scripts\python.exe' engine_c\etl_yfinance.py
& '.venv\Scripts\python.exe' scripts\daily_beta_snapshot.py --format markdown --risk-view changes
```

第一支抓 X＋RSS＋EDGAR watch 新項，以 `since_id`／URL-hash 去重；第二支刷新 Engine C financial snapshots。
第四支對固定 ETF／權值股 universe 刷新 Engine C TechnicalObservation，再由 Engine D 產
`HOLD / PAUSE CONTRIBUTION / CONTRIBUTE REVIEW`。Runtime／JSON 只保留一條
`self_funded_supported_range`：共同可投資現金池固定等於 `Portfolio CASH − cash floor`，cash floor 以上
全部可供 Alpha 與 Beta 使用。不得再推導 5% operating reserve、3% alpha reserve、planned outflows，
也不得恢復 Sheet／household 雙 cash view。Alpha／Beta 如何分配由各自 campaign budget、Decision sizing、
單筆上限與風控另外決定，不能用 cash reserve 偷渡固定 sleeve 比例。
`Capital Authority` 以 `spreadsheets.readonly` 只讀 `cash_floor` 與 `credit_facility`；cash floor 缺失、stale 或 FX
錯誤時，單一 self-funded range fail closed 歸零。`contingent_credit_available` 只顯示為「未動用貸款額度」，
另列已借款與估計利息，明標不算自有現金、未納入本輪上限；
`loan_funded_supported_range=manual_review_required`。Portfolio cash 仍是自有 cash 唯一 authority，undrawn
credit 不進 NAV／cash／allocation。technical／capital telemetry 不進 pq1，recommendation
不推定 choice／fill，也不推定 draw，且不寫 Google Sheet。fetch／parse 失敗各記 harvest_log；
自有現金 baseline 每 5 個完整交易日固定主動提醒一次，週期由 Engine C 全部 distinct observed sessions
定錨，不綁 RSI／MACD／tier；資料不足仍歸零。貸款不在例行提醒內，提款時間表留待另案人工核准。
**解析失敗 ≠ 無新文**。每筆失敗必須保存 `failure_class`；最新一次仍失敗的來源由
`harvest-health` 持續顯示。Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，
因此 Daily 的唯一權限來源是 `.codex/rules/stockbot-automations.rules` 的窄 fixed entry；不得再用 project
permission profile 當成 scheduled primary path。下列連外命令**第一次呼叫就用 `require_escalated` 命中 exact
outside-sandbox rule**，
不是先製造可預期的 `access_blocked` 再以升權重重跑；不得放行整個 PowerShell、Python、Git 或 working tree。
fixed entry 包含
`crons\harvest_leads.py`、`engine_c\etl_yfinance.py`、`fetchers\edgar.py`、
`scripts\daily_beta_snapshot.py`、`engine_b.cli list`、`engine_b.cli drain`、
`scripts\catalyst_watch.py`、`scripts\prepare_research_action.py --action-file`、
`decision_lab today`、`engine_b.todo sync`、`scripts\publish_daily_state.py` 與
`scripts\publish_daily_brief.py`；十二條 rule 就是單一 authority，不是 primary＋fallback 兩套來源。
`query.bottleneck`、harvest health、trace backlog、todo list 與 JSON 檢查已可留在 sandbox；使用者核准後的
apply／reassess／complete-ra／commit intake 不加入 unattended rule，仍走 type-aware 人工 gate。
若 exact rule 未匹配、升權限被拒或命令仍出現 `access_blocked`，保留結構化 failure、讓受影響資料 fail closed，
不得改用第二條更寬 rule、手動重跑或改寫成「零筆」／`no_result`。權限正確後若仍發生暫時性 transport error，
只允許該命令**既有的 bounded、idempotent retry 作最後一步**（例如 TWSE bounded retry、Discord 每段最多
3 次）；不得在 routine 層重跑整份 fixed entry、整份 Daily Brief，或重做已 checkpoint 的研究／authority
mutation。retry 用盡後照樣保存 failure 並 fail closed。
`harvest-health`、queue list／count、JSON 檢查等純本機唯讀命令維持 sandbox。
`insufficient_history`／`unavailable`／`stale`
也必須在健康段落明示並讓受影響的
technical 或 self-funded range 歸零。Windows 本機與
scheduled task 一律使用 repo `.venv`，不要依賴父 shell 是否剛好 activate。
Engine C 同一筆 observation 保存 adjusted-close 的 1／5／20-session return；Engine D 必須分開保存
signal benchmark 與商品自身價格序列。TQQQ／00631L 等可使用未槓桿 benchmark 決定 timing／pace，但人類
看到的 return、RSI、drawdown 與均線熱度必須來自該商品自身 provider symbol。Engine D 再把這些資料組成 Mobile-friendly
燈號。燈號必須配 `可評估／冷卻／觀察／資料不足` 文字與明確系統動作，且不構成 live permission。
每個商品的 1 日漲跌前必須明列商品自身的最新完整交易日 `YYYY-MM-DD`；即使今日不用啟動投入評估、
本輪可評估上限為 0 或所有標的都是 `HOLD`，主力逐檔行情表仍是每日心跳，不得省略或濃縮成狀態句。
`stale`／`quarantined` 時改列官方 reference 日期與當日漲跌並附降級原因，不得把最近收盤誤稱即時今日行情。
燈號與文字不得在 agent 摘要時省略：🟢 `可評估`、🟡 `冷卻／排序中`、⚪ `觀察`、🔴 `資料不足／暫停新增`。
動作對照固定為：`CONTRIBUTE REVIEW`＝可新增評估（不是買進）；`HOLD`＝維持／等待；
`PAUSE CONTRIBUTION`＝暫停新增。若使用者只看到顏色而看不到動作文字，視為 brief 缺欄。
內部 `etf_leverage.nominal_weight` 的人類標籤固定為「槓桿 ETF 資金占比」；乘上 2x／3x 後的
`effective_weight` 才稱「換算槓桿曝險」，不得再輸出模糊的「名目槓桿」。`pace=0.25` 顯示為
「節奏 25%」，並解釋它是該 sleeve 完整 campaign budget 的四分之一，不是 NAV／現金／持倉的 25%。
Portfolio risk 另以 ignored append-only JSONL 保存 aggregate snapshot：Daily 只顯示門檻跨越／狀態翻轉，
Weekly 才用 `--risk-view full --no-record-risk` 顯示完整快照。硬擋包含 ETF nominal／effective 槓桿 cap、
總曝險 cap、callable debt cap 與 investment policy 的 5% 單筆上限；issuer concentration 與 alpha 總量只警告。
`issuer_loads` 是已知、partial ownership look-through，不是完整 ETF 成分，也不含 Engine A 上游依賴；
coverage 為 `partial` 時一律顯示「已知至少 X%」，不得輸出成完整曝險估計。
若輸出 `event_search_requests`，只對該 packet 做一次 WebSearch，列可能原因、曝險與「未經查證」；不得
建立 lead／pq1／pq2、不得寫 Engine A／C／D authority，深入研究必須另走 lead-intake。

### Step 2 — Triage 新 pending leads（依 signal-triage 判準）

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli list --status pending --by-priority --tracked <已追蹤ticker>
```

default store 的 Google Sheet 持股或 Neo4j chokepoint context 任一不可讀時，priority list 必須 exit 2、
fail closed；不得把持股靜默降成空集合後仍宣稱已依完整 priority 排序。

對每條**新** pending lead 套 `skills/signal-triage/SKILL.md` 五要素判準。判斷完寫回（本機用 CLI、
雲端用 MCP `record_lead_decision`），並帶上 priority flags（供 pq1 排序）：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go   --tier 3 --reason "<要素>" [--contradiction] [--novelty] [--independent]
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --no-go --tier 4 --reason "<為何篩掉>"
```

triage 寬鬆（關聯性與可引用性是硬指標，其餘軟指標命中即 go）；no-go 也記 reason。`tier` 是來源初步
分級，**不是** evidence tier、不影響入圖強度。priority flags（矛盾/反證、新穎、獨立來源）只供 pq1 排序。

### Step 3 — pq1 drain（priority，可續跑）

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli drain
```

`drain` 首次呼叫使用 exact outside-sandbox rule；default store 的 Decision work orders、Google Sheet 持股或
Neo4j chokepoint context 任一不可讀時 exit 2，心跳仍輸出，但本輪不得用降級排序選 pq1。

列出接下來可研究的 bounded jobs。**使用者已明確 go 的 Decision gap work order 優先**，再以剩餘
budget 取 leads（依 priority；pop triaged_go＋researching）。每輪 limit 由
`config/daily_routine.json` 控制；tracked tickers 預設由 lifecycle＋Decision cohorts 自動導出，
需要臨時覆寫時才傳 `--limit`／`--tracked`。依每輪 limit 自動跑
**pq1＝source-trace＋extraction**（`skills/source-trace`＋`skills/lead-intake` 的研究部分），逐則
checkpoint 狀態。Triage PASS 只授權研究、不授權入圖；prepared RA 進 pq2 後才等待使用者 `go`：

`drain` 命令本身只列 bounded jobs，不會自動完成研究。brief 必須分開報告「本輪實際選中並研究」、
「仍在 `triaged_go` 但因本輪 cap／同分 tie-break 延後」與「未出現在候選（例如尚未 harvest／triage）」；
對延後項目列 score、排序原因與 `first_seen`，不可籠統寫成「沒看到」或「優先度不夠」。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> researching        # 開始
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> action_prepared --ref research_action_id=<ra_id>   # prepare 完
```

Decision review 的 `go` 只授權 bounded gap research，先留下跨 session receipt，**不得立刻拿舊
assessment bare reassess**：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo dispatch <todo_n>
& '.venv\Scripts\python.exe' -m engine_b.todo work <todo_n> --to researching --receipt <研究起始ref>
```

若只需讀既有 authorities／生成五軸 assessment，可完成研究後執行 `reassess`，再用新
decision receipt 結案：

```powershell
& '.venv\Scripts\python.exe' -m decision_lab reassess <baseline_decision_id> --assessment <assessment.json> --catalyst "<可驗證催化劑>" --disproof "<可證偽條件>" --expiry <ISO-8601> --intent paper
& '.venv\Scripts\python.exe' -m engine_b.todo work <todo_n> --to completed --receipt decision:<new_decision_id>
```

**`--intent paper` 是預設（2026-08-08 使用者定案）。** paper 是模擬帳本：不碰真錢、不寫
Google Sheet、不建立 live permission，live 仍 100% 人工。改用 paper intent 的理由是
`research` intent **從不 request paper lane**，於是連 coverage 全乾淨的標的也永遠 range 0——
實測 9 個 cohort 全是 research intent，paper ledger 從未被寫過。而一個從不被寫入的模擬帳本
是純成本、零效益：它讓「系統的判斷準不準」永遠無法用證據回答，也就無從決定系統該留該砍。

只有在**明確不想留下模擬部位**時才用 `--intent research`（例如 thesis 正處於使用者設定的
hold 期間）。

**`--disproof` 是必填，不是選填。** 它只是一句話、不依賴任何外部證據，卻是系統第一大
blocker（實測 9 個 cohort 有 4 個卡在 `disproof_missing`）。研究迴圈產 packet、產 work order，
就是不產那句話——這是產出規格缺一欄，不是證據不足。合格的證偽條件必須**可觀測、有門檻、
有日期**，並依 L7 附上核查頻率與觸發後 48 小時動作：

- ✅「到 2027-06-30，IQE 的 photonics／InP 相關營收未出現連續兩季 YoY 成長 ≥20%」
- ✅「Tower 或任何主要客戶公開宣布第二家合格 InP epiwafer 供應商」
- ❌「thesis 被證明是錯的」（循環，不可觀測）
- ❌「股價下跌 30%」（那是價格，不是 thesis 的證據；thesis 可以對而股價先跌）
- ❌「競爭加劇」（沒有門檻，永遠無法判定觸發）

證偽條件由 agent 起草，但**必須隨 packet 進 pq2 由使用者確認**：讓「想證明 thesis 成立」的
同一個 agent 自己決定自己的證偽門檻，是 L8 形狀的自我報告偏誤，會寫出一個永遠不會響的警報。

**`--expiry` 必須由催化劑的預期時點決定，不是固定期間。** `catalyst / disproof / expiry` 是
一組：「我預期 X 在 T 之前發生；沒發生就代表時序假設錯了。」硬規則是 **expiry 不得早於
催化劑的預期時點**——實測 co:axt 的 expiry 是 2026-08-09 而催化劑是 2026-11 初的 Q3 10-Q，
催化劑根本不可能在有效期內發生，這種設定保證產生一次假到期。催化劑有明確日期時取
「該日 ＋1～2 週緩衝」；沒有明確日期時取「下一個可能揭露的時點」，通常是下一次財報。

若結果需要 Engine A 入圖、Engine C manual observation、thesis revise／retire 或其他 authority mutation，
先 checkpoint `awaiting_approval` 並把完整 packet 放回 pq2；人工 gate 完成且取得 receipt 後才 reassess。

pq1 是唯一昂貴階段（web search + 讀文件 + 抽 claim）——priority 決定貴的 token 先花在哪。被 5 小時
限制/中斷後**重跑 drain 從剩下的接**（靠 lead status checkpoint）。有可核准的 graph delta 才 prepare；
若追源未果、原主張被一手資料否定，或結果依 L4 只屬 Engine C 時變 observation，就 park 並記 outcome，
不為了讓每個 PASS 都進 pq2 而製造空 Research Action。drain 最遠到 prepared，**不入圖**。

prepare 前先把「graph delta 涵蓋哪些公司」與「完成後唯一要建立／沿用哪個 Decision cohort」分開。
把唯一 `focus_company_id` 寫入綁定 lead，並讓 `ra_admission` pq2 的 hint 明列
`Decision handoff：co:x`；RA 內其他公司預設只作 evidence／relationship context，不自動建 cohort。
若沒有唯一 focus，先留 pq1 修正；若確實要追多個投資標的，分開提出明確 handoff，不由「入圖多家公司」
推定「全部開始投資追蹤」。

有 graph delta 時，把 research-action/v1 request 寫到 ignored
`library/leads/action_drafts/<lead_id>.json`，再用窄 fixed entry 凍結 server-owned packet：

```powershell
& '.venv\Scripts\python.exe' scripts\prepare_research_action.py --action-file library\leads\action_drafts\<lead_id>.json
```

這支 CLI 只接受該 draft 目錄、重跑既有 extraction／storage／permission validation 並寫 owner-only private
staging；不 apply、不寫 Neo4j、不建 Decision／live permission。只有回 `status=ready` 才可把 lead checkpoint
成 `action_prepared`。SEC 原文若需 repo fetcher，使用 `fetchers\edgar.py` exact rule；其他公開頁可走
WebSearch／Browser，兩者是 shell rules 之外的獨立權限 surface。

每輪 drain 後另列不會被一般 queue 自動撿回的 trace backlog：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog
```

一般 event／scheduled trigger 仍回 pq1；只有 `trace_requires_user=true` 才由 `todo sync` 建立
`source_trace_review`。其 `go` 只 dispatch exact lead 回 pq1，不接受 claim、不提高 tier，也不授權付費。
`trace_next_trigger` 只做人類說明；可執行 linkage 使用 `trace_trigger_kind`＋`trace_trigger_entities`，
kind 目前有兩種：`related_entity_signal`（任何共用具名標的的新 lead）與 `primary_source_signal`
（只有該標的的 tier-1 一手來源才算）。同標的新 lead 通過 triage 時會留下 triggering lead receipt 並重排
不需人工 authority 的 exact parked trace；沒有共同具名 ticker／company_id 時不得靠語意自動喚醒。
`related_entity_signal` 以 `trace_requeue_consumed_entities` 記錄已消化標的，同一標的只喚醒一次——
park 的理由不會因為「又一則提到同一檔的貼文」而改變。

**`auto_trigger_reachable=false` 必須逐筆列出並附 `unreachable_reason`，不得只回報總數。** 那代表它
既不需人工 authority、又沒有任何具名標的可比對，兩種 kind 都永遠不會命中——看起來在等事件，實際上
沒有任何機制會讓它前進。只有三種誠實處置，擇一並寫明理由：(a) 主體其實已登記但沒填進機器欄位 →
補 `trace_trigger_entities`；(b) 根本沒有可追的 claim（原文即該貼文本身）→ 改
`trace_status=original_obtained` 豁免重排；(c) 真的需要人工 access／付費／改優先權 → 設
`trace_requires_user=true` 進 pq2。**不得原樣留著**——那是安靜沉底，漏掉時沒有人會發現。

brief 的 pq1 進度不得只寫「park」或只列數量。每一筆本輪處理的 `parked` lead 至少列：完整主詞／ticker、
`parked_reason`（自然語言）、`trace_status`、`trace_next_trigger`、`trace_requires_user`，以及「是否產生
prepared RA」（通常為否）。`original_obtained` 也要說明「已取得原文但屬時變 observation／沒有唯一 graph delta」；
`isolated_tier_3`／截圖／paywall 則要說明「缺哪一份可逐字核對的一手原文」。park 不得被簡寫成已入圖或
「已完成」；若沒有任何可核對 reason，視為 brief 缺欄而非正常 park。

### Step 4 — 今日決策佇列、alpha 候選與到期 thesis

```powershell
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
& '.venv\Scripts\python.exe' scripts\catalyst_watch.py
& '.venv\Scripts\python.exe' -m query.bottleneck
```

第三支是**買進側**，與第二支的賣出側對稱。它回答使用者實際的選股問題——
「哪個公司佔據了瓶頸、且是市場資金關注的部分」——輸出即
`## Alpha 候選（瓶頸 × 資金關注）` 的唯一排序來源。

⚠ **呈現判準委派給 [`skills/alpha-status`](../alpha-status/SKILL.md)，本檔不再複製一份。**
2026-08-19 本節曾自行維護一份三維度判準，08-21 判準收斂為四維度（新增**客戶端資本承諾**
與**標的純度**）後就地過期而無人察覺——同一份呈現契約有兩個副本時，後改的那份不會回頭
更新前一份（`AGENTS.md`「清單會腐壞，判準不會」）。四維度、禁用指標、相關性警告與
「outcome 0/8 不是拒絕排序的理由」一律以 alpha-status 的 pane 1 為準。

`bottleneck` 的表格直接給出四維度中的前兩項（替代難度／`sole_source`＝瓶頸地位；
需求錨點與距需求端跳數＝資金是否在那條鏈上）。**第 3 項（誰付錢給誰）與第 4 項
（市值／`analyst_count`）不在排序內，必須另看** ——見 alpha-status pane 1。
⚠ **2026-08-19 之前這支從未進入 daily 流程**：`rank_bottlenecks()` 早就把 COHR→NVIDIA
（5/5 sole_source、外部印證、距需求端 2 跳）排在第 1，但 brief 沒有消費端，使用者看不到，
於是 agent 被問「推薦哪一檔」時只能答「無法推薦」。這是 L13「管子只接了一頭」的實例。
它的已知限制必須隨表一起呈現，不得只貼排名：`substitutability` 覆蓋率僅約 16%（沒填的邊
是隱形的）、不含 lead time（難替代 ≠ 換掉要很久）、`documents` 是注意力指標不參與排序。

第二支是**賣出側**：把每筆 decision 已經必填的 `disproof`／`catalyst`／`expiry` 從卡片上的
散文變成每天被檢查的狀態。L7 的原話是「欄位有填但沒有後續流程，等於貼了一個永遠不會響的
火警警報」——這一支就是那個缺掉的流程。它是**條件檢查不是訊號**（只回答「你自己寫下的條件
今天到了沒」，不預測任何東西），因此不受 D7「先量測後放閘」限制。輸出四態：
`設定不完整`／`已逾期`／`即將到期`／`監控中`，**`設定不完整` 排最前面**——它的到期提醒本身
就是假的，先修它才有意義。散文裡的日期**不猜**：只用結構化的 `expiry` 與
`thesis/lifecycle.json` 的 `catalyst_checkpoints`，猜出來的日期會產生「看起來有排程、
其實是編的」提醒，比沒有提醒危險。報表末尾必須顯示「N/M 檔有結構化催化劑日期」——
其餘檔的 `expiry 早於催化劑` 錯誤測不到，**沒抓到問題不等於沒有問題**（L13）。

第一支回今日 `NO ACTION / REVIEW / TRADE / HEDGE`，每個 probe 附**自追蹤變化%**與**evidence_delta**
（material=有觸及 thesis 因果結構的新證據 → 建議 reassess；peripheral=只多週邊 source；none=無變或
純價格波動）。再讀 `thesis/lifecycle.json` 列到期需複查的 thesis。純讀，不建 decision。

### Step 5 — 同步統一待辦池並組 brief（繁中、exception-first、**穩定編號**）

先同步所有 pq2 來源：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync
```

`library/leads/todo_pool.json` 是回覆編號的唯一 authority：項目首次進池時取得編號，直到 resolve 才釋放；
**不得依當日排序、section 或模型輸出重新編號**。用池內原編號把決策佇列／等 apply 的 RA／
到期 thesis／有 material evidence-delta 的 probe 組成 brief，每項附明確指令。無事就一行
`NO ACTION ＋日期`。

### 待核准項目的內容密度

stable pq2 編號後不得只貼短標題或 `co:*` ID。每一個需要使用者決定的 item 至少包含：

1. 一段一句話 TL;DR，直接寫清楚「誰、對誰、做了什麼」。
2. 完整公司名與 ticker（若有），以及供應商／客戶／產品／材料／技術的角色與方向。
3. 事件成熟度（例如 announcement、sampling、qualification、capacity commitment、volume production、revenue）。
4. 為什麼影響投資判斷；證據來源、反證與不能推論的邊界。
5. `go` 實際授權的 action type：排入 bounded research、exact graph admission、manual observation、thesis review，
   或其他明確 authority mutation；不得只寫「核准」。

內容可以 mobile-friendly，但不能把理解成本轉嫁給使用者。queued／researching／awaiting_approval 的 item
改寫為狀態更新，不再要求使用者重複 `go`。

第一行固定是 `# Daily Brief YYYY-MM-DD (Asia/Taipei)`（Asia/Taipei 當日），讓不同天的 brief 可分辨。

```
# Daily Brief <YYYY-MM-DD> (Asia/Taipei)

## 需要你動作
[1] REVIEW — Coherent（COHR）供應鏈缺口
TL;DR：<完整主詞＋關係＋事件>
成熟度／投資意義：<為何現在需要判斷>
證據邊界：<來源＋不能推論什麼>
go 授權：<bounded research／exact authority mutation>

[2] RA admission — AXT（AXTI）→ Coherent（COHR）6 吋 InP substrate
TL;DR：<誰供應誰、產品與技術用途>
成熟度／投資意義：<agreement／qualification／volume／revenue 邊界>
證據邊界：<一手來源與反證>
go 授權：exact graph delta＋已揭露的 Decision handoff
...

## pq1 研究進度（無 pq2 編號）
完成：AXTI 8-K ×3 → prepared `ra_xxx`，已以上方穩定編號 [2] 等核准
park：社群 CPO 推論 → 一手來源未支持，不產空 RA
續跑：尚有 triaged_go ×N
每筆 park 必須附：`parked_reason`、`trace_status`、`trace_next_trigger`、`trace_requires_user`、
以及「是否產生 prepared RA」；每筆尚未 drain 的 lead 必須標明「本輪 cap 延後／尚未 harvest／尚未 triage」
等具體原因與 score，不能只列總數。

## Alpha 候選（瓶頸 × 資金關注｜無 pq2 編號）
TL;DR：<直接回答「今天要不要加碼、加哪一檔」；不得只列清單不給首選>
排序來源：`query/bottleneck.py` 的 `rank_bottlenecks()`（唯一權威；不得用 axis_ceiling／paper target／ELIGIBLE 數量代替）
相關性提醒：<本清單集中在哪個主題；列 N 檔不等於 N 個獨立機會，全買是同一賭注下 N 次>
判斷性質：研究判斷，非回測或統計勝率；尺寸一律不給，由使用者決定
| # | 標的 | 卡在哪（瓶頸邊） | 替代難度 | 證據強度 | 需求錨點／距需求端 | 現在的判斷 | disproof 狀態 |
|---|---|---|---|---|---|---|---|
| 1 | Coherent（COHR） | supplies_to → co:nvidia | 5/5｜sole_source | 外部印證（客戶端出資） | tech:ai_switch／2 跳 | 首選；已持有可加碼 | 已綁定，Q1 FY2027 檢查毛利率 40.2% |
| 2 | … | … | … | 供應商自報（L8 弱） | … | 觀察；等客戶端印證 | 未綁定 → 該補 |

必填規則**以 [`skills/alpha-status`](../alpha-status/SKILL.md) pane 1 為準**，此處只列
daily 特有的兩條：

- 已持有部位必須列 disproof 狀態；`None` 或 lifecycle `expired` 要當成缺口提出。
- 只出**可行動排序**（`rows`）。`structural_rows`（該補誰的證據）與 coverage gaps
  （哪裡是空白）不進 daily——那是使用者主動問「我們缺什麼」時才需要的深度，每天出會稀釋
  brief 的 action-first 性質。要看完整四 pane 請直接呼叫 alpha-status。
- 本段**不得因今天無新事件而省略**，規則同 Beta 主力表。

## 追蹤中的外部事件（無 pq2 編號）
資料源：`& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog`
| 標的／主題 | 在等什麼 | 可自動喚醒 | 已等待 |
|---|---|---|---|
| Agility Robotics（CCXI→AGLT） | 公開 Form S-4 含 Agility 經審計財務，或交易完成取得 AGLT ticker | 是 | 自 2026-08-13 |

必填規則：
- 只列 `trace_status=original_obtained` 或 `partial` **且**有 `trace_next_trigger` 的項目——
  那代表「一手已追過、在等世界產生新事實」，不是研究失敗。
- `trace_requires_user=true` 的**不放這裡**，它們該走 `source_trace_review` 取 pq2 編號。
- ⚠ **本段不得因為「今天沒有新進展」而省略。** 這正是它存在的理由：
  2026-08-20 使用者問「追蹤 X 這麼久，humanoid 的 lead 為何圖裡都沒有」，而 CCXI 那條
  其實被處理得很好——9 筆 filing 逐一取得一手、逐字比對（`agility 0 次、robotics 0 次`）、
  確認 S-4 仍為 confidential submission、設好 `related_entity_signal` 喚醒條件、並連到
  pq2 [74]。問題只在於 brief 僅顯示**當輪** park 的項目，08-13 之後它就再也不出現，
  使用者因此完全看不到系統正在等什麼。這與「bottleneck 排名早就把 COHR 排第一卻沒進
  brief」是同一個病：**做了正確的工作，但產出沒有消費端**（L13）。

## 已持有 alpha 部位的 disproof 追蹤（無 pq2 編號）
| 標的 | 進場 | 現價／損益 | catalyst（何時會知道） | disproof 是否觸發 | lifecycle |
|---|---|---|---|---|---|
逐筆列出 `live_execution_reports` 中的部位。**進場價與 disproof 判準必須同列**，
否則使用者只看得到損益、看不到「當初憑什麼買、什麼情況該認錯」。

## Beta capital observation（無 pq2 編號）
TL;DR：最大化約 30 年後 `retirement_net_terminal_wealth`；technical 只決定新增 timing／pace；列今日可人工評估標的與最重要的動態風控 warning
今天是否投入：<先直接回答今天是否應啟動人工投入評估>
例行提醒：<每 5 個完整交易日一次；本期是否到期；只涵蓋自有現金，貸款不在提醒內；只在此處列一次>
自有現金可部署：<Portfolio CASH − cash floor；Alpha／Beta 共用>
本輪可評估上限：<同一主路徑經 technical 節奏與 risk caps 後的 ceiling；不是下單金額>
未動用貸款額度：<amount／已借款／估計利息／terms status；明標不算自有現金、未納入本輪上限>
貸款投入：不在例行提醒內；提款時間表未建立，仍為 manual_review_required
相對比較：<有無相對加碼證據；若全部只有 baseline，明說沒有證據可排首選>
| 標的 | 系統動作 | 每檔 TL;DR（商品自身價格） | 相對結論 | 個別例外／上限 |
|---|---|---|---|---|
評估日期、可部署現金與投組 hard caps 在表格上方只列一次。每列只保留商品自身的 RSI／1／5／20 日變化／
距高點／趨勢、相對比較結論，以及真正會因標的不同而變化的 freshness、單輪預算、槓桿容量與重疊排序。
每列的 1 日變化必須寫成「最新完整交易日 `YYYY-MM-DD`：1日 ±X%」，不能因今天不是投入評估日而省略；
資料 stale／quarantined 時則顯示官方 reference 日期、當日漲跌與降級原因。
若 signal benchmark 與商品不同，TL;DR 必須明寫（例如「自身價格看 TQQQ；節奏訊號看 QQQ」）。所有 pace
仍是該 sleeve 單輪 campaign budget 比例，不是 NAV 比例。
| QQQ | HOLD | 🟡 自身 RSI 43.2；… | 今日不比較（尚未到投入評估日） | 無；共用條件見上方 |
| SOXX | CONTRIBUTE REVIEW | 🟢 自身 RSI 42.5；… | 例行候選；沒有相對加碼證據 | 本檔人工評估上限 … |
| TQQQ | CONTRIBUTE REVIEW | 🟢 TQQQ 自身漲跌／RSI；節奏訊號看 QQQ | 回檔觀察優先；Signal 尚未驗證 | 槓桿容量 … |

## 低優先（摺疊）
EDGAR Form 4 ×55、較舊 filing——預設摺疊只列數量（要看再展開）

## 無事項目
paper 無異動｜live 無 pending fill｜...

---
回覆：`<編號…> go｜drop｜pending`（例：`3 4 go 5 drop`）
```

pq2／lead priority **不使用顏色維度**（顏色曾混淆 triage 與優先度），一律使用明確指令字串。Beta
technical 區可用配有文字的燈號表達 deterministic state，但不得只靠顏色，也不得把 `可評估` 寫成 `買進`。
Beta 必須使用上述表格，每個 ticker 一列；不能再用一長串 bullet 堆 raw 數字。首屏先回答今天是否啟動投入評估，表格才比較商品。TL;DR 至少回答「商品自身現在在什麼水位、這是趨勢還是回檔、訊號基準是什麼、是否有個別例外」。RSI 區間只是一致的解讀標籤，不改變 `config/beta_policy.json` 的 numeric gate，也不構成 live permission。
`NO ACTION`／非投入評估日也不得刪除主力表；「今天是否投入」只控制 capital discussion 與 ceiling，
不控制行情是否顯示。
Codex desktop 若支援 inline mobile visualization，Beta 區依「自有現金可部署／本輪可評估上限／未動用貸款
額度 → 風險燈號 → 標的燈號」層級呈現；不支援的 executor 必須輸出相同層級的 Markdown，不能因此退化成
raw field names 或省略燈號。
主力首屏依序顯示 `QQQ`、`TQQQ`、`LON:VWRA`、`SOXX`、`00631L.TW`、`2330.TW`、`00981A.TW`；
個股與其他標的縮成 exception-first 摘要。Form 4 與較舊 filing 一律進
「低優先（摺疊）」只列數量——冷啟動 EDGAR seed 偏 Form 4，別淹沒新訊號。

### Step 6 — 批次 dispatch（type-aware）

使用者回 `1 3 7 go 4 drop 5 6 pending`。先讀池中 exact item，再用 deterministic parser 解析，
不自由心證：

Codex／Claude Code 都是可互換的本機 executor，不把 routine、研究或完整 pq2 流程寫死給任一方。收到
使用者對 **exact pq2 item** 的明確核准後，當下 agent 可走完整 type-aware 動作，但必須重新讀
`todo_pool.json` 與 underlying authority；權限與完成狀態綁 action type＋receipt，不綁 provider。上一個 task 的
`memory.md`／transcript 或模型 recommendation 不能授權，也不能證明 item 已執行。兩個本機 agent 不得同時
dispatch 或同時寫同一 working tree。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo list --json
& '.venv\Scripts\python.exe' -c "from engine_b.batch import parse_batch_reply; import json,sys; print(json.dumps(parse_batch_reply(sys.argv[1])))" "1 3 7 go 4 drop 5 6 pending"
```

依編號對應的**項目類型** dispatch（type-aware；動詞不新增任何權限語意）。`todo batch` 不會代做
pq1／apply／reassess；沒有完成 receipt 的 `go` 會失敗並留在池中。必須先完成或 checkpoint 對應動作，
再由 type-specific completion command（或附該類型要求的 receipt）結案，不能先 resolve 再假裝已執行：

| 動詞 | legacy lead | Source trace review | 已 prepared 的 RA | Decision review | 到期 thesis |
|------|-------------|---------------------|-------------------|-----------------|-------------|
| `go` | raw lead 不再進 pq2 | `todo dispatch` 回 pq1；不接受 claim、不授權付費 | **apply 入圖**（見下）＋入圖後自動建 Shadow | `todo dispatch` 排入 gap pq1；不先 resolve、不 bare reassess | 引導複查；authority mutation 仍另核准 |
| `drop` | raw lead 不再進 pq2 | 略過本次人工追源 | 略過該 RA | 略過本次補缺口 | 標記已看、不複查 |
| `pending` | 維持不動、留到之後 brief | 同左 | 同左 | 同左 | 同左 |

`decision_review go` 的原 pq2 項目在研究期間維持 active，但標成 queued／researching／awaiting_approval，
brief 不得再次請使用者 go。只有 `parked` outcome receipt，或補缺口後產生的**新 decision receipt**，才能
結案；舊 baseline decision 不算完成 receipt。

`source_trace_review go` 也使用 `todo dispatch <n>`：原 pq2 在 queued／researching 期間保持 active 但不重複
詢問。只有 prepared action receipt，或誠實的 `trace:<trace_status>` parked receipt 才能結案；前者若需入圖，
仍另建立 `ra_admission` pq2。新報告訂閱／購買需 exact 價格的獨立人工核准。

`ra_admission` 顯示時必須讓 hint 明列唯一 `Decision handoff`。`focus_company_id` 是 pq1 在 RA 凍結前，
依主要投資問題篩出的 cohort 目標，不等於 action 內唯一公司；使用者的 `go` 同時核准 exact graph delta
與已揭露的 handoff。若 hint 顯示未聲明／多個 focus blocker，不得先 apply 再事後補選。

**go 一個 prepared RA ＝入圖**：走既有 `apply_research_action`（本機或 MCP native approval，一次確認）
→ `advance <lead> applied --ref research_action_id=<ra_id> --ref action_digest=<digest> --ref focus_company_id=co:x`
→ `scripts/commit_pending_intake.py` 完成 durable publication → 用同一個 deterministic completion point 驗證
apply／publish 並自動建立（或沿用）Decision Shadow：

```powershell
& '.venv\Scripts\python.exe' scripts\commit_pending_intake.py
& '.venv\Scripts\python.exe' -m engine_b.todo complete-ra <todo_n> --digest <完整 action_digest> [--company-id co:x] [--ticker <T>]
```

`complete-ra` 只有在 RA 為 `pushed`（local-only 則 `applied/not_required`）、所有文件／report receipt 完整、
來源 lead 已 `applied` 且有唯一 `focus_company_id`、Decision handoff 回傳 cohort 後，才以
`action:<id>;digest:<sha256>;commit:<sha|not_required>;cohort:<dc_id>` resolve pq2；中途失敗可安全重跑。
已有 active cohort 時不重複建，後續由 evidence-delta 顯示新 action。**live 決策（record-choice／
record-fill）不在批次動詞集合**——永遠本機明確 flags，不得由 recommendation 推定 choice、choice 推定
fill。系統不連 broker。

Beta 的 `CONTRIBUTE REVIEW` 只是一個當日人工 capital discussion prompt，不因出現在 brief 就取得 pq2
approval、loan draw、choice 或 fill 語意。貸款路徑在沒有 exact draw／instrument／tranche 核准前不得輸出自動金額。
固定例行提醒亦同：它只以自有現金 baseline 提醒使用者評估，不包含或暗示貸款提款。

### Step 7 — 收尾同步

- **本機 scheduled task**：執行 `& '.venv\Scripts\python.exe' scripts\publish_daily_state.py`；它只准提交
  `pending_leads.json` 與 `todo_pool.json`，guard 失敗不得改用廣泛 Git 命令繞過。
- **入圖帳本**：有實際 apply 才另外跑 `scripts/commit_pending_intake.py`。
- **遠端 chat fallback**：`record_lead_decision` 仍由本機 MCP server 窄 pathset commit+push leads.json。

### Step 8 — provider-neutral 單向通知（best effort）

Daily Brief 組成後，Codex 與本機 Claude Code 都呼叫同一支 repo publisher；不得在兩份 hook／prompt
各自複製 Discord 業務邏輯。publisher 只做 outbound，不接受 Discord 的 `go`、交易、入圖或任何核准指令，
也不改變 todo／Decision／Graph／Sheet authority。

把**同一份最終 Markdown**（包含日期、pq2 穩定編號、完整 Beta 表與回覆語法）由 stdin 或私有檔交給：

```powershell
& '.venv\Scripts\python.exe' scripts\publish_daily_brief.py `
  --brief-file <private-brief.md> --summary "<一則 action-first 摘要>" `
  [--claude-share-url <url>] [--claude-session-id <id>] [--codex-thread-id <id>]
```

設定由本機 `.env` 讀取：`NOTIFY_DISCORD_WEBHOOK_URL`（Discord private Forum channel webhook）、
`NOTIFY_DISCORD_TAG_USER_ID`（摘要 mention）、`NOTIFY_CHANNEL_ALIAS`、`NOTIFY_CONTENT_CLASS`、
`NOTIFY_MAX_ATTEMPTS=3`。Webhook secret 不得輸出或進 Git；不需要 Discord bot token、OAuth、Claude API key
或 Codex API key。每份 Daily Brief 先建立一個新的 Forum 討論串，再把摘要與完整 Markdown 分段送進同一串；
私有 SQLite outbox 以 `brief_digest + channel_alias` 去重，保存 `thread_id`／`thread_name` 與每段 delivery attempt receipt。Claude Code session 以可複製
`claude -r <session-id>` 附上；Claude App share URL 能取得才附；Codex 只附 thread ID，第一版不猜
未文件化的 app URI。Windows PowerShell 5.1 的 `$OutputEncoding` 預設為 ASCII，**不得直接使用
`Get-Content <private-brief.md> | ... --stdin` 傳送含中文的 brief；若無法使用 `--brief-file`，必須先明確把
stdin 設為 UTF-8。

發送失敗只回傳 `delivery_failed`／`not_configured` receipt 並繼續輸出 Daily Brief；CLI 預設永遠不以
通知失敗阻斷 routine，只有診斷時才使用 `--strict`。
task 最終回覆必須原樣輸出送入 publisher 的 canonical Markdown；不得在取得 delivery receipt 後另產生
精簡版、摘要版或重新措寫版。receipt 可附在完整 brief 後方，但不能取代、刪除或濃縮任何 section。

---

## 現行本機排程與遠端 fallback

`crons/daily_brief_prompt.md` 是 Codex desktop 每日 06:30 的本機 scheduled task prompt，可直接讀 repo 與
private authorities；本機 Claude Code session 亦可沿用同一 prompt 手動執行；`crons/weekly_scan_prompt.md`
是台北週日 04:00 的本機 weekly prompt。Cloud session＋MCP 不承擔現行排程，只保留遠端 chat／手機
intake 的 fallback；遠端永遠不得取代本機 decision／lifecycle authority。

## 已知會壞的地方（v0，撞到回頭修）

- priority 權重是拍腦袋 v0；用真實流量調（可重算所以能迭代）。
- 初期流量稀，brief 常一行 NO ACTION——來源清單問題，非管線問題。
- RSS feed 只曝露最新數篇；長期不開 session 舊文掉出視窗。
- evidence-delta 的 causal-path 精度可能太吵或太鈍，用真實入圖撞。
