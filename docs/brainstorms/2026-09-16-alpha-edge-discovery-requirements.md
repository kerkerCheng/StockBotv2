# Alpha 轉向：邊緣小公司的 power-law 漏斗（決定紀錄，2026-09-16）

> 使用者原話（2026-09-15～16）：「我們要往 AXTI 或像台股之前上銓或其他光通的邊邊走，搭配光通現在的
> 集中度，這樣才有機會被放量，這確實才是我最初想像的目標，現在確實花太多力氣在 beta 上。」
> 「10 倍當然只是目標，2、3、5 倍我都很 OK，但主要是想表達是這種等級的倍率，而不是 beta 波動。」
> 「alpha 部位結構不變就一直抱。」
>
> **本檔是這次轉向的決定紀錄（SSOT），在 AGENTS／ROADMAP 整併完成之前，新 session 以本檔為準。**
> 它記的是**決定與驗收條件**，不是解法；解法由 development-flow 的 PLAN_PROPOSAL 產出。

## 1. 問題（2026-09-15 blind-spot-audit 的三個 🔴，數字為當時實測）

1. **儀器對不上目標。** 現行主流程是 FY+1 EPS × 目標倍數找 20% 錯價，適合高覆蓋大型股；使用者要的是
   邊緣小公司的 2 到 10 倍。COHR 首屏「賭對了值 244、現價 266」是這個錯位的直接產物：thesis 講 FY28
   產能倍增後的量與利潤率，模型只有 FY27 一格。
2. **想去的地方排序看不到。** 上詮、聯亞、華星光、全新、IET-KY、Sivers、Aehr 在圖裡都有邊、也接得到需求錨，
   但 `rank_bottlenecks` 把未填 substitutability 的邊當 0 過濾（門檻 4），可投資排序 37 列一檔都沒有。
   整張圖 substitutability 覆蓋 15%，填了的全是大公司。
3. **研究火力與資本落點錯位。** alpha 格實際 1.6%（目標 10%）；22 檔追蹤等權 −3.0% vs QQQ；12/22 在漲完
   之後才入圖（入圖前 30 天中位 +0.8%、之後 −3.5%）。單一帳號 aleabitoreddit 兩個月 492 則：65% no-go、
   31% parked、4.5% 進圖。

## 2. 使用者定案（D0–D15）

| # | 決定 | 備註 |
|---|---|---|
| **D0** | **文件整併是 Step 0。** AGENTS 的憲法（五條 authority separation、六條 invariant、四個人工 gate）、L1–L17、協作邊界**一字不動**；呈現契約整章重寫；被取代的句子**劃線加日期留在原地**或搬 archive 並留指向，不得靜默刪除；ROADMAP 照 2026-09-03 先例整份搬 `docs/archive/`。 | 驗收見 §5 |
| D1 | alpha 格改 `observed_only`；beta 五格目標保留（沒有目標時「誰跌深投誰」就回來，那是 2026-08-01 實測輸 22% 的機制）。 | `config/target_allocation.json` |
| D2 | 部位尺寸由使用者決定。系統只給三件：**判斷錯了值多少**（反證觸發後的假設套同一條橋，與賭注 variant overlay 對稱）、**歸零旗標**（現金跑道／負債／稀釋／going concern，紅黃綠不給數字）、**alpha 全歸零淨值少幾 %**。 | 改契約：現行「bear 是散文不是下檔數字」→ 改為對稱 overlay |
| D3 | 出場只認反證；目標價到了**只提醒**，`realized` 降為提醒不觸發出場。 | thesis lifecycle |
| D4 | 以 AI capex 為起點找邊邊，同時開始找下一個大題材；選題由使用者，機制是 system-decompose。 | |
| D5 | X 來源：手動轉發與 API 抓並行。**帳號登記表**（封閉清單，tier：probation／measured／trusted）＋**每則貼文自動蓋章**（貼文時間＋當日收盤價＋具名實體）＋**每週計分表五欄**（點名後 30／90 天對 QQQ 與 SOXX 超額報酬中位數、點名前 30 天漲幅、追源成功率、假設命中率、no-go 率）＋**計分表 materialize 進 APP**。tier 升降是一季一次的 pq2 manual。新帳號一律 probation，只影響 pq1 優先序不影響入池。 | 推文永遠是 tier-4 lead（lead-intake 不變） |
| D6 | beta 凍結開發；只保留「大盤比例」觀測；beta 個股呈現若擋路可拆，不為維持 beta 架構繞路。 | |
| D7 | 初始三檔各測一條 filing 管道：**SIVE.ST**（瑞典 MFN）、**3081.TWO 聯亞**（MOPS）、**IQE.L**（英國 RNS）。 | IQE 帶 going-concern 待辦，先測歸零旗標 |
| D8 | 第一個研究工作：把已在圖裡的邊緣公司補齊**可替代性、外部印證、瓶頸業務占營收比例**三格，讓它們浮上排序。 | 研究項走 pq2 |
| D9 | pq2 [577]（COHR sole_source 核實）、[578]（COHR 賭注改寫）擱置。 | |
| D10 | 流程：本檔 → 新 session 走 development-flow **Z3** 出 PLAN_PROPOSAL → **停下等核准** → 實作。Step 0 產出是 diff。 | |
| D11 | 候選門檻改為**覆蓋厚薄**（`analyst_count`、市值），不限上市地；非英語 filing 是加分不是門檻。 | AXTI、AEHR、POET 與台股同一把尺 |
| D12 | Daily 拆三層：**心跳**（零 LLM，Python 排程）＋**分類**（便宜模型、每日硬上限、失敗不阻斷、印「未 triage N」）＋**研究**（只在互動 session 手動 research-drain；daily 的 `drain_limit_per_run` 歸零）。weekly 同一套，帳號計分表在 weekly 算。 | 心跳規格見 §4 |
| D13 | Skill 不在 Step 0 重整，隨各 Step 同 change 更新。例外（Step 0 一起做）：daily-brief／alpha-status 頂端加 scope note「呈現契約重寫中，衝突時以 AGENTS 為準」；blind-spot-audit 加 lens「瓶頸壽命／擁擠度／週期位置」。改完跑 `scripts/sync_agent_skills.py`。 | |
| D14 | 資本與部位：alpha **原則上不用貸款資金**，這是使用者自己的紀律，系統不建 gate；Google Sheet 記貸款額度、投入標的與現金，**Sheet 是部位真相**，Decision Store 只留可選 receipt；下單由使用者透過 session 記進 Sheet。 | A5 不擴張 |
| D15 | lead 到期：parked 超過 **60 天**未動自動標 expired 並計數（不刪）；台股**每月營收**納入 Engine C 一手 datum，並補 MOPS 重訊 watcher；追蹤表統計換成 **12／24 個月內達 2 倍的比例、最大單檔貢獻、籃子總報酬**（等權中位數保留但降為次要）。 | INV-2 |

## 3. 四層漏斗（架構骨架，解法留給 plan）

| 層 | 要回答的問題 | 已有 | 缺 |
|---|---|---|---|
| 發現 | 誰值得進佇列 | `crons/harvest_leads.py`（X／RSS／EDGAR，零 LLM）、lead-intake、source-trace、圖的傳播、MOPS／MFN／RNS fetcher | 帳號登記表與計分表、來源標籤跟著 lead 走到 outcome、傳播到小公司（「誰供應這個供應商」）、MOPS 重訊與月營收 watcher |
| 篩選 | 它是不是倍率候選 | `rank_bottlenecks`、L8、五項核驗清單、`analyst_count` 快照 | 機械條件（覆蓋家數上限、市值上限、瓶頸業務占營收下限、至少一條外部印證的瓶頸邊、入圖前 30 天漲幅上限、12 個月內指名假設的催化劑）；INV-3 逐檔報 input／accepted／filtered／reasons |
| 表達 | 怎麼買、怎麼抱、怎麼砍 | thesis lifecycle、反證三件套、5% 單筆硬擋、`alpha/reverse` 反向橋 | 多年反向橋（「五倍要什麼為真」）取代 FY+1 EPS；賭注與判斷錯的對稱 overlay；歸零旗標；entry criterion 降為 optional 中的 optional |
| 量測 | 哪個管道與特徵產出贏家 | 22 檔追蹤表、chasing 計數、`hypotheses.py`、`lead_trace_status` 封閉字彙 | 來源歸因欄、帳號計分表、power-law 統計量、回溯評分 |

**篩選是 filter 不是分數**（沿用 2026-09-15 D2）。籃子頁「首選」的三個條件換成漏斗條件；沒有一檔通過就沒有首選。

## 4. 心跳規格（D12）

固定五段，每段可以只有一行；由 Python 從 state 檔組出，推到既有 Discord publisher：

1. **資料新鮮**：每個 harvest 來源 ok／fail、行情最新交易日、APP 今天是否 materialize。
2. **變了什麼**：門檻跨越、反證觸發、催化劑到期、現價過目標價（提醒不是動作）。
3. **佇列**：新 lead N、待 triage N、pq1 可做 N、pq2 卡在你 N、expired N。
4. **部位**：alpha 占淨值、全歸零少幾 %、追蹤表三個 power-law 統計量、幾檔共用同一需求錨。
5. **帳號計分表變動**（weekly）：量測起始日與樣本數必印，讓「還沒量」看得見。

硬規則：LLM 失敗心跳照發；「未 triage N」必印（L13：沒發生與沒看到不得同形）；writer lock 照留（harvest 仍寫共用檔）；
不需要 agent 當 orchestrator 時，Codex sandbox 的 fixed entry 與 `test_codex_daily_permissions.py` 要同 change 對齊。

## 5. Step 0（文件整併）的驗收（L14：哪個數字會變）

- ~~`AGENTS.md` 字元數 **< 現在的一半**（2026-09-16 實測 69,671）。~~
  **2026-09-16 使用者定案（Step 0 收尾，選 A）改為：字元數必須降，且內容驗收全過**（憲法／六條 invariant／
  四個 gate／L1–L17／協作邊界一字不動；每句被移除的舊契約有去向）。理由：69,671 是 `wc -c` 的 bytes 不是字元
  （真字元 36,075），而一字不動的段落合計約 19,800 字元已超過一半，「減半」在 D0 之下結構上不可達。
  實測 36,075 → 34,624 字元；細節見 `docs/refactor/alpha-edge-step0-migration.md` §0。
- L1–L17 **17 條全部在**（grep `### L1 ` … `### L17 `）。
- `python -m audit invariants` **FAIL 0**。
- `tests/test_codex_daily_permissions.py` 與所有讀 prompt／skill 字串的測試**綠**。
- 每一句被移除的舊契約都答得出「去了哪裡」（劃線留原地、或 archive 路徑）。
- 產出是 **diff**，使用者看過才合併；動到判準句屬常規推進授權的例外 ④，必停。

## 6. 回溯評分（讓計分表不必等半年）

今天就能算的：
- **aleabitoreddit 492 則**已在 `library/leads/pending_leads.json`，帶 `published_at` 與 `entities`；
  配 yfinance 歷史價即可算「點名後 30／90 天對 QQQ／SOXX 超額」與「點名前 30 天漲幅」，零 X 成本。
- **全部 1,085 則 lead** 可按來源（x／edgar／mfn／yahoo）比較同一組統計，回答「哪個管道歷史上產出贏家」。
- **新帳號**：X API user-timeline 端點可取每帳號最近至多 3,200 則（pay-per-use 約 $0.005／則，
  一個帳號上限約 $16）——**但不抓滿，分三段停損**（2026-09-16 使用者要求，不海測）：
  ① 先用免費來源判斷值不值得花錢：Substack／RSS 全文帶日期免費、Reddit 公開 JSON 免費、X 用 Firefox cookie
  的搜尋只看最近 30 天免費；② 付費探針只抓最近 100～200 則原創貼文（約 $0.5～1），過「具體性、貼一手連結、
  有具名標的」三條才進第三段；③ 回填以 **stop rule** 收尾：抓到 **20 則具名點名、跨 ≥5 檔** 就停
  （這是計分表 probation→measured 的最低樣本，不是 3,200 則），排除 replies／retweets 後多數帳號落在
  100～400 則、$0.5～2。另設 `harvest_config` **每月 X 總花費上限**（建議 $10），超過即停並在心跳印出。
  帳號池靠既有好帳號的引用／回覆圖每月長 1～2 個，不需要海測。
- **算不回來的**：假設命中率（需 filing 裁決）、追源成功率（要重跑 trace，只能抽樣）。

回溯的三個已知偏差要印在計分表上：倖存者（帳號是因為對過才被選）、後見之明、以及 2026 年光互連單邊上漲
（所以必須同時對 SOXX 算超額，不只 QQQ）。

## 7. 初始候選池（全部 probation、信任為零；2026-09-16 網頁搜尋撈到）

X：@PhotonCap、@TheValueist、@demian_ai、@crux_capital_、@dnystedt。
Substack：G2AI／Global Semi Research、Yiazou、China Tech Bite、ELI5 DeFi、Gannon Capital。
台股：財報狗、鉅亨網、工商時報、豐雲學堂、vocus 作者。
下一步是看這些帳號引用誰、誰回覆他們，兩層即可。摸瓜用網頁搜尋＋`fetchers/x_api.py`；
last30days 本機未接 X（只有 Reddit／HN／GitHub），要用得先接 Firefox cookie 或 xAI 金鑰，且它的輸出沒有 provenance 契約，
只做一次性探勘，不串進管線。

## 8. 計畫自己的紅隊（三個最可能壞的地方，皆已有對策）

1. **發現層變餵食器**：lead 進得比手動研究快 → D15 到期計數 ＋ pq1 優先序把「補三格」排最前。
2. **計分表半年才有意義**：D5 印量測起始日與樣本數；§6 回溯評分先補一版。
3. **主題翻轉十檔一起 −50%**：使用者已接受單一主題集中；心跳只印回撤不給燈號；「結構不變就抱、出場只認反證」寫在 D3。

## 9. 明確不做

- 不給部位尺寸、不下單、不連 broker、不動四個人工 gate、不放寬 L8。
- 不因為籃子空就放寬篩選條件（讓它非空的路是研究）。
- 不在 Step 0 動任何程式。
- 不把 last30days 串進無人值守管線。
