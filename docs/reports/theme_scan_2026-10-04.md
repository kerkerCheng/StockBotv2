# 題材掃描 — 2026-10-04

- 窗：2026-09-20（上一份 `weekly_scan_2026-09-20.md`）～2026-10-04；`config/themes.txt` 5 個主題（cpo、sivers、robotics、power、cooling），每個主題 2–3 次 WebSearch。
- 本輪邊界（`skills/theme-scan`）：只發現、不處置——沒有追源、抽取、入圖，沒有對任何 pq2 編號給 go／drop。觸發：Phase 7 plan Step 7.1 ①「掃題材至少一次」。
- Stage 0：`python -m engine_b.cli onboard-candidates` 111 個（lead 點名、名冊沒有）。

## 30 秒 brief

- **電力鏈有一個可能的邊緣新股：Forgent Power Solutions**（S-1 2026-05-26、修正 06-29）。名冊、lead 都沒有它；只提名，登記成研究題目。
- **台達 2026-09-29 發表給 Vera Rubin 用的 800 VDC in-row power**——P3 擱置的「DC/DC power shelf」那則（park 理由是供貨關係沒證實）要看這次有沒有具名客戶；回看照登記在 Wave 2（7.4）。
- **液冷供給側正在被大型股吃掉**：Ecolab 完成收購 CoolIT（2026-07-02）、Eaton 完成收購 Boyd Thermal（2026-03-12）——純液冷的獨立廠變少，C1 要找的是「還剩誰」。
- 光通訊、Sivers、機器人：窗內沒有新的結構事件（Sivers 的 Glasgow 擴產與 10/22 臨時股東會 daily 都已抓到；CCXI 的 S-4/A 已打成入圖包 [683]）。
- 本輪無新需求錨（電力、散熱已由 [685][686] 開題）。

## Topic Digest

### 1. Forgent Power Solutions S-1（power）→ research
- 來源：[SEC S-1（2026-06-29）](https://www.sec.gov/Archives/edgar/data/0002080126/000119312526288605/na-20260629.htm)、[S-1 初版（2026-05-26）](https://www.sec.gov/Archives/edgar/data/0002080126/000119312526239485/na-20260526.htm)（搜尋 GOES 時出現，本輪沒讀內文）
- 影響：電力鏈目前圖上 0 節點、名冊 0 家；新股多半覆蓋薄，可能是坐在變壓器／開關設備層的邊緣公司。
- 為何值得研究：先答它坐哪一層、資料中心客戶占比、有沒有客戶端資本承諾；答案會改變電力鏈的候選集合。
- 已登記：`lead_259eeb933c8222fc944d53526751b967`（`theme_scan:power`）

### 2. 台達 800 VDC in-row power for Vera Rubin（power／800VDC）→ research
- 來源：[PR Newswire 轉載，2026-09-29](https://www.manilatimes.net/2026/09/29/tmt-newswire/pr-newswire/delta-electronics-unveils-ai-modular-data-center-with-800-vdc-in-row-power-for-nvidia-vera-rubin-and-microgrid-solutions-at-data-center-world-asia-2026/2435106/amp)；脈絡：[TI 800 VDC 架構（2026-03-16）](https://www.ti.com/about-ti/newsroom/news-releases/2026/2026-03-16-ti-unveils-complete-800-vdc-power-architecture-for-future-generation-ai-data-centers-with-nvidia.html)、[Power Electronics News：GTC 2026 800 VDC 夥伴](https://www.powerelectronicsnews.com/nvidia-gtc-2026-800-vdc-power-partnerships-from-grid-to-processor/)
- 影響：P3 擱置五則之一 `lead_fa672a299978b3f3ec2b0cf8ae1d4130`（DC/DC power shelf）的 park 理由是「supplier relationship not proven」；產品發表本身仍不是供貨合約。
- 已登記：`lead_b050a3eea55f48ee93ba1f7571c58ccf`（`theme_scan:power`）

### 3. 液冷供給側整併（cooling）→ research
- 來源：[Ecolab IR：完成收購 CoolIT](https://investor.ecolab.com/news/news-details/2026/Ecolab-Closes-CoolIT-Acquisition-and-Expands-AI-Cooling-Platform-as-Global-High-Tech-Business-Targets-4-Billion-by-2030/default.aspx)、[Ecolab 8-K](https://www.sec.gov/Archives/edgar/data/31462/000110465926032446/tm269446d1_ex99-1.htm)、[Eaton 8-K](https://www.sec.gov/Archives/edgar/data/0001551182/000155118226000010/etn03312026exhibit99.htm)；tier 3：[DATAAD CDU 廠商彙整](https://dataad.com/post/ai-data-center-cdu-manufacturers)、[The Cooling Report 供應鏈指南](https://thecoolingreport.com/intel/data-center-cooling-supply-chain-guide-2026.html)（「Google 給英維克約 25% CDU 份額」——待追一手）
- 影響：C1 decompose 的冷板、CDU 兩層（`lead_5b8cc7e2`、`lead_f96bfb99`）的供給側有兩家主要獨立廠已併入大型股。
- 已登記：`lead_f7c61cbb512de3c686be46ee6da946fb`（`theme_scan:cooling`）

### 4. GOES 擴產（power）→ 附在既有題目
- 來源（tier 3 彙整，未追一手）：[Straits Research](https://straitsresearch.com/report/grain-oriented-electrical-steel-market)、[Procurement Resource](https://www.procurementresource.com/resource-center/grain-oriented-electrical-steel-price-trends)、[Industrial Sage：交期 128 週](https://www.industrialsage.com/power-transformer-lead-times-us-grid-shortage/)
- 內容：Cleveland-Cliffs 在 Weirton 蓋變壓器廠、國內 GOES 噸數增約 30–40%；JFE＋JSW 在印度約 35 萬噸、2027 起；現代製鐵 2026-04 與北美變壓器廠簽 GOES 供貨。
- 處置：不另開 lead，寫進 `lead_21b7830dc4f69e8466089850f88dce8b`（GOES decompose 題目）的 `trace_review_hint`，追源時先找這三件的一手。

### 5. FYI（不登記）
- Sivers：[Glasgow 擴產 3,000 萬美元、CW DFB 年產能上看 1 億顆、2027Q4 上線](https://www.sivers-semiconductors.com/press/sivers-semiconductors-invests-usd-30-million-to-expand-european-photonics-manufacturing-for-ai-datacenters/)；[光電工程 VP 換人](https://www.sivers-semiconductors.com/press/sivers-semiconductors-makes-changes-to-senior-leadership-team-for-next-phase-of-commercial-growth/)；10/22 臨時股東會（daily 已抓到：`lead_b434220bb…`、`lead_92e72d0ae…`）。給 10-29 thesis 複查讀。
- CPO：Deutsche Bank 稱 Lumentum 200G 雷射售罄、ASP 約前一代兩倍（[financefeeds 轉述](https://financefeeds.com/lumentum-coherent-ciena-corning-ai-optics-2026)，券商轉述，tier 3）；AMAT 與 Besi 擴大合作（2026-10-01，封裝層）。
- 機器人：窗內沒有新的供應協議；Schaeffler–Humanoid 是 2026-05 的舊事（已在圖上）。

## 建議 onboard 候選（只提名；onboarding 改名冊，走 `skills/company-onboard`、由使用者點名）

| ticker | 被點名次數 | 跟哪條鏈有關 | 樣本 |
|---|---|---|---|
| Forgent Power Solutions（尚無 ticker） | 0（本輪搜尋發現） | 電力 | S-1 2026-05／06 |
| BE（Bloom Energy） | 6 | 電力（資料中心現場發電） | onboard-candidates |
| GNRC（Generac） | 2 | 電力 | onboard-candidates |
| NVTS（Navitas） | 2 | 電力／800VDC（GaN；P3 `lead_a4c2e1439…`） | onboard-candidates |
| FN（Fabrinet） | 2 | 光通訊（CPO OSA） | onboard-candidates |
| SMTC（Semtech） | 5 | 光通訊 | onboard-candidates |

其餘 105 個（AMZN 19 次、SPCX 7 次等）多半是需求端、題材外或單次點名，本輪不提名。

## 新錨提案

本輪無新錨：電力、散熱兩條鏈已由使用者 Q2 選題、[685][686] 開題；其他 topic 的需求錨都在既有題材內。

## 本次註冊的 lead

- `lead_259eeb933c8222fc944d53526751b967`（`theme_scan:power`）Forgent S-1
- `lead_b050a3eea55f48ee93ba1f7571c58ccf`（`theme_scan:power`）台達 800 VDC in-row power
- `lead_f7c61cbb512de3c686be46ee6da946fb`（`theme_scan:cooling`）液冷供給側整併

> 本報告是當次的 point-in-time 發現，不是 lead／todo／lifecycle 的狀態源（AGENTS）。
