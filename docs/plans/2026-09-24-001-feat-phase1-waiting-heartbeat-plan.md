---
date: 2026-09-24
topic: phase1-waiting-heartbeat
status: active
derived_from: docs/ROADMAP.md（Phase 1，含 2026-09-24 amendment A1–A4）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G7、G8）、docs/reports/2026-09-23-phase0-closeout.md §7–§8
plan_review: pending（使用者 2026-09-24 opt-in：乾淨 context 的 Opus 5.5、effort max；WORK_REQUEST 見 §0.6）
---

# Phase 1 等待與心跳：一個 daily、語意條件 watch、反證有人盯（給執行模型的完整 plan）

> **執行者：便宜模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。唯一例外是 Step 1.6（強模型，見該節）。**
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 1」（含本 plan §0.4 的 amendment A1–A4）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → ROADMAP「Phase 1」「硬約束」→ 本 plan §0.1–§0.4 →
> [`2026-08-31-event-watch-module-requirements.md`](../brainstorms/2026-08-31-event-watch-module-requirements.md)（G7 擴充的設計來源）→
> [`2026-09-17-structural-reading-layer.md`](../brainstorms/2026-09-17-structural-reading-layer.md)（讀圖 ledger 的設計來源）→
> `docs/refactor/historical-failure-matrix.md` §2 六條 invariant → `docs/OPERATIONS.md`「sandbox impact review 五步」與「心跳」節。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是 **watch registry 的筆數與狀態、pq2 的項目、daily 執行紀錄**
> 這類「等待 registry」與「機制存在與否」的計數，不是研究結果（見 §12）。

---

## 0.1 使用者定案（2026-09-24 互動 session；本 plan 的判斷全部來自這張表）

| # | 題目 | 定案 |
|---|---|---|
| 1 | 哪些反證要登記成 watch | 只登記 thesis 與讀圖的反證。舊 Decision Store 凍結的 `coverage_assessments.disproof` **不登記**，心跳另印一行「凍結歷史 N（不盯）」 |
| 2 | 反證欄位與既有反證 | 讀圖 contract 加結構化 `disproof[]`（v2），寫入時自動登記；thesis envelope 加結構化反證，寫 memo 時自動登記。**既有 3 份 thesis 與 2 份現行讀圖由強模型逐條補登記並引用原文位置**（Step 1.6）。驗收①分母改成「3 份 thesis ＋ 2 份現行讀圖」；敘事的登記 hook 延到 Phase 3（amendment A2） |
| 3 | 到期時鑄 pq2 的範圍 | 語意型、假設型到期 → 鑄 pq2 `watch_decision`；pq2 型到期 → 把它指向的編號翻回「球在你」（不另鑄號）；追源型（`wake_lead`）到期 → lead 轉終局並計數（amendment A3） |
| 4 | `watch_decision` 常規授權 | **不列入**（`config/standing_authorization.json` 的 `never`） |
| 5 | 語意核對誰做 | 預設在互動 session 判定；Codex 預篩額度旋鈕預設 0；語意 watch 只比對一手文件、**排除持股申報（Form 3／4／5、144、SC 13D／13G）**、**不等 triage**（amendment A4） |
| 6 | 驗收②③④真實資料未發生時 | 測試證明機制，照實寫「已交付、未生效」，並登記回查用的 date watch（④ 最早 2026-11-22 才可能發生）。⚠ 使用者定案的是 ④；②③ 套同一處置是 plan 作者的類推，已在 plan 交付時向使用者點名 |
| 7 | 心跳接哪些孤兒 | 段 1 加**備份新鮮度**；段 4 加 **NAV 比例**；position events 延到 Phase 5；`forward_view_backlog`（短評待寫數）**不印** |
| 8 | 稽核接點 | audit 的 `Lifecycle`／`Expiry`／`QueueLiveness`／`Orphans` 改讀新 registry；**不沿用** `config/decision_blockers.json` 的 `resolution_mode`（watch＝等事件、`watch_decision`＝等你決定，用 kind 分開） |
| 9 | Phase 0 殘留 | 舊店五個讀取端改 `mode=ro`（Step 1.1）；`{assumption:…}` 回填延 Phase 3、`argument` 標題延 Phase 2／3、`counter_path_relation` 延 Phase 2 |
| 10 | 執行期間 R2 | 六條 trigger 命中時**常規 opt-in**（不停下來問，直接發 WORK_REQUEST） |
| 11 | MCP 開機啟動 | ✅ 已完成（`9cb32fa`：graph_mcp 改 `-m` 啟動、vbs 同日改好） |
| A | 排程重排 | 納入 Phase 1：**一個 Windows daily**（零 LLM，取代 `StockBotv2-Heartbeat` 與 `StockBotv2-FxSync`）＋ **Codex 只做 triage**；長版 Daily Brief 退出無人值守；daily 直接列出要你決定的 pq2；時間只住 config，註冊命令由它導出，每次執行自我比對（amendment A1） |
| B | weekly | Codex weekly 退役；健康審查與 invariants **每天**跑；**沒有週日版**：題材雷達、計分表、本機備份都每天；找題材改成互動 skill「掃題材」；「距上次掃題材 N 天」同時出現在 Discord 與 session 開頭；**所有 `weekly` 字眼拿掉**（AGENTS 兩句改寫已核准，見 §0.4 末） |
| — | 直接修 | harvest 超過門檻沒跑時段 1 亮 ⚠、段 3 印「沒跑」而不是 0；印出分類層上次跑的時間 |
| — | 時間 | daily 維持 **05:30** 起跑（合併後訊息約 05:40 到，原本要等 07:00 心跳）；下限約 05:15（冬令美股 05:00 才收盤）。Codex triage 由使用者設在 daily 起跑後 ≥45 分（建議 06:15） |

## 0.2 現況實測（2026-09-24；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| Codex daily／weekly automation | 兩個都 `PAUSED`（2026-09-22 21:26 Phase 0 為單一 writer 暫停） | `grep ^status ~/.codex/automations/stockbotv2-*/automation.toml` |
| harvest 最後一輪 | 2026-09-22 05:33（harvest 住在 Codex daily 裡，一起停了） | 心跳段 1；`library/leads/pending_leads.json` 的 `harvest_log` |
| APP artifact | 今天 materialize 0 份，7 份都不是今天的 | `python -m webapp status` |
| 心跳段 3 那句「零＝真的沒有，不是沒跑」 | **今天是假的**（沒跑）——L13 同形 | `crons/heartbeat.py::build_queue` |
| T0 喚醒的前提 | 只比對 triage 判 `go` 的 lead——沒有 triage 就沒有任何 watch 會醒 | `engine_b/event_watch.py::check_watches`（`if (lead.get("triage") or {}).get("decision") != "go": continue`） |
| Event Watch | 95 筆；active 90（喚醒 lead 80／pq2 7／假設 3）；kind：related_entity_signal 57、entity_filing_signal 27、fact_verification 9、date 2；**semantic 0**；最早到期 **2026-11-22** | `python -m engine_b.event_watch counters`；下方 §1 片段 |
| thesis 反證條目 | **16**：AXT §7「什麼會推翻這個 thesis」6 條（`-` 條列，之後接 `### 7b` 子節不算）、COHR §6 5 條（`-`）、Sivers §6 5 條（`1.` 編號） | 依標題含「推翻」定位、數到下一個任何層級標題為止 |
| 讀圖 ledger | 8 筆紀錄、2 個節點（`mat:inp_substrate`、`tech:cw_dfb_laser`）的 supersede 鏈，**現行 2 份**；反證只在 `reading` 散文裡，無結構欄位 | `ls library/private/alpha/structure_readings/`；`python -m alpha structure-reading <node> --format json` |
| 短評 ledger | 3 本（AXTI／COHR／LITE），無反證欄位 | `ls library/private/alpha/briefs/` |
| EDGAR lead | 413 筆：**Form 4 共 305 筆、入圖 0**；其他 108 筆、入圖 12 | 標題格式 `<TICKER> <FORM> filed <date>` |
| 各管道 lead → 入圖 | weekly 6→3、decompose 35→15、X 507→22、EDGAR 413→12 | source 前綴 × status |
| 備份 | 最後一次 2026-09-19，Drive `skipped`；**沒有任何排程在跑**；`LOCAL_RETENTION = 3` | `python scripts/backup_private.py status`；`scripts/backup_private.py:70` |
| 健康審查／invariants | `health_audit --local` 4 秒、13 節、🔴 1（重複 SourceDoc）；`audit invariants` 27 秒、13 PASS | 直接跑 |
| 舊 Codex daily 每次開工要讀的字數 | 約 8.1 萬字（AGENTS 15k＋daily prompt 20k＋daily-brief skill 35k＋alpha-status 11k） | `wc -m` |
| 排程時間 | **兩個 SSOT 無機械連結**：`config/daily_routine.json` 與 OS 排程器；2026-09-12 只改了排程器（06:30→05:30）而 config 沒跟上，避讓窗兩個方向都錯 | `config/daily_routine.json` 的 `schedule._doc` |
| 心跳 Windows 工作 | `StockBotv2-Heartbeat` 07:00、`ExecutionTimeLimit PT10M`、`InteractiveToken`、`StartWhenAvailable true`；`StockBotv2-FxSync` 06:55 | `schtasks /Query /TN StockBotv2-Heartbeat /XML` |
| weekly 心跳 | **從來沒跑過**（`weekly=True` 0 次） | `grep -c "weekly=True" library/private/heartbeat/heartbeat_task.log` |
| 行情「完整交易日」 | 依**各交易所當地時間**判斷（Engine C 價格：yfinance `marketState`；技術面：交易所當地 18:00 後才算完整）——與我們幾點跑無關 | `engine_c/etl_yfinance.py`、`engine_c/technical.py::_session_complete` |

## 0.3 本 Phase 刻意不做

- 不做讀圖的 `socket` kind、走圖問句、`graph_holes`（Phase 2）；不做候選狀態與三題（Phase 3）；不做量測（Phase 5）。
- 不把 Form 4 改成機械 FILTER（量測支持，但未經使用者定案；列入結案待決，見 §15）。
- 不修「重複 SourceDoc」那盞紅燈（要動圖＝authority；列入結案待決）。
- 不自動上傳 Drive 備份（Testing 模式的 OAuth token 7 天過期；維持手動，心跳現形）。

## 0.4 ROADMAP amendment（五欄；使用者 2026-09-24 定案，ROADMAP Phase 1／Phase 3 列已同 commit 改寫）

**A1｜排程重排與 weekly 退役**

| 欄 | 內容 |
|---|---|
| 原 roadmap | Phase 1「做什麼」只談 watch 與心跳內容；「AI 分類層…每日硬上限，只標旗」隱含跑在 Codex daily；排程維持 Codex daily＋Codex weekly＋兩個 Windows 工作 |
| 新觀察 | §0.2：Codex 暫停讓抓資料與喚醒全停，而心跳照印「未 triage 0」；使用者 Codex 額度稀缺；weekly 一生只產出 6 則 lead；weekly 心跳從未跑過；備份無排程；排程時間兩個 SSOT 已出過事故 |
| proposed change | 一個 Windows daily（固定步驟清單、零 LLM、唯一發 Discord）；Codex 只做 triage；長版 Daily Brief 退出無人值守（互動 session 說「daily brief」才組含建議的版本）；daily 列出要你決定的 pq2；時間只住 config＋註冊命令＋自我比對；weekly 退役：題材掃描改互動 skill，「距上次掃題材 N 天」常駐；健康審查、invariants、題材雷達、計分表、本機備份每天跑 |
| why | 驗收②③需要輸入；「LLM 失敗心跳照發」（AGENTS）必須在結構上成立而不是靠 Codex 活著；額度花在研究而不是跑程式 |
| impact | 新增 `crons/daily_task.py`、`scripts/register_daily_task.py`、`crons/triage_prompt.md`、`skills/theme-scan/`、`crons/theme_scan_hint.py`；封存兩份 Codex prompt；`.codex/rules` 收窄；Windows 工作 ＋`StockBotv2-Daily` −`Heartbeat` −`FxSync`；Codex 設定由使用者改；AGENTS 兩句改寫（見本節末） |

**A2｜驗收①的分母與敘事 hook**

| 欄 | 內容 |
|---|---|
| 原 roadmap | ①「`semantic_condition` 筆數 0 → ≥ 現有 3 thesis ＋ 8 讀圖的反證數」；做什麼「thesis／讀圖／敘事寫反證時自動 register」 |
| 新觀察 | 8 筆讀圖是 2 個節點的 supersede 鏈（現行 2 份），數 8 份會把被取代的反證重複算；讀圖與短評都沒有結構化反證欄位；Phase 3 會為 `candidate_state` 改同一本敘事 ledger |
| proposed change | ①分母＝**16（3 份 thesis 的反證條目）＋ 2 份現行讀圖的反證條數（Step 1.6 逐字列出後定數）**；讀圖 contract v2 加 `disproof[]`、thesis envelope 加結構化反證；**敘事寫反證時自動登記移到 Phase 3**（與 `candidate_state` 同一次改 ledger） |
| why | 不重複計數；把散文 parse 成標籤違反 L18；同一本 ledger 不改兩次 |
| impact | ROADMAP Phase 1 ①、Phase 3「做什麼」多一句 |

**A3｜到期處置與未發生時的結案**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「watch 到期鑄 pq2 新 kind `watch_decision`」；④「到期的 watch 出現在 pq2 為 `user_decision`，不消失」 |
| 新觀察 | active 90 筆裡 80 筆是追源型；全部鑄 pq2 會把 Phase 0 剛拆掉的注意力噪音灌回來（AGENTS：lead 留在 pq1、不占 pq2 編號）；最早到期 2026-11-22，Phase 1 期間④看不到真實資料 |
| proposed change | 語意／假設型到期 → `watch_decision`；pq2 型到期 → 它指向的編號翻回「球在你」；追源型到期 → lead 的 `trace_status` 轉終局 `watch_expired`＋計數；②③④ 結案時若尚未自然發生：測試證明機制、照實寫「已交付、未生效」、登記回查 date watch，Phase 1 可結案 |
| why | INV-2「到期是重問不是丟」只對需要人決定的等待重問；L13 不得把已交付寫成已生效；不造假資料觸發驗收 |
| impact | `engine_b/todo.py` 型別與收集器、`config/standing_authorization.json`、`config/lead_trace_status.json`、closeout 措辭 |

**A4｜語意核對的執行者**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「AI 分類層對 T0 實體比對命中的新文件問『是否觸及條件』，每日硬上限，只標旗」 |
| 新觀察 | Codex 額度稀缺；語意核對要讀全文；EDGAR lead 74% 是 Form 4（0 入圖） |
| proposed change | 語意 watch 以實體比對一手文件（排除持股申報）、**不等 triage**；醒來＝待檢；判定在互動 session（`semantic-queue`／`judge`）；Codex 預篩額度 `semantic_screen_budget_per_run` 預設 0，>0 時只寫標旗不改狀態 |
| why | G7 的實質不變（AI 只標旗、判定在互動）；成本可調、退化路徑就是 0；驗收③「AI 層關閉時未檢 N」成為預設狀態 |
| impact | `engine_b/event_watch.py`、`config/event_watch.json`、`crons/triage_prompt.md` 的選配步驟 |

**AGENTS 兩句改寫（使用者 2026-09-24 核准的逐字版本；Step 1.9 執行，不得改動其他判準句）：**

- 「3. **weekly 只發現、不處置**；處置建議只由讀得到 pool 現值的 daily／互動 session 給出。」
  → 「3. **題材掃描只發現、不處置**：掃描報告不對 pq2 編號給 go／drop；處置建議只由讀得到 pool 現值的 daily／互動 session 給出。」
- 「…daily brief 不留檔；weekly report 留檔但不是 current-state truth。」
  → 「…daily brief 不留檔；題材掃描報告留檔但不是 current-state truth。」

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-09-24 已核准的 PLAN_PROPOSAL（「Ok 寫吧 然後review」）。** 但使用者同時要求**開工前先過一次 plan review**：
**P0 未 ✅ 之前，`/phase-run` 不得開工**——停在 `AWAITING_HUMAN`，印出 §0.6 的 WORK_REQUEST 請使用者貼給乾淨 context 的 Opus 5.5（effort max）。
review 回 `GO` → 使用者把結果貼回任一 session，該 session 修 plan（findings 逐條處理並記進 §0.7）、P0 標 ✅、commit、push；回 `NO_GO` → 改 plan 後重審。

P0 ✅ 之後：`AGENTS.md`「常規推進授權」照用——Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 1 結案。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（使用者 2026-09-24 定案 #10）**：Step 1.3 之後發 R2-a（無人值守可執行面）、Step 1.7 之後發 R2-b（pq2 授權字彙），不停下來問。

**使用者動作不是停止條件。** Step 1.3 需要使用者在 Codex app 改設定、刪 weekly automation；執行者在 HUMAN SUMMARY 逐字列出步驟後**接著做下一個 Step**，
結案前再核對（§13）。同理，Step 1.6 需要強模型：便宜模型執行到它時**跳過、標「待強模型」並接著做 1.7**；1.6 不擋後續 Step，但**結案前必須完成**。

**每個 Step 一個 commit（1.2 例外：a／b 兩個），訊息第一行寫 Step 編號；Step 為 GO 就 push。** 新 session 先看下面進度表與 `git log --oneline -20`，
從第一個未 ✅ 的 Step 接續（「待強模型」的 1.6 不算阻擋）。commit 短碼由下一個 Step 的 commit 補填（同 Phase 0）。

**同一 working tree 只讓一個 writer 寫入。** Codex daily／weekly 目前 `PAUSED`；Step 1.2a 註冊新 daily 之後，**每天 05:30 起有一個排程 writer**。
執行者在 05:15–06:45 之間不做會寫 `library/leads/` 的動作；長時間寫入前跑 `python scripts/writer_guard.py check`（exit 2＝不可）。

| Step | 內容 | 狀態 | commit |
|---|---|---|---|
| P0 | plan review（乾淨 context 的 Opus 5.5 max；使用者跑 §0.6） | ○ | — |
| 1.0 | 基準快照 | ○ | |
| 1.1 | 舊店讀取端改唯讀連線（`mode=ro`） | ○ | |
| 1.2a | 一個 daily：`crons/daily_task.py`、config 唯一時間來源、註冊命令、自我比對；註冊新工作並**停用**舊兩個 | ○ | |
| 1.2b | 至少一次排程觸發成功後，**刪除**舊兩個 Windows 工作與 `crons/heartbeat_task.py`（不擋 1.3 起的 Step） | ○ | |
| 1.3 | Codex 縮成分類層（triage prompt、rules 收窄、writer lock 第三個 owner、daily-brief skill 改成互動專用）＋ R2-a | ○ | |
| 1.4 | `semantic_condition` kind（待檢、判定、預篩旋鈕、排除持股申報、EDGAR form 結構化） | ○ | |
| 1.5 | 反證登記 hook（讀圖 v2 `disproof[]`、thesis envelope）＋ `wake_reading`（客戶出新文件 → 讀圖標 stale）＋ 在盯／未盯計數 | ○ | |
| 1.6 | 既有反證補登記（**強模型**；16 條 thesis ＋ 2 份現行讀圖；不擋後續 Step、結案前必完成） | ○ | |
| 1.7 | 到期處置（`watch_decision`、pq2 型翻回、追源型結案）＋ R2-b | ○ | |
| 1.8 | 心跳改版（較昨 diff、watch／反證計數、pq2 逐筆、備份、健康、NAV、計分表每日、Discord 摘要） | ○ | |
| 1.9 | 題材掃描（weekly 退役、`skills/theme-scan`、提醒 hook、AGENTS 兩句、`weekly` 字眼清掉） | ○ | |
| 1.10 | 稽核改讀新 registry | ○ | |
| 結案 | 九項 gate ＋ closeout 報告 ＋ R2 | ○ | |

**開工／續工指令：貼 `/phase-run` 即可**（skill 會照下面這段做；不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。P0 未 ✅ 就停下印 §0.6。沒有需要我核准的事就一直做到 Phase 1 結案；
撞到六條停止條件才停。每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 P0：plan review 的 WORK_REQUEST（使用者貼給乾淨 context 的 Opus 5.5，effort max）

```
WORK_REQUEST（plan review，Phase 1 開工前；使用者 2026-09-24 opt-in）
Target: master 最新 commit 的 docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md
Claimed: 這份 plan 忠實落實 ROADMAP Phase 1（含 §0.4 amendment A1–A4）與 §0.1 的使用者定案，且便宜模型拿到就能照做
Do not trust: 上面那行是待驗證的宣稱，不是事實；plan 裡每一個「現況」與「程式在哪」都要自己去 repo 核對
先讀：AGENTS.md → docs/ROADMAP.md（Phase 1、Phase 3、硬約束）→ docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G6–G10）
      → docs/reports/2026-09-23-phase0-closeout.md §7–§8 → docs/brainstorms/2026-08-31-event-watch-module-requirements.md → 本 plan
Task: 逐項 ✅／❌ 附證據（檔案:行號或實際跑出的命令輸出），回 REVIEW（verdict GO／NO_GO ＋ findings，每條標 blocking／non-blocking）
  1. 定案對得上：§0.1 每一列都有 Step 落地、且 Step 的做法沒有偷偷改變定案的意思；沒有 Step 做了定案以外的事
  2. amendment 合法：A1–A4 與 G1–G12、AGENTS 的邊界不衝突；ROADMAP Phase 1／Phase 3 列的改寫與 §0.4 一致；
     AGENTS 只改 §0.4 末那兩句、逐字相同
  3. 驗收層級：§12 每個驗收數字數的是圖／讀圖／敘事／等待 registry／追蹤表或「機制存在與否」，沒有「幾檔通過某個 filter」
  4. 可執行：抽查每個 Step「改哪裡」的檔案與函式真的存在、「怎麼驗」的命令真的能跑（至少跑 --help 或唯讀那幾條）；
     §0.2 的現況數字抽三條重跑
  5. 事實核對（plan 的關鍵前提，逐條驗真假）：
     a. engine_b/event_watch.py::check_watches 只比對 triage decision == go 的 lead
     b. engine_b/writer_lock.acquire 同 owner 是續期（所以不同 writer 必須用不同 owner）
     c. tests/test_layer_separation.py 禁止 alpha/（providers 以外）import engine_b
     d. engine_b/todo.py::_mark_source_cleared 永不自動 resolve
     e. scripts/backup_private.py 的 LOCAL_RETENTION、StockBotv2-Heartbeat 的 ExecutionTimeLimit
     f. 三份 thesis memo 的反證條目數（AXT 6、COHR 5、Sivers 5）
  6. 安全面：Windows daily 取代 Codex 的 sandbox 後，「固定步驟清單＋清單相等測試」是否足以當補償控制（L15：放行與收緊同時發生）；
     `.codex/rules` 收窄後 Codex triage 還跑得動嗎；有沒有哪一步會在無人值守時寫任何 authority
  7. 停止條件與 R2：§0.5 的推進規則、使用者動作不停、1.6 可跳過但結案前必完成——有沒有違反 AGENTS「協作與邊界」六條停止條件
  8. 漏掉的：ROADMAP Phase 1 列或決定紀錄 G7／G8 要求、但本 plan 沒有任何 Step 負責的東西；或 §14 陷阱沒列到、但照 plan 做一定會踩的坑
Boundaries: 只讀。不改 code、不改文件、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不跑 crons/daily_task.py 或任何會寫
            library/ 的命令（唯讀命令可以跑）
```

## 0.7 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| | | | | |

---

## 0. 不可越線（違反即 NO_GO）

1. **不新增任何 authority 寫入路徑。** 不寫 Neo4j、不改 thesis lifecycle 與 memo 內容、不寫 Google Sheet、不碰 `library/trades/`。
   Engine C 只保留既有的機械寫入（XBRL 基期補值那一支），不新增欄位、不新增寫入者。
2. **舊 Decision Store 只准讀，且從 Step 1.1 起在連線層強制唯讀。** Step 1.0 記 sha256 與 `live_choices`，結案比對必須相同。
3. **四個人工 gate 不放寬。** `watch_decision` 的 `go` 不含任何 authority、永不列入常規授權；語意 watch 判定「觸及」只 consume 並印下一步，
   **不得自動鑄 `thesis_mutation`、不得改 lifecycle**——那是使用者的 pq2。
4. **`AGENTS.md` 只改 §0.4 末那兩句，逐字照核准版本。** 其他判準句要改 → 五欄 amendment ＋ `AWAITING_HUMAN`。
5. **任何無人值守可執行面變更 → sandbox impact review 五步，同一個 commit 改測試**：Windows daily 的步驟清單、`.codex/rules`、Codex prompt、
   SessionStart hook。不得用寬權限掩蓋整合缺口。
6. **心跳零 LLM、零網路、除 `--out` 與快照外零寫入；`crons/daily_task.py` 零 LLM。** Codex 只做 triage（與預篩旋鈕 >0 時的標旗）。
7. **不刪 `docs/archive/`、`docs/reports/`（含全部 `weekly_scan_*.md`）、`docs/brainstorms/`、`docs/lessons-incidents.md`。** 舊 lead 的 `source`（`weekly:`）不改寫。
8. **測試跟機制走**：刪一個測試檔就在八欄列出它守的機制；活判準的斷言**改主詞不刪**（例：Codex prompt 的人工 gate 斷言搬到 daily-brief skill 的測試）。
9. **每個 Step 動手前答 L11-6 第④問，並真的去看那一筆，寫進八欄。**
10. **不造假資料去觸發驗收**：不得手寫 lead、filing 或改時間戳讓 watch 醒來或到期。真實資料沒發生就照 A3 處置。
11. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 使用者動作（Codex 設定）與強模型 Step（1.6）不是停止條件，見 §0.5。

## 1. Step 1.0 基準快照（Z0，一個 commit）

全部存進 `docs/reports/<實跑日>-phase1-baseline.md`，**每項附實際輸出**：

```powershell
.venv\Scripts\python.exe -c "import json,collections;w=json.load(open('library/leads/event_watches.json',encoding='utf-8'))['watches'];print(len(w));print(collections.Counter((x['kind'],x['status']) for x in w));a=[x for x in w if x['status']=='active'];print(collections.Counter('pq2' if x.get('wake_pq2') else 'lead' if x.get('wake_lead') else 'hyp' for x in a));print(sorted(x['expires'] for x in a)[:5])"
.venv\Scripts\python.exe -m engine_b.todo list
.venv\Scripts\python.exe -m webapp status
.venv\Scripts\python.exe -m pytest -q          # 記最後一行與測試檔數
.venv\Scripts\python.exe -m audit invariants
.venv\Scripts\python.exe query\health_audit.py --local     # 記 13 節的 🟢／🔴
.venv\Scripts\python.exe scripts\retired_mechanism_grep.py  # Phase 0 的 0／0／0 仍成立
.venv\Scripts\python.exe scripts\backup_private.py status
schtasks /Query /TN StockBotv2-Heartbeat /XML   # 另存成 Step 1.2 的註冊範本（不進 git 的話記在報告裡）
schtasks /Query /TN StockBotv2-FxSync /XML
```

另記：兩個 Codex automation 的 `status` 行（只讀 `~/.codex/automations/stockbotv2-*/automation.toml` 的 `status`／`rrule`，不印其他內容）；
Decision Store 各檔 sha256 與 `live_choices` 筆數（同 Phase 0 片段）；三份 thesis 的反證條目數（依標題含「推翻」定位、數到下一個任何層級標題為止）；
兩個讀圖節點的現行 reading_id（`python -m alpha structure-reading <node> --format json` 的 `current`）；今天的心跳輸出存一份原文。

驗收：報告存在且含上面每一項的實際輸出。**這些是結案時的比對基準。**

## 2. Step 1.1 舊店讀取端改唯讀連線（Z1，R1）

- **改哪裡：** 仍用 `open_default_store()`（可寫 handle）讀舊店的五個 kept_file：`webapp/materialize.py`、`engine_b/routine_config.py`、
  `audit/sources.py`、`thesis/generate_lane_memo.py`、`scripts/dualrun_axis_conversion.py`；唯讀入口加在 `decision_lab/bootstrap.py`
  （或沿用 `decision_lab/cli.py` 已有的 `mode=ro` 直連寫法，二選一，不要兩套）。
- **怎麼改：** 提供 `open_readonly_store()`（`file:<path>?mode=ro` URI）；五個讀取端改用它。⚠ 先讀 `DecisionStore.__init__`：若開店時會跑 migration、
  `PRAGMA` 寫入或建表，唯讀連線會直接失敗——那就讓唯讀入口繞過這些步驟，而不是把連線改回可寫。DB 檔不存在時唯讀入口**回明確缺席**，不得建空庫。
- **怎麼驗：** 新測試：唯讀 store 上呼叫任何寫入方法 → `sqlite3.OperationalError`（readonly）；`pytest tests/test_private_backup_restore.py` 與相關 webapp／audit 測試綠；
  `python -m webapp materialize --positions` 照跑；`python -m audit invariants` 綠（`DecisionLineage` 349 筆仍追得回）；舊店 sha256 與 1.0 相同。
- **L11-6 ④：** 最先壞的是 `positions` kind（`webapp/materialize.py` 讀 live choice 歷史）與 audit 的 `DecisionLineage`——改完兩個都實跑一次看輸出。

## 3. Step 1.2 一個 daily（Z2，R1；R2 併入 1.3 之後的 R2-a）

### 1.2a（一個 commit）

| 改哪裡 | 怎麼改 |
|---|---|
| `crons/daily_task.py`（新；由 `crons/heartbeat_task.py` 演化，後者留到 1.2b） | 一份**封閉的步驟清單** `DAILY_STEPS`（每步：名稱、argv、timeout、會不會寫、會不會連網）。每步獨立 subprocess＋timeout、**失敗記錄後繼續**（fail-soft），寫執行紀錄 `library/private/heartbeat/daily_run_<日期>.json`（每步 status／exit／秒數／stderr 末段）。**永遠 exit 0**（同 heartbeat_task 的理由：下游是人眼）。開頭 `writer_lock.acquire("scheduled")`，撞到外人鎖 → 跳過所有寫入步驟、仍跑心跳並把原因印在段 1 |
| 步驟順序 | ① `crons\harvest_leads.py` → ② `engine_c\etl_yfinance.py` → ③ `scripts\sync_fx_observations.py`（取代 FxSync 工作）→ ④ `scripts\daily_beta_snapshot.py --format markdown --risk-view changes` → ⑤ `scripts\outcome_if_settled_today.py` → ⑥ `-m engine_b.cli consume-fired` → ⑦ `-m engine_b.todo sync`（含 watch 比對與到期）→ ⑧ `-m engine_b.todo standing-go --run` → ⑨ `scripts\backfill_fiscal_year_results.py --write`（**先確認它的資料仍有消費端**：grep `fiscal_year_results` 的讀取者；沒有就不列入並記 §0.7）→ ⑩ `-m webapp materialize --tracked --registry-listed --structure-table --beta --coverage --watches --positions --structure-readings --scorecard` → ⑪ `query\health_audit.py --local --json`（本 Step 補 `--json` 旗標，**不要 parse markdown 標題**）→ ⑫ `-m audit invariants --json` → ⑬ `scripts\backup_private.py run --no-drive` → ⑭ `scripts\finalize_daily_state.py`（釋放鎖）→ ⑮ 組心跳（`crons.heartbeat`，讀執行紀錄）→ ⑯ `scripts\publish_daily_brief.py --brief-file <md> --summary <摘要>`。**刻意不列**：`catalyst_watch.py`、`engine_b.cli trace-backlog`、`harvest-health`（它們的唯一消費者是退役的 LLM brief；心跳自己讀 harvest_log 與無到期等待計數）、`event_watch sweep`（WebSearch 是研究，互動 session 做） |
| `config/daily_routine.json` 的 `schedule` | `daily_local_time` 成為**唯一**時間來源；加 `task_name: "StockBotv2-Daily"`、`execution_time_limit_minutes`（≥45；舊心跳工作的 PT10M 一定不夠）；刪 `heartbeat_local_time`、`heartbeat_task_name`、`weekly_local_time`、`weekly_weekday`；`_doc` 改寫成「一個來源＋註冊命令＋自我比對」並保留 09-12 事故一句。`harvest_stale_hours`（心跳用）加在同檔 |
| `scripts/register_daily_task.py`（新） | 讀 config → 以 1.0 存下的舊心跳 XML 為範本組 Task Scheduler XML（`InteractiveToken`、`StartWhenAvailable true`、`WorkingDirectory` repo root、`Command` venv python、`Arguments crons\daily_task.py`、觸發時間與 ExecutionTimeLimit 來自 config）。預設 dry-run 印差異；`--apply` 註冊（`schtasks /Create /XML … /F`）並**停用**（不刪）`StockBotv2-Heartbeat`／`StockBotv2-FxSync`；`--retire-legacy` 才刪（1.2b 用） |
| 自我比對 | `daily_task.py` 開頭查自己的工作（`schtasks /Query /TN <task_name> /XML`），把「實際觸發時間／時限」與 config 比對結果寫進執行紀錄；**心跳只讀紀錄**（心跳不得自己開 subprocess）。不一致 → 段 1 亮 ⚠ 並印修正命令；查不到 → 印「排程設定讀不到（unknown）」，不得安靜 |
| `crons/heartbeat.py`（最小改動；完整改版在 1.8） | 段 1 讀執行紀錄（失敗步驟逐條、排程比對）；harvest 最後一輪超過 `harvest_stale_hours` → 段 1 ⚠；段 3 的「未 triage」在 harvest 過期時改印「harvest N 天沒跑——0 不代表沒有新文件」（刪掉那句恆真的「零＝真的沒有」）；段 3 加「分類層上次跑：<時間>（N 天前）」（取 lead store 裡最新的 `triage.decided_at`） |
| `scripts/writer_guard.py`、`tests/test_writer_guard.py` | 讀新 schedule 欄位；時間窗仍由 `daily_local_time`＋`expected_duration_minutes`＋`guard_margin_minutes` 導出 |
| 文件 | `docs/OPERATIONS.md`「心跳」節改寫為「Daily」節（步驟、註冊、改時間的唯一做法、自我比對、失敗長相）；`docs/ARCHITECTURE.md` §4.1 Daily 三層改成「Windows daily／Codex 分類／互動研究」 |

- **sandbox impact review 五步**寫在八欄：可執行面＝`DAILY_STEPS` 這份封閉清單（無 LLM 選命令）；連網主機與憑證與原 Codex daily 相同（X API、SEC、TWSE／TPEx／MOPS、Yahoo、Google Sheet readonly、Discord webhook；**不含 Drive**）；
  寫入範圍：`library/leads/` 四份 state、Engine C private runtime（既有兩支）、`library/private/app/`、`library/private/backups/`、`library/private/heartbeat/`；**不碰 git、不碰 tracked 檔**。
- **怎麼驗：** `tests/test_daily_task.py`（新）：`DAILY_STEPS` 與預期 tuple **逐項相等**（守門：清單不得出現 `webapp serve`、`record_mechanical_observation`、任何 `git`、任何 LLM CLI）；
  單步失敗不阻斷後續、心跳一定跑、exit 0；自我比對不一致時紀錄帶 ⚠。`python crons\daily_task.py --dry-run` 印清單與 config 時間。
  **實跑一次**（`python crons\daily_task.py`；這就是正常的每日動作）：執行紀錄每步有結果、`harvest_log` 最新一輪＝今天、`webapp status` 今天、Discord 收到**一則**（publisher receipt）、段 1 沒有 harvest ⚠。
  `python scripts\register_daily_task.py` → `--apply` → `schtasks /Query /TN StockBotv2-Daily /XML` 與 config 一致、舊兩個工作 `Disabled`。
- **L11-6 ④：** 最先壞的是 `pending_leads.json`／`todo_pool.json`／`event_watches.json` 的 lost update（兩個 writer 撞上）——看執行紀錄的 acquire 結果與 `library/leads/.writer_lock.json`；
  其次是 X API 月上限——實跑後看段 1 的「本月 X 花費」。

### 1.2b（一個 commit；不擋 1.3 起的 Step）

新工作**至少一次排程觸發成功**（`LastTaskResult 0` 且當天執行紀錄完整）之後：`python scripts\register_daily_task.py --retire-legacy` 刪舊兩個工作；
刪 `crons/heartbeat_task.py`（它的 docstring 理由搬進 `daily_task.py`）；`tests/` 裡指向它的斷言改主詞。
驗收：`schtasks /Query` 只剩 `StockBotv2-Daily`；`python -m pytest -q` 綠。

## 4. Step 1.3 Codex 縮成分類層（Z2，R1 ＋ R2-a 常規 opt-in）

| 改哪裡 | 怎麼改 |
|---|---|
| `crons/triage_prompt.md`（新，短） | ① 讀 `skills/signal-triage/SKILL.md` ② `python scripts\writer_guard.py acquire --owner triage --purpose "Codex triage"`（撞鎖 → 停、回報、不重試）③ `-m engine_b.cli list --status pending --by-priority --triage-batch` ④ 逐則 `-m engine_b.cli triage …`（PASS 必帶 `--content-type`＋`--decision-impact`，`capital_commitment` 另帶 `--payment-direction`）⑤ `-m engine_b.cli classification-health` ⑥ 選配：`config/event_watch.json` 的 `semantic_screen_budget_per_run` > 0 才跑預篩（1.4 之後才有命令；之前整段跳過）⑦ `writer_guard release --owner triage` ⑧ 最終回覆一行摘要（處理 N、PASS a、FILTER b、未進本批 c）。**不組 brief、不 materialize、不發 Discord、不研究** |
| `crons/daily_brief_prompt.md` | 逐字封存到 `docs/archive/<日期>-codex-daily-brief-prompt-v1.8.md`，**原檔刪除**（萬一舊 automation 被誤開，它第一步就找不到 runbook 而停）；所有指向它的連結改指新 prompt 或封存檔 |
| `.codex/rules/stockbot-automations.rules` | 只留 triage 需要的：`-m engine_b.cli list`（要讀 Sheet＋Neo4j，escalated）。其餘 11 條刪除（它們搬去 Windows daily 了）。writer_guard、`engine_b.cli triage`、`classification-health` 只寫 repo 內檔案，留在 workspace-write。**用產品自己的 parser 驗載入**（OPERATIONS「文字存在不等於 rule 生效」） |
| `engine_b/writer_lock.py`、`scripts/writer_guard.py` | 加 `TRIAGE_OWNER = "triage"`；`acquire／release --owner {interactive,triage}`（預設 interactive）。**同 owner 是續期、不是互斥**——三個 writer 必須三個 owner |
| `skills/daily-brief/SKILL.md` | 開頭寫明：無人值守的每日訊息是 Windows daily（心跳）；本 skill 只在互動 session 被叫（「daily brief」），讀當天 daily 輸出與 pool 現值，給 pq2 建議與批次指令。刪掉「Codex 組 brief」的流程段；**保留收尾建議摘要的呈現契約**。跑 `python scripts/sync_agent_skills.py` |
| 測試 | `tests/test_codex_daily_permissions.py`：條數與 entry 改成只剩 triage；「相鄰高權限動詞仍在 allowlist 外」照斷言；守 materialize-vs-serve、XBRL 只寫一個欄位、scorecard 網路上限的判準**搬到 `tests/test_daily_task.py`**（改主詞）。`tests/test_routine_prompts.py` 的 DAILY 部分：守「Codex 組 brief」的斷言跟機制退役（逐條列）；守人工 gate、批次語法、pq2 主詞完整的斷言搬到 `tests/test_daily_brief_skill.py` |

- **使用者動作（執行者不代做；HUMAN SUMMARY 逐字列出，接著做 1.4）：**
  1. Codex app → 「StockBotv2 Daily Brief」automation：prompt 改成
     「在 StockBotv2 專案的 master working tree 執行分類層。先讀 AGENTS.md 與 crons/triage_prompt.md，完整照做；不要組 brief、不要發 Discord、不要建立 branch 或 worktree。全程繁體中文。」；
     時間設在 daily 起跑後 ≥45 分（config 05:30 → **06:15**）；reasoning 調成 medium；狀態 ACTIVE（名稱可改成「StockBotv2 Triage」）。
  2. Codex app → 「StockBotv2 Weekly Scan」automation：**刪除**。
- **怎麼驗：** parser 對 `engine_b.cli list` 那條回 `allow`、對已刪的任一條回非 allow；`pytest` 綠；執行者照 `triage_prompt.md` 實跑一小批（daily 抓進來的 pending lead）當 smoke test：
  triage 收據寫入、鎖釋放、心跳段 3「分類層上次跑」更新。
- **L11-6 ④：** 最先壞的是 `engine_b.cli list --triage-batch`——它要讀 Sheet 與 Neo4j，rule 誤刪就 fail closed（exit 2）。刪 rule 後用 parser 對這條 exact command 跑一次。

**R2-a（1.3 GO 之後發；常規 opt-in）：**
```
WORK_REQUEST（R2-a，Phase 1 Step 1.2＋1.3：無人值守可執行面從 Codex 搬到 Windows daily）
Target: 1.2a、1.3 的 commit；crons/daily_task.py、scripts/register_daily_task.py、.codex/rules、crons/triage_prompt.md
Do not trust: 八欄的 sandbox impact review 結論
Task: ①DAILY_STEPS 每一步的網路主機、憑證、寫入範圍逐條核對，有沒有任何一步能寫 authority 或 git；②清單相等測試能不能擋住「有人加一步」；
      ③三個 writer（scheduled／triage／interactive）是否真的互斥；④rules 收窄後 triage 的每條命令是否都能在 sandbox 或剩下那條 rule 下跑；
      ⑤daily 失敗（任一步、鎖被佔、排程不一致）時心跳是否都照發且把原因印出來
Boundaries: 只讀；不跑會寫 library/ 的命令
```

## 5. Step 1.4 `semantic_condition` kind（Z2，R1）

| 改哪裡 | 怎麼改 |
|---|---|
| `engine_b/event_watch.py` 型別 | `WATCH_KINDS` 加 `semantic_condition`。欄位：`condition`（**原文逐字**，≥20 字）、`entities`（T0 過濾用，必須是 registry 解析得到的 ticker／`co:*`，INV-1）、`node`（層或插槽節點，可選）、`source_ref`（`thesis:<memo 路徑>#<條目序>`／`reading:<reading_id>#<序>`）、`quote_locator`（原文在哪一節）、`check_frequency`、`action_48h`、`expires`。`add_watch` 驗：L7 三件套（條件、核查頻率、48 小時動作）缺一拒收；`expires` 晚於建立日；**不得早於條件自己寫的核查點或催化劑**（有寫日期時） |
| 喚醒目標 | 新目標 `disproof_ref`（＝`source_ref`）。「恰好擇一」的不變式照舊：語意型必須是 `disproof_ref`，其他 kind 不變 |
| T0 比對 | 語意型比對的 lead 必須：①一手（`is_primary_source`）②**不是持股申報**（字彙住 `config/event_watch.json` 的 `ownership_forms_excluded`）③實體有交集 ④lead 時間晚於建立 ⑤不在 `consumed_leads`、不是追源重排。**只有語意型不要求 triage `go`**；其他 kind 的判準一個字都不改 |
| EDGAR form 結構化 | `crons/harvest_leads.py` 對 EDGAR lead 寫 `refs.edgar_form`（來自 feed 的 form 欄位）；比對時舊 lead 退回 parse 標題 `<TICKER> <FORM> filed`（寫成一個有測試的函式，不散落） |
| 平行消費端（L16） | `watch_detail`、`_render_watch`、`counters`（加 `semantic_active`、`semantic_pending_check`、`semantic_flagged`、`wake_disproof`）、`wake_target`、`add` CLI、`list`；`webapp` 的 watches kind 呈現語意型（**APP 先讀得到**，Daily 才能不印全文） |
| 新 CLI | `register-disproof`（語法糖）；`semantic-queue`（列 fired 語意型：watch_id、條件原文、觸發 lead 標題／URL／form、來源指標）；`judge <watch_id> --touches yes\|no --note …`：no → `reactivate`（note 必填）；yes → `consume`＋寫 `judgment`（note 與 `--quote`＝文件逐字**必填**，L18），並印「下一步：L7 48 小時動作＝<action_48h>；authority 變更走 thesis_mutation／thesis_lifecycle pq2」；`flag <watch_id> --verdict likely_touches\|likely_unrelated --quote …`（預篩用，只寫 `semantic_flag`，不改狀態） |
| `config/event_watch.json` | `semantic_screen_budget_per_run: 0`（`_doc`：0＝AI 預篩關閉，判定一律互動 session）；`ownership_forms_excluded` |
| `engine_b/queue_segments.py` | 新段 `semantic_pending_check`（cost research；consumer「互動 session：`python -m engine_b.event_watch semantic-queue` → `judge`」）；audit `QueueSegments` 不得出現 unmapped |

- **怎麼驗：** 參數化測試**對 `WATCH_KINDS` 每一員**斷言 `watch_detail` 不回「未知 kind」（2026-09-02 事故的守門）；T0 矩陣：一手 8-K 命中、Form 4 不命中、非一手 X 不命中、未 triage 的一手文件命中、已 consumed 的 lead 不重醒；
  `judge` 兩個方向的狀態轉移與必填欄；缺 L7 件拒收；counters。`python -m engine_b.event_watch list` 正常；`python -m audit invariants` 綠。
- **L11-6 ④：** 最先壞的是**既有 95 筆 watch 的 T0 行為**。把 1.0 的 `event_watches.json` 複製到 `%TEMP%`，改前改後各跑一次 `check_watches`（同一份 leads），**非語意型的觸發結果必須逐筆相同**。

## 6. Step 1.5 反證登記 hook ＋ `wake_reading` ＋ 在盯／未盯（Z2，R1）

| 改哪裡 | 怎麼改 |
|---|---|
| `alpha/structure_reading/contracts.py` | `RECORD_VERSION = "structure-reading/v2"`；加 `disproof: tuple[DisproofEntry, ...]`（condition、entities、check_frequency、action_48h、可選 expires）。`moat`／`volume` 至少一條；`undecided`／`neither` 可空。**v1 紀錄照樣解析成 `disproof=()`，不改寫**（L10：append-only） |
| `alpha/cli.py` `structure-reading --add` | spec 收 `disproof`；append 成功後呼叫 `alpha/providers/structure_readings.py` 的新函式登記語意 watch（`source_ref=reading:<id>#<n>`，`expires` 預設＝讀圖的 `expires`）。⚠ **`alpha/cli.py` 不得 import `engine_b`**（`tests/test_layer_separation.py`），一律經 `alpha/providers/`。supersede：被取代讀圖仍 active 的語意 watch → consume，note「superseded by <新 id>」；retract 同理 |
| `wake_reading`（ROADMAP 的 reread_layer） | 同一個 provider 呼叫另外替**需求側客戶**（快照 `demand_side` 裡的公司端點，解析成 `co:*`）登記 `entity_filing_signal`、新喚醒目標 `wake_reading: <node>`、到期＝讀圖到期。觸發後不重讀、只標 stale：`--structure-readings` materialize 讀 registry，把該節點列進 `needs_reread`，理由「客戶 <X> 出了新文件 <lead>」；該節點下一次 `--add` 時把已 fired 的 reread watch consume |
| thesis | `thesis/generate_lane_memo.py` 的 envelope 加結構化 `disproof_conditions`；驗證：條數必須等於 memo 裡「推翻」那一節的條目數（機械數），不符 fail closed；寫出 memo 後登記語意 watch（`source_ref=thesis:<memo 路徑>#<n>`）。⚠ 先查 `tests/test_layer_separation.py` 允不允許 `thesis` import `engine_b`；不允許就經一個窄 adapter。`prompts/lane_memo_system.md` §6 同步 |
| 在盯／未盯計數（1.8 心跳用） | 新函式（放 `engine_b/`，心跳與 audit 共用）：預期條目＝lifecycle.json 非 retired 的 memo 在「推翻」那一節的條目（`thesis:<memo>#1..n`）＋ 各節點現行 v2 讀圖的 `disproof[]`；在盯＝active 或 fired 的語意 watch 其 `source_ref` 在預期集合裡；未盯＝差集；另回「v1 讀圖散文 N 份（不可機械數）」與「凍結歷史 N（不盯）」（舊店唯讀讀 `coverage_assessments` 的反證數） |

- **怎麼驗：** v2 contract（moat 無反證拒收、v1 解析成功）；`--add` 在暫存 registry 登記 N 筆；supersede consume 舊的；reread watch 觸發 → `needs_reread` 帶理由；thesis 條數不符 fail closed；
  計數函式用兩種 fixture（AXT 式：`-` 條列後面接 `### 7b` 子節；Sivers 式：`1.` 編號）。
- **L11-6 ④：** 最先壞的是**既有 8 筆 v1 讀圖紀錄的解析與 staleness**。改完跑 `python -m alpha structure-reading mat:inp_substrate --check`、`tech:cw_dfb_laser --check` 與 `python -m webapp materialize --structure-readings`，解析失敗必須 0。

## 7. Step 1.6 既有反證補登記（**強模型**；Z1，R1；不擋後續 Step，結案前必完成）

**為什麼要強模型：** 挑實體、判斷一條敘述是不是反證、定位原文，是判斷（L18）；便宜模型做會把散文換成標籤。

1. **先列、後登記。** 在八欄先逐字列出每一條（這就是驗收①的分母）：
   - 三份 thesis：`thesis/axt_inp_v1_lane_memo.md` §7（6 條）、`thesis/coherent_cpo_v2_lane_memo.md` §6（5 條）、`thesis/sivers_v4_lane_memo.md` §6（5 條）。
     AXT 的 `### 7b` 不是反證清單——讀過後若判定裡面有反證型條件，列出來並說明，但不併入 16。上修型條件（例：AXT 取得出口許可）**照登記**：G7 要求「反證與確認事件」都登記。
   - 兩份現行讀圖（1.0 記下的 reading_id）：從 `reading` 散文逐字找出每一條反證／確認條件，附所在句。
2. **每條的欄位：** `condition`＝原文逐字；`entities`＝registry 解析得到的 id（INV-1：**不憑名字猜**；解析不到要寫是「ID 沒解析對」還是「圖中真無此公司」）；
   `check_frequency`／`action_48h`＝memo 開頭「核查頻率」「觸發後 48h 動作」兩行（讀圖則依讀圖自己的到期）；`expires`＝條件自己寫的日期之後，否則下一個核查點＋一個核查週期，**不得早於催化劑**。
3. **登記：** `python -m engine_b.event_watch register-disproof …`，每條一筆；八欄列 watch_id ↔ source_ref ↔ 原文。
- **驗收①：** `semantic_condition` 筆數 ≥ 16 ＋ 兩份現行讀圖的條數（本 Step 第 1 點定的數）。
- **L11-6 ④：** 最先壞的是實體挑錯——watch 永遠不會醒卻看起來在盯。每筆登記後看 `event_watch list` 的 entities 是 registry id，
  並抽一筆用 1.0 之後最近的真實 lead 在暫存 registry 跑一次 `check_watches`，確認比對路徑走得通。

## 8. Step 1.7 到期處置（Z2，R1 ＋ R2-b 常規 opt-in）

| 改哪裡 | 怎麼改 |
|---|---|
| `engine_b/todo.py` | `ITEM_TYPES` 加 `watch_decision`；`GO_AUTHORIZATION["watch_decision"] = ("現在啟動研究：查這條條件是否已成立（bounded research）", "任何 authority mutation（入圖、Engine C 判讀、thesis mutation、live）")`；`SOURCE_COLLECTORS` 加 `("watch_expiry", "_collect_watch_expiry_rows")`、`SOURCE_ITEM_TYPES` 對應 |
| 收集器語意 | 語意型／假設型、`status=expired` 且沒有 `expiry_resolution` → 一列 `watch_decision`。**每個到期事件恰好一個編號**（ref_id 帶 watch_id 與到期時間，不重鑄、不漏）。標題不得只寫 `co:*` 或 watch_id（AGENTS：不得假設使用者能還原主詞）：「反證 watch 到期、條件沒發生：<條件前 40 字>（來源 <memo 或讀圖>）」 |
| 三個動詞 | `go`：receipt 必須指得回研究結果（lead id、報告路徑或新 watch id；`_validate_go_receipt` 加這一型），watch 記 `expiry_resolution`。`drop`：watch 記 `expiry_resolution`（drop、編號、理由）。**續等（`pending --until <日期>` 在這一型上的 type-aware 語意）：watch 以新到期日回 `active`（歷史附加，不覆寫），該編號結案並在 receipt 記新到期日**——**等待只住 registry，不得同時掛在 pq2 的 `waiting_on`**（AGENTS：所有等待住同一個 registry；不建立第二個狀態源）。⚠ `_mark_source_cleared` 永不自動 resolve，所以結案要在同一個動作裡明確做 |
| pq2 型到期 | `_check_event_watches`：`wake_pq2` 的 watch 到期 → 它指向的未結案編號清掉 `waiting_on`／`deferred_at`、log 記 `watch_expired`（同 `watch_wake` 的寫法）→ 回到「球在你」；watch 記 `expiry_resolution: requeued_to_pq2` |
| 追源型到期 | `wake_lead` 的 watch 到期 → 該 lead 的 `trace_status` 設為新的終局值 `watch_expired`（`config/lead_trace_status.json` 登記為 terminal）；心跳計數「追源到期結案 N（今日 M）」 |
| `engine_b/event_watch.py` | 到期時記 `expired_at`；`expiry_resolution` 欄；`renew(watch_id, until)` |
| `config/standing_authorization.json` | `never` 加 `watch_decision`（理由：它真正要你答的是續等或放棄；自動 go 會讓重問消失） |
| `engine_b/queue_segments.py` | `NOT_WORK['watch:expired']` 改寫成「到期：需要人決定的已轉 pq2；追源型已結案」 |

- **怎麼驗：** 測試：到期語意型 → 一個 `watch_decision`；再 sync 不重複；續等 → watch active、新到期、編號結案；drop → `expiry_resolution`；pq2 型到期 → 編號可動作；追源型 → 終局＋計數；
  `standing-go` 跳過 `watch_decision`；`tests/test_engine_b_todo.py` 兩個 dict 鍵一致；`tests/test_standing_authorization.py` 封閉性。**真實資料最早 2026-11-22 才到期**——照 A3。
- **L11-6 ④：** 最先壞的是**既有 7 筆 pq2 型 watch 指向的編號**——改前改後各跑一次 `python -m engine_b.todo sync`（先用暫存池），`todo list` 對未到期的項目**逐筆不變**。

**R2-b（1.7 GO 之後發；常規 opt-in）：**
```
WORK_REQUEST（R2-b，Phase 1 Step 1.7：pq2 新型別 watch_decision 的授權語意）
Target: 1.7 的 commit；engine_b/todo.py、engine_b/event_watch.py、config/standing_authorization.json、config/lead_trace_status.json
Do not trust: 八欄的 GO_AUTHORIZATION 與「等待只住 registry」宣稱
Task: ①go 的授權範圍是否真的不含任何 authority，receipt 是否指得回研究結果；②續等是否讓同一個等待同時住在 pq2 與 registry；
      ③每個到期事件是否恰有一個編號（重跑 sync、續等後再到期）；④追源型終局是否被 parked_without_expiry 與心跳正確計數；
      ⑤standing-go 是否可能碰到這一型
Boundaries: 只讀
```

## 9. Step 1.8 心跳改版（Z2，R1）

**五段不增不減；拿掉的內容換成缺席宣告；缺席分型用 `alpha.absence.ABSENCE_KINDS`。** 心跳仍零 LLM、零網路：需要網路的東西（NAV）由 daily 的 materialize 產生、心跳讀 state。

| 段 | 本 Step 之後的內容（粗體＝新增或改寫） |
|---|---|
| 1 資料新鮮 | harvest（過期 ⚠）、X 花費、行情、月營收、FX、APP materialize、**daily 執行紀錄（N 步成功／失敗逐條）**、**排程時間（config 與實際；不一致 ⚠＋修正命令）**、**備份（最後 N 天前、Drive 狀態）**、**健康審查（N 節｜🔴 M：標題）**、**invariants（PASS／FAIL）** |
| 2 變了什麼 | **較昨變動（快照 diff；第一天印「尚無昨天」）**、**watch：今日醒 a｜今日到期 b｜標旗 c｜未檢 d**、**反證在盯 e／未盯 f（v1 讀圖散文 g 份不可機械數；凍結歷史 h 不盯）**、**今天第一次被點名、圖裡沒有的名字（依首次點名時間排；不依次數，否則 AMZN 會恆亮）**、thesis、候選板缺席、讀圖（含 reread 理由）、已定價缺席、beta |
| 3 佇列 | 未 triage（1.2 已修語意）、分類層上次跑、pq1、**pq2 球在你 N：逐筆「[n] 標題｜go＝…｜不含…」（字串取自 `GO_AUTHORIZATION`，L16）＋批次語法一行；超過 10 筆印前 10 並寫其餘 N 筆**、**到期待決 `watch_decision` N**、watch 到期／總數／無到期等待、**追源到期結案 N**、**距上次掃題材 N 天（≥ 門檻時粗體並移到訊息第一行）** |
| 4 部位 | 既有各行 ＋ **NAV：bucket 分布一行、最大單筆占 NAV（只呈現；完整表在 APP positions）**——producer 是 `webapp materialize --positions` 把 `build_nav_exposure` 的摘要寫進 positions state |
| 5 帳號計分表 | **每天印**：tier 分布＋較昨變化；完整表在 APP。拿掉 `--weekly` 與 `method_not_applicable` 那條路 |

- **快照：** `library/private/heartbeat/snapshots/<日期>.json`，鍵是封閉清單 `SNAPSHOT_KEYS`（watch 各狀態數、語意型各數、pq2 未結案／球在你、lead 各狀態、讀圖現行／該重讀、thesis 各狀態、反證在盯／未盯、健康 🔴 數、invariants FAIL 數）；diff 只印變了的鍵，其餘印「N 項與昨天相同」。
- **Discord 摘要行**（`publish --summary`）：`Daily <日期>｜球在你 N` ＋ 紅旗（harvest 沒跑、daily 有步驟失敗、健康紅燈、題材 ≥ 門檻、備份 >7 天、排程不一致）。
- **備份：** `scripts/backup_private.py` 的 `LOCAL_RETENTION` 3 → 7（每天跑、留一週）；backup 狀態讀取沿用 `briefing/sources.load_backup_status`——⚠ 先查層規則允不允許 `crons` import `briefing`，不允許就把那個 loader 搬到 `shared/`。
- **怎麼驗：** 測試：五段恆在；每個新行在資料源缺席時印缺席分型；第一天 diff；題材門檻兩側；pq2 逐筆的 go／不含字串等於 `GO_AUTHORIZATION`；Discord 摘要組法。
  實跑 `python -m crons.heartbeat --out %TEMP%\hb.md` 並與 1.0 存的心跳逐行對照。
- **L11-6 ④：** 最先壞的是**既有心跳行的文字**（下游是人眼與 Discord 分段）——對照 1.0 那份：每一條拿掉的行都要有取代行或缺席宣告。

## 10. Step 1.9 題材掃描：weekly 退役（Z1，R1）

| 改哪裡 | 怎麼改 |
|---|---|
| `skills/theme-scan/SKILL.md`（新） | 觸發詞：掃題材、找新題材、有什麼新趨勢、theme scan。Stage 0：讀 `config/themes.txt`、上一份報告、`engine_b.cli onboard-candidates`。Stage 1：每個主題 2–3 次 WebSearch；可選 `/last30days <主題>`（**只限互動**，硬約束 8）；看新點名雷達。Stage 2：值得研究的註冊 lead `--source theme_scan:<主題>`；新需求錨用 `decompose-propose` 鑄 manual pq2（**選題是使用者**）。Stage 3：報告 `docs/reports/theme_scan_<日期>.md`（30 秒 brief、Topic Digest、建議 onboard 候選、新錨提案）。鐵律：只發現不處置、不追源不抽取不入圖；舊標籤 `weekly:` 是同一管道的歷史名稱。跑 `python scripts/sync_agent_skills.py` |
| `crons/weekly_scan_prompt.md` | 逐字封存 `docs/archive/<日期>-weekly-scan-prompt-v1.2.md`，原檔刪；它的健康審查／thesis 提醒／beta 快照三段已由 Windows daily 接手 |
| `engine_b/theme_scan.py`（新，小） | `last_scan()`：取 `docs/reports/theme_scan_*.md` 與 `weekly_scan_*.md` 檔名日期的最大值，回日期與天數。心跳（1.8 的那一行）與 hook 共用 |
| `crons/theme_scan_hint.py`（新）＋ `.claude/settings.json` | SessionStart hook：天數 ≥ `config/daily_routine.json` 的 `theme_scan.nudge_after_days`（7）才輸出，systemMessage＋additionalContext「【請在第一則回覆開頭轉述】已 N 天沒掃題材——說『掃題材』」。任何例外安靜跳過、命令尾 `|| true`（同 `phase_status_hint.py`：hook 不能讓 session 開不起來） |
| `AGENTS.md` | §0.4 末兩句，**逐字照核准版本** |
| 其他 `weekly` 字眼 | `rg -n "weekly" AGENTS.md skills crons config tests docs/OPERATIONS.md docs/ARCHITECTURE.md CONCEPTS.md`：每一處改名、退役或留下附理由（歷史引用、封存檔路徑可留）。`tests/test_routine_prompts.py` 的 WEEKLY 斷言跟機制退役；「只發現不處置」的判準改由 theme-scan skill 的測試守 |

- **怎麼驗：** hook 用假日期測兩側（6 天不印、7 天印）；實跑 `python crons\theme_scan_hint.py`；**開一個新的 Claude Code session 確認開得起來**；心跳那一行數字正確；`rg "weekly"` 剩下的每一處都有理由。
- **L11-6 ④：** 最先壞的是 SessionStart hook 讓 session 開不起來——實開一次 session。

## 11. Step 1.10 稽核改讀新 registry（Z1，R1）

- **改哪裡：** `audit/checks.py`、`audit/sources.py`、對應測試。
- **怎麼改：**
  - `Lifecycle`：拿掉讀舊店 `probe_lifecycle_epochs` 的那段（凍結資料恆 PASS＝不會滅，L14-4；凍結歷史由 `DecisionLineage` 照看）；加 watch 生命週期一致性（status 在封閉字彙內、fired 必有 `woken_by`、consumed／expired 為終局、`expiry_resolution` 與狀態相符）。
  - `Expiry`：到期的語意／假設型若既沒有未結案的 `watch_decision`、也沒有 `expiry_resolution` → **FAIL**（INV-2：到期是重問不是丟）；pq2 型到期但指向的編號仍在 `waiting_on` → FAIL。
  - `QueueLiveness`：fired 語意型超過 `_STALLED_DAYS` 沒判定 → finding；`watch_decision` 指向不存在的 watch → finding。
  - `Orphans`：`disproof_ref` 指向不存在的 memo 條目或 reading_id → finding；`wake_reading` 指向沒有讀圖的節點 → finding。
- **怎麼驗：** 每條新判準都有一個會紅的 fixture（空跑檢查）；真實資料上 `python -m audit invariants` 綠。
- **L11-6 ④：** 最先壞的是現有 95 筆 watch 若有歷史資料不符新判準——提交前先在真實資料上跑；**若真實資料不過，那是 finding，不得放鬆判準讓它過**。

## 12. 驗收數的是哪一層

| ROADMAP 驗收 | 數什麼 | 層 | 查證 |
|---|---|---|---|
| ① `semantic_condition` 0 → ≥ 16 ＋ 兩份現行讀圖的條數 | watch registry 裡語意型的筆數；分母來自 thesis memo 與讀圖 ledger | 等待 registry（分母：敘事／讀圖） | `python -m engine_b.event_watch counters`；1.6 八欄的逐字清單 |
| ② 第一次真實的「今日醒 ≥1」 | 當天 `woken_by.at` 為今天的 watch 數 | 等待 registry | 心跳段 2；`event_watches.json` |
| ③ AI 預篩關閉時「未檢 N」且 N>0 | fired 語意型、未判定的筆數 | 等待 registry | 心跳段 2；`event_watch semantic-queue` |
| ④ 到期的語意／假設 watch 出現在 pq2 | `watch_decision` 項目 | 等待 registry → pq2 | `python -m engine_b.todo list` |
| ⑤（A1）一個 daily、每天一則 Discord、時間與 config 一致 | Windows 工作清單、執行紀錄、publisher receipt、自我比對結果 | 機制存在與否（同 Phase 0 的做法） | `schtasks /Query`；`library/private/heartbeat/daily_run_*.json` |

②③④ 結案時若尚未自然發生：照 A3——測試證明機制、closeout 寫「已交付、未生效」、登記回查 date watch（④ 用 2026-11-23；②③ 用結案日＋14 天），
**不得造假資料觸發**。本 Phase 沒有任何驗收數字是「幾檔通過某個 filter」。

## 13. Phase 1 結案

**completion gate（historical-failure-matrix §9 八項＋第九項）：**

1. `pytest -q` 全綠；測試數與 1.0 的差＝新增測試檔－跟機制退役的測試檔（逐檔列）。
2. `python -m audit invariants` 綠（含 1.10 的新判準）。
3. 無未解釋語意 diff：心跳與 1.0 那份逐行對照，拿掉的行都有取代或缺席宣告；APP 個股頁文字 digest 與 1.0 相同（本 Phase 不動個股頁）。
4. 無新 dual authority：排程時間只住 config；等待只住 registry（`watch_decision` 續等不掛 `waiting_on`）；Codex 不再組 brief。
5. 無 silent drop：持股申報排除、追源型到期結案、預篩額度 0 都有計數或理由現形。
6. Point-in-time：語意比對只用 watch 建立之後的 lead；不以抓取日冒充 `published_at`。
7. lifecycle 可達：到期 → pq2／終局兩條路都有測試；`Expiry` 新判準綠。
8. executable protection：`DAILY_STEPS` 清單相等測試、`WATCH_KINDS` 參數化測試、`GO_AUTHORIZATION` 鍵一致、自我比對測試。
9. **驗收數的是 registry 與機制存在與否**，沒有「幾檔通過某個 filter」。

另核對：舊店 sha256 與 `live_choices` 與 1.0 相同；使用者已完成 Codex 兩個動作（證據：心跳「分類層上次跑」在 1 天內、`~/.codex/automations/stockbotv2-weekly-scan` 已不存在或已停用——只讀檢查）；1.6 已完成；1.2b 已完成。
缺任何一項 → `AWAITING_HUMAN`，說明缺什麼。

closeout 報告存 `docs/reports/<日期>-phase1-closeout.md`（格式照 Phase 0 closeout：Step 與 commit、九項 gate、逐檔刪除的測試守什麼、R2 結果、§15 待決問題）。

### 結案 R2（使用者已常規 opt-in）

```
WORK_REQUEST（R2，Phase 1 結案）
Target: master 最新 commit；docs/reports/…-phase1-baseline.md 與 …-phase1-closeout.md
Claimed acceptance: Phase 1 九項 gate 與驗收①–⑤（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m engine_b.event_watch counters → 語意型筆數 ≥ closeout 宣稱的分母；抽 3 筆核對 source_ref 指得回 memo／讀圖原文、entities 是 registry id
  2. python -m pytest -q → 全綠；刪除的測試檔逐檔核對「守的是哪個退役機制」
  3. python -m audit invariants → 全綠；讀 audit/checks.py 確認 Expiry 的「到期未重問＝FAIL」真的存在且有會紅的測試
  4. schtasks /Query /TN StockBotv2-Daily /XML 與 config/daily_routine.json 一致；舊兩個工作不存在；最近兩天的 daily_run_*.json 每步有結果
  5. 讀 crons/daily_task.py 的 DAILY_STEPS：沒有 LLM、git、serve、任意欄位寫入者；讀 .codex/rules：只剩 triage 需要的
  6. python -m crons.heartbeat --out <temp> → 五段都在；段 2 有 watch 計數與反證在盯／未盯；段 3 有 pq2 逐筆與距上次掃題材
  7. engine_b/todo.py 的 watch_decision：GO_AUTHORIZATION 不含任何 authority；config/standing_authorization.json 的 never 有它；續等不掛 waiting_on
  8. AGENTS.md 與 1.0 前的差異只有 §0.4 那兩句
  9. 舊 Decision Store sha256 與 live_choices ＝ baseline
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不跑會寫 library/ 的命令
```

### 結案之後：停，不要開 Phase 2

R2 回 GO 後：ROADMAP Phase 1 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。
然後 **`AWAITING_HUMAN`**：Phase 2 還沒有 plan。HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令，
並在 closeout 附「本 Phase 執行中發現、Phase 2 要決定的問題」清單（種子見 §15）。

## 14. 已知陷阱

- **`WATCH_KINDS` 有一串平行消費端**（`watch_detail`、`_render_watch`、`counters`、`wake_target`、CLI、`queue_segments`、audit、webapp watches kind、心跳）。2026-09-02 漏一處讓 daily 整批 KeyError、38 筆 watch 一輪 0 檢查。用參數化測試守，不要靠記得。
- **「恰好擇一」的喚醒目標**：新增 `disproof_ref`、`wake_reading` 兩種後，`add_watch` 的擇一檢查、`wake_target()`、`counters` 要一起改。
- **只有語意型跳過 triage `go`**；其他 kind 的 T0 判準一個字都不能動（1.4 的 L11-6 ④ 就是在驗這件事）。
- **`writer_lock` 同 owner 是續期不是互斥**：scheduled／triage／interactive 三個 writer 三個 owner。
- **層規則**：`alpha/`（providers 以外）不得 import `engine_b`；`crons` 不得 import `audit`；`crons` 能不能 import `briefing`、`thesis` 能不能 import `engine_b`——動手前查 `tests/test_layer_separation.py`。
- **心跳只讀**：不得在心跳裡開 subprocess、連網或讀 Sheet；排程比對與 NAV 都由 daily 的步驟產生、心跳讀結果。
- **Windows 工作設定**：舊心跳工作的 `ExecutionTimeLimit` 是 10 分鐘，合併後一定不夠（config 驅動，≥45 分）；照抄 `InteractiveToken` 與 `StartWhenAvailable`（電腦 05:30 沒開時開機後補跑）；入口一律 Python（`.cmd` 會被 cp950 讀壞，見 heartbeat_task docstring）。
- **Windows PowerShell 5.1 的 UTF-8 管線**：publisher 一律 `--brief-file`，不要 pipe 中文。
- **Codex automation 的舊 prompt 指向 `crons/daily_brief_prompt.md`**：1.3 封存並刪除原檔，舊設定若被誤開會在第一步停下；使用者改設定前 Codex daily 維持 PAUSED。
- **thesis 反證章節的編號與格式不一致**（AXT 在 §7 用 `-`，後面接 `### 7b`；COHR §6 用 `-`；Sivers §6 用 `1.`）：以標題含「推翻」定位、數到下一個**任何層級**標題為止。
- **EDGAR lead 74% 是 Form 4**：語意型必須排除持股申報，否則大公司的 watch 會被數十筆 Form 4 淹沒（2026-09-09 NVDA／TSM 同型事故）。
- **`_mark_source_cleared` 永不自動 resolve**：`watch_decision` 的結案要在動詞處理的同一個動作裡明確做。
- **大檔手術**：`crons/heartbeat.py` 925 行、`engine_b/todo.py` 2035 行。Phase 0 的教訓：按「下一個 def」切區塊在大檔上誤刪過五次活程式——切之前先列出區間內所有頂層定義。
- **新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`**（`tests/test_config_tracking.py`）；本 plan 盡量只改既有 config。
- **`LOCAL_RETENTION` 3 → 7** 會多用磁碟；改前看一份備份多大（`backups/` 目錄）。
- **健康審查今天就有一盞紅燈**（重複 SourceDoc）：daily 每天都會印它，直到有人修——不得為了讓 daily 安靜而隱藏它。
- **Windows：python 不認 `/tmp`**，暫存用 `%TEMP%`；大段文字用 Write 工具，不要用 heredoc（>8 KB 會截斷）。
- **現況數字會腐壞**：寫進文件的每個數字附查證命令；引用自家文件的數字前先跑命令。

## 15. 結案時要列的待決問題（種子；執行中發現的往下加）

1. **Form 4 機械 FILTER**：305 筆、入圖 0，依 L4 本來就不入圖；改成機械 FILTER（附理由與計數）可省約一半 triage 量。要不要做、放哪個 Phase？
2. **重複 SourceDoc 紅燈**：要動圖（authority），誰、什麼時候修？
3. **`weekly:` 與 `theme_scan:` 同一管道**：Phase 5 量測管道產出時要合併計算。
4. `counter_path_relation` 字彙（Phase 2 走圖要不要接）、`{assumption:…}` placeholder 回填（Phase 3）、`argument` 標題（Phase 2／3）——Phase 0 延下來的三題。
5. Drive 備份要不要自動化（OAuth consent 發布 Production 之後才可行）。
6. `scripts/catalyst_watch.py` 失去消費端之後要退役還是留作互動入口。
