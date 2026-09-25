# Phase 1 等待與心跳——結案報告（2026-09-25）

> plan：[`docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md`](../plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md)；
> 基準：[`2026-09-24-phase1-baseline.md`](2026-09-24-phase1-baseline.md)；決定紀錄 G1–G12：
> [`docs/brainstorms/2026-09-22-graph-first-direction-decision.md`](../brainstorms/2026-09-22-graph-first-direction-decision.md)。
> 本檔每個數字都附查證命令；數的是**等待 registry 的筆數與狀態、pq2 項目、daily 執行紀錄、機制存在與否**（plan §12），
> 沒有一個是「幾檔通過某個 filter」。

## 0. Phase 1 做了什麼（23 個 commit，2026-09-24 → 09-25）

| Step | commit | 一句話 |
|---|---|---|
| 1.0 | b07427b | 基準快照（watch 95／active 90／semantic 0；pq2 球在你 0；2180 測試；invariants 13 PASS；舊店 sha256） |
| 1.1 | e830c72 | 舊 Decision Store 讀取端改連線層唯讀（7 個呼叫端 `open_readonly_store()`，可寫入口整支拿掉） |
| 1.2a | dcc8d2c | 一個 Windows daily：封閉步驟清單、config 唯一時間來源、註冊命令、自我比對、最外層保證、鎖續期 |
| 1.3 | 3d5daa1、c8a7dea、fc5304d | triage 併進 daily：`claude -p` 零工具提議、每次 init 能力檢查、`triage-apply` 程式寫入；`.codex/rules` 12 → 0；R2-a GO |
| 1.4 | 5c5d875 | `semantic_condition` watch：feed 宣告一手與公司、回填實體、排除持股申報、不看 triage；語意預篩只標旗 |
| 1.5 | f9b8e7c | 反證登記 hook（讀圖 v2 `disproof[]`、thesis 由 `todo sync` 對帳）＋ `wake_reading` ＋ 計數 ＋ 觸及後的 `thesis_lifecycle` |
| 1.6 | 1c60b29 | 既有反證補登記（強模型）：thesis 16 條＋讀圖 v2 兩份 11 條＋需求側客戶 `wake_reading` 5 |
| 1.7 | c9e950f、19120b9、155f6ec、b67f1fb、259147c、53d4838 | 到期處置：A7（thesis／讀圖來源併進複查與重讀、`watch_decision` 只給假設型）；R2-b 兩次 NO_GO → 回滾 → 修 → 第三輪 GO |
| 1.8 | 5134575 | 心跳改版：較昨 diff、備份／健康／invariants、watch 今日與反證計數、pq2 逐筆、NAV、計分表每天、Discord 摘要行 |
| 1.9 | 1a1217f | 題材掃描：weekly 退役、`skills/theme-scan`、session 開頭「距上次掃題材 N 天」、AGENTS 兩句逐字改寫 |
| 1.10 | 2299f9f、f2159f7 | 稽核改讀新的等待 registry（Lifecycle／Expiry／Orphans／QueueLiveness） |
| 1.2b | fc0f2a6 | 舊兩個 Windows 工作與 `crons/heartbeat_task.py` 刪除；排程只剩 `StockBotv2-Daily` |
| 結案前置 | bf0bf7e | 心跳「今日醒」漏算當輪就排回的醒來（09-24／25 真醒 2／3 筆都印 0；L13 同形） |
| 結案 | 17e6dc1、（本 commit） | 本報告（R2 前）；R2 GO 後處置 N1、ROADMAP Phase 1 ✅、plans README completed |

## 1. 九項 completion gate（plan §13）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試數差＝新增－退役（逐檔） | ✅ **2520 passed, 1 skipped**（基準 2180 passed）；測試檔 **183 ＝ 175（基準）＋ 8（新增）− 0（刪除）**，無改名。新增：`test_audit_waiting`、`test_daily_task`、`test_decision_store_readonly`、`test_disproof_registry`、`test_heartbeat_phase1`、`test_semantic_watch`、`test_triage_apply`、`test_watch_expiry`。**沒有刪任何測試檔、沒有改名**；但在既有檔裡**拿掉 33 個測試函式、加 26 個**（6 檔，逐條去向見 §3；R2 N1 更正本檔初稿「唯一是 1.2b 那 5 條」的說法） | `python -m pytest -q`；`git log --diff-filter=A --name-only --pretty=format: b07427b..HEAD -- tests/`（`--diff-filter=D` 為空） |
| 2 | `python -m audit invariants` 綠（含 1.10 新判準） | ✅ **13 項 PASS／0 FAIL（共檢查 4730 筆）**；1.10 的新判準（`Lifecycle` 讀 watch 收據 127 筆、`Expiry` 116 個等待全有到期與去處、`Orphans` 134 個跨檔引用、`QueueLiveness` 142 項）都在其中。今天 05:30 那輪 daily 的 ⑮ 是 FAIL 1（Expiry＝[586] `pending --trigger` 沒有到期）；使用者當天補 `--until 2026-12-31` 後轉綠 | `python -m audit invariants` |
| 3 | 無未解釋語意 diff | ✅ **心跳**：與 1.0 那份（09-24 07:00 舊版）逐行對照，拿掉的三行都有取代行——「事件監看：本輪該查／已觸發未消費／到期」→ 段 2「watch：今日醒…」＋段 3「watch 到期…」（偏差 #21，T2 輪詢已移出 daily、沒有 consumer）；段 3「（零＝真的沒有，不是沒跑）」→ 刻意刪（恆真，1.2a），由「分類層：本輪…」與 harvest 過期 ⚠ 說話；段 5「計分表是 weekly 才算的」→ 每天的 tier 分布。五段不增不減。**APP 個股頁**：同一天（09-25）materialize 前後 `--per-panel` digest **逐字相同**（368 行 diff 0；materialize 80/80 成功）。⚠ 限制照實寫：「前」那份是 05:30 daily 以 2299f9f 的程式產生，所以同日比對只證明 1.2b 與 bf0bf7e 沒動個股頁；Phase 1 整體的證據是**程式面**——對 `webapp/`、`alpha/` 的改動只在 watches／positions／structure_readings 三個 state kind、讀圖 contract 與 `alpha/cli.py`，沒有碰個股頁 builder（`git diff --stat cb4b9c4..HEAD -- webapp/ alpha/`）。參考：對 1.0 基準那份（09-24），292 個面板沒有多也沒有少，變了 25 個（research 22、brief 3——AXTI／COHR／LITE 三本短評，數字 placeholder 每天由 authority 填）；**未逐面板歸因** | `python -m crons.heartbeat --out <temp>`；`python scripts/analyst_view_text_digest.py --per-panel` 在同一天 materialize 前後比對 |
| 4 | 無新 dual authority | ✅（一個列出的例外）排程時間只住 config（兩天的自我比對都 `match`）；Codex 沒有自己的時間、不在任何無人值守步驟（兩個 automation `PAUSED`、`.codex/rules` 0 條）；等待只住 registry（`watch_decision` 續等不掛 `waiting_on`，`engine_b/todo.py` 的三個動詞與 `tests/test_watch_expiry.py`；觸及後的等待住該 thesis 的 `thesis_lifecycle` 那一筆）；**triage 判斷的寫入者只有 `leads.triage()`**（CLI `triage` 與 `triage-apply` 共用，`engine_b/cli.py`）。⚠ **例外照實列**：`leads.requeue_trace`（`engine_b/leads.py:928`）在 watch 叫醒舊 lead 排回 pq1 時機械地寫一筆 `triage`（`decision: go`、沿用舊 tier 與分類）——Phase 1 之前就存在（[321]），不是判斷而是重排；1.3 的 c8a7dea 已讓心跳「分類層上次成功」排除它；它排回的 lead 缺分類就是 §7 #14。是否該改成不寫 `triage` 列 §7 #17 | `grep -n 'lead\["triage"\] =' engine_b/leads.py`；`grep -n "leads.triage(" engine_b/cli.py` |
| 5 | 無 silent drop | ✅ 各有計數或理由現形：持股申報排除（`test_t0_matrix`）、追源型到期結案（心跳「追源到期結案今日 N」、`trace_expired_closed`）、預篩額度截斷與無全文／無 fetcher／截斷／引文拒收（心跳段 3 預篩行；`test_semantic_watch` 的 prepare／apply 各條）、LLM 能力檢查不符（執行紀錄 `violations`；`test_daily_task` 能力檢查各條）、feed 新欄位驗證錯誤（`test_provenance_error_is_counted_not_silently_dropped`）、叫不醒的反證（心跳段 2「叫不醒 2」、`semantic_unreachable`）、`triage-apply` 拒收（心跳「拒收 N」、`tests/test_triage_apply.py`）、`published_at` 解析不到（`test_unparsable_published_at_falls_back_to_first_seen_and_is_counted`）、sidecar 與 memo 不符（心跳常駐行、audit `Orphans`） | 見各測試；`python -m engine_b.event_watch counters` |
| 6 | Point-in-time | ✅ 語意比對只用 watch 建立之後的 lead（`test_t0_matrix`：`first_seen` 早於建立、`published_at` 早於建立日都不醒）；`published_at` 解析不到時退回 `first_seen` 並計數，不以抓取日冒充（`test_condition_dates_and_published_at_parsing`）；audit `PointInTime` PASS | `python -m pytest tests/test_semantic_watch.py -q` |
| 7 | lifecycle 可達 | ✅ 到期 → pq2（假設型 `watch_decision`、pq2 型翻回）／併進複查與重讀（A7）／追源型終局，判定觸及 → `thesis_lifecycle`，都有測試（`tests/test_watch_expiry.py` 72 條、`tests/test_disproof_registry.py`）；`Expiry` 與 `QueueLiveness` 新判準綠且有會紅的測試（`tests/test_audit_waiting.py`，1.10 的 18 條變異全紅） | 同 1、2 |
| 8 | executable protection | ✅ `tests/test_daily_task.py`：`DAILY_STEPS` 逐項相等、LLM argv 逐項相等（`--tools ""`、`--strict-mcp-config`、`--setting-sources ""`、`disableAllHooks`、`autoMemoryEnabled:false`、`--disable-slash-commands`、`--include-hook-events`、`--json-schema`，禁用旗標不出現、cwd 在 repo 外）、環境變數白名單（擋 `ANTHROPIC_API_KEY`／`NOTIFY_*`／`X_*`）、能力檢查每種不符與六欄各自缺席、init 不符在 result 前殺行程、`run_id` 配對、保險檢查指紋與順序（`.git/config` 變了不跑 git）、自我比對、進迴圈前例外仍發心跳、鎖續期；`tests/test_triage_apply.py`、`test_semantic_watch.py` 的 apply 拒收；`tests/test_codex_daily_permissions.py::test_rules_file_has_zero_prefix_rules`；排程器實跑的 init 原值見 §4 | `python -m pytest tests/test_daily_task.py tests/test_triage_apply.py tests/test_codex_daily_permissions.py -q` |
| 9 | 驗收數的是 registry 與機制存在與否 | ✅ §2 每個數字都是 watch 筆數／狀態、pq2 項目、執行紀錄、工作清單 | — |

**另核對（plan §13）：** 舊 Decision Store 三個 `*.db` 的 sha256 與 `live_choices` 與 1.0 逐字相同（§5）✅；兩個 Codex automation `status = "PAUSED"`（不是 ACTIVE）✅、
執行紀錄的 triage 步驟最近兩天都有結果（§4）✅；1.6 ✅；1.2b ✅；`AGENTS.md` 與 Phase 1 開工前（cb4b9c4）的差異只有 plan §0.4 核准的兩句（`git diff cb4b9c4 HEAD -- AGENTS.md`：2 行改 2 行）✅。

## 2. ROADMAP Phase 1 驗收①–⑤

| # | 驗收 | 結果 | 層 | 查證 |
|---|---|---|---|---|
| ① | `semantic_condition` 0 → ≥ 16＋兩份現行讀圖條數，並寫出可被動喚醒 N、叫不醒 M | ✅ **0 → 27**（thesis 16：AXT 6、COHR 5、Sivers 5；讀圖 11：`mat:inp_substrate` 6、`tech:cw_dfb_laser` 5）；**可被動喚醒 25、叫不醒 2**（AXT §7-3 的 JX／住友沒有任何 feed、`mat:inp_substrate` ③ 的 IQE 沒有一手 feed）；另有需求側客戶 `wake_reading` 5 | 等待 registry（分母：敘事＝thesis、讀圖） | `python -m engine_b.event_watch counters`（`semantic_active` 27、`semantic_unreachable` 2）；逐條表 [`2026-09-24-phase1-step16-disproof-registration.md`](2026-09-24-phase1-step16-disproof-registration.md) |
| ② | 心跳出現第一次真實的「今日醒 ≥1」 | ✅（附註）**真實喚醒已發生**：09-24 醒 2 筆（`ew_0042`、`ew_0055`）、09-25 05:32 醒 3 筆（`ew_0066`／`ew_0091`／`ew_0093`，被新的 AXTI 公告 `lead_cad23eb9…` 叫醒、當場排回 pq1）。**但排程發出的兩份心跳都印「今日醒 0」**：計數只看現行 `woken_by`，當輪就排回的醒來紀錄已移進 `reactivations`（L13 同形）。bf0bf7e 修正後，同日以真實資料重組的心跳印「**今日醒 3**」。排程心跳第一次正確印出 ≥1 要等下一次真實喚醒 | 等待 registry | 心跳段 2；`event_watches.json` 各 watch 的 `reactivations[].woken_by.at` |
| ③ | 心跳印「未檢 N」且 N>0 | **已交付、未生效**：27 條語意 watch 到今天沒有一條被一手文件叫醒（`semantic_pending_check` 0）；心跳每天照印「未檢 0」。機制由 `tests/test_semantic_watch.py`（醒來＝待檢、預篩只標旗不減少未檢）證明 | 等待 registry | 心跳段 2；`python -m engine_b.event_watch semantic-queue` |
| ④ | 到期的 watch 不消失（A7） | **已交付、未生效**：真實資料 expired 0；最早的讀圖來源到期 2026-11-17（`tech:cw_dfb_laser` 5 條，11-18 轉 expired）、假設型 2026-12-31（`ew_0004`／`ew_0006`，2027-01-01 轉 expired）。機制由 `tests/test_watch_expiry.py`（72 條）與 1.7 的時間快轉試跑（到 2027-10：`watch_decision` 27+ → 4、pq2 球在你 31 → 6）證明。⚠ watch 的「今天」是 UTC 日期（§7 #16），daily 裡實際轉 expired 會再晚一天 | 等待 registry → pq2／複查／重讀 | `python -m engine_b.todo list`；`python -m alpha structure-reading <node> --check` |
| ⑤ | 一個 Windows daily、每天一則 Discord、時間與 config 一致、triage 是其中一步 | ✅ `schtasks /Query` 只剩 `StockBotv2-Daily`（05:30、時限 240 分鐘，與 config 一致）；09-24 run `9dffbd83`（`schtasks /Run`）與 09-25 run `4fe5bce1`（**第一次排程自然觸發**，`Last Result 0`）都 completed、自我比對 `match`、Discord `sent`；triage 兩天都有結果與 session id（§4） | 機制存在與否 | `schtasks /Query /FO LIST`；`library/private/heartbeat/daily_run_*.json` |

**②③④ 的回查（使用者 2026-09-25 定案：用心跳計數器，不另建等待）：** plan §0.1 #6 原寫「登記回查用的 date watch」，但 date watch 醒來只能叫醒 pq2 編號，
而 AGENTS「開發項不走 pq2」——兩者衝突，結案時向使用者提出，使用者選「用心跳計數器」。回查的載體因此是已經存在、會自己出現的計數器：
心跳段 2 每天印「今日醒 N」與「未檢 N」、段 3 每天印「watch 到期：今日／累計＋處置逐格」；「較昨變動」的封閉快照鍵含
`semantic.pending_check`（③）、`watch.expired`、`disproof.expired_pending`（④），**第一次從 0 變成非 0 的那天 Daily 會自己印出來**。
下一個 Phase 的 plan（或 closeout）核對③④是否已生效並補記。這是「拿掉一個機制」的做法：不新增 pq2 編號、不新增 watch。

## 3. 測試跟機制走（沒有刪測試檔；函式層級拿掉 33、加 26；不可越線 8）

⚠ 初稿本節寫「唯一的『測試跟機制走』是 1.2b」——**錯**，R2 N1 抓到。以 `cb4b9c4` 為起點逐檔比 `def test_` 名稱（查證命令見 §9），6 個既有檔拿掉 33 個函式、加 26 個：

| 檔 | 拿掉／加 | Step | 拿掉的守什麼 → 現在由誰守 |
|---|---|---|---|
| `test_codex_daily_permissions.py` | 13／4 | 1.3 | 舊 `.codex/rules` 12 條逐條（每條 parse 得到、窄 rule、fetchers 不整包放行、sweep 不升權、相鄰命令不放行）→ rules **0 條**：`test_rules_file_has_zero_prefix_rules`、`test_every_retired_prefix_is_no_longer_allowed_by_the_parser`（Codex 自己的 parser 驗舊 12 條都不是 allow）、`test_adjacent_commands_are_not_allowed_either`、`test_retired_list_matches_the_history_written_in_the_rules_header`。掛在 rules 上的**活判準改主詞**到 `tests/test_daily_task.py`：materialize 不含 serve（`test_daily_runs_materialize_but_never_serve`）、機械段跑而使用者動詞不跑（`test_mechanical_segments_run_but_user_verbs_never_do`）、XBRL 只寫一個欄位（`test_xbrl_backfill_is_the_only_engine_c_manual_writer_and_writes_one_field`）、scorecard 網路上限在程式裡（`test_scorecard_network_surface_has_a_hard_cap_in_code_and_the_review_admits_it`）、MOPS 主機寫出來且月營收留在互動（`test_mops_hosts_are_written_in_the_review_and_monthly_revenue_stays_interactive`） |
| `test_routine_prompts.py` | 8／8 | 1.3、1.9 | 舊 Codex daily／weekly prompt 的內容斷言（兩份 prompt 已逐字封存）→ 封存本身（`test_codex_daily_prompt_is_archived_not_live`、`test_weekly_prompt_is_archived_not_live`）、triage prompt 零工具／資料不是指令／不寫死上限、題材掃描只發現不處置、互動 brief 預設不發第二則、canonical brief 逐字輸出、決策區塊只改閱讀順序 |
| `test_heartbeat.py` | 8／10 | 1.2b、1.8 | 舊入口 5 條 → `test_daily_task.py`「無人值守入口」節（下表）；weekly 計分表 3 條 → 每天印（`test_scorecard_prints_every_day_with_tiers_change_and_where_the_full_table_is`、`test_scorecard_without_artifact_says_so_instead_of_rebuilding`）；`test_weekly_scorecard_is_not_applicable_on_daily` 是**真刪**（weekly 退役，沒有「非 weekly 不適用」可守）。另加段 1／段 3 的 daily 執行紀錄各條 |
| `test_daily_brief_skill.py` | 2／2 | 1.3 | 「排程第一次呼叫走固定入口、重試是最後手段」「排程自動 drain pq1 但保留入圖 gate」→ skill 改互動專用後：`test_source_failures_stay_visible_and_retry_is_last_resort`、`test_pq1_drain_keeps_the_admission_gate` |
| `test_beta_monitor.py` | 1／1 | 1.9 | weekly 完整版 → 「沒變就安靜、完整版要明說」主詞改成 full view |
| `test_fx_sync.py` | 1／1 | 1.2a | 「不在 Codex sandbox 升權」→ 「是 daily 的一步、不經 Codex」 |

**守門變弱的兩處（R2 N1，照實列，§7 #18 待決）：** ①只斷言在已封存 Codex prompt 上的幾句，現在沒有測試守：「同一來源後續成功才算 recovered」（`skills/daily-brief/SKILL.md` 有這句、無斷言）、「不得依 section」、「單檔行情降級不歸零」、「Alpha／Beta 共用」——它們還是不是活判準要先決定；②舊心跳測試要求輸出本身印量測窗、樣本數與三條偏差，新測試只要求「已知偏差 N 條（在 APP）」；偏差在 artifact 層仍由 `tests/test_account_scorecard.py` 守，APP `app.js` 的呈現沒有測試。

1.2b 的 5 條改主詞（守 `crons/heartbeat_task.py` → 守 `crons/daily_task.py`）：

| 舊（守 `heartbeat_task.py`） | 新主詞（守 `daily_task.py`） |
|---|---|
| 入口是 `.py` 不是 `.cmd` | 同，另斷言舊入口不存在、註冊命令跑的是 `crons\daily_task.py` |
| `--dry-run` 只產檔不發送 | `--dry-run` 不建 `DailyRun`：一步都不跑、一則都不發（比舊的更嚴） |
| publisher 失敗 exit 0 | publisher 失敗記進紀錄、run 照樣收尾（exit 0 另由 `test_main_always_exits_zero` 守） |
| 沒產出要說「沒有東西可發」（L13-2） | ⑱ 失敗、⑲ 失敗、publisher 回 `delivery_failed`（讀不到心跳檔）三種都由 `routine_hint` 在開 session 時說——**這三個分支在 daily 側原本沒有測試**，補上 |
| 只有一個出口 | `DAILY_STEPS` 裡唯一連網的發送步驟是 `publish_daily_brief.py`；`daily_task.py`、`llm_step.py`、`heartbeat.py` 都沒有第二條出口 |

四個變異（拿掉 receipt 分支、拿掉心跳失敗分支、dry-run 建 `DailyRun`、`llm_step.py` 加 `urllib.request`）全紅。

## 4. 排程器實跑紀錄（gate 8 要求的 init 能力欄位原值）

| run | 觸發 | ⑦a triage | init 能力欄位（原值） | hook 事件 | 違規 | ⑦b |
|---|---|---|---|---|---|---|
| `9dffbd83`（09-24） | `schtasks /Run`（1.3 驗收） | 13 則 1 次呼叫、session `c241cf2a-5b5d-4484-bf89-2cceb41b3e5c`、`claude-sonnet-5` | `tools ["StructuredOutput"]`、`mcp_servers []`、`plugins` 只有 `agents-md@builtin`／`telemetry@builtin`、`slash_commands []`、`skills []`、`apiKeySource "none"`、`memory_paths` 缺席 | 0 | 無 | 處理 13／PASS 2／FILTER 11／拒收 0 |
| `4fe5bce1`（09-25） | **排程自然觸發 05:30** | 5 則、session `d6d5ae32-5855-416a-9880-be3df68a84ea`、`claude-sonnet-5`、`rate_limit allowed` | 同上（逐欄相同） | 0 | 無 | 處理 5／PASS 3／FILTER 2／拒收 0 |

09-25 那輪 25 步：ok 23、failed 2——⑦c `classification-health` exit 2（兩則被排回的 7 月 AXTI 8-K 缺分類＝§7 #14，燈是設計上要亮的）、⑮ invariants exit 1（[586]，當天已補）。
兩輪都沒有 `integrity_violation`、`capability_violation`。

## 5. 舊 Decision Store（A5 不受傷；不可越線 2）

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

與 1.0 基準（`2026-09-24-phase1-baseline.md` §9）三個檔逐字相同。自 1.1 起讀取端在連線層唯讀（`mode=ro`），可寫入口 `open_default_store()` 已拿掉。

## 6. 等待 registry 現況（結案當下；現況會腐壞，引用前重跑）

`python -m engine_b.event_watch counters`：watch 127（active 114、consumed 13）；語意型 27（在盯 27、叫不醒 2、待檢 0、標旗 0）；
`wake_reading` 5；喚醒 lead 78／pq2 1／假設 3；fired 未消化 0；expired 0。pq2 未結案 2（[586] 等到 2026-12-31、[632]），球在你 0。

## 7. 本 Phase 執行中發現、Phase 2 要決定的問題（plan §13「結案之後」要求；細節見 plan §15）

1. **thesis 引用的 claim 反證要不要登記**（G8「411 條只登記被引用的」）：三份 thesis 引用的 claim 39 條（AXT 11、COHR 12、Sivers 16）全部帶 `disproof_condition`（1.6 報告 §5）。
2. **重複 SourceDoc 紅燈**（健康審查唯一 🔴）：要動圖（authority），誰、什麼時候修。
3. **`weekly:` 與 `theme_scan:` 是同一管道**：Phase 5 量測管道產出時要合併計算。
4. Phase 0 延下來的三題：`counter_path_relation` 字彙（Phase 2 走圖要不要接）、`{assumption:…}` 回填（Phase 3）、`argument` 標題（Phase 2／3）。
5. **Drive 備份要不要自動化**（OAuth consent 發布 Production 之後才可行）。
6. **`scripts/catalyst_watch.py`** 失去消費端，退役還是留作互動入口。
7. **daily 要不要做研究**（`pq1.drain_limit_per_run` 0 → N＝改 AGENTS 判準句，走 amendment）。
8. **預篩全文的覆蓋**：`sivers:press` 等沒有 fetcher；MFN 不抓 PDF 附件、EDGAR 不抓 EX-99。結案時實際數字：預篩 0 次（沒有語意 watch 醒過），無從判斷比例——建議等 ③ 生效後再決定。
9. **`claude -p` 的 context 仍帶帳號 email**（訂閱登入）；init 的 `agents` 欄要不要納入能力檢查。
10. **AXT `### 7b` 的 variant 推翻條件**（「Q3 2026 營收 ≥ US$60M」）要不要登記。
11. **一則 Sivers 一手公告會同時叫醒 7 條語意 watch、預篩每日名額 10**——工作量，不是錯。
12. **R2-b 第三輪 NB3-10、NB3-11 (a)(b)(c)(e)**（觸及待處置遇 memo 換版的處置入口、試跑所見）。
13. **`pending --trigger` 不帶 `--until` 仍被接受**：提案 `--trigger` 必須同時帶 `--until` 或綁 watch（動 CLI contract）。
14. **追源 watch 把已終局的舊 lead 排回 pq1、排回後缺分類**（09-25 第一次自然觸發；daily ⑦c 亮燈）：已終局的 trace 要不要被排回、缺分類怎麼接。
15. **使用者動作**：要用 Codex 互動 session 需信任 1.9 新增的 SessionStart hook。
16. **watch 的「今天」是 UTC 日期**，daily 在台北 05:30（UTC 前一天）跑：daily 裡的到期判斷一律比本地日期晚一天、執行紀錄檔名卻用本地日期。要不要統一成 `schedule.timezone`（動 contract）。1.2b 已把兩條以本地日期寫死的測試改成讀程式的 `_today()`。
17. **`leads.requeue_trace` 機械寫 `triage`**（gate 4 例外）：watch 排回舊 lead 時寫 `decision: go`、沿用舊 tier——它是重排不是判斷，要不要改成不寫 `triage`（例如另記 `requeued_by`），讓「triage 寫入者只有 `leads.triage()`」字面成立；與 #14 同一處。
18. **封存 prompt 帶走的幾句判準還是不是活的**（R2 N1）：「同一來源後續成功才算 recovered」「不得依 section」「單檔行情降級不歸零」「Alpha／Beta 共用」
    原本只斷言在已封存的 Codex daily prompt 上，現在沒有測試守；是活判準就補斷言（守它實際住的地方），不是就在封存說明裡寫明退役。
    另：計分表的量測窗／樣本數／三條偏差在 APP `app.js` 的呈現沒有測試（artifact 層有）。
19. **讀圖 v2 `disproof[]` 的出處欄位**（R2 N2；L18）：`tech:cw_dfb_laser` 現行讀圖 `sr_d07679979a8e4202` 的散文沿用前一份、寫「六條」，
    而 `disproof[]` 5 條是從 `sr_a181641ddb99c69c` 逐字搬來、各項沒有指回來源紀錄的欄位——追回原文要跳兩層，這條鏈只記在 1.6 報告與偏差 #15。
    ledger 是 append-only 不能改；要不要在 v2 contract 給 disproof 項加出處欄位，或下次重讀該節點時讓散文與 `disproof[]` 自洽——Phase 2（讀圖是主角）決定。

## 8. R2 結果

**2026-09-25 台北 07:59–08:12，乾淨 context 的 reviewer，唯讀（對 `17e6dc1`）。Verdict：GO。** 九項全 ✅；blocking 0；non-blocking 3。
reviewer 另做了本檔沒有的反證：audit 三組記憶體內變異（`_TOUCHED_GRACE`、`_EXPIRY_GRACE` 放大、`_open_review_ids` 恆真）各自讓對應測試轉紅；
`codex execpolicy` 以**舊** rules 檔跑同樣 12 條全回 `allow`（證明對現行 rules 的「不是 allow」不是空轉）；語意 watch 14 個實體全在 registry、
抽 4 筆（Sivers `ew_0107`、`tech:cw_dfb_laser` `ew_0122`、叫不醒的 `ew_0114`／`ew_0098`、POET `ew_0124`）逐字對回原文與一手 lead 交集。

| # | finding | 處置 |
|---|---|---|
| N1 | 本檔 §3 初稿說「唯一的測試跟機制走是 1.2b 那 5 條」，實際 6 檔拿掉 33 個函式；其中兩處守門變弱 | **結案 commit 當下修**：§3 改成函式層級逐檔去向（自己重跑比對，33／26 相符）、gate 1 那格改寫；變弱的兩處列 §7 #18 |
| N2 | `tech:cw_dfb_laser` 的反證要跳兩層才追得回原文（L18） | append-only 不能改；列 §7 #19 給 Phase 2 |
| N3 | 同一輪兩種「今天」（心跳用本地、watch 到期用 UTC） | 已是 §7 #16，reviewer 確認現象屬實；不另處置 |

## 9. 附錄：本次實跑的命令

```powershell
schtasks /Query /TN StockBotv2-Daily /V /FO LIST
schtasks /Query /FO LIST | Select-String StockBotv2
python scripts\register_daily_task.py --retire-legacy
python -m pytest -q
python -m audit invariants
python -m engine_b.event_watch counters
python -m engine_b.todo list
python -m crons.heartbeat --out <scratchpad>\hb_check.md
python scripts\writer_guard.py check
python scripts\analyst_view_text_digest.py --per-panel      # materialize 前
python -m webapp materialize --tracked --registry-listed --structure-table --beta --coverage --watches --positions --structure-readings --scorecard
python scripts\analyst_view_text_digest.py --per-panel      # materialize 後
git diff cb4b9c4 HEAD -- AGENTS.md
git log --diff-filter=A --name-only --pretty=format: b07427b..HEAD -- tests/
# 函式層級：對 cb4b9c4 的每個 tests/test_*.py，比 `git show cb4b9c4:<檔>` 與 HEAD 的 `^def test_` 名稱集合（§3 的 33／26）
```
