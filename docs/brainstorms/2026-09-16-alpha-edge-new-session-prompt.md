# 給新 session 的啟動 prompt（2026-09-17 改寫；原 2026-09-16 版見文末歷程）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。

---

## 開工指令（貼這一段）

> ## ⚠ 2026-09-17 收尾狀態（先讀這塊，再讀下面的任務書）
>
> **這一輪做完的：** Phase 1 Step 1.3 收尾｜Phase 2 Step 2.1（心跳產生器）＋ 2.2（接上獨立 Windows 排程
> `StockBotv2-Heartbeat` 每日 07:00、`drain_limit_per_run` 5→0、`.codex/rules` 20→15）｜
> pq2 [587]–[590] 四項研究＋[591][594] 入圖｜`rank_bottlenecks()` 補上 INV-3 的 filtered 報表。
>
> **Q1–Q5 使用者已於 2026-09-17 全部照建議核准。下一輪直接開工，不必再問。**
>
> | | 決定 | 狀態 |
> |---|---|---|
> | **Q2** 籃子每列強制「有賭注 或 Abstention」，不准空白 | A | ○ **下一輪第一件** |
> | **Q5** 讀圖落地 append-only ＋ staleness 分級 ＋ 掛心跳與 pq1 | A | ○ 接著做 |
> | **Q1** 籃子宇宙擴到被門檻擋下的那 26 條，分兩個分頁 | A | ○ 排 Q2／Q5 之後 |
> | Q3 量的賭注的反向橋 | B：留 Phase 7 | — |
> | **Q4** 結構讀圖（零 LLM 查詢） | A | ✅ **已交付** `python -m query.structure <node>` |
>
> **為什麼 Q2 排第一（實測，不是偏好）：** 籃子 16 檔**沒有一檔**因 substitutability 被擋，
> **15 檔卡在 `no_bet`**——開別的門、擴別的宇宙，如果進來的東西一樣沒人寫賭注，籃子還是空的。
>
> **Q5 的設計已經寫完了，直接照做**（見 structural-reading-layer.md §5b／§6b）：
> 存輸入不存結論、staleness 分級（`documents` 計數變動不得觸發）、
> 落點是 pq1 新段不是心跳、必須有到期、**staleness 直接接既有 disproof 機制不另立通知路徑**。
>
> §2e 未做完清單裡 [586] 已設 pending（等外部文件），其餘已結案。
>
> **兩份必讀的新文件：**
> [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md)（為什麼籃子空的真正原因）
> 與 [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md)（瓶頸性不是一條邊）。
>
> ⚠ **Phase 2 尚未完成**：驗收要「連續 3 天心跳零 LLM 成功發出」，**最早 2026-09-20 才驗得完**。
> 查證：`schtasks /Query /TN StockBotv2-Heartbeat /FO LIST /V`（看 Last Run Time 與 Last Result）。

**任務：Q2 →（Q5）→（Q1），三件都已核准。** Phase 1 四個 Step 與 Phase 2 的 Step 2.1／2.2 都已交付並合併 master。
⚠ **Phase 1 刻意維持 ▶ 不標 ✅**（TW／TWO／ST 實測 0）；**Phase 2 也尚未完成**（等 9/20 的三天心跳驗收）。
兩者都不必重做。

**先讀（順序固定；這一輪需要的全部在這裡，沒有第七份）：**

| # | 檔案 | 為什麼這一輪需要它 |
|---|---|---|
| 1 | `AGENTS.md` | 憲法、六條 invariant、四個人工 gate、L1–L17（一字不動）。⚠ 尤其「Alpha 呈現契約」與 L7（disproof 三件套）——Q2 直接動到它們 |
| 2 | [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | **Q2／Q1 的全部依據**。籃子為什麼空的量測、A／B 兩種賭注、三條「改掉 substitutability」為什麼都是錯的 |
| 3 | [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md) | **Q5 的完整設計**，§5b（存輸入不存結論）與 §6b（怎麼 trigger 重新推理）**照做即可，不要重新設計** |
| 4 | [`docs/ROADMAP.md`](../ROADMAP.md) | **進度與驗收的唯一權威**。Phase 4 那一列（Q1／Q2 要改它的定義欄，需先給五欄 amendment）、Phase 2 那一列、completion gate 八項 |
| 5 | [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | **決定紀錄 D0–D15**（使用者原話）。⚠ Q2 動到 D2（賭注與「判斷錯了值多少」對稱）、D3（`realized` 只提醒）、D15（power-law 統計量） |
| 6 | `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md` | Zoom／Review 判定與八欄交付格式。Q2 改籃子契約，**至少 Z2** |

**只在需要時才讀（不必一開始載入）：**

| 檔案 | 什麼時候 |
|---|---|
| [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md) | 要查 Phase 1 做過什麼、§2e／§2f 六項的處置結果 |
| [`2026-09-17-alpha-edge-phase2-plan.md`](2026-09-17-alpha-edge-phase2-plan.md) | 要查心跳怎麼來的、Step 2.3（分類層）還沒做什麼 |
| `docs/OPERATIONS.md` | 要實際跑操作時（「心跳」節、「Daily / pq1 / 待辦池的參數」節） |
| `docs/ARCHITECTURE.md` §4.1／§8 | 要動 Daily 三層或 APP 呈現時 |

⚠ **本輪不必讀的**：其餘 15 份 brainstorm 都是 2026-07～08 的舊題目（confidence 五軸、capital expression、
event watch…），與 Alpha Edge 無關。**Alpha Edge 只有上面列的 6 份 brainstorm ＋ ROADMAP。**

~~**Step 1.3 要做的四件：**~~（2026-09-17 全部完成，見 ROADMAP 與計畫檔 §2d／§2e；以下留作歷程）

1. **ROADMAP Phase 1 驗收行回填 before → after 實測值。** 舊句劃線加日期留原地，不靜默刪除。
   四個 Step 的實測值都在計畫檔 §2／§2b／§2c，但**回填前先自己跑一次查證命令**，不要抄現成數字。
2. **Phase completion gate 八項逐項核對**（ROADMAP「每個 Phase 的 completion gate」），
   每項寫「過／不過＋依據」。第 8 項（該 Phase 負責的 critical historical failure 已有 executable protection）
   要對照 `docs/refactor/historical-failure-matrix.md` §9 的責任分配。
3. **標記 Phase 1 狀態。** ⚠ **驗收行明訂：可投資排序的 TW／TWO／ST 檔數仍為 0 就不得標完成**——
   2026-09-17 實測確實是 0。所以只能標「**研究已做、證據不足以進榜**」並**逐項列出缺哪份文件**，
   **不得為了讓籃子非空而放寬門檻 4**（`AGENTS.md`：籃子空就空，讓它非空的路是研究）。
4. **決定 §2c「未做完清單」四件的去向**（併入 Phase 4 篩選層，或另立 pq2）。這四件需要使用者判斷，
   所以**交回 Step 1.3 結果時把它們列成待決問題，停下等使用者**——不要自己決定。

**Step 1.3 完成後，沒有待使用者決定的事就直接接著做 Phase 2，不要停下來問。**
（2026-09-17 使用者定案，`AGENTS.md` 常規推進授權已擴大到 Phase 邊界：**Phase 做完不是停止理由**。）
Phase 2 是 D12 心跳＋分類——改排程、`drain_limit_per_run` 歸零、Codex fixed entry 與 permission test
同 change 對齊。它動到 unattended surface，所以**必出 `PLAN_PROPOSAL` 並同 change 做 sandbox impact
review 五步**；但 **plan 是思考紀律不是核准請求**——plan 裡若沒有需要使用者選的問題（ROADMAP Phase 2
那一列已定義到可直接執行），照出 plan 然後往下做。

**真正要停下來等人的只有這些：** 四個人工 gate（graph admission／Engine C 判讀寫入／thesis mutation／
live）、資本或任何 append-only authority、要改 `AGENTS.md` 判準句或 ROADMAP 的 Phase／Step 定義、
需要 R2、Verdict 不是 `GO`、或 plan 裡真有要使用者選的問題。
⚠ **撞到 pq2 就掛號繼續做下一件不需核准的事**，收尾一次給批次指令——**不得停在編號上等**。

**不得做：** 部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬篩選條件、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯。

**收尾格式：** HUMAN SUMMARY（5–10 行）＋ 八欄 `STEP_RESULT`；有待使用者決定的事，
決策區塊放最前面（格式見 `skills/daily-brief/SKILL.md`「待核准項目的內容密度」）。

---

## 現況與查證命令（引用前先跑）

| 現況（2026-09-17 實測） | 查證命令 |
|---|---|
| 可投資排序 37 列／17 家；TW／TWO／ST **0 檔**；IQE.L 第 9 | `python -m query.bottleneck --top-n 60` |
| `audit invariants` FAIL 0／PASS 13（4,087 筆） | `python -m audit invariants` |
| 全套 pytest 2,481 passed／1 skipped | `python -m pytest -q` |
| 待辦池無本 Phase 未決編號 | `python -m engine_b.todo list` |
| `.ST`／`.L` 各 5 條路由，rung2 的 `mfn`／`rns` 皆 `verified=true` | `python -m sourcing.routes SIVE.ST` |
| canonical 邊 529 條、materialized 屬性 358 個 | `python -m loader.edge_resolution project --dry-run` |
| 七家有 `product_line_revenue_share`（AEHR 缺） | `python -m engine_c.set_manual_field --list 3081.TWO` |

## Phase 1 已完成的四個 Step（細節在計畫檔，不在這裡展開）

- **1.0** 公司名稱解析歸位——排序的證據分級改讀 registry 真有的 `display_name`（改判 39 條邊）
- **1.1** `fetchers/mfn.py`＋`fetchers/rns.py`＋`.ST`／`.L` 路由階＋三條管道各一份 smoke 文件
- **1.2** D8 補三格：七家產品線營收占比、四條新供應邊、聯亞 `substitutability`=3；
  Tower 自家公告補 IQE 的客戶端外部印證（IQE.L 第 12 → 第 9）
- **兩個當下修掉的靜默缺陷：** MOPS 的 PDF 吐出 CJK 相容表意文字害逐字比對失敗（`fetchers/mops.py` 加 NFC 正規化）；
  publish preflight 把 supersede 走廊的正常改寫當成「別的 writer 動過」而擋死六筆已核准的入圖
  （`intake/publish.py` 把兩種語意分開）

## Phase 1 的核心發現（Step 1.3 要如實寫進 ROADMAP）

**補完格之後排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的 substitutability
全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：**各家在自家年報裡逐字
互相具名指認對方是同層競爭者**（全新點名聯亞與 IQE、英特磊點名全新與 IQE、聯亞點名英特磊與 IQE）。
證據方向一致指向「多家並存的量產供應層」。

---

## 歷程（舊狀態行，不靜默刪除）

> ~~**狀態（2026-09-16）：Step 0 已核准並合併進 master（branch `docs/alpha-edge-step0`）。**
> 新 session 照下面順序讀完文件後，**直接從「Step 1 以後」開始**：先出 Phase 1 的 PLAN_PROPOSAL（Z3），停下等核准。~~
>
> ~~**狀態（2026-09-16 21:30）：** Step 0 已合併；Phase 1 PLAN 已核准（決策 A go／B 選 1／C 選 1／D 選 2，
> 順序 1.0 → 1.1 → 1.2 → 1.3）；Step 1.0 已 GO 並合併 master（merge `d06f5bf`）。**從 Step 1.1 開工**。~~
>
> ~~**狀態（2026-09-17 早）：** Step 1.1 已 GO 並合併 master；三份 smoke 文件的 RA 已 prepare 為
> pq2 [579][580][581]，入圖待使用者批次 go。**從 Step 1.2 開工**。~~
>
> ~~**狀態（2026-09-17）：** Step 1.1 與 1.2 都已做完；六個 pq2 編號 [579][580][581][583][584][585]
> 等使用者批次 go。**從 Step 1.3 收尾開工。**~~
> （2026-09-17 使用者已批次 `go`，六筆全部 apply → push → `complete-ra` 結案；
> 本檔正文於同日改寫為從 Step 1.3 開工，上列狀態行改置於此。）
>
> ~~**狀態（2026-09-17 晚）：** 從 Step 1.3 收尾開工。~~
> （Step 1.3 同日完成：ROADMAP 驗收行回填、completion gate 八項逐項核對、Phase 1 維持 ▶ 不標 ✅、未做完清單擴為六項待使用者決定去向。**本檔正文改寫為從 Phase 2 開工。**）

**2026-09-16 原版正文（Step 0 任務書）已完成並封存**——去向清單見
[`docs/refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)，
Phase 1 的核准計畫與工單見 [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md)。
**不要重做 Step 0，也不要重做 Step 1.0／1.1／1.2。**

**常設授權（2026-09-16 使用者定案，仍有效）：** Step 的 Verdict 為 **GO** 且沒有待使用者決定的問題時，
**直接合併 master 並接續下一個 Step，不逐 Step 請核准**。仍要停：Verdict 非 GO、有待決問題、
動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句、需要 R2。
pq2 的圖寫入（`ra_admission`）與 Engine C 判讀寫入仍逐筆核准——研究段落收尾照常給批次指令。
