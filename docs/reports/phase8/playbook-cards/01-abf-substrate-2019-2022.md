# 劇本卡 1｜ABF 載板 2019–2022

> 段：ABF 載板｜期間：2019–2022｜清單上寫的結尾的型：供給追上＋下游庫存修正
> 錨：伺服器與高效能運算的處理器（買家：Intel、AMD）｜層：處理器用的 ABF 增層載板（節點名冊裡相近的是 `mat:ic_package_substrate`（IC 載板），範圍比這張卡寬；第一輪不碰圖）
> 代表公司：欣興（3037）、南電（8046）、景碩（3189）；海外文件取 Ibiden、AT&S、LG Innotek（公司名是文字加出處，不是實體主張）
> 樣本標記：原始清單｜欄位 v1｜做卡日 2026-11-22｜**不是盲判**（結局是公開常識，代表公司也是照結局挑的）
> 寫法見 [README](README.md)。引號裡是原始檔逐字；`〔…〕`是檔尾出處清單的鍵。

## 先讀這一段（描述，不判）

這一段照日期排下來的順序：

1. **2018-11**　Ibiden 決定第一期擴產（700 億日圓）。台廠代表公司的起漲月是 2018-10 與 2019-05。
2. **2020-04 → 2021-06**　擴產一期比一期大（Ibiden 600 億 → 1,800 億日圓；AT&S 17 億歐元新廠）。
3. **2021-03 起**　買家第一次在申報文件寫載板短缺，接著改用長約與預付搶產能：AMD 的不可取消採購承諾一年內從 32 億變 91 億美元；欣興的合約負債一年增加 285 億元。
4. **2021-10 ～ 2022-02**　三家股價的高點月。當月營收年增仍有 +30% 到 +45%，毛利率還在往上。
5. **2022-02 ～ 2022-04**　新進者宣布進場（LG Innotek）；Ibiden 把 2022 年個人電腦的預估改成衰退。
6. **2022-04 ～ 2022-06**　三家月收盤回落到高點的七成以下。
7. **2022-07 ～ 2022-11**　買家口徑才轉向（Intel 下修、AMD 寫個人電腦供應鏈庫存修正）。
8. **2022Q3 ～ Q4**　三家單季毛利率的高點——在股價高點之後兩到四季。
9. **2022-11 ～ 2023-01**　月營收年增轉負。2023 年全年營收是高點那一年的 0.74 到 0.81，毛利率從 2022 年的 36% 到 40% 掉到 19% 到 25%。

兩件事在這張卡上看得到：**股價的高點比毛利率的高點早兩到四季、比買家說出口早五到九個月**；**高點落在預付與擴產公告最密集的那一年年底**。這是一段的觀察，不是規則。

## A 怎麼起來

**A1 錨的需求**

- 伺服器與影像處理｜「in order to meet the increasing demand for servers and image processing units from our Customer」〔ibiden_notice_2021-04-27_en〕｜2021-04-27｜供應商自述
- 買家自己的說法｜「During 2021, the semiconductor industry experienced widespread shortages of substrates and other components and available foundry manufacturing capacity, and we anticipate that such shortages will continue in 2022.」〔intel_10k_fy2021〕｜2022-01-27｜客戶端

**A2 為什麼卡在這一層**

- 能做的家數少｜「certain non-proprietary materials or components such as memory, printed circuit boards (PCBs), interposers, substrates and capacitors used in the manufacture of our products are currently available from only a limited number of sources.」〔amd_10k_fy2020〕｜2021-01-29｜客戶端（風險因素段，例行揭露）
- 同一顆晶片吃掉的載板產能變大（面積變大、層數變多、線路變細）｜「Increase SAP Load due to Further Refinement, High Density Multilayer and Upsizing of IC Package Substrate」〔ibiden_pres_2021-11-01〕｜2021-11-01｜供應商自述
- 新進者自己的說法｜「Yet, the number of companies producing FC-BGA is limited, causing shortage in supply.」〔lg_innotek_fcbga〕｜2022-03-15（董事會決議 2022-02-22）｜供應商自述

**A3 第一個公開訊號**

- 供應商端最早：擴產決定｜「We aim to increase capacity of IC package substrate in order to meet the new demand with high-performance and high-speed semiconductors, servers and image processing.」〔ibiden_pres_2018-11-02〕｜2018-11-02｜供應商自述。同一頁寫產能增加約五成：「The plan enables us to increase the productive capacity of IC package substrate by about 50% (layer conversion) including the contribution from the prior investment by FY2021.」〔ibiden_pres_2018-11-02〕
- 客戶端最早寫到短缺：｜「PC revenue will be tempered by the industry-wide shortage of critical third-party components, such as substrates, which the company is working with its supply chain partners to mitigate.」〔intel_8k_2021-03-23_ex992〕｜2021-03-23｜客戶端。EDGAR 全文搜尋 Intel 的申報文件：2018-01-01 到 2021-03-22 含 substrates 的是 0 份，這一份是第一份。
- 兩者相隔 28 個月：供應商擴產在前，買家喊缺在後。

**A4 層的成員**

- 這張卡手上的文件點到的供應商：Ibiden、欣興、南電、景碩、AT&S；2022 年新進的 LG Innotek。｜出處：各自的文件（見下）
- 完整名單與市占：沒找到一手（找過：欣興 109、110 年度年報的競爭段，沒有具名同業）。

**A5 數字鐘、A6 價格鐘**（機械；算法見 README）

| | 欣興 3037 | 南電 8046 | 景碩 3189 |
|---|---|---|---|
| 起漲月 | 2018-10 | 2018-10 | 2019-05 |
| 高點月 | 2022-02 | 2021-11 | 2021-10 |
| 起漲到高點 | 40 個月 | 37 個月 | 29 個月 |
| 月收盤倍數（還原權息） | 17.8 倍 | 26.3 倍 | 6.5 倍 |
| 營收年增連續為正的起點 | 2020-12（連 25 個月） | 2019-04（連 45 個月） | 2020-02（連 33 個月） |
| 那一段年增最高的月 | 2022-05，+51.5% | 2021-01，+58.1% | 2020-02，+56.2% |
| 高點月當月的營收年增 | +44.5% | +30.4% | +33.6% |
| 單季毛利率低點 | 2018Q2，6.4% | 2018Q1，−4.2% | 2019Q1，5.8% |
| 單季毛利率高點 | 2022Q3，38.2% | 2022Q4，42.5% | 2022Q4，41.8% |
| 高點月那一季的毛利率 | 32.3% | 33.2% | 33.6% |

- 起漲月到高點月之間營收年增為負的月：欣興 2018-12、2019-01、2020-08、2020-11（所以連續為正的起點落在 2020-12，比起漲月晚 26 個月）；南電 2019-02、2019-03；景碩 2019-05 到 2019-10、2020-01。
- **三家在起漲後的頭六個月內都有營收年增為負的月**——起漲月的時候，營收年增還沒有連續為正。

**A7 當時公司自己怎麼講**（高點前一年內）

- 欣興｜「受惠5G產業及高速運算應用等的發展，推升了全球PCB及IC載板的需求成長。」〔unimicron_ar_fy2020〕｜2021-05-31｜供應商自述
- Ibiden｜「Strengthen Foundations for Business Growth in the Mid-Term with Prior Investment in PKG Market that is Expected to Grow」〔ibiden_pres_2021-11-01〕｜2021-11-01｜供應商自述

## B 高點前後出現什麼

**B1 同層擴產**（高點前 12 個月到後 6 個月＝2020-10 ～ 2022-08；較早的兩筆一併列出）

| 發布日 | 誰 | 多少 | 預定開出 | 原句 |
|---|---|---|---|---|
| 2018-11-02 | Ibiden 第一期 | 700 億日圓 | 2020 年度量產 | 「Investment Value ：70.0 billion yen」〔ibiden_pres_2018-11-02〕、「We plan to come online sequentially in FY2019 and start commercial production in FY2020.」〔ibiden_pres_2018-11-02〕 |
| 2020-04-27 | Ibiden 第二期 | 600 億日圓 | 2021 年度量產 | 「600億円(2020～2022 年度合計、第 1 期投資と合わせた総額は 1,300 億円)」〔ibiden_notice_2020-04-27_jp〕、「2020 年度末より順次稼働開始し、2021 年度より量産開始の計画」〔ibiden_notice_2020-04-27_jp〕 |
| 2021-04-27 | Ibiden 第三期 | 1,800 億日圓 | 2023 年內開始 | 「Amount: JPY180 billion (estimation basis)」〔ibiden_notice_2021-04-27_en〕 |
| 2021-06-10 | AT&S 馬來西亞新廠 | 17 億歐元 | 2024 年商轉 | 「involves a proposed total investment of RM8.5 billion (€1.7 billion) and will create 5,000 high-tech and high impact jobs」〔ats_malaysia_2021〕；馬來西亞貿工部同日新聞稿（第三方）：「The construction of the facility is scheduled to begin in the second half of 2021 with commercial operations targeted to come on stream in 2024.」〔miti_ats_2021-06-10〕 |
| 2022-05-23 | 欣興 | 與客戶合作擴產（金額沒寫在這一句） | — | 「與客戶在載板高階技術領域的共同合作擴產，發展長期關係」〔unimicron_ar_fy2021〕 |

- 窗內（2020-10 ～ 2022-08）有文件的擴產：Ibiden 第三期、AT&S、欣興，加上 B2 的新進者，共 4 家。Ibiden 三期的金額是 700 → 600 → 1,800 億日圓：**最大的一期在高點前 6 到 10 個月宣布**。
- 欣興的資本支出（機械；合併現金流量表的「取得不動產、廠房及設備」〔unimicron_ar_fy2022〕）：2021 年 231.7 億元、2022 年 320.7 億元。
- 南電、景碩、Shinko、三星電機的擴產公告：沒找（這一輪只抓了上面幾份）。

**B2 第二來源或新進者**

- LG Innotek 第一次投資這個產品｜「announced at a board meeting on the February 22nd that it had decided to invest KRW 413 billion in」〔lg_innotek_fcbga〕、「This is LG Innotek's first investment in the FC-BGA business」〔lg_innotek_fcbga〕｜2022-03-15（決議 2022-02-22）｜供應商自述
- 客戶端或第三方寫出向新供應商採購的文件：沒找到（找過：Intel、AMD 2021–2022 的 10-K、10-Q；它們不具名供應商）。

**B3 買家口徑轉向**

- Intel 下修｜「The sudden and rapid decline in economic activity was the largest driver, but the shortfall also reflects our own execution issues,」〔intel_q222_release〕｜2022-07-28｜客戶端
- AMD 寫庫存修正｜「a 40% decrease in Client segment revenue primarily due to lower processor shipments driven by a weak PC market and significant inventory correction actions across the PC supply chain.」〔amd_10q_2022q3〕｜2022-11-02｜客戶端
- 供應商轉述的買家預估先動（比買家自己說早三個月）｜「Forecast Stable Trend for Mid-to-Long Term after Temporary Decline Due to Reflecting Peaking-Out in Demand for Remote Work, Online Education and OS Updates」〔ibiden_pres_2022-04-28〕｜2022-04-28｜供應商自述
- Ibiden 簡報同一張圖（載板需求換算成 SAP 面積的指數；圖上註「based on customer information」〔ibiden_pres_2022-04-28〕、「indexed by FY 19=100」〔ibiden_pres_2022-04-28〕，橫軸印 CY19 到 CY25）在三個日期印的數列——2022-04-28「100 118 151 164 184 209 227」〔ibiden_pres_2022-04-28〕；2022-10-28「100 118 151 152 160 190 210」〔ibiden_pres_2022-10-28〕；2023-05-02「100 118 151 147 140 170 210」〔ibiden_pres_2023-05-02〕。數列是從簡報文字層抽的，**沒有對著圖核過哪個數對哪一年**；照橫軸順序讀，2022 年那一格從 164 改到 152 再到 147，2023 年從 184 改到 160 再到 140，2025 年從 227 改到 210。

**B4 買家的錢**

這一段買家不是舉債撐支出，而是**拿現金預付給供應商換產能**：

- Intel｜「as we have faced industry shortages of substrates and other components, we have increasingly entered into long-term agreements with suppliers and foundry service providers, some of which involve prepayments」〔intel_10k_fy2021〕｜2022-01-27｜客戶端
- AMD｜「We have long-term purchase commitments with some of our substrate suppliers.」〔amd_10q_2021q2〕｜2021-07-28｜客戶端
- AMD 不可取消的採購承諾總額（晶圓與載板合計，機械）：2020 年底 31.91 億美元〔amd_10k_fy2020〕→ 2021 年底 90.66 億〔amd_10k_fy2021〕→ 2022 年底 86.10 億〔amd_10k_fy2022〕。其中一年以後才到期的：1.65 億 → 33.01 億 → 21.21 億美元。
- 供應商這一頭收到的（欣興合併報表，機械）：合約負債 2021 年一年增加 285.0 億元、2022 年再增加 159.1 億元；非流動的合約負債 2021 年底 293.5 億元、2022 年底 423.2 億元〔unimicron_ar_fy2022〕。
- 買家舉債或供應商反過來融資給買家：這一段沒有看到。

**B5 價格與合約條件**

- 買家開始調整承諾的付款與交貨時點｜「On an ongoing basis, the Company works with suppliers on the timing of payments and deliveries of purchase commitments, taking into account business conditions」〔amd_10k_fy2022〕｜2023-02-27｜客戶端。前一年的 10-K 同一段沒有這一句。
- 買家自己早就寫過反面的風險｜「Conversely, a decrease in customer demand could result in excess substrate inventory and an increase in our production costs.」〔amd_10q_2021q2〕｜2021-07-28｜客戶端
- 供應商新廠時程往後｜2021-04 寫「Start of production: To be first started within 2023, then shifted finally to high-volume manufacturing」〔ibiden_notice_2021-04-27_en〕；2022-04 寫「New Building in Gama Plant Starts Mass Production in 2024」〔ibiden_pres_2022-04-28〕；2023-10 寫「The launch of the Ono Plant takes a lead, adjusting changes in demand for IC package substrates.」〔ibiden_pres_2023-10-27〕
- 載板報價、漲價停止的日期：沒找到一手（公司文件不寫單價）。

## C 怎麼結束

**C1 層回落**（機械）

| | 欣興 3037 | 南電 8046 | 景碩 3189 |
|---|---|---|---|
| 回落到高點七成以下的月 | 2022-06（高點後 4 個月） | 2022-04（後 5 個月） | 2022-06（後 8 個月） |
| 之後 18 個月回到前高 | 沒有 | 沒有 | 沒有 |
| 那 18 個月裡的最低點 | 2022-09，高點的 0.47 | 2022-09，高點的 0.31 | 2022-09，高點的 0.39 |
| 高點後第一個營收年增為負的月 | 2023-01（後 11 個月） | 2023-01（後 14 個月） | 2022-11（後 13 個月） |

**C2 公司自己怎麼解釋**

- 欣興｜「受惠於各類科技應用需求強勁成長，新技術新產品推陳出新，然而在COVID-19疫情、俄烏戰爭、通膨、存貨調整及地緣政治等多重影響下，市場狀況由盛轉衰」〔unimicron_ar_fy2022〕｜2023-05-11｜供應商自述
- Ibiden｜「Estimated to Continue Inventory Adjustment until Early CY2023, Meeting Reduced Demand since Late CY2022」〔ibiden_pres_2023-05-02〕｜2023-05-02｜供應商自述

**C3 高點後兩年**（機械；全年營收以高點月所在年度為 1）

| | 欣興（高點年 2022） | 南電（高點年 2021） | 景碩（高點年 2021） |
|---|---|---|---|
| 高點年 | 1.00｜毛利率 35.9% | 1.00｜28.5% | 1.00｜29.5% |
| 後一年 | 0.74｜19.5% | 1.24｜40.0% | 1.17｜38.1% |
| 後兩年 | 0.82｜14.1% | 0.81｜19.4% | 0.75｜25.2% |

- 南電與景碩的股價高點在 2021 年底，**之後一年營收還多 17% 到 24%、毛利率還多 9 到 12 個百分點**，再下一年才掉。

## D 讀這張卡要知道的

**D1 事前看得到的、事後才知道的**（相對高點月 2021-10 ～ 2022-02）

| 高點之前就公開的 | 高點之後才公開的 |
|---|---|
| Ibiden 三期擴產（前 35 到 39、18 到 22、6 到 10 個月） | LG Innotek 進場（高點當月到後 5 個月） |
| Intel 寫短缺（前 7 到 11 個月） | Ibiden 把個人電腦預估改成衰退（後 2 到 6 個月） |
| AT&S 新廠（前 4 到 8 個月） | Intel 下修（後 5 到 9 個月） |
| AMD 寫與載板供應商有長約、也寫了需求掉下來會有多餘庫存（前 3 到 7 個月） | AMD 寫庫存修正（後 9 到 13 個月） |
| Intel 10-K 寫預付、AMD 採購承諾跳到 91 億美元（高點前後 0 到 3 個月） | 毛利率高點（後 2 到 4 季）、營收年增轉負（後 11 到 14 個月） |

**D2 沒找到、量不到的**

- A4 完整成員名單與市占（找過欣興年報競爭段）。
- B1 南電、景碩、Shinko、三星電機的擴產公告（沒抓）。
- B2 客戶端具名新供應商的文件（買家申報文件不具名）。
- B5 載板單價與漲價停止的日期。
- 欣興 2020 年底的合約負債餘額（110 年度年報的財報頁抽不出字；108 年度年報幾乎整份是圖檔）。
- 法說逐字稿沒有用（不在申報文件裡，轉錄來源不逐字）。

**D3 這張卡的偏差**

- 三家代表公司都是倖存者，而且是照漲最多的印象挑的；倍數不能當這一層的典型值。
- 三家都不是純 ABF：欣興還有 HDI 與一般電路板，南電、景碩有 BT 載板。營收與毛利率是整家公司的。
- 供應商的話全是自述；客戶端只有 Intel 與 AMD 兩家，Intel 的句子多半在風險因素與前瞻聲明段。
- 買家口徑只讀申報文件，法說會上更早的說法不在卡上——買家比股價晚轉向，可能有一部分是這個造成的。
- 這一段同時疊了疫情帶來的個人電腦需求，分不開哪些是伺服器、哪些是個人電腦。

## 出處

引文程式核過（見檔尾核對行）。原始檔住本機私有區（不進 repo）。

| 鍵 | 文件 | 文件日期 | 網址 | sha256 前 16 碼 |
|---|---|---|---|---|
| intel_8k_2021-03-23_ex992 | Intel 8-K 附件 99.2 | 2021-03-23 | https://www.sec.gov/Archives/edgar/data/50863/000119312521091374/d153275dex992.htm | a88fdfe5d60f6c46 |
| intel_10k_fy2021 | Intel 10-K（2021 年度） | 2022-01-27 | https://www.sec.gov/Archives/edgar/data/50863/000005086322000007/intc-20211225.htm | 4d306b7fd2702c23 |
| intel_q222_release | Intel 2022Q2 財報新聞稿（8-K 附件） | 2022-07-28 | https://www.sec.gov/Archives/edgar/data/50863/000005086322000029/q222_earningsrelease.htm | e67a0e0e59d3d566 |
| amd_10k_fy2020 | AMD 10-K（2020 年度） | 2021-01-29 | https://www.sec.gov/Archives/edgar/data/2488/000162828021001185/amd-20201226.htm | c26ecae782e73555 |
| amd_10q_2021q2 | AMD 10-Q（2021Q2） | 2021-07-28 | https://www.sec.gov/Archives/edgar/data/2488/000000248821000116/amd-20210626.htm | c9c3cf2c46c5eee4 |
| amd_10k_fy2021 | AMD 10-K（2021 年度） | 2022-02-03 | https://www.sec.gov/Archives/edgar/data/2488/000000248822000016/amd-20211225.htm | bce4b6489488807f |
| amd_10q_2022q3 | AMD 10-Q（2022Q3） | 2022-11-02 | https://www.sec.gov/Archives/edgar/data/2488/000000248822000170/amd-20220924.htm | 09dc2ff9d7deafed |
| amd_10k_fy2022 | AMD 10-K（2022 年度） | 2023-02-27 | https://www.sec.gov/Archives/edgar/data/2488/000000248823000047/amd-20221231.htm | 5d71ebe44dc28370 |
| ibiden_pres_2018-11-02 | Ibiden 法說簡報（2018 年度上半年） | 2018-11-02 | https://www.ibiden.com/ir/items/presentation2018_1_rev02.pdf | 3d9d3dc7daad9006 |
| ibiden_notice_2020-04-27_jp | Ibiden 第二期投資公告（日文） | 2020-04-27 | https://www.ibiden.co.jp/ir/items/06753486edba41a82b42940f2ea3507a.pdf | c7bf0e5ebea7110c |
| ibiden_notice_2021-04-27_en | Ibiden 設備投資計畫公告 | 2021-04-27 | https://www.ibiden.com/ir/items/210427release_EN.pdf | 1285331a12379b9f |
| ibiden_pres_2021-11-01 | Ibiden 法說簡報（2021 年度上半年） | 2021-11-01 | https://www.ibiden.com/ir/items/211101IRpresentationEN.pdf | 55c1b6e25631a42d |
| ibiden_pres_2022-04-28 | Ibiden 法說簡報（2021 年度） | 2022-04-28 | https://www.ibiden.com/ir/items/FY21IRpresentation_EN.pdf | 4c4d50d36e37abad |
| ibiden_pres_2022-10-28 | Ibiden 法說簡報（2022 年度上半年） | 2022-10-28 | https://www.ibiden.com/ir/items/221028IRpresentationEN.pdf | 3534d7cb0e41562c |
| ibiden_pres_2023-05-02 | Ibiden 法說簡報（2022 年度） | 2023-05-02 | https://www.ibiden.com/ir/items/FY22IRpresentation_EN.pdf | 2d92ad75f99b6e9a |
| ibiden_pres_2023-10-27 | Ibiden 法說簡報（2023 年度上半年） | 2023-10-27 | https://www.ibiden.com/ir/items/en_chuukanhoukoku.pdf | 3da8c5af581962aa |
| ats_malaysia_2021 | AT&S 新聞稿 | 2021-06-10 | https://ats.net/en/press/ats-chooses-malaysia-for-its-first-production-site-in-southeast-asia/ | f2d010858d29a9f8 |
| miti_ats_2021-06-10 | 馬來西亞貿工部新聞稿（第三方） | 2021-06-10 | https://www.miti.gov.my/miti/resources/Media%20Release/MR_-_AUSTRIAN_ATS_CHOOSES_MALAYSIA_10_JUNE_2021.pdf | c78ec896b14f649c |
| lg_innotek_fcbga | LG 官方新聞室：LG Innotek 首次投資 FC-BGA | 2022-03-15 | https://www.lgcorp.com/media/release/24560 | 12ec26ad2b2ee6f8 |
| unimicron_ar_fy2020 | 欣興 109 年度股東會年報 | 2021-05-31（上傳日） | 公開資訊觀測站電子書 2020_3037_20210617F04.pdf | 5492224d742abd80 |
| unimicron_ar_fy2021 | 欣興 110 年度股東會年報 | 2022-05-23（上傳日） | 公開資訊觀測站電子書 2021_3037_20220615F04.pdf | 60c92add306f6def |
| unimicron_ar_fy2022 | 欣興 111 年度股東會年報 | 2023-05-11（上傳日） | 公開資訊觀測站電子書 2022_3037_20230530F04.pdf | 0524174332e214a3 |

機械格的資料：月線＝yfinance 還原權息月收盤（抓取日 2026-11-22）；月營收與年增＝公開資訊觀測站月營收彙總（2014-05 ～ 2023-12）；單季毛利率、全年營收與全年毛利率＝公開資訊觀測站綜合損益表彙總（四季合計，到 2024Q4）。

核對行：引文 38 段，38 段都在原始檔裡逐字找得到（兩邊去空白後比對；`check_quotes`，2026-11-22）。不是引文的數字與日期由做卡的人對原始檔核過，沒有第二個人核。
