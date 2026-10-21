# Phase 7 監看來源與母體變動（cohort changes）

> **append-only。** 每次監看來源（X 帳號、harvest 來源、雷達）、題材清單、主題等權組或 R3 母體有變動，就在檔尾加一筆：
> **日期｜改了什麼｜為什麼｜影響哪些量測（從哪一天起量、回不回溯）**。T1 manifest 與 T0 的每一類差異都要歸因到這裡的某一筆（plan §11 第 5 項）。
> 新 X 帳號：照 `config/signal_sources.json` 的規則以 probation 加入、`crons/harvest_config.json` 的 handles 同步；**加入日起量、不回溯**（plan §0.1 Q4）。

---

## 2026-10-04　T0

- **T0 manifest**：`library/private/measurement/phase7/T0-2026-10-04.json`（private、不進 Git），sha256 `eb13ae65709a842209e19ae16bfb9d878a22776815dd2d76da4aa19b0afa924a`，
  生成於 2026-10-04T07:09:14Z；對照心跳 `heartbeat_2026-10-04.md`（一致，registration §8）；產生程式碼＝registration 附錄 A。
- **監看來源**：X 帳號 1 個——`aleabitoreddit`（active，tier probation，自 2026-09-17）；harvest 來源 36 個（心跳段 1）；
  `crons/harvest_config.json` sha256 `1a2a4aa6dac12641a8e257082c97067682e58466e7ab36d1d5e42a877044dda2`、
  `config/signal_sources.json` sha256 `8f3c92638d939bdfd0e6a6473c24a5c713457e554c7a3974cc89e57929f81613`。
- **題材**：`config/themes.txt` 3 個主題（cpo、sivers、robotics），sha256 `898c9813fd70ac15ae986c94dfdc9f2e80f37bfd6a5af77572ca381f36082556`。
- **主題等權組**：1 組——`tc_35b0d5cd521656ea`（AI 光互連／CPO，2026-09-30，pq2 [656]，15 檔）。
- **R3 母體**：光通訊組 15 檔＋AI 基礎設施觀察名單 43 檔（registration §5.2）。
- **已知會在 T0 之後發生的變動**（發生時各記一筆，這裡只預告）：Step 7.0f 外部雷達上線（新來源 `web_radar:<theme>`）與 `config/themes.txt` 加 `power`、`cooling`；
  Step 7.1 電力、散熱主題等權組的前瞻定義（pq2）與它們的成分 append 進 R3 母體（從第二個窗口起計，registration §5.3）；使用者之後加的 X 帳號。

## 2026-10-04　Step 7.0f 外部雷達上線（首輪 2026-10-05）＋題材加 power、cooling

- **新監看來源**：外部雷達 `web_radar:<主題>`（daily ①b–①e：`claude -p` 只開 WebSearch 提議、`engine_b/radar.py` 驗證後寫 secondary lead；每日上限 5 則；網址必須出自同一次執行的搜尋結果）。**2026-10-05 首輪起量、不回溯**；八週試驗到 2026-11-29（56 天），停止條件見 ROADMAP Phase 7（7.5 數「雷達 lead 中 triaged_go 且追到一手或入圖、而且沒有別的管道更早登記同一個網址或同一事件」的筆數，0 就退役）。
- **題材**：`config/themes.txt` 3 → 5 個主題（加 `power`、`cooling`；只有描述與關鍵字，**核心公司 7.1 的 decompose 再定**，所以 tracked 不變），sha256 `aa650297882f685ab4abd41f5c45a6f19ca9c4b16640736c18d99dc6c87e02ab`（T0 是 `898c9813…2556`）。
- **影響哪些量測**：lead 的主題標記（`leads._themes_for`）從這個 commit 起對新登記的 lead 生效、舊 lead 不回溯；H6 的判讀線不吃雷達的 lead（registration H6：雷達是「一般資訊」的對照組，7.5 只並列印出）；triage 批次的選取順序（雷達排在所有非雷達 lead 之後，plan 偏差 #16）；T1 manifest 的 `sources_config` 對 `themes.txt` 的差異歸因到這一筆。

## 2026-10-05　R3 母體追加 IC 載板類 6 檔（pq2 [711]）

- **改了什麼**：R3 母體（registration §5）追加 ATS.VI、009150.KS、4062.T、3037.TW、3189.TW、8046.TW——登記文件檔尾「更正與追加」同日一筆。
- **為什麼**：載板層兩檔 2026 年各漲約 20 倍，而 T0 的 43 檔觀察名單沒有 IC 載板類（cases X3 2026-10-05）。
- **影響哪些量測**：R3 從第二個窗口（2026-10-01 →）起分母 58 → 64；第一個窗口不追溯。不進任何研究佇列、不入圖、不建主題等權組。

## 2026-10-06　X 帳號 1 → 5（使用者點名加入四個）

- **改了什麼**：`config/signal_sources.json` 與 `crons/harvest_config.json` 的 `x_accounts.handles` 加 `jukan05`、`vikramskr`、`dnystedt`、`carrioresearch`，四個都是 `status=active`、`tier=probation`（自 2026-10-06，D5）。
  sha256：`crons/harvest_config.json` `7c23e745f0ab1ae4fc34a216aefd800f7f5e23e6c86929691313db8349808a0b`、`config/signal_sources.json` `b487baa64dec035245c94daf756733889cd519ee33746cafee4f4a354668417c`。
- **為什麼**：使用者 2026-10-06 點名（三個附理由：AI 供應鏈／光模組細節、前 Qualcomm 半導體研究、技術導向半導體分析；一個未附）。清單推薦與背景不是量測，信任仍為零。
- **影響哪些量測**：四個帳號**自下一輪 daily harvest 起量、不回溯**（冷啟動只抓一頁 `max_results=25`，不做 30 天 backfill）；帳號計分表（Phase 3）的分母自 2026-10-06 起多四列；H6 的判讀線對新帳號的 lead 一樣適用（來源標籤 `x:<handle>`）。
  T1 manifest 的 `sources_config` 對這兩個檔的差異歸因到這一筆。月花費上限 `monthly_spend_cap_usd=10` 不變——9 月一個帳號實花 $0.14；五個帳號若撞上限，心跳段 1 會印 `budget_exhausted`（不是故障，不推進 since_id）。

## 2026-10-06　題材 5 → 6（加 `aibio`）＋robotics 一個誤報短字換長寫法

- **改了什麼**：`config/themes.txt` 加 `aibio`（AI 生醫——AI 藥物發現把實驗量往下游灌；只有描述與關鍵字、**不列核心公司**，同 power／cooling 的作法）；
  robotics 的 `Digit` 換成 `Agility Digit`、`Digit humanoid`、`Digit robot`。sha256 `529daf06c3cc9eaeadaf98c044e78c6e4e02c1620bb0563c0f522ae7db545539`。
- **為什麼**：`aibio`＝使用者 2026-10-06 選題（pq2 [723]；registration B1）。`Digit`：英文比對不分大小寫、要詞邊界，"triple digit"、"single digit" 都會命中——
  現有 lead 裡 robotics 標記靠 `Digit` 的 5 則中 3 則是這種誤報、0 則只靠它命中真案例（L17 當下修）。
- **影響哪些量測**：主題標記只對新登記的 lead 生效、舊 lead 不回溯（同 2026-10-04 那筆）；雷達每日搜尋的主題多一個（每日 5 則上限不變）；
  `aibio` 沒有核心公司，所以 tracked、materialize 頁數、EDGAR 監看都不變。T1 manifest 對 `themes.txt` 的差異歸因到這一筆與 2026-10-04 那筆。

## 2026-10-07　case G1（IC 載板上游：低膨脹玻纖布）開題

- **改了什麼**：registration 檔尾 append case G1；監看來源、題材、X 帳號、R3 母體都**不變**（R3 不追加載板材料，列 plan §14 待決）。名冊 +2（日東紡 3110.T、景碩 3189.TW）隨入圖包 pq2 [733] staged，**核准後才進名冊**——進了以後 tracked、materialize 頁數與 Engine C 取價會多這兩檔。
- **為什麼**：續工 ① 走圖「下一層 0 條」——IC 載板層判量但上游沒讀；主供應商是系統口徑的邊緣公司。
- **影響哪些量測**：H1 的 T0 之前接觸列可能 +1（入圖並讀圖後）；H5、H6、H9 另印各 +1；T1 manifest 的名冊差異歸因到 [733]。

## 2026-10-08　鑄號：載板鏈主題等權組 [736]、散熱組 v2 [738]（都等使用者 go，尚未寫入）

- **改了什麼**：還沒改——兩個 pq2 編號凍結了 spec。[736]「AI 封裝載板與上游材料」6 檔等權（ATS.VI、4062.T、3037.TW、3189.TW、8046.TW、3110.T；digest `fad569063611856c`），Ibiden、欣興、南電三筆名冊條目隨號 staged、go 才 commit；[738]「AI 資料中心散熱」v2 取代 `tc_2efac5d9b16b46cf`，加雙鴻（3324.TWO）成 5 檔（digest `2cf18022ba5424d1`），Vertiv 的排除理由改寫成實質理由、新增排除 Modine／AAON／Munters。
- **為什麼**：[736]＝G1 寫日東紡第一份敘事前要先有本鏈的對照組（failure log #26 的教訓）；[738]＝v1 排除雙鴻的理由是「不在名冊」，雙鴻 10-07 登記（[732]）後照同一準則合格——「不在名冊」是會過期的理由，v2 改寫成實質理由。
- **影響哪些量測**：go 之後——H5、H9 與 2×2 的「對主題等權組的超額」多一組載板（日東紡、AT&S、景碩的已定價脈絡有中位數可比）；散熱組中位數多一檔；新登記的五檔（景碩、日東紡、Ibiden、欣興、南電）與雙鴻的價格歷史在第一次抓取補上，補上前組中位數照實印缺。T1 manifest 的名冊差異歸因到 [736]（三筆）。

## 2026-10-08　名冊 +1 隨入圖包 staged：華明裝備（[739]，等使用者 go）

- **改了什麼**：還沒改——`co:huaming`（002270.SZ、CNY、SZSE）隨分接開關入圖包 pq2 [739] staged，**核准後才進名冊**；進了以後 tracked、materialize 頁數與 Engine C 取價多這一檔。監看來源、題材、X 帳號、R3 母體都不變。
- **為什麼**：走圖第 7 型「沒人供應」——分接開關層有第三方（能源部 2022）說可能是瓶頸、供給側 0 家；華明是系統口徑的邊緣公司、主業就是分接開關。
- **影響哪些量測**：H1 的 T0 之後新接觸 +1（第一次接觸＝2026-10-08 走圖，lead registry 之前 0 則）；電力組主題等權組之後可能要重看（華明主業是變壓器零件、不是變壓器整機——入不入組是判斷，另鑄號）。T1 manifest 的名冊差異歸因到 [739]。

## 2026-10-08　名冊 +1 隨入圖包 staged：Reinhausen（[740]，私人公司，等使用者 go）

- **改了什麼**：還沒改——`co:reinhausen`（Reinhausen GmbH，研究 ticker 明確 null）隨國家實驗室報告的入圖包 pq2 [740] staged，**核准後才進名冊**。私人公司沒有個股頁、不進 tracked、不取價。
- **為什麼**：國家實驗室 2026-05 報告點名它是美國唯一在產的有載分接開關廠；圖上要能寫它的供貨邊。
- **影響哪些量測**：無個股頁、無價格；T1 manifest 的名冊差異歸因到 [740]。

## 2026-10-08　落地：載板鏈主題等權組（[736]）、散熱組 v2（[738]）；名冊 +15（[736][737][739][740]）

- **改了什麼**：使用者 10-08 早上 go。主題等權組 ledger 新增 `tc_5061f2233f77a865`（AI 封裝載板與上游材料，6 檔）、`tc_113e1c8eec9e00b6`（AI 資料中心散熱 v2，5 檔，取代 `tc_2efac5d9b16b46cf`）；名冊 143 → 158（commit 9800d618；13 家有研究 ticker，進 tracked 與每日 materialize）。
- **為什麼**：見 2026-10-08 鑄號那一筆與 [739][740] 的名冊條目。
- **影響哪些量測**：H5、H9 與 2×2 的「對主題等權組的超額」多一組載板；散熱組多雙鴻。⚠ 兩組的 decided_on 記成 2026-10-07（ledger 用 UTC 日期；使用者是台北 10-08 早上決定的）——failure log #49，點時查詢時以 10-08 為準。新登記 13 檔的價格歷史在第一次抓取補上；[737] 的 10 家邊緣公司進閉環母體的「邊緣沒座位」那一格（坐哪一層短檢查）。

## 2026-10-21　補記：外部雷達 10-19～10-21 改了四次（八週試驗中途換儀器）

> 10-21 唯讀盤點發現 10-08 之後本檔沒有再記任何變動，而雷達在試驗期間改了四次——這裡一次補齊，各自標生效的 daily 日期。
> X 帳號、harvest 來源、`config/themes.txt`、主題等權組、R3 母體在 10-08 之後 git 上沒有變動（`git log --since=2026-10-08 -- crons/harvest_config.json config/signal_sources.json config/themes.txt` 為空）。

- **改了什麼**：
  1. `8e6dad9b`（10-19 23:07 台北，10-20 daily 起）：市場層加第 5 題「需求反轉與延誤」（退出、取消、延後、電網延誤、融資受阻）。
  2. `444bb827`（10-20 14:23，10-21 daily 起；雷達精進 A）：截短的 watch id 恰好對到一條才收（之前整條丟）、市場層上限＝題數。
  3. `6650c0ec`（10-21 00:04，10-21 daily 起；精進 B）：市場層第 6 題「供應鏈分工與採購轉移（結構性）」、上限 6；前 7 天已收標題交給 LLM。
  4. `6166e4a9`（10-21，**10-22 daily 起**；精進 C3）：主題層加「讀過的層」每日輪替（每天 max(8, ⌈層數÷7⌉) 層，58 層 → 9 層／天）；
     在盯條件只帶今天輪到的層掛的那些（約 20 條，原本全量約 270 條）；搜尋上限 24 → 32、timeout 12 → 16 分鐘；收據加 `rotation`、lead 加 `refs.radar_layer`。
- **為什麼**：使用者點名漏抓（Microsoft 退出 Nscale，failure log #88）、NVHBM base die 雷達沒收（X 帳號先抓到）、relates_to 26 條被丟（#92）、themes 7 題與讀過的 56 層脫節；計畫 `docs/plans/2026-10-21-001-feat-radar-impact-mapping-plan.md`。
- **影響哪些量測**：7.5 檢查點的雷達計數（「triaged_go 且追到一手或入圖、沒有別的管道更早登記」）要**按這四個日期切段**報——10-20 之後的市場層、10-22 之後的層輪替多出來的收穫不能算成同一台儀器的表現；
  「提到在盯的條件」計數 10-21 起含截短 id 解析（之前低估）、10-22 起只在今天輪到的層的條件裡比（分母變了）。不回溯。
  另：每日摘要（⑪c）10-22 起多一張「可能怎麼影響」清單（雷達精進 C2）——不改任何來源與母體，只改短版輸出，不影響量測。

## 2026-10-21　題材 7 → 6（移除 `cnbio`）＋`aibio` 改寫成「三問全中」的定義；補記 10-07 加 `cnbio`

- **改了什麼**：
  1. **補記**：`95509fda`（2026-10-07 14:28 台北）在 `config/themes.txt` 加 `cnbio`（中國創新藥授權鏈；使用者「B ok」，pq2 [726]），題材 6 → 7——**當時本檔沒記**。sha256 `15ea5a47d7ebfab85ff0a7f8d6993b1eaa02fcc8a36c60b55d6cbc1b316bd420`（前一筆 10-06 是 `529daf06…5539`）。雷達查詢 10-08 起才出現 cnbio 題（10-07 的 26 個查詢裡沒有）。
  2. 移除 `cnbio`（7 → 6）；`aibio` 的描述與關鍵字改寫成「三問全中才算 AI 生醫」：①付錢的是 AI 程式 ②買的是實體輸入、量跟著 AI 走 ③落得到一層或具名供應商。關鍵字 40 → 48：拿掉實驗猴／臨床前類 9 個（IND-enabling、preclinical CRO、non-human primate、cynomolgus、臨床前、临床前、食蟹猴、實驗猴、实验猴）與泛用字 6 個（AI-designed drug、oligo synthesis、protein expression、protein production、antibody discovery、high-throughput screening），加 23 個（HT-SPR、Carterra、Adaptyv、oligo pool、Perturb-seq、virtual cell、Ultima Genomics、Tahoe Therapeutics、data generation agreement、TuneLab、autonomous lab 等）；反證詞拿掉 pharma R&D budget cut、monkey supply easing，加 in-house wet lab。仍不列核心公司。sha256（`git show <commit>:config/themes.txt | sha256sum`）見本筆的 commit。
- **為什麼**：使用者 10-21「生醫 go」——在意的是 AI；這推翻 10-20「生醫兩題留著」（`docs/plans/2026-10-21-001-feat-radar-impact-mapping-plan.md` 開頭）。`cnbio` 的需求一手歸因是融資與授權、不是 AI（cases.md B1 結案段）；舊 `aibio` 的實驗猴字讓 aibio 也收到 cnbio 的新聞（lead_268ffc9e 同時標 aibio、cnbio）。近 14 天雷達在這兩題收 9 則（aibio 5、cnbio 4）：8 則 triaged_no_go、1 則 parked；套三問只有 1 則（Danaher／Abcam 自主實驗室）會收，它的 triage 也是 no-go。
- **影響哪些量測**：
  - 雷達主題層 7 → 6 題，**10-22 daily 起**，不回溯；每天約少 1–2 次搜尋（10-08～10-21 cnbio 類查詢每天 1–2 次）。7.5 檢查點與 56 天報告的雷達計數，在上一筆的四個切點之外**再加這一個切點**；`web_radar:cnbio` 的 4 則舊 lead 照實留在試驗計數裡。
  - lead 主題標記（`leads._themes_for`）只對新登記或內容被補長的 lead 生效；舊 lead 已存的 `themes` 不回溯（`backfill_themes` 只補沒有標記的）。新規則下 Adaptyv、Carterra、HT-SPR 會標到 aibio，實驗猴、臨床前不再標；triage 提示的命中詞隨之改變。
  - 不變：cnbio 的三個日期等待（ew_0650 到 2027-02-12、ew_0740 到 2026-11-15、ew_0741 到 2027-02-14；kind=date、`poll.eligible=false`，只靠到期日叫醒——移除主題後到期前不會再有雷達新聞讓人看到，使用者在意 AI，接受）；tracked、materialize 頁數、EDGAR 監看（兩題都沒有核心公司）；主題等權組（兩題都沒有）；H1／H5／H9 的 case 清單。T1 manifest 對 `themes.txt` 的差異歸因到這一筆（含 10-07 補記）。

## 2026-10-21　補記：外部雷達 10-07 加市場層（10-08 daily 起）——上一筆補記漏的那一次

- **改了什麼**：`f0854048`（10-07 13:22 台北，**10-08 daily 起**）：雷達 prompt 由「主題＋在盯條件」改成兩層——加**市場層**（`config/daily_routine.json` 的 `radar.market_topics` 4 題、各一次搜尋、上限 `max_market_items`＝3，與主題層分開計上限），主題層改成「每個主題至少一次廣搜」；收據與 lead refs 帶 `scope`（market／theme／watch）。
- **為什麼**：使用者 2026-10-07「我們還是必須知道 AI CAPEX 整個市場的大事，不能見樹不見林」。
- **影響哪些量測**：八週試驗的雷達計數多切一段——10-05～10-07 是沒有市場層的儀器（v0），10-08 起才有（v1）；上一筆補記寫「10-08 之後本檔沒有再記任何變動」，這一次在 10-07，同樣沒記。不回溯。
