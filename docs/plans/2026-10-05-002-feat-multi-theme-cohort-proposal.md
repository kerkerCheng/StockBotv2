# 多主題等權組（電力、散熱兩鏈的組能落地）——PLAN_PROPOSAL

> **狀態：S1 ✅ GO（2026-10-06）；S2 兩鏈的組已鑄 pq2 [713]（電力）、[714]（散熱），等使用者 go。** 原狀態 PLAN_PROPOSAL → AWAITING_HUMAN（2026-10-05）；
> 2026-10-06 使用者選 A（非組員列具名缺席）→ S1 實作 → R2 CONDITIONAL_GO（C1、C2）→ 連同 F3 修完 → 窄範圍複審 GO（見文末「R2 與複審」）。Zoom **Z2**（量測口徑：追蹤表與計分表的組基準由「全域一組」改成「每一列用自己所屬的組」）；
> Review **R2**（命中 trigger 1：已核准的主題組 ledger 被讀的方式改變；Phase 7 plan Q7：開發 Step 命中 trigger 的 R2 常規 opt-in）。
> 出處：Phase 7 failure log #16（2026-10-05：「否（1 次）；但它擋住新鏈的第一份敘事——7.5 之前若有新鏈要寫敘事，要提前處理」）與 #26（同日，散熱鏈四份敘事寫在組落地之前）。
> 系統主動提出的開發項：**不主動要求 go**——排在 ROADMAP「旁支開發項」；要在 7.5 之前做，由你決定。沒有要你選的技術問題。

## 研究撞到了什麼（真實案例與次數）

| 日期 | 案例 | 撞到哪裡 |
|---|---|---|
| 2026-10-05 | P1／C1 入圖（[691]–[697]）後要定電力、散熱兩鏈的主題等權組（plan 7.1 ② ④） | `alpha.theme_cohort.measurement_cohort` 遇到多於 1 組就回 `ambiguous_cohort`——第二組一寫進 ledger，**光通訊各列的組超額與 G9 量測基準整格消失**；所以沒有鑄號（#16） |
| 2026-10-05 | research-drain 段 5 照閉環佇列寫了散熱鏈四份敘事（台達、健策、高力、富世達） | 組還沒落地，違反 plan 7.1 ④、驗收⑤（#26）；組員候選早約 5 小時已提交（`afdb4698`），組成不是事後挑的 |
| 2026-10-05（本提案盤點） | 題材 ledger 的檔名 | `alpha/providers/theme_cohorts.py` `slug()` 把非英數字元一律換成 `_`：「電力」「散熱」都是 `__.jsonl`，兩組一建就寫進同一個檔；`current_cohorts` 每個檔只挑一份現行組，**其中一組會被安靜蓋掉**（INV-3） |

電力鏈下一個要寫敘事的是 267260.KS、298040.KS、6501.T、CLF——閉環佇列今天停在它們前面，等組落地。

## 現在的邊界

- 讀：`current_cohorts()` 以**檔案**為單位挑現行組；`measurement_cohort()` 只接受全域一組（plan §12 #4「哪一組是基準只有一個答案」）。
- 用：追蹤表（`scripts/outcome_if_settled_today.py` 的 `_apply_theme_cohort`）把同一組套到三條 lane 的每一列；計分表（`engine_b/account_scorecard.py`）同一支。
- 三題的「主題等權組中位數／相對漲幅」列已經逐組印（多組時取第一組進 placeholder），**這一層不用改**。
- 寫：`ledger_path(theme)` ＝ `slug(theme).jsonl`，有碰撞。現有唯一一本：`AI_____CPO.jsonl`（「AI 光互連／CPO」）。

## 提議的邊界（兩個 Step）

1. **S1 讀寫與量測改成「每列自己的組」**
   - `current_cohorts()` 改以**題材**分組挑現行組（不以檔名）——就算檔名碰撞也不會蓋掉。
   - `ledger_path()`：題材已有 ledger 就沿用那個檔（掃描既有檔找同一題材）；新題材的檔名＝`slug` ＋ `_` ＋ 題材的 sha1 前 8 碼。**既有檔不搬**。
   - 新函式「這一列屬於哪一組」：以 `company_id` 比對組員——1 組＝用它；0 組＝具名缺席 `not_in_any_cohort`；≥2 組＝具名缺席 `ambiguous_membership`（列出組 id，不猜）。
     `measurement_cohort()` 留給「全域一組」的舊呼叫端（若還有），追蹤表與計分表改走新函式。
   - 測試：光通訊組＋兩個新組並存時，光通訊各列的組超額不變、新鏈各列用自己的組；「電力」「散熱」兩個題材各自讀得到自己的現行組；變異檢查（拿掉按題材分組 → 測試紅）。
2. **S2 兩條鏈的組**（研究 session，不是開發）：照 plan 7.1 ④ 寫 spec → `todo add-theme-cohort` → 使用者 go → `complete-theme-cohort`。
   散熱的組員以 2026-10-05 候選名單為準（奇鋐、健策、高力、富世達；commit `afdb4698`，早於第一份敘事）；電力的組員在研究 session 依 P1／P2 的讀圖列出。

### 已替你決定（不另問）

- 既有 ledger 檔不搬、不改名（搬檔＝動已核准的資料位置；讀取改成按題材分組就不需要搬）。
- 一檔同時是兩組的組員時不猜，具名缺席（跟現在 `ambiguous_cohort` 的精神一致，只是粒度從「全域」縮到「這一列」）。
- 不動任何人工 gate、不寫 thesis／敘事；組的組成仍是判斷、仍走 pq2。

## Success criteria（數的是追蹤表與稽核區，不是 filter 通過數）

1. 新增第二、第三組後，追蹤表三條 lane **有組超額的列數不減少**（前後對照；光通訊列逐列相同）。
2. 「電力」「散熱」兩個題材的 ledger 各自讀得到現行組（兩個檔、兩份現行）。
3. 散熱四份既有敘事（#26）在組落地後，稽核區的「主題等權組中位數／相對漲幅」由缺席變有值；電力鏈第一份敘事寫出時，追蹤表那一列有組超額、不是缺席。

## 如果這個修法是錯的，最先壞掉的是哪一筆（L11-6）

光通訊組的 15 個組員列：它們今天有組超額。S1 的第 1 條驗收就是逐列比對它們在新增組前後完全相同。

## SCOPE_ESCALATION（2026-10-05，使用者 go 之後、動手之前的查證）

```
Original zoom:   Z2（S1：每一列用自己所屬的組）
Observed issue:  驗收①「有組超額的列數不減少」的前提不成立——今天的追蹤表把唯一一組（光通訊）套到三條 lane 的**每一列**，
                 不只組員。實測（scripts/outcome_if_settled_today 的 lane 規劃，不取價）：history 22 列只有 7 列是光通訊組員，
                 另 15 列（META、NVDA、MU、MP、LYC.AX、6680.HK、6324.T、6268.T、6594.T、AEVA、AEHR、HIMX、TSEM、GFS、000660.KS）
                 今天的「對主題等權組超額」都是拿光通訊組當基準；paper 59 列只有 15 列是組員。
                 照本提案「0 組＝具名缺席」，有組超額的列會由 history 22→7、paper 59→15（加散熱 4 檔→19），驗收①照設計就不成立。
Recommended zoom: 仍是 Z2，但要使用者選非組員列的基準（下面三選一），選完才動 S1
Why local patch is insufficient: 「這一列跟哪個組比」是量測口徑的語意，不是實作細節——選哪一個都會改變追蹤表的數字
```

非組員列怎麼辦（三選一；**建議 A**）：

- **A 具名缺席（提案原設計）**：非組員列印 `not_in_any_cohort`，QQQ／SOXX 的超額照印。理由：拿稀土、機器人跟光通訊籃子比，
  是一個欄位承載兩種語意（組員＝同題材比較、非組員＝跨題材比較，L12）；補這些列的路是替它們的題材定組（研究），不是借別的組。
  代價：AVGO、MRVL、TSM 這類**同題材但不是組員**的列也會失去主題基準。驗收①改寫成「組員列逐列不變；非組員列由『對光通訊組
  的超額』改為具名缺席，列數與名單照印」。
- **B 維持現狀**：組員用自己的組，非組員一律對光通訊組——不建議（L12：同一欄兩種語意，下游讀不出差別）。
- **C 每一列宣告自己的題材**（例：組 spec 多一個「適用範圍」名單，或由該檔座位走到需求錨所屬的題材）——語意最準，但是新字彙、
  範圍超出 S1，要另起一格。

## 使用者 2026-10-06：選 A → S1 實作

- **驗收①改寫（選 A）**：組員列逐列不變；非組員列由「對光通訊組的超額」改為具名缺席 `not_in_any_cohort`，**列數與名單照印**
  （追蹤表每條 lane 的 `theme_cohort_excess.absent`、計分表每格的 filter reasons）。
- **實作**：`alpha/providers/theme_cohorts.py`（以紀錄的題材分組挑現行組；寫入沿用該題材既有檔，新題材檔名＝slug＋題材 sha1 前 8 碼）；
  `alpha/theme_cohort.py`（`cohort_for_row`＋`summarize_cohorts` 取代 `measurement_cohort`，缺席種類 `ROW_COHORT_ABSENCES`）；
  追蹤表 `scripts/outcome_if_settled_today.py`、計分表 `engine_b/account_scorecard.py`、APP（positions／account_scorecard 契約各升 /3）、心跳兩格。
- **四個變異都紅**：以檔挑現行組、檔名改回 slug、只有一組就每列都比、非組員點名不計理由。
- **真實資料驗收與 R2**：見 STEP_RESULT（本檔不重抄）。

### R2 與複審（2026-10-06）

- **R2（commit 6b568507）＝CONDITIONAL_GO**：C1 APP 計分表寫「不是組員的點名列在每格的濾掉理由裡」但頁面沒印；C2 組員但組報酬取不到的列
  不在 n 也不在缺席名單（paper 12＋45＝57、分母 58）；另找到既有問題 F3（錨點晚於最後收盤被算成 0.0）。使用者：「C1 修｜C2 修｜F3 修」。
- **修正（commit be98810b）**：計分表組那幾格印出濾掉的則數與理由；量得到報酬的列構造上不是有值就是具名缺席（新增 `theme_cohort_unpriced`、
  `no_measurement_window`）；`series_return` 起點晚於終點回 None、paper 錨點那根之後沒有新收盤→`no_close_since_anchor`、live 對稱面同；
  缺席短標籤收進 `alpha.theme_cohort.ROW_COHORT_ABSENCE_LABELS` 跟著資料走（L16）。
- **F3 的實際影響比 R2 估的大**：71 檔裡 66 檔的第一份 v2 敘事寫在 10-05，台股最後一根是 10-05（與錨點同一根）、美股資料源只到 10-02——
  修正前 paper 58 列報酬有 55 列是同一根 K 棒相除的假 0；修正後當天只有 3 列量得到。2026-10-06 那一行 `outcome_aggregate.jsonl`（daily 05:35 舊程式寫的）
  未改寫（使用者授權不含改舊紀錄）。
- **窄範圍複審（sonnet）＝GO**：C1 以 headless Edge 實際看到「濾掉 702／994 則：…不是任何組的組員 645」；C2 三條 lane 有值＋缺席＝分母；
  七個變異在隔離 worktree 重做都紅。non-blocking：markdown 逐列那一格還印種類字串——已當下修（印標籤）。
