# StockBotv2 — 操作手冊 (Operations Runbook)

> 這裡是「怎麼跑」：指令、環境變數、排程流程、已知操作陷阱。
> 「為什麼這樣做」與判準在 [`AGENTS.md`](../AGENTS.md)；交付歷史與待辦方向在 [`ROADMAP.md`](ROADMAP.md)。
> **實際操作前讀本檔；只做判斷或研究時不必載入。**

所有 Python 命令一律使用 repo venv：`& '.venv\Scripts\python.exe' ...`

---

## 每日操作

**2026-09-24（Phase 1 Step 1.2a）起，無人值守只有一條路：Windows 工作 `StockBotv2-Daily`。**
它取代三個東西：Codex daily automation（抓資料、機械段、materialize）、`StockBotv2-Heartbeat`（07:00 心跳）、
`StockBotv2-FxSync`（06:55 FX 同步）——舊兩個工作在 1.2a 只**停用**，2026-09-25 第一次排程觸發成功（`Last Result 0`、執行紀錄 25 步齊全）後
由 1.2b **刪除**，舊入口 `crons/heartbeat_task.py` 同步刪除。研究仍只在互動 session。

```
Daily   Windows 工作 StockBotv2-Daily（時間只住 config/daily_routine.json 的 schedule，現為 05:30）
          → crons/daily_task.py：固定步驟清單 DAILY_STEPS（程式寫死；LLM 不決定跑什麼）
             ① harvest → ①b–①e 外部雷達（準備 → claude -p 只開 WebSearch 提議 → 保險檢查 → 程式驗證後寫 secondary lead；
                            radar.enabled 控制；Phase 7 Step 7.0f）
             → ② Engine C ETL → ③ FX 同步 → ④ beta 快照 → ⑤ outcome
             → ⑥ triage 批次 → ⑦a triage 提議（claude -p 零工具；Step 1.3 接上）→ ⑧ 保險檢查
             → ⑦b triage 套用（程式驗證後寫入；Step 1.3 接上）→ classification-health
             → ⑨ consume-fired → ⑩ todo sync → ⑪ standing-go → ⑫ XBRL 基期補值 → ⑬ materialize
             → ⑭ 健康審查（--json）→ ⑮ invariants（--json）→ ⑯ 本機備份 → ⑰ 收尾（驗 state、釋放鎖）
             → ⑱ 心跳（零 LLM、零網路）→ ⑲ Discord（唯一發送者）
研究    只在互動 session 的 research-drain（daily 的 drain_limit_per_run = 0）
```

查證：
```powershell
schtasks /Query /TN StockBotv2-Daily /FO LIST /V                  # Status=Ready、Next Run Time=明天 05:30
& '.venv\Scripts\python.exe' crons\daily_task.py --dry-run          # 步驟清單、config 時間、timeout 加總
& '.venv\Scripts\python.exe' scripts\register_daily_task.py         # dry-run：與現行註冊值的差異應為「無」
Get-Content library\private\heartbeat\daily_run_<YYYY-MM-DD>.json    # 每步 status／exit／秒數／stderr 末段
& '.venv\Scripts\python.exe' -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"   # 0
```

### Daily（`crons/daily_task.py`）——唯一的無人值守排程

**改時間的唯一做法：** 改 `config/daily_routine.json` 的 `schedule`（`daily_local_time`／`execution_time_limit_minutes`）
→ `python scripts\register_daily_task.py`（dry-run 看差異）→ `--apply`。**不要在工作排程器 UI 裡改**——daily 每次開跑都拿
實際註冊值比對 config，不一致時心跳段 1 亮 ⚠ 並印這條命令（2026-09-12 事故：兩個 SSOT 沒有機械連結，只改了排程器）。

**失敗長相**（心跳一律照發，除了保險檢查那一列）：

| 情況 | 會看到什麼 |
|---|---|
| 某一步失敗／timeout | 段 1「daily（run xxxxxxxx）：N 步完成｜**失敗 k**：…」；其餘步驟照跑 |
| 進步驟迴圈前就失敗（config 壞掉等） | 段 1「⚠ daily 進步驟迴圈前就失敗：…——今天只組了心跳」 |
| 互動 session 持有 writer lock | 段 1「⚠ 沒拿到 writer lock」，所有寫入步驟跳過 |
| 排程設定與 config 不一致／讀不到 | 段 1「⚠ 排程設定與 config 不一致」＋修正命令；讀不到印 unknown |
| harvest 超過 `harvest_stale_hours` 沒跑 | 段 1 ⚠；段 3「harvest N 天沒跑——0 不代表沒有新文件」 |
| ⑯ Drive 上傳失敗（`auth_expired`／`delivery_failed`） | 段 1「失敗 1：16_backup」＋備份行 ⚠「Drive <狀態>（最後成功上傳：N 天前）」；本機那份照留、⑯b 照驗。修好後 `python scripts\backup_private.py upload` 補傳（token 過期先 `auth`） |
| T2 輪詢超過 `min_recheck_days` 沒人跑、而有該查的 | 段 3「⚠ T2 輪詢：…最後一次 <日期>（N 天前）」＋摘要行「T2 輪詢 N 天沒跑」；sweep 沒有排程，在互動 session 跑 `python -m engine_b.event_watch sweep` |
| 開跑時工作區不乾淨 | 段 1 ⚠ 列出路徑（照跑） |
| 保險檢查觸發（LLM 步驟前後指紋變了） | **沒有心跳也沒有 Discord**（心跳會 import 被改的檔）；開 session 時 `crons/routine_hint.py` 第一句說出來 |
| daily 根本沒跑 | 開 session 時 `crons/routine_hint.py`：「今天沒有 daily 執行紀錄」 |

手動跑（這就是正常的每日動作，**會真的發一則 Discord**；⚠ 當下不得持有 interactive 鎖，否則寫入步驟全跳過）：
```powershell
& '.venv\Scripts\python.exe' crons\daily_task.py
schtasks /Run /TN StockBotv2-Daily       # 走真正的排程路徑
Get-Content library\private\heartbeat\daily_task.log -Tail 30
```

**回滾**：LLM 步驟出事 → `config/daily_routine.json` 的 `llm.executor` 改 `none`（triage 與預篩一起停，其餘照跑）。
舊兩個工作已於 2026-09-25（1.2b）刪除，「重新啟用舊工作」這條退路不存在了；真要退回舊形狀，註冊範本在
`library/private/heartbeat/legacy_tasks/*.xml`（`schtasks /Create /TN <名稱> /XML <檔>`），而舊心跳入口要先從 git 還原
`crons/heartbeat_task.py`（1.2b 之前的任一 commit）。

⚠ **`LogonType Interactive`＝只在使用者已登入時執行。** 換成「不論是否登入都執行」要存密碼，會在機器上多一份憑證——刻意不做。
`StartWhenAvailable`：05:30 電腦沒開，開機後補跑。註冊時觸發起點取「下一次」而不是今天（今天已過的時間會被當成錯過的一次、當場補跑）。

### 心跳（`crons/heartbeat.py`）——零 LLM、零網路、固定五段

```powershell
& '.venv\Scripts\python.exe' crons\heartbeat.py                    # Markdown 到 stdout
& '.venv\Scripts\python.exe' crons\heartbeat.py --format json      # 機器可讀
& '.venv\Scripts\python.exe' crons\heartbeat.py --out .\hb.md       # 寫 UTF-8 檔，交給既有 publisher
```

它**只讀**本機 authority（`pending_leads.json`／`todo_pool.json`／`event_watches.json`／
`thesis/lifecycle.json`）、`webapp` 已 materialize 的 state artifact 與 daily 的執行紀錄，**不寫任何 authority、不連外、
不呼叫任何模型、不開 subprocess**（排程比對由 daily 查、心跳只讀結果）。無人值守時由 daily 的 ⑱ 產檔、⑲ 發送；
手動要送到 Discord 仍走既有的 publisher（心跳自己不發送，也不新增任何 outbound surface）：

```powershell
& '.venv\Scripts\python.exe' crons\heartbeat.py --out <private.md>
& '.venv\Scripts\python.exe' scripts\publish_daily_brief.py --brief-file <private.md> --summary "心跳"
```

⚠ **不要用管線把心跳的輸出餵給 publisher**：Windows PowerShell 5.1 的 `$OutputEncoding` 預設 ASCII，
中文會在 Python 讀到之前就被換掉——這就是 `--out` 存在的理由（既有坑，見本檔「Daily Brief 通知」節）。

**失敗模式刻意與眾不同：心跳永遠 exit 0。** 任何一段的資料源壞掉，那一段印出降級行並宣告
`absence_kind`（封閉字彙來自 `alpha/absence.py`），其餘四段照印。
查證：`python -m pytest tests/test_heartbeat.py -q`（其中
`test_every_source_broken_still_renders_five_sections` 就是這條契約本身）。

~~無人值守進入點 `crons/heartbeat_task.py`＋工作 `StockBotv2-Heartbeat`（07:00）~~——2026-09-24 Phase 1 Step 1.2a 起由
`StockBotv2-Daily` 的 ⑱⑲ 取代（1.2a 停用、2026-09-25 1.2b 刪除）；它們的理由（LLM 失敗心跳照發、永遠 exit 0、Python 不用 `.cmd`、
發送走 subprocess）搬進 `crons/daily_task.py` 的 docstring，守它們的測試改主詞搬進 `tests/test_daily_task.py`「無人值守入口」節。

### Sandbox impact review 結論（2026-10-06：daily ⑯ 含 Drive 異地、⑯b 還原驗證；心跳備份行三格與 T2 輪詢行）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | ⑯ 的 argv 由 `scripts/backup_private.py run --no-drive` 改成 `run`（**同一支既有入口拿掉一個旗標，不是新入口**）。新連網主機：`oauth2.googleapis.com`（refresh token 換 access token）、`www.googleapis.com`（Drive v3 `files.list`／`files.create`／`files.update` 移垃圾桶）。憑證是既有的 OAuth user credential `library/private/gdrive_oauth/token.json`——scope 只有 `drive.file`（只看得到本 app 建的檔）；10-06 實測 09-10 發的 refresh token 仍可用，consent screen 早已不是 Testing。上傳成功後寫回同一個 token 檔（access token 更新）。上傳內容＝當天那份本機備份的 zip（10-06 實測 79 MB、15 秒；`gdrive_oauth/` 不進任何備份），雲端只動 `StockBotv2-backups` 資料夾裡自己命名前綴的檔，留 8 份、超出移垃圾桶（30 天可救）。⑯b `verify-restore`：新的 daily 步、既有入口，純本機（10-06 實測 3 秒），寫 `library/private/backups_verify_tmp/`（驗完刪）與 `backups/last_backup.json`。不寫 tracked 檔、不碰 `.git`、不寫任何 authority。心跳仍零網路，只多讀 `config/event_watch.json` 與 watch registry（T2 行）。 |
| **2 canonical skill／prompt／本檔** | 本節；「Daily」失敗長相表（加 Drive 一列）；「Private authority 備份」節；「事件監看」節的 T2 段（無人值守 sweep 的舊敘述改成現況）；`docs/ARCHITECTURE.md` §4.1；`scripts/backup_private.py` 檔頭。 |
| **3 最窄 rule** | Windows daily 不經 Codex，`.codex/rules` 仍是 0 條。放行只有兩個 argv：拿掉 `--no-drive`、多一步 `verify-restore`。Drive 能碰到什麼由 OAuth scope `drive.file` 限住，不是由 rule。回滾：⑯ 加回 `--no-drive`（同一個 commit 改 `tests/test_daily_task.py`）。 |
| **4 contract test** | `tests/test_daily_task.py` 逐項相等（⑯ 連網、⑯b 新步）；`tests/test_backup_entrypoint.py`：「曾經驗過」與「這一份驗過」分開、最後一次成功上傳跨失敗保留、上傳途中被 timeout 強殺留下的 zip 下一輪會清、token 寫回是原子的（換檔前被打斷時舊 token 原封不動；後兩條是 R2 的條件 B、C）；`tests/test_heartbeat_phase1.py`：備份行三格各自現形、三格都成立才不亮、摘要行同一份判定、T2 行與旗標隨「有沒有人輪詢」亮滅、T2 計數與 `sweep` 同一份篩選。 |
| **5 端到端 smoke** | 2026-10-06 實跑：`backup_private.py upload`（`stockbotv2_backup_20261005T214555Z.zip`、79 MB、15 秒，雲端 4 份）→ `verify-restore`（decision_lab 19 表、engine_c 13 表、files.zip 1,402 成員、Neo4j 3,066 nodes／6,927 rels 一致）→ 心跳試跑：段 1「Drive 已上傳｜還原驗證 這份有」、段 3「T2 輪詢：可輪詢 16｜該查 1｜最後一次 2026-10-05（1 天前）」、摘要行無備份旗標；時間快轉到 10-09 不跑 sweep，T2 行亮、摘要行出「T2 輪詢 4 天沒跑」。⚠ 端到端驗收是 10-07 05:30 **真正的排程觸發**那一輪（L13-1：手動觸發不算）。 |

### Sandbox impact review 結論（2026-10-04，Phase 7 Step 7.0f：外部雷達）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily 多四步（harvest 之後、⑥ triage 批次之前）：①b `python -m engine_b.radar prepare`——唯讀 `config/themes.txt`、watch registry、identity registry，只寫 `library/private/heartbeat/radar_batch_<日期>.json`；①c `claude -p`——**能力變更：多開一個 `WebSearch`**（搜尋走 Anthropic 的伺服器端工具；Python 這邊沒有新的連線主機），環境變數白名單、repo 外的 cwd、hook／記憶／外部工具伺服器（`--strict-mcp-config`）／plugin 全關照舊，結果寫 `radar_proposals_<日期>.json`（含程式從 stream 收的 `search`）；①d 指紋保險；①e `python -m engine_b.radar apply`——**寫 lead registry**（`leads.register`＋`annotate_refs`，新鍵登記在 `config/lead_ref_keys.json` 的 `web_radar`）與收據 `radar_<日期>.json`。另外 ⑥ `engine_b.cli list --triage-batch` 的選取把雷達的 lead 排到所有非雷達 lead 之後才截上限；心跳段 3 多一行、`SNAPSHOT_KEYS` 多四鍵（讀執行紀錄）。不喚醒語意 watch、不發通知、不寫任何 authority 以外的 state |
| **2 canonical skill／prompt／本檔** | `crons/radar_prompt.md`（新）、`crons/radar_schema.json`（strict，新）；`config/daily_routine.json` 的 `radar` 區塊與 `_doc`；`docs/ARCHITECTURE.md` §4.1 的層表（加雷達一列、寫明它不是 last30days）；本節與「Daily」流程圖、Routine 分工；`skills/daily-brief/SKILL.md` 的 daily 組成句；`.codex/rules/stockbot-automations.rules` 的註解（daily LLM 步驟零工具的唯一例外）；`config/themes.txt` 加 `power`、`cooling`（只有關鍵字，核心公司 7.1 再定） |
| **3 最窄 rule** | 放行只有 `--settings` 的 `permissions.allow: ["WebSearch"]`——`--allowedTools`、`--permission-mode`、`--dangerously-skip-permissions`、`--permission-prompt-tool` 都在雷達自己的禁用清單（`RADAR_FORBIDDEN_FLAGS`）；每一輪 init 檢查工具**恰為** {StructuredOutput, WebSearch}，多一個少一個都殺行程、整步丟棄；權限被拒判失敗（探針：被拒時 CLI 回 `is_error: false`＋空結果）。`.codex/rules` 仍是 0 條；Codex 不在任何無人值守步驟裡；APP 不加路由。回滾：`radar.enabled=false`（或刪掉整段＝關閉）、`llm.executor=none` |
| **4 contract test** | `tests/test_radar.py`（34 條）：argv 與零工具那份只差兩個值、錄下的雷達 init 只在雷達工具集合下通過、其他工具集合一律不符、收集器只收 CLI 的搜尋結果（摘要文字與其他工具的網址不收）、權限被拒＝失敗、零工具 init 一到就殺；prepare 的哨兵（不讀 Sheet／持股、prompt 沒有私人路徑）；apply：網址不在搜尋結果拒收、寫成 secondary＋搜尋結果的標題＋LLM 那句另放 `refs.radar_fact`、已登記的不碰、上限由程式截、published_at 讀不懂或未來＝null、未知主題→new、未知 watch id 丟棄並計數、壞欄位拒收、搜尋結果裡的壞網址不進允許清單也不弄垮整輪、舊 run_id 拒絕、不喚醒語意 watch；triage 批次雷達排最後（提到持股也不擠掉 harvest 的）；daily 整條流程（結果檔的網址是程式收的）、三種關閉理由、`executor=none`、時限；心跳那一行與四個快照鍵。`tests/test_daily_task.py` 的封閉清單、LLM 步驟清單、跳過集合跟著改。**變異八個各自轉紅**：多開 WebFetch、收集器抓摘要網址、權限被拒不判失敗、不驗網址出處、上限不截、未來日期照收、triage 不排最後、開關不擋 |
| **5 端到端 smoke** | 探針（2026-10-04）：A 不放行——WebSearch 被拒、stream 出 `permission_denied`、result `is_error: false`＋`items: []`（＝現在判失敗的那個同形）；B 只加 `permissions.allow`——正常搜尋，init 與零工具那份**只差 `tools`**（存成 `tests/fixtures/claude_init_radar_ok.json`）。真資料試跑（真主題 5、在盯條件 36 → 真的 `claude -p` → apply 寫進 lead registry **副本**）：status ok、權限被拒 0、搜尋 16 次（prompt 建議 6 次以內——次數每天印在心跳那一行，八週試驗一起看）、148 個網址、18 turns、95.6 秒，提議 0 則（`no_material_change`），寫入 0。`python crons/daily_task.py --dry-run`：四步在清單裡、timeout 加總 224 < 240 分鐘。**第一輪真實排程 2026-10-05 05:30**：看心跳段 3 那一行與 `radar_2026-10-05.json`（ROADMAP Phase 7 驗收⑦「第一輪收據」） |

### Sandbox impact review 結論（2026-10-04，Phase 7 Step 7.0e：個股頁首屏五題＋是不是新賭注）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ materialize（argv 不變）：候選輸入（`candidate_context`）多讀**同一輪**剛寫的 `structure_table` state artifact（`webapp/materialize.py::bet_structure`；`--dir`／`--state-dir` 時讀那個目錄的），層與插槽用候選輸入原本就載的那一份邊（`seats_from_edges`，不多查一次）；另一次唯讀 Neo4j 查節點名（只查持有那幾家坐的、結構表沒帶名字的層；fail-soft）。個股頁 artifact 與候選板多一格 `shared_bet`、`.meta.json` 多 `first_screen_questions`。不寫任何 authority、沒有新網路來源、request path 不變（APP 只讀 artifact） |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` §6.11 與 AnalystView 面板樹。不動任何 skill、prompt |
| **3 最窄 rule** | daily argv 不變；不新增 step、allowlist、APP 路由；APP 仍無寫入端點；`.codex/rules` 的 fixed entry 數不變 |
| **4 contract test** | `tests/test_five_questions_shared_bet.py`（五題七格各放一次且照 plan 對照、元件封閉、`.meta.json` 帶唯一一份、app.js 不留標題、每個元件前端都認得、帶不齊每一格照舊版面；坐的層與讀圖面板同一個函式；互相列出與錨的來處、row 勝過 company、字母序不是共用多寡、自己不列、沒共用是答案、Sheet 讀不到暫停、結構表讀不到只比層、走不到錨照實寫、沒載輸入是缺席、沒有分數名次部位欄位名；候選板與個股頁同一份且候選狀態照宣告；`bet_structure` 讀與缺席）。變異六個（錨的來處一律 row、照共用多寡排、Sheet 讀不到照算、結構表讀不到當成沒錨、自己也列、前端不檢查帶齊）各自轉紅。request path 四種證明照綠 |
| **5 端到端 smoke** | 真資料：改前（HEAD）與改後各 materialize 一次到暫存目錄（`--dir`，`--tracked --registry-listed --structure-table --candidates`，各 78/78）逐頁比對——76 頁 `freshness_identity` 76/76 相同；拿掉 `shared_bet`、時間戳與價格脈絡後 76/76 逐字相同（19 頁的價格序列差在小數點後幾位，是兩次抓行情的浮點差；`content_digest` 本來就含 `generated_at`，每次都會變，不能拿它歸因）；候選板除 4 列的 `shared_bet` 外相同、結構表相同、`.meta.json` 只多 `first_screen_questions`、候選狀態序列那一行相同。headless Edge 實點 AXTI／COHR／LITE／SIVE.ST：五題 5/5、七格都在、COHR 與 SIVE.ST 互列「同一層／插槽 High-power CW DFB laser」、首屏沒有分數名次字樣；AAPL（無敘事）照舊版面；候選板印 6 句共用 |

### Sandbox impact review 結論（2026-10-04，Phase 7 Step 7.0d：敘事加碼條件 `confirm[]`）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 互動寫入端 `python -m alpha brief <T> --add`：spec 多收 `confirm[]`；寫入後多登記 `condition_role=confirm` 的語意 watch（同一個 registry 檔、同一條 `add_watch`、同一個寫入前預演）。daily 會跑的消費端只**多讀一個欄位**：⑬ materialize（候選板與個股頁多一份 `confirm` 列）、⑱ 心跳段 2 多一行與三個快照鍵、健康審查與 `audit invariants`（Orphans 對 `#c<n>` 解析到敘事的 `confirm[]`）。語意預篩、T0 喚醒、佇列分段、到期與 liveness 照 `disproof_ref` 走，不分角色——讀取、寫入、查詢、網路都不變 |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` §6.11；`skills/research-drain/SKILL.md` 段 `narrative_rewrite` 的 ⓒⓓ（`confirmed` 處置、觸及只提醒）；研究 packet 的 `brief_frame`（`_how_to_use`、`spec_shape`）。預篩 prompt 本來就寫「反證或確認條件」——不改 |
| **3 最窄 rule** | daily argv 不變；不新增 step、allowlist、APP 路由；APP 仍無寫入端點 |
| **4 contract test** | `tests/test_narrative_confirm.py`（選填欄不進 id、真實 ledger 每一行 id 重算逐位相同、三件套與實體與出處、寫入端四條拒收、登記成 `brief:<id>#c1`＋`condition_role`、角色封閉且只限敘事來源、不被算成反證〔計數、downside、可開〕、觸及進 `narrative_rewrite` 且下一版以 `confirmed` 處置、候選狀態照宣告、到期也進重寫、候選板列〔每句由 `confirm_line` 在 materialize 端組好、`app.js` 照印不組字——它的全檔部位用語禁字檢查不放寬〕、心跳那一行與快照鍵、audit 解析到 `confirm[]`）。變異三個：加碼條件被算成反證 → 1 紅；可開不跳過它＋id 欄位無條件放進 `confirm` → 3 紅 |
| **5 端到端 smoke** | 真資料：心跳段 2「反證：在盯 37（其中叫不醒 3）｜觸及待處置 0…」與今天 05:30 的心跳逐字相同、新的一行「加碼條件：在盯 0｜觸及待處置 0｜到期待重寫 0」；20 行敘事 ledger 的 `brief_id` 重算 20 行逐位相同；`audit invariants` 14 PASS |

### Sandbox impact review 結論（2026-10-04，Phase 7 Step 7.0c：敘事「要翻倍需要什麼」、翻倍起點、「已定價」白話）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ `python -m webapp materialize`：讀取、寫入、查詢都不變——read model 的財報觀測多一格 `market_cap_settlement`（同一份快照的 price × shares × 名冊報價單位的換算係數——係數由 `briefing/alpha_view/sources.py::identity_mapping` 從 `identity.currency` 查好注入，builder 是純函式、不碰 identity；不打匯率），敘事的兩個新 placeholder 只**選取**它與既有的 `revenue_ttm`；`.meta.json` 的字彙多一個鍵 `plain_priced_in`。個股頁 artifact 不收財報觀測那一節，所以四檔真資料的 artifact 除 `generated_at` 逐位相同。互動寫入端（`python -m alpha brief <T> --add`）多一條拒收（重押讀圖時格層引用指向被取代的讀圖），不碰任何新檔 |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` 敘事 v2 段與 §6.6「已定價嗎」那句；研究 session 的題目由 packet 的 `brief_frame` 帶（`BRIEF_FRAME_V2`），skill 不另抄題目——不改 |
| **3 最窄 rule** | daily argv 不變；不新增 step、allowlist、APP 路由；APP 仍無寫入端點 |
| **4 contract test** | `tests/test_narrative_doubling.py`（新題目與字彙、`{price}`／已定價數字在這一格照拒、sources 從名冊字彙查換算係數、GBp 換成 GBP 而且不打匯率、報價單位未登記 fail closed、起點印金額＋幣別＋日期或不給值、填值與舊紀錄不變、被取代的讀圖拒收並列出該換的 id、現行讀圖與別的單位放行）；`tests/test_webapp_api.py::test_priced_in_is_explained_from_one_string_on_both_places`。變異：拿掉第 ⑦ 項 → 1 紅；市值不換單位 → 1 紅 |
| **5 端到端 smoke** | 真資料：重新 materialize AXTI／COHR／LITE／SIVE.ST——敘事四檔各 8 格逐字相同、artifact 除 `generated_at` 逐位相同、`.meta.json` 只多 `plain_priced_in`；headless Edge 開 `#/AXTI`：頁面渲染、白話出現兩次（首屏、稽核區）；`python -m alpha research AXTI` 的 packet 印新題目；市值換算：IQE.L 729.5 億 GBp → **7.3 億 GBP**、AXTI 56.3 億 USD、SIVE.ST 106.1 億 SEK、300308.SZ 9,016.0 億 CNY；20 行敘事 ledger 解析 0 失敗 |

### Sandbox impact review 結論（2026-10-04，Phase 7 Step 7.0b：巢狀 writer lock、thesis 逾期提醒只看 lifecycle）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | ①`engine_b/writer_lock.hold`（新 context manager）：同 owner 的未過期鎖已在 → 不 acquire、不續期、不 release（鎖檔一個 byte 都不寫）；否則照常 acquire／release；異 owner 照舊 fail closed。改用它的四支都是**互動專用**的遷移工具（`loader/migrate_sourcedoc_json_section.py` 兩處、`loader/migrate_identity_cleanup.py`、`engine_c/migrate_fundamental_metrics.py`），daily 的 `scheduled` acquire／release 不動。②`crons/thesis_freshness_check.py`（SessionStart hook）：讀的檔不變（`thesis/lifecycle.json`、`thesis/*_lane_memo.md`、`library/leads/todo_pool.json`）、不寫任何檔；拿掉「memo 生成日＋週期」那一套（到期只委派 `thesis.lifecycle_schedule.is_due`），lifecycle 讀不到改成明講，「沒有 lifecycle 的舊 memo N 份」只在 hook 有話要說時附上。③daily 的健康審查（`python -m query.health_audit --json`）：「Memo 新鮮度」那一節改吃同一個 `check()`（`is_due`）並多一行舊 memo 清單；讀取、寫入、節數（14）都不變。④`engine_b/todo.py` 的 pq2 收集器呼叫的 `lifecycle_due_detail` 多一個選填 `today`，預設行為不變 |
| **2 canonical skill／prompt／本檔** | 本節；上面「Writer lock」段補一句；`skills/development-flow/SKILL.md` 的 INTAKE 多一行 `Case`、`docs/AGENT_WORKFLOW.md` 的 `Zoom / Review`（開發 gate 的落點，與本節的程式無關） |
| **3 最窄 rule** | daily argv 不變、不新增 step／allowlist；SessionStart hook 的命令字串不變；四支遷移工具仍是互動專用、不進任何無人值守清單 |
| **4 contract test** | `tests/test_writer_lock.py`（巢狀不動外層鎖與 TTL、單獨跑照常取放、本體失敗也釋放、異 owner 照擋、過期的同 owner 鎖照常接手）；`tests/test_engine_c_equity_issuance.py::test_migration_cli_refuses_a_missing_db_and_leaves_a_users_lock_alone`（既有）；`tests/test_lifecycle_hook.py`（複查過的 thesis 到 next_check 才報、沒有 lifecycle 的 memo 只列不報、沒有排程出口的照報、10-04 的 hook 安靜、說話時附舊 memo、lifecycle 讀不到要說、粗體生成日期讀得到）；`tests/test_agent_workflow.py::test_intake_carries_the_case_that_exposed_a_development_item`。變異：`hold` 一律取放 → 2 紅；`check` 不看 `is_due` → 2 紅；拿掉「讀不到要說」→ 1 紅 |
| **5 端到端 smoke** | 真資料：SessionStart hook 2026-10-04 安靜（exit 0、沒有輸出）；舊程式同日的 `check()`＝`[('cpo', 91), ('sivers', 36)]` → 新程式 `[]`（兩則假逾期 → 0）；真 lifecycle 三筆：10-04 都不到期、10-30 axt_inp（Q3 催化劑，推估日）＋sivers（next_check 10-29）、12-01 再加 coherent_cpo；健康審查 14 節全綠，「Memo 新鮮度」只剩「不算逾期的舊 memo 6 份」 |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.7d：預測表改寫規則①）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ materialize 讀圖 artifact 的 `predictions`：只改一個判定分支（同 `result_digest` 的後繼要**同 kind 或同一天**才算改寫，否則落到 reversed）；讀取、寫入、查詢都不變 |
| **2 canonical skill／prompt／本檔** | 本節；規則全文住 `alpha/structure_reading/predictions.py` 模組 docstring。skill／prompt 不描述預測表終局——不改 |
| **3 最窄 rule** | daily argv 不變；不新增 step、allowlist、APP 路由 |
| **4 contract test** | `tests/test_reading_predictions.py::test_rule_one_same_digest_rewrite_needs_the_same_kind_or_the_same_day`（同 digest 不同 kind 隔日＝reversed、同日＝改寫、同 kind 隔日＝改寫）；變異兩個全紅 |
| **5 端到端 smoke** | 真實讀圖 ledger（同一個 process，git HEAD 規則 vs 新規則）：15 筆終局逐筆相同、受影響 0；計數＝對 0／錯 0／改寫 9／現行 2／非斷言 4，與 Phase 5 結案相同 |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.7c：排除未收盤 K 棒）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑤ `scripts/outcome_if_settled_today.py` 與 ⑬ materialize（部位頁、計分表、個股頁的走勢折線、brief 的事件監控）的**請求、主機、寫入都不變**：同一個 `yf.Ticker(...).history(...)`，多讀同一個 handle 上已經回來的 `history_metadata`（不多打請求）。判定收進 `alpha/providers/close_series.py`（`bar_state`／`closed_points`）：交易所當地今天＋盤中 → 拿掉那一根；拿不到交易時段 → 保留。輸出多一格 `price_budget.closing_bars`（checked、拿掉的檔、收盤狀態未知的檔、字彙）；報告與 APP **有才印**。`fetch_close_series` 的 `today` 參數（沒有呼叫端用）換成 `now`／`states` |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` 單檔走勢圖那段（owner）。skill／prompt 不描述取價——不改 |
| **3 最窄 rule** | daily argv 不變（`tests/test_daily_task.py`、`tests/test_codex_daily_permissions.py`）；不新增 step、allowlist、APP 路由 |
| **4 contract test** | `tests/test_closing_bars.py`（盤中拿掉、收盤後保留、交易所當地今天而不是台北的今天、10-03 實測的收盤後週五那根、沒有交易時段＝未知、交易時段滾到下一段＝已收、時戳無時區＝未知、NaN 先跳過、五個取價點都走 owner 且逐檔記狀態、追蹤表與計分表把計數放進輸出且報告那一句共用、APP 兩頁有才印）；變異五個全紅 |
| **5 端到端 smoke** | 同一份價格（同一個 process，yfinance 回應第一次真抓、之後重播）：git HEAD 的舊程式 vs 新程式——追蹤表 `collect()` **逐欄相同**（history 22 列；扣新加的 `closing_bars`），計分表 `build_scorecard()` 只差 `generated_at`／`content_digest`；今天（週六）新程式 checked 32＋49 檔、拿掉 0、未知 0。與今天 05:30 daily 的 artifact 有不同（部位頁的報酬聚合、計分表的 30／90 日窗走滿筆數），但同一份價格上舊新相同，所以不是本 Step 的程式；計分表那部分的來源是 `day`（05:30 跑時 UTC 日期是 10-02、現在是 10-03），部位頁那部分沒有逐項追 |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.7b：APP 自偵舊程式）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `python -m webapp serve` 的 request path 只多一件事：`/api/v1/health` 對 `webapp/` 套件目錄做本機 `os.walk`＋`stat`（約十個檔），比對啟動時記下的指紋；**不讀檔案內容、不寫、不跑 subprocess、不連網路、不 import 新模組**（`webapp/api.py` 的 import allowlist 不變，指紋函式住 `webapp/contracts.py`，那裡原本就允許 `os`／`datetime`）。health 多一格 `code`（stale、啟動時間、前後檔數與最新改動時間；**沒有路徑**）。前端每次換頁多一次 `GET /api/v1/health`。daily 不跑 serve，不受影響 |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` §6.9。skill／prompt 不描述 APP 的健康檢查——不改 |
| **3 最窄 rule** | 不新增路由（health 原本就在）、不新增 allowlist、不改 Cloudflare 邊界；重啟仍是使用者動作 |
| **4 contract test** | `tests/test_webapp_code_freshness.py`（剛啟動不 stale、改一支 .py 就 stale、多一支 mtime 舊的檔也 stale、`__pycache__` 與 static 以外的非 .py 不算、static 任何檔都算、health 不透露路徑、預設根是 webapp 套件、前端每次換頁問 health 且伺服器比畫面舊也印）；`tests/test_webapp_request_path.py` 照綠 |
| **5 端到端 smoke** | headless Edge（8799）：①舊伺服器（6.7b 之前起跑）＋新畫面 → 頂端印「APP 跑的程式比這個畫面舊（健康檢查沒有程式指紋）——請重啟」；②重啟後 `stale: false`、橫幅隱藏；③只改 `webapp/static/styles.css` 的 mtime → 結構表頁頂端印「APP 跑的是 2026-10-03T12:21+08:00 的程式，之後程式有更新——請重啟」 |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.7a：結構表逐列需求錨）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ materialize（結構表與個股頁）**讀取不變**：同一份 assertion 列與逐字，`demand_chain` 每列多走一次節點側（純記憶體），沒有新查詢、主機或憑證。值逐列重算：`demand_anchor`／`chain`／`demand_hops`（先節點、走不到才退回公司）；欄位變多：結構表每列 `anchor_basis`／`anchor_basis_label`、`notes.anchor_column`、`vocab.anchor_basis`，個股讀取模型 `ScarcityInputs.demand_anchor_basis`、邊表的 `demand_anchor_basis`、「需求錨點／距需求端跳數」的 `reason`；心跳部位段「前三錨」那一行多「公司層 N 列」。`python -m query.bottleneck` 的欄名與表後讀法換新 |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` structure_table kind 那段；`CONCEPTS.md` `anchor_basis` 一列。skill／prompt 沒有描述需求錨的走法——不改。`alpha/models/session_assessor.py` 的 LLM 輸入多一個鍵 `demand_anchor_basis`（只在互動 session 跑，不在 daily） |
| **3 最窄 rule** | daily argv 不變（`tests/test_daily_task.py`）；不新增 step、allowlist、APP 路由 |
| **4 contract test** | `tests/test_row_demand_anchor.py`（先節點後公司、有錨只多不少、同公司可不同錨、markdown 只標退回那格、artifact 字彙／讀法／identity、心跳「公司層 N 列」與舊 artifact 不印 0、provider 與個股頁帶 basis、白話對照 key 集合相同）；變異五個全紅（一律從公司走、只從節點走、provider 不帶、個股頁不加註、心跳不分舊 artifact） |
| **5 端到端 smoke** | 真實圖（唯讀，worktree 新程式）：224 列、有錨 211 → 213、改前有錨改後沒錨 0；basis row 146／company 67／兩邊都走不到 11；Lam 9 列 6 列 row、3 列公司層；前三錨 `tech:ai_switch` 102 → 126、`tech:optical_scale_up` 39 → 29、`tech:essential_chips_mature_node` 29 → 21。provider（sub≥4，17 家）：同公司內順序只有 GFS 變、Q1 取到的邊 0 家變、Q1 那條邊的錨變 3 家（AXT、Coherent、Micron）、跳數變 9 家；產業組 0 家變（baseline §21） |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.6：稀釋燈只認募資文件）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ②b `python -m engine_c.history_backfill --incremental` 的 **argv、主機、請求數都不變**：落後檢查本來就為每檔（已有財報列者）抓一次 `data.sec.gov/submissions`，`fetchers/edgar.py` 拆成「抓一次」（`fetch_submissions`）＋「依表單篩」（`filings_from_submissions`），同一份清單順帶寫進 Engine C 的**兩張新表** `equity_offering_filings`／`equity_offering_checks`（私有 SQLite；開庫時 `CREATE TABLE IF NOT EXISTS`，**不動既有表與 CHECK**）。`get_filings` 行為不變（多回 `items`、`accession_dashed` 兩個鍵）。非增量的互動回填會為清單補抓一次（每檔多 1 次請求，同一組主機；daily 不走這條）。⑬ materialize 經同一支 `get_wipeout_inputs` 的連線多讀兩張表（唯讀 SELECT）；稀釋燈的判色變了、理由句換新，artifact 形狀不變（inputs 多 `offerings`／`offering_summary`／`context_summary`） |
| **2 canonical skill／prompt／本檔** | 本節與上面歷史回填那幾行；`docs/ARCHITECTURE.md` 三題那一列；稀釋燈規則全文住 `alpha/wipeout.py::_DILUTION_RULE`（印在稽核層）；封閉清單住 `engine_c/offerings.py`。skill 不需要改：沒有任何 skill 描述稀釋燈怎麼判色 |
| **3 最窄 rule** | daily ②b 與 ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、allowlist、APP 路由；Postgres 以 `engine_c/migrations/20261003_add_equity_offering_filings.sql`＋`schema.sql` 同步（只建表，寫入照舊只接 SQLite） |
| **4 contract test** | `tests/test_dilution_offerings.py`（plan §7 五個夾具、封閉清單逐表單、以申報日落窗、as-of 之後不可見、清單涵蓋不到窗＝灰、找到了照樣黃、沒有金額不上色、**增量不多抓一次** submissions、`get_filings` 舊鍵不變）；`tests/test_wipeout_flags.py`、`tests/test_engine_c_equity_issuance.py` 的金額那一半照守 |
| **5 端到端 smoke** | 見 baseline §20：正式庫以檔案複製到 scratchpad（當下 WAL 0 位元組）、對副本跑 `--incremental --no-prices`：43 檔寫入清單、3 檔這輪沒抓（沒有既存財報列）、30 檔不是 SEC 申報人；11 檔黃燈逐檔前後對照（10 黃、LRCX 轉灰）並手核 AXTI／COHR／NVDA／INTC 的文件封面；正式庫 sha256 前後相同、沒有新表（上線後由 daily 建表與寫入） |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.5：sub 旗標跟著值走到消費端）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ 的 materialize **讀取與寫入都不變**：旗標由 6.4 起已在同一個唯讀 transaction 取得的 assertion 列與逐字算出（`query.sub_language.sub_language_flags`，本機字表），沒有新查詢、沒有新主機或憑證。artifact 欄位變多：結構表每列 `sub_assertion_id`／`sub_language_in_quote`、走圖第 1 型命中 `demand_quote`／`demand_quote_note`、個股讀取模型「替代難度」的 `reason`；讀圖 artifact 的五個角度的邊多 `sub_language_in_quote`（不進 digest） |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` §3「sub 旗標跟著值走」；`CONCEPTS.md` `sub_language_in_quote` 一列。skill／prompt 不改（字表不得出現在 `prompts/`、`skills/`——L19） |
| **3 最窄 rule** | daily ⑬ argv 不變；不新增 step、allowlist、APP 路由；APP 只多照抄兩格（結構表那一格、走圖那一句） |
| **4 contract test** | `tests/test_sub_language_consumers.py`（贏家的旗標、缺不是 false、不進 digest／快照列且讀圖仍 current、走圖第 1 型旁註、「替代難度」旁註且值與 Q1 不變） |
| **5 端到端 smoke** | 見 baseline §19：4 份現行讀圖的 status／分級／變化清單／digest 改前改後逐位相同（CLI `--digest` 也相同）；真實圖結構表 66 列帶 sub（撐得住 9／撐不住 57） |

### Sandbox impact review 結論（2026-10-03，Phase 6 Step 6.4：證據等級讀逐字——逐來源具名＋轉述字表）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 證據等級的分類（`query.bottleneck.classify_evidence`）**多讀全部逐字**，所以每個會分類的入口在**同一個唯讀 transaction** 裡多跑一條唯讀 Cypher（`query.sub_language.fetch_all_quotes`：`MATCH (ea:EdgeAssertion)-[:QUOTES]->(s:Source) RETURN …`）：daily ⑬ 的 `materialize --structure-table`（本來就讀，改成與邊同一個 transaction）、`--graph-walk`（同上）、`--structure-readings`／`--candidates`／個股頁（經 `query.structure._load_edges` 與 `alpha.providers.graph_neo4j`，新多一條）；互動入口 `python -m query.bottleneck`、`python -m query.structure`、`scripts/audit_sole_source_independence.py`、兩支遷移工具的 dry-run 同樣多讀一次。`scripts/prepare_research_action.py` 在既有的 READ session 裡多讀三樣（assertion 列、`QUOTES` 連結、`Source` 逐字）算「入圖後證據等級會變的邊」，寫進 RA 紀錄既有的 `merge_side_effect_check` 收據。新讀一個 tracked 設定檔 `config/relay_language.json`。**寫入面不變**（artifact 欄位變多：`graph_walk.layer_stats` 的 `corroboration_withheld`／`ec_without_naming_quote`／`evidence_vs_baseline`／`relay_language`，`ec_quote_does_not_name_supplier` 退役）；**無新網路主機、無新憑證**（本機 Neo4j bolt，與既有 `_graph_driver` 同一組）、不碰 `.git` |
| **2 canonical skill／prompt／本檔** | 本節；`docs/ARCHITECTURE.md` §3「證據等級」；`CONCEPTS.md`「外部印證」；closed-vocabulary registry 登記轉述字表。**skill／prompt 刻意不改**：轉述字表與具名規則不得出現在 `prompts/`、`skills/`（L19；plan 不可越線 7）——抽取端讀得到就會挑不含那些字的引文 |
| **3 最窄 rule** | daily ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條；APP 不新增路由、request path 不跑分類（只讀 artifact）。prepare 的多讀與既有的唯讀查圖同一個 session、同一組憑證 |
| **4 contract test** | `tests/test_corroboration.py`（plan §5 九個夾具＋Sivers 舊口徑對照＋逐份豁免）、`tests/test_relay_language.py`（字表形狀、比對、L19 守門與偵測器自測）、`tests/test_layer_stats.py`（三種理由、違反數、基準升降、`summary_line`）、`tests/test_research_actions.py`（packet 的證據等級預告與讀不到時的缺席）、`tests/test_merge_side_effects.py`（MERGE 語意的模擬） |
| **5 端到端 smoke** | 見 baseline §18：真實圖上新規則 230 條外部印證（6.0 基準 250：升 2〔6.3c 名冊新公司〕、降 22〔6.3b GSR 3＋規則 19：未具名 13／名冊無名 4／轉述 2〕），逐條與 6.0 模擬對照；`ec_without_naming_quote` 0；①獨家且全自報 73 → 77（與 plan §0.2 預測的 4 個節點相同）；走圖九型命中不變；分類全圖 0.5 秒。daily ⑬ 的**同一條 argv** 加 `--dir <scratchpad>` 實跑一次（真實 APP 狀態與候選序列不動）：84／84 完成、exit 0；真實目錄只重 materialize `--graph-walk --structure-table`，心跳段 3 印出新的那一行 |

### Sandbox impact review 結論（2026-10-02，Phase 5 Step 5.6：候選狀態每日序列）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ 的 `python -m webapp materialize --candidates` **多一個寫入、讀取不變**：候選板 artifact 寫完之後，改寫 `library/private/measurement/candidate_state_series.jsonl`（目錄由程式建；ignored、private）。做法是讀既有行、同日那一行換掉、壞行原樣留著，整檔寫到同目錄的 `.tmp` 再 `os.replace`。**只寫不讀**：心跳與 APP 都不吃它。**沒有新讀取、沒有新網路主機或憑證**。寫失敗只印警告，候選板 artifact 照寫。預設以外的 state 目錄（測試、`--dir`、`STOCKBOT_APP_STATE_DIR`）寫在那個目錄裡的 `measurement/`，試跑碰不到真實序列 |
| **2 canonical skill／prompt／本檔** | 本節；plan §7。這份序列是量測的原料，結案與之後的 Phase 才會讀它；在那之前沒有任何 skill 或 prompt 需要知道它 |
| **3 最窄 rule** | daily ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條。新寫入點在 `library/private/` 之下（已 ignored，`git ls-files library/private` 仍為空），與 ⑬ 既有的寫入（`library/private/app/state/`）是同一棵樹、同一個 writer。request path 不碰它：寫入只在 `materialize_candidates`，serve 端三個模組不得 import materialize（`tests/test_webapp_request_path.py`） |
| **4 contract test** | `tests/test_webapp_candidates_series.py` 涵蓋：同日重跑 1 行、跨日 2 行、壞行原樣保留且前後好行都在、計數照抄 artifact（`held` 讀不到是 null）、只有預設 state 目錄寫真實路徑、真的走 `materialize_candidates`、寫失敗不擋候選板 |
| **5 端到端 smoke** | 2026-10-02 真實 `materialize --candidates`：序列出現第一行，`counts`／`side`／`no_narrative`、`date`、`oldest_stall_days` 與 artifact 相同；心跳逐行對照沒有新行（候選行的變動是當天 Sheet 補了 COHR）；備份的「之後變動未備份」多 1 檔，代表新檔在備份範圍內 |

### Sandbox impact review 結論（2026-10-02，Phase 5 Step 5.5：計分表接主題等權組基準＋APP 計分表頁）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ 的 `python -m webapp materialize --scorecard` **讀取變多、寫入不變**：多讀主題等權組 ledger `library/private/alpha/theme_cohorts/*.jsonl`（本機、唯讀；「哪一組是基準」與追蹤表同一支 `alpha.theme_cohort.measurement_cohort`）。**網路**：yfinance 多抓「組成員中原本不在取價清單的」那幾檔（2026-10-02：42 → 49 檔，多 7 檔），**同一組主機、無新憑證**；仍受程式裡的上限 `MAX_PRICED_SYMBOLS`（200）約束，截斷順序是基準 → 點名標的 → 成員（基準永遠留著、成員先被截），截掉的印在 artifact 的 `price_budget.truncated` 與 `theme_cohort.missing`。取價改為跳過 NaN 收盤（§0.6 #3）。**寫入**：仍只寫 ignored derived cache `account_scorecard.json`（schema `/2`）。**APP**：多一個 GET `/api/v1/account-scorecard`，只讀這份 artifact、照抄，不重算、不抓價、不寫任何東西。心跳段 5 讀同一份 artifact，多印一格「主題等權組基準：有／無」，零網路 |
| **2 canonical skill／prompt／本檔** | 本節；plan §6；`docs/ARCHITECTURE.md` 心跳段 5 那一段（四個已知偏差、第三個基準、APP 頁）。`skills/daily-brief` 的畫面表不變：它照抄心跳段 5，那一格已在心跳裡 |
| **3 最窄 rule** | daily ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條。APP 多一個**只讀**路由（仍只綁 127.0.0.1、仍在 Cloudflare Access 後面、沒有寫入端點）：請求路徑的四種證明改走同一份 `STATE_ROUTES`，另有一條測試守「路由表＝`/meta` 的 endpoints＝四種證明走的清單」——順手補上一直沒被證明過的 `/structure-readings` 與 `/meta` 漏列的 `/candidates` |
| **4 contract test** | `tests/test_account_scorecard.py`（對組的超額＝手算、本檔被排除、組缺席三種 kind 不是 0、成員取不到價有自己的 reason、成員併進取價清單且 `requested` 增量＝新增檔數、截斷先截成員不擠掉基準與點名、多組不猜、freshness 跟組不跟價、render 與心跳那一格、NaN 收盤被跳過端點退回前一根、第四條已知偏差）；`tests/test_webapp_request_path.py`（`STATE_ROUTES`＋守門測試）；`tests/test_heartbeat.py` |
| **5 端到端 smoke** | 見 baseline §18：同一份真實價格上改前（master）與改後逐格比對 16／16 相同；重放 10-01 的 NaN 收盤 7／10 格被污染、改後＝乾淨價格；真實 `materialize --scorecard`；心跳段 5 逐行對照只多那一格；headless Edge 在臨時實例渲染 `#/account-scorecard` |

### Sandbox impact review 結論（2026-10-02，Phase 5 Step 5.4：圖預測對錯表）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ 的 `python -m webapp materialize --structure-readings` **讀取變多、寫入不變**：多讀每個節點讀圖 ledger 的全部紀錄（含被取代的；本來就讀）、`library/leads/pending_leads.json`（判觸及引用文件的 `published_at`）、同一個 Neo4j bolt 本機連線上一條**唯讀** Cypher（`MATCH (d:SourceDoc) RETURN d.id, d.published_at`，`READ_ACCESS` session、用完即關）。**無新增網路主機或憑證**（Neo4j 本機與既有 `_graph_driver` 同一組）。只寫 ignored derived cache `structure_readings.json`（schema `/2`）。Neo4j 讀不到時錯的種類整段 `upstream_unavailable`、終局照算；as-of 視角明確拒絕（`point_in_time_unavailable`） |
| **2 canonical skill／prompt／本檔** | 本節；plan §5；讀圖頁的預測表與 `this_is_not` 新句 |
| **3 最窄 rule** | daily ⑬ 的 argv **不變**；不新增 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條；APP 不新增路由（structure-readings 同一個 GET，artifact 多 `predictions`） |
| **4 contract test** | `tests/test_reading_predictions.py`（夾具鏈 A／A'／B／C／D／E 逐筆終局、改寫不算對、staleness 不是判定、沒日期與年月精度是未定日、讀不到圖是 upstream_unavailable、判觸及只看單數 judgment 與 `#n` 後綴、到期後重讀同讀法＝對、真實 15 筆的形狀、artifact v2、心跳一行與三種缺席、快照鍵） |
| **5 端到端 smoke** | 見 baseline §17（真實資料 materialize、預測表與 5.0 手算逐筆相同、心跳逐行對照、headless Edge 渲染讀圖頁） |

### Sandbox impact review 結論（2026-10-02，Phase 5 Step 5.3：`record_trade.py --backfill-before-receipts`）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 只在互動 session 由使用者跑。**網路**：Google Sheet 讀一次，與 `--log-only` 同一組呼叫（`read_portfolio_values`、`fetch_portfolio`、`locate_portfolio_cells`）；Sheet 寫入函式 **0 呼叫**，因為旗標強制 `--log-only`，配 `--apply` 會被拒收。**寫入**：只有 `library/trades/trade_log.jsonl` append 一行（A5，append-only）；同一筆重跑不重寫。**讀**：`config/beta_policy.json`、`config/investment_policy.json`、名冊、排程時區設定。**不讀**今天的判斷：敘事 ledger、候選板、個股頁、watch、lifecycle 都不碰（R2-a 用記次替身與開檔稽核實測為 0）。**fail closed**：七種入口拒收與「排程時區讀不到」都在碰 Sheet 之前；「名冊讀不到」在讀 Sheet 之後、寫入之前。三者都是 exit 2、什麼都不寫。**無新增網路主機或憑證** |
| **2 canonical skill／prompt／本檔** | 本節；本檔「記一筆成交」的回填段；plan §4。`skills/investment-research` 只指到 `scripts/record_trade.py`，不必改 |
| **3 最窄 rule** | 不進任何無人值守路徑：`record_trade` 在 `.claude/**`（tracked）、`.codex/**`、`crons/**`、`config/**` 都是 0 命中。tracked 的 `.claude/settings.json` 沒有 allow 條目，`.codex/rules` 0 條。⚠ **使用者本機、gitignored 的 `.claude/settings.local.json` 有 `Bash(python *)`**：互動 session 不經提示就能跑這條，也就是直接 append trade_log。這條寬權限早於 5.3，對每一支 `scripts/*.py` 都一樣，包括既有的 `--log-only`／`--apply`。本 Step 不改權限檔；要不要收窄由使用者決定（plan §14） |
| **4 contract test** | `tests/test_record_trade_receipt.py` §7 涵蓋：七種拒收逐字斷言理由，且 Sheet 0 讀、trade_log 不建檔、判斷讀取 0；排程時區讀不到也拒收；名冊讀不到 fail closed；名冊沒有這家照實記 None；放行一筆時收據形狀逐鍵相等、Sheet 0 寫、重跑不重寫；5% 上限的夾具持股合計＝NAV，並斷言擋下理由是「超過單筆上限」（R2-a C2，上限放寬到 99% 的變異會紅）；回填賣出不要 watch；不帶旗標的 `--log-only` 照讀敘事；`NARRATIVE_STATES` 封閉。live lane 照抄 `backfilled` 標記的測試在 `tests/test_measurement_lanes.py` |
| **5 端到端 smoke** | 沒有真實跑：回填寫的是 append-only authority，屬於使用者動作（plan §14 #3）。R2-a 的獨立 harness 跑 132 項檢查、0 失敗：Sheet 呼叫記次、socket 全擋、開檔稽核、真實 trade_log 指紋 `861d2008…d5` 前後不變。條件修正後另跑窄範圍覆核 |

### Sandbox impact review 結論（2026-10-02，Phase 5 Step 5.2：追蹤表三條 lane＋主題等權組基準）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑤ `scripts/outcome_if_settled_today.py` 與 ⑬ `python -m webapp materialize --positions` 共用的 `collect()` **讀取變多、寫入不變**：多讀 `library/trades/trade_log.jsonl`（live lane）、敘事 ledger `library/private/alpha/briefs/`（paper lane）、`library/leads/pending_leads.json`（首次點名它的 lead）、主題等權組 ledger、`config/beta_policy.json`（alpha 判別）與名冊（持股解析）——全是本機檔、唯讀。**網路**：history lane 的 22 檔與 2 個基準沿用原路徑；新 lane 多抓 paper／live 與主題等權組成員的收盤（yfinance，**同一組主機、無新憑證**），去重後受程式裡的上限 `MAX_LANE_SYMBOLS`（60，基準永遠留著）約束、截掉的印在報表與 artifact 的 `price_budget`；2026-10-02 實際 17 檔（2 基準＋4 paper＋15 成員，重疊 4）。**寫入**：⑤ 仍只寫 `library/private/decision_lab/outcome_aggregate.json`／`.jsonl`（既有四欄＝history，一字不動；新資料只住 `lanes`／`theme_cohort` 兩個新鍵）；**帶 `--no-benchmark` 的診斷跑法改為不寫**（以前會把當天那一行的超額蓋成 null，plan §0.6 #1）。⑬ 仍只呼叫 `collect()`、不寫聚合檔，只寫 ignored derived cache `positions.json`（schema `/2`） |
| **2 canonical skill／prompt／本檔** | 本節；plan §3；APP positions 頁頁首的三條 lane 說明與 `this_is_not` 新句 |
| **3 最窄 rule** | daily ⑤ 與 ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條；APP 不新增路由（positions 同一個 GET，artifact 多 `lanes`） |
| **4 contract test** | `tests/test_measurement_lanes.py`（主題等權組排除本檔與缺價列出、NaN 收盤不收、live 收據照抄與 backfilled 標記、賣出 FIFO、幣別不一致缺席、paper 錨第一份 v2、GBp 結算、三條 lane 分母分開、組缺席／多組、取價上限截斷、空 lane 印「還沒有列」、聚合檔四欄不變＋同日去重、`--no-benchmark` 不寫、artifact v2 照抄、freshness 跟成員不跟價、心跳段 4 與快照鍵、舊 artifact 缺 lanes 印缺席）；`tests/test_webapp_positions.py`（materialize 只呼叫 collect）；`tests/test_heartbeat*.py` |
| **5 端到端 smoke** | 2026-10-02 真實資料：`collect()` → live 0 列（beta 事件 2 不進 lane）、paper 4 列（錨點 2026-09-29，SIVE.ST 用第一份 v2）、history 22 列錨點指紋 `6ea352ed…7b93` 與 5.0 相同；同一份價格上改前（HEAD 版）與改後 history 的 rows／三量／等權逐位相同；`materialize --positions` 後聚合檔指紋不變、artifact `/2`；心跳段 4 與 5.0 逐行對照只在 lane 行變；headless Edge 在臨時實例（8798）實際渲染 `#/positions` 的三條 lane 與 paper 表。⚠ 2026-09-10 起長駐的 APP 行程用的是當時的程式，要重啟才讀得到 `/2`（它對 09-10 之後新增的結構表、走圖、讀圖、候選板也一直回 404） |

### Sandbox impact review 結論（2026-09-30，Phase 3 Step 3.7：個股頁首屏、稽核區、readiness、downside）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `python -m webapp materialize <T>…`（daily ⑬ 同一條）的讀取**變多、寫入不變**：每一輪多載一次候選推導的輸入（同一輪帶 `--candidates` 時個股頁與候選板共用這一份，不是各讀一次 Sheet／FX）——與 `--candidates` 同一個 `alpha.providers.candidates.candidate_context`：watch registry、thesis lifecycle、讀圖對圖（Neo4j bolt 本機，唯讀）、敘事 ledger、Google Sheet（`spreadsheets.readonly`，已持有判定）、邊緣判定（Engine C 本機檔＋市值正規化的 FX，yfinance，與 `--beta`／`--candidates` 同一個 `get_fx_snapshot`）；thesis memo 檔（downside 的推翻條件，唯讀）。只寫 ignored derived cache（個股 artifact，atomic）。**無新增網路主機或憑證**。as-of 視角不載（`point_in_time_unavailable`）。`python -m briefing alpha-card`／`analyst-view` 單檔 CLI 多讀一次圖與讀圖 ledger（鏈段需求端、讀圖面板），唯讀；CLI **不讀 Sheet**，所以候選與 downside 兩個選配面板在 CLI 印「這次沒有給」（as-of 視角讀圖也明確拒絕）。讀不到任何一項＝兩個選配面板說 `upstream_unavailable`，其餘照走 |
| **2 canonical skill／prompt／本檔** | 本節；`skills/research-drain` 段 5 補「讀圖缺席 blocker 的下一步是寫讀圖、不得標 settled」；`docs/ARCHITECTURE.md` §6.7（面板、readiness、鏈段需求端）；`CONCEPTS.md`「候選狀態板」「判斷錯了值多少」 |
| **3 最窄 rule** | daily ⑬ 的 argv **不變**（`tests/test_daily_task.py` 逐項相等照過）；不新增 step、不進任何 allowlist；`.codex/rules` 仍是 0 條；APP 不新增路由（個股頁多三個面板，同一個 GET） |
| **4 contract test** | `tests/test_stock_page_phase3.py`（downside 歸屬與落格、個股頁與候選板同一推導、三種缺席、讀圖升核心兩個方向＋圖變動端到端、鏈段需求端、三題稽核格是同一個 Datum、bet 三段純文字、history_not_comparable 對稱面）；`tests/test_analyst_view.py`（封閉清單、INJECTED_PANELS）；`tests/test_argument_layer.py` |
| **5 端到端 smoke** | 見 Step 3.7 的合併驗收（真實資料 materialize、readiness 前後對照、鏈段逐檔比對、headless Edge 渲染 AXTI 與無敘事一檔） |

### Sandbox impact review 結論（2026-10-06：心跳段 3 加「等你提供的文件 N 份」；source-trace 預設改開口）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 心跳段 3 多一行、快照多一鍵 `pq2.source_trace_review`：數的是 `engine_b.todo.active_items()` 裡 `type == "source_trace_review"` 的筆數——與「球在你手上」同一個 SSOT、同一次 `todo.load()`，**不新增任何讀取面、不寫任何 authority、不連外、不開 subprocess**。skill 的改動只影響互動 session（研究者撞到拿不到的來源時鑄 `source_trace_review` 而不是 park）；daily 裡沒有任何步驟讀 source-trace skill |
| **2 canonical skill／prompt／本檔** | `skills/source-trace/SKILL.md`「付費報告」預設翻轉＋新節「向使用者要文件」（兩種要求、格式、讀後報告）；`.agents/`、`.claude/skills` 副本由 `scripts/sync_agent_skills.py` 同步；本節；Phase 7 failure log #29 |
| **3 最窄 rule** | 無新 rule、無新 allowlist、daily 的 argv 不變；`.codex/rules` 仍是 0 條 |
| **4 contract test** | `tests/test_heartbeat.py::test_documents_awaiting_user_line_counts_source_trace_review_from_todo_ssot`（數字等於 todo SSOT；快照鍵存在）；既有 `test_heartbeat_phase1` 的快照鍵封閉清單測試隨鍵更新照跑 |
| **5 端到端 smoke** | 2026-10-06 本機 `crons\heartbeat.py`：段 3 印「等你提供的文件 0」（pool 裡目前沒有未結案的 `source_trace_review`——這個 0 是「沒人開口」，不是「沒東西要」；第一次開口那天較昨 diff 會亮） |

### Sandbox impact review 結論（2026-09-29，Phase 3 Step 3.6：候選狀態板＋心跳）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `python -m webapp materialize --candidates`：推導、**不寫任何 authority**——讀敘事 ledger（`library/private/alpha/briefs/`）、讀圖對圖（Neo4j bolt 本機，唯讀）、watch registry、thesis lifecycle、Engine C（三題走 `?mode=ro`；四盞燈走唯一串接點 `alpha.providers.wipeout.wipeout_for`（2026-10-01 Step 4.6a 合一；取數仍是 `engine_c.checklist.get_wipeout_inputs`），與單檔 materialize 同一條一般連線，`get_conn` 開庫時會跑建表 DDL；邊緣判定的市值正規化 `alpha/providers/market_normalization.py` 另以 `sqlite3.connect` 開一般連線）、Google Sheet（`spreadsheets.readonly`，已持有判定）、邊緣判定的 FX（同一支 `market_normalization` 經 yfinance 取一次，與同一步 `--beta` 用的是同一個 `get_fx_snapshot`）。Step 4.6 起稀釋燈要印「占市值 %」：新股發行金額有值時（只有 10-K／10-Q 國內申報人）`wipeout_for` 多經同一支 `market_normalization.screen_inputs` 讀本機快照與 registry——**結算幣別是 USD 就不取 FX**（2026-10-01 這 35 檔全是 USD 掛牌），所以單檔 materialize 實際仍不取 FX；哪天出現非 USD 的國內申報人，會走同一個 `get_fx_snapshot`（同一組主機，無新憑證）；只寫 ignored derived cache `library/private/app/state/candidates.json`（atomic）。**無新增網路主機或憑證**：Sheet readonly 與 `--positions` 同一組、yfinance FX 與 `--beta` 同一組、Engine C 是本機檔（2026-09-29 3.6 審查 c9 與覆核更正：原稿把 Engine C 全寫成 `?mode=ro`、漏了 FX，覆核再抓到 FX 的同組來源寫錯）。`engine_b/cli.py::_held` 改呼叫共用的持股身分解析，語意不變（全部持股、含 beta、Sheet 讀不到 fail closed；2026-09-29 實測 pq1 排序對 3.0 基準 12 則逐位相同）。`risk/hard_caps.py` 只匯出判別函式（#17），硬擋行為不變。心跳只多讀一份 state artifact（零網路） |
| **2 canonical skill／prompt／本檔** | 本節與上方 materialize 命令；`skills/alpha-status`（pane 1 候選板照抄 artifact）、`skills/daily-brief`（持久畫面表加候選板、⑬ 命令同步）、`skills/lead-intake`（三題已落地）；`docs/ARCHITECTURE.md` state artifact 段；`CONCEPTS.md`「候選狀態板」 |
| **3 最窄 rule** | daily ⑬ 的 argv 加一個旗標 `--candidates`（`tests/test_daily_task.py` 逐項相等）；不新增任何 step、不進任何新的 allowlist；`.codex/rules` 仍是 0 條。APP 多一個 GET 路由 `/api/v1/candidates`（沒有寫入端點；請求路徑測試四份清單都加了它，含 405 與斷網） |
| **4 contract test** | `tests/test_candidates.py`（持股解析、已持有、五組＋附組、前提四條各一、連結斷了進佇列段、滯留不歸零、組內字母序、rollup 只數、`_held` 語意、`hard_caps` 匯出同一函式）；`tests/test_webapp_candidates.py`；`tests/test_webapp_request_path.py`；`tests/test_heartbeat.py`／`test_heartbeat_phase1.py`（候選行、三題行、歸零旗標彙總、新鍵首日） |
| **5 端到端 smoke** | 2026-09-29：真實資料 `materialize --candidates` → 可開 0／缺 X 0／等回落 1（AXTI）／不要 0／已持有 1（SIVE.ST，宣告缺 X 照留）／非倍率候選 2（COHR、LITE）／無敘事 69、持股解析不到 1（TYO:7803）；`webapp status` 列得出 `candidates`；headless Edge 實際渲染 `#/candidates` 與 positions 頁的候選板連結；心跳較昨印「首日 10 項」而不是 10 個「未讀到→N」 |

### Sandbox impact review 結論（2026-09-29，Phase 3 Step 3.4：短評 v2 與敘事來源的 watch）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | ①`python -m alpha brief <T> --add spec.json` 的副作用**變多**：寫入前讀 Neo4j（讀圖現行狀態，唯讀 bolt）與 Engine C（三題，`?mode=ro`），先在 registry 副本上**預演** watch 登記（任何登記失敗都在 append 之前拒收，ledger 不動；R2-a C1），再 append `library/private/alpha/briefs/<T>.jsonl`，最後正式**寫 `library/leads/event_watches.json`**（`disproof[]` 登記成語意 watch、收掉舊版 active 的、寫處置收據；寫入前先把本公司敘事來源已過到期／date 已到的 watch 做 daily 同一條轉換）；新寫一律 v2。`--retract` 同樣會收 watch。**寫 registry 前先取互動 writer lock**（plan §0.5；daily 也寫這個檔）。②`python -m engine_b.event_watch add` 新旗標 `--wake-brief <co:*>`（kind 限 date／entity_filing_signal／related_entity_signal）。兩者都是互動專用、零 LLM、不寫圖／Engine C／thesis |
| **2 canonical skill／prompt／本檔** | 本節；`skills/research-drain`（新段 `narrative_rewrite` 的 consumer）；`docs/ARCHITECTURE.md` §6.11 v2 段；研究包 `brief_frame` 改 v2（`alpha/models/session_assessor.py`） |
| **3 最窄 rule** | 兩個命令都不進任何無人值守 allowlist；`.codex/rules` 仍是 0 條；daily 的 `DAILY_STEPS` 不變——daily 的 ⑩ `todo sync` 照舊跑 `check_watches`，`wake_brief` 的 date watch 到點會在那一步轉 fired（分到 narrative_rewrite，不鑄號） |
| **4 contract test** | `tests/test_narrative_v2.py`（v2 拒收規則逐條、寫入當下前提、連結不重登、換版／撤回不吞觸及、重寫須處置、wake_brief 兩條路、歸屬以來源）；`tests/test_queue_segments.py`（段序封閉） |
| **5 端到端 smoke** | 2026-09-29：真實 registry 上 `semantic_active` 仍 36、147 筆既有 watch 的 `expiry_class` 一筆沒變；v1 7 行 id 重算 7／7、固定夾具的 `fill_brief` 輸出 sha 等於 3.0 基準；`python -m audit invariants` 13 PASS |

### Sandbox impact review 結論（2026-09-29，Phase 3 Step 3.3：三題、主題等權組、邊緣判定）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | ①`python -m alpha theme-cohort [<TICKER>] [--format json]`：**唯讀**（讀 `library/private/alpha/theme_cohorts/*.jsonl`），零網路。②`python -m engine_b.todo add-theme-cohort --spec <file>`：驗 spec、成員以 registry 嚴格比對解析，**寫 `library/leads/todo_pool.json`**（鑄一個帶凍結 spec＋digest 的 manual 項）。③`python -m engine_b.todo complete-theme-cohort <n>`：讀凍結 spec、比對 digest，**append `library/private/alpha/theme_cohorts/<題材>.jsonl`**，再結案那個編號。②③都是互動專用、零網路、不寫 Engine C／圖／thesis。三題本身沒有新入口：materialize 時由 `briefing/alpha_view/sources.py` 以**唯讀**連線讀 Engine C（`?mode=ro`）；邊緣判定的市值正規化沿用 `alpha/providers/market_normalization.py`（FX 取一次），只在 materialize 跑 |
| **2 canonical skill／prompt／本檔** | 本節與下方「主題等權組」命令段；`CONCEPTS.md` 新增三個詞條（財務三題、主題等權組、邊緣判定）；`docs/ARCHITECTURE.md` read model authority map 加 `three_questions` 列。research-drain／daily-brief 的 consumer 在 3.4／3.6 接 |
| **3 最窄 rule** | ②③寫 pq2 池與 private ledger，**不進任何無人值守 allowlist**；`.codex/rules` 仍是 0 條；daily 的 `DAILY_STEPS` 本 Step 不變（三題跟著既有 ⑬ materialize 跑） |
| **4 contract test** | `tests/test_theme_cohort_pq2.py`（bare go／手寫 receipt 拒收、digest 不符拒收、已 drop 拒收、一般 manual 不受波及）；`tests/test_three_questions.py`（每個缺席出口、PIT、ADR 型不換算、沒有布林結論、邊緣 AND 與無法量）；`tests/test_three_question_inputs.py` |
| **5 端到端 smoke** | 2026-09-29：`python -m alpha theme-cohort` 印「0 組」；73 檔三題試跑每一行都有值或具名缺席；邊緣三態 25／46／2 與 3.0 基準相同 |

主題等權組（互動）：
```powershell
& '.venv\Scripts\python.exe' -m alpha theme-cohort [<TICKER>]                       # 唯讀：現行的組／一檔屬於哪幾組
& '.venv\Scripts\python.exe' -m engine_b.todo add-theme-cohort --spec <spec.json>   # 研究步驟：凍結 spec 進一個 pq2 編號
& '.venv\Scripts\python.exe' -m engine_b.todo complete-theme-cohort <n>             # 使用者 go 之後：比對 digest 才寫 ledger（bare go 拒收）
```

### Sandbox impact review 結論（2026-09-29，Phase 3 Step 3.2：Engine C 機械歷史表＋daily ②b）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 新入口 `python -m engine_c.history_backfill`（回填；互動）與 `... --incremental`（daily ②b，排在 ② ETL 之後）。**網路**：yfinance（`query*.finance.yahoo.com`，與 ② 同一個主機群）、SEC `data.sec.gov`（companyfacts、submissions）與 `www.sec.gov/files/company_tickers.json`（與 ⑫ 基期補值同一組主機）。**寫入**：只寫 Engine C 正式庫的三張新表 `price_history`／`corporate_actions`／`fundamental_history`（可重建的 ETL 觀測；建表由 `engine_c.db._ensure_sqlite_schema` 在開庫時 CREATE IF NOT EXISTS，舊表一欄不動——2026-09-29 以 `PRAGMA table_info` 指紋比對 3.0 基準相同）。不寫人工 ledger、不寫任何 authority、不碰 `.git`、零 LLM、零憑證（SEC 只要 User-Agent）。單檔失敗記進報告、不 fail 整步；全部價格都抓不到才 exit 1（心跳段 1 看得到） |
| **2 canonical skill／prompt／本檔** | 本節；本檔 Engine C 命令段（回填與增量兩行）；`crons/daily_task.py` 的 `DAILY_STEPS` 註解。skill 不動 |
| **3 最窄 rule** | Windows daily 不經 Codex，`.codex/rules` 仍是 0 條，不增不減；新命令字串只進 `DAILY_STEPS` 這一個封閉清單 |
| **4 contract test** | `tests/test_daily_task.py::test_daily_steps_are_exactly_the_closed_list`（②b 逐項相等：argv、15 分鐘、writes、network）與 `::test_timeouts_fit_inside_the_task_time_limit`；`tests/test_engine_c_history.py`（PIT、冪等、分割、20-F 只有年度、拒寫原因、落後不寫） |
| **5 端到端 smoke** | 2026-09-29 先對正式庫的 backup API 副本跑全體回填（73 檔價格、EDGAR 43 檔寫入／29 檔無 CIK／CDNS 落後 89 天不寫），再在 writer lock 下對正式庫跑；台股月營收以既有 `python -m engine_c.monthly_revenue --backfill 48` 補到 2022-09（TPEX 2022-10 一個月 MOPS 逾時，報告列出）。回填報告：`docs/reports/2026-09-29-phase3-step32-backfill.md` |

### Sandbox impact review 結論（2026-10-01，Phase 4 Step 4.6：`fundamental_history` CHECK 遷移）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 新入口 `python -m engine_c.migrate_fundamental_metrics`（**互動專用、一次性**；預設 dry-run 只印列數與缺的字彙）。`--apply`：先取互動 writer lock（被占用 exit 2，不等、不搶）→ sqlite3 backup API 把正式庫（WAL）整份備份到同目錄 `backups/<stem>.pre-metrics-<UTC>.db`（`quick_check`＋`fundamental_history` 列數與內容摘要相同才算備好；不覆寫既有備份）→ 一個 `BEGIN IMMEDIATE` 交易內建新表、整表複製、對帳、換名、補索引、再對帳——任何一步不符就 rollback，正式庫一字不動（exit 3）→ 收據 JSON 寫在備份旁。只動 `fundamental_history` 一張表的 CHECK；不寫人工 ledger、不寫任何 authority、不連網、不碰 `.git`、零 LLM、零憑證。冪等：已是新字彙就印「不需要遷移」 |
| **2 canonical skill／prompt／本檔** | 本節；本檔 Engine C 命令段。skill 不動 |
| **3 最窄 rule** | **不進任何無人值守 allowlist**：daily 不跑它，`.codex/rules` 仍是 0 條。daily ②b 的既有命令不變；未遷移的庫上它只略過兩個新指標並計數（`summary.late_metrics_skipped`，daily 印得出來），其餘指標照寫——不會因 CHECK 而整批 `outcome=error`。落在本機既有的 `Bash(python *)` 之下，補償控制＝dry-run 預設＋writer lock＋備份對帳＋單交易 rollback |
| **4 contract test** | `tests/test_engine_c_equity_issuance.py`（未遷移只略過並計數；備份／重建／對帳／冪等／不覆寫備份；對帳不符 rollback 且舊 CHECK 原樣；新 CHECK 收得下新指標）；`tests/test_engine_c_history.py::test_metric_vocabulary_is_the_same_in_sqlite_postgres_and_schema_sql`（SQLite DDL、`schema.sql`、Postgres 遷移檔三處字彙相等；Postgres 走版本化檔 `engine_c/migrations/20261001_add_equity_issued_value_metric.sql`，已套用的舊檔不改） |
| **5 端到端 smoke** | 2026-10-01：正式庫 dry-run（5637 列、缺 2 個字彙）；正式庫 `--apply` 被執行環境的權限檢查擋下，**未遷移**。整條入口改在副本上跑完：`?mode=ro`＋backup API 複製 → `--db <副本>` dry-run → `--apply`（5637 列、摘要前後相同、table_info 指紋不變）→ 再跑一次印「不需要遷移」→ 非增量 EDGAR 回填兩輪（舊指標 5637 列逐列相同）→ 逐檔燈色（`docs/reports/2026-10-01-phase4-baseline.md` §22）。同日 23:25 經使用者授權，正式庫照同一順序跑完：`--apply`（5637 列、摘要前後相同，收據在 `library/private/engine_c/backups/`）→ 互動 writer lock 下非增量回填 → 舊指標逐列相同、逐檔燈色與副本 73 檔相同 |

### Sandbox impact review 結論（2026-09-29，Phase 3 Step 3.1c：兩支唯讀 CLI 退役）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `python -m query.coverage_gaps`、`python -m query.duplicate_nodes` 兩個命令字串**退役**：`__main__` 只印退役訊息到 stderr 並 exit 2（不連 Neo4j、不讀任何檔、不寫任何東西）。模組裡的掃描與分桶函式（`scan`、`bucketize`、`pair_candidates`…）照留，`query.graph_walk.collect()` 照舊呼叫。**純收緊，零新增**：沒有新網路主機、新憑證、新寫入 |
| **2 canonical skill／prompt／本檔** | 本節；本檔「Web App／API」命令清單與 materialize 表那一列；`skills/research-drain` 第三段（⑨ 的逐字對照改看走圖第 9 型）、`skills/daily-brief`（覆蓋缺口一句）。skill 的 `name`／`description` 未變，不需重跑 `sync_agent_skills.py` |
| **3 最窄 rule** | 兩個命令字串從未進過任何 unattended allowlist（`git grep` `.codex`／`.claude`／`config`／`crons`／`deploy` 為 0）；`.codex/rules` 仍是 0 條，不增不減 |
| **4 contract test** | `tests/test_duplicate_nodes.py::test_the_retired_clis_say_so_instead_of_exiting_quietly`（兩支都 exit 2、stderr 指回走圖）；`::test_the_queue_segment_points_at_a_consumer_that_really_mentions_it`（skill 不得再叫人跑 `-m query.duplicate_nodes`）；逐字到得了輸出的三條測試改驗走圖 markdown |
| **5 端到端 smoke** | 2026-09-29 實跑：兩支舊命令 exit 2；`python -m query.graph_walk` 第 9 型逐對印兩端逐字（例 `tech:eml` ↔ `tech:inp_eml`）與射程段；daily 不跑這兩個命令，不受影響 |

### Sandbox impact review 結論（2026-09-26，Phase 2 Step 2.6：走圖取代 coverage）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | daily ⑬ 的命令字串 `-m webapp materialize ... --coverage ...` → `... --graph-walk ...`（**同一個入口的旗標改名，不是新入口**；舊旗標不留別名）。`--graph-walk` 跑 `query.graph_walk.collect()`：本機 Neo4j bolt 唯讀（邊、全部節點 id、coverage 掃描、重複節點掃描，同一個 session）＋讀圖 ledger（`library/private/alpha/structure_readings/*.jsonl`，唯讀）＋`library/leads/pending_leads.json`（唯讀）。**只寫** `library/private/app/state/graph_walk.json`（ignored derived cache，atomic）。無新網路主機、無憑證、不寫任何 authority、不碰 `.git`。`python -m query.graph_walk` 是互動／稽核用的新唯讀入口（不在 daily 清單） |
| **2 canonical skill／prompt／本檔** | 本節；本檔「Web App／API」命令與 materialize 表；`skills/research-drain`（第三段改成走圖）、`skills/alpha-status`、`skills/daily-brief`、`skills/system-decompose` 已同步（`python scripts/sync_agent_skills.py`）；`docs/ARCHITECTURE.md` state kind 段 |
| **3 最窄 rule** | Windows daily 不經 Codex，`.codex/rules` 仍是 0 條，不增不減 |
| **4 contract test** | `tests/test_daily_task.py` 的 `DAILY_STEPS` 逐項相等斷言同一個 commit 改；`tests/test_webapp_graph_walk_watches.py` 斷言舊路由 `/api/v1/coverage` 回 404、`#/coverage` 不在 nav；`tests/test_graph_walk.py` 守 `query/` 只有 `graph_walk.collect()` 一處 import `alpha/` |
| **5 端到端 smoke** | 2026-09-26 實跑 `python -m webapp materialize --graph-walk`：`graph_walk.json` 約 190 KB、九型與 `python -m query.graph_walk` 同數；`python -m webapp status` 列 `graph_walk`、不列 `coverage`；`python -m crons.heartbeat` 段 3 印九格走圖行；`python -m audit invariants --only QueueSegments` 讀得到 `graph_holes`（不再是三段「未讀到」） |

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.2a：一個 Windows daily）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | **可執行面＝`crons/daily_task.py` 的 `DAILY_STEPS` 這份封閉清單**（程式寫死、無 LLM 選命令；1.2a 時兩個 LLM 步驟由 `llm.executor=none` 記 skipped）。每步 `shell=False`、venv python、cwd＝repo root。**連網主機與憑證與原 Codex daily 相同**：X API、SEC（`www.sec.gov`、`data.sec.gov`）、TWSE／TPEx／MOPS（harvest 的重訊 watcher：`openapi.twse.com.tw`、`www.tpex.org.tw`、`mopsov.twse.com.tw`，公開、無憑證；月營收刻意不在 daily——歷史頁永久可查，維持互動入口）、Yahoo／yfinance（含 `webapp materialize --scorecard` 取價；上限 `MAX_PRICED_SYMBOLS` 由 `engine_b/account_scorecard.py` 在程式裡執行，不只寫在這裡）、Google Sheet（`spreadsheets.readonly`；⑥ 的 `--by-priority` 也讀它）、Discord webhook、X 圖片快取 `pbs.twimg.com`（harvest `cache_media`，寫 `library/private/lead_media/`；R2-a NB-4 補列，舊 rules 的 justification 也漏了它）、本機 Neo4j bolt（`NEO4J_PASSWORD`，只讀：⑬ materialize、⑭ 健康審查、⑮ invariants、⑯ 備份匯出）、harvest 的 feed 主機（`crons/harvest_config.json` 的 `feeds[].url`：`mfn.se`、`www.sivers-semiconductors.com`、`feeds.finance.yahoo.com`）；**不含 Drive**（`backup_private.py run --no-drive`；2026-10-06 起含 Drive，見該日的 review）。Anthropic（`claude -p`）要到 Step 1.3 才加。**寫入範圍**：`library/leads/` 四份 state 與鎖／收工標記、Engine C private runtime（etl、FX、beta technical、XBRL 基期補值四支，不新增寫入者）、`library/private/decision_lab/` 的 `portfolio_risk_snapshots.jsonl` 與 `outcome_aggregate.json`／`.jsonl`（**不含任何 `*.db`**）、`library/private/app/`、`library/private/backups/`、`library/private/heartbeat/`（執行紀錄、心跳、capture 檔、log）。**不寫 git、不寫任何 tracked 檔**（保險檢查只讀 git，且一律帶 `-c core.fsmonitor=false`）。**Discord 發送授權**由 Windows daily 持有（原本授權給 Codex daily automation）；每一條限制由 `notifications/publisher.py` 強制（host、logical channel `private-investing`、content class `full_private`），不靠 prompt。⚠ publisher 擋不住「`.env` 的 webhook 被換成另一個 Discord webhook」——所以保險檢查比對 `.env` 指紋。 |
| **2 canonical skill／prompt／本檔** | 本節與上面兩節；`docs/ARCHITECTURE.md` §4.1；`config/daily_routine.json` 的 `schedule._doc`（唯一時間來源）與新的 `llm` 區塊；`crons/daily_brief_prompt.md` 在 Step 1.3 封存（使用者停用 Codex automation 之前它維持 PAUSED）。 |
| **3 最窄 rule** | Windows daily **不經 Codex**，`.codex/rules` 對它不適用；本 Step 不增不減任何 rule（1.3 清為 0 條）。新增的無人值守入口只有 `crons/daily_task.py` 一支；它呼叫的全部是既有腳本，新增旗標只有 `query/health_audit.py --json`（同一組檢查的機器可讀版，不新增任何連線或寫入）。 |
| **4 contract test** | `tests/test_daily_task.py`：`DAILY_STEPS` 與預期 tuple **逐項相等**；清單不得出現 serve、任意欄位寫入者、git、LLM CLI、catalyst_watch、trace-backlog、harvest-health、sweep、drain；各步 timeout 加總 < `execution_time_limit_minutes`；fail-soft、心跳一定跑、exit 0；進迴圈前例外仍組心跳並發送；保險檢查五個 fixture（tracked 檔、HEAD、`.env`、`.git/config`、`.claude/settings.local.json`）各自中止其後全部步驟；`.git/config` 變了不啟動任何 git 子行程；鎖續期（拿掉續期這條測試會紅，已實測）；外人鎖跳過寫入；自我比對三態；register 產的 XML 讀回與 config 相同。 |
| **5 端到端 smoke** | 2026-09-24 實跑 `python crons\daily_task.py`（run `bf21bb07`）：19 步 17 ok、2 skipped（`executor=none`）、約 7 分鐘（materialize 282 秒最長）；harvest 最後一輪＝當天、APP 7 份 state 當天 materialize、publisher 回 `sent` 3/3、鎖已釋放、收工標記 `finalized`。`register_daily_task.py --apply` 後 `StockBotv2-Daily` Ready（下次 05:30）、自我比對 `match`；舊兩個工作 `Disabled`。⚠ 端到端驗收仍要等**真正的排程觸發**（1.2b 的前提：`LastTaskResult 0` 且當天執行紀錄完整），手動觸發不算（L13-1）。 |

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.10：稽核改讀新 registry）

**不新增無人值守可執行面**：`DAILY_STEPS` 與各步 argv 不變，不新增主機、憑證或寫入檔案。行為變化只在 ⑩ `engine_b.todo sync`、
寫的是它本來就在寫的 `library/leads/event_watches.json`：喚醒目標只有一個、而那個目標已結案的 active watch（`wake_pq2` 指向已結案編號、
`wake_lead` 指向 applied／triaged_no_go 的 lead）轉 `consumed` 並記 `closed`（`pq2_item_gone`／`lead_closed`）——與它醒來或到期時
既有的處置同一個結論，只是提早到目標消失的那一刻（NB2-12）；編號或 lead 不存在的不收（資料錯，由 `audit` Orphans 現形），leads 讀不到
就整個不動追源型。sync 輸出多一句「收掉叫醒目標已結案的 N」。`audit/` 只讀，不在任何無人值守步驟裡。
契約測試：`tests/test_audit_waiting.py::test_sync_closes_waits_whose_only_consumer_is_gone`；首跑（2026-09-24 互動、writer lock 下）收掉 8 筆。

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.8：心跳改版）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `DAILY_STEPS` 只改 ⑱ 的 argv：`-m crons.heartbeat --out {brief} --summary-out {summary_file} --write-snapshot`。心跳仍**零 LLM、零網路**：新讀的全是本機檔——⑭／⑮ 的 capture、`library/private/backups/last_backup.json`（`briefing.sources.load_backup_status`，APP 首屏同一支）、registry、leads、`docs/reports/` 檔名（題材掃描日期）、`config/daily_routine.json` 的 `theme_scan`。**新增的寫入只在 `library/private/heartbeat/`**：`heartbeat_<日期>.summary.txt`（摘要行）與 `snapshots/<日期>.json`（留 14 天，舊的刪）；都是 derived，不是 authority。⑲ 的 `--summary` 由 daily 讀那個摘要檔（讀不到退回「每日心跳」），不新增主機。⑬ `materialize --positions` 多讀一次 Google Sheet（`spreadsheets.readonly`，daily 原本就有的憑證與主機）產 `nav_exposure`，寫的仍是 `library/private/app/state/positions.json`。⑯ 備份本機保留 3 → 7 份。 |
| **2 canonical skill／prompt／本檔** | 本節；ARCHITECTURE §4.1（心跳改版那一段）；`config/daily_routine.json` 的 `theme_scan._doc`。 |
| **3 最窄 rule** | 不經 Codex，`.codex/rules` 維持 0 條。心跳不 import `audit/`、不碰 Neo4j（`tests/test_heartbeat.py::test_heartbeat_does_not_import_any_llm_or_network_surface`）。 |
| **4 contract test** | `tests/test_daily_task.py`：`DAILY_STEPS` 逐項相等（含 ⑱ 新 argv）；`tests/test_heartbeat_phase1.py`：快照鍵的字彙與 SSOT 相等（lead 狀態、thesis 狀態、tier、到期處置）、第一天與斷天的 diff、保留 14 天、段 1 三行的缺席分型、題材門檻兩側與橫幅、pq2 逐筆字串等於 `GO_AUTHORIZATION`、到期行加總、摘要行紅旗、NAV 三態與「槓桿」註記、⑲ 的摘要讀檔與退回。 |
| **5 端到端 smoke** | 2026-09-24 實跑 `python -m crons.heartbeat --out %TEMP%\hb.md --summary-out %TEMP%\hb_summary.txt`：五段齊全、摘要行 `Daily 2026-09-24｜球在你 0｜⚠ 健康紅燈 1`；`materialize --positions` 後 NAV 行為真實 bucket 分布。與 1.0 存的心跳逐行對照：每一條拿掉的行都有取代行（「本輪該查」是 T2 輪詢配額，輪詢 1.2a 已移出 daily，故不再印）。 |

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.7：到期處置）

**不新增無人值守可執行面**：`DAILY_STEPS` 與各步 argv 不變，不新增主機、憑證或寫入檔案。行為變化只在兩個既有寫入步驟、
寫的都是它們本來就在寫的檔：⑨ `engine_b.cli consume-fired` 多做「追源型到期」——`expires` 已過的 watch 轉 `expired`、
parked lead 的 `trace_status` 轉終局 `watch_expired`（`library/leads/pending_leads.json`）、watch 記 `expiry_resolution`
（`library/leads/event_watches.json`）；⑩ `engine_b.todo sync` 多鑄 `watch_decision`（只有假設型等沒有自己複查週期的到期，A7；thesis／讀圖來源的列進 thesis 複查項目與節點重讀理由；CLI 先跑 thesis 反證對帳再收集；對帳讀不到 `thesis/lifecycle.json` 時整輪不動任何等待）、把 pq2 型到期指向的
編號翻回球在你（`library/leads/todo_pool.json`）、讀圖型到期與「memo 已被取代」的到期只記處置。**`watch_decision` 永不列入常規授權**
（`config/standing_authorization.json` 的 `never`），無人值守路徑不會替使用者按它的 `go`／`drop`／續等；`go` 必附指得回的研究結果，
不授權任何 authority mutation。互動路徑：`python -m engine_b.todo resolve <n> --verb pending --until <日期>`（續等）／`--verb drop`／研究後條件已被觸及：`--verb go --receipt "outcome:touched;report:<docs/reports 或 thesis 下、內文提到該 watch 的 .md>" --quote "<原文>"`。

**試跑（2026-09-24 起的常規做法）**：改到等待系統（到期、喚醒、反證登記、心跳段 2／3）時，交付前跑
`python scripts/trial_run_waiting.py [--until <日期>]`——拿真實 registry／待辦池／leads 的暫存副本（`library/private/trial_runs/waiting/`）把「今天」逐個事件日快轉，跑 ⑨⑩ 與心跳相關行，並模擬一次續等／放棄／判定觸及；真檔 byte 不變（腳本結尾檢查）。它換掉模組時鐘，**不得**放進任何無人值守步驟；輸出是試跑，不是「已生效」的證據。

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.5：反證登記 hook）

**不新增無人值守可執行面**：`DAILY_STEPS` 不變。⑩ `engine_b.todo sync` 多做一件事——thesis 反證對帳
（`engine_b/disproof.py`），寫的是 ⑩ 本來就在寫的 `library/leads/event_watches.json`；讀 `thesis/lifecycle.json`、
現行 memo 與 sidecar（唯讀）。心跳段 2 多一行反證計數：全部本機讀取（registry、lifecycle、memo、讀圖 ledger、
harvest 設定、凍結舊店以 `mode=ro`），零網路。讀圖 `--add` 後的等待登記只在互動 session 發生。
`thesis/pending_lifecycle.py`（thesis mutation 的人工 gate contract）一個字未動。

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.4：語意條件 watch ＋ 語意預篩）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | `DAILY_STEPS` 加三步：⑩a `-m engine_b.event_watch prescreen-prepare`（程式，連網）、⑩b 預篩提議（`claude -p`，**與 ⑦a 同一個呼叫函式、同一組 argv、白名單、能力檢查**；只回標旗 JSON）、⑩c `-m engine_b.event_watch prescreen-apply`（程式驗引文逐字後**只寫 `semantic_flag`、不改 watch 狀態**）；⑩b 後另一道保險檢查。**新增的連網只到既有主機**：`www.sec.gov`（EDGAR 主文件，`fetchers/edgar.py:fetch_filing_text`）與 `mfn.se`（公告頁；`engine_b/semantic_prescreen.py:fetch_mfn_text` 只取頁面文字）——**不含 `mb.cision.com`**（不抓 MFN 的 PDF 附件；`fetchers/mfn.py:fetch_release` 會抓，所以不用它）。**新增的寫入只到 `library/private/`**：`semantic_text/<lead_id>.txt`（＋sha256 meta，已存在就重用）、`heartbeat/prescreen_batch_<日期>.json`／`prescreen_<日期>.json`；⑩c 寫 `library/leads/event_watches.json` 的 `semantic_flag`（寫入步驟，在 daily 的鎖底下）。harvest 多寫三個 lead 頂層欄位（`source_class`／`company_id`／`form_type`，由 feed 宣告或 EDGAR／MOPS 固定值），不新增主機。 |
| **2 canonical skill／prompt／本檔** | `crons/prescreen_prompt.md`、`crons/prescreen_schema.json`（新，strict）；`config/event_watch.json` 的 `_doc` 與 `semantic_screen_daily_limit`／`prescreen_text_max_chars`／`ownership_forms_excluded`；`crons/harvest_config.json` 每個 feed 宣告 `company_id`／`source_class`；本節；ARCHITECTURE 決策表那一列。 |
| **3 最窄 rule** | 不經 Codex，`.codex/rules` 維持 0 條。預篩額度由 CLI 截斷（`semantic_screen_daily_limit` 扣當日已標旗），不寫進 prompt。 |
| **4 contract test** | `tests/test_daily_task.py`：清單相等含 ⑩a–⑩c、⑩b 與 ⑦a 同一條 LLM 路徑、以 `run_id` 配對；`tests/test_semantic_watch.py`（新）：kind × 喚醒目標、T0 矩陣（一手 8-K 命中、Form 4 即使 tier=1 不命中、secondary 不命中、X 不命中、未 triage 的 MFN 公告命中、ISO／RFC 822 回補舊文件不命中）、登記驗證、預篩名額（每日、無 fetcher 不佔名額）、只連 `mfn.se`、引文逐字、`run_id` 不符一則不寫。 |
| **5 端到端 smoke** | 回填實跑：`backfill-entities --provenance` 補 EDGAR 419、MFN 64、sivers 26、yahoo 26、MOPS 4、X 514，第二次 0（冪等）；Sivers 兩個 feed 的 lead 含 `co:sivers_semiconductors` 由 0 → 100%。真實資料上醒來的語意 watch 目前 0（1.6 才登記條件）——預篩照實印「預篩 0」，不造假資料觸發。 |

### Sandbox impact review 結論（2026-09-24，Phase 1 Step 1.3：triage 併進 daily、Codex 退出無人值守）

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 新增的無人值守能力只有一個：⑦a 以 `claude -p` 呼叫 Anthropic（**訂閱登入**，`apiKeySource == "none"`）。**LLM 手上沒有任何工具**：`--tools ""`（只剩 `--json-schema` 帶進來的 `StructuredOutput`）、`--strict-mcp-config`、`--setting-sources ""`、`disableAllHooks`、`autoMemoryEnabled:false`、`--disable-slash-commands`、`--include-hook-events`；cwd＝repo 外的空目錄（`llm.cwd`）；環境變數白名單 10 個鍵，不帶任何憑證（含 `ANTHROPIC_API_KEY`——漏進去會改走 API 計費）。規則與批次由程式組成 prompt 從 stdin 餵，LLM 不讀檔、不跑命令。**每次執行**邊讀 stream 邊檢查 init 的能力欄位（六欄缺席算不符、`memory_paths` 出現算不符、任何 `hook_started` 算不符），不符就殺行程樹、丟棄輸出、不寫結果檔。寫入由 ⑦b `engine_b.cli triage-apply` 做（同一個 `leads.triage()`；逐則驗證、收據帶 `decided_by`）。新增的寫入只在 `library/private/heartbeat/`（結果檔）與 `library/leads/pending_leads.json`（⑦b，與 CLI `triage` 同一條路徑）；`claude -p` 自己的 session 紀錄在 `~/.claude/projects/<以 llm.cwd 命名的目錄>/`（供稽核）。 |
| **2 canonical skill／prompt／本檔** | `crons/triage_prompt.md`（新）、`crons/triage_schema.json`（新）、`skills/signal-triage/SKILL.md`（判準加起訖標記，由程式逐字截取）、`skills/daily-brief/SKILL.md`（改成互動專用）、`crons/daily_brief_prompt.md` 逐字封存 `docs/archive/2026-09-24-codex-daily-brief-prompt-v1.8.md`、本節。 |
| **3 最窄 rule** | `.codex/rules/stockbot-automations.rules` **12 → 0 條**：Codex 不在任何無人值守步驟裡。⚠ 刪 prompt 不是保證；**真正的保證是 rules 0 條＋使用者停用兩個 Codex automation**。 |
| **4 contract test** | `tests/test_daily_task.py`：LLM argv 逐項相等、禁用旗標不出現、cwd＝`llm.cwd`、白名單擋得住 `ANTHROPIC_API_KEY`／`NOTIFY_*`／`X_*`／`CLAUDECODE`、能力檢查每種不符（六欄各自缺席、`memory_paths` 出現、hook 事件在 init 前後）都丟棄輸出且 init 不符時在 result 前就殺、分批任一批不符整步丟棄、同日舊結果檔先刪、`subtype: success`＋`is_error: true` 判失敗、`rate_limit` 非 allowed 才算額度問題。`tests/test_triage_apply.py`（新）。`tests/test_codex_daily_permissions.py`：prefix 數＝0、舊 12 條逐條以 execpolicy parser 驗非 allow；原本掛在 rules 上的判準（materialize 不含 serve、XBRL 只寫一個欄位、scorecard 網路上限在程式裡、重訊主機寫出來、月營收留在互動）改主詞搬到 `tests/test_daily_task.py`。 |
| **5 端到端 smoke** | `llm.executor` 改 `claude` 後以 `schtasks /Run /TN StockBotv2-Daily` 走真正的排程路徑跑一次（結果記在 plan 進度表與 Step 1.3 的八欄）。 |

### Sandbox impact review 結論（2026-09-17，Phase 2 Step 2.2：研究層移出 Daily）

五步：

1. **path＋side effect＋capability**：
   - `crons/heartbeat_task.py`（**新的無人值守入口，但不在 Codex sandbox 裡**）：由 Windows 工作排程直接執行，
     不經 Codex，所以 `.codex/rules` 對它不適用。它讀本機 authority 與 materialize 好的 state artifact，
     寫 ignored 的 `library/private/heartbeat/`（Markdown ＋ log），再以 subprocess 呼叫**既有的**
     `scripts/publish_daily_brief.py`。**無新增網路主機**（只有既有的 Discord webhook）、**無新增憑證**
     （`.env` 既有）、不寫任何 authority、不碰 `.git` 或任何 tracked 檔。
   - `crons/heartbeat.py` 本身：零網路、零 LLM，由測試在原始碼層強制
     （`test_heartbeat_does_not_import_any_llm_or_network_surface`）。
2. **canonical skill／prompt／本檔**：`crons/daily_brief_prompt.md` v1.7 → v1.8（檔頭三層分工表、
   fixed entry 列舉、步驟 5 整段停用並以 `<details>` 保留原文）；`docs/ARCHITECTURE.md` §4.1；本節與上面的心跳節。
3. **最窄 rule**：`.codex/rules` 由 20 條**減為 15** 條。移除的五條是研究層專用：
   `fetchers\edgar.py`、`fetchers\mops.py`、`engine_b.cli drain`、
   `scripts\prepare_research_action.py --action-file`、`engine_b.todo work`。
   **這一步是純收緊，沒有任何新增**——心跳不經 Codex，所以它一條 rule 都不需要。
   ⚠ fetchers 目錄現在**一支都不在列**（原本 edgar／mops 在列）。
4. **permission contract test**：`tests/test_codex_daily_permissions.py` 同 change 對齊——條數斷言 20 → 15、
   五條從「必須存在」改成「必須不在」，並**加進 `test_adjacent_privileged_commands_remain_outside_the_allowlist`
   的 parametrize，由 Codex 自己的 execpolicy parser 證明它們真的不再被允許**（不只是「rules 檔裡找不到那串字」）。
   `test_fetchers_directory_is_not_broadly_allowed` 由「只放行兩支」翻面成「一支都不在列」。
5. **smoke test**：`crons/heartbeat_task.py --dry-run` 產檔通過；**接著以 `schtasks /Run` 走真正的排程路徑
   實跑一次**——`Last Result: 0`、publisher 回 `{"status": "sent", "sent_parts": 2, "total_parts": 2}`。
   ⚠ 端到端驗收仍未完成：ROADMAP Phase 2 要的是**連續 3 天 07:00 自動發出**，那要等三天，
   不得以「手動觸發成功」冒充（L13-1：驗收條件是產出出現在下游消費者手上）。

不放寬：四個人工 gate 一個不動；心跳不寫任何 authority；研究搬到互動 session 之後**判準一字未改**
（disproof 三件套、park 的四個欄位、只有 prepared RA 才進 pq2）——**搬走的是執行者，不是規則**。

### Sandbox impact review 結論（2026-09-22，Phase 0 Step 0a.1：decision_lab 研究側停跑）

**純收緊，零新增。** 五步：

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 沒有任何新增的 path、side effect 或 capability。移除的兩條 entry 原本各自的 surface：`-m decision_lab today`（讀 Google Sheet／Neo4j／private Decision Store，產 decision brief）與 `-m engine_b.todo reassess-stale`（同一組資源，對 `decision_review` append 新 decision）。兩者的機制都退役（ROADMAP Phase 0／G3、G12），移除後**無任何無人值守呼叫端**。 |
| **2 canonical skill／prompt／本檔** | `crons/daily_brief_prompt.md` 同 commit 移除兩個步驟、fixed entry 列舉與機械段計數器的 `reassess 結案 b` 欄；`crons/weekly_scan_prompt.md` 的 `today` 改指心跳；本節。`skills/daily-brief/SKILL.md` 等研究 skill 在 Step 0a.3 一併改。 |
| **3 最窄 rule** | `.codex/rules` 由 14 條**減為 12** 條。**沒有新增、沒有放寬任何既有 pattern。** `standing-go` 那條的 surface 同時變窄：`config/standing_authorization.json` 的 `authorized` 從兩種（`decision_review`＋`source_trace_review`）減為一種，`decision_review` 移到 `never`（不是刪掉——ITEM_TYPES 封閉性要求每種都明寫在其中一邊）。 |
| **4 permission contract test** | `tests/test_codex_daily_permissions.py` 同 commit：條數斷言 14 → 12（兩處），兩條從「必須存在」**翻面成必須不在**，且比對的是 `pattern=[...]` 內容而不是整份檔案的字串——檔頭的退役註記刻意寫出它們的名字，用字串存在與否來驗會讓「退役」與「沒退役」同形（L13）。`tests/test_standing_authorization.py` 的斷言同樣翻面：`set(authorized) == {"source_trace_review"}`，且 `advance_decision_review` 在 `standing_go` 裡一次都不得被呼叫。 |
| **5 端到端 smoke** | `python -m audit invariants --only QueueSegments` 綠且輸出不再有 `reassess_stale` 段；`python -m engine_b.cli counts` 正常；`python scripts/analyst_view_text_digest.py` 與全測試（2823 passed／1 skipped，與 Step 0.0 基準同數）未動。⚠ **未跑真正的排程路徑**：daily 由 Codex desktop 觸發，下一次是 2026-09-23 06:30——這一條要等那一輪才算驗完（L13-1：驗收是產出出現在下游消費者手上）。 |

排程收尾跑 `scripts/finalize_daily_state.py`：驗證四份本機 state、釋放自己的 writer lock、
寫收工標記。它不碰 Git、不連網，因此留在 workspace-write 且不占 unattended allowlist。
四份 state（`pending_leads.json`＋`todo_pool.json`＋`event_watches.json`＋`hypotheses.json`）
由 `.gitignore` 明確排除並納入 private backup。

**追源證據隨引用一起備份（2026-09-19）：** `engine_b_state.zip` 同時收進**被 state 指名引用、
且確實存在**的 `library/raw/` 原文。集合由 state 推導，**不是把 `library/raw/` 整目錄打包**；
缺檔、路徑穿越或 private 路徑一律 fail closed，restore 驗證會重算同一集合。
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

⚠ `--only PointInTime` 會**實跑一次 as-of 投影**（取「最新證據日 −60 天」當 `as_of`），
驗它沒有漏出未來的證據。所以它比其他 check 慢一點，也需要 Neo4j 開著。

### SourceDoc 定日回填（mechanical，不需 pq2）

```powershell
python scripts/backfill_source_dating.py --list          # 誰還沒定日、擋住幾條 assertion
python scripts/backfill_source_dating.py --batch loader/manifests/<file>.json --dry-run
python scripts/backfill_source_dating.py --doc-id <id> --value 2026-02-03 `
    --method url_path --basis "URL 路徑 fool.com/.../2026/02/03/"
```

判準與四道補償控制見 `AGENTS.md` 記憶層那段與 `loader/source_dating.py` 的 docstring。
**這支寫不進任何 claim、邊或判讀屬性**——那些仍走 graph admission（pq2）。
`--dry-run` 只驗不寫；已有值時要改必須 `--supersede`（舊值會留在 basis 裡）。
回填紀錄留在 `loader/manifests/sourcedoc-dating-backfill-<date>.json`（可重放）。

### 排序前段 vs 後段的等權報酬（已退役）

`scripts/rank_forward_returns.py` 已於 2026-09-23 Phase 0 Step 0b.3（`7db4e1f`）隨排序退役刪除，**沒有替代命令**。
當時的實測：期數個位數、標的高度集中在 AI 光互連，第一期幾乎全由 `SOI.PA` 一檔決定。
報酬回測不重建，理由見 ROADMAP Phase 5（2026-10-02 amendment）。
問得太早時 as-of 保險絲會拒絕該期，那是正確行為，輸出會列出被拒的期數。

### Writer lock（雙向互斥，2026-09-02）

同一 working tree 的排程與互動 session 靠 `library/leads/.writer_lock.json`
（gitignored，`engine_b/writer_lock.py`）互斥，取代原本只有互動側的時間窗單向避讓：

- **排程側**：`crons/harvest_leads.py` 一般 harvest 開跑 acquire `scheduled`（TTL 90 分，
  依 2026-09-02 量測 daily 中位 19 分／p90 30 分／最長 43 分取兩倍餘裕）；
  `scripts/finalize_daily_state.py` 收尾 release（結果附 `writer_lock_released`）；state 驗證失敗
  仍釋放自己的鎖並留下 `state_invalid` 收工標記，避免錯誤路徑把鎖留到 TTL。
  互動 session 持鎖時 `crons/daily_task.py` 開頭就拿不到鎖 → **跳過所有寫入步驟**、心跳照發並在段 1 印出原因
  （2026-09-24 Phase 1 Step 1.2a；每個寫入步驟前以同一 owner 續期，續期失敗其後的寫入步驟也跳過）。
- **互動側**：長時間寫入前 `python scripts/writer_guard.py acquire --minutes N --purpose "…"`，
  收尾 `release`；`check` 同時看排程時間窗與鎖（鎖補上時間窗防不了的延遲開跑——
  2026-08-29 排程 08:21 才收尾的那種）。互動手跑 harvest 時用
  `STOCKBOT_WRITER_OWNER=interactive` 表明身分，避免與自己持有的鎖互撞。
  **工具內部要持鎖一律用 `with writer_lock.hold(...)`**，不要自己 acquire／release：同 owner 的外層 session 鎖已在時
  它不續期、不拆（2026-10-03 [671] 的遷移工具自己 release，把使用者的 session 鎖一起拆了——Phase 6 #17，2026-10-04 修）。
- **stale-tolerant**：鎖過期或損毀即可被接手（新鎖記 `superseded` 供稽核）；
  崩潰的 session 最多卡別人一個 TTL。不得手動拆別人的**未過期**鎖。
- **Sandbox impact review 結論（2026-09-19）：** 鎖檔是 repo 內一般檔案（workspace-write
  已涵蓋），無 identity／ACL／網路／credential 副作用；allowlist 15 → 14，刪掉的是會
  push public Git 的 state publisher。acquire 嵌在 harvest fixed entry，release 由
  workspace-write 的本機 finalizer 執行。契約斷言見 `tests/test_writer_lock.py` 與
  `tests/test_daily_state_finalizer.py`。

**Routine 分工：**
- daily（Windows `StockBotv2-Daily` → `crons/daily_task.py`，2026-09-24 起）＝harvest ＋ 外部雷達（2026-10-05 起；`claude -p` 只開 WebSearch 提議、程式驗證後寫 secondary lead）＋ ETL ＋ beta monitor ＋ triage（`claude -p` 零工具提議、程式寫入）＋ 機械段 ＋ materialize ＋ 健康審查 ＋ invariants ＋ 備份 ＋ 心跳；互動 session 說「daily brief」才組含 pq2 建議的長版。~~`crons/daily_brief_prompt.md`~~ 已封存
- ~~weekly~~（2026-09-24 Phase 1 Step 1.9 退役）：題材掃描改互動 skill `skills/theme-scan`（說「掃題材」），報告 `docs/reports/theme_scan_<日期>.md`；健康審查、thesis 唯讀提醒、投組風險快照由 Windows daily 接手；舊 prompt 封存於 `docs/archive/2026-09-24-weekly-scan-prompt-v1.2.md`

兩者刻意錯開，且都不替使用者寫 thesis 結論、入圖或建立 live facts。

### 自主研究迴圈（2026-08-29 建立；互動 session 內由使用者觸發）

**Trigger：** 使用者說「跑自主研究迴圈」（單輪）或「/loop 自主研究」（連續、agent 自排程、
使用者隨時打斷）。**不設 cron、不進無人值守排程**——它與 daily 共用 working tree，
必須由互動 session 承載才能遵守 single-writer 契約。

**每輪固定形狀：** 從題源挑一題 → bounded research → 留 receipt（park／prepared RA／
Engine C 提案）→ 報告本輪產出與下一題。**所有 authority mutation 照常停在 pq2**：
迴圈只堆 packet，不 apply、不 complete、不改 lifecycle、不動 registry（onboard 亦打包成
`ra_admission` 等 `go`，見 `AGENTS.md`「Onboard 也走 pq2」）。

**題源優先序（確定性，不自創）：**
1. 使用者點名的題（含 decompose 積壓題——選題永遠是使用者的）
2. `trace-backlog` 觸發條件已命中的 parked lead
3. 結構表（`query.bottleneck structure_table`）上仍是 self_reported 的邊（→ 客戶端印證）；跨檔排序已於 2026-09-23 退役（G1）
4. L8 不足公司的第三 origin 狩獵（`_check_source_diversity` < 3 者）
5. `coverage_gaps` 的 🔴 未知供應層
6. 缺五軸 assessment 的 cohort（如 `research_assessment_missing` 者）
7. `single_origin_report` 單源 claim 補強

> ⚠ 2026-09-16：D12 落地後研究只在互動 session 跑，本節就是**唯一**研究路徑（daily 的 drain 歸零）。
> D8「補三格」（已在圖裡的邊緣公司的可替代性／外部印證／瓶頸業務占營收比例）依決定紀錄 §8 排到題源最前——
> 落地隨 ROADMAP Phase 1，落地前題源順序照上表。

**紅線：** ①daily 的寫入窗（台北 05:15–06:45；`python scripts/writer_guard.py check`）內不動 working tree，
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

### 委派唯讀 subagent（已無專用入口）

⚠ **`luna-reviewer` skill 與 `.codex/agents/luna-operator.toml` 已於 2026-09-04 退役**
（實測：2026-08-01 上線、只用過 2 次、之後 34 天／744 個 commit 零使用）。
要用便宜模型做唯讀盤點時，**直接用 harness 原生的 subagent**：Claude Code 的 `Agent`
工具可指定 `model`（`haiku`／`sonnet`…）與唯讀的 `Explore` 型別；Codex 側用它自己的
custom-agent 機制。**不要再包一層 skill** ——那層才是當初重造的輪子。

授權邊界不因此改變（`AGENTS.md`「協作與邊界」）：回傳只是 review packet 不是 authority，
主代理是唯一 writer，所有人工 gate 照舊。

### 待辦池（統一 pq2）
```powershell
& '.venv\Scripts\python.exe' -m engine_b.todo sync          # 同步後列出（＝「待辦事項統整」）
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb go|drop|pending [--reason ...] [--receipt ...]
& '.venv\Scripts\python.exe' -m engine_b.todo resolve <n> --verb pending --until 2026-08-27 --trigger "Q2 財報"
& '.venv\Scripts\python.exe' -m engine_b.todo add "<標題>" [--hint ...] [--company-id co:x]   # 手動項；帶 company_id（名冊驗證）再 pending，每檔閉環才認得是使用者 defer（2026-10-05）
& '.venv\Scripts\python.exe' -m engine_b.todo dispatch <n>  # source_trace_review → pq1 job（decision_review 已於 2026-09-23 退役，legacy 只能 drop）
& '.venv\Scripts\python.exe' -m engine_b.todo work <n> --to researching|completed|parked --receipt ...
& '.venv\Scripts\python.exe' -m engine_b.todo complete-ra <n> --digest <sha256> [--company-id ...]
& '.venv\Scripts\python.exe' -m engine_b.todo complete-observation <n>       # Engine C 人工觀測寫入
& '.venv\Scripts\python.exe' -m engine_b.todo complete-thesis-mutation <n>   # thesis lifecycle 變更
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go [--run]         # 佇列段 2b：常規授權類別（config/standing_authorization.json）直接下使用者本來會下的 go；pending／等世界／付費的不碰
```

`pending` 帶 `--until`／`--trigger` 會歸入「等事件」區，觸發前不佔決策注意力。⚠ **2026-09-26 起 `--trigger` 必須同時帶 `--until <日期>` 或 `--watch <ew_id>`**（那筆 watch 的 `wake_pq2` 必須是這個編號、仍在等）——只有散文 trigger 的等待沒有到期（INV-2），CLI 拒收並印兩種正確寫法；既有項目不回溯改寫。分類判準見 `config/decision_blockers.json` 的 `resolution_mode`。

### Private authority 備份（本機＋Google Drive 異地）

```powershell
python scripts/backup_private.py run             # 完整備份：SQLite＋Neo4j＋private files＋Engine B state＋Drive（daily ⑯）
python scripts/backup_private.py run --no-drive  # 只做本機備份
python scripts/backup_private.py verify-restore  # restore 到暫存＋checksum／integrity 驗證（daily ⑯b）
python scripts/backup_private.py upload          # auth 修好後補上傳最新一份本機備份
python scripts/backup_private.py status          # 印出 last_backup.json
python scripts/backup_private.py auth            # 一次性 OAuth 瀏覽器授權（換 client 或 token 失效時重跑）
```

- **備份對象**是「今天重新取一次拿不回來」的 authority（L10 判準）：Decision Store、Engine C
  authority（`runtime_pointer.json` 指向）、Neo4j 全圖，以及四份 Engine B 本機 state。
  其餘 private 檔案進 `files.zip`；Engine B state 與其指名的 raw provenance 進
  `engine_b_state.zip`。排除 `models/`（可重下載）、`lead_media/`、`gdrive_oauth/`（金鑰不出境）。
- **本機**留 `library/private/backups/`（rotation 7 份，manifest 全 checksum）；**Drive**
  留 `StockBotv2-backups` 資料夾（rotation 8 份，超出移垃圾桶 30 天可救）。
- **無人值守（2026-10-06 起）：daily ⑯ 跑 `run`（含 Drive）、⑯b 跑 `verify-restore`。** 在那之前 ⑯ 一直是
  `run --no-drive`（Phase 1 Step 1.2a 怕 Testing 模式 token 7 天過期而不自動上傳，待決 #5 之後沒人再決定），
  結果 09-10 之後沒有任何一份上 Drive、心跳天天印 `Drive skipped` 卻不亮；10-06 實測 09-10 的 refresh token
  仍可用——consent screen 早已不是 Testing。
- **Drive 憑證是 OAuth user credentials**：`library/private/gdrive_oauth/client_secret.json`
  （Cloud Console `my-project-stockbot` 的 Desktop client）＋`token.json`（`auth` 產生）。
  ⚠ **service account 走不通，不要再試**——2026-08-29 實測 `files.create` 回 403
  「Service Accounts do not have storage quota」，兩條官方出路都要 Workspace。
- ⚠ **consent screen 停在 Testing 模式時 refresh token 7 天過期**；過期不會安靜壞掉：⑯ exit 3（本機那份照留）、
  心跳段 1 備份行亮 `auth_expired`，重跑 `auth` 再 `upload` 補傳。發布 Production 後 token 長效。
- **心跳段 1 的備份行三格**（2026-10-06）：最後備份 N 天前（超過 7 天亮）｜Drive（不是 `uploaded` 就亮，附最後一次
  **成功**上傳幾天前——`drive_last_uploaded` 跨 run 保留）｜還原驗證（**這一份**沒驗過就亮，附最後一次驗是幾天前）。
  從未備份、狀態檔讀不懂也亮。三格的判定只有一份（`crons/heartbeat.py::_backup_problems`），Discord 摘要行用同一份。
  「之後變動未備份 N 檔」只印不亮（daily 自己的執行紀錄在備份之後才寫，平常就不是 0）。
  ⚠ 2026-10-06 之前只有「超過 7 天」會亮：會亮 Drive 與還原驗證的舊 renderer（`briefing/render.py`）早已沒有呼叫端，
  本節原本描述的是它——同一個狀態兩份渲染、規則不同（L16），舊的已刪。

> ⚠ **`decision_review` 的 `go`（全函數：dispatch／reassess／assessment-gap）已於 2026-09-23（Phase 0 Step 0b.4） 隨 decision_lab 研究側退役**：
> `decision_review`／`sheet_only_holding` 是 legacy 型，`go` 一律被拒，歷史項目只能 drop。原文（含三條內部路徑與 `--intent` 註記）
> 逐字封存於 [`archive/2026-09-23-phase0-retired-sections.md`](archive/2026-09-23-phase0-retired-sections.md)。

### Leads
```powershell
& '.venv\Scripts\python.exe' crons\harvest_leads.py                 # 零 token；--dry-run 只印不寫
& '.venv\Scripts\python.exe' -m engine_b.cli consume-fired [--dry-run]  # 佇列段 1：fired 的追源 watch 排回 pq1（機械、零 token；drain 之前先跑）
& '.venv\Scripts\python.exe' -m engine_b.cli drain                  # pq1 依 priority 的下一批（首行印段 0–1 計數器）
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --go --tier N --reason ... --content-type <type> --decision-impact <impact> [--payment-direction <direction>] [--classified-by interactive:graph_walk|interactive:directed]
#   --classified-by：互動 session 自己鑄、自己 triage 的 lead——走圖命中起的用 interactive:graph_walk，使用者點名或 plan 指定題目起的用 interactive:directed（不是走圖產出，量測要分得出來）
& '.venv\Scripts\python.exe' -m engine_b.cli triage <lead_id> --no-go --tier N --reason ...
& '.venv\Scripts\python.exe' -m engine_b.cli classification-health # active 缺分類回 exit 2
& '.venv\Scripts\python.exe' -m engine_b.cli advance <lead_id> <status> [--ref k=v]
& '.venv\Scripts\python.exe' -m engine_b.cli trace-backlog          # parked 追源未果與 trigger
& '.venv\Scripts\python.exe' -m engine_b.cli related <lead_id>      # 共用具名標的的其他 lead
& '.venv\Scripts\python.exe' -m engine_b.cli harvest-health         # 各來源最新未恢復失敗
& '.venv\Scripts\python.exe' -m engine_b.cli onboard-candidates --min-leads 3
& '.venv\Scripts\python.exe' -m engine_b.cli decompose-propose --system "<一台實體>" --anchor <tech:x> --why "<為什麼是新錨>" [--lead <id>] [--dry-run]   # 新需求錨才鑄 pq2；drop 過不重生；open ≤2
```

Leads authority 是本機、Git ignored 且納入 private backup 的
`library/leads/pending_leads.json`；狀態機與 API 見 `engine_b/leads.py`。
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
Engine D 的 identity_registration_pending——已於 2026-09-23（Phase 0 Step 0b.4） 隨研究側退役，完全沒登記的先前無任何浮現路徑）。
cashtag 由 `entities.py` 確定性抽取；公司名寫成純文字時 regex 抓不到，
由研究者在 `onboard_candidate_names` 標註（L15：語意由 LLM 解析，registry 判權限）。
**它只回答「誰一直出現卻不在圖裡」，不回答該不該 onboard**——後者仍走
`skills/company-onboard` 並由使用者決定。

### Engine D（舊 Decision Store，frozen 2026-09-22）
```powershell
& '.venv\Scripts\python.exe' -m decision_lab status              # 表筆數、schema 版本、檔案 sha256（唯讀，mode=ro）
& '.venv\Scripts\python.exe' -m decision_lab history --decisions # 歷史 live 選擇／成交回報與各 cohort 最後一筆 decision（唯讀）
```

研究側命令（evaluate-signal／reassess／today／card／references／record-choice／record-fill）已於 2026-09-23（Phase 0 Step 0b.4） 退役，
舊店只剩上面兩個唯讀窗；成交紀錄與資本硬擋見「記錄成交」；遠端的 `get_decision_brief` 工具同批退役。原命令段封存於 archive。

### Alpha Card（canonical read model，2026-09-05）

```powershell
& '.venv\Scripts\python.exe' -m briefing alpha-card COHR                      # 完整卡（Markdown）
& '.venv\Scripts\python.exe' -m briefing alpha-card COHR --format json -o card.json
& '.venv\Scripts\python.exe' -m briefing alpha-card COHR --no-causal          # 略過路徑／結構事件（較快）
& '.venv\Scripts\python.exe' -m briefing alpha-card COHR --as-of 2026-06-30   # as-of 視角（Engine A 投影＋Engine C 時序）
```

純讀：不 freeze context、不建 decision、不寫任何 authority。session 判斷檔預設找
`library/private/alpha/judgments/<TICKER>.json`（也接受舊的 `<ticker>_judgment.json`）；
判斷是對舊 context 做的時仍呈現但整段標 **stale**，`--strict-judgment` 改成視為無判斷。
（`decision_lab today` 的「Alpha Card 摘要」區已於 2026-09-23（Phase 0 Step 0b.4） 隨研究側退役；APP 個股頁與 `analyst-view` 消費同一份 view。）
架構與 authority map 見 `docs/ARCHITECTURE.md` §6.1。**互動專用，不進 unattended rule。**

### Analyst View（消費端投影，2026-09-07 Step 3.5）

**要「看懂一檔股票」時用這個，不是 `alpha-card`。** `alpha-card` 依資料結構排列（18 個 section），
Analyst View 依**消費者問句**排列：現在多少錢（只有現價）→ 短評 → 論證（鏈／時間表／風險）→ 研究（反證與檢核點）→ 歸零旗標 → 稽核區。
（2026-09-23（Phase 0 Step 0b.4）：原本的頭條尺「現價 → future target → 隱含報酬」與預測／差異／entry threshold 各段隨估值鏈退役。）

```powershell
& '.venv\Scripts\python.exe' -m briefing analyst-view COHR                  # 完整判讀畫面（Markdown）
& '.venv\Scripts\python.exe' -m briefing analyst-view COHR --format json -o analyst.json   # 預先 materialize 給 APP 讀
& '.venv\Scripts\python.exe' -m briefing analyst-view COHR --as-of 2026-09-06              # 歷史視角（PIT）
& '.venv\Scripts\python.exe' -m briefing analyst-view COHR --sandbox-hurdle 0.15           # 非持久驗算 optional entry（不寫 ledger）
```

**純投影：** 它消費 `alpha-card` 的同一份 `AlphaInvestmentView`，**一個數字都不重算**
（每一行都是 read model 裡同一個 `Datum` 物件的參照），不寫任何 authority、不呼叫 LLM。
`--format json` 的輸出完全 JSON-able 且保留 `null`，可預先產生給未來 APP 點擊直接讀。

**讀 readiness：** `ready`／`ready_with_flags`／`blocked` **只看核心各段**（`CORE_PANELS`，2026-09-30 起含讀圖）；
optional 的 entry 缺席只會出現在 `optional_unavailable`，**不會**讓 readiness 變差
（產品決策見 `docs/archive/roadmap-pre-alpha-edge.md`「主流程的終點是 Implied Return」；2026-09-16 起該終點排定由
多年反向橋取代，見 `docs/ROADMAP.md` Phase 7，落地前照舊）。
架構見 `docs/ARCHITECTURE.md` §6.7。**互動專用，不進 unattended rule。**

### Sandbox impact review 結論（2026-09-09，研究閉環 P5：Daily 吃機械段）——已封存
三支命令中 `engine_b.todo reassess-stale` 已於 2026-09-22（Step 0a.1）退役；`standing-go` 自 2026-09-23（Phase 0 Step 0b.4） 起不再開 Decision Store
（只對 `source_trace_review` 派回 pq1）；`consume-fired` 不變。原 review 表逐字封存於 archive；rules 條數的現況由
`tests/test_codex_daily_permissions.py` 斷言。

### Sandbox impact review 結論（2026-09-08，APP materialize 納入 Daily 收尾）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m webapp materialize --tracked --structure-table --beta --coverage --watches --positions` | 寫 **ignored derived cache**（`library/private/app/{analyst_view,state}/*.json`，atomic）。**不寫任何 authority**：不入圖、不寫 Engine C、不建 decision、不 append 風險快照、不碰 `.git` 或任何 tracked 檔 | Neo4j bolt（本機）＋Engine C SQLite＋private ledger（唯讀）＋Google Sheet `spreadsheets.readonly`＋yfinance FX——**與既有 fixed entry `daily_beta_snapshot.py`／`decision_lab today` 完全同一組**，無新增網路主機或憑證 | **納入 Daily 收尾**（第十七個 fixed entry）。ticker 清單由 `engine_b.routine_config` 導出，與 pq1 drain 同一權威，不手寫 |
| `python -m webapp materialize --structure-readings`（2026-09-17 Q5 新增的旗標，**不是新入口**） | 同上：只寫 `library/private/app/state/structure_readings.json`。**唯讀** append-only 讀圖 ledger 與圖，不寫 ledger、不重新推理、不排 pq1 | Neo4j bolt（本機）＋ private ledger（唯讀）——**既有 prefix `-m webapp materialize` 已涵蓋，fixed entry 數量不變**（查證：`pytest tests/test_codex_daily_permissions.py`） | **納入 Daily 收尾**同一行指令。重新推理不在這裡：那是研究，只在互動 session（D12） |
| `python -m webapp serve` | **綁定本機 port**（listener surface） | 新增 listener；外部認證邊界在 Cloudflare Access 而非程式本身 | **仍不在 rule 內**。它由開機自啟的 `stockbot-graph-services.vbs` 長駐，排程不啟動它。放行整個 `-m webapp` 會把它一併帶進去 |
| `python -m webapp status｜verify` | 唯讀 | 無 | **互動專用**，不在 rule 內（prefix 只到 `materialize`） |

**為什麼 fail-soft：** materialize 失敗只記入健康段、不中止 Daily——artifact 是 derived cache，舊的那份仍在，且 APP 會自己顯示 stale。這與 harvest 失敗必須中止整輪**刻意不同**：harvest 持有 writer lock 且會寫共用檔，跳過它續跑會讓兩個 writer 撞上；materialize 不碰任何共用檔，失敗的代價只是「畫面舊了一天」，而那是看得見的。

查證：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'webapp'   # 只該有 materialize，不該有 serve
& '.venv\Scripts\python.exe' -m webapp status                                    # artifact 年齡應 < 1 天
```

### Web App／API（2026-09-07 Step 5）

**兩種 materialize 宇宙（2026-09-09 P4）：** `--tracked`＝pq1 的導出權威（thesis lifecycle＋cohort＋主題核心，
與 drain 同一份）；`--registry-listed`＝registry 裡所有有 research_ticker 的公司（上市 73 家）。後者**只給
materialize 用**，不動 `discover_tracked_tickers`——那會連帶擴大 EDGAR harvest 並稀釋 priority 加分。

```powershell
& '.venv\Scripts\python.exe' -m webapp materialize --registry-listed      # 全部上市公司的單檔判讀（多數 blocked，那是起點）
& '.venv\Scripts\python.exe' -m webapp status | Select-String "ready"     # 到終局的檔數看這裡
```

**日常要看一檔股票，開瀏覽器比開終端機快。** APP 讀的是**已經算好**的判讀——
`LLM changes cognition; APP reads cognition`。

```powershell
# 1) materialize：**唯一**會跑模型、連 Neo4j／Engine C、讀 private ledger 的一步（約 4.2 秒／檔）
& '.venv\Scripts\python.exe' -m webapp materialize COHR LYC.AX 6324.T IQE.L
& '.venv\Scripts\python.exe' -m webapp materialize            # 不給 ticker ＝ 重跑目錄裡已有的每一檔
& '.venv\Scripts\python.exe' -m webapp materialize COHR --as-of 2026-09-05   # PIT 視角
& '.venv\Scripts\python.exe' -m webapp materialize --structure-table         # 結構表（state artifact；照抄 structure_table，不排序、不設門檻，2026-09-23）
& '.venv\Scripts\python.exe' -m webapp materialize --structure-table --as-of 2026-09-05   # as-of 視角的結構表；被排除的 assertion 計數帶在 artifact 內
& '.venv\Scripts\python.exe' -m webapp materialize --beta                    # 資產配置（state artifact；daily_beta_snapshot --no-refresh --no-record-risk 照抄，2026-09-08）
& '.venv\Scripts\python.exe' -m webapp materialize --graph-walk --watches    # 走圖九型＋在等什麼（唯讀照抄；2026-09-26 取代 --coverage）
& '.venv\Scripts\python.exe' -m query.graph_walk                            # 走圖：九型問句各自「命中／母體」（零 LLM、不排序、不加總）；第 9 型逐對印兩端逐字與 registry note
#   （重複節點與覆蓋缺口原本各有一支 CLI，2026-09-29 Phase 3 Step 3.1c 退役——跑它們會 exit 2 並指回走圖）
& '.venv\Scripts\python.exe' -m webapp materialize --candidates              # 候選狀態板（2026-09-29 Phase 3 Step 3.6；不寫 authority：敘事 ledger、讀圖對圖、watch、Engine C、Sheet readonly、FX）
& '.venv\Scripts\python.exe' -m webapp materialize --tracked --registry-listed --structure-table --beta --graph-walk --watches --positions --structure-readings --scorecard --candidates   # Daily ⑬ 的完整一輪（crons/daily_task.py 是唯一權威）

# 2) serve：純讀。**不重建任何東西**
& '.venv\Scripts\python.exe' -m webapp serve                  # http://127.0.0.1:8790/

# 3) 現況與健檢
& '.venv\Scripts\python.exe' -m webapp status                 # 每份 artifact 的新鮮度／readiness／blocker kind
& '.venv\Scripts\python.exe' -m webapp verify                 # 重新驗 schema／digest／必要欄位（fail closed）
```

**判讀舊了怎麼辦：** artifact 超過 24 小時會標 `stale`（`STOCKBOT_APP_MAX_AGE_HOURS` 可調）。
**stale 不會自己重建**——那是刻意的：request path 一旦能重建，它就有能力改變系統對一家公司的認知。
要更新就重跑 `materialize`（排序同理：`--ranking`；資產配置：`--beta`——它讀 daily ETL 已存的行情，所以先跑完 daily 再 materialize 才是最新）。

**blocked 怎麼讀：** 畫面會逐條寫「卡在哪一層 ＋ 為什麼」，而「為什麼」是封閉字彙不是散文：
`還沒寫`（去研究）／`刻意不主張`（**這已經是答案，不用動作**）／`方法不適用`（補資料解不掉）／
`上游缺料`（要補的是上游）。紫色徽章 ＝ settled ＝ 不必去補。

**遠端存取：** 重用既有 Cloudflare Tunnel ＋ Cloudflare Access，程序與**尚未完成的人工步驟**見
[`deploy/cloudflare/README.md`](../deploy/cloudflare/README.md)。APP 預設只綁 `127.0.0.1`，
**沒有自己的帳號密碼系統**；要綁其他介面必須明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則拒絕啟動。

**Abstention ledger（「刻意不主張」）：**

```powershell
& '.venv\Scripts\python.exe' -m alpha abstention 6324.T                       # 列出
& '.venv\Scripts\python.exe' -m alpha abstention 6324.T --add spec.json       # append（reason 與 revisit_when 必填）
& '.venv\Scripts\python.exe' -m alpha abstention 6324.T --retract ab_xxxx     # append 一筆撤回
```

**三層各有自己的 subject**（封閉字彙，寫錯直接拒收）：`valuation/forward_earnings_multiple.target_pe`、
`research/axis.catalyst`、**`bet/variant.overlay`**（2026-09-17 Q2 新增：「目前沒有可辯護的賭注」）。
⚠ **不得互相頂替**：估值層那筆說的是「本益比法沒有可校準的對象」，虧損年照樣可以寫
「如果 X 為真它值 Y」——把它讀成賭注層的 abstention，等於把待辦冒充成答案。
（籃子頁與心跳第 4 段的「賭注帳」已於 2026-09-22／23 退役；`bet/variant.overlay` 這本 ledger 的資料留著，L10。）

```jsonc
// spec.json 範例（賭注層；reason ≥ 20 字、revisit_when ≥ 10 字，型別層強制）
{"company_id": "co:iqe", "ticker": "IQE.L", "layer": "bet", "subject": "variant.overlay",
 "reason": "……為什麼今天寫不出可辯護的賭注……", "revisit_when": "……什麼證據出現才會重看……"}
```

⚠ 它**不會產生任何數字**——宣告之後 fair value 仍然缺席、readiness 仍然 blocked，改變的只有
「為什麼缺席」。`Abstention` 在型別層不可能長出可裝數值的欄位。
架構見 `docs/ARCHITECTURE.md` §6.8／§6.9。**互動專用，不進 unattended rule。**


**結構讀圖（Structure Reading，2026-09-17 Q5）：「四條邊一起讀才讀得出來」的 append-only 紀錄。**

```powershell
& '.venv\Scripts\python.exe' -m query.structure tech:cw_dfb_laser          # 五個角度一次查出（零 LLM、零判斷）
& '.venv\Scripts\python.exe' -m query.structure prod:supernova --unit socket --quotes   # 插槽視角（只用在 prod:*）：多印「誰的產品」「客戶端原文」兩段，不進 digest
& '.venv\Scripts\python.exe' -m alpha structure-reading tech:cw_dfb_laser  # 列出讀圖紀錄
& '.venv\Scripts\python.exe' -m alpha structure-reading tech:cw_dfb_laser --check   # 跟現在的圖比一次並分級（唯讀）
& '.venv\Scripts\python.exe' -m alpha structure-reading tech:cw_dfb_laser --add spec.json
& '.venv\Scripts\python.exe' -m webapp materialize --structure-readings   # 算 staleness，心跳第 2 段才看得到
```

```jsonc
// spec.json（v3，2026-09-25：unit／kind／reading／expires 必填；**快照不得夾帶**，由命令現跑 query.structure 產生）
{"unit": "layer",                       // layer＝一層（tech／mat）；socket＝客戶產品裡的一格（只能是 prod:*）
 "kind": "volume", "reading": "……為什麼讀成量的賭注而不是護城河賭注……",
 "expires": "2026-12-16", "tickers": ["COHR", "LITE"],
 // moat／volume 必須兩半各至少一段：quote 要是那條邊出自 source_id 的逐字（先跑 query.structure <node> --quotes 挑）
 "citations": [
   {"angle": "demand_side", "edge": ["tech:cpo", "depends_on", "tech:cw_dfb_laser"], "quote": "……≥20 字逐字……", "source_id": "<doc_id>"},
   {"angle": "supply_side", "edge": ["co:coherent", "supplies_to", "tech:cw_dfb_laser"], "quote": "……", "source_id": "<doc_id>",
    "independent": false}               // 插槽的 moat 需至少一段供給側 independent=true（來源不是供應商自己、且解析得到）
 ],
 "disproof": [{"condition": "……", "entities": ["co:…"], "check_frequency": "每季", "action_48h": "……",
               "source": "self"}]       // self＝本份寫下；沿用舊讀圖的寫它的 sr_*
}
```

⚠ **引用由命令對同一次查詢的圖上逐字核對**：邊不在這次快照的那個角度、片段不是那條邊出自 `source_id` 的逐字、
`independent` 的來源是供應商自己或解析不到、反證的 `sr_*` 不在同節點 ledger——任何一條不過就整筆拒收並逐條說明。
判不出 A／B 的寫 `undecided`（不強制引用），在 `reading` 寫清楚缺哪一格。

⚠ **存輸入，不存結論**：紀錄的主體是「當時那五條查詢回什麼」，判讀只是附帶——
只有結果集比對得出「多了一條我當初沒讀到的邊」。`kind` 由寫的人宣告，**不由程式從 angles 推**
（A/B 判準表刻意還沒機械化：先產出幾十份、看它準不準，INV-5）。

⚠ **分級不是 binary**：供給側增減／sub 變動＝`high`（進走圖第 4 型 `reading_stale`、佇列段 `graph_holes`；2026-09-26 前是段 `stale_structure_readings`）；
只有 evidence 變＝`low`（記錄，不進佇列）；**`documents` 計數根本到不了這一層**（`EdgeView.key()` 不含它）
——binary 的 stale 會恆亮，而恆亮＝零鑑別力（L14-4）。

⚠ 供給側多一家／反向路徑變動**同時是既有 disproof 的觸發**（量的賭注賭的正是「產能一時補不上」）。
系統只標記；**thesis 要不要改由人決定**（thesis mutation 是四個人工 gate 之一）。

### Engine C
```powershell
& '.venv\Scripts\python.exe' engine_c\etl_yfinance.py <TICKER>
& '.venv\Scripts\python.exe' engine_c\checklist.py <TICKER>
& '.venv\Scripts\python.exe' -m engine_c.set_manual_field --fields <T>   # 列出已登記觀測欄位（階層式）
# ⚠ set_manual_field 只建立待核准提案，不直接寫 ledger；核准後走 todo complete-observation
& '.venv\Scripts\python.exe' -m engine_c.set_manual_field --list <T>     # 列出該標的已填欄位
# 機械歷史表（Phase 3 Step 3.2）：價格 raw／adjusted＋分割、EDGAR 基本面（每份申報各一列，as-of 看 filed）
& '.venv\Scripts\python.exe' -m engine_c.history_backfill --report <file.json>   # 全體回填（寫正式庫：先取 writer lock、不得與 daily 同時）
& '.venv\Scripts\python.exe' -m engine_c.history_backfill --incremental          # daily ②b 跑的那一行
& '.venv\Scripts\python.exe' -m engine_c.history_backfill --db <副本.db> --tickers AXTI   # 對暫存副本試跑（副本用 sqlite3 backup API 產生，正式庫是 WAL）
# 募資文件清單（Phase 6 Step 6.6；稀釋燈的判色依據，表與封閉清單住 engine_c/offerings.py）：增量時落後檢查本來就抓一次
# submissions，同一份清單順帶寫進 equity_offering_filings／equity_offering_checks（請求數不變）；報告的 summary.offerings
# 印 written／not_fetched（這檔還沒有財報列，下一輪才順帶）／unavailable。非增量回填會為它補抓一次。
# fundamental_history 的 metric CHECK 遷移（Phase 4 Step 4.6；新增指標時才用；預設 dry-run）
& '.venv\Scripts\python.exe' -m engine_c.migrate_fundamental_metrics                # 印列數與 CHECK 缺哪些字彙
& '.venv\Scripts\python.exe' -m engine_c.migrate_fundamental_metrics --apply        # 取 writer lock → 備份 → 單交易重建 → 對帳
# 遷移後**立刻**補新指標的歷史：daily ②b 的增量只在有新申報時重抓，舊申報裡的新指標要跑一次非增量回填；
# 跑完看報告裡逐檔的 edgar outcome——不是 written 的那幾檔（unavailable／lagging／error）還沒有新指標，
# 讀取端分不出「還沒重抓」與「真的沒有」（plan §14 #23），下一次非增量回填前它們的稀釋燈理由不可盡信
& '.venv\Scripts\python.exe' scripts\writer_guard.py acquire --minutes 30 --purpose "EDGAR 非增量回填"
& '.venv\Scripts\python.exe' -m engine_c.history_backfill --no-prices --report <file.json>
& '.venv\Scripts\python.exe' scripts\writer_guard.py release
```

⚠ **寫入含 `$` 的金額字串不要經 PowerShell 傳參**——`US$71.3M` 會被當變數前綴展開成 `US.3M`，在 append-only ledger 造成需 supersede 才能更正的損毀。用 Python 或 heredoc。

### Beta 快照
```powershell
& '.venv\Scripts\python.exe' scripts\daily_beta_snapshot.py --format markdown --risk-view changes
```
輸出明標 `policy_mode=paper_observation`、`capital_scope=shared_cash_pool`；不建立 choice／fill、不下單、不寫 Sheet、不把 undrawn loan 算資本。
⚠ 2026-09-16 D6：beta 凍結開發，本命令維持、不再擴充；只保留「大盤比例」觀測。

### 記錄成交（手動下單後）

```powershell
& '.venv\Scripts\python.exe' scripts\record_trade.py --symbol QQQ --side buy `
    --shares 10 --price 687.79 --executed-at 2026-07-31T13:04:53-04:00 `
    --broker IB --account-ref "U****1599" --note "<券商通知逐字內容>"
```

預設 **dry-run**，只印出將變更的三格（`shares`／`avg_cost`／現金）。確認後：

- `--apply`：實際寫入 Sheet 並記錄事件
- `--log-only`：**Sheet 已由你手動更新過**時使用，只記事件不碰 Sheet。
- **重跑 `--apply` 一律拒絕（2026-09-30）**：這筆（trade_id）已在事件紀錄就 exit 2、不寫 Sheet——原本只印警告、照寫，股數與現金會重複計算。Sheet 需要更正請手動改。
- **一筆成交只讀一次 Sheet（2026-09-30）**：同一份原始格交給定位、硬擋與研究收據；寫入前的逐格重讀（防你同時手改）照留。

寫入的三個不變量（有測試守住）：按**欄名**定位（你調欄序不會寫錯欄）、
**只寫指定儲存格**（不會蓋掉你手填的欄位）、**寫前比對現值**（不符即整批中止）。
市值與 NAV 不由本腳本改動。

**alpha 成交的研究收據（2026-09-30，Phase 3 Step 3.8）：**

```powershell
& '.venv\Scripts\python.exe' scripts\record_trade.py --symbol FRA:2DG --side buy `
    --shares 100 --price 7.1 --currency EUR --fx-to-base 1.08 --cash-column none `
    --executed-at <ISO> --broker IB `
    --why "<一句：為什麼現在買>"                                   # alpha 必填（碰 Sheet 之前就驗）
#   ⚠ 非 USD 成交要給 --currency <那一列的幣別> --fx-to-base <1 該幣 = ? USD> 與 --cash-column（台幣 cash_twd；
#     日圓／歐元只有 none）。2026-09-30 起：成交幣別（沒給時是 USD）對不上 Sheet 那一列的 currency 就 exit 2、不寫、
#     不記事件（--log-only 也擋）；現金欄幣別對不上成交幣別也 exit 2；--cash-column 只收 cash_usd／cash_twd／none。
#     之前只印負數警告就照寫，會把歐元／日圓／台幣金額當美元扣掉
#   沒有現行 v2 敘事的 alpha 買進 → exit 4（fail closed）；確定要買：
#   --no-narrative-override "<理由>"                              # 理由寫進收據；不放行硬擋
#   賣出：--why 必填；--disproof-watch <watch_id>（可選，觸發賣出的反證，以來源歸屬驗）
```

**回填收據機制上線（2026-09-30）前的舊 alpha 成交（2026-10-02，Phase 5 Step 5.3）**——Sheet 已有、trade_log 沒有的那幾筆：

```powershell
& '.venv\Scripts\python.exe' scripts\record_trade.py --symbol COHR --side buy `
    --shares 10 --price 316.23 --currency USD --executed-at 2026-08-18T11:02:30-04:00 --broker IB `
    --why "<一句：當時為什麼買>" --log-only `
    --backfill-before-receipts "Sheet 已有這筆、trade_log 沒有（收據機制上線前的成交）"
#   歐元成交（FRA:2DG）另給 --currency EUR --fx-to-base <1 EUR = ? USD>（硬擋要量得到）
```

- ⚠ **回填沒有乾跑**：通過入口檢查與硬擋就直接寫進 append-only 的 trade_log，寫錯改不掉。跑之前先拿券商成交通知與 Sheet 那一列，
  核對股數、價格、幣別、成交時間（含時區）。拿掉 `--log-only` 不會變成預覽，只會被拒收（R2-a C3）。
- **只准配 `--log-only`**（Sheet 已是現況，不再改）；成交日（排程時區）**必須早於 2026-09-30**——那天或之後的成交走正常路徑；
  **只收 alpha**（beta 本來就不需要收據）；**必附理由**；不能配 `--apply`／`--no-narrative-override`／`--disproof-watch`。
  七種拒收與「排程時區讀不到」都在碰 Sheet 之前、exit 2、什麼都不寫。名冊讀不到也 exit 2，發生在讀 Sheet 之後、寫入之前，
  不會吞成「解析不到」：「讀不到」與「名冊沒有這家」寫進 append-only 的收據會同形。
- 以**日期**為界（plan §4 ②）：台北 2026-09-30 00:00 之後的成交一律拒收，即使早於收據機制 commit 的 07:06。
  硬擋量的是**今天**的 Sheet：那一列今天的市值若已超過 NAV 5%，回填會被擋（exit 3）；確定要記就加 `--override --reason`。
- 收據寫 `narrative: backfilled`、`declared`／`derived` 都是 `null`：**不讀敘事、候選板、個股頁**——今天的判斷不得冒充當時（INV-6）。
  公司身分照解析（`resolve_holding`）。硬擋照算（`--log-only` 語意：不碰現金格、照算 5% 與 ETF cap，超過照擋）；同一筆重跑不重寫。
- 追蹤表的 live lane（`scripts/outcome_if_settled_today.py`）照抄這個標記，印「回填、無當時收據」。
- alpha／beta 只由 `risk/hard_caps.py` 的公開判別決定（賣出也判）。beta（QQQ 等）不要收據、行為不變；給 beta 帶 `--why`
  會被拒（exit 2），不是默默忽略。
- 順序：定位（恰好一列）→ 硬擋 → 收據；**dry-run 也組收據、也印、也擋**。exit code：2＝輸入錯、3＝硬擋、4＝缺敘事
  （缺敘事也含「敘事 ledger 讀不到／有壞行／registry 沒有 research ticker」＝`narrative: unreadable`——確認不了現行是哪一版）；
  定位不到那一列是 exit 2 並提示首次建倉的旗標（見下方首次建倉）。旗標以「有沒有給」判斷：給了空字串（例：shell 變數展開成空）照樣拒絕。
  **兩個放行互不放行**：`--override --reason`（硬擋）不放行缺敘事，`--no-narrative-override`（敘事）不放行硬擋。
- 收據進那一筆事件的 `research_receipt`：`declared`（現行 v2 敘事的 brief_id、候選狀態、兩題答案、騎的讀圖與寫入當時的
  result_digest、歸屬本檔還在處理中的 watch）／`derived`（**當天**候選板 artifact 那一列、個股頁 artifact 的三題稽核行、成交前的
  Sheet 持有）。收據路徑只讀本機檔案與 Sheet readonly——**不連 Neo4j、不打行情或 FX**；artifact 缺席或不是今天只記
  `derived: upstream_unavailable`，**不擋成交**。要收據帶得到當天的推導，先讓 daily ⑬ 跑過，或手動
  `python -m webapp materialize <研究代號> --candidates`（`--candidates` 只重算候選板；三題稽核行住個股頁 artifact，要連該檔一起跑）。
  個股頁 artifact 是 as-of 視角、三題整段缺席、或候選板那一列的敘事版本不是現行，也都記 `upstream_unavailable`＋原因。
  「成交前持有」記兩個層級：這一列（symbol＋broker）與公司層級（同一家公司任何一列）。
- Sheet symbol → 公司：Sheet 列自己的 company_id → execution 別名（`FRA:2DG`→`SIVE.ST`）→ registry；都不中＝`narrative: unresolved`
  （不猜；要買就補 registry 或用 `--no-narrative-override`）。
  執行代號住名冊（`config/company_identity.json` 的 `execution_symbol`；`identity.execution.get_execution_aliases()` 由它派生）。
  ⚠ 2026-10-01（Phase 4 Step 4.1d）起 `fetchers/gsheets.py` **不再替任何列注入身分欄**（原本替 FRA:2DG 塞 `neo4j_id`，收據因此記
  `sheet_company_id`）：今天的 Sheet 沒有 company_id 欄，FRA:2DG 走 `execution_alias`；新增一檔跨掛牌持股＝在名冊那一家加
  `execution_symbol`（構造時檢查不得撞任何公司的 research ticker／ticker alias／另一家的執行代號），不是改 Sheet 解析。
- **首次建倉走對話（2026-09-30 使用者定案）**：跟 session 說一句「我在 IB 買了 AXTI 100 股、每股 12.3 美元，因為…」，由 session 跑
  `--open-position --broker <券商> --currency <幣別> --cash-column <cash_usd／cash_twd／none> --bucket <Sheet 既有的 bucket> [--company <公司名>]`。**全部明給**（R2 2026-09-30 blocking：新列沒有既有列可以核對，預設的 IB／USD／cash_usd 會被照寫進 Sheet——台股代號配 USD，市值高估約 31 倍、回讀驗證抓不到）。寫入前就擋——**代號寫法白名單**（R2 覆核：只擋認得出的錯會漏）：台股 `XXXX.TW`／6 碼 ETF `.TW`＝TWD（`TPE:` 與裸碼要改寫成 `.TW`——Sheet 的慣例寫法）、日股 `XXXX.T`＝JPY（**公司名冊的寫法**；`TYO:XXXX` 要改寫成 `XXXX.T`——2026-09-30 使用者定案 Sheet 用名冊寫法、不為 Sheet 另做別名，既有的 `TYO:7803` 已改成 `7803.T`；公式把兩者當同一檔，比對也用同一個正規化）、`FRA:`／`ETR:`／`EPA:`／`AMS:`＝EUR、美股裸代號（後綴只收股別 `.A`／`.B`）＝USD；**其他寫法一律拒收、請手動建列**（上櫃 `.TWO`、`LON:`〔GBX 股票配 USD 會高估百倍〕、`.ST`／`.PA` 等公式轉不出代號的）；裸 4 碼台股要寫成 `.TW`（公式把兩者當同一檔，比對同一檔時也用同一個正規化）；公式不認得的幣別（只有 USD／TWD／EUR／JPY）、代號不是大寫或含前後空白（Sheet 公式分大小寫，寫進去的是原字串）、現金欄幣別與成交幣別不同（**既有列加碼也擋**——2026-09-30 起兩條路徑同一條規則：日股／歐股沒有對應的現金欄，請給 `--cash-column none`；只有 `--log-only` 不碰現金格不擋；既有列另比對 Sheet 那一列的 currency）、bucket 不在 Sheet 既有的值裡、**這個代號已在別家券商有列**（多半是 `--broker` 給錯；真的在新券商建倉才加 `--also-at-other-broker`）、**同一家公司已以別的代號持有**（5% 上限按代號加總，換代號建倉會繞過它；按公司合併是 Phase 4 的使用者決定）。沒有列又沒給旗標是 exit 2，提示會列出這個代號在哪些券商有列；已有那一列時給旗標也拒收。做法（`fetchers/gsheets.py` 的四個函式，公式形狀以 2026-09-30 唯讀實測為準）：
  ①插在**同券商最後一列持股的下一列**（沒有同券商持股就插在第一個 CASH 列上面）——必須落在 `nav_base` 的 `SUM($I$2:$I$25)` 範圍**內部**，Sheets 才會把範圍撐大，新列才算進 NAV（接在最後一列之後，5% 硬擋就用錯分母）；②公式與格式從同券商一列**標準形狀**的持股列複製（多數列的形狀為準；手寫公式的列——例：7803.T 抓不到價、手寫市值——照實列出、不當範本；沒有一種占三分之二就中止）；③插列、複製、填值在**同一個原子請求**，只寫新插的那一列；④寫完立刻回讀：公式形狀、NAV 範圍涵蓋到最後一列、整張表照樣讀得過、**新列市值 > 0**（抓價公式只換算 USD／TWD／EUR／JPY，其他幣別或代號抓不到價會被吃成 0）——任何一項不過就刪掉那一列還原、不寫事件紀錄；**回讀本身丟例外（網路、429／5xx）也還原**；開列請求丟例外時先回讀，分三種：插入點那一列的代號＋券商＋股數都是剛寫的（列數至少多一列）＝已套用、刪掉還原（只比代號會把別家券商的同代號列當成新列刪掉）；列數沒變而且整張表沒有這個代號＋這家券商＝**此刻**沒套用（伺服器可能稍後才套用，重跑前先看一眼）；其他（例：你同時改了列數）＝無法確認、不動手、請你看；還原刪列前同樣三項都比；現金格寫入丟例外時（只有「寫入前比對不符」這一種確定一格都沒寫）回讀現金格：還是舊值就刪新列、已是新值代表整筆其實寫完了就照常記事件（`sheet_write_note`）、都不是就不刪不記、大聲說請手動核對；（開列路徑判成「此刻沒套用」前會隔 3 秒再讀一次，訊息只說「目前讀回未套用」，不宣稱確定沒改動）；刪完回讀列數與 NAV 範圍確認回到寫入前，確認不了就照實說。現金那一格因插列下移一列，照樣逐格重讀比對後才寫。dry-run 會印新列的完整內容與插入位置；成交後現金變負數會警告。
  ⚠ 插列撐大 `SUM` 範圍、貼上調整相對列號是 Sheets 的一般行為，官方文件沒有逐字寫——第一次真的建倉用小部位、當場看一眼 Sheet；行為不符時回讀驗證會抓到並還原（R2 以模擬確認過兩種「不符」都會觸發還原）。
- 旗標給了空字串（`--broker ""`）一律拒收，不退回預設；`--executed-at` 必須帶時區。
- ⚠ 既有列路徑（不是建倉）寫到一半丟網路例外時**沒有還原**，只印出哪幾格可能已寫入、請手動核對（2026-08-01 起的既有行為，ROADMAP 旁支待排程）。
- 重跑防呆比對的是正規化後的成交（代號大小寫、券商、UTC 時間、股數、價格），不只 trade_id——換大小寫或時區寫法重跑照樣拒。同一秒同價同股數的兩筆真的不同成交會被當成重跑（fail closed）；真遇到就在 `--executed-at` 用券商通知的精確時間。
- 舊事件（3.8 之前的 2 筆）沒有 `research_receipt`：未來讀取端要把它當**缺席**，不是錯誤（plan §14）。

事件紀錄在 tracked `library/trades/trade_log.jsonl`（append-only）。
它是「發生了什麼」的稽核軌跡，**不是持股真相**——後者永遠只有 Sheet。
2026-09-16 D14 再確認：**Sheet 是部位真相**（含貸款額度、投入標的與現金），Decision Store 只留可選 receipt；
alpha 原則上不用貸款資金是使用者自己的紀律，本腳本**不加 gate**。

### Google Sheet 的 Dashboard 分頁（2026-10-02 v6）

- Dashboard 整頁都是對 Portfolio 的即時公式——**持股表的標的清單也是**（`UNIQUE(FILTER(...))`，隱藏的 M:O 是輔助欄，容量 57 檔），
  所以 Portfolio **新增或移除一檔不用做任何事**；只有**版面或公式要改**才重跑：
  `& '.venv\Scripts\python.exe' fetchers\build_dashboard.py`（讀 `.env` 的 service account、寫入 scope；**互動專用**，不進任何無人值守步驟）。
- 它會整頁清掉重建——值、條件格式、圖表都重來（v4 每跑一次疊一層，2026-10-02 實測疊到 20 條條件格式）；分母是**含現金的 NAV**
  （AGENTS：`bucket=CASH` 計入 NAV 不計曝險；v4 的「% of Total」五格加起來 107%）；槓桿 ETF 印名目與有效曝險兩行
  （倍數讀 `config/beta_policy.json`，列舉全部倍數 > 1 的代號，Sheet 上沒有的算 0）。
- 2026-10-02 整理紀錄：Portfolio 補回 COHR 列（IB 觀察 10 股 @316.23，2026-08-18 成交、Sheet 漏列）；`DRAM` 改寫成 `BATS:DRAM`
  （GOOGLEFINANCE 的「DRAM」是 Defiance Memory UCITS，市值少算約 $3,300），`config/beta_policy.json` 的 `sheet_aliases` 同步加 `BATS:DRAM`。
  COHR 與 FRA:2DG 都還沒有 trade_log 事件——Phase 5 Step 5.3 的 `--backfill-before-receipts` 做好後，由使用者照 Sheet 回填。

### 入圖：apply 固定入口（2026-10-01 Phase 4 Step 4.2d）
使用者在對話中明確核准 pq2 `ra_admission` [N] 之後（授權載體仍是那句核准）：
```powershell
& '.venv\Scripts\python.exe' scripts\apply_ra_admission.py --pq2 <N> --digest <action_digest>
```
四道 fail closed——①[N] 存在、型別 `ra_admission`、未結案（drop 的編號永久拒絕；要重提請重跑 prepare 取新編號）
②[N] 的 ref_id 是一筆存在的 Research Action ③digest＝紀錄凍結的 `action_digest` ④紀錄 ready 且未過期，或同編號同 digest
中斷在 partial／applying 的重試——四道過了、**蓋戳記之前**再做一道唯讀 token 檢查（2026-10-02 Phase 5 Step 5.1）：以 apply 寫圖的
routine 憑證 `CALL db.propertyKeys()`，與 `loader.load_to_neo4j.written_property_names()`（loader 會 SET 的屬性名，唯一一份）比對，
缺任何一個就拒絕（exit 2、印缺哪些、請 admin 跑 `schema/neo4j_setup.cypher` 的 1b 預熱——routine writer 不能建新屬性名，
pq2 [666] 就是蓋了戳記才在寫圖時被 Forbidden 擋下）；讀不到圖也拒絕（`upstream_unavailable`）。兩種都不留戳記——
通過後先把 `approval={pq2_n, digest, at}` 寫進紀錄的 execution，再 apply。
**不 publish、不結案**：之後照下面「入圖收尾」publish，再 `python -m engine_b.todo complete-ra <N> --digest …`
（它比對 approval 戳記——沒經過本入口的 apply 結不了案）。結束碼 0＝已 apply、2＝四道沒過（沒有任何寫入）、3＝已蓋戳記但
apply 沒完成（看輸出的 next_action）。私有函式 `intake.application._apply_research_action_impl` 不再是操作入口。

**sandbox impact review 五步（新增 `scripts/*.py` 入口）：**

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 讀 `library/leads/todo_pool.json` 與 `library/private/research_actions/`；寫入只有兩處：那一筆 RA 紀錄的 `execution.approval`（在 action lock 內）與既有 apply 的寫圖／provenance（沿用 `_apply_research_action_impl`，`NEO4J_ROUTINE_*` 憑證）。不 Git、不 publish、不 resolve pq2、不連外網。 |
| **2 skill／prompt／本檔** | `prompts/intake_protocol.md` §4.3、`skills/daily-brief/SKILL.md`、`skills/lead-intake/SKILL.md` 改指本入口；本節。 |
| **3 最窄 rule** | **互動專用，沒有新增任何 rule**：不進 `.codex/rules`（仍是 0 條前綴）、不進 daily 固定步驟、不進 `.claude/settings.json` 的 allow。它落在本機 `.claude/settings.local.json` 既有的寬鬆放行 `Bash(python *)` 之下——補償控制是**四道檢查＋核准戳記＋`complete-ra` 比對戳記**（沒經過入口的 apply 結不了案）。 |
| **4 permission contract test** | `tests/test_apply_ra_admission.py::test_entry_is_interactive_only`（rules／daily 步驟／專案 allow 都不含本入口）、四道拒絕不寫入、戳記先於 apply、partial 只能原編號重試；`tests/test_engine_b_todo.py::test_complete_ra_refuses_an_apply_that_bypassed_the_entry`。 |
| **5 端到端 smoke** | 2026-10-01 R2-a 覆核者在暫存根目錄以夾具（fake loader）跑過 create → 池裡 `ra_admission` → 本入口 → `complete-ra`（經入口的那筆結得了案、繞過入口的被拒；腳本在該次覆核的 scratchpad）；**repo 裡串成一條的測試待 Step 4.9 full chain**（今天 `tests/test_apply_ra_admission.py` 停在 apply、complete-ra 的測試用 mock 紀錄）。真資料只跑拒絕路徑（已結案的編號 exit 2、沒有寫入）。 |

**2026-10-02 Phase 5 Step 5.1 增補：蓋戳記前的 token 檢查。** ①capability：多一次**唯讀** Neo4j 讀取（`CALL db.propertyKeys()`，`READ_ACCESS` session、用完即關），
憑證就是 apply 本來就用的 `NEO4J_ROUTINE_*`（`intake.application._driver`）——本入口原本就會連圖寫入，沒有新增 capability；寫入面不變（缺 token 時連戳記都不寫）。
②skill／本檔：本節；`schema/neo4j_setup.cypher` 1b 預熱清單同 Step 補齊 37 個屬性名（`tests/test_robotics_ontology.py` 的對稱測試：預熱 ⊇ loader 會 SET 的，`id` 除外）。
③rule 不變（互動專用、不進任何無人值守 allowlist）。④測試：`tests/test_apply_ra_admission.py` 缺 token 拒絕且無戳記、讀不到圖拒絕、全在照舊、重試路徑缺 token 戳記不動，
四道沒過時不連圖；變異：拿掉 preflight → 4 條紅。⑤真資料：只跑唯讀的 `check_property_tokens()`——今天的圖通過（routine 憑證讀得到 56 個 key）；
要求一個不存在的名時正確拒絕。入口本身不在真資料上跑（[666] 重試是使用者動作）。

**2026-10-03 增補（使用者已 go 的 pq2 [673] 撞到）：完成收據走廊的歸檔證據改以內容核對。** 改寫 `library/private/intake_state/<doc_id>.json`
的條件仍是「現存收據指的那一版 extraction 已歸檔在 `superseded/`」；先前只認 `<doc_id>.<canonical hash 前 8 碼>.json` 這個檔名，
走廊上線（2026-09-11）前的歸檔以**原始位元組** sha256 命名（`nvidia_sipho_blog_partner_roles.c48feb4b.json`，內容的 canonical hash 才是收據記的
`8189ac4b`），於是確實歸檔過的那一版被判成沒歸檔、[673] 停在 partial（圖已寫入）。現在檔名找不到時，在同一個 `superseded/` 目錄裡找內容
canonical hash 相等的檔（`intake.provenance._superseded_extraction_archive`）。sandbox impact review：①capability 不變——多讀同一目錄的既有歸檔檔，
寫入面不變；②本節；③rule 不變（入口仍互動專用、`apply_ra_admission.py` 仍是 ask）；④`tests/test_intake_completion_corridor.py` 兩條：舊式命名、
內容相符 → 收據跟上且舊收據歸檔；同 doc_id、內容不符 → 照樣拒絕（變異：撤掉修法前者紅）；⑤真資料：[673] 以同編號同 digest 重試 → applied。

**2026-10-04 本機 ask 規則：** 6.7e 在 `.claude/settings.local.json` 對本入口加的 8 條 `permissions.ask` 已依使用者明說拿掉（`record_trade.py` 的 8 條保留）。
本入口回到 step 3 表格寫的狀態：落在本機既有的寬鬆放行之下，補償控制是四道檢查＋核准戳記＋`complete-ra` 比對戳記；授權載體仍是使用者在對話中對 pq2 的 `go`。

### 入圖收尾
```powershell
& '.venv\Scripts\python.exe' scripts\commit_pending_intake.py --status | --dry-run
& '.venv\Scripts\python.exe' scripts\commit_pending_intake.py      # 每 action 一 commit、整批一 push
```

### SourceDoc 欄位更正（2026-10-03 Phase 6 Step 6.3d：`origin_entity` 進同步欄位）
```powershell
& '.venv\Scripts\python.exe' loader\migrate_sourcedoc_json_section.py --corrections loader\manifests\sourcedoc-origin-20261003.json            # dry-run：計畫＋證據等級會變的邊
& '.venv\Scripts\python.exe' loader\migrate_sourcedoc_json_section.py --corrections loader\manifests\sourcedoc-origin-20261003.json --apply --pq2 <N>   # 使用者 go 之後
```
同步欄位只有一份（`loader.sourcedoc_sync.FIELDS`＝section／title／origin_entity；圖那一側的查詢 `GRAPH_CYPHER` 也住那裡，audit 與健康審查共用）。
更正 manifest 每筆宣告 doc_id／field／before／after／why／source；apply 前核對每份抽取檔（base＋addendum）與圖上現值都等於 before，
pq2 項的 ref_id 要逐字等於 manifest 的 `pq2_ref`；JSON 先改（綁收據的舊版歸檔）、圖 compare-and-set、最後重跑一致性核對（不一致 exit 3）。
sandbox impact review：互動專用（不進 rules／daily）；與既有 `--apply-graph` 同一個寫入面（`SourceDoc` 的同步欄位）與同一套編號核對＋writer lock，沒有新增 capability。

### 身分清理遷移（2026-10-03 Phase 6 Step 6.2：OpenLight 合併、nava 退役）
```powershell
& '.venv\Scripts\python.exe' loader\migrate_identity_cleanup.py                 # dry-run（唯讀；印計畫 JSON：抽取檔逐項改動、名冊 diff、入圖副作用、證據等級會變的邊、活的引用）
& '.venv\Scripts\python.exe' loader\migrate_identity_cleanup.py --apply --pq2 <N> --backup-dir library\private\backups\<name>   # 使用者對 [N] go 之後
```
manifest 住 `loader/manifests/identity-cleanup-20261003.json`（宣告式：每個決定附理由與一手原文；`pq2_ref` 是 pq2 項的 `ref_id`）。
`--apply` 的順序：pq2 編號核對（存在、未結案、`manual`、`ref_id`＝`pq2_ref`）→ backup-dir 的 `neo4j_export.json` 非空且 counts 自洽 →
重算計畫、改後抽取檔重載的入圖副作用必須為 0 → **先寫圖**（管理員憑證：scoped 重載、刪舊 id 的 assertion 與節點、重投影）→ 再寫抽取檔
（舊版歸檔 `extractions/superseded/`）與名冊 → 對真的圖逐條重算證據等級，必須等於 dry-run 的預告 → 結果寫 `…result.json`。
**Neo4j 回 Forbidden 就停下問使用者，不換憑證重試。** 事前匯出：`scripts/backup_private.py` 的 `export_neo4j_payload()` 寫進 backup-dir。

**sandbox impact review 五步（新增 `loader/migrate_identity_cleanup.py`；`scripts/prepare_research_action.py` 多一次唯讀查圖）：**

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 遷移工具：dry-run 只讀（`NEO4J_*` 的 READ session、讀 `extractions/`、名冊、四份 authority 檔找活的引用）；`--apply` 寫 Neo4j（管理員憑證，與既有 `migrate_*.py` 同）、兩份抽取檔、`extractions/superseded/` 歸檔、`config/company_identity.json`、`loader/manifests/…result.json`。prepare：多一個 READ session（routine 憑證，原本就為同 URL 檢查開過），只跑 MATCH；寫入面不變（RA 紀錄多一個收據欄位）。都不連外網、不 Git。 |
| **2 skill／prompt／本檔** | 本節；上面 prepare 那一段；`docs/ARCHITECTURE.md` 不需改（遷移工具是一次性）。skill 不必改：RA 的 packet 是 server 端 render，skill 照舊「把 packet 原文給使用者」。 |
| **3 最窄 rule** | **沒有新增任何 rule**：兩者都是互動專用——不進 `.codex/rules`、不進 daily 固定步驟、不進 `.claude/settings.json` 的 allow。遷移工具的補償控制是 pq2 編號核對＋事前匯出＋writer lock＋副作用 0 才寫＋寫後逐條重算。 |
| **4 permission contract test** | `tests/test_identity_cleanup.py`（編號核對、備份核對、`--apply` 缺參數是用法錯誤、照抄後副作用 0／不照抄有副作用）；`tests/test_research_actions.py::test_prepare_reads_the_graph_read_only_and_never_publishes`（假 driver 擋任何寫入 Cypher）與讀不到圖印「無法核對」。 |
| **5 端到端 smoke** | 真資料只跑 dry-run（2026-10-03：8 條證據等級變動，與 baseline §3 的模擬相同；兩份檔照抄後副作用 0；什麼都沒寫——`git status` 與圖都不變）。`--apply` 在 pq2 go 之後跑。 |

### Skill 轉接層
```powershell
& '.venv\Scripts\python.exe' scripts\sync_agent_skills.py           # 新增 skill 或改 name/description 後
& '.venv\Scripts\python.exe' scripts\sync_agent_skills.py --check   # 交接前驗證兩端無漂移
```

### 佇列段序（2026-09-09）

「有工作存在」的每一種狀態都必須指得出 consumer；段序是封閉字彙，住
`engine_b/queue_segments.py`（段 0 pending 分流 → 段 1 fired 消化 → ~~段 2 reassess 維護~~（2026-09-22 退役） → 段 3
已核准工單 → 段 4 triaged_go → 段 5 forward view backlog → 段 6 覆蓋缺口 → 段 7 主動輪詢）。
機械段（fired 重排、pq2 翻醒）**不吃** `drain_limit_per_run`；研究段共用它。

```powershell
& '.venv\Scripts\python.exe' -m audit invariants --only QueueSegments   # 每段幾筆；分不到段的狀態 FAIL（＝新工作類型沒有 consumer）
& '.venv\Scripts\python.exe' -m engine_b.cli consume-fired             # 段 1
& '.venv\Scripts\python.exe' -m engine_b.todo sync                     # 段 1 的 pq2 型（順便同步待辦池）
& '.venv\Scripts\python.exe' -m engine_b.todo standing-go --run        # 段 2b（常規授權；互動限定，daily 採用歸 P5）
& '.venv\Scripts\python.exe' -m engine_b.cli drain                     # 段 3–4（首行印段 0–1 計數器＋段 5 一行）
& '.venv\Scripts\python.exe' -m webapp status                          # 段 5 的完整版：每檔閉環（到終局幾檔、下一檔是誰、為什麼）
```

段 5 的工單與下一檔選取住 `alpha/closure.py`（`NEXT_PICK_RULE` 七條依序比：第一條是「使用者沒有明示 defer」，倒數第二條「已有基期觀測」只破平手；深度優先由 skill 執行）。

新增一種工作狀態時：先在 `queue_segments.py` 登記它屬於哪一段、誰來取，再寫產生它的程式——
反過來做，`QueueSegments` 會在第一筆資料出現當天變紅，那是設計，不是誤報。

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
靠到期或主動輪詢救）／`expired`（到期；追源型由 daily 轉終局 `watch_expired` 並計數，Phase 1 A3）／`unwatched`（沒有任何
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
- ⚠ **T2 目前沒有排程，只在互動 session 跑。** 2026-08-31 曾放行由 Codex daily agent 無人值守跑 sweep；2026-09-24
  （Phase 1 Step 1.2a）換成 Windows daily 時 sweep 刻意不列（`tests/test_daily_task.py` 的禁用字含 `sweep`），
  那份 review 引用的測試也已不在。之後沒有任何 skill 叫人跑它，心跳也拿掉了「本輪該查」——registry 的
  `last_checked` 在 08-31 與 10-05 之間沒有任何日期，10-05 補跑時兩條在等的一手早已出現（NVDA 擔保 8-K 是 08-17）。
  **2026-10-06 起心跳段 3 每天印「T2 輪詢：可輪詢 N｜該查 M（最久 D 天沒查）｜最後一次 <日期>」**，有該查的、卻超過
  `min_recheck_days` 沒有任何一次輪詢就粗體並進 Discord 摘要行（計數與 `sweep` 同一份篩選：`event_watch.t2_status`）。
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
- **addendum 的 `source_doc` 必須與母文件逐字相同的兩欄：`title`（母文件標題，不加「——addendum」字樣）與
  `section`（2026-10-01 Phase 4 Step 4.2e）。** SourceDoc 每次載入都以那一份 JSON 直接覆寫（loader 契約：一手優先），
  所以誰最後載入誰的值就蓋上圖；addendum 的說明寫進 `_note`，不寫進 title。不一致會出現在健康審查「SourceDoc 與
  抽取 JSON」與 `python -m audit invariants` 的 `SourceDocSync`。修復程序：**以抽取 JSON 為準重載**——先讓所有
  抽取檔對齊（`python loader/migrate_sourcedoc_json_section.py` dry-run → `--apply-json`；只動這兩欄、綁收據的
  舊版先歸檔到 `extractions/superseded/`），圖上落後的值再經 pq2 核准後 `--apply-graph --pq2 <N>` 對齊（或重載）。
  ⚠ 不要在圖上直接改 section／title 而不改 JSON——那正是「只存在圖上、重建就消失」的來源（L10）。

---

## 環境變數

| 用途 | 變數 |
|------|------|
| Engine A 讀寫 | `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、可選 `NEO4J_DATABASE` |
| Engine A 決策唯讀（**不得 fallback 到可寫帳號**） | `NEO4J_DECISION_READER_USER`、`NEO4J_DECISION_READER_PASSWORD` |
| Live holdings | `GSHEETS_SERVICE_ACCOUNT_JSON`、`GSHEETS_SPREADSHEET_ID`、可選 `GSHEETS_SHEET_NAME` |
| X harvest（**只放本機**） | `X_BEARER_TOKEN` |
| Engine C Postgres（可選，預設 SQLite） | `POSTGRES_HOST`／`POSTGRES_DSN` |
| Daily Brief outbound Discord Forum（**只放本機**） | `NOTIFY_DISCORD_WEBHOOK_URL`、可選 `NOTIFY_DISCORD_TAG_USER_ID`、`NOTIFY_CHANNEL_ALIAS`、`NOTIFY_CONTENT_CLASS`、`NOTIFY_MAX_ATTEMPTS`、`NOTIFY_TIMEOUT_SECONDS` |

Sheet 的 credential scope 分兩種：日常全部走 `SCOPES`（`spreadsheets.readonly`），
只有 `scripts/record_trade.py --apply` 會走 `WRITE_SCOPES`（`spreadsheets`）。
這個分離讓 daily brief、beta snapshot、Engine D 等流程不會持有可寫 token。

Sheet adapter 的標準輸出是 `ticker`、`shares`、`currency`、`market_value_base`、`nav_base`、`base_currency`；可直接提供完整標準欄位，或以逐列 mark-to-market `market_usd` 安全正規化成 USD NAV。**禁止退回 `avg_cost` 或 `market_twd` 猜值。**

Price／FX 預設 yfinance（無 API key）。非同幣 FX 缺失或方向不符一律 fail closed。

⚠ **2026-09-24（Phase 1 Step 1.3）起本段是歷史：`.codex/rules` 已清為 0 條，Codex 不在任何無人值守步驟裡**（無人值守只剩 Windows daily，見「Daily」節）。下面保留原文，因為「文字存在不等於 rule 生效」那條教訓仍然適用於任何 rules 檔。

Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，因此 project permission profile 不作 Daily authority。唯一升權來源是 `.codex/rules/stockbot-automations.rules` 的十四個（2026-09-22 Step 0a.1 起 12 個）窄 fixed entry：harvest、Engine C ETL、Alpha purity snapshot、Beta snapshot、pending priority list、catalyst watch、Alpha outcome snapshot、~~decision today~~（2026-09-22 退役）、todo sync、todo ~~reassess-stale~~（2026-09-22 退役）、todo standing-go、Discord publisher、APP materialize、基期實績 XBRL 補值，第一次呼叫就用 `require_escalated` 命中各自 exact outside-sandbox rule；不先失敗再升權重補跑，也不放行任意 Python、PowerShell、Git 或 working tree。state finalizer 只碰 workspace 內本機檔案，刻意不進 rules。修改 rules 後須讓 Codex 重新載入設定；但在要求重啟前先確認 exact rule **確實存在、而且整份檔載入得起來**——重啟不能修復漏寫的 rule，**也不能修復語法錯誤**。

⚠ **文字存在不等於 rule 生效（2026-09-10 事故）。** 一段 Python 式的隱式字串串接不是合法 Starlark，整份 allowlist 因此**完全沒有載入**，二十條 fixed entry 全部落回 Auto-review；而本檔各節慣用的 `Select-String`「字串在不在檔裡」查證**全部是綠的**，因為它們驗的是文字不是載入。唯一算數的查證是拿產品自己的 parser 跑一次（decision 應為 `allow`；整份檔壞掉時它會直接報 parse error）：

```powershell
codex execpolicy check --rules .codex\rules\stockbot-automations.rules `
  -- .venv\Scripts\python.exe -m engine_b.todo standing-go
```

`tests/test_codex_daily_permissions.py` 已把**十四條 prefix 全部**與相鄰禁止動詞接上這支 parser（`ALLOWED_PREFIXES` 是 fixed entry 數量的唯一權威）。⚠ 它只在真的找不到 Codex CLI 時 skip——**恆 skip 的測試與恆綠的測試同形**，所以 `_codex_binary()` 除了 PATH 也會問 app bundle 的安裝點。

**Triage classification surface impact（2026-08-27）：** `engine_b.cli triage` 新增的分類參數只會
atomic 寫本機 `library/leads/pending_leads.json`；`classification-health` 只讀同檔並以 exit 2
回報 active 缺口；互動 migration `scripts/backfill_lead_classification.py --from-json ... --apply`
也只寫同一本機 authority。三者都不讀 credential／private authority、不呼叫 OS security API、
不連網、不碰 `.git`，所以留在 `workspace-write` sandbox，**不新增 unattended rule**。既有
`engine_b.cli drain` 仍只用原 fixed entry 讀 Decision／Sheet／Neo4j context；新增的
`withheld_unclassified_lead` 是本機 validation，沒有新增 capability 或副作用。

**`engine_b.cli triage --classified-by` 的 sandbox impact review 五步（2026-10-01 Phase 4 Step 4.5b）：**

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 與既有 `triage` 同一個寫入：atomic 寫本機 `library/leads/pending_leads.json` 的 `triage.classification.classified_by`（封閉字彙 `engine_b.leads.CLASSIFIED_BY`，argparse 與函式兩層都拒收未登記值）。不讀 credential／private authority、不連網、不碰 `.git`、不開子行程。配套的 refs 鍵 `graph_walk_subject`／`graph_walk_as_of` 走既有 `annotate`（登記在 `config/lead_ref_keys.json`）。 |
| **2 skill／prompt／本檔** | `skills/research-drain/SKILL.md` 段 4 ②（register → annotate → triage `--classified-by interactive:graph_walk`）；本節與上面的 Leads 指令表。 |
| **3 最窄 rule** | **互動專用，沒有新增任何 rule**：daily 走的是 `triage-apply`（分類層），不是 `triage`；`.codex/rules` 與 daily 固定步驟都不含 `--classified-by`。落在本機既有的 `Bash(python *)` 之下，補償控制＝封閉字彙＋心跳把互動 triage 另計（「分類層上次成功」不算它、另印「互動 triage N 則」，pq1 行印「其中互動起的研究 lead N」）。 |
| **4 permission contract test** | `tests/test_engine_b_cli.py::test_graph_walk_research_mints_a_lead_and_triages_it_as_interactive`（未登記值 exit 2）、`tests/test_engine_b_leads.py` 三條（預設值、封閉字彙、佇列段分開計）、`tests/test_company_onboard_skill.py::test_research_drain_graph_walk_lines_parse_with_the_real_cli`（skill 的三行指令拿真 parser 解析）。 |
| **5 端到端 smoke** | 夾具版由 register → annotate → triage → 讀回 refs 與 `classified_by` 跑通（同上第一條測試）；真資料不跑（鑄 lead 只在 Step 4.8 研究啟動時）。 |

**2026-10-02 Phase 5 Step 5.1（#34）增補：字彙多一個值 `interactive:directed`**（使用者點名或 plan 指定題目起的互動研究，不是走圖命中）。
五步逐條對照：①path／side effect／capability 不變（同一個寫入、同一個欄位，只是封閉字彙多一個值）；②skill：`skills/research-drain/SKILL.md` 段 4 ② 補一句點名研究用這個值，本節與上面的指令表同步；
③rule 不變（互動專用、不進任何無人值守 allowlist；daily 的 `triage-apply` 不帶 `--classified-by`）；補償控制照舊——心跳的「互動 triage N 則」與「其中互動起的研究 lead N」都以 `interactive:` 前綴計，新值自動分開計；
④測試：`tests/test_engine_b_leads.py::test_directed_research_is_its_own_classifier_not_a_graph_walk_hit`（新值收、三個同義詞擋）、佇列段分開計那條補新值、
`tests/test_engine_b_cli.py::test_directed_research_triages_as_interactive_directed_through_the_cli`、`tests/test_heartbeat.py` 分類層那條補新值；⑤夾具 smoke 同上；真資料不跑。
既有 cw_dfb 那則（來源 `directed:phase4-plan-4.8`、標 `interactive:graph_walk`）與三則 `directed:sub_backfill`（標成預設的 `triage_semantic_v1`）**不改寫**——lead registry 是 authority，改資料走 pq2（plan §14）。

### Sandbox／private authority 排錯

`workspace-write` 只保證普通 workspace path 操作；它不自動授予 Windows ACL inspection、credential、network、child process 或 `.git` 能力。`library/private/` 是 repo 內的 ignored enclave，但 `storage.relational.initialize_private_root()`／`validate_private_destination()` 會先執行 owner-only 驗證，因此開啟 Decision Store／Engine C／notification outbox 仍可能跨 capability boundary。

遇到 `PrivateStorageVerificationUnavailable`／`access_blocked` 時依序檢查：

1. 記下完整 interpreter、module／script、subcommand 與參數前綴；不可只寫「Python 被擋」。
2. 用 `rg` 在 `.codex/rules/`、canonical skill 與 cron prompt 查同一個 exact command；skill 有命令而 rules 沒有，就是 integration gap。
3. 區分 `verification.status=unavailable` 與 `invalid`：前者先查 sandbox capability，後者才代表 ACL 判準沒通過。
4. 新增或改名 unattended command 時，同一 commit 更新 rule、skill／prompt、本文與 permission test；測試要同時斷言相鄰高權限動詞仍未放行。
5. 用 scheduled task 相同的 `workspace-write`＋首次 `require_escalated` exact command 做 smoke test。只有 rule 已存在但載入版本仍舊時才需要重啟。

Research Action prepare 的固定入口是 `.venv\Scripts\python.exe scripts\prepare_research_action.py --action-file library\leads\action_drafts\<lead>.json`。draft 目錄已 ignore；CLI 只接受該目錄下的 JSON，重跑 server-side validation 並寫 private staging，不 apply、不寫 Neo4j。**它會唯讀查圖**：同 URL 多段檢查（既有），以及 2026-10-03（Phase 6 Step 6.2d）起的入圖副作用核對——READ session 比對本包要 MERGE 的節點與 SourceDoc 的現值，收據存在 RA 紀錄的 `merge_side_effect_check`、packet 印「入圖副作用」一節（會被覆寫的節點欄位、別名聯集、SourceDoc 欄位衝突與日期倒退）；讀不到圖記 `upstream_unavailable`（印「副作用無法核對」，不是「無副作用」）。只印、不放閘。`engine_b.cli list --by-priority` 與 `drain` 在 default store 讀不到 Decision／Sheet／Neo4j context 時 exit 2，不再把持股 silently 降成空集合。

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

## 非美股 filing 抓取（台股 MOPS／瑞典 MFN／英國 RNS／日股 TDnet）

⚠ **要查分部附註（IFRS 8）就抓財報，不要抓股東會年報**（2026-09-04 實測）。
MOPS 的 `t57sb01` 分兩區，`mtype` 決定查哪一區：

| `--kind` | MOPS 區（`mtype`） | 內容 |
|---|---|---|
| `annual_report`／`meeting_*` | `F` 股東會相關 | 股東會年報、議事手冊、議事錄——**不含財務報表附註** |
| `consolidated_financial_statement` | `A` 財報 | IFRSs 合併財報（含「十四、部門資訊」） |
| `separate_financial_statement` | `A` 財報 | IFRSs 個別財報（無子公司者用這個） |

```powershell
& '.venv\Scripts\python.exe' fetchers\mops.py --co-id 3363 --year 115 `
    --kind consolidated_financial_statement --list
```

**事發：** 3081 的股東會年報 112 頁／281,784 字，`部門`／`IFRS 8` 命中 0 次，於是被記成
「單一部門公司」——但那份文件 `Independent Auditor` 也是 0 次，**它根本不含財報附註**。
改抓 `mtype=A` 後，附註逐字寫著「歸屬為單一報導部門」。結論相同，但**這次是證據**。

⚠ 下載端的 `mtype` 必須與列檔時相同，否則 MOPS 不回下載路徑；舊版寫死 `F`，
錯誤訊息卻說「檔名可能有誤，或該文件已下架」——**檔名其實是對的**（L12 一表兩義）。

**Sandbox impact review（2026-09-04）：** 本次只新增 `--kind` 的兩個選項與內部
`mtype` 對照，**未新增 CLI 名稱、未新增網路主機、未碰 credential／private authority**；
`.codex/rules` 的 `fetchers\mops.py` 是 prefix rule，涵蓋新參數，**十六條 entry 數量未變**。


**台股：`fetchers/mops.py`**（互動式入口，**未加入任何 unattended routine**）。

```bash
python -m fetchers.mops --co-id 3081 --list                 # 先看有哪些文件
python -m fetchers.mops --co-id 3081 --kind annual_report   # 抓年報（預設只取最新修訂）
python -m fetchers.mops --co-id 4971 --kind annual_report --all-revisions
```

輸出與 `edgar.py` 一致：`library/raw/{doc_id}.txt` ＋ `.meta.json`。
年報「營運概況」含最近二年度占進（銷）貨總額 10% 以上之客戶——台股客戶集中度的一手來源。
2026-09-17 起 meta 帶 `published_at`（MOPS 列表「上傳時間」民國轉西元，對照組 `mops_3363` 115/05/07 → 2026-05-07）、
`published_at_method=filing_metadata`、`published_at_basis`、`retrieved_at`；上傳時間解析不到就留 null 並印出來，**不用抓取日冒充**。
⚠ 沒有子公司的公司只申報「IFRSs個別財報」（實測聯亞 3081 的 114／115 年財報區合併財報 0 份）——`--kind consolidated_financial_statement`
會得到「本公司未申報此類」，照訊息換 `separate_financial_statement`，那不是查無文件。

**⚠ 不要改抓公司 IR 網站。** 多數台廠年報 PDF 連結是動態載入，靜態抓取只拿得到零散附件
（2026-08-28 實測聯亞只取得「前十大股東關係表」，一度被誤判成「可抽文字為 0」）。

fetcher 已封裝的**五個**坑，自己刻之前先讀 `fetchers/mops.py` 的 docstring：
① 兩段式下載（`step=9` 回的是 HTML，裡面才有帶時戳的一次性 PDF 路徑；直接猜
`/pdf/{filename}` 一律 404）；② 列表頁是 **big5**，不設 encoding 會拿到亂碼；
③ `--year` 是**民國查詢年度**而非資料年度，查 115 回的是 114 年度年報；
④ 同年度可能有多份修訂（原始版 F04 ／股東會後修訂本 F11），共用 doc_id 會**靜默覆蓋**，
預設只取最新並印出略過訊息。

⑤ **PDF 會吐出 CJK 相容表意文字（U+F900–U+FAFF）**（2026-09-17 實測）。它們與正常字
**視覺完全相同**但碼位不同——4971 年報 50 個、4979 年報 126 個，「系列原料」的「列」是
U+F99C 而不是 U+5217。後果是逐字引用比對、`grep`、入圖前的 quote 核對**全部靜默失敗**，
而失敗長得像「年報沒寫這句」。`pdf_to_text` 已對輸出做 **NFC** 正規化（相容表意文字有
canonical decomposition，NFC 會映射回標準碼位；**刻意不用 NFKC**——它會把財報表格的全形
數字改成半形，那樣「逐字引用」就不再逐字）。
⚠ **既有入庫檔不會自己修好**：`mops_4979_annual_report_2025` 與
`intelliepi_4971_annual_report_fy2025_20260827` 仍含相容字元（各 126／2 個），要清理必須
重抓並走 `supersedes_extraction_sha256` 更正走廊。查證：

```powershell
& '.venv\Scripts\python.exe' -c "from pathlib import Path;import glob;print([(p,sum(1 for c in Path(p).read_text(encoding='utf-8') if 0xF900<=ord(c)<=0xFAFF)) for p in glob.glob('library/raw/*.txt') if any(0xF900<=ord(c)<=0xFAFF for c in Path(p).read_text(encoding='utf-8'))])"
```

**瑞典（Nasdaq Stockholm／First North）：`fetchers/mfn.py`**（互動式入口，**未加入任何 unattended routine**；2026-09-17 Phase 1 Step 1.1）。

```bash
python -m fetchers.mfn --company sivers-semiconductors --list --match "Q2 2026"     # RSS 視窗內的公告（REG＝法定）
python -m fetchers.mfn --url https://mfn.se/cis/a/sivers-semiconductors/<headline-slug>-<id>   # 正文＋附件 PDF
python -m fetchers.mfn --company sivers-semiconductors --match "reports q2 2026" --latest
```

輸出與 `mops.py` 一致；附件 PDF（期中報告本體）各自成 `{doc_id}_att{N}`。三個坑：①瑞典文與英文各發一則、同一事件，
預設只取英文（`--lang all` 才兩則都抓）；②日期只認公告頁 JSON-LD `datePublished`（UTC，＝RSS pubDate），頁面的
`publish-date` 是當地時間，沒有 datePublished 就拒寫；③附件不在 RSS 裡，只掛在公告頁「Bifogade filer」，且原始 HTML
的 `<a>` 屬性跨行（第一次 smoke 就因此零附件）。⚠ 探到 404 先檢查 URL 是否被截斷（尾端要有 8 碼 id）。

**英國（LSE RNS，經 investegate 鏡像）：`fetchers/rns.py`**（互動式入口，**未加入任何 unattended routine**）。

```bash
python -m fetchers.rns --company IQE --list --match results          # 清單走 /company/IQE/announcements（AJAX）
python -m fetchers.rns --url https://www.investegate.co.uk/announcement/rns/iqe--iqe/<headline-slug>/<id>
python -m fetchers.rns --company IQE --match "FY 2025 Financial Results" --latest
```

四個坑：①公司頁 HTML 裡零筆公告，清單是 AJAX；②日期不在 metadata（JSON-LD 只是 WebPage），一手日期是 RNS 本體開頭
的 dateline（`IQE PLC / 28 May 2026`），清單另有日期＋時間，兩者都記進 `published_at_basis`；③「Summary by AI」不是一手，
只取 `news-window` 內的 RNS 本體；④站點會整段時間回 502（2026-09-16 晚間半小時）——5xx／timeout 印「站點暫時不可用」
並重試兩次，404 印「這則不存在」不重試，兩句話對應兩個下一步（等 vs 換 id）。
⚠ IQE 年報 PDF 的查核報告雙欄交錯、pdfplumber 也讀不出來；going concern 附註要抓**年度業績 RNS 全文**
（2026-05-28 `rns_iqe_9588930`，「2.2 Going concern」段完整可讀）——這才是該待辦卡住的真正原因。

**Sandbox impact review（2026-09-17，Phase 1 Step 1.1，兩支新抓取器）：** ①path／side effect／capability——只連
`mfn.se`、`mb.cision.com`、`investegate.co.uk`，無憑證、只寫 `library/raw/`、不碰 identity／ACL／private authority／`.git`；
②本節、`docs/ARCHITECTURE.md` §4、`skills/source-trace/SKILL.md` 路由行同 change 更新；③**不新增 unattended rule**
（fixed entry 維持二十條）——兩支都是互動式入口，smoke 只跑過一次，還沒累積到「daily 遇到 .ST／.L 就自動抓」的量測（INV-5）；
④`tests/test_codex_daily_permissions.py::test_fetchers_directory_is_not_broadly_allowed` 明確斷言 `fetchers\mfn.py`／
`fetchers\rns.py` **不在** allowlist；⑤端到端 smoke 以互動 session 跑（不是 scheduled task 的 sandbox——它們本來就不進排程）：
`mops_3081_separate_financial_statement_202602`（29 頁）、`mfn_sivers_semiconductors_6543505f`（＋附件 `_att1`）、
`rns_iqe_9588930`（50,894 字）三份落地，`published_at` 分別取 MOPS 上傳時間、JSON-LD datePublished、RNS dateline。

**日股：** 有価証券報告書走 EDINET，受注残高與決算數字走決算短信（TDnet）。
⚠ EDINET API v2 需 subscription key（未申請）；2026-08-28 實測改抓 TDnet 決算短信正本
即取得所需資料。尚未封裝成 fetcher。

**已納入 Daily（2026-08-28 完成 sandbox impact review）。** `fetchers\mops.py` 是第十六個
fixed entry，與 `edgar.py` 同構：無憑證、不碰 Windows identity／ACL、不寫 private authority、
不觸 `.git`，只把公開文件下載到 `library/raw/`。Daily pq1 遇到台股標的時直接以
`require_escalated` 命中該 exact rule。

### 基期實績 XBRL 補值（P7-a，2026-09-10 完成 sandbox impact review）

`scripts\backfill_fiscal_year_results.py` 已納入 Daily。五步結論：

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 網路只連 `data.sec.gov`（companyfacts）與 `www.sec.gov`（company_tickers.json），與既有 `fetchers\edgar.py` **同一組主機、無憑證**。寫 Engine C SQLite 的 `manual_observations`（ignored private runtime）。不碰 `.git`、不碰 tracked 檔、不碰 Google Sheet、不連 Neo4j。 |
| **2 skill／prompt／本檔** | daily prompt 步驟 3 加一行（`--write`）；`skills/daily-brief/SKILL.md` 健康段加「寫入 W／跳過 S／拒寫 R」；本節。 |
| **3 最窄 rule** | `pattern=[".venv\\Scripts\\python.exe", "scripts\\backfill_fiscal_year_results.py"]`。**刻意只放行這一支**：同目錄的 `record_mechanical_observation.py` 接受任意 `--field`，它的 surface 是「registry 裡所有 mechanical 欄位」而不是一個。 |
| **4 permission contract test** | `test_xbrl_backfill_is_allowed_but_the_generic_observation_writer_is_not`（允許項＋三個相鄰禁止動詞）＋ `test_xbrl_backfill_can_only_write_one_mechanical_field`（斷言腳本內建那道閘門）。 |
| **5 端到端 smoke** | 見下。 |

**⚠ 這支能進 allowlist 的唯一理由是它只寫得了一個欄位，而那道閘門在腳本裡。**
`append_manual_observation` 本身**不擋** judgment 欄位（它只在 mechanical 時多驗數值是否可機械比對），
所以「只寫 mechanical」不能靠 `FIELD` 常數沒被改過——腳本啟動時查 `observation_fields` registry，
非 mechanical 直接 `exit 3`，且沒有任何 CLI 參數可以換掉欄位。放行與收緊必須同時發生（L15）。

**另外五道收緊**（都在 `fetchers/edgar_xbrl.py`，各有實測事故）：白名單 tag 歧異拒寫｜
只收 10-K／20-F 且期間 300–400 天｜單一計價單位不換算｜`source_filed_at` 取 accession 的
`filed` 日期（**不得用今天**，INV-6）｜基期超過 550 天拒寫。

**⚠ 非美股（25 檔）本支一律不碰**，記 `no_cik` 並列進報告。TWSE／EDINET／DART／KIND 各有各的
格式，硬套會在 `source_ref` 上造假——那正是 L11 記過的坑。

**⚠ `fetchers/` ~~不是整包放行。只有 `edgar.py` 與 `mops.py` 兩支公開文件下載器在列~~
（2026-09-17 Phase 2 Step 2.2 起改為**一支都不在列**）。** daily 的研究層關閉後，抓原文只
發生在互動 session，那兩支沒有任何無人值守呼叫端。同目錄的 `gsheets.py` 使用 Google service
account 憑證，屬 credential-bearing surface。
`tests/test_codex_daily_permissions.py::test_fetchers_directory_is_not_broadly_allowed`
會擋下把整個目錄、任一支或 `-m fetchers` 放行的寫法。要放行其中任何一支都必須另做一次
impact review。

### FX 觀測同步（2026-09-19 完成 sandbox impact review）

`scripts\sync_fx_observations.py` 是 Windows daily 的 ③（在 ⑱ 心跳之前，所以心跳當天讀得到最新狀態）。
~~由獨立 Windows 排程 `StockBotv2-FxSync` 每日 06:55 觸發~~——2026-09-24 Phase 1 Step 1.2a 併入 daily、2026-09-25 1.2b 刪除該工作；
下表是 2026-09-19 的 impact review 原文（第 3、5 列講的「獨立排程」即指那個已刪的工作）。

**它要消掉的失敗模式：** 消費端只接受與現價 `bar_date` 相差 ±3 天內的匯率觀測
（`alpha/fx.py::FX_AS_OF_TOLERANCE_DAYS`），而 2026-09-13 手抄的四筆每一筆的 `_note` 自己就寫著
「現價 bar_date 換了就要補新的一筆」——**沒有任何東西在補它**。實測 2026-09-19：過期 8 天，
6680.HK／HEXA-B.ST／XFAB.PA／XPEV 四檔（當時的）隱含報酬全部算不出來，而**它不會壞、不會報錯、測試不會紅**（估值鏈已於 2026-09-23 退役；FX 觀測的鮮度契約仍在，心跳照印）。

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 網路只連 yfinance（`{base}{quote}=X` 日線），**與現價同一個 provider**——匯率用不同來源會讓「fair value 與現價是不是同一把尺」多一個無從核對的差。寫 Engine C SQLite 的 `manual_observations`（ignored private runtime）。不碰 `.git`、不碰 tracked 檔、不碰 Google Sheet、不連 Neo4j。 |
| **2 skill／prompt／本檔** | 本節；心跳段 1 已有常駐的 FX 新鮮度那一行（容忍窗 import `alpha.fx` 的 SSOT，不重寫那個 3）。 |
| **3 最窄 rule** | **不需要**——它跑在獨立 Windows 排程裡，不經 Codex，與心跳同一個理由（Codex 沒起來時它照跑）。`tests/test_fx_sync.py` 鎖「rules 的 `pattern=[...]` 不得出現 `sync_fx_observations`」。 |
| **4 permission contract test** | `tests/test_fx_sync.py` 5 條：registry 閘門會擋｜沒有任何 CLI 旗標換得掉欄位／作者／標的｜幣別對從 ledger 導出（**測行為不掃原始碼字串**）｜不在 Codex rules｜每一組都落在 written／skipped／failed（INV-3）。 |
| **5 端到端 smoke** | `schtasks /Run /TN StockBotv2-FxSync` 走真正的排程路徑實跑，`Last Result 0`；四筆寫入後四檔 readiness `blocked → ready`。 |

**⚠ 這支能進無人值守的唯一理由是它只寫得了一個欄位，而那道閘門在腳本裡。**
`fx_rate` 在 `engine_c/observation_fields.py` 是 `verifiability='mechanical'`，依 2026-09-04 定案
**不需要 pq2**；但「只寫 mechanical」不能靠 `FIELD` 這個常數沒被改過——腳本啟動時查 registry，
非 mechanical 或 `requires_user_approval` 一律 `exit 3`，**沒有任何 CLI 參數可以換掉欄位**。
放行與收緊必須同時發生（L15）。

**⚠ 幣別對從既有觀測導出，不手寫清單**（L16）：今天資料支持的就是已經有人建立過的那幾組。
**新標的的第一筆仍然是人工**——那時心跳段 1 會說「FX 觀測 N 檔」而那一檔不在裡面。
刻意不去猜「哪些標的可能需要匯率」（那要跑整條 view，而且會猜錯）。

```powershell
& '.venv\Scripts\python.exe' scripts\sync_fx_observations.py --dry-run   # 只印會寫什麼
& '.venv\Scripts\python.exe' scripts\sync_fx_observations.py             # 同步
Get-Content library\private\heartbeat\daily_run_<YYYY-MM-DD>.json          # 03_fx_sync 的 status／exit
```


### 台股月營收與重大訊息（Phase 6 / D15，2026-09-17 完成 sandbox impact review）

**兩件事的性質相反，所以落點也相反**——這是本節唯一要記住的判準：

| | 重大訊息 | 每月營收 |
|---|---|---|
| 來源只有多久 | **只有前一營業日那一批** | 歷史頁按年月**永久可查** |
| 漏抓的後果 | **永久漏，補不回來** | 隨時 `--backfill` 補得回來（L10） |
| 落點 | **進 daily harvest**（走既有 `crons\harvest_leads.py` entry） | **互動式入口**，不進無人值守 |
| 該補時誰說話 | harvest 的 `fetch_failed` 現形在心跳第 1 段 | 心跳第 1 段印「落後 N 個月」 |

```powershell
# 月營收（互動式；每月 11 日後跑一次 --sync 就跟得上）
& '.venv\Scripts\python.exe' -m engine_c.monthly_revenue --ticker 3081.TWO
& '.venv\Scripts\python.exe' -m engine_c.monthly_revenue --sync
& '.venv\Scripts\python.exe' -m engine_c.monthly_revenue --backfill 24

# 抓取層（要看原始列或某個歷史月份時才用）
& '.venv\Scripts\python.exe' -m fetchers.mops_open_data --revenue --market tpex --year 2026 --month 7
& '.venv\Scripts\python.exe' -m fetchers.mops_open_data --announcements --ticker 3105.TWO
```

**sandbox impact review 五步：**

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 重訊在既有 `crons\harvest_leads.py` 底下新增三個**公開、無憑證**主機：`openapi.twse.com.tw`、`www.tpex.org.tw`、`mopsov.twse.com.tw`。只 `register` lead（進 pending 交下輪 triage），不自動 triage、不入圖、不寫 Engine C、不碰 `.git`。月營收寫 Engine C SQLite 的 `monthly_revenue_observations`（ignored private runtime），**但不在無人值守路徑上**。 |
| **2 skill／prompt／本檔** | 不動 daily prompt（重訊走既有 harvest 步驟）；本節；`.codex/rules` 的 harvest justification 明寫新主機。 |
| **3 最窄 rule** | **沒有新增任何 rule**（仍是 15 條）。重訊重用既有 entry；月營收刻意留互動式——要改成排程必須重做一次本 review。 |
| **4 permission contract test** | `test_mops_watcher_reuses_the_harvest_entry_and_admits_its_new_hosts`（條數不變＋三個主機都寫在 justification 裡＋抓取器不得出現在 allowlist）、`test_monthly_revenue_stays_an_interactive_entry`、`test_heartbeat_monthly_revenue_line_reads_no_network`（心跳的零網路契約）。 |
| **5 端到端 smoke** | 2026-09-17 實跑：7 檔台股各 24 個月月營收入庫（兩個來源在 2026-08 交叉一致、衝突 0）；重訊首跑抓到 3105.TWO 一則並正確解析出 `co:win_semiconductor`。 |

⚠ **這一輪撞到的兩個坑，都寫成測試了：**
① **歷史頁末尾那個數字是註冊地不是流水號**（`_0` 本國／`_1` 外國）——只抓 `_0` 時 4971.TWO（IET-KY）
在 24 個月回補裡一筆都沒有，而當期 API 有它。
② **`.codex/rules` 是 Starlark，不吃 Python 的隱式字串串接**——多行 justification 必須用 `+`
串接。寫成隱式串接時整份 allowlist 載入失敗，11 個 execpolicy 測試同時變紅（與 2026-09-10
那次同形，這次是測試先攔下來的）。


### 台股季報股數（Phase 7 旁支開發「台股歷史股數」，2026-10-05 完成 sandbox impact review）

已定價①（自家三年 P/S 百分位）要「當天的市值」＝當天收盤 × **當時已知的**股數；TWSE／TPEx 開放資料只有當期股本，
所以台股的這一格到 2026-10-05 一律缺席。來源是 MOPS 資產負債表彙總 `ajax_t163sb05`（一季一份、全市場），
**與月營收同性質**（按季永久可查，漏抓補得回來，L10）→ **互動式入口**，不進無人值守；心跳第 1 段印最舊哪一季、落後幾季、
核對沒過幾筆。

```powershell
# 每季法定期限（5/15、8/14、11/14、次年 3/31）過後跑一次 --sync 就跟得上；重跑冪等
& '.venv\Scripts\python.exe' -m engine_c.tw_share_capital --ticker 3081.TWO
& '.venv\Scripts\python.exe' -m engine_c.tw_share_capital --sync
& '.venv\Scripts\python.exe' -m engine_c.tw_share_capital --backfill 14
```

- **股數**＝股本（千元）×1000 ÷ 面額 10 元 − 母公司暨子公司持有之庫藏股；**交叉核對**：權益（歸屬母公司業主；表上是「--」
  而且沒有非控制權益時用權益總計）÷ 每股參考淨值。差 >2% → `mismatch`：照寫進表、讀取端整季不用、`--ticker` 與回補報表逐筆印
  ——面額不是 10 元的公司在這裡現形，不會被靜默算錯十倍。
- **版型**：只收一般業（23 欄）與異業（22 欄，「權益總額」）——表頭逐字比對（`fetchers.mops_open_data.BALANCE_SHEET_TEMPLATES`）。
  銀行、金控、保險、證券期貨的半年報期限比一般業晚，套一般業期限會提早看到（INV-6）→ 拒收、回補報表列出；表頭變了同樣拒收。
- **可知日**＝一般業法定期限（季後 45 日、年報 3 個月；`available_on_basis=statutory_deadline_only`），是上界、不是公告日。
- 季與季之間的配股由 `corporate_actions` 的 split（yfinance 記成分割）乘上去（`alpha.three_questions.shares_on`）。

**sandbox impact review 五步：**

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 新端點 `mopsov.twse.com.tw/mops/web/ajax_t163sb05`（POST、公開、無憑證；主機已是月營收在用的那一台）。寫 Engine C SQLite 的 `tw_share_capital_observations`（ignored private runtime、可重建）。**不在無人值守路徑上**；心跳只讀本機。 |
| **2 skill／prompt／本檔** | 不動 daily prompt；本節。plan（2026-10-05-001）原寫「S3 daily 接線」——照月營收先例改成互動式＋心跳計數器，比排程窄。 |
| **3 最窄 rule** | **沒有新增任何 rule**。要改成排程必須重做一次本 review。 |
| **4 permission contract test** | `test_tw_share_capital_stays_an_interactive_entry`（rules 與 harvest 都不得出現）、`test_heartbeat_monthly_revenue_line_reads_no_network`（擴充：`sync_latest`／`fetch_balance_sheet` 不得出現在心跳）。 |
| **5 端到端 smoke** | 2026-10-05 實跑：`--backfill 14` 寫入 12 檔 × 14 季＝168 筆、失敗 0；交叉核對攔下 4 筆（3081.TWO 2026Q2 股本含待分配股票股利、3017.TW 三季）；月營收 `--backfill 48` 補到 2022-10；12 檔台股已定價① 12/12 由缺席變有值（第 88–100 百分位，窗 1,087–1,092 天、覆蓋率 1.0）。R2 另抽線上 115Q2：上市收 1,053 列、拒 31 列（銀行、金控、保險、證券），上櫃收 884、拒 7（證券期貨）。 |

---

## 遠端操作

**沒有對外的寫入入口。** 手機以 Claude Code Remote Control 連本機 session，走的是同一套本機工具與人工 gate。
遠端 graph server、tunnel 的兩條 hostname 與 claude.ai connector 已於 2026-09-24 停用、2026-09-25（Phase 2 Step 2.1）
連同程式刪除；Cloudflare Tunnel 只剩 APP 一條（`deploy/cloudflare/README.md`）。
Research Action 的本機協定見 `prompts/intake_protocol.md`；舊的遠端架構與操作說明逐字封存於
`docs/archive/2026-09-25-remote-access-architecture.md`，**不要照著重新啟動**。

---

## （歷史／fallback）雲端 egress 白名單

2026-07-24 首跑時 cloud 直連 `substack.com` 與 `www.sec.gov` 收到 proxy 403，實際是 claude.ai cloud environment 的 Network access allowlist，不是平台硬限制。現行 daily 已在本機（weekly 已於 2026-09-24 退役），以下只在日後重啟 cloud fallback 時適用。

- 白名單需含：`sec.gov`、`*.sec.gov`、`substack.com`、`*.substack.com`，並保留 default package-manager 清單
- **`WebSearch` 不受影響**（是工具不是 egress）；受影響的只有直接抓取（`WebFetch`／`curl`／`urllib`）
- 設計取捨：維持 Custom 白名單較安全——本 routine 天職就是讀不受信任的網路內容且握有圖寫入能力，收斂 egress 可壓低 prompt-injection 外流面

---

## 本機音訊追源

官方 podcast／錄音沒有 transcript 時用 `scripts/transcribe_audio.py` 跑 `faster-whisper`；預設 CPU `small.en`，模型與完整逐字稿只存 ignored `library/private/`。ASR 只提供 timestamp locator，**不自行提高 evidence tier**；精確技術詞與 quote 仍須回聽核對。cloud fallback 不假設有此工具。

---

# 協作與排程程序

> 以下六節於 2026-09-04（Phase 3.9）自 `AGENTS.md` 搬入。
> **判準留在 `AGENTS.md`，程序在這裡。** 分野：
> **OPERATIONS 被改壞 → 跑不起來；AGENTS 被改壞 → 跑起來了，但做錯事。**

## 雙代理協作（Claude Code / Codex）

- **研究 skill 唯一權威：** `skills/<name>/SKILL.md`。`.agents/skills/`（Codex）與
  `.claude/skills/`（Claude Code）是生成的薄轉接層，不直接手改。
  新增 skill 或改 `name`／`description` 後跑 `python scripts/sync_agent_skills.py`；
  交接前用 `--check` 驗證兩端無漂移。
- **平台設定分開：** Codex 設定放 `.codex/`，Claude Code 本機設定放
  `.claude/settings.local.json`；共用行為呼叫同一支 repo Python 程式，
  不在兩份 hook 裡複製業務邏輯。
- **切換交接：** 本機 Codex／Claude Code 序列切換可沿用 `master` 與同一組 private
  authorities，但下一個 agent 必須重新讀 `git status --short`、`todo_pool.json`、
  對應 action／decision receipt，**不得依賴上一個 session 的自然語言摘要**。
  交接訊息至少附：目前 plan 路徑、進行中的編號、`git status --short`、
  最後一次驗證命令與結果。
- 本機開發 agent 可以是 Claude Code 或 Codex；手機經 Remote Control 連的是本機 Claude Code session。

### 開發流程（Agent Development Flow，2026-09-07）

判準與流程模型在 [`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md)，執行步驟在
`skills/development-flow/SKILL.md`。**這裡只放怎麼跑。**

```powershell
& '.venv\Scripts\python.exe' -m pytest tests\test_agent_workflow.py -q      # 流程文件的防腐測試
& '.venv\Scripts\python.exe' scripts\verify_test_nonvacuity.py --only AgentFlow   # 證明上面那些斷言會紅
& '.venv\Scripts\python.exe' scripts\sync_agent_skills.py --check           # 兩端轉接層無漂移
```

⚠ **沒有新的 executable surface**：本流程不新增 CLI、不新增排程入口、不改任何
`python -m <module>` 命令字串，`.codex/rules` 的 `prefix_rule(` 仍是 16 條（`tests/test_codex_daily_permissions.py` 斷言）。
它改變的是 agent 的行為，不是機器的權限——**因此沒有 sandbox impact review 要做**。

### Push 政策（2026-07-22 使用者定案）

push 是常規動作——session 收尾（邏輯 commits 完成後）把 master push 到 origin，
不需逐次人工確認。私有隔離依 `.gitignore`（`library/private/`、`.env`）；
**push 前 sanity check：`git ls-files library/private` 應為空。**

四個 leads state 檔不再屬於 push 範圍；它們固定留在原本本機路徑、由 writer lock 保護，
並隨 private backup 進 `engine_b_state.zip`。Daily 不得以 unattended Git 命令發布它們；
一般 session push 前以 `git check-ignore` 與 `git ls-files` 確認 ignored／untracked。

## Codex sandbox：判準的落點

> ⚠ **排錯順序、14 條 fixed entry 與 retry 邊界的完整內容已經在本檔上方**
> （「Sandbox／private authority 排錯」與 harvest 那一節）。**不要在這裡再抄一份**——
> 2026-09-04 從 `AGENTS.md` 搬入時就差點造出第二份清單，而「清單會腐壞，判準不會」
> 正是這次搬移要消除的違規。

`workspace-write` 是路徑邊界，**不是「repo 內所有 OS 能力都可用」**。
命令即使只碰 repo 內路徑，只要還會呼叫 Windows identity／ACL（`whoami`、`Get-Acl`、
`icacls`）、credential store、網路、child shell、`.git`，或 permission profile 對該子路徑
有更窄限制，仍可能需要 outside-sandbox exact rule。`library/private/` 雖在 repo 內，
開啟 authority 前會驗 owner-only ACL，屬 capability-sensitive path。

**排錯先看 command surface，再碰 ACL 或要求重啟。**
⚠ **重啟只會重新載入**已存在**的 rule，不能補上一條根本沒寫的 rule。**
rule 缺漏時不得把重啟當修復。詳細五步見上方「Sandbox／private authority 排錯」。

### Sandbox impact review 結論（2026-09-04，Phase 6／7 新增的三支入口）

本次新增 `scripts/backfill_source_dating.py`、`scripts/rank_forward_returns.py` 與
`portfolio/alpha_exposure.py`。**三者都不進 unattended rule**，結論如下：

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `scripts/backfill_source_dating.py` | 寫 Neo4j 的 SourceDoc metadata（白名單兩個日期欄位） | Neo4j bolt（本機），不碰 identity／ACL／credential | **互動專用**。它會寫圖，就算欄位再窄也不該無人值守跑 |
| `scripts/rank_forward_returns.py` | 唯讀；讀 Neo4j ＋ yfinance | 對外網路（yfinance） | **互動專用**。它是研究檢核，不是排程產出（2026-09-23 已隨排序退役刪除，`7db4e1f`） |
| `portfolio/alpha_exposure.py` | 純函式，無 I/O | 無 | 不是 CLI，無 surface |

查證（三者都不該出現在 rules）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules `
  -Pattern 'backfill_source_dating|rank_forward_returns|alpha_exposure'
```
⚠ 十六條 fixed entry **數量未變**；`tests/test_codex_daily_permissions.py` 斷言
`prefix_rule(` 恰好 16 次，加一條就會紅。

### Sandbox impact review 結論（2026-09-05，Alpha Investment Read Model）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m briefing alpha-card` | 唯讀；讀 Neo4j＋Engine C SQLite＋Decision Store（`mode=ro` sqlite，不開可寫 store）＋thesis JSON | 與（已退役的）`decision_lab today` 相同的本機資源，無新增網路主機、憑證或 identity／ACL 呼叫 | **互動專用**。新 CLI 名稱，不進 unattended rule |
| ~~`python -m decision_lab today`~~（當時的 fixed entry；2026-09-23 隨研究側退役） | 新增「Alpha Card 摘要」區：對排序前 5 檔組卡；整批共用一個 Neo4j provider（排序只算一次）與一個 Engine C provider，Decision Store 走唯讀連線 | **無新增 capability**——三者 `today` 原本就讀（ranking、`_read_financial`、store）；全程 fail-soft，讀不到只讓該區寫「未提供」 | 命令字串未變、rule 未動。實測 `today` 全程 104 秒（含 Sheet 與 Neo4j），Alpha Card 區單獨計時見 [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md)（2026-09-20 自 ROADMAP 搬出） |

查證（新入口不該出現在 rules；十六條 fixed entry 數量未變）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'briefing'
```

### Sandbox impact review 結論（2026-09-05，Causal Fundamental Model）——已封存
FY+1 因果橋模型已於 2026-09-23（Step 0b.1b-C/H 2/2）退役；基期實績／指引的 mechanical 觀測與假設 ledger 仍活（見下方「Causal Fundamental Model：怎麼跑」）。原 review 表封存於 archive。

### Sandbox impact review 結論（2026-09-06，Research Refresh／Dependency Invalidation v1）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m briefing refresh <T> [--scenario …]` | 唯讀：Engine C 快照時序（`snapshot_series`）＋兩個 ledger 欄位的歷史列（`observation_history`）＋假設 ledger＋`library/leads/event_watches.json`＋`thesis/lifecycle.json`＋圖投影差集；情境只在記憶體疊事件，**不寫任何 authority** | 與 `alpha-card` 相同的本機資源；無新增網路主機、憑證或 identity／ACL | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `python -m briefing alpha-card`／~~`decision_lab today`~~ 的 Alpha Card 摘要（既有） | 多跑一次變更偵測（同上的唯讀來源）＋純函式 resolver；多一個 `refresh_status` section 與精簡卡 `refresh` 欄 | 無新增（同一 Engine C 連線、本機檔案）；每檔多一次 `get_structural_changes_since` 投影（記憶體快取） | 命令字串未變 |
| `python -m alpha assumptions <T> --add`（既有） | spec 多三個可選欄位 `calibration_refs`／`comparison_refs`／`review_conditions`；仍只 append private ledger | 無新增 | 既有判定不變（互動專用） |
| `python -m engine_b.event_watch add --wake-hypothesis oa_*`（既有） | `hypothesis_ref` 可指向假設 id；fired 後由 refresh 引擎標 review_required | 無新增 | 既有判定不變 |

查證（新入口不該出現在 rules）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'refresh'
```

### Valuation Model／Base-case Implied Return／Entry Logic（2026-09-06 Step 1–3）——已退役、已封存
三者（`alpha/valuation`、`alpha/implied_return`、`alpha/entry` 與 `briefing valuation／implied-return／entry` 三個子命令）
已於 2026-09-23（Phase 0 Step 0b.1b C／F／H 組）整組退役；估值假設／horizon／entry 判準三本 ledger 的檔案留在
`library/private/alpha/`（L10），不再消費。六個小節（三份 sandbox review ＋ 三份「怎麼跑」）逐字封存於 archive。

### Sandbox impact review 結論（2026-09-07，Web App／API／Abstention ledger／Step 5）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m webapp materialize [T ...] [--as-of] [--dir]`　⚠ **本列的「互動專用」判定已於 2026-09-08 改判**（見下方該日 review：materialize 已納入 Daily 收尾，成為第十七個 fixed entry；`serve` 仍不在列） | 寫 **derived cache**（`library/private/app/analyst_view/*.json`，atomic）；讀 Neo4j／Engine C／private ledger。**不寫任何 authority**、不入圖、不建 decision | 與 `alpha-card` 相同的本機資源；無新增網路主機或憑證 | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `python -m webapp serve [--host] [--port] [--dir]` | **開一個本機 listener**（預設 `127.0.0.1:8790`）。唯讀：無寫入端點、無模型執行、無外部抓取 | ⚠ **新增 executable surface**：綁定本機 port。非 `127.0.0.1` 需明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則程式拒絕啟動。外部認證邊界是 Cloudflare Access（`deploy/cloudflare/README.md`），不是本程式 | **互動／長駐專用**，不進 unattended rule |
| `python -m webapp status｜verify [--dir]` | 唯讀：只讀 artifact 目錄 | 無 | 互動專用 |
| `python -m webapp materialize --coverage｜--watches [--state-dir]`（2026-09-08 B2b；⚠ `--coverage` 已於 2026-09-26 由 `--graph-walk` 取代，見 Phase 2 Step 2.6 的 review） | 寫 **derived cache**（`state/coverage.json`／`state/watches.json`，atomic）；`--coverage` 讀 Neo4j（`coverage_gaps.scan` ＋ `duplicate_nodes.scan`，同一個 session 兩份查詢），`--watches` 只讀 repo 內的 `event_watches.json` 與 `pending_leads.json`。**唯讀**：不喚醒 watch、不 mark-checked、不改 lead | `--coverage` 同覆蓋缺口與重複節點兩份掃描（本機 Neo4j bolt，皆唯讀；兩支 CLI 已於 2026-09-29 退役）；`--watches` 無網路、無憑證 | **互動專用**。同一命令字串的新 flag，不進 unattended rule；Phase A 排進 daily 收尾前須再走一次本表 |
| `python -m webapp materialize --beta [--state-dir]`（2026-09-08 B2） | 寫 **derived cache**（`library/private/app/state/beta.json`，atomic）；讀 Google Sheet 持股與 Capital Authority（`spreadsheets.readonly`）、yfinance FX、Engine C technical_observations。**不寫任何 authority**：`--no-refresh` 不寫 Engine C、`--no-record-risk` 不 append 風險快照 | 與 `scripts\daily_beta_snapshot.py` 相同的本機資源與憑證；無新增網路主機 | **互動專用**。同一命令字串的新 flag，不進 unattended rule；Phase A 排進 daily 收尾前須再走一次本表 |
| `python -m webapp materialize --ranking [--as-of] [--state-dir]`（2026-09-08 B1） | 寫 **derived cache**（`library/private/app/state/ranking.json`，atomic）；讀 Neo4j（`query.bottleneck.fetch_assertions`，與 `python -m query.bottleneck` 同一條路）與 registry。**不寫任何 authority**、不入圖 | 與 `python -m query.bottleneck` 相同的本機資源（Neo4j bolt）；無新增網路主機或憑證 | **互動專用**。同一個命令字串的新 flag，不進 unattended rule；日後 Phase A 要排進 daily 收尾前須再走一次本表 |
| `python -m alpha abstention <T> [--list｜--add｜--retract]` | `--add`／`--retract` **append** 一筆到 private ledger（`library/private/alpha/abstentions/`）；**結構上不可能寫入任何數值主張** | 無 | **互動專用**（authority write，需使用者明確執行） |
| `webapp/{api,store,contracts}.py`（serve 端） | 無：import allowlist 不含任何模型／DB／LLM 模組，且四種互相獨立的證明逐條斷言（`tests/test_webapp_request_path.py`） | 無 | 純讀層 |

查證（新入口不該出現在 rules；十六條 fixed entry 數量未變）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'webapp|abstention'
```

### Sandbox impact review 結論（2026-09-07，Analyst Consumer v1／Step 3.5）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m briefing analyst-view <T> [--as-of] [--scenario …] [--sandbox-hurdle] [--format] [-o]` | 唯讀：消費與 `alpha-card` **完全相同**的一次 `fetch_alpha_investment_view`，之後是純函式投影；`-o` 只寫使用者自己指定的輸出檔（不是 authority） | 與 `alpha-card` 相同的本機資源；無新增網路主機、憑證或 identity／ACL | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `briefing/analyst_view/`（新 package） | 無：三支檔案的 import allowlist 不含任何 I/O 模組（`tests/test_analyst_view.py` 以 AST 掃描守著），也不含 `open(`／`write_text`／`store.` 等寫入型 token | 無 | 純函式層，沒有 executable surface |

查證（新入口不該出現在 rules；十六條 fixed entry 數量未變）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'analyst-view|analyst_view'
```

### Analyst View：怎麼跑（互動）

```powershell
# 1) 看一檔（Markdown；依消費者問句排列，不是依 section 編號）
python -m briefing analyst-view COHR
# 2) 只看頭條與 readiness（機器可讀）
python -m briefing analyst-view COHR --format json | python -c "import json,sys;v=json.load(sys.stdin);h={l['key']:l['datum']['value'] for l in v['headline']['lines']};print(v['readiness']['state'], h['current_price'], h['fair_value'], h['price_return'], h['annualized_price_return'])"
# 3) 確認 optional 的 entry 不影響 core readiness
python -m briefing analyst-view COHR --format json | python -c "import json,sys;v=json.load(sys.stdin);print(v['entry']['status'], v['readiness']['blockers'], v['readiness']['optional_unavailable'])"
# 4) 歷史視角（上游缺 → blocked，而不是拿當前值冒充）
python -m briefing analyst-view COHR --as-of 2026-09-05
# 5) 預先 materialize 給未來 APP 讀（純函式輸出，不需要 runtime LLM）
python -m briefing analyst-view COHR --format json -o analyst_COHR.json
```

⚠ 它**不重算任何數字**：每一行都是 read model 裡同一個 `Datum` 物件的參照。要改一個數字只能去改上游 authority
（假設 ledger／估值假設／horizon／判準），改不了「畫面上的那格」——這是刻意的阻力。

### Research Refresh／Dependency Invalidation：怎麼跑（互動）

```powershell
# 1) 現況：什麼變了、影響誰、要做什麼（read model 第 15 節）
python -m briefing refresh COHR
python -m briefing refresh COHR --format json | python -c "import json,sys;r=json.load(sys.stdin);print(r['overall'], r['counts'])"
# 2) 情境：在真實 state 上疊一件假想變化（不寫任何 authority）
python -m briefing refresh COHR --scenario price_only        # 只有市場導出量 recalculate，研究判斷 current
python -m briefing refresh COHR --scenario graph_edge        # Q1 recalculate；引用該邊的 Q2／假設 review_required
python -m briefing refresh COHR --scenario fiscal_rollover   # FY 假設 superseded；模型 review_required：需新假設
# 3) 歷史視角：只看 T 之前已知的變化與成果
python -m briefing refresh COHR --as-of 2026-09-04
# 4) 假設帶角色與 machine-readable 條件（spec 見 .pytest_tmp/cohr_dc_v2.json 的形狀）
python -m alpha assumptions COHR --add spec.json           # evidence_refs=supporting；calibration_refs／comparison_refs 另列
# 5) 把條件鏈到 Event Watch（fired → 假設 review_required；值不自動改）
python -m engine_b.event_watch add --kind fact_verification --entities COHR,co:coherent --fact "…" --wake-hypothesis oa_xxx --expires 2027-03-31
```

**state 的下一步（機器可讀，`required_action`）：** `recalculate`→重跑即可（不需判斷）；`review_required`→在
session 重新評估，**不得自動取代**，舊值只是歷史；`invalidated`→不得再當 current，退場或用新證據重建；
`stale`→排程複查到期，不隱含新證據；`superseded`→歷史。**引擎不呼叫 LLM、不改任何判斷。**

### Causal Fundamental Model：怎麼跑（互動）

```powershell
# 1) 基期實際與指引（mechanical，不需 pq2；value 契約見 config/engine_c_observation_fields.json 的 why）
python scripts/record_mechanical_observation.py --ticker COHR --field fiscal_year_results --value '<JSON>' --source-ref "<8-K EX-99.1 accession + 表號>" --as-of 2026-06-30
python scripts/record_mechanical_observation.py --ticker COHR --field company_guidance    --value '<JSON>' --source-ref "<Business Outlook 逐字>" --as-of 2026-08-12
# 2) FY 別共識（daily ETL 已含；要立刻有就對單檔跑一次）
python engine_c/etl_yfinance.py COHR
# 3) 明示假設（session 寫；evidence_refs 必須是 alpha-card evidence index 或 Engine C 觀測的 ref）
python -m alpha assumptions COHR --add spec.json      # spec：period_end／driver／scope／value／basis／rationale／evidence_refs
python -m alpha assumptions COHR --list
python -m alpha assumptions COHR --retract oa_xxx --rationale "..."
# 4) 看結果：共識 section 直接讀 Engine C；FY+1 橋與 expectation_gap.internal_vs_consensus 已於 2026-09-23 退役
python -m briefing alpha-card COHR
```

⚠ 假設解析不到證據會被拒用並在 refresh 的假設 artifact 標 `invalidated`（`earnings_bridge` 已於 2026-09-23 退役），
不會靜默生效；缺任何一條 driver 就是 `missing`，不補 0。driver 是封閉字彙
（`alpha/fundamental/contracts.py::ASSUMPTION_DRIVERS`）。

### unattended surface 變更的 impact review 五步

判準（「必須在同一個 change 完成」）是 invariant，住 `AGENTS.md`；五步在這裡：

1. 列出 path ＋ side effect ＋ OS／network capability
2. 更新 canonical skill／prompt 與本檔
3. 需要越界時新增**最窄**的 `.codex/rules/*.rules` exact prefix
4. 更新 permission contract test，明確斷言允許項**與禁止的相鄰動詞**
5. 用 scheduled task 的相同 sandbox／exact command 跑一次端到端 smoke test

### SessionStart hook 的分工（2026-09-08 重審）

**重審結論：兩個 hook 都留，刪掉的是一支沒有呼叫端的死碼。**

| 誰在講 thesis 到期 | 什麼時候 | 講什麼 | 為什麼不重複 |
|---|---|---|---|
| `crons/thesis_freshness_check.py`（SessionStart hook） | 你開 session 時 | **尚未進待辦池**的新到期項目 | 它是 Daily 沒跑時的唯一提醒。2026-09-05→09-08 排程停了三天，那三天只有它會說話 |
| Daily Brief 的「賣出側」 | 每天 06:30 | 每筆 decision 的 `disproof`／`catalyst`／`expiry` 四態 | 那是 decision 層的到期，不是 lifecycle 層；且已進池的項目 hook 會靜默 |
| ~~Weekly report 的「Thesis 核查」~~（2026-09-24 隨 weekly 退役） | — | — | 由 Windows daily 心跳段 2 的 thesis 行與 `thesis_lifecycle` 項目承擔 |

⚠ **「三個嘴」曾被判為重複，實測後不成立**：hook 對已進池項目會靜默（`active_lifecycle_todo_refs`），
而 `thesis/lifecycle.json` 現有 3 條 active 且都有 `next_check`（最近 2026-09-28）——它會觸發、不是死機制。
**判準是「這個機制實際產出過幾筆」，不是「看起來像不像重複」。**

**刪掉的是 `crons/weekly_scan_digest.py`**：它自 U7b（2026-07-11）之後就沒有掛在任何 `hooks.json` 上，
weekly prompt 也不呼叫它——沒有呼叫端的提醒不是提醒。連同 `tests/test_weekly_scan_digest.py` 一起刪。
查證：`Select-String -Path .claude\settings.json,.codex\hooks.json -Pattern 'weekly_scan_digest'` 應為空。

## Daily / pq1 / 待辦池的參數與去重

- **Daily pq1 budget：** 每輪上限唯一 authority 是 `config/daily_routine.json` 的
  `pq1.drain_limit_per_run`，它是**吞吐量 cap 不是每日 quota**。查證：
  `python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`
  排序權重唯一 authority 是 `engine_b/priority.py`。tracked thesis impact 由非 retired
  lifecycle ＋ non-terminal Decision cohorts 自動導出。
  ⚠ **2026-09-26（Phase 2 Step 2.8）**：字典序拿掉「瓶頸」鍵（drain 不再為排序讀 Neo4j），`lead_id` 之前加
  lead 首見時間（舊的先；缺值排同級最後、不補假日期）；`decision_impact` 的 `ranking`（誰是第一會變）標 legacy、
  與新值 `structure_change`（結構或讀圖會變）同級，triage 不再提供、`triage-apply` 拒收並計數。
  ✅ **2026-09-17（Phase 2 Step 2.2）已落地：`drain_limit_per_run` = 0**（研究只在互動 session 跑）。
  同一條查證命令印出 > 0 就是有人改回去了。⚠ **0 不是「無上限」**——它原本被驗證器拒絕正是因為那個誤讀，
  現在改由 `tests/test_engine_b_cli.py::test_drain_limit_zero_selects_nothing_of_every_kind` 證明
  limit=0 時每一種工作都選不出來（比「拒絕寫下 0」強：那只擋得住 config，擋不住消費端）。
- **提醒去重：** lifecycle SessionStart hook 只提醒**尚未進池**的新到期項目；已存在的
  `thesis_lifecycle`（含 deferred）由 Daily Brief 顯示，hook 必須靜默。分工全表見上方
  「SessionStart hook 的分工」。
  新提醒只走 `additionalContext` 呈現一次。
- **Sheet 持股的「解析不到」與「使用者決定不研究」（2026-10-01 Phase 4 Step 4.7b）：** 候選板的已持有判定
  （`alpha/candidates.py::held_index`）先排除 beta（beta universe 的 SSOT 只有 `config/beta_policy.json`）、現金與股數 0 的列；
  其餘解析不到 `co:*` 的列，Sheet 代號若登記在 `config/holdings_coverage.json` 的 `ignored`（使用者明確決定不研究；
  每筆 `sheet_ticker`／`reason`／`decided_at`，讀者 `portfolio/holdings.py::load_ignored`）就另列「使用者決定不研究」、
  不算解析不到；其餘列「解析不到」（不猜，要不要登記是 identity 的決定）。心跳段 2 常駐印
  「持股解析不到 N（使用者決定不研究 M）」（0 也印），候選板頁首另列名單、理由與決定日。
  設定檔讀不到、版本不對或任何一筆形狀不對 → 整份不採用、全部照列解析不到，並印讀取問題（fail safe：寧可多問一次）。
  （舊的 daily brief 三分類讀者已於 2026-09-23 Phase 0 隨研究側退役，這份設定檔在 4.7b 之前沒有讀者。）
- ~~**Decision gap dispatch**~~：2026-09-23（Phase 0 Step 0b.4） 退役——`decision_review` 的 go／dispatch／reassess 整組隨 decision_lab 研究側退役，
  legacy 項目只能 drop；pq1 budget 只給 lead。
- **事件監控：** issuer 曝險 ≥20% 且對應 series 單日報酬首次跌破 −4% 才產 ephemeral
  `event_search_requests`；daily agent 只做一次 WebSearch，輸出可能原因＋曝險並標
  未經查證，**不建 lead／decision、不進 pq1/pq2、不寫 Engine A**。需要深挖才另走
  `skills/lead-intake`。

## Source-trace backlog 的 park 程序

pq1 每次因 `isolated_tier_3`／截圖／paywall 未果而 park 時，必須留下 `trace_status`、
`trace_attempts_ref`、`trace_next_trigger` 與 `trace_requires_user`。

**等待條件的唯一 registry 是 Event Watch**（[321]，2026-08-31）：追源 backlog 已併入
`library/leads/event_watches.json`，與待辦等待、假設對照共用同一個引擎與計數器。
線索 park 當下自動建 watch 並取得到期日（`config/event_watch.json` 的 `trace_ttl_days`，
預設 120 天＝一個財報週期＋緩衝）。

`wake_state` 四態：`watching`（有事件在等）／`stalled`（具名標的已全部觸發過一輪，
被動層短期不會再醒）／`expired`（到期）／`unwatched`（沒有任何機制在等它）。
**後三者用 `engine_b.cli trace-backlog --needs-attention` 撈出並逐筆處置。**

**Lead 之間的關聯鍵：** URL hash 只認同一篇文章。跨文章關聯靠 `engine_b/entities.py`
的具名標的做確定性比對（cashtag、`edgar:<TICKER>`、registry 反查的 `co:*`）。
`trace_next_trigger` 保留給人讀；機器改用 `trace_trigger_kind=related_entity_signal`
＋`trace_trigger_entities`。同標的的新 lead 通過 triage 後，會把不需人工 access／付費的
parked trace 排回 bounded pq1，留下 triggering lead receipt。

一般 scheduled／event-triggered 重查仍屬 pq1，不占 pq2；只有需要使用者提供合法 access、
核准付費或明確改變研究優先權時，`todo sync` 才建立 `source_trace_review`。
該類型的 `go` 只把 exact lead dispatch 回 pq1，**不代表相信截圖、提高 evidence tier 或
graph admission**。任何新訂閱／購買必須另列 exact 金額與方案。

## 報告留檔與 outbound 通知

**daily brief 不留檔**（只出在 session；稽核價值由待辦池 log ＋ leads 狀態機 ＋
Decision Store 承擔）；**題材掃描報告留檔**（`docs/reports/theme_scan_<日期>.md`，含無法從池重建的
topic discovery；舊的 `weekly_scan_<日期>.md` 保留為歷史）。不回到 PR/Issue 形式。

**題材掃描 authority hierarchy（2026-09-24 起；原 Weekly）：** `AGENTS.md` 是政策 SSOT；`skills/theme-scan/SKILL.md`
是 runbook，只有開發／人工修 policy 時才改，**掃描本身不得自我改寫**；報告是當次 point-in-time 發現，不是 current-state truth。
帳號計分表每天由 daily ⑬ materialize 進 APP、心跳段 5 印 tier 分布（原「在 weekly 算」隨 weekly 退役）。

**Daily Brief outbound 通知（2026-08-04）：** 完成後可由 Codex 或本機 Claude Code 呼叫
同一支 `scripts/publish_daily_brief.py`，outbound-only 送到 Discord private Forum
channel。失敗是 `delivery_failed`／`not_configured` 的 best-effort 狀態，**不得阻斷**；
`.env`、webhook 與 `library/private/notifications/` 永遠不得進 Git。
去重鍵、Forum thread 保存、分段重試與 PowerShell UTF-8 陷阱見本檔上方 harvest 段落。

## 來源路由（一手來源優先）

通用搜尋（Tavily 等）只配 LLM 品質評分 gate，用在第三層。
**機器可執行的路由與未果處置唯一權威是 [`../skills/source-trace/SKILL.md`](../skills/source-trace/SKILL.md)**；
快速記憶：美股走 SEC EDGAR，台股走公開資訊觀測站（含月營收揭露），
A股走年報／問詢函／海關數據，技術走 arXiv／OFC/ECOC／專利。
各市場都優先做上下游上市公司交叉驗證。
