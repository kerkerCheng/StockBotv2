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

把回傳的 `head` 記下來，之後每個里程碑用它比對：

```powershell
& '.venv\Scripts\python.exe' scripts\writer_guard.py verify --since <開跑時的 HEAD>
```

exit 2 代表期間排程側提交過共用檔——**立刻重讀 `todo_pool.json`／`pending_leads.json`
再繼續，不得沿用記憶中的狀態**。

⚠ **這是單向避讓不是互斥鎖**：只有互動側會檢查。真正的雙向鎖要動 daily 的 sandbox
allowlist（見 ROADMAP）。單向仍然有效，因為 daily 有界且時間可預測——讓開就不會撞。

接著**先清機械段，再讀狀態**（2026-09-09 起；段序定義見 `engine_b/queue_segments.py`）：

```powershell
git status --short
& '.venv\Scripts\python.exe' -m engine_b.cli consume-fired          # 段 1：fired 的追源 watch 排回 pq1（零 token）
& '.venv\Scripts\python.exe' -m engine_b.todo sync                  # 段 1 的 pq2 型翻醒＋同步待辦池
& '.venv\Scripts\python.exe' -m engine_b.todo reassess-stale --run  # 段 2：只因 context 過期而 REVIEW 的，reassess 後結案
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

1. **所有「使用者已授權、還沒做完」的項目** — 放著不動是本 skill 要修的那個 bug。
   **永遠排第一，不論它們看起來多無聊。** 包含兩類，同級處理：
   - **`pq1 進行中` 的工單**（`dispatch_status` 為 queued／researching）
   - **`manual` 型已授權項**（`todo list` 的 manual 段，hint 註明使用者指示者）——
     ⚠ 2026-09-01 實測：[325] 授權後一天沒被排入，因為當時本段只寫了工單。
     **佇列定義漏掉的授權項不會自己出現**（L16 的形狀：分類存在，沒送到消費端手上）。
2. **`triaged_go` 線索** — 順序**只認 `engine_b.cli drain` 的輸出**。
   ⚠ 不得另建排序：`engine_b/priority.py` 是 pq1 排序的唯一權威，
   「我覺得這條比較有趣」正是它要防的東西。
3. **每檔閉環（段 5，2026-09-09 起）** — 前兩段清空後、覆蓋缺口之前。工單不是自己列的：
   `drain` 首行的「段5 每檔閉環」一行與 `python -m webapp status` 的「每檔閉環」段，都由
   `alpha/closure.py` 從 analyst view artifact 的 `readiness.blocker_details` 照抄（每格帶
   `absence_kind`／`settled`）。**下一檔選誰不是自由心證**——`closure.NEXT_PICK_RULE` 七條依序比：
   使用者沒有明示 defer → 有同期 EPS 共識 → forward EPS 為正（0y 與 +1y 同時為正）
   → 產業能加一（所屬產業尚無 ready 檔）→ 瓶頸排序名次 → 已有基期觀測 → ticker。
   ⚠ 第一條是**使用者的明示指示**（pq2 有未結案的 `deferred_at`），所以排在四條研究判準之前；
   它往後排、**不過濾**——藏起來會讓「沒做」與「不存在」同形。
   ⚠ 倒數第二條的成本維度相反，**只破平手**：前四條的相對順序一格都沒動，它只在四條全部同分時
   才說話（2026-09-11 實測：59 檔未到終局，57 檔落在 3 個前四條同分的群組裡——原本真正在決定
   順序的是 ticker 字典序）。
   **深度優先**：第 N 檔未到終局不開第 N+1 檔，除非它卡在 pq2 或世界。終局三種：ready／
   剩餘 blocker 全部 settled／全部掛在 pq2 編號上。每一格的路（判準機械，見 `alpha/absence.py`）：
   - `not_yet_recorded`／`upstream_unavailable` 的基期實績、指引 → 抓一手財報寫 mechanical 觀測（不碰 gate）
   - 營運假設、倍數、horizon、判斷檔 → session 判斷寫 ledger，evidence_refs 必須解析得到；倍數依
     `AGENTS.md`「隱含報酬的兩個桿」預設校準倍數，折價要指得出證據
   - 客戶端承諾、獨立來源 → source-trace，可能結成 RA packet（入圖仍是 pq2）
   - `provider_missing` → 換來源，否則提案 Abstention（pq2，因為它把這格從工單上拿掉）
   - `method_not_applicable`（虧損）→ 留給 ROADMAP P6，不硬做
   - 判讀型 Engine C 觀測（backlog、客戶集中）→ 打包觀測提案（pq2）；同類缺口跨多檔就打包成一批
   每消一格 `python -m webapp materialize <TICKER>` 一次，讓下一格的判斷讀到新狀態。
4. **圖的覆蓋缺口** — 只有前三段清空後才做。這一段沒有既有排序，是唯一需要判斷的地方，
   判準見下。

### 第 4 段（覆蓋缺口）的排序判準（唯一需要判斷之處）

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
& '.venv\Scripts\python.exe' -m engine_b.event_watch counters   # fired_unconsumed 只剩假設對照型（lead 型與 pq2 型為 0）
& '.venv\Scripts\python.exe' -m engine_b.todo reassess-stale    # 候選 0
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go       # 候選 0（常規授權類別都已排入 pq1）
& '.venv\Scripts\python.exe' -m engine_b.cli counts          # triaged_go 為 0
& '.venv\Scripts\python.exe' -m engine_b.todo list           # 無 queued／researching 的 dispatch_status
& '.venv\Scripts\python.exe' -m query.coverage_gaps          # 每個 🔴 都已有對應終局（packet／park／pq1）
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

成績單（Step 6）固定加三個數：到終局檔數（ready＋settled）、有 ready 檔的產業數、
下一檔與它還缺的格。覆蓋缺口可能因為新節點入圖而增加，**增加不代表退步**，代表發現了新的層。

**另外三個品質數由 `closure-gate` 自己印出來，照抄進成績單**（2026-09-10 起）：
隱含報酬正負分布｜倍數＝校準倍數的檔數｜有折溢價主張的檔與各自的貢獻。

⚠ **這三個數是「衝檔數沒有犧牲品質」的唯一證據。** 68 檔的 blocker 完全同形，意味著最省事的
做法是套同一份模板——而模板化的判斷在 readiness 上看起來跟真的一模一樣（ready 就是 ready）。
它們掛在 closure-gate 上而不是另開一支命令，是因為每輪本來就要跑它：**計數器要自己出現，
不能靠人記得去查**（L14）。有折溢價主張的每一筆都必須指得出證據（`AGENTS.md`「隱含報酬的
兩個桿」）；全負時要先分辨「倍數貢獻接近 0 ＝市場太貴」與「負值大半來自倍數折價 ＝方法偏空」，
**在分得出這兩者之前不要把「全負」讀成結論**。

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
- **decompose 提案直接鑄成 pq2 編號（2026-09-09 起）**：覆蓋缺口只會減不會增——
  `coverage_gaps` 只能從既有節點往回看，新層唯一產生器是 `system-decompose`。本 skill 每輪收尾
  若本輪的 lead／研究裡出現**需求錨不是 AI capex 也不是人形放量**的實體系統（判準機械：
  錨不在 `config/sector_anchors.json` 各組、且不在圖裡），就用
  `python -m engine_b.cli decompose-propose --system "<一台實體>" --anchor <tech:x> --why "<為什麼是新錨>" --lead <id>`
  鑄一個 `manual` 型編號，讓使用者在批次行裡一起決定；**同時 open ≤2、drop 過沒新 lead 不重生**。
  核准仍逐題、系統不自行開題，decompose gate 不因此放寬。沒有合格候選就寫「本輪無新錨」。
- **最後一行單獨給可複製的批次指令**（如 `341 342 343 go 344 drop`）
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
