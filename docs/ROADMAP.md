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

**目前沒有進行中的 plan。** 七份 brainstorm 中仍有未實作項目，見下方「已 brainstorm 但未實作」。

---

## 已交付

| 完成日 | 項目 | 歷史 plan |
|--------|------|-----------|
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

**Engine D 仍未包含：** notification、remote Decision MCP、broker routing。

---

## 開放 backlog

**M1 遺留（仍開）：**
- TSEM intake（`ra_2bf1494b`）的 2027–29 光通訊集體擴產 oversupply watch
- MACOM／Semtech 作為 Tower TIA 客戶（tier 3，待客戶端揭露印證）
- GF 對 Tower 專利訴訟未追源

**已知未修的操作缺陷：**
- `harvest_x` 不分頁，長時間未跑後可能永久漏掉中間批次（見 [`OPERATIONS.md`](OPERATIONS.md)）
- `decision_review` 若研究已完成但 work order 已 terminal，狀態機沒有 `go` 路徑，只能 `pending`（2026-07-30 [64] 實例）
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

其餘五份 brainstorm 的主體都已交付（見上方表格），保留作需求推導的歷史。

---

## 未來想法（尚未承諾）

記在這裡的東西**不是待辦**，是「想清楚了但還沒決定要不要做」。要動工才升格成上方表格或開 plan。

### Parked lead 的第二層召回

現況：`engine_b/entities.py` 以具名標的（cashtag、`edgar:<TICKER>` 結構化 source、registry 反查的 `co:*`）做**確定性**比對，精準度高但召回率有限——主題相關卻沒有共同 ticker 的關聯抓不到（例如「FCC 禁中國 humanoid」對上「Agility 上市」）。

三個層級，成本由低到高：

1. ~~**主題關鍵字比對**~~ — **2026-07-31 已實作**（`engine_b/themes.py`）。`config/themes.txt` 補上 robotics 主題後，FCC 那則 parked lead 從只能接上 8 筆（共用 ticker）變成 14 筆（共用主題）。反證關鍵字同樣標記該主題並另旗標，因為反面證據要找得到而不是被過濾掉（L7）。
2. **Embedding 相似度** — 理論上召回最好，但引入模糊比對、模型依賴與門檻調校。**代價要誠實計算**：false positive 消耗的是使用者注意力，而降低注意力噪音正是 2026-07-30 那輪重構的目的。若要做，應該只當「排序提示」而非「自動 retrigger」，並且先量測目前漏掉多少關聯，再判斷值不值得。
3. **事件觸發自動化** — `trace_next_trigger` 目前是自由文字，從來沒有被程式評估過。要讓「FCC 規則公布」真的自動 un-park，得先把它變成登記過的 code（像 `config/decision_blockers.json` 那樣），才能程式比對。

判準與封閉字彙表同一條：**會改變決策的事實不能只住在自由文字裡。** `trace_next_trigger` 現在正好違反這條。

### 其他

- **技術指標擴充**（相對強弱 vs QQQ、ATR）— `engine_c/technical.py` 的 `_METRIC_COLUMNS` 寫死且是 DB 欄位，需配 migration
- **Engine D 未上市公司支援** — 2026-07-30 使用者定案暫不做。現況：`research_ticker` 屬核心 identity 欄位，缺它整組 fallback 成 unresolved 並丟掉 `company_id`，導致未上市公司無論圖品質多好都撞 `identity_unresolved`＋`graph_company_missing`。Lane Memo 不受影響（`generate_lane_memo.py` 完全不經過 Engine D，`--ticker` 為選用，無 ticker 走「產業全圖模式」）
- **灌文件提升圖深度** — 2026-07-30 實測：53 家公司、63 份 SourceDoc，僅 3 家（Coherent、Sivers、AAOI）有 ≥3 distinct origin 可過 L8。**擋住 Lane Memo 的是證據深度不是 gate 嚴格度**；一家從 1 個 origin 到 3 個約需 2–3 份文件，零架構風險
