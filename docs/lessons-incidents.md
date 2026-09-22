# Lessons 事發與實作落點（不自動載入）

> **判準句住 `AGENTS.md`，事發與實作落點住這裡**（2026-09-22 依 G11 搬出）。每條事發是歷史記錄，帶日期、數字不隨現況更新。
> 內容自 2026-09-22 換版前的 `AGENTS.md` **逐字搬入**，只加標題不改寫；逐字副本另見 `docs/archive/agents-pre-graph-first-2026-09-22.md`。
> 新增 lesson 時：判準句進 AGENTS，事發進本檔，兩邊同一個 commit。

---

# 踩過的坑 / 通用判準 (Lessons)

> **格式：** 每條先給 **Learned invariant**（不變的那一句）、再給 **事發**（歷史記錄，
> 帶日期，不因現況改變而更新）、最後標 **Implementation 可改？**
>
> **引用慣例：** 使用者記不住 L 編號。任何回覆或報告提到 L1–L18 時，該編號**第一次出現
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
生命週期（2026-09-15 起多一個 `realized`：目標價已達，「對了」也要有出場觸發，與 disproof 對稱；由人提案，
現價高於目標價只是提醒不是自動轉移；出口同 `review_required`）：`active`（定期核查，建議每季）→ `watch`（leading indicator 朝 disproof 移動）
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
6. **同一套紀律適用於自己的技術診斷與自己提的修法，不只引用的事實。** 一天內三個診斷落地後被推翻，
   共同形狀是**錯誤朝「有洞察力的結論」偏**，且每個都能用本檔的 lesson 語言包裝——
   **能套進某條 L 只代表值得查，不代表已經查過**。落地前跑一條**試圖讓結論變成假**的
   命令（不是驗證它為真）。
   ⚠ **修法也是一個待否證的結論**（2026-09-13 使用者定案，主詞由「診斷」擴大到「修法」）：
   提案時就要答出**「如果這個修法是錯的，最先壞掉的是哪一筆現有資料？」並去看那一筆**，
   不是等實作完再看。事發（2026-09-13）：提案「同幣別就不該套匯率容差」時，最先會壞的是
   台積電與聯電那兩筆——查它們的基期幣別是 30 秒的事；實作完才發現那兩家的基期也記成美元，
   修法打掉的是兩個真案例。**這一條在提案當下就可否證，所以整個實作與還原都不必發生。**
   操作化住 [`skills/development-flow/SKILL.md`](skills/development-flow/SKILL.md) Step 3 的「修法層級」第④問。
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

### L17 — 不夠 general 的機制當下就修，別讓它進 backlog
**Invariant（2026-09-10 使用者定案）：**
1. **看到「這個機制只認得我當初那個案例」就當下修掉**，不是記一筆 backlog。
   理由是這一類缺陷**不會壞、不會報錯、測試不會紅**——正因為沒有東西被它逼著回來修，
   放進 backlog 等於永遠不修，而它每天都在安靜地偏。
2. **檔次判準（決定當下修還是排程）：** 十行內、不動 contract → **當下修**；
   動到 contract／封閉字彙／多個 owner → Z2 給 proposal；
   **等於重寫一個既有子系統** → 才進 ROADMAP（例：為節點屬性做一套 `edge_resolution`
   等價物）。⚠「不是重構等級」是門檻，不是藉口——說不出它動到哪個 contract 就是當下修。
3. **三個問句：** ①這個 key 真的唯一嗎（寫 `dict[k]=v` 前先問 k 會不會重複）？
   ②這個欄位是覆蓋還是聯集，覆蓋掉的那份還有第二個地方留著嗎？
   ③這個機制的對稱面做了嗎（邊做了點呢、偵測做了誰消費）？
4. **「不夠 general」的相反不是「盡量 general」，是「general 到資料支持的那一格為止」。**
   在沒有事實支撐的地方泛化，得到的是會誤報的分類（L16-4）。
**事發（2026-09-10）：** 一個 session 內撞到六個同形缺陷——`MERGE_NODE` 重載時靜默覆蓋
`name`、`doc_id → 檔案` 被當成一對一（實測 229 份檔案只有 206 個 doc_id）、
publisher 對「別人順手 commit 過」沒有表示、新增的兩個偵測沒有 consumer。
**六個沒有一個會讓測試變紅。** 逐案與判準見
[`mechanism-built-for-one-case.md`](docs/solutions/architecture-patterns/mechanism-built-for-one-case.md)。
**Implementation：** 各處｜**可改？NO**（判準）／**YES**（各處實作）。

### L18 — 抽取之後逐字就退出系統，於是每個下游都只能相信 label
**Invariant：**
1. **任何「把原始證據換成一個標籤」的步驟，都必須讓那個標籤指得回原始證據。**
   指不回去時，下游**結構上不可能**發現標籤錯了——而測試不會紅，因為測試問的是
   「程式有沒有照標籤做」，不是「標籤對不對」。迴圈是封閉的：
   **抽取時 LLM 給 label → 程式照 label 做 → 測試驗程式 → 回到 label**；
   逐字是唯一在迴圈外的東西。
2. **判別法：這個工具的輸出裡，有沒有任何一個字是「當初那份文件實際寫的」？**
   沒有 → 用它的人挖不出這一類問題，不論他多想挖。
3. **「請深入思考」型的 prompt 修法在這裡無效，兩個理由**：①它靠自律——L11-6
   （落地前跑一條試圖讓結論變成假的命令）這條判準早就寫在本檔，事發當天照樣發生，
   那是 L16 的形狀（判準有 SSOT 但沒跟著資料走到需要它的地方）；②**就算想挖也沒東西可挖**。
   **根解是拿掉資訊落差，不是在落差上面加一層提醒**——加一張檢查清單也是加機制（L17-2／
   development-flow Step 3 第③問）。
4. **深挖若需要繞過自己的工具，它就不會例行發生。**
5. ⚠ **推論：機械偵測器的用途是「自動生出那種問句」，不是自動修。**
   事發當天真正觸發深挖的，是使用者問了一句「Sivers 的需求錨怎麼會是成熟製程」——
   系統要能自己生出那種問句，否則它等著一個剛好起疑的人。
**事發（2026-09-18）：** 重判一個 relation 的 82 條邊，**29 條要改（35%）、8 條逐字
根本不支持任何關係（10%）**；同日另找到 `tech:inp_eml` 與 `tech:eml` 是重複節點、
`external_laser_source is_component_of isolator` 方向相反且其逐字只是列舉兩樣產品。
**全部靠直接讀 `extractions/*.json` 才發現**——因為 `loader/load_to_neo4j.py` 有六個
`MERGE_*` 卻獨缺 sources，**1,105 段逐字（192,055 字元）在載入那一刻被丟掉**，
而 `query/structure.py`／`query/bottleneck.py`／`query/graph_context.py` 提到 `quote`
的次數是 **0**。完整量測與架構見
[`2026-09-18-verbatim-never-reaches-the-decision.md`](docs/brainstorms/2026-09-18-verbatim-never-reaches-the-decision.md)。
**Implementation：** loader 的 sources MERGE ＋ 讀路徑的 `--quotes`｜
**可改？NO**（判準）／**YES**（實作）。

---

---

# 其他自 AGENTS.md 搬出的事發段落

## 「建議只由 pool ground truth 導出」的事發（2026-08-30）

事發：2026-08-30 weekly 對八個編號建議 `drop`，聲稱「來源已停止產出」——實測
`source_cleared` 是 **0/8**，其中兩項是等事件、一項是使用者明示 defer；同晨 daily 又對
其中三項建議 `go`，兩份排程直接互相矛盾。

## 「現況數字會過期，判準不會」的兩次事發（2026-08-19）

實測代價（2026-08-19 一天內兩次）：① ROADMAP 寫著「`live_choices` 仍為 0 筆——live 這條
路徑從未被走過」，agent 直接引用它告訴使用者，但使用者前一天就走完了全鏈；② ROADMAP 寫著
`commercial_maturity` 的缺口是「缺人去讀年報」，agent 差點照做，實測後發現 7 個積壓沒有
一個是讀年報能解的。

**同理適用於任何 repo 裡已有結構化來源的清單：清單會腐壞，判準不會。**
曾在本檔維護 skill 清單，新增 `luna-reviewer` 後沒同步，表上長期少一個（2026-08-19 發現）。

## 圖公司 ID 憑名猜的事發（2026-07-21）

- **圖公司 ID（`co:*`）不要憑公司名猜。** 唯一權威是 `config/company_identity.json`。
  例：Sivers 是 `co:sivers_semiconductors`，不是 `co:sivers`（2026-07-21 週掃即因猜 ID
  未命中而漏掉比對）。ID 未命中時要區分「ID 沒解析對」與「圖中真無此公司」，**不能默默跳過**。

## 技術訊號三次實測的完整記錄（2026-08-01；原文「任何改寫都不得刪減它」，故整段逐字搬此）

**實測記錄（歷史，不因後續移除而改寫，任何改寫都不得刪減它）：** 三次實測全部失敗——
以訊號 gate 現金投入使終值**輸給無腦定投 8.5%**（QQQ 91.5%、SOXX 91.9%）；訊號調節借款
提取**無可測得效果**；訊號決定投給哪個標的**輸給固定單押最佳標的 22%**，且三分之一時間
買進 CAGR 僅 7.2% 的弱標的——**「買跌最深的」會系統性把錢導向長期較弱的資產**。
`stretched_above_sma200` 同為未實測的推論。完整證據見
[`2026-07-31-leverage-glide-path-requirements.md`](docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md)。

**那三次的 scope 全部是 beta sleeve 的定投擇時**（2026-09-10 使用者定案；全文見 archive）：沒有一次測過 alpha 個股的
進出場；唯一做了 rolling start 的是測試二（**無效果**），「−8.5%」來自**單一路徑**；原禁令攔的範圍大於它被驗證的範圍（L15-1）。

## L19 的事發：排序 Goodhart 鏈（2026-09-15 → 2026-09-22）

**唯一排序權威仍是 `query/bottleneck.py::rank_bottlenecks()`。** alpha 排序必須**消費**它，不得重算結構分或自建第二套；
`research_status` 是研究完整度，不得拿來排序；篩選只在它的順序上**過濾**。事發（2026-09-15）：上詮、聯亞、Sivers 等七家
在圖裡都有邊、也接得到需求錨，但未填 `substitutability` 被當 0 過濾（門檻 4），可投資排序 37 列一檔都沒有——
**看不見的不是候選，是我們沒填的格**。

**2026-09-22 診斷：** 上面那段加「必須輸出有序清單與明確的首選」「首選＝filter 不是分數」，再加 Phase 1 驗收行「可投資排序要出現台股」，
讓研究火力去補 `substitutability` 讓特定公司通過 filter。實測：pq2 歷來 650 個編號有 52% 由財務／決策層自動鑄；186 個技術節點 65% 只有一家供應商。
判準與數字見 `docs/brainstorms/2026-09-22-graph-first-direction-decision.md` §1.4。


---

# development-flow Step 3 的事發（自 `skills/development-flow/SKILL.md` 逐字搬出，2026-09-22）

## Step 3 第①②問的事發（2026-09-11）

  事發（2026-09-11）：同一輪裡我提了兩個修法，使用者問一句「這些都是真修、不是
  workaround？」之後自查，**兩個都是補丁**：①「lead 的 pq2 gate 已消失沒有偵測」我提
  加一個偵測（顯形），而根除是讓結案時自動推進來源 lead——孤兒從「看得見」變成
  「不可能發生」；②追源路徑我提一張要自己勾的 checklist（自律），而根除是可執行的
  route resolver，park 要附**它的** receipt 而不是我的自陳。
  **兩次自查都只因為使用者問了才發生**——所以它必須是欄位，不是美德。

## Step 3 第③問的事發（2026-09-13）

  事發（2026-09-13）：提案是「把虧損股的 Abstention 納入常規授權清單」——那是**加一層授權**，
  編號照鑄照 resolve，要求宣告的那個機制一個字沒動。被逼著回答③之後找到的根解是**拿掉**：
  估值方法本來就由 ledger 裡寫了哪一筆假設決定，那道「必須先鑄一個編號才能切換」的閘門是重複的。
  同一輪的第三個提案「新增一個共識口徑字彙值」也是加機制，而且是把機械檢查換成人工宣告
  ——那正是 L15（先解析身分再查權限）要防的 authority laundering。

## Step 3 第④問的事發（2026-09-13）

  事發（2026-09-13）：提案「同幣別就不該套匯率容差」，前三問全部給它高分（讓失敗結構上不可能、
  靠程式、而且是收緊）。實作完 materialize 才發現四檔全部失去容差——**包含兩個真案例**，
  因為那兩家的基期觀測也記成美元。**而④在提案當下 30 秒就問得出來**：最先壞的就是那兩筆，
  去看一眼它們的基期幣別即可。整個實作與還原都不必發生。

## Step 3 逐題對照（2026-09-13）

  **逐題對照本輪三個提案：**①被③攔下（加授權 vs 拿掉重複閘門）；②只有④攔得到；
  ③被②與③同時攔下（人工宣告＝自律、且是加機制）。
  ⚠ **①③原本就在兩問的射程內**——兩問不是攔不到，是**答題者可以誠實地答錯**。
  ③把「是加還是減」變成一個沒有模糊空間的事實題，④把它變成一條要跑的命令；
  這與本條開頭那句是同一件事：**欄位比美德可靠**。


---

# 已撤回的技術診斷（自 ROADMAP 逐字搬入，2026-09-22）

## 清單

> **這一節不是自責，是一份檢查清單。** 每一筆都是「已經寫進 commit／ROADMAP／程式註解，
> 事後被推翻」的技術診斷——不是待辦、不是 bug，是**曾經看起來完全正確的錯誤結論**。
>
> **共同形狀：錯誤有方向性——全都朝「產生一個有洞察力的結論」偏**，而且每一個都能用專案
> 自己的 lesson 語言包裝（L12 一表兩義、L15 gate 攔錯東西）。
> **模式匹配是提出假說，不是確認假說。** 一個現象能被套進某條 L，只代表它值得查。
>
> **用法：** 宣稱「找到根因了」之前，先跑一條**試圖讓自己的結論變成假的**命令
> （不是驗證它為真——那是確認偏誤）。專案對每個 thesis 都強制 `disproof_condition`，
> 這一節是把同一個要求套到自己的技術診斷上。

| 日期 | 被推翻的診斷 | 一條就能否證它的命令 |
|---|---|---|
| 2026-08-19 | COHR「Engine C 的 `bar_date` 是憑空生成的、`price` 對不上任何收盤」 | `date(2026,8,17).strftime('%A')` → `Monday`。**一本日曆就能否證** |
| 2026-08-19 | 待辦池 `decision_review` 不退場是因為「空 `blockers` 被判成非純系統」 | `python -m decision_lab card <decision_id>` → `card.blockers` 有 **7 個碼**，不是空的 |
| 2026-08-19 | 「`execution_fx_stale_since_decision` 未登記，掉進泛用 prefix」 | 讀 `config/decision_blockers.json` 的 `_matching`（**最長**匹配，不是第一個）。真相是它早就以 exact prefix 登記 |
| 2026-08-19 | 「`live_choices` 仍為 0 筆，live 路徑從未被走過」——**直接引用自家文件** | `select count(*) from live_choices` → **1** |
| 2026-08-19 | 「`commercial_maturity` 積壓缺的是有人去讀年報附註」 | 逐一看 7 個積壓的 `missing_data` → 6 個是 `research_assessment_missing`。**靠讀年報能下降的是 0 個** |
| 2026-08-28 | 「COHR live reassess 失敗的根因是 `--as-of` 沒給」 | 修好 marker 後**不給 as-of 再跑一次** → marker 沒出現。真因在 `adapters.py::current_holdings` 另一處吞例外 |
| 2026-08-28 | 「`co:lumentum` 有兩個 cohort，重複偵測有漏」 | `sed -n '869,876p' decision_lab/store.py` → 註解逐字記著已檢查過這個確切案例。回空集合是正確行為 |
| 2026-08-28 | 「U2 把 `weakest_axis` 改成 level 排序是**零行為變化**的純重構」 | 改完直接 `pytest tests/test_probe_sizing.py` → `[missing_ref]` 立刻紅 |

**有可執行檢查的診斷活不過幾分鐘；沒有的全靠當下願不願意多查一步。**
（實測：U2「零行為變化」被測試抓到用了 3 分鐘；靠運氣發現的兩筆活到下一輪。）
所以落地前不是把診斷寫得更清楚，是**把診斷寫成一條會紅的檢查再落地**。

⚠ **這一節自己的 disproof：** 若之後仍發生「診斷已落地才被推翻」，代表它沒生效。
屆時該做的是把否證步驟綁進會自己執行的東西（測試、hook、commit 前檢查），
**不是把這張表寫得更長**。
