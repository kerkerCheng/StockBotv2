# Weekly 審查 — Codex 本機 Prompt（v1.2）

> 現行執行端是 Codex 本機 scheduled task（台北週日 04:00），直接在 `master` working tree 執行。
> 不建立 branch／worktree、不走 Claude cloud clone、不靠 MCP 才能讀本機 authority。Windows 命令一律
> 使用 `.venv\Scripts\python.exe`。

## 定位

Weekly 只做三件事：

1. **Topic discovery（發現未知）**：掃 watch 清單外的新公司／新題材，只到 topic digest，不追源、不抽取。
2. **系統健康審查**：直接跑本機完整 health audit；可確定性修復的維護問題先修再複查。
3. **Lifecycle 唯讀提醒**：`retired`／`revised` 與正式核查結論仍由使用者決定。

Daily 負責已知來源的 X／EDGAR harvest、triage、Engine C refresh、today 與統一 pq2 brief；Weekly
不重做 daily backlog，也不另建第二套編號。

## 執行流程

### Stage 0 — 前置

1. 讀 `AGENTS.md`、`config/themes.txt`、`skills/signal-triage/SKILL.md`、
   `library/leads/todo_pool.json` 與前一份 `docs/reports/weekly_scan_*.md`。
2. 確認 branch 是 `master`；不是就停止並回報。保留所有無關的使用者變更。
3. 跑 `.venv\Scripts\python.exe query\health_audit.py --local`，把它當健康查詢唯一權威。

### Stage 1 — Topic discovery

- 對每個 active theme 搜尋過去 7 天的新事件；每個主題以 2–3 次搜尋為度。
- 掃 Engine B 策展來源近期內容，但 X 已由 daily API harvest 覆蓋，Weekly 只找 daily watch 外的聚類與
  新題材，不重複按 tweet 建項。
- 對材料套 signal-triage 五要素；同一事件聚成一個 topic。
- 每個 topic 給摘要、來源連結、影響、為何值得 research，以及 `research`／`onboard`／`FYI`。
- **到此停止**：不跑 source-trace、不抽 claim、不 prepare／apply Research Action。

### Stage 2 — 健康修復邊界

- 可直接修：ETL 過期、可重建的 index/cache、skill adapter 漂移、明確的 code/config 錯誤。修後重跑 audit。
- 不可假裝修：單一來源補證、SIVE.ST `customer_concentration`／`backlog`、thesis lifecycle 結論、
  Google Sheet 的真實 `nav_base`／`market_value_base`。這些需要證據或使用者 authority。
- 健康 finding 與 pq2 是正交的：純維護不進 pq2；需要使用者研究／資料／thesis 判斷才進統一待辦池。

### Stage 3 — pq1／pq2 同步

- Weekly 中建議 `research` 且尚未存在的重大 topic，使用
  `.venv\Scripts\python.exe -m engine_b.cli register --source weekly:<theme> --url <url> --title "<事情>"`
  註冊成 lead，再依 signal-triage 寫回 PASS／FILTER。PASS 進自動 pq1，不直接占 pq2 編號。
- `onboard` 只有在完成公司文件研究、形成 prepared action 後才進 pq2；純候選仍留 Topic Digest。
- lifecycle／decision blocker 交由 `.venv\Scripts\python.exe -m engine_b.todo sync` 收斂。
- prepared RA 與 authority 決策才引用 todo pool 的穩定編號。Weekly 不在報告內另造核准編號。

### Stage 4 — Report

輸出並保存 `docs/reports/weekly_scan_<YYYY-MM-DD>.md`：

```text
# 週審查 — <日期>
## 30 秒 brief
## Topic Digest
## Thesis 核查
## 系統健康審查（修前／修後）
## Triage 稽核
## 建議 onboard 候選
## pq2（只列真正需使用者決定的穩定編號）
```

只提交本週 report 與本次確實更新的統一 state files，直接在 master push；不要開 PR／Issue。若 working
tree 或 Git guard 使安全提交不成立，就保留檔案、回報原因，不擴大 pathset。

## 鐵律

- 全程繁體中文。
- 不確定就標示不確定；找不到值得說的事也要輸出 sparse-week 心跳。
- 不追源、不抽取、不入圖、不改 lifecycle 結論、不替使用者填真實持倉。
- Weekly 只把真正需決定的大事送 pq2；健康維護先自動修，證據缺口保留為明確 blocker。
