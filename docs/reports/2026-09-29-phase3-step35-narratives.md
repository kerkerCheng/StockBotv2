# Phase 3 Step 3.5 收據：v2 敘事四份＋兩類 pq2（2026-09-29）

> 研究步驟（強模型、互動 session）。寫 ledger 與 `event_watches.json` 全程持互動 writer lock（13:23–13:50 台北，daily 在 05:30）。
> 本檔是收據，不是 current-state truth——現況以下列查證命令為準（AGENTS「現況數字會過期」）。

查證命令：`python -m alpha brief <T> --list`、`python -m engine_b.event_watch list`、`python -m engine_b.event_watch counters`、
`python -m engine_b.todo list`、`python -m webapp status`、`python -m audit invariants`。

## 1. 四份敘事（現行 id）

每份都有兩行：第一行是本 Step 的內容；第二行是**同日換版、只更正措辭**（見 §5 第 2 點），內容、候選狀態、反證不變。

| 檔 | 現行 brief_id | 同日第一版 | 取代的 v1 | 騎的格（單位／讀圖判讀） | 候選狀態 | 在等的 watch | answers（已定價／數字裡） | 邊緣 |
|---|---|---|---|---|---|---|---|---|
| AXTI | `ib_3100d4c6f394b679` | `ib_b6b3b1b8ebaaa438` | `ib_d6a413c3dbc796c5` | InP 基板（層，`sr_bac985bacbea64b7` volume） | **等回落**（priced_wait） | `ew_0148`（date，until 2026-11-13，expires 2027-01-15） | yes／yes | 邊緣（市值約 48 億美元、分析師 5 位） |
| COHR | `ib_1ddf59d7c3cf4fe4` | `ib_9a581a19a43d2e41` | `ib_37dfb9b27153eba8` | CW DFB 雷射（層，`sr_d49b81b6465e1181` volume） | **不要**（pass：非邊緣） | — | yes／yes | 非邊緣（約 553 億美元、22 位） |
| LITE | `ib_bc97e6ccde70f264` | `ib_78d7b285e8b517ea` | `ib_b36e5f298bceef47` | CW DFB 雷射（層，`sr_d49b81b6465e1181` volume） | **不要**（pass：非邊緣） | — | yes／yes | 非邊緣（約 826 億美元、25 位） |
| SIVE.ST | `ib_cb5642b674f08e14` | `ib_84e5efaf6360f042` | （第一份） | CW DFB 雷射（層）＋ SuperNova 雷射陣列（插槽，`sr_268d2fd79db629ff` undecided）＋ O-Net ELS 八通道雷射陣列（插槽，`sr_35ca0ce58617d5f6` undecided） | **缺 X**（missing） | `ew_0149`（date，until 2026-11-26，expires 2027-01-31） | 無法量／無法量 | 邊緣（約 10 億美元、1 位） |

**四份的候選狀態沒有預期值，也沒有為了候選板非空放寬任何前提**（硬約束 7）：可開 0 份。
- AXTI 不宣告可開，理由是價格：自家三年 P/S 第 88 百分位（今天的倍數是三年中位數的二十倍以上，寫入日）。
- SIVE.ST 不宣告可開，理由是兩個插槽讀圖都 undecided，而且兩題都量不到。

### 供給側證據（騎的格＝本公司在那份讀圖快照的供給側；寫入端逐條驗過）

- **AXTI → InP 基板層**：供給側 3／3／3（AXT、住友電工、JX）。客戶端逐字說多源：
  - Coherent：「we have multiple six-inch indium phosphide substrate suppliers」。
  - Lumentum：「found additional substrate help from AXT」。
  - 反向路徑 0 條。
- **COHR、LITE → CW DFB 雷射層**：供給側六家，六條供貨邊都沒有客戶端或第三方印證。
  - NVIDIA 技術部落格（2026-09-29 回原文核對）在「ELS lasers and subassemblies」一欄把 Lumentum、Sumitomo、Coherent 並列。
  - COHR 10-Q 逐字寫那份協議是「non-exclusive」。
- **SIVE.ST → 同一層＋兩個插槽**：三份讀圖的供給側都含 `co:sivers_semiconductors`。插槽的確認端全在供應商側與聯合公告方（讀圖原文）。

### 首屏前後對照（對 3.0 基準 §10）

| 檔 | 3.0（v1） | 本 Step 之後（v2） |
|---|---|---|
| AXTI | brief 面板 partial：`market_view`、`our_bet`、`if_right_if_wrong` 缺 `{assumption:…}`、`{bet_target}`、`{payoff}`、`{downside_*}`（估值鏈退役後恆「（尚無）」） | available；七句全填：已定價「自家三年 P/S 的第 88 百分位」、數字裡「年增 +164.8%（2026-06-30）」、檢核點 2026-10-30 |
| COHR | partial：`our_bet` 兩個 assumption 全缺、`if_right_if_wrong` 三個目標價缺、`when` 缺 `{value_date}` | available |
| LITE | partial：同 COHR，另缺 `{downside_*}` | available |
| SIVE.ST | 沒有短評：readiness **blocked**（`brief：missing`） | partial（已定價那句的 `{own_history_pctile}`／`{own_history_basis}` 印「（尚無）」——瑞典申報人沒有機械的財報歷史，這是誠實的缺席）；readiness **ready** |

- readiness 從 ready 3／blocked 70 變成 ready 4／blocked 69（`python -m webapp status` 實數）。
- 首屏的標題列與 status light 沒動。AXTI／COHR／LITE 的 light 仍是「有假設改過，判斷還沒重看」，來源是退役估值鏈的 `axis:expectation_gap`（plan §14 #6，與本 Step 無關）。

## 2. 反證：搬進來的與出處

| 檔 | 新登 | 連結既有（來源鍵） | 沒搬的與為什麼 |
|---|---|---|---|
| AXTI | 1：`ew_0151`（`brief:ib_3100d4c6f394b679#5`，self）：AXT 揭露任一家產能客戶退出或沒照約付款（Coherent 解約／要回預付、Lumentum 第一筆押金沒如約支付或協議終止、Casela 未在 2026-12-31 前付清另一半） | 4：thesis `axt_inp_v1_lane_memo.md#5`（Q3 營收低於 Q2）；讀圖 `sr_bac985bacbea64b7#1`（第四家）、`#4`（擴產提前）、`#5`（出口管制解除） | thesis #1、#2 是 v1 估值賭注的「結構 vs 議價權」之爭，#3 由讀圖 #4 涵蓋，#4 由讀圖 #5 涵蓋，#6 是資金面細節；讀圖 #2、#3、#6、#7 是「護城河 vs 量」的分類條件，響了重讀的是讀圖——這份敘事不直接依賴它們 |
| COHR | 0 | 0 | 「不要」的理由只有非邊緣一條，由候選板機械重算；本層的反證由讀圖自己在盯（`ew_0142`–`0147`） |
| LITE | 0 | 0 | 同 COHR |
| SIVE.ST | 0 | 5：thesis `sivers_v4_lane_memo.md#1`（ELS 時程）、`#3`（Ayar 節點）、`#4`（資金螺旋）、`#5`（信用重開）；讀圖 `sr_d49b81b6465e1181#6`（買家內製 CW 雷射） | thesis #2（Jabil 通道）不是這份敘事的依據；插槽讀圖的確認／反證條件（`ew_0135`–`0141`）由讀圖自己在盯，本敘事騎插槽但沒有新的依賴 |

- AXTI 同日換版時，舊版的 `ew_0150` 被收掉（consumed，superseded），同一條件以新 id 重登為 `ew_0151`，淨增 0。
- 登記全由寫入端在 append 前先預演、append 後正式跑（R2-a C1）。

### L11-6 ④（真實 registry，本 Step 前後）

| 計數 | 前 | 後 | 增量 | 應為 |
|---|---|---|---|---|
| `semantic_active` | 36 | 37 | +1 | 四份的新登條數 1（連結 9 條不增加）✅ |
| `wake_brief` | 0 | 2 | +2 | 缺 X＋等回落份數 2（AXTI、SIVE.ST）✅ |
| `active` | 123 | 126 | +3 | 1 語意＋2 date ✅ |

- 同日換版之後三個計數不變（37／2／126）。
- 心跳「反證：在盯 37｜未盯 0」。
- `python -m audit invariants` 13 項全 PASS，`narrative_rewrite=0`。

## 3. 兩類 pq2（已掛號，**等你 go**；go 之後由收到 go 的 session 寫入）

### [656] 主題等權組第一版成分（`manual`；`complete-theme-cohort 656`，bare go 拒收）

- **題材**：`config/sector_anchors.json` 的「AI 光互連／CPO」。
- **15 檔等權**：AXTI、IQE.L、4971.TWO（IntelliEPI）、2455.TW（全新）、3081.TWO（聯亞）、4979.TWO（光環）、SIVE.ST、COHR、LITE、300308.SZ（中際旭創）、AAOI、FN、POET、ENA.V、3363.TWO（上詮）。每一檔的入選理由都指得回圖上的邊，寫在凍結的 spec 裡。
- **大型股入組（明寫理由）**：籃子同時是 G9 的量測基準——「主題整體漲三倍時一檔兩倍是輸」。拿掉 COHR／LITE／中際旭創／Fabrinet，它就變成「邊緣小型股籃子」，量到的是規模效應，不是題材；等權避免它們主導。
- **排除**：
  - 住友電工、JX：綜合集團，光通訊基板不是主業（判斷，未量化）。
  - 需求端與 AI capex 本身：NVIDIA、Broadcom、Arista、Marvell、雲端業者。
  - Corning：多元業務。
  - MACOM、Tower、穩懋、Soitec、奇景、光寶、Jabil：光互連只是業務的一部分。
  - 其他題材。
- **digest**：`977a8f8fb7ca1347…`（寫入時比對，spec 鑄號後被改就拒收）。
- **go 只定「已定價②③的對照組是誰」**，不含任何排序、尺寸或買賣。
- 若結案時仍未 go：已定價②③全體缺席，照實寫（plan §14 #3）。

### [657]–[661] going concern 判讀（`engine_c_observation`；`complete-observation <n>`，bare go 拒收）

| 編號 | 檔 | 判讀 | 查核人／報告日／頁 | 逐字（節錄） | 請你核准時一起看的 |
|---|---|---|---|---|---|
| [659] | AXTI | no_substantial_doubt | BPM LLP／2026-03-17／10-K p.75 | 「In our opinion, the consolidated financial statements present fairly, in all material respects…」 | 依據是**說明段不存在**（10-K 全文沒有 going concern／substantial doubt），不是一句肯定句；唯一 CAM 是存貨跌價 |
| [657] | COHR | no_substantial_doubt | EY／2026-08-14／10-K FY2026 pp.51–52 | 同上形式（FY2026） | 同 AXTI；10-K 是本 session 唯讀抓取（accession 0000820318-26-000020），未入 library |
| [658] | LITE | no_substantial_doubt | Deloitte／2026-08-17／10-K p.61 | 同上形式 | going concern 只出現在風險因子一句（可轉債提前償還），那是管理層的風險揭露，不是查核結論 |
| [661] | SIVE.ST | **substantial_doubt** | Deloitte AB／2026-05-13／Årsredovisning 2025 s.76 | 「Väsentlig osäkerhetsfaktor avseende antagandet om fortsatt drift … Dessa förhållanden tyder på att det finns en väsentlig osäkerhetsfaktor som kan leda till betydande tvivel om bolagets förmåga att fortsätta verksamheten. Vi har inte modifierat vårt uttalande på grund av detta.」 | 查核報告用 ISA 570 的「betydande tvivel」（significant doubt），對到本欄字彙的 substantial_doubt——**這個對應本身是判讀**；意見未修正（非保留） |
| [660] | IQE.L | no_substantial_doubt | KPMG／2026-05-28／AR2025 印刷頁 90–91（PDF 第 47 頁）第 4 節 | 「we have not identified, and concur with the directors’ assessment that there is not, a material uncertainty…」 | ⚠ 同節第三點的模板句寫「and their identification therein of a material uncertainty…」，與第二點及董事結論字面矛盾；本判讀依查核人員自己的結論（第二點）＋第 2 節「agree with the directors that the assessment of the going concern is not a significant judgement」。wipeout.py 原本點名 IQE 是「會亮」的第一個案例——依原文它會亮**綠**，不是紅 |

- 五筆的來源欄都寫了 accession／URL 與本機檔位置。
- 核准前可以用 `python -m engine_b.todo list` 看完整 payload。

## 4. 工具毛病＝回頭修（比照 Phase 2 偏差 #7–#9）

1. **已定價①拿過期的 TTM 當「今天」判口徑**（plan 偏差 13，修 3.3）：
   - 現象：COHR 的營業利益 tag 停在 2024-06；LITE 的總負債 tag 停在 2023-04。舊版因此判成 EV/S。
   - 修法：新增 `FUNDAMENTAL_MAX_AGE_DAYS = 200`。口徑判定要求營業利益 TTM 與營收 TTM 同一季收尾、而且不過期；逐日序列裡過期的那一天不算樣本。
   - 修後兩檔落 P/S，理由寫出是哪一側過期。這兩檔的 priced_in 句也照實寫了口徑為什麼是 P/S。
2. **`{in_numbers_latest}` 的說明寫「序列最新一點」，實際填的是年增率**（plan 偏差 16，修 3.4）：
   - 我照說明寫成「最新一季營收 {in_numbers_latest}」，填出來變成「營收 +164.8%」。
   - 字彙說明與 `brief_frame` 題目已改成「年增 {in_numbers_latest}」。三份的措辭已同日換版更正；SIVE.ST 順便把讀起來不通的缺席句改順。
   - 另記一個沒修的缺口：分部占比序列的最新一點沒有年增，這個 placeholder 會印「（尚無）」（plan §14 #24）。
3. **v1 自己引用的錯**（L11-2：別對自己引用鬆）：
   - v1 寫 Lumentum「第一筆押金 43,500,000 美元已付」；一手（AXT 10-Q 2026-08-13）只寫「an initial deposit of $43,500,000, due within thirty (30) business days」。
   - Casela 的「先付一半」同樣是條款，Coherent 的預付也是約定。
   - v2 全改成「約定」，並把「客戶沒照約付款」寫成新登的反證（可觀測：下一份 10-Q 的客戶預付／押金餘額）。

4. **3.4 的測試一直在讀真實 ledger**（plan 偏差 17）：寫進第一筆 v2 後，`disproof_counts` 的一條測試期望 3 得 4——沒給 `briefs` 就讀真實短評 ledger。7 處測試呼叫改為注入空的敘事。同一輪發現 3.4 收尾 commit（`6dd0fd4`，已 push）讓 `alpha/cli.py` 直接 import `engine_b`（違反分層），改由 provider 取「今天」。全套 2717 passed。

## 5. 刻意沒做

- 沒有替任何一檔宣告可開，沒有為了讓候選板非空放寬任何前提。
- 沒有動四個人工 gate：兩類 pq2 只掛號，不寫入。
- 沒有寫 thesis。SIVE.ST 的 thesis 核查（hook 提醒 memo 超過 30 天週期）不在本 Step，由 thesis-monitor 處理。
- COHR 10-K、Sivers 年報 PDF 只抓到 scratchpad 讀，沒有入 library（入庫是另一個流程）。
