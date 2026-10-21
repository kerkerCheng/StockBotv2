# PLAN_PROPOSAL：海外財報來源③日本 EDINET、④韓國 OpenDART——三題對日韓由缺席變有值（Z2）

> 日期 2026-10-21｜狀態：**APPROVED**（使用者 2026-10-21「日韓 AAA」＝Q1 A 半年 TTM、Q2 A 普通股 distb_stock_co、Q3 A 只收整行總額）｜ROADMAP「海外財報來源」③④格
> **實作前的設計修正（10-21 唯讀子代理 `jpkr_design` 實測 EDINET 39 次、OpenDART 8 次）：** ①書類一覧的 periodStart／End 不能用（160 是整個會計年度、140 是單季、訂正書是 null）——期間與 context 一律由 DEI（`TypeOfCurrentPeriodDEI`、`CurrentPeriodEndDateDEI`）決定，docType 不參與（6594 S100UOHJ：docType 160 但 DEI 是 Q2）；②股數只扣自己保有株式，不扣「自己株式等合計」（相互保有在 7/18 份出現，法律上仍是流通股）；③除權日落在期末前 10 天內的那一期股數整期不用（6594 2024-09 實測會少算一半；4062、5706 的 2026-09-29 分割即將重演）；④S1 先把 `late_metrics_supported` 改成逐個 metric 檢查——全有全無的寫法會讓新字彙遷移前美股稀釋燈與 capex 整批略過；⑤日韓 13＋6 檔都沒有整行總借款 → 依 Q3 A 淨負債一律缺席、已定價①用 P/S。
> 使用者 2026-10-21：「741 742 我已經把 API 貼上去」——[741][742] 已結案（go；唯讀連線測試通過，收據
> `library/private/research_notes/doc_requests/2026-10-21_overseas_api_keys.md`，不含 key）。開發項的唯一載體是 ROADMAP 與本檔。
> 調查底稿：research-drain 10-21 唯讀子代理（EDINET 帶 key 2 次、OpenDART 5 次；照台股提案 `2026-10-05-001` 的形狀）。

## INTAKE

- Zoom：**Z2**——`fundamental_history.metric` 封閉字彙加兩個、申報人類別加兩類、三題的 revenue_kind 與半年 TTM（改契約與既有輸出語意）；Engine C 多兩個外部來源。
- Review：**R2**（命中 financial identity・PIT・units 與 security・credentials 兩條；Phase 7 plan Q7 對命中 trigger 的開發 Step 常規 opt-in）。
- Case：使用者指示（ROADMAP 2026-10-04「研究過程用到就一起做」；[741][742] 提供 key＝go）＋ failure log #19（10-05 同日 3 次，含 6324.T）＋ 候選板現值 3110.T 日東紡「缺：②已定價的主參照（日本申報人沒有自家歷史）。11 月上旬第 2 季決算後重看」＋ 6 份日本「不要」敘事的已定價答「無法量」。

## 現況（10-21 唯讀查到）

- 名冊：.T 13 檔（邊緣 7：2768、3110、5411、5706、6268、6324、6481）、.KS 6 檔（邊緣 0、敘事 0）、.KQ 0。ROADMAP 寫的「日 3／韓 3」已過期。
- Engine C：19 檔 `fundamental_history` 都是 0 列；`fx_history` 只有 TWD。
- 稽核區：日韓 19 頁的 `own_history_pctile` 與 `in_numbers_series` 各 19/19 `upstream_unavailable`，理由寫「非美國 SEC 申報人、非台股：沒有機械的財報歷史來源（歷史不可得）」——對日韓這句是錯的（L11-5：「我找不到」與「它不存在」是兩個 claim）。
- 查證命令（今天 19／19）：
  `.venv/Scripts/python.exe -c "import json,glob,os,collections as C;c=C.Counter();[c.update([(l['datum']['dependencies']['row_key'],l['datum']['absence_kind'] or 'value')]) for p in glob.glob('library/private/app/analyst_view/*.json') if os.path.basename(p)[:-5].endswith(('.T','.KS','.KQ')) for d in [json.load(open(p,encoding='utf-8'))] for l in d['view']['three_questions']['lines'] if l['datum']['dependencies']['row_key'] in ('own_history_pctile','in_numbers_series')];print(sorted(c.items()))"`

## 實測到的事實（決定設計的那幾條）

- **EDINET**：コードリスト 13 檔全中；書類取得 type=5 CSV 有 `NetSales`、`OperatingIncome`、`CashAndCashEquivalents`、發行股數、自己株式；**JGAAP 沒有總負債元素**；訂正報告書期間欄是 null、要從 DEI 取；2024-04 以後 Q1／Q3 沒有法定申報。
- **OpenDART**：corp_code 6 檔全中；**`fnlttSinglAcntAll` 只回更正版 rcept_no**（SK hynix FY2020 會記成 2021-03-30，比原件晚 8 天）——保守的晚知道、代價是覆蓋率下降，要印；回應沒有期間起訖日；借款 tag 跨年會變；個人資料每 2 年要重新同意，否則 key 失效（901）。

## 提議的邊界：寫進現有 `fundamental_history`，不另開表

`accession`＝docID／rcept_no；`filed`＝可知日（日本 `submitDateTime` 的 JST 日期、韓國 rcept_dt）；`form`＝`EDINET-<docTypeCode>`／`DART-<reprt_code>`；`source`＝`edinet://`／`opendart://`。可重建的投影（L10：EDINET 保存 10 年、DART 2015 起都查得到）。名冊不加欄位：コード與 corp_code 執行時從官方對照檔解析，0 筆或多筆就拒收（照 EDGAR CIK 的先例）。

## Steps（日本先做——3110.T 要在 11 月上旬重寫）

- **S1 契約＋共用（不連網）**：metric 加 `revenue_half`、`operating_income_half`（Postgres 遷移＋SQLite CHECK 重建，照 10-08 capex 先例）；FILER_CLASSES 加 `jp_semiannual`、`kr_quarterly`；三題 `ttm` 參數化（季：最近 4 季、間隔 80–100 天；半年：最近 2 個半年、間隔 170–200 天；最新一期最多 200／290 天）；來源標籤改從資料列取（現在寫死「SEC companyfacts」「EDGAR 季營收」，KR 列會被標成 EDGAR——L18）；還沒接的市場理由改成「這個市場的機械來源還沒接」。
  驗收：真資料重跑 materialize 後美股、台股頁三題逐位不變；半年 TTM 變異「相鄰間隔不檢查」要紅。
- **S2 日本 EDINET**：`fetchers/edinet.py`＋`engine_c/edinet_history.py`（CLI `--backfill`／`--sync`／`--ticker`）；逐日掃書類一覧（本地快取）、篩 13 個コード、docTypeCode 120–170、取 type=5 CSV；JGAAP／IFRS 兩套白名單（US GAAP 拒收）、只收連結、同一期兩個 tag 給不同數就拒寫；H1 取半期報告書（2024 以前取第 2 季四半期 6 個月累計）、H2＝FY−H1 標 derived；股數＝期末發行−自己株式。**S2 第一個驗收（不過就不寫入）**：半期報告書與 2024 以前第 2 季四半期的 context 名稱、IFRS 公司的營收元素變體（今天沒驗）。
- **S3 韓國 OpenDART**：`fetchers/opendart.py`＋`engine_c/dart_history.py`；list.json（含更正版）＋`fnlttSinglAcntAll`＋`stockTotqySttus`，2021–2026；季營收與營業利益取 `thstrm_amount`、Q4＝年報−Q3 累計（derived）；可知日 rcept_no 對 list.json 的 rcept_dt，對不到就拒收；狀態碼各對一個具名結局。約 300 次呼叫（每日上限 1.5%）。落地時登記一筆有到期的等待：key 2 年重新同意（約 2028-09，INV-2）。
- **S4 心跳＋文件**：心跳段 1 加「日韓財報」一行（每市場有值幾檔、最新一期、落後法定期限幾檔、拒收幾筆；「落後」與「抓到但不能用」分開印）；OPERATIONS 一節＋sandbox impact review；`.env.example` 加兩個佔位行；ROADMAP 檔數改現值附查證命令。

## daily：不加步驟

兩個來源都永久可查、漏抓補得回來（L10）；不把 API key 放進無人值守路徑。互動入口＋心跳計數器（先例：月營收 09-17、台股季報股數 10-05、台股年報地區別 10-14）。另加測試：rules、harvest、daily steps 都不得出現這兩個入口。**連帶副作用要在 S3 的 sandbox review 寫出來**：KR 季營收寫進來後，daily ②b 會多向 FRED 抓 DEXKOUS（同主機、argv 不變、多 1 個序列）；capture 與 path_layers 會讀韓國季營收，逐頁列出 payload 變動。

## 要你選（各附推薦）

- **Q1 日本季度缺口**（2024-04 以後 Q1／Q3 沒有法定申報）：**A（推薦）** 接受半年頻率，H1＋FY 的半年 TTM；B J-Quants Free（只限私的使用、排除最近 12 週、只有 2 年、一年後自動解約）；C 付費 J-Quants Light ¥1,650／月（要明確核准金額）。
- **Q2 韓國股數口徑**：**A（推薦）** 普通股 `distb_stock_co`（發行−庫藏），Samsung 優先股不加、稽核區註明「只算普通股」；B 照 EDGAR「多股類不加總」，Samsung 整格缺席。
- **Q3 總借款**：**A（推薦）** 維持只收整行總額——JGAAP 與部分韓股淨負債缺席，已定價①用 P/S；B 分項白名單加總（改契約；SK hynix 借款 tag 跨年會變）。

## 已替你決定（照先例）

可知日只到日（同 EDGAR 的限制）；日韓都不換匯（報表幣別＝結算幣別）；期末日由程式從資料推、不從代號猜（L16）。
mechanical 數字不需 pq2；judgment（會計師意見、分部占比、backlog、客戶集中度、韓國잠정실적）維持 `engine_c_observation` pq2、本計畫不碰。

## 驗收（L14：只數稽核區）

日韓 19 頁的 `own_history_pctile` 與 `in_numbers_series` 由 19/19 `upstream_unavailable` 變成有值的檔數；仍沒值的每檔有具名 absence_kind 與理由（預期 5016.T `insufficient_evidence`：窗不滿三年）。PIT 測試：T 早於可知日時看不到那一期（變異「拿掉 filed≤T」要紅）；key 不外洩（變異「拿掉遮罩」要紅）。研究端之後：3110.T 的「缺 X ②」與 6 份日本敘事的「已定價＝無法量」在重寫時變成 yes／no 的份數（不算本 change）。

## 規模與風險

程式約 1,100–1,300 行（約 11 檔）、測試約 600 行；一次性回補 EDINET 約 1,750 次呼叫（每次至少間隔 2 秒，約 1–1.5 小時、可續跑）、DART 約 300 次——回補寫正式庫要先取 writer lock、不和 daily 重疊。
風險：①EDINET 規約禁止「短時間における大量のアクセス」——間隔 ≥2 秒、429 退避、中止時計數未掃日期（INV-3）；內容 PDL1.0、原檔不進 repo（公開）。②key 在 URL query 裡（`requests` 例外訊息會帶出 URL）——一律遮罩、有測試（R2 trigger）。③OpenDART 2 年重新同意。④DART 只給最新更正版（保守、覆蓋率下降要印）。⑤日本未驗項列為 S2 第一個驗收。
