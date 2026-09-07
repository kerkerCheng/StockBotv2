# Phase 2 Step 4 — Full-chain Adversarial Acceptance（2026-09-07）

> **這是 point-in-time 報告，不是 current-state truth。** 裡面的數字是 2026-09-07 的實測值；
> 判準與結論才是要留下來的東西。查證命令都寫在各段落裡，**引用前先跑一次**。
>
> Baseline commit：`ba2e7c6`。標的＝COHR（唯一有完整 Step 0–3.5 鏈的公司）。
> 本輪**沒有**新增金融模型、**沒有** onboarding 新公司、**沒有**動 thesis／variant view。

## 判定：**GO**（原判 CONDITIONAL GO，條件已於同日解除）

> **2026-09-07 收尾補記。** 原本的唯一條件是「跑一次 private authority 備份」——
> `fair value 223.60` 的唯一來源（三本 private ledger）當時不在任何一份備份裡。
> 使用者當日指示執行，已完成：備份 `20260907T070519Z`（524 檔，含
> `alpha/assumptions|valuation|horizon/COHR.jsonl` 與 `alpha/cohr_judgment.json`），
> `unbacked_files` **17 → 0**。同時 [483] 已 `go` 並執行 re-anchor（見 §8）。
> ⚠ **仍未解除的是異地副本**：`drive: skipped`，本機單一磁碟。首屏計數器照樣紅字。
> 查證：`python scripts/backup_private.py status`

可以進 2–3 檔 heterogeneous Coverage Pilot（見 §10）。

---

## 1. 驗收數字

| 項目 | before（`ba2e7c6`） | after | 說明 |
|---|---:|---:|---|
| `pytest -q` | 1,809 passed／1 skipped | **1,860 passed／1 skipped** | ＋51，其中 35 條是新的 `tests/test_full_chain_acceptance.py` |
| 突變非空跑 | 148 個／空跑 0 | **156 個／空跑 0** | ＋8；並修掉一條**因為 Step 4 自己而變成空跑**的舊突變（見 §5） |
| `python -m audit invariants` | FAIL 0｜PASS 11｜**SKIPPED 1** | **FAIL 0｜PASS 12｜SKIPPED 0** | `GateDiscrimination` 落地（§7） |
| golden fixture 漂移 | 0 | **0** | `python scripts/capture_golden_fixtures.py --verify` 14/14 |
| Baseline 核心數字 | — | **一格未動** | §8 |

---

## 2. Full-chain acceptance matrix

**不建第二份 dependency graph。** 每一列都是拿既有的 `assumption_ids`／`evidence_refs`／
`alpha.refresh` policy 表跑出來的實測，不是另外宣告一次誰依賴誰。
可執行版本住 `tests/test_full_chain_acceptance.py::MATRIX`；下表是 2026-09-07 的 `actual`。

查證：`python -m briefing refresh COHR [--scenario <name>] --format json`

Baseline：`overall=current`｜29 個成果｜current 25、superseded 2、missing 2。

### 2.1 Refresh／dependency（實跑七個情境）

| # | changed_input | expected_affected | expected_unaffected | actual | 判定 |
|---|---|---|---|---|---|
| A | **price-only**（現價前進） | `fair_value_gap`／`implied_return`／`market_implied_eps_growth` recalculate | fair value、Q1–Q5、thesis、三本 ledger 的假設**全部** | 完全一致，判斷型成果動 **0 格** | ✅ |
| B | **consensus revision**（FY27 EPS 9.42→10.00） | 數值 gap recalculate；Q4／thesis review；估值＋horizon 假設 review（calibration ref 命中） | Q1／Q2、`fundamental_model`、`modeled_metric:*`、營運假設 | 一致（10 格動） | ✅ |
| C | **graph edge changed**（substitutability／sole_source） | Q1 recalculate；**引用該邊的**成果 review | 未引用該邊的假設（tax／shares／NCI／interest／Industrial）、horizon 判斷 | 18 格動，全部指得回引用；horizon current | ✅ |
| D | **new guidance** | driver 相關的營運假設 review、Q2／Q4 review | Q1、horizon 判斷、shares／NCI（無 driver 對應） | 一致 | ✅ |
| E | **new actual** | 橋 recalculate、heuristic proxy 假設 review | Q1、Q4、session_judgment 型假設（D&C +60% 不因新實際值自動重看） | 一致 | ✅ |
| F | **fiscal rollover** | 全部 FY2027 假設 superseded、`fundamental_model` review_required、下游整條缺席 | — | 29 → **19 個成果**；headline `missing`、readiness **blocked** | ✅ |
| G | **disproof signal** | 被指名的 artifact ＋其下游 review | Q1（未被指名） | 一致（13 格動） | ✅ |
| H | **supporting evidence withdrawn** | 依賴該證據的成果 `invalidated` | 其餘 | 引擎層實測，見 `tests/test_refresh_engine.py::test_retracted_supporting_evidence_invalidates_dependents` | ✅ |
| I | **operating／valuation assumption supersede** | 舊紀錄 superseded、下游 recalculate | 其他假設 | 引擎層 ＋ 真實 ledger（`va_30800fc2323efd6b` 已被 supersede，實測不在生效清單） | ✅ |
| J | **horizon supersede／expiry** | implied return recalculate／到期即 stale | fair value、基本面 | `tests/test_refresh_engine.py::test_horizon_supersede_recalculates_the_return_and_expiry_makes_it_stale` | ✅ |

> **這張表的價值在 `expected_unaffected` 那一欄。** 少了它，一個「把所有東西都標
> review_required」的實作會全綠——那正是 Step 0 抓到的 over-invalidation。

### 2.2 PIT／temporal

| # | 對抗手法 | expected_readiness | actual | 判定 |
|---|---|---|---|---|
| K | as-of 早於三本 ledger 建立日（2026-08-01） | blocked，fair value／implied return **null 且帶原因** | 一致；現價仍在（它那天真的存在） | ✅ |
| L | as-of 2026-08-15 的證據索引 | 沒有任何 `published_at > as_of` | 0 條漏出 | ✅ |
| M | price `bar_date` ≠ ETL date | `horizon_start = 2026-09-04`（bar），不是 09-07 | 一致，持有 299 天 | ✅ |
| N | fiscal-period rollover | 見 §2.1 F | 舊期間數字**一格都沒有**冒充新期間 | ✅ |
| O | superseded record 復活 | 只能是歷史 | 被篩掉的 1 筆有計數＋`reasons={'superseded':1}` | ✅ |

### 2.3 Missing／identity

| # | 對抗手法 | actual | 判定 |
|---|---|---|---|
| P | base actual missing | 整條缺席並說原因；**共識仍看得到**（缺的是我們的預測不是市場的） | ✅ |
| Q | consensus missing | 數值 gap 消失，**且內部預測也整條缺席** ← 見 §9 觀察 1 | ✅（fail closed） |
| R | valuation ledger missing | fair value missing → implied return missing | ✅ |
| S | horizon ledger missing | **fair value 仍在 223.60**、implied return missing | ✅（層級正確） |
| T | GAAP vs non-GAAP mismatch | 橋拒收異口徑假設；共識口徑 unverified 不得相減 | ✅（`test_fundamental_model.py` 既有） |
| U | fiscal-period mismatch | FY27 內部不與 FY26／FY28 共識相比 | ✅（既有） |
| V | quote-unit mismatch（`GBp` vs `USD`） | gap 與 implied return 皆 **null**，不硬除 | ✅ |
| W | private authority file missing／malformed／truncated | 見 §6 | ✅ |

---

## 3. 真 bug vs false alarm

### 真 bug（3 個，全部已修）

**B1 — forward-year rollover 污染（correctness，最嚴重）**
`engine_c/estimates.py::revision_over` 比較窗口兩端的 forward EPS，卻**沒有任何機制確認兩端
是同一個會計年度**。yfinance 的 `forwardPE` 指「下一個會計年度」——那是相對於抓取日的標籤，
公司一報完年報它就換一年。實測 COHR：

| 日期 | price | pe_forward | 導出 forward EPS | 相對前一觀測 |
|---|---:|---:|---:|---:|
| 2026-08-12 | ~327 | ~39 | 8.21 | — |
| 2026-08-13 | 327.23 | 24.08 | **13.59** | **+62.3%** |

FY2026 財報（8-K，2026-08-12）一出，forward year 由 FY2027 換成 FY2028。
30 個觀測的窗口（2026-08-04 → 09-04）跨過它，於是 `estimate_revision_30d` 報 **+68.3%**，
`market_implied_eps_growth` 報 **+238.7%**——**兩個都是換尺，不是分析師上修**。

**修法（fail closed，不猜）：** `revision_over` 現在要求窗口兩端的 `forward_period_end` 相同。
身分由**當日 `consensus_estimates` 的估計值反查**（值相等，相對容差 `1e-3`），
查不到就是身分不明 → `comparable=False`。實測結果：`consensus_estimates` 只有 2026-09-04
一天有列，所以窗口起點身分不明 → **`+68.3%` → `not_comparable`**，`eps_change=None`（不是 0），
`price_change` 仍然給（股價沒有會計年度身分問題）。
`market_implied_eps_growth` 的值不變，但 method 現在寫出 `forward 會計年度=2028-06-30`。

⚠ **刻意不用幅度門檻猜**（「跳超過 30% 就算 rollover」）——那本身就是一個未經量測的 gate（L14）。

⚠ 連帶撤回兩處被污染的書面結論：`engine_c/estimates.py` 與
`tests/test_estimate_revision.py` 的模組 docstring 原本寫著
「COHR forward EPS +69.9%／+68.3% 而股價下跌＝expectation gap 的原型」——那是同一個假象。
**AXTI 的 +186.1% 同樣未經身分驗證，一併不得引用。**

**B2 — 頭條「無」是一句全域措辭配一個局部範圍（presentation）**
`analyst-view` 頭條的 attention 只看 `HEADLINE_ARTIFACTS`（implied_return／fair_value／
fair_value_gap／horizon_assumption／valuation_assumption），卻印出「需要重看的研究成果：**無**」。
實測 `--scenario fiscal_rollover`：畫面上方 `overall=review_required`（3 stale），
第 36 行寫「無」——**兩句互相否定的話在同一個畫面上**（L12：一個表示兩種語意）。

**修法：** `AnalystPanel` 新增 `attention_scope`／`attention_total`；renderer 有 scope 就必須印出
範圍，並在有全域計數時寫出「本節之外另有 N 項」。修後那一行變成：
「無（範圍：只列頭條這幾格自己的成果（…））；本節之外另有 **4** 項需要動作——見 5.6」。

**B3 — 備份計數器只報年齡、不報覆蓋（durability）**
見 §6。

### False alarm（2 個）

**F1 — `fiscal_rollover` 下 10 個成果從報表上消失（`current → —`）**
看起來像 silent drop。實測不是：FY2027 的假設全部 `superseded`，FY2028 **沒有任何假設**，
所以 `modeled_metric:*`／`fair_value`／`implied_return` 這些成果**根本不存在**，不是被過濾掉。
消失的原因由留在報表上的 `fundamental_model: review_required` 逐字說出
（「基期已推進到 FY2027；8 條 FY2027 假設是歷史，不沿用；FY2028 需明示新假設」），
消費端則直接是 `readiness=blocked` ＋ headline `missing`。**這是 fail closed 的正確形狀。**

**F2 — `graph_edge` 情境動到 18 個成果，疑似 over-invalidation**
逐格追過：每一格都指得回**那條邊的 ref**（兩條營運假設與估值假設都把它列為 supporting，
再由 `propagated_from` 往下傳）。沒有引用它的假設（tax／shares／NCI／interest／Industrial）
與 horizon 判斷維持 `current`。引擎層另有
`test_refresh_engine.py::test_single_edge_change_does_not_cascade_to_everything` 守著。

---

## 4. 正確 fail closed 的 scenario（彙總）

`K`／`N`／`P`／`Q`／`R`／`S`／`V`／`W` 八組全部 fail closed，且**每一格缺席都帶原因**。
最值得記的是 **S**：horizon ledger 消失時 `fair value 223.60 仍在`、只有 implied return 缺席——
缺料停在它自己那一層，沒有往上污染，也沒有往下漏出一個乾淨的報酬。

**沒有任何一個 scenario 產出「看起來合理但語意錯誤」的結果。**
唯一曾經產出這種東西的是 B1（`+68.3%` 看起來完全正常），而它現在 fail closed。

---

## 5. Rollover proxy contamination 結論

1. **確認是真的，而且已經污染過一次判斷。** COHR 的 Q4 重判（2026-09-07）在 rationale 裡逐字
   寫著「兩個看起來會支持升等的代理**已查證為會計年度換檔假象，不得引用**」——那是**人工**擋下的。
   本輪把它從散文變成機器強制的 contract。
2. **現有 contract 確實分不出來**：`financial_snapshots` 沒有任何欄位記錄 forward 指哪一年；
   `consensus_estimates`（唯一有 `fiscal_period_end` 的表）**只有 2026-09-04 一天、2 檔標的**。
   所以答案是 `not_comparable`，不是猜。
3. **解除條件**：`consensus_estimates` 累積到窗口兩端都有列（daily ETL 每天補一列，
   30 個觀測窗口約需 **6 週**）之後，`estimate_revision_30d` 會自己恢復——不需要改程式。
   查證：`python -c "import sqlite3;c=sqlite3.connect('library/private/engine_c/stockbot-engine-c-private-v1-458db5270ee2.db');print(c.execute(\"select count(distinct coalesce(bar_date,snapshot_date)) from consensus_estimates where ticker='COHR'\").fetchone())"`
4. ⚠ **這件事讓一條舊突變變成空跑**：`tests/test_audit.py` 原本靠「掃註冊表找 `run is None`」
   來守「未實作不得回 PASS」，`GateDiscrimination` 落地後那個迴圈體再也不會執行。
   已改成自己造一個 `run=None` 的 check——**守的是規則本身，不是註冊表現在有幾個空缺**。
   這正是本檔記過的形狀：清單會腐壞，判準不會。

---

## 6. Evidence coverage 與 Private authority durability

### 6.1 Evidence coverage boundary（`ResearchContext.evidence_refs`）

**問：這是 deliberate boundary 還是 coverage hole？**
**答：deliberate boundary，但它以前沒有被說出來——而「沒說出來的邊界」在實務上等於 coverage hole。**

`ResearchContext` 必須先建好，財務模型才拿它當 `evidence_index` 的**底**去擴充
（`alpha/fundamental/model.py` §2 的 `index.setdefault`）。方向是單向的：
context → model。把模型層的 ref 灌回 context 會是一個循環。所以軸判斷（Q1–Q5）的索引裡
只有 19 條（18 條 graph ＋ `engine_c://financial_snapshot/COHR`），
**沒有** `engine_c://consensus_estimate/*` 與 `engine_c://manual_observation/*`。

**問：Q4 若依賴 numeric comparison，正確 provenance 應該怎麼被引用？**
**答：引用成果 `alpha://fundamental/compare`，不是引用共識本身。**
Q4 是 ordinal 判斷，numeric gap 是確定性成果——**兩個 authority**（見 §7 語意陷阱 2）。
共識的 provenance 由 compare 這個成果自己帶；Q4 引用共識等於把一個 numeric gap
直接當成 ordinal 分數的證據，正是必須避免的合併。

**問：能不能沿用 `AlphaInvestmentView` 已有的 evidence index，而不產生第二份 evidence authority？**
**答：已經是了。** `analyst-view` §4.6 的證據索引列得出
`engine_c://consensus_estimate/COHR/eps/2027-06-30`、`engine_c://manual_observation/mo_*`——
它們是**同一批 `EvidenceRef` 物件**，只是索引在模型層做了 superset 擴充（`setdefault` 永不覆寫）。
**沒有第二份 evidence authority，也不需要建一份。**

**最小 contract-level 修正（不放寬 resolver）：**
- `alpha/models/session_assessor.py` 新增 `EVIDENCE_SCOPE`，並寫進 research packet 的
  `evidence_scope` 欄位：涵蓋哪些前綴、**不涵蓋什麼、不涵蓋的住哪裡**。
- `compose_signal` 的拒絕訊息分成兩種語意：**「這個 ref 不存在」**（可能是 laundering）與
  **「這個 ref 存在但不屬於這一層」**（層級錯誤，附「它住哪」）。
  混成一句話會讓真正的 laundering 藏在合法的層級錯誤裡（L12）。
- fail-closed 測試 2 條＋突變 1 個。**邊界本身一格都沒有放寬。**

### 6.2 Private authority durability

**現有 contract 存在，而且涵蓋這些檔案：**
`scripts/backup_private.py` 的 `files.zip` 用 `rglob` 收整個 `library/private/`，
`alpha/` 不在 `EXCLUDE_TOP_DIRS` 裡；daily brief 首屏另有常駐的「最後一次備份 N 天前」計數器
（`briefing/render.py::_render_backup_status`）。

**但 2026-09-07 的實際覆蓋是這樣：**

| 檔案 | 內容 | 在最後一份備份（`20260904T150924Z`）裡？ |
|---|---|---|
| `alpha/cohr_judgment.json` | Q4 重判（09-07 12:34） | **有，但是舊版本** |
| `alpha/assumptions/COHR.jsonl` | 8 條營運假設 → 內部 EPS 8.94 | **沒有**（目錄 09-05 才建立） |
| `alpha/valuation/COHR.jsonl` | target PE 25x → fair value 223.60 | **沒有** |
| `alpha/horizon/COHR.jsonl` | horizon 2027-06-30 | **沒有** |

也就是說：**`fair value 223.60` 與 `−20.7%` 的全部輸入判斷，當時沒有任何一份備份收過**，
而 `drive: skipped`（沒有異地副本）。**這是本輪唯一的 CONDITIONAL 條件。**

> **2026-09-07 已解除（本機那一半）。** 使用者當日指示執行
> `python scripts/backup_private.py run --no-drive` → 備份 `20260907T070519Z`
> （decision_lab.db ＋ engine_c.db ＋ neo4j_export 1,536 nodes／1,861 rels ＋ files.zip 524 檔），
> 其中 `alpha/` 由 4 檔變 **7 檔**——三本 ledger 全部收錄；`unbacked_files` **17 → 0**。
> ⚠ 輪替 `LOCAL_RETENTION=3`，最舊的 `20260830T031723Z` 已被輪出，而
> `last_backup.json.restore_verification.backup_id` 仍指向它——**「restore 已驗證」現在指向
> 一個已不存在的備份**。這不影響本次備份的完整性（manifest checksum 自成一體），
> 但那個欄位已經是 stale。要清掉就跑 `python scripts/backup_private.py verify-restore`。
> **異地副本仍未解決**（`drive: skipped`，需要一次瀏覽器 OAuth：`backup_private.py auth`）。

**對抗測試（全部通過）：** file missing／malformed JSON／partial write（截斷行）／stale 舊判斷
四種都**不會**靜默回退成一個看起來 current 的舊判斷——
- 三本 ledger 任一不見 → 該層 missing、下游整條缺席（`test_a_missing_private_ledger_fails_closed_at_its_own_layer`）；
- 截斷的一行 → **被計數**（`input_count > accepted_count`），好的行照常算（`test_a_malformed_ledger_line_is_counted_not_silently_dropped`）；
- 判斷檔壞掉 → 研究段缺席並說原因，而**確定性那一段不受影響**；
- 舊判斷 → 呈現但標「判斷與目前 context：不一致」。

**修法（B3，最小）：** 計數器多回一個數字——
`unbacked_files`＝private root 底下有幾個檔在最後一份備份之後才變動過（排除備份自己的產物）。
實測現在是 **17 個**（含 `alpha/cohr_judgment.json` 與 `decision_lab.db`），
首屏會紅字寫出來。**「N 天前備份」與「這幾個檔有沒有被收進去」是兩個問題**（L13-2：
成功與失敗在同一個訊號上同形）。

**⚠ `%TEMP%` 不是 durability 機制**，本輪沒有把它當成任何一環。

---

## 7. GateDiscrimination 結論

**已完成，不是為了全綠而 invent 一個 gate。**

**為什麼原本 skipped：** 註冊表寫著 `owner_phase="Phase 4"`、`run=None`。
F-26 記的是 `axis_ceiling`／`live_supported_range` 那一層，而**那一層已於 2026-08-28 整組移除**，
所以「要量哪些 gate」在當時失去了對象。

**現在有真實可區分案例：** Decision Store 的 `coverage_assessments` 有 **269 份帶時戳的評估、
41 個 cohort**，三條 lane（coverage／paper／live）共 **63 個具名 blocker**——它們今天仍在決定
研究流程的去留，而且有完整歷史。

**兩個率的分母刻意不同：**
- **觸發率** ＝ 出現在幾份 assessment ÷ 全部 assessment。近 100% ＝零鑑別力（恆亮）。
- **清除率** ＝ 曾經響過、**且之後還有過評估**的 cohort 裡有幾個後來不再響。
  ⚠ 分母必須是「有機會被清除的」。用「曾經響過」當分母的第一版把
  `identity_unresolved` 算成 **0/9 = 0% 清除（不會滅）**——實測那 9 個 cohort 有 6 個
  **只被評估過一次**，根本沒有清除的機會。那是把沒發生讀成失敗（L13-2）。
  改用正確分母後是 0/3，樣本不足。

**實跑結果：** `PASS`｜63 個 gate 量過觸發率、其中 **24 個**樣本夠也量得出清除率。
沒有恆亮（最高 `execution_intent_research_only` 65.8%），沒有不會滅
（最低 `holdings_unconfirmed` 33.3%）。39 個樣本不足的列成 `insufficient_data`，
**不當作通過也不當作失敗**。

**本 check 自己也受 INV-5 約束：** 一個 gate 都判不動時（`judged == 0`）回 **SKIPPED 不是 PASS**——
一個判不動任何 gate 的鑑別力檢查，鑑別力自己是零。5 條測試 ＋ 2 個突變守著它。

查證：`python -m audit invariants --only GateDiscrimination`

---

## 8. Baseline drift

**核心數字一格未動**（`tests/test_full_chain_acceptance.py::test_baseline_numbers_are_pinned_and_each_traces_to_an_authority` 釘住）：

| 項目 | 期望 | 實測 |
|---|---:|---:|
| Internal FY27 EPS | 8.94 | **8.9441** ✅ |
| Consensus FY27 EPS | 9.42 | **9.4163** ✅ |
| Q4 | weak 0.25／current | **0.25／`axis:expectation_gap = current`** ✅ |
| Fair value | 223.60 | **223.6034** ✅ |
| Price（bar 2026-09-04） | 281.86 | **281.86** ✅ |
| Value date／Horizon | 2027-06-30 | **2027-06-30／aligned** ✅ |
| Simple implied return | −20.7% | **−20.67%** ✅ |
| Annualized | −24.6% | **−24.64%** ✅ |
| Entry | optional missing | **missing，`blockers=[]`** ✅ |
| Core readiness | ready | **ready** ✅ |

**兩處確實漂了，provenance 如下（沒有改 golden 讓測試過）：**

1. **`judged_context_matches`：True → False → True（已於同日 re-anchor 修復）。**
   起因是 B1：`ValuationSnapshot.method`（Q4 的原料描述）由
   「estimate_revision=forward EPS +68.3% vs 股價 −2.2%」變成
   「estimate_revision=not_comparable（…）」，而 `method` 進 `ResearchContext.digest`。
   **這是正確的**：Q4 判斷所看到的原料確實變了。判斷本身的結論不受影響——它早就自己
   把那兩個代理列為「不得引用」——但 digest 錨點需要重新對齊。
   **這是 A3 的 private authority，走人工 gate**：鑄成 **pq2 [483]**，使用者 2026-09-07 `go`。
   已執行：`_packet_digest` `sha256:178a17f9…` → `sha256:bc32a785…`，`_restated` 新增第 3 條
   逐字記錄。**逐鍵驗證只動了這兩格**——五軸、thesis、variant_view、bull／base／bear、
   risks、catalysts、disproof_conditions 與三本 assumption ledger **一格未動**；
   Q4 仍是 weak／0.25、`axis:expectation_gap = current`。
   ⚠ **動手前先跑了備份**——那個檔案當時是唯一副本。

2. **refresh 成果數：30 → 29（`current` 26 → 25）。**
   消失的是 `market_implied:estimate_revision_vs_price`——`estimate_revision_30d` 現在是 `None`，
   那個成果**不存在**，所以不在報表裡。它在 consensus section 以
   `not_applicable` ＋逐字理由現形（並在 §2「其他期間的共識與市場觀測」下方多一條 `註：`）。

---

## 9. Consumer 黑箱驗收（`python -m briefing analyst-view COHR`）

全部通過（`tests/test_full_chain_acceptance.py` §5）：

- **每個 core number 與 canonical `AlphaInvestmentView` 同值**（price_return／annualized／
  fair_value／current_price／refresh.overall／schema_version）；
- **不重算、不造 Datum**：`AnalystLine` 沒有 `value` 欄位，每一行都是 read model 裡**同一個物件**
  （既有 `id()` 集合測試）；
- **no runtime LLM／no authority write**：`briefing/analyst_view/*.py` 的 import 掃描禁
  `sqlite3`／`neo4j`／`anthropic`／`openai`／`requests`／`httpx`／`decision_lab.store`／`engine_c.db`；
- **Missing != Zero**：序列化那一端掃過整份 JSON，valueless status 帶值的格子 **0 個**；
- **contradictory states 現形**：`--scenario consensus_revision` → `overall=review_required`、
  `readiness=ready_with_flags`、flags 非空、markdown 裡出現 `review_required`；
- **呈現陷阱已修**：見 §3 B2。

⚠ 禁字掃描用**欄位名**比對不用全文——畫面上刻意寫著「不是 portfolio permission」這種否定句，
全文比對會誤報，而**一個會誤報的防呆本身就是 L16 明文禁止的東西**。

---

## 10. 是否安全進 Coverage Pilot

**是，2–3 檔 heterogeneous 標的可以開始。** 依據：

- 七個 refresh 情境的「不該動的沒動」全部成立 → 加一檔不會讓別檔的 state 亂跳；
- 上游缺料八種全部 fail closed 且**停在自己那一層** → 第二檔資料不齊不會污染第一檔；
- 黑箱一致性與 Missing≠Zero 由序列化端守著 → 多檔並列時不會冒出假 0。

**選檔建議（heterogeneous 才測得到東西）：** 一檔**非美元報價**（驗 §2.3 V 的單位路徑走真資料，
例如 SIVE.ST／IQE.L）＋一檔**沒有人工分部觀測**的（驗 Q3 缺料）。
⚠ 每加一檔就要新增三本 ledger 的判斷——那是 **pq2 研究工作**，不是開發工作。

**先決條件：** §6.2 的備份（否則 pilot 會在「唯一來源沒有備份」的狀態下再多三倍檔案）。

---

## 11. 誠實的剩餘缺口（不在本輪 scope，記在這裡不遺失）

1. **`estimate_revision` 現在對每一檔都是 `not_comparable`**，直到 `consensus_estimates`
   累積夠歷史（約 6 週）。這是正確的降級，但它意味著 Q4 少了一個原料。
2. **calibration ref 解析不到 ＝ 整筆假設被拒**（§2.3 Q）。方向對（fail closed），但顆粒度
   可議：`supporting` 與 `calibration` 目前是同一個判準。**收緊或放寬都要先量**（L14／L15），
   本輪只釘住現況並在測試 docstring 裡說出它，沒有動它。
3. **`AlphaLineage` 仍只驗 digest 存在與格式**（`ResearchContext` 未持久化）。與本輪無關，
   但它是「lineage 完整」這句話目前唯一撐不住的地方。
4. **`market_implied_eps_growth` 的值沒有降級**，只加了會計年度標註。它是 heuristic proxy，
   不決定任何金額；但它跨的是**兩年**（trailing FY2026 → forward FY2028）而不是一年。
