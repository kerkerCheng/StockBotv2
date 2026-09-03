# Phase 1 — Alpha Contracts

> **性質：** Phase 0 產出物之一，也是下一步的施工圖。
> **前置：** 本檔與 [`current-architecture.md`](current-architecture.md)、
> [`target-architecture.md`](target-architecture.md)、
> [`engine-d-decomposition.md`](engine-d-decomposition.md)、
> [`roadmap-migration.md`](roadmap-migration.md)、
> [`historical-failure-matrix.md`](historical-failure-matrix.md) 邏輯一致後才開工。
>
> ⚠ **開工前必讀 `historical-failure-matrix.md` §2 的六條 hard invariant 與 §9 的
> completion gate。** Phase 1 不是「寫幾個 dataclass」——它的一半價值在於
> **把三個歷史事故的防線做進型別**（§2.1b）。

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
                           ＋ RankedList（截斷集合必帶完整 id 集合，見 F-20）
  causal.py                StructuralEvent / CausalPath / CompanyImpact / 三個 enum
  provider.py              GraphResearchProvider Protocol ＋ 回傳型別
  errors.py                PointInTimeUnsupported / ContractViolation
  identity.py              CompanyId / InstrumentId / Ticker / Alias 型別（INV-1）
  testing.py               FakeGraphResearchProvider（給契約測試與 Phase 2 用）
  audit/
    __init__.py            runtime invariant checker 骨架（12 個 check 的註冊表）
```

### 2.1b 三個由歷史事故直接導出的型別（不是可選的）

出自 [`historical-failure-matrix.md`](historical-failure-matrix.md)。
**Phase 1 的 completion gate 第 8 項就是這三個。**

| 型別 | 防哪個事故 | 為什麼型別層才擋得住 |
|---|---|---|
| **`RankedList[T]`**：同時帶 `rows`（截斷後）與 `full_ids`（截斷前完整集合） | **F-20**：ranking DTO 只帶前 `limit` 名，直接比對把排 11 名之後的公司誤判成「不在排序」 | 只要有人拿 `rows` 做成員判斷就會錯；**把完整集合綁在同一個型別上，成員判斷才有正確的東西可用**（INV-3） |
| **每個 score 都有 `declared` 與 `effective` 兩個值**（或 `effective_*` 顯性欄位） | **F-25**：`weakest_axis` 用 raw `level` 排序會漏掉「宣告 corroborated 但引用不成立」的軸——ceiling 被打成 0 卻不動 level | `AlphaSignal` 的 5 個 score 有**完全相同的形狀**（宣告 vs 引用實際成立）。不顯性化就會重演 |
| **`CompanyId` / `InstrumentId` / `Ticker` 是不同型別，不是 `str`** | **F-01～F-05**：`co:sivers` 猜錯 ID、報價單位當結算幣別、registry 缺欄位靜默關管線 | `str` 讓四種 identifier 可以互相賦值；分型別後**編譯／型別檢查層就擋得住**，不必靠人記得（INV-1） |

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
| `AlphaSignal` | contracts | **無任何 position 欄位**；**無 scalar `value`／`alpha`**（2026-09-03 定案，見 `target-architecture.md` §5 硬規則 4）；每個非 None score 必須有 trace；排序由 `ordering_key()` 字典序產生 |
| `Score` | contracts | `declared` / `effective` / `trace` / `downgrade_reason`（F-25） |
| `OrderingRule` | contracts | 具名、版本化的排序鍵順序；換規則要能答出「幾筆排序會變」 |
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
| `test_none_is_not_zero` | `structural_score=None` 與 `=0.0` 產生不同的 `AlphaSignal`；`None` 排最後且該 signal 標 `incomplete`，**不得當 0 參與比較** | 把 `None` 當 0 → 必須紅 |
| **`test_alpha_signal_has_no_composite_scalar`** | 掃 `AlphaSignal` 欄位名，出現 `value`／`alpha`／單數總分 `score` 即失敗；排序只能經 `ordering_key()` | 加一個 `value: float` → 必須紅（2026-08-21 加權總分補償性的直接繼承） |
| `test_provider_returns_evidence` | fake provider 的 9 個方法，每個回傳物件的 `evidence` 皆非空 | 讓 fake 回空 tuple → 必須紅 |
| **`test_as_of_raises_when_unsupported`** | `provider.get_bottlenecks(as_of=date(2026,6,30))` 在未實作 as-of 的 provider 上 **raise `PointInTimeUnsupported`**，**不得靜默回傳當前資料** | 改成回傳當前資料 → 必須紅。**這條是 Phase 6 的保險絲，Phase 1 就要裝** |
| **`test_filing_published_after_as_of_is_excluded`** | fake provider 帶兩份 SourceDoc（`published_at` 6/30 與 7/5），`as_of=6/30` 的 `ResearchContext` 的 `evidence_refs` **不含**後者 | prompt §19 的原句：7/5 才發布的 filing 不得出現在 6/30 的 ResearchContext |
| `test_missing_published_at_is_excluded_and_counted` | `published_at is None` 的證據在 as-of 模式下被排除，且計入 `context.freshness["evidence_undated_excluded"]` | L11-5：「我找不到 ≠ 它不存在」，不得默認當成在 T 之前 |
| `test_causal_confidence_is_weakest_link` | 三段 HIGH ＋ 一段 UNKNOWN 的路徑 → `CompanyImpact.confidence == UNKNOWN` | 改成平均 → 必須紅 |
| `test_decision_lab_does_not_import_alpha` | AST 掃 `decision_lab/`，無 `import alpha`／`portfolio`／`risk` | 暫時加一行 import → 必須紅 |
| `test_alpha_does_not_import_decision_store` | AST 掃 `alpha/`，無 `decision_lab.store`／`neo4j`／`yfinance`／`anthropic` | 同上 |
| `test_cypher_stays_in_query_layer` | 正規表達式掃 `alpha/`，無 `MATCH (`／`MERGE (`／`RETURN ` | 同上 |
| **`test_core_does_not_import_mcp_server`** | AST 掃 `alpha/`／`portfolio/`／`risk/`，無 `import mcp_server`。⚠ **暫不涵蓋既有 package**——今天 `engine_b/todo.py` 等 5 處會紅，那是 Phase 3 的範圍，測試要用 explicit allowlist 記下這 5 個已知例外並在 Phase 3 逐一移除 | allowlist 為空時對 `engine_b` 跑一次 → 必須紅 |
| **`test_ranked_list_carries_full_id_set`** | `RankedList` 截斷後 `rows` 少於 `full_ids`，且成員判斷 API 只吃 `full_ids` | 讓成員判斷讀 `rows` → 必須紅（F-20） |
| **`test_declared_score_without_valid_evidence_has_lower_effective`** | 宣告 `corroborated` 但引用不成立時，`effective_*` 必須低於 `declared`，且排序用 `effective` | 用 `declared` 排序 → 必須紅（F-25） |
| **`test_company_id_and_ticker_are_not_interchangeable`** | `CompanyId("co:axt")` 不得被當成 `Ticker` 使用（型別層或 runtime 檢查） | 互相賦值 → 必須紅（F-01～F-05，INV-1） |
| **`test_audit_registry_reports_not_implemented_not_pass`** | `alpha/audit/` 的 12 個 check 在未實作時回 `SKIPPED(not_implemented)`，**不得回 `PASS`** | 改成回 PASS → 必須紅（L13） |

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
| T8 | point-in-time 三條測試（含 `PointInTimeUnsupported`） | 測試 | 對應 F-31 |
| T9 | `test_layer_separation.py` 三條 import 邊界測試 | 測試 | 最後做：前面的檔案都存在了才掃得到 |
| T10 | 兩個 config 字彙檔 ＋ `.gitignore` 白名單 ＋ `test_config_tracking` 通過 | config | |
| T11 | `alpha/identity.py`：`CompanyId`／`InstrumentId`／`Ticker`／`Alias` 型別（INV-1）＋不可互換測試 | 型別 | 可與 T1 併做——`EvidenceRef` 會用到 |
| T12 | `alpha/audit/` 骨架：12 個 check 的註冊表，全部回 `SKIPPED(not_implemented)` | 骨架 | **只建骨架**；各 check 由對應 Phase 補。骨架先建的理由是讓「還沒實作」在每次執行時現形 |
| T13 | **`tests/fixtures/golden/` 14 類 fixture，凍結 refactor 前的 expected semantic behavior** | fixture | ⚠ **必須在任何搬遷之前**——B1 之後就補不回「舊行為長什麼樣」了 |

---

## 4. Exit criteria（2026-09-03 實測結果）

> ✅ **全數達成。** 實測值記在每一條後面；重跑方式見括號內命令。

| 條件 | 結果 |
|---|---|
| `alpha/` 零外部相依 | ✅ `[]`（`python -c "import alpha, sys; print([m for m in ('neo4j','yfinance','anthropic','decision_lab','engine_c','mcp_server') if m in sys.modules])"`） |
| 新增測試斷言 | ✅ **6 個測試檔、73 條**（原訂 5 檔 ≥17 條；多出的是真實 fixture 那一組） |
| 每條斷言做過「故意違規→確認會紅」 | ✅ **17/17 突變全部讓測試變紅、空跑 0**（`python scripts/verify_test_nonvacuity.py`） |
| 真實資料 fixture | ✅ 3 份（`tests/fixtures/alpha/`），由 `scripts/capture_alpha_fixtures.py` 從真實 authority 擷取並 scrub |
| 全套測試 | ✅ **1,175 → 1,248 passed／0 skipped** |
| 既有 package 變更 | ✅ **0 行**（`decision_lab`／`engine_b`／`engine_c`／`query`／`loader`／`thesis`／`identity`／`storage`／`mcp_server` 皆未動） |
| F-20／F-25／F-31 三個 🔴 歸零 | ✅ `RankedList`／`Score.declared-effective`／`PointInTimeUnsupported` 各有會紅的突變守著 |

### 4.0 動工過程中撞出的三件事（比計畫本身更有價值）

**① 真實資料撞出兩個契約缺口**（T2／T5，`scripts/capture_alpha_fixtures.py --report`）：
- **既有五軸與新的五個 score 不是同一組東西。** 舊五軸問「證據多強」，新五 score 問
  prompt §6 的五個投資問題。映射是**輸入**不是改名：`technical_causal_link`→Q1、
  `commercial_maturity`→Q2、`financial_resilience`→Q3（**只是部分**，真正要的
  segment revenue 在 Engine C 沒有欄位）、`valuation_payoff`→Q4；
  而 **`source_reliability` 沒有對應**——它是 meta 軸，限定所有 `EvidenceRef` 的品質。
- **Q5 catalyst 在舊系統沒有任何軸**，住在 `coverage_assessments.catalyst` 的自由文字裡。
  所以 COHR 的真實 `AlphaSignal` 是 `incomplete`、`catalyst_score is None`——
  順帶讓「`None` ≠ 0」在**真實資料**上被驗到，不只在手寫案例上。

**② 真實 `evidence_refs` 有 3/10 是散文型引用**（帶 `accession` 但無結構化 id），
契約 10/10 都裝得下。這是 F-22 的世界，也是 Phase 2 resolver 的難度預覽。

**③ 兩個守衛第一次跑就攔錯東西（L15 的現場實例，各記在程式碼註解裡）：**
- `FORBIDDEN_POSITION_TOKENS` 含 `exposure` → 直接攔下 `earnings_exposure_score`
  （那是 Q3 的研究維度不是部位）。修法是**改它問問題的方式**：名單只留無歧義 token。
- Cypher 偵測用 `IGNORECASE` → 把 `_ENTITY_RE.match(` 判成 `MATCH (`。
  改成大小寫敏感 ＋ 前面不得是 `.`。

**④ 突變工具自己有偽陰性。** 每跑一次就有一條不同的斷言被報成「空跑」，
手動重現卻會紅。成因是 Python 的 pyc 失效判準是 `(source_mtime_秒, source_size)`——
`os.replace` 保留來源檔 mtime，相鄰兩個突變若讓檔案大小相同又落在同一秒，
直譯器就沿用上一輪的 bytecode。修法是每次用全新的 `PYTHONPYCACHEPREFIX`。
**這個 bug 的形狀正是它自己要防的東西：一個看起來在檢查、實際沒在檢查的檢查。**

### 4.1 原始 checklist（保留供對照）

- [ ] `alpha/` 存在（`contracts`／`causal`／`provider`／`errors`／`identity`／`testing`／`audit`），**零外部相依**：
      `python -c "import alpha; import sys; print([m for m in sys.modules if m in ('neo4j','yfinance','anthropic','decision_lab')])"` → `[]`
- [ ] 新增 5 個測試檔、**≥ 17 條斷言**（§2.4），全綠
- [ ] **每條斷言都做過「故意違規 → 確認會紅」的空跑檢查**，結果記在 commit message
- [ ] `tests/fixtures/alpha/` 有 2 份**由真實資料手工組成**的 fixture（T2、T5），
      且組裝過程中發現的契約缺口已回寫進 `target-architecture.md`
- [ ] 全套測試綠。**baseline 2026-09-03：`1175 passed, 0 skipped`（3 分 17 秒）**；
      Phase 1 後應為 `1175 + 新增條數 passed, 0 skipped`。查證：`python -m pytest -q`
- [ ] daily 端到端跑一次成功且輸出**內容不變**（pq2 項目數、首屏計數器與 Phase 1 前一致）
- [ ] `git diff --stat` 顯示 **`decision_lab/`／`engine_b/`／`engine_c/`／`query/`／`loader/` 的變更為 0 行**
      （Phase 1 是純新增；有任何一行動到既有 package 就代表 scope 漏了）

### 4.2 Completion gate（八項，出自 `historical-failure-matrix.md` §9）

- [ ] 1. Historical regression suite pass — **Phase 1 只需建立 `tests/fixtures/golden/`
      的 14 類 fixture 並凍結現況輸出**（refactor 前的 baseline；此時沒有新舊可比）
- [ ] 2. Runtime invariant audit pass — Phase 1 只需 **`alpha/audit/` 骨架＋12 個 check
      的註冊表**，check 本身可以全部回 `SKIPPED(not_implemented)`，**但不得回 `PASS`**
      （L13：成功與未實作不得在同一個訊號上同形）
- [ ] 3. No unexplained semantic diff — N/A（純新增，無舊路徑可比）
- [ ] 4. No new dual authority — `alpha/` 不落地任何快取表，不開新 DB
- [ ] 5. No silent-drop path — `RankedList` 型別已強制帶 `full_ids`
- [ ] 6. Point-in-time tests pass — §2.4 的三條 as-of 測試
- [ ] 7. All migrated lifecycle objects reachable — N/A（未搬任何 object）
- [ ] 8. **本 Phase 負責的 🔴 已歸零：F-20（`RankedList`）、F-25（declared vs effective）、
      F-31（`PointInTimeUnsupported`）**

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
**但依使用者 2026-09-03 給的優先序（Alpha Research 是 #2、Portfolio 是 #7），
B1 排在 Phase 2 之後，成為 Phase 3.5。** 先做完第一條 vertical slice 再搬 Portfolio——
流程上「先搬最乾淨的一刀當練習」是合理的，但它會延後使用者真正要的東西（先能研究一家公司）。

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
| **2 — First research vertical slice** | **COHR**（2026-09-03 定案）從 graph context → financial → expectations → `AlphaSignal`，能跑 `python -m alpha research COHR` | ①輸出的每個 score 都能 explain 到 `EvidenceRef`；②圖零新增節點；③與現行 `rank_bottlenecks` 首選一致或能說明為何不一致 |
| **3 — Engine D decomposition** | B2／B3／B5／B6 ＋ `mcp_server` domain 抽出 | `decision_lab/` 13,502 → ≤8,000 行；直接相依環 3 → 0；**core → `mcp_server` import 5 → 0**；daily 輸出內容不變且 bytes 下降 |
| **3.5 — Portfolio / Risk 搬家** | B1 | `decision_lab/` −2,054 行；`engine_c → decision_lab` 環消失；三個硬擋逐筆一致（characterization） |
| **4 — Expectation Gap** | implied fundamentals vs market implied | `expectation_gap_score` 對 ≥5 檔可算出且能 explain；低 P/E 案例的 gap ≈ 0 |
| **5 — Causal propagation** | `StructuralEvent` → `CompanyImpact` | 對 ≥1 個真實事件產出 ≥1 個二階受益／受害者，且路徑可追溯 |
| **6 — Backtest / validation** | as-of 圖投影 ＋ anti-lookahead 回測 | SourceDoc `published_at` 覆蓋 → 100%；as-of provider 通過 anti-lookahead 測試；排序前段 vs 後段的等權報酬差有 ≥2 期 |
| **7 — Portfolio / Risk 完整化** | view → target exposure → limits（B1 已於 3.5 搬完） | 不新增任何 alpha 尺寸；target exposure 可由 `AlphaSignal[]` 導出 |
| **8 — Automation / productization** | daily／weekly／skills／MCP 適配新架構 | 16 條 sandbox rule 完成 impact review；skills 同步 `--check` 無漂移 |
