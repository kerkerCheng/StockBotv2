---
title: Bottleneck Ranking as System Terminus - Plan
type: refactor
date: 2026-08-28
topic: bottleneck-ranking-terminus
artifact_contract: ce-unified-plan/v1
artifact_readiness: requirements-only
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

**Resolve Before Planning**

- `decision_lab today` 首屏的新結構：排序表要顯示幾檔、依 `rows` 還是 `structural_rows` 排、NAV 呈現放在排序之前或之後。

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
