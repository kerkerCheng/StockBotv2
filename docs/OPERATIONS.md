# StockBotv2 — 操作手冊 (Operations Runbook)

> 這裡是「怎麼跑」：指令、環境變數、排程流程、已知操作陷阱。
> 「為什麼這樣做」與判準在 [`AGENTS.md`](../AGENTS.md)；交付歷史與待辦方向在 [`ROADMAP.md`](ROADMAP.md)。
> **實際操作前讀本檔；只做判斷或研究時不必載入。**

所有 Python 命令一律使用 repo venv：`& '.venv\Scripts\python.exe' ...`

---

## 每日操作

本機說「daily brief」或由 06:30 排程觸發 `$daily-brief`。流程：

```
Codex local scheduled task
  → X／EDGAR harvest
  → Engine C financial／beta technical ETL
  → 單一 shared-cash-pool beta monitor
  → triage
  → priority pq1 best-effort drain
  → prepared RA／today／lifecycle todo sync
  → brief
```

排程收尾只跑 `scripts/publish_daily_state.py`（窄 state publisher，只發布 `pending_leads.json` ＋ `todo_pool.json`，不得用 unattended 廣泛 Git 命令碰其他檔）。

**Routine 分工：**
- daily（`crons/daily_brief_prompt.md`）＝harvest ＋ ETL ＋ beta monitor ＋ triage ＋ today ＋ 統一 pq2 brief
- weekly（`crons/weekly_scan_prompt.md`，台北週日 04:00）＝topic discovery ＋ 完整本機健康審查 ＋ 唯讀 lifecycle，報告留 `docs/reports/`

兩者刻意錯開，且都不替使用者寫 thesis 結論、入圖或建立 live facts。

---

## 常用指令

### 待辦池（統一 pq2）
```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync          # 同步後列出（＝「待辦事項統整」）
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb go|drop|pending [--reason ...] [--receipt ...]
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb pending --until 2026-08-27 --trigger "Q2 財報"
& '.venv\Scripts\python.exe' -m engine_b.todo dispatch <n>  # decision_review → pq1 job
& '.venv\Scripts\python.exe' -m engine_b.todo work <n> --to researching|completed|parked --receipt ...
& '.venv\Scripts\python.exe' -m engine_b.todo complete-ra <n> --digest <sha256> [--company-id ...]
```

`pending` 帶 `--until`／`--trigger` 會歸入「等事件」區，觸發前不佔決策注意力。分類判準見 `config/decision_blockers.json` 的 `resolution_mode`。

### Leads
```powershell
& '.venv\Scripts\python.exe' crons\harvest_leads.py                 # 零 token；--dry-run 只印不寫
& '.venv\Scripts\python.exe' -m engine_b.cli drain                  # pq1 依 priority 的下一批
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go|--no-go --tier N --reason ...
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> <status> [--ref k=v]
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog          # parked 追源未果與 trigger
& '.venv\Scripts\python.exe' -m engine_b.cli related <lead_id>      # 共用具名標的的其他 lead
& '.venv\Scripts\python.exe' -m engine_b.cli harvest-health         # 各來源最新未恢復失敗
```

Leads authority 是 tracked `library/leads/pending_leads.json`；狀態機與 API 見 `engine_b/leads.py`。

### Engine D 決策
```powershell
& '.venv\Scripts\python.exe' -m decision_lab evaluate-signal "<Signal>" --ticker <T> --intent research --format markdown
& '.venv\Scripts\python.exe' -m decision_lab reassess <decision_id|cohort_id> --assessment <a.json> --intent research --format markdown
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
& '.venv\Scripts\python.exe' -m decision_lab card <decision_id>
```

只有使用者明確要求才用 `--intent paper`／`live`；live 另加 `--confirm-holdings`。決策命令只在本機執行；遠端 chat 看決策才用 MCP 唯讀 `get_decision_brief`。

### Engine C
```powershell
& '.venv\Scripts\python.exe' engine_c\etl_yfinance.py <TICKER>
& '.venv\Scripts\python.exe' engine_c\checklist.py <TICKER>
& '.venv\Scripts\python.exe' -m engine_c.set_manual_field --fields <T>   # 列出已登記觀測欄位（階層式）
& '.venv\Scripts\python.exe' -m engine_c.set_manual_field --list <T>     # 列出該標的已填欄位
```

⚠ **寫入含 `$` 的金額字串不要經 PowerShell 傳參**——`US$71.3M` 會被當變數前綴展開成 `US.3M`，在 append-only ledger 造成需 supersede 才能更正的損毀。用 Python 或 heredoc。

### Beta 快照
```powershell
& '.venv\Scripts\python.exe' scripts\daily_beta_snapshot.py --format markdown --risk-view changes
```
輸出明標 `policy_mode=paper_observation`、`capital_scope=shared_cash_pool`；不建立 choice／fill、不下單、不寫 Sheet、不把 undrawn loan 算資本。

### 入圖收尾
```powershell
& '.venv\Scripts\python.exe' scripts\commit_pending_intake.py --status | --dry-run
& '.venv\Scripts\python.exe' scripts\commit_pending_intake.py      # 每 action 一 commit、整批一 push
```

### Skill 轉接層
```powershell
& '.venv\Scripts\python.exe' scripts\sync_agent_skills.py           # 新增 skill 或改 name/description 後
& '.venv\Scripts\python.exe' scripts\sync_agent_skills.py --check   # 交接前驗證兩端無漂移
```

---

## 環境變數

| 用途 | 變數 |
|------|------|
| Engine A 讀寫 | `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、可選 `NEO4J_DATABASE` |
| Engine A 決策唯讀（**不得 fallback 到可寫帳號**） | `NEO4J_DECISION_READER_USER`、`NEO4J_DECISION_READER_PASSWORD` |
| Live holdings | `GSHEETS_SERVICE_ACCOUNT_JSON`、`GSHEETS_SPREADSHEET_ID`、可選 `GSHEETS_SHEET_NAME` |
| X harvest（**只放本機**） | `X_BEARER_TOKEN` |
| Engine C Postgres（可選，預設 SQLite） | `POSTGRES_HOST`／`POSTGRES_DSN` |
| MCP | `GRAPH_MCP_PORT`、`GRAPH_MCP_TOKEN` |

Sheet adapter 的標準輸出是 `ticker`、`shares`、`currency`、`market_value_base`、`nav_base`、`base_currency`；可直接提供完整標準欄位，或以逐列 mark-to-market `market_usd` 安全正規化成 USD NAV。**禁止退回 `avg_cost` 或 `market_twd` 猜值。**

Price／FX 預設 yfinance（無 API key）。非同幣 FX 缺失或方向不符一律 fail closed。

---

## X／EDGAR harvest 細節

**X API 是主來源**（`crons/harvest_leads.py` 的 `harvest_x`）。曾經的「SubStack RSS 就夠」前提已被推翻：該 feed 至今只有 1 篇 2026-05-19 舊文，但本人在 X 極度活躍（[@aleabitoreddit](https://x.com/aleabitoreddit)，顯示名 Serenity）。substack feed 已於 2026-07-25 移除。

**成本模型（2026-02 起 pay-per-use）：** 約 $0.005/則、按回傳貼文數計費、無月費下限。控制四件套實測有效：`since_id` 增量、`exclude=replies,retweets`、`max_results` 上限、`user_id` 快取。實測首抓 23 則 $0.115；立即重跑 0 則 $0.000。日常估 $1–2/月。

**內容保存：** tracked lead 存單行可搜尋全文 `title` 與保留換行的 `raw_text`；API 同回應請求 `note_tweet` 與 `attachments.media_keys` expansion，media metadata 隨 lead 保存，預覽快取至 ignored `library/private/lead_media/`。harvest 不做 OCR。舊 lead 可用 `--refresh-x-lead <lead_id>` 精準回填，不做全量昂貴 backfill。

**歷史回補：** `--backfill-x-handle` 以 RFC3339 time window ＋ pagination token ＋ `max_posts` 成本硬上限；可納入 replies，且**不得推進 daily `since_id`**。

**⚠ 只在本機跑。** 任何 cloud fallback 都不得抓 X，避免重複計費與擴大計費憑證 blast radius。

**⚠ 已知限制（未修）：** `harvest_x` 不分頁。若新貼文數超過 `max_results`（預設 25），單次只取部分而 `since_id` 仍前進 → **可能永久漏掉中間那批**。日常每天跑不會觸發；長時間沒跑（估 >2–3 天）再開機時要留意。要修就是加分頁並設總量上限。

**來源存取防漏：** harvest 失敗保存 bounded `failure_class`。疑似 sandbox／proxy／網路權限造成的 `access_blocked` **必須原命令權限重跑一次**；仍失敗再走 `$source-trace` 官方替代路徑。`blocked` 永遠不等於「零筆新資料」或 `no_result`，後續同來源成功才算 recovered。

---

## MCP server

本機 `mcp_server/graph_mcp.py` + Cloudflare Tunnel + connector，十二工具 surface，Git 能力僅 leads.json 一個窄例外。daily／weekly 現行排程不需要 MCP（直接在本機 repo 執行）。完整資料流與安全邊界見 [`remote-access-architecture.md`](remote-access-architecture.md)。

**⚠ 改完 `mcp_server/` 一定要重啟 process，否則遠端看到的是舊 tool surface。** 沒有 auto-reload：process 開機由 `shell:startup` 的 `stockbotv2-graph-services.vbs` 啟動、之後一直跑舊程式碼。2026-07-24 首次 daily routine 即因此回報「三支新工具不在 tool surface」（程式碼有、跑著的 process 沒有）。

重啟：停掉 `graph_mcp` python process 再跑 `.venv\Scripts\python.exe mcp_server\graph_mcp.py`（或雙擊該 `.vbs`）。**驗證跑著的版本：** 對 `http://127.0.0.1:$GRAPH_MCP_PORT/$GRAPH_MCP_TOKEN/mcp` 送 MCP `tools/list` 數工具數，**不要只看原始碼或測試**（那只證明 repo 對）。

---

## （歷史／fallback）雲端 egress 白名單

2026-07-24 首跑時 cloud 直連 `substack.com` 與 `www.sec.gov` 收到 proxy 403，實際是 claude.ai cloud environment 的 Network access allowlist，不是平台硬限制。現行 daily／weekly 已移回本機，以下只在日後重啟 cloud fallback 時適用。

- 白名單需含：`sec.gov`、`*.sec.gov`、`substack.com`、`*.substack.com`，並保留 default package-manager 清單
- **MCP connector 流量不受影響**（走 Anthropic 伺服器轉發）——證據：403 那次 MCP 工具仍可呼叫
- **`WebSearch` 不受影響**（是工具不是 egress）；受影響的只有直接抓取（`WebFetch`／`curl`／`urllib`）
- 設計取捨：維持 Custom 白名單較安全——本 routine 天職就是讀不受信任的網路內容且握有圖寫入能力，收斂 egress 可壓低 prompt-injection 外流面

---

## 本機音訊追源

官方 podcast／錄音沒有 transcript 時用 `scripts/transcribe_audio.py` 跑 `faster-whisper`；預設 CPU `small.en`，模型與完整逐字稿只存 ignored `library/private/`。ASR 只提供 timestamp locator，**不自行提高 evidence tier**；精確技術詞與 quote 仍須回聽核對。cloud fallback 不假設有此工具。
