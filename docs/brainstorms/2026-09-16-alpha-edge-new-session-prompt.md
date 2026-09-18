# 給新 session 的啟動 prompt（2026-09-18 晚第五輪改寫；前四輪逐字狀態見文末歷程與 git history）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。
>
> ⚠ **日期會被寫超前。** 2026-09-17 那輪的收尾塊自稱「09-18」，害下一個 session 以為心跳已經
> 自動跑過一次。**開工第一件事就是 `date`**，不要相信任何檔案裡的「今天」。

---

## 開工指令（貼這一段）

> ## 現在的狀態（2026-09-18 晚，第五輪收尾）
>
> **開工三件事（每次都跑，不要憑記憶）：**
> ```
> date                                                     # 檔案裡的「今天」不可信
> python scripts/writer_guard.py check                     # writer_lock 應為 null、daily_done_today
> schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V      # Last Run / Last Result / Next Run
> ```
>
> ### ⚠ 常設授權：沒有需要我核准的事情就繼續做，不要停下來問
>
> 使用者原話（2026-09-17／09-18 兩次確認）：「**我想要的是沒有需要我核准的事情就繼續**」。
> **停的理由必須是「有東西要使用者決定」，不是「到了某個邊界」**——Phase 做完不是停止理由、
> Z2 本身不是停止理由、「想說一聲」更不是。撞到 pq2 就掛號、**接著做下一件不需核准的事**，
> 收尾一次給批次指令，**不得停在編號上等**。
>
> **仍要停下等人（不因此放寬）：** 四個人工 gate（graph admission／Engine C 判讀寫入／
> thesis mutation／live）、資本或任何 append-only authority、要改 `AGENTS.md` 判準句或
> ROADMAP 的 Phase／Step 定義（後者先給五欄 amendment）、需要 R2、Verdict 不是 `GO`、
> 或 plan 裡真有要使用者選的問題。
>
> ⚠ **還有一種必須停**：你要做的事與**既有的書面決定相反**時，先把那句話與你的反證擺給使用者看。
> 2026-09-18 實測代價：[610] 的 packet 建議合併 `tech:inp_eml`，卻沒提 `config/entity_aliases.json`
> 早就寫著「不併」——使用者是在資訊不完整的情況下核准的。**後來證明該合併，但那不是重點。**
>
> **收尾時**：更新本檔（`docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`），
> **下一份 prompt 必須原樣帶著上面這整個「常設授權」小節**——它是每一輪都要傳下去的東西。
>
> ### Phase 狀態
>
> **Phase 1 ▶（研究已做、證據不足以進榜）｜Phase 2 ▶（等時間）｜Phase 3 ✅｜
> Phase 4 ▶（成因①②已交付，剩③`no_demand_edge` 57／④`upstream_dead_end` 6）｜
> Phase 5 ▶（D15／D2 對稱 overlay／歸零旗標／alpha 全歸零／D3 已交付，剩第四盞燈與「賭注 V4」）｜
> Phase 6 ✅｜Phase 7 ○。**
> **另加一條跨 Phase 的新主線：L18 三層**（V1 ✅ 逐字入圖｜V2 ◐ 只做了 `query.structure --quotes`｜
> V3 ○ 重複節點偵測器｜V4 ○ bet 輸入契約）。
>
> **⚠ Phase 2 的「連續 3 天心跳」：第 1 天 ✅ 2026-09-18 07:00:01 `Last Result 0`。
> 第 2 天＝09-19、第 3 天＝09-20。** 那是等時間不是等工作；3 天湊滿之前不標完成。
>
> ### 本輪（2026-09-18 一整天）做完的
>
> | | 交付 | before → after |
> |---|---|---|
> | **Phase 4 成因分開** | 封閉字彙 `ANCHOR_GAP_CAUSES` ＋ `classify_anchor_gaps()` | 「瓶頸節點走不到錨」**先前沒有任何地方數過** → 87／159 並拆成因 |
> | **`graph_context` 截斷說話** | 六段全改走 `_fetch()`（第一趟原查詢取列、第二趟拿掉 LIMIT 只數總數） | **六段裡五段先前沉默** → 全印 `N／M`；資料列逐行相同 |
> | **L18 寫進 `AGENTS.md`** | 抽取之後逐字退出系統 → 每個下游只能相信 label | `grep -c "^### L"` 17 → **18** |
> | **V1 逐字入圖** | `loader` 新增 `MERGE_SOURCE` ＋ `[:QUOTES]`；`scripts/backfill_source_quotes.py` 回填 | 圖裡逐字 **0 → 1,057 段**；`source_ids` 命中 **0% → ~100%**；既有輸出**八項逐位不變** |
> | **V2 `--quotes`** | `query.structure` 每條邊印得出它自己的逐字 | 該工具先前**一個字都不是文件實際寫的** |
> | **`is_component_of` 盲區** | 它在 dst 側的五角度裡 **68／68 條看不見** | 全部看得見；`tech:cpo` 下一層 **4 → 21** |
> | **[606][607] 研究執行** | 82 條 `enables` 逐條對來源逐字重判（覆蓋 82/82） | 判決 keep 47／改型別 17／翻向 10／退回研究 8／刪 2 |
> | **[608][609][610] 入圖＋程式歸位** | migration 改 22 份抽取檔、29 改判＋4 移除、刪 30 條孤兒邊；`enables` 移出 `UPSTREAM_RELATIONS` | **走不到錨 87 → 63（−28%）**；`enables_direction_unresolved` **17 → 0**；**accepted 37 列逐位不變** |
>
> ### ⚠ 本輪最該記住的五件
>
> **① 今天所有發現，都是繞過自己的工具、直接 `grep extractions/` 找到的。**
> `loader` 有六個 `MERGE_*` 卻獨缺 sources，**1,105 段逐字在載入那一刻被丟掉**。
> 迴圈是封閉的：抽取時 LLM 給 label → 程式照 label 做 → 測試驗「程式有沒有照 label 做」→ 回到 label。
> **判準：深挖若需要繞過自己的工具，它就不會例行發生**（L18）。V1／V2 是這條的解法，**V3／V4 還沒做**。
>
> **② base rate 是 35%。** 只重判了一個 relation（82 條）就有 29 條要改、8 條逐字根本不支持任何關係。
> **沒有理由相信別的 relation 更乾淨**——`is_component_of` 上已找到同型錯誤（isolator 那條）。
>
> **③ 順序不可換，這是實測不是推論。** 資料寫反的那批與程式寫反的那邊**互相抵銷**了。
> 只改程式不改資料，`no_demand_edge` 會由 51 打到 **67**（更糟）；兩邊都修才是 87 → 63。
>
> **④ 已修好的成因要退場，不要留恆為 0 的格子。** 今天退場兩個（`constrained_by`、`enables` 方向），
> 各留一條**方向測試**守迴歸。同理 `loader/validate.py` 的例外清單已歸零——**從今天起沒有豁免**。
>
> **⑤ 兩次被自己的驗收測試抓到，兩次都值得。** ①`graph_context` 首版把 `LIMIT` 從 Cypher 拿掉改在
> Python 端截，看似等價——實測 Neo4j 的 Top-N tie-break 不同，`co:axt` 的 20 條 claim **換了一批**；
> ②V1 首版只接了邊斷言與 claim、**漏了節點**。**「只多一行字、不動任何一列」這種宣稱必須可否證。**
>
> ### 待使用者決定：目前沒有
>
> ### 不需核准就能接著做的（依序建議）
>
> **① V3 重複節點偵測器**（L18 的 L2 層）——現在跑就有 **37 對候選、31 對同 `abstraction_level`、
> 涉及 43／297 節點（14.5%）**，一個 30 行純字串比對。**只提名不合併**（合併仍逐筆 `ra_admission`）。
> 它的用途是**讓系統自己生出「這裡看起來不對」的問句**——今天真正觸發深挖的是使用者問了一句。
> **② 重讀兩份 stale 的結構讀圖**（`mat:inp_substrate`／`tech:cw_dfb_laser`）——走訪方向改了，
> 它們的判讀基礎變了。研究，只在互動 session（D12）。查證：心跳第 2 段、`python -m alpha structure-reading <node> --check`。
> **③ 替 AXTI 寫 `downside` 情境假設**——它有 15 筆 OperatingAssumption，`scenario` 全是
> `base`／`variant`，**`downside` 0 筆**，所以「判斷錯了值多少」那條對稱橋在唯一走得最深的那檔上也是空的。
> **④ ROADMAP backlog 剩下的**：409 條 disproof 沒人比對（**Z2 有岔路，見下**）、心跳報昨天（維持營運）、
> 歸零旗標第四盞（Z2 動 Engine C 字彙）、`review_conditions` 對照不到期中實績（Z2 動封閉字彙）。
>
> ⚠ **409-disproof 那條的岔路已經量完、寫在 ROADMAP 裡**：零 LLM 訊號鑑別力 174/323＝53.9%，
> 但它**抓到促成它的案例是因為錯的理由**，而且**沒有「清除」機制就是牆不是閘門**。
> 真正要建的是一份 claim review ledger，不是偵測器——**那一步有使用者要選的問題，到那裡停。**
>
> ⚠⚠ **binding constraint 連續八輪沒動過：籃子 16 檔 `bet` 2／`abstained` 0／`unanswered` 14。**
> 今天一整天做的全部是**讓圖說實話**——那是前提，**不是進展**。能讓籃子非空的只有兩條路，
> 兩條都要人：①替某一檔寫下帶 disproof 的賭注；②寫一筆 `bet/variant.overlay` 的 Abstention。
> **兩者都是答案，只有空白不是。** 不要讓交付看起來像進展。

---

## 先讀（順序固定）

| # | 檔案 | 為什麼需要它 |
|---|---|---|
| 1 | `AGENTS.md` | 憲法、六條 invariant、四個人工 gate、**L1–L18**（一字不動）。⚠ 尤其「Alpha 呈現契約」、L7（disproof 要附核查頻率＋48h 動作）、**L18（逐字必須指得回原始證據）** |
| 2 | [`docs/ROADMAP.md`](../ROADMAP.md) | **進度與驗收的唯一權威**。Phase 表、completion gate 八項、backlog |
| 3 | [`2026-09-18-verbatim-never-reaches-the-decision.md`](2026-09-18-verbatim-never-reaches-the-decision.md) | **L18 的完整 zoom-out**：四個實測、為什麼 prompt 層修不動、L1/L2/L3 與 V1–V4 |
| 4 | [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | **決定紀錄 D0–D15**（使用者原話） |
| 5 | [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | 籃子為什麼空的量測、A／B 兩種賭注 |
| 6 | `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md` | Zoom／Review 判定與八欄交付格式 |

**只在需要時才讀：** `docs/OPERATIONS.md`、`docs/ARCHITECTURE.md` §4.1／§8、各 Phase 的 plan 檔。
⚠ **本輪不必讀的**：其餘 2026-07～08 的舊 brainstorm 與 Alpha Edge 無關。

---

## 現況與查證命令（引用前先跑）

| 現況（2026-09-18 22:09 實測） | 查證命令 |
|---|---|
| 可投資排序 **37 列**；filter `input 221／accepted 37／filtered 184`；理由 `unfilled 155／below_threshold 29` | `python -m query.bottleneck --top-n 60` |
| **瓶頸節點走不到需求錨 63／158**：`no_demand_edge` **57**（co 16／mat 2／prod 4／tech 35）、`upstream_dead_end` **6** | 同上，看「瓶頸節點走不到需求錨」段 |
| canonical 邊 **526**、materialized 屬性 **360**、`substitutability` 覆蓋 **86／526** | `python -m loader.edge_resolution project --dry-run` |
| **圖裡逐字 `Source` 1,058 個（帶 quote 1,057）、`QUOTES` 邊 2,959**；Entity 697、Claim 409 | `MATCH (s:Source) RETURN count(s)`；或 `python -m query.structure <node> --quotes` |
| `audit invariants` FAIL 0／PASS 13（**4,192 筆**） | `python -m audit invariants` |
| 全套 pytest **2,674 passed／1 skipped** | `python -m pytest -q`（約 8 分鐘） |
| 待辦池未結案 **35**；**pq2 球在你手上 18**；pq1 可做 **11**；**結構讀圖待重讀 2**；未 triage 0 | `python -m engine_b.todo list`／`python crons/heartbeat.py` |
| 籃子 16 檔：`bet` **2**｜`abstained` **0**｜`unanswered` **14**；量的候選 15 家通過 **0** | 讀 `library/private/app/state/basket.json` 的 `bet_ledger` |
| 歸零旗標 16 檔 × 4 盞：紅 2（COHR、IQE.L）｜黃 8｜綠 20｜**灰 34**（灰不是綠） | 心跳第 4 段；或讀同檔 `wipeout_ledger` |
| 追蹤表 22 檔｜量測起始 2026-07-21｜**籃子總報酬 +3.17%**｜最大單檔 **AXTI 等權貢獻 +2.70%**／其餘 21 檔 +0.47%｜**還沒有一檔滿 12 個月**（最長 59 天） | `python scripts/outcome_if_settled_today.py` |
| `downside` 假設 **0 筆**（含 AXTI） | `python -m alpha assumptions AXTI --list`（看 `〔downside〕`） |
| 心跳排程 Last Run **2026-09-18 07:00:01**／Result **0**／Next **09-19 07:00** | `schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V` |

---

## 不得做

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、**因籃子空而放寬篩選條件**、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯（要改先量「幾列真的變了」）、
**跑 `scripts/backup_private.py run`**（Drive token 存在，那會上傳＝對外動作；要備份用
`export_neo4j_payload()` 做純本機匯出）。

## 收尾格式

決策／收據區塊（若有要使用者決定的事，放**最前面**）→ HUMAN SUMMARY（5–10 行）→ 八欄 `STEP_RESULT`
→ **最後一行給可直接複製的批次指令**。格式見 `skills/development-flow/SKILL.md` Step 4.5／5。
Push 是常規動作；push 前 sanity check：`git ls-files library/private` 應為空。

---

## 歷程（每輪壓成一行；逐字收尾狀態在 git history）

| 輪次 | 做完的 | commit 範圍 |
|---|---|---|
| 2026-09-16 | Step 0（呈現契約重寫）＋ Phase 1 計畫核准 | `d06f5bf` 前後 |
| 2026-09-17 早 | Phase 1 Step 1.0／1.1／1.2 | …`fbc1b4f` |
| 2026-09-17 晚 | Step 1.3｜Phase 2 心跳＋排程｜Q1／Q2／Q4／Q5（結構讀圖、籃子賭注契約） | `fbc1b4f`…`e6f07d0` |
| 2026-09-17 深夜 | Phase 3（D5 計分表）｜AXTI InP 賭注｜Phase 6 前兩項｜[602] 入圖 | `8eee2e1`…`65eec17` |
| 2026-09-18 早 | Phase 3／6 標 ✅｜[603] 入圖｜Phase 2 第 1 天 | `19af823`…`c1e4638` |
| 2026-09-18 白天 | Phase 4 ①`constrained_by`｜Phase 5 D15 三量｜D2 對稱 overlay｜歸零旗標｜`demand_anchor` 讀法＋[606] | `2140eca`…`47862a3` |
| 2026-09-18 下午 | Phase 4 成因分開｜`enables` 防呆＋[607]｜`graph_context` 截斷說話 | `ec47822`…`9032aff` |
| **2026-09-18 晚** | **L18 zoom-out＋沉澱｜V1 逐字入圖｜V2 `--quotes`｜`is_component_of` 盲區｜[606][607] 執行｜[608][609][610] migration＋`enables` 程式歸位** | `7e6a3bd`…`53b059f` |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項。**

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**。**不得為了讓籃子非空而放寬門檻 4。**
