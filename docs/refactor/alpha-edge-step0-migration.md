# Alpha Edge Step 0 — 文件整併的去向清單（2026-09-16）

> **性質：** 轉向 Step 0（D0）的產出物之一。決定紀錄是
> [`../brainstorms/2026-09-16-alpha-edge-discovery-requirements.md`](../brainstorms/2026-09-16-alpha-edge-discovery-requirements.md)。
> 本檔只記「每一句被移除或改寫的舊契約去了哪裡」與「每個舊 ROADMAP 標題去了哪裡」，不重抄內容。
> 兩份逐字封存：[`../archive/agents-presentation-contract-pre-alpha-edge.md`](../archive/agents-presentation-contract-pre-alpha-edge.md)
> （`AGENTS.md` 舊呈現契約整章）、[`../archive/roadmap-pre-alpha-edge.md`](../archive/roadmap-pre-alpha-edge.md)（舊 ROADMAP 整份）。

## 0. 驗收數字（Step 0 的 L14：哪個數字會變）

| 驗收 | before（2026-09-16 master `c810588`） | after（branch `docs/alpha-edge-step0`） | 查證 |
|---|---|---|---|
| `AGENTS.md` 字元數 < 34,836 | 36,075 字元 | **34,624 字元** ✅ | `python -c "import io;print(len(io.open('AGENTS.md',encoding='utf-8').read()))"` |
| L1–L17 全在 | 17 | **17** ✅ | `grep -c "^### L" AGENTS.md` |
| `python -m audit invariants` | FAIL 0 | **FAIL 0｜PASS 13** ✅ | 同左 |
| `tests/test_codex_daily_permissions.py` | 綠 | 綠 ✅ | `.venv\Scripts\python.exe -m pytest tests/test_codex_daily_permissions.py` |
| 全套 pytest（`.venv`） | 2026-09-15 master 綠 | **2,447 passed／1 skipped** ✅（2026-09-16，417 秒） | `.venv\Scripts\python.exe -m pytest -q` |
| 憲法／六條 invariant／四個 gate／協作邊界／L1–L17 一字不動 | — | **逐段 diff 相同** ✅ | `patch_agents.py` 第 5 步逐段比對（本檔 §5 有等價命令） |
| 每句被移除的舊契約列得出去向 | — | §1、§2 | 本檔 |

⚠ **單位要講清楚（L11-6：修法也是待否證的結論）。** 決定紀錄 §5 寫「字元數 < 現在的一半（2026-09-16 實測 69,671）」，
但 69,671 是 `wc -c` 的 **bytes（含 CRLF）**，不是字元；真正的字元數是 36,075。啟動 prompt 據此寫成「< 34,836」，
以字元計只是 −3.4%，**不是減半**。而減半在 D0 之下**結構上做不到**：憲法（2,535）＋協作邊界（4,040）＋L1–L17 與
文件化學習（11,174）＋標頭／角色表／工作語言（1,593）這些「一字不動」的段落合計約 **19,800 字元**，已超過
36,075 的一半（18,038）。本次做到 34,624（−1,451 字元；bytes 69,671 → 65,838，−5.5%）——**達到啟動 prompt 的字面
門檻，沒有達到「減半」的意圖**。要減半只有兩條路，都要使用者決定：①把 L1–L17 的「事發」段落搬 archive（違反 D0
「一字不動」）；②接受本次數字並把驗收改寫成「字元數必須降，且內容驗收全過」（2026-09-04 Phase 3.9 先例的寫法）。

**2026-09-16 使用者定案：選 A。** 驗收改寫為「字元數必須降，且內容驗收全過」；決定紀錄 §5 與啟動 prompt 已同步劃線改寫，
ROADMAP Phase 0 標 ✅。

其餘會變的數字：`docs/ROADMAP.md` 209,214 → 13,095 字元（579 → 240 行）；舊呈現契約整章 10,491 字元進 archive。

## 1. `AGENTS.md`——逐句去向

處置字彙：**留**（判準原句留原地，可能壓縮措辭但語意不變）／**劃線**（劃線加日期留原地）／**archive**（逐字只在封存檔，
原地留指向）／**改寫**（語意依 D0–D15 改變，舊句在 archive）／**新增**。

### 1.1 標頭與「資本與風控」（不在呈現契約章，只加不刪）

| 句 | 處置 | 去向 |
|---|---|---|
| 「目標一句話」（power-law 倍率、不是 20% 錯價、結構不變就抱、出場只認反證、決定紀錄連結） | 新增 | 標頭「定位一句話」之後 |
| 「alpha 格自 2026-09-16 起只觀測、不設目標（D1）」＋查證命令 | 新增 | 「資本與風控」Numeric SSOT 段之後；config 未動（Step 0 不動程式），查證命令會告訴讀者落地了沒 |
| 「部位真相是 Google Sheet（D14）…alpha 原則上不用貸款資金…系統不建 gate」 | 新增 | 「資本與風控」Capital Authority 段之後 |

### 1.2 舊「Alpha 呈現契約：候選＋事件追蹤，不是部位尺寸」

| 舊句（節錄） | 處置 | 去向 |
|---|---|---|
| 系統只負責兩件事：哪些標的值得看、它們有什麼新事件；買多少由使用者決定 | 改寫 | 新版第一段擴為五件（值得看／新事件／賭對值多少／判斷錯值多少／哪個管道產出贏家）；原句 archive |
| 「理由是實測而非偏好（2026-08-15／08-28 實測值）…6 個 ELIGIBLE cohort…axis_ceiling…COHR 三個資本風控沒有一個 binding…」 | archive | 事發與當時數字；判準句「產出若無法讓人分辨做了什麼與沒做，它就不算產出」**留**在新版第一段 |
| 使用者原話「繞了這麼久只得到我很早就看到的幾間公司…」 | archive | 同上 |
| 「因此資本表達層已整組移除：live_supported_range／axis_ceiling／paper_target／probe cap 與四動作」 | 留（壓縮成一句） | 新版第三段 |
| ~~系統終點是瓶頸度排序，注意力狀態只剩 MONITOR／REVIEW~~ | 劃線 | 原地，加 2026-09-16「終點是四層漏斗」註 |
| 「修正（2026-09-15 D1）：…個股頁的中心改為賭注…scenario=variant overlay…payoff…條件句不是機率加權…沒有 bull／bear…型別層強制 independent＋supporting…沒寫賭注是 optional 缺席…不得補 bull case…」 | 改寫（壓縮） | 判準進四層漏斗「表達」列（賭注與「判斷錯了值多少」對稱、仍無 bull／bear、無機率）；機制細節本來就住 `ARCHITECTURE.md` §6.10（該節已加 D2 註）；全文 archive |
| 查證 `analyst_view/COHR.json` 的 `bet.status` 命令 | archive | 現況查證命令；`ARCHITECTURE.md` §6.10 仍有入口 |
| 「outcome 量測改為等權重報酬追蹤：只記哪天推薦了這檔、當時股價、之後報酬率」 | 劃線 | 原地，加 D15 註（主統計量換成三個 power-law 統計量） |
| 查證 `investment_policy.json` 的 `probe_lane` 命令與說明 | 留 | 新版第三段 |
| 「真正的風控完全不變…NAV 比例呈現是純呈現、零門檻——不判斷好壞、不告警、不阻擋」 | 留（壓縮） | 新版第三段 |

### 1.3 舊「哪些標的值得看」的交付要求

| 舊句 | 處置 | 去向 |
|---|---|---|
| 「判準四維度住 ARCHITECTURE；這裡是對輸出的硬要求」 | archive | 四維度仍住 `ARCHITECTURE.md` §6（該節已加 D11 註） |
| 有序清單與明確首選、直接回答「現在要加碼哪一檔」 | 留 | 交付要求第 1 條；＋「首選＝filter」與漏斗條件（落地前沿用三條） |
| 證據不足要指出缺哪一項具體證據、不得以「未經 outcome 驗證」搪塞 | 留（壓縮） | 第 2 條 |
| 「outcome 還沒驗證」不是拒絕排序的理由…死循環…判斷與尺寸是兩件事…⚠ 刻意不寫死比值 | 留（壓縮） | 第 2 條 |
| 排序是研究判斷、明標非回測、附 disproof | 留 | 第 3 條 |
| 相關性：N 檔不等於 N 個獨立機會、全買是同一賭注下 N 次 | 留（壓縮）＋新增「主題翻轉十檔一起 −50%…心跳只印回撤」 | 第 4 條 |
| 進場靠判斷，出場靠 disproof | 留 | 交付要求末段 |

### 1.4 舊「隱含報酬的兩個桿」

| 舊句 | 處置 | 去向 |
|---|---|---|
| 沒有 re-rating 證據時目標倍數＝校準倍數；折溢價必須指得出證據；兩欄拆解；「保守選擇說不出證據是偏差」 | 留 | 同名小節 |
| 「這與 ROADMAP『沒有 differentiated evidence 時 EPS 收斂到 consensus 是健康的』是同一條原則」 | 留（改為引句） | 原則原文在 archive ROADMAP「Post-MVP」；blind-spot-audit A2 同句 |
| 事發（2026-09-08）：COHR／LYC.AX −20.7%／−36.3%、倍數折價 −16%／−20%、「較市場折價約 17%」的習慣 | archive | 事發 |

### 1.5 舊「已知會失焦的指標」

| 舊句 | 處置 | 去向 |
|---|---|---|
| evidence 等級／供應商計數／documents 計數三條＋判別法 | 留（壓縮成一句） | 同名小節；＋新增計分表倖存者警告 |
| 「首選＝filter 不是分數（2026-09-15 D2）…三條條件…INV-3…不得為了非空放寬…讓它非空的路是研究」 | 留（搬位） | 交付要求第 1 條＋四層漏斗「篩選」列 |
| 「唯一排序權威是 rank_bottlenecks()…不得重算…research_status 不得拿來排序」 | 留 | 四層漏斗表之後的排序權威段 |
| 「（axis_ceiling／paper target 曾被誤當排序代理…）」 | archive | 歷史括號 |

### 1.6 舊「Beta 呈現契約」

| 舊句 | 處置 | 去向 |
|---|---|---|
| 「使用者的實際行為是定期投入而非擇時…呈現層不得以任何名義復刻擇時語言（今天是否投入、本輪上限、節奏、可評估／暫停新增）」 | archive（理由句） | 判準由「技術訊號的地位」的「beta 定投擇時這條路已關…不得以任何名義回到 beta 的文件或輸出」承接（留） |
| band 是容忍區間不是 gate；再平衡只用新錢、不賣出；不給金額不排名不產生尺寸；貸款 tranche 不適用 | 留 | Beta 第 1 條 |
| 相對水位只呈現、不排序、不換算金額；「長期上漲…不是該等回檔的訊號」；拿它排序就變回訊號 | 留 | 第 2 條 |
| 燈號只表達行情資料狀態；舊語意已於 2026-08-29 明文廢止 | 留（原句） | 第 3 條 |
| 逐檔表與目標配置表住 APP；Daily 只印門檻跨越與狀態翻轉 | 留 | 第 4 條 |
| 「⚠ 舊規則『即使沒有配置缺口，逐檔表仍不得省略』到此廢止——它成立的前提是…廢止必須寫出來」 | 留（壓縮成一句廢止紀錄） | 第 4 條；理由全文 archive |
| 「不變的是 invariant 本身：逐檔心跳必須永遠看得到…APP 當天沒被 materialize 時 Daily 必須印出來（L12）」 | 留 | 第 4 條 |
| 兩條相關性警告由 APP 常駐（alpha 與 beta 同一賭注；TSMC look-through 約 28%） | 留（壓縮） | 第 5 條 |
| 「⚠ 這不是放寬：每天講一次變成每次看都看得到」 | archive | 說明句 |
| 呈現細節見 ARCHITECTURE §8 | 留 | 段末 |
| — | 新增「開發凍結（D6）」 | 標題與首段 |

### 1.7 舊「APP 呈現契約」

| 舊句 | 處置 | 去向 |
|---|---|---|
| LLM changes cognition；request path 不得…；只有 materialize；「這不是效能考量」；查證 pytest | 留（壓縮） | 第 1 段 |
| 首屏是句不是格：七格前因後果的逐項列舉（什麼在放量／…／什麼時候知道）、一把尺三端、六段論證的逐段名稱 | 留（壓縮，列舉 → `ARCHITECTURE.md` §6.11–6.12 本來就有） | 第 2 段 |
| 「算術與圖的敘述由封閉句型組（alpha/narrative/argument.py）…『跳』『邊』『sub=5』『tier』不進論證層，只講『誰說的、有沒有別人印證』」 | archive | `ARCHITECTURE.md` §6.12 有同義描述 |
| 三條不可退讓（文字進 append-only ledger／數字 placeholder／禁字表型別層拒收）；沒寫短評印「還沒寫短評」 | 留 | 第 2 段 |
| 事發：V0 首屏約 30 個數字、使用者原話「一堆數字跟內部名詞…看不懂」 | archive | 事發 |
| 查證 `python -m alpha brief COHR --list` | 留 | 第 2 段 |
| 缺席不得壓成「無資料」；absence_kind 由產生端宣告；四種缺席 | 留（壓縮） | 第 3 段 |
| 「刻意不主張」只能來自 Abstention；reason／revisit_when；結構上不可能帶數字；settled 不讓 readiness 變好 | 留（壓縮） | 第 3 段 |
| accounting_basis 標籤；「Lynas／HDS／IQE 在 ledger 裡全都寫 gaap」 | 留（壓縮）；例子 archive | 第 4 段 |
| Daily 與 APP 分工判準；pq2 核准留 Daily；「球在誰手上」四段住 APP；分段依據 resolution_mode | 留（壓縮） | 第 5 段 |
| 「⚠ 09-08 原句『放 APP 只多一次摩擦』到此廢止」；「在 webapp status 列得出 queue kind 之前，Daily 的四段照舊完整印出」 | archive | 由「還沒有 APP 畫面的段落一律留在 Daily」（留）涵蓋 |
| 順序是 invariant：APP 先讀得到 Daily 才能不印；還沒有 APP 畫面的段落留 Daily；`webapp status` 機械判準 | 留 | 第 5 段 |
| APP 沒有寫入端點／帳號系統；無 POST／PUT／PATCH／DELETE；Cloudflare Access；127.0.0.1；ALLOW_PUBLIC_BIND；四個 gate 不放寬 | 留（壓縮） | 末段 |
| — | 新增「Daily 拆三層（D12）」規格段＋「尺多一端（D2）」句 | 第 6 段、第 2 段 |

### 1.8 舊「技術訊號的地位」

| 舊句 | 處置 | 去向 |
|---|---|---|
| 實測記錄（歷史，不因後續移除而改寫，任何改寫都不得刪減它）整段 | **留（逐字）** | 同名小節第 1 段（`patch_agents.py` 以 regex 從舊檔取出原文插入，非手抄） |
| 「⚠ 那三次測的是什麼（2026-09-10 補）：…全部是 beta sleeve 的定投擇時…禁令是全域的…L15-1…強度也不齊：rolling start 只有測試二…『有害 −8.5%』來自單一路徑…『回測方法論約束』自己就寫著…」 | 留（壓縮成三句） | 第 2 段；全文 archive |
| beta 定投擇時這條路已關；移除清單（RSI／MACD／sma_50_slope／tier／pace／campaign_budget_fraction_by_sleeve／三態／本輪可評估上限）；不得改名回填；查證 beta_policy | 留（原句） | 第 3 段 |
| 其餘 scope 適用通則：四個條件 | 留（壓縮） | 第 4 段；＋新增「D5 計分表是第一個實例」 |
| 「⚠ 前置條件是 outcome 追蹤：樣本太少時…更弱的結論」 | 留（壓縮） | 第 5 段末 |
| 「⚠ 兩個數字不要混用（2026-09-11 更正——前一版只給了後者）」：等權報酬追蹤與 measured_outcomes 各自的命令與語意 | 留（壓縮；更正歷史 archive） | 第 5 段；＋D15 註 |
| 機制性警告：「買跌最深的」（EFA CAGR 7.2%、98 次）；alpha 上「哪檔跌最深＝哪檔 beta 最高」 | 留 | 第 6 段 |
| 量測／訊號／脈絡三分；位置指標拿去排序就變回訊號 | 留（壓縮）；＋「歸零旗標」列入量測 | 第 7 段 |

## 2. 舊 `docs/ROADMAP.md`——逐標題去向

| 舊標題 | 判定 | 去向 |
|---|---|---|
| 檔頭（指向 2026-09-03 archive 與 roadmap-migration） | 改寫 | 新檔頭同時指向兩份 archive、本檔與決定紀錄 |
| 「⚠ 開發項只住這裡，不進 pq2」 | **KEEP 逐字** | 新 ROADMAP（`AGENTS.md`「授權載體唯一」引用它） |
| 「現行路線圖：Alpha Research Refactor」（North Star、Evidence→…→Outcome Learning、三層責任、五份設計文件連結） | archive | North Star 由 Alpha Edge 版取代；設計文件仍住 `docs/refactor/`（AGENTS「本檔的角色」已指向該目錄；historical-failure-matrix 在新檔 completion gate 段仍有連結） |
| 「Phase 表」Phase 0–8 | archive（交付歷史） | Phase 4 🔶 的剩餘：`market_implied_margin` 需 segment 資料＝研究（pq2 逐檔）；peer registry 建議不建＝已在「明確不排程」 |
| 「⚠ AGENTS.md 的改動分兩類」 | archive | A 類判準「code 改動讓某句話變成假的，同一個 commit 改掉」已住 `skills/development-flow/SKILL.md` Step 3；B 類（Phase 3.9）已完成 |
| 「每個 Phase 的 completion gate（八項）」 | **KEEP 逐字** | 新 ROADMAP（`AGENT_WORKFLOW.md` §10 引用它） |
| 「重構期間的硬約束」12 條 | 改寫為「硬約束（轉向不放寬任何一條）」14 條 | 12 條原則全部沿用（去掉會腐壞的數字：662 條／268 筆／126 個測試檔／16 條 rule）；新增 D6 凍結、D14、籃子不放寬、last30days 不進無人值守 |
| 「開放 backlog」約 90 列 | DONE 列 archive；**OPEN 16 列**逐列判定 | 新檔「舊 backlog 未結案項」表（Phase 4／5／7、維持營運、留 archive、重複列結案） |
| 「產品決策：主流程的終點是 Implied Return，Entry Threshold 是 optional」 | archive | 契約到 Phase 7 前仍生效；`OPERATIONS.md`（Analyst View 段）與 `CONCEPTS.md`（Optional Analytical Capability／Base-case Implied Return）已加註指向 |
| 「Post-MVP Alpha Edge Roadmap」核心原則＋A–H | archive | 核心原則句由 `AGENTS.md`「隱含報酬的兩個桿」引用、blind-spot-audit A2 承接；A（attribution，分母太小不做）、C（lead indicator）→ 發現層、D（substitutability quality）→ Phase 1 補三格、E（coverage）→ D11 覆蓋厚薄、F（outcome learning）→ 量測層 Phase 5、G（model backlog）→ Phase 7 反向橋、H 順序全 ✅ |
| 「明確不排程」 | 新檔保留清單標題 | 理由與量測住 archive；「轉向不重開這些」 |
| 「研究主題範圍」（2026-08-20 定案＋2026-09-09 修正） | 壓縮 | 新檔同名段（D4＋09-09 三條＋HBM 不變）；全文 archive |
| 「開工前必讀／已撤回的診斷」 | **KEEP 逐字** | 新 ROADMAP（`AGENTS.md` L11 Implementation 指向它） |
| 「開工前必讀／看起來像缺口但不是」 | **KEEP 逐字** | 新 ROADMAP（active guardrail） |
| 「想法怎麼變成程式」 | **KEEP 逐字** | 新 ROADMAP |
| 「什麼值得開發／什麼交給 Claude」 | **KEEP 逐字** | 新 ROADMAP |

## 3. `ARCHITECTURE.md`／`OPERATIONS.md`／`CONCEPTS.md`——只加註、只劃線，零刪除

| 檔 | 位置 | 加了什麼 |
|---|---|---|
| ARCHITECTURE §4 | daily harvest bullet 之後 | D5／D15 規格（帳號登記表、蓋章、計分表、MOPS 重訊、月營收、lead 60 天到期），明標「尚未交付」 |
| ARCHITECTURE §4.1（新） | §4 末 | Daily 三層與心跳五段規格（D12），附「落地前現況」與查證命令 |
| ARCHITECTURE §6 | 排序權威段之後 | 轉向對本節的三個後果（補三格、覆蓋厚薄 filter、FY+1 → 反向橋） |
| ARCHITECTURE §6 四維度 | 第 4 點之後 | D11：市值／analyst_count 仍不進排序，但是 filter 的輸入 |
| ARCHITECTURE §6.10 | 規則 4 之後 | D2 對稱 overlay（仍非 bear、仍無機率） |
| ARCHITECTURE §6.10 | 「刻意不做（留給 V1–V4）」 | **劃線**＋註（V1–V3 已交付、V4 併入 Phase 5） |
| ARCHITECTURE §6.13 | 首選 filter 段之後 | D3 `realized` 降為提醒；D11 首選條件將換成漏斗六條 |
| ARCHITECTURE §8 | 呈現的家段之後 | D6 beta 凍結 |
| ARCHITECTURE §8 | 目標配置查證命令之後 | D1 alpha 格 `observed_only`（附落地前現況與查證） |
| ARCHITECTURE §8 | `store.record_live_choice` 段之後 | D14 Sheet 是部位真相 |
| OPERATIONS 每日操作 | 流程圖之後 | D12 三層：落地前照舊；落地時同 change 改本節、drain 歸零、fixed entry 對齊 |
| OPERATIONS 自主研究迴圈 | 題源優先序之後 | D12 後這裡是唯一研究路徑；D8 補三格排最前（落地隨 Phase 1） |
| OPERATIONS Analyst View | ROADMAP 指向 | 改指 archive ＋ Phase 7 註（原指向會斷） |
| OPERATIONS Beta 快照 | 命令說明之後 | D6 凍結 |
| OPERATIONS 記錄成交 | 末段 | D14 再確認、不加 gate |
| OPERATIONS Daily／pq1 參數 | drain_limit bullet | D12 落地後應為 0 |
| OPERATIONS 報告留檔 | Weekly authority 段之後 | D5：計分表在 weekly 算 |
| CONCEPTS Signal Source Registry | Avoid 之後 | D5 tier 字彙（舊 candidate／active／suspended **劃線**廢止） |
| CONCEPTS Crowding Discount | Avoid 之後 | D11（sizing rule **劃線**；改為 filter 條件） |
| CONCEPTS Base-case Implied Return | Avoid 之後 | Phase 7 註 |
| CONCEPTS Optional Analytical Capability | Avoid 之後 | Phase 7 註 |
| CONCEPTS 檔尾（新節） | 「Alpha Edge（2026-09-16 轉向後的詞彙）」 | 14 個新詞：四層漏斗、覆蓋厚薄、帳號登記表、蓋章、帳號計分表、回溯評分、心跳、分類層、判斷錯了值多少、歸零旗標、alpha 全歸零淨值少幾 %、power-law 統計量、多年反向橋、Lead 到期；明標「機制交付前只存在於文件」 |

⚠ 既有但與**本次轉向無關**的 stale 詞條（`CONCEPTS.md` 的 Confidence Envelope／Action Card 仍描述 2026-08-28 已移除的資本表達層、
Watchlist Gate 描述已除役的升格）**刻意未動**——那是另一筆清理，不混進 Step 0 的 diff。
⚠ **2026-09-21 已做完那一筆清理**：production code 字串、LLM system prompt、會被載入的 skill 與判準檔（`CONCEPTS.md`／`investment-sop.md`／`scoring_rubric.md`／`closed-vocabulary-registry.md`／`ARCHITECTURE.md` §2）全部改掉，`output_type` 欄位移除。**已產出的歷史 memo 與其 sidecar 刻意不動**——那是當時的產出，改它等於竄改紀錄。

## 4. Skills（D13）

| 檔 | 改了什麼 |
|---|---|
| `skills/daily-brief/SKILL.md` | 標題下加 scope note：呈現契約重寫中，衝突以 `AGENTS.md` 為準；D12 三層隨該 Phase 同 change 改寫；在那之前流程照舊 |
| `skills/alpha-status/SKILL.md` | 同型 scope note（D1／D11／D15 會改什麼；四 pane 照舊） |
| `skills/blind-spot-audit/SKILL.md` | 新 lens **A9 瓶頸壽命、擁擠度與週期位置**（C11 之前）；不含任何已退役字彙 |
| `scripts/sync_agent_skills.py` | 已跑；轉接層只讀 frontmatter，`--check` 無漂移 |

## 5. 本檔自己的驗收（讓「沒有東西被靜默丟掉」可機械查）

```powershell
# 舊呈現契約整章 == archive 檔去掉檔頭（逐字）
python -c "import subprocess,io;m=subprocess.run(['git','show','master:AGENTS.md'],capture_output=True).stdout.decode('utf-8').replace('\r\n','\n');s=m.index('\n# 呈現契約\n')+1;e=m.index('\n# 協作與邊界\n')+1;a=io.open('docs/archive/agents-presentation-contract-pre-alpha-edge.md',encoding='utf-8').read();print(a.endswith(m[s:e]))"
# 舊 ROADMAP == archive（git 記為 rename，內容零改動）
git diff --stat -M master -- docs/ROADMAP.md docs/archive/roadmap-pre-alpha-edge.md
# 不可動段落逐字相同（憲法／協作邊界／Lessons）
python -c "import subprocess,io;m=subprocess.run(['git','show','master:AGENTS.md'],capture_output=True).stdout.decode('utf-8').replace('\r\n','\n');n=io.open('AGENTS.md',encoding='utf-8').read();seg=lambda t,a,b:t[t.index(a):(t.index(b,t.index(a)) if b else len(t))];print([seg(m,a,b)==seg(n,a,b) for a,b in [('# 憲法\n','# 授權與決策\n'),('# 協作與邊界\n','# Schema 快速記憶'),('# 踩過的坑',None)]])"
```
