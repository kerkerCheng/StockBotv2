---
name: development-flow
description: >
  開發請求的統一入口：先做一次便宜的 scope triage（Zoom Level），再決定要多遠的 review
  （Review Level），最後以「HUMAN SUMMARY（人話 5–10 行）＋固定八欄 STEP_RESULT」交回使用者。當使用者提出任何「改程式、
  改 config、改 schema、改呈現邏輯」的請求時使用——包含「我想做 X」「這裡壞了」「加一個
  功能」「重構 XXX」「這個能不能改成…」「zoom out」。**使用者說「先討論、不實作」「重新 review
  整個工作流」「大方向」時同樣要進**：Z2／Z3 的規定產出本來就是討論（PLAN_PROPOSAL），
  「只討論」不是跳過 scope triage 的理由。它不是另一個 agent，預設由當前主
  agent 在既有 context 內完成，不 spawn。研究請求（改變「我知道什麼」）不走本 skill，
  走研究路徑：intake／source-trace／extraction 在 pq1，只有產生 exact authority mutation
  proposal 時才進 pq2 核准。觸發詞：我想做、幫我改、加一個、修一下、重構、zoom out、這個 Step、
  下一步要做什麼、重新 review、先討論、大方向、整個工作流。
---
<!-- agent-workflow-canonical -->

# Development Flow — 開發請求的統一入口

模型與判準全文在 [`docs/AGENT_WORKFLOW.md`](../../docs/AGENT_WORKFLOW.md)。
**本檔是照著跑的步驟**，不重複定義字彙。

## 先確認這是不是開發請求

**判準一句話：`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？**

- 改變「我知道什麼」（圖、Engine C、thesis、資本裡的事實）→ **不走本 skill**，走研究路徑。
- 改變「系統怎麼運作」（程式、config、schema、呈現邏輯）→ 走本 skill，載體是 `docs/ROADMAP.md`。

⚠ **「研究」不等於「pq2」。** 研究路徑本身有兩段，別把整段路由到核准佇列：

| 段 | 誰在做 | 佔不佔編號 |
|---|---|---|
| **intake／source-trace／extraction** | routine 在 **pq1** 自動研究（raw／triaged leads 不占 pq2 編號） | 否 |
| **exact authority mutation proposal**（prepared RA 入圖、Engine C 判讀寫入、thesis mutation、手動 authority） | 鑄 **pq2** 編號請使用者核准 | 是 |

把 pq1 的工作提早鑄成 pq2，會讓同一題在研究前與入圖前被問兩次——那正是統一編號空間要消除的事。

例：「補某條邊的 substitutability」＝研究——**追源與抽取在 pq1 自動跑**，只有最後那筆
graph-write 提案才鑄 pq2 編號等核准；「改 `rank_bottlenecks` 的排序鍵」＝開發（本 skill）。

⚠ **「先討論、不實作」不是豁免，是 Z2／Z3 的正常路徑。** 判準一句話沒有「討論」這個例外：
只要 `go` 之後改變的是系統怎麼運作，就先做 INTAKE；Zoom 判出 Z2／Z3 時，規定產出**就是**討論
（PLAN_PROPOSAL → `AWAITING_HUMAN`），不是 diff。事發（2026-09-08）：使用者要求「重新 review 整個
工作流……research drain skill 重構……可以先討論不實作」，執行者把「先討論」讀成不走本 skill，
直接寫了一份沒有 INTAKE、沒有 proposed current Step 的分析——內容接近 zoom-out 七段，但使用者
拿不到一個可以核准的 Step，這正是 Z3 格式要防的事。

---

## Step 1｜INTAKE：scope triage（必做，但要很便宜）

**不 spawn、不開新 context、不做完整 architecture 盤點。** 只依序問四個問題：

1. 這個改動會改變任何 contract、封閉字彙、authority 歸屬，或既有輸出的語意嗎？→ 是則至少 **Z2**
2. 要改的那個責任，現在有幾個 owner？超過一個 → 至少 **Z2**
3. 使用者的目標能不能在現有 architecture 裡達成？不能／答不出來 → **Z3**
4. 皆否 → 範圍在一個模組內 = **Z1**；模組行為都不變 = **Z0**

答不出第 2 題就是還沒 triage 完——先 `grep` 一次那個責任的字串，不要用印象作答。

輸出一個 `INTAKE` 區塊（三行就夠，不要寫成報告）：

```
INTAKE
Zoom: Z1（理由：只動 webapp/api.py 的 renderer，無 contract 變更）
Review: R0（不命中 R2 六條 trigger）
```

## Step 2｜依 Zoom 決定下一步

| Zoom | 下一步 |
|---|---|
| **Z0** | 直接 implement → 跑必要測試 → R0 → 報告 |
| **Z1** | 先給 3–5 行 light plan（改哪幾個檔、驗收條件）→ implement → R0／R1 → 報告 |
| **Z2** | **停止實作。** 輸出 affected responsibilities／current boundary／proposed boundary／Step proposal／success criteria → `AWAITING_HUMAN` |
| **Z3** | **停止實作。** 走 zoom-out：goal → current architecture → historical baggage → local-optimum traps → possible new architecture → migration phases → proposed current Step → `AWAITING_HUMAN` |

⚠ Z2／Z3 的產出是 `PLAN_PROPOSAL`，不是 diff。使用者核准哪一個 Step，就只做哪一個 Step。

### 途中要升級時

發現「同一責任多份 owner／要改 canonical identity／workaround 開始擴散／新需求其實暴露
architecture boundary 問題／scope 明顯超出原 Step」任一項 → 停下，輸出：

```
SCOPE_ESCALATION
Original zoom:
Observed issue:
Recommended zoom:
Why local patch is insufficient:
```

**然後停止擴 scope。不得順便重構整套。**
使用者說 `zoom out` 是強制升級，直接照做，不辯護原本的判定。

## Step 3｜Implementation 的固定要求

- **改變行為的改動，動手前先答出「這會讓哪個 baseline 數字變？」**（L14 第 5 點）答不出來就先進 ROADMAP，不做。
  維持營運型（管線壞了、腳本報錯）直接修，但**它不算進展**。
- 動 `python -m <module>` 命令字串、或新增任何 unattended routine 會跑到的入口 → 同一個 change 內完成
  **sandbox impact review 五步**（`docs/OPERATIONS.md`），並確認 `.codex/rules` 的 fixed entry 數量是否該變。
- 新增 `config/*.json` → 同一個 change 補 `.gitignore` 的 `!config/<name>.json`。
- 新增或改 skill 的 `name`／`description` → 跑 `python scripts/sync_agent_skills.py`。
- code 改動讓 `AGENTS.md` 的某句話變成假的 → **同一個 commit** 改掉那句話。

## Step 4｜REVIEW

Review Level 由 `INTAKE` 決定，但**實際做了哪一級要寫進 STEP_RESULT**，不是寫當初打算做哪一級。

### R0 — Self-check（預設）

跑必要測試 → 讀一次自己的 diff → 逐條對照 acceptance criteria → 報告。

### R1 — 同一 agent 的對抗回合

**明確切換心態：從「這個實作為什麼是對的」切到「我要找出它為什麼是錯的」。**
先挑一個 profile（下方兩個 profile 只挑需要的，不要每次全跑），再加這六項通檢：

hidden assumptions｜affected behavior｜**unaffected behavior**｜fail-closed behavior｜
mechanism actually exercised｜regression path。

### R2 — Fresh independent reviewer

命中六條 trigger 之一才**提出**（authority mutation／financial identity・PIT・units／
security・credentials・capital・destructive write／architecture boundary migration／
phase closure 且下一階段高度依賴／implementer 自認判斷不了 fix 有沒有改到 binding constraint）。

⚠ **提出 ≠ 自行 spawn。** subagent 委派預設關閉、每次明確 opt-in（`AGENTS.md`「協作與邊界」）。
說明「為什麼這題值得第二份 token」，然後等使用者決定。

真的要委派時，`WORK_REQUEST` 只給下列內容，**不給自己的推理過程**：

```
WORK_REQUEST（R2）
Target: <commit / branch / 檔案清單>
Claimed acceptance: <本 Step 宣稱達成了什麼>
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo 與 diff，自己跑可證偽的檢查，回 REVIEW（含 verdict）
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis
```

---

## Review profile：development

只在 R1／R2 時套用，**挑相關的問，不要全跑**：

| # | 問題 | 為什麼 |
|---|---|---|
| 1 | **semantic correctness** — 這個值的意思在改動前後是同一件事嗎？ | 語意漂移不會讓測試變紅 |
| 2 | **authority boundary** — 誰有權寫這筆？改動有沒有造出第二個 current-state authority？ | 五條 authority separation |
| 3 | **hidden defaults** — 有沒有哪裡把「沒給」悄悄補成一個值？ | 預設值會偽裝成觀測 |
| 4 | **Missing != Zero** — 讀不到時輸出 0／空集合，還是誠實降級？ | 「你一檔都沒買」vs「我沒讀到你買了什麼」導向相反的行動（L12） |
| 5 | **PIT／identity／units** — as-of 語意、entity identity（不是 ticker）、報價單位 vs 結算幣別 | 這三類錯誤靜默且昂貴（差 100 倍那次） |
| 6 | **affected + unaffected behavior** — 宣稱沒動到的那部分，真的沒動到嗎？ | 「零行為變化的純重構」被自家測試打臉過 |
| 7 | **dead mechanism** — 這個機制實際產出過幾筆？ | 不看有沒有實作，看有沒有輸出（原 D13） |
| 8 | **fix efficacy** — 改完之後，**現有資料有幾筆真的變了**？ | 答案 0 就代表沒改到 binding constraint（L14／原 D14） |
| 9 | **fail closed** — 出錯時是拒絕，還是靜默回一個看起來合理的值？ | INV-6 |
| 10 | **一個表示兩種語意** — 有沒有欄位同時承載兩件事，使下游二選一而兩邊都錯？ | L12（原 D15）。訊號：放寬與收緊都能舉出災難；某個修法讓警報消失得太乾淨 |
| 11 | **可重建 vs point-in-time** — 這筆資料今天重取一次拿得回來嗎？ | 拿得回來的要有修復路徑，不該凍結（原 D17） |

## Review profile：operational

| # | 問題 | 為什麼 |
|---|---|---|
| 1 | **duplicate responsibility** — 同一件事有沒有第二個地方也在做？ | L16 的形狀 |
| 2 | **hook／reminder ownership** — 這個提醒由誰產生、誰會關掉它？ | SessionStart hook 與待辦池的邊界 |
| 3 | **queue liveness** — producer 指得出 consumer 嗎？ | INV-4。「已排入」不等於「已推進」（L13） |
| 4 | **unattended mutation** — 無人值守時它會寫什麼？被哪個 gate 約束？ | 不得用 broad permission 掩蓋整合缺口 |
| 5 | **silent degradation** — 降級時有沒有東西會說話？ | INV-3：「查不到了」不是合法 lifecycle |
| 6 | **APP／Daily／pq1／pq2 邊界** — 這個責任屬於哪一個？有沒有跨界？ | APP 讀認知、LLM 改認知；pq1 自動、pq2 要人 |
| 7 | **materialization／publication freshness** — 使用者看到的是哪一版判讀？ | request path 不得重建，否則答不出這題 |
| 8 | **只有入口沒有出口** — 這東西怎麼離開？不關會怎樣？ | 入口是使用者的一次動作，出口不該也要求他記得（原 D16） |

**research profile 不在本檔**——它是 [`skills/blind-spot-audit/SKILL.md`](../blind-spot-audit/SKILL.md)。

---

## Step 4.5｜HUMAN SUMMARY（先講人話，預設 5–10 行）

**八欄回答「這個結果可不可信」；HUMAN SUMMARY 回答「這對我的目標意味著什麼」。**
兩者問的不是同一件事，所以**不是摘要與被摘要的關係**——把八欄壓縮一遍充當它，等於什麼都沒加。

輸出順序固定：**決策／收據區塊 → HUMAN SUMMARY → `STEP_RESULT`。**

⚠ **本 Step 若要使用者決定任何事，最前面必須是決策區塊**，格式用共用的那一份：
[`skills/daily-brief/SKILL.md`](../daily-brief/SKILL.md)「待核准項目的內容密度」。
**本 skill 不自己定義那個格式。** 開發項不鑄號（載體仍是 `ROADMAP.md`），所以走常規授權
做掉的改動用該檔規定的**收據行**（事後告知＋可否決，必含「會變的數字」與「可逆」兩格）。

⚠ **`STEP_RESULT` 是附錄，不是開場。** 它回答「這個結果可不可信」——那是使用者**事後**
才需要的；決策區塊回答「要不要」，那是他**當下**需要的。2026-09-11 實測：一份收尾裡
真正的決策資訊只有 7 項 × 5 行，其餘約 60 行都是附錄，而批次行被壓在最後面。

```text
HUMAN SUMMARY
做了什麼：<產品／責任層一句話——使用者拿到什麼能力。不先出現 module／class／artifact 名稱>
為什麼重要：<它讓使用者離 Phase goal 更近在哪一步>
現在在哪：<一行 progress map：✅ 已完成 → ▶ 這一步 → ○ 剩餘主要 Step；每項用看得懂的名字>
下一步：What — <實際會做什麼>
        Why now — <為什麼現在做它最合理>
        After this — <做完後這個 Phase 還缺什麼>
```

**五條硬要求：**

1. **預設 5–10 行。** 超出就是第二份報告——使用者會兩份都不讀。
2. **roadmap／內部 ID 不得單獨出現。** 首次出現必須同時給 plain-language title，例如
   `B2b — 把研究缺口與事件監看搬成 APP 可持久讀取的狀態`；同一份輸出內第二次起可只用 ID。
3. **工程證據留在八欄**：測試數、bytes、函式／模組／artifact 名稱不進這一段。
   **唯一例外**是那個數字本身會改變使用者的產品判斷（例：「只有四檔有資料，其餘要手動跑」）。
4. **progress map 只列 Phase 的主要 Step**，不列子任務、不列內部編號。
5. **「下一步」三段缺一不可。** 少了 `Why now`，使用者無從判斷要不要現在做；
   少了 `After this`，他答應之後仍不知道距離終點還有多遠。

⚠ 這一節**不改變任何 routing**：Zoom／Review 判定、`GO` 的語意、八欄內容一律不動，
也不新增 agent 或 canonical 檔。它只規定「先給人看的那幾行長什麼樣」。

---

## Step 5｜STEP_RESULT（八欄，缺一不可）

```
STEP_RESULT
Current Phase:        
Current Step:         
Zoom / Review:        （實際用了哪一級；與 INTAKE 不同時要說明為什麼）
Verdict:              GO / CONDITIONAL_GO / NO_GO / HUMAN_REQUIRED
Acceptance status:    逐條 success criteria ✅／❌，附查證命令
Blocking findings:    
Non-blocking debt:    
Suggested next Step:  ＋它的 success criteria（**只是建議**）
```

然後 **`AWAITING_HUMAN`**。

⚠ 八欄之前必須先有 `HUMAN SUMMARY`（Step 4.5）——兩者一起交回，缺任一半都不算交付。

---

## 硬禁止（違反即視為未完成）

1. **GO 只關閉本 Step，不開啟下一個 Step。** 但 2026-09-08 起使用者已常規授權：**Verdict 為 GO
   且下一步沒有待他決定的問題時，可直接接續**（六條停止條件見 `AGENT_WORKFLOW.md` §5：Z2／Z3、
   四個人工 gate、資本／live／append-only authority、改 `AGENTS.md` 判準句或 ROADMAP Step 定義、
   需要 R2、Verdict 不是 GO）。**買的是「不必為了說一聲而停」，不是「不必為了決定而停」。**
2. **不得偷改 `ROADMAP.md` 並繼續跑。** 要改先給五欄 amendment（原 roadmap／新觀察／proposed change／why／impact）→ `AWAITING_HUMAN`。
3. **NO_GO 之後不自動 repair loop。** 顯示 findings → `AWAITING_HUMAN`，由使用者選修／挑戰／改 scope／park／放棄。
4. **不自行 spawn subagent。** 每次委派都要明確 opt-in；回傳是 review packet 不是 authority。
5. **四個人工 gate 不放寬**：graph admission／Engine C 判讀寫入／thesis mutation／live choice-fill。
6. **不建立第二套流程狀態源**：不做 message queue、workflow database、autonomous merge bot、
   branch orchestration framework、agent loop、automatic roadmap execution。七種 message 是**標題行**，不是檔案。
