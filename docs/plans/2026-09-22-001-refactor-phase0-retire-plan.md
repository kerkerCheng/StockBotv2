---
date: 2026-09-22
topic: phase0-retire
status: active
derived_from: docs/ROADMAP.md（Phase 0）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G1–G12）
---

# Phase 0 拆：退役估值鏈、排序驅動、decision_lab 研究側（給執行模型的完整 plan）

> **執行者：便宜模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。**
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 0」與「Phase 0 退役清單」導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → ROADMAP「Phase 0」「退役清單」「decision_lab 凍結」「硬約束」→
> `docs/refactor/historical-failure-matrix.md` §2 六條 invariant → `docs/OPERATIONS.md`「sandbox impact review 五步」→ 本 plan。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字全部是「殭屍 grep 命中數」「state kind 數」「pq2 未結案數」
> 「Decision Store sha256」這類**機制存在與否**的計數，不是研究結果。

---

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-09-22 已核准的 PLAN_PROPOSAL。** 0b 的 Z2 不再停等核准；`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step，Step 與 Phase 邊界一視同仁**，做到 Phase 0 結案為止。
只有六條停止條件之一成立才停（其中本 Phase 會撞到的只有：§6「撞到就停」的切不開情況、Verdict 不是 GO、需要 R2）。
0c 的 pq2 批次 drop 已授權（見 §4），不再回頭請求。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（使用者 2026-09-22 定案）**：0b.4 動到成交路徑硬擋時直接發 `WORK_REQUEST`，不停下來問。

**每個 Step 一個 commit，訊息第一行寫 Step 編號；Step 為 GO 就 push。** 這是續工的唯一依據：新 session 先看下面進度表與 `git log --oneline -20`，
從第一個未 ✅ 的 Step 接續，不重做已 ✅ 的。進度表由執行者在每個 Step 的 commit 裡更新（把 ○ 改 ✅ 並填 commit 短碼）。

**同一 working tree 只讓一個 writer 寫入：** 執行本 plan 期間**暫停 Codex daily／weekly 排程**（它們與 0a.1、0a.2 改的是同一批檔），Phase 0 結案後再開。

> **排程狀態（2026-09-22 15:28 實測，Step 0.0 記錄）：** 本機唯二的排程 writer `StockBotv2-Heartbeat`
> 與 `StockBotv2-FxSync` 下次觸發都是 **2026-09-23 早上**；今天是星期二，Codex weekly（週日）不跑，
> daily（台北 06:30）同樣是明天。**今天沒有第二個 writer，所以未停排程也不衝突。**
> ⚠ **時限 2026-09-23 06:30**：Phase 0 若跨到明天早上，續工的第一件事是先暫停排程再動手。
> 查證與細節見 [基準報告 §0](../reports/2026-09-22-phase0-baseline.md)。
>
> **續工實測（2026-09-23 07:39，C／H 2/2 開工前）：** `StockBotv2-FxSync` 06:55、`StockBotv2-Heartbeat` 07:00 今早都已跑完
> （LastResult 0），下次 **2026-09-24 早上**；Codex daily 06:30 沒留下任何 commit 或 tracked 變更（`git status` 乾淨，
> `library/` 只有心跳／FX 的觀測輸出）。**今天仍沒有第二個 writer。** ⚠ 新時限 **2026-09-24 06:30**。
> 查證：`Get-ScheduledTask | ? {$_.TaskName -match 'StockBot'} | Get-ScheduledTaskInfo`、`git log --since=2026-09-23`。

**進度表的 commit 欄：** 一個 Step 的 commit 短碼在它自己的 commit 裡算不出來（填進去就會改變雜湊），
所以**由下一個 Step 的 commit 補填**；`○ → ✅` 本身在該 Step 的 commit 裡完成。

| Step | 內容 | 狀態 | commit |
|---|---|---|---|
| 0.0 | 基準快照 | ✅ | d6e3fca |
| 0a.1 | 排程與規則停跑 | ✅ | 36f59f9 |
| 0a.2 | 心跳與 APP 入口停跑 | ✅ | b65c1a1 |
| 0a.3 | 研究 skill 改句 | ✅ | 4c78df4 |
| 0a.4 | 池子收集端停鑄 | ✅ | 20f21a4 |
| 0b.1a | 個股頁消費層：why／entry 退役、argument 升核心、尺與四價下架 | ✅ | e38c7ee |
| 0b.1b-D | D 組整組退役：多年反向橋＋要幾倍＋那把尺 | ✅ | 2fb7960 |
| 0b.1b-C | C／H 組：估值鏈與隱含報酬（兩段，見下） | ✅ | 3be1756＋2/2 |
| 0b.1b-F | F 組整組退役：entry criterion（進場門檻） | ✅ | c1d0331 |
| 0b.1b-E | E 組整組退役：賭注四價 overlay（含 downside、target_reached） | ✅ | bd34a63 |
| 0b.1b-C/H（1/2） | 估值品質計數器（closure 三個數＋webapp 消費端） | ✅ | 3be1756 |
| 0b.1b-C/H（2/2） | **樞紐**：拆 6 個 section、刪 `alpha/valuation`／`alpha/implied_return`／`alpha/fundamental` 模型半邊（§0.9；偏差 §0.6 #18–27） | ✅ | 1ed420e |
| 0b.2 | 刪估值鏈（收尾：expectation_gap 腳本、`multiple_horizon` 讀寫；偏差 §0.6 #28–31） | ✅ | |
| 0b.3 | 排序與籃子 | ○ | |
| 0b.4 | 四價、decision_lab 凍結、硬擋搬家、活文件 | ○ | |
| 0c | 池子 17 筆 drop | ✅ | cd275e3 |（**先於 0b 執行**：兩者無相依，0b.1 撞到 §6「切不開」要停，先把獨立的 Step 收掉）|
| 結案 | 九項 gate ＋ closeout 報告 ＋ ROADMAP 標 ✅ | ○ | |

**開工／續工指令：貼 `/phase-run` 即可**（skill 會照下面這段做；不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 0 結案；撞到六條停止條件才停。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」）

plan 的 §0 說「衝突時以 ROADMAP 與決定紀錄為準，並回頭修本 plan」。下面每一筆都已回頭修過本 plan 的對應段落。

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 0.0 | 只列五條基準命令 | 另存**個股頁文字 digest**（新增唯讀腳本 `scripts/analyst_view_text_digest.py`）、心跳基準、測試檔數、排程狀態 | 結案 gate 3 與 R2 檢查 7 要求「materialize 前後文字不變」，沒有固定配方就證不出來。只 hash 敘事文字，不 hash 數字與時戳——把會隨刷新而動的算進去，gate 永遠紅＝永遠被忽略 |
| 2 | 0a.1 | 「standing_authorization **移除** `decision_review` 類別」 | 從 `authorized` **搬到 `never`** | `ITEM_TYPES` 封閉性驗證要求每種都明寫在其中一邊（`engine_b/standing_authorization.py` 載入時驗）；整格刪掉會讓 config 拒絕載入 |
| 3 | 0a.1 | 「`queue_segments` 移除 reassess-stale 段」 | 同時改 `audit/checks.py` | 它是那個段唯一的資料注入端（`reassess_only_numbers`）。先斷 producer 再刪段，否則稽核會把它算成 `unmapped` 而 INV-4 變紅 |
| 4 | 0a.1 | 0a 的檔案清單沒有 `engine_b/cli.py` | **未動**，留給批 3 | `_chokepoint()` 仍以 `rank_bottlenecks` 的**成員**（不是順序）餵 pq1 優先序。批 3 的 L11-6 註記寫「0a.1 應已移除」，**那句話不成立**——該檔在批 3 才改讀結構表 |
| 5 | 0a.2 | 只列 `webapp/__main__.py` materialize 清單、`api.py` 路由、`index.html` nav | 另外把兩個 kind 從 `webapp/contracts.py` 的**封閉字彙** de-register | 不 de-register 的話心跳段 1 會一直唸「不是今天的 N 份：basket、multi_year」——那正是 0a 要移除的注意力噪音；ROADMAP 驗收③也要求 `webapp status` 不列它們。代價實測只有 7 個測試檔／14 條測試，全部已處理 |
| 6 | 0a.2 | 「段 2 的『現價過目標價』與**籃子行**」 | 段 2 改一行；**段 4 改兩行** | 實測籃子／量的候選／要幾倍／歸零旗標彙總四行都在**段 4**，不在段 2（見基準報告 §8） |
| 7 | 0a.2 | 未提歸零旗標 | 彙總暫停並印 `upstream_unavailable` 明示缺席；**逐檔那盞燈未動** | 歸零旗標是**活的量測**（`AGENTS.md`「量測、訊號、脈絡三分」），但它唯一的 producer 是籃子 artifact。逐檔的燈住在個股頁 `wipeout` 面板（0b.1 明列為核心面板），所以停的只有彙總，且它自己說得出停在哪裡 |
| 17 | 0b.1b | 「批 1 全部斷 import → 批 2 全部刪模組」 | **改成逐組**（D → C/H → F → E），每組的「斷 import ＋ 刪模組 ＋ 刪測試」放同一個 commit | plan 的順序保證是「先斷 import 再刪模組」，逐組做**完全保留**那個保證（組內仍是先斷後刪），但每個 commit 都能全測試綠。原順序會讓中間狀態紅燈跨 session——而紅燈的 suite 沒有鑑別力（下次真的壞掉時看不出差別，L13）|
| 11 | 0b.1 | 「批 1 一個 commit」 | 拆成 **0b.1a（消費層）** 與 **0b.1b（斷 import，逐組）** 兩個以上 commit | 這一批涉及約 24,000 行、20 個檔，`builder.py` 一檔 3,570 行。拆成兩段讓每一段都能保持全測試綠、也讓 diff 讀得完；批 1 的驗收（importer 地圖、materialize 73 檔、blocked 歸屬、三個測試檔）在 0b.1b 結束時整批驗一次 |
| 12 | 0b.1a | 未提 `MarketSection` | **新增** `briefing/alpha_view/contracts.py` 的 `market` section ＋ builder 的 `_market_section` | 現價原本只住在 `ValuationSection`／`ImpliedReturnSection`／`EntryLogicSection` 三個**全部要退役**的 section 裡。它是 A2 觀測（Engine C 收盤快照），與估值無關，卻會跟著模型一起消失。新 section 只有一格、零算術，直接讀 `build.context.market`——與 `sources._current_price` 同一個來源 |
| 13 | 0b.1a | ROADMAP 核心面板列 `headline` | `headline` **留在核心但換主詞**：由「現價 → future target → 隱含報酬」改成「現在多少錢」（只有現價） | 原本的 headline 就是 AGENTS「首屏拿掉尺」指的那把尺，8 格數字全來自估值鏈。留著它又刪掉資料源會讓 73/73 blocked（與 `why` 同一個形狀）。實測現價 73/73 檔 available，所以換主詞後零檔因它 blocked |
| 14 | 0b.1a | 未提 `brief`／`wipeout` 升核心的代價 | 照 ROADMAP 做，並**量出代價**：blocked 由 18 → 70 | 成因歸屬實測：**brief 70 檔、wipeout 3 檔、research 12 檔，fundamental 0 檔**。批 1 的驗收句「blocked 檔數不因 fundamental 缺席而增加」因此成立——fundamental 由核心降選配，只會讓 blocked 變少。⚠ 70/73 是真實 backlog（沒寫短評就是沒有產出），但它同時讓 `forward_view_backlog` 由 11 變成約 70，**下一個 Phase 要注意這個佇列的主詞已經換成「去寫短評」** |
| 15 | 0b.1a | gate 3「argument 文字不變」 | **已用機械方式證明**：把兩個 panel 的標題換回舊字串後，73/73 檔的 `brief` 與 `argument` digest 與改版前**逐字相等**；`research` 與 `our_bet` 本來就 0 檔變動 | 標題改了是刻意的（panel 的角色換了）。除標題外一個字沒動。⚠ `argument` 的 `numbers`／`market` 兩段**還沒拿掉**（它們讀估值鏈），那是 0b.1b 的事；拿掉後 argument 由 6 段變 4 段，實測沒有任何一檔會變空（chain 73／timeline 73／bet 73／risks 63） |
| 16 | 0b.1a | — | `review_required` 不再讓任何核心 panel 的 status 變差 | 背它的那個 panel 是 `why`（status 取估值鏈三段最差）。退役後它只走 refresh／attention 那條路（測試已改問那三個地方）。**Phase 2 讀圖 panel 升核心時要把這條路接回來** |
| 9 | 0a.4 | 「移除 `collect_from_decisions` 的呼叫」 | 從 `SOURCE_COLLECTORS` 登記表移除 `("decisions", …)`，並**刪掉 `include_decisions` 參數與 `--no-decisions` 旗標** | 留一個預設 `True` 的開關等於留一道旁門：傳個參數就把退役的 collector 叫回來（L15：權限要 deterministic）。同時從 `SOURCE_ITEM_TYPES` 移除 decisions 那一列，讓兩個 legacy kind 與 `manual` 同形——缺席不代表完成 |
| 10 | 0a.4 | 未提 `engine_b/cli.py::_cmd_drain` 的 `include_decisions` | **未動**，留給批 3／4 | 它從 Decision Store 讀 work order 餵 pq1。**無人值守那條路已經走不到**：daily 的 `drain_limit_per_run=0`，兩個區塊都是 `if include_decisions and limit:`，`limit` 為 0 直接短路；互動那條路的指示已在 0a.3 從 skill 移除。所以「停跑」已達成，刪除留給批次 |
| 8a | 0a.3 | 檔案清單列 6 個 skill | 改了 **7 個**（多 `skills/lead-intake/SKILL.md`） | 它有 7 處 `decision_lab`／`reassess` 的**可執行呼叫**（Fast Path 的 `evaluate-signal`、Step 7 整節、接點表）。不改它，退役的命令會繼續被 agent 照著跑 |
| 8b | 0a.3 | 驗收寫「`retired_mechanism_grep.py` 的 skills 列 → 0」 | **做不到，且不應該做**：7 個 skill 檔仍有約 44 處命中，**全部是退役註記或 `AGENTS.md` 自己要求的措辭** | 見下方 §0.7。D、F、H 三組的 skills 已歸零 |
| 8c | 0a.3 | 未提 `tests/test_skill_decision_contract.py`、`tests/test_daily_brief_skill.py` | 兩檔的斷言翻面（4 條） | 原本要求兩個研究 skill **必須**出現 Engine D 四支命令、daily-brief **必須**出現 `decision_lab today`。機制退役後那些斷言會逼人把退役的命令寫回去 |
| 8d | 0a.3 | — | 第一版把 daily-brief 的 `--disproof`／`--expiry` 整段**誤刪**（開放式切片吃過頭），已 `git checkout` 還原後改用精確邊界重做 | 反證／催化劑／到期三件套是 L7 與 `AGENTS.md` 的判準、Phase 1 的主角，**不是 Engine D 的東西**。它只是承載欄位從 CLI 旗標換成 ledger 欄位 |
| 8 | 0a.2 | 未提 `webapp/static/app.js` | **未動**，留給批 1／批 3 | nav 已移除兩個入口，但 `renderBasket`／`renderMultiYear` 與 router 分支仍在。手動打 `#/basket` 會拿到 API 錯誤而不是崩潰 |
| 18 | 0b.1b-C/H 2/2 | §0.9「`alpha/fundamental` 的模型半邊只剩 `sources.py` 的 `build_fundamental_model`」 | 模型裡還藏著一條活路：**會計年度別共識**（`ConsensusSection.fiscal_items`）與它的**口徑核實**（`consensus_bases`）是在模型裡算的。搬成取數層直接讀 Engine C（`sources._engine_c_financials`），模型原本的 PIT 自我核對（基期 `recorded_at`／共識 `captured_at`＋`fetched_at` ≤ T）逐條搬過去；`compare.py` 留下 `verify_consensus_basis`／`reconcile_consensus_base`，刪 `compare_metric` | ROADMAP H 列明寫 Engine C `consensus_estimates` 資料**留**（三題「已定價」要用）；不搬就會跟橋一起消失，而 PIT 檢查一起消失是 INV-6 破口 |
| 19 | 0b.1b-C/H 2/2 | §0.9「`gap_closure` 可分開（只需判斷日與共識時序）」 | 可分開，但「朝我們移了幾成」的**分母是內部 EPS**——沒有了。改成只量共識自判斷日以來的移動：`our_value=None`、`closed_fraction` 恆 `None`（不是 0），標籤與理由改寫；`target_reached`／`bet_recorded_on` 一併退役 | 分母消失就不得假裝有比例（Missing != Zero）；量測本身（共識移了多少）仍成立，Phase 3「已定價嗎」接手 |
| 20 | 0b.1b-C/H 2/2 | plan 未提 `alpha/providers/valuation_drift.py`、`scripts/target_pe_drift_check.py` 與心跳「目標倍數背離 N 檔」那一行 | 隨 C 組退役（它讀估值假設 ledger 的 `target_pe` 對市場倍數）；心跳那一行換成 `not_yet_recorded` 缺席宣告「已定價嗎（財務三題）未落地」，**不整段消失**；FX 觀測兩行的主詞由「隱含報酬算不出來」改成「換算依據過期」 | 目標倍數是 C 組 regex；五段永遠出現、拿掉的內容換成缺席宣告（0a.2 同一做法，INV-3） |
| 21 | 0b.1b-C/H 2/2 | plan 未提 refresh 的假設 artifact 是**由模型**登記的（`artifacts_from_model`） | 改成 `artifacts_from_assumptions`：builder 自己跑 `alpha.fundamental.assumptions.select_assumptions`（ledger 邏輯，留下的那一半），拒收原因決定終局——as-of 之後寫的 → missing、其他期間 → missing（基期那一年 → superseded）、被取代／撤回 → superseded、**證據解析不到 → invalidated**——四條判準一條不少；證據索引＝context ＋ 基期觀測／共識／指引／期中實績的 ref（取數層供應）。只登記 base 鏈（overlay 紀錄與退役前一樣不進 refresh）。不再登記 `modeled_metric`／`expectation_comparison`／`fundamental_model`；`artifacts_from_valuation`／`_implied_return` 刪 | 假設的 `review_conditions` 與 Event Watch 的 disproof 目標（`oa_*`）要有 artifact 可掛，否則「假設被推翻」無處現形（INV-3）。第一版漏接證據解析那一條，實測 TSM 的 invalidated 消失、LITE 冒出 30 條 overlay 的「等待中」——materialize 前後對照抓到的（L13） |
| 22 | 0b.1b-C/H 2/2 | plan 未提 opinion stance（「我們有沒有形成自己的觀點」）與 APP 第一屏的 stance 計數器 | 整組退役：`OPINION_STANCES`／`opinion_stance()`／`PLAIN_STANCE`／`PLAIN_MULTIPLE_DERIVATION`／`PLAIN_DRIVER_LABELS`／`overview.opinion_stance`／app.js 的 stance 徽章與橫幅；第一屏計數器改成 `view_counters`（已有判讀／有賭注），**不消失** | stance 是 FY+1 模型對估值假設 `derivation` 的聚合（H 組）；常駐計數器不得消失（L14）。`OPINION_BEARING_DRIVERS` 留：它是 overlay 假設紀錄的型別驗證字彙（L10） |
| 23 | 0b.1b-C/H 2/2 | `scenarios.py` 的 `fiscal_rollover` | 退役（定義是「重跑模型」）；其餘六個情境改吃共識清單／生效假設／基期結束日／目標期間，不再吃 `FundamentalModelResult` | 沒有模型可重跑；`--scenario` 的 choices 同步 |
| 24 | 0b.1b-C/H 2/2 | 「`test_fundamental_model` 整檔退役」 | 45 條測試退役，但它的**資料夾具**（基期觀測／假設／共識）被 7 個存活測試檔引用 → 搬到 `tests/fixtures_fundamental.py`（不以 `test_` 開頭，pytest 不收集） | 存活測試守的是 refresh、口徑核實、共識 section、overlay ledger 閘門，需要同一組夾具；`_run()` 不搬（沒有東西可跑） |
| 25 | 0b.1b-C/H 2/2 | `test_full_chain_acceptance`「批 2 重寫成新管線」 | 本步先做一半：16 條估值鏈測試退役、12 條改主詞（refresh 矩陣改成 axis／assumption key、PIT 改驗假設不漏、黑箱 CLI 改比現價與共識格）；整檔重寫仍留給 0b.2 | 這一步要全綠（含 Neo4j 在線的整合測試）；新管線要的讀圖 ledger／三題 absence 還沒有 |
| 26 | 0b.1b-C/H 2/2 | 短評 placeholder | `base_target`／`base_return`／`value_date` 與帶參數的 `{assumption:…}` 四個 placeholder 的來源退役，值改 `None` → 印「（尚無）」並標 partial；`sell_side_target`（賣方目標價均值，A2）照填；**placeholder 字彙一個不刪** | append-only 短評紀錄引用它們（L10）；與 E 組處理 `{bet_*}` 同一條 |
| 28 | 0b.2 | 「`alpha/fundamental/`（只留資料契約，若已搬則整包刪）」 | **留在原地**：`contracts.py`（會計期間、假設紀錄、Engine C 觀測與共識型別）、`assumptions.py`（ledger 解析／選取／supersede）、`compare.py`（口徑核實與基期對帳）三檔各有活消費端（provider、refresh、read model 的共識 section、催化劑熟成度）；不搬到 `alpha/contracts.py` | 搬家只會把 H 組 regex 的 `alpha\.fundamental` 命中變成零，不改任何行為——那是為了 grep 好看而動 20 個 import（L17：general 到資料支持的那一格為止）。結案 gate 8 走 keep-list：`kept_file: 資料契約與 ledger 邏輯` |
| 29 | 0b.2 | 「`test_full_chain_acceptance` 重寫成新管線（圖 → 讀圖 ledger → 敘事 → 三題 absence → 心跳）」 | **延到 Phase 2／3**：2/2 已把 16 條估值鏈測試退役、12 條改主詞（refresh 矩陣、PIT、黑箱 CLI），檔頭寫明「會重寫」；新管線的四節裡讀圖 ledger 與三題 absence 還不存在 | 現在重寫只能寫出對不存在機制的測試（空跑，L14-4）；留 12 條活的判準比留一份假的重寫誠實 |
| 30 | 0b.2 | 批 2 驗收「C／D／F／H 四組在 code 命中 0」（已 amend 為 keep-list） | 剩餘命中逐條分類：退役註記（各檔）、legacy key／placeholder（`calibration_refs`、`{base_target}`…）、Engine C 資料層（`engine_c/*`、`alpha/providers/fundamentals.py`、`pe_forward`）、refresh 字彙常數、批 3 的 `webapp/basket.py`／app.js 籃子頁、以及 `alpha/context.py` 的 PE 比值 proxy＋refresh 的 `market_implied_eps_growth` artifact | 最後一項**不在 Phase 0 退役清單**：它是研究 packet 給 session 判 Q4 的 heuristic proxy（`alpha/context`，核心研究層），read model 的呈現格已於 2/2 拿掉；拿掉 packet 裡的量要另開決定（Phase 3「已定價嗎」的資料源之一）。結案 keep-list 的類別：`kept_file` |
| 31 | 0b.2 | 未提 `scripts/repricing_check.py`／`scripts/closure_probe.py`（H 組命中） | **留**：前者是「已被定價了嗎」的股價變化分解（唯讀算術，2026-08-18；Phase 3 三題的前身），後者只在 docstring 提到口徑核實 | 不在退役清單；H regex 命中的是 `pe_forward`（Engine C 欄位名） |
| 27 | 0b.1b-C/H 2/2 | 「argument 少掉的只能是估值來源的段」 | 「數字怎麼算出來」「和市場差在哪」兩段退役（E 組已拿掉「賭注」），六段變三段；句型 `numbers_paragraph`／`market_paragraph`／`bet_paragraph` 刪；`timeline_paragraph` 不再收 value_date／horizon_end／reached | ROADMAP 第 82 行的驗收條件；實測見本 Step 八欄（各檔段數前後對照） |

## 0.8 ✅ 已裁決（2026-09-23）：**A——`argument` 升核心、`why` 退役**（原 escalation 紀錄留存於下）

使用者定案 A。ROADMAP 消費層對照表、批 1 的做法與驗收、結案 gate 3、R2 檢查 7 已同步改為 argument（commit 見 git log）。
升核心前多一個檢查：列出各檔 argument 行數的前後對照，確認刪掉估值來源段後沒有任何一檔變空。


**這正是 §6「撞到就停」預測的那一格，而且 plan 與 ROADMAP 在這裡互相矛盾。**

```
SCOPE_ESCALATION
Original zoom: Z2（0b.1，plan 已核准的 PLAN_PROPOSAL）
Observed issue: `why` 面板 100% 由估值鏈組成，但 plan 與 ROADMAP 都要它留在**核心**面板
Recommended zoom: 使用者一個決定即可回到 Z2（不需要重新規劃整批）
Why local patch is insufficient: 核心面板缺內容＝blocked。保留 `why` 而刪掉它的資料源，
  會讓 73/73 檔全部變成 blocked——而 0b.1 自己的驗收寫的是「blocked 檔數不因 fundamental 缺席而增加」
```

### 事實（實測，不是推論）

| 量到的 | 數字 |
|---|---|
| `why` 面板的 line 來源 | **1,910 行全部**是 `assumption` 510／`sensitivity` 343／`trace` 911／`epistemics` 146——**零行敘事** |
| 組裝它的程式 | `briefing/analyst_view/compose.py::_why_panel`，輸入只有 `view.earnings_bridge`、`view.valuation`、`view.implied_return` 三者（批 2 全刪） |
| 現行核心面板 | `CORE_PANELS = ("headline", "fundamental", "why", "research")` |
| ROADMAP 要的核心面板 | headline、短評（`brief`）、`why`、`research`、讀圖（Phase 2）、歸零旗標（`wipeout`）；`fundamental` 降選配 |
| 若照做 | `why` 永久 `missing` → **73/73 檔 blocked** |
| `argument` 面板現況 | **73/73 檔都有內容**（合計 438 段；available 63／partial 10），但目前標 `optional=True`。它的標題就是「為什麼這樣想：鏈、數字、市場、賭注、風險、時間表」 |

查證：`python scripts/analyst_view_text_digest.py --per-panel`、`grep -n "_why_panel" -A 30 briefing/analyst_view/compose.py`。

### 三個選項（請選一個；我不自行決定，因為它改的是消費契約）

| | 做什麼 | 代價 | 我的建議 |
|---|---|---|---|
| **A** | **`argument` 升為核心、`why` 退役**。論證層＝`argument`（憑什麼）＋`research`（什麼會推翻它）＋`downside`（反證連 watch）＋`bet`（純文字） | 要改 ROADMAP 那一行「論證層留 why」與 gate 3 的「why 文字不變」 | ✅ **建議這個。** 73/73 檔今天就有內容，零檔變 blocked；而「憑什麼」本來就是 `argument` 在回答的問題，`why` 回答的是「估值怎麼算」——那個問題整個退役了 |
| **B** | `why` 留在核心，但內容改讀敘事 ledger | 敘事 ledger today **沒有** assumption／sensitivity 這種分格資料，所以 `why` 會是空的或與 `argument` 重複；等於 A 但多一層改名 | ✗ |
| **C** | `why` 留在核心並印明示缺席，直到 Phase 2 讀圖接手 | 73/73 檔 blocked 兩個 Phase；gate 3 的「why 文字不變」必失敗 | ✗ |

**不論選哪個都要同時改的：** ROADMAP 個股頁那一列的「論證 → 留 why」、plan 批 1 的驗收句、
結案 gate 3 與 R2 檢查 7 的「`view.why` 文字 digest ＝ baseline」。

### 在這個決定之前，0b.1 的哪些部分可以先做？

**刻意不先做。** 0b.1 的檔案清單（`builder.py`／`sources.py`／`contracts.py`／`render.py`／
`compose.py`／`webapp/*`／`app.js`）與 readiness 規則改寫是同一批；`why` 的去向決定
`CORE_PANELS`、`_readiness()`、型別層與那 8 個測試檔怎麼改。先動一半會讓下一個 session
接到一個半改的樞紐，而樞紐正是這批最難接手的東西。

## 0.7 ✅ 已裁決（2026-09-23）：**差集 keep-list**（原紀錄留存於下）

使用者定案：保留八組 regex，腳本加 `KEEP`（鍵是（檔，組字母）、值是「類別: 理由」，類別限 kept_file／legacy_key／retirement_note／boundary_sentence／guard_assertion 五類），
驗收改為腳本印出的三個數字都是 0：未列 keep-list 的命中、已列但不再命中、理由類別不合法。`scripts/retired_mechanism_grep.py` 已加支援（KEEP 目前為空，由你逐條填）；
ROADMAP 驗收①與本 plan gate 8、R2 檢查 1 已同步。精確到（檔，組）而不是只到檔，是為了讓一個因 G 組留下的檔若多出 C 組引用仍會被抓到。


**ROADMAP Phase 0 驗收①與本 plan 結案 gate 8 寫的是「八組 regex 在 code／skills／tests／config／static 命中 0」。
這條在字面上無法達成，而且其中兩處是因為 `AGENTS.md` 自己要求那個措辭。** 五類證據（實測數字）：

| # | 情形 | 實例與命中數 | 為什麼不能歸零 |
|---|---|---|---|
| 1 | plan／ROADMAP 明寫「留」的檔仍命中自己那一組 | `decision_lab/store.py` G 組 11｜`tests/test_private_backup_restore.py` G 組 23｜`engine_c/estimates.py` H 組 15（`pe_forward`）｜`alpha/providers/fundamentals.py` H 組 12｜`config/alpha_screen.json` B 組 3｜`query/bottleneck.py` A 組 25 | 它們**依設計留下來**。ROADMAP 硬約束 2 要求舊 Decision Store 凍結唯讀（schema 不動、資料不刪），所以 `decision_lab` 這個字必然還在 |
| 2 | legacy 封閉字彙 key | `engine_b/todo.py` G 組 150｜`tests/test_engine_b_todo.py` G 組 166 | 0a.4 明文要求 `decision_review` **不刪 key**（池裡歷史項目仍是這個 type），且測試斷言兩個 dict 鍵一致 |
| 3 | `AGENTS.md` 強制要求寫出退役 | 各檔的「X 已退役」註記 | `AGENTS.md`（Beta 節）：「舊語意已明文**廢止**——**安靜消失擋不住下次回填，所以廢止必須寫出來**」。要歸零就得把退役註記全部刪掉，那正是它禁止的事 |
| 4 | **`AGENTS.md` 自己的句子命中退役 regex** | E 組 `賭對了值\|判斷錯了值`：`AGENTS.md`「系統只負責……**賭對了值多少、判斷錯了值多少**」｜B 組 `籃子`：「已定價」主參照是自己的歷史、**主題籃子**只當脈絡 | **同一串字同時是退役的四價尺與現行的判準句。** 要歸零就得改 `AGENTS.md` 的判準句 |
| 5 | 退役守門斷言本身 | `tests/test_queue_segments.py` 等翻面斷言 | 「有人把它加回來會變紅」需要在斷言裡指名它。已盡量改成封閉字彙**相等**斷言（不指名）來減少，但無法全免 |

**提案（五欄 amendment；`AGENTS.md`「不得偷改 ROADMAP 後繼續跑」，所以只提案不自改）：**

| 欄 | 內容 |
|---|---|
| **原 roadmap** | Phase 0 驗收①＋結案 gate 8：「八組 regex 在 code／skills／tests／config／static 命中 **0**」 |
| **新觀察** | 五類反例（上表），其中第 4 類要歸零就得改 `AGENTS.md` 的判準句，第 1、2 類要歸零就得違反 ROADMAP 硬約束 2 與 0a.4 |
| **proposed change** | 驗收改成「**命中但不在 keep-list 上的檔 = 0**」：在 `scripts/retired_mechanism_grep.py` 加一份 `KEEP` 清單（檔 → 為什麼留，逐檔一句），腳本多印一個數字「未列入 keep-list 的命中檔數」。**那一個數字才是 gate，而它可以是 0。** 誰新增一個命中的檔就會讓它非零 |
| **why** | 保住原本的意圖（沒有殭屍**機制**），拿掉不可能達成的部分（沒有殭屍**字串**）。keep-list 逐檔寫理由，讓「為什麼留」可被質疑；季度重跑時看的是同一個數字 |
| **impact** | 只動 `scripts/retired_mechanism_grep.py`（＋ROADMAP 那兩行驗收文字）。不動任何 authority、不放寬任何 gate。**執行者不自改**——批 2／3／4 的 grep 驗收會照實報告命中數與分類，結案 gate 8 等本 amendment 定案 |

## 0.9 ✅ 已完成（2026-09-23）：C／H 2/2（樞紐）的落點（實作偏差見 §0.6 #18–27；以下為開工前的地圖，留作紀錄）

**這是 Phase 0 剩下最大的一塊，也是唯一還沒動的樞紐。** 前面四組（D／F／E／C-H 1/2）已把它的
外圍消費端全部斷乾淨，所以現在的 importer 地圖只剩 8 個檔（實測，2026-09-23）：

| 退役模組 | 活 importer |
|---|---|
| `alpha/valuation` | `alpha/cli.py`、`alpha/providers/valuation_assumptions.py`、`alpha/refresh/artifacts.py`、`briefing/alpha_view/{builder,sources}.py`、`scripts/verify_test_nonvacuity.py` |
| `alpha/implied_return` | 同上 ＋ `alpha/closure.py` 已斷、`alpha/providers/horizon_assumptions.py` |
| `alpha/fundamental` 的**模型**半邊 | 只剩 `briefing/alpha_view/sources.py`（`build_fundamental_model`）|

`alpha/providers/{valuation_assumptions,horizon_assumptions}.py` 本身只服務退役模型，**視為退役模組**
（與 0b.1b-F 處理 `entry_criteria.py` 同一條）；ledger 檔案留在 `library/private/alpha/`（L10）。

### 要從 read model 拆掉的 section（6 個；現有 21 段）

| Section | 為什麼退役 | 注意 |
|---|---|---|
| `price_implied_expectations` | 價格隱含的 proxy（`market_implied_eps_growth`），C 組 regex 命中 | `reverse_dcf` 是 `not_modeled`，一起走 |
| `internal_fundamentals` | 我們的 FY+1 預測，來自 `alpha/fundamental` 模型 | 它與下面兩個同出於 `_fundamental_parts()` |
| `earnings_bridge` | FY+1 因果橋 | 同上 |
| `valuation` | 估值鏈本體 | `CurrentPrice` 已於 0b.1a 搬進 `market` section，**不要跟著刪** |
| `implied_return` | 隱含報酬 | `target_reached` 欄位已停算（E 組），這裡連欄位一起走 |
| `scenarios` 的 `target_valuation` 一格 | 照抄 `valuation.fair_value` | ⚠ **section 本身留**：bull／base／bear 是 session 散文，不在 C／H regex 內 |

### 三個切不開但可分開的地方（動手前先讀）

1. **`expectation_gap_section`（builder 約 2392 行）同時服務活與退役**：
   活的是 `gap_closure`（市場承認了嗎：共識 EPS 自判斷日以來的移動）與 `consensus_series`；
   退役的是 `numeric_comparisons`（內部 vs 共識）、`opinion_stance`、`multiple_derivation`、`proxies`。
   **可分開**（`gap_closure` 只需要判斷日與共識時序，不需要我們的模型），所以不是 §6 的停點。
2. **`fundamental` analyst panel（已於 0b.1a 降為選配）** 會失去 internal／comparison 兩組 line，
   留下 consensus／market_context。ROADMAP 稽核區「留 fundamental 原始數字」指的就是後者。
3. **短評的 `{assumption:driver[scope]}` placeholder** 由 `bridge.assumptions` 填。橋退役後它會與
   E 組拿掉的 `{bet_assumption:…}` 一樣印「（尚無）」。**placeholder 不得從封閉字彙移除**
   （append-only 短評紀錄引用它，L10；三本既有短評都用了）。

### 已知會紅的測試檔（逐檔列，改主詞不刪判準）

`test_alpha_investment_view`、`test_alpha_view_fundamental`、`test_alpha_view_render`、
`test_alpha_view_refresh`、`test_alpha_view_brief`、`test_alpha_view_as_of_cohr`、
`test_full_chain_acceptance`（批 2 要**重寫**成新管線，不是刪）、`test_absence_semantics`、
`test_gap_closure`、`test_opinion_stance`、`test_sole_source_tristate`、`test_estimate_revision`、
`test_coverage_pilot_generalization`。
**整檔退役的**：`test_valuation_model`、`test_implied_return`、`test_fundamental_model`。

### 做法（前四組實測有效，照用）

**逐組：斷 import → 刪模組 → 刪測試，同一個 commit，每個 commit 全測試綠。**
⚠ **區塊切除（按「下一個 def」切）在這個檔上已經誤刪五次同區的活程式**
（`_FundamentalParts`、`_SESSION_LEVEL_LABEL`、`WIPEOUT_IS_NOT`／`A_WIPEOUT`／`_wipeout_section`、
`A_BRIEF`／`BRIEF_IS_NOT`）。每次都由測試當場抓到並逐字還原，但**切之前先 `awk` 列出該區間內
所有頂層定義**會比事後修便宜。

## 0. 不可越線（違反即 NO_GO）

1. **不碰資料 authority：** 不碰 Neo4j、Engine C ledger、thesis lifecycle、Google Sheet、`library/private/`、`library/trades/`。
2. **舊 Decision Store 只准讀。** Step 0.0 記下檔案 sha256 與 `live_choices` 筆數，Phase 結案時比對，必須相同。
3. **不刪 `docs/archive/`、`docs/lessons-incidents.md`、`docs/brainstorms/`。** 退役機制的文字只從活文件（OPERATIONS／ARCHITECTURE／CONCEPTS／skills）拿掉。
4. **任何 `python -m <module>` 命令字串變更 → sandbox impact review 五步**，同一個 commit 改 `.codex/rules` 與 `tests/test_codex_daily_permissions.py`。
5. **每刪一個測試檔，八欄的 Blocking findings 列出它守的是哪個退役機制。** 活機制的測試不可刪斷言（ROADMAP 硬約束 9）。
6. **每批動手前先答 L11-6 第④問：「如果這個刪除是錯的，最先壞掉的是哪一筆現有資料或哪個活的 import？」去看那一筆，寫進八欄。**
7. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 已知會撞的：某個檔同時服務活機制與退役機制且切不開（見 §6）。
8. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** 本 Phase 不寫任何 authority。

## 1. Step 0.0 基準快照（Z0，一個 commit）

全部存進 `docs/reports/2026-09-2x-phase0-baseline.md`（日期用實跑日）：

```bash
python scripts/retired_mechanism_grep.py                 # 八組命中數（code／static／skills／tests／config／livedocs）
python -m webapp status | tail -12                        # 9 個 state kind
python -m engine_b.todo list                              # pq2 未結案（預期 19：17 decision_review ＋ 2 manual）
python -m pytest -q 2>&1 | tail -1                        # 全綠基準與測試數
python -m audit invariants                                # 六 invariant 綠
python - <<'EOF'
import hashlib,glob,sqlite3
for p in glob.glob('library/private/decision_lab/*.db'):
    print(p, hashlib.sha256(open(p,'rb').read()).hexdigest()[:16],
          sqlite3.connect(p).execute('select count(*) from live_choices').fetchone())
EOF
```

驗收：報告存在且含上面每一項的實際輸出。**這些數字是 Phase 結案時的比對基準**（現況數字會腐壞，所以要存下來）。

## 2. Step 0a 停跑（Z1，四個小 commit）

目的：**先讓退役機制不再產生任何注意力**，再刪。每項改最少的東西。

| # | 改哪裡 | 怎麼改 | 怎麼驗 |
|---|---|---|---|
| 0a.1 排程與規則 | `crons/daily_brief_prompt.md`、`crons/weekly_scan_prompt.md`、`engine_b/queue_segments.py`、`.codex/rules/*`、`config/standing_authorization.json` | prompt 拿掉 decision_lab `today`／reassess／籃子／首選段；`queue_segments` 移除 reassess-stale 段與任何以 `rank_bottlenecks` 順序餵的段；`.codex/rules` 移除 `decision_lab today` 與 reassess-stale 兩條 fixed entry（**五步 review**，`tests/test_codex_daily_permissions.py` 同 commit）；standing_authorization 移除 `decision_review` 類別（`engine_b/standing_authorization.py` 載入時驗封閉性，`tests/test_standing_authorization.py` 同 commit） | `python -m engine_b.cli counts` 佇列段少 reassess；`pytest tests/test_codex_daily_permissions.py tests/test_standing_authorization.py tests/test_routine_prompts.py` 綠 |
| 0a.2 心跳與 APP 入口 | `crons/heartbeat.py` 段 2 **與段 4**；`webapp/contracts.py` 封閉字彙；`webapp/__main__.py` materialize 清單；`webapp/api.py` 路由；`webapp/static/index.html` nav（**實際落地見 §0.6 第 5–8 筆**）| 段 2 的「現價過目標價」與籃子行換成一行 `候選狀態板未落地（not_yet_recorded）`（**五段永遠出現**）；materialize 清單移除 `multi_year`、`basket`；`/api/v1/multi-year` 與 basket 路由移除；nav 移除「要幾倍」「籃子」（籃子 Phase 3 以候選板回來） | `python -m webapp status` 沒有 `multi_year`、`basket`；`pytest tests/test_heartbeat.py tests/test_webapp_request_path.py` 綠（heartbeat 測試裡斷言籃子行的斷言跟機制退役，列進八欄） |
| 0a.3 研究 skill | `skills/daily-brief/SKILL.md`、`skills/research-drain/SKILL.md`、`skills/alpha-status/SKILL.md`、`skills/investment-research/SKILL.md`、`skills/blind-spot-audit/SKILL.md`、`skills/system-decompose/SKILL.md` | 拿掉或改寫首選、籃子、payoff、隱含報酬、目標價、排序驅動研究、decision_review 的句子；alpha-status 的「現在該投什麼」改答「候選狀態板（Phase 3 前印未落地）」；跑 `python scripts/sync_agent_skills.py` | `python scripts/retired_mechanism_grep.py` 的 skills 列 → 0；`pytest tests/test_daily_brief_skill.py tests/test_agent_workflow.py` 綠（skill 測試裡斷言退役段落的斷言跟機制走） |
| 0a.4 池子收集端 | `engine_b/todo.py` | `collect_all(include_decisions=False)` 成為唯一路徑：移除 `collect_from_decisions` 的呼叫；`ITEM_TYPES` 與 `GO_AUTHORIZATION` 裡的 `decision_review`、`sheet_only_holding` **改成 legacy 標記**（照 `lead_research` 的寫法，不刪 key：池裡歷史項目仍是這兩個 type，讀取要認得，且 `tests/test_engine_b_todo.py` 斷言兩個 dict 鍵一致） | 跑一次 collect 後 `todo list` 沒有新鑄的 decision_review；`pytest tests/test_engine_b_todo.py` 綠 |

**0a 結案驗收：** 心跳五段照印；`webapp status` 9 kind → 7；skills 命中 0；`todo` 新鑄來源無 `decision_lab`。

## 3. Step 0b 刪除（Z2 一次 PLAN_PROPOSAL，四批各一個 commit）

**順序不可換：先斷 import，再刪模組。** 2026-09-22 的 importer 地圖（`docs/ROADMAP.md` 退役清單的補充，實跑時重算一次）：

| 要刪的 | 被誰 import（活的程式，不含測試） |
|---|---|
| `alpha/valuation` | `briefing/alpha_view/sources.py`、`builder.py`、`alpha/implied_return/*`、`alpha/providers/valuation_assumptions.py`、`alpha/entry/*`、`alpha/cli.py`、`alpha/refresh/artifacts.py` |
| `alpha/implied_return` | `builder.py`、`sources.py`、`contracts.py`、`render.py`、`alpha/providers/horizon_assumptions.py`、`alpha/cli.py`、`alpha/closure.py`、`alpha/entry/*`、`alpha/refresh/artifacts.py` |
| `alpha/fundamental` | **25 個**：含 `alpha/contracts.py`、`alpha/providers/fundamentals.py`、`alpha/providers/assumptions.py`、`briefing/multi_year.py`、`builder.py`、`sources.py`… → **它有兩半**：`FundamentalsSnapshot` 這類**資料契約**要留，FY+1 因果橋**模型**要刪 |
| `alpha/reverse` | `briefing/multi_year.py`、`sources.py` |
| `alpha/entry` | `builder.py`、`sources.py`、`contracts.py`、`render.py`、`alpha/providers/entry_criteria.py`、`alpha/cli.py`、`alpha/refresh/artifacts.py` |
| `alpha/ranking` | `decision_lab/brief.py`、`alpha/brief.py`、`briefing/today.py`、`sources.py` |
| `alpha/backtest` | `scripts/rank_forward_returns.py` |
| `briefing/multi_year` | `briefing/cli.py`、`sources.py`、`webapp/materialize.py` |
| `webapp/basket` | `webapp/materialize.py` |
| `rank_bottlenecks()` 當排序 | `alpha/providers/graph_neo4j.py`、`webapp/materialize.py`、`builder.py`、`basket.py`、`webapp/api.py`、`alpha/ranking.py`、`query/structure.py`、`alpha/provider.py`、`engine_b/cli.py` |
| decision_lab 研究側 | `engine_b/todo.py`、`briefing/today.py`、`sources.py`、`engine_b/signal_source_registry.py`、`alpha/catalyst.py`、`alpha/cli.py`、`briefing/public_view.py`、`briefing/render.py`、`engine_b/leads.py` |
| `decision_lab.store`（**唯讀留**） | `alpha/__init__.py`、`briefing/today.py`、`webapp/api.py`、`webapp/materialize.py`、`webapp/__init__.py`、`webapp/__main__.py`（positions kind 讀 live choice 歷史，讀取合法） |

**樞紐是 `briefing/alpha_view/builder.py`（估值鏈 166 處）與 `sources.py`。** 它們 import 了幾乎所有退役模組，所以第一批是重寫樞紐，不是刪模組。

### 批 1｜斷 import：個股頁 builder 重寫（最大的一批）

- 檔：`briefing/alpha_view/{builder,sources,contracts,render,changes}.py`、`briefing/analyst_view/{compose,contracts}.py`、
  `alpha/refresh/artifacts.py`、`alpha/closure.py`、`alpha/cli.py`、`alpha/contracts.py`、
  `alpha/providers/{valuation_assumptions,horizon_assumptions,entry_criteria,assumptions,fundamentals}.py`、
  `webapp/{api,materialize,__main__}.py`、`webapp/static/{app.js,index.html}`。
- 做：依 ROADMAP「消費層對照表／個股頁」——首屏拿掉尺（現價／沒賭對／賭對／判斷錯了）與「要翻倍需要什麼為真」計算框；
  論證層 `bet` 改純文字（讀 `our_bet`）、`entry` 面板刪；稽核區拿掉 q4 隱含報酬、q7 payoff；`overview` 拿掉 `implied_return`、`payoff`、
  `future_target`、`sell_side_target`、`target_reached`；readiness 核心面板改為 headline、短評、**argument**、research、歸零旗標（讀圖面板 Phase 2 加）、
  fundamental 降為選配；**`why` 面板退役**（它只吃估值鏈三個輸入，問的問題已被 G3 退役；`argument` 才是在答「憑什麼」的面板，73 檔都有內容——2026-09-23 使用者定案 A）。
  升核心前先確認：argument 的「數字」「賭注」段刪掉估值鏈來源後，**沒有任何一檔的 argument 變空**（列出各檔 argument 行數的前後對照）。`alpha/fundamental` 的 `FundamentalsSnapshot` 等資料契約搬進 `alpha/contracts.py` 或留在 `alpha/fundamental/contracts.py`，
  模型檔（因果橋）留到批 2 刪。`alpha/cli.py` 拿掉 valuation／implied／entry／reverse 子命令。
- 驗收：**importer 地圖重算後，退役模組只被退役模組自己與測試 import**；`python -m webapp materialize` 全 73 檔成功；
  `python -m webapp status` 的 blocked 檔數不因 fundamental 缺席而增加（readiness 規則換了）；`pytest tests/test_webapp_request_path.py tests/test_analyst_view.py tests/test_absence_semantics.py` 綠（斷言尺與 q4／q7 的測試跟機制走，逐一列出）。
- L11-6 第④問：**最先壞的是 `alpha/providers/fundamentals.py`**——它 import `alpha.fundamental` 三處；動手前確認它要的是資料契約不是模型。

### 批 2｜刪估值鏈

- 刪：`alpha/valuation/`、`alpha/implied_return/`、`alpha/fundamental/`（只留資料契約，若已搬則整包刪）、`alpha/reverse/`、`alpha/entry/`、
  `alpha/providers/entry_criteria.py`、`briefing/multi_year.py`、`scripts/multi_year_check.py`、`scripts/alpha_expectation_gap.py`、
  `alpha/models/session_assessor.py` 裡的 `multiple_horizon` 讀寫（判斷檔資料留，不再消費）。
- 刪測試：`test_implied_return`、`test_valuation_model`、`test_fundamental_model`、`test_reverse_bridge*`、`test_multi_year_*`、`test_entry_logic`、
  `test_brief_multiple_question`、`test_variant_scenario`（四價部分）、`test_estimate_revision`（若只服務估值）。`test_full_chain_acceptance` **重寫**成新管線
  （圖 → 讀圖 ledger → 敘事 → 三題 absence → 心跳），不是刪。
- 驗收：殭屍 grep 的 C、D、F、H 四組在 code／static／tests 命中 0；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 `engine_c/estimates.py`**——H 組 regex 命中它 15 處，但它是資料層（共識估計），**留**；確認刪的是 `alpha/` 的模型不是它。

### 批 3｜排序與籃子

- 刪：`alpha/ranking.py`、`alpha/backtest.py`、`scripts/rank_forward_returns.py`、`webapp/basket.py`、`scripts/outcome_if_settled_today.py`、`scripts/alpha_screen_check.py`。
- 改：`query/bottleneck.py` → 結構表：保留逐邊 rows（證據等級、sub、sole_source、qualification、自報／外部印證、走不走得到錨）、`anchor_gaps`、
  INV-3 的 filtered reasons；**拿掉** `min_substitutability` 當排名門檻、top-N、「可行動排序」與「純結構排序」兩份序、`--sector` 分組；
  函式改名 `structure_table()`，`rank_bottlenecks` 名稱不留 alias。`alpha/providers/graph_neo4j.py`、`alpha/provider.py`、`query/structure.py`、
  `engine_b/cli.py`、`webapp/{materialize,api}.py` 改讀結構表；state kind `ranking` → `structure_table`；`app.js` 排序頁改結構表頁（拿掉排名框）。
  `config/alpha_screen.json`（覆蓋厚薄門檻）**留**，改由 Phase 3 候選板消費；`config/lead_classification.json` 的排序引用改走圖。
- 刪測試：`test_webapp_basket`、`test_basket_screen_thresholds`、`test_bet_endgame`、`test_ranking_view`；`test_bottleneck_ranking`、`test_webapp_ranking`、
  `test_sole_source_tristate` **改寫**成結構表測試（保留三態、去重、證據上限那些活的斷言）。
- 驗收：殭屍 grep 的 A、B 兩組命中 0；`webapp status` 列得出 `structure_table`；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 `engine_b/priority.py`／`queue_segments.py` 有沒有拿排序當 pq1 優先序**——0a.1 應已移除，動手前 grep 一次 `rank_bottlenecks` 確認只剩結構表。

### 批 4｜賭注四價、decision_lab 凍結、硬擋搬家、活文件

- 賭注四價（E 組）：payoff 計算與四價渲染刪；`bet/variant.overlay` ledger **資料留**；`alpha/narrative/argument.py` 的 payoff 引用改文字；
  `config/decision_blockers.json`、`config/engine_c_observation_fields.json` 裡只服務 payoff／估值的 blocker 碼與欄位移除（封閉字彙，`tests/test_config_tracking.py` 與相應測試同 commit）；
  `decision_lab/sizing.py`、`tests/test_probe_sizing.py`、`test_weakest_axis`、`test_downside_overlay`、`test_bet_state_opinion_in_base`、`test_brief_downside_symmetry` 刪。
- decision_lab 凍結（依 ROADMAP「decision_lab 凍結」表）：刪 `execution.py`、`outcomes.py`、`sizing.py`、`context.py`、`coverage.py`、`coverage_queries.py`、
  `intake.py`、`workflow.py`、`workflow_ports.py`、`brief.py`、`action_card.py`、`references.py`；`cli.py` 只留唯讀 `history`／`status`；
  `store.py` 寫入方法留著但無呼叫端，docstring 第一行加 `frozen 2026-09-22（G12）`；`engine_b/todo.py` 刪 `collect_from_decisions` 與所有 decision_review 分支
  （legacy 標記已在 0a.4）；`briefing/today.py`、`public_view.py`、`render.py` 拿掉 decision brief pane；`alpha/catalyst.py`、`engine_b/signal_source_registry.py`、
  `engine_b/leads.py` 的研究側 import 斷掉；MCP `get_decision_brief` 工具退役（先 `grep -rn get_decision_brief` 找定義）。
  刪測試：`test_decision_lab_e2e`、`test_action_card`、`test_operational_workflow`、`test_layer_separation`（若只驗研究側）；`test_private_backup_restore` **留且必須綠**。
- 硬擋搬家：`store.py` 的 `_assert_user_sized_within_capital_caps` 搬到 `risk/`（或 `portfolio/`，選已有 policy 載入的那個），
  `scripts/record_trade.py` 在 `--apply` 前呼叫：以 Sheet NAV 算成交後單筆占比與槓桿曝險，超過 5% 單筆或 ETF 槓桿 cap → fail closed；
  `--override --reason "<理由>"` 才放行並在 trade_log 事件寫 `override_reason`。**新增測試**：dry-run 超 5% 必須 fail closed；override 無 reason 必須拒絕。
- 活文件：`docs/OPERATIONS.md` 的 decision_lab 命令段、`docs/ARCHITECTURE.md` §8.2 對應列與 §7／§9 提到 Engine D 研究側的段、`CONCEPTS.md` 的相關詞條
  **同 commit 更新**；殭屍 grep 的 `livedocs` 命中逐句列在八欄，只有「不做 X」「X 已退役」型的句子可留。
- 驗收：殭屍 grep 的 E、G 兩組命中 0；Decision Store sha256 與 `live_choices` 與 Step 0.0 相同；`python -m audit invariants` 綠；
  `pytest tests/test_private_backup_restore.py` 綠；record_trade 兩個新測試綠；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 positions kind**——`webapp/materialize.py` 讀 `DecisionStore` 取 live choice 歷史；確認它只用讀取方法，凍結後仍能 materialize。

## 4. Step 0c 池子（Z0，一個 commit）

17 筆未結案 `decision_review` 一次批次 `drop`，理由逐字：「機制退役（ROADMAP Phase 0，2026-09-22 使用者定案 G3／G12）」。
這是 pq2 動作；**使用者已於 2026-09-22 明示授權**（`AGENTS.md`「使用者主動指示＝已授權」），receipt 註明語境。
只 drop `type=decision_review` 且未結案的；2 筆 `manual` 不動。

驗收：`python -m engine_b.todo list` 未結案 = 2（manual）；`todo_pool.log` 有 17 筆 drop 且理由相同。

## 5. Phase 0 結案（completion gate 九項）

1. `pytest -q` 全綠，測試數與 0.0 基準的差＝刪除的測試檔（逐檔列在八欄）。
2. `python -m audit invariants` 綠。
3. 語意 diff：`python -m webapp materialize` 前後，73 檔的 `brief`／`argument`／`research` 面板文字不變（只拿掉面板與估值段，不改文字；argument 少掉的只能是估值來源的段）。
4. 無新 dual authority：收據只住 trade_log，舊店無寫入呼叫端（grep `record_live_choice(` 呼叫端 = 0）。
5. 無 silent drop：心跳五段照印；被拿掉的段落印 `not_yet_recorded` 不是空白。
6. Point-in-time 測試綠。
7. lifecycle 可達：pq2 未結案 2；watches 95 筆仍在。
8. Executable protection：`scripts/retired_mechanism_grep.py` 印出的「未列 keep-list 的命中（檔，組）數」為 0，且「已列但不再命中」為 0；keep-list 每條理由屬五類之一；輸出存進 `docs/reports/…-phase0-closeout.md`。
9. **驗收數的是機制存在與否**（kind 數、命中數、sha256、pq2 數），沒有一個是「幾檔通過某個 filter」。

結案後同 commit：ROADMAP Phase 0 標 ✅、ARCHITECTURE §8.2 的「建議區間已移除、煞車仍在」列改指 `record_trade.py`。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

九項 gate 由執行者自報之後，**發下面這份 `WORK_REQUEST` 給乾淨 context 的 reviewer**（能 spawn 就 spawn；不能就原文交回由使用者貼給新 session）。
reviewer 只讀不寫，回 `REVIEW`（verdict `GO`／`NO_GO` ＋ findings）；`NO_GO` → `AWAITING_HUMAN`，執行者不得自動修。

```
WORK_REQUEST（R2，Phase 0 結案）
Target: master 最新 commit；docs/reports/…-phase0-baseline.md 與 …-phase0-closeout.md
Claimed acceptance: Phase 0 九項 gate 全過（見 closeout 報告）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python scripts/retired_mechanism_grep.py → 「未列 keep-list 的命中（檔，組）」＝0、「已列但不再命中」＝0；逐條審 keep-list 理由是否屬五類且成立，
     kept_file 類的檔另 grep 確認它沒有活的呼叫端指向退役程式；livedocs 命中逐句列出並判斷是否為禁止句
  2. python -m webapp status | tail -10 → 沒有 basket、multi_year；kind 數與 closeout 一致
  3. python -m engine_b.todo list → 未結案 2，皆 manual
  4. python -m pytest -q → 全綠；測試檔數差 ＝ closeout 列出的刪除清單，逐檔核對「守的是哪個退役機制」是否成立
  5. python -m audit invariants → 全綠
  6. library/private/decision_lab/*.db 的 sha256 與 live_choices 筆數 ＝ baseline 報告
  7. library/private/app/analyst_view/COHR.json：overview 沒有 payoff／implied_return／future_target／sell_side_target／target_reached 鍵；
     overview.brief.our_bet 與 view.argument／research 的文字 digest ＝ baseline（只拿掉面板與估值段，不改文字）
  8. python -m crons.heartbeat --out <temp> → 五段標題都在；段 2 含「候選狀態板未落地」且 absence_kind 為 not_yet_recorded
  9. grep -rn "record_live_choice(" 呼叫端 ＝ 0（舊店無寫入端）；scripts/record_trade.py 的兩個新測試存在且綠
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet
```

使用者留下的只有三件：讀 reviewer 的 verdict；reviewer 對「刪除的測試守什麼」有疑慮時裁決；三個月後決定紀錄 §10 的四條否證。

### 結案之後：停，不要開 Phase 1

R2 回 GO 後：ROADMAP Phase 0 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。
然後 **`AWAITING_HUMAN`**：Phase 1 還沒有 plan，不得自行開工。HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`
「每個 Phase 開工前要有一份 plan」那段指令，並在 closeout 報告附「本 Phase 執行中發現、Phase 1 要決定的問題」清單
（例如：語意條件 kind 的欄位、watch_decision 的 go 語意、哪些反證先登記）。這是本 plan 唯一刻意的停點。

## 6. 已知陷阱

- **`ITEM_TYPES` 是封閉字彙且有測試綁鍵一致**（`tests/test_engine_b_todo.py`）：退役 kind 用 legacy 標記，不刪 key。
- **心跳五段永遠出現**（`crons/heartbeat.py` 三條不可退讓）：拿掉的內容換成 `absence_kind` 行，不能整段消失。
- **config 封閉字彙改動**要同步 `tests/test_config_tracking.py` 與 `.gitignore` 的 `!config/<name>.json`。
- **`alpha/fundamental` 有兩半**：資料契約留、模型刪；`engine_c/estimates.py` 是資料層，留。
- **`decision_lab.store` 的讀取端合法**（positions kind、backup／restore）；凍結是「無寫入呼叫端」不是「無人 import」。
- **Windows：python 不認 `/tmp`**，暫存用 `%TEMP%`；大檔用 Write 工具不用 heredoc（>8 KB 會截斷）。
- **測試裡的退役斷言**：`test_heartbeat`（籃子行）、`test_daily_brief_skill`（首選段）、`test_alpha_investment_view`（尺與相關性）等會紅——
  紅的斷言若守的是退役機制就跟著退役並列出；若守的是活的判準（例如相關性提醒必印）就**改主詞不刪斷言**。
- **`scripts/verify_test_nonvacuity.py`** 列了退役測試的空跑檢查（估值鏈 13 處、entry 6 處）：同批更新，否則它會對不存在的測試報錯。
- **撞到就停：** 某個檔同時服務活機制與退役機制且切不開（例如 `briefing/alpha_view/sources.py` 裡讀圖與估值共用一個 loader）→
  `SCOPE_ESCALATION` ＋ `AWAITING_HUMAN`，不自行重構整套。
