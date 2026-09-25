---
date: 2026-09-25
topic: phase2-reading-units-graph-walk
status: active
derived_from: docs/ROADMAP.md（Phase 2，含本 plan §0.4 的 amendment A1–A6）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G2、G5、G7、G8）、docs/reports/2026-09-25-phase1-closeout.md §7、docs/brainstorms/2026-09-17-structural-reading-layer.md、docs/brainstorms/2026-09-18-verbatim-never-reaches-the-decision.md
plan_review: 未做 P0（使用者 2026-09-25 選 8A：執行期間 R2 常規 opt-in，plan 本身不先審）
---

# Phase 2 讀圖兩種單位 ＋ 走圖（給執行模型的完整 plan）

> **執行者：便宜模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。唯一例外是 Step 2.5（強模型、互動 session、研究不是開發，見該節）。**
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 2」（含本 plan §0.4 的 amendment A1–A6）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → ROADMAP「Phase 2」「旁支開發項：Graph MCP 退役」「硬約束」→ 本 plan §0.1–§0.4 →
> [`2026-09-17-structural-reading-layer.md`](../brainstorms/2026-09-17-structural-reading-layer.md)（讀圖 ledger 與 staleness 的設計來源）→
> [`2026-09-18-verbatim-never-reaches-the-decision.md`](../brainstorms/2026-09-18-verbatim-never-reaches-the-decision.md)（L18：讀圖必須消費逐字）→
> `docs/refactor/historical-failure-matrix.md` §2 六條 invariant → `docs/OPERATIONS.md`「sandbox impact review 五步」。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**讀圖 ledger 的紀錄與引用、走圖問句在圖上的命中／母體、
> APP 的 state kind、機制存在與否**（見 §11），不是研究結果。

**一句話目標：** 讀圖要能宣告「我讀的是一層，還是某個客戶產品裡的一格」，而且判讀憑的每一半都指得回圖上的原文；
另外有一支零 LLM、零分數的程式每天從圖上報出「該去研究的洞」。**這兩件事都不排序、不給分、不 gate 任何東西。**
它們服務的目標是 `AGENTS.md` 那一句：**邊緣小公司的 power-law 倍率——某個集中需求把量灌進一層薄的供應商。**
所以走圖問句的第一型就是「硬需求下的薄層，還沒有人讀」（§7）。

---

## 0.1 使用者定案（2026-09-25 互動 session；本 plan 的判斷全部來自這張表）

| # | 題目 | 定案 |
|---|---|---|
| 1 | 讀圖「單位」放哪 | **A**：新增欄位 `unit`（`layer` 層／`socket` 插槽）；判讀結論字彙 `READING_KINDS`（moat／volume／neither／undecided）**不動**；v1／v2 舊紀錄一律解析成 `layer`。ROADMAP 原寫「`READING_KINDS` 加 `socket`」改寫（amendment A1） |
| 2 | 讀圖的逐字義務（含 Phase 1 待決 #19） | **A**：護城河／量必須引用圖上原文，寫入時由程式核對，對不上就拒收；每條反證加「出處」欄（amendment A2；細化見 R-1） |
| 3 | 反向路徑成員（Phase 0 延下來的 `counter_path_relation`） | **A**：反向路徑只收「互相競爭」（`competes_with`），`constrained_by` 移出（它本來就同時算在需求側／下一層）；`schema/vocab.json` 的 `counter_path_relation` 成為讀圖工具的唯一來源（amendment A3） |
| 4 | 研究佇列排序（G2） | **A**：拿掉 pq1「公司坐在難替代邊上就往前排」一軸；同級改按 lead 時間（舊的先）；triage 對 lead 本身的分類保留；走圖的洞另成一段、不跟 lead 混排（amendment A4；細化見 R-2） |
| 5 | 走圖問句清單 | **A**：ROADMAP 五型照做但「走不到錨」收窄到「有往下供貨的公司」；保留 coverage 頁原有的「沒人供應」「建模待補」兩型（amendment A5；細化見 R-3、R-4） |
| 6 | Graph MCP 退役（旁支） | **A**：當本 plan 的 Step 2.1；AGENTS 那句改寫**使用者已核准**（逐字見 §0.4 A6） |
| 7 | Phase 1 留下的小修 | **a＋b＋c**：#13 `pending --trigger` 必帶到期或綁 watch；#14＋#17 追源排回不再寫假 triage、缺分類有人接；#16 watch 的「今天」改台北日期（Step 2.9） |
| 8 | R2 | **A**：執行期間六條 trigger 命中就**常規 opt-in**（不停下來問，直接發 `WORK_REQUEST`）；plan 本身**不做 P0** |

### plan 作者的細化（使用者 2026-09-25「再針對我們的目標想想這幾點…是的話就繼續」授權；**開工前使用者可否決任一條**）

使用者要求對照目標（集中需求灌進薄層的 power-law）複查一次再寫。複查時實測了三件事（§0.2），改動如下——全部是收緊或拿掉機制，沒有放寬任何 gate：

| # | 對哪一題 | 細化 | 為什麼（實測） |
|---|---|---|---|
| R-1 | 2A | 護城河／量要**兩半各至少一段**引用：需求側（「繞不過」那一半）與供給側（「分布」那一半）——A/B 判準表讀的正是這兩半。**插槽的護城河**另外要求至少一段供給側引用來自**不是該供應商自己**的來源（客戶端或可解析的第三方；解析不到的 `needs_review` 不算），即 L8（sole_source 需客戶端或第三方印證）。`neither`／`undecided` 不強制 | 圖上 525 條 canonical 邊 **525 條都有逐字**，所以強制引用不會卡死；需求側繞不過的 13 個節點裡 7 個兩半都引得到，另外 6 個供給側 0 家——本來就判不出 A/B，寫 `undecided` 才誠實。SuperNova 那格唯一的原文是一篇 substack（tier 3、`needs_review`）：照這條規則它現在**不能**讀成護城河——那正是 Sivers 插槽賭注目前的真實證據強度 |
| R-2 | 4A | `config/lead_classification.json` 的 `decision_impact` 第一鍵裡有一類叫 `ranking`（「候選不變，但**誰是第一**會變」），`confidence_only` 的說明是「把已知第一名確認成第一名」——**daily 的 triage LLM 每天還在被問一個已退役的排序問題**。新增 `structure_change`（「圖的結構或讀圖判讀會變」），`ranking` 標 legacy（舊 lead 保留、排序與 `structure_change` 同級、triage 不再提供），兩句說明拿掉「第一名」 | 與 chokepoint 那軸同一件事：排序退役後殘留在研究注意力入口的兩處之一；不改，新的 lead 會繼續按「誰是第一」分類（L19：每 session 載入的字句會被當成目標——triage prompt 也是每天載入） |
| R-3 | 5A | 加兩型，都直接服務目標：`thin_layer_unread`（硬需求下的薄層，沒有人讀過）與 `supply_unfilled`（硬需求層的供給側 substitutability 全未填——ROADMAP 消費層對照表寫的「未填格併進走圖」） | 前者是「讀圖是新中心」的研究入口：走圖若不會說「去讀這一層」，讀圖只會停在既有兩個節點；實測 4／13（31%）。後者正是 InP 基板第一份讀圖判 `undecided` 的原因；實測 2／7（29%） |
| R-4 | 5A | **拿掉**先前提案的「插槽沒有主人」一型 | brainstorm 時報的「10／52（19%）」**母體算錯**：該問句只對「有人供貨的產品」有意義，正確是 **10／13（77%，恆亮）**。根因是圖上 `supplies_to → prod:` 一個關係承載兩種語意（L12）：13 個有供貨邊的產品裡，AMAT／NVIDIA／Tower／IQE／POET 多是「製造者自己」，Sivers→SuperNova 才是「零件供應商進客戶產品」。修它要動圖（入圖 gate），不是開發。本 Phase 改由插槽視角**明示**「分不出製造者還是零件供應商」（§5），Step 2.5 由強模型把資料修正提成 pq2（研究路徑） |

另：個股頁的讀圖面板印每份讀圖的**狀態**（現行／stale／過期）——`AGENTS.md`「結構不變就抱」要求持有者看得到「我騎的那一層結構變了沒」，這是它第一次出現在個股頁上（§8）。

## 0.2 現況實測（2026-09-25；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| 讀圖 ledger | 10 行、2 個節點（`mat:inp_substrate` 6 行、`tech:cw_dfb_laser` 4 行）；現行 2 份皆 v2、皆 `volume`：`sr_ad503ae880ceb398`（反證 6）、`sr_d07679979a8e4202`（反證 5，但這 5 條逐字搬自 `sr_a181641ddb99c69c`、無出處欄——Phase 1 待決 #19） | `python -m alpha structure-reading <node> --format json`；`library/private/alpha/structure_readings/*.jsonl` |
| `READING_KINDS` | `{"moat","volume","neither","undecided"}`——裝的是**判讀結論**，不是單位 | `alpha/structure_reading/contracts.py:55`；`tests/test_structure_reading_ledger.py:95` |
| 讀圖 id | content-addressed；v1 用 `_ID_FIELDS`、v2 用 `_ID_FIELDS_V2`（多 `disproof`），依 `record_version` 分支——**舊 id 一個字都不能變**（Phase 1 的語意 watch 以 reading_id 指回來源） | `alpha/structure_reading/contracts.py:66-70,175-182` |
| digest 欄位 | `EdgeView.key()`＝(src, relation, dst, substitutability, sole_source, **qualification_status**, evidence)——ROADMAP 要的「digest 含 `qualification_status`」**已成立**；`documents` 刻意不在內 | `query/structure.py:116-119` |
| canonical 邊的逐字覆蓋 | **525／525** 條至少一段逐字（V1 之後） | `MATCH (ea:EdgeAssertion)-[:QUOTES]->(:Source)` 以 (src_id, relation, dst_id) 去重，對 `collapse_assertions` 的 canonical 邊比對 |
| 需求側繞不過的節點（需求側至少一條 sub≥4） | **13**：`mat:inp_substrate`（已讀）、`tech:cw_dfb_laser`（已讀）、`tech:hbm`、`tech:semiconductor_manufacturing_equipment`、`tech:six_inch_inp_production`、`tech:uhp_laser`、`mat:rare_earth_magnets`（4 家）、另 6 個供給側 0 家（`mat:gallium_nitride`、`mat:glass_substrate`、`mat:rare_earth_metals`、`mat:silicon_wafer`、`tech:inp_6inch_fab`、`tech:mems_mirror_array`） | 對圖上所有 tech:／mat:／prod: 節點跑 `query.structure.build_structure`，取 `demand_side` 有 `substitutability >= 4` 者 |
| └ 薄層（供給側 1–3 家）且沒有現行讀圖 | **4／13**（hbm、semiconductor_manufacturing_equipment、six_inch_inp_production、uhp_laser） | 同上，扣掉 ledger 有現行讀圖的節點 |
| └ 供給側恰 1 家且那家不是外部印證 | **2／13**（`tech:semiconductor_manufacturing_equipment`←AMAT `self_reported_costly`；`tech:six_inch_inp_production`←Coherent `self_reported`） | 同上，看那條邊的 `evidence`（`classify_evidence` 的結果） |
| └ 供給側 ≥1 家但 substitutability 全未填 | **2／7** | 同上 |
| └ 兩半（需求側 sub≥4 的邊、供給側的邊）都至少一段逐字可引 | **7／13**（其餘 6 個供給側 0 家） | 同上 ＋ 逐字覆蓋 |
| 反向路徑非空的節點 | **26**；其中**只靠 `constrained_by`** 的 **7**（含 `mat:inp_substrate`：唯一一條是 `co:iqe constrained_by mat:inp_substrate`）；`tech:cw_dfb_laser` 的反向路徑只有 `prod:blazar competes_with`，**不受 A3 影響** | `python -m query.structure mat:inp_substrate --json` 的 `angles.counter_path` |
| `counter_path_relation` | `schema/vocab.json` 內 `["competes_with","constrained_by"]`；**沒有任何 loader**（唯一 loader 隨 `engine_d_runtime` 於 Phase 0 退役）；`query/structure.py:94` 自己硬編 `_COUNTER` | `python -c "import json;print(json.load(open('schema/vocab.json',encoding='utf-8'))['counter_path_relation'])"` |
| 走不到需求錨 | 所有 tech／mat／prod 節點 **93／182（51%，恆亮）**；有供應商的節點 49／113（43%）；所有公司 43／92（47%）；**有往下 `supplies_to`（tech／mat／prod）的公司 6／51（12%）** | `query.bottleneck.build_upward_index` ＋ `demand_chain` |
| 產品節點（插槽的候選） | 圖上 52 個 prod:，有 `supplies_to` 進來的 **13**；其中沒有任何 `develops`／`deploys` 進來的 10（77%）。`supplies_to → prod:` 同時承載「製造者賣自己的產品」（`co:applied_materials→prod:amat_ags`、`co:nvidia→prod:blackwell`…）與「零件供應商進客戶產品」（`co:sivers_semiconductors→prod:supernova`）——**L12** | `MATCH (c)-[:SUPPLIES_TO]->(p) WHERE p.id STARTS WITH 'prod:'` ＋ develops／deploys |
| `prod:supernova` | 需求側 1 條（`prod:teraphy_chiplet depends_on`）、供給側 1 條（Sivers，`qualification_status=designed_in`、evidence `needs_review`、sub 未填）；**兩條邊唯一的逐字都來自** `silicon_matter_sivers_ayar_2026_03_14`（tier 3、origin `silicon_matter_substack`）；下一層 0、反向 0、**走不到需求錨**；圖上沒有 Ayar Labs 對它的 `develops` 邊 | `python -m query.structure prod:supernova --quotes` |
| lead 點名但不在圖 | triaged_go 13 則中 10 則的 `entities.company_ids` 非空；其中 **4** 則點名的公司圖上沒有節點（`co:amd` ×2、`co:iren` ×2、`co:sandisk`）；registry 解析不到的 ticker 另有（`AKAM`、`SPCX`、`CXMT`…）——「ID 沒解析對」與「圖中真無此公司」要分開計（INV-1） | `library/leads/pending_leads.json` 的 `entities` 對圖節點 |
| coverage 現況 | 🔴 真缺口 9／🟡 建模待補 10／重複節點候選 23（沒人提過） | `python -m webapp status` 的 coverage 列 |
| pq1 排序鍵 | 字典序：`user_authority → decision_impact → content_type → payment_direction → chokepoint → relevance → tier → independent_source → novelty → lead_id`——**沒有 lead 時間**；`chokepoint` 由 `engine_b/cli.py::_chokepoint` 以 `structure_table()` 的 sub≥4 且有錨的列算（Phase 0 偏差 #33 刻意留給 Phase 2） | `engine_b/priority.py:200-230`；`engine_b/cli.py:37-100` |
| `decision_impact` 字彙 | `_order`：`exit_condition, candidate_set, ranking, unknown, confidence_only`；`ranking` 說明「誰是第一會變」、`confidence_only` 說明「把已知第一名確認成第一名」 | `config/lead_classification.json` |
| 佇列段 | 研究段裡與本 Phase 相關的三段：`coverage_gaps`、`duplicate_node_candidates`、`stale_structure_readings`（order 6）；`fired_reading_reread`（order 1，醒來驅動）**留** | `engine_b/queue_segments.py:108-127` |
| APP state kinds | 7：structure_table、beta、coverage、watches、positions、structure_readings、account_scorecard；`structure_readings` **已有 kind 與 API、沒有頁** | `python -m webapp status` |
| daily 的 materialize 旗標 | `crons/daily_task.py:184` 帶 `--coverage` 與 `--structure-readings`；`tests/test_daily_task.py` 斷言 `DAILY_STEPS` 逐項相等 | 讀程式 |
| 心跳 | 段 2 有「結構讀圖 N 份｜現行｜該重讀」一行；段 3「pq1 可做…＋結構讀圖待重讀」 | `crons/heartbeat.py:655-690,915-925` |
| Graph MCP | 已停（Phase 1 C5）；程式、測試、文件仍在；本 session 的工具清單仍列 claude.ai 上的 `stockbotv2-graph` connector（後端 404）——**移除它是使用者在 claude.ai 設定裡的動作** | ROADMAP 旁支列的盤點命令 |

## 0.3 本 Phase 刻意不做

- 不做候選狀態、三個財務是非題、`record_trade.py --receipt`、readiness 核心面板換（Phase 3）；讀圖面板**只加為選配**。
- 不做層中心選源規則與 `substitutability` 的 `auto` 投影稽核（Phase 4）；不做量測（Phase 5）。
- **不動圖**（Neo4j 的節點、邊、屬性）：`supplies_to → prod:` 的兩義、重複 SourceDoc 紅燈、缺的 `develops` 邊都是入圖 gate 的研究題，由 Step 2.5 或互動 session 提 pq2，不由執行者改。
- 不動 read model 的 `get_bottlenecks`（個股頁 argument「鏈」段用的 sub≥4 成員判準，Phase 0 偏差 #33 的另一半）：它是呈現，不餵佇列；拿不拿掉留到 Phase 3 面板重排時一起決定（§14）。
- 不把 A/B 判準表寫成程式自動分類（`contracts.py` 檔頭第 3 條、INV-5）；讀圖仍由寫的人宣告。
- 不讓走圖產出任何跨型別的分數、top-N、「最重要的洞」。
- 不改 `pq1.drain_limit_per_run`（daily 不做研究，改它＝改 AGENTS 判準句）。
- Phase 1 closeout §7 其餘各題不在本 Phase：#1 thesis 引用的 claim 反證（Phase 3，G8 說只登記被候選讀圖或敘事引用的）、#2 重複 SourceDoc（研究）、#3 管道合併（Phase 5）、#5 Drive 備份、#6 `catalyst_watch.py`、#7 daily 做研究、#8 預篩全文覆蓋（等 ③ 生效）、#9 `claude -p` context、#10 AXT 7b（研究）、#11、#12、#15（使用者動作）、#18 封存 prompt 判準句——全部列進結案待決（§14）照實帶到下一 Phase。
- `test_full_chain_acceptance` 重寫仍留 Phase 3（三題的 `absence_kind` 要那時才有；Phase 0 偏差 #29）。

## 0.4 ROADMAP amendment（五欄；使用者 2026-09-25 定案，ROADMAP Phase 2 列與旁支列已同 commit 改寫）

**A1｜讀圖的單位是一個新欄位，不是判讀字彙的一個新值**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「`READING_KINDS` 加 `socket`」 |
| 新觀察 | `READING_KINDS` 裝的是判讀結論（護城河／量／都不是／判不出），不是單位；插槽讀圖本身也要回答「護城河還是量」（決定紀錄 G5：護城河賭注騎插槽） |
| proposed change | 讀圖紀錄 v3 加 `unit ∈ {layer, socket}`（封閉字彙 `READING_UNITS`）；`READING_KINDS` 不動；v1／v2 解析成 `layer`；選取與 staleness 以（節點, unit）為單位各自算 |
| why | 把「讀的是什麼」塞進「讀成什麼」就是一個欄位兩種語意（L12），下游會被迫二選一而兩邊都錯；`AGENTS.md`「讀圖必須宣告它讀的是哪一種單位」 |
| impact | `alpha/structure_reading/`、`alpha/cli.py`、`alpha/providers/structure_readings.py`、webapp 的 structure_readings kind；舊紀錄 id 不變 |

**A2｜讀圖的判讀必須指得回圖上的原文**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「讀圖輸出必含逐字（L18）」 |
| 新觀察 | 逐字已入圖且 525／525 條邊都有；`query.structure --quotes` 印得出來，但**讀圖紀錄不存判讀憑哪一段**，寫的人仍可只看標籤；現行 CW DFB 讀圖的 5 條反證追回原文要跳兩層（Phase 1 待決 #19） |
| proposed change | v3 加 `citations[]`（角度、邊、原文片段、來源 id），寫入時由程式核對：邊在當次快照的那個角度裡、片段是圖上該邊某段逐字的子字串；`moat`／`volume` 需求側與供給側**各至少一段**；`unit=socket` 的 `moat` 另需至少一段供給側引用的來源**不是該供應商自己**且可解析（L8）；`disproof[]` 每條加 `source`（`self` 或同節點 ledger 裡既有的 `sr_*`） |
| why | L18：把原始證據換成標籤的步驟，標籤必須指得回原始證據；答不出「憑哪一段」就寫不進去，比「請深入思考」有效 |
| impact | 同 A1；寫讀圖多一步挑引文；`neither`／`undecided` 不受限 |

**A3｜反向路徑只收競爭關係，字彙成為唯一來源**

| 欄 | 內容 |
|---|---|
| 原 roadmap | （Phase 0 closeout §7-3 待決：`counter_path_relation` 要接還是退役） |
| 新觀察 | 反向路徑非空的 26 個節點中 7 個只靠 `constrained_by`——那是「又一個人繞不過它」，是利多不是反證；InP 基板讀圖（`sr_6ad5c884eb7bc3fb`）已寫明它的反證 ③ 會因此誤響；`query/structure.py` 硬編 `_COUNTER`、字彙沒有 loader |
| proposed change | `schema/vocab.json` 的 `counter_path_relation` 改 `["competes_with"]`（附註解寫明 `constrained_by` 為何移出）；`query/structure.py` 反向路徑改讀它（唯一 loader） |
| why | 反證來源不乾淨，「出場只認反證」就會被誤報訓練成忽略；分類有 SSOT 就要讓資料走到它（L16） |
| impact | 7 個節點的反向路徑變空；`mat:inp_substrate` 的現行讀圖因此轉 stale 一次（預期，Step 2.5 重讀）；`constrained_by` 仍在需求側／下一層 |

**A4｜研究佇列排序拿掉最後的結構排序殘留**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「優先序＝lead 時間＋使用者點名」 |
| 新觀察 | pq1 字典序第五鍵 `chokepoint` 吃 sub≥4 的結構表成員（Phase 0 偏差 #33 延後）；第一鍵 `decision_impact` 的 `ranking` 類問的是「誰是第一會變」（R-2）；排序鍵沒有 lead 時間 |
| proposed change | 拿掉 `chokepoint` 鍵與 `_chokepoint()`（drain 不再為排序讀 Neo4j）；`decision_impact` 新增 `structure_change`、`ranking` 標 legacy；在 `lead_id` 之前加 lead 時間（`first_seen`，舊的先）；triage 對 lead 本身的其他分類軸保留；`graph_holes` 不排序：型別固定順序（閱讀順序，不是價值判斷）、型別內按節點 id |
| why | G1／G2：有優先分數就是換名字的排序；triage 分類判的是 lead 本身，拿掉會把 2026-08-21 量到的 Form 4 洗版叫回來（`engine_b/priority.py` 檔頭） |
| impact | `engine_b/priority.py`、`engine_b/cli.py`、`config/lead_classification.json`、triage prompt 與 `triage-apply` 驗證、`scripts/backfill_lead_classification.py` 與相應測試 |

**A5｜走圖問句清單：九型，實測後才定母體**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 五型：需求側繞不過但只有一家且全自報、走不到錨、讀圖過期、lead 點名但不在圖、重複節點候選；驗收要求每型觸發率 <50% |
| 新觀察 | 「走不到錨」照字面 93／182（51%）第一天就不過；讀圖是新中心，但沒有一型會說「去讀這一層」；「未填格」在消費層對照表有寫、Phase 列漏掉；「插槽沒有主人」實測 77%、根因是圖的兩義（R-4） |
| proposed change | 九型（§7 表）：`thin_layer_unread`、`sole_supplier_self_reported`、`supply_unfilled`、`reading_stale`、`lead_not_in_graph`、`supplier_no_anchor`（收窄）、`no_supplier`、`modelling_gap`、`duplicate_node`；「插槽沒有主人」不做 |
| why | 驗收 <50% 是 ROADMAP 自己的（L14-4 恆亮＝零鑑別力）；問句要窄到指得出下一個研究動作 |
| impact | 新 `query/graph_walk.py`；`graph_holes` 吸收三個既有佇列段；coverage kind 改名 `graph_walk` |

**A6｜Graph MCP 退役排入 Phase 2，AGENTS 一句改寫（使用者 2026-09-25 核准逐字）**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 旁支開發項「Graph MCP 退役」，前置「Phase 1 結案」、「排在 Phase 之間」 |
| 新觀察 | Phase 1 已結案，現在正是 Phase 之間；它與 Phase 2 改同一批檔（skills、OPERATIONS、ARCHITECTURE），同一個 writer 依序做最安全 |
| proposed change | 成為 Step 2.1，驗收沿用旁支列①–⑤。`AGENTS.md`「協作與邊界」的 **Local-first** 一句：原「**Local-first：** 「Claude」預設指本機 Claude Code；cloud＋MCP 是備援，新核心不得依賴 MCP。」→ 新「**Local-first：** 「Claude」預設指本機 Claude Code；遠端操作走 Remote Control 連本機 session，不開對外的寫入入口。」 |
| why | MCP 是一個對外的寫入入口（`record_lead_decision`、`apply_research_action`、`load_extraction`），不用就不該開著；那句今天核准，執行者不必為了它停下（停止條件④） |
| impact | 旁支列描述的全部檔案；`AGENTS.md` 只改這一句（Step 2.1 的 commit 裡改，`git diff` 必須只有這一行） |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-09-25 已核准的 PLAN_PROPOSAL**（§0.1 八題＋R-1～R-4 細化，細化開工前可否決）。`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 2 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（使用者 2026-09-25 定案 8A）**：R2-a（2.1 之後）、R2-b（2.3＋2.4 之後）直接發 `WORK_REQUEST`，不停下來問；NO_GO → `AWAITING_HUMAN`。

**唯一預定的停點：2.4 的 R2-b 回 GO 之後，停下來請使用者切強模型做 Step 2.5**（研究，不是開發）。2.5 完成後使用者切回便宜模型貼 `/phase-run`，從 2.6 接續。
（2.5 刻意排在走圖與讀圖頁之前：讓第一份真實插槽讀圖先跑過工具，工具的毛病在建頁面之前冒出來——L13：驗收是產出到了消費者手上。）

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。commit 短碼由下一個 Step 的 commit 補填。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（05:30）是唯一排程。它寫 `library/`，不寫 tracked 程式；但 **2.6 改 `crons/daily_task.py` 的 materialize 旗標**、**2.8 改 triage 分類字彙**——這兩個 Step 的 commit 不得跨越 05:30 還沒 push（半改的狀態會被 daily 跑到）。開工前查 `schtasks /Query /TN StockBotv2-Daily /V /FO LIST` 的下次執行時間。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 2.0 | 基準快照 | ○ | 便宜 | |
| 2.1 | Graph MCP 退役 ＋ AGENTS 一句（R2-a） | ○ | 便宜 | |
| 2.2 | 反向路徑只收競爭關係 | ○ | 便宜 | |
| 2.3 | 讀圖契約 v3：`unit`、`citations[]`、反證出處 | ○ | 便宜 | |
| 2.4 | 插槽視角 ＋ 分單位的 staleness（R2-b 涵蓋 2.3＋2.4） | ○ | 便宜 | |
| 2.5 | 第一份插槽讀圖、InP 基板重讀、兩個插槽試跑 | ○ | **強模型** | （ledger 不在 git；收據寫進 plan §0.6 與報告） |
| 2.6 | 走圖：`query/graph_walk.py`、`graph_holes` 段、`graph_walk` kind、心跳 | ○ | 便宜 | |
| 2.7 | 讀圖頁 ＋ 個股頁讀圖面板（選配） | ○ | 便宜 | |
| 2.8 | pq1 排序：拿掉 chokepoint、`decision_impact` 換詞、加 lead 時間 | ○ | 便宜 | |
| 2.9a | `pending --trigger` 必帶到期或綁 watch | ○ | 便宜 | |
| 2.9b | 追源排回不寫假 triage、缺分類有人接 | ○ | 便宜 | |
| 2.9c | watch 的「今天」改台北日期 | ○ | 便宜 | |
| 結案 | completion gate ＋ closeout 報告 ＋ R2 ＋ ROADMAP ✅ | ○ | 便宜 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 2 結案；撞到六條停止條件才停。
Step 2.5 是強模型的研究步驟：輪到它時停下來，印出 §6 的「強模型貼這段」給我。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|

---

## 0. 不可越線（違反即 NO_GO）

1. **不碰資料 authority：** 不改 Neo4j、Engine C ledger、thesis lifecycle、Google Sheet、`library/trades/`。**讀圖 ledger 只由 Step 2.5（強模型）經 `python -m alpha structure-reading <node> --add` 寫**；其他 Step 的測試一律用暫存目錄，不得 append 真實 ledger。
2. **既有讀圖紀錄一行都不改寫**；v1／v2 的 `reading_id` 用新程式重算必須逐字相同（Phase 1 的語意 watch 與 audit `Orphans` 以它指回來源）。
3. **舊 Decision Store 只准讀**：Step 2.0 記 sha256 與 `live_choices`，結案比對必須相同。
4. **任何 `python -m <module>` 命令字串變更 → sandbox impact review 五步**（ROADMAP 硬約束 10），同一個 commit 改相應測試。本 Phase 已知會撞：2.6 的 `--coverage` → `--graph-walk`。
5. **每刪一個測試檔或測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守**（Phase 1 R2 N1 的教訓：函式層級也要列）。活機制的測試不可刪斷言。
6. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
7. **走圖不排序、不打分、不 gate**：沒有跨型別的數字合成、沒有 top-N、沒有「最該研究」；型別順序只是閱讀順序。
8. **`AGENTS.md` 只准改 §0.4 A6 那一句**（Step 2.1），`git diff` 只能有那一行。
9. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 已知會撞：某型走圖問句收窄後仍 ≥50%（§7「母體規則」）；v1／v2 id 重算不同。
10. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** 走圖與讀圖都是 A3（研究判斷、可重算）的輸入或輸出，不得長成第二個 A1 current-state authority：**不落地任何快取表當真相**（APP artifact 是可重建的 derived cache）。

## 1. Step 2.0 基準快照（Z0，一個 commit）

全部存進 `docs/reports/2026-09-2x-phase2-baseline.md`（日期用實跑日），每項附實際輸出：

```powershell
python -m pytest -q                               # 全綠基準與測試數；另記 tests/test_*.py 檔數
python -m audit invariants                         # 13 PASS 基準
python -m webapp status                            # 7 個 kind
python -m engine_b.cli counts
python -m engine_b.event_watch counters
python -m engine_b.todo list
python scripts\retired_mechanism_grep.py           # 八組 keep-list 三個 0
python -m alpha structure-reading mat:inp_substrate --check
python -m alpha structure-reading tech:cw_dfb_laser --check
python -m crons.heartbeat --out <scratchpad>\hb_base.md
git grep -n -i -e mcp_server -e graph_mcp -e "\bMCP\b" -e stockbotv2-graph -e "mcp\.minatoyukina" -e record_lead_decision -e apply_research_action -e load_extraction
```

另外記：
- 舊 Decision Store 三個 `*.db` 的 sha256 與 `live_choices`（照 Phase 1 基準 §9 的做法）。
- **全圖每個節點的 `result_digest`**（對圖上所有出現在邊裡的節點跑 `build_structure(...).result_digest()`，存成 `node → digest` 的 JSON 到 scratchpad、報告只記筆數與檔案 sha256）——2.2 與 2.4 要拿它證明「只有預期的節點變了」。
- 兩份現行讀圖、以及全部 10 行 ledger 的 `reading_id` 重算結果（2.3 要逐字比對）。
- pq1 目前 13 則 triaged_go 的排序（`engine_b.cli` 列 pq1 的那條命令；2.8 要逐則解釋位移）。
- §0.2 表的每個數字重跑一次（圖可能已變）；不一致的照實寫，**以重跑的為準**。

驗收：報告存在且含上面每一項。

## 2. Step 2.1 Graph MCP 退役 ＋ AGENTS 一句（Z2，R1 ＋ R2-a 常規 opt-in）

**照 ROADMAP「旁支開發項：Graph MCP 退役」那一列逐字執行**（刪／改寫／封存／歷史留著四類、`retired_mechanism_grep.py` 加 MCP 組並把 AREAS 擴到所有 tracked `.md`、`AGENTS.md`／`prompts/`／`deploy/`／`.claude/skills` 都要掃）。本 plan 只補三件：

1. **AGENTS 那一句**照 §0.4 A6 逐字改；ROADMAP 硬約束 12「Local-first；Core 不得 import `mcp_server`」改成「Local-first；不開對外的寫入入口」（`mcp_server/` 不存在後，原句的後半是守一個不存在的東西）。
2. 可拆兩個 commit：2.1a 程式與測試（`mcp_server/` 刪、只守它的測試刪、`tests/test_layer_separation.py` 的 `KNOWN_MCP_CONSUMERS`、各模組註解與分支）；2.1b 文件、skill（跑 `python scripts/sync_agent_skills.py`）、封存、grep 組與 keep-list、AGENTS 一句、ROADMAP 旁支列標 ✅。
3. HUMAN SUMMARY 的「使用者動作」列：①到 claude.ai 設定移除 `stockbotv2-graph` connector；②本機 `.claude/settings.local.json` 裡 MCP 工具的權限條目（若該檔未被 git 追蹤，由執行者直接清並在八欄列出清了哪幾條）。

- **驗收**：旁支列①–⑤（`mcp_server/` 不存在；MCP 組殭屍 grep 在所有 tracked 檔扣 keep-list 為 0、keep-list 每條理由是「歷史紀錄」且無腐壞條目；`pytest` 綠、`audit invariants` 綠；`~/.cloudflared/config.yml` 沒有 `mcp.`／`neo4j.`；AGENTS 一句有核准紀錄＝本 plan §0.4 A6）。另：`git diff <2.0 commit> HEAD -- AGENTS.md` 只有那一行。
- **L11-6 ④**：最先壞的是**本機仍在用的 `intake/` 路徑與 `engine_b/todo.py`／`webapp/api.py` 裡提到 MCP 的分支**——刪分支前確認那條分支在本機路徑上不可達（grep 呼叫端），`intake/` 的 domain 本身留。另查 `.claude/settings.json` 的三個 SessionStart hook 沒有一個呼叫 MCP。
- **R2-a**（trigger：security／architecture boundary migration）：GO 後照常接續。`WORK_REQUEST` 的檢查：旁支列①–⑤自己重跑；逐條審 keep-list；抽 5 個刪掉的測試函式確認它守的東西已不存在或已由別處守。

## 3. Step 2.2 反向路徑只收競爭關係（Z1，R1）

- **改哪裡**：`schema/vocab.json`（`counter_path_relation` → `["competes_with"]`，加 `_counter_path_relation_comment`：`constrained_by` 為什麼移出、2026-09-18 讀圖 `sr_6ad5c884eb7bc3fb` 的量測、它仍在需求側／下一層）；`query/structure.py`（`_COUNTER` 改由一支讀 `schema/vocab.json` 的函式提供——先找 repo 裡既有的 vocab loader 用它，沒有才新增一支、並讓它是唯一一支）；`docs/solutions/architecture-patterns/closed-vocabulary-registry.md` 那一列；`schema/graph_schema.md` 若提到 counter path。
- **不改**：`staleness.py` 的 `DISPROOF_KINDS`（`counter_path` 仍是反證來源，只是成員變乾淨）；`tests/test_is_variant_of.py` 守的「`is_variant_of` 不進任何走訪清單」必須照樣綠。
- **怎麼驗**：新測試：反向路徑成員＝字彙（改字彙就改行為，不能各寫一份）；`constrained_by` 邊仍出現在需求側或下一層；對 2.0 的全圖 digest 重算，**變動的節點集合＝§0.2 那 7 個（或 2.0 重跑的數字）**，一個不多一個不少；`python -m alpha structure-reading mat:inp_substrate --check` 報 stale、變化只有 `counter_path` 消失 1 條；`tech:cw_dfb_laser --check` 與 2.0 相同。
- **驗收（層：圖——讀圖工具的角度成員）**：反向路徑非空的節點 26 → 19（或 2.0 重跑的數 − 只靠 `constrained_by` 的數）。
- **L11-6 ④**：最先壞的是 **`mat:inp_substrate` 讀圖的反證 ③（「反向路徑新增」）**——它登記成語意 watch（Phase 1 Step 1.6）；確認 watch 的條件原文與實體不受影響（語意 watch 不讀角度，只比對一手文件），並在八欄寫明「InP 基板讀圖轉 stale 是本 Step 的預期結果，由 2.5 重讀」。**不要為了讓它回 current 去改 digest 或 staleness 規則。**

## 4. Step 2.3 讀圖契約 v3（Z2，R1；R2-b 在 2.4 之後一起發）

- **改哪裡**：`alpha/structure_reading/contracts.py`、`__init__.py`、`alpha/providers/structure_readings.py`（寫入端核對、取逐字）、`alpha/cli.py::cmd_structure_reading`、`tests/test_structure_reading_ledger.py`、登記語意 watch 的 hook（Phase 1 Step 1.5）與其測試。
- **怎麼改**：
  1. `RECORD_VERSION = "structure-reading/v3"`；v1／v2 常數與 id 算法**一字不動**；v3 的 id 欄位＝v2 欄位 ＋ `unit`、`citations`（同 v2 對 `disproof` 的做法，依 `record_version` 分支）。
  2. `READING_UNITS = {"layer": "層讀圖：技術／材料節點（含變體）", "socket": "插槽讀圖：客戶的產品／專案 × 那一格零件"}`（封閉字彙）；`unit=socket` ⇒ 節點必須是 `prod:`；`unit=layer` ⇒ 不得是 `co:`。v1／v2 解析成 `layer`。
  3. `citations[]` 每條：`angle`（`ANGLE_KEYS` 之一）、`edge`（[src, relation, dst]）、`quote`（≥20 字）、`source_id`。**契約層**驗：`moat`／`volume` 需 `demand_side` 與 `supply_side` 各 ≥1 條；`unit=socket` 且 `moat` 需 ≥1 條 `supply_side` 引用標了 `independent=true`。**寫入端**（provider，走圖查詢）驗：邊在當次快照該角度裡；`quote` 去空白正規化後是圖上該邊某段 `Source.quote` 的子字串；`independent=true` 的那條，其 `SourceDoc.origin_entity` 經 `company_id_for_origin`（`query/bottleneck.py` 既有 owner，不重造）解析得到、且不是該供應商本身。任何一條不過就拒收並印出是哪一條、為什麼。
  4. `disproof[]` 每條加 `source`：`"self"`（本份寫下）或同節點 ledger 裡既有的 `sr_*`（沿用自哪一份）；寫入端驗 `sr_*` 存在。
  5. `select_reading(records, unit=…, …)` 與 `reading_status` 以（節點, unit）為單位；CLI `--unit` 旗標（`--add` 的 spec 必填 `unit`；`--list`／`--check` 預設列兩種）。
  6. `undecided`／`neither` 可以帶 `disproof[]`：用來登記「什麼事件發生就能判」的確認條件（G7：反證與確認事件寫下那一刻就登記）；登記 hook 對它們一樣運作。
- **怎麼驗**：10 行既有 ledger 用新程式解析、`reading_id` 重算與 2.0 逐字相同；v3 的拒收案例各一條測試（缺一半引用、引用的邊不在快照、片段不在圖上、插槽護城河只有供應商自報的引用、`independent` 的來源解析不到、反證 `source` 指向不存在的 `sr_*`、`socket` 用在 `tech:` 節點）；v3 合法紀錄在暫存 ledger append 成功且語意 watch 登記得到；`python -m audit invariants --only Orphans` 綠。
- **驗收（層：讀圖）**：既有 10 行 id 相同 10／10；v3 拒收規則每條有一個會紅的測試。
- **L11-6 ④**：最先壞的是 **Phase 1 登記的 11 條讀圖來源語意 watch**（它們以 `sr_ad503ae880ceb398`、`sr_d07679979a8e4202` 指回來源）——id 若重算不同，audit `Orphans` 會紅、心跳「叫不醒」會亂。動手前先寫「重算舊 id」那條測試並讓它綠。

## 5. Step 2.4 插槽視角 ＋ 分單位的 staleness（Z2，R1 ＋ R2-b 常規 opt-in）

- **改哪裡**：`query/structure.py`、`alpha/structure_reading/staleness.py`、各自測試；`alpha/providers/structure_readings.py`（快照帶 unit）。
- **怎麼改**：
  1. `python -m query.structure <prod:…> --unit socket [--quotes] [--json]`：四個邊角度與需求錨**照舊**（`result_digest` 函式不變，所以同一個節點兩種單位的指紋相同，差別只在讀法與分級）。插槽另外印兩段，**都不進 digest**：
     - **製造者**：供給側裡同時對該產品有 `develops` 邊的公司標「製造者（不是零件供應商）」；圖上沒有任何 `develops`／`deploys` 進這個產品時，印明示缺席「圖上分不出這個產品是誰的：`supplies_to` 可能是製造者自己，也可能是零件供應商（L12，見 plan R-4）」——不得安靜印空。
     - **客戶端原文**：這個產品相關邊上的逐字中，來源 `origin_entity` 解析得到、且不是任何一家供應商的；沒有就印「沒有任何客戶端或可解析第三方的一手原文」並列出現有來源的等級（例：SuperNova 只有一篇 tier 3 substack）。
     - 不進 digest 的理由寫在程式註解：逐字篇數會隨我們多讀文件而單調上升（`AGENTS.md` 已知會失焦的指標）；「客戶第一次具名」已經由 digest 裡那條邊的 `evidence` 欄位捕捉到。
  2. `staleness.py`：`grade_changes(..., unit=...)`；`unit=socket` 時，**供給側邊的 `evidence` 變動**用新 `CHANGE_KIND` `supply_evidence`（`high`：「插槽的供貨邊證據等級變了——客戶或第三方第一次具名，是插槽賭注的確認或推翻事件」）；`qualification_status` 變動本來就走供給側 `high`，不動；`layer` 的分級一字不動。`reading_status` 讀紀錄自己的 `unit`。
  3. `--json` 多 `unit` 與 `socket` 子物件（makers、customer_quotes、absence）。
- **怎麼驗**：在 **`prod:supernova`、`prod:els_8ch_module`、`prod:ph18da`** 三個產品跑（L17：只認得當初那個案例的機制當下就修）——各自的製造者段與客戶端原文段符合圖上事實（逐一寫進八欄）；對 2.0 之後（2.2 之後）的全圖 digest 重算：**0 個節點變動**（本 Step 不得動指紋）；staleness 新測試：插槽紀錄遇供給側 evidence 變動 → `stale`（high）、層紀錄同樣變動 → `stale_low`（不變）。
- **驗收（層：讀圖工具）**：三個產品的插槽視角輸出存進報告；全圖 digest 變動 0。
- **L11-6 ④**：最先壞的是 **`tech:cw_dfb_laser` 的現行讀圖狀態**——它若因本 Step 由 current 變 stale，就是插槽的附加段漏進 digest 了。
- **R2-b**（trigger：authority mutation——A3 append-only ledger 的寫入契約與 id 算法）：對 2.3＋2.4 發。檢查：v1／v2 id 重算自己跑；每條拒收規則自己造一個反例；三個產品的插槽視角自己跑並對圖；全圖 digest 前後比對自己跑。**GO 之後停下來（§0.5 唯一預定停點），HUMAN SUMMARY 的「下一步」逐字印 §6 的「強模型貼這段」。**

## 6. Step 2.5 第一份插槽讀圖、InP 基板重讀、兩個插槽試跑（**強模型、互動 session**；研究，不是開發）

**這是研究（改變「我們相信什麼」），不走 development-flow 八欄；收據寫進本 plan §0.6 與 `docs/reports/2026-09-2x-phase2-step25-readings.md`。** 讀圖不是四個人工 gate 之一；**任何需要改圖的發現一律提 pq2（manual／ra_admission），不直接動圖。**

強模型貼這段：

```
讀 docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md 的 §0.1、§0.2、§4、§5、§6，照 §6 做 Step 2.5。
這是研究步驟：讀圖寫進 ledger（python -m alpha structure-reading <node> --add），需要動圖的發現提 pq2、不直接改圖。
做完寫報告、更新 plan 進度表與 §0.6，commit、push，然後告訴我切回便宜模型貼 /phase-run。
```

1. **Sivers × Ayar SuperNova 插槽讀圖**（決定紀錄 §4.3 點名的那一個）：`python -m query.structure prod:supernova --unit socket --quotes`，寫一份 `unit=socket` 的 v3 讀圖，`tickers` 含 `SIVE.ST`。依 §0.2，圖上唯一的原文是一篇 substack，所以依 A2 它**不能**寫成護城河——預期是 `undecided`，`reading` 寫清楚缺哪一格（客戶端一手原文、Ayar 對 SuperNova 的 `develops` 邊、需求錨鏈），並用 `disproof[]` 登記確認條件（例：「Ayar Labs 的一手文件具名 Sivers 為 SuperNova 雷射陣列供應商」，實體含 `co:sivers_semiconductors` 與 Ayar 的 `co:*`）。**若研究時找到客戶端一手原文，照 source-trace／入圖流程提 pq2，不在讀圖裡引用圖上還沒有的原文。**
2. **兩個插槽試跑**：`prod:els_8ch_module`、`prod:ph18da` 跑插槽視角；值得就寫讀圖，不值得就在報告寫「工具在這個插槽上顯示了什麼、有沒有錯」。目的是驗工具不是只認得 SuperNova。
3. **`mat:inp_substrate` 重讀**（2.2 讓它轉 stale）：寫一份 v3 `unit=layer`，`supersedes_id` 指現行那份；兩半各至少一段引用；反證沿用的每條 `source` 指 `sr_ad503ae880ceb398`，新寫的標 `self`。反證 ③ 的母體瑕疵（`constrained_by`）已在 2.2 修掉，照實改寫它。
4. **`supplies_to → prod:` 的兩義**（R-4）：看完三個產品後，若判斷要修，寫一筆 pq2 manual 提案（哪些邊該是 `develops`、依據哪段原文、影響哪些插槽），**不自己改圖**。
5. `tech:cw_dfb_laser` 的現行讀圖 2026-10-18 到期：本 Step 不必重讀；若時間允許可一併做成 v3 並解決 #19（反證出處）。

- **驗收（層：讀圖、registry）**：ledger 出現第一份 `unit=socket` 讀圖（ROADMAP 驗收①）；`mat:inp_substrate` 回 current；新紀錄的語意 watch 登記得到（`python -m engine_b.event_watch counters` 前後差）；報告列三個產品的工具輸出與任何工具毛病（毛病＝回頭修 2.4，記偏差）。

## 7. Step 2.6 走圖（Z2，R1）

- **改哪裡**：新 `query/graph_walk.py`；`webapp/contracts.py`（kind `coverage` → `graph_walk`，同 Phase 0 `ranking` → `structure_table` 的做法）、`webapp/materialize.py`（`materialize_graph_walk`）、`webapp/__main__.py`（`--graph-walk`）、`webapp/api.py`（`/api/v1/graph-walk`）、`webapp/static/app.js`／`index.html`（`#/graph-walk`、nav「走圖」，取代 coverage 頁）；`engine_b/queue_segments.py`（新段 `graph_holes`，刪 `coverage_gaps`、`duplicate_node_candidates`、`stale_structure_readings` 三段；`fired_reading_reread` 留）；`audit/checks.py` 的段計數注入；`crons/heartbeat.py`；`crons/daily_task.py` 的 materialize 旗標（**sandbox impact review 五步**、`tests/test_daily_task.py` 同 commit）；`skills/research-drain/SKILL.md` 第三段、`skills/alpha-status/SKILL.md`「哪裡還沒挖」、`skills/daily-brief/SKILL.md` 提到 coverage 的句子（跑 `sync_agent_skills.py`）；OPERATIONS／ARCHITECTURE 相應段。
- **九型問句（封閉字彙 `QUESTION_TYPES`；順序是閱讀順序，不是價值判斷）：**

| # | key | 問句（印給人看的） | 母體 | 命中 | 下一個研究動作 | 基準（§0.2） |
|---|---|---|---|---|---|---|
| 1 | `thin_layer_unread` | `{node}` 繞不過、供應商只有 {n} 家，還沒有人讀過 | 需求側有 sub≥4 的節點 | 供給側 1–3 家、且沒有任何單位的現行讀圖 | `query.structure` → 寫讀圖 | 4／13 |
| 2 | `sole_supplier_self_reported` | `{node}` 繞不過、圖上只有 `{co}` 一家，證據只有它自己說 | 同上 | 供給側恰 1 家、那條邊 `evidence` 不是 `externally_corroborated`／`counterparty_joint` | 從客戶端或第三方找第二家或印證（層中心選源） | 2／13 |
| 3 | `supply_unfilled` | `{node}` 繞不過，但 {n} 家供應商的可替代性都沒填——判不出護城河還是量 | 需求側 sub≥4 且供給側 ≥1 家 | 供給側 substitutability 全為 None | 補供給側 sub | 2／7 |
| 4 | `reading_stale` | `{node}`（{unit}）的讀圖跟圖不一致或過期：{變化摘要} | 現行讀圖（節點, unit） | `needs_reread()` 為真（stale／expired；`stale_low` 不算） | 重讀 | 1／2（2.2 後、2.5 前） |
| 5 | `lead_not_in_graph` | lead `{lead_id}` 點名 `{co}`，圖上沒有這家 | triaged_go／researching 且 `entities.company_ids` 非空的 lead | 有 registry 解析到、但圖上沒有節點的公司 | onboard 評估（company-onboard） | 4／10 |
| 6 | `supplier_no_anchor` | `{co}` 有往下供貨，但走不到任何需求錨 | 有往下 `supplies_to`（tech／mat／prod）的公司 | `demand_chain` 為空 | 補需求鏈或確認它不屬本題材 | 6／51 |
| 7 | `no_supplier` | 誰供應 `{node}`？（圖上 0 家） | coverage 既有定義 | coverage 🔴 | 找供應商 | 9 |
| 8 | `modelling_gap` | `{node}` 有研究但邊沒接到它 | coverage 既有定義 | coverage 🟡 | 補建模 | 10 |
| 9 | `duplicate_node` | `{a}` 與 `{b}` 可能是同一個節點 | `duplicate_nodes` 既有定義（只收 `unmentioned`） | 候選對 | 判定同一個 → pq2 ra_admission | 23 對 |

  - 第 5 型：registry **解析不到**的名字不算命中，但同一行另印「另有 N 個名字 registry 解析不到」（INV-1：ID 沒解析對 ≠ 圖中真無此公司；INV-3：不得靜默丟棄）。
  - 型別內順序：節點 id 字典序；第 5 型按 lead `first_seen`（舊的先）。**不得**跨型別合成任何數字。
  - 資料來源：1／2／3／6 由圖（`query.structure` 與 `query.bottleneck` 的既有函式，**不重造 collapse 或 evidence 判定**，L16）；4 由讀圖 ledger 的 staleness（composition 在 `webapp/materialize.py`，`query/` 不 import `alpha/`——先跑 `tests/test_layer_separation.py` 確認分層規則）；5 由 leads；7／8／9 沿用 `query/coverage_gaps.py`、`query/duplicate_nodes.py`（重用，不搬）。
  - **母體規則（L14-4）**：每型輸出 `hit_n／scope_n`。實作完先跑一次：母體 ≥10 的型別若命中率 ≥50%，**收窄母體**（不是刪型別）並記偏差；收窄後仍 ≥50% → `AWAITING_HUMAN`。母體 <10 的型別（例：第 4 型）命中率只印不判，結案時照實寫。
- **心跳**：段 3 一行「走圖：」接九型各自「中文短名 命中／母體」，**0 也印**；artifact 讀不到時印 `upstream_unavailable` 不印 0（INV-3）；段 3 原本「＋結構讀圖待重讀 N」改由走圖那行承載。段 2 讀圖那行加單位拆分（層 N／插槽 M）。
- **怎麼驗**：`python -m query.graph_walk`（markdown）與 `--json` **重現 §0.2 的基準數**（或 2.0／2.5 之後重跑的數），差異逐項解釋（L11-6）；`python -m webapp materialize --graph-walk` 後 `webapp status` 列得出 `graph_walk`、不再列 `coverage`；`python -m audit invariants`（含 `QueueSegments`、`QueueLiveness`）綠；心跳輸出含走圖行；`pytest tests/test_webapp_request_path.py` 綠（request path 不查圖）。
- **驗收（層：圖——走圖問句在圖上的命中／母體；機制存在與否）**：九型各有命中／母體；母體 ≥10 的型別皆 <50%。
- **L11-6 ④**：最先壞的是 **`audit invariants --only QueueSegments`**（三個舊段被刪、注入還指著它們會變 `unmapped`）與 **心跳段 3**（`observe(coverage_gaps=None, stale_structure_readings=…)` 的呼叫簽名）；其次是 daily 的 materialize 步驟（旗標改名後舊旗標會讓那一步失敗——`test_daily_task` 的逐項相等要同 commit 改）。

## 8. Step 2.7 讀圖頁 ＋ 個股頁讀圖面板（Z1，R1）

- **改哪裡**：`webapp/materialize.py`（structure_readings kind 的 payload）、`webapp/static/app.js`／`index.html`（`#/structure-readings`、nav「讀圖」）、`briefing/analyst_view/`（新選配面板 `readings`，加進 `OPTIONAL_PANELS`）、materialize 時預算「公司 → 它坐的節點」對照。
- **怎麼改**：
  1. 讀圖頁：每個（節點, unit）一列——單位、判讀、狀態（現行／stale／stale_low／過期，附變化摘要與重讀理由）、到期、引用的原文（片段＋來源）、反證（含 `source`）與它登記的 watch id。沒有讀圖的節點不列（那是走圖第 1 型的事）。
  2. 個股頁 `readings` 面板：由**圖**推這家公司（`co:*`，INV-1：不靠讀圖紀錄裡的 ticker）以 `supplies_to` 或 `develops` 連到的節點 → 那些節點的現行讀圖（兩種單位）→ 每份印判讀、單位、**狀態**。缺席分型：「這家公司坐的層與插槽都還沒有讀圖」（`not_yet_recorded`）／「這次沒讀到圖」（`upstream_unavailable`），不得壓成同一句（L16：`absence_kind` 由產生缺席的程式宣告）。
  3. **選配**：不進 `CORE_PANELS`，不改 readiness（Phase 3 一起換）。
- **怎麼驗**：`python -m webapp materialize --tracked --registry-listed --structure-readings` 前後，既有核心面板的 `--per-panel` 文字 digest **逐字相同**（`scripts/analyst_view_text_digest.py`）；新面板在 SIVE.ST、AXTI、COHR 三檔有內容且狀態與 `--check` 一致；`pytest tests/test_webapp_request_path.py` 綠（request path 不查圖、不跑 LLM）。
- **驗收（層：讀圖——有讀圖面板內容的個股頁數；機制存在與否）**：`webapp status` 列得出 `structure_readings` 且讀圖頁可開（ROADMAP 驗收③的一半）；有讀圖面板內容的個股頁 N 檔（寫實數）。
- **L11-6 ④**：最先壞的是 **既有 73 檔的 readiness 與核心面板文字**——若 `readings` 誤進核心，blocked 數會跳；前後 digest 比對抓得到。

## 9. Step 2.8 pq1 排序（Z2，R1）

- **改哪裡**：`engine_b/priority.py`、`engine_b/cli.py`（刪 `_chokepoint`、`_CHOKEPOINT_MIN_SUBSTITUTABILITY` 與兩處呼叫）、`config/lead_classification.json`、daily triage 的 prompt 組裝與 `triage-apply` 驗證（grep `decision_impact` 找落點；`crons/daily_task.py`／`engine_b/llm_step.py` 之類）、`scripts/backfill_lead_classification.py`、相應測試（`test_engine_b_priority`、`test_triage_apply`、`test_daily_task`、`test_backfill_lead_classification`、`test_engine_b_cli`、`test_engine_b_leads`、`test_source_routes`）。
- **怎麼改**：
  1. `LeadRank` 拿掉 `chokepoint`；`label` 拿掉「瓶頸」；在 `lead_id` 之前加 `first_seen`（lead 的首見時間，舊的先；缺值的排在同級最後並計數，不補假日期——INV-6）。
  2. `decision_impact`：新增 `structure_change`（label「結構或讀圖會變」；hint：「某一層多一家或少一家、合格狀態變、客戶第一次具名、出現新的替代路線——讀圖的判讀可能翻」）；`_order` 改 `exit_condition, candidate_set, structure_change, ranking, unknown, confidence_only`，其中 **`ranking` 與 `structure_change` 同級**（實作上兩者映到同一個名次）；`ranking` 加 `"legacy": true` 與退役註記（G1；舊 lead 保留此值；triage 不再提供）；`candidate_set` hint 改「候選或圖上的公司會多一個或少一個」；`confidence_only` hint 改「判讀不會動，只是更確定」。
  3. triage prompt 只列非 legacy 值；`triage-apply` 對**新**分類的 `ranking` 拒收並計數（心跳「拒收 N」照既有規則）；讀舊 lead 時照常認得 `ranking`。
- **怎麼驗**：`drain` 在 Neo4j 停掉時仍能排序（不再為排序讀圖；`_held` 的 strict 行為不變）；新測試：同級舊的先、`ranking` 與 `structure_change` 同級、`triage-apply` 拒收新 `ranking`；對 2.0 記下的 13 則 pq1 排序重排，**每一則位移都指得出原因**（chokepoint 鍵消失或時間鍵）寫進八欄。
- **驗收（機制存在與否）**：`git grep -n "_chokepoint\|chokepoint_impact"` 在 code 為 0（keep-list 不需要：這不是 Phase 0 八組）；triage 字彙不再提供 `ranking`。
- **L11-6 ④**：最先壞的是 **daily ⑦ 的 triage-apply**——字彙改了而 prompt 沒改（或反過來）會讓當天 triage 整批拒收；本 Step 的 commit 必須在 05:30 之前 push（§0.5），並用 `crons/daily_task.py --dry-run` 或 triage 的離線測試跑一次。

## 10. Step 2.9 Phase 1 留下的三個小修（各 Z1，R1，各一個 commit）

- **2.9a `pending --trigger`**（Phase 1 待決 #13）：`engine_b/todo.py` 的 `pending --trigger` 必須同時帶 `--until <日期>` 或綁一筆 watch（`--watch <ew_id>`），否則拒收並印兩種正確寫法；既有未結案項目不回溯改寫（[586] 已帶 until）。OPERATIONS 用法同步。**L11-6 ④**：最先壞的是互動 session 與 daily-brief skill 裡寫著 `pending --trigger` 的範例句——grep 一次同 commit 改。
- **2.9b 追源排回**（#14＋#17）：`engine_b/leads.py::requeue_trace` **不再寫 `lead["triage"]`**，改追加 `lead["requeued"]`（watch_id、時間、原狀態）；「triage 的寫入者只有 `leads.triage()`」自此字面成立（Phase 1 closeout gate 4 的例外消失）。排回的 lead 若沒有 `triage.classification`：必須有 consumer 補分類且**不重判 go／no_go**——優先用既有 `scripts/backfill_lead_classification.py` 的路徑（先讀它是否需要 LLM、在不在 daily 裡）；分類健康審查把「排回的舊 lead 缺分類」單獨計數並指出 consumer（INV-4），不得把它們排除在審查外。**L11-6 ④**：最先壞的是**心跳「分類層上次成功」**（它排除 requeue 寫的 triage，c8a7dea）與 **pq1 對排回 lead 的排序**（它讀 `triage.classification`）——兩者都要有測試。
- **2.9c watch 的「今天」**（#16）：`engine_b/event_watch.py::_today()` 等所有以日期比較到期的地方改用 `config/daily_routine.json` 的 `schedule.timezone`（台北）；時間戳記仍存 UTC ISO（PIT 不變）。這是 contract 變更：八欄寫明「到期判斷比原本早一天生效」。**L11-6 ④**：最先壞的是 `tests/test_watch_expiry.py` 與 1.2b 改成讀 `_today()` 的兩條測試；以及 audit `Expiry` 的寬限——三者一起跑。

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ① 第一份插槽讀圖 | ledger 裡 `unit=socket` 的紀錄數 0 → ≥1 | 讀圖 |
| ROADMAP ② 走圖每日計數、每型 <50% | 走圖問句在圖上的命中／母體（九型） | 圖 |
| ROADMAP ③ 走圖頁與讀圖頁 | `webapp status` 的 kind：`graph_walk`、`structure_readings` | 機制存在與否 |
| A2 引用 | 現行 v3 讀圖中 moat／volume 的兩半引用都核對得到的份數／份數 | 讀圖 |
| A3 反向路徑 | 反向路徑非空的節點 26 → 19 | 圖（讀圖工具的角度成員） |
| A1 單位 | 既有 10 行 id 重算相同 10／10；現行讀圖按單位的份數 | 讀圖 |
| 2.5 語意 watch | 新讀圖登記的語意 watch 筆數 | registry |
| 2.7 個股頁 | 有讀圖面板內容的個股頁數 | 讀圖 |
| A4、A6、2.9 | 符號與檔案存在與否、拒收測試 | 機制存在與否 |

**沒有任何一個是「幾檔通過某個 filter」。** 走圖第 2 型用了 sub≥4 當母體定義——它決定「要不要問這一題」，不決定任何一檔的去留、排名或尺寸。

## 12. Phase 2 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役（逐檔）；**函式層級**：以 2.0 commit 為起點逐檔比 `def test_` 名稱，拿掉的每一個寫去向（Phase 1 R2 N1）。
2. `python -m audit invariants` 綠。
3. 無未解釋語意 diff：心跳與 2.0 那份逐行對照，每一行增刪有取代行或理由；個股頁既有核心面板 `--per-panel` digest 與 2.7 前相同。
4. 無新 dual authority：走圖與讀圖頁只讀、不落地真相；triage 寫入者只有 `leads.triage()`（2.9b 之後字面成立）。
5. 無 silent drop：走圖每型 0 也印；解析不到的名字有計數；插槽視角的缺席有明示；`triage-apply` 拒收有計數。
6. Point-in-time：讀圖 `--check` 的比對用當次快照；2.9c 之後時間戳仍是 UTC；audit `PointInTime` PASS。
7. lifecycle 可達：`graph_holes` 段有 consumer（research-drain 第三段）；audit `QueueLiveness` 綠；讀圖 expired 仍回得出（`select_reading` 不把過期當不存在）。
8. executable protection：v3 拒收規則各有會紅的測試；`QUESTION_TYPES` 封閉字彙相等斷言；反向路徑成員＝字彙的斷言；`retired_mechanism_grep.py` 九組（含 MCP）三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊 Decision Store 三個 `*.db` sha256 與 `live_choices` 與 2.0 相同；`git diff <2.0> HEAD -- AGENTS.md` 只有 A6 那一行；**Phase 1 驗收③④的回查**（Phase 1 closeout §2 末段）：心跳「未檢 N」是否出現過非 0、`watch.expired` 是否出現過非 0——照實補記（④ 讀圖來源最早 2026-11-18、假設型最早 2027-01-01，大概率仍「已交付、未生效」）。

closeout 報告存 `docs/reports/2026-09-2x-phase2-closeout.md`，附「本 Phase 執行中發現、Phase 3 要決定的問題」（§14 種子＋執行中新增）。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 2 結案）
Target: master 最新 commit；docs/reports/…-phase2-baseline.md、…-phase2-step25-readings.md、…-phase2-closeout.md；
        docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md（§0.4 amendment、§0.6 偏差）
Claimed acceptance: Phase 2 completion gate 九項全過、ROADMAP Phase 2 驗收①–⑤成立（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級的增刪自己比（2.0 commit 起），抽 5 個拿掉的函式確認去向成立
  2. 讀圖 ledger：既有 v1／v2 行的 reading_id 用現行程式重算＝檔內值；至少一筆 unit=socket；v3 每筆 moat／volume 的引用逐條對圖核對
     （邊在快照角度內、片段是該邊 Source.quote 的子字串、插槽護城河的 independent 來源不是供應商本身）；自己造 3 個應拒收的 spec 確認被拒
  3. python -m query.structure prod:supernova --unit socket --quotes：製造者缺席與客戶端原文缺席照實印；
     全圖 result_digest 與 closeout 附的清單一致；反向路徑成員＝schema/vocab.json 的 counter_path_relation
  4. python -m query.graph_walk --json：九型各有 hit／scope；母體 ≥10 的型別 <50%；抽每型 2 筆命中對圖確認問句屬實；沒有任何跨型別合成數字或 top-N
  5. python -m webapp status：有 graph_walk、structure_readings，沒有 coverage；request path 測試綠；個股頁核心面板 digest 與 2.7 前一致
  6. python -m crons.heartbeat --out <temp>：五段照印；段 3 走圖行九型都在（含 0）；段 2 讀圖行有單位拆分
  7. engine_b：git grep _chokepoint 為 0；triage 字彙不提供 ranking、新 ranking 被 triage-apply 拒收；pending --trigger 無 until／watch 被拒；
     requeue_trace 不寫 triage；watch 的今天用 schedule.timezone
  8. python scripts/retired_mechanism_grep.py：九組三個 0；mcp_server/ 不存在；git diff <2.0> HEAD -- AGENTS.md 只有 Local-first 一行
  9. library/private/decision_lab/*.db 的 sha256 與 live_choices ＝ baseline
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫讀圖 ledger
```

### 結案之後：停，不要開 Phase 3

R2 回 GO 後：ROADMAP Phase 2 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：Phase 3 還沒有 plan。
HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **讀圖 id 是 content-addressed 且依版本分支**：v3 加欄位只能加在 v3 的欄位集合裡；把新欄位加進 `_ID_FIELDS` 會讓舊 10 行 id 全變、Phase 1 的 watch 全部變孤兒。
- **快照必須由 `--add` 現跑**（`cmd_structure_reading` 已拒收夾帶快照的 spec）；引用核對也要對**同一份**快照，不要另查一次圖（兩次查詢之間圖可能變）。
- **`digest_changed` 分不出「圖變了」與「走訪清單改了」**（`sr_6ad5c884eb7bc3fb` 已記）：2.2 會讓 InP 基板轉 stale，**那是預期**；不要為了讓它回 current 去動 digest。
- **插槽的附加段不得進 digest**：一進去，逐字篇數就會讓 staleness 恆亮（AGENTS：會隨我們多讀文件單調上升的指標）。
- **`query/` 不得 import `alpha/`**（`tests/test_layer_separation.py`）：讀圖狀態由 `webapp/materialize.py` 組進走圖，或以參數注入 `query/graph_walk.py`。
- **evidence 與 origin 解析有唯一 owner**（`query/bottleneck.py::classify_evidence`、`company_id_for_origin`）：`query/structure.py` 曾因自己不經過它而印錯 430 條（L16）；走圖第 2 型與 v3 的 `independent` 核對都用它。
- **`webapp/contracts.py` 的 kind 是封閉字彙**：改名要同步 materialize、api、app.js、`webapp status` 提示、心跳 `_load_state`、測試；舊 `coverage.json` 留在磁碟當孤兒（同 Phase 0 的 basket.json）。
- **`engine_b/queue_segments.py` 是封閉字彙且 audit 注入計數**：刪段時 `audit/checks.py` 與心跳 `observe()` 的注入參數一起改，否則 `unmapped` 或 TypeError。
- **daily 的 `DAILY_STEPS` 有逐項相等測試**：改 materialize 旗標要同 commit 改 `tests/test_daily_task.py`，並在 05:30 前 push。
- **triage 字彙改動影響無人值守步驟**：prompt 與 `triage-apply` 驗證必須同 commit；舊 lead 的 `ranking` 必須仍讀得到。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad／`%TEMP%`；程式碼不要放 heredoc，用 Write 成檔再跑；子行程用 `sys.executable`。
- **Neo4j 要開**：`query.structure`、走圖、整合測試都需要；讀不到圖時各處印 `upstream_unavailable`，不印 0、不印 current。
- **不要把「供應商數」當瓶頸性證據**：走圖第 1 型用 1–3 家定義「薄」是**問句母體**，不是結論；65% 單供應商量到的是我們讀了誰的文件（決定紀錄 §1.1）。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. **`supplies_to → prod:` 的兩義**（R-4）：製造者與零件供應商共用一個關係；2.5 若提了 pq2，結案時寫處置狀態；schema 層要不要另給一個關係（Phase 4 層中心選源時一起定）。
2. **read model 的 `get_bottlenecks`（sub≥4 成員）**：個股頁 argument「鏈」段仍用它；Phase 3 面板重排時決定留不留（Phase 0 偏差 #33 的另一半）。
3. **讀圖面板升核心**與 readiness 換（Phase 3，ROADMAP 已排）；Phase 0 偏差 #16「`review_required` 的路接回讀圖面板」一併處理。
4. **`tech:cw_dfb_laser` 讀圖 2026-10-18 到期**與反證出處（#19）若 2.5 沒做，列進研究並行。
5. **走圖母體 <10 的型別**（`reading_stale` 等）命中率只印不判——讀圖份數長大後要不要回到 <50% 規則。
6. Phase 1 closeout §7 未併入本 Phase 的各題（§0.3 最後一條列的編號），照實帶到 Phase 3 的 plan session。
7. `argument` 面板標題（Phase 0 延下來、Phase 1 定「Phase 2／3」）：本 Phase 沒有重排面板，延 Phase 3。
