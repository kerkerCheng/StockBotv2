# StockBotv2 — 系統架構

> **這份文件回答一個問題：系統長什麼樣、為什麼這樣切？**
>
> 它描述的是**目前的實現方式**，不是憲法。判別問法（`AGENTS.md` 的分野）：
> **「換掉 Neo4j、把 Engine D 拆成三個 package 之後，這句話還對嗎？」**
> 還對 → 它屬於 `AGENTS.md`（約束行為）；會跟著變 → 它屬於這裡。
>
> 五份文件的分工見 `AGENTS.md`「本檔的角色與另外四份」。
> 完整設計論證與逐檔搬遷判定見 [`refactor/target-architecture.md`](refactor/target-architecture.md)
> 與 [`refactor/current-architecture.md`](refactor/current-architecture.md)；本檔是它們的蒸餾版。

---

## 1. 五條 authority separation 今天由誰實現

**不可變的是權責分離（`AGENTS.md` §憲法），可變的是下面這一欄「今天由誰」。**
「四引擎架構」本身是 CURRENT_ARCHITECTURE，2026-09-03 使用者明示它不是憲法。

| Authority | 擁有什麼真相 | 唯一寫入者 | 可變性 | 今天由誰實現 |
|---|---|---|---|---|
| **A1 結構／證據** | 實體、關係、claim、provenance、逐字引文 | 經人工 admission gate 的 loader | 可重建（extraction 檔是 ground truth） | Engine A（Neo4j）＋`loader/` |
| **A2 財務觀測** | 帶時戳的財務／市場／共識觀測 | ETL（可重建）＋ append-only 人工 ledger | 混合 | Engine C（`engine_c/`） |
| **A3 研究判斷／Alpha** | 「我們相信什麼、憑什麼、什麼會推翻它」 | 研究流程（session 提議 → schema 驗證） | **可重算** | `alpha/`（Phase 1–6 建立） |
| **A4 Portfolio／Risk** | 目前曝險、目標配置、硬上限 | policy config ＋ Google Sheet（外部 authority） | 可重算 | `portfolio/`＋`risk/` |
| **A5 資本決策／問責** | 「當時憑什麼決定、使用者選了什麼、後來對不對」 | 明確的人工動作 | **append-only，Git 救不回** | `library/trades/trade_log.jsonl`（成交事件內嵌收據，`scripts/record_trade.py` 寫；硬擋 `risk/hard_caps.py`）；舊 Decision Store（`decision_lab/`）frozen 2026-09-22，唯讀歷史 |

### 四引擎的「不負責什麼」（這一欄比引擎命名有價值）

| 引擎 | 角色 | 不負責 |
|------|------|--------|
| **Engine A** | 供應鏈、物理／關係瓶頸、claim 與 provenance | Signal queue、部位、價格時序、交易決策 |
| **Engine B** | 外部 Signal discovery／intake 與研究注意力排序 | 提高 evidence tier、自動投資、graph admission bypass |
| **Engine C** | 財務、估值、市場與其他帶時戳 observation | thesis、持股真相、最終部位決策 |
| **Engine D** | Decision & Accountability：Shadow、Coverage、system decision、live choice／fill、lifecycle、outcome | 寫 Engine A、複製 Engine C current truth、取代 Google Sheet、broker routing、**任何部位尺寸** |

---

## 2. 分層與依賴方向

```
External Signal / Source
   │  Engine B — discovery / intake / source tracing
   ▼
Evidence ──────────────────────────────────┐
   │  loader + schema                      │ EvidenceRef 是唯一的跨層
   ▼                                       │ provenance 載體——任何一層都
Knowledge Graph（Engine A / Neo4j）         │ 不得「知道一件事卻說不出
   │  GraphResearchProvider（唯一出口）      │ 誰說的、什麼時候說的」
   ▼                                       │
Alpha Research Core（alpha/）◀─────────────┘◀── Engine C（財務／市場／共識）
   Q1 結構稀缺 → Q2 價值攫取 → Q3 盈餘曝險 → Q4 預期落差 → Q5 催化劑
   ↓ ResearchContext（as_of 凍結、content-addressed）
AlphaSignal — research view only，**不含部位**
   ▼
Portfolio（portfolio/）— view → target exposure ▸ Risk（risk/）— hard limits
   ▼
trade_log（library/trades/）— 成交收據；risk/hard_caps.py — 寫入前的兩道硬擋｜舊 Engine D（decision_lab/）frozen 2026-09-22，唯讀歷史
```

**依賴方向只准 peripheral → core。** `alpha/` 的契約與模型層零外部相依
（`tests/test_layer_separation.py::FORBIDDEN_IN_ALPHA`），唯一允許碰外部世界的是
`alpha/providers/`。`audit/` 是 composition root：它看得到所有層，所有層看不到它。
`briefing/` 是 daily brief 與 **Alpha Investment Read Model**（§6.1）的組裝層，同樣看得到
所有層；Engine D 的 domain 模組不得 import 它（`FORBIDDEN_FOR_ENGINE_D`）。

**MCP／remote access 是 Legacy Peripheral，不是核心。** 新核心必須能在完全沒有 MCP
的情況下運作；`Core → mcp_server` 的 import 已於 Phase 3 歸零。

---

## 3. 記憶層（持久知識庫）

- **Neo4j 知識圖譜（Engine A）：** 供應鏈結構、技術關係、來源可追溯的主張。
  Property graph，不是 tree。選型理由見 `AGENTS.md` L1。
- **SQLite / Postgres（Engine C）：** 財務快照、財務核驗五項（舊稱 Watchlist Gate，該層已於 2026-09-02 除役，見 §9；五項本身仍有效）。零安裝預設 SQLite；
  設 `POSTGRES_HOST`／`POSTGRES_DSN` 切 Postgres。SQLite authority 在 ignored
  `library/private/engine_c/`，由 `library/private/runtime_pointer.json` 指向。
  ETL projection 可由 tracked schema 重建；**同庫的 append-only manual observation
  ledger 是 private authority**（該不變式住 `AGENTS.md`）。
  見 [`solutions/tooling-decisions/engine-c-sqlite-dual-backend.md`](solutions/tooling-decisions/engine-c-sqlite-dual-backend.md)。
- **向量 RAG：** 暫用 Neo4j 內建，量大再分。

### Point-in-time：兩種凍結，不可混用

| | `ResearchContext`（A3） | `DecisionContext`（A5；**frozen 2026-09-22**，只剩歷史，新收據住 trade_log） |
|---|---|---|
| 凍結什麼 | 該次研究實際使用的 A1／A2 slice | 該次決策實際使用的全部 context ＋ policy version |
| 可否重算 | **可以**（研究可以重跑） | **不可以**（append-only，舊 decision 永遠引用原 digest） |
| 住哪 | `alpha/contracts.py` | Engine D 的 `context_bundles` |

⚠ 「凍結 Engine A」一律指**凍結該次實際使用的 slice**，不是 snapshot／dump 整張 Neo4j。

### as-of 圖投影（Phase 6）

canonical edge **沒有時間欄位**——唯一時間線索是 `CITES → SourceDoc.published_at`。
投影靠它做：`query/bottleneck.py::project_assertions_as_of` 依「引用的文件在 `as_of`
之前發表過沒有」篩 assertion，**再**交給 `structure_table`（原 `rank_bottlenecks`，跨檔排序已於 2026-09-23 退役）。

⚠ **順序不可顛倒。** 先排序再砍列會留下用未來文件算出的 `substitutability` 與
`evidence`——列是對的、值是偷看來的，那是 lookahead 最難察覺的形式。
未定日一律排除**並計數**。圖上完全沒有日期、或 `as_of` 早於最早證據時，
`Neo4jGraphResearchProvider` 拋 `PointInTimeUnsupported` 而不是回空 list。

---

## 4. 管道層（Engine B discovery → 入庫）

```
文件 → library/raw/ → extract.py → loader/validate.py → loader/load_to_neo4j.py → Neo4j
fetchers/{edgar,mops,mfn,rns}.py ↑      engine_c/etl_yfinance.py → SQLite
線索 → source-trace → prepare_research_action（server-owned review packet）
     → 使用者明確核准 ID → apply_research_action（filesystem-first + resumable graph write）
     → 本機 session 執行 scripts/commit_pending_intake.py
```

- **抽取與 DB 解耦：** `extract.py` 只輸出 DB 無關 JSON；loader 可替換（L3）。
- **fetchers：** `fetchers/edgar.py`（美股 SEC EDGAR）、`fetchers/mops.py`（台股 MOPS）、`fetchers/mfn.py`（瑞典 MFN，Nasdaq Stockholm／First North）、`fetchers/rns.py`（英國 RNS，經 investegate 鏡像）。四支同構：只從公開來源把指定文件寫到 `library/raw/`，meta 帶 `published_at` 與其依據；**mfn／rns 是互動式入口，不進無人值守**（2026-09-17 Phase 1 Step 1.1；放行是另一次 impact review 的事）。
- **daily harvest：** `crons/harvest_leads.py` 以 X API `since_id`＋EDGAR watch 抓
  metadata → triage PASS → routine 依 priority 自動 pq1 → prepared RA 才進 pq2。
- **2026-09-16 定案、尚未交付（規格，不是現況；ROADMAP Phase 3／6）：** X 帳號登記表（封閉清單，tier
  `probation`／`measured`／`trusted`，只影響 pq1 優先序）＋每則貼文自動蓋章（貼文時間＋當日收盤價＋具名實體）
  ＋每週計分表五欄、materialize 進 APP（D5）；MOPS 重訊 watcher 與台股每月營收 datum；parked lead 超過 60 天
  自動 `expired` 並計數、不刪（D15，INV-2）。推文永遠是 tier-4 lead，lead-intake 不變。
- **題材掃描（原每週審查）：** 2026-09-24 起（Phase 1 Step 1.9）是互動 skill `skills/theme-scan`，只做 topic discovery；
  原 weekly 的健康審查／thesis 唯讀提醒／投組風險快照由 Windows daily 接手（⑭、心跳段 2、④）。舊 prompt 逐字封存於
  `docs/archive/2026-09-24-weekly-scan-prompt-v1.2.md`。
- **本機音訊追源：** `scripts/transcribe_audio.py`（`faster-whisper`），模型與逐字稿
  只存 ignored `library/private/`。ASR 只提供 timestamp locator。
- **遠端存取：** 本機 MCP server ＋ Cloudflare Tunnel ＋ connector，十一工具 surface（`get_decision_brief` 於 2026-09-23（Phase 0 Step 0b.4） 退役）。
  完整資料流與安全邊界見 [`remote-access-architecture.md`](remote-access-architecture.md)。
- **各類來源的抽取 instruction：** [`extraction-instructions.md`](extraction-instructions.md)。

> ⚠ 這張圖裡的 `prepare_research_action`／`apply_research_action` 是 **MCP 的動詞**。
> 它們之所以出現在架構圖裡是歷史因素（Research Action 的 domain 曾被關在
> `mcp_server/` 裡），Phase 3 已把 domain 抽到 `intake/`。

### 4.1 Daily 三層與心跳規格（2026-09-16 使用者定案 D12；ROADMAP Phase 2 交付前這裡是規格，不是現況）

> **落地前的現況：** Daily 仍是上面那條「harvest → triage → pq1 drain → brief」的單一 Codex 排程。
> 查證：`python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`
> 印出 > 0 就是還沒落地；落地後應為 0。
>
> **2026-09-17（Phase 2 Step 2.1／2.2）：三層已落地，上面那條「落地前的現況」自此不再是現況。**
> ①心跳＝`crons/heartbeat.py`（零 LLM、零網路、固定五段、失敗只降級不消失），無人值守進入點是
> `crons/heartbeat_task.py`，由**獨立的 Windows 工作排程 `StockBotv2-Heartbeat`（每日 07:00）**觸發
> ——**刻意不經 Codex**，這樣「LLM 失敗心跳照發」是結構上成立而不是靠運氣。
> ②研究層移出：`drain_limit_per_run` 已為 **0**，`.codex/rules` 由 20 條收緊為 **15** 條
> （移除 `fetchers\edgar.py`／`fetchers\mops.py`／`engine_b.cli drain`／
> `prepare_research_action.py --action-file`／`engine_b.todo work` 五條研究層專用 entry）。
> ③分類層仍在 Codex 排程（05:30）。
> ⚠ **驗收尚未完成**：ROADMAP Phase 2 要「連續 3 天心跳零 LLM 成功發出」，手動觸發成功不算數（L13-1）。
> 查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`、
> `python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`。

> **2026-09-24（Phase 1 Step 1.2a；A1、C1、C4、C6）：無人值守收斂成一個 Windows daily。**
> Windows 工作 `StockBotv2-Daily`（時間只住 `config/daily_routine.json` 的 `schedule`，由 `scripts/register_daily_task.py`
> 導出、`crons/daily_task.py` 每次開跑比對）跑一份**程式寫死的封閉步驟清單** `DAILY_STEPS`：抓資料、機械段、materialize、
> 健康審查、invariants、本機備份、心跳、發送。它取代 Codex daily automation、`StockBotv2-Heartbeat` 與 `StockBotv2-FxSync`
> （舊兩個工作與舊入口 `crons/heartbeat_task.py` 於 2026-09-25 Step 1.2b 刪除；上面 09-17 那段的查證命令已查不到東西）。
> **daily 的目標：心跳不靠 LLM；其他步驟可以用 LLM，但 LLM 只產出提議，由程式驗證後寫入**（C4）。分類（triage）與語意預篩
> 是 daily 裡的兩步，一律 `claude -p` 零工具、只回 JSON、每次檢查 init 能力欄位（Step 1.3、1.4 接上；在那之前 `llm.executor=none`）。
> 失敗長相與改時間的唯一做法見 OPERATIONS「Daily」節。查證：`schtasks /Query /TN StockBotv2-Daily /FO LIST /V`、
> `python crons/daily_task.py --dry-run`。

| 層 | 誰跑 | LLM | 做什麼 |
|---|---|---|---|
| **心跳** | Windows daily 的 ⑱（純 Python，從 state 檔與 daily 執行紀錄組出），⑲ 推到既有 Discord publisher | 零 | 固定五段，每段可以只有一行 |
| **分類／語意預篩** | Windows daily 的兩步：`claude -p` 零工具提議、程式驗證後寫入（Step 1.3／1.4 接上） | 每日硬上限（由 CLI 截斷，不靠 prompt） | 失敗不阻斷；印「未 triage N」與分類層本輪結果 |
| **研究** | 互動 session 手動 research-drain | 有 | daily 的 `drain_limit_per_run` 歸零 |

> **2026-09-24（Phase 1 Step 1.8）心跳改版**：五段不增不減。段 2 第一行是**較昨變動**——⑱ 帶 `--write-snapshot` 寫
> `library/private/heartbeat/snapshots/<日期>.json`（鍵是封閉清單 `crons/heartbeat.SNAPSHOT_KEYS`、留 14 天；derived、只給 diff，
> **不是** current-state authority），只印變了的鍵。段 1 加備份／健康審查（⑭ capture）／invariants（⑮ capture）；段 2 的 watch 行改讀
> registry（今日醒／今日到期／已觸發未消化／語意標旗／未檢），加**新點名雷達**（今天第一次被點名、registry 沒有的名字，依首次點名
> 時間排、不依次數）與讀圖重讀理由；段 3 加預篩本輪結果、LLM 額度（不是 allowed 才印）、**pq2 逐筆**（go／不含字串取自
> `todo.GO_AUTHORIZATION`，超過 10 筆印前 10）、到期行（今日／累計，累計照 `EXPIRY_RESOLUTION_KINDS` 逐格）、**距上次掃題材 N 天**
> （每天印；≥ `theme_scan.nudge_after_days` 時粗體並移到訊息第一行）；段 4 加 NAV（bucket 分布、最大單筆；producer 是
> `materialize --positions` 的 `nav_exposure`）；段 5 **每天印** tier 分布＋較昨，完整表在 APP（`--weekly` 拿掉）。
> ⑱ 另寫 Discord 摘要行 `heartbeat_<日期>.summary.txt`（`Daily <日期>｜球在你 N`＋紅旗），⑲ 帶進 `publish --summary`。

心跳固定五段：
1. **資料新鮮**：每個 harvest 來源 ok／fail、行情最新交易日、APP 今天是否 materialize、**台股月營收最新月份與落後幾個月**（2026-09-17 Phase 6：月營收**刻意不進無人值守**——歷史頁按年月永久可查、漏抓補得回來（L10），與「只有前一營業日、漏一天永久漏」的重訊性質相反。所以它不需要排程，需要的是**該補的時候自己說話**；`lag` 相對**法定公告期限**（次月 10 日）算，不是相對今天，否則每個月前 10 天都會誤報落後）。
2. **變了什麼**：門檻跨越、反證觸發、催化劑到期、現價過目標價（提醒不是動作）、**結構讀圖 staleness**（2026-09-17 Q5：N 份現行／該重讀 M，含哪個節點、哪個角度變了；§6.14）。
3. **佇列**：新 lead N、待 triage N、pq1 可做 N、pq2 卡在你 N、expired N。
4. **部位**：alpha 占淨值、全歸零少幾 %、追蹤表三個 power-law 統計量、**歸零旗標帳**（2026-09-18 D2：每檔四盞，**盞數與有紅燈的檔數分開算**——「一檔亮四盞」與「四檔各亮一盞」是兩件事；⚠ **灰＝沒量到，不是綠**，`alpha/wipeout.py` 是判色的唯一權威，心跳與 APP 都只照抄。「alpha 全歸零少幾 %」直接取 `beta` artifact 的 `risk.snapshot.alpha_total_weight`，**不另算一份**，也不得與同段「占已投入非現金」混用——分母不同）、幾檔共用同一需求錨、**兩個宇宙各自的賭注帳**（2026-09-17 Q2／Q1：有賭注／刻意不主張／**欠一個答案**，護城河籃子與量的候選**分開計數**——兩個宇宙問的是不同問題，合起來的數字沒有意義）。
5. **帳號計分表**（2026-09-24 起每天：tier 分布＋較昨；以下為 weekly 時代的完整表規格，現在住 APP 帳號計分表頁）：量測起始日與樣本數必印，讓「還沒量」看得見（2026-09-17 Phase 3 交付：D5 五欄＋三個已知偏差；**心跳只讀 `state/account_scorecard.json`，不自己算**——計分表要抓價格，而心跳零網路。更新跑 `python -m webapp materialize --scorecard`；讀不到就誠實說讀不到，不偷偷重建）。
   ⚠ **兩個基準必須都印**：2026-09-17 第一次量測，同一個帳號對 QQQ 是 −2.03%、對 SOXX 是 +3.06%——**相反符號**。只印一個會得到相反的結論，而兩個結論都是錯的。
   ⚠ 第 1 段另加**本月 X 花費／上限**與預算停抓列（`budget_exhausted` 刻意不是 `fetch_failed`：它是保護生效不是故障，塞進失敗會讓健康段恆亮，而恆亮等於零鑑別力）。

硬規則：LLM 失敗心跳照發；「未 triage N」必印（L13：沒發生與沒看到不得同形）；writer lock 照留（harvest 仍寫共用檔）；
不需要 agent 當 orchestrator 時，Codex sandbox 的 fixed entry 與 `tests/test_codex_daily_permissions.py` 要同一
change 對齊（sandbox impact review 五步，見 OPERATIONS）。

---

## 5. Skill 層（Claude Code / Codex 共用操作介面）

權威內容在 `skills/<name>/SKILL.md`；`.agents/skills/`（Codex）與 `.claude/skills/`
（Claude Code）是**生成的薄轉接層**，不直接手改。

**這裡不重抄 skill 清單**——每個 `SKILL.md` 的 `description` frontmatter 就是權威，
兩端 harness 自動載入。曾經在此維護一張表，新增 `luna-reviewer` 後沒同步，表上長期
少一個（2026-08-19 發現）。**清單會腐壞，判準不會**。

---

## 6. Alpha Research Core（`alpha/`）

五個投資問題，取代舊的五軸 Confidence（不並存，轉換器 `alpha/legacy_axes.py`）：

| Score | 問句 | 主要輸入 |
|---|---|---|
| Q1 結構稀缺 | 這個位置有多難繞過？ | Engine A 的 `substitutability`／`sole_source`／qualification |
| Q2 價值攫取 | 卡住了，錢收得到嗎？ | 客戶端資本承諾、毛利、議價 |
| Q3 盈餘曝險 | 這塊業務對 EPS／FCF 多重要？ | `segment_revenue_share`（Engine C 人工 ledger） |
| Q4 預期落差 | 市場是不是已經 price in 了？ | forward EPS 修正 vs 股價變動（`engine_c/estimates.py`） |
| Q5 催化劑 | 什麼時候會被重新定價？ | catalyst watch、財報／認證里程碑 |

**`source_reliability` 不是第六個維度，是套在所有維度上的上限**
（`alpha/evidence_quality.py`）：「你憑什麼相信前面那些答案」不是投資問題。

**結構表：** 結構事實的唯一權威是 `query/bottleneck.py::structure_table()`（2026-09-23 Phase 0 Step 0b.3 起；
前身 `rank_bottlenecks()` 已退役、名稱不留 alias）。它只做稽核——逐邊 rows（證據等級、sub、sole_source、qualification、
自報／外部印證、走不走得到錨）、`anchor_gaps`、INV-3 的 filtered reasons——**不排序、不設門檻、不給首選**（G1）。
alpha 不得自建第二套結構評分；「下一個研究誰」由圖報洞與 lead 驅動，不由分數。

> ⚠ **2026-09-16 轉向（D0–D15）→ 2026-09-22 圖是中心（G1–G12）：** 目標是邊緣小公司的 power-law 倍率。
> 對本節的後果：①排序不再是任何佇列或頁面的輸入（Phase 0 已落地，硬約束 4）；②候選門檻改為覆蓋厚薄（Phase 3 候選狀態板）；
> ③§6.2／6.4–6.6 的 FY+1 主流程與多年反向橋一併退役，財務只回答三題（Phase 3）。

### 「哪些標的值得看」的四維度（`AlphaSignal` 五 score 的前身）

1. **瓶頸地位** — `substitutability` 4–5、`sole_source`、距需求端跳數。
2. **需求錨點** — 資金在不在那條鏈上；為空者不是候選。
3. **客戶端資本承諾** — 誰付錢給誰。客戶掏錢綁供應商＝真瓶頸；**供應商付錢或給股權
   換訂單＝不是瓶頸**（POET 以 2,292 萬份認股權證換 Lumilens 訂單）。這一項自帶方向
   性且最難偽造，任何以「替代難度」為主的排序都抓不到後者。
4. **標的純度** — 瓶頸業務占該公司多少。同為 `sub=5`，AVGO 的 CPO 只是一塊業務，
   AXTI／POET 才有資訊落差。市值與 `analyst_count` 在 Engine C，**不在排序內**。
   ⚠ 2026-09-16 D11：市值與 `analyst_count` 仍不進排序，但它們是**篩選層 filter 的輸入**（覆蓋厚薄＝候選門檻，
   不限上市地；非英語 filing 是加分不是門檻）。filter 只過濾、不打分（ROADMAP Phase 4）。

### 排序驗證（Phase 6）

`alpha/backtest.py`＋`scripts/rank_forward_returns.py`：把 as-of 排序切前後段算等權
報酬。⚠ 它是**研究判斷的檢核，不是回測勝率**——期數個位數、標的高度集中在 AI 光互連，
前後段都不是獨立賭注；輸出強制列逐檔報酬與「這期主要由誰決定」。

---

### 6.1 Alpha Investment Read Model（`briefing/alpha_view/`，2026-09-05）

**角色一句話：StockBot 對一家公司目前投資理解的 canonical、machine-readable 表示。**
Alpha Card 只是它的一個 consumer。它是 **composition／read model，不是新的 authority**——
不重算 Q1–Q5、不重排、不算估值、不判定催化劑狀態，只做**選取、正規化、語意標註、組裝、
序列化**。

```
GraphResearchProvider ─┐
Engine C provider ─────┼─► alpha.context.build_research_context ─► ContextBuild ─┐
session 判斷檔 ────────┴─► alpha.models.compose_signal ──────────► AlphaSignal ──┤
Engine D 公開 cohort 事實（coverage／cohort_thesis／lifecycle）──────────────────┼─► build_alpha_investment_view
thesis/lifecycle.json＋catalyst_calendar.json、engine_c.checklist ──────────────┘          │
                                                                                          ▼
                                                                    AlphaInvestmentView（canonical DTO）
                                                                       │            │             │
                                                            Daily Brief 摘要   `python -m briefing   未來 Web／API
                                                            （compact_card）     alpha-card`（完整卡） （消費同一份 DTO）
```

**為什麼住 `briefing/` 而不是 `alpha/`：** 它必須同時看得到 Engine C、Engine D 與 thesis，
而 `alpha/contracts.py` 是零外部相依的 research contract。`AlphaSignal` 仍然只是研究判斷的
載體，**不是** UI DTO、不是跨層 composition blob、不含部位。四支檔案的分工：
`contracts.py`（型別＋字彙，純 stdlib）／`builder.py`（純函式組裝）／`render.py`
（Markdown，只依賴 contracts＋`shared.markdown`）／`sources.py`（唯一碰 I/O 的地方）。
`tests/test_alpha_view_render.py` 用 import 掃描守著這個分工。

**兩個正交的語意軸**（讓不同種類的知識在文字裡不再「看起來同樣可信」）：

| 軸 | 值 | 回答 |
|---|---|---|
| `status` | `available`／`partial`／`stale`／`missing`／`insufficient_evidence`／`not_modeled`／`not_applicable` | 這格有沒有東西、為什麼沒有。**`missing`＝有能力沒資料；`not_modeled`＝系統還沒有這個能力** |
| `basis` | `deterministic`／`observation`／`heuristic_proxy`／`session_judgment`／`narrative`／`structural_inference`／`none` | 這格是哪一種知識 |

`Datum` 在型別層強制 **Missing != Zero**：`status` 屬於「沒有值」那組時 `value` 必須是
`None`；`available` 時不得是 `None`。

**Authority map（每個 section 的真相來源與知識種類）：**

| Section | 來源 authority | basis／capability（今天） |
|---|---|---|
| structural_thesis | `structure_table()`（經 provider；原 `rank_bottlenecks()`，2026-09-23）＋`alpha.context.structural_score` | Q1 `deterministic`；邊屬性 `observation` |
| causal_paths | `GraphResearchProvider` 的路徑／`propagate`／`get_structural_changes_since` | `structural_inference`，capability＝**`structural_causal_model`**（不是 financial） |
| fundamentals | Engine C `financial_snapshots`＋manual ledger（segment）＋`checklist` | `observation` |
| consensus | Engine C `financial_snapshots`＋`engine_c.estimates`＋**`consensus_estimates`**（FY-identified EPS／營收，`fiscal_items`） | `observation`，status **`partial`**（快照欄位＋0y／+1y 兩個會計年度；缺第三年起、目標價高低、逐位分布） |
| ~~price_implied_expectations~~（2026-09-23 退役） | `alpha.context._implied_valuation` | **`heuristic_proxy`**（trailing/forward PE − 1）；隱含利潤率與 reverse DCF `not_modeled` |
| ~~internal_fundamentals~~（2026-09-23 退役） | **`alpha/fundamental`**（§6.2）：假設 ledger → 確定性橋 | `deterministic`（capability `financial_causal_model`）；每格 `dependencies.input_dependency` 帶最弱輸入假設的知識種類。**沒有假設或沒有基期觀測＝`missing`**（有能力、沒資料），不再是 `not_modeled` |
| ~~earnings_bridge~~（2026-09-23 退役） | 同上 | 每格 observation／assumption／derived 各自標 basis；`assumptions`／`sensitivities`／`selection` 隨附 |
| expectation_gap（2026-09-23 起只剩 `gap_closure`／`consensus_series`；`numeric_comparisons`／`opinion_stance` 退役） | Q4（session）＋估計修正 vs 股價（`engine_c.estimates`）＋**`alpha/fundamental/compare`**（`numeric_comparisons`） | Q4 `session_judgment`（ordinal）**與**數值 gap `deterministic`（capability `numeric_internal_vs_consensus`）並存、分開標；數值 gap 只在同期、同口徑、同幣別時有值，否則 `not_applicable`／`missing` |
| catalysts | AlphaSignal.catalysts＋thesis checkpoints＋Engine D 散文＋`shared.catalyst_state` | `partial`，capability＝`structured_dates_without_repricing_link` |
| falsification | AlphaSignal.disproof_conditions（L7 三件套）＋Engine D 散文＋thesis lifecycle | capability＝`structured_conditions_with_expiry_watch`；自動失效引擎 `not_modeled` |
| scenarios（`target_valuation` 一格已於 2026-09-23 退役） | AlphaSignal bull／base／bear | **`narrative`**；機率 `not_modeled`；`target_valuation` 自 2026-09-06 起照抄 valuation 的單點 fair value（逐情境仍無） |
| ~~valuation~~（2026-09-23 退役） | **`alpha/valuation`**（§6.4）：內部 EPS × 明示目標倍數 | `deterministic`（capability `deterministic_fair_value_v1`）；fair value／`value_date`／現價／gap 分開，gap 附 `gap_is_not`；沒有估值假設或內部 EPS＝`missing`；估值假設未宣告時點語意時 `value_date`＝`missing` |
| ~~implied_return~~（2026-09-23 退役） | **`alpha/implied_return`**（§6.5）：現價 ＋ fair value 時點語意 ＋ 明示 horizon | `deterministic`（capability `base_case_implied_return_v1`）；`price_return`／`annualized_price_return` 確定性、`horizon` 與 `value_date` 是判斷、`total_return`／`probability_weighted_return` **`not_modeled`**；四個輸入缺一＝`missing`；每次列 `is_not` |
| ~~entry_logic~~（2026-09-23 退役） | **`alpha/entry`**（§6.6）：implied return ＋ **明示的要求報酬判準**（`investor_policy`） | `deterministic`（capability `analytical_entry_threshold_v1`）；`entry_price`／`price_to_entry_gap`／`hurdle_comparison` 確定性、`required_annualized_return` 是**投資人政策**（新 basis `investor_policy`）；沒有判準＝`missing`＋「缺投資門檻判斷，不是 ETL 缺口」；alignment 不對齊＝`review_required`；每次列 `is_not`（**不是 buy／sell、不是部位、不是資本許可**） |
| ~~downside~~（2026-09-23 退役） | alpha://assumptions（`scenario=downside`） | ~~**`not_modeled`**，並列出「不要跟什麼混淆」~~（2026-09-18 D2 交付）：與賭注**對稱**的 overlay——反證成真時的假設套同一條橋。沒寫是 `missing`＋`not_yet_recorded`（有能力、還沒人寫），**不再是 `not_modeled`**；「不是什麼」由 `DOWNSIDE_IS_NOT` 帶著走（不是 bear case／不是機率加權／不是停損線／不是尺寸） |
| evidence | 全部 `EvidenceRef` 的索引＋as-of 篩選計數＋L8 品質摘要 | `observation` |

**as-of 視角的邊界（2026-09-05 Phase 1.1 定案）：** 三種來源三種處置，判準是「authority
答不答得出 T 時刻」。① Engine A（投影）與 Engine C（時序）：原生 as-of。② Decision Store：
append-only 且每張表帶時間戳，所以 `decision_lab.coverage_queries.company_decision_facts(as_of=…)`
做**真正的歷史過濾**（cohort `created_at`、decision `effective_at`、coverage `created_at`、
lifecycle 狀態由事件回放、variant perception 含 supersede 時點），回傳值帶 `point_in_time`；
builder **只接受標記與 `context.as_of` 相符的事實**，沒有標記或不符一律拒收成
`not_applicable`（呼叫端傳錯不會把當前值混進歷史卡）；到期狀態以 as_of 當今天判定。
③ `thesis/*.json` 與檢核點是當前狀態檔、沒有歷史 → 一律 `not_applicable` 並附 INV-6 原因。
Decision Store 只經 `mode=ro` sqlite 連線讀，查詢只回研究欄位、選 cohort 的規則寫在回傳值裡。

**判斷新鮮度：** session 判斷是對某一份 `ResearchContext` 做的。`compose_signal(...,
allow_stale_context=True)` 是唯讀 view 的明確 opt-in——舊判斷仍呈現但整段標 `stale`，
`identity.signal.context_matches=False`；`python -m alpha research --judgment` 維持嚴格。
判斷檔約定位置 `library/private/alpha/judgments/<TICKER>.json`（private，不進 Git）。

view 的 `capability_map()` 就是「知道什麼／還不知道什麼」的常駐計數器。

### 6.2 Causal Fundamental Model（`alpha/fundamental/`）——模型半邊已退役（2026-09-23，Phase 0 Step 0b.1b-C/H 2/2）

FY+1 因果橋（`bridge.py`／`model.py`：分部營收 × 假設 → 內部 EPS → 與共識的數值 gap）整組退役；`read model` 的
`internal_fundamentals`／`earnings_bridge` 兩個 section 與 `expectation_gap.numeric_comparisons` 一起拿掉。
**留下的是資料契約與 ledger 邏輯**（plan §0.6 #18／#28）：`contracts.py`（會計期間、假設紀錄、Engine C 觀測與共識型別）、
`assumptions.py`（`library/private/alpha/assumptions/` ledger 的解析／選取／supersede）、`compare.py`（共識口徑核實
`verify_consensus_basis` 與基期對帳）。read model 的 `consensus` section 直接讀 Engine C（`sources._engine_c_financials`），
模型原本的 PIT 自我核對逐條搬過去；refresh 的假設 artifact 由 `artifacts_from_assumptions` 登記。
原節逐字封存於 [`archive/2026-09-23-phase0-retired-sections.md`](archive/2026-09-23-phase0-retired-sections.md)。

### 6.3 Research Refresh／Dependency Invalidation（`alpha/refresh/`，2026-09-06 Step 0.5 v1）

**角色一句話：什麼變了？影響哪些研究成果？哪些只需重算？哪些需要重新研究？哪些已失效？**

它是 **dependency／orchestration authority**，不是 analyst authority——這條邊界必須寫死：

| 誰 | 產生什麼 | refresh 引擎對它做什麼 |
|---|---|---|
| Data authority（A1 Engine A、A2 Engine C） | 觀測、結構事實 | 只讀時序，導出 `ChangeEvent` |
| Research authority（A3：session 判斷、`OperatingAssumption`） | 判斷、假設 | **不產生、不修改**；只決定每個成果的 refresh state |
| Refresh／Invalidation（`alpha/refresh`） | `RefreshReport` | 不產生新事實、不產生新假設、不改 thesis、**不自動呼叫 LLM** |

```
Engine C 時序／圖投影差集／假設 ledger／Event Watch／lifecycle ─► briefing/alpha_view/changes.py ─► ChangeEvent[]
                                                                                                   │
既有 provenance（ComponentTrace.evidence_refs、OperatingAssumption.evidence_refs＋dependency_roles、  │
ModeledMetric.assumption_ids、ExpectationComparison.consensus_refs）─► artifacts.py ─► ArtifactDependency[]
                                                                                                   ▼
                                   alpha/refresh/resolver.py（policy.py 的表 × 引用命中 × 一層傳播）─► RefreshReport
                                                                                                   ▼
                                   briefing/alpha_view：refresh_status section＋各格 status；只組裝，不判 impact
```

**封閉字彙（contract）：** state ＝ `current`／`recalculate`／`review_required`／`invalidated`／`stale`／
`superseded`／`missing`；change class ＝ `market_price`／`consensus`／`financial_actual`／`company_guidance`／
`graph_edge`／`graph_claim`／`evidence`／`operating_assumption`／`fiscal_period_rollover`／`thesis_review_due`／
`disproof_signal`／`context_digest`（殘餘：digest 變了但沒有 class 能解釋——必須現形）。

**三條規則（改它們要先答出「現有幾個成果的 state 會變」，L14）：**

1. **`digest changed` 不是變化。** 每個 `ChangeEvent` 都指得出 class、authority、物件、`observed_at`（系統何時
   知道，決定 as-of 可見性）、`published_at`（世界何時知道，決定「判斷當時知不知道」）。同一身分、不同值才是
   變化——共識表「第一次出現」是資料覆蓋變了，不是世界變了（同 `documents` 不參與排序的理由）。
2. **recalculate ≠ review_required ≠ invalidated ≠ stale。** 確定性成果（Q1、橋、數值 gap、市場 proxy）的輸入
   變了 → `recalculate`；判斷型成果（Q2–Q5、thesis、假設）的依據 material change → `review_required`；
   supporting evidence 撤回／解析不到／review condition 宣告 → `invalidated`；L7 核查週期到期 → `stale`，
   不隱含任何新證據。舊 D&C 假設被新紀錄取代、或 FY2027 有了實際值 → `superseded`（歷史，不沿用）。
3. **不 cascade。** 影響只由 `policy.py` 的表（class → axis／basis／driver）與**引用命中**（變化的 ref ∈ 成果的
   supporting refs）決定；傳播只沿 `assumption_ids` 走一層（模型輸出 ← 假設）並標 `propagated_from`。
   **v1 materiality 立場：price-only 變化只讓市場導出量 recalculate，任何研究判斷維持 current**——沒有經量測的
   門檻能說「漲 6.6% 該重看、0.6% 不用」，假裝有比誠實說沒有更危險。共識有 1% 雜訊地板，那是抖動不是 materiality。

**假設 provenance（Step 0.5 擴充，舊 ledger 不改寫）：** `dependency_roles`（ref → `supporting`／`calibration`／
`comparison`）、`review_conditions`（machine-readable：metric／scope／period／operator／threshold／`on_trigger`）、
`provenance_semantics`（`legacy`＝2026-09-05 的 v1 紀錄；讀取端 fail safe：未分類 ref 當 supporting，同期共識 ref 依
前綴當 calibration）。**同期分析師共識不得是 supporting**（契約拒收）——那是 provenance 循環：共識支持假設 →
假設推出內部預測 → 再拿去比共識。Event Watch 的 `hypothesis_ref` 可指向 `oa_*` 假設 id；watch fired →
`disproof_signal` → 該假設 `review_required`，值不自動改。

**PIT：** `--as-of T` 只看 `observed_at <= T` 的變化、`established_at <= T` 的成果（其餘計數為 excluded）；
未來的 contradiction 不得回頭把歷史成果標 invalidated——當時它是 current。

**read model 的消費：** `SectionStatus` 多了 `review_required`／`invalidated`（有值但不得當 current）；`stale`
從此**只**表示時間／排程到期。`identity.signal.context_matches` 仍是「判斷對的是不是這份 context」的事實，
但它不再自動讓 Q2–Q5／thesis／情境整份 stale。沒跑變更偵測時（`refresh_changes=None`）退回舊語意並標
`change_detection=not_run`。`falsification.automatic_invalidation` 由 `not_modeled` 改為 `partial`（capability
`dependency_impact_v1`，明列不做：解析自然語言條件、改 thesis、呼叫 LLM）。

**入口：** `python -m briefing refresh <TICKER> [--scenario price_only|consensus_revision|graph_edge|new_guidance|
new_actual|fiscal_rollover|disproof] [--as-of]`；完整卡第 15 節；精簡卡 `refresh` 欄；`python -m alpha assumptions
--add` 的 spec 可帶 `calibration_refs`／`comparison_refs`／`review_conditions`。

**刻意不做（v1 限制）：** 語意 materiality（只有 class 級規則＋1% 雜訊地板）；自然語言 rationale／disproof 不解析；
`evidence`／`graph_claim` class 有契約但沒有 runtime 偵測來源（圖不記錄撤回）；ResearchContext 未持久化，所以
digest 殘餘差異只能整批標 `context_digest`；行情 as-of 仍以 `bar_date` 篩（判斷基線用 `fetched_at`）。

### 6.4–6.6 Valuation Model／Base-case Implied Return／Entry Logic——已退役（2026-09-23，Phase 0 Step 0b.1b C／F／H 組）

`alpha/valuation`（內部 EPS × 目標倍數 → fair value）、`alpha/implied_return`（現價 → fair value 的隱含報酬與兩桿歸因）、
`alpha/entry`（要求報酬判準 → 門檻價）與 read model 的 `valuation`／`implied_return`／`entry_logic` section、
Analyst View 的頭條那把尺、q4／q7 兩個問句、`briefing valuation／implied-return／entry` 三個子命令整組退役（G3：財務只回答三題，
不得長回估值模型）。三本 ledger（估值假設／horizon／entry 判準）的檔案留在 `library/private/alpha/`（L10），不再消費；
`CurrentPrice` 搬進 `market` section（現價是 A2 觀測，與估值無關）。**「已定價嗎」由 Phase 3 財務三題回答**，主參照是
自己的歷史、不設門檻。三節原文逐字封存於 [`archive/2026-09-23-phase0-retired-sections.md`](archive/2026-09-23-phase0-retired-sections.md)。

### 6.7 Analyst Consumer（`briefing/analyst_view/`，2026-09-07 Phase 2 Step 3.5 v1）

**角色一句話：把 canonical read model 依「使用者打開一檔股票時會依序問的六個問題」重新投影，
讓人在很短時間內看懂 StockBot 相信什麼、跟市場差在哪、怎麼算到這裡、最弱假設是什麼、什麼會讓結論需要重看。**

**產品決策（2026-09-23 Phase 0 改寫）：** 原本的 stock-level 主流程「Evidence → Internal Forecast → Valuation → Horizon →
Implied Return，終點是 implied return；EntryCriterion 是 optional analytical capability」整條已隨估值鏈退役（G3：財務只回答三題，
不得長回估值模型）。現在這一層的單位是**句與段**：短評（session 寫）→ 論證（鏈／時間表／風險）→ 研究（反證與檢核點）→
歸零旗標；`fundamental` 降為選配；readiness 只看核心面板（`headline`／`brief`／`argument`／`research`／`wipeout`），
optional 缺席不得拉低它，也不得為了讓畫面「完整」補任何預設值。

```
AlphaInvestmentView（§6.1 canonical read model；18 個 section，依資料結構排列）
        │  build_analyst_view（純函式；只組裝／排序／label）
        ▼
AnalystView ── headline   （現在多少錢：只有現價｜refresh／review state；2026-09-23 起無目標價、無隱含報酬）
            ├─ brief      （短評：session 寫的句，數字由 authority 填 placeholder；沒寫就「還沒寫短評」）
            ├─ argument   （論證：鏈／風險與認錯條件／時間表；2026-09-23 起 numbers／market／bet 三段退役）
            ├─ research   （Q6 Q1–Q5／thesis／催化劑／disproof／missing・stale・review_required）
            ├─ wipeout    （歸零旗標四盞：只給燈不給數字；灰＝沒量到）
            └─ fundamental（**optional**：Engine C 原始數字與同期共識；`why`／`entry` 兩個面板已於 Phase 0 退役）
                │
        readiness（只看核心面板 headline／brief／argument／research／wipeout）＋refresh 摘要＋limits（「不是什麼」）
                │
     `python -m briefing analyst-view <T> [--as-of] [--format markdown|json] [-o]`
```

**它為什麼不可能變成第二個研究層（型別層強制，不是自律）：** panel 裡每一行的 `datum` 都是
`AlphaInvestmentView` 裡**同一個 `Datum` 物件的參照**（`is` 相等）；`AnalystLine` 刻意**沒有 `value` 欄位**，
所以「值」只有一個住處。`tests/test_analyst_view.py` 用 `id()` 集合逐行比對——compose 只要自己 `Datum(...)`
生一格（哪怕值一模一樣）就會紅。三支檔案另有 import allowlist、float 字面值掃描（**全模組 0 個**）與
「不得 import 任何 `alpha.*` 模型模組」的檢查。

**唯一被允許的數值動作是排序**：既有敏感度依 `abs(fair_value_relative)` 由大到小。它不產生新值，
也**不是新的 attribution model**——`context.sensitivity_order` 把這句話寫在資料裡。

**「最脆弱的輸入」是宣告好的列入規則，不是新判斷。** `WEAK_INPUT_RULES` 是封閉字彙，每一條 `WeakInput`
必須說出自己被哪一條規則列進來：`largest_modeled_sensitivity`（既有敏感度中 |Δ| 最大）／`refresh_flagged`／
`heuristic_proxy_input`／`session_judgment_input`／`weakest_known_axis`（抄 `AlphaSignal.weakest_axis`）／
`unknown_axis`（該軸 missing——**未知不是「沒問題」**）。

**status roll-up 與 readiness 都是查表。** panel `status` ＝來源 section `meta.status` 取最嚴
（`_WORST_FIRST` 是宣告好的嚴重度序，且 `source_statuses` 保留取最嚴之前的原值）；
`readiness` ∈ `ready`／`ready_with_flags`／`blocked`，**只看核心四段**，判準逐字寫在 `readiness.rule`。
**optional panel 不參與**——`tests/test_analyst_view.py` 逐欄比對「有判準 vs 沒判準」兩份投影的 readiness。

**頭條那一句話不是 consumer 造的。** （2026-09-23 前）`implied_return.epistemics.one_sentence` 由
`alpha://implied_return/model` 自己組出，consumer 只是把它挪到最前面並註明出處；估值鏈退役後頭條只剩現價，判準不變——造句就是在 read model
之外生出第二種說法。

**PIT／materialize：** `--as-of` 直接透傳到 `fetch_alpha_investment_view`；投影本身是純函式，
`AnalystView.to_dict()` 完全 JSON-able 且保留 `null`，可預先產生給未來 APP 點擊直接讀
（不需要 runtime LLM，也不需要重跑任何 authority）。

**刻意不做：** buy／sell／sizing／portfolio、跨標的比較與排序、任何新的 forecast／valuation／return 公式、
為 consumer 新建 attribution model、runtime LLM、APP／API（Step 5）。

---

### 6.8 缺席語意（`alpha/absence.py`＋`alpha/abstention/`，2026-09-07 Phase 2 Step 5）

**角色一句話：`status` 回答「這一格能不能用」，`absence_kind` 回答「它為什麼沒有」——兩者正交。**

事發（2026-09-07 Coverage Pilot §4.3）：6324.T 的估值 blocker 逐字是「尚未寫入任何估值假設」，
而真實狀態是研究結論「126x 錨不住任何可辯護的倍數，所以不寫」。**兩種語意共用一句話**（L12），
而 APP 會把那句話直接放到使用者眼前——他無從分辨「還沒做」與「這已經是答案」。

```
alpha/absence.py         封閉字彙 ABSENCE_KINDS（11 種）＋ DEFAULT_ABSENCE_KIND（status → kind 的查表）
        │                零相依（只有 __future__／typing），所以呈現層 import 它不違反分層
        ├─ ValuationResult.absence_kind      ← build_valuation 走到哪個分支**自己宣告**
        ├─ ImpliedReturnResult.absence_kind  ← 上游缺席時**繼承**估值層的 kind，不降級成「還沒寫」
        ├─ Datum.absence_kind / SectionMeta.absence_kind（read model）
        └─ AnalystPanel.absence_kind / AnalystBlocker（consumer；blockers 的欄位化版本）
```

**十一種 kind**：`not_yet_recorded`（還沒做）／`deliberate_abstention`（刻意不主張）／
`method_not_applicable`（方法對這筆資料無定義）／`upstream_unavailable`（上游缺，要補的是上游）／
`inputs_incompatible`（每格都有值但身分不相容）／`provider_missing`／`capability_absent`（not_modeled）／
`point_in_time_unavailable`／`insufficient_evidence`／`invalidated`／`not_applicable_unspecified`。

⚠ **`not_applicable` 的預設刻意是 `not_applicable_unspecified`。** 它今天同時被 PIT（沒有時點投影）
與方法層（本益比法遇到虧損）使用；猜任何一邊都是替 authority 造一個它沒說過的區別。知道自己是哪一種的
呼叫端要**明示**——那正是這張表存在的目的。

**`SETTLED_ABSENCE_KINDS`（刻意不主張／方法不適用／本層沒有這個能力）表示「這已經是答案，不要去補」。**
⚠ 它**不**讓 readiness 變好——blocked 還是 blocked，只是使用者知道該不該花力氣。

**`Abstention`（`alpha/abstention/`）是「刻意不主張」的 append-only authority。**
`library/private/alpha/abstentions/<TICKER>.jsonl`；content-addressed `ab_*` id、
`supersedes_id`／`retracted` 語意與假設 ledger 完全一致、as-of 選取共用同一套規則。
三條型別層強制：①**結構上不可能攜帶數字**（`_assert_no_value_fields` 在 import 當下掃描欄位名，
長出 `value`／`target_pe`／`multiple` 之類的欄位是 import 失敗）；②`reason` 與 `revisit_when` 都必填
（沒有「什麼證據出現才會改寫」的 abstention 是永遠不會響的火警警報，L7）；③`layer`／`subject` 是封閉字彙
（~~v1 只有 `valuation.forward_earnings_multiple.target_pe`~~ **2026-09-17：這份清單已經腐壞過一次**——`research/axis.catalyst` 2026-09-11 加入時沒同步到這裡。清單的 SSOT 是 `ABSTENTION_SUBJECTS`，查證：`python -c "from alpha.abstention.contracts import ABSTENTION_SUBJECTS;print(dict(ABSTENTION_SUBJECTS))"`；**加一層的代價是要多一段消費端語意**，所以每層只開資料支持的那幾個 subject），否則它會變成「任何一格都可以宣布自己是刻意留白」
的萬用擋箭牌。入口 `python -m alpha abstention <T> --list／--add spec.json／--retract <id>`。

**它不是第二份 ValuationAssumption authority**（估值假設 ledger 已於 2026-09-23 隨估值鏈退役，資料留）。後者曾擁有「目標倍數是幾」，前者只擁有「我們不主張」；
宣告之後 `fair_value` 仍然是 `None`、readiness 仍然 `blocked`，改變的只有那句「為什麼」。

**accounting basis 的呈現別名（`ACCOUNTING_BASIS_DISPLAY`）** 解的是同一天記下的另一筆語意債：
`ACCOUNTING_BASES = ("gaap", "non_gaap", "not_applicable", "unverified")` 是 **contract identity**——
它是三本 private append-only ledger 每一筆紀錄身分的一部分，改字彙等於改既有紀錄的身分（L10）。
所以**不改字彙，加一層呈現別名**：`gaap` → 「As reported（法定財報口徑）」，
且 label **一律不含準則名稱**（Lynas 是 AASB／IFRS、HDS 是日本基準、IQE 是 IFRS，三者在 ledger 裡都寫 `gaap`；
authority 裡沒有「是哪一套準則」那一格，寫上去就是替它主張它沒說過的事）。`raw` 永遠一併輸出供稽核。

---

### 6.9 Web App／API（`webapp/`，2026-09-07 Phase 2 Step 5 MVP）

**產品 invariant：`LLM changes cognition; APP reads cognition.`**

```
authority（Neo4j／Engine C／private ledger）
     │  python -m webapp materialize   ← **唯一**會跑模型、連 DB、讀 ledger 的地方（約 4.2 秒／檔）
     ▼
AlphaInvestmentView → AnalystView → MaterializedArtifact（JSON，atomic write）
     │                                library/private/app/analyst_view/<TICKER>.json
     │  python -m webapp serve         ← 純讀：open → json.loads → validate → return
     ▼
GET /api/v1/{health,meta,stocks,stocks/{ticker},ranking,beta,coverage,watches} ＋ / （responsive Web App）
     ▼
Cloudflare Tunnel（既有那條）→ Cloudflare Access → iPhone Safari／桌機瀏覽器
```

**為什麼 materialize 與 serve 必須是兩條責任鏈：** 不只是「組裝一次要 4.2 秒」，而是
**點一下就重跑一次研究會讓 request path 有能力改變（或看起來改變）系統對一家公司的認知**。
分開之後，「APP 只是讀」變成一件可以被機械證明的事。

**四種互相獨立的證明**（`tests/test_webapp_request_path.py`，25 條）：
①**import 靜態掃描**（serve 端三個模組的 import 是 allowlist）；
②**runtime 模組哨兵**（打完一輪 request，斷言 `sys.modules` 沒多出任何模型／IO 模組——擋函式內延遲 import）；
③**檔案系統快照**（request 前後對 artifact 目錄與 `library/private/` 取雜湊，斷言一格未動——同時擋寫入與
cache-miss 自動重建）；④**socket 封殺**（request 期間 `connect`／`create_connection` 直接 raise，
斷言回應照樣完整正確）。⚠ 第 4 條攔的是 `connect` 而不是 socket 建構子：TestClient 的 event loop 自己要用
一對 loopback socket，攔建構子會攔到測試腳手架而不是被測物（L15-1）。

**artifact 契約**（`webapp/contracts.py`）：`schema_version`／`generated_at`／`as_of`／
`research_context_digest`／**兩個 digest**／`readiness`／`refresh`／`overview`／完整 `view`。
- **`content_digest`** 對整份內容取雜湊——偵測寫到一半或寫入後被改。
- **`freshness_identity`** 只對「認知狀態」取雜湊（as-of、context digest、read model 版本、readiness、
  refresh overall）。**價格動了不算認知變了**；兩件事共用一個訊號就會讓其中一件永遠讀不出來（L12）。
- fail closed：解析失敗／版本不符／digest 不合／缺必要欄位 → `ArtifactUnavailable` → **503**。
  ⚠ **「artifact 讀不到」（503）與「這檔沒有研究結論」（200 ＋ `readiness=blocked`）是兩件事，不得同形。**
- **stale 是狀態不是錯誤**：過期照樣回，明確標年齡，**絕不重建**。

**overview 是選取不是計算。** 清單卡片要的那幾格全部照抄 `AnalystView`——沒有百分比換算、沒有幣別換算、
沒有 gap 重算。單位原樣帶著走（GBp 與 GBP 差 100 倍，`dependencies.quote_unit` 是欄位不是要 parse 的句子）。

**private path 在 materialize 端遮蔽一次。** read model 的理由句會寫出 authority 檔案路徑
（例：「找不到 session 判斷檔（library/private/alpha/judgments/…）」）；那對開發者有用，但它是 private
filesystem 結構，不該經由 HTTP 出去。遮成 `«private-authority»`，**其餘文字逐字保留**。
在 materialize 端做一次，而不是讓每個消費端各自記得要遮（L16）。

**state artifact（2026-09-08，呈現責任重切 B1）：** per-ticker 的 Analyst View 之外，多了**跨標的的 state**
（`library/private/app/state/<kind>.json`；`webapp/contracts.py::STATE_SCHEMA_VERSIONS` 是封閉的 kind 字彙，
2026-09-23 起是 `structure_table`／`beta`／`coverage`／`watches`／`positions`／`structure_readings`／`account_scorecard`；
`ranking`／`basket`／`multi_year` 已於 Phase 0 退役，查證 `python -m webapp status`）。`python -m webapp materialize --structure-table`
走與 `python -m query.bottleneck` **同一條路**（同一個 driver、`fetch_assertions`、registry），把 `structure_table()` 的逐邊事實
**照抄**成 artifact——不排序、不加權、不設門檻、不給首選（G1）；`GET /api/v1/structure-table` 與單檔同一套紀律：讀不到 503 ＋ remedy。
（2026-09-08 至 09-23 之間這裡是 `ranking` kind：兩份排序＋`top_pick`；隨 G1 退役，見 plan §0.6 #40。）

**`beta` kind（2026-09-08 B2）：** `python -m webapp materialize --beta` 以 `--no-refresh --no-record-risk` 純讀呼叫
`scripts/daily_beta_snapshot.run()`（同一個 `portfolio.allocation.build_beta_monitor`），**不重抓行情、不 append 風險快照**；
sleeve／差距狀態／行情狀態／降級原因的中文標籤全部從 `portfolio.allocation` 的對照函式取（L16）。逐檔折線的序列只搬
Engine C `technical_observations` 的 `session_date`＋`close_adjusted`——那張表還留著 08-29 前的動能欄位，**永遠不進 artifact**
（`tests/test_webapp_beta.py` 掃整份 JSON 鍵名）。畫面依 dataviz skill：水平堆疊條（現在的配置，色跟 sleeve 走）、分歧條
（距目標多遠，灰帶＝容忍區間）、儀表（風控上限、52 週位置）、單系列折線（自身收盤，含十字線 tooltip 與表格版）；
調色盤用 dataviz 參考實例的已驗證值（深淺兩套）。`freshness_identity` 只含各 sleeve 狀態／各檔行情狀態／風險警告，
價格心跳變了不算認知變了。

**`coverage`／`watches` kind（2026-09-08 B2b）：** 前者照抄 `query.coverage_gaps.scan()` 的分桶，並把 🔴 桶依
**前綴**切成「真正該挖的子瓶頸（`tech:`／`mat:`）」與「抽取產生的產品名詞（`prod:`）」——那是機械比對不是語意判斷，
判準與固定文字都住 `query/coverage_gaps.py`（markdown 與 artifact 同源）。後者照抄 Event Watch registry 的
`counters()`／`sweep_due()`／`is_stalled()` 與 `leads.trace_backlog()`，把**停滯**與**需要當場處置的追源**
獨立成區——那是這個機制唯一會安靜失效的地方（L14：防呆要自己出現）。兩者的 `freshness_identity` 只含
「哪些節點還空白」「有哪些 watch、各自什麼狀態」，節點改名或 `poll.last_checked` 更新不算認知變了。
⚠ **APP 不寫任何東西**：不喚醒 watch、不消化 fired、不改 lead 狀態。

**`positions` kind（2026-09-08 B2-positions）：** 把 `scripts/outcome_if_settled_today.py` 的資料收集段
抽成 `collect()`，另抽 `equal_weight_aggregate()`／`live_lane_rows()`／`anchor_health()` 三個純函式——
**markdown 與 artifact 讀同一份**（L16；第二份實作會立刻開始偏離）。抽取是行為保持的：`main()` 只剩
「collect → render」，輸出以「去數字後的骨架」比對零差異（盤中重跑會因價格變動換名次，所以不能比位元組）。
materialize **只呼叫 `collect()` 不呼叫 render**，因此不 append 排序快照、不寫聚合檔：維持唯讀。
計數器直接取 `DecisionStore.capital_expression_counters()`（本來就回傳 dict，不需重構 Engine D）。
⚠ 這一頁的**排版順序本身是判準**：真實部位 → **樣本效度** → 計數器 → 聚合 → 逐檔。反過來排的話，
一份有效 n 接近 1 的觀測會讀起來像 N 個獨立驗證（`tests/test_webapp_positions.py` 斷言這個順序）。state 目錄的解析只有一條規則
（`webapp/store.py::resolve_state_dir`：明示 > analyst 目錄下的 `state/` > 預設），serve／materialize／status 都走它。

**Web App 的資訊階層**（`webapp/static/`，vanilla JS，零外部資源，CSP 只允許 same-origin）：
⚠ **2026-09-08 依使用者回饋重排**（原話：「太多展開、太多字、全部是內部術語，基本上看不懂」）。
單檔頁順序改為：①**結論**（現價／我們算的目標價／要漲跌多少）→ ②**這檔自己的收盤走勢**
→ ③卡在哪（只在 blocked／有旗標時出現）→ ④最脆弱的地方（前 3 條）→ ⑤什麼會推翻它
→ ⑥我們 vs 市場 → ⑦**一個** `<details>`「完整細節」把原本六個面板的每一格原樣收進去。
**刪的是版面不是內容**：API 回應一個欄位沒少，`tests/test_webapp_api.py` 斷言六個面板的
renderer 都還在那個 details 裡。

**白話別名（2026-09-08）：** `PLAIN_PANEL_TITLES`／`PLAIN_LINE_LABELS`／`PLAIN_ABSENCE_SHORT`／
`PLAIN_READINESS` 住 `briefing/analyst_view/contracts.py`，經 `.meta.json` 送到 API——
**字彙一個字沒改**（那是 read model 與 private ledger 的身分，L10），加的是「同一個東西怎麼講給人聽」，
同 `ACCOUNTING_BASIS_DISPLAY` 的先例。前端**不維護第二份**：原本 app.js 裡硬編碼的 `ABSENCE_SHORT`
已移除（它正是 L16 說的重造品，字彙一改它就安靜偏離）。別名**不得宣稱 authority 沒有的東西**——
`ready` 的說明逐字寫著「不是『可以買』的意思」。

**單檔走勢圖：** `alpha/providers/close_series.py` 取 180 個**已收盤**交易日（不含今天的盤中 bar，L12），
在 materialize 端抓、存進 artifact 的 `price_series`。它是**脈絡不是訊號**：不參與排序、不決定尺寸、
不畫任何均線或動能指標（`tests/test_webapp_api.py` 掃這段程式碼）；`freshness_identity` 不含它——
價格動了不算認知變了。抓失敗只是沒有折線，不讓整份 artifact 失敗。
**UI 只改資訊階層，不產生任何新的 summary judgment**：頭條那句話取自
（2026-09-23 前）`implied_return.epistemics.one_sentence`（authority 自組）並註明出處——估值鏈退役後頭條只剩現價；
缺席語意的中文說明來自 `/api/v1/meta` 的字彙表，前端不維護第二份對照表。

**技術棧沿用既有的**：`starlette` ＋ `uvicorn` 已隨 `mcp>=1.28` 安裝，**本次沒有新增任何套件**，
也沒有前端建置工具鏈。部署重用既有 Cloudflare Tunnel（見 `deploy/cloudflare/README.md`）。

**刻意不做：** runtime chatbot／LLM、broker、買賣、部位尺寸、Portfolio 排序、跨標的排序（2026-09-23 起 `/structure-table` 只照抄 `structure_table()`，不排序）、
任何寫入端點、原生 App。

---

### 6.10 賭注：variant scenario → payoff——四價已退役（2026-09-23，Phase 0 Step 0b.1b-E）

「如果對了值多少／判斷錯了值多少」的算術（variant／downside overlay 各跑一次估值鏈得四個價格）與首屏那把尺整組退役；
`bet/variant.overlay`、`bet/downside.overlay` 的 Abstention 字彙與 ledger 資料留（L10），`bet` 面板改純文字讀 `our_bet`。
反證那一端沒有退役——它住 `research` 面板的 disproofs，Phase 1 接 watch registry。原節逐字封存於
[`archive/2026-09-23-phase0-retired-sections.md`](archive/2026-09-23-phase0-retired-sections.md)。

### 6.11 投資人短評（`alpha/narrative/`，2026-09-15）

**角色一句話：首屏的單位是「句」不是「格」——七格前因後果，文字由 session 寫、數字由 authority 填。**

```
python -m alpha research <T>  → packet 多 brief_frame（七格提問＋placeholder 字彙＋禁字表）
        │  session 寫七句（只寫文字與 {placeholder}，每格帶 evidence_refs）
        ▼
python -m alpha brief <T> --add spec.json  → library/private/alpha/briefs/<T>.jsonl（append-only，ib_*）
        │  型別層：七格缺一不可／placeholder 封閉／禁字拒收／每格必帶引用
        ▼
read model InvestorBriefSection：fill_brief() 把既有 Datum 的值格式化填入 placeholder（缺值印「（尚無）」）
        │  一把尺（現價／base 目標／賭注目標）＋一顆燈（refresh overall 白話）
        ▼
AnalystView.brief（optional）→ APP 首屏 briefCard；六張卡收進「為什麼這樣算」，再下一層「完整細節」
```

**為什麼數字用 placeholder：** session 打的數字會過期、會錯、會與 authority 不一致；placeholder 讓句子永遠
讀到 materialize 當下的值，而且填不到時那一格自己現形（`partial`＋理由），不是留白。
**為什麼禁字表在型別層：** 首屏是投資人的；「白話別名」那次是把欄位翻成中文，欄位還在——這次是欄位不上首屏。
**套件叫 `narrative` 不叫 `brief`：** `alpha/brief.py` 已是 daily brief 的渲染模組。

### 6.12 個股頁三層：短評／論證／稽核（2026-09-15）

**判準一句話：消費層的單位是句與段；格只住稽核層。**

| 層 | 讀法 | 內容 | 誰產生文字 |
|---|---|---|---|
| ① 短評 | 20 秒 | 七句＋一把尺＋一顆燈（§6.11） | session 寫、authority 填數字 |
| ② 論證 | 5 分鐘，可長文 | 六段：這條鏈怎麼走／數字怎麼算出來／和市場差在哪／賭注／風險與認錯條件／時間表；段後附研究時寫的長文（假設理由、賭注理由、風險、認錯條件，逐字）與圖裡的 claim 引文（statement、誰說的、哪天） | 算術與圖的敘述＝封閉句型（`alpha/narrative/argument.py`）；判斷＝session 長文照抄 |
| ③ 稽核 | 不是給人讀的 | 原本的六張卡＋完整細節（每格的來源、狀態、算式、敏感度、refresh、限制、警告） | read model 的格 |

```
graph provider.get_narrative_context(company_id, node_ids)   ← 節點 name ＋ Claim.statement／SourceDoc（origin、published_at）
        ▼
builder._argument_section：只選取既有 Datum（chain／risks／disproofs／checkpoints；bridge／comparisons／reverse／payoff 四類已於 2026-09-23 退役）
        │  → alpha.narrative.argument.*_paragraph（格式化與選詞，零算術）
        ▼
ArgumentSection（6 個 Datum：value＝段落；dependencies.long_form／citations）→ AnalystView.argument（optional）
        ▼
APP：briefCard → argumentCard → priceCard → drill「稽核」→ drill「完整細節」
```

**三條規則：** ①句型輸出掃同一張禁字表（`FORBIDDEN_TERMS`），「跳／邊／sub=5／tier」不出現，只講「誰說的、有沒有別人印證」；
②只有公司自己說的連結合成一句並點名為「整條鏈最薄的地方」，有印證的逐條講；③缺料就一句話說缺什麼，不硬寫、不補。
**還沒做：** 清單頁同構（R4）；`EvidenceRef.quote` 仍空——論證層直接查 Claim，不經 evidence index（R3 留待）。

### 6.13 賭注 V1–V2：熟成度、市場承認（2026-09-15；籃子與目標價比較已於 Phase 0 退役）


| 件 | 住哪 | 一句話 |
|---|---|---|
| 熟成度（V1） | `Catalyst.resolves` → builder 的 `catalyst_quantitative_link` | 催化劑指名它裁決哪幾條假設；state＝只看事件日期與 ledger created_at（resolved／due／pending／unlinked），不解析散文 |
| 市場承認了嗎（V2） | `alpha/gap_closure.py` → `expectation_gap.gap_closure`／`consensus_series` | 共識自判斷日以來朝我們移了幾成；起點等於我們的值時 None 不是 0；量測不是訊號。⚠ 2026-09-23：「朝我們移了幾成」的分母（內部 EPS）已退役，`closed_fraction` 恆 `None`（不是 0）；只量共識自判斷日以來的移動 |
| ~~目標價比較（V2）~~ | ~~`implied_return.target_reached`~~ | 2026-09-23 隨估值鏈退役（C 組） |
| 兌現出口（V2b） | `thesis/pending_lifecycle.py::ALLOWED_TRANSITIONS`＋`lifecycle_schedule.is_due` | `realized`：active／watch → realized → retired／revised；恆視為到期。進入由人提案（thesis mutation gate），`target_reached` 只提醒 |
| ~~籃子（V3）~~ | ~~`webapp/basket.py`~~ | 2026-09-22／23 Phase 0 退役（G1）；Phase 3 以候選狀態板回來 |

⚠ 2026-09-16 D3：`realized` **降為提醒，不觸發出場**——出場只認反證；lifecycle 字彙不動，改的是它的後果（ROADMAP Phase 5）。

### 6.14 結構讀圖（`query/structure.py`＋`alpha/structure_reading/`，2026-09-17 Q4／Q5）

**瓶頸性不是一條邊。** 圖給的是一堆單邊事實，賭注要的是一個結構判斷，中間原本是空的——
「需求側繞不過、供給側誰都不獨佔」這種話要四條邊一起讀才讀得出來，而每次都要手打十幾條查詢。

| 層 | 誰做 | 可不可以決定去留 |
|---|---|---|
| 圖（事實與 provenance） | 確定性 loader ＋ 人工 gate | — |
| 結構表（`structure_table`；跨檔排序已於 2026-09-23 退役） | 確定性，零 LLM | 不排序、不設門檻、不給首選 |
| **結構讀圖** | `query.structure` 查（零 LLM）＋ 互動 session 讀 | **不可以**——只寫下讀到什麼，不濾、不排、不給尺寸 |
| 賭注／Abstention | 人（或 LLM 起草、人確認） | 不可以 |

**五個角度是封閉清單**（`ANGLES`）：需求側／供給側／下一層／反向路徑／需求錨可達性。
清單來自 2026-09-17 那次真的問出答案的四次查詢，不是憑空設計——要加第六個角度前先問
「它在哪一個實際案例裡改變過結論」，答不出來就不要加（L17-4）。

**維護靠「存輸入，不存結論」**（`alpha/structure_reading/`，append-only ledger，主鍵是 node 不是 ticker）：
紀錄的主體是**當時那五條查詢回什麼**，判讀只是附帶。存結論沒有用——它不會告訴你什麼時候不再成立。
⚠ 比對的是**查詢結果集**而不是「我讀過哪幾條邊」：最危險的變化是「多了一條我當初沒讀到的邊」，
存邊清單偵測不到，存結果集偵測得到。

```
query.structure <node>  ──result_digest──▶  ledger（sr_*：angles 快照 ＋ kind ＋ 憑什麼 ＋ expires）
        ▲                                              │
        └── webapp materialize --structure-readings ◀──┘   （確定性比對，零 LLM）
                     │
                     ├─▶ state artifact `structure_readings` ─▶ 心跳第 2 段「該重讀 N」
                     └─▶ 佇列段 `stale_structure_readings` ─▶ research-drain（互動 session 重讀）
```

**分級（`staleness.py`）**：供給側增減／sub 變動＝`high`；下一層／反向路徑／需求錨＝`normal`；
只有 evidence＝`low`（記錄，不進佇列）。⚠ **binary 的 stale 會恆亮，而恆亮＝零鑑別力（L14-4）。**
`documents` 計數在更上游就被擋掉（`EdgeView.key()` 不含它）——它是研究量的函數，
讓它觸發重讀等於讓「我們讀得多」自己製造工作。

**staleness 直接接既有 disproof，不另立通知路徑**：對一個量的賭注來說，「供給側多了一家」
本來就是它的 disproof 條件之一（賭的是產能一時補不上）。系統**只標記**；
thesis 要不要改由人決定（thesis mutation 是四個人工 gate 之一）。

⚠ **這套機制維護的是「讀圖跟圖還一不一致」，不是「讀圖對不對」。** 一份跟圖完全一致但判斷錯誤的
讀圖，digest 永遠不會變——**那是設計如此，不是漏洞**；「對不對」要靠 outcome 量測。兩件事不得混為一談。

⚠ **A/B 判準表刻意還沒機械化**：先讓它以文字形式產出幾十份、看它講得準不準，再談要不要寫成程式
（INV-5：未量測的機制不得享有默認信任）。所以 `kind` 是**寫的人宣告的**，型別層只驗字彙。

## 7. Engine D（Decision Lab）——frozen 2026-09-22（G12）

- 研究側（signal intake → context 凍結 → coverage → decision → action card → live choice／fill）於 2026-09-23（Phase 0 Step 0b.4） 整組退役。
  留下：`decision_lab/store.py`（寫入方法無呼叫端；`record_live_choice`／`record_live_fill` 直接拒絕）、`coverage_queries.py`
  （`mode=ro` 純讀，個股頁 research 面板與 `scripts/catalyst_watch.py` 讀凍結歷史）、`cli.py`（`status`／`history` 唯讀）、
  `bootstrap.py`／`models.py`／`schema.sql`／`adapters/holdings.py`（備份還原與 store 的相依）。
- Decision facts 存於 ignored `library/private/decision_lab/`；只允許 backup／restore，**不再寫入、不做破壞性 reset**。
  歷史唯一一筆 live choice（2026-08-18 COHR 10 股）留作稽核。查證：`python -m decision_lab status`（sha256 對 Phase 0 基準）。
- A5 的現行落點：成交事件內嵌收據住 `library/trades/trade_log.jsonl`（`scripts/record_trade.py`）；資本硬擋住 `risk/hard_caps.py`（§8.2）。
  U7（2026-08-28）拆掉的是憑空的建議尺寸，不是煞車；Phase 0 把煞車搬到真的有人走的路上。

---

## 8. Portfolio / Risk（`portfolio/`＋`risk/`）

**單向：view → target exposure → hard limits。** A4 不形成 view，A3 不算尺寸。
判準與禁令（band 不是 gate、水位只呈現、不得復刻擇時語言）住 `AGENTS.md`；
這裡是它今天長什麼樣。

⚠ **呈現的家自 2026-09-08 起是 APP（`#/beta`），不是 Daily。** 下面這些欄位規格、燈號文字、
台股 freshness 與槓桿商品序列規則**一條都沒改**，改的是它們每天出現在哪裡：APP 由
`-m webapp materialize --beta` 每日更新、隨時可看，Daily 只印門檻跨越與狀態翻轉。
**Daily 仍須在 APP 當天沒被 materialize 時把這件事印出來**——否則「看不到」與「沒發生」同形（L12）。

⚠ **2026-09-16 D6：beta 凍結開發。** 本節只維護「大盤比例」觀測；欄位規格不再擴充，beta 個股呈現若擋路可拆，
不為維持 beta 架構繞路。以下規則在凍結期間照舊有效。

**輸入／輸出（`target-architecture.md` §9）：**

| | `portfolio/` | `risk/` |
|---|---|---|
| 輸入 | `AlphaSignal[]` ＋ 現有持股 ＋ `config/target_allocation.json` | portfolio 的 target exposure |
| 輸出 | target exposure、配置差距、相對水位 | binding limits、violation 清單 |
| **不做** | 不形成 view、**不排序標的** | 不判斷好壞 |

`portfolio/alpha_exposure.py` 是 alpha 那一側的接點（Phase 7）：把 `AlphaSignal[]` join
到持股，回答「**這些候選我現在持有多少**」。它輸出的每個數字都是已經發生的事實，
**不是建議**；候選順序原樣沿用傳入順序（本層不排序；跨檔排序已於 2026-09-23 退役）。
⚠ 它刻意以 duck typing 接受 signal，**不 import `alpha/`**——保持
`portfolio/ → alpha/` 沒有相依。
⚠ 持股讀不到時**整份降級並帶出 `blockers`，不逐檔輸出 0.0%**：那會讓使用者看到
「你一檔都沒買」，而事實是「我沒讀到你買了什麼」（L12）。
`single_position_nav_cap_reference` 的欄位名自己說出它不是 gate——真正的硬擋在
`store.record_live_choice`。
⚠ 2026-09-16 D14：**部位真相是 Google Sheet**（貸款額度、投入標的、現金）；Decision Store 只留可選 receipt；
alpha 原則上不用貸款資金是使用者自己的紀律，**系統不建 gate**（A5 不擴張）。

- **目標配置比例** SSOT 只有 `config/target_allocation.json`：sleeve 層級六格，分母是
  **已投入的非現金部位**（不含現金；cash floor 是另一個 authority）。
  查證：`python -c "import json;d=json.load(open('config/target_allocation.json'));print(d['basis'], sorted(d['sleeves']))"`
  ⚠ 2026-09-16 D1：**alpha 格改 `observed_only`**（只印不比），beta 五格目標保留——沒有目標時「誰跌深投誰」就回來。
  落地前 config 六格都還有 `target`；查證：`python -c "import json;print(json.load(open('config/target_allocation.json'))['sleeves']['alpha'])"`。
- **相對水位** 只用位置指標：52 週區間位置（主要）、距 52 週高點、距 SMA200，
  全部取自商品**自身**價格序列。⚠ **不得用動能指標表達水位**：RSI 量的是最近漲跌的
  單邊程度，與「站在自己區間哪裡」可以完全脫鉤，而且它正是 2026-08-01 測失敗的輸入，
  以「水位」之名放回來是換名字重來。
- **燈號固定配文字**：🟢行情正常／🔴資料不足（含 TWSE 官方較新而暫時隔離）／⚪歷史不足。
  舊語意（🟢可評估／🟡冷卻／排序中／⚪觀察／🔴暫停新增）已於 2026-08-29 廢止，不得回填。
- **標的表只負責三欄比較**：行情心跳（自身價格）、相對水位（自身價格）、所屬 sleeve
  配置狀態。可部署現金、投組 hard caps 與兩條相關性警告是**全局條件**，不在每檔重複。
- **逐檔心跳的最小要求**：每列明示商品自身的「最新完整交易日 `YYYY-MM-DD`＋1 日漲跌」；
  不能只寫沒有日期的「1 日」，也不能把最近收盤誤稱即時今日行情。
  `stale`／`quarantined` 時改列官方 reference 的日期與當日漲跌並附降級原因。
  逐檔表欄位保留完整（心跳 1／5／20 日＋52 週區間位置、距高點、距 SMA200）——
  2026-09-02 的「輕量版面」砍的是段落與重複敘述，**不是表格欄位**。
- 槓桿／重疊商品必須用自身價格序列：TQQQ 不得冒用 QQQ（實測 69% vs 85%），
  00631L／006208 同理不得冒用 0050。
- **台股 freshness：** `.TW` 先用 TWSE `STOCK_DAY_ALL` OpenAPI 校驗最新交易日；
  Yahoo session 落後、官方代碼缺列或 freshness 取不到時，該標的行情必須 `quarantined`，
  改列官方 reference 並附降級原因。⚠ 2026-08-29 起**單檔行情降級不再歸零任何 supported
  range**；降級的後果是那一列的水位不可信、必須現形，不是靜默消失。
  TWSE 的未還權 OHLC 只作最新日期與當日漲跌 reference，
  **不得混入 Yahoo adjusted-close 長期序列**。
- **自有現金可部署**固定顯示 `Portfolio CASH − cash floor`，並明說 cash floor 以上為
  Alpha／Beta 共用；另獨立顯示「未動用貸款額度／已借款／估計利息」，明標貸款不算自有現金。
  **不得用未解釋的斜線或 raw field name。**

## 8.1 兩條 gate 的補償控制細節

判準（「可否確定性重導」）與「放行與收緊必須同時發生」住 `AGENTS.md`；實作長這樣。

**Engine C 人工 ledger（`config/engine_c_observation_fields.json` 的 `verifiability`）：**
`mechanical` 換來的補償控制是 `append_manual_observation` 強制 value 必須是可機械比對的
JSON 數值（散文一律拒絕）——`mechanical` 的定義就是「可被重導核對」，而散文無法被 diff。
專用寫入口是 `scripts/record_mechanical_observation.py`，它**拒絕 judgment 欄位**，
那是它最重要的行為。⚠ 刻意**不驗 `source_ref` 格式**：現有觀測橫跨 SEC／AMF／HKEX／ASX／
TDnet 五種寫法，用 regex 驗會攔掉合法的法國 URD 引用（L15 記過的坑）。provenance 仍必填。
查證：`python -c "from engine_c.observation_fields import get_observation_field_registry as g;print(g().mechanical_field_names)"`

**圖 metadata 回填（`loader/source_dating.py`）四道補償控制：**
① 屬性白名單（只有 `published_at`／`retrieved_at`）；② `--basis` 必填並落地成節點屬性；
③ 寫入值另存 `published_at_backfilled`，**basis 與現值脫鉤是可偵測的**；
④ `published_at_method` 是封閉字彙，宣稱 `url_path` 的由 audit 拿當下的 `url` 重導。
另有一條真不變式：`published_at` 不得晚於 `retrieved_at`。
⚠ `loader/load_to_neo4j.py` 的 `MERGE_SOURCE_DOC` 用 `coalesce`，否則抽取 JSON 沒帶日期時
會把回填洗成 null，而**不會有任何東西報錯**。

## 8.2 由 `AGENTS.md` 搬來的現況陳述與查證（2026-09-22）

`AGENTS.md` 自 2026-09-22 起只寫目標與邊界，**指名函數、表、門檻值或 Phase 的句子一律住這裡**
（決定紀錄 G10：`docs/brainstorms/2026-09-22-graph-first-direction-decision.md`）。下列每一項在 AGENTS 都還有對應的判準句；這裡是它的落點與查證。

| 判準（住 AGENTS） | 落點／現況／查證 |
|---|---|
| 常規授權類別是封閉字彙 | SSOT `config/standing_authorization.json`；唯一 loader `engine_b/standing_authorization.py`（載入時驗封閉性）；consumer `engine_b.todo standing-go`（Daily 每天跑）。現行類別：只剩 `source_trace_review` 的派回 pq1（付費取得除外）；`decision_review` 自 2026-09-22 列 `never`（機制退役） |
| pq2 編號空間唯一 | 狀態存 `library/leads/todo_pool.json`（Git ignored、納入 private backup）；鑄 `manual` 型編號用 `todo add` |
| 「等你決定」與「等事件」分離 | `config/decision_blockers.json` 的 `resolution_mode`（`user_decision`／`awaiting_external`／`system_internal`）；使用者可用 `pending --until/--trigger` 指定等待條件，優先於自動推導。G7 之後所有等待住 Event Watch registry（`library/leads/event_watches.json`）；「語意條件」kind（`semantic_condition`）2026-09-24 Phase 1 Step 1.4 交付：thesis／讀圖的反證條件原文逐字、喚醒目標 `disproof_ref`；T0 只比對 lead 的來源宣告（`source_class=primary`、非持股申報、實體交集、時間在建立之後），**不看 triage**；醒來＝待檢，daily 預篩只標旗，判定在互動 session（`event_watch semantic-queue` → `judge`）。**誰登記（Step 1.5）**：讀圖 v2 的 `disproof[]` 在 `structure-reading --add` 後由 provider 登記（被取代／撤回的收掉；需求側客戶另登 `wake_reading`，客戶出新一手文件→該節點列進 needs_reread）；thesis 的結構化反證由 `todo sync` 對帳（sidecar hash 與 memo 相符才登記、換 memo／retire 收舊）。**判定觸及之後**：thesis 來源由同一筆 `thesis_lifecycle` 接住（`disproof_watch_ids`，go／drop 標 handled），讀圖來源列進 needs_reread——等待不消失。**到期處置（Step 1.7，amendment A3）**：每筆 expired 都落在一個處置（`expiry_resolution`）裡，心跳照數未處置的——**有自己複查週期的等待，重問併進那個複查（A7，使用者 2026-09-24 選 B）**：thesis 來源的反證到期 → 列進該 thesis 的 `thesis_lifecycle`（理由「反證等滿一輪都沒發生 N 條」），go／drop 後 `disproof.after_thesis_review` 續到下一個核查點、觸及的標 handled 並續盯；讀圖來源的 → 列進節點重讀理由。thesis 反證對帳：lifecycle 讀不到 fail closed、條件以文字認位置（relink，不以 `#n` 去重）。沒有自己複查週期的（假設型等）到期 → pq2 `watch_decision`（每個到期事件一個編號，ref_id＝`<watch_id>@<expires>`；續等＝`resolve <n> --verb pending --until <日期>`：watch 回 active、編號結案 `renewed`，**等待只住 registry、不掛 `waiting_on`**，來源已非現行拒收；`go`＝研究結論「條件已被觸及」：receipt 帶 `outcome:touched`＋研究結果（lead／report／watch，須晚於這次到期）、`--quote` 原文，假設型回 fired 交假設對照（`hypotheses verify` → consume）；report 收據內文須提到該 watch；沒觸及不得 go；過時的到期事件只准 drop（`stale_event`）；處置 kind 是封閉字彙 `EXPIRY_RESOLUTION_KINDS`；thesis 對帳的去重認任何非 consumed——到期待決的條件不重登；永不列入常規授權；R2-b 修訂 2026-09-24）；pq2 型到期 → 它指向的編號翻回球在你；讀圖型到期 → 只記處置（讀圖自己的到期重問）；**追源型（`wake_lead`）到期 → lead 的 `trace_status` 轉終局 `watch_expired`、心跳印「追源到期結案 N（今日 M）」。追源型的重問＝轉終局並計數現形，不佔 pq2（lead 留在 pq1、不占 pq2 編號）；需要人決定的等待才鑄 `watch_decision`。**這與 AGENTS「到期是重問不是丟」、G7「到期＝進 pq2 重問」字面有張力——使用者 2026-09-24 已核准（定案 #3），不要照字面修回每筆都鑄 pq2 |
| 建議區間已移除、煞車仍在 | `live_supported_range` 已隨 U7 移除；煞車自 2026-09-23 住成交路徑：`scripts/record_trade.py` 每一筆買進在寫 Sheet／trade_log 前過 `risk/hard_caps.py`（5% 單筆 NAV 上限只管 alpha；ETF 槓桿 nominal／effective cap；NAV／匯率量不到就 fail closed；dry-run 也擋；`--override --reason` 放行並把理由與 verdict 寫進事件紀錄）。舊店 `record_live_choice` 已凍結拒絕。查證：`python -m pytest -q tests/test_hard_caps.py tests/test_record_trade.py` |
| alpha 格只觀測不設目標 | 查證：`python -c "import json;print(json.load(open('config/target_allocation.json'))['sleeves']['alpha'])"` 應看到 `observed_only` |
| 資本表達層已移除 | 查證：`python -c "import json;p=json.load(open('config/investment_policy.json'));print(sorted(p['probe_lane']), p['single_position_nav_cap'])"`——`probe_lane` 不該有 `axis_ceilings` 等尺寸 cap；`single_position_nav_cap` 應仍是 0.05 |
| mechanical／judgment 兩處現行畫法 | Engine C 人工 ledger 按 `verifiability` 分（§8.1）；圖的 metadata 回填只放行既有 SourceDoc 的 `published_at`／`retrieved_at`——新的 claim／邊、`substitutability`／`sole_source`／`evidence_tier` 仍是 pq2 |
| `accounting_basis` 標籤不宣稱 authority 沒有的東西 | 只分「as reported vs 公司調整後」，字彙不改（L10），label 一律不含準則名稱 |
| 首屏的單位是句不是格 | 查證：`python -m alpha brief COHR --list` |
| 兩個 outcome 數字不得混用 | 等權報酬追蹤 `library/private/decision_lab/outcome_aggregate.json`（時序在同目錄 `.jsonl`）回答「追蹤了幾檔、跑了多久」；`measured_outcomes`（`library/private/app/state/positions.json` 的 `counters`）回答「正式結算過幾筆」 |
| beta 定投擇時已關 | 拔除 commit `6aa31de`；查證：`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"` 不應出現 `signal` |
| 部位真相是 Sheet | 下單由使用者透過 session 記進 Sheet：`scripts/record_trade.py` |
| APP 預設只綁 127.0.0.1 | 綁其他介面必須明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1` |
| 報價單位 ≠ 結算幣別 | 唯一正規化入口 `identity/currency.py` |

---

## 9. 報告產出：cohort 是研究終點

Decision cohort 就是終點層級——Watchlist／Underwrite 三級模板已於 2026-09-02 除役
（實測：升格標記在生產碼中沒有任何下游消費端）。其中有價值的兩塊各有去處：

- **variant perception 收編進 cohort 的 thesis 欄位。** 操作定義：「當前股價／估值隱含
  的假設是 X，本 thesis 認為真實情況會是 Y，催化劑 Z 會讓市場重新定價。」
  重點是**股價說什麼**，不是「多數人信什麼」。
- **Lane Memo 降級為隨叫隨到的視圖**（`thesis/generate_lane_memo.py`）：想要一頁式綜合
  時從圖＋cohort＋variant perception 渲染。它是輸出格式，不是流程的一站，不 gate 任何事。

---

## 10. v0 Schema 的具體形狀

完整欄位表、vocab、claims 格式、`sole_source` 驗證規則見
[`../schema/graph_schema.md`](../schema/graph_schema.md)。

- **node** 帶內在慢變屬性（`ramp_difficulty_intrinsic`；`concentration_score` 為衍生值非手填）
- **edge** 帶關係型屬性（`substitutability`、`sole_source`、`structural_lead_time_weeks`、
  `ramp_execution`）
- `confidence` 只在不同 `origin_event` 之間累加（同一法說會多份摘要 ＝ 一個 origin_event）
- `consensus_coverage` / 股價 / 財務數字 → **不進圖**，進 Engine C

**三層 symbol 不可混用**（以 Sivers 為例）：研究行情是瑞典主掛牌 `SIVE.ST`（SEK）；
Google Sheet／execution authority 是 `FRA:2DG`（EUR）；Yahoo provider syntax 由
`identity/execution.py` 正規化成 `2DG.F`。快照對外仍回 canonical `FRA:2DG`。

---

## 11. 這份文件不涵蓋什麼

| 要找什麼 | 去哪 |
|---|---|
| 「我可以／不可以做什麼」 | [`../AGENTS.md`](../AGENTS.md) |
| 「這個詞是什麼意思」 | [`../CONCEPTS.md`](../CONCEPTS.md) |
| 「這件事怎麼跑」 | [`OPERATIONS.md`](OPERATIONS.md) |
| 「接下來要做什麼」 | [`ROADMAP.md`](ROADMAP.md) |
| 某個封閉字彙住哪、能不能擴充 | [`solutions/architecture-patterns/closed-vocabulary-registry.md`](solutions/architecture-patterns/closed-vocabulary-registry.md) |
| 36 筆歷史事故 → 六條 invariant → executable protection | [`refactor/historical-failure-matrix.md`](refactor/historical-failure-matrix.md) |
