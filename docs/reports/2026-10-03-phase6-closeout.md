# Phase 6 證據判準 — 結案報告（2026-10-03）

> plan：[`docs/plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md`](../plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md)（偏差全文 §0.6 #1–#19）；
> 基準：[`2026-10-03-phase6-baseline.md`](2026-10-03-phase6-baseline.md)（§0–§14 是 6.0 快照，§15–§21 是各 Step 的真實資料驗收）；
> 研究收據：[`2026-10-03-phase6-step68-research.md`](2026-10-03-phase6-step68-research.md)。
> 執行者全程 opus 5.5。本報告的數字都是 2026-10-03 13:5x–14:3x 台北量的（星期六，各市場休市）；**現況數字會腐壞，引用前重跑各列的查證命令**。
> **狀態：使用者 2026-10-03 對 [670]–[676] go、[677]／[678] drop，全部執行完畢（§6）；結案 R2 的 B1 由 [670] apply＋C1 五項解除，C1＋C2 窄範圍覆核 GO（§8）——ROADMAP Phase 6 ✅（2026-10-04）。**
> 量測前以 HEAD（`839d48a7`）重跑 materialize（6.0 同一行：`--tracked --registry-listed --structure-table --graph-walk --structure-readings --candidates`，80/80），
> 量測腳本與全文在 scratchpad（`p6c_*.py`、`p6_close.json`、`p6_stockpage_close.json`、`hb_close.md`、`invariants_close.out`），全部唯讀。

## 0. Phase 6 做了什麼（26 個 Step commit，2026-10-03；起點 `06350d0b`＝[666] 的 publish commit）

| Step | commit | 內容 |
|---|---|---|
| 6.0 | 8dabd23f | [666] 收尾（10-02 的 go；6 條升外部印證）；基準快照；證據等級凍結 `evidence_classes_2026_10_03`（537 條） |
| 6.1 | e5d35b84 | 插槽讀圖 staleness：同級標籤互換算低等級（rank 由呼叫端注入、沒有預設） |
| 6.2 | 94673cd6、369c7dfb、9362764f | 身分清理遷移工具（manifest 驅動、dry-run 預設、apply 要 pq2＋非空圖匯出）、入圖副作用 owner、RA packet 副作用段；R2-a GO；**pq2 [670]** |
| 6.3 | 39841c1a、bdd6ff93、f8a054c5、e9e53620、4890f225、3ce1c292、b27a8409、3a89c0a4 | 名冊寫法（Arista、GF；Apollo 不加）、GSR → media、名冊新公司 5 家、`origin_entity` 進 SourceDoc 同步欄位、更正 manifest；**pq2 [671]、[672]** |
| 6.4 | 153bd093 | 「算不算外部印證」收成一個 owner（`query.origin_resolution.corroboration`）：逐來源具名＋轉述字表；所有消費端改走它；計數器改口徑；RA packet 印入圖後會變等級的邊 |
| 6.5 | d46c9e66 | sub 旗標跟著值走到四個消費端（結構表、五個角度的邊、走圖第 1 型、個股頁「替代難度」旁註）；不進讀圖 digest |
| 6.6 | fbac7a61、7e29439d、edb1ad46 | 稀釋燈只認窗內募資文件（EDGAR 申報清單、Engine C 兩張新表、daily 請求數不變）；R2-b CONDITIONAL_GO → 條件修正 → 窄範圍覆核 GO |
| 6.7 | 76d421e9、aade23db、a16a2134、a0c800ec、7c6b22d3、f65ef0d9 | 小修：結構表逐列需求錨、APP 自偵舊程式、排除未收盤 K 棒、預測表改寫規則①、本機 ask 規則 16 條 |
| 6.8 | bdd3ea63 | 研究：降級 22 條逐條有去向；補引文 RA **pq2 [673]–[676]**（[677]／[678] 作廢）；重讀 InP、CW DFB；四檔敘事換版 |
| 6.9 | 839d48a7 | 新管線 full chain 測試（證據鏈到心跳與讀圖核對；稀釋燈鏈到個股頁首屏與稽核區；五個變異） |

**本 Phase 沒有任何一次 Neo4j 寫入**（[666] 的 apply 在起點之前）：全圖 assertion 699、canonical 邊 537、SourceDoc 220 與 6.0 相同；圖上的變動全部等 [670]–[676] 的 go。

## 1. 九項 completion gate（plan §12）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級拿掉的每一個有去向 | ✅ **3445 passed, 1 skipped**（6.0：3303 passed, 1 skipped）；測試檔 **211 → 221**＝＋10（`test_identity_cleanup`、`test_merge_side_effects`、`test_corroboration`、`test_relay_language`、`test_sub_language_consumers`、`test_dilution_offerings`、`test_row_demand_anchor`、`test_webapp_code_freshness`、`test_closing_bars`、`test_evidence_criteria_full_chain`），退役 0；函式 **2673 → 2791**，新增 120、**拿掉 2，各有去向**（§3） | `python -m pytest -q`；`git grep -n -E "^\s*(async )?def test_" <rev> -- 'tests/*.py'`（6.0 名單 sha `c1db1da2…` 重建一致；scratchpad `p6c_testfns.py`） |
| 2 | `python -m audit invariants` 綠 | ✅ **14 PASS／0 FAIL（共檢查 5476 筆）**；SourceDocSync「重建會遺失 0（section 0／title 0／origin 0）｜圖落後 JSON 0」（origin 是 6.3d 加進同步欄位的）；PointInTime 207/220、681/699（＝6.0）；QueueLiveness 204 項；Expiry 127 個等待全部有到期；Lifecycle「待辦池 678 項結案狀態一致；watch 171 筆」 | `python -m audit invariants` |
| 3 | 無未解釋語意 diff | ✅ **心跳**與 6.0 的 `hb_base.md` 逐行對照（64 → 74 行），每一處都歸得到來源（§1.1；R2 逐條驗過）。⚪ **個股頁：四個維度＋程式 hunk 內無未解釋 diff；面板級對 6.0 無法驗證**（plan §0.6 #19：6.0 沒存逐面板 digest）——73 → 76 份（＋2768.T、CRDO、USAR：6.3c 新進名冊的上市公司），舊 73 份的 `content_digest` **73／73 變**，但這個數沒有分辨力：6.6 的規則文字與 inputs 住在每一頁的歸零燈與三題稽核列，另外每一頁的 `price_series`（`webapp/materialize.py` → `alpha/providers/close_series.fetch_close_series`，6.7c 改過、每次 materialize 重抓）也是每頁都有的來源，6.0 沒存這份序列；四個維度之外的面板若有預期外的變動會被一起蓋掉（R2 C2）。逐檔歸因與限制見 §1.2。**讀圖 `result_digest`**：變的只有 6.8 重讀的兩份（新紀錄，因為標籤變了）；SuperNova、ELS 兩份 id 與 ledger 指紋＝6.0；sub 旗標不進 digest（`test_the_flag_never_reaches_the_reading_digest_or_snapshot_rows`；6.5 實測四份 status 與 digest 改前改後逐位相同，baseline §19） | `python -m crons.heartbeat --out <檔>`（不帶 `--write-snapshot`）；scratchpad `p6c_compare.py`、`p6c_chain_show.py`、`p6c_watches.py`、`p6c_onboard.py` |
| 4 | 無新 dual authority | ✅ 「算不算外部印證」只有 `query.origin_resolution.corroboration`——呼叫端 `query/bottleneck.py:450`（`edge_corroborations`→結構表與 `_classify_edges`）、`query/structure.py:306`（插槽視角）、`alpha/providers/structure_readings.py:138`（讀圖 independent 引用核對）、`scripts/audit_sole_source_independence.py:75`；名字比對只有 `quote_names_company`（owner、RA packet 顯示 `intake/actions.py:299`、層計數器的「違反」重算 `query/layer_stats.py:177`——後者刻意不經 owner 直接重算，L14-2 gate 本身也要驗，只計數不判定）；轉述字表只有 `get_relay_language` 一個 loader（owner 與層計數器）；募資文件判定只有 `_equity_issuance`（`engine_c/checklist.py:656`）→ `dilution_flag`（`alpha/wipeout.py:318`）；需求錨只有 `demand_chain`（結構表、走圖、讀圖快照） | `git grep -n "corroboration(\|quote_names_company(\|get_relay_language(\|dilution_flag(\|_equity_issuance(\|demand_chain(" -- '*.py' ':!tests/'` |
| 5 | 無 silent drop | ✅ 沒升外部印證的每條邊帶三種理由之一（`test_withheld_reasons_are_a_closed_vocabulary`、`test_edges_that_did_not_rise_are_listed_by_reason_with_their_documents`；真實圖 未具名 13／名冊無名 4／轉述 2＝19＋GSR 資料更正 3＝降 22）；名冊無名可比與引文沒具名分開（`test_3_subject_without_usable_name_forms_is_no_name_forms_not_unnamed`）；讀不到 → `upstream_unavailable`（`test_an_unreadable_filing_list_is_upstream_unavailable_not_green_or_amber`、`test_prepare_says_side_effects_are_unknown_when_the_graph_is_unreachable`、`test_8_callers_that_do_not_pass_quotes_fail_loudly`）；未收盤 K 棒拿掉的與「收盤狀態未知」的都計數（`test_the_tracker_counts_what_its_default_fetchers_dropped`、`test_without_a_trading_period_the_bar_is_kept_and_called_unknown`）。**今天正式資料上就有一例**：11 盞稀釋燈因正式庫還沒有募資文件清單印「募資文件清單讀不到——不判黃也不判綠」，沒有被靜默算成綠或黃（§2 ④） | 各測試檔；`python -m crons.heartbeat` 段 4 |
| 6 | Point-in-time | ✅ 募資文件以 EDGAR `filed` 落窗、只取 `filed ≤ today`（`test_only_filings_inside_the_window_and_known_by_today_count`）；清單涵蓋不到窗就說不出「沒有」（`test_a_list_that_does_not_reach_back_to_the_window_cannot_say_none`）；`audit PointInTime` PASS；as-of 投影只讀 as-of 當時可見的 assertion（`alpha/providers/graph_neo4j.py` 的註解寫明逐字讀的是現在版本——與屬性值同一個近似） | `python -m audit invariants --only PointInTime` |
| 7 | lifecycle 可達 | ✅ 本 Phase 鑄的 9 個編號（[670]–[678]）結案時全部在池中、**心跳逐筆列出**（段 3「pq2 球在你手上 9」下 9 行），2026-10-03 使用者批次後**全部到終局**（§6）；4 份現行讀圖全部有到期（82–90 天）；Expiry「127 個等待全部有到期」；新寫的 14 筆 watch 全部有 `expires` | `python -m engine_b.todo list`；`python -m crons.heartbeat` |
| 8 | executable protection | ✅ owner 的九個夾具＋三個變異（`tests/test_corroboration.py` 1–9、6.4 變異）；6.1 同級互換三條（`test_a_same_rank_swap_on_a_socket_supply_edge_is_low` 等）；6.5 旗標不進 digest；6.6 兩個變異；遷移工具 apply 要 pq2 且先查編號、無 pq2 或無備份是用法錯誤（`test_apply_checks_the_pq2_number_before_any_write`、`test_apply_without_pq2_or_backup_is_a_usage_error`；dry-run 是預設）；L19 守門三條（`test_no_prompt_or_skill_points_at_the_relay_vocabulary_file`、`test_no_prompt_or_skill_line_carries_a_pasted_relay_term_list`、`test_the_pasted_relay_list_detector_itself_fires`）；6.9 五個變異各自轉紅；**殭屍 grep 未列 0／腐壞 0／不合法 0** | `python scripts/retired_mechanism_grep.py` |
| 9 | 驗收數的是 §11 的層 | ✅ §2 每個數字都是圖、讀圖、敘事、等待 registry、稽核區或機制存在與否；沒有任何一個是「幾檔通過某個 filter」（候選板「可開 0」只印不驗收） | — |

### 1.1 心跳逐行歸因（`hb_base.md` 64 行 → `hb_close.md` 74 行）

- **日期與營運**：標題時間；備份「之後變動未備份 91 → 105」（6.8 的 ledger、3 份新個股頁與今天的 artifact，都在備份範圍內）。
- **本 Phase 鑄號**：「pq2 球在你手上 0 → 9｜池中未結案 1 → 10」＋逐筆 9 行＋批次範例行（[670]–[678]）；段 2 較昨變動多出「pq2 未結案 7→10、球在你 6→9」。
- **6.8 研究寫入**：結構讀圖「現行 2 → 4、低級 2 → 0」；較昨「watch 已收 30→44、讀圖現行 2→4」；事件監看總數 157 → 171（新 14＝InP 新讀圖 7＋CW DFB 新讀圖 6＋AXTI 新敘事第 5 條反證 1；收掉 14＝兩份舊讀圖的 13 筆＋AXTI 舊敘事那 1 筆——收據 §3「反證 watch 換新（InP 7、CW DFB 6，舊的收掉）」；扣掉這 14 筆，已收正好是 6.0 的 30）；圖預測「改寫 9 → 11、現行最早到期 2026-12-24 → 2027-01-01」（6.8 的兩份新讀圖讀法相同、沒有帶來新來源＝`predictions.py` 的「同讀法、無新來源 → 改寫」，不算對錯；現行最早到期跟著新讀圖的 90 天到期往後移）。
- **6.4 證據判準**：段 3「層：」行——①獨家且全自報 73 → 77（與 plan §0.2 預測相同）、「外部印證但引文不具名供應商 15」換成「外部印證違反 0｜沒升外部印證：未具名 13／名冊無名 4／轉述 2（轉述字表 v1·base）｜證據等級較 6.0：升 2／降 22／同級互換 0」。
- **6.3c 名冊新公司**：「層：」行②「origin 解析不到的來源 8 → 5」；三題 73 → 76 檔（缺席 46 → 49、26 → 29＝新三檔還沒有資料）；候選「無敘事 69 → 72」；「累計被點名但未登記 112 → 111」（同一份 lead 以 6.0 名冊重算＝112，差的那一個是 **CRDO**——6.3c 登記了 Credo；`p6c_onboard.py`）。
- **6.7a 逐列錨**：結構表「9 → 10 個需求錨（前三 tech:ai_switch 102 → 126、tech:optical_scale_up 39 → 29、tech:essential_chips_mature_node 29 → 21；公司層 67 列）」。
- **6.6 稀釋燈（過渡狀態，§2 ④）**：歸零旗標「73 → 76 檔；黃 44 → 33；灰 139 → 162（method_not_applicable 38 → 41、not_yet_recorded 68 → 71、upstream_unavailable 9 → 26）」——黃少的 11 盞＝11 檔稀釋燈改印「募資文件清單讀不到」；其餘 12 盞灰＝新三檔 × 4 盞（3＋3＋6）。合計 21＋33＋88＋162＝304＝76×4。三題「會死嗎 四盞非灰 3 → 0」同一個原因。

**未解釋 0。**

### 1.2 個股頁逐檔歸因（6.0 批次 73 檔 → 結案）

⚠ **限制（plan §0.6 #19）**：6.0 只存了逐檔的整份 `content_digest`、「這條鏈怎麼走」的文字、邊的證據標籤參照與點亮的稀釋燈（`p6_stockpage_base.json`、`p6_base.json`），**沒有存逐面板 digest**（Phase 3／4 的 `analyst_view_text_digest.py --per-panel` 那種），所以面板級的 diff 無法對 6.0 重建。改以下列四個維度＋程式 hunk 歸因完成：

- **鏈段文字 11／73 變**（`p6c_chain_show.py` 逐句）：
  - 7 檔只差「現行（圖上只有證據等級變了）」→「現行」（2455.TW、3081.TWO、4979.TWO、5016.T、5802.T、AXTI、SIVE.ST）＝6.8 重讀 InP、CW DFB；
  - AVGO「Broadcom 供應 Co-Packaged Optics；…有客戶或第三方印證」搬進「只有公司自己在講」＝6.4（Meta 論文那段沒具名 Broadcom）；
  - COHR「CW DFB」「6-inch InP Fab」兩條搬進「只有公司自己在講」（3 → 5 條）＝6.3b GSR → media、6.4（NVIDIA 部落格主詞是 it；[675] 補）＋讀圖重讀；
  - LITE「UHP」搬進「只有公司自己在講」（2 → 3 條）、「Pluggable turnkey ELS module」由「有客戶或第三方印證」改「公司自己說的，但寫在正式申報文件裡」＝6.4（UHP 未具名，延後見 §5 #11；ELS 是轉述句，[674] 補）＋讀圖重讀；
  - GFS 同一組句子、兩句互換順序＝6.7a（逐列錨改了同公司內 tie-break；6.7a 實測「只有 GFS 的同公司內順序變了」）。
- **證據標籤參照 1／73 變**：LITE `co:lumentum/supplies_to/tech:uhp_laser` 外部印證 → 待判定（6.4）。
- **稀釋燈**：6.0 點亮 11 盞黃 → 結案 0 盞（11 檔改印「募資文件清單讀不到」＝6.6 過渡狀態，§2 ④）。
- **敘事新版**（6.8）：AXTI、COHR、LITE、SIVE.ST 各一筆（ledger 前綴不變、各多 1 行）。
- **程式 hunk**（`git diff 06350d0b HEAD`）：`briefing/` 只有 6.5（替代難度旁註）與 6.7a（錨的來處欄位與註）兩組；`alpha/providers/graph_neo4j.py` 是 6.4（逐字跟著 assertion 走進分類）、6.5（sub 旗標）、6.7a（`demand_anchor_basis`）；`alpha/wipeout.py`＋`engine_c/` 是 6.6；`alpha/providers/close_series.py` 是 6.7c——**每一頁的 `price_series`**（`webapp/materialize.py` 的 `_close_series` → `fetch_close_series`）走它，而且每次 materialize 都重抓 yfinance（R2 C2 補上；初版漏列）；**`webapp/materialize.py::materialize_view`／`build_overview` 0 個 hunk**（materialize 的 hunk 全在結構表與走圖 artifact）。
  所以 73／73 的 digest 變動＝6.6 規則文字與 inputs（每一頁）＋每頁的 `price_series`（6.7c 的程式；週六兩次 materialize 都在各市場收盤後，預期不變，但 6.0 沒存這份序列、**無法驗**）＋上列逐檔項；有結構邊的頁另多 `demand_anchor_basis` 欄位（6.7a）與有 sub 的邊的「替代難度」旁註（6.5）。
- **結論（照 R2 C2 改寫）**：上面四個維度與程式 hunk 範圍內，無未解釋 diff；**面板級（三題數值、其他三盞燈、稽核列、替代難度旁註、錨的來處、價格序列）對 6.0 無法驗證**——不寫成無條件的 ✅。機械的補法有兩條：①以 `06350d0b` 與 HEAD 兩版程式對同一份輸入各 materialize 一次到暫存目錄、逐面板比（worktree 讀不到 `library/private`，要明確指路徑）；②下一個 Phase 的基準快照加跑 `scripts/analyst_view_text_digest.py --per-panel`（plan §0.6 #19）。

**另核對（plan §12）：**
- 舊店三個 `*.db`：sha256 與 6.0 **逐字相同** ✅（`e887b3d4…`、`af3dc690…`、`e99d1c79…`）。
- `library/trades/trade_log.jsonl`：sha256 `861d2008…`＝6.0 ✅。
- `git diff 06350d0b HEAD -- AGENTS.md` **為空** ✅。
- 主題等權組 ledger `AI_____CPO.jsonl`：sha256 `25721a7a…`＝6.0 ✅。
- 讀圖 ledger：SuperNova、ELS 逐位元＝6.0；InP 7 → 8 行、CW DFB 5 → 6 行（6.8 的 `sr_b8b405c96d8747c1`、`sr_00e18cf604cc66b9`）✅。敘事 ledger：四檔各多 1 行、前綴不變（6.8 的 `ib_8c35bc994d0c1047`、`ib_0c22f37bf4b8052c`、`ib_c8dd6783f5fd2dd2`、`ib_c9445bd7b28f7fcf`）✅。`event_watches.json`：新 14／收 14 全部對得上 6.8（§1.1）✅。
- Google Sheet：本 Phase 新增的程式碼 0 個 Sheet 寫入呼叫（`git diff 06350d0b HEAD -- '*.py' ':!tests/'` 的新增行掃 `update_cell|append_row|batch_update|…`＝0）✅。
- `python -m webapp status`：State artifacts **8 份**、analyst views 76 份 ✅。
- `git ls-files library/private` 為空 ✅。
- `.claude/settings.local.json`：allow 52／**ask 0 → 16**（6.7e）／deny 0。

## 2. ROADMAP Phase 6 驗收與 §11 其他列

| 驗收 | 數的東西 | 結果 |
|---|---|---|
| ①（A1）外部印證名副其實 | 逐來源違反數；降級的每一條在收據有去向；另印外部印證、①、走圖第 2 型 | ✅ **違反 0**（`ec_without_naming_quote`＝0，逐來源口徑）。外部印證 **250 → 230**（結案時；使用者對 [673]–[676] go 後 **236**，§6）（升 2：6.3c 名冊新公司——`co:lynas supplies_to mat:separated_heavy_reo`、`tech:near_package_optics competes_with tech:cpo`；降 22：GSR 資料更正 3＋規則 19〔未具名 13／名冊無名 4／轉述 2〕；同級互換 0；新增 0、消失 0）；**降級 22 條逐條有去向**（收據 §1：補引文 RA 6 條 [673]–[676]、身分修正 4 條 [670]、6.3b 定案 3、維持降級附理由 8、延後附到期 1）；①獨家且全自報 73 → **77**（誠實的回升，與 §0.2 預測相同）；走圖第 2 型命中 0／13 → **0／13**（圖） |
| ② 身分 | 同一家兩個代號、不是公司的公司節點 | ✅ **2 → 0**（2026-10-03 使用者對 [670] go 後 apply：`co:openlight`、`co:nava_thailand` 兩個節點與 3 筆舊 id 的 assertion 刪除、名冊 105 → 103；事後重算＝dry-run 預告 8 條；R2 C1 五項成立，§8）。結案時（4ef5e5e3）是「已交付、未生效：2 → 2」——plan §0.5 規定 6.2 的編號未 go 就停在 `AWAITING_HUMAN`，那是結案 R2 的 B1。⚠ 勘誤（R2 N3）：baseline §16.1 寫「沒有任何來源把『Nava』指向代工廠」不精確——庫內 `library/raw/fn_10_k_20260818.txt`（Fabrinet 10-K）寫 Fabrinet「acquiring an 8-acre campus in Navanakorn, Thailand in May 2026」；處置不受影響：Lumentum 那次法說（Q2 FY2026，2026-02-03）早於 Fabrinet 買廠，DEF 14A 也逐字寫 Navanakorn 是 Lumentum「our largest manufacturing facility」（R2 重抓 SEC 原文核過） |
| ③ 讀圖與敘事跟上 | stale 讀圖各有新一筆或延後且有到期；四檔 v2 敘事各有新版或不換版理由 | ✅ 6.0 時 stale_low 的兩份（InP、CW DFB）各有新一筆（6.8，現行、到期都是 90 天）；四份讀圖全部 current、「該重讀 0」；兩份新讀圖跑 `verify_citations` 0 個問題——但兩份都沒有標 independent 的引用，所以「過新的 independent 規則」是**空的成立**（R2 N7）；四檔敘事各有新版：LITE 改一句＋重押讀圖、AXTI／COHR／SIVE.ST 七格文字不改只重押讀圖，不改字的理由逐檔寫在收據 §4（讀圖、敘事） |
| ④ 稀釋燈 | 亮黃的每一檔指得出窗內一份募資文件；11 檔逐檔前後對照 | ✅ **機制與逐檔對照（正式庫的檔案副本）**：黃 11 → 10、每盞黃燈指得出窗內一份募資文件、LRCX 轉灰並印理由（baseline §20；R2-b 覆核過；結案 R2 自己抓 11 檔 EDGAR submissions、自己寫封閉清單重算，逐份相同）。這是**照封閉清單的字面成立**——NVDA、META 配到的是公司債說明書，實質要等 §5 #10（R2 N2）。⚪ **正式 APP 要等 10-04 05:30 的 daily**：6.6 量測期間沒寫正式庫（正式庫 sha256 前後相同）；清單由 daily ②b（`engine_c.history_backfill --incremental`）用落後檢查同一次 submissions 順帶寫入（`history_backfill.py` 的落後檢查快取 → `_store_offerings`；11 檔都有財報列，R2 核過）。**之後的正式庫（R2 N1）**：10-03 12:23（6.7 執行期間）第一次以新程式開庫時，`_ensure_sqlite_schema` → `ensure_offering_schema` 建了兩張新表、**0 列**（每次開庫都跑，讀取路徑也會建表；CREATE IF NOT EXISTS）——正式庫 sha256 `85b14e4a…` → `bcd71318…`、mtime 12:23:15。在 daily 寫入之前，11 檔印「有新股發行金額，但募資文件清單讀不到——不判黃也不判綠」（稽核區的 `offering_reason` 逐字是「這一檔還沒抓過 EDGAR 申報清單（daily 的 EDGAR 增量在有既存財報列時才抓）」；fail closed，不是退步）。**10-04 的核對**：心跳段 4 的「黃」應由 33 回到約 43（CRDO、USAR 第一輪才存財報列、第二輪才抓清單，6.6 實測）；若仍是 33，就是 ②b 沒寫進清單（L13），查當天 daily 報告的 02b 段（稽核區） |
| 另印：解析不到的 SourceDoc | 16 → N | ✅ **16 → 11 → 8**（Credo、Noveon、Sojitz、Telescent、USA Rare Earth 那 5 份解析成名冊公司——6.3c；Soitec、Novanta、綜述論文 3 份——[671]，心跳「origin 解析不到的來源 5 → 3」） |
| 另印：sub 旗標出現在消費端的處數 | 處數 | ✅ **4 處**：結構表、五個角度的邊、走圖第 1 型、個股頁「替代難度」旁註（6.5；真實結構表 66 列帶 sub：撐得住 9／撐不住 57） |
| 另印：staleness 同級互換、[666] 的證據等級變動 | 機制；邊 | ✅ 同級互換＝低等級（6.1，三條測試；真實資料 baseline §15）；[666] 升外部印證 6 條（baseline §0） |
| 小修 | 機制存在與否 | ✅ Lam 9 列逐列錨＋basis（6 列逐列、3 列公司層；全表有錨 211 → **213**＝逐列 146＋公司層 67，無錨 11）；APP 頂端「請重啟」橫幅；未收盤 K 棒計數；預測表規則①（真實 15 筆終局不變）；ask 16 條（下一次跑 `record_trade.py`／`apply_ra_admission.py` 時你會被問一次，§7） |
| pq2 | 本 Phase 鑄的每個編號在終局或在列 | ✅ **9／9 到終局**（2026-10-03）：[670]–[676] go——[673]–[676] 由 `complete-ra` 比對入口戳記結案、[670]–[672] 附 authority receipt；[677]／[678] drop（§6）。心跳「pq2 球在你手上 0」 |

## 3. 測試函式增刪（`06350d0b` → HEAD）

**拿掉 2 個，各有去向：**
- `tests/test_layer_stats.py::test_corroborated_edges_whose_quote_never_names_the_supplier_are_listed`（舊計數器 `ec_quote_does_not_name_supplier`，口徑是「這條邊任何一段引文具名」）→ 6.4 換成 `test_edges_that_did_not_rise_are_listed_by_reason_with_their_documents`（三種理由分格、每條帶 origin 與文件）與 `test_the_violation_counter_catches_a_corroboration_label_the_quotes_do_not_support`（計數器不經 owner 重算、抓得到誤標）。
- `tests/test_research_actions.py::test_prepare_validates_every_document_without_graph_or_publication` → 6.2d 改寫成 `test_prepare_reads_the_graph_read_only_and_never_publishes`（假 driver 擋寫入 Cypher），另加 `test_prepare_says_side_effects_are_unknown_when_the_graph_is_unreachable`、`test_prepare_prints_which_existing_values_the_load_would_overwrite`（plan §0.6 #5：舊測試守的「prepare 不開圖」從來沒被守住）。

**新增 120 個**：`test_identity_cleanup` 15、`test_closing_bars` 14、`test_corroboration` 14、`test_merge_side_effects` 12、`test_dilution_offerings` 11、`test_row_demand_anchor` 10、`test_migrate_sourcedoc_json_section` 7、`test_webapp_code_freshness` 7、`test_relay_language` 6、`test_sub_language_consumers` 5、`test_layer_stats` 4、`test_evidence_criteria_full_chain` 3、`test_research_actions` 3、`test_structure_reading_v3` 3、`test_engine_b_leads` 2、`test_origin_resolution` 2、`test_alpha_as_of_projection` 1、`test_reading_predictions` 1。
既有三支 full chain（`test_full_chain_acceptance`、`test_layer_document_full_chain`、`test_measurement_full_chain`）的斷言 0 處變動；有改的是呼叫：`test_layer_document_full_chain` 的 helper `_classified` 在 6.4 多收 `quotes`（`classify_evidence` 的必填參數），`test_measurement_full_chain` 在 6.7c 讓假取價函式多收 `states=None`（R2 N5 更正：初版只寫了後者）。R2 另掃了既有測試檔裡被刪的 assert 行，全部是 `classify_evidence` 必填參數造成的呼叫改寫或 GSR → media 的期望值更新，沒有斷言被拿掉。

## 4. 執行中發現、實際做了什麼（偏差摘要；全文 plan §0.6）

- **plan 內部衝突的裁決（#2）**：宣告 `origin_linkage=independent` 的文件不套轉述檢查（照 ROADMAP「翻案靠逐份宣告」）——照 §13 原註記的讀法，使用者 10-02 核准的 [666] 會被整個抵銷。
- **起算點（#3）**：外部印證以 [666] 之後的 250 起算；GSR 連鎖只剩 3 條；綜述論文掛 34 條。
- **身分遷移的副作用（#4、#12）**：只照抄改名那一個節點會蓋掉 `co:newphotonics` 的兩個屬性 → 每個圖上已存在的節點都照抄現值；「每個寫法都與另一家共用」也算名冊無名可比（OpenLight 兩個代號）。
- **名冊寫法（#6）**：Apollo 不加——4 段裡 2 段是 Google 的 Apollo OCS 專案代號。
- **owner 的形狀（#10、#11）**：assertion 層記「每段逐字出自哪份文件、那份宣告了什麼」（取代舊的 `origin_linkages`）；插槽視角照列過了 `publisher_lifts` 的發布者引文並旁註，不讓改前列得出的原文靜默消失。
- **稀釋燈（#13–#15）**：多一張「抓清單紀錄」表，分開「抓過、窗內沒有」與「從沒抓過」；理由句不帶表單代號（D2）；R2-b 抓到已知限制漏寫 MRVL 的兩份公司債說明書（L11-2）。
- **逐列錨的範圍（#16）**：錨一改逐列，個股頁同一格也要帶來處，否則是 L12 的形狀。
- **未收盤 K 棒（#17）**：基準指數是對稱面；`fetch_close_series` 原本的第二套「收盤了沒」規則收掉。
- **研究（#18）**：四檔敘事都寫新版（三檔只重押讀圖）；UHP 那條延後；RA 第一版兩份作廢（[677]／[678]）。
- **結案（#19）**：個股頁逐面板 digest 無法對 6.0 重建（6.0 沒存），改以四個維度＋程式 hunk 歸因（§1.2）。
- **6.9 的 L11-6**：一度以為灰燈的 inputs 沒送到個股頁；查正式 73 頁，APP 稽核區（三題面板）每盞灰燈都帶 detail——撤回修法，測試改斷言 APP 真正渲染的那一列。

## 5. 下一步要決定的問題（plan §14 #1–#13；結案新增 #14–#17）

**要你決定（使用者的題）：**
- **#10 424B2／424B5 分不出股權或債**：NVDA、META 的黃燈與 MRVL 的兩份配到的是公司債說明書。①每份新出現的 424B 多抓一次文件判股權／債（daily 偶爾多 1–2 次請求，動到「請求數不變」）；②維持現狀，讀的人看稽核區的文件代號自己判。
- **#11 同一個 doc_id 有兩份抽取檔**（`co:lumentum supplies_to tech:uhp_laser` 住附錄檔，更正走廊改不到，所以 UHP 那條的補引文延後）：①把附錄併進主抽取檔（一次遷移）；②讓更正走廊認得附錄檔（改 intake 契約）。收據 §1.5 的延後「到期＝結案當天」就在這裡重問（到期是重問不是丟；它是開發題，載體是下一份 plan 讀的這張清單，不進 pq2——R2 N6）。
- **#12 BD 官網上的 Hyundai Mobis 新聞稿算誰說的**：origin 是 Boston Dynamics，內文是「Hyundai Mobis announced…」——要不要把 origin 改成 Hyundai Mobis（更正走廊或 6.3d 式的 origin 更正）。
- **#13 策展摘錄的標籤指不回原文**（L18）：要不要掃一次「摘錄裡的方括號／改寫框架」有多少份。
- **#7 Phase 7 候選**：旁支「海外財報來源」（邊緣候選 22 檔裡 18 檔缺「已定價」的主參照）。

**照帶（資料口徑與機制題，不急）：**
- #1 12-22 回查（決定紀錄 §10）——今天的值：結構讀圖 ledger **4 個檔、17 筆紀錄**；候選「可開」序列 **2 行（10-02、10-03）皆 0**；09-22 之後新鑄 pq2 **28 個，財務／決策層 5 個（18%）**（manual 11、research_action 10、engine_c 5、lifecycle 1、theme_cohort 1）；單供應商節點 **117／186（63%）**（09-22：121／186，65%）。
- #2 Phase 5 closeout §5 #5、#6、#9、#10（#8 FRA:2DG 回填是使用者動作）；#3 Phase 4 closeout §6 資料口徑題；#4 Phase 3 closeout §5 #14、#15。
- #5 轉述偵測只套發布者；#6 字表 v1 是否漏常見寫法（另：`states` 會誤中「United States」，0 筆受影響）；#8 插槽視角照列撐不住的發布者引文是否雜訊太多；#9 更正走廊 `raw_excerpt` 表頭重複、`forbidden_driver` 絆線可能空跑、Noveon／USAR 引文掛在 MP 的邊上是否錯置、`co:apollo` 的名字寫法。
- **#14（結案新增）人工 lead 的代號字串對不上名冊**：Sojitz 已登記（2768.T），但那則 lead 記的是「Sojitz Corporation (2768.T)」，所以「被點名未登記」清單仍列它（111 個裡的 1 個）。照「資料對齊名冊」改 lead 的字串——改 lead registry 要 pq2（6.3f 先例）。
- **#15（6.9 新增）wipeout 面板沒點亮的那幾格不帶規則與 inputs**（點亮的才帶）：APP 稽核區走三題面板、資訊沒遺失；只有 markdown 版分析視角看不到灰燈的 inputs。要對稱就是 76 頁 digest 全變、消費端零增益——建議不改。
- **#16（結案 R2 N4）四檔新版敘事裡仍有被取代讀圖的 id**：6.8 照 Phase 4 Step 4.8 的先例只換 `rides[]` 與反證連結，格層的 `evidence_refs` 沒換——最新一行裡 AXTI 指舊 InP `sr_bac985…` 7 處、COHR／LITE 指舊 CW DFB `sr_d49b81…` 各 4 處、SIVE.ST 指 `sr_d49b81…` 6 處與 `sr_268d2f…` 4 處。ref 仍解析得到，但讀的人點進去看到的是舊讀圖（L18：標籤要指得回原始證據）。要不要在重押讀圖時一併換格層 ref（動到敘事寫入的契約）——使用者的題。
- **#17（pq2 批次執行時發現）巢狀的 writer lock 會被內層工具拆掉**：`loader/migrate_sourcedoc_json_section.py`（兩處）與 `loader/migrate_identity_cleanup.py`
  在 apply 時自己 `acquire(INTERACTIVE_OWNER, ttl_minutes=15／30)`、`finally` 裡 `release`——同 owner 的外層 session 鎖（`scripts/writer_guard.py acquire`）
  會先被續期成較短的 TTL、最後被刪掉（`engine_b/writer_lock.py`：同 owner 再 acquire＝續期、release＝直接刪）。2026-10-03 [671] 結束時外層鎖被拆，
  [672] 寫 lead registry 那一刻沒有持鎖（§6）。修法：內層工具先看 `holder()`，同 owner 的未過期鎖在就不 acquire、不 release（或在 `writer_lock` 加一個
  會看巢狀的 context manager）——L17「只認得當初那個案例」，下一個 session 當下修（daily 不跑這兩支工具）。

## 6. pq2 go 的執行紀錄

- **本 Phase 執行的 go：[666]**（使用者 10-02 的 go）——6.0a 經 `scripts/apply_ra_admission.py` 入口 apply、`commit_pending_intake.py`（commit `06350d0b`）、`complete-ra 666`；6 條升外部印證（baseline §0）。
- **本 Phase 鑄的 9 個**：結案時全部在池中、心跳逐筆列出；使用者 2026-10-03 回批次 `670 go 671 go 672 go 673 go 674 go 675 go 676 go 677 drop 678 drop`，
  同晚在 writer lock 下逐項執行（照各編號 hint 的 exact 動作，沒有加任何 hint 未載明的動作）：
  - [677]／[678] → **drop**（`todo resolve --verb drop`；第一版 RA 作廢，已由 [673]／[676] 取代）。
  - [673]–[676] → `scripts/apply_ra_admission.py --pq2 <N> --digest <digest>`（6.7e 的 ask 規則每次都問了使用者）→ `commit_pending_intake.py`
    （commit `886a90a5`、`fc2b1416`、`d9e75078`、`a43ee9a7`）→ `complete-ra`（receipt＝action；digest；commit）。
    ⚠ **[673] 第一次停在 partial**（圖已寫入並投影，卡在改寫完成收據）：收據記 extraction canonical hash `8189ac4b`，那一版確實歸檔過，但檔名是
    走廊上線（09-11）前的原始位元組 sha（`…c48feb4b.json`），走廊只認 canonical 檔名。依 L17（只認得當初那個案例的機制當下修）以 commit `6aa35a08`
    把歸檔證據改成內容核對（放行條件不變寬；測試＋變異；OPERATIONS sandbox impact review），再以同編號同 digest 重試 → applied。
    沒有手動補新式檔名的歸檔檔（那個檔照設計只由 publish 產生）。另記：這份收據自 09-18／09-19 兩次改檔後就落後於抽取檔（那兩次沒走走廊）。
  - [671] → `loader/migrate_sourcedoc_json_section.py --corrections … --apply --pq2 671`：dry-run 與 hint 逐項相同（4 個抽取檔、3 份 SourceDoc、32 條）；
    一致性核對通過；收據 `loader/manifests/sourcedoc-corrections-20261003.{graph,json}-sync.json`；authority receipt `graph_sourcedoc_origin_sync`。
  - [672] → 先備份 `library/leads/pending_leads.json`（`library/private/backups/pq2-672-20261003T153708Z/`）、對 4 則呼叫 `correct_classified_by`
    （1 則 `interactive:graph_walk`、3 則 `triage_semantic_v1` → `interactive:directed`；舊值與編號記在 `classified_by_correction`、狀態不動）；
    authority receipt `lead_registry_correction`。⚠ 這一步**實際沒有持 writer lock**：[671] 的工具結束時把同 owner 的外層 session 鎖一起釋放了（§5 #17）；
    當時沒有其他 writer（daily 在 05:30、這是唯一的 session），實際沒有衝突，但與 hint 的「writer lock 下」不符，照實記錄。
  - [670] → 事前全圖匯出（`library/private/backups/pq2-670-20261003T153755Z/neo4j_export.json`，2698 nodes／6107 relationships，verify 通過）→
    dry-run（副作用只剩一個別名聯集、8 條、活的引用 0、兩份抽取檔指紋相符）→ `loader/migrate_identity_cleanup.py --apply --pq2 670 --backup-dir …`
    → `evidence_mismatch_vs_dry_run`＝[]；收據 `loader/manifests/identity-cleanup-20261003.result.json`；authority receipt `graph_migration`。
  - 三條把 go 前真實資料寫成前提的測試改用暫存名冊副本／虛構刊名重建前提、斷言不動（commit `dfa6d8c9`；修前全套 3 failed／3445 passed，修後 **3448 passed, 1 skipped**）。
- **這一批 go 之後（同晚量）**：全圖 canonical 邊 537 → 534、**外部印證 230 → 236**；沒升外部印證 未具名 13 → 8、名冊無名 4 → 0、轉述 2 → 1；
  對 6.0 凍結鍵 升 4（6.3c 2＋[670] 雙方聯合 2）／降 16（22 − RA 補回 6 − nava 那條併掉 1 ＋ [671] 的 Novanta 1）／同級互換 31（[671] 的論文）／消失 3（[670]），
  逐條歸得到事件；個股頁 COHR「6-inch InP Fab」、LITE「Pluggable turnkey ELS module」回到「有客戶或第三方印證」；讀圖現行 4、stale 0（這批沒讓任何讀圖變舊）；
  心跳「pq2 球在你手上 0」、①獨家且全自報 77 → 75、②解析不到的來源 5 → 3；③b「新增或重寫的帶 sub」4／4 → 4／10——多出的 6 筆是綜述論文的 assertion
  （[671] 改了它的 origin，內容指紋跟著變而被算成重寫；sub 值與引文沒變，本來就在 ③a 不含可替代性語言的 102 筆裡）。

## 7. 使用者動作（非阻擋）

- **10-04 05:30 之後看一眼心跳段 4 的「黃」**：應由 33 回到約 43（§2 ④）；仍是 33 就是 daily ②b 沒寫進募資文件清單。
- **重啟長駐 APP（預設埠 8790）**：它從 2026-09-10 起沒重啟過，跑的是舊程式；6.7b 之後重啟一次，頁面頂端的「請重啟」橫幅就會在下次程式更新時自己出現。
- **下一次跑 `record_trade.py` 或 `apply_ra_admission.py` 時會被問一次**（6.7e 的 ask 規則），確認那一次真的有被問。

## 8. 結案 R2（使用者已常規 opt-in）

乾淨 context、唯讀的審查者（2026-10-03 14:1x 起；中途撞到額度上限、17:3x 從中斷處接續；各版程式以 `git archive` 匯出、沒有建 worktree；
腳本與輸出在 scratchpad `r2close/`）。**Verdict：CONDITIONAL_GO。**

| 項 | 結果（審查者自己的命令） |
|---|---|
| 1 測試／invariants／函式增刪 | ✅ 3445 passed, 1 skipped；14 PASS；2673 → 2791（新增 120、拿掉 2、重複 0；6.0 名單 sha 與基準相同） |
| 2 證據等級 | ✅ 自己寫轉述比對與 `publisher_lifts`（只沿用 `resolve_origin`、`quote_names_company`）：外部印證 230、**違反 0**、反向檢查 0；對凍結鍵以「同一份圖換程式版本或 config」的反事實逐條歸因：只換 publishers 降 3（6.3b）、只換名冊升 2（6.3c）、只換程式降 19（6.4：未具名 13／名冊無名 4／轉述 2）、規則從不讓邊升級；合計升 2／降 22；圖上最新 `updated_at` 是 [666]，本 Phase 0 次寫圖；升級邊讀原文 3 條（Sojitz→Lynas、Credo→NPO、[666] 的 Sumitomo→Lumentum 重抓 mining.com 原網頁逐字找到） |
| 3 身分 | ❌ 字面不成立（名冊與圖上兩個代號都在）——[670] 未 go 的預期狀態；dry-run 預告的 apply 後狀態符合（105 → 103、OpenLight 三種寫法解析到 `co:openlight_photonics`、8 條、副作用只剩一個別名聯集）；nava 處置與收據一致（DEF 14A 重抓 SEC 原文逐字相符） |
| 4 staleness | ✅ 同級互換三條測試；SuperNova 真實重放判 stale_low；153bd093／d46c9e66／HEAD 三版程式對同一份圖快照，278 個節點的 `result_digest` 逐位相同；四份讀圖 ledger 存的 digest＝今天算出的值 |
| 5 稀釋燈 | ✅ 11 檔 EDGAR submissions 各抓 1 次、自己寫封閉清單：10 黃、LRCX 灰，窗與文件與正式路徑、基準 §20 逐份相同；「正式 APP 要等 10-04 daily」與程式一致 |
| 6 研究收據 | ✅ `corroboration_withheld.unnamed` 13 條逐條有去向（合計 22）；四個 RA digest 相符；兩份重讀的讀圖 `verify_citations` 0 問題（independent 規則空的成立）；四檔敘事前綴 sha＝基準、LITE 只改一句、其餘三檔七格逐字不變 |
| 7 心跳 | ✅ 自己跑的 74 行與 `hb_close.md` 只差標題時間；§1.1 逐條驗過（112 → 111＝CRDO、四盞非灰 3 → 0＝AXTI／COHR／LITE 的稀釋燈、304 盞的組成）；備份行 91 → 105 只能粗驗（6.0 沒存逐檔 mtime）；`SNAPSHOT_KEYS` 64＝64 |
| 8 殭屍 grep 與不變的東西 | ✅ 三個 0；trade_log、舊店三檔、主題等權組 ledger、AGENTS.md 的 sha＝基準；Sheet 0 寫入；字表不在 prompts／skills |

- **B1（阻擋）→ `AWAITING_HUMAN`**：ROADMAP ② 未生效；plan §0.5「結案前若 6.2 的編號仍未 go：停在 `AWAITING_HUMAN`（驗收②靠它，這是使用者的決定）」。所以 **ROADMAP Phase 6 不標 ✅、plans README 不改 completed**。
- **C1（解 B1，[670] go 並 apply 之後）**，五項全部成立才標 ✅：名冊 JSON 沒有 `co:openlight`、`co:nava_thailand`，共 103 家；唯讀 Cypher `MATCH (n) WHERE n.id IN ['co:openlight','co:nava_thailand'] RETURN count(n)`＝0；`company_id_for_origin('OpenLight', get_registry())`＝`co:openlight_photonics`；apply 的事後重算等於 dry-run 預告的 8 條；`python -m audit invariants` 14 PASS。使用者若明說要在 ② 未生效的情況下結案，記下這個決定、② 維持「未生效」。
- **B1 解除（2026-10-03）**：使用者對 [670] go → apply（§6）。C1 五項的實際輸出：①名冊 103 家、`co:openlight`／`co:nava_thailand` 都不在；
  ②唯讀 Cypher 兩個 id 的節點數 0（另以 `fetch_assertions` 查 697 筆 assertion，指著舊 id 的 0 筆）；③`company_id_for_origin('OpenLight', get_registry())`＝`co:openlight_photonics`；
  ④`identity-cleanup-20261003.result.json` 的 `evidence_changes` 8 條、`evidence_mismatch_vs_dry_run`＝[]；⑤`python -m audit invariants` 14 PASS（5462 筆）。
  C1＋C2 交給一個新的窄範圍審查者一起覆核（結果見本節最後）。
- **C2（已改，本 commit）**：gate 3 與 §1.2 改寫——每頁來源補上 `price_series`（`fetch_close_series`，6.7c）；個股頁寫成「四個維度＋程式 hunk 內無未解釋 diff；面板級對 6.0 無法驗證」。機械驗法：本檔 grep 得到 `price_series`／`close_series` 與「面板級」。C1＋C2 在 [670] apply 之後由一個新的窄範圍審查者一起覆核（plan §0.5 #14 的做法）。
- **非阻擋與處置**：N1 正式庫兩張空表與 sha 變動 → 寫進 §2 ④；N2 NVDA／META 公司債 → §2 ④ 註明「照封閉清單的字面成立」、實質見 §5 #10；N3 Fabrinet 的 Navanakorn 廠區 → §2 ② 勘誤、baseline §16.1 補更正註記；N4 敘事格層仍指舊讀圖 → §5 #16；N5 full chain 測試的呼叫改寫漏寫一支 → §3 更正；N6 UHP 延後的重問 → §5 #11 寫明；N7 independent 規則空的成立 → §2 ③ 寫明；N8 審查者唯讀連線碰到 -shm 旁檔（`decision_lab.db-shm`、Engine C 的 -shm）、兩個主 DB 的 sha 與 mtime 不變——照實記錄於此。
- **C1＋C2 窄範圍覆核（新的 sonnet 審查者、乾淨 context、唯讀；HEAD `914a42dd`）：Verdict GO。** C1 ①名冊 103 家、兩個 id 不在 ②Cypher 節點數 0
  ③OpenLight → `co:openlight_photonics` ④`evidence_changes` 8、`evidence_mismatch_vs_dry_run`＝[]（另讀 `loader/migrate_identity_cleanup.py` 的收尾：
  apply 對真圖重算、逐條比 dry-run，不等就中止、不會寫出乾淨的 result）⑤invariants 14 PASS（覆核當下 5459 筆，與 §8 記的 5462 差 3 筆＝會腐壞的佇列／watch 計數快照）；
  pq2 [670]–[678] 9／9 到終局（[673]–[676] receipt 的 commit 與 git log 逐筆相符）；C2 grep 命中 `price_series`／`close_series` 與「面板級」、
  gate 3 個股頁是 ⚪ 不是無條件 ✅。非阻擋三句：PointInTime 13 份未定日（已知限制）、GateDiscrimination 40／64 樣本不足（audit 自己標不判）、§5／§7 的後續事項。
  → ROADMAP Phase 6 ✅、`docs/plans/README.md` completed、plan status completed（2026-10-04）。
