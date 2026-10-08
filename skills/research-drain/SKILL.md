---
name: research-drain
description: >
  把「目前能做的研究」一次做到底：先清已核准的 pq1 工單，再依 drain 排序清 triaged_go
  線索，最後補走圖報出的洞與已具名候選的初判。中途不報告、不等使用者；撞到 authority
  gate 就把該項掛成 pq2 編號**接著做下一件不需核准的研究**，直到閉包（每項工作都到達
  packet／誠實 park／排入 pq1 三種終局之一）才回來，用一份批次核准摘要收尾。當使用者說
  「清工單」「把 pq1 清掉」「你能做的全部做掉」「一路挖到沒東西做」「最後我一次核准」時使用。
  ⚠ 它不放寬任何 gate：入圖、Engine C 寫入、thesis mutation、live、decompose 選題、
  付費取得，全部仍需使用者逐項核准。
  觸發詞：清工單、清 pq1、全部做掉、一路挖、挖到沒東西做、最後一次核准。
---

# Research Drain Skill（v1）

## 定位一句話

**「做完」必須是機器查得出來的，否則我會在還有東西做的時候停下來。**

---

## 為什麼需要它：`/goal` 與 `/loop` 都擋不住這個失敗

2026-08-31 實測：同一個 session 內同時有 `/loop` 與 `/goal`，五張**使用者已核准**的
pq1 工單（Schaeffler、NVIDIA、奇景、Lynas、上詮）從頭到尾沒被碰過。原因不是指令沒生效，
是當時的 goal 條件寫成「持續累積我需要核准的事項」——而「累積」在任何一刻都成立，
於是一產出一批就滿足了。

**判準：停止條件若能在任意時刻被滿足，它就不是停止條件。**
本 skill 的存在理由就是把「做完」換成 `counts` 查得出來的數字。

---

## Step 0 — 先避讓排程，再讀狀態

**本 skill 是長時間、連續寫入的操作，而本機排程寫的是同一組檔。**
`AGENTS.md`：「同一 working tree 只讓一個 agent 寫入……**排程與互動 session 也算兩個
writer，不能重疊**。」重疊時最危險的不是報錯，是**靜默的 lost update**——daily 剛
harvest 進來的 lead 被本 skill 用舊狀態覆蓋掉，沒有任何東西會叫。

```powershell
& '.venv\Scripts\python.exe' scripts\writer_guard.py check --minutes <預計時長>
```

**exit 2 就不要開始。** 四種不安全：現在落在 daily 避讓窗內、**這段 run 會跨進窗內**
（起跑時安全不代表跑到一半安全，而跑到一半撞上最難收拾）、working tree 不乾淨
（可能有另一個 writer 在跑，或上一輪沒收乾淨）、**writer lock 被排程持有**
（鎖補上時間窗防不了的延遲開跑——2026-08-29 排程 08:21 才收尾的那種）。

check 通過後**取鎖再開跑**（2026-09-02 起雙向互斥：排程 harvest 撞到會自己 fail closed 讓開）；
收尾（含中斷收尾）release：

```powershell
& '.venv\Scripts\python.exe' scripts\writer_guard.py acquire --minutes <預計時長> --purpose "research-drain"
# …工作…
& '.venv\Scripts\python.exe' scripts\writer_guard.py release
```

鎖有 TTL，session 崩潰最多卡排程一個 TTL；loop 模式每輪醒來重新 acquire（同 owner 是續期）。

writer lock 是雙向互斥：排程 harvest 也會 acquire `scheduled`，互動側持有
`interactive` 時它會 fail closed。state 已退出 Git，因此不再用 HEAD／publisher commit
間接猜另一個 writer；里程碑續跑時重新確認自己仍持有 lock，並重讀
`todo_pool.json`／`pending_leads.json`，不得只沿用記憶中的狀態。

接著**先清機械段，再讀狀態**（2026-09-09 起；段序定義見 `engine_b/queue_segments.py`）：

```powershell
git status --short
& '.venv\Scripts\python.exe' -m engine_b.cli consume-fired          # 段 1：fired 的追源 watch 排回 pq1（零 token）
& '.venv\Scripts\python.exe' -m engine_b.todo sync                  # 段 1 的 pq2 型翻醒＋同步待辦池
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go --run     # 段 2b：常規授權類別（config/standing_authorization.json）直接下使用者本來會下的 go
& '.venv\Scripts\python.exe' -m engine_b.cli counts
& '.venv\Scripts\python.exe' -m engine_b.todo list
& '.venv\Scripts\python.exe' -m engine_b.cli drain                  # 首行是段 0–1 計數器；假設對照的 fired watch 逐筆列在這裡
```

機械段不吃研究預算，跑完才知道研究段真正有多少工作——2026-09-08 實測 39 筆 fired 沒人接、
`drain` 卻顯示佇列只剩 2 件，就是因為這三支從沒被排進任何流程。

⚠ **這一步在續跑時同樣要做。** token 用完後的新 session 必須能只靠 repo 狀態接手——
`git status --short`、`todo_pool.json`、`counts`、各 action／decision receipt——
**不得依賴前一個 session 的自然語言摘要**（`AGENTS.md` 雙代理交接契約）。

---

## Step 1 — 工作順序：已核准的先做，其餘用既有排序

**順序不是自由心證，三段固定**（前面另有機械段 1–2，見 Step 0；`drain` 首行列出的**假設對照**
fired watch 屬段 0b：拿 `fact` 去對觸發 lead 的一手數字，落 `engine_b.hypotheses` 的 verification 後
`python -m engine_b.event_watch consume <watch_id>` 收掉——它是研究，不是機械）：

⚠ **段 0b 對照下來是「無關」時用 `reactivate`，不是 `consume`**（2026-09-11 補上 CLI）：
`python -m engine_b.event_watch reactivate <watch_id> --note "為什麼判定無關"`。
`consume` 說的是「這個等待結束了」；`reactivate` 說的是「觸發它的那則 lead 不是它在等的東西，
等待條件依然成立」。用錯會讓一個還沒被回答的問題安靜消失。觸發 lead 在 fire 時就已進
`consumed_leads`，所以同一則不會再叫醒第二次；到期仍由 `expires` 收斂。
實測（2026-09-09）：ew_0005／0007／0057 三個 `fact_verification` 都被**無關的** tier-1 lead
以 entity 交集誤觸（COHR 8-K 是 RSU、AAOI 8-K 是租賃），當時沒有這個命令，只能直接改 JSON。

**段 `poll_hits_pending`（T2 輪詢命中待檢，2026-10-06 起；與段 0b 同級）**：daily ⑩d–⑩g 每天替到期的等待上網查一輪，
查到的東西**只掛在那條等待上**（網址出自同一次搜尋；摘要與日期是模型寫的，欄名標明）。判定在這裡：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.watch_poll queue          # 逐條列命中（標題、網址、模型摘要）與判定命令
& '.venv\Scripts\python.exe' -m engine_b.watch_poll judge <watch_id> --url <網址> --touches yes --note "…" --quote "文件逐字"
& '.venv\Scripts\python.exe' -m engine_b.watch_poll judge <watch_id> --url <網址> --touches no --note "為什麼無關"
```

**先打開網址讀原文再判**——摘要是模型的話，不是原文（L18）；轉載或舊聞重刊判無關（2026-10-06 雷達實例：AK&M 把 2024 年的
意向書重刊成新事件）。判定觸及＝那條等待被叫醒，之後照它的喚醒目標走既有的路：追源線索跑 `consume-fired` 排回 pq1、
pq2 型跑 `todo sync` 翻回球在你、假設型進段 0b。命中掛超過兩週沒判，`audit invariants` 的 QueueLiveness 會亮紅。

**段 `narrative_rewrite`（敘事該重寫，2026-09-29 Phase 3 Step 3.4 起；與段 0b 同級，排在下面三段固定之前**——
它和 0b 一樣是**已經醒來的等待**，醒來的反證不排在新線索後面）：敘事自己的反證（`brief:` 語意 watch）
與「缺 X」「已定價等回落」在等的事（`wake_brief` watch）**醒來、被判觸及或到期未判**都進這一段——不鑄 pq2、
不進假設對照。下一步是**重寫那一檔的敘事**（研究；寫敘事是強模型的工作，便宜模型只列出來交回）：

- ⓐ 讀那一檔的現行敘事（`python -m alpha brief <T>`）與觸發的 watch（`python -m engine_b.event_watch list`）；
- ⓑ 重跑 `python -m alpha research <T>` 的 packet（`brief_frame` 是 v2）與三題稽核區；
- ⓑ′ **連結斷了**（2026-09-29 Step 3.6；心跳段 3「敘事該重寫 N（其中連結斷 M）」、候選板那一列的「該重寫」）：敘事
  `disproof[].link_source_ref` 連到的 watch 已不在盯，並寫出為什麼斷——來源已收掉（讀圖重讀、memo 換版）就把那條改成新來源鍵
  （新讀圖的 `reading:<新 id>#n`）或改為新登；來源被判觸及／到期未判就先看來源那一邊（thesis 複查、節點重讀）怎麼處置，再改寫這份敘事；
- ⓒ 寫新的一版 `python -m alpha brief <T> --add spec.json`，`acknowledged_touched[]` **逐條處置本公司名下
  所有**該重寫的 watch（`still_holds`／`thesis_changed`／`retired`／`confirmed`＋一句 note）——**不列就拒收**；
  換版與撤回都不會吞掉它們（已過到期日但 daily 還沒標記的，寫入端會先照日期轉成到期）。處置寫成 watch 既有的收據
  （fired → consumed、觸及 → `judgment.handled`、到期 → `expiry_resolution: narrative_rewritten`）。
- ⓓ **加碼條件**（`confirm[]`、watch 帶 `condition_role=confirm`，2026-10-04 Phase 7 Step 7.0d）也走這一段：
  **觸及＝「結構確認了」的提醒，不是買進訊號**——新的一版以 `confirmed` 處置，在敘事裡寫明確認了什麼、候選狀態換不換
  （系統不自動改）；**到期沒觸及**＝「確認事件沒在期限內發生」，本身就是資訊，照實處置（`still_holds`／`thesis_changed`／`retired`）。
  它不是反證：不算進「反證：在盯／觸及」，也不擋可開。契約上是選填欄（寫入端不擋），但**持有或可開的敘事要寫**——ROADMAP Phase 7 驗收②「持有或可開的另有加碼條件」；形狀見 packet 的 `brief_frame.spec_shape`。

以下是**三段固定**：

1. **所有「使用者已授權、還沒做完」的項目** — 放著不動是本 skill 要修的那個 bug。
   **永遠排第一，不論它們看起來多無聊。** 包含兩類，同級處理：
   - **`pq1 進行中` 的工單**（`dispatch_status` 為 queued／researching）
   - **`manual` 型已授權項**（`todo list` 的 manual 段，hint 註明使用者指示者）——
     ⚠ 2026-09-01 實測：[325] 授權後一天沒被排入，因為當時本段只寫了工單。
     **佇列定義漏掉的授權項不會自己出現**（L16 的形狀：分類存在，沒送到消費端手上）。
2. **`triaged_go` 線索** — 順序**只認 `engine_b.cli drain` 的輸出**。
   ⚠ 不得另建排序：`engine_b/priority.py` 是 pq1 排序的唯一權威，
   「我覺得這條比較有趣」正是它要防的東西。
3. **每檔閉環（段 5，2026-09-09 起；2026-10-07 Phase 7 Step 7.0g 收窄母體）** — 前兩段清空後、走圖之前。工單不是自己列的：
   `drain` 首行的「段5 每檔閉環」一行與 `python -m webapp status` 的「每檔閉環」段，都由
   `alpha/closure.py` 從 analyst view artifact 的 `readiness.blocker_details` 照抄（每格帶
   `absence_kind`／`settled`）。
   **母體（`closure.population_for`；每檔各自的是非題，不跨檔比較）**——深度住在層、廣度住在檔（plan 2026-10-04-001 A4）：
   - **在母體**：已持有、有 thesis（lifecycle）、現行候選（缺 X／等回落／可開）、邊緣或量不到**且**供給側有座位（結構表 `supplies_to` 列）。
     邊緣判定或座位讀不到的，一律留在母體（INV-3）。
     ⚠ **研究時碰到名冊外（或還沒 materialize）的公司，判邊緣一律跑 `python -m alpha edge <代號…>`**——同一個判定與門檻，
     缺的輸入用 yfinance 補、逐欄標來源；**不得目測市值就寫「邊緣大小」**（failure log #43：冷板讀圖把分析師 16 家的雙鴻寫成邊緣）。
     讀圖、敘事、層說明裡寫「邊緣」時附上那一列的判定與來源；「邊緣無法量」照實寫缺哪一項。
   - **非倍率**（非邊緣、以上皆非）：**不寫敘事、不寫讀圖、不為了湊終局鑄 Abstention**——它的文件進層說明當在位者或客戶的證據
     （例：Dover 的 10-Q 是快接頭與板式熱交換器兩份層說明的關鍵證據）。closure-gate 逐檔列名附市值與覆蓋；每次 materialize 重算，翻回邊緣就自己回母體。
     ⚠ **不得替非倍率檔寫「不要（非邊緣）」敘事**：那是把 filter 的結果冒充研究判斷（L12）——10-05 寫的 39 份之後 0 筆改判。
   - **邊緣沒座位**：做一次「坐哪一層」**短檢查**——讀它自己的年報／決算的業務段與客戶段（不用供應商自述補，L8），結論三選一：
     ①**補供貨邊**（研究包走 pq2 `ra_admission`；入圖後它就在母體）②**開發中**（只有 develops 邊、還沒供貨）③**不坐任何層／在需求側**。
     ②③寫一份 v2 敘事（候選狀態照研究結論，理由寫明是哪一種）；closure-gate 以 90 天內有沒有 v2 敘事判「查過」，到期自己回到佇列重問。
     ①的入圖包鑄號之後（focus＝這一檔），closure-gate 列成「等入圖（[n]）」、不排——go＋apply 之後它有座位、自己進母體；
     drop 了短檢查又到期（2026-10-08，failure log #51：原本只認得②③的出口，①掛 pq2 之後仍被列成可推進）。
     ⚠ ②③若寫成「缺 X」（現行候選），它就進了母體，卡點照母體的路走（例：讀圖「圖上沒有它供貨或開發的層」→ 補座位走 pq2）。
   - ⚠ **「已定價」不是分流條件**（不設門檻）：已定價的寫「已定價等回落」並鑄 watch，**不得寫成「不要」**——「不要」不帶到期，會讓它安靜地離開視野。
   - **等主題組**（2026-10-08，failure log #26）：一條**新鏈**的主題等權組要在它第一份 v2 敘事之前定義（plan 7.1 ④）——順序是
     `python -m engine_b.todo add-theme-cohort --spec <file>` 鑄號 → 使用者 go → `complete-theme-cohort <n>` → 才寫第一份敘事。
     組提案還在 pq2 時，那幾檔在 closure-gate 列成「等主題組（[n]）」、不排；`alpha brief --add` 對它們的第一份敘事整筆拒收。
     ⚠ 機器只認得「已經鑄號的組提案」：新鏈的候選名單只寫在文件裡、沒鑄號，就擋不到——**新鏈先鑄組提案**，再進段 5。
   **下一檔選誰不是自由心證**——`closure.NEXT_PICK_RULE` 五條依序比：
   使用者沒有明示 defer → 產業能加一（所屬產業尚無 ready 檔）→ 有帶 substitutability 的結構邊 → 已有基期觀測 → ticker
   （2026-10-07 刪「有同期 EPS 共識」「forward EPS 為正」：理由引用的 bridge.py 在 Phase 0 已刪，而它們讓有共識的大型股排在前面）。
   ⚠ 第一條是**使用者的明示指示**（pq2 有未結案的 `deferred_at`），所以排在研究判準之前；
   它往後排、**不過濾**——藏起來會讓「沒做」與「不存在」同形。
   ⚠ 倒數第二條的成本維度**只破平手**：前面幾條的相對順序一格都沒動。
   **廣度短敘事的範圍**（邊緣、有座位、還沒有現行敘事——或它的 watch 醒了）：每檔**一份**有範圍的 v2 敘事，上限一份年報＋packet；
   先宣告賭注騎在層還是插槽；三題引用稽核區的數字；候選狀態＋有到期的 watch。**三項必查**（三個錯都是「證據在手上卻沒讀到」）：
   ①致股東報告書／經營者的話（failure log #32）②財報表頭是個體還是合併（#35）③這一層在圖上有沒有同義節點（#36：讀圖與走圖只讀其中一個 id）。
   「缺 X」的 X 若是層的問題（幾家能做、客戶為什麼選、什麼會換掉它）→ 那是**層深讀**的入口（下方），不在段 5 深挖個股。
   **深度優先**：第 N 檔未到終局不開第 N+1 檔，除非它卡在 pq2 或世界。終局三種：ready／
   剩餘 blocker 全部 settled／全部掛在 pq2 編號上。每一格的路（判準機械，見 `alpha/absence.py`）：
   - `not_yet_recorded`／`upstream_unavailable` 的基期實績、指引 → 抓一手財報寫 mechanical 觀測（不碰 gate）
   - ⚠ **2026-09-22（Phase 0）：營運假設、倍數、horizon 這三格隨估值鏈退役**（ROADMAP Phase 0／G3）。
     判斷檔仍寫 ledger（敘事、短評、反證），evidence_refs 必須解析得到；**不再有校準倍數與折溢價主張**。
   - 客戶端承諾、獨立來源 → source-trace，可能結成 RA packet（入圖仍是 pq2）
   - `provider_missing` → 換來源，否則提案 Abstention（pq2，因為它把這格從工單上拿掉）
   - ⚠ **2026-09-22（Phase 0）：虧損檔選估值方法（`ev_to_sales` vs 本益比）那一條退役**
     ——整個估值層不再存在。`Abstention` 保留它自己那件事：**宣告這一格不用再做**（→`settled`），
     它是 append-only 紀錄，不是呈現層的標籤。
   - 判讀型 Engine C 觀測（backlog、客戶集中）→ 打包觀測提案（pq2）；同類缺口跨多檔就打包成一批
   - ⚠ **2026-09-30（Phase 3 Step 3.7）：讀圖面板升核心。** `readings=not_yet_recorded`（這家公司坐的層與插槽都還
     沒有讀圖）的下一步是**寫那一層或插槽的讀圖**——強模型、研究：`python -m query.structure <node> --quotes` →
     `python -m alpha structure-reading <node> --add spec.json`（兩半各至少一段引用）；那一層若已由走圖第 1 型
     （薄層沒人讀）排入，就在那裡一起做，不重複開題。坐在哪幾個節點見個股頁讀圖面板的 `seats`。
     **不得為了讓閉環收斂把讀圖缺席標成 settled**——「刻意不主張」只能來自 Abstention 紀錄（它是研究結論，要寫得出理由）。
     `readings=upstream_unavailable` 有兩種，看理由句（產生端寫明）：「圖上沒有它供貨或開發的層或插槽」＝先補圖的供貨／開發邊（入圖走 pq2 `ra_admission`），或判定它在需求側（寫進敘事）；「這次沒讀到圖或讀圖 ledger」＝先修取數。兩者都不是去寫讀圖。
     `readings=review_required`（讀圖 stale，readiness 只帶 flag）→ 走圖第 4 型重讀，不在段 5 處理。
   每消一格 `python -m webapp materialize <TICKER>` 一次，讓下一格的判斷讀到新狀態。
   **層深讀的入口**（S4 層說明＋層讀圖；研究火力的主產品——一份層說明同時改坐在那一層的每一檔）：節點命中任一條就可以開——
   走圖第 1／2 型、F48「下一層 0 條」、**有任何一份敘事的「缺 X」指向這一層**（只看有沒有、不數幾份——數了就變回分數）、
   讀圖過期（第 4 型）、層主張的 watch 醒、使用者點名。**它們之間不排序**：先後只看觸發或 lead 的時間與使用者點名（G2）。
   讀完回頭改坐在這一層的每一頁被影響的那一格，「不要」的頁也要看（InP 磊晶那一份就是這樣改了 4 份敘事）。
4. **走圖：圖上該去研究的洞**（段 key `graph_holes`；2026-09-26 Phase 2 Step 2.6 起取代原「3.5 結構讀圖過期」與
   「4 圖的覆蓋缺口」兩段）——只有前面各段清空後才做。清單不是自己列的：
   ```powershell
   & '.venv\Scripts\python.exe' -m query.graph_walk            # 九型各自「命中／母體」＋每筆的問句（--json 給機器）
   ```
   ⚠ **走圖不排序、不打分**：九型的順序是閱讀順序，型別內按節點 id（lead 按首見時間）——**不是先後名次**。
   沒有「最該研究的洞」；挑哪一筆由 lead 時間與使用者點名決定（`AGENTS.md`「不得輸出跨檔全序」）。
   每一筆命中都附下一個研究動作；各型的做法：

   - **①薄層沒人讀**（`thin_layer_unread`）：`python -m query.structure <node> --quotes` → 寫讀圖
     （`python -m alpha structure-reading <node> --add spec.json`；兩半各至少一段引用，A2）。這是
     「集中需求灌進薄層」的研究入口；「只有 1–3 家」是問句母體，**不是瓶頸性證據**（量到的是我們讀了誰的文件）。
   - **②獨家且自報**（`sole_supplier_self_reported`；2026-10-01 Phase 4 Step 4.5 起有記憶與終局）：
     命中旁印 `open_lead`（已經有人在追的 lead）與 `reading`（過期的層讀圖）——**有 `open_lead` 就接著那一則做，
     不重鑄**；已有現行層讀圖的節點本來就不會命中。**研究啟動的那一刻**才鑄 lead（不是每一筆命中都鑄；
     沒有任何無人值守步驟會鑄它）：
     ```powershell
     & '.venv\Scripts\python.exe' -m engine_b.cli register --source graph_walk:sole_supplier_self_reported --url "graph-walk://sole_supplier_self_reported/<node>" --title "<人寫的研究問句>"
     & '.venv\Scripts\python.exe' -m engine_b.cli annotate <lead_id> --ref graph_walk_subject=<node> --ref graph_walk_as_of=<graph_walk artifact 的 generated_at>
     & '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go --tier 4 --reason "<為什麼現在追>" --content-type structural_fact --decision-impact structure_change --classified-by interactive:graph_walk
     ```
     `--url` 有真實文件就用真實 URL；用合成 URL 時 `published_at` 留空（不編日期，INV-6）。`--classified-by` 讓心跳的
     「分類層上次成功」不把它算成分類層跑過（另印「互動 triage N 則」）。**不是走圖命中**、而是使用者點名或 plan 指定
     題目起的互動研究，鑄號時來源寫 `directed:<出處>`、`--classified-by interactive:directed`（量測要分得出「走圖的產出」
     與「點名的產出」，不要借用 `interactive:graph_walk`）。接著以 lead-intake／source-trace 追源
     （source-trace「輸入是層／節點時」那一節）。**終局只有三種**（不加 trace_status 字彙）：
     ① 找到第二家供應商或客戶端／第三方印證 → 研究包走 pq2 `ra_admission`，核准後經 `scripts/apply_ra_admission.py`
     入圖（lead 終局 `applied`）；
     ② 公開的層文件找不到、或只有付費 → `advance <lead_id> parked --ref trace_status=awaiting_named_disclosure
     --ref "trace_trigger_entities=co:x;co:y"`（該層的客戶或供應商，分號分隔；`advance` 會自動建追源 watch，到期由
     `watch_expired` 計數現形），
     或 `--ref trace_status=not_pursued --ref parked_reason=…`（附理由）；
     ③ 圖上已經多了第二家（別的研究入圖了）→ 命中自己消失；lead 若仍 open，在這一段以 `not_pursued`
     收掉，理由寫「已由入圖消解：<那條邊>」。
   - **③供給側未填**：source-trace 找客戶端或第三方一手（source-trace「輸入是層／節點時」那一節）；補 `substitutability`
     或第二家供應商的研究包入圖仍走 pq2 `ra_admission`。
   - **④讀圖該重讀**（`reading_stale`；原段 3.5）：重跑 `python -m query.structure <node>`（插槽加 `--unit socket`）→
     重讀五個角度 → `alpha structure-reading <node> --add`（帶 `supersedes_id`）。
     ⚠ **只做 `stale`／`expired`**：`stale_low`（只有 evidence 等級變）刻意不進——恆亮＝零鑑別力（L14-4）。
     ⚠ 「客戶出新文件叫醒的重讀」不在這一型，在段 `fired_reading_reread`（同一件事不算兩次）。
     ⚠ **變化若被標成 `disproof_trigger`**（供給側多一家／反向路徑新增），那是**既有 disproof 的觸發**：
     依 L7 要在 48 小時內處置。但 **thesis 要不要改是四個人工 gate 之一**——鑄成 `thesis_mutation` 型 pq2 編號，**不要自己改 thesis**。
   - **⑤lead 點名不在圖**：onboard 評估（`skills/company-onboard`）。「另有 N 個名字 registry 解析不到」是
     **ID 沒解析對**，不是圖中無此公司（INV-1）——先修 registry 解析，不是 onboard。
     ticker 用 lead 關聯的同一條規則解析（`$SIVE`→`SIVE.ST`，2026-09-29 起）；「去掉後綴對到多家」另列候選、
     不解析——那要人看原文決定是哪一家，不是 registry 缺。
   - **⑥供貨走不到錨**：補需求鏈（誰買它的產出），或確認它不屬本題材（寫進 lead／報告，不要默默略過）。
   - **⑦沒人供應**／**⑧建模待補**／**⑨重複節點**（原覆蓋缺口與重複節點兩題）：**⑦之前先看⑨**——
     重複節點正是⑦的誤報來源：一個已經有供應商的東西被攤成兩個節點之後，其中孤立的那一個看起來像空白
     （`config/entity_aliases.json` 的 `_readme` 逐字記過這個後果）。逐字對照看走圖第 9 型——
     `python -m query.graph_walk` 對每一對印兩端各自的逐字，registry 的 note 也照抄在旁邊
     （原 `query.duplicate_nodes` 的 CLI 已於 2026-09-29 退役）；**只做 `unmentioned`**（registry 的 note 提過的先讀 note——
     「刻意不併」與「留待研究判斷」長得一模一樣，機械分不出來，要人讀）。判定「是同一個」是研究判斷，
     合併走 pq2 `ra_admission`；**判斷依據是兩端各自的逐字，不是 id 與 name**（L18）。
     ⑦的孤立節點（連一條邊都沒有）下一步是**先確認它該掛在 stack 哪一層**，不是「誰供應它」；
     `prod:` 前綴的 0 家節點是抽取副產品，只計數、不是題目。
     ⑧的下一步是補邊（入圖走 pq2），不是重新研究。

---

## Step 1.5 — ~~寫 assessment 之前先查該軸接受什麼~~（2026-09-22 退役）

原本這一步跑 `decision_lab references <cohort_id>`，查每個信心軸接受哪些 authority
（`financial_resilience` 只吃 `engine_c_financial`／`engine_c_manual`、`valuation_payoff` 只吃
`engine_c_valuation`／`fx`／`market`…），並分辨「引用對不上」與「證據不足」這兩種完全不同的失敗。

**五軸、Coverage 分數與 assessment JSON 整組在 Phase 0 退役**（ROADMAP Phase 0／G12）。
**那條判準本身沒有退役，只是換了主詞**：寫任何判斷時，`evidence_refs` 必須解析得到，
而「我找不到」與「它不存在」是兩個 claim（L11-5）。今天檢查它的地方是敘事 ledger 自己的
ref 解析，不是一支前置查詢命令。

## Step 2 — 每一條的終局只有兩種，沒有第三種

| 終局 | 條件 | 動作 |
|---|---|---|
| **產出入圖包** | 有可核准的 graph delta | `prepare_research_action.py` → `advance action_prepared` → 取得 pq2 編號 |
| **產出 onboard 包** | 標的不在 registry，但四維初判（瓶頸地位／需求錨／客戶端資本承諾／純度）值得入圖 | 打包 registry 條目＋首批 extraction＋L8 來源清單成 ra_admission packet 取號（`AGENTS.md`「Onboard 也走 pq2」）——**不要 park 成開放式 scope 問題** |
| **誠實 park** | 追源未果／被一手否定／只屬 Engine C 時變觀測／沒有唯一 focus／四維初判不過 | `advance parked` ＋ 完整 trace refs |

**onboard 包與 park 的分界是四維初判，不是「要不要多問使用者」。** 2026-09-01 實測：ESMT、
Samsung 兩例都 park 成 scope 問題丟回給使用者，但契約早就允許發現方直接打包取號——
使用者的核准介面是編號＋`go`，開放式問題反而是介面失敗。初判不過（如 ESMT 無客戶端
資本承諾）就誠實 park 並寫明哪一維不過；初判過就打包，讓使用者對 exact packet 決定。

**不得為了讓每條都有產出而製造空 Research Action。** park 必須附
`parked_reason`、`trace_status`（封閉字彙）、`trace_next_trigger`、`trace_requires_user`。
**`trace_next_trigger` 要寫出等誰的什麼文件**（「AXT 下一份 10-Q」，不是「同標的後續揭露」）：沒有明示 `trace_trigger_entities` 時，
watch 等的就是這句點名的已登記公司（2026-10-08）；沒點名任何一家就只會在日子到時叫醒一次。沒有要等的寫「無；<理由>」。
被排回的 lead（drain 清單印「↩ 上一輪：…」）重新停放時要把 `trace_status` 換成不同的值，得加 `--replace-trace-status`。

⚠ **2026-09-22（Phase 0）：工單（decision gap）原本的第三種終局「研究完成後重新評估、
以新 decision receipt 結案」已退役**（ROADMAP Phase 0／G12）。終局回到兩種：packet 或誠實 park。

---

## Step 3 — 撞到這些就停下來，不自行放寬

**硬 gate（永遠不自動）：**

- **入圖**（Research Action apply）——包含隨之而來的 registry 增列
- **Engine C 寫入**（manual observation ledger）
- **thesis revise／retire**
- **live choice／fill**
- **decompose 選題**——`system-decompose` 明訂系統由使用者指定，排程不得自行挑題
- **付費取得**（訂閱、報告購買）——必須另列 exact 金額與方案

**這些不是停止，是繼續：** 產出入圖包、park 線索、跑工單、註冊新研究題目、
確定性維護（fired watch 重排、pq2 型翻醒）。撞到硬 gate 時，把該項掛成 pq2 編號後
**接著做下一條**，不要停下來等。

**真正該停下來問的只有一種：需要使用者做 scope 決定**（例：「要不要把記憶體軸擴到
Samsung／SKH 側」）。這種問題 park 成 pq2 並繼續下一條，收尾時一起問。

---

## Step 4 — 研究紀律（本 skill 最容易鬆手的地方）

1. **搜尋摘要不是一手。** 2026-08-31 實測：搜尋引擎對晶界擴散那題給出「Dy 用量降 40–70%」
   「日系廠採用率 15–25%」「Tb₂Fe₁₄B 22T」三組具體數字，抓原文後**該文一個數字都沒有**——
   全是跨來源合成。**任何要入圖的數字必須來自實際抓到的原文**（L11 第 3 點）。
2. **方向與結論一致的來源最該起疑。** 尤其是市場研究公司的行銷頁與零件經銷商的部落格。
3. **互惠交易不是客戶資本承諾。** 雙方互為對方客戶（A 買 B 的零件、B 買 A 的成品）且
   無股權／預付款時，`payment_direction` 判 `unclear`，不判 `customer_to_supplier`。
   這是 POET「以認股權證換訂單」的推廣。
4. **誠實的否定結果是產出，不是失敗。** 補完 `sub` 發現只有 2 或 3、產業組因此仍是空的——
   那就是答案。**不得為了讓產業組長出來而灌高數值**（L14：未經量測的機制不得享有默認信任，
   而憑空的數值連機制都不是）。
5. **`n.attributes` 是覆寫不是合併。** 宣告既有節點時必須帶回它現有的 attributes，
   否則會靜默抹掉（實測差點抹掉 `co:tsmc` 的 ticker）。

---

## Step 5 — 停止條件（機器查得出來）

**「做完」＝閉包，不是「佇列空」（2026-09-01 使用者定案）。** 事發：skill 上線首日，
執行者在 `triaged_go=0`＋工單清空時就收工睡覺，而第三段（當時叫覆蓋缺口，今為走圖）還有 15 個 🔴、
外加一批已具名未初判的 onboard 候選——**那些全是不需要使用者核准的研究**。
使用者原話：「不是說需要我核准就停，你可以去做其他不需要我核准的研究。」
「等核准的東西堆著」從來不是停止條件；authority gate 擋的是**入圖**，不是**研究**。

閉包的定義：**工作集合裡每一項都到達三種終局之一**——
①packet 已備（取得 pq2 編號等核准）；②誠實 park（帶 trace_status＋trigger）；
③已排入 pq1 佇列（留給 budget 化的排程輪）。工作集合＝前兩段佇列＋**走圖九型的每一筆命中**
（段 4；含原本的 🔴／🟡 缺口、沒人提過的重複節點候選、該重讀的結構讀圖）＋一手文件已具名、
但尚未做四維初判的 onboard 候選。

**這回答「會不會停不下來」：工作集合是有限清單，每項有終局，閉包必然可達**——
不需要靠 loop 間隔或使用者插話來煞車。會讓它看起來無限的只有兩件事：
新 harvest（一天一批，有界）與 decompose 開新題（選題權在使用者，不會自己長）。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.event_watch counters   # fired_unconsumed 只剩假設對照型（lead 型與 pq2 型為 0）
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go       # 候選 0（常規授權類別都已排入 pq1）
& '.venv\Scripts\python.exe' -m engine_b.cli counts          # triaged_go 為 0
& '.venv\Scripts\python.exe' -m engine_b.todo list           # 無 queued／researching 的 dispatch_status
& '.venv\Scripts\python.exe' -m query.graph_walk           # 段 4：九型每一筆命中都已有終局（packet／park／pq1／讀圖已寫）
& '.venv\Scripts\python.exe' -m audit invariants --only QueueSegments   # 每段的數字；分不到段的狀態＝新工作沒有 consumer
& '.venv\Scripts\python.exe' -m webapp closure-gate         # 段5：exit 0＝閉包／1＝還有工作／2＝讀不到
```

⚠ **段 5 的停止條件由 `webapp closure-gate` 回答，不由執行者自稱**（2026-09-10 改）。
`exit 0` 才是閉包；`exit 1` 代表還有可自主推進的檔，**此時不得宣告 noop、不得拉長 loop 間隔、
不得收工**；`exit 2` 是讀不到 artifact，**fail closed 當成沒做完**，不是當成做完。

> **事發（2026-09-09，`git log` 可查）：** 這條原本寫成「到終局檔數在本輪至少 +1」。
> 那一句同時承載**進度下限**（不准開三檔各補一格）與**停止條件**（滿足就算做完）兩種語意——
> L12（一個表示承載兩種語意，下游被迫二選一而兩邊都錯）。執行者讀成後者：
> `23:18→23:28` 把 LITE 做到 ready，`23:33` 就轉去段 4 收工，而段 5 還剩 67 檔。
> 本 skill 開場白寫著「停止條件若能在任意時刻被滿足，它就不是停止條件」——這次是
> **被滿足得太早**，同一個毛病換一個位置復發。

分開之後兩邊各自定規則：

| | 現在是什麼 | 誰執行 |
|---|---|---|
| **停止條件** | `closure-gate` exit 0 | `python -m webapp closure-gate` |
| **進度下限** | 一輪若 0 檔到終局，**必須報告原因**（硬中斷／卡 pq2／卡世界），不得靜默宣告 noop | Step 6 收尾 |
| **深度優先** | 同時只開一檔 | 執行者 |

⚠ **深度優先是「同時開幾檔」的上限（1），不是「一輪做幾檔」的上限（沒有上限）。**
一輪要做到撞上硬中斷為止，能做幾檔做幾檔。把這兩件事混為一談，會讓使用者以為
他得為每一檔說一次「繼續」——那是 68 次，而正確答案是「每個 session 一次」。

某檔確實推不動時（卡 pq2 編號、卡世界），用 `--skip` **顯式**排除並在收尾寫明理由：

```powershell
& '.venv\Scripts\python.exe' -m webapp closure-gate --skip IQE.L --skip AEVA
```

**gate 不會自己去猜哪一檔卡在 pq2**——pq2 歸屬今天只存在於 `todo_pool.json` 的散文標題裡，
去 parse 它就是 L16（分類要跟著資料走，呈現層不得 parse 理由句去猜）禁的那件事。
`--skip` 讓「我判斷它推不動」變成一個留在該輪 commit 裡、可被回頭檢查的宣告。

⚠ **「等財報」那一類已經不需要 `--skip`**（2026-09-12 起）：目標期間（共識 `0y`）**已經結束
但財報還沒公布**時，`alpha/closure.py` 會自己判成第三種終局 `awaiting_report` 並逐檔印出期末與
已過天數。那是機械可判的事實，交給人記得就會漏——實測當天手動只認出 MU 與 6594.T，
偵測器多找出 JBL（才過 12 天）。`--skip` 從此只留給**真的需要人判斷**的兩種：卡 pq2、卡世界。

成績單（Step 6）固定加三個數：到終局檔數（ready＋settled）、有 ready 檔的產業數、
下一檔與它還缺的格。走圖的洞可能因為新節點入圖而增加，**增加不代表退步**，代表發現了新的層。

⚠ **2026-09-22（Phase 0）：原本 `closure-gate` 還印三個估值品質數**（隱含報酬正負分布｜
倍數＝校準倍數的檔數｜有折溢價主張的檔與貢獻）。**整條估值鏈退役**（ROADMAP Phase 0／G3），
三個數一併退役。

⚠ **它們要防的那件事沒有退役：** 68 檔的 blocker 完全同形，意味著最省事的做法是套同一份模板
——而模板化的判斷在 readiness 上看起來跟真的一模一樣（ready 就是 ready）。
接手這個角色的是 Phase 5 的量測（追蹤表三個 power-law 統計量＋來源標籤跟著 lead 走到 outcome）。
**在它落地之前，「衝檔數沒有犧牲品質」沒有機械證據**——不得假裝有（L14-2：gate 本身也要驗）。

⚠ **token 用完不是停止條件，是中斷。** 中斷時必須：
① 所有 in-flight lead 都 checkpoint 在合法狀態（不留 `researching` 懸空）；
② commit ＋ push；③ 回覆裡寫明「已清 N／剩 M」與下一條要做什麼。
續跑的 session 從 Step 0 重讀狀態接手。

⚠ **撞到避讓窗也是中斷，處置完全相同。** 跑到一半 `writer_guard verify` 回 exit 2，
或時間逼近 daily 窗，一律照中斷程序收乾淨後停——**不要「再做完這一條就好」**：
留一個 `researching` 懸空的 lead 給排程去撞，正是本 guard 要防的事。

## Step 5.5 — 什麼時候該中斷（這一條**無法**機器判定，要誠實）

⚠ **先講限制：執行者無法可靠測量自己的剩餘 context。** 寫一個假裝測得到的門檻
（「剩 20% 就停」）比沒有更糟——它看起來像規則，實際是憑感覺再貼一個數字。
2026-09-01 實測：本 skill 上線後兩次中斷都寫成「上下文快到界線」，而 Step 5 只規定了
**怎麼**中斷、沒規定**何時**。那正是本 skill 當初要修的同一個毛病換一個位置復發。

所以判準不是「還剩多少」，是下面**四層**（⓪ 是硬前提，①–③ 才是判準）：

### ⓪ 「剩餘 context 不足」永遠不是停止理由（硬性）

**對話變長時會自動壓縮並帶著摘要繼續，所以「快用完了」根本不是一個真實的邊界。**
不得因為「我判斷剩下的量做不完下一個項目」而收工——那是**預測**，而 ② 要的是**已經發生的事實**。

⚠ 這一條是專門補 ② 的漏洞，不是重複它。2026-09-10 實測：執行者做完段 5 的 TSM 後停下，
理由寫成「下一檔 TSEM 與 TSM 同型，判斷剩餘 context 不足以在同一 session 把它推到終局」。
它**沒有**違反上面那句「不要寫死門檻」（沒有貼任何數字），卻仍然提早收工，
使用者原話：「你判斷 context 不足 但不是都會壓縮喔？」——續跑後同一個 session 又完成了七檔、
發現三個結構性缺陷。**提早停的代價不是少做一點，是使用者要為同一批工作再說一次「繼續」**，
而消滅那件事正是本 skill 的存在理由（開場白：停止條件必須是機器查得出來的）。

判準一句話：**「我覺得快不夠了」不是訊號，「我剛才真的重讀了本 run 已經讀過的東西」才是。**

### ① 邊界規則（硬性，這條最重要）

**只在項目邊界中斷，永不中途。** 一個「項目」＝一張工單／一條 lead／一個入圖包；
項目結束＝狀態 checkpoint 合法 ＋ commit ＋ push。

只要每個項目都這樣收，**中斷點落在哪裡幾乎不影響成本**——續跑的 session 從 Step 0
重讀就接得上。**把中斷成本壓到接近零，比抓對中斷時機容易得多，也可靠得多。**

### ② 降級訊號（**已觀察到**就在下一個邊界停）

任一出現即可。⚠ 四條全部是**已經發生的事實**，不是「我覺得快發生了」——把預測寫進這一格就是繞過 ⓪：

- 需要重讀本 run 早先已經讀過的東西，才想得起現在的狀態
- 開始重新推導本 run 已經有結論的事
- 敘述從「查證後」滑成「我記得剛才」
- 連續兩個項目沒有產生新的 receipt 或 commit

⚠ **降級發生在 context 用完之前。** 等到快用完才停，最後幾個項目其實已經做差了——
所以觸發條件是**品質訊號**，不是剩餘量。這也是為什麼不該追求「把這一輪塞滿」。

### ③ 硬中斷（立即在下一個邊界停，不評估）

- `writer_guard check`／`verify` 回 exit 2
- 時間進入 daily 避讓窗
- 使用者插話
- 呼叫端有給項目上限且已達到（例：`/research-drain 最多做 5 個項目`）

### ④ 撞到機制缺陷時：先分類，再決定「當下修」還是「寫一列」

研究途中會撞到系統自己的缺陷（這是好事，它代表管子真的被走過了）。
載體照 `AGENTS.md`：**開發項寫 [`ROADMAP.md`](../../docs/ROADMAP.md)，不鑄 pq2**。
但「寫哪裡」與「現在做不做」是兩件事，而混為一談的方向是固定的。

⚠ **實測 4 比 0（2026-09-12）**：一輪寫了四列並逐列註明「本輪不自行修」，
使用者只問了一句「可以直接做掉嗎」，四列**全部在同一個 session 內做完了**，
其中一列還直接解開一個使用者早已核准、卻卡著關不掉的 pq2（[542]）。
也就是當時的分類**全錯**，而錯的方向固定偏向「這個我不能碰」——
跟 L16 說的偏向「看起來需要更多研究」是同一個病。

**三個問句，順序不可換：**

1. **這個修法會改變「使用者能核准什麼」嗎？**
   不會 → 它**不是** gate 變更，**即使它住在 gate 的程式裡**。
   實測：入圖完成收據的更正走廊住在 `intake/provenance.py` 的入圖路徑上，
   但它不新增任何寫圖權限——核准照擋，改的只是核准**之後**的簿記。
   當時我憑「它在哪個檔」就判成 gate 變更。**判準是 authority，不是檔名。**
2. **它是放寬、收緊、還是「分開」？**
   「分開」（L12 的處方）**不受放寬的限制**——分開之後兩邊都可以更嚴。
   實測：折溢價計數器我引了程式註解「放寬一個稽核用的計數器要人決定」就停手，
   而正確的修法**根本沒動那個容差**，它只是把兩種語意拆成兩欄。
3. **它動到封閉字彙，或有第二個 owner 要同意嗎？**
   只有這一題成立才是「寫列、不動手」（＝L17-2 的 Z2 檔次）。

⚠ **規模不是 gate，authority 才是。** 四列裡最大的那一列（orphan tracker）動了三個檔、
加五條測試，仍然是一個 session 內做得完的。「這看起來很大」不是停手的理由。

⚠ **反向也要防**：這一段**不授權**動四個人工 gate 本身、不授權寫任何 authority、
不授權改 `AGENTS.md` 的判準句。它只收掉「住在附近就不敢碰」這一類誤判。

⚠ **放行與收緊同時發生**（`AGENTS.md`）：當下修的那一列，**同一個 change 就要附可機械驗證的收緊面**。
上面那四列各自都有一條——沒有歸檔證據就不給走廊／未宣告 derivation 當成主張要人舉證／
未上市公司的 cohort 行為不得改變。**只有放行面的修法不算做完。**

### ⚠ 一個容易漏的危險

**context 被壓縮時，執行者可能不會察覺**，於是拿著摘要當完整狀態繼續做，
而摘要裡的數字是「當時為真」不是「現在為真」。

防法：把 Step 0 的重讀當成**每個項目開始前**的動作，不只是續跑時才做。
`git status --short` ＋ `engine_b.cli counts` ＋ 該項目自己的 receipt——三個都便宜，
而且它們回答的正是「我以為的狀態還成立嗎」。

⚠ **注意方向：壓縮的正確反應是「重讀」，不是「提早停」。** 這兩者很容易被混成一件事——
「壓縮可能讓我拿舊摘要當現況」聽起來像是該停下的理由，但停下並不會讓摘要變準，
重讀才會。⓪ 與這一段是同一枚硬幣：**怕壓縮就多讀一次 repo，不要少做一個項目。**

---

## Step 6 — 收尾：一份批次核准摘要

依 `AGENTS.md` 的收尾義務，最後一則回覆必須有：

- **每個新編號一個決策區塊**，格式是共用的那一份：
  [`skills/daily-brief/SKILL.md`](../daily-brief/SKILL.md)「待核准項目的內容密度」。
  **本 skill 不自己定義格式**——欄位、折行方式、「不含」與「圖影響」兩欄的必填規則都在那裡。
  ⚠ 不得用表格，也不得把欄位用 `｜` 串成一行：使用者在手機上讀，那需要左右滑。
- **decompose 提案直接鑄成 pq2 編號（2026-09-09 起）**：走圖的洞（原覆蓋缺口）只會減不會增——
  走圖（含原 `coverage_gaps`）只能從既有節點往回看，新層唯一產生器是 `system-decompose`。本 skill 每輪收尾
  若本輪的 lead／研究裡出現**需求錨不是 AI capex 也不是人形放量**的實體系統（判準機械：
  錨不在 `config/sector_anchors.json` 各組、且不在圖裡），就用
  `python -m engine_b.cli decompose-propose --system "<一台實體>" --anchor <tech:x> --why "<為什麼是新錨>" --lead <id>`
  鑄一個 `manual` 型編號，讓使用者在批次行裡一起決定；**同時 open ≤2、drop 過沒新 lead 不重生**。
  核准仍逐題、系統不自行開題，decompose gate 不因此放寬。沒有合格候選就寫「本輪無新錨」。
- **最後一行單獨給可複製的批次指令**（如 `341 342 343 go 344 drop`）；**鑄的每個編號同時寫建議**
  （`python -m engine_b.todo recommend <n> --verb go|drop|pending --reason "<go 會讓哪個數字變>"`）——
  daily 短版的 ③ 照抄它組出同一行（2026-10-08 使用者指示；沒寫的編號會列在「沒寫建議」）
- **本輪的否定結果**：哪些研究做完後結論是「不是瓶頸」——這一段不得省略，
  它是這個 skill 最容易被誤讀成「沒產出」的部分
- **本輪寫下的 ROADMAP 列，逐列標檔次**（段 5.5 ④ 的三問結果）：`當下修`（已做完，附驗收數字）／
  `Z2——等你點頭`（動到封閉字彙或第二個 owner，做得完但需要你決定）／`要排程`（等於重寫一個子系統）。
  ⚠ 這是**資訊，不是 `go` 請求**——`AGENTS.md` 的「開發項不主動要求 go」照舊。
  但只寫「本輪不自行修」是**不夠的資訊**：使用者看不出那是「不能碰」還是「來不及」，
  於是他只能反問一句，而 2026-09-12 那次反問之後四列全部當場做完了。
- **剩餘工作量**：清了幾條、剩幾條、下一條是什麼
- **這次為什麼停**：三者擇一寫明——`停止條件成立`（Step 5 三項都過）／
  `硬中斷`（哪一項，見 Step 5.5 ③）／`降級訊號`（哪一個，見 Step 5.5 ②）。
  ⚠ 不得只寫「告一段落」——使用者要能分辨**做完了**、**被打斷**、**做不動了**，
  這三種的下一步完全不同（前者不必再跑，後者該換新 session）。

---

## 單次 vs Loop（2026-09-01 使用者兩次定案後的現行語意）

**預設是單次跑到閉包（Step 5），不需要 loop。** 閉包可達（工作集合有限），
所以「一個段落」就是一次完整的 `/research-drain`；跑完的正確狀態是
「所有能自主做的事都有終局，剩下的全在使用者的核准介面上」。

`/loop` 只是掛機模式——使用者不在場時讓系統跟著兩個外部節奏繼續：
①daily harvest 一天補一批線索；②使用者 `go` 解鎖下一段。兩者都會產生新工作，
但都不是執行速度能改變的。**不要為了「這輪要有產出」而降低終局品質**
（灌 RA、硬塞引用都是 L14/L15 違規）。

- **每輪醒來＝一次完整 Step 0**：writer_guard check、重讀 counts／todo list／drain。
  有未達終局的工作（新 harvest、剛核准的授權項、**或段 5／段 6 還有可推進的缺口**）
  → 做到閉包；⚠ **「佇列空」不等於閉包**——2026-09-01 實測，執行者把前兩段清空
  誤讀成沒事做，睡掉了第三段整批不需核准的研究。
  **真正的 noop 只有一種：`webapp closure-gate` 回 exit 0 且無新 harvest。**
  ⚠ 這一句刻意寫成命令而不是形容詞——2026-09-01 與 2026-09-09 兩次睡太早，
  都是因為「閉包」在當下是執行者的自我判斷（L14：未量測的機制不得享有默認信任）。
- **一輪＝做到撞上硬中斷為止，不是做到一檔。** 實測一檔約 7–10 分鐘、3 個 commit
  （2026-09-09 的 SOI.PA 與 LITE），所以一輪內通常應該有多檔到終局。
  **一輪只推進一檔還宣告收工，是本節要防的失敗**。
- **不自行開題**：decompose 選題權在使用者；閉包成立時提案（Step 6 固定行）而不是自己開。
- **避讓窗與中斷語意照舊**（Step 5／5.5）：撞 daily 窗、guard exit 2、降級訊號，
  一律邊界收乾淨後停；loop 的下一輪從 Step 0 重讀接手，不依賴上一輪記憶。
- **建議醒頻**：**`closure-gate` 回 exit 1 時，下一輪立刻排（60 秒）**——還有工作卻睡 20 分鐘
  就是在浪費 loop。只有 exit 0（閉包成立）才回到 20–30 分鐘的守候節奏，連續 noop 時再拉長。
  每輪收尾摘要照 Step 6 出，含 decompose 題目提案行。
- **產出待核准編號時必須推播（2026-09-01 使用者定案）**：loop 輪的收尾摘要埋在
  背景輪的捲動輸出裡，使用者不在終端機前就等於沒送達——實測使用者說「我沒看到你給我
  批的訊息」，而批次行其實每輪都在，只是在長訊息尾巴。修法：本輪若鑄了新的待核准編號
  （或閉包卡在既有編號上超過一輪），收尾時**另發一則 PushNotification**，內容就是
  可直接複製的批次行（如 `380 382 383 go`）＋一句這批是什麼。noop 輪不推播——
  推播的成本是打斷，只在「有事等使用者」時花。
- **收尾訊息的順序（2026-09-01 手機截圖實證）**：緊貼 `ScheduleWakeup` 之前的長訊息
  在手機 remote 端會被摺疊或不渲染——實測整份含批次行的摘要在手機上消失，而中間的
  短狀態訊息全部正常顯示。因此 Step 6 詳細摘要必須放在**最後一批工具呼叫之前**輸出；
  排 wakeup 前的最後一則文字＝**fenced code block 批次行（一鍵複製）＋每個編號一行
  TLDR**（2026-09-01 使用者兩次指正合併：不用標題放大；每個數字要配一句話讓使用者
  不回讀長摘要就知道在批什麼）。格式：
  ```
  396 402 go
  ```
  - 396：Lynas 美國政府 LOI 一手化（第二主權客戶承諾）
  - 402：Aehr 10-K 升級（CPO 逐字＋集中度趨勢）
  長版詳細摘要仍放在最後一批工具呼叫之前。

## 與其他 skill 的分工

| 情況 | 用哪個 |
|---|---|
| 每天一份 action-first 摘要，有 budget cap | `daily-brief` |
| **一次把能做的做到底，無 cap、中途不報告** | **本 skill** |
| 單條線索從進場到入庫 | `lead-intake` |
| 追一手 | `source-trace` |
| 產生圖裡沒有的新層（選題由使用者） | `system-decompose` |
| 現在該投哪一檔 | `alpha-status` |

⚠ **本 skill 不取代 daily-brief。** daily 回答「今天要不要動作」，
本 skill 回答「把積欠的研究一次還完」。兩者的 budget 語意相反，不要混用。
