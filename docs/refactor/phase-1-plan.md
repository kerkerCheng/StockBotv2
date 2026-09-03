# Phase 1 — Alpha Contracts

> **性質：** Phase 0 產出物之一，也是下一步的施工圖。
> **前置：** 本檔與 [`current-architecture.md`](current-architecture.md)、
> [`target-architecture.md`](target-architecture.md)、
> [`engine-d-decomposition.md`](engine-d-decomposition.md)、
> [`roadmap-migration.md`](roadmap-migration.md) 邏輯一致後才開工。

---

## 1. Goal

**建立 Alpha Research Core 的型別契約與測試，一行既有 runtime 行為都不改。**

Phase 1 完成後，系統能做的事跟今天完全一樣；差別只在於**下一步（Phase 2）
可以在既有 code 之外獨立長出一條 vertical slice**，而不必先動 Engine D。

### ⚠ 這個 Phase 的驗收條件是特別的（L14 誠實處理）

L14 要求「說得出哪個現有數字會變」。Phase 1 的誠實答案是 **0 個現有數字會變**——
它是純新增。所以它**不得用「行為沒壞」當驗收**（那是恆真的），必須改用兩個替代條件：

1. **契約能承載真實資料**：用一個真實 cohort 的既有資料手工組出一個合法 `AlphaSignal`，
   若有欄位裝不下，就是契約設計錯了，當場改。
2. **每條新測試都要證明它不是空跑**：加測試的同時故意造一次違規（例如在
   `decision_lab/` 加一行 `import alpha`），確認測試**會紅**，再移除。
   （2026-08-28 U2 的教訓：宣稱「零行為變化」而沒有會紅的檢查，錯誤會原封不動進 master。）

---

## 2. Deliverables

### 2.1 新增檔案

```
alpha/
  __init__.py              package docstring：這一層的責任與禁止事項
  contracts.py             EvidenceRef / ResearchContext / AlphaSignal / AlphaModel
  causal.py                StructuralEvent / CausalPath / CompanyImpact / 三個 enum
  provider.py              GraphResearchProvider Protocol ＋ 回傳型別
  errors.py                PointInTimeUnsupported / ContractViolation
  testing.py               FakeGraphResearchProvider（給契約測試與 Phase 2 用）
```

**Phase 1 不寫任何 concrete provider、不寫 LLM 呼叫、不寫 CLI。**
`alpha/` 在 Phase 1 結束時是**純型別 ＋ 一個 fake**，沒有任何外部相依
（不 import neo4j、yfinance、anthropic、engine_c、decision_lab）。

### 2.2 型別清單（欄位定義見 `target-architecture.md` §2–§8）

| 型別 | 檔案 | 關鍵約束 |
|---|---|---|
| `EvidenceRef` | contracts | 三個時間欄位（`published_at`／`retrieved_at`／`recorded_at`）＋五套強度欄位並列，**不得壓成單一分數** |
| `FundamentalsSnapshot`／`MarketSnapshot`／`ConsensusSnapshot`／`ValuationSnapshot` | contracts | 每個欄位都是 `X \| None`；`None`＝不知道，不是 0 |
| `ScarcityInputs` | contracts | substitutability／sole_source／qualification_status／lead_time＋各自 evidence |
| `FreshnessState` | contracts | `(as_of, age_days, status)`；status ∈ available/stale/missing/quarantined（沿用 Engine D 既有字彙） |
| `ResearchContext` | contracts | `digest` 為 content-addressed；`freeze()` 是純函式 |
| `Catalyst` | contracts | **封閉字彙 `kind`**（見 §2.3） |
| `DisproofCondition` | contracts | `condition`＋`check_frequency`＋`action_within_48h`（L7 三件套，缺一即 raise） |
| `ComponentTrace` | contracts | `inputs`／`rule_version`／`evidence_refs`／`value` |
| `AlphaSignal` | contracts | **無任何 position 欄位**；每個非 None score 必須有 trace |
| `AlphaModel` | contracts | Protocol，`predict(ticker, as_of, context) -> AlphaSignal` |
| `StructuralEvent`／`CausalPath`／`CompanyImpact` | causal | `CompanyImpact.confidence` 取路徑最弱段 |
| `ImpactDirection`／`ImpactMagnitude`／`ImpactConfidence`／`TimeHorizon` | causal | enum |
| `GraphResearchProvider` | provider | 9 個方法，全部帶 `as_of`；回傳型別全部帶 `evidence` |

### 2.3 兩個新的封閉字彙（照 `closed-vocabulary-registry.md` 的判準）

| 字彙 | taxonomy 還是 contract | 住哪 | 理由 |
|---|---|---|---|
| `Catalyst.kind` | **taxonomy**（世界會長出新品類） | `config/catalyst_kinds.json` | 初版：qualification／design_win／competitor_exit／capacity_inflection／repricing／margin_inflection／production_ramp／inventory_reversal／estimate_revision／regulatory_transition／technology_transition |
| `StructuralEvent.kind` | **taxonomy** | `config/structural_event_kinds.json` | 初版見 `target-architecture.md` §8 |
| `EvidenceRef.kind` | **contract**（刻意有限） | code 內 `Literal` | 打開它是 bug——多一種 kind 代表多一個 provenance 路徑，必須有人設計 |

⚠ **新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`**，
否則 fresh clone 會缺檔而靜默失效（`tests/test_config_tracking.py` 是這道剎車）。

### 2.4 新增測試

```
tests/test_alpha_contracts.py          AlphaSignal / EvidenceRef schema 與必填規則
tests/test_alpha_provider_contract.py  GraphResearchProvider 的契約測試（跑在 fake 上）
tests/test_alpha_point_in_time.py      anti-lookahead
tests/test_alpha_causal.py             CausalPath / CompanyImpact 的 confidence 規則
tests/test_layer_separation.py         import 邊界
```

**逐條的最小斷言：**

| 測試 | 斷言 | 怎麼證明它不是空跑 |
|---|---|---|
| `test_alpha_signal_has_no_position_fields` | 掃 `AlphaSignal` 的欄位名，出現 `weight`／`shares`／`nav`／`size`／`target` 即失敗 | 暫時加一個 `weight: float` 欄位 → 必須紅（手法同 `tests/test_nav_exposure.py` 的禁用字掃描） |
| `test_score_without_trace_is_rejected` | 給一個有 `structural_score` 但 `model_components` 缺對應 key 的 payload → raise | 移掉檢查 → 必須紅 |
| `test_disproof_requires_frequency_and_action` | `DisproofCondition` 缺 `check_frequency` 或 `action_within_48h` → raise（L7） | 同上 |
| `test_none_is_not_zero` | `structural_score=None` 與 `=0.0` 產生不同的 `AlphaSignal`，且 `None` 不參與 `value` 計算 | 把 `None` 當 0 → 必須紅 |
| `test_provider_returns_evidence` | fake provider 的 9 個方法，每個回傳物件的 `evidence` 皆非空 | 讓 fake 回空 tuple → 必須紅 |
| **`test_as_of_raises_when_unsupported`** | `provider.get_bottlenecks(as_of=date(2026,6,30))` 在未實作 as-of 的 provider 上 **raise `PointInTimeUnsupported`**，**不得靜默回傳當前資料** | 改成回傳當前資料 → 必須紅。**這條是 Phase 6 的保險絲，Phase 1 就要裝** |
| **`test_filing_published_after_as_of_is_excluded`** | fake provider 帶兩份 SourceDoc（`published_at` 6/30 與 7/5），`as_of=6/30` 的 `ResearchContext` 的 `evidence_refs` **不含**後者 | prompt §19 的原句：7/5 才發布的 filing 不得出現在 6/30 的 ResearchContext |
| `test_missing_published_at_is_excluded_and_counted` | `published_at is None` 的證據在 as-of 模式下被排除，且計入 `context.freshness["evidence_undated_excluded"]` | L11-5：「我找不到 ≠ 它不存在」，不得默認當成在 T 之前 |
| `test_causal_confidence_is_weakest_link` | 三段 HIGH ＋ 一段 UNKNOWN 的路徑 → `CompanyImpact.confidence == UNKNOWN` | 改成平均 → 必須紅 |
| `test_decision_lab_does_not_import_alpha` | AST 掃 `decision_lab/`，無 `import alpha`／`portfolio`／`risk` | 暫時加一行 import → 必須紅 |
| `test_alpha_does_not_import_decision_store` | AST 掃 `alpha/`，無 `decision_lab.store`／`neo4j`／`yfinance`／`anthropic` | 同上 |
| `test_cypher_stays_in_query_layer` | 正規表達式掃 `alpha/`，無 `MATCH (`／`MERGE (`／`RETURN ` | 同上 |

---

## 3. 任務順序

| # | 任務 | 產出 | 為什麼是這個順序 |
|---|---|---|---|
| T1 | 寫 `alpha/contracts.py` 的 `EvidenceRef` ＋ `test_alpha_contracts.py` 的前三條 | 型別 | **`EvidenceRef` 先做**：它是所有其他型別的欄位，設計錯了全部要改 |
| T2 | **用真實資料驗證 `EvidenceRef`**：從圖裡取 5 條 EdgeAssertion、從 Engine C 取 3 筆 manual observation、從 Engine D 取 1 個 context bundle 的 reference index，手工組成 `EvidenceRef` | 一份 `tests/fixtures/alpha/evidence_refs_real.json` | ⚠ **這是 Phase 1 最重要的一步**。契約若裝不下真實資料，後面全白做 |
| T3 | `ResearchContext` ＋ 各 snapshot 型別 ＋ `freeze()` | 型別 | |
| T4 | `AlphaSignal` ＋ `ComponentTrace` ＋ `DisproofCondition` ＋ schema 測試 | 型別 | |
| T5 | **用真實 cohort 驗證 `AlphaSignal`**：取 COHR 或 LITE 的既有五軸 assessment ＋ variant perception ＋ rank row，手工組成一個 `AlphaSignal` | fixture | 同 T2 的理由 |
| T6 | `AlphaModel` Protocol ＋ `causal.py` ＋ 對應測試 | 型別 | |
| T7 | `provider.py` Protocol ＋ 回傳型別 ＋ `testing.FakeGraphResearchProvider` | 型別＋fake | |
| T8 | point-in-time 三條測試（含 `PointInTimeUnsupported`） | 測試 | |
| T9 | `test_layer_separation.py` 三條 import 邊界測試 | 測試 | 最後做：前面的檔案都存在了才掃得到 |
| T10 | 兩個 config 字彙檔 ＋ `.gitignore` 白名單 ＋ `test_config_tracking` 通過 | config | |

---

## 4. Exit criteria（可逐條驗證）

- [ ] `alpha/` 存在，6 個 `.py` 檔，**零外部相依**：
      `python -c "import alpha; import sys; print([m for m in sys.modules if m in ('neo4j','yfinance','anthropic','decision_lab')])"` → `[]`
- [ ] 新增 5 個測試檔、**≥ 12 條斷言**，全綠
- [ ] **每條斷言都做過「故意違規 → 確認會紅」的空跑檢查**，結果記在 commit message
- [ ] `tests/fixtures/alpha/` 有 2 份**由真實資料手工組成**的 fixture（T2、T5），
      且組裝過程中發現的契約缺口已回寫進 `target-architecture.md`
- [ ] 全套測試綠。**baseline 2026-09-03：`1175 passed, 0 skipped`（3 分 17 秒）**；
      Phase 1 後應為 `1175 + 新增條數 passed, 0 skipped`。查證：`python -m pytest -q`
- [ ] daily 端到端跑一次成功且輸出**內容不變**（pq2 項目數、首屏計數器與 Phase 1 前一致）
- [ ] `git diff --stat` 顯示 **`decision_lab/`／`engine_b/`／`engine_c/`／`query/`／`loader/` 的變更為 0 行**
      （Phase 1 是純新增；有任何一行動到既有 package 就代表 scope 漏了）

---

## 5. Non-goals（Phase 1 明確不做）

| 不做 | 什麼時候做 |
|---|---|
| concrete `GraphResearchProvider`（接 Neo4j） | Phase 2 |
| LLM assessor | Phase 2 |
| `python -m alpha research <TICKER>` CLI | Phase 2 |
| 搬任何一行 `decision_lab/` 的 code | Phase 3（B1 除外，見下） |
| Expectation Gap 的計算 | Phase 4 |
| Engine C 欄位擴充（forwardEps 等） | Phase 4 |
| as-of 圖投影的實作 | Phase 6 前置 |
| 改 `.codex/rules` 的 16 條 command prefix | 全部穩定後一次改 |

**唯一的例外討論：** `engine-d-decomposition.md` 的 **B1（Portfolio/Risk 搬家，約 2,054 行）**
技術上可以與 Phase 1 平行，因為它完全不依賴新契約。
**但建議排在 Phase 1 之後、Phase 2 之前**——先讓 Phase 1 的「零既有 package 變更」
驗收條件保持乾淨，B1 才有一個明確的 before/after 可以對照。

---

## 6. 風險與對策

| 風險 | 徵兆 | 對策 |
|---|---|---|
| **契約設計得太漂亮但裝不下真實資料** | T2/T5 組 fixture 時發現欄位不夠 | 這正是 T2/T5 排在前面的理由。**發現就當場改契約，不要在 Phase 2 才發現** |
| **`AlphaSignal` 悄悄長出 position 欄位** | 有人想加 `suggested_weight` | `test_alpha_signal_has_no_position_fields` 的禁用字掃描 |
| **五個 score 被固定加權成 `value`** | `composite.py` 出現 `0.3*a + 0.2*b + ...` | Phase 1 就把 `value` 的推導定義成具名、版本化的 `CompositionRule`，並要求它能回答「換規則有幾筆排序會變」 |
| **Phase 1 悄悄變成 Phase 2** | `alpha/` 開始 import neo4j | exit criteria 第一條（零外部相依）＋ `test_alpha_does_not_import_*` |
| **daily 被打斷** | 排程失敗 | Phase 1 不動任何 entry point；exit criteria 有「既有 package 零變更」 |
| **文件與程式漂移** | 契約改了但 `target-architecture.md` 沒改 | exit criteria 第四條要求把 T2/T5 的發現回寫 |

---

## 7. 之後的 Phase（只列 Goal 與 Exit，細節到時再展開）

| Phase | Goal | Exit criteria |
|---|---|---|
| **2 — First research vertical slice** | 一支 ticker 從 graph context → financial → expectations → `AlphaSignal`，能跑 `python -m alpha research COHR` | ①輸出的每個 score 都能 explain 到 `EvidenceRef`；②圖零新增節點；③與現行 `rank_bottlenecks` 首選一致或能說明為何不一致 |
| **3 — Engine D decomposition** | 執行 B2–B6（B1 已在 Phase 1.5） | `decision_lab/` 13,502 → ≤8,000 行；直接相依環 3 → 0；daily 輸出內容不變且 bytes 下降 |
| **4 — Expectation Gap** | implied fundamentals vs market implied | `expectation_gap_score` 對 ≥5 檔可算出且能 explain；低 P/E 案例的 gap ≈ 0 |
| **5 — Causal propagation** | `StructuralEvent` → `CompanyImpact` | 對 ≥1 個真實事件產出 ≥1 個二階受益／受害者，且路徑可追溯 |
| **6 — Backtest / validation** | as-of 圖投影 ＋ anti-lookahead 回測 | SourceDoc `published_at` 覆蓋 → 100%；as-of provider 通過 anti-lookahead 測試；排序前段 vs 後段的等權報酬差有 ≥2 期 |
| **7 — Portfolio / Risk** | view → target exposure → limits | 三個硬擋行為與現況逐筆一致（characterization 測試）；不新增任何 alpha 尺寸 |
| **8 — Automation / productization** | daily／weekly／skills／MCP 適配新架構 | 16 條 sandbox rule 完成 impact review；skills 同步 `--check` 無漂移 |
