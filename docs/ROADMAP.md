# StockBotv2 — 交付歷史與待辦方向 (Roadmap)

> 這裡是「做過什麼、還想做什麼」。判準與現行契約在 [`AGENTS.md`](../AGENTS.md)；指令與程序在 [`OPERATIONS.md`](OPERATIONS.md)。
> **規劃或決定下一步時讀本檔；日常操作不必載入。**
>
> `docs/plans/` 已轉純歷史（見 [`plans/README.md`](plans/README.md)）。小工作直接做、不開 plan 檔；只有大型開發才新建 plan。

## 想法怎麼變成程式

```
ROADMAP「未來想法」  →  docs/brainstorms/  →  docs/plans/  →  實作
   （還沒決定要做）      （需求與盲點審查）     （規格與驗收）
```

四階不是每次都要走完。判準是**改錯的成本**：小工作直接做；需要先想清楚需求與反面的走
brainstorm；範圍大到需要驗收條件才開 plan。brainstorm 用 frontmatter 的 `planned_in:`
指向自己的 plan，plan 完成後回填到上方「已交付」表。

**目前沒有進行中的 plan。** 仍有未實作的 brainstorm 項目，見下方「開放 backlog」與「已 brainstorm 但未實作」。

---

## 已撤回的診斷（開工前掃一遍）

> **這一節不是自責，是一份檢查清單。** 每一筆都是「已經寫進 commit／ROADMAP／程式註解，
> 事後被推翻」的技術診斷——不是待辦、不是 bug，是**曾經看起來完全正確的錯誤結論**。
>
> **為什麼需要它：** 2026-08-19 一天之內有三個診斷被推翻，共同形狀是
> **錯誤有方向性——全都朝「產生一個有洞察力的結論」偏**，而且每一個都能用專案自己的
> lesson 語言包裝（L12 一表兩義、L15 gate 攔錯東西）。**模式匹配是提出假說，不是確認假說。**
> 一個現象能被套進某條 L，只代表它值得查，不代表它已經被查過。
>
> `AGENTS.md` L11 判準 2 已經逐字寫下這個失效模式（「剛好嵌得進已成形的敘事時，
> 恰恰最該起疑」），L14 也已寫下「寫進本檔不等於會生效」——**所以解方不是再加判準**。
> 第三欄才是重點：**每個錯誤診斷都有一條 30 秒就能否證它的命令，而當下沒有人跑。**
>
> **用法：** 宣稱「找到根因了」之前，先跑一條**試圖讓自己的結論變成假的**命令
> （不是驗證它為真——那是確認偏誤）。專案對每個 thesis 都強制 `disproof_condition`，
> 這一節是把同一個要求套到自己的技術診斷上。

| 日期 | 被推翻的診斷 | 當時為什麼看起來對 | 一條就能否證它的命令 |
|---|---|---|---|
| 2026-08-18→19 | COHR「Engine C 的 `bar_date` 是憑空生成的、`price` 對不上任何收盤」 | 使用者成交價與系統顯示差 10%，需要一個解釋；`history()` 當下沒回 08-17 那根（**盤中查的**，最後一根是進行中的 bar），拼出「08-17 不存在」。剛好是漂亮的 L12「一表兩義」案例，於是寫進 commit message、ROADMAP 🔴 與程式 docstring，還差點據此在 ETL 加一道會 quarantine 掉正確資料的交叉驗證 | `date(2026,8,17).strftime('%A')` → `Monday`。**08-17 是星期一，一本日曆就能否證** |
| 2026-08-19 | 待辦池三個 `decision_review` 不退場是因為「空 `blockers` 被 `todo.py:1448` 判成非純系統」 | `sizing` 的 `assessment_blockers`／`paper_blockers` 確實全空，且 paper 已 ELIGIBLE；「空集合被判成非純系統」又是一個漂亮的 L12 案例 | `python -m decision_lab card <decision_id>` → `card.blockers` 有 **7 個碼**，不是空的 |
| 2026-08-19 | 同上，第二版：「`execution_fx_stale_since_decision` 未登記，掉進 `execution_` 泛用 prefix 被判 `awaiting_external`」 | 自己寫的檢查腳本取「**第一個** prefix 匹配」而非登記表 `_matching` 規定的「**最長**匹配」，於是自製了一個不存在的 bug。剛好是 L15「gate 攔錯東西」的形狀，可執行、可驗收，看起來完全合理 | 讀 `config/decision_blockers.json` 的 `_matching` 那一行；或 `get_blocker_registry().classify(codes)` 直接跑。真相是它**早就以 exact prefix 登記為 `system_internal`**。補進去後被 `test_registry_is_the_single_source_of_severity` 以「重複 key 73≠72」擋下——**測試比我可靠** |

| 2026-08-19 | 「`live_choices`／`live_execution_reports` 仍為 0 筆，live 這條路徑**從未被走過**」——並據此對使用者斷言 | **直接引用本檔自己的文字**，而該句寫於 2026-08-15 之前、當時為真。錯誤不在推理而在**根本沒推理**：把自家文件當成 current-state truth 引用，正是 L11 判準 2 說的「對外部 claim 嚴、對自家文件鬆」。使用者前一天才走完全鏈，且系統完整記錄了 choice 與 fill | `select count(*) from live_choices` → **1**。已改為附查證命令，並新增 `AGENTS.md`「現況數字會過期，判準不會」小節 |
| 2026-08-19 | 「`commercial_maturity` 積壓缺的是**有人去讀年報附註**」 | 本檔原條目這樣寫，聽起來完全合理（IQE 正是這樣解掉的），差點就照做去讀年報 | 逐一看 7 個積壓的 `missing_data` → 6 個是 `research_assessment_missing`（**連 assessment 都沒有**，且五軸 reason 一字不差），AVGO 甚至早就有那兩筆觀測；第 7 個 Agility 未上市、沒有年報可讀。**靠讀年報能下降的是 0 個** |

⚠ **這一節自己的 disproof：** 若之後仍發生「診斷已落地才被推翻」，代表它沒生效，
不要靠加字補救——那正是 L14 批評的「要人讀的段落」。屆時該做的是把否證步驟綁進
會自己執行的東西（測試、hook、或 commit 前的檢查），而不是把這張表寫得更長。

---

## 已交付

> **記錄實測 before → after，不只記「做了什麼」。** 一個改動若說不出哪個現有數字變了，
> 它與沒做在結果上不可區分（`AGENTS.md` L14 第 1 條）。翻歷史時要看得出哪些是真交付、
> 哪些是白工——2026-08-02 至 08-08 的四次「已實作但供給為零」如果當初這樣記，
> 第二次就會被抓到。

| 完成日 | 項目 | 歷史 plan |
|--------|------|-----------|
| 2026-08-19 | **第一筆真實部位變成可量測** — COHR（使用者 08-18 買進 10 股 @ 316.23）的 decision 原本 `disproof`／`catalyst`／`expiry` **全是 `None`**、且 cohort lifecycle 於 07-25 以 `expired` 終結。實測確認再次結案會拋 `terminal epoch already has a different outcome`＝**新 disproof 觸發時拿不到 `claim_correctness`**，正是 outcome 長期 0/8 的其中一個成因。修法：綁定以 Q4 FY2026 一手數據為基準的四條 disproof（non-GAAP 毛利率 40.2%＝822.6／2,045.5 為領先指標），並新增 `DecisionStore.reopen_lifecycle_epoch()` 開 epoch 2（**append 不覆寫**：epoch 1 與其 outcome 原封不動，符合 L10）。before → after：`catalyst_watch` 設定不完整 **1 → 0**、COHR lifecycle `expired` → `active(epoch 2)`。⚠ 同輪否證了自己前一天的診斷「lifecycle expired 會讓 disproof 不被檢查」——`catalyst_watch.fetch_entries` 讀 `coverage_assessments`、根本不碰 `probe_lifecycle_epochs`，disproof 一直都有被檢查 | — |
| 2026-08-19 | **Alpha 候選排序進入 daily** — `rank_bottlenecks()` 早已把 COHR→NVIDIA（5/5 `sole_source`、外部印證、距需求端 2 跳）排第 1，但**從未進入 daily 流程**，使用者看不到、agent 被問推薦時只能拒答（L13 管子只接一頭）。補上 `AGENTS.md` Alpha 契約的「哪些標的值得看」判準（瓶頸地位／需求錨點／L8 證據強度三維度）與 `skills/daily-brief` 的消費端（Step 4 接 `query.bottleneck` 為買進側，與既有 `catalyst_watch` 賣出側對稱）。同輪三檔補人工估值觀測，`axis_ceiling > 0` **8/16 → 11/16** | — |
| 2026-08-15 | **引用解析缺口修復＋全域 cohort 掃描** — `assessment_context_mismatch` 使 AXT／LITE 的 paper 由 `SHADOW_ONLY／target 0` → **`ELIGIBLE／target 0.1%`**，frozen 非零 live 區間 **0/75 → 2/77**（現行 v3 骨架 **2/4**）；成因是引用字串與 `reference_index` 的 key 對不上——最刺眼一筆兩邊是**同一份 10-Q、同一個 SEC accession**，只因描述段不同而三種解析全不命中。修法選在源頭消歧義（新增 `decision_lab references`，寫 assessment 前看得到合格引用），**解析規則一字未動**，故無 authority laundering 空間。另修 Engine C 觀測提案 `as_of` 契約與 ledger 不一致（提案曾能建立、進池、被使用者核准，卻在寫入 ledger 那一刻才失敗）。**全域掃描 13 個 cohort 確認引用問題只影響這 2 筆**，並非原先推測的普遍主因 | — |
| 2026-08-14 | **資本表達層 workstream（§4 六步完成五項，僅第 5 項待使用者決定）** — outcome 量測 0→9/9（AXTI 超額 QQQ +72.8%）；blocker severity 移進 config ＋ lane 維度，live 非零 **0→8**、binding 由 `live_lane_blockers` 71/72 變成 **`weakest_axis` 31**；引用無歧義解析＋「至少一個合格」，`axis_ceiling==0` **23→17**；催化劑排程使 AXT 複查日 **2026-11-15→2026-10-30**；daily brief 兩個常駐計數器上線 | [方向與 baseline](brainstorms/2026-08-13-capital-expression-direction-requirements.md) |
| 2026-08-14 | **量測與資料語意收尾** — Shadow 錨點回填使可量測 cohort **7→9**（另 4 個無 ticker，屬正確 unavailable）；Engine C 拆出 `bar_date`／`price_kind`，`snapshot_date`（ETL 執行日）不再被誤當行情交易日；`engine_b.todo.SOURCE_COLLECTORS` 單一登記表使全套測試由 **911/1 紅 → 918/0**；`AGENTS.md` lessons **188→160 行**（15 個編號全保留，砍考古留判準） | — |
| 2026-07-18 | **M1 CPO Depth Sprint** — AXT onboard；Coherent／Lumentum／NVIDIA／Broadcom 各 ≥3 distinct `origin_entity`；20 條 edge conflict 全數 resolve 並 project 進圖 | — |
| 2026-07-19 | **第二條垂直切片／L9 前置 #1** — AMAT/LRCX mature-node Lane Memo（非 AI／非 CPO），評分 23/30，`_check_second_slice()` 通過（commit `a7abdf5`） | [005](plans/2026-07-08-005-feat-second-vertical-slice-plan.md) |
| 2026-07-21 | **Action-Oriented Alpha Decision Lab v1** — Signal → Shadow → Coverage／Confidence → sizing → funded paper／Action Card → outcome 閉環 | [2026-07-21-001](plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md) |
| 2026-07-22 | **Engine D operational workflow** — `evaluate-signal`／`reassess`／`today` 三個正常入口，不要求 internal digest／Coverage ID／idempotency key | [2026-07-22-001](plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md) |
| 2026-07-22 | **L9 剩餘財務核驗缺口** — COHR 客戶集中度與 backlog 補入 manual observation ledger；`preconditions.py` 全綠、`checklist.py COHR` 五項 gate_pass=true。**L9 三前置條件全部達標，投資諮詢 gate 開放** | — |
| 2026-07-23 | **Daily Approval Loop v1.0 骨架** — leads 狀態機＋harvest、partial-identity 修復、MCP `get_decision_brief`、`/daily-brief` skill | [2026-07-22-002](plans/2026-07-22-002-feat-daily-approval-loop-plan.md) |
| 2026-07-26 | **Daily Approval Loop v1.2 本機 rollout** — runner 改 Codex desktop local scheduled task，不再依賴 cloud clone／MCP | [2026-07-24-001](plans/2026-07-24-001-feat-daily-approval-loop-v1-1-plan.md) |
| 2026-07-28 | **Daily Beta Technical Monitor v1** — 11 條 technical series、append-only `technical_observations`、shared cash pool | [2026-07-28-001](plans/2026-07-28-001-feat-daily-beta-technical-monitor-plan.md) |
| 2026-07-29 | **Portfolio Risk Policy Redesign** — 統一 numeric SSOT；只有 ETF 槓桿 cap 與 5% 單筆上限歸零 live range，其餘只記錄／警告 | [2026-07-29-001](plans/2026-07-29-001-refactor-portfolio-risk-policy-plan.md) |
| 2026-07-29 | **Serenity 30-Day Research Campaign** — 279 則回補、robotics ontology mini-slice 入圖 | [2026-07-29-002](plans/2026-07-29-002-feat-serenity-30d-research-campaign-plan.md)、[報告](reports/serenity_30d_research_2026-07-29.md) |
| 2026-07-30 | **封閉字彙收斂** — Engine C 觀測欄位 registry、blocker registry、authority token 單一權威；待辦池分離「等決定／等事件」 | [封閉字彙登記表](solutions/architecture-patterns/closed-vocabulary-registry.md) |
| 2026-08-01 | **Routine reliability 收尾** — daily X bounded pagination checkpoint、lead refs registry、terminal Decision gap 明確 redispatch、自有現金每 5 個完整交易日例行提醒 | — |

**Engine D 仍未包含：** notification、remote Decision MCP、broker routing。

---

## 開放 backlog

> **這是 loop #2 的工作台。** 開發／維護的推進靠使用者主動進來，不靠自動提醒——
> 因此本節要解決的不是「會不會想起來」，而是**打開後能不能立刻知道下一步做什麼、
> 以及上一步有沒有成功**。
>
> **每項強制四欄：項目／為什麼／驗收條件（哪個數字會變）／前置。**
> 沒有驗收條件的不准進佇列（`AGENTS.md` L14 第 1 條）。動工前先看驗收條件，
> 做完後回頭比對，再把實測 before → after 記進「已交付」。

### 進行中

**資本表達層 workstream 已於 2026-08-15 結案。** 原目標「把 Engine D 從永遠不下注變成
小注但有意義」已達成：live 非零 **0/72 → 9/89**（現行骨架 9/16）、ELIGIBLE cohort **0 → 8**。
但它的下半段（§4 第 5 項「決定 alpha baseline 尺寸」）被使用者用另一種方式結掉了——
**決定不看尺寸**（見 `AGENTS.md`「Alpha 呈現契約」）。理由是實測：6 個 ELIGIBLE cohort 的
target 全是同一個 0.1%，常數不帶資訊，而使用者要的是「撒網、推薦幾檔、追蹤新事件」。

### 主題範圍（2026-08-20 使用者定案）

**以 CPO 與 humanoid 兩條為主。** 使用者原話：HBM「太大了，資金太瘋狂了，而且太寡占，
感覺現在進去太晚了」。因此 HBM／記憶體軸**只做到 Micron 這筆入圖候選為止，不再往下深挖**
（`co:micron_technology` 已註冊、prepared RA `ra_b70b2699` 待核准）；SK Hynix／Samsung
不主動 onboarding。

判準本身仍然有效——tech:hbm 確實是圖中最大的供給側空白——但**「是個真瓶頸」不等於
「現在該投」**：寡占程度、資金擁擠度與進場時點是使用者的判斷維度，不由 chokepoint
排名決定。往後做廣度掃描時，先用這條過濾，不要再把 HBM 當首選推薦。

**優先序是主線／備援，不是並列（2026-08-20 澄清）：** 其他非 HBM 的 AI 相關瓶頸
——SerDes／serializer、載板與中介層（`mat:glass_substrate`、`mat:silicon_interposer`）、
測試（圖中連節點都還沒有）——使用者的原話是「上面暫時沒東西走的話可以挖」。
**只有 CPO 與 humanoid 兩條主線當輪沒有可推進的工作時才動它們**，不得因為某個備援
節點的 chokepoint 分數較高就插隊。已勘查的現況（留給屆時直接接手）：
`tech:serdes` 0 供應商且 `IS_COMPONENT_OF tech:ai_switch`；
`tech:dsp_1p6t` 0 供應商且 `IS_COMPONENT_OF tech:cpo`（這個其實長在 CPO 主線上）；
Marvell FY2026 10-K Item 1 一段內同時逐字涵蓋 ultra-high-speed SerDes、PAM／coherent
optical DSP、TIA、CPO、LPO chipset、AEC DSP 與 PCIe retimer，是補這幾格的現成一手來源
（注意其 10-Q 為財務導向，`\bDSP\b`／SerDes／optical 皆 0 次，產品描述只在 10-K）。

⚠ humanoid 的可投資機會在**零組件供應商**不在整機：`co:agility_robotics` 未上市
（`research_ticker=null`，其 cohort 長期卡在「Agility 未上市，尚無任何紀錄」）、
`co:boston_dynamics` 屬 Hyundai。圖中已有的實體關係只有
`co:hyundai_mobis SUPPLIES_TO co:boston_dynamics` 與
`co:schaeffler DEVELOPS prod:schaeffler_rotary_actuator_platform`
（後者 `IS_COMPONENT_OF tech:humanoid_robot_systems`）。
**5 個 robotics chokepoint 全部 0 個公司供應商**（`tech:robotic_actuator`、
`tech:humanoid_robot_systems`、`tech:robotics_as_a_service`、
`tech:advanced_robotic_devices`、`tech:logistics_tote_transfer`），
而 `tech:robotic_actuator IS_COMPONENT_OF prod:atlas_humanoid_robot`——
actuator 是已在圖中被標為關鍵零組件、卻完全沒有供給側的那一格。

新 workstream：**廣度、事件追蹤、量測**。三條各有可驗證的數字，取代舊的「非零 live 區間」：

| 目標 | 現值（2026-08-15） | 怎麼變好 |
|---|---|---|
| 🔴 **可執行性**：使用者能否據此下手 | **2026-08-19 前為 0** | **本表原本缺這一列，是最上游的問題。** 前三個目標全是「系統內部指標」，沒有一個回答使用者真正的問題——「我不知道投哪個，你能幫我做到什麼」。實測後果：`rank_bottlenecks()` 早就把 COHR→NVIDIA（5/5 `sole_source`、外部印證、距需求端 2 跳）排在第 1，但它**從未進入 daily 流程**，於是使用者被迫自己判斷，而 agent 被問到推薦時以「outcome 0/8 未驗證」拒答。判準與交付要求已寫入 `AGENTS.md` Alpha 呈現契約「哪些標的值得看」小節，消費端已補進 `skills/daily-brief/SKILL.md`（Step 4 ＋ `## Alpha 候選` 段落）。**驗收：daily brief 每天輸出有序候選＋明確首選＋各自 disproof** |
| **廣度**：可評估標的數 | 8 個 ELIGIBLE cohort | ⚠ **這一列的指標本身有問題**：`ELIGIBLE` 是 paper 資本閘門，不是選股判準，把它當「廣度」會誤導成「候選越多越好」。使用者要的是**收斂到首選**，不是擴大清單——16 個 cohort 高度集中於 AI 光互連，列 N 檔不等於 N 個獨立機會（同一 sector 移動被複製 N 次，見下方錨點效度下修）。真正的廣度缺口是**不同主題的瓶頸**，做法仍是瓶頸目標導向：`query/bottleneck.py` 已能列 chokepoint 與已知供應商，缺的是「這條 chokepoint 上還有誰沒研究過」→ 具名 harvest target（見 [`2026-08-18-alpha-live-user-sized`](brainstorms/2026-08-18-alpha-live-user-sized-requirements.md) §8.9）。舊做法（清 pq1 積壓、擴來源）沒有方向 |
| **事件追蹤**：新事件進 brief 的延遲 | 未量測 | 先補 watcher 覆蓋（今天才發現 TSEM 長期空轉），再談延遲 |
| **量測**：可量測 cohort 與超額中位數 | 10/15 個可算出數字，但**有效 n≈1**（見下） | **先讓錨點帶有進場判斷**，再談樣本期 |

🔴 **2026-08-18 查證後下修：這條目前不是「樣本還不夠」，是「量的東西不對」。**
使用者提出「錨點應該只是剛好我們那時候把系統打通，而且建 cohort 是因為入圖、
不是因為我們覺得那時候可以買」——查證屬實，兩項證據：

1. `decision_cohorts.dedupe_key` **全部**是 `claim:<hash>`——cohort 由**入圖**建立。
   錨點日的語意是「這家公司的 claim 那天進圖」，**不含任何進場時點判斷**。
2. 10 個 observed 錨點全部落在 `2026-07-21 ~ 08-14`（24 天、4 個日曆週），
   而 SOXX 在 07-28 見底、正好在窗口中間；標的又幾乎全屬 AI 光通訊主題。

合起來：那不是 10 個獨立觀測，是**一次 sector 移動被高度相關的標的複製了 10 次**，
而那個窗口正好是系統被建起來的期間。先前寫的「超額中位數 +11.1%」與
「錨點前 -9.2%／錨點後 +15.0%」都只描述**這批標的是在什麼行情位置入圖的**，
**不構成選股能力的證據**。

`scripts/outcome_if_settled_today.py` 的「錨點體檢」段落已改為先講樣本效度再講數字，
跨度短於 60 天就出紅字警示。**修法方向不是累積更久，是讓錨點帶有進場判斷**
（見 [`2026-08-18-alpha-live-user-sized`](brainstorms/2026-08-18-alpha-live-user-sized-requirements.md) §7）。

**舊 workstream 的步驟表仍在 [`2026-08-13-capital-expression-direction`](brainstorms/2026-08-13-capital-expression-direction-requirements.md) §4**，
六步已全部完成或被上述決定取代，保留作需求推導的歷史。

⚠ **仍然有效的一條：不得因為「閘門已經修好了」就順手調大 `axis_ceilings`**（D7 先量測後放閘）。
現在更沒有理由動它——尺寸已不對使用者呈現，調大它不會改變任何人看到的東西，只會讓
paper 記分板失去可比性。

### 未排程

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| **補齊各 cohort 的 `commercial_maturity` 觀測** | 該軸只接受 `engine_c_backlog`／`engine_c_customer`，沒有觀測就整軸歸零。IQE 曾因此停在 `SHADOW_ONLY`，2026-08-15 補上 FY2025 年報 Note 4.3 的客戶集中度觀測後轉為 `ELIGIBLE`。2026-08-15 已驗證**這不是非美股的結構性障礙**：SIVE 用年報 Note 5「Information about major customers」、IQE 用 Note 4.3，兩者都揭露。<br>🔴 **2026-08-19 實測後下修：本條原寫「缺的是有人去讀年報附註並建觀測」，但對現存積壓一筆都不適用。** 逐一檢查 16 個 cohort 的最新 decision，7 個含 `commercial_maturity_unknown`，拆開後**沒有一個是「讀年報就能解」**：①**AVGO、POET** 的 `missing_data` 是 `research_assessment_missing`、**五個軸的 reason 全部相同**（「尚未提供語意研究評估」），而 `library/private/decision_lab/` 裡**根本沒有 avgo／poet 的 assessment 檔**——AVGO 甚至**早就有** `customer_concentration`＋`backlog` 兩筆觀測，補第三筆是 0 筆變化；②**Agility** 是唯一真的卡在缺 Engine C authority 的，但它**未上市、沒有年報可讀**（該筆 reason 已自陳「Agility 未上市，尚無任何紀錄」）；③其餘 **4 個是歷史 frozen／重複 cohort**（META、AAOI+AXT+SIVE 混合、Agility 另一筆、一筆無標的），對應公司多半已有更新 cohort 且該軸已通過，依 append-only 契約**不回寫**。<br>**兩層關卡不可混為一談：** `research_assessment_missing` 由 `workflow.py::_unknown_assessment()` 在**完全沒有 assessment** 時對五軸一次性寫入（severity `fatal`）；而 `sizing.py:41` 註解記的「有那兩筆觀測的 cohort 全部 bounded_hypothesis、沒有的全部 unknown，相關性 100%」是在**已有 assessment** 的 cohort 之間測的。**順序是 assessment → 觀測才有機會被引用**，本條原文漏掉前置，於是把積壓的成因指到了錯的一層。IQE 軌跡是三段完整反證：08-04 `research_assessment_missing` → 08-08 有 assessment、missing 轉為「Engine C manual observation：IQE 客戶集中度」→ 08-15 補上 Note 4.3，`ceiling` 0 → 0.002 | 因 `commercial_maturity_unknown` 而 `axis_ceiling=0` 的 cohort 數下降（現值 **7/16**，2026-08-19 實測）。⚠ **但這 7 個要靠補觀測下降的數量是 0**——要動這個數字，binding constraint 是**替 AVGO／POET 跑五軸 assessment**（研究工作，非讀年報）。本條僅對**未來已有 assessment 卻缺觀測的 cohort** 有效，屆時 `missing_data` 會明講缺哪一筆（如 IQE 08-08），不會是 `research_assessment_missing` | 先確認該 cohort 的 `missing_data` **不是** `research_assessment_missing`；是的話前置變成跑 assessment |
| **Engine D cohort 重複** | 同公司可能同時存在 claim-keyed 與 company-keyed 兩個 cohort（2026-07-30 [74]／[75] 實例） | 新建 cohort 時偵測同公司既有 cohort 並警告。**不回溯清理**——Decision Store append-only，不做破壞性去重 | 無 |
| **ETF 完整 look-through** | `issuer_loads` 只涵蓋 policy 已登記的 ownership，曝險輸出恆為 `partial` | 曝險輸出出現 `coverage: full` 的標的 ≥1 | 無 |
| **本機 single-writer guard** | 目前靠人工紀律確保同一 working tree 只有一個 agent 寫入 | 模擬兩個 writer 併發時會被擋下（可寫成測試） | 無 |
| **Token-efficient Daily Runner 重構** | daily 的 token 成本 | 單次 daily run token 用量下降且產出不變。**動工前先量現值**，否則無從比較 | 先量 baseline |
| **Workstream B：Paywall ROI／合法手動入口** | 付費來源何時值得買、合法人工取得路徑 | 產出「已遇到的 paywall 清單＋各自 exact 金額與方案」，使用者可逐項核可（`AGENTS.md`：任何新訂閱須另列 exact 金額） | 無 |
| **Sheet writer** | 現行所有 runtime 都不寫 Google Sheet | ⚠ **需求尚不具體。動工前先確認要寫什麼欄位、為什麼不能唯讀**；在那之前維持不做 | 需求具體化 |
| **Confidence 五軸重構為三類**（否決／信心／賠率） | [`confidence-axes`](brainstorms/2026-08-02-confidence-axes-restructure-requirements.md) §4 | **部分已被 §4 第 4 步取代**（`unknown → 0`、`corroborated + missing_data` 懲罰）。剩餘未解的是「賠率類」維度——目前完全不存在，且如何量化尚未決定（見該檔 §6「尚未決定」） | §4 第 4 項完成後**重評是否仍需要** |
| ~~`execution_fx_missing`／`live_nav_missing` 未登記，導致無事可決的 cohort 每天照問~~ **（2026-08-19 結案：「每天照問」不是 bug，不需修）** | **這條在同一天被診斷錯三次，全部是「查驗工具本身有問題，卻信了它的輸出」，留著當範例。** ①「`blockers=[]` 被 `todo.py:1448` 判成非純系統」——錯，實測 [167] meta 的 `card.blockers` 有 7 個碼；我只看 `sizing` 的 `assessment_blockers`／`paper_blockers` 全空就推論 item 也空。②「`execution_fx_stale_since_decision` 掉進 `execution_` prefix 被判 `awaiting_external`」——錯，它**早就以 exact prefix 登記為 `system_internal`**；我的檢查腳本取「第一個 prefix 匹配」而非登記表 `_matching` 規定的**最長匹配**，於是自製了一個不存在的 bug（補了條目才被 `test_registry_is_the_single_source_of_severity` 以「重複 key 73≠72」擋下）。③ 隱含假設「補登記就會讓它們退場」——錯。**真正原因是 `evidence_delta == "material"`**：collector 有一行刻意的 `not material_event`，語意是「有觸及 thesis 因果結構的新證據時，不得因為同時有 stale 診斷而被吞掉」。那是**正確設計**，且通過 L14 恆亮測試（實測 11 個 item：material 6／none 4／peripheral 1，有鑑別力）。**用原始 config 實測：meta／sivers 的 `system_internal_only` 本來就是 `True`**，登記表沒問題 | 不需修，config 改動已還原。唯一屬實的遺漏是 `execution_fx_missing`／`live_nav_missing` 沒有 exact 條目（落入泛用 `execution_` prefix → `awaiting_external`），但**補了也是 0 筆變化**（material 優先），依 L14 不做。要動必須先出現「只有 stale／execution blocker 且無 material evidence」的真實 cohort | 已關閉 |
| `_only_system_internal_blockers` 的空集合分支語意可疑（`if not codes: return False`） | 空 blockers 意味著「什麼都沒卡住」，卻走「非純系統內部」分支。**但 2026-08-19 全面檢查 11 個 brief item，沒有任何一個的 `blockers` 是空的**——這個分支目前無實例 | ⚠ **依 L14 不得動它**：改了會讓 0 筆資料變化，且風險不對稱——`action=REVIEW` 有兩個與 blockers 無關的來源（`disproof_triggered` → `urgency=within_48h`、`lifecycle.status ∈ {rejected,expired}`），把空集合改成「不必問」會把 L7 的火警警報藏掉。要動它必須先讓 REVIEW 的原因出現在 item 自己的證據欄位裡（L12 末尾的「因果被截斷」） | 先出現真實實例 |
| **`_safe_timestamp` 的本機時區測試在 Windows 上等於不存在** | `tests/test_engine_d_runtime.py::_local_timezone` 靠 `TZ` 環境變數 ＋ `time.tzset()`，兩者都只在 POSIX 有效。主要開發機是 Windows，於是 2026-08-18 之前它是**硬失敗**（`pytest -x` 停在此處，後面 test 等於沒跑），現已改成明確 skip。但 skip 不等於已驗證——date-only → 本機午夜這條路徑在唯一實際執行它的平台上沒有測試覆蓋 | `_safe_timestamp` 可注入時區（或測試改用可控的 tz 物件而非 process 全域狀態），且該測試在 Windows 上**實際執行並通過**，不是 skip | 無 |
| ~~🔴 `financial_snapshots.price` 取自 `yfinance.info`，且 `bar_date` 是憑空生成的~~ **（2026-08-19 撤回：此 bug 不存在）** | 原條目（2026-08-18 寫入）宣稱 COHR 的 `bar_date=2026-08-17` 是 ETL 憑空生成、`price=351.22` 對不上任何收盤。**逐項複核後三個前提全錯：**（a）08-17 是**星期一**，正常交易日，原文「週五 08-14 → 週二 08-18」漏掉了它；（b）`yf.Ticker('COHR').history()` 實測**有** 08-17 那根 K 線，收盤 `351.220001`——就是 Engine C 記的值；（c）ETL 讀的是 `currentPrice`／`regularMarketPrice`，不是 `previousClose`，且 `_bar_identity()` 的 docstring 明講只取 provider 明示欄位（`regularMarketTime`＋`exchangeTimezoneName`＋`marketState`）、**不做推斷**、欄位缺就回 `None`。**抓取時戳佐證：**該筆 `fetched_at=UTC 2026-08-17 22:33`＝美東 08-17 18:33（收盤後）＝台北 08-18 06:33（daily 排程），所以 `snapshot_date=08-18`（台北日）配 `bar_date=08-17`（美東交易日）是 2026-08-14 拆開兩者的**設計本意**。原始現象（使用者 08-18 以 316.23 成交 vs 系統顯示 351.22）的真正原因是**當天 COHR 跌 12.7%**（351.22 → 306.43，盤中低 305.50），不是資料污染。「+17% → +33%」也不是錯誤被修正，而是 as-of 從 08-17 收盤換成 08-18 盤中的**必然差異**。⚠ 誤判發生在**盤中**（對話時間台北 08-18 22:00＝美東 08-18 10:00，開盤半小時）：此時 `history()` 最後一根是進行中的 bar，初版寫的「08-18 收 309.00」是把即時價當收盤（實際收 306.43）。錯的**不是觀察是推論**——從「history 沒顯示 08-17」跳到「08-17 不是交易日」，正是 L15 第 5 點「我找不到 ≠ 它不存在」，而這裡一本日曆就能否證 | 不需修。⚠ **原本擬議的「ETL 加交叉驗證：info 與 history 不一致就 quarantine」不得實作**——它會把完全正確的資料 quarantine 掉，正是 L15 說的「gate 攔下的不是它想攔的東西」 | 已關閉 |
| **`current_holdings` 用裸 `except Exception` 壓平所有失敗** | `engine_d_runtime/adapters.py` 的 `current_holdings` 把「Sheet 真的沒有持股」「網路讀不到」「憑證失效」全部收斂成同一個 `holdings_unavailable`（L12 一表兩義）。下游只能二選一，而兩邊都錯。2026-08-17 花了數步才確定是沙箱無 egress 而非設定問題 | 三種情形產生可區分的 blocker／診斷欄位，且至少一個既有測試能分辨「空持股」與「讀取失敗」 | 無 |
| **`checkpoint_decision_review` 的 completed 路徑非原子，裸 decision id 會造成 pool 與 work order 脫鉤** | `engine_b/todo.py::checkpoint_decision_review` 用 `receipt.removeprefix("decision:")` 查 decision，**裸 `pd_*` 與 `decision:pd_*` 都查得到**，於是裸 id 能通過前半段驗證並**先執行** `store.transition_research_work_order`（寫進 DB），但函式最後的 `resolve()` 走 `_validate_go_receipt`，那裡要求 `receipt.startswith("decision:pd_")` → 拋錯 → pool 不存檔。結果是 **work order 已 completed、todo item 仍 awaiting_approval**，且後續用正確格式重試會被「illegal transition: completed -> completed」擋死，CLI 再也修不回來。2026-08-19 實測踩到（[166]），最後靠直接呼叫 `todo.resolve()` 補 pool 端才收斂。這是 L12 的變體：同一個 receipt 字串在同一支函式裡被兩套規則解讀，寬的那套先產生副作用 | 用裸 `pd_*` 呼叫 `todo work <n> --to completed` 時，**work order 狀態不變**（在 transition 前就被拒），且 pool 與 work order 不會出現不一致；可寫成測試 | 無 |
| **待辦池沒有 evidence conflict 類型，未解 conflict 無人提起** | `engine_b/todo.py` 的 `ITEM_TYPES` 九種裡沒有 edge conflict。2026-08-18 那兩個 conflict 是入圖後**順手**發現的（其中一個推翻了同輪自己剛寫進去的 `substitutability=4`——把「找到 AXT 這個新供應來源」誤讀成「對 InP 的依賴變可替代」，而該 quote 語意正好相反）。若沒注意到，它們會一直開著、那幾條邊一直缺屬性，daily brief 不顯示、pq2 拿不到編號 | ⚠ **依 L14，動手前要先答出「這會讓哪個數字變」，而現在答案是 0**：2026-08-19 實測 `query.edge_conflicts` 列出 22 個 conflict，`library/resolutions/` 有 22 個 resolution，兩集合**完全相同 ⇒ 目前 0 個真正 open**。**先累積幾輪 drain 的 conflict 產生率與平均滯留時間**，有非零滯留才實作；否則就是替不存在的問題加機制 | 先量 conflict 產生率 |

**M1 研究遺留（仍開）：**

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| TSEM intake（`ra_2bf1494b`）2027–29 光通訊集體擴產 oversupply watch | 供給側擴張正是 AXT v4 由偏多轉謹慎偏空的同一主軸 | 圖中出現可支持／反駁 oversupply 的 dated claim ≥1，或明確結案為「本輪無新證據」 | 無 |
| MACOM／Semtech 作為 Tower TIA 客戶 | tier 3，待客戶端揭露印證（L8） | 取得客戶端一手揭露 → 升 tier 入圖；**或**判定「對方結構上不會揭露」→ 標為永久 tier 3 並停止重試（見 §1 D4） | 無 |
| GF 對 Tower 專利訴訟未追源 | M1 遺留 | 追到一手訴狀／法院文件，或確認公開管道不可得並記錄 | 無 |

**看起來像缺口但不是——請勿「修正」：**

- **5 個 cohort 的最新 `expiry` 仍是 `+72h` 預設值，不要去清。**
  2026-08-19 全庫掃描：16 個 cohort 中有 5 個（4 個無 ticker 的歷史 cohort ＋ LITE 的舊
  重複 cohort `dc_ebaf2286`）最新 assessment 的 expiry ＝ `created_at + 72h`，是
  2026-08-15 修復前的遺留。**但它們的 lifecycle 全部已 `expired`，且 `catalyst_watch`
  根本不顯示它們**（無 ticker 者 `company_id IS NULL` 被查詢排除；LITE 因同 company_id
  去重只取最新的 `dc_4d28e508`）。依 L14，修它們會讓 **0 筆**下游資料變化。
  根因（reassess 未帶 `--expiry` 時回退成 policy 三天預設，把財報里程碑改造成假急件）
  已由 `300b8e0`（2026-08-15 05:19 UTC）修復，並有 `tests/test_operational_workflow.py:399`
  防迴歸；逐筆核對修復後只剩兩筆 `+72h`，兩筆都是**新建 cohort**（無舊值可繼承），屬正常。


- **Beta 例行成交不進 Engine D 的 `record-fill`，這是設計正確。**
  `record_live_fill` 要求的不只是 `decision_id`，而是一整條責任鏈：
  decision → `record-choice`（使用者明確接受某個部位大小）→ fill，並驗證成交時間
  不早於 choice、幣別符合凍結 context 的執行身分。目的是回答「Engine D 的建議準不準」。

  Beta 例行投入沒有 decision、沒有支持區間、沒有接受動作——**它是時間表不是決策**。
  硬塞進去要替每筆投入捏造 decision，後果是 Decision Store 被假決策汙染、
  outcome attribution 變成把 QQQ 漲跌歸因給「今天是 15 號」、以及同一筆成交
  出現在兩處成為第二個真相來源。且 2026-08-01 已實測 beta 訊號 0 勝 3 敗，
  替它建 attribution 是測量已知無效的東西。

  **正確分工：** beta 例行成交 → `library/trades/trade_log.jsonl`（事件紀錄）；
  alpha thesis 驅動成交 → 未來同時進 trade_log 與 Engine D fill。

  **真正待補的是後者。** ⚠ **2026-08-19 更正：本段原寫「`live_choices`／
  `live_execution_reports` 仍為 0 筆——live 這條路徑從未被走過」，該陳述已過期。**
  實測：`live_choices` 1 筆（`lc_734a39a6`，COHR 10 股、`selected_weight=0.00732`、
  `choice_type=user_sized`，系統當時 supported upper 僅 0.002）、
  `live_execution_reports` 1 筆（`lf_92aede7e`，`ib-cohr-2026-08-18-10sh`，
  10 股 @ USD 316.23），**2026-08-18 已首次走完 decision → choice → fill 全鏈**。
  `paper_events` 已於 2026-08-08 首次寫入。
  📌 教訓：本檔的「目前為 0 筆」型陳述會過期，引用前必須查 DB 而非引用本檔——
  2026-08-19 就有一次直接引用本段過期文字對使用者說「這條路徑從未被走過」，
  而一個 `select count(*)` 即可否證（L11 第 2 點：別對外部 claim 嚴、對自家文件鬆）。
  2026-08-15 起 `live_supported_range` 首次出現非零（AXT／LITE，各 `(0, 0.002)`），
  但兩筆的 intent 都是 paper、`live_status` 仍為 `NOT_REQUESTED`，
  `record-choice` 依舊無從執行。等真正要下第一筆 Engine D 驅動的 alpha 單時再加
  `record_trade.py --decision-id`，那時需求才具體；現在補等於對沒跑過的路徑猜規格。
  **解除條件是資本表達層 workstream（見「進行中」），不是補這支腳本。**

**已知未修的操作缺陷：**
- 同一公司可能同時存在 claim-keyed 與 company-keyed 兩個 cohort（2026-07-30 [74]／[75] 實例）；Decision Store append-only，不做破壞性去重

---

## 什麼值得開發 / 什麼交給 Claude

### 值得開發（邊際效益高、省 token、跨 session 有用）

| 類別 | 具體項目 | 理由 |
|------|---------|------|
| 知識累積 | 更多公司 onboarding、更多高品質文件 | 圖的大小決定回答的深度 |
| Skill 介面 | SKILL.md 檔（已有 8 個）| 讓 Claude Code / Codex 每次都能正確使用記憶 |
| 高槓桿 fetcher | EDGAR 季報自動更新、arXiv 論文抓取 | 減少人工取文件摩擦 |
| G5 L8 偏誤檢查 | `validate.py` 加 origin_entity 同質性警告（2026-07-17 已實作：供應商自報 sole_source 在文件層 WARN） | 低工程量、高資料品質槓桿 |

### 不值得自己開發（Claude 做得更好或沒意義）

| 類別 | 理由 |
|------|------|
| 長文解讀、文章分析 | Claude 的 context window + 推理比自製 pipeline 好 |
| Text2Cypher / 對話式查詢 | 直接給 Claude 原始 graph context，Claude 自己解讀 |
| 自動選文件頁面（G2）| Claude 看 TOC 判斷比 embedding filter 更準確 |
| 節點重要性評分（G8）| Claude 從 edge 數量、tier、公司規模能即時判斷 |
| 公司識別（G1）| Claude training data 知道公司是誰，hallucination 風險由 TICKER_MAP 控制 |
| 自動代替使用者做最終投資決定或送單 | Engine D 可以提出有邊界的建議與 paper counterfactual，但 live 接受、覆寫與 broker 下單永遠需要人工 |

---

## 已 brainstorm 但未實作

需求已想過、盲點已審過，但沒開 plan。要動工先回去讀該 brainstorm，不要重新發明。

出自 [`2026-07-26-next-phase-operating-model-requirements.md`](brainstorms/2026-07-26-next-phase-operating-model-requirements.md)，該檔明載「只有重複摩擦出現時才另立 plan」：

- **Workstream B：Paywall ROI／合法手動入口** — 付費來源何時值得買、以及合法的人工取得路徑
- **Token-efficient Daily Runner（通用 daily runner 重構）**
- **ETF 完整 look-through** — 目前 `issuer_loads` 只涵蓋 policy 已登記的 ownership，輸出必標 `partial`
- **Sheet writer** — 現行所有 runtime 都不寫 Google Sheet
- **本機 single-writer guard** — 目前靠人工紀律確保同一 working tree 只有一個 agent 寫入

出自 [`2026-07-31-leverage-glide-path-requirements.md`](brainstorms/2026-07-31-leverage-glide-path-requirements.md)：

- 總曝險硬擋與自有現金固定例行提醒已於 2026-08-01 完成。
- 唯一剩餘的**貸款提款時間表**由使用者明確暫緩；目前不預期這麼早手動投入貸款，
  未來若重啟再核准 exact 日期／金額／標的／tranche。glide path 公式亦延後，現況資源尚不構成綁定。

出自 [`2026-08-13-capital-expression-direction-requirements.md`](brainstorms/2026-08-13-capital-expression-direction-requirements.md)
— **要動資本層先讀這份，它取代 `confidence-axes` §7 的順序判準**：

- **方向已定案（D1–D7）**：研究是手段不是目的；不確定性用尺寸承擔不用 gate 禁止參與；
  診斷與閘門分離（49 個 blocker 全留當診斷，只有講得出因果機制的能歸零）；證據標準
  校準到個人投資者可達成的補救；alpha 需要 baseline（beta 已有 `baseline_pace`，
  alpha 從未 port）；**gate 本身也不得未經量測就享有默認信任**；先量測後放閘。
- **§2 凍結了 2026-08-13 的 baseline 數字**，未來 audit 拿它做 diff 而非做判斷。
  關鍵三項：`live_supported_range` 非零 **0/72**、`axis_ceiling` 從未達 0.005、
  已量測 outcome **0/8**。
- **§4 的六步含可證偽驗收條件**，第 1 項（補跑 7 個 cohort 的 outcome 量測）必須先做。
- ⚠ **§6 的防呆不可省略**：daily brief 需增加兩個常駐計數器，否則本檔會變成第五份
  被堆積的正確診斷（同一結論已被正確寫下四次，見該檔 §0）。

出自 [`2026-08-02-confidence-axes-restructure-requirements.md`](brainstorms/2026-08-02-confidence-axes-restructure-requirements.md)：

- **Confidence 五軸重構為三類（否決／信心／賠率）** — 現行五軸全在問「證據多強」，
  高度相關又取 min，等於最弱那份文件決定一切；且完全沒有賠率維度，系統只能用
  「不參與」表達不確定性。提議拆成二元否決類、序數信心類、連續賠率類。
- 該檔的**最小改動已於 2026-08-02 交付**：coverage blocker 依嚴重度分成「致命（仍歸零）」
  與「研究不完整（只降尺寸）」，讓 `axis_ceiling` 得以生效。動軸結構前先跑一兩週看樣本
  品質——若變成可評估的標的其實不值得看，問題在 pq1 選題而不在 gate。
- 動工前必讀該檔第 6 節：`closed-vocabulary-registry.md` 仍把五軸列為「刻意凍結」，
  但那個理由已因 `rubric_version` 版本化而失效，需一併更新登記表。

其餘五份 brainstorm 的主體都已交付（見上方表格），保留作需求推導的歷史。

---

## 未來想法（尚未承諾）

### ⚠ 2026-07-31 回測發現：以「等回檔才投入」決定是否進場，對 30 年累積目標是負貢獻

把現行 `signal_state` 的 gate 邏輯拿去跑 2015-08 ~ 2026-07（128 個月，每月 $1,000）：

| 標的 | A 無腦每月定投 | B 只在 gate 觸發時投入 | B/A |
|---|---|---|---|
| QQQ | $394,034 | $360,533 | **91.5%** |
| SOXX | $820,624 | $754,498 | **91.9%** |

兩個標的都輸約 8.5%。原因是市場多數時間在漲，等回檔＝在上漲期間抱現金；
即使現金最終幾乎都投出去（殘餘僅 $5–9k），時點延後就損失複利。

觸發頻率本身不是問題（QQQ 9.5%、SOXX 14.4% 的交易日），問題是**逐年極度不均**：
2017 年 QQQ 觸發 0 天、2021 年 1 天，2022 年 127 天。在強多頭年份幾乎完全不進場。

**限制：** 這是單一路徑、兩個標的、且 2015–2026 是異常強的多頭。方向與已知證據一致
（Vanguard 2012：一次投入在約 68% 的 12 個月期間勝過分批），但不足以當定論。

**問題不在訊號，在它被用來決定「要不要投」。** AGENTS.md 寫的是「technical signal
只決定新增 timing／pace」，但實作上 pace=0 會讓 `supported_order_range` 歸零，
輸出讀起來就是「今天不要投」。

**建議方向（未實作）：** 把 gate 從「是否投入」改成「投給誰」。
1. 基準永遠投入——固定月投不受訊號影響，這是時間複利的來源
2. 訊號只決定**這筆錢分配給哪個候選標的**（誰最接近趨勢／回撤最深）
3. 若要保留逆勢加碼，用**再平衡帶**（目標權重＋偏離門檻）而不是技術訊號——
   它天生就會在下跌後買進，且不需預測

---

### 2026-07-31 回測：深跌加碼槓桿 ETF 的真實效果與其致命限制

使用者要求「跌深多買、以槓桿 ETF 放大」。實測（真實 TQQQ 2010-02~2026-07，198 個月 × $1,000）：

| 策略 | 終值 | vs 基準 | 觸發月數 |
|---|---|---|---|
| 全 QQQ | $1,174,561 | — | — |
| 回撤 −10% 改投 TQQQ | $2,149,786 | **183.0%** | 30/198 |
| 回撤 −20% 改投 TQQQ | $1,208,296 | 102.9% | 11/198 |
| 回撤 −30% 改投 TQQQ | $1,190,704 | 101.4% | 4/198 |

**⚠ 第一版回測是錯的，必須記下來避免重蹈。** 原本用「3×日報酬」模擬 3x 回到 1999，
得到 B/A = 724% 的驚人結果。錯誤在於：模擬淨值在 2000-2002 跌到趨近零（−100%），
而用「$1,000 ÷ 趨近零的價格」計算股數會讓股數爆炸性放大再乘回來。**那是除以趨近零
的數字產生的假象，不是報酬。** 現實中基金早已清算或反分割，無法從那裡複利回來。
任何跨越 2000-2002 或 2008 的槓桿回測都必須用真實基金資料，或明確處理清算。

**結論不是「跌越深買越多越好」，而是「2010-2026 這個 regime 裡槓桿越多越好」。**
−10% 門檻贏最多只是因為它觸發最頻繁（30 次）＝在多頭中待在槓桿的時間最長。
樣本期最大回撤僅 −35.1%，**完全不含網路泡沫等級的事件**。

**反例（決定性）：** 2000-03 ~ 2002-10，QQQ 跌 82.8%，模擬 3x 淨值剩 **0.05%**（−99.95%）。
在那個情境下「跌深加碼」不但救不回來，還會一路買到歸零。

**真正的保護來自 NAV 上限，不是回撤觸發條件。** 若槓桿 sleeve 受
`leveraged_effective_cap` 限制，即使該 sleeve 歸零，損失上限＝ nominal 權重。
2026-07-31 已設 nominal 20%／effective 40%：純 3x 時 effective 先綁定，
對應 nominal 約 13.3%，最壞情況損失約 12% NAV——痛但可存活。

**未實作的機制：** 目前每個標的各自獨立產生訊號，沒有「深跌時把資金路由到槓桿標的」
的機制。要做需新增 allocation routing，屬資本行為變更，須經 brainstorm。

### 2026-07-31 既有研究：槓桿的正確變數是「人生階段」不是「回撤深度」

搜尋後確認這題有成熟學術與實務基礎，不需自行重推。

**Ayres & Nalebuff（Yale, 2008）"Life-Cycle Investing and Leverage"**
（[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1149340)）——
用 1871 年起的資料與 10,000 次模擬，論證年輕時該用槓桿。核心不是擇時，是
**時間分散（temporal diversification）**：年輕人未來的儲蓄尚未進入市場，
等於一生的股票曝險過度集中在後期；早期加槓桿是在修正這個失衡。
結果：退休預期財富較 lifecycle fund 高 90%、較 100% 股票高 19%。

**關鍵處方與本專案原構想的差異：**
- 槓桿倍數是**距離目標的函數**（三階段 glide path：0–50% 目標用 2x，之後遞減），
  **不是回撤深度的函數**
- 他們明確**上限 2x，不是 3x**

**實務 out-of-sample：HFEA（UPRO/TMF 55/45，3x）** —— 2010–2021 表現優異，
**2022 崩潰**：升息使股債同向下跌，risk parity 的對沖正好在最需要時失效，
最大回撤逾 70%。這是 3x 長抱最接近真實的自然實驗，結論是「在某個 regime 有效」
而非「長期必然有效」。

**波動耗損直觀例子：** 先漲 10% 再跌 10%，QQQ 損失 1%、TQQQ 損失 **9%**（不是 3%）。

**對本專案的意涵（未實作）：** 若要提高槓桿參與度，依研究應調整的是
**依距離退休目標的 glide path**，而非回撤觸發門檻；且總曝險上限宜參考 2x 而非 3x。
現行 `leveraged_effective_cap` 只涵蓋槓桿 ETF，不等於總投組股票曝險，
兩者不可直接比較——要導入 glide path 需先定義總曝險口徑。

### 其他想法

記在這裡的東西**不是待辦**，是「想清楚了但還沒決定要不要做」。要動工才升格成上方表格或開 plan。

#### Parked lead 的第二層召回

現況：`engine_b/entities.py` 以具名標的（cashtag、`edgar:<TICKER>` 結構化 source、registry 反查的 `co:*`）做**確定性**比對，精準度高但召回率有限——主題相關卻沒有共同 ticker 的關聯抓不到（例如「FCC 禁中國 humanoid」對上「Agility 上市」）。

三個層級，成本由低到高：

1. ~~**主題關鍵字比對**~~ — **2026-07-31 已實作**（`engine_b/themes.py`）。`config/themes.txt` 補上 robotics 主題後，FCC 那則 parked lead 從只能接上 8 筆（共用 ticker）變成 14 筆（共用主題）。反證關鍵字同樣標記該主題並另旗標，因為反面證據要找得到而不是被過濾掉（L7）。
2. **Embedding 相似度** — 理論上召回最好，但引入模糊比對、模型依賴與門檻調校。**代價要誠實計算**：false positive 消耗的是使用者注意力，而降低注意力噪音正是 2026-07-30 那輪重構的目的。若要做，應該只當「排序提示」而非「自動 retrigger」，並且先量測目前漏掉多少關聯，再判斷值不值得。
3. **事件觸發自動化** — `trace_next_trigger` 目前是自由文字，從來沒有被程式評估過。要讓「FCC 規則公布」真的自動 un-park，得先把它變成登記過的 code（像 `config/decision_blockers.json` 那樣），才能程式比對。

判準與封閉字彙表同一條：**會改變決策的事實不能只住在自由文字裡。** `trace_next_trigger` 現在正好違反這條。

#### lead `refs` 是未登記字彙

~~2026-08-01 實測：`refs` 有 56 個不同鍵名，拼錯會靜默失效。~~ **已實作：**
`config/lead_ref_keys.json` 已盤點並登記全部 56 個既有鍵與 value type；`annotate`／`advance`
拒絕未登記鍵，近似拼錯會提示已知名稱。既有歷史資料保持可讀。

#### 其他

- **技術指標擴充**（相對強弱 vs QQQ、ATR）— `engine_c/technical.py` 的 `_METRIC_COLUMNS` 寫死且是 DB 欄位，需配 migration
- **Engine D 未上市公司支援** — 2026-07-30 使用者定案暫不做。現況：`research_ticker` 屬核心 identity 欄位，缺它整組 fallback 成 unresolved 並丟掉 `company_id`，導致未上市公司無論圖品質多好都撞 `identity_unresolved`＋`graph_company_missing`。Lane Memo 不受影響（`thesis/generate_lane_memo.py` 完全不經過 Engine D，`--ticker` 為選用，無 ticker 走「產業全圖模式」）
- **灌文件提升圖深度** — 2026-07-30 實測：53 家公司、63 份 SourceDoc，僅 3 家（Coherent、Sivers、AAOI）有 ≥3 distinct origin 可過 L8。**擋住 Lane Memo 的是證據深度不是 gate 嚴格度**；一家從 1 個 origin 到 3 個約需 2–3 份文件，零架構風險
