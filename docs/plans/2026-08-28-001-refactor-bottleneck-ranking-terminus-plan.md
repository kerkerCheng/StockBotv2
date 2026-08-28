---
title: Bottleneck Ranking as System Terminus - Plan
type: refactor
date: 2026-08-28
topic: bottleneck-ranking-terminus
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-brainstorm
execution: code
---

# Bottleneck Ranking as System Terminus - Plan

## Goal Capsule

- 目標：系統終點由「資本額度」改回「瓶頸度排序」。五軸算出每檔的排序與最弱軸，以股票為單位輸出，使用者可見輸出中不出現任何部位百分比。
- 反向新增：Google Sheet 各股 NAV 比例純呈現，失衡由使用者看數字自行判斷。
- Product authority：`query/bottleneck.py` 的 `rank_bottlenecks()` 仍是唯一排序權威；`AGENTS.md` 是政策 SSOT，本次會推翻其中的 alpha 資本表達段落。
- 不變：live 永遠由使用者手動下單，Google Sheet 仍是 live inventory 唯一權威，graph admission 與 Engine C ledger 寫入的人工 gate 不受影響。
- Open blockers：`decision_lab today` 首屏的新結構未定（見 Outstanding Questions）。

---

## Product Contract

### Summary

把 Engine D 的資本表達層（`supported_range`／`axis_ceiling`／probe cap／paper target）從系統終點移除，終點改回五軸驅動的瓶頸度排序，以股票為單位輸出、不給額度。同時新增反向的持股 NAV 比例呈現，作為事後失衡檢視而非事前限制。

### Problem Frame

系統目前的終點是一組資本數字，而那組數字擋住了它自己。

2026-08-28 實測：21 個 operational cohort 中 20 個 `live_supported_range` 為 `[0.0, 0.0]`。對排序第一名的 COHR 追下去，`assessment_blockers` 是空的、`live_blockers` 是空的，`constraint_trace` 顯示三個資本風控（單筆 5%、single probe 0.5%、probe book 2%）**沒有一個 binding**，唯一 binding 的是 `weakest_axis`，cap 0.002。換算後是 2.94 股、約 869 美元。

那個 0.002 來自 `confidence-envelope-v1`，而 `measured_outcomes` 是 2/12。也就是一個從未被驗證的機制在決定資本——正是 `AGENTS.md` L14 明文禁止的事。同一份文件在 2026-08-15 已記錄過使用者的判斷：「繞了這麼久只得到我很早就看到的幾間公司、都等於 0.2%，我會不知道我到底做了什麼」。當時的結論是「alpha 對使用者的輸出是候選＋事件追蹤，不是部位尺寸」，但只做了一半——paper lane 留著、`supported_range` 仍在輸出、`axis_ceiling` 仍在決定資本。

代價不只是數字沒用。整條漏斗因此無法解讀：786 個 lead 進來、41 個入圖、1 筆 live choice，而中間那段的損耗有多少來自研究不足、有多少來自這組額度，從輸出上看不出來。

使用者對這批數字的定位很明確：沒有建立過合邏輯的上限規則，只有一堆 0.002／0.005。買入尺寸由使用者在買入前自行判斷，或當下對話決定。

### Key Decisions

**Outcome 量測改為等權重報酬追蹤** (session-settled: user-directed — chosen over 保留 paper lane 0.1% 模擬部位：要能回答「排序準不準」，但不要任何額度)。只記錄「哪天推薦了這檔、當時股價、之後報酬率」，等權重比較。paper lane 的 0.1% 部位、probe book、paper target 全部移除。

**Decision 記錄保留 context 凍結與 catalyst／disproof，移除 action_card 四動作與 sizing** (session-settled: user-directed — chosen over 全拔或只拔 sizing)。事後檢討需要知道「當時根據什麼推薦」，到期提醒需要 catalyst／disproof；四動作在沒有額度後語意不完整，`NO_ACTION`／`TRADE`／`HEDGE` 失去對象。

**「這檔還缺什麼」改由 weakest_axis 導出** (session-settled: user-directed — chosen over 沿用 `decision_review` 判定)。五軸已經算出最弱軸（COHR 是 `technical_causal_link`，因 counter_paths 為空）。直接拿它當 pq2 項目，與「提高排序」是同一個目的，不再經過資本語意。

**NAV 比例監控純呈現、零門檻** (session-settled: user-directed — chosen over 帶相對比較標記)。只算並列出各股 NAV%、bucket 分布、相關性分組。不判斷好壞、不告警。

**beta 的槓桿 ETF cap 不動。** 使用者要移除的是 alpha 那批憑空的 0.002／0.005；`config/beta_policy.json` 的 nominal／effective cap 對應真實歸零與追繳風險，且屬另一個 sleeve，留在原地。

**既有 decision 記錄不改寫。** 依 L10，Decision Store 是沒有第二份來源的 private append-only authority，只允許 backup／restore 與 append-only correction。歷史 128 筆 decision 仍會帶著 sizing 欄位；本次只停止新增，不做破壞性 migration。

### Requirements

**終點改為排序輸出**

R1. 使用者可見的 alpha 輸出以股票為單位，每檔至少含：排序名次、卡在哪條邊、替代難度、證據等級、需求錨點、最弱軸。
R2. 排序來源是 `query/bottleneck.py` 的 `rank_bottlenecks()`，不另建平行排序。
R3. 排序表同時保留既有的兩份輸出語意：`rows`（可行動，證據優先）與 `structural_rows`（純結構，回答該去補誰的證據），兩者不可互換。
R4. 排序輸出必須標明它是研究判斷，不是回測或統計勝率，並附各候選的 disproof。

**移除資本表達**

R5. 使用者可見輸出中不出現 `live_supported_range`、`axis_ceiling`、`paper_target`、probe cap 或任何部位百分比。
R6. `action_card` 的四動作（`NO_ACTION`／`REVIEW`／`TRADE`／`HEDGE`）自使用者可見輸出移除。
R7. 五軸保留，角色由「決定資本上限」改為「決定排序與指出最弱軸」；各軸的 `level` 與 `missing_data` 續用，`ceiling` 數值停止產生。
R8. Decision 記錄續存 context bundle digest 與 catalyst／disproof；停止寫入 sizing 欄位。

**Outcome 量測改制**

R9. Outcome 記錄改為「推薦日、當時價格、後續報酬率」，不含部位大小或 NAV 比例。
R10. Outcome 可回答「排序前段的標的，後續報酬是否優於後段」；比較基準為等權重。

**NAV 比例呈現（新增）**

R11. 從 Google Sheet 讀取持股，輸出各標的佔 NAV 百分比。
R12. 併同輸出 bucket 分布（現況為 CORE／大盤／觀察／CASH／槓桿）與相關性分組（例：AI 光互連合計佔比）。
R13. 不設門檻、不告警、不阻擋任何動作；輸出為純數字呈現。

**缺口浮現改道**

R14. pq2 的研究缺口項目由各標的的最弱軸導出，項目文字須指出「補哪一檔的哪一軸」。
R15. 缺口項目的 `go` 仍只授權 bounded research；graph admission、Engine C ledger 寫入、thesis mutation 各自的人工 gate 不因本次變更放寬。

### Acceptance Examples

AE1. **Covers R1, R5.** 對排序第一名的 COHR 輸出時，顯示「卡在 `supplies_to → co:nvidia`、替代難度 5/5｜sole_source、證據外部印證、最弱軸 `technical_causal_link`」，不顯示任何股數或百分比。

AE2. **Covers R14.** COHR 的最弱軸是 `technical_causal_link`（counter_paths 為空），pq2 項目應為「補 COHR 的 counter-path 證據：什麼會讓 NVIDIA 不從 COHR 買」，而非「REVIEW — co:coherent」。

AE3. **Covers R11, R13.** NAV 呈現對某檔佔 18% 的持股，輸出「18%」並列在表中，不附加任何警示文字或建議。

AE4. **Covers R8.** 對既有 cohort 執行 reassess 後，新 decision 含 context digest 與 disproof，不含 `live_supported_range` 欄位；查詢舊 decision 仍能取回它當時的 sizing（歷史不改寫）。

### Success Criteria

- 使用者可見輸出中的部位百分比數量為 0（可用關鍵字掃描驗證）。
- `decision_lab today` 首屏是排序表，不是四動作分類。
- NAV 呈現可對現有 24 列持股跑出結果。
- 既有 128 筆 decision 與 12 筆 outcome 記錄未被改寫，可原樣讀回。
- 拔除後至少有一個 pq2 缺口項目由 weakest_axis 導出並可被執行。

### Scope Boundaries

**不在本次範圍**

- `config/beta_policy.json` 的槓桿 ETF nominal／effective cap——真實風險，非憑空數字。
- `config/investment_policy.json` 的 5% 單筆上限——保留作為 NAV 呈現時的參考線，但不再進入任何 gate 判定。
- 歷史 decision／outcome 的資料 migration——append-only，只停止新增。
- broker 整合與自動下單——本來就不做。
- `query/bottleneck.py` 排序演算法本身——它已是權威，本次只改它的消費端與輸出形式。

### Dependencies / Assumptions

- 假設 `rank_bottlenecks()` 的 `substitutability` 覆蓋率（現為 60/413，15%）足以支撐排序作為終點。覆蓋率偏低會讓排序偏向已被抽取過的邊——這是既有限制，本次不解決，但輸出須沿用排序表現有的「已知限制」聲明。
- `weakest_axis` 目前由 `decision_lab/sizing.py` 計算。移除 sizing 的資本部分時，最弱軸的計算需保留並改掛到排序輸出上。
- Google Sheet 讀取路徑（`fetchers/gsheets.py`）已驗證可用，24 列、含 bucket 欄位。
- 12 個 production 模組與 16 個測試檔引用 `supported_range`／`axis_ceiling`／`paper_target`，變更面須一次涵蓋。

### Outstanding Questions

**Resolved（2026-08-28）**

- `decision_lab today` 首屏結構：**排序在前、NAV 在後**。排序區同時列 `rows`（可行動）與 `structural_rows`（研究 ROI 最高），兩份並列且標明用途不同。

**Deferred to Planning**

- weakest_axis 轉成 pq2 項目文字的具體模板（每一軸各自的「該補什麼」措辭）。
- Outcome 等權重報酬的計算窗口（自推薦日起算幾天／到 catalyst 為止）。
- 相關性分組的判定來源（由圖的鏈路推導，或由人工維護的分組表）。

### Sources / Research

- 2026-08-28 實測，COHR cohort `dc_957bff3701ea4e46d962bfb9ff0932c8`：`constraint_trace` 顯示 `weakest_axis` 是唯一 binding 的 cap（0.002），三個資本風控皆 `binding: false`。
- 同日實測：21 個 operational cohort 中 20 個 `live_supported_range` 為 `[0.0, 0.0]`；`capital_expression_counters()` 回 `measured_outcomes 2/12`、`eligible_cohorts 8/16`。
- `AGENTS.md`「Alpha 呈現契約（2026-08-15 使用者定案）」與 L14——本次是把該契約未完成的另一半做完。
- `AGENTS.md` L10 的適用範圍註記——Decision Store 屬不可重建的 private authority，只能 append。
- 變更面：`decision_lab/sizing.py`（595 行）、`decision_lab/action_card.py`（546 行）、`decision_lab/coverage.py`（193 行），以及 `decision_lab/brief.py`、`decision_lab/outcomes.py`、`decision_lab/store.py`、`decision_lab/models.py`、`decision_lab/cli.py`、`decision_lab/beta_monitor.py`、`decision_lab/blocker_severity.py`、`decision_lab/capital_authority.py`、`thesis/investment_policy.py`。
- `decision_lab/brief.py` 的 `_ACTION_PRIORITY = {"NO ACTION": 0, "TRADE": 1, "HEDGE": 2, "REVIEW": 3}` 是首屏排序鍵，移除四動作後須一併重寫。
- `decision_lab/sizing.py:376` 的 `weakest_axis = min(AXES, key=lambda axis: (axes[axis]["ceiling"], AXES.index(axis)))`——最弱軸目前以 ceiling 排序，而 ceiling 正是要移除的欄位。
- `decision_lab/outcomes.py:_market_outcome` 以 `store.get_shadow(cohort_id)` 取價格錨點，該錨點與部位大小無關。

---

## Planning Contract

**Product Contract preservation：** Product Contract 未變更。本次 enrichment 只新增 Planning Contract 以下內容，並把 Outstanding Questions 的 `Resolve Before Planning` 標為已解決。

### Key Technical Decisions

**KTD1. `weakest_axis` 改用 `LEVELS` 排序，tie-break 沿用 `AXES` 宣告次序** (session-settled: user-approved — chosen over 保留 ceiling 排序：ceiling 正是要拔除的東西)。改以 `LEVELS.index(axes[axis]["level"])` 為主鍵，`unknown` < `bounded_hypothesis` < `corroborated`。⚠ level 只有三階，比 ceiling 粗，同階並列會變常見；tie-break 沿用 `AXES.index()`，即 `source_reliability` 優先。這與實測相符：13 個 active cohort 的最弱軸幾乎全是 `source_reliability`。

**KTD2. 保留 shadow 錨點，只拔 paper 部位** (session-settled: user-approved — chosen over 連 shadow 一起拔)。等權重報酬需要推薦當天的價格，該價格由 shadow observation 提供，而它只有價格與時點、不含部位大小。被移除的是 `paper_target`、`paper_max_supported_position` 與 probe book 的資本語意。

**KTD3. 不設過渡 unit，接受 `today` 中途半新半舊** (session-settled: user-directed — chosen over 先寫新首屏再切換)。U6 之前 `_ACTION_PRIORITY` 仍在。本機單人使用，過渡期成本低於多一個 unit 的複雜度。

**KTD4. 歷史 decision 不做 migration。** 依 L10，Decision Store 是不可重建的 private append-only authority。sizing 欄位停止新增，既有 128 筆原樣保留；讀取端遇舊欄位時忽略，不回寫。

**KTD5. NAV 呈現獨立成模組，不進 `sizing.py`。** 它是事後檢視，與資本閘門無關；放進 sizing 會讓已拔除的資本語意從另一個門回來。

### System-Wide Impact

- `decision_lab today` 的輸出結構改變——那是使用者每日入口。
- `engine_b.todo` 的 `decision_review` collector 來源與項目文字改變。
- Daily routine 文件（`crons/daily_brief_prompt.md`、`skills/daily-brief/SKILL.md`、`skills/alpha-status/SKILL.md`）對首屏的描述需同步。
- `.codex/rules` 不受影響：本次不新增 CLI 入口。

---

## Implementation Units

### U1. NAV 比例呈現

**Goal：** 從 Google Sheet 讀持股，輸出各標的佔 NAV 百分比、bucket 分布與相關性分組。純新增，不動既有程式碼。

**Requirements：** R11, R12, R13

**Dependencies：** 無

**Files：** 建立 `decision_lab/nav_exposure.py`、`tests/test_nav_exposure.py`

**Approach：** 沿用 `engine_d_runtime/adapters.py` 的持股取得路徑（已正規化，含 `market_value_base`、`bucket`、`is_cash`），以 `nav_base` 為分母算百分比。bucket 分布依 Sheet 欄位彙總。相關性分組由 `co:*` 在圖中的鏈路推導，取不到時標「未分組」而非猜測。

**Execution note：** 純新增且輸出為數字，適合 test-first——先寫「給定持股列回傳百分比」的失敗測試再實作。

**Patterns to follow：** `decision_lab/beta_monitor.py` 的唯讀 snapshot 組裝；`adapters.py::current_holdings` 的 fail-closed 慣例（含 `failure` marker）。

**Test scenarios：**
- 給定 24 列持股與 `nav_base`，各標的百分比加總為 1.0（容浮點誤差）。
- 現金列計入 NAV 分母但不列為標的曝險。
- `bucket` 缺漏歸「未分類」，不丟棄也不報錯。
- holdings 回 `unavailable` 時回傳明確不可用結果並帶上 upstream `failure`，不得回空字典假裝零曝險。
- 相關性取不到圖鏈路時歸「未分組」。
- 零門檻斷言：輸出不得出現 `cap`／`limit`／`warning`／`breach` 欄位。

**Verification：** 對現有 24 列跑出結果，百分比加總 1.0，輸出無門檻欄位。

### U2. weakest_axis 改用 LEVELS 排序

**Goal：** 讓最弱軸不再依賴 `ceiling`，為 U5 與 U7 鋪路。

**Requirements：** R7；支撐 R14

**Dependencies：** 無

**Files：** 修改 `decision_lab/sizing.py`、對應測試檔

**Approach：** 依 KTD1 換排序主鍵。此時 `ceiling` 仍存在（U7 才移除），本 unit 只換鍵不刪欄位，讓改動可獨立驗證。

**Execution note：** 先寫「同 level 依 AXES 次序 tie-break」的失敗測試再改。

**Test scenarios：**
- 五軸 level 各異時回傳 level 最低者。
- 兩軸同為 `unknown` 時回傳 `AXES` 中較前者。
- 全部 `corroborated` 時仍回傳確定值而非 None。
- 回歸：COHR 的最弱軸仍為 `technical_causal_link`。

**Verification：** 對 13 個 active cohort 重算，最弱軸分布與實測一致（多數 `source_reliability`）。

### U3. 瓶頸排序輸出

**Goal：** 產生股票為單位的排序輸出，含名次、卡點邊、替代難度、證據等級、需求錨點、最弱軸，並保留兩份排序語意。

**Requirements：** R1, R2, R3, R4

**Dependencies：** U2

**Files：** 建立 `decision_lab/ranking_view.py`、`tests/test_ranking_view.py`

**Approach：** 消費 `query/bottleneck.py::rank_bottlenecks`，不另建排序邏輯。把 U2 的最弱軸接到每列。沿用排序表既有的「已知限制」聲明措辭，不重寫。

**Test scenarios：**
- 輸出同時含 `rows` 與 `structural_rows` 且不互換。
- 每列含最弱軸欄位。
- 含「研究判斷、非回測或統計勝率」標註與各候選 disproof。
- 零額度斷言：不含 `supported_range`／`axis_ceiling`／`paper_target` 或任何部位百分比。

**Verification：** 對現有圖跑出排序，第一名為 COHR→NVIDIA，輸出無部位數字。

### U4. Outcome 改等權重報酬追蹤

**Goal：** Outcome 改記「推薦日、當時價格、後續報酬率」，移除部位與 NAV 佔比語意。

**Requirements：** R9, R10

**Dependencies：** U3

**Files：** 修改 `decision_lab/outcomes.py`、對應測試檔

**Approach：** 保留 shadow 作為進場價錨點（KTD2）。移除 payload 中的部位與 NAV 佔比欄位。比較基準改等權重：排序前段與後段的報酬中位數。既有 12 筆依 KTD4 不改寫，讀取端須容忍舊欄位。

**Execution note：** 動的是 append-only ledger 的寫入格式——先加 characterization 測試鎖住既有 12 筆的讀取行為，再改寫入端。

**Test scenarios：**
- 新 outcome 含推薦日、進場價、報酬率，不含部位或 NAV 佔比。
- shadow 為 `unavailable` 時標為不可量測，不得以 0 充數。
- characterization：讀取既有舊格式 outcome 不報錯。
- 等權重比較：給定前後段報酬，回傳兩組中位數。

**Verification：** `capital_expression_counters()` 的 `measured_outcomes` 分子不因格式改動而變。

### U5. 缺口由 weakest_axis 導出 pq2

**Goal：** pq2 缺口項目改由最弱軸產生，文字指出補哪一檔的哪一軸。

**Requirements：** R14, R15

**Dependencies：** U2, U3

**Files：** 修改 `engine_b/todo.py`、對應測試檔

**Approach：** collector 觸發來源由 `action_card` 的 REVIEW 判定改為最弱軸。每軸對應一句「該補什麼」：`source_reliability` 補獨立來源、`technical_causal_link` 補 counter-path、`commercial_maturity` 補客戶端商業承諾、`financial_resilience` 補 Engine C 財務觀測、`valuation_payoff` 補估值錨點。`go` 仍只授權 bounded research。

**Patterns to follow：** `engine_b/todo.py` 的 `SOURCE_COLLECTORS` 登記方式與 hint 措辭。

**Test scenarios：**
- 最弱軸為 `technical_causal_link` 的 cohort 產生「補 counter-path」項目，文字含標的與軸名。
- 五軸各自產生對應措辭，無「REVIEW — co:xxx」這種無成因文字。
- 回歸：項目的 `go` 不觸發 graph admission、Engine C 寫入或 thesis mutation。
- 已有 in-flight work order 的 cohort 不重複產生項目。

**Verification：** 對 13 個 active cohort 跑 sync，缺口項目數與最弱軸分布一致，每項都指名軸別。

### U6. today 首屏重寫

**Goal：** 首屏改為排序在前（兩份並列）、NAV 在後；移除四動作排序鍵。

**Requirements：** R1, R5, R6

**Dependencies：** U1, U3

**Files：** 修改 `decision_lab/brief.py`、對應測試檔

**Approach：** 移除 `_ACTION_PRIORITY`，改以排序名次為主序。`build_today_brief` 組裝順序改為排序區 → NAV 區 → 其餘既有區塊，`render_today_markdown` 同步。依 KTD3 不設過渡。

**Test scenarios：**
- 首屏第一個區塊是排序，含兩份。
- NAV 區在排序之後。
- 輸出不含四動作字樣。
- 輸出不含任何部位百分比。
- 排序為空時仍渲染區塊並說明原因，不得整段消失。

**Verification：** 跑 `decision_lab today`，首屏為排序表，全文無四動作字樣與部位數字。

### U7. 移除資本表達層

**Goal：** 移除 `supported_range`／`axis_ceiling`／`paper_target`／probe cap 與四動作的產生端。

**Requirements：** R5, R6, R7, R8

**Dependencies：** U2, U3, U4, U5, U6

**Files：** 修改 `decision_lab/sizing.py`、`decision_lab/action_card.py`、`decision_lab/coverage.py`、`decision_lab/store.py`、`decision_lab/models.py`、`decision_lab/cli.py`、`decision_lab/blocker_severity.py`、`decision_lab/capital_authority.py`、`decision_lab/beta_monitor.py`、`thesis/investment_policy.py` 與對應測試檔

**Approach：** 停止產生 sizing 欄位與四動作；保留 decision 的 context digest 與 catalyst／disproof。五軸的 `level` 與 `missing_data` 續用，`ceiling` 停止產生。讀取端須容忍既有 128 筆的舊欄位。⚠ `beta_monitor.py` 與 `capital_authority.py` 屬 beta sleeve，只移除 alpha 的 axis ceiling 引用，不動槓桿 cap。

**Execution note：** 影響面最大——逐檔改並在每檔後跑該檔測試，不要一次改完再跑。

**Test scenarios：**
- 新 decision payload 不含 `live_supported_range`／`axis_ceiling`／`paper_target`。
- characterization：讀取既有帶 sizing 欄位的舊 decision 不報錯。
- `action_card` 不再輸出四動作。
- 回歸：`config/beta_policy.json` 的槓桿 cap 仍生效。
- `config/investment_policy.json` 的 5% 上限可被 NAV 呈現引用為參考線，但不進入任何 gate 判定。

**Verification：** 全套測試通過；對既有 cohort 跑 reassess 產生的 decision 無 sizing 欄位；beta snapshot 槓桿 cap 行為不變。

### U8. 文件與 routine 描述同步

**Goal：** 讓政策與 routine 文件對首屏與 alpha 輸出的描述與實作一致。

**Requirements：** R1, R5

**Dependencies：** U6, U7

**Files：** 修改 `AGENTS.md`、`crons/daily_brief_prompt.md`、`skills/daily-brief/SKILL.md`、`skills/alpha-status/SKILL.md`

**Approach：** 把 2026-08-15 契約中「paper lane 繼續運作」與 supported range 相關描述更新為現況。依「現況數字會過期，判準不會」，新描述附查證命令而非寫死數字。

**Test scenarios：** `Test expectation: none -- 純文件同步，無行為變更。` 替代驗證：`python scripts/sync_agent_skills.py --check` 通過，且文件中不再出現已移除的欄位名。

**Verification：** skill 轉接層同步檢查通過；`supported_range`／`axis_ceiling` 在 docs 與 skills 中無殘留描述。

---

## Verification Contract

| 閘門 | 命令 | 通過條件 |
|---|---|---|
| 全套測試 | `python -m pytest tests/ -q` | 全綠 |
| Skill 轉接層 | `python scripts/sync_agent_skills.py --check` | in sync |
| 零額度 | 於使用者可見輸出路徑 grep `supported_range`、`axis_ceiling`、`paper_target` | 無命中 |
| 四動作已移除 | 跑 `decision_lab today` 後 grep `NO ACTION`、`TRADE`、`HEDGE` | 無命中 |
| 歷史未改寫 | `capital_expression_counters()` 的 `decisions` 與 `outcomes` 分母 | 不減少 |
| beta 未誤傷 | `scripts/daily_beta_snapshot.py --format markdown` | 槓桿 cap 行為不變 |
| NAV 可跑 | `decision_lab/nav_exposure.py` 對現有 24 列 | 百分比加總為 1.0 |

## Definition of Done

- 八個 unit 全部完成，各自的 Verification 通過。
- 使用者可見輸出中的部位百分比數量為 0。
- `decision_lab today` 首屏是排序表（兩份並列），NAV 比例在後。
- 至少一個 pq2 缺口項目由 weakest_axis 導出並指名軸別。
- 既有 128 筆 decision 與 12 筆 outcome 可原樣讀回，未被改寫。
- `config/beta_policy.json` 槓桿 cap 與 `config/investment_policy.json` 5% 上限行為未變。
- 全套測試通過，skill 轉接層 in sync。
