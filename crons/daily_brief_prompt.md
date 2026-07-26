# Daily Approval Brief — Codex 本機排程 Prompt（v1.2）

> 現行執行端是 Codex desktop 的 standalone local scheduled task，每日台北 06:30 直接在
> `C:\Users\Cheng\code\StockBotv2` 的 `master` working tree 執行。電腦需保持開機、Codex App
> 保持運行。不要建立 branch／worktree，也不要使用 Claude cloud clone 或遠端 MCP 降級路徑。

## 任務

明確使用 `$daily-brief` skill，產出一份繁體中文、action-first、穩定 pq2 編號的 Daily Brief。
這個本機 task 可直接讀 repo、`.env`、Neo4j、Engine C private runtime、Decision Store 與 Google Sheet；
X／EDGAR、Engine C ETL、today 與 todo pool 都在同一次執行完成。

## 執行契約

1. 先讀 `AGENTS.md` 與 `skills/daily-brief/SKILL.md`。確認目前 branch 是 `master`；若不是就停止並回報，
   不自行切 branch。若 working tree 有與本 routine 無關的使用者變更，保留不碰。
2. Windows 一律使用專案 interpreter：`.venv\Scripts\python.exe`，不得用 bare `python`。
3. 依序執行：
   - `.venv\Scripts\python.exe crons\harvest_leads.py`（X＋EDGAR；以 `since_id`／URL hash 去重）
   - `.venv\Scripts\python.exe engine_c\etl_yfinance.py`（35 檔 Engine C daily snapshot）
   - 對今日新增 pending leads 套 `skills/signal-triage/SKILL.md`，用本機 CLI 寫回 triage
   - `.venv\Scripts\python.exe -m decision_lab today --format markdown`
   - `.venv\Scripts\python.exe -m engine_b.todo sync`
   - `.venv\Scripts\python.exe -m engine_b.todo list`
4. 任何來源失敗都要誠實列出 `fetch_failed`／`parse_failed`；單一來源失敗不阻斷其他段落。X token
   只從本機 `.env` 讀取，不得輸出或搬移 token。
5. 先組出不會因研究失敗而消失的心跳 snapshot，再 best-effort 執行
   `.venv\Scripts\python.exe -m engine_b.cli drain`。每輪上限由 `config/daily_routine.json` 控制；
   tracked tickers 由非 retired lifecycle 與 non-terminal Decision cohorts 自動導出。對最高 priority leads 逐則
   source-trace＋extract，checkpoint `researching` → `action_prepared`。有可核准 graph delta 才 prepare；
   追源未果、原主張被否定或僅屬 Engine C 時變 observation 時 park 並記 outcome，不製造空 RA。
   只有 prepared RA 才進 pq2；triage PASS 與 pq1 自動研究都不代表入圖核准。
6. Graph admission、thesis retire／revise、Google Sheet 真實持倉值、`record-choice`／`record-fill` 永遠
   保留人工 gate；不得因 routine recommendation 推定使用者核准。
7. 收尾執行 `.venv\Scripts\python.exe scripts\publish_daily_state.py`。這支固定 publisher 只准提交
   `library/leads/pending_leads.json` 與 `library/leads/todo_pool.json`；若 guard 拒絕，保留檔案並在 brief
   回報，不要改用廣泛 `git add/commit/push` 繞過。

## 輸出

只用 `library/leads/todo_pool.json` 的既有穩定編號；不得依 section 或當日排序重新編號。

```text
# Daily Brief <YYYY-MM-DD>

## 需要你動作
[N] <type> — <摘要> → <為什麼需要決定>

## 新 leads（依 priority）
<僅列 pq1 進度／失敗；raw lead 不占 pq2 編號>

## 健康／資料降級
<本次 harvest、Engine C、Neo4j、Sheet 的失敗或缺口；無則寫正常>

## 無事項目
<NO ACTION 類別>

回覆：`<編號…> go｜drop｜pending`（例：`13 17 go 10 16 pending`）
```

即使無新事項，也輸出 `NO ACTION + 日期` 心跳。Daily brief 不另存 report；稽核由 todo log、leads
狀態機、Decision Store 與窄 state commit 承擔。
