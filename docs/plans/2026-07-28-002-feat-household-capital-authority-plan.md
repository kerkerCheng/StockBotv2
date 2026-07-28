---
title: Household Capital Authority Phase II-A - Plan
type: feat
date: 2026-07-28
topic: household-capital-authority
status: completed
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: user-directed
execution: code
completed: 2026-07-28
---

# Household Capital Authority Phase II-A - Plan

## Goal Capsule

- **Objective:** 在不改變 Google Sheet live inventory authority、也不取得 Sheet 寫入權限的前提下，讀取私人
  `Capital Authority` tab，建立 content-addressed point-in-time household capital view，並把自有現金與未動用
  貸款清楚分流。
- **User outcome:** Daily Beta output 同時呈現 `sheet_conservative_range`、
  `household_cash_supported_range`、`contingent_credit_available`、`loan_funded_supported_range`，避免把可借額度
  誤認為可部署現金，也避免私人 operating floor 靜默取代 Phase I 的 5% NAV reserve。
- **Authority contract:** 自有 cash 金額仍只認 `Portfolio`；`Capital Authority` 只提供 cash routing、operating floor、
  planned outflows 與 credit-facility 條款。所有 Google API scope 維持 `spreadsheets.readonly`；本切片不建立 writer、
  choice、fill 或 broker order。
- **Execution profile:** 本次完成 read-only adapter、strict validation、freshness／FX fail-closed、capital snapshot、
  Engine D 四欄輸出、Daily runbook／skill、測試、真實 Sheet 唯讀驗收、文件、commit 與 push。
- **Stop conditions:** 若需要把個人金額寫進 tracked repo、猜 missing FX、把 undrawn facility 加入 NAV／cash、以
  recommendation 推定提款核准、或新增任何 Sheet write scope／API method，立即停止並降級。

---

## Scope Decision

### Phase II-A — 本次實作與驗收

1. `fetchers/gsheets.py` 新增獨立 `Capital Authority` 唯讀 fetcher；不讓 Portfolio-only consumer 因新 tab 缺失而
   改變既有行為。
2. 對已定案的 28 欄 schema 做 exact header、record ID、record type、數字、布林、幣別、日期與重複資料驗證；
   私人 free-text notes 不進 Daily public output。
3. 建立 point-in-time capital snapshot 與 SHA-256 digest；authority 過期、future-dated、缺 required record、cash
   routing 不符、FX missing／stale／direction mismatch 都只讓 household range fail closed。
4. `household_cash_supported_range` 以 Portfolio cash 扣 private operating floor、planned outflows 與既有 3% NAV
   alpha reserve；再沿用 Phase I campaign、leverage、technology、issuer cap 做同一輪 sequential allocation。
5. 原本 Phase I `supported_order_range_base` 與 `sheet_conservative` aggregate 保留；household 候選並列，不覆寫
   Phase I，不升格 live permission。
6. `contingent_credit_available` 只顯示可用額度、幣別、條款完整度與 blockers；不得進 NAV、deployable cash 或
   任一 instrument allocation。
7. `loan_funded_supported_range` 在沒有 exact user choice 時固定為 `manual_review_required`，不輸出自動金額；
   `drawn_amount > 0` 或 minimum-payment／可變條款不完整時額外 fail closed，不假裝 household net capital 已完整。
8. Daily Markdown 與 JSON 都輸出四欄；beta household authority 故障列入健康降級，但不進 pq1／pq2，也不阻斷
   technical monitor 與 Phase I range。

### 明確不在本切片

- Google Sheet writer、tab／欄位自動建立、成交回寫與 reconciliation receipt。
- loan draw workflow、debt-service stress engine、stacked-leverage live promotion。
- ETF point-in-time 完整 look-through、intraday／regional scheduler、always-on server。
- 每日 LLM 黑天鵝研究、Engine A graph admission 或新的 pq 流程。

---

## Product Contract

### 四欄語意

| 欄位 | 來源 | 是否可進 deterministic allocation | 失敗語意 |
|------|------|-----------------------------------|----------|
| `sheet_conservative_range` | Portfolio cash − 5% NAV operating − 3% NAV alpha | 是，paper observation | 沿用 Phase I fail closed |
| `household_cash_supported_range` | Portfolio cash − private floor − planned outflows − 3% NAV alpha | 是，paper observation | 只歸零 household 欄 |
| `contingent_credit_available` | undrawn verified facility | 否 | unavailable／incomplete terms |
| `loan_funded_supported_range` | exact human-reviewed draw proposal | 否（本切片） | 固定 `manual_review_required` |

### Required Capital Authority records

- 一筆 `portfolio_cash_authority`，`amount_source` 必須指向 Portfolio cash；不得另填 amount 後重複加總。
- 一筆 `operating_floor`，有 finite non-negative `amount` 與三碼 currency。
- 一筆 `planned_outflows_reserve_24m`，有 finite non-negative `amount` 與三碼 currency。
- 至少一筆 `contingent_liquidity_credit_facility`；limit／drawn amount 合法、drawn 不大於 limit、automatic deployment 必須 false、
  deployment mode 必須是 manual review。

### Acceptance Tests

- Reader 只呼叫 Sheets `values.get`，credential scope 仍只有 `spreadsheets.readonly`；程式碼中無 `update`、
  `append` 或 `batchUpdate` 路徑。
- 正常 fixture 可產穩定 digest 與四欄；改變任一經驗證 authority scalar 會改 digest。
- 缺 tab、缺 header、duplicate record、stale／future as-of、錯幣別、FX missing／stale／wrong direction、cash routing
  不符時，household range 歸零且 blocker 不洩漏 secret／notes；Phase I range 保持原值。
- 任意 credit limit 增大都不改變任何 instrument 的 Phase I／household cash range。
- `drawn_amount > 0` 不會被當成 undrawn cash；在 Phase II-A 未完整建 debt authority 前 household range 歸零並要求
  debt review。
- 真實 E2E 可讀 Portfolio＋Capital Authority、取得 FX、輸出四欄；執行前後 Sheet digest／read-back 值不變。
- targeted tests、skill sync check 與 full suite 全綠。

---

## Implementation Units

- [x] **U1 — Read-only Sheet surface:** 新增 Capital Authority range reader、exact schema 與 reader tests。
- [x] **U2 — Capital view:** 新增 validation、freshness、FX normalization、digest 與 degraded-safe unit tests。
- [x] **U3 — Dual allocation view:** 抽出可重用 sequential allocator，保留 Phase I 並產 household candidate ranges。
- [x] **U4 — Daily integration:** 固定 entry 同次抓 capital records／needed FX，輸出四欄與健康狀態。
- [x] **U5 — Contract/docs:** 更新 daily skill、prompt、brainstorm、AGENTS、plan index，執行 skill sync。
- [x] **U6 — Verification:** targeted／full tests、真實 Sheet 唯讀 E2E、盲點審查、complete plan、commit/push。

---

## Rollback Boundary

本切片沒有外部 write migration。若 household path 發生問題，可移除 capital fetcher／snapshot wiring，Phase I
`supported_order_range_base` 與 Engine C technical ledger 不受影響。私人 Sheet 不由 runtime 修改，因此不需要資料回滾。

---

## Completion Notes（2026-07-28）

- Google credential scope 保持單一 `spreadsheets.readonly`；Capital Authority reader 只使用 `values.get`，沒有
  `update`／`append`／`batchUpdate` 路徑。
- 真實 E2E 成功讀取 Portfolio、4 筆 Capital Authority records 與 exact-direction TWD/USD；連續兩次 read-back
  content digest 一致，沒有 Sheet mutation。個人 exact 金額未寫入 tracked repo。
- Daily JSON／Markdown 已輸出四欄；當 household authority／FX 故障時只歸零 household range，Phase I
  `supported_order_range_base` 與 `sheet_conservative_range` 保持可用。
- 現有 facility 的最低還款條款仍未完整，因此 contingent credit 誠實標示 `credit_terms_incomplete`；額度沒有進
  NAV、cash 或任一 allocation，loan-funded range 固定 `manual_review_required`。
- 盲點修補：drawn debt 判斷不依賴 facility FX；只要 drawn amount 非零就封鎖 household cash path。household
  全域故障只在資本健康列呈現，不再把所有標的重複洗版成暫停。
- 驗證：targeted suites passed；full suite **598 passed**；skill adapters sync；`git diff --check` 通過。
