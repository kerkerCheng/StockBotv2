---
name: alpha-status
description: >
  Alpha 現況總覽：回答「圖的結構現在長什麼樣」「該去補誰的證據」「哪裡還是空白」「已投的
  部位怎麼樣」四題。當使用者說「alpha status」「alpha 現況」「瓶頸排序」「現在該投什麼」
  「我們缺什麼」「哪裡還沒挖」「挖到哪了」時使用。四個 pane 的持久內容自 2026-09-08 起住 APP，daily-brief 只印較昨變動；本 skill 仍是「完整四 pane」的權威，隨叫隨到。
  ⚠ **不輸出跨檔全序、不輸出首選**（2026-09-22 Phase 0）：「該買誰」是人讀敘事的判斷，
  系統只給結構與候選狀態。**純消費端：只讀既有 authority 的輸出，一個數字都不自己重算**——
  它報告排程實際做了什麼，不是自己另算一份。不入圖、不改 thesis、不動資本，所有人工 gate 不受影響。
  觸發詞：alpha status、alpha 現況、瓶頸排序、現在該投什麼、缺什麼、哪裡還沒挖。
---

# Alpha Status Skill（v1.1）

> ⚠ **Scope note（2026-09-22 更新）：本檔任何句子與 `AGENTS.md` 衝突時以 `AGENTS.md` 為準。**
> 方向是「圖是中心」（決定紀錄 [`2026-09-22-graph-first-direction-decision.md`](../../docs/brainstorms/2026-09-22-graph-first-direction-decision.md) G1–G12）：
> **跨檔排序與首選已於 Phase 0 退役**——它們讓研究火力去補格子過 filter（L19）。
> 取代它們的是：pane 1 印**結構表**（哪條邊薄、走不走得到需求錨）與**候選狀態板**
> （五值封閉字彙，Phase 3 落地；在那之前印「未落地」）；追蹤表主統計量是三個 power-law
> 統計量（D15，已落地）；alpha 格只觀測不設目標（D1）。

## 定位一句話

**把「結構長什麼樣／該挖什麼／哪裡是空白／已投的怎麼樣」四題，一次答完。**
⚠ **不排順序、不挑首選**——`AGENTS.md`「消費契約：圖是中心」明文禁止跨檔全序與首選。

系統只負責使用者自己做不動的事：**哪些邊緣公司值得看**、**有什麼新事件**、
**賭對了值多少、判斷錯了值多少**、**哪個管道與特徵產出贏家**。
買多少、什麼時候買由使用者決定（`AGENTS.md`「消費契約：圖是中心」）。

---

## 鐵律一：純消費端，不自己重算

本 skill **不得**自行查圖、自行計算分數、或另建任何排名。它只跑既有指令並轉述。

理由：若它自己算一份，它報告的現況就會與**排程實際做的**不同，使用者無從分辨
「我看到的」與「系統做的」是不是同一件事——這正是 L13（驗收要驗下游消費者手上的東西）
要防的。**自己算等於改自己的考卷。**

| 要回答的 | 唯一權威 | 指令 |
|---|---|---|
| 結構長什麼樣（哪條邊薄、走不走得到錨） | `query/bottleneck.py` 的逐邊 rows | `python -m query.bottleneck` |
| 哪裡是空白、該去研究的洞 | `query/graph_walk.py`（第 7／8 型沿用 `query/coverage_gaps.py` 的分桶） | `python -m query.graph_walk` |
| 覆蓋厚薄（市值／分析師家數） | Engine C `financial_snapshots`／`consensus_coverage_observations` | 見 §pane 1 |
| 候選狀態（可開／缺 X／已定價等回落／不要／已持有） | narrative ledger 的 `candidate_state` | **Phase 3 才落地；在那之前印「未落地」** |
| 部位與計數器 | APP 的 `positions` state artifact | `python -m webapp status`／`python -m crons.heartbeat` 段 4 |
| 注意力佇列現況 | `engine_b/priority.py` 的分類 | `python -m engine_b.cli drain` |

⚠ **這張表 2026-09-22 少了兩列**：「現在能投什麼」（可行動排序）與「股價已經定價了什麼」
（`alpha_expectation_gap.py`）。前者是跨檔排序、後者是估值鏈，兩者都在 Phase 0 退役。
**沒有等價替代品**：「該買誰」改由人讀敘事決定，「已定價嗎」改由財務三題的第二題回答
（主參照是自己的歷史、不設門檻，Phase 3 落地）。

---

## 鐵律二：輸出前的自檢——這個數字會隨我們多讀一份文件而上升嗎？

**會 → 它測的是研究量，不是世界的樣子。** 要嘛不呈現，要嘛必須同時呈現分母與「這是研究
深度的函數」的但書。

已知會失焦、**不得單獨用作瓶頸性證據**的三項（`AGENTS.md` 已明訂禁用）：

- **`evidence` 等級**——最高級要靠研究找到客戶端文件才拿得到，預設每條邊都是 `self_reported`
- **同一 chokepoint 的供應商計數**——反映我們研究了幾家，不是世界上有幾家
- **`documents` 計數**——`bottleneck.py` 已排除

**客戶端資本承諾不會隨閱讀量上升**（離散事件，要嘛發生要嘛沒有），所以它是四維度裡最可靠的。

---

## Pane 1 — 結構長什麼樣 ＋ 候選狀態

⚠ **不輸出有序清單、不輸出首選、不回答「現在要加碼哪一檔」。**
2026-09-22（Phase 0／G1、L19）：原文寫「必須輸出有序清單與明確首選……違反即視為未完成」，
那句話讓研究火力去補格子把某一檔推上第一名。**「該買誰」是人讀敘事的判斷，不是本 skill 的產出。**

這一 pane 出兩塊：

**(a) 結構表** — 跑 `python -m query.bottleneck`，逐邊照抄：證據等級、`substitutability`、
`sole_source`、`qualification_status`、自報／外部印證、走不走得到需求錨、`anchor_gaps`，
以及母體定義排除的列與理由（INV-3：input／accepted／excluded／reasons 四個數都要有；
2026-09-23 起**沒有門檻**——`substitutability` 未填或很低的邊都在表上，各自帶著自己的值）。
**照抄順序即可，不得宣稱那是優先序**；`demand_anchor` 為空的列不是候選，但要列出來並說明。

**(b) 候選狀態板** — 封閉字彙五值：可開／缺 X／已定價等回落／不要／已持有。
**Phase 3 才落地**；在那之前這一塊照實印「候選狀態板未落地（`not_yet_recorded`）」，
**不得用結構表的前幾名冒充它**。「可開」是每檔各自過的 filter 不是分數，可同時多檔；
**可開為零就零，不得為了非空放寬條件**。

覆蓋厚薄（市值／分析師家數）補在結構表旁邊：

```powershell
& '.venv\Scripts\python.exe' scripts\alpha_purity_snapshot.py --format markdown --tickers <結構表裡的 tickers>
```

這是正式的唯讀 consumer：它從 active Engine C authority 讀最新 `financial_snapshots` 與
`consensus_coverage_observations`，依 `identity/currency.py`＋`config/currency_units.json` 把 GBp 等
minor quote unit 換回結算幣別後輸出市值。**本 skill 只轉述結果，不再自己乘。** 不同結算幣別
沒有做 FX，仍不得直接當成同一尺度排序；`manual_required` 是未知，不得寫成 0。

此入口屬 Daily 的 exact outside-sandbox rule。若回 `private_acl_verification_unavailable`，意思是目前
執行環境無法執行 owner-only ACL 驗證、所以 fail closed，**不等於 ACL 不合格**；不得再以 ad-hoc
SQL 繞過。真正的 `private_storage_boundary_rejected` 才是 storage boundary 拒絕。

### 第 5 塊：~~股價已經定價了什麼~~（2026-09-22 退役）

原本必附 `scripts/alpha_expectation_gap.py`：市場隱含成長 vs 分析師估、誰比較高。
**整條估值鏈在 Phase 0 退役**（ROADMAP Phase 0／G3），腳本本身在批 2 刪除。

接手它的是**財務三題的第二題「已定價嗎」**（`AGENTS.md`「財務只回答三個是非題」）：
主參照是**自己的歷史**（EV/S 或虧損期 P/S 的三年百分位）、主題籃子只當脈絡、**不設門檻**，
敘事那一句必須引用稽核區的數字。三題 Phase 3 落地；在那之前這一塊印「未落地」，
**不得自己算一個估值數字補上**。

⚠ 原文記載的那條 lesson 仍然成立，換個主詞照用：Phase 4a 把欄位算了出來，
但六個面向使用者的 surface 引用次數全是 0——**驗收要驗使用者看得到，不是欄位算得出來**（L13）。

### 第 6 塊：單檔 Alpha Card（canonical read model，2026-09-05 新增；隨叫隨到）

```powershell
& '.venv\Scripts\python.exe' -m briefing alpha-card <TICKER>            # 完整卡
& '.venv\Scripts\python.exe' -m briefing alpha-card <TICKER> --format json
```

使用者問「這一檔到底知道什麼、還不知道什麼」時用它，不要自己從 packet／圖／Engine C 拼。
它是 `briefing/alpha_view/` 的 read model：每一格都帶 **status**（有／部分／過期／缺料／
尚未建模／需複查／已失效／不適用）與 **basis**（確定性規則／觀測值／粗略代理／session 判斷／
散文／結構推論／**投資人政策**）。
**本 skill 只轉述，四條不得改寫：**（a）`not_modeled`（系統**沒有這個能力**）就說「尚未建模」，
`missing`（有能力、這檔沒資料）就說「缺料」＋原因——**兩者不得互換**，也不得用 Q 分數、賣方
目標價或散文補；（b）`stale` 的 session 判斷要明說「判斷是對舊 context 做的」；
（c）`heuristic_proxy` 不得寫成「模型」；（d）~~`entry_logic` 的 `meets_analytical_hurdle`~~
——進場邏輯（`alpha/entry`）已於 2026-09-22 Phase 0 退役（73 檔全 missing，從未用過）；
**進場靠判斷，出場靠 disproof**，系統不再有任何「門檻價」的概念。
Daily 的「Alpha Card 摘要」區是同一份 view 的一列精簡版。

⚠ **哪些 section 是 `not_modeled` 會隨開發而變**（而 2026-09-22 起會**往回變**：
估值、隱含報酬、進場邏輯、多年橋整批退役，它們不是「還沒建」而是「刻意不再有」）
——**不要在本檔維護那份清單**，
每次直接問 view：
`python -m briefing alpha-card <T> --format json | python -c "import json,sys;print({k:v['status'] for k,v in json.load(sys.stdin)['capability_map'].items()})"`

### 第 6b 塊：單檔 Analyst View（消費端投影，2026-09-07 Step 3.5 新增）

```powershell
& '.venv\Scripts\python.exe' -m briefing analyst-view <TICKER>
```

**使用者問「我該怎麼看這一檔」時用它；問「系統對這一檔知道什麼、缺什麼」時才用 `alpha-card`。**
同一份 read model，差別在排列方式：`alpha-card` 依 section 編號，`analyst-view` 依消費者問句
（短評 → 我們相信什麼、憑什麼 → 什麼會推翻它 → 稽核區的數字）。它一個數字都不重算。

**轉述時再多守一條：**（e）**首屏的單位是句不是格**（`AGENTS.md`「APP」）——第一層短評、
第二層論證、第三層才是格；沒寫短評就印「還沒寫短評」，**不得用任何數字補**。
⚠ 2026-09-22：原文寫的問句序列（頭條隱含報酬 → 市場預測 → 差異 → optional entry threshold）
整條隨估值鏈與進場邏輯退役。
（f）`readiness` 的三態（`ready`／`ready_with_flags`／`blocked`）只描述**核心四段**讀不讀得成，
**不是**可不可以買的信號，也不是 Engine D 的 `research_status`。

### 四維度（`AGENTS.md` 為唯一權威，此處只是操作提示）

1. **瓶頸地位** — `substitutability` 4–5／5、`sole_source`、距需求端跳數
2. **需求錨點** — 資金在不在那條鏈上。`demand_anchor` 為空者不是候選
3. **客戶端資本承諾** — **誰付錢給誰**。客戶掏錢綁供應商＝真瓶頸；供應商付錢或給股權換訂單
   ＝**不是**瓶頸。這一項自帶方向性且最難偽造，是四項裡權重最高的判準
4. **標的純度** — 瓶頸業務占該公司多少。市值與 `analyst_count` **不在排序內，必須另看**

### 措辭：節點與代碼寫中文，首次附原始 label（2026-08-31 使用者定案）

判準是**望文生義還是要查表**，不是「內不內部」：`co:axt`／`co:coherent` 本身就是公司名，
**留著不翻**；含縮寫或長蛇形命名的才翻，並於首次出現以反引號附原始 label 供查圖——
「超高功率雷射 `tech:uhp_laser`」「磷化銦基板 `mat:inp_substrate`」「客戶端印證」
「供應商自報」「獨家供應」；關係動詞寫「供貨給 NVIDIA」／「依賴 X」。
同一份輸出內重複出現可只寫中文。Pane 3 的研究題目同理——寫「誰供應薄膜鈮酸鋰平台
`tech:tfln_platform`」，不寫裸 label。完整判準見 `skills/daily-brief/SKILL.md`「面向使用者的措辭層」。

### 三個必附，缺一即未完成

- **相關性警告**：本圖標的高度集中於 AI 光互連。列出 N 檔**不等於 N 個獨立機會**，
  全買是同一賭注下 N 次。有近期同向波動資料時直接附上（例：2026-08-17→20，
  AXTI −23.8%／COHR −17.4%／AAOI −16.7%／LITE −9.2%／NVDA −3.6%，跌幅單調遞增於
  「離光通訊下游越遠、市值越小」）。
- **各候選的 disproof**：出場靠 disproof，不是進場的前置條件。
- **明標這是研究判斷**，不是回測或統計勝率。

### ⛔ 不得用來拒絕排序的理由

- **「outcome 還沒驗證」不算理由，不論當下比值是多少。** 不出手就沒有 outcome，沒 outcome
  就不敢排序，是死循環。L14 要求的是不得讓未量測機制**決定資本尺寸**，不是不得表達研究判斷。
- 若確實無法排序，**必須指出缺哪一項具體證據**，不得以「證據不足」概括。
- **尺寸仍然不給**——系統自 2026-08-28 起根本不產生尺寸（`axis_ceiling`／paper target 已移除）。
  `research_status` 是研究完整度，不是選股判準，也不得拿來排序。

---

## Pane 2 — 該去補誰的證據

取同一次 `python -m query.bottleneck` 的結構表，挑出**結構很卡但證據沒跟上**的邊
（`substitutability` 高、`evidence` 仍是 `self_reported`、或 `sole_source` 只有供應商自稱）。

它回答的是「該去補誰的證據」：那些邊是研究投入的最高 ROI。

⚠ 2026-09-22（Phase 0／G1）：原文要的是**兩份排序**（可行動 vs 純結構）與它們的差異列。
**兩份序都退役了**——現在只有一份結構表，pane 2 是對同一張表問一個不同的問題，不是第二份排名。

**這一 pane 是「有標的、還沒挖」**，不是「缺標的」。兩者的下一步完全不同。

---

## Pane 3 — 哪裡還是空白（本 skill 唯一的產生器）

跑 `python -m query.graph_walk`（2026-09-26 起；APP `#/graph-walk`）。它報九型問句各自的「命中／母體」，
**不排序、不加總**；本 pane 讀其中「沒人供應」（第 7 型＝原 🔴）與「建模待補」（第 8 型＝原 🟡），
分桶判準仍是 `query/coverage_gaps.py` 那一份。其餘七型（薄層沒人讀、獨家且自報…）照走圖原樣列出，不在這裡重算。

| 桶 | 意義 | 下一步 |
|---|---|---|
| 🟡 **建模待補** | 已有公司經 `prod:` 或公司對公司邊間接相連——**這個領域研究過了**，只是邊沒接上 chokepoint 節點 | 補邊（走 graph admission），**不是重新研究** |
| 🔴 **研究缺口** | 沒有任何公司連到它 | 見下方分類 |

### ⚠ 🔴 的數字**不可直接當研究待辦**

該清單混了兩種完全不同的東西，直接報「缺 N 個標的」就是**把抽取量當研究地圖**——
跟「挖得多＝證據強烈」是同一個錯誤換位置藏：

- **真的該去挖的 chokepoint**：`tech:tfln_platform`、`tech:silicon_photonics_chiplet`、
  `tech:wdm_laser_16ch`、`tech:scale_up_cpo`／`scale_out_cpo`、`tech:dsp_1p6t` 這類
  ——有名有姓、零供應商的子瓶頸，新 alpha 候選最可能從這裡長出來
- **只是從文件掉出來的名詞**：`prod:jericho3`、`prod:tomahawk6`、`prod:altus_family`、
  `prod:sabre_family` 這類產品型號——它們是抽取的副產品，**從來不是我們選定要研究的瓶頸**

**輸出時必須分開兩類並只把前者列為研究題目**，後者僅計數並標明性質。

### 產生器職責

本 pane 的輸出**必須是可直接進 pq1 的研究題目**（「誰供應 `tech:X`」），不是一張看完點頭
的清單。每題附上 §「答案回來會改變什麼」的分類（多半是 `候選集合`）。

⚠ 但走圖（含 `coverage_gaps`）只能從**既有節點**往回看。**它無法提出一個我們從沒聽過的瓶頸**——
那需要由上而下的系統拆解（見 `skills/system-decompose`，尚未建立時請明說這一格是空的）。

---

## Pane 4 — 部位與問責

三塊，使用既有唯讀入口，不以 ad-hoc SQL 另算：

1. **常駐計數器**：取 `python -m crons.heartbeat` 段 4 已輸出的計數（追蹤表檔數、等權絕對與超額、
   正式結算過幾筆、入圖前已漲、三個 power-law 統計量、賭注收斂、alpha 全歸零）；
   **不得回頭自己掃歷史製造另一個分母**。
   ⚠ 2026-09-22：原文取的是 `decision_lab today`，那條路已退役（ROADMAP Phase 0／G12）。
2. **真實部位**：讀 APP 的 `positions` state artifact（`python -m webapp status` 看新鮮度）。
   成交價、最新已收盤價、報酬必須與 catalyst、disproof／lifecycle 狀態合併呈現，不得只列損益；
   後者取 `python scripts/catalyst_watch.py`。
3. **監控覆蓋**：alpha live 部位目前**不在** `event_search_requests` 的覆蓋範圍內
   （`portfolio_risk.py` 只走 `beta_policy.json` 的 `instruments`）。有 live 部位時必須
   明示這一點，不得讓使用者以為有人在看。

---

## 與 pq1 佇列的關係

跑 `python -m engine_b.cli drain` 可看注意力佇列現況與每則的分類標籤
（`[出場條件·財務事實]` 這種）。本 skill **只轉述，不重排**。

若首屏出現 `未分類`，代表該 lead 尚未經 `skills/signal-triage` 的語意分類——**這是要報告
的缺口**，不是忽略它的理由。

---

## 輸出格式

四個 pane 依序出，每個 pane 開頭一句 TL;DR。
⚠ **pane 1 不得有首選、不得有跨檔全序**（2026-09-22 Phase 0／G1；原文寫的正是相反的要求）。
⚠ **2026-09-08 起 Daily 不再嵌入四 pane**（持久內容住 APP，Daily 只印較昨變動）——那不是「另建刪減版判準」，而是把同一份內容移到每天都會更新、隨時可看的地方；判準本身仍只有本檔一份。被呼叫時（`$alpha-status`）一律輸出完整四 pane，不因 Daily 縮了就跟著縮。

**每一列都要標「答案回來會改變什麼」**：`候選集合`／`出場條件`／`只是信心`
（`排序` 那一值隨排序退役，封閉字彙本身在 Phase 0 批 3 一併更新——在那之前讀到它就當
`只是信心`，**不得據它排序**）。
標到「只是信心」的，就是在告訴使用者別做。
**該表開頭固定放一行圖例**（2026-08-31 使用者定案，不得假設使用者記得字彙表）：
`「答案會改變 X」＝這一列的下一個研究題，答案回來時會改變什麼：出場條件（觸發 disproof）>候選集合（清單多/少名字）>排序（誰第一會變）>只是信心（只是更確定）`。

收尾三行：
```
本次未涵蓋：<明說哪一 pane 因資料不足而空>
需要你決定的：<列出待你判斷的項目，不要藏起來>
下一步最高 ROI：<一句，指向 pane 2 或 pane 3 的具體題目>
```

---

## 不做什麼

- **不留檔。** 輸出只出現在 session（同 daily brief）。稽核價值由待辦池 log ＋ leads
  狀態機 ＋ Decision Store 承擔。判準：**這個產物如果不存，明天會有誰真的少了東西？**
  答案若是「只有負責檢查它有沒有過期的那支程式」——不要存。
- **不入圖、不改 thesis、不動資本、不建 pq2 編號。** 它是報告，不是 authority。
- **不給部位尺寸。** 5% 單筆上限、ETF 槓桿 cap、總曝險 cap 全部不變，
  live choice／fill 仍然 100% 人工。

## 與其他 skill 的分工

| 情況 | 用哪個 |
|---|---|
| 今天有什麼要核准 | `skills/daily-brief`（只印較昨變動；持久內容在 APP `#/structure-table`／`#/graph-walk`） |
| 單一標的深挖 | `skills/investment-research` |
| 由上而下拆解一個系統、產生新節點 | `skills/system-decompose` |
| 新公司入圖 | `skills/company-onboard` |
