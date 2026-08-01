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

# Daily Approval Brief Skill（v1.5）

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

### Step 0 — Codex task 識別

Codex desktop scheduled run 的第一個 App 動作必須實際呼叫 `codex_app__set_thread_title`，把目前 task
改為 `StockBotv2 Daily Brief — YYYY-MM-DD`（日期取 Asia/Taipei 當日），並確認工具回傳成功後才繼續。
只在 brief 內輸出日期標題、或只用自然語言說「已更名」，都不算完成。若工具在該 executor 不可用或
呼叫失敗，routine 仍繼續，但健康段落必須列 `title_update_failed` 加上可觀測原因（例如
`App callback timeout／no response`、例外類別、嘗試次數與 `success_receipt=false`）；不得只留裸旗標，
也不得把「呼叫已送出」寫成成功。非 Codex desktop executor 跳過此 App-specific 動作。

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
`harvest-health` 持續顯示。fixed entry 若疑似 sandbox／proxy／本機網路權限受阻，原命令必須在允許
本機網路的權限下重跑一次；第一次記 `access_blocked`，只有同一來源後續成功才標 recovered，重跑仍失敗
不得改寫成「零筆」或 `no_result`。`insufficient_history`／`unavailable`／`stale` 也必須在健康段落明示並讓受影響的
technical 或 self-funded range 歸零。Windows 本機與
scheduled task 一律使用 repo `.venv`，不要依賴父 shell 是否剛好 activate。
Engine C 同一筆 observation 保存 adjusted-close 的 1／5／20-session return；Engine D 才負責把
return、RSI、252-session drawdown、signal tier、cooldown 與 capital constraints 組成 Mobile-friendly
燈號。燈號必須配 `可評估／冷卻／觀察／資料不足` 文字與明確系統動作，且不構成 live permission。
燈號與文字不得在 agent 摘要時省略：🟢 `可評估`、🟡 `冷卻／排序中`、⚪ `觀察`、🔴 `資料不足／暫停新增`。
動作對照固定為：`CONTRIBUTE REVIEW`＝可新增評估（不是買進）；`HOLD`＝維持／等待；
`PAUSE CONTRIBUTION`＝暫停新增。若使用者只看到顏色而看不到動作文字，視為 brief 缺欄。
內部 `etf_leverage.nominal_weight` 的人類標籤固定為「槓桿 ETF 資金占比」；乘上 2x／3x 後的
`effective_weight` 才稱「換算槓桿曝險」，不得再輸出模糊的「名目槓桿」。`pace=0.25` 顯示為
「節奏 25%」，並解釋它是該 sleeve 完整 campaign budget 的四分之一，不是 NAV／現金／持倉的 25%。
Portfolio risk 另以 ignored append-only JSONL 保存 aggregate snapshot：Daily 只顯示門檻跨越／狀態翻轉，
Weekly 才用 `--risk-view full --no-record-risk` 顯示完整快照。硬擋包含 ETF nominal／effective 槓桿 cap、
總曝險 cap、callable debt cap 與 investment policy 的 5% 單筆上限；issuer concentration 與 alpha 總量只警告。
`issuer_loads` 是已知、partial ownership look-through，不是完整 ETF 成分，也不含 Engine A 上游依賴。
若輸出 `event_search_requests`，只對該 packet 做一次 WebSearch，列可能原因、曝險與「未經查證」；不得
建立 lead／pq1／pq2、不得寫 Engine A／C／D authority，深入研究必須另走 lead-intake。

### Step 2 — Triage 新 pending leads（依 signal-triage 判準）

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli list --status pending --by-priority --tracked <已追蹤ticker>
```

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

若只需讀既有 authorities／生成五軸 assessment，可完成研究後執行 research-intent `reassess`，再用新
decision receipt 結案：

```powershell
& '.venv\Scripts\python.exe' -m decision_lab reassess <baseline_decision_id> --assessment <assessment.json> --catalyst "<可驗證催化劑>" --disproof "<可證偽條件>" --expiry <ISO-8601> --intent research
& '.venv\Scripts\python.exe' -m engine_b.todo work <todo_n> --to completed --receipt decision:<new_decision_id>
```

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

每輪 drain 後另列不會被一般 queue 自動撿回的 trace backlog：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog
```

一般 event／scheduled trigger 仍回 pq1；只有 `trace_requires_user=true` 才由 `todo sync` 建立
`source_trace_review`。其 `go` 只 dispatch exact lead 回 pq1，不接受 claim、不提高 tier，也不授權付費。

brief 的 pq1 進度不得只寫「park」或只列數量。每一筆本輪處理的 `parked` lead 至少列：完整主詞／ticker、
`parked_reason`（自然語言）、`trace_status`、`trace_next_trigger`、`trace_requires_user`，以及「是否產生
prepared RA」（通常為否）。`original_obtained` 也要說明「已取得原文但屬時變 observation／沒有唯一 graph delta」；
`isolated_tier_3`／截圖／paywall 則要說明「缺哪一份可逐字核對的一手原文」。park 不得被簡寫成已入圖或
「已完成」；若沒有任何可核對 reason，視為 brief 缺欄而非正常 park。

### Step 4 — 今日決策佇列與到期 thesis

```powershell
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
```

回今日 `NO ACTION / REVIEW / TRADE / HEDGE`，每個 probe 附**自追蹤變化%**與**evidence_delta**
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

## Beta capital observation（無 pq2 編號）
TL;DR：最大化約 30 年後 `retirement_net_terminal_wealth`；technical 只決定新增 timing／pace；列今日可人工評估標的與最重要的動態風控 warning
例行提醒：<每 5 個完整交易日一次；本期是否到期；只涵蓋自有現金，貸款不在提醒內>
自有現金可部署：<Portfolio CASH − cash floor；Alpha／Beta 共用>
本輪可評估上限：<同一主路徑經 technical 節奏與 risk caps 後的 ceiling；不是下單金額>
未動用貸款額度：<amount／已借款／估計利息／terms status；明標不算自有現金、未納入本輪上限>
貸款投入：不在例行提醒內；提款時間表未建立，仍為 manual_review_required
| 標的 | 系統動作 | 一句 TL;DR（燈號＋RSI 水位＋1／5／20 日變化＋距高點／趨勢或回檔） | 今日節奏／資本限制 |
|---|---|---|---|
| QQQ | HOLD | ⚪ RSI 43.2（弱／中性）；… | 0%；… |
| SOXX | CONTRIBUTE REVIEW | 🟢 RSI 42.5（弱／中性）；… | 25%；上限 … |
| DRAM | PAUSE CONTRIBUTION | 🔴 資料不足；… | 暫停新增 |

## 低優先（摺疊）
EDGAR Form 4 ×55、較舊 filing——預設摺疊只列數量（要看再展開）

## 無事項目
paper 無異動｜live 無 pending fill｜...

---
回覆：`<編號…> go｜drop｜pending`（例：`3 4 go 5 drop`）
```

pq2／lead priority **不使用顏色維度**（顏色曾混淆 triage 與優先度），一律使用明確指令字串。Beta
technical 區可用配有文字的燈號表達 deterministic state，但不得只靠顏色，也不得把 `可評估` 寫成 `買進`。
Beta 必須使用上述表格，每個 ticker 一列；不能再用一長串 bullet 堆 raw 數字。TL;DR 至少回答「現在在什麼水位、這是趨勢還是回檔、今天能不能新增、限制是什麼」。RSI 區間只是一致的解讀標籤，不改變 `config/beta_policy.json` 的 numeric gate，也不構成 live permission。
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
