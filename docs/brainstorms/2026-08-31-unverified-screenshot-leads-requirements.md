# 追不到原檔的 lead：「假設為真」機制（brainstorm，2026-08-31）

> 使用者原話：「針對找不到來源的 lead（例如附圖但我們找不到原檔案）……感性上我們可以把
> 它當作真的，但現在是不是就直接 park，我們的圖也用不到，基本上也找不到文件就石沉大海。
> 但如果我們放一個特殊的邊，假設訊息為真，我們能得到什麼？這部分該怎麼做才能追到更前段
> 的 alpha，我基本上是相信推文的截圖不是改圖的。」
> 狀態：**方向討論，未成為政策**——四個 authority gate 與 evidence tier 紀律不因此放寬。

## 現況與痛點

現行：截圖／paywall 未果 → `parked`＋`trace_status=isolated_tier_3`＋`trace_next_trigger`。
防漏機制只有兩個：同標的新 lead 觸發 related_entity_signal 重排 bounded pq1、
`source_trace_review` 問使用者要不要付費。**圖完全不用它**——於是最早的訊號（往往是
alpha 最前段）以「等到有可追源版本」為代價被延後，而很多截圖永遠等不到。

使用者的判斷是對的一半：截圖偽造率低（改圖成本高、曝光風險大）；但 L11 的教訓是另一半
——截圖真實 ≠ 截圖裡的陳述真實（原推可能本身就錯、斷章、或後來被刪除修正）。
所以問題不是「信不信」，是**「假設為真」的資訊能不能被系統性使用而不污染 evidence**。

## 核心洞察：假設為真的價值不在「入圖」，在「回答 what-if」

把截圖 claim 直接入圖（哪怕標弱）是走錯門——它會進 evidence 計數、進排序、被未來的
自己引用（L11 假交叉驗證的溫床）。真正要的是回答三個問題：

1. **如果這是真的，排序會變嗎？**（decision_impact 預演）——會大變的截圖才值得花錢／
   花力氣追原檔；不會變的 park 掉毫無損失。這直接把「要不要追」從感覺變成可計算。
2. **如果這是真的，它與圖上哪些既有 claim 矛盾？**——矛盾偵測不需要 claim 為真，
   矛盾本身就是研究訊號（disproof 的 leading indicator）。
3. **它指向哪些我們沒 onboard 的實體？**——新公司／新技術詞的 discovery 價值與真偽無關。

## 設計草案：hypothesis overlay（假設層），不是特殊的邊

- **儲存**：獨立於 canonical graph 的 hypothesis 記錄（掛在 lead 上或獨立
  `library/leads/hypotheses.json`），欄位＝結構化的假想 claim/edge（同 extraction schema）
  ＋`provisional: true`＋來源截圖 ref＋**到期日**（無限期假設會腐爛成事實）。
- **消費端唯一入口＝what-if 查詢**：`rank_bottlenecks(..., overlay=[hypothesis])` 輸出
  「疊加後排序 diff」——只在 source-trace／pq1 receipt 裡呈現「若為真：COHR→X 邊 sub 4→5，
  可行動排序 #2→#1」，**不寫入圖、不進 daily 排序**。
- **升級路徑不變**：what-if 顯示高影響 → 升高追原檔優先權（加大 trace 重試、建議付費、
  或以 entity linkage 掛更強 trigger）；原檔到手才走正常 admission。
- **矛盾偵測**：overlay claim 與 canonical claim 對撞時，產一條 pq1 研究題
  （「截圖聲稱 X，圖上 tier-1 說 Y——值得查」），這不需要相信截圖。

## 硬邊界（不可談判）

1. hypothesis **永不**參與 evidence 分級、L8 計數、五軸 assessment 的 evidence_refs。
2. **永不**出現在預設排序輸出；what-if diff 只在明確請求時計算（標題必含「若為真」）。
3. 每筆必有到期／觸發條件；到期未升級自動歸檔（不是刪除——留 audit）。
4. 入圖唯一路徑仍是原檔 admission；「what-if 影響很大」不構成 tier 豁免
   （L15：LLM 可以解析與提議，不可以授權）。

## 付費牆現實：多數原檔永遠拿不到（2026-08-31 使用者補充後改寫主軸）

> 使用者：「很多報告我其實始終都不會拿到原檔案，因為大部分都要付費，我可能也不會付。」

這改變了機制的重心。「找不到原檔」其實是三類，處置完全不同：

| 類 | 例 | 原檔會出現嗎 | 正確機制 |
|---|---|---|---|
| **A. 官方文件的截圖** | filing 頁面、PR、法說 slide | 會，免費，只是晚幾天 | 預寫 RA 骨架＋EDGAR/MOPS watch，原檔落地小時級入圖 |
| **B. 付費研究的截圖** | TrendForce、sell-side note、DigiTimes 全文 | **永遠不會**（不付費） | **claim 級平行驗證**（見下） |
| **C. 匿名爆料／供應鏈傳聞** | 無出處推文、群組轉傳 | 無原檔概念 | 事件驗證 trigger（等世界揭曉） |

**B 類的核心 reframe：追的不是「原檔」，是「同一事實的可及一手」。** 付費報告裡的
「事實」（產能、市占、訂單、價格）幾乎都源自更上游的一手（公司揭露、政府統計、財報）
或會在數週內被公司自己證實；報告裡的「觀點」（評級、預測）本來就不是 evidence、
只有 lead 價值。所以把截圖 claim 拆成 atomic facts 後，每個 fact 標**平行驗證路徑**：

1. **現在就免費可查**（公司 filing／MOPS／政府統計）→ 那不是 dead lead，是普通研究題
   ——本專案實際上一直在做這件事（Cignal 全文 paywall，但摘要頁關鍵句免費；TrendForce
   數字常被公司法說證實）。
2. **未來事件可驗**（「Q3 訂單暴增」→ Q3 財報出來自動對照）→ 掛 fact-check trigger，
   **驗證免費、只是要等**；等待期 what-if 先用。這類 trigger 是現有 waiting 機制的
   直接延伸（`event_type=fact_verification`＋對照欄位）。
3. **永遠無法驗的純觀點** → park 是對的，但 park 前跑一次 what-if：高影響者轉成
   「找平行證據」研究題，低影響者安心沉底。

**付費變成可計算的決策**：what-if 累積下來，若某訂閱源的截圖反覆命中「高影響＋
無平行路徑」，`source_trace_review` 給使用者的就不再是模糊的「要不要付費」，而是
「這個源過去 N 次高影響、平行驗證失敗率 M%，年費 $X」——不付仍是預設，但拒絕變得有據。

## 開放問題

- overlay 的量測：追蹤「what-if 判高影響 → 後來原檔到手」的命中率，才知道這機制
  是在找 alpha 還是在生噪音（L14：新機制不得默認信任，要能回答讓哪個數字變）。
- 截圖本身的保存：`library/private/` 存圖檔＋OCR 文字？（版權與 storage_permission 要議）
- 與 weekly topic discovery 的分工：hypothesis 高影響清單是否進 weekly 報告。

## 下一步（需 pq2 核准才動工）

1. 最小原型：hypotheses.json schema＋`bottleneck --what-if <file>` 輸出排序 diff。
2. 挑 2-3 條歷史 parked 截圖 lead 回填測試：what-if 會不會判出「當時就該花力氣追」。
