# StockBotv2 — 交付歷史與待辦方向 (Roadmap)

> 這裡是「做過什麼、還想做什麼」。判準與現行契約在 [`AGENTS.md`](../AGENTS.md)；指令與程序在 [`OPERATIONS.md`](OPERATIONS.md)。
> **規劃或決定下一步時讀本檔；日常操作不必載入。**
>
> `docs/plans/` 已轉純歷史（見 [`plans/README.md`](plans/README.md)）。小工作直接做、不開 plan 檔；只有大型開發才新建 plan。

## 想法怎麼變成程式

```
ROADMAP「未來想法」  →  docs/brainstorms/  →  docs/plans/  →  實作
   （還沒決定要做）      （需求與盲點審查）     （規格與驗收）
```

四階不是每次都要走完。判準是**改錯的成本**：小工作直接做；需要先想清楚需求與反面的走
brainstorm；範圍大到需要驗收條件才開 plan。brainstorm 用 frontmatter 的 `planned_in:`
指向自己的 plan，plan 完成後回填到上方「已交付」表。

### ⚠ 開發項只住這裡，不進 pq2（2026-08-31 使用者定案）

**本檔是系統開發項的唯一載體。** 改的是程式、config、schema 或呈現邏輯，而不是圖／
Engine C／thesis／資本裡的任何一筆事實 → 它是開發項，寫進下方「開放 backlog」或
「未來想法」，**不鑄 pq2 編號**。

判準：**`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？** 前者是研究（pq2 編號），
後者是開發（本檔）。例如「補某條邊的 substitutability」改變圖裡的事實＝研究；
「改 `rank_bottlenecks` 的排序鍵」改變系統行為＝開發，即使兩者都會讓排序表變樣。

理由是**兩種東西的決策資訊完全不同**：研究項要的是「證據夠不夠、授權到哪」，一行決策行
就夠；開發項要的是「這會讓哪個數字變、驗收條件、與其他開發項的相對優先序」（L14 第 5 點），
而那些只有在本檔的表格裡排得出來。實測：2026-08-31 之前約 10 個開發項走過 pq2
（[270][304][305][306][315][321][322][323][324][329]，全部已 resolve），每一個都稀釋了
同一份待辦清單的訊噪比。

系統主動提出的開發構想寫進本檔待排程，**不主動要求 `go`**——它會在下次規劃時一起看，
而不是插隊進每日核准迴路。開發項落地後若要動圖或 authority，那是另一個 pq2 編號。
判準全文見 [`AGENTS.md`](../AGENTS.md)「授權載體唯一」。

**目前沒有進行中的 plan。** 仍有未實作的 brainstorm 項目，見下方「開放 backlog」與「已 brainstorm 但未實作」。

---

## 已撤回的診斷（開工前掃一遍）

> **這一節不是自責，是一份檢查清單。** 每一筆都是「已經寫進 commit／ROADMAP／程式註解，
> 事後被推翻」的技術診斷——不是待辦、不是 bug，是**曾經看起來完全正確的錯誤結論**。
>
> **為什麼需要它：** 2026-08-19 一天之內有三個診斷被推翻，共同形狀是
> **錯誤有方向性——全都朝「產生一個有洞察力的結論」偏**，而且每一個都能用專案自己的
> lesson 語言包裝（L12 一表兩義、L15 gate 攔錯東西）。**模式匹配是提出假說，不是確認假說。**
> 一個現象能被套進某條 L，只代表它值得查，不代表它已經被查過。
>
> `AGENTS.md` L11 判準 2 已經逐字寫下這個失效模式（「剛好嵌得進已成形的敘事時，
> 恰恰最該起疑」），L14 也已寫下「寫進本檔不等於會生效」——**所以解方不是再加判準**。
> 第三欄才是重點：**每個錯誤診斷都有一條 30 秒就能否證它的命令，而當下沒有人跑。**
>
> **用法：** 宣稱「找到根因了」之前，先跑一條**試圖讓自己的結論變成假的**命令
> （不是驗證它為真——那是確認偏誤）。專案對每個 thesis 都強制 `disproof_condition`，
> 這一節是把同一個要求套到自己的技術診斷上。

| 日期 | 被推翻的診斷 | 當時為什麼看起來對 | 一條就能否證它的命令 |
|---|---|---|---|
| 2026-08-18→19 | COHR「Engine C 的 `bar_date` 是憑空生成的、`price` 對不上任何收盤」 | 使用者成交價與系統顯示差 10%，需要一個解釋；`history()` 當下沒回 08-17 那根（**盤中查的**，最後一根是進行中的 bar），拼出「08-17 不存在」。剛好是漂亮的 L12「一表兩義」案例，於是寫進 commit message、ROADMAP 🔴 與程式 docstring，還差點據此在 ETL 加一道會 quarantine 掉正確資料的交叉驗證 | `date(2026,8,17).strftime('%A')` → `Monday`。**08-17 是星期一，一本日曆就能否證** |
| 2026-08-19 | 待辦池三個 `decision_review` 不退場是因為「空 `blockers` 被 `todo.py:1448` 判成非純系統」 | `sizing` 的 `assessment_blockers`／`paper_blockers` 確實全空，且 paper 已 ELIGIBLE；「空集合被判成非純系統」又是一個漂亮的 L12 案例 | `python -m decision_lab card <decision_id>` → `card.blockers` 有 **7 個碼**，不是空的 |
| 2026-08-19 | 同上，第二版：「`execution_fx_stale_since_decision` 未登記，掉進 `execution_` 泛用 prefix 被判 `awaiting_external`」 | 自己寫的檢查腳本取「**第一個** prefix 匹配」而非登記表 `_matching` 規定的「**最長**匹配」，於是自製了一個不存在的 bug。剛好是 L15「gate 攔錯東西」的形狀，可執行、可驗收，看起來完全合理 | 讀 `config/decision_blockers.json` 的 `_matching` 那一行；或 `get_blocker_registry().classify(codes)` 直接跑。真相是它**早就以 exact prefix 登記為 `system_internal`**。補進去後被 `test_registry_is_the_single_source_of_severity` 以「重複 key 73≠72」擋下——**測試比我可靠** |

| 2026-08-19 | 「`live_choices`／`live_execution_reports` 仍為 0 筆，live 這條路徑**從未被走過**」——並據此對使用者斷言 | **直接引用本檔自己的文字**，而該句寫於 2026-08-15 之前、當時為真。錯誤不在推理而在**根本沒推理**：把自家文件當成 current-state truth 引用，正是 L11 判準 2 說的「對外部 claim 嚴、對自家文件鬆」。使用者前一天才走完全鏈，且系統完整記錄了 choice 與 fill | `select count(*) from live_choices` → **1**。已改為附查證命令，並新增 `AGENTS.md`「現況數字會過期，判準不會」小節 |
| 2026-08-19 | 「`commercial_maturity` 積壓缺的是**有人去讀年報附註**」 | 本檔原條目這樣寫，聽起來完全合理（IQE 正是這樣解掉的），差點就照做去讀年報 | 逐一看 7 個積壓的 `missing_data` → 6 個是 `research_assessment_missing`（**連 assessment 都沒有**，且五軸 reason 一字不差），AVGO 甚至早就有那兩筆觀測；第 7 個 Agility 未上市、沒有年報可讀。**靠讀年報能下降的是 0 個** |

| 2026-08-28 | 「COHR 首次 live reassess 失敗的根因是 `--as-of` 沒給，讓 `_snapshot()` 的 `except Exception` 把整份 snapshot 塌成 unavailable」 | 第一次不給 as-of 失敗、六分鐘後給了就成功，時間相關性極強；而 `_snapshot()` 確實有吞例外的 `except Exception`，形狀完美吻合 L12「一表兩義」 | 修好 `snapshot_failure` marker 後**不給 as-of 再跑一次**——marker 沒出現、blockers 為空。真正的根因在 `adapters.py::current_holdings` 的另一處吞例外（Sheet 瞬時失敗） |
| 2026-08-28 | 「首次 live reassess 必失敗，因為 `_confirm_holdings_if_requested` 要求 `status=='available'` 才寫 confirmation，形成時序死結」 | `holdings_confirmations` 當天只有兩筆，恰好對應第二、三次成功的跑，第一次沒有；上一筆 confirmation 已隔十天 | `grep -n "holdings_unavailable" engine_d_runtime/adapters.py` → 它**只由 adapter 的 `except Exception` 產生**，與 confirmation 邏輯無關。第一次的 blocker 正是那個 code |
| 2026-08-28 | 「`co:lumentum` 有兩個 cohort，而 `duplicate_cohort_companies` 回空集合是漏掉了這個形狀」 | `list_operational_cohorts` 明明回了兩個 LITE，檢查卻說沒有重複——看起來就是檢查有洞 | `sed -n '869,876p' decision_lab/store.py` → 註解逐字記著 2026-08-15 已檢查過**這個確切案例**：舊 probe 早已 `expired`，`close` 會拒絕再結一次，故該檢查只算「同時有多個 active probe」。回空集合是正確行為 |
| 2026-08-28 | 「U2 把 `weakest_axis` 從 ceiling 排序改成 level 排序是**零行為變化**的純重構」 | `config/investment_policy.json` 的 `axis_ceilings` 確實是 level 到 ceiling 的嚴格單調映射（0.0 / 0.002 / 0.005），推論同 level 必定同 ceiling | 改完直接 `pytest tests/test_probe_sizing.py` → `[missing_ref]` 立刻紅。`_validate_assessment` 在 `fatal_axis_blocker` 時把 ceiling 打成 0 卻**不動 level**，所以 ceiling 攜帶了 level 沒有的資訊 |

⚠ **這一節自己的 disproof：** 若之後仍發生「診斷已落地才被推翻」，代表它沒生效，
不要靠加字補救——那正是 L14 批評的「要人讀的段落」。屆時該做的是把否證步驟綁進
會自己執行的東西（測試、hook、或 commit 前的檢查），而不是把這張表寫得更長。

**上面那條 disproof 已於 2026-08-28 觸發**（九天後，同一形狀，四筆）。依它自己的要求，
這裡不再加判準，只記一個**可行動的分野**——四筆裡兩筆被機制抓到、兩筆靠運氣：

| 錯誤診斷 | 怎麼被發現 | 存活時間 |
|---|---|---|
| U2「零行為變化」 | characterization 測試紅了 | 約 3 分鐘 |
| 「as-of 是根因」 | 自己剛加的 `snapshot_failure` marker，回頭一驗即推翻 | 約 10 分鐘 |
| holdings confirmation 時序 | 恰好又多查了一層 `adapters.py` | 直到下一輪 |
| `co:lumentum` 檢查有漏 | 恰好去讀了那段註解 | 直到下一輪 |

**有可執行檢查的診斷活不過幾分鐘；沒有的全靠當下願不願意多查一步。**
所以下一步不是寫得更清楚，是**把診斷寫成一條會紅的檢查再落地**——U2 那次如果只在
commit message 寫「這是純重構」，錯誤會原封不動進 master；因為寫成了測試，它三分鐘後
就自己打臉。這條本身也可否證：若之後出現「有測試卻仍讓錯誤診斷落地」，這個分野就不成立。

---

## 已交付

> **記錄實測 before → after，不只記「做了什麼」。** 一個改動若說不出哪個現有數字變了，
> 它與沒做在結果上不可區分（`AGENTS.md` L14 第 1 條）。翻歷史時要看得出哪些是真交付、
> 哪些是白工——2026-08-02 至 08-08 的四次「已實作但供給為零」如果當初這樣記，
> 第二次就會被抓到。

| 完成日 | 項目 | 歷史 plan |
|--------|------|-----------|
| 2026-08-30 | **Private authority 備份接上入口＋Drive 異地＋常駐計數器（原未排程唯一 🔴）** — before：`decision_lab/backup.py` 蓋好但 production 呼叫端 **0**（L13「管子只接一頭」）、Neo4j 連 dump 腳本都沒有，「上次備份是什麼時候」的誠實答案是**沒有備份過**。after：`scripts/backup_private.py` 統一入口（`auth`／`run`／`upload`／`verify-restore`／`status`），首跑實測：decision_lab＋engine_c SQLite 一致性快照、Neo4j 邏輯匯出 **1,151 nodes／1,419 rels**（counts 自我驗證）、其餘不可回復檔案 **289 檔** 打包 files.zip（排除 `models/` 可重下載、`lead_media/`、OAuth 金鑰）、上傳使用者 Drive `StockBotv2-backups`（本機 rotation 3 份／雲端 8 份）。**restore 已實際驗證**：restore 到暫存位置，manifest 全 checksum＋SQLite integrity＋逐表筆數＋zip CRC 全過——三條驗收（①一行可跑入口②brief 首屏「最後一次備份：N 天前」③實跑 restore 比對 checksum）全數達成。計數器三分語意（L12）：surface 無 private root＝略過、從未備份／狀態檔壞掉／超過 7 天／Drive 未上傳＝🔴 現形；refresh token 若因 consent screen Testing 模式 7 天過期，以 `auth_expired` 現形而非安靜停掉。⚠ **Drive 憑證是 OAuth user credentials，service account 死路不要再試**（2026-08-29 實測 403 storageQuotaExceeded，個人帳號無官方出路）。查證：`python scripts/backup_private.py status`；brief 首屏應有「最後一次備份」行。操作程序見 `docs/OPERATIONS.md`「Private authority 備份」 | — |
| 2026-08-29 | **移除 compound-engineering（workstream A）** — ce 的 `ce-plan`／`ce-work`／`ce-brainstorm` 與本 repo 既有的 `skills/` ＋ `AGENTS.md` 工作流重疊，同一件事兩套詞彙。**repo 側**：移除 2026-07-10 遺留的 `.claude/worktrees/swirling-cuddling-puddle` 與其分支（刪前驗證 `master..` 獨有 commit **0 筆**、worktree 乾淨），`git worktree list` 現在只剩主樹。**全域側**：從 `~/.claude/settings.json`（`enabledPlugins` ＋ `extraKnownMarketplaces`）、`installed_plugins.json`、`known_marketplaces.json` 三處移除登記，並刪除 27MB 的 `cache/` 與 `marketplaces/` 目錄；另兩個 plugin（last30days、karpathy-skills）完好。**還原資訊**：三個設定檔已備份於 `~/.claude/backups/ce-removal-20260829-132102/`，來源 `EveryInc/compound-engineering-plugin` v3.19.0 sha `e745e966`。⚠ **`docs/plans/`（8 份帶 `artifact_contract: ce-unified-plan/v1` frontmatter）與 `docs/brainstorms/` 一律保留**——它們是交付與需求推導的歷史，不隨工具移除而刪；那段 frontmatter 從此沒有消費者，屬無害殘留。查證：`git worktree list` 應只有一列；`grep -rl compound-engineering ~/.claude/settings.json ~/.claude/plugins/*.json` 應無命中 | — |
| 2026-08-29 | **beta 訊號拔除的文件同步（B-1 收尾）** — 程式已於 `6aa31de` 拔掉訊號，但 `AGENTS.md`／`crons/daily_brief_prompt.md`／`skills/daily-brief/SKILL.md` 仍在描述**已不存在的行為**：三態動作、RSI／MACD／tier、`signal.baseline_pace`、單輪 campaign budget 百分比、「本輪可評估上限」、「每 5 個完整交易日主動提醒一次」、以及 🟢可評估／🟡冷卻的舊燈號語意。這是 L13 的鏡像——不是「管子只接一頭」，而是**管子換了但說明書沒換**，下一個 session 會照著說明書把已被量測為有害的機制講回來。改寫三份文件的 beta 契約成「目標配置比例（`config/target_allocation.json`，band 是容忍區間不是 gate）＋相對水位（只呈現、不排序、不換算金額）」，燈號改為只表達行情資料狀態。⚠ **2026-08-01 三次回測失敗的實測記錄完整保留**——它是拔除的依據，只改「因此我們這樣用訊號」的結論段。順帶修掉一條已成假的敘述：文件寫「單檔行情 stale／quarantined 時該商品 supported range 歸零」，但已無逐檔區間，實測 00631L／00981A／0050／006208 四檔隔離時 `self_funded_supported_range` 仍為 USD 30,710。**文件契約測試不是刪斷言而是換 token**（刪掉等於失去剎車）：`technical 只決定新增 timing／pace` → `只呈現、不參與排序、不換算金額`＋`不得用 RSI／MACD 等動能指標表達`；`本輪可評估上限` → `目標配置差距`＋`config/target_allocation.json`＋`貸款 tranche 不適用配置建議`；燈號斷言 🟢🟡⚪🔴 → 🟢行情正常／🔴資料不足／⚪歷史不足，並新增「舊語意必須明文廢止」的正向斷言。負向斷言刻意只禁**當成現行欄位使用的形式**（`本輪可評估上限：`、`節奏 25%`），不禁詞本身——三份文件都刻意留著移除紀錄，那段紀錄正是防回填的剎車。查證：`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"` 不應出現 `signal` | — |
| 2026-08-29 | **`research_status` 改用嚴重度 SSOT，不再把「這次沒要 paper lane」講成「研究資料缺」** — 事發：U7 把 `paper_status` 改名為 `research_status`（研究完整度）時忠實沿用了舊判準 `if paper_blockers:`，不分嚴重度。但 `coverage.apply_execution_intent` 會把 diagnostic 級的 `execution_intent_research_only` 塞進 `paper_blockers`，於是**任何 `research` intent 的評估恆為 `DATA_NEEDED`**，與研究本身完不完整無關——一個欄位兩種語意（L12），而且是在改名成「研究完整度」之後才變刺眼。嚴重度分類本來就有 SSOT（`config/decision_blockers.json`：三個 intent／context blocker 皆 `diagnostic` ＋ `system_internal`，`market_missing`／`fx_missing` 為 `fatal`），只是沒被送到判準那裡用（L16）。改為 `fatal_blockers(paper_blockers, lane="paper")`。⚠ **這是放閘，所以先量測（L14）**：對 21 個 operational cohort 的最新 decision 套用新判準，**3 筆改判**（co:micron_technology、co:harmonic_drive_systems、co:schaeffler），三筆的 `paper_blockers` 都只含參數造成的碼；其餘 18 筆不變，仍為 `DATA_NEEDED` 的都帶著 fatal 的 market／fx／identity 缺料。既有 decision 依 append-only 不回寫，改判要等各自 reassess。順帶把兩條用間接代理量測的測試改成直接斷言（防偽造那條改看凍結的 `paper_blockers` 是否含 `catalyst_missing`；空圖那條的 verdict 由 `DATA_NEEDED` 變 `INCOMPLETE`，而後者更準確——缺的是因果鏈不是行情）。查證：`python -c "from decision_lab.blocker_severity import is_fatal; print(is_fatal('execution_intent_research_only', lane='paper'))"` 應為 `False` | — |
| 2026-08-28 | **系統終點由資本額度改回瓶頸度排序（U1–U8 全數完成）** — 事發：21 個 operational cohort 有 20 個 `live_supported_range` 是 `[0,0]`，而排序第 1 的 COHR 三個資本風控**沒有一個 binding**，唯一 binding 的是 `weakest_axis` 的 0.002（換算約 2.94 股、869 美元）——一個 `measured_outcomes` 2/12、從未被驗證的機制在決定資本，正是 L14 禁止的事。移除 `live_supported_range`／`axis_ceiling`／`paper_target`／probe cap／`constraint_trace` 與四動作（`NO_ACTION`／`REVIEW`／`TRADE`／`HEDGE`），改為兩態 `attention`（`MONITOR`／`REVIEW`）＋三態 `research_status`；五軸保留，角色由「決定資本上限」改為「決定排序與指出最弱軸」。新增 NAV 比例呈現（純數字、零門檻）與由最弱軸導出的 pq2 缺口項目。**production 淨 −272 行**（+349/−621）。⚠ 落地時補了兩個「管子只接一頭」（L13）：`build_ranking_view` 交付時**沒有任何 production 呼叫端**，`decision_lab today` 首屏渲染的是「未提供排序資料」而不是排序表；`fetch_nav_exposure` 同樣未被 brief 消費。接上後首屏可行動第 1 名 COHR→NVIDIA、純結構第 1 名 AVGO→CPO。另修 NAV 逐 Sheet row 輸出的缺陷——同一檔散在多個帳戶時**沒有任何一列顯示真實曝險**（實測 LON:VWRA 拆成 21.7%＋4.4%，真實是 26.1%），改為以 ticker 彙總並保留 `lots`。**真實風控一項未動**：5% 單筆上限、ETF 槓桿 nominal／effective cap 全部保留，`record_live_choice` 對每一筆非零選擇仍硬擋。查證：`python -c "import json;p=json.load(open('config/investment_policy.json'));print(sorted(p['probe_lane']), p['single_position_nav_cap'])"` | [plan](plans/2026-08-28-001-refactor-bottleneck-ranking-terminus-plan.md) |
| 2026-08-26 | **`_safe_timestamp` 的本機時區測試由 skip 變成實際執行** — 該測試靠 POSIX 的 `TZ`＋`time.tzset()` 切換 process 時區，兩者在 Windows 皆不存在，於是在**唯一會實際執行這條路徑的平台上永遠 skip**。而它守的不是邊角案例：date-only 的 `snapshot_date` 由 `date.today()`（本機時區）產生，若貼 UTC 午夜就會讓 `_normalize_financial` 判 `financial_timestamp_future` 並 quarantine 整份財務——**台北 00:00–08:00 結構上必中，而 daily routine 正是 06:30**，2026-08-14／08-17 已實測炸過兩次。修法照原驗收條件：`_safe_timestamp` 新增 `local_tz` 參數（預設 `None`，行為與注入前完全相同），測試改用 `ZoneInfo` 物件而非 process 全域狀態。**before → after：`tests/test_engine_d_runtime.py` 2 skipped → 0 skipped、19 passed；全套 1005/2 skipped → 1008/0 skipped。** 另加一條 `test_injected_timezone_matches_process_default` 守住注入與預設等價——否則測到的是另一條路徑而非 production 走的那條。⚠ 落地前實測過測試非空跑：以舊的 UTC 午夜行為重跑，`status` 為 `quarantined`、`blockers=['financial_timestamp_future']`，斷言確實會失敗 | — |
| 2026-08-25 | **Alpha live 部位事件監控（原未排程表唯一 🔴）** — 事發：08-18 開出系統第一筆真實 alpha 部位（COHR 10 股 @ US$316.23，約 0.732% NAV）後，08-18 單日 **−12.75%**、08-19 −6.19%、08-24 −4.85%，系統全程沒有任何路徑會發現。成因不是 bug 而是 lane 錯配：`portfolio_risk.event_search_requests()` 只走 `config/beta_policy.json` 的 `instruments`（已登記 issuer 僅 TSMC／ALPHABET／MICRON／NVIDIA／TESLA），且要求曝險 ≥20%——**alpha 單筆上限本來就是 5%，永遠碰不到**。依 L14 第 4 點三個免 outcome 測試，那是「恆滅」（觸發率恆為 0），鑑別力與恆亮的閘門同樣是零。修法：新增 `decision_lab/alpha_event_monitor.py`，觸發依據改 keyed 在 **`trigger_basis=live_fill_exists`** 而非曝險占比，門檻沿用 −4% 單日＋首次跨越去重（實測支持：抓到 08-18 與 08-24，08-19 被正確抑制為同一段下跌）。⚠ 一個查證出來的意外：**行情不能取自 Engine C `technical_observations`**——該表只涵蓋 beta 那 14 個 benchmark，COHR 一筆都沒有，故比照 `outcome_if_settled_today.py` 直接取 provider 已收盤序列（唯讀、不寫 Engine C）。before → after：**alpha live 部位產生的事件 packet 0 → 1**（首發即為 COHR 08-24 −4.85%、距進場 −12.88%），驗收條件達成。packet 維持 `persistence=none`／`authority_effect=none`，不建 lead、不進 pq1/pq2、不改任何資本閘門 | — |
| 2026-08-22 | **pq1 排序由加權總分改為語意分類＋字典序（workstream 3a）** — 事發：每日 5 個 pq1 slot 有 **3 個**排的是 7 週前的 Micron 內部人 Form 4，而 Micron 已明文降範圍；90 個候選裡 Form 4 佔 36 筆。成因不是權重調錯，是**加權總分的補償性**：`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`，三個各自成立的弱理由相加就壓過真正的資本承諾事件（2026-08-12 修 `FOCUS_TICKER_CAP` 只動稀釋係數、沒動加法，同一個病換面貌復發）。⚠ **關鍵發現：判斷一直都在，只是無處落腳**——舊 triage 只有 `go`／`no_go`，agent 寫下「MU Form 4……**低優先**」時只能放進自由文字 `reason`，排序讀不到；同類文件 167 筆中被判 107 次 `no_go`、36 次 `go`，證明沒有字彙時判斷會逐次飄移。修法依 L15：LLM 做封閉字彙分類（triage 寫入一次），程式做字典序（drain 純函數，可重現可稽核），字典序**結構上**沒有補償性。before → after：**pq1 前 5 名「只是信心／無內容」3 → 0**、**前 20 名 Form 4 16 → 0**、活躍 lead 未分類 90 → 0。副產品：新首屏第 1–2 名正是 pq2 [10] 在等的「SIVE Q2+ 財報重編分辨點」（一直躺在佇列裡，舊排序沒有欄位能表達「會觸發 disproof」）；第 6 名示範 `payment_direction`——MRVL 給 Google 122 億美元認股權是**供應商付錢給客戶**（POET 形狀），被一筆 820 萬美元、方向相反的訂單壓在下面 | [`2026-08-21-research-attention-allocation`](brainstorms/2026-08-21-research-attention-allocation-requirements.md) |
| 2026-08-20 | **chokepoint 覆蓋掃描區分「研究缺口」與「建模待補」** — 原問題：以「供應商數」找研究缺口會把**已研究過的領域誤報成空白**，而那正是選題的輸入。實例是 `tech:robotic_actuator` 顯示 0 個公司供應商，但圖中早有 Boston Dynamics 官方頁面（Hyundai Mobis「will supply actuators for Atlas」，客戶端印證 tier 2）與 Schaeffler Q1 2026 法說的逐字證據——只是邊建成公司對公司或經 `prod:` 中轉，沒接到 chokepoint 節點上。`query/coverage_gaps.py`（commit `7817166`）改為同時檢查間接相連。before → after：`tech:robotic_actuator` 由「0 供應商」**改判 🟡 建模待補（`co:boston_dynamics`）**，驗收條件達成。現況 171 節點｜🔴 研究缺口 42｜🟡 建模待補 12｜✅ 已覆蓋 111（查證：`python -m query.coverage_gaps`）。⚠ 2026-08-21 補充：該 🔴 清單**不可直接當研究待辦**——它混了真瓶頸（`tech:tfln_platform` 等）與只是從文件掉出來的產品名詞（`prod:jericho3`、`prod:altus_family`），直接當缺口數＝把抽取量當研究地圖 | — |
| 2026-08-19 | **第一筆真實部位變成可量測** — COHR（使用者 08-18 買進 10 股 @ 316.23）的 decision 原本 `disproof`／`catalyst`／`expiry` **全是 `None`**、且 cohort lifecycle 於 07-25 以 `expired` 終結。實測確認再次結案會拋 `terminal epoch already has a different outcome`＝**新 disproof 觸發時拿不到 `claim_correctness`**，正是 outcome 長期 0/8 的其中一個成因。修法：綁定以 Q4 FY2026 一手數據為基準的四條 disproof（non-GAAP 毛利率 40.2%＝822.6／2,045.5 為領先指標），並新增 `DecisionStore.reopen_lifecycle_epoch()` 開 epoch 2（**append 不覆寫**：epoch 1 與其 outcome 原封不動，符合 L10）。before → after：`catalyst_watch` 設定不完整 **1 → 0**、COHR lifecycle `expired` → `active(epoch 2)`。⚠ 同輪否證了自己前一天的診斷「lifecycle expired 會讓 disproof 不被檢查」——`catalyst_watch.fetch_entries` 讀 `coverage_assessments`、根本不碰 `probe_lifecycle_epochs`，disproof 一直都有被檢查 | — |
| 2026-08-19 | **Alpha 候選排序進入 daily** — `rank_bottlenecks()` 早已把 COHR→NVIDIA（5/5 `sole_source`、外部印證、距需求端 2 跳）排第 1，但**從未進入 daily 流程**，使用者看不到、agent 被問推薦時只能拒答（L13 管子只接一頭）。補上 `AGENTS.md` Alpha 契約的「哪些標的值得看」判準（瓶頸地位／需求錨點／L8 證據強度三維度）與 `skills/daily-brief` 的消費端（Step 4 接 `query.bottleneck` 為買進側，與既有 `catalyst_watch` 賣出側對稱）。同輪三檔補人工估值觀測，`axis_ceiling > 0` **8/16 → 11/16** | — |
| 2026-08-15 | **引用解析缺口修復＋全域 cohort 掃描** — `assessment_context_mismatch` 使 AXT／LITE 的 paper 由 `SHADOW_ONLY／target 0` → **`ELIGIBLE／target 0.1%`**，frozen 非零 live 區間 **0/75 → 2/77**（現行 v3 骨架 **2/4**）；成因是引用字串與 `reference_index` 的 key 對不上——最刺眼一筆兩邊是**同一份 10-Q、同一個 SEC accession**，只因描述段不同而三種解析全不命中。修法選在源頭消歧義（新增 `decision_lab references`，寫 assessment 前看得到合格引用），**解析規則一字未動**，故無 authority laundering 空間。另修 Engine C 觀測提案 `as_of` 契約與 ledger 不一致（提案曾能建立、進池、被使用者核准，卻在寫入 ledger 那一刻才失敗）。**全域掃描 13 個 cohort 確認引用問題只影響這 2 筆**，並非原先推測的普遍主因 | — |
| 2026-08-14 | **資本表達層 workstream（§4 六步完成五項，僅第 5 項待使用者決定）** — outcome 量測 0→9/9（AXTI 超額 QQQ +72.8%）；blocker severity 移進 config ＋ lane 維度，live 非零 **0→8**、binding 由 `live_lane_blockers` 71/72 變成 **`weakest_axis` 31**；引用無歧義解析＋「至少一個合格」，`axis_ceiling==0` **23→17**；催化劑排程使 AXT 複查日 **2026-11-15→2026-10-30**；daily brief 兩個常駐計數器上線 | [方向與 baseline](brainstorms/2026-08-13-capital-expression-direction-requirements.md) |
| 2026-08-14 | **量測與資料語意收尾** — Shadow 錨點回填使可量測 cohort **7→9**（另 4 個無 ticker，屬正確 unavailable）；Engine C 拆出 `bar_date`／`price_kind`，`snapshot_date`（ETL 執行日）不再被誤當行情交易日；`engine_b.todo.SOURCE_COLLECTORS` 單一登記表使全套測試由 **911/1 紅 → 918/0**；`AGENTS.md` lessons **188→160 行**（15 個編號全保留，砍考古留判準） | — |
| 2026-07-18 | **M1 CPO Depth Sprint** — AXT onboard；Coherent／Lumentum／NVIDIA／Broadcom 各 ≥3 distinct `origin_entity`；20 條 edge conflict 全數 resolve 並 project 進圖 | — |
| 2026-07-19 | **第二條垂直切片／L9 前置 #1** — AMAT/LRCX mature-node Lane Memo（非 AI／非 CPO），評分 23/30，`_check_second_slice()` 通過（commit `a7abdf5`） | [005](plans/2026-07-08-005-feat-second-vertical-slice-plan.md) |
| 2026-07-21 | **Action-Oriented Alpha Decision Lab v1** — Signal → Shadow → Coverage／Confidence → sizing → funded paper／Action Card → outcome 閉環 | [2026-07-21-001](plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md) |
| 2026-07-22 | **Engine D operational workflow** — `evaluate-signal`／`reassess`／`today` 三個正常入口，不要求 internal digest／Coverage ID／idempotency key | [2026-07-22-001](plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md) |
| 2026-07-22 | **L9 剩餘財務核驗缺口** — COHR 客戶集中度與 backlog 補入 manual observation ledger；`preconditions.py` 全綠、`checklist.py COHR` 五項 gate_pass=true。**L9 三前置條件全部達標，投資諮詢 gate 開放** | — |
| 2026-07-23 | **Daily Approval Loop v1.0 骨架** — leads 狀態機＋harvest、partial-identity 修復、MCP `get_decision_brief`、`/daily-brief` skill | [2026-07-22-002](plans/2026-07-22-002-feat-daily-approval-loop-plan.md) |
| 2026-07-26 | **Daily Approval Loop v1.2 本機 rollout** — runner 改 Codex desktop local scheduled task，不再依賴 cloud clone／MCP | [2026-07-24-001](plans/2026-07-24-001-feat-daily-approval-loop-v1-1-plan.md) |
| 2026-07-28 | **Daily Beta Technical Monitor v1** — 11 條 technical series、append-only `technical_observations`、shared cash pool | [2026-07-28-001](plans/2026-07-28-001-feat-daily-beta-technical-monitor-plan.md) |
| 2026-07-29 | **Portfolio Risk Policy Redesign** — 統一 numeric SSOT；只有 ETF 槓桿 cap 與 5% 單筆上限歸零 live range，其餘只記錄／警告 | [2026-07-29-001](plans/2026-07-29-001-refactor-portfolio-risk-policy-plan.md) |
| 2026-07-29 | **Serenity 30-Day Research Campaign** — 279 則回補、robotics ontology mini-slice 入圖 | [2026-07-29-002](plans/2026-07-29-002-feat-serenity-30d-research-campaign-plan.md)、[報告](reports/serenity_30d_research_2026-07-29.md) |
| 2026-07-30 | **封閉字彙收斂** — Engine C 觀測欄位 registry、blocker registry、authority token 單一權威；待辦池分離「等決定／等事件」 | [封閉字彙登記表](solutions/architecture-patterns/closed-vocabulary-registry.md) |
| 2026-08-01 | **Routine reliability 收尾** — daily X bounded pagination checkpoint、lead refs registry、terminal Decision gap 明確 redispatch、自有現金每 5 個完整交易日例行提醒 | — |

**Engine D 仍未包含：** notification、remote Decision MCP、broker routing。

---

## 開放 backlog

> **這是 loop #2 的工作台。** 開發／維護的推進靠使用者主動進來，不靠自動提醒——
> 因此本節要解決的不是「會不會想起來」，而是**打開後能不能立刻知道下一步做什麼、
> 以及上一步有沒有成功**。
>
> **每項強制四欄：項目／為什麼／驗收條件（哪個數字會變）／前置。**
> 沒有驗收條件的不准進佇列（`AGENTS.md` L14 第 1 條）。動工前先看驗收條件，
> 做完後回頭比對，再把實測 before → after 記進「已交付」。

### 進行中（2026-08-29 使用者定序）

三條，依使用者指定順序。每條動工前先量 baseline——沒有 before 就沒有辦法說有沒有進展（L14）。

| | 做什麼 | 為什麼 | 驗收（哪個數字會變） | 前置 |
|---|---|---|---|---|
| ~~**A**~~ | ~~移除 compound-engineering（ce）~~ | ✅ **2026-08-29 完成**，見「已交付」。 | — | — |
| **B** | **Daily 架構重整＋beta 減量（可大修）** | 使用者定案。beta 區目前是 daily 最長的一段（主力逐檔表＋燈號＋pace＋貸款區塊），而 2026-08-01 已實測 beta **訊號 0 勝 3 敗**、有證據的只有 baseline 定投——呈現成本與證據價值不成比例。⚠ 減量不等於刪除行情心跳：`AGENTS.md`「行情表是每日心跳」仍然生效，要減的是**訊號衍生的敘述**，不是最新交易日與 1 日漲跌。<br>🔶 **2026-09-02 減量規則已落地待量測**：使用者讀完當日 brief（本機留底 `library/private/notifications/daily_brief_2026-09-02.md`，**baseline 24,195 bytes**）後定案五項——①pq2 同型項打包（7 個補證項的樣板重複 40+ 行）；②每編號整份只完整出現一次（[129][311][359] 曾三現）；③parked lead trace 欄位只在非預設值時展開；④Pane 1 同公司壓一列、Pane 2 已有編號只引用、Pane 3 改計數＋變動；⑤**beta 輕量版面**（半年投一次定案；同日使用者修正：表格橫向可滑，**欄位保留完整**——砍的是段落與重複敘述，不是欄位；無 TL;DR、無複述行、risk threshold 只在跨越時出現），AGENTS 契約已補定案句。規則進 `skills/daily-brief/SKILL.md`＋`crons/daily_brief_prompt.md`，契約測試換 token 不刪剎車（21 綠）。**本項保持掛著（使用者 2026-09-02 指示）**：等後續 daily 實跑對照 bytes 與 pq2 項目數，還可再減 | ①單次 daily 的輸出長度與 token 用量下降，且 **pq2 項目數不減少**（baseline 2026-09-02：24,195 bytes；查證：`Get-ChildItem library\private\notifications`）；②「研究完整但不在瓶頸排序內」的標的數 → 0（見下方 C-1，✅已落地）。 | ✅baseline 已取得（notifications 留底） |
| ~~**C**~~ | ~~把 pq1 drain 乾淨~~ | ✅ **2026-08-29 完成**：110 條 `triaged_go`（66 Form 4＋11 filing＋11 Sivers/IQE＋22 X）逐條追源處置至 **0**，同日 decompose 產出的 11 條新題亦全數研究完畢再歸零（commit `c03743b`→`3acf18e`）。查證：`python -m engine_b.cli counts` 的 `triaged_go`。 | 110 → 0（兩次） | — |

#### B 的範圍（2026-08-29 使用者細化）

**B-1 beta：訊號機制整組拔除，改為「目標比例 ＋ 相對水位」。**

使用者的實際行為是**定期投入**，不是擇時：大筆約半年一次、動用貸款額度；其餘零星隨意投入。
每次要決定的只有一件事——**這次投哪一檔**。現行 beta engine 回答的卻是「今天該不該投」
（燈號／tier／pace／baseline_pace），那是使用者不做的決策。

- **拔除**：`CONTRIBUTE REVIEW`／`HOLD`／`PAUSE CONTRIBUTION` 三態、RSI／MACD／tier、
  `signal.baseline_pace` 與單輪 campaign budget 百分比、以及由它們導出的所有敘述。
  依據不只是「太長」——2026-08-01 **實測 0 勝 3 敗**（訊號 gate 現金投入輸無腦定投 8.5%；
  訊號調節借款提取無可測得效果；訊號選標的輸固定單押 22%）。拔掉的是已被量測為有害的東西。
- **保留**：每檔的**相對水位**（距 52 週高／低點、距 200 日均線一類的位置指標，**只呈現不 gate**）；
  `AGENTS.md`「行情表是每日心跳」的最新完整交易日＋1 日漲跌；
  `config/beta_policy.json` 的槓桿 nominal／effective cap（對應真實歸零與追繳，與訊號無關）；
  槓桿／重疊商品必須用**自身**價格序列（TQQQ 不得冒用 QQQ 的水位）。
- **新增**：一份寫下來的**目標比例**，LLM 每次的建議由它出發。
  ⚠ **這一條是本項的成敗關鍵，不是形式。** 「看哪檔在低水位就多投」＝用相對位置決定配置，
  正是 2026-08-01 輸掉 22% 的那個機制，把 RSI 換成 LLM 不會讓它變好。分野在有沒有目標：
  **再平衡**（高低水位只決定「補哪一檔比較接近目標」，界線來自目標）與**擇時**（純看誰跌得深）
  是兩個機制。比例本身不必精確、不必常改——它的作用是把建議錨住，不是控制尺寸。
- **目標比例必須先回答的事**：使用者曝險高度集中於科技，而 **alpha 與 beta 是同一個賭注**
  （alpha 全在 AI 光互連，beta 是 QQQ／SOXX／2330／TQQQ）。`AGENTS.md` 只說過 alpha 內部
  「列 N 檔不等於 N 個獨立機會」，跨 sleeve 這句從來沒有人講。年齡 30／30 年期限支持高股票
  比重與容忍回撤，但**長期限解決的是波動風險，不是單一產業風險**——兩者不可混用。
  2026-08-29 實測：直接可見的科技部位約 54%（未計 0050 與 VWRA 內含的科技權重，
  故真實值更高）；系統目前算不出來，因為 `issuer_loads` 覆蓋恆為 `partial`（見未排程
  「ETF 完整 look-through」）。
- **不適用 LLM 建議的例外**：**貸款 tranche**。半年一次的大筆借款投入仍走 `AGENTS.md`
  「Capital Authority」既有的 explicit manual review——每次提款、標的與 tranche 都要人核准，
  「高信心」不構成 machine permission，月息若需靠賣出 beta 支付則該 tranche 不成立。
  零星隨意投入才適用 LLM 比例建議。

**B-2 alpha：pq2 每項太長，看不到重點。** ✅ **2026-08-29 落地**：`engine_b/todo.py` 的
`GO_AUTHORIZATION`（先前只有登記表、消費端 0——L13）已接進 `_item_line`，每個決策項第一行
之後緊跟「go＝授權；不含排除」，hint（密度內容）收在其下並擴及所有類型（先前僅
decision_review 顯示＝其他類型的 TL;DR 在 CLI 完全遺失）。C-1 亦同日落地（見下）。

使用者可接受術語，問題是**掃不到**。⚠ 這不是「2026-07-30 內容密度契約寫錯了」——那份契約
是為了修相反的毛病（項目只有 `co:*` ID，使用者無法還原主詞）。現在感受到的是它的代價：
**完整 ≠ 可掃描**。所以修法是改**閱讀順序**，不是刪內容。

第一版方向：每項最前面一行「決策行」——做什麼、為什麼是現在、`go` 會授權什麼——
其餘既有欄位原樣收在下面。內容密度不減，但一眼能決定要不要展開。
使用者明說沒有明確目標，先出一版再調。

**驗收**：①單次 daily 輸出長度與 token 下降，**且 pq2 項目數不減少**；②beta 區不再出現
三態動作字樣與 pace 百分比，但每檔仍有最新交易日、1 日漲跌與相對水位；③每個 pq2 項目
第一行可獨立判斷要不要展開。

**C-1（B 的子項，2026-08-29 code review 導出）：研究完整的 cohort 會同時掉出待辦池與排序表。**
`research_status` 改用嚴重度判準後，Micron／Harmonic Drive／Schaeffler 三筆 reassess 後會變
`READY` → 首屏 `MONITOR` → 不進 pq2；而它們是工業標的，`rank_bottlenecks` 的
`substitutability >= 4` 過濾又讓它們不在瓶頸排序裡。**兩邊都不在＝研究做完整之後標的反而消失。**
兩個方向：把「`READY` 且尚無 live choice」重新納入 pq2 收集（會回到待辦編號），或在首屏加一段
「研究完整但不在瓶頸排序內」的常駐清單（只呈現、不催辦）。後者較符合「不給尺寸、只給候選」的契約。
刻意不在 review 收尾時半修——它是首屏結構問題，屬 B 的範圍。
✅ **2026-08-29 落地（採常駐清單方向）**：brief item 新增 `research_status`／`live_user_choice`
（L16 跟著資料走）、DTO 新增 `ready_not_ranked`（ranking 未注入時為 None，不與空 list 混用），
首屏排序區後渲染「研究完整但不在瓶頸排序內（常駐；只呈現，不催辦）」。
⚠ 實作時踩到並修掉一個誤報源：ranking DTO 的 rows 只帶前 `limit` 名，直接比對會把
排 11 名之後的公司誤判成「不在排序」——`ranking_view` 已加截斷前的完整 `company_ids` 集合。
首跑實測清單=co:iqe、co:sivers（兩者的邊未填 substitutability，非工業標的過濾——
說明文字如實指出「該補的是邊上的 substitutability」）。

---

**資本表達層 workstream 已於 2026-08-15 結案。** 原目標「把 Engine D 從永遠不下注變成
小注但有意義」已達成：live 非零 **0/72 → 9/89**（現行骨架 9/16）、ELIGIBLE cohort **0 → 8**。
但它的下半段（§4 第 5 項「決定 alpha baseline 尺寸」）被使用者用另一種方式結掉了——
**決定不看尺寸**（見 `AGENTS.md`「Alpha 呈現契約」）。理由是實測：6 個 ELIGIBLE cohort 的
target 全是同一個 0.1%，常數不帶資訊，而使用者要的是「撒網、推薦幾檔、追蹤新事件」。

### 研究注意力分配 workstream（2026-08-21 開工）

**需求與完整推導：[`2026-08-21-research-attention-allocation-requirements.md`](brainstorms/2026-08-21-research-attention-allocation-requirements.md)。**
動 pq1 排序或新增 skill 前必讀該檔 §2（「答案回來會改變什麼」四級判準）與 §6（產物持久化判準）。

**起點是兩個實測（2026-08-21 當時值，⚠ 非現況；每輪上限唯一權威是
`config/daily_routine.json` 的 `pq1.drain_limit_per_run`）：**① pq1 每輪 5 個 slot 有 **3 個**排的是 Micron 內部人 Form 4（7 週前、
且 Micron 已明文降範圍）；90 個候選裡 Form 4 佔 36 筆。成因不是權重調錯，是**加權總分的
補償性**——`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`，三個各自成立的弱理由相加就壓過
維度 3 事件。② Lane Memo 的成本不在 11 份文件，在周圍 9 個維護模組，而 Engine D 完全不讀它。

| | 做什麼 | 驗收（哪個數字會變） | 狀態 |
|---|---|---|---|
| **3a** | `config/lead_classification.json` ＋ `signal-triage` 分類 ＋ `priority.py` 改字典序 ＋ 90 則 backfill | **pq1 前 5 名裡「只是信心／無內容」筆數：3 → 0** | ✅ 2026-08-22 完成（見「已交付」） |
| **3b** | `skills/alpha-status/SKILL.md`（純消費，四 pane；**一個數字都不自己重算**，否則是改自己的考卷） | 能一句話回答「現在加碼哪一檔」，三類缺口各自現形 | ✅ 2026-08-22 完成。首跑即給出明確首選（COHR）並讓三類缺口現形；同輪查出 `daily-brief` 自 08-19 維護的**第二份三維度判準**已就地過期，改為委派 alpha-status（「清單會腐壞」實例） |
| **3c** | `skills/system-decompose/SKILL.md`——使用者可隨時呼叫，週掃只執行積壓題＋提名候選（**不可讓無人值守排程自己選題**，它只能從圖裡挑＝原地繞回） | 首次拆解**未知層 Z ≥ 1**，且最終長出 ≥1 條有供應商的邊。⚠ Z=0 的正確結論是「拆得太粗」，不是「覆蓋完整」 | ✅ **2026-08-29 兩項驗收皆達成**。08-25 首跑 Z=5（commit `6f93dff`）；08-29 第二跑（使用者選題 NVIDIA CPO switch）Z=8，衍生研究＋onboard 後長出**兩條有供應商的邊**：`co:foci → tech:fiber_attach_unit`（上詮，FAU 層 1→2 家）與 `co:luxnet → tech:cw_dfb_laser`（華星光，CW DFB 台系量產者），另 Fabrinet 三邊入圖（commit `3acf18e`）。機制證實能產出「圖裡原本沒有的名字」 |
| **2** | epoch 錨點：cohort／epoch 兩個都留，epoch 錨點**不得事後回填**；補 COHR epoch 2 的 08-18 錨點 | 未來 outcome 的正確性。**不會讓 0/8 變 1/8，別記成進展** | 未開始 |

### 主題範圍（2026-08-20 使用者定案）

**以 CPO 與 humanoid 兩條為主。** 使用者原話：HBM「太大了，資金太瘋狂了，而且太寡占，
感覺現在進去太晚了」。因此 HBM／記憶體軸**只做到 Micron 這筆入圖候選為止，不再往下深挖**
（`co:micron_technology` 已註冊、prepared RA `ra_b70b2699` 待核准）；SK Hynix／Samsung
不主動 onboarding。

判準本身仍然有效——tech:hbm 確實是圖中最大的供給側空白——但**「是個真瓶頸」不等於
「現在該投」**：寡占程度、資金擁擠度與進場時點是使用者的判斷維度，不由 chokepoint
排名決定。往後做廣度掃描時，先用這條過濾，不要再把 HBM 當首選推薦。

**優先序是主線／備援，不是並列（2026-08-20 澄清）：** 其他非 HBM 的 AI 相關瓶頸
——SerDes／serializer、載板與中介層（`mat:glass_substrate`、`mat:silicon_interposer`）、
測試（圖中連節點都還沒有）——使用者的原話是「上面暫時沒東西走的話可以挖」。
**只有 CPO 與 humanoid 兩條主線當輪沒有可推進的工作時才動它們**，不得因為某個備援
節點的 chokepoint 分數較高就插隊。已勘查的現況（留給屆時直接接手）：
`tech:serdes` 0 供應商且 `IS_COMPONENT_OF tech:ai_switch`；
`tech:dsp_1p6t` 0 供應商且 `IS_COMPONENT_OF tech:cpo`（這個其實長在 CPO 主線上）；
Marvell FY2026 10-K Item 1 一段內同時逐字涵蓋 ultra-high-speed SerDes、PAM／coherent
optical DSP、TIA、CPO、LPO chipset、AEC DSP 與 PCIe retimer，是補這幾格的現成一手來源
（注意其 10-Q 為財務導向，`\bDSP\b`／SerDes／optical 皆 0 次，產品描述只在 10-K）。

⚠ humanoid 的可投資機會在**零組件供應商**不在整機：`co:agility_robotics` 未上市
（`research_ticker=null`，其 cohort 長期卡在「Agility 未上市，尚無任何紀錄」）、
`co:boston_dynamics` 屬 Hyundai。圖中已有的實體關係只有
`co:hyundai_mobis SUPPLIES_TO co:boston_dynamics` 與
`co:schaeffler DEVELOPS prod:schaeffler_rotary_actuator_platform`
（後者 `IS_COMPONENT_OF tech:humanoid_robot_systems`）。
**5 個 robotics chokepoint 全部 0 個公司供應商**（`tech:robotic_actuator`、
`tech:humanoid_robot_systems`、`tech:robotics_as_a_service`、
`tech:advanced_robotic_devices`、`tech:logistics_tote_transfer`），
而 `tech:robotic_actuator IS_COMPONENT_OF prod:atlas_humanoid_robot`——
actuator 是已在圖中被標為關鍵零組件、卻完全沒有供給側的那一格。

新 workstream：**廣度、事件追蹤、量測**。三條各有可驗證的數字，取代舊的「非零 live 區間」：

| 目標 | 現值（2026-08-15） | 怎麼變好 |
|---|---|---|
| 🔴 **可執行性**：使用者能否據此下手 | **2026-08-19 前為 0** | **本表原本缺這一列，是最上游的問題。** 前三個目標全是「系統內部指標」，沒有一個回答使用者真正的問題——「我不知道投哪個，你能幫我做到什麼」。實測後果：`rank_bottlenecks()` 早就把 COHR→NVIDIA（5/5 `sole_source`、外部印證、距需求端 2 跳）排在第 1，但它**從未進入 daily 流程**，於是使用者被迫自己判斷，而 agent 被問到推薦時以「outcome 0/8 未驗證」拒答。判準與交付要求已寫入 `AGENTS.md` Alpha 呈現契約「哪些標的值得看」小節，消費端已補進 `skills/daily-brief/SKILL.md`（Step 4 ＋ `## Alpha 候選` 段落）。**驗收：daily brief 每天輸出有序候選＋明確首選＋各自 disproof** |
| **廣度**：可評估標的數 | 8 個 ELIGIBLE cohort | ⚠ **這一列的指標本身有問題**：`ELIGIBLE` 是 paper 資本閘門，不是選股判準，把它當「廣度」會誤導成「候選越多越好」。使用者要的是**收斂到首選**，不是擴大清單——16 個 cohort 高度集中於 AI 光互連，列 N 檔不等於 N 個獨立機會（同一 sector 移動被複製 N 次，見下方錨點效度下修）。真正的廣度缺口是**不同主題的瓶頸**，做法仍是瓶頸目標導向：`query/bottleneck.py` 已能列 chokepoint 與已知供應商，缺的是「這條 chokepoint 上還有誰沒研究過」→ 具名 harvest target（見 [`2026-08-18-alpha-live-user-sized`](brainstorms/2026-08-18-alpha-live-user-sized-requirements.md) §8.9）。舊做法（清 pq1 積壓、擴來源）沒有方向 |
| **事件追蹤**：新事件進 brief 的延遲 | 未量測 | 先補 watcher 覆蓋（今天才發現 TSEM 長期空轉），再談延遲 |
| **量測**：可量測 cohort 與超額中位數 | 10/15 個可算出數字，但**有效 n≈1**（見下） | **先讓錨點帶有進場判斷**，再談樣本期 |

🔴 **2026-08-18 查證後下修：這條目前不是「樣本還不夠」，是「量的東西不對」。**
使用者提出「錨點應該只是剛好我們那時候把系統打通，而且建 cohort 是因為入圖、
不是因為我們覺得那時候可以買」——查證屬實，兩項證據：

1. `decision_cohorts.dedupe_key` **全部**是 `claim:<hash>`——cohort 由**入圖**建立。
   錨點日的語意是「這家公司的 claim 那天進圖」，**不含任何進場時點判斷**。
2. 10 個 observed 錨點全部落在 `2026-07-21 ~ 08-14`（24 天、4 個日曆週），
   而 SOXX 在 07-28 見底、正好在窗口中間；標的又幾乎全屬 AI 光通訊主題。

合起來：那不是 10 個獨立觀測，是**一次 sector 移動被高度相關的標的複製了 10 次**，
而那個窗口正好是系統被建起來的期間。先前寫的「超額中位數 +11.1%」與
「錨點前 -9.2%／錨點後 +15.0%」都只描述**這批標的是在什麼行情位置入圖的**，
**不構成選股能力的證據**。

`scripts/outcome_if_settled_today.py` 的「錨點體檢」段落已改為先講樣本效度再講數字，
跨度短於 60 天就出紅字警示。**修法方向不是累積更久，是讓錨點帶有進場判斷**
（見 [`2026-08-18-alpha-live-user-sized`](brainstorms/2026-08-18-alpha-live-user-sized-requirements.md) §7）。

**舊 workstream 的步驟表仍在 [`2026-08-13-capital-expression-direction`](brainstorms/2026-08-13-capital-expression-direction-requirements.md) §4**，
六步已全部完成或被上述決定取代，保留作需求推導的歷史。

⚠ **這條已於 2026-08-28 結案：`axis_ceilings` 連同整個資本表達層被移除**（見下方交付表）。
原文是「不得因為閘門已修好就順手調大 `axis_ceilings`」（D7 先量測後放閘）；最後的處置不是
調整它而是拔掉它——一個從未被 outcome 驗證、卻是唯一 binding 的 cap，沒有資格決定資本。
D7 的判準本身仍然有效，只是不再有這個 gate 可套用。

### 未排程

| 項目 | 為什麼還沒做 | 驗收條件 | 先做什麼 |
|---|---|---|---|
| **✅已交付 2026-09-02：alpha pane1 按族群（sector）分段呈現瓶頸排序**（commit 70200ed；e2e 三群現形,機器人群缺席=接邊研究題已進 pq1） | 2026-09-02 使用者發現：預期每個族群有自己的瓶頸排名，實際 pane1 是單一全域混排。資料層其實齊了——`config/sector_anchors.json` 已定義五個族群（[323] 交付），`rank_bottlenecks()` 每列都帶 `demand_anchor`——但呈現層沒用它分組，是 L16 形狀（SSOT 在、沒送到消費端）。排序權威不變（仍是 `rank_bottlenecks` 的兩份排序），只改呈現：按 demand_anchor 所屬 sector 分段，各段內保持原排序鍵 | pane1 輸出按五個 sector 分段，各段有自己的第一名；跨段仍可看全域序（段標附全域名次）；`sector_anchors.json` 新增族群時 pane1 自動長出新段 | 無（純呈現層改動） |
| **✅已交付 2026-09-02：`prepare_research_action` 在 prepare 時擋「同 URL 無 section」**（graph_mcp `_prepare_extraction_impl` 重用 loader `check_duplicate_url`；三個驗收例實測：缺 section 拒＋指出原因、母 doc 缺 section 拒、nextfinancial 互異 section 放行；Neo4j 不可用時降級由 apply 端兜底） | 2026-09-01 實測：兩個已核准的 RA（原 [360][361]）apply 時才撞 loader 的 `DuplicateUrlError`（curated 節錄文件與母文件同 URL、payload 凍結無法補 `section`），只能重新 prepare＋重新請求核准——把 loader 端 gate 提前到 prepare 端可在核准前就發現。同輪還 backfill 了三個舊母文件的 null section（fas_dod／lynas_q1_fy26／miningweekly） | prepare 一個同 URL 且缺 section 的 draft 會被 rejected 並指出缺哪個欄位；既有通過案例（nextfinancial 雙 section）仍通過 | 無 |
| **OK已交付 2026-09-02（互動/loop 版）：fetchers/edgar_watch**——dry-run 實測 8 天 18 份新申報(含 NVDA/MRVL 10-Q);accession URL 天然去重。daily unattended 掛載仍待 sandbox impact review | 2026-09-02 使用者核准排程。現況：EDGAR 抓取只在 pq1 被動觸發，新 10-Q/8-K 要等 harvest 撞到或人想起來。目標：對 registry 內有 SEC ticker 的公司輪詢 EDGAR filing index，新申報自動 register 成 pending lead（帶 form type/accession 去重）。⚠ 若掛進 daily 排程屬 unattended surface 變更，須走 sandbox impact review（現有 16 條裡已有「SEC EDGAR pq1 fetch」，擴 scope 前先比對該 rule 是否涵蓋） | registry 公司出新 10-Q 後一個排程日內池中出現對應 lead；同一 accession 不重複註冊；interactive 手動跑同一入口結果一致 | 先盤點 registry 內 SEC ticker 清單與 filing index API 的 rate limit |
| **✅已交付 2026-09-02：`fetchers/arxiv.py`**（Apollo 論文實測 62,858 字元落地；metadata API 429/timeout 降級不擋全文） | 2026-09-02 使用者核准排程。本週 TPU/G1 兩次 decompose 都靠手寫 requests+pypdf 抓 arXiv PDF——重複樣板。目標：`fetchers/arxiv.py`，給 id/URL 產出 raw excerpt＋meta（title/authors/published），與 edgar.py 同構；純互動工具，不掛排程，無 sandbox 議題 | `python -m fetchers.arxiv --id 2304.01433` 產出 library/raw 可直接進 extract 流程的檔案；本週兩篇論文用它重跑結果一致 | 無 |
| **✅已交付 2026-09-02：assessment 骨架生成器**（`decision_lab assessment-scaffold`；Google cohort 實測五軸引用預填 12/37/0/1/0、`references --assessment` 診斷零 rejected；判斷欄位刻意留白不代寫） | 2026-09-02 使用者核准排程。本週最大重複摩擦：每張補證工單的終點都是五軸 assessment，而 `decision_lab references` 已經算出每軸的合格引用，人卻要手抄進 JSON 再逐軸寫 reason。目標：`decision_lab assessment-scaffold <cohort>` 讀 reference_index 產出骨架（各軸 evidence_refs 預填合格引用、level=unknown、reason/missing_data 留空給研究者），研究者只填判斷不抄引用 | scaffold 產出的檔案直接過 `reassess --assessment` 的引用驗證（零 assessment_context_mismatch）；用 [397]/[400] 兩張現役工單實測 | 無 |
| **✅已交付 2026-09-02：complete-ra lead refs 自動回寫**（apply 成功即回寫 digest/focus 並推進 applied；best-effort 不動搖 durable apply；compact 後 focus 從 record 頂層讀） | 2026-09-02 使用者核准排程。現況：RA apply 成功後要手動對每條來源 lead annotate `action_digest`＋`focus_company_id` 再 advance applied，本週手動做了四次、漏一次就撞「applied lead 的 action_digest 缺失」。目標：apply 成功時自動把 digest/focus 回寫到 `research_action_id` 綁定的 leads 並推進 applied——L16 的形狀（分類跟著資料走到消費端） | complete-ra 在不手動 annotate 的情況下直接成功；重放（replayed apply）不重複回寫 | 無 |
| **✅已交付 2026-09-02：outcome 等權重聚合+排序快照+brief 首屏**——聚合行進 outcome_if_settled_today(首測:19 檔等權絕對 -2.8%/超額QQQ -2.5%)＋腳本落 `outcome_aggregate.json` 狀態檔＋brief 首屏常駐「排序品質」行(帶量測日;未量測顯示提示不靜默);排序順序快照逐日 append(前/後段對照待史料累積) | 2026-09-02 使用者核准排程。AGENTS 的 outcome 契約說「比較基準是等權重，回答排序前段是否優於後段」，但至今沒有自動化的量測在任何地方出現——這正是 L14 說的該做成常駐計數器的數字。目標：以既有 Alpha outcome snapshot／Shadow 價格為底，聚合出「排序前半 vs 後半的 N 日等權報酬差」，進 daily brief 首屏常駐區。不含部位、不含 NAV、不產生任何 gate | daily brief 首屏出現該數字且隨 snapshot 更新；回填歷史 snapshot 可算出至少一期的前/後段對照 | 先確認 Alpha outcome snapshot 現存欄位是否足夠（缺什麼再補 snapshot 欄位，不重造） |
| **✅已交付 2026-09-02：公司三集合對齊 enforcement 三層全落地**——②常駐計數器進 brief 首屏（實測 圖∖registry=0／registry∖圖=9）；①prepare 端 fail-closed（graph_mcp 對未登記 co:* 拒收並指出補條目路徑；loader validate 維持 WARN 供人分流 typo vs 待 onboard，理由已入註解）；③`onboard-candidates` 接進 weekly Stage 1（唯讀提名，不自行 onboard） | 2026-09-02 使用者問「有 align 嗎」實測：圖 90 vs registry 98（修正前 1 個洩漏 co:openlight 在圖不在 registry——join-key 契約破口，已當場補）；9 家「registry 有、圖沒有」（部分刻意如 SPAC shell，部分是真缺口如 Nidec/THK）；`onboard-candidates` 偵測器（逐字點名但 registry 沒有的標的）**存在但沒有任何 routine 消費它**——L16 標準形狀。三層修法：①loader/prepare 對不在 registry 的 `co:*` company node fail closed（private 也要 null 條目，慣例已立）；②「圖∖registry=0」進 health_audit 硬斷言＋daily 首屏常駐計數器（含「registry∖圖」計數一行現形）；③`onboard-candidates` 輸出接進 weekly topic discovery（唯讀提名給使用者挑，不自行 onboard） | ①載入一個 registry 沒有的 co:* 被拒並指出補條目路徑；②兩個計數出現在 brief 且洩漏=0；③weekly 報告出現候選提名段 | ②先做（最便宜且立即防退化） |
| **✅已交付 2026-09-02：variant perception 落地為 cohort thesis 欄位（①–④全數）**——①schema v9 `cohort_thesis` 表(append-only+supersede 留歷史,migration 帶 backup+筆數驗證);②brief REVIEW 項帶「→ 差異點」一行,未寫者現形提示;③assessment-scaffold summary 對未寫 cohort 附提醒行;④generate_lane_memo 新增 `latest_variant_perception_for_company` 反查注入 user prompt(已寫定版為權威,memo 只渲染不改寫方向)。首筆實例:MP cohort dc_21d81aa1 | 對任一 cohort 寫入 variant perception 後,brief 的該檔 REVIEW 項出現差異點一行;未填者顯示「(未寫 variant perception)」現形不隱藏 | 無 |
| **✅已交付 2026-09-02：排程與互動 session 升級為雙向 advisory writer lock**——先量測（前置達成）：23 個正常日以 publisher commit 為結束 proxy，daily 全程中位 19 分／p90 30 分／最長 43 分，`expected_duration_minutes=60` 確認偏寬但保留（鎖上後窗只是輔助）；並抓到關鍵離群值 **08-29 排程 08:21 才收尾**＝時間窗結構性防不了延遲開跑，正是要上鎖的理由。交付：`engine_b/writer_lock.py`（單一鎖檔 `library/leads/.writer_lock.json`，gitignored；TTL 90 分＝最長實測兩倍；stale/損毀可接手並記 `superseded`；不得拆別人未過期鎖）；**排程側嵌在既有 fixed entry 內**（harvest 開跑 acquire、state publisher 收尾 release）——不新增命令、不動 16 條 allowlist，sandbox impact review 五步同 change 完成（結論與斷言見 OPERATIONS＋`tests/test_writer_lock.py`）；互動側 `writer_guard acquire/release`，`check` 整合鎖；daily prompt 明訂 harvest `writer_lock_held`＝整輪中止（防繞過）；research-drain Step 0 改雙向。smoke 實測：互動持鎖時 harvest exit 3 fail closed（鎖檢查在網路呼叫前）。baseline 0 檢查 → 兩側都取同一把鎖，7 條併發/stale 測試綠 | 兩側都在寫 `library/leads/*.json` 前取得同一個 advisory lock；lock 需 stale-tolerant（崩潰的 session 不得永久卡住）。baseline：目前互動側 exit 2 可擋、排程側 0 檢查 | ✅先量測完成（見左） |


**private authority 備份已於 2026-08-30 交付**（見「已交付」表；service account 死路與
Testing 模式 token 過期兩個判準保留在 `docs/OPERATIONS.md`「Private authority 備份」）。

**2026-08-29 code review 導出（U7 收尾時未修，理由各自附上）：**

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| **✅已結案 2026-09-02（前提被否證，無需變更）：`paper_exposure_invalid`** 產生端仍活著——`workflow._paper_exposure` 每次 freeze 都呼叫 `store.paper_exposure_snapshot`，invalid 時由 `context.py:671` 觸發。否證命令：`grep -n paper_exposure_invalid decision_lab/context.py`（L11-6：能套進 lesson 只代表值得查，不代表已經查過） | U7 移除 paper 部位後，唯一會產生這個 blocker 的程式碼一併消失，但它仍登記在 `config/decision_blockers.json` 且標 fatal——一個永遠不會亮的 fatal blocker 是死規則，讀者會以為那項健全性有人在管 | 該碼從 registry 移除，或恢復一個真的會觸發它的檢查。**先確認哪一個才對**：paper ledger 已凍結為歷史，可能根本不需要檢查 | 無 |
| **✅已結案 2026-09-02（保留＋記錄理由）：`paper_portfolio/ledger.py`**——`replay_decision_store_events` 是 e2e（test_decision_lab_e2e）對 store paper projection 的獨立重放驗證器，理由已寫進模組 docstring | `atomic_assess_probe` 永久停止寫 `paper_events` 後，這個模組在本 diff 之前就已是 test-only | 刪除後全套測試仍綠，或明確記錄它為何要留 | A（ce 移除）之後一併清 |
| **✅已交付 2026-09-02：`system_paper_return` 錨點收斂**——只在真有 paper 起始 decision 時計算（自其凍結價以來的報酬），無 paper 歷史即 None；Shadow 錨定報酬走 market attribution 的 absolute_return，兩者不再混 | 有 legacy paper event 的 cohort 錨在舊 decision、沒有的錨在當前 decision；`AGENTS.md` 敘述的錨點則是 Shadow observation。三者不一致（L12 形狀） | 錨點來源收斂成一個，或在欄位名上把兩種錨點分開 | 無 |
| **✅已交付 2026-09-02：`_nav_base` 多列互異正值時 fail closed 回 None**（上游渲染「未提供 NAV」現形，不給錯分母） | 多帳戶／多幣別 Sheet 會全部按第一列的 NAV 計算佔比，而 NAV 呈現的整個用途就是看佔比 | 給定兩列不同 `nav_base` 的持股時，行為是明確的（取和、或 fail closed），不是靜默取第一個 | 無 |
| **✅已交付 2026-09-02：例外分支測試**（tests/test_optional_branches.py×3）；`store.complete_paper_amendment` 已不存在於 codebase，該子項過時註銷 | `cli._optional`、`adapters.fetch_ranking_view`、`store.complete_paper_amendment` 的 `.get()` 容錯都沒有測試會真的觸發 | 各補一條會 raise 的測試；`complete_paper_amendment` 需用直接 INSERT 造 legacy paper event | 無 |
| **✅已交付 2026-09-02：`fetch_ranking_view` 轉換段納入同語意 try**（轉換例外也回 None＋warning，docstring 承諾成立） | `rank_bottlenecks()`／`build_ranking_view()` 在 try/except 之外，docstring 承諾的「讀不到回 None」對轉換例外不成立，目前只靠 `cli._optional` 兜住 | 轉換例外也回 None，或把承諾改寫成實際行為 | 無 |

**其餘未排程：**

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| **`decision_lab today` footer 的 `live_choices=0` 與 outcome 的 1 筆 live fill 不一致（consumer drift）** | 2026-09-02 daily brief 自陳。兩個 surface 對「有沒有 live 部位」給出相反答案（L12）——讀 footer 的人會以為 live 路徑從未走過，而那正是 2026-08-19 已踩過一次的坑 | 兩個 surface 對同一 DB 回答一致；或 footer 欄位改名以區分「本次 run 的 choice」與「歷史累計」 | 先查 footer 的 `live_choices` 讀的是哪個範圍（本次 vs 累計） |
| **`event_watches.json`／`hypotheses.json` 不在 state publisher 窄 pathset** | 2026-09-02 daily 實測：排程更新了 watch 狀態但只能留本機未提交，等互動 session 順手 commit——兩個 writer 的變更混在同一份未提交 diff 裡，正是 writer lock 要防的形狀殘留 | 擴 publisher pathset（動 unattended surface＝走 sandbox impact review 五步），或明文定為互動側收尾責任並寫進 OPERATIONS | 先決定歸屬；擴 pathset 需 impact review |
| ✅**（2026-09-01 當日交付）Engine C 行情層缺 TSM 序列——真因是 registry 缺 `market_currency`，不是 ETL universe**——`TICKER_MAP` 本來就含 TSM；`engine_d_runtime/adapters.py` 在 `market_currency is None` 時判 identity partial、整段跳過 market/fx fetch。修法：`config/company_identity.json` 補 `co:tsmc: USD`＋同病的 `co:soitec: EUR`。驗收達成：reassess 後 `market_missing`/`fx_missing` 消失、`yfinance://history/TSM` 進 reference_index、TSMC cohort READY（pd_66201450）。identity/currency 測試 79 綠 | 2026-09-01 [275] 實測：registry 有 `research_ticker: TSM`，但 reassess 帶 `--ticker TSM` 仍 `market_missing`／`fx_missing` | TSMC cohort reassess 後 `market_missing` 消失、`yfinance://history/TSM` 出現在 reference_index。查證：`python -m decision_lab references dc_29ef9f7194dc996c9b7eb62a9b21afc6` | 已交付 |
| ✅**（2026-09-01 當日交付，使用者指示直接補）research-drain 升級為單一研究入口＋loop 模式**——四缺口全補進 `skills/research-drain/SKILL.md`：①Step 1 第一段擴為「所有使用者已授權項」（工單＋manual 同級）；②Step 2 終局新增 onboard 包（四維初判過就打包取號，不 park 成開放式 scope 問題）；③Step 6 收尾固定附 decompose 題目提案行（系統只提案不開題）；④新增 Loop 模式段（節流閥語意、每輪 Step 0、noop、醒頻）。adapters 已 sync。原文保留於下供驗收對照 | 2026-09-01 一輪全清（28→0）後盤點，skill 的三段佇列（工單→triaged_go→coverage gaps）覆蓋大部分研究行為，但有四個缺口：①**manual 已授權項不在佇列定義內**（[325] 授權後靠執行者讀池才發現，授權過的工作可能滯留）；②**onboard candidate 一律 park 成 scope 問題**，而 onboard 契約早已允許發現方直接打包 registry＋首批 extraction 成 ra_admission packet 取號（同日 ESMT、Samsung 兩例都只 park）；③**pane 3 只會減不會增**——`coverage_gaps` 只能從既有節點往回看，新層唯一產生器是 `system-decompose` 且明訂使用者選題，drain 清空後 pane 3 成長即停；④**無 loop 語意**（清空輪的 noop、隨 daily harvest 補貨與使用者核准後的自動接續）。四個 authority gate 不因此改變 | L14 各對應一個數字：①manual 已授權項的滯留天數（baseline：[325] 授權後 1 天未被排入）；②onboard 候選「發現→pq2 packet」轉換（baseline 2026-09-01：0/2，全 park）；③每輪收尾摘要固定含「建議下一個 decompose 題目」提案行（選題權仍在使用者，系統只提案不插隊）；④loop 模式下清空輪以 noop 現形 | 改 `skills/research-drain/SKILL.md`（佇列定義補 manual 段、終局清單補 onboard RA、新增 loop 模式段）＋`python scripts/sync_agent_skills.py`；不動 `coverage_gaps` 程式 |
| ✅**（2026-08-31 已交付）decision_review 收集端消費「bounded research 可解性」**——corroboration 殘餘類以 `residual_digest`（missing_data 內容雜湊）當復活判準：resolve 過且內容沒變不重生、變了才鑄號且標題直接講當前缺口（`engine_b/todo.py`；`tests/test_decision_review_churn.py`）。原文保留於下供背景 | 「go 了沒用」的機械成因：只要 cohort 還有 `user_decision` blocker，sync 就把它放進決策佇列吃 `go`——即使 receipt 已明寫剩餘 blocker 是 bounded research 解不了的（[255] Micron counter_path 需使用者 scope 決策「要不要擴大記憶體軸到 Samsung/SKH 側」；[254] 聯亞需五軸 assessment 而非 dispatch）。使用者 go 之後研究部分清掉 blocker、reassess 又鑄新號再問一次＝無限迴圈（2026-08-29 實測 [192][229][238]→[253][254][255]）。分類其實已在 receipt／hint 文字裡，只是收集端沒消費（L16） | 收集端能把「需 scope 決策」項改鑄成明確的 scope 問題（吃 pending/明確回答，不吃研究 go）、「需 assessment」項的 hint 指向 assessment 而非 dispatch。baseline：2026-08-30 的 5 個 deciding decision_review 中 [255] 屬前者、[254] 屬後者 | 先盤點 blocker registry 哪些碼屬「bounded research 不可解」 |
| ✅**（2026-08-31 已交付；同日 [321] 再擴充為單一等待入口）waiting_on trigger 可達性＋Event Watch 模組**——F1/F2/F3 全落地（`engine_b/event_watch.py`：T0/T1 sync 喚醒＋T2 sweep K 旋鈕＋計數器；驗收 baseline 0/3→3/3 達成）。<br>🔴 **本列右欄「trace 端是成熟引擎、49 筆等待全可達」已於當日被實測推翻，留原文供對照。** trace 的 consumed-marker 沒有到期兜底，標的用完即靜默沉底：50 筆非 terminal backlog 有 **10 筆已不可能再被喚醒**，而 `auto_trigger_reachable` 對它們全回 `true`（該欄位只答「有沒有標的可比對」，卻被讀成「還會不會醒」——L12）。[321] 因此把 trace 併入 registry（新增 kind `related_entity_signal`、喚醒目標 `wake_lead`、`is_stalled()`＋`stalled` 計數器、`ensure_trace_watch()` 接住入口端），真正收益是**讓 trace 繼承 `expires`**。`primary_source_signal` 併入 `entity_filing_signal`（判準本就相同），`PRIMARY_SOURCE_TIER` 收斂到 `lead_refs` 單一 SSOT，舊 fallback 路徑實測 0 筆會走到已整段刪除。⚠ **系統仍有三套獨立等待機制未併**：RA expiry、thesis lifecycle、catalyst calendar（見下方未排程項）。原稽核背景見 [`docs/reports/trigger_audit_2026-08-31.md`](reports/trigger_audit_2026-08-31.md)） | 使用者問「等事件的量大了之後真的喚得醒嗎」。⚠ 2026-08-31 稽核**下修昨日結論**：[81] 並非「until 機器可達」——**全 codebase 沒有任何程式比對 `until` 與今天**（[81] 實際騎在 RA `expires_at` 上僥倖可達）；3 個 waiting 項機器可達其實是 0。對照組：trace 端（`related_entity_signal`／`primary_source_signal`＋consumed-marker＋死件自標）是成熟引擎，49 筆等待全可達——**兩套等待、一套引擎閒置**：[200] 等的 Agility S-4 落地成 EDGAR lead 時會喚醒相關 trace，卻不會喚醒 pq2 [200] | ①F1：sync 比對 `until`，到期翻回「等你決定」＋`until_expired` 標記（不自動 drop/go）；②F2：`event_link` 新增 `entity_filing_signal {entities}` 複用 trace 引擎——tier-1 新 lead 共用具名標的即喚醒 pq2 項回 user_decision；與截圖 brainstorm 的 `fact_verification` 共用底座；③F3：daily 首屏常駐「等事件 N（機器可達 M）／trace backlog K（死件 J）」。baseline：waiting 3 項可達 0 | 無 |
| **等待機制仍有三套在 Event Watch 之外（[321] 收尾稽核發現）** | brainstorm 原本列出**五套**「以後要回來看」的機制：trace 引擎、pq2 waiting、RA expiry、thesis lifecycle、catalyst calendar。[321] 併掉 trace、pq2 waiting 已接上（`wake_pq2`），**其餘三套仍各自為政**：RA expiry（`mcp_server/research_actions.py` 的 30 天）、thesis lifecycle（`review_by`，SessionStart hook＋daily 檢查）、catalyst calendar（`scripts/catalyst_watch.py`）。它們目前**都有實際檢查者**（不像 trace 那樣會靜默沉底），所以不是漏洞、是重複——真正的成本是每加一類等待都要選一套去疊，而選錯的那次不會有人發現 | 三套的到期／觸發改由 registry 判定，或**明確記錄為何該獨立**（catalyst calendar 有強日期語意與 L7 的 48 小時動作要求，可能真的該分開）。⚠ 動手前先答 L14：**這會讓哪個數字變？** trace 那次的答案是「10 筆假裝在等的變 0」；這三套若答不出對應數字，就先留著不動 | 先量測三套各自有沒有「看起來在等、實際不會醒」的實例 |
| **補齊各 cohort 的 `commercial_maturity` 觀測** | 該軸只接受 `engine_c_backlog`／`engine_c_customer`，沒有觀測就整軸歸零。IQE 曾因此停在 `SHADOW_ONLY`，2026-08-15 補上 FY2025 年報 Note 4.3 的客戶集中度觀測後轉為 `ELIGIBLE`。2026-08-15 已驗證**這不是非美股的結構性障礙**：SIVE 用年報 Note 5「Information about major customers」、IQE 用 Note 4.3，兩者都揭露。<br>🔴 **2026-08-19 實測後下修：本條原寫「缺的是有人去讀年報附註並建觀測」，但對現存積壓一筆都不適用。** 逐一檢查 16 個 cohort 的最新 decision，7 個含 `commercial_maturity_unknown`，拆開後**沒有一個是「讀年報就能解」**：①**AVGO、POET** 的 `missing_data` 是 `research_assessment_missing`、**五個軸的 reason 全部相同**（「尚未提供語意研究評估」），而 `library/private/decision_lab/` 裡**根本沒有 avgo／poet 的 assessment 檔**——AVGO 甚至**早就有** `customer_concentration`＋`backlog` 兩筆觀測，補第三筆是 0 筆變化；②**Agility** 是唯一真的卡在缺 Engine C authority 的，但它**未上市、沒有年報可讀**（該筆 reason 已自陳「Agility 未上市，尚無任何紀錄」）；③其餘 **4 個是歷史 frozen／重複 cohort**（META、AAOI+AXT+SIVE 混合、Agility 另一筆、一筆無標的），對應公司多半已有更新 cohort 且該軸已通過，依 append-only 契約**不回寫**。<br>**兩層關卡不可混為一談：** `research_assessment_missing` 由 `workflow.py::_unknown_assessment()` 在**完全沒有 assessment** 時對五軸一次性寫入（severity `fatal`）；而 `sizing.py:41` 註解記的「有那兩筆觀測的 cohort 全部 bounded_hypothesis、沒有的全部 unknown，相關性 100%」是在**已有 assessment** 的 cohort 之間測的。**順序是 assessment → 觀測才有機會被引用**，本條原文漏掉前置，於是把積壓的成因指到了錯的一層。IQE 軌跡是三段完整反證：08-04 `research_assessment_missing` → 08-08 有 assessment、missing 轉為「Engine C manual observation：IQE 客戶集中度」→ 08-15 補上 Note 4.3，`ceiling` 0 → 0.002 | 因 `commercial_maturity_unknown` 而 `axis_ceiling=0` 的 cohort 數下降（現值 **7/16**，2026-08-19 實測）。⚠ **但這 7 個要靠補觀測下降的數量是 0**——要動這個數字，binding constraint 是**替 AVGO／POET 跑五軸 assessment**（研究工作，非讀年報）。本條僅對**未來已有 assessment 卻缺觀測的 cohort** 有效，屆時 `missing_data` 會明講缺哪一筆（如 IQE 08-08），不會是 `research_assessment_missing` | 先確認該 cohort 的 `missing_data` **不是** `research_assessment_missing`；是的話前置變成跑 assessment |
| **`structural_lead_time_weeks` 的欄位語意錯位，唯一有值的那筆填的是交貨週期** | `bottleneck.py` 的已知限制寫著它要回答「換掉一個供應商要多久」（qualification lead time），但全圖唯一有值的 `co:globalfoundries -[depends_on]-> tech:semicon_manuf_equipment = 52 週`，其 quote 是「supplier-specific or industry-wide **lead times for delivery** can be as long as twelve months or more」——那是**設備交貨週期**，不是換供應商的合格週期。交貨慢不代表難替代，兩者混用會讓「難替代 vs 換掉要多久」這個原本正確的區分失效。2026-08-21 使用者提問「這個我們填得出來嗎，還是只是亂猜」時查出 | 欄位拆成 delivery 與 qualification 兩個，或明確限定只填 qualification 並把既有那筆改標；且抽取指引要說明兩者差異。⚠ 動手前先確認**真實可得性**：qualification time 在財報出現機率低，多半只在法說 Q&A，可能導致拆完後兩欄都接近全空——若如此，寧可只留一欄並在輸出標明語意 | 無 |
| **`evidence` 分級重構（2026-08-30 使用者核准，設計已依「自報懲罰」討論修正）** ⚠ 原設計只往上加「客戶端具名」級；使用者指出現行做法**過度懲罰業者自報**——大多數 lead 天然只有自報，而客戶端印證常與重定價事件同時到達（COHR 實測：Shadow 42.76 → 印證時 68+），等印證＝系統性遲到。修正後的階梯要**在自報內部分級**：`externally_corroborated`（客戶端具名）＞ `counterparty_joint`（雙方聯合公告）＞ `self_reported_costly`（自報但難偽造：審計揭露的客戶%、已收預付款、已完成募資、產能資本支出——金流/審計事實）＞ `self_reported`（敘述性自報）＞ tier-3 轉述。Tower 的 $290M 已收預付款、上詮的已完成募資都該落在 costly 級而非被壓在最底層 | 兩者都算 `externally_corroborated`，但強度差一個量級：NVIDIA 在自家 PR 點名 COHR，與媒體報導提及，可稽核性完全不同。這使排序無法反映最硬的那類證據 | `evidence` 增加一級並讓 `EVIDENCE_RANK` 反映；驗收是至少一條邊的排名因此改變 | 先確認圖中有足夠的客戶端具名實例可區分 |
| **Engine D cohort 重複** | 同公司可能同時存在 claim-keyed 與 company-keyed 兩個 cohort（2026-07-30 [74]／[75] 實例） | 新建 cohort 時偵測同公司既有 cohort 並警告。**不回溯清理**——Decision Store append-only，不做破壞性去重 | 無 |
| **ETF 完整 look-through** | `issuer_loads` 只涵蓋 policy 已登記的 ownership，曝險輸出恆為 `partial` | 曝險輸出出現 `coverage: full` 的標的 ≥1 | 無 |
| **✅已交付 2026-09-02：本機 single-writer guard**——併入雙向 writer lock（見上）；驗收條件「模擬兩個 writer 併發時會被擋下」由 `tests/test_writer_lock.py::test_second_writer_is_blocked` 滿足 | 目前靠人工紀律確保同一 working tree 只有一個 agent 寫入 | 模擬兩個 writer 併發時會被擋下（可寫成測試） | 無 |
| **Token-efficient Daily Runner 重構** | daily 的 token 成本 | 單次 daily run token 用量下降且產出不變。**動工前先量現值**，否則無從比較 | 先量 baseline |
| **Workstream B：Paywall ROI／合法手動入口** | 付費來源何時值得買、合法人工取得路徑 | 產出「已遇到的 paywall 清單＋各自 exact 金額與方案」，使用者可逐項核可（`AGENTS.md`：任何新訂閱須另列 exact 金額） | 無 |
| **Sheet writer** | 現行所有 runtime 都不寫 Google Sheet | ⚠ **需求尚不具體。動工前先確認要寫什麼欄位、為什麼不能唯讀**；在那之前維持不做 | 需求具體化 |
| **Confidence 五軸重構為三類**（否決／信心／賠率） | [`confidence-axes`](brainstorms/2026-08-02-confidence-axes-restructure-requirements.md) §4 | **部分已被 §4 第 4 步取代**（`unknown → 0`、`corroborated + missing_data` 懲罰）。剩餘未解的是「賠率類」維度——目前完全不存在，且如何量化尚未決定（見該檔 §6「尚未決定」） | §4 第 4 項完成後**重評是否仍需要** |
| ~~`execution_fx_missing`／`live_nav_missing` 未登記，導致無事可決的 cohort 每天照問~~ **（2026-08-19 結案：「每天照問」不是 bug，不需修）** | **這條在同一天被診斷錯三次，全部是「查驗工具本身有問題，卻信了它的輸出」，留著當範例。** ①「`blockers=[]` 被 `todo.py:1448` 判成非純系統」——錯，實測 [167] meta 的 `card.blockers` 有 7 個碼；我只看 `sizing` 的 `assessment_blockers`／`paper_blockers` 全空就推論 item 也空。②「`execution_fx_stale_since_decision` 掉進 `execution_` prefix 被判 `awaiting_external`」——錯，它**早就以 exact prefix 登記為 `system_internal`**；我的檢查腳本取「第一個 prefix 匹配」而非登記表 `_matching` 規定的**最長匹配**，於是自製了一個不存在的 bug（補了條目才被 `test_registry_is_the_single_source_of_severity` 以「重複 key 73≠72」擋下）。③ 隱含假設「補登記就會讓它們退場」——錯。**真正原因是 `evidence_delta == "material"`**：collector 有一行刻意的 `not material_event`，語意是「有觸及 thesis 因果結構的新證據時，不得因為同時有 stale 診斷而被吞掉」。那是**正確設計**，且通過 L14 恆亮測試（實測 11 個 item：material 6／none 4／peripheral 1，有鑑別力）。**用原始 config 實測：meta／sivers 的 `system_internal_only` 本來就是 `True`**，登記表沒問題 | 不需修，config 改動已還原。唯一屬實的遺漏是 `execution_fx_missing`／`live_nav_missing` 沒有 exact 條目（落入泛用 `execution_` prefix → `awaiting_external`），但**補了也是 0 筆變化**（material 優先），依 L14 不做。要動必須先出現「只有 stale／execution blocker 且無 material evidence」的真實 cohort | 已關閉 |
| `_only_system_internal_blockers` 的空集合分支語意可疑（`if not codes: return False`） | 空 blockers 意味著「什麼都沒卡住」，卻走「非純系統內部」分支。**但 2026-08-19 全面檢查 11 個 brief item，沒有任何一個的 `blockers` 是空的**——這個分支目前無實例 | ⚠ **依 L14 不得動它**：改了會讓 0 筆資料變化，且風險不對稱——`action=REVIEW` 有兩個與 blockers 無關的來源（`disproof_triggered` → `urgency=within_48h`、`lifecycle.status ∈ {rejected,expired}`），把空集合改成「不必問」會把 L7 的火警警報藏掉。要動它必須先讓 REVIEW 的原因出現在 item 自己的證據欄位裡（L12 末尾的「因果被截斷」） | 先出現真實實例 |
| ~~🔴 `financial_snapshots.price` 取自 `yfinance.info`，且 `bar_date` 是憑空生成的~~ **（2026-08-19 撤回：此 bug 不存在）** | 原條目（2026-08-18 寫入）宣稱 COHR 的 `bar_date=2026-08-17` 是 ETL 憑空生成、`price=351.22` 對不上任何收盤。**逐項複核後三個前提全錯：**（a）08-17 是**星期一**，正常交易日，原文「週五 08-14 → 週二 08-18」漏掉了它；（b）`yf.Ticker('COHR').history()` 實測**有** 08-17 那根 K 線，收盤 `351.220001`——就是 Engine C 記的值；（c）ETL 讀的是 `currentPrice`／`regularMarketPrice`，不是 `previousClose`，且 `_bar_identity()` 的 docstring 明講只取 provider 明示欄位（`regularMarketTime`＋`exchangeTimezoneName`＋`marketState`）、**不做推斷**、欄位缺就回 `None`。**抓取時戳佐證：**該筆 `fetched_at=UTC 2026-08-17 22:33`＝美東 08-17 18:33（收盤後）＝台北 08-18 06:33（daily 排程），所以 `snapshot_date=08-18`（台北日）配 `bar_date=08-17`（美東交易日）是 2026-08-14 拆開兩者的**設計本意**。原始現象（使用者 08-18 以 316.23 成交 vs 系統顯示 351.22）的真正原因是**當天 COHR 跌 12.7%**（351.22 → 306.43，盤中低 305.50），不是資料污染。「+17% → +33%」也不是錯誤被修正，而是 as-of 從 08-17 收盤換成 08-18 盤中的**必然差異**。⚠ 誤判發生在**盤中**（對話時間台北 08-18 22:00＝美東 08-18 10:00，開盤半小時）：此時 `history()` 最後一根是進行中的 bar，初版寫的「08-18 收 309.00」是把即時價當收盤（實際收 306.43）。錯的**不是觀察是推論**——從「history 沒顯示 08-17」跳到「08-17 不是交易日」，正是 L15 第 5 點「我找不到 ≠ 它不存在」，而這裡一本日曆就能否證 | 不需修。⚠ **原本擬議的「ETL 加交叉驗證：info 與 history 不一致就 quarantine」不得實作**——它會把完全正確的資料 quarantine 掉，正是 L15 說的「gate 攔下的不是它想攔的東西」 | 已關閉 |
| **`current_holdings` 用裸 `except Exception` 壓平所有失敗** | `engine_d_runtime/adapters.py` 的 `current_holdings` 把「Sheet 真的沒有持股」「網路讀不到」「憑證失效」全部收斂成同一個 `holdings_unavailable`（L12 一表兩義）。下游只能二選一，而兩邊都錯。2026-08-17 花了數步才確定是沙箱無 egress 而非設定問題 | 三種情形產生可區分的 blocker／診斷欄位，且至少一個既有測試能分辨「空持股」與「讀取失敗」 | 無 |
| **`checkpoint_decision_review` 的 completed 路徑非原子，裸 decision id 會造成 pool 與 work order 脫鉤** | `engine_b/todo.py::checkpoint_decision_review` 用 `receipt.removeprefix("decision:")` 查 decision，**裸 `pd_*` 與 `decision:pd_*` 都查得到**，於是裸 id 能通過前半段驗證並**先執行** `store.transition_research_work_order`（寫進 DB），但函式最後的 `resolve()` 走 `_validate_go_receipt`，那裡要求 `receipt.startswith("decision:pd_")` → 拋錯 → pool 不存檔。結果是 **work order 已 completed、todo item 仍 awaiting_approval**，且後續用正確格式重試會被「illegal transition: completed -> completed」擋死，CLI 再也修不回來。2026-08-19 實測踩到（[166]），最後靠直接呼叫 `todo.resolve()` 補 pool 端才收斂。這是 L12 的變體：同一個 receipt 字串在同一支函式裡被兩套規則解讀，寬的那套先產生副作用 | 用裸 `pd_*` 呼叫 `todo work <n> --to completed` 時，**work order 狀態不變**（在 transition 前就被拒），且 pool 與 work order 不會出現不一致；可寫成測試 | 無 |
| **待辦池沒有 evidence conflict 類型，未解 conflict 無人提起** | `engine_b/todo.py` 的 `ITEM_TYPES` 九種裡沒有 edge conflict。2026-08-18 那兩個 conflict 是入圖後**順手**發現的（其中一個推翻了同輪自己剛寫進去的 `substitutability=4`——把「找到 AXT 這個新供應來源」誤讀成「對 InP 的依賴變可替代」，而該 quote 語意正好相反）。若沒注意到，它們會一直開著、那幾條邊一直缺屬性，daily brief 不顯示、pq2 拿不到編號 | ⚠ **依 L14，動手前要先答出「這會讓哪個數字變」，而現在答案是 0**：2026-08-19 實測 `query.edge_conflicts` 列出 22 個 conflict，`library/resolutions/` 有 22 個 resolution，兩集合**完全相同 ⇒ 目前 0 個真正 open**。**先累積幾輪 drain 的 conflict 產生率與平均滯留時間**，有非零滯留才實作；否則就是替不存在的問題加機制 | 先量 conflict 產生率 |

**M1 研究遺留（仍開）：**

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| TSEM intake（`ra_2bf1494b`）2027–29 光通訊集體擴產 oversupply watch | 供給側擴張正是 AXT v4 由偏多轉謹慎偏空的同一主軸 | 圖中出現可支持／反駁 oversupply 的 dated claim ≥1，或明確結案為「本輪無新證據」 | 無 |
| MACOM／Semtech 作為 Tower TIA 客戶 | tier 3，待客戶端揭露印證（L8） | 取得客戶端一手揭露 → 升 tier 入圖；**或**判定「對方結構上不會揭露」→ 標為永久 tier 3 並停止重試（見 §1 D4） | 無 |
| GF 對 Tower 專利訴訟未追源 | M1 遺留 | 追到一手訴狀／法院文件，或確認公開管道不可得並記錄 | 無 |

**看起來像缺口但不是——請勿「修正」：**

- **人工 runway 觀測寫入後 `financial_runway_manual_required` 仍亮，多半是 100 天鮮度窗，不要去改窗。**
  2026-08-30 全鏈實測（6324.T）：ledger 有觀測、`get_probe_financial_baseline` 正確附
  `manual_runway`、`derive_runway` 單測回 `self_funding`——blocker 來自
  `context._normalize_financial` 的 `runway_freshness_days=100`（觀測 as_of 距評估日 109 天，
  同時亮 `financial_runway_stale`，在截斷的 blocker 清單裡容易漏看）。這個窗是刻意對齊
  財報節奏的設計（見該處註解），**正解是用最新一季財報刷新觀測**（已登記 pq1 lead），
  不是放寬窗。⚠ 紀律：runway 觀測的 `as_of` 應填**資產負債表日**，不是申報日。


- **5 個 cohort 的最新 `expiry` 仍是 `+72h` 預設值，不要去清。**
  2026-08-19 全庫掃描：16 個 cohort 中有 5 個（4 個無 ticker 的歷史 cohort ＋ LITE 的舊
  重複 cohort `dc_ebaf2286`）最新 assessment 的 expiry ＝ `created_at + 72h`，是
  2026-08-15 修復前的遺留。**但它們的 lifecycle 全部已 `expired`，且 `catalyst_watch`
  根本不顯示它們**（無 ticker 者 `company_id IS NULL` 被查詢排除；LITE 因同 company_id
  去重只取最新的 `dc_4d28e508`）。依 L14，修它們會讓 **0 筆**下游資料變化。
  根因（reassess 未帶 `--expiry` 時回退成 policy 三天預設，把財報里程碑改造成假急件）
  已由 `300b8e0`（2026-08-15 05:19 UTC）修復，並有 `tests/test_operational_workflow.py:399`
  防迴歸；逐筆核對修復後只剩兩筆 `+72h`，兩筆都是**新建 cohort**（無舊值可繼承），屬正常。


- **Beta 例行成交不進 Engine D 的 `record-fill`，這是設計正確。**
  `record_live_fill` 要求的不只是 `decision_id`，而是一整條責任鏈：
  decision → `record-choice`（使用者明確接受某個部位大小）→ fill，並驗證成交時間
  不早於 choice、幣別符合凍結 context 的執行身分。目的是回答「Engine D 的建議準不準」。

  Beta 例行投入沒有 decision、沒有支持區間、沒有接受動作——**它是時間表不是決策**。
  硬塞進去要替每筆投入捏造 decision，後果是 Decision Store 被假決策汙染、
  outcome attribution 變成把 QQQ 漲跌歸因給「今天是 15 號」、以及同一筆成交
  出現在兩處成為第二個真相來源。且 2026-08-01 已實測 beta 訊號 0 勝 3 敗，
  替它建 attribution 是測量已知無效的東西。

  **正確分工：** beta 例行成交 → `library/trades/trade_log.jsonl`（事件紀錄）；
  alpha thesis 驅動成交 → 未來同時進 trade_log 與 Engine D fill。

  **真正待補的是後者。** ⚠ **2026-08-19 更正：本段原寫「`live_choices`／
  `live_execution_reports` 仍為 0 筆——live 這條路徑從未被走過」，該陳述已過期。**
  實測：`live_choices` 1 筆（`lc_734a39a6`，COHR 10 股、`selected_weight=0.00732`、
  `choice_type=user_sized`，系統當時 supported upper 僅 0.002）、
  `live_execution_reports` 1 筆（`lf_92aede7e`，`ib-cohr-2026-08-18-10sh`，
  10 股 @ USD 316.23），**2026-08-18 已首次走完 decision → choice → fill 全鏈**。
  `paper_events` 已於 2026-08-08 首次寫入。
  📌 教訓：本檔的「目前為 0 筆」型陳述會過期，引用前必須查 DB 而非引用本檔——
  2026-08-19 就有一次直接引用本段過期文字對使用者說「這條路徑從未被走過」，
  而一個 `select count(*)` 即可否證（L11 第 2 點：別對外部 claim 嚴、對自家文件鬆）。
  2026-08-15 起 `live_supported_range` 首次出現非零（AXT／LITE，各 `(0, 0.002)`），
  但兩筆的 intent 都是 paper、`live_status` 仍為 `NOT_REQUESTED`，
  `record-choice` 依舊無從執行。等真正要下第一筆 Engine D 驅動的 alpha 單時再加
  `record_trade.py --decision-id`，那時需求才具體；現在補等於對沒跑過的路徑猜規格。
  **解除條件是資本表達層 workstream（見「進行中」），不是補這支腳本。**

**已知未修的操作缺陷：**
- 同一公司可能同時存在 claim-keyed 與 company-keyed 兩個 cohort（2026-07-30 [74]／[75] 實例）；Decision Store append-only，不做破壞性去重

---

## 什麼值得開發 / 什麼交給 Claude

### 值得開發（邊際效益高、省 token、跨 session 有用）

| 類別 | 具體項目 | 理由 |
|------|---------|------|
| 知識累積 | 更多公司 onboarding、更多高品質文件（⚠ 這是**研究方向**非開發項——現行 research-drain 閉包語意已涵蓋：coverage 缺口與具名候選的四維初判是常備工作，onboard 包由發現方自動鑄號。2026-09-02 使用者確認持續投入） | 圖的大小決定回答的深度 |
| Skill 介面 | SKILL.md 檔（已有 8 個）| 讓 Claude Code / Codex 每次都能正確使用記憶 |
| 高槓桿 fetcher | EDGAR 季報自動更新、arXiv 論文抓取 | 減少人工取文件摩擦 |
| G5 L8 偏誤檢查 | `validate.py` 加 origin_entity 同質性警告（2026-07-17 已實作：供應商自報 sole_source 在文件層 WARN） | 低工程量、高資料品質槓桿 |

### 不值得自己開發（Claude 做得更好或沒意義）

| 類別 | 理由 |
|------|------|
| 長文解讀、文章分析 | Claude 的 context window + 推理比自製 pipeline 好 |
| Text2Cypher / 對話式查詢 | 直接給 Claude 原始 graph context，Claude 自己解讀 |
| 自動選文件頁面（G2）| Claude 看 TOC 判斷比 embedding filter 更準確 |
| 節點重要性評分（G8）| Claude 從 edge 數量、tier、公司規模能即時判斷 |
| 公司識別（G1）| Claude training data 知道公司是誰，hallucination 風險由 TICKER_MAP 控制 |
| 自動代替使用者做最終投資決定或送單 | Engine D 可以提出有邊界的建議與 paper counterfactual，但 live 接受、覆寫與 broker 下單永遠需要人工 |

---

## 已 brainstorm 但未實作

需求已想過、盲點已審過，但沒開 plan。要動工先回去讀該 brainstorm，不要重新發明。

出自 [`2026-07-26-next-phase-operating-model-requirements.md`](brainstorms/2026-07-26-next-phase-operating-model-requirements.md)，該檔明載「只有重複摩擦出現時才另立 plan」：

- **Workstream B：Paywall ROI／合法手動入口** — 付費來源何時值得買、以及合法的人工取得路徑
- **Token-efficient Daily Runner（通用 daily runner 重構）**
- **ETF 完整 look-through** — 目前 `issuer_loads` 只涵蓋 policy 已登記的 ownership，輸出必標 `partial`
- **Sheet writer** — 現行所有 runtime 都不寫 Google Sheet
- **本機 single-writer guard** — 目前靠人工紀律確保同一 working tree 只有一個 agent 寫入

出自 [`2026-07-31-leverage-glide-path-requirements.md`](brainstorms/2026-07-31-leverage-glide-path-requirements.md)：

- 總曝險硬擋與自有現金固定例行提醒已於 2026-08-01 完成。
- 唯一剩餘的**貸款提款時間表**由使用者明確暫緩；目前不預期這麼早手動投入貸款，
  未來若重啟再核准 exact 日期／金額／標的／tranche。glide path 公式亦延後，現況資源尚不構成綁定。

出自 [`2026-08-13-capital-expression-direction-requirements.md`](brainstorms/2026-08-13-capital-expression-direction-requirements.md)：

> ⚠ **2026-08-28 起本檔只剩歷史價值，不再是可執行指引。** 它整份是在推導「怎麼把資本
> 表達調對」，而 U7 的結論是**整層拿掉**——`live_supported_range`／`axis_ceiling`／
> `paper_target`／probe cap 都不再產生。§2 凍結的三個 baseline 數字（非零 live 0/72、
> `axis_ceiling` 從未達 0.005、已量測 outcome 0/8）與 §4 的六步，指涉的欄位已不存在。
> **D1–D7 的方向判準仍然有效**（見下），失效的是它們的實作對象。

- **仍然有效的方向（D1–D7）**：研究是手段不是目的；不確定性用尺寸承擔不用 gate 禁止參與；
  診斷與閘門分離（blocker 全留當診斷，只有講得出因果機制的能歸零）；證據標準
  校準到個人投資者可達成的補救；**gate 本身也不得未經量測就享有默認信任**；先量測後放閘。
  ——2026-08-29 那次 `research_status` 改判準（`if paper_blockers:` → `fatal_blockers`）
  就是 D3 的直接應用，且照 D7 先量測（3/21 改判）才動手。
- **已失效**：§2 的三個 baseline 數字與 §4 的六步（指涉的欄位已隨 U7 移除）；
  「alpha 需要 baseline 尺寸」這條方向被使用者以另一種方式結掉了——**改成不給尺寸**。
- **§6 的防呆仍然成立但對象已換**：daily brief 的常駐計數器還在，只是量的不再是資本
  （`live_range_nonzero` 已凍結為歷史欄位），而是研究廣度與可量測數。

出自 [`2026-08-02-confidence-axes-restructure-requirements.md`](brainstorms/2026-08-02-confidence-axes-restructure-requirements.md)：

- **Confidence 五軸重構為三類（否決／信心／賠率）** — 現行五軸全在問「證據多強」，
  高度相關又取 min，等於最弱那份文件決定一切；且完全沒有賠率維度，系統只能用
  「不參與」表達不確定性。提議拆成二元否決類、序數信心類、連續賠率類。
- 該檔的**最小改動已於 2026-08-02 交付**：coverage blocker 依嚴重度分成「致命」與
  「研究不完整」。⚠ 該次交付的目的是「讓 `axis_ceiling` 得以生效」，而 `axis_ceiling`
  已隨 U7 移除；**那套嚴重度分類本身仍然是活的**，現在決定的是 `research_status` 三態。
  動軸結構前先跑一兩週看樣本品質——若變成可評估的標的其實不值得看，問題在 pq1 選題
  而不在 gate。
- 動工前必讀該檔第 6 節：`closed-vocabulary-registry.md` 仍把五軸列為「刻意凍結」，
  但那個理由已因 `rubric_version` 版本化而失效，需一併更新登記表。

其餘五份 brainstorm 的主體都已交付（見上方表格），保留作需求推導的歷史。

---

## 未來想法（尚未承諾）

### ⚠ 2026-07-31 回測發現：以「等回檔才投入」決定是否進場，對 30 年累積目標是負貢獻

把現行 `signal_state` 的 gate 邏輯拿去跑 2015-08 ~ 2026-07（128 個月，每月 $1,000）：

| 標的 | A 無腦每月定投 | B 只在 gate 觸發時投入 | B/A |
|---|---|---|---|
| QQQ | $394,034 | $360,533 | **91.5%** |
| SOXX | $820,624 | $754,498 | **91.9%** |

兩個標的都輸約 8.5%。原因是市場多數時間在漲，等回檔＝在上漲期間抱現金；
即使現金最終幾乎都投出去（殘餘僅 $5–9k），時點延後就損失複利。

觸發頻率本身不是問題（QQQ 9.5%、SOXX 14.4% 的交易日），問題是**逐年極度不均**：
2017 年 QQQ 觸發 0 天、2021 年 1 天，2022 年 127 天。在強多頭年份幾乎完全不進場。

**限制：** 這是單一路徑、兩個標的、且 2015–2026 是異常強的多頭。方向與已知證據一致
（Vanguard 2012：一次投入在約 68% 的 12 個月期間勝過分批），但不足以當定論。

**問題不在訊號，在它被用來決定「要不要投」。** AGENTS.md 寫的是「technical signal
只決定新增 timing／pace」，但實作上 pace=0 會讓 `supported_order_range` 歸零，
輸出讀起來就是「今天不要投」。

**建議方向（未實作）：** 把 gate 從「是否投入」改成「投給誰」。
1. 基準永遠投入——固定月投不受訊號影響，這是時間複利的來源
2. 訊號只決定**這筆錢分配給哪個候選標的**（誰最接近趨勢／回撤最深）
3. 若要保留逆勢加碼，用**再平衡帶**（目標權重＋偏離門檻）而不是技術訊號——
   它天生就會在下跌後買進，且不需預測

---

### 2026-07-31 回測：深跌加碼槓桿 ETF 的真實效果與其致命限制

使用者要求「跌深多買、以槓桿 ETF 放大」。實測（真實 TQQQ 2010-02~2026-07，198 個月 × $1,000）：

| 策略 | 終值 | vs 基準 | 觸發月數 |
|---|---|---|---|
| 全 QQQ | $1,174,561 | — | — |
| 回撤 −10% 改投 TQQQ | $2,149,786 | **183.0%** | 30/198 |
| 回撤 −20% 改投 TQQQ | $1,208,296 | 102.9% | 11/198 |
| 回撤 −30% 改投 TQQQ | $1,190,704 | 101.4% | 4/198 |

**⚠ 第一版回測是錯的，必須記下來避免重蹈。** 原本用「3×日報酬」模擬 3x 回到 1999，
得到 B/A = 724% 的驚人結果。錯誤在於：模擬淨值在 2000-2002 跌到趨近零（−100%），
而用「$1,000 ÷ 趨近零的價格」計算股數會讓股數爆炸性放大再乘回來。**那是除以趨近零
的數字產生的假象，不是報酬。** 現實中基金早已清算或反分割，無法從那裡複利回來。
任何跨越 2000-2002 或 2008 的槓桿回測都必須用真實基金資料，或明確處理清算。

**結論不是「跌越深買越多越好」，而是「2010-2026 這個 regime 裡槓桿越多越好」。**
−10% 門檻贏最多只是因為它觸發最頻繁（30 次）＝在多頭中待在槓桿的時間最長。
樣本期最大回撤僅 −35.1%，**完全不含網路泡沫等級的事件**。

**反例（決定性）：** 2000-03 ~ 2002-10，QQQ 跌 82.8%，模擬 3x 淨值剩 **0.05%**（−99.95%）。
在那個情境下「跌深加碼」不但救不回來，還會一路買到歸零。

**真正的保護來自 NAV 上限，不是回撤觸發條件。** 若槓桿 sleeve 受
`leveraged_effective_cap` 限制，即使該 sleeve 歸零，損失上限＝ nominal 權重。
2026-07-31 已設 nominal 20%／effective 40%：純 3x 時 effective 先綁定，
對應 nominal 約 13.3%，最壞情況損失約 12% NAV——痛但可存活。

**未實作的機制：** 目前每個標的各自獨立產生訊號，沒有「深跌時把資金路由到槓桿標的」
的機制。要做需新增 allocation routing，屬資本行為變更，須經 brainstorm。

### 2026-07-31 既有研究：槓桿的正確變數是「人生階段」不是「回撤深度」

搜尋後確認這題有成熟學術與實務基礎，不需自行重推。

**Ayres & Nalebuff（Yale, 2008）"Life-Cycle Investing and Leverage"**
（[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1149340)）——
用 1871 年起的資料與 10,000 次模擬，論證年輕時該用槓桿。核心不是擇時，是
**時間分散（temporal diversification）**：年輕人未來的儲蓄尚未進入市場，
等於一生的股票曝險過度集中在後期；早期加槓桿是在修正這個失衡。
結果：退休預期財富較 lifecycle fund 高 90%、較 100% 股票高 19%。

**關鍵處方與本專案原構想的差異：**
- 槓桿倍數是**距離目標的函數**（三階段 glide path：0–50% 目標用 2x，之後遞減），
  **不是回撤深度的函數**
- 他們明確**上限 2x，不是 3x**

**實務 out-of-sample：HFEA（UPRO/TMF 55/45，3x）** —— 2010–2021 表現優異，
**2022 崩潰**：升息使股債同向下跌，risk parity 的對沖正好在最需要時失效，
最大回撤逾 70%。這是 3x 長抱最接近真實的自然實驗，結論是「在某個 regime 有效」
而非「長期必然有效」。

**波動耗損直觀例子：** 先漲 10% 再跌 10%，QQQ 損失 1%、TQQQ 損失 **9%**（不是 3%）。

**對本專案的意涵（未實作）：** 若要提高槓桿參與度，依研究應調整的是
**依距離退休目標的 glide path**，而非回撤觸發門檻；且總曝險上限宜參考 2x 而非 3x。
現行 `leveraged_effective_cap` 只涵蓋槓桿 ETF，不等於總投組股票曝險，
兩者不可直接比較——要導入 glide path 需先定義總曝險口徑。

### 其他想法

記在這裡的東西**不是待辦**，是「想清楚了但還沒決定要不要做」。要動工才升格成上方表格或開 plan。

#### Parked lead 的第二層召回

現況：`engine_b/entities.py` 以具名標的（cashtag、`edgar:<TICKER>` 結構化 source、registry 反查的 `co:*`）做**確定性**比對，精準度高但召回率有限——主題相關卻沒有共同 ticker 的關聯抓不到（例如「FCC 禁中國 humanoid」對上「Agility 上市」）。

三個層級，成本由低到高：

1. ~~**主題關鍵字比對**~~ — **2026-07-31 已實作**（`engine_b/themes.py`）。`config/themes.txt` 補上 robotics 主題後，FCC 那則 parked lead 從只能接上 8 筆（共用 ticker）變成 14 筆（共用主題）。反證關鍵字同樣標記該主題並另旗標，因為反面證據要找得到而不是被過濾掉（L7）。
2. **Embedding 相似度** — 理論上召回最好，但引入模糊比對、模型依賴與門檻調校。**代價要誠實計算**：false positive 消耗的是使用者注意力，而降低注意力噪音正是 2026-07-30 那輪重構的目的。若要做，應該只當「排序提示」而非「自動 retrigger」，並且先量測目前漏掉多少關聯，再判斷值不值得。
3. **事件觸發自動化** — `trace_next_trigger` 目前是自由文字，從來沒有被程式評估過。要讓「FCC 規則公布」真的自動 un-park，得先把它變成登記過的 code（像 `config/decision_blockers.json` 那樣），才能程式比對。

判準與封閉字彙表同一條：**會改變決策的事實不能只住在自由文字裡。** `trace_next_trigger` 現在正好違反這條。

#### lead `refs` 是未登記字彙

~~2026-08-01 實測：`refs` 有 56 個不同鍵名，拼錯會靜默失效。~~ **已實作：**
`config/lead_ref_keys.json` 已盤點並登記全部 56 個既有鍵與 value type；`annotate`／`advance`
拒絕未登記鍵，近似拼錯會提示已知名稱。既有歷史資料保持可讀。

#### 其他

- **技術指標擴充**（相對強弱 vs QQQ、ATR）— `engine_c/technical.py` 的 `_METRIC_COLUMNS` 寫死且是 DB 欄位，需配 migration
- **Engine D 未上市公司支援** — 2026-07-30 使用者定案暫不做。現況：`research_ticker` 屬核心 identity 欄位，缺它整組 fallback 成 unresolved 並丟掉 `company_id`，導致未上市公司無論圖品質多好都撞 `identity_unresolved`＋`graph_company_missing`。Lane Memo 不受影響（`thesis/generate_lane_memo.py` 完全不經過 Engine D，`--ticker` 為選用，無 ticker 走「產業全圖模式」）
- **灌文件提升圖深度** — 2026-07-30 實測：53 家公司、63 份 SourceDoc，僅 3 家（Coherent、Sivers、AAOI）有 ≥3 distinct origin 可過 L8。**擋住 Lane Memo 的是證據深度不是 gate 嚴格度**；一家從 1 個 origin 到 3 個約需 2–3 份文件，零架構風險
