# AGENTS.md 逐段 triage（2026-09-22，供使用者審）

> **這張表回答：現行 `AGENTS.md` 的每一段去了哪裡、為什麼。** 草稿已於 2026-09-22 apply 為 `AGENTS.md`（換版前逐字副本：`docs/archive/agents-pre-graph-first-2026-09-22.md`）。
> 判準只有一條（G10）：**這句話指名了函數、表、門檻值或 Phase 嗎？** 指名了就是手段，不住 AGENTS。
> 查證命令是唯一例外。Lesson 依 G11：判準句留、敘述改、事發搬、真衝突才刪且附理由。
>
> **處置字彙：** 留｜留·壓縮｜改寫｜搬 ARCHITECTURE｜搬 archive｜搬 incidents｜搬 schema｜**刪（附理由）**。
> apply 時另做三件事：①現行 AGENTS.md 全文逐字封存為 `docs/archive/agents-pre-graph-first-2026-09-22.md`；
> ②新建 `docs/lessons-incidents.md` 收全部 L1–L19 的事發與實作落點（逐字搬，不改寫）；
> ③搬去 ARCHITECTURE 的句子在同一個 commit 補進去，不留「見 ARCHITECTURE」卻找不到的斷鏈。

| 現行 AGENTS.md | 值 | 草稿 | 值 |
|---|---|---|---|
| 字元 | 36,385 | 字元 | 14,623（實測，原檔的 40%） |
| 行 | 807 | 行 | 292 |
| Lessons 占比 | 36% | Lessons 占比 | 18%（只剩判準句） |

## 檔頭與導覽

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 1 | 「本檔回答一個問題…只放會約束行為的規則」 | 改寫 | 加准入判準一句：指名函數／表／門檻／Phase 的是手段，不住這裡；查證命令例外 | G10；原檔有判別法但只套在憲法節 |
| 2 | 定位一句話、「系統不給部位尺寸」 | 留 | | 目標與邊界 |
| 3 | 目標一句話（2026-09-16）＋指向 09-16 決定紀錄 | 改寫 | 目標句留；新增「方向（2026-09-22）：圖是中心…圖到人之間沒有任何一段算分數」；指向改為 09-22 決定紀錄與 brainstorms/README | 09-16 檔已封存，仍有效的 D 已抄進本檔 |
| 4 | 「本檔的角色與另外五份」表＋判準 | 留·壓縮 | 表留；加 `docs/lessons-incidents.md` 與 archive 指向 | 結構性 |
| 5 | 「⚠ 本檔每個 session 完整載入…」 | 留 | 併進檔頭 | 它就是 G10 的成本論證 |

## 工作語言

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 6 | 整節（五個 bullet＋判準） | 留·壓縮 | 五 bullet 壓成一段，內容一字不少 | 行為規範 |

## 憲法

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 7 | 「不要把四引擎架構當憲法」 | 留·壓縮 | 一句 | 邊界 |
| 8 | 五條 authority 表 | 改寫 | A3 的說明加「讀圖、敘事」三字 | 新方向的研究判斷物件要有歸屬 |
| 9 | 五條分離規則 | 改寫 | 第 3 條「`ResearchContext` 與 `DecisionContext` 必須分開」→「研究判斷與決策紀錄必須是兩個物件」 | 指名了 class（手段）；原則不變 |
| 10 | 判別問法「換掉 Neo4j 之後仍成立」 | 留 | | 這正是 G10 的雛形 |
| 11 | 六條 hard invariant 表＋`python -m audit invariants` | 留 | | 查證命令例外 |
| 12 | 四個 gate＋「go 只授權自己的 action type」 | 留 | | 核心邊界 |
| 13 | mechanical／judgment 判準（含「今天有兩處這樣畫：Engine C 按 verifiability 分；圖的 metadata 回填只放行 published_at／retrieved_at」） | 改寫 | 判準留；「今天有兩處這樣畫」那句搬 ARCHITECTURE §8.1 | 那句是現況清單，會腐壞 |
| 14 | 「放行與收緊必須同時發生（L15）…補償控制清單見 ARCHITECTURE §8.1」 | 留·壓縮 | | 邊界 |
| 15 | 「不得用 ingest 日期冒充 published_at」＋查證 | 留 | | INV-6 推論 |

## 授權與決策

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 16 | 「所有真正需要決策的事只有一個編號空間…狀態存本機 `library/leads/todo_pool.json`」 | 改寫 | 規則留；檔案路徑句搬 ARCHITECTURE | 路徑是手段 |
| 17 | 「授權載體唯一（2026-08-30）…一律先以 `todo add` 鑄成 manual 型」 | 改寫 | 規則留；`todo add` 命令名去掉（OPERATIONS 有） | 命令是手段 |
| 18 | 「go 的語意＝推進到下一個人工 gate」全段 | 留·壓縮 | | 授權語意 |
| 19 | 「使用者主動指示＝已授權」 | 留 | | 授權語意 |
| 20 | 「常規授權類別（2026-09-09）…SSOT 為 `config/standing_authorization.json`（`engine_b/standing_authorization.py` 是唯一 loader…）consumer 是 `engine_b.todo standing-go`…`decision_review` 的 bounded gap research、`source_trace_review` 的派回 pq1」 | 改寫 | 規則、永不列入清單、判準一句留；三個檔名／命令與兩個現行類別搬 ARCHITECTURE | 指名了三個手段；類別清單會隨 config 變 |
| 21 | 「系統開發項不走 pq2，唯一載體是 ROADMAP」＋判準＋理由（L14） | 改寫 | 留；加一句 G10：驗收數字只准數圖／讀圖／敘事／registry／追蹤表 | 這裡是驗收規則最該住的位置 |
| 22 | 「等你決定與等事件必須分離…`config/decision_blockers.json` 的 `resolution_mode`…`pending --until/--trigger`」 | 改寫 | 原則留；config 與旗標名搬 ARCHITECTURE；**新增**「所有等待住同一個 registry、有到期、到期是重問不是丟；語意條件由 AI 層標旗不判定」 | G7；指名手段 |
| 23 | 「人工判讀不等於外部事件（2026-08-15）」 | 留·壓縮 | | 分類判準 |
| 24 | 「建議只由 pool ground truth 導出（2026-08-30）」三條＋事發（weekly 對八個編號建議 drop，source_cleared 0/8） | 改寫 | 三條留；事發搬 incidents | 事發是歷史 |
| 25 | 「收尾建議摘要是義務」 | 留 | | 呈現義務 |
| 26 | 「待核准內容的呈現契約全文住 daily-brief SKILL…不可退讓的一條」 | 留·壓縮 | 併進上一條 | 邊界 |

## 資本與風控

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 27 | Numeric SSOT 三個 config＋硬擋只有兩項＋live_override | 留 | | SSOT 指向是 authority 位置，不是手段 |
| 28 | 「alpha 格只觀測不設目標（D1）…查證 `python -c …['sleeves']['alpha']`」 | 留·壓縮 | 查證命令搬 ARCHITECTURE（那是「落地了沒」的查證，落地後就腐壞） | 指向 Phase 交付狀態 |
| 29 | 「`live_supported_range` 已隨 U7 移除但硬擋仍在——`store.record_live_choice` 對每一筆…」 | 改寫 | 「系統給的建議區間已移除，煞車仍在：三碼硬擋、七天時效、fail closed」；函式名搬 ARCHITECTURE | 指名函數與 U7 |
| 30 | 共同可投資現金池 | 留·壓縮 | | 邊界 |
| 31 | 兩個槓桿指標不得混用 | 留·壓縮 | | 呈現邊界（beta 凍結但仍有效） |
| 32 | Capital Authority（Sheet 兩種 record、readonly scope、未動用額度） | 留·壓縮 | | 邊界 |
| 33 | 部位真相是 Sheet（D14）＋`scripts/record_trade.py` | 改寫 | 腳本名去掉（OPERATIONS 有） | 手段 |
| 34 | 曝險邊界（CASH 列、unlevered 降級、issuer_loads partial、Engine A 上游不混 ownership、frozen decision 不回寫） | 留·壓縮 | 「Engine A 上游依賴不可混成 issuer ownership」併進 look-through 那句 | 邊界 |
| 35 | 退休貸款資本目標（2026-07-28） | 留·壓縮 | | 使用者目標，約束 tranche review |

## 呈現契約 → 消費契約（整章重寫，舊章逐字封存）

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 36 | 章首「2026-09-16 整章重寫…每句去向見 alpha-edge-step0-migration…被取代的句子劃線加日期留原地」 | 搬 archive | 章首改為「2026-09-22 定案；取代舊 Alpha 呈現契約，舊章逐字封存 archive」。**劃線留原地的慣例改為整段封存**（09-16 已用過此法） | 劃線堆積是 36k 的一個來源 |
| 37 | 「系統只負責使用者自己做不動的事…產出若無法讓人分辨做了什麼與沒做，它就不算產出」 | 留 | | 目標句 |
| 38 | ~~系統終點是瓶頸度排序~~／~~outcome 量測改為等權重~~ 兩條劃線句 | 搬 archive | | 已被劃線兩次的歷史 |
| 39 | 「資本表達層已於 2026-08-28 整組移除…查證 `probe_lane`／`single_position_nav_cap`」 | 搬 ARCHITECTURE | 查證命令與說明一起搬到 §8.1 | 是「某機制已移除」的驗證，不是行為邊界；「不給尺寸」已在定位句 |
| 40 | 目標與儀器：「目標是倍率不是錯價…realized 降為提醒（D3）」 | 改寫 | 「realized 只提醒不觸發出場」併入「進場靠判斷，出場靠 disproof」bullet | 保留 |
| 41 | 目標與儀器：「現行主流程（FY+1 EPS × 目標倍數）是給大型股的儀器…取代物是多年反向橋，排在 ROADMAP 最後一個 Phase；落地前隱含報酬照印、照兩欄拆解，但不得拿 FY+1 的負數當結論」 | 搬 archive | | G3：估值層停跑，整段失效；事發（COHR 244 vs 266）已在 09-16 archive |
| 42 | 目標與儀器：「候選門檻是覆蓋厚薄，不是上市地（D11）」 | 留·壓縮 | 一句 | 仍有效 |
| 43 | 四層漏斗表：發現列（X 帳號封閉清單、tier、週計分表五欄、推文永遠 tier-4、升降一季一次） | 改寫 | 壓成「量測」bullet 的兩句：來源標籤跟著 lead 走到 outcome；tier 只動 pq1 優先序、升降一季一次 pq2 | 量測層仍有效；欄位細節是手段 |
| 44 | 四層漏斗表：篩選列（filter 不是分數、INV-3、籃子空就空不得放寬、補三格 D8） | 改寫 | 「籃子」換成「候選狀態」：可開是 filter 不是分數；可開為零就零不得放寬；讓它非空的路是研究。**「補三格（可替代性、外部印證、瓶頸業務占營收比例）」刪** | G1／G6；三格是綁排序的手段 |
| 45 | 四層漏斗表：表達列（賭注與判斷錯對稱、歸零旗標紅黃綠、alpha 全歸零淨值少幾 %、沒有 bull/bear） | 改寫 | 歸零旗標是燈不是數字、沒有 bull/bear／機率加權留；「賭注與判斷錯了值多少對稱」的**數字版**搬 archive（G3 停跑賭注四個價格），文字版由敘事承擔 | G3 |
| 46 | 四層漏斗表：量測列（三個 power-law 統計量、起始日與樣本數、三個已知偏差） | 改寫 | 留；加主題等權籃子基準與「圖自己的預測也要量」 | G9 |
| 47 | **「唯一排序權威仍是 `query/bottleneck.py::rank_bottlenecks()`。alpha 排序必須消費它…篩選只在它的順序上過濾」＋事發（2026-09-15 七家未填 sub 被當 0 過濾…看不見的不是候選，是我們沒填的格）** | 搬 archive＋搬 incidents | 規則整句退役（G1）；事發搬進 incidents 作為 **L19 的事發** | 這是 Goodhart 鏈的起點 |
| 48 | 「哪些標的值得看」交付要求：「必須輸出有序清單與明確的首選…首選＝filter 不是分數…條件換成漏斗六條（ROADMAP Phase 4），落地前沿用三條」 | 搬 archive | 換成「不得輸出跨檔全序或首選」bullet | G1；指名 Phase 4 與六條 |
| 49 | 交付要求：「無法排序就指出缺哪一項具體證據；outcome 還沒驗證不是拒絕排序的理由；L14 禁的是未量測機制決定資本尺寸，不是表達研究判斷；刻意不寫死比值」 | 改寫 | 「無法判斷就指出缺哪一項證據，缺 X 必鑄 watch」併入候選狀態 bullet；「L14 禁的是…不是表達研究判斷」併入 L14 判準句 | 原則有效，主詞由排序換成候選狀態 |
| 50 | 交付要求：「排序是研究判斷，必須明標它不是回測或統計勝率，並附各候選的 disproof」 | 改寫 | 主詞換成「讀圖與敘事是研究判斷（A3）…不 gate 任何東西」 | 主詞換掉 |
| 51 | 交付要求：「必須點明相關性…心跳只印回撤、不給燈號、不給動作」 | 留 | | 邊界 |
| 52 | 「進場靠判斷，出場靠 disproof」 | 留 | 加「每條反證寫下即登記 watch」 | G7 |
| 53 | 「隱含報酬的兩個桿：EPS 與倍數適用同一條原則（2026-09-09）…必須拆成兩欄」 | 搬 archive | 只留判準句「一個保守選擇若說不出證據，它是偏差不是審慎」 | G3 停跑；判準句通用 |
| 54 | 「已知會失焦的指標——判別法：會隨多讀一份文件而單調上升嗎」＋帳號計分表倖存者 | 留·壓縮 | | 圖指標的通用判準 |
| 55 | Beta 呈現契約整節（band、再平衡、相對水位、燈號廢止、逐檔表住 APP、兩條相關性警告） | 改寫 | 壓成四行：凍結、band 不是 gate、只補不賣不排名、水位燈號不是訊號、兩條警告常駐頁尾；其餘搬 ARCHITECTURE §8（多數已在） | 呈現細節是手段；beta 凍結 |
| 56 | APP：「LLM changes cognition; APP reads cognition」＋request path 五個不得＋查證 | 留 | | 邊界＋查證 |
| 57 | APP：「首屏的單位是句不是格…三條不可退讓…查證 `python -m alpha brief COHR --list`」 | 留·壓縮 | 查證命令搬 ARCHITECTURE（指名 COHR 與模組） | 原則留 |
| 58 | APP：「缺席不得被壓成無資料…Abstention…settled 不讓 readiness 變好」 | 留·壓縮 | | INV-3 推論 |
| 59 | APP：「`accounting_basis` 的標籤不得宣稱 authority 沒有的東西」 | 搬 ARCHITECTURE | | 欄位語意（手段） |
| 60 | APP：「Daily 與 APP 的分工…順序是 invariant…`python -m webapp status` 列得出 kind 才算搬完」 | 留·壓縮 | 查證命令留一句 | 邊界 |
| 61 | APP：「Daily 拆三層（D12）…drain_limit_per_run 歸零…五段規格住 ARCHITECTURE §4.1」 | 改寫 | 移到新的「等待與心跳」節；旗標名去掉；加「未檢 N 必印」與心跳要印的計數器 | G7 |
| 62 | APP：「沒有寫入端點、Cloudflare Access、127.0.0.1、STOCKBOT_APP_ALLOW_PUBLIC_BIND」 | 留·壓縮 | 環境變數名去掉（OPERATIONS 有） | 安全邊界 |
| 63 | 技術訊號：實測記錄（三次失敗、數字、「不因後續移除而改寫，任何改寫都不得刪減它」） | 留·壓縮 | 三個數字壓成一句，完整證據指向 07-31 brainstorm（已標歷史證據） | 邊界的量測根據；G11 允許改寫敘述 |
| 64 | 技術訊號：「那三次的 scope 全部是 beta 定投擇時…−8.5% 來自單一路徑」 | 留·壓縮 | 併入「其餘 scope 適用通則」 | scope 界定 |
| 65 | 技術訊號：「beta 定投擇時已關…commit `6aa31de`…查證 beta_policy 不應出現 signal」 | 改寫 | commit hash 去掉；查證命令搬 ARCHITECTURE | 手段 |
| 66 | 技術訊號：「其餘 scope 適用通則…四個條件」 | 留·壓縮 | | INV-5 應用 |
| 67 | 技術訊號：「兩個數字不要混用（outcome_aggregate.json vs measured_outcomes counters）」 | 搬 ARCHITECTURE | | 檔案路徑與計數器名 |
| 68 | 技術訊號：「買跌最深的」警告＋量測／訊號／脈絡三分 | 留·壓縮 | | 判準 |

## 協作與邊界

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 69 | 專案記憶唯一權威／研究 skill 唯一權威 | 留 | | |
| 70 | 開發流程唯一權威＋Zoom／Review＋R2 opt-in | 留·壓縮 | | |
| 71 | 「GO 只關閉本 Step」＋常規推進授權六條停止條件＋09-17 使用者原話 | 留·壓縮 | 六條與判準句留；原話「我想要的是沒有需要我核准的事情就繼續」壓進判準 | 這是使用者授權，AGENTS 是正確的家；dev skill 之後只指向這裡 |
| 72 | Local-first、Provider-neutral、單一 writer、Session memory 不是 authority | 留·壓縮 | 各一行 | 邊界 |
| 73 | unattended routine sandbox impact review | 留·壓縮 | | 邊界 |
| 74 | subagent 委派預設關閉＋「⚠ 專用的 `luna-reviewer` skill 已於 2026-09-04 退役…」 | 改寫 | 委派規則留；**luna-reviewer 那句刪** | **刪的理由：** 一次性交接註記，該 skill 已不存在，規則本身與它無關（原文自己這麼寫） |
| 75 | Push 常規動作＋sanity check | 留 | | |
| 76 | 通知不是 authority／Canonical Brief 只有一份 | 留·壓縮 | | |
| 77 | 不建立第二個狀態源 | 留·壓縮 | | |
| 78 | 一手來源優先＋五項核驗清單 | 留·壓縮 | 「機器可執行的路由唯一權威是 source-trace SKILL」句去掉（skill 權威已在 69） | 重複 |
| 79 | 「現況數字會過期，判準不會」整節（含兩次事發、四條規則、skill 清單腐壞例） | 留·壓縮 | 四條規則留；兩次事發搬 incidents | 事發是歷史 |

## Schema 快速記憶 → 圖的寫入紀律

| # | 現行段落 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 80 | 導言（完整欄位表見 graph_schema；表的形狀鎖死字彙留鬆；L4 三分） | 留·壓縮 | 節名改「圖的寫入紀律」 | |
| 81 | `co:*` ID 不憑名猜＋Sivers 事發 | 留·壓縮 | 事發搬 incidents | INV-1 推論 |
| 82 | 報價單位 ≠ 結算幣別＋`identity/currency.py` | 改寫 | 模組名去掉 | 手段 |
| 83 | confidence 累加、sole_source 印證、數字不進圖、disproof 三件套、variant perception 必填 | 留·壓縮 | 「variant perception 是必填，操作定義見 ARCHITECTURE」→ **刪** | **刪的理由：** variant perception 是賭注 overlay 的欄位，G3 停跑；文字版由敘事承擔，不需獨立必填規則 |

## Lessons（G11）

| # | 現行 | 處置 | 去向／改寫要點 | 理由 |
|---|---|---|---|---|
| 84 | 格式說明＋引用慣例 | 留·壓縮 | 引用慣例一句留 | |
| 85 | L1–L3、L5（早期選型判準句） | 留·壓縮 | 各一行；「Implementation｜可改？」欄搬 incidents | 判準 |
| 86 | L4 三連問＋事發（chokepoint-atlas ComponentNode） | 留·壓縮 | 三連問留；事發搬 incidents | |
| 87 | L6 三條＋事發（Coherent ZR/ZR+ 幻覺；Gap 4 仍活著） | 留·壓縮 | 判準留；事發與「Gap 4 仍然活著」搬 incidents（後者是會腐壞的現況） | |
| 88 | L7＋生命週期＋realized | 留·壓縮 | | |
| 89 | L8 三條＋事發（Lumentum） | 留·壓縮 | 事發搬 incidents | |
| 90 | L9＋「現況：三個前置條件已於 2026-07-22 達標…`thesis/preconditions.py`」 | 改寫 | 判準留；現況句與模組名搬 incidents | 現況會腐壞 |
| 91 | L10＋適用範圍 | 留·壓縮 | | |
| 92 | L11 六點＋三段事發（SIVE going-concern、3081 分部歸屬三次、同幣別匯率容差） | 留·壓縮 | 六點各壓成一句；三段事發搬 incidents | 最長的一條，判準全部保留 |
| 93 | L12＋事發（2026-08-05 四缺陷）＋solutions 連結 | 留·壓縮 | 事發與連結搬 incidents | |
| 94 | L13 三點＋事發（filing watcher 78 筆 pending 等三次） | 留·壓縮 | 事發搬 incidents | |
| 95 | **L14 五點＋事發（AXTI／LITE／COHR／SIVE 兩週漲 31–64%…「寫進本檔不等於會生效」）** | **改寫** | 第 1 點加「且那個數字只准是圖、讀圖、敘事、registry、追蹤表裡的東西，不准是幾檔通過某 filter（2026-09-22 改寫；原句曾把研究導向補格子過 filter）」；事發搬 incidents | **使用者點名的那句**：原句本身沒錯，錯在數字選了「幾檔通過排序」；改寫把數字的合法範圍寫死 |
| 96 | L15 四點＋事發（`yfinance://history` 少 ticker 後綴） | 留·壓縮 | 事發搬 incidents | |
| 97 | L16 四點＋事發（2026-08-26 三次） | 留·壓縮 | 事發搬 incidents | |
| 98 | L17 四點＋事發（六個同形缺陷）＋solutions 連結 | 留·壓縮 | 事發與連結搬 incidents | |
| 99 | L18 五點＋事發（82 條邊 29 條要改；1,105 段逐字被丟掉）＋brainstorm 連結 | 留·壓縮 | 事發與連結搬 incidents（該 brainstorm 已標設計來源） | |
| 100 | **L19（新增）** | 新增 | 判準：每 session 載入的檔裡的手段句會被當成目標；手段句不進本檔、驗收數字不准綁 filter 通過數。事發（排序 Goodhart 鏈，2026-09-15 → 09-22）寫進 incidents，引用第 47 列那段 | 使用者 2026-09-22 的診斷，值得成為判準 |
| 101 | 文件化學習（solutions、closed-vocabulary-registry、.gitignore config 規則） | 留·壓縮 | | |

## 刪除清單（G11：每筆附理由）

| 列 | 刪了什麼 | 理由 |
|---|---|---|
| 44 | 「補三格（可替代性、外部印證、瓶頸業務占營收比例）讓籃子非空」 | 三格是為了讓特定公司過排序 filter 而定的手段；G1 退役排序後無主詞。原文逐字仍在 archive |
| 74 | 「luna-reviewer skill 已於 2026-09-04 退役…上面這幾條授權邊界與它無關」 | 一次性交接註記；規則與它無關是原文自述 |
| 83 | 「variant perception 是必填，操作定義與生命週期見 ARCHITECTURE」 | 它是賭注 overlay（G3 停跑）的欄位；「我們賭什麼」由敘事文字承擔 |

**沒有任何 lesson 被刪。** 三筆刪除都不是 lesson。

## 沒搬、沒改、需要你留意的三處

1. **常規推進授權六條停止條件現在只住 AGENTS。** Step 3（development-flow）會把 skill 裡重複的那份改成指向；`AGENT_WORKFLOW.md` §5 也有一份，
   apply 時一併改成指向。三份變一份。
2. **草稿 14,623 字元，比原先說的 12k 多兩千。** 多出來的全是資本與風控、協作與邊界兩節——那裡每一句都是邊界，壓縮了但沒有一句能拿掉。
   要再往下只能拿掉邊界，我不建議。
3. **「等待與心跳」是新節**，內容來自 G7，現行 AGENTS 沒有對應段落。它是唯一「新增」的節。
