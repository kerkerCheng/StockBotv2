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

### Luna reviewer（手動 opt-in）

預設不啟動。每次要用時在指令前加 `$luna-reviewer` 或 `Luna reviewer：`；只對該次指令有效，不會黏到下一個 session／下一個請求。

```text
Luna reviewer：pq1 5
$luna-reviewer pq1 5
Luna reviewer：alpha NBIS，先做財務五項與反證蒐集
Luna reviewer：repo audit，檢查 queue schema 與測試失敗
Luna reviewer：停止
```

入口會啟動既有 `.codex/agents/luna-operator.toml`：Luna 唯讀批量執行，主代理逐項 review 並保留唯一寫入與所有人工 gate。若 Luna runtime 不可用，不自動換成較昂貴 subagent。完整契約見 `skills/luna-reviewer/SKILL.md`。

### 待辦池（統一 pq2）
```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync          # 同步後列出（＝「待辦事項統整」）
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb go|drop|pending [--reason ...] [--receipt ...]
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb pending --until 2026-08-27 --trigger "Q2 財報"
& '.venv\Scripts\python.exe' -m engine_b.todo dispatch <n>  # decision_review → pq1 job
& '.venv\Scripts\python.exe' -m engine_b.todo work <n> --to researching|completed|parked --receipt ...
& '.venv\Scripts\python.exe' -m engine_b.todo complete-ra <n> --digest <sha256> [--company-id ...]
& '.venv\Scripts\python.exe' -m engine_b.todo complete-observation <n>       # Engine C 人工觀測寫入
& '.venv\Scripts\python.exe' -m engine_b.todo complete-thesis-mutation <n>   # thesis lifecycle 變更
```

`pending` 帶 `--until`／`--trigger` 會歸入「等事件」區，觸發前不佔決策注意力。分類判準見 `config/decision_blockers.json` 的 `resolution_mode`。

**⚠ `decision_review` 有兩種成因，處置完全不同（2026-08-26 實測撞到；本機 Codex 與 Claude Code 各自獨立
命中同一處）。** 舊 hint 一律寫「核准 bounded gap research」，把「REVIEW 來自 context 過期」誤呈現成
「存在可 dispatch 的研究缺口」；使用者照著下 `go`，`dispatch` 拒絕（沒有 work order）、`resolve --verb go`
也拒絕（decision_review 不得 bare go），看起來像死結。**hint 已於同日改為逐項動態判定**
（`engine_b.todo._dispatchable_cohorts` 查該 cohort 有無 research work order），
`todo list`／`sync` 會在每個編號下方直接印出該走哪條路。兩條路是：

- **coverage 有 blocker** → `dispatch <n>` 派回 pq1 做 bounded research，完成後 `work <n> --to ...` checkpoint。
- **coverage 無 blocker、REVIEW 來自凍結 context 過期** → 直接
  `python -m decision_lab reassess <cohort_id> --intent <原 intent>` 產生新 decision，**下一次 `todo sync`
  會自己把該編號結掉**，不需要任何 verb。

⚠ **`--intent` 必須沿用該 cohort 上一筆 decision 的值**，不可套用別處的習慣。實測：對一個先前是 `paper`
的 cohort 跑 `--intent research`，`paper_status` 會由 `ELIGIBLE` 退成 `DATA_NEEDED`——那不是資料變壞，
是 `execution_intent_research_only` 這個 paper blocker，純粹由參數造成。查證：
`select json_extract(payload_json,'$.request.execution_intent') from system_decisions where cohort_id=? order by rowid desc limit 1`。

### Leads
```powershell
& '.venv\Scripts\python.exe' crons\harvest_leads.py                 # 零 token；--dry-run 只印不寫
& '.venv\Scripts\python.exe' -m engine_b.cli drain                  # pq1 依 priority 的下一批
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go|--no-go --tier N --reason ...
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> <status> [--ref k=v]
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog          # parked 追源未果與 trigger
& '.venv\Scripts\python.exe' -m engine_b.cli related <lead_id>      # 共用具名標的的其他 lead
& '.venv\Scripts\python.exe' -m engine_b.cli harvest-health         # 各來源最新未恢復失敗
& '.venv\Scripts\python.exe' -m engine_b.cli onboard-candidates --min-leads 3
```

Leads authority 是 tracked `library/leads/pending_leads.json`；狀態機與 API 見 `engine_b/leads.py`。

`drain` 每輪上限的唯一權威是 `config/daily_routine.json` 的 `pq1.drain_limit_per_run`
（`engine_b/routine_config.py` 是唯一 loader）。**文件裡出現的任何 slot 數字都是當時快照**，
查證：`python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`。

`trace_status` 是封閉字彙，唯一權威是 `config/lead_trace_status.json`；
`annotate`／`advance` 拒絕未登記值與已淘汰同義詞。**`terminal=true` 的值會離開
`trace-backlog`**，所以寫錯不是命名問題而是行為問題——已完成的 lead 會永遠掛著，
或真的在等的 lead 會消失。

`onboard-candidates` 列出**已通過 triage 的 lead 中點名、但 registry 沒有的標的**，
補上 pq2 六個 collector 都不負責的缺口（已有 cohort 但缺 ticker 的走
`decision_lab.brief.identity_registration_pending`，完全沒登記的先前無任何浮現路徑）。
cashtag 由 `entities.py` 確定性抽取；公司名寫成純文字時 regex 抓不到，
由研究者在 `onboard_candidate_names` 標註（L15：語意由 LLM 解析，registry 判權限）。
**它只回答「誰一直出現卻不在圖裡」，不回答該不該 onboard**——後者仍走
`skills/company-onboard` 並由使用者決定。

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
# ⚠ set_manual_field 只建立待核准提案，不直接寫 ledger；核准後走 todo complete-observation
& '.venv\Scripts\python.exe' -m engine_c.set_manual_field --list <T>     # 列出該標的已填欄位
```

⚠ **寫入含 `$` 的金額字串不要經 PowerShell 傳參**——`US$71.3M` 會被當變數前綴展開成 `US.3M`，在 append-only ledger 造成需 supersede 才能更正的損毀。用 Python 或 heredoc。

### Beta 快照
```powershell
& '.venv\Scripts\python.exe' scripts\daily_beta_snapshot.py --format markdown --risk-view changes
```
輸出明標 `policy_mode=paper_observation`、`capital_scope=shared_cash_pool`；不建立 choice／fill、不下單、不寫 Sheet、不把 undrawn loan 算資本。

### 記錄成交（手動下單後）

```powershell
& '.venv\Scripts\python.exe' scripts\record_trade.py --symbol QQQ --side buy `
    --shares 10 --price 687.79 --executed-at 2026-07-31T13:04:53-04:00 `
    --broker IB --account-ref "U****1599" --note "<券商通知逐字內容>"
```

預設 **dry-run**，只印出將變更的三格（`shares`／`avg_cost`／現金）。確認後：

- `--apply`：實際寫入 Sheet 並記錄事件
- `--log-only`：**Sheet 已由你手動更新過**時使用，只記事件不碰 Sheet。
  腳本無法自行判斷 Sheet 是否已更新，重複 `--apply` 會把同一筆算兩次。

寫入的三個不變量（有測試守住）：按**欄名**定位（你調欄序不會寫錯欄）、
**只寫指定儲存格**（不會蓋掉你手填的欄位）、**寫前比對現值**（不符即整批中止）。
市值與 NAV 不由本腳本改動。

事件紀錄在 tracked `library/trades/trade_log.jsonl`（append-only）。
它是「發生了什麼」的稽核軌跡，**不是持股真相**——後者永遠只有 Sheet。

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
| Daily Brief outbound Discord Forum（**只放本機**） | `NOTIFY_DISCORD_WEBHOOK_URL`、可選 `NOTIFY_DISCORD_TAG_USER_ID`、`NOTIFY_CHANNEL_ALIAS`、`NOTIFY_CONTENT_CLASS`、`NOTIFY_MAX_ATTEMPTS`、`NOTIFY_TIMEOUT_SECONDS` |

Sheet 的 credential scope 分兩種：日常全部走 `SCOPES`（`spreadsheets.readonly`），
只有 `scripts/record_trade.py --apply` 會走 `WRITE_SCOPES`（`spreadsheets`）。
這個分離讓 daily brief、beta snapshot、Engine D 等流程不會持有可寫 token。

Sheet adapter 的標準輸出是 `ticker`、`shares`、`currency`、`market_value_base`、`nav_base`、`base_currency`；可直接提供完整標準欄位，或以逐列 mark-to-market `market_usd` 安全正規化成 USD NAV。**禁止退回 `avg_cost` 或 `market_twd` 猜值。**

Price／FX 預設 yfinance（無 API key）。非同幣 FX 缺失或方向不符一律 fail closed。

Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，因此 project permission profile 不作 Daily authority。唯一權限來源是 `.codex/rules/stockbot-automations.rules` 的十五個窄 fixed entry：harvest、Engine C ETL、Alpha purity snapshot、SEC EDGAR pq1 fetch、Beta snapshot、pending priority list、pq1 drain、catalyst watch、Alpha outcome snapshot、Research Action prepare、decision today、todo sync、已核准 work order checkpoint、state publisher、Discord publisher，第一次呼叫就用 `require_escalated` 命中各自 exact outside-sandbox rule；不先失敗再升權重補跑，也不放行任意 Python、PowerShell、Git 或 working tree。`engine_b.todo work` 只可推進已有 `dispatch_ref` 的 USER-GO work order，不授權 dispatch／resolve／reassess。修改 rules 後須讓 Codex 重新載入設定；但在要求重啟前先確認 exact rule **確實存在**，因為重啟不能修復漏寫的 rule。

### Sandbox／private authority 排錯

`workspace-write` 只保證普通 workspace path 操作；它不自動授予 Windows ACL inspection、credential、network、child process 或 `.git` 能力。`library/private/` 是 repo 內的 ignored enclave，但 `storage.relational.initialize_private_root()`／`validate_private_destination()` 會先執行 owner-only 驗證，因此開啟 Decision Store／Engine C／notification outbox 仍可能跨 capability boundary。

遇到 `PrivateStorageVerificationUnavailable`／`access_blocked` 時依序檢查：

1. 記下完整 interpreter、module／script、subcommand 與參數前綴；不可只寫「Python 被擋」。
2. 用 `rg` 在 `.codex/rules/`、canonical skill 與 cron prompt 查同一個 exact command；skill 有命令而 rules 沒有，就是 integration gap。
3. 區分 `verification.status=unavailable` 與 `invalid`：前者先查 sandbox capability，後者才代表 ACL 判準沒通過。
4. 新增或改名 unattended command 時，同一 commit 更新 rule、skill／prompt、本文與 permission test；測試要同時斷言相鄰高權限動詞仍未放行。
5. 用 scheduled task 相同的 `workspace-write`＋首次 `require_escalated` exact command 做 smoke test。只有 rule 已存在但載入版本仍舊時才需要重啟。

Research Action prepare 的固定入口是 `.venv\Scripts\python.exe scripts\prepare_research_action.py --action-file library\leads\action_drafts\<lead>.json`。draft 目錄已 ignore；CLI 只接受該目錄下的 JSON，重跑 server-side validation 並寫 private staging，不 apply、不寫 Neo4j。`engine_b.cli list --by-priority` 與 `drain` 在 default store 讀不到 Decision／Sheet／Neo4j context 時 exit 2，不再把持股 silently 降成空集合。

Daily Brief 通知由 `.venv\Scripts\python.exe scripts\publish_daily_brief.py --brief-file <private-brief.md> --summary "..."` 發送；
Codex 與本機 Claude Code 共用同一支 publisher。它只接受 stdin／私有 brief 檔，不提供 Discord inbound
command surface。Forum publisher 每日建立一個討論串，`library/private/notifications/outbox.db` 保存 digest/channel 去重、thread ID 與 delivery receipt；
通知錯誤是 best-effort，不得阻斷 routine。Windows PowerShell 5.1 的 `$OutputEncoding` 預設是 ASCII，含中文的
brief 不可直接用 `Get-Content | --stdin` 管線傳送；`--brief-file` 會由 Python 直接以 UTF-8 讀取。Webhook secret 不得輸出或進 Git。

---

## X／EDGAR harvest 細節

**X API 是主來源**（`crons/harvest_leads.py` 的 `harvest_x`）。曾經的「SubStack RSS 就夠」前提已被推翻：該 feed 至今只有 1 篇 2026-05-19 舊文，但本人在 X 極度活躍（[@aleabitoreddit](https://x.com/aleabitoreddit)，顯示名 Serenity）。substack feed 已於 2026-07-25 移除。

**成本模型（2026-02 起 pay-per-use）：** 約 $0.005/則、按回傳貼文數計費、無月費下限。控制組合：`since_id` 增量、`exclude=replies,retweets`、`max_posts_per_run` 單輪硬上限、`max_results` page size、`user_id` 快取。實測首抓 23 則 $0.115；立即重跑 0 則 $0.000。日常估 $1–2/月。

**內容保存：** tracked lead 存單行可搜尋全文 `title` 與保留換行的 `raw_text`；API 同回應請求 `note_tweet` 與 `attachments.media_keys` expansion，media metadata 隨 lead 保存，預覽快取至 ignored `library/private/lead_media/`。harvest 不做 OCR。舊 lead 可用 `--refresh-x-lead <lead_id>` 精準回填，不做全量昂貴 backfill。

**歷史回補：** `--backfill-x-handle` 以 RFC3339 time window ＋ pagination token ＋ `max_posts` 成本硬上限；可納入 replies，且**不得推進 daily `since_id`**。

**⚠ 只在本機跑。** 任何 cloud fallback 都不得抓 X，避免重複計費與擴大計費憑證 blast radius。

**Daily 分頁與成本上限：** `max_results` 是 page size（預設 25），`max_posts_per_run` 是單輪成本硬上限（預設 200）。超過單輪上限時保存 `x_pagination_*` checkpoint，下次 scheduled run 從相同 frozen `since_id`＋pagination token 續抓；最後一頁完成前不推進 durable `since_id`，避免長時間未跑後永久漏掉中間批次。

**來源存取防漏：** harvest 第一次呼叫即走 fixed-entry exact rule。rule 未匹配、升權限被拒或 sandbox／proxy 回 `access_blocked` 時，保存 bounded `failure_class` 並 fail closed；不得用更寬 rule 或手動 replay 事後補跑。權限正確後的暫時性 transport error，只允許命令內既有 bounded、idempotent retry 作最後一步，不重跑整個 Daily／已 checkpoint 工作；用盡後保留 failure。`blocked` 永遠不等於「零筆新資料」或 `no_result`，後續新一輪同來源成功才算 recovered。

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
