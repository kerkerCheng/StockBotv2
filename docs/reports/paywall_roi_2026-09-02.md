# Paywall ROI 清單（Workstream B，2026-09-02）

> 依 `AGENTS.md`：任何新訂閱／購買必須另列 exact 金額與方案，由使用者逐項核可。
> 本清單盤點**至今實際遇到**的 paywall（來源：`pending_leads.json` 的
> `trace_requires_user`／付費 parked reason，2026-09-02 實測 11 筆命中、去重後 3 類）。
> 這是 point-in-time 報告；之後遇到新 paywall 由 pq1 park 流程自然累積，不回寫本檔。

## 第 1 類：賣方研究報告（機構通路）

| 實例 | 需求 | 方案與金額 | 建議 |
|---|---|---|---|
| Rosenblatt channel check（AAOI/CPO，pq2 [193] 已 defer） | 驗證轉述的 channel check 細節 | **無公開零售方案**——機構訂閱制，個人無法單買 | **不買也買不到**。轉述已依 L8 隔離 tier 3（該來源有已知誤判紀錄：曾誤指 AMD 為 AAOI 首個 CPO 客戶）；等一手 filing 印證同一事實即可 |
| 賣方 ASP 預估（ESMT/記憶體，原 [354]） | 記憶體價格週期預估 | 同上，機構通路 | **使用者已於 2026-09-01 明確 drop**——ESMT 四維第 3 維不過、無系統承接點，terminal |

## 第 2 類：法說會逐字稿（transcript）

**這是唯一重複出現的真實缺口**（兩例：COHR Q4 FY2026 三句關鍵 quote、MTSI 的 InP DFB
短缺 quote——皆不在任何 SEC filing，免費 transcript 源 404）。

| 方案 | Exact 金額 | 覆蓋 |
|---|---|---|
| Seeking Alpha Premium | **US$299/年**（常見促銷 US$239 首年） | 美股 transcript 完整，延遲數小時 |
| 本機音訊追源（既有能力，**US$0**） | `scripts/transcribe_audio.py`＋官方 webcast replay | ASR 提供 timestamp locator，精確技術詞回聽核對；`AGENTS.md` 已定此路徑 |

**建議：不訂閱。** 系統已有零成本路徑（faster-whisper 本機轉錄＋回聽核對），且需求頻率
（兩個月 2 例）撐不起年費；ASR 路徑同時符合「不提高 evidence tier、quote 須回聽核對」
的既有紀律。若未來頻率升到每週一例再重開本項。

## 第 3 類：非 paywall 的誤命中（記錄以免重查）

- Samsung 法說轉述（lead_39827ad9）：卡的是**記憶體軸 scope 決策**不是付費——已另行處理。
- AEVA 8-K（lead_1aa835b3）：卡的是 registry onboard 前置，一手免費可得。

## 結論

**目前沒有任何值得核可的付費項**：第 1 類買不到也不需要、第 2 類有零成本替代、
第 3 類不是 paywall。Workstream B 的常設機制照舊：pq1 park 時標
`trace_requires_user=true`＋exact 金額，`source_trace_review` 取 pq2 編號問使用者。
