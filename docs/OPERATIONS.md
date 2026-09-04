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

排程收尾只跑 `scripts/publish_daily_state.py`（窄 state publisher，只發布四個 leads state 檔：`pending_leads.json`＋`todo_pool.json`＋`event_watches.json`＋`hypotheses.json`——2026-09-02 由二擴四，impact review 結論見腳本 docstring；不得用 unattended 廣泛 Git 命令碰其他檔）。

**追源證據隨引用一起發布（2026-09-04）：** 同一筆提交會帶上**被那份 state 指名引用、
且確實存在**的 `library/raw/` 原文。集合由 state 推導（`_referenced_evidence`），
**不是把 `library/raw/` 加進 pathset**——state 沒提到的下載內容一律留在本機；
上限 20 份，超過 fail closed（`guard_evidence_volume`）。
事發：`audit invariants` 實測 3 筆 `trace_attempts_ref` 有 2 筆指向已不存在的檔案——
引用推上 origin、被引用的檔案留在本機，之後就沒了。
查證：`python -m audit invariants --only Orphans`。

**斷鏈要不要重新下載補檔，取決於來源可不可變：**

| 來源 | 可否重抓 | 理由 |
|---|---|---|
| SEC EDGAR `/Archives/{cik}/{accession}/` | ✅ 可 | accession number 定址，內容不可變——重抓得到的是**同一份文件**，不是代替品 |
| arXiv 版本號、DOI、其他內容定址 | ✅ 可 | 同上 |
| 新聞頁、公司官網、法說會頁面 | ❌ 不可 | 今天抓到的是**今天的版本**。補一個 `retrieved_at` 是今天的檔案去冒充當時的追源嘗試，等於偽造 provenance（INV-6） |

可重抓時**仍須核對**還原內容與 lead 既有的 `research_outcome` 相符，再宣稱復原
（2026-09-04 復原 `mu_8_k_20260826`／`mu_4_20260825` 即以人事異動三個人名逐字核對）。
不可重抓時不要硬補——讓 audit 一直紅著，直到有人明確判定「這筆證據確實遺失」。

### Runtime invariant audit

```powershell
python -m audit invariants              # 12 個跨層 invariant check
python -m audit invariants --only Orphans,Expiry
python -m audit invariants --json       # 機器可讀（findings 不截斷）
```

唯讀，不寫任何 authority。exit code 非 0 代表有 FAIL。
報表上 **SKIPPED 不是 PASS**，而且「檢查了 0 筆」會自動從 PASS 降級成 SKIPPED——
一個看了 0 筆資料的檢查，鑑別力與恆滅的閘門一樣是零（INV-5）。
Neo4j 沒開時相關 check 顯示 `unavailable`，**不會**因此變成綠燈。

### Writer lock（雙向互斥，2026-09-02）

同一 working tree 的排程與互動 session 靠 `library/leads/.writer_lock.json`
（gitignored，`engine_b/writer_lock.py`）互斥，取代原本只有互動側的時間窗單向避讓：

- **排程側**：`crons/harvest_leads.py` 一般 harvest 開跑 acquire `scheduled`（TTL 90 分，
  依 2026-09-02 量測 daily 中位 19 分／p90 30 分／最長 43 分取兩倍餘裕）；
  `scripts/publish_daily_state.py` 收尾 release（結果附 `writer_lock_released`）。
  互動 session 持鎖時 harvest exit 3＋stderr `writer_lock_held`，**整輪 Daily 中止**
  （見 `crons/daily_brief_prompt.md`），不得跳過 harvest 續跑會寫共用檔的命令。
- **互動側**：長時間寫入前 `python scripts/writer_guard.py acquire --minutes N --purpose "…"`，
  收尾 `release`；`check` 同時看排程時間窗與鎖（鎖補上時間窗防不了的延遲開跑——
  2026-08-29 排程 08:21 才收尾的那種）。互動手跑 harvest 時用
  `STOCKBOT_WRITER_OWNER=interactive` 表明身分，避免與自己持有的鎖互撞。
- **stale-tolerant**：鎖過期或損毀即可被接手（新鎖記 `superseded` 供稽核）；
  崩潰的 session 最多卡別人一個 TTL。不得手動拆別人的**未過期**鎖。
- **Sandbox impact review 結論（2026-09-02）：** 鎖檔是 repo 內一般檔案（workspace-write
  已涵蓋），無 identity／ACL／網路／credential 副作用；未新增 CLI 命令、未動
  `.codex/rules` 16 條 allowlist——acquire／release 嵌在既有 fixed entry
  （harvest／state publisher）內部。契約斷言見 `tests/test_writer_lock.py`。

**Routine 分工：**
- daily（`crons/daily_brief_prompt.md`）＝harvest ＋ ETL ＋ beta monitor ＋ triage ＋ today ＋ 統一 pq2 brief
- weekly（`crons/weekly_scan_prompt.md`，台北週日 04:00）＝topic discovery ＋ 完整本機健康審查 ＋ 唯讀 lifecycle，報告留 `docs/reports/`

兩者刻意錯開，且都不替使用者寫 thesis 結論、入圖或建立 live facts。

### 自主研究迴圈（2026-08-29 建立；互動 session 內由使用者觸發）

**Trigger：** 使用者說「跑自主研究迴圈」（單輪）或「/loop 自主研究」（連續、agent 自排程、
使用者隨時打斷）。**不設 cron、不進無人值守排程**——它與 daily／weekly 共用 working tree，
必須由互動 session 承載才能遵守 single-writer 契約。

**每輪固定形狀：** 從題源挑一題 → bounded research → 留 receipt（park／prepared RA／
Engine C 提案）→ 報告本輪產出與下一題。**所有 authority mutation 照常停在 pq2**：
迴圈只堆 packet，不 apply、不 complete、不改 lifecycle、不動 registry（onboard 亦打包成
`ra_admission` 等 `go`，見 `AGENTS.md`「Onboard 也走 pq2」）。

**題源優先序（確定性，不自創）：**
1. 使用者點名的題（含 decompose 積壓題——選題永遠是使用者的）
2. `trace-backlog` 觸發條件已命中的 parked lead
3. 瓶頸排序 `structural_rows` 前段的證據缺口（self_reported → 客戶端印證）
4. L8 不足公司的第三 origin 狩獵（`_check_source_diversity` < 3 者）
5. `coverage_gaps` 的 🔴 未知供應層
6. 缺五軸 assessment 的 cohort（如 `research_assessment_missing` 者）
7. `single_origin_report` 單源 claim 補強

**紅線：** ①台北 04:00（週日 weekly）與 06:30（daily）前後 30 分鐘內不動 working tree，
排程結束後先讀 `git status --short` 再續跑；②每輪必留 receipt，違反 = 該輪視為未發生。

**節奏（2026-08-30 使用者定案：做到底、gate 事後批次審）：** 迴圈**不因 gate 而閒置**——
撞到 authority gate 就鑄號堆進待審清單、立刻切下一題，直到題源枯竭或額度考量才停；
每輪收尾的建議摘要必須**彙總所有累積未審編號**成單一批次指令，供使用者一次事後審。
先前「積壓 ≥10 暫停產 packet」紅線由此取代。四個 authority gate 本身不放寬——
堆著等審不等於先斬後奏。

**成績單（L14——迴圈的存在必須讓這些數字動）：** prepared RA 數、L8 達 3/3 的公司數、
`substitutability` 覆蓋率（`query.bottleneck` caveat 行）、🔴 未知層帶供應商邊數、
單源 claim 數。連續多輪零產出＝題源枯竭，停迴圈並回報，不空轉。

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

### Private authority 備份（本機＋Google Drive 異地）

```powershell
python scripts/backup_private.py run             # 完整備份：SQLite 快照＋Neo4j 匯出＋files.zip＋Drive 上傳
python scripts/backup_private.py run --no-drive  # 只做本機備份
python scripts/backup_private.py verify-restore  # restore 到暫存＋checksum／integrity 驗證
python scripts/backup_private.py upload          # auth 修好後補上傳最新一份本機備份
python scripts/backup_private.py status          # 印出 last_backup.json
python scripts/backup_private.py auth            # 一次性 OAuth 瀏覽器授權（換 client 或 token 失效時重跑）
```

- **備份對象**是「今天重新取一次拿不回來」的三塊（L10 判準）：Decision Store、Engine C
  authority（`runtime_pointer.json` 指向）、Neo4j 全圖邏輯匯出；其餘 private 檔案打包
  `files.zip`。排除 `models/`（可重下載）、`lead_media/`、`gdrive_oauth/`（金鑰不出境）。
- **本機**留 `library/private/backups/`（rotation 3 份，manifest 全 checksum）；**Drive**
  留 `StockBotv2-backups` 資料夾（rotation 8 份，超出移垃圾桶 30 天可救）。
- **Drive 憑證是 OAuth user credentials**：`library/private/gdrive_oauth/client_secret.json`
  （Cloud Console `my-project-stockbot` 的 Desktop client）＋`token.json`（`auth` 產生）。
  ⚠ **service account 走不通，不要再試**——2026-08-29 實測 `files.create` 回 403
  「Service Accounts do not have storage quota」，兩條官方出路都要 Workspace。
- ⚠ **consent screen 停在 Testing 模式時 refresh token 7 天過期**；過期不會安靜壞掉，
  brief 首屏計數器會亮 `auth_expired` 🔴，重跑 `auth` 即恢復。發布 Production 後 token 長效。
- 「最後一次備份：N 天前」常駐在 daily brief 首屏（資料源 `backups/last_backup.json`）；
  從未備份、狀態檔壞掉、超過 7 天、Drive 未上傳都會 🔴 現形。

**`decision_review` 的 `go` 是全函數（2026-08-26 起）——你只要下 `go`，不必分辨它屬於哪一類。**
`engine_b.todo.advance_decision_review` 依實際狀態自動選路；下面三條是它內部做的事，
**列出來是為了讓輸出可讀，不是要你自己選**：

| 狀態 | `go` 實際做什麼 |
|---|---|
| 有 research work order | dispatch 回 pq1（`outcome=dispatched`） |
| 無 work order、無 `user_decision` blocker | 以原 intent reassess，下次 sync 自動結案（`outcome=reassessed`） |
| 無 work order、仍有 `user_decision` blocker | 先 reassess，再以 `assessment_gap:<cohort>` 排入 pq1 並印出研究範圍（`outcome=queued_assessment_gap`） |

⚠ **四個 authority gate 不受影響**：graph admission、Engine C ledger 寫入、thesis mutation、
live 資本仍各走 `complete-*` 與 exact 人工核准。`go` 只自動化「研究要不要開始」這件可逆的事。

⚠ `assessment_gap:` 的 dispatch **沒有** Decision Store work order（work order 只在
`coverage_pending` 時建立，而 `assessment_blockers` 是 sizing 階段才算出來的），
`checkpoint_decision_review` 會跳過 work-order transition，但 terminal 仍須 receipt。
慣例同 `source_trace_review` 的 `lead:<id>` ref。

歷史：改成全函數之前，`go` 只覆蓋第一種情況，其餘一律拒絕——實測 9 個 REVIEW 有 **4 個**
會死在這裡（本機 Codex 與 Claude Code 各自獨立撞到）。兩條內部路徑是：

- **coverage 有 blocker** → `dispatch <n>` 派回 pq1 做 bounded research，完成後 `work <n> --to ...` checkpoint。
- **coverage 無 blocker、REVIEW 來自凍結 context 過期** → 直接
  `python -m decision_lab reassess <cohort_id> --intent <原 intent>` 產生新 decision，**下一次 `todo sync`
  會自己把該編號結掉**，不需要任何 verb。

⚠ **`--intent` 沿用該 cohort 上一筆 decision 的值**，讓評估條件不因呼叫端習慣而跳動。
（原本還有一個更強的理由：對先前是 `paper` 的 cohort 跑 `--intent research` 會讓研究完整度
由 `READY` 退成 `DATA_NEEDED`，純由參數造成。**那個陷阱已於 2026-08-29 從源頭修掉**——
`sizing.py` 改用嚴重度分類，diagnostic 級的 `execution_intent_research_only` 不再有改判權。）
查證：
`select json_extract(payload_json,'$.request.execution_intent') from system_decisions where cohort_id=? order by rowid desc limit 1`。

### Leads
```powershell
& '.venv\Scripts\python.exe' crons\harvest_leads.py                 # 零 token；--dry-run 只印不寫
& '.venv\Scripts\python.exe' -m engine_b.cli drain                  # pq1 依 priority 的下一批
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go --tier N --reason ... --content-type <type> --decision-impact <impact> [--payment-direction <direction>]
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --no-go --tier N --reason ...
& '.venv\Scripts\python.exe' -m engine_b.cli classification-health # active 缺分類回 exit 2
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> <status> [--ref k=v]
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog          # parked 追源未果與 trigger
& '.venv\Scripts\python.exe' -m engine_b.cli related <lead_id>      # 共用具名標的的其他 lead
& '.venv\Scripts\python.exe' -m engine_b.cli harvest-health         # 各來源最新未恢復失敗
& '.venv\Scripts\python.exe' -m engine_b.cli onboard-candidates --min-leads 3
```

Leads authority 是 tracked `library/leads/pending_leads.json`；狀態機與 API 見 `engine_b/leads.py`。
PASS 的 `content_type`／`decision_impact`／`payment_direction` 只認
`config/lead_classification.json`。classification 與 triage 在同一次 atomic save 落盤；
trace requeue 沿用最近合法 receipt。`classification-health` 只檢查 active
`triaged_go`／`researching`／`action_prepared`；缺漏項會在 `drain` 顯示
`withheld_unclassified_lead` 且不參與排序，但不改 evidence tier、graph admission 或任何人工 gate。

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

### Event Watch（等待事件統一 registry，2026-08-31）

所有「以後要回來看」的等待條件住 `library/leads/event_watches.json`
（模組 `engine_b/event_watch.py`，設計見
`docs/brainstorms/2026-08-31-event-watch-module-requirements.md`）。
**2026-08-31（[321]）起追源 backlog 也在裡面**——等待只有一個入口，三種去處：
待辦編號（`wake_pq2`）、假設對照（`hypothesis_ref`）、追源線索排回 pq1（`wake_lead`）。

追源線索在 `advance(..., "parked")` 當下由 `ensure_trace_watch()` 自動建 watch 並取得
到期日（預設 120 天＝一個財報週期＋緩衝，`config/event_watch.json` 的 `trace_ttl_days`
可調）。查「被動層救不了、需要人動手」的：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog --needs-attention
```

`wake_state` 四種：`watching`（有事件在等）／`stalled`（具名標的已全部觸發過一輪，
靠到期或主動輪詢救）／`expired`（到期，該決定續等或放棄）／`unwatched`（沒有任何
機制在等它，唯一真正的黑洞）。

⚠ **測試必須隔離 registry。** `leads.advance(..., "parked")` 會寫真實 registry，
而寫錯不會報錯、只會靜默污染（實作當天就先中了一次：用假 lead 觸發了 3 個真 watch）。
`tests/conftest.py` 有 autouse fixture 把 `WATCHES_PATH` 導向暫存檔；新增測試不要繞過它。

```powershell
& '.venv\Scripts\python.exe' -m engine_b.event_watch list        # 全部 watch＋計數器
& '.venv\Scripts\python.exe' -m engine_b.event_watch sweep       # 本輪 T2 該查的 K 個（agent 拿 query hint 去 WebSearch）
& '.venv\Scripts\python.exe' -m engine_b.event_watch sweep --mark-checked   # 查完標記
& '.venv\Scripts\python.exe' -m engine_b.event_watch add --kind entity_filing_signal --wake-pq2 <N> --expires YYYY-MM-DD --entities "co:x,TICK" [--poll --query-hint "..."]
```

- T0（新 tier-1 PASS lead 比對具名標的）與 T1（until 日期）在每次 `todo sync` 自動檢查；
  fired watch 把 pq2 項的 waiting_on 翻回「等你決定」＋`watch_wake` 稽核，**不自動 go**。
- T2 力度旋鈕在 `config/event_watch.json`（`sweep_budget_per_run` 調 0＝退回純被動，
  系統照常運作）。互動 session／自主迴圈可直接 sweep。
- **無人值守 sweep 已於 2026-08-31 完成 sandbox impact review 並放行**：
  ①命令 surface：`python -m engine_b.event_watch sweep [--mark-checked]`——讀
  `config/event_watch.json`＋`library/leads/event_watches.json`、寫後者（同目錄
  tempfile 原子替換）；無網路、無憑證、無 identity/ACL、無 private authority、無 `.git`
  ——**完全在 workspace-write sandbox 內，不需（也不得新增）outside-sandbox rule**；
  ②WebSearch 由 daily agent 既有能力執行（同事件監控先例），每輪 ≤`sweep_budget_per_run`
  次、每 watch 一次；③命中只 register lead 交下輪 triage，不直接喚醒 pq2、不寫 authority；
  ④contract test：`tests/test_codex_daily_permissions.py::test_event_watch_sweep_is_in_sandbox_not_escalated`
  鎖「rules 不得出現 event_watch」與「daily prompt 必帶 sweep 步驟與 cap」；
  ⑤smoke：以 PowerShell exact 命令實跑 sweep＋`--mark-checked` 驗證 `last_checked` 落檔。
- 給 pq2 項設等待時：能結構化的一律建 watch（散文 `--trigger` 只給人讀）；
  `expires` 必填，過期自動歸檔留稽核。

### 截圖假設層（hypothesis overlay，2026-08-31）

追不到原檔的 lead（B/C 類，見截圖 brainstorm）不再只是 park——結構化成假設，
物理隔離於圖外（`library/leads/hypotheses.json`，模組 `engine_b/hypotheses.py`）：

```powershell
& '.venv\Scripts\python.exe' -m engine_b.hypotheses list
& '.venv\Scripts\python.exe' -m engine_b.hypotheses add <payload.json>    # 欄位見 add_hypothesis docstring
& '.venv\Scripts\python.exe' -m engine_b.hypotheses verify <hy_id> --outcome hit|miss --receipt "doc:<一手 doc_id>"
& '.venv\Scripts\python.exe' -m query.bottleneck --what-if               # 全部 active 假設疊加，輸出純結構排序 diff
& '.venv\Scripts\python.exe' -m query.bottleneck --what-if hy_0001_...   # 指定假設
```

- **唯一消費入口是 `--what-if`**：只比純結構排序（「若為真」問的是真值不是證據）；
  名次有動＝值得追平行證據（B1 免費一手／B2 fact-check watch），沒動＝安心 park。
- 假設**永不**進 evidence 分級、L8 計數、assessment refs、預設排序；入圖唯一路徑仍是
  一手 admission。`verify --outcome` 同步記帳號級 credibility（`source_credibility`
  ledger）——匿名帳號連續命中會浮出來，連續失敗自動降權。
- watch 可用 `--hypothesis-ref` 級欄位鏈假設（fact_verification 喚醒時 woken_by 自帶
  fact＋hypothesis_ref，醒來直接對照，不必回頭翻）。

### Addendum extraction 的 edge id 陷阱（2026-08-30 實測）

**Addendum（重用既有 doc_id 的補充 extraction）裡的 edge id 絕不可重用 `e1`、`e2` 這類原檔已用的 id。**
EdgeAssertion 的全域 id＝`doc_id + edge id`——同名會 MERGE 覆寫原檔的 assertion，讓原本的
canonical 邊失去 assertion backing，`loader.edge_resolution project` 會以
`relationships_without_assertions` fail closed（2026-08-30 一次撞出 21 條 orphan）。

- 規則：addendum 的 edge id 用檔案唯一前綴（如 `cov3_1`、`sole1`）。
- 修復程序（如已撞上）：①把 addendum 的 edge id 改唯一；②重載**原始** extraction 檔還原被覆寫的
  assertion；③重載修正後的 addendum；④重跑 `python -m loader.edge_resolution project`。
- 同理 source id：addendum 引用原檔 source（如 `..._s1`）是刻意共用、安全；但**新增** quote 時
  source id 也要避開原檔已用的編號。

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

Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，因此 project permission profile 不作 Daily authority。唯一權限來源是 `.codex/rules/stockbot-automations.rules` 的十六個窄 fixed entry：harvest、Engine C ETL、Alpha purity snapshot、SEC EDGAR pq1 fetch、MOPS 台股 pq1 fetch、Beta snapshot、pending priority list、pq1 drain、catalyst watch、Alpha outcome snapshot、Research Action prepare、decision today、todo sync、已核准 work order checkpoint、state publisher、Discord publisher，第一次呼叫就用 `require_escalated` 命中各自 exact outside-sandbox rule；不先失敗再升權重補跑，也不放行任意 Python、PowerShell、Git 或 working tree。`engine_b.todo work` 只可推進已有 `dispatch_ref` 的 USER-GO work order，不授權 dispatch／resolve／reassess。修改 rules 後須讓 Codex 重新載入設定；但在要求重啟前先確認 exact rule **確實存在**，因為重啟不能修復漏寫的 rule。

**Triage classification surface impact（2026-08-27）：** `engine_b.cli triage` 新增的分類參數只會
atomic 寫 tracked `library/leads/pending_leads.json`；`classification-health` 只讀同檔並以 exit 2
回報 active 缺口；互動 migration `scripts/backfill_lead_classification.py --from-json ... --apply`
也只寫同一 tracked authority。三者都不讀 credential／private authority、不呼叫 OS security API、
不連網、不碰 `.git`，所以留在 `workspace-write` sandbox，**不新增 unattended rule**。既有
`engine_b.cli drain` 仍只用原 fixed entry 讀 Decision／Sheet／Neo4j context；新增的
`withheld_unclassified_lead` 是本機 validation，沒有新增 capability 或副作用。

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

## 非美股 filing 抓取（台股 MOPS／日股 TDnet）

**台股：`fetchers/mops.py`**（互動式入口，**未加入任何 unattended routine**）。

```bash
python -m fetchers.mops --co-id 3081 --list                 # 先看有哪些文件
python -m fetchers.mops --co-id 3081 --kind annual_report   # 抓年報（預設只取最新修訂）
python -m fetchers.mops --co-id 4971 --kind annual_report --all-revisions
```

輸出與 `edgar.py` 一致：`library/raw/{doc_id}.txt` ＋ `.meta.json`。
年報「營運概況」含最近二年度占進（銷）貨總額 10% 以上之客戶——台股客戶集中度的一手來源。

**⚠ 不要改抓公司 IR 網站。** 多數台廠年報 PDF 連結是動態載入，靜態抓取只拿得到零散附件
（2026-08-28 實測聯亞只取得「前十大股東關係表」，一度被誤判成「可抽文字為 0」）。

fetcher 已封裝的四個坑，自己刻之前先讀 `fetchers/mops.py` 的 docstring：
① 兩段式下載（`step=9` 回的是 HTML，裡面才有帶時戳的一次性 PDF 路徑；直接猜
`/pdf/{filename}` 一律 404）；② 列表頁是 **big5**，不設 encoding 會拿到亂碼；
③ `--year` 是**民國查詢年度**而非資料年度，查 115 回的是 114 年度年報；
④ 同年度可能有多份修訂（原始版 F04 ／股東會後修訂本 F11），共用 doc_id 會**靜默覆蓋**，
預設只取最新並印出略過訊息。

**日股：** 有価証券報告書走 EDINET，受注残高與決算數字走決算短信（TDnet）。
⚠ EDINET API v2 需 subscription key（未申請）；2026-08-28 實測改抓 TDnet 決算短信正本
即取得所需資料。尚未封裝成 fetcher。

**已納入 Daily（2026-08-28 完成 sandbox impact review）。** `fetchers\mops.py` 是第十六個
fixed entry，與 `edgar.py` 同構：無憑證、不碰 Windows identity／ACL、不寫 private authority、
不觸 `.git`，只把公開文件下載到 `library/raw/`。Daily pq1 遇到台股標的時直接以
`require_escalated` 命中該 exact rule。

**⚠ `fetchers/` 不是整包放行。** 只有 `edgar.py` 與 `mops.py` 兩支公開文件下載器在列；
同目錄的 `gsheets.py` 使用 Google service account 憑證，屬 credential-bearing surface，
刻意排除。`tests/test_codex_daily_permissions.py::test_fetchers_directory_is_not_broadly_allowed`
會擋下把整個目錄或 `-m fetchers` 放行的寫法。要動 `gsheets.py` 必須另做一次 impact review。

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
