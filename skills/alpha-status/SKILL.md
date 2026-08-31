---
name: alpha-status
description: >
  Alpha 現況總覽：回答「現在最值得投哪一檔」「該去補誰的證據」「哪裡還是空白」「已投的
  部位怎麼樣」四題。當使用者說「alpha status」「alpha 現況」「瓶頸排序」「現在該投什麼」
  「我們缺什麼」「哪裡還沒挖」「挖到哪了」時使用；daily-brief 目前嵌入本 skill 的完整四個 pane。
  **純消費端：只讀既有 authority 的輸出，一個數字都不自己重算**——它報告排程實際做了什麼，
  不是自己另算一份。不入圖、不改 thesis、不動資本，所有人工 gate 不受影響。
  觸發詞：alpha status、alpha 現況、瓶頸排序、現在該投什麼、缺什麼、哪裡還沒挖。
---

# Alpha Status Skill（v1.1）

## 定位一句話

**把「該投什麼／該挖什麼／哪裡是空白／已投的怎麼樣」四題，一次答完並排出順序。**

系統只負責兩件使用者自己做不動的事：**哪些標的值得看**、**它們有什麼新事件**。
買多少、什麼時候買由使用者決定（`AGENTS.md`「Alpha 呈現契約」）。

---

## 鐵律一：純消費端，不自己重算

本 skill **不得**自行查圖排序、自行計算分數、或另建任何平行排名。它只跑既有指令並轉述。

理由：若它自己算一份，它報告的現況就會與**排程實際做的**不同，使用者無從分辨
「我看到的」與「系統做的」是不是同一件事——這正是 L13（驗收要驗下游消費者手上的東西）
要防的。**自己算等於改自己的考卷。**

| 要回答的 | 唯一權威 | 指令 |
|---|---|---|
| 現在能投什麼 | `query/bottleneck.py` 的 `rows` | `python -m query.bottleneck` |
| 該補誰的證據 | 同上的 `structural_rows` | 同上（同一次輸出） |
| 哪裡是空白 | `query/coverage_gaps.py` | `python -m query.coverage_gaps` |
| 標的純度（市值／分析師） | Engine C `financial_snapshots`／`consensus_coverage_observations` | 見 §pane 1 |
| 部位與計數器 | `decision_lab today`＋`scripts/outcome_if_settled_today.py` | 見 §pane 4 |
| 注意力佇列現況 | `engine_b/priority.py` 的分類 | `python -m engine_b.cli drain` |

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

## Pane 1 — 現在要投哪一檔

**必須輸出有序清單與明確首選，並直接回答「現在要加碼哪一檔」。這是交付要求，違反即視為未完成。**

跑 `python -m query.bottleneck`，取 `rows`（可行動排序：`evidence` 優先於
`substitutability`，回答「現在能投什麼」）。再對前段候選補上四維度中排序**不包含**的第 4 項：

```powershell
& '.venv\Scripts\python.exe' scripts\alpha_purity_snapshot.py --format markdown --tickers <Pane 1 前段候選 tickers>
```

這是正式的唯讀 consumer：它從 active Engine C authority 讀最新 `financial_snapshots` 與
`consensus_coverage_observations`，依 `identity/currency.py`＋`config/currency_units.json` 把 GBp 等
minor quote unit 換回結算幣別後輸出市值。**本 skill 只轉述結果，不再自己乘。** 不同結算幣別
沒有做 FX，仍不得直接當成同一尺度排序；`manual_required` 是未知，不得寫成 0。

此入口屬 Daily 的 exact outside-sandbox rule。若回 `private_acl_verification_unavailable`，意思是目前
執行環境無法執行 owner-only ACL 驗證、所以 fail closed，**不等於 ACL 不合格**；不得再以 ad-hoc
SQL 繞過。真正的 `private_storage_boundary_rejected` 才是 storage boundary 拒絕。

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
`tech:tfln_platform`」，不寫裸 label。完整判準見 `AGENTS.md`「面向使用者的措辭層」。

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

取同一次 `python -m query.bottleneck` 的 **`structural_rows`**（純結構排序，**完全不看證據**）。

它回答的是「該去補誰的證據」：結構很卡但證據沒跟上的邊，是研究投入的最高 ROI。
與 pane 1 的 `rows` **用途不同、不可互換**。

輸出時務必點出兩份排序的差異列（`bottleneck.py` 自己會標「⬆ 可行動排序第 N——補證據可翻上來」）。

**這一 pane 是「有標的、還沒挖」**，不是「缺標的」。兩者的下一步完全不同。

---

## Pane 3 — 哪裡還是空白（本 skill 唯一的產生器）

跑 `python -m query.coverage_gaps`，它已經把節點分成 🔴 研究缺口／🟡 建模待補／✅ 已覆蓋。

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

⚠ 但 `coverage_gaps` 只能從**既有節點**往回看。**它無法提出一個我們從沒聽過的瓶頸**——
那需要由上而下的系統拆解（見 `skills/system-decompose`，尚未建立時請明說這一格是空的）。

---

## Pane 4 — 部位與問責

三塊，使用既有唯讀入口，不以 ad-hoc SQL 另算：

1. **常駐計數器**：取 `python -m decision_lab today --format markdown` 已輸出的研究進展／可量測／
   結案歸因計數；不得回頭直接掃歷史 decision 筆數製造另一個分母。
2. **真實部位**：跑 `python scripts/outcome_if_settled_today.py`，只消費其 `Live 部位 vs 只有 paper`
   與錨點體檢。成交價、最新已收盤價、live 報酬必須與同 cohort 的 epoch、catalyst、disproof／lifecycle
   狀態合併呈現；後者取同一次 `decision_lab today`／`catalyst_watch.py`，不得只列損益。
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

四個 pane 依序出，每個 pane 開頭一句 TL;DR。**pane 1 必須有明確首選。**獨立呼叫與嵌入
Daily Brief 時使用同一份輸出契約；Daily 不得另建刪減版或平行判準，直到使用者看過完整成品後另行定案。

**每一列都要標「答案回來會改變什麼」**：`候選集合`／`排序`／`出場條件`／`只是信心`。
標到「只是信心」的，就是在告訴使用者別做——那一級的上限被鎖死在「把已知第一名確認成第一名」。
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
| 今天有什麼要核准 | `skills/daily-brief`（目前嵌入本 skill 的完整四個 pane） |
| 單一標的深挖 | `skills/investment-research` |
| 由上而下拆解一個系統、產生新節點 | `skills/system-decompose` |
| 新公司入圖 | `skills/company-onboard` |
