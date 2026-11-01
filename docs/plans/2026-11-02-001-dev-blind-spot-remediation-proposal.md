---
title: 盲點審查的修法（層 1–4）——決策的最後一公尺、drain 觸發、量測載體、把關
type: dev
status: active
date: 2026-11-02
derived_from: docs/reports/2026-11-01-system-blind-spot-audit.md（8 視角＋兩反方；編號 1–24 見同日對話整理，本檔照那份編號）
---

# 盲點審查修法 PLAN_PROPOSAL（2026-11-02）

> 狀態：**方向已核准、AGENTS 逐字改法待使用者看一次 diff**。雲端 session 額度將盡，本檔是交接；下一個 session（本機、強模型）從 §4 接續。
> 本檔只寫、不實作。現況數字是 2026-11-01 的快照，動手前照各項查證命令重跑。

## 0. 使用者定案（逐字，2026-11-01～11-02 雲端 session）

- 「可不可以稍微先整理一下 從簡單到完整的就是這些缺陷 跟該怎麼解決 我先弄懂我們再來討論要怎麼改」→ 整理成 24 條（層 1 衛生 1–6、層 2 改 skill／登記 7–15、層 3 要你決定 16–21、層 4 根本 22–24）。
- 「17~21應該都可以照你建議」；19：「我基本上是台股+IB，IB有就有」；20：「我很相信你的建議，你該怎麼替我把關?」；21：「我會說都做都是出於我看完你整段敘述，我覺得你講得我都同意」。
- 「對 我同意18」——**等於 22 選 (a)：可開恆為 0 是門設計太嚴，不是方向錯**（主 session 當面確認的問句：「你同意 18，其實等於對 22 選了 (a)……是這樣嗎？」→「對」）。
- 「隨機抽查 開subagent這件事 其實你就當成我是開綠燈吧」——**常規 opt-in：入圖包隨機抽樣的唯讀 reviewer**（範圍見 §2 第 20 條；不擴及其他委派）。
- 「剩下都ok」——層 1、層 2 照建議；24 照主 session 提的候選停止條件；23 仍待使用者的數字（「ok」無法替代數字）。

## 1. 層 1（衛生；十行內、不動 contract；執行者直接做，L17 當下修）

| # | 做什麼 | 驗收（數哪一層） | 查證 |
|---|---|---|---|
| 1 | Q3W 裁決回填：五檔（002428.SZ、002270.SZ、300395.SZ、AXTI、LYC.AX）從研究日誌十一／十三與各版 `ib_*` append `cases.md` Q3W「裁決」行；research-drain SKILL 段 5 ⓪ 加一句「Q3W 名單內敘事換版或複查的同一個動作 append 裁決行」；心跳狀態塊加「Q3W 裁決：到點 N／已寫 M」 | cases.md 裁決行 0 → 5（追蹤表）；**11-20 前完成**（之後被 30 天價格污染） | `grep -n "### 裁決" -A 8 docs/reports/phase7/cases.md` |
| 2 | `engine_b/todo_ledger.py::next_prompt`：推 `/research-drain` 的條件改成「進展格」（`todo.disproof_touched`、`todo.confirm_touched`、重開達成、只差已定價／可開出現、使用者點名）任一非零，或任一待辦格最老天數 ≥ 7；否則印「只剩維護，照 plan Q8 每週 2–3 次清」。drain Step 6 收尾加印「本段候選狀態移動 N／鑄 ra_admission M」。判準句：**會叫人動手的數字，要問它歸零時有沒有任何一檔離決定更近；沒有的只當健康度、只在太老時叫人** | 兩週後 research-log drain 段數／週 ≤ 3（研究日誌）；收尾行出現 | `python -m engine_b.todo_ledger`（或心跳 ⑤）看提示行 |
| 3 | `todo_ledger.py:143` `candidate:priced_wait` 中 `open_gaps == []` 的列改進 ③ 待你決定（其餘等回落照 `wait`） | ③ 出現 3081.TWO／4979.TWO／AXTI（registry；本機 materialize 後） | 短版 ③ |
| 4 | `crons/harvest_leads.py:828` 丟掉的 `select_tickers` INV-3 報告：`filtered_not_watched` 印進心跳段 1 | 心跳段 1 出現 MOPS 名冊外筆數 | 心跳段 1 |
| 5 | ARCHITECTURE §8.2 純讀 config 的四條（alpha `observed_only`、`single_position_nav_cap`、beta_policy 無 signal、standing_authorization 封閉性）寫成 `audit invariants` 一條 | invariants 多一條 PASS | `python -m audit invariants` |
| 6 | `event_watch.judge()` 把 daily 預篩的 `semantic_flag.verdict` 寫進 judgment；counters 印「預篩 vs 互動不一致 N」 | counters 多一行 | `python -m engine_b.event_watch counters` |
| 20a | 入圖包兩個 gate 路徑上的第 1 次缺陷（在 gate 路徑上，所以不等第 2 次）：#58「庫內已有幾份」改由 prepare 機械 grep 名冊名稱與別名、印進審查文字；#57 公開報告文字出現私有路徑或券商報告標記即拒收 | 下一個入圖包的「庫內已有幾份」是機器數的（入圖包） | failure-log #57、#58 |

## 2. 層 2（改 skill 一句或在 registration 檔尾登記；不動 AGENTS）

| # | 做什麼 | 落點 |
|---|---|---|
| 7 | 已達 2 倍（自入圖或第一次接觸起）的標的，自家三年百分位在稽核區只印、不得作為「等回落」理由；已定價那格改寫「價格已假設了什麼、翻倍還需要那之外的什麼」 | research-drain SKILL 段 5 |
| 8 | **H1b**：①接觸前 30 天對該鏈組超額是否 > 預登記值（例 +15%）②接觸日早於或晚於窗內最大單日重評價日；兩量不比大小、不隨量測日變；H1 原線照留只印 | registration.md 檔尾（先於任何計算） |
| 9 | `lane_summary` 加 `by_anchor_state`（`paper_lane_plan` 第 649 行 `anchor_state` 已算出、沒進分組鍵），帶小樣本旗 | `scripts/outcome_if_settled_today.py` |
| 10 | 兩個計數器：①三條 lane 自錨點回撤 ≥30% 的檔數 vs 其中反證曾被觸及的檔數；②持有／可開敘事裡「逾期型反證（X 未在 D 前發生）0 條」的份數；段 5 要求持有／可開敘事至少一條逾期型反證。**不改出場規則** | 追蹤表＋SKILL 段 5 |
| 11 | AXTI 11-13 10-Q 複查的 revised／retired rationale 逐條寫「方向在 v4 下支持或推翻」「效果落在 12／24 個月窗內或 2028 之後」。不加欄位、不改 L7 | thesis 複查（研究） |
| 12 | 讀圖 `neither` 也要求「換得掉」引用並標來源型別（買方事實／買方政策／第三方／媒體）——收緊不是放寬 L8；追蹤表加子群「騎在 neither 層上的邊緣公司」 | `alpha/structure_reading/contracts.py:91、93`（Z1–Z2，動讀圖契約：先看一次 diff） |
| 13 | **H15**：名冊內「<10B 且 ≤12 家」對「<10B 且 13–20 家」12／24 個月達 2 倍率與等權超額；門檻值、遲滯、撤回規則都不動 | registration.md 檔尾 |
| 14 | 先量：11-10 月營收後、11-14 季報前，Q3W 第 14–25 列幾檔被重答——0 就不加營收叫醒 | cases.md Q3W 一行 |
| 15 | `config/source_routes.json` 補海關提單一格（rung 2、tier_cap 2、CAPTCHA 即停），只對「缺 X 恰是具名美國客戶」的檔查一次（華城 1519.TW、KSH）；Form 4 code P 從 auto no_go 拿出 | config＋分類規則（後者動無人值守 surface：sandbox impact review） |
| — | 另：完整性批評三條量測——敘事事實抽樣（每段 drain 收尾抽 1 份逐句核一手、cases.md append）、§5.2 觀察名單等權當第二基準、每月 5 檔影子重寫一致率 | registration＋追蹤表 |

## 3. 層 3–4（使用者已核准方向；動 AGENTS 或 A5 的要先看一次逐字 diff）

| # | 核准的方向 | 要動哪裡 | 狀態 |
|---|---|---|---|
| **18＋16** | 可開分起始與加碼兩道門：**可開（起始）**＝會死嗎非紅＋押的層讀過且非 `neither`＋反證寫下且有到期＋「已定價」寫成一句脈絡；讀到邊與深挖清單（#119）搬去當加碼條件 `confirm[]`。等回落併回可開當脈絡（=P2，plan 2026-11-01-002，**不等 12-22、不等 H14(b)**） | AGENTS「讀到邊才算讀懂……答不出就寫缺 X」「候選狀態是封閉字彙：可開／缺 X／已定價等回落／不要／已持有」兩句；`open_preconditions`；research-drain 段 5；plan 2026-11-01-002 P2 改 ✅ 方向 | **待看 AGENTS diff** |
| **17** | 「看了沒買」的 A5 append-only 載體：與成交紀錄同處、同收據格式，kind＝看了沒買；欄位：日期、代號、選擇（進／不要／等到條件）、一句理由、當時敘事版本 | `library/trades/`、`scripts/record_trade.py` 或旁支一支（Z2；A5 authority；AGENTS「資本與風控」補一句） | **待看設計與 AGENTS diff** |
| **19** | 買得到嗎：.TW／.TWO 走台灣券商；其餘「IB 能下單就算」；每個市場一條規則、個別代號可例外；買不到的只當層證據與主題組成員，不寫個股敘事、不進 paper lane | `config/company_identity.json` 的 `execution_venue`（今天美股 100／157 為 None）；段 5 一句 | **待使用者在 IB 各搜一檔確認 6 個市場**：KS、NS、SS（688）、SZ（300／002）、VI、V；主 session 印象中美、日、港、瑞典、德、加、英、法、澳、瑞士、芬蘭都可 |
| **20** | 把關四層：①程式擋（apply 入口四道、L8、逐字＋20a 兩條）②每包第一行只寫「要你判斷的一句」，無判斷成分的標「純機械」③**每 10 包隨機抽 1 包給乾淨 context 唯讀 reviewer 從頭核（使用者 11-02 常規 opt-in）**④計數器「本月照建議 go N／偏離 M／事後抓到包內缺陷 K」（`todo_pool.json` 既有 `recommendation.verb` 與 `resolution`，零 schema 變更）。K>0 且 M=0 → 抽樣加密。四個人工 gate 不放寬 | AGENTS「subagent 委派預設關閉、每次明確 opt-in」後補一句常規 opt-in 的範圍；skills（research-drain／daily-brief 的入圖包呈現） | **待看 AGENTS diff** |
| **21** | 開發提案分兩組：「建議現在做」（第 2 次以上、擋住研究、在 gate 路徑上、十行內）／「建議先記下」（第 1 次、只是便利）；每項一句「不做會怎樣」，寫不出就不提；批次指令只涵蓋第一組 | `skills/development-flow/SKILL.md`、`skills/daily-brief/SKILL.md` 呈現契約 | 可直接做（skill 文字） |
| **22** | (a) 設計：§10 條 2 改寫成「只差已定價的名單恆為 0 或恆非 0」，並補 §10 自己的核查（每個檢查點）與觸發後動作（使用者在「設計／方向錯」兩個封閉選項裡選一個寫進決定紀錄） | `docs/brainstorms/2026-09-22-graph-first-direction-decision.md` §10（append 一段定案，不改原文） | 可直接做 |
| **24** | 系統自己的停止條件：決策時段上線後連續 8 週「可開＋只差已定價」名單非空而使用者決定（含不要）仍 0 筆，或 23 算出一檔 5 倍最大貢獻 < NAV 2% → 縮成「beta 紀律＋等待 registry＋每月一頁」 | 同上 §10 append；plan 7.5 檢查點加一項 | 可直接做 |
| **23** | alpha 格意圖規模、一檔起始筆（N）、可忍單檔虧損（L）——住使用者自己的紀律或 Sheet 備註，**不進 config** | — | **待使用者數字** |
| 決策時段 | 每週 15 分鐘、與 drain 分開；只看「可開＋只差已定價」，每檔三選一（最小部位進走 `record_trade.py --why`／不要一句理由／設可機械比對的重開條件）；以 17 記錄 | 使用者習慣＋17 的載體 | 隨 17 上線 |

## 4. 下一個 session 從這裡接（順序）

1. **11-20 前必做**：§1 第 1 條 Q3W 五檔裁決回填（會被價格污染）。
2. §1 其餘（2–6、20a）＋第 21、22、24 條（不動 AGENTS）——各自跑相關測試，一個 commit 一件。
3. §2 的 registration 檔尾登記（8、13、量測三條）——**先於任何計算** commit。
4. 把 18＋16、17、20 的 AGENTS 逐字 diff 一次給使用者看（Z2；AGENTS 停止條件④），go 之後實作；17 動 A5，同 change 做測試＋變異。
5. 19 等使用者回 6 個市場；23 等使用者數字。
6. 本機 materialize 一次，驗 §1 第 3 條與 P0 真資料。

## 5. 刻意不做（本輪）

- 12-22 前不開新 feed（EDGAR 全文檢索等）、新 lane（除第 9 條加分組鍵）、第二模型逐條裁決（除第 20 條抽樣）、營收叫醒（等第 14 條的量）——審查的完整性批評指出「加機制 vs 停加機制」是存活發現間最大的矛盾，§10 原文已選了邊。
- 不放寬四個人工 gate；不放寬 L8；不給尺寸、不排序、不首選、不算目標價。
- 不加 X 帳號、不砍帳號（H6 沒有對「對其他管道早不早」的尺；Q4 R3 加一欄「X 點名過、系統 park、後來前四分之一」）。
