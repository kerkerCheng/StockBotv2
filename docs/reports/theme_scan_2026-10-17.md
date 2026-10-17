# 題材掃描 — 2026-10-17

- 窗：2026-10-04（上一份 `theme_scan_2026-10-04.md`）～2026-10-17；`config/themes.txt` 8 組（cpo、sivers、robotics、power、cooling、cnbio、aibio，另加一組「題材外的集中需求」outside），每組 2–3 次 WebSearch、0–2 次 WebFetch。
- 本輪邊界（`skills/theme-scan`）：只發現、不處置——沒有追源、抽取、入圖，沒有對任何 pq2 編號給 go／drop。觸發：心跳「已 13 天沒掃題材（門檻 7 天）」＋使用者 10-17「然後掃題材」。
- Stage 0：`python -m engine_b.cli onboard-candidates` 99 個（lead 逐字點名、名冊沒有）；其中 10-04 之後第一次被點名的 18 個。
- 執行：互動 session 的唯讀 workflow（8 位，一組一位；寫入只有 Stage 2 的 3 則 lead 註冊，由主 session 做）。

## 30 秒 brief

- **電力：固態變壓器（SST）第一次有出貨時間線**——台達說 2026 年底出貨 100 台、2028 年才顯著放量；Eaton 本季開始出中壓 SST、明年量產；Infineon 供 SiC 給 Eaton MVSST 2.0。三則都是轉述。系統整合商都是大型股，值得研究的是 SST 下一層（高壓 SiC 模組、中頻變壓器磁芯）有沒有薄的供應商；這也是 Wave 2「800VDC 回看」的時間錨。→ research
- **散熱：名冊外的榮惠-KY（6924）營收在放量**——9 月 2.92 億元、年增 141.5%（鉅亨寫成「141 倍」，要以 MOPS 為準），3Q26 7.2 億元創新高，公司說 CDU 出貨暢旺、客戶追加水冷模組與快接頭。它坐哪一層、客戶是誰還答不出來。→ onboard 評估
- **cnbio：中國擬加生技出口管制、但豁免授權交易**——發布機關、日期、條文都還沒看到原文（Qz 403）。它正碰到這條鏈頭的反證條件「授權放緩」；要先拿到條文，才判得出它是反證還是脈絡。→ research
- 光通訊（cpo、sivers）、機器人、題材外：窗內沒有在 daily 範圍外的新結構事件。OCP 週（10-13～16）的光通訊事件已由 daily 的 X 帳號抓到，在 drain 處理。
- 本輪沒有新需求錨。

## Topic Digest

### 1. 固態變壓器從展示走到出貨（power）→ research

- **摘要**：①Taipei Times 2026-10-15 轉述台達：2026 年底前出貨 100 台 SST，「looks forward to a more significant increase in shipments in 2028」；產品把中壓 AC 直接轉成 800V DC，整合 SST、DC/DC 與控制；資料中心是最大占比，主要市場是美國與中國的雲端業者；產能目前在中國，台灣廠「expected to be completed soon」，Dallas 擴產排在明年。同一篇轉述 Eaton 本季已開始出貨中壓 SST、明年進入量產。②EE Times Asia 2026-10-06 轉述：Infineon 供 SiC 功率元件給 Eaton MVSST 2.0（800VDC、亞太）；雙方在評估下一代改用 2.3kV／3.3kV SiC 模組，沒有量產時程。③DG Matrix（私人）在 OCP 發表模組化 SST cell，AC 輸入最高 34.5 kV、輸出 800 VDC（轉述，日期未確認）。
- **來源**（全部轉述）：https://www.taipeitimes.com/News/biz/archives/2026/10/15/2003865972 ／ https://www.eetasia.com/infineon-eaton-target-800vdc-ai-data-centers-with-sic-solid-state-transformers/ ／ https://transformer-magazine.com/news/dg-matrix-unveils-800-vdc-sst-system/
- **影響**：給 800VDC 鏈的 SST 一條時間線——2026 年底小量、2027 年 Eaton 量產、2028 年台達放量；上游拉貨落在 2027–2028 年。反過來看，SST 的量還小，近期替代不了大型電力變壓器，也緩解不了 LPT 與電工鋼的吃緊。
- **為何值得研究**：①2.3kV／3.3kV SiC 模組能量產的有幾家 ②中頻變壓器的奈米晶或鐵氧體磁芯由誰供應 ③台達、Eaton 的一手文件有沒有具名這些上游。先把「100 台／2028 放量」與 Eaton「本季出貨、明年量產」追回一手（現在都只有 Taipei Times 轉述）。

### 2. 榮惠-KY（6924）液冷 CDU 與水冷零組件放量（cooling）→ onboard

- **摘要**：9 月合併營收 2.92 億元、月增約 20.5%、年增 141.5%；3Q26 7.2 億元，季增 39.9%、年增 80.3%，單月與單季都創新高。報導原文：「CDU（冷卻分配單元）出貨量暢旺」「客戶追加水冷模組與水冷快速接頭（QD）、感應器、PCBA、板金機殼等相關零組件」「新開發美系客戶出貨量擴大」；沒有點名客戶或平台。工商時報 10-12：股價漲停。
- **來源**（四篇都轉述同一份營收公告與公司說法，獨立性只算一個 origin）：https://news.cnyes.com/news/id/6625997 ／ https://news.nextapple.com/finance/20261011/8D10C372E1093C71AC28B01AB9ECB69D ／ https://www.ctee.com.tw/news/20261012700803-430201
- **影響**：可能是 CDU／液冷模組這一層的一家小供應商，營收已在數字裡；但它是 CDU 代工組裝，還是快接頭、感應器、板金這類可替代零組件的整合商，現在看不出來，所以讀不到邊（客戶為什麼選它、什麼會讓它被換掉）。注意 CDU 層的現行讀圖判 neither（供給側多家、新進者一年內做進來）。
- **為何值得研究**：名冊外、邊緣量級、直接連到 CDU 與快接頭兩層。onboard 要追：MOPS 月營收一手、年報的產品組合與 CDU 是自有品牌還是代工、「美系客戶」有沒有客戶端或第三方印證（L8：供應商自述不能當自己是瓶頸的獨立佐證）。

### 3. 名冊內台股液冷廠 9 月營收（cooling）→ FYI

- 高力（8996）9 月 16.1 億元、年增 153.7%，前三季 94.7 億元、年增 120.78%；分產品是板式熱交換器年增 19.94%、熱能產品年增 163.69%——**放量在熱能產品，而這個科目把燃料電池熱元件和液冷混在一起**，不能直接讀成板式熱交換器層緊（L12）。
- 富世達（6805）9 月 16.13 億元、年增 32.17%；轉述的「水冷接頭月產能 4Q 由 300 萬顆拉到 450 萬顆」與快接頭層說明的主張 Q4（產能資本輕、以季加得上去）同方向——是供給放寬的訊號，不是吃緊。
- 都是名冊內公司的例行月營收，由 daily 的財務觀測處理；不建 lead。

### 4. 中國擬加生技出口管制、但豁免授權交易（cnbio）→ research

- **摘要**：Qz 標題「China proposes biotech export controls that exempt licensing deals」、The Edge Malaysia「China looks to tighten biotech exports, allows licensing deals」。兩次 WebFetch 失敗（Qz 403）；發布機關（推測商務部，未見原文）、意見截止日、管制範圍、豁免條件都沒有確認。網址尾碼像 2026-10-16，沒讀到原文，日期不填。
- **來源**（轉述）：https://qz.com/china-biotech-export-controls-licensing-deals-exemption-101626 ／ https://theedgemalaysia.com/node/822141
- **影響**：若授權真的豁免，鏈頭不會被切斷，10-07 的需求歸因（猴需求的一手歸因是創新藥授權）照樣成立；若管制涵蓋 IND 資料包、生物材料或跨境 CRO 服務，「授權 → 中國安評 → 猴需求」這條邊的傳導會變。
- **為何值得研究**：要追徵求意見稿原文的四件事——發布日與截止日、清單是否列臨床前資料／細胞株／生物樣本／實驗動物、豁免授權的逐字條件、生效日。

### 5. 中國對外授權金額年初至今再創紀錄（cnbio）→ FYI

- Reuters Breakingviews 2026-10-16（付費牆，數字來自搜尋摘要）：截至 2026-10-08 中國生技對外授權 1,394 億美元，超過去年全年；前三季預付款 80 億美元，高於 2025 全年的 72 億美元。資料供應商與口徑未確認（L11-3）。窗內具名交易 Roche × Rona Therapeutics（最高約 11.6 億美元）；窗外 Novartis × Abogen（預付 5.75 億美元，CNBC 10-02）。兩家授權方都未上市。
- 鏈頭在窗內繼續上行，沒有「授權放緩」的反證；不改 10-07 結論（上市公司層沒有候選，等天勤生物、鼎泰藥研掛牌）。

### 6. Ginkgo Datapoints 拿下 Lilly TuneLab 資料生成合約（aibio）→ FYI

- 轉述（2026-10-11 彙整頁）：Ginkgo 與 Eli Lilly TuneLab 簽 data-generation agreement；另組 10,000 抗體的可開發性聯盟（與 Apheris）。沒有金額。TuneLab 的濕實驗供應商因此至少 3 家（Twist、Charles River、Ginkgo）——偏向商品化。Ginkgo 在 10-07 已評過（A6 層判否），這次沒有推翻它的數字。留給 ew_0318（AI 新藥需求端，11-30 到期）重問時當數據點；一手新聞稿要從 Ginkgo IR 核對。

### 7. 大藥廠 × AI 設計公司的授權持續（aibio）→ FYI

- Zealand Pharma × Generate Biomedicines 2026-10-13 一手新聞稿（GlobeNewswire）；AstraZeneca × insitro（預付 4,000 萬美元、里程碑最高 14.6 億美元，pharmaphorum 轉述，公告日未核）。錢流向 AI 設計方，沒有點名下游濕實驗供應商——與 10-07 記錄的模式相同，不產生候選。

### 沒有建 topic 的組（看了，沒找到；不是沒看）

- **cpo**：3 次搜尋、2 次抓取。Tower × NewPhotonics（9 月，窗外、兩家在名冊）、switch 側 CPO 雷射 merchant 只有 Lumentum 與 Coherent 的轉述（09-24，窗外）、POET 6-K（08-13，窗外）都不列。
- **sivers**：Cision 一手新聞稿 09-15 之後只有兩則、都在窗外（09-24 高管異動；09-29 臨時股東會通知：稽核師換 EY 的理由原文是「potential dual listing of the shares in the United States, expected to be completed during the first half of 2027」、P11 選擇權約 2.0% 稀釋）。10-22 股東會在窗後。
- **robotics**：Agility 經 CCXI 掛牌的時程（S-4 生效、約 11 月股東會）已由 lead_8600523b 停放處理——de-SPAC 完成時是名冊身分事件（INV-1：ticker 不是 entity identity），要從 EDGAR 確認新代號。Schaeffler × Humanoid（05-13，窗外）不列。
- **outside**：三次搜尋回來多是無日期或窗外的彙整頁。WF6 特氣漲價（Digitimes 07-28，窗外；本機 0 命中，是現有題材沒涵蓋的一層，需求錨是記憶體 fab）、HVLP4 銅箔缺口（06-11，窗外）只記為下次的起點。
- **power** 其餘：LPT 交期與電工鋼、套管與分接開關搜到的都是無日期的常青整理文；Eaton、Hitachi Energy、Siemens Energy 的擴產都在窗外。反證（交期緩解、擴產過剩）窗內沒命中——只搜一次，是「沒命中」不是「沒發生」。
- **沒看的**（下次補）：cooling 的反證面（air cooling sufficient、rear-door）、浸沒式與分歧管；cnbio 的 NAMs 替代；aibio 的反證（AI 設計藥臨床失敗、生技募資下滑、基因合成降價）。

## 建議 onboard 候選（只提名）

- **榮惠-KY（6924）**：名冊外（topic 2）。被點名 0 次（不是 cashtag 管道進來的），樣本標題「AI液冷組件需求訂單激增 榮惠9月、Q3營收雙創新高本季展望樂觀」。
- `onboard-candidates` 前十（點名數）：BE 10、QCOM 9、CXMT 8、SPCX 8、ASX 5、DRAM 5、EWY 5、SMTC 5、ALAB 4、AMKR 4——多數是大型股或 ETF（DRAM、EWY），邊緣與否要跑 `python -m alpha edge`，這裡不判。
- 10-04 之後第一次被點名的 18 個：APH 3；ADI、AGLT、COHU、CSCO、DELL、ILMN、KOSPI、NXPI、RMBS、SNPS、SSNLF、STX、T、TWST、TXG、WDC、XNDU 各 1。AGLT 是 Agility 的預定新代號（見上）。

## 新錨提案

- 無（SST 屬既有的電力鏈與 800VDC，不是新實體系統）。

## 本次註冊的 lead

- `lead_3b9966f3db00f1077e0a76f25396182a` ← `theme_scan:power`（SST）
- `lead_dd35eb3dd08b5e8af830582292e996cb` ← `theme_scan:cooling`（榮惠-KY）
- `lead_f12babb10f57aee0bd83e1149c91641d` ← `theme_scan:cnbio`（生技出口管制）

三則都已 triage go，由同日的 research-drain 接手。
