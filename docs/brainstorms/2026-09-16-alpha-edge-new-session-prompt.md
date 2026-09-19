# 給新 session 的啟動 prompt（2026-09-19 第十三輪改寫；前十二輪逐字狀態見文末歷程與 git history）

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
> ⚠⚠ **2026-09-19 實測代價（同一個 session 內犯了兩次，第二次被使用者當場質問「不需核准你為何停？」）：**
> 停的理由寫成「**這一輪已經到一個完整交付點**」「**下一步有多條路，值得讓使用者知道現況再決定**」
> ——**那兩句都是「想說一聲」的變體，是明文排除的理由**。當時的 token 餘額是 1,490 萬，
> 不是 context 不夠，**是判斷錯誤**。
> **操作化成一個問句：我現在要停，是因為「有東西非你決定不可」嗎？**
> 如果答案是「不是，但我覺得該回報一下」——**那就繼續做，把回報留到真的停下來的時候**。
> ⚠ 同一個 session 裡做了九件事**不構成**停止理由；交付清單長**不構成**停止理由。
>
> **收尾時**：更新本檔，**下一份 prompt 必須原樣帶著上面這整個「常設授權」小節**。
>
> ### ▶ 這一輪的第一件事：**出 Phase 7 剩餘的 plan（含五欄 amendment），然後停一次**
>
> **Phase 0–7 之中，只剩 Phase 7 的後半與依賴它的 Phase 4b 沒做。**
> Phase 5 已於 2026-09-19 標 ✅（八項 gate 全過；驗收行使用者定案取「**有賭注的檔都要有對稱的下檔**」，
> 今天 payoff 與 downside 都是 AXTI／COHR／LITE，3/3）。
>
> Phase 7 的目標逐字是「**多年反向橋取代 FY+1 主流程；entry criterion 降級**」。
> 7.1–7.4 已交付（倍率參數化／`multiple_horizon`＋`span_years`／`briefing multi-year` CLI／進 APP），
> **但「取代」還沒發生**——多年橋今天是**並列的另一條路**，主 view 的 target 仍永遠是基期+1。
> ⚠ **剩下的部分還沒拆成 Step**，而拆 Step 要先給五欄 amendment（`AGENTS.md`）——
> 所以這一輪的正確產出是**一份 PLAN_PROPOSAL ＋ 五欄 amendment**，交回來等一次核准。
> 那份 plan 至少要回答：①「取代」是換掉還是並存後改預設？②`entry criterion 降級`降到哪？
> ③Phase 4b 的驗收（「多年橋算得出倍率與它的前提鏈，且每一格配 disproof」）怎麼機械驗證？
>
> **出 plan 之前與之後，不需核准的事照做完**（下面兩件都是）：
>
> - **`multiple_horizon` 只有 COHR 一檔填了**（62 檔裡 1 檔），心跳每天印「還沒寫下目標年度 15」。
>   ⚠ **填它是 judgment 走 pq2**——要有那一檔自己的一手依據（COHR 用的是 10-Q 逐字
>   「support future production volumes **through 2030**」）。**沒有依據就不要填**；
>   有依據的可以鑄號一次批多檔。
> - **pq2 球在你手上 17 項**，其中多數是「等世界發生某事」。開工時掃一次，
>   把真的能動的挑出來做掉，不能動的維持原狀。
>
> ### 還有一個要你給兩個數字才能動的：Phase 2 Step 2.3（分類層）
>
> 它是 D12 三層（心跳／分類／研究）的**中間那層**：讓便宜模型每天自動分流新 lead，
> 有每日硬上限、失敗不阻斷心跳。⚠ **它會每天自動花錢，所以模型與上限是使用者的決定。**
> ⚠ **先看量測再決定要不要做**：近 16 天每日新 lead 平均約 15 則（2–26），
> 而「未 triage」長期只有個位數——規則式 auto-no-go 已經在清大部分。
> **上一輪的建議是先不做**；使用者若要做，請給「哪個便宜模型」與「每日幾則上限」兩個數字。
>
> **這幾件之外沒有需要核准的事就直接做，不要為了回報而停。**
>
> ### 還有一個槓桿，但它要核准：填更多檔的 `multiple_horizon`
>
> 多年橋整條鏈已經通了（CLI／artifact／API／APP 頁面／心跳計數器），但 **62 檔裡只有 COHR 一檔
> 寫下了「倍率在哪一年實現」**。心跳每天會印「還沒寫下目標年度 15」。
> ⚠ **填它是 judgment 走 pq2**——要有那一檔自己的一手依據（COHR 用的是 10-Q 逐字
> 「support future production volumes **through 2030**」）。沒有依據就不要填。
>
> ⚠ **Phase 4a 的最後兩條已經量完，結論都是「今天不該接」**（不是待辦，是已結案的判斷）：
> 入圖日那條缺的是資料歷史長度（圖只有 69 天）、瓶頸業務占比那條缺的是那個數字本身。
> 逐項實測見 ROADMAP Phase 4a 那一列與 `python scripts/alpha_screen_check.py`。
>
> ### ▶ 已完成（不要重做）：Phase 7 的 7.1–7.4
>
> [630] 已核准並執行：**COHR 的第一條多年橋跑通了**（FY2030，距基期 4 年）：
> **2 倍需要 Datacenter & Communications 分部四年累積成長 4.65 倍**；**3 倍以上所有 driver
> 拉到極限都做不到**。⚠ 這是系統第一次說出**可以去查證**的話。
>
> **整條鏈已經通到 APP**（Step 7.4）：`python -m briefing multi-year <T>`｜
> `python -m webapp materialize --multi-year`｜`GET /api/v1/multi-year`｜導覽列「要幾倍」｜
> 心跳段 4 每天印「還沒寫下目標年度 N」。
> ⚠ 它**必須**是 materialize 出來的——多年橋是金融模型，APP 契約禁止 request path 跑模型。
> ⚠ 它**沒有污染 FY+1 主 view**：`build_fundamental_model` 的 target 永遠是基期+1，
> FY2030 的假設被 refresh 正確標成「不是目前目標期間；本視角不評估」。
>
> ⚠ **籃子現在是空的（通過 0、首選無），而那是合法結果**——Phase 4a 接上市值與覆蓋
> 兩條門檻後，LITE 以 **83.5B／25 位覆蓋**被擋掉。它從來就不是「邊緣小公司」。
>
> ---
>
> ## ⚠⚠ 先讀這一段：上一輪修完七個缺陷之後，籃子為什麼還是只有一檔
>
> **2026-09-19 實測（改完之後重新量的，不是舊數字）：**
>
> ```
> 籃子 16 檔｜通過 filter 0｜首選 無     ← Phase 4a 接上三條門檻之後
> market_cap_above_max 10｜analyst_count_above_max 9｜no_externally_corroborated_edge 7
> no_bet 13｜payoff_not_positive 2
> 催化劑那一格（拆成四種形狀）：
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
> ### 三題已答（2026-09-19，使用者「三題找你推薦」後全部落地）
>
> **① `sole_source_verification` 欄位 → 不要。** 決定已寫進 `schema/graph_schema.md` §7
> （降級後的正確表達只有 `sole_source=false` ＋ `sole_source_evidence_quality=weak` 兩欄，
> 判讀理由寫 `.review.md`）。⚠ 下次再有人想加它，先回答「`false` 時的『驗證模式』指什麼」。
>
> **② 多年反向橋要不要提前 → 使用者 2026-09-19 採納，amendment 已生效並做到 Step 7.4。**
> L11-6 前置的結論：逐筆重讀那 4 筆 Abstention，**四筆全部該 abstain，80% 站得住**；
> 而比那個統計更有力的是 `revisit_when`——四筆有三筆逐字指名「估值層新增
> **mid-cycle／multi-year method**」或「虧損期 method」，全 ledger 11 檔理由同型。
> **研究層早就把需求規格寫好了。** Phase 表已改：Phase 4 拆成 4a／4b、Phase 7 提前。
>
> **③ refresh 按年度過濾 → 選 (a)，已落地。** `consensus` 類事件若年度明確不是 `0y` 就不觸發複查，
> 但**計數＋逐條進 notes**（不是靜默丟棄）。`None` 照舊觸發（fail open）；只對 `consensus` 生效。
> 實測 LITE 與 AXTI 的 thesis 由 `review_required` → `current`，**2/16 檔的假警報清掉而訊號沒消失**。
> 選 (a) 而不是 (b) 的理由是 L14-4：COHR 講 FY28 的缺口要靠多年橋補，不是靠一個對 15/16 檔都會亮的訊號。
>
> ### 編號狀態
>
> - **[577]／[627]／[628] 都已 resolve。** [627] 實測：`rank_bottlenecks` 該列 **#2 → #5**，
>   籃子不變（通過 1、首選 LITE）；COHR 首屏第三句已改寫（brief `ib_37dfb9b27153eba8`）。
>   [628]：`co:nvidia` 供給側 **3 條 → 4 條**，新那條 `attributes` 刻意留空（逐字不支持任何主張）。
> - **[629] 已執行**：COHR 的 thesis `active` → **`review_required`**（disproof[1]「出現第二家
>   取得 NVIDIA CPO 外部光源 design win 的供應商」已觸發；48h 動作的前半就是 [627]）。
>   ⚠ **thesis 內容與 variant 刻意未動**——那是重新評估的產出，不是轉狀態的副作用。
>   **重新評估本身還沒做**，是一個開著的研究缺口。
> - **[630] 已執行**：COHR 的 `multiple_horizon` = 2030-06-30（一手：10-Q 逐字
>   「support future production volumes through 2030」）＋ FY2030 七條錨點假設。
> - **[631] 已執行**（2026-09-19）：COHR 的 downside overlay，一手依據是 Q1 FY2027 指引區間**下緣**（variant 用的是同一個區間的上緣）。
> - **pq2 球在你手上 17 項**，全部是既有的（`python -m engine_b.todo list`）。
>
> ### ⚠ 已經做完、不要重做
>
> - **七個系統性缺陷全部交付**（1／2／4／5／6／7 於 2026-09-19，3 於同日稍早）。逐項的
>   before → after 數字寫在 ROADMAP 那七列裡，**要引用先去讀那一列**。
> - **Phase 4a 已結案**：三條接進 filter（市值／覆蓋家數／至少一條外部印證的邊）、
>   一條本來就在（催化劑）、**兩條量完確認今天不該接**（入圖日缺資料歷史長度、
>   瓶頸業務占比缺那個數字本身）。不要再去「補」那兩條——它們不是待辦。
> - **Phase 7 的 7.1–7.4 全部交付**（倍率參數化／`multiple_horizon`＋`span_years`／
>   `briefing multi-year` CLI／進 APP）。
> - **Phase 5 已結案標 ✅**（2026-09-19）：八項 completion gate 全過、驗收行四項全綠。
>   驗收行的讀法使用者定案：**「有賭注的檔都要有對稱的下檔」**，判準是**成對**不是固定名單
>   ——所以**未來新寫賭注的檔，一樣要同時寫下檔**，這條不隨名單腐壞。
> - **FX 觀測已自動化**（`StockBotv2-FxSync` 每日 06:55）。⚠ **不要再手抄匯率**；
>   新標的的第一筆仍然是人工（幣別對從既有觀測導出，不手寫清單）。
> - **`closure_terminal` 已認得第三種終局**（`awaiting_report`）。
>   ⚠ **不要用 `overview.downside` 量下檔覆蓋**——那一格恆為 null，要讀 `view.downside`。
> - **不要重新量「未到終局幾檔」而用 `row_from_artifact`**：它**結構上回不出第三種終局**
>   （`awaiting_report` 需要目標期末日，artifact 只存 `period` 標籤）。權威路徑是
>   `alpha.providers.closure.collect_backlog`：ready 52／settled 7／awaiting_report 4／未到終局 10。
> - **不要再查「daily 今天為什麼沒收乾淨」的前半段**：已經收斂到一個點——
>   `daily_run_finished_at` 沒更新 ⇒ 是**排程被中斷**不是收尾缺 release；
>   而 harvest 05:33 跑完 35 筆、state 05:47–05:52 寫出，**中斷在 finalize 之前**。
>   下一次只需確認「是不是同樣斷在 finalize 前」。
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
| **籃子 16 檔通過 0、首選無**（Phase 4a 接上兩條門檻後）；`market_cap_above_max` 10｜`analyst_count_above_max` 9｜`no_bet` 13｜`payoff_not_positive` 2｜催化劑四種形狀 `undated 6`／`missing_resolves 3`／`no_catalyst_recorded 4`／`after_value_date 1` | 讀 `library/private/app/state/basket.json` 的 `filter` 與 `top_pick_absent_reason` |
| **「N 倍要什麼為真」四級階梯**（Phase 7 Step 7.1）：AXTI **2x 可達**、3x 以上做不到；LITE／COHR 連 2x 都有 driver 做不到 | 讀 view 的 `expectation_gap.reverse_bridge.value['return_ladder']` |
| **`multiple_horizon` 填寫率 1 檔（COHR＝2030-06-30）**；`python -m briefing multi-year COHR` 印得出 FY2030 四級階梯，LITE 誠實回「還沒有人寫下來」 |
| **Phase 4a 已接三條**（市值、覆蓋家數、至少一條外部印證的邊）；籃子 **通過 0**；`no_externally_corroborated_edge` 7 檔。**另兩條量完確認不接** | 讀 `basket.json` 的 `filter.reasons`；`python scripts/alpha_screen_check.py` |
| **多年視角整條鏈已通**：`multi_year` state kind｜`--multi-year`｜`/api/v1/multi-year`｜APP「要幾倍」頁｜心跳段 4 一行。**16 檔算得出 1** | `python -m webapp status`（應列出 `multi_year｜fresh`）｜`python -m briefing multi-year COHR` | `python -c "import json,pathlib;print(sum(1 for p in pathlib.Path('library/private/alpha/judgments').glob('*.json') if json.loads(p.read_text(encoding='utf-8')).get('multiple_horizon')))"` |
| 賭注帳：籃子 `bet 3｜abstained 0｜opinion_in_base 3｜unanswered 10`；量的候選 `opinion_in_base 8｜unanswered 4` | 讀同一份 artifact 的 `bet_ledger`／`volume_bet_ledger`，或 `python crons/heartbeat.py` 第 4 段 |
| **目標倍數背離：全 ledger 生效 `target_pe` 49 筆｜`drift_exceeds 13`／`within_band 32`／`not_applicable 2`／`cannot_compare 2`**（門檻 5%） | `python scripts/target_pe_drift_check.py`（心跳段 2 也每天印一行） |
| **packet 的市值現在帶著單位走**：16/16 檔有 `quote_unit`（其中 6 檔非 USD），市值缺席 0 檔 | `python -m pytest tests/test_market_quote_unit.py -q`（4 條） |
| D11 門檻套用：input 16／accepted 5／filtered 11（缺值 0）；通過的 5 檔有 **4 檔儀器算不出 payoff** | `python scripts/alpha_screen_check.py` |
| 門檻值：市值 ≤ US$10B、覆蓋 ≤ 12（**兩條必須 AND**） | `python -c "import json;d=json.load(open('config/alpha_screen.json'));print(d['market_cap_max_usd'],d['analyst_count_max'])"` |
| `co:coherent supplies_to co:nvidia`：`sole_source` **`false`**（[627] 2026-09-19 寫入）；`co:nvidia` 供給側 **4 條**（含新增的 Sumitomo） | `python -m query.structure co:nvidia`——COHR 那列 `sole` 欄應為 ✗ |
| **refresh 不再對別的會計年度的共識變動強制複查**：LITE／AXTI 的 thesis 由 `review_required` → `current`，事件改印在 notes | `python -m briefing refresh LITE`（找「印出來但不觸發複查」那一行） |
| `co:lumentum supplies_to tech:uhp_laser`：`sole_source` **`false`**（[626] 已寫入） | `python -m query.structure tech:uhp_laser` |
| LITE：base +4.4%｜賭對了 +5.7%｜**判斷錯了 804.21（−13.6%）**；AXTI **判斷錯了 35.15（−49.8%）**；兩檔首屏都印得出下檔 | `python -m briefing alpha-card LITE`／`AXTI` |
| **有短評的檔 3 筆**（LITE／AXTI／COHR）；COHR 沒有 downside scenario，首屏刻意不寫下檔句 | `python -m alpha brief COHR --list` |
| `Catalyst.resolves` 填寫率：judgments/ **62 檔 104 條，填 0 條**（沒有改必填，刻意） | ROADMAP 該列的查證命令 |
| 可投資排序 **37 列**；⚠ **沒有任何 `.TW`／`.TWO`／`.ST`**——Phase 1 的驗收行卡在這裡（是答案不是缺漏） | `python -m query.bottleneck --top-n 60` |
| `audit invariants` FAIL 0／PASS 13／共 4,239 筆 | `python -m audit invariants` |
| 待辦池：**pq2 球在你手上 17**（[577][627][628][629][630][631] 全部結案） | `python -m engine_b.todo list` |
| **賭注收斂（V4，2026-09-19 新增）**：有賭注 3 檔｜朝我們 0｜反向 0｜共識沒動 2｜賭注寫下後還沒有共識抓取 1｜已觀測 1–3 天。⚠ **COHR 與 AXTI 的共識 13 天一個數都沒動**（9.41634／0.868） | `python scripts/outcome_if_settled_today.py`（找「賭注收斂」那段）｜讀 `outcome_aggregate.json` 的 `bet_convergence`｜心跳段 4 |
| ~~FX 觀測過期，4 檔算不出來~~ **✅ 已自動化（2026-09-19）**：`StockBotv2-FxSync` 每日 06:55；四檔 readiness `blocked → ready`，隱含報酬 6680.HK +35.8%／HEXA-B.ST −1.6%／XFAB.PA −1.2%／XPEV −7.5% | `python crons/heartbeat.py`（段 1 應印「全部在窗內」）｜`schtasks /Query /TN StockBotv2-FxSync /FO LIST /V` |
| 段 5 終局：**ready 56／settled 7／awaiting_report 4／未到終局 6**（6 檔全部是真的還沒研究）。⚠ **artifact 的 `closure_terminal` 現在與它逐位一致**（2026-09-19 以前差 4 檔） | `python -c "from alpha.providers.closure import collect_backlog;import collections;print(collections.Counter(r.terminal for r in collect_backlog()[0]))"` |
| 賭注／下檔的覆蓋：**payoff 3 檔｜downside 3 檔（AXTI／COHR／LITE，完全對稱）｜歸零旗標 73/73** | 讀 `library/private/app/analyst_view/*.json` 的 `overview.payoff`／**`view.downside`**（⚠ `overview.downside` 恆為 null）／`overview.wipeout` |
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

| **2026-09-19 收尾** | **[627][628] 執行（COHR sole_source 降為 false、Sumitomo 邊補進圖）｜[629] 鑄號（COHR 的 disproof 已觸發）｜三題全部落地：①不要 `sole_source_verification`（記進 schema §7）②L11-6 前置做完＋五欄 amendment 提出 ③refresh 按年度過濾已實作（LITE／AXTI 假警報清掉）｜Phase 2 第 2 天回填** | 本輪 |

| **2026-09-19 深夜** | **amendment 採納生效（Phase 4 拆 4a／4b、Phase 7 提前）｜Step 7.1 倍率參數化（AXTI 2x 可達是三檔唯一）｜Step 7.2 機制（`multiple_horizon`＋`span_years`；兩個量測在動手前改變了做法）｜Phase 4a 前兩條接進 filter（籃子誠實變空）｜[629] 執行、[630] 鑄號** | 本輪 |

| **2026-09-19 收尾** | **[630] 執行：COHR 倍率射程＝FY2030（一手逐字 through 2030）＋七條錨點假設（carried_forward，不是預測）｜第一條多年橋跑通：2 倍需要資料中心分部四年累積成長 4.65 倍｜順帶分開一個承載兩種語意的 rollover 斷言** | 本輪 |

| **2026-09-19 夜** | **Step 7.3（`briefing multi-year` CLI）｜Phase 4a 第三條（至少一條外部印證的邊，7 檔被擋）｜查出「入圖日」這個欄位從來不存在** | 本輪 |

| **2026-09-19 深夜 2** | **Phase 4a 第三條（外部印證的邊，7 檔被擋）｜另兩條量完確認不接（入圖日缺歷史長度、瓶頸占比缺那個數字）｜`loader` 加 `admitted_at`（`ON CREATE SET`，既有 691 節點永遠 null）｜Step 7.4 多年視角進 APP（artifact＋API＋頁面＋心跳）** | 本輪 |

| **2026-09-19 傍晚** | **Phase 5 剩的兩項都交付＋八項 completion gate 逐項核對**：**V4 賭注收斂**——量測前先發現起算日錯了兩層（63 個 judgment 檔只有 14 個有 `_produced_at`；賭注那條線用判斷日當起點，而三檔沒有一檔同日，LITE 的 +1.26% 來自賭注寫下前四天）；`gap_at_start` 攤開分母（5802.T −7175.7）；四個消費端接上。**readiness 語意**——跑查證命令才知道它已經解了（由 research 層 settled **0 → 2**，且那 2 檔到終局的唯一原因就是它）。**Phase 5 不標 ✅**：驗收行卡在 COHR 沒有 downside，鑄 [631]。順帶：FX 觀測過期偵測進心跳（🔴 自動化要決定）、`closure_terminal` 回不出第三種終局（🟡 兩方案）、daily 中斷點收窄到 finalize 之前。全量 **2,771 passed／0 failed**；`audit invariants` FAIL 0／4,242 筆 | 本輪 |

| **2026-09-19 深夜 3** | **四個待決一次清掉（使用者「631 go 開發項都照你建議做」）**：**[631]** COHR 下檔——一手依據是 Q1 FY2027 指引區間**下緣**，而 variant 用的是**同一個區間的上緣**；三個 scenario 正好是那個區間的三個點（下緣 −0.00058／中點 +0.0221→base 0.025／上緣 +0.0437→variant 0.045）；首屏那把尺四個數到齊（317.36／223.60／243.97／**197.54**）。**FX 自動化**——`StockBotv2-FxSync` 每日 06:55，四檔 `blocked → ready`，未到終局 **10 → 6**。**第三種終局進 APP**——等價性 73/73 量過後把 `collect_backlog` 那份查詢移除，判準只留一份。⚠ 三個交付各踩到一次自己的坑並當場修：L15（引用不在 context 內 → 整筆靜默拒用）、L17-1（同一函式兩個呼叫端兩種形狀）、測試名稱撞到既有 fixture。全量 **2,780 passed／0 failed**；`audit invariants` FAIL 0／4,244 筆 | 本輪 |

| **2026-09-19 收尾 2** | **Phase 5 結案標 ✅**：驗收行的讀法使用者定案取「有賭注的檔都要有對稱的下檔」（原話「走後者吧」），判準是**成對**不是固定名單——實測 payoff 與 downside 都是 AXTI／COHR／LITE，兩組**完全相同**。⚠ 另一個讀法（COHR＋另外三檔＝4 檔，缺 SIVE.ST）已明確排除：SIVE.ST 連賭注都還沒寫，要它有下檔等於要求「沒下注也要說認錯值多少」 | 本輪 |

**不要重做 Step 0，也不要重做 Phase 1／2／3／6 已交付的任何一項，也不要重做 V1／V2／V3。**

### Phase 1 的核心發現（仍然成立，不要重查）

**補完格之後可投資排序仍然沒有任何台股，而那是答案不是資料缺漏。** 四家台系磊晶廠的
`substitutability` 全部低於門檻 4——聯亞 3、華星光 2、全新 2、英特磊 2。判準不是自由心證：
**各家在自家年報裡逐字互相具名指認對方是同層競爭者**。**不得為了讓籃子非空而放寬門檻 4。**
