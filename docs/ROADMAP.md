# StockBotv2 — Roadmap

> **本檔只放 active future work。** 判準與契約在 [`AGENTS.md`](../AGENTS.md)；
> 指令與程序在 [`OPERATIONS.md`](OPERATIONS.md)。
>
> **2026-09-16 轉向：** 前一版路線圖（Alpha Research Refactor Phase 0–8、研究閉環 P0–P7、賭注 V0–V4、
> Post-MVP A–H、開放 backlog 約 90 列）已**整份逐字封存**於
> [`docs/archive/roadmap-pre-alpha-edge.md`](archive/roadmap-pre-alpha-edge.md)（照 2026-09-03 先例）。
> 每個標題與每一列未結案項的去向見
> [`docs/refactor/alpha-edge-step0-migration.md`](refactor/alpha-edge-step0-migration.md)。
> 轉向的決定紀錄（使用者原話、D0–D15、驗收、紅隊）是
> [`brainstorms/2026-09-16-alpha-edge-discovery-requirements.md`](brainstorms/2026-09-16-alpha-edge-discovery-requirements.md)。

---

## ⚠ 開發項只住這裡，不進 pq2（2026-08-31 使用者定案）

**本檔是系統開發項的唯一載體。** 改的是程式、config、schema 或呈現邏輯，而不是圖／
Engine C／thesis／資本裡的任何一筆事實 → 它是開發項，寫進本檔，**不鑄 pq2 編號**。

判準：**`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？** 前者是研究（pq2 編號），
後者是開發（本檔）。例如「補某條邊的 substitutability」改變圖裡的事實＝研究；
「改 `rank_bottlenecks` 的排序鍵」改變系統行為＝開發。

理由是**兩種東西的決策資訊完全不同**：研究項要的是「證據夠不夠、授權到哪」，一行決策行
就夠；開發項要的是「這會讓哪個數字變、驗收條件、與其他開發項的相對優先序」（L14 第 5 點），
而那些只有在本檔的表格裡排得出來。

系統主動提出的開發構想寫進本檔待排程，**不主動要求 `go`**。開發項落地後若要動圖或
authority，那是另一個 pq2 編號。判準全文見 [`AGENTS.md`](../AGENTS.md)「授權載體唯一」。

**每項強制四欄：做什麼／為什麼／驗收條件（哪個數字會變）／前置。**
沒有驗收條件的不准進佇列（L14 第 1 條）。


---

# 現行路線圖：Alpha Edge——邊緣小公司的 power-law 漏斗

**North Star：** 系統要能回答
**「哪些邊緣小公司會因為集中需求（今天是 AI capex）卡在它們身上而被放量；我們多早、憑什麼、從哪個管道知道；
事後哪個管道與哪些特徵真的產出了贏家？」**

使用者原話（2026-09-15～16）：「我們要往 AXTI 或像台股之前上銓或其他光通的邊邊走，搭配光通現在的集中度，
這樣才有機會被放量，這確實才是我最初想像的目標，現在確實花太多力氣在 beta 上。」
「10 倍當然只是目標，2、3、5 倍我都很 OK，但主要是想表達是這種等級的倍率，而不是 beta 波動。」
「alpha 部位結構不變就一直抱。」

```
發現（誰值得進佇列） → 篩選（它是不是倍率候選） → 表達（怎麼買、怎麼抱、怎麼砍） → 量測（哪個管道與特徵產出贏家）
```

**為什麼轉向（2026-09-15 blind-spot-audit 的三個 🔴，數字為當時實測）：**
①**儀器對不上目標**——FY+1 EPS × 目標倍數找 20% 錯價是高覆蓋大型股的工具；COHR 首屏「賭對了值 244、現價 266」
是這個錯位的直接產物（thesis 講 FY28 產能倍增，模型只有 FY27 一格）。②**想去的地方排序看不到**——上詮、聯亞、華星光、
全新、IET-KY、Sivers、Aehr 在圖裡都有邊、也接得到需求錨，但 `rank_bottlenecks` 把未填 `substitutability` 的邊當 0
過濾（門檻 4），可投資排序 37 列一檔都沒有；整張圖覆蓋 15%，填了的全是大公司。③**研究火力與資本落點錯位**——alpha 格
實際 1.6%（目標 10%）；22 檔追蹤等權 −3.0% vs QQQ；12/22 在漲完之後才入圖；單一帳號兩個月 492 則：65% no-go、
31% parked、4.5% 進圖。

## 現在在哪裡（一頁看完）

**一句話：機制蓋好了，研究只做了三檔。**

系統裡有 73 家公司，每一家每天都自動更新得出一頁分析。但往漏斗下游走會急遽收斂：

| 走到哪一步 | 幾家 | 這一步是什麼意思 |
|---|---|---|
| 進到系統、每天自動更新 | **73** | 有行情、有財報基期、有供應關係 |
| 有研究判斷 | **63** | 有人寫下「我們相信什麼、什麼會推翻它」 |
| 有估值 | **58** | 有目標倍數，算得出現在貴不貴 |
| **有賭注** | **3** | **寫下了「賭對了值多少、判斷錯了值多少」**（AXTI／COHR／LITE） |
| 有倍率射程 | **2** | 寫下了「要翻倍的話是哪一年」（AXTI／COHR） |

**最陡的一階是 58 → 3。** 估值做了 58 家，但只有三家有人寫下我們到底賭什麼。
而目標要的是「**小賠多檔、一檔補回**」——**三檔湊不出 power-law。**

⚠ **Phase 0–6 全部結案；唯一還在進行中的是 Phase 7，而它卡在研究端不是程式。**
（2026-09-21 更新：Phase 1 已於 09-20 結案、4b 於 09-21 結案。原句寫「三個在進行中（1／4b／7）」，
那是 09-20 當天的快照——現況數字會腐壞，判準不會。）

查證（這幾個數字會腐壞，引用前先跑）：
`python -m webapp status`（幾家）｜`python scripts/multi_year_check.py`（倍率射程）｜
讀 `library/private/app/analyst_view/*.json` 的 `overview.payoff.simple.value`（幾家有賭注）

## 四層漏斗：已有／缺（架構骨架；解法留給各 Phase 的 PLAN_PROPOSAL）

| 層 | 要回答的問題 | 已有 | 缺 |
|---|---|---|---|
| 發現 | 誰值得進佇列 | `crons/harvest_leads.py`（X／RSS／EDGAR，零 LLM）、lead-intake、source-trace、圖的傳播、MOPS／MFN／RNS fetcher | 帳號登記表與計分表、來源標籤跟著 lead 走到 outcome、傳播到小公司（「誰供應這個供應商」）、MOPS 重訊與月營收 watcher |
| 篩選 | 它是不是倍率候選 | `rank_bottlenecks`、L8、五項核驗清單、`analyst_count` 快照 | 機械條件（覆蓋家數上限、市值上限、瓶頸業務占營收下限、至少一條外部印證的瓶頸邊、入圖前 30 天漲幅上限、12 個月內指名假設的催化劑）；INV-3 逐檔報 input／accepted／filtered／reasons |
| 表達 | 怎麼買、怎麼抱、怎麼砍 | thesis lifecycle、反證三件套、5% 單筆硬擋、`alpha/reverse` 反向橋 | 多年反向橋（「五倍要什麼為真」）取代 FY+1 EPS；賭注與判斷錯的對稱 overlay；歸零旗標；entry criterion 降為 optional 中的 optional |
| 量測 | 哪個管道與特徵產出贏家 | 22 檔追蹤表、chasing 計數、`hypotheses.py`、`lead_trace_status` 封閉字彙 | 來源歸因欄、帳號計分表、power-law 統計量、回溯評分 |

**篩選是 filter 不是分數**（沿用 2026-09-15 D2）。籃子頁「首選」的三個條件換成漏斗條件；沒有一檔通過就沒有首選，
**不得為了讓籃子非空而放寬條件**——讓它非空的路是研究。

## Phase 表

> **每列只答三件事：做什麼、到哪了、還差什麼。**
> ⚠ 每個 Phase 的**交付史、實測 before → after、踩過的坑**全部逐字搬到
> [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md)（2026-09-20，一字未刪）。
> 搬走的理由：那 8 列曾佔全檔 **34%**、最長一列 **17,138 字元**，而且 Phase 1 那列在反斜線處斷成兩行、
> **表格實際上是壞的**。要查「當初怎麼交付的」看封存檔；要看「**現在還差什麼**」看本表。
>
> 標記：▶ 進行中｜○ 未開工｜✅ 完成。研究項（pq2）不占本表。
>
> **推進規則（2026-09-16 使用者定案，未變）：** Verdict 為 `GO` 且沒有待使用者決定的問題時，
> 直接合併 master 並接續下一個 Step，不逐 Step 請核准。**仍要停：** Verdict 非 `GO`、有待決問題、
> 動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句或本表的 Phase／Step 定義
> （後兩者須先給五欄 amendment）。**四個人工 gate 不因此放寬。**

| Phase | 做什麼 | **做完的定義**（驗收行） | 現在 |
|---|---|---|---|
| **0** ✅ | 把系統的說話方式從「找錯價」改成「找倍數」 | 呈現契約整章重寫、每句舊契約列得出去向 | ✅ 2026-09-16 |
| **1** ✅ | 把小公司在圖裡缺的格子補起來，讓它們排得進候選 | ~~排序要出現台股（TW／TWO／ST ≥1）~~ **2026-09-20 修訂：補完三格之後，排序的答案講得出來、而且講得出為什麼** | ✅ **結案**。答案是否定的且有依據：四家台系磊晶廠可替代性 2–3（低於門檻 4），因為**各家在自己年報裡逐字互相指認對方是同層競爭者**。門檻沒放寬、那四家仍排不進來，**而那是正確的** |
| **2** ✅ | 每天一份不靠 AI 的固定日報，排程自己跑 | 連續 3 天零 LLM 成功發出、每天印「未 triage N」、`drain_limit_per_run`=0 | ✅ 2026-09-20（三天全自動觸發、4／1／1、=0） |
| **3** ✅ | 消息來源記分：哪個帳號真的帶來贏家 | 帳號登記表封閉、每則貼文蓋章、計分表五欄進 APP | ✅ 2026-09-17 |
| **4a** ✅<br>**4b** ✅ | 用機械條件挑出倍率候選，挑不出就誠實說空 | 4a：filter 逐檔報 input／accepted／filtered／reasons ✅<br>4b：~~每一格配 disproof~~ **2026-09-20 修訂：有賭注的檔，其賭注所依賴的 driver 有反證在盯** | 4a ✅（三條已接、兩條量完確認不接）<br>4b ✅ **2026-09-21**（pq2 [641]）：`no_disproof_link` **2 → 0**、accepted **0 → 2**。**算得出倍率的檔已 100% 連得上反證**；LITE 仍被擋是 `no_horizon`（判斷檔沒寫 `multiple_horizon`）——**那是 Phase 7 的形狀，不是 4b 的**，見下方〈4b 為什麼不等 LITE〉。查證：`python scripts/multi_year_check.py` |
| **5** ✅ | 賭對了值多少、判斷錯了值多少、會不會歸零 | 有賭注的檔都要有對稱的下檔（成對，不是固定名單） | ✅ 2026-09-19。⚠ 但歸零旗標**四盞只有兩盞在跑**（現金跑道 67/73、負債 70/73；**稀釋與 going concern 都是 0/73**）→ 見〈[還沒做的開發項](#還沒做的開發項)〉 |
| **6** ✅ | 台股月營收與重訊自動進系統 | 月營收成為一手 datum、重訊 watcher、parked lead 逾期自動計數 | ✅ 2026-09-17 |
| **7** ▶ | 問「要幾倍，哪一格得為真」，而不是「被低估幾 %」 | ~~多年橋**取代** FY+1 主流程；entry criterion 降級~~ **2026-09-20 修訂：寫下倍率射程的檔，首屏的「賭對了值多少」由多年視角回答；沒寫的維持 FY+1 並標明它是哪一種** | **機制端全做完**（倍率階梯／倍率射程／虧損公司改用營收倍數／進 APP／驗收腳本）。**差最後一步：首屏還沒接上多年視角** |

## ✅ 驗收行修訂（2026-09-20 提出，**同日使用者核准並生效**）

使用者的問題逐字：「**真的卡住的是真的有需要卡？還是那只是最一開始設立的 criteria？
不要被我們最一開始設定的細節卡死，以大目標為主。**」

下面三條驗收行逐條重審。**判準只有一個：這條驗收行量的東西，是不是大目標要的東西。**

**三條使用者均於 2026-09-20 核准（原話「都照你提案修改」），已寫進上方 Phase 表。**
⚠ 舊驗收行**劃線留在原處不刪**——它們是當初的決定，看得到才知道為什麼改。

### ① Phase 1「可投資排序要出現台股」——建議：**不該再卡**

| 五欄 | 內容 |
|---|---|
| **原 roadmap** | 驗收行：可投資排序中 TW／TWO／ST 後綴檔數 0 → ≥1（目標 3）；並註明「仍為 0 就不得標完成」 |
| **新觀察** | 研究**已經做完了**，而且答案是否定的：四家台系磊晶廠的可替代性全部低於門檻（聯亞 3、華星光 2、全新 2、英特磊 2），**判準不是自由心證——各家在自己年報裡逐字互相指認對方是同層競爭者**。它們排不進來，是因為**它們不是瓶頸**，不是因為格子沒填 |
| **proposed change** | 驗收行改成「**補完三格之後，排序的答案講得出來、而且講得出為什麼**」。Phase 1 依此結案 ✅ |
| **why** | 大目標是「找到會被放量的瓶頸供應商」，不是「讓台股出現在清單裡」。**原驗收行把一個地區當成了目標的代理**，而實測證明那個代理是錯的。繼續卡著等於要求研究去證明一個已經被否證的假設——那正是 `AGENTS.md` 禁的「為了讓籃子非空而放寬門檻」的鏡像：**為了讓驗收行達標而扭曲研究結論** |
| **impact** | 不動門檻 4、不改任何一家的可替代性、不放寬任何篩選條件。**只改「Phase 1 算不算做完」這一件事**。那四家台廠仍然排不進來，而且那仍然是正確的 |

### ② Phase 7「多年反向橋**取代** FY+1 主流程」——建議：**「取代」換成「有能力且優先」**

| 五欄 | 內容 |
|---|---|
| **原 roadmap** | 「多年反向橋（「五倍要什麼為真」）**取代** FY+1 主流程；entry criterion 降級」 |
| **新觀察** | ①**「取代」會讓事情變糟**：FY+1 那條鏈要對分析師共識，而共識只到 FY+1／+2；多年橋**沒有共識可對**。Step 7.3 在交付當天就論證過這件事，並刻意做成兩條路。②**`entry criterion 降級` 指錯了對象**——實測 73/73 檔的 entry 全是 missing、0 檔宣告過門檻價，它從來不是 gate；真正在用 FY+1 錯價替人決定「值不值得買」的是籃子那條 `payoff_not_positive`。③機制端已經全部做完，今天缺的是**有幾檔寫下了倍率射程**（2 檔） |
| **proposed change** | 驗收行改成「**寫下倍率射程的檔，首屏的「賭對了值多少」由多年視角回答；沒寫的維持 FY+1 並標明它是哪一種**」。`entry criterion 降級`改寫成「把籃子的進場判準從 FY+1 錯價換掉」，並註明它**不是** `EntryCriterion` 那個欄位 |
| **why** | 大目標是「問得出『要幾倍需要什麼為真』」，那個能力**已經有了**。「取代」是手段被寫成了目標 |
| **impact** | 不動籃子任何一條篩選條件（換掉 `payoff_not_positive` 要等夠多檔算得出倍率，否則會對 16 檔全部亮＝恆亮的牆）。不動 FY+1 主 view。**只改「Phase 7 算不算做完」與那半句指錯對象的話** |

### ⚠ ②的一處自我更正（2026-09-20 落地當天發現，**等使用者定案**）

**核准的那句話實作不了，我寫的時候沒想清楚。**

修訂後的 Phase 7 驗收行是「寫下倍率射程的檔，**首屏的『賭對了值多少』由多年視角回答**」。
但實作時比對兩邊的形狀才發現：

- **首屏那把尺要的是四個價格**（COHR 實測：現價 317.36／沒賭對 223.60／賭對 243.97／判斷錯了 197.54）
- **多年橋不產生價格**，它產生的是「要 2 倍，資料中心分部營收得成長 **465%（變成 5.65 倍）**」
  （⚠ 2026-09-20 更正措辭：橋的公式是 `base × (1 + growth)`，`revenue_growth=4.651` 是**成長 465%**；原本寫的「成長 4.65 倍」會被讀成「變成 4.65 倍」，**差一倍量級**。L11-1：措辭精度本身就是一個 claim）

**兩者形狀不同，換不掉。**

⚠ 但那個錯位是真的，而且比我原本寫的更精確——**錯的不是數字，是那句結論的期間**：
系統算出 payoff −23.1%（**FY2027**），研究者據此在首屏寫「所以今天不是加碼點」，
而同一份 thesis 講的是 **FY2030** 的六吋產能倍增。**一句 FY2027 的結論被掛在一個 FY2030 的主張下面。**

**三個選項：**

| | 做什麼 | 代價 |
|---|---|---|
| **(a)** 〔建議〕 | 那把尺**不動**（它誠實回答 FY+1），首屏**另外加一句**「要翻倍需要什麼為真」 | 首屏多一句；但兩個問題各自回答各自的，不互相污染 |
| (b) | 讓多年橋反推出一個 FY2030 目標價，塞進那把尺 | **要多一組沒有證據的假設**（四年後的倍數、四年後的股數），而多年橋現在刻意不猜這些 |
| (c) | 不動機制，改成研究紀律：有倍率射程的檔，短評不得用 FY+1 的 payoff 下「該不該加碼」的結論 | 零程式改動，但**靠自律**——L18-3 說過這類修法在這裡無效 |

**我建議 (a)**：它讓「明年值多少」與「這個結構允不允許翻倍」各佔一句，
而那正是 Step 7.1 當初分開 `market_implied_eps` 與 `required_eps` 的同一個理由（L12）。

### ③ Phase 4b「每一格配 disproof」——建議：**收窄到「有賭注的那幾格」**

| 五欄 | 內容 |
|---|---|
| **原 roadmap** | 「多年橋算得出倍率與它的前提鏈，且**每一格**配 disproof」 |
| **新觀察** | 實測：63/63 檔都有反證、63/63 的 L7 三件套齊全、**60 檔（95%）的散文已經逐字指名了它會推翻哪個 driver**。缺的只是一個程式讀得到的欄位，而那個欄位 2026-09-20 已經加好（`DisproofCondition.invalidates`）。**[638] 一批就會讓第一檔通過** |
| **proposed change** | 驗收行改成「**有賭注的檔，其賭注所依賴的 driver 有反證在盯**」——不是「每一格」 |
| **why** | 大目標是「出場只認反證」，那要求的是**我們下注的那幾格**有反證，不是圖上每一格。對一個沒下注的 driver 要求反證，是在替一個不存在的部位買保險 |
| **impact** | 不鬆動 L7 三件套（仍然缺一即拒收）。不改 `invalidates` 的封閉字彙強制 |

### 4b 為什麼不等 LITE（2026-09-21 結案理由）

| 五欄 | 內容 |
|---|---|
| **原 roadmap** | 4b 的現況欄寫「3 檔有賭注、0 檔連得上反證…另兩檔是 AXTI／LITE」，讀起來像要三檔都過才算完 |
| **新觀察** | 2026-09-21 實測 `python scripts/multi_year_check.py`：input 16／accepted 2／filtered 14，**filtered 的 14 檔理由 100% 是 `no_ladder`，`no_disproof_link` 是 0**。LITE 的確切 reason 是 `no_horizon`——「判斷檔沒有 `multiple_horizon`，還沒有人寫下這個 thesis 主張的倍率在哪一年實現」 |
| **decision** | **4b 結案 ✅，不等 LITE。** LITE 的缺口是「沒寫下倍率射程」，而那正是 **Phase 7 的驗收行**（「寫下倍率射程的檔，首屏的『賭對了值多少』由多年視角回答」）逐字在講的東西 |
| **why** | 4b 量的是「有反證在盯」。**凡是算得出倍率階梯的檔，現在 100% 連得上反證**——4b 自己的判準已經滿足。若要等 LITE，4b 的完成就取決於一個屬於 Phase 7 的缺口，那正是 2026-09-20 使用者原話要避免的：「不要被我們最一開始設定的細節卡死，以大目標為主」 |
| **impact** | 不鬆動 L7 三件套、不改 `invalidates` 的封閉字彙強制、不改 4b 的驗收行本身。LITE 仍然會在 Phase 7 下被追——它沒有從任何清單上消失，只是換了正確的那張清單 |

---

> ⚠ **真正還缺的開發項**見下方〈[還沒做的開發項](#還沒做的開發項)〉——那張表是唯一一份，**不要在別處再列一次**（2026-09-20 整理時我自己一度列了兩份，正是 L12 的形狀：同一件事兩個地方，兩邊都會開始腐壞）。

## ✅ Phase 排序 amendment（2026-09-19 提出，**同日使用者核准並生效**）

使用者原話：「**採納 做到有需要我同意事項為止 不然就繼續直接做完**」。
Phase 表已照此更新：**Phase 4 拆成 4a／4b、Phase 7 提前到 4a 之後**。
以下五欄保留為決定紀錄。

| 欄 | 內容 |
|---|---|
| **原 roadmap** | Phase 4（篩選）＝D11 六條機械條件＋籃子首選換成這組條件；Phase 7（多年反向橋）**排最後**，理由逐字是「最大的契約變更，**前六個 Phase 不依賴它**」 |
| **新觀察** | ①D11 兩條門檻落地後實測：通過的 5 檔有 **4 檔「儀器算不出 payoff」（80%）**，被擋下的 11 檔只有 1 檔（9%）。②L11-6 逐筆重讀那 4 筆 Abstention：**四筆全部該 abstain**，且**三筆的 `revisit_when` 逐字指名「估值層新增 mid-cycle／multi-year／虧損期 method」**。③全 ledger **11 檔**宣告不主張目標倍數，理由同型；AAOI 那筆逐字寫著「**那是開發項，載體是 ROADMAP 不是本 ledger**」。④**Phase 4 的六條裡只有一條依賴估值儀器**——「payoff 為正」；其餘五條（覆蓋家數、市值、瓶頸業務占營收、外部印證的瓶頸邊、30 天漲幅、催化劑）**與估值無關** |
| **proposed change** | **(1) Phase 4 拆成 4a／4b。** 4a＝五條不依賴儀器的機械條件，接進 `webapp/basket.py` 的 filter，**照原序做**；4b＝「payoff 為正」那一條，**移到 Phase 7 之後**。**(2) Phase 7（多年反向橋）由「最後做」提前到 4a 之後。** |
| **why** | 「前六個 Phase 不依賴它」這句話在 D11 落地後**不再成立**——Phase 4 的首選判定依賴它，而它對目標區沒有鑑別力（80% 算不出）。不提前的話，Phase 4 做完得到的是一個**必然空的籃子**，而空的原因是**儀器不適用**，不是篩選條件正確運作。而需求規格研究層已經寫好了（11 筆 Abstention 的 `revisit_when`） |
| **impact** | 4a 的驗收不變（filter 報 input／accepted／filtered／reasons，INV-3）。**4b 的驗收要重寫**：從「payoff 為正」變成「多年橋算得出倍率與它的前提鏈，且每一格配 disproof」。⚠ **兩個要誠實講的代價**：①Phase 7 是最大的契約變更，提前會讓 Phase 4 完成得更晚；②**反向橋不會讓籃子非空**——它把「為什麼空」換成「這幾檔各自要什麼為真、哪一格最先會破」。不影響 Phase 1／2／5／6 |

**⚠ 明確排除的第三條路：** 「把『payoff 為正』從首選條件裡拿掉」**不是選項**——
那會讓籃子立刻變非空，正是 `AGENTS.md` 明文禁止的「為了讓籃子非空而放寬篩選條件」。

**~~不採納也是一個合法答案~~**（2026-09-19 使用者採納，此路未走）。

### ⚠ 核准當天補上的一處更正（它改變了優先序的理由，但沒改變結論）

提案時寫「11 筆 Abstention 各自獨立寫下、卻指向同一件事」——**那不精確，它們指向兩件事**：

| 要的是什麼 | 哪幾檔 | 它解決的問題 |
|---|---|---|
| **虧損期估值法**（營收倍數取代盈餘倍數） | IQE.L／POET／AAOI／CRWV／3363.TWO | 「這家**現在**虧錢的公司**今天**值多少」 |
| **多年期預測／mid-cycle** | 6324.T／SOI.PA | 「**幾年後**的樣子值多少」 |
| 靠 rollover 自己解 | MP（FY2027 共識已轉正 0.89562） | — |

⚠ **這個區別會影響排序，而且方向與直覺相反：** 虧損期估值法**看起來能解更多筆**（5 檔 vs 2 檔），
但它**仍然是一年期的錯價儀器**——只是把分母從盈餘換成營收，回答的還是「今天被低估幾 %」。
**照「解得多」排優先序會選到對不上目標的那一個。**
更糟的是：先做它，籃子會因為「虧損公司終於算得出 payoff」而變非空——
**那是用一把對不上目標的尺把籃子填滿，比空籃子危險得多。**

---

## Phase 表外的交付：結構讀圖（2026-09-17 Q4＋Q5，使用者核准 A）

**它不屬於某一個 Phase，因為它是 Phase 1（讓邊緣公司看得見）與 Phase 4（篩選）之間缺的那塊中間物：**
圖給一堆單邊事實，賭注要一個結構判斷。設計與決定見
[`brainstorms/2026-09-17-structural-reading-layer.md`](brainstorms/2026-09-17-structural-reading-layer.md)。

| | 交付 | 驗收（哪個數字會變） |
|---|---|---|
| **Q4** ✅ | `python -m query.structure <node>`：五個角度一次查出，零 LLM、零判斷、不寫 authority | 手打十幾條查詢 → 一條命令。一跑就冒出具體缺口：`mat:inp_substrate` 有 15 條需求側邊、圖說它 sub=5 最卡，但**供給側 3 條全部沒填 sub** |
| **Q5** ✅ | append-only 讀圖 ledger（`alpha/structure_reading/`）＋ staleness 分級 ＋ 心跳第 2 段 ＋ pq1 段 `stale_structure_readings` ＋ `webapp materialize --structure-readings` | 心跳第 2 段從沒有這一行 → 有「結構讀圖 N 份／該重讀 M」；佇列段 12 → **13**（查證：`python -c "from engine_b import queue_segments as q;print(len(q.SEGMENTS))"`）；state kind 6 → **7**（查證：`python -m webapp status`）。**2026-09-17 實測：ledger 0 筆，心跳印「一份都還沒寫」**——那是誠實的起點，不是壞掉。⚠ API 端點已開（`/api/v1/structure-readings`），**前端頁面刻意未做**：心跳那一行已足夠，等 ledger 有幾十筆再看要不要給它一頁 |

⚠ **刻意還沒做的兩件**（都不是遺漏）：
① **A/B 判準表不機械化**——先產出幾十份、看它講得準不準再談（INV-5：先量測後放閘）；
② **不自動重新推理**——重讀是研究，只在互動 session（D12）。分級本身是零 LLM 的，所以這不花 token。

⚠ **它維護的是「讀圖跟圖還一不一致」，不是「讀圖對不對」。** 後者要靠 outcome 量測（Phase 3／5）。

## 每個 Phase 的 completion gate（八項，缺一不得宣稱完成）

出自 [`historical-failure-matrix.md`](refactor/historical-failure-matrix.md) §9。
**不得僅以「tests pass／CLI works／architecture looks cleaner」判定完成。**

1. Historical regression suite pass（golden fixtures）
2. Runtime invariant audit pass（`audit invariants`）
3. No unexplained semantic diff（old/new dual run）
4. **No new dual authority**
5. No silent-drop path（每個 filter 都能報 input／accepted／filtered／reasons）
6. Point-in-time tests pass
7. All migrated lifecycle objects reachable
8. **該 phase 負責的 critical historical failure 已有 executable protection**

> ~~現況：36 筆歷史事故中，**🔴 僅有文字保護的有 10 筆**。~~（2026-09-17 Step 1.3 重量：
> **36 筆中 ✅ 21／🟡 8／🔴 7**——`historical-failure-matrix.md` §4 的「17／9／10」與本句都是已腐壞的快照，
> §1 的逐列狀態才是現值。查證：`python -c "import re,collections;ls=open('docs/refactor/historical-failure-matrix.md',encoding='utf-8').read().split(chr(10));c=collections.Counter(next((m for m in ('✅','🟡','🔴') if m in l.rstrip('|').rsplit('|',1)[-1]),'?') for l in ls if re.match(r'^\| \*\*F-[0-9/]+\*\* \|',l));print(dict(c))"`）
> 各 Phase 的責任分配見該檔 §9。
> ⚠ **2026-09-20 已重驗第 8 項**：🔴 由 7 筆歸零，真正還缺 executable protection 的剩三筆（其中一筆本質上防不了）。
> ⚠ **§9 的「各 Phase 🔴 責任分配」表用的是舊 refactor 的 Phase 編號**（contracts／Portfolio-Risk／
> vertical slice／Engine D 分解…），**與本檔 Alpha Edge 的 Phase 0–7 沒有對應關係**。
> 第 8 項要對照的是「本 Phase 實際動到哪些事故的形狀」，不是編號對編號。

> **Phase 1／3／4b／5／6 的逐項核對記錄**（每項的查證命令與當時實測值）逐字封存在
> [`archive/roadmap-completion-gate-log.md`](archive/roadmap-completion-gate-log.md)。
> ⚠ 那些數字是**當時**的實測值，不隨現況更新——要現值請跑查證命令。

## 硬約束（轉向不放寬任何一條）

1. **不重建 Neo4j。** 資產是 EdgeAssertion 的 provenance，不是節點數。
2. **Decision Store schema 不動。** append-only 紀錄 Git 救不回（L10）。
3. **四個人工 gate 不放寬**（graph admission／Engine C 判讀寫入／thesis mutation／live）；**L8 不放寬**。
4. **`rank_bottlenecks()` 仍是唯一排序權威**；篩選層只在它的順序上過濾，不重算、不加權。
5. **系統仍然不給 alpha 部位尺寸、不下單、不連 broker**（`AGENTS.md` Alpha 呈現契約）。
6. **beta 訊號不得以任何名義復刻**（2026-08-01 實測 0 勝 3 敗）；**beta 開發凍結（D6）**，只保留大盤比例觀測。
7. **不因籃子空就放寬篩選條件**——讓它非空的路是研究。
8. **last30days 不串進無人值守管線**（本機未接 X、輸出沒有 provenance 契約，只做一次性探勘）。
9. **既有測試檔全部保留**——可改 import 路徑，不可刪斷言。
10. **改任何 `python -m <module>` 命令字串前，先走 sandbox impact review 五步**——`.codex/rules` 的 exact prefix 會靜默打斷 daily。
11. **六條 hard invariant 全程適用**（`historical-failure-matrix.md` §2）。
12. **Local-first；Core 不得 import `mcp_server`。**
13. **alpha 原則上不用貸款資金是使用者自己的紀律，系統不建 gate（D14）；Sheet 是部位真相，Decision Store 只留可選 receipt。**
14. **`AGENTS.md` 不是憲法**——不可變的是五條 authority separation；**lesson 一條都不刪**。

## 凍結與明確不做

- **beta 開發凍結**（D6）：beta 個股呈現若擋路可拆，不為維持 beta 架構繞路。
- **明確不排程（理由已量測，勿重開）：** 舊表整份在 archive「明確不排程」節——peer valuation／`peer_groups.json`、
  等待機制三套併入 Event Watch、待辦池 evidence conflict 類型、ETF 完整 look-through 管線、Confidence 五軸重構、
  技術指標擴充、貸款 glide path、parked lead embedding 召回、`coverage_gaps` 走 `DEPENDS_ON`。
  **轉向不重開這些**：否決的理由是量測結果，不隨目標改變。
- pq2 **[577]**（COHR sole_source 核實）、**[578]**（COHR 賭注改寫）擱置（D9）。
- 決定紀錄 §9：不給部位尺寸、不下單、不連 broker、不動四個人工 gate、不放寬 L8、不在 Step 0 動任何程式。

## 研究主題範圍

- **以 AI capex 為起點找邊邊，同時開始找下一個大題材（D4）**；選題由使用者，機制是 `system-decompose`。
- 2026-09-09 定案照舊：新需求錨的 decompose 提案由系統自動鑄成 pq2（manual 型），核准後與既有主題同級；
  同時 open 的提案最多兩個；drop 過的系統除非新 lead 再點名否則不重生。
- **HBM 不變：SK Hynix／Samsung 不主動 onboarding**（使用者對擁擠度的判斷）；humanoid 的可投資機會在零組件供應商不在整機。
  完整歷史（2026-08-20 定案與 2026-09-09 修正）見 archive「研究主題範圍」。

## 還沒做的開發項

> ⚠ **這張表只放「真的還沒做、而且值得占路線圖」的。** 三類東西刻意不放這裡：
> **維持營運**（排程時間、錯誤訊息、重複鑄號——該修就修，不占 Phase）、
> **已有結論**（「記下來是為了別再有人去建它」那一類）、
> **已完成但文件沒更新的**。41 列原文逐字封存在
> [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md)。
>
> ⚠⚠ **這張表本身需要重驗，而旁邊那份已經驗完了。**
> **歷史事故矩陣的重驗（總檢驗第一步）已於 2026-09-20 做完**——7 筆 🔴 裡 **6 筆早就解了**，
> 🔴 歸零、真正還缺保護的只剩三筆。逐筆實測見
> [`refactor/historical-failure-matrix.md`](refactor/historical-failure-matrix.md) 開頭那一節。
> **下面這張表（backlog）還沒做同樣的重驗**，而已知至少一筆腐壞：
> `is_component_of` 的第二種語意早就由 [613] 解決（`is_variant_of` 已進封閉字彙）。
> **拿一份腐壞的清單去驗收，會把已解的當待辦、也可能把真紅的漏掉。**

| 缺什麼 | 為什麼重要 | 大小 | 驗過了嗎 |
|---|---|---|---|
| **會不會倒閉那盞燈點不亮** | 四盞歸零旗標只有兩盞在跑（現金跑道 67/73、負債 70/73；**稀釋與 going concern 都是 0/73**）。`AGENTS.md` D2 直接要求四盞 | Z2（動 Engine C 欄位字彙） | ✅ **2026-09-20 實測確認仍缺** |
| **反證沒有人在定期核對** | 圖裡 409 條 claim 都帶反證條件，但沒有東西拿它比對新證據——L7 說的「永遠不會響的火警」 | Z2 | ❌ 未重驗 |
| **逐字證據到不了決策**（V4） | V1–V3 已交付；剩下這一半是「每個下游只能相信 label，而 label 的 base rate 是 35% 錯」 | Z3，已有 zoom-out 文件 | ❌ 未重驗 |
| 讀圖印得出「這條邊的逐字」，印不出「這一格的逐字」 | 深挖需要繞過自己的工具，就不會例行發生（L18-4） | Z2（動讀路徑契約） | ❌ 未重驗 |
| 「刻意不併」沒有登記處 | 重複節點候選清單只會因為真的合併而變短，判斷過「不該併」的沒有地方記 | Z2，有使用者要選的問題 | ❌ 未重驗 |
| 封閉字彙被兩個問題共用（`counter_path_relation`） | 結構讀圖的「反向路徑」裡混進了結構上不該算的邊 | Z2 | ❌ 未重驗 |
| 核查條件對照不到期中實績 | 只從年度實績攤平，半年／季報的數字對不進去 | Z2 | ❌ 未重驗 |
| 同一期間有兩筆生效觀測 | 5 個欄位 14 組；2026-09-20 只修了基期那一個，另 4 個的根因是 schema 的單值限制 | 🔶 部分接 | ✅ 已修 1/5 |
| 工單把「需求側節點」與「供給側候選」當成同一種東西 | 正是篩選層要分的 | Phase 4 | ❌ 未重驗 |
| **屬性值「沒有人不同意」就直接生效（`auto` 路徑沒有閘門）** | `substitutability` 只有在**兩筆 assertion 互相衝突**時才進人工閘門；單一候選值走 `auto` 直接投影成 canonical，而它是 `rank_bottlenecks()` 排序鍵的第二位。2026-09-21 實測：136 筆帶 `substitutability` 的 assertion 裡，**103 筆掛著的逐字不含任何可替代性語言**（關鍵字刻意放寬到連 `capacity`／`compete`／`產能` 都算命中）；其中 sub≥4 去重後 47 條邊，**37 條是 `auto`**（含 7 條 sub=5，`tech:cpo depends_on tech:external_laser_source` 在內），**經過裁決的那 8 條反而都留下了 rationale 並下修 confidence**。⚠ 閘門量的是「有沒有人不同意」，不是「有沒有證據」——這是 L14-4 的第四種失效：**它不是恆亮也不是牆，它是在只有一個聲音的地方根本不存在**。⚠ 誠實的限制：逐字是 ~200 字節錄（170 段裡 75 段 ≥190 字），「不在 quote 裡」≠「不在文件裡」，所以這是**可稽核性**缺口而不是「37 條都錯」 | Z2（動投影契約） | ✅ **2026-09-21 實測** |


## 開工前必讀

### 已撤回的診斷

> **這一節不是自責，是一份檢查清單。** 每一筆都是「已經寫進 commit／ROADMAP／程式註解，
> 事後被推翻」的技術診斷——不是待辦、不是 bug，是**曾經看起來完全正確的錯誤結論**。
>
> **共同形狀：錯誤有方向性——全都朝「產生一個有洞察力的結論」偏**，而且每一個都能用專案
> 自己的 lesson 語言包裝（L12 一表兩義、L15 gate 攔錯東西）。
> **模式匹配是提出假說，不是確認假說。** 一個現象能被套進某條 L，只代表它值得查。
>
> **用法：** 宣稱「找到根因了」之前，先跑一條**試圖讓自己的結論變成假的**命令
> （不是驗證它為真——那是確認偏誤）。專案對每個 thesis 都強制 `disproof_condition`，
> 這一節是把同一個要求套到自己的技術診斷上。

| 日期 | 被推翻的診斷 | 一條就能否證它的命令 |
|---|---|---|
| 2026-08-19 | COHR「Engine C 的 `bar_date` 是憑空生成的、`price` 對不上任何收盤」 | `date(2026,8,17).strftime('%A')` → `Monday`。**一本日曆就能否證** |
| 2026-08-19 | 待辦池 `decision_review` 不退場是因為「空 `blockers` 被判成非純系統」 | `python -m decision_lab card <decision_id>` → `card.blockers` 有 **7 個碼**，不是空的 |
| 2026-08-19 | 「`execution_fx_stale_since_decision` 未登記，掉進泛用 prefix」 | 讀 `config/decision_blockers.json` 的 `_matching`（**最長**匹配，不是第一個）。真相是它早就以 exact prefix 登記 |
| 2026-08-19 | 「`live_choices` 仍為 0 筆，live 路徑從未被走過」——**直接引用自家文件** | `select count(*) from live_choices` → **1** |
| 2026-08-19 | 「`commercial_maturity` 積壓缺的是有人去讀年報附註」 | 逐一看 7 個積壓的 `missing_data` → 6 個是 `research_assessment_missing`。**靠讀年報能下降的是 0 個** |
| 2026-08-28 | 「COHR live reassess 失敗的根因是 `--as-of` 沒給」 | 修好 marker 後**不給 as-of 再跑一次** → marker 沒出現。真因在 `adapters.py::current_holdings` 另一處吞例外 |
| 2026-08-28 | 「`co:lumentum` 有兩個 cohort，重複偵測有漏」 | `sed -n '869,876p' decision_lab/store.py` → 註解逐字記著已檢查過這個確切案例。回空集合是正確行為 |
| 2026-08-28 | 「U2 把 `weakest_axis` 改成 level 排序是**零行為變化**的純重構」 | 改完直接 `pytest tests/test_probe_sizing.py` → `[missing_ref]` 立刻紅 |

**有可執行檢查的診斷活不過幾分鐘；沒有的全靠當下願不願意多查一步。**
（實測：U2「零行為變化」被測試抓到用了 3 分鐘；靠運氣發現的兩筆活到下一輪。）
所以落地前不是把診斷寫得更清楚，是**把診斷寫成一條會紅的檢查再落地**。

⚠ **這一節自己的 disproof：** 若之後仍發生「診斷已落地才被推翻」，代表它沒生效。
屆時該做的是把否證步驟綁進會自己執行的東西（測試、hook、commit 前檢查），
**不是把這張表寫得更長**。


### 看起來像缺口但不是——請勿「修正」

- **人工 runway 觀測寫入後 `financial_runway_manual_required` 仍亮，多半是 100 天鮮度窗，
  不要去改窗。** 那個窗刻意對齊財報節奏，**正解是用最新一季財報刷新觀測**。
  ⚠ runway 觀測的 `as_of` 應填**資產負債表日**，不是申報日。
- **5 個 cohort 的最新 `expiry` 仍是 `+72h` 預設值，不要去清。** 它們的 lifecycle 全部已
  `expired` 且 `catalyst_watch` 根本不顯示它們；依 L14，修它們會讓 **0 筆**下游資料變化。
  根因已由 `300b8e0` 修復並有測試防迴歸。
- **Beta 例行成交不進 Engine D 的 `record-fill`，這是設計正確。** `record_live_fill` 要求
  一整條責任鏈（decision → choice → fill），目的是回答「Engine D 的建議準不準」。
  beta 例行投入沒有 decision、沒有接受動作——**它是時間表不是決策**。硬塞會讓
  outcome attribution 變成把 QQQ 漲跌歸因給「今天是 15 號」。
  正確分工：beta → `library/trades/trade_log.jsonl`；alpha thesis 驅動 → 同時進 trade_log 與 Engine D fill。
- **`_bar_identity()` 的 ETL 不得加「info 與 history 不一致就 quarantine」的交叉驗證。**
  它會把完全正確的資料 quarantine 掉，正是 L15 說的「gate 攔下的不是它想攔的東西」。


---

## 想法怎麼變成程式

```
ROADMAP「開放 backlog」  →  docs/brainstorms/  →  docs/plans/  →  實作
     （還沒決定要做）        （需求與盲點審查）     （規格與驗收）
```

四階不是每次都要走完。判準是**改錯的成本**：小工作直接做；需要先想清楚需求與反面的走
brainstorm；範圍大到需要驗收條件才開 plan。`docs/plans/` 已轉純歷史
（見 [`plans/README.md`](plans/README.md)）。


## 什麼值得開發 / 什麼交給 Claude

**值得開發：** 知識累積（更多公司 onboarding、更多高品質文件——這是**研究方向**非開發項，
已由 `research-drain` 的閉包語意涵蓋）｜Skill 介面｜高槓桿 fetcher｜資料品質檢查。

**不值得自己開發：** 長文解讀｜Text2Cypher｜自動選文件頁面｜節點重要性評分｜公司識別
（Claude 做得更好）｜**自動代替使用者做最終投資決定或送單**（Engine D 可提出有邊界的建議，
但 live 接受、覆寫與 broker 下單永遠需要人工）。

