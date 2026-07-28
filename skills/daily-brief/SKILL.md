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

# Daily Approval Brief Skill（v1.2）

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
& '.venv\Scripts\python.exe' engine_c\etl_yfinance.py
& '.venv\Scripts\python.exe' scripts\daily_beta_snapshot.py --format markdown
```

第一支抓 X＋RSS＋EDGAR watch 新項，以 `since_id`／URL-hash 去重；第二支刷新 Engine C financial snapshots。
第三支對固定 ETF／權值股 universe 刷新 Engine C TechnicalObservation，再由 Engine D 產
`HOLD / PAUSE CONTRIBUTION / CONTRIBUTE REVIEW` 與 Sheet-only conservative range；technical telemetry
不進 pq1，recommendation 不推定 choice／fill，且不寫 Google Sheet。fetch／parse 失敗各記 harvest_log；
**解析失敗 ≠ 無新文**，`insufficient_history`／`unavailable`／`stale` 也必須在健康段落明示並讓該商品
range 歸零。Windows 本機與
scheduled task 一律使用 repo `.venv`，不要依賴父 shell 是否剛好 activate。

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

### Step 4 — 今日決策佇列與到期 thesis

```powershell
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
```

回今日 `NO ACTION / REVIEW / TRADE / HEDGE`，每個 probe 附**自追蹤變化%**與**evidence_delta**
（material=有觸及 thesis 因果結構的新證據 → 建議 reassess；peripheral=只多週邊 source；none=無變或
純價格波動）。再讀 `thesis/lifecycle.json` 列到期需複查的 thesis。純讀，不建 decision。

### Step 5 — 同步統一待辦池並組 brief（繁中、exception-first、**穩定編號、無顏色**）

先同步所有 pq2 來源：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync
```

`library/leads/todo_pool.json` 是回覆編號的唯一 authority：項目首次進池時取得編號，直到 resolve 才釋放；
**不得依當日排序、section 或模型輸出重新編號**。用池內原編號把決策佇列／等 apply 的 RA／
到期 thesis／有 material evidence-delta 的 probe 組成 brief，每項附明確指令。無事就一行
`NO ACTION ＋日期`。

第一行固定是 `# Daily Brief YYYY-MM-DD (Asia/Taipei)`（Asia/Taipei 當日），讓不同天的 brief 可分辨。

```
# Daily Brief <YYYY-MM-DD> (Asia/Taipei)

## 需要你動作
[1] REVIEW — co:coherent｜自追蹤 +3.2%｜證據 material  → 有新證據，reassess
[2] TRADE  — 等 apply ra_xxx（Tower TIA 客戶揭露 draft）  → 核准入圖：go 2
...

## pq1 研究進度（無 pq2 編號）
完成：AXTI 8-K ×3 → prepared `ra_xxx`，已以上方穩定編號 [2] 等核准
park：社群 CPO 推論 → 一手來源未支持，不產空 RA
續跑：尚有 triaged_go ×N

## 低優先（摺疊）
EDGAR Form 4 ×55、較舊 filing——預設摺疊只列數量（要看再展開）

## 無事項目
paper 無異動｜live 無 pending fill｜...

---
回覆：`<編號…> go｜drop｜pending`（例：`3 4 go 5 drop`）
```

**不使用顏色維度**（顏色曾混淆 triage 與優先度）；改用明確指令字串。Form 4 與較舊 filing 一律進
「低優先（摺疊）」只列數量——冷啟動 EDGAR seed 偏 Form 4，別淹沒新訊號。

### Step 6 — 批次 dispatch（type-aware）

使用者回 `1 3 7 go 4 drop 5 6 pending`。先讀池中 exact item，再用 deterministic parser 解析，
不自由心證：

Codex／Claude Code 本機交互執行時，收到核准的 agent 必須以當下 `todo_pool.json` 與 underlying authority
重新核對；上一個 task 的 `memory.md`／transcript 不能證明 item 已執行。兩個本機 agent 不得同時 dispatch
或同時寫同一 working tree。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo list --json
& '.venv\Scripts\python.exe' -c "from engine_b.batch import parse_batch_reply; import json,sys; print(json.dumps(parse_batch_reply(sys.argv[1])))" "1 3 7 go 4 drop 5 6 pending"
```

依編號對應的**項目類型** dispatch（type-aware；動詞不新增任何權限語意）。`todo batch` 只會更新池與
稽核 log，**不會代做** pq1／apply／reassess；必須先完成或 checkpoint 對應動作，再以
`python -m engine_b.todo resolve <編號> --verb <動詞>` 記錄結果，不能先 resolve 再假裝已執行：

| 動詞 | legacy lead | 已 prepared 的 RA | Decision review | 到期 thesis |
|------|-------------|-------------------|-----------------|-------------|
| `go` | raw lead 不再進 pq2 | **apply 入圖**（見下）＋入圖後自動建 Shadow | `todo dispatch` 排入 gap pq1；不先 resolve、不 bare reassess | 引導複查；authority mutation 仍另核准 |
| `drop` | raw lead 不再進 pq2 | 略過該 RA | 略過本次補缺口 | 標記已看、不複查 |
| `pending` | 維持不動、留到之後 brief | 同左 | 同左 | 同左 |

`decision_review go` 的原 pq2 項目在研究期間維持 active，但標成 queued／researching／awaiting_approval，
brief 不得再次請使用者 go。只有 `parked` outcome receipt，或補缺口後產生的**新 decision receipt**，才能
結案；舊 baseline decision 不算完成 receipt。

**go 一個 prepared RA ＝入圖**：走既有 `apply_research_action`（本機或 MCP native approval，一次確認）
→ `advance <lead> applied --ref focus_company_id=co:x` → **入圖後自動建 Shadow 追蹤**：

```powershell
& '.venv\Scripts\python.exe' -m decision_lab evaluate-signal "入圖後自動追蹤 co:x" --company-id co:x --ticker <T> --intent research
```

（或程式內 `decision_lab.ensure_shadow_for_company`；已有 probe 則不重複建、改走 evidence-delta。）
本機入圖後跑 `scripts/commit_pending_intake.py` 補 provenance 帳本。**live 決策（record-choice／
record-fill）不在批次動詞集合**——永遠本機明確 flags，不得由 recommendation 推定 choice、choice 推定
fill。系統不連 broker。

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
