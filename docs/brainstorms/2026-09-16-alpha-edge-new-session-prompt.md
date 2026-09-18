# 給新 session 的啟動 prompt（2026-09-19 第七輪改寫；前六輪逐字狀態見文末歷程與 git history）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。
>
> ⚠ **日期會被寫超前。開工第一件事就是 `date`**，不要相信任何檔案裡的「今天」。

---

## 開工指令（貼這一段）

> ## 目標：找出十倍股
>
> 不是大型股的 20% 錯價，不是 beta 波動。**邊緣小公司的 2–10 倍**，靠 AI capex 這類集中需求
> 被放量的瓶頸供應商。小賠多檔一檔補回；結構不變就抱；出場只認反證。
> 系統不給部位尺寸——買多少、什麼時候買由使用者自己決定。
>
> **開工三件事（每次都跑，不要憑記憶）：**
> ```
> date                                                     # 檔案裡的「今天」不可信
> python scripts/writer_guard.py check                     # writer_lock 應為 null
> schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V      # Last Run / Last Result / Next Run
> ```
>
> ### ⚠ 常設授權：沒有需要我核准的事情就繼續做，不要停下來問
>
> 使用者原話（2026-09-17／09-18／09-19 三次確認）：「**我想要的是沒有需要我核准的事情就繼續**」、
> 「**沒有需要我核准的就繼續走完**」。
> **停的理由必須是「有東西要使用者決定」，不是「到了某個邊界」**——Phase 做完不是停止理由、
> Z2 本身不是停止理由、「想說一聲」更不是。撞到 pq2 就掛號、**接著做下一件不需核准的事**，
> 收尾一次給批次指令，**不得停在編號上等**。
>
> **仍要停下等人（不因此放寬）：** 四個人工 gate（graph admission／Engine C 判讀寫入／
> thesis mutation／live）、資本或任何 append-only authority、要改 `AGENTS.md` 判準句或
> ROADMAP 的 Phase／Step 定義（後者先給五欄 amendment）、需要 R2、Verdict 不是 `GO`、
> 或 plan 裡真有要使用者選的問題。
>
> ⚠ **還有一種必須停**：你要做的事與**既有的書面決定相反**時，先把那句話與你的反證擺給使用者看。
> 2026-09-18 實測代價：[610] 的 packet 建議合併 `tech:inp_eml`，卻沒提 `config/entity_aliases.json`
> 早就寫著「不併」——使用者是在資訊不完整的情況下核准的。**後來證明該合併，但那不是重點。**
>
> **收尾時**：更新本檔，**下一份 prompt 必須原樣帶著上面這整個「常設授權」小節**。
>
> ---
>
> ## ⚠⚠ 先讀這一段：籃子第一次有了首選，而它不是目標標的
>
> **2026-09-19：`top_pick` 由 null 變成 LITE（16 檔通過 1）。這是系統第一次回答「現在要加碼哪一檔」。**
>
> ```
> LITE 一把尺：現價 893.61｜沒賭對 1,065.76（+19.3%）｜賭對了 1,078.72（+20.7%）｜判斷錯了 881.63（−1.3%）
> ```
>
> **⚠ 但使用者要先決定一件事：LITE 是市值 $80.2B、26 位分析師覆蓋的大型股，不是 D0／D11 說的「邊緣小公司」。**
> 它會成為首選，是因為 **Phase 4 的市值／覆蓋門檻還沒交付**——filter 目前只問「有賭注、payoff 為正、
> 有催化劑」。三條它都過，而且過得誠實（沒有放寬任何條件）。**這正好證明 Phase 4 是現在最該做的一格。**
>
> ⚠ 另一件必須誠實說的：**LITE 的賭注只有 +0.5pp**（base 40.0% → variant 40.5%，都在公司指引區間內）。
> 因為 base 的 `derivation` 是 `company_guidance`——「我們的差異看法」內容就是「相信公司的指引」，
> 那個看法已整個住在 base 裡。**這不是研究不足，是結構性的。**
>
> ### 上一輪（09-19）撞出的五個系統性缺陷——全部已記 ROADMAP backlog，動手前先讀那五列
>
> 1. **`Catalyst.resolves` 從未被填**：新格式 62 個判斷檔、104 條催化劑，填寫數 **0**。
>    催化劑那格 15/16 亮著不是「沒有催化劑」，是一個**可選欄位**沒人填（Z2）。
> 2. **`review_required` 拿 +1y 的共識去判定校準在 0y 的 base**：15/15 檔 base 都在 0y，
>    每次 rollover 全部假警報；LITE 的 +1y 覆蓋由 22 人崩到 1 人還被讀成「共識上修 +19.2%」（Z2）。
> 3. **overlay 的 `scope` 與 base 不一致時不覆蓋而是疊加**：不報錯、測試不紅，
>    本輪實測產出假的 **+50.3%**（真值 +20.7%）。⚠ **錯誤方向對自己有利**，靠手算對照才發現（Z2）。
> 4. **首屏結構上講不出「判斷錯了值多少」**：`PLACEHOLDERS` 沒有 downside 端，D2 的對稱只做了一半（Z2）。
> 5. **4 檔 base 已含觀點卻被標「還沒寫賭注」**（LITE／SOI.PA／LYC.AX／6324.T）。
>
> ### 這一輪建議做的（依序；前兩件不需核准）
>
> **① Phase 4 的 D11 機械條件**（覆蓋家數上限、市值上限…）。理由見上：籃子現在的首選是大型股，
> 而那正是 Phase 4 要擋的。⚠ 改判準前先量「現有 16 檔有幾檔的判定真的變了」（L14）。
> **② 上面五個缺陷挑一個做**。建議順序 3 → 1 → 2（3 會靜默產生對自己有利的假數字，最危險）。
> **③ 第四檔做到底。** ⚠ 選檔前先跑一次「儀器可用 ∩ 催化劑條件」的交集：
> 本輪實測 5 檔已宣告不主張目標倍數（SOI.PA／IQE.L／MP／POET／6324.T），**它們寫了賭注也算不出 payoff**。
>
> ### ⚠ 已經做完、不要重做
>
> - **不要重新校準 LITE 的 base**：FY2027 共識實測只動 +0.13%，`review_required` 是缺陷 2 的假警報。
> - **不要重寫 LITE 的 variant／downside／短評／催化劑 resolves**（四格都已有值，2026-09-19 寫入）。
> - **不要把 `Lumentum is sold out through 2028` 寫進假設**——它是 tier 3 二手（Reuters 引 SemiAnalysis），
>   本輪刻意未採用。**要動營收那一桿，先把它追到一手**（那會讓 LITE 的賭注從 +0.5pp 變大）。
>
> ### ⚠ 不要做的
>
> - **不要換一個全新的標的池**——問題不在磊晶，在於研究到底的樣本只有三個。
> - **不要為了讓籃子非空而放寬篩選條件**（`AGENTS.md` 明文禁止）。
> - 不要重做 Phase 0／1／2／3／6，也不要重做 V1／V2／V3。

---

## 先讀（順序固定）

| # | 檔案 | 為什麼需要它 |
|---|---|---|
| 1 | `AGENTS.md` | 憲法、六條 invariant、四個人工 gate、**L1–L18**。⚠ 尤其「Alpha 呈現契約」、L7、**L18** |
| 2 | [`docs/ROADMAP.md`](../ROADMAP.md) | **進度與驗收的唯一權威**。Phase 表、completion gate、backlog |
| 3 | [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | **決定紀錄 D0–D15**（使用者原話） |
| 4 | [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | 籃子為什麼空的量測、A／B 兩種賭注 |
| 5 | [`2026-09-18-verbatim-never-reaches-the-decision.md`](2026-09-18-verbatim-never-reaches-the-decision.md) | L18 的完整 zoom-out（V1–V4；V1/V2/V3 已交付） |
| 6 | `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md` | Zoom／Review 判定與八欄交付格式 |

---

## 現況與查證命令（引用前先跑）

| 現況（2026-09-19 實測） | 查證命令 |
|---|---|
| **籃子 16 檔通過 1，首選 LITE**：`no_bet` 13｜`payoff_not_positive` 2｜`no_catalyst_in_horizon` **14** | 讀 `library/private/app/state/basket.json` 的 `filter` 與 `top_pick` |
| LITE：base 1,065.76（+19.3%）｜賭對了 1,078.72（+20.7%）｜**判斷錯了 881.63（−1.3%）**；首屏七句已寫 | `python -m briefing alpha-card LITE`／`python -m alpha brief LITE --list` |
| **已宣告不主張目標倍數的 5 檔**（寫了賭注也算不出 payoff）：SOI.PA／IQE.L／MP／POET／6324.T | `ls library/private/alpha/abstentions/` |
| `Catalyst.resolves` 填寫率：judgments/ **62 檔 104 條，填 0 條**（LITE 的 2 條寫在 judgment 檔內） | 見 ROADMAP backlog 該列的查證命令 |
| AXTI：base 68.91（+1.7%）｜賭注對了 46.97（−30.7%）｜**判斷錯了 35.15（−48.1%）** | `python -m briefing alpha-card AXTI` |
| 可投資排序 **37 列**；filter `input 221／accepted 37／filtered 184` | `python -m query.bottleneck --top-n 60` |
| **重複節點候選 28 對**｜涉及節點 39／185｜**沒人提過 23** | `python -m query.duplicate_nodes` |
| relation 分布：`supplies_to` 302｜`enables` 78｜`is_component_of` **73**｜`depends_on` 63｜`develops` 57｜**`is_variant_of` 17**（2026-09-19 新增） | Cypher `MATCH (ea:EdgeAssertion) RETURN ea.relation, count(*)` |
| `tech:cpo` 的「它自己卡在誰身上」**20 條**（[613][614] 之前是 24，中途一度 25） | `python -m query.structure tech:cpo` |
| 圖裡逐字 `Source` 1,058 個、`QUOTES` 邊 2,959 | `python -m query.structure <node> --quotes` |
| `audit invariants` FAIL 0／PASS 13（筆數隨資料浮動，**驗收條件是 FAIL 0 不是筆數**） | `python -m audit invariants` |
| 待辦池：**pq2 球在你手上 13**；結構讀圖待重讀 0 | `python -m engine_b.todo list` |
| 歸零旗標 16 檔 × 4 盞：紅 2（COHR、IQE.L）｜灰 34（灰不是綠） | 心跳第 4 段 |
| 追蹤表 22 檔｜量測起始 2026-07-21｜**還沒有一檔滿 12 個月** | `python scripts/outcome_if_settled_today.py` |
| 心跳排程每日 07:00 | `schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V` |

⚠ **pytest 要用 `.venv\Scripts\python.exe`**，裸的 `python` 沒有 pytest。

---

## 不得做

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、**因籃子空而放寬篩選條件**、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯（要改先量「幾列真的變了」）、
**跑 `scripts/backup_private.py run`**（Drive token 存在，那會上傳＝對外動作；要備份用
`export_neo4j_payload()` 做純本機匯出）、**自行合併重複節點**（只提名，合併走 pq2）。

## 收尾格式

決策／收據區塊（若有要使用者決定的事，放**最前面**）→ HUMAN SUMMARY（5–10 行）→ 八欄 `STEP_RESULT`
→ **最後一行給可直接複製的批次指令**。格式見 `skills/development-flow/SKILL.md` Step 4.5／5。
Push 是常規動作；push 前 sanity check：`git ls-files library/private` 應為空。

---

## 歷程（每輪壓成一行；逐字收尾狀態在 git history）

| 輪次 | 做完的 | commit 範圍 |
|---|---|---|
| 2026-09-16 | Step 0（呈現契約重寫）＋ Phase 1 計畫核准 | `d06f5bf` 前後 |
| 2026-09-17 | Phase 1 全部｜Phase 2 心跳＋排程｜Phase 3｜Phase 6｜結構讀圖層 | …`65eec17` |
| 2026-09-18 早／白天 | Phase 4 成因分開｜Phase 5 的 D15／D2／歸零旗標｜`graph_context` 截斷說話 | `19af823`…`9032aff` |
| 2026-09-18 晚 | **L18：V1 逐字入圖｜V2 `--quotes`**｜[606]–[610] | `7e6a3bd`…`53b059f` |
| 2026-09-18 深夜 | **V3 重複節點偵測器**｜證據欄從未被賦值（430／526）｜[611][612] | `39a2ff0`…`1de7652` |
| **2026-09-19 早** | **`is_component_of` 全重判 92 條｜新增 `is_variant_of` relation（[613] B）｜[614] 8 條修正｜[615] 4 對合併｜28 對候選判讀｜AXTI downside｜[571]–[575] drop** | `fec9db6`… |
| **2026-09-19 深夜** | **催化劑那格量到底（`resolves` 0/104）｜LITE 做到底：variant＋downside＋resolves＋首屏七句｜`top_pick` 首次非空＝LITE｜修好 `--retract` 撤不回 overlay 的 bug＋守門測試｜五個系統性缺陷進 backlog** | 本輪 |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項，也不要重做 V1／V2／V3。**

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**。**不得為了讓籃子非空而放寬門檻 4。**
