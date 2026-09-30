# 研究佇列追源結果（2026-09-30）

> 來源：唯讀追源 workflow（15 條 triaged_go 線索各一位追源者；建議入圖的再由懷疑者逐字核對）。**寫入一律由主 session 做**。
> 同日額度用完：15 條中 10 條追完，5 條沒跑完（原封留在 pq1）；建議入圖的 4 條，懷疑者核對步驟全部中斷——**未經核對，不做 RA 包**，狀態仍 triaged_go。
> 使用者 2026-09-30 指示「先不要每檔都跑、太花 token，先把 Phase 3 與核准的東西收乾淨」，所以段 5 每檔閉環與這 9 條的後續都暫停。
> 本檔是研究紀錄，不是 current-state truth；lead 的狀態以 `library/leads/pending_leads.json` 為準。

## 1. 已 park（6 條）

### lead_20ce4e7dbc43c34707018373137935ec

**結論：** 美國雙重掛牌仍停在「準備中、2027 上半年完成準備」，沒有正式決議、發行人 SEC 註冊或伴隨募資的一手證據；存託銀行已先設立 1:3 的 ADR 計畫（F-6EF，2026-09-29），不涉發新股。

**否定結果：** 1）triage 理由標為「新資訊」的「預計 2027 上半年完成的美國雙重掛牌」不是新資訊，而且讀過頭了。本機 library/raw/mfn_sivers_semiconductors_6543505f_att1.txt 第 156–158 行（Q2 2026 期中報告，2026-08-27）已經寫「We continue to progress our US dual listing preparations carefully and with discipline, and expect to complete all necessary preparations during H1 2027」。2027-H1 完成的是「準備」，掛牌本身仍是 potential，沒有承諾日期；Q2 當季還認列了 SEK 12.4m 的 US dual listing preparations 成本（同檔第 240 行）。
2）沒有更正式的掛牌公告。MFN 近 48 則（2026-05-20 至 2026-09-29）、官網 investors/shares 頁、2026-04-16 官方評估公告都只寫 evaluating／potential／preparations。
3）沒有伴隨募資的證據。EGM 議程沒有現金發行授權；2026-04 與 06-30 的增資用途都沒有列美國掛牌。
4）EDGAR 公開面沒有發行人的 F-1／20-F／8-A12B／公開 DRS。但依 L11-5，機密 DRS 無法排除，「找不到」不等於「沒遞」。
5）新發現的 2026-09-29 F-6EF（Deutsche Bank，CIK 0002157475，1 ADS＝3 股，25M ADS，Rule 466 即時生效）只有存託機構簽署、和發行人之間沒有合約，形狀符合存託銀行自行設立的 ADR 計畫（推論，原文沒有 unsponsored 一詞）。它不發新股、不是募資、不是 Nasdaq 掛牌，不觸發反證 #4。
6）連帶被排回的 lead_9b9d579795099de39f2ae6e50a5a5597（Saxo Japan／Nasdaq 掛牌推文）：它的 trace_next_trigger「Sivers 正式 Nasdaq dual-listing announcement」這次仍未成立，因為 EGM 公告措辭還是 potential，可以用同一句 outcome 續 park。
7）EDGAR 全文檢索裡 byNordic Acquisition Corp 的 8 筆命中日期都在 2024-08 到 2025-03，早於 2026-04 的評估公告，本次沒有打開，和這條線索無關。

**下一次重查的條件：** 任一項成立就重查：①EDGAR 出現 Sivers 發行人自己的新 CIK（不是 0002157475 /ADR）申報 F-1／F-1/A、20-F 註冊、8-A12B、公開的 DRS／DRSLTR，或由發行人共同簽署的新 F-6；②MFN 法定公告出現 Nasdaq（US）掛牌決議、ADS 發行或 US offering 意向、prospectus；③MFN 出現 2026-07 增資 120 天 lock-up 到期後的新定向增資或配售；④2026-11-26 Q3 報告的 dual listing 段落改寫（時程延後、放棄、或改成含 offering）

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** 建議新登記一筆（kind=semantic_condition 或 entity_filing_signal，entities=[\"co:sivers_semiconductors\",\"SIVE\"]）：
條件：「Sivers 美國掛牌正式化：EDGAR 出現發行人自己的申報（F-1／F-1/A、20-F 註冊、8-A12B、公開 DRS／DRSLTR，或發行人共同簽署的 F-6），或 MFN 法定公告出現 Nasdaq（US）掛牌決議、ADS offering、prospectus。⚠ 排除 CIK 0002157475『SIVERS SEMICONDUCTORS AB/ADR』的存託機構申報（F-6EF／POS AM 等）：2026-09-29 那份 F-6EF 是 Deutsche Bank 的 ADR 計畫，不算。」
叫醒時要做兩件事：(a) 重查本 lead，確認掛牌是否伴隨發行新股（F-1 註冊 primary shares 或同步定向增資）；(b) 若伴隨發行新股，喚醒 ew_0110（thesis sivers_v4_lane_memo.md#4 資金螺旋）做判定。只標旗不判定。
到期：2027-07-31（公司自述 2027-H1 完成準備，加 1 個月），到期時重問，不丟。
poll query_hint：EDGAR browse-edgar company=sivers，以及 efts 全文檢索 \"Sivers Semiconductors\" forms=F-1,20-F,DRS,8-A12B,F-6。
中途檢查點：2026-11-26 Q3 報告（ew_0149 的日期 watch 已涵蓋，不另登）。
附註：①既有 ew_0042_2026-08-31 的 query_hint 是「Sivers 正式 Nasdaq dual-listing announcement」，expires=2026-12-24，早於公司自己的時程。它到期時應改接這筆新 watch 重問，不要讓它靜默到期。②2026-07 增資承諾的 120 天發行 lock-up，以 7 月初交割推算約 2026-10 底到 11 月初到期（推算值）。不另登日期 watch，因為任何新增資公告都會經 MFN harvest 喚醒 ew_0110。

<details><summary>逐條 atom</summary>

- **臨時股東會召集公告第 6 點：提名委員會提議將會計師從 Deloitte AB 換成 Ernst & Young AB，理由之一是「為可能在美國雙重掛牌做準備，預期 2027 上半年完成」**｜original_obtained｜tier 1｜中性（重申既有時程，不是正式掛牌決議）
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/notice-to-attend-an-extraordinary-general-meeting-of-sivers-semiconductors-ab-535ec0a1（英文版公告「Election of auditor (item 6)」第 2 段；瑞典文原件同段：『förberedelserna för en potentiell dubbelnotering av aktierna i USA, som förväntas slutföras under första halvåret 2027』（kallelse-till-extra-bolagsstamma-...-f626491b）；JSON-LD datePublished=2026-09-29T16:51:51Z）
  - 逐字：The Nomination Committee considers it appropriate to establish a new long-term audit relationship with a Big Four firm in view of the Company's growth, its increasing international presence and its preparations for a potential dual listing of the shares in the United States, expected to be completed during the first half of 2027. Ernst & Young AB has extensive experience of Swedish listed companies with U.S. capital markets activities and SEC reporting requirements.
  - 圖裡已有？否。依 L4（屬性歸位：講的是市場，不是物理現實）掛牌屬資本市場事實，本來就不入圖。時程本身也不是新資訊：本機 library/raw/mfn_sivers_semiconductors_6543505f_att1.txt 第 156–158 行（Q2 2026 期中報告 CEO 信）已經寫了「expect to complete all necessary preparations during H1 2027」
- **換會計師的起因是歐盟 537/2014 規定的十年強制輪替，公告明文說不是因為對會計或財報有歧見**｜original_obtained｜tier 1｜反駁負面讀法
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/notice-to-attend-an-extraordinary-general-meeting-of-sivers-semiconductors-ab-535ec0a1（英文版公告「Election of auditor (item 6)」第 2 段）
  - 逐字：Deloitte AB has been the Company's auditor for ten years. Under Article 17 of Regulation (EU) No 537/2014, the audit engagement of a public-interest entity may as a general rule not exceed ten consecutive years. ... The proposal is not based on any disagreement regarding the Company's accounting or financial reporting
  - 圖裡已有？否（治理事實，不入圖）；ew_0111（信用重開）已在 2026-09-30 判定 touches=no
- **員工選擇權 P11 上限 7,280,000 股，稀釋約 2.0%；連同流通在外的 15,929,025 股選擇權，合計稀釋上限約 6.1%。截至 2026-09-29 普通股 356,740,332 股，公司自有 12,872,916 股**｜original_obtained｜tier 1｜中性
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/notice-to-attend-an-extraordinary-general-meeting-of-sivers-semiconductors-ab-535ec0a1（英文版公告 Resolution on a long-term incentive program（item 7）「Dilution effects」段；股數見「Number of shares and votes」段）
  - 逐字：The Board of Directors proposes that the P11 shall consist of a maximum of 7,280,000 new Stock Options ... corresponding to approximately 2.0 per cent of the shares and votes in the Company after dilution, based on the 356,740,332 ordinary shares outstanding in the Company as per 29 September 2026. Including the 15,929,025 stock options outstanding under the Company's existing incentive programs, P11 and the outstanding incentive programs together correspond to a dilution of not more than approximately 6.1 per cent
  - 圖裡已有？否（稀釋屬 Engine C 或歸零旗標的範圍，不入圖）；ew_0110 已判定 touches=no
- **這次臨時股東會沒有任何現金增資或一般性發行授權議案，唯一的發行授權是 P11 交付用的 C 類股（按面額 0.50 SEK 由銀行認購）**｜original_obtained｜tier 1｜不觸發反證 #4
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/notice-to-attend-an-extraordinary-general-meeting-of-sivers-semiconductors-ab-535ec0a1（英文版公告「Proposal for agenda」第 1–9 項；item 8 第 2 段）
  - 逐字：The purpose of the authorisation and the reason for the deviation from the shareholders' preferential rights in the event of implementation of the share issue is to ensure delivery of shares to participants under the Company's outstanding incentive programs and in order to on terms of liquidity to secure social security charges.
  - 圖裡已有？否；ew_0110 已判定 touches=no
- **2026-07-01 增資公告（約 SEK 700m）CEO 說『intent to complete the listing process over the next few quarters』；增資用途列的是 InP 產能、field、R&D，沒有掛牌；公司承諾增資完成後 120 天內不再發新股**｜original_obtained｜tier 1｜中性
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/sivers-semiconductors-has-resolved-on-a-directed-share-issue-of-shares-amounting-to-approximately-sek-700-million-a4130eba（CEO 引言末句；「Lock-up undertakings」段；用途見「The proceeds from the Directed Share Issue are for expanding manufacturing capacity for InP lasers and optical amplifiers...」；datePublished=2026-06-30T23:15:00Z）
  - 逐字：With all U.S. listings, the level of accounting and legal effort is significant and essential. As previously communicated, we continue to invest and make progress on all necessary steps with the intent to complete the listing process over the next few quarters" ... The Company has undertaken a lock-up undertaking, with certain exceptions, not to issue additional shares for a period of 120 calendar days after completion of the Directed Share Issue.
  - 圖裡已有？否（repo 裡沒有這份原文；KuCoin 2026-07-01 的『evaluation to execution』是二手轉述，只拿來找路）
- **2026-06-15 年度股東會授權董事會，在下次年度股東會前發行最多 53,844,956 股普通股（約 15%，可排除優先認購權）；7/1 的 700 MSEK 增資動用了這項授權，發行 12,280,701 股**｜original_obtained｜tier 1｜中性（反證 #4 的前置條件：已有工具，未動用）
  - 來源：https://mfn.se/cis/a/sivers-semiconductors/bulletin-from-sivers-semiconductors-ab-publ-s-annual-general-meeting-on-15-june-2026-cf1d358b（AGM 公報「Resolution on authorisation for the Board of Directors to resolve on issues of shares, warrants and/or convertible bonds」段；動用見 700 MSEK 公告首段「pursuant to the authorization from the annual general meeting on June 15, 2026, resolved on a directed share issue of 12,280,701 ordinary shares」）
  - 逐字：The Annual General Meeting resolved to authorise the Board of Directors to, on one or several occasions during the period until the next Annual General Meeting, with or without deviation from the shareholder's preferential rights, resolve on share issues, issues of warrants and/or issues of convertible bonds that involve the issue of or conversion to a maximum of 53,844,956 ordinary shares, corresponding to a dilution of approximately 15.0 per cent
  - 圖裡已有？否（融資能力屬 Engine C 的範圍）
- **【新一手，repo 0 命中】2026-09-29 Deutsche Bank Trust Company Americas 以 Form F-6EF 註冊 25,000,000 股代表 Sivers 普通股的 ADS，每 1 ADS＝3 股普通股，依 Rule 466 申報即生效**｜original_obtained｜tier 1｜中性（和發行人的掛牌是兩件事）
  - 來源：https://www.sec.gov/Archives/edgar/data/2157475/000110465926111655/tm2626116d1_f6ef.htm（F-6EF 封面 CALCULATION OF REGISTRATION FEE 表；Part II Item 3(c)；簽名頁只有存託機構（Michael Tompkins／Rob Bruder，簽於 2026-09-24）；Exhibit (a) Article 8 依 Rule 12g3-2(b) 豁免；Exhibit (e) 以 Hochtief AG（333-228091）的同條款 F-6 作 Rule 466 依據；EDGAR CIK 0002157475「SIVERS SEMICONDUCTORS AB/ADR」，file no. 333-299185，申報清單只有這一筆）
  - 逐字：American Depositary Shares evidenced by American Depositary Receipts, each American Depositary Share representing three (3) ordinary shares of Sivers Semiconductors AB | 25,000,000 American Depositary Shares ... It is proposed that this filing become effective under Rule 466 x immediately upon filing ... (c) Any material contract relating to the deposited securities between the Depositary and the issuer of the deposited securities in effect at any time within the last three years. - None.
  - 圖裡已有？否（repo grep 2157475／F-6EF／Deutsche Bank Trust 皆 0 命中；ADR 屬市場可得性事實，不入圖）。發行人官網 investors/shares 頁沒有提到 ADR
- **Sivers 美國掛牌已正式決議或已向 SEC 遞交發行人註冊（F-1／20-F／8-A12B），而且伴隨募資**｜partial｜tier 1（支持部分：Q2 報告、7/1 增資公告、EGM 公告）｜未支持（不是反駁，是還沒發生或看不到）
  - 來源：https://efts.sec.gov/LATEST/search-index?q=%22Sivers%20Semiconductors%22&forms=F-1,F-1/A,20-F,DRS,DRS/A,DRSLTR,8-A12B,F-6,F-6EF,F-6/A,CORRESP,UPLOAD,6-K,40-F,F-3（EDGAR 公司名搜尋『sivers』只回傳 /ADR CIK 0002157475。全文檢索加表單篩選，5 筆 DRS/A 全是無關公司（ACTUATE THERAPEUTICS、WISeSat.Space）。data.sec.gov submissions 對 CIK 0002157475 只有 F-6EF 一筆。MFN RSS（2026-05-20 至 2026-09-29，約 48 則）沒有任何正式掛牌或 ADS 發行公告。官網 /press/sivers-semiconductors-ab-evaluates-a-potential-dual-listing-of-its-shares-on-the-nasdaq-new-york/；本機 library/raw/mfn_sivers_semiconductors_6543505f_att1.txt L156-158）
  - 逐字：（沒有支持這一項的逐字原文。只有部分支持：①官網 2026-04-16 公告『evaluating a potential dual listing of its shares on Nasdaq New York while maintaining the company's Domicile in Sweden』；② Q2 2026 報告『expect to complete all necessary preparations during H1 2027』）
  - 圖裡已有？否

</details>

### lead_26bd4214b4b0434765071f14a7a955e4

**結論：** trace:partial——AXTI 點有界重查找到出處（Digitimes 2026-08-28，tier 3，paywall），但沒有 AXT 或商務部一手，也沒有圖增量；照舊 park

**否定結果：** 不是新瓶頸證據。觸發事件是同一作者 tier-4 推文，AXT 的 LTA 預付款早已入圖。第 13 點三句其實是 Digitimes 2026-08-28 付費文導言的轉述（tier 3，說話者是未具名的業界人士）。一手面：AXT 在 08-19 之後沒有新 filing 或實質新聞稿；商務部 2026 年 7–9 月沒有任何放寬磷化銦、砷化鎵或基板出口管制的公告。「近期放寬」在一手層沒有支持；「InP 基板嚴重短缺」只是既有 InP 受限敘事的轉述，結構已在圖中。

**下一次重查的條件：** （1）AXT 下一份 8-K（特別是 Item 2.02 的 2026Q3 業績，或 7.01／8.01）或 IR 新聞稿逐字揭露 InP／GaAs 出口許可狀態（例如恢復對美出貨）、ASP 或原料漲價、產能或新客戶承諾；（2）商務部公告欄出現調整 2024 年第 46 號的公告（第 72 號暫停期 2026-11-27 屆滿），或任何逐字含磷化铟／砷化镓／衬底的出口管制公告；（3）其餘 atoms 照舊：任一具名公司 filing／新聞稿逐字揭露對應的容量、價格、lead time 或客戶承諾。

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** 建議主執行者考慮登記兩個比 ew_0066 窄的 fact 型 watch，只叫醒本 lead 的第 13 點：
(a) 條件：EDGAR 出現 AXTI 新 8-K（Item 2.02／7.01／8.01），或 AXT IR 新聞稿逐字提到 export permit、indium phosphide／gallium arsenide 的價格、產能或客戶承諾；到期 2026-11-30；叫醒 lead_26bd4214b4b0434765071f14a7a955e4（重查 atom 13a／13b）。Q3 業績日期尚未經公告確認，只是依往例推估在 10 月底到 11 月初。
(b) 條件：商務部公告欄出現調整 2024 年第 46 號的公告（2025 年第 72 號暫停期 2026-11-27 屆滿），或任何逐字含磷化铟／砷化镓／衬底的出口管制公告；到期 2026-12-15；叫醒同一 lead（atom 13b）。
另外兩點觀察，只供參考，不是登記請求：
- ew_0066_2026-09-01 是涵蓋 27 個實體的 related_entity_signal，目前 active、到期 2026-12-30。它已被同作者的 tier-4 推文叫醒 4 次（09-09 GOOGL、09-11 SPCX、09-24 AXTI、09-30 AAPL），consumed_leads 共 10 筆，沒有一次帶來一手。這符合 L14 的「恆亮」形狀（未量測的機制不得享有默認信任；三個免 outcome 測試之一）。要不要收窄屬開發項，走 ROADMAP，不是這裡的 watch 決定。
- 2026-09-30T03:32 的第 4 次叫醒（lead_9a65a3ce681c46f375e8c211e3d18463，共用 AAPL／co:apple）不在本次 AXTI 有界重查範圍內，我沒有查。主執行者需要另外處理，或確認它已經併入這次重查。

<details><summary>逐條 atom</summary>

- **13a：GaAs 基板材料與鎵磊晶源料在 2026Q3 再一輪漲價，據報為管制初期的 5–6 倍**｜isolated_tier_3｜tier 3（宣稱來源 Digitimes；未取得原句）｜未驗證（access_blocked：Digitimes paywall）
  - 來源：https://www.digitimes.com/news/a20260828PD211/inp-substrate-capacity-demand-data-center.html（null）
  - 逐字：null（推文引號句 "5 to 6 times higher than at the early stage of the restrictions" 在 Digitimes 2026-08-28／07-01／06-15／08-25／08-27 五篇的可見段落皆 0 命中；推測在 08-28 付費正文內，未能核對）
  - 圖裡已有？否；而且屬時變價格，依 L4 永不入圖。AXT 10-Q（2026-08-13）只有泛用風險句 "We have experienced delays obtaining critical raw materials and spare parts, including gallium"，沒有 Q3 漲價揭露
- **13b：中國近期放寬了部分基板出口管制**｜isolated_tier_3｜tier 3｜一手面不支持也不反駁。商務部 2026 年公告第 1–38 號標題對磷化铟／砷化镓／镓／锗／衬底／暂停 0 命中；AXT 10-Q（2026-08-13）仍寫 "While we continue to receive permits, we have a backlog of orders for which we have not yet received permits"。「放寬」可能指逐案發證變多（Digitimes 2026-06-15 導言："China has allowed the release of a fresh supply of indium phosphide (InP) substrates, which are under export controls. A first 2026 batch shipped at the end of May"），不是法規變更；本輪無法區分
  - 來源：https://www.digitimes.com/news/a20260828PD211/inp-substrate-capacity-demand-data-center.html（Digitimes 2026-08-28（datePublished 2026-08-28T10:43:42+08:00）meta description／paywall 前導言首句；正文 "The article requires paid subscription."）
  - 逐字：Compound semiconductor supply-chain players say China has recently eased some substrate export controls, but the upgrade of high-frequency transmission in AI data centers toward 200G and 400G has made optical communications a key technology breakthrough,
  - 圖裡已有？否；出口管制狀態是時變政策，不入圖
- **13c：InP 基板嚴重短缺（per Digitimes）**｜isolated_tier_3｜tier 3｜與既有圖一致，無增量
  - 來源：https://www.digitimes.com/news/a20260828PD211/inp-substrate-capacity-demand-data-center.html（同上 meta description（在 "lo" 截斷））
  - 逐字：creating a severe indium phosphide (InP) substrate shortage and sparking a trend toward signing long-term contracts and lo
  - 圖裡已有？結構面已有：Lumentum FY2026 10-K 基板段（客戶端一手，extractions/lite_10_k_20260817_substrate.json）、AXT 與 Casela／Coherent／Lumentum 的 LTA 文件（已抽取）、Reuters／GSR 的 InP 市占引文（tier 3，co:axt competes_with 邊）。「嚴重」程度屬時變市場認知，不入圖
- **觸發 lead_cad23 的 AXT 句：AXT 用 LTA 客戶預付款支應擴產**｜original_obtained｜tier 1｜支持但無增量
  - 來源：https://www.sec.gov/Archives/edgar/data/1051627/000143774926027677/axti20260630_10q.htm（AXT 10-Q（2026-08-13）Item 1A 風險因子，LTA／customer prepayments 段（原文 HTML 有 &#160; 空白實體，已正規化）；另 Casela："Casela is required to pay 50% of the total purchase price as a prepayment"；Coherent："for a prepayment of $22,288,500"）
  - 逐字：We have entered into long-term supply agreements with customers that include customer prepayments or other advance payments.
  - 圖裡已有？是：extractions/axti_8_k_20260617_casela_supply.json、axti_8_k_20260702_coherent_inp_supply.json、axt_pr_lumentum_lta_2026_07_30.json
- **補充查到：商務部 2025 年第 72 號公告暫停 2024 年第 46 號第二款至 2026-11-27**｜original_obtained｜tier 1｜不支持 13b：全文沒有出現磷化铟／砷化镓／衬底，第 46 號第二款涵蓋哪些物項本文沒寫（L6：類別不能推出具體品項）；日期 2025-11-09 也不是 9 月的「近期」事件
  - 來源：https://www.mofcom.gov.cn/zcfb/blgg/gg/2025/art/2025/art_bc4513421bb24faaa84e44c2e4f36dc5.html（公告正文唯一一段；落款「商务部 2025年11月9日」）
  - 逐字：经批准，自即日起至2026年11月27日，商务部公告2024年第46号（《关于加强相关两用物项对美国出口管制的公告》）第二款暂停实施。
  - 圖裡已有？否（時變政策，不入圖）
- **1：Google 與 NVIDIA 一起參與 MediaTek US$3.9B 募資**｜lead_only_tier_4｜tier ?｜未驗證（有界重查範圍外）
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查，沿用前次）
  - 圖裡已有？否
- **2：Samsung Electro-Mechanics 揭露 US$778.9M MLCC 合約**｜original_obtained｜tier ?｜支持（沿用前次）
  - 來源：https://www.samsungsem.com/global/newsroom/news/view.do?id=10502（）
  - 逐字：null（前次已取得，本次未重開；客戶未具名）
  - 圖裡已有？否（前次判定客戶未具名、無可核准 graph delta）
- **3：中國通路調查稱行星滾柱螺桿、六維力感測器、靈巧手難以國產替代**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **4：Samsung 約 70% 記憶體產能承諾到 2031；TrendForce 預估 3Q26 伺服器 DRAM 合約價 QoQ +13–18%；SK Hynix 稱短缺延續到 2030**｜isolated_tier_3｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查；價格屬時變，L4 不入圖）
  - 圖裡已有？否
- **5：CXMT 小量生產 HBM3E、據報宣稱 LPDDR6 量產**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **6：Cisco 在 SEMICON Taiwan 稱 CPO 可量產部署、可插拔仍是主流；MRVL 稱客戶最早 2027 部署 scale-up optics**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **7：聞泰與 Nexperia 控制權爭議、Nexperia 資產 US$300M 被凍結；Apple 指控 OpenAI 銷毀證據**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查；非題材）
  - 圖裡已有？否
- **8：Soitec 有 10+ 客戶簽 LTA、US$200m 營收為 floor**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **9：高功率 MOSFET／大面積 TVS 交期約 52 週；STM 8/23 第三次漲價**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **10：傳統封裝產能 2027 缺口逾 20%，打線設備為主要瓶頸**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **11：六大 ABF 供應商 2026 滿載、交期 12–14 個月；NVDA／AMD／hyperscaler 鎖產能到 2028**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **12：CCL 第七次漲價 10–20%；HVLP4 銅箔缺口 2026 約 48%；Low-Dk／T-Glass 交期逾 30 週**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **14：AMD 與 AVGO 包下力成 FOPLP 大部分規劃產能**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **15：Intel 考慮以 Intel Foundry 代工 HBM4E base die；SK Hynix 回應部分內容與事實不同**｜lead_only_tier_4｜tier ?｜未驗證（含反證旗標，沿用前次）
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查）
  - 圖裡已有？否
- **16：OpenAI 囤積數萬台 Mac mini／Mac Studio；Anthropic 向 AMZN 租用 Mac mini**｜lead_only_tier_4｜tier ?｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2094704372831920324（）
  - 逐字：null（本次未重查；非題材）
  - 圖裡已有？否

</details>

### lead_05fd6b8549fc9482a754775461c90391

**結論：** Akamai 8-K 證實 Anthropic 以 7 年 take-or-pay 承諾 116 億美元買 CPU 雲端算力，Akamai 經 Jabil 寄售預購約 17 億美元記憶體元件；但沒有記憶體種類、記憶體供應商或 CPU 供應商名，所以只算需求端背景，對記憶體層沒有增量。

**否定結果：** 這條不是記憶體層（或 CPU 層）的圖增量，只是需求端背景。Anthropic 的 116 億美元承諾買的是 Akamai 的 CPU 雲端算力。Akamai 經 Jabil 寄售預購約 17 億美元的 memory components，這是買方端的預購行為，但一手文件沒有記憶體種類、沒有供應商名，也沒有 CPU 廠名。推文的「$AMD 到 $MU 應該高興」只是作者推論，8-K 本體、EX-99.1、說明會逐字稿都沒有支持。能入圖的只剩 Akamai、Jabil、Lenovo 三家覆蓋厚的中大型公司之間的邊，對「集中需求灌進薄供應層」的讀圖沒有貢獻。

**下一次重查的條件：** Akamai Q3 2026 10-Q（季末 2026-09-30，大型加速申報人期限約 2026-11-09）送件。8-K 明說 Anthropic MSA、Jabil Agreement（含 Build Request）、Lenovo Agreement 的全文會隨這份 10-Q 附上。只有當附件逐字出現記憶體種類（DRAM／DDR5／HBM／NAND）或具名的記憶體或 CPU 供應商時才重查。其他觸發：Akamai Q3 2026 法說點名供應商；或 Micron、Samsung、SK hynix、Jabil 自己的文件點名這筆預購。

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** 一筆 awaiting_external watch。條件：Akamai（CIK 1086222）的 Q3 2026 10-Q 送件，附件含 Anthropic MSA／Project Plans、Jabil Agreement（Build Request）、Lenovo Agreement（依 8-K Item 1.01 的預告）。到期：2026-11-16（10-Q 法定期限約 2026-11-09 再加一週緩衝）。到期時是重問，不是丟掉。叫醒：lead_05fd6b8549fc9482a754775461c90391，做一次有界重查，只 grep 附件有沒有逐字寫出記憶體種類（DRAM／DDR5／HBM／NAND）、記憶體供應商（Micron／Samsung／SK hynix 等）或 CPU 供應商（AMD／Intel）；命中才重評有沒有記憶體層增量，沒命中就維持 park。另外，推文的 AMD／MU atom 是「誰應該高興」的推論，不是「誰供應誰」的斷言，所以不建議照 source-trace 的截圖假設規則建 hypothesis；如果主執行者仍保守建一筆，co:akamai 不是圖節點，預期 query.bottleneck --what-if 的結構表不會動。

<details><summary>逐條 atom</summary>

- **Akamai 與 Anthropic 簽下約 116 億美元、7 年期的合約承諾（Akamai 供應專屬雲端算力與託管支援）**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1086222/000119312526401048/d288154d8k.htm（8-K（Date of Report 2026-09-18，2026-09-24 送件）Item 1.01「Anthropic Master Services Agreement」第一段；MSA 簽於 2026-05-05，本次是 Project Plan 2、Project Plan 3）
  - 逐字：pursuant to which the Company provides Anthropic with dedicated cloud computing capacity and related managed support services. Subject to any termination described below and satisfaction of certain delivery and service availability requirements, Anthropic has committed to pay the Company approximately $11.6 billion in the aggregate under the Project Plans. Each Project Plan has an initial seven-year term commencing on their respective service start dates.
  - 圖裡已有？否。co:akamai 不在 config/company_identity.json（走圖第 5 型 unresolved_names 仍列 AKAM）；co:anthropic 供給側目前只有 co:broadcom、co:nvidia 兩條 supplies_to
- **這筆承諾全部用於 CPU workload（推文寫 accelerated，原文是 accelerating；本案沒有 GPU）**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/0001086222/000119312526401048/d288154dex991.htm（EX-99.1 新聞稿 dateline 段（CAMBRIDGE, Mass., Sept. 24, 2026）；另見說明會 CFO Ed McGowan 回答 Oppenheimer 的提問："So this particular deal, the one we announced today, is all CPU."（Quartr 轉錄，tier 上限 2））
  - 逐字：The multi-year commitment will support Anthropic’s accelerating CPU workload demands by leveraging Akamai Cloud’s distributed AI infrastructure and software.
  - 圖裡已有？否
- **與這筆承諾相關的 capex 估計約 55 億美元**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/0001086222/000119312526401048/d288154dex991.htm（EX-99.1 倒數第二個內文段。說明會 CFO 補充時程：2026 年第四季約 17 億、2027 全年約 31 億、2028 年約 7 億）
  - 逐字：Total capital expenditures related to today’s $11.6 billion commitment are estimated to be approximately $5.5 billion.
  - 圖裡已有？不適用。capex 推估是時變數字，永不入圖（L4：屬性歸位看值會不會隨時間變）
- **2026 年 capex 增加約 17 億美元，用於確保並預購含記憶體在內的關鍵供應鏈零件**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/0001086222/000119312526401048/d288154dex991.htm（EX-99.1 倒數第二個內文段；CFO 在說明會上說在 2026 年第四季："First, we plan to spend approximately $1.7 billion of the $5.5 billion to secure and pre-purchase critical supply chain components, including memory, in the fourth quarter of 2026."）
  - 逐字：Akamai anticipates no impact to the company’s 2026 revenue guidance, and an increase of approximately $1.7 billion in capital expenditures in 2026 to secure and pre-purchase critical supply chain components, including memory.
  - 圖裡已有？不適用（時變 capex）
- **（一手新增、比推文更精確）Akamai 授權 Jabil 代購約 17 億美元的 memory components，以寄售方式由 Jabil 保管，使用時按成本回購**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1086222/000119312526401048/d288154d8k.htm（8-K Item 1.01「Jabil Agreement」第一段（Build Request 簽於 2026-09-24，依附 2019-05-23 的 Jabil MSA））
  - 逐字：Pursuant to the Build Request, the Company has authorized Jabil to purchase approximately $1.7 billion of memory components, with the Company paying Jabil all corresponding supplier invoice amounts upon Jabil’s receipt of such components. Pending use, Jabil will hold such components in consignment as bailee for the Company and will repurchase such components from the Company at cost as they are utilized.
  - 圖裡已有？否
- **Jabil 替 Akamai 代工客製伺服器硬體（候選新邊 co:jabil supplies_to co:akamai）**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1086222/000119312526401048/d288154d8k.htm（8-K Item 1.01「Jabil Agreement」第一段）
  - 逐字：pursuant to which Jabil provides the Company with contract manufacturing and related services, including the manufacture of customized server hardware and warranty, spare parts and repair services.
  - 圖裡已有？否。co:jabil 在 registry（JBL）、也在圖上，但只有 co:sivers_semiconductors supplies_to co:jabil 一條
- **（一手新增）Lenovo 供應 Akamai 硬體產品、軟體與服務，SOW 期限 7 年**｜original_obtained｜tier 1｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1086222/000119312526401048/d288154d8k.htm（8-K Item 1.01「Lenovo Agreement」（2026-09-23 簽署 MPSA 與 SOW No. 1））
  - 逐字：pursuant to which Lenovo will provide the Company and certain of its affiliates with hardware products, software programs and related services. ... The Lenovo SOW has a term of seven years.
  - 圖裡已有？否。co:lenovo 不在 registry
- **推文說「$AMD 到 $MU 應該高興」，隱含本案 CPU 由 AMD、記憶體由 Micron 供應**｜lead_only_tier_4｜tier 4｜unsupported（一手沒有支持；也不算反駁，只是沒點名）
  - 來源：https://x.com/aleabitoreddit/status/2103232350348001701（推文內文第二句。反向核對：在 8-K 本體、EX-99.1、說明會逐字稿三份文件逐字 grep AMD|Intel|EPYC|Xeon|Micron|Samsung|Hynix|DRAM|DDR|HBM|NAND|Nvidia|Supermicro|Dell，命中全是誤報（Address→ddr、intellectual／intelligence→intel），零真命中）
  - 逐字：$AMD to $MU should be happy to hear this…
  - 圖裡已有？co:amd、co:micron_technology 在圖上，但和 Akamai 或這筆交易沒有任何邊
- **「Anthropic／OpenAI 不是在喊 AI 放緩嗎」**｜lead_only_tier_4｜tier 4｜uncertain
  - 來源：https://x.com/aleabitoreddit/status/2103232350348001701（推文最後一句）
  - 逐字：So much for Anthropic/OpenAI calling for an AI slowdown?
  - 圖裡已有？不適用
- **合約是 take-or-pay：交付後保證付款；營收 2027 下半年開始，2028 年底滿載後年化約 17 億美元；整個組合的電力約 95–105 MW，多數在美國，由多家 colo 承接**｜original_obtained｜tier 2｜supports
  - 來源：https://stockanalysis.com/stocks/akam/transcripts/759377-investor-update/（2026-09-24 投資人說明會，CFO Ed McGowan 的 prepared remarks（Quartr 轉錄，第三方，tier 上限 2）。8-K 另有限定："Subject to any termination described below and satisfaction of certain delivery and service availability requirements"。CFO 也說 "there's some scarcity in the marketplace"，但沒指明是哪一種零件）
  - 逐字：Because of this take-or-pay structure, in which Akamai is guaranteed payment upon delivery, revenue will hold steady for the remainder of the contract once revenue is fully ramped.
  - 圖裡已有？不適用（時變的財務與營運數字）

</details>

### lead_bf096e971f65b0a1604848dc2bcae8d5

**結論：** 一手 8-K 已取得並逐字核對，是例行股息公告，沒有圖增量，也沒有 Engine C 增量，park。

**否定結果：** 這條 lead 不是瓶頸證據，也不是結構事實：MRVL 2026-09-25 的 8-K 是例行季度股息公告（Item 8.01＋9.01），附件只有股息新聞稿和公司簡介樣板，沒有點名任何客戶、供應商、產品或產能。它也沒有讓相關 lead lead_55bd36e6（SENKO 連接器層）的 trace_next_trigger 成立。

附帶發現兩件事，都不影響本 lead 的處置，交給主執行者判斷：

一、identity 漂移（INV-1：ticker 不是 entity identity，解析要走 registry）：Event Watch ew_0029_2026-08-31 的 entities 寫的是 'co:marvell'，但 config/company_identity.json 登記的是 'co:marvell_technology'（第 332 行），'co:marvell' 不在 registry 裡。這次比對成功是因為同一筆 watch 也列了 ticker 'MRVL'。等於那筆 watch 的 company_id 欄目前是死字，實際靠 ticker 在比對。'co:nvidia' 有登記，沒問題。

二、watch 雜訊：ew_0029 的種類是 entity_filing_signal，只要 MRVL 或 NVDA 發任何 filing 就會叫醒；但 lead_55bd36e6 真正在等的是語意條件（SENKO／US Conec 出現上市母體或被併購、第三家 connector 進入 CPO）。這條 lead 已經被叫醒三次（09-02、09-09、09-25），每次條件都沒成立，這次甚至只是股息 8-K。這很接近 L14-4 說的恆亮問題。要不要收窄屬於開發項，應寫進 ROADMAP，不是本 packet 的研究結論。

**下一次重查的條件：** 無。這條 lead 只對應單一份 filing，內容已完整取得且沒有增量，不需重查。MRVL 日後若有 Item 1.01（重大合約）、2.01（併購完成），或講客戶、供應協議、產能、CPO／光通訊元件的 7.01／8.01 filing，會各自成為新的 edgar lead，不掛在這條上。

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** 不登記新的 watch：這條 lead 是單一 filing 的終局 park，沒有要等的事件。

另外給主執行者兩個建議，都不屬於本 packet 的寫入範圍：

(a) ew_0029_2026-08-31 的 entities 把 'co:marvell' 改成 registry 裡的 'co:marvell_technology'。這是 INV-1 的 identity 修正；做之前先確認 event_watch 的比對邏輯吃的是哪個欄位。

(b) 評估 ew_0029 是否要從 entity_filing_signal（任何 MRVL／NVDA filing 都會叫醒）改成只在含 SENKO、US Conec 或 connector 字樣的文件才標旗。這是開發項，應先寫進 ROADMAP 排程，不在研究 packet 裡直接改。

<details><summary>逐條 atom</summary>

- **MRVL 2026-09-25 的 8-K（accession 0001628280-26-063592）只有兩個 Item：Item 8.01 Other Events（季度股息）與 Item 9.01 Financial Statements and Exhibits；沒有 Item 1.01／2.01／7.01 或任何講供應鏈、客戶、產能承諾的內容**｜original_obtained｜tier 1｜neutral_no_delta
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000162828026063592/mrvl-20260925.htm（8-K 本體 Item 8.01 段；EDGAR index-headers 的 ITEM INFORMATION 兩行是 'Other Events' 與 'Financial Statements and Exhibits'，和本體一致）
  - 逐字：Item 8.01 Other Events. On September 25, 2026, the Company announced that its Board of Directors had declared the payment of its quarterly dividend of $0.06 per share to be paid on October 29, 2026 to stockholders of common stock, including preferred stock on an as converted to common stock basis, of record as of October 9, 2026.
  - 圖裡已有？不適用：股息是可重取的時變財務事實，依 L4（屬性歸位：會隨時間變的值不進圖）不入圖。grep library/raw、extractions 找 063592／a20260925dividend 都是 0 筆，自家庫沒存過這份 filing
- **唯一的附件 EX-99.1 是股息新聞稿加上公司簡介的樣板文字，沒有點名任何客戶、供應商、產品或產能**｜original_obtained｜tier 1｜neutral_no_delta
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000162828026063592/a20260925dividendpressrele.htm（EX-99.1 第一段（dateline Santa Clara, Calif. (September 25, 2026)），接著 'About Marvell' 樣板段）
  - 逐字：Marvell Technology, Inc. (NASDAQ: MRVL), today announced a quarterly dividend of $0.06 per share of common stock, including preferred stock on an as converted to common stock basis, payable on October 29, 2026 to stockholders of record as of October 9, 2026.
  - 圖裡已有？不適用；簡介段（'we move, store, process and secure the world's data...'）是形容詞與樣板話，依 L6（公司名／型號必須在 quote 逐字出現才能建節點）不能當 node attribute
- **這條 8-K 是 Event Watch ew_0029 叫醒相關 lead lead_55bd36e6（SENKO／CPO 可拆卸光連接器層）的觸發事件。它沒有讓那條 lead 的 trace_next_trigger 成立：沒有 SENKO／US Conec 的上市母體或併購，也沒有第三家 connector 供應商進入 CPO**｜original_obtained｜tier 1｜does_not_satisfy_trigger
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000162828026063592/mrvl-20260925.htm（8-K 本體 Item 9.01 (d) Exhibits 清單（只列 99.1 與 104））
  - 逐字：99.1 Press Release dated September 25, 2026, titled “Marvell Technology, Inc. Declares Quarterly Dividend Payment”
  - 圖裡已有？lead_55bd36e6 的 refs.outcome（2026-09-26）已自述『只有 Item 8.01 季度股息』。本次打開一手原文獨立核對，和那句一致（L11-2：對自己引用的事實也用同一套追源紀律）

</details>

### lead_a6a00003eb1ad0fefdd1ed3e77d93233

**結論：** 注意交易資訊重訊（第53款）一手核對完成：無圖增量、Engine C 已承載 8 月營收；不滿足 lead_f169 的重查觸發條件。

**否定結果：** 這不是瓶頸證據、也不是新業務事件：它是櫃買中心因量價異常強制要求的反應式揭露，公司自陳無第 4 條重大訊息。8 月營收在 Engine C 已有（545,866 千元，YoY 37.44%，t21sc03 與 tpex openapi 兩個來源一致，as-of 視角 conflicts=[]）；本重訊只是既有事實的轉述。一處非實質差異：重訊的去年同月 398 百萬與法定月營收表的 397,141 千元不一致（四捨五入應為 397），所以重訊 YoY 37.19% ≠ 月營收表 37.44%；以法定月營收表為準，不需寫入。它觸發的 lead_f169 重查，觸發條件（CW laser 產品線、產能、具名客戶、聯亞關係）在本重訊中一個字都沒有出現，重查應以「觸發事件不滿足 trace_next_trigger」結束。另外 triage 理由寫的「可用於排序判斷」引用的是 2026-09-22 已退役的跨檔排序概念。

**下一次重查的條件：** 本 lead 不需重查（月營收、季報由 collector 機械承載）。只有華星光發布第 4 條所列重大訊息（新客戶／合約／擴產／資本支出）或 115Q3 季報附註出現客戶／產品線結構變化時，才另開新 lead，而不是重啟本則。

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** 不需登記 watch：沒有等待中的反證或確認事件，後續月營收與季報都由 collector 機械承載。給主執行者的旁註（開發項，屬 ROADMAP 不屬 pq2，不在本 packet 權限內）：第 53 款「注意交易資訊」重訊對高動能小型股會反覆出現，這次 triage 判為 financial_fact／go，又透過實體比對觸發了結構性追源 lead_f169 重查；兩者在結構上都不可能帶來圖增量。collector／triage 端可考慮把第 53 款重訊分類成「Engine C 機械已承載」，並排除在 related_triaged_lead 重查觸發之外，以免每一則都占掉 pq1 並誤觸重查。

<details><summary>逐條 atom</summary>

- **華星光 115/08（2026-08）單月營業收入 546 百萬元，去年同月 398 百萬元，年增 37.19%（合併自結數，未經會計師查核）**｜original_obtained｜tier 1｜neutral（與既有月營收觀測一致；另記一處非實質差異：重訊的去年同月 398 百萬與法定月營收表 397,141 千元不一致——397,141 四捨五入是 397 不是 398，重訊 YoY 37.19% 即 546/398；敘事若引用 8 月 YoY 應用 Engine C 的 37.44%，不用重訊的 37.19%）
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&step=2&firstin=true&off=1&seq_no=1&spoke_date=20260923&spoke_time=150255)（MOPS 重大訊息明細 序號 1，發言日期 115/09/23 15:02:55，符合條款第 53 款，說明 3.(1) 單月表第一列＋說明 6.(1)）
  - 逐字：營業收入(百萬元) 546 398 37.19% ... (1)115年8月和去年同期比較數之財務資料係本公司採IFRS會計準則編製之合併自結數，未經會計師查核(閱)，僅供投資人參考。
  - 圖裡已有？不適用入圖（L4：時變數字永不入圖）。Engine C monthly_revenue_observations 已有 4979.TWO 2026-08 兩列，兩個一手來源一致：mr_3b71e5e5…（mopsov t21sc03_115_8_0.html）與 mr_a338464f…（tpex openapi mopsfin_t187ap05_O），revenue_current=545,866 千元、revenue_year_ago=397,141 千元、change_yoy_pct=37.44；monthly_revenue_as_of(as_of=2026-09-30) conflicts=[]、available_on=2026-09-10。本次另以 curl 重讀 MOPS t21sc03_115_8_0.html（出表日期 115/09/30）逐字核對：『4979 華星光 545,866 508,777 397,141 7.28 37.44 3,537,229 2,939,879 20.31』。
- **華星光 115/08 單月稅前淨利 113 百萬元（年增 25.56%）、歸屬母公司業主淨利 92 百萬元（年增 2.22%）、EPS 0.64 元（去年同月 0.64 元），自結未查核**｜original_obtained｜tier 1｜neutral（營收年增 37% 但 EPS 持平：去年同月稅前＝歸母淨利＝90，即去年同月幾乎無所得稅費用，今年隱含稅率約 19%，加上股本增加；屬稅負正常化，不構成反證）
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&step=2&seq_no=1&spoke_date=20260923&spoke_time=150255)（MOPS 重大訊息 115/09/23 序號 1，說明 3.(1) 單月表第 2–4 列）
  - 逐字：稅前淨利(百萬元) 113 90 25.56% / 歸屬母公司業主淨利 92 90 2.22% (百萬元) / 每股盈餘(元) 0.64 0.64 -
  - 圖裡已有？不入圖（L4）。Engine C 沒有月度損益表，此三個數字未被承載；台股三題輸入（engine_c/three_question_inputs.py L106–114）只用 monthly_revenue，無 consumer 缺口。
- **華星光 115 年第 2 季單季營收 1,289 百萬元（年增 18.58%）、稅前淨利 248 百萬元（年增 161.05%）、歸屬母公司淨利 184 百萬元（年增 93.68%）、EPS 1.29 元（年增 92.54%），經會計師核閱**｜original_obtained｜tier 1｜neutral
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&step=2&seq_no=1&spoke_date=20260923&spoke_time=150255)（MOPS 重大訊息 115/09/23 序號 1，說明 3.(2) 單季表＋說明 6.(2)）
  - 逐字：營業收入(百萬元) 1,289 1,087 18.58% / 稅前淨利(百萬元) 248 95 161.05% / 歸屬母公司業主淨利 184 95 93.68% / 每股盈餘(元) 1.29 0.67 92.54% ... (2)最近一季115年第2季係指單季數字，係經會計師查核(閱)。
  - 圖裡已有？不入圖（L4）。Engine C 交叉核對：月營收 2026-04/05/06 相加 412,778＋421,247＋455,083＝1,289,108 千元 ✓；2025-04/05/06 相加 383,150＋347,922＋356,414＝1,087,486 千元 ✓。季度稅前／淨利／EPS 未以結構化列承載（fundamental_history 對 4979.TWO 0 列；manual_observations 只有 FY2025 fiscal_year_results 與 product_line_revenue_share），但台股三題路徑不消費季度損益，無 consumer 缺口；若日後需要，正確來源是 fetchers.mops --kind consolidated_financial_statement 的季報正本，不是本重訊。
- **華星光最近四季累計（114Q3–115Q2）營收 4,713 百萬元、稅前淨利 1,004 百萬元、歸屬母公司淨利 870 百萬元、EPS 6.15 元（經會計師查核(閱)）**｜original_obtained｜tier 1｜neutral
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&step=2&seq_no=1&spoke_date=20260923&spoke_time=150255)（MOPS 重大訊息 115/09/23 序號 1，說明 3.(3)＋說明 6.(3)）
  - 逐字：(3)最近四季累計 114年第3季至115年第2季 營業收入(百萬元) 4,713 稅前淨利(百萬元) 1,004 歸屬母公司業主淨利 870 (百萬元) 每股盈餘(元) 6.15
  - 圖裡已有？不入圖（L4）。Engine C financial_snapshots（4979.TWO，snapshot_date 2026-09-30，id 4102）revenue_ttm＝4,713,039,872 ✓，已機械承載。
- **本重訊的觸發事件是櫃買中心通知有價證券達「注意交易資訊標準」（第 53 款），公司聲明無第 4 條所列重大訊息之情事、無第 11 條記者會**｜original_obtained｜tier 1｜neutral（公司自陳股價異動背後沒有未揭露的重大業務事件——沒有新客戶、合約、擴產公告）
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&year=115&month=09 列表；明細 seq_no=1)（MOPS 重大訊息 115/09/23 15:02:55，符合條款 第53款，說明 2、4、5；115/09 該公司僅此一則重訊）
  - 逐字：2.發生緣由:依財團法人中華民國證券櫃檯買賣中心通知辦理。... 4.有無「財團法人中華民國證券櫃檯買賣中心對有價證券上櫃公司重大訊息之查證暨公開處理程序 」第4條所列重大訊息之情事（如「有」，請說明）:無。
  - 圖裡已有？不入圖：交易量價異常屬市場認知／時變（L4），股價由 price_history 機械承載。
- **（meta）本 lead 以實體比對觸發 lead_f169 重查（ew_0055_2026-08-31）；本重訊內容是否滿足 lead_f169 的 trace_next_trigger「CW laser 產品線、產能數字、具名客戶；聯亞供應關係求一手」**｜contradicts｜tier 1｜contradicts（對 f169 的重查觸發而言：重訊全文無雷射／產品線／產能／客戶／聯亞任何字樣，觸發條件不成立；f169 的重查是機械實體比對誤觸，不是新證據）
  - 來源：https://mopsov.twse.com.tw/mops/web/ajax_t05st01 (POST TYPEK=otc&co_id=4979&step=2&seq_no=1&spoke_date=20260923&spoke_time=150255)（MOPS 重大訊息 115/09/23 全文）
  - 逐字：3.財務業務資訊: (1)單月 ... (2)單季 ... (3)最近四季累計 ...（全文只有營收、稅前淨利、歸母淨利、EPS 四個科目）
  - 圖裡已有？圖中 co:luxnet 已存在（query.structure：需求錨 tech:optical_scale_up → co:lumentum → tech:cw_dfb_laser → co:luxnet，距需求端 3 跳；extractions/luxnet_4979_annual_report_fy2025.json 等 3 檔引用 co:luxnet）。

</details>

### lead_a56462e38aa2a955ddbc33e3dd700179

**結論：** 背景機制有一手支撐（MU D4/LP4 EOL、Alliance 替代通路、PSMC 協助客戶進 8G DDR4），但沒有具名小型承接者，候選集合不變；PSMC–Micron 新關係與 SK hynix 法定揭露的 LTA 限定句另以 watch／標旗處理。

**否定結果：** 沒有任何一手文件具名承接 MU 停產 legacy DRAM 的小型公司，作者心中的名單仍然未知。這條 lead 其實是既有公開事實的轉述：MU 在 2025-06 法說已公開 D4/LP4 EOL；Alliance 早在 2014／2016／2017／2025 就長期做 Micron EOL 料號的 drop-in 替代。再加上一個研究方向（追 PSMC）。它不改變候選集合，也沒有 AI capex 錨上的新邊。

「SK/Samsung 向更小記憶體公司採購」與「直供 Samsung」兩條都停在 tier 4。依 L11-5（「我找不到」與「它不存在」是兩個 claim），這是找不到，不是不存在：若答案存在，最可能在台灣 fabless DRAM 設計公司的 MOPS 年報，「主要進貨廠商」可能點名力積電，「主要銷貨客戶」則多以代號揭露、不得對應具名公司。這一步需要 fetchers.mops，本次唯讀邊界內沒走。

副產品有兩個：①SK hynix DART 1H2026 半年報新增「장기공급 계약에 따른 수주 현황은 없습니다」，它限定了圖中既有 claim sk_hynix_q2_2026_results_cl2 的措辭，交互動 session 判讀；②PSMC–Micron 的 post-wafer 關係有雙邊一手，但不足以 onboard，改掛 watch。

**下一次重查的條件：** ①Micron FQ4 FY2026 法說（2026-09-30 當天）逐字稿，或 FY2026 10-K（預期 2026-10 上中旬），以客戶端文字點名 PSMC 承接 post-wafer／HBM 製程或已通過驗證：重評 PSMC onboarding。②台灣 fabless DRAM 設計公司年報或月營收公告出現「主要進貨廠商：力積電」且有 8Gb DDR4 新產品線：開具名候選追源。③作者或任何其他來源具名承接 MU／Samsung EOL 料號的公司。④SK hynix 3Q26 분기보고서（約 2026-11 中）「나. 수주상황」一句是否再改寫。

**追源者建議的等待（未登記；park 的 trigger 已涵蓋時不另登）：** W1（語意條件，對既有 claim 標旗，不判定）
- 對象：extractions/sk_hynix_q2_2026_results.json 的 claim sk_hynix_q2_2026_results_cl2。它的 disproof：\"Update if ... disclosed LTA terms turn out to be non-binding framework agreements\"。
- 標旗依據：SK hynix DART 1H2026 半年報（rcpNo=20260814003509，本機 library/raw/sk_hynix_dart_semiannual_1h2026_20260814.txt 第 435 行）逐字：「당사는 주요 고객사들과 월별/분기별 상호 합의에 따른 공급 물량 및 가격을 결정하고 있으며, 장기공급 계약에 따른 수주 현황은 없습니다.」同一節在 FY2025 年報（rcpNo=20260317000635）只寫到「…결정하고 있습니다.」，也就是說完成 LTA 後才新增了「沒有依長期供應合約的在手訂單」子句。
- 叫醒：互動 session 判讀 cl2 的「customer-side lock-in」措辭要不要修（thesis／claim mutation 仍走人工 gate）。
- 到期：2026-11-20（SK hynix 3Q26 분기보고서 之後），到期重問，不丟。

W2（事件等待）
- 條件：Micron FQ4 FY2026 法說逐字稿（2026-09-30）、FY2026 10-K（預期 2026-10 上中旬）或其後任一 Micron filing，以客戶端文字點名 PSMC／Powerchip 承接 post-wafer assembly／HBM 相關製程，或說明驗證完成。
- 叫醒：重開本 lead，評估 PSMC onboard（ra_admission pq2）；可直接用 graph_delta_proposal 的草案。
- 到期：2026-11-30。

W3（可選，低優先）
- 條件：台灣 fabless DRAM 設計公司 FY2026 年報（約 2027-05）「主要進貨廠商」點名力積電，且有 8Gb DDR4 產品線營收。
- 叫醒：具名候選追源（本 lead 的原始問題）。
- 到期：2027-06-30。

<details><summary>逐條 atom</summary>

- **SK hynix／Samsung 的產能協議（capacity agreements）可能延長到 3–5 年（作者用的是條件句「if」）**｜partial｜tier 3（年期）／1（DART 的限定句）｜部分支持＋限定：五年期只有 tier 3 轉述支撐（SK hynix newsroom 原稿沒有年期）；法定揭露反而寫「沒有依長期供應合約的在手訂單、量價按月／季協議」
  - 來源：https://www.koreaherald.com/article/10828101 ；對照 C:\Users\Cheng\code\StockBotv2\library\raw\sk_hynix_dart_semiannual_1h2026_20260814.txt（DART rcpNo=20260814003509）（Korea Herald 全文（WebFetch 摘出，byline Moon Joon-hyun）；DART 半年報 II-4. 매출 및 수주상황 › 나. 수주상황（本機檔第 435 行））
  - 逐字：[Korea Herald 2026-08-02, tier 3] "Five years is the typical term, although conditions vary by customer and product."（SK hynix）；"The contracts generally begin with a five-year term and are reviewed annually, allowing another year to be added on a rolling basis."（Samsung）｜[SK hynix DART 1H2026 半年報, tier 1] "당사는 주요 고객사들과 월별/분기별 상호 합의에 따른 공급 물량 및 가격을 결정하고 있으며, 장기공급 계약에 따른 수주 현황은 없습니다."
  - 圖裡已有？部分：extractions/sk_hynix_q2_2026_results.json 的 cl2 已有「與約 10 家客戶完成 LTA」；年期沒有；DART 這句限定語從未被任何 extraction 引用（grep 全庫只命中 .gitignore 與 meta）
- **分析師對 2027E 模型給 2.8–3.3x（倍數）**｜lead_only_tier_4｜tier 4｜未驗證、未追
  - 來源：https://x.com/aleabitoreddit/status/2101906175046635887（推文本文）
  - 逐字：your analysts model 2.8-3.3x 2027E
  - 圖裡已有？否（也不應入圖）
- **legacy memory 有 ASP 調漲潛力，是現在有意思的交易**｜lead_only_tier_4｜tier 4｜作者意見
  - 來源：https://x.com/aleabitoreddit/status/2101906175046635887（推文本文）
  - 逐字：I think legacy memory a very interesting trade currently due to ASP hike potential
  - 圖裡已有？否
- **SK hynix／Samsung 會向更小的記憶體公司採購記憶體（小公司敏感度更高）**｜lead_only_tier_4｜tier 4｜未驗證
  - 來源：https://x.com/aleabitoreddit/status/2101906175046635887（推文本文）
  - 逐字：these same companies procure memory from even smaller memory companies (that might have higher sensitivity)
  - 圖裡已有？否
- **Micron 停產（EOL）了 legacy 記憶體（D4／LP4）**｜original_obtained｜tier 2（第三方轉錄上限；逐字稿裡有 "one alpha DNEM node" 這種轉錄錯字，要升 tier 1 必須對 IR replay）｜支持（背景事實，2025-06 已公開）
  - 來源：https://www.fool.com/earnings/call-transcripts/2025/06/25/micron-mu-q3-2025-earnings-call-transcript/（Micron FQ3 FY2025 法說（2025-06-25），Sanjay Mehrotra 的 prepared remarks，以 "Recent press reports have discussed the end of life of D4 and LP4 products." 開頭的那段）
  - 逐字：Micron has sent EOL notices for these products to customers in high-volume segments like mobile, client, data center, and consumer, several months ago with final shipments occurring in two to three quarters from now.｜"Micron intends to support its longevity customers with long-term and relatively lower volume requirements in segments like automotive, industrial, defense, and networking with the supply of these one alpha DRAM products."｜"We are now on allocation for these products"
  - 圖裡已有？否：圖裡只有 co:micron_technology supplies_to tech:dram_technology，沒有 DDR4／legacy DRAM 節點；本機 mu_10_k_fy2025_20251003.txt 對 end-of-life／EOL／discontinu 0 命中（10-K 只列 DDR4 為銷售組合，沒寫停產）
- **Alliance Memory 提供 Micron 停產 legacy DRAM 的替代品**｜original_obtained｜tier 1（僅限 Alliance 自己的產品供給；對 Micron EOL 的描述是 Alliance 轉述，不是 Micron 一手）｜支持（「透過 Alliance 替代」這個通路確實存在，而且是長期業務，不是新事件）
  - 來源：https://www.alliancememory.com/maintain-supply-and-lower-costs-with-alliance-memory-equivalents-for-eold-micron-dram/ ；https://www.alliancememory.com/about/（Alliance Memory 網頁，日期 July 31, 2025；About 頁 "Alliance Memory: Offering Drop-In Replacements..." 段）
  - 逐字：Micron Technologies has announced the end-of-life of its 60-series legacy DRAM products, including DDR, DDR2, LPDDR, and SDRAM. Alliance Memory offers direct, in-stock replacements for these parts—providing long-term availability and significant cost savings without the constraints of last-time buys or NCNR terms.｜"As a fabless semiconductor manufacturer, Alliance Memory provides a broad portfolio of legacy and new technology memory products"｜"Our pin-for-pin compatible solutions serve as drop-in replacements for memory ICs supplied by major manufacturers such as Micron, Samsung, Infineon/Cypress, Macronix, Winbond, ISSI, Nanya, and Hynix."｜"dual-sourcing supply strategy"
  - 圖裡已有？否；Alliance Memory 不在 config/company_identity.json
- **追 PSMC 晶圓配置可以找到透過 Alliance 或直供 Samsung、承接 MU 停產料號的公司（作者說不在 X 上點名）**｜partial｜tier 1（發行人自述）｜部分支持機制（PSMC 的 DRAM 代工客戶正要進 8Gb DDR4），但沒有任何具名客戶；「需求壓力」是供應商自述（L8：供應商自述不能當自己是瓶頸的獨立佐證）
  - 來源：https://www.powerchip.com/en-global/insights/press-releases/content/20260316 ；https://www.powerchip.com/en-global/insights/press-releases/content/20260121（PSMC 新聞稿 2026-03-16 第 2 段（Dr. Frank Huang）；2026-01-21 第 2、4 段）
  - 逐字：[PSMC 2026-03-16] "through the advancement of DRAM technology, PSMC will not only assist customers in entering the 8G DDR4 product line but also significantly increase the output value of wafer manufacturing"｜[PSMC 2026-01-21] "PSMC’s 12-inch wafer fab in Hsinchu possesses a monthly memory production capacity of 50,000 wafers, primarily providing DRAM and Flash foundry services using 2x-nanometer processes."；"the company has experienced intense demand pressure from customers in recent months"；"assist domestic and international memory design firms in developing high-specification products with greater capacity and speed"
  - 圖裡已有？否；PSMC／Powerchip／力積電在 extractions 與 company_identity 都是 0 命中
- **（追 PSMC 時順帶取得，lead 本身沒寫）Micron 以 US$1.8B 買下 PSMC 銅鑼 P5 廠；雙方意向建立長期關係：由 PSMC 承接 Micron 的 post-wafer assembly processing，Micron 支援 PSMC 的 legacy／specialty DRAM 製程**｜original_obtained｜tier 1（雙邊發行人）；但「HBM」一詞只出現在 PSMC 自述，Micron 端只寫 post-wafer assembly processing，而且停在 LOI 意向（"aims to"）｜新結構事實（lead 沒寫；是追 PSMC 時取得的）
  - 來源：https://investors.micron.com/news/press-release/2026/Micron-Signs-Letter-of-Intent-to-Purchase-Tongluo-Site-Begin-Strategic-Partnership-with-PSMC-01-17-2026/default.aspx ；https://www.powerchip.com/en-global/insights/press-releases/content/20260117 ；https://www.powerchip.com/en-global/insights/press-releases/content/20260316 ；https://www.sec.gov/Archives/edgar/data/0000723125/000072312526000015/mu-20260528.htm（Micron LOI 新聞稿第 1 段；PSMC LOI 新聞稿第 1、2 段；PSMC 完成交易新聞稿第 2 段；Micron 10-Q Note 7 Property, Plant, and Equipment）
  - 逐字：[Micron 2026-01-17] "The LOI also aims to establish a long-term relationship between Micron and PSMC for Micron’s post-wafer assembly processing and to support PSMC in its legacy DRAM portfolio."｜[PSMC 2026-01-17] "Micron will establish a long-term foundry relationship with PSMC on DRAM advanced packaging wafer manufacturing. Furthermore, Micron will assist PSMC in enhancing its existing specialty DRAM process technologies at it’s Hsinchu P3 fabrication."；"the company will be integrated into Micron’s DRAM advanced packaging supply chain upon passing certification."｜[PSMC 2026-03-16] "the company will further provide HBM/PWF foundry services to Micron."｜[Micron 10-Q 期末 2026-05-28, Note 7] "In March 2026, we completed the acquisition of a wafer fabrication facility in Tongluo, Miaoli County, Taiwan, from Powerchip Semiconductor Manufacturing Corporation for total cash consideration of $1.8 billion."
  - 圖裡已有？否：query.structure co:micron_technology 的供給側是 0 條

</details>

## 2. 建議入圖、但未經懷疑者核對（4 條，仍 triaged_go）

下列 graph delta 是**草案**：引用的逐字與 locator 還沒有第二位核對者打開原文驗過（L11-6）。做 RA 包之前，先重跑核對。

### lead_9a65a3ce681c46f375e8c211e3d18463

**追源者的判斷：** 三個有增量的 atom 都已追到 tier-1 原文，而且客戶端、供應端都有：
(1) 客戶端：MRVL 兩季 10-Q（2026-05-28、2026-08-28）逐字把 large body substrates 列為供給吃緊、造成 "inability to meet demand" 的資源之一；Q1 10-Q 另外揭露，季後已簽約鎖定 substrate 產能到 FY2033，並承諾付押金（押金與晶圓合計 $870.0M）。
(2) 供應端：AT&S 兩則公告。2026-06-15 說 Kulim 擴產 €1.5–2.0B "fully supported and financed by long-term customer commitments"，具名客戶 AMD；2026-09-22 的 EQS 說 Marvell 就是那家 "additional customer"。
(3) 供應端：Samsung Electro-Mechanics 2026-09-29 新聞稿，加上 DART 2026-09-28 신규시설투자 公告（4.27 兆韓元、占權益 43.6%）。新聞稿逐字寫 "Global customer funding support resolves risks of new facility investment (CAPEX)"，但沒有點名客戶。

圖裡目前沒有 package substrate 這一層（只有 mat:inp_substrate、mat:glass_substrate、mat:silicon_interposer、tech:advanced_packaging），co:marvell_technology 的「下一層」也是 0 條，所以增量是真的。

【能不能直接當新層入口，照實說】能，走最小切片。decompose skill 自己寫明「任何一層要進圖，走原本的 raw→extract→RA→pq2 路徑」，decompose 是用來發現「沒有線索的層」的研究地圖，不是入圖前置條件。這裡已經有 raw 撐著，不需要先 decompose。
但有兩點要分清楚：
①入圖只能證明「這層被客戶端卡住」，證明不了「這層薄」。一手可證的供應商已經有兩家（AT&S、SEMCO），兩家都拿客戶的錢擴產；Ibiden、Unimicron、Nan Ya PCB 等只出現在 tier-3 報導，這次沒有驗。所以載板廠這一層「幾家能做、換掉要多久」答不出來，substitutability 一律不填。
②真正可能薄的是上游：AT&S 自己（身為買方）逐字說 "currently tight supply of key materials such as fiberglass mats"；ABF 膜（Ajinomoto 約 95%）只有 tier-3 的 TechTimes 轉述 wing.vc。要把上游拆清楚是 decompose 級的問題，選題屬於使用者決定（不在常規授權內），我只提名、不代選。可提名的實體：「Marvell custom XPU 的 FCBGA 封裝」或「NVIDIA GB300 的 package substrate」。

【INV-1】co:ats（AT&S，ISIN AT0000969985，Vienna）與 co:samsung_electro_mechanics（009150.KS）都不在 config/company_identity.json。SEMCO 不得併進 co:samsung（那是 005930.KS Samsung Electronics）。E3–E6 要先由主執行者走 company-onboard 補 registry，和 RA 同包進 ra_admission pq2（packet 附 L8 來源清單）。E1、E2、E7 不需要新公司，可以先做。

【四維初判（AT&S，給 onboard 用）】
- 瓶頸地位：中偏弱。客戶端只證明「類別」吃緊，AT&S 是至少兩家之一，單家的可替代性未知。
- 需求錨：Marvell 在圖內，走 tech:ai_switch→tech:cpo→co:marvell_technology，2 跳到得了；AMD 在 registry 但圖中沒有邊。原文的終端寫的是 "custom accelerators"、"AI and cloud infrastructure"。
- 客戶端資本承諾：強，這是四維裡最硬的一項。AT&S 原文 "payments from customers"；MRVL 自揭有 substrate 產能押金。但 $870M 在逐字上無法歸屬給 AT&S（L6）。
- 純度：未知。AT&S 也做 mobile、automotive、industrial PCB，IC substrate 營收占比屬 Engine C，這次沒取；官網列有 Hybrid Convertible Bond 2026，稀釋與負債也待 Engine C 看。
SEMCO 是 MLCC／相機模組／載板的大型綜合廠，純度低、覆蓋厚，不是「邊緣小公司」候選。它入圖的價值只在「同一層的第二家一手可證供應商」，讓這一層讀得出供應端分散。

【附帶發現，不屬本線索】DART 20260929800281：SEMCO 與「글로벌 대형기업」簽 MLCC 及 Inductor 供應合約，USD 210,801,070，期間 2027-01-01～2027-12-31，無預付款，對手名稱保密到 2027-12-31。可能跟 triaged_go 的 lead_26bd4214b4b0434765071f14a7a955e4（SEMCO MLCC 交易）有關，交主執行者判斷。

【程序備註（誠實揭露）】第一次 curl webdisclosure.com 時，我在 User-Agent 字串裡帶了使用者 email 的 local-part（"c3035281"），只有那一次請求，之後都改成通用 UA。這違反「不得把 email 送到無關服務」的規則，特此記錄。除了 scratchpad 暫存檔，repo 沒有任何寫入。

**否定結果：** ① 「NVDA 拿下 LITE Greensboro 50% UHP 雷射產能、並可能鎖剩下的（Barclays 在 ECOC 的通路調查）」：isolated_tier_3。Barclays 報告不公開，只找到推文本身的轉載（KuCoin，same_origin）。圖裡已有 co:nvidia invests_in co:lumentum、co:lumentum supplies_to co:nvidia（designed_in）、Greensboro InP fab（lumentum_q3fy26_cpo），沒有增量。產能占比是合約條款、而且會隨時間變（L4），就算證實也不進圖。不建議建假設：邊早就存在，what-if 結構表不會動。
② 推文說 MRVL 把 large body substrates 列為 "core bottlenecks of their program"：措辭是作者自己的框架（L11-1）。10-Q 原文是三個例子之一："tight supply environment ... such as advanced wafer fabrication, advanced packaging, and large body substrates"。
③ SEMCO 的出資客戶是誰，一手沒有揭露。Korea Herald 寫的 "Nvidia and other big-tech customers had provided advance payments" 是轉述當地媒體轉述業界人士（tier 3 轉 tier 3），不得建 SEMCO→NVIDIA 邊。
④ MRVL Q1 10-Q 的 $870.0M 押金涵蓋 wafer 加 substrate，沒有點名供應商。時間上和 AT&S 2026-06-15 公告吻合，但逐字上無法歸屬 AT&S，不得相連。
⑤ 「與 AT&S 等多家簽擴產協議」：一手只證實 AT&S 一家，其他具名載板夥伴找不到。這是「我找不到」，不是「不存在」（L11-5）。
⑥ MRVL FY2026 10-K 全文有沒有 large body substrates 沒驗成（WebFetch 截斷；repo 裡的 raw 只是節錄），不能說 10-K 沒寫。
⑦ 載板廠這層依現有一手資料不是薄層：至少兩家 tier-1 可證、而且都在擴產。可能的薄層在上游（玻纖布、ABF 膜），目前未驗證。
⑧ AMD 以 $8.2B 收購 World Labs、NVDA $150B 回購、OpenAI 延後 Astra-6.1：題材外或時變財務，沒有追。

**graph delta 草案：**

【最小切片：package substrate 層入口】（所有 published_at 都取原文日期，不用抓取日）

■ 節點
N1 mat:ic_package_substrate（新）｜type=Material｜abstraction_level=materials_substrate（比照 mat:glass_substrate、mat:silicon_interposer）｜name "IC Package Substrate"｜aliases 只收各自原文裡逐字出現的詞："large body substrates"（MRVL 10-Q）、"advanced IC substrates"／"IC substrates"（AT&S）、"FCBGA"／"Flip Chip-Ball Grid Array"（SEMCO）、"패키지기판"（DART）。
  定義 quote（SEMCO PR 2026-09-29，tier 1，origin_entity Samsung Electro-Mechanics）："FCBGA is a highly integrated semiconductor substrate that connects high-performance semiconductors such as AI accelerators, GPUs, and CPUs to the mainboard, supplying electrical signals and power."
  ⚠ 四個詞併成一個節點是建模判斷（L12：FCBGA 是封裝形式，large body 是尺寸屬性）。保守的替代做法是另建 mat:fcbga_substrate is_variant_of mat:ic_package_substrate。
  ⚠ 不要把它併進 tech:advanced_packaging：MRVL 原文把 "advanced packaging" 和 "large body substrates" 並列成兩項。
N2 co:ats（新；registry 未登錄，要先走 company-onboard）｜AT&S Austria Technologie & Systemtechnik AG｜aliases "AT&S"｜ISIN AT0000969985｜Vienna Stock Exchange｜market_currency EUR。
  quote（AT&S EQS 2026-09-22）："AT&S is a global technology company and leading manufacturer of high-end IC substrates and complex printed circuit boards."
N3 co:samsung_electro_mechanics（新；registry 未登錄）｜Samsung Electro-Mechanics Co., Ltd.｜009150.KS｜KRW。⚠ 不等於 co:samsung（005930.KS）。
N4（可選）mat:fiberglass_mat（新）｜"fiberglass mats" 逐字見 AT&S 2026-06-15。

■ 邊
E1 co:marvell_technology constrained_by mat:ic_package_substrate｜confidence≈0.9｜兩個 origin_event，同一 origin_entity（Marvell，客戶端）：
  s1 doc mrvl_10_q_20260828（已在 library/raw）｜tier 1｜URL https://www.sec.gov/Archives/edgar/data/1835632/000183563226000025/mrvl-20260801.htm｜locator Part II Item 1A "We rely on our manufacturing partners…"（p.46–47）｜quote "We are currently in a supply constrained environment. These supply challenges have limited our ability to fully satisfy demand for some of our products. For example, there continues to be a tight supply environment for AI related components and manufacturing resources, such as advanced wafer fabrication, advanced packaging, and large body substrates which results in increased lead times, inability to meet demand, and increased costs."
  s2 doc mrvl_10_q_20260528（新存）｜tier 1｜URL https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm｜locator Part II Item 1A｜quote "there has and continues to be a tight supply environment for AI related components and manufacturing resources, such as advanced wafer fabrication, advanced packaging, and large body substrates which have in the past and may continue to result in increased lead times, inability to meet demand, and increased costs."
E2（可選）co:marvell_technology constrained_by tech:advanced_packaging｜同 E1 的 s1、s2。
E3 co:ats supplies_to mat:ic_package_substrate｜tier 1｜origin_entity AT&S｜URL https://ats.net/en/ir-news/ats-and-marvell-technology-expand-collaboration-to-support-next-generation-ai-infrastructure/｜quote "to increase advanced IC substrate capacity for next-generation AI and cloud infrastructure"＋N2 那句自述。
E4 co:ats supplies_to co:marvell_technology｜tier 1｜origin_entity AT&S（EQS News ID 2402726，2026-09-22 09:16 CEST）｜quotes：
  "The agreement builds on the companies’ existing relationship and supports Marvell Technology’s growing demand for advanced substrates as AI deployments continue to scale."
  "Marvell Technology is the additional customer identified in AT&S’s previously announced expansion of its Kulim manufacturing site."
  Marvell SVP & CSCO Vinay Krishna："Our expanded collaboration with AT&S further strengthens our supply chain foundation and positions us to scale increasingly complex semiconductor solutions…"
  屬性：不主張 sole_source；qualification_status 不填（"existing relationship" 不是 qualified 的逐字）；substitutability 不填。
E5 co:ats supplies_to co:amd｜tier 1｜origin_entity AT&S｜URL https://ats.net/en/press/ats-expands-kulim-site-to-support-long-term-customer-demand-and-deepen-strategic-technology-partnerships/（2026-06-15）｜quote "AT&S announced the expansion of its Kulim manufacturing site, based on agreements with its customer AMD and another leading technology company."
E6 co:samsung_electro_mechanics supplies_to mat:ic_package_substrate｜tier 1｜origin_entity SEMCO｜quotes：PR https://www.samsungsem.com/global/newsroom/news/view.do?id=10562 "Investment of KRW 4.27 trillion to expand high-performance semiconductor substrate (FCBGA) production at the Sejong business site in Korea"；DART https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260928800810 "투자대상 패키지기판 생산시설 증설"。
E7（可選，alpha 關聯低）co:tsmc supplies_to co:marvell_technology｜sole_source=true，範圍限 advanced process-node wafers｜客戶端陳述，符合 L8 強證據｜doc mrvl_10_q_20260828｜locator Item 1A "Regional Concentration"（p.46）｜quote "Taiwan Semiconductor Manufacturing Company Limited (\"TSMC\") is currently our sole source foundry for all of our advanced process-node wafers."；輔證 "TSMC is currently the sole wafer supplier for our advanced node products, including our 3nm products."
E8（可選）co:ats constrained_by mat:fiberglass_mat｜tier 1｜AT&S 是這項材料的買方，對上游層而言是客戶端陳述｜URL 同 E5｜quote "The forecast assumes no significant deterioration of the geopolitical situation or in the currently tight supply of key materials such as fiberglass mats."

■ Claims（每條都附 disproof 三件套，L7）
C1（subject E4／E5）AT&S Kulim 擴產 €1.5–2.0B「fully supported and financed by long-term customer commitments」，含 "payments from customers"；客戶為 AMD（6/15）與 Marvell（9/22 指為 "the additional customer"）。
  demand_proof_level：guided。供應端自述；6/15 時條款仍 "subject to final negotiation and execution"，客戶端沒有具名付款揭露。
  disproof：AT&S 公告協議終止、縮減或 Kulim Plant 2 延後，或後續財報沒有認列客戶付款（合約負債／預收）｜核查頻率：AT&S 每季財報與 ad-hoc｜觸發後 48h：把 C1 降為 inferred，E4／E5 標 review_required 並重讀原文。
C2（subject E1）MRVL 客戶端：large body substrates 供給吃緊，限制其滿足需求（Q1→Q2 措辭從 "may continue to result" 改成 "results in"，屬 dated claim）；另外自揭已鎖定 substrate 產能到 FY2033 並付押金（押金含晶圓，合計 $870.0M，供應商未具名）。
  demand_proof_level：confirmed（客戶自揭）。
  disproof：下一份 MRVL 10-Q／10-K 的 Item 1A 從吃緊清單移除 large body substrates，或改稱供給正常化｜核查頻率：每季 MRVL filing｜觸發後 48h：E1 改為歷史 dated claim、讀圖標 review_required。
C3（subject E6）SEMCO 世宗 FCBGA 4.27 兆韓元（占 2025 年底合併權益 43.6%），"includes customer funding support and mid- to long-term volume guarantees"，客戶未具名。
  demand_proof_level：guided。
  disproof：DART 出 정정公告縮減或撤回신규시설투자，或 SEMCO 法說稱客戶出資沒有到位｜核查頻率：每季 SEMCO 財報與 DART｜觸發後 48h：C3 降級、重看 E6 是否只剩產能自述。

■ L8 盤點
「這一層被卡住」的主張有 3 個不同 origin_entity：Marvell（客戶端，2 個 origin_event）、AT&S（供應端）、SEMCO（供應端），其中有客戶端來源。沒有任何載板供應商的 sole_source 主張。

■ 不進圖、交 Engine C
MRVL "Prepayments on supply capacity reservation agreements" 487.0（2026-08-01）vs 278.8（2026-01-31），單位 $M｜MRVL 季後押金 $870.0M（as_of 2026-05-28）｜SEMCO 投資額與占權益 43.6%｜AT&S 2026/27 營收成長 45–55%、EBITDA margin 32–37%、CAPEX €1.0–1.2B（6/15 指引）。

■ 追源紀錄
local：grep extractions／library/raw／config（substrate、FC-BGA、ABF、AT&S、Samsung Electro 在圖中皆無）；query.structure co:marvell_technology、co:tsmc；engine_b.cli related；sourcing.routes MRVL／ATS.VI／009150.KS。
EDGAR：直接讀 Archives 的 mrvl-20260502.htm 與 0001835632-26-000019-index（申報日 2026-05-28）；FY2026 10-K 經 WebFetch 截斷，未完成。
AT&S：ats.net IR news 與 press、webdisclosure.com（EQS 轉載）。
SEMCO：samsungsem.com newsroom list-ajax → view.do?id=10562；DART detailSearch → rcpNo 20260928800810、20260929800281（MLCC，無關）、20260928800821（越南子公司，未讀）。
搜尋：Korea Herald、KED Global、TechTimes（tier 3，只作指路）。
paywall／登入：無。

**建議的等待（未登記）：** W1｜條件：MRVL Q3 FY27 10-Q 申報（季末約 2026-10-31，預計 12 月上旬）。檢查 Item 1A 的 "large body substrates" 吃緊措辭是持續、升級還是移除（C2／E1 的反證點），以及 substrate 產能協議有沒有點名供應商（能否把押金歸屬到 AT&S）｜到期 2026-12-15｜叫醒：本線索的 E1／C2 disproof 與 AT&S onboard packet。
W2｜條件：AT&S H1 2026/27 半年報（預計 2026-11 上旬）。檢查 Kulim 協議是否已 final execution、客戶付款是否認列、IC substrate 營收占比（純度）、fiberglass mats 供給評論｜到期 2026-11-20｜叫醒：C1 disproof、AT&S 四維的純度欄。
W3｜條件：SEMCO 2026 Q3 財報與法說（預計 2026-10 下旬），以及 DART 上任何 신규시설투자 정정公告。檢查出資客戶是否具名、FCBGA 稼動率｜到期 2026-11-05｜叫醒：C3 disproof；若客戶具名，才可評估 SEMCO→客戶邊。
W4（低優先，fact_verification）｜條件：Lumentum FQ1 FY27 10-Q（預計 2026-11 上旬）有沒有揭露 NVIDIA 的產能保留或 Greensboro 產能分配｜到期 2026-11-20｜叫醒：atom 1（isolated_tier_3）重查。

**要存進 library/raw 的原文：**
- https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm：MRVL Q1 FY27 10-Q（申報 2026-05-28）。客戶端 tier-1：Item 1A 的 large body substrates 吃緊句（E1 的第二個 origin_event），以及 Note 9 的 substrate 產能押金句（C2）。依 EDGAR 截斷坑，存 curated excerpt（Item 1A 該段＋Note 9＋MD&A Liquidity 該句），不要 head-truncate
- https://ats.net/en/ir-news/ats-and-marvell-technology-expand-collaboration-to-support-next-generation-ai-infrastructure/：AT&S EQS 2026-09-22（News ID 2402726）。E3／E4 的一手，含 Marvell CSCO 具名引述
- https://ats.net/en/press/ats-expands-kulim-site-to-support-long-term-customer-demand-and-deepen-strategic-technology-partnerships/：AT&S 2026-06-15 Kulim 擴產公告。客戶出資（C1）、AMD 具名（E5）、fiberglass mats 吃緊（E8）的一手
- https://www.samsungsem.com/global/newsroom/news/view.do?id=10562：SEMCO 2026-09-29 新聞稿。FCBGA 擴產與 customer funding support 的逐字（E6／C3），也是 N1 的定義句
- https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260928800810：SEMCO DART 신규시설투자등（2026-09-28 董事會決議）。法定揭露的投資標的（패키지기판）、金額與占權益 43.6%，是 E6 的第二份一手，也是 Engine C 的數字來源

<details><summary>逐條 atom</summary>

- **NVIDIA 透過 ECOC 通路調查（Barclays）已取得 Lumentum Greensboro 50% UHP 雷射產能，且可能有合約可鎖剩餘產能（推文估 $5B／年）**｜isolated_tier_3｜tier 3（券商通路調查轉述；原報告付費不可得）｜neutral
  - 來源：https://x.com/aleabitoreddit/status/2104698369591706069（）
  - 逐字：
  - 圖裡已有？部分：co:nvidia invests_in co:lumentum（lite_8_k_20260302、nvda_lumentum_partnership_pr_2026_03_02、lumentum_q3fy26_cpo）、co:lumentum supplies_to co:nvidia designed_in、Greensboro InP fab（lumentum_q3fy26_cpo_s1 等）已入圖；50% 產能占比不在圖內，依 L4 也不應進圖
- **Samsung Electro-Mechanics 正擴大 FC-BGA 載板產能（世宗廠 4.27 兆韓元，2026-09～2028-05；越南子公司約 2.51 兆韓元）**｜original_obtained｜tier 1｜supports
  - 來源：https://www.samsungsem.com/global/newsroom/news/view.do?id=10562（SEMCO Press Release 2026.09.29 摘要第一點；DART rcpNo=20260928800810 신규시설투자등 第1–4項（이사회결의일 2026-09-28））
  - 逐字：Investment of KRW 4.27 trillion to expand high-performance semiconductor substrate (FCBGA) production at the Sejong business site in Korea - Investment period from September 2026 to May 2028, with mass production starting in September 2028… Largest single-product investment to date ／ DART：투자대상 패키지기판 생산시설 증설 … 투자금액(원) 4,270,000,000,000 … 자기자본대비(%) 43.6
  - 圖裡已有？否（圖中沒有 SEMCO、沒有 package substrate 節點）
- **Samsung Electro-Mechanics 這次 FC-BGA 擴產由客戶出資，並有中長期量能保證**｜original_obtained｜tier 1｜supports
  - 來源：https://www.samsungsem.com/global/newsroom/news/view.do?id=10562（SEMCO Press Release 2026.09.29 摘要第二點與「Establishing FCBGA Production System…」段；DART 公告本身沒提客戶出資）
  - 逐字：Securing business stability through global customer funding support and mid- to long-term volume commitments - Global customer funding support resolves risks of new facility investment (CAPEX) … As the investment includes customer funding support and mid- to long-term volume guarantees, the company expects to strengthen the competitiveness of its FCBGA business based on a stable demand foundation.
  - 圖裡已有？否
- **SEMCO 的出資客戶包括 NVIDIA（當地媒體引述業界人士）**｜isolated_tier_3｜tier 3（媒體轉述他報、再轉述匿名業界人士）｜neutral
  - 來源：https://www.koreaherald.com/article/10887298（Korea Herald 2026-09-29, Moon Joon-hyun）
  - 逐字：Local media reports citing multiple industry officials said Nvidia and other big-tech customers had provided advance payments totaling trillions of won
  - 圖裡已有？否
- **Marvell 在 SEC 文件把 large body substrates 列為造成供給受限的資源之一**｜original_obtained｜tier 1（客戶端 filing）｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000183563226000025/mrvl-20260801.htm（10-Q（期末 2026-08-01，申報 2026-08-28）Part II Item 1A，風險因子 "We rely on our manufacturing partners…"（p.46–47，接在 TSMC 產能保留段之後）；毛利率風險因子另有一處同句。Q1 FY27 10-Q（申報 2026-05-28）同段措辭為 "have in the past and may continue to result in"，Q2 改成現在式 "results in"）
  - 逐字：We are currently in a supply constrained environment. These supply challenges have limited our ability to fully satisfy demand for some of our products. For example, there continues to be a tight supply environment for AI related components and manufacturing resources, such as advanced wafer fabrication, advanced packaging, and large body substrates which results in increased lead times, inability to meet demand, and increased costs.
  - 圖裡已有？否。原文已在 library/raw/mrvl_10_q_20260828.txt（meta 有 accession 000183563226000025），但沒有抽取；既有 extractions 無 substrate 相關邊
- **Marvell 先進製程晶圓 sole source 依賴 TSMC**｜original_obtained｜tier 1（客戶端 filing）｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000183563226000025/mrvl-20260801.htm（Q2 FY27 10-Q Part II Item 1A，"Regional Concentration" 小節（p.46）與前一段 foundry 依賴說明）
  - 逐字：Taiwan Semiconductor Manufacturing Company Limited ("TSMC") is currently our sole source foundry for all of our advanced process-node wafers. ／ In particular, TSMC is currently the sole wafer supplier for our advanced node products, including our 3nm products.
  - 圖裡已有？否（co:tsmc 在圖中沒有任何 supplies_to 邊；co:marvell_technology 的下一層 0 條）
- **Marvell 近期與 AT&S 簽擴產／產能協議**｜original_obtained｜tier 1（發行人 EQS 公告，EQS News ID 2402726）｜supports
  - 來源：https://ats.net/en/ir-news/ats-and-marvell-technology-expand-collaboration-to-support-next-generation-ai-infrastructure/（EQS-News 2026-09-22 09:16 CEST，Key word(s): Agreement；第 1 段與 "Building a long-term partnership" 段的 Marvell 高管引述）
  - 逐字：Leoben, September 22, 2026 – AT&S today announced an expanded collaboration with Silicon Valley company Marvell Technology, a leading provider of data infrastructure semiconductor solutions, to increase advanced IC substrate capacity for next-generation AI and cloud infrastructure. The agreement builds on the companies’ existing relationship and supports Marvell Technology’s growing demand for advanced substrates as AI deployments continue to scale. Marvell Technology is the additional customer identified in AT&S’s previously announced expansion of its Kulim manufacturing site. ／ （Marvell SVP & CSCO Vinay Krishna）“Our expanded collaboration with AT&S further strengthens our supply chain foundation and positions us to scale increasingly complex semiconductor solutions…”
  - 圖裡已有？否（AT&S 不在 registry、也不在圖中）
- **AT&S Kulim 擴產（€1.5–2.0B）由長期客戶承諾出資、含客戶付款，客戶為 AMD 與另一家（9/22 揭露為 Marvell）**｜original_obtained｜tier 1（發行人公告）｜supports
  - 來源：https://ats.net/en/press/ats-expands-kulim-site-to-support-long-term-customer-demand-and-deepen-strategic-technology-partnerships/（AT&S Press 2026-06-15 第1段、"Financial discipline and risk mitigation"、"Increased outlook" 段）
  - 逐字：Leoben, June 15, 2026 – AT&S announced the expansion of its Kulim manufacturing site, based on agreements with its customer AMD and another leading technology company. … Based on agreed upon key terms, the € 1.5 to 2.0 billion investment is fully supported and financed by long-term customer commitments. … Key financial elements of the agreements, which remain subject to final negotiation and execution, include payments from customers, which are expected to positively impact revenue and earnings in the current year.
  - 圖裡已有？否（co:amd 在 registry，但圖中沒有任何邊）
- **Marvell 自揭：季後簽約鎖定晶圓與載板產能（分別到 FY2030／FY2033），承諾付押金合計 $870.0M**｜original_obtained｜tier 1（客戶端 filing）｜supports
  - 來源：https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm（Q1 FY27 10-Q（期末 2026-05-02，申報 2026-05-28，accession 0001835632-26-000019）Note 9 Commitments and Contingencies；MD&A Liquidity 段有同義句）
  - 逐字：Subsequent to quarter end, the Company entered into agreements to secure wafer and substrate manufacturing capacity through fiscal years 2030 and 2033, respectively. In connection with these agreements, the Company committed to pay deposits totaling $ 870.0 million, payable in quarterly installments from the second quarter of fiscal 2027 through the second quarter of fiscal 2028.
  - 圖裡已有？否（此 10-Q 不在 library/raw）
- **AT&S（身為買方）指出玻纖布（fiberglass mats）等關鍵材料目前供給吃緊**｜original_obtained｜tier 1（發行人公告；對上游層而言屬客戶端陳述）｜supports
  - 來源：https://ats.net/en/press/ats-expands-kulim-site-to-support-long-term-customer-demand-and-deepen-strategic-technology-partnerships/（AT&S Press 2026-06-15 "Increased outlook" 段末）
  - 逐字：The forecast assumes no significant deterioration of the geopolitical situation or in the currently tight supply of key materials such as fiberglass mats.
  - 圖裡已有？否
- **ABF 膜由 Ajinomoto 控制約 95% 高階供給，產線滿載（載板擴產的上游牆）**｜isolated_tier_3｜tier 3（TechTimes 轉述 wing.vc／edaily）｜neutral
  - 來源：https://www.techtimes.com/articles/328150/20260928/samsung-electro-mechanics-commits-5-billion-ai-chip-substrates-record-bet-hits-upstream-wall.htm（）
  - 逐字：
  - 圖裡已有？否
- **題材外：AMD 以 $8.2B 收購 World Labs；NVDA 授權 $150B 回購；OpenAI 延後 Astra-6.1、NVDA 推 AI safety 平台**｜lead_only_tier_4｜tier 4｜neutral
  - 來源：https://x.com/aleabitoreddit/status/2104698369591706069（）
  - 逐字：
  - 圖裡已有？否

</details>

### lead_f169462653573e002ee5aa0f194466d0

**追源者的判斷：** 這次有界重查的觸發事件（lead_a6a0，TPEx 注意交易資訊）只含財務，本身沒有讓 trace_next_trigger 成立。但依 trigger 走 MOPS 法說清單時，找到先前 park（2026-08-29）時沒看過的 2026-08-28 法說簡報（MOPS 497920260828M001.pdf；中英文檔 byte 相同）。它是 tier-1 一手，含三項真正的圖增量：①華星光進入 tech:eml 供給層，EML 流程具名誼虹（Optoway）EPI→華星光 EML 晶片→誼虹 EML laser，2H26 初始出貨；目前 tech:eml 供給側只有 Coherent／Lumentum。②新節點 co:optoway（非上市關係人：持股 10.63%、董事長同一人，年報一手）。③CW／EML 晶片的「Foundry service」經營型態，這是現有 co:luxnet→tech:cw_dfb_laser 邊的新 assertion。另有 ELS、NPO 兩條可選的低信心邊。全部是 issuer 自報，誼虹是關係人，不構成獨立 origin（L8），所以信心封頂、不給 sole_source、不上修 sub。產能與財務數字另交 Engine C。聯亞→華星光一條仍追不到一手（isolated_tier_3），而且兩份年報的機械算術已排除「聯亞是華星光主要進貨供應商」，只剩 consignment 形狀待證；輝達包產能一條被原文反駁（contradicts）。

**否定結果：** ①原 trace_next_trigger 指定的 2025-12-22 簡報（497920251222E001.pdf）逐頁（文字層＋全部圖片）核過：沒有 CW 字樣、沒有產能數字、沒有具名客戶、沒有聯亞。這是對那份文件的否定判定，答案在 2026-08-28 新簡報。②兩份簡報都沒有具名終端客戶。EML 流程的終端只寫「A global leader in high-speed optical interconnect solutions」，依 L6 不得對應。年報代號客戶 LC01082 標「與發行人關係：無」，而誼虹是 10.63% 大股東兼同一董事長，所以 LC01082 大概不是誼虹（這是判讀，不入圖）。③「輝達包產能」原文（工商時報 2025-12-21）指的是 NVIDIA 包下「其EML雷射晶片供應商」的產能，華星光只被稱作「CW晶片代工廠」→ contradicts，不得寫成華星光是輝達供應商。④聯亞→華星光：沒有任何一手互相具名。算術上，華星光 113 年向 LV221309 進貨 1,720,502 仟元，大於聯亞 113 年全年銷貨淨額 1,208,422 仟元，所以主要供應商不可能是聯亞，114 年聯亞若有供貨也 <10%。只有「客戶向聯亞買磊晶、交華星光代工」的 consignment 形狀未被排除，也未被證實。⑤觸發事件 lead_a6a0 本身不是結構事件。⑥存取障礙：wantrich.chinatimes.com 回 403、twincn.com 回 0 bytes，都已停止、沒有繞過。⑦2026-08-28 法說影音（irconference.twse.com.tw/4979_12_20260828_ch.mp4，約 291MB 中文）沒有轉錄：本機只快取 small.en 模型，轉錄腳本預設寫 library/private，超出唯讀邊界。所以 Q&A 內容（如「16 個波長」「三家 CSP」「ZR 獨家代工」）屬「我找不到」，不是「不存在」。

**graph delta 草案：**

【新文件】doc_id 建議：mops_4979_investor_conference_20260828｜source_type ir_deck｜evidence_tier 1｜origin_entity：LuxNet Corporation（華星光通）｜origin_event：2026-08-28 中信證券線上法人說明會｜url：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（E001 為同一檔）｜published_at：2026-08-28。依據是 MOPS t100sb07_1 清單「召開法人說明會日期：115/08/28」與檔名；若主執行者要求「上傳時間」級依據，這裡應標 published_at_method=event_date，並列入 PIT 報告。｜storage_permission：repo_excerpt。
入圖前先確認 SourceDoc URL 去重（此 URL 目前不在任何 extraction）。

【sources】
- s1｜p.4 文字層｜"LD & PD/APD .OSA, Optical Engine, ELS, CoC.Transceiver.OEM /ODM & JDM / Foundry Business主要產品及服務"
- s2｜p.24 標題與圖內｜"High-value CW/EML Chip Foundry service" / "Scaling chip production capacity with technology advancement"
- s3｜p.25 圖內｜"EPI wafers" "OPTOWAY TECHNOLOGY INC." "(10.6% shareholder of LuxNet)" "R&D team from SOURCE PHOTONICS" "EML chips" "LuxNet processes EPI wafers into EML chips and optical modules" "EML laser" "A global leader in high-speed optical interconnect solutions" "Initial shipments expected from 2H26, with meaningful volume ramp anticipated in 2027"
- s4｜p.26、p.29 文字層｜"模組與封裝Roadmap … 1.6TNPO3.2TNPO 6.4TNPO32T CPO"；"•NPO optical module"
- 既有文件 mops_4979_annual_report_2025 補兩個 source：
  - _s6｜p.68 主要股東名單（115/3/31）｜"誼虹科技股份有限公司 15,130,000 10.63%"
  - _s7｜p.25 董事利益迴避｜"本公司簡惠敏董事長與誼虹科技股份有限公司之董事長為同一人"

【新節點】co:optoway｜Company｜name "Optoway Technology Inc."｜aliases ["誼虹科技股份有限公司","誼虹科技","OPTOWAY"]｜abstraction_level device_chip｜source_ids [s3, 年報_s6]｜confidence 0.85。
⚠ 必須先補 config/company_identity.json：非上市，ticker 明確 null（L9）。目前只有搜尋摘要稱「未公開發行」，twincn 被擋，需主執行者在 registry 步驟另行核實。
Source Photonics 只以「R&D team from」出現，是人員來源，不是供應關係，不建節點、不建邊。

【新邊】全部 self_reported，L8 封頂，不給 sole_source：
- E1：co:luxnet develops tech:eml｜conf 0.7｜source [s3]｜理由：原文是現在式的加工流程，但出貨要 2H26 才開始。等出貨被一手確認後，另開 supplies_to（qualification_status 由彼時證據定），現在不預先寫。
- E2：co:optoway supplies_to co:luxnet｜conf 0.6｜source [s3]｜attributes：qualification_status null｜註：依流程圖的欄位與箭頭，Optoway 名稱逐字出現在「EPI wafers」欄；是關係人 captive 供應。
- E3：co:optoway invests_in co:luxnet｜conf 0.9｜source [年報_s6, 年報_s7, s3]｜持股％不進 attribute（時變，L4），只寫進 claim 並帶 as_of 115/3/31。
- E4（可選、低信心）：co:luxnet develops tech:external_laser_source｜conf 0.5｜source [s1]｜依據："ELS" 是 tech:external_laser_source 既有 alias 的機械命中；只是產品清單列名，沒有出貨或合格證據。
- E5（可選）：co:luxnet develops tech:npo｜conf 0.6｜source [s4]
- 既有邊 co:luxnet supplies_to tech:cw_dfb_laser：新增 EdgeAssertion，source [s2]。不改 substitutability（維持 2），不寫 qualification_status。「代工」型態放 claim；schema 沒有對應屬性，不要硬塞 attribute。

【claims】各附 disproof_condition 三件套：
- cl1（subject co:luxnet）：華星光 CW／EML 晶片以「Foundry service」形式提供（設計方／客戶未具名）。晶圓 2025 3K→2026WE 6K、晶粒 14mm→30mm 是 issuer 前瞻估計，放 dated claim；時變數字的正式紀錄歸 Engine C。
  disproof：①條件：後續法說／年報改稱自有品牌 CW 晶片，或揭露代工客戶終止；②核查頻率：每季（法說簡報）＋每年（年報約 5 月）；③觸發後 48 小時：重跑 query.structure co:luxnet 與 tech:cw_dfb_laser，更新本 claim 與讀圖 tech_cw_dfb_laser。
- cl2（subject co:luxnet）：EML 新產線是誼虹（10.63% 大股東、董事長同一人）EPI → 華星光 EML 晶片 → 誼虹 EML laser 的關係人流程，研發團隊來自 Source Photonics，2H26 初始出貨、2027 放量（issuer 自報）。
  disproof：①條件：2026 年報或 2027Q1 前的法說／月營收說明沒有 EML 出貨，或計畫延後／取消；②核查頻率：每季；③觸發後 48 小時：E1 維持 develops 或降 conf，並在讀圖 tech:eml 註記 pre-ramp 未兌現。
- cl3（subject co:luxnet；可選，作為研究紀錄）：兩份年報的算術排除聯亞是華星光 ≥10% 進貨供應商；只剩 consignment 形狀未證。
  disproof：①條件：任一方 tier-1 具名對方；②核查頻率：每年兩家年報；③觸發後 48 小時：依鐵律 7 建正確的多跳形狀。

【不入圖】產能、無塵室面積、資產負債與損益、股本 1,408→1,428 百萬元、員工 600→700、Yole／LightCounting／SemiAnalysis 市場預測，全部歸 Engine C 或脈絡（L4）。

**建議的等待（未登記）：** W1（確認事件）｜條件：華星光在月營收說明、2026Q4／2027 法說或 2026 年報（約 2027-05）中揭露 EML 晶片已開始出貨，或延後／取消｜到期：2027-06-30（到期重問，不丟）｜叫醒：E1（co:luxnet develops tech:eml）升級 supplies_to 或降 conf 的 RA 複查，以及 cl2 的 disproof 檢查｜entities：4979.TWO、co:luxnet、co:optoway（待入 registry）。
W2（反證／確認事件）｜條件：聯亞或華星光任一方 tier-1 文件（年報、法說逐字、重訊）或第三方客戶 filing 具名對方為 CW 磊晶／後段代工夥伴｜到期：2027-06-30（兩家 2026 年報刊印後）｜叫醒：本 lead 的聯亞→華星光 consignment 假設（若主執行者先照 source-trace 建 engine_b 假設，就掛在該假設上）｜entities：3081.TWO、co:landmark_optoelectronics、4979.TWO、co:luxnet。
不另登記影音轉錄：它不是外部事件，而是「是否啟動」的研究動作，應留在 user_decision 或互動 session 的研究清單。

**要存進 library/raw 的原文：**
- https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf：2026-08-28 華星光法說簡報（tier-1，MOPS），是 E1–E5、cl1–cl2 的唯一一手來源，含 p.24 CW/EML Chip Foundry、p.25 Optoway EML 流程、p.17 InP roadmap、p.15 產能。E001.pdf 與它 byte 相同，只存一份。p.17/p.24/p.25 的關鍵文字在圖片內，保存時需附頁碼 locator（文字層抽不到）。
- https://www.ctee.com.tw/news/20251221700017-430502：可選，只存 repo_excerpt 引文：作為「輝達包產能」contradicts 的反證紀錄（原文是包 EML 雷射晶片供應商的產能，華星光只被稱為 CW晶片代工廠）。tier 3，不支持任何新邊。

<details><summary>逐條 atom</summary>

- **（原 trace_next_trigger 指定文件）2025-12-22 法說簡報的產品線：主要產品及服務列出 LD、PD/APD、OSA、Optical Engine、ELS、CoC、Transceiver、OEM/ODM & JDM／Foundry。19 頁文字層，以及 p.4/7/8/13/15/17 的圖片都逐張看過：沒有「CW」字樣、沒有產能數字（只有無塵室面積）、沒有具名客戶，也沒有聯亞。**｜original_obtained｜tier 1｜對 BigGo 所稱「下游雷射元件」是支持。對 trace_next_trigger 要求的「CW 產品線／產能數字／具名客戶」三項，本文件是否定結果：這份文件裡沒有（這是對這份文件的判定，不是說它們不存在）。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920251222E001.pdf（p.4「公司簡介」文字層；p.13 無塵室頁同列「OSA , Optical Engine,ELS, CoC」）
  - 逐字：LD & PD/APD .OSA, Optical Engine, ELS, CoC.Transceiver.OEM /ODM & JDM / Foundry Business主要產品及服務
  - 圖裡已有？部分已在圖：年報 cl3 已涵蓋模組、晶粒與 CoC。ELS 沒有任何 co:luxnet 的邊（tech:external_laser_source 的 aliases 含 "ELS"）。
- **2026-08-28 法說簡報（MOPS；中信證券線上法說）把 CW／EML 晶片業務定位為「代工服務」，並不是自有品牌晶片。**｜original_obtained｜tier 1（issuer 自報，L8 self_reported）｜支持，且與工商時報 tier-3「CW晶片代工廠華星光」一致。它也與年報「自 2019 年即與策略合作夥伴共同開發 CW DFB Laser 晶粒」相容：設計方與客戶都未具名。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.24 標題（文字層））
  - 逐字：High-value CW/EML Chip Foundry service
  - 圖裡已有？邊 co:luxnet supplies_to tech:cw_dfb_laser 已在圖（sub=2，3 份文件：年報、cw_dfb addendum、borecraft），但圖裡沒有記錄「代工」這個經營型態。
- **EML 新產線的供應流程：誼虹（Optoway）供 EPI wafers，華星光把它加工成 EML 晶片與模組，交回誼虹做成 EML laser，最終交給一家未具名的「高速光互連全球領導者」。研發團隊來自 Source Photonics。預計 2H26 開始出貨，2027 放量。**｜original_obtained｜tier 1（issuer 自報；誼虹與華星光的董事長是同一人，互為關係人，不構成獨立交叉方，見 L8）｜新增。年報 cl2/cl3 只寫了「與策略合作夥伴共同開發 200G EML 光源」，沒有具名；本頁把 EPI 來源與流程具名。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.25「EML Chip in the process」，文字在圖片內（非文字層），四欄流程圖加兩個底框）
  - 逐字：EPI wafers ｜ OPTOWAY TECHNOLOGY INC. (10.6% shareholder of LuxNet) ｜ R&D team from SOURCE PHOTONICS ｜ EML chips ｜ LuxNet processes EPI wafers into EML chips and optical modules ｜ EML laser ｜ OPTOWAY ｜ A global leader in high-speed optical interconnect solutions ｜ Potential to become one of few APAC suppliers of high-speed EML chips ｜ Initial shipments expected from 2H26, with meaningful volume ramp anticipated in 2027
  - 圖裡已有？不在圖。tech:eml 供給側目前只有 co:coherent、co:lumentum 兩條（query.structure tech:eml），co:luxnet 對 tech:eml 沒有任何邊。Optoway 不在 registry、也不在任何 extraction。
- **誼虹科技是華星光持股 10.63% 的最大股東，華星光董事長簡惠敏同時是誼虹董事長。114 年董事會有關係人提供技術服務案與關係人合約案。**｜original_obtained｜tier 1｜支持 A3 的關係人性質。誼虹對華星光的任何陳述都不能算獨立 origin（L8）。
  - 來源：https://mopsov.twse.com.tw/nas/STR/2025_4979_annual_report.pdf（library/raw/mops_4979_annual_report_2025.txt；MOPS 檔名 2025_4979_20260527F04.pdf）（年報 p.68（二）主要股東名單；p.25 董事對利害關係議案迴避之執行情形（raw txt 約第 1412–1428、3540 行））
  - 逐字：誼虹科技股份有限公司 15,130,000 10.63%（主要股東名單，日期：115 年 3 月 31 日）；「本公司簡惠敏董事長與誼虹科技股份有限公司之董事長為同一人」（114/3/13 關係人合約案）
  - 圖裡已有？文件已入圖（doc mops_4979_annual_report_2025），但這兩段沒有抽取，也沒有 Optoway 節點。
- **晶片產能計畫：晶圓 2025 年 3K 片 → 2026WE 6K 片；晶粒 2025 年 14mm → 2026E 30mm；無塵室總面積 24/E 4,000、25/E 6,550、26/E 8,150、27/E 13,650 m²；第四廠八德 5,500 m²（2027~）。**｜original_obtained｜tier 1（issuer 自報、前瞻估計）｜支持原 lead tier-3 的「2026 產能倍增」（晶圓 3K→6K）。「mm」照原文記錄，解讀為 million 屬判讀（未宣告，一律當 judgment）。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.24 圖片（Chip Maintenance 框）；p.15 Manufacturing Space 文字層）
  - 逐字：Chip Maintenance ｜ 3K wafers 2025 ｜ 6K wafers 2026WE ｜ 14mm Chips 2025 ｜ 30mm Chips 2026E（p.24 圖內）；Total cleaning room space: 24/E 4,000 ; 25/E 6,550 ; 26/E 8,150 ; 27/E 13,650（p.15 文字層）；4thplant : 5,500 m2Bade (2027~)
  - 圖裡已有？不適用。這些是時變數字，永不入圖（L4），屬 Engine C 觀測。
- **InP 晶圓 roadmap：CW 從 20/40/70/100mW（2"、3"）走向 CW 400mW（DFB+SOA，4"）與 CW >400mW（6"，約 2028–2030）；2026E 推進 4 吋製程。**｜original_obtained｜tier 1（issuer 自報）｜新資訊（前瞻）。現行量產仍在 2"/3"。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.17（四張圖片條）；p.24 Tech Roadmap 框）
  - 逐字：CW 400mW (DFB+SOA)｜EML 400G｜CW 400mW｜CW >400mW｜CW 70/100mW｜EML 100G/200G（p.17 InP Wafer Roadmap 圖內）；Advance 4-inch wafer process in 2026E（p.24 圖內）
  - 圖裡已有？不在圖；只是 roadmap，不建邊。
- **原 lead 的 tier-3 說法「輝達包產能」（被讀成包華星光的產能）**｜contradicts｜tier 3（工商時報／今周刊，劉煥彥，2025-12-21，轉述 TrendForce）｜反駁。原文包產能的對象是「EML雷射晶片供應商」，華星光在文中只被稱為「CW晶片代工廠」。兩份華星光法說簡報都沒有把 NVIDIA 列為客戶（NVIDIA 只以市場背景出現）。
  - 來源：https://www.ctee.com.tw/news/20251221700017-430502（curl 取得的本文段落（「CW雷射成為雲端大廠的新寵兒」小節之前）與文末 TrendForce 段）
  - 逐字：輝達為了確保供貨無虞，包下了其EML雷射晶片供應商的產能，導致市面上EML雷射晶片供給吃緊。｜根據TrendForce分析，吃到這波光通訊雷射商機的台廠，有CW磊晶供應商聯亞、CW晶片代工廠華星光及光環、PD供應商環宇，以及PD磊晶代工廠全新。
  - 圖裡已有？否
- **聯亞做上游 InP CW 磊晶，華星光直接承接其 CW 後段代工（「關係明確」）**｜isolated_tier_3｜tier 3（TOPONE Markets，券商行銷內容，2026-09-02）｜未驗證。該文沒有引用任何一手。華星光年報與兩份法說簡報都 0 提及聯亞，聯亞年報與 CW 長約重訊也 0 提及華星光（本機 grep）。
  - 來源：https://www.top1markets.com/tw/news/landmark-3081-cpo-cw-laser-valuation-2027（文中「供應鏈環節」表與 FAQ「聯亞和華星光、全新有什麼不同？」）
  - 逐字：聯亞做上游 InP CW Laser 磊晶，華星光（4979）負責其後段代工，兩者關係直接｜後段代工 華星光 4979 承接聯亞 CW Laser 後段，出貨年增約 4 倍 強（關係明確）
  - 圖裡已有？否（圖裡沒有 co:landmark_optoelectronics 與 co:luxnet 之間的邊）
- **機械交叉核對：聯亞不可能是華星光的主要進貨供應商 LV221309，也不是華星光任一年度 ≥10% 的供應商。**｜original_obtained｜tier 1（兩份法定年報；推論是算術，不是任何一方的陳述）｜反駁「聯亞是華星光主要上游」這種讀法。華星光 113 年向 LV221309 進貨 1,720,502 仟元，大於聯亞 113 年全年銷貨淨額 1,208,422 仟元，所以 LV221309≠聯亞。114 年華星光其餘供應商各 <10%（<296,393 仟元），聯亞若有供貨，也是非主要供應商。⚠ 不否證代工客供料（consignment）路徑：客戶向聯亞買磊晶片再交華星光加工，這筆不會出現在華星光的進貨帳。
  - 來源：library/raw/mops_4979_annual_report_2025.txt ＋ library/raw/mops_3081_annual_report_2025.txt（兩份 MOPS 年報）（華星光年報 營運概況—主要進貨供應商（約 p.94 附近）；聯亞年報 p.82 前「最近二年度主要銷貨客戶資料」）
  - 逐字：華星光：「LV22 1309 1,720,502 74.20 無 LV221309 2,182,255 73.63 無 ... 進貨淨額 2,318,643 100.00 進貨淨額 2,963,928 100.00」；聯亞：「1 C06 公司(註) 401,820 33.25 無 C06 公司(註) 567,378 25.76 無 ... 銷貨淨額 1,208,422 100.00  銷貨淨額 2,202,822 100.00」
  - 圖裡已有？華星光那段已入圖（s5／cl4），聯亞銷貨表已在 raw，但兩者沒有被交叉比對過。
- **聯亞自述：透過多家外包夥伴的策略合作，提供從磊晶到後段加工的全製程服務（外包夥伴未具名）。**｜original_obtained｜tier 1｜與「聯亞磊晶＋他廠後段代工」的結構相容，但沒有具名，依 L6 不得對應到華星光。
  - 來源：library/raw/mops_3081_annual_report_2025.txt（聯亞 114 年度年報，MOPS）（聯亞年報「致股東報告書—深化製程整合，提升生產韌性」（raw txt 約第 163–166 行））
  - 逐字：亦透過與多家外包夥伴之策略合作，提供由磊晶至後段加工之全製程服務，提升供應彈性與交付穩定性，以回應客戶多元製程需求。
  - 圖裡已有？否（extractions 中無「外包夥伴」）
- **觸發本次重查的 lead_a6a0（TPEx 注意交易資訊，2026-09-23）：8 月營收 546 百萬，YoY +37.19%；115Q2 營收 1,289 百萬，EPS 1.29 元。**｜original_obtained｜tier 1｜Q2 數字與法說簡報 p.6 一致。這個事件只含財務，本身沒有讓 trace_next_trigger（CW 產品線／產能／具名客戶／聯亞）成立；這次重查有收穫，是因為順勢找到了 2026-08-28 新簡報。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.6 交叉核對；TPEx openapi 原 URL 本次未重抓）（lead_a6a0 raw_text；簡報 p.6）
  - 逐字：營業收入1,087 1,193 1,289 ... 基本每股盈餘(元) 0.67      1.62 1.29（p.6 損益表 2025Q2／2026Q1／2026Q2）
  - 圖裡已有？不適用（財務屬 Engine C）
- **華星光有 NPO 模組 roadmap（1.6T/3.2T/6.4T NPO → 32T CPO），並展示 NPO optical module 組裝流程；管理層引 SemiAnalysis 認為 2027–2029 NPO 會取代 CPO 成為主要出貨。**｜original_obtained｜tier 1（roadmap 為 issuer 自報）；p.12 市場觀點為第三方轉述｜新增（roadmap）。p.12 是 issuer 轉述第三方的市場觀點，不入圖。
  - 來源：https://mopsov.twse.com.tw/nas/STR/497920260828M001.pdf（p.26、p.29 文字層；p.12 文字層）
  - 逐字：模組與封裝Roadmap ... 1.6TNPO3.2TNPO 6.4TNPO32T CPO（p.26）｜•NPO optical module（p.29）｜Y2027~Y2029 NPO取代CPO為主要出貨，最大的原因是CPO 的良率還不夠好，且幾乎無維修性（p.12，Source: SemiAnalysis AI Networking Model (2026)）
  - 圖裡已有？tech:npo 已在圖，co:luxnet 對它沒有邊。
- **第三方部落格對 2026-08-28 法說的轉述：CW 已做到 16 個波長；晶圓年產能「2026 年約 3,000 片、2027 年約 6,000 片」。**｜isolated_tier_3｜tier 3（same_origin：轉述同一場法說，不是新 origin）｜「16 個波長」不在簡報文字層與圖片裡（可能出自 Q&A），未驗證。晶圓年度與簡報 p.24（3K＝2025、6K＝2026WE）相牴觸，以一手為準。
  - 來源：https://www.simpletechtrend.com/post/luxnet-4979-2026-q2-earnings-inp-cw-npo（文章 2026-08-29）
  - 逐字：公司的 CW 目前已經做到 16 個波長，而市場大多只做單波或 4 波｜年產能 2026 年約 3,000 片、2027 年約 6,000 片（WebFetch 模型摘錄，未以 curl 逐字核對）
  - 圖裡已有？否

</details>

### lead_13daec452dbebc11be549f54c5a4626e

**追源者的判斷：** 一手正本已取得（US Conec 官網聯名新聞稿 PDF；Fujikura 官網日文版是共同發布方自己的版本），另外追到 5 份 US Conec 聯名的 MMC／TMT 授權新聞稿（2021–2026），以及 NVIDIA 官網把 MMC 列為自家 CPO 交換器 switch connector 的客戶端一手。對圖的增量是一個新層加上它的供給結構：MMC VSFF 連接器／TMT ferrule 由 US Conec 設計，至少 6 家具名廠商經授權或專利和解可以生產；透過 NVIDIA 的客戶端 quote，這一層掛得上既有的 tech:scale_out_cpo。現在圖裡 CPO 連接器層（tech:cpo_fiber_attach）的供給側只有 co:coherent 一條邊，sub／sole 都沒填，沒有任何 MMC／ferrule 節點。這個增量讓讀圖的人看得到：這一層在生產端是多源，設計 IP 集中在一家非上市 JV，而不是一層很薄的供應商。另外，本次一手 About 段直接反駁了母線索 lead_55bd36e6 的「US Conec 無上市母體」，由主執行者補寫該 lead 的 outcome（pq1 層級）。入圖屬於 ra_admission，要 pq2 核准；registry 需先補 co:us_conec（null）、co:fujikura 等條目（INV-1，這是 ID 必須走 registry、不能憑名稱猜的規則）。

**否定結果：** ①triage 假設的「圖中某連接器／ferrule 層記成 sole_source、本稿是反證」不成立。全 extractions 找不到任何 "sole_source": true；tech:cpo_fiber_attach 與 tech:fiber_attach_unit 都沒有 sole／sub 值。所以本稿不是反證，而是新層的供給結構證據。②本稿不是 MMC 層第一次多源：Fujikura 2021、Sumitomo Electric Lightwave 2023、Senko 2024（和解）、Sanwa 2025／2026、Hakusan 2026-02 都在它之前。2026-03-11 這份只是把擴束版 PRIZM TMT 納入既有的多源化。③PRIZM TMT（擴束版）本身沒有任何一手連到 CPO 或具名客戶；NVIDIA 頁只寫 MMC，沒寫 PRIZM／expanded beam。所以不得建 PRIZM TMT → CPO 的邊（L6：型號與公司名必須逐字出現在 quote 裡）。④「enabled to produce」與「will provide」只代表授權／能力，不代表已在具名客戶 qualified 或出貨。客戶端具名的 MMC 供應商找不到，不設 sole_source，也不設 substitutability 數值。⑤沒有浮現邊緣小型的上市純標的：US Conec 是非上市 JV（Corning／Fujikura／NTT-AT），Hakusan 67% 由古河電工持有，SENKO 非上市，Sanwa Technologies 的上市狀態未查證；上市母體 Corning、Fujikura、Sumitomo Electric、Furukawa Electric、NTT 都是大型綜合企業，這一層的純度極低。⑥MMC 是交換器前面板的 switch-side 連接器，與 TSMC 論壇「光纖連接器」被對映成的 tech:fiber_attach_unit（FAU）不是同一個元件。不得合併，也不得拿本證據去下修 tech:cpo constrained_by tech:fiber_attach_unit（L12：一個表示不能承載兩種語意）。

**graph delta 草案：**

【前置：registry（INV-1／L9）】config/company_identity.json 需新增：co:us_conec（research_ticker null，非上市 JV）、co:fujikura（5803.T，JPY）；選配：co:sanwa_technologies（上市狀態未查證，先填 null 並註明）、co:hakusan（null）、co:furukawa_electric（5801.T）、co:ntt_at（null，母體 NTT）。SEL 要對映到 co:sumitomo_electric，還是另建子公司節點，由主執行者決定（一手：「Sumitomo Electric Lightwave (SEL), a subsidiary of Sumitomo Electric Industries, Ltd.」，2026-03-11 PDF p.3）。

【節點】
N1 tech:mmc_connector（TechNode，module_subsystem；aliases 只收 quote 裡有的："MMC", "MMC-12/APC", "MMC16"）
  — quote：「The PRIZM® TMT ferrule delivers next-generation expanded beam technology in the prevalent TMT format, enabling use in the widely adopted MMC connectivity platform.」｜usconec 2026-03-11 PDF p.1｜origin US Conec｜tier 1
N2 tech:tmt_ferrule（TechNode，device_chip；alias "TMT"）
  — quote：「The MMC, a multi-fiber connector employing a reduced-size 1x16-fiber MT-style ferrule (TMT), improves MPO port density by a factor of three」｜Fujikura 2021-09-29 PDF p.1｜origin US Conec／Fujikura｜tier 1
N3 tech:prizm_tmt_ferrule（TechNode，device_chip；alias "PRIZM® TMT"）
  — 同 N1 quote。
N4 co:us_conec（Company；research_ticker null）
  — quote：「US Conec is headquartered in Hickory, North Carolina, and is an equity venture of three leading communications technology companies—Corning Optical Communications, Fujikura, and NTT-AT.」｜2026-03-11 PDF p.2｜tier 1
N5 co:fujikura（Company，5803.T）— 同 atom 1 quote。

【邊】（每條都附 source_ids；confidence 只在不同 origin_event 之間累加）
E1 tech:mmc_connector is_component_of tech:scale_out_cpo
  — quote：「The CPO switch uses MMC-12/APC fiber connections only.」＋ 表格「MPO12/MMC16」／「Q3450-LD, SN6800, SN6810」｜https://www.nvidia.com/en-us/networking/interconnect/ ｜origin NVIDIA（客戶端）｜tier 1（或 2）｜published_at null
  — 輔證（不同 origin_entity、供應商端，弱）：2026-02-17 US Conec／Sanwa／Hakusan PDF p.1「…employing co-packaged and embedded optics are taking advantage of the higher densities of the MMC connector platform both internal to the equipment and as the optical I/O.」
  — ⚠ 不要把 MMC 併入 tech:fiber_attach_unit 或 tech:cpo_fiber_attach：NVIDIA blog 的角色句雖含「data output to the front panel」，是否等同 MMC 由主執行者判斷；保守做法是 E1 直掛 tech:scale_out_cpo。
E2 tech:tmt_ferrule is_component_of tech:mmc_connector — 同 N2 quote（2021）。
E3 tech:prizm_tmt_ferrule is_variant_of tech:tmt_ferrule — 同 N1 quote（2026-03-11）。
E4 co:us_conec develops tech:mmc_connector — quote：「US Conec's MMC connector combines a novel, reduced footprint multi-fiber ferrule with a very small Form factor (VSFF) connector footprint which is 1/3 the size of the MPO format.」｜2023-03-08 PDF p.1｜tier 1
E5 co:us_conec develops tech:prizm_tmt_ferrule — quote：「…each enabled to produce the US Conec designed ferrule and associated MMC connector components…」｜2026-03-11 PDF p.1
E6 co:us_conec licenses_to co:fujikura — 兩個 origin_event：①2021「Fujikura and US Conec have reached an agreement for licensing and collaboration that enables both companies to manufacture intermateable multi-fiber and duplex VSFF (Very Small Form Factor) connectors.」②2026-03-11 atom 1 quote＋Fujikura 日文版「US Conecと同様の合意を個別にしており」
E7 co:us_conec licenses_to co:sumitomo_electric（經由 SEL）— ①2023「…a definitive license agreement enabling Sumitomo Electric Lightwave, Corp. to manufacture MMC connector and TMT ferrule components…」②2026-03-11 atom 1 quote
E8 co:us_conec licenses_to co:corning — 2026-03-11 atom 1 quote（單一 origin_event；原文用詞是「separate agreements」／「enabled to produce」，沒有「license」字樣，寫入時照實註記）
E9（選配）co:us_conec licenses_to co:sanwa_technologies — 2025「…a definitive license agreement enabling SANWA Technologies to produce and supply … MMC VSFF multi-fiber adapters.」＋ 2026-02「…offering the industry acclaimed MMC multi-fiber connector embodiment.」
E10（選配）co:hakusan supplies_to tech:tmt_ferrule — 2026-02「Hakusan Inc. will … manufacture and supply the TMT ferrule in both x12 and x16 fiber variants.」
E11 co:corning invests_in co:us_conec；co:fujikura invests_in co:us_conec（選配 co:ntt_at）— N4 quote＋Fujikura 日文版「Corning Incorporated、株式会社フジクラ、NTTアドバンステクノロジ株式会社の3社による合弁会社です。」（兩個 origin_entity 都是當事人）
E12（選配）co:furukawa_electric acquired co:hakusan — 古河 2024-11-07「2025年1月30日付で白山の株式を約67%取得します。」
SENKO 的 2024 和解：寫成 claim，不要寫成 licenses_to（原文是 settlement，其餘條款 confidential）。

【Claim（附 disproof 三件套）】
CL1 subject tech:mmc_connector：「MMC／TMT 連接器層在生產端是授權多源：US Conec 設計；Fujikura（2021）、Sumitomo Electric Lightwave（2023）、Senko（2024 和解）、Sanwa（2025／2026）、Hakusan（2026，TMT ferrule）、Corning／Fujikura／SEL（2026，PRIZM TMT）都已取得授權或和解，可以生產或提供。NVIDIA CPO 交換器（Q3450-LD、SN6800、SN6810）的 switch connector 列為 MPO12/MMC16。設計 IP 集中在 US Conec（非上市 JV）；『可生產』不等於已在具名客戶 qualified。所有多源陳述都是 US Conec 與被授權方共同發布（對 US Conec 而言是不利於 sole_source 的自認），沒有客戶端具名的 MMC 供應商。」
  disproof_condition：條件＝客戶端文件（NVIDIA／hyperscaler）具名 MMC／TMT 的 qualified 供應商只有一家（或只有 US Conec 自產），或任一授權被終止、專利訴訟重啟；核查頻率＝每季（OFC／ECOC、NVIDIA LinkX 頁面更新、被授權方法說）；觸發後 48 小時＝重跑 query.structure tech:mmc_connector，licenses_to 邊加註，並對相關 supplies_to 邊評估 sole_source／substitutability。
  confidence 建議：多源事實 0.85（多個獨立 origin_event，但都有 US Conec 共同發布）；MMC→CPO 連結 0.8（客戶端單一頁面，頁內 12／16 芯不一致）。

【不建議入圖】substitutability 數值與 sole_source（沒有 buyer-specific 的供應邊）；Hakusan 市佔排名、70% 插拔力等效能數字（L4：市佔屬時變觀測，效能是產品規格、不是瓶頸證據）；PRIZM TMT→CPO 任何邊（沒有一手）。

【追源紀錄】usconec.com PDF ×6（200）；usconec.com/resources/press-releases（200）；fujikura.co.jp 英日版（200，英文 About 段誤譯）；opticalcomponent.fujikura.com 2021 PDF（200）；blog.sumitomoelectriclightwave.com（200，same_origin）；nvidia.com/en-us/networking/interconnect/（200）；furukawaelectric.com 2024 release（200）；prnewswire.com 原 URL（curl 卡住後 exit 23 寫檔失敗；WebFetch 只拿到摘要，未取逐字，由 issuer PDF 取代）；corning.com MMC-PRIZM 頁（403，access_blocked，已停止）；barchart Corning OFC 2026 轉載（202 空回應，疑似 anti-bot，已停止）；本機 grep extractions／library／registry；query.structure tech:cpo_fiber_attach、co:corning、tech:scale_out_cpo；engine_b.cli related（0 筆）。routes_attempted：local_library、issuer_site、alternate_primary、authorized_syndication（失敗）；未走 sec_edgar（Corning 10-K 不太可能具名 US Conec，且 JV 股權已有兩個當事人一手）。

【附帶給主執行者（pq1 層級，非 authority）】lead_55bd36e6 的 refs.outcome「SENKO／US Conec…無上市母體」被 atom 3 反駁，建議 append 更正：四維初判對 US Conec 從「不適用」改為「可評、純度極低（GLW／5803.T／NTT）」。ew_0029_2026-08-31 的 query_hint 前提要一併修正。

**建議的等待（未登記）：** W1（fact_verification／entity_filing_signal；entities: co:nvidia, NVDA, co:us_conec, co:corning, co:fujikura, co:sumitomo_electric）：條件＝客戶端（NVIDIA LinkX 文件、交換器 user manual，或 hyperscaler）具名 CPO 交換器所用 MMC／TMT 的供應商，或 NVIDIA 頁內 MMC-12 vs MMC16、MPO vs MMC 的不一致被更正；到期 2027-03-31（涵蓋 OFC 2027）；叫醒本 lead 的 RA（若已入圖，就叫醒 tech:mmc_connector 的供給側讀圖）。到期時重問，不是丟棄。W2（entity_filing_signal；entities: co:corning, GLW, co:fujikura, 5803.T, co:sumitomo_electric, 5802.T）：條件＝被授權方在法說、決算資料或 filing 揭露 PRIZM TMT／MMC 已出貨、量產或具名客戶 qualification，讓證據從「enabled to produce」推進到已供貨；到期 2027-03-31；叫醒本 lead。另建議：修改既有 ew_0029_2026-08-31 的 query_hint，拿掉「US Conec 出現上市母體」（前提已被 atom 3 反駁），改為「SENKO 出現上市母體／被併購，或客戶端具名 CPO connector 供應商」。

**要存進 library/raw 的原文：**
- https://www.usconec.com/media/h4zopm3k/us-conec-corning-fujikura-and-sumitomo-electric-joint-press-release_3-11-2026_final.pdf：本 lead 的 issuer 正本（取代 PR Newswire same_origin 轉載）；含 PRIZM TMT 多源與 US Conec 股權 About 段
- https://www.fujikura.co.jp/news/pressrelease/20260311prizm_tmtmmcus_conec.html：共同發布方 Fujikura 日文版：個別協議與 JV 股權的當事人自述（英文版 About 段誤譯，不存英文版）
- https://www.nvidia.com/en-us/networking/interconnect/：唯一的客戶端 quote：CPO 交換器 switch connector MPO12/MMC16、Q3450 只用 MMC-12/APC；頁面無日期、內容會變，需要快照
- https://www.usconec.com/media/seffcyh3/usconec_sanwa_hakusan_mmc-joint-press-release_feb-17-2026.pdf：Hakusan TMT ferrule、Sanwa MMC 連接器授權；供應商端 MMC 用於 co-packaged optics 的陳述
- https://www.usconec.com/media/gjsgvpj0/us-conec_sumitomo-press-release-08_mar_2023.pdf：SEL 取得 MMC／TMT 授權、second source 原句（獨立 origin_event）
- https://www.opticalcomponent.fujikura.com/wp-content/uploads/2022/06/newsrelease20210929.pdf：2021 Fujikura 授權、TMT 定義、雙方開模可互接（獨立 origin_event；E2 的 quote 來源）
- https://www.usconec.com/media/cbihwbe3/us-conec-and-sanwa-joint-press-release_03-24-2025.pdf：Sanwa 授權（選配邊 E9）
- https://www.usconec.com/media/abhcy2tj/senko-and-us-conec-joint-press-release-9-3-2024.pdf：Senko 和解後可提供 MMC；同時與母線索 lead_55bd36e6 的 SENKO 研究相關
- https://www.furukawaelectric.com/release/2024/kei_20241107.html：古河電工取得白山 67%（選配邊 E12；Hakusan 的上市母體）

<details><summary>逐條 atom</summary>

- **US Conec 與 Corning、Fujikura、Sumitomo Electric Lightwave 分別簽約：三家都可生產 US Conec 設計的 PRIZM TMT 擴束 ferrule 與相關 MMC 連接器元件，並將提供 PRIZM TMT 纜線方案（2026-03-11）**｜original_obtained｜tier 1（issuer 聯名新聞稿；供應商端）｜支持線索標題；但不是 triage 設想的 sole_source 反證（圖中沒有 sole_source 可反駁）
  - 來源：https://www.usconec.com/media/h4zopm3k/us-conec-corning-fujikura-and-sumitomo-electric-joint-press-release_3-11-2026_final.pdf（NEWS RELEASE p.1 第一段（dateline: HICKORY, NC, March 11, 2026））
  - 逐字：Corning, Fujikura and Sumitomo Electric Lightwave are each enabled to produce the US Conec designed ferrule and associated MMC connector components and will provide PRIZM® TMT based cabling solutions.
  - 圖裡已有？否：extractions 裡沒有 US Conec／PRIZM／MMC／ferrule 字樣；query.structure tech:cpo_fiber_attach 供給側只有 co:coherent 一條，sub／sole 皆空
- **Fujikura 官網自家版本確認：它與 US Conec 達成協議，Corning、Sumitomo Electric Lightwave 也分別簽了同樣的協議**｜original_obtained｜tier 1（共同發布方自己的 newsroom）｜支持 atom 1（共同發布方自證）
  - 來源：https://www.fujikura.co.jp/news/pressrelease/20260311prizm_tmtmmcus_conec.html（プレスリリース本文第一段（2026年3月11日））
  - 逐字：フジクラの他、Corning Incorporated、Sumitomo Electric Lightwave CorporationについてもUS Conecと同様の合意を個別にしており、各社が今後、同技術の普及と標準化を図っていきます。
  - 圖裡已有？否
- **（母線索 lead_55bd36e6 refs.outcome 的結論）SENKO／US Conec 無上市母體**｜contradicts｜tier 1（US Conec 自述自身股權，且由上市股東 Fujikura 在自家 newsroom 再述）｜反駁母線索：US Conec 長期就有上市股東 Corning（GLW）、Fujikura（5803.T）、NTT-AT（NTT 集團）
  - 來源：https://www.usconec.com/media/h4zopm3k/us-conec-corning-fujikura-and-sumitomo-electric-joint-press-release_3-11-2026_final.pdf（p.2 About US Conec；同句也出現在 2023／2024／2025／2026-02 各份 US Conec 新聞稿；Fujikura 日文版 About 段：「Corning Incorporated、株式会社フジクラ、NTTアドバンステクノロジ株式会社の3社による合弁会社です。」）
  - 逐字：US Conec is headquartered in Hickory, North Carolina, and is an equity venture of three leading communications technology companies—Corning Optical Communications, Fujikura, and NTT-AT.
  - 圖裡已有？否（沒有 co:us_conec 節點，registry 也沒有條目）
- **MMC／TMT 早在 2021 年就已多源：Fujikura 與 US Conec 授權協議，兩家都可生產可互接的 MMC／MDC；TMT ferrule 兩家都已開模**｜original_obtained｜tier 1（issuer 聯名新聞稿）｜修正線索的新穎性：本稿不是 MMC 層第一次多源
  - 來源：https://www.opticalcomponent.fujikura.com/wp-content/uploads/2022/06/newsrelease20210929.pdf（September 29, 2021 聯名新聞稿 p.1 第二段；同頁：「The MMC, a multi-fiber connector employing a reduced-size 1x16-fiber MT-style ferrule (TMT), improves MPO port density by a factor of three」）
  - 逐字：The new TMT ferrule has now been tooled by both US Conec and Fujikura with full intermateability eliminating assurance of supply concerns.
  - 圖裡已有？否
- **2023-03-08 US Conec 授權 Sumitomo Electric Lightwave 生產 MMC 連接器與 TMT ferrule 元件，US Conec 稱其為 second source**｜original_obtained｜tier 1（issuer 聯名新聞稿）｜支持生產端多源
  - 來源：https://www.usconec.com/media/gjsgvpj0/us-conec_sumitomo-press-release-08_mar_2023.pdf（p.1 第一段；同頁 Joe Graham 引言：「Their long history as a premier MT ferrule maker makes Sumitomo Electric an excellent second source partner for TMT ferrules and MMC connector components.」）
  - 逐字：Sumitomo Electric Industries, Ltd. and US Conec Ltd. announce the execution of a definitive license agreement enabling Sumitomo Electric Lightwave, Corp. to manufacture MMC connector and TMT ferrule components for the deployment of next-generation, high-density, multi-fiber cabling solutions.
  - 圖裡已有？部分：co:sumitomo_electric 已在圖中（只有 supplies_to co:nvidia 的 ELS 邊），沒有連接器相關邊
- **2024-09-03 SENKO 與 US Conec 和解 VSFF 專利訴訟，SENKO 得以提供 MMC 連接器與轉接器**｜original_obtained｜tier 1（雙方聯名）｜支持生產端多源；也補足母線索 SENKO 的連接器角色
  - 來源：https://www.usconec.com/media/abhcy2tj/senko-and-us-conec-joint-press-release-9-3-2024.pdf（p.1 第一段（September 3, 2024））
  - 逐字：Also as part of their settlement, Senko will be able to offer MMC connector and adapter products, and US Conec will be able to offer SN connector and adapter products.
  - 圖裡已有？否（SENKO 只在 NVIDIA 生態系名單 quote 裡被提及，沒有節點）
- **2025-03-24 US Conec 授權 SANWA Technologies 生產 MDC 連接器、MDC 轉接器與 MMC 轉接器；2026-02-17 擴大到 MMC 多芯連接器本體**｜original_obtained｜tier 1｜支持生產端多源
  - 來源：https://www.usconec.com/media/cbihwbe3/us-conec-and-sanwa-joint-press-release_03-24-2025.pdf（2025 稿 p.1 第一段；2026-02-17 稿 p.1：「Sanwa Technologies will expand on their VSFF solutions of MDC duplex and MMC adapters by offering the industry acclaimed MMC multi-fiber connector embodiment.」）
  - 逐字：US Conec and SANWA Technologies announce the execution of a definitive license agreement enabling SANWA Technologies to produce and supply MDC VSFF (Very Small Form Factor) duplex optical connectors, MDC VSFF duplex adapters and MMC VSFF multi-fiber adapters.
  - 圖裡已有？否（registry 沒有 Sanwa；FOCI 年報 raw 有提到 Sanwa，但沒有抽取）
- **2026-02-17 Hakusan 將生產供應 TMT ferrule（x12／x16）；同稿稱 CPO 等新架構採用 MMC 平台，用於設備內部與 optical I/O**｜original_obtained｜tier 1（issuer 聯名新聞稿；CPO 用途是供應商端自述，沒有具名客戶）｜支持生產端多源；以供應商端（弱）把 MMC 連到 CPO
  - 來源：https://www.usconec.com/media/seffcyh3/usconec_sanwa_hakusan_mmc-joint-press-release_feb-17-2026.pdf（p.1 第一段；同頁第二段：「In addition, emerging networking and server cluster technologies employing co-packaged and embedded optics are taking advantage of the higher densities of the MMC connector platform both internal to the equipment and as the optical I/O.」）
  - 逐字：Hakusan Inc. will leverage their decades of expertise in low-loss MT technology to manufacture and supply the TMT ferrule in both x12 and x16 fiber variants.
  - 圖裡已有？否
- **NVIDIA 官網：CPO 交換器（Q3450-LD、SN6800、SN6810）的 switch connector 為 MPO12/MMC16；Q3450 CPO 交換器只用 MMC-12/APC 光纖連接**｜original_obtained｜tier 1（客戶／系統商端的直接產品揭露；若主執行者比照既有 NVIDIA blog 標 tier 2 也可）｜支持：MMC 是 NVIDIA CPO 交換器的 switch-side 連接器（客戶端）；同一欄並列 MPO12，代表連接器格式本身在 SKU 間可替代
  - 來源：https://www.nvidia.com/en-us/networking/interconnect/（FAQ「Can the Q3450 CPO switch support copper cables?」；Specifications 表 Switch Connector 列的 CPO 欄：「MPO12/MMC16」，Compatible Switches：「Q3450-LD, SN6800, SN6810」。⚠ 同頁 FAQ 另寫：「XDR and CPO deployments use the same MPO-12/APC single-mode crossover fiber cables as NDR/400G」——頁內 MMC-12 vs MMC16、MPO vs MMC 不一致，照實記錄，不擇一）
  - 逐字：The CPO switch uses MMC-12/APC fiber connections only.
  - 圖裡已有？否（extractions 沒有 MMC 字樣）
- **古河電工以股權轉讓取得白山（Hakusan）約 67%（2025-01-30 生效）；古河稱白山多芯 MT ferrule 全球市佔第 2**｜original_obtained｜tier 1（收購方 issuer 新聞稿）｜補充：新 TMT 被授權方 Hakusan 有上市母體 Furukawa Electric（5801.T）
  - 來源：https://www.furukawaelectric.com/release/2024/kei_20241107.html（ニュースリリース 2024年11月7日 本文；同頁：「白山は光通信に欠かせないコネクタ部品の一つである多心型光MTフェルールの世界シェアが第2位で」；會社概要表：「古河電工67%、米川達也13%　ほか」）
  - 逐字：2025年1月30日付で白山の株式を約67%取得します。
  - 圖裡已有？否（registry 與 extractions 都沒有 Furukawa／Hakusan）
- **FOCI（3363.TWO）2025 年報：光纖被動元件主要供應商為阿博隆、US Conec、Sanwa、Senko、寧波多普勒**｜original_obtained｜tier 1（客戶端法定揭露）｜旁證：客戶端的被動元件是多供應商
  - 來源：library/raw/mops_3363_annual_report_2025.txt（MOPS 年報；本機已存）（(三) 主要原料之供應狀況 表（raw 檔第 3489–3491 行））
  - 逐字：光纖被動元件 阿博隆、US Conec、Sanwa、Senko、寧波多普勒 良好、穩定
  - 圖裡已有？已在 library/raw，但未抽入圖（extractions 沒有 US Conec 字樣）

</details>

### lead_c34859d883443ae775b8095e5931e9c5

**追源者的判斷：** 已取得一手原文（GA-ASI 2024-07-19 首飛稿、2022-08-16 整合測試稿），也有圖增量：多一個 MQ-9B 推進第二來源（P&WC PT6 E-Series，qualifying），並讓現行 Honeywell TPE331-10 邊有 substitutability 依據。

**主執行者的問題：是否與 lead_628c 合併？答：合併成同一包，不單獨成包。** 理由有四：
① PT6 稿只寫「MQ-9B’s current engine」，依 L6 不能由它推出 Honeywell TPE331-10，現行端只有 628c 的 datasheet 逐字具名。所以 substitutability 這個 assertion 必須同時引用兩份文件才完整。
② 兩個 lead 同為 GA-ASI 的 origin_entity、同一個需求錨（tech:aerospace_defense_platform），節點集合重疊（co:ga_asi、prod:mq_9b_skyguardian、Honeywell 邊）。分開成包，本包的邊會懸空，或必須依賴另一包先核准。
③ 合併只占一個 ra_admission pq2 編號。
④ 若 628c 被 park 或 drop，本 lead 同步 park（見 park_fields 的備用值）。

信心與分級：只有單一 origin_entity，依 lead-intake Step 4 應低 confidence 並標 needs_review，不宜高信心。qualification_status 只能寫 qualifying。

**否定結果：** ① 推進層不是薄供應層，也沒有可投的邊緣小公司。兩條路徑都是巨型公司：Honeywell（HON）、Pratt & Whitney Canada（RTX 旗下，RTX 稿逐字寫「Pratt & Whitney is an RTX (NYSE: RTX) business.」）；整合方 GA-ASI 是私人公司。本 lead 不產生 onboard 候選。它的價值是把 decompose 地圖的推進層從 🔴 未知改成「已知、兩條路徑、非瓶頸」，避免下次重挖。
② triage 的「兩條已驗證路徑」言過其實。一手只支撐「整合完成＋2024-07-15 試飛 44 分鐘」，也就是 qualifying。首飛 26 個月內沒有任何客戶選用、合約或交付的一手紀錄：GA-ASI 2025–2026 新聞稿清單 PT6 命中 0；03/2026 datasheet 的 POWER PLANT 只列 TPE331-10；RTX FY2025 10-K 與 2025-10 PT6 E-Series 稿的平台清單沒有 MQ-9B。
③ triage 寫的「optional upgrade」不在 2024 稿裡，逐字來源是 2022 稿的「alternate option for future customers」。
④ triage 的 decision_impact=ranking 已過時。排序在 2026-09-22 退役，本 lead 只影響圖的結構，不影響任何排序。
⑤ GA-ASI 自研引擎（HFE 2.0、Achates IP）指向 Gray Eagle，不是 MQ-9B 的第三條路徑。

**graph delta 草案：**

【整包併入 lead_628c 的 ra_admission packet；以下只列本 lead 貢獻的部分。節點若 628c 已提，以 628c 為準、不重複建】

source docs（doc_id 由主執行者取；source_ids 用 <doc_id>_sN 格式）：
- D1 = GA-ASI 2024-07-19 首飛稿。source_type=press_release，evidence_tier=2，origin_entity=GA-ASI，origin_event=2024-07-15 MQ-9B PT6 首飛，published_at=2024-07-19（依據：dateline「SAN DIEGO – 19 July 2024」與頁尾「Jul 19, 2024」）。
- D2 = GA-ASI 2022-08-16 整合測試稿。evidence_tier=2，origin_entity=GA-ASI，origin_event=2022-07-29 地面全功率測試，published_at=2022-08-16（依據：dateline）。
- D3 = 628c 的 datasheet（共用；published_at 待定，檔名 032026 與頁內「0925／©2025」不一致，推不出就留 null 並列入報告，L11-5）。

節點（628c 未涵蓋時才補）：
- co:pratt_whitney_canada（name「Pratt & Whitney Canada」，role 由主執行者依 vocab 定；母公司 RTX，依據 RTX 稿「Pratt & Whitney is an RTX (NYSE: RTX) business.」；INV-1：身分走 registry 登記，不以 ticker RTX 冒充子公司身分）。
- prod:pt6_e_series（「PT6 E-Series」逐字見 D1）。
- co:ga_asi（私人公司，依 D1「an affiliate of General Atomics」；INV-1／L9：ticker 映射為明確 null）。
- prod:mq_9b_skyguardian。
- co:honeywell（或 Honeywell Aerospace；分拆後身分需在登記時查證，本次未查）。

邊：
- E1：co:pratt_whitney_canada —supplies_to→ prod:mq_9b_skyguardian（或 co:ga_asi，與 628c 的 Honeywell 邊用同一個 dst，確保兩條邊可比）。attributes={qualification_status:"qualifying"}；不寫 substitutability、不寫 sole_source。建議 confidence 0.6（兩個 origin_event、單一 origin_entity、needs_review）。
  - D1_s1：「flew a company-owned MQ-9B SkyGuardian® Remotely Piloted Aircraft on July 15, 2024, with a PT6 E-Series model turboprop engine supplied by Pratt & Whitney Canada」
  - D1_s2：「Engine Demonstrates Its Viability for MQ-9B SkyGuardian®/SeaGuardian® RPA」
  - D2_s1：「Integrating their PT6 E-Series engine onto our MQ-9B SkyGuardian® aircraft offers an alternate option for future customers」
- E2（628c 的 Honeywell 邊，本 lead 另加一個 EdgeAssertion）：co:honeywell —supplies_to→ 同一 dst。本 lead 貢獻 attributes={substitutability: 3}，這是判讀值（judgment，走 pq2）。理由：替代引擎已完成整合並試飛，也公開作為客戶選項；但未進型錄、無客戶選用，換引擎仍需各客戶採購決定。qualification_status=designed_in 屬 628c datasheet 那個 assertion。**sole_source 不主張（留 null）**：量產只見 TPE331-10，但第二來源在驗證中，「今天量產唯一」與「結構上唯一」是兩種語意（L12：一欄承載兩種語意會兩邊都錯）。判讀理由寫進 review.md。
  - D3_s?：「POWER PLANT Honeywell TPE331-10 Turboprop」
  - D1_s3：「PT6 delivers a 33 percent increase in power over MQ-9B’s current engine, with a highly mature dual-channel Full Authority Digital Engine Controller.」
  - D2_s1（同上）。

disproof_condition（L7 三件套）：
- E1／E2 的 substitutability 條件：GA-ASI 公告停止 PT6 整合；或 2027 年版 datasheet 的 POWER PLANT 仍只列 TPE331-10，且 PT6 仍無任何客戶選用。
- 核查頻率：每半年（GA-ASI press-releases-by-year 清單 grep PT6＋重抓 datasheet 的 POWER PLANT 欄）。
- 觸發後 48 小時動作：在 review.md 記錄，提 EdgeAssertion 修正 proposal（substitutability 回調、E1 降 confidence）。
- 反方向：出現客戶選用或交付公告時，提 E1 升 qualified／designed_in 的 proposal。

L4 檢查：+33% 是相對另一端引擎的規格比，已留在 quote，不另立 attribute；沒有股價、估值、共識等時變數字。

review.md 備註（不入圖）：RTX 2025-10-14 稿平台清單與 RTX FY2025 10-K 都沒有 MQ-9B；FlightGlobal 149882 為 access_blocked。

**建議的等待（未登記）：** W1（awaiting_external，雙向）
- 條件（任一成立即叫醒）：
  - 正向：任一 MQ-9B 客戶宣布選用或交付 PT6 版本；或 GA-ASI datasheet 的 POWER PLANT 欄加列 PT6；或 P&WC／RTX 文件把 MQ-9B 列為 PT6 E-Series 平台。
  - 反向：GA-ASI 公告停止 PT6 整合；或 2027 年版 datasheet 仍只列 TPE331-10。
- 到期：2027-03-31。到期要重問，不是丟棄。
- 叫醒：本 lead（入圖後改指 E1 的 P&WC→MQ-9B EdgeAssertion，以及 E2 的 substitutability assertion）。
- 查法：curl https://www.ga-asi.com/press-releases-by-year.php?year=<當年> 後 grep PT6／Pratt；重抓 datasheet 後 grep「POWER PLANT」。
- 登記時點：本 watch 在 628c 包送審時一起登記；若包被 park，就掛在 park 紀錄上。

**要存進 library/raw 的原文：**
- https://www.ga-asi.com/ga-asi-flies-mq-9b-with-pratt-and-whitney-canada-pt6-e-series-engine：E1 與 E2 substitutability 的主要一手：P&WC PT6 E-Series 在 MQ-9B 首飛、+33% 動力、客戶可選（D1）
- https://www.ga-asi.com/ga-asi-tests-pt6-e-series-engine-pratt-whitney-mq9b-rpa：「alternate option for future customers」的逐字來源，也是第二個 origin_event（2022 地面測試）；內含 P&W Military Engines 總裁引言（D2）
- https://www.ga-asi.com/remotely-piloted-aircraft/pdf/mq9b-skyguardian-datasheet-032026.pdf：現行引擎「Honeywell TPE331-10 Turboprop」唯一的逐字具名，substitutability 的另一端錨點；與 628c 共用，只存一次（D3）
- https://www.rtx.com/news/news-center/2025/10/14/rtxs-pratt-whitney-canada-pt6-e-series-engine-surpasses-500-000-flight-hours：選存，供 review.md 使用：供應商端平台清單不含 MQ-9B，是「PT6 停在驗證階段」的佐證；也是 P&WC 隸屬 RTX 的逐字來源

<details><summary>逐條 atom</summary>

- **GA-ASI 於 2024-07-15 用一架公司自有的 MQ-9B SkyGuardian 首飛 Pratt & Whitney Canada 供應的 PT6 E-Series 渦輪螺旋槳引擎，飛行 44 分鐘**｜original_obtained｜tier 2（整合方／客戶端 GA-ASI 的整合與試飛公告；私人公司新聞稿，不是法定揭露）｜supports
  - 來源：https://www.ga-asi.com/ga-asi-flies-mq-9b-with-pratt-and-whitney-canada-pt6-e-series-engine（新聞稿第 1 段，dateline「SAN DIEGO – 19 July 2024」；副標「Engine Demonstrates Its Viability for MQ-9B SkyGuardian®/SeaGuardian® RPA」）
  - 逐字：General Atomics Aeronautical Systems, Inc. (GA-ASI) flew a company-owned MQ-9B SkyGuardian® Remotely Piloted Aircraft on July 15, 2024, with a PT6 E-Series model turboprop engine supplied by Pratt & Whitney Canada. Representatives from GA-ASI and Pratt & Whitney witnessed the first flight of the PT6 engine on MQ-9B, which lasted 44 minutes and demonstrated exemplary handling and acceleration.
  - 圖裡已有？否。extractions/*.json 對 PT6／Pratt／GA-ASI／MQ-9 的 quote 命中 0；config/company_identity.json 命中 0；全 repo（含 gitignore）只有 pending_leads／todo_pool 提到 MQ-9B
- **PT6 比 MQ-9B 現行引擎多 33% 動力，並配有 dual-channel FADEC**｜original_obtained｜tier 2｜supports
  - 來源：https://www.ga-asi.com/ga-asi-flies-mq-9b-with-pratt-and-whitney-canada-pt6-e-series-engine（新聞稿第 3 段）
  - 逐字：PT6 delivers a 33 percent increase in power over MQ-9B’s current engine, with a highly mature dual-channel Full Authority Digital Engine Controller.
  - 圖裡已有？否
- **PT6 是給 MQ-9B 客戶的替代選項（triage 理由寫的是「optional upgrade」）**｜original_obtained｜tier 2｜supports（但措辭有修正）
  - 來源：https://www.ga-asi.com/ga-asi-tests-pt6-e-series-engine-pratt-whitney-mq9b-rpa（2022-08-16 新聞稿（dateline「SAN DIEGO – 16 August 2022 – On July 29, 2022」地面全功率測試）第 2 段 David R. Alexander 引言；2024 稿第 2 段另有「customers who choose the Pratt & Whitney engine will benefit from…」）
  - 逐字：Integrating their PT6 E-Series engine onto our MQ-9B SkyGuardian® aircraft offers an alternate option for future customers that includes a 33 percent increase in power, dual channel electronic propeller and engine control system, as well as all the benefits of the PT6 engine family.
  - 圖裡已有？否
- **MQ-9B 現行（量產）動力為 Honeywell TPE331-10，而且截至 datasheet 版本，POWER PLANT 欄沒有列出 PT6**｜original_obtained｜tier 2｜limits（限縮第二來源的成熟度）
  - 來源：https://www.ga-asi.com/remotely-piloted-aircraft/pdf/mq9b-skyguardian-datasheet-032026.pdf（PDF 第 2 頁 CHARACTERISTICS 表；全文只有這個引擎型號，PT6／Pratt 命中 0；「Optional MQ-9B mission kits」清單也沒有引擎選項。⚠ 檔名寫 032026，但頁內版次碼是「0925」、版權「©2025」，published_at 不可直接取檔名（INV-6：答不出時間點就不能靜默填當前值））
  - 逐字：POWER PLANT
Honeywell TPE331-10 Turboprop
  - 圖裡已有？否（這份文件屬於 lead_628c 的一手）
- **推進層「至少有兩條已驗證路徑」（triage 理由）＝PT6 已成為可量產或已被客戶選用的第二來源**｜partial｜tier 2｜partially_contradicts（試飛有支撐；已驗證或量產沒有支撐）
  - 來源：https://www.ga-asi.com/press-releases-by-year.php?year=2026（GA-ASI 新聞稿年度清單：2025 年 62 篇、2026 年 46 篇（至今年 9 月，無分頁），PT6／Pratt 命中 0；2024 年只有首飛這一篇；datasheet POWER PLANT 只列 TPE331-10）
  - 逐字：Engine Demonstrates Its Viability for MQ-9B SkyGuardian®/SeaGuardian® RPA
  - 圖裡已有？否
- **交叉方（P&WC／RTX、Honeywell）獨立印證 PT6 用於 MQ-9B**｜partial｜tier 1（RTX 10-K）／2（RTX 新聞稿）｜neutral（沒有否認，只是沒有列入）
  - 來源：https://www.rtx.com/news/news-center/2025/10/14/rtxs-pratt-whitney-canada-pt6-e-series-engine-surpasses-500-000-flight-hours（RTX 2025-10-14 PRNewswire 稿第 1 段，平台清單沒有 MQ-9B。RTX FY2025 10-K（rtx-20251231.htm，Pratt & Whitney 2025 年重點）只有一句「Finally, in 2025, Pratt & Whitney Canada’s PT6 E-Series™ engine family surpassed 500,000 engine flight hours since entering service.」，沒有 MQ-9B。EDGAR 全文檢索「TPE331」2022–2026 共 0 筆。Honeywell TPE331 產品頁的「Compatible Platform」是動態載入，靜態頁沒有具名 MQ-9B。P&W 的聲音只以引言形式出現在 GA-ASI 2022 稿內：「Our PT6 E-series is the ideal engine for this mission and we look forward to working with General Atomics on this important program,” said Jill Albertelli, president of Pratt & Whitney Military Engines.」（origin_entity 仍是 GA-ASI）。FlightGlobal 149882 全文在付費牆後（access_blocked，只看到導言））
  - 逐字：Powering the Daher TBM 960 and the Pilatus PC-12 NGX and recently launched PRO, more than 700 PT6 E-Series engines are now in service with operators worldwide.
  - 圖裡已有？否
- **GA-ASI 自研或收購的引擎（HFE 2.0、Achates Power IP）是否構成 MQ-9B 的第三條推進路徑**｜contradicts｜tier 2｜contradicts（這個假設不成立）
  - 來源：https://www.ga-asi.com/ga-asi-completes-final-qualification-test-for-hfe-20-engine（HFE 2.0 稿副標（2024-11-19）；Achates 稿（2025-08-19）只寫「acquisition of key assets, including a portfolio of patents and other intellectual property, from Achates Power, Inc.」，沒有提到 MQ-9B）
  - 逐字：200-HP Heavy Fuel Engine Will Be Used for Gray Eagle 25M
  - 圖裡已有？否

</details>

## 3. 沒跑完（5 條，仍 triaged_go，未改任何欄位）

- lead_43890d7498305f453d34737e125a5c51
- lead_628cbb8d9793c06efda195b821bd4e1f
- lead_cad23eb9c017f318ac8f52d75da7d4a8
- lead_6c5046efbcfed55e7429f19f270a2a07
- lead_9b9d579795099de39f2ae6e50a5a5597
