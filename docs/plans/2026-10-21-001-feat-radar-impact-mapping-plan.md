# PLAN_PROPOSAL：雷達精進 C——「拉進來的東西會怎麼影響敘事」＋主題層加輪替（Z2）

> 日期 2026-10-21｜狀態：**AWAITING_HUMAN**（核准哪幾個 Step 就只做那幾個）｜ROADMAP「雷達精進」列 C
> 使用者指示（2026-10-20）：「我預期繼續 refine 雷達這一塊，拉進來的東西我也想要問他會怎麼影響到我們的敘事」；
> 同日回三問：①主題層與輪替**並存**②每日摘要的 LLM **可以讀敘事各格摘錄**③生醫兩題（aibio／cnbio）**留著**。
> 調查底稿：research-drain 10-20 唯讀調查 `radar_refine`（原型 `impact_proto.py`／`impact_proto2.py`，回放結果見下）。

## INTAKE

- Zoom：**Z2**——新模組（影響對照）、改每日摘要的 LLM 契約與 schema、改短版與心跳輸出語意、加 research-drain 的 consumer。
- Review：R1（Step 各自）；R2 六條 trigger 都沒命中（不寫任何 authority、不涉 point-in-time、不涉資本）。
- Case：使用者指示；另有三個真實案例——Microsoft 退出 Nscale（failure log #88，雷達漏抓）、NVHBM（X 抓到但停放理由寫「沒有讀圖可接」，
  其實 HBM 讀圖缺的兩格正是它碰到的）、雷達 relates_to 26 條丟失（#92，已修）。

## Affected responsibilities／current boundary

| 責任 | 現在誰 | 問題 |
|---|---|---|
| 新進的一則（雷達或任何 lead）碰到哪些敘事／讀圖／在盯條件 | **沒有 owner** | research-drain 靠人自己想；NVHBM 那則就漏了 HBM 讀圖 |
| 每日摘要（⑪c 一次零工具 LLM 呼叫） | `engine_b/digest.py`＋`crons/digest_prompt.md` | 只摘要外部 lead，不知道我們的敘事 |
| 主題層搜什麼 | `config/themes.txt`（7 題） | 和讀過的 56 層脫節：HBM、載板、CCL、玻纖布、銅箔、測試都沒有主題層搜尋；在盯條件 272 條全塞給 LLM（約 75 KB）搜不完 |

## Proposed boundary（三個 Step，可分開核准）

### Step C1｜確定性影響對照（零 LLM）——`engine_b/impact.py`（新）

- 輸入：一則 lead（雷達或 harvest）。輸出：它碰到的①敘事（own＝company_id 命中；rides＝騎的讀圖在結構角度上有這個實體或節點名；
  slot＝哪一格原文具名了它）②讀圖（只認結構角度）③在盯 watch（active／fired 語意條件、實體有交集；歸屬一律呼叫
  `engine_b/narrative_watches.attributed_watches`，不自己解析）。
- 實體分兩欄、不混用（L12）：「結構化給的」（lead.entities.company_ids＋雷達 radar_company_ids）與「名冊名字掃到的」
  （`query.bottleneck.quote_names_company`，唯一 owner）。
- **樞紐實體只計數不展開**（一個實體單獨碰到 ≥10% 現行敘事或 ≥15 條在盯 watch：今天是 Coherent、NVIDIA、Broadcom、Lumentum、
  TSMC、台光電）——不做會恆亮（L14-4）：v1 回放 NVHBM 一則碰到 42 份敘事。
- 節點名只有英文，中文新聞比不到要**計數現形**（不靜默）。
- 唯讀 CLI：`python -m engine_b.impact --lead <id>`；不寫進 lead refs（對照會隨敘事變動，可重建，L10）。
- 回放（原型 v2，近 7 天雷達收下 43 則）：碰到 ≥1 份敘事 27 則、≥1 條 watch 24 則、≥1 份讀圖 23 則、什麼都沒碰到 14 則。

### Step C2｜每日摘要加一句「可能怎麼影響」（併進 ⑪c，不加 LLM 呼叫次數）

- 程式把 C1 的候選對（lead_id, target）交給 LLM，target 是 watch_id、brief_id#格、reading_id；**附該格摘錄（每格約 200 字）**
  ——使用者 10-20 同意摘要 LLM 讀敘事摘錄；只限零工具的那一步，`digest` 的「不讀私人路徑」聲明與哨兵測試同步改寫成
  「只讀程式交給它的摘錄、不讀持股與 Sheet」。
- LLM 回 {lead_id, target, verdict∈may_touch／unrelated／unclear, quote, sentence≤80 字}；apply 端驗證：那一對必須在候選集內（L15）、
  quote 必須是 lead 原文的逐字子字串（L18）、每日上限約 15 對、截掉的照數印（INV-3）。**只標旗、不判定**：不改 watch 狀態、
  不寫 semantic_flag、不減「未檢」。LLM 失敗時 C1 的確定性對照照印（L13）。
- 輸出位置（不違反「短版五段」「推播只送短版」）：Discord ② 每則雷達新聞下加一行「↳ 碰到：〈敘事〉的〈哪一格〉、讀圖〈節點〉、
  在盯 反證 a／加碼 b」（最多 3 個、其餘「另 N」、樞紐只印「另經 NVIDIA／TSMC 碰到 N 份」）＋ LLM 那一句標「提議」；
  Discord ① 一行總數；完整表進心跳落檔。APP 這次不做（還沒有畫面的段落留在 Daily）。

### Step C3｜主題層加「讀過的層」每日輪替（與 themes.txt 並存）

- prepare 依日期序號固定輪替每天 K＝8 個有現行讀圖的節點（約 7 天輪完 56 層），每個帶：層名、讀圖 supply_side 的公司名、
  掛在該節點的讀圖反證、騎它的敘事的條件（短 id 傳給 LLM，程式再對回原 id）。themes.txt 7 題照舊（使用者：並存）。
- 在盯條件不再全量塞給 LLM（約 75 KB → 約 13 KB）；搜尋上限 24 → 32（多 8 層，每層一次）；雷達 timeout 照 daily 總時限重算。
- 生醫兩題照留（使用者 10-20）。

### Step C4｜consumer：research-drain park 前必須處置對照

- `skills/research-drain/SKILL.md`：處理或 park 一條 lead 前讀 `engine_b.impact`；park 理由要逐條處置對照列出的在盯條件
  （不相關／等一手／已處理）。常駐計數器「park 理由未處置對照所列 watch 的筆數」（心跳段 3）——它會歸零、不恆亮。
- ⑤不加「碰到 N」計數（每天必然 >0，恆亮）。

## Success criteria（L14：只數圖、讀圖、敘事、等待 registry、追蹤表）

1. **漏抓回放追蹤表**（新，放 failure log 旁）：每列一個使用者點名事件（事件日、第一次進 registry 的管道與日期、雷達有沒有收、
   C1 對照列出的讀圖／watch／敘事格）。現有兩列：Nscale → MSFT、NBIS、IREN（敘事已撤回的照記）、AAON.demand；NVHBM → tech:hbm、
   ew_0762、ew_0763、FORM.demand。往後只收 market_topics 沒點名的事件才算泛化。
2. 等待 registry：雷達掛上的 watch 數 0 → >0（#92 修後回放 26/26）。
3. 讀圖：有現行讀圖的節點裡，過去 7 天被雷達輪到的節點數 → 56/56（C3）。
4. park 理由未處置對照所列 watch 的筆數 → 0（C4）。

## 修法層級（development-flow Step 3 四問）

- ①讓失敗「被看見」（顯形）：漏看的連結會自己出現在短版與 drain 前；不保證研究一定處置對（那是判斷）。
- ②靠程式（C1 確定性、C4 計數器），C2 的那一句是 LLM 提議、靠 apply 驗證擋候選外的對與非逐字 quote。
- ③加機制：拿掉的方式達不到——現在沒有任何 owner 回答「碰到誰」，不是重複閘門。同時拿掉一個：在盯條件全量塞給 LLM（C3）。
- ④若錯，最先壞的是：Discord ② 每則多一行，樞紐門檻設錯會讓真新聞被壓成數字（例：只碰到 TSMC 的台積電法說）——對策是那個數字照印、
  並宣告 absence_kind；C3 的輪替若選錯節點集會讓某層 7 天沒被搜——驗收 3 會現形。

## 要動的檔與規模

程式：`engine_b/impact.py`（新）、`engine_b/radar.py`、`engine_b/digest.py`、`engine_b/routine_config.py`、`crons/radar_prompt.md`、
`crons/digest_prompt.md`、`crons/digest_schema.json`、`crons/daily_brief.py`、`crons/heartbeat.py`、`config/daily_routine.json`；
文件：`skills/research-drain/SKILL.md`、ROADMAP、failure log 旁的漏抓回放追蹤表；測試：`tests/test_radar.py`、`tests/test_daily_digest.py`、
`tests/test_heartbeat.py`、`tests/test_impact.py`（新）。預估程式約 450–550 行、測試約 300 行。
LLM 呼叫數不變（C2 併進 ⑪c）；摘要 prompt 約多 8–12 KB。sandbox impact：不新增 unattended 命令字串（C1 的 CLI 是互動用）。

## 建議的執行順序

C1 → C4（先讓研究 session 自己用得到，最快止血 NVHBM 那類漏看）→ C2（短版那一行）→ C3（輪替，改雷達請求）。
每個 Step 各自測試、變異、R1，GO 才接下一個。
