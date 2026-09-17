# 給新 session 的啟動 prompt（2026-09-17 改寫；原 2026-09-16 版見文末歷程）

> 用法：在新的 Claude Code session 貼「開工指令」那一段，或直接
> `@docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md`。
>
> ⚠ **本檔的狀態句會腐壞**（`AGENTS.md`「現況數字會過期，判準不會」）。
> 每句現況都附了查證命令，**引用前先跑那一條**。進度的唯一權威是
> [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表與 `library/leads/todo_pool.json`，不是本檔。

---

## 開工指令（貼這一段）

**任務：Alpha Edge Phase 1 的最後一步 Step 1.3「收尾」。** Step 1.0／1.1／1.2 都已完成並合併 master，
六個 pq2 編號已由使用者批次 `go`、全部入圖並 `complete-ra` 結案。

**先讀（順序固定）：**
1. `AGENTS.md`（憲法、六條 invariant、四個人工 gate、L1–L17：一字不動）
2. `docs/brainstorms/2026-09-16-alpha-edge-phase1-plan.md`
   （§0 核准紀錄與常設授權、§2b Step 1.1 結果、**§2c Step 1.2 結果與未做完清單**、§1 的 Step 1.3 驗收行）
3. `docs/ROADMAP.md`（Phase 1 那一列的驗收欄，與「每個 Phase 的 completion gate（八項）」）
4. `docs/AGENT_WORKFLOW.md` ＋ `skills/development-flow/SKILL.md`（Step 1.3 判為 **Z0／R0**：只回填文件與核對，
   不動程式；若途中發現需要動程式，先重判 Zoom）

**Step 1.3 要做的四件：**

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

**Step 1.3 完成後不要自行開始 Phase 2。** Phase 2 是 D12 心跳＋分類（改排程與 Codex fixed entry），
動到 unattended surface，屬常規推進授權的例外，必須先出 PLAN_PROPOSAL 等核准。

**不得做：** 部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬篩選條件、
把 last30days 串進無人值守管線、改 `rank_bottlenecks()` 的排序邏輯、擅自開始下一個 Phase。

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

**2026-09-16 原版正文（Step 0 任務書）已完成並封存**——去向清單見
[`docs/refactor/alpha-edge-step0-migration.md`](../refactor/alpha-edge-step0-migration.md)，
Phase 1 的核准計畫與工單見 [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md)。
**不要重做 Step 0，也不要重做 Step 1.0／1.1／1.2。**

**常設授權（2026-09-16 使用者定案，仍有效）：** Step 的 Verdict 為 **GO** 且沒有待使用者決定的問題時，
**直接合併 master 並接續下一個 Step，不逐 Step 請核准**。仍要停：Verdict 非 GO、有待決問題、
動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句、需要 R2。
pq2 的圖寫入（`ra_admission`）與 Engine C 判讀寫入仍逐筆核准——研究段落收尾照常給批次指令。
