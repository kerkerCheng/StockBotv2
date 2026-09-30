# Phase 3 候選狀態 ＋ 三題——結案報告（2026-09-30）

> plan：[`docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md`](../plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md)（amendment A1–A7 見 §0.4、執行偏差 #1–#41 見 §0.6、P0 處置見 §0.7）；
> 基準：[`2026-09-29-phase3-baseline.md`](2026-09-29-phase3-baseline.md)；回填：[`2026-09-29-phase3-step32-backfill.md`](2026-09-29-phase3-step32-backfill.md)；
> 3.5 收據：[`2026-09-29-phase3-step35-narratives.md`](2026-09-29-phase3-step35-narratives.md)；3.7 收據：[`2026-09-30-phase3-step37-stock-page.md`](2026-09-30-phase3-step37-stock-page.md)。
> 本檔每個數字都附查證命令；數的是**敘事 ledger、等待 registry、個股頁稽核區（Engine C 觀測的投影）、trade_log、走圖問句、機制存在與否**（plan §11），
> 沒有一個是「幾檔通過某個 filter」——候選板「可開」「非倍率候選」的檔數只印不驗收。
> 證據由一次唯讀 workflow 收集（HEAD `5ae780a`、基準 `559414e`；變異只在 `git archive` 匯出到 `%TEMP%` 的副本上做，repo `git status` 前後皆空），
> 本報告 commit 另含三處結案修正（§1 gate 8 的註）。

## 0. Phase 3 做了什麼（19 個 Step commit＋2 個結案 commit，2026-09-29 → 09-30）

| Step | commit | 一句話 |
|---|---|---|
| 3.0 | 559414e | 基準快照（2592 測試／184 檔；invariants 13 PASS；v1 短評 id 7／7；73 份個股頁 digest；歸零旗標 67／70／0／0） |
| 3.1 | ebab3d0、50954a9、61f0377 | Phase 2 帶過來的三個小修：`graph_holes` 段計數改「有命中的型別數」；走圖第 5 型用 lead 的 ticker 規則（`unresolved_names` 12→10）；第 9 型印兩端逐字並退役 `coverage_gaps`／`duplicate_nodes` 的 CLI |
| 3.2 | aaf926b、42f2596、b403e78、4c8edc2 | Engine C 機械歷史表（價格／公司行動／財報，as-of 讀法在 `shared/as_of.py`）、正式庫一次回填＋daily 增量、going concern 結構化欄位；R2-c CONDITIONAL_GO → 條件修正後 GO |
| 3.3 | 1a4e640 | 三題稽核區（`alpha/three_questions.py` 純函式、取數只在 Engine C）；主題等權組 ledger（寫入綁 pq2）；邊緣判定 |
| 3.4 | 4e96223、0d4c7ad、6dd0fd4 | 短評 v2 契約（七格改題、`rides`／`disproof`／`answers`／`candidate_state`）、敘事來源的語意 watch、`narrative_rewrite` 佇列段；R2-a CONDITIONAL_GO → 條件修正後 GO |
| 3.5 | 9945509 | （強模型、研究）v2 敘事四份：AXTI 等回落、COHR／LITE 不要（非邊緣）、SIVE.ST 缺 X；主題等權組與 going concern 的 pq2 [656]–[661] |
| 3.6 | f7f1711、d73247f | 候選狀態推導（一個 `derive_row`）與候選板 `candidates` kind、心跳段 2／3／4；`hard_caps` 判別函式公開（#17 預先授權，只匯出） |
| 3.7 | f942d26 | 個股頁：首屏候選狀態＋三題三個字、稽核區三題、讀圖升核心、argument 鏈段改讀騎的讀圖需求側、downside 反證連 watch |
| 3.8 | be73d4e、ec8f19b | `record_trade.py` 研究收據（#16 預先授權）：缺 v2 敘事的 alpha 買進 fail closed（exit 4）、兩種放行互不放行；R2-b 兩位都 GO |
| 3.9 | 5ae780a | 新管線 full chain（夾具版）；真 runtime 那份 27 passed＝3.0，一條未動 |
| 結案 | 889bc0e、（R2 GO 後的 commit） | 本報告；殭屍 grep keep-list 腐壞 1 條、docstring 指向、`indirect` 斷言三處結案修正；R2 GO 後 ROADMAP Phase 3 ✅、plans README completed |

## 1. 九項 completion gate（plan §12）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級拿掉的每一個有去向 | ✅ **2867 passed, 1 skipped**（基準 2592 passed, 1 skipped）；測試檔 **184 → 194**＝＋10（`test_engine_c_history`、`test_three_questions`、`test_three_question_inputs`、`test_theme_cohort_pq2`、`test_narrative_v2`、`test_candidates`、`test_webapp_candidates`、`test_stock_page_phase3`、`test_record_trade_receipt`、`test_phase3_full_chain`）－0。函式層級（`file::function`，對 3.0 名單）：新增 **228**、拿掉 **1**，去向見 §3 | `python -m pytest -q`；`git diff 559414e HEAD --name-status -- tests` |
| 2 | `python -m audit invariants` 綠 | ✅ **13 PASS／0 FAIL（共檢查 4877 筆）**；`QueueSegments` 多一段 `narrative_rewrite=0`；QueueLiveness 171 筆（基準 161） | `python -m audit invariants` |
| 3 | 無未解釋語意 diff | ✅ **心跳**（與 3.0 那份逐行對照，基準 57 行、今日 68 行）：69 個變動行全部歸類——Phase 3 程式預期 13 行（APP artifact 7→8 份、候選行、持股解析不到、三題行、敘事該重寫、watch 到期行多「等敘事重寫」、刪「賭注帳」行、歸零旗標改印盞數）；3.5 寫入的資料 12 行（反證在盯 36→37、pq2 [656]–[661]、事件監看 147→151）；其餘是日期、價格與營運漂移（今天 07a／10b rate_limited）；**未解釋 0**。**個股頁**（逐面板 digest，73 檔、292 個面板鍵相同）：brief 73／73 變＝偏差 #10（69 檔沒有短評的列 v2 七題）＋3.5 四份 v2；argument 73／73 變＝3.7 偏差 #33（標題）與 #30（鏈段）＋SIVE.ST timeline 1 段（基準前的 thesis 複查資料）；our_bet 4／73＝3.5；**research 17／73 字面變了，排除 `notes::` 後 73／73 相同**——差異全是每日共識 notes（「共識變動…」「首次出現於…」），產生端 `alpha/refresh/resolver.py` 自基準無 commit，Phase 3 前的備份裡同一種 notes 本來就每天變（判準寫明：research 面板「排除 notes 後不變」） | `python -m crons.heartbeat --out <tmp>`；`python scripts/analyst_view_text_digest.py --per-panel` |
| 4 | 無新 dual authority | ✅ 候選狀態只有 `alpha/providers/candidates.py::derive_row`（候選板與個股頁在 materialize 共用一份 context 呼叫它；心跳與收據只讀 `candidates` artifact）；持股身分解析只有 `portfolio/holdings.py::resolve_holding(s)`（候選板、收據、`engine_b/cli.py::_held` 共用；`_held` 仍含 beta、預設 store 讀不到 fail closed）；watch 歸屬只有 `engine_b/narrative_watches.py::attributed_watches`（可開前提③、寫入端、downside、收據）；本 Phase 新增的 alpha／beta 判別只走 `risk.hard_caps.is_beta_symbol`／`beta_instrument_for`（`risk/snapshot.py:85` 是既有第二份、自基準 0 行 diff，列 §5）；三題取數只在 `engine_c/three_question_inputs.py`＋`checklist.get_wipeout_inputs`，判定只在 `alpha/three_questions.py`／`alpha/wipeout.py`（候選板 rollup 與 73 份個股頁逐 row_key 比對 0 不一致）；台股營收只住 `monthly_revenue_observations`（`fundamental_history` 台股 0 列；343＝7 檔 × 49）；主題等權組只有 `library/private/alpha/theme_cohorts` 一本；lead 與走圖共用 `engine_b.entities.resolve_lead_ticker` | `git grep -n "derive_row\|resolve_holding\|attributed_watches"`；`python -m pytest -q tests/test_candidates.py tests/test_stock_page_phase3.py` |
| 5 | 無 silent drop | ✅ 候選板 counts 十格相加＝宇宙 73（`no_narrative` 69、`legacy` 0、`precondition_failed` 0、`edge_unmeasurable` 0；`holdings.unresolved`＝TYO:7803），心跳段 2 每格 0 也印；三題 695 行中 value 279、缺席 416 **每一行都有 `absence_kind` 與 reason**（`line()` 缺 kind 或缺 reason 在建構時 raise）；回填報告逐檔列缺什麼 | `library/private/app/state/candidates.json`；`python -m crons.heartbeat` 段 2 |
| 6 | Point-in-time | ✅ 歷史表的 PIT 測試 9 條（`filed` 之前拿不到、`fetched_at` 不決定可用日且原始碼不含 `fetched_at <=`、台股月營收的可用日＝法定期限、`published_at` 恆 None、今天與歷史同一個函式所以晚申報在申報前看不到）；`audit PointInTime` PASS（207／220、677／695），`get_bottlenecks` 探針仍在 `audit/checks.py:1324`、自基準未改 | `python -m pytest -q tests/test_engine_c_history.py tests/test_engine_c_monthly_revenue.py tests/test_three_questions.py tests/test_stock_page_phase3.py -k "latest_filing_known or fetched_at_never or statutory_deadline or price_series_reads_as_of or tenth_of_next_month or never_becomes_published_at or late_filing_is_invisible or point_in_time_not_upstream"`（9 passed）；`python -m audit invariants --only PointInTime` |
| 7 | lifecycle 可達 | ✅ `narrative_rewrite` 段 consumer＝research-drain（skill 真的寫到 `narrative_rewrite` 與 `acknowledged_touched`，測試斷言）；`wake_brief` date watch 到 `until` 進 `narrative_rewrite` 不進假設對照、到期不鑄 `watch_decision`；連結斷餵同一段；QueueLiveness、Expiry PASS | `python -m audit invariants --only QueueLiveness`；`python -m pytest -q tests/test_narrative_v2.py -k "narrative_rewrite or wake_brief"` |
| 8 | executable protection | ✅ 八項各有會紅的測試（變異在副本上做）：v2 拒收（新寫 v1、首屏禁字）、`open` 前提（讀圖不現行，候選端與寫入端各一）、`held` 不可宣告（兩道防線，兩道都拿掉才紅——任一道單獨存在時不變式都守得住）、供給側檢查、重寫須處置觸及（supersede／retract 兩條紅）、收據 fail closed、兩種放行互不放行（M7a、M7b 各紅）、三題無門檻（加 `threshold`／`is_priced` 各紅）。殭屍 grep **九組三個 0**（未列 0／腐壞 0／理由不合法 0）——**證據收集當時是腐壞 1**：`('briefing/alpha_view/contracts.py','D')`，那一行「倍率射程刻意不印」註解在 3.7（f942d26）換成 `rides` 欄位註解時刪了、keep-list 沒同步縮（§13 陷阱寫過的形狀）；本 commit 移除該條目後三個 0 | `python scripts/retired_mechanism_grep.py` |
| 9 | 驗收數的是 §11 的層 | ✅ §2 每個數字都是敘事 ledger、等待 registry、個股頁稽核區、trade_log、走圖、機制存在與否 | — |

**本 commit 的另兩處結案修正（L17：十行內、不動 contract，當下修）：**
- `alpha/three_questions.py` docstring 兩處寫輸入來自 `engine_c.checklist.get_three_question_inputs`（不存在），改指 `engine_c.three_question_inputs`。
- 3.1c 拿掉 `test_coverage_gaps::test_render_separates_two_gap_kinds_with_counts` 時，它另外守的「建模待補要指名間接供應商」沒有接手的斷言（替代測試只守兩桶分開）；`test_graph_walk.py::test_coverage_types_reuse_the_scanner_buckets_and_count_product_noise_separately` 補一行 `modelling["hits"][0]["indirect"] == ["co:lumentum"]`（把 `graph_walk.py:317` 的 `indirect` 改成 `[]` → 1 failed，還原 → passed）。

**另核對（plan §12）：**
- 舊 Decision Store 三個 `*.db`：sha256 與 `live_choices` 與基準**逐字相同** ✅（`backup_pre_v8…` `e887b3d4…` 0；`backup_pre_v9…` `af3dc690…` 1；`decision_lab.db` `e99d1c79…` 1；`?mode=ro` 連線計數、讀前讀後 sha 不變；`decision_lab.db` mtime 仍是 09-21）。
- `library/trades/trade_log.jsonl`：2 行、sha256 `861d2008…c7b8d5`＝基準 ✅（本 Phase 沒有使用者真實成交；3.8／3.9 的測試與 dry-run 不寫它，測試後 sha 不變）。
- `git diff 559414e HEAD -- AGENTS.md` **為空** ✅。
- `identity/registry.py` 自基準 0 行 diff、blob 相同，`company_id_for_ticker` 未改 ✅（`config/company_identity.json` 與 `identity/` 也 0 行）。
- `python -m webapp status` 列得出 `candidates`（8 個 kind 全 ok）✅；基準當時的四個孤兒 artifact（basket／coverage／multi_year／ranking）已不在。

## 2. ROADMAP Phase 3 驗收①–⑤ 與 §11 其他列

| # | 驗收 | 結果 | 層 | 查證 |
|---|---|---|---|---|
| ① | 有敘事的檔 100% 有候選狀態 | ✅ 現行敘事是 v2 的檔數／有現行敘事的檔數＝**4／4**（AXTI `priced_wait`、COHR／LITE `pass`（非邊緣：約 553 億美元 22 位／約 826 億美元 25 位）、SIVE.ST `missing`）；v1 現行 0；ledger parse errors 0 | 敘事 | `python -m alpha brief <ticker> --format json`（逐檔，最新未撤回的一列）；`engine_b.disproof.current_briefs()` |
| ② | 「缺 X」100% 指向活的 watch | ✅ **2／2**：AXTI → `ew_0148_2026-09-29`（date，until 2026-11-13、expires 2027-01-15）、SIVE.ST → `ew_0149_2026-09-29`（date，until 2026-11-26、expires 2027-01-31），皆 `active`、`wake_brief` 是本公司、`attributed_watches` 歸屬本檔、未過期 | 敘事 × 等待 registry | `python -m engine_b.event_watch list`（找 ew_0148、ew_0149）；`engine_b.narrative_watches.attributed_watches` |
| ③ | 三題每題對每檔有值或有 `absence_kind` | ✅ 73 份個股頁 × 三題逐行 **695／695**（會死嗎 292／292、已定價 292／292、出現在數字裡 111／111）；依 kind：有值 279、`not_yet_recorded` 292、`upstream_unavailable` 63、`insufficient_evidence` 53、`inputs_incompatible` 8。缺席最多的三列是**結構性的**：`wipeout_going_concern` 73（pq2 [657]–[661] 未 go）、`cohort_median`／`rel_return_30d`／`rel_return_90d` 各 73（主題等權組 0 組，[656] 未 go） | 敘事（個股頁稽核區） | `library/private/app/analyst_view/*.json` 的 `view.three_questions.lines` |
| ④ | 歸零旗標四盞有值的檔數 | ✅ **現金跑道 67→67、負債 70→70、稀釋 0→30、going concern 0→0**。稀釋 30 檔全是 SEC 封面股數來源（國內申報人，一年窗滿；IREN 窗未滿＝`insufficient_evidence`），非 SEC 來源 0 檔亮燈；顏色與 3.0 相比只有 dilution 由灰變黃 24／綠 6。GC 0：結構化欄位與取數已交付（3.2），觀測寫入要 pq2 [657]–[661] go——**已交付、未生效** | 敘事（個股頁稽核區） | `engine_c.checklist.get_wipeout_inputs`＋`alpha.wipeout.wipeout_flags`（唯讀重算，與 artifact 逐格相同） |
| ⑤ | 新成交事件 100% 帶收據 | ✅ **已交付、未生效**：be73d4e 之後新增 alpha 成交事件 **0 筆**（trade_log 仍是基準的 2 筆，都在 3.8 之前、沒有 `research_receipt`，§5 #33 當缺席處理）。測試證明：`tests/test_record_trade_receipt.py` 30 passed＋`tests/test_record_trade.py` 18 passed＋`tests/test_phase3_full_chain.py` 3 passed（三檔合跑 51 passed，跑前跑後 trade_log sha 不變；3.9 整鏈的 `--apply` 用假 Sheet、暫存 log 斷言事件帶收據） | 追蹤表（trade_log） | `python -m pytest -q tests/test_record_trade_receipt.py tests/test_record_trade.py tests/test_phase3_full_chain.py` |
| A1 | v1 不變 | ✅ v1 7 行 id 重算 **7／7**，與基準清單逐位相同（v2 8 行另 8／8） | 敘事 | `python -c "import json,pathlib; from alpha.narrative.contracts import new_brief_id as f; rows=[json.loads(l) for p in pathlib.Path('library/private/alpha/briefs').glob('*.jsonl') for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; print(sum(f(r)==r['brief_id'] for r in rows), len(rows))"`（2026-09-30：15 15） |
| — | 反證登記 | ✅ 現行 v2 的 `disproof[]` 共 **10 條＝新登 1（AXTI #5 → `ew_0151`）＋連結 9**（AXTI #1–4 → ew_0100／0128／0131／0132 active；SIVE.ST #1–4 → ew_0107／0109／0110／0111、#5 → ew_0147）；link_breaks 0；無重複登記。**`semantic_active` 字面是 26、不是 37**：active 26＋fired 11＝37＝基準 36＋新登 1——少掉的 11 筆是 2026-09-30 05:31 daily 被同一則 lead（`lead_20ce4e7d…`，Sivers 臨時股東會召集公告）叫醒（active→fired），與登記無關；fired 仍算活連結，`semantic_pending_check`＝11 待判（研究動作） | 等待 registry | `python -m engine_b.event_watch counters` |
| A2 | 主題等權組 | ✅ ledger **0 組**（[656] 未 go），已定價②③全體印 `not_yet_recorded` | 機制存在與否 | `python -m alpha theme-cohort`（唯讀；目錄在第一筆寫入前不存在） |
| A6 b | 走圖第 5 型 `unresolved_names` | ✅ **12 → 10**（SIVE、SOI 不再列）；圖 2688 節點不變，九型（命中，母體）與基準完全相同 | 圖（走圖問句） | `python -m query.graph_walk --json` |
| A5、A6 a／c、A7、3.6 | 符號與 kind 存在、拒收測試 | ✅ 見 §1 gate 4／8；`candidates` kind 已登記 | 機制存在與否 | `python -m webapp status` |

**只印不驗收（plan §11 末句）：** 候選板今天 可開 0｜缺 X 0｜等回落 1｜不要 0｜已持有 1｜非倍率候選 2｜邊緣無法量 0｜舊版 0｜前提失效 0｜無敘事 69。
可開為零是合法結果——讓它非空的路是研究（寫敘事），不是改前提或門檻。

## 3. 拿掉的測試函式與去向（559414e 起；plan §0 第 7 條）

| 檔 | 拿掉 | 去向 |
|---|---|---|
| `test_coverage_gaps.py::test_render_separates_two_gap_kinds_with_counts` | 1 | 3.1c（61f0377）隨 `query.coverage_gaps` 的 markdown 與 CLI 退役：「兩種缺口分開、下一步不同」由 `test_graph_walk.py::test_coverage_types_reuse_the_scanner_buckets_and_count_product_noise_separately` 守（commit message 與原檔註解都寫明）；它原本另守的「建模待補指名間接供應商」本 commit 補上斷言（§1 末）；markdown 那幾條斷言隨 `render_markdown` 一起退役，前提消失 |

`tests/test_full_chain_acceptance.py` 一條未拿、未搬（27 passed＝3.0 基準）。

## 4. 執行中發現、實際做了什麼（偏差摘要；全文在 plan §0.6）

- **資料口徑（3.2／3.3／3.5）**：#1–#9、#13——表多 `form`／`tag` 欄讓每列指得回原 tag；落後檢查抽成 `companyfacts_lag_status`（20-F 也報、抓不到＝`unknown`、快照日只看營收白名單）；as-of 規則一份住 `shared/as_of.py`；20-F／40-F 一律 `inputs_incompatible`（不猜 ADS 比率）；序列鮮度規則；兩種占比切法不湊點；已定價①的口徑判定要營業利益與營收同一季收尾、不過期（COHR、LITE 原本拿兩三年前的數判 EV/S）。
- **敘事契約（3.4／3.5）**：#10–#12、#14–#17——沒有短評的 69 檔改列 v2 七題；寫入端讀圖與三題；舊版 `brief:` watch 收掉不 reactivate；「連結來源換版進 `narrative_rewrite`」3.4 **漏做**（R2-a N1 抓到），移到 3.6 由候選推導判；寫入前先做 daily 同一條時間轉換、登記先在副本預演；`{in_numbers_latest}` 說明改成年增率；測試與真實 ledger 隔離（3.4 的一條測試一直在讀真實資料）；**3.4 收尾（6dd0fd4）在 `alpha/cli.py` 直接 import `engine_b`、違反 `test_layer_separation` 且已 push**——當時只跑子集測試沒抓到，3.5 修正並改跑全套。
- **候選板（3.6）**：#18–#26——`_held` 的 company_id 集合是舊集合的超集（pq1 排序逐位不變）；宇宙＝materialize 目錄 ∪ 敘事 ∪ 只在 Sheet 持有；beta 不算「解析不到」（否則恆 ≥10）；字彙與純函式搬到零 I/O 的 `alpha/candidates.py`（請求路徑哨兵原本會變瞎）；歸零旗標印盞數不印每檔最差色（灰不是綠）；drain 段 1 的第二份 watch 分類改呼叫 `classify_watch`。
- **個股頁（3.7）**：#27–#34——三題進選配面板 `three_questions`（Datum 在 builder 組）；候選與 downside 為注入面板；讀圖 context 搬進 alpha；鏈段三種缺席分開說、沒有 sub≥4 邊的句子不再自相矛盾；downside 由 `engine_b.disproof.downside_rows` 產生、同一筆 watch 只印一列；R1 38 條＋覆核 13 條全修（as-of 明確拒絕、Sheet 讀不到＝持有判定暫停、坐了沒讀與沒坐的層分開…）。
- **收據（3.8）**：#35–#40——三題稽核行讀個股頁 artifact、候選列讀候選板 artifact，兩份各驗是不是今天；exit 4 與旗標誤用 exit 2；`--log-only` 不回推持有；FRA:2DG 經 `_TICKER_ENRICHMENT` 解析（§5 #35）；R1 28 條（1 blocking：三題整段缺席被記成 available＋空陣列）全修；**#40 流程違規**：R2-b 期間執行者在同一 working tree 跑變異與寫 3.9 檔（審查者以 mtime 防護確認證據未受影響）。
- **#41（結案時發現）**：2026-09-30 05:30 的 daily（head `f942d26`）開跑時工作區有 3.8 未提交的 `portfolio/research_receipt.py`（心跳「開跑時工作區不乾淨」照印）。f942d26 沒有任何 tracked 檔 import 它，daily 取得了 writer lock、`integrity_violation` 為 None、產出不受影響；但它說明互動 session 在 daily 時段仍在同一個 working tree 寫程式檔——同 #40 的教訓，之後跨 05:30 的寫入改在獨立 worktree 或先 commit。

## 5. Phase 4 要決定的問題（plan §14 #1–#41，#39–#41 是結案新增；照實帶到下一個 plan session）

**要使用者決定（契約、判準、identity、資本）：**

1. **稀釋燈接近恆亮**（§14 #20）：國內申報人 30 檔中 24 檔黃——FN +0.01% 與 AXTI +42% 同樣是黃（L14-4）。要不要把員工股酬與增發分開、用什麼非憑空的判準（例如只看 S-3／424B）。
2. **舊 session assessor 的反證 240 條（63 檔）在 downside 全印「未盯」**（§14 #29）：退役不印，還是改寫進 thesis memo／敘事並登記 watch。
3. **讀圖面板要不要一條 Abstention settle 路徑**（§14 #32）：圖上沒有坐的層的 23 檔（AAPL、MSFT…）若判定是需求側，閉環永遠到不了終局。
4. **重跑 `--apply` 會再寫一次 Sheet**（§14 #34，HEAD 起既有、資本路徑、超出 #16）；**一筆成交讀三次 Sheet**（§14 #38）；**首次建倉要不要能新增 Sheet 列**（§14 #11）。
5. **identity**：`_TICKER_ENRICHMENT` 是第二份 ticker→co:* 對照（§14 #35）；TYO:7803 在 registry 解析不到、「持股解析不到」恆 ≥1（§14 #13）；Phase 2 的「客戶高管在供應商新聞稿具名算不算客戶端印證」（§14 #1 內 #15）。
6. **邊緣門檻 10B／12 位**（§14 #12）：候選板上線後若非倍率候選與邊緣無法量長期占多數要不要重量——**不得為了可開非空而調**。
7. **pq2 [656]（主題等權組成分）與 [657]–[661]（going concern 觀測）仍等 go**（§14 #3、#25）：go 之前已定價②③與 GC 燈全體缺席；[657]–[661] 有兩個判讀點要使用者看（SIVE.ST 的 ISA 措辭、IQE.L 的 KPMG 模板句）。

**退役與清理候選（Phase 4 排程時一起看）：**

8. `get_bottlenecks`／Q1 scarcity 那條路要不要退役（§14 #5；PointInTime 探針要先換成等價探針）；argument 鏈段的邊仍經 sub≥4 過濾，57／73 檔沒有邊可講（§14 #30，與 #5 一起定）。
9. `refresh=review_required` 的來源全是退役估值鏈殘留（§14 #6）。
10. `risk/snapshot.py:85` 的第二份 alpha 判別（§14 #7）。
11. 請求路徑哨兵對 `webapp.materialize` 本身是瞎的（§14 #26）；`alpha/providers/__init__` eager import 有連線能力的 provider（§14 #37）；測試隔離（13 條在沒有 `.env`／真實資料的 checkout 會紅，§14 #31）。
12. R2-a／3.6 覆核的 non-blocking 殘留（§14 #22、#23、#28），其中 **`alpha brief --add` 程式內沒有強制 writer lock**（#23 ④）最值得先做。
13. Phase 2 帶過來未併入的（§14 #1：#2、#4、#6、#7、#10、#11、#13、#14、#16、#17）。

**資料與口徑（Engine C）：**

14. `fundamental_history` 年度營收與 `fiscal_year_results` 誰是 authority（§14 #8）；ADR 比率與報表幣別≠結算幣別（§14 #9）；台股歷史股數（§14 #10）；20-F 便利換算延遲一年（§14 #15）；companyfacts 部分收錄（§14 #16）；落後檢查更窄的一種形狀（§14 #19）；adjusted 價格窗邊界（§14 #17）；Postgres 讀取端（§14 #18）。
15. 三題尚未接 as-of 視角（§14 #21）；「剛轉型」只能由敘事宣告（§14 #2）；占比序列沒有年增、`{in_numbers_latest}` 對它恆「（尚無）」（§14 #24）。

**量測（Phase 5 前要有答案）：**

16. 從 trade_log 收據重建量測；舊事件與 beta 事件沒有收據是缺席不是錯誤（§14 #4、#33）；收據的 derived 要當天個股頁 artifact（§14 #36）。
17. 「可開恆為 0 或恆非 0」要有夠長的每日序列（§14 #14；2026-12-22 回查）。

**結案新增（§14 #39–#41）：**

18. **research 面板 digest 會隨每日共識 notes 變**：跨日語意 diff 的判準只能是「排除 notes 後不變」；另外看到基準前就有的怪象——「首次出現於」的日期每天往後推（6268.T 09-24…09-29）、2455.TW 同一條 note 曾重複 5 次（`alpha/refresh/resolver.py`，不在本 Phase 範圍）。
19. `get_wipeout_inputs`→`wipeout_flags` 的串接在 `alpha/providers/candidates.py:208-225` 與 `briefing/alpha_view/sources.py:438-451` 各寫一次（同一組取數與判定函式、實測結果一致；兩份串接日後會各自長）。
20. `held` 不可宣告有兩道防線，測試分不出是哪一道擋下（兩道都拿掉才紅）——各加一條只拆一道的測試，或刪掉其中一道。
21. §14 #27（`test_watch_expiry` 一次全套跑紅）：3.6 之後的全套跑（含結案這次）都綠，重現不出來；維持觀察。

## 6. 使用者動作（非阻擋）

- pq2 [656]–[661] 的 go（§5 #7）；go 之後的寫入由收到 go 的 session 做。
- `semantic_pending_check` 11 筆（Sivers 臨時股東會召集公告叫醒的 thesis／讀圖反證）待互動 session 判讀——研究動作；SIVE.ST 敘事的四條連結來源在其中。
- claude.ai 的 `stockbotv2-graph` connector 仍連不上（Phase 2 已列）。

最後一次全套：`python -m pytest -q` → **2867 passed, 1 skipped**（2026-09-30 07:42，結案修正後；新增的是一行斷言、不是函式，所以函式數不變）；`python -m audit invariants` → 13 PASS／4877 筆。

## 7. 結案 R2（2026-09-30；乾淨 context 的唯讀審查者，使用者已常規 opt-in）

**Verdict：GO**——五位審查者（四位分工跑 plan §12 WORK_REQUEST 八項、一位逐條核對本報告）**全部 GO、blocking 0**（所以沒有啟動反方驗證者）。
各自重跑成立的：全套 2867 passed／1 skipped（唯一 skip 是 `test_layer_separation.py:313` 刻意的空參數集，自基準 0 行 diff）；audit 13 PASS／4877；
測試檔 184→194、函式 +228／−1（regex 與 AST 兩種算法相同，含非 ASCII 函式名），拿掉那一條的去向＋本 commit 補的斷言在副本上變異會紅；
敘事 ledger v1 7／7、v2 8／8 id 重算、`rides[]` 本公司在供給側、`disproof[]` 無重複登記、缺 X／等回落的 watch active 且歸屬；
自造 5 個應拒收的 v2 spec 全被拒、對照組寫入暫存目錄成功、真實 ledger 與 `event_watches.json` sha256 前後不變；
三題 695／695、抽三檔（國內、20-F、台股）對歷史表手算自家百分位與 artifact 相同、沒有門檻或布林結論欄位、營收的 PIT 成立；
候選板組內按 ticker、無分數、FRA:2DG 在已持有、beta 不在任何組、非邊緣不在可開；心跳段 2 兩行照印含 0；
`CORE_PANELS` 含 readings 不含 fundamental、鏈段需求端不經 `get_bottlenecks`（定義與 PointInTime 探針仍在）、downside 連 watch；
`record_trade.py` 對 FRA:2DG／TYO:7803／QQQ 各 dry-run 一次、trade_log sha 不變；殭屍 grep 三個 0；Decision Store 三檔、AGENTS.md、`company_id_for_ticker` 不變。
五位的起訖 HEAD 都是 `889bc0e`、`git status` 前後皆空（主執行者 R2 期間沒有寫 working tree）。

**Non-blocking 的處置**（同一條多位提到的合併；需要改程式的一律不在 R2 GO 之後動，登記 plan §14 #42–#51 帶到 Phase 4）：

| # | 內容 | 處置 |
|---|---|---|
| 1 | 本報告⑤測試條數寫錯（31／33）；③的 artifact 路徑寫錯（多了 `state/`）；A1、A2 的查證命令不能直接重跑；§0「19 個 commit」含糊 | 本 commit 更正（30／18／3 passed；`library/private/app/analyst_view/*.json` 的 `view.three_questions.lines`；A1 改一行可跑的 id 重算、A2 改 `python -m alpha theme-cohort`） |
| 2 | §4 漏寫 6dd0fd4 已 push 的分層違規（只跑子集測試）；#14 寫得偏中性（原文是 3.4 漏做、R2-a 抓到） | 本 commit 補進 §4 |
| 3 | ROADMAP Phase 3 列的「做什麼」欄沒有照 amendment 改寫（仍寫 `--receipt`、缺收據 fail closed、主題籃子、籃子頁），⑤沒寫只算 alpha | 標 ✅ 的同一個 commit 照 A1／A2／A4／A5／A7 的**已定案用語**同步（不改任何驗收或定義，只把漏改的字換成 amendment 原文），並在該列註明 |
| 4 | 「research 排除 notes 後 73／73 相同」無法獨立重算（基準只存 digest，不存面板原文） | 照實記錄：這一條只有結案證據收集那次算過；之後的基準快照連同要比的面板原文（或已排除 notes 的 digest）一起存（§14 #51） |
| 5 | 同一份 v2 敘事裡兩條相同的 self 反證會登記兩筆同條件 watch（探針在暫存副本上重現；真實 ledger 沒有這種情形） | §14 #42 |
| 6 | `{rel_return_30d}`／`{rel_return_90d}` 兩個登記的 placeholder 因 regex 不收數字而寫不進任何格；「首屏沒有價格報酬」今天的資料成立（0 命中）但型別層沒有強制（`現價 {price}`、字面「報酬 +50%」可寫進首屏格） | §14 #43、#44——兩條連在一起：修 regex 之前要先定「相對組漲幅能不能上首屏」，**使用者決定** |
| 7 | 分部占比在 as-of 下沒有 T 過濾（`_segment_points`）；今天被 view 的 `point_in_time_unavailable` 擋住 | §14 #45，寫成 §14 #21 的前置條件 |
| 8 | 自家百分位的「滿 3 年」只看頭尾跨度（LRCX 751 個交易日只有 314 個樣本、2–7 月全缺）；百分位用嚴格小於沒有測試守；20-F 的 `inputs_incompatible` 比字彙定義寬（GFS 不是 ADS）；無布林結論的測試只守 `evaluate()` | §14 #46–#48 |
| 9 | TYO:7803 天天以「持股解析不到」出現，但 `config/holdings_coverage.json` 已記使用者 2026-07-29 決定不研究（恆亮的問句） | §14 #49（與 #13 一起） |
| 10 | 心跳以讀寫模式開 Engine C 私有庫（09-17／09-19 既有）；`?mode=ro` 讀 WAL 庫仍會更新 `-shm` mtime（不能當「有人碰過」的訊號） | §14 #50 |
| 11 | 殭屍 grep A–H 以（檔，組）為粒度會吸收同檔新命中（I 組已釘數）；掃描範圍不含 `fetchers/` 等；敘事寫入不記 ride 當時的 status（日後無法證偽「寫入當時現行」）；completion gate 只數函式、不清點斷言層級的翻面；CLI 的建模待補不印間接供應商（只有 APP 印、JS 無測試）；基準的函式名單 sha 無法重現 | §14 #51 |
| 12 | SIVE.ST 敘事連結的四條 thesis 反證在 fired（Sivers 臨時股東會公告叫醒） | 已在 §6；下一個互動 session 判讀 11 筆（研究動作） |

## 8. 結案後（2026-09-30 下午）：[656]–[661] go 與研究佇列

**使用者 go [656]–[661]**，同日寫入：主題等權組 ledger `tc_35b0d5cd521656ea`（15 檔等權）、Engine C going concern 五筆
（`mo_8d37…`、`mo_98d4…`、`mo_20aa…`、`mo_9266…`、`mo_bfce…`）。重跑 materialize（81/81）後逐行重數 73 份個股頁：

- **④ 歸零旗標**：going concern 非灰 **0 → 5**。AXTI、COHR、IQE.L、LITE 是「沒有重大疑慮」；SIVE.ST 是「有重大疑慮」
  （Deloitte 查核報告的 väsentlig osäkerhetsfaktor，未修改查核意見）。④ 現為 **67／70／30／5**。
- **A2 主題等權組**：0 → **1 組**。相對組漲幅 30／90 天有值 **0 → 15**；**組中位數仍 0 檔有值**（10 檔是本檔已定價①缺席
  連帶的 `upstream_unavailable`、5 檔 `insufficient_evidence`）——根因是非美國標的沒有財報歷史來源（§5 #14）。
- **新發現的卡點（使用者決定 §5 #4／plan §14 #43–#44 從「潛在」變成「現行」）**：組內成員的 v2 敘事現在寫不進去。
  寫入端要求相對組漲幅有值時 `priced_in` 必須引用 `{rel_return_30d}` 或 `{rel_return_90d}`，型別層的 placeholder
  regex 卻不收數字、把它當格式錯誤——不引用被寫入端拒、引用被型別層拒。以 COHR 現行那一版原樣重演寫入檢查（不落地），被拒
  「priced_in：相對組漲幅有值，這一格必須一併引用 {rel_return_30d} 或 {rel_return_90d}」。受影響的是組內 15 檔
  （含 AXTI、SIVE.ST、COHR、LITE 的任何換版）。修 regex 等於讓相對漲幅上首屏，所以等使用者決定 #4，不自行改。

**研究佇列（research-drain，同日；使用者中途指示「先不要每檔都跑、太花 token」而停止）：**

- 待分流 8 → 0（2 go、6 no-go）。Sivers 臨時股東會召集公告叫醒的 11 筆語意 watch 逐條判「無關」，回 active；
  `semantic_active` 回到 37（＝基準 36＋新登 1，§2 反證登記那一列的字面差距消失）。
- 已核准線索 15 → 9：6 條 park、4 條「建議入圖但未經第二人核對」只加註記（仍在 pq1）、5 條沒追完（未改任何欄位）。
  研究紀錄：[`2026-09-30-drain-trace-packets.md`](2026-09-30-drain-trace-packets.md)。
  其中值得記的一手：存託銀行 Deutsche Bank 2026-09-29 以 F-6EF 註冊 Sivers ADR（1 ADS＝3 股），**不是**發行人掛牌或募資；
  Sivers「2027 上半年」指的是**完成美國掛牌的準備**，不是完成掛牌（triage 理由讀過頭，park 紀錄已更正）。
- 段 5 每檔閉環未動（69 檔）：其中 23 檔在 §5 #3 使用者決定前結構上收斂不了、11 檔卡 §5 #4。
- 流程：一位唯讀 agent 用 curl 在 repo 根目錄寫了一個 215 bytes 的錯誤頁（`t.html`，BlobNotFound），
  writer guard 因「工作區不乾淨」擋下後續寫入，確認是 agent 產物後刪除——guard 在這裡真的擋到了東西。
