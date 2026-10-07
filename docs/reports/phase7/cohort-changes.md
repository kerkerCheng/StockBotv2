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
