# 海外財報資料源：缺什麼、為什麼、可用來源（2026-09-30）

> 唯讀 workflow 的結果原樣整理（盤點 1 位、分市場查證 6 位；同日額度中斷，**只有盤點與日本、韓國兩市場跑完**，台、中港、歐英北歐、加澳與 20-F 的查證沒有結果——下表未列者一律視為未驗證）。
> 「API 有這個欄位」多半來自官方規格頁，**沒有 key 就沒有打到任何一筆實際資料**（各段 caveats 照抄）。
> 排程見 ROADMAP 旁支「海外財報來源」。本檔是研究紀錄，不是 current-state truth。

## 1. 盤點（73 份個股頁 artifact、Engine C 正式庫唯讀）

**計數：** 範圍與前提：分析的是 library/private/app/analyst_view/*.json，共 73 檔，generated_at 在 2026-09-30T01:25–01:30Z 之間。總行數 695（與結案報告的 695 相符）。非美國國內申報人共 37 檔：帶交易所後綴的 29 檔，加上美國掛牌的 20-F 8 檔。以下都只數這 37 檔。

【因資料源而缺席】
- own_history_pctile：37/37 缺席，0 檔有值。upstream_unavailable 29 檔：非美非台沒有財報歷史 22 檔，台股沒有歷史股數 7 檔。inputs_incompatible 8 檔：幣別錯配 4 檔（TSM、UMC、XPEV、NBIS），20-F 股數單位 4 檔（GFS、HIMX、POET、TSEM）。
- cohort_median：upstream_unavailable 10 檔，都是①缺席連帶（2455.TW、300308.SZ、3081.TWO、3363.TWO、4971.TWO、4979.TWO、ENA.V、IQE.L、POET、SIVE.ST）。
- in_numbers_series：upstream_unavailable 22 檔（非美非台）；insufficient_evidence 2 檔（TSM、UMC 停在 FY2023）。有值 13 檔：台股月營收 7 檔、20-F 年度營收 6 檔。
- wipeout_cash_runway：upstream_unavailable 3 檔（5016.T、5802.T、XPEV：yfinance FCF 是 null）。有值 34 檔，其中 6324.T、688836.SS 靠人工 runway_inputs。
- wipeout_debt：upstream_unavailable 2 檔（5016.T、5802.T）。有值 35 檔。
- wipeout_dilution：insufficient_evidence 37/37。沒有歷史股數來源，yfinance 快照序列最早從 2026-07-08 起，一年窗不滿；colour_available_on 落在 2027-07-08 到 2027-09-03。

【不算資料源缺席，但照實列出】
- cohort_median、rel_return_30d、rel_return_90d：各 27 檔 not_yet_recorded，原因是不在任何主題等權組。37 檔都有價格。
- wipeout_going_concern：not_yet_recorded 35 檔、有值 2 檔（IQE.L、SIVE.ST）。這是經 pq2 的人工判讀欄，美股也一樣：36 檔裡 33 檔是 not_yet_recorded。
- in_numbers_structure：24 行，是人工分部或產品線占比，每個欄位只有一個點。

【對照：美國國內申報人 36 檔】
- own_history：有值 27、insufficient_evidence 8、upstream_unavailable 1（CDNS 落後）。
- in_numbers：有值 34、upstream_unavailable 2（CCXI、CDNS）。
- dilution：有值 30、insufficient_evidence 6。
- cash_runway：upstream_unavailable 3。debt：upstream_unavailable 1。

【查證命令】在 repo 根目錄、Git Bash 下執行：
(1) 各格計數：.venv/Scripts/python.exe -c "import json,glob,collections as C;F={'GFS','HIMX','NBIS','POET','TSEM','TSM','UMC','XPEV'};c=C.Counter();[c.update([(l['datum']['dependencies']['row_key'],l['datum']['absence_kind'] or 'value')]) for p in glob.glob('library/private/app/analyst_view/*.json') for d in [json.load(open(p,encoding='utf-8'))] if '.' in d['ticker'] or d['ticker'] in F for l in d['view']['three_questions']['lines']];[print(k,v) for k,v in sorted(c.items())]"
要看美股對照，把條件改成 if not (...)。
(2) 列出每格是哪幾檔：同一個 one-liner 改成用 collections.defaultdict(list) 以 (row_key, absence_kind) 分組、append d['ticker']，只收 absence_kind 非空的行。
(3) Engine C 唯讀：sqlite3.connect('file:C:/Users/Cheng/code/StockBotv2/library/private/engine_c/stockbot-engine-c-private-v1-458db5270ee2.db?mode=ro', uri=True)，然後執行 SELECT ticker, metric, COUNT(*) FROM fundamental_history GROUP BY 1,2。帶後綴的 29 檔結果都是 0 列。
(4) 快照窗：SELECT ticker, MIN(snapshot_date), SUM(free_cash_flow_ttm IS NOT NULL), COUNT(*) FROM financial_snapshots GROUP BY ticker。

scratchpad 腳本：C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2\bf551b7b-6727-49f4-a878-72e0f0d42c82\scratchpad\nonus\（dump_tq.py、matrix.py、reasons.py、wipe_detail.py、db_counts.py、sec_probe.py、sec_6k.py、tw_probe.py）。全程沒有寫入 repo，git status 為空。

**特例：** 1. 【20-F／ADR】美國掛牌的 20-F 8 檔，已定價①全部是 inputs_incompatible，而且這個判定比字彙本身的定義寬（plan §14 #47 已記錄）。GFS、HIMX、POET、TSEM 的真正狀況是：封面股數在 fundamental_history 裡是 0 列，因為 history_backfill.py:361 刻意不收；它們也沒有季度營收，因為 :336 不收。實測 companyfacts 的 20-F 有年度 dei:EntityCommonStockSharesOutstanding（GFS、HIMX、POET、TSEM、TSM、UMC 都有，最新一筆 period 2025-12-31；例如 TSM 25,932,524,521 股，filed 2026-04-16），所以「來源沒有」只對 NBIS、XPEV 成立。哪幾檔真的是 ADS、比率是多少：config/company_identity.json 沒有這個欄位，本次也沒驗證；plan §14 #47 記 GFS 掛牌的是普通股。另外 6-K 的 XBRL 只有零星收錄（GFS 季度到 2025-09、TSEM 只有半年點、TSM 0），而程式本來就不讀 6-K（history_backfill.py:303、:548）。

2. 【companyfacts 部分收錄（TSM／UMC）】2026-09-30 我實際打了 companyfacts：TSM 最新一份 20-F（filed 2026-04-16）和 UMC 最新一份 20-F（filed 2026-04-30）都在 companyfacts 裡，但這兩份申報的營收白名單 fact 都是 0 筆；營收最新 filed 仍停在 2025-04-17／2025-04-24。所以 Step 3.2 的 lagging 判定到今天仍成立。Engine C 裡的 fundamental_history 只到 FY2023（現金只到 FY2022），in_numbers 因此印 insufficient_evidence（1004 天）。FY2024 被多單位守則擋掉（TWD＋USD 便利換算）這件事，是 Step 3.2 報告的說法，本次沒有重驗。同時 Engine C 已經有這兩檔的人工 fiscal_year_results（FY2025），但三題的取數只讀 fundamental_history（three_question_inputs.py:26-31、:104-105），不讀它（plan §14 #8、#16）。

3. 【報表幣別≠結算幣別】已經觸發的有 4 檔：TSM／UMC（TWD）、XPEV（CNY）、NBIS（RUB＋USD）。潛在的有 4 檔，現在被 upstream_unavailable 蓋住，一旦補上財報來源就會撞 three_questions.py:216-224：6680.HK（CNY／HKD）、HEXA-B.ST（EUR／SEK）、XFAB.PA（USD／EUR）、ENA.V（USD／CAD）。這幾組幣別取自 yfinance 的 financialCurrency 欄位，屬二手資料，未對一手驗證。plan §14 #9 的名單有兩處和資料不符：它列了 IQE.L，但 IQE.L 只是 GBp／GBP 單位差、已處理；它漏了 6680.HK。Engine C 的人工 fx_rate 只有 4 檔（6680.HK、HEXA-B.ST、XFAB.PA、XPEV），各 12 筆，期間 2026-09-11 到 09-29，不夠支撐 3 年的歷史換匯。另外發現一個缺陷：_yoy_quarters（alpha/three_questions.py:341-351）不檢查幣別。NBIS 的 in_numbers 序列 FY2022 印出 yoy＝-1.0，實際上是拿 USD 13.5M 除以 FY2021 的 RUB 356.171B。Step 3.2 報告寫「三題端以同一序列幣別一致擋」，這只對 ttm() 成立（:110-112）。序列值也沒有帶幣別欄，所以 XPEV 的 CNY 數字印出來沒有單位。

4. 【台股歷史股數】已實測 TWSE t187ap03_L、TPEx mopsfin_t187ap03_O（有已發行股數）以及 t187ap07 資產負債表（有股本與庫藏股數），全部只有當期（出表日期 1150929；年度 115、季別 2）。repo 目前沒有程式讀這些端點。現在台股稀釋燈唯一的股數來源是 yfinance，而它有一個明顯壞點：3105.TWO 在 2026-07-26 從 423,940,384 股跳到 80,825,000 股（−81%），但 TPEx 當天的 IssueShares 是 423,940,384。一年窗滿之後，這盞燈可能拿壞點判成「沒增加」，在短窗內甚至可能判成綠。

5. 【可知日（INV-6，point-in-time）】所有 yfinance 來源的現金、負債、FCF，燈上的 as_of 都是 ETL 執行日：etl_yfinance.py:150 寫 snapshot_date＝date.today()，checklist.py:410 再把它當成 as_of（稽核層顯示 2026-09-30T00:00:00+00:00）。yfinance.info 本身不帶期末日或申報日。非美市場的現金與負債燈只有這一個來源。人工 runway_inputs 則用資產負債表日當 as_of（6324.T 是 2026-06-30，申報日另見 TDnet 2026-08-07），也不是可知日。

6. 【其他】
- 上市或重新掛牌太晚的 3 檔，就算補上來源，①也會是 insufficient_evidence：688836.SS 29 列、5016.T 373 列、NBIS 486 列。
- 帶後綴的 ticker 在 history_backfill.py:621 一律不查 SEC。實測兩個可能的例外都沒有財報 fact：IQEPF 回 404；SK hynix（HXSCL）只有 ffd namespace。
- 任務前提有一處更正：config/company_identity.json 沒有市場欄，也沒有 CIK 欄。它的欄位是 company_id、research_ticker、market_currency、execution_*、display_name、aliases。CIK 是執行時從 SEC company_tickers.json 解析的（history_backfill.py:594-596），市場則由 ticker 後綴推。
- 追源方面（L11：「我找不到」與「它不存在」是兩個 claim）：MOPS 歷史季報股本、集保一年上限、SSE、EDINET、HKEX 的結構化財報端點，本次都沒驗證。

### 台股（TWSE .TW／TPEx .TWO）（2301.TW, 2455.TW, 3081.TWO, 3105.TWO, 3363.TWO, 4971.TWO, 4979.TWO）

- **缺什麼：** 【已定價①】own_history_pctile：7/7 缺席，全是 upstream_unavailable（沒有歷史股數）。【已定價②③】5 檔在主題組裡（2455／3081／3363／4971／4979）：cohort_median 是 upstream_unavailable，這是①缺席連帶下來的；rel_return_30d／90d 有值。2301、3105 是 not_yet_recorded（不在組裡，不是資料源的問題）。【出現在數字裡了嗎】in_numbers_series：7/7 有值（MOPS 月營收，12 個月；最新一期 2026-08，available_on 2026-09-10，days_since_last 60）。【會死嗎】wipeout_cash_runway 與 wipeout_debt：7/7 有值（來源 yfinance.info；4971.TWO 現金跑道紅燈）。wipeout_dilution：7/7 是 insufficient_evidence，yfinance 快照序列從 2026-07-18 到 08-30 才開始，不滿一年，所以 colour_available_on 落在 2027-07-18 到 2027-08-30。wipeout_going_concern：7/7 是 not_yet_recorded（這是人工判讀欄，不算資料源缺口）。
- **為什麼：** 已定價①被程式碼直接擋下：engine_c/three_question_inputs.py:106-113 碰到 .TW／.TWO 就寫死 gate＝upstream_unavailable，理由是「台股歷史股數沒有機械來源，不用今天的股數回推」；alpha/three_questions.py:208-210 照這個 gate 輸出缺席。基本面表 fundamental_history 對這 7 檔是 0 列：engine_c/history_backfill.py:621 對帶後綴的 ticker 設 cik=None，於是在 :516-519 記成 no_cik。營收改走 monthly_revenue_observations，每檔 49 列，published_at 全是 NULL，可知日用法定期限 disclosure_deadline（INV-6：T 時刻知道什麼就只能用什麼，不得拿抓取日冒充）。稀釋燈的路徑：engine_c/checklist.py:320 判定不是 domestic_quarterly 就不用 SEC 封面股數，退回 :452 的 yfinance_snapshot 序列，再由 alpha/wipeout.py:162-170 判成灰燈並寫到期日。我在 2026-09-30 實際打過兩個 OpenAPI 端點：https://openapi.twse.com.tw/v1/opendata/t187ap03_L 有「已發行普通股數或TDR原股發行股數」，https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O 有 IssueShares，但兩者的出表日期都只有一個值 1150929，也就是只有當期。資產負債表端點 t187ap07_L_ci／mopsfin_t187ap07_O_ci 有「股本」和庫藏股股數，同樣只有 年度 115、季別 2。repo 裡沒有任何 *.py 用到 t187ap03／t187ap07／IssueShares（grep 結果 0 檔）。另外兩條可能的歷史來源——「集保股權分散表只能查一年」出自 Step 3.2 報告；MOPS 歷史季報的逐季股本——這兩條本次都沒驗證。
- **現有抓取程式：** fetchers/mops_open_data.py：當期月營收（t187ap05_L／mopsfin_t187ap05_O）、歷史月營收頁 t21sc03、重大訊息。engine_c/monthly_revenue.py：寫入月營收。fetchers/mops.py：抓 MOPS 電子書 PDF（年報、財報），拿去抽取用，不產結構化數字。engine_c/twse.py：TWSE 最新日行情的鮮度檢查。股數：沒有 fetcher。

### 日本（.T）（5016.T, 5802.T, 6268.T, 6324.T, 6481.T, 6594.T）

- **缺什麼：** own_history_pctile：6/6 upstream_unavailable。in_numbers_series：6/6 upstream_unavailable；另有 4 檔各有一個人工分部占比點，只印成 in_numbers_structure。cohort_median 與 rel_return：6/6 not_yet_recorded（不在組裡）。wipeout_cash_runway：5016.T、5802.T 是 upstream_unavailable，其餘 4 檔有值。wipeout_debt：5016.T、5802.T 是 upstream_unavailable，其餘有值。wipeout_dilution：6/6 insufficient_evidence（yfinance 快照從 2026-07-18 或 08-21 起）。going_concern：6/6 not_yet_recorded。
- **為什麼：** 已定價①和出現在數字裡：history_backfill.py:621 → :516-519 記成 no_cik，fundamental_history 0 列。three_question_inputs.py:115 算出 filer_class＝unknown，:123-129 寫下 gate「非美國 SEC 申報人、非台股：沒有機械的財報歷史來源」。alpha/three_questions.py:392-398 因為沒有月營收、季營收、年營收任何一列，寫 upstream_unavailable。5016.T／5802.T 的現金與負債燈缺席，是因為 yfinance 最新一筆快照的 freeCashflow 是 null：5016.T 在 63 筆裡只有 14 筆有 FCF、最後一筆是 2026-08-08；5802.T 在 63 筆裡只有 7 筆、最後一筆是 2026-08-01。缺值的路徑是 engine_c/checklist.py:488 只取最新快照 → shared/runway.py:50-52 回 manual_required → alpha/wipeout.py:87-88、:108-110。6324.T 的 yfinance FCF 是 0/39，靠人工 runway_inputs（決算短信，as_of 用資產負債表日 2026-06-30）才亮燈。5016.T 價格從 2025-03-19 才有（373 列），就算補上財報，①也會因為窗不滿 3 年而是 insufficient_evidence。
- **現有抓取程式：** 沒有 fetcher。config/source_routes.json 的 edinet 路線標 verified:false；沒有 TDnet 的路線。

### 韓國（.KS）（000660.KS, 005930.KS, 012330.KS）

- **缺什麼：** own_history_pctile：3/3 upstream_unavailable。in_numbers_series：3/3 upstream_unavailable（000660、005930 各有一個人工分部占比 structure 點）。cohort 與 rel_return：3/3 not_yet_recorded。wipeout_cash_runway 與 debt：3/3 有值。wipeout_dilution：3/3 insufficient_evidence（快照從 2026-07-18、07-30、08-21 起）。going_concern：not_yet_recorded。
- **為什麼：** 缺席路徑和日本相同（history_backfill.py:621、three_question_inputs.py:123-129、three_questions.py:392-398、checklist.py:320）。SEC 這條路我實際查過：company_tickers.json 裡 HXSCL 對應 CIK 0002120882（SK hynix Inc.），2026-09-30 打 companyfacts，只有 ffd namespace 的 5 個 fact（申報費用資料），沒有任何財報 fact。就算有 CIK，也拿不到財報歷史。
- **現有抓取程式：** 沒有 fetcher 模組。config/source_routes.json 的 dart 路線標 verified:true，但它是人工抓文件的路線（POST dart.fss.or.kr/dsab007/detailSearch.ax），不產結構化時間序列。

### 中國 A 股（.SZ／.SS）（002472.SZ, 300308.SZ, 688017.SS, 688836.SS）

- **缺什麼：** own_history_pctile：4/4 upstream_unavailable。in_numbers_series：4/4 upstream_unavailable（002472 有一個分部占比 structure 點）。300308.SZ 在主題組裡：cohort_median 是 upstream_unavailable（①連帶），rel_return 有值；其餘 3 檔是 not_yet_recorded。wipeout_cash_runway 與 debt：4/4 有值（688836.SS 靠人工 runway_inputs 招股書 2025-12-31；yfinance FCF 0/25）。wipeout_dilution：4/4 insufficient_evidence。going_concern：not_yet_recorded。
- **為什麼：** 主要缺席路徑同上（no_cik → filer_class unknown → gate）。688836.SS 是 2026-08-19 才上市，price_history 只有 29 列；即使補上財報來源，①也會因窗不滿 3 年缺席，這不是資料源的問題。
- **現有抓取程式：** 沒有 fetcher 模組。source_routes 的 szse 路線標 verified:true（人工抓公告 PDF），sse 標 verified:false。

### 香港（.HK）（6680.HK）

- **缺什麼：** own_history_pctile：upstream_unavailable。in_numbers_series：upstream_unavailable（另有一個分部占比 structure 點）。cohort 與 rel_return：not_yet_recorded。wipeout_cash_runway 與 debt：有值。wipeout_dilution：insufficient_evidence（快照從 2026-09-02 起，到期 2027-09-02）。going_concern：not_yet_recorded。
- **為什麼：** 缺席路徑同上。另外 yfinance 的 financial_currency 是 CNY，結算幣別是 HKD。就算補上財報來源，alpha/three_questions.py:216-224 也會判成 inputs_incompatible（程式不換匯）。
- **現有抓取程式：** 沒有 fetcher。source_routes 的 hkex 路線標 verified:false。

### 瑞典（.ST）（HEXA-B.ST, SIVE.ST）

- **缺什麼：** own_history_pctile：2/2 upstream_unavailable。in_numbers_series：2/2 upstream_unavailable；SIVE.ST 有產品線與分部占比各一個點，只印成 structure。SIVE.ST 在主題組裡：cohort_median 是 upstream_unavailable（①連帶），rel_return 有值；HEXA-B.ST 是 not_yet_recorded。wipeout_cash_runway 與 debt：2/2 有值（SIVE.ST 紅燈）。wipeout_dilution：2/2 insufficient_evidence。SIVE.ST 的 yfinance 股數 2026-09-24 從 295,418,537 變成 318,837,358（+7.9%），數字只進稽核層，不上色。going_concern：SIVE.ST 有值（人工）、HEXA-B.ST 是 not_yet_recorded。
- **為什麼：** 缺席路徑同上。HEXA-B.ST 的 yfinance financial_currency 是 EUR，結算幣別是 SEK；補上財報來源後同樣會撞 three_questions.py:216-224。
- **現有抓取程式：** fetchers/mfn.py：抓 MFN 法定揭露的全文與附件 PDF，用於追源和抽取，不產結構化財報序列。

### 英國（.L）（IQE.L）

- **缺什麼：** own_history_pctile：upstream_unavailable。in_numbers_series：upstream_unavailable（產品線與分部占比各一個 FY2025 點，只當 structure）。它在主題組裡：cohort_median 是 upstream_unavailable（①連帶），rel_return_30d／90d 有值。wipeout_cash_runway 與 debt：有值。wipeout_dilution：insufficient_evidence（快照從 2026-08-05 起，到期 2027-08-05）。going_concern：有值（人工 no_substantial_doubt）。
- **為什麼：** 缺席路徑同上。GBp／GBP 只是報價單位不同，由 price_to_settlement＝0.01 處理，不是幣別錯配。SEC 這條路查過：company_tickers.json 有 IQEPF（CIK 0001550405），但 2026-09-30 打 companyfacts 回 404。
- **現有抓取程式：** fetchers/rns.py：經 investegate 抓 RNS 全文，只拿全文、不產結構化數字。

### 德國（.DE）／法國（.PA）（SHA0.DE, SOI.PA, XFAB.PA）

- **缺什麼：** own_history_pctile：3/3 upstream_unavailable。in_numbers_series：3/3 upstream_unavailable。cohort 與 rel_return：not_yet_recorded。wipeout_cash_runway 與 debt：3/3 有值。wipeout_dilution：3/3 insufficient_evidence。going_concern：not_yet_recorded。
- **為什麼：** 缺席路徑同上。XFAB.PA 的 yfinance financial_currency 是 USD，結算幣別是 EUR，屬幣別錯配的預備案例。
- **現有抓取程式：** 沒有 fetcher，source_routes 也沒有 Euronext 或德國的路線。

### 澳洲（.AX）（LYC.AX）

- **缺什麼：** own_history_pctile：upstream_unavailable。in_numbers_series：upstream_unavailable（有一個分部占比 structure 點）。cohort 與 rel_return：not_yet_recorded。wipeout_cash_runway 與 debt：有值。wipeout_dilution：insufficient_evidence（快照從 2026-08-31 起）。going_concern：not_yet_recorded。
- **為什麼：** 缺席路徑同上。
- **現有抓取程式：** 沒有 fetcher，source_routes 也沒有 ASX 路線（extractions/ 裡的 ASX 抽取都是人工抓的）。

### 加拿大 TSXV（.V）（ENA.V）

- **缺什麼：** own_history_pctile：upstream_unavailable。in_numbers_series：upstream_unavailable。它在主題組裡：cohort_median 是 upstream_unavailable（①連帶），rel_return 有值。wipeout_cash_runway：有值（紅燈）。debt：有值。wipeout_dilution：insufficient_evidence。going_concern：not_yet_recorded。這一檔連人工 fiscal_year_results 都沒有。
- **為什麼：** 缺席路徑同上。yfinance financial_currency 是 USD，結算幣別是 CAD，屬幣別錯配的預備案例。
- **現有抓取程式：** 沒有 fetcher，source_routes 也沒有 SEDAR+ 路線。

### 美國掛牌的 20-F 發行人（非國內申報人）（GFS, HIMX, NBIS, POET, TSEM, TSM, UMC, XPEV）

- **缺什麼：** own_history_pctile：8/8 inputs_incompatible。分兩種：TSM、UMC（TWD≠USD）、XPEV（CNY≠USD）、NBIS（RUB／USD≠USD）是報表幣別不等於結算幣別；GFS、HIMX、POET、TSEM 是「20-F 股數與掛牌證券不是同一單位」。in_numbers_series：GFS、HIMX、NBIS、POET、TSEM、XPEV 6 檔有值（20-F 年度營收，最新 FY2025，days_since_last 273）；TSM、UMC 是 insufficient_evidence（最新一期 FY2023，距今 1004 天，超過 550 天上限）。POET 在主題組裡：cohort_median 是 upstream_unavailable，rel_return 有值；其餘 7 檔是 not_yet_recorded。wipeout_cash_runway：XPEV 是 upstream_unavailable（yfinance FCF 0/38），其餘 7 檔有值。wipeout_debt：8/8 有值。wipeout_dilution：8/8 insufficient_evidence。going_concern：8/8 not_yet_recorded。
- **為什麼：** 已定價①的缺席分兩層：(a) 幣別檢查在前，alpha/three_questions.py:216-224；(b) foreign_annual 檢查在後，:225-229。就算拿掉這兩道 gate，①還是算不出來，因為回填端刻意不存兩樣東西：engine_c/history_backfill.py:336 不存季度，:361 不存封面股數。而 _multiple_series 一定要季度 TTM（three_questions.py:169）和封面股數（:172）。我在 2026-09-30 實際打了 companyfacts（https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json）：GFS、HIMX、POET、TSEM、TSM、UMC 的 20-F 都有 dei:EntityCommonStockSharesOutstanding（最新一筆 period 2025-12-31）；NBIS、XPEV 是 0 筆。也就是說，這 6 檔的年度股數在來源端有，是程式沒收。季度數字方面：回填只讀 20-F／40-F 這兩種表單（history_backfill.py:303、:548），6-K 不讀。實測 GFS 的 6-K 有 20 個季度營收 fact（到 2025-09-30 那一季，filed 2025-11-12）；TSEM 只有 6 月的半年點（到 2024-06-30）；TSM 是 0 個；POET 只有 1 個。TSM／UMC 的 in_numbers 缺席是 companyfacts 部分收錄造成的，見特例。XPEV 的現金燈缺席，是 yfinance 從沒給過 freeCashflow（shared/runway.py:50-52）。稀釋燈同樣走 checklist.py:320 → yfinance 快照這條路。
- **現有抓取程式：** fetchers/edgar.py：ticker_cik_map、get_filings。fetchers/edgar_xbrl.py：fetch_companyfacts、companyfacts_lag_status。fetchers/edgar_watch.py：申報偵測。engine_c/history_backfill.py：回填與每日增量。

## 2. 已查證的市場

### JP（東證 .T；repo 內 5016.T ＪＸ金属、5802.T 住友電工、6268.T ナブテスコ、6324.T ハーモニック・ドライブ、6481.T ＴＨＫ、6594.T ニデック）

**建議：** **結論：JP 有可機械取得、帶精確可知日的一手來源，首選 EDINET API v2，但要先由使用者本人註冊 key。另外有一個結構性缺口：2024-04 以後的 Q1／Q3 不再有法定申報，只剩 TDnet 決算短信，而免費又合規的歷史路徑只有 J-Quants Free（排除最近 12 週、只有 2 年）。**

1. **首選：EDINET API v2（年度＋上半年＋2024 年以前的季度）**
   - 做法：照 fetchers/edgar_xbrl.py 的形狀另寫一支 EDINET fetcher。先用 Edinetcode.zip 做 secCode→edinetCode 靜態對照（L9／INV-1：不猜）；逐日掃 documents.json?type=2，用 edinetCode 篩 docTypeCode 120／130／140／150／160／170；取 type=5 的 CSV（或 type=1 的 XBRL）。
   - 寫入 fundamental_history：filed＝submitDateTime、accession＝docID、form＝docTypeCode。依 jpdei_cor:AccountingStandardsDEI 分 JGAAP／IFRS 兩套白名單。歧異時照現行規則拒寫，不挑一個。
   - 範圍：6 檔全有 EDINET コード；回溯 10 年，涵蓋 repo 的 5 年窗。速率自訂 ≤1 req/s，並處理 429。
   - key 由使用者本人註冊：要建 EDINET 帳號，還要過 SMS 或語音 MFA，我代辦不了。規約與仕様書都沒有收費條款，內容適用 PDL1.0。

2. **季度缺口（2024-04 以後的 Q1／Q3）有三條路，只有第一條免費又合規，其餘要使用者決定：**
   - (a) **J-Quants Free /fins/summary**：有 Sales、OP、CashEq、ShOutFY／TrShFY，帶 DiscDate／DiscTime，訂正不覆寫。限制是排除最近 12 週、只有 2 年、沒有負債欄、只限私的使用，而且免費訂閱一年後自動解約。
   - (b) **TDnet 31 天窗每日往前捕捉決算短信 XBRL**：技術上已驗證可行，但東證條款禁止『無断で転用、複製』，JPX 也請大家不要高頻自動取得，屬灰區，要使用者判斷。
   - (c) **J-Quants Light（¥1,650／月，5 年）或 TDnet アドオン（¥11,000／月）**：屬付費，照 AGENTS 必須由使用者決定。
   - 三條都不走的話，就接受 JP 是『半年頻率』：用 EDINET 的 H1 與 FY 推 H2。三題端要把『季度缺席』宣告成具名的 absence_kind，不能靜默（L16：缺席種類由產生缺席的程式自己宣告）。

3. **要先由使用者決定的 contract 問題（動 contract，不是補字彙）：**
   - ① 有利子負債：JGAAP 沒有總額元素。若維持『只收整行總額 tag』，5802、6324 的 total_debt 會缺席（IFRS 公司看有沒有用 BondsAndBorrowingsLiabilities／InterestBearingLiabilities 總額）；要改成分項白名單加總，是改 contract。
   - ② metric 字彙沒有『半年』：JP 在 2024 年以後是 H1 累計。要嘛新增 metric，要嘛等有 Q1 來源再推 Q2＝H1−Q1。
   - ③ 股數：日本申報給的是發行總數（含庫藏）加庫藏股數，不是 dei 那種『流通股』。要定義 shares_outstanding_cover 對 JP 的口徑（直接相減算不算 derived），也要對 5802 的 2026-07-01 ×4 分割。

4. **仍需人工觀測補的：**
   - 分部占比、backlog、客戶集中度（judgment），維持現行人工觀測。
   - 在 key 或 contract 決定之前，最新一季數字照現行做法人工記錄。
   - 6594.T ニデック 要特別處理：FY2026/3 的 Q3＋通期短信延到 2026-09-30，有報也申請延長。機械管線要有與 companyfacts 同形的 lagging 判定，不能把『最新是 2025-09 上半年』讀成現況。

5. **確定做不到、或本次查不到的：**
   - 免 key、合規地機械讀 EDINET：做不到（規約禁爬網站，要走 API）。
   - 免費取得 31 天以前、最近 12 週以內的決算短信：J-Quants Free 不給，TDnet 原檔 31 天後回 403。
   - 決算短信 Summary 本身不含現金與負債。
   - 用 TDnet 文件編號推開示日：不可以，會錯一天。

6. **這次改不了但已發現的：**
   - config/source_routes.json 的 edinet 路徑 verified:false 仍正確（還沒實際取回過任何一份 EDINET 文件），但 why 欄只列 5016／6268／6481／6594，漏了 5802.T、6324.T。
   - 等 EDINET fetcher 實測通過再一起改；tests/test_source_routes.py 是資料驅動的，改成 true 不會變紅。

**限制與未驗證：** - **沒有 key，所以沒有對 EDINET 或 J-Quants 取回過這 6 檔的任何一筆實際資料。**所有『EDINET 有這個欄位』的陳述都來自官方仕様書與タクソノミ要素清單，意思是『元素存在』，不是『這幾家公司的申報確實有用』（L11-5：我找不到 ≠ 它不存在；反過來，規格有 ≠ 申報有）。
- 能用真實數字驗證的只有 TDnet 決算短信 XBRL 兩份：一份是 TDnet 原件 186A0，另一份是 5016.T 的日經鏡像。5016 的 Q1 預測值與 repo 既有人工觀測一致。
- 「EDINET 免費」是由規約與仕様書都沒有收費條款、發 key 流程沒有付款步驟推得，沒有找到明文『無料』；搜尋摘要說可商用二次利用，那不是一手。
- 四半期報告書廢止：施行日 2024-04-01 已由 FSA 頁面確認；『2024-04-01 以後開始的四半期不再提出』則依 FSA 頁面『各決算期における適用時期』的標題、JPX 四半期開示見直し資料與搜尋摘要，**沒有逐字讀到法條本身**。
- 有報『3 個月內』、半期報告書『45 日』這類法定期限沒有從一手核對。因為 EDINET 有實際 submitDateTime，這些期限用不到。
- 其他沒有驗證的：J-Quants 海外居住者能否註冊、台灣手機能否完成 EDINET MFA、東証上場会社情報サービスの歷史短信是否附 XBRL、TDnet データベースサービスの價格、日經／Yahoo 鏡像的使用條款。
- J-Quants /fins/summary 的 CashEq 在 1Q／3Q 多半空白，是由 JPX 1Q／3Q CF 任意揭露推得，沒有用實際資料驗證。
- 6594.T 的會計基準本次沒有驗證。
- 本次全程唯讀：repo 工作樹沒有任何變更（git status 為空），沒有寫 library/，沒有取 writer lock，沒有跑 materialize、daily 或 backfill。Engine C 正式庫只用 file:...?mode=ro 讀。
- 暫存檔都在 scratchpad：C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2\bf551b7b-6727-49f4-a878-72e0f0d42c82\scratchpad\jp\（含仕様書 PDF／txt、コードリスト、TDnet／日經 XBRL zip、ixbrl_dump.py、tdnet_probe.py、q_db.py）。
- 對 TDnet 的自動抓取只有一次性驗證用的少量請求（一天 4 頁列表、6 次搜尋、2 個 zip、2 個 PDF），不代表條款允許常態自動化。

- **EDINET API v2（金融庁；書類一覧 API＋書類取得 API，type=1 XBRL／type=5 XBRL_TO_CSV）**（https://api.edinet-fsa.go.jp/api/v2/documents.json （仕様書 https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf ；利用規約 https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0030.html ））
  - 取得方式：要 Subscription-Key（query 參數 Subscription-Key=）。取得方式（仕様書 2-3）：在 EDINET 閲覧サイト建帳號（Microsoft 帳號式登入，強制多要素認證：SMS 或語音電話，畫面要輸入『国コード』與電話號碼）→ API キー発行画面登錄連絡先 → 顯示 key，之後持續可用。費用：仕様書與利用規約都**沒有任何收費條款**、發 key 流程沒有付款步驟（『免費』是由缺少收費條款推得，不是找到一句『無料』的明文）。速率：沒有公布數字；規約 3.2 禁止『短時間における大量のアクセス』，違反可『予告なく停止』；API 回 429 時要求『十分な時間を空けて再試行』。條款：內容適用 PDL1.0（公共データ利用規約第1.0版，需標示出典，加工需註明）；規約 2.2 禁止用爬蟲抓 EDINET 網站，機械取得『API機能を利用してください』——所以**沒有合規的免 key 機械路徑**。台灣手機號能否收 SMS 完成 MFA：未驗證。
  - 欄位：營收：有（JGAAP NetSales；IFRS 有 RevenueIFRS／NetSalesIFRS 等多個變體，需白名單）。營業利益：有（PL 本表 jppfs_cor:OperatingIncome／jpigp_cor:OperatingProfitLossIFRS；經營指標摘要表沒有）。現金：有（CashAndCashEquivalents…；JGAAP 部分公司 BS 只有 CashAndDeposits，兩者口徑不同）。有利子負債：**JGAAP 沒有單一總額元素**，只有短借／一年內長借／長借／社債／CP／租賃分項，公司也常用自訂擴充元素；IFRS 有 BondsAndBorrowingsLiabilitiesIFRS、InterestBearingLiabilitiesLiabilitiesIFRS 這類總額元素，但是否使用因公司而異。股數：有（期末發行總數、提出日現在發行數；自己株式要另從『自己株式等の状況』取，流通股＝發行−庫藏要自己減）。期間：有価証券報告書（120）＝年度；半期報告書（160）＝上半年累計；四半期報告書（140）只到『2024-04-01 以前開始的四半期』（令和5年金商法改正，2024-04-01 施行，FSA https://www.fsa.go.jp/news/r5/sonota/20240327/20240327.html ）——之後 Q1／Q3 **不再有法定申報**，只剩 TDnet 決算短信。回溯：閲覧期間 10 年（有報、半期報告書 5＋5 年；四半期報告書 3＋7 年；半期延長只適用 2024-04-01 以後提出者），書類一覧 API 可指定 10 年內日期。訂正報告書 130／150／170 另有 docTypeCode。
  - 可知日：有，而且是精確時戳：submitDateTime（提出日時，到分鐘）＝可知日，直接對應 repo fundamental_history.filed；accession 可用 docID。不需要用法定期限冒充（有報『3 個月內』、半期『45 日』這類期限本次**未從一手核對**，但既然有實際提出日時就用不到）。注意：磁碟／紙本提出時，書類列在『提出操作日』那天的一覽（仕様書 3-1 注）。
  - 實際打過：①2026-09-30 不帶 key 打 GET https://api.edinet-fsa.go.jp/api/v2/documents.json?date=2026-06-26&type=2 → HTTP 200，body {"StatusCode": 401,"message": "Access denied due to invalid subscription key..."}；v1 同路徑 → 403 Service unavailable（v1 已停）。②下載並逐節讀了官方仕様書 Version 2（2026 年 6 月版）：書類一覧 API 以『ファイル日付』逐日查詢（不能按公司查），輸出欄位含 secCode、edinetCode、docTypeCode、periodStart、periodEnd、submitDateTime（YYYY-MM-DD hh:mm）、xbrlFlag、csvFlag、legalStatus；書類取得 API type=1 提出本文書（含 XBRL）、type=5 CSV（XBRL 轉 CSV）；錯誤碼含 429 Too Many Requests。③下載官方 EDINET コードリスト https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip （不需 key，2026-09-30 現在 11,394 件）→ 6 檔全部命中：5016＝E01081（3月末日）、5802＝E01333（3/31）、6268＝E01726（12/31）、6324＝E01712（3/31）、6481＝E01678（12/31）、6594＝E01975（3/31）。④下載 2026 年版タクソノミ要素リスト ESE140114／勘定科目リスト ESE140115／IFRS 要素リスト ESE140184，確認元素名存在：jpcrp_cor:NetSalesSummaryOfBusinessResults、RevenueIFRSSummaryOfBusinessResults、CashAndCashEquivalents(IFRS)SummaryOfBusinessResults、TotalNumberOfIssuedSharesSummaryOfBusinessResults、NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc、NumberOfIssuedSharesAsOfFilingDate…；jppfs_cor:OperatingIncome、CashAndDeposits、ShortTermLoansPayable、LongTermLoansPayable、CurrentPortionOfLongTermLoansPayable、BondsPayable、CurrentPortionOfBonds、CommercialPapersLiabilities；jpigp_cor:OperatingProfitLossIFRS、CashAndCashEquivalentsIFRS、BorrowingsCLIFRS／NCLIFRS、BondsAndBorrowingsCL／NCL／LiabilitiesIFRS、InterestBearingLiabilitiesCL／NCL／LiabilitiesIFRS。⚠ 營業利益在『主要な経営指標等の推移』裡只有 USGAAP 版（OperatingIncomeLossUSGAAPSummaryOfBusinessResults），JGAAP／IFRS 要從 PL 本表取。⑤**未驗證**：沒有 key，所以沒有實際列出任何一檔的書類清單、沒有下載過任何一份 EDINET 有報／半期報告書 XBRL；上面的欄位是『仕様書＋タクソノミ說有這個元素』，不是『這 6 檔的申報裡確實有這個 tag』。
  - 我們這幾檔：6／6 有 EDINET コード（已驗證，見上）。實際申報覆蓋未驗證（無 key）。已知的特殊情況（來自 repo 既有人工觀測與 TDnet 一手 PDF）：6594.T ニデック 2026 年 3 月期有報申請延長提出期限（repo manual_observations 2026-06-16 那筆），且 2026-09-29 TDnet 公告『2026年３月期第３四半期決算短信及び2026年３月期決算短信』延到 2026-09-30 才開示——所以今天這一檔最新可用的一期財報仍是 2025 年 9 月的上半年，需要 repo 已有的 lagging 語意。5016.T 2025-03-19 才上市，上市前是否有有報（E01081 是舊編號）未驗證。5802.T 2026-07-01 生效 1:4 分割，股數序列要與 corporate_actions 對齊。會計基準（由 repo 人工觀測引用的決算短信標題與本次 XBRL 取得）：5016 IFRS（本次 XBRL DocumentName〔ＩＦＲＳ〕已驗）、5802 JGAAP、6268 IFRS、6324 JGAAP、6481 IFRS（且有非継続事業，需取『継続事業』欄）、6594 未驗證。
  - 機械或判讀：mechanical：每個數都指得回 docID＋元素名＋context，任何人重讀得同一數。例外兩處要先定規則才可機械：①有利子負債——若沿用 repo 現行『只收整行總額 tag』規則，JGAAP 公司（5802、6324）大多會缺席；若改成『分項白名單加總』是動 contract，屬使用者決定；②營收／現金在 IFRS、JGAAP 間有多個候選元素，需按 jpdei_cor:AccountingStandardsDEI 分流的白名單，歧異時照 repo 慣例拒寫、不挑一個。
- **TDnet 適時開示情報閲覧サービス（東證；決算短信 PDF＋XBRL zip，公開 31 日）**（https://www.release.tdnet.info/inbs/I_main_00.html （搜尋：https://www.release.tdnet.info/onsf/TDJFSearch/I_head ；JPX 說明 https://www.jpx.co.jp/equities/listing/disclosure/tdnet/index.html ））
  - 取得方式：免費、免註冊、無 key；無公布速率。條款：TDnet 頁面免責（/onsf/js/I_MENSEKI.js）原文『適時開示情報閲覧サービスに記載されている内容は、著作物として著作権法により保護されており、株式会社東京証券取引所に無断で転用、複製又は販売等を行うことは固く禁じます』；JPX 網站條款 https://www.jpx.co.jp/term-of-use/index.html ：『当サイトへの高頻度・高負荷に繋がる可能性のある自動取得等はご遠慮いただいております』『有料・無料を問わずJPXからの許諾を得ている場合を除き、商用目的によるデータ収集のほか如何なる用途に関わらず二次利用及び再配信はできません』。→ 個人本機低頻率抓 6 檔、只存數字不轉發，是否算『複製／二次利用』是灰區，需使用者判斷；不像 EDINET 是 PDL1.0。
  - 欄位：Summary：營收、營業利益、總資產、淨資產、期末發行股數（含庫藏）、期末庫藏股、期中平均股數、預測值；**Summary 沒有現金、沒有負債**。Attachment：BS（現金、借款分項）、PL、CI，1Q／3Q 的 CF 是任意揭露（JPX 四半期開示見直し資料 p.9：CF 計算書『投資者ニーズに応じた開示を要請』；p.27：1Q・3Q 財務諸表需附 XBRL）。季度：1Q／2Q／3Q／通期都有（2024-04 後 1Q／3Q 只存在於此）。回溯：只有 31 天。⚠ 營收元素名因公司不同（186A0 用 SalesIFRS、5016 用 NetSalesIFRS），需白名單。⚠ Summary 的 Sales／OP 是累計期間值（Q1 累計、Q2 累計…），單季要自己減。
  - 可知日：有：列表每列有開示時刻（例 16:00），XBRL 內有 tse-ed-t:FilingDate（例『2026年８月６日』）。⚠ **不得從 TDnet 文件編號推日期**：實證 5016 的 140120260805510453 編號帶 20260805，但 XBRL FilingDate 與 repo 人工觀測都是 2026-08-06 開示（L11-5 的同一類陷阱）。多數決算短信在 15:00 收盤後公布，as-of 對價格時應視為次一交易日可知。
  - 實際打過：①GET I_main_00.html → 200，列表頁只有 I_list_001_20260831.html 到 I_list_001_20260930.html；GET I_list_001_20260814.html → 404；搜尋頁的期間下拉也只有 2026/08/31～2026/09/30。JPX 頁面原文：『開示日を含めて31日分(土・日 祝日含む。)をJPXのウェブサイト(適時開示情報閲覧サービス)で閲覧できます。また、過去10年分の適時開示資料について、東証上場会社情報サービスで閲覧できます。なお、過去5年分の開示データすべてについても、有料のデータベースサービス(TDnetデータベースサービス)を利用することで縦覧可能です。』②抓 2026-09-11 一整天（4 頁、345 列）：決算短信 79 列，大多數附 XBRL zip（081220…zip），少數（例 34830）只有 PDF。③下載 https://www.release.tdnet.info/inbs/081220260911535119.zip （186A0 第1四半期決算短信〔IFRS〕）：Summary iXBRL 用 tse-ed-t 元素——SalesIFRS、OperatingIncomeIFRS、TotalAssetsIFRS、NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock（142,120,700）、NumberOfTreasuryStockAtTheEndOfFiscalYear、AverageNumberOfShares、FilingDate；Attachment（BS／PL／CI／CF／セグメント）用 EDINET 同一套 jpigp_cor 元素，BS 有 CashAndCashEquivalentsIFRS、BorrowingsCLIFRS、BorrowingsNCLIFRS、LeaseLiabilities…，另有公司自訂 ConvertibleBondType…。④POST 搜尋 q=6594／5016／6268（2026-08-31～09-30）→ 各得 10／1／1 筆非財報公告（含 ニデック 決算延期公告）；5802／6324／6481 → 0 筆。⑤31 天前的原檔 https://www.release.tdnet.info/inbs/140120260805510453.pdf 與 .zip → 403（過期即不可取）。
  - 我們這幾檔：6 檔都是東證上市，決算短信都走 TDnet（repo 既有人工觀測已逐檔引用 TDnet 決算短信）。但 31 天窗內目前沒有這 6 檔任何一份決算短信（3 月決算的 Q1 在 7–8 月、12 月決算的 Q2 在 7–8 月，都已過期）；ニデック 的 FY2026/3 Q3＋通期短信預定 2026-09-30 開示，會是窗內第一份。
  - 機械或判讀：數字本身 mechanical（XBRL 元素＋context，已用 5016 對照：Q1 NetSalesIFRS 260,604 百萬、OperatingIncomeIFRS 81,446 百萬；通期予想 1,025,000／232,000 百萬與 repo manual_observations company_guidance 的 1.025e12／2.32e11 一致）。取得合規性是 judgment（條款灰區），且只能做『往前每日捕捉』，不能補歷史。
- **J-Quants API v2（JPX総研；/fins/summary 決算短信摘要、/fins/details BS/PL/CF、TDnet アドオン /td/list /td/files）**（https://api.jquants.com/v2/fins/summary （規格 https://jpx-jquants.com/ja/spec/fin-summary ；方案 https://jpx-jquants.com/ja ；格納期間 https://jpx-jquants.com/ja/spec/data-spec ；條款 https://jpx-jquants.com/termsofservice ））
  - 取得方式：要 API key（header x-api-key），需註冊帳號。方案（方案頁原文，月額含稅）：Free ¥0／Light ¥1,650／Standard ¥3,300／Premium ¥16,500；TDnet/適時開示情報アドオン ¥11,000／月（Free 不可加）。速率：Free 5 件/分、Light 60、Standard 120、Premium 500；429 無 Retry-After，大幅超過會被封約 5 分鐘。條款：『本サービス及び本データの利用目的は、登録ユーザーのみによる私的使用の目的に限ります』，第三者可見或商用／學術不算私的使用；『無料プランへのサブスクリプションは、1年後に自動的に解約されます』（每年要重訂）。海外居住者能否註冊：未驗證。付費方案依 AGENTS 屬『任何付費』，不在常規授權內。
  - 欄位：/fins/summary（Free 起）：營收 Sales、營業利益 OP、現金 CashEq（多半只在有 CF 的 2Q／通期出現，1Q／3Q 常為空字串——此點依 JPX 1Q/3Q CF 任意揭露推得，未以實際資料驗證）、股數 ShOutFY／TrShFY／AvgSh；**沒有負債欄**。季度：1Q／2Q／3Q／FY 各一列（累計值）。/fins/details（僅 Premium）才有借款分項。回溯：Free 只有 2 年且排除最近 12 週。
  - 可知日：有：DiscDate＋DiscTime（官方說明『TDnetの正式な開示日』），訂正另立 DiscNo、不覆寫——符合 INV-6 的 as-of 語意。
  - 實際打過：①不帶 key 打 GET https://api.jquants.com/v2/fins/summary?code=6594 → 403 {"message": "The api key is required."}；v1 https://api.jquants.com/v1/fins/statements?code=6594 → 403 {"message":"Forbidden"}。②讀了官方規格頁與方案頁（2026-09-30）：/fins/summary 欄位 DiscDate（TDnetの開示日 JST）、DiscTime、DiscNo、DocType、CurPerType、CurPerSt／En、CurFYSt／En、Sales、OP、OdP、NP、EPS、TA、Eq、CFO、CashEq（現金及び現金同等物期末残高）、ShOutFY（期末発行済株式数）、TrShFY（期末自己株式数）、AvgSh；規格明文『訂正開示には新しい開示番号が割り振られ、既存レコードは上書きされません』『当社で分割調整や訂正等による過去データの遡及修正は行っておらず』。/fins/details 以 EDINET タクソノミ英文冗長ラベル為 key 提供 BS/PL/CF 全項目，但『提出者別タクソノミで定義される企業独自の項目は、本APIの提供対象外』。③格納期間表：財務情報 Free＝『12週間前〜 2年12週間前まで』、Light 5 年、Standard 10 年、Premium 20 年（資料自 2008/7/7）；財務諸表(BS/PL/CF) 只有 Premium（2009/1/13〜）；TDnet アドオン 5 年。④沒有 key，所以**沒有取回任何一檔的實際資料**。
  - 我們這幾檔：涵蓋東證全上市股（依服務說明）；逐檔覆蓋未驗證（無 key）。5016.T 上市（2025-03-19）後才有資料是合理預期，未驗證。
  - 機械或判讀：mechanical（結構化欄位、每列帶開示日與開示番號；不做分割調整，股數要自己對 corporate_actions）。但它是 JPX 的加工再散布（值取自 XBRL、以円為單位），不是申報原檔；要回指原文需另對 TDnet 原件。
- **東証上場会社情報サービス（適時開示 10 年）／TDnet データベースサービス（有料，5 年）**（https://www2.jpx.co.jp/tseHpFront/JJK010010Action.do）
  - 取得方式：上場会社情報サービス：免費網頁；受 JPX 網站條款約束（禁高頻自動取得、未經許諾不得二次利用）。TDnet データベースサービス：付費，價格未驗證。
  - 欄位：決算短信 PDF（XBRL 附件是否可下載未驗證）；欄位同 TDnet 決算短信。
  - 可知日：網頁列有開示日（依 TDnet 慣例推測，未驗證）。
  - 實際打過：只驗到兩件事：GET 首頁 → 200（9,455 bytes，表單式 Struts 頁面）；JPX TDnet 概要頁原文說『過去10年分の適時開示資料について、東証上場会社情報サービスで閲覧できます』『過去5年分の開示データすべてについても、有料のデータベースサービス(TDnetデータベースサービス)』。**沒有**實際查過任何一檔的歷史決算短信、沒確認是否附 XBRL、沒查 TDnet データベースサービス的價格與介面——皆未驗證。
  - 我們這幾檔：理論上 6 檔全有（東證上市），未驗證。
  - 機械或判讀：數字 mechanical，但取得方式是網頁表單＋條款限制自動化，實務上只適合人工偶爾補一份，不適合當機械來源。
- **TDnet 檔案的第三方鏡像（日經 irftp、Yahoo! ファイナンス storage）**（https://www.nikkei.com/markets/ir/irftp/data/tdnr/tdnetg3/20260806/g2ajxx/081220260805510453.zip （例））
  - 取得方式：免 key；鏡像網站的使用條款**未讀、未驗證**；URL 路徑規則（日期目錄、g2ajxx 片段）未公開，不能從編號可靠推出。
  - 欄位：與 TDnet 原件同（決算短信 PDF＋XBRL）。
  - 可知日：鏡像本身不給開示時刻；可知日要回 XBRL FilingDate 或原 TDnet 列表。
  - 實際打過：repo 人工觀測已用過這兩個鏡像取 PDF（5016.T 的 source_ref）。本次 HEAD 日經 .../140120260805510453.pdf → 200 application/pdf；同目錄 081220260805510453.zip → 200 application/x-zip-compressed；Yahoo https://finance-frontend-pc-dist.west.edge.storage-yahoo.jp/disclosure/20260511/20260510521173.pdf → 200。下載日經的 5016 Q1 XBRL zip（17 檔，與 TDnet 原件同結構），抽出 NetSalesIFRS 260,604／OperatingIncomeIFRS 81,446（百萬円）、期末發行股數 953,183,210、庫藏 2,288,019、BS CashAndCashEquivalentsIFRS 218,978、BondsAndBorrowingsNCLIFRS 404,067、BorrowingsCLIFRS 32,513——注意 5016 的借款 tag（BondsAndBorrowingsNCL）與 186A0（BorrowingsNCL＋自訂可轉債）不同。
  - 我們這幾檔：已確認 5016.T 有；其他 5 檔未驗證。
  - 機械或判讀：內容 mechanical，但來源是非一手主機且條款未知——只適合研究 session 人工回指原文（repo 現行用法），不建議做成機械 fetcher。
- **發行人 IR 網站（決算短信／有報 PDF）與 repo 既有 manual_observations**（例：https://www.thk.com/jp/wordpress/wp-content/uploads/2026/08/260805_financial_result_ja.pdf ；https://sumitomoelectric.com/jp/sites/japan/files/2026-05/download_documents/2025_allv.pdf）
  - 取得方式：免費，人工逐份。
  - 欄位：全部（含分部、backlog、客戶集中度等 XBRL 不一定有的判讀項）。
  - 可知日：人工記錄開示日；可靠度取決於記錄者（見上面 TDnet 編號日期陷阱）。
  - 實際打過：用 file:...?mode=ro 唯讀查 Engine C 正式庫：fundamental_history 對 6 檔 0 列；manual_observations 共 17 筆（5016×2、5802×2、6268×2、6324×7、6481×2、6594×2），欄位為 fiscal_year_results、company_guidance、segment_revenue_share、backlog、customer_concentration、runway_inputs、litigation_and_audit_flags，source_ref 逐筆指到 TDnet 決算短信（經鏡像或 IR 網站取得）；financial_snapshots（yfinance）38–63 列／檔、price_history 373–750 列／檔。repo 內沒有任何 EDINET／TDnet／J-Quants fetcher（grep fetchers/、engine_c/ 皆無）；config/source_routes.json 的 edinet 路徑是 verified:false、how 寫『（未驗證）』。
  - 我們這幾檔：6／6 都已有至少一份人工觀測，但只有最近一兩期，沒有歷史序列。
  - 機械或判讀：混合：損益表數字是 mechanical（已宣告的欄位可免 pq2），分部占比、backlog、客戶集中度是 judgment。

### KR（韓股 .KS／.KQ；repo 內 000660.KS SK hynix、005930.KS Samsung Electronics、012330.KS Hyundai Mobis）

**建議：** KR 市場有可機械取得、帶申報日的一手財報與股數來源，**首選 OpenDART API**。

**repo 現況（2026-09-30 用 mode=ro 讀正式庫）：**
- 三檔 .KS 在 price_history 各有 746 列，fundamental_history 是 0 列。
- manual_observations 只有少量（fiscal_year_results 1–2 筆等）。
- engine_c/three_question_inputs.py 對 .KS 的缺席理由寫「非美國 SEC 申報人、非台股：沒有機械的財報歷史來源（歷史不可得）」。這句現在不成立：韓股是「這條路還沒建」，不是「歷史不可得」。這和 source_routes.json 裡 DART 那條記錄的教訓同形（L11-5：「我找不到」與「它不存在」是兩個 claim）。
- fetchers/ 目前只有 EDGAR、MOPS、RNS、MFN 等，沒有 DART fetcher。

**建議做法（這是開發項，照 AGENTS.md 寫進 ROADMAP 五欄，不走 pq2）：**

1. **前置：使用者自己申請 OpenDART 個人 key。**
   - 只需要 email，即時發放，免費，每日 20,000 次。
   - key 放 .env，不 commit。
   - 個人資料每 2 年要重新同意，否則 key 失效（錯誤碼 901）。這是一個會到期的等待，要登記進 watch registry（INV-2：每個等待都必須有到期）。
   - 這一步系統做不了。

2. **財報：fnlttSinglAcntAll（fs_div=CFS）。**
   - 呼叫範圍：bsns_year 2021–2026 × reprt_code 11013／11012／11014／11011。三檔 5 年約 60 次呼叫，遠低於上限。
   - 對應 fundamental_history 現有欄位，不用改 schema：
     - accession＝rcept_no；
     - filed＝list.json 的 rcept_dt（官方欄位；rcept_no 前 8 碼只當交叉檢查，網頁清單實測 232／232 相符）；
     - form＝reprt_code 或 report_nm；
     - tag＝account_id；
     - currency＝currency。
   - 營收用 ifrs-full_Revenue，營業利益用 dart_OperatingIncomeLoss。季報損益表的 thstrm_amount 就是 3 個月值。
   - Q4 照 EDGAR 衍生 Q4 的做法：年報減 Q3 報告的累計（thstrm_add_amount），derived 欄寫兩個 rcept_no。
   - 現金用 ifrs-full_CashAndCashEquivalents。
   - **負債：三家沒有共同的單一總額行。**要不要定一組固定 tag 相加，是口徑決定，要使用者選。在決定之前，照 EDGAR 現行慣例「只有分項→淨負債缺席、已定價①退回 P/S」。

3. **股數：stockTotqySttus。**
   - 取 istc_totqy 或 distb_stock_co，as-of 用 stlm_dt，可知日用該報告的 rcept_dt。
   - 優先股與庫藏股的口徑要使用者決定一次（Samsung 有優先股）。
   - 這會改動 plan 使用者定案 #14（非美股稀釋燈續用 yfinance 快照）。改 KR 的來源要使用者定案；定案後照「逐檔單一來源、不混」切換。

4. **市值序列（已定價①）：**
   - 可以用 DART 季度股數乘價格。
   - 或用 KRX OPEN API stk_bydd_trd 的 LIST_SHRS／MKTCAP：每日、2010 起、可知日＝交易日；要會員＋key＋逐 API 核准。
   - 或用 data.go.kr 的 lstgStCnt：自動核准、每日 10,000 次、公共누리第 4 類不可再散布；回溯起點未驗證。
   - 這三條的口徑不同（上市股數 vs 發行股數），選一條，不混。

5. **PIT 的第一個驗收測試（拿到 key 後先做，還沒通過前不寫入）：**
   - 案例：SK hynix 2020 사업보고서（原始 20210322000782／정정 20210330000776）、Hyundai Mobis 2023 사업보고서（20240312000681／20240319000626）。
   - 看 fnlttSinglAcntAll 回的 rcept_no 與數字對應哪一版。
   - 如果回的是「更正版數字配原始 rcept_no」，就會 as-of 洩漏，必須改用 list.json 逐份報告或原件核對。

**不要做的事：**
- 不要用 재무정보 일괄다운로드當帶可知日的來源：沒有 접수번호／접수일자，數字會被後續정정覆寫（官方頁原文，加上檔名的重產時間戳佐證）。它只適合沒有 key 時做交叉核對。
- 不要用 data.krx.co.kr 網頁平台：要登入。

**要不要人工觀測補：**
- 不需要用人工觀測補主要的三題歷史，機械來源夠用。
- 可選的人工項只有 잠정실적：比定期報告早 16–48 天，數字只在公告本文。現行用定期報告的 rcept_dt 是「晚知道」的保守做法，不會洩漏，所以不補也不錯。
- going concern／감사의견仍然是判讀，走 Engine C 判讀寫入 gate（pq2）。

**做不到、或今天沒驗證到的：**
- 沒有 key，看不到 OpenDART 的真實回應。
- 2015 年以前 OpenDART 財報 API 不提供。
- 2015 年的 taxonomy 前綴（ifrs_）和 2016 年以後（ifrs-full_）不同，白名單要兩個都收——這一點只在일괄檔觀察到，API 是否一樣未驗證。
- KRX OPEN API 的日呼叫上限與核准時間未驗證。

**限制與未驗證：** 1. **沒有 OpenDART key。**
   - 所有 OpenDART 資料端點只驗到錯誤碼：缺 key 回 100，假 key 回 010，不帶 key 且用 curl 預設 UA 會 302 到 error1.html。
   - 欄位與回溯範圍來自官方 guide 頁原文，實際回應形狀未驗證。
   - OpenDART guide 頁的樣本 key 是 xxxx 遮罩，不像 KRX 那樣公開樣本 key。

2. **最大的 PIT 風險未驗證。**遇到 [기재정정] 的期間，fnlttSinglAcntAll 回哪一版的 rcept_no 與數字，要拿到 key 後用上面列的兩組原始／更正配對先測。
   - 三檔更正版的數量：SK hynix 10 份、Hyundai Mobis 8 份、Samsung 1 份（網頁清單 report_nm 含「정정」的列數）。

3. **rcept_no 前 8 碼＝接수일자只是經驗規則。**
   - 樣本是三檔 232 份定期報告；잠정실적公告的 rcpNo 也符合。
   - 官方文件沒有這樣寫，正式可知日要以 list.json 的 rcept_dt 為準。
   - rcept_dt 只有日期（KST），沒有時間。

4. **일괄다운로드「數字會被覆寫」的證據：**
   - 官方頁原文：「기준일자 이후로 제출인이 재무제표를 정정할 경우 수치가 변경될 수 있습니다」。
   - 檔名的重產時間戳（例 2016_4Q_PL_20241115…）。
   - 我沒有逐值比對某個更正期間的新舊數字。

5. **一次核對，不是全面核對。**只核了一份報告的兩個值：SK hynix 2026 半期的營收與營益。일괄檔、DART 原件、財報 API 三者一致，只確認了前兩者之間。

6. **口徑決定都要使用者定案，本報告不替使用者選：**
   - 總借款要不要用 tag 相加；
   - 股數用發行、流通還是上市股數，優先股算不算；
   - 是否改動 plan #14（非美股稀釋燈續用 yfinance 快照、兩個來源不混）；
   - plan #3 對其他市場印「無法量：歷史不可得」的定案，KR 是否改寫。

7. **KRX OPEN API 與 data.go.kr 只驗到欄位規格與 401／樣本端點。**
   - 日呼叫上限（KRX）、核准時間、data.go.kr 的回溯起點都未驗證。
   - data.go.kr 是 T+1 營業日下午才更新。

8. **OpenDART 申請：**申請頁表單只要求 email、密碼、用途，沒看到韓國手機本人認證。但我沒有實際註冊，非韓國居民能不能順利申請未驗證。

9. **DART 網頁搜尋的兩個行為是實測觀察，不是文件規格：**期間太長（2015-01-01 到 2026-09-30）回「조회 결과가 없습니다」、maxResults=100 回 0 列。

10. **本報告的數字是 2026-09-30 的快照。**
    - 查證方式：重跑 scratchpad 裡的 dart_search.py、ro_check.py、peek_codes.py。
    - 位置：C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2\bf551b7b-6727-49f4-a878-72e0f0d42c82\scratchpad\kr\。

11. **唯讀邊界已遵守：**
    - 沒有改 repo 的任何檔案，沒有 commit，沒有取 writer lock；
    - Engine C 只用 file:...?mode=ro 讀；
    - 所有暫存檔與腳本都在 scratchpad，沒有寫進 repo。
    - 這一輪接續了上一輪（用量上限前）留在 scratchpad 的官方頁 HTML 與 h2t.py，關鍵頁（FAQ nttId 26／29／31、條款）已重新抓取、核對內容一致。

- **OpenDART 단일회사 전체 재무제표（fnlttSinglAcntAll；另有精簡版 fnlttSinglAcnt 주요계정）**（https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020 （端點 https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json））
  - 取得方式：免費但要 key。條款 https://opendart.fss.or.kr/intro/terms.do 第 11 條原文「금융감독원이 제공하는 서비스는 원칙적으로 무료입니다」（약관 2020-01-21 施行）。速率：FAQ（POST /cop/bbs/selectArticleDetail.do，bbsId=B0000000000000000002、nttId=29）原文「개인 : 일 20,000건 (서비스별 한도가 아닌 오픈API 83종 전체 서비스 기준)」，另外「과도한 네트워크 접속(분당 1,000회 이상)은 서비스 이용이 제한될 수 있으니」；guide 頁錯誤碼 020＝超過請求上限。申請：https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do，個人會員只填 email、密碼、使用環境與用途；FAQ nttId=31 寫「개인회원 : 계정신청 완료 후 즉시 발급」。**個人資料每 2 年要重新同意，否則自動退會**（申請頁「2년마다 재동의」；錯誤碼 901＝保有期間屆滿、key 不能再用）。商用：FAQ nttId=26 寫「공익이나 타인의 권리를 침해하지 않는 선에서 데이터의 공개 및 활용은 제한되지 않습니다」。
  - 欄位：請求參數：corp_code、bsns_year（「2015년 이후 부터 정보제공」）、reprt_code（11013＝1분기、11012＝반기、11014＝3분기、11011＝사업보고서）、fs_div（CFS 連結／OFS 個別）。回應每列：rcept_no（14 碼）、sj_div（BS／IS／CIS／CF／SCE）、account_id（XBRL 標準科目 ID）、account_nm、thstrm_amount（官方原文：分／半期報告的損益表是「[3개월] 금액」）、thstrm_add_amount（累計）、frmtrm_*、bfefrmtrm_*（只有年報有）、currency。依일괄檔對同一批 XBRL 的觀察，三檔用得到的科目是：營收 ifrs-full_Revenue；營業利益 dart_OperatingIncomeLoss；現金 ifrs-full_CashAndCashEquivalents。**借款沒有單一總額行**，三家 tag 組合不同：SK hynix／Hyundai Mobis 是 CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings＋LongtermBorrowings；Samsung 是 dart_CurrentLoansReceived＋CurrentPortionOfLongtermBorrowings＋NoncurrentPortionOfNoncurrentBondsIssued＋NoncurrentPortionOfNoncurrentLoansReceived。**這支 API 沒有股數**（IssuedCapital 是자본금金額）。頻率：Q1／半期／Q3／年報四種，年報只給全年，Q4 要用減法衍生。回溯：2015 年起（11 年多）。
  - 可知日：回應只有 rcept_no，**沒有 rcept_dt**。可知日的正式來源是 list.json 的 rcept_dt（見下一項）。另外做了經驗核對：用 DART 網頁搜尋列三檔 2009–2026 全部定期報告，共 232 份，rcpNo 前 8 碼等於網頁顯示的 접수일자，232／232 全部一致。但這是觀察到的規律，不是官方文件的陳述，所以只當交叉檢查。法定上界見「자본시장법」一項。**未驗證**：遇到 [기재정정] 的期間，這支 API 回傳的 rcept_no 是原始版還是更正版、數字又是哪一版。
  - 實際打過：讀了官方 guide 頁原文（curl 抓下 HTML 轉文字）。打端點三種方式：①不帶 crtfc_key、curl 預設 UA → 302 轉到 /error1.html；②瀏覽器 UA＋crtfc_key 空值 → 200 {"status":"100","message":"인증키가 누락되었습니다."}；③假 key（40 個 0） → 200 {"status":"010","message":"등록되지 않은 인증키입니다."}。端點活著、確定要 key。**repo 內沒有 OpenDART key（.env 與環境變數都沒有），所以沒看過真實資料回應**——欄位描述只來自官方文件。另用不需 key 的 DART 原件核對同一份報告：SK hynix 반기보고서 rcpNo=20260814003509 的「2-2. 연결 포괄손익계산서」：매출액 79,318,746、영업이익 60,542,608（백만원），與下面일괄檔的值逐位相同。
  - 我們這幾檔：三檔都是 KOSPI 上市、IFRS 連結申報人，DART corp_code：SK hynix 00164779、Samsung 00126380、Hyundai Mobis 00164788（從 DART 網頁搜尋結果的 openCorpInfoNew 取得）。三檔的 2026 半期連結損益表在일괄檔裡都有 ifrs-full_Revenue 與 dart_OperatingIncomeLoss，2015 年報也都有營收與營益列。定期報告 2009 起都在（每檔 71 個報告期），但財報 API 只從 2015 開始。
  - 機械或判讀：mechanical：結構化數字，指得出 rcept_no，任何人重取都拿到同一個數。例外是兩個口徑決定，定一次之後就能機械化：①『總借款』用哪組 tag 相加（跨公司不一致）；②衍生 Q4 的規則。在定案前，照 EDGAR 慣例處理——只有分項的就讓淨負債缺席。
- **OpenDART 주식의 총수 현황（stockTotqySttus）**（https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2020002 （端點 https://opendart.fss.or.kr/api/stockTotqySttus.json））
  - 取得方式：同 OpenDART：免費、要 key、個人每日 20,000 次（83 種 API 合計）。
  - 欄位：請求：corp_code、bsns_year（2015 起）、reprt_code（四種定期報告）。回應：rcept_no、corp_cls、se（구분：증권의종류／합계／비고，可以分普通股與優先股）、isu_stock_totqy（발행할 주식의 총수）、now_to_isu_stock_totqy、now_to_dcrs_stock_totqy（含 redc 감자、profit_incnr 이익소각、rdmstk_repy、etc）、**istc_totqy（발행주식의 총수）**、**tesstk_co（자기주식수）**、**distb_stock_co（유통주식수＝Ⅳ−Ⅴ）**、stlm_dt（결산기준일）。頻率：每季一點（Q1／半期／Q3／年報），as-of 是期末 stlm_dt。回溯 2015 起。
  - 可知日：回應有 rcept_no 與 stlm_dt，沒有 rcept_dt；可知日用 list.json 的 rcept_dt 取（rcept_no 前 8 碼當交叉檢查）。和 EDGAR 封面股數不同：這裡的股數是期末數，不是接近申報日的數。
  - 實際打過：讀了官方 guide 頁原文。端點沒帶 key 時與上一項同樣 302 到 error1.html；帶 key 的回應因為沒有 key 而**未驗證**。
  - 我們這幾檔：三檔都是定期報告申報人，理論上都有。Samsung 有優先股，se 會分列普通股／優先股／合計；registry 只登記 005930.KS 普通股。實際回應未驗證。旁證：DART 清單顯示 SK hynix 2026-08-19 有「주식소각결정」與자기주식相關公告，股數確實會變動。
  - 機械或判讀：mechanical（結構化表格、有 rcept_no）。只有一個口徑要先決定一次：稀釋燈用 istc_totqy（發行總數）還是 distb_stock_co（扣庫藏股）、優先股算不算。
- **OpenDART 공시검색（list.json）——可知日（rcept_dt）的正式欄位**（https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001 （端點 https://opendart.fss.or.kr/api/list.json））
  - 取得方式：同 OpenDART。FAQ nttId=29：企業會員（要營業登記證與 IP 登記）的 공시검색／기업개황不限次數，個人會員則算在每日 20,000 次內。
  - 欄位：參數：corp_code、bgn_de／end_de（沒給 corp_code 時限 3 個月）、last_reprt_at（Y＝只看最終報告；預設 N＝連同更正版全部列出）、pblntf_ty（A＝정기공시）、pblntf_detail_ty（A001 사업보고서、A002 반기、A003 분기）、page_count 上限 100。回應：corp_code、stock_code、report_nm（會帶 [기재정정]、[첨부정정] 等前綴）、**rcept_no**、**rcept_dt（「공시 접수일자(YYYYMMDD)」）**、rm（「정」＝這份報告提交後另有更正）。
  - 可知日：有：rcept_dt 就是申報日（KST，只有日期）。可以用 rcept_no 和財報／股數 API 的回應 join。原始版與更正版各有自己的 rcept_no 與 rcept_dt，所以能分辨 as-filed 與更正版。
  - 實際打過：讀了官方 guide 頁原文。打端點：crtfc_key 空值 → status 100「인증키가 누락되었습니다」；假 key → status 010。有效回應未驗證（沒有 key）。不需要 key 的等價路線是 DART 網頁搜尋（見第 5 項），已實測。
  - 我們這幾檔：三檔都有。網頁版實測到的定期報告數：SK hynix 81 份（其中 10 份是정정）、Samsung 72 份（1 份정정）、Hyundai Mobis 79 份（8 份정정），範圍 2009-03 到 2026-08。
  - 機械或判讀：mechanical。
- **OpenDART 재무정보 일괄다운로드（整批 TXT，不需 key）**（https://opendart.fss.or.kr/disclosureinfo/fnltt/dwld/main.do （清單 POST https://opendart.fss.or.kr/disclosureinfo/fnltt/dwld/list.do；下載 https://opendart.fss.or.kr/cmm/downloadFnlttZip.do?fl_nm=<檔名>））
  - 取得方式：免費、不需 key、不需登入（今天 2026-09-30 實測的結果）。頁面宣告「금융감독원이 이 정보의 정확성 및 완전성을 보장하는 것은 아닙니다」，過度存取可能被「예고 없이 제한 및 중단」。
  - 欄位：營收、營業利益、現金、借款各分項（BS）、현금흐름、자본변동都有；**沒有股數**。季度與年度都有（損益表有 3 個月值與累計值）。回溯：2015 年只有年報，2016 起四期齊全。
  - 可知日：**沒有。**頁面原文：「기준일자 이후로 제출인이 재무제표를 정정할 경우 수치가 변경될 수 있습니다」。檔名的產生時間戳也顯示舊期間的檔案會在多年後重新產生（例：2016_4Q_PL_20241115…、2016_1Q_PL_20230119…、2015_4Q_PL_20230503…）。所以檔裡是『最新版的數字』，不是 as-filed；如果拿定期報告的接수일자去貼這些數字，更正後的值會被標成原始申報日，形成 as-of 洩漏（INV-6）。
  - 實際打過：實際打了。list.do 回 172 個 zip，年度 2015–2026：2015 只有 FY，2016 起每期都有 FQ／HY／TQ／FY，每期 BS／PL／CF／CE 四檔。**沒有登入也能下載**：2026_2Q_PL（3,845,025 bytes）、2026_2Q_BS（5,216,224 bytes）、2015_4Q_PL（2,660,031 bytes）都下載成功，內容是 cp949 編碼、tab 分隔。表頭：재무제표종류、종목코드、회사명、시장구분、업종、업종명、결산월、결산기준일、보고서종류、통화、항목코드、항목명、當期 3 個月／累計、前期…。**表頭沒有 접수번호，也沒有 접수일자。**2015 年的檔用舊 taxonomy 前綴 ifrs_Revenue（2026 年是 ifrs-full_Revenue），欄位排列也不同；Hyundai Mobis 另有 entity00164788_udf_* 自訂科目。
  - 我們這幾檔：三檔都在：2026 半期連結 PL／BS 都命中，2015 年報 PL 也命中營收與營益。
  - 機械或判讀：數字本身是 mechanical，但**不能當帶可知日的來源**：沒有 rcept_no，而且數字會被覆寫。只適合沒有 key 時做冷啟動核對，或交叉驗證 API 回來的值。
- **DART 網頁版搜尋＋原件 viewer（repo 既有路線 config/source_routes.json key=dart，不需 key）**（https://dart.fss.or.kr/dsab007/detailSearch.ax ；https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<rcpNo> ；https://dart.fss.or.kr/report/viewer.do）
  - 取得方式：免費、不需 key、HTML 抓取、沒有公開的速率條款（未驗證）。repo 已登記為 rung 2 追源路線，verified=true。
  - 欄位：清單：rcpNo、公司、報告名（含정정前綴）、접수일자、corp_code。原件：整份報告逐節 HTML，包括連結財報、주석、「주식의 총수 등」、매출 및 수주상황。季度與年度都有，2009 起。
  - 可知日：有：清單的 접수일자，原始版與更正版分列。
  - 實際打過：實際打了。detailSearch.ax 要先 GET main.do 拿 cookie。**一次查的期間不能太長**：2015-01-01 到 2026-09-30 回「조회 결과가 없습니다」，切成 3 年一段就正常。maxResults=100 回 0 列，30 就正常。publicType=A001/A002/A003 可以只篩定期報告。三檔共 232 份定期報告，rcpNo 前 8 碼與 접수일자 232／232 相符。原件 viewer 取 SK hynix 20260814003509 的「2-2. 연결 포괄손익계산서」成功（目錄 128 個節點）。另外用 publicType=I002 查到 2026 年的 잠정실적 公告（見第 10 項）。
  - 我們這幾檔：三檔都有。定期報告 2009-03 到 2026-08，每檔 71 個報告期。
  - 機械或判讀：清單（rcpNo 與 접수일자）是 mechanical。原件表格要解析 HTML，節點名稱與版面會隨年份與公司變動，比較脆弱——適合人工追源與逐列核對（現行用途），不適合當主要的機械回填。
- **KRX Data Marketplace OPEN API 유가증권 일별매매정보（stk_bydd_trd）——每日上市股數／市值**（https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd?BO_ID=JvJFzlAENzZlPBDNGAWC （端點 https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd））
  - 取得方式：要註冊 Data Marketplace 會員、申請 key，而且每一支 API 要另外申請使用、等管理員核准（OPPINFO003 流程：「인증키 신청 (관리자 승인 후 사용 가능)」「API 활용 신청 후 관리자 승인대기」）。申請時要選使用期間 1M／3M／6M／12M，用途可選「개인 연구」。**每日呼叫上限與核准要多久：未驗證**（FAQ 是動態載入，沒抓到）。KRX 的 data.krx.co.kr 網頁資料平台不登入時回 400「LOGOUT」（見第 8 項）。
  - 欄位：只有股數與市值（每日），沒有財報。一次呼叫回全市場當天全部個股，3 年大約 750 次呼叫。回溯到 2010-01-04。
  - 可知日：BAS_DD 是交易日。那天收盤後就知道上市股數與市值，可知日＝BAS_DD。
  - 實際打過：服務清單（POST OPPUSES001_S1D1.cmd path=sto）列出這支 API：「유가증권시장에 상장되어 있는 주권의 매매정보 제공 ('10년01월04일 데이터부터 제공)」；規格頁 2020/09/22 登記、2026/01/16 修改。解碼頁內的 bld XML，輸出欄位有 BAS_DD、ISU_CD、ISU_NM、MKT_NM、TDD_CLSPRC、…、**MKTCAP（시가총액）**、**LIST_SHRS（상장주식수）**；輸入只有 basDd。正式端點不帶 key → 401 {"respMsg":"Unauthorized Key"}。用官方頁公開的樣本 key 打樣本端點 /svc/sample/apis/sto/stk_bydd_trd.json?basDd=20200414，回了真實形狀的資料（例：088980 맥쿼리인프라 LIST_SHRS 349044336、MKTCAP 3909296563200）。
  - 我們這幾檔：三檔都是 KOSPI（유가증권），在這支 API 的範圍內；實際回應未驗證（沒有 key）。Samsung 優先股 005935 是另一個 ISU_CD。
  - 機械或判讀：mechanical。要注意口徑：LIST_SHRS 是上市股數，和 DART istc_totqy（發行總數）或 distb_stock_co（流通股數）不是同一個量；照 plan #14「兩個來源不混」，一檔只能選一種。
- **공공데이터포털 금융위원회_주식시세정보（getStockPriceInfo）——每日上市股數／市值**（https://www.data.go.kr/data/15094808/openapi.do （端點 https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo））
  - 取得方式：「비용부과유무 무료」；「개발계정 : 10,000」次／日；開發與營運階段都是「자동승인」。授權是公共누리第 4 類：「출처표시 + 상업적 이용금지 + 변경금지」，而且「제3자 무단 제공 및 재배포가 엄격히 금지」——本機自用沒有衝突，但不能再散布。頁面說明更新時間是「기준일자로부터 영업일 하루 뒤 오후 1시 이후」。
  - 欄位：每日行情＋lstgStCnt＋mrktTotAmt，沒有財報。**回溯起點未驗證**。
  - 可知日：basDt 是交易日。但資料是 T+1 營業日下午才上架——如果要比對『那天我手上有沒有』，要注意這一天延遲；以交易日當可知日，語意上仍是當天收盤後可知的市場事實。
  - 實際打過：讀了官方頁：欄位 schema 有 lstgStCnt（「종목의 상장주식수」）、mrktTotAmt、basDt（기준일자），查詢參數有 basDt／beginBasDt／endBasDt／likeSrtnCd 等。端點不帶 key → 401 {"errMsg":"SERVICE_KEY_IS_NULL"}。有效回應未驗證。
  - 我們這幾檔：KRX 上市股都在範圍內，三檔應該都有；實際回應未驗證。
  - 機械或判讀：mechanical；口徑與 KRX LIST_SHRS 相同（上市股數），同樣不能和 DART 股數混用。
- **KRX 정보데이터시스템（data.krx.co.kr，网页資料平台）**（https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd （bld=dbms/MDC/STAT/standard/MDCSTAT01701））
  - 取得方式：要登入會員；自動化條款未查。
  - 欄位：（沒拿到資料，無法確認）
  - 可知日：（未驗證）
  - 實際打過：實際打了：先 GET mdiLoader 頁（200），再 POST getJsonData.cmd → 400，內容 6 bytes「LOGOUT」。不登入就拿不到。
  - 我們這幾檔：（未驗證）
  - 機械或判讀：不建議：需要登入 session 抓取；同一份資料已有第 6 項（KRX OPEN API）這個正式介面。
- **자본시장과 금융투자업에 관한 법률 第 159／160 條（法定申報期限；可知日的備援上界）**（https://www.law.go.kr/LSW/lsSideInfoP.do?lsiSeq=283193&joNo=0159&joBrNo=00&docCls=jo&urlMode=lsScJoRltInfoR （160 條把 joNo 改成 0160））
  - 取得方式：免費公開條文。
  - 欄位：只有期限規則，沒有數字。
  - 可知日：法定上界：年報是期末加 90 天，半期／季報是期末加 45 天（首次連結可 60 天）。只有拿不到 rcept_dt 時才當保守備援；有 rcept_dt 就用 rcept_dt。
  - 實際打過：讀了 law.go.kr 條文原文，現行版本「[시행 2026. 2. 3.] [법률 제21324호]」。159 條①：「사업보고서를 각 사업연도 경과 후 90일 이내에 금융위원회와 거래소에 제출하여야 한다」。160 條①：반기／분기보고서「각각 그 기간 경과 후 45일 이내」，以連結為準首次申報時「그 최초의 사업연도와 그 다음 사업연도에 한하여 … 60일 이내」。觀察值吻合：SK hynix FY2025 年報 2026-03-17（第 76 天）、Q1／半期／Q3 都在第 45 天。
  - 我們這幾檔：三檔都適用（주권상장법인）。
  - 機械或判讀：mechanical（規則）。
- **DART 연결재무제표기준영업(잠정)실적(공정공시)——比定期報告更早公開的初步業績**（https://dart.fss.or.kr/dsab007/detailSearch.ax （publicType=I002））
  - 取得方式：網頁免費；OpenDART list.json（pblntf_ty=I）也列得到，但數字只在文件本文裡。
  - 欄位：營收、營業利益、稅前損益、淨利的初步值，只有季度；沒有現金、負債、股數。數字格式是公告本文表格，不在任何結構化財報 API 裡（我沒找到；是否有結構化來源未驗證）。
  - 可知日：有：접수일자（rcpNo 前 8 碼，這類公告的 rcpNo 第 9–10 碼是 80）。
  - 實際打過：實際打了，查 2026 年。Samsung 13 筆공정공시，其中잠정실적：2026-04-30、2026-07-07、2026-07-30（另有同日 [기재정정]）。SK hynix：2026-01-28、2026-04-23、2026-07-29。Hyundai Mobis：2026-01-28、2026-04-24、2026-07-24。對照定期報告：SK hynix FY2025 잠정 2026-01-28 → 사업보고서 2026-03-17（早 48 天）；Q2 잠정 2026-07-29 → 반기보고서 2026-08-14（早 16 天）。
  - 我們這幾檔：三檔都有，每季一次。
  - 機械或判讀：judgment（要從公告本文解析表格，而且잠정值之後會被正式報告取代）。如果需要，走人工觀測；不是必要。
