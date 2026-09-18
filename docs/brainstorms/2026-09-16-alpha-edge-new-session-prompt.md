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

> ## 現在的狀態（2026-09-18 收尾）
>
> **開工三件事（每次都跑，不要憑記憶）：**
> ```
> date                                                    # 檔案裡的「今天」不可信
> python scripts/writer_guard.py check                    # writer_lock 應為 null、daily_done_today
> schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V     # Last Run Time / Last Result / Next Run Time
> ```
>
> **Phase 狀態：Phase 1 ▶（研究已做、證據不足以進榜）｜Phase 2 ▶（等驗收）｜Phase 3 ✅｜Phase 4 ▶｜Phase 5 ○｜Phase 6 ✅｜Phase 7 ○。**
>
> **⚠ Phase 2 的「連續 3 天心跳」進度（每天實測一次）：第 1 天 ✅ 2026-09-18 07:00:01 自動觸發、
> `Last Result 0`、publisher `sent` 2/2。第 2 天＝09-19、第 3 天＝09-20。**
> 那是等時間不是等工作；在 3 天湊滿之前 Phase 2 不標完成。
> 查證：`library/private/heartbeat/heartbeat_task.log` 逐日一段。
>
> **這兩輪做完的（2026-09-17 深夜 ～ 09-18）：**
>
> | | 交付 | before → after |
> |---|---|---|
> | **Phase 6** 台股月營收進 Engine C | `engine_c/monthly_revenue.py`＋`fetchers/mops_open_data.py` | 3081.TWO **0 → 24 個月**（7 檔台股共 175 列） |
> | **Phase 6** MOPS 重訊 watcher | `harvest_mops`＋`mops_watch` config | harvest 來源 **29 → 36**；**第一天自動跑就抓到 3 則**（見下） |
> | **Phase 6** 沒有到期的等待 | `leads.parked_without_expiry()`＋心跳第 3 段計數器 | 黑洞 **3 → 0** |
> | **Phase 3** 驗收行改寫（A 案） | `Metric.revisit_after` | 90 天兩格由「沒有值」變成「沒有值＋**2026-09-27 會有**」 |
> | **[602]** AXT↔JX competes_with 入圖 | commit `8c76bde` | `query.structure co:axt` 反向路徑 **1 → 2** |
> | **[603]** gsr cl2 的過期分句與已觸發 disproof | commit `19af823` | statement／disproof 就地標記，as-of 那句**逐字保留** |
>
> **⚠ 這兩輪最該記住的三件事：**
>
> **① 兩個 pq2 的提案診斷都被實測推翻，而兩次查詢都在動手前跑。**
> [602] 說「圖裡缺 AXT↔JX 的邊，所以 JX 的擴產證據不在 AXT 的 context slice 裡」——實測**最短路徑
> 本來就是 2 跳**，擋住它的是 `LIMIT`（兩跳內 **154 條 claim**，讀圖只印 **20** 條，排序鍵是 proof level
> ＋confidence，**不是相關性**；`claim_limit=20` → JX 出現 0 次、`=200` → 7 次）。**補邊改不動那件事。**
> [603] 提案說「措辭過期」——實測是**那條 claim 自己的 disproof 在寫下一個月後就被觸發**
> （條件逐字寫著「any of the three announces a material capacity expansion」，JX 2026-06-16 做了），
> 而**觸發它的那份新聞稿就在同一張圖裡**，三個月沒有任何東西響過。
>
> **② 兩個機制缺口已寫進 ROADMAP backlog（🔴，待 Z2），不要在不知情的情況下再撞一次：**
> **(a)** `query/graph_context.py` 的 claim 截斷不說話——**409 條 claim 全部帶 `disproof_condition`，
> 被標成 TRIGGERED 的只有 1 條**（就是本輪手動標的）；對照組是 Q5 的結構讀圖 staleness，
> **同一族的機制、claim 這一側沒有**。
> **(b)** 心跳排 07:00 而 daily 07:26 才結束，**心跳第 1 段每天報的都是「昨天」**
> （實測：心跳說 APP 今天 materialize 0 份，20 分鐘後是 8 份）。修法不是把心跳延後——
> 那會弱化它存在的全部理由（daily 死掉時心跳照發）。
>
> **③ MOPS 重訊 watcher 第一天自動跑就抓到三則有研究價值的，已在 pq1 排隊：**
> **3105.TWO 穩懋「訂購廠務工程」NT$353,562,825**（累計訂單，擴產資本支出的一手證據）；
> **2455.TW 全新「二」「三」兩檔可轉債行使贖回權**——觸發條款逐字是「普通股收盤價**連續三十個
> 營業日超過轉換價格達 30%**」，且贖回會逼 CB 轉普通股＝**稀釋**（核驗清單五項之一）。
> 這是 Phase 6 的第一個真實產出，**不是靠人記得去看**。
>
> **待使用者決定：目前沒有。** [602][603] 都已結案。
>
> **不需核准就能接著做的（依序建議）：**
> **① Phase 4 的 `constrained_by` 那一條**（開發項）：`query/bottleneck.py` 的 `UPSTREAM_RELATIONS`
> 只有 `("enables", "is_component_of")`，不含 `constrained_by`，所以 `tech:cpo_full_stack_test`／
> `tech:inp_dfb_laser` 走不到需求錨。⚠ **驗收行明訂要先量「加了之後有幾列真的變了」再決定放不放閘**
> （L14-3：先量測後放閘）——那是一次唯讀量測，做完才知道值不值得動。
> **② Phase 5 的表達層**（D2 對稱 overlay「判斷錯了值多少」、歸零旗標、三個 power-law 統計量）。
> ⚠ **Phase 4 剩下的兩條機械條件（覆蓋厚薄、瓶頸業務占營收）仍然不該做**——實測會讓 0 家變 0 家。
>
> ⚠⚠ **binding constraint 連續四輪沒有動過：籃子 16 檔 `bet` 2、`abstained` 0、`unanswered` 14。**
> 能讓籃子非空的只有兩條路，**兩條都要人**：①替某一檔寫下帶 disproof 的賭注；
> ②寫一筆 `bet/variant.overlay` 的 Abstention。**兩者都是答案，只有空白不是。**
> 上面那兩件開發項**都不會碰到它**——這點要對使用者說清楚，不要讓交付看起來像進展。
>
> **月營收的消費端今天很窄，刻意沒補**：只到達心跳的新鮮度行與 CLI——你看得到「有沒有跟上」，
> **看不到「聯亞 8 月 YoY +180.90%」**。要不要讓它進 APP／隱含報酬橋是呈現契約的決定。
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

| 現況（2026-09-18 實測） | 查證命令 |
|---|---|
| 可投資排序 **37 列**；**TW／TWO／ST 仍 0 檔**（6 檔台股在「低於門檻」區） | `python -m query.bottleneck --top-n 60` |
| canonical 邊 **530**、materialized 屬性 **363**；`substitutability` 覆蓋 **91/530（17%）** | `python -m loader.edge_resolution project --dry-run` |
| `audit invariants` FAIL 0／PASS 13（**4,183 筆**） | `python -m audit invariants` |
| 全套 pytest **2,620 passed／1 skipped** | `python -m pytest -q` |
| 待辦池未結案 **35** 項；**pq1 可做 11**（含 3 則 MOPS 重訊） | `python -m engine_b.todo list`／`python crons/heartbeat.py` |
| 籃子 16 檔：`bet` **2**｜`abstained` **0**｜`unanswered` **14**；量的候選 15 家通過 **0** | 讀 `library/private/app/state/basket.json` 的 `bet_ledger` |
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
| 2026-09-18 | Phase 3 驗收行改寫＋標 ✅｜Phase 6 第三項＋標 ✅｜[603] 入圖｜Phase 2 第 1 天 | `19af823`…（本輪） |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項。**
Step 0 的去向清單見 [`docs/refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)。

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**（全新點名聯亞與 IQE、英特磊點名全新與 IQE、
聯亞點名英特磊與 IQE）。證據方向一致指向「多家並存的量產供應層」。
**不得為了讓籃子非空而放寬門檻 4。**
