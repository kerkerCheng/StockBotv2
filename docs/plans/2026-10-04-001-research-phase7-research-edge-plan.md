---
date: 2026-10-04
topic: phase7-research-edge
status: active
derived_from: docs/brainstorms/2026-10-04-phase7-research-edge-proposal.md（能力盤點、failure analysis、十個假說、回放與前瞻設計、驗證集、§13 決策流程）、docs/ROADMAP.md（Phase 7 列；本 plan §0.4 amendment A1 新增）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G1–G12、§6、§10）、docs/reports/2026-10-03-phase6-closeout.md §5、AGENTS.md（L7、L11、L12、L14、L16、L17、L18、L19；INV-2、INV-3、INV-5、INV-6）
---

# Phase 7 研究使用與量測（持續型；第一期到 2026-12-22 檢查點）

> **執行者分工（使用者 2026-10-04 定案）：** 開發 Step（7.0b–7.0f）與機械回放（7.2 的 R1、R3）由執行模型走 `skills/development-flow/SKILL.md`
> （Z1 以上 R1；7.0d、7.0f 另有 R2，見 §0.5）；**研究 Step（7.0a 的登記內容、7.1、7.2 的 R2／R4、7.3、7.4）用強模型在互動 session 做**——
> 讀圖、敘事、case 裁決都是判斷（決定紀錄 §6.3）。
> 本 plan 從 proposal 與 ROADMAP「Phase 7」（本 plan §0.4 A1 新增）導出；衝突時以 ROADMAP、決定紀錄與使用者定案為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → ROADMAP「Phase 7」列 → proposal 全文（§0 AXTI 時間表、§3 十個假說、§4 回放的兩個限制、§5 前瞻設計、
> §6 驗證集、§13 決策流程）→ 本 plan §0.1–§0.4 與附錄 → `docs/reports/2026-10-03-phase6-closeout.md` §5（帶進來的待決題）→ 各 Step 指名的檔。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表／機制），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 研究的驗收數的是**讀圖**、**敘事**、**等待 registry**（watch、lead、截圖假說、pq2）與
> **追蹤表**（case 表、2×2、回放）；開發的驗收數的是**機制存在與否**。**候選板「可開」只印不驗收——可開為零就零。**

**一句話目標：** 用預先登記的真實案例與前瞻凍結，逐步淘汰錯的 edge 假說；同時讓 APP 照「每檔過五題、小部位起步、確認了才加碼、反證才出場」的流程呈現，
讓研究正常產生可以下手的候選。**它不排序、不打分、不給尺寸；開發只從 failure log 來。**

---

## 0.1 使用者定案（2026-10-04；「都照你建議」＋「先這樣做一版」）

| # | 題目 | 定案 |
|---|---|---|
| Q1 | Phase 7 的形狀 | **A**：持續型研究期，研究約 75%／量測約 15%／開發 ≤10%；12-22 是第一個檢查點、之後每季；開發只從 failure log 來（≥2 個 case 重複）；AGENTS 加一句（§0.4 A2） |
| Q2 | 新的鏈（decompose 選題是使用者的） | **A**：光通訊（既有，跟 Q3 財報）＋**電力**（超高壓變壓器與它的上游：電工鋼、套管、分接開關、測試產能；09-03 800VDC decompose 擱置的五則）＋**散熱**（小規模，台股液冷——月營收讓中迴路變快） |
| Q3 | 歷史回放 | **A**：只做機械的四個（R1 已定價回放、R2 parked 回查、R3 漏網稽核、R4 history lane 輸家驗屍）；LLM 不站在 2026-06 之前判讀 |
| Q4 | SNS | **A**：40 則首次點名的人工 claim 裁決（用截圖假說層），不建引擎；**X 帳號使用者之後逛到再加**——加入那天起量、不回溯，記一筆來源變更（§1 第 5 項） |
| Q5 | 新聞雷達 | **A**：daily 加一步只開 WebSearch 的 `claude -p`，網址必須出自同一次搜尋結果、每日上限約 5 則、寫成 tier-4 secondary lead、不另發通知；八週試驗＋停止條件；sandbox impact review＋R2 |
| Q6 | 個股頁表達 | **A**：「已定價」白話；敘事允許寫「要翻倍需要什麼」（營業數字，不寫目標價）；重押讀圖時換格層引用（Phase 6 #16） |
| Q7 | 執行期間 R2 | **A**：研究 Step 不做 R2（四個人工 gate 照舊管）；開發 Step 命中六條 trigger 常規 opt-in（預定 R2-a＝7.0d、R2-b＝7.0f）；檢查點 R2 常規 opt-in |
| Q8 | 研究節奏 | 每週 2–3 次互動研究 session；兩波各約 4–6 週 |
| A1 | APP 的組織原則 | **A**：五題（押什麼／押對夠大嗎／錯了怎麼知道、哪天知道／會不會死／是不是新賭注）＋起始部位＋確認了才加碼＋反證才出場（proposal §13；附錄 C） |
| A2 | 敘事加「加碼條件」 | **A**：加 `confirm[]`，與反證對稱：寫下即登記 watch，觸及只提醒「結構確認了」、不是買進訊號；7.0d，wave 1 的新敘事就能用 |
| A3 | 標「和持股共用需求錨」 | **A**：要（候選板與個股頁；機械、只列不排） |
| A4 | 成交紀錄加階段 | **B**：先不要；使用者第一次照起始／加碼節奏下單前再加（檢查點待決題） |

## 0.2 現況實測（2026-10-04 寫 plan 當下；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| 結構讀圖 | 現行 **4 份**（`mat:inp_substrate`、`tech:cw_dfb_laser`、`prod:supernova`、`prod:els_8ch_module`），全在光通訊；ledger 17 筆 | `Get-ChildItem library\private\alpha\structure_readings`；各檔行數 |
| v2 敘事 | **4 檔**（AXTI 等回落、COHR 不要〔非邊緣〕、LITE 不要〔非邊緣〕、SIVE.ST 缺 X）；ledger 共 20 行 | `Get-ChildItem library\private\alpha\briefs`；`python -m alpha brief <T> --list` |
| 候選板 | 可開 0｜缺 X 0｜等回落 1｜不要 0｜已持有 2（COHR、SIVE.ST）｜非倍率候選 1｜無敘事 72／76 | `library/private/app/state/candidates.json` 的 `counts` |
| 等待 registry | watch 171（語意條件 active 36、consumed 30、fired 1）；pq2 未結案 1（manual） | `library/leads/event_watches.json`；`python -m engine_b.todo list` |
| lead registry | 1,212 則：triaged_go 23（最老 first_seen 2026-08-26）、parked 484（其中 `original_obtained` 353）、triaged_no_go 617、applied 88 | proposal §2 的查證命令 |
| 被點名未登記 | 111 | `python -m engine_b.cli onboard-candidates` |
| 外部來源 | X 帳號 1 個（aleabitoreddit，probation；992 次具名點名、40 檔）；本月 X 花費 $0.01／上限 $10 | `config/signal_sources.json`；心跳段 1 |
| 帳號計分表 | 30 天對主題等權組 −6.3%（n＝802）、首次點名 90 天 −11.1%（n＝29）；`hypothesis_hit_rate`＝`capability_absent`；追源成功率 39%（n＝471） | `library/private/app/state/account_scorecard.json` |
| 追蹤表 | history 22（入圖日錨，8／22 入圖前已漲）、paper 4（09-29 起）、live 0 | `library/private/app/state/positions.json` 的 `lanes` |
| 圖預測 | 對 0／錯 0／現行 2／改寫 11／非斷言 4；現行最早到期 2027-01-01 | 心跳段 4「圖預測」 |
| 截圖假說 | 7 則（verified 2、active 5；兩則 InP 漲價／短缺 08-31 登記、至今 active） | `python -m engine_b.hypotheses list` |
| 圖 | SourceDoc 220（有日期 207；2026 年發表 160）、assertion 697、公司節點 90、技術／產品／材料 186（只有一家供應商 118） | proposal §1 與決定紀錄 §1.1 的 Cypher |
| 名冊／主題 | 名冊 103 家；`config/themes.txt` 3 個主題（cpo、sivers、robotics）；主題等權組 1 組（AI 光互連／CPO，15 檔，`tc_35b0d5cd521656ea`） | `config/company_identity.json`；`python -m alpha theme-cohort` |
| SessionStart「thesis 逾期」 | 「cpo 91／90 天、sivers 36／30 天」——**兩則都是提醒程式量錯**：它量 memo 的生成日、不看 `thesis/lifecycle.json` 的 `last_checked`；sivers 2026-09-29 已複查（pq2 [655]，無 mutation 所以 memo 沒重寫）；`cpo_v1_lane_memo.md` 是被 `coherent_cpo_v2` 取代、沒有 lifecycle entry 的舊 memo（套 90 天預設） | `crons/thesis_freshness_check.py::check`；`thesis/lifecycle.json` |
| 測試 | 3,448 passed／1 skipped；invariants 14 PASS（Phase 6 結案） | Phase 6 closeout §6、§8 |

## 0.3 本 Phase 刻意不做

- **不排序、不打分、不給尺寸、不設門檻。** 五題、加碼條件、共用需求錨都只呈現：不進候選狀態的前提、不排序、不換算金額（G1、G6、AGENTS「消費契約」）。
- **不算目標價、不加回估值模型**（G3）。「翻倍條件」寫營業數字（營收、出貨、產能、毛利），`{price}` 仍不得出現在那一格；不算「倍數回到中位數時營收要多少」（proposal §13：會重演 H9 的失敗）。
- **不做完整歷史回放；LLM 不站在 2026-06 之前判讀**（proposal §4.2：研究者的知識截止污染）。
- 不建 reputation engine、不自動化 claim 裁決、不做二階瓶頸的 schema 或走圖新型別（proposal §8：三個 case 之前沒有證據）。
- **不升 narrative 的 `record_version`**（47 處程式判 `RECORD_VERSION_V2`；`confirm[]` 做成 v2 的選填欄，§0 第 7 條）；不開新 state kind。
- 不改 `scripts/record_trade.py`（A4＝B）；不寫 trade_log、Google Sheet；不動舊 Decision Store。
- 雷達的 lead **不喚醒語意 watch**（T0 只認一手文件，G7）、不另發通知（AGENTS「Canonical Brief 只有一份」）。
- 海外財報來源照旁支：研究撞到哪個市場才做那一格（韓國 DART 等 key 由使用者申請）。
- Phase 6 待決 #10–#15 照帶（被某個 case 撞到才進 failure log）。

## 0.4 amendments（五欄；使用者 2026-10-04 定案；本 plan 的 commit 同時改 ROADMAP 與 AGENTS）

**A1｜ROADMAP 新增 Phase 7「研究使用與量測（持續型）」**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 沒有 Phase 7；`docs/plans/README.md` 記「使用者 2026-10-04 定：先研究，Phase 7 暫不開，到 12-22 回查再議」 |
| 新觀察 | 同日稍晚的整體能力評估（proposal）：機制遠超過使用——7 個 Phase、測試 3,448，讀圖 4、敘事 4、可開每天 0、外部來源 1 個；edge 有沒有、從哪裡來，現有量測要到 2027 才成熟；唯一證據完整的案例（AXTI）顯示判斷層可能把我們從贏家身上說服走（n＝1） |
| proposed change | ROADMAP Phase 表新增「7 研究使用與量測（持續型）」一列（做什麼／為什麼／驗收／前置見 ROADMAP）；plan＝本檔；「研究並行」一節註明 2026-10-04 起研究本身就是 Phase 7。「先研究」的決定不變——Phase 7 就是那個研究，只是有了預先登記、凍結與檢查點 |
| why | 使用者 2026-10-04：「直接把整個當作 phase7；phase7 可以是持久且延續的，除非我們想要做其他系統層的改動」 |
| impact | 新增一列；不改 Phase 0–6；`docs/plans/README.md` 的「目前沒有 active 的 Phase plan」段改寫 |

**A2｜AGENTS「開發項不走 pq2」段加一句**

| 欄 | 內容 |
|---|---|
| 原 AGENTS | 「系統主動提出的開發構想寫進 ROADMAP 待排程，**不主動要求 `go`**。ROADMAP 每項強制四欄（做什麼／為什麼／驗收／前置）；」 |
| 新觀察 | 09-22 → 10-04 交付 7 個 Phase，驗收多半是「機制存在與否」；同期研究產出 4 份讀圖、4 份敘事（proposal §2 F1、F9） |
| proposed change | 該句之後加：「**系統主動提出的開發項，「為什麼」必須指得出暴露它的真實案例與重複次數，指不出來的不排程**（L17 的當下修除外；2026-10-04）；」 |
| why | 使用者 2026-10-04：開發必須由真實失敗驅動；這句是邊界不是手段（不指名函數、表、門檻或 Phase），符合 AGENTS 准入判準；使用者直接指示的開發項不受它限制（AGENTS「使用者主動指示＝已授權」） |
| impact | AGENTS 一句；development-flow 八欄的範圍欄加「暴露它的案例」（Step 7.0b）；ROADMAP 新開發項的「為什麼」照寫 |

**A3｜O6（光通訊磊晶與 MOCVD 產能）從 7.4 提前到 7.1，以「層說明」形式產出（2026-10-06 使用者定案）**

| 欄 | 內容 |
|---|---|
| 原 plan | 進度表：O6 是 7.4 Wave 2 的二階瓶頸三個 case 之一；7.1 的清單是積壓、電力與散熱開題、S1 claim 抽樣、O3、O5 |
| 新觀察 | 2026-10-06 brainstorm（個股頁 schema §11 F40–F42、failure log #28）：讀圖五角度全是拓撲，沒有「客戶為什麼選這家的變體」那一格；11 檔「缺 X」裡 X 是層說明補得了的，InP 磊晶最多（IQE.L 缺的就是這一層的讀圖、全新 2455 缺 CW 雷射客戶、聯亞等回落），而且圖上沒有這一層（聯亞掛在下一層、IQE 的磊晶邊接在客戶公司上） |
| proposed change | 7.1 加一項、排第一件：InP 磊晶層說明（個股頁 plan S4 的四段規格：物理與變體／各家變體與階段附證據等級／客戶為什麼選這家的變體附客戶端出處／主張登記成 watch），落 `library/private/research_notes/`，新層節點與重掛邊走 RA → pq2；它同時是 O6 的 case 段 |
| why | 使用者 2026-10-06：「選對我系統來說最有價值的」；一份研究兩邊用（O6 與 S4）；圖的形狀本身是錯的，層說明寫完會動圖 |
| impact | 進度表 7.1 一行；§7 清單加第 6 項；ROADMAP Phase 7 列不改（它只寫「二階瓶頸」不列 case）；7.4 的二階 case 少一個、不補 |

**A4｜研究預算分層：深度在層、廣度在檔——閉環母體收窄（failure log #22 從 7.5 提前）、資料檢查跟著全部個股頁、research 面板降選配（2026-10-07 使用者定案 Q1 A、Q2 A、Q4 A；Q3 待決）**

| 欄 | 內容 |
|---|---|
| 原 plan | 7.1 照 research-drain 段 5 跑「每檔閉環」，母體＝全部已 materialize 的個股頁、不分邊緣；#22（沒有誠實出口的檔）的修法排 7.5、二擇一；`NEXT_PICK_RULE` 前兩條是「有 EPS 共識」「forward EPS 為正」；個股頁核心面板含 `research`（舊式 session 判斷）；資料錯靠寫敘事的人撞到（#20 A＋H 股數、#23 營收幣別差 32 倍、#27 同日多筆生效，三個都是寫非邊緣檔的敘事時發現） |
| 新觀察 | 10-05 首版敘事 66 份，其中 39 份理由以「非邊緣」開頭、之後 0 筆改判；5 份層說明改了 2 筆候選狀態（4971.TWO 不要→缺、6805.TW 缺→不要），並在它碰到的 7 份廣度敘事裡抓到 3 個事實錯（#32、#35、#36；挑過的樣本，不外推）；閉環剩 26 檔，20 檔非邊緣、6 檔邊緣裡 4 檔沒有供給側座位（2026-10-07 實算：`alpha.providers.edge.edge_states`＋結構表 artifact）；EPS 兩條引用的 `alpha/fundamental/bridge.py` 已在 Phase 0 刪除，讓有共識的大型股排在前面，方向與決定紀錄 G4（預算從深挖大公司移到列舉薄層的供應商）相反；股數檢查遇到沒有財報股數的檔直接跳過、不出聲（INV-3） |
| proposed change | 新增開發 Step **7.0g**（§6b），四段依序：①**資料檢查**（Q2 A）先做——營收量級（新）、股數（補覆蓋）、同日多筆生效（既有）三個檢查的母體改成全部個股頁、不跟閉環走，每個檢查印比對數與無法比的逐檔清單，三個原始案例回放命中才往下；②**閉環母體**（Q1 A；#22 選項②）＝已持有 ∪ 有 thesis（lifecycle：使用者明示）∪（邊緣或量不到 ∩ 供給側有座位）∪ 現行候選（缺 X／等回落／可開）；母體外逐檔列名分兩類（非倍率：附市值與覆蓋、每次 materialize 重算、翻回邊緣就回母體；邊緣沒座位：列「坐哪一層」短檢查，查過的 90 天後重問）；刪 `NEXT_PICK_RULE` 的兩條 EPS；③**`research` 面板降選配**（Q4 A）；④research-drain 段 5 寫進分層（非倍率不寫敘事、邊緣沒座位做短檢查、廣度短敘事的範圍與三項必查、層深讀的入口） |
| why | 使用者 2026-10-06：「我們需要針對每一檔都這麼高深度的讀圖嗎？……如果已經定價，可以研究當作借鏡，但不會是主要 token 花費的地方」；2026-10-07 選 Q1 A、Q2 A、Q4 A。深度的單位是層（一份層說明同時改坐在那一層的多檔），廣度是每檔一份有範圍的登記；「下一個研究誰」仍只由觸發或 lead 的時間與使用者點名決定，系統只說「這檔／這層命中了觸發條件 X」、不做跨檔比較（G2） |
| impact | 本檔進度表加 7.0g、§6b 新節、§14 加 12–15；failure log #22 由「→ 7.5」改「→ 7.0g」；ROADMAP 旁支表加一列（四欄）；`alpha/closure.py`、`alpha/providers/closure.py`、`alpha/providers/candidates.py`（沒有敘事那幾檔也算邊緣）、`webapp/__main__.py`（closure-gate）、`briefing/analyst_view/contracts.py`（`CORE_PANELS`）、`skills/research-drain/SKILL.md`；AGENTS 不改（L19：手段句不進 AGENTS）。**Q3（層頁先做或跟 S5）待使用者回覆，不在本 Step** |

**A5｜拿掉「開發 ≤10%」比例；判準改成「它擋不擋研究」，過 gate 的開發項隨時提（2026-10-07 使用者定案）**

| 欄 | 內容 |
|---|---|
| 原 plan | §0.1 Q1「持續型研究期，研究約 75%／量測約 15%／開發 ≤10%……開發只從 failure log 來（≥2 個 case 重複）」；ROADMAP Phase 7 列同一句比例；§11 第 3 項：過 gate 的開發項到 7.5 檢查點才以五欄 amendment 提給使用者 |
| 新觀察 | 2026-10-07 Q3（層頁先做或跟 S5）的推薦理由之一是「開發預算上限 10%」——比例在替一個判斷背書，自己卻沒被量過（INV-5）；7.0g 是開發，交付後段 5 才不再替大型股寫淺敘事——該做的開發本來就在替研究開路；6 條層主張因為層說明 ledger 還沒落地而沒有到期（INV-2 缺口），等比例或等檢查點都是繞路 |
| proposed change | ①拿掉比例（ROADMAP Phase 7 列改寫；§0.1 Q1 是使用者 10-04 的定案原文，留作歷史、由本 amendment 取代；個股頁 plan 那一句同改）；②開發排在哪裡只看**它擋不擋研究**：研究要用卻用不了、研究產出沒地方落地或沒有到期的，排在研究前；不擋的照 ROADMAP 排程；③過 gate 的開發項**隨時**以五欄 amendment 提，不等 7.5（§11 第 3 項改成「列出期間提過、做過的開發項」）；④**不變**：系統主動提出的開發項仍要指得出真實案例與重複次數（AGENTS「開發項不走 pq2」那句；使用者直接指示與 L17 當下修除外）；開發的驗收仍只數圖、讀圖、敘事、registry、追蹤表（G10） |
| why | 使用者 2026-10-07：「開發預算上限 10% 這個看要不要拿掉，太死了，真的該開發的東西還是要擺在研究前，不必為了這個條件繞遠路」 |
| impact | ROADMAP Phase 7 列一句；本檔 §11 第 3 項；個股頁 plan「和 Phase 7 的關係」一句；AGENTS 不改（比例本來就不在 AGENTS；「指得出真實案例」那句是邊界、不是比例，照留） |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者已核准的 PLAN_PROPOSAL**（§0.1）。`AGENTS.md`「常規推進授權」照用：Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**；
只有六條停止條件之一成立才停。**本 Phase 執行期間六條 trigger 命中的 R2 常規 opt-in（Q7）**：預定 **R2-a**＝7.0d（append-only 敘事 ledger 的契約與 watch 語意，
trigger 1）、**R2-b**＝7.0f（無人值守 LLM 步驟的能力變更，trigger 3）；其他開發 Step 若命中同樣直接發 `WORK_REQUEST`。研究 Step 不發 R2。
條件修正後的覆核：開一位新的、窄範圍的審查者，條件原文照貼，不喚回原審查者。NO_GO → `AWAITING_HUMAN`。

**Step 的順序與交錯：** 7.0a 一定最先（預先登記早於任何新研究紀錄）。**7.1 的「積壓」那一半在 7.0a 之後就可以開始**（清 lead、掃題材不需要新範本）；
**寫新敘事要等 7.0c、7.0d 落地**（範本與 `confirm[]`）。7.2 可與 7.1 交錯。**7.3 有日期（各家財報日），到點插隊**。進度表的順序是預設，不是限制；
`/phase-run` 從第一個未 ✅ 的 Step 接續——研究 Step 由強模型在互動 session 跑，便宜模型跑到研究 Step 就停下交回（HUMAN SUMMARY 寫「下一步要強模型」）。

**pq2 停點（掛號後接著做下一件，不停在編號上等——AGENTS）：** 新鏈的主題等權組成分（`todo add-theme-cohort` → go → `complete-theme-cohort`）、
入圖（`ra_admission`）、thesis mutation、lead registry 更正、Engine C 判讀寫入。**decompose 選題使用者已定（電力、散熱）**：鑄 manual pq2 只為稽核、受理時即 resolve，
不回頭再請求 `go`（AGENTS「使用者主動指示＝已授權」）。每個研究 session 收尾印「目前等你 go 的編號」與一行批次指令。

**每個 Step 一個 commit（大的可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。** 研究 Step 每個 session 收尾一個 commit
（case 表、failure log、收據）。新 session 先看下面進度表與 `git log --oneline -20`。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30）是唯一排程；動到 daily 會跑的程式（7.0d、7.0e 的 materialize 與心跳、7.0f 的新步驟）的 commit
**不得跨越 05:30 還沒 push**；寫 `library/` 的 authority（讀圖、敘事、`event_watches.json`、lead registry、截圖假說）前先
`python scripts/writer_guard.py acquire --minutes <N> --purpose "<做什麼>"`，寫完 `release`（7.0b 修好巢狀鎖之前，**不要在持鎖期間跑兩支遷移工具**——Phase 6 #17）。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 7.0a | 預先登記（十個假說與殺死條件、驗證集、裁決規則、failure log、開發 gate、漏網稽核母體）＋T0 凍結 | ✅（`docs/reports/phase7/` 四檔：registration——H1–H10 各附殺死條件與最小 n、16 個 case〔附錄 A 14＋二階 O1-U、O6〕、R3 母體〔光通訊組 15＋觀察名單 43〕、S1 框架 40 則、R2 樣本 36 則；T0 manifest `library/private/measurement/phase7/T0-2026-10-04.json`〔07:09:14Z，計數與當日心跳一致〕；偏差 #1–#4） | 強模型 | 見 git log「Step 7.0a」 |
| 7.0b | 開發 gate 落地（development-flow 範圍欄）＋兩個當下修：巢狀 writer lock（Phase 6 #17）、thesis 逾期提醒量錯 | ✅（INTAKE 加 `Case` 行＋`Zoom / Review` 重抄；`writer_lock.hold` 一個 owner，四支遷移工具改用；逾期只看 `is_due`——SessionStart 兩則假逾期 → 0、10-30 照報 axt_inp＋sivers；偏差 #5–#8） | 執行模型 | 見 git log「Step 7.0b」 |
| 7.0c | 敘事範本：「要翻倍需要什麼」＋兩個 placeholder（市值、近四季營收）＋「已定價」白話＋重押讀圖換格層引用（Phase 6 #16） | ✅（題目與字彙；`market_cap_settlement`——IQE.L 換成 7.3 億 GBP；「已定價」白話一份、首屏與稽核區各一次〔Edge 實點〕；寫入端第 ⑦ 項；四檔敘事 8 格逐字相同；偏差 #9–#11） | 執行模型 | 見 git log「Step 7.0c」 |
| 7.0d | 敘事「加碼條件」`confirm[]`：寫下即登記 watch、觸及只提醒、到期重問；心跳、候選板、個股頁（R2-a） | ✅（v2 選填欄、只在非空時進 id——真實 ledger 20 行重算逐位相同；watch `brief:<id>#c<n>`＋`condition_role=confirm`，判斷只住 `is_confirm`，反證計數、downside、可開都不吃〔變異紅〕；觸及與到期進 `narrative_rewrite`、以 `confirmed` 處置、候選狀態不自動改；心跳一行＋三個快照鍵、候選板與個股頁逐條列〔句子在 materialize 端組好、前端照印〕；**R2-a GO**〔獨立重算 20/20、兩個變異紅、consumer 逐處盤點無漏〕；偏差 #12） | 執行模型 | 見 git log「Step 7.0d」 |
| 7.0e | 個股頁首屏照五題排列＋候選板與個股頁標「和持股共用需求錨」 | ✅（五題對照唯一一份 `FIRST_SCREEN_QUESTIONS` 經 `.meta.json`、app.js 不留第二份；`shared_bet` 只呈現、依 ticker 字母列、缺席分型由產生端宣告；改前改後各 materialize 76 頁——拿掉新欄位、時間戳與價格脈絡後 76/76 逐字相同、`freshness_identity` 76/76 相同；Edge 實點四頁五題 5/5、COHR 與 SIVE.ST 互列 CW DFB 層；變異六個紅；偏差 #13–#14） | 執行模型 | 見 git log「Step 7.0e」 |
| 7.0f | 外部雷達：daily 只開 WebSearch 的 LLM 步驟、八週試驗（R2-b；sandbox impact review） | ✅（探針：不放行時 WebSearch 被拒、卻回 `is_error: false`＋空結果→一律判失敗；最窄放行＝`permissions.allow`；雷達 init 與零工具那份只差 `tools`；daily ①b–①e、`radar.enabled`（沒有那一段＝關閉）；網址必須出自同一次搜尋〔程式從 stream 收〕、去重且已登記的不碰、每日 5 則、secondary、不喚醒語意 watch；triage 批次雷達排最後〔偏差 #16〕；真資料試跑：搜尋 16 次、148 網址、提議 0；變異八個紅；**R2-b GO**〔11 種網址變體無一繞過、找不到多拿能力的路徑、prompt 無持股〕；偏差 #15–#18；**第一輪真實排程 2026-10-05 05:30——看心跳段 3 那一行與 `radar_2026-10-05.json`（ROADMAP 驗收⑦）**） | 執行模型 | 見 git log「Step 7.0f」 |
| 7.0g | 研究預算分層（A4）：資料檢查跟著全部個股頁 → 閉環母體收窄（#22 提前）＋刪兩條 EPS → `research` 面板降選配 → 段 5 分流文字 | ✅（2026-10-07；R1。①資料檢查母體＝全部 92 頁：股數比 60／比不了 32 逐檔列、營收量級（新，materialize 端換匯）比 67／0 檔對不上／比不了 25、同日多筆生效 14 組；三個原始案例回放 3／3〔#20、#23、#27〕；幣別標籤抽成 `alpha.contracts.reporting_currency_for` 單一函式。②`closure.population_for`：可推進 26 → 6〔短檢查 6481.T、XFAB.PA、XPEV、5411.T；廣度敘事 CLF、SILEX.ST〕、非倍率 56 檔逐檔列名、邊緣沒座位已查 2〔2768.T、CCXI〕；#22 的量 17 → 0；EPS 兩條與 `_consensus_flags` 退役。③research 降選配：10 檔少一個卡點、0 檔只卡它；refresh 雜訊旗標 23／23 不再升級成整頁旗標〔可逆，§14 #17〕。④段 5 改寫＋OPERATIONS 一句；偏差 #22） | 執行模型 | 見 git log「Step 7.0g」 |
| 7.1 | Wave 1 研究（約 4 週）：**InP 磊晶層說明（O6 提前，A3，排第一件）**、積壓、電力與散熱開題、S1 claim 抽樣、O3、O5 | ○（2026-10-07 已做：InP 磊晶等五份層說明＋個股頁 S4a／S4b〔偏差 #23〕；**積壓：triaged_go 清到 0**（第二批 53 則＋深挖 12 條，全部終局）；**S1：40 則全有裁決**（證實 14、未定 6 帶到期、不適用 13、價格型 7）；**O3** POET v2 敘事（不要）；入圖 [715][719][721][727][728] 與新層、鄰層讀圖 10 份新寫或換版（CDU 層改判 neither）；AI 生醫 B1 結案、延伸的中國創新藥授權鏈 decompose（[726]，上市公司層無候選，ew_0319 等掛牌）；X 帳號四個。****晚段（同日，第二個 session）已做**：①波若威 3163.TWO 第一份敘事 `ib_a35b0492e80432ee`（缺 X）②負錨點兩檔時光機頁→ 個股頁 schema **v1.0 凍結**（brainstorm §15：分得開的是「價」自家三年百分位與「錢」的自家毛利位置，B3 供給緊四件事方向相反——改讀法不改元素；新假說候選待使用者決定登不登記）③電工鋼、冷板、分歧管三層重讀並各登兩個條件 watch（電工鋼加寫「這一層沒有可投資的公司」；冷板的邊緣台廠不在圖上 → directed lead `lead_d9c78bb0aff0b8a882d925766c309410`）④段 5 七檔全部到終局（closure-gate open 7 → closed；5411.T 補供貨邊 → pq2 [729]）⑤走圖第 1 型兩層第一份讀圖（UHP 雷射 volume、6 吋 InP 產線 undecided）⑥FAU 同義節點合併鑄 pq2 [730]；failure log #41、#42。**同晚使用者 go [729][730][731] 已做**：[729] JFE 日本本廠 GOES 供貨邊入圖（`0b1c05e0`）→ 電工鋼層重讀 `sr_761bd010a662901a`（判讀不變）；[730] FAU 同義節點合併（`a5024b04`，備份後 apply，−1 節點、殘留 0）→ FAU 層重讀 `sr_aa0b79ad032a31c4`、波若威與上詮敘事換騎；[731] H13 預先登記（`8d8043df`）後在 H12 事件全集上測 → **削弱**（兩格同時在頂端的先崩較多、也更常翻倍；S4 rubric 不寫「週期頂點的形狀」，`docs/reports/phase7/replay-h13-priced-margin-top.md`）。**續工指標**：①下一批層說明（冷板供給側列舉的 directed lead 起；走圖「下一層 0 條」優先）②`tech:cpo`／`tech:scale_out_cpo` 疑似同義（[730] 另案；第二例出現再提機械面）③有日期：10/11 題材掃描、10/12 台股 9 月月營收與 AEHR 財報後的敘事重寫（wake_brief 等待醒）、10/29 Sivers thesis 複查、11/04 Silex Q3、11 月上旬起 Q3 財報季（7.3 插隊）。O5 的 2×2 在 7.5 填。已知偏差：散熱四份敘事早於該鏈主題等權組（failure log #26）〔研究：強模型在互動 session〕） | 強模型 | |
| 7.2 | 回放：R1 已定價、R3 漏網稽核（機械）；R2 parked 回查、R4 輸家驗屍（研究） | ✅（四份 `docs/reports/phase7/replay-*.md`，產生程式碼逐字附錄、偏差標註齊全。R1：124 格有值 10、PIT 違規 0，H9 兩個子群都「不足」（#12 價格歷史深度）；R3 第一窗：Q3 前四分之一逐檔有 `first_seen` 或「沒有接觸」（#13 名冊新增後 lead 身分不重掃；第二窗在 7.5）；R2：36 則證實 1（CCXI S-4）、H2 的 X2 部分「不足」、與 P3 合併判（#15 park 等的東西出現了卻沒接回；「無法判」「不適用」兩類是回查時加的，報告已註明不影響判讀）；R4：五檔全部「證據不足以判」（#14 反證做成被評公司的供貨邊）） | 執行模型（R1、R3）＋強模型（R2、R4） | 見 git log「Step 7.2」 |
| 7.3 | 中迴路裁決（Q3 財報季；到點插隊）：AXTI、COHR、LITE、SIVE.ST＋新鏈有裁決點的 | ○ | 強模型 | |
| 7.4 | Wave 2 研究（約 4–6 週）：二階瓶頸三個 case、800VDC 回看、依 failure log 選題 | ○ | 強模型 | |
| 7.5 | 檢查點（2026-12-22）：決定紀錄 §10＋假說證據帳＋failure log 排序＋雷達停止條件＋T1 manifest＋R2＋下一期 | ○ | 執行模型＋強模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-10-04-001-research-phase7-research-edge-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1；R2-a、R2-b 已常規 opt-in，見 §0.5）。研究 Step（7.0a 的登記內容、7.1、7.2 的 R2／R4、7.3、7.4）
要強模型在互動 session 做：若你不是強模型，做到研究 Step 就停下交回。撞到 pq2 gate 掛號後接著做下一件，不停在編號上等。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 7.0a | §1「驗證集（附錄 A 的 14 個 case）」 | 登記 **16 個**：附錄 A 的 14 個＋二階 case **O1-U**（InP 上游：銦、晶體生長、出口管制）與 **O6**（光通訊磊晶與 MOCVD 產能）；附錄 A 已 append 這兩列 | §10 寫「二階瓶頸三個 case……三個 case 在 7.0a 已登記，wave 2 只能 append 新 case、不能改這三個的判準」，但附錄 A 只有 P2——不在 7.0a 登記，另兩個就會在 wave 2 才定判準（正是 §10 要防的事後放寬）。附錄 A 本身寫「可 append、不可改」 |
| 2 | 7.0a | §8 R2「抽樣規則先寫進 replay 報告再看結果」 | 抽樣規則與**樣本本身（36 則 lead id）**在 7.0a 就固定進 registration §7.3／附錄 C（分層、不按比例、合併時依層母體加權；層內順序＝lead id 加固定前綴後的 sha256，程式見 registration 附錄 C；排除 P3 的五則）；§8 R2 那一段已補指向 | 比「寫進 replay 報告」更早凍結，7.2 的執行者沒有選樣裁量；EDGAR 237／348 照比例抽會讓樣本幾乎只剩例行申報，所以不按比例、合併時加權 |
| 3 | 7.0a | §1 第 2 項 T0 manifest 的內容清單 | 照清單全做，另加四類：**逐邊證據等級**（534 條，與走圖／心跳同一條路 `_classify_edges`）、S1 框架 40 則、parked×`original_obtained` id 清單、追蹤表 history／paper 名單、舊店三檔與 trade_log 的 sha256；07:06:17Z 先產過一版（沒有逐邊等級），**在任何使用之前刪除重產**（07:09:14Z） | H3／H4 的分組要以 T0 的證據等級為準（之後的升降不得改分組），不凍結就會被之後的更正污染；S1、R2 的框架在看結果之前凍結；§11 第 7 項「另核對」要比對舊店與 trade_log 的 sha256 |
| 4 | 7.0a | §7 第 3 項 S1「每則……寫進截圖假說層」 | registration §6：主張類型封閉四選一（結構／財務／價格／無可否證主張）；**只有結構與財務型寫進截圖假說層**；價格型只記價格路徑；無可否證主張（只點名、情緒、問句）只計數、在 `cases.md` 記裁決「不適用」 | 把沒有可否證陳述的點名寫進假說層，會變成一條永遠叫不醒的等待（INV-2）；ROADMAP 驗收④「40 則各有裁決或到期」照算——「不適用」是預先登記的裁決之一，筆數照印 |
| 5 | 7.0b | §2 第 2 項「`loader/migrate_sourcedoc_json_section.py`（兩處）與 `loader/migrate_identity_cleanup.py` 改用它」 | 三支照做，另把 `engine_c/migrate_fundamental_metrics.py` 自己寫的同一套「同 owner 未過期就不取不放」也換成 `writer_lock.hold` | 那是同一個判斷的第二個 owner（development-flow INTAKE 第 2 問）；L17 三問的「對稱面做了嗎」。行為不變，既有的巢狀測試照綠 |
| 6 | 7.0b | §2 第 3 項「以 max(memo 生成日, last_checked) 對 check_interval_days（或直接用 `is_due`，一個 owner）……另印一行『沒有 lifecycle 的舊 memo N 份』；變異：把 last_checked 拿掉 → 真逾期要被報」 | 取 `is_due` 當唯一 owner：「memo 生成日」那一套整段拿掉；`max(memo 生成日, last_checked)` 只用來印天數。舊 memo 那一行**只在 hook 有話要說時附上**，健康審查「Memo 新鮮度」節每天照列；lifecycle 讀不到時 hook 明講。變異改成「拿掉 last_checked **與** next_check → 要報」（`is_due` 下只拿掉 last_checked，next_check 仍是出口、本來就不該報），另加兩個變異（`check` 不看 `is_due`、拿掉「讀不到要說」） | 一個 owner（`thesis/lifecycle_schedule.py` 自稱「什麼時候該重看的唯一權威」）；舊 memo 那行若單獨每天亮，就是把一個恆亮換成另一個恆亮（L14）；拿掉 memo 日期那套之後，「讀不到」不能靜默（INV-3） |
| 7 | 7.0b | （plan 沒寫） | `DATE_RE` 認得「`**生成日期：** 2026-08-04`」的粗體寫法（L17 當下修，三行） | 先前三份新格式 memo 全退回檔案 mtime；現在只影響「幾天沒核查」的天數呈現 |
| 8 | 7.0b | §2 第 1 項「八欄的範圍欄（或 STEP_RESULT 對應欄）加『暴露它的案例』」 | 八欄沒有「範圍」欄：INTAKE 加一行 `Case:`（範圍判定就在這裡做），收尾在 `Zoom / Review` 重抄；`docs/AGENT_WORKFLOW.md` 同步；不開第九欄 | `tests/test_agent_workflow.py` 數 STEP_RESULT 剛好八欄；新測試釘住 `Case` 行（刪掉它不會讓任何東西變紅，系統只會安靜地回到「想到就做」） |
| 9 | 7.0c | §3 第 2 項「`revenue_ttm`（近四季營收，Engine C 機械歷史表，含口徑與 as_of）」 | 選取 read model **既有**的 `revenue_ttm`（Engine C 快照的 TTM，財報幣別）；填值寫成「近四季，快照 <日期>」 | 同一項要求「先確認兩個值在 read model 裡已有 Datum」——它已在，而且稽核區印的就是這一格；另從機械歷史表組一格會讓同一頁出現兩個營收數（L12、L16）。快照的日期是取數日、不是財報期末，所以字面寫「快照」（INV-6） |
| 10 | 7.0c | §3 第 2 項「`market_cap`（Engine C 快照的市值，含幣別與 as_of）」 | read model 既有的 `market_cap` 是「price × shares、未正規化」——builder 另組一格 `market_cap_settlement`（同一份快照 × 名冊報價單位的換算係數——係數由 sources 從 `identity.currency` 查好注入，builder 是純函式不碰 identity；不做匯率；報價單位未登記 fail closed），placeholder 選它；原格語意不動 | 直接用未正規化那格，IQE.L 會填出「729.5 億」（便士）——真資料核對：換算後 7.3 億 GBP。一格不承載兩種語意（L12） |
| 11 | 7.0c | §3 第 3 項的白話「拿今天的倍數（EV/S，虧損時 P/S）」 | 照 `alpha/three_questions.py::decide_basis` 寫：「有獲利、而且有同一期的淨負債資料時用 EV/S；其餘（虧損、台股、資料不齊）用 P/S」，其餘照 plan 的意思 | P/S 不只在虧損時用（COHR 是因為營業利益資料停在 2024 年中）；自己寫給人讀的事實套同一套追源紀律（L11-2） |
| 12 | 7.0d | §4 第 2 項「登記一筆 `semantic_condition` watch，來源鍵與反證分得開……類別是 `confirm`（`watch_category` 加一類）」 | 照做；**怎麼分**：watch 多一個 `condition_role=confirm`（判斷只住 `engine_b/event_watch.py::is_confirm`），`disproof_ref` 照舊當「指回原文的來源鍵」（＝`source_ref`），不另開 `confirm_ref` 欄位；寫入端另加兩條拒收（同版重複、與反證同一條件） | 用 `disproof_ref` 認「語意 watch」的地方有八處（喚醒、佇列、待辦、liveness、audit、變動偵測）——另開欄位漏改一處，加碼條件就叫不醒、沒人消費（INV-4）；沿用它的代價是名字不貼切，分角色的地方（計數、downside、可開、判定標籤、audit 解析）逐一改並有測試＋變異。交 R2-a 挑戰——**R2-a 判定不構成 L12**：「算不算反證」另開封閉欄位，`disproof_ref` 仍只承載「指回原文的來源鍵」一種語意；代價只是名字不貼切 |
| 13 | 7.0e | §5 第 1 項「每檔輸出 `shared_with_holdings: [{held_ticker, shared_anchors[], shared_layers[]}]`」 | 欄位叫 `shared_bet`：`{rows: [{ticker, company_id, state: "held", shared_anchors[], shared_layers[]}], absence, anchors_absence, anchors_as_of, lines[]}`——「持有」只以 `state` 的值出現；每一句在 `alpha/providers/candidates.py::shared_bet` 組好，候選板與個股頁照印 | 個股頁有兩道既有的欄位名掃描（`tests/test_stock_page_phase3.py`、`tests/test_analyst_view.py`：`held`、`holdings` 不得當欄位名——分析畫面不帶部位欄位），plan 的名字兩個都會被攔；換同義字繞過是 L16 明文禁止的，所以把「持有」放回候選狀態既有的值字彙。缺席有兩種分型（Sheet 讀不到、結構表讀不到；L16 由產生端宣告），所以外面包一層而不是裸 list |
| 14 | 7.0e | §5 第 1 項「materialize 一次載入（同一個 session）……需求錨取自結構表的逐列錨（`query.bottleneck.structure_table`……唯一來源）」 | 讀**同一輪** `--structure-table` 寫下的 `structure_table` artifact（`webapp/materialize.py::bet_structure`；artifact 是 `structure_table()` 輸出照抄），不另開 Neo4j 連線重算；有共用錨時句子標「需求錨取自 <日期> 的結構表逐列錨」；讀不到＝需求錨這半邊 `upstream_unavailable`、層照比 | 「載入結構表」已有三個 owner（`query.bottleneck` CLI、`materialize_structure_table`、graph provider 的快取），再開第四個就是 L16；daily 的 materialize 同一輪先寫結構表（`--structure-table` 排在個股頁與候選板之前），讀它＝同一份、少一次全圖查詢，個股頁與結構表頁的錨保證是同一份 |
| 15 | 7.0f | §6 第 2 項 apply「寫成 lead：`source=web_radar:<theme>`、`source_class=secondary`、tier 4」 | lead 的 tier 只住 triage 的結果（1–4），登記時沒有這一欄：雷達的 lead 在 triage 之前的 pq1 排序本來就是 tier 4（`engine_b/priority.py::rank_lead` 的預設），triage 批次裡另排在所有非雷達 lead 之後（偏差 #16）；triage 讀過內容後給的 tier 照它——雷達搜到公司官網的新聞稿可以是 tier 1 | 登記時寫死 tier 4 會蓋掉 triage 對**文件本身**的判斷：「發現管道是二手」與「文件是二手」是兩件事（L12）。交 R2-b 挑戰 |
| 16 | 7.0f | §6 L11-6 ④「30 則上限下要確認它不擠掉 harvest 的 lead（批次的選取順序照實寫）」 | 查證結果是**會擠**：pending lead 的排序先比 relevance（提到持股排最前）才比首見時間，雷達點名 COHR／SIVE.ST 的 lead 會排到 harvest 的前面，暴量那天最多把 `radar.max_items` 則 harvest 的 lead 擠到隔天。改成 `engine_b/cli.py` 的 triage 批次先把雷達的 lead 移到所有非雷達 lead之後再截上限（兩邊各自原順序不動；note 印「外部雷達 N 則排在最後（進本批 k 則）」——R2-b 指出原本只印截斷前的數）；測試＋變異 | 讓擠掉不可能發生（根除），不是只把它印出來；這是加一道規則——拿掉的方式（雷達不進 triage）會讓它的 lead 永遠沒人分類（INV-4） |
| 17 | 7.0f | §6 第 4 項「`config/themes.txt` 加 `power`（…）與 `cooling`（…）兩個主題」 | 照加，**只有描述與關鍵字、不列核心公司**；會誤報的短字改長寫法：英文 GOES（＝goes）、單獨的 transformer（AI 模型）、CDU（政黨）、SST 不放，中文「冷板」（冷板凳）、「套管」改「水冷板」「變壓器套管」 | 核心公司會餵進 tracked（`routine_config.theme_core_tickers` → materialize 頁數、EDGAR 監看、pq1 relevance），plan 說核心公司由 7.1 的 decompose 再修——不在雷達這一步先擴；主題比對英文不分大小寫、要詞邊界，中文是子字串 |
| 18 | 7.0f | §6 第 2 項「`run_claude` 加一個只給雷達用的選填收集器（收搜尋結果裡的網址）」 | 照做（`observe` 參數＋`SearchCollector`，只收 `tool_use_result.results[*].content[*].url`，摘要字串裡的網址不收），另外：①收集器同時收搜尋結果的**標題**——lead 的標題用它、不用 LLM 寫的；LLM 那句事實放 `refs.radar_fact`（不放 `raw_text`）；②`run_claude` 對**每一步**都把權限被拒判失敗（零工具步驟不可能被拒，行為不變）；③沒有 `radar` 區塊＝關閉 | 探針 A：不放行時 CLI 拒絕 WebSearch、照樣回 `is_error: false`＋空結果——不判失敗，「被擋住」就和「沒東西」同形（L13）；標籤要指得回原文（L18）；新的無人值守能力要明寫打開才跑 |
| 19 | 7.1 | §7 第 6 項「落 `library/private/research_notes/layer_notes/mat_inp_epitaxy.md`」 | 檔名照提議的節點 id：`mat_inp_epiwafer.md`（節點 `mat:inp_epiwafer`，RA [715]） | S4 規格「主鍵是節點或轉換 id」；被供應的東西是磊晶片——L4：節點是換掉交易對手也不變的那個東西；與 `mat:inp_substrate`、`prod:quantum_dot_laser_epiwafer` 的命名一致 |
| 20 | 7.1 | §7 第 6 項 ④「每條主張登記成 watch」 | 牽涉公司賭注的 7 條主張掛在四份敘事的反證上（2455.TW、IQE.L、3081.TWO、4971.TWO 換版）；純屬這一層的 3 條（A6–A8）列在層說明、等 `mat:inp_epiwafer` 入圖後掛層讀圖 | 語意 watch 的來源鍵只認 thesis／reading／brief（failure log #31）；個股頁 plan S4 的程式（層說明 ledger）落地前，層說明沒有自己的來源鍵——不另開臨時來源鍵（那是動 contract） |
| 21 | 7.1 | §0.1 Q2「新的鏈……光通訊＋電力＋散熱」、§13「decompose 同時 open 最多兩個：電力、散熱正好兩個」 | 使用者 2026-10-06 加選第四條鏈 **AI 生醫**（pq2 [723]，稽核用、受理即 resolve），照 §7 第 2 項電力／散熱的七步走；registration 檔尾 append case **B1**（開題日＝該 commit 日）；`config/themes.txt` 加 `aibio`（只放關鍵字，核心公司由 decompose 定）；R3 母體不追加（§14 第 11 項） | decompose 選題是使用者的（AGENTS「新題材由使用者選」）；「同時 open ≤ 2」數的是**未 resolve 的提案編號**（`engine_b/decompose_proposals.py::open_proposals`），[685]／[686]／[723] 都受理即 resolve，所以不超限——§13 那句是寫 plan 當下的計數，不是第二條上限 |
| 22 | 7.0g | §6b 第 2 項「母體外……邊緣沒座位（列「坐哪一層」短檢查……結論＝補座位走 RA，或 v2 敘事寫「不坐任何層」）」；第 3 項「只因 `research` 卡住的檔逐檔列出改前改後的 readiness」 | ①短檢查結論分**三種**（補供貨邊／開發中／不坐任何層或在需求側），②③都寫 v2 敘事；②research 降選配時，refresh 的「需要重看」不再升級成整頁旗標（不保留「只旗標不擋」）；③只卡 research 的檔是 0，改列「research 是卡點之一」的 10 檔改前改後 | ①只有 develops 邊的公司（#22 第二型）不是「不坐任何層」，壓成一種就是 L12；②真實資料這個旗標 23／23 是雜訊（L14-4 恆亮），保留它等於延續退役估值鏈的殘留——可逆（§14 #17）；③照實量，0 就寫 0 |
| 23 | 7.1（個股頁 S4b） | §0.3「不開新 state kind」 | 開了第 9 個 kind `layer_notes`（層說明閱讀頁） | 個股頁 plan 2026-10-07 amendment（使用者選「A＋純文字閱讀頁」）原文就是「APP 新 kind」；§0.3 那句管的是 Phase 7 自己的 Step（7.0d 的加碼條件做成 v2 選填欄、不另開 kind），使用者直接指示的旁支不受它限制（AGENTS「使用者主動指示＝已授權」）。L11-6 ④ 實查：今早 daily 產的 6 個個股頁與新程式重產的 readiness、讀圖面板狀態、`freshness_identity` 6/6 相同 |
| 24 | 7.1（個股頁 S1） | 7.1 的研究項（積壓、電力與散熱、S1 抽樣、O3、O5、InP 磊晶層說明）不含個股頁 plan 的工作；個股頁 S1 凍結 v1.0 的負錨點驗收屬個股頁 plan，原排在「第一波走完、使用者點名 S2」之前另做 | 負錨點兩檔的時光機頁併入 7.1 續工（候選合晶 6182、矽創 8016） | 使用者 2026-10-07「D7選B」（個股頁 plan 待決 D7）：負錨點本身是研究（起漲前的時光機頁），驗的是十三塊能不能分辨「量起來後翻倍」與「量起來後先崩」——對上 brainstorm F51「覆蓋晚於倍率」與 H11；做完 schema 可凍結 v1.0，個股頁 S2 不必等第一波結束。不改 7.1 的定義與驗收 |

---

## 0. 不可越線（違反即 NO_GO）

1. **研究輸出與評估分離。** 評估檔（`docs/reports/phase7/`）只**引用**研究的 id（`sr_*`、`ib_*`、`ew_*`、lead id、pq2 編號），不改任何 ledger；ledger 只 append；
   評估永遠用**開題當時那一版**（paper lane 用第一份 v2 敘事是同一個紀律）。評估檔不是第二個狀態源（AGENTS）：lead、pq2、watch 的狀態只住各自的 registry。
2. **預先登記先於研究。** 7.0a 的 commit 早於 wave 1 的任何新讀圖／敘事的 `created_at`；`registration.md` commit 之後**不改**，更正只能在檔尾 append「更正」段（日期、改什麼、為什麼）。
   新增 case 也是 append（開題日＝append 的 commit 日，不得早於它）。
3. **不排序、不打分、不給尺寸、不設門檻**；「可開」只印不驗收；五題、加碼條件、共用需求錨都不進候選狀態前提（G1、G6）。
4. **四個人工 gate**：入圖、Engine C 判讀寫入、thesis mutation、live；主題等權組成分寫入走 pq2；decompose 選題已由使用者定（§0.5）。
5. **不寫 trade_log、Google Sheet；不動舊 Decision Store；不改 `scripts/record_trade.py`。**
6. **INV-6：** 「當時知道什麼」以 ledger `created_at`、SourceDoc `published_at`、lead `first_seen` 為準；回放每一列標 **discovery lookahead** 與**選樣偏差**；
   LLM 不得站在 2026-06 之前判讀；推不出日期的留 null 並計數。
7. **敘事契約：不升 `record_version`；新增欄位不得改變既有紀錄的 `brief_id`**——真實 ledger 每一行（10-04 共 20 行）重算逐位相同（測試＋真實核對）。
8. **雷達：** LLM 只開 WebSearch；prompt **不放持股、NAV、Sheet 任何欄位、私人路徑**；輸出只經程式驗證寫成 tier-4 secondary lead；**網址必須出自同一次執行的搜尋結果**；
   不喚醒語意 watch；不另外發通知；`llm.executor=none` 時與 triage、預篩一起停。
9. **任何 `python -m <module>` 或 `scripts/*.py` 的行為變更 → sandbox impact review 五步**（ROADMAP 硬約束 10）：7.0d、7.0e（materialize、心跳讀新欄位）、7.0f（daily 新步驟）。
10. **每刪一個測試函式，八欄列出它守什麼、現在由誰守**；`tests/test_heartbeat.py` 釘住的格式改主詞不刪判準；`SNAPSHOT_KEYS` 是封閉清單，加鍵同 commit 改測試。
11. **每個 Step 動手前先答 L11-6 第④問**（如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？去看那一筆），寫進八欄；各 Step 已預填起點。
12. **命名：** 不得新增殭屍 grep 九組的命中（`basket`、`籃子`、`payoff`、`首選`、`target`…）；新名字：`confirm`（加碼條件）、`web_radar`（雷達來源）、
    `shared_with_holdings`（共用需求錨）、`market_cap`／`revenue_ttm`（placeholder）。
13. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 五條 authority separation、六條 invariant 全程適用。

---

## 1. Step 7.0a 預先登記＋T0 凍結（Z0；強模型寫登記內容）

**改哪裡（新檔）：** `docs/reports/phase7/registration.md`、`docs/reports/phase7/cases.md`、`docs/reports/phase7/failure-log.md`、`docs/reports/phase7/cohort-changes.md`；
`library/private/measurement/phase7/T0-<日期>.json`（private；不進 Git）。

**怎麼做：**
1. **`registration.md`（commit 後凍結）**：
   - 十個假說 H1–H10（proposal §3），每個寫：一句假說、今天的證據（含 n）、用哪些 case 測、**殺死條件**（什麼結果出現就判削弱）。H8（point-in-time）寫明是效度條件、不是 edge 假說。
   - 驗證集（附錄 A 的 14 個 case），每個寫：case id、鏈、類型、測哪幾個假說、**開題時已知**（引用 ledger id 與日期）、預期會暴露的 failure mode、支持／削弱的判準、裁決點與日期。
   - 裁決規則：快／中／慢三個迴路的單位與裁決來源（proposal §5.2）；「錯」分**當時已有反例**／**之後才出現**／**未定日**（沿用 `alpha/structure_reading/predictions.py` 的分法）；
     2×2 的判法（結構斷言被證實或推翻 × paper lane 錨點起對**該鏈主題等權組**的超額，proposal §5.3）。
   - failure log 模板（使用者七問，附錄 B）與開發 gate（≥2 個 case 重複、第 3 問答得出來、第 7 問指得到某個迴路的量）。
   - **漏網稽核的母體（R3 用，T0 定、之後只 append 不刪）**：三個主題等權組成分（光通訊現有；電力、散熱在 7.1 定義後 append）＋一份約 40 檔的「AI 基礎設施觀察名單」，
     **今天列、看結果之前列**，涵蓋光通訊、電力設備、散熱、先進封裝／測試、記憶體各數檔（每檔一句為什麼在名單上）。
   - SNS 抽樣規則（S1 用）：先寫抽樣規則（例：帳號計分表 `metrics_first_call_per_symbol` 的 40 檔首次點名、每檔取第一則），**看結果之前寫**。
2. **T0 manifest（唯讀；第一份手動以既有 CLI 與唯讀查詢產生，手動做不下去才寫腳本——L17）**，內容：
   名冊公司 id 清單與 sha256；`onboard-candidates` 清單；lead id 依狀態分組（parked、triaged_go）與 sha256；`crons/harvest_config.json`、`config/signal_sources.json`、
   `config/themes.txt` 的 sha256；assertion id 集合的 sha256、筆數與最大 `updated_at`（唯讀 Cypher）；SourceDoc 筆數；讀圖與敘事 ledger 各檔 sha256 與現行 id；
   `thesis/lifecycle.json` 與各 memo 的 sha256；截圖假說 id 與 sha256；watch registry 的 id、kind、status、expires 與 sha256；候選狀態序列最後一列；主題等權組 id；帳號 tier；
   生成時刻與當天心跳檔名。**產生用的程式碼貼進 `registration.md` 附錄**（scratchpad 會消失，評估要能重算）。
3. **`cases.md`**：每個 case 一段，開題時只放「登記見 registration §x」；之後的研究產出（只寫 id）、裁決（每次 append 一行：日期、文件、結論）、2×2、failure log 條目都 append 在該段下。
4. **`failure-log.md`**：模板＋空表；每條帶 case id 與第幾次出現。
5. **`cohort-changes.md`**：第一筆「T0」；之後每次監看來源或母體變動 append 一筆（日期、改了什麼、為什麼）——**使用者之後加 X 帳號就記在這裡**（新帳號 probation、加入日起量、不回溯），
   7.0f 雷達上線、7.1 新增 `themes.txt` 主題與主題等權組也記在這裡。

**怎麼驗：** `registration.md` 的 commit 時間早於 wave 1 任何新讀圖／敘事的 `created_at`（7.1 結束時核對，讀圖、敘事 ledger）；
T0 manifest 的各計數與當天心跳相同（registry、ledger）；`registration.md` 每個 case 的欄位齊全；manifest 不在 `git ls-files` 裡。

L11-6 ④：最先壞的是「T0 之後才寫的紀錄被算進 T0」——manifest 的生成時刻與各 ledger 最後一行的 `created_at` 對照、寫進八欄。

## 2. Step 7.0b 開發 gate 落地＋兩個當下修（Z1，R1）

1. **開發 gate**：`skills/development-flow/SKILL.md` 八欄的範圍欄（或 STEP_RESULT 對應欄）加「暴露它的案例：case id 與第幾次出現；使用者直接指示的寫『使用者指示』」；
   跑 `python scripts/sync_agent_skills.py`；`tests/test_agent_workflow.py` 若釘住欄位格式，同 commit 改。AGENTS 那一句已在本 plan 的 commit 落地（§0.4 A2），本 Step 只核對測試綠。
2. **巢狀 writer lock（Phase 6 #17，L17 當下修）**：`engine_b/writer_lock.py` 加一個會看巢狀的 context manager——**同 owner 的未過期鎖已在就不 acquire、不 release、不縮短 TTL**；
   `loader/migrate_sourcedoc_json_section.py`（兩處）與 `loader/migrate_identity_cleanup.py` 改用它。測試：外層鎖在內層結束後仍在且 TTL 不變；單獨跑時照常 acquire／release；
   不同 owner 照舊互斥。
3. **thesis 逾期提醒量錯（L17、L14：恆亮＝零鑑別力）**：`crons/thesis_freshness_check.py::check` 目前量 memo 的「生成日期」、不看 `thesis/lifecycle.json`。改成：
   有 lifecycle entry 的 thesis，以 `max(memo 生成日, last_checked)` 對自己的 `check_interval_days`（或直接用 `thesis/lifecycle_schedule.is_due` 那一套，**一個 owner**）；
   沒有任何 lifecycle entry 指向的 memo（例：`cpo_v1_lane_memo.md`）**不算逾期**，另印一行「沒有 lifecycle 的舊 memo N 份」（INV-3：不靜默丟）。
   測試：sivers（memo 08-29、last_checked 09-29、30 天）在 10-04 不逾期、在 10-30 逾期；cpo_v1 不出現在逾期、出現在舊 memo 行；**變異：把 last_checked 拿掉 → 真逾期要被報**。

**怎麼驗：** `pytest` 綠；本機起一個 session 看 SessionStart 不再報兩則假逾期（截圖或輸出貼八欄）。
L11-6 ④：最先壞的是「thesis 真的逾期時提醒不響」——上面的變異測試就是它；另看 `thesis/lifecycle.json` 三筆在 10-04 與 10-30 的判定。

## 3. Step 7.0c 敘事範本：翻倍條件、兩個 placeholder、「已定價」白話、重押換格層引用（Z1，R1）

1. **範本**（`alpha/narrative/contracts.py::BRIEF_FRAME_V2["what_must_be_true"]`）：題目改成「什麼必須為真？**要翻倍需要什麼**（營收、出貨、產能或毛利要到多少、在什麼時候）？
   錯的訊號是什麼？」；`do_not` 改成：「翻倍的起點可以用 `{market_cap}`；條件用營業數字。⚠ 不寫目標價、股價、報酬率；`{price}`、`{own_history_pctile}`、`{cohort_median}`
   仍不得出現在這一格」。`WHAT_MUST_BE_TRUE_FORBIDDEN` **不動**（型別層的禁令照舊）。
2. **placeholder**：`PLACEHOLDERS_V2` 加 `market_cap`（Engine C 快照的市值，含幣別與 as_of）與 `revenue_ttm`（近四季營收，Engine C 機械歷史表，含口徑與 as_of）；
   填值只走既有 authority，讀不到印「（尚無）」並帶理由（同既有 placeholder）。先確認兩個值在 read model 裡已有 `Datum`（沒有就由 builder 從既有取數層組一格，**不在 compose 端算**）。
3. **「已定價」白話**：一份字串 SSOT（放在 `briefing/analyst_view/contracts.py` 的白話別名旁），經 `.meta.json` 送到 APP，首屏「已定價嗎」與稽核區那一題的標題旁各印一次。內容（可微調用字，意思不變）：
   「拿今天的倍數（EV/S，虧損時 P/S）跟它自己過去三年比，落在第幾百分位——回答『市場是不是已經對它重新評價過』。**不是『太貴』，也不是目標價。**
   高百分位代表價格已經假設好消息會持續；不代表不能再漲，代表好消息一斷會跌得比較深。這一格有沒有區分力還在量（Phase 7 R1）。」
4. **重押讀圖時換格層引用（Phase 6 #16，L18）**：`alpha/providers/briefs.py::v2_write_problems` 加一條——新紀錄的 `rides[]` 已指向某節點的現行讀圖時，
   任何一格的 `evidence_refs` 若指向**同一節點**已被取代的讀圖 id → 拒收並列出是哪幾格、該換成哪一個 id（**不自動改寫 session 的文字或引用**）。既有紀錄不動（append-only）。

**怎麼驗：** `pytest` 綠（範本文字、placeholder 填值與缺席、`what_must_be_true` 仍拒 `{price}`、舊讀圖 id 被拒、新讀圖 id 通過）；`python -m alpha research AXTI` 的 packet 印新題目；
真實四檔 ledger 20 行全部照常解析與填值；`python -m webapp materialize AXTI` 後個股頁「已定價嗎」旁有白話（Edge headless，見 §8）。
L11-6 ④：最先壞的是既有四檔敘事的填值——新 placeholder 不在舊紀錄裡，fill 不得因此報錯或改變舊紀錄的輸出（四檔 brief 面板文字改前改後逐字相同）。

## 4. Step 7.0d 敘事「加碼條件」`confirm[]`（Z2，R1＋**R2-a 常規 opt-in**）

**語意（A2）：** 加碼條件＝「這件事發生，代表結構被確認了」（客戶自己的文件點名它、合格狀態走到量產、數字出現在營收裡……）。**觸及只提醒、不是買進訊號、不改候選狀態**；
與反證對稱：寫下即登記 watch、有到期、到期是重問。

1. **契約**（`alpha/narrative/contracts.py`）：`NarrativeConfirm`——`condition`、`check_frequency`、`action_48h`（觸及後 48 小時：研究 session 重寫敘事，換候選狀態或寫明不變）、
   `entities`（至少一個 `co:*`）、`expires`、`source`（前綴規則同反證，指得回原文）。v2 的選填欄 `confirm[]`。
   **id 穩定：** `new_brief_id` 只在 `confirm` 非空時把它納入 id 欄位集合（或等價做法）——**既有 20 行重算逐位相同**（測試讀真實 ledger 的副本；§0 第 7 條）。
2. **登記**（`engine_b/narrative_watches.py::register_brief_watches`）：每條 confirm 登記一筆 `semantic_condition` watch，來源鍵與反證分得開（例：`brief:<brief_id>#c<n>`），
   **類別是 `confirm`**（`engine_b/disproof.py::watch_category` 加一類）——**不得被算成反證**：心跳「反證：在盯／觸及」、downside 面板、圖預測表、`narrative_watches.blocking_for_open` 都不吃它。
   換版／撤回收掉舊版 active 的 confirm watch（同反證）。
3. **觸及與到期**：觸及（互動 session `event_watch judge` 判 yes）→ 候選板那一列與個股頁印「加碼條件已觸及：<條件>（<日期>）——提醒，不是買進訊號」，並進佇列段 `narrative_rewrite`
   （新一版敘事的 `acknowledged_touched` 處置字彙加 `confirmed`）；到期未觸及 → 同樣進 `narrative_rewrite`（「確認事件沒在期限內發生」本身就是資訊）。**不自動改候選狀態**。
4. **消費端**：心跳段 2 加一行「加碼條件：在盯 N｜觸及待處置 M｜到期待重寫 K」（`SNAPSHOT_KEYS` 加鍵）；候選板列與個股頁（7.0e 的第③題旁）列出每條加碼條件與狀態；
   audit 的 Expiry、QueueLiveness 認得這一類（觸及與到期都有 consumer：`narrative_rewrite`）。
5. **sandbox impact review 五步**（OPERATIONS）：materialize 與心跳讀新欄位、registry 多一類。

**怎麼驗：** `pytest` 綠：契約、登記、類別分離（**變異：把 confirm 算成反證 → 紅**）、心跳行、候選板列、id 穩定（真實 ledger 副本 20 行）、到期進 `narrative_rewrite`；
`python -m audit invariants` 綠；真實 registry 上心跳的「反證：在盯 37」改前改後相同（今天沒有 confirm）。
**R2-a `WORK_REQUEST`**：審查者自己重算真實 ledger 的 20 個 `brief_id`、跑類別分離的變異、看觸及／到期兩條路都有 consumer、確認候選狀態不會被自動改。
L11-6 ④：最先壞的是心跳「反證：在盯／觸及」的計數與 `blocking_for_open`——confirm watch 若被當成反證，「可開」的前提會被它卡住。

## 5. Step 7.0e 個股頁首屏五題＋共用需求錨（Z2，R1）

1. **共用需求錨**（A3）：materialize 一次載入（同一個 session，**不在 request path 算**）——每檔的需求錨取自結構表的逐列錨（`query.bottleneck.structure_table` 的 `demand_anchor`／`anchor_basis`，
   **唯一來源**），坐的層與插槽取自 `seat_readings_context`；已持有的 alpha 檔取自 `held_index`（Sheet、alpha、股數 > 0）。每檔輸出
   `shared_with_holdings: [{held_ticker, shared_anchors[], shared_layers[]}]`（實作名 `shared_bet`，偏差 #13；需求錨讀同一輪的結構表 artifact，偏差 #14），依 ticker 字母列、**不打分、不排序、不加權**。缺席分型由產生端宣告：Sheet 讀不到＝持有判定暫停（`upstream_unavailable`）；
   走不到任何需求錨＝照實寫。注入候選板列與個股頁（與 `candidate`／`downside` 面板同一種「來源不在 read model」的注入例外）。
2. **首屏五題**（A1）：`webapp/static/app.js::briefCard` 依序排五題，各題底下放既有句子與燈，**不改任何 `Datum`、不改 ledger**：
   ①這一檔押的是什麼（`our_bet`；`bottleneck`、`position` 收在題下）②押對了夠大嗎（`what_must_be_true` 的翻倍條件、`demand`、「已定價嗎」與白話、「出現在數字裡了嗎」）
   ③錯了怎麼知道、哪天知道（每條反證與它的 watch 狀態、`when`；7.0d 的加碼條件列在旁邊）④會不會死（歸零燈；灰＝沒量到）⑤是不是新賭注（共用需求錨／同一層）；
   候選狀態那一行（狀態、理由、在等的 watch）照舊。**五題的標題與「哪一格放哪一題」的對照只有一份**（放 `briefing/analyst_view/contracts.py`，經 `.meta.json` 給 APP；
   app.js 不維護第二份，L16）。沒有 v2 敘事的頁照舊版面（「還沒寫短評」）。
3. **sandbox impact review**（materialize 多讀結構表與 Sheet 的 held_index）。

**怎麼驗：** `pytest` 綠（compose／meta 的五題對照、`shared_with_holdings` 的組法與缺席分型、request path 四種證明照綠）；**真資料重跑 materialize 後 Edge headless 實點**
（memory「APP 前端用 headless Edge 驗」的做法）：AXTI、COHR、LITE、SIVE.ST 四頁五個標題都在、句子沒少；COHR 與 SIVE.ST 這兩檔已持有的互相列出共用的層或錨（今天兩者都在 CW DFB 這一層）；
候選板列印共用需求錨；首屏沒有任何排序或分數字樣。
L11-6 ④：最先壞的是個股頁 artifact 的 `content_digest` 與 readiness——只改呈現順序與多一個注入欄位；76 頁 digest 的變動要全部歸因到 `shared_with_holdings`（`freshness_identity` 不含它）。

## 6. Step 7.0f 外部雷達（Z2，R1＋**R2-b 常規 opt-in**；sandbox impact review）

1. **先探針（結果寫八欄）**：以 `--tools WebSearch` 跑一次 `claude -p`（其餘旗標同 `crons/llm_step.py::llm_argv`），確認：init 的 `tools` 恰為 `WebSearch` 與 `StructuredOutput`；
   `-p` 模式下 WebSearch 要不要權限、**最窄的放行方式**（`--settings` 的 permissions allow 或其他）；stream 裡搜尋的 tool_use／tool_result 長什麼樣、網址在哪一欄。
   `FORBIDDEN_LLM_FLAGS` 對 triage／預篩**照舊**；雷達有自己的 argv 函式與自己的禁用清單（測試釘住）。
2. **程式**：`crons/llm_step.py` 加 `radar_argv`、能力檢查依步驟參數化（雷達期望 tools＝{WebSearch, StructuredOutput}，其他五欄同既有）、`run_claude` 加一個只給雷達用的選填收集器
   （收搜尋結果裡的網址）；`crons/radar_prompt.md`、`crons/radar_schema.json`（strict）；雷達的 prepare／apply（放 `engine_b/`，例 `engine_b/radar.py`）：
   - prepare：prompt 由程式組——`config/themes.txt` 的主題與關鍵字＋在盯的語意 watch 條件原文與實體（讓它找得到「碰到哪條反證或加碼條件」的新聞）；**不讀 Sheet、positions、NAV、私人路徑**（測試以哨兵證明）。
   - LLM 回：`items[{url, title, publisher, published_at|null, fact（一句、繁中）, entities[], theme（主題 slug 或 new）, relates_to[]（watch id）, why}]`、`no_material_change`。（實作與 tier、triage 順序、主題、收集器的差異見偏差 #15–#18）
   - apply（程式驗證後寫入）：**網址必須出現在同一次執行的搜尋結果裡**（否則拒收、計數）；正規化網址後與 lead registry 去重；`published_at` 讀不懂就 null（不拿抓取日冒充，INV-6）；
     每日上限 `radar.max_items`（預設 5，超過的計數不寫）；實體以名冊寫法解析，解析不到留原字；寫成 lead：`source=web_radar:<theme>`、`source_class=secondary`、tier 4、
     `refs.radar_run`、`refs.relates_to`；收據 `library/private/heartbeat/radar_<日期>.json`（收／拒與理由，INV-3）。**不喚醒語意 watch**（T0 只認一手）。
3. **daily**：`DAILY_STEPS` 在 ① harvest 之後、⑥ triage 批次之前加三步（prepare → LLM 提議 → 保險檢查 → apply），雷達的 lead 第二天（或同一輪，視順序）進 triage；
   `config/daily_routine.json` 加 `radar` 區塊（`enabled`、`max_items`、`timeout_minutes`）；`llm.executor=none` 或 `radar.enabled=false` 都讓它記 skipped（回滾開關）。
4. **主題**：`config/themes.txt` 加 `power`（超高壓變壓器、開關設備、電工鋼／GOES、套管、分接開關、800VDC、固態變壓器、SiC／GaN 功率元件）與 `cooling`（液冷、冷板、CDU、快接頭、浸沒式）兩個主題
   ——使用者 Q2 選的鏈；7.1 的 decompose 再修。記進 `cohort-changes.md`。
5. **心跳段 3** 一行：「外部雷達：新 N｜重複 a｜拒收 b（網址不在搜尋結果 c、超過上限 d）｜提到在盯的條件 K｜沒有重要變化／沒跑（理由）」（`SNAPSHOT_KEYS` 加鍵）。
6. **八週試驗與停止條件**（寫進 ROADMAP Phase 7 列）：上線日起 56 天；7.5 檢查點數「雷達 lead 中，triaged_go 且追到一手文件或入圖、而且沒有別的管道更早登記同一個網址或同一事件」的筆數——
   **0 就退役**（`radar.enabled=false`，程式留或刪在檢查點決定），非 0 就列出那幾筆、由使用者決定續不續（registry）。
7. **sandbox impact review 五步**（OPERATIONS 新節）＋ARCHITECTURE §4.1 的表（分類／語意預篩／**雷達**）同 commit 更新；說清楚它不是 last30days（硬約束 8 的理由是「輸出沒有 provenance 契約」，雷達的契約是網址必須出自搜尋結果）。

**怎麼驗：** `pytest` 綠：argv 逐項（tools 恰為 WebSearch、禁用旗標不在）、能力檢查各種不符、網址不在搜尋結果被拒、去重、上限、prompt 不含持股（哨兵）、`executor=none` 與 `enabled=false` 都 skipped、
心跳行；`python crons/daily_task.py --dry-run` 列出新步驟且時限加總仍在 `execution_time_limit_minutes` 內；**第一次真實排程跑完後**看心跳那一行與收據（ROADMAP 驗收寫「已交付、第一輪 <日期>」）。
**R2-b `WORK_REQUEST`**：審查者看探針紀錄、argv、能力檢查、網址驗證、prompt 組法（不得碰 Sheet）、回滾開關。
L11-6 ④：最先壞的是 daily 的保險檢查（LLM 步驟前後的檔案指紋）與 triage 批次上限——雷達的 lead 進 ⑥，30 則上限下要確認它不擠掉 harvest 的 lead（批次的選取順序照實寫）。

## 6b. Step 7.0g 研究預算分層：深度在層、廣度在檔（Z3，R1；A4；2026-10-07 使用者定案 Q1 A、Q2 A、Q4 A）

**為什麼是現在：** 段 5 照現行規則（closure-gate 回 exit 1 不得收工）會繼續替大型股寫淺敘事；剩下 26 檔裡 20 檔非邊緣。研究 session 在本 Step 交付前**不跑段 5**，先做不經閉環的研究（AI 生醫拆層、層說明）。

1. **7.0g-1 資料檢查跟著全部個股頁（Q2 A；先於撤非邊緣敘事）**
   - 母體＝全部已 materialize 的個股頁（`ArtifactStore.read_all`），**不跟閉環母體走**；每個檢查印「比對 N 檔／無法比 M 檔」並逐檔列出無法比的——跳過不得安靜（INV-3）。
   - **營收量級（新）**：個股頁印出的近四季營收（值＋幣別標籤）對基期觀測的年營收（各自幣別），以同一個換匯來源換成美元，比值超出 [0.5, 2.0] 就列出（口徑差異不會差到兩倍，量級錯會）。
   - **股數（既有，補覆蓋）**：從閉環列改成全部個股頁；沒有財報股數可比的逐檔列，港股另標「快照可能只含 H 股」（名冊沒有記 A 股那一邊，A＋H 判不出來——照實印，不猜）。
   - **同日多筆生效（既有）**：照舊全庫。
   - **驗收**：三個原始案例回放命中 3／3——#20（6680.HK：快照 241,144,516 對財報 1,360,000,000）、#23（UMC 修法前印的「2,507 億 USD」對 20-F 基期）、#27（SOI.PA `segment_revenue_share@2026-03-31` 兩筆生效）；測試以原始數字寫死，拿掉檢查即紅；closure-gate 每輪印三行與覆蓋數。
2. **7.0g-2 閉環母體收窄（Q1 A；#22 選項②）**
   - 母體＝已持有 ∪ 有 thesis（lifecycle；使用者明示）∪（邊緣或量不到 ∩ 供給側有座位）∪ 現行候選（敘事狀態缺 X／等回落／可開）。
     邊緣讀候選板 artifact（materialize 時對全部個股頁算一次，補上還沒有敘事那幾檔的 `edge`；closure-gate 不打外部）；座位讀結構表 artifact 的 `supplies_to` 列（`depends_on`／`constrained_by` 是買方那一側，不算供給側座位；結構表收下游關係、走不到需求錨的列照收，`develops`／`invests_in` 不收）。
   - 母體外**逐檔列名**，分兩類：**非倍率**（非邊緣、沒持有、沒有 thesis：附市值、覆蓋、判定日；每次 materialize 重算，翻回邊緣就回母體）；
     **邊緣沒座位**（列「坐哪一層」短檢查；有 v2 敘事且 90 天內的算查過，超過 90 天或從沒查過就回到可推進——每個等待都有到期，INV-2）。
   - `NEXT_PICK_RULE` 刪「有同期 EPS 共識」「forward EPS 為正」兩條（Phase 0 殭屍：理由引用已刪的 bridge.py）；其餘順序不動。
   - **驗收**：#22 預先寫的量「未到終局裡沒有出口的檔數」17 → 0（閉環佇列）；母體外兩類逐檔列名、各附理由；之後 7.5 量「非倍率檔在本 Step 之後新寫的敘事版本數＝0」（敘事 ledger）。
3. **7.0g-3 `research` 面板降選配（Q4 A）**：`CORE_PANELS` 拿掉 `research`、`OPTIONAL_PANELS` 加入；內容照印、只是不再決定 readiness。契約升版、全量 materialize、重啟長駐 serve。
   **驗收**：只因 `research` 卡住的檔逐檔列出改前改後的 readiness（閉環佇列）；其他面板的狀態逐位相同。
4. **7.0g-4 段 5 分流寫進 skill**：非倍率不寫敘事（它的文件進層說明當在位者或客戶證據）；邊緣沒座位做一次短檢查（結論＝補座位走 RA，或 v2 敘事寫「不坐任何層」）；
   廣度短敘事的範圍（一份年報＋packet；先宣告單位；三項必查：致股東報告書 #32、表頭個體或合併 #35、同義節點 #36）；層深讀的入口（走圖第 1／2 型、下一層 0 條、有敘事的缺 X 指向這一層——只印有無不印次數、讀圖過期、層主張的 watch 醒、使用者點名）。
   `python scripts/sync_agent_skills.py`。

**不做：** 不動 tracked 名單（它也餵 EDGAR 監看與 pq1 relevance）；不寫非邊緣檔的「不要」敘事來充當研究判斷（L12）；「已定價」不當分流條件（不設門檻，AGENTS）；火力比例（T2 約 20%、T3 約 45–50%、T4 約 25%）只是初值、不寫進程式。
**L11-6 ④：** 最先壞的是「供給側座位」的判定——只有 `develops` 邊的公司（開發中、還沒供貨；#22 第二型 5 檔）與只有 `invests_in` 邊的公司會被當成沒座位而進短檢查；去看 5411.T（只有投資電工鋼合資廠的邊）與 6481.T、XFAB.PA、XPEV（2026-10-07 實查：0 條邊），短檢查的結論要能把它們分成「補供貨邊」「開發中」「不坐任何層」三種，而不是一律寫成「不坐任何層」。

## 7. Step 7.1 Wave 1 研究（強模型；約 4 週；寫 ledger 前取 writer lock）

收據：`docs/reports/phase7/cases.md`（各 case 段 append）＋每個研究 session 的收尾摘要（含等 go 的編號）。

1. **積壓**（7.0a 之後就可以開始）：research-drain 清 23 則 triaged_go 到終局（`python -m engine_b.cli drain` 的順序；終局：入圖、park 附 trace_status、not_pursued 附理由）；
   掃題材至少一次（`skills/theme-scan`）；Sivers 的 thesis 複查照 lifecycle 的 `next_check`（2026-10-29）做（7.0b 修好提醒後，以 lifecycle 為準）。每一則撞到系統的缺點就寫 failure log。
2. **電力、散熱開題**（Q2；選題已定）：每條鏈 ①鑄 manual pq2 只為稽核、受理即 resolve ②`skills/system-decompose` 由上而下拆（電力：超高壓變壓器 → 上游；800VDC 回看 09-03 擱置的五則；
   散熱：液冷 → 冷板／CDU／快接頭）③層中心選源（客戶 filing 的供應商段、產業報告、規格書；韓國 DART 等海外來源撞到才依旁支做）→ RA → pq2 `ra_admission`
   ④**該鏈的主題等權組在第一份該鏈敘事之前定義**（spec → `todo add-theme-cohort` → 使用者 go → `complete-theme-cohort`；成分是判斷，附理由與日期——**前瞻定義，不是回溯**；決定紀錄 §6.7）
   ⑤薄層寫層讀圖（v3，兩半引用）⑥有邊緣公司坐在薄層上才寫 v2 敘事（含翻倍條件、`disproof[]`、`confirm[]`、候選狀態）；坐的都是巨頭或私人公司 → 寫明「這一層沒有可投資的公司」
   （讀圖結論或 Abstention），那正是 P2／P1 的預期類型之一 ⑦case 段 append 產出 id 與 failure log。
3. **S1 claim 抽樣**：照 7.0a 寫好的抽樣規則取 40 則首次點名，每則：主張原文（lead 原文）→ 主張類型（結構／財務／價格）→ 最早的一手證實或推翻文件與 `published_at` →
   比我們其他管道第一次接觸早或晚幾天 → 點名到一手之間價格走了多少（Engine C／既有取價）→ 裁決（證實／推翻／未定）。寫進截圖假說層（`python -m engine_b.hypotheses add`／`verify`）；
   未定的帶到期（INV-2）。**細則照 registration §6**（偏差 #4：只有結構與財務型主張寫進截圖假說層；無可否證主張只計數、裁決「不適用」記在 `cases.md`）。結果摘要寫進 S1 段——它就是計分表那一格 `hypothesis_hit_rate` 的手動版，**不改計分表程式**。
4. **O3 POET**：寫 v2 敘事（候選狀態照研究結論；預期「不要」，理由：供應商給認股權證換訂單＝不是瓶頸，ARCHITECTURE §6 四維度）＋case 段。
   **O5 COHR 外部光源第二來源**：從 thesis mutation 歷史與當時的圖寫 case 段（斷言、被推翻的文件與日期、之後的價格），填 2×2。
5. **使用者加 X 帳號**（Q4，隨時）：照 `config/signal_sources.json` 的規則以 probation 加入、`crons/harvest_config.json` 的 handles 同步，記進 `cohort-changes.md`。

6. **InP 磊晶層說明（A3，2026-10-06；排第一件）**：照個股頁 plan S4 的四段規格寫——①物理與變體（InP 磊晶對 CW DFB／EML／PD 各是什麼、MOCVD 與 6 吋基板、自製 vs 外購）②各家變體與階段附證據等級（聯亞、全新、英特磊、IQE；Coherent／Lumentum／MACOM 內製）③客戶為什麼選這家的變體、什麼會讓它被換掉，附客戶端出處（IDM 法說、10-K 供應商段、論文）④每條主張登記成 watch。落 `library/private/research_notes/layer_notes/mat_inp_epitaxy.md`（S4 ledger 落地後搬）；新層節點與重掛邊（聯亞、IQE 的磊晶邊）寫 RA → pq2 `ra_admission`；同時是 O6 的 case 段。
   **撞到拿不到的文件就照 source-trace 的要求格式列給使用者（有問題型附結果表、探索型附上限），鑄 `source_trace_review`，不 park。**
   怎麼驗：讀完的報告（問了什麼／答到／沒答到／相反／沒問到卻讀到的）；registry 裡因它改變候選狀態的筆數；它的主張變成 watch 的條數。

**怎麼驗：** ①光通訊以外 **≥2 條鏈各有現行讀圖、每份 ≥1 條登記反證**（讀圖、registry）；②本波新寫的每份敘事都有候選狀態、`rides[]`、翻倍條件那一句（持有或可開的另有 `confirm[]`）（敘事）；
③23 則 triaged_go 各到終局（registry）；④S1 的 40 則各有裁決或到期（registry）；⑤新鏈的主題等權組在該鏈第一份敘事之前落地（registry：pq2 編號與 ledger 時間）；
⑥每個開了的 case 段有產出 id 與至少一筆裁決或「尚未到裁決點」（追蹤表）。**不數「可開」幾檔。**
L11-6 ④：最先壞的是「研究先於登記」——每份新讀圖／敘事的 `created_at` 晚於 7.0a 的 commit；其次是主題等權組晚於第一份敘事（paper lane 的組超額會變成回溯）。

## 8. Step 7.2 回放（R1、R3 執行模型；R2、R4 強模型；可與 7.1 交錯）

報告：`docs/reports/phase7/replay-<名稱>.md`，**每一列標 discovery lookahead 與選樣偏差**，產生用的程式碼貼在附錄（scratchpad 會消失）。

- **R1 已定價回放（機械，H9）**：母體＝history lane 22 ∪ 光通訊主題等權組 15（去重）中有自家歷史的檔；時點＝入圖日，與入圖日前 30／90／180 天；
  以**三題同一個純函式**（`alpha/three_questions.py` 與 `engine_c/three_question_inputs.py` 的取數規則；as-of 規則 `shared/as_of.py`）在 scratchpad 算當時的自家三年百分位，
  對照之後到今天的報酬與對主題等權組的超額；呈現分組表（高／中／低百分位 × 之後報酬），**不算 p 值、不下「有效／無效」以外的結論**，n 照印。
  ⚠ 三題的 as-of 視角今天沒接（Phase 3 #15）：純函式加 as-of 篩過的輸入算得出來就照做；算不出來就寫 failure log、照實寫「未量」，**不在本 Step 改產品程式**。
- **R3 漏網稽核（機械，H1、F6；每季一次，第一次在 7.2、第二次在 7.5）**：母體＝7.0a 預先列的名單；該季對主題等權組漲最多的前四分之一，逐檔查 lead registry 的 `first_seen`、
  來源、最後狀態與「為什麼沒進研究」（registry 查得到的照抄；查不到寫「系統沒有接觸」）。含 HBM／記憶體那幾檔（「刻意不做」的代價）。
- **R2 parked 回查（研究，H2、F4、F5）**：從 353 則 `original_obtained` 的 parked 依管道分層抽 30–40 則（抽樣規則先寫進 replay 報告再看結果；**偏差 #2：規則與 36 則樣本已在 7.0a 固定於 registration §7.3／附錄 C，replay 報告照抄**），每則：之後有沒有一手證實（文件與日期）、
  證實前價格走了多少、當初 park 的理由現在看站不站得住。
- **R4 history lane 輸家驗屍（研究）**：AEVA、MP、LYC.AX、6594.T、6680.HK——入圖時的圖投影說了什麼（`project_assertions_as_of`）、之後的一手文件說了什麼：結構讀錯了，還是只是價格路徑。

**怎麼驗：** R1 每檔有各時點的百分位與之後報酬，或寫明缺哪一項（追蹤表）；R3 每檔有 `first_seen` 或「沒有接觸」（registry）；R2 每則有證實日或「未證實」（registry）；
R4 每檔一段結論（追蹤表）。每份報告的偏差標註齊全。
L11-6 ④：最先壞的是 R1 的 as-of——拿今天的財報數字算過去的百分位就是 lookahead；核對每個時點用的財報 `filed` 日都早於那個時點。

## 9. Step 7.3 中迴路裁決（強模型；Q3 財報季，到點插隊）

對象：AXTI、COHR、LITE（11 月上旬，日期以各家公告為準）、SIVE.ST（2026-11-26）；新鏈若已有敘事且裁決點落在窗內也做。每一檔：
1. 讀一手財報（10-Q／8-K／季報）→ 逐條裁決「必須為真」（含翻倍條件）、每條反證（`python -m engine_b.event_watch semantic-queue` → `judge`）、每條加碼條件；
2. 寫新一版敘事（`acknowledged_touched` 逐條處置）或在 case 段寫明不換版理由；
3. case 段 append 裁決（日期、文件、結論，「錯」分當時已有／之後才出現）；
4. 填 2×2：結構斷言被證實或推翻 × paper lane 錨點起對主題等權組的超額。COHR、LITE 的敘事是「不要（非邊緣）」——它們的裁決是**層的證據**（需求、產能、內製比例），不是股價。

**怎麼驗：** 四檔各有財報後新版或不換版理由（敘事）；窗內到期的 watch 全部有處置（registry）；2×2 四列（追蹤表）。
L11-6 ④：最先壞的是「財報後改寫舊判斷」——新版是新紀錄，2×2 用的是開題當時那一版；核對 case 段引用的 `ib_*` 是 7.0a 登記時的現行版。

## 10. Step 7.4 Wave 2 研究（強模型；約 4–6 週）

- **二階瓶頸三個 case**（proposal §8）：P2（變壓器上游：電工鋼、套管、分接開關、測試產能）、O1 延伸（InP 上游：銦、晶體生長、出口管制）、光通訊磊晶與 MOCVD 產能。
  每個回答三問：①現有圖與走圖有沒有自己把上游限制報出來？②卡住研究的是證據還是表示法？③上游那一層有沒有比第一層更不擁擠、而且可投資的公司？
- **P3 800VDC 回看**：09-03 擱置的五則（VRM、BBU／超級電容、整流與 busway、GaN／SiC、DC/DC power shelf），當初 park 的理由今天站不站得住、世界動了什麼。
- **依 failure log 選題**：wave 1 撞到最多次的缺口相關的 case 優先；補還沒覆蓋到的類型。
- C1 若在 wave 1 找到邊緣公司：寫敘事、用台股月營收跑中迴路。

**怎麼驗：** 三個二階 case 各有結論：「表示法擋住」／「證據擋住」／「上游沒有可投資標的」，各指得出讀圖、敘事或 Abstention 紀錄（讀圖、敘事）；
本波新敘事同 7.1 ②；failure log 每條帶 case id（追蹤表）。
L11-6 ④：最先壞的是「二階」的定義被事後放寬——三個 case 在 7.0a 已登記，wave 2 只能 append 新 case、不能改這三個的判準。

## 11. Step 7.5 檢查點（2026-12-22；之後每季；completion gate 照 historical-failure-matrix §9 八項＋第九項）

1. **決定紀錄 §10 四條**：讀圖 ledger 份數、「可開」序列（恆 0 或恆非 0？）、09-22 之後新鑄 pq2 的來源比例、單供應商節點比例——印值與解讀。
2. **H1–H10 證據帳**：每個假說一列——支持的 case、削弱的 case、n、狀態（支持／削弱／不足）；**不合成分數**。
3. **failure log 依重複次數排序**；列出這一期提過、做過的開發項（2026-10-07 A5 起，過 gate 的開發項——≥2 個 case、第 3 問、第 7 問——**隨時**以五欄 amendment 提，不等檢查點；擋住研究的排在研究前）。
4. **雷達停止條件**（§6 第 6 項）的結論；**A4（成交紀錄加階段）**使用者是否已開始用起始／加碼節奏下單——是的話提出來。
5. **T1 manifest**（同 T0 的內容；與 T0 的差異逐類列出、每一類歸因到 `cohort-changes.md` 的事件）；第二次漏網稽核（R3）。
6. 報告：`docs/reports/2026-12-22-phase7-checkpoint.md`（日期用實跑日），附「下一期要決定的問題」（§14 種子＋執行中新增）。
7. **completion gate**：`pytest -q` 全綠（測試檔數差＝新增－退役，函式層級拿掉的寫去向）；`python -m audit invariants` 綠；心跳逐行歸因（與 7.0a 當天比）；無新 dual authority
   （共用需求錨只有一個組法、加碼條件只有一條登記路徑、雷達只有一個寫入口）；無 silent drop（雷達拒收、R1 未量、R3 沒接觸都計數）；point-in-time（§0 第 6 條）；
   lifecycle 可達（本期鑄的 pq2 與 watch 都在終局或心跳逐筆列出）；executable protection（7.0b–7.0f 的變異測試）；驗收數的是 §12 的層。
   **另核對：** 舊店三個 `*.db` 與 `library/trades/trade_log.jsonl` 的 sha256＝7.0a；`registration.md` 自 commit 後只有檔尾 append；`git ls-files library/private` 為空。

### 檢查點 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 7 第一期檢查點）
Target: master 最新 commit；docs/reports/phase7/（registration、cases、failure-log、cohort-changes、replay-*）、docs/reports/…-phase7-checkpoint.md；
        docs/plans/2026-10-04-001-research-phase7-research-edge-plan.md（§0.4 amendment、§0.6 偏差）
Claimed acceptance: 檢查點 completion gate 全過；ROADMAP Phase 7 驗收①–⑧成立（或依報告照實寫的未成立項）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（7.0a commit 起）
  2. 預先登記：registration.md 的 git log 只有一次建立加檔尾 append；它的 commit 時間早於 wave 1 每一份新讀圖／敘事的 created_at（自己列出比對）
  3. 研究與評估分離：cases.md 引用的 ib_*／sr_* 都存在、2×2 用的是登記當時的現行版；評估檔沒有改任何 ledger（ledger 前綴的 sha 與 T0 manifest 一致，只多了新行）
  4. 敘事契約：自己重算 7.0a 當天 ledger 的每一行 brief_id，逐位相同；confirm watch 不被算成反證（心跳反證計數、downside 面板、預測表）
  5. 雷達：radar_*.json 收據裡每一筆寫入的 url 都在同一次的搜尋結果裡；prompt 組法不碰 Sheet；停止條件的計數自己從 lead registry 重算
  6. 回放：R1 每個時點用的財報 filed 日早於該時點；每份 replay 報告都有選樣偏差與 discovery lookahead 標註
  7. 假說證據帳：每個假說列出的 case 都在 cases.md 找得到對應的裁決；沒有任何一行是「幾檔通過某個 filter」
  8. 舊店三檔、trade_log 的 sha256 不變；Sheet 沒有程式寫入；git ls-files library/private 為空
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger、不跑任何 --apply
```

### 檢查點之後：停

R2 回 GO 後：本 plan status 改 `completed`、`docs/plans/README.md` 對照表本列改 completed（Phase 7 本身在 ROADMAP 仍是 ▶ 持續型，列上註「第一期檢查點 ✅」），commit、push。
然後 **`AWAITING_HUMAN`**：HUMAN SUMMARY 的「下一步」印三件事：①檢查點報告的「下一期要決定的問題」；②過 gate 的開發項與它們的五欄 amendment；
③`docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令（下一期的 plan 照它寫；是 Phase 7 第二期還是另開系統層的 Phase，由使用者決定）。

---

## 12. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ① 新鏈讀圖 | 光通訊以外 ≥2 條鏈各有現行讀圖，每份 ≥1 條登記反證 | 讀圖、registry |
| ② 新敘事 | 每份有候選狀態、`rides[]`、翻倍條件；持有或可開的另有 `confirm[]` | 敘事 |
| ③ 預先登記與凍結 | 登記 commit 早於 wave 1 的新讀圖／敘事；T0 manifest 與當天心跳一致 | 讀圖、敘事、registry |
| ④ S1 | 40 則 claim 各有裁決或到期 | registry |
| ⑤ 中迴路 | Q3 後四檔敘事各有新版或不換版理由；窗內到期 watch 全部處置 | 敘事、registry |
| ⑥ case 與 2×2 | 每個開了的 case 有產出 id 與裁決或「尚未到裁決點」；2×2 各列 | 追蹤表 |
| ⑦ 雷達 | 上線、第一輪收據、八週停止條件的結論 | registry、機制 |
| ⑧ 檢查點 | H1–H10 每個有證據列與 n | 追蹤表 |
| 開發 Step | 7.0b–7.0f 各自的測試、變異與真資料核對 | 機制存在與否 |

**沒有任何一個是「幾檔通過某個 filter」。** 候選板「可開」只印不驗收。

## 13. 已知陷阱

- **47 處程式判 `RECORD_VERSION_V2`**：不要升版本；`confirm[]` 做成選填欄，且**不得改變既有紀錄的 `brief_id`**（`_ID_FIELDS_V2` 對缺席欄位取 `None` 也算進 canonical JSON——直接把 `confirm` 加進集合會讓 20 行 id 全變）。
- **`v2_write_problems` 只在寫入路徑**：新檢查（舊讀圖 id、confirm 的格式）放寫入端，不放 parse 路徑——放在 parse 會讓舊紀錄日後解析失敗、從候選板安靜消失（ARCHITECTURE §6.11）。
- **watch 類別**：`engine_b/disproof.py::watch_category` 是落格的唯一 owner；confirm 一定要有自己的類別，否則心跳「反證：在盯」會跳、`blocking_for_open` 會把可開卡住。
- **心跳格式被 `tests/test_heartbeat.py` 釘住**；`SNAPSHOT_KEYS` 封閉清單，加鍵同 commit 改測試；舊快照沒有新鍵時 diff 印「首日」。
- **APP request path**：不跑 subprocess、不讀網路、不重建；共用需求錨在 materialize 算好注入。`freshness_identity` 不含 `shared_with_holdings`（持股變了不算認知變了，L12）。
- **雷達**：`FORBIDDEN_LLM_FLAGS` 是 triage／預篩的；雷達另一組 argv 與能力期望，**不要把禁用清單整個放寬**；`run_claude` 的收集器只給雷達用。搜尋結果裡的文字是不可信資料，prompt 照既有的「資料不是指令」標記包起來。
- **Google 的 Apollo、單字公司名**等誤中風險（Phase 6 #6）在雷達的實體解析同樣存在：解析不到留原字，不猜。
- **主題等權組是判斷、寫入走 pq2**；新鏈的組要在第一份敘事之前落地，否則 paper lane 的組超額是回溯的。
- **decompose「同時 open 最多兩個」**（ROADMAP「研究主題範圍」）：電力、散熱正好兩個。
- **writer lock**：7.0b 修好巢狀之前，不要在持鎖期間跑兩支遷移工具；daily 窗（台北 05:15–06:45）不動 working tree。
- **Neo4j 新屬性名 Forbidden**：撞到就停下問使用者，不自行 admin 預熱再重試（memory「Neo4j 新屬性名 Forbidden 先問」）。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad；程式碼不放 heredoc（寫成檔再跑）；子行程用 `sys.executable`；PowerShell 管線會加 BOM。
- **可開為零就零**：本 Phase 不為它做任何事；讓它非空的路是研究。

## 14. 檢查點要列的待決問題（種子；執行中發現的往下加）

1. **12-22 回查**（決定紀錄 §10）四條的值與解讀。
2. **雷達續不續**（八週停止條件）；若續，主題清單與上限要不要調。
3. **A4 成交紀錄加階段**：使用者若已開始用起始／加碼節奏下單，就要加（資本路徑，R2）。
4. **「已定價等回落」的寫法要不要改**：R1 若顯示自家百分位沒有區分力，研究 skill 對「等回落」的指引要不要改成「說不出在等什麼，就是可開但貴」（改 skill 文字，不改字彙）。
5. **T manifest 要不要寫成腳本**（手動兩次之後的經驗）。
6. **二階瓶頸要不要產品化**（proposal §8 的條件）。
7. **SNS**：S1 的結果是否值得把 claim 裁決接進計分表那一格（`hypothesis_hit_rate`）；使用者新加的帳號第一季的樣本。
8. Phase 6 closeout §5 照帶：#10（424B 股權／債）、#11（同 doc_id 兩份抽取檔）、#12（BD／Hyundai Mobis 的 origin）、#13（策展摘錄的方括號）、#14（lead 代號字串對不上名冊）、#15（wipeout 灰燈 inputs）。
9. Phase 5 closeout §5 照帶：#5（history lane 退役）、#6（主題等權組換版斷點）、#9（預測表納入 thesis 反證觸及）、#10（計分表逐則記組是否已定義）；#8 FRA:2DG 回填（使用者動作）。
10. 三題的 as-of 視角（Phase 3 #15）：R1 若因此量不到，它就是第一個有案例的開發項。
11. **AI 生醫的漏網稽核母體**（2026-10-06，偏差 #21）：R3 只涵蓋 AI 基礎設施；要不要替 AI 生醫另定一個前瞻母體（類別、檔數、起量窗），定了就照 §5.3 從下一個窗口起量、不回溯。
12. **火力比例初值**（A4；2026-10-07）：廣度短敘事約 20%、層深讀約 45–50%、個股深挖約 25%、已定價借鏡 ≤5%——等 10-29 與 11 月季報第一批層主張有裁決後在檢查點調；深度研究自己的錯誤率還沒量（INV-5）。
13. **廣度短敘事抽樣複核**：隨機抽首版敘事，數事實錯的份數（今天的 3／7 是層說明挑過的樣本，不外推）。
14. **層主張的預期裁決日**：InP 磊晶 A6–A8、板式熱交換器 H1–H3 共 6 條還在等待 registry 外（`layer_note:` 來源鍵等個股頁 plan S4 程式），檢查點列出各條預期裁決日。
    → **2026-10-07 個股頁 S4a 解**：6 條登記 `ew_0310`–`ew_0315`（`layer_note:` 來源鍵），到期都是 2026-12-31；檢查點照 registry 印觸及／到期，不再手列。
15. **用邊緣門檻分配注意力的代價**：R1 的 2 倍贏家裡 MU、000660.KS、300308.SZ、GFS、LITE 今天都算非邊緣——用 R1 現成資料量一次「當時非邊緣的翻倍格有幾格」。
16. **APP 清單分組仍只看 readiness**（7.0g 非阻擋債，L16 的形狀）：closure-gate 說「母體外·非倍率」的頁，APP 照舊分在「還沒做」——要讓 materialize 的 overview 也帶母體分類（它要讀候選板、結構表、lifecycle），或 APP 改讀 closure 的分類。
17. **research 的「需要重看」不再升級成整頁旗標**（7.0g-3 的可逆選擇）：真實資料 23／23 是雜訊（18 筆 digest 變化無法解釋、5 筆目標價小動）；若之後 refresh 長出有鑑別力的訊號（例如反證觸及），改成「只旗標不擋」只要一行。

---

## 附錄 A：驗證集（proposal §6.2；7.0a 照此登記，可 append、不可改）

| # | case | 鏈 | 類型 | 主要測 | 裁決點 |
|---|---|---|---|---|---|
| O1 | AXTI／InP 基板 | 光通訊 | 結構對、判斷可能錯 | H1、H7、H9、H10 | Q3 財報（11 月上旬） |
| O2 | SIVE.ST／CW DFB 與 ELS | 光通訊 | 結構漂亮、獲利攫取弱 | H3 | Q3 2026-11-26；年底 ELS |
| O3 | POET | 光通訊 | 公司小但不是關鍵供應商 | H10 反例 | 既有證據 |
| O4 | AAOI | 光通訊 | 供應商自報強、客戶證據弱（加 ATM 稀釋） | H3 | Q3 財報 |
| O5 | COHR 外部光源第二來源 | 光通訊 | 圖的斷言被推翻（09-19） | H4 | 已發生 |
| S1 | X 帳號 40 則首次點名的 claim 裁決 | 跨鏈 | SNS 早點名但沒被證實 | H6 | 抽樣當下＋到期 |
| P1 | 345／765 kV 超高壓變壓器 | 電力 | 瓶頸明顯、市場高度共識 | H1 對 H9 | 下一季訂單／產能公告 |
| P2 | 變壓器上游：電工鋼、套管、分接開關、測試產能 | 電力 | 二階瓶頸；可能沒有可投資的公司 | H5 | 擴產公告、交期 |
| P3 | 800VDC 功率半導體與電源層（09-03 擱置五則） | 電力 | park 後世界動了什麼 | H2 | 合作 → 量產訂單 |
| C1 | 液冷（冷板、CDU、快接頭）台股供應商 | 散熱 | 圖上不顯眼、數字可能加速 | H1、H10 | 每月 10 日月營收 |
| X1 | 已定價回放（R1） | 跨鏈 | — | H9 | 一次性 |
| X2 | parked 回查（R2） | 跨鏈 | 系統的保守有多貴 | H2 | 一次性 |
| X3 | 漏網稽核（R3，含 HBM 刻意不做） | 跨鏈 | 系統完全沒找到 | H1 | 每季 |
| X4 | history lane 輸家驗屍（R4） | 跨鏈 | 圖看錯／股價跌 | H1、H3 | 一次性 |
| O1-U | InP 上游：銦、晶體生長、出口管制（7.0a append，偏差 #1） | 光通訊 | 二階瓶頸 | H5 | Wave 2（7.4） |
| O6 | 光通訊磊晶與 MOCVD 產能（7.0a append，偏差 #1） | 光通訊 | 二階瓶頸 | H5 | Wave 2（7.4） |

## 附錄 B：模板

**case 段（`cases.md`）：** 登記（見 registration §x）｜研究產出（只寫 id：讀圖、敘事、RA、watch、截圖假說、pq2）｜裁決（每次一行：日期、文件、結論、「錯」的種類）｜
2×2（結構斷言 × 對該鏈主題等權組的超額）｜failure log 條目。

**failure log 條目（`failure-log.md`）：** ①哪個 case 暴露 ②第幾次出現（列出其他 case）③為什麼現有系統＋人工研究不夠 ④增加的是資訊還是便利 ⑤有沒有新增 authority surface
⑥怎麼驗收 ⑦做完後哪個研究 outcome 會變好、怎麼知道。**過 gate＝至少兩個 case、③答得出來、⑦指得到某個迴路的量**（L17 的當下修除外）。

## 附錄 C：決策流程（A1；個股頁首屏與研究 session 共用）

1. 候選板先分組（系統機械做）：可開／缺 X／等回落／不要／已持有。「不要」多半是大型股，在圖上是證據不是賭注；「缺 X」「等回落」是「還沒」，各綁一個會叫醒人的 watch。
   **只需要對「可開」那幾檔做決定**；要人決定的時刻只有四種：某檔變成可開、加碼條件被觸及、反證被觸及、使用者自己想重看——前三種心跳會印。
2. 每一檔可開的，問五題（系統給證據，答案是人的）：①押的是什麼（一句話：押這一層的量，還是押某個客戶插槽換不掉）②押對了夠大嗎（要翻倍，營收／出貨要到多少、什麼時候，窗口內做不做得到）
   ③錯了怎麼知道、哪天知道（反證與裁決日）④會不會死（歸零燈；灰＝沒量到）⑤是不是新賭注（共用需求錨／同一層算同一筆）。答不出來就不買。
3. 部位節奏是使用者自己的紀律，**系統不給尺寸，只守 5% 單筆上限**：起始部位小且每檔一樣大（排不出先後）；加碼只在結構確認事件之後（不因股價漲跌）；出場只在反證被觸及（48 小時內處置）。
   「判斷錯了值多少」＝放進去的那一筆；「賭對了值多少」＝翻倍條件成不成立——兩個都不需要目標價。
4. 「已定價」是脈絡不是否決：它該做的是讓第②題寫得更嚴（價格已經假設了什麼、翻倍還需要那之外的什麼）；它有沒有區分力由 R1 量。
