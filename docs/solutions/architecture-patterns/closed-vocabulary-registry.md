---
title: "封閉字彙登記表：哪些集合是鎖死的、住在哪、能不能擴充"
date: 2026-07-31
category: docs/solutions/architecture-patterns/
module: cross-engine
problem_type: architecture_pattern
component: configuration
severity: high
applies_when:
  - 遇到一個真實世界的事實塞不進既有欄位／狀態／關係
  - 想新增一個 blocker、觀測欄位、graph relation 或 lifecycle 狀態
  - 發現自己把細節寫進自由文字的「Caveat:」「附註：」
  - 某個值寫得進資料庫卻不影響任何決策
  - 交接時要知道哪些地方改 config 就好、哪些要改 code
tags:
  - vocabulary
  - registry
  - config-driven
  - extension-points
  - taxonomy-vs-contract
  - blocker
  - engine-a
  - engine-c
  - engine-d
  - schema-evolution
  - drift-guard
---

# 封閉字彙登記表

## 為什麼需要這張表

2026-07-30 一整個 session 的大部分時間，花在同一件事上：**讀 Python 才知道某個集合是封閉的、邊界在哪**。

具體是這樣發生的：AXT 的 2026-07-08 8-K 揭露 11 家 PE 基金合計 RMB 324,404,508（約 US$49M）的贖回權，加上 Coherent US$22,288,500 可退預付款，或有流出上限約 US$71.3M——足以把淨現金從 +$29.6M 翻成 -$19.4M。這是會改變 `financial_resilience` 判斷的事實。它成功寫進 Engine C 的 append-only ledger，卻**完全不影響任何決策**，因為 `engine_c/checklist.py` 把五個項目寫死在 Python 裡，讀不到第六個。

寫入 schema 開放、讀取 schema 封閉。資訊不是無法分類，是讀取端看不到。

同一個 session 還撞到另外三個同型問題：Digit 與 Digit v5 沒有可表達世代關係的 relation；未上市公司因為 `research_ticker` 被當成核心 identity 欄位而永遠 unresolved；`_explicit_authorities` 內建一份只含 graph token 的白名單，讓 Engine C 的 authority 被靜默過濾掉。

## 判準：taxonomy 還是 contract

這是能事先判斷的那條線。問一句：**這個集合是在描述「世界上有哪些東西」，還是在描述「系統允許哪些動作／狀態」？**

**Taxonomy** — 世界會長出新品類，字彙必須留鬆，且應該住在 `config/` 或 `schema/`。財務事實類型、graph relation、技術指標、高風險屬性都屬此類。

**Contract** — 刻意有限才有意義，打開它是 bug 不是修復。執行 intent、使用者動詞、狀態機轉移、資本 record 類型、Confidence 的五軸三級都屬此類。Confidence 五軸尤其如此：它是評分骨架且已凍進所有既有 decision 的 payload，config 化會直接削弱「舊 decision 永遠引用原 digest」的稽核契約。

## 登記表

### 可自由擴充（改 config 就好，不動 code）

| 字彙 | 位置 | 擴充方式 |
|---|---|---|
| node_type／abstraction_level／role／relation／qualification_status／demand_proof_level／source_type／evidence_tier | `schema/vocab.json` | 加一項；`loader/validate.py` 讀同一份。2026-07-29 的 robotics ontology 就是這樣加的 |
| 公司 ID ↔ research／execution 識別 | `config/company_identity.json` | 加一列；`identity/registry.py` 是唯一 loader |
| Engine C 人工觀測欄位 | `config/engine_c_observation_fields.json` | 加一項且 `gate_member` 必須為 false；`engine_c/observation_fields.py` 是唯一 loader |
| Blocker 說明與分類 | `config/decision_blockers.json` | 加 exact code 或 prefix；`decision_lab/blockers.py` 是唯一 loader |
| Authority token（證據來自哪個引擎、哪個軸能引用） | `config/authority_tokens.json` | 加一項並指定 `owner`；`identity/authority_tokens.py` 是唯一 loader，Engine C 與 Decision Lab 共用 |
| Engine B lead `refs` 鍵名 | `config/lead_ref_keys.json` | 加一項並說明用途與 value type；`engine_b/lead_refs.py` 是唯一 loader，`annotate`／`advance` 拒絕未登記鍵 |
| 投資／beta 政策數值、持股覆蓋分類、daily routine 參數、信號來源 | `config/investment_policy.json`、`config/beta_policy.json`、`config/holdings_coverage.json`、`config/daily_routine.json`、`config/signal_sources.json` | 各自為該領域的 numeric／設定 SSOT |

> ⚠ `config/*.json` 在 `.gitignore` 中**預設被忽略**（該目錄放 Google service account 憑證），靠白名單開例外。新增 config 檔一定要補 `!config/<name>.json`，否則 fresh clone 與另一個 agent 會缺檔而整個功能靜默失效——本機因為檔案在，測試還會全綠。2026-07-30 一天內踩到兩次。`tests/test_config_tracking.py` 是這道剎車。

### 刻意凍結（不要打開）

| 字彙 | 位置 | 為什麼凍結 |
|---|---|---|
| Confidence 五軸與三級 | `decision_lab/sizing.py` 的 `AXES`／`LEVELS` | 評分骨架，已凍進所有既有 decision payload |
| 軸 → authority 對照 | `decision_lab/sizing.py` 的 `AXIS_REFERENCE_AUTHORITIES` | 證據來源分權；它會擋下「拿 Engine A 文件冒充 Engine C 財務證據」這類錯誤 |
| 財務核驗清單五項 | `engine_c/checklist.py` 的 `items` | L9 前置條件 #3 的 Watchlist 升格 gate。`gate_pass` 對全體取 `all()`，加第六項會讓**所有既有標的**的 gate 退化 |
| lead 狀態機 | `engine_b/leads.py` 的 `ALLOWED_TRANSITIONS` | 狀態是行為不是分類；加狀態本來就要加邏輯 |
| 執行 intent | `decision_lab/workflow.py` 的 `_INTENTS`（research／paper／live） | 資本邊界 |
| 使用者動詞 | `engine_b/todo.py` 的 `VERBS`（`engine_b/batch.py` 另有一份含 `skip`） | 對話介面契約 |
| 資本 authority record 類型 | `decision_lab/capital_authority.py` 的 `_ALLOWED_TYPES` | 2026-07-30 定案只保留 cash_floor 與 credit_facility |

### 會再咬人（是 taxonomy，但目前寫死在 Python）

| 字彙 | 位置 | 會觸發它的具體事實 |
|---|---|---|
| 技術指標欄位 | `engine_c/technical.py` 的 `_METRIC_COLUMNS` | 想看相對強弱（vs QQQ）、ATR、Bollinger。同時是 DB 欄位，需配 migration |
| 高風險屬性 | `thesis/evidence_manifest.py` 的 `HIGH_RISK_ATTRIBUTES` | 學到新的危險屬性型態時（L11 那類體悟） |
| edge 衝突處理動作 | `loader/edge_resolution.py` 的 `ALLOWED_ACTIONS` | 需要「scope 切分」「移到 dated observation」時 |
> authority token 曾在此區。2026-07-31 已收斂為單一權威 `config/authority_tokens.json`——先前判斷「`decision_lab` 不得反向依賴 Engine C 所以無法合併」是過度套用分層規則：該規則擋的是依賴 Engine C 的 runtime authority，而 `decision_lab` 本來就直接讀 `config/`（beta_policy、decision_blockers、holdings_coverage、signal_sources）。改讀中立 loader 後三份副本剩一份，漂移不再可能發生。

## 兩個實用訊號

**訊號一：你開始把細節塞進自由文字。** 當你（或 agent）寫下「Caveat:」「附註：」「這個數字其實是…」，那就是撞到封閉讀取字彙了。系統裡有現成證據——AAOI 的 manual field 值是這樣的：

> `...Customer Concentration. Caveat: Q1 的 74.5% 是應收帳款集中度，不是營收占比；不得混用。`

那不是註解風格，是症狀：裝不進欄位的資訊被逼進機器讀不到的地方。這個訊號比讀 code 早得多。

**訊號二：某個值寫得進去卻不影響任何決策。** 如果你新增了一筆資料，然後任何 gate、軸、brief 都沒有變化，那它就掉進了讀取端的盲區。

## 加欄位的判準

不是「這個現象很複雜所以需要新欄位」，而是：**任何會改變決策的事實，都不能只住在自由文字裡。**

三層切分：**結構化欄位**（有限、已登記、階層式）承載機器要讀的部分；**自由文字**承載細節與 nuance；規則是會改變決策的維度才需要進字彙，其餘全部留給自由文字。這也回答了「字彙會不會無限長」——不會，因為門檻是「會不會改變決策」，不是「複不複雜」。

## 相關

- 判準源頭：AGENTS.md 的 L2（不要在動工前追求完美 schema：表的形狀鎖死、字彙留鬆）與 L4（屬性歸位三分）
- [`knowledge-graph-data-quality-and-engine-c-join-key.md`](knowledge-graph-data-quality-and-engine-c-join-key.md)：Engine A→C join key 為何必須是靜態 registry
- [`engine-d-content-addressed-decision-context.md`](engine-d-content-addressed-decision-context.md)：為何評分骨架不能熱改
