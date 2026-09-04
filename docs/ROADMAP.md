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
| **2** ✅ | First research vertical slice（標的＝COHR） | B4：`alpha/providers/{graph_neo4j,fundamentals}.py`、`alpha/context.py`（Q1 deterministic）、`alpha/models/session_assessor.py`（**不接 API**）、`python -m alpha research COHR` | ✅ 全數達成：①每個 score 都 explain 得到 `EvidenceRef`（無引用即 reject）；②圖零新增節點（provider 唯讀）；③Q1 直接消費 `rank_bottlenecks`，不重算；④突變 23 → **30 個、空跑 0**；⑤全套 1,283 → **1,394 passed / 0 skipped** | Phase 1 |
| **3** ✅ | Engine D decomposition ＋ `mcp_server` domain 抽出 | B2／B3／B5／B6：shared infra 升格、alpha 模組搬入、`sizing` 切三段、`brief` 拆四 pane；core → `mcp_server` import 5 → 0 | ✅ **依賴方向指標全數歸零**（這才是本 Phase 要買的東西）：`decision_lab` 相依環 **3 → 0**；搬遷 shim **15 → 0**；`PENDING_B6_COUPLINGS` **1 → 0**；core → `mcp_server` **5 → 0**；`engine_c`／`portfolio`／`risk`／`shared`／`query` → Engine D **各 0**。<br>量體：`mcp_server/` 4,016 → **673**（domain 2,261 行抽到 `intake/`）；`decision_lab/` 10,653 → **8,807**；`brief.py` 1,462 → **763**。<br>套件品質：1,394 → **1,441 passed / 1 skipped**；突變 30 → **46 個、空跑 0**；`audit invariants` **FAIL 0｜PASS 10｜SKIPPED 2**；golden fixture 漂移 **0**（每一批都是）。<br>daily 端到端**內容不變已實測**（B6 對 HEAD worktree 同 `--as-of` 逐欄 diff：items 45／45、sheet-only 覆蓋分類逐筆相同、markdown 正規化後 diff 0 行）。<br><br>⚠ **原 exit criterion「`decision_lab/` ≤8,000 行」已於 2026-09-04 撤回**，理由是它**算錯了**，不是做不到就改分。逐檔查證後：設計文件 §6 把已搬到 `shared/` 的 `capital_authority.py` **419 行重複計入**，另有四處估計失準——`brief` 估 ~400（實際地板 **763**：`_current_authority_context` 102＋`_reassessable_axes` 60＋`ranking_annotations` 48＋`identity_registration_pending` 43 是純 Engine D，只能拆成另一個同套件檔案，對總行數是 0）、`sizing` 估 ~300（實際 **450**，字彙移出後剩下全是 §3 自己判為 D 的 gate）、`references` 估可 D∩A 切半（實際 **整支是 D**：它同時要 frozen bundle 與 `AXIS_REFERENCE_AUTHORITIES`，「讀者是研究者」不決定層級）、`workflow` 估 ~600（實際 **0 可移**，研究部分 3c 已移走）。重算後真正的地板是 **~8,630**（僅剩 `cli.py` 三個研究輔助子命令 ~170＋`adapters/holdings.py` 8），而唯一夠大的來源是 `store.py` 3,125 或 `context.py` 713——設計文件都明列「不搬」，且為了一個**代理指標**去動 append-only authority 的模組與 point-in-time 凍結機制，正是 L14 禁止的事（未經量測的機制不得決定行動）。**行數是代理，方向才是目的**；方向指標已全綠。 | Phase 2 |
| **3.5** ✅ | Portfolio / Risk 搬家（B1） | `portfolio/{policy,exposure,allocation,brief}.py`、`risk/{policy,snapshot}.py` | ✅ 全數達成（隨 Phase 3 各批一起落地，2026-09-03～04）：`portfolio/`＋`risk/` 共 **2,693 行**已在 `decision_lab/` 之外；`engine_c → decision_lab` import **0**（`portfolio`／`risk`／`shared`／`query` 亦為 0）；三個硬擋逐筆一致（`single_position_nav_cap` 0.05、nominal 12.5%／20%、effective 30%／40%）。查證：`python -c "import ast,pathlib;print(sum('decision_lab' in (n.module or '') for p in pathlib.Path('engine_c').rglob('*.py') for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,ast.ImportFrom)))"` | Phase 2 |
| **3.9** ✅ | **`AGENTS.md` 結構瘦身 ＋ 新增 `docs/ARCHITECTURE.md`**（一次做完） | PROCEDURE 搬 OPERATIONS／skills；L1–L16 加「Learned invariant／事發／可改？」欄；CURRENT_ARCHITECTURE 段落 → 新的 `docs/ARCHITECTURE.md`；四引擎表 → 五條 authority separation ＋ 六條 hard invariant | ✅ **2026-09-04 交付。**<br>**實測 before → after：** `AGENTS.md` **802 行／52,229 字元 → 638 行／26,147 字元（字元 −50%）**；新增 `docs/ARCHITECTURE.md` 290 行；`OPERATIONS.md` 554 → 693；`CONCEPTS.md` 190 → 215；pq2 呈現規格落到 `skills/daily-brief`（Luna 契約當時落到 `skills/luna-reviewer`，**該 skill 已於同日稍晚退役**，見下方 backlog）。<br>⚠ **原 exit criterion「≤450 行」已於 2026-09-04 經使用者裁決改記為字元數。** 理由**不是做不到就改分**：內容確實砍掉一半，差距全部來自**折行慣例**——舊檔把整段塞成一行（87 字元/非空行），新檔照 ~80 欄折行（49 字元/非空行）；同樣內容照舊密度重排約 **300 行**。而 450 行這個目標的**目的**是省 session context，**context 成本是字元／token 不是行數**；為了湊行數把 bullet 重排成長行會讓 `git diff` 顆粒度變粗、之後改一句話整段變紅。**判準改成：字元數必須降，且下列內容驗收全過。**<br>**內容驗收（全過）：** ①**16 條 lesson 一條未刪**，各自標明 implementation 可不可改；②40 條 invariant 逐條仍在（含 `工作語言`／五條 authority／六條 INV／四個 gate／資本三硬擋／Alpha 交付要求／Beta 兩條相關性警告／技術訊號 0 勝 3 敗的實測記錄）；③`grep` 不到與 `.codex/rules`／`skills/*` 重複的清單。<br>⚠ **搬移過程被自家剎車抓到兩次，兩次都是修對而不是放寬：** ① `tests/test_codex_daily_permissions.py` 斷言 sandbox review 的七個 token 在 `AGENTS.md`，搬走四個後當場變紅——改成「**判準驗 AGENTS、程序驗 OPERATIONS**」兩份各驗自己該有的，每個 token 仍被斷言存在；② 往 `OPERATIONS.md` 追加時**差點造出第二份 16 條 fixed entry 清單**（該檔早就有一份），已刪除並在原處留下「不要在這裡再抄一份」的警語——「清單會腐壞，判準不會」正是這次搬移要消除的違規；③ `tests/test_routine_prompts.py` 斷言 Beta 心跳欄位在 `AGENTS.md`，欄位細節搬 ARCHITECTURE 後變紅——同樣改成兩組各驗自己該有的，並把「舊燈號語意已明文廢止」「逐檔表不得省略、每列須明示最新完整交易日」兩條**判準**寫回 AGENTS。<br>**驗收：** 1,538 passed / 1 skipped；`audit invariants` FAIL 0｜PASS 11｜SKIPPED 1；golden 漂移 **0**；`sync_agent_skills.py --check` 無漂移；突變 76 個空跑 0。 | Phase 3.5（boundary 定下來才動） |
| **4**<br>🔶進行中 | Expectation Gap | Engine C 欄位擴充（forwardEps／revenue estimate／segment revenue）、peer registry、implied fundamentals | 🔶 **4a 已完成（2026-09-04）：估計修正與股價變動分離。** `engine_c/estimates.py`＋`alpha/providers/fundamentals.py::estimate_revision`＋`alpha/context.py` 的 method 字串。<br>⚠ **第一項交付的前提被實測推翻，而那是好消息。** 原計畫「Engine C 缺 forwardEps，要擴充欄位」——實測 yfinance 的 `forwardPE` **恆等於** `price / forwardEps`（COHR／NVDA／2330.TW／6324.T／SIVE.ST 相對差 <1e-7），而 `price` 與 `pe_forward` 我們**每天都存**：`financial_snapshots` 1,931 筆有 1,836 筆（95%）兩者皆有值，最早回到 2026-07-08。**新增欄位今天才開始有資料，導出立刻有兩個月歷史。**<br>真正修掉的是 L12：`estimate_revision_30d` 原本取 `pe_forward` 的 30 日變化，而倍數同時被「分析師改估計」與「股價漲跌」推動，下游無從分辨。分開後實測（31 個觀測，2026-08-03→09-03）：**COHR forward EPS +68.3% 而股價 +0.6%**、LITE +81.4%／+18.7%、IREN −73.6%／−2.2%；而 AAPL／GOOGL／TSM／MU／INTC 全部落在 ±5% 內。**「便宜」與「估計與價格脫鉤」被分開了**——後者才是 gap。<br>驗收：可算出修正的標的 **70/70 檔**（exit 要求 ≥5）；`低 P/E 但共識與 thesis 一致 → gap ≈ 0` 已由上述成熟大型股實證；1,441 → **1,457 passed**；突變 46 → **49 個空跑 0**；`audit invariants` FAIL 0；golden 漂移 0；`python -m alpha research COHR` 端到端顯示 method 字串。<br>⚠ **單位陷阱已編碼成測試**：導出值以**報價單位**計。實測 IQE.L（`GBp` 報價）導出 −0.196 便士 vs yfinance 回報 −0.00196 英鎊，**差 100 倍**。因此本模組只保證同一標的的**時間序列比值**（單位消掉），**不得跨標的比絕對值**。<br><br>**剩餘（4b／4c，尚未動工）：**<br>🔶 **4b 機制已完成、資料待核准（2026-09-04）：** `segment_revenue_share` 已登記進 `config/engine_c_observation_fields.json`（`gate_member=false`，五項 gate 契約未動）並接上 `alpha/providers/fundamentals.py` — 有觀測就流到 Q3，沒有就誠實 `None`。⚠ **讀不到一律 `None` 不回 `{}`**：空 dict 會通過「有沒有分部資料」的檢查，然後讓 Q3 讀成「每一塊業務都是 0%」，比誠實說不知道危險得多。<br>✅ **gate 判準已改（2026-09-04 使用者定案）：** Engine C 人工 ledger 的 pq2 不再按「存哪張表」畫，改按 **`verifiability`＝可否確定性重導**（沿用 L10）。`segment_revenue_share` 與 `runway_inputs` 判 `mechanical` → **不需 pq2**；其餘 12 個判 `judgment` → 維持。補償控制：`mechanical` 欄位的 value 強制必須是可機械比對的 JSON 數值（散文一律拒絕）——放行與收緊同時發生。⚠ `gate_member` 五項與 `mechanical` 的交集必須為空，已寫成斷言。<br>**真實資料仍是 0 檔**，但現在卡的是工作量不是核准： yfinance 沒有分部資料，只能從 10-K／年報分部附註（IFRS 8／ASC 280）人工讀入，而寫 Engine C manual ledger 是四個 gate 之一——**每一檔都要一個 pq2 編號**。查證：`python -c "import sqlite3,json,pathlib;p=pathlib.Path('library/private');db=p/json.loads((p/'runtime_pointer.json').read_text())['engine_c'];print(sqlite3.connect(f'file:{db}?mode=ro',uri=True).execute(\"SELECT COUNT(*) FROM manual_fields WHERE field_name='segment_revenue_share'\").fetchone()[0])"`<br>✅ **4c 的第一項已交付（2026-09-04）：`revenue_estimate_next_fy`。**<br>⚠ **它拖到現在，是因為上面這行原本寫著一句假話。** 原文：「yfinance 只有 `revenueGrowth`（成長率）與 `epsCurrentYear`，**沒有絕對營收估計**」。照 AGENTS「引用自家文件的現況陳述前先跑查證命令」實測——`yf.Ticker().revenue_estimate` 直接給 `+1y` 的 avg／low／high／growth／numberOfAnalysts，**73/73 檔全覆蓋**（含 `000660.KS`／`002472.SZ`／`2301.TW`）。**這是同型錯誤第三次**（前兩次見「現況數字會過期」那節）——一句沒人回頭驗證的陳述，把一個 30 秒可得的欄位擋了一整個 Phase。<br>落地：`engine_c/migrations/20260904_add_revenue_estimate_next_fy.sql`（三欄）＋`db.py` 兩種方言＋`etl_yfinance._next_fy_revenue_estimate`＋`ConsensusSnapshot` 兩個新欄位。實跑 COHR：`revenue_estimate_next_fy=14.67B`／共識成長 `+38.2%`／22 位分析師。<br>⚠ **兩個單位陷阱寫成測試：**①絕對值以**報表幣別**計（SK Hynix 是 534 兆 KRW），只能比同一標的的時間序列，`..._growth` 才可跨標的比；②**營收成長 ≠ EPS 隱含成長**——實測 COHR 市場隱含 +244.6% vs 共識營收 +38.2%，那 206 個百分點的差**不是 gap**，它同時包含「市場預期利潤率大幅擴張」。突變測試守著「不得合併成一個 `growth_gap` 欄位」。<br>**剩餘：**`market_implied_margin` 仍需 segment 資料（非美股 11 檔見下方 backlog）；③ peer registry ——⚠ **建議先不建 `config/peer_groups.json`**：`config/sector_anchors.json` 已經是一份分組 SSOT，再造一份就是 L16（分類已有 SSOT 時不要重造）記過的事。要建必須先答出「需求鏈分組對估值比較為何不堪用」，且要有消費端——否則是一個「寫得進去卻不影響任何決策」的死 config。 | Phase 2 |
| **5** ✅ | Causal propagation | `StructuralEvent` → `CausalPath` → `CompanyImpact` | ✅ **5a＋5b 均已完成。5a 二階傳播（2026-09-04）：** `Neo4jGraphResearchProvider.propagate()`＋`get_second_order_beneficiaries`／`get_second_order_victims`（原本明確拋 `NotImplementedError`）。<br>✅ **exit criterion 達成**，實跑 36 條真實排序列：`mat:inp_substrate` supply_disruption／tightening → **co:nvidia 是二階受害者**，路徑 `mat:inp_substrate →constrains→ co:coherent →supplies_to→ co:nvidia`，帶 2 條 `EvidenceRef`；`co:coherent` tightening → **co:lumentum／co:broadcom 二階受益**（替代鏈）。<br>傳播規則寫成明文（規則不是量測）：邊化約成「A 依賴 B」，只有兩條路徑——**依賴鏈**（遞移依賴 subject 者，tightening 時 VICTIM）與**替代鏈**（供同一 chokepoint 的其他公司，tightening 時 BENEFICIARY）；`loosening` 整組反向。<br>三個刻意不做：**不加權總分**（magnitude 由跳數＋路徑最低 substitutability，且**二階最高只到 MEDIUM**——推論不得自稱與觀測同級）、**不編時間**（`lead_time_weeks` 缺席就 `UNKNOWN`，不套「供應鏈大概一季」）、**不取平均信心**（`CausalPath.confidence` 取最弱一段，契約強制）。<br>首跑抓到自己的兩個 bug 並寫成回歸測試：① 逆走的邊沿用原標籤，路徑印成 `mat:inp_substrate -depends_on-> co:coherent`——**因果方向剛好講反**；② magnitude 用 `_finite`(夾 0..1，confidence 專用) 讀 `substitutability`(1–5)，**每筆都變 None**，看起來像資料不足其實資料在。<br>驗收：1,470 → **1,483 passed**；突變 54 → **59 個空跑 0**；`audit invariants` FAIL 0；golden 漂移 0。<br><br>✅ **5b 已於 Phase 6 一併完成（2026-09-04）：`get_structural_changes_since` 不再拋 `NotImplementedError`**——它比對「`since` 的 as-of 投影」與「當前圖」的差集。實跑：`since=2026-06-30` → 1 個事件（`co:axt supplies_to co:lumentum`，`substitution`／`loosening`，observed 2026-07-29）；`since=2026-03-01` → 3 個。<br>首跑同樣抓到自己的兩個 bug：① `observed_at` 取整條邊最早的引用日，於是 `since=2026-06-30` 產出 **`observed_at=2026-03-06` 的「變化」**——一個發生在觀察窗之前的事件。成因是差集混了兩件事：真的新邊，與**舊邊剛跨過 `sub>=4` 門檻**（早期 assertion 沒填 `substitutability`）。改成「事件日必須來自窗內新到的那份文件，窗內沒有新文件就不是事件」。② 第一個已知供應商被報成 `substitution`／`loosening`——那是**我們開始研究一個新領域**，不是世界鬆了（同 `documents` 不參與排序的理由）。兩個修法讓 `since=2026-03-01` 從 17 個「事件」收斂成 3 個。<br>⚠ **`capacity_constraint`／`qualification` 兩個分支在真實圖上一次都沒觸發過**（實測：`since` 兩側都存在的邊 19／32 條，屬性有變的 **0** 條）——它們目前只由 `tests/test_alpha_as_of_projection.py` 守著。 | Phase 2 |
| **6** ✅ | Backtest / validation | as-of 圖投影、anti-lookahead 測試、epoch 錨點 | ✅ **2026-09-04 交付。** `query/bottleneck.py::project_assertions_as_of`＋`Neo4jGraphResearchProvider._rank(as_of)`＋`loader/source_dating.py`（回填走廊）＋`alpha/backtest.py`＋`audit` 的 `PointInTime` check。<br>**實測 before → after：** SourceDoc `published_at` **166/200（83.0%）→ 187/200（93.5%）**；EdgeAssertion 可定日 **382/662（57.7%）→ 645/662（97.4%）** ✅ 達標（≥95%）。查證：`python -m audit invariants --only PointInTime`<br>⚠ **`published_at` 100% 沒有達成，而那是刻意的。** 剩 13 份文件、擋住 17 條 assertion：9 份是**常設產品／公司頁**（Nabtesco／Nidec／Novanta／Proterial×2／Harmonic Drive／Aehr／HyperLight 官網），那類頁面**本來就沒有出版日**；2 份圖上連 URL 都沒有（`damnang`／`silicon_matter` 分析文）；2 份有 URL 但頁面不帶日期（TradingView 轉載的 Zacks、Coherent datasheet PDF——後者抓取工具自陳「這看起來是 logo 檔不是 datasheet」，**兩義訊號不採用**）。**留 null 並列進報告**（L11-5：「我找不到」≠「它不存在」），不用 ingest 日期冒充——那會讓所有東西看起來都是最近才發表的。<br>**as-of 投影實跑：** `2025-06-30` → 2 列、`2026-03-01` → 19 列、`2026-06-30` → 32 列、當前 36 列。⚠ **過濾在排序之前**：`rank_bottlenecks` 是在 assertion 上 collapse 屬性的，先排序再砍列會留下「列是對的、值是偷看來的」，那是 lookahead 最難察覺的形式。<br>**保險絲換條件、沒有拿掉：** `_reject_as_of` 已由兩條 `PointInTimeUnsupported` 取代——圖上完全沒有 `published_at`、或 `as_of` 早於最早證據時仍然拋（回空 list 會與「那天沒有瓶頸」同形，L13）。三條測試守著它。<br>**回填走廊四道補償控制**（放行與收緊同時發生）：屬性白名單／`--basis` 必填並落地／寫入值另存供比對／`url_path` 由 audit 實際重導。⚠ 順手修掉一個靜默炸彈：`MERGE_SOURCE_DOC` 原本無條件 `SET sd.published_at = $published_at`，抽取 JSON 沒帶日期時會把回填**洗成 null**，而不會有任何東西報錯；已改 `coalesce`。<br>**排序前段 vs 後段等權報酬：3 期全部為正**（`+97.8%`／`+3.6%`／`+9.2%`，`scripts/rank_forward_returns.py`）。⚠ **不得讀成排序有效**：第一期幾乎全由 `SOI.PA` 一檔決定（+334.1%，偏離該期均值 +264%），所以輸出強制列出逐檔報酬與「這期主要由誰決定」。期數個位數、標的十來檔且高度集中在 AI 光互連，前後段都不是獨立賭注。<br>**baseline diff（動手前凍結，回填後比對）：** 268 筆既有 decision 的五軸 effective level **0 筆改變**（frozen decision 不回寫，point-in-time contract 成立）；變的是 `python -m alpha research COHR` 的 `context_digest`（`12406e75` → `e682eb67`），因為 evidence_index **9 → 19**——排序列現在帶得出實際引用的 SourceDoc 與其發表日。Q1 分數與 evidence_quality 等級**不變**（`origin_entity` 仍刻意留 None，L8 獨立性計數不受影響）。<br>**驗收：** 1,483 → **1,538 passed / 1 skipped**；突變 59 → **76 個空跑 0**；`audit invariants` **FAIL 0｜PASS 11｜SKIPPED 1**（12 項）（`PointInTime` 由 SKIPPED → PASS，只剩 Phase 4 的 `GateDiscrimination`）；golden 漂移 **1，已解釋為 EXPECTED_CHANGE**（`point_in_time_boundary`：assertion dated 382 → 645、claim dated 300 → 359，正是本 Phase 要推的那個數字）。 | Phase 4、5 |
| **7** ✅ | Portfolio / Risk 完整化 | view → target exposure → hard limits | ✅ **2026-09-04 交付。** `portfolio/alpha_exposure.py`——Phase 3.5 已把 `portfolio/`／`risk/` 搬出 `decision_lab/`，但**兩者對 `AlphaSignal` 的引用實測是 0**：研究端排出了候選、投組端知道持有什麼，中間一條線都沒有，使用者得自己在兩份輸出之間對照 ticker。這支把它接起來，回答「**這些候選我現在持有多少**」。<br>**驗收：**①**不新增任何 alpha 尺寸**——`test_output_contains_no_position_sizing_field` 掃描輸出的每個 key，命中 `target`／`suggested`／`size`／`shares`／`supported_range`／`ceiling` 等字樣即紅；參考線欄位刻意命名為 `single_position_nav_cap_reference`，**名字要自己說出它不是 gate**（超過 5% 不產生 blocker、不告警）。②**target exposure 可由 `AlphaSignal[]` 導出**——join 到持股後每檔給出 `nav_pct`／`held`／`sleeve`，並附 `held_count`／`unheld_count`／`candidate_nav_pct_total`。<br>⚠ **最重要的一條不是功能是分辨力：持股讀不到時整份降級並帶出 `blockers`，不逐檔輸出 0.0%。** 那會讓使用者看到「你一檔都沒買」，而事實是「我沒讀到你買了什麼」——兩者導向相反的行動（L12）。呈現層的措辭也被測試綁住（必須出現「讀不到」「無法」，不得出現「未持有」）。<br>⚠ 三個刻意不做：**不重排候選**（唯一排序權威是 `rank_bottlenecks`，突變已守）、**不 import `alpha/`**（duck typing，保持 `portfolio/ → alpha/` 零相依）、**沒有 ticker 的 signal 列進 `unresolved_signal_indexes` 而不是靜默丟棄**（INV-3）。<br>**驗收：** 1,538 → **1,556 passed / 1 skipped**；突變 76 → **79 個空跑 0**；`audit invariants` FAIL 0；golden 漂移 0。 | Phase 3.5 |
| **8** ✅ | Automation / productization | daily／weekly／skills／MCP 適配 | ✅ **2026-09-04 交付（使用者確認排程未在跑後實跑）。**<br>①**16 條 sandbox rule impact review**：本 session 新增的三支入口（`scripts/backfill_source_dating.py`／`scripts/rank_forward_returns.py`／`portfolio/alpha_exposure.py`）**一律不進 unattended rule**——前兩者互動專用（一個會寫圖、一個吃對外網路），第三個不是 CLI；十六條 fixed entry **數量未變**（`tests/test_codex_daily_permissions.py` 斷言 `prefix_rule(` 恰好 16 次）。結論表見 OPERATIONS。<br>②`sync_agent_skills.py --check` **無漂移**（luna-reviewer 退役後 11 個 skill，兩端轉接層已重生）。<br>③**daily 端到端綠**，11 步逐一實跑：harvest（新增 3 筆 lead／總計 989）→ Engine C ETL（**73/73** snapshot）→ Beta 快照（逐檔心跳完整、2 檔 TWSE 較新而正確隔離）→ Alpha purity → catalyst watch → outcome 快照（**已量測 20/20** 個有 Shadow 錨點的 cohort）→ pending priority → pq1 drain（budget 12，本輪 3 件）→ `decision_lab today` → `todo sync`（新增 0／29 項待辦／watch 35 筆）→ state publisher。<br>⚠ **publisher 第一次刻意 fail closed：`guard_unpushed_commits`。** 它偵測到有未 push 的本機 commit，拒絕把兩個 writer 的變更混進同一份 diff——**那是它該做的事，不是故障**；push 之後重跑即 `status: pushed`。這也是這條窄 pathset 設計唯一一次被真正觸發驗證。<br>⚠ **端到端綠不等於資料沒缺口**（L13：驗的是管線，不是內容）。本輪暴露的既有缺口原樣留著、不順手補：MP 的 `disproof`／`catalyst` 皆未填（L7：沒有證偽條件的警報永遠不會響）；**28 檔只有 14 檔有結構化催化劑日期**，其餘只有散文 catalyst，`expiry 早於催化劑` 這類錯誤在它們身上測不到。兩者都需要 pq2／使用者決定，不由本 Phase 代勞。 | Phase 3 |

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
| **移除最後兩個 LLM API 相依**（新增 2026-09-03；⚠ `generate_lane_memo` 仍未搬） | 使用者定案不再使用 API。全 repo 只剩 `extract.py` 與 `thesis/generate_lane_memo.py` 呼叫 `anthropic`，兩者都是 legacy——實際流程早已是 session-in-the-loop（`assessment-scaffold` → session 寫判斷 → `reassess --assessment`，268 筆紀錄佐證） | `grep -rn anthropic --include=*.py` 在 production 碼命中 **0**；repo 不再需要 `ANTHROPIC_API_KEY` | `generate_lane_memo` 併入 Phase 3 的 B3；`extract.py` 另評估 |
| **非美股 11 檔的 `segment_revenue_share`**（新增 2026-09-04） | 美股 15 檔已補（Q3 從 0 檔可算變成 15 檔），非美股卡在**沒有統一 API**：台股走 MOPS、日股 TDnet、HK HKEX、UK RNS、AU ASX、DE／SE 公司 IR、FR AMF URD。實測台股 3081：管道通（PDF 163 頁抽得出 214k 字）但抓到的是 **2023 年報**且 `部門別`／`分部` 命中 0 次——小型單一部門公司，用舊年度分部配當期財務會誤導 | 11 檔中能取得**當期**分部揭露的補上；確實單一部門的，登記為單段 1.0 並在 provenance 註明；查不到當期揭露的維持 `None`（不得用舊年度湊） | ⚠ `segment_revenue_share` 是 `verifiability=mechanical`，**不需 pq2**；卡的是工作量不是核准 |
| **AEVA／TSEM 已查證未揭露**（新增 2026-09-04） | AEVA 只揭露「認列時點」（point in time／over time）不是產品別；TSEM 單一 foundry 分部，20-F 內無帶金額的產品別表 | 若日後年報開始揭露就補上。⚠ 這兩檔是**已查證未揭露**，與 11 檔非美股的**尚未查**性質不同（L11-5：「我找不到」≠「它不存在」），不得混為一談 | 無 |
| ~~**Luna reviewer 專用委派 skill**~~ ✅ **2026-09-04 退役** | — | **量測後退役**：2026-08-01 上線、實際使用 **2 次**（`luna_reviewer_2026-08-01_pq1_5`／`_2026-08-02_pq1_10`，共 10 筆 lead），之後 **34 天／744 個 commit 零使用**，`.toml` 自上線日起未再修改。兩個原因：①**成本模型變了**——subagent 每次 spawn 都是冷啟動、要重新推導主代理已有的 context，便宜模型省下的往往被 context 重灌吃掉；②**原生功能已覆蓋**——各 harness 的 subagent 本來就能指定便宜模型與唯讀型別。⚠ 真正重造的輪子是疊在 Codex 原生 custom-agent 上的 95 行 skill 協定層。**授權邊界沒有跟著消失**（回傳只是 review packet／主代理唯一 writer／不得委派寫入與四個 gate），已改寫成 provider-neutral 版留在 `AGENTS.md`。移除紀錄與不得回填的理由登記在 closed-vocabulary-registry 的「已移除」區。 | ✅ |
| Engine D cohort 重複（claim-keyed vs company-keyed） | 同公司可能同時存在兩個 cohort（2026-07-30 [74]／[75]） | 新建 cohort 時偵測同公司既有 cohort 並警告。**不回溯清理**（append-only） | 無 |
| **把 `mcp_server/` 的 domain 抽出到 application layer**（新增 2026-09-03） | 實測：`mcp_server/` 4,016 行有 **79%（3,165 行）不是 MCP**——Research Action 的 domain、filesystem provenance 原語、local-only Git 發布，全被關在 transport package 裡。因此 5 個 core 消費端被迫 import 它，其中包含 pq2 待辦池本身 | `Core → mcp_server` 的 import **5 → 0**；`scripts/prepare_research_action.py` 不再呼叫私有 `_impl` 函式 | 併入 Phase 3（分類見 `target-architecture.md` §14.2） |
| ~~**`audit invariants` runtime checker**~~ ✅ **2026-09-04 交付（10/12）** | — | **驗收達標**：上線首跑就抓到真實問題——3 筆 `trace_attempts_ref` 有 2 筆指向已不存在的檔案（daily 把追源原文寫進 `library/raw/`、路徑寫進 leads state，但 publisher pathset 不含它）。搬到 top-level `audit/`（讀遍所有層的東西不能住 core）。**2026-09-04 Phase 6 補上 `PointInTime`（11/12）**——它會**實跑一次 as-of 投影**驗它沒漏出未來，不是只讀覆蓋率。剩 `GateDiscrimination`（Phase 4）。查證：`python -m audit invariants` | ✅ |
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
