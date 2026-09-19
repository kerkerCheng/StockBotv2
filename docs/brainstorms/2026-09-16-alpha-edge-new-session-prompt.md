# 給新 session 的啟動 prompt（2026-09-19 第十輪改寫；前九輪逐字狀態見文末歷程與 git history）

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
> 使用者原話（2026-09-17／09-18／09-19 共**四次**確認）：「**我想要的是沒有需要我核准的事情就繼續**」、
> 「**沒有需要我核准的就繼續走完**」、「**一樣不需要我核准的就繼續做到完**」（2026-09-19 傍晚，
> 與本檔的 `577 go` 同一句）。
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
> ### ▶ 這一輪的第一件事：**先看使用者的三個待決題**（見下方「等你決定的三題」）
>
> 上一輪（2026-09-19）把 **[577] 與七個系統性缺陷全部做完**了，中途鑄了三個待核准編號。
> 如果使用者這一輪沒有指定題目，**先把那三題問清楚**（它們各自會改變接下來做什麼），
> 再照常設授權往下做「不需核准的事」。
>
> ---
>
> ## ⚠⚠ 先讀這一段：上一輪修完七個缺陷之後，籃子為什麼還是只有一檔
>
> **2026-09-19 實測（改完之後重新量的，不是舊數字）：**
>
> ```
> 籃子 16 檔｜通過 filter 1（LITE）｜首選 LITE
> no_bet 13｜payoff_not_positive 2
> 催化劑那一格（本輪由一句話拆成四種形狀）：
>   catalyst_undated 6｜catalyst_missing_resolves 3｜no_catalyst_recorded 4｜catalyst_after_value_date 1
> ```
>
> **這四個數字第一次讀得出一句話：14 檔被催化劑那一格擋下，其中只有 GFS 這 1 檔是判準真的在運作**
> （它的催化劑有指名假設，但日期晚於目標價日）。**另外 13 檔全部是我們自己沒填**——
> 9 檔沒日期或根本沒記錄、3 檔只差一個 `resolves`。
>
> ⚠ **這不鬆動「籃子空就空」**：四個理由**全部仍然是 filtered**，被擋的檔數一個沒少，
> `resolves` 也**沒有**改必填。拆開只是讓「我們沒填」與「它真的不合格」不再長得一樣。
>
> **賭注帳同一天也拆開了**（七缺陷之 5）：
> ```
> 籃子     有賭注 3｜刻意不主張 0｜觀點已在 base、待決定 overlay 3｜欠一個答案 10
> 量的候選 通過 0｜觀點已在 base、待決定 overlay 8｜欠一個答案 4
> ```
> 量的候選那 15 家先前**12 家全被說成「沒人看過」，實際上三分之二的 base 已經有觀點**。
>
> ### 等你決定的三題（都不是我可以自己決定的）
>
> **① `sole_source_verification` 這個欄位要不要存在？**（[626] 收尾留下，上一輪沒動）
> 它在 `extractions/`／`schema/`／`prompts/`／`config/` 全都不存在，而 `schema/graph_schema.md` §7
> 把 `verified_by_absence` 定義成 **`sole_source=true` 時的驗證模式（弱主張）**——跟 `false` 並存會
> 反轉語意。三條路：①**不要這個欄位**（推薦；現況 `sole_source=false`＋`sole_source_evidence_quality=weak`
> 已足夠）；②改記在 `.review.md`（已寫）；③真要入圖就先進 `schema/vocab.json` 封閉字彙。
>
> **② 「多年反向橋」要不要提前？** 動 ROADMAP 的 Phase 排序要先給五欄 amendment。
> 支持提前的證據：D11 門檻通過的 5 檔有 4 檔「儀器算不出 payoff」（80%），被擋下的 11 檔只有 1 檔（9%）。
> ⚠ **L11-6 先做**：逐筆重讀那 4 筆 Abstention 的 `reason` 與 `revisit_when`——若其中任一筆其實不該
> abstain，80% 就會掉下來。**不要拿這個數字直接去改 Phase 排序。**
>
> **③ refresh 事件要不要按年度過濾？**（七缺陷之 2 只做了一半）
> 事件現在**標明**了年度（`FY2028（+1y）… 覆蓋 21 → 21 人`），但 `THESIS_POLICY` 仍把**任何**
> `consensus` 事件變成 `review_required`，不看年度。要讓「只有 base 校準年度的變動才觸發」必須給
> `ChangeEvent` 加年度維度（動 `alpha/refresh/contracts.py`＋`policy.py`，多個 owner）。
> ⚠ **L11-6：最先壞掉的是 COHR**——AGENTS.md 明文寫著它「thesis 講 FY28，模型只有 FY27 一格」，
> `+1y` 一律不觸發會讓跨年度 thesis 結構上收不到訊號。兩個選項：
> **(a)** 只有 base 年度觸發 `review_required`、其他年度降級成 note；
> **(b)** 兩個年度各自成事件、都觸發但在 UI 分開呈現（**現況等於 (b) 的前半**）。
>
> ### 三個待核准編號（上一輪鑄的；撞到就掛號，沒停下來等）
>
> - **[627] COHR sole_source 降級寫入**：`co:coherent→co:nvidia` 的 `sole_source` true→false ＋改寫首屏第三句。
>   追源已完成（packet 在 `library/private/alpha/sole_source_rejudge/coherent_nvidia.json`，
>   判讀紀錄在 tracked 的 `extractions/coherent_q3fy26_cpo.review.md`）。
>   **證據比 [626] 更強**：Coherent 自己的 10-Q 逐字寫著「**The non-exclusive agreement**」，
>   而 NVIDIA 的 partner blog 把 ELS 供應商逐字列成「**Lumentum, Sumitomo, and Coherent**」三家。
> - **[628] 圖缺口**：上一條的逐字已經在圖裡，但 `co:sumitomo_electric→co:nvidia` 這條邊從來沒被生出來
>   （L18 的另一面：逐字在，label 沒生）。
> - **[577] 已 resolve**（研究完成，receipt 是那份 packet）。
>
> ### ⚠ 已經做完、不要重做
>
> - **七個系統性缺陷全部交付**（1／2／4／5／6／7 於 2026-09-19，3 於同日稍早）。逐項的
>   before → after 數字寫在 ROADMAP 那七列裡，**要引用先去讀那一列**。
> - 不要重新校準 LITE 的 base、不要重寫 LITE／AXTI 的 variant／downside／短評。
> - 不要重做 `co:lumentum supplies_to tech:uhp_laser` 的 sole_source 判讀（[617]／[626] 已完成）。
> - 不要把「Lumentum is sold out through 2028」寫進假設（tier 3 二手，未追到一手）。
>
> ### ⚠ 不要做的
>
> - **不要換一個全新的標的池**——問題不在標的池，在儀器。
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
| 籃子 16 檔通過 1、首選 LITE；`no_bet` 13｜`payoff_not_positive` 2｜**催化劑四種形狀 `undated 6`／`missing_resolves 3`／`no_catalyst_recorded 4`／`after_value_date 1`** | 讀 `library/private/app/state/basket.json` 的 `filter` 與 `top_pick` |
| 賭注帳：籃子 `bet 3｜abstained 0｜opinion_in_base 3｜unanswered 10`；量的候選 `opinion_in_base 8｜unanswered 4` | 讀同一份 artifact 的 `bet_ledger`／`volume_bet_ledger`，或 `python crons/heartbeat.py` 第 4 段 |
| **目標倍數背離：全 ledger 生效 `target_pe` 49 筆｜`drift_exceeds 13`／`within_band 32`／`not_applicable 2`／`cannot_compare 2`**（門檻 5%） | `python scripts/target_pe_drift_check.py`（心跳段 2 也每天印一行） |
| **packet 的市值現在帶著單位走**：16/16 檔有 `quote_unit`（其中 6 檔非 USD），市值缺席 0 檔 | `python -m pytest tests/test_market_quote_unit.py -q`（4 條） |
| D11 門檻套用：input 16／accepted 5／filtered 11（缺值 0）；通過的 5 檔有 **4 檔儀器算不出 payoff** | `python scripts/alpha_screen_check.py` |
| 門檻值：市值 ≤ US$10B、覆蓋 ≤ 12（**兩條必須 AND**） | `python -c "import json;d=json.load(open('config/alpha_screen.json'));print(d['market_cap_max_usd'],d['analyst_count_max'])"` |
| `co:coherent supplies_to co:nvidia`：`sole_source` **仍是 `true`**（[627] 待核准才會改） | `python -m query.structure co:nvidia`——供給側 COHR 那列 `sole` 欄目前是 ✓ |
| `co:lumentum supplies_to tech:uhp_laser`：`sole_source` **`false`**（[626] 已寫入） | `python -m query.structure tech:uhp_laser` |
| LITE：base +4.4%｜賭對了 +5.7%｜**判斷錯了 804.21（−13.6%）**；AXTI **判斷錯了 35.15（−49.8%）**；兩檔首屏都印得出下檔 | `python -m briefing alpha-card LITE`／`AXTI` |
| **有短評的檔 3 筆**（LITE／AXTI／COHR）；COHR 沒有 downside scenario，首屏刻意不寫下檔句 | `python -m alpha brief COHR --list` |
| `Catalyst.resolves` 填寫率：judgments/ **62 檔 104 條，填 0 條**（沒有改必填，刻意） | ROADMAP 該列的查證命令 |
| 可投資排序 **37 列**；filter `input 221／accepted 37／filtered 184` | `python -m query.bottleneck --top-n 60` |
| `audit invariants` FAIL 0／PASS 13／共 4,239 筆 | `python -m audit invariants` |
| 待辦池：**pq2 球在你手上 18**（含新鑄的 [627][628]） | `python -m engine_b.todo list` |
| 追蹤表 22 檔｜量測起始 2026-07-21｜**還沒有一檔滿 12 個月**（最長 59 天） | `python scripts/outcome_if_settled_today.py` |
| 心跳排程每日 07:00｜Last Result 0 | `schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V` |

⚠ **pytest 要用 `.venv\Scripts\python.exe`**，裸的 `python` 沒有 pytest。
⚠ **`python -m webapp materialize`（不帶旗標）只重建各檔 overview，不重建 basket**——
兩個都要就分兩次跑，而且**順序是先 overview 再 `--basket`**（上一輪在這裡量錯過一次）。

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
| 2026-09-19 早 | `is_component_of` 全重判 92 條｜新增 `is_variant_of`｜[614] 8 條修正｜[615] 4 對合併｜AXTI downside｜[571]–[575] drop | `fec9db6`… |
| 2026-09-19 上午 | [616] 紅隊審查撈到倍數陳舊｜[617] sole_source 追源→鑄 [626]｜D11 兩條門檻落地｜量到「通過的 5 檔有 4 檔算不出 payoff」 | … |
| 2026-09-19 中午 | [626] 寫入：`co:lumentum→tech:uhp_laser` 的 `sole_source` true→false｜排序位移 #2→#5 | … |
| 2026-09-19 下午 | 七缺陷之 3：overlay scope 未命中 base 時寫入端拒收＋8 條守門測試 | … |
| **2026-09-19 這一輪** | **[577] 追源完成（鑄 [627][628]）＋七個缺陷剩下的六個全部交付**：7 報價單位跟著市值走｜6 目標倍數背離偵測＋心跳常駐計數器｜2 覆蓋崩塌不再發假警報｜4 首屏講得出「判斷錯了值多少」｜5 「欠一個答案」拆成兩格｜1 催化劑四種形狀分開。**全量測試 2,727 passed／0 failed；`audit invariants` FAIL 0** | `8919afc`…本輪 |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項，也不要重做 V1／V2／V3。**

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**。**不得為了讓籃子非空而放寬門檻 4。**
