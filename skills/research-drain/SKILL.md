---
name: research-drain
description: >
  把「目前能做的研究」一次做到底：先清已核准的 pq1 工單，再依 drain 排序清 triaged_go
  線索，最後補圖裡的覆蓋缺口。中途不報告、不等使用者，只在全部清空或撞到 authority gate
  時才回來，並用一份批次核准摘要收尾。當使用者說「清工單」「把 pq1 清掉」「你能做的全部
  做掉」「一路挖到沒東西做」「最後我一次核准」時使用。
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

1. **`pq1 進行中` 的工單（`dispatch_status` 為 queued／researching）** — 使用者早就 `go` 過了，
   放著不動是本 skill 要修的那個 bug。**永遠排第一，不論它們看起來多無聊。**
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
| **誠實 park** | 追源未果／被一手否定／只屬 Engine C 時變觀測／沒有唯一 focus | `advance parked` ＋ 完整 trace refs |

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

**三個都成立才算做完：**

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli counts          # triaged_go 為 0
& '.venv\Scripts\python.exe' -m engine_b.todo list           # 無 queued／researching 的 dispatch_status
& '.venv\Scripts\python.exe' -m query.coverage_gaps          # 🔴 研究缺口不再下降（連兩輪同數）
```

前兩個是硬條件。第三個是軟條件——覆蓋缺口可能因為新節點入圖而增加，
**增加不代表退步**，代表發現了新的層；判準是「這一輪有沒有真的往前推」。

⚠ **token 用完不是停止條件，是中斷。** 中斷時必須：
① 所有 in-flight lead 都 checkpoint 在合法狀態（不留 `researching` 懸空）；
② commit ＋ push；③ 回覆裡寫明「已清 N／剩 M」與下一條要做什麼。
續跑的 session 從 Step 0 重讀狀態接手。

⚠ **撞到避讓窗也是中斷，處置完全相同。** 跑到一半 `writer_guard verify` 回 exit 2，
或時間逼近 daily 窗，一律照中斷程序收乾淨後停——**不要「再做完這一條就好」**：
留一個 `researching` 懸空的 lead 給排程去撞，正是本 guard 要防的事。

---

## Step 6 — 收尾：一份批次核准摘要

依 `AGENTS.md` 的收尾義務，最後一則回覆必須有：

- **建議摘要表**：每個新編號＋建議動詞＋一句理由
- **最後一行單獨給可複製的批次指令**（如 `341 342 343 go 344 drop`）
- **本輪的否定結果**：哪些研究做完後結論是「不是瓶頸」——這一段不得省略，
  它是這個 skill 最容易被誤讀成「沒產出」的部分
- **剩餘工作量**：清了幾條、剩幾條、下一條是什麼

---

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
