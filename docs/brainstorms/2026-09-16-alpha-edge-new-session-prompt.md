# 給新 session 的啟動 prompt（2026-09-16）

> 用法：在新的 Claude Code session 貼下面整段，或直接 `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。

---

> ~~**狀態（2026-09-16）：Step 0 已核准並合併進 master（branch `docs/alpha-edge-step0`）。**
> 新 session 照下面順序讀完文件後，**直接從「Step 1 以後」開始**：先出 Phase 1 的 PLAN_PROPOSAL（Z3），停下等核准。~~
>
> **狀態（2026-09-16 21:30）：Step 0 已合併；Phase 1 PLAN 已核准（決策 A go／B 選 1／C 選 1／D 選 2，順序 1.0 → 1.1 → 1.2 → 1.3）；
> Step 1.0「公司名稱解析歸位」已 GO 並合併 master（merge `d06f5bf`）。**
> 新 session 照下面順序讀完文件後，再讀 **`docs/brainstorms/2026-09-16-alpha-edge-phase1-plan.md`**（核准的計畫、工單、Step 1.0 殘餘、
> MFN／RNS／MOPS 的探測事實），然後**直接從 Step 1.1 開工**（兩支抓取器＋路由登記＋三份 smoke 文件入圖）。
> **常設授權（2026-09-16 使用者定案）：Step 的 Verdict 為 GO 且沒有待使用者決定的問題時，直接合併 master 並接續下一個 Step，
> 不逐 Step 請核准。** 仍要停：Verdict 非 GO、有待決問題、動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句。
> pq2 的圖寫入（`ra_admission`）與 Engine C 判讀寫入仍逐筆核准——研究段落收尾照常給批次指令。
> 不要重做 Step 0（去向清單 `docs/refactor/alpha-edge-step0-migration.md`），也不要重做 Step 1.0。

先做 Step 0 文件整併並交回 diff，未核准前不得動任何程式。

**先讀（順序固定）：**
1. `docs/brainstorms/2026-09-16-alpha-edge-discovery-requirements.md`（決定紀錄 D0–D15；在 AGENTS／ROADMAP 整併完成前，它是 SSOT）
2. `AGENTS.md`（憲法、invariant、gate、L1–L17：這些一字不動）
3. `docs/AGENT_WORKFLOW.md` 與 `skills/development-flow/SKILL.md`（本請求是 **Z3**，且動到判準句，屬常規推進授權例外 ④：每個 Step 交回後停下等人）
4. `docs/refactor/historical-failure-matrix.md`（動 contracts 前必讀）

**任務：** 依決定紀錄把系統從「大型股 FY+1 錯價」轉向「邊緣小公司 power-law 漏斗」。分 Step 交付，每個 Step 交回 HUMAN SUMMARY ＋ 八欄 STEP_RESULT，Verdict 不是 GO 或有待決問題就停。

**Step 0（先做，只動文件）：**
- 依決定紀錄 §2 D0 與 §5 驗收整併 `AGENTS.md`、`docs/ROADMAP.md`；ROADMAP 現行內容照 2026-09-03 先例整份搬 `docs/archive/`，新表只放四層漏斗的 Phase（每項四欄：做什麼／為什麼／驗收哪個數字會變／前置）。
- 被取代的呈現契約句子劃線加日期留原地或搬 archive 並留指向；不得靜默刪除。
- 依 D13 加兩個 skill scope note 與 blind-spot-audit 的新 lens，然後跑 `python scripts/sync_agent_skills.py`。
- 更新 `docs/ARCHITECTURE.md`、`docs/OPERATIONS.md`、`CONCEPTS.md` 中與新目標衝突的段落，同樣劃線不刪。
- 驗收：~~AGENTS 字元數 < 34,836~~ AGENTS 字元數必須降且內容驗收全過（2026-09-16 使用者定案，實測 36,075 → 34,624）；`grep -c "^### L" AGENTS.md` 得 17；`python -m audit invariants` FAIL 0；`python -m pytest tests/test_codex_daily_permissions.py` 綠；每句移除的舊契約列出去向。
- 產出：**diff 與去向清單**，在獨立 branch。停下等核准。

**Step 1 以後（Step 0 核准後才出 plan，先出 PLAN_PROPOSAL 再實作）：** 建議順序，可在 plan 裡改，但要說明理由：
1. 研究項（pq2）：D8 補三格讓邊緣公司浮上排序，D7 三檔先做。驗收：可投資排序出現幾檔 TPEx／STO／L。
2. D12 心跳＋分類：純 Python 排程、固定五段、`drain_limit_per_run` 歸零、Codex fixed entry 與 permission test 同 change 對齊。驗收：連續 3 天心跳零 LLM 成功發出且印出「未 triage N」。
3. D5 帳號登記表、蓋章、計分表、APP materialize；§6 回溯評分先用 492 則既有資料跑一版。驗收：計分表有 ≥1 個帳號、5 欄有值、印量測起始日與 n。
4. D11 篩選層機械條件 ＋ 籃子首選換條件（INV-3 逐檔報 reasons）。驗收：filter 報表 input／accepted／filtered 與 reasons 計數。
5. D2 對稱 overlay（判斷錯了值多少）、歸零旗標、alpha 全歸零 −X%；D3 realized 降為提醒；D15 追蹤表三個 power-law 統計量。驗收：COHR 與三檔初始標的各有這些格。
6. D15 台股月營收 datum、MOPS 重訊 watcher、lead 60 天到期計數。驗收：3081 有月營收序列；expired 計數出現在心跳。
7. 多年反向橋（「五倍要什麼為真」）取代 FY+1 主流程；entry criterion 降級。最後做，因為它是最大的契約變更。

**不得做：** 部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬條件、把 last30days 串進無人值守管線、在 Step 0 動程式、擅自開始下一個 Step。

**每個 Step 都要：** 先答「如果這個修法是錯的，最先壞掉的是哪一筆現有資料」（L11-6）並去看那一筆；驗收寫成「現有資料有幾筆真的變了」（L14）；unattended surface 變更同 change 做 sandbox impact review；改 skill 後跑 `scripts/sync_agent_skills.py`；收尾附建議摘要與可複製的批次指令。
