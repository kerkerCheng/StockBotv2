---
name: luna-reviewer
description: >-
  明確 opt-in 的 Luna 委派＋主代理 review 工作流。只在使用者明確輸入
  `$luna-reviewer ...`、`Luna reviewer：...`、`Luna reviewer: ...`，或清楚說
  「這次用 Luna reviewer」時使用；不得因任務看起來機械、便宜、適合平行化，
  或只提到 pq1、alpha、audit 而自動啟動。適用於 pq1 bounded drain、alpha 事實蒐集、
  repo／queue 盤點、測試與 log 分析等可逐項驗收的唯讀子任務。Luna 只交 review packet；
  主代理負責選樣、驗證、唯一寫入、人工 gate 與最終結論。
---

# Luna Reviewer

把本 skill 視為既有 `.codex/agents/luna-operator.toml` 的手動啟動器，不建立第二個 agent。

## 啟動語意

- 每次明確觸發只授權該次指令；完成後自動退出，不跨到下一個使用者指令。
- 沒有觸發前綴時維持一般主代理流程，不自行派 Luna。
- `$luna-reviewer` 與 `Luna reviewer：` 等價。
- 若使用者輸入 `Luna reviewer：停止`，停止尚未完成的 Luna 子任務；已完成的 review packet 仍不構成 authority。
- 若 `luna_operator` 無法使用，不得靜默改派較昂貴的其他 subagent；由主代理說明後自行處理或等使用者決定。

常用指令：

```text
Luna reviewer：pq1 5
$luna-reviewer pq1 5
Luna reviewer：alpha NBIS，先做財務五項與反證蒐集
Luna reviewer：repo audit，檢查 queue schema 與測試失敗
```

## 分工契約

### Luna (`luna_operator`)

- 只做明確、有限、可獨立驗收的唯讀工作。
- 適合 source-trace、原子 claim／locator 抽取、固定清單事實蒐集、queue／repo 盤點、測試與 log 分析。
- 每份回傳包含 scope、result、evidence、conflicts、commands、review_required。
- 不寫 working tree／private authority，不改 lead／todo，不 prepare／apply RA，不做 graph admission、pq2 resolve、thesis 或投資結論。

### 主代理

- 開始前讀 `AGENTS.md` 與任務觸發的 domain skills；決定 acceptance criteria 與不可委派部分。
- 解析 deterministic scope；需要 checkpoint／lock 時由主代理寫入後才派工。
- 最多平行派三個 `agent_type="luna_operator"`，使用互不重疊的 bounded shard；優先 `fork_turns="none"` 並在 prompt 提供必要路徑、ID、判準與交付格式，減少昂貴 context 複製。
- 逐份 review packet：核對 primary source、日期、identity registry、來源獨立性、graph delta／Engine C observation 分流與 authority boundary。只重開會改變 disposition 的決定性證據，不重做整輪廣搜。
- 主代理是唯一 writer，負責狀態轉移、Research Action、驗證、commit／push與最終對使用者輸出。

## 任務路由

### `pq1 N`

1. 由 current config 與 priority authority 取得 deterministic 前 N 筆；不得讓 Luna 自選 queue。
2. 主代理 checkpoint exact IDs，再按來源或主題切成最多三個互斥 shard。
3. Luna 執行 source-trace、claim 拆解、原文 locator、支持／反證與建議 disposition。
4. 主代理逐筆判定 `parked`、`action_prepared` 或其他合法狀態；只有真正的最小 graph delta 才 prepare RA，永不自動 apply。

### `alpha <標的／主題>`

1. 主代理先定義候選 universe、財務五項、variant perception 所需資料、disproof 與估值／freshness 日期。
2. Luna 只蒐集固定清單事實、primary sources、相反證據與缺口。
3. 主代理完成 thesis synthesis、證據強度、估值含義、watchlist／underwrite 判斷與任何資本結論。

### 其他任務

只委派其中可唯讀、機械驗收的部分；需要設計取捨、authority mutation、投資判斷或跨檔寫入的部分保留給主代理。

## 收尾輸出

至少報告：

- Luna shard 數、處理項目數與主代理 override 數；
- 每項最終 disposition 與仍需使用者核准的 exact ID；
- 驗證命令與結果；
- 是否有 graph／Engine C／D／live mutation；
- 平台若未提供 agent token／費用，不虛構金額；改以「多少初查由 Luna、多少進主代理深審」呈現可驗證的成本代理指標。
