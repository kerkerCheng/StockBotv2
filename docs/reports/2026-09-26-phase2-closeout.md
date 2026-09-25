# Phase 2 讀圖兩種單位 ＋ 走圖——結案報告（2026-09-26）

> plan：[`docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md`](../plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md)（amendment A1–A6 見 §0.4、執行偏差 #1–#19 見 §0.6）；
> 基準：[`2026-09-25-phase2-baseline.md`](2026-09-25-phase2-baseline.md)；Step 2.5 收據：[`2026-09-25-phase2-step25-readings.md`](2026-09-25-phase2-step25-readings.md)；
> 決定紀錄 G1–G12：[`docs/brainstorms/2026-09-22-graph-first-direction-decision.md`](../brainstorms/2026-09-22-graph-first-direction-decision.md)。
> 本檔每個數字都附查證命令；數的是**讀圖 ledger 的紀錄與引用、走圖問句在圖上的命中／母體、APP 的 state kind、機制存在與否**（plan §11），
> 沒有一個是「幾檔通過某個 filter」。

## 0. Phase 2 做了什麼（20 個 commit，2026-09-25 → 09-26）

| Step | commit | 一句話 |
|---|---|---|
| 2.0 | 475e167 | 基準快照（2520 測試；invariants 13 PASS；讀圖 10 行 id 重算 10／10；全圖 278 節點 digest；§0.2 全數重跑一致） |
| 2.1 | ba47419、6da4892、6053c25 | Graph MCP 退役：`mcp_server/` 與只守它的三個測試檔刪除、AGENTS Local-first 一句照 A6 改寫、殭屍 grep 第九組（所有 tracked 檔）；R2-a GO |
| 2.2 | 73d8c53 | 反向路徑只收 `competes_with`，`schema/vocab.json` 的 `counter_path_relation` 成為唯一來源；digest 變動恰好＝預先算好的 14 個節點 |
| 2.3 | cb6c612 | 讀圖契約 v3：`unit`（層／插槽）、`citations[]` 兩半逐字由寫入端對同一份快照核對、反證 `source`；v1／v2 id 10／10 不變 |
| 2.4 | 12dbc8c、f1fe714 | 插槽視角（誰的產品、客戶端原文，不進 digest）＋分單位 staleness；R2-b CONDITIONAL_GO → B1（製造者只認 `develops`）已修 |
| 2.5 | c9390b9、647245d、4ab71d4、974e2c9、c0db0a1、eb2a7ce | （強模型、研究）第一份插槽讀圖 2 份、層讀圖 2 份重讀成 v3；工具毛病三個當下修；[651]–[654] 與衝突決策收據 |
| 2.6 | be7a85e | 走圖：九型問句各自「命中／母體」、`graph_walk` kind 取代 `coverage`、三個佇列段併成 `graph_holes`、心跳段 3 一行九格 |
| 2.7 | 1f80ac3 | 讀圖頁 `#/structure-readings` ＋ 個股頁讀圖選配面板（印狀態）；併做待決 #13、#22 |
| 2.8 | a1640db | pq1 排序刪「瓶頸」鍵（drain 不再為排序讀圖）、`decision_impact` 的 `ranking` 標 legacy 同級、`structure_change` 新增、加首見時間鍵 |
| 2.9a | a124746 | `pending --trigger` 必帶 `--until` 或綁一筆會叫醒它的 watch（`--watch`） |
| 2.9b | 28057cf | 追源排回不再寫假 triage（只追加 `requeued`）；缺分類的排回 lead 在健康審查單獨計數並指出 consumer |
| 2.9c | c00896e | watch 的「今天」改排程時區（台北）日期；同一個 `_today()` 給 disproof、pq2 `until` 叫回、audit Expiry |
| 結案 | 354b315、（本 commit） | 本報告（R2 前）；結案 R2 GO 後處置 non-blocking、ROADMAP Phase 2 ✅、plans README completed |

## 1. 九項 completion gate（plan §12）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級拿掉的每一個有去向 | ✅ **2590 passed, 1 skipped**（基準 2520 passed）；測試檔 **183 → 184**＝＋4（`test_graph_walk`、`test_heartbeat_graph_walk`、`test_migrate_relation_rejudge_additions`、`test_structure_reading_v3`）−3（`test_engine_c_mcp`、`test_graph_mcp_manual`、`test_leads_mcp`，2.1）；改名 1（`test_webapp_coverage_watches` → `test_webapp_graph_walk_watches`）。函式層級：拿掉 **29**、新增 **91**，逐個去向見 §3 | `python -m pytest -q`；`git diff 475e167 HEAD --name-status -M -- tests` |
| 2 | `python -m audit invariants` 綠 | ✅ **13 PASS／0 FAIL（共檢查 4832 筆）**；`QueueSegments` 讀得到 `graph_holes=60`（原三段在稽核裡恆「未讀到」） | `python -m audit invariants` |
| 3 | 無未解釋語意 diff | ✅ **心跳**與 2.0 那份逐行對照：段 2 讀圖行「結構讀圖 2 份｜現行 2」→「結構讀圖 4 份（層 2／插槽 2）｜現行 4」（取代行＋單位拆分，2.6）；段 3 新增「走圖：」一行九格（取代原本只在非 0 時出現的「＋結構讀圖待重讀 N」）；較昨 diff 的封閉鍵多九個 `walk.*`；其餘差異是資料與時間（今天 daily 未跑）。**個股頁**：核心面板（brief／argument／research）文字 digest 2.7 前後**逐字相同** `b620cdb0be9cb3a1`（73 檔）、readiness 73／73 相同 | `python -m crons.heartbeat --out <tmp>`；`python scripts/analyst_view_text_digest.py --per-panel` |
| 4 | 無新 dual authority | ✅ 走圖、讀圖頁、讀圖面板都只讀、artifact 是可重建的 derived cache；讀圖狀態只有一份算法（`alpha/providers/structure_readings.py::reading_status_rows`，讀圖 artifact 與走圖共用）；**triage 判斷的寫入者只有 `leads.triage()`**（2.9b 之後字面成立——`grep -n 'lead\["triage"\] =' engine_b/leads.py` 另兩處是回到 pending 時清成 `None`，不是判斷）；「今天」只有一個定義（`event_watch._today()`） | `git grep -n 'lead\["triage"\] =' engine_b/leads.py` |
| 5 | 無 silent drop | ✅ 走圖每型 0 也印、讀不到印 `upstream_unavailable`（`test_summary_line_prints_zero_and_absence_differently`）；registry 解析不到的名字另計（第 5 型 `unresolved_names`）；`prod:` 0 家節點只計數；插槽視角缺席明示（`SOCKET_NO_MAKER`／`SOCKET_NO_CUSTOMER_QUOTE`）；`triage-apply` 對 legacy `ranking` 拒收並計入拒收數；排回缺分類單獨計數（`requeued_unclassified_count`） | 各測試見 §3 |
| 6 | Point-in-time | ✅ 讀圖 `--add` 的引用核對對同一次唯讀查詢的快照（`load_snapshot_with_quotes`）；2.9c 後時間戳仍存 UTC ISO，只有「今天」換成排程時區；`audit PointInTime` PASS | `python -m audit invariants --only PointInTime` |
| 7 | lifecycle 可達 | ✅ `graph_holes` 的 consumer 是 research-drain 第三段（skill 真的提到 `query.graph_walk`，`test_the_queue_segment_points_at_a_consumer_that_really_mentions_it`）；`QueueLiveness` PASS；讀圖過期仍回得出（`select_readings` 不把過期當不存在；走圖第 4 型以 `expired` 命中） | `python -m audit invariants --only QueueLiveness` |
| 8 | executable protection | ✅ v3 拒收規則各有會紅的測試（`tests/test_structure_reading_v3.py`）；`QUESTION_TYPES` 封閉字彙相等斷言；反向路徑成員＝字彙斷言；`query/` 只有一處 import `alpha/` 的斷言；殭屍 grep **九組三個 0**；新測試抽樣做過突變（走圖第 4／5 型、#22 兩端、排回的事件判別）都會紅 | `python scripts/retired_mechanism_grep.py` |
| 9 | 驗收數的是 §11 的層 | ✅ §2 每個數字都是讀圖 ledger、圖、APP kind、機制存在與否 | — |

**另核對（plan §12）：**
- 舊 Decision Store 三個 `*.db`：sha256 與 `live_choices` 與基準**逐字相同** ✅（`backup_pre_v8…` `e887b3d4…` 0；`backup_pre_v9…` `af3dc690…` 1；`decision_lab.db` `e99d1c79…` 1；`?mode=ro` 連線計數）。
- `git diff 475e167 HEAD -- AGENTS.md` **只有 A6 那一行**（Local-first：「cloud＋MCP 是備援，新核心不得依賴 MCP」→「遠端操作走 Remote Control 連本機 session，不開對外的寫入入口」）✅。
- **Phase 1 驗收③④回查**（Phase 1 closeout §2 末段）：心跳快照目前只有 2026-09-25 一份，`semantic.pending_check`＝0、`watch.expired`＝0；registry 現值同為 0（`python -m engine_b.event_watch counters`：active 123、semantic 在盯 36、expiry_unresolved 0）。**③④仍是「已交付、未生效」**——語意 watch 還沒有被一手文件叫醒過；最早的讀圖來源到期在 2026-11 之後。較昨 diff 的封閉鍵第一次變非 0 的那天 Daily 會自己印。

## 2. ROADMAP Phase 2 驗收①–⑤

| # | 驗收 | 結果 | 層 | 查證 |
|---|---|---|---|---|
| ① | ledger 出現第一份 `unit=socket` 讀圖 | ✅ **0 → 2**（`prod:supernova`、`prod:els_8ch_module`，皆 `undecided`，Step 2.5）；ledger 共 14 行；現行按單位：層 2／插槽 2 | 讀圖 | `python -m alpha structure-reading prod:supernova --unit socket --check` |
| ② | `graph_holes` 每型每日印命中／母體，母體 ≥10 的型別觸發率 <50% | ✅ 九型：薄層沒人讀 **4／13**（31%）、獨家且自報 **2／13**（15%）、供給側未填 2／7（母體 <10，只印不判）、讀圖該重讀 0／4（同）、lead 點名不在圖 **4／10**（40%）、供貨走不到錨 **6／51**（12%）、沒人供應 **9／129**（7%）、建模待補 **10／181**（6%）、重複節點 **23／188**（12%）——**母體 ≥10 的七型全部 <50%**，不需收窄；心跳段 3 每天一行九格 | 圖 | `python -m query.graph_walk --json`；`python -m crons.heartbeat` 段 3 |
| ③ | 走圖頁與讀圖頁在 `webapp status` 列得出 kind | ✅ `graph_walk`、`structure_readings` 都列得出、`coverage` 不再列；兩頁以 headless Edge 實際渲染過（九個區塊／4 份讀圖含引文與 watch id） | 機制存在與否 | `python -m webapp status` |
| ④ | 現行 v3 讀圖中護城河／量的兩半引用都核對得到 | ✅ **2／2**（`mat:inp_substrate` 層 volume、`tech:cw_dfb_laser` 層 volume：`verify_citations` 對現在的圖 0 問題、需求側與供給側各至少一段）；兩份插槽讀圖是 `undecided`（不強制引用） | 讀圖 | §0 closeout 事實腳本（`verify_citations(record, load_snapshot_with_quotes(node)[1])`） |
| ⑤ | 反向路徑非空的節點 26 → 19 | ✅ **19**（tech／mat／prod 口徑；全節點 42；2.2 當下即為此數，[653]／[654] 入圖後不變） | 圖 | 對每個節點 `build_structure(node, _load_edges()).angles["counter_path"]` 非空計數 |

## 3. 拿掉的測試函式與去向（475e167 起；plan §0 第 5 條）

| 檔 | 拿掉 | 去向 |
|---|---|---|
| `test_engine_c_mcp.py`（刪檔，6）、`test_graph_mcp_manual.py`（刪檔，5）、`test_leads_mcp.py`（刪檔，5）、`test_layer_separation.py`（5 個 MCP 相關） | 21 | 守的 `mcp_server/` 已不存在（2.1）；「不得有對外寫入入口」改由殭屍 grep 第九組（所有 tracked 檔 MCP 字樣扣 keep-list 為 0）守。R2-a 已抽 5 個確認 |
| `test_structure_reading.py::test_constrained_by_answers_demand_side_and_next_layer_not_only_counter_path` | 1 | 改名翻面為 `…_not_counter_path`（A3：`constrained_by` 不在反向路徑）＋ `test_counter_path_members_are_the_vocabulary`、`…_fails_closed_when_missing`（2.2） |
| `test_webapp_coverage_watches.py` 四條（counts／identity／scope／固定文字同源） | 4 | 檔改名 `test_webapp_graph_walk_watches.py`：`test_graph_walk_artifact_copies_every_type_and_adds_no_total`、`…_identity_tracks_who_is_hit_not_the_wording`、`…_scope_limit_travels_with_the_data`、`test_duplicate_hits_keep_their_verbatim_on_both_sides`；`test_fixed_text_has_one_home_and_the_markdown_prints_it` 守的是「coverage artifact 與 markdown 同源」——artifact 退役後**前提消失**，不是改由別處守（R2 non-blocking #2 更正；原句寫「由 `tests/test_coverage_gaps.py` 繼續守」是過度說法） |
| `test_decompose_proposals.py::test_shipped_sector_anchors_load_and_coverage_nodes_extract` | 1 | 改名 `…_walk_nodes_extract`（節點清單改讀 `graph_walk` artifact，欄位缺席 raise） |
| `test_engine_b_priority.py::test_chokepoint_impact_lifts_supply_chain_leads_over_generic_commentary` | 1 | **機制刻意退役**（A4）：斷言翻面為 `test_chokepoint_is_no_longer_an_input_and_lead_time_decides_within_a_tier`（有人把瓶頸鍵加回來會紅） |
| `test_engine_b_cli.py::test_trace_requeue_restores_latest_classification_from_history` | 1 | **行為刻意改變**（2.9b）：翻成 `test_trace_requeue_leaves_classification_to_its_consumer_and_never_rejudges`（缺分類交給 backfill 的確定性還原、consumer 真的接得住）＋兩條新測試 |

## 4. 執行中發現、實際做了什麼（偏差摘要；全文在 plan §0.6）

- #11 稽核直接跑走圖 authority 算 `graph_holes`（不讀 derived cache，也不再恆「未讀到」）；代價：`QueueSegments` 那一格依賴 Neo4j、多約 4 秒。
- #12 plan 以為 `tests/test_layer_separation.py` 有「`query/` 不得 import `alpha/`」——沒有；現在由新測試守「只有 `graph_walk.collect()` 一處」。讀圖狀態的算法從 `webapp/materialize.py` 原樣搬到讀圖 provider，兩個消費端共用。
- #13 第 7／8／9 型母體取「這一題對誰問得出來」（129／181／188）；第 9 型命中是候選對、母體是節點（單位不同，已寫在 `scope_rule`／`hit_rule`）。
- #14 **佇列段 `graph_holes` 的計數＝九型命中之和（60）**——只在 `observe()`／稽核那一行，用來回答「這一段有沒有工作」；心跳、APP、CLI 一律九格各自印、沒有加總欄位。**請 R2 判斷要不要改成「有命中的型別數」**。
- #15 一條在 HEAD 就是紅的測試（[654] 入圖後夾具過期）、materialize 提示印底線 kind（貼了會失敗）、心跳重讀理由帶單位。
- #16 讀圖面板是唯一來源不在 read model 的 panel：`build_analyst_view(view, *, readings=None)` 注入；兩條「panel 狀態抄自 read model」測試把它列為 `INJECTED_PANELS` 例外，另有三條專屬測試。
- #17 #22 的製造者從同一次查詢的逐字鍵取（不改快照格式）；真實資料 0 筆變動。
- #18 13 則 pq1 位移 0：被拿掉的「瓶頸」鍵與「持股關聯」鍵在這批資料上共線。
- #19 「今天」另有三處同義的比較一起改；順手修「追源到期結案今日」拿 UTC 前 10 碼比本地今天的少算。

## 5. Phase 3 要決定的問題（plan §14 種子＋執行中新增；照實帶到下一個 plan session）

**本 Phase 執行中新增：**

1. **`graph_holes` 段的計數語意**（偏差 #14；結案 R2 判定「形式上是跨型別合成、不違反 §0 第 7 條的立法目的、不擋結案」）：它是**異單位加總**（第 9 型是候選對、其他是節點或 lead），而且不只在 `observe()`／稽核那一行——`queue_segments.observe()` 的 `research_total` 會再加一次（該欄位目前沒有 production consumer），心跳 `build_queue` 也自己算了一份傳進 `observe()`（與 `audit/checks.py::_graph_holes` 兩份實作）。R2 建議二擇一：段計數改「有命中的型別數」，或段計數留 int、稽核那一行改印逐型字串（同 `summary_line`）並刪 `research_total` 或排除 `graph_holes`。
2. **3 則排回的舊 lead 缺分類**（`lead_44ce140c…`、`lead_f6d7fdd6…` AXTI 8-K、`lead_9b9d5797…` $SIVE）：沒有可還原的歷史 receipt，consumer 是**互動 session 的語意補分類**（`scripts/backfill_lead_classification.py --from-json … --apply`，不重判 go／no_go）；在做之前 daily ⑦c `classification-health` 每天照舊亮燈（exit 2），drain 扣住它們。**這是研究動作，不是開發**。
3. **lead 實體的 ticker 解析缺口**（走圖第 5 型的「registry 解析不到」列出 `SIVE`、`ASML`、`AMZN`、`STM`、`SOI`…12 個）：`SIVE` 在 registry 是 `SIVE.ST`，cashtag 解析不到＝INV-1「ID 沒解析對」，不是圖中無此公司。要不要讓 `company_id_for_ticker` 認無後綴的 cashtag（有歧義風險），是 identity 的決定。
4. **稽核 `QueueSegments` 那一格依賴 Neo4j**（偏差 #11）：圖沒開時 `graph_holes` 印「未讀到」並註明——可接受，還是要回到「稽核不讀圖」？
5. **`python -m query.coverage_gaps`／`query.duplicate_nodes` 兩支 CLI 仍在**（走圖第 7–9 型重用它們的函式）；APP 的 `coverage.json` 留在磁碟當孤兒（同 basket.json）。要不要退役 CLI，隨 Phase 3 的面板重排一起看。
6. **#22 的修正要 #20 才會生效**：O-Net／Ayar 的 origin 解析不到（71／100 家公司沒有 `display_name`），客戶端原文目前一段都認不出來。

**plan §14 種子（未在本 Phase 解決，原樣帶過去）：**

7. §14 #1 `supplies_to → prod:` 兩義：schema 要不要另給一個關係（Phase 4 層中心選源時一起定；[654] 已用「只加 `develops`」解掉插槽視角那一半）。
8. §14 #2 read model 的 `get_bottlenecks`（sub≥4 成員）仍餵個股頁 argument「鏈」段——Phase 3 面板重排時決定留不留。
9. §14 #3 讀圖面板升核心與 readiness 換（Phase 3，ROADMAP 已排）；Phase 0 偏差 #16「`review_required` 的路接回讀圖面板」一併處理。
10. §14 #5 走圖母體 <10 的型別（`supply_unfilled` 7、`reading_stale` 4）只印不判——讀圖份數長大後要不要回到 <50% 規則。
11. §14 #6 Phase 1 closeout §7 未併入的各題（#1、#2、#3、#5、#6、#7、#8、#9、#10、#11、#12、#15、#18）。
12. §14 #7 `argument` 面板標題（Phase 0 延下來）。
13. §14 #8 本機 Research Action apply 入口（已排 ROADMAP 旁支）；#9 `_finalize_research_action_impl` 無 production 呼叫端；#10 `verify_test_nonvacuity.py` 幾條突變指向已不存在的測試。
14. §14 #11 `wake_reading` 與 `reread_reasons` 以節點為單位（等第一個同時有層與插槽讀圖的 prod 節點出現）；#15 插槽的客戶重讀 watch 改綁製造者——**觸發條件（[654] 入圖）已成立**，與 #11 一起處理。
15. §14 #12 延伸（未定）：「客戶高管在供應商新聞稿裡具名」算不算插槽護城河要的客戶端印證——**契約問題，要使用者決定**。
16. §14 #16 兩條新語意 watch 叫不醒（`ew_0138` 只綁私人公司、`ew_0140` 只綁港股）——涵蓋面的決定。
17. §14 #17 `classify_evidence` 把支撐屬性值的引文算成邊的外部印證（Phase 4）；#18 `prod:` 一表多義；#19 SuperNova 唯一的 substack 原文未定日；#20 聯合公告偵測對 71／100 家無效（改了會動很多邊的證據等級——先量）；#21 OpenLight 兩個 ID（重複節點研究題）。

## 6. 使用者動作（非阻擋）

- claude.ai 設定裡的 `stockbotv2-graph` connector 仍在工具清單（後端 404）——移除是使用者在 claude.ai 的動作（2.1 已列）。
- 上面 §5 第 2 條的 3 則補分類（研究，互動 session）。

最後一次全套：`python -m pytest -q` → **2590 passed, 1 skipped**（2026-09-26 結案前）。

## 7. 結案 R2（2026-09-26；乾淨 context 的 reviewer，使用者已常規 opt-in）

**Verdict：GO**——plan §12 的九項 reviewer 自己重跑全數成立（2590 passed；audit 13 PASS；ledger 14／14 id 重算相同；
v3 volume 引用 20／20 逐條對圖；自造 6 筆應拒收的 spec 全被拒、對照組寫入成功、真實 ledger sha256 前後不變；走圖九型逐型抽樣對圖屬實；
核心面板 digest `b620cdb0be9cb3a1`；triage-apply 端到端拒收 ranking；Decision Store 三檔相同）。**Blocking：無。**

Non-blocking 的處置：

| # | 內容 | 處置 |
|---|---|---|
| 1 | `graph_holes` 是異單位加總，且另在 `research_total` 與心跳各算一次（closeout 原寫「只在 observe()／稽核那一行」不精確） | §5 #1 改寫成精確描述＋R2 的兩個方案，**Phase 3 決定**（不擋結案） |
| 2 | §3 `test_fixed_text_has_one_home…` 的去向說法過度 | §3 改成「前提消失」 |
| 3 | 插槽「扣掉製造者」的正向面只有單元測試守，真實資料驗不到（#20） | 已在 §5 #6；#20 修好後用真實資料再驗 |
| 4 | 小瑕疵：plan §0.6 偏差 #6 排在 #5 前；`ANGLE_KEYS` 註解寫「五個角度」實際 4 個 key（anchor 另計）；`coverage.json`／`ranking.json` 磁碟孤兒 | 照實記錄；前兩者是文字，不動行為，留給下一次動到那兩處的 Step 順手改 |

## 8. 結案後的回歸修正（2026-09-26 06:30 後；使用者要求處理 3 則排回 lead 與 QueueLiveness 紅燈時發現）

2.9b（排回不再改寫 `triage.decided_at`）漏掉兩個把 `decided_at` 當「進 pq1 時間」的消費端（L11-6 ④沒列到）：
①稽核 QueueLiveness 把今早 daily 新式排回的 `lead_55bd36e6…` 報成「16 天沒人取」（真實 FAIL）；
②重新停放時建追源 watch 的 `created_at` 會退回原始 triage 時間，剛觸發排回的 lead 可能立刻再叫醒它。
修法：`engine_b/leads.py::last_entered_pq1_at`（triage 與最後一次排回取較晚）一個定義、兩處共用；
QueueLiveness 線索側原本沒有任何測試，補兩條（突變驗過會紅）。修後 invariants 13 PASS、2592 passed。
