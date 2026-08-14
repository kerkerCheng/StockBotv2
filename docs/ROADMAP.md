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

## 已交付

> **記錄實測 before → after，不只記「做了什麼」。** 一個改動若說不出哪個現有數字變了，
> 它與沒做在結果上不可區分（`AGENTS.md` L14 第 1 條）。翻歷史時要看得出哪些是真交付、
> 哪些是白工——2026-08-02 至 08-08 的四次「已實作但供給為零」如果當初這樣記，
> 第二次就會被抓到。

| 完成日 | 項目 | 歷史 plan |
|--------|------|-----------|
| 2026-08-14 | **資本表達層 workstream（§4 六步完成 5 項）** — outcome 量測 0→7/7（AXTI +83.5%、超額 QQQ +76.4%）；blocker severity 移進 config ＋ lane 維度，live 非零 0→8、binding 由 `live_lane_blockers` 71/72 變成 `weakest_axis` 31；引用無歧義解析＋「至少一個合格」，`axis_ceiling==0` 23→17；催化劑排程使 AXT 複查日 2026-11-15→2026-10-30；daily brief 兩個常駐計數器上線 | [方向與 baseline](brainstorms/2026-08-13-capital-expression-direction-requirements.md) |
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

目前唯一 workstream：**資本表達層**——把 Engine D 從「永遠不下注」變成「小注但有意義」。

| 內容 | 位置 |
|---|---|
| 方向（D1–D7） | [`2026-08-13-capital-expression-direction`](brainstorms/2026-08-13-capital-expression-direction-requirements.md) **§1** |
| 凍結的 baseline 數字（audit 拿它做 diff） | 同檔 **§2** |
| **六步工作清單＋各步驗收條件** | 同檔 **§4** |
| 明確待驗證、尚不得當結論 | 同檔 **§5** |

**步驟表只有一份，在該檔 §4，本檔不複製**（複製會漂移）。

**下一步 = §4 第 1 項**：對 7 個有 shadow 錨點的 cohort 補跑 outcome 量測（唯讀報表，
不 close cohort、不動 authority）。驗收：報表出現 ≥5 筆非 null `absolute_return`，
且 AXTI 相對 $42.76 顯示約 +85%。

⚠ **§4 第 1 項必須先於第 3、4 項**（先量測後放閘，見該檔 D7）。

### 未排程

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| **`AGENTS.md` L1–L14 整理** | 14 條含重複（L2／L3 近乎同義）、已完成的考古（L6 Gap 1–3 已修、L9 三前置已由 `thesis/preconditions.py` 機器強制，散文只是重複程式碼）、與已定案不會再翻的（L1 選型、L5 評估）。每條都在花掉**每一個** session 的 context | lessons 段落行數下降，且 L6 Gap 4／L8／L11／L12–L14 的區辨仍在。⚠ **不得刪掉任何仍會改變行為的判準**；L12／L13／L14 是三個不同時刻（表示層／驗收層／信任層），不合併 | §4 第 1 項 |
| **Engine C `snapshot_date` 語意錯誤** | 2026-08-13 查證：該欄是「跑 ETL 的日期」不是行情交易日。收盤後跑的批次被標成隔天（`fetched_at` 07-28 22:34 取到 07-28 收盤 42.76，標成 `snapshot_date=07-29`），盤中跑的則存盤中價——一個欄位三種語意（L12）。任何拿它當 as-of 的消費者都系統性差一天，point-in-time 重建全部失準 | 分離成 `bar_date`（行情交易日）與 `fetched_at`（既有），並標記 intraday 與 close 兩種 `price_kind`；驗收＝拿現有 AXTI 序列重放，`bar_date` 與 provider 收盤日逐日對得上 | 無 |
| **Engine D cohort 重複** | 同公司可能同時存在 claim-keyed 與 company-keyed 兩個 cohort（2026-07-30 [74]／[75] 實例） | 新建 cohort 時偵測同公司既有 cohort 並警告。**不回溯清理**——Decision Store append-only，不做破壞性去重 | 無 |
| **6 個 `unavailable` Shadow 錨點回填** | 13 個 cohort 有 6 個 shadow 是 `unavailable`（含 2026-08-12 建立、明明有 `research_ticker` 的 LITE 與 NVDA）。錨點是**可重建**資料（L14／D17），今天仍查得到，卻被當 point-in-time 凍結 | 回填後 `scripts/outcome_if_settled_today.py` 的「已量測」從 7/13 上升 | 無 |
| **ETF 完整 look-through** | `issuer_loads` 只涵蓋 policy 已登記的 ownership，曝險輸出恆為 `partial` | 曝險輸出出現 `coverage: full` 的標的 ≥1 | 無 |
| **本機 single-writer guard** | 目前靠人工紀律確保同一 working tree 只有一個 agent 寫入 | 模擬兩個 writer 併發時會被擋下（可寫成測試） | 無 |
| **Token-efficient Daily Runner 重構** | daily 的 token 成本 | 單次 daily run token 用量下降且產出不變。**動工前先量現值**，否則無從比較 | 先量 baseline |
| **Workstream B：Paywall ROI／合法手動入口** | 付費來源何時值得買、合法人工取得路徑 | 產出「已遇到的 paywall 清單＋各自 exact 金額與方案」，使用者可逐項核可（`AGENTS.md`：任何新訂閱須另列 exact 金額） | 無 |
| **Sheet writer** | 現行所有 runtime 都不寫 Google Sheet | ⚠ **需求尚不具體。動工前先確認要寫什麼欄位、為什麼不能唯讀**；在那之前維持不做 | 需求具體化 |
| **Confidence 五軸重構為三類**（否決／信心／賠率） | [`confidence-axes`](brainstorms/2026-08-02-confidence-axes-restructure-requirements.md) §4 | **部分已被 §4 第 4 步取代**（`unknown → 0`、`corroborated + missing_data` 懲罰）。剩餘未解的是「賠率類」維度——目前完全不存在，且如何量化尚未決定（見該檔 §6「尚未決定」） | §4 第 4 項完成後**重評是否仍需要** |

**M1 研究遺留（仍開）：**

| 項目 | 為什麼 | 驗收條件 | 前置 |
|---|---|---|---|
| TSEM intake（`ra_2bf1494b`）2027–29 光通訊集體擴產 oversupply watch | 供給側擴張正是 AXT v4 由偏多轉謹慎偏空的同一主軸 | 圖中出現可支持／反駁 oversupply 的 dated claim ≥1，或明確結案為「本輪無新證據」 | 無 |
| MACOM／Semtech 作為 Tower TIA 客戶 | tier 3，待客戶端揭露印證（L8） | 取得客戶端一手揭露 → 升 tier 入圖；**或**判定「對方結構上不會揭露」→ 標為永久 tier 3 並停止重試（見 §1 D4） | 無 |
| GF 對 Tower 專利訴訟未追源 | M1 遺留 | 追到一手訴狀／法院文件，或確認公開管道不可得並記錄 | 無 |

**看起來像缺口但不是——請勿「修正」：**

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

  **真正待補的是後者**，但 `live_choices`／`live_execution_reports` 仍為 0 筆
  （`paper_events` 已於 2026-08-08 首次寫入，現 4 筆 × 0.1% NAV）——live 這條路徑
  從未被走過，72 筆 decision 的 `live_supported_range` 全為 0，連 `record-choice`
  都無從執行。等真正要下第一筆 Engine D 驅動的 alpha 單時再加
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
- **Engine D 未上市公司支援** — 2026-07-30 使用者定案暫不做。現況：`research_ticker` 屬核心 identity 欄位，缺它整組 fallback 成 unresolved 並丟掉 `company_id`，導致未上市公司無論圖品質多好都撞 `identity_unresolved`＋`graph_company_missing`。Lane Memo 不受影響（`generate_lane_memo.py` 完全不經過 Engine D，`--ticker` 為選用，無 ticker 走「產業全圖模式」）
- **灌文件提升圖深度** — 2026-07-30 實測：53 家公司、63 份 SourceDoc，僅 3 家（Coherent、Sivers、AAOI）有 ≥3 distinct origin 可過 L8。**擋住 Lane Memo 的是證據深度不是 gate 嚴格度**；一家從 1 個 origin 到 3 個約需 2–3 份文件，零架構風險
