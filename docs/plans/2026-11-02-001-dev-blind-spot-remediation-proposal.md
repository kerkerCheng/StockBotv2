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
> **2026-11-03 本機 session**：§4 第 1–3、6 步完成；第 4 步（§6 AGENTS diff）與 §7 兩個契約改法等使用者看過回 go；第 5 步 11-03 使用者已答（19 做完、23 記進決定紀錄 §10.2）。逐項見 §8。

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
| **19** | 買得到嗎：.TW／.TWO 走台灣券商；其餘「IB 能下單就算」；每個市場一條規則、個別代號可例外；買不到的只當層證據與主題組成員，不寫個股敘事、不進 paper lane | `config/company_identity.json` 的 `execution_venue`（今天美股 100／157 為 None）；段 5 一句 | ~~待使用者在 IB 各搜一檔確認 6 個市場~~ **✅ 2026-11-03**（使用者「IB這些都可以下」）：`config/execution_access.json` 19 個市場各一格＋個別代號例外；IB 的 A 股走滬深港通，HKEX 名單對名冊 26 檔 A 股 2 檔不在（688836.SS、688818.SS，都已非倍率）；paper lane 不收買不到的（宇樹原是最大單檔貢獻者）。`1d7c7e34`（登記）、`de28f2be`。閉環母體與寫入端暫不擋（0 筆會變；只擋寫入會卡死循環） |
| **20** | 把關四層：①程式擋（apply 入口四道、L8、逐字＋20a 兩條）②每包第一行只寫「要你判斷的一句」，無判斷成分的標「純機械」③**每 10 包隨機抽 1 包給乾淨 context 唯讀 reviewer 從頭核（使用者 11-02 常規 opt-in）**④計數器「本月照建議 go N／偏離 M／事後抓到包內缺陷 K」（`todo_pool.json` 既有 `recommendation.verb` 與 `resolution`，零 schema 變更）。K>0 且 M=0 → 抽樣加密。四個人工 gate 不放寬 | AGENTS「subagent 委派預設關閉、每次明確 opt-in」後補一句常規 opt-in 的範圍；skills（research-drain／daily-brief 的入圖包呈現） | **待看 AGENTS diff** |
| **21** | 開發提案分兩組：「建議現在做」（第 2 次以上、擋住研究、在 gate 路徑上、十行內）／「建議先記下」（第 1 次、只是便利）；每項一句「不做會怎樣」，寫不出就不提；批次指令只涵蓋第一組 | `skills/development-flow/SKILL.md`、`skills/daily-brief/SKILL.md` 呈現契約 | 可直接做（skill 文字） |
| **22** | (a) 設計：§10 條 2 改寫成「只差已定價的名單恆為 0 或恆非 0」，並補 §10 自己的核查（每個檢查點）與觸發後動作（使用者在「設計／方向錯」兩個封閉選項裡選一個寫進決定紀錄） | `docs/brainstorms/2026-09-22-graph-first-direction-decision.md` §10（append 一段定案，不改原文） | 可直接做 |
| **24** | 系統自己的停止條件：決策時段上線後連續 8 週「可開＋只差已定價」名單非空而使用者決定（含不要）仍 0 筆，或 23 算出一檔 5 倍最大貢獻 < NAV 2% → 縮成「beta 紀律＋等待 registry＋每月一頁」 | 同上 §10 append；plan 7.5 檢查點加一項 | 可直接做 |
| **23** | alpha 格意圖規模、一檔起始筆（N）、可忍單檔虧損（L）——住使用者自己的紀律或 Sheet 備註，**不進 config** | — | **✅ 2026-11-03**「Alpha NAV 10%吧 可以接受歸零（最大底線了）」→ 決定紀錄 §10.2：10% 只是停止條件的輸入、不是目標；第二子句以此規模不成立（起始筆 ≥ 0.5% NAV 一檔 5 倍就 ≥ 2%），檢查點改用實際起始筆重算；N 沒給，用成交紀錄 |
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

## 6. AGENTS 逐字 diff 草稿（2026-11-03 起草；§4 第 4 步——使用者看過、回 go 才改 AGENTS 與實作）

> 三處一起看。`<核准日>` 套用時換成使用者回 go 的日期。按本檔准入判準，句子裡不寫函數、表、比例；比例與實作落點住 ARCHITECTURE。
> 跟現行第 169 行「反證用來決定何時認錯，不是進場的前置條件」的關係：起始門要的是反證**寫下**（知道何時認錯），不是要它先被驗過，兩句不衝突。

**18＋16（第 160–161、164–165 行）**

```diff
   **讀到邊才算讀懂（2026-10-06）：** 一份讀圖或敘事若答不出「客戶為什麼選這家的變體、什麼會讓它被換掉」，它讀的是點不是邊；
-  答不出就寫「缺 X」並向使用者要文件，不得用供應商自述補（L8）。
+  答不出就寫成加碼條件並向使用者要文件，不得用供應商自述補（L8）。**讀到邊是加碼的門、不是起始的門**（<核准日>；
+  決定紀錄 §10.1 條 2 作答 (a)：門對邊緣小公司天生答不齊，是設計太嚴、不是方向錯）。
```

```diff
-- **候選狀態是封閉字彙：可開／缺 X／已定價等回落／不要／已持有。** 「可開」是每檔各自過的 filter 不是分數，可同時多檔；
-  **可開為零就零，不得為了非空放寬條件**——讓它非空的路是研究。「缺 X」與「等回落」必鑄 watch；「不要」附理由、append-only。
+- **候選狀態是封閉字彙：可開／缺 X／不要／已持有。** 「可開」是每檔各自過的起始門、不是分數，可同時多檔：會死嗎不是紅、
+  押的那一層讀過且判讀不是 neither、反證已寫下且有到期、「已定價嗎」寫成一句脈絡（已定價時翻倍條件寫得更嚴）。
+  讀到邊與深挖清單是**加碼條件**，住同一份敘事、各自鑄 watch；起始與加碼是兩個時點，不是尺寸。
+  **可開為零就零，不得為了非空放寬條件**——讓它非空的路是研究；門的設計只由使用者在決定紀錄裡改。「缺 X」必鑄 watch；「不要」附理由、append-only。
```

**17（第 145 行之後補一點）**

```diff
 - **部位真相是 Google Sheet（2026-09-16）**；「當時憑什麼決定」的收據跟著成交事件走，舊 Decision Store 凍結唯讀（2026-09-22）。alpha 原則上不用貸款資金是使用者自己的紀律，**系統不建 gate**。
+- **沒買也是決定（<核准日>）**：決策時段看過的可開與只差已定價，每檔的選擇（進／不要／等到條件）連一句理由與當時的敘事版本，
+  跟成交事件走同一條路、同一種收據，append-only（A5）——它回答「當時憑什麼沒買」；系統不由它產生任何動作、不由它算尺寸。
```

**20（第 246 行之後補一句）**

```diff
 - **subagent 委派預設關閉、每次明確 opt-in**；回傳只是 review packet；不得委派任何寫入、核准、入圖、thesis mutation、資本配置、commit／push。
+  **常規 opt-in 只有一種**（2026-11-02 使用者：「隨機抽查 開subagent這件事 其實你就當成我是開綠燈吧」）：入圖包隨機抽查——
+  抽中的包交乾淨 context 的唯讀 reviewer 從頭核、回 review packet；抽中與否、核出什麼都不改 gate，入圖仍是人工 `go`。比例與加密規則住 ARCHITECTURE。
```

**go 之後的實作範圍**（每項各自 commit；18＋16 與 17 是 Z2，照 development-flow）：
- 18＋16：`open_preconditions` 改起始四項、讀到邊與深挖清單搬進 `confirm[]`；等回落併回可開（封閉字彙少一格，候選板、心跳、APP、序列跟著改；
  舊紀錄的等回落照「可開＋已定價脈絡」讀，不回寫）；research-drain 段 5；plan 2026-11-01-002 P2 改 ✅。
- 17：「看了沒買」的載體——與 `library/trades/` 成交紀錄同處、同收據格式、kind＝看了沒買；寫入端拒收缺理由或缺敘事版本的；測試＋變異同一個 change。
- 20：ARCHITECTURE 寫比例（每 10 包抽 1、K>0 且 M=0 就加密）；skills 改入圖包呈現（第一行只寫要你判斷的一句，無判斷成分的標「純機械」）；
  計數器「本月照建議 go N／偏離 M／事後抓到包內缺陷 K」讀 `todo_pool.json` 既有欄位，零 schema 變更。

## 7. 兩個契約改法（2026-11-03 起草；L17「動 contract 給 proposal」——使用者看過、回 go 才實作）

**第 12 條：讀圖 `neither` 也要付「換得掉」的證據（Z1–Z2）。** 既有 v3 讀圖 neither 36 份（全部版本）——契約的 `__post_init__`
讀舊紀錄時也會跑，所以規則放**寫入端**擋新的，舊的不回溯。

```diff
 # alpha/structure_reading/contracts.py
 KINDS_REQUIRING_CITATIONS = frozenset({"moat", "volume"})
+#: `neither` 也要付證據（<核准日>，盲點修法第 12 條；審查 research_quality-5：「換不掉」要付證據、「換得掉」免費——
+#: 讀圖若偏向 neither，系統既擋了人、又永遠量不出來）：至少一段引用標出「換得掉」憑的是哪一型來源。寫入端擋新的、舊的不回溯。
+KINDS_REQUIRING_REPLACEABLE_BASIS = frozenset({"neither"})
+#: 「換得掉」的來源型別（封閉字彙）：買方事實／買方政策／第三方／媒體。供應商自述不在裡面——收緊，不是放寬 L8。
+REPLACEABLE_BASES = ("buyer_fact", "buyer_policy", "third_party", "media")

 class Citation:
     independent: bool = False
+    #: 「換得掉」憑的來源型別（neither 用）。None＝沒宣告；as_dict 只在有值時寫——舊紀錄的 id 不變。
+    basis: str | None = None
     def __post_init__(self) -> None:
+        if self.basis is not None and self.basis not in REPLACEABLE_BASES:
+            raise ContractViolation(f"citation.basis 未登記：{self.basis!r}；已知 {list(REPLACEABLE_BASES)}")

 # alpha/providers/structure_readings.py::append_reading_record
     if not parsed.retracted:
         problems = verify_disproof_sources(record, existing)
+        if parsed.kind in KINDS_REQUIRING_REPLACEABLE_BASIS and not any(c.basis for c in parsed.citations):
+            problems.append("neither（換得掉）也要付證據：至少一段引用標 basis（買方事實／買方政策／第三方／媒體）——"
+                            "供應商自述不算；判不出來請寫 undecided 並說缺哪一格")
```

另：追蹤表 paper lane 加子行「騎在 neither 層上的邊緣公司：N 列｜等權絕對｜曾達 2 倍」（只印、帶小樣本旗；審查時只有富世達 6805.TW）；
research-drain 寫讀圖那段補一句。預期副作用：之後的 neither 會有一部分改寫成 undecided——這正是收緊要的。

**第 10 條②：敘事反證多一個「逾期型」宣告（Z1）。** 計數器要分得出「X 未在 D 前發生」型的反證，今天的欄位分不出來；
用字串比對去猜是會誤報的 linter（L16），所以加一個宣告欄。

```diff
 # alpha/narrative/contracts.py::NarrativeDisproof
     source: str
     link_source_ref: str | None = None
+    #: 逾期型（<核准日>，盲點修法第 10 條②；審查 strategy-4：事件型反證要等一份新文件才醒，輸家常常什麼都不發）：
+    #: 條件寫成「X 未在 expires 前發生」，到期本身就是觸發。只是宣告——到期照舊是重問，不自動判觸及、不改出場規則。
+    #: as_dict 只在 True 時寫——舊紀錄的 brief_id 不變。
+    deadline: bool = False
```

另：候選板 counts 多一格、短版狀態塊印「逾期型反證 0 條的持有／可開敘事 N（逐檔）」（今天可開 0、持有 2：COHR、SIVE.ST）——
plan 原寫「追蹤表」，建議改這裡：它數的是現行敘事、不是 lane 的列；`alpha brief --add` 宣告可開或已持有時一條都沒有就印一行提醒
（只印、不擋）；research-drain 段 5 一句「持有／可開敘事至少一條反證寫成『X 未在 D 前發生』並標 `deadline: true`」。

## 8. 進度（2026-11-03 本機 session；依 §4 順序）

| § | 項 | 狀態 |
|---|---|---|
| §4-1 | §1 第 1 條 Q3W 裁決回填＋「到點 N｜已寫 M」 | ✅ `639e889a` |
| §4-2 | §1 第 2 條 drain 提示只在進展格推 | ✅ `7f399a96`（偏差：只差已定價／可開不算進展格——它們進 ③ 待你決定） |
| §4-2 | §1 第 3 條 只差已定價進 ③ | ✅ `d2c55b25`；真資料 ③＝STLTECH.NS 1 檔（預期的 3081／4979／AXTI 各有醒來待判的反證 watch，要判完才會進來） |
| §4-2 | §1 第 4 條 MOPS 全市場報告進段 1 | ✅ `e684c028`（多修一處：fetcher 原本先丟掉代號解析不出的列） |
| §4-2 | §1 第 5 條 ConfigBoundaries | ✅ `14d1ed07` |
| §4-2 | §1 第 6 條 預篩 vs 互動一致率 | ✅ `40b290c1`；近 30 天 467 筆，對回去 123：一致 109、不一致 3、看不出 11 |
| §4-2 | §1 第 20a 條 #58 庫內已有幾份 | ✅ `bfbdff2b`；#57 不做：結構上已修，字串偵測 10-21 已否決 |
| §4-2 | 第 21／22／24 條 | ✅ `6f816063`、`44abe853` |
| §4-3 | §2 第 8、13 條＋量測三條 登記 | ✅ `bb0a0c39`（先於任何計算） |
| §2 | 第 7 條 | ✅ `aec4b775` |
| §2 | 第 9 條 by_anchor_state | ✅ `c9939d63` |
| §2 | 第 10 條① 跌深 vs 反證觸及 | ✅ `1e9922c6`；真資料 paper 36：1（AXTI）、history 6：0 |
| §2 | 第 10 條② 逾期型反證 | 待看 §7 diff |
| §2 | 第 11 條 AXTI 10-Q 複查逐條寫方向與時窗 | 研究；10-Q 約 11-13，跟 [896] 一起做 |
| §2 | 第 12 條 neither 付證據 | 待看 §7 diff |
| §2 | 第 14 條 月營收重答數 | ✅ 登記 `3e19605a`；結果 11-14 append 在 cases.md Q3W 處置紀錄 |
| §2 | 第 15 條前半 海關提單按需路徑 | ✅ `f8806991` |
| §2 | 第 15 條後半 Form 4 code P 拿出 auto no_go | ✅ `007682e4`（附 sandbox impact review）；實測 466 份 Form 4 裡 23 份含 P，21 份是 TSM——3.5 個月約多 23 則進分類層，多半會被篩掉 |
| §2 | 最後一列 ②第二基準 | ✅ `91e69899`；名單 T0 → 11-03 −25.6%，paper 對它超額 +0.4% |
| §2 | 最後一列 ①敘事事實抽樣、③影子重寫 | ①每段 drain 收尾照 skill 抽；③ 2026-12 起 |
| §4-4 | 18＋16、17、20 的 AGENTS diff | 待使用者看 §6 |
| §4-5 | 19 六個市場、23 數字 | ✅ 11-03 使用者答：19＝`1d7c7e34`（登記先於程式）、`de28f2be`（paper 138 → 137 列，最大單檔貢獻者 688836.SS → CLF）；23＝決定紀錄 §10.2 |
| §4-6 | materialize＋P0＋H15 凍結 | ✅ `f66a0c29`（P0：個股頁與首頁卡片都印出只差已定價；H15 邊緣 80、鄰組 16）；ROADMAP 旁支「候選板標出只差已定價」搬進已交付（原列逐字封存） |
