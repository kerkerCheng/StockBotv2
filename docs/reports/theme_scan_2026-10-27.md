# 題材掃描 — 2026-10-27

- 窗：2026-10-17（上一份 `theme_scan_2026-10-17.md`）～2026-10-27；`config/themes.txt` 6 組（cpo、sivers、robotics、power、cooling、aibio），另加一組「題材外的集中需求」（outside）。每組 2–3 次 WebSearch，Iambic S-1 附件用 1 次 WebFetch 看是什麼合約。
- 邊界（`skills/theme-scan`）：只發現、不處置——沒有追源、抽取、入圖，也沒有對任何 pq2 編號給 go／drop。觸發：使用者 2026-10-27「掃題材」（心跳提醒「已 10 天沒掃題材」）。
- 這一輪兼補雷達：daily 的外部雷達 10-24～10-27 四輪都沒跑——10-24、10-25 撞週額度，10-26、10-27 OAuth 過期。所以這份窗口刻意蓋住 10-17～10-27，用題材層級補那四天。逐條雷達（每個主題最近 7 天最重要的一則＋輪替層 14 天）會在 daily 恢復後自己往回補 7 天，但每個主題只收一則，補不滿四天。
- Stage 0：`python -m engine_b.cli onboard-candidates` 共 105 個（lead 逐字點名、名冊沒有）。10-17 之後第一次被點名的有 16 個：PANW、ACMR、ANT、APPL、BABA、FTNT、HPE、OKTA、PONY、QQQ、SMH、SOX、SOXX、TMUS、WRD、XLP。全是大型股、ETF、拼錯的代號，或已處理過的（ACMR 今天已停放），沒有邊緣候選。
- 執行：主 session 自己跑（沒有開子代理）。

## 30 秒 brief

- **robotics：Tesla 10-22 的 Q3 法說說 Optimus 已在 Fremont 高量產線開始早期生產**，目標約一年內每週 2 萬台，明年底開始對外交付；同一場也說 2027 年的 Megapack 幾乎賣完。這兩句都還只有轉述，所以先註冊一則 lead 核對逐字稿。它是這次漏抓的實例：落在雷達停擺那幾天，EDGAR 雖抓到同一天的 8-K，但分類時只拿到封面頁、判成 no_go（見下方「附帶發現」）。→ research
- **power：變壓器零件比本體更緊的說法在擴散**——轉述稱套管交期最長約 130 週、有載分接開關約 80–90 週。圖上已有套管與分接開關兩層，這輪找到的都是彙整站與部落格，沒有一手。→ FYI
- cooling、cpo、sivers、aibio、outside：窗內沒有 daily 範圍外的新結構事件。富世達快接頭擴產是供給放寬的方向；Sivers 光達量產單由 daily 抓到；aibio 找到的都是授權與合作，不過三問。
- 本輪沒有新需求錨。NAND SLC／HBF 由使用者同日另外點名 decompose，不在這份報告裡提案。

## Topic Digest

### 1. Tesla Q3 2026 法說：Optimus 早期生產、Megapack 2027 幾乎賣完（robotics；附 power）→ research

- **摘要**：轉述（Benzinga、Yahoo、KuCoin、Not a Tesla App）稱：Tesla 已在 Fremont 的高量產線開始 Optimus「early production」；目標約一年內達每週 2 萬台，初期爬坡「shallow slope and somewhat bumpy」；手與手指是最難的硬體；明年底前後開始交付外部公司。同一場法說稱 2027 年 Megapack「almost sold out」，並盡量提高 Megapack 產量；儲能部署 13.7 GWh、毛利率 33.1%（含關稅退款與電芯保固補償）。
- **來源**（轉述與逐字稿網址；一手要對 8-K 附件 99.1 與逐字稿原句）：
  - https://www.fool.com/earnings/call-transcripts/2026/10/22/tesla-tsla-q3-2026-earnings-call-transcript/
  - https://finance.yahoo.com/energy/articles/tesla-ramping-megapack-production-much-000131653.html
  - https://www.sec.gov/Archives/edgar/data/0001318605/000162828026066738/exhibit9914.htm
- **影響**：
  - 人形機器人那幾層（致動器、行星滾柱螺桿、減速機、馬達）的需求錨有了時間點。10-22 的 10-Q 只寫「preparations and investments in large-scale production」（`lead_6e5fa645` 停放理由），法說多了量產線與週產目標。
  - Megapack 那句是供應商自己說 BESS 層的供給吃緊，可以補今天剛入圖的 [872] BESS 層。
- **為何值得研究**：要確認三件事——逐字稿原句；8-K 附件有沒有寫 Optimus 產線與 Megapack 交期；有沒有任何具名的致動器或電芯供應商。沒有具名供應商就只是需求錨的時點，進敘事的脈絡，不進邊。

### 2. 變壓器零件（套管、分接開關）交期比本體長的說法在擴散（power）→ FYI

- **摘要**：彙整站寫高壓套管交期最長約 130 週、有載分接開關約 80–90 週；美國唯一的電工鋼產地是 Cleveland-Cliffs Butler Works；Siemens Energy 投資約 3,000 萬美元擴充義大利的套管產能（日期沒看到原文）；Hitachi Energy 密西西比 5.28 億美元變壓器廠 2029 年投產（2026-09，在窗外）。
- **來源**（全是二手）：https://greentechlead.com/power/global-transformer-shortage-in-2026-why-prices-are-rising-and-vendors-are-expanding-factories-55963 ／ https://distroforge.com/blog/transformer-bushing-lead-times-component-spec/ ／ https://www.industrialsage.com/power-transformer-lead-times-us-grid-shortage/
- **影響**：如果屬實，大型變壓器層的卡點在零件，不在組裝；但圖上套管、分接開關兩層已經有供應邊，供應商又多是私人公司或綜合大集團（failure log #72）。
- **為何不建 lead**：沒有一手；兩層已在圖上，等一手由 daily（Siemens Energy、Hitachi Energy 的申報與新聞稿）帶進來。

### 3. 名冊內液冷廠的供給放寬訊號（cooling）→ FYI

- 富世達（6805）第 4 季把水冷接頭月產能由 300 萬顆提高到 450 萬顆，規劃 2027 上半年再到 600 萬顆（MoneyDJ 轉述：https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=e8648abc-1a61-4961-b101-463f259552ec）。跟快接頭層說明的 Q4 主張同方向（產能資本輕、以季加得上去），是供給放寬，不是吃緊。
- 榮惠-KY（6924）9 月營收、Q4 加單——10-17 已提名 onboard（`lead_dd35eb3d`），沒有新事實。

### 4. Sivers 光達量產單（sivers）→ FYI

- 10-20 Sivers 公告策略光達客戶下量產單、第四季開始出貨，產品生命週期累計營收潛力 5,300 萬～1.38 億美元；daily 的 sivers:press 已抓到，在 drain 處理。

### 5. AI 生醫：只有授權與合作（aibio）→ FYI

- GSK 擴大與 Chai Discovery 的合作（10-09）、Lonza 與 Onava 合作（10-09）、AstraZeneca 付 insitro 4,000 萬美元預付（10 月）、Iambic Therapeutics S-1 的附件 10.12（與 Takeda 的研究合作與授權合約，2026-02-03）。
- 全部只中三問的第 1 問（付錢的是藥廠或 AI 公司本身，買的是授權或研究服務），沒有一則是 AI 程式向濕實驗供應商買實體輸入的量（`config/themes.txt` aibio 的判準）。不建 lead。
- 來源：https://www.contractpharma.com/breaking-news/chai-discovery-gsk-announce-collaboration-following-wet-lab-evaluation/ ／ https://www.contractpharma.com/breaking-news/lonza-onava-strike-ai-biologics-pact-to-speed-drug-discovery/ ／ https://www.sec.gov/Archives/edgar/data/0001997038/000119312526396704/iam-ex10_12.htm

### 沒有建 topic 的組（看了，沒找到；不是沒看）

- **cpo**：窗內一般搜尋只回產業指南與舊聞；Lumentum 執行長「賣到 2029 年初」（10-09）、Tower 與 Semtech 擴大協議（10-13，已在圖上 `tower_semtech_sige_capacity_agreement_2026_10_13`）都在窗外或已處理。
- **outside**：記憶體 2027 年賣完、雲端產能預售到明年都由 daily 的 X 帳號抓到；Bloomberg 10-13「電力與人才是最大瓶頸」是泛論。

## 附帶發現（不是題材，是漏抓的機制）

- **分類器只看得到標題時，會把 lead 判 no_go。** 2026-09-01 起有 25 則 triaged_no_go 的理由是「原文為空／原文空白／僅有標題」。
  - 來源分布：EDGAR 8 則（TSM、TSEM×3、GFS、POET、CCXI 的 6-K／8-K，TSLA 10-21 的 8-K）、外部雷達 14 則、MFN 3 則。
  - 雷達裡有幾則看起來不該丟：Samsung 基板擴產拿到客戶支持（digitimes 10-06）、AVC 6MW CDU、Wiwynn／Ayar Labs／GUC 的 CPO 展示。
  - 這不是三天停擺造成的，是系統性的：EDGAR 6-K／8-K 的主文件是封面頁，內容在附件；雷達只給標題與網址。
  - 已記進 failure log；處置（重新分類這 25 則、修分類前抓全文）由互動 session 決定。
  - 查證：`python library/private/wf_tmp/empty_text_nogo.py 2026-09-01`（本機暫存腳本）。

## 建議 onboard 候選

- 無新增。10-17 提名的榮惠-KY（`lead_dd35eb3d`）照舊。

## 新錨提案

- 無（NAND SLC／HBF 是使用者同日直接點名的 decompose，不經提案）。

## 本次註冊的 lead

- `lead_90dce94b320190f12cffec9b31861846` ← `theme_scan:robotics`（Tesla Q3 法說：Optimus 早期生產、Megapack 2027 幾乎賣完）
