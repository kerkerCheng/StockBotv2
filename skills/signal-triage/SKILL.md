---
name: signal-triage
description: >
  Stage 2 判斷層：決定一則從 web search 或 Engine B（如 aleabitoreddit）harvest 到的
  原始材料，值不值得進 pq1（source-trace＋抽取）。由 daily／weekly routine 在 harvest
  之後自動呼叫；設計上刻意寬鬆，PASS 後可自動研究，但不等於入圖核准。
  觸發詞：本 skill 由 routine 自動呼叫，不是使用者直接觸發的入口。
---

# Signal Triage Skill

## 定位一句話

**便宜的自動判斷：這則原始材料值不值得花 pq1 成本，先整理成可供使用者判斷的核准包。**

這不是 L8 來源獨立性的最終判定——那個判定永遠留給人工核准。PASS 只會把 lead 放進自動 pq1；
routine 追源、抽取並取得 prepared Research Action 後，才以完整核准包進 pq2。使用者 `go` 的語意是核准
prepared RA 入圖，不必在研究前先回答一次。判斷錯了的主要代價是多花一點研究 token，所以由 priority
與每輪 limit 控制，整體原則仍是**寧可放行，不要卡關**。

---

## 輸入

每則原始材料（raw item）包含：
- `text`：搜尋結果摘要 / 推文全文 / 轉發截圖的文字內容
- `source_url`：來源連結
- `matched_theme`：這則材料是因為匹配 `config/themes.txt` 的哪個主題/公司才被撈到的
- `harvest_channel`：`web_search` 或 `engine_b`（哪個管道找到的）

---

## 判斷五要素

### 1. 關聯性（Relevance）
這則材料是否真的關聯 `config/themes.txt` 或 `TICKER_MAP` 裡已追蹤的公司/主題？

- 命中具體公司名/ticker/技術詞（如 "Sivers"、"CPO"、"external laser source"）→ 過
- 只是泛用市場情緒、跟任何已追蹤標的都扯不上關係 → 不過

### 2. 新穎性（Novelty）
這是不是圖裡已經有的事實的第 N 次重複？

- 若能連到 Neo4j（U7a 通道正常運作時）：查 `query/graph_context.py --company-id co:<slug>`，比對這則材料的核心主張是否已經被現有 claims 覆蓋
- **若查不到圖（通道異常、逾時、或本次 routine 執行時暫時連不上）：不要因此卡住這則材料——直接跳過新穎性判斷，視為「無法確認，寬鬆放行」，並在稽核紀錄寫明原因**

### 3. 可引用性（Quotability）
材料裡有沒有具體、可逐字查核的內容？呼應 `AGENTS.md`「第一次真實抽取」的反幻覺鐵律。

- 有具體公司名/型號/數字逐字出現在原文 → 過
- 只有「業界人士認為」、「有消息指出」這種無法追溯的泛泛之詞 → 不過（這種材料就算抽取出來，也會在 extract 階段因為找不到逐字 quote 而被拒，等於白跑一趟，triage 階段先篩掉比較划算）

### 4. 潛在獨立性（Potential New `origin_entity`）
這則材料的來源，看起來像不像跟這家公司現有來源不同的 `origin_entity`？**這是五要素裡對 L8 gate 進展最有價值的一項。**

- 若這家公司在圖裡的來源目前都同一個 origin_entity（例如都是自報）→ 這則材料只要來源不同（客戶、第三方分析、轉發的券商研究）→ 高度優先放行，即使其他三項有點模糊
- 若這家公司已經有 ≥3 個 distinct origin_entity（L8 已過）→ 這一項的急迫性降低，但仍照其他三要素判斷

### 5. 矛盾／反證價值（Contradiction Value）
材料是否與現有 Claim、thesis 或主流因果鏈方向相反？反向材料不是雜訊；它可能最接近
`disproof_condition`，其優先度與「新 origin_entity」相同。

- 現有 thesis 認為 optical/CPO 取代 copper，但客戶文件顯示特定距離或世代仍偏好 copper → 高優先 PASS
- 現有 claim 認為 sole source，但客戶公告新增第二供應商 → 高優先 PASS
- 只是在社群上唱反調，沒有可逐字查核的公司名、事件或數字 → 仍因可引用性不足 FILTER

矛盾性只提高優先度，不放寬關聯性與可引用性兩個硬指標。與現有 thesis 相反的材料即使
不是新主題、也不是新 origin，只要具體可查，就不應被「已看過類似內容」的新穎性判斷濾掉。

---

## 決策規則

只有兩種結果，沒有「先問一下」的第三種：

- **PASS** → 寫回 `triaged_go`，由 routine 依 priority 自動 source-trace＋extract；prepared RA 才進 pq2
- **FILTER** → 寫回 `triaged_no_go`／park，並記錄材料摘要 + 篩掉理由

**寬鬆原則的具體操作：** 五要素中，關聯性和可引用性是硬指標（沒關聯、沒有可查核內容 → 直接 FILTER，抽取了也沒用）。新穎性、潛在獨立性與矛盾／反證價值是軟指標；後三者任一項不確定、可能有價值或明確命中時，一律 PASS。不要因為材料反駁現有 thesis、或與既有主題重疊就篩掉——這是「寧可多花一點抽取力氣、也不要悄悄漏掉好線索」的核心（R12）。

---

## 輸出格式

每次 routine 執行後，Stage 2 的結果彙整進 Daily Brief／Weekly Report 的稽核段；不開 PR／Issue：

```
## Triage 結果

本次 harvest N 則原始材料。

**通過（M 則）：** 進 priority pq1；完成後以 prepared RA 進 pq2
- [材料摘要] — 判斷理由：[哪一項要素觸發放行]

**篩掉（P 則）：**
- [材料摘要] — 篩掉理由：[關聯性不足 / 無可查核內容]
```

篩掉的項目**必須列出來**，不能悄悄消失——這是使用者事後稽核「篩選有沒有太嚴格」的唯一依據。

---

## 與其他 skill 的分工

| 情況 | 用哪個 skill |
|------|-------------|
| 本機 daily／weekly routine 判斷一則 harvest 材料值不值得進 pq1 | 本 skill |
| 使用者自己貼一條推文/新聞，要不要入庫 | `skills/lead-intake`（人在場的 Fast Path，判斷邏輯類似但由人主導） |
| 新公司決定要不要入圖 | `skills/company-onboard`（本 skill 只建議候選，不觸發） |
