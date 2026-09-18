# 給新 session 的啟動 prompt（2026-09-18 收斂改寫；前四輪的逐字收尾狀態見文末歷程與 git history）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。
>
> ⚠ **日期會被寫超前。** 2026-09-17 那輪的收尾塊自稱「09-18」，害下一個 session 以為心跳已經
> 自動跑過一次。**開工第一件事就是 `date`**，不要相信任何檔案裡的「今天」。

---

## 開工指令（貼這一段）

> ## 現在的狀態（2026-09-18 第四輪收尾）
>
> **開工三件事（每次都跑，不要憑記憶）：**
> ```
> date                                                    # 檔案裡的「今天」不可信
> python scripts/writer_guard.py check                    # writer_lock 應為 null、daily_done_today
> schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V     # Last Run Time / Last Result / Next Run Time
> ```
>
> **Phase 狀態：Phase 1 ▶（研究已做、證據不足以進榜）｜Phase 2 ▶（等時間）｜Phase 3 ✅｜Phase 4 ▶（①已交付）｜Phase 5 ▶（D15／D2 對稱 overlay／歸零旗標／alpha 全歸零／D3 全部已交付，剩第四盞燈與「賭注 V4」）｜Phase 6 ✅｜Phase 7 ○。**
>
> **⚠ Phase 2 的「連續 3 天心跳」：第 1 天 ✅ 2026-09-18 07:00:01、`Last Result 0`、publisher sent 2/2。
> 第 2 天＝09-19、第 3 天＝09-20。** 那是等時間不是等工作；3 天湊滿之前不標完成。
> 查證：`library/private/heartbeat/heartbeat_task.log` 逐日一段。
>
> **本輪（2026-09-18 下午）做完的三件：**
>
> | | 交付 | before → after |
> |---|---|---|
> | **Phase 5 歸零旗標**（D2） | `alpha/wipeout.py` 純函式判色 ＋ read model 的 `WipeoutFlagsSection` ＋ 四個消費端（alpha-card 13f／analyst-view／APP 個股頁／心跳第 4 段） | 籃子 16 檔 × 4 盞：**紅 2（COHR、IQE.L 的負債燈）｜黃 8｜綠 20｜灰 34**；先前是 0 盞 |
> | **Phase 5 alpha 全歸零淨值**（D2） | 心跳第 4 段直接取 `risk.snapshot.alpha_total_weight`，不另算一份 | 由 `capability_absent` → **「alpha 全歸零淨值少 1.46%」** |
> | **D3 驗證＋心跳的假宣告** | D3 早在 2026-09-15（`7e7012f`）就交付且有三條守門測試；順手移除心跳裡沒有 consumer 的 `PENDING_PHASE` 死表 | 心跳不再每天印「power-law 三量：還沒建」（它當天 09:31 就交付了） |
>
> **⚠ 本輪最該記住的四件事：**
>
> **① 真實資料第二次當場推翻首版設計，形狀與上一輪一模一樣。** 稀釋那盞的第一版用「窗內有沒有增加」
> ×「燒不燒錢」判紅黃，一跑 16 檔就看到 **COHR +0.10%（54 天，員工股酬等級）與 LITE +15.30%** 拿到同一組
> 規則的顏色，IQE.L 更是靠 **+0.0044%** 亮紅。那是 L12：`change > 0` 同時承載「雜訊」與「靠發股活著」。
> **修法不是設量級門檻**（憑空參數，INV-5），是**把判不出來的那一半留白**——窗滿一個完整會計年度才判色。
> 連續兩輪的教訓同一句：**寫完新統計量／新判準，一定要用真資料跑一次再說它對。**
>
> **② 綠燈只能由「量到了而且沒事」產生。** 這是整個機制唯一會造成實害的失敗點，所以灰**刻意不在**
> `FLAG_COLOURS` 裡——它是「沒有顏色」＋一個 `absence_kind`，型別層因此讓「這盞是綠的」與「這盞沒點亮」
> 不可能同形。64 盞裡有 34 盞是灰，**那是誠實的起點，不是壞掉**。
>
> **③ 每天印一句假話的機制不會有任何東西變紅。** 心跳的 `PENDING_PHASE`（「還沒建的能力指到哪個 Phase」）
> 三筆裡兩筆已交付、最後一筆指向已完成的 Phase 3，**而且整張表一個 consumer 都沒有**（INV-4）。
> 判準：**交付一項能力時，同一個 change 要把宣告它「還沒建」的那一行也改掉**——否則它只會安靜地偏。
>
> **④ 燈把數字留在稽核層，所以可疑值一眼看得出來。** IQE.L 的現金跑道用 yfinance 的 FCF TTM 算出
> **394 個月**，而它自己年報的 base case 流動性 headroom 在 2026-05 掉到 £6.1m——**燈沒錯，錯的是它吃到的那個數**。
> 修法是補一筆 H1 2026 的 `runway_inputs`（`mechanical` 欄位，**不需 pq2**），已列進 ROADMAP backlog。
>
> **待使用者決定：目前沒有。**
>
> **不需核准就能接著做的（依序建議）：**
> **① 重讀 `mat:inp_substrate` 的結構讀圖**（研究不是開發，互動 session 才能做，D12）——上一輪的
> `constrained_by` 放閘讓它的需求側從 15 條變 16 條，ledger 那份仍標 `stale`。
> 查證：`python -m query.structure mat:inp_substrate`、心跳第 2 段。
> **② Phase 4 剩下的三種成因**（②`enables` 一表兩義、③`tech:photodiode` 真的沒有需求方邊、④鏈長）。
> **③ ROADMAP backlog 的三條 🔴／🔶**：claim 截斷不說話、409 條 disproof 只有 1 條 TRIGGERED、心跳報昨天；
> 外加本輪新增的兩條（歸零旗標第四盞的結構化欄位、IQE.L 的 `runway_inputs`）。
> ⚠ **「賭注 V4：variant 收斂納入 outcome 量測」在 backlog 裡沒有驗收條件**，依 ROADMAP 自己的規矩
> （「沒有驗收條件的不准進佇列」，L14-1）要先補一行「這會讓哪個數字變」才排得進來。
>
> ⚠⚠ **binding constraint 連續六輪沒有動過：籃子 16 檔 `bet` 2、`abstained` 0、`unanswered` 14；
> `downside` 假設 0 筆。** 本輪交付的四盞燈**一盞都不會動到它**——燈回答「這家公司會不會歸零」，
> 不回答「我們賭它什麼」。能讓籃子非空的只有兩條路，**兩條都要人**：①替某一檔寫下帶 disproof 的賭注；
> ②寫一筆 `bet/variant.overlay` 的 Abstention。**兩者都是答案，只有空白不是。**
> 這點要對使用者說清楚，不要讓交付看起來像進展。
>
> **仍要停下來等人的（不因常設授權放寬）：** 四個人工 gate（graph admission／Engine C 判讀寫入／
> thesis mutation／live）、資本或任何 append-only authority、要改 `AGENTS.md` 判準句或 ROADMAP 的
> Phase／Step 定義（後者先給五欄 amendment）、需要 R2、Verdict 不是 `GO`、或 plan 裡真有要使用者選的問題。
> ⚠ **撞到 pq2 就掛號、接著做下一件不需核准的事**，收尾一次給批次指令——**不得停在編號上等**。

---

## 先讀（順序固定）

| # | 檔案 | 為什麼需要它 |
|---|---|---|
| 1 | `AGENTS.md` | 憲法、六條 invariant、四個人工 gate、L1–L17（一字不動）。⚠ 尤其「Alpha 呈現契約」與 L7（disproof 要附核查頻率＋觸發後 48h 動作） |
| 2 | [`docs/ROADMAP.md`](../ROADMAP.md) | **進度與驗收的唯一權威**。Phase 表、completion gate 八項、舊 backlog（含本輪新增的兩條 🔴） |
| 3 | [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | **決定紀錄 D0–D15**（使用者原話） |
| 4 | [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | 籃子為什麼空的量測、A／B 兩種賭注、三條「改掉 substitutability」為什麼都是錯的 |
| 5 | [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md) | Q5 結構讀圖的完整設計（§5b 存輸入不存結論、§6b 怎麼 trigger 重新推理） |
| 6 | `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md` | Zoom／Review 判定與八欄交付格式 |

**只在需要時才讀：** `docs/OPERATIONS.md`（要實際跑操作時）、`docs/ARCHITECTURE.md` §4.1／§8
（要動 Daily 三層或 APP 呈現時）、各 Phase 的 plan 檔。

⚠ **本輪不必讀的**：其餘 15 份 brainstorm 都是 2026-07～08 的舊題目，與 Alpha Edge 無關。

---

## 現況與查證命令（引用前先跑）

| 現況（2026-09-18 第四輪實測） | 查證命令 |
|---|---|
| 可投資排序 **37 列**；**TW／TWO／ST 仍 0 檔**（6 檔台股在「低於門檻」區） | `python -m query.bottleneck --top-n 60` |
| canonical 邊 **530**、materialized 屬性 **363**；`substitutability` 覆蓋 **91/530（17%）** | `python -m loader.edge_resolution project --dry-run` |
| `audit invariants` FAIL 0／PASS 13（**4,183 筆**） | `python -m audit invariants` |
| 全套 pytest **2,652 passed／1 skipped**（含本輪新增的 16 條） | `python -m pytest -q` |
| 待辦池未結案 **35** 項；**pq2 球在你手上 18**；pq1 可做 **11**；未 triage **0** | `python -m engine_b.todo list`／`python crons/heartbeat.py` |
| 籃子 16 檔：`bet` **2**｜`abstained` **0**｜`unanswered` **14**；量的候選 15 家通過 **0** | 讀 `library/private/app/state/basket.json` 的 `bet_ledger` |
| **歸零旗標 16 檔 × 4 盞：紅 2（COHR、IQE.L）｜黃 8｜綠 20｜灰 34** | 讀同檔的 `wipeout_ledger`；或 `python crons/heartbeat.py` 第 4 段 |
| **alpha 全歸零淨值少 1.46%**（＝alpha 佔 NAV 比例本身；別與同段「占已投入非現金 1.57%」混用） | `python -c "import json;print(json.load(open('library/private/app/state/beta.json',encoding='utf-8'))['risk']['snapshot']['alpha_total_weight'])"` |
| 追蹤表 22 檔：籃子總報酬 **+0.03%**、最大單檔 **AXTI +2.29pp**、其餘 21 檔 **−2.26pp**、曾達 2 倍 **1/22**；**還沒有一檔滿 12 個月**（最長 57 天） | `python scripts/outcome_if_settled_today.py`（看「power-law 三量」段） |
| 結構讀圖 ledger **2 個節點**，其中 **1 份該重讀**（`mat:inp_substrate`） | `python -m query.structure mat:inp_substrate`、心跳第 2 段 |
| `downside` 假設 **0 筆**（每一檔的 13b 段都是「還沒寫」） | `python -m briefing alpha-card COHR`（13b 段）、`python -m alpha assumptions COHR --list` |
| 7 檔台股各 **24 個月**月營收；3081.TWO 2026-08 **YoY +180.90%** | `python -m engine_c.monthly_revenue --ticker 3081.TWO` |
| 無到期的等待 **0**；事件監看 93 | `python -c "from engine_b import leads;print(len(leads.parked_without_expiry(leads.load())))"` |

---

## 不得做

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、**因籃子空而放寬篩選條件**、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯（要改先量「幾列真的變了」）。

## 收尾格式

決策／收據區塊（若有要使用者決定的事，放**最前面**）→ HUMAN SUMMARY（5–10 行）→ 八欄 `STEP_RESULT`。
格式見 [`skills/development-flow/SKILL.md`](../../skills/development-flow/SKILL.md) Step 4.5／5
與 [`skills/daily-brief/SKILL.md`](../../skills/daily-brief/SKILL.md)「待核准項目的內容密度」。
**最後一行給可直接複製的批次指令。**

## 常設授權（2026-09-16 定案，2026-09-17 擴大到 Phase 邊界）

Step 的 Verdict 為 **GO** 且沒有待使用者決定的問題時，**直接合併 master 並接續下一個 Step 或 Phase**，
不逐 Step 請核准。**Phase 做完不是停止理由，Z2 本身不是停止理由，「想說一聲」更不是。**
使用者原話：「**我想要的是沒有需要我核准的事情就繼續**」。
Push 是常規動作，session 收尾把 master push 到 origin；push 前 sanity check：
`git ls-files library/private` 應為空。

---

## 歷程（每輪壓成一行；逐字收尾狀態在 git history）

| 輪次 | 做完的 | commit 範圍 |
|---|---|---|
| 2026-09-16 | Step 0（呈現契約重寫）＋ Phase 1 計畫核准 | `d06f5bf` 前後 |
| 2026-09-17 早 | Phase 1 Step 1.0／1.1／1.2（公司名稱解析、MFN／RNS 抓取器、D8 補三格） | …`fbc1b4f` |
| 2026-09-17 晚 | Step 1.3 收尾｜Phase 2 心跳＋排程｜Q1／Q2／Q4／Q5（結構讀圖、籃子賭注契約） | `fbc1b4f`…`e6f07d0` |
| 2026-09-17 深夜 | Phase 3（D5 計分表）｜AXTI InP 賭注寫下｜Phase 6 前兩項｜[602] 入圖 | `8eee2e1`…`65eec17` |
| 2026-09-18 早 | Phase 3 驗收行改寫＋標 ✅｜Phase 6 第三項＋標 ✅｜[603] 入圖｜Phase 2 第 1 天 | `19af823`…`c1e4638` |
| 2026-09-18 白天 | Phase 4 ①`constrained_by` 量測＋放閘｜Phase 5 D15 三個 power-law 統計量｜Phase 5 D2 對稱 overlay | `2140eca`…`9e23bd4` |
| 2026-09-18 下午 | Phase 5 歸零旗標四盞燈｜alpha 全歸零淨值｜D3 驗證＋移除心跳的 `PENDING_PHASE` 死表 | `a592ed8`… |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項。**
Step 0 的去向清單見 [`docs/refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)。

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**（全新點名聯亞與 IQE、英特磊點名全新與 IQE、
聯亞點名英特磊與 IQE）。證據方向一致指向「多家並存的量產供應層」。
**不得為了讓籃子非空而放寬門檻 4。**
