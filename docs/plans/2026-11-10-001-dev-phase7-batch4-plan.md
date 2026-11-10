# 開發：Phase 7 批次四——failure log 過 gate 的十項＋#118 租賃那一半（2026-11-10）

> 日期 2026-11-10｜狀態：**APPROVED**（使用者 2026-11-10「#118 只做租賃那一半；月營收量測順延到 12 月；開發 #142 #148 #147 #150 #152
> #140 #32 #139 #141 #143 照推薦做」＝11-10 收尾回覆「要你決定」第 1、3 項照推薦；第 2 項月營收量測順延是研究登記，已寫進
> `docs/reports/phase7/cases.md` 處置紀錄，不在本檔）｜載體：本檔＋ROADMAP（開發項不走 pq2）。
> **順序：** A #118 負債燈只算借款 → B #140 錯的訊號對反證 → C #150 裁決時點過了提醒換版 → D #143 新進者漏列提醒 →
> E #152 研究讀燈遮價格 → F #141 私有券商報告索引 → G #32＋#139 寫入時列自家庫一手 → H #148 MOPS 重訊回補 →
> I #142 台股財報上架當 lead、J #147 IR／E-IR 一手 feed——**I、J 動手前先問**：plan `2026-11-02-001` §5「12-22 前不開新 feed」，
> I、J 都是新 feed，與那一條衝突（H 是既有重訊 feed 的回補，不算新 feed）。撞到要使用者選的就停下問。
> **不碰：** 四個人工 gate 的語意；可開起始門的條目（A 只換會死嗎那一盞的輸入口徑，使用者 11-10 定）；歸零燈的其他三盞與 #118 現金流
> 那兩半（11-07 使用者「先記下」照舊）；AGENTS 判準句；ROADMAP 的 Phase／Step 定義。

## 0. 進度

| # | failure log | 做什麼（一句） | Zoom／Review | 狀態 |
|---|---|---|---|---|
| A | #118（租賃那一半） | 負債燈比借款（總債扣掉同一季的租賃負債），租賃另列一行 | Z2（方向使用者已選）／R1（R2 見 A 節末） | ✅ 11-10（負債燈翻色 7 檔、全往綠；會死嗎最差紅 → 黃 3 檔：IQE.L、3234.TWO、BW） |
| B | #140 | 敘事「錯的訊號」每一條標它對應的反證編號，寫入端核 | Z2／R1 | ✅ 11-10（回放 AXTI 11-07 版印出「通美融資沒能交割」；現行 93 份會拒收 0、換版時提醒 21） |
| C | #150 | 敘事的裁決時點過了（或引用的文件已到）提醒換版、候選板計數 | Z2／R1 | ✅ 11-10（候選板點名 17 檔：申報 7、日期 7、佔位字 3；逐一看過都是真的過了；11-11 起再多 8） |
| D | #143 | 讀圖條件寫「新進者」而圖上同一節點的公司不在 entities，收據印出 | Z1／R1 | ✅ 11-10（回放 275 份讀圖印出 3 筆，全是 CW DFB 三版漏了環宇） |
| E | #152 | 研究讀燈與稽核區的唯讀出口遮價格欄 | Z2／R1 | ✅ 11-10（Q3W 名單 28 檔預設輸出的價格欄 0 個、原樣 339 個，四盞燈照印） |
| F | #141 | 私有券商報告存 sidecar 索引（不抄內容），drain 讀某檔時列出點名它的報告 | — | ○ |
| G | #32＋#139 | 敘事／讀圖寫入收據列出同一公司自家庫已有、沒引用的一手（只印不擋） | — | ○ |
| H | #148 | MOPS 重訊補抓前幾天、新進範圍回補 90 天 | — | ○ |
| I | #142 | 有現行敘事的台股每日列 `t57sb01` 財報清單、新上架出 lead | — | ⏸ 先問（新 feed） |
| J | #147 | 有現行敘事公司的 IR 新聞頁／E-IR 當 harvest 一手 feed | — | ⏸ 先問（新 feed） |

## A 負債燈只算借款、租賃另列（#118 租賃那一半）

```
INTAKE
Zoom: Z2（改既有輸出的語意：負債燈比的數由總債換成借款；Engine C financial_snapshots 新欄位＋遷移）——方向使用者 11-10 已選，
      plan 裡沒有要使用者再選的題，照常規推進授權做
Review: R1＋R2 提出（命中「financial identity・PIT・units」：租賃取自另一張表，要與總債同一季、同一份來源）
Case: failure log #118 第 3 次（10-31 SLNG、11-06 CECO 是現金流那兩半；11-10 IQE.L 是第一個會翻色的 case，翻的是總債口徑）
```

**現況（2026-11-10 唯讀）：** `alpha/wipeout.py::debt_flag` 比「現金 ≥ 總債」；總債＝Engine C 快照 `total_debt`＝yfinance `info.totalDebt`，
含 IFRS 16／ASC 842 的租賃負債——IQE.L 2026-06-30 5,394 萬英鎊＝借款 1,141 萬＋租賃 4,253 萬（季報表 Total Debt 與 info 逐位相同）；
3234.TWO、BW、MXL 同樣含。人工觀測 `runway_inputs` 照抄報表總債（KSHINTL.NS 9 月底那筆含租賃）。歷史表 `fundamental_history.total_debt`
（us-gaap LongTermDebt／ifrs-full Borrowings）本來就不含租賃——兩條路口徑不一。改動前 197 檔負債燈：綠 92、黃 86、紅 15、灰 4。

**做什麼：**
①Engine C `financial_snapshots.lease_liabilities`（SQLite ALTER＋PG 遷移 `20261110_add_lease_liabilities.sql`；既有列留 NULL、不回填）。
ETL 讀 `quarterly_balance_sheet` 裡**與 `info.mostRecentQuarter` 同一季**那一欄的 `Capital Lease Obligations`；沒有合計列就把長短期兩列加總；
租賃列都沒值、同一欄有 Total Debt＝量到的 0；那一季的欄不在或抓取失敗＝NULL（WARN 一行）。
②`shared.runway.derive_runway`、人工觀測 `runway_inputs` 選填 `lease_liabilities`——只跟同一份來源的總債走：跑道取自人工觀測時不拿快照的租賃補。
③`debt_flag` 比借款＝總債 − 租賃；分不出租賃（NULL、負值、非數值）照總債判、理由句補「總債可能含租約，分不出來」；租賃 > 總債（口徑對不上）不扣。
稽核層多兩格（其中租賃負債——另列，不算借款；借款——負債燈比的是這個）；口徑代碼 `lease_basis`（`separated`／`not_separated`／`inconsistent`）
只在 artifact。規則句寫明：IFRS 下租金本金列在籌資活動，營業現金流對 IFRS 公司偏樂觀——那是 #118 現金流那一半，未改。
④APP「數字與出處」兩個中文標籤；決定紀錄 §10.4 記使用者 11-10 的決定（會死嗎是起始門的一項，改它的輸入＝改門的輸入）。

**四問：** ①根除（燈不再把租約當成到期要還的借款）＋顯形（分不出租賃時理由句自己說，不是靜默照舊）。
②程式。③加一個輸入（租賃欄）。拿掉的方式——把總債換成歷史表的 Borrowings（本來就不含租賃）——不行：歷史表只有 SEC／DART／EDINET 申報人，
台股、英國、印度多數沒有，換了會讓一半以上的燈變灰；所以加欄，同一個 yfinance 來源、同一季。
④最先壞掉的那一筆：**info.totalDebt 不含租賃、季報表卻有租賃列**的公司——扣了會把借款低估、塗成綠。動手前看過四檔：IQE.L、BW、MXL
季報表 Total Debt＝info.totalDebt、且＝借款列＋租賃列；3234.TWO info 3.983 億 vs 季報表 3.999 億台幣（同一季、差 0.4%），季報表的 Total Debt
也＝借款＋租賃。全量 ETL 之後逐檔再核一次（落地段）。

**驗收（現有資料；不數 filter 通過檔數）：** 會死嗎稽核區的負債燈——①IQE.L 紅 → 綠、會死嗎最差色紅 → 黃（現金跑道照舊黃）；
②全量重算前後逐檔比對：翻色幾檔、翻成什麼、各自的租賃與借款（每一檔寫進落地段）；③分不出租賃的檔數與原因。
機制：`tests/test_wipeout_debt_leases.py`＋變異（燈比總債、租賃比總債大也扣、分不出當 0、人工觀測拿快照的租賃、跑道不帶租賃、
ETL 不比季別、量到的零當分不出、快照讀不到租賃欄、SQLite 不寫租賃——九個都要紅）。
**前置：** 無。

**落地（2026-11-10）：** `alpha/wipeout.py`（`_borrowings`、`LEASE_BASES`、規則句）；`engine_c/etl_yfinance.py`
（`lease_liabilities_from_balance_sheet`、`QUARTER_LABEL_DRIFT_DAYS`、`SAME_NUMBER_REL`）；`engine_c/db.py`＋`migrations/20261110_add_lease_liabilities.sql`；
`engine_c/checklist.py`（快照讀租賃欄、人工觀測選填、只跟同源走）；`shared/runway.py`；`webapp/static/app.js`（兩個標籤、代碼不上畫面）；
`config/engine_c_observation_fields.json`（runway_inputs 說明）；CONCEPTS「歸零旗標」；決定紀錄 §10.4。
**動手後才看到的（④ 去看那一筆）：** 第一版只認「季報表欄的日期＝`mostRecentQuarter`」，全量 ETL 197 檔有 50 檔對不上：①52／53 週制，
Yahoo 把季末標成月底（LITE 9-26 → 欄 9-30、AVGO 8-02 → 7-31）；②Yahoo 季報表晚 info 一季（AXTI、2455.TW、0522.HK、6501.T：info 已是第三季、
表只到第二季）；③KSHINTL.NS 的 `mostRecentQuarter` 寫 6 月，info 的總債其實是 3 月那一欄（逐位相同）。改成先找 Total Debt 同一個數的欄、
再找一週內的欄並核 info 的總債離「含租賃」比離「扣掉租賃」近——分不出 50 → 40；變異多三個（不找同一個數、不限一週、一週內不核含不含），12／12 變紅。
**真資料（11-10 全量 ETL 197/197，改動前後逐檔比對）：** 負債燈 綠 92 → 99、黃 86 → 82、紅 15 → 12、灰 4 → 4。翻色 7 檔、全往綠：
- IQE.L 紅 → 綠（現金 4,160 萬、總債 5,394 萬、其中租賃 4,253 萬、借款 1,141 萬英鎊；營業現金流 −392 萬）——會死嗎最差 紅 → 黃（現金跑道黃）
- 3234.TWO 紅 → 綠（現金 3.513 億、總債 3.983 億、租賃 0.996 億、借款 2.987 億台幣；營業現金流 −0.837 億）——最差 紅 → 黃
- BW 紅 → 綠（現金 3.140 億、總債 3.223 億、租賃 0.454 億、借款 2.768 億美元；營業現金流 −0.347 億）——最差 紅 → 黃（稀釋黃）
- 黃 → 綠：PSIX（借款 0.383 億 vs 現金 0.720 億美元）、SOI.PA（4.284 億 vs 5.631 億歐元）、BE（24.80 億 vs 24.87 億美元）、298040.KS
  （6,348 億 vs 6,360 億韓元）——後兩檔是幾乎打平的翻色，本業都賺錢，起始門不受影響
- 照舊紅：MXL、301511.SZ、688313.SS（扣掉租賃仍是借款比現金多、本業燒錢）
口徑：分得出 156、分不出 40（29 檔 Yahoo 季報表還沒上 info 那一季，日韓台印港居多，表更新後自己會好；11 檔取自人工觀測，那份文件沒寫租賃）、
口徑對不上 1（LIDR：租賃 122 萬 > 總債 82 萬，不扣）。**燈不改敘事宣告**：IQE.L、3234.TWO、BW 的敘事宣告缺 X（X＝會死嗎紅），
起始門這一項過了，要研究 session 換版重判。測試：`tests/test_wipeout_debt_leases.py`；相關 43 檔 746 passed。
**R2：** 命中「financial identity・PIT・units」（租賃取自另一張表），但上面三種對欄失敗都是自己量到、測試與變異都覆蓋，R2 不另開（記在本節，
使用者要的話再發 WORK_REQUEST）。

## B 錯的訊號逐條對反證（#140）

```
INTAKE
Zoom: Z2（敘事寫入契約多一條拒收）——格式沿用研究 session 已在用的寫法，沒有要使用者選的題
Review: R1（寫入端檢查；不寫任何 authority；六條 R2 trigger 都不命中）
Case: failure log #140（AXTI 11-07 版「通美融資沒能交割」沒有反證；三個 case，③⑦照原條）
```

**現況（2026-11-10 唯讀）：** 寫入端只核 `disproof[]` 的形狀；「錯的訊號」是「必須為真」格的自由文字。現行 93 份 v2 敘事（`select_brief`，
與候選板同一個讀法）：有「錯的訊號…：」段落 60 份（其中 41 份已自己用「（第 N 條）」或「讀圖第 N 條」標過至少一條）、沒有這個段落 33 份
（多半是「不要」寫成「要推翻它：…」）。⚠ 初版這裡寫「142 份」：計數腳本把最新一筆是撤回的公司也算進去（撤回前的舊版仍是 live 版本鏈的頭），
同日 C 節回放時對不上才發現，已改。

**做什麼：** ①`alpha.narrative.contracts.wrong_signal_items`：段落從「錯的訊號…：」起到括號外第一個「。」，括號外「；」切條，每條抓「第 N 條」；
「讀圖第 N 條」指讀圖自己的反證（那一條本來就有 watch），算有標、不核編號。②寫入端 ⑭（`wrong_signal_ref_problems`）：編號不在
1..len(disproof[]) → 拒收。③沒標的條目只印（寫入結果 `notices`），條目原文照列。④brief frame 與 research-drain「完整重讀」(3) 寫明格式。

**四問：** ①根除一半（指錯編號寫不進去）＋顯形（沒標的條目寫入當下印出來）。沒標的不擋：條目是從自由文字切出來的，切錯一條就會擋掉合法的
寫入（L16：不用會誤報的檢查擋）。②拒收是程式；沒標的靠寫的人看收據。③加一條檢查——拿掉的方式（錯的訊號整格改成結構化欄位、由 `disproof[]`
直接產生）要改敘事契約與首屏，超出本項。④最先壞掉的那一筆：現行敘事裡「第 N 條」指的是別的東西（法條、公告號）而 N 大於反證條數——
下次換版會被誤拒。看過：現行 93 份逐份跑 ⑭，會拒收 0 份。

**驗收（現有資料）：** 回放 AXTI 11-07 版（`ib_5a2398613c6e7598`）印出 5 條沒標的錯訊號，含「通美融資沒能交割、或三年後投資人行使贖回而 AXT
以增發股票代買」；現行 93 份：全部對到 39、換版時會提醒 21（含 AXTI 現行版 6／6 條沒標）、會拒收 0、沒有段落 33。
機制：`tests/test_wrong_signal_refs.py`＋變異 7／7 變紅（⑭ 沒接上寫入端、編號範圍不核、沒標的不印、讀圖第 N 條當沒標、括號裡的句號也停、
括號裡的分號也切、讀圖第 N 條當成 disproof 編號）。**前置：** 無。

## C 何時格的裁決點已過就叫重寫（#150）

```
INTAKE
Zoom: Z2（候選列 rewrite[] 多一種原因、整板清單多 kind=checkpoint、寫入收據多兩個只印的提示；artifact 加法欄、不升版）——
      沒有要使用者選的題
Review: R1（只讀、不寫任何 authority、不碰 gate；六條 R2 trigger 都不命中——見末段「名冊沒有歷史」）
Case: failure log #150（EFXT 10-31 重述版仍寫「等第三季 6-K」；PSIX 何時格 10-28 寫「第三季 10-Q」，10-Q 11-05 交、到 11-10 才換版）
```

**現況（2026-11-10 唯讀）：** 何時格是自由文字；`{next_checkpoint_date}` 每天換成名冊（`thesis/lifecycle.json`＋`catalyst_calendar.json`）上
≥ 今天的最早日子。judge 與 restates 都不看何時格。現行 93 份 v2 的何時格：寫了「寫下時還沒到」的日子 81 份，點名定期報告（「第三季 10-Q」）
22 份，把佔位字寫成某件事的日子（「{next_checkpoint_date} 的第三季財報」）8 份；EDGAR 監看的 lead 池裡，定期報告 82 筆、57 家公司。

**做什麼：** ①`alpha/narrative/checkpoints.py`（純函式）三種「過了」——日期：寫下那天還沒開始的最早一個日子，今天已過它的最後一天
（「約 11 月初」是 11-01～11-10 一段）；申報：點名的 10-Q／10-K／20-F／40-F 在寫下之後交了（`edgar:` 來源；8-K、6-K 有事就交，不收）；
佔位字：「{next_checkpoint_date} 的…」而寫下那天名冊上的下一個檢核點已過（單獨寫的佔位字每天自己換，不核）。「寫下那天」＝何時格這段
文字最早出現的那一版。②候選列 `rewrite[]`「何時格的裁決點已過：…」（首屏「裁決點過了」）與 `checkpoint_passed`；整板清單 kind=checkpoint；
counts.checkpoint_passed；⑤「敘事該重寫」點名；板上 `checkpoint_check` 說申報與佔位字兩半核了沒（讀不到＝沒核，不是沒過）。
③寫入收據兩個只印的提示：照抄的何時格裁決點已過；佔位字寫成某件事的日子。④research-drain ⓑ⁗ 寫處置（月營收寫「每月 10 日前」）。

**四問：** ①顯形（何時格仍是自由文字，不是根除）。②程式（每天重算）＋寫入收據。③加一個檢查。拿掉的方式——何時格改成結構化欄位
（日子＋文件）——要改敘事契約與首屏，超出本項；佔位字那一半是「拿掉」的方向：提示寫的人別把佔位字當某件事的日子。
④最先壞掉的那一筆（現行 93 份逐份印出抽到的日子與表單、明天會點名的逐檔看過）：(a) 3363.TWO 11-06「到 7 月 10 日 6 月營收公布為止」
指 2027 年，取最近一年會讀成今年已過——沒寫年份的改落在「往回 60 天、往前 305 天」的窗（讀錯的代價不對稱：過去的讀成明年只多一個排在
後面的日子）；(b) MOD 11-07「照前兩季 7 月底、11 月初的節奏」的「11 月初」是剛過的那一次——旬改成一段，開始那天晚於寫下那天才算在等；
(c) 6805.TW「去年是 11 月 4 日」讀成今年，點名仍對（那一格等的「11 月初的第三季財報」本來就過了）。

**驗收（現有資料；不數 filter 通過檔數）：** 候選板 11-10 點名 17 檔，逐檔看過都是真的過了——申報 7（AAON、AEHR、CLF、FORM、LIDR、OUST、
TTMI 的 10-Q 都在何時格寫下之後交了）、日期 7（6805.TW、COHU、HPS-A.TO、KLIC、MTRS.ST、VIAV、XFAB.PA）、佔位字 3（6268.T 上半期決算 10-30、
AAOI 第三季 11-06、HIMX 第三季 11-05——畫面原本印「最近的裁決點是（尚無）的第三季財報」）；11-11 起再多 8 檔（3081.TWO、3363.TWO、
4979.TWO 寫的「11 月 10 日前的 10 月營收」，5411.T、6324.T、ENS、SPB.TO、VSH 寫的「11 月上旬」）。回放：PSIX 10-31 那一版從 11-05 起
會被點名、到 11-10 換版；EFXT 那一例抓不到（6-K）。機制：`tests/test_narrative_checkpoints.py`＋變異 26／26 變紅（寫下當天也算在等、
寫下時已在那一旬裡也算在等、等最晚那一個才點名、沒寫年份的旬不收、月中國當日子、月底只算最後一天、寫下之前交的申報也算、6-K／8-K 也核、
指名抓的文件當申報、lead 池不濾表單、修正版不算同一種、單獨寫的佔位字也核、名冊上寫下之前的日子也算、沒寫年份取最近一年、何時格改過也往回
沿用、Q3-4 當日期、1-3 月與 3-5 GW 當日期、首屏字沒有這一種、候選列沒寫、整板清單沒有、讀不到的池當沒有申報、計數恆 0、⑤ 不點名、⑤ 不說
沒核、寫入端不印、寫入端不看照抄）。**前置：** 無。

**落地（2026-11-10）：** `alpha/narrative/checkpoints.py`；`alpha/providers/checkpoints.py`（lead 池的定期報告、名冊——候選板與寫入端共用）；
`alpha/providers/candidates.py`（`derive_row`、`board_rewrite`、`checkpoint_inputs`、`checkpoint_check`）；`alpha/candidates.py`（`REWRITE_WHY`、計數）；
`alpha/providers/briefs.py`（`WriteContext` 兩個輸入、`checkpoint_notices`）；`engine_b/todo_ledger.py`（⑤ 點名、沒核的註記、COVERAGE）；
`webapp/materialize.py`＋`webapp/contracts.py`（`checkpoint_check` 帶進 artifact、加法欄不升版）；research-drain ⓑ⁗。
**名冊沒有歷史：** 佔位字那一半拿**今天的**名冊回推「寫下那天它指哪一件」——名冊是現況檔，寫下之後改過（COHR 的六吋 InP 檢核點已不在名冊，
佔位字現在指的是第二季財報）就會讀錯；讀錯的方向是少點名或點錯是哪一件，只叫重寫、不寫任何判斷，所以不開 R2（INV-6 的「T 時刻我知道什麼」
只用在點名，不進任何 authority）。**sandbox：** 可執行面沒變（同一支 `python -m webapp materialize`，多讀兩份本機檔），不另寫 OPERATIONS 結論。

## D 讀圖反證寫「新進」卻漏列 develops 的公司（#143）

```
INTAKE
Zoom: Z1（讀圖寫入收據多一行只印的提示；不改契約、不改 watch 登記）
Review: R1（只讀；不寫任何 authority；六條 R2 trigger 都不命中）
Case: failure log #143（CW DFB 讀圖反證①寫「不在現有 14 家之內的新進者首次量產」，entities 只列 11 家——環宇不在其中）
```

**現況（2026-11-10 唯讀）：** 語意 watch 靠 `disproof[].entities` 比對文件主詞；寫入端不拿圖上同一層的 develops 去對「新進者」。
現行讀圖的反證寫「新進」的 4 條（HVLP 銅箔 #4、磷化銦基板 #1、極薄載體銅箔 #1、CW DFB #1），develops 漏列的只有 CW DFB（co:gcs_holdings）；
敘事寫「新進」的 5 條全都 `link_source_ref` 連到讀圖那一條（watch 是讀圖的），沒有自己登記的。

**做什麼：** `alpha/structure_reading/entrants.py`（純函式）：寫「新進」的那一條（新進者、新進入者、新進銅箔廠），列出快照 developers 角度
`develops` 這一層、不在那一條 entities 的公司；`alpha structure-reading --add` 寫入後印在收據（附 research ticker），**append 之前算好**——
算不成只印一行，不讓等待登記跟著沒跑。research-drain 段 4 ④ 補一句（寫「新進」的那一條把 develops 的公司列進 entities）。

**四問：** ①顯形（寫入當下點名漏了誰），不擋。②程式＋寫的人看收據。③加一個檢查。拿掉的方式——「新進者」的反證 watch 改成比對整層的
develops 公司、不靠 entities 列舉——要改 watch 的比對規則（`engine_b`），超出本項。④最先壞掉的那一筆：「第二家」「新廠」這種寫法講的是
買方的第二來源或既有廠擴產，若也算新進者，磷化銦、極薄銅箔那幾條會被誤點——比對字只認「新進」；看過現行 10 條候選寫法，只有 CW DFB 點名。
failure log 另外三個 case（8996.TW 條件點名的美超微、VNP.TO 的 York／Redwire／Solestial、SILEX.ST 的 Teledyne DALSA 不在名冊）是
「條件點名的公司不在名冊」，不是新進者——補名冊走 pq2，不在本項。

**驗收（現有資料）：** 回放全部 275 份讀圖紀錄（含已取代），印出 3 筆，全是 CW DFB 的三版（11-06、11-07×2；含現行 `sr_790f15cdae054ce3`），
點名的都是 co:gcs_holdings（4991.TWO）；其他 272 份不印。機制：`tests/test_reading_entrants.py`＋變異 8／8 變紅（is_variant_of 的節點也算、
沒寫新進也核、已列的也算漏、只認「新進者」三個字、編號從 0 起算、收據不附 ticker、收據不印、提示出錯就中斷寫入）。**前置：** 無。
**落地（2026-11-10）：** `alpha/structure_reading/entrants.py`；`alpha/providers/structure_readings.py::entrant_notices`；`alpha/cli.py`
（`cmd_structure_reading` 收據）；research-drain 段 4 ④。CW DFB 那一條要不要補環宇是研究判斷，照 failure log 原處置：下一版讀圖手動補
（換版代價是騎它的敘事換騎，不為這一條單獨換）。

## E 研究讀燈與讀敘事全文的出口遮價格欄（#152）

```
INTAKE
Zoom: Z2（三個互動出口的預設輸出變了：研究 packet、新命令 alpha lights、alpha brief --show；不碰 artifact、ledger、APP）
Review: R1（只讀；無人值守路徑不變；六條 R2 trigger 都不命中）
Case: failure log #152（11-10 一輪 Q3W 被動曝光 5 次：主 session 印 3163.TWO 稽核區看到「−32.9%」、子代理讀 2455.TW 時工具印出
      priced_at_write、C／H2 組讀 IQE.L 等個股頁物化檔帶到價格欄、兩組 grep 私有券商報告帶到目標價與收盤價）
```

**現況（2026-11-10 唯讀）：** 研究讀三題稽核區**沒有正式命令**——`library/private/tmp`、`wf_tmp` 裡各 session 自寫了十幾支
`three_questions_for(...)` dump 腳本，整份印出（含已定價三行的值與 detail）；讀上一版敘事全文沒有出口，直接開 ledger jsonl（帶
`priced_at_write`）；`python -m alpha research <T>` 的 packet 帶 `deterministic.market` 的市價與市值、`consensus` 的目標價與本益比；
個股頁物化檔光價格欄就有十幾處（走勢、收盤、市值、目標價、事件後報酬）。Q3W 名單 28 檔（#152 點名的四檔都在裡面）照原樣輸出三題，
價格欄 339 個。

**做什麼：** `alpha/price_mask.py`（純函式）——三題稽核區遮已定價每一行的值與 detail、稀釋那盞的市值兩個鍵；packet 遮市價、市值、
目標價、三個本益比類欄位、市場隱含兩欄；敘事紀錄遮 `priced_at_write`。遮掉印成「〔已遮：價格〕」（字串、不是 null——遮掉與缺席不同形，
L12）；缺席與理由照印（量不到是研究要知道的）；出現在數字裡了嗎整段照印。三個出口預設遮、加 `--prices` 拿原樣：新命令
`python -m alpha lights <T…>`（與候選板同一個串接點 `_wipeout_and_three_questions`、同一份 history_not_comparable，L16）、
`alpha research` 的 packet、`alpha brief <T> --show [<id>]`（讀一版全文）。research-drain ⓑ、起始門、ⓔ（Q3W）與派工提示改走這幾個出口。

**四問：** ①顯形＋拿掉資訊落差（遮在出口，不靠自報）。②程式（出口）＋寫的人（加 `--prices` 是有意識的動作）。③加一個出口、改兩個
出口的預設；拿掉的是「研究要看燈就得 dump 整份」那條路——十幾支 tmp 腳本不再需要。④最先壞掉的那一筆：寫已定價那一格的人
（要答 yes／no／量不到）——預設遮掉後得加 `--prices`，SKILL 寫明；敘事的已定價格寫的是 placeholder（`{own_history_pctile}` 等，
render 時由 authority 填），寫入端本身不受影響。個股頁與候選板物化檔照印價格（那是給使用者看的）；券商報告正文的目標價不在本項
（F 的索引讓研究不必 grep 全文，讀那幾頁時照 SKILL 跳過封面）。

**驗收（現有資料）：** Q3W 名單 28 檔 `alpha lights --format json` 預設輸出的價格欄 **0** 個（原樣 339）、會死嗎有燈 62 盞照印、
未讀到 0；3163.TWO 的「−32.9%」那一行印成遮掉。packet：IQE.L、AXTI 預設輸出市價、市值、目標價等有值的欄全部遮掉（`--prices` 照原樣）；
`alpha brief 2455.TW --show` 的 `priced_at_write` 遮掉。機制：`tests/test_price_mask.py` 11 條＋變異 10／10 變紅（已定價的值不遮、
detail 不遮、會死嗎市值不遮、遮掉印成 null、封包目標價不遮、缺席也印成遮掉、research 預設不遮、lights 的 --prices 沒作用、
brief --show 不遮、讀燈不帶現行敘事的歷史不可比）。**前置：** 無。
**落地（2026-11-10）：** `alpha/price_mask.py`；`alpha/providers/candidates.py::lights_for`；`alpha/providers/briefs.py::raw_record`；
`alpha/cli.py`（`lights`、`research --prices`、`brief --show/--prices`）；research-drain ⓑ、起始門、ⓔ、派工提示。
**sandbox：** 只動互動命令；daily 不呼叫這幾個出口，可執行面沒變，不另寫 OPERATIONS 結論。
