---
name: daily-brief
description: >
  每日核准迴路：把 harvest → triage → pq1 自動研究 → 今日決策 → 到期 thesis 聚合成一份
  action-first 的 Daily Approval Brief。持久現況（瓶頸排序／資產配置／研究缺口／在等什麼）自 2026-09-08
  起住 APP，Daily 只印較昨變動。使用者用一行批次語法
  （`1 3 7 go 4 drop 5 6 pending`）
  核准。當使用者說「daily brief」「今天有什麼要處理」「跑每日摘要」「有哪些待判斷」「今天需要
  動作嗎」時使用。三道閘門不放寬：graph admission 必經核准、深挖由 priority/使用者驅動但入圖仍
  核准、live 資本永遠人工。Scheduled run 可自動 pq1 到 prepared，但不建 decision、不下單、不自動入圖。觸發詞：daily brief、
  每日摘要、今天有什麼、待判斷、今天需要動作嗎。
---

# Daily Approval Brief Skill（v1.7）

## 定位一句話

**每天一份 action-first brief；routine 先把 PASS 線索研究成 prepared RA，使用者只核准完整 pq2。**

系統做便宜的 harvest／triage，再依 priority 自動 drain pq1 到 prepared；人工判斷要不要入圖。
無事時 brief 是一行 `MONITOR`。三道閘門永不自動：graph
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
第四支對固定 ETF／權值股 universe 刷新 Engine C TechnicalObservation，再由 Engine D 產**目標配置差距
＋相對水位**。**beta 不回答「今天該不該投」**，只回答兩件事：各 sleeve 距目標配置多遠、每檔在什麼水位。
Runtime／JSON 只保留一條
`self_funded_supported_range`：共同可投資現金池固定等於 `Portfolio CASH − cash floor`，cash floor 以上
全部可供 Alpha 與 Beta 使用；2026-08-29 起它就是**可部署現金本身**，不再乘任何 pace 或單輪比例。
不得再推導 5% operating reserve、3% alpha reserve、planned outflows，
也不得恢復 Sheet／household 雙 cash view。Alpha／Beta 如何分配由 `config/target_allocation.json` 的目標配置
比例、Decision sizing、單筆上限與風控另外決定，不能用 cash reserve 偷渡固定 sleeve 比例。
`Capital Authority` 以 `spreadsheets.readonly` 只讀 `cash_floor` 與 `credit_facility`；cash floor 缺失、stale 或 FX
錯誤時，單一 self-funded range fail closed 歸零。`contingent_credit_available` 只顯示為「未動用貸款額度」，
另列已借款與估計利息，明標不算自有現金；
`loan_funded_supported_range=manual_review_required`，且**貸款 tranche 不適用配置建議**，仍走 Capital
Authority 的逐次 explicit manual review。Portfolio cash 仍是自有 cash 唯一 authority，undrawn
credit 不進 NAV／cash／allocation。行情／capital telemetry 不進 pq1，recommendation
不推定 choice／fill，也不推定 draw，且不寫 Google Sheet。fetch／parse 失敗各記 harvest_log；
訊號整組已於 2026-08-29 移除（commit `6aa31de`）——三態動作、RSI／MACD／tier、`signal.baseline_pace`、
單輪 campaign budget 百分比與「每 5 個完整交易日主動提醒一次」的節奏都不得復刻，改名成
「熱度」「節奏」再放回排序或尺寸同樣禁止。查證：
`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"` 不應出現 `signal`。
**解析失敗 ≠ 無新文**。每筆失敗必須保存 `failure_class`；最新一次仍失敗的來源由
`harvest-health` 持續顯示。Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，
因此 Daily 的唯一權限來源是 `.codex/rules/stockbot-automations.rules` 的窄 fixed entry；不得再用 project
permission profile 當成 scheduled primary path。下列連外命令**第一次呼叫就用 `require_escalated` 命中 exact
outside-sandbox rule**，
不是先製造可預期的 `access_blocked` 再以升權重重跑；不得放行整個 PowerShell、Python、Git 或 working tree。
fixed entry 包含
`crons\harvest_leads.py`、`engine_c\etl_yfinance.py`、`fetchers\edgar.py`、`fetchers\mops.py`、
`scripts\alpha_purity_snapshot.py`、
`scripts\daily_beta_snapshot.py`、`engine_b.cli list`、`engine_b.cli drain`、
`scripts\catalyst_watch.py`、`scripts\outcome_if_settled_today.py`、`scripts\prepare_research_action.py --action-file`、
`decision_lab today`、`engine_b.todo sync`、`engine_b.todo work`、`engine_b.todo reassess-stale`、
`engine_b.todo standing-go`、`scripts\publish_daily_state.py` 與
`scripts\publish_daily_brief.py`、`-m webapp materialize`；十九條 rule 就是單一 authority，不是 primary＋fallback 兩套來源。
`engine_b.cli consume-fired` 刻意**不在列**：它只讀寫 repo 內 JSON，在 sandbox 內就能跑（與 `event_watch sweep` 同先例）。
⚠ `fetchers/` 不是整包放行：只有 `edgar.py` 與 `mops.py` 在列，`gsheets.py` 帶 Google 憑證故排除。
`engine_b.todo work` 只 checkpoint 已由使用者 exact `go` 且已有 `dispatch_ref` 的 decision-review work order；
它不授權 `dispatch`／`resolve`／`reassess`，也不放寬 graph admission 或 live gate。
`query.bottleneck`、`query.coverage_gaps`、harvest health、trace backlog、todo list 與 JSON 檢查已可留在 sandbox；使用者核准後的
apply／reassess／complete-ra／commit intake 不加入 unattended rule，仍走 type-aware 人工 gate。
若 exact rule 未匹配、升權限被拒或命令仍出現 `access_blocked`，保留結構化 failure、讓受影響資料 fail closed，
不得改用第二條更寬 rule、手動重跑或改寫成「零筆」／`no_result`。權限正確後若仍發生暫時性 transport error，
只允許該命令**既有的 bounded、idempotent retry 作最後一步**（例如 TWSE bounded retry、Discord 每段最多
3 次）；不得在 routine 層重跑整份 fixed entry、整份 Daily Brief，或重做已 checkpoint 的研究／authority
mutation。retry 用盡後照樣保存 failure 並 fail closed。
`harvest-health`、queue list／count、JSON 檢查等純本機唯讀命令維持 sandbox。
`insufficient_history`／`unavailable`／`stale`
也必須在健康段落明示，並讓受影響那一列的相對水位標為不可信而非靜默消失；
**單檔行情降級不歸零共用 self-funded range**（已無逐檔區間），只有資本 authority 失效或硬擋才歸零。Windows 本機與
scheduled task 一律使用 repo `.venv`，不要依賴父 shell 是否剛好 activate。
Engine C 同一筆 observation 保存 adjusted-close 的 1／5／20-session return；Engine D 呈現的行情心跳與
相對水位**一律取自該商品自身 provider symbol**：TQQQ 不得冒用 QQQ（2026-08-29 實測水位 69% vs 85%），
00631L／006208 不得冒用 0050。這條原本規範訊號基準，訊號拔除後改規範水位。Engine D 再把這些資料組成
Mobile-friendly 燈號。**燈號只表達行情資料狀態，不表達投入建議**，必須配 `行情正常／資料不足／歷史不足`
文字，且不構成 live permission。
每個商品的 1 日漲跌前必須明列商品自身的最新完整交易日 `YYYY-MM-DD`；即使所有 sleeve 都「到位
（區間內、無偏好）」、今天沒有任何配置缺口，主力逐檔行情表仍是每日心跳，不得省略或濃縮成狀態句。
`stale`／`quarantined` 時改列官方 reference 日期與當日漲跌並附降級原因，不得把最近收盤誤稱即時今日行情。
燈號與文字不得在 agent 摘要時省略：🟢 `行情正常`、🔴 `資料不足`、⚪ `歷史不足`。
🟡 與舊語意 `可評估／冷卻／排序中／觀察／暫停新增` 已於 2026-08-29 廢止，不得回填；
若使用者只看到顏色而看不到狀態文字，視為 brief 缺欄。
內部 `etf_leverage.nominal_weight` 的人類標籤固定為「槓桿 ETF 資金占比」；乘上 2x／3x 後的
`effective_weight` 才稱「換算槓桿曝險」，不得再輸出模糊的「名目槓桿」。目標配置比例顯示為
「目標 40.0%｜容忍區間 ±5.0%」，並解釋分母是**已投入的非現金部位**，不是 NAV／現金／單輪預算。
Portfolio risk 另以 ignored append-only JSONL 保存 aggregate snapshot：Daily 只顯示門檻跨越／狀態翻轉，
Weekly 才用 `--risk-view full --no-record-risk` 顯示完整快照。硬擋包含 ETF nominal／effective 槓桿 cap、
總曝險 cap、callable debt cap 與 investment policy 的 5% 單筆上限；issuer concentration 與 alpha 總量只警告。
`issuer_loads` 是已知、partial ownership look-through，不是完整 ETF 成分，也不含 Engine A 上游依賴；
coverage 為 `partial` 時一律顯示「已知至少 X%」，不得輸出成完整曝險估計。
若輸出 `event_search_requests`，只對該 packet 做一次 WebSearch，列可能原因、曝險與「未經查證」；不得
建立 lead／pq1／pq2、不得寫 Engine A／C／D authority，深入研究必須另走 lead-intake。

**Alpha live 部位另有一條獨立管道：`alpha_position_events`（2026-08-25 補）。** 它由
`alpha/position_events.py` 產出（行情由 `alpha/providers/close_series.py` 取），觸發依據是「**該 cohort 有沒有 live fill**」而非曝險占比——
beta 的 20% 集中度門檻對單筆上限 5% 的 alpha 結構上恆不觸發（L14 第 4 點的「恆滅」）。處置與
`event_search_requests` 完全相同：一次 WebSearch、標未經查證、不建任何 authority。輸出時**必須同時給
單日跌幅與距進場損益**，後者才是使用者實際承受的數字。`alpha_position_events` 為 `null` 代表這個 surface
不提供該能力（如遠端受限 surface），與空 list（有部位但今天沒事）不是同一件事，不得混用。

### Step 2 — Triage 新 pending leads（依 signal-triage 判準）

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli list --status pending --by-priority --tracked <已追蹤ticker>
```

default store 的 Google Sheet 持股或 Neo4j chokepoint context 任一不可讀時，priority list 必須 exit 2、
fail closed；不得把持股靜默降成空集合後仍宣稱已依完整 priority 排序。

對每條**新** pending lead 套 `skills/signal-triage/SKILL.md` 五要素判準。判斷完寫回（本機用 CLI、
雲端用 MCP `record_lead_decision`），並帶上 priority flags（供 pq1 排序）；MCP 的 PASS 亦必須傳
`content_type`／`decision_impact`／必要的 `payment_direction`，與本機同一契約：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go --tier 3 --reason "<要素>" --content-type <type> --decision-impact <impact> [--payment-direction <direction>] [--classification-reason "<分類理由>"] [--contradiction] [--novelty] [--independent]
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --no-go --tier 4 --reason "<為何篩掉>"
& '.venv\Scripts\python.exe' -m engine_b.cli classification-health
```

triage 寬鬆（關聯性與可引用性是硬指標，其餘軟指標命中即 go）；no-go 也記 reason。`tier` 是來源初步
分級，**不是** evidence tier、不影響入圖強度。priority flags（矛盾/反證、新穎、獨立來源）只供 pq1 排序。
PASS classification 的封閉字彙與判準只認 `skills/signal-triage/SKILL.md`／
`config/lead_classification.json`；health 非零必須在健康段逐筆列出。缺分類 lead 不進 drain 排名，
但不得因此隱藏或自動 FILTER。

### Step 3 — 先清機械段，再 pq1 drain（priority，可續跑）

**機械段（2026-09-09 研究閉環 P5 起由 Daily 每天跑；零 token、不吃 drain_limit_per_run）：**

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli consume-fired          # 段 1：fired 的追源 watch 排回 pq1（sandbox 內）
& '.venv\Scripts\python.exe' -m engine_b.todo sync                  # 段 1 的 pq2 型翻醒（既有）
& '.venv\Scripts\python.exe' -m engine_b.todo reassess-stale --run  # 段 2：純 system_internal blocker 的 REVIEW → reassess 結案（exact rule）
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go --run     # 段 2b：常規授權類別直接下使用者本來會下的 go（exact rule）
```

三支的輸出數字進 brief 首屏的「今日自動清了 N」計數器（見模板）；skipped 逐筆列理由。**判斷類（forward view、
decision gap 研究）不在 daily 自動做**——LLM 無人值守寫判斷檔的 allowlist 縮不到安全範圍，那是 research-drain 的事。
段序定義見 `engine_b/queue_segments.py`。

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

**`--intent paper` 是預設（2026-08-08 使用者定案；2026-08-28 語意改變）。** intent 不再產生
任何模擬部位——資本表達層已整組移除。它現在只決定**要求哪些 lane 的資料完整度**，進而影響
`research_status`（`READY`／`INCOMPLETE`／`DATA_NEEDED`）。

⚠ intent **不會**壓低研究完整度。`execution_intent_research_only` 這類碼在
`config/decision_blockers.json` 是 `diagnostic` 級，自 2026-08-29 起不再有改判權
（判準改用 `fatal_blockers`），所以 `research` intent 一樣可以是 `READY`。
維持 `--intent paper` 為預設是為了讓同一 cohort 的評估條件不因呼叫端習慣而跳動。

「系統的判斷準不準」由等權重報酬回答，錨點是 Shadow observation（只有價格與時點，不含部位），
與 intent 無關。

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
成 `action_prepared`。SEC 原文若需 repo fetcher，使用 `fetchers\edgar.py` exact rule；台股原文用 `fetchers\mops.py` exact rule；其他公開頁可走
WebSearch／Browser，兩者是 shell rules 之外的獨立權限 surface。

每輪 drain 後另列不會被一般 queue 自動撿回的 trace backlog：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog --needs-attention   # 被動層救不了的
```

一般 event／scheduled trigger 仍回 pq1；只有 `trace_requires_user=true` 才由 `todo sync` 建立
`source_trace_review`。其 `go` 只 dispatch exact lead 回 pq1，不接受 claim、不提高 tier，也不授權付費。

**等待條件的判定與喚醒一律由 Event Watch registry 負責（[321]）**，`leads.py` 沒有第二套引擎。
線索 park 當下自動建 watch 並取得到期日；`trace_next_trigger` 只做人類說明，機器比對用
watch 的 `entities`。`trace_trigger_kind` 仍是 lead 上的寫入端字彙（擋拼字錯誤），但**行為由
`event_watch.WATCH_KINDS` 決定**——`primary_source_signal` 建 watch 時映射到
`entity_filing_signal`（判準相同：tier-1 ＋ 具名標的交集）。消化標記住在 watch 的
`consumed_entities`，不再於 lead refs 留第二份。

**`wake_state` 必須逐筆列出，`stalled`／`expired`／`unwatched` 三種必須當場處置。** 它們代表
被動層救不了——等下去不會有事發生：
- `stalled`：具名標的都觸發過一輪了。靠到期日兜底或開主動輪詢（`poll.eligible`）撈回。
- `expired`：等待到期。決定續等（延長）、改主動輪詢、或放棄（改 terminal `trace_status`）。
- `unwatched`：**沒有任何機制在等它**，唯一真正的黑洞。三種誠實處置擇一：(a) 主體已登記但
  沒填進機器欄位 → 補 `trace_trigger_entities` 後重建 watch；(b) 根本沒有可追的 claim
  （原文即該貼文本身）→ 改 terminal `trace_status` 豁免重排；(c) 真的需要人工 access／付費／
  改優先權 → 設 `trace_requires_user=true` 進 pq2。**不得原樣留著。**

brief 的 pq1 進度不得只寫「park」或只列數量。每一筆本輪處理的 `parked` lead 至少列：完整主詞／ticker、
`parked_reason`（自然語言）、`trace_status`、`trace_next_trigger`、`trace_requires_user`，以及「是否產生
prepared RA」（通常為否）。`original_obtained` 也要說明「已取得原文但屬時變 observation／沒有唯一 graph delta」；
`isolated_tier_3`／截圖／paywall 則要說明「缺哪一份可逐字核對的一手原文」。park 不得被簡寫成已入圖或
「已完成」；若沒有任何可核對 reason，視為 brief 缺欄而非正常 park。

### Step 4 — 今日決策佇列、部位與到期 thesis

```powershell
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
& '.venv\Scripts\python.exe' scripts\catalyst_watch.py
& '.venv\Scripts\python.exe' scripts\outcome_if_settled_today.py
```

⚠ **2026-09-08 起，瓶頸排序、產業分組、覆蓋缺口與標的純度不再由 Daily 印出**——它們住 APP
（`#/ranking`、`#/coverage`），由收尾的 `-m webapp materialize` 每天更新。Daily 仍需要排序資料，
但只用來算「較昨變動」：`decision_lab today` 的輸出已含兩份排序，與
`library/private/decision_lab/ranking_order_snapshots.jsonl` 的前一筆比對即可。因此
`query.bottleneck`／`--by-sector`／`alpha_purity_snapshot`／`query.coverage_gaps` 四支從 Daily
的命令清單移除；它們仍是 [`skills/alpha-status`](../alpha-status/SKILL.md) 的入口，隨叫隨到。

⚠ **這不推翻 2026-08-19 的教訓，正好相反。** 當時的問題是 `rank_bottlenecks()` 早就把
COHR→NVIDIA 排在第 1，但 brief 沒有消費端，於是使用者問「推薦哪一檔」時 agent 只能答
「無法推薦」——**做了正確的工作，產出沒有消費端**（L13）。今天它有兩個消費端：APP 的
`#/ranking`（完整、隨時可看）與 Daily 的「較昨變動」（只講今天不一樣的地方）。
**要把一段內容移出 Daily，唯一合法的前提是它在別處已經讀得到**；反過來做就是 L13 重演。

第一支是決策佇列與常駐計數器的唯一權威，也提供部位與問責那一段的資料。第二支是**賣出側**：
把每筆 decision 已經必填的 `disproof`／`catalyst`／`expiry` 從卡片上的散文變成每天被檢查的狀態。
L7 的原話是「欄位有填但沒有後續流程，等於貼了一個永遠不會響的火警警報」——這一支就是那個缺掉的
流程。它是**條件檢查不是訊號**（只回答「你自己寫下的條件今天到了沒」，不預測任何東西），因此不受
「先量測後放閘」限制。輸出四態：`設定不完整`／`已逾期`／`即將到期`／`監控中`，**`設定不完整`
排最前面**——它的到期提醒本身就是假的，先修它才有意義。散文裡的日期**不猜**：只用結構化的
`expiry` 與 `thesis/lifecycle.json` 的 `catalyst_checkpoints`，猜出來的日期會產生「看起來有排程、
其實是編的」提醒，比沒有提醒危險。報表末尾必須顯示「N/M 檔有結構化催化劑日期」——其餘檔的
`expiry 早於催化劑` 錯誤測不到，**沒抓到問題不等於沒有問題**（L13）。

第三支唯讀提供真實 fill、最新已收盤價與 point-in-time 報酬，不 close、不寫 authority；它也負責
append 當日的排序快照（同日去重），那是「較昨變動」的基準。

`decision_lab today` 自 2026-09-05 起在排序之後多一區 **「Alpha Card 摘要」**（可行動排序前 5 檔
各壓成一列）。**Daily 不再印它**——單檔的完整判讀在 APP 的單檔頁面，比一列摘要完整得多；需要
終端機版本時用 `& '.venv\Scripts\python.exe' -m briefing alpha-card <TICKER>`。


### Step 5 — 同步統一待辦池並組 brief（繁中、exception-first、**穩定編號**）

先同步所有 pq2 來源：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync
```

`library/leads/todo_pool.json` 是回覆編號的唯一 authority：項目首次進池時取得編號，直到 resolve 才釋放；
**不得依當日排序、section 或模型輸出重新編號**。用池內原編號把決策佇列／等 apply 的 RA／
到期 thesis／有 material evidence-delta 的 probe 組成 brief，每項附明確指令。無事就一行
`MONITOR ＋日期`。

### 待核准項目的內容密度

**每個待核准項目的開頭必須是決策區塊**（2026-08-29 立，2026-09-11 改版面）。

⚠ **版面規定：每個欄位自己一行，行內不得用 `｜` 串接多個欄位，也不得用表格。**
使用者在手機上讀 brief；單行加 `｜` 的舊格式必須左右滑動才讀得完，而這正是他最需要
一眼看到的東西。**欄位一個都沒有減少——改的只是折行方式。** 每行盡量控制在 30 個
全形字以內；超過就讓它自然換行，因為每行都有欄位標籤，換行後仍然讀得懂。

```text
[N] <動詞＋主詞：這次 go 會讓誰去做什麼>
    為什麼現在：<一個子句>
    go＝<action type>
    不含：<最相鄰但未授權的動作，逗號分隔>
    圖影響：<+N 節點、M 邊、K claims（來源，tier）>
```

範例——不展開密度欄位就能決定：

```text
[14] 補 COHR 的 counter-path 證據
     為什麼現在：最弱軸 technical_causal_link，counter_paths 為空
     go＝bounded research
     不含：入圖、Engine C 寫入、live
     圖影響：無（研究產出為 assessment，不動圖）
```

⚠ 決策區塊改的是**閱讀順序**，不是刪內容——下面的密度欄位一項都不減。使用者接受術語，
不能接受的是「要讀完四段才知道要不要動作」。

**「不含」欄逐項寫出最相鄰的未授權動作**（研究 `go` 不含入圖、入圖 `go` 不含 thesis
mutation、任何 `go` 都不含 live），否則使用者要靠記憶區分授權邊界。

**「圖影響」欄固定要有**（2026-08-31 使用者定案）：`ra_admission` 由 `todo list` 的
`圖影響：` 行直接取用（sync 時從凍結 payload 計算：+N 節點、M 邊、K claims＋來源與
tier）；其他類型由撰寫者一句話回答「核准後我的圖／authority 多了什麼」；真的不動圖就
寫「無」並說明產出是什麼。使用者要能不展開密度欄位就知道「我核准了什麼、對我的圖有何影響」。

### 這個區塊是所有 skill 共用的，不是 daily-brief 專屬（2026-09-11 使用者定案）

`AGENTS.md` 早就寫著「待核准內容的呈現契約全文住本檔」，但實查（2026-09-11）只有
`skills/alpha-status/SKILL.md` 指過來，`research-drain` 與 `development-flow` 各自造了
一份格式——**三個 skill、兩份契約，其中一份自稱唯一**。那是 L16 在 skill 層的形狀。
凡是要使用者核准的輸出，一律用上面這個區塊，不得另造。

**開發項不鑄號，用「收據行」不用決策行。** 開發項的唯一載體仍是
[`ROADMAP.md`](../../docs/ROADMAP.md)（`AGENTS.md` 2026-08-31 定案，本次未動）；
走常規授權做掉的改動是**事後告知＋可否決**，不是事前請求核准，所以沒有編號可批。
它的區塊少掉 `go＝`（沒有 go 可下），多掉兩格，且必須指得回 ROADMAP：

```text
（本輪已做）讓「哪些邊有值但沒填」每輪自己出現
     為什麼現在：段5 卡 60 檔時，要手算才知道 58 檔算不出結構分
     會變的數字：closure-gate 印「不在瓶頸排序內 58／59 檔」（先前不存在）
     可逆：單一 commit，可 revert
     ROADMAP：開放 backlog「NEXT_PICK_RULE 沒有成本維度」
```

⚠ **「會變的數字」與「可逆」兩格不得省略。** 前者是 L14（答不出哪個數字會變就不該做）；
後者是這類改動能走常規授權的**唯一理由**——不可逆的東西不在常規授權範圍內，要另外問。

**pq1 排序標籤必附圖例**（2026-08-31 使用者定案）：brief 出現 `候選集合·財務事實` 這類
複合標籤時，同一節開頭固定放一行圖例，不得假設使用者記得字彙表：
`標籤讀法：前段＝答案回來會改什麼（出場條件>候選集合>排序>只是信心），後段＝材料是什麼（資本承諾/結構事實/財務事實/內部人/情緒）`。
字彙 SSOT 仍是 `config/lead_classification.json`，圖例措辭與其 label 同步。

**區塊依「現在能不能決定」分，不依類型分（2026-08-31 使用者定案）：** 四段固定為
「建議 go／建議 drop／你之前說晚點再決定的／不用動」；`ra_admission`／`decision_review`／
`source_trace_review` 這些是系統的分類軸，不再拿來當使用者可見的段落標題。同一段內
若有多種類型，用每項自己的「授權範圍」行區分。

⚠ **第三段不得摺疊，也不得併進「不用動」。** 分段依據是 `waiting_on` 是否為空——
為空代表使用者隨時可以決定（只是上次說晚點），必須逐項現形並**附已等待天數**；
`waiting_on` 有值才是真的在等外部事件，那種才可摺疊。`deferred_at` 只影響排序位置，
不影響可見性。

事發（2026-08-31）：brief 把 [193]（付費報告 access，已 defer 10 天）與 [230]
（已 defer 6 天）跟「等事件」混在同一段摺疊，使用者當場指出「這個不應該被藏起來」——
兩者 `waiting_on` 都是空的，是**欠著的決定**不是等待中的事件。
附天數是為了讓拖延自己現形（L14：防呆要會自己出現，不是要人記得）。

### 面向使用者的措辭層（2026-08-31 使用者定案）

這是同一個張力的第三次調整，方向一致、不是推翻前兩次——07-30 修的是「只給 `co:axt`
無法還原主詞」，08-29 修的是「要讀完四段才知道要不要動作」，本次修的是**術語密度本身**。
使用者原話：「我可能 care 這次核准建立了哪兩個公司之間的哪種關係，但他是怎麼在圖裡用
什麼 property 表達，其實我不是很在意。」

1. **判準是「望文生義還是要查表」，不是「內不內部」。** 使用者原話：「`co:axt` 這類
   內部 ID 好像也可以留著……但太長或比較艱澀的 label，我偏好直接能看懂的。」
   所以 `co:axt`／`co:coherent` 本身就是公司名，**留著**，翻譯反而多一層轉換；
   真正要翻的是含縮寫或長蛇形命名的：`tech:uhp_laser` → 超高功率雷射、
   `mat:inp_substrate` → 磷化銦基板、`externally_corroborated` → 客戶端印證、
   `self_reported_costly` → 供應商自報、`research_assessment_missing` → 缺獨立來源、
   `ra_admission` → 入圖核准。翻譯後首次出現以反引號附原始 label，讓使用者能貼回來查圖。
2. **三樣必須留，其餘可省：** pq2 編號（唯一核准介面）、公司全名＋ticker、
   `go` 授權什麼／不含什麼。前兩者是使用者的操作把手，第三者是四個 authority gate 的
   界線——省掉它，使用者就得靠記憶區分「核准入圖」與「核准下單」。
3. **內部機制名稱不出現在使用者可讀區**：`action_digest`、`focus_company_id`、
   `cohort_id`、`work order`、`consumed marker` 等留在 receipt 與 log，不進 brief 正文。

判準：**問「使用者讀到這個詞，要做的決定會不同嗎？」** 不會 → 它是實作細節，收進 receipt。

### 收尾建議摘要是義務（2026-08-30 使用者定案）

每個研究段落、daily／weekly 報告與較長的互動回覆，結尾必附「建議摘要」——
`go`／`drop`／`pending`／不動各列編號＋一句理由，**最後一行單獨給可直接複製的批次指令**
（如 `252 253 256 257 go 255 pending`），使用者不回讀全文即可複製回覆。

stable pq2 編號後不得只貼短標題或 `co:*` ID。決策行之下，每一個需要使用者決定的 item 至少包含：

1. 一段一句話 TL;DR，直接寫清楚「誰、對誰、做了什麼」。
2. 完整公司名與 ticker（若有），以及供應商／客戶／產品／材料／技術的角色與方向。
3. 事件成熟度（例如 announcement、sampling、qualification、capacity commitment、volume production、revenue）。
4. 為什麼影響投資判斷；證據來源、反證與不能推論的邊界。
5. `go` 實際授權的 action type：排入 bounded research、exact graph admission、manual observation、thesis review，
   或其他明確 authority mutation；不得只寫「核准」。

**同型項打包（2026-09-02 使用者定案）：** 同一段內若有多個 item 的 action type、授權／不含
邊界與圖影響句**完全相同**（最常見：一批「補客戶端／第三方證據」的 bounded research），
**共用欄位提升到組層級寫一次**，每項只留一行決策行（公司全名＋ticker＋具體要找什麼＋
補的是哪個分組／哪個軸）。五欄密度由「組聲明＋項目行」合計滿足，**不逐項重複樣板**——
2026-09-02 實測 7 個同型項各自重複「go = bounded research，不含入圖…」「圖影響：不直接
改圖…」共燒掉 40+ 行，資訊量為零。⚠ 邊界有任何差異（例如其中一項多了「不含 registry
修正」）就不得併組——寧可獨立一項，也不能讓使用者以為邊界相同。

**每個編號整份 brief 只完整出現一次（2026-09-02 使用者定案）：** 四段（go／drop／晚點再決定／
不用動）是編號的唯一家；「無事項目」不得再複述已在四段出現的編號（2026-09-02 實測
[129][311][359] 出現三次）。收尾「建議摘要」照舊列編號＋一句理由（那是義務），但不重述
內文理由。「無事項目」段只保留四段未涵蓋的零事件聲明；若無獨有內容，整段省略。

內容可以 mobile-friendly，但不能把理解成本轉嫁給使用者。queued／researching／awaiting_approval 的 item
改寫為狀態更新，不再要求使用者重複 `go`。

第一行固定是 `# Daily Brief YYYY-MM-DD (Asia/Taipei)`（Asia/Taipei 當日），讓不同天的 brief 可分辨。
**首屏第二行固定是 watch 計數器**（2026-08-31 定案，L14 常駐計數器）：照抄 `todo sync` 摘要的
「watch N 筆（T1 a／T0 b／可輪詢 c，本輪喚醒 w）」；「等事件」區有項目卻無對應 watch 的逐項點名。
⚠ **[321] 起 registry 同時涵蓋追源，計數器必須加報「停滯 s」**——那是「看起來在等、但被動層
不會再醒」的筆數，是這個機制唯一會安靜失效的地方，必須常駐可見（L14：防呆要自己出現）。
`derived_from_blockers` 的等待項不需要 watch（每次 sync 重新推導），不算缺口。
**Pane 1 末尾附 `query.bottleneck --by-sector` 的每產業 top-3**（含開頭兩條需求錨重疊警告）；
分組解決可視性、分數不可跨組比較，單一排序仍是唯一權威；空產業組與「🔴 無需求錨」要現形。

```
# Daily Brief <YYYY-MM-DD> (Asia/Taipei)

## 需要你動作

### 建議 go（N 項）
[2] AXT（AXTI）— 兩個客戶掏錢綁產能
<一到兩句話：誰對誰做了什麼，用人話，數字要在>
核准後：<圖／authority 多了什麼，一句話>
授權範圍：只是入圖。不含建立投資論點，不含下單。
細節：<成熟度｜一手來源｜缺什麼｜反證邊界，一行內用｜分隔>

### 建議 drop（N 項）
[278][293][295] IQE／Marvell／POET 補佐證 — <為何可關；為何不會換號重生>

### 你之前說晚點再決定的（N 項）— 不得摺疊
[193] Rosenblatt 券商報告 access — 已等 10 天｜要你決定買不買（付費）
[230] Schaeffler 補佐證 — 已等 6 天｜要你決定要不要現在研究
<`waiting_on` 為空＝隨時可決定。逐項列，附已等待天數；deferred_at 只讓它排在
建議 go 之後，不讓它消失>

### 不用動（N 項）
等事件 N 項｜研究進行中 N 項
<只有 `waiting_on` 有值（世界要先發生某事）或系統正在跑的才進這段，可摺疊成一行>
...

## pq1 研究進度（無 pq2 編號）
完成：AXTI 8-K ×3 → prepared `ra_xxx`，已以上方穩定編號 [2] 等核准
park：社群 CPO 推論 → 一手來源未支持，不產空 RA
續跑：尚有 triaged_go ×N
每筆 park 必須附 `parked_reason` 與「是否產生 prepared RA」；trace 四欄
（`trace_status`／`trace_next_trigger`／`trace_requires_user`）**只在非預設值時現形**
（2026-09-02 使用者定案）：`original_obtained`＋無 trigger＋不需使用者＝一句
「已取一手，無後續等待」收掉，不逐欄列——2026-09-02 實測七條 parked lead 六條全是
預設值樣板。**有** trigger、**需要**使用者、或 `partial`／`isolated_tier_3` 的才逐欄展開。
同發行人的同類文件（如一批 Form 4）彙總一行列數量與唯一例外，不逐筆點名。
每筆尚未 drain 的 lead 必須標明「本輪 cap 延後／尚未 harvest／尚未 triage」
等具體原因與 score，不能只列總數。

## 現況：都在 APP，Daily 只講變動（無 pq2 編號）

今日自動清了 N（fired 重排 a／reassess 結案 b／常規授權 go c），機械段剩 M；基期實績補值：寫入 W／跳過 S／拒寫 R（拒寫逐筆列理由）｜每檔閉環：到終局 T／未到終局 U，下一檔 X
<2026-09-09 P5 固定第一行（L14 常駐計數器）：數字照抄三支機械段命令與 `webapp status` 的「每檔閉環」行；沒跑成寫「未跑：<原因>」，不得印 0>

四個持久畫面由收尾的 `-m webapp materialize` 每天更新；**本段只印計數與較昨變動，完整內容一律不重印**。

| 畫面 | 今天 | 較昨 |
|---|---|---|
| 瓶頸排序 `#/ranking` | 可行動 N 條；首選 <公司（ticker）→ 瓶頸> | 首選未變／前五無進出 |
| 資產配置 `#/beta` | 6 sleeve：低於 N／高於 N／到位 N | 無門檻跨越 |
| 研究缺口 `#/coverage` | 🔴 真缺口 N／🟡 建模待補 N | ±0 |
| 在等什麼 `#/watches` | 在等 N／停滯 N／fired 未消化 N／追源需處置 N | fired +1 |

必填規則：

- **有變動才展開，各一行寫清楚「什麼變了」**：首選換人、sleeve 進出容忍區間、風控門檻被跨過、
  缺口節點增減、watch 由 active 轉 fired／stalled。沒變就只留計數。
  排序的較昨基準是 `library/private/decision_lab/ranking_order_snapshots.jsonl`（每日 append、同日去重）。
- ⚠ **APP 若沒被 materialize（收尾那一步失敗），本段必須改印「APP 未更新：<原因>」**，
  不得照印昨天的計數——否則「看不到」與「沒發生」又同形了（L12）。
- 排序的完整讀法與已知限制、Beta 的逐檔心跳與目標配置表、兩條相關性警告、缺口清單與 watch 清單
  **都住 APP，Daily 不再複述**（2026-09-08 使用者定案；契約見 `AGENTS.md`「Beta 呈現契約」與
  「APP 呈現契約」）。要看完整版本：開 APP，或呼叫 `$alpha-status`（它仍是四 pane 的完整權威）。

## 部位與問責：只印變動（無 pq2 編號）

完整內容住 APP `#/positions`（真實成交、逐檔報酬、常駐計數器、錨點體檢），由收尾 materialize 每天更新。
**Daily 只印今天不一樣的**：新增 fill、disproof 觸發、計數器分子變動、live 樣本數變化。沒有變動就一行帶過。
⚠ 兩種報酬的錨點語意不同（live 以成交價、shadow 以入圖日），**Daily 引用任一數字時必須標明是哪一種**。

TL;DR：<上線標的／可量測／結案歸因常駐計數器；真實部位、錨點樣本效度與監控覆蓋>

| 標的 | 進場 | 現價／損益 | catalyst（何時會知道） | disproof 是否觸發 | lifecycle／監控覆蓋 |
|---|---|---|---|---|---|

逐筆列出 `live_execution_reports` 中的部位。**進場價與 disproof 判準必須同列**。監控覆蓋一欄自
2026-08-25 起由 `alpha_position_events` 回答：有 live fill 的部位一律在覆蓋內，該欄改記今日是否觸發
（未觸發寫「覆蓋中／今日未觸發」，不得再寫「不在覆蓋範圍」）。
已持有部位必須列 disproof 狀態；`None` 或 lifecycle `expired` 要當成缺口提出。

## 賣出側：證偽條件與催化劑（無 pq2 編號）

資料源 `scripts/catalyst_watch.py`。**只印四態計數，加上「設定不完整」與「逾期或即將到期」的逐檔**；
全部監控中就一行帶過（含追蹤檔數與最近一個到期日）。**「N/M 檔有結構化催化劑日期」那一行不得省略**
——其餘檔的「expiry 早於催化劑」測不到，沒抓到問題不等於沒有問題（L13）。


## 低優先（摺疊）
EDGAR Form 4 ×55、較舊 filing——預設摺疊只列數量（要看再展開）

## 無事項目
paper 無異動｜live 無 pending fill｜...

---
回覆：`<編號…> go｜drop｜pending`（例：`3 4 go 5 drop`）
```

pq2／lead priority **不使用顏色維度**（顏色曾混淆 triage 與優先度），一律使用明確指令字串。
Form 4 與較舊 filing 一律進「低優先（摺疊）」只列數量——冷啟動 EDGAR seed 偏 Form 4，別淹沒新訊號。

**Beta 的呈現規則整組移到 APP（2026-09-08 使用者定案）：** 目標配置差距表、主力逐檔表、燈號文字、
52 週相對水位、兩條相關性警告都在 `#/beta`，由 `-m webapp materialize --beta` 每天更新。Daily 只在
**門檻被跨越或狀態翻轉**時各印一行（sleeve 進出容忍區間、某檔行情降級、風控門檻跨越）。
**判準一個字都沒改，改的是它住在哪裡**——完整契約見 `AGENTS.md`「Beta 呈現契約」，
呈現細節見 `docs/ARCHITECTURE.md` §8。⚠ 燈號仍不得只靠顏色、`行情正常` 仍不得讀成 `可買進`，
那條在 APP 端一樣成立。

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

Beta 的「低於目標、新資金可優先補」只是一個人工 capital discussion prompt，不因出現在 brief 就取得 pq2
approval、loan draw、choice 或 fill 語意，也不產生任何金額或部位尺寸。貸款路徑在沒有 exact draw／
instrument／tranche 核准前不得輸出自動金額；**貸款 tranche 不適用配置建議**，仍走 Capital Authority
的逐次 explicit manual review。

### Step 7 — 收尾同步

- **更新 APP 讀的畫面**（2026-09-08；2026-09-09 起加 `--registry-listed`，APP 73 檔每天更新）：
  `& '.venv\Scripts\python.exe' -m webapp materialize --tracked --registry-listed --ranking --beta --coverage --watches --positions`。
  APP 讀的是**已經算好**的判讀（`LLM changes cognition; APP reads cognition`），所以「今天的資料」必須由這一步推進；
  不跑它，使用者打開 APP 看到的是上一次 materialize 的內容（畫面會自己標 stale，但那不是新資訊）。
  只寫 ignored derived cache，不寫任何 authority；**失敗只記健康段、不中止 Daily**。
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
- 初期流量稀，brief 常一行 `MONITOR`——來源清單問題，非管線問題。
- RSS feed 只曝露最新數篇；長期不開 session 舊文掉出視窗。
- evidence-delta 的 causal-path 精度可能太吵或太鈍，用真實入圖撞。
