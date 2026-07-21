---
name: lead-intake
description: >
  把一條「原料」(X 推文 / 產業報導 / 法說會 / 論文 / 小道消息)從進場到入庫的完整驗證 SOP。
  當使用者丟來一條推文、一則新聞、一份文件、或任何「我看到這個消息,該怎麼查證、該不該加進知識庫」
  的線索時,務必使用本 skill。它定義:拆原子 claim → 依源登記表跑獨立驗證 → 套用證據/獨立性/幻覺
  鐵律自動標記 → 分層決定入圖或 park → 接既有 extract/loader pipeline 入庫 → 產出 Directional
  Lane Memo。本 skill 是引擎B(線索)與引擎A(知識庫)之間的閘門,也是系統規模化「亂抓」後不被
  低品質資訊淹沒的護城河。觸發詞:驗證推文、查證消息、這條要不要入庫、餵給引擎A、跑 intake、線索處理。
---

# 線索驗證入庫 SOP (Lead Intake)

## ⚡ Fast Path（≤3 輪，常用入口）

當使用者看到一條 SNS 貼文 / 標題 / 幾句話，想快速知道「值不值得繼續研究」：

**Turn 1 — 分類（研究 agent 做）：**
讀輸入後立刻給：
```

同時，凡是具名公司、可歸因、可證偽且有 expiry 的 qualified lead，先呼叫
`decision_lab.intake.capture_signal` 保存 Signal 與 observed-time Shadow Observation；這一步不代表
evidence admission、不寫 Engine A，也不自動建立 funded paper。後續 Coverage／Action Card 只呼叫
Decision Lab primitive，不在本 skill 複製 Gate、部位百分比或 sizing 公式。
訊號類型：[產品/技術消息 | 供應鏈異動 | 法說/財報 | 市場情緒/猜測]
關聯圖內公司：[列出或「無」]
初始 tier：[1-4]
```

**Turn 2 — Go/No-Go（研究 agent 判斷，說明理由）：**
| 情況 | 判斷 |
|------|------|
| tier 1-2 且關聯現有 thesis 的公司 | **Go** — 值得入庫，觸發文件發現 |
| tier 3 且有新角度 | **Go with caveat** — 入庫但需補獨立來源 |
| tier 4（純社群猜測）或與現有圖無交集 | **No-Go** — 存為 lead-only，不走 pipeline |
| 有具體公司名 + 具體動作 + 可查 | **Go** — 走 company-onboard 補資料 |

**Turn 3（若 Go）— 先追原文，再觸發文件發現：**
完整讀取並執行 `skills/source-trace/SKILL.md`。追到原文才以原文進抽取；tier 1–2
轉述未能取得上游文件時依手冊誠實降級；tier 3–4 未果只留 lead，不生成 extraction。
若結果需要新公司完整 onboarding，再切換到 `skills/company-onboard`。本機美股文件可用
`python fetchers/edgar.py --ticker <TICKER>`；遠端 chat 不得假設可執行本機命令。

用戶可在 Turn 2 說「No」直接結束，或說「只存不研究」跳過 Turn 3。

---

## ⚠️ 這個 skill 為什麼存在(怕忘記版 — 先讀這段)

**問題:** 當 StockBotv2 成熟後,你會開始「亂抓」大量資訊(推文、報導、法說、論文)來發想、餵知識庫。
抓資訊本身是大宗商品,誰都能爬。真正決定你的庫是「可投資的知識資產」還是「一坨會互相佐證的幻覺」的,
是**那道『不讓什麼進圖』+『每條進圖的東西都能追回源頭』的閘門**。

**這個 skill 就是那道閘門的明文流程。** 它的目的不是怕你忘記判準（判準散在 `AGENTS.md` 的「屬性歸位」、「第一次真實抽取」、「Thesis 生命週期」、「自我報告確認偏誤」
與「來源獨立性鐵律」裡），而是把那些判準從「教訓」翻譯成「**LLM 每次都能照跑的步驟**」，並補上 `AGENTS.md`
原本沒有的兩塊:**(1) 拆 claim → 逐條驗證的迴圈**、**(2) 規模化時的自動分層處置**(人不可能每條都手審)。

**護城河的精確定義:** 不是爬蟲,是這套 provenance + 來源獨立性閘門的紀律,在規模化、且交給會漂移的 LLM
跑的時候,還能穩定執行。沒有這份 SOP,每個 session 的 agent 會重新賭一次要不要查、查多深、怎麼標記。

**這份是 v0,故意會壞。** 等引擎A 成熟、開始真實流量時拿去撞它,撞出的洞回頭修這份 SOP(L2 精神)。

---

## 適用範圍 / 何時觸發

- 輸入:一條 X 推文、一則產業報導、一份法說會 / IR 文件、一篇論文、一個小道消息。
- 不適用:已經是結構化、已驗證的資料(那直接走 `extract.py` → loader)。本 skill 專管**未驗證的原料進場**。
- 核心心法:**原料進來預設是「線索(lead)」,不是「證據(evidence)」。** 要升格成可入圖的證據,必須通過下面的閘門。

---

## 鐵律(整條流程都遵守,違反者該條 claim 不得入圖)

1. **來源獨立性(最重要):** `confidence` 只在不同 `origin_event` × `origin_entity` 之間才累加。
   一條推文提到 5 家公司,仍是**一個** origin_event(作者),不是 5 重佐證。轉述他人法說 ≠ 該公司的原始事件;
   要算數必須回到原始文件。每個 source 記 `origin_entity`(誰發出)+ `origin_event`(哪個原始事件)。
2. **證據四階(`evidence_tier`):** 1 filing/法說逐字/IR/客戶供應商直接揭露 > 2 官方名單變動/design-win 公告/
   產能通知 > 3 可信產業報導/券商摘要 > 4 社群貼文/論壇。推文 = tier 4,沒得商量。
3. **L8 自我報告偏誤:** 供應商自己的法說/IR 不能當「自己是瓶頸/sole_source」的獨立佐證。`sole_source` 確認
   來源必須是**客戶端或第三方**。供應商自稱 → `verified_by_absence`(弱,`confidence ≤ 0.5`、
   標 `sole_source_evidence_quality: weak`);客戶/第三方印證 → 才可 `verified_by_search`(強)。
4. **L6 幻覺逐字檢查:** 具體型號/公司名/數字**必須在來源 quote 裡逐字出現**才可建節點。若 quote 只給類別詞
   (如 "data center interconnect"),不可推出具體型號節點(如 ZR/ZR+)。形容詞("reference laser"、
   "god-mode"、"mog every player")不是事實,不可當 node attribute。
5. **provenance 鐵律:** 每個 node/edge 必掛 `source_ids`,且用全域唯一格式 `<doc_id>_s<N>`(L6 Gap2),
   不可用文件局部 ID。
6. **L4 屬性歸位:** 物理現實 → node;會隨關係另一端變的(substitutability/sole_source/lead_time/供應商 ramp)
   → edge;會隨時間變的(市場認知/擁擠度)→ 不進圖,進引擎C 的 Postgres 時間序列。
   **記住:瓶頸的 alpha 大半在邊上,不在點上。**
7. **間接關係更正(tier-3 客戶地圖常見):** tier-3「客戶地圖」常把「X 的零件出現在 Y 的產品裡」
   寫成「X 直接供貨 Y」。若獨立來源顯示其實是多跳(X→中介→Y),正確處置是:建齊正確的多跳邊、
   **移除那條錯形狀的直接邊**(不是只降 confidence——低分的直接邊仍在斷言錯的結構,會誤導查圖的人),
   再把原 tier-3 claim 改掛節點當「已更正」紀錄。動圖前先備份受影響物件(見 `loader/manifests/` 慣例)。

---

## 流程(端到端)

### Step 0 — 輸入分類與登記
- **先查再 onboard(去重防呆):** 取好原文 URL 後,**先問圖「這份文件是不是已經在了」**——用該 URL 或
  origin_event 查有無既有 `SourceDoc`(`MATCH (sd:SourceDoc) WHERE sd.url ...`),避免同一份文件被以不同
  `doc_id` 重複 onboard。`doc_id` 是自取的名字、不是文件身分;换個名字系統不會自動擋。loader 已有 URL 去重
  guard(同 URL 不同 doc_id 會 fail closed);`query/health_audit.py` 有「重複 SourceDoc」事後巡檢。
- 判定原料的 `source_type`(social/news/transcript/filing/ir_deck/industry_report/paper)與初始 `evidence_tier`。
- 原始文字存進 `library/raw/`,給一個全域 `doc_id`(例:`tweet_<handle>_20260629`)。
- **輸出:** 一筆 intake 紀錄(doc_id / source_type / tier / origin_entity / origin_event / 原文連結)。

### Step 1 — 拆原子 claim（`AGENTS.md` 原本沒有的步驟）
把原料拆成獨立、可單獨驗證的主張。每條標:
- claim 文字(盡量逐字)
- schema 落點(會變成哪個 node / 哪條 edge / 哪個 Claim)
- 初始 `demand_proof_level`(confirmed/guided/inferred/speculative)
- 這條是「事實主張」還是「作者推斷/形容」(後者標記,不進驗證迴圈,只當 lead)
> 一坨敘事拆開後通常是 5–15 條強度天差地別的主張。不拆,就會把作者的形容詞當成事實入圖。

### Step 2 — 驗證迴圈（依 `AGENTS.md`「來源登記表」）
對**每條事實主張**，完整讀取並依 `skills/source-trace/SKILL.md` 跑共同追源手冊。
市場路由、什麼算原文、tier 1–2 誠實降級、tier 3–4 未果隔離與嘗試紀錄格式，
一律以該手冊為單一事實來源，本 skill 不複製第二份分路規則。

- 目標仍是 ≥3 個不同 `origin_entity`，但同一原始事件的多份轉述只算一次。
- 排序先做最高槓桿的客戶端／合作方 tier-1 文件；找反證與找支持證據同等重要。
- trace 結果為 `isolated_tier_3` 或 `lead_only_tier_4` 時，不進後續自動標記／入庫步驟。
- **輸出:來源核對表** — `claim × source(doc_id_sN) × origin_entity × evidence_tier × 逐字 quote × 支持/反對/不確定`。

### Step 3 — 套鐵律自動標記
依 Step 2 結果,對每條 claim 機械地套上面鐵律:
- 湊不到 ≥3 獨立 origin_entity → `confidence` 封頂、sole_source 一律 `weak`
- 來源全是被分析公司自己 → 標 `sole_source_evidence_quality: weak`(L8 #3)
- 具體實體沒逐字出現 → 退回 claim、不建節點(L6)
- 算 `confidence`:只在不同 origin_event 間累加

### Step 4 — 分層處置（規模化關鍵，`AGENTS.md` 尚未展開的操作層）
**「亂抓」流量下,人不可能每條都手審。** 用下表自動分流,人只審「升格」這一關:

| 情況 | 處置 |
|------|------|
| tier ≤ 2 且 ≥2 獨立 origin_entity 印證 | 自動寫入圖(node/edge,`active`),記 source_ids |
| tier 3,或獨立來源不足但無矛盾 | 寫入圖但低 confidence + 標 `needs_review`;進人工 review 佇列 |
| tier 4(純社群),或僅作者推斷/形容 | **不入圖**,存成 `lead-only`(留在 `library/raw/` + intake 紀錄),當未來搜尋線索 |
| 有來源直接矛盾 | park 成 `conflict`,人工裁決,不自動入圖 |
> 原則:**寧可 park,不可污染圖。** 圖的價值在每條都可追溯;一條沒來源的 claim 進去,整個庫的可信度打折。

### Step 5 — 入庫(接既有 pipeline,不重造輪子)
通過 Step 4 要入圖的 claim:
- 整理成 DB 無關中介格式(`schema/intermediate_format.schema.json`),如同 `extract.py` 的輸出
- 跑 `loader/validate.py`(vocab + schema 形狀檢查;新 relation/type 先補 `schema/vocab.json`)
- 跑 `loader/load_to_neo4j.py` 寫入(Claim 自動補 `name`,L6 Gap1)
- node/edge 帶齊 `source_ids`(全域格式)、`confidence`、L4 歸位好的屬性

### Step 6 — 產出 Directional Lane Memo
若這批線索構成一個方向,用 `query/graph_context.py` 取 context → `thesis/generate_lane_memo.py`
(system prompt:`prompts/lane_memo_system.md`)產出 Lane Memo 草稿。必含:
- 一句 thesis / 需求驅動 / stack 摘要 / 主瓶頸 / 最強證據 / 什麼會推翻它 / 接下來盯什麼
- **variant perception(必填):** 用「**當前股價/估值隱含假設 X → 本 thesis 認為 Y → 催化劑 Z**」格式,
  從 forward P/E / EV-Sales 反推,**不是**「多數人沒注意到」。缺這段不能升格(估值數字現缺 → 標 TODO,等引擎C)。
- **`disproof_condition` + 核查頻率 + 觸發後 48h 動作**(L7,缺這兩個欄位等於沒裝火警)。
> Lane Memo 是方向備忘,**不是可操作投資建議**。升格 Watchlist 需另過財務核驗 5 項(L9),那是 gate 不是本流程。

---

## 與既有系統的接點(檔案對照)
- Signal／Shadow capture：`decision_lab.intake.capture_signal`（qualified lead 先保留，再跑研究）
- Decision Lab Action Card：`python -m decision_lab ... card <decision_id>`（純讀，不產生交易）
- 原文落地:`library/raw/`
- 中介格式:`schema/intermediate_format.schema.json`、字彙:`schema/vocab.json`
- 抽取參考:`prompts/extract_system.md`(L6 Gap4 幻覺規則在此)、`extract.py`
- 入庫:`loader/validate.py` → `loader/load_to_neo4j.py`
- 取 context:`query/graph_context.py`
- Lane Memo:`thesis/generate_lane_memo.py`、`prompts/lane_memo_system.md`、評分:`thesis/scoring_rubric.md`
- 找盲點(對產出的 thesis 做紅隊):`skills/blind-spot-audit`

## 產出物(一次 intake 跑完應該有)
1. intake 紀錄(doc_id / tier / origin / 連結)
2. 原子 claim 表
3. 來源核對表(claim × source × origin_entity × tier × quote × 立場)
4. 分層處置決定(哪些入圖 / 哪些 lead-only / 哪些 conflict)
5. (若入圖)中介格式 JSON + 通過 validate
6. (若構成方向)Lane Memo 草稿

## 已知會壞的地方 / 等著撞(v0,撞到回頭修這份)
- **variant perception 需要估值數字**,引擎C 未上線前只能手填或標 TODO — 這是目前最大缺口。
- **「≥3 獨立 origin_entity」門檻可能太嚴或太鬆**,真實流量會告訴你。
- **Step 4 自動入圖的 tier/數量門檻是拍腦袋的**,要用 precision/recall 撞(入了多少垃圾 vs 漏了多少真貨)。
- **拆 claim 的顆粒度**沒有客觀標準,不同原料可能要不同粒度。
- **L5 單一 lens 風險:** 很多原料來自偏多頭的小市值瓶頸獵手(X 大佬),別讓系統世界觀被綁死;一律當「眾多視角之一的 weak source」。
