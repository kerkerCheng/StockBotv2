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

## 四層漏斗：已有／缺（架構骨架；解法留給各 Phase 的 PLAN_PROPOSAL）

| 層 | 要回答的問題 | 已有 | 缺 |
|---|---|---|---|
| 發現 | 誰值得進佇列 | `crons/harvest_leads.py`（X／RSS／EDGAR，零 LLM）、lead-intake、source-trace、圖的傳播、MOPS／MFN／RNS fetcher | 帳號登記表與計分表、來源標籤跟著 lead 走到 outcome、傳播到小公司（「誰供應這個供應商」）、MOPS 重訊與月營收 watcher |
| 篩選 | 它是不是倍率候選 | `rank_bottlenecks`、L8、五項核驗清單、`analyst_count` 快照 | 機械條件（覆蓋家數上限、市值上限、瓶頸業務占營收下限、至少一條外部印證的瓶頸邊、入圖前 30 天漲幅上限、12 個月內指名假設的催化劑）；INV-3 逐檔報 input／accepted／filtered／reasons |
| 表達 | 怎麼買、怎麼抱、怎麼砍 | thesis lifecycle、反證三件套、5% 單筆硬擋、`alpha/reverse` 反向橋 | 多年反向橋（「五倍要什麼為真」）取代 FY+1 EPS；賭注與判斷錯的對稱 overlay；歸零旗標；entry criterion 降為 optional 中的 optional |
| 量測 | 哪個管道與特徵產出贏家 | 22 檔追蹤表、chasing 計數、`hypotheses.py`、`lead_trace_status` 封閉字彙 | 來源歸因欄、帳號計分表、power-law 統計量、回溯評分 |

**篩選是 filter 不是分數**（沿用 2026-09-15 D2）。籃子頁「首選」的三個條件換成漏斗條件；沒有一檔通過就沒有首選，
**不得為了讓籃子非空而放寬條件**——讓它非空的路是研究。

## Phase 表（每項四欄：做什麼／為什麼／驗收哪個數字會變／前置）

> 順序是決定紀錄的建議；Step 0 核准後才出 Step 1 的 PLAN_PROPOSAL，順序可在 plan 裡改，但要說明理由。
> 每個 Step 交回 HUMAN SUMMARY ＋ 八欄；~~Verdict 不是 GO 或有待決問題就停——本路線圖屬 **Z3** 且動到判準句，
> 是常規推進授權的例外 ④（[`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md) §5）。~~
> **2026-09-16 使用者定案（Phase 1 Step 1.0 交回後）：Verdict 為 GO 且沒有待使用者決定的問題時，直接合併 master 並接續下一個 Step，
> 不逐 Step 請核准。** 仍要停：Verdict 非 GO、有待決問題、動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句
> （後者仍須先給五欄 amendment）。四個人工 gate 不因此放寬：pq2 的圖寫入與 Engine C 判讀寫入仍逐筆核准。
> Phase 1 核准的計畫與工單見 [`brainstorms/2026-09-16-alpha-edge-phase1-plan.md`](brainstorms/2026-09-16-alpha-edge-phase1-plan.md)。
> 標記：▶ 進行中｜○ 未開工｜✅ 完成（回填實測 before → after）。研究項（pq2）不占本表，本表只追它的驗收數字。

| Phase | 漏斗層 | 做什麼 | 為什麼 | 驗收（哪個數字會變） | 前置 |
|---|---|---|---|---|---|
| **0** ✅ | — | **文件整併**（2026-09-16 交付並合併）：`AGENTS.md` 呈現契約整章重寫（憲法／六條 invariant／四個 gate／L1–L17／協作邊界**一字不動**）；舊 ROADMAP 整份 archive、換成本表；`ARCHITECTURE`／`OPERATIONS`／`CONCEPTS` 與新目標衝突的段落劃線加註不刪；daily-brief／alpha-status 頂端 scope note；blind-spot-audit 加「瓶頸壽命／擁擠度／週期位置」lens；跑 `scripts/sync_agent_skills.py` | 舊契約每個 session 完整載入，會把新 session 拉回舊目標（D0） | `AGENTS.md` 字元數必須降且內容驗收全過（使用者 2026-09-16 定案，取代「< 34,836／減半」，理由見 migration doc §0）：**36,075 → 34,624** ✅；`grep -c "^### L" AGENTS.md` = 17；`python -m audit invariants` FAIL 0；`python -m pytest tests/test_codex_daily_permissions.py` 綠；每句被移除的舊契約列得出去向 | — |
| **1** ▶ | 篩選（可見性） | **讓邊緣公司浮上排序。** (a) 研究項——已在圖裡的邊緣公司補齊**可替代性、外部印證、瓶頸業務占營收比例**三格（D8；研究走 pq2）；(b) 開發項——D7 初始三檔各測一條 filing 管道：**SIVE.ST**（瑞典 MFN）、**3081.TWO 聯亞**（MOPS）、**IQE.L**（英國 RNS，帶 going-concern 待辦，先測歸零旗標）。<br>**2026-09-16 PLAN 核准拆四個 Step：** **1.0** ✅ 公司名稱解析歸位——排序的證據分級改讀登記表真有的 `display_name`（原讀不存在的 `name`，100 家 0 家解析得到）、比對前去尾端括號註解與法律型態尾綴、補 23 家登記名稱（各自財報封面印的字串）；**1.1** ✅ `fetchers/mfn.py`＋`fetchers/rns.py`（與 `mops.py` 同構；互動式入口，不進無人值守）、`config/source_routes.json` 登記 `.ST`／`.L` 兩階、三條管道各 smoke 一份文件入圖（MOPS 抓聯亞 mtype=A ~~合併財報~~ **個別財報**——2026-09-17 實測聯亞無子公司、財報區合併財報 0 份；MFN 抓 Sivers Q2 2026 期中報告；RNS 抓 IQE FY2025 年度業績全文，含 going concern 附註）；三份 RA 已 prepare 為 pq2 [579][580][581]，~~入圖待使用者批次 go~~（2026-09-17 使用者批次 `go`，六筆全部 apply → push → `complete-ra` 結案）；**1.2** ✅ 研究項（pq2）——七家補三格：可替代性（addendum → `ra_admission`）、外部印證（客戶端／對手方文件；第三方媒體維持「待判定」，決策 C1）、瓶頸業務占營收比例（新增觀測欄位「產品線營收占比」，mechanical；決策 D2）。全新、IET-KY 沒有任何瓶頸邊，是**補邊**不是補格；Aehr 另補一條到需求錨的邊；華星光 sub=2 只重看、不得為進榜改判（**2026-09-17 實測未動，仍是 2**）；**1.3** ✅ 收尾回填（產出即本列驗收欄 ＋ 下方「Phase 1 completion gate 逐項核對」） | 想去的地方在排序裡看不見，不是資料不足，是格沒填**或邊沒有**；三條管道從沒有可重用的抓取器（既有入庫文件全是 session 手抓） | ~~可投資排序（`python -m query.bottleneck`）出現幾檔 TPEx／STO／L（2026-09-16 實測 0）；三條管道各有一份帶 `published_at` 的 SourceDoc 入庫~~（2026-09-16 PLAN 核准更正：L 當時已有 1 檔、三條管道當時已各有手抓的定日文件——照原句什麼都不做就達標，L14）。改為——**1.0** ✅ 證據分級改判 39 條邊（升 31／降 8）、待判定 90 → 53、解析不到的（邊，來源）131 → 83、IQE.L 由第 28 升第 12（雙方聯合）、排序仍 37 列、`python -m audit invariants` FAIL 0（查證：`python -m query.bottleneck --top-n 60`）；**1.1** 由抓取器產出、meta 帶 `published_at`、經 RA 入圖的文件 MOPS 2 → 3、MFN 0 → 1、RNS 0 → 1（2026-09-17：三份已由抓取器產出且 meta 帶 `published_at`＋`published_at_basis`——`mops_3081_separate_financial_statement_202602` 2026-08-12、`mfn_sivers_semiconductors_6543505f_att1` 2026-08-27、`rns_iqe_9588930` 2026-05-28；~~圖中計數在 [579][580][581] go 後才變~~ → **2026-09-17 入圖後實測達標：MOPS 2 → 3 ✅（`mops_3363_annual_report_2025` 2026-05-07／`mops_4979_annual_report_2025` 2026-05-31／`mops_3081_separate_financial_statement_202602` 2026-08-12）、MFN 0 → 1 ✅、RNS 0 → 1 ✅**，查證：`python -c "...MATCH (d:SourceDoc) WHERE d.id STARTS WITH 'mops_' OR d.id STARTS WITH 'mfn_' OR d.id STARTS WITH 'rns_' RETURN d.id"`）；`.ST`／`.L` 各多一階路由 ✅ 4 → 5 條、rung2 `mfn`／`rns` 皆 `verified=true`（查證：`python -m sourcing.routes SIVE.ST`）；IQE going concern 段落由「一手不支持」變可逐字引用 ✅（`library/raw/rns_iqe_9588930.txt` 附註 2.2 全段）；fixed entry 仍 20 條且 permission test 斷言 `fetchers\mfn.py`／`fetchers
ns.py` 不在 allowlist ✅；**1.2**（2026-09-17 全部現跑重量，不抄計畫檔）①~~可投資排序中 TW／TWO／ST 後綴檔數 0 → ≥1（目標 3）~~ **實測 0 → 0，未達**——但這是答案不是資料缺漏：七家的向下邊**全部走得到需求錨**，唯一卡點是 `substitutability` 低於門檻 4（逐檔 reasons 見下方「Phase 1 completion gate 逐項核對」第 5 項）；②`substitutability` 覆蓋 80 → **85／529（16%），未達 ≥86，差 1 條**；③八家「產品線營收占比」4 → ~~**7（AEHR 缺）**~~ → **8／8 ✅ 達標**（2026-09-17 [589] 補上 AEHR：FY2026 10-K『revenues by product category』表，Systems 57.34%／Contactors 29.77%／Services 12.89%，`mo_5a56be9daaef6ad94fd42bab4ee9093a`；**不需要 XBRL companyfacts，那張表本來就在 10-K 正文裡**。查證：`python -m engine_c.set_manual_field --list AEHR`）；④非驗收但實際發生的變化：IQE.L 由第 12 升 **第 9**（Tower 自家公告把該邊由雙方聯合升為外部印證）、公司→向下邊 218 → 222 條、外部印證 28 → 29／待判定 53 → 52／解析不到（邊，來源）83 → 82。查證：`python -m query.bottleneck --top-n 60`、`python -m loader.edge_resolution project --dry-run`、`python -m engine_c.set_manual_field --list <TICKER>`；**1.3** ✅ 收尾實測（2026-09-17）：`python -m audit invariants` **FAIL 0｜PASS 13｜檢查 4,087 筆**；全套 pytest **2,481 passed／1 skipped**；canonical 邊 **529**、materialized 屬性 **358**；`.ST`／`.L` 各 **5** 條路由、`mfn`／`rns` rung2 `verified=true`；`.codex/rules` fixed entry **20** 條；`python -m webapp status` 的 ranking artifact **current**（可行動 37／純結構 37）；待辦池無本 Phase 未決編號（[579]–[585] 全部結案）。**⚠ Phase 1 維持 ▶ 不標 ✅**——驗收行明訂「TW／TWO／ST 仍為 0 就不得標完成」，現況是**研究已做、證據不足以進榜**；缺哪份文件逐項列在下方 completion gate 第 5 項，**不得為了讓籃子非空而放寬門檻 4** | Phase 0 |
| **2** ▶ | 發現／量測 | **心跳＋分類（D12）**：純 Python 排程、固定五段、`config/daily_routine.json` 的 `drain_limit_per_run` 歸零、Codex fixed entry 與 `tests/test_codex_daily_permissions.py` 同一 change 對齊；weekly 同一套 | 研究火力被無人值守 drain 吃掉；心跳被 brief 淹沒；LLM 失敗時整份不發（沒發生與沒看到同形，L13） | 連續 3 天心跳**零 LLM** 成功發出，且每天印出「未 triage N」；`drain_limit_per_run` 由現值 → 0（查證命令見 OPERATIONS「Daily / pq1 / 待辦池的參數」）<br>**2026-09-17 進度（Step 2.1＋2.2 已交付，使用者選 A：獨立 Windows 排程）：** ①`drain_limit_per_run` **5 → 0 ✅**（查證：`python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`）；②`.codex/rules` fixed entry **20 → 15 ✅**（移除五條研究層專用 entry，純收緊；permission test 同 change 對齊，並由 Codex 自己的 execpolicy parser 證明那五條真的不再被允許）；③心跳排程 `StockBotv2-Heartbeat` 已註冊、每日 07:00、`Status=Ready`（查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`）；④以 `schtasks /Run` 走真正的排程路徑實跑一次：`Last Result: 0`、publisher 回 `sent` 2/2 段。<br>**❌ 尚未達標的那一條：「連續 3 天心跳零 LLM 成功發出」——手動觸發成功不算數**（L13-1：驗收條件是產出出現在下游消費者手上）。**最早 2026-09-20 才驗得完**，在那之前 Phase 2 不標完成。<br>⑤Step 2.3（分類層每日硬上限）未開工。計畫與 sandbox impact review 見 [`brainstorms/2026-09-17-alpha-edge-phase2-plan.md`](brainstorms/2026-09-17-alpha-edge-phase2-plan.md)。 | Phase 0；sandbox impact review 五步 |
| **3** ○ | 發現 | **D5 帳號登記表（封閉清單，tier `probation`／`measured`／`trusted`）、每則貼文蓋章、每週計分表五欄、計分表 materialize 進 APP**；決定紀錄 §6 的回溯評分先用 492 則既有資料跑一版（三段停損；`harvest_config` 加每月 X 總花費上限，超過即停並在心跳印出） | 單一帳號兩個月 492 則只有 4.5% 進圖；沒有量測就不能有第二個帳號；計分表半年才有意義，回溯先補一版 | 計分表有 ≥1 個帳號、5 欄有值、印量測起始日與 n；三個偏差（倖存者／後見之明／單邊上漲）印在表上；`harvest_config` 有每月花費上限 | Phase 2（weekly 算計分表） |
| **4** ▶ | 篩選 | **D11 篩選層機械條件**（覆蓋家數上限、市值上限、瓶頸業務占營收下限、至少一條外部印證的瓶頸邊、入圖前 30 天漲幅上限、12 個月內指名假設的催化劑）＋籃子首選換成這組條件；**＋Q2：籃子每一列強制「有賭注 或 Abstention」，不准空白**；**＋Q1：籃子宇宙擴到被門檻擋下、但已研究過的那 26 條，分兩個分頁**（2026-09-17 使用者核准 A，五欄 amendment 見 [`brainstorms/2026-09-17-no-evidence-case-zoom-out.md`](brainstorms/2026-09-17-no-evidence-case-zoom-out.md) §7） | 首選是 filter 不是分數；今天的三條是賭注條件，不是倍率候選的條件；需求側節點與供給側候選今天被當成同一種東西（舊 backlog 2026-09-11 列） | filter 報表印 input／accepted／filtered 與 reasons 計數（INV-3）；`top_pick` 的判定條件由三條變六條；純需求側節點從候選集合裡被明確 filtered 而不是消失；**Q2：每一列的 `bet_state` ∈ {bet, abstained, unanswered}，`unanswered` 逐檔計數並出現在心跳第 4 段**<br>**2026-09-17 Q2 已交付（Phase 4 的第一件）：** 落地點是「沒有 variant 假設」那個分支——它先前硬編 `not_yet_recorded`，把「已研究、結論是不下注」和「沒人看過這一檔」壓成同一格（L12），而同一個檔案早就在讀 Abstention ledger（L16：分類有 SSOT 卻沒跟著資料走到需要它的地方）。新增 abstention layer `bet`／subject `variant.overlay`（寫入端零改動，沿用既有 `python -m alpha abstention <T> --add`）。**before → after 實測**（查證：`python -m webapp materialize --basket` 後讀 `basket.json` 的 `bet_ledger`，或 `python crons/heartbeat.py` 看第 4 段）：籃子 filter 理由由 3 種 → 4 種（`no_bet` 拆出 `bet_abstained`）；賭注帳 **有賭注 1｜刻意不主張 0｜欠一個答案 15**（16 檔）——**這 15 才是籃子空的原因，沒有一檔是被 substitutability 或證據強度擋下的**。⚠ 刻意**沒有**自動把估值層的 abstention 當成賭注層的：實測 16 檔有 5 檔（SOI.PA／IQE.L／MP／POET／6324.T）已宣告 `valuation/target_pe`，若頂替會把 5 筆待辦冒充成答案（`SETTLED_ABSENCE_KINDS`）。守門測試 `tests/test_bet_endgame.py`（10 條，含空跑檢查）<br>**2026-09-17 Q1 已交付：** ranking artifact 補上 `filtered_rows`／`filter`（籃子是純函式、只吃 artifact，先前讀不到第二個宇宙）；籃子多一頁「量的候選」，條件四條可機械驗證：**已在出貨**（`qualification_status ∈ {qualified, designed_in}`）、需求錨可達、不是已在護城河籃子裡的、外加 Q2 的賭注契約。**before → after 實測**（查證：`python -m webapp materialize --ranking --basket` 後讀 `basket.json` 的 `volume_filter`）：宇宙由 37 條邊 → **多了 26 條已研究但低於門檻的**（`unfilled` 的 159 條刻意不進來——那是研究缺口，去 pq1）；去重後 **12 家，通過 0 家**；理由分佈 `not_shipping_yet 8｜already_in_moat_basket 3｜no_bet 11`。**真正新出現、已在出貨、有需求錨的只有 2 家：3081.TWO 聯亞與 SHA0.DE**——而它們唯一被擋的理由就是 `no_bet`，**與 Q2 的量測完全一致：擴大宇宙之後，擋路的還是「沒人寫賭注」**。<br>⚠ **量的候選刻意沒有排序、沒有首選**：這些邊是被排序權威濾掉的，它們沒有名次；而 `rank_bottlenecks()` 的排序鍵是為護城河問題設計的（sub 是第二鍵），套到「量」上就是自建第二套評分（AGENTS 明禁）。依 ticker 字母序列出並在頁面上寫明「那是字母序不是排名」。<br>⚠ **D11 六條裡有兩條今天沒有資料源**，已在頁面與 artifact 逐條寫出（`volume_filter.missing_criteria`），不假裝已經全上：①覆蓋厚薄（`analyst_count`、市值）——`alpha_purity_snapshot` 有算，但還沒進 overview；②瓶頸業務占營收——Engine C 的 `product_line_revenue_share` 八家有值，同樣還沒進 overview。③第三條「入圖前 30 天漲幅上限」的資料源缺口見 zoom-out §6b（`technical_observations` 只有 14 檔 beta 商品）。守門測試 `tests/test_webapp_basket.py`（8 條新增，第一條驗**護城河那份逐位未動**）<br>**2026-09-17 併入（使用者定案，Phase 1 §2e 第 4 項）：六個 tech 節點走不到任何需求錨。**~~這是圖的結構缺口，補邊即可。~~ ⚠ **2026-09-17 [589] 實測推翻了這個診斷——它不是一種形狀，是四種，而且其中兩種根本不是研究問題：**<br>①**`constrained_by` 沒有被走訪**（`tech:cpo_full_stack_test`、`tech:inp_dfb_laser`）：圖裡**已經有** `tech:cpo --constrained_by--> tech:cpo_full_stack_test` 與 `co:coherent --constrained_by--> tech:inp_dfb_laser`，但 `query/bottleneck.py` 的 `UPSTREAM_RELATIONS = ("enables", "is_component_of")` 不含它，`build_upward_index` 因此跳過。**這是開發項不是研究項**（改 `rank_bottlenecks` 的行為＝開發）。⚠ **不得用「再補一條 relation 不同但語意相同的邊」去繞過 traversal**——那是用資料操弄排序，比改程式更糟。<br>②**`enables` 在圖中承載兩種語意**（元件使能 vs 需求驅動，L12 一表兩義）：`tech:ai_compute_buildout --enables--> tech:cloud_transceiver` 走的是 `upward[enabler].add(enabled)`，對「需求驅動」型的 `enables` 方向是反的。修法是先分開再各自定規則，不是調參數。<br>③**真的沒有任何需求方邊**（`tech:photodiode`）：只有三家公司 `supplies_to` 它、外加一條它自己的 `depends_on`——沒有人記錄過「誰需要光二極體」。**這一個才是真研究缺口。**<br>④**鏈長／中繼節點也到不了錨**（`tech:pluggable_transceiver`：`upward={prod:spectrum_6}`，但 `prod:spectrum_6` 自己也走不到錨）。<br>驗收多兩條：**這六個節點必須在 filter 報表裡以明確 reason 出現、且四種成因要分得開**（不得壓成一句「走不到錨」）；**`constrained_by` 要不要進 `UPSTREAM_RELATIONS` 必須先量「加了之後有幾列真的變了」再決定**（L14-3：先量測後放閘）。查證：`python -m query.bottleneck --top-n 60`（末列的🔴走不到錨提示）| Phase 1 |
| **5** ○ | 表達／量測 | **D2 對稱 overlay（判斷錯了值多少＝反證觸發後的假設套同一條橋）、歸零旗標（現金跑道／負債／稀釋／going concern，紅黃綠）、alpha 全歸零淨值少幾 %；D3 `realized` 降為提醒不觸發出場；D15 追蹤表三個 power-law 統計量**（12／24 個月內達 2 倍的比例、最大單檔貢獻、籃子總報酬）；舊 backlog「賭注 V4：variant 收斂納入 outcome」併入本 Phase | 尺寸由使用者決定，系統只給三件；出場只認反證；等權中位數量不到 power-law | COHR 與三檔初始標的各有這些格；`library/private/decision_lab/outcome_aggregate.json` 多三個統計量 | Phase 1 |
| **6** ○ | 發現／量測 | **D15 台股每月營收納入 Engine C 一手 datum、MOPS 重訊 watcher、parked lead 超過 60 天自動 `expired` 並計數（不刪）** | 台股月營收比季報早；重訊是最早的一手；parked lead 沒有到期就是 INV-2「等待沒有到期」 | 3081.TWO 有月營收序列；`expired` 計數出現在心跳第 3 段 | Phase 2 |
| **7** ○ | 表達 | **多年反向橋（「五倍要什麼為真」）取代 FY+1 主流程；entry criterion 降級**（最後做：最大的契約變更，前六個 Phase 不依賴它） | 現行儀器是給大型股 20% 錯價的；thesis 講 FY28，模型只有 FY27 一格 | 個股頁的「賭對了值多少」由 FY+1 單格變成多年橋；COHR 首屏 244 vs 266 的錯位消失；舊 backlog 裡橋契約的四個未結案（口徑、另類資產、共識核實、多筆生效）在此一併重看 | Phase 5 |

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
> ⚠ **§9 的「各 Phase 🔴 責任分配」表用的是舊 refactor 的 Phase 編號**（contracts／Portfolio-Risk／
> vertical slice／Engine D 分解…），**與本檔 Alpha Edge 的 Phase 0–7 沒有對應關係**。
> 第 8 項要對照的是「本 Phase 實際動到哪些事故的形狀」，不是編號對編號。

### Phase 1 completion gate 逐項核對（2026-09-17，Step 1.3；每項附查證命令）

| # | 項目 | 結論 | 依據（現跑，不抄） |
|---|---|---|---|
| 1 | Historical regression suite pass（golden fixtures） | **過** | `tests/fixtures/golden/` 14 份 fixture＋`tests/test_golden_fixtures.py` 在全套內綠。查證：`python -m pytest tests/test_golden_fixtures.py -q` |
| 2 | Runtime invariant audit pass | **過** | FAIL 0｜PASS 13｜檢查 4,087 筆。查證：`python -m audit invariants` |
| 3 | No unexplained semantic diff（old/new dual run） | **過** | Step 1.0 對 218 條「公司→向下」邊做過舊解析器 vs 新解析器 dual run：39 條改判全部有分類（升 31 條每條指得出一個解析到非主詞 registry 公司的 origin，違規 0；降 8 條全是主詞自家文件被括號註解污染成第三方的歸位）→ 0 筆 unexplained。Step 1.1／1.2 是**純新增**（新抓取器、新 SourceDoc、新邊），不改既有輸出路徑，依 §8「純新增不需 dual run」。⚠ 誠實補一句：當時的舊實作副本放在**未追蹤**的 `.pytest_tmp/old_bottleneck.py`，**那次 dual run 今天已不可重跑**，只剩 commit `69c8388` 的逐筆紀錄 |
| 4 | **No new dual authority** | **過** | 三樣新東西都沒有建立第二個 current-state authority：抓取器只寫 `library/raw/`，不落任何快取表；`product_line_revenue_share` 登記在 `config/engine_c_observation_fields.json` 由 Engine C 承擔，且**刻意不覆寫** `segment_revenue_share`（決策 D2——報導部門占比與產品線占比是兩個語意，不是同一真相的兩份）；`config/source_routes.json` 是 how-to 不是事實。查證：`python -c "import json;d=json.load(open('config/engine_c_observation_fields.json',encoding='utf-8'));print([f['field_name'] for f in d['fields'] if f['field_name']=='product_line_revenue_share'])"` |
| 5 | No silent-drop path | **過（本 Phase 的範圍內）** | 兩支新抓取器逐則報 input／accepted／filtered／reasons（`fetchers/mfn.py:165`、`fetchers/rns.py:165`，CLI 印到 stderr）；排序的 as-of 投影由 `AsOfProjection.reasons()` 報 `published_after_as_of`／`undated`（`query/bottleneck.py:630`）。⚠ **門檻 4 的 filter 在 CLI 上今天只印覆蓋率、不印逐檔 reasons——那是 Phase 4 的驗收項**；本次收尾以唯讀重量補出逐檔報表（見下） |
| 6 | Point-in-time tests pass | **過** | `audit invariants` 的 PointInTime：SourceDoc `published_at` 202/215（94.0%）、EdgeAssertion 可定日 657/674（97.5%）；13 份未定日**逐份列名**且擋住的邊有計數（L11-5 留 null 不猜）。三份新文件 `published_at` 皆 ≤ `retrieved_at`。查證：`python -m audit invariants --only PointInTime` |
| 7 | All migrated lifecycle objects reachable | **過** | audit 的 Lifecycle 598 筆／Expiry 85 筆（進行中的等待全部有到期日）／QueueLiveness 31 筆／QueueSegments 1,760 筆全 PASS；[579]–[585] 六個編號全部帶 `action/digest/commit/cohort` receipt 結案，池中無本 Phase 未決編號。查證：`python -m engine_b.todo list` |
| 8 | **critical historical failure 已有 executable protection** | **過（但編號對照不成立，見上）** | 本 Phase 實際動到的是**排序的證據分級**（F-20 截斷集合被當全集）與**新來源的定日**（F-31 Engine A 無 as-of）。兩筆在 §1 都已是 ✅：`alpha.contracts.RankedList` 強制帶 `full_ids`、`contains()` 只讀它，突變測試會紅；`PointInTimeUnsupported`＋`PointInTime` audit 今天 PASS。**本 Phase 沒有新增任何 🔴**。⚠ 未清掉也不在本 Phase 範圍的 🔴 仍有 7 筆（含 F-03） |

**結論：八項全部過，但 Phase 1 仍不標 ✅**——completion gate 過不等於驗收行達標。
驗收行明訂「可投資排序的 TW／TWO／ST 檔數仍為 0 就不得標完成」，2026-09-17 實測**仍是 0**。

#### 第 5 項的逐檔報表：門檻 4 的 filter（INV-3，2026-09-17 唯讀重量）

`input 222｜accepted 37｜filtered 185`——filtered 的理由只有三種：
`substitutability` 未填 **162**、`substitutability=3` **15**、`substitutability=2` **8**。
**沒有任何一檔是因為走不到需求錨被濾掉**（所有 TW／TWO／ST 公司的向下邊都接得到錨）。

| 公司 | 向下邊 | 現況 | **缺哪一份文件**（不得靠放寬門檻取代） |
|---|---|---|---|
| 上詮 `co:foci`（3363.TWO） | 1 → `tech:fiber_attach_unit` | sub 未填、自報·filing | Himax 或長約對手方的**客戶端具名確認**。一手只有自述目標（「長期目標係成為 CPO 光纖陣列元件之主要及重要供應商」）與產能投資；Hunterbrook 是媒體，依決策 C1 維持待判定 |
| 聯亞 `co:landmark_optoelectronics`（3081.TWO） | 1 → `tech:cw_dfb_laser` | **sub=3**（2026-09-17 新填） | 2026-08-26 四年長約的**條款**（最低採購量／獨家性／價格）。對照組是 IQE→Tower 判 4：雙向最低採購承諾逐字可讀。條款只可能由**對手方**（未具名的美國客戶）的法定文件揭露 |
| 華星光 `co:luxnet`（4979.TWO） | 1 → `tech:cw_dfb_laser` | sub=2 | **對照組，本 Phase 明訂不得改判**；2026-09-17 複查未動 |
| 全新 `co:vpec`（2455.TW） | 2 → `tech:cw_dfb_laser`、`tech:photodiode` | sub=2 ×2（本輪補邊） | 客戶端具名＋替代難度的正面證據。**現有一手證據方向相反**：全新在自家年報點名聯亞與 IQE 是同層競爭者 |
| IET-KY `co:intelliepi`（4971.TWO） | 2 → `tech:vcsel`、`tech:photodiode` | sub=2 ×2（本輪補邊） | 同上；英特磊自家年報點名全新與 IQE |
| Sivers `co:sivers_semiconductors`（SIVE.ST） | **15，其中 14 條 sub 未填** | `prod:els_8ch_module` 那條**已外部印證但 sub 未填**——這是最接近進榜的一格 | Ayar Labs 自家文件（`ayarlabs.com` 對本機 UA 回 403）；`tech:wdm_laser_16ch` 要它才能由供應商自報回到雙方聯合 |
| **穩懋 `co:win_semiconductor`（3105.TWO）** | 1 → `co:sivers_semiconductors` | **已是外部印證、sub 未填** | ⚠ **2026-09-17 收尾新發現，不在 Step 1.2 的七家工單裡**。證據等級已經夠，缺的只有 `substitutability` 的判讀依據 |
| Aehr `co:aehr_test_systems`（AEHR） | 1 → `tech:cpo_full_stack_test` | sub 未填，且該 tech 節點**走不到任何需求錨** | 先補「`tech:cpo_full_stack_test` → `tech:cpo`／`tech:ai_switch`」那條邊，否則補了 sub 仍然排序不可見 |

查證：`python -m query.bottleneck --top-n 60`（表內不會出現任何 `.TW`／`.TWO`／`.ST`）。



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

## 舊 backlog 未結案項（自封存表移入；只留標題與去向，內容看 archive）

| 舊表列（archive 的開放 backlog） | 舊標記 | 去向 |
|---|---|---|
| 賭注 V4：variant 收斂納入 outcome 量測 | ○ | **Phase 5**（量測） |
| APP 的標的列表還不知道「等財報」這種終局——它會顯示成「還沒做」（2026-09-12） | ○ | 維持營運（當下修檔次，不占 Phase） |
| AEVA／TSEM 已查證未揭露（2026-09-04） | ○ | 留 archive（資訊，不是工作） |
| 節點屬性沒有衝突解決機制（偵測那一半已於 2026-09-10 交付） | 🔶 | 留 archive，等第二個實例再泛化（L17-4） |
| 誠實回 `unknown` 的軸讓該檔結構上永遠到不了段 5 終局（2026-09-10） | 🔶 | **Phase 5**（重看 readiness 語意時一併） |
| Engine C 快照的 `gross_margin` 是 TTM、`operating_margin` 是單季（2026-09-11） | 🔴 | 已由同表 2026-09-13 ✅ 列解決（重複列），結案 |
| 入圖後自動追蹤把非公司節點也建成 cohort（2026-09-11） | 🔴 | 已由同表 2026-09-12 ✅ 列解決（重複列），結案 |
| 殘餘缺口已鑄成 Engine C 觀測 pq2 之後，collector 仍為同一缺口鑄「去做研究」的 pq2（2026-09-11） | 🔴 | 維持營運；**Phase 2** 整理佇列段時一併 |
| 段 5 的工單把「需求側節點」與「供給側候選」當成同一種東西（2026-09-11） | 🔴 | **Phase 4**（正是篩選層要分的） |
| registry 缺 `market_currency` 會讓 headline 整格消失，錯誤訊息不指向 registry（2026-09-11） | 🔴 | 維持營運（當下修檔次） |
| `FiscalYearActuals.revenue` 是單一口徑，GAAP 與 non-GAAP 連營收都不同（2026-09-11） | 🔴 | **Phase 7**（橋契約） |
| 基期觀測有 8 檔同時有兩筆以上「生效」紀錄（寫入端已擋，既有 14 組還在；2026-09-13） | 🔶 | **Phase 7**（橋契約） |
| 橋的形狀對另類資產管理業不成立（加法鏈等使用者決定兩個契約問題；2026-09-13） | 🔶 | 留 archive——另類資產管理不是邊緣瓶頸供應商，轉向後優先序最低 |
| 共識口徑的核實只有一條路（`year_ago_actual`），基期被重述時結構性不可用（2026-09-13） | 🔴 | **Phase 7**（橋契約） |
| `*_fx_tolerated` 被套用在同幣別標的上（Z2，動的是 2026-09-11 定案的容差；2026-09-13） | 🔶 | 留 archive，待使用者決定，不排程 |
| 「卡世界」只能靠 `--skip` 人工宣告；機械代理實測恆亮（否定結果；2026-09-13） | 🔶 | 留 archive（記下來是為了不要有人再去建它） |

---

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

