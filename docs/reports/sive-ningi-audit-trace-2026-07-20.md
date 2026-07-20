# SIVE 來源可信度審查 — Ningi 指控追源記錄

**日期：** 2026-07-20
**追源對象：** `sivers_ar_2025_financials` / `sivers_ar_2025_photonics_excerpt` 的 `source_under_audit` hold
**audit_id：** `sivers_2025_annual_report_2026_07_12`（status=active，review_by 2026-08-27）
**起因：** 執行「SIVE 收尾」時發現此 hold，改為追 Ningi 指控原文（使用者指示：追 #1）

---

## 1. 追源結論（一句）

**這不是單純做空方噪音。指控本身是 tier-3（Ningi 做空報告），但關鍵指控已由公司「自己的審計」以 tier-1 佐證：2023–25 帳目已重編至 US PCAOB、年報已出具 going-concern 材料不確定性。credibility hold 有紮實基礎，且比本地舊記錄描述的「pending」更嚴重——多項已是既成事實。**

---

## 2. Trace 記錄（source-trace 格式）

```yaml
claim: "Ningi Research 指控 Sivers ~97M SEK(~2025 營收 31%)不當認列;審計 going-concern;重編"
lead_url: "本地 audit ledger + thesis/sivers_v2_lane_memo.md（二手轉述，evidence_ref 僅指 GitHub Issue #2）"
claimed_origin: "Ningi Research（做空報告）"
attempts:
  - route: "exact-phrase 搜尋 Ningi 一手"
    query_or_url: "Ningi Research Sivers Semiconductors short report revenue recognition"
    result: found
    note: "定位一手報告 ningiresearch.com/2026/06/01/... 標題含 'Dubious Revenue Accounting...Since 2018';多家二手覆核"
  - route: "WebFetch Ningi 一手全文"
    query_or_url: "https://ningiresearch.com/2026/06/01/sivers-semiconductors-sive-st-...（完整見 ledger）"
    result: blocked
    note: "HTTP 403 Forbidden;做空站擋抓取。指控內容經 ad-hoc-news / dealroom / marketscreener 等多家二手一致覆核"
  - route: "公司 tier-1 佐證（Sivers AR / 審計）"
    query_or_url: "Sivers Semiconductors Ningi response restatement going concern 2026"
    result: found
    note: "審計要求 2023-25 重編至 US PCAOB;2025 淨損 186.5M->222.6M SEK;年報 going-concern。與已入庫 sivers_ar_2025_financials 數字一致"
  - route: "公司一手（Sivers 自家 press）"
    query_or_url: "https://www.sivers-semiconductors.com/press/...directed-share-issue...（2026-06-30）"
    result: found
    note: "SEK 600M 定向增資,以 AI datacenter/LiDAR 成長 + R&D 為名,隻字未提 going-concern / 指控 / 重編"
  - route: "公司回應 / 反駁"
    query_or_url: "Sivers official response rebuttal Ningi board resignation lock-up"
    result: found
    note: "迄 2026-07 中,公司未提出詳細公開反駁。另證實董事會出走與監管調查"
  - route: "公司一手 AR PDF 逐字核 going concern（回應使用者質疑來源）"
    query_or_url: "https://www.sivers-semiconductors.com/wp-content/uploads/2026/05/Sivers_annualreport_2025_2.pdf（WebFetch 無法解析,存本地後以 pypdf 抽 86 頁）"
    result: partial
    note: "找到公司/Board 自揭 material going-concern uncertainty 逐字;但審計(Deloitte)正式意見段未乾淨抽出,無法證實『審計保留意見』。更正先前過度陳述"
trace_status: tier_1_2_honest_passthrough
obtained_origin_entity: "Ningi Research（指控,tier-3）+ Sivers/審計（佐證事實,tier-1,已入庫 AR）"
obtained_source_type: "industry_report(做空) / filing(公司 AR) / official_pr(增資)"
evidence_tier: 3
quote: null   # Ningi 一手 403;引用以二手覆核與公司 tier-1 佐證為準
locator: null
storage_permission: local_only   # Ningi 站授權不明 + 擋抓取,僅存 canonical URL
next_action: park_trace_backlog   # hold 維持;8/27 為量級分辨點
```

---

## 3. 指控內容（Ningi 一手，2026-06-01，tier-3；經多家二手一致覆核）

- **~97M SEK（≈2025 營收 31%）不當認列**，具體：
  - 政府/研究補助（grants）當成商業營收入帳；
  - 改寫會計政策，使**原料到倉即認列營收**（尚未出貨、產品尚未製造）；
- **客戶合約空洞**、**2018 起「即將量產」承諾一再跳票**。
- **2026-07-01 追打**：Ningi 發第二則 thread 批評 SEK 700M 定向增資。

## 4. 已是既成事實的 tier-1 佐證（公司自己的年報，非做空方說法）

已核 Sivers 2025 Annual Report 全文（86 頁，Deloitte AB / Alexandros Kouvatsos 簽證；2026-07-20 以 pypdf 抽 PDF 驗證）：

- **2023–25 帳目已重編至 US PCAOB 標準**；2025 淨損由原報 186.5M **重編為 222.6M SEK**（= 已入庫 `sivers_ar_2025_financials` 的數字）。
- **公司/Board 於年報「going concern 風險」段自揭 material going-concern uncertainty**，逐字：「there is a material risk and uncertainty factor that the Group and the Parent Company may not be able to continue operations to the planned extent」，財報仍以 going concern basis 編製。
  - ⚠ **精確界定**：這是**公司自揭的 material uncertainty**，非已證實的「審計保留意見」。PDF 可抽文字中 `material uncertainty related to going concern` / `substantial doubt` / `qualified opinion` / `emphasis of matter` / `in our opinion` **皆為 0**；Deloitte 正式意見段（revisionsberättelse）未乾淨抽出，故不能斷言審計已修正意見。先前把它寫成「審計出具 going-concern 保留意見」是**過度陳述**，已更正。
- 佐旁：Q1 2026 淨銷售 61.9M SEK（-22% YoY）、adj EBITDA -13.8M、營運現金流 -49.2M。

## 5. 伴隨的治理/融資危機（tier-3 discovery，方向一致）

- **董事會出走**：副主席 Tomas Duffy、創辦人 Erik Fallström、Keith Halsey 於 6/15 AGM 前辭任。
- **雙重監管 + 洩密(insider/leak)調查**進行中。
- **SEK 600M 定向增資（2026-06-30）**，以成長為名、未提 going-concern；April placement 的 lock-up 須豁免才能完成本輪，稀釋壓力大。
- 股價自高點蒸發約 2/3;7/16 lock-up 到期後內部人再上鎖（120 天/1 年）試圖穩盤。

---

## 6. 對 hold 與 thesis 的判斷

1. **credibility hold 維持 active，且應維持到 going-concern 解除為止**——不是「8/27 一過就清」。going-concern + 重編已是既成事實，即使 8/27 Q2 沒有更多壞消息，這兩點在後續乾淨審計出來前都成立。清除 hold 的正確條件是：**後續審計報告撤除 going-concern 材料不確定性 + 營收認列項目獲釐清**，而非時間到期。

2. **⚠ thesis 生命週期：disproof 條件疑似已觸發。** `sivers_v2_lane_memo.md` 自訂的 retire 條件之一是「審計出具持續經營保留意見 → retired」。追源顯示審計**已在年報標示 going-concern 材料不確定性**。需釐清那是「保留意見(qualified opinion)」還是「材料不確定性 emphasis」——用語不同、觸發判定不同——但無論何者，**thesis 應由 `review_required` 下修，建議直接 `retired`**（或至少 severe watch），不宜停在 review_required。此為 L7 人工決策 + 更新 `thesis/lifecycle.json`，未擅自改。

3. **對任何 SIVE thesis 的直接殺傷**：Ningi 指控的核心（grants 當營收、原料到倉即認列）直接打在 Photonics 營收（SEK 93.4M）上，而那正是任何看多論點的立足點。加上 going-concern + 稀釋 + 董事出走 + 監管調查，**SIVE 在本系統證據基底清乾淨前，實務上不可投資**。

---

## 7. 8/27 分辨點要看什麼

- Q2 報告是否再度重編營收、幅度是否達 Ningi 指控量級（31% / 97M SEK）。
- 審計對 going-concern 的最新措辭（維持/升級/撤除）。
- 公司是否終於提出逐項反駁（迄今無）。
- 增資後現金跑道與稀釋後股數。

## 8. 未擅自做、留給使用者決定

- 將治理危機（going-concern / 重編 / 董事出走 / SEK 600M 增資 / 監管調查）作為 claim/edge 入圖（tier-1 部分來自已入庫 AR，可補；tier-3 部分僅 discovery）。
- 更新 `thesis/lifecycle.json` 把 SIVE thesis 轉 `retired`（見 §6.2）。
