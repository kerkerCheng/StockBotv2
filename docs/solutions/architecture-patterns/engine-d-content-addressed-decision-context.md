---
title: "Engine D：以 Content-Addressed Context 建立決策與責任層"
date: 2026-07-22
category: docs/solutions/architecture-patterns/
module: decision-lab
problem_type: architecture_pattern
component: service_object
severity: medium
applies_when:
  - "需要把 Engine A/B/C 的研究輸入轉成可稽核的投資決策時"
  - "需要保存決策當下看到的資料，但不能複製外部 current-state authority 時"
  - "需要讓 system paper 與人工 live execution 共存時"
related_components:
  - database
  - assistant
tags:
  - decision-lab
  - engine-d
  - decision-accountability
  - point-in-time-context
  - content-addressed
  - authority-boundary
  - human-in-the-loop
---

# Engine D：以 Content-Addressed Context 建立決策與責任層

## Context

StockBotv2 原有 Engine A（知識圖譜）、Engine B（Signal discovery／intake）與 Engine C（財務／市場 observation），但三者都不適合擁有「當時為何建議這個行動、允許多少資本、使用者最後怎麼選、結果如何」這組責任資料。把這些 facts 塞回圖譜會混入高頻時序與個人部位；只輸出研究報告又無法事後區分來源、系統與使用者各自的決策品質。

因此 Decision Lab 應正式定位為 **Engine D — Decision & Accountability Engine**。它不是第四個資料來源，也不是自動交易器；它消費上游研究與狀態，保存 point-in-time decision context、資本許可、paper counterfactual、明確的使用者 live facts 與 outcome attribution。產品邊界與名稱的 current authority 見 `AGENTS.md:35-62` 與 `CONCEPTS.md:96-108`。

這個定位也修正一個容易造成錯誤實作的說法：「凍結圖譜」不是替整張 Neo4j 建 snapshot，而是凍結某次 assessment 實際使用的 **Engine A decision context slice**。

## Guidance

### 四引擎先分 authority，再談 workflow

| 引擎 | 擁有的 current truth | Engine D 保存什麼 | Engine D 不可做什麼 |
|------|----------------------|-------------------|----------------------|
| Engine A | claim、供應鏈／瓶頸關係、provenance | 本次使用的 stable IDs、source refs、causal／counter path 與 normalized evidence slice | 寫圖、把未追源 Signal 升格、保存全圖副本 |
| Engine B | Signal discovery、來源登記與 intake 狀態 | qualified Signal、cohort、Shadow inception 與來源 snapshot | 把 whitelist 當 evidence、推定 funded eligibility |
| Engine C | 帶時戳的財務、市場、估值與 manual observations | 本次計算使用的 scalar、status、as-of、fetched-at 與 source refs | 維護第二份 current financial projection |
| Engine D | immutable decision history、paper events、明確 user choice/fill、lifecycle/outcome | 自己的完整 authority | 取代 Google Sheet live inventory、推定成交、broker routing |

Google Sheet 與 versioned policy 是額外 authority：前者擁有 live inventory，後者擁有門檻與 sizing 規則。Engine D 只凍結 assessment 使用的 holdings confirmation 與 `policy_version`，不複製一份可獨立修改的真相。

### 凍結決策內容，不凍結資料庫

`build_context_bundle()` 接受 identity、evidence、financial、market、FX、holdings、paper exposure、execution venue data 與 freshness policy，將 normalized payload canonicalize 後計算 SHA-256 digest（`decision_lab/context.py:300-317`、`decision_lab/context.py:491-507`）。`DecisionStore.freeze_context_bundle()` 會重算 digest、核對 cohort identity，並拒絕同一 digest 對應不同內容（`decision_lab/store.py:516-565`）。

因此一份 point-in-time context 應只回答「這次決策實際用了什麼」：

1. atomic claim 與 canonical company／ticker；
2. 一條 claim-to-economics causal path；
3. 一條 substitution／counter-thesis path；
4. 直接支撐主張的 source/provenance 與 graph stable IDs；
5. 財務、價格、FX、持股與 paper exposure 的值、狀態與時間；
6. policy、rubric、calculator 與 query attribution 版本。

它不是 Neo4j disaster-recovery artifact，也不保證能重建 Engine A。Engine A 可持續由其他研究流程入圖；舊 decision 繼續引用原 `context_digest`。若要比較現在的圖，只產生 attributed delta diagnostic，現有 graph adapter 明確回傳 `automatic_repair = False`（`decision_lab/adapters/graph.py:87-148`）。

### Engine A 對 Engine D 是唯讀 consumption boundary

Decision Lab 的 graph port 只接受單一 read query，拒絕 write keywords、`CALL` 與多語句，並以 READ access mode 開 session（`decision_lab/adapters/graph.py:15-50`）。這是 application-level guard；production 仍應使用 Neo4j least-privilege read credential，不能把 routing hint 當成伺服器 RBAC。

未來的 operational workflow 應負責「查 Engine A → 組 bounded evidence slice → freeze context」，但不得為了方便另建一套 graph admission、source-trace 或 evidence tier 規則。完整圖的更新仍走既有 Engine A intake／approval 管道。

### paper 可以原子套用，live 永遠需要明確的人

`assess_probe()` 使用已保存的 context 與 coverage；eligible 時 system decision 與 funded paper event 在同一 transaction 落地（`decision_lab/execution.py:36-106`）。Paper 是使用虛擬 NAV 的 prospective counterfactual，不是 broker order。

Live lane 只提供 supported range。使用者必須明確接受、縮小、跳過或 override，親自下單，再以 explicit report 記錄 fill（`decision_lab/execution.py:113-158`）。Recommendation、choice、fill 與 Google Sheet current position 是不同 facts，不能互相推定。

### 新入口只編排既有 primitive

CLI、Daily Brief、skill 或 remote MCP 都應重用同一組 capture、context、coverage、sizing、execution、card 與 outcome primitive。入口可以改變，以下內容不能分叉：

- 不建立平行 Coverage Gate 或 sizing 公式；
- 不建立第二份 paper／live position truth；
- 不因排程或遠端入口擴大交易權限；
- 資料缺失時保留 Shadow／work order，funded range 歸零而不是猜值；
- re-assess 產生新 context，不回頭改寫舊 decision。

## Why This Matters

Content-addressed point-in-time context 讓系統能回答「在當時的資料與 policy 下，為何做出這個建議」。若事後只重查最新 Engine A/C，新增證據、修 edge conflict、價格更新或 policy 變更都會悄悄重寫歷史推理背景。

只凍結 bounded slice，則 Engine A 仍可作為持續成長的研究記憶；Engine C 與 Google Sheet 仍擁有 current state；Engine D 只擁有不可變的決策責任。這同時避免 selection bias：Shadow、零部位、使用者 skip／override 與 funded paper 都留在同一 prospective cohort，而不是只保存最後有交易的案例。

人工 live boundary 則確保「系統提出行動」不等於「系統獲得送單權」。Engine D 可以讓建議更 actionable，但不能把產品定位偷換成 broker automation。

## When to Apply

- 每個通過 Probe Gate、值得進入 prospective cohort 的 Signal。
- 每次 assess、re-assess 或 revised lifecycle epoch。
- Engine A/C、market／FX、holdings 或 policy 會改變，而未來需要還原 decision-time reasoning 的流程。
- 建立 on-demand workflow、Daily Brief、remote decision surface 或新的資料 adapter 時。

不要用於 Engine A backup／migration、graph admission、未追源資料升格或 broker routing。

## Examples

錯誤做法：

```text
Signal → dump 整張 Neo4j → 用全圖 checksum 當 decision context
       → 其他研究 agent 正常入圖 → 舊 decision 被誤判為遭修改
```

正確做法：

```text
Engine B Signal
  + Engine A bounded evidence / causal slice（唯讀）
  + Engine C financial / market observations
  + confirmed Google Sheet holdings
  + versioned policy
        ↓
Engine D freeze content-addressed context
        ↓
Coverage → Confidence → system decision
        ├─ eligible paper：原子建立 counterfactual event
        └─ live range：等待使用者選擇、手動下單與回報
        ↓
Action Card → lifecycle → outcome attribution
```

SIVE 類型的社群 Signal 可以先建立 Shadow；若只有技術 reference design、尚無 production order，commercial axis 會限制 supported capital。之後出現新證據時建立新 assessment/context，而不是把新資料倒回最初的 decision。

## Related

- `docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md` — v1 設計與驗收歷史。
- `docs/investment-sop.md` — paper/live、Google Sheet 與人工決策邊界的規則語意權威。
- `docs/solutions/architecture-patterns/knowledge-graph-data-quality-and-engine-c-join-key.md` — Engine A→C canonical identity／join key。
- `docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md` — Engine C backend 選型歷史；runtime authority 以目前程式、AGENTS 與 SOP 為準。

