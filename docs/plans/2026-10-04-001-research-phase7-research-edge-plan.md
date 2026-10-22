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

**A6｜名冊外的公司也能判邊緣：研究時的機械入口（failure log #43；2026-10-07 使用者「可以 做掉」，10-08 交付）**

| 欄 | 內容 |
|---|---|
| 原 plan | 邊緣判定（市值 ≤ 100 億美元**且**分析師 ≤ 12 家，`config/alpha_screen.json`）只在 materialize 時對名冊內的檔算（`alpha.providers.edge.edge_states` → `screen_inputs`：名冊＋Engine C）；名冊外的代號回 `unmeasurable`。research-drain 段 5 只寫「邊緣判定或座位讀不到的，一律留在母體」，研究走到名冊外的公司沒有入口 |
| 新觀察 | failure log #43，2 次：C1 冷板讀圖與 directed lead 寫「邊緣大小的台廠雙鴻」——目測市值；套系統口徑雙鴻分析師 16 家、不是邊緣。O5 FAU 讀圖寫「邊緣大小的是 Browave」——同樣目測。同晚 G1 的日東紡、台玻、建榮也只能目測。研究要找的正是名冊外的新邊緣候選，目測只看得到市值、看不到覆蓋厚薄 |
| proposed change | 唯讀入口 `python -m alpha edge <代號…>`（`alpha.providers.edge.adhoc_edge_states`）：同一個純函式 `alpha/edge.py::edge_state`、同一份門檻；名冊＋Engine C 有值的欄位照用（候選板同一條路），缺的欄位才用 yfinance 補——市值＝價格×股數、報價單位照 `identity/currency.py` 換成結算幣別再換美元（不用 yfinance 的 marketCap 欄：小單位報價時單位不保證），家數＝`numberOfAnalystOpinions`；**每個欄位標來源**；取數失敗（含限流）照實落「量不到」並寫理由，家數缺值不當 0。research-drain 段 5 加一行：名冊外的公司用這個命令判、不目測，讀圖／敘事／層說明寫「邊緣」時附判定與來源 |
| why | 使用者 2026-10-07「可以 做掉」；A5 的判準：它擋研究——研究走到名冊外的公司時只能目測，目測已經錯了一次（雙鴻） |
| impact | `alpha/providers/edge.py`（新函式，materialize 走的 `edge_states` 不動）、`alpha/cli.py`（`edge` 子命令）、`tests/test_alpha_edge_adhoc.py`（5 條：三個原始案例、GBp 小單位、未登記報價單位 fail closed、名冊值優先只補缺欄、取數失敗照實寫）、`skills/research-drain/SKILL.md` 一行；不動 contract、不進 request path、不寫任何 authority。驗收：真資料回放 3324.TWO → 非邊緣（16 家）、3110.T → 邊緣（42.3 億美元、9 家）、3163.TWO → 量不到（家數取不到）＝3／3；變異 3 個全紅（拿掉小單位換算、yfinance 覆蓋名冊值、家數缺值當 0）；全套 3754 passed／1 skipped。之後的量：讀圖、敘事、層說明裡「邊緣」字樣附得出判定的比例（10-07 是 0／3） |

**A7–A12｜10-21 計畫盤點的六條修正（2026-10-21 使用者「A7-A12 go」；盤點：research-drain 10-21 唯讀子代理 `phase7_plan`）**

| # | 原 plan | 新觀察 | proposed change | why | impact |
|---|---|---|---|---|---|
| A7 | 進度表 7.1 狀態格「○（2026-10-07 已做：…」連同逐日紀錄與「續工指標」七條，約 43 KB | 7.1 驗收①③④已達成；續工七條有五條是過時事實（例：「等 [765]」，[765] 10-19 已結案）；7.1 永遠 ○，`/phase-run` 永遠停在 7.1 | 7.1 改 ✅ 並寫收尾句；逐日紀錄**逐字**搬到 `docs/reports/phase7/research-log.md`（append-only）；新增 7.1b「持續研究」一列，佇列以 registry 命令為準，手寫的只放命令列不出來的、每行指一個 registry id | AGENTS「現況數字會過期……做成會自己出現的計數器」；L14 常駐計數器 | 進度表兩列、新檔一份；驗收：搬出去的與原文逐字相同（sha256）、手寫佇列引用已結案 pq2 的行數＝0 |
| A8 | 驗收⑤「Q3 財報後四檔敘事」；§9 對象 AXTI、COHR、LITE、SIVE.ST | LITE 敘事 10-20 撤回；窗內有裁決點的敘事遠多於四檔；名單不先凍結就會事後挑樣本 | ⑤改成「Q3 財報季窗（10-21～11-30）裁決點落在窗內的現行敘事，名單 10-21 凍結」；`cases.md` 新增 Q3W 段（28 份、排除 2 份附理由、裁決點來源） | 對象已不存在；凍結才不會變成事後挑樣本 | ROADMAP ⑤、進度表 7.3、§9 四處、§12 ⑤；`cases.md` Q3W；failure log #34 過 gate（盤點再見 4 筆） |
| A9 | 驗收②「新敘事每份有候選狀態、押的讀圖與翻倍條件，持有或可開的另有加碼條件」 | 17 份沒有 rides 全是短檢查判「不要」；COHR 判不要但持有、12 版沒有 confirm[]；SIVE.ST 14 版沒有 confirm[]；AXTI、SIVE.ST 沒有翻倍句 | ②拆開兩種語意：不坐任何層的寫明理由、不另立 rides；持有或可開且不是「不要」的另有加碼條件；持有但判不要的非倍率持股，加碼與反證住它的 thesis。研究待辦：SIVE.ST 補 confirm[] 與翻倍句、AXTI 補翻倍句，併進 Q3 換版 | 同一欄位承載兩種語意（L12） | ROADMAP ②；研究 skill 一句 |
| A10 | ROADMAP「八週試驗：上線 56 天後…為 0 就退役」；§6 第 6 項、§11 第 4 項 | 第 56 天＝11-29（報告 11-30），早於 12-22；10-09～10-12 沒跑；試驗中儀器改了 5 次、題材 1 次（cohort-changes 10-21 三筆）；計數 2 或 3（Tower–Semtech 邊界） | 11-30 出「第 56 天報告」逐筆 lead id＋更早管道 lead id；按版本分段計數（v0 10-05～10-07、v1 10-08～10-19 加市場層 `f0854048`、v1.1 10-20、v1.2 10-21、v2 10-22 起；生醫題材 7→6 也從 10-22 起；沒跑的天數照印，§6 第 6 項 A10 段）；**原停止條件照原定義算**（預先登記的殺死條件，看過計數後不改：全期為 0 就退役），新講法只用來報告；「更早登記」＝別的管道有同一網址或同一事件的 lead、不論當時 triage 結果；Tower–Semtech 另列「雷達救回被誤判 no-go 的一手」；**此定義是看過計數之後才提**，兩種數字都照印；續不續由使用者 12-22 決定 | 停止條件日期在檢查點之前，而且試驗中換了儀器 | ROADMAP 一句、§6 第 6 項、§11 第 4 項 |
| A11 | §7 七步（主題組在第一份敘事之前）；registration 的 B1、G1 前例；§1 第 5 項 cohort-changes 每次變動 append | [831] Bloom 已 go、21 個 pq1 題目但沒有 case；PCB 高速材料鏈已有讀圖與敘事但沒有 case；cohort-changes 10-08 後沒再記 | registration 追加 E1（Bloom SOFC 現場發電），必須早於第一份 SOFC 讀圖；PCB 鏈事後登記、不進 H1 判讀線；SOFC 主題組 spec 在第一份 SOFC 敘事前鑄 pq2；§14 加一題（R3 母體要不要加現場發電與 PCB 材料）；cohort-changes 補登 | 不登記，新鏈結果就變成回溯評估（§7 L11-6 ④） | registration、cohort-changes 追加；§14 一題 |
| A12 | failure log 檔頭「過 gate 的在 7.5 檢查點以五欄 amendment 提」 | 與 A5「隨時提」不一致；標「7.5 提」的 15 條囤著；7.0g 量測「非倍率新敘事版本數＝0」實際 20 版／12 檔；paper lane 混著撤回的 41 列 | 檔頭改成與 A5 一致；15 條（＋#34、#90）合成一份批次 PLAN_PROPOSAL（`docs/plans/2026-10-21-003-dev-phase7-batch2-plan.md`，排序只看擋不擋研究）；7.5 報告照實寫 20 版、10-20 起重量；paper lane 依 current_state 分組列印 | A5 的意思是擋研究的開發排在研究前；量測不照實記＝未量測的機制享有默認信任（INV-5） | failure log 檔頭；新 plan 一份；7.5 報告寫法 |

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
| 7.1 | Wave 1 研究（約 4 週）：**InP 磊晶層說明（O6 提前，A3，排第一件）**、積壓、電力與散熱開題、S1 claim 抽樣、O3、O5 | ✅（2026-10-21 收尾〔amendment A7〕：驗收①③④達成——①散熱 5 層、高速 PCB 材料 4 層（CCL、HVLP 銅箔、Low-Dk 布、石英布）的現行讀圖每份 ≥1 條登記反證（電力 7 層中乾式變壓器 `sr_cfed15e6eb35a726` 反證 0）、③T0 的 23 則 triaged_go 全到終局（parked 19、applied 4）、④S1 40 則全有裁決或到期（證實 14、未定 6 帶到期、不適用 13、價格型 7）；②持股 SIVE.ST 現行敘事 `ib_81fcd7087c1afe4c`（缺 X）沒有 `confirm[]`，COHR `ib_4233a575e88d7756`（不要）見 A9；⑤散熱鏈主題組晚於該鏈第一份敘事（failure log #26，已知偏差；同條普查另有載板 ATS.VI；PCB 鏈 [801] 落地 10-18T05:14Z 晚於 TTMI 短檢查與台玻第一份敘事、聯茂第一份敘事早於 v3 [832] 落地——#26 的 D6 只擋已鑄號組提案裡的成員）；⑥O1 段沒 append AXTI 自己的敘事與讀圖版本，7.3 AXTI 裁決時補。逐日紀錄逐字搬到 `docs/reports/phase7/research-log.md`；之後的研究看 7.1b） | 強模型 | 見 git log「plan 7.1」「research(phase7)」 |
| 7.1b | 持續研究（Wave 1 之後到 7.5）：照 §7 的研究規則接著做——新 lead 與積壓清到終局、層深讀、新鏈的主題等權組先於該鏈第一份敘事、registry 叫醒的反證／加碼條件／敘事重寫逐條處置、撞到系統缺點寫 failure log；7.3 到點插隊、7.4 可交錯 | ○（**續工指標**：佇列以命令為準——`python -m engine_b.cli drain --limit 50`（段 0–1 計數器、段 5 閉環、pq1 lead）、`python -m engine_b.event_watch semantic-queue`（醒來待檢的反證與加碼條件，照組 judge——重訊叫醒的同公司同類一組一次（批次二 E2））、`python -m engine_b.todo list`（待你決定與等事件）、`python -m query.graph_walk`（段 4 走圖九型）。手寫（四條命令列不出來的；每項指一個 registry id，結案即刪）：**無**（2026-10-22 清空：原 ①`hy_0022` 已登記 `ew_1452`〔date 10-30，醒來進假設對照〕；同一天另把 8 筆沒有等待指回的 active 假說各登記一筆到期前一週的 date watch〔ew_1444–ew_1451〕；之後新的手寫項一律先登記成 watch 或 pq2，不寫在這裡——短版 ⑤ 數得到的才算接住）。已知照報不做：走圖第 9 型 19 對已於 10-17 給終局（`docs/reports/phase7/graph-walk-terminals-2026-10-17.md`）。每個研究 session 收尾在 `docs/reports/phase7/research-log.md` 檔尾追加一段，不寫回本格〔研究：強模型在互動 session〕） | 強模型 | |
| 7.2 | 回放：R1 已定價、R3 漏網稽核（機械）；R2 parked 回查、R4 輸家驗屍（研究） | ✅（四份 `docs/reports/phase7/replay-*.md`，產生程式碼逐字附錄、偏差標註齊全。R1：124 格有值 10、PIT 違規 0，H9 兩個子群都「不足」（#12 價格歷史深度）；R3 第一窗：Q3 前四分之一逐檔有 `first_seen` 或「沒有接觸」（#13 名冊新增後 lead 身分不重掃；第二窗在 7.5）；R2：36 則證實 1（CCXI S-4）、H2 的 X2 部分「不足」、與 P3 合併判（#15 park 等的東西出現了卻沒接回；「無法判」「不適用」兩類是回查時加的，報告已註明不影響判讀）；R4：五檔全部「證據不足以判」（#14 反證做成被評公司的供貨邊）） | 執行模型（R1、R3）＋強模型（R2、R4） | 見 git log「Step 7.2」 |
| 7.3 | 中迴路裁決（Q3 財報季 2026-10-21～11-30；到點插隊）：A8 凍結名單 28 份（`docs/reports/phase7/cases.md` Q3W 段）＋非倍率公司的財報當層證據（COHR、LITE） | ○ | 強模型 | |
| 7.4 | Wave 2 研究（約 4–6 週）：二階瓶頸三個 case、800VDC 回看、依 failure log 選題 | ○（2026-10-17 提前做（使用者「wave2有需要也可以先做」）：**三個二階 case 結論**寫進 cases.md——O1-U (i) 都沒擋／(ii) 沒有（上游折進第一層、銦金屬不在管制清單；InP 基板讀圖換版 `sr_9aa50cb6a36e4822`）、O6 (i) 證據／(ii) 沒有（AIXTRON 非邊緣、比第一層更擁擠）、P2 (i) 證據／(ii) 有（華明；CTC 層的 KSH、Precision Wires 由美國海關提單找到 → 入圖包 [774]）→ **H5 達削弱條件**（2／3 個 (ii)＝沒有；正式裁決在 7.5）；**P3 回看** 0/5 證實（設計選用不算 H2 證實——判準定一次）、五則改停成等具名揭露（failure log #69）；SST 一手只有設計採用、不是薄層（停放）。還沒做：依 failure log 選題、KSH／Precision Wires 入圖後的 CTC 層讀圖與兩份敘事、絕緣層讀圖 | 強模型 | |
| 7.5 | 檢查點（2026-12-22）：決定紀錄 §10＋假說證據帳＋failure log 排序＋雷達停止條件＋T1 manifest＋R2＋下一期 | ○ | 執行模型＋強模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-10-04-001-research-phase7-research-edge-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1；R2-a、R2-b 已常規 opt-in，見 §0.5）。研究 Step（7.0a 的登記內容、7.1、7.2 的 R2／R4、7.3、7.4）
要強模型在互動 session 做：若你不是強模型，做到研究 Step 就停下交回。撞到 pq2 gate 掛號後接著做下一件，不停在編號上等。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

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

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 2. Step 7.0b 開發 gate 落地＋兩個當下修（Z1，R1）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 3. Step 7.0c 敘事範本：翻倍條件、兩個 placeholder、「已定價」白話、重押換格層引用（Z1，R1）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 4. Step 7.0d 敘事「加碼條件」`confirm[]`（Z2，R1＋**R2-a 常規 opt-in**）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 5. Step 7.0e 個股頁首屏五題＋共用需求錨（Z2，R1）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 6. Step 7.0f 外部雷達（Z2，R1＋**R2-b 常規 opt-in**；sandbox impact review）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 6b. Step 7.0g 研究預算分層：深度在層、廣度在檔（Z3，R1；A4；2026-10-07 使用者定案 Q1 A、Q2 A、Q4 A）

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

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

（已完成；全文逐字移到 [`docs/archive/phase7-plan-closed-sections-2026-10-22.md`](../archive/phase7-plan-closed-sections-2026-10-22.md)——2026-10-22 輕量整理，內容一字未改）

## 9. Step 7.3 中迴路裁決（強模型；Q3 財報季，到點插隊）

對象（A8，2026-10-21）：裁決點落在 Q3 財報季窗（2026-10-21～11-30）內的現行敘事——持股＋缺 X＋已定價等回落；名單 2026-10-21 凍結、寫進 `docs/reports/phase7/cases.md` 的 Q3W 段（28 份；規則、排除理由、裁決點日期與來源在該段），凍結後新寫或改判的敘事不追加。非倍率公司（含 LITE、COHR 的層面）的財報只當層的證據，寫進讀圖換版或 case 段。每一檔：
1. 讀一手財報（10-Q／8-K／季報）→ 逐條裁決「必須為真」（含翻倍條件）、每條反證（`python -m engine_b.event_watch semantic-queue` → `judge`）、每條加碼條件；
2. 寫新一版敘事（`acknowledged_touched` 逐條處置）或在 case 段寫明不換版理由；
3. case 段 append 裁決（日期、文件、結論，「錯」分當時已有／之後才出現）；
4. 填 2×2：結構斷言被證實或推翻 × paper lane 錨點起對主題等權組的超額（registration §3.3：到量測日沒有裁決寫「尚未到裁決點」、組未定義寫「組未定義」，都不填格）。非倍率公司（COHR 持股、名單內 MP；LITE 2026-10-20 已撤回敘事）的財報是**層的證據**（需求、產能、內製比例），寫進讀圖換版或 case 段，不是股價。

**怎麼驗：** Q3W 凍結名單每份各有財報後新版或不換版理由（敘事；case 段逐檔一行）；非倍率公司的財報各有讀圖換版或 case 段一行（讀圖）；Q3W 段列出的已觸發、窗內到期與窗內叫醒的 watch，以及窗內新觸發的，全部有處置收據（registry：consumed／reactivate／`expiry_resolution`）；2×2 名單每份一列（追蹤表）。
L11-6 ④：最先壞的是「財報後改寫舊判斷」——新版是新紀錄，2×2 用的是開題當時那一版；核對 case 段引用的 `ib_*`：7.0a 已登記的 case（O1、O2 等）用登記時的現行版，其餘用 Q3W 段凍結的那一版。

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
4. **雷達**：讀 11-30 的「第 56 天報告」（§6 第 6 項 A10）——原停止條件照原定義的結論、分版計數；非 0 時續不續由使用者在本檢查點決定；**A4（成交紀錄加階段）**使用者是否已開始用起始／加碼節奏下單——是的話提出來。
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
| ② 新敘事 | 每份有候選狀態、`rides[]`（沒押的寫明短檢查結論，不另立）、翻倍條件（判「不要」的寫出為什麼翻不了倍就算數，2026-10-21）；持有或可開、且狀態不是「不要」的另有 `confirm[]`；持有但判「不要」的非倍率持股，加碼與反證住它的 thesis（A9） | 敘事（thesis 那一半：等待 registry 的反證 watch） |
| ③ 預先登記與凍結 | 登記 commit 早於 wave 1 的新讀圖／敘事；T0 manifest 與當天心跳一致 | 讀圖、敘事、registry |
| ④ S1 | 40 則 claim 各有裁決或到期 | registry |
| ⑤ 中迴路 | Q3 財報季窗（10-21～11-30）的凍結名單每份有財報後新版或不換版理由；非倍率公司的財報寫進讀圖換版或 case 段；窗內到期與已觸發 watch 全部處置 | 敘事、讀圖、registry |
| ⑥ case 與 2×2 | 每個開了的 case 有產出 id 與裁決或「尚未到裁決點」；2×2 各列 | 追蹤表 |
| ⑦ 雷達 | 上線、第一輪收據、11-30「第 56 天報告」（分版計數、逐筆 lead id）、八週停止條件的結論 | registry、機制 |
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
2. **雷達續不續**（八週停止條件；依 11-30「第 56 天報告」的分版計數，A10）；若續，主題清單、層輪替與上限要不要調。
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
18. **R3 母體要不要加 AI 載板材料**（2026-10-07，case G1）：R3 的觀察名單有載板廠（10-05 追加 6 檔）但沒有它們的材料（玻纖布、ABF 膜、銅箔）；要加就照 §5.3 從下一個窗口起量、不回溯。
19. **名冊 note「留待研究判斷」的重複節點對會從走圖第 9 型安靜消失**（2026-10-15 收尾掃描，failure log #60②）：目前 1 對——
    `tech:dram`／`tech:dram_technology`；與 HBM 不主動 onboarding（[701]–[703]，同一天到期）一起重看：判了就在名冊寫決定（併走 pq2、
    不併照寫理由），不判就照帶下一季。機械上要分得開「刻意不併」與「留待」，得有結構化欄位——隨 #60 的五欄 amendment 一起提。
20. **R3 漏網稽核母體要不要加現場發電與高速 PCB 材料**（2026-10-21，amendment A11；registration case E1、G2）：§5.2 的觀察名單在現場發電只有 Bloom（#18），沒有它的供應層（熱箱、電解質片、連接板、感測元件、超級電容）也沒有替代路（燃氣渦輪、往復式引擎——只有 GEV、ENR.DE 當共識對照）；高速 PCB 材料（CCL、HVLP 銅箔、Low-Dk 與石英布、極薄載體銅箔）一檔都沒有（10-05 追加的 6 檔是載板廠；銅箔與玻纖布跟第 18 題的載板材料重疊，一起決定）。要加就照 §5.3 從下一個窗口起量、不回溯；⚠ 這兩類的名字在本 Phase 研究時已看過價格（PCB 鏈敘事引用自家三年百分位與組中位數），成分要用類別規則選（主業、名冊解析得到、有價格歷史），每列標選樣偏差（registration §0.1），不得拿「漲過」當入選理由。順帶：光互連組 v2（`tc_cee164691d22da1e`，10-18）補的 4 檔（光環 3234.TWO、環宇 4991.TWO、波若威 3163.TWO、Ligent 9856.HK）也不在 R3 母體（新易盛已是 §5.2 #2），同一題一起問。

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
