# 題材掃描 — 2026-11-06

- 窗：2026-10-27（上一份 `theme_scan_2026-10-27.md`）～2026-11-06。範圍是 `config/themes.txt` 的 6 組（cpo、sivers、robotics、power、cooling、aibio），另加一組「題材外的集中需求」（outside）。共 WebSearch 19 次、WebFetch 6 次（看 Counterpoint、Azenta 8-K、pharmaphorum、KED、The Elec、日立能源新聞稿）。
- 邊界（`skills/theme-scan`）：只發現、不處置。沒有追源、抽取、入圖，也沒有對任何 pq2 編號給 go／drop。觸發：使用者 2026-11-06「掃題材」，心跳提醒「已 10 天沒掃題材」。
- **跟上一輪不同，daily 的外部雷達窗內每天都有跑**（`daily_run_*.json` 的 `radar_items`，10-28～11-06 每天 1–12 則）。窗內雷達抓到的 lead：cpo 5 則、cooling 11 則、power 12 則、robotics 3 則、sivers 1 則、new 46 則，**aibio 0 則**。所以這輪不補洞，重點放在三件事：雷達沒蓋到的 aibio、題材外的集中需求、跨來源的叢集。
- Stage 0：`python -m engine_b.cli onboard-candidates` 共 111 個（lead 逐字點名、名冊沒有）。10-27 之後第一次被點名的有 7 個：KLAC、TOELY、CLS、HOOD、LWLG、OKLO、NOW。
  - 除 LWLG 外都是大型股，或是同一則總體貼文順帶點名。
  - LWLG（Lightwave Logic，電光聚合物調變器）是唯一的小型股，但出處是一則講避險基金去槓桿的貼文，沒有結構事實，不提名。
- 執行：主 session 自己跑，沒有開子代理。

## 30 秒 brief

- **outside：MLCC 是圖上沒有的一層。** The Elec 11-02 報導兩件事：
  - 村田 FY2026–2030 五年要投約 1 兆日圓在 MLCC，其中岡山約 1,500 億日圓，**分別建 MLCC 廠與陶瓷片／原料廠**。
  - 村田因 AI 伺服器用 MLCC 的需求，**已婉拒部分客戶訂單**。

  MLCC 本身是兩家大型股的寡占，不是邊緣小公司；要研究的是上游原料（陶瓷粉體、鎳粉）是不是更薄的一層。→ research
- **power：日立能源 10-22 在巴西新建套管與分接開關工廠。** 這是圖上兩層的供給側擴產，華明裝備（002270.SZ）的敘事騎在分接開關那層。上一份報告寫「等一手由 daily 帶進來」，結果沒有進來，這次補一則。→ research
- **cpo：Marvell 11-02 宣布以全股票、約 1,150 億美元收購 Lumentum。** daily 已抓到 37 則相關 lead，drain 已經處理過。→ FYI
- **AI capex 需求錨的反向叢集。** 10-28～11-05 至少 8 則同方向（neocloud 融資受阻、建照暫停、capex 低於計畫），daily 全部抓到。drain 判定是「主題翻轉的反向脈絡」，不是任何一層的結構事實。錨層級的反證已登記在 [900]（等 2027-02-06）。→ FYI
- aibio、cooling、robotics、sivers：窗內沒有 daily 範圍外的新結構事件。aibio 找到的仍然只是授權、合作與供應商自述，不過三問。
- 本輪沒有新需求錨，也沒有 onboard 提名。

## Topic Digest

### 1. MLCC：村田五年 1 兆日圓、岡山另建陶瓷片／原料廠、因 AI 伺服器需求婉拒訂單（outside）→ research

- **摘要**：
  - **村田**（The Elec 2026-11-02 報導村田的說法）：
    - FY2026–FY2030 五年約 1 兆日圓投資 MLCC。
    - 岡山村田要在瀨戶內投資約 1,500 億日圓，「to build separate production facilities for MLCCs and for ceramic sheets and raw materials」。
    - MLCC 廠 2027-04 動工、2028 年底完工。
    - 村田「had been forced to turn down some customer orders because of growing demand for MLCCs used in AI servers」。
  - **三星電機**：另有一筆 1.07 兆韓元（7.4 億美元）的一年期 AI 伺服器 MLCC 合約，客戶未具名（KED Global 2026-09-01）。
  - **二手總覽**：AI 伺服器 MLCC 村田約 45%、三星電機約 40%；高容 MLCC 交期 20–40 週。
- **來源**：
  - https://www.thelec.net/news/articleView.html?idxno=15139 （11-02，轉述；一手要對村田的決算說明資料或新聞稿原句）
  - https://www.kedglobal.com/electronics/newsView/ked202609010006 （09-01，轉述；一手是三星電機的 DART 公告）
  - 二手總覽：https://passive-components.eu/mlccs-in-the-age-of-ai-q2-2026-market-tightness/ ／ https://www.astutegroup.com/news/general/mlcc-shortages-deepen-as-ai-demand-extends-lead-times/
- **影響**：
  - 圖上沒有 MLCC 或電容的節點（`tech:`／`mat:`／`comp:` 名稱與 id 都沒有 capacitor、MLCC）。
  - MLCC 這一層本身是兩家大型股的寡占，不會是 power-law 標的。
  - 如果有薄層，會在上游：村田這次把「陶瓷片與原料」單獨建廠，表示原料是它自己也要擴的一段。外購原料的業者（三星電機、太陽誘電等）向誰買鈦酸鋇粉、鎳粉，才是要回答的問題。
- **為何值得研究**：
  - 9 月起有 10 則 X 貼文提到 MLCC、村田或太陽誘電，9 則停放、1 則 no_go，因為每一則都只是總覽貼文裡的一句。
  - 沒有任何一則一手進來過——同一件事一直被順帶點名，但沒有一則單獨夠格。
  - 第一步只是核對村田一手的三句原文：婉拒訂單、1 兆日圓、岡山原料廠。再看上游有沒有薄層；沒有就停在脈絡。

### 2. 日立能源巴西套管與分接開關新廠（power）→ research

- **摘要**（日立能源新聞稿 2026-10-22）：
  - 投資 3.85 億雷亞爾，「a new facility dedicated to manufacturing bushings and tap changers」，與 Pindamonhangaba 興建中的變壓器園區同址。
  - 「will add oil-impregnated paper (OIP) bushing capacity, as well as increase capacity for dry-type resin-impregnated paper (RIP) and paperless bushings」。
  - Guarulhos 擴絕緣材料。
  - 稱會帶來「shorter lead times, greater supply chain resilience, and increased availability」。
  - **新聞稿沒寫投產日，也沒寫產能數字。**
  - 二手（inspenet、transformer-magazine）另寫「約 7,700 萬美元」「產能增加一倍以上」「出口北美與中東」，這幾句我在一手原文裡沒看到。二手說法不等於一手已證實（L11）。
- **來源**：https://www.hitachienergy.com/news-and-events/press-releases/2026/10/hitachi-energy-s-new-brl-385-million-investment-to-strengthen-brazil-as-a-latin-america-hub-for-transformer-components
- **影響**：
  - 圖上 `tech:transformer_bushing`、`tech:transformer_tap_changer`、`mat:transformer_insulation` 三層都有讀圖。
  - 002270.SZ 華明裝備（分接開關）的敘事騎在分接開關那層。
  - 一家既有大廠的供給側擴產，可能碰到這幾份讀圖的反證或「已定價嗎」的脈絡，要由 drain 對照。
- **為何值得研究**：
  - 上一份報告的 Topic 2 寫「等一手由 daily（Siemens Energy、Hitachi Energy 的申報與新聞稿）帶進來」。
  - 10-20 以來沒有任何 lead 的標題或網址含 Hitachi Energy（查證見文末），所以這條等待沒有自己實現。這是第 1 次觀察到，不提開發項。

### 3. Marvell 收購 Lumentum（cpo）→ FYI

- **摘要**：
  - 2026-11-02 宣布，全股票：每股 Lumentum 換 4.5 股 Marvell，隱含企業價值約 1,150 億美元，較 10-28 收盤溢價 23.9%。
  - 預計 2028 上半年完成，需雙方股東與各國反壟斷核准（Counterpoint 點名中國 SAMR）。
  - 同日 Lumentum 揭露 NPO／CPO 逾 50 億美元的採購承諾。
- **來源**：https://techcrunch.com/2026/11/02/in-one-of-the-largest-deals-in-tech-history-marvell-buys-lumentum-for-115b/ ／ https://www.sec.gov/Archives/edgar/data/0001633978/000119312526442760/d163169d425.htm （Form 425）／ https://counterpointresearch.com/en/insights/marvell-buys-lumentum-to-climb-the-ai-laser-wall （11-03）
- **影響**：
  - 交割後，CW 雷射層的獨立商用供應商少一家。
  - Counterpoint 寫：與 Marvell 競爭的買方會想要「a second, independent laser source」。這是分析師推測，沒有買方一手。
- **處理狀態**：10-27 起有 37 則 lead 提到 Marvell，其中 29 則來自 carrioresearch。drain 已判：
  - 併購由一手 8-K 承載。
  - 交易要到 2028 上半年才完成，現行供貨關係與各格事實不變。
  - 「模組廠會找第二家雷射」是作者推測，判定不研究。

  所以不建 lead。之後要看的是 S-4 的風險因子有沒有寫客戶的反應。

### 4. AI capex 需求錨的反向叢集（outside）→ FYI

- **摘要**：窗內至少 8 則同方向，全部由 daily 抓到：
  - CoreWeave 重挫後資料中心融資凍結（IFR，10-28）。
  - 銀行延後與 Anthropic 相關的資料中心債（10-29）。
  - 德州暫停 17 張資料中心建照（10-29）。
  - Prometheus 放棄懷俄明 Natrona 案（10-30）。
  - 聖地牙哥市議會通過資料中心停建令（11-01）。
  - Fermi 與 TensorWave 的租約錯過交割期限（11-03）。
  - The Information 轉述 Microsoft 9 月季 capex 比計畫少約 50 億美元，部分因 IREN 延誤（11-05）。
  - 德州選舉引發停建令疑慮（11-05）。
- **同窗的另一面**（也由 daily 抓到）：
  - Alphabet 維持 2026 capex、說 2027 會顯著增加（10-28）。
  - Amazon 把 2026 AI capex 上修到 2,200 億美元，仍受產能限制（10-30）。
  - 三星說明年 HBM 供給已賣完（10-30）。
- **影響**：
  - drain 對這幾則的判定一致：主題翻轉的反向脈絡，不是任何層或讀圖的結構事實。
  - 本圖標的高度集中於同一題材，這類事件心跳只印回撤、不給燈號、不給動作（AGENTS 消費契約）。
  - 錨層級的反證／加碼條件已登記在 [900]：雲端四大 2026 Q4 法說後判 2027 capex 指引，等到 2027-02-06。

### 5. AI 生醫：只有供應商自述與合作（aibio）→ FYI

- **Azenta（2026-10-30 8-K 新聞稿）**：GENEWIZ 基因合成的策略投資，含收購 SynPlexity 的 pooled gene assembly。
  - 新聞稿寫「including AI-generated designs」「AI-enabled drug discovery」，但沒有具名客戶，也沒有產能數字。
  - 這是供應商自述，第 1 問（付錢的是 AI 程式）答不出來。
  - https://www.sec.gov/Archives/edgar/data/0000933974/000162828026068443/pressrelease-synplexitya.htm
- **Twist Bioscience**：FY2026 Q4 財報 11-12 才出。
- **上市申請**：Ultima、Carterra、Adaptyv 都沒找到 S-1（搜到的 Adaptin Bio 是另一家公司）。
- **pharmaphorum 10 月總覽**：GSK–Chai、AZ–insitro、Iambic 上市上一輪已列。Danaher 與 NVIDIA 的自主實驗室合作是合作，不是採購。
  - https://pharmaphorum.com/news/ai-drug-discovery-development-news-watch-october-2026
- 全部不過三問，不建 lead。

### 沒有建 topic 的組（看了，沒找到；不是沒看）

- **cooling**：
  - 搜到的是產品發表，不是供給吃緊或客戶事實：Cooler Master 2.5MW CDU（OCP 2026，目標 Q4 量產）、Ecolab 與 CoolIT 的平台（SC26）。
  - 雷達窗內 11 則在 drain：Vertiv、JCI、nVent、Trane、Carrier、LG、雙鴻、富世達擴產、Modine、散熱四雄 10 月營收。
- **robotics**：
  - 中文二手稱 Optimus V3 進入量產、Tesla 要求供應商年底週產 2,000–2,500 台、新劍傳動（行星滾柱螺桿，私人公司，2026-01 輔導備案），全是二手。
  - 上一輪註冊的 Tesla Q3 法說 lead 已併入 EDGAR 8-K 那則（`lead_987597a1`）一起研究。
  - 雷達窗內 3 則，例如 GXO 與 Agility 擴大部署。
- **sivers**：
  - Q3 報告在 11-26。
  - 光達量產單（10-20）已由 daily 抓到。
  - 股價回檔 19% 和兩家空單揭露是行情，不是結構。
- **cpo（Marvell 以外）**：都由雷達抓到：住友電工把 InP 基板產能目標上調到 FY2029 達 2024 年的 4.5 倍（11-03）、源傑三季報、AXT、Coherent、Lumentum 財報、NVIDIA 向六家供應商鎖載板與中介層產能（轉述）。
- **outside（MLCC 以外）**：
  - T-glass（日東紡）、PCB／ABF 載板吃緊的說法很多。
  - 圖上已有七層：T-glass 玻纖布、低 Dk 玻纖布、石英玻纖布、HVLP 銅箔、載體銅箔、高速 CCL、IC 載板。
  - 窗內沒找到新一手。

## 建議 onboard 候選

- 無。7 個新點名的名字見上方 Stage 0。

## 新錨提案

- 無。MLCC 是 AI 伺服器底下的一層，不是新的需求錨；AI 伺服器已在圖上。

## 本次註冊的 lead

- `lead_ab7d32804c7c5bccd783ea000a4f4cc2` ← `theme_scan:outside`（村田 MLCC：五年 1 兆日圓、岡山陶瓷片／原料廠、因 AI 伺服器需求婉拒訂單；圖上沒有 MLCC 層）
- `lead_20f6b2612d9f7d1bf5735cf405d41ed2` ← `theme_scan:power`（日立能源 10-22：巴西套管與分接開關新廠、擴絕緣材料）

## 查證（本機暫存腳本，唯讀）

- 窗內雷達每天有沒有跑：`python library/private/tmp/radar_status_window_1106.py`
- 窗內 lead 按來源：`python library/private/tmp/radar_leads_window_1106.py 2026-10-27`
- 新點名的名字：`python library/private/tmp/onboard_new_since_1106.py 2026-10-27`
- 圖上有沒有 MLCC 或電容層：`python library/private/tmp/anchors_and_layers_1106.py mlcc capacitor`
- 日立能源與 MLCC 的既有 lead：`python library/private/tmp/grep_leads_1106.py 2026-10-20 "hitachi energy" hitachienergy.com`、`python library/private/tmp/grep_leads_1106.py 2026-09-01 mlcc murata "taiyo yuden"`
