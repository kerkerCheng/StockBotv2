# Prospective Paper Portfolio

> Decision Lab 啟用後，private Decision Store 的 `paper_events` 是 system
> counterfactual transactions 唯一權威；`paper_position_projection` 只能由事件重播重建。
> 本目錄既有 CSV ledger 保留為歷史 characterization／fixture，不再是新 Probe 的 runtime。

`paper_portfolio.ledger.replay_decision_store_events()` 提供不寫檔的 domain replay facade。
System paper、Google Sheet live holdings 與使用者 live choice 是三種不同真相，彼此不得回寫。

本目錄的 `config.json`／`transactions.csv` 已退出 Git/runtime authority；若本機仍看得到，僅是
cutover 前留下的 ignored legacy 檔。Fresh clone 不需要也不應建立它們。新 runtime 位於
owner-only 的 `library/private/decision_lab/decision_lab.db`，完整 recovery export 也只能留在
`library/private/`。下方 CSV 操作說明只適用於 legacy characterization tests。

這是一個獨立的前瞻模擬投資帳本，用來稽核「當時知道什麼、怎麼決策、是否遵守 disproof 與部位規則」。它不會下實盤、不做歷史回填或回測，也不因少量績效宣稱 alpha。

## 邊界

- `transactions.csv` 是唯一交易事件真相；不建立或手改 `positions.csv`。
- 每筆事件在當下凍結 thesis hash、政策版本、成交價、FX、理由與 disproof 條件。
- 舊事件不可改寫。錯誤用 append-only `correction` 或 `reversal` 修正。
- 現金、持倉、NAV 與損益皆由 `ledger.py` 重放衍生；缺價格或 FX 時回 `unknown`，不猜值。
- reviews 保存研究判斷，不回頭改寫 thesis；績效只是 review context。
- 模擬帳本與 `thesis/`、Neo4j、Engine C 事實資料分離。Engine C 只提供當期價格/FX 輸入。

## 初始化

Repo 內的 `config.json` 刻意保持未初始化，避免把真實資產或未經使用者決定的幣別寫入版本庫。第一次使用須明確提供 base currency 與虛擬 NAV；可以使用標準化 NAV 100：

```powershell
python paper_portfolio/ledger.py init --base-currency USD --initial-nav 100
```

初始化後不可原地改 base currency 或 initial NAV；要重開組合需建立新的 portfolio。這裡的 NAV 是虛擬尺度，不是實際資產。

## 事件規則

合法交易順序為 `open → add/trim → close`。`target_weight` 是事件後相對該筆 `policy_decision.total_nav`（決策當下凍結 NAV）的目標權重；`changed_weight` 必須等於新 target 與「既有 units 依本次事件價換算的當下權重」之差。程式用事件價與 FX 把目標名目金額換成 units，並驗證現金與當時凍結的 U16 `maximum_position`。

`correction` 以 `corrects_event_id` 在重放時替換原事件；`reversal` 移除原事件的效果。原列與更正列都保留。若移除後使後續 state transition 不合法，整本帳拒絕重放，必須補完整的更正鏈。

## Review

每季、disproof 觸發或 close 時新增 `reviews/YYYY-MM-DD-<ticker>.md`，至少記錄：

- 原 thesis version/hash 與 evidence manifest ref
- 本次新證據與 disproof 狀態
- 若今天空手是否仍會建立
- 決定與理由
- 當期損益及選填 benchmark context

`SOXX` 可作半導體標的的機會成本對照，但不是 gate，也沒有自訂 AI basket。
