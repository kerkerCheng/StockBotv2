# StockBotv2 — 專案記憶 (Project Memory)

> **本檔回答一個問題：我可以／不可以做什麼？**
> 只放**會約束行為的規則**——invariant、authority 邊界、人工 gate、lesson 的判準句。
> 任何 session 在此資料夾開工前先讀本檔。

**定位一句話：** 研究輸入（結構／證據／財務）＋ 決策責任 → 有根據且可控的投資決策。
**系統不給部位尺寸**——買多少、什麼時候買由使用者在買入前自行判斷，並自行手動下單。
本機單人自用，使用者會寫 Python、碰過 API。

## 本檔的角色與另外四份

| 檔案 | 回答的問句 | 什麼時候讀 |
|---|---|---|
| **`AGENTS.md`**（本檔） | **我可以／不可以做什麼？** | 每個 session 開工前 |
| [`CONCEPTS.md`](CONCEPTS.md) | 這個詞是什麼意思？ | 遇到不懂的詞 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 系統長什麼樣、為什麼這樣切？ | 新增 module／動邊界前 |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | 這件事怎麼跑？ | 要實際執行操作時 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 接下來要做什麼？ | 規劃或決定下一步時 |

**判準：這句話改變的是我的行為、我的用詞、我的結構、我的按鍵、還是我的排程？**
最實用的一條分野：**OPERATIONS 被改壞 → 跑不起來；本檔被改壞 → 跑起來了，但做錯事。**
另有 [`docs/refactor/`](docs/refactor/)（設計文件；**動 contracts 前必讀
[`historical-failure-matrix.md`](docs/refactor/historical-failure-matrix.md)**）與
[`docs/archive/`](docs/archive/)（交付歷史逐字封存）。
⚠ 本檔每個 session 完整載入，所以每加一段都在花掉未來每一次執行的 context。

## 工作語言（繁體中文）

**與使用者的所有溝通、以及實作過程本身的敘述，一律用繁體中文——不只是最終答案，過程也是。**

- **使用者輸入可能是簡體（語音輸入所致），這不改變工作語言。** 回覆一律維持繁體，
  不要跟著切簡體、也不要因輸入是簡體就以為要改語言。
- **涵蓋：** 對話回覆、工具呼叫之間的狀態更新、步驟說明、分析、計畫、思考敘述；
  Task subject／description、commit message、PR 說明、plan 檔、`docs/` 報告；
  skill 最終輸出（含 last-30-days 等）。
- **程式碼：** 新寫的註解／docstring 跟隨該檔既有語言慣例；面向本專案的新說明優先中文。
- **維持原文、不強行翻譯：** 程式識別符、既定英文技術術語（going concern、sole_source、
  evidence tier、backlog…）、第三方 API 欄位與字串、檔名／路徑、一手文件的逐字 quote。

判準：語言規範針對「溝通與敘述」，不是把程式碼或逐字證據中文化。
若發現實作過程飄成英文，視為違反本規範，切回中文。

---

# 憲法

## 五條 authority separation

> **使用者定案（2026-09-03）：不要把「Engine A/B/C/D 四引擎架構本身」當成不可變憲法。**
> 引擎命名是現行實現方式（見 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)）；
> 不可變的是權責分離。

| # | Authority | 擁有什麼真相 | 可變性 |
|---|---|---|---|
| **A1** | 結構／證據 truth：實體、關係、claim、provenance、逐字引文 | 可重建 |
| **A2** | 財務觀測：帶時戳的財務／市場／共識 | projection 可重建；人工 ledger 只能 append |
| **A3** | 研究判斷／Alpha：「我們相信什麼、憑什麼、什麼會推翻它」 | **可重算** |
| **A4** | Portfolio／Risk：目前曝險、目標配置、硬上限 | 可重算 |
| **A5** | 資本決策／問責：「當時憑什麼決定、使用者選了什麼、後來對不對」 | **append-only，Git 救不回** |

**五條分離規則：**

1. **A1 不含時變數字。** 股價、估值、共識、未來 EPS、capex 推估**永不入圖**（L4）。
2. **A3 不得成為第二個 A1／A2 current-state authority。** research provider 是唯讀 view，
   不落地任何快取表。
3. **A3 可重算、A5 不可重算。** 這是 `ResearchContext` 與 `DecisionContext` 必須分開的
   全部理由（L10 的直接推論）。
4. **A4 不形成 view，A3 不算尺寸。** view → target exposure → hard limits 是單向的。
5. **A5 是唯一能授權資本的地方**，且 live 永遠 100% 人工。
   **research automation ≠ capital authority。**

**判別問法：** 一條規則若在「換掉 Neo4j」「把 Engine D 拆成三個 package」之後仍然成立，
它屬於這五條；否則它是 CURRENT_ARCHITECTURE，該住 ARCHITECTURE.md。

## 六條 hard invariant

出自 [`historical-failure-matrix.md`](docs/refactor/historical-failure-matrix.md) §2，
全程適用。查證：`python -m audit invariants`。

| | Invariant | 一句話 |
|---|---|---|
| **INV-1** | IDENTITY | ticker 不是 entity identity；解析走 registry，不猜 |
| **INV-2** | LIFECYCLE | 每個 active object 答得出五問；**每個等待都必須有到期** |
| **INV-3** | NO SILENT DROP | 「查不到了」不是合法 lifecycle；每個 filter 都能報 input／accepted／filtered／reasons |
| **INV-4** | QUEUE LIVENESS | producer 指得出 consumer |
| **INV-5** | MEASURED GATE | 未量測的機制不得享有默認信任 |
| **INV-6** | POINT-IN-TIME & PROVENANCE | 答不出「T 時刻我知道什麼」就明確拒絕，不得靜默回傳當前值 |

## 四個人工 gate（不因任何理由放寬）

**graph admission ／ Engine C 判讀寫入 ／ thesis mutation ／ live choice-fill。**

`go` 一律只授權該項自己的 action type。研究 `go` 不含入圖、入圖 `go` 不含 thesis
mutation、**任何 `go` 都不含 live**。

⚠ **gate 攔的是「新的知識主張」，不是「這個欄位在哪張表／在不在圖裡」。**
判準沿用 L10：**「這筆資料今天重新取一次拿得回來嗎？」**
`mechanical`（值是結構化數字、指得出一手來源的確切位置、任何人重讀都得到同一個數）
→ **不需 pq2**；`judgment`（需要決定「這算不算」「這是什麼意思」）→ **維持 pq2**，
**未宣告一律 fail safe 當 judgment**。今天有兩處這樣畫：Engine C 人工 ledger 按
`verifiability` 分；圖的 metadata 回填只放行既有 SourceDoc 的 `published_at`／
`retrieved_at`（**新的 claim／邊、`substitutability`／`sole_source`／`evidence_tier`
仍是 pq2**）。

**放行與收緊必須同時發生**（L15）：拿掉一道人工閘門就必須在同一個 change 補上**可機械
驗證**的補償控制，否則那條走廊就是後門。補償控制清單見
[`ARCHITECTURE.md`](docs/ARCHITECTURE.md) §8.1。
⚠ 其中一條反向禁令屬本檔：**不得用 ingest／retrieval 日期冒充 `published_at`**——
那會讓所有東西看起來都是最近才發表的，回測會在每個歷史時點看到全部證據。
推不出日期的**留 null 並列進報告**（L11-5）。
查證：`python -m audit invariants --only PointInTime`

# 授權與決策

## 授權介面唯一：pq2 編號 ＋ `go`

**所有真正需要使用者決策的事只有一個編號空間**——prepared RA 入圖核准、決策複查、
thesis 到期、Sheet-only 持股、手動 authority。Raw／triaged leads 留在 pq1 由 routine
自動研究，不占 pq2 編號；否則同一題會在研究前與入圖前問兩次。
編號首次進池後直到 resolve 才釋放；狀態存 tracked `library/leads/todo_pool.json`。

**授權載體唯一（2026-08-30 使用者定案，取代所有口頭授權）：** 任何需要核准的**研究與
authority 動作**——研究工程、終局 cohort 的重建、sub 補值這類 graph-write 研究——
**一律先以 `todo add` 鑄成 `manual` 型 pq2 編號再請求核准**。口頭「可以做」不構成授權
管道；收尾摘要只得引用編號，不得出現「口頭指示即可」類措辭。收集端不鑄的號，提案端自己鑄。
**Onboard 也走 pq2**：新公司 registry 增列＋首批 extraction 打包成 prepared RA 取
`ra_admission` 編號（packet 內必含 L8 來源清單）；統一的是核准的**載體**，不是時機。

**`go` 的語意＝推進到下一個人工 gate。** 不是「把這題排進佇列」，是「授權你往下走，
直到撞上我下一個需要授權的 gate」。排入 pq1、checkpoint、reassess 都只是路上的簿記；
**互動 session 收到 `go` 就在當次把研究做到產出 packet（新 pq2 編號）或誠實 park 為止**，
不得 dispatch 完就停。無人值守排程受 budget cap 約束可以只做一段，但未完成的必須留在
佇列由下一個執行者接續，**不得把「已排入」回報成「已推進」**（L13）。

**使用者主動指示＝已授權。** 使用者口頭／文字請求的工作，鑄號只為稽核（受理時即以 `go`
resolve，receipt 註明語境），**不得回頭再請求一次 `go`**——重複要核准是介面失敗。
`go` 請求流程只適用於**系統主動提案**的項目。四個 authority gate 不因此放寬。

**⚠ 系統開發項不走 pq2，唯一載體是 [`ROADMAP.md`](docs/ROADMAP.md)（2026-08-31 定案）。**
判準一句話：**`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？**
前者是研究（pq2），後者是開發（ROADMAP）。例：「補某條邊的 substitutability」改變圖裡的
事實＝研究；「改 `rank_bottlenecks` 的排序鍵」改變系統行為＝開發。
理由不是分類潔癖，是**兩種東西的決策資訊完全不同**：研究項要「證據夠不夠、授權到哪」，
一行決策行就夠；開發項要「這會讓哪個數字變、驗收條件、與其他開發項的相對優先序」
（L14），而那些只有在 ROADMAP 的表格裡排得出來。系統主動提出的開發構想寫進 ROADMAP
待排程，**不主動要求 `go`**。

### 「等你決定」與「等事件」必須分離

池子同時裝著兩種性質不同的東西，混在一起會讓訊噪比降到約 1:1（歷來 76 個編號有 31 個被
drop）。`config/decision_blockers.json` 的 `resolution_mode` 是分類判準：
`user_decision`／`awaiting_external`／`system_internal`。
保守規則——**只要有一個 blocker 需要人決定，整個項目就留在決策佇列**，寧可多問也不要
安靜藏起來。使用者可用 `pending --until/--trigger` 明確指定等待條件，優先於自動推導。

**人工判讀不等於外部事件（2026-08-15 定案）：** 若現有公開資料已可開始 bounded research、
source-trace、assessment 或 manual observation proposal，`go` 的決定是「是否啟動這份
研究」，項目必須留在 `user_decision`；**不能因 next step 含「人工填入／人工判讀」就藏進
`awaiting_external`**。只有世界必須先產生新 filing、掛牌或到達既定日期才屬 `awaiting_external`。

### 建議只由 pool ground truth 導出＋必過 L14（2026-08-30 定案）

事發：2026-08-30 weekly 對八個編號建議 `drop`，聲稱「來源已停止產出」——實測
`source_cleared` 是 **0/8**，其中兩項是等事件、一項是使用者明示 defer；同晨 daily 又對
其中三項建議 `go`，兩份排程直接互相矛盾。

1. **推薦 `go` 前必須答得出「go 會讓哪個數字變」**（L14）。receipt 已判定 bounded
   research 解不了的（需使用者 scope 決策、需世界先發生某事），不得推薦 `go`——改建議
   `pending --trigger`，或把真正要的 scope 問題直接問出來。
2. **推薦 `drop` 前必須查 pool ground truth**（`source_cleared` 實值＋`waiting_on`＋
   `deferred_at`）並附查證命令。collector 仍會重新推導的項目 drop 只會換號重生
   （`sheet_only` [18]-[33]→[46]-[60] 先例）——正確做法是修 collector 端分類。
3. **分工：weekly 只發現、不處置。** 週報至多列「疑似 stale——待互動 session 以 ground
   truth 驗證」；處置建議只由讀得到 pool 現值的 daily／互動 session 給出。

**收尾建議摘要是義務：** 每個研究段落、daily／weekly 報告與較長的互動回覆，結尾必附
「建議摘要」——各列編號＋一句理由，**最後一行單獨給可直接複製的批次指令**
（如 `252 253 256 257 go 255 pending`）。呈現規格見
[`skills/daily-brief/SKILL.md`](skills/daily-brief/SKILL.md)。

**待核准內容的呈現契約全文住 [`skills/daily-brief/SKILL.md`](skills/daily-brief/SKILL.md)**
——決策行、密度五欄、**面向使用者的措辭層**、四段分段軸都在那裡（2026-09-04 搬移）。本檔只留一條不可退讓的判準：
**不得假設使用者能從 `co:*` ID 或內部術語自行還原主詞**，且決策行的「不含」欄必須逐項
寫出最相鄰的未授權動作——否則使用者要靠記憶區分授權邊界，而那正是這些 gate 存在的理由。

## 資本與風控

**Numeric SSOT：** `config/investment_policy.json` 與 `config/beta_policy.json`
（目標配置比例另在 `config/target_allocation.json`，它是**錨點不是 gate**）。
只有 **ETF 槓桿 cap 與 5% 單筆上限**是硬擋，其餘曝險只記錄／警告。
使用者仍可走 prepared `live_override` 留下 exact action ＋ reason receipt；系統不自動下單。

⚠ `live_supported_range` 已隨 U7 移除，但**硬擋本身仍在**——`store.record_live_choice`
對每一筆非零 live 選擇仍擋這三碼，外加凍結快照七天時效與「部位量不到就 fail closed」。
**移除的是系統給的建議區間，不是煞車。**

**共同可投資現金池只有一條：** `Portfolio CASH − cash floor`，供 Alpha／Beta 共用。
不扣 operating reserve、alpha reserve 或 planned outflows，沒有 Sheet／household 雙 range。
**cash floor 不承擔 sleeve allocation**；cash floor authority 失效時 fail closed，
不回退到百分比 reserve。

**兩個槓桿指標不得混用：** `nominal_weight` 是「投入槓桿 ETF 的資金占 NAV」
（12.5%／20% warning/cap）；`effective_weight` 是乘上 2x／3x 後的「換算槓桿曝險」
（30%／40% warning/cap）。面向使用者不得把前者寫成模糊的「名目槓桿」。

**Capital Authority：** 私人 Google Sheet 只保留 `cash_floor` 與 `credit_facility` 兩種
record；日常 credential scope 只有 `spreadsheets.readonly`。貸款額度、已借款、利率、
計息方式、期限與還本方式獨立保存；**未動用額度不算 NAV／cash／allocation**。
每次提款、標的與 tranche 都是 explicit manual review，**「高信心」不構成 machine permission**。

**曝險邊界：** Sheet `bucket=CASH` 列計入 NAV 但不計曝險。未知非現金持股按 unlevered
direct issuer ＋ alpha exposure 誠實降級，不因缺 mapping 阻擋。`issuer_loads` 只代表
policy 已登記的 ownership look-through，輸出必標 `partial`；coverage 為 partial 時，
人類輸出一律寫「已知至少 X%」，**不得把已建模部分冒充完整曝險**。
Engine A 上游依賴不可混成 issuer ownership。**既有 frozen decision 不回寫。**

**退休貸款資本目標（2026-07-28 定案）：** 使用者約 30 歲、退休目標約 60 歲；可長抱至到期
的貸款資本以約 30 年後 `retirement_net_terminal_wealth` 最大化為方向，不以降低中途回撤為
第一目標。契約為利息按月支付、期間不攤還本金、到期一次還本、允許投資用途。
broad unlevered beta 是主要候選；daily 3x 可投資但維持衛星定位，exact review 必須扣除
借款成本與到期本金比較退休淨終值，**月息若需靠賣出 beta 支付則該 tranche 不成立**。

---

# 呈現契約

## Alpha 呈現契約：候選＋事件追蹤，不是部位尺寸

**系統只負責兩件使用者自己做不動的事：哪些標的值得看、它們有什麼新事件。**
買多少、什麼時候買由使用者決定。

理由是實測而非偏好（**以下為 2026-08-15／08-28 定案當時的實測值，非現況**）：
6 個 ELIGIBLE cohort 每檔 target 固定 0.1% NAV、合計 0.6%（每檔約 30 美元），
而該尺寸來自當時從未被 outcome 驗證的 `axis_ceiling`（`measured_outcomes` 0/8）。
2026-08-28 再測：21 個 operational cohort 有 20 個 `live_supported_range` 是 `[0,0]`，
排序第一名 COHR 的三個資本風控**沒有一個 binding**，唯一 binding 的是 `weakest_axis`
的 0.002——**一個從未被驗證的機制在決定資本**，正是 L14 明文禁止的事。
使用者的原話：「繞了這麼久只得到我很早就看到的幾間公司、都等於 0.2%，我會不知道我到底
做了什麼」——**產出若無法讓人分辨做了什麼與沒做，它就不算產出**。

**因此資本表達層已整組移除：** `live_supported_range`、`axis_ceiling`、`paper_target`、
probe cap 與四動作（`NO_ACTION`／`REVIEW`／`TRADE`／`HEDGE`）都不再產生。
系統終點是**瓶頸度排序**，注意力狀態只剩 `MONITOR`／`REVIEW`。
**outcome 量測改為等權重報酬追蹤**：只記「哪天推薦了這檔、當時股價、之後報酬率」，
不含部位大小或 NAV 佔比。

> **查證（別相信這段文字，跑一次）：**
> `python -c "import json;p=json.load(open('config/investment_policy.json'));print(sorted(p['probe_lane']), p['single_position_nav_cap'])"`
> `probe_lane` 不該再有 `axis_ceilings`／`probe_book_nav_cap`／`single_probe_nav_cap`／
> `live_adv_fraction_cap`；`single_position_nav_cap` 應仍是 0.05。

**真正的風控完全不變。** 拿掉的是憑空的建議尺寸，不是煞車；live choice／fill 仍然
100% 人工，系統不連 broker。**NAV 比例呈現是純呈現、零門檻**——不判斷好壞、不告警、
不阻擋任何動作。

### 「哪些標的值得看」的交付要求（違反即視為未完成）

判準四維度（瓶頸地位／需求錨點／客戶端資本承諾／標的純度）住
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)；這裡是對輸出的硬要求。

- 必須輸出**有序清單與明確的首選**，並直接回答「現在要加碼哪一檔」。
- 若因證據不足而無法排序，必須指出**缺哪一項具體證據**，不得以「未經 outcome 驗證」搪塞。
- **「outcome 還沒驗證」不是拒絕排序的理由，不論當下比值是多少。** 不出手就沒有 outcome，
  沒 outcome 就不敢排序，是死循環；L14 要求的是「不得讓未量測機制**決定資本尺寸**」，
  不是「不得表達研究判斷」。判斷與尺寸是兩件事，尺寸仍然不給。
  ⚠ 這條刻意**不寫死比值**——把判準綁在會變的數字上，數字一變讀者就以為判準失效。
- 排序是**研究判斷**，必須明標它不是回測或統計勝率，並附各候選的 disproof。
- 必須點明候選之間的**相關性**：本圖標的高度集中於 AI 光互連，列出 N 檔不等於 N 個獨立
  機會。全買是同一賭注下 N 次，不是分散。

**進場靠判斷，出場靠 disproof。** 反證的用途是決定何時承認判斷錯了，不是進場的前置條件；
混用會產生「永遠不出手、只累積反證」的無效產出。

### ⚠ 已知會失焦的指標——不得單獨用作瓶頸性證據

- **`evidence` 等級**：最高級必須靠研究找到客戶端文件才拿得到，它是**研究深度的函數**。
- **同一 chokepoint 的供應商計數**：反映的是**我們研究了幾家**，不是世界上有幾家。
- **`documents` 計數**：`bottleneck.py` 已排除，否則分數會變成「我們讀了幾份文件」。

**判別法：這個指標會隨我們多讀一份文件而單調上升嗎？** 會 → 它測的是研究量。

**唯一排序權威是 `query/bottleneck.py::rank_bottlenecks()`。** alpha 排序必須**消費**它，
不得重算結構分，也不得繞過它自建第二套結構評分。（`axis_ceiling`／paper target 曾被誤當
排序代理，它們是資本閘門不是選股判準；`research_status` 是研究完整度，也不得拿來排序。）

## Beta 呈現契約：只回答「距目標多遠」與「現在在什麼水位」

使用者的實際行為是定期投入而非擇時，每次真正要決定的只有「這次投哪一檔」。
**呈現層不得以任何名義復刻擇時語言**（今天是否投入、本輪上限、節奏、可評估／暫停新增）。

- **目標配置比例的 `band` 是容忍區間不是 gate**——落在區間內即視為到位、沒有偏好。
  **再平衡只用新投入的錢往低於目標的格子補，不賣出**；此表只給差距，**不給金額、
  不排名、不產生部位尺寸**。貸款 tranche 不適用配置建議。
- **相對水位只呈現、不參與排序、不換算金額**，且必須寫明「長期上漲的標的多數時間落在
  高位是正確資訊，不是該等回檔的訊號」（2026-07-31 回測：等回檔對 30 年終值是負貢獻）。
  **一旦有人拿它排序或調整尺寸，它就變回訊號。**
- **燈號只表達行情資料狀態，不表達投入建議。** 舊語意（可評估／冷卻／暫停新增）
  已於 2026-08-29 明文**廢止**——安靜消失擋不住下次回填，所以廢止必須寫出來。
- **行情表是每日心跳，不受今日是否投入影響**——即使所有 sleeve 都到位、今天沒有任何
  配置缺口，逐檔表仍**不得省略**，且每列必須明示商品自身的**最新完整交易日**。
- **兩條相關性警告每天都要講一次，不因每天一樣而省略：**（a）**alpha 與 beta 是同一個
  賭注**——兩個 sleeve 的目標比例分開寫**不代表**它們是兩個獨立風險來源；
  （b）**TSMC look-through 約 28%**，高於 `issuer_concentration_warning` 0.25，
  且系統算不出精確值（`issuer_loads` 覆蓋恆為 `partial`）。

呈現細節（欄位、燈號文字、台股 freshness、槓桿商品序列）見
[`ARCHITECTURE.md`](docs/ARCHITECTURE.md) §8。

## 技術訊號的地位（2026-08-01 實測後定案；2026-08-29 整組移除）

**實測記錄（歷史，不因後續移除而改寫，任何改寫都不得刪減它）：** 三次實測全部失敗——
以訊號 gate 現金投入使終值**輸給無腦定投 8.5%**（QQQ 91.5%、SOXX 91.9%）；訊號調節借款
提取**無可測得效果**；訊號決定投給哪個標的**輸給固定單押最佳標的 22%**，且三分之一時間
買進 CAGR 僅 7.2% 的弱標的——**「買跌最深的」會系統性把錢導向長期較弱的資產**。
`stretched_above_sma200` 同為未實測的推論。完整證據見
[`2026-07-31-leverage-glide-path-requirements.md`](docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md)。

**因此訊號機制已整組移除（commit `6aa31de`），不是降級使用。** RSI／MACD／`sma_50_slope`／
tier／pace／`campaign_budget_fraction_by_sleeve`／三態系統動作／「本輪可評估上限」這個概念
全部拔除。**這些字彙不得以任何名義回到文件或輸出**——包括改名成「熱度」「節奏」，
或借用「水位」之名讓動能指標重新參與排序／尺寸。
查證：`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"`
不應出現 `signal`。

**須區分量測、訊號與脈絡：** 總曝險倍數、歸零門檻、追繳門檻、利息覆蓋屬**量測**，
有價值且應強化；RSI／MACD／tier／pace 屬**訊號**，三次受測皆未通過。
位置指標是**呈現用的脈絡**——既不是量測也不是訊號，它不決定任何金額、不參與任何排序；
**一旦有人拿它排序或調整尺寸，它就變回訊號**，適用同一條實測紀律。

---

# 協作與邊界

- **專案記憶唯一權威：** 本檔。`CLAUDE.md` 只用 `@AGENTS.md` 匯入，不再複製內容。
  **研究 skill 唯一權威：** `skills/<name>/SKILL.md`。
- **Local-first（2026-07-26 定案）：** 未特別寫 `claude.ai`／cloud 時，文件中的「Claude」
  一律指**本機 Claude Code session**。**cloud session＋MCP 是備援**，不要求等權。
  新核心必須能在完全沒有 MCP 的情況下運作；若 MCP 相容性與新核心架構衝突，**優先選新核心**。
- **Provider-neutral 執行契約（2026-07-29 定案）：** 本機 Codex 與本機 Claude Code 都是可
  互換 executor。任一 agent 只有在使用者對 **exact pq2 item** 明確核准後才可走完整
  type-aware 動作；**權限與完成狀態綁 action type、underlying authority 與 receipt，
  不綁 provider**。模型 recommendation／session transcript／「使用者通常會同意」都不能自我授權。
- **同一 working tree 只讓一個 agent 寫入。** 兩邊同時工作必須用不同 worktree／branch；
  **排程與互動 session 也算兩個 writer，不能重疊。**
- **Session memory 不是 authority。** Codex `memory.md`、task context 與 Claude Code
  transcript 都只是 disposable advisory cache。核准後必須先完成 type-aware 動作並留下
  underlying receipt，最後才寫 `todo_pool.log`／resolution；**未寫 authority 的「已 go」
  不得被另一個 agent 視為完成。**
- **任何 unattended routine 的 executable surface 變更，都必須在同一個 change 完成
  sandbox impact review**（五步見 OPERATIONS）。**不得用 broad permission 掩蓋整合缺口**——
  只放行能由既有人工 gate、action type 與 receipt 約束的最窄 command prefix；
  縮不到可安全 allowlist 的入口就保留互動 approval。
- **subagent 委派預設關閉、每次明確 opt-in。** 不得因工作看似機械、便宜或適合平行化而
  自行派工——每次 spawn 都是冷啟動，要重新推導主代理已經有的 context。
  **subagent 的回傳只是 review packet，不是 authority**；不得委派任何寫入、evidence
  tier 升級、graph admission、pq2 核准／resolve、thesis mutation、資本配置、commit／push。
  同一 working tree 維持主代理為唯一 writer；真要 writing subagent 必須另建 worktree／
  branch 並指定唯一 owner。
  ⚠ 專用的 `luna-reviewer` skill 已於 2026-09-04 退役（實測 34 天零使用，且各 harness
  原生的 subagent 已可指定便宜模型＋唯讀）；**上面這幾條授權邊界與它無關，照舊適用**。
- **Push 是常規動作**，session 收尾把 master push 到 origin，不需逐次確認；
  push 前 sanity check：`git ls-files library/private` 應為空。程序見 OPERATIONS。
- **通知不是 authority。** Daily Brief 的 outbound 通知不接受 Discord `go`／交易／入圖
  指令，不寫任何 authority。**Canonical Brief 只有一份**——task 最終回覆與 publisher 必須
  使用同一份最終 Markdown，publisher 完成後不得再另寫精簡版或刪除 section。
  發送失敗是 best-effort 狀態，**不得阻斷**。
- **不建立與待辦池競爭的第二個狀態源。** daily brief 不留檔（稽核價值由待辦池 log ＋
  leads 狀態機 ＋ Decision Store 承擔）；weekly report 留檔 `docs/reports/`，
  但它是 point-in-time 歷史報告，**不是 current-state truth**。
- **一手來源優先（來源登記表）。** 通用搜尋只配 LLM 品質評分 gate，用在第三層；
  機器可執行的路由與未果處置唯一權威是 [`skills/source-trace/SKILL.md`](skills/source-trace/SKILL.md)。
  **出投資建議前必看的核驗清單五項：** 客戶集中度、毛利率／產能利用率、backlog／營收結構、
  稀釋、估值壓力。

## ⚠ 現況數字會過期，判準不會（2026-08-19 定案）

**任何「目前 N 筆」「至今 0／8」「從未發生過」型陳述，在文件裡都是會腐壞的快照。**
判準寫進文件是對的（它不隨時間變），**現況數字寫進文件是錯的**——它會在某天悄悄變成假的，
而讀者無從察覺。

實測代價（2026-08-19 一天內兩次）：① ROADMAP 寫著「`live_choices` 仍為 0 筆——live 這條
路徑從未被走過」，agent 直接引用它告訴使用者，但使用者前一天就走完了全鏈；② ROADMAP 寫著
`commercial_maturity` 的缺口是「缺人去讀年報」，agent 差點照做，實測後發現 7 個積壓沒有
一個是讀年報能解的。

1. 政策檔與 ROADMAP 陳述現況時，**必須附上查證命令或 authority 路徑**，讓讀者能一行驗證。
2. **引用自家文件的現況陳述前，先跑那條查證命令。** 這是 L11 第 2 點的直接應用；
   兩次事故都是 30 秒內可否證。
3. Lesson 的「事發」段落是**歷史記錄**，其中的數字是當時實測值，**不因現況改變而更新**；
   但必須帶事發日期，避免被誤讀成現況。
4. 數字若確實需要常駐可見，**做成會自己出現的計數器**，不要靠文件段落。

**同理適用於任何 repo 裡已有結構化來源的清單：清單會腐壞，判準不會。**
曾在本檔維護 skill 清單，新增 `luna-reviewer` 後沒同步，表上長期少一個（2026-08-19 發現）。

---

# Schema 快速記憶

完整欄位表與 vocab 見 [`schema/graph_schema.md`](schema/graph_schema.md)；結構說明見
[`ARCHITECTURE.md`](docs/ARCHITECTURE.md)。設計原則：**表的「形狀」鎖死，字彙留鬆**（L2）；
屬性按 L4 三分歸位。

- **圖公司 ID（`co:*`）不要憑公司名猜。** 唯一權威是 `config/company_identity.json`。
  例：Sivers 是 `co:sivers_semiconductors`，不是 `co:sivers`（2026-07-21 週掃即因猜 ID
  未命中而漏掉比對）。ID 未命中時要區分「ID 沒解析對」與「圖中真無此公司」，**不能默默跳過**。
- **報價單位 ≠ 結算幣別（2026-08-05 定案）。** 交易所報價單位（`GBp`／`ILA`／`ZAc`）是
  minor unit，不是 ISO-4217 結算幣別；唯一正規化入口是 `identity/currency.py`。
  未登記且非 ISO 形式一律 fail closed，**不得為了通過驗證把報價單位改寫成 ISO code——
  價格會差 100 倍。**
- `confidence` 只在不同 `origin_event` 之間累加（同一法說會多份摘要 ＝ 一個 origin_event）。
- `sole_source` 需**客戶端或第三方**印證；供應商自稱 → `verified_by_absence`（弱，≤0.5）。
- **股價／估值／共識／財務數字不進圖**，進 Engine C（A1 不含時變數字）。
- **每份 thesis／claim 必帶 `disproof_condition`**，且必須附核查頻率與觸發後 48 小時的
  動作（L7）。**variant perception 是必填**，操作定義與生命週期見 ARCHITECTURE。

---

# 踩過的坑 / 通用判準 (Lessons)

> **格式：** 每條先給 **Learned invariant**（不變的那一句）、再給 **事發**（歷史記錄，
> 帶日期，不因現況改變而更新）、最後標 **Implementation 可改？**
>
> **引用慣例：** 使用者記不住 L 編號。任何回覆或報告提到 L1–L16 時，該編號**第一次出現
> 必須括號備註一句是哪條判準**，例如「L7（disproof 要附核查頻率＋48h 觸發動作）」。
> 同一份輸出內重複出現同編號可不再備註。
>
> L1–L3、L5 是專案早期的選型與動工判準，架構已定案，此處只留判準句
> （2026-08-19 壓縮，編號原地保留供交叉引用；事發經過見 git history）。

### L1 — 不要為了「少裝一個系統」而用不成熟工具去做專案核心
**Invariant：** 核心元件優化**能力、生態成熟度、可觀測性**，不優化「系統數量」——後者在
本機／單人情境下很廉價。需要人工 review 的資料結構，**視覺化是硬需求**；polyglot 對
「質化知識＋量化數字」雙軌是正確架構，別拿「統一技術棧」當反射性理由。
**Implementation：** Neo4j｜**可改？NO**（選型已鎖，且理由本身是 invariant）。

### L2 — 不要在動工前追求「完美 schema」
**Invariant：**「現在搞錯、以後要搬全部資料才能修」的才現在想清楚（**表的形狀**）；
「以後加一列設定就能補」的（**字彙**）直接動工讓資料教你。
**Implementation：** `schema/vocab.json`｜**可改？YES**。

### L3 — 別讓 DB / 框架的選型卡住垂直切片
**Invariant：** 抽取層輸出 DB 無關 JSON，選型隨時可換。流程穩了再包框架。
**Implementation：** `extract.py` → `loader/`｜**可改？YES**。

### L4 — 屬性歸位：物理 / 關係 / 時變 三分（schema 建模鐵律）
**Invariant — 三連問決定一個屬性放哪：**
① **換掉關係另一端，值會變嗎？** 不變 → node；會變 → edge。
② **值會隨時間變嗎？** 會 → 不是靜態圖屬性，是**帶時戳的觀測**（進 Engine C，不進圖）。
③ **講的是物理現實，還是證據強度／市場認知？** 後兩者 → metadata 或市場狀態，不是實體屬性。
結論：品類集中度／內在量產難度＝node；可替代性／sole-source／lead-time／供應商 ramp
執行力＝edge；需求證據強度＝掛在主張上的 metadata；市場擁擠度＝時變觀測。
**一句話：瓶頸的 alpha 大半在邊上，不在點上。**
**事發：** 評估 chokepoint-atlas 的 `ComponentNode` 五個瓶頸欄位——它們長得像同類，
實際分屬三種物件；作者全塞進一個 node，是因為他的 skill 無狀態、不在乎持久化。
**Implementation：** node/edge attributes ＋ Engine C 時變觀測｜**可改？NO**——新架構的
`ScarcityInputs`／`FundamentalsSnapshot` 分野直接繼承它。

### L5 — chokepoint-atlas / serenity-skill 是方法論藍圖，不是相依套件
**Invariant：** 抄骨架（stack 分層、role 分類、證據四階、output-formats），不裝套件、
不綁相依。⚠ 它是**單一 lens**（偏小市值瓶頸獵手）——當眾多視角之一，
**別讓系統世界觀被綁死**。
**Implementation：** 無相依套件｜**可改？YES**。

### L6 — 第一次真實抽取撞出的 schema/pipeline gap
**Invariant：** ① Schema gap 只有真實資料撞上去才會現形（L2 再次驗證）。
② 局部 ID 在單文件內沒問題，**跨文件 MERGE 後會命名空間衝突**。
③ **具體型號／公司名必須在 quote 裡逐字出現**——LLM 從類別詞推斷出具體實體是最常見的
幻覺型態，review 時重點抽查這一項。
**事發：** Coherent 法說 CPO 段落，quote 只說「data center interconnect 需求強」，
LLM 自己推出 ZR/ZR+ 節點。四個洞中 Gap 1–3 已於 2026-08-14 修復驗證，**Gap 4 仍然活著**。
**Implementation：** `prompts/extract_system.md`、loader 加 doc_id 前綴｜
**可改？YES（實作）／NO（逐字規則）**。

### L7 — Thesis 生命週期：`disproof_condition` 是欄位，不是流程
**Invariant：** 光是填 `disproof_condition` 不夠。**每條 disproof 必須附「核查頻率」與
「觸發後 48 小時內要做什麼」**，否則是一個永遠不會響的火警警報。
生命週期：`active`（定期核查，建議每季）→ `watch`（leading indicator 朝 disproof 移動）
→ `review_required`（條件已觸發，強制 review）→ `retired`（確認失效，出場並記錄推翻原因）
或 `revised`（修正後重新 `active` 並更新 disproof）。
**Implementation：** `thesis/lifecycle.json`＋`catalyst_watch.py`｜
**可改？YES（實作）／NO（三件套要求，已由 `DisproofCondition` 型別強制）**。

### L8 — 自我報告確認偏誤：供應商的法說會不能作為「自己是瓶頸」的獨立佐證
**Invariant：**
① **來源獨立性檢查（多文件入圖前）：** 文件選源清單中至少 **3 個不同 `origin_entity`**。
「被分析的公司自己的文件」只能算佐證，不能算主要確認來源。
② **`sole_source` 確認來源必須是客戶端或第三方。** 供應商自稱 → `verified_by_absence`
（弱）；客戶在法說會說「目前只有一個供應商」、或第三方產業報告列供應商名單只有該公司
→ 才能考慮 `verified_by_search`（強）。
③ **圖裡的交叉驗證：** 某條 `sole_source=true` 的邊，其所有 source 的 `origin_entity`
全是同一家供應商時，標 `sole_source_evidence_quality: weak`。
**事發：** 計畫用 Lumentum 法說會作為「Lumentum 是 CPO 外部雷射 sole_source」的主要佐證。
但 Lumentum 在法說會裡天然會強調自家不可替代性；那不是獨立證據，是當事人陳述。
**Implementation：** `validate.py` WARN、`single_origin_report.py`｜
**可改？YES（實作）／NO（獨立性判準）**。

### L9 — 跨引擎匯流的前置條件
**Invariant：** 跨引擎 join 必須有**靜態 lookup 的共同 ID**，不由 LLM 推斷；
私有公司映射到**明確 null** 而非空缺（＝INV-1）。
**現況：** 投資諮詢開放的三個前置條件已於 2026-07-22 全部達標，gate 已開放；
判準由 `thesis/preconditions.py` 機器強制（`check_all()` 隨時可跑），
**不在此複述以免與程式漂移**。核驗清單五項仍是出手前的必要 gate。
**Implementation：** `config/company_identity.json`／`identity.registry`｜
**可改？YES（實作）／NO（＝INV-1）**。

### L10 — 早期資料庫以 correctness 優先，不背錯誤相容包袱
**Invariant：** **判準是「這筆資料今天重新取一次拿得回來嗎？」**
拿得回來 → 允許直接改 schema、搬移／重建／覆寫；拿不回來 → **只能 append**。
仍須保留 dump／備份、dry-run、migration manifest、reconciliation 與測試。
此授權不等於任意擴 scope；只用於修正已確認的高風險設計問題。
⚠ **適用範圍（2026-08-13 補；本條寫於只有 Neo4j 的時期）：** 只適用 Engine A graph、
tracked schema 與可由 ETL 重建的 projection。**不適用 private append-only authority**——
Engine C 的 manual observation ledger 與 Decision Store 都是**沒有第二份來源、Git 救不回**
的真相，發現錯誤用新的 correction record supersede 舊筆，**兩筆都留在 ledger 裡**。
**Implementation：** Engine A 可重建；Engine C ledger／Decision Store 只能 append｜
**可改？NO**（＝INV-6 的一半，也是 ResearchContext／DecisionContext 分離的依據）。

### L11 — 自己引用的「事實」要套跟圖裡 claim 同一套追源紀律
**Invariant：**
1. **具體審計／法律術語的措辭精度本身就是一個 claim。** qualified opinion、going-concern
   qualification、restatement、default、fraud、sole_source 這類詞必須一手核對、不能沿用
   二手框架。「公司自揭 material uncertainty」≠「審計出具保留意見」。
2. **對自己要輸出的事實，套用跟圖裡 claim 同一套 tier 與追源紀律。** 方向「感覺對」、
   剛好嵌得進已成形的敘事時，恰恰最該起疑；**別對外部 claim 嚴、對自己引用鬆**。
3. **多個二手都這樣說 ≠ 一手已證實。** 它們可能同源於一個原始誤述（假交叉驗證）。
4. **追源前先 grep 自家庫。** 一手常常已 ingest 在手邊。
5. **「我找不到」與「它不存在」是兩個不同的 claim，後者舉證責任高得多。**
   工具回報的「沒有」先問它是不是「讀不到」。**關鍵字未命中要改用語意定位**（分部附註／
   IFRS 8 段落／目錄），不是換幾個關鍵字再放棄——搜 `accounted for` 而年報寫 `account for`，
   一個時態差異就造出「這個 gate 對非美股結構性不可及」的架構級假結論。
   ⚠ **在解讀「沒命中」之前，先確認這份文件在結構上會不會包含答案**（2026-09-04 補）。
   這一步比換關鍵字更前面，而且**「我確實查了」擋不住它**。事發：3081 的分部歸屬被判成
   「單一部門」兩次，第一次依 2023 年報、第二次依當期 FY2025 股東會年報（112 頁／281,784 字，
   `部門`／`IFRS 8` 命中 0）——**兩份都不含財務報表附註**（`Independent Auditor` 也是 0 次），
   而分部附註本來就不在股東會年報裡。改抓 MOPS 財報區後，附註逐字寫著「歸屬為單一報導部門」：
   **結論三次相同，但只有最後一次是知識，前兩次是巧合。**
   操作化成一個問句：**「如果答案存在，它會出現在我手上這份文件的哪一節？」答不出來就別解讀 0。**
6. **同一套紀律適用於自己的技術診斷，不只引用的事實。** 一天內三個診斷落地後被推翻，
   共同形狀是**錯誤朝「有洞察力的結論」偏**，且每個都能用本檔的 lesson 語言包裝——
   **能套進某條 L 只代表值得查，不代表已經查過**。落地前跑一條**試圖讓結論變成假**的
   命令（不是驗證它為真）。
**事發（2026-07-20）：** 追 SIVE 的做空 audit 時，把「公司在 2025 年報自揭 material
going-concern uncertainty」誤述成「審計出具 going-concern 保留意見」，還標成「tier-1
審計佐證」。實際來源只是二手聚合新聞的措辭＋自家二手 memo。諷刺的是當下正在執行
source-trace——對圖裡的 claim 嚴格追源，對自己口頭引用的事實卻放鬆。
**Implementation：** ROADMAP「已撤回的診斷」｜**可改？NO**（全部是 invariant）。

### L12 — 一個表示承載兩種語意：閘門顆粒度錯位的共同形狀
**Invariant：** 某個表示同時承載兩種語意時，下游被迫二選一，而**兩邊都是錯的**——
這正是它難修、也活得久的原因。修法形狀永遠一樣：**不是放寬也不是收緊，是先分開再各自
定規則**；分開後每一邊都能套用比原本更嚴格的規則，混在一起時只能取兩者的下限。
**最有用的兩個訊號：**（a）**兩個修法方向都會壞**——若「放寬」與「收緊」都能舉出具體
災難，多半不是參數沒調好，是兩件事被壓在一起；（b）**修法讓警報消失得太乾淨**。
**另一個相鄰但不同的毛病是因果被截斷：任何會改變輸出的輸入，都必須出現在該輸出自己的
證據欄位裡。**
**事發（2026-08-05）：** 一個 session 內修掉四個表面無關的缺陷——LSE 標的行情永遠
quarantine（`currency` 同時是報價單位 GBp 與結算幣別 GBP）、歐洲標的整份行情被一根未結算
bar 廢掉、人工 runway 觀測永遠過期、待辦池無法得知項目已完成。分屬三個引擎，同一個形狀。
完整實例見 [`one-representation-two-meanings.md`](docs/solutions/architecture-patterns/one-representation-two-meanings.md)。
**Implementation：** 各處｜**可改？NO**。

### L13 — 基礎設施改動的驗收是「端到端有產出」，不是「元件會動」
**Invariant：**
1. **驗收條件寫成「產出出現在下游消費者手上」**，不是「這一步回傳成功」。交付前必須答得出
   「這條路徑的產出最後出現在哪裡、誰會消費它」；答不出來就是死路，不算完成。
2. **最危險的是成功與失敗在同一個訊號上同形**——空集合、沒有 in-flight 狀態、回傳 OK
   都是。要驗就驗那個會因為「真的成功」而改變的東西。
3. 這是 L12 的操作版：**驗證者自己讀了那個兩義訊號**，於是把「沒發生」誤讀成「已完成」。
**事發（2026-08-11～12，兩天內三次）：**（一）補上 filing watcher，實跑 78 筆 new 就宣告
「從完全靠人記得變成有自動監測」——但那 78 筆全躺在 `pending`，`pending` 不進 pq1 drain，
管子只接了一頭。（二）綁 `--event-type decision_evidence_delta` 後宣告「比較嚴格」——
但 `reactivation_event` 只寫不讀，沒有 consumed-marker，等待條件永遠黏不住。
（三）從 `counts` 沒有 `researching` 推論「排程沒跑 pq1」——但**跑完**的 drain 同樣不留
in-flight 狀態，實際上 5 個 slot 全滿。
**Implementation：** —｜**可改？NO**（＝INV-4）。

### L14 — 未經量測的機制不得享有默認信任，**gate 也不例外**
**Invariant：**
1. **驗收條件寫成「現有資料有幾筆真的變了」**，不是「這一步回傳成功」。答案是 0 就代表
   沒改到 binding constraint，不論改動本身多正確，**不得標記完成**。
2. **gate 本身也要被驗證。**「更嚴格比較安全」不是免於驗證的理由。
3. **順序不可顛倒：先量測，後放閘。** 先放寬而沒有量測 ＝ 拆煞車不裝儀表板。
4. 判斷 gate 有沒有用的三個**免 outcome** 測試：**恆亮**（觸發率近 100% ＝ 零鑑別力）、
   **不會滅**（清除率近 0 ＝ 那是牆不是閘門）、**講不出因果機制**（說不出「亮起時標的更
   可能變壞」＝ 行政流程假扮風控）。第四種失效「會滅但沒用」需要 outcome 才測得了。
5. **每次修東西先分兩類：維持營運**（管線壞了、腳本報錯）直接修、不必對齊終點，
   但**它也不算進展**；**改變行為**（新增／收緊 gate、改判準、改欄位語意、改 sizing）
   動手前必須答出**「這會讓哪個 baseline 數字變？」**，答不出來就不做或先進 ROADMAP。
   混在一起就是「東補西補一個月而沒有方向」的成因。
**事發（2026-08-13）：**「AXTI／LITE／COHR／SIVE 兩週漲 31–64%，系統為何沒形成入場判斷」。
實測 72 筆 decision 的 `live_supported_range` 全是 [0,0]、`axis_ceiling` 從未超過 0.002、
已量測 outcome 0/8；三個真正的資本上限一次都沒 binding 過——100% 的歸零由資料與研究完整度
造成。而同一診斷已被正確寫下四次，每次都沒改到 binding constraint。
**⚠ 寫進本檔不等於會生效。** L12（08-06）與其操作版 L13（08-12）相隔六天，就是同一形狀
在本檔已完整載入的情況下復發。**真正的防呆是會自己出現的常駐計數器，不是要人讀的段落。**
**Implementation：** daily brief 首屏的常駐計數器｜**可改？NO**（＝INV-5）。

### L15 — Gate 與語言處理的分工：先解析「這是什麼」，再判「它算不算數」
**Invariant：**
1. **gate 的正當性來自「它對目標有幫助」，不來自「它存在」或「它比較嚴格」。**
   自問：**這個 gate 攔下的，是不是它想攔的東西？** 若攔的是格式、時區、字串後綴、
   單位寫法、缺一個參數——它攔錯了，**該修的是它問問題的方式**。
2. **語意交給語言處理，權限永遠 deterministic。**
   語意（LLM 擅長、機械比對必誤判）：兩個引用是否同一來源、某陳述算不算獨立佐證、
   推文在講哪家公司。權限（永遠由 registry／人工 gate 決定）：authority 歸屬、
   evidence tier、資本、graph admission、live choice。
   **LLM 可以解析與提議，不可以授權**；解析結果必須落成可稽核的確定性紀錄。
3. **順序不可反：先解析身分，再查權限。** 解析時若偏好「能通過的答案」，等於讓引用去
   尋找能通過的權威——那正是 L8／L11 要防的 laundering。
4. **放寬解析不等於放寬判準——分開之後兩邊都要更嚴。**
**事發（2026-08-13～14）：** 五軸 evidence gate 用 `ref in reference_index`（exact 字串
相等）當判準。研究者寫 `yfinance://history`，index 的 key 是 `yfinance://history/AAOI`
——**一個少了 ticker 後綴的字串，讓整筆決策的資本歸零**，實測 22 次。
同輪另發現判準是 `any(失敗)` 而非「至少一個合格」，多附一個脈絡引用就整軸歸零。
**Implementation：** `sizing._resolve_reference`｜**可改？YES（實作）／NO（分工原則）**。

### L16 — 分類已經有 SSOT 時，要讓它**跟著資料走**到需要它的地方
**Invariant：**
1. 需要一個分類時先問兩層，缺一不可：**(a) 這個分類有 SSOT 嗎？(b) 它有沒有跟著資料送到
   需要它的地方？** 三次事故全部死在第 (b) 層——只問 (a) 會得到「有啊」然後繼續猜。
2. **修法是把分類附到 payload 上，不是再寫一份文件叫人記得去查。**
3. **字彙一旦有行為後果就必須被強制。** 自由字串卻決定去留，打錯不報錯、只是靜默沉底。
   收斂成封閉字彙後，**寫入端連已淘汰的同義詞都要拒絕**——同義詞的危險不是拼法不整齊，
   是它讓寫的人以為表達了一個沒被記錄的區別。
4. ⚠ **不要用會誤報的 linter 來防這件事。** 同日實測「掃描重複字彙分組」的原型：16 個命中
   有 14 個在 `tests/`，2 個 production 命中都是有書面理由的政策集合。
   **做一個會誤報的防呆來防止過度工程，本身就是過度工程。**
**事發（2026-08-26，一天內三次）：** ① `trace_status` 自創 9 個同義詞，而 `trace_backlog`
正是靠其中兩個值決定 lead 去留；② 手寫一組 stale 清單去判斷「哪些 blocker 要人動手」，
而 `resolution_mode` 早就是唯一權威；③ 口頭把 `system_internal` blocker 斷言成「bug 要解」，
而 registry 的 `next_step` 直接寫著怎麼處理。
**三次都不是粗心。共同形狀是：我需要一個分類，系統有，但我手上的介面沒帶。**
在那個位置上自己猜一份是阻力最小的路，而且**猜錯不會有任何東西壞掉**，它只會安靜偏掉。
偏的方向還是固定的——**永遠偏向「看起來需要更多研究」**。
**與 L15 的分工：** L15 講「解析與權限要分開」；本條講**分開之後，分類結果必須送到下游
手上**，否則每個消費端都會重造一份，而重造品會立刻開始偏離。
**Implementation：** `blockers_by_mode` 等｜**可改？NO**。

---

## 文件化學習

踩過的坑與設計決定沉澱在 `docs/solutions/`（帶 YAML frontmatter 可搜尋）；詞彙見
[`CONCEPTS.md`](CONCEPTS.md)。**遇到「某個事實塞不進既有欄位／狀態／關係」時先讀
[`closed-vocabulary-registry.md`](docs/solutions/architecture-patterns/closed-vocabulary-registry.md)**：
判準是 **taxonomy**（世界會長出新品類 → 字彙留鬆，放 `config/`／`schema/`）
vs **contract**（刻意有限 → 打開它是 bug）。
⚠ 新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`，否則 fresh clone
會缺檔而靜默失效；`tests/test_config_tracking.py` 是這道剎車。
