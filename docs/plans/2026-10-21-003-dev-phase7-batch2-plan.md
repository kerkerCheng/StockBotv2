# PLAN_PROPOSAL：Phase 7 開發批次二——failure log 過 gate 的 15 條＋#90（2026-10-21）

> 日期 2026-10-21｜狀態：**APPROVED**（使用者 2026-10-21「給我一次做你推薦的方式」＝Q1 A、Q2 A、Q3 A、Q4 A、Q5 B；照 §0 順序逐 Step 做，各自 R1，E6 走 R2）｜載體：本檔＋ROADMAP（開發項不走 pq2）
> **起因（使用者 2026-10-21「A7-A12 go」）：** A12＝把 failure log 裡過 gate、原標「7.5 提」的開發項現在合成一份提案——plan `2026-10-04-001` §0.4 A5（2026-10-07）已改成「過 gate 的隨時提、擋研究的排在研究前」，囤到 12-22 違反 A5。
> **這份是提案，不是施工授權：** A12 的 go 授權「現在提」，不授權「全部做」。使用者回覆 Q1–Q5 並點頭後，沒有待選問題的 Step 照 AGENTS 常規推進授權接續；命中 R2 trigger 的（E6）照 Phase 7 Q7 常規 opt-in 走窄範圍審查者。
> **盤點方法（2026-10-21 唯讀）：** failure log 末欄逐列解析；每條的修法落點跑 `git log --since=<登記日> -- <檔>` 並 grep 現行程式。**15 條＋#90 全部還沒被其他 commit 修掉**（各 Step「現況」附證據）。
> **不碰：** 四個人工 gate 的語意（入圖、Engine C 判讀寫入、thesis mutation、live）；資本路徑；AGENTS 判準句；A3「追源到期＝轉終局並計數」（2026-09-24）。

## 0. 進度與排序

排序只看「擋不擋研究」（A5）：研究產出答不出 → 叫醒噪音吃研究時間 → 讀圖安靜過期 → 公開 repo 風險（不擋研究但不可逆，明確排上）→ 核准時看到的資訊不全 → 標籤與母體正確性 → 不擋研究。同檔的合做：E3／E4 都動 `alpha/structure_reading/staleness.py`，先 E4 再 E3。

| Step | failure log | 做什麼（一句） | 擋研究？ | Zoom／Review | 規模 | 要你選 | 狀態 |
|---|---|---|---|---|---|---|---|
| E1 | #81 | 名冊寫入時就補足新台股三年窗的月營收與股數 | 是 | Z2／R1 | 中（約 60 行＋測試） | Q1 A | ✅ 10-21（變異 9／9；鉤子在兩條 complete、心跳兩行加「三年窗不滿」） |
| E2 | #63 | 例行重訊叫醒的反證，照主旨分組判 | 是 | Z2／R1 | 中 | Q2 A | ✅ 10-21（變異 7／7；回放 32 次叫醒 → 8 組） |
| E3 | #87 | 讀圖 digest 收 develops／is_variant_of | 是 | Z2／R1 | 中 | — | ✅ 10-21（變異 7／7；升版當天該重讀 0、印「digest 升版」14 份） |
| E4 | #75 | 只因同義節點合併而換 id，不算讀圖變動 | 是 | Z1／R1 | 小 | — | ✅ 10-21（變異 5／5；現行 58 份讀圖狀態 0 份改變） |
| E5 | #79＋#59 | 共用別名進走圖第 9 型＋入圖乾跑提示 | 是 | Z2／R1 | 中 | — | ✅ 10-21（變異 4／4；全圖只靠別名 11 對、reliant／photoresist 仍不配） |
| E6 | #90 | 券商內容不進公開 repo 的機制 | 否（公開、不可逆） | Z2／**R2** | 中 | **Q3** | ○ |
| E7 | #85② | 更正走廊乾跑列出 claim 改句 | 半（核准資訊） | Z1／R1 | 小（約 20 行） | — | ✅ 10-21（變異 4／4；回放 [812] 2 筆、[814] 1 筆） |
| E8 | #62 | 輪詢不掛已取得的同一份申報；終局 lead 名下等待收掉 | 半 | Z2／R1 | 中 | — | ✅ 10-21（變異 4／4；回放 ew_0020 3/3 擋下；終局不等名下 active 等待現值 5 → 下次 sync 收） |
| E9 | #10＋#11 | 證據等級認得關係人自述與買方自述 | 半 | Z2／R1 | 中 | — | ○ |
| E10 | #64 | 覆蓋家數取三者最大 | 半 | Z2／R1 | 小＋重算 | **Q4** | ○ |
| E11 | #68 | 「供給側多一家」不再是機械反證觸發；讀圖反證寫新增產能 | 半 | Z2／R1 | 小 | — | ✅ 10-21 程式＋skill（回放 InP 基板 8 份舊讀圖：仍該重讀、觸發 0）；③兩條「圖上第 N 家」反證待下次換版改寫 |
| E12 | #50 | 證據清單列得出敘事的 library/raw 引用 | 否 | Z2／R1 | 小 | — | ○ |
| E13 | #60 | ROADMAP 改寫時待決題不得消失＋「刻意不併／留待」結構化 | 否 | Z2／R1 | 中 | — | ○ |
| E14 | #40 | 改動後自動重啟 serve | 否 | Z2／R1＋sandbox | 小 | **Q5** | ○（推薦不做） |
| E15 | —（7.5 前置） | 追蹤表 paper lane 依現行狀態分組印 | 否（7.5 報告要用） | Z1／R1 | 小（約 12 行） | — | ✅ 10-21 程式（變異紅；真資料驗收待下一次 daily 追蹤表：各組 n 加總＝paper 列數） |

**另：#96 建議併回 #1（由主 session 確認，本檔不展開）。** #96（10-20：一則轉述 Lumentum 10-K 的推文以共用 `co:lumentum` 排回 13 則停放 lead，6 組重查全是誤醒）與 #1 第 12、13 次（10-14 GF 6-K、10-15 台積電 6-K，觸發形式都是 `related_triaged_lead`）是同一個缺點；照 failure log 檔頭「第二次被另一個 case 撞到就在原條目追加」，已 ≥3 次、過 gate。2026-10-08 D1 修的是停放時 watch 的標的，沒有動 `engine_b/leads.py` 的 `related_triaged_lead` 排回。確認後排在 E2 之後（擋研究）。

## 1. 要你選的（各附推薦）

- **Q1（E1）新台股的歷史在哪裡補？** **A（推薦）** 名冊寫入的兩條互動路徑（`todo complete-registry-batch`、入圖包 staged 名冊條目的 `complete-ra`）完成時，對本次新增的台股直接回補；B daily 加一步回補「序列為 0 或不滿三年窗」的已登記台股——動無人值守 executable surface（sandbox impact review），而且違反 OPERATIONS「台股月營收」節「月營收是互動式入口、不進無人值守」的判準；C 只印命令不跑（仍要人記得，L14）。
- **Q2（E2）例行重訊怎麼處理？** **A（推薦）** 醒來時機械附上重訊主旨類別，判定區塊照（公司、類別）分組、一組判一次，喚醒條件不動；跑兩週量「例行重訊占語意判定的比例」再談 B（INV-5：先量測後放閘）。B 對零內容的三類（注意交易資訊、法說會召開通知、內線／澄清公告）不叫醒、只計數——「取得或處分資產」不能列（它本身就是快接頭層反證 #3 的條件）。C 兩個一起做。
- **Q3（E6）券商內容怎麼擋在公開 repo 外？** **A（推薦）** RA draft 加一欄 `private_context`：只寫進 `library/private/`，決策區塊照樣印給你看，公開入圖報告只印「有私有脈絡 N 段」；SKILL 寫「券商讀到的只寫這一欄」——用結構分開兩種語意（L12），不靠字串偵測。B prepare 對公開三段掃券商標記、命中就拒收——會誤報：今天公開檔 7 處命中有 4 處只是點名「這則 lead 從哪份券商報告來」，不是內容（L16 末句：不要用會誤報的 linter 防這件事）。C 不做機制（你 10-20 對既有兩份選了 c；規則仍只住 SKILL 文字）。
- **Q4（E10）覆蓋家數改口徑後門檻怎麼辦？** **A（推薦）** 家數取 EPS 0y、營收 0y、目標價三者最大，門檻 12 照舊；先用新口徑重算一次，翻盤的檔逐檔列給你看。B 同 A，再重量一次門檻斷點（改 `config/alpha_screen.json`）。C 不改口徑，只在判定旁印三個數。
- **Q5（E14）要不要做自動重啟？** **B（推薦）不做**：10-07 起流程是「有改動就重啟並驗 `code.stale=false`」，failure log 沒有第 3 次；A 做——materialize 收尾偵測長駐 serve 就重啟，要 sandbox impact review。

## E1 名冊寫入時補足新台股的三年窗（#81）

```
INTAKE
Zoom: Z2（名冊寫入的兩條路多一個副作用：寫 Engine C 觀測；心跳那一行多一格）
Review: R1（Engine C 是可重建的 A2 projection；只呼叫既有 backfill，不改 PIT 邏輯；不命中 R2）
Case: #81 第 2 次（10-18 [796]–[799] 環宇、光環、台玻、金居、富喬：月營收 0 個月、季報股數 0 季；#39 10-07 波若威等四檔）
```

**現況：** `crons/daily_task.py` 沒有月營收或股數步驟（唯一的 Engine C 步驟是 `history_backfill --incremental`）——照 OPERATIONS「台股月營收與重大訊息」節，月營收刻意是互動式入口。心跳 `_monthly_revenue_line` 已印「N 檔一筆都沒有」（2026-10-21：26/26 有值），但「有值、湊不滿三年窗」不印（10-18 回補 40 個月後仍只有 857 天，要 54 個月）。
**做什麼：** ①（Q1 A）`complete_registry_batch` 與 `complete_ra_admission` 寫完名冊後，對本次新增、交易所是台股的條目跑 `engine_c.monthly_revenue.backfill(months=54, tickers=…)` 與 `engine_c.tw_share_capital` 回補 20 季；失敗不擋名冊寫入，收據逐檔寫補到幾個月、哪幾檔沒補到（INV-3）。②心跳的月營收與季報股數兩行各多一格「三年窗不滿 N 檔」。③鉤子依交易所後綴分派，日韓（plan `2026-10-21-002`）落地時接同一點；本 Step 只做台股。
**四問：** ①根除（新登記不再缺歷史）＋顯形（不滿三年窗常駐計數）。②程式。③加一個副作用——沒有東西可拿掉，現在是「要人記得補」。④最先壞的：名冊寫入要打外部（MOPS）——complete 原本不打網路；看過：兩條 complete 都只在互動 session 跑。
**驗收：** ①回放：10-18 五檔若在 complete 當下補，第一份敘事的 `answers` 兩題（已定價、出現在數字裡）不是 `unmeasurable`（敘事 ledger：拿五檔第一版的 answers 對照）；②機制：測試＋變異（拿掉鉤子 → 紅；回補失敗時名冊照寫、收據列名 → 綠）。
**前置：** 無。

## E2 例行重訊叫醒的反證照主旨分組（#63）

```
INTAKE
Zoom: Z2（語意等待醒來後的判定呈現；Q2 選 B 才動喚醒條件）
Review: R1（等待 registry 是 pq1 狀態，不寫 authority）
Case: #63 3 次（10-15 一次判 8 條；10-16 台達法說時間、華星光注意交易叫醒 7 條；10-17 奇鋐、富世達內線澄清一則叫醒 14 條——全部判無關）
```

**現況：** `engine_b/semantic_prescreen.py`、`engine_b/event_watch.py` 10-15 之後沒有 commit。
**做什麼（Q2 A）：** MOPS 重訊在 harvest 已存主旨（`announcements_to_leads`）；醒來時以封閉字彙附主旨類別（注意交易資訊／法說會召開／內線或澄清／子公司間交易／取得或處分資產／其他），drain 的判定區塊照（公司、類別）分組、一組判一次；「只標旗不判定」不變。
**四問：** ①顯形（A 不減少叫醒、只減少判定次數）。②程式。③加一個分類——讀的是重訊自己的主旨，不新造資料；B 才是拿掉叫醒。④最先壞：主旨寫法不一（「澄清」「說明」）——未知一律落「其他」、單獨判（INV-3）。
**驗收：** 等待 registry：回放 10-15～10-17 三輪 29 次叫醒 → 判定次數＝組數（10-17 那一則 14 條 → 1 組）；量：每週語意判定裡「例行重訊類別」的占比（registry＋drain 收據；上線兩週後出第一個值）。

**落地（2026-10-21）：** `engine_b/announcement_category.py`（六類封閉字彙、從重訊自己的主旨判、認不得落「其他」；「取得或處分資產」不在例行）；語意 watch 被重訊叫醒時 `woken_by.announcement` 附類別；`semantic-queue` 照（公司、類別）分組、每組印一條判定命令；`judge` 一次收一組（有一筆不合法整組不寫）；判定記 `announcement_category`；`counters` 多印「近 7 天語意判定裡例行類別幾筆」（兩週後出第一個值）。喚醒條件一字不動。回放 10-15～10-17：叫醒 32 次 → 8 組（例行三類 23 次）；計畫寫的「10-17 那一則 14 條 → 1 組」實際是奇鋐 10 條＋富世達 4 條兩家公司，照（公司、類別）是 2 組。

## E3 讀圖 digest 收 develops／is_variant_of（#87）

```
INTAKE
Zoom: Z2（讀圖快照與 result_digest 的內容改變——所有現行讀圖的比對基準）
Review: R1（A3 讀圖的 staleness；不寫 authority）
Case: #87 3 次（穩懋 develops 6 吋 InP、[789] cowos is_variant_of 先進封裝、[815] Nokia develops 6 吋 InP——入圖後讀圖都沒變 stale）
```

**現況：** `alpha/structure_reading/staleness.py`、`query/structure.py` 自 2026-10-03 沒有 commit。
**做什麼：** 讀圖快照與 digest 收「指向本節點的 develops／is_variant_of 邊」（供給側角度多一類，或第六個角度 `developers`）；新增一家開發者＝供給側變化，分級照 `CHANGE_KINDS`（預設 high）。升版方式（預設）：digest 帶算法版本；升版當天舊讀圖若只有「算法升版」的差異，印「digest 升版、內容未變」、不進該重讀——沿用 E4 的同一個出口。
**四問：** ①根除。②程式。③加一類邊進快照——沒有可拿的；這是對稱面（L17 第三問：供給側收 supplies_to 卻不收 develops）。④最先壞：全部現行讀圖的 result_digest 會一次改變——所以要版本化；回放先數「升版當天會被標該重讀的份數」，必須只等於真的有新 develops／is_variant_of 的那幾份。
**驗收：** 讀圖：回放 [815]、穩懋 develops（6 吋 InP 讀圖）、[789]（先進封裝讀圖）→ 3/3 印 stale；升版當天「該重讀」只多出有新邊的那幾份（逐份列）。
**前置：** E4。

**實作前的發現（2026-10-21 唯讀實測）：** 現行 58 份讀圖裡 15 個節點有指向它的 develops／is_variant_of 邊（共 25 條）；舊讀圖快照沒有這一類，升版當天若直接比，15 份全會被標 stale——所以「只多出有新邊的那幾份」需要每條邊的**入圖時間**。圖上的 canonical 邊不帶 `source_doc_id`（來源要經 `query.bottleneck.fetch_assertions`），而那裡只帶 `published_at`——那是世界何時知道，不是我們何時入圖，用它會把「舊文件、新入圖」的 [815] 那一種判成早就知道。做法改成：`fetch_assertions` 多帶 SourceDoc 的 `retrieved_at`，舊讀圖（快照沒有 developers 這一類）只把**最早取得日晚於讀圖日**的邊算新增、其餘印「digest 升版、內容未變」；新讀圖照常存這一類。驗收不變。
**落地（2026-10-21）：** `query.structure` 第六個角度 `developers`（指向本節點的 develops／is_variant_of；空的不進 digest——沒有這類邊的節點 digest 一位元不變）；`CanonicalEdge.first_retrieved`（引用文件最早的 retrieved_at，不進 digest）；`staleness`：快照沒有這一類的舊讀圖只把取得日晚於讀圖日的邊算 `developer_added`（high），其餘 `current`＋「digest 升版、內容未變」（取得日不明照已在算並計數）。真資料：現行 58 份讀圖升版當天該重讀 **0**、「digest 升版」14 份（都在開發者邊入圖後才重讀過）；回放 [815] Nokia → 6 吋 InP 10-07、10-17 兩版 stale ✓；[789] cowos → 先進封裝 10-08、10-17 兩版 stale ✓；穩懋 develops 10-04 入圖（assertion updated_at 10-04），早於 6 吋 InP 第一份讀圖（10-07）——照「只算讀圖之後的新邊」它對任何一版都不是新邊，它的問題是從沒出現在任何快照裡，現在由那 14 份「digest 升版」的提示看得見。已知盲點：文件早取得、晚入圖的邊會被當成已在（取得日≤入圖日；assertion 的 updated_at 會被遷移改寫，不拿來用）。

## E4 只因同義節點合併而換 id，不算讀圖變動（#75）

```
INTAKE
Zoom: Z1（staleness 多讀一份已核准的 registry；輸出多一個狀態說明）
Review: R1
Case: #75 2 次（10-17 [776][777][778] 合併：4 份讀圖換版＋10 份敘事換騎，零判讀改變；10-07 [730] FAU：1＋2）
```

**現況：** staleness.py 不讀 `config/entity_aliases.json`（grep 0）。另：7.0g 之後「非倍率」的 19 個新版本裡 14 個是這種換騎（3105.TWO、LITE 10-17～10-19 各 4 版）。
**做什麼：** 比對前用 entity_aliases（只取有 approval_receipt 的）把讀圖快照裡的別名 id 換成 canonical；換完沒差異 → 印「只有合併換名」、不進該重讀；digest 那一半一起（用換名後重算的 digest 比，避免落到「digest 變了但逐項比對找不出差異」那一支）。讀圖不換版，敘事就不必換騎。
**四問：** ①根除。②程式。③加一個唯讀讀取，拿掉一類人工換版。④最先壞：合併同時帶進真的新邊的讀圖（外部光源、6 吋 InP）——要照舊標；回放有這兩份。
**驗收：** 讀圖：回放 10-17 四份舊讀圖（sr_9aa50cb6a36e4822、sr_b3bc2d7d852c3f3c、sr_d6819880c609bef7、sr_6dac58d92d454708）對合併後的圖 → 4/4 不進該重讀；FAU sr_8c9292bfbc2b492a 對 [730] 後的圖同樣；外部光源、6 吋 InP 照舊標。敘事 ledger：之後每次合併，「內容一字不改」的換騎版本 0（10-17 是 10、10-07 是 2）。
**落地（2026-10-21）與兩處偏差：** `staleness.canonical_snapshot`＋`reading_status(aliases=)`（純函式，對照表由 provider 注入）；讀圖所在節點本身被併掉時查 canonical 那一個。①對照表用 `identity.entities` 驗證過的全部條目——`name_identical` 是機械可驗、名冊規則本來就直接收（沒有 receipt 欄位），語意合併的 receipt 由載入器強制；計畫寫的「只取有 approval_receipt 的」會把機械那兩筆排除，沒有理由。②回放只能對**今天的圖**（合併當下的圖不在手上）：5 份舊讀圖由換名造成的差異 5/5 消失；2/5（sr_9aa50cb6a36e4822、sr_6dac58d92d454708）變 current；另 3 份剩下的差異全是合併之後才入圖的真邊（cpo→tia_driver、10-18 onboard 的光環與 Ligent、FAU→scale_out_cpo），照舊標——正是「真的新邊照舊標」那一半。現行 58 份讀圖換名前後狀態 0 份改變（都已在合併後重讀過）。敘事那一個驗收數字（合併後內容不改的換騎版本＝0）要等下一次合併才量得到。

## E5 共用別名進走圖第 9 型＋入圖乾跑提示（#79＋#59）

```
INTAKE
Zoom: Z2（`MATCH_RULES` 是封閉字彙；守門測試要改寫）
Review: R1（唯讀偵測；只印不擋）
Case: #79 第 2 次（MRM 兩節點；全圖 13 對共用別名，現行規則抓 3、漏 10）；#59 第 2 次（NPO 兩節點 [752]、FAU [730]）
```

**現況：** `query/duplicate_nodes.py` 第 64 行 `MATCH_RULES = ("id_token_subset", "name_identical")`；`loader/merge_side_effects.py` 只做單一節點的別名聯集，不比跨節點。
**做什麼：** ①`MATCH_RULES` 加 `alias_shared`（正規化——不分大小寫、去空白與連字號——後 aliases∪name 交集非空）；守門測試 `test_the_rejected_third_rule_never_comes_back` 改成「被否決的 off-by-one 規則不得回來」（它原本擋的是 09-18 那條單 token 全配的規則，不是別名）。②入圖乾跑對本包新技術節點跑同一個比對，只印不擋（同一個函式，不另寫一份）。③資料那一半（別名污染：`tech:cpo` 掛「NPO」、`tech:ai_switch` 掛 scale-out／scale-up network）是圖遷移，走研究＋pq2，不在本 Step。
**四問：** ①顯形。②程式。③加一條規則——兩條機械規則看不見「名字不同、別名相同」。④最先壞：污染對會一起冒出來（#79 的 10 對混了真重複、污染、上下位三種）——所以只能是提示。
**驗收：** 走圖第 9 型：全圖回放新增恰好 #79 列的 10 對，09-18 的 `prod:reliant`／`mat:photoresist` 仍不配；入圖乾跑：回放 [752] 之前的 NPO 包（`tech:npo` vs `tech:near_package_optics`）印出提示。

**落地（2026-10-21）：** `query/duplicate_nodes.py` 第三條規則 `alias_shared`（正規化去空白連字號底線、不分大小寫；一方別名＝另一方名字或別名），`match_rules` 一支給候選對與入圖乾跑共用；守門測試改守「off-by-one 那條不得回來」。入圖乾跑（`merge_side_effects.side_effects`）對本包新的非公司節點查圖上名字與別名、跑同一支比對，只印「可能與圖上既有節點是同一個」，不算副作用、不擋。回放全圖：候選 36 對、含別名 14、只靠別名 11（計畫寫 #79 的 10 對；混了 `tech:cpo` 掛「NPO」等別名污染——③資料那一半走研究＋pq2）；`prod:reliant`／`mat:photoresist` 仍不配。

## E6 券商內容不進公開 repo（#90；Q3）

```
INTAKE
Zoom: Z2（RA draft 多一欄；公開入圖報告與私有 packet 分流）
Review: R2（security：公開 repo；Phase 7 Q7 常規 opt-in，窄範圍審查者）
Case: #90 第 2 次（#57 [750]；10-20 [823] 入圖報告引元大兩句、10-17 ra_d4b8… 一個份額估計）
```

**現況：** tests、`intake/`、`scripts/prepare_research_action.py` 對「凱基｜元大｜Yuanta｜KGI」grep 0——沒有守門。`git grep -E "凱基|元大" -- library/intake`：5 份 6 處，含券商內容 2 份（就是 #90 那兩份，使用者 10-20 選 c 保留），其餘 3 份只點名 lead 的來源報告。
**做什麼（Q3 A）：** RA draft 多一個選填欄 `private_context[]`；prepare 存到 `library/private/`（同 action id），決策區塊與私有 packet 照印，公開入圖報告只印段數；digest 收它的雜湊不收原文（核准的仍是同一份內容）；lead-intake／source-trace SKILL 寫「券商讀到的只寫這一欄」。
**四問：** ①根除（結構上就不會進公開檔）。②程式＋SKILL 一句。③加一欄——公開報告三段本來就沒有私有出口。④最先壞：apply 的雜湊收據與公開報告的對應——私有欄的雜湊要進收據、原文不進。
**驗收：** 機制：測試＋變異（`private_context` 不出現在公開報告、出現在決策區塊；拿掉分流 → 紅）；量：之後新增入圖報告裡的券商內容句（`git grep` 後人工判，點名來源不算），基準今天新增 0。

## E7 更正走廊乾跑列出 claim 改句（#85②）

```
INTAKE
Zoom: Z1（乾跑報告多一欄；不碰 apply 與 gate）
Review: R1
Case: #85② 2 次（10-19 GF 更正包 [812]、華明更正包 [814] 乾跑都只印「0 claims」，loader 其實會 SET 覆寫 statement）
```

**現況：** `loader/merge_side_effects.py` 只比節點與 SourceDoc 欄位；10-19 之後沒有 commit。
**做什麼：** `fetch_graph_state` 多取本包 claim id 的 statement／disproof／confidence；`compute_side_effects` 多 `claim_overwrites`；render 印「Claim X 的 statement 會被改：舊 → 新」（約 20 行，超過 L17 十行）。
**驗收：** 圖：回放 [812]、[814] 草稿乾跑各印出 ≥1 筆 claim 改句，且等於 apply 後圖上 statement 實際改變的 claim；變異：拿掉比對 → 紅。

**落地（2026-10-21）：** `loader/merge_side_effects.py` 多查本包 claim（id 用 loader 同一個 `evidence_id` 前綴）的 statement／disproof_condition／confidence，`claim_overwrites` 逐欄列「Claim X 的 statement 會被改：舊 → 新」，`has_side_effects` 算它。回放：以 git 前一版抽取檔當圖上現值——[812] 列出 2 筆（statement、disproof_condition）、[814] 1 筆（statement），都等於現在圖上 statement 已是更正版的那一個 claim。

## E8 輪詢不掛已取得的同一份申報；終局 lead 名下等待收掉（#62）

```
INTAKE
Zoom: Z2（T2 輪詢掛命中的條件；`lead_closed` 收法的認定擴大）
Review: R1
Case: #62 3 次（ew_0020：10-15 8-K 主文、10-16 同 accession 的 Ex 99.1、10-19 10-Q 0001045810-26-000075——都是 lead_2f5aebfb 已取得或已查過的）
```

**現況：** `engine_b/watch_poll.py`、`engine_b/event_watch.py` 10-15 之後沒有 commit；`ORPHAN_CLOSE_KINDS = ("pq2_item_gone", "lead_closed")`，`lead_closed` 只認 applied／no-go（event_watch.py 第 638 行）。
**做什麼：** ①輪詢命中的申報與 lead 的 `trace_original_url`、`trace_attempts_ref` 同一個 accession（含同 accession 的附件）→ 不掛命中、記「已取得」；②lead 停在終局 trace_status 且觸發寫「無」時，名下追源型等待以 `lead_closed` 收掉並留理由（擴 `lead_closed` 的認定，不新增 close kind）。
**驗收：** 等待 registry：回放 ew_0020 三次 → 0 次掛命中；「lead 已終局、名下仍 active 的追源等待」上線前先量現值 → 0。

**落地（2026-10-21）：** ①`watch_poll.apply` 對有 `wake_lead` 的等待，命中網址的 SEC accession（`…-26-000075` 或路徑 18 碼）若在 lead 的 `trace_original_url`／`trace_attempts_ref`／`primary_url` 寫過 → 拒收 `already_obtained`（同 accession 的附件一併）；②`todo._close_orphaned_waits`：lead 停放、trace_status 終局、`trace_trigger_kind=none` → 以 `lead_closed` 收（擴認定、不新增收法）。回放：ew_0020 三筆命中 3/3 會被擋；上線前「lead 已終局且明示不等、名下仍 active 的追源等待」現值 **5**（ew_0020 contradicts、ew_0490／0498／0526／0578 original_obtained），下一次 `todo sync` 收成 0。

## E9 證據等級認得關係人自述與買方自述（#10＋#11）

```
INTAKE
Zoom: Z2（證據等級封閉字彙多兩個標籤；分類器多讀持股邊）
Review: R1（讀時分類，不搬資料、不放寬 gate）
Case: #10 3 次（[691] JFE→合資、[690] Ecolab→CoolIT、[695] 富世達→奇鋐）；#11 6 次（[689] IREN、[694] NVIDIA MGX、[721] Google CDU、[766] NVIDIA、[771] Meta、[772] Coherent）
```

**現況：** `query/origin_resolution.py` 自 10-03 沒有 commit；`query/bottleneck.py` 第 170–177 行 `EVIDENCE_LABEL` 只有「供應商自報」一個自述標籤。
**做什麼：** ①corroboration 讀圖上 origin 與主詞之間的 `acquired`／`invests_in` 邊（任一方向、或同一母公司）→ 降為「關係人自述」；②`depends_on`／`constrained_by` 這類主詞是需求方的邊，origin＝主詞時標「買方自述」（filing 另標），不印「供應商自報」。
**四問：** ④最先壞：讀圖 staleness 對證據等級變化的分級——改判會讓多份讀圖一次出現 evidence 變化；回放先數它們落在 `stale_low` 還是 `stale`。
**驗收：** 圖（讀時標籤）：[690] 兩條、[691] 一條由外部印證改判關係人自述；[689] 兩條、[694] 三條、[721] 一條、[766] 兩條、[771] 四條、[772] 一條由「供應商自報」改標買方自述；讀圖：因此狀態改變的讀圖逐份列（不自動重讀）；變異：拿掉判定 → 回到原標籤。

## E10 覆蓋家數取三者最大（#64；Q4）

```
INTAKE
Zoom: Z2（邊緣判定的取數口徑；`config/alpha_screen.json` 門檻是用舊口徑量的斷點）
Review: R1
Case: #64 2 次（10-16 五檔：002472.SZ 8→19、002837.SZ 2→13、688017.SS 5→14、SOI.PA 6→19、XPEV 3→25；10-17 0522.HK 一天內 18→7 翻盤）
```

**現況：** `alpha/providers/market_normalization.py::analyst_count`（第 87–96 行）仍只取 `metric='eps' AND relative_label='0y'`；10-16 之後沒有 commit。
**驗收：** 敘事：新口徑下翻盤的檔各有新版或不換版理由（敘事 ledger）；機制：邊緣判定附三個家數與各自來源（候選板那一列）。

## E11 「供給側多一家」不再是機械反證觸發（#68）

```
INTAKE
Zoom: Z2（`DISPROOF_KINDS` 是封閉集合；研究 skill 一句）
Review: R1（拿掉一個觸發，補償控制見四問③）
Case: #68 2 次（10-08 [751] Freiberger、10-17 [760] 雲南鍺業——都是列舉補齊，觸發 InP 基板讀圖反證①）
```

**現況：** `alpha/structure_reading/staleness.py` 第 88 行 `DISPROOF_KINDS = {"counter_path", "supply_added"}`；現行讀圖（ledger 最新）68 份裡寫「圖上供給側第 N 家」型條件的 2 條：InP 基板 sr_e8cab2cad68816c0 ①、CW DFB sr_def7cb705477572e ①；另 6 條寫「一手點名第 N 家」，不受影響。
**做什麼：** ①`supply_added` 留在變化分級（照舊讓讀圖該重讀），從 `DISPROOF_KINDS` 拿掉——家數會隨我們多讀一份文件單調上升（AGENTS 失焦指標判別法）；②`skills/research-drain/SKILL.md` 段 4 ④「變化若被標成 disproof_trigger（供給側多一家／反向路徑新增）」改成只剩反向路徑，並加一句：讀圖反證寫新增產能或新進者的一手（擴產公告、首次量產），不寫「圖上第 N 家」；③上面 2 條在下次換版時改寫（研究，不在本 Step）。
**四問：** ③拿掉一個觸發；補償控制（L15）：`supply_added` 仍讓讀圖該重讀，人讀到真的新進者照讀圖反證處置。
**驗收：** 讀圖：回放 [751]、[760] → 不標 disproof_trigger、仍標該重讀；現行讀圖「圖上第 N 家」型反證 2 → 0（換版時）。

**落地（2026-10-21）：** `DISPROOF_KINDS` 只剩 `counter_path`；`supply_added` 照舊 high、照舊讓讀圖該重讀（補償控制）；`skills/research-drain/SKILL.md` 段 4 ④改成只剩反向路徑，並寫「讀圖反證寫新增產能或新進者的一手，不寫圖上第 N 家」。回放 InP 基板：[751] Freiberger、[760] 雲南鍺業之前的 8 份讀圖對現在的圖全部 stale、該重讀、`disproof_triggers` 0。③（InP 基板 sr_e8cab2cad68816c0 ①、CW DFB sr_def7cb705477572e ①）是研究，下次換版改寫。

## E12 證據清單列得出敘事的 library/raw 引用（#50）

```
INTAKE
Zoom: Z2（A3 研究判斷的引用範圍——`EVIDENCE_SCOPE` 契約與 packet 指示）
Review: R1
Case: #50 2 次（10-08 KLIC 等 6 份短檢查敘事；回看 10-07 XFAB.PA、6481.T、XPEV 同形）
```

**現況：** `alpha/models/session_assessor.py` 第 181 行 `EVIDENCE_SCOPE.in_scope_prefixes` 只有 graph://edge／source／claim 與 engine_c 快照；`briefing/analyst_view/compose.py::_evidence_for` 只查 evidence index；10-08 之後兩檔都沒有 commit。寫入端其實收 `library/raw/<檔名>` 引用。
**做什麼：** 證據清單列得出敘事引用的 library/raw 節錄（同層說明 `raw:<檔名>` 的規則：寫入時檢查指得回、呈現時列出）；packet 指示改成與寫入端一致。
**驗收：** 敘事：短檢查敘事（ENS、VSH、KLIC、NVTS、POWI、LPK.DE、XFAB.PA、6481.T、XPEV）各格引用在證據清單列得出的比例——上線前先量現值，目標全部。

## E13 ROADMAP 改寫時待決題不得消失＋「刻意不併／留待」結構化（#60）

```
INTAKE
Zoom: Z2（③動 `config/entity_aliases.json` 條目的形狀）
Review: R1
Case: #60 3 例（「人工觀測的取代鏈」懸空 22 天；`duplicate_nodes` 檔頭指向已被拿掉的列；[613]／[614] 後的兩條 is_variant_of 待判只留在封存檔）
```

**現況：** tests 裡的「ROADMAP「…」」只出現在註解，沒有守門。
**做什麼：** ①測試：程式、skill、測試裡的「ROADMAP「X」」對不到現行列時，`docs/archive/roadmap-backlog-log.md` 那一列要有完成或退役標記，否則紅；②ROADMAP 改寫的檢查命令（手動跑，不進 hook——ROADMAP「不做 ROADMAP 驗收 linter」那一句照守）：對 git 前一版做「等使用者決定且沒有完成標記的列」差集，新版或 Phase plan 待決清單找不到的列出來；③（plan §14 #19）名冊 note 的「刻意不併」與「留待研究判斷」改成條目上的結構化欄位，走圖第 9 型只排除「刻意不併」。
**驗收：** 機制：①的測試（今天會紅 1 處：`query/duplicate_nodes.py` 檔頭）；量：懸空引用 1 → 0；走圖第 9 型：`tech:dram`／`tech:dram_technology`（留待）回到問句。

## E14 改動後自動重啟 serve（#40；Q5，推薦不做）

選 A 才做：materialize 收尾偵測長駐 `webapp serve`（8790）在跑就重啟並驗 `/api/v1/health` 的 `code.stale=false`；動 daily 的 executable surface，同一個 change 做 sandbox impact review。

## E15 追蹤表 paper lane 依現行狀態分組印（7.5 前置）

```
INTAKE
Zoom: Z1（`lane_summary` 多一個鍵；既有鍵不變）
Review: R1
Case: 不是 failure log 條目——A12 盤點 7.5 報告寫法時發現：10-20 撤回的非倍率敘事仍以 7.0g 前的「不要」當 paper 錨點，混在聚合裡
```

**現況：** `scripts/outcome_if_settled_today.py::paper_lane_plan` 錨點＝每檔最早一筆未撤回 v2；`lane_summary`（第 781 行）的等權、power-law、組超額對 paper 全部列一起算。2026-10-21：paper 114 列，現行狀態 pass 44、**retracted 41**、missing 26、priced_wait 3。表格逐列已印「當時→現行」（第 1495 行），聚合行沒有分。
**做什麼（最小改法）：** `lane_summary` 對 paper lane 多一個鍵 `by_current_state`：{狀態: {n, aggregate: `equal_weight_aggregate(該組)`, reached_2x_ever: `power_law_aggregate(該組)["reached_2x_ever"]`}}；`render_lanes` 在 paper 的等權那一行之後每組印一行。`lanes_payload` 吃 `lane_summary`，聚合檔與 APP artifact 自動多這個鍵（加鍵、不改既有鍵；APP 畫面不動）。`tests/test_measurement_lanes.py` 加一條（拿掉分組 → 紅）。
**驗收：** 追蹤表：paper lane 印各組的 n 與等權，各組 n 加總＝當天 paper 列數。

## 2. 不做

- #96 的修法（先由主 session 確認併回 #1）；別名污染、MP／HDS 供貨邊等資料面（研究＋pq2）；AGENTS 任何一句；tracked 名單。
- 不為了湊進度把 E14 做掉：它不擋研究，推薦不做。

## 3. 與 Phase 7 plan 的關係

本檔是 plan `2026-10-04-001` §0.4 A12 的產出；failure log 各條末欄改指到本檔。7.5 檢查點 §11 第 3 項照 A5 只列「這一期提過、做過的開發項」。
