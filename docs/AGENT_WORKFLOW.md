<!-- agent-workflow-canonical -->
# StockBotv2 — Agent Development Flow

> **本檔回答一個問題：一個開發請求，從「我想做什麼」到「可以關掉這個 Step」，中間要經過哪些節點？**
>
> 判準（可不可以做）仍在 [`AGENTS.md`](../AGENTS.md)；指令在 [`OPERATIONS.md`](OPERATIONS.md)；
> 開發項的清單與優先序在 [`ROADMAP.md`](ROADMAP.md)。**本檔只放流程本身。**
>
> 執行入口是 [`skills/development-flow/SKILL.md`](../skills/development-flow/SKILL.md)。
> 本檔是模型與判準，skill 是照著跑的步驟；兩者不得各寫一份字彙。

---

## 0. 流程

```
IDEA（使用者說「我想做 X」）
  → INTAKE：scope triage（決定 Zoom Level；在既有 context 內做，不 spawn）
  → 需要時 zoom-out（Z2／Z3）
  → PLAN_PROPOSAL：Phase／Step／success criteria
  → AWAITING_HUMAN  ←──── 人工 checkpoint
  → 已核准的當前 Step → implementation
  → REVIEW（R0／R1／R2）
  → STEP_RESULT（含 verdict）
  → AWAITING_HUMAN  ←──── 人工 checkpoint
```

**使用者不需要事先知道 Phase／Step 怎麼切。** 由 agent 從 goal 提出、由使用者裁決。

⚠ **本流程消除的是跨 App 的複製貼上，不是人工 checkpoint。**
少掉的是「把 commit hash 與需求敘述手動搬到另一個視窗」，不是少掉使用者的決定。

---

## 1. Zoom Level：我要站多遠才看得對問題？

| | 名稱 | 典型 | 流程 |
|---|---|---|---|
| **Z0** | Local | typo、CSS／版面、明確局部 bug、小型 renderer 改動 | implement → tests → R0 → report |
| **Z1** | Component | 單一 subsystem 的功能、邊界明確的 refactor、CLI／API 增強 | light plan → implement → R0／R1 → report |
| **Z2** | Cross-cutting | 跨模組責任、contract／workflow／語意改動、refresh／publication 路徑、多個 surface 有 ownership 重疊 | **先不 implement**：輸出 affected responsibilities／current boundary／proposed boundary／Step proposal／success criteria → AWAITING_HUMAN |
| **Z3** | Goal／Architecture | 新的大產品能力、大 refactor、authority ownership 重切、interaction model 根本改變、local patch 一直累積但 binding problem 沒消失 | **真正的 zoom-out**：goal → current architecture → historical baggage → local-optimum traps → possible new architecture → migration phases → proposed current Step → AWAITING_HUMAN |

### 判別四問（依序問，第一個「是」就決定下限）

1. **這個改動會改變任何 contract、封閉字彙、authority 歸屬，或既有輸出的語意嗎？** 是 → 至少 Z2。
2. **要改的那個責任，現在有幾個 owner？** 超過一個 → 至少 Z2（那是 L16 的形狀：分類有 SSOT 但沒跟著資料走到消費端）。
3. **使用者的目標能不能在現有 architecture 裡達成？** 不能／答不出來 → Z3。
4. 以上皆否 → 改的範圍在一個模組內 → Z1；連模組行為都不變 → Z0。

⚠ **改動行數不是 routing authority。** 一行的 currency identity 修正可以是 Z1／R2；
一千行的 UI 重做可以是 Z3／R1。

---

## 2. Zoom escalation：做到一半發現站太近

Worker 在 Z0／Z1 途中若發現下列任一項，**必須停止擴 scope 並輸出 `SCOPE_ESCALATION`**：

- 同一責任存在多份 owner
- 需要改 canonical identity
- workaround 開始擴散（同一個判斷在第二、第三個地方被重寫）
- 新需求其實暴露了 architecture boundary 問題
- scope 明顯超出原 Step

`SCOPE_ESCALATION` 必含四欄：**original zoom／observed issue／recommended zoom／why local patch is insufficient**。

**不得自行「順便重構整套」。** 升級是提案，不是授權。

使用者隨時可手動說 **`zoom out`**——那是強制升級，不受 agent 原本的 routing 判定限制。

---

## 3. Review Level：我要離 implementer 多遠才能相信結果？

Review 與 Zoom 是**兩個獨立維度**。Zoom 問「看對問題了嗎」，Review 問「這個結果可信嗎」。

| | 名稱 | 誰做 | 成本 |
|---|---|---|---|
| **R0** | Self-check | 同一 agent：implementation → 必要測試 → 讀 diff → 對照 acceptance → report | 幾乎為零 |
| **R1** | Same-agent adversarial pass | 同一 agent、同一 session，但**明確切換心態**：停止替 implementation 辯護，改成試圖證偽它 | 低（只花 context） |
| **R2** | Fresh independent reviewer | 新 context／新 agent：不繼承 worker 的推理過程、不信任 DELIVERY、直接讀 repo／commit／diff、自己跑可證偽測試 | **高（第二份 token）** |

### R1 至少要檢查的六項

hidden assumptions｜affected behavior｜**unaffected behavior**（宣稱沒動到的，真的沒動到嗎）｜
fail-closed behavior｜mechanism actually exercised（這條路徑真的被跑過嗎，還是只是編譯得過）｜regression path。

### R2 的自動 trigger（六條）

1. authority ownership／mutation
2. financial identity／fiscal period／point-in-time／units
3. security／credentials／capital／destructive write
4. major architecture boundary migration
5. phase-level closure，且下一階段高度依賴本 Phase
6. implementer 明確發現**自己無法判斷這個 fix 有沒有改到 binding constraint**

**其餘情況預設不花第二份 agent token。**

⚠ **「自動 trigger」＝自動*提出*，不是自動 spawn。**
`AGENTS.md`「協作與邊界」規定 subagent 委派預設關閉、每次明確 opt-in，所以 R2 的啟動本身就是一個
human checkpoint：agent 說明「為什麼這題值得第二份 token」，使用者決定。
使用者也可反向 override：「這個不用 fresh reviewer」／「這個多看一雙眼睛」。

⚠ **R2 的回傳是 review packet，不是 authority。** fresh reviewer 不在 review round 順手改 code，
不核准 pq2、不入圖、不動 thesis、不 commit。同一 working tree 維持主 agent 為唯一 writer。

---

## 4. Routing 預設

| Zoom | 預設 Review |
|---|---|
| Z0 | R0 |
| Z1 | R0；邏輯 tricky 或錯誤成本較高時 R1 |
| Z2 | R1；命中 R2 六條 trigger 之一才提 R2 |
| Z3 | architecture zoom-out 走人工 checkpoint；**implementation 的 review 不自動是 R2** |

**Z3 ≠ R2。** 大改動不等於高錯誤成本；小改動也可能是。

---

## 5. Human checkpoint 語意

**Agent 不得自動 goal-seeking 到 roadmap 終點。**

### 硬 invariant

> **GO 只關閉本 Step，不開啟下一個 Step。**

`STEP_RESULT` 裡的「建議下一步」永遠只是建議。使用者說 GO 之後，agent 回到 AWAITING_HUMAN，
等待對**下一個 Step** 的明確指示。這與 `AGENTS.md`「`go` 的語意＝推進到下一個人工 gate」一致：
Step 邊界本身就是那個 gate。

### `STEP_RESULT` 必填七欄

每個 Step 結束時**一定要**呈現，缺一不可：

```
Current Phase        現在在哪個 Phase
Current Step         現在哪個 Step
Zoom / Review        本 Step 實際用了哪一級（不是原本 routing 說要用哪級）
Verdict              GO / CONDITIONAL_GO / NO_GO / HUMAN_REQUIRED
Acceptance status    逐條 success criteria 的達成與否（含查證命令）
Blocking findings    擋住 verdict 的發現
Non-blocking debt    知道但這輪不修的
Suggested next Step  ＋它的 success criteria（**只是建議**）
```

⚠ **`Zoom / Review` 欄不是裝飾。** 依 L16（分類已有 SSOT 時要讓它跟著資料走到需要它的地方），
使用者必須不用回頭讀 transcript 就知道「這個結論是自己看自己看出來的，還是有人獨立驗過」。
實際使用的等級與原本 routing 判定不同時，要寫出來並說明為什麼。

---

## 6. Verdict 四值

| Verdict | 語意 | 之後發生什麼 |
|---|---|---|
| **GO** | 本 Step 的 acceptance 通過，Step 可關閉。**不要求所有下游產出都已就緒。** | 回 AWAITING_HUMAN |
| **CONDITIONAL_GO** | 只剩明確、有限、可驗證、**不需重新設計**的條件 | 條件逐條列出並附驗證方式；回 AWAITING_HUMAN |
| **NO_GO** | 本 Step 的 acceptance 未通過 | **預設停下來給人看，不自動進入修復迴圈** |
| **HUMAN_REQUIRED** | 現有 repo／invariant 沒有授權 agent 替使用者做這個決定 | 把待決問題問出來 |

⚠ 條件多到需要重新設計，那不是 CONDITIONAL_GO，是 NO_GO。這條分野被濫用時，
CONDITIONAL_GO 會變成「其實沒過但不想說」的委婉語。

---

## 7. Message protocol（只有七種，刻意不擴充）

`IDEA`｜`PLAN_PROPOSAL`｜`WORK_REQUEST`｜`DELIVERY`｜`REVIEW`｜`SCOPE_ESCALATION`｜`HUMAN_DECISION`

**這是七個字彙，不是七個檔案、七個佇列或七個 agent。** 它們是回覆裡的標題行。
本流程**不建立** message queue、workflow database、autonomous merge bot、branch orchestration
framework、infinite agent loop、custom agent server、automatic roadmap execution。

---

## 8. NO_GO 之後不預設 auto-repair

reviewer 判 NO_GO 後**不要**進入 `Reviewer → Worker → Reviewer → Worker until GO` 的迴圈。

正確流程：`NO_GO` → 顯示 findings → `AWAITING_HUMAN`。使用者可選：修（R1／R2）、
挑戰這個 finding、改 scope、park、放棄。

未來若某類純機械 bug 被證明適合 auto-repair，那是另一個 Step，另外加。

---

## 9. Roadmap 是 live hypothesis，但不得偷改

實作中發現需要插入 Step 2.5、新的驗收 phase、coverage pilot 或 consumer layer 時，
**可以**提 roadmap amendment，但必須先寫出五欄：**原 roadmap／新觀察／proposed change／why／impact**，
然後 AWAITING_HUMAN。

**不得偷偷改 `ROADMAP.md` 並繼續跑。**

---

## 10. 與既有機制的分工（不要重造）

| 既有機制 | 它是什麼 | 它**不是**什麼 |
|---|---|---|
| `python -m audit invariants` | deterministic runtime invariant checker。語意保證：`SKIPPED ≠ PASS`、`examined == 0` 自動降級成 `SKIPPED`、check 自己爆了算 FAIL 不算 SKIPPED | **不是 agent、不是 reviewer**。reviewer 可以引用它當 evidence source，不得拿它代替判斷，也不得 wholesale rewrite |
| ROADMAP 的 Phase completion gate（八項） | Phase 級的關閉條件 | 不是 Step 級。單一 Step 的 acceptance 由該 Step 自己的 success criteria 決定 |
| pq2 待辦池 | **研究**與 authority 動作的唯一授權介面 | 開發項不進 pq2，唯一載體是 `ROADMAP.md`（`AGENTS.md` 2026-08-31 定案） |
| sandbox impact review 五步 | unattended routine 的 executable surface 變更必經 | 不是 code review。它只問「這條命令會不會在無人值守時做出沒被 gate 約束的事」 |
| `scripts/sync_agent_skills.py` | canonical skill → `.claude`／`.agents` 轉接層 | 轉接層**不是** SSOT，不手改 |
| `scripts/verify_test_nonvacuity.py` | 證明斷言不是空跑（故意違規 → 確認會紅） | 不是覆蓋率工具 |

**四個人工 gate 不因為多了一套開發流程而放寬**：graph admission／Engine C 判讀寫入／
thesis mutation／live choice-fill。

---

## 11. Canonical 檔案預算（hard max 4）

本流程的 canonical 檔以 HTML 註解 `<!-- agent-workflow-canonical -->` 標記，**上限四份**：

1. `docs/AGENT_WORKFLOW.md`（本檔）— 模型與判準
2. `skills/development-flow/SKILL.md` — intake、routing、R0／R1 執行、development／operational review profile
3. `skills/blind-spot-audit/SKILL.md` — research review profile

第四個位置留白。**要新增第五份，必須先退役一份。**
`tests/test_agent_workflow.py` 機械擋住這條，並擋住 `worker.md`／`reviewer.md`／`architect.md`／
`planner.md`／`orchestrator.md`／`delivery.md`／`verdict.md`／`zoom.md` 這類碎檔重生。

生成的轉接層（`.claude/skills/`、`.agents/skills/`）不計入預算——它們不是 SSOT。

---

## 12. 這套流程自己的 disproof（L7 套在自己身上）

沒有 `disproof_condition` 的東西不是機制，是信仰。本流程的證偽條件：

| 觀測到什麼 → 就代表這套流程沒生效 | 核查頻率 | 觸發後 48 小時 |
|---|---|---|
| 出現「因為上一個 Step GO 了所以我就繼續做下一個」 | 每次 Step 收尾 | 把該次 transcript 當事故記錄；若是流程講不清楚造成的，改判準句而不是加文件 |
| `STEP_RESULT` 的七欄開始有欄位長期空白或寫「N/A」 | 每次 Step 收尾 | 那一欄要嘛沒用（刪掉），要嘛沒人填（改成會自己出現的東西）。**不要留著假裝有** |
| R2 從未被觸發過，或每次都觸發 | 每季 | 恆亮或不會滅＝零鑑別力（L14 第 4 點）。六條 trigger 要重寫，不是調鬆緊 |
| 開發請求繞過 intake 直接開工，而事後看 zoom 判錯了 | 每次 | 記錄實際 zoom vs 應有 zoom；若判準四問答不出來，是四問的問題 |

⚠ **這套流程本身不得用來宣告自己有效。** bootstrap phase 由既有人工雙邊流程驗收。
第一次 dogfood 的結果才是第一份證據。
