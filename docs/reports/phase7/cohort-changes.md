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

## 2026-10-21　補記：10-07～10-20 漏記的六筆（題材、名冊、主題等權組、新鏈開題、敘事撤回）

> 10-21 計畫盤點（amendment A11）發現。⚠ 更正同日上一筆（雷達四次改動）的前言：它寫「主題等權組、R3 母體在 10-08 之後 git 上沒有變動」——**主題等權組 ledger 住 `library/private/alpha/theme_cohorts/`、不進 Git**，git log 看不到；10-08 之後實際寫了 4 筆（下面 ③④）。R3 母體確實沒變（registration 自 10-08 之後沒有 commit）。時間為 UTC，括號為台北。
> 查證：主題組全部版本 `python -c "import json,glob;[print(r['cohort_id'],r['created_at'],r.get('supersedes_id')) for f in glob.glob('library/private/alpha/theme_cohorts/*.jsonl') for l in open(f,encoding='utf-8') if l.strip() for r in [json.loads(l)]]"`；名冊家數 `git show <rev>:config/company_identity.json | python -c "import json,sys;print(len(json.load(sys.stdin)['companies']))"`。

（① 10-07 加 `cnbio`：已在同日「題材 7 → 6」那筆補記，不重複。）

### ② 2026-10-08～10-20　名冊 158 → 195（+37；有研究 ticker 116 → 148）

| commit（台北） | pq2 | 新增 |
|---|---|---|
| `083c6b89` 10-08 11:22 | [743] | MXL、OUST（+2） |
| `22fa801d` 10-08 16:13 | [751] | Freiberger（私人，+1） |
| `e37bd126` 10-08 21:20 | [753] | Amazon（+1） |
| `ed6e13ea` 10-17 00:15 | [760][761][763] | 雲南鍺業、大立光、ASMPT（+3） |
| `b031ec7f` 10-17 17:33 | [773][774] | 新易盛、Source Photonics、Ligent、KSH International、Precision Wires India（+5） |
| `db9820cb` 10-18 09:44 | [792][795][797][798][799] | Oncor、Core Scientific、Fermi、環宇-KY、Semtech、光環、台燿、金居、三井金屬、台光電、台玻、富喬、滬電（+13） |
| `6942dce9` 10-18 09:49 | [796] | VIAV、COHU、TTMI（+3） |
| `8faaf758` 10-19 07:41 | [808] | 古河電工（+1） |
| `e869d32f`、`4c69c053` 10-19 | [809][810] | 只加別名（+0） |
| `1a5314c7` 10-19 08:00 | [813] | 京東方（+1） |
| `ea7fc3e1` 10-19 08:18 | [815][816][817] | Nokia、德福、方邦、CFL（私人）（+4；[817] 只加 Oracle 別名） |
| `483865cd` 10-20 09:26 | [824][826] | Nscale、聯茂、菲利華（+3） |

- **為什麼**：入圖包隨包 staged（go 才進）與名冊批次；每筆 pq2 都已 go（待辦池核對 2026-10-21）。
- **影響哪些量測**：tracked、每日 materialize 頁數、Engine C 取價多 32 檔（其餘 5 家沒有研究 ticker）。H1 的第一次接觸：名冊多了才以 company_id 比對，但新登記公司的舊 lead，`entities` 不一定抽得到（例：2026-07-25 那則 X 原文的「Mitsui Kinzoku (5706)」「Nittobo」沒被抽成 company_id；`registry-rescan` 的 stale 計數是 0，表示是抽取規則不認得，不是沒重算）——7.5 照 §0.1 逐列做名字比對、記比對法。R3 的「是否在名冊」欄另印登記日。T1 manifest 的名冊差異歸因到上表各 pq2。

### ③ 2026-10-18　光互連組 v2：`tc_cee164691d22da1e`（[802]，20 檔）取代 `tc_35b0d5cd521656ea`

- **改了什麼**：加光環 3234.TWO、環宇-KY 4991.TWO、新易盛 300502.SZ、波若威 3163.TWO、Ligent 9856.HK；新增兩條排除（Semtech／Marvell、GF）。鑄號 04:19Z、落地 05:14Z（台北 13:14）。
- **為什麼**：環宇、光環第一份敘事的反方審查指出「不在任何主題等權組」是我們登記晚了（L16）；照原準則補上組定義之後才登記的五家。
- **影響哪些量測**：**registration §0.1 寫死光通訊的超額基準是 `tc_35b0d5cd521656ea`**——照 §0 第 4 條，O 系列 case 的 2×2 與 R3 的排名（§5.3 第 3 點）照用 v1（15 檔），v2 另欄並列、標版本（Phase 5 closeout #6 換版斷點）。⚠ 追蹤表（`current_cohorts()`）10-18 起算的是 v2，所以追蹤表上的光通訊對組超額與 registration 的基準不同版。R3 母體不因 v2 自動追加（新易盛已是 §5.2 #2；其餘 4 檔併 plan §14 第 20 題）。T1 manifest 的主題組差異歸因到本筆。

### ④ 2026-10-18～10-20　高速 PCB 組 v1 → v2 → v3（[801][807][832]）

- **改了什麼**：主題等權組 ledger 新增「AI 高速 PCB 與上游材料」三版——v1 `tc_c928d2d9fdc6d76a`（[801]，8 檔：2383.TW、6274.TWO、8358.TWO、5706.T、1815.TWO、3110.T、002463.SZ、TTMI；鑄號 2026-10-18T02:26Z、落地 05:14Z＝台北 13:14）；v2 `tc_51042f19a27dee98`（[807]，+1802.TW 台玻，9 檔；2026-10-18T23:40Z 落地＝**台北 10-19 07:40**）；v3 `tc_af5ca457df73ab8b`（[832]，+6213.TW 聯茂，10 檔；鑄號 2026-10-20T06:30Z、落地 11:57Z＝台北 19:57）。
- **為什麼**：v1＝[799] 入圖，新鏈的組要在第一份敘事之前（plan 7.1 ④、failure log #26）；v2＝台玻 2026 Q2 玻璃纖維部門營收已超過平板玻璃、v1 的排除理由不成立，使用者 10-19 同意重議；v3＝聯茂 [826] 入圖、名冊登記，正是 v1／v2 排除理由寫的時點。
- **影響哪些量測**：H5、H9 與 2×2 多一組（registration G2，事後登記）。⚠ v2 的 `decided_on` 記成 2026-10-18（ledger 用 UTC 日期），使用者是台北 10-19 早上決定的——failure log #49 同形，點時查詢以 10-19 為準。⚠ 本鏈第一份敘事（台玻 `ib_5a22d69af8f2d5d7`，2026-10-18T04:26:55Z）比 v1 落地早 47 分鐘（同一個台北日；台玻當時在 v1 的排除名單，`alpha brief --add` 只擋待核准組提案的成員，所以沒擋）——驗收⑤對本鏈照實記「組晚 47 分鐘」。⚠ 日東紡同時在載板組 `tc_5061f2233f77a865` 與本組：追蹤表（`cohort_for_row`）對它回 `ambiguous_membership`、兩組都不比——G1 的 2×2 欄要在檢查點指定載板組手算；菲利華、德福、方邦不是任何組的組員（`not_in_any_cohort`）。T1 manifest 的主題組差異歸因到本筆。

### ⑤ 2026-10-20　新鏈開題：Bloom SOFC 現場發電（[831]）

- **改了什麼**：使用者 go [831] → system-decompose：2026-10-20T12:37Z 登記 21 則 pq1 題目（source `decompose:bloom_energy_server_sofc_ai`，triaged_go、tier 4），12:38Z 結案。監看來源、題材、X 帳號、R3 母體、主題等權組都不變；名冊不變（本鏈只有高力在名冊）。registration 2026-10-21 append case E1（預先登記，先於本鏈任何讀圖與敘事）。
- **為什麼**：高力一手核對走回 Bloom（lead `lead_9d629ed0aa9cd6f2c1115c09d63e3ca3`）：會計師附註定案 Bloom 占 2025 營收 31.27%，但圖上沒有燃料電池／現場發電層。
- **影響哪些量測**：lead registry +21（T1 manifest 的 lead 差異歸因到本筆）；H1、H10 的 case 多 E1。⚠ power 主題的替代／反證關鍵字有「behind-the-meter generation」——之後的現場發電 lead 會被標成 power 的反證（只影響主題標記，不影響判讀線）。SOFC 層有讀圖之後，雷達「讀過的層」輪替的層數跟著變（10-22 起的機制；同 10-21 那筆的分段）。SOFC 主題等權組未定義——第一份 SOFC 敘事之前要鑄號並落地（registration E1）。

### ⑥ 2026-10-20　撤回 41 份非邊緣「不要」敘事

- **改了什麼**：敘事 ledger append 41 筆撤回紀錄（created_at 都是 2026-10-20T14:56Z＝台北 22:56；note 寫「使用者 2026-10-20 決定撤回（「第2題 撤回」）…撤回不是改判：候選板照舊把它列在非倍率」）。41 檔：009150.KS、012330.KS、2301.TW、2308.TW、300308.SZ、3017.TW、3105.TWO、3653.TW、5016.T、5802.T、6594.T、688836.SS、AAPL、AMAT、AMD、ANET、AVGO、CRWV、FN、GFS、GLW、GOOGL、GXO、HEXA-B.ST、INTC、IREN、JBL、LITE、LRCX、META、MRVL、MSFT、MTSI、NBIS、NVDA、ORCL、TSEM、TSLA、TSM、TTMI、UMC。ledger 不進 Git，沒有對應的 commit。
- **為什麼**：research-drain 規定不替非倍率（非邊緣）公司寫「不要」敘事；這批隨讀圖換版一直亮「該重寫」、有過時句（failure log #93 的調查）。
- **影響哪些量測**：**paper lane 的母體不變**——`paper_lane_plan` 取每檔最早一筆**未撤回**的 v2，原本那幾筆沒被改，所以 41 檔仍是 paper 列（錨點狀態都是「不要」），現行狀態變成 retracted；2026-10-21 實算 114 列＝缺 26、不要 44、retracted 41、已定價等回落 3。三量、等權、追高計數仍含這 41 列（36%），它們的錨是 filter 的結果（非邊緣）、不是研究判斷——7.5 照實並列兩欄：全部 114 列、去掉現行狀態 retracted 的列（只印不比、不改判讀線）。主題等權組成員（光互連 v2 的 LITE、FN、300308.SZ；散熱 v2 的 3017.TW、3653.TW；PCB 組的 TTMI）與 R3 母體（2308.TW、009150.KS 等）都不受撤回影響——組是價格籃子，不看敘事。plan 驗收⑤（A8）的 Q3 名單只收現行敘事。case 段引用的敘事若之後被撤回，照 registration §0 第 4 條仍評開題那一版。
