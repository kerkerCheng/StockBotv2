# 給新 session 的啟動 prompt（2026-09-18 深夜第六輪改寫；前五輪逐字狀態見文末歷程與 git history）

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

> ## 現在的狀態（2026-09-18 深夜，第六輪收尾）
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
> **跨 Phase 主線 L18 三層：V1 ✅ 逐字入圖｜V2 ✅ `query.structure --quotes`｜V3 ✅ 重複節點偵測器｜V4 ○ bet 輸入契約。**
>
> **⚠ Phase 2 的「連續 3 天心跳」：第 1 天 ✅ 2026-09-18 07:00:01 `Last Result 0`。
> 第 2 天＝09-19、第 3 天＝09-20。** 那是等時間不是等工作；3 天湊滿之前不標完成。
>
> ### 本輪（2026-09-18 深夜）做完的
>
> | | 交付 | before → after |
> |---|---|---|
> | **V3 重複節點偵測器** | `query/duplicate_nodes.py`：兩條純字串比對規則，每一對**帶兩端各自的逐字** | 「圖裡有沒有兩個節點在講同一件事」**先前沒有任何工具答得出來** → 34 對候選、逐字並排可讀 |
> | **接進三個既有落點** | CLI／APP coverage 頁（artifact `duplicates` 鍵，schema `coverage/1`→`/2`）／`queue_segments` 新段 `duplicate_node_candidates` | 候選從 **0 個地方可見 → 3 個**；`webapp status` 也印 |
> | **consumer 真的存在** | `skills/research-drain/SKILL.md` 第 4 段改寫：**先問「它是不是旁邊那個」，再問「誰供應它」** | 段的 consumer 欄不再是空話（守門測試會驗 skill 真的提到它） |
> | **修掉 V1 留下的回歸** | `coverage_gaps` 的 `degree` 把證據邊也算成結構邊 | 188 個節點 degree 虛增；`tech:scale_out_network` 的 `isolated` 標記**回來了** |
> | **🔴 證據欄從未被賦值** | `query.structure` 的「證據」欄是 dataclass 預設值，全圖都印「供應商自報」 | **526 條裡 430 條（81.7%）印錯** → 真實分布外部印證 217（41.3%）／待判定 108／自報·filing 105／自報 96 |
> | **兩份 stale 結構讀圖重讀** | `mat:inp_substrate`（第 5 筆）、`tech:cw_dfb_laser`（第 2 筆），兩份都**維持 volume** | 佇列段「結構讀圖待重讀」**2 → 0** |
> | **[611][612] 核准後執行完畢** | 三個出口管制節點併成一個｜一條 `is_component_of` 翻轉方向 | 候選 **34 → 32**、沒人提過 **30 → 28**——**清單第一次真的變短**（L14-4「會滅」那一條的答案） |
> | **ROADMAP 回填** | V1／V2 的交付紀錄**先前根本沒寫進 ROADMAP**（該行還寫著「停在這裡等人」） | 三個 V 的交付、量測與兩次被推翻都落在唯一權威上 |
>
> ### ⚠ 本輪最該記住的六件
>
> **① 「這會讓哪個數字變」這次答得出來，而且是實測：4 個 🔴 真缺口裡有 2 個同時是重複節點候選的一端**
> （`tech:scale_up_cpo` ↔ `tech:cpo`、`tech:scale_across_components` ↔ `tech:scale_across`），
> 🟡 建模待補 14 個裡另有 2 個。**這不代表那 2 個 🔴 是假的**——它代表派研究去挖之前先有一個可機械生成的問句。
>
> **② 第三條規則被真實資料當場推翻（第三次了，形狀同 D15 與稀釋那盞）。** 想抓
> `dram_manufacturing`／`dram_production` 那型而寫的「同 token 數、只差一個 token」，一跑就讓**所有單 token id
> 互相全配**（`prod:reliant` 配上 `mat:photoresist`）。改法是**明說自己抓不到那一型**，不是用會誤報的規則假裝抓得到。
>
> **③ 首版用裸的 `in` 判 registry note，被本模組自己的測試抓到**——`tech:nand` 是 `tech:nand_flash` 的子字串。
> 兩輪之內第三次「首版被自己的驗收測試抓到」。**這是好事，不是浪費**：沒有那條測試它會安靜地錯。
>
> **④ `mentioned` 刻意不叫「已決定不併」。** registry 的 note 是自由文字，「刻意不併」與「留待研究判斷」
> （兩者今天都真實存在）長得一模一樣——機械讀得出「有沒有提到這兩個 id」，讀不出它說了什麼。所以只端 note 逐字給人讀。
>
> **⑤ 結構讀圖的「證據」欄過去一直在說謊，而且它藏在一句自己寫對了的註解底下。** `_load_edges()` 的註解逐字寫著
> 「共用 `collapse_assertions`，不自己收斂——否則結構讀圖與排序會對同一條邊給出不同的值」。**那件事正在發生，
> 只是發生在它沒想到的那一欄**：收斂共用了，賦值沒有。後果不是欄位難看——判 A（護城河）還是 B（量）的人看到的是
> 「所有證據都是供應商自報」，而 41.3% 其實是外部印證。修完立刻兌現：`tech:cw_dfb_laser` 那份讀圖的
> **「明顯高於其他」的 sub=5 是自報，最低的 sub=2 反而有外部印證**——L8 的形狀，扣掉自報高點才看得出它是 volume。
>
> **⑥ V1／V2 第一次在例行工作中兌現。** [612] 那條方向相反的邊，是重讀時用 `--quotes` 自己撞到的；
> 上一輪的同型錯（[610]）是繞過工具 `grep extractions/` 找到的。**差別就是 L18-4 那句話。**
> ⚠ 但也量到 **V2 只做了一半**：`--quotes` 印得出「這條邊的逐字」，印不出「這一格的逐字」——要回答
> 「`sub=3` 憑什麼」仍必須繞過工具直接查 EdgeAssertion（已進 ROADMAP）。
>
> ### 待使用者決定：目前沒有
>
> **[611][612] 已於 2026-09-18 核准並執行完畢**（V3 交付當天就走完第一趟全程：提名 → packet → 核准 → 入圖 → 清單變短）。
> 候選 **34 → 32 對**、「沒人提過」**30 → 28**、節點 191 → 189；兩次入圖後排序都逐位不變。
>
> ### 不需核准就能接著做的（依序建議）
>
> **① 讀那 28 對「沒人提過」的候選**（`python -m query.duplicate_nodes`）——逐字已經並排印好，
> 判「是同一個」就打包 pq2 `ra_admission`；判「不是」目前**沒有地方寫**（見下面那條 backlog）。
> 先挑與 coverage 🔴／🟡 重疊的那 4 個，因為它們同時解掉一個誤報。
> **② 替 AXTI 寫 `downside` 情境假設**——它有 15 筆 OperatingAssumption，`scenario` 全是
> `base`／`variant`，**`downside` 0 筆**，所以「判斷錯了值多少」那條對稱橋在唯一走得最深的那檔上也是空的。
> **③ 把 `is_component_of` 整個 relation 逐條對逐字重判**——[610] 與 [612] 是**同一份抽取檔、同一段逐字**
> （`coherent_ofc_march25.json` 的 e23 與 e22 共用 source `s13`）的兩個實例，
> 而 `enables` 重判的 base rate 是 35%。**沒有理由相信這個 relation 更乾淨。**
> ⚠ 已知還有第三件在同一段逐字上：e23（[610] 已翻正方向）的逐字《We also, I think you make -- design and
> manufacture a significant fraction of the world's isolator》**只說 Coherent 做 isolator，沒說它是 ELS 的元件**
> ——方向修對了，關係本身仍沒有逐字支撐。
> **④ 驗一件可能已經過期的事（30 秒）**：pq2 [571]–[575] 五個 Abstention 提案鑄於 **2026-09-13**，
> 而**同一天**的政策改動說「虧損檔寫一筆 `ev_to_sales` 估值假設就走完，**不需要 pq2**」。
> 已查 ground truth：XFAB.PA 的 `ev_to_sales`（`va_7dbc97f4`）**已寫**、Abstention ledger **0 筆**。
> 若五檔皆如此，它們是**被政策取消的類別**，該 drop 而不是執行。⚠ 但 `closure-gate` 仍把 XFAB.PA 列為
> 「forward EPS 共識非正」卡住——**兩件事要對起來才能下結論**，本輪沒做完。
> **⑤ ROADMAP backlog 剩下的**：409 條 disproof 沒人比對（**Z2 有岔路**）、Phase 4 的成因③④、
> 心跳報昨天（維持營運）、歸零旗標第四盞（Z2 動 Engine C 字彙）、`review_conditions` 對照不到期中實績（Z2 動封閉字彙）。
>
> ⚠ **三條新的 backlog 都有「使用者要選的問題」，所以都停在提案階段**：
> ⓪**V2 只做了一半**：`--quotes` 印得出「這條邊的逐字」，印不出「這一格的逐字」。要選的是
> 「只印有填屬性的那幾筆」還是「加一個 `--why <屬性>` 旗標」。
> ①**「刻意不併」沒有結構化登記處**——`entity_aliases.json` 只有 `canonical`（＝「這兩個是同一個」），
> 「不是同一個」沒地方寫，所以候選清單只會因為真的合併而變短。要選的是：不併算不算研究判斷？
> 算 → 每否決一對都要鑄一個 pq2 號；不算 → 就是一個沒有 receipt 的宣告，而 registry 明寫那不是 canonical identity。
> ②**409-disproof**：零 LLM 訊號鑑別力 174/323＝53.9%，但它抓到促成它的案例是**因為錯的理由**，
> 而且沒有「清除」機制就是牆不是閘門。要建的是 claim review ledger，不是偵測器。
>
> ⚠⚠ **binding constraint 連續九輪沒動過：籃子 16 檔 `bet` 2／`abstained` 0／`unanswered` 14。**
> V1／V2／V3 做的全部是**讓圖說實話**——那是前提，**不是進展**。能讓籃子非空的只有兩條路，兩條都要人：
> ①替某一檔寫下帶 disproof 的賭注；②寫一筆 `bet/variant.overlay` 的 Abstention。
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

| 現況（2026-09-18 深夜實測） | 查證命令 |
|---|---|
| 可投資排序 **37 列**；filter `input 221／accepted 37／filtered 184`；理由 `unfilled 155／below_threshold 29` | `python -m query.bottleneck --top-n 60` |
| **瓶頸節點走不到需求錨 63／158**：`no_demand_edge` **57**、`upstream_dead_end` **6** | 同上，看「瓶頸節點走不到需求錨」段 |
| **重複節點候選 32 對**｜同層 25｜涉及節點 46／189｜registry 提過 4｜**沒人提過 28** | `python -m query.duplicate_nodes` |
| 覆蓋掃描 **🔴 真缺口 4／🟡 建模待補 14**；**🔴 有 2 個同時是重複節點候選的一端** | `python -m webapp materialize --coverage` ＋ `python -m webapp status` |
| canonical 邊 **526**、materialized 屬性 **360**、`substitutability` 覆蓋 **86／526** | `python -m loader.edge_resolution project --dry-run` |
| **圖裡逐字 `Source` 1,058 個（帶 quote 1,057）、`QUOTES` 邊 2,959**；Entity 697、Claim 409 | `python -m query.structure <node> --quotes` |
| **證據等級真實分布**：外部印證 **217（41.3%）**／待判定 108／自報·filing 105／供應商自報 96（共 526 條） | `python -m query.structure mat:inp_substrate` 看「證據」欄 |
| `audit invariants` FAIL 0／PASS 13（**4,193 筆**；筆數隨資料浮動，**驗收條件是 FAIL 0 不是筆數**） | `python -m audit invariants` |
| 全套 pytest **2,687 passed／1 skipped**（本輪 +13：V3 十一條、coverage degree 一條、證據欄一條） | `python -m pytest -q`（約 8 分鐘） |
| 待辦池未結案 **35**；**pq2 球在你手上 18**；**結構讀圖待重讀 0**（本輪三份讀圖都寫了）；未 triage 0 | `python -m engine_b.todo list`／`python crons/heartbeat.py` |
| 籃子 16 檔：`bet` **2**｜`abstained` **0**｜`unanswered` **14** | 讀 `library/private/app/state/basket.json` 的 `bet_ledger` |
| 歸零旗標 16 檔 × 4 盞：紅 2（COHR、IQE.L）｜黃 8｜綠 20｜**灰 34**（灰不是綠） | 心跳第 4 段；或讀同檔 `wipeout_ledger` |
| 追蹤表 22 檔｜量測起始 2026-07-21｜**還沒有一檔滿 12 個月**（最長 59 天） | `python scripts/outcome_if_settled_today.py` |
| `downside` 假設 **0 筆**（含 AXTI） | `python -m alpha assumptions AXTI --list`（看 `〔downside〕`） |
| 心跳排程 Last Run **2026-09-18 07:00:01**／Result **0**／Next **09-19 07:00** | `schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V` |

⚠ **pytest 要用 `.venv\Scripts\python.exe`**，裸的 `python` 沒有 pytest（2026-09-18 踩到）。

---

## 不得做

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、**因籃子空而放寬篩選條件**、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯（要改先量「幾列真的變了」）、
**跑 `scripts/backup_private.py run`**（Drive token 存在，那會上傳＝對外動作；要備份用
`export_neo4j_payload()` 做純本機匯出）。
**⚠ 不得自行合併重複節點**——`query.duplicate_nodes` 只提名，合併是 graph admission（pq2 `ra_admission`）。

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
| 2026-09-18 晚 | L18 zoom-out＋沉澱｜V1 逐字入圖｜V2 `--quotes`｜`is_component_of` 盲區｜[606][607] 執行｜[608][609][610] migration | `7e6a3bd`…`53b059f` |
| **2026-09-18 深夜** | **V3 重複節點偵測器（CLI＋APP＋佇列段＋research-drain consumer）｜coverage degree 回歸｜證據欄從未被賦值（430/526）｜三份結構讀圖（待重讀 2→0）｜[611][612] 鑄號→核准→入圖（候選 34→32、沒人提過 30→28）｜ROADMAP 回填 V1／V2／V3＋三條新 backlog** | `39a2ff0`… |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項，也不要重做 V1／V2／V3。**

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**。**不得為了讓籃子非空而放寬門檻 4。**
