# CPO 反向 thesis(SemiAnalysis「Powered Down, Lights Off」)追源記錄

**日期:** 2026-07-21
**動機:** 方向 1 深挖客戶端時發現此報告是對圖中 CPO 需求 thesis 的最強公開反駁(2026-06-09 發布當日 LITE/COHR/AAOI/GLW/MRVL 大跌);圖中原本完全沒有反面視角。

---

## 1. 結論(一句)

**SemiAnalysis 原報告(tier 3,付費)追源未果——不得直接入圖;以公開的 GSR 反駁文(tier 3,origin=Global Semi Research,逐字取得)作 honest passthrough 載體入庫:SA 主張標明「原報告未獨立取得、依 GSR 轉述」,GSR 自己的反駁與供應鏈查核依其逐字入庫。論戰兩面都進圖,但 SA 主張不算獨立 origin。**

## 2. Trace 記錄(source-trace 格式)

```yaml
claim: "SemiAnalysis『Powered Down, Lights Off』(2026-06-09)主張 CPO 延遲(scale-out 下修至 2027、scale-up 推 2029、Spectrum-6 slip)"
lead_url: "web search 發現(多家二手一致提及)"
claimed_origin: "SemiAnalysis(付費研究報告)"
attempts:
  - route: "exact-phrase 搜尋一手 URL"
    query_or_url: "SemiAnalysis \"Powered Down, Lights Off\" co-packaged optics June 2026"
    result: no_result
    note: "多家二手(viksnewsletter/GSR/tradingkey/KuCoin)一致轉述,但無 canonical 一手 URL"
  - route: "URL 猜測 1(newsletter 子網)"
    query_or_url: "https://newsletter.semianalysis.com/p/powered-down-lights-off"
    result: no_result
    note: "HTTP 404"
  - route: "sitemap 掃描"
    query_or_url: "https://newsletter.semianalysis.com/sitemap/2026"
    result: no_result
    note: "sitemap 無此標題(付費文章可能不列)"
  - route: "URL 猜測 2(主站日期樣式)"
    query_or_url: "https://semianalysis.com/2026/06/09/powered-down-lights-off/"
    result: no_result
    note: "HTTP 404"
trace_status: tier_1_2_honest_passthrough   # 載體=GSR 反駁文(逐字取得);SA 主張標「未獨立取得」
obtained_origin_entity: "Global Semi Research"
obtained_source_type: industry_report
evidence_tier: 3
quote: "見 extractions/gsr_cpo_not_delayed_2026_06_10.json(7 句逐字)"
locator: "globalsemiresearch.substack.com/p/co-packaged-optics-is-not-delayed"
storage_permission: repo_excerpt
next_action: extract   # 已入庫;SA 原文若日後取得→比對轉述並升級 cl1
```

## 3. 入庫形狀(extractions/gsr_cpo_not_delayed_2026_06_10.json)

- **cl1**(honest passthrough):SA 延遲主張存證——scale-out 下修至 2027、scale-up 推 2029、Spectrum-6 >3.5dB insertion loss;明標「依 GSR 轉述,原報告未獨立取得」,speculative。
- **cl2**:GSR 反駁——「CPO is not being delayed」;Lumentum FA 產線 booked out 與延遲敘事矛盾;0.95^32≈19% 良率算法凍結悲觀單點。
- **cl3**(dated observation):NVIDIA 對 Coherent/Lumentum 的 CW 雷射 guidance 1月 ~40M → 4-5月 ~100M 顆(GSR 供應鏈查核)。
- **邊**:s4 逐字點名兩家 → `coherent→nvidia`、`lumentum→nvidia` supplies_to 各補一筆 **GSR 第三方 assertion**(coherent 邊由 2 源升 3 源,首個非當事方)。

## 4. 順帶結構性發現(方向 1 深挖客戶端的結論)

- **買方不揭露雷射 BOM 是結構性的**:NVIDIA 官方 CPO 技術 blog(2025-08-26)只點名 TSMC(COUPE),雷射僅稱「industry partners」;NVIDIA/Broadcom 法說與 PR 同樣不點名。Coherent/Lumentum 那 37 條技術層供貨自報邊**無法**靠客戶端逐字補強,只能靠第三方供應鏈研究(GSR/SemiAnalysis 這類)點名。
- **公司層** 的客戶端印證是可得的(本輪:NVIDIA→Lumentum $2B 8-K+PR、GSR 點名兩家供 NVIDIA CW 雷射),L8 補強應集中在公司層邊。

## 5. Lead only(未入庫,留線索)

- **SemiAnalysis 利益衝突指控**:多家幣圈聚合站引「Serenity」(= aleabitoreddit Substack channel 名)稱 SemiAnalysis 發空報後參與 LAZR ETF、納入其唱空標的(LITE/Himax 等)。tier 3-4、未追到一手 → lead only,不入圖。若成立,會影響 cl1 反向 thesis 的權重(SA 動機可疑),8/27 前後如有監管動作再追。
- SemiAnalysis 報告全文:若日後取得(訂閱/公開化),比對 GSR 轉述準確性,升級或修正 cl1。
