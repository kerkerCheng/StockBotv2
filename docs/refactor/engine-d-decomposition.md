# Engine D 分解 — 逐檔 audit 與搬遷路徑

> **性質：** Phase 0 產出物之一。對 `decision_lab/`（35 檔／13,502 行）與
> `engine_d_runtime/`（3 檔／1,269 行）**逐檔**判定歸屬，並給出搬遷順序。
>
> 查證：`git ls-files decision_lab engine_d_runtime | grep '\.py$' | xargs wc -l | sort -rn`
>
> ⚠ **這份是判定與計畫，不是已完成的搬遷。** Phase 0 不動任何 code。

---

## 0. 為什麼 Engine D 會膨脹（先講成因，否則搬完會再長回來）

**不是因為寫得隨便。三個結構性原因：**

1. **它是唯一有 point-in-time 凍結能力的地方。** 任何需要「當時看到什麼」的功能——
   五軸評估、catalyst 檢查、排序快照——除了塞進 Decision Store，沒有第二個家。
2. **它是唯一同時看得到 A/B/C 三個引擎的地方。** 需要 join 的東西自然往這裡長。
3. **daily brief 的首屏是它渲染的。** 只要使用者說「這個也放進來」，最短路徑就是
   在 `brief.py` 加一段——`brief.py` 因此從決策摘要長成 1,462 行的全系統儀表板。

→ **對應的解方：** ①`ResearchContext` 提供第二個凍結能力；②`GraphResearchProvider`
＋ Engine C provider 提供第二個 join 點；③brief 改成**組裝多個 DTO 的薄殼**，
每個 pane 由它自己的 domain 提供。**只搬 code 不修這三條，兩個月後會原地重演。**

---

## 1. 逐檔判定

歸屬代碼：**D**＝真正的 Engine D｜**A**＝Alpha Research｜**P**＝Portfolio｜**R**＝Risk｜
**C**＝Engine C｜**I**＝shared infrastructure｜**X**＝obsolete / test-only

| 檔案 | 行 | 歸屬 | 判定理由 | 搬遷難度 |
|---|---:|:---:|---|---|
| `store.py` | 3,125 | **D** | Decision Store：cohort／decision／shadow／lifecycle／outcome／live facts。append-only private authority | — 不搬 |
| `brief.py` | 1,462 | **D → 拆** | 決策摘要是 D，但它同時渲染排序、NAV、beta、identity 對齊、備份狀態＝全系統儀表板 | 🔴 高：需先有各 domain 的 DTO |
| `context.py` | 713 | **D** | DecisionContext freeze、reference index、freshness gate。**這是全案最該保留的機制** | — 不搬 |
| `workflow.py` | 773 | **D → 瘦** | `evaluate_signal`／`reassess` 的高階編排。研究部分（assessment 產生）移出後會瘦 | 🟡 中 |
| `cli.py` | 613 | **D → 拆** | 15 個子命令；`references`／`assessment-scaffold`／`variant-perception` 屬 A | 🟡 中：⚠ 動到 daily 的 exact command |
| `action_card.py` | 521 | **D** | 注意力狀態（MONITOR／REVIEW）＋ approval boundary 呈現 | — 不搬 |
| `capital_authority.py` | 419 | **D** | cash floor ＋ 貸款額度 telemetry。純資本 authority | — 不搬 |
| `intake.py` | 334 | **D** | Signal → Probe/Shadow 的 deterministic 捕捉 ＋ Signal Source Registry | — 不搬（見註 1） |
| `outcomes.py` | 289 | **D** | probe lifecycle ＋ claim/market/decision 分離的 outcome | — 不搬 |
| `execution.py` | 250 | **D** | live choice／fill 的 application boundary。**四個 gate 之一** | — 不搬 |
| `models.py` | 213 | **D → 拆** | immutable domain records；`ProbeSizingResult`／`research_status_of` 屬 A | 🟢 低 |
| `coverage.py` | 189 | **D** | Coverage Gate＝lane permission。approval semantics | — 不搬 |
| `blocker_severity.py` | 191 | **I** | blocker 嚴重度 SSOT，被 A/D/呈現層共用 | 🟢 低（升為 shared） |
| `blockers.py` | 190 | **I** | blocker 中文 label ＋ resolution_mode 分類 registry | 🟢 低（升為 shared） |
| `references.py` | 139 | **D ∩ A** | `build_reference_options` 是研究輔助（A）；引用解析與 authority 比對是 gate（D） | 🟡 中：需切兩半 |
| `identity.py` | 69 | **I** | 組合 registry ＋ execution alias | 🟢 低 |
| `bootstrap.py` | 21 | **D** | 開 private store | — 不搬 |
| `backup.py` | 210 | **I** | owner-only SQLite backup/restore；Engine C 也用 | 🟢 低 |
| `export.py` | 97 | **I** | recovery / redacted export | 🟢 低 |
| `redaction.py` | 42 | **I** | 敏感值偵測；`engine_c.cutover` 也 import | 🟢 低（解 `engine_c → decision_lab` 環） |
| `workflow_ports.py` | 136 | **I** | **repo 裡唯一真正的 port**。`GraphResearchProvider` 照它的形狀做 | — 不搬，當範本 |
| `adapters/graph.py` | 156 | **I** | Neo4j 唯讀 port ＋ 寫入語句攔截 | 🟢 低：`alpha/providers/` 共用 |
| `adapters/market.py` | 185 | **C** | 市場／FX payload 的 fail-closed normalization | 🟡 中：語意上屬 Engine C 的正規化邊界 |
| `adapters/holdings.py` | 8 | **P** | Sheet alias 薄 adapter | 🟢 低 |
| — | | | | |
| **`sizing.py`** | **490** | **A** | 五軸 Confidence Envelope＝**證據品質研究判斷**。名字是歷史包袱（U7 後已不產生任何額度） | 🔴 高：`store` 的 `"sizing"` payload key 已凍結 |
| **`catalyst_watch.py`** | **207** | **A** | disproof／catalyst／expiry 的每日檢查＝catalyst analysis | 🟢 低 |
| **`alpha_event_monitor.py`** | **194** | **A** | alpha 部位的單日跌幅事件偵測＝event monitoring | 🟢 低 |
| **`ranking_view.py`** | **195** | **A** | 瓶頸排序 → 股票清單的轉換層（消費 `query.bottleneck`） | 🟢 低 |
| — | | | | |
| **`beta_monitor.py`** | **897** | **P** | 行情心跳、相對水位、sleeve 目標配置差距 | 🟡 中：`engine_c.technical` 反向依賴 |
| **`beta_policy.py`** | **444** | **P** | beta policy ＋ target allocation 載入與驗證 | 🟡 中：`engine_c.technical` import 它 |
| **`portfolio_risk.py`** | **538** | **R** | 槓桿倍數、issuer 曝險、追繳／歸零門檻、風險快照 | 🟢 低 |
| **`nav_exposure.py`** | **167** | **P** | 持股 NAV 佔比呈現（零門檻，刻意不告警） | 🟢 低 |
| — | | | | |
| `engine_d_runtime/adapters.py` | 1,228 | **I → 拆** | concrete authority composition。內含 `fetch_ranking_view`（A）、`fetch_nav_exposure`（P）、`bounded_evidence_query`（A 的 graph provider 雛形） | 🔴 高 |
| `engine_d_runtime/bootstrap.py` | 35 | **I** | composition root | 🟢 低 |

> **註 1（`intake.py`）：** Signal Source Registry 看起來像 Engine B，但它管的是
> 「哪個來源可以自動觸發 Shadow 捕捉」＝**capture permission**，屬 D。
> `engine_b/leads.py` 管的是研究注意力。兩者不重複，不要合併。

### 1.1 統計

`decision_lab/` 35 檔 13,502 行的分佈（`engine_d_runtime/` 1,269 行另計）：

| 歸屬 | 檔數 | 行數 | 佔比 |
|---|---:|---:|---:|
| **D**（Engine D 核心） | 13 | 6,871 | 51% |
| **拆分中的大檔**（`brief.py` 1,462 ＋ `cli.py` 613） | 2 | 2,075 | 15% |
| **P**（Portfolio，該搬） | 4 | 1,516 | 11% |
| **I**（shared infra） | 10 | 1,231 | 9% |
| **A**（Alpha Research，該搬） | 4 | 1,086 | 8% |
| **R**（Risk，該搬） | 1 | 538 | 4% |
| **C**（Engine C 正規化） | 1 | 185 | 1% |
| 合計 | 35 | 13,502 | 100% |

**可立刻搬走且低風險的：2,054 行**＝P（1,516）＋R（538），即 §4 的 **B1**。
**再一批（B3）：596 行**＝`catalyst_watch`＋`alpha_event_monitor`＋`ranking_view`。
**需要先做 contract 才能搬的：`sizing.py`（490）＋`brief.py`（1,462）。**

---

## 2. `brief.py` 的拆解（最難的一塊，單獨說明）

`build_today_brief()` 的簽名已經自陳問題——它收 **11 個注入參數**：

```
store, as_of, current_holdings, change_context_by_cohort, portfolio_context_by_cohort,
current_authority_by_cohort, provider, registry, alpha_series_by_ticker,
ranking, nav_exposure, identity_alignment
```

其中 `ranking`（Alpha）、`nav_exposure`（Portfolio）、`identity_alignment`（Engine A 健康）
之所以「由呼叫端注入」，正是因為 `decision_lab` 不得 import Neo4j／Google Sheet。
**這個 workaround 是對的，但它證明了這些 pane 不屬於 Engine D。**

**目標形狀：**
```python
# decision_lab/brief.py  ← 只剩決策摘要
def build_decision_brief(store, *, as_of, ...) -> DecisionBriefDTO

# 各 domain 各自提供自己的 pane DTO
alpha.brief.build_alpha_pane(...)        -> AlphaPaneDTO      # 排序、缺口、REVIEW 項
portfolio.brief.build_portfolio_pane(...) -> PortfolioPaneDTO  # NAV、配置差距、水位
risk.brief.build_risk_pane(...)          -> RiskPaneDTO       # 門檻跨越

# 組裝層（薄殼，不含判斷邏輯）
scripts/daily_brief_assembler.py  或  skills/daily-brief 的 Step 順序
```

> **✅ 2026-09-04 實際落地（與上面的草圖有三處差異，都是實作時才看得到的）：**
>
> 1. **組裝層是 `briefing/` package，不是 `scripts/` 腳本。** 因為它有第二個
>    呼叫者——`public_view.get_decision_brief_core`（MCP／`engine_b todo sync`）。
>    腳本不能被 import，兩條路徑就會各自組裝，而 sheet-only 覆蓋分類正好在那條
>    鏈上：漏掉就是持股從 pq2 靜默消失。`public_view.py` 因此一併搬進 `briefing/`，
>    **兩條路徑收斂成一條**。
> 2. **pane 的 markdown 跟著 pane 走，不是集中在組裝層。** `render_ranking` 住
>    `alpha/brief.py`、`render_nav_exposure` 住 `portfolio/brief.py`——「`None` ≠
>    空」那些 L12 措辭是 pane 的呈現契約，離開 domain 就會漂移。組裝層只管順序。
> 3. **沒有 `risk.brief`。** 現況 brief 沒有獨立的 risk pane（門檻跨越目前由
>    `risk.snapshot` 在別的 surface 呈現），憑空造一個空 pane 只是為了對稱。
>
> 另外 `sheet_only_items` 在 `build_decision_brief` 是**必填**參數（不給預設值），
> 那是刻意的摩擦：新增第四條呼叫路徑時忘記做覆蓋分類會是 `TypeError`，而不是一份
> 少了持股、看起來完全正常的 brief（L13：成功與未執行不得同形）。

⚠ **拆解時的硬約束：** `crons/daily_brief_prompt.md` ＋ `skills/daily-brief/SKILL.md`
＋ `tests/test_daily_brief_skill.py`／`tests/test_today_first_screen.py` 是契約測試，
斷言首屏必須出現哪些 token。**不得為了通過測試而刪斷言**——
2026-08-29 的教訓是「文件契約測試不是刪斷言而是換 token（刪掉等於失去剎車）」。

---

## 3. `sizing.py` 的切法（第二難）

現況一支檔做三件事：

| 段落 | 性質 | 目標歸屬 |
|---|---|---|
| `AXES`／`LEVELS`／`AXIS_RESEARCH_PROMPT`／`weakest_axis_of` | 研究語彙與判斷 | **A**：`alpha/contracts.py` 的評分維度 |
| `_resolve_reference`／`AXIS_REFERENCE_AUTHORITIES`／`_validate_assessment` | 引用解析 ＋ authority 比對 | **D**：這是 gate（L15：LLM 可提議，不可授權） |
| `calculate_probe_limits`／`ProbeSizingResult` | 已無額度輸出，只回最弱軸與 research_status | **D**（消費 A 的輸出） |

**切法：**
1. `alpha/` 產出 `AlphaSignal`（含五個 score 與 `evidence_refs`）。
2. `decision_lab/adapters/alpha.py` 把它轉成既有五軸 assessment payload。
3. `decision_lab/sizing.py` 的驗證段**完全不動**——它繼續對 frozen `reference_index`
   驗證引用。這樣 authority laundering 的防線一行都沒鬆。

⚠ **`store` 的 decision payload 有一個凍結的 `"sizing"` key，涵蓋 268 筆歷史紀錄。
不得改名、不得 migration。** 模組可以搬，key 不能動（L10：拿不回來的資料只能 append）。

---

## 4. 搬遷順序（strangler，七批 B0–B6）

> **⚠ 本節（與 §1 的逐檔行數）是 Phase 0 當時的判定，不是現況。** 交付紀錄的唯一
> authority 是 [`ROADMAP.md`](../ROADMAP.md) 的 Phase 表。截至 2026-09-04：
> **B0／B2／B4／B5／B6 已完成，B1 已完成，B3 只完成 `ranking_view`**——
> `catalyst_watch.py` 仍在 `decision_lab/`（`store.py` 反向依賴它，要先倒轉），
> `alpha_event_monitor.py` 已於 B6 搬走（`alpha/position_events.py`＋
> `alpha/providers/close_series.py`），因為 alpha pane 一旦搬家就不能再回頭
> import Engine D。
>
> 查證：`git ls-files decision_lab | grep '\.py$' | xargs wc -l | sort -rn`

每一批的驗收條件都是 **①全套測試綠 ②daily 端到端跑一次成功 ③被搬走的模組
在原位置留 re-export shim 或已確認零呼叫端**。

| 批 | 內容 | 行數 | 為什麼是這個順序 | 風險 |
|---|---|---:|---|---|
| **B0**<br>（Phase 1） | 建 `alpha/contracts.py`＋`alpha/provider.py`（Protocol only，無實作）＋分離測試 | 新增 | 不動既有 code，先立契約 | 🟢 |
| **B1**<br>（Phase 3.5） | `risk/` ← `portfolio_risk.py`；`portfolio/` ← `nav_exposure.py`、`beta_monitor.py`、`beta_policy.py`、`adapters/holdings.py` | ~2,054 | **最乾淨的一刀**：對外介面窄、測試齊（`test_portfolio_risk`／`test_nav_exposure`／`test_beta_monitor`／`test_beta_policy`）、與 Decision Store 只有 policy 載入的耦合。當作 strangler 的練習。⚠ **2026-09-03 依使用者優先序改排在 Phase 2 之後**——Portfolio 是優先序 #7，不得延後 vertical slice | 🟡 `engine_c.technical` import `decision_lab.beta_policy` → 改指向 `portfolio.policy`，順手解掉一條環 |
| **B2**<br>（Phase 3） | `I` 類升格：`blockers.py`／`blocker_severity.py`／`redaction.py`／`identity.py`／`backup.py`／`export.py` → `shared/` 或留原位但明確標示為 shared | ~840 | 解 `engine_c → decision_lab` 環 | 🟢 |
| **B3**<br>（Phase 3） | `alpha/` ← `ranking_view.py`、`catalyst_watch.py`、`alpha_event_monitor.py`；`alpha/thesis/` ← `thesis/lifecycle*.py`、`generate_lane_memo.py`、`evidence_manifest.py`；`risk/limits.py` ← `thesis/investment_policy.py` 的 cap 部分 | ~1,400 | 解 `decision_lab ↔ thesis` 環；把 research thesis 與 capital policy 分開 | 🟡 `thesis/preconditions.py` 的 L9 gate 要決定歸屬（建議留 D） |
| **B4**<br>（Phase 2） | `alpha/providers/graph_neo4j.py` 實作 `GraphResearchProvider`，包 `query/`＋`engine_d_runtime.bounded_evidence_query` | 新增 | concrete provider，Phase 2 的核心交付 | 🟡 |
| **B5**<br>（Phase 3） | `sizing.py` 切三段（§3）；`decision_lab/adapters/alpha.py` 消費 `AlphaSignal` | ~490 | 需要 B0/B4 先完成 | 🔴 |
| **B6**<br>（Phase 3） | `brief.py` 拆成 4 個 pane builder ＋ 薄組裝層 | ~1,462 | 最後做。需要 B1/B3 的 DTO 先存在 | 🔴 |

**B1 先做的理由不只是簡單，是它能證明整套搬遷可行**——如果 2,000 行、測試齊全、
邊界最清楚的一塊搬起來都會出事，那後面的都不該做。

---

## 5. 搬遷期間不得違反的硬約束

1. **Decision Store schema 不動。** 41 個 cohort、268 筆 decision、268 個 context bundle
   是 append-only private authority，Git 救不回（L10 適用範圍）。搬 module 可以，
   改 schema／改 payload key 不行。
2. **`.codex/rules/stockbot-automations.rules` 的 16 條 exact command prefix。**
   任何 `python -m <module>` 的字串改變都必須走 **sandbox impact review 五步**
   （列 side effect → 更新 skill/OPERATIONS → 加最窄 rule → 更新 permission contract test
   → 用排程的相同 sandbox 跑端到端 smoke）。
   👉 **實務建議：搬遷期間保留舊 entry point 的 shim，等全部穩定後再一次改 rule。**
3. **四個人工 gate 不放寬：** graph admission、Engine C 觀測寫入、thesis mutation、
   live choice/fill。
4. **`rank_bottlenecks()` 仍是唯一排序權威。** `alpha/scarcity.py` 消費它，不重算。
5. **既有 126 個測試檔全部保留。** 允許改 import 路徑，不允許刪斷言。
6. **每一批都要能回答「哪個數字變了」**（L14）。搬遷批次的答案通常是
   「0 個數字變，這是純重構」——那就必須有 characterization 測試證明它，
   而不是在 commit message 裡宣稱（2026-08-28 U2 的教訓）。

---

## 6. 搬完之後 Engine D 應該長什麼樣

```
decision_lab/                    ≈ 7,900 行（現 13,502，−41%）
  store.py            3,125      Decision Store（append-only authority）
  context.py            713      DecisionContext freeze
  workflow.py          ~600      evaluate / reassess 編排（瘦身後）
  action_card.py        521      注意力狀態 ＋ approval boundary
  brief.py             ~400      決策摘要 pane（拆後）
  cli.py               ~450      決策命令（拆後）
  capital_authority.py  419      cash floor ＋ 貸款
  intake.py             334      Signal → Probe/Shadow ＋ source registry
  outcomes.py           289      lifecycle ＋ outcome attribution
  execution.py          250      live choice/fill boundary
  coverage.py           189      lane permission
  sizing.py            ~300      引用驗證 ＋ research_status（切後）
  models.py            ~180      immutable records
  adapters/alpha.py     新增      AlphaSignal → assessment payload
  workflow_ports.py     136      外部 authority ports
  bootstrap.py           21
```

（上表逐項相加 ≈ 7,927 行。**目標設 ≤ 8,000 而不是更漂亮的 ≤7,000，是因為逐項算得出來——
訂一個算不出來的數字，之後只會靠刪註解達成。**）

**驗收條件（L14：哪個數字會變）：**
- `decision_lab/` 行數 **13,502 → ≤ 8,000**
- `decision_lab` 的**直接相依環 3 條（`engine_d_runtime`／`thesis`／`engine_c`）→ 0 條**
- `tests/test_engine_d_separation.py`（新增）斷言 `decision_lab` 不 import `alpha`／`portfolio`／`risk`
- daily brief 端到端輸出**內容不變**（bytes 可變，pq2 項目數與首屏計數器不變）
