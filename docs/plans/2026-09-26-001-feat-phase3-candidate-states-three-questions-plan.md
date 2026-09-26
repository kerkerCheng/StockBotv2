---
date: 2026-09-26
topic: phase3-candidate-states-three-questions
status: active
derived_from: docs/ROADMAP.md（Phase 3，含本 plan §0.4 的 amendment A1–A6）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G3、G6、G8、G9、G12；§4.2、§6）、docs/reports/2026-09-26-phase2-closeout.md §5、docs/reports/2026-09-25-phase1-closeout.md §7
plan_review: 未做 P0（使用者 2026-09-26 定案 12A：執行期間 R2 常規 opt-in，plan 本身不先審）
---

# Phase 3 候選狀態 ＋ 財務三題（給執行模型的完整 plan）

> **執行者：跑 `/phase-run` 的模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。**
> 使用者 2026-09-26 表示本 Phase 會用強模型接著跑；Step 3.5 是研究步驟（寫敘事），**執行者是強模型時不停、直接做**；
> 若換成便宜模型執行，輪到 3.5 時停下來請使用者切強模型（見 §6）。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 3」（含本 plan §0.4 的 amendment A1–A6）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文（尤其「消費契約」「資本與風控」）→ ROADMAP「Phase 3」「消費層對照表」「硬約束」→ 本 plan §0.1–§0.4 →
> 決定紀錄 §4（三題的正解）與 §6（已知問題）→ `docs/refactor/historical-failure-matrix.md` §2 六條 invariant →
> `docs/OPERATIONS.md`「sandbox impact review 五步」→ `alpha/narrative/contracts.py` 檔頭（短評三條規則）→ `alpha/wipeout.py` 檔頭。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**敘事 ledger 的紀錄與欄位、watch registry 的連結、
> 稽核區三題每檔的值或缺席、成交事件的收據、APP 的 state kind、機制存在與否**（見 §11）。
> ⚠ 「可開」的檔數**不是驗收數字**——可開為零就零（ROADMAP 硬約束 7）；它只在心跳與候選板上被印出來。

**一句話目標：** 每一份個股敘事的最後一行，都答得出「為什麼還沒買／為什麼可以開」，而且那個答案指得回一筆在等的 watch 或一句理由；
財務只回答三個是非題——會死嗎、已定價嗎、出現在數字裡了嗎——每題都印得出數字與資料源，印不出就說為什麼。
**程式不替人下結論：** 「可開」由寫的人宣告、程式只驗前提；三題中兩題的答案由寫的人宣告、程式只印數字並強制引用。
它服務 `AGENTS.md` 的「產出若無法讓人分辨做了什麼與沒做，它就不算產出」與 G6「沒有排序後的對稱風險是永遠不收斂」。

---

## 0.1 使用者定案（2026-09-26 互動 session；本 plan 的判斷全部來自這張表）

| # | 題目 | 定案 |
|---|---|---|
| 1 | 敘事長什麼樣 | **A**：同一本短評 ledger 升 **v2**。七格保留、改題：拿掉已退役的估值 placeholder；「市場怎麼看」改「已定價嗎」（必引稽核區數字）；「對了／錯了」改「什麼必須為真、錯的訊號」。加結構化欄位 `rides[]`（節點＋單位＋讀圖 id）、`disproof[]`、三題答案、`candidate_state`。v1 照讀、標「舊版、缺候選狀態」 |
| 2 | 「可開」誰判 | **A**：寫的人宣告，程式驗前提——騎的讀圖現行且結論是護城河或量、三題都有答案或宣告無法量、沒有待處置的反證；前提事後破掉時候選板印「可開（前提失效：…）」、ledger 不改寫。**「已持有」一律由 Sheet 推導**，寫的人不能宣告 |
| 3 | 已定價嗎的三年歷史 | **A**：一次機械回填——價格 3 年；營收歷史美股 EDGAR、台股月營收；有歷史淨負債的算 EV/S，沒有的算 P/S 並標口徑；其他市場印「無法量：歷史不可得」 |
| 4 | 主題籃子 | **A**：**定義移到 Phase 3**（append-only，每次變動附理由與日期；Phase 5 直接沿用）；第一版成分在研究步驟提出、使用者定（pq2） |
| 5 | 三題的答案誰給 | **A**：會死嗎＝四盞燈（機械）；已定價嗎、出現在數字裡了嗎＝程式只印數字＋資料源＋最新一期日期，答案由寫的人宣告、型別層強制引用那幾格 |
| 6 | 稀釋與 going concern | **A**：稀釋——回填同口徑股數一年以上（美股 EDGAR 封面股數；其他市場無法量）；going concern——新增結構化欄位（有／無／未查），互動 session 讀審計意見後寫，屬判讀，走 Engine C 判讀寫入 gate（pq2） |
| 7 | 成交收據範圍 | **A**：alpha 買進缺敘事 → fail closed，`--override --reason` 放行並記「無敘事」；alpha 賣出要輕收據（一句理由＋觸發的反證 watch id，若有）；beta 不需收據 |
| 8 | thesis 引用的 39 條 claim 反證（Phase 1 #1） | **A**：只自動登記新敘事 `disproof[]` 寫下的；39 條裡被新敘事引用到的，在研究步驟搬進去（G8「只登記被引用的」） |
| 9 | 強模型研究步驟 | **A**：排進 plan（Step 3.5）：用 v2 重寫 AXTI、COHR、LITE，寫 Sivers 第一份，每份宣告候選狀態；主題等權組第一版成分在這一步提 pq2。**使用者補充：本 Phase 用強模型執行，3.5 不必停下換模型** |
| 10 | 個股頁面板重排殘留（Phase 2 #8、#9、#12） | **A**：一起做——argument「鏈」段拿掉 `get_bottlenecks`（sub≥4 成員）改印騎的讀圖；`review_required` 接回讀圖面板；argument 標題改 |
| 11 | Phase 2 帶過來的小修 | **a＋b＋c**：a `graph_holes` 段計數改「有命中的型別數」、刪重複加總、心跳與稽核共用一份；b cashtag 無後綴解析（registry 唯一才解析，歧義列出不猜）；c `coverage_gaps`／`duplicate_nodes` 兩支 CLI 退役＋清磁碟孤兒 artifact。d（稽核依賴 Neo4j）**維持不動** |
| 12 | R2 | **A**：執行期間六條 trigger 命中就**常規 opt-in**（直接發 `WORK_REQUEST`，NO_GO 才停）；plan 本身**不做 P0** |

## 0.2 現況實測（2026-09-26；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| 短評 ledger | **3 檔**（AXTI 2 行、COHR 2 行、LITE 3 行），全是 `investor-brief/v1` | `ls library/private/alpha/briefs/`；每檔 `wc -l` |
| 短評裡的退役估值 placeholder | 三份現行短評的 `if_right_if_wrong` 都寫了 `{bet_target}`／`{payoff}`（COHR、LITE 另有 `{base_target}`），Phase 0 後填出來是「（尚無）」；`market_view` 用 `{sell_side_target}`／`{market_multiple}`／`{analyst_count}` | 讀三檔最後一行的 `slots` |
| 殭屍 grep 對短評的 keep-list | `alpha/narrative/contracts.py`、`alpha/models/session_assessor.py`、`tests/test_investor_brief.py` 在 C 組（`sell_side_target`）以 legacy_key 留著 | `scripts/retired_mechanism_grep.py` 約 111–141 行 |
| thesis lifecycle | 3 筆：AXTI、COHR、SIVE.ST（Sivers 有 thesis 無短評；LITE 有短評無 thesis） | `python -c "import json;print(list(json.load(open('thesis/lifecycle.json',encoding='utf-8'))))"` |
| 個股頁 readiness | 73 份；絕大多數 `blocked`，最常見 blocker `brief=not_yet_recorded` | `python -m webapp status` |
| 核心／選配面板 | `CORE_PANELS=("headline","brief","argument","research","wipeout")`；`OPTIONAL_PANELS=("fundamental","bet","readings")` | `briefing/analyst_view/contracts.py:73,82` |
| Engine C 快照範圍 | `financial_snapshots` **2026-07-08 → 今天、73 檔**（每檔約 60 列）；`ev_revenue` 72 檔有值——**沒有任何一檔有三年歷史** | scratchpad 查詢：`SELECT min(snapshot_date), max(snapshot_date), count(DISTINCT ticker) FROM financial_snapshots` |
| 股數序列 | 73 檔都有，最長約 80 天 → 稀釋燈窗不滿一年，**今天 0/73 判色** | 同上，`WHERE shares_outstanding IS NOT NULL GROUP BY ticker` |
| going concern | `manual_fields` 的 `litigation_and_audit_flags` 1 筆（6594.T，自由文字）；`going_concern_flag()` **必回灰**（`capability_absent`） | `alpha/wipeout.py::going_concern_flag` |
| 月營收 | 7 檔台股、各 25 個月（2024-09 → 2026-08） | `monthly_revenue_observations` |
| 分部／產品線營收占比 | 人工觀測 31 檔／8 檔 | `manual_observations` 的 `segment_revenue_share`／`product_line_revenue_share` |
| 上市地分布 | 73 檔：美股 44、`.T` 6、`.TWO` 5、`.KS` 3、`.SZ`／`.TW`／`.SS`／`.ST`／`.PA` 各 2、`.HK`／`.V`／`.L`／`.AX`／`.DE` 各 1 | ticker 後綴計數 |
| 成交事件 | `library/trades/trade_log.jsonl` 2 行 | `wc -l` |
| alpha／beta 判別 | `risk/hard_caps.py`：不在 `config/beta_policy.json` `instruments` 裡的標的＝alpha | `risk/hard_caps.py:14-17,105` |
| 心跳的候選板缺席 | `_CANDIDATE_BOARD_ABSENCE`、`_PRICED_IN_ABSENCE` 兩個 `not_yet_recorded`（段 2 與段 4 共三處印） | `crons/heartbeat.py:604-612,658,702,1216` |
| 已退役的 state kind | `basket`、`multi_year` 由 `webapp/contracts.py` 拒收——候選板**不能**叫 `basket` | `webapp/contracts.py:57-60` |
| 殭屍 grep B 組 | regex `basket\|籃子\|…`，掃 code／skills／tests／config／static——**主題籃子在這些區域不得叫「籃子」或 `basket`** | `scripts/retired_mechanism_grep.py:18` |
| `graph_holes` 段計數 | 九型命中之和（異單位）；`queue_segments.observe()` 的 `research_total` 再加一次；心跳與 `audit/checks.py::_graph_holes` 各算一份 | Phase 2 closeout §5 #1；`engine_b/queue_segments.py:339` |
| `get_bottlenecks` | read model 仍以 sub≥4 成員餵個股頁 argument「鏈」段 | `alpha/provider.py:82`、`alpha/providers/graph_neo4j.py:249` |

## 0.3 本 Phase 刻意不做

- **不動圖**（Neo4j 節點、邊、屬性）；不動讀圖 ledger（讀圖是 Phase 2 的；3.5 只**讀**現行讀圖）。
- 不做量測（Phase 5）：追蹤表的組基準、三個 power-law 統計量、圖預測對錯表、計分表接組超額。**本 Phase 只定義主題等權組、並讓「已定價嗎」讀它**；Phase 5 沿用同一個定義。
- 不做層中心選源與 `substitutability` 的 `auto` 投影稽核（Phase 4）。
- **三題不得長回估值模型**（ROADMAP「明確不做」）：不算目標價、不算 payoff、不對同業倍數校準、不設「已定價」門檻。組中位數只當脈絡印。
- 不讓候選狀態排序：候選板組內按 ticker 字母，沒有分數、沒有 top-N、沒有「最該買」。
- 不改 `AGENTS.md`（本 Phase 沒有任何判準句要改）。
- 不回填 Engine C 的**人工** ledger（`manual_observations` append-only）：回填只進新的機械歷史表（§3）。
- Phase 2 closeout §5 其餘各題（#2 研究動作、#4 維持、#6／#7／#10／#11／#13–#17）不在本 Phase，照實帶到結案待決（§14）。

## 0.4 ROADMAP amendment（五欄；使用者 2026-09-26 定案，ROADMAP Phase 3 列與 Phase 5 列同 commit 改寫）

**A1｜敘事是短評 v2：七格改題，加結構化欄位**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「narrative ledger 加 `candidate_state`（五值封閉字彙）」 |
| 新觀察 | 敘事 ledger 就是短評 ledger（`library/private/alpha/briefs/`，3 檔）；七格裡「市場怎麼看」「如果對了／錯了」兩格的題目與 placeholder 仍是已退役的估值鏈，三份現行短評都寫了 `{payoff}` |
| proposed change | `investor-brief/v2`：slot key 集合換成 `demand`、`supply`、`bottleneck`、`priced_in`、`our_bet`、`what_must_be_true`、`when`（**改了語意的格換 key，不沿用舊 key**——L12）；placeholder 字彙拿掉 `base_target`、`bet_target`、`base_return`、`payoff`、`downside_target`、`downside_return`、`value_date`、`sell_side_target`、`market_multiple`，加三題稽核區的 placeholder（§4）；結構化欄位 `rides[]`、`disproof[]`、`answers`、`candidate_state`（§5）。v1 照讀、id 不變 |
| why | L19：每次載入的題目會被當成目標；只加欄位，寫的人每次都會照舊題目寫估值 |
| impact | `alpha/narrative/`、`alpha/providers/briefs.py`、`alpha/cli.py` 的 brief 入口、`alpha/models/session_assessor.py`、`briefing/alpha_view/builder.py`（填值）、殭屍 grep C／E 組 keep-list 縮小 |

**A2｜主題等權組定義從 Phase 5 移到 Phase 3**

| 欄 | 內容 |
|---|---|
| 原 roadmap | Phase 5「主題等權籃子定義（append-only、附理由與日期）」 |
| 新觀察 | 「已定價嗎」三行中的第二、三行（組中位數、30／90 天相對漲幅）都要它；留到 Phase 5，這兩行整個 Phase 3 都只能印缺席 |
| proposed change | Phase 3 建 append-only 的主題等權組 ledger（§4.2）；成分由研究步驟提 pq2、使用者定；**程式與 UI 一律叫「主題等權組」／`theme_cohort`**（殭屍 grep B 組會掃「籃子」「basket」）；Phase 5 直接沿用同一個定義 |
| why | 決定紀錄 §4.2「籃子定義與 G9 量測基準共用同一個」；§6.7「成分是一個判斷，寫下時附理由與日期，變動 append-only」 |
| impact | 新 ledger 與讀取器；ROADMAP Phase 5 列刪掉「主題等權籃子定義」改成「沿用 Phase 3 的主題等權組」 |

**A3｜三題的資料源：一次機械回填**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「已定價嗎＝自家 EV/S（虧損期 P/S）三年百分位…」「會死嗎＝歸零旗標補稀釋與 going concern 兩盞」 |
| 新觀察 | 快照最早 2026-07-08，沒有任何一檔有三年；股數序列約 80 天，稀釋燈 0/73 判色；going concern 沒有能判色的欄位 |
| proposed change | Engine C 加機械歷史表（價格、營收、股數、淨負債；每列帶來源與 `published_at`／`filed`），一次回填＋可冪等重跑；EV/S 需要同期淨負債，沒有就算 P/S 並標口徑；拿不到的市場印 `absence_kind`。going concern 加結構化欄位 `going_concern_opinion`（`substantial_doubt`／`no_substantial_doubt`／`not_reviewed`），屬 judgment，寫入走既有 Engine C 人工觀測路徑（pq2 `engine_c_observation`） |
| why | 不回填，這兩題三年內恆為缺席（L14-4 恆亮）；going concern 的措辭精度本身是 claim（L11-1），不得從自由文字機械推 |
| impact | `engine_c/` 新 migration 與回填模組；`engine_c/checklist.py::get_wipeout_inputs`；`alpha/wipeout.py` |

**A4｜成交收據的範圍與 override**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「`record_trade.py --receipt`：成交事件內嵌…，缺收據 fail closed」 |
| 新觀察 | beta ETF 沒有敘事；使用者可能買一檔還沒寫敘事的標的——無條件 fail closed 等於讓研究 gate 資本（違反 A5 是唯一授權資本的地方） |
| proposed change | alpha 買進：自動組完整收據，缺敘事 fail closed，`--override --reason` 放行並在收據記 `narrative: absent`；alpha 賣出：輕收據（一句理由＋觸發的反證 watch id，若有），缺理由 fail closed；beta：不需要收據。override 形狀與 5% 硬擋相同 |
| why | 收據是問責不是授權；「出場只認反證」所以賣出要記是哪一條反證 |
| impact | `scripts/record_trade.py`、`risk/hard_caps.py`（只讀其 alpha 判別） |

**A5｜個股頁面板重排一併處理 Phase 2 殘留**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「readiness 核心面板換」 |
| 新觀察 | argument「鏈」段仍吃 `get_bottlenecks`（sub≥4 成員＝filter 殘留，G1）；讀圖面板 `review_required` 的路沒接（Phase 0 偏差 #16）；argument 標題延了兩個 Phase |
| proposed change | readiness 換的同一個 Step 裡：「鏈」段改印敘事 `rides[]` 指向的讀圖；`review_required` 接回讀圖面板；argument 標題改 |
| why | 同一批面板，拆開做要改兩次同一份 digest 基準 |
| impact | `briefing/alpha_view/builder.py`、`briefing/analyst_view/`、read model 的 `get_bottlenecks` 呼叫端 |

**A6｜Phase 2 帶過來的三個小修**

| 欄 | 內容 |
|---|---|
| 原 roadmap | （Phase 2 closeout §5 #1、#3、#5 待決） |
| 新觀察 | 見 closeout §5 |
| proposed change | a `graph_holes` 段計數＝**有命中的型別數**，刪 `research_total` 對它的加總，心跳與稽核共用一個函式；b `company_id_for_ticker` 對無後綴 cashtag：registry 中**恰一個**後綴版本時解析，零個或多個時回 `None` 並把候選列進「解析不到」計數（不猜）；c `python -m query.coverage_gaps`／`query.duplicate_nodes` 的 CLI 入口退役（函式留給走圖用），磁碟孤兒 `coverage.json`、`ranking.json`、`basket.json` 刪除 |
| why | a：異單位加總不該存在（§0 第 7 條的立法目的）；b：INV-1 「ID 沒解析對」不是「圖中無此公司」；c：退役要拿乾淨 |
| impact | `engine_b/queue_segments.py`、`audit/checks.py`、`crons/heartbeat.py`、`identity/registry.py`、`query/coverage_gaps.py`、`query/duplicate_nodes.py` |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-09-26 已核准的 PLAN_PROPOSAL**（§0.1 十二題）。`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 3 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（使用者 2026-09-26 定案 12A）**：預定兩處——R2-a（3.4 之後：append-only 敘事 contract ＋ 自動登記 hook）、
R2-b（3.8 之後：資本路徑上的收據與 fail closed）；其他 Step 若命中 trigger 同樣直接發 `WORK_REQUEST`。NO_GO → `AWAITING_HUMAN`。

**停點：** 無預定停點。3.5 由強模型做（使用者已表示本 Phase 用強模型執行）；**若執行者是便宜模型，3.5 停下來印 §6 的「強模型貼這段」**。
3.5 會鑄兩類 pq2（主題等權組成分 `manual`、going concern 觀測 `engine_c_observation`）——**掛號後接著做下一件，不停在編號上等**；
它們 go 之後的寫入由收到 `go` 的那個 session 做（§6 第 3 點）。

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。commit 短碼由下一個 Step 的 commit 補填。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30）是唯一排程，它寫 `library/`、Engine C 快照、APP artifact。
**3.2（Engine C migration）與 3.6（`crons/daily_task.py` 的 materialize 旗標）的 commit 不得跨越 05:30 還沒 push**；3.2 的回填**不得與 daily 同時跑**（同一個 SQLite）。
開工前查 `schtasks /Query /TN StockBotv2-Daily /V /FO LIST` 的下次執行時間。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 3.0 | 基準快照 | ○ | 執行模型 | |
| 3.1 | Phase 2 帶過來的三個小修（A6 a／b／c） | ○ | 執行模型 | |
| 3.2 | Engine C 機械歷史表＋一次回填；going concern 結構化欄位 | ○ | 執行模型 | |
| 3.3 | 三題稽核區：會死嗎（稀釋改讀 EDGAR 序列、GC 讀新欄位）、已定價嗎三行、出現在數字裡；主題等權組 ledger | ○ | 執行模型 | |
| 3.4 | 敘事 v2 契約：七格改題、`rides[]`、`disproof[]`＋自動登記、`answers`、`candidate_state` 與前提驗證（R2-a） | ○ | 執行模型 | |
| 3.5 | 研究：v2 重寫 AXTI／COHR／LITE、寫 Sivers；提主題等權組成分與 going concern 觀測的 pq2 | ○ | **強模型** | |
| 3.6 | 候選狀態板：`candidates` kind 與頁、positions 連「已持有」、心跳各狀態檔數與最老滯留、較昨 diff | ○ | 執行模型 | |
| 3.7 | 個股頁：首屏候選狀態＋三個字、稽核區三題、readiness 核心面板換、argument 鏈段／標題、`review_required` 接讀圖面板 | ○ | 執行模型 | |
| 3.8 | `record_trade.py` 收據（R2-b） | ○ | 執行模型 | |
| 3.9 | `test_full_chain_acceptance` 重寫成新管線 full chain（Phase 0 偏差 #29） | ○ | 執行模型 | |
| 結案 | completion gate ＋ closeout ＋ R2 ＋ ROADMAP ✅ | ○ | 執行模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 3 結案；撞到六條停止條件才停。
Step 3.5 是強模型的研究步驟：執行者是強模型就直接做，不是就停下來印 §6 的「強模型貼這段」給我。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|

---

## 0. 不可越線（違反即 NO_GO）

1. **不碰圖與讀圖 ledger**：不改 Neo4j；讀圖 ledger 只讀。
2. **敘事 ledger 只由 Step 3.5（強模型）經正式入口 append**；其他 Step 的測試一律用暫存目錄。**既有 7 行 v1 紀錄一行都不改寫**，`brief_id` 用新程式重算必須逐字相同。
3. **Engine C 人工 ledger（`manual_observations`、`manual_fields`）只能經既有人工觀測路徑 append，且 judgment 欄位要有 pq2 `go`**；回填只寫新的機械歷史表。**going concern 觀測的寫入是 Engine C 判讀寫入 gate**——3.5 只鑄 pq2，不寫。
4. **舊 Decision Store 只准讀**：3.0 記 sha256 與 `live_choices`，結案比對必須相同。
5. **`library/trades/trade_log.jsonl` 與 Google Sheet 不得在測試或試跑中寫入**；`record_trade.py` 的試跑一律 dry-run（不帶 `--apply`）或指到暫存 log。
6. **任何 `python -m <module>` 命令字串變更 → sandbox impact review 五步**（ROADMAP 硬約束 10），同一個 commit 改相應測試。本 Phase 已知會撞：3.1c（兩支 CLI 退役）、3.2（新回填入口，**不進任何無人值守 allowlist**）、3.6（daily materialize 旗標）。
7. **每刪一個測試檔或測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守。** 活機制的測試不可刪斷言。
8. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
9. **不排序、不打分、不設門檻**：候選板組內按 ticker；三題沒有「已定價／未定價」的門檻；組中位數只是脈絡；沒有跨檔合成數字。
10. **命名：** code／skills／tests／config／static 裡不得出現「籃子」「basket」（殭屍 grep B 組）與 `sell_side_target`、`payoff`、`隱含報酬`、`目標倍數`、`calibrat`（C／E 組）的新命中；主題籃子一律叫「主題等權組」／`theme_cohort`。
11. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。**
12. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** 敘事與候選狀態是 A3（研究判斷、可重算、append-only）；收據是 A5；**A3 不得替 A5 做決定**——候選狀態不擋成交（收據只記它），不給尺寸。

---

## 1. Step 3.0 基準快照（Z0，一個 commit）

寫 `docs/reports/2026-09-2x-phase3-baseline.md`，每項附命令與輸出摘要：

1. `python -m pytest -q` 通過數；測試檔數；以本 commit 為起點的 `def test_` 名單存檔（結案比對函式層級增刪）。
2. `python -m audit invariants`（13 PASS 預期）。
3. 短評 ledger：3 檔 7 行的 `brief_id` 用現行程式重算＝檔內值（7／7）。
4. 73 份個股頁：每檔 readiness 與 blockers、核心面板文字 digest（`python scripts/analyst_view_text_digest.py --per-panel`）。
5. 歸零旗標四盞每盞有值（非灰）的檔數／73——**④ 的基準**（預期稀釋 0、GC 0）。
6. `python -m crons.heartbeat --out <tmp>` 全文存檔（段 2 兩個 `not_yet_recorded` 那幾行要逐字記）。
7. `python -m engine_b.event_watch counters`；`python -m query.graph_walk --json` 的九型命中／母體；`python -m webapp status` 的 kind 清單。
8. 舊 Decision Store 三個 `*.db` 的 sha256 與 `live_choices`（`?mode=ro`）；`trade_log.jsonl` 行數與 sha256。
9. `python scripts/retired_mechanism_grep.py` 九組三個 0；列出 C／E 組目前與短評相關的 keep-list 條目（3.4 後要縮小，且不得有「已列但不再命中」的腐壞條目）。
10. 三檔 v1 短評目前填出來的首屏文字（哪幾格印「（尚無）」）——3.5 重寫後對照用。

## 2. Step 3.1 Phase 2 帶過來的三個小修（各 Z1，R1，可拆三個 commit）

**a｜`graph_holes` 段計數。** 改哪裡：`engine_b/queue_segments.py`（段計數語意、`research_total` 不再加 `graph_holes`）、`audit/checks.py::_graph_holes`、`crons/heartbeat.py::build_queue`。
怎麼改：新增一個共用函式（放在走圖或 queue_segments，二擇一，理由寫八欄）回「有命中的型別數」；心跳與稽核都呼叫它，刪掉另一份實作。心跳段 3 的九格逐型印法**不變**。
怎麼驗：`test_there_is_no_cross_type_number_anywhere_in_the_result` 等既有測試照綠；新測試斷言段計數 ≤ 9 且等於「命中 >0 的型別數」；`grep -n research_total` 的每個消費端寫明（目前沒有 production consumer）。
L11-6 ④：`QueueSegments`／`QueueLiveness` 稽核那一行——看 3.0 的輸出，改後數字從 60 變成型別數，其他格不變。

**b｜cashtag 無後綴解析。** 改哪裡：`identity/registry.py::company_id_for_ticker`（或其呼叫端的 lead 實體解析，二擇一，理由寫八欄）；走圖第 5 型的 `unresolved_names`。
怎麼改：精確命中優先；無後綴且 registry 中**恰一個** `<TICKER>.<後綴>` → 解析；零或多個 → `None`，多個時把候選放進解析不到的明細（不猜）。
怎麼驗：`SIVE` → `co:sivers_semiconductors`（經 `SIVE.ST`）；造一個有兩個後綴的夾具回 `None` 且列出候選；走圖第 5 型的解析不到清單在真實資料上變短，逐項寫出哪幾個被解析、哪幾個仍解析不到與原因。
L11-6 ④：所有呼叫 `company_id_for_ticker` 的地方——**美股 ticker 與某個外國後綴 ticker 同名**時（例 `SOI`）會不會被錯解析？先 grep registry 列出所有「無後綴 ticker 同時存在帶後綴版本」的碰撞，寫進八欄。

**c｜兩支 CLI 退役＋孤兒。** 改哪裡：`query/coverage_gaps.py`、`query/duplicate_nodes.py` 的 `__main__`／`main`；`docs/OPERATIONS.md` 提到它們的段落；APP artifact 目錄的 `coverage.json`、`ranking.json`、`basket.json`。
怎麼驗：`python -m query.coverage_gaps` 不再是入口（或印退役訊息 exit 非 0，二擇一寫八欄）；走圖照常；`git grep -n "query.coverage_gaps\|query.duplicate_nodes"` 在活文件與 skills 為 0（歷史文件除外）；三個孤兒檔不存在。
sandbox impact review 五步（命令字串退役）。

## 3. Step 3.2 Engine C 機械歷史表＋一次回填；going concern 結構化欄位（Z2，R1）

**改哪裡：** `engine_c/migrations/<日期>_add_history_tables.sql`、`engine_c/schema.sql`；新模組 `engine_c/history_backfill.py`（CLI `python -m engine_c.history_backfill`）；`engine_c/observation_fields.py`（新欄位 `going_concern_opinion`）；`fetchers/edgar.py`（若需 companyfacts 取數）。

**怎麼改：**
1. 新表（名稱可調，理由寫八欄）：`price_history`（ticker、bar_date、close、currency、source、fetched_at）、`fundamental_history`（ticker、metric ∈ {revenue_ttm, revenue_quarter, shares_outstanding_cover, cash, total_debt}、period_end、**filed／published_at**、value、currency、unit_scale、source、source_ref、fetched_at）。**每列都要答得出「T 時刻我知道什麼」**：財報數字的可用日＝`filed`（EDGAR）或月營收的 `published_at`，**不得用 fetched_at 冒充**（INV-6、L11-5）。
2. 來源：價格——yfinance 3 年日線（全部 73 檔）；營收——美股 EDGAR companyfacts（季度＋年度，組 TTM），台股——既有 `engine_c/monthly_revenue.py`／`twse.py` 往回補到 3 年；淨負債——美股 EDGAR 同一份 companyfacts（現金、總債）；股數——美股 EDGAR 封面股數（`dei:EntityCommonStockSharesOutstanding`，帶封面日期）。**其他市場不硬湊**：寫一列 absence 紀錄或在讀取端回 `absence_kind`（見 §4）。
3. 冪等：同 (ticker, metric, period_end, source) 重跑不重複；回填報告印每檔每種 metric 的列數、最早、最晚、缺什麼。
4. going concern：`observation_fields` 登記 `going_concern_opinion`，`kind=judgment`，封閉值 `substantial_doubt`／`no_substantial_doubt`／`not_reviewed`，必帶 `source_ref`（審計報告位置）與 `as_of`（審計報告日）。**寫入走既有人工觀測路徑，judgment 欄位要 pq2**——本 Step 只登記欄位與驗證，不寫任何一筆。

**怎麼驗：** migration 在暫存 DB 上 up 成功、既有表不變；回填在**暫存 DB 副本**先跑一次（用真實網路），報告寫進八欄；再對正式 DB 跑（不得與 daily 同時）。
新測試：PIT——`as_of=T` 的查詢只回 `filed ≤ T` 的列；同口徑——股數序列只收 `shares_outstanding_cover` 一個來源（不與 yfinance 快照混）；冪等；`going_concern_opinion` 值不在封閉字彙拒收、無 `source_ref` 拒收。
**L11-6 ④：** daily 的 Engine C ETL（`engine_c/etl_yfinance.py`）與 `get_wipeout_inputs()` 讀的是舊表——確認 migration 不改舊表、daily 下一輪照常（3.0 的快照列數＋1 天）。
sandbox impact review：新 CLI 只給互動 session 用，不進任何無人值守 allowlist。

## 4. Step 3.3 三題稽核區＋主題等權組（Z2，R1）

**改哪裡：** 新模組 `alpha/three_questions.py`（純函式，判色／取數分開，比照 `alpha/wipeout.py`）；`engine_c/checklist.py`（取數：歷史表、組成分的價格）；`alpha/wipeout.py`（稀釋讀 EDGAR 序列、GC 讀新欄位）；主題等權組 ledger `library/private/alpha/theme_cohorts/<theme>.jsonl` 與 `alpha/providers/theme_cohorts.py`、CLI `python -m alpha theme-cohort`；`briefing/alpha_view/`（read model 加 `three_questions` section）。

**4.1 三題，每題每行都是 `{value, source, as_of, 口徑}` 或 `absence_kind`（既有封閉字彙；需要新詞先登記，L16）：**

| 題 | 行 | 規則 | 缺席出口 |
|---|---|---|---|
| 會死嗎 | 四盞燈 | 既有 `wipeout_flags`；**稀釋**改讀 `shares_outstanding_cover` 序列（同口徑、窗 ≥365 天才判色，規則不變）；**going concern** 讀 `going_concern_opinion`：`substantial_doubt`→紅、`no_substantial_doubt`→綠、`not_reviewed` 或無紀錄→灰 | 沿用各燈的 `absence_kind`；GC 無紀錄從 `capability_absent` 改 `not_yet_recorded`（欄位已存在，只是還沒人寫） |
| 已定價嗎 | ①自家歷史百分位 | 今天的 EV/S（有同期淨負債時；否則 P/S，口徑欄寫明）落在自己 3 年序列的第幾百分位；序列每個點只用當時已公開的營收與淨負債（PIT）；**虧損期**（TTM 營業利益 <0）照 ROADMAP 用 P/S | 窗不滿 3 年：印實際窗長並回 `insufficient_evidence`；剛上市或剛轉型：`inputs_incompatible`「歷史不可比」（誰算「剛轉型」由敘事宣告，程式不猜；沒宣告就照算） |
| | ②主題等權組中位數 | 組成分今天的同口徑倍數中位數；**只印，不比較、不算差** | 組未定義：`not_yet_recorded`「主題等權組未定義（pq2 [N]）」；成分資料不足一半：`insufficient_evidence` |
| | ③相對組的 30／90 天漲幅 | 本檔 30／90 天價格報酬 − 組等權報酬 | 同②；價格序列不足：`insufficient_evidence` |
| 出現在數字裡了嗎 | 序列 | 有月營收的：最近 12 個月 YoY 序列＋最新一期與公布日；有分部／產品線營收占比人工觀測的：該序列與觀測日；其餘：最近 8 季營收序列（EDGAR） | 都沒有：`upstream_unavailable`；只有一點：`insufficient_evidence` |

**4.2 主題等權組 ledger：** append-only、content-addressed id、`supersedes_id`；每筆必帶 `theme`、`members[]`（ticker＋company_id，registry 解析得到才收）、`reason`、`decided_on`、`pq2_ref`（使用者核准的編號；**沒有就拒收**）。等權、成分變動即新紀錄。本 Step **只建機制、不寫任何一筆**（3.5 提 pq2，`go` 後才寫）。

**怎麼驗：** 純函式測試每行每個缺席出口都會出現（L12：燈滅與燈綠不同形）；PIT 測試（造一檔在 T 之後才公布的營收，T 的百分位不得用到它）；組 ledger 拒收無 `pq2_ref`、成員解析不到、重複 id；**稽核區沒有任何「門檻」「已定價／未定價」判定字**（測試斷言 section 裡沒有布林結論欄位）。
真實資料試跑：73 檔三題每行的「有值／缺席（依 kind）」計數表寫進八欄——這就是 ROADMAP ③ 的第一次讀數。
**L11-6 ④：** 個股頁 wipeout 面板——稀釋改讀新序列後，美股有幾檔從灰變色、非美股仍灰；逐檔列在八欄，任何一檔**從有色變灰**都要解釋。

## 5. Step 3.4 敘事 v2 契約（Z2，R1 ＋ R2-a 常規 opt-in）

**改哪裡：** `alpha/narrative/contracts.py`（`RECORD_VERSION` 分支、slot 集合、placeholder 字彙、驗證）、`alpha/providers/briefs.py`（寫入端＋登記 hook）、`alpha/cli.py` 的 brief 入口、`alpha/models/session_assessor.py`（`BRIEF_FRAME` 消費端）、`briefing/alpha_view/builder.py`（`fill_brief`、`select_brief`）、`engine_b/disproof.py`（`current_readings` 同形的「現行敘事」、`disproof_counts` 認敘事來源）、`audit/sources.py`／`audit/checks.py`（Orphans 解析 `brief_id`）、`scripts/retired_mechanism_grep.py`（keep-list 縮小）。

**怎麼改：**
1. **v1 不動**：`investor-brief/v1` 的 slot 集合、placeholder、`brief_id` 欄位集合原樣保留（id 依版本分支，比照讀圖 `_ID_FIELDS`／`_ID_FIELDS_V2`）；v1 的現行紀錄在候選板印「舊版，缺候選狀態」。
2. **v2 七格**（問題寫進新的 `BRIEF_FRAME_V2`，`do_not` 照舊風格）：`demand`（什麼在放量、誰在花錢）、`supply`（它坐在哪幾層／哪幾格、各占多少營收——**占比必須是 placeholder 或引用**）、`bottleneck`（為什麼卡在它——必須引用 `rides[]` 的讀圖結論，誰想殺它＝反向路徑）、`priced_in`（已定價嗎——**必須含 `{own_history_pctile}`**，組的兩行有值時必須一併引用）、`our_bet`（賭的是哪一件事、騎層還是插槽）、`what_must_be_true`（什麼必須為真、錯的訊號是什麼——**不得有價格或報酬**）、`when`（`{next_checkpoint_date}`）。
3. **v2 placeholder 字彙**：留 `price`、`analyst_count`、`next_checkpoint_date`、`ripeness`、`gap_closure`、`{assumption:…}`（Phase 1 #4 回填問題照舊）；拿掉 A1 列的九個；新增三題稽核區的 placeholder（`own_history_pctile`、`own_history_basis`、`cohort_median`、`rel_return_30d`、`rel_return_90d`、`in_numbers_latest`、`in_numbers_published_at`；名稱可調，不得撞殭屍 grep）。
4. **結構化欄位**（進 v2 的 id 欄位集合）：
   - `rides[]`：`{node, unit, reading_id}`；寫入時 `reading_id` 必須是該（節點, 單位）的現行讀圖（`alpha/providers/structure_readings.py::select_readings`）。
   - `disproof[]`：每條 L7 三件套（`condition`、`check_frequency`、`action_48h`）＋`source`（`self`，或 thesis claim 的 id／讀圖 id——指得回原文，L18）。**寫入成功後自動登記 `semantic_condition` watch**（比照 `register_reading_watches`，來源＝`brief_id`，同一條件換版時收舊登新）。
   - `answers`：`{priced_in: yes|no|unmeasurable, in_numbers: yes|no|unmeasurable}`；`unmeasurable` 只在對應稽核行全是缺席時允許；`yes`／`no` 時對應 slot 必須含該題的 placeholder（型別層強制，決定 5A）。會死嗎不由人答。
   - `candidate_state`：`{state, watch_id?, reason?}`，`state ∈ {open, missing, priced_wait, pass}`（**`held` 不收**——由 Sheet 推導，決定 2A）。`missing`／`priced_wait` 必帶 `watch_id` 且那筆 watch 在寫入當下是 active 且有到期；`pass` 必帶 `reason`；`open` 過三個前提（下一點）。
5. **`open` 的前提驗證（寫入時，決定 2A）**：①`rides[]` 至少一條、每條讀圖現行且 `kind ∈ {moat, volume}`；②兩個 `answers` 都有值；③這檔的 thesis、`rides[]` 讀圖、本敘事前一版登記的語意 watch 中**沒有**「觸及待處置」的。任一不過 → 拒收並印是哪一條。**顯示端每天重驗同三條**（§7），破掉時印「可開（前提失效：…）」——ledger 不改寫。
6. **反證觸及後的去處（INV-4）**：敘事來源的語意 watch 被判觸及 → 該檔候選板列印「敘事該重寫：反證 <watch id> 觸及」；到期 → 同一處印「敘事該重寫：反證 <id> 到期未判」（比照讀圖來源進重讀理由）。consumer＝research-drain 第三段（skill 同 commit 補一句）。
7. **殭屍 grep**：v2 拿掉的 placeholder 只剩 v1 相容碼命中——keep-list 理由改寫成「v1 相容（legacy_key）」，不再需要的條目刪掉；「已列但不再命中」的腐壞條目為 0。

**怎麼驗：** v1 7 行 id 重算 7／7；v2 拒收規則各一條會紅的測試（禁字、未知 placeholder、`priced_in` 缺 placeholder、`answers=unmeasurable` 但稽核行有值、`missing` 缺 watch_id／watch 不 active／無到期、`pass` 缺 reason、`open` 三個前提各自不過、`held` 被拒、`rides[].reading_id` 不是現行）；登記 hook 測試（寫入即登記、換版收舊登新、同內容重跑不重複登記）；`disproof_counts` 與心跳「反證在盯／未盯」認得敘事來源；audit Orphans 解析得到 `brief_id`。
**L11-6 ④：** 三檔 v1 短評的首屏——3.4 後它們仍照 v1 填（`if_right_if_wrong` 繼續印「（尚無）」），**逐字與 3.0 相同**；語意 watch 計數器 `semantic_active` 與 3.0 相同（還沒有 v2 敘事）。

**R2-a（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-a，Phase 3 Step 3.4）
Target: 3.4 的 commit；alpha/narrative/contracts.py、alpha/providers/briefs.py、engine_b/disproof.py、audit/checks.py
Claimed acceptance: v1 id 7／7 不變；v2 拒收規則全有會紅的測試；open 三前提寫入時驗；disproof 寫入即登記 semantic_condition；held 不可宣告
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑 pytest 相關檔與 audit invariants；用暫存目錄造 8 筆應拒收的 v2 spec 與 1 筆應收的，確認結果；
      確認 v2 的 id 欄位集合包含 rides／disproof／answers／candidate_state、v1 的沒有；確認沒有任何 code path 會為 v1 紀錄補寫候選狀態；
      殭屍 grep 九組三個 0 且 keep-list 無腐壞條目
Boundaries: 不改 code、不 commit、不寫真實 ledger、不核准 pq2
```

## 6. Step 3.5 研究：v2 敘事四份＋兩類 pq2（**強模型、互動 session**；研究，不是開發）

**強模型貼這段（執行者是便宜模型時印給使用者）：**
```
讀 docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md §6，做 Step 3.5：
用 v2 重寫 AXTI、COHR、LITE 三份短評、寫 SIVE.ST 第一份，每份宣告候選狀態；提主題等權組與 going concern 的 pq2。完成後更新進度表、commit、push。
```

1. 每檔先跑：`python -m alpha research <T>` 的 packet（`brief_frame` 已是 v2）、`python -m query.structure <node> --unit <unit> --quotes`（它騎的每一格）、三題稽核區（3.3）。
2. **寫四份 v2**（AXTI、COHR、LITE、SIVE.ST），`supersedes_id` 指舊 v1（SIVE.ST 沒有舊版）。
   - `rides[]`：只能騎現行讀圖。**已知**：AXTI → `mat:inp_substrate`（層、volume）；COHR、LITE 要先確認它們騎的節點有沒有現行讀圖——**沒有就不得宣告 `open`**，寫 `missing`（X＝那一層／格的讀圖），watch 用 date 型、到期＝你預計讀它的日子；Sivers 的兩份插槽讀圖都是 `undecided` → 只能 `missing`。
   - `disproof[]`：從該檔 thesis 引用的 claim 反證（Phase 1 #1：AXT 11、COHR 12、Sivers 16 條）與讀圖反證中挑**這份敘事真的依賴的**，`source` 指回原處；沒被引用的不搬（決定 8A）。
   - `answers`：照稽核區實際印出來的東西答；組未定義時 `priced_in` 仍要引用自家歷史那一行。
3. **提 pq2（掛號後接著做下一件，不停）：**
   - `manual`：主題等權組第一版成分（theme＝`config/sector_anchors.json` 現行題材；成員限 Engine C 有快照的上市公司；附每個成員入選理由一句與排除了誰、為什麼；**大公司是否入組要明寫理由**——決定紀錄 §4.2「主題整體漲三倍時一檔兩倍是輸」）。`go` 後由收到 `go` 的 session 以 `python -m alpha theme-cohort --add` 寫入、`pq2_ref` 填該編號。
   - `engine_c_observation`：四檔的 `going_concern_opinion`（讀最近一份年報審計意見，逐字引文＋頁碼；非英語照原文）。`go` 後由收到 `go` 的 session 經人工觀測路徑寫入。
4. **工具毛病＝回頭修 3.3／3.4，記偏差**（比照 Phase 2 偏差 #7–#9）。
5. 收據：`docs/reports/2026-09-2x-phase3-step35-narratives.md`——每份的 `brief_id`、候選狀態與它指的 watch、搬進來的反證與出處、兩類 pq2 編號、首屏前後對照（對 3.0 第 10 項）。
6. **四份的候選狀態沒有預期值**。全部是 `missing` 就照實寫——**不得為了讓候選板非空而放寬任何前提**（硬約束 7）。

## 7. Step 3.6 候選狀態板＋心跳（Z2，R1）

**改哪裡：** `webapp/contracts.py`（新 kind `candidates`）、`webapp/materialize.py`（`--candidates`）、`webapp/api.py`、`webapp/static/app.js`（新頁）、positions 頁（「已持有」連回）、`crons/daily_task.py`（materialize 旗標）、`tests/test_daily_task.py`、`crons/heartbeat.py`（段 2、段 4、較昨 diff 封閉鍵）、`skills/alpha-status/SKILL.md`、`skills/daily-brief/SKILL.md`、`skills/research-drain/SKILL.md`（敘事該重寫的 consumer）＋`python scripts/sync_agent_skills.py`。

**怎麼改：**
1. **狀態推導（顯示端，每天重算，可重建的 derived cache）**：Sheet 持有 → `held`（不論敘事宣告什麼；Sheet 有、敘事沒有 → 「已持有、缺敘事」）；否則取現行 v2 敘事的宣告；`open` 每天重驗三前提，破掉印「可開（前提失效：…）」；`missing`／`priced_wait` 的 watch 已不 active → 印「缺 X（watch 已 <狀態>，該重寫）」；v1 現行 → 「舊版，缺候選狀態」；沒有敘事的 → 不上板（計數另印）。
2. **頁面**：五組（可開／缺 X／已定價等回落／不要／已持有）＋「舊版」「前提失效」兩個附組；**組內按 ticker 字母**；每列印騎的讀圖判讀、三題三個字（§8 第 1 點）、在等的 watch id 與到期、滯留天數（自宣告那筆的 `created_at`）。
3. **心跳**：段 2 以「候選：可開 N｜缺 X N｜等回落 N｜不要 N｜已持有 N｜舊版 N｜前提失效 N；最老滯留 <state> <天>」取代 `_CANDIDATE_BOARD_ABSENCE` 那行；`_PRICED_IN_ABSENCE` 那行換成「三題：已定價 有值 N／缺席 M｜出現在數字裡 有值 N／缺席 M｜會死嗎 四盞有值 N」；段 4 那處同步；較昨 diff 加 `candidate.*` 封閉鍵（每個狀態一個）。**0 也印**；候選板 artifact 讀不到印 `upstream_unavailable`。
4. `webapp status` 列得出 `candidates`。

**怎麼驗：** 推導測試（Sheet 推 held 蓋過宣告、前提失效三種、watch 失效、v1 舊版、無敘事不上板但計數）；心跳封閉鍵相等斷言更新；`test_webapp_request_path.py` 綠（request path 不跑 LLM、不寫 authority）；daily `DAILY_STEPS` 逐項相等測試同 commit 改；headless Edge 實際渲染候選板與 positions 連結（`reference_headless_edge_app_check`）。
**L11-6 ④：** 心跳的較昨 diff——新鍵第一天沒有昨天值，要印「首日」而不是把全部算成變動；拿 3.0 的心跳檔當昨天試跑。
sandbox impact review（daily 旗標）；**05:30 前 push**。

## 8. Step 3.7 個股頁：首屏、稽核區、readiness、面板殘留（Z2，R1）

**改哪裡：** `briefing/analyst_view/contracts.py`（`CORE_PANELS`、`OPTIONAL_PANELS`）、`briefing/analyst_view/compose.py`、`briefing/alpha_view/builder.py`（argument 鏈段、`bet` 純文字、稽核區）、`webapp/static/app.js`、`alpha/providers/graph_neo4j.py::get_bottlenecks` 的呼叫端。

1. **首屏**：短評之後一行候選狀態（顯示端推導的那一個）＋三題三個字：會死嗎＝四盞燈的最差色與灰燈數（「紅」「黃」「綠」「灰 N」，燈不是數字）；已定價嗎／出現在數字裡＝敘事宣告的「是／否／無法量」，v1 或無敘事印「未答」。
2. **稽核區**：三題各行 `{value, source, as_of, 口徑}` 或缺席 kind 的中文；讀圖逐字（沿用讀圖面板）。
3. **readiness**：`CORE_PANELS` → `headline`、`brief`、`argument`、`research`、`readings`、`wipeout`；`fundamental`、`bet` 留選配。**⚠ ROADMAP 已提醒：argument 的「數字」「賭注」段今天讀估值鏈殘留，換之前確認沒有任何一檔的 argument 變空**；變空的逐檔列出並修到有內容或明示缺席。
4. **argument**：「鏈」段不再呼叫 `get_bottlenecks`，改印敘事 `rides[]` 的讀圖（無 v2 敘事時印該公司連到的節點的現行讀圖狀態，沿用 2.7 的 `readings_input_for()`）；`get_bottlenecks` 若因此沒有 production 呼叫端，連同 provider 方法與只守它的測試退役（逐條列去向）；標題改成使用者看得懂的一句（例「為什麼這樣想」，執行者定，寫八欄）。
5. **`review_required` 接回讀圖面板**（Phase 0 偏差 #16）：個股頁 `refresh=review_required` 時，讀圖面板印是哪一份讀圖、為什麼要重讀。
6. **`bet`**：純文字——`our_bet` 格＋`rides[]` 的單位＋`what_must_be_true`；沒有任何價格。

**怎麼驗：** readiness 73 檔前後對照表（每檔 blocked／ready 變化逐檔指得出是哪個面板造成）；核心面板文字 digest 只在預期的面板變（brief 對 v2 四檔、argument 鏈段全體、readings 升核心）；`get_bottlenecks` grep 0 或列出剩下的呼叫端與理由；headless Edge 渲染一檔 v2（AXTI）與一檔無敘事（例 AAOI）。
**L11-6 ④：** readiness 換核心後，本來 `ready_with_flags` 的檔（若有）會不會因 `readings` 缺席變 `blocked`——3.0 記下的清單逐檔看。

## 9. Step 3.8 `record_trade.py` 收據（Z2，R1 ＋ R2-b 常規 opt-in；資本路徑）

**改哪裡：** `scripts/record_trade.py`、測試 `tests/test_record_trade*.py`、`docs/OPERATIONS.md` 成交紀錄段。

**怎麼改（決定 7A）：**
1. alpha／beta 判別沿用 `risk/hard_caps.py` 的 instrument 規則（**不另寫一份**）；Sheet `symbol` → ticker → company_id 走 identity registry，解析不到＝alpha 且 `narrative: unresolved`（不猜）。
2. **alpha 買進**：自動組收據——現行敘事 `brief_id` 與內容 digest、`rides[]` 的 `reading_id` 與讀圖 digest、顯示端推導的候選狀態（含「前提失效」與否）、三題答案與稽核區各行當下的值、在盯的 watch id（該檔所有 active 語意／date watch）、使用者一句理由（`--reason`，必填）。**沒有現行 v2 敘事 → fail closed**（exit code 與硬擋區分），`--override --reason` 放行、收據寫 `narrative: absent`＋override 理由。v1 現行＝當作沒有 v2（收據記 `narrative: legacy_v1`，同樣要 override）。
3. **alpha 賣出**：輕收據——`--reason` 必填；`--disproof-watch <id>`（可選，給了就驗是這檔的 watch）；附當下候選狀態。缺 `--reason` fail closed。
4. **beta**：不需要收據，行為與今天相同。
5. 收據進 `trade_log.jsonl` 那一筆事件內（不另開檔）；**dry-run 也組收據並印出**；硬擋（5%／ETF 槓桿）順序不變、在收據檢查之前。

**怎麼驗：** 測試全用暫存 log 與假 Sheet：alpha 買進有 v2 敘事→收據欄位齊全；無敘事→fail closed、override 後收據記 absent；v1→同無敘事；賣出缺 reason→fail closed；錯誤的 `--disproof-watch`→拒收；beta 不要求收據；硬擋先於收據（超 5% 的 alpha 買進先被硬擋擋下）。真實試跑只做 dry-run（例：`--symbol AXTI --side buy --shares 1 …`，不帶 `--apply`），輸出貼八欄。
**L11-6 ④：** 既有 2 筆 `trade_log` 事件——讀取端（positions、計分表、`scripts/outcome_if_settled_today.py`）遇到沒有收據的舊事件不得報錯或當成缺漏；確認 sha256 不變。

**R2-b（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-b，Phase 3 Step 3.8）
Target: 3.8 的 commit；scripts/record_trade.py 與其測試
Claimed acceptance: alpha 買進缺 v2 敘事 fail closed、override 附理由留收據；賣出缺理由 fail closed；beta 不變；硬擋順序不變；舊事件讀取端不受影響
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑測試；對 AXTI（有 v2）、AAOI（無敘事）、QQQ（beta）各做一次 dry-run 並核對輸出；讀 diff 確認沒有任何路徑在 dry-run 寫 Sheet 或 trade_log；
      確認 alpha 判別只有一份實作；library/trades/trade_log.jsonl sha256 ＝ baseline
Boundaries: 不改 code、不 commit、不帶 --apply、不動 Sheet、不核准 pq2
```

## 10. Step 3.9 `test_full_chain_acceptance` 重寫（Z1，R1）

把 `tests/test_full_chain_acceptance.py` 改成新管線的 full chain：夾具圖 → 讀圖（暫存 ledger）→ v2 敘事（暫存 ledger、disproof 自動登記到暫存 watch 檔）→ 三題稽核區（暫存 Engine C）→ 候選板推導 → 個股頁 compose → 收據 dry-run。
每一段斷言**產出到了下一段手上**（L13），並有一條「中間一段缺席時，下一段印缺席而不是空白」的測試。拿掉的舊斷言逐條列去向。

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ① 有敘事的檔 100% 有候選狀態 | 現行敘事是 v2 的檔數／有現行敘事的檔數（3.5 後預期 4／4；v1 現行 0） | 敘事 |
| ROADMAP ② 缺 X 100% 指向活的 watch | `missing`／`priced_wait` 敘事中 watch 為 active 且有到期的份數／份數 | 敘事 × registry |
| ROADMAP ③ 三題每題對每檔有值或有 `absence_kind` | 73 檔 × 三題（逐行）中「有值或有 kind」的格數／總格數（應 100%）＋依 kind 的分布 | 稽核區（Engine C 觀測的投影） |
| ROADMAP ④ 歸零旗標四盞有值的檔數 | 每盞非灰的檔數：3.0 基準 → 結案（稀釋預期美股上升；GC 取決於 pq2 是否 go，照實寫） | 稽核區 |
| ROADMAP ⑤ 新成交事件 100% 帶收據 | 3.8 之後新增的 alpha 事件中帶收據的筆數／筆數；**0 筆時寫「已交付、未生效」＋測試證明** | 追蹤表（trade_log） |
| A1 v1 不變 | v1 7 行 id 重算 7／7 | 敘事 |
| 反證登記 | 敘事來源的 `semantic_condition` 筆數 0 → N（N＝四份 `disproof[]` 總條數） | registry |
| A2 主題等權組 | ledger 紀錄數（pq2 go 了才 ≥1；否則 0 並印缺席） | 機制存在與否 |
| A5、A6、3.6 | 符號與 kind 存在與否、拒收測試 | 機制存在與否 |

**沒有任何一個是「幾檔通過某個 filter」。「可開」的檔數只印不驗收。**

## 12. Phase 3 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役（逐檔）；**函式層級**以 3.0 名單比對，拿掉的每一個寫去向。
2. `python -m audit invariants` 綠。
3. 無未解釋語意 diff：心跳與 3.0 逐行對照；個股頁核心面板 digest 只在 3.7 預期處變。
4. 無新 dual authority：候選狀態只有一個推導函式（候選板、心跳、個股頁、收據共用）；alpha／beta 判別只有 `hard_caps` 一份；三題取數只在 Engine C、判定只在 `alpha/three_questions.py`／`alpha/wipeout.py`；主題等權組只有一本 ledger。
5. 無 silent drop：候選板沒有敘事的檔計數、v1 舊版計數、前提失效計數；三題每個缺席有 kind；回填報告列出每檔缺什麼。
6. Point-in-time：歷史表的 `filed`／`published_at` 測試；`audit PointInTime` PASS。
7. lifecycle 可達：敘事來源的語意 watch 觸及／到期有 consumer（候選板「該重寫」＋research-drain）；`QueueLiveness` 綠。
8. executable protection：v2 拒收規則、`open` 三前提、`held` 不可宣告、收據 fail closed、三題無門檻斷言，各有會紅的測試；殭屍 grep 九組三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊 Decision Store 三個 `*.db` sha256 與 `live_choices` ＝ 3.0；`trade_log.jsonl` 除了使用者真實成交外不變；`git diff <3.0> HEAD -- AGENTS.md` 為空。

closeout 報告存 `docs/reports/2026-09-2x-phase3-closeout.md`，附「本 Phase 執行中發現、Phase 4 要決定的問題」（§14 種子＋執行中新增）。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 3 結案）
Target: master 最新 commit；docs/reports/…-phase3-baseline.md、…-phase3-step35-narratives.md、…-phase3-closeout.md；
        docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md（§0.4 amendment、§0.6 偏差）
Claimed acceptance: Phase 3 completion gate 九項全過、ROADMAP Phase 3 驗收①–⑤成立（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（3.0 commit 起），抽 5 個拿掉的函式確認去向成立
  2. 敘事 ledger：v1 行 id 重算＝檔內值；每份現行 v2 的 rides[].reading_id 當時是現行、disproof[] 每條在 watch registry 找得到對應 semantic_condition；
     missing／priced_wait 的 watch 現在 active 且有到期；自己造 5 個應拒收的 v2 spec 確認被拒
  3. 三題：73 檔 × 三題逐行「有值或有 kind」＝100%；抽 3 檔對 Engine C 歷史表手算自家百分位；確認沒有任何門檻或已定價布林欄位；
     PIT：任選一檔一個過去日期，確認只用到當時已公開的營收
  4. python -m webapp status 有 candidates；候選板組內按 ticker、無分數；Sheet 持有的檔一律 held；心跳段 2 候選與三題兩行照印（含 0）
  5. 個股頁：CORE_PANELS 含 readings、不含 fundamental；argument 鏈段不呼叫 get_bottlenecks；首屏沒有任何價格報酬
  6. record_trade.py：對 v2 敘事的 alpha、無敘事的 alpha、beta 各 dry-run 一次；trade_log.jsonl 與 baseline 的差只有使用者真實成交
  7. python scripts/retired_mechanism_grep.py：九組三個 0、keep-list 無腐壞；code／skills／tests／config／static 無「籃子」「basket」新命中
  8. library/private/decision_lab/*.db 的 sha256 與 live_choices ＝ baseline；git diff <3.0> HEAD -- AGENTS.md 為空
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger
```

### 結案之後：停，不要開 Phase 4

R2 回 GO 後：ROADMAP Phase 3 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：Phase 4 還沒有 plan。
HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **殭屍 grep B 組掃「籃子」「basket」**（code／skills／tests／config／static）：主題籃子一律「主題等權組」／`theme_cohort`；候選板 kind 叫 `candidates`，**不得**沿用已退役的 `basket` kind（`webapp/contracts.py` 拒收）。C 組掃 `sell_side_target`，E 組掃 `payoff\b`——v2 拿掉它們後 keep-list 要同 commit 縮小，否則「已列但不再命中」會讓驗收紅。
- **短評 id 是 content-addressed**：v2 的新欄位只能加在 v2 的 id 欄位集合；動到 v1 的集合，7 行舊 id 全變。
- **改了語意的格換 key**：`market_view`→`priced_in`、`if_right_if_wrong`→`what_must_be_true`；沿用舊 key 會讓下游分不出這格是估值題還是三題（L12）。
- **回填的日期**：財報數字的可用日是 `filed`（EDGAR）或公布日，不是會計期末、更不是抓取日（INV-6、L11-5）；百分位序列每一點只能用當時已知的營收與淨負債。
- **同口徑**：股數序列只收一個來源（EDGAR 封面股數）；與 yfinance `shares_outstanding` 混用就是 `wipeout.py` 檔頭記過的 `inputs_incompatible`。
- **EV 需要同期淨負債**：拿不到就 P/S，口徑欄照寫；不得用今天的淨負債套到過去。
- **非美股的歷史**：不硬湊；缺席 kind 照實印。「29 檔非美股的已定價①大多缺席」是現況，不是 bug——驗收③要的是「有值或有 kind」。
- **「已持有」只從 Sheet 推導**：Sheet 讀不到時印 `upstream_unavailable`，不得退回敘事宣告。
- **收據的 alpha 判別**只能呼叫 `risk/hard_caps.py` 那一份；Sheet symbol 與 ticker 不一定同形（`SIVE.ST`），走 identity registry。
- **readiness 換核心會讓 blocked 數變**：那是預期，逐檔指得出是哪個面板；不得為了讓 ready 變多而把 `readings` 留選配。
- **daily 的 `DAILY_STEPS` 有逐項相等測試**：3.6 改 materialize 旗標要同 commit 改測試並在 05:30 前 push；3.2 的回填不得與 daily 同時跑。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad／`%TEMP%`；程式碼不要放 heredoc，用 Write 成檔再跑；子行程用 `sys.executable`。
- **Neo4j 要開**：`query.structure`、讀圖選取、走圖、整合測試都需要；讀不到圖時印 `upstream_unavailable`，不印 0。
- **可開為零就零**：3.5 四份全是 `missing` 是完全合法的結果；看到候選板「可開 0」時要做的是研究（讀圖、答三題），不是改前提。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. Phase 2 closeout §5 未併入本 Phase 的：#2（3 則排回 lead 補分類——研究）、#4（稽核依賴 Neo4j，本 Phase 維持）、#6（聯合公告偵測 `display_name`，先量）、#7（`supplies_to → prod:` 兩義，Phase 4）、#10（走圖母體 <10 型別）、#11（Phase 1 §7 殘題）、#13（apply 入口旁支、`_finalize…` 無呼叫端、`verify_test_nonvacuity.py` 失效突變）、#14（`wake_reading` 以節點為單位）、#15（「客戶高管在供應商新聞稿具名」算不算客戶端印證——**要使用者決定**）、#16（兩條叫不醒的語意 watch）、#17（`classify_evidence` 屬性引文算邊印證、`prod:` 一表多義、SuperNova 原文未定日、OpenLight 兩個 ID）。
2. **「剛轉型」由誰宣告**（§4.1 已定價①）：本 Phase 由敘事宣告；若敘事沒寫而歷史其實不可比，百分位會照算——要不要讓讀圖或 thesis 也能宣告。
3. **主題等權組 pq2 若結案時仍未 go**：已定價②③全體缺席；照實寫，Phase 5 前要有人定。
4. **Phase 5 的量測從 trade_log 收據重建**：本 Phase 的收據欄位是否足夠（候選狀態、三題答案、讀圖 digest 都在），由 Phase 5 plan 驗。
5. `{assumption:driver[scope]}` 回填（Phase 1 #4、Phase 0 延下來）：v2 仍保留這個 placeholder；它的值來源在估值鏈退役後還在不在，3.4 查、照實列。
