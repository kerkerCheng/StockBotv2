# Alpha Edge Phase 2 計畫（PLAN_PROPOSAL，2026-09-17）

> ⚠ **已封存（2026-09-22）：不要再讀。** 本檔的決定已被 [`2026-09-22-graph-first-direction-decision.md`](2026-09-22-graph-first-direction-decision.md) 整併或取代，只為歷史稽核保留；分類與理由見 [`README.md`](README.md)。

> **性質：** ROADMAP Phase 2「心跳＋分類（D12）」的 **Z2** PLAN_PROPOSAL。
> 規格來源是 [`ARCHITECTURE.md`](../ARCHITECTURE.md) §4.1 與決定紀錄 D12。
> **進度的唯一權威是 [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表**；本檔的現況數字會腐壞，引用前先跑查證命令。
> ⚠ **Step 的拆法還沒被核准。** 依 `AGENTS.md`，改 ROADMAP 的 Phase／Step 定義要先給五欄 amendment
> ——本檔第 5 節就是那份 amendment，等使用者決定後才寫進 ROADMAP。

## 0. INTAKE

```
INTAKE
Zoom: Z2（理由：改變既有輸出的語意——Daily 從「一份 LLM 組的 brief」變成「心跳＋分類＋研究」三層；
          「daily 產出什麼」今天有四個 owner：crons/daily_brief_prompt.md、skills/daily-brief/SKILL.md、
          scripts/publish_daily_brief.py、config/daily_routine.json）
Review: R1（六條 R2 trigger 都不命中：不動 authority mutation、不動財務身分／PIT／單位、
          不動資本或 live、不是 architecture boundary migration。動到 unattended executable surface
          的部分由 sandbox impact review 五步處理——那是既有機制，不是第二份 token）
```

## 1. 目標與它要消掉的失敗模式

**Phase 2 要換掉的不是「brief 太長」，是「沒發生」與「沒看到」同形。**
現行 Daily 是一份由 LLM 組出來的 brief：LLM 沒起來、某個研究段落卡住、sandbox 擋掉一條命令，
**整份就不會發出**——而 Discord 上「今天沒事」與「今天沒人跑」長得一模一樣（L13-2）。
同時研究火力被無人值守的 `drain` 吃掉：`drain_limit_per_run` 現值 5，而研究依 D12 只該在互動 session 做。

三層的分工（ARCHITECTURE §4.1）：

| 層 | 誰跑 | LLM | 失敗時 |
|---|---|---|---|
| **心跳** | 純 Python 排程 | 零 | 只降級該段，**照發** |
| **分類** | 便宜模型（signal-triage） | 每日硬上限 | 不阻斷心跳；印「未 triage N」 |
| **研究** | 互動 session 的 research-drain | 有 | daily 不跑（`drain_limit_per_run`＝0） |

## 2. Step 拆法（三步；**2.1 已交付**）

| Step | 做什麼 | 驗收（哪個數字會變） | 動到 unattended surface？ | 待使用者決定？ |
|---|---|---|---|---|
| **2.1** ✅ | `crons/heartbeat.py`：零 LLM／零網路的純消費端，固定五段、缺席分型、失敗只降級不消失；`tests/test_heartbeat.py` | 見 §3 | **否**（沒有任何排程會叫它） | 否 |
| **2.2** ✅（見 §3b） | 切換載體：心跳接上排程、`config/daily_routine.json` 的 `drain_limit_per_run` 5 → 0、`crons/daily_brief_prompt.md` 研究段移出、`.codex/rules` fixed entry 與 `tests/test_codex_daily_permissions.py` 同 change 對齊、OPERATIONS／ARCHITECTURE 現況改寫 | `drain_limit_per_run` 由 5 → 0；連續 3 天心跳零 LLM 成功發出且每天印「未 triage N」 | **是**（sandbox impact review 五步） | **是——見 §5** |
| **2.3** ○ | 分類層：signal-triage 每日硬上限、失敗不阻斷、未 triage 計數進心跳段 3（段 3 已先做好，2.3 補的是「誰去跑 triage、跑幾則就停」） | 每日 triage 上限由「無」→ 明確值；LLM 失敗當天心跳仍發出且「未 triage N」非零 | 是 | 隨 2.2 的選擇而定 |

## 3. Step 2.1 交付與實測（2026-09-17）

**交付：** `crons/heartbeat.py`（零 LLM、零網路、不寫任何 authority）＋ `tests/test_heartbeat.py`（14 條）
＋ OPERATIONS 新增「心跳」操作節 ＋ ARCHITECTURE §4.1 標注現況。

**五段各自從哪裡來（全部是消費，不重算）：**

| 段 | 資料源 | 為什麼是它 |
|---|---|---|
| 1 資料新鮮 | `pending_leads.json` 的 `harvest_log`；`beta` artifact 的 `instruments[].latest_close.session_date`／`price_status`；`StateArtifactStore.read_all()` | 逐檔行情心跳必須明示**商品自身**的最新完整交易日；APP 當天沒 materialize 必須印出來（AGENTS Beta 呈現契約＋L12） |
| 2 變了什麼 | `watches` artifact；`thesis/lifecycle.json`；`basket` artifact 的 `price_above_target`；`beta` artifact 的 `warnings` | 現價過目標價**只提醒不觸發出場**（D3）；beta 只印門檻跨越與狀態翻轉 |
| 3 佇列 | **`engine_b.queue_segments.observe()`**＋**`engine_b.todo.actionable_items()`** | 兩個都是既有 SSOT。在心跳裡自己數一份就是 L16 的形狀：猜錯不會有東西壞掉，只會安靜偏掉 |
| 4 部位 | `beta` artifact 的 alpha sleeve；`positions` artifact 的 `aggregate`／`anchor_health`；`ranking` artifact 的 `demand_anchor` 分佈 | alpha **只觀測不設目標**（D1）；需求錨分佈回答「N 檔不等於 N 個獨立機會」 |
| 5 帳號計分表 | 尚未建（Phase 3） | daily 宣告 `method_not_applicable`、weekly 宣告 `capability_absent`，**兩種不同的「沒有」** |

**驗收（每條都跑過）：**

| 驗收條件 | 實測 |
|---|---|
| 固定五段，順序固定 | ✅ `python crons/heartbeat.py` 印出 1–5 段 |
| **資料源全滅仍印五段**（＝「LLM 失敗心跳照發」的機械版） | ✅ `test_every_source_broken_still_renders_five_sections`；`test_main_always_exits_zero_even_when_everything_is_broken` 另斷言四段**真的**各爆一次（`RuntimeError: boom` 出現 4 次，避免 monkeypatch 沒生效也綠） |
| 「未 triage N」必印，0 也印 | ✅ 實跑印出「**未 triage 0**」；`test_untriaged_count_is_always_printed_even_when_zero` |
| 段 3 消費 `queue_segments.observe()`，不自己數 | ✅ `test_queue_section_consumes_queue_segments_not_its_own_count`（斷言 observe 被呼叫一次） |
| pq2「球在你手上」等於 `todo.actionable_items()` | ✅ 實測 15（池中未結案 31 − 等事件 16）；`test_pq2_ball_in_user_court_uses_todo_ssot` |
| 缺席用既有封閉字彙、不自創第二套 | ✅ 全部取自 `alpha/absence.py`；字彙外的值在建構時就 raise |
| 零 LLM／零網路是契約不是慣例 | ✅ `test_heartbeat_does_not_import_any_llm_or_network_surface`（原始碼不得出現 requests／httpx／openai／anthropic／urllib.request／neo4j／publisher） |
| exit code 永遠 0 | ✅ 上面那條測試 |
| 沒有新增任何 outbound surface | ✅ `.codex/rules` fixed entry **仍 20 條**、permission test 15 條綠 |

**心跳的數字與既有 authority 對得起來（試圖否證，不是驗證它為真）：**
`pq2 球在你手上 15` vs `python -m engine_b.todo list` 的「等事件 16 項」＋未結案 31 → 31−16=15 ✅；
`追蹤表 22 檔／等權絕對 −3.63%` vs `library/private/decision_lab/outcome_aggregate.json`（n=22、−0.036256）✅；
`APP 今天已 materialize 1 份／不是今天的 5 份` vs `python -m webapp status`（ranking fresh 0.8h、其餘 stale 26.9h）✅。

**R1 對抗回合（切換成「我要找出它為什麼是錯的」）抓到三件，全部當下修掉：**

1. **`None` 被加成 0。** pq1 可做數原本寫 `sum(counts.get(k) or 0)`——而 `observe()` 的 `None` 意思是
   「本次沒讀到那個 authority」，不是 0。加成 0 會讓「沒讀到」與「真的沒有」同形（INV-3／L12）。
   改成排除 `None` 並把未讀到的段名逐一印出；`test_unread_segment_is_not_counted_as_zero` 鎖住。
2. **`exit 0` 看起來像在掩蓋失敗。** 它其實是 **fail visible**：心跳的下游是人眼，它一旦不發人就什麼都
   看不到，所以失敗要印在該印的那一行而不是變成非零 exit。這與 INV-6 不衝突（INV-6 禁的是**靜默**回傳當前值），
   但必須寫在檔頭，否則下一個讀者會以為這裡漏了 fail closed。已補。
3. **段 2 印的是狀態不是 diff。** 「現價過目標價」若連續三十天都是同兩檔，它就從訊息變成噪音。
   真正的「較昨變動」需要昨天的心跳快照——**排程接上之前不存在昨天**，所以刻意不假裝有，
   並把這個限制寫進檔頭與本節（Step 2.2 接上排程後再補，屆時第一天仍然沒有昨天，那一天要誠實印出來）。

**全套 pytest 抓到第四件（R1 沒抓到，測試抓到）：** 心跳原本 `from audit import sources` 讀 leads／watches／todo——
而 `audit/` 是 composition root，**站在所有層之上、不被任何層 import**，`crons` 又在 `CORE_PACKAGES` 裡，
所以 `tests/test_layer_separation.py::test_nothing_imports_audit` 直接紅。
改成走 `engine_b.leads.load()`／`engine_b.event_watch.load_watches()`／`engine_b.todo.load()`——
**同一份檔案、同一個 authority，只是換成該層自己的 loader**，數字一個都沒變（`pq2 球在你手上 15` 前後相同）。
⚠ 這一條值得記：R1 的六項通檢與兩個 profile 都沒問到「依賴方向」，**是既有測試把它擋下來的**——
那正是 L14 說的「真正的防呆是會自己紅的東西，不是要人讀的段落」。

**R1 另外確認、但刻意不改的一件：** 心跳今天**沒有任何自動 consumer**（INV-4）。
這不是漏掉，是順序：先有不依賴 LLM 的東西頂上，才拿得掉 LLM 那一層。
已寫進 `crons/heartbeat.py` 檔頭、本計畫 §2 與 ROADMAP Phase 2 那一列——
**「已交付」不得被寫成「已生效」**（L13-1：驗收條件是產出出現在下游消費者手上）。

**修法層級（Step 3 的四問）：**
①**顯形**，不是根除——心跳讓「今天沒人跑」變成看得見，但它不會讓 Daily 不失敗。
根除是 2.2 才會發生的事（把研究從無人值守路徑裡移走，失敗就不再有機會吃掉心跳）。
②**靠程式**：五段是常數 tuple、`_guard` 吞例外、exit 0 是寫死的，不靠任何人記得。
③**加一個機制**。為什麼不能用拿掉的方式達成：要拿掉的那個東西（LLM 組 brief）**在 2.2 才拿得掉**，
而拿掉它的前提是先有一個不依賴 LLM 的東西頂上——順序不能反，否則就是拆煞車不裝儀表板（L14-3）。
本 Step 因此刻意是純新增、零 surface 變更。
④**如果它是錯的，最先壞掉的是哪一筆現有資料？** 答案是**一筆都不會**——沒有任何排程會叫它，
它也不寫任何東西。真正會壞的是「它報的數字與 authority 不符」，所以上面那三條對照就是④的動作，
三條全部逐位對上。

## 3b. Step 2.2 結果（2026-09-17）

**交付四塊：**

| 塊 | 內容 | 驗收（現跑） |
|---|---|---|
| 排程 | `crons/heartbeat_task.py`（無人值守進入點）＋ Windows 工作排程 `StockBotv2-Heartbeat`（每日 07:00，`LogonType Interactive`，免密碼免管理員） | `schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V` → `Status=Ready`、`Next Run Time=2026/9/18 07:00`；`schtasks /Run` 實跑 → `Last Result: 0`、publisher 回 `{"status":"sent","sent_parts":2,"total_parts":2}` |
| 研究層移出 | `config/daily_routine.json` 的 `drain_limit_per_run` **5 → 0**；`engine_b/routine_config.py` 讓 0 合法並寫下語意；`engine_b/cli.py` 讓 `gap_jobs` 也吃 limit | `python -c "...['pq1']['drain_limit_per_run']"` → **0** |
| allowlist 收緊 | `.codex/rules` **20 → 15** 條（移除 `fetchers\edgar.py`／`fetchers\mops.py`／`engine_b.cli drain`／`prepare_research_action.py --action-file`／`engine_b.todo work`） | `tests/test_codex_daily_permissions.py` 20 條全過，**且五條已加進 execpolicy 的負面 parametrize——由 Codex 自己的 parser 證明不再被允許**，不只是「檔案裡找不到那串字」 |
| prompt | `crons/daily_brief_prompt.md` v1.7 → v1.8：檔頭三層分工表、fixed entry 列舉更新、步驟 5 整段停用並以 `<details>` 保留原文不刪 | 殘留的五個命令字串全部只出現在已停用區塊或說明句裡 |

**⚠ 三個「動手才知道」的發現：**

1. **`drain_limit_per_run` 的驗證器原本直接拒絕 0**（`必須是 1..20`），因為舊語意是「0＝無上限」。
   那是一個表示承載兩種語意（L12）。修法**不是放寬也不是收緊，是先分開再各自定規則**：
   0＝研究層關閉、1..20＝每輪上限、其餘仍拒絕。
   ⚠ 關鍵是**原本那道保護沒有被刪，是被換成更強的**：原斷言（0→ValueError）只擋得住有人把 0 寫進 config，
   擋不住任何一個把 limit 當「沒有上限」用的消費端；新的
   `test_drain_limit_zero_selects_nothing_of_every_kind` 直接證明 limit=0 時每一種工作都選不出來。
   **空跑檢查做過**：把 `lead_batch` 的切片改成無上限 → 該測試立刻紅。
2. **`gap_jobs` 根本不吃 `limit`。** 只有 decision work order 與 lead 吃——所以即使
   `drain_limit_per_run=0`，daily 仍然會被派 assessment-gap 研究工單，**而且不會有任何東西變紅**
   （L17：機制只認得當初那個案例）。同一個 change 補上 `and limit`。
3. **四條既有的 drain 測試隱含依賴 production 的 `config/daily_routine.json`。** 改成 0 之後它們全紅。
   修法是**讓測試自帶輸入**（`_routine_with_limit()`），不是把 production 值改回去——
   否則 config 被測試綁架，而那四條測的本來就是排序與 fail-closed，不是當天的預算值。

**⚠ 第一版 wrapper 寫成 `.cmd`，實跑直接解析失敗：** `cmd.exe` 以 OEM codepage（本機 cp950）讀檔，
而檔案是 UTF-8，中文註解被拆成無效指令（`'」這類狀態印出來。' is not recognized as...`）。
改用 Python 進入點。**這不是風格偏好，是編碼事實**，已寫進 `heartbeat_task.py` 檔頭與 OPERATIONS。

**修法層級（Step 3 的四問）：**
①**根除**——研究從無人值守路徑整段移走之後，「研究失敗吃掉心跳」在結構上不可能再發生；
心跳走的是另一條完全不經 Codex 的路。②**靠程式**：排程是 OS 的、limit=0 由驗證器與行為測試守、
allowlist 由 Codex 自己的 parser 守。③**拿掉一個機制**（五條 rule ＋ daily 的整個研究段），
只加了一個純新增、零 authority 的排程入口。④**如果它是錯的，最先壞掉的是哪一筆現有資料？**
答案是**明天 05:30 的 daily**——所以「哪些步驟還會被呼叫」是逐條 grep 過的，而且
**移除的每一條 rule 都對應到同一個 change 裡被停用的 prompt 步驟**，不是先收權限再看哪裡壞。

**❌ 唯一未達的驗收：「連續 3 天心跳零 LLM 成功發出」。** 手動觸發成功不算數（L13-1：驗收條件是
產出出現在下游消費者手上，而「下游」在這裡是每天 07:00 自己跑起來）。**最早 2026-09-20 才驗得完**，
在那之前 **Phase 2 不標完成**。

## 4. ~~Step 2.2 的預定內容（尚未動工）~~（2026-09-17 已交付，見 §3b；原文留作對照）

- `config/daily_routine.json`：`pq1.drain_limit_per_run` 5 → 0（查證命令已在 OPERATIONS「Daily / pq1 / 待辦池的參數」）
- `crons/daily_brief_prompt.md`：研究段（drain／prepare RA）移出 daily；心跳與分類兩層的執行契約寫清楚
- `.codex/rules`：依 §5 的選擇決定要不要新增 `crons\heartbeat.py` 這一條 fixed entry；
  **心跳本身無網路、無憑證、只寫 `--out` 指定的檔**，照 `consume-fired` 的先例可能在 sandbox 內就跑得動、根本不需要 entry
  ——這一點要在 2.2 實測，不先假設
- `tests/test_codex_daily_permissions.py`：同 change 對齊（fixed entry 條數的斷言住這裡，散文不寫死）
- OPERATIONS「每日操作」流程圖與 ARCHITECTURE §4.1 的「落地前的現況」blockquote 改寫

## 5. **五欄 amendment：要使用者決定的一件事——✅ 2026-09-17 使用者選 A**

> **使用者原話：「心跳你能幫我用windows排程嗎？ 我不在電腦前面 或是有沒有其他方式 不然就走B」**
> ——條件式的 A：做得到就 A，做不到才退 B。
>
> **先證明做得到，再承諾。** 實測順序：①`whoami` 非 admin；②用拋棄式工作測 `Register-ScheduledTask`
> ——`LogonType Interactive` 不需要密碼、不需要管理員，`REGISTER_OK` 後立刻 `Unregister` 清掉；
> ③確定可行才建真正的工作。**沒有先問「我可以建嗎」然後發現建不起來。**
>
> ⚠ 沒有第三種方式。`/schedule` 這類 cloud 排程跑的是 cloud agent，**讀不到本機的 Neo4j、Engine C
> 與 private authority**，心跳的五段有四段在那裡取不到值——那不是心跳，是一份空表。
> 開機常駐的 Python loop 比排程差（多一個長駐程序、崩了沒人知道）。所以只有 A 與 B。



| 欄 | 內容 |
|---|---|
| **原 roadmap** | Phase 2「心跳＋分類（D12）：**純 Python 排程**、固定五段、`drain_limit_per_run` 歸零、Codex fixed entry 與 permission test 同一 change 對齊；weekly 同一套」 |
| **新觀察** | 「純 Python 排程」在本機沒有載體。今天觸發 Daily 的是 **Codex desktop 的 standalone scheduled task**（`crons/daily_brief_prompt.md` 檔頭逐字），repo 裡沒有任何 OS 排程的登記或文件——`grep -i "schtasks\|task scheduler" docs/OPERATIONS.md` 命中 0。**所以「心跳由誰觸發」不是實作細節，是一個沒有預設答案的選擇。** |
| **proposed change** | 在 ROADMAP Phase 2 那一列補上 §2 的三個 Step，並把選定的觸發載體寫進驗收欄 |
| **why** | 兩個選項對「LLM 失敗心跳照發」這條硬規則的滿足程度**不一樣**，而那正是 Phase 2 存在的理由——選錯會讓整個 Phase 的驗收變成空的 |
| **impact** | 影響 Step 2.2 的 sandbox impact review 範圍與 `.codex/rules` 要不要多一條 fixed entry；不影響已交付的 2.1 |

**選項 A（建議）：新增一個獨立的 Windows 工作排程，直接跑 `.venv\Scripts\python.exe crons\heartbeat.py --out <檔>` 再跑既有 publisher。**
- 真正的「純 Python 排程」：**Codex 沒起來、LLM 壞掉、sandbox 擋住，心跳照發**——D12 的硬規則因此是結構上成立，不是靠運氣。
- 代價：機器上多一個排程工作；要在工作排程器建一次（或授權我用 `schtasks` 建）。
- 兩個排程會不會撞？心跳**不寫任何共用檔**，所以不需要 writer lock；但時間仍應錯開，避免它讀到 daily 寫到一半的 state。

**選項 B：不新增 OS 排程，讓現有的 Codex daily task 第一步就跑心跳。**
- 代價：**Codex 沒起來就沒有心跳**——而「Codex 沒起來」正是這個 Phase 要讓它看得見的失敗之一。
  硬規則從「結構上成立」降級成「大部分時候成立」。
- 好處：零新增排程、零新增 surface，2.2 的 sandbox review 範圍最小。

⚠ **這一題的判準不是「哪個省事」，是「心跳要不要比 LLM 更耐活」。** 若答案是要，A 是唯一能成立的；
若使用者評估 Codex 幾乎不會掛、不值得為此多一個排程，B 是誠實的取捨——但那要寫進 ROADMAP 的驗收欄，
**不能讓「連續 3 天零 LLM 成功發出」看起來達標而實際上仍掛在 LLM 底下**。

## 6. 不得做（沿用 Phase 1）

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬篩選條件、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯、
**用 broad permission 掩蓋整合缺口**（只放行能由既有人工 gate、action type 與 receipt 約束的最窄 command prefix）。
