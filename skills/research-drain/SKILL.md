---
name: research-drain
description: >
  把「目前能做的研究」一次做到底：先清已核准的 pq1 工單，再依 drain 排序清 triaged_go
  線索，最後補圖裡的覆蓋缺口與已具名候選的初判。中途不報告、不等使用者；撞到 authority
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

**exit 2 就不要開始。** 三種不安全：現在落在 daily 避讓窗內、**這段 run 會跨進窗內**
（起跑時安全不代表跑到一半安全，而跑到一半撞上最難收拾）、working tree 不乾淨
（可能有另一個 writer 在跑，或上一輪沒收乾淨）。

把回傳的 `head` 記下來，之後每個里程碑用它比對：

```powershell
& '.venv\Scripts\python.exe' scripts\writer_guard.py verify --since <開跑時的 HEAD>
```

exit 2 代表期間排程側提交過共用檔——**立刻重讀 `todo_pool.json`／`pending_leads.json`
再繼續，不得沿用記憶中的狀態**。

⚠ **這是單向避讓不是互斥鎖**：只有互動側會檢查。真正的雙向鎖要動 daily 的 sandbox
allowlist（見 ROADMAP）。單向仍然有效，因為 daily 有界且時間可預測——讓開就不會撞。

接著讀狀態：

```powershell
git status --short
& '.venv\Scripts\python.exe' -m engine_b.cli counts
& '.venv\Scripts\python.exe' -m engine_b.todo list
& '.venv\Scripts\python.exe' -m engine_b.cli drain
```

⚠ **這一步在續跑時同樣要做。** token 用完後的新 session 必須能只靠 repo 狀態接手——
`git status --short`、`todo_pool.json`、`counts`、各 action／decision receipt——
**不得依賴前一個 session 的自然語言摘要**（`AGENTS.md` 雙代理交接契約）。

---

## Step 1 — 工作順序：已核准的先做，其餘用既有排序

**順序不是自由心證，三段固定：**

1. **所有「使用者已授權、還沒做完」的項目** — 放著不動是本 skill 要修的那個 bug。
   **永遠排第一，不論它們看起來多無聊。** 包含兩類，同級處理：
   - **`pq1 進行中` 的工單**（`dispatch_status` 為 queued／researching）
   - **`manual` 型已授權項**（`todo list` 的 manual 段，hint 註明使用者指示者）——
     ⚠ 2026-09-01 實測：[325] 授權後一天沒被排入，因為當時本段只寫了工單。
     **佇列定義漏掉的授權項不會自己出現**（L16 的形狀：分類存在，沒送到消費端手上）。
2. **`triaged_go` 線索** — 順序**只認 `engine_b.cli drain` 的輸出**。
   ⚠ 不得另建排序：`engine_b/priority.py` 是 pq1 排序的唯一權威，
   「我覺得這條比較有趣」正是它要防的東西。
3. **圖的覆蓋缺口** — 只有前兩段清空後才做。這一段沒有既有排序，是唯一需要判斷的地方，
   判準見下。

### 第 3 段的排序判準（唯一需要判斷之處）

依序問，先滿足者先做：

1. **答案會改變候選集合嗎？** 會 → 最先。`coverage_gaps` 的 🔴 研究缺口（零供應商節點）
   多半屬此。
2. **是不是同一次沒做完的拆解殘骸？** 是 → 接著做。層的名字已經在那裡、只缺供應商，
   成本最低（例：CPO stack 的 `scale_up_cpo`／`tfln_platform`／`wdm_laser_16ch` 那一群）。
3. **缺的是「值」還是「證據」？** 缺值優先。**沒填 `substitutability` 的邊在排序裡是隱形的**，
   而證據弱的邊至少看得見——隱形比薄弱危險。
4. **🟡 建模待補**（已研究過、只差接邊）排最後：它的下一步是補邊走入圖，不是重新研究。

---

## Step 1.5 — 工單：寫 assessment **之前**先查該軸接受什麼

```powershell
& '.venv\Scripts\python.exe' -m decision_lab references <cohort_id> [--assessment <file>]
```

**這一步不是可選的。** 每個信心軸只接受特定 authority，寫錯了會得到
`assessment_context_mismatch`——而那個碼看起來像「證據不足」，實際上是「引用對不上」，
兩者的處置完全相反。

它會直接告訴你三件事：
- 每軸**接受哪些 authority**（例：`financial_resilience` 只吃 `engine_c_financial`／
  `engine_c_manual`，**不收 `market`**；`valuation_payoff` 只吃 `engine_c_valuation`／
  `fx`／`market`，**不收 `engine_c_financial`**）
- 這份 frozen context 裡**有哪些 key 可以引用**（整串複製，字面必須完全一致）
- 帶 `--assessment` 時逐條標出哪個 ref 不合格、為什麼

⚠ **最重要的是它會分辨兩種完全不同的失敗：**

| 工具說什麼 | 意義 | 處置 |
|---|---|---|
| `✗ 解析不到任何 key` | 引用寫錯（常見：把散文當 ref） | 改成 index 裡的 key |
| `✗ authority 是 X，這一軸不接受` | 引用了對的東西給錯的軸 | 換一個該軸吃的 ref |
| **`這一軸沒有任何合格引用`** | **上游根本沒產出該 authority** | **改引用救不了**——需要補上游資料，多半是 Engine C 人工觀測（使用者 gate） |

第三種是研究做不完的：2026-08-31 實測 Schaeffler／Himax／Lynas 三個 cohort 的
`commercial_maturity` 全部零合格引用，因為它只吃 `engine_c_backlog`／`engine_c_customer`，
而那兩筆是財務核驗清單上的人工待填項。**這種軸誠實留 `unknown` 並把缺口寫進
`missing_data`，不得硬塞其他 ref**——那就是讓引用去尋找能通過的權威（L15 的
authority laundering）。

**效率提示：** 同一個 authority 缺口常跨多個 cohort。逐張工單各撞一次是浪費——
先把幾張的 `references` 一起查完，把同類缺口打包成一批 Engine C 觀測提案給使用者
一次核准，比逐張跑有效得多。

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

工單（decision gap）另有第三種終局：研究完成後可 `reassess` 產生新 decision receipt，
再以 `todo work <n> --to completed --receipt decision:<id>` 結案。

---

## Step 3 — 撞到這些就停下來，不自行放寬

**硬 gate（永遠不自動）：**

- **入圖**（`apply_research_action`）——包含隨之而來的 registry 增列
- **Engine C 寫入**（manual observation ledger）
- **thesis revise／retire**
- **live choice／fill**
- **decompose 選題**——`system-decompose` 明訂系統由使用者指定，排程不得自行挑題
- **付費取得**（訂閱、報告購買）——必須另列 exact 金額與方案

**這些不是停止，是繼續：** 產出入圖包、park 線索、跑工單、註冊新研究題目、
確定性維護（凍結 context 過期 → `reassess`）。撞到硬 gate 時，把該項掛成 pq2 編號後
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
執行者在 `triaged_go=0`＋工單清空時就收工睡覺，而第三段（覆蓋缺口）還有 15 個 🔴、
外加一批已具名未初判的 onboard 候選——**那些全是不需要使用者核准的研究**。
使用者原話：「不是說需要我核准就停，你可以去做其他不需要我核准的研究。」
「等核准的東西堆著」從來不是停止條件；authority gate 擋的是**入圖**，不是**研究**。

閉包的定義：**工作集合裡每一項都到達三種終局之一**——
①packet 已備（取得 pq2 編號等核准）；②誠實 park（帶 trace_status＋trigger）；
③已排入 pq1 佇列（留給 budget 化的排程輪）。工作集合＝前兩段佇列＋第三段的
🔴／🟡 缺口＋一手文件已具名、但尚未做四維初判的 onboard 候選。

**這回答「會不會停不下來」：工作集合是有限清單，每項有終局，閉包必然可達**——
不需要靠 loop 間隔或使用者插話來煞車。會讓它看起來無限的只有兩件事：
新 harvest（一天一批，有界）與 decompose 開新題（選題權在使用者，不會自己長）。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli counts          # triaged_go 為 0
& '.venv\Scripts\python.exe' -m engine_b.todo list           # 無 queued／researching 的 dispatch_status
& '.venv\Scripts\python.exe' -m query.coverage_gaps          # 每個 🔴 都已有對應終局（packet／park／pq1）
```

前兩個是硬條件。第三個的判準是「這一輪有沒有真的往前推」——覆蓋缺口可能因為
新節點入圖而增加，**增加不代表退步**，代表發現了新的層。

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

所以判準不是「還剩多少」，是下面三層：

### ① 邊界規則（硬性，這條最重要）

**只在項目邊界中斷，永不中途。** 一個「項目」＝一張工單／一條 lead／一個入圖包；
項目結束＝狀態 checkpoint 合法 ＋ commit ＋ push。

只要每個項目都這樣收，**中斷點落在哪裡幾乎不影響成本**——續跑的 session 從 Step 0
重讀就接得上。**把中斷成本壓到接近零，比抓對中斷時機容易得多，也可靠得多。**

### ② 降級訊號（觀察到就在**下一個邊界**停）

任一出現即可：

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

### ⚠ 一個容易漏的危險

**context 被壓縮時，執行者可能不會察覺**，於是拿著摘要當完整狀態繼續做，
而摘要裡的數字是「當時為真」不是「現在為真」。

防法：把 Step 0 的重讀當成**每個項目開始前**的動作，不只是續跑時才做。
`git status --short` ＋ `engine_b.cli counts` ＋ 該項目自己的 receipt——三個都便宜，
而且它們回答的正是「我以為的狀態還成立嗎」。

---

## Step 6 — 收尾：一份批次核准摘要

依 `AGENTS.md` 的收尾義務，最後一則回覆必須有：

- **建議摘要表**：每個新編號＋建議動詞＋一句理由
- **「建議下一個 decompose 題目」固定一行**：pane 3（覆蓋缺口）只會減不會增——
  `coverage_gaps` 只能從既有節點往回看，新層唯一產生器是 `system-decompose` 且選題權
  在使用者。本 skill 每輪收尾**提案一個題目**（從 🔴 真瓶頸類或既有拆解殘骸推導），
  使用者順手回一行就補貨；**系統只提案、不自行開題**，decompose gate 不因此放寬
- **最後一行單獨給可複製的批次指令**（如 `341 342 343 go 344 drop`）
- **本輪的否定結果**：哪些研究做完後結論是「不是瓶頸」——這一段不得省略，
  它是這個 skill 最容易被誤讀成「沒產出」的部分
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
  有未達終局的工作（新 harvest、剛核准的授權項、**或第三段還有可推進的缺口**）
  → 做到閉包；⚠ **「佇列空」不等於閉包**——2026-09-01 實測，執行者把前兩段清空
  誤讀成沒事做，睡掉了第三段整批不需核准的研究。真正的 noop 只有一種：
  閉包成立且無新 harvest。
- **不自行開題**：decompose 選題權在使用者；閉包成立時提案（Step 6 固定行）而不是自己開。
- **避讓窗與中斷語意照舊**（Step 5／5.5）：撞 daily 窗、guard exit 2、降級訊號，
  一律邊界收乾淨後停；loop 的下一輪從 Step 0 重讀接手，不依賴上一輪記憶。
- **建議醒頻**：閉包狀態下 20–30 分鐘一次即可；連續 noop 時拉長。
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
  排 wakeup 前的最後一則文字只留**一行**：批次指令本身，**固定用 fenced code block**
  （app 端有一鍵複製按鈕），不得改用標題或粗體放大（2026-09-01 使用者指正）。
  長內容靠前、單行殿後，兩者都送達。

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
