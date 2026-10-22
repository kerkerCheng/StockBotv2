# Phase 7 plan——已完成段落（逐字封存，2026-10-22）

> 從 [`docs/plans/2026-10-04-001-research-phase7-research-edge-plan.md`](../plans/2026-10-04-001-research-phase7-research-edge-plan.md) 逐字搬出（使用者 10-22「輕量整理」）：§0.6 執行偏差紀錄、§1–§6b（開發 Step 7.0a–7.0g，全部 ✅）、§8（回放 7.2，✅）。plan 裡留著各節標題、指到這裡；進度表、amendments、7.1／7.3／7.4／7.5 與 §14 待決清單都還在原檔。

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 7.0a | §1「驗證集（附錄 A 的 14 個 case）」 | 登記 **16 個**：附錄 A 的 14 個＋二階 case **O1-U**（InP 上游：銦、晶體生長、出口管制）與 **O6**（光通訊磊晶與 MOCVD 產能）；附錄 A 已 append 這兩列 | §10 寫「二階瓶頸三個 case……三個 case 在 7.0a 已登記，wave 2 只能 append 新 case、不能改這三個的判準」，但附錄 A 只有 P2——不在 7.0a 登記，另兩個就會在 wave 2 才定判準（正是 §10 要防的事後放寬）。附錄 A 本身寫「可 append、不可改」 |
| 2 | 7.0a | §8 R2「抽樣規則先寫進 replay 報告再看結果」 | 抽樣規則與**樣本本身（36 則 lead id）**在 7.0a 就固定進 registration §7.3／附錄 C（分層、不按比例、合併時依層母體加權；層內順序＝lead id 加固定前綴後的 sha256，程式見 registration 附錄 C；排除 P3 的五則）；§8 R2 那一段已補指向 | 比「寫進 replay 報告」更早凍結，7.2 的執行者沒有選樣裁量；EDGAR 237／348 照比例抽會讓樣本幾乎只剩例行申報，所以不按比例、合併時加權 |
| 3 | 7.0a | §1 第 2 項 T0 manifest 的內容清單 | 照清單全做，另加四類：**逐邊證據等級**（534 條，與走圖／心跳同一條路 `_classify_edges`）、S1 框架 40 則、parked×`original_obtained` id 清單、追蹤表 history／paper 名單、舊店三檔與 trade_log 的 sha256；07:06:17Z 先產過一版（沒有逐邊等級），**在任何使用之前刪除重產**（07:09:14Z） | H3／H4 的分組要以 T0 的證據等級為準（之後的升降不得改分組），不凍結就會被之後的更正污染；S1、R2 的框架在看結果之前凍結；§11 第 7 項「另核對」要比對舊店與 trade_log 的 sha256 |
| 4 | 7.0a | §7 第 3 項 S1「每則……寫進截圖假說層」 | registration §6：主張類型封閉四選一（結構／財務／價格／無可否證主張）；**只有結構與財務型寫進截圖假說層**；價格型只記價格路徑；無可否證主張（只點名、情緒、問句）只計數、在 `cases.md` 記裁決「不適用」 | 把沒有可否證陳述的點名寫進假說層，會變成一條永遠叫不醒的等待（INV-2）；ROADMAP 驗收④「40 則各有裁決或到期」照算——「不適用」是預先登記的裁決之一，筆數照印 |
| 5 | 7.0b | §2 第 2 項「`loader/migrate_sourcedoc_json_section.py`（兩處）與 `loader/migrate_identity_cleanup.py` 改用它」 | 三支照做，另把 `engine_c/migrate_fundamental_metrics.py` 自己寫的同一套「同 owner 未過期就不取不放」也換成 `writer_lock.hold` | 那是同一個判斷的第二個 owner（development-flow INTAKE 第 2 問）；L17 三問的「對稱面做了嗎」。行為不變，既有的巢狀測試照綠 |
| 6 | 7.0b | §2 第 3 項「以 max(memo 生成日, last_checked) 對 check_interval_days（或直接用 `is_due`，一個 owner）……另印一行『沒有 lifecycle 的舊 memo N 份』；變異：把 last_checked 拿掉 → 真逾期要被報」 | 取 `is_due` 當唯一 owner：「memo 生成日」那一套整段拿掉；`max(memo 生成日, last_checked)` 只用來印天數。舊 memo 那一行**只在 hook 有話要說時附上**，健康審查「Memo 新鮮度」節每天照列；lifecycle 讀不到時 hook 明講。變異改成「拿掉 last_checked **與** next_check → 要報」（`is_due` 下只拿掉 last_checked，next_check 仍是出口、本來就不該報），另加兩個變異（`check` 不看 `is_due`、拿掉「讀不到要說」） | 一個 owner（`thesis/lifecycle_schedule.py` 自稱「什麼時候該重看的唯一權威」）；舊 memo 那行若單獨每天亮，就是把一個恆亮換成另一個恆亮（L14）；拿掉 memo 日期那套之後，「讀不到」不能靜默（INV-3） |
| 7 | 7.0b | （plan 沒寫） | `DATE_RE` 認得「`**生成日期：** 2026-08-04`」的粗體寫法（L17 當下修，三行） | 先前三份新格式 memo 全退回檔案 mtime；現在只影響「幾天沒核查」的天數呈現 |
| 8 | 7.0b | §2 第 1 項「八欄的範圍欄（或 STEP_RESULT 對應欄）加『暴露它的案例』」 | 八欄沒有「範圍」欄：INTAKE 加一行 `Case:`（範圍判定就在這裡做），收尾在 `Zoom / Review` 重抄；`docs/AGENT_WORKFLOW.md` 同步；不開第九欄 | `tests/test_agent_workflow.py` 數 STEP_RESULT 剛好八欄；新測試釘住 `Case` 行（刪掉它不會讓任何東西變紅，系統只會安靜地回到「想到就做」） |
| 9 | 7.0c | §3 第 2 項「`revenue_ttm`（近四季營收，Engine C 機械歷史表，含口徑與 as_of）」 | 選取 read model **既有**的 `revenue_ttm`（Engine C 快照的 TTM，財報幣別）；填值寫成「近四季，快照 <日期>」 | 同一項要求「先確認兩個值在 read model 裡已有 Datum」——它已在，而且稽核區印的就是這一格；另從機械歷史表組一格會讓同一頁出現兩個營收數（L12、L16）。快照的日期是取數日、不是財報期末，所以字面寫「快照」（INV-6） |
| 10 | 7.0c | §3 第 2 項「`market_cap`（Engine C 快照的市值，含幣別與 as_of）」 | read model 既有的 `market_cap` 是「price × shares、未正規化」——builder 另組一格 `market_cap_settlement`（同一份快照 × 名冊報價單位的換算係數——係數由 sources 從 `identity.currency` 查好注入，builder 是純函式不碰 identity；不做匯率；報價單位未登記 fail closed），placeholder 選它；原格語意不動 | 直接用未正規化那格，IQE.L 會填出「729.5 億」（便士）——真資料核對：換算後 7.3 億 GBP。一格不承載兩種語意（L12） |
| 11 | 7.0c | §3 第 3 項的白話「拿今天的倍數（EV/S，虧損時 P/S）」 | 照 `alpha/three_questions.py::decide_basis` 寫：「有獲利、而且有同一期的淨負債資料時用 EV/S；其餘（虧損、台股、資料不齊）用 P/S」，其餘照 plan 的意思 | P/S 不只在虧損時用（COHR 是因為營業利益資料停在 2024 年中）；自己寫給人讀的事實套同一套追源紀律（L11-2） |
| 12 | 7.0d | §4 第 2 項「登記一筆 `semantic_condition` watch，來源鍵與反證分得開……類別是 `confirm`（`watch_category` 加一類）」 | 照做；**怎麼分**：watch 多一個 `condition_role=confirm`（判斷只住 `engine_b/event_watch.py::is_confirm`），`disproof_ref` 照舊當「指回原文的來源鍵」（＝`source_ref`），不另開 `confirm_ref` 欄位；寫入端另加兩條拒收（同版重複、與反證同一條件） | 用 `disproof_ref` 認「語意 watch」的地方有八處（喚醒、佇列、待辦、liveness、audit、變動偵測）——另開欄位漏改一處，加碼條件就叫不醒、沒人消費（INV-4）；沿用它的代價是名字不貼切，分角色的地方（計數、downside、可開、判定標籤、audit 解析）逐一改並有測試＋變異。交 R2-a 挑戰——**R2-a 判定不構成 L12**：「算不算反證」另開封閉欄位，`disproof_ref` 仍只承載「指回原文的來源鍵」一種語意；代價只是名字不貼切 |
| 13 | 7.0e | §5 第 1 項「每檔輸出 `shared_with_holdings: [{held_ticker, shared_anchors[], shared_layers[]}]`」 | 欄位叫 `shared_bet`：`{rows: [{ticker, company_id, state: "held", shared_anchors[], shared_layers[]}], absence, anchors_absence, anchors_as_of, lines[]}`——「持有」只以 `state` 的值出現；每一句在 `alpha/providers/candidates.py::shared_bet` 組好，候選板與個股頁照印 | 個股頁有兩道既有的欄位名掃描（`tests/test_stock_page_phase3.py`、`tests/test_analyst_view.py`：`held`、`holdings` 不得當欄位名——分析畫面不帶部位欄位），plan 的名字兩個都會被攔；換同義字繞過是 L16 明文禁止的，所以把「持有」放回候選狀態既有的值字彙。缺席有兩種分型（Sheet 讀不到、結構表讀不到；L16 由產生端宣告），所以外面包一層而不是裸 list |
| 14 | 7.0e | §5 第 1 項「materialize 一次載入（同一個 session）……需求錨取自結構表的逐列錨（`query.bottleneck.structure_table`……唯一來源）」 | 讀**同一輪** `--structure-table` 寫下的 `structure_table` artifact（`webapp/materialize.py::bet_structure`；artifact 是 `structure_table()` 輸出照抄），不另開 Neo4j 連線重算；有共用錨時句子標「需求錨取自 <日期> 的結構表逐列錨」；讀不到＝需求錨這半邊 `upstream_unavailable`、層照比 | 「載入結構表」已有三個 owner（`query.bottleneck` CLI、`materialize_structure_table`、graph provider 的快取），再開第四個就是 L16；daily 的 materialize 同一輪先寫結構表（`--structure-table` 排在個股頁與候選板之前），讀它＝同一份、少一次全圖查詢，個股頁與結構表頁的錨保證是同一份 |
| 15 | 7.0f | §6 第 2 項 apply「寫成 lead：`source=web_radar:<theme>`、`source_class=secondary`、tier 4」 | lead 的 tier 只住 triage 的結果（1–4），登記時沒有這一欄：雷達的 lead 在 triage 之前的 pq1 排序本來就是 tier 4（`engine_b/priority.py::rank_lead` 的預設），triage 批次裡另排在所有非雷達 lead 之後（偏差 #16）；triage 讀過內容後給的 tier 照它——雷達搜到公司官網的新聞稿可以是 tier 1 | 登記時寫死 tier 4 會蓋掉 triage 對**文件本身**的判斷：「發現管道是二手」與「文件是二手」是兩件事（L12）。交 R2-b 挑戰 |
| 16 | 7.0f | §6 L11-6 ④「30 則上限下要確認它不擠掉 harvest 的 lead（批次的選取順序照實寫）」 | 查證結果是**會擠**：pending lead 的排序先比 relevance（提到持股排最前）才比首見時間，雷達點名 COHR／SIVE.ST 的 lead 會排到 harvest 的前面，暴量那天最多把 `radar.max_items` 則 harvest 的 lead 擠到隔天。改成 `engine_b/cli.py` 的 triage 批次先把雷達的 lead 移到所有非雷達 lead之後再截上限（兩邊各自原順序不動；note 印「外部雷達 N 則排在最後（進本批 k 則）」——R2-b 指出原本只印截斷前的數）；測試＋變異 | 讓擠掉不可能發生（根除），不是只把它印出來；這是加一道規則——拿掉的方式（雷達不進 triage）會讓它的 lead 永遠沒人分類（INV-4） |
| 17 | 7.0f | §6 第 4 項「`config/themes.txt` 加 `power`（…）與 `cooling`（…）兩個主題」 | 照加，**只有描述與關鍵字、不列核心公司**；會誤報的短字改長寫法：英文 GOES（＝goes）、單獨的 transformer（AI 模型）、CDU（政黨）、SST 不放，中文「冷板」（冷板凳）、「套管」改「水冷板」「變壓器套管」 | 核心公司會餵進 tracked（`routine_config.theme_core_tickers` → materialize 頁數、EDGAR 監看、pq1 relevance），plan 說核心公司由 7.1 的 decompose 再修——不在雷達這一步先擴；主題比對英文不分大小寫、要詞邊界，中文是子字串 |
| 18 | 7.0f | §6 第 2 項「`run_claude` 加一個只給雷達用的選填收集器（收搜尋結果裡的網址）」 | 照做（`observe` 參數＋`SearchCollector`，只收 `tool_use_result.results[*].content[*].url`，摘要字串裡的網址不收），另外：①收集器同時收搜尋結果的**標題**——lead 的標題用它、不用 LLM 寫的；LLM 那句事實放 `refs.radar_fact`（不放 `raw_text`）；②`run_claude` 對**每一步**都把權限被拒判失敗（零工具步驟不可能被拒，行為不變）；③沒有 `radar` 區塊＝關閉 | 探針 A：不放行時 CLI 拒絕 WebSearch、照樣回 `is_error: false`＋空結果——不判失敗，「被擋住」就和「沒東西」同形（L13）；標籤要指得回原文（L18）；新的無人值守能力要明寫打開才跑 |
| 19 | 7.1 | §7 第 6 項「落 `library/private/research_notes/layer_notes/mat_inp_epitaxy.md`」 | 檔名照提議的節點 id：`mat_inp_epiwafer.md`（節點 `mat:inp_epiwafer`，RA [715]） | S4 規格「主鍵是節點或轉換 id」；被供應的東西是磊晶片——L4：節點是換掉交易對手也不變的那個東西；與 `mat:inp_substrate`、`prod:quantum_dot_laser_epiwafer` 的命名一致 |
| 20 | 7.1 | §7 第 6 項 ④「每條主張登記成 watch」 | 牽涉公司賭注的 7 條主張掛在四份敘事的反證上（2455.TW、IQE.L、3081.TWO、4971.TWO 換版）；純屬這一層的 3 條（A6–A8）列在層說明、等 `mat:inp_epiwafer` 入圖後掛層讀圖 | 語意 watch 的來源鍵只認 thesis／reading／brief（failure log #31）；個股頁 plan S4 的程式（層說明 ledger）落地前，層說明沒有自己的來源鍵——不另開臨時來源鍵（那是動 contract） |
| 21 | 7.1 | §0.1 Q2「新的鏈……光通訊＋電力＋散熱」、§13「decompose 同時 open 最多兩個：電力、散熱正好兩個」 | 使用者 2026-10-06 加選第四條鏈 **AI 生醫**（pq2 [723]，稽核用、受理即 resolve），照 §7 第 2 項電力／散熱的七步走；registration 檔尾 append case **B1**（開題日＝該 commit 日）；`config/themes.txt` 加 `aibio`（只放關鍵字，核心公司由 decompose 定）；R3 母體不追加（§14 第 11 項） | decompose 選題是使用者的（AGENTS「新題材由使用者選」）；「同時 open ≤ 2」數的是**未 resolve 的提案編號**（`engine_b/decompose_proposals.py::open_proposals`），[685]／[686]／[723] 都受理即 resolve，所以不超限——§13 那句是寫 plan 當下的計數，不是第二條上限 |
| 22 | 7.0g | §6b 第 2 項「母體外……邊緣沒座位（列「坐哪一層」短檢查……結論＝補座位走 RA，或 v2 敘事寫「不坐任何層」）」；第 3 項「只因 `research` 卡住的檔逐檔列出改前改後的 readiness」 | ①短檢查結論分**三種**（補供貨邊／開發中／不坐任何層或在需求側），②③都寫 v2 敘事；②research 降選配時，refresh 的「需要重看」不再升級成整頁旗標（不保留「只旗標不擋」）；③只卡 research 的檔是 0，改列「research 是卡點之一」的 10 檔改前改後 | ①只有 develops 邊的公司（#22 第二型）不是「不坐任何層」，壓成一種就是 L12；②真實資料這個旗標 23／23 是雜訊（L14-4 恆亮），保留它等於延續退役估值鏈的殘留——可逆（§14 #17）；③照實量，0 就寫 0 |
| 23 | 7.1（個股頁 S4b） | §0.3「不開新 state kind」 | 開了第 9 個 kind `layer_notes`（層說明閱讀頁） | 個股頁 plan 2026-10-07 amendment（使用者選「A＋純文字閱讀頁」）原文就是「APP 新 kind」；§0.3 那句管的是 Phase 7 自己的 Step（7.0d 的加碼條件做成 v2 選填欄、不另開 kind），使用者直接指示的旁支不受它限制（AGENTS「使用者主動指示＝已授權」）。L11-6 ④ 實查：今早 daily 產的 6 個個股頁與新程式重產的 readiness、讀圖面板狀態、`freshness_identity` 6/6 相同 |
| 24 | 7.1（個股頁 S1） | 7.1 的研究項（積壓、電力與散熱、S1 抽樣、O3、O5、InP 磊晶層說明）不含個股頁 plan 的工作；個股頁 S1 凍結 v1.0 的負錨點驗收屬個股頁 plan，原排在「第一波走完、使用者點名 S2」之前另做 | 負錨點兩檔的時光機頁併入 7.1 續工（候選合晶 6182、矽創 8016） | 使用者 2026-10-07「D7選B」（個股頁 plan 待決 D7）：負錨點本身是研究（起漲前的時光機頁），驗的是十三塊能不能分辨「量起來後翻倍」與「量起來後先崩」——對上 brainstorm F51「覆蓋晚於倍率」與 H11；做完 schema 可凍結 v1.0，個股頁 S2 不必等第一波結束。不改 7.1 的定義與驗收 |

---

## 1. Step 7.0a 預先登記＋T0 凍結（Z0；強模型寫登記內容）

**改哪裡（新檔）：** `docs/reports/phase7/registration.md`、`docs/reports/phase7/cases.md`、`docs/reports/phase7/failure-log.md`、`docs/reports/phase7/cohort-changes.md`；
`library/private/measurement/phase7/T0-<日期>.json`（private；不進 Git）。

**怎麼做：**
1. **`registration.md`（commit 後凍結）**：
   - 十個假說 H1–H10（proposal §3），每個寫：一句假說、今天的證據（含 n）、用哪些 case 測、**殺死條件**（什麼結果出現就判削弱）。H8（point-in-time）寫明是效度條件、不是 edge 假說。
   - 驗證集（附錄 A 的 14 個 case），每個寫：case id、鏈、類型、測哪幾個假說、**開題時已知**（引用 ledger id 與日期）、預期會暴露的 failure mode、支持／削弱的判準、裁決點與日期。
   - 裁決規則：快／中／慢三個迴路的單位與裁決來源（proposal §5.2）；「錯」分**當時已有反例**／**之後才出現**／**未定日**（沿用 `alpha/structure_reading/predictions.py` 的分法）；
     2×2 的判法（結構斷言被證實或推翻 × paper lane 錨點起對**該鏈主題等權組**的超額，proposal §5.3）。
   - failure log 模板（使用者七問，附錄 B）與開發 gate（≥2 個 case 重複、第 3 問答得出來、第 7 問指得到某個迴路的量）。
   - **漏網稽核的母體（R3 用，T0 定、之後只 append 不刪）**：三個主題等權組成分（光通訊現有；電力、散熱在 7.1 定義後 append）＋一份約 40 檔的「AI 基礎設施觀察名單」，
     **今天列、看結果之前列**，涵蓋光通訊、電力設備、散熱、先進封裝／測試、記憶體各數檔（每檔一句為什麼在名單上）。
   - SNS 抽樣規則（S1 用）：先寫抽樣規則（例：帳號計分表 `metrics_first_call_per_symbol` 的 40 檔首次點名、每檔取第一則），**看結果之前寫**。
2. **T0 manifest（唯讀；第一份手動以既有 CLI 與唯讀查詢產生，手動做不下去才寫腳本——L17）**，內容：
   名冊公司 id 清單與 sha256；`onboard-candidates` 清單；lead id 依狀態分組（parked、triaged_go）與 sha256；`crons/harvest_config.json`、`config/signal_sources.json`、
   `config/themes.txt` 的 sha256；assertion id 集合的 sha256、筆數與最大 `updated_at`（唯讀 Cypher）；SourceDoc 筆數；讀圖與敘事 ledger 各檔 sha256 與現行 id；
   `thesis/lifecycle.json` 與各 memo 的 sha256；截圖假說 id 與 sha256；watch registry 的 id、kind、status、expires 與 sha256；候選狀態序列最後一列；主題等權組 id；帳號 tier；
   生成時刻與當天心跳檔名。**產生用的程式碼貼進 `registration.md` 附錄**（scratchpad 會消失，評估要能重算）。
3. **`cases.md`**：每個 case 一段，開題時只放「登記見 registration §x」；之後的研究產出（只寫 id）、裁決（每次 append 一行：日期、文件、結論）、2×2、failure log 條目都 append 在該段下。
4. **`failure-log.md`**：模板＋空表；每條帶 case id 與第幾次出現。
5. **`cohort-changes.md`**：第一筆「T0」；之後每次監看來源或母體變動 append 一筆（日期、改了什麼、為什麼）——**使用者之後加 X 帳號就記在這裡**（新帳號 probation、加入日起量、不回溯），
   7.0f 雷達上線、7.1 新增 `themes.txt` 主題與主題等權組也記在這裡。

**怎麼驗：** `registration.md` 的 commit 時間早於 wave 1 任何新讀圖／敘事的 `created_at`（7.1 結束時核對，讀圖、敘事 ledger）；
T0 manifest 的各計數與當天心跳相同（registry、ledger）；`registration.md` 每個 case 的欄位齊全；manifest 不在 `git ls-files` 裡。

L11-6 ④：最先壞的是「T0 之後才寫的紀錄被算進 T0」——manifest 的生成時刻與各 ledger 最後一行的 `created_at` 對照、寫進八欄。

## 2. Step 7.0b 開發 gate 落地＋兩個當下修（Z1，R1）

1. **開發 gate**：`skills/development-flow/SKILL.md` 八欄的範圍欄（或 STEP_RESULT 對應欄）加「暴露它的案例：case id 與第幾次出現；使用者直接指示的寫『使用者指示』」；
   跑 `python scripts/sync_agent_skills.py`；`tests/test_agent_workflow.py` 若釘住欄位格式，同 commit 改。AGENTS 那一句已在本 plan 的 commit 落地（§0.4 A2），本 Step 只核對測試綠。
2. **巢狀 writer lock（Phase 6 #17，L17 當下修）**：`engine_b/writer_lock.py` 加一個會看巢狀的 context manager——**同 owner 的未過期鎖已在就不 acquire、不 release、不縮短 TTL**；
   `loader/migrate_sourcedoc_json_section.py`（兩處）與 `loader/migrate_identity_cleanup.py` 改用它。測試：外層鎖在內層結束後仍在且 TTL 不變；單獨跑時照常 acquire／release；
   不同 owner 照舊互斥。
3. **thesis 逾期提醒量錯（L17、L14：恆亮＝零鑑別力）**：`crons/thesis_freshness_check.py::check` 目前量 memo 的「生成日期」、不看 `thesis/lifecycle.json`。改成：
   有 lifecycle entry 的 thesis，以 `max(memo 生成日, last_checked)` 對自己的 `check_interval_days`（或直接用 `thesis/lifecycle_schedule.is_due` 那一套，**一個 owner**）；
   沒有任何 lifecycle entry 指向的 memo（例：`cpo_v1_lane_memo.md`）**不算逾期**，另印一行「沒有 lifecycle 的舊 memo N 份」（INV-3：不靜默丟）。
   測試：sivers（memo 08-29、last_checked 09-29、30 天）在 10-04 不逾期、在 10-30 逾期；cpo_v1 不出現在逾期、出現在舊 memo 行；**變異：把 last_checked 拿掉 → 真逾期要被報**。

**怎麼驗：** `pytest` 綠；本機起一個 session 看 SessionStart 不再報兩則假逾期（截圖或輸出貼八欄）。
L11-6 ④：最先壞的是「thesis 真的逾期時提醒不響」——上面的變異測試就是它；另看 `thesis/lifecycle.json` 三筆在 10-04 與 10-30 的判定。

## 3. Step 7.0c 敘事範本：翻倍條件、兩個 placeholder、「已定價」白話、重押換格層引用（Z1，R1）

1. **範本**（`alpha/narrative/contracts.py::BRIEF_FRAME_V2["what_must_be_true"]`）：題目改成「什麼必須為真？**要翻倍需要什麼**（營收、出貨、產能或毛利要到多少、在什麼時候）？
   錯的訊號是什麼？」；`do_not` 改成：「翻倍的起點可以用 `{market_cap}`；條件用營業數字。⚠ 不寫目標價、股價、報酬率；`{price}`、`{own_history_pctile}`、`{cohort_median}`
   仍不得出現在這一格」。`WHAT_MUST_BE_TRUE_FORBIDDEN` **不動**（型別層的禁令照舊）。
2. **placeholder**：`PLACEHOLDERS_V2` 加 `market_cap`（Engine C 快照的市值，含幣別與 as_of）與 `revenue_ttm`（近四季營收，Engine C 機械歷史表，含口徑與 as_of）；
   填值只走既有 authority，讀不到印「（尚無）」並帶理由（同既有 placeholder）。先確認兩個值在 read model 裡已有 `Datum`（沒有就由 builder 從既有取數層組一格，**不在 compose 端算**）。
3. **「已定價」白話**：一份字串 SSOT（放在 `briefing/analyst_view/contracts.py` 的白話別名旁），經 `.meta.json` 送到 APP，首屏「已定價嗎」與稽核區那一題的標題旁各印一次。內容（可微調用字，意思不變）：
   「拿今天的倍數（EV/S，虧損時 P/S）跟它自己過去三年比，落在第幾百分位——回答『市場是不是已經對它重新評價過』。**不是『太貴』，也不是目標價。**
   高百分位代表價格已經假設好消息會持續；不代表不能再漲，代表好消息一斷會跌得比較深。這一格有沒有區分力還在量（Phase 7 R1）。」
4. **重押讀圖時換格層引用（Phase 6 #16，L18）**：`alpha/providers/briefs.py::v2_write_problems` 加一條——新紀錄的 `rides[]` 已指向某節點的現行讀圖時，
   任何一格的 `evidence_refs` 若指向**同一節點**已被取代的讀圖 id → 拒收並列出是哪幾格、該換成哪一個 id（**不自動改寫 session 的文字或引用**）。既有紀錄不動（append-only）。

**怎麼驗：** `pytest` 綠（範本文字、placeholder 填值與缺席、`what_must_be_true` 仍拒 `{price}`、舊讀圖 id 被拒、新讀圖 id 通過）；`python -m alpha research AXTI` 的 packet 印新題目；
真實四檔 ledger 20 行全部照常解析與填值；`python -m webapp materialize AXTI` 後個股頁「已定價嗎」旁有白話（Edge headless，見 §8）。
L11-6 ④：最先壞的是既有四檔敘事的填值——新 placeholder 不在舊紀錄裡，fill 不得因此報錯或改變舊紀錄的輸出（四檔 brief 面板文字改前改後逐字相同）。

## 4. Step 7.0d 敘事「加碼條件」`confirm[]`（Z2，R1＋**R2-a 常規 opt-in**）

**語意（A2）：** 加碼條件＝「這件事發生，代表結構被確認了」（客戶自己的文件點名它、合格狀態走到量產、數字出現在營收裡……）。**觸及只提醒、不是買進訊號、不改候選狀態**；
與反證對稱：寫下即登記 watch、有到期、到期是重問。

1. **契約**（`alpha/narrative/contracts.py`）：`NarrativeConfirm`——`condition`、`check_frequency`、`action_48h`（觸及後 48 小時：研究 session 重寫敘事，換候選狀態或寫明不變）、
   `entities`（至少一個 `co:*`）、`expires`、`source`（前綴規則同反證，指得回原文）。v2 的選填欄 `confirm[]`。
   **id 穩定：** `new_brief_id` 只在 `confirm` 非空時把它納入 id 欄位集合（或等價做法）——**既有 20 行重算逐位相同**（測試讀真實 ledger 的副本；§0 第 7 條）。
2. **登記**（`engine_b/narrative_watches.py::register_brief_watches`）：每條 confirm 登記一筆 `semantic_condition` watch，來源鍵與反證分得開（例：`brief:<brief_id>#c<n>`），
   **類別是 `confirm`**（`engine_b/disproof.py::watch_category` 加一類）——**不得被算成反證**：心跳「反證：在盯／觸及」、downside 面板、圖預測表、`narrative_watches.blocking_for_open` 都不吃它。
   換版／撤回收掉舊版 active 的 confirm watch（同反證）。
3. **觸及與到期**：觸及（互動 session `event_watch judge` 判 yes）→ 候選板那一列與個股頁印「加碼條件已觸及：<條件>（<日期>）——提醒，不是買進訊號」，並進佇列段 `narrative_rewrite`
   （新一版敘事的 `acknowledged_touched` 處置字彙加 `confirmed`）；到期未觸及 → 同樣進 `narrative_rewrite`（「確認事件沒在期限內發生」本身就是資訊）。**不自動改候選狀態**。
4. **消費端**：心跳段 2 加一行「加碼條件：在盯 N｜觸及待處置 M｜到期待重寫 K」（`SNAPSHOT_KEYS` 加鍵）；候選板列與個股頁（7.0e 的第③題旁）列出每條加碼條件與狀態；
   audit 的 Expiry、QueueLiveness 認得這一類（觸及與到期都有 consumer：`narrative_rewrite`）。
5. **sandbox impact review 五步**（OPERATIONS）：materialize 與心跳讀新欄位、registry 多一類。

**怎麼驗：** `pytest` 綠：契約、登記、類別分離（**變異：把 confirm 算成反證 → 紅**）、心跳行、候選板列、id 穩定（真實 ledger 副本 20 行）、到期進 `narrative_rewrite`；
`python -m audit invariants` 綠；真實 registry 上心跳的「反證：在盯 37」改前改後相同（今天沒有 confirm）。
**R2-a `WORK_REQUEST`**：審查者自己重算真實 ledger 的 20 個 `brief_id`、跑類別分離的變異、看觸及／到期兩條路都有 consumer、確認候選狀態不會被自動改。
L11-6 ④：最先壞的是心跳「反證：在盯／觸及」的計數與 `blocking_for_open`——confirm watch 若被當成反證，「可開」的前提會被它卡住。

## 5. Step 7.0e 個股頁首屏五題＋共用需求錨（Z2，R1）

1. **共用需求錨**（A3）：materialize 一次載入（同一個 session，**不在 request path 算**）——每檔的需求錨取自結構表的逐列錨（`query.bottleneck.structure_table` 的 `demand_anchor`／`anchor_basis`，
   **唯一來源**），坐的層與插槽取自 `seat_readings_context`；已持有的 alpha 檔取自 `held_index`（Sheet、alpha、股數 > 0）。每檔輸出
   `shared_with_holdings: [{held_ticker, shared_anchors[], shared_layers[]}]`（實作名 `shared_bet`，偏差 #13；需求錨讀同一輪的結構表 artifact，偏差 #14），依 ticker 字母列、**不打分、不排序、不加權**。缺席分型由產生端宣告：Sheet 讀不到＝持有判定暫停（`upstream_unavailable`）；
   走不到任何需求錨＝照實寫。注入候選板列與個股頁（與 `candidate`／`downside` 面板同一種「來源不在 read model」的注入例外）。
2. **首屏五題**（A1）：`webapp/static/app.js::briefCard` 依序排五題，各題底下放既有句子與燈，**不改任何 `Datum`、不改 ledger**：
   ①這一檔押的是什麼（`our_bet`；`bottleneck`、`position` 收在題下）②押對了夠大嗎（`what_must_be_true` 的翻倍條件、`demand`、「已定價嗎」與白話、「出現在數字裡了嗎」）
   ③錯了怎麼知道、哪天知道（每條反證與它的 watch 狀態、`when`；7.0d 的加碼條件列在旁邊）④會不會死（歸零燈；灰＝沒量到）⑤是不是新賭注（共用需求錨／同一層）；
   候選狀態那一行（狀態、理由、在等的 watch）照舊。**五題的標題與「哪一格放哪一題」的對照只有一份**（放 `briefing/analyst_view/contracts.py`，經 `.meta.json` 給 APP；
   app.js 不維護第二份，L16）。沒有 v2 敘事的頁照舊版面（「還沒寫短評」）。
3. **sandbox impact review**（materialize 多讀結構表與 Sheet 的 held_index）。

**怎麼驗：** `pytest` 綠（compose／meta 的五題對照、`shared_with_holdings` 的組法與缺席分型、request path 四種證明照綠）；**真資料重跑 materialize 後 Edge headless 實點**
（memory「APP 前端用 headless Edge 驗」的做法）：AXTI、COHR、LITE、SIVE.ST 四頁五個標題都在、句子沒少；COHR 與 SIVE.ST 這兩檔已持有的互相列出共用的層或錨（今天兩者都在 CW DFB 這一層）；
候選板列印共用需求錨；首屏沒有任何排序或分數字樣。
L11-6 ④：最先壞的是個股頁 artifact 的 `content_digest` 與 readiness——只改呈現順序與多一個注入欄位；76 頁 digest 的變動要全部歸因到 `shared_with_holdings`（`freshness_identity` 不含它）。

## 6. Step 7.0f 外部雷達（Z2，R1＋**R2-b 常規 opt-in**；sandbox impact review）

1. **先探針（結果寫八欄）**：以 `--tools WebSearch` 跑一次 `claude -p`（其餘旗標同 `crons/llm_step.py::llm_argv`），確認：init 的 `tools` 恰為 `WebSearch` 與 `StructuredOutput`；
   `-p` 模式下 WebSearch 要不要權限、**最窄的放行方式**（`--settings` 的 permissions allow 或其他）；stream 裡搜尋的 tool_use／tool_result 長什麼樣、網址在哪一欄。
   `FORBIDDEN_LLM_FLAGS` 對 triage／預篩**照舊**；雷達有自己的 argv 函式與自己的禁用清單（測試釘住）。
2. **程式**：`crons/llm_step.py` 加 `radar_argv`、能力檢查依步驟參數化（雷達期望 tools＝{WebSearch, StructuredOutput}，其他五欄同既有）、`run_claude` 加一個只給雷達用的選填收集器
   （收搜尋結果裡的網址）；`crons/radar_prompt.md`、`crons/radar_schema.json`（strict）；雷達的 prepare／apply（放 `engine_b/`，例 `engine_b/radar.py`）：
   - prepare：prompt 由程式組——`config/themes.txt` 的主題與關鍵字＋在盯的語意 watch 條件原文與實體（讓它找得到「碰到哪條反證或加碼條件」的新聞）；**不讀 Sheet、positions、NAV、私人路徑**（測試以哨兵證明）。
   - LLM 回：`items[{url, title, publisher, published_at|null, fact（一句、繁中）, entities[], theme（主題 slug 或 new）, relates_to[]（watch id）, why}]`、`no_material_change`。（實作與 tier、triage 順序、主題、收集器的差異見偏差 #15–#18）
   - apply（程式驗證後寫入）：**網址必須出現在同一次執行的搜尋結果裡**（否則拒收、計數）；正規化網址後與 lead registry 去重；`published_at` 讀不懂就 null（不拿抓取日冒充，INV-6）；
     每日上限 `radar.max_items`（預設 5，超過的計數不寫）；實體以名冊寫法解析，解析不到留原字；寫成 lead：`source=web_radar:<theme>`、`source_class=secondary`、tier 4、
     `refs.radar_run`、`refs.relates_to`；收據 `library/private/heartbeat/radar_<日期>.json`（收／拒與理由，INV-3）。**不喚醒語意 watch**（T0 只認一手）。
3. **daily**：`DAILY_STEPS` 在 ① harvest 之後、⑥ triage 批次之前加三步（prepare → LLM 提議 → 保險檢查 → apply），雷達的 lead 第二天（或同一輪，視順序）進 triage；
   `config/daily_routine.json` 加 `radar` 區塊（`enabled`、`max_items`、`timeout_minutes`）；`llm.executor=none` 或 `radar.enabled=false` 都讓它記 skipped（回滾開關）。
4. **主題**：`config/themes.txt` 加 `power`（超高壓變壓器、開關設備、電工鋼／GOES、套管、分接開關、800VDC、固態變壓器、SiC／GaN 功率元件）與 `cooling`（液冷、冷板、CDU、快接頭、浸沒式）兩個主題
   ——使用者 Q2 選的鏈；7.1 的 decompose 再修。記進 `cohort-changes.md`。
5. **心跳段 3** 一行：「外部雷達：新 N｜重複 a｜拒收 b（網址不在搜尋結果 c、超過上限 d）｜提到在盯的條件 K｜沒有重要變化／沒跑（理由）」（`SNAPSHOT_KEYS` 加鍵）。
6. **八週試驗與停止條件**（寫進 ROADMAP Phase 7 列）：上線日起 56 天；7.5 檢查點數「雷達 lead 中，triaged_go 且追到一手文件或入圖、而且沒有別的管道更早登記同一個網址或同一事件」的筆數——
   **0 就退役**（`radar.enabled=false`，程式留或刪在檢查點決定），非 0 就列出那幾筆、由使用者決定續不續（registry）。
   **A10（2026-10-21 使用者 go）——11-30 出「第 56 天報告」**（`docs/reports/phase7/radar-day56.md`；10-05 起算第 56 天是 11-29）：
   ①逐筆列計入的雷達 lead id，以及別的管道「同一網址或同一事件」的更早 lead id——「更早登記」＝別的管道有那則 lead，**不論當時 triage 結果**；
   ②按儀器版本分段計數：v0（10-05～10-07：主題＋在盯條件；10-07 起多 aibio，`c4be9f93`）、v1（10-08～10-19：加市場層 4 題、上限 3，`f0854048`）、v1.1（10-20：市場層反向題，`8e6dad9b`）、v1.2（10-21：精進 A `444bb827`＋B `6650c0ec`，市場層 6 題、上限 6）、v2（10-22 起：讀過的層每日輪替，`6166e4a9`）；
   ③沒跑的天照印，不從分母拿掉也不補（10-09～10-12：LLM 七天額度用完，心跳「外部雷達：沒跑（01e_radar_apply skipped：llm_not_ok：01c_radar_propose 沒有成功）」）；
   ④Tower–Semtech 另列「雷達救回被誤判 no-go 的一手」：EDGAR `lead_6f4fdb17`（TSEM 6-K，10-13，內文就是同一份新聞稿，triage 以「原文內容為空」判 no_go）、雷達自己 10-14 的 `lead_e1f0f1b2` 也 no_go，10-17 的 `lead_79e8c3cc` 才 go 並入圖（`ra_845dd2f81adba3517e08a2a9ee6199cc`）；
   ⑤誠實註明：「更早登記不論 triage」這個講法是看過計數之後才寫清楚的，兩種數字（10-21 試算 2 或 3，以 11-30 重算為準）都照印；**原停止條件照原定義算**（全期為 0 就退役），新講法不拿來觸發或避開它；
   ⑥續不續由使用者在 12-22 檢查點決定（§11 第 4 項、§14 第 2 項）。
7. **sandbox impact review 五步**（OPERATIONS 新節）＋ARCHITECTURE §4.1 的表（分類／語意預篩／**雷達**）同 commit 更新；說清楚它不是 last30days（硬約束 8 的理由是「輸出沒有 provenance 契約」，雷達的契約是網址必須出自搜尋結果）。

**怎麼驗：** `pytest` 綠：argv 逐項（tools 恰為 WebSearch、禁用旗標不在）、能力檢查各種不符、網址不在搜尋結果被拒、去重、上限、prompt 不含持股（哨兵）、`executor=none` 與 `enabled=false` 都 skipped、
心跳行；`python crons/daily_task.py --dry-run` 列出新步驟且時限加總仍在 `execution_time_limit_minutes` 內；**第一次真實排程跑完後**看心跳那一行與收據（ROADMAP 驗收寫「已交付、第一輪 <日期>」）。
**R2-b `WORK_REQUEST`**：審查者看探針紀錄、argv、能力檢查、網址驗證、prompt 組法（不得碰 Sheet）、回滾開關。
L11-6 ④：最先壞的是 daily 的保險檢查（LLM 步驟前後的檔案指紋）與 triage 批次上限——雷達的 lead 進 ⑥，30 則上限下要確認它不擠掉 harvest 的 lead（批次的選取順序照實寫）。

## 6b. Step 7.0g 研究預算分層：深度在層、廣度在檔（Z3，R1；A4；2026-10-07 使用者定案 Q1 A、Q2 A、Q4 A）

**為什麼是現在：** 段 5 照現行規則（closure-gate 回 exit 1 不得收工）會繼續替大型股寫淺敘事；剩下 26 檔裡 20 檔非邊緣。研究 session 在本 Step 交付前**不跑段 5**，先做不經閉環的研究（AI 生醫拆層、層說明）。

1. **7.0g-1 資料檢查跟著全部個股頁（Q2 A；先於撤非邊緣敘事）**
   - 母體＝全部已 materialize 的個股頁（`ArtifactStore.read_all`），**不跟閉環母體走**；每個檢查印「比對 N 檔／無法比 M 檔」並逐檔列出無法比的——跳過不得安靜（INV-3）。
   - **營收量級（新）**：個股頁印出的近四季營收（值＋幣別標籤）對基期觀測的年營收（各自幣別），以同一個換匯來源換成美元，比值超出 [0.5, 2.0] 就列出（口徑差異不會差到兩倍，量級錯會）。
   - **股數（既有，補覆蓋）**：從閉環列改成全部個股頁；沒有財報股數可比的逐檔列，港股另標「快照可能只含 H 股」（名冊沒有記 A 股那一邊，A＋H 判不出來——照實印，不猜）。
   - **同日多筆生效（既有）**：照舊全庫。
   - **驗收**：三個原始案例回放命中 3／3——#20（6680.HK：快照 241,144,516 對財報 1,360,000,000）、#23（UMC 修法前印的「2,507 億 USD」對 20-F 基期）、#27（SOI.PA `segment_revenue_share@2026-03-31` 兩筆生效）；測試以原始數字寫死，拿掉檢查即紅；closure-gate 每輪印三行與覆蓋數。
2. **7.0g-2 閉環母體收窄（Q1 A；#22 選項②）**
   - 母體＝已持有 ∪ 有 thesis（lifecycle；使用者明示）∪（邊緣或量不到 ∩ 供給側有座位）∪ 現行候選（敘事狀態缺 X／等回落／可開）。
     邊緣讀候選板 artifact（materialize 時對全部個股頁算一次，補上還沒有敘事那幾檔的 `edge`；closure-gate 不打外部）；座位讀結構表 artifact 的 `supplies_to` 列（`depends_on`／`constrained_by` 是買方那一側，不算供給側座位；結構表收下游關係、走不到需求錨的列照收，`develops`／`invests_in` 不收）。
   - 母體外**逐檔列名**，分兩類：**非倍率**（非邊緣、沒持有、沒有 thesis：附市值、覆蓋、判定日；每次 materialize 重算，翻回邊緣就回母體）；
     **邊緣沒座位**（列「坐哪一層」短檢查；有 v2 敘事且 90 天內的算查過，超過 90 天或從沒查過就回到可推進——每個等待都有到期，INV-2）。
   - `NEXT_PICK_RULE` 刪「有同期 EPS 共識」「forward EPS 為正」兩條（Phase 0 殭屍：理由引用已刪的 bridge.py）；其餘順序不動。
   - **驗收**：#22 預先寫的量「未到終局裡沒有出口的檔數」17 → 0（閉環佇列）；母體外兩類逐檔列名、各附理由；之後 7.5 量「非倍率檔在本 Step 之後新寫的敘事版本數＝0」（敘事 ledger）。**2026-10-21 照實預記：照字面不是 0。** 7.0g 交付（`a2d30165`，2026-10-07 04:09 台北）後、10-20 撤回前，候選理由以「非邊緣」起頭、非撤回、不是持有也沒有 thesis 的版本 **19 筆／11 檔**（009150.KS、012330.KS、3105.TWO×5、5016.T、5802.T、6594.T、GLW、INTC、LITE×5、MTSI、UMC）——**首版 0**，19 筆全是 7.0g 前既有「不要（非邊緣）」敘事跟著讀圖換版的換騎／換引用（其中 14 筆是同義節點合併或讀圖換版的「內容一字不改」換騎，failure log #75；012330.KS 一版改寫兩句）；10-20 起這類敘事撤回（撤回紀錄 40 筆／40 檔）。7.5 兩個數都印：首版 0、換版 19。（10-21 主 session 另數為 20 版／12 檔，差 1 版 1 檔，定義差異待對齊後再改此句。）
3. **7.0g-3 `research` 面板降選配（Q4 A）**：`CORE_PANELS` 拿掉 `research`、`OPTIONAL_PANELS` 加入；內容照印、只是不再決定 readiness。契約升版、全量 materialize、重啟長駐 serve。
   **驗收**：只因 `research` 卡住的檔逐檔列出改前改後的 readiness（閉環佇列）；其他面板的狀態逐位相同。
4. **7.0g-4 段 5 分流寫進 skill**：非倍率不寫敘事（它的文件進層說明當在位者或客戶證據）；邊緣沒座位做一次短檢查（結論＝補座位走 RA，或 v2 敘事寫「不坐任何層」）；
   廣度短敘事的範圍（一份年報＋packet；先宣告單位；三項必查：致股東報告書 #32、表頭個體或合併 #35、同義節點 #36）；層深讀的入口（走圖第 1／2 型、下一層 0 條、有敘事的缺 X 指向這一層——只印有無不印次數、讀圖過期、層主張的 watch 醒、使用者點名）。
   `python scripts/sync_agent_skills.py`。

**不做：** 不動 tracked 名單（它也餵 EDGAR 監看與 pq1 relevance）；不寫非邊緣檔的「不要」敘事來充當研究判斷（L12）；「已定價」不當分流條件（不設門檻，AGENTS）；火力比例（T2 約 20%、T3 約 45–50%、T4 約 25%）只是初值、不寫進程式。
**L11-6 ④：** 最先壞的是「供給側座位」的判定——只有 `develops` 邊的公司（開發中、還沒供貨；#22 第二型 5 檔）與只有 `invests_in` 邊的公司會被當成沒座位而進短檢查；去看 5411.T（只有投資電工鋼合資廠的邊）與 6481.T、XFAB.PA、XPEV（2026-10-07 實查：0 條邊），短檢查的結論要能把它們分成「補供貨邊」「開發中」「不坐任何層」三種，而不是一律寫成「不坐任何層」。

## 8. Step 7.2 回放（R1、R3 執行模型；R2、R4 強模型；可與 7.1 交錯）

報告：`docs/reports/phase7/replay-<名稱>.md`，**每一列標 discovery lookahead 與選樣偏差**，產生用的程式碼貼在附錄（scratchpad 會消失）。

- **R1 已定價回放（機械，H9）**：母體＝history lane 22 ∪ 光通訊主題等權組 15（去重）中有自家歷史的檔；時點＝入圖日，與入圖日前 30／90／180 天；
  以**三題同一個純函式**（`alpha/three_questions.py` 與 `engine_c/three_question_inputs.py` 的取數規則；as-of 規則 `shared/as_of.py`）在 scratchpad 算當時的自家三年百分位，
  對照之後到今天的報酬與對主題等權組的超額；呈現分組表（高／中／低百分位 × 之後報酬），**不算 p 值、不下「有效／無效」以外的結論**，n 照印。
  ⚠ 三題的 as-of 視角今天沒接（Phase 3 #15）：純函式加 as-of 篩過的輸入算得出來就照做；算不出來就寫 failure log、照實寫「未量」，**不在本 Step 改產品程式**。
- **R3 漏網稽核（機械，H1、F6；每季一次，第一次在 7.2、第二次在 7.5）**：母體＝7.0a 預先列的名單；該季對主題等權組漲最多的前四分之一，逐檔查 lead registry 的 `first_seen`、
  來源、最後狀態與「為什麼沒進研究」（registry 查得到的照抄；查不到寫「系統沒有接觸」）。含 HBM／記憶體那幾檔（「刻意不做」的代價）。
- **R2 parked 回查（研究，H2、F4、F5）**：從 353 則 `original_obtained` 的 parked 依管道分層抽 30–40 則（抽樣規則先寫進 replay 報告再看結果；**偏差 #2：規則與 36 則樣本已在 7.0a 固定於 registration §7.3／附錄 C，replay 報告照抄**），每則：之後有沒有一手證實（文件與日期）、
  證實前價格走了多少、當初 park 的理由現在看站不站得住。
- **R4 history lane 輸家驗屍（研究）**：AEVA、MP、LYC.AX、6594.T、6680.HK——入圖時的圖投影說了什麼（`project_assertions_as_of`）、之後的一手文件說了什麼：結構讀錯了，還是只是價格路徑。

**怎麼驗：** R1 每檔有各時點的百分位與之後報酬，或寫明缺哪一項（追蹤表）；R3 每檔有 `first_seen` 或「沒有接觸」（registry）；R2 每則有證實日或「未證實」（registry）；
R4 每檔一段結論（追蹤表）。每份報告的偏差標註齊全。
L11-6 ④：最先壞的是 R1 的 as-of——拿今天的財報數字算過去的百分位就是 lookahead；核對每個時點用的財報 `filed` 日都早於那個時點。

