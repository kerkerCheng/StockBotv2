# StockBotv2 — 專案記憶 (Project Memory)

> **本檔回答一個問題：我可以／不可以做什麼？** 只放目標與邊界：authority 邊界、人工 gate、資本硬擋、協作規則、
> lesson 的判準句。任何 session 在此資料夾開工前先讀本檔。
>
> ⚠ **准入判準（2026-09-22 定案）：這句話指名了函數、表、門檻值或 Phase 嗎？** 指名了就是手段，不住這裡——
> 做了的住 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，要做的住 [`docs/ROADMAP.md`](docs/ROADMAP.md)。
> 唯一例外是**查證命令**：它讓現況陳述可否證。本檔每個 session 完整載入，每加一段都在花未來每一次執行的 context。

**定位：** 研究輸入（結構／證據／財務）＋決策責任 → 有根據且可控的投資決策。**系統不給部位尺寸**——買多少、什麼時候買
由使用者自行判斷並手動下單。本機單人自用，使用者會寫 Python。

**目標（2026-09-16 定案）：** 邊緣小公司的 **power-law 倍率**（2 到 10 倍：某個集中需求把量灌進一層薄的供應商），
不是大型股的 20% 錯價，不是 beta 波動。**小賠多檔一檔補回；結構不變就抱；出場只認反證。**
**題材是會換的，本檔不綁題材。** 現行題材（2026-09 是 AI capex）與需求錨住 ROADMAP「研究主題範圍」與需求錨 config；
新題材由使用者選，經 decompose 進入。

**方向（2026-09-22 定案）：圖是中心。** 把圖建成層中心、讀懂它、由個股敘事消費讀圖；財務只回答三個是非題。
**圖到人之間沒有任何一段算分數。** 決定紀錄（G1–G12）：
[`docs/brainstorms/2026-09-22-graph-first-direction-decision.md`](docs/brainstorms/2026-09-22-graph-first-direction-decision.md)。
brainstorm 檔讀哪些、不讀哪些見 [`docs/brainstorms/README.md`](docs/brainstorms/README.md)。

## 本檔的角色與另外五份

| 檔案 | 回答的問句 | 什麼時候讀 |
|---|---|---|
| **`AGENTS.md`**（本檔） | 我可以／不可以做什麼？ | 每個 session 開工前 |
| [`CONCEPTS.md`](CONCEPTS.md) | 這個詞是什麼意思？ | 遇到不懂的詞 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 系統長什麼樣、為什麼這樣切？ | 新增 module／動邊界前 |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | 這件事怎麼跑？ | 要實際執行操作時 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 接下來要做什麼？ | 規劃或決定下一步時 |
| [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md) | 一個開發請求要經過哪些節點？ | 收到「我想做 X」時 |

判準：**OPERATIONS 被改壞 → 跑不起來；本檔被改壞 → 跑起來了，但做錯事。**
Lesson 的事發經過與實作落點住 [`docs/lessons-incidents.md`](docs/lessons-incidents.md)（不自動載入）；
被本檔取代的舊章逐字封存於 [`docs/archive/`](docs/archive/)。動 contracts 前必讀
[`docs/refactor/historical-failure-matrix.md`](docs/refactor/historical-failure-matrix.md)。

## 工作語言（繁體中文）

**與使用者的所有溝通、以及實作過程本身的敘述，一律用繁體中文——不只是最終答案，過程也是。**
使用者輸入可能是簡體（語音所致），不改變工作語言。涵蓋對話、狀態更新、計畫、Task／commit／PR 說明、plan 檔、
`docs/` 報告、skill 輸出。程式碼註解跟隨該檔既有慣例。**維持原文、不強行翻譯：** 識別符、既定英文術語、
第三方 API 欄位、檔名、一手文件逐字 quote。發現過程飄成英文，視為違反本規範，切回中文。

---

# 憲法

## 五條 authority separation

引擎命名是現行實現方式（見 ARCHITECTURE）；**不可變的是權責分離**，不是四引擎架構本身（2026-09-03 定案）。

| # | Authority | 擁有什麼真相 | 可變性 |
|---|---|---|---|
| **A1** | 結構／證據 truth：實體、關係、claim、provenance、逐字引文 | 可重建 |
| **A2** | 財務觀測：帶時戳的財務／市場／共識 | projection 可重建；人工 ledger 只能 append |
| **A3** | 研究判斷：讀圖、敘事、thesis——「我們相信什麼、憑什麼、什麼會推翻它」 | **可重算** |
| **A4** | Portfolio／Risk：目前曝險、目標配置、硬上限 | 可重算 |
| **A5** | 資本決策／問責：「當時憑什麼決定、使用者選了什麼、後來對不對」 | **append-only，Git 救不回** |

1. **A1 不含時變數字。** 股價、估值、共識、未來 EPS、capex 推估永不入圖（L4）。
2. **A3 不得成為第二個 A1／A2 current-state authority。** 研究層是唯讀 view，不落地任何快取表。
3. **A3 可重算、A5 不可重算。** 研究判斷與決策紀錄必須是兩個物件（L10 的直接推論）。
4. **A4 不形成 view，A3 不算尺寸。** view → target exposure → hard limits 是單向的。
5. **A5 是唯一能授權資本的地方**，且 live 永遠 100% 人工。**research automation ≠ capital authority。**

判別問法：一條規則若在「換掉 Neo4j」「把某個 package 拆成三個」之後仍然成立，它屬於這五條；否則它是現行架構，住 ARCHITECTURE。

## 六條 hard invariant

出自 historical-failure-matrix §2，全程適用。查證：`python -m audit invariants`。

| | Invariant | 一句話 |
|---|---|---|
| **INV-1** | IDENTITY | ticker 不是 entity identity；解析走 registry，不猜 |
| **INV-2** | LIFECYCLE | 每個 active object 答得出五問；**每個等待都必須有到期** |
| **INV-3** | NO SILENT DROP | 「查不到了」不是合法 lifecycle；每個 filter 都能報 input／accepted／filtered／reasons |
| **INV-4** | QUEUE LIVENESS | producer 指得出 consumer |
| **INV-5** | MEASURED GATE | 未量測的機制不得享有默認信任 |
| **INV-6** | POINT-IN-TIME & PROVENANCE | 答不出「T 時刻我知道什麼」就明確拒絕，不得靜默回傳當前值 |

## 四個人工 gate（不因任何理由放寬）

**graph admission ／ Engine C 判讀寫入 ／ thesis mutation ／ live choice-fill。**
`go` 一律只授權該項自己的 action type：研究 `go` 不含入圖、入圖 `go` 不含 thesis mutation、**任何 `go` 都不含 live**。

- gate 攔的是「新的知識主張」，不是「這個欄位在哪張表」。判準沿用 L10「這筆資料今天重新取一次拿得回來嗎」：
  `mechanical`（結構化數字、指得出一手來源位置、任何人重讀得同一個數）不需 pq2；`judgment`（要決定「這算不算」）維持 pq2；
  **未宣告一律當 judgment。**
- **放行與收緊必須同時發生**（L15）：拿掉一道人工閘門就必須在同一個 change 補上可機械驗證的補償控制。
- **不得用 ingest／retrieval 日期冒充 `published_at`**；推不出日期的留 null 並列進報告（L11-5）。
  查證：`python -m audit invariants --only PointInTime`。

# 授權與決策

## 授權介面唯一：pq2 編號 ＋ `go`

- **所有真正需要使用者決策的事只有一個編號空間。** raw／triaged leads 留在 pq1 自動研究，不占 pq2 編號。編號到 resolve 才釋放。
- **授權載體唯一（2026-08-30）：** 需要核准的研究與 authority 動作一律先鑄 `manual` 型 pq2 編號再請求；口頭「可以做」不構成授權管道。
  Onboard 也走 pq2（prepared RA 取 `ra_admission` 編號，packet 必含 L8 來源清單）。
- **`go` 的語意＝推進到下一個人工 gate。** 互動 session 收到 `go` 就在當次把研究做到產出 packet 或誠實 park；
  無人值守可只做一段，未完成的留在佇列由下一個執行者接續，**不得把「已排入」回報成「已推進」**（L13）。
- **使用者主動指示＝已授權。** 鑄號只為稽核（受理時即 resolve），**不得回頭再請求一次 `go`**。`go` 請求流程只適用於系統主動提案。
- **常規授權類別（2026-09-09）：** 系統主動提案中，若 `go` 只是**注意力 gate**（授權可逆、不寫任何 authority 的 bounded research
  或派回 pq1），使用者已預先授權，不再逐項請求；清單是封閉字彙，SSOT 與 consumer 見 ARCHITECTURE。**永不列入：** `ra_admission`、
  `engine_c_observation`、thesis mutation／lifecycle、live、任何付費、decompose 選題。判準：**這個 `go` 攔的是注意力還是 authority？**

## 開發項不走 pq2，唯一載體是 ROADMAP（2026-08-31）

判準：**`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？** 前者是研究（pq2），後者是開發（ROADMAP）。
系統主動提出的開發構想寫進 ROADMAP 待排程，**不主動要求 `go`**。ROADMAP 每項強制四欄（做什麼／為什麼／驗收／前置）；
**驗收數字只准數圖、讀圖、敘事、等待 registry、追蹤表裡的東西，不准數「幾檔通過某個 filter」**（G10）。

## 「等你決定」與「等事件」必須分離；等待不得消失

- 兩種等待混在一起訊噪比會降到約 1:1。**只要有一個 blocker 需要人決定，整個項目就留在決策佇列**，寧可多問。
- **人工判讀不等於外部事件：** 現有公開資料已可開始研究的，`go` 的決定是「是否啟動」，留在 user_decision；
  只有世界必須先產生新 filing、掛牌或到達既定日期才是 awaiting_external。
- **所有等待住同一個 registry，每筆有到期，到期是重問不是丟**（INV-2、G7）。反證與確認事件寫下的那一刻就登記；
  語意條件由心跳的 AI 層對 T0 篩過的新文件標旗，**只標旗不判定**，判定留給互動 session。

## 建議只由 ground truth 導出，收尾必附摘要（2026-08-30）

1. **推薦 `go` 前必須答得出「go 會讓哪個數字變」**（L14）；bounded research 解不了的改建議 `pending --trigger`，或直接問 scope 問題。
2. **推薦 `drop` 前必須查 pool 現值**並附查證命令；collector 仍會重新推導的項目 drop 只會換號重生，正確做法是修 collector 端分類。
3. **weekly 只發現、不處置**；處置建議只由讀得到 pool 現值的 daily／互動 session 給出。
4. **收尾建議摘要是義務：** 各列編號＋一句理由，最後一行單獨給可直接複製的批次指令。呈現契約住
   [`skills/daily-brief/SKILL.md`](skills/daily-brief/SKILL.md)；不可退讓的一條：**不得假設使用者能從 `co:*` ID 或內部術語還原主詞**，
   決策行的「不含」欄必須逐項寫出最相鄰的未授權動作。

## 資本與風控

- **Numeric SSOT** 是 `config/investment_policy.json`、`config/beta_policy.json`、`config/target_allocation.json`（後者是錨點不是 gate）。
  只有 **ETF 槓桿 cap 與 5% 單筆上限**是硬擋，其餘曝險只記錄／警告。系統不自動下單；使用者可走 prepared `live_override` 留 receipt。
- **alpha 格只觀測、不設目標（2026-09-16）**；beta 五格目標保留（沒有目標時「誰跌深投誰」就回來）。alpha 的比例只印不比。
- **系統給的建議區間已移除，煞車仍在，而且必須住在真的有人走的路上：** 每一筆非零 live 成交紀錄寫入前都要過 5% 單筆與 ETF 槓桿 cap，超過 fail closed；override 須附理由並留收據。
- **共同可投資現金池只有一條：`Portfolio CASH − cash floor`**，Alpha／Beta 共用；cash floor 不承擔 sleeve allocation，其 authority 失效時 fail closed。
- **兩個槓桿指標不得混用：** `nominal_weight`（投入槓桿 ETF 的資金占 NAV）與 `effective_weight`（乘上倍數後的曝險）；面向使用者不得寫成模糊的「名目槓桿」。
- **Capital Authority：** 私人 Sheet 只保留 `cash_floor` 與 `credit_facility`；credential scope 只有 readonly；**未動用額度不算 NAV／cash／allocation**；
  每次提款、標的與 tranche 都是 explicit manual review，「高信心」不構成 machine permission。
- **部位真相是 Google Sheet（2026-09-16）**；「當時憑什麼決定」的收據跟著成交事件走，舊 Decision Store 凍結唯讀（2026-09-22）。alpha 原則上不用貸款資金是使用者自己的紀律，**系統不建 gate**。
- **曝險邊界：** `bucket=CASH` 計入 NAV 不計曝險；未知非現金持股按 unlevered direct issuer ＋ alpha exposure 誠實降級，不因缺 mapping 阻擋；
  issuer look-through 覆蓋恆為 `partial`，人類輸出一律寫「已知至少 X%」。既有 frozen decision 不回寫。
- **退休貸款資本目標（2026-07-28）：** 使用者約 30 歲、退休約 60 歲；可長抱至到期的貸款資本以約 30 年後淨終值最大化為方向，
  不以降低中途回撤為第一目標。exact review 必須扣除借款成本與到期本金；**月息若需靠賣出 beta 支付則該 tranche 不成立**。

---

# 消費契約：圖是中心（2026-09-22 定案；取代舊「Alpha 呈現契約」，舊章逐字封存 archive）

**系統只負責使用者自己做不動的事：哪些邊緣公司值得看、有什麼新事件、賭對了值多少、判斷錯了值多少、哪個管道與特徵產出贏家。**
買多少、什麼時候買由使用者決定。**產出若無法讓人分辨做了什麼與沒做，它就不算產出。**

- **讀圖與敘事是研究判斷（A3）：** append-only、可重算、**不 gate 任何東西、不濾、不排、不給尺寸**。LLM 可以解析與提議，不可以授權（L15）。
  讀圖必須宣告它讀的是哪一種單位（層或插槽）；賭注必須宣告騎在哪一種上。
- **不得輸出跨檔全序或首選。** 「下一個研究誰」由圖報洞與 lead 並行驅動，優先序由 lead 時間與使用者點名決定，不由分數；
  「該買誰」是人讀敘事的判斷。**走圖的問句不得恆亮**（L14-4）。
- **候選狀態是封閉字彙：可開／缺 X／已定價等回落／不要／已持有。** 「可開」是每檔各自過的 filter 不是分數，可同時多檔；
  **可開為零就零，不得為了非空放寬條件**——讓它非空的路是研究。「缺 X」與「等回落」必鑄 watch；「不要」附理由、append-only。
- **財務只回答三個是非題：會死嗎／已定價嗎／出現在數字裡了嗎。** 每題宣告資料源與「無法量」出口，**不得長回估值模型**。
  「已定價」主參照是自己的歷史、主題籃子只當脈絡、**不設門檻**；敘事的那一句必須引用稽核區的數字。
  歸零旗標（現金跑道／負債／稀釋／going concern）是燈不是數字。
- **進場靠判斷，出場靠 disproof。** 反證用來決定何時認錯，不是進場的前置條件；每條反證寫下即登記 watch。
  `realized`（目標價已達）只提醒，不觸發出場。仍沒有 bull／bear、沒有機率加權。
- **必須點明相關性：** 本圖標的高度集中於當前題材，N 檔不等於 N 個獨立機會；主題翻轉時十檔一起 −50% 是使用者已接受的集中——
  心跳只印回撤，不給燈號、不給動作。
- **候選門檻是覆蓋厚薄，不是上市地**（分析師家數、市值）；非英語 filing 是加分不是門檻。
- **量測：** 追蹤表印三個 power-law 統計量（12／24 個月內達 2 倍的比例、最大單檔貢獻、籃子總報酬）與量測起始日、樣本數；
  基準含主題等權籃子；**圖自己的預測也要量**（讀圖說只有一家、半年後客戶 filing 列出第二家＝讀圖錯）。
  來源標籤跟著 lead 走到 outcome；帳號 tier 只動 pq1 優先序，升降一季一次 pq2。
- **已知會失焦的指標判別法：這個指標會隨我們多讀一份文件而單調上升嗎？** 會 → 它測的是研究量，不得單獨用作瓶頸性證據。
  帳號計分表在樣本不足時量到的是倖存者。
- **一個保守選擇若說不出證據，它是偏差，不是審慎。**

## 等待與心跳

- **Daily 拆三層：心跳**（零 LLM、固定五段永遠出現、印較昨 diff）、**分類**（便宜模型、每日硬上限、失敗不阻斷）、
  **研究**（只在互動 session）。**LLM 失敗心跳照發；「未 triage N」「未檢 N」必印**（L13）。
- 心跳印每個候選狀態的檔數與最老滯留天數、watch 今日醒／到期／標旗數、反證在盯與未盯數。
  **這些是會自己出現的計數器，不是要人記得的段落**（L14）。

## APP：LLM changes cognition; APP reads cognition（2026-09-07）

- request path **不得**跑 LLM、寫任何 authority、抓外部資料、跑金融模型、或因 cache miss 偷偷重建；更新判讀只有明確跑一次 materialize。
  查證：`python -m pytest tests/test_webapp_request_path.py`。
- **首屏的單位是句不是格**：第一層短評、第二層論證、第三層才是格（稽核區）。文字由研究 session 寫進 append-only ledger，
  數字由 authority 填 placeholder，首屏禁字表型別層拒收；沒寫短評就印「還沒寫短評」。
- **缺席不得被壓成「無資料」。** `absence_kind` 由產生缺席的程式自己宣告（L16）；「刻意不主張」只能來自 append-only 的 Abstention 紀錄，
  settled 不讓 readiness 變好。
- **昨天和今天一樣的住 APP，今天變了的＋要你決定的住 Daily**；順序是 invariant：APP 先讀得到，Daily 才能不印；
  **還沒有 APP 畫面的段落一律留在 Daily**，判準是機械的：`python -m webapp status` 列得出那個 kind 才算搬完。
- **APP 沒有任何寫入端點、沒有自己的帳號系統**；認證邊界是 Cloudflare Access，預設只綁 127.0.0.1。四個 gate 不因多一個畫面而放寬。

## Beta：開發凍結（2026-09-16）

只保留「大盤比例」觀測。**`band` 是容忍區間不是 gate；再平衡只用新投入的錢往低於目標的格子補，不賣出；只給差距，不給金額、不排名。**
相對水位只呈現、不參與排序、不換算金額——**一旦有人拿它排序或調整尺寸，它就變回訊號**。
**燈號只表達行情資料狀態，不表達投入建議**；舊語意（可評估／冷卻／暫停新增）已於 2026-08-29 明文**廢止**——安靜消失擋不住下次回填，所以廢止必須寫出來。
兩條相關性警告常駐 APP 頁尾：alpha 與 beta 是同一個賭注；TSMC look-through 約 28% 且系統算不出精確值。細節住 ARCHITECTURE §8。

## 訊號的地位

- **beta 定投擇時已關，不是降級使用**（2026-08-01 三次實測：訊號 gate 定投輸給無腦定投 8.5%、訊號調節借款無可測效果、
  訊號選標的輸給固定單押 22%；完整證據見 brainstorms 2026-07-31）。RSI／MACD／tier／pace 不得以任何名義回到 beta，
  包括改名成「熱度」「節奏」「水位」。
- **其餘 scope 適用通則：未經量測的指標不得參與任何排序或尺寸決定（INV-5），但可以被提出、被測。** 四條件缺一不可：
  宣告 scenario、先量測後放閘、過三個免 outcome 測試（恆亮？不會滅？講不出因果？）、驗收寫成「現有資料有幾筆真的變了」。
- **「買跌最深的」會系統性把錢導向長期較弱的資產**；在 alpha 上更危險——同漲同跌的圖裡「跌最深」多半只是「beta 最高」。
- **量測、訊號、脈絡三分：** 曝險倍數、歸零門檻、利息覆蓋、歸零旗標是量測；RSI／MACD 是訊號；位置指標是呈現用脈絡——拿它排序就變訊號。

---

# 協作與邊界

- **專案記憶唯一權威：本檔**；`CLAUDE.md` 只 `@AGENTS.md`。研究 skill 唯一權威：`skills/<name>/SKILL.md`。
- **開發流程唯一權威：** AGENT_WORKFLOW（模型）＋ development-flow skill（執行）。先 scope triage（Z0–Z3）再定 review 距離（R0–R2）；
  **R2 是唯一花第二份 token 的路徑，六條 trigger 之外不啟動且要人工 opt-in。**
  **Phase 結案的 R2、以及 Phase 執行期間六條 trigger 命中的 R2，使用者已常規 opt-in（2026-09-22）：** 由乾淨 context 的 reviewer 跑驗收命令或審 diff、回 verdict；
  reviewer 唯讀，不 commit、不寫任何 authority；NO_GO 回 AWAITING_HUMAN，不自動修。
- **`GO` 只關閉本 Step，不開啟下一個 Step**；不得偷改 ROADMAP 後繼續跑（要改先給五欄 amendment）。
  **常規推進授權（2026-09-08；09-17 擴大到 Phase 邊界）：** Verdict 為 `GO` 且下一步沒有任何待使用者決定的問題時可直接接續。
  **下列任一成立一律停下：** ①Z2／Z3 且 plan 裡確實有要使用者選的問題；②動到四個人工 gate；③動到資本、live 或 append-only authority；
  ④要改本檔判準句或 ROADMAP 的 Phase／Step 定義；⑤需要 R2；⑥Verdict 不是 `GO`。
  判準：**這條授權買的是「不必為了說一聲而停」，不是「不必為了決定而停」。** 撞到 pq2 gate 時掛號後接著做下一件不需核准的事，不得停在編號上等。
- **Local-first：** 「Claude」預設指本機 Claude Code；cloud＋MCP 是備援，新核心不得依賴 MCP。
- **Provider-neutral：** 本機 Codex 與 Claude Code 是可互換 executor；權限與完成狀態綁 action type、authority 與 receipt，不綁 provider。
- **同一 working tree 只讓一個 agent 寫入**；排程與互動 session 也算兩個 writer。
- **Session memory 不是 authority**：transcript／memory 都是 disposable advisory cache；未寫 authority 的「已 go」不得被視為完成。
- **任何 unattended routine 的 executable surface 變更，都必須在同一個 change 完成 sandbox impact review**；
  **不得用 broad permission 掩蓋整合缺口**——只放行能由既有人工 gate、action type 與 receipt 約束的最窄 command prefix。
- **subagent 委派預設關閉、每次明確 opt-in**；回傳只是 review packet；不得委派任何寫入、核准、入圖、thesis mutation、資本配置、commit／push。
- **Push 是常規動作**；push 前 `git ls-files library/private` 應為空。
- **通知不是 authority**；Canonical Brief 只有一份；發送失敗不得阻斷。
- **不建立與待辦池競爭的第二個狀態源**；daily brief 不留檔；weekly report 留檔但不是 current-state truth。
- **一手來源優先**；出投資建議前必看五項：客戶集中度、毛利率／產能利用率、backlog／營收結構、稀釋、估值壓力。

## 現況數字會過期，判準不會（2026-08-19）

任何「目前 N 筆」型陳述在文件裡都是會腐壞的快照。①政策檔與 ROADMAP 陳述現況必附查證命令；②引用自家文件的現況陳述前先跑那條命令；
③Lesson 的事發數字是歷史記錄，帶日期、不更新；④數字若需常駐可見，做成會自己出現的計數器。清單同理會腐壞。

# 圖的寫入紀律

完整規格見 [`schema/graph_schema.md`](schema/graph_schema.md)。**表的形狀鎖死，字彙留鬆**（L2）；屬性按 L4 三分歸位。

- `co:*` ID 唯一權威是 `config/company_identity.json`，不憑公司名猜；未命中要區分「ID 沒解析對」與「圖中真無此公司」，不能默默跳過。
- 報價單位 ≠ 結算幣別；未登記且非 ISO 一律 fail closed，**不得為了通過驗證改寫成 ISO code**。
- `confidence` 只在不同 `origin_event` 之間累加；`sole_source` 需客戶端或第三方印證，供應商自稱是弱主張（L8）。
- **每份 thesis／claim 必帶 `disproof_condition` 三件套**（條件、核查頻率、觸發後 48 小時動作，L7）。

---

# Lessons（判準句；事發與實作住 docs/lessons-incidents.md）

引用慣例：回覆或報告中 L 編號第一次出現必須括號備註一句是哪條判準。

- **L1** 核心元件優化能力、生態成熟度、可觀測性，不優化「系統數量」；需要人工 review 的資料結構，視覺化是硬需求。
- **L2** 「現在搞錯、以後要搬全部資料才能修」的才現在想清楚（表的形狀）；「以後加一列設定就能補」的直接動工（字彙）。
- **L3** 抽取層輸出 DB 無關 JSON；流程穩了再包框架。
- **L4 屬性歸位三連問：** ①換掉關係另一端值會變嗎（不變→node，會→edge）；②值會隨時間變嗎（會→帶時戳觀測，不進圖）；
  ③講的是物理現實還是證據強度／市場認知（後兩者→metadata 或時變）。**瓶頸的 alpha 大半在邊上，不在點上。**
- **L5** 外部方法論只抄骨架、不綁相依；它是單一 lens，別讓系統世界觀被綁死。
- **L6** Schema gap 只有真實資料撞上去才現形；跨文件 MERGE 要防 ID 衝突；**具體型號／公司名必須在 quote 裡逐字出現**。
- **L7** `disproof_condition` 是欄位不是流程：必附核查頻率與觸發後 48 小時動作。生命週期 active→watch→review_required→retired／revised，
  另有 realized（只提醒）。
- **L8** 供應商的法說會不能作為「自己是瓶頸」的獨立佐證：多文件入圖前至少 3 個不同 `origin_entity`；`sole_source` 確認須客戶端或第三方；
  所有 source 同一供應商的 sole_source 邊標 weak。
- **L9** 跨引擎 join 必須有靜態 lookup 的共同 ID，不由 LLM 推斷；私有公司映射到明確 null（＝INV-1）。
- **L10** 判準「這筆資料今天重新取一次拿得回來嗎」：拿得回來→可改 schema、重建、覆寫；拿不回來→只能 append。
  只適用 Engine A graph 與可重建 projection；**不適用 private append-only authority**（Engine C ledger、Decision Store）。
- **L11 自己引用的事實要套跟圖裡 claim 同一套追源紀律：** ①審計／法律術語的措辭精度本身是 claim；②別對外部 claim 嚴、對自己引用鬆；
  ③多個二手都這樣說≠一手已證實；④追源前先 grep 自家庫；⑤「我找不到」與「它不存在」是兩個 claim，解讀「沒命中」前先問
  **「如果答案存在，它會在我手上這份文件的哪一節」**；⑥同一紀律適用於自己的技術診斷與修法——落地前跑一條試圖讓結論變假的命令，
  提案時就答「如果這個修法是錯的，最先壞掉的是哪一筆現有資料」並去看那一筆。
- **L12** 一個表示承載兩種語意時，下游被迫二選一而兩邊都錯；修法永遠是先分開再各自定規則。訊號：放寬與收緊都會壞；修法讓警報消失得太乾淨。
  任何會改變輸出的輸入都必須出現在該輸出的證據欄位裡。
- **L13** 基礎設施改動的驗收是「產出出現在下游消費者手上」，不是「元件會動」；最危險的是成功與失敗在同一訊號上同形（＝INV-4）。
- **L14 未量測的機制不得享有默認信任，gate 也不例外：** ①驗收寫成「現有資料有幾筆真的變了」，**且那個數字只准是圖、讀圖、敘事、
  等待 registry、追蹤表裡的東西，不准是「幾檔通過某個 filter」**（2026-09-22 改寫；原句曾把研究導向補格子過 filter）；
  ②gate 本身也要驗；③先量測後放閘；④三個免 outcome 測試：恆亮、不會滅、講不出因果；⑤維持營運直接修但不算進展，
  改變行為先答「哪個 baseline 數字變」。**真正的防呆是會自己出現的常駐計數器，不是要人讀的段落。**
- **L15** 先解析「這是什麼」，再判「它算不算數」：gate 的正當性來自對目標有幫助；語意交給語言處理，權限永遠 deterministic；
  LLM 可解析可提議不可授權；放寬解析不等於放寬判準。
- **L16** 分類已有 SSOT 時要讓它跟著資料走到需要它的地方；修法是把分類附到 payload 上；字彙有行為後果就必須被強制、同義詞也拒收；
  不要用會誤報的 linter 防這件事。
- **L17** 「只認得當初那個案例」的機制當下就修，別進 backlog；十行內不動 contract 當下修，動 contract 給 proposal，重寫子系統才進 ROADMAP。
  三問：key 真的唯一嗎、欄位是覆蓋還是聯集、對稱面做了嗎。general 到資料支持的那一格為止。
- **L18** 任何「把原始證據換成標籤」的步驟必須讓標籤指得回原始證據；判別法：工具輸出裡有沒有一個字是文件實際寫的；
  「請深入思考」型修法無效，根解是拿掉資訊落差；機械偵測器的用途是自動生出問句，不是自動修。
- **L19（2026-09-22 新增）每 session 載入的檔裡的手段句會被當成目標。** 「唯一排序權威」「必須輸出首選」四句加一條綁排序的驗收行，
  讓研究火力去補格子過 filter（Goodhart 鏈）。判準：**手段句不進本檔；驗收數字不准綁 filter 通過數。** agent 讀到「唯一」「不得」時
  分不出邊界與手段，所以只能靠不把手段寫進來。

## 文件化學習

踩過的坑與設計決定沉澱在 `docs/solutions/`；詞彙見 CONCEPTS。「某個事實塞不進既有欄位」時先讀
[`closed-vocabulary-registry.md`](docs/solutions/architecture-patterns/closed-vocabulary-registry.md)：taxonomy（字彙留鬆）vs contract（打開它是 bug）。
新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`；`tests/test_config_tracking.py` 是這道剎車。
