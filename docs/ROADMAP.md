# StockBotv2 — Roadmap

> **本檔只放 active future work。** 判準與契約在 [`AGENTS.md`](../AGENTS.md)；
> 指令與程序在 [`OPERATIONS.md`](OPERATIONS.md)。
>
> **交付歷史、已結案項目與需求推導**已於 2026-09-03 移到
> [`docs/archive/roadmap-pre-alpha-refactor.md`](archive/roadmap-pre-alpha-refactor.md)（逐字保留）。
> 每一項的去向見 [`docs/refactor/roadmap-migration.md`](refactor/roadmap-migration.md)。

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

# 現行路線圖：Alpha Research Refactor

**North Star：** 系統要能回答
**「我們知道了什麼市場可能還沒有充分 pricing，以及這個 expectation gap 是否值得轉化成資本曝險？」**

```
Evidence → Knowledge → Causal Understanding → Fundamental Impact
        → Market Expectations → Variant Perception → Alpha
        → Portfolio → Capital Decision → Outcome Learning
```

三層責任不再混在一起：
**Knowledge Graph** ＝研究記憶與結構 edge｜**Alpha Research Core** ＝investment reasoning
engine｜**Engine D** ＝capital permission 與 accountability。

設計文件（動工前必讀）：
[`current-architecture.md`](refactor/current-architecture.md)（實測盤點）｜
[`target-architecture.md`](refactor/target-architecture.md)（契約與邊界）｜
[`engine-d-decomposition.md`](refactor/engine-d-decomposition.md)（逐檔搬遷）｜
[`phase-1-plan.md`](refactor/phase-1-plan.md)（施工圖）｜
**[`historical-failure-matrix.md`](refactor/historical-failure-matrix.md)（36 筆歷史事故 → 六條 hard invariant → completion gate）**

## Phase 表

| Phase | Goal | Deliverables | Exit criteria（哪個數字會變） | Dependencies |
|---|---|---|---|---|
| **0** ✅ | Architecture inventory ＋ AGENTS 分類 ＋ MCP 降級 ＋ 歷史事故矩陣 | 六份 `docs/refactor/*.md` ＋ 舊 roadmap 封存 | 六份文件邏輯一致；舊 roadmap 22 個標題都有去向判定；36 筆事故已分類 | — |
| **1** ✅ | Alpha contracts ＋ 三個防事故型別 ＋ audit 骨架 ＋ golden fixtures ＋ 舊五軸轉換 | `alpha/{contracts,causal,provider,errors,identity,testing}.py`＋`alpha/audit/`；5 個測試檔；`tests/fixtures/golden/` 14 類 | ✅ 全數達成：`alpha/` 零外部相依；**23/23 突變證明斷言會紅**；**既有 package 變更 0 行**；1,175 → **1,283 passed / 0 skipped**；golden fixtures 14/14；舊五軸 dual run 41 cohort、UNEXPECTED 0；F-20／F-25／F-31 三個 🔴 歸零 | Phase 0 |
| **2** | First research vertical slice（**標的＝COHR**） | B4：concrete `GraphResearchProvider`、LLM assessor、`python -m alpha research COHR --as-of ...` | ①每個 score 都能 explain 到 `EvidenceRef`；②圖零新增節點；③與 `rank_bottlenecks` 首選一致或能說明差異 | Phase 1 |
| **3** | Engine D decomposition ＋ `mcp_server` domain 抽出 | B2／B3／B5／B6：shared infra 升格、alpha 模組搬入、`sizing` 切三段、`brief` 拆四 pane；core → `mcp_server` import 5 → 0 | `decision_lab/` 13,502 → **≤8,000 行**；直接相依環 **3 → 0**（`engine_d_runtime`／`thesis`／`engine_c`）；daily 輸出 **bytes 下降且 pq2 項目數不減**（baseline 2026-09-02＝24,195 bytes） | Phase 2 |
| **3.5** | Portfolio / Risk 搬家（B1） | `portfolio/`、`risk/` | `decision_lab/` −2,054 行；`engine_c → decision_lab` 環消失；三個硬擋逐筆一致 | Phase 2 |
| **3.9** | **`AGENTS.md` 結構瘦身 ＋ 新增 `docs/ARCHITECTURE.md`**（一次做完） | PROCEDURE 搬 OPERATIONS／skills；L1–L16 改五欄格式；CURRENT_ARCHITECTURE 段落 → 新的 `docs/ARCHITECTURE.md`（由 `target-architecture.md` 蒸餾）；四引擎表 → 五條 authority separation | `AGENTS.md` **771 → ≤450 行**且 INVARIANT 一條未刪；16 條 lesson 全部保留且各自標明 implementation 可不可改；`grep` 不到與 `.codex/rules`／`skills/*` 重複的清單；**五份文件的任一句話都歸得到 `target-architecture.md` §17.1 的一個問句**（歸不到＝它不該存在） | Phase 3.5（boundary 定下來才動） |
| **4** | Expectation Gap | Engine C 欄位擴充（forwardEps／revenue estimate／segment revenue）、peer registry、implied fundamentals | `expectation_gap_score` 對 **≥5 檔**可算出且可 explain；低 P/E 但共識與 thesis 一致的案例 gap ≈ 0 | Phase 2 |
| **5** | Causal propagation | `StructuralEvent` → `CausalPath` → `CompanyImpact` | 對 **≥1 個真實事件**產出 **≥1 個**二階受益／受害者，路徑可追溯到 `EvidenceRef` | Phase 2 |
| **6** | Backtest / validation | as-of 圖投影、anti-lookahead 測試、epoch 錨點 | SourceDoc `published_at` 覆蓋 **83% → 100%**；EdgeAssertion 可定日比例 **58% → ≥95%**；排序前段 vs 後段等權報酬差有 **≥2 期** | Phase 4、5 |
| **7** | Portfolio / Risk 完整化 | view → target exposure → hard limits | **不新增任何 alpha 尺寸**；target exposure 可由 `AlphaSignal[]` 導出 | Phase 3.5 |
| **8** | Automation / productization | daily／weekly／skills／MCP 適配 | 16 條 sandbox rule 完成 impact review；`sync_agent_skills.py --check` 無漂移；daily 端到端綠 | Phase 3 |

### ⚠ `AGENTS.md` 的改動分兩類

**A 類——防止文件說謊，不可延後。** code 改動讓某句話變成假的，就在**同一個 commit** 改掉。
依據是 2026-08-29 實測：程式已於 `6aa31de` 拔掉 beta 訊號，三份文件卻仍在描述**已不存在的
行為**——**管子換了但說明書沒換**，下一個 session 會照著說明書把已被量測為有害的機制講回來。
逐 Phase 的小改，清單見 [`roadmap-migration.md`](refactor/roadmap-migration.md) §10。

**B 類——結構瘦身，一次做完＝Phase 3.9。** 約 310 行 PROCEDURE 搬走、L1–L16 五欄重寫、
四引擎表換成五條 authority separation。放在 3.5 之後是因為 architecture boundary 到那時
才真的定下來；更早寫的瘦身版本會在後面每個 Phase 再被改一次。

⚠ **`docs/ROADMAP.md` 本身的重構已於 Phase 0 完成**（673 → 227 行、逐字封存、22 個標題
全有去向判定）。之後只剩每個 Phase 完成時回填實測 before → after，那是維護不是重構。

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

> 現況：36 筆歷史事故中，**🔴 僅有文字保護的有 10 筆**。各 Phase 的責任分配見該檔 §9。

## 重構期間的硬約束

1. **不重建 Neo4j。** 資產是 662 條 EdgeAssertion 的 provenance，不是節點數。
2. **Decision Store schema 不動。** 268 筆 append-only 紀錄，Git 救不回（L10）。
3. **四個人工 gate 不放寬：** graph admission、Engine C 觀測寫入、thesis mutation、live。
4. **`rank_bottlenecks()` 仍是唯一排序權威。**
5. **系統仍然不給 alpha 部位尺寸**（`AGENTS.md` Alpha 呈現契約）。
6. **beta 訊號不得以任何名義復刻**（2026-08-01 實測 0 勝 3 敗）。
7. **既有 126 個測試檔全部保留**——可改 import 路徑，不可刪斷言。
8. **改任何 `python -m <module>` 命令字串前，先走 sandbox impact review 五步**——
   `.codex/rules/stockbot-automations.rules` 的 16 條 exact prefix 會靜默打斷 daily。
9. **六條 hard invariant 全程適用**（`historical-failure-matrix.md` §2）：
   IDENTITY（ticker 不是 entity identity）／LIFECYCLE（每個 active object 答得出五問）／
   **NO SILENT DROP**（「查不到了」不是合法 lifecycle）／QUEUE LIVENESS（producer 指得出
   consumer）／MEASURED GATE（未量測的機制不得享有默認信任）／POINT-IN-TIME & PROVENANCE。
10. **Core 不得 import `mcp_server`。** MCP／remote 是 optional adapter，
    依賴方向只准 peripheral → core。⚠ 今天**不是** 0：`engine_b/todo.py`、
    `query/health_audit.py`、`crons/weekly_scan_digest.py`、`scripts/*` 共 5 個消費端。
11. **Local-first：新核心必須能在完全沒有 MCP 的情況下運作。**
    若 MCP 相容性與新核心架構衝突，**優先選擇新核心架構**。
12. **`AGENTS.md` 不是憲法。** 「四引擎架構」是 CURRENT_ARCHITECTURE；
    不可變的是五條 authority separation（`target-architecture.md` §12）。
    ⚠ **lesson learned 一條都不刪**——綁定實作的改寫成
    Context → Failure → Learned invariant → Current implementation → 可改？

---

## 開放 backlog（與重構平行，可獨立進行）

| 做什麼 | 為什麼 | 驗收（哪個數字會變） | 前置 |
|---|---|---|---|
| `decision_lab today` footer 的 `live_choices=0` 與 outcome 的 1 筆 live fill 不一致 | L12 一表兩義：讀 footer 的人會以為 live 路徑從未走過，而那是 2026-08-19 已踩過的坑 | 兩個 surface 對同一 DB 回答一致 | 建議併入 Phase 3 拆 brief 時一起修 |
| `event_watches.json`／`hypotheses.json` 不在 state publisher 窄 pathset | 排程更新了 watch 狀態卻只能留本機未提交，兩個 writer 的變更混在同一份 diff | 擴 pathset 或明文定為互動側責任並寫進 OPERATIONS | 擴 pathset 需 sandbox impact review |
| `current_holdings` 用裸 `except Exception` 壓平三種失敗 | 「Sheet 真的沒持股」「網路讀不到」「憑證失效」收斂成同一個 `holdings_unavailable`（L12） | 三種情形產生可區分的 blocker，且至少一個測試能分辨「空持股」與「讀取失敗」 | 建議併入 Phase 3 拆 `engine_d_runtime/adapters.py` |
| `checkpoint_decision_review` completed 路徑非原子 | 裸 `pd_*` 能通過前半驗證並先寫 DB，最後 `resolve()` 才拋錯 → work order completed 但 todo item 仍 awaiting_approval，CLI 修不回來（2026-08-19 實測 [166]） | 用裸 `pd_*` 呼叫 `todo work` 時 work order 狀態不變；可寫成測試 | 無 |
| Engine D cohort 重複（claim-keyed vs company-keyed） | 同公司可能同時存在兩個 cohort（2026-07-30 [74]／[75]） | 新建 cohort 時偵測同公司既有 cohort 並警告。**不回溯清理**（append-only） | 無 |
| **把 `mcp_server/` 的 domain 抽出到 application layer**（新增 2026-09-03） | 實測：`mcp_server/` 4,016 行有 **79%（3,165 行）不是 MCP**——Research Action 的 domain、filesystem provenance 原語、local-only Git 發布，全被關在 transport package 裡。因此 5 個 core 消費端被迫 import 它，其中包含 pq2 待辦池本身 | `Core → mcp_server` 的 import **5 → 0**；`scripts/prepare_research_action.py` 不再呼叫私有 `_impl` 函式 | 併入 Phase 3（分類見 `target-architecture.md` §14.2） |
| **`audit invariants` runtime checker**（新增 2026-09-03） | 36 筆歷史事故有 **10 筆只有文字保護**。L14 已寫過「真正的防呆是會自己出現的常駐計數器，不是要人讀的段落」 | 12 個 check 全部可對真實 DB 執行且 fail loudly；上線後**至少抓到過 1 筆真實問題**（抓到 0 筆的 audit 依 INV-5 是恆滅閘門） | Phase 1 建骨架，各 Phase 補檢查 |
| ~~**Golden fixtures / 歷史回歸套件**~~ ✅ **2026-09-03 交付** | — | 14/14 類已凍結（`scripts/capture_golden_fixtures.py --verify` 偵測漂移）。B1／B5／B6 的 dual run 仍待各批執行 | ✅ |

### 明確不排程（理由已量測，勿重開）

| 項 | 為什麼不做 |
|---|---|
| `_only_system_internal_blockers` 的空集合分支 | 依 L14：改了 **0 筆**資料會變，且風險不對稱（會把 L7 的火警警報藏掉）。要動必須先出現真實實例 |
| 等待機制三套併入 Event Watch | 2026-09-02 實測三套的「假死」實例全為 **0/0/0**。**重構不得以「統一」為由推翻已量測結論** |
| 待辦池 evidence conflict 類型 | 史上最重度 drain 期 `open_conflicts` 仍為 **0**，滯留 0 |
| ETF 完整 look-through 管線 | 使用者定案：LLM 當下概算即可，明標「概算·未經查證」，不寫進 `issuer_loads` |
| Confidence 五軸重構為三類 | 「賠率類」要解的問題在無尺寸系統裡無載體。⚠ **Phase 4 完成後重評**——`expectation_gap_score` 某種程度就是賠率維度 |
| 技術指標擴充（RSI vs QQQ、ATR） | beta 訊號已整組拔除；新增動能指標違反「不得用動能指標表達水位」 |
| 貸款提款時間表／glide path 公式 | 使用者明確暫緩；要導入 glide path 需先定義總曝險口徑 |
| Parked lead 第二層召回（embedding） | false positive 消耗的是使用者注意力，而降低注意力噪音正是當初重構的目的。要做須先量測目前漏掉多少 |

---

## 研究主題範圍（2026-08-20 使用者定案）

**以 CPO 與 humanoid 兩條為主。** HBM／記憶體軸只做到 Micron 這筆入圖候選為止，
不再往下深挖；SK Hynix／Samsung 不主動 onboarding。使用者原話：HBM「太大了，
資金太瘋狂了，而且太寡占，感覺現在進去太晚了」。

判準仍有效——`tech:hbm` 確實是圖中最大的供給側空白——但**「是個真瓶頸」不等於
「現在該投」**：寡占程度、資金擁擠度與進場時點是使用者的判斷維度。

**優先序是主線／備援，不是並列。** 其他非 HBM 的 AI 瓶頸（SerDes、載板與中介層、測試）
**只有 CPO 與 humanoid 當輪沒有可推進的工作時才動**，不得因某節點 chokepoint 分數較高就插隊。

⚠ humanoid 的可投資機會在**零組件供應商**不在整機（Agility 未上市、Boston Dynamics 屬 Hyundai）。

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
