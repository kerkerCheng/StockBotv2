# Roadmap Migration Matrix

> **性質：** Phase 0 產出物之一。把重構前的 `docs/ROADMAP.md`（673 行）逐項判定去向。
>
> **原檔完整保留於 [`docs/archive/roadmap-pre-alpha-refactor.md`](../archive/roadmap-pre-alpha-refactor.md)**
> （2026-09-03 逐字封存，112 KB）。本檔只記「每一項去哪了」，不重抄內容。

## 判定字彙

| 代碼 | 意思 |
|---|---|
| **KEEP** | 留在新 ROADMAP（仍是 active work 或 active guardrail） |
| **MOVE** | 搬到別的載體（archive／pq2／brainstorm／AGENTS） |
| **MERGE** | 併進新 Phase 的某一項 |
| **REDESIGN** | 目標仍成立但作法要重想（重構後才知道怎麼做） |
| **OBSOLETE** | 前提已不成立，作廢 |
| **DONE** | 已交付，只留歷史 |
| **DEFER** | 有意義但明確不排程（多半因為 L14「動了 0 筆資料會變」） |

---

## 1. 結構性段落

| 原段落 | 判定 | 去向 | 理由 |
|---|---|---|---|
| 「想法怎麼變成程式」四階流程 | **KEEP** | 新 ROADMAP | 判準（改錯的成本）不隨架構變 |
| 「⚠ 開發項只住這裡，不進 pq2」 | **KEEP** | 新 ROADMAP | 這是 `AGENTS.md` 明文引用的授權載體契約 |
| 「已撤回的診斷」表（7 筆＋分野表） | **KEEP** | 新 ROADMAP「開工前必讀」 | ⚠ **`AGENTS.md` L11-6 有連結指向這個標題**，移走會斷連結；而且它是 active checklist 不是歷史 |
| 「已交付」表（27 列） | **MOVE** | archive | 交付歷史。新 ROADMAP 只在 Phase 表裡記 exit criteria |
| 「什麼值得開發／什麼交給 Claude」 | **KEEP（壓縮）** | 新 ROADMAP | 判準有效；表格壓成四行 |
| 「看起來像缺口但不是——請勿『修正』」（4 條） | **KEEP** | 新 ROADMAP「開工前必讀」 | active guardrail：刪掉會有人去「修」正確的東西 |
| 「已知未修的操作缺陷」 | **MERGE** | 新 ROADMAP 開放 backlog | 與下方 cohort 重複項同一件事 |

---

## 2. 「進行中」三條

| 原項 | 判定 | 去向 |
|---|---|---|
| **A** 移除 compound-engineering | **DONE**（2026-08-29） | archive |
| **B** Daily 架構重整＋beta 減量 | **MERGE → Phase 3 / B6** | 驗收①「單次 daily 輸出長度下降且 pq2 項目數不減」原封不動搬進 Phase 3 的 exit criteria；baseline 2026-09-02 = 24,195 bytes 保留。**B 的技術路徑改成「brief 拆成四個 pane builder」**（見 `engine-d-decomposition.md` §2），不再是「在 brief.py 裡減字」 |
| **C** pq1 drain 清空 | **DONE**（2026-08-29，110→0 兩次） | archive |
| **B-1** beta 訊號拔除 | **DONE**（commit `6aa31de` ＋ 文件同步） | archive；契約已入 `AGENTS.md` |
| **B-2** pq2 決策行 | **DONE**（2026-08-29） | archive |
| **C-1** 研究完整的 cohort 掉出待辦與排序 | **DONE**（常駐清單 `ready_not_ranked`） | archive。⚠ 重構後 `ready_not_ranked` 的正確歸屬是 `alpha/` 的 pane，不是 brief |

---

## 3. 「最終消化層（investable digest）」— 2026-09-03 使用者提出

**這一項是本次重構的直接前身，整項升格。**

| 原子項 | 判定 | 去向 |
|---|---|---|
| P1 Engine C info 快照欄位擴充（forwardEps／forwardPE／marketCap／analystCount） | **MERGE → Phase 4** | 正是 `current-architecture.md` §8 的缺口 #2、#8。Phase 4「Expectation Gap」的第一步 |
| P2 top-N cohort 補 variant perception | **KEEP（研究項，走 pq2）** | 這是研究不是開發（`AGENTS.md` 判準：改變的是「我知道什麼」）。**但重構後它的家是 `AlphaSignal.variant_view`**，不是 `cohort_thesis` 自由文字 |
| P3 共用組裝器抽出（lane memo × digest 同料兩顆粒度） | **MERGE → Phase 2** | 「共用資料組裝層」正是 `ResearchContext`。digest＝橫切面渲染、memo＝縱深渲染，兩者都是 `ResearchContext` 的 renderer。**使用者 2026-09-03 的合併定案在新架構下自動成立** |
| P4 接 outcome 追蹤 | **MERGE → Phase 6** | |
| 三條驗收（零自算數字／圖零新增節點／錨點筆數 >0） | **KEEP** | 逐字搬進 Phase 2 與 Phase 4 的 exit criteria |
| 「兩段隔離＝L4」的架構定位 | **KEEP** | 升格為 `target-architecture.md` 的硬規則：未來 EPS／capex／條件式營收**永不入圖**，歸 Engine C 與 `AlphaSignal` |

---

## 4. 「研究注意力分配」workstream

| 原項 | 判定 | 去向 |
|---|---|---|
| 3a pq1 排序改字典序 | **DONE**（2026-08-22，前 5 名「只是信心」3→0） | archive。⚠ **「加權總分有補償性」這條判準 KEEP**——`AlphaSignal.value` 的組合規則直接受它約束（見 `target-architecture.md` §5 硬規則 4） |
| 3b `skills/alpha-status` 四 pane | **DONE**（2026-08-22） | archive。重構後它消費 `AlphaSignal`，pane 結構不變 |
| 3c `skills/system-decompose` | **DONE**（Z=5、Z=8 兩跑，長出兩條有供應商的邊） | archive。**KEEP 為常備機制**：它是唯一能產出「圖裡根本沒這個節點」的入口，`coverage_gaps` 只能從既有節點往回看 |
| **#2 epoch 錨點（不得事後回填）** | **KEEP → Phase 6** | 未開始。它是 outcome 量測正確性的前置 |

---

## 5. 「廣度／事件追蹤／量測」workstream

| 原項 | 判定 | 去向 |
|---|---|---|
| 🔴 可執行性（使用者能否據此下手） | **KEEP → Phase 2 的 exit criteria** | 這是整份重構的 North Star 的另一種說法 |
| 廣度：可評估標的數 | **REDESIGN** | 原表自陳指標有問題（`ELIGIBLE` 是資本閘門不是選股判準）。新指標：**有完整 `AlphaSignal` 的標的數**，且必須跨 ≥2 個 demand anchor |
| 事件追蹤：新事件進 brief 的延遲 | **KEEP → Phase 5** | 併入 `StructuralEvent` 的產生與傳播 |
| 量測：可量測 cohort 與超額中位數 | **KEEP → Phase 6** | ⚠ **2026-08-18 的下修結論 KEEP**：現有錨點是「入圖日」不是「進場判斷日」，10 個觀測是一次 sector 移動被複製 10 次，**不構成選股能力證據**。這條在 Phase 6 之前都必須每次複述 |
| 主題範圍（CPO ＋ humanoid 兩條主線；HBM 只到 Micron 為止） | **KEEP** | 研究 scope policy，不隨架構變。搬進新 ROADMAP |

---

## 6. 「未排程」大表（約 25 列）

### 6.1 已交付（2026-09-01 ~ 09-02 密集交付）→ 全部 **DONE / archive**

pane1 按 sector 分段｜`prepare_research_action` 擋同 URL 無 section｜`fetchers/edgar_watch`｜
`fetchers/arxiv.py`｜assessment 骨架生成器｜complete-ra lead refs 自動回寫｜
outcome 等權重聚合＋排序快照＋brief 首屏｜公司三集合對齊 enforcement 三層｜
variant perception 落地為 cohort thesis 欄位｜雙向 writer lock｜
`structural_lead_time_weeks` 語意限定｜`evidence` 五級分級｜Engine C TSM 序列（registry 缺 `market_currency`）｜
research-drain 升級為單一研究入口＋loop 模式｜decision_review 收集端消費「可解性」｜
waiting_on trigger 可達性＋Event Watch 模組｜Paywall ROI 清單｜本機 single-writer guard｜
private authority 備份

**其中三條的結論升格為新架構的硬約束（KEEP）：**
- `evidence` 五級 `EVIDENCE_RANK` → `EvidenceRef.evidence_class`
- variant perception 的操作定義（市場隱含 X／thesis Y／催化劑 Z）→ `AlphaSignal.variant_view`
- Event Watch 是等待條件的唯一 registry → Phase 5 的 `StructuralEvent` 不得另建第二套等待

### 6.2 已結案（量測後決定不做）→ **DEFER，理由保留**

| 項 | 為什麼保留理由 |
|---|---|
| 等待機制三套在 Event Watch 之外 | 實測假死實例 **0/0/0**，依 L14 留著不動。**重構不得以「統一」為由推翻已量測結論** |
| 待辦池 evidence conflict 類型 | 兩週最重度 drain 期 `open_conflicts` 仍為 0 |
| ETF 完整 look-through | 使用者定案「LLM 當下概算即可，不寫 `issuer_loads`」 |
| Sheet writer | 前提被否證（`scripts/record_trade.py` 就是窄版 writer） |
| Confidence 五軸重構為三類 | 「賠率類」要解的問題（尺寸隨賠率放大）在無尺寸系統裡無載體。⚠ **重構後可能重開**：`AlphaSignal` 的 `expectation_gap_score` 某種程度就是賠率維度 → 標記為 **Phase 4 完成後重評** |
| `paper_exposure_invalid` | 前提被否證，產生端仍活著 |
| `paper_portfolio/ledger.py` | 保留為 e2e 獨立重放驗證器，理由已入 docstring |

### 6.3 仍開的技術缺陷 → **KEEP**（進新 ROADMAP 的「維持營運」區）

| 項 | 判定 | 備註 |
|---|---|---|
| `decision_lab today` footer `live_choices=0` 與 outcome 的 1 筆不一致 | **KEEP** | L12 一表兩義。**Phase 3 拆 brief 時順手修**——不要單獨開工 |
| `event_watches.json`／`hypotheses.json` 不在 state publisher pathset | **KEEP** | 需 sandbox impact review。與重構無關，獨立處理 |
| `current_holdings` 裸 `except Exception` 壓平三種失敗 | **KEEP** | L12。Phase 3 拆 `engine_d_runtime/adapters.py` 時一併修 |
| `checkpoint_decision_review` completed 路徑非原子 | **KEEP** | 已有實測踩坑紀錄（[166]）。與重構無關，獨立處理 |
| Engine D cohort 重複（claim-keyed vs company-keyed） | **KEEP** | append-only，不回溯清理；只加建立時警告 |
| `_only_system_internal_blockers` 空集合分支 | **DEFER** | 依 L14 不得動：改了 0 筆資料會變，且風險不對稱 |
| 補齊各 cohort `commercial_maturity` 觀測 | **MOVE → 研究（pq2）** | ⚠ 2026-08-19 已下修：現存積壓**沒有一個是讀年報能解的**，binding constraint 是「替 AVGO／POET 跑五軸 assessment」。重構後這變成「跑 AlphaModel」 |

### 6.4 M1 研究遺留 → **MOVE → pq2（研究項，非開發項）**

TSEM oversupply watch｜MACOM／Semtech 作為 Tower TIA 客戶（tier 3 待客戶端印證）｜
GF 對 Tower 專利訴訟未追源。

三項都是「改變我知道什麼」而非「改變系統怎麼運作」，依 `AGENTS.md` 判準應走 pq2，
不該躺在 ROADMAP。

✅ **2026-09-03 已鑄號：[469] TSEM oversupply｜[470] MACOM／Semtech Tower TIA 客戶｜
[471] GF 對 Tower 專利訴訟。** 三項皆為 `manual` 型、active 待使用者 `go`——
使用者當日授權的是「鑄號」（把它們從 ROADMAP 搬進正確的載體），**不是啟動研究**，
因此不在受理時 resolve。

---

## 7. 「已 brainstorm 但未實作」

| 來源 brainstorm | 判定 | 去向 |
|---|---|---|
| `2026-07-26-next-phase-operating-model` 的五項 | **DONE / DEFER** | 五項已全部結案（見 §6.1、6.2） |
| `2026-07-31-leverage-glide-path` | **DEFER** | 貸款提款時間表由使用者明確暫緩；三次訊號回測記錄 **KEEP 為 `AGENTS.md` 的拔除依據** |
| `2026-08-13-capital-expression-direction` | **OBSOLETE（實作對象）／KEEP（D1–D7 方向）** | §2 baseline 與 §4 六步指涉的欄位已隨 U7 移除。**D1–D7 判準仍有效**，尤其 D6/D7（gate 本身也要量測、先量測後放閘）——重構的每個 Phase 都受它約束 |
| `2026-08-02-confidence-axes-restructure` | **DEFER → Phase 4 後重評** | 見 §6.2 |
| `2026-08-21-research-attention-allocation` | **KEEP** | §2「答案回來會改變什麼」四級判準與 §6 產物持久化判準，是 Phase 2 選題的直接輸入 |
| `2026-08-31-event-watch-module` | **DONE** | |
| `2026-08-31-industry-sector-ranking` | **DONE**（pane1 分段） | |
| `2026-08-31-unverified-screenshot-leads` | **DONE**（hypothesis overlay） | |

---

## 8. 「未來想法（尚未承諾）」

| 原項 | 判定 | 去向 |
|---|---|---|
| 2026-07-31 回測：等回檔才投入是負貢獻（QQQ 91.5%／SOXX 91.9%） | **KEEP** | 已是 `AGENTS.md` 的拔除依據。archive 保留完整數字 |
| 2026-07-31 回測：深跌加碼槓桿 ETF 的真實效果與致命限制 | **KEEP** | 含「第一版回測是錯的」的方法論教訓——**任何跨 2000-2002／2008 的槓桿回測必須用真實基金資料**。Phase 6 開工前必讀 |
| Ayres & Nalebuff life-cycle leverage（槓桿的變數是人生階段不是回撤深度） | **DEFER** | 要導入 glide path 需先定義總曝險口徑 |
| Parked lead 第二層召回（embedding／事件觸發） | **DEFER** | 第 1 層（主題關鍵字）已實作；第 2 層 embedding 的代價（false positive 消耗注意力）大於收益 |
| lead `refs` 未登記字彙 | **DONE**（`config/lead_ref_keys.json`） | |
| 技術指標擴充（相對強弱 vs QQQ、ATR） | **OBSOLETE** | beta 訊號已整組拔除；新增動能指標會違反「不得用動能指標表達水位」 |
| **Engine D 未上市公司支援** | **REDESIGN → Phase 2** | 現況：缺 `research_ticker` 就整組 fallback 成 unresolved。**重構後這是 `ResearchContext` 的問題不是 Engine D 的問題**——研究不需要 ticker（Agility、Ewellix、Unitree 上市前都研究過），只有資本決策需要。分離之後這個限制自然解掉 |
| 灌文件提升圖深度（L8 三 origin 門檻） | **MOVE → 研究（常備）** | `research-drain` 的閉包語意已涵蓋 |

---

## 9. 新 ROADMAP 的 Phase 對照

| Phase | 吸收了哪些舊項 |
|---|---|
| **1 — Alpha contracts** | 新增（無舊項） |
| **2 — First research vertical slice** | 舊「🔴 可執行性」｜digest P3｜Engine D 未上市公司支援｜研究注意力分配 §2/§6 判準 |
| **3 — Engine D decomposition** | 舊「進行中 B」（daily 架構重整）｜footer 不一致｜`current_holdings` 裸 except |
| **4 — Expectation Gap** | digest P1／P2｜Confidence 五軸重評｜Engine C 估值欄位擴充 |
| **5 — Causal propagation** | 事件追蹤延遲｜`system-decompose` 的下游 |
| **6 — Backtest / validation** | epoch 錨點 #2｜量測 workstream｜錨點效度下修結論｜槓桿回測方法論教訓 |
| **7 — Portfolio / Risk** | beta 呈現契約（不變，只搬家）｜target allocation |
| **8 — Automation / productization** | daily/weekly routine 適配｜skills 更新｜MCP surface |

---

## 10. `AGENTS.md` 條目的去向（2026-09-03 補充 audit）

> **完整分類在 [`current-architecture.md`](current-architecture.md) §11；
> 調整建議在 [`target-architecture.md`](target-architecture.md) §15。**
> 這裡只記「哪一段最後會住在哪個檔案」，作為 roadmap 層級的搬遷追蹤。
>
> ⚠ **第一輪不執行**——`AGENTS.md` 每個 session 完整載入，改它的風險最高。

### AGENTS.md 的改動分兩類，時機完全不同

**A 類——「防止文件說謊」的即時修正。不可延後，必須在同一個 change 內完成。**
當 code 改動讓 `AGENTS.md` 的某句話變成假的，那句話就要在同一個 commit 改掉。
依據是 2026-08-29 的實測教訓：程式已於 `6aa31de` 拔掉 beta 訊號，但三份文件仍在描述
**已不存在的行為**——那不是 L13 的「管子只接一頭」，是**管子換了但說明書沒換**，
下一個 session 會照著說明書把已被量測為有害的機制講回來。
下表「什麼時候動」標成具體 Phase 的，全部屬 A 類。

**B 類——一次性結構瘦身。排成 Phase 3.9（Phase 3.5 之後、Phase 4 之前）。**
包含：把約 310 行 PROCEDURE 搬去 OPERATIONS／skills、L1–L16 改寫成五欄格式、
四引擎表換成五條 authority separation。

**為什麼是 3.9 而不是更早：** architecture boundary 要到 Phase 3.5 結束才真的定下來
（Engine D 拆完、`mcp_server` domain 抽出、`alpha/` 擁有 research、Portfolio/Risk 搬完）。
在那之前寫的瘦身版本，會在後面每個 Phase 落地時再被改一次——那正是使用者原話
「確認新的 architecture boundary 後，再進行 `AGENTS.md` 瘦身」要避免的。

**為什麼不能全部等到 3.9：** A 類延後就是讓文件說謊，而本 repo 已經因此踩過一次。

| `AGENTS.md` 段落 | 判定 | 去向 | 什麼時候動 |
|---|---|---|---|
| 工作語言 | **KEEP** | `AGENTS.md` | — |
| 現況數字會過期，判準不會 | **KEEP** | `AGENTS.md` | — |
| 資本與風控 | **KEEP** | `AGENTS.md` | — |
| 授權載體唯一＝pq2 編號｜`go` 的語意 | **KEEP** | `AGENTS.md` | — |
| Alpha 呈現契約的 invariant 部分（不給尺寸／交付要求） | **KEEP** | `AGENTS.md` | — |
| 技術訊號的地位（三次回測記錄） | **KEEP，不得刪減** | `AGENTS.md` | — |
| L1–L16 | **KEEP（重寫成五欄格式）** | `AGENTS.md` | **Phase 3.9（B 類）** |
| **系統架構（四引擎／四層）表** | **REDESIGN** | 改為五條 authority separation | **Phase 3.9（B 類）** |
| Engine D 的 authority 欄（含五軸／排序／NAV） | **REDESIGN** 🔴 | 只留 A5 | Phase 3（B5/B6 落地時） |
| 「唯一排序權威是 `rank_bottlenecks()`」 | **REDESIGN** 🔴 | 改為「結構排序唯一權威；alpha 排序必須消費它」 | Phase 2（`AlphaSignal` 首次排序時） |
| 「哪些標的值得看」四維度 | **MERGE → 五 score** | `alpha/contracts.py` ＋ `AGENTS.md` 摘要 | Phase 4 |
| 「報告產出：cohort 是終點」 | **REDESIGN** | 「`AlphaSignal` 是研究終點」 | Phase 2 |
| point-in-time contract（只講 Engine D） | **REDESIGN**（擴充） | 加研究／回測側 | Phase 1（`PointInTimeUnsupported` 落地時） |
| Beta 呈現契約 | **MOVE** | 隨 `portfolio/` 搬家，`AGENTS.md` 留一段摘要 | Phase 3.5（A 類） |
| pq2 呈現規格（約 90 行） | **MOVE** | `skills/daily-brief/SKILL.md` | **Phase 3.9（B 類）**——B6 拆 brief 時只確保不說謊，搬移在 3.9 一次做 |
| Codex sandbox／16 條 rule 抄本 | **MOVE** | `docs/OPERATIONS.md` | Phase 8 |
| Luna 委派契約 | **MOVE** | `skills/luna-reviewer/SKILL.md` | 隨時 |
| Daily routine 權限與 retry｜報告留檔策略｜outbound 通知細節 | **MOVE** | `docs/OPERATIONS.md` | **Phase 3.9（B 類）** |
| 五套證據強度字彙 | **MOVE** | `CONCEPTS.md` | Phase 1（A 類：`EvidenceRef` 落地時必須對得上） |
| 管道層 ASCII 圖含 MCP 動詞 | **REDESIGN** | 改 application service 名稱 | Phase 3 |
| 「MCP server 十二工具 surface」 | **MOVE → OPTIONAL_ADAPTER** | 標為 optional peripheral | Phase 8 |
| L9 三前置條件已達標 | **KEEP**（實作可搬） | `thesis/preconditions.py` → Engine D | Phase 3 |

---

## 11. MCP / Remote access 相關項目的優先級調整

> **使用者定案（2026-09-03）：MCP／remote access／cloud session 是 Legacy Peripheral。**
> 純 remote/cloud-session 的 roadmap 項目一律降級，**除非它對目前 local-first workflow
> 有直接價值**。

| 項目 | 原本在哪 | 新判定 | 理由 |
|---|---|---|---|
| **Research Action 的 domain semantics**（bounded mutation／digest identity／immutable review packet／explicit approval／idempotent apply／state machine） | 分散在 archive 的多筆交付 | **KEEP → 升格為 core** | 這是系統最貴的資產之一，只是住錯 package。**不得因為「MCP 可以忽略」就一起丟掉** |
| `mcp_server/` 的 79% domain code（3,165 行） | 未在 roadmap | **EXTRACT_FROM_CORE**（新增項） | `current-architecture.md` §12.1 實測。**新增到 Phase 3 的範圍** |
| `Core → mcp_server` 的 5 個反向依賴 | 未在 roadmap | **EXTRACT_FROM_CORE**（新增項） | `engine_b/todo.py` 等；驗收＝該 import 計數 5 → 0 |
| remote Decision MCP（「Engine D 仍未包含」） | archive | **OPTIONAL_ADAPTER / DEFER** | 遠端能看建議、不能替使用者接受 choice——這條邊界不變，但不排程 |
| `record_lead_decision` 的窄 Git 例外（`leads_git.py`） | archive（已交付） | **LEGACY_BUT_HARMLESS**（原始理由已失效） | 它存在是為了讓 cloud routine 讀 pushed leads，**而 cloud routine 已於 2026-07-26 移回本機** |
| cloud session ＋ MCP 作為 daily／weekly 備援 | `AGENTS.md`／skills | **DEFER** | daily／weekly prompt 已逐字禁用 MCP；備援定位保留但不投資 |
| 雲端 egress 白名單 | `docs/OPERATIONS.md` | **DEFER** | 只影響日後 cloud fallback |
| ChatGPT full-MCP write 方案／connector refresh | `docs/remote-access-architecture.md` | **OBSOLETE（作為設計約束）** | 第三方平台限制，不得影響 core |
| MCP action quota／30 天過期／5 MiB 上限 | `docs/remote-access-architecture.md` | **OBSOLETE（作為 domain rule）** | transport／ops 限制，不得升格為 domain invariant |
| OAuth 2.1／短效 audience-bound token（殘餘安全升級） | `docs/remote-access-architecture.md` | **DEFER** | 只在手機入口仍使用時才有價值 |
| 手機 ad hoc intake（`skills/lead-intake` 遠端入口） | skills | **KEEP_AS_ADAPTER** | 這是 MCP **唯一仍有現實價值**的用途：使用者在手機上看到線索時的入口 |

**⚠ 一條反向的注意事項：** 降級 MCP **不等於**降級 `skills/source-trace`、
`prompts/intake_protocol.md` 或 storage permission 規則——那些是 **provenance domain**，
只是最初因為遠端入口才被寫下來。它們對 local-first 一樣適用。

---

## 12. 歷史事故的遷移責任

完整矩陣見 [`historical-failure-matrix.md`](historical-failure-matrix.md)。
roadmap 層級只記一句：

> **本次 refactor 的每個 phase，exit criteria 必須包含
> [`historical-failure-matrix.md`](historical-failure-matrix.md) §9 的八項 completion gate；
> 該 phase 負責的 🔴（僅有文字保護的 lesson）未歸零前，不得宣稱完成。**

現況：36 筆事故中 **🔴 10 筆**。各 Phase 的責任分配見該檔 §9。

---

## 13. 這份 matrix 自己的驗收

- [x] **舊 ROADMAP 的每一個標題都在本檔出現過**——2026-09-03 實測：
      `grep -n "^## \|^### \|^#### " docs/archive/roadmap-pre-alpha-refactor.md` 得 **22 個標題**，
      逐一比對後全部在本檔 §1–§8 有對應判定。
- [x] **`AGENTS.md` 對 ROADMAP 的連結仍能命中**——「已撤回的診斷」與「看起來像缺口但不是」
      兩節**刻意留在新 ROADMAP**（它們是 active guardrail 不是歷史），
      `AGENTS.md` L11-6 的錨點連結因此不會斷。
- [x] **三個 M1 研究遺留已鑄成 pq2 編號**（2026-09-03）：[469] TSEM oversupply／
      [470] MACOM-Semtech tier 3／[471] GF-Tower 訴訟追源。查證：`python -m engine_b.todo list`
- [ ] 沒有任何一項被判成 OBSOLETE 卻仍有程式碼在跑（反例：技術指標擴充判 OBSOLETE，
      而 `engine_c/technical.py` 的 legacy 動能欄位仍在 schema 裡——那是**刻意保留的歷史列**，
      不是活的功能，已在 schema 註解載明）
